"""Faut-il incrementer CFG_HOLDER avant ce `pio run` ? (plan tasks/plans/temps-compilation.md, A1, 2026-11-01)

Avant : le pre-script incrementait CFG_HOLDER a CHAQUE `pio run`. user_config_override.h changeait donc a chaque fois,
et tasmota.ino.cpp n'etait jamais repris du cache objet (`build_cache_dir`), ni tout Berry : berry_conf.h inclut
my_user_config.h, donc ce .h. Mesure sur la cuve le 2026-11-01 : 175 fichiers recompiles a chaque increment.

Regle decidee par l'utilisateur : incrementer seulement si user_config_override.h a change depuis le dernier increment
(la ligne `#define CFG_HOLDER` exclue : sinon chaque increment en appellerait un autre), et seulement pour un `pio run`
qui construit le firmware (aucune cible, upload, erase_upload) : jamais pour un `nobuild upload`, un buildfs ou un
uploadfs seuls. Le _persist.json n'entre pas dans la regle : il part avec le FS et ne passe pas par SECTION1.

CFG_HOLDER et ce .h sont communs a tous les envs : l'etat aussi, sinon chaque env incrementerait a son tour et
invaliderait le cache des autres. Il vit dans %LOCALAPPDATA%\\outils_tasmota\\build\\cfg_holder.json, HORS depot
(propre a ce PC) ; absent ou illisible = increment (comportement d'avant). Banc : test_cfg_holder.py.
"""
import hashlib
import json
import os
import re
from pathlib import Path

FICHIER_ETAT = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "outils_tasmota" / "build" / "cfg_holder.json"
CIBLES_FIRMWARE = {"upload", "erase_upload", "buildprog"}
LIGNE_CFG_HOLDER = re.compile(rb"^\s*#define\s+CFG_HOLDER\b")


def construit_firmware(cibles):
    """Vrai si ce `pio run` compile le firmware : aucune cible, ou une cible d'envoi du firmware sans `nobuild`."""
    cibles = set(cibles)
    if "nobuild" in cibles:
        return False
    return not cibles or bool(cibles & CIBLES_FIRMWARE)


def empreinte(chemin_h):
    """sha1 du .h sans la ligne CFG_HOLDER (fins de ligne normalisees : le pre-script le reecrit en mode texte)."""
    try:
        texte = Path(chemin_h).read_bytes().replace(b"\r\n", b"\n")
    except OSError:
        return ""
    return hashlib.sha1(b"\n".join(l for l in texte.split(b"\n") if not LIGNE_CFG_HOLDER.match(l))).hexdigest()


def _lit_etat(fichier):
    try:
        etat = json.loads(Path(fichier).read_text(encoding="utf-8"))
        return etat if isinstance(etat, dict) else {}
    except (OSError, ValueError):
        return {}


def doit_incrementer(chemin_h, fichier=FICHIER_ETAT):
    """(oui, motif) : motif lisible, affiche par le pre-script dans la sortie du build."""
    connu = _lit_etat(fichier).get("h")
    if connu is None:
        return True, "premier build connu"
    if connu != empreinte(chemin_h):
        return True, "user_config_override.h modifie depuis le dernier increment"
    return False, "user_config_override.h n'a pas change"


def enregistre(chemin_h, fichier=FICHIER_ETAT):
    """Memorise l'empreinte du .h, APRES l'increment ; un echec d'ecriture vaut un increment au prochain build."""
    try:
        Path(fichier).parent.mkdir(parents=True, exist_ok=True)
        temporaire = Path(str(fichier) + ".tmp")
        temporaire.write_text(json.dumps({"h": empreinte(chemin_h)}), encoding="utf-8")
        os.replace(temporaire, fichier)
    except OSError:
        pass
