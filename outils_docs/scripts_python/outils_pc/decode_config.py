"""decode-config (tasmota/decode-config, LGPL-3.0) pour l'onglet « Sauvegarde configuration » de la page build.

decode-config lit un .dmp (/dl d'une carte : Settings + fichiers .drvset*) en JSON et ecrit un nouveau .dmp a partir
d'un JSON partiel. Il vit dans un environnement Python dedie, HORS du Python de PlatformIO (configargparse et paho-mqtt
y manquent) et hors du depot : %LOCALAPPDATA%\\outils_tasmota\\decode_config\\venv, version epinglee.

  python decode_config.py              installe si besoin
  python decode_config.py --verifier   code 0 si utilisable, 1 sinon

Deux defauts de decode-config 16.0.0.0, mesures le 2026-11-03, d'ou les gardes :
- ecrire un texte commun ESP8266/ESP32 (hostname, button_text...) tronque la reserve de textes au SET_MAX de l'ESP8266 :
  sur un ESP32, tout ce qui suit (textes d'interrupteurs 9-28, Range Extender, InfluxDB...) est perdu. Les textes sont
  donc ecrits ici, a leur indice ESP32 (`_pose_textes`), decode-config ne recoit que les autres cles ;
- il ignore SET_APBSSID1/2 (fin de la reserve depuis Tasmota 15.5) : ces textes bruts doivent rester identiques.
Apres chaque ecriture, la copie est relue et comparee a l'attendu : un ecart et rien n'est garde.
"""

import functools
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

VERSION_PAQUET = "16.0.0.0"
DOSSIER = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "outils_tasmota" / "decode_config"
PYTHON = DOSSIER / "venv" / "Scripts" / "python.exe"
SCRIPT = DOSSIER / "venv" / "Scripts" / "decode-config.py"
GROUPES = Path(__file__).with_name("decode_config_groupes.py")
VERSION_CONNUE = 0x10000000          # derniere disposition de Settings connue du paquet
# Plus recentes : seulement si leur Settings a ete compare (tasmota_types.h et enum SettingsTextIndex de tasmota.h)
VERSIONS_VERIFIEES = {0x10000002: "Settings identique a 16.0.0.0 hors SET_APBSSID1/2, vu le 2026-11-03"}
TEXTES_CONNUS = 126                  # textes de la reserve connus du paquet ; au-dela, SET_APBSSID1/2
SET_MAX = 128                        # SettingsTextIndex ESP32 de tasmota.h (banc : test_build_sauvegarde.py)
XOR = 0x5A                           # CONFIG_FILE_XOR
NON_COMPARES = ("header", "cfg_crc32", "cfg_crc", "cfg_timestamp", "save_flag")


def _xor(donnees):
    """settings.ino::SettingsBufferXor sur le fichier entier (son propre inverse) -> (octets, debut de Settings)."""
    d = bytearray(donnees)
    multi = d[:10] == b"/.settings"
    for i in range(18 if multi else 2, len(d)):
        d[i] ^= (XOR + i) & 0xFF
    return d, 16 if multi else 0


def settings(donnees):
    """Settings (4 096 o) en clair d'un .dmp, en-tete /.settings retire."""
    d, debut = _xor(donnees)
    return bytes(d[debut:debut + 4096])


def crc_valide(donnees):
    """Vrai si les Settings du .dmp portent leur CRC32 (settings.ino::GetCfgCrc32) : un .dmp et non une page web."""
    s = settings(donnees)
    return len(s) == 4096 and struct.unpack_from("<I", s, 0xFFC)[0] == zlib.crc32(s[:4092], 0xFFFFFFFF)


def version(donnees):
    return int.from_bytes(settings(donnees)[8:12], "little")


def nom_version(v):
    return f"{v >> 24}.{(v >> 16) & 0xFF}.{(v >> 8) & 0xFF}.{v & 0xFF}"


def editable(v):
    return v <= VERSION_CONNUE or v in VERSIONS_VERIFIEES


def textes_bruts(donnees):
    """Textes de la reserve, sans les entrees vides de la fin (leur nombre suit la longueur des autres)."""
    return settings(donnees)[0x17:0x17 + 699].rstrip(b"\0").split(b"\0")


def utilisable():
    return PYTHON.exists() and SCRIPT.exists() and subprocess.run(
        [str(PYTHON), "-c", "import configargparse, requests"], capture_output=True).returncode == 0


def installe():
    if utilisable():
        return
    DOSSIER.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "venv", str(DOSSIER / "venv")], check=True)
    subprocess.run([str(PYTHON), "-m", "pip", "install", "-q", f"decode-config=={VERSION_PAQUET}"], check=True)


def _lance(*args):
    try:
        r = subprocess.run([str(PYTHON), str(SCRIPT), *map(str, args)], capture_output=True, timeout=120,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    except (OSError, subprocess.TimeoutExpired) as erreur:
        raise RuntimeError(f"decode-config : {erreur}") from None
    if r.returncode not in (0, 1):   # 1 = restauration sautee, donnees inchangees
        lignes = r.stderr.decode("utf-8", "replace").strip().splitlines() or [f"code {r.returncode}"]
        raise RuntimeError(f"decode-config : {lignes[-1]}")
    return r.stdout.decode("utf-8")


def decode(chemin):
    """Parametres d'un .dmp (dict) ; ValueError si sa version n'est pas lisible sans risque."""
    v = version(Path(chemin).read_bytes())
    if not editable(v):
        raise ValueError(f"version {nom_version(v)} non vérifiée : sauvegarde restaurable, mais pas lisible ni éditable")
    return json.loads(_lance("-s", chemin, "-w"))


@functools.cache
def disposition():
    """{groupes: {cle: groupe}, textes: {cle: [indice, nombre]}, noms: [...]} (decode_config_groupes.py)."""
    try:
        r = subprocess.run([str(PYTHON), "-I", str(GROUPES), str(SCRIPT)], capture_output=True, check=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as erreur:
        raise RuntimeError(f"decode-config : disposition illisible ({erreur})") from None
    return json.loads(r.stdout)


def groupes():
    """{cle: groupe decode-config} (Wifi, Mqtt, Timer, Management...) : themes de la page."""
    return disposition()["groupes"]


def _pose_textes(chemin, textes):
    """Ecrit {cle: valeur} dans la reserve de textes du .dmp, a l'indice ESP32, puis CRC16 et CRC32."""
    d, debut = _xor(Path(chemin).read_bytes())
    s = d[debut:debut + 4096]
    reserve = bytes(s[0x17:0x17 + 699]).rstrip(b"\0").split(b"\0")
    reserve += [b""] * (SET_MAX - len(reserve))
    for cle, valeur in textes.items():
        indice, nombre = disposition()["textes"][cle]
        valeurs = valeur if nombre else [valeur]
        if not isinstance(valeurs, list) or len(valeurs) > (nombre or 1) or not all(isinstance(v, str) for v in valeurs):
            raise ValueError(f"{cle} : {'liste de ' + str(nombre) + ' textes' if nombre else 'texte'} attendu")
        for i, v in enumerate(valeurs):
            if "\0" in v:
                raise ValueError(f"{cle} : caractère nul interdit")
            reserve[indice + i] = v.encode("utf-8")
    texte = b"\0".join(reserve)
    if len(texte) + 1 > 699:
        raise ValueError(f"réserve de textes pleine ({len(texte) + 1} o sur 699)")
    s[0x17:0x17 + 699] = texte.ljust(699, b"\0")
    struct.pack_into("<H", s, 14, sum(s[i] * (i + 1) for i in range(3584) if i not in (14, 15)) & 0xFFFF)  # GetCfgCrc16
    struct.pack_into("<I", s, 0xFFC, zlib.crc32(bytes(s[:4092]), 0xFFFFFFFF))     # GetCfgCrc32 (depart a 0)
    d[debut:debut + 4096] = s
    Path(chemin).write_bytes(bytes(_xor(bytes(d))[0]))


def ecrit_copie(source, dest, modifs):
    """Ecrit dest = source + modifs (cles de decode()) et le relit ; rien n'est garde si le resultat s'ecarte."""
    source, dest = Path(source), Path(dest)
    avant = decode(source)
    inconnues = sorted(set(modifs) - set(avant))
    if inconnues:
        raise ValueError(f"paramètres inconnus : {', '.join(inconnues)}")
    for k, v in list(modifs.items()):
        nombre = (disposition()["textes"].get(k) or [0, None])[1]
        if nombre and isinstance(v, str) and isinstance(avant.get(k), list):
            modifs[k] = [v] + avant[k][1:]
    textes = {k: v for k, v in modifs.items() if k in disposition()["textes"]}
    autres = {k: v for k, v in modifs.items() if k not in textes}
    shutil.copyfile(source, dest)
    try:
        if autres:
            with tempfile.TemporaryDirectory() as t:
                partiel = Path(t) / "modifs.json"
                partiel.write_text(json.dumps({"header": avant["header"], "config_version": avant["config_version"],
                                               **autres}), encoding="utf-8")
                _lance("-s", dest, "-i", partiel, "-w")
        if textes:
            _pose_textes(dest, textes)
        apres = decode(dest)
        attendu = {**avant, **modifs}
        ecarts = [k for k in set(attendu) | set(apres) if k not in NON_COMPARES and attendu.get(k) != apres.get(k)]
        if textes_bruts(source.read_bytes())[TEXTES_CONNUS:] != textes_bruts(dest.read_bytes())[TEXTES_CONNUS:]:
            ecarts.append("textes inconnus de decode-config (SET_APBSSID1/2)")
        if ecarts:
            raise RuntimeError(f"copie refusée, la relecture s'écarte de l'attendu : {', '.join(sorted(ecarts))}")
        return apres
    except BaseException:
        dest.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    if "--verifier" in sys.argv:
        print("decode-config utilisable" if utilisable() else f"decode-config absent : lancer {Path(__file__).name}")
        sys.exit(0 if utilisable() else 1)
    installe()
    print(f"decode-config {VERSION_PAQUET} : {SCRIPT}")
