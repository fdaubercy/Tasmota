"""Filtre du moniteur serie PlatformIO : colore les logs Tasmota / Berry.

Activation dans un environnement (platformio_tasmota_cenv.ini) :
    monitor_filters = esp32_exception_decoder, couleurs_tasmota
Ordre voulu : le decodeur d'exceptions lit les lignes BRUTES (les codes couleur
casseraient sa detection de 'Backtrace:'), la couleur est posee apres.

Tasmota n'ecrit PAS le niveau de log dans la ligne : la gravite est deduite du
contenu (erreur / alerte / succes / bruit). Le prefixe d'un module Berry
(CONTROLE_GENERAL:, GLOBAL_CHGT_...:) prend la couleur de sa famille (1er mot).
"""

import hashlib
import os
import re

try:
    from platformio.public import DeviceMonitorFilterBase
except ImportError:  # importe hors PlatformIO (pont_serie.py) : seules les regles servent
    DeviceMonitorFilterBase = None

RAZ = "\x1b[0m"
GRAS = "\x1b[1m"
ESTOMPE = "\x1b[2m"
ROUGE = "\x1b[91m"
JAUNE = "\x1b[93m"
VERT = "\x1b[92m"
GRIS = "\x1b[90m"

# Gravite deduite du contenu, testee dans cet ordre (la premiere qui correspond gagne).
MOTIFS_GRAVITE = [
    (GRAS + ROUGE, re.compile(
        r"Guru Meditation|abort\(\)|Backtrace:|panic|Exception>|stack traceback|"
        r"LoadProhibited|StoreProhibited|_ERREUR|\bERROR\b|[EÉ]chec|rst:0x(?!1\b)|assert failed",
        re.IGNORECASE)),
    (JAUNE, re.compile(
        r"timeout|denied|not found|bad json|undeclared|Tentative de connexion|"
        r"Nouvelle tentative|settings have been reset|Red[ée]marre|No '", re.IGNORECASE)),
    (GRIS + ESTOMPE, re.compile(r"BRY: GC from|DHT: Pin\d+ (cycles|timeout)")),
    (VERT, re.compile(
        r"Connect[ée]\b|Successfully loaded|FTP Server started|Web server active|Synced by NTP")),
]

# Familles de modules Berry -> couleur fixe (le reste : couleur stable par hachage).
COULEURS_FAMILLES = {
    "CONTROLE": "\x1b[96m",    # cyan
    "GLOBAL": "\x1b[95m",      # magenta
    "CONFIG": "\x1b[94m",      # bleu
    "WEBSERVER": "\x1b[36m",   # cyan fonce
    "MODBUS": "\x1b[33m",      # jaune fonce
    "UDP": "\x1b[35m",         # magenta fonce
    "TCP": "\x1b[35m",
    "RECUP": "\x1b[34m",       # bleu fonce
    "STAT": "\x1b[32m",        # vert fonce
}
PALETTE_SECOURS = ["\x1b[96m", "\x1b[95m", "\x1b[94m", "\x1b[36m", "\x1b[33m", "\x1b[35m", "\x1b[32m"]

# "HH:MM:SS.mmm PREFIXE: reste" (horodatage optionnel : lignes du bootloader, traceback)
LIGNE = re.compile(r"^(\d{2}:\d{2}:\d{2}\.\d{3} )?([A-Z][A-Z0-9_]*:)?(.*)$", re.DOTALL)


def active_vt_windows():
    """Active l'interpretation des sequences ANSI dans une console Windows classique."""
    if os.name != "nt":
        return
    try:
        import ctypes
        noyau = ctypes.windll.kernel32
        poignee = noyau.GetStdHandle(-11)          # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if noyau.GetConsoleMode(poignee, ctypes.byref(mode)):
            noyau.SetConsoleMode(poignee, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:  # pas de console (terminal VS Code) : les couleurs y marchent deja
        pass


def couleur_famille(prefixe):
    famille = prefixe.rstrip(":").split("_")[0]
    if famille in COULEURS_FAMILLES:
        return COULEURS_FAMILLES[famille]
    indice = int(hashlib.md5(famille.encode()).hexdigest(), 16) % len(PALETTE_SECOURS)
    return PALETTE_SECOURS[indice]


def colore_ligne(ligne, dans_traceback):
    """Renvoie (ligne coloree, dans_traceback mis a jour)."""
    horodatage, prefixe, reste = LIGNE.match(ligne).groups()
    sortie = GRIS + horodatage + RAZ if horodatage else ""
    # Suite d'un 'stack traceback:' Berry : "HH:MM:SS.mmm \t<unknown source>: in function ..."
    suite_traceback = not prefixe and reste.startswith("\t")
    if dans_traceback and suite_traceback:
        return sortie + ROUGE + reste + RAZ, True
    gravite = next((c for c, motif in MOTIFS_GRAVITE if motif.search(ligne)), "")
    if prefixe:
        # Prefixe court (WIF:, MQT:, BRY:...) = coeur Tasmota, laisse neutre ;
        # prefixe long ou compose = module Berry, colore par famille.
        berry = len(prefixe) > 4 or "_" in prefixe
        sortie += (GRAS + couleur_famille(prefixe) + prefixe + RAZ) if berry else prefixe
    sortie += (gravite + reste + RAZ) if gravite else reste
    return sortie, "stack traceback" in ligne


class Coloriseur:
    """Colore un flux livre par morceaux arbitraires : seules les lignes COMPLETES sont
    colorees, la fin incomplete attend le morceau suivant."""

    def __init__(self):
        self.tampon = ""
        self.dans_traceback = False

    def morceau(self, text):
        self.tampon += text
        if "\n" not in self.tampon:
            return ""
        lignes = self.tampon.split("\n")
        self.tampon = lignes.pop()
        sortie = []
        for ligne in lignes:
            fin = "\r" if ligne.endswith("\r") else ""
            texte, self.dans_traceback = colore_ligne(ligne.rstrip("\r"), self.dans_traceback)
            sortie.append(texte + fin)
        return "\n".join(sortie) + "\n"


if DeviceMonitorFilterBase is not None:

    class CouleursTasmota(DeviceMonitorFilterBase):
        NAME = "couleurs_tasmota"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.coloriseur = Coloriseur()
            active_vt_windows()

        def rx(self, text):
            return self.coloriseur.morceau(text)

        def tx(self, text):
            return text
