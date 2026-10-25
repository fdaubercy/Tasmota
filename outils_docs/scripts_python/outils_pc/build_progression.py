r"""Progression d'un `pio run` de la page Build et televersement : lecture de la sortie, ligne a ligne.

Module PUR : aucune E/S, aucun appel a pio. Il recoit les lignes de la sortie (avec leurs codes ANSI
et leurs chemins `\` ou `/`), en deduit l'etape, le pourcentage, le resultat et un extrait d'erreur.
Les durees ne sont PAS lues dans la sortie : elles sont mesurees par l'execution en serie.

Les expressions suivent les formats connus de PlatformIO / SCons / esptool et les lignes propres au
depot (`post_esp32.py`, pre-script), calibrees sur de vraies sorties (A8, 2026-10-25) : un build
complet reprend la plupart des objets du cache (`Retrieved ... .o' from cache`, comptes comme les
`Compiling`), un build incremental n'en compile qu'une partie, et esptool ecrit plusieurs zones
(bootloader, partitions, firmware, littlefs...), chacune de 0 a 100 %.
"""

import re
from collections import deque

ETAPE_PREBUILD = "Pré-build"
ETAPE_COMPILATION = "Compilation"
ETAPE_LIENS = "Édition des liens"
ETAPE_ENVOI = "Téléversement"
ETAPE_FS = "Construction du FS"
ETAPE_EFFACEMENT = "Effacement de la flash"

ACTIONS = ("compiler", "upload", "erase_upload", "buildfs", "uploadfs")
PLAFOND = 99          # jamais 100 % avant le [SUCCESS] de pio

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07")
# "Compiling <chemin>.o" : SCons, chemin avec / ou \ (les .cpp/.c seuls ne sont pas des objets)
_COMPILE = re.compile(r"^\s*Compiling\s+\S.*\.o\s*$")
_REPRIS = re.compile(r"^\s*Retrieved\s+`.*\.o' from cache\s*$")
_ZONE = re.compile(r"^\s*Writing\s+'([^']+)'\s+at\s+0x")
_LIENS = re.compile(r"^\s*Linking\s+\S")
# esptool : "Writing at 0x00010000 [=====>  ] 45.2% 123/456 bytes..." ou ancien "Writing at 0x... (45 %)"
_ESPTOOL = re.compile(r"Writing at 0x[0-9a-fA-F]+.*?(\d+(?:\.\d+)?)\s*%")
# espota (OTA) : "Uploading: [=====     ] 52%"
_OTA = re.compile(r"^\s*Uploading:\s*\[[^\]]*\]\s*(\d+(?:\.\d+)?)\s*%")
_ENVOI = re.compile(r"^\s*(Uploading\s+\S|Looking for upload port|Auto-detected:|Configuring upload protocol)")
# "Uploading <fichier>" ; PAS "Uploading stub flasher..." qu'esptool ecrit en se connectant pour erase-flash
_TELEVERSE = re.compile(r"^\s*Uploading\s+(?!stub\b)\S")
# erase_upload : libelle "Erasing..." de l'action $ERASECMD (platforms/espressif32/builder/main.py:1990), puis
# esptool v5.4.0 "Erasing flash memory (this may take a while)..." et "Flash memory erased successfully in X
# seconds." (packages/tool-esptoolpy/esptool/cmds.py:2273 et :2282)
_EFFACEMENT = re.compile(r"^\s*(Erasing\.\.\.|Erasing flash\b)")
_EFFACE = re.compile(r"^\s*Flash memory erased successfully")
_FS = re.compile(r"Nous allons créer le système de fichiers|Building FS image|mklittlefs|Creating filesystem")
_FS_AUSSI = re.compile(r"Utilisera une commande de téléchargement personnalisée")
_RESULTAT = re.compile(r"\[(SUCCESS|FAILED)\]")
_ERREUR = re.compile(r"error:|Error|FAILED|fatal error")     # esptool : "A fatal error occurred: ..."


def retire_ansi(texte):
    """Texte sans les codes de couleur / de curseur ANSI."""
    return _ANSI.sub("", texte)


class Suivi:
    """Etat d'un `pio run` en cours. `ligne()` renvoie un evenement quand l'etat change, sinon None.

    `reference_o` : nombre total d'objets de l'env (build complet) ; `increment` : objets du dernier
    build incremental. La base du % est l'increment, sauf des qu'un objet sort du cache (build
    complet) ou que l'increment est depasse : alors le total. `estime` : le total est emprunte a un
    autre env (premier build de celui-ci), il est affiche « ≈ » dans le detail.
    """

    def __init__(self, action, reference_o=None, increment=None, estime=False):
        if action not in ACTIONS:
            raise ValueError(f"action inconnue : {action!r}")
        self.action = action
        self.reference_o = reference_o if reference_o and reference_o > 0 else None
        self.increment = increment if increment and increment > 0 else None
        self.estime = estime
        self.nb_o = 0
        self.repris = False
        self.zone = ""
        self.resultat = None
        self.extrait_erreur = []
        self.fs_aussi = False
        self.efface = False               # erase_upload : effacement termine
        self.etape = ETAPE_PREBUILD
        self.pourcent = None
        self.detail = ""
        self._erreurs = deque(maxlen=10)

    def _evenement(self, etape, pourcent, detail):
        if pourcent is not None:
            pourcent = max(0, min(PLAFOND, int(pourcent)))
        if (etape, pourcent, detail) == (self.etape, self.pourcent, self.detail):
            return None
        self.etape, self.pourcent, self.detail = etape, pourcent, detail
        return {"etape": etape, "pourcent": pourcent, "detail": detail}

    def ligne(self, texte):
        t = retire_ansi(texte).rstrip("\r\n")
        if _ERREUR.search(t):
            self._erreurs.append(t.strip())
            self.extrait_erreur = list(self._erreurs)
        if _FS_AUSSI.search(t):
            self.fs_aussi = True
        m = _RESULTAT.search(t)
        if m:
            self.resultat = "succes" if m.group(1) == "SUCCESS" else "echec"
            if self.resultat == "succes":
                self.pourcent, self.detail = 100, "terminé"     # seul cas ou 100 % est permis
                return {"etape": self.etape, "pourcent": 100, "detail": "terminé"}
            return self._evenement(self.etape, self.pourcent, "échec")
        repris = bool(_REPRIS.match(t))
        if repris or _COMPILE.match(t):
            self.nb_o += 1
            self.repris = self.repris or repris
            base = self._base()
            if base:
                marque = "≈" if self.estime and base == self.reference_o else ""
                return self._evenement(ETAPE_COMPILATION, self.nb_o * 100 // base,
                                       f"{self.nb_o}/{marque}{base} fichiers")
            return self._evenement(ETAPE_COMPILATION, None, f"{self.nb_o} fichiers")
        if self.action == "erase_upload" and not self.efface:
            # Recherche du port et effacement : une seule etape, jusqu'a "Uploading <firmware>"
            if _EFFACE.match(t):
                self.efface = True
                return self._evenement(ETAPE_EFFACEMENT, None, "flash effacée")
            if _EFFACEMENT.match(t) or (_ENVOI.match(t) and not _TELEVERSE.match(t)):
                return self._evenement(ETAPE_EFFACEMENT, None, "")
        m = _ZONE.match(t)
        if m:
            self.zone = re.split(r"[\\/]", m.group(1))[-1]
            return self._evenement(ETAPE_ENVOI, None, self.zone)
        if _LIENS.match(t):
            return self._evenement(ETAPE_LIENS, None, "")
        m = _ESPTOOL.search(t) or _OTA.match(t)
        if m:
            return self._evenement(ETAPE_ENVOI, float(m.group(1)), self.zone)
        if _ENVOI.match(t):
            return self._evenement(ETAPE_ENVOI, None, self.zone)
        if _FS.search(t):
            return self._evenement(ETAPE_FS, None, "")
        return None

    def _base(self):
        """Base du % de compilation (voir la docstring de la classe), None si aucune."""
        if self.increment and not self.repris and self.nb_o <= self.increment:
            return self.increment
        return self.reference_o
