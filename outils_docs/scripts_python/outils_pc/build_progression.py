"""Progression d'un `pio run` de la page Build et televersement : lecture de la sortie, ligne a ligne.

Module PUR : aucune E/S, aucun appel a pio. Il recoit les lignes de la sortie (avec leurs codes ANSI
et leurs chemins `\` ou `/`), en deduit l'etape, le pourcentage, le resultat et un extrait d'erreur.
Les durees ne sont PAS lues dans la sortie : elles sont mesurees par l'execution en serie.

Les expressions suivent les formats connus de PlatformIO / SCons / esptool et les lignes propres au
depot (`post_esp32.py`, pre-script) ; elles sont a calibrer sur une vraie sortie (action A8 du plan).
"""

import re
from collections import deque

ETAPE_PREBUILD = "Pré-build"
ETAPE_COMPILATION = "Compilation"
ETAPE_LIENS = "Édition des liens"
ETAPE_ENVOI = "Téléversement"
ETAPE_FS = "Construction du FS"

ACTIONS = ("compiler", "upload", "buildfs", "uploadfs")
PLAFOND = 99          # jamais 100 % avant le [SUCCESS] de pio

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07")
# "Compiling <chemin>.o" : SCons, chemin avec / ou \ (les .cpp/.c seuls ne sont pas des objets)
_COMPILE = re.compile(r"^\s*Compiling\s+\S.*\.o\s*$")
_LIENS = re.compile(r"^\s*Linking\s+\S")
# esptool : "Writing at 0x00010000 [=====>  ] 45.2% 123/456 bytes..." ou ancien "Writing at 0x... (45 %)"
_ESPTOOL = re.compile(r"Writing at 0x[0-9a-fA-F]+.*?(\d+(?:\.\d+)?)\s*%")
# espota (OTA) : "Uploading: [=====     ] 52%"
_OTA = re.compile(r"^\s*Uploading:\s*\[[^\]]*\]\s*(\d+(?:\.\d+)?)\s*%")
_ENVOI = re.compile(r"^\s*(Uploading\s+\S|Looking for upload port|Auto-detected:|Configuring upload protocol)")
_FS = re.compile(r"Nous allons créer le système de fichiers|Building FS image|mklittlefs|Creating filesystem")
_FS_AUSSI = re.compile(r"Utilisera une commande de téléchargement personnalisée")
_RESULTAT = re.compile(r"\[(SUCCESS|FAILED)\]")
_ERREUR = re.compile(r"error:|Error|FAILED")


def retire_ansi(texte):
    """Texte sans les codes de couleur / de curseur ANSI."""
    return _ANSI.sub("", texte)


class Suivi:
    """Etat d'un `pio run` en cours. `ligne()` renvoie un evenement quand l'etat change, sinon None."""

    def __init__(self, action, reference_o=None):
        if action not in ACTIONS:
            raise ValueError(f"action inconnue : {action!r}")
        self.action = action
        self.reference_o = reference_o if reference_o and reference_o > 0 else None
        self.nb_o = 0
        self.resultat = None
        self.extrait_erreur = []
        self.fs_aussi = False
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
        if _COMPILE.match(t):
            self.nb_o += 1
            if self.reference_o:
                return self._evenement(ETAPE_COMPILATION, self.nb_o * 100 // self.reference_o,
                                       f"{self.nb_o}/{self.reference_o} fichiers")
            return self._evenement(ETAPE_COMPILATION, None, f"{self.nb_o} fichiers")
        if _LIENS.match(t):
            return self._evenement(ETAPE_LIENS, None, "")
        m = _ESPTOOL.search(t) or _OTA.match(t)
        if m:
            return self._evenement(ETAPE_ENVOI, float(m.group(1)), "")
        if _ENVOI.match(t):
            return self._evenement(ETAPE_ENVOI, None, "")
        if _FS.search(t):
            return self._evenement(ETAPE_FS, None, "")
        return None
