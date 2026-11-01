"""Faut-il incrementer CFG_HOLDER avant ce `pio run` ? (plan tasks/plans/temps-compilation.md, A1, 2026-11-01)

Avant : le pre-script incrementait CFG_HOLDER a CHAQUE `pio run`. user_config_override.h changeait donc a chaque fois,
et tasmota.ino.cpp (~7,6 Mo, un seul coeur) n'etait jamais repris du cache objet (`build_cache_dir`) : 655 s pour
ce seul fichier sur la cuve le 2026-10-31, meme quand seul le Berry avait change.

Regle decidee par l'utilisateur : incrementer seulement si, depuis le dernier increment de CET env,
  - user_config_override.h a change (la ligne `#define CFG_HOLDER` exclue : sinon chaque increment en appellerait un autre),
  - ou le `_persist.json` de l'env a change ;
et seulement pour un `pio run` qui construit le firmware (aucune cible, upload, erase_upload) : jamais pour un
`nobuild upload`, un buildfs ou un uploadfs seuls.

Etat par env dans %LOCALAPPDATA%\\outils_tasmota\\build\\cfg_holder.json, HORS depot (propre a ce PC) ; absent ou
illisible = increment (comportement d'avant). Banc : test_cfg_holder.py.
"""
import hashlib
import json
import os
import re
from pathlib import Path

FICHIER_ETAT = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "outils_tasmota" / "build" / "cfg_holder.json"
CIBLES_FIRMWARE = {"upload", "erase_upload", "buildprog"}
LIGNE_CFG_HOLDER = re.compile(r"^\s*#define\s+CFG_HOLDER\b")


def construit_firmware(cibles):
    """Vrai si ce `pio run` compile le firmware : aucune cible, ou une cible d'envoi du firmware sans `nobuild`."""
    cibles = set(cibles)
    if "nobuild" in cibles:
        return False
    return not cibles or bool(cibles & CIBLES_FIRMWARE)


def _empreinte(chemin, sans_cfg_holder=False):
    """sha1 du fichier (fins de ligne normalisees : le pre-script le reecrit en mode texte), "" s'il est absent."""
    try:
        texte = Path(chemin).read_bytes().replace(b"\r\n", b"\n")
    except OSError:
        return ""
    if sans_cfg_holder:
        texte = b"\n".join(l for l in texte.split(b"\n") if not LIGNE_CFG_HOLDER.match(l.decode("utf-8", "replace")))
    return hashlib.sha1(texte).hexdigest()


def empreintes(chemin_h, chemin_persist):
    return {"h": _empreinte(chemin_h, sans_cfg_holder=True), "persist": _empreinte(chemin_persist)}


def _lit_etat(fichier):
    try:
        etat = json.loads(Path(fichier).read_text(encoding="utf-8"))
        return etat if isinstance(etat, dict) else {}
    except (OSError, ValueError):
        return {}


def doit_incrementer(env, chemin_h, chemin_persist, fichier=FICHIER_ETAT):
    """(oui, motif) : motif lisible, affiche par le pre-script dans la sortie du build."""
    actuel = empreintes(chemin_h, chemin_persist)
    connu = _lit_etat(fichier).get(env)
    if not isinstance(connu, dict):
        return True, "premier build connu de cet env"
    changes = [nom for nom, cle in (("user_config_override.h", "h"), ("_persist.json", "persist"))
               if connu.get(cle) != actuel[cle]]
    if changes:
        return True, " et ".join(changes) + " modifie(s) depuis le dernier increment"
    return False, "ni user_config_override.h ni _persist.json n'ont change"


def enregistre(env, chemin_h, chemin_persist, fichier=FICHIER_ETAT):
    """Memorise les empreintes de l'env, APRES l'increment ; un echec d'ecriture vaut un increment au prochain build."""
    etat = _lit_etat(fichier)
    etat[env] = empreintes(chemin_h, chemin_persist)
    try:
        Path(fichier).parent.mkdir(parents=True, exist_ok=True)
        temporaire = Path(str(fichier) + ".tmp")
        temporaire.write_text(json.dumps(etat, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(temporaire, fichier)
    except OSError:
        pass
