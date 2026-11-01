"""Faut-il incrementer CFG_HOLDER avant ce `pio run` ? (plan tasks/plans/temps-compilation.md, A1, 2026-11-01)

Avant : le pre-script incrementait CFG_HOLDER a CHAQUE `pio run`. user_config_override.h changeait donc a chaque fois,
et tasmota.ino.cpp n'etait jamais repris du cache objet (`build_cache_dir`), ni tout Berry : berry_conf.h inclut
my_user_config.h, donc ce .h. Mesure sur la cuve le 2026-11-01 : 175 fichiers recompiles a chaque increment.

Regle decidee par l'utilisateur : incrementer seulement si user_config_override.h a change depuis le dernier increment
(la ligne `#define CFG_HOLDER` exclue : sinon chaque increment en appellerait un autre), et seulement pour un `pio run`
qui construit le firmware (aucune cible, upload, erase_upload) : jamais pour un `nobuild upload`, un buildfs ou un
uploadfs seuls. Le _persist.json n'entre pas dans la regle : il part avec le FS et ne passe pas par SECTION1.

Par env depuis le 2026-11-01 (soir) : une carte qui a sa section `#elif defined(FIRMWARE_...)` dans le .h y porte SON
CFG_HOLDER (`incremente_section`, lignes posees au premier increment), et son empreinte ne compte que la partie commune
du .h et SA section. Modifier la section d'une carte ne recharge donc plus SECTION1 sur les autres (elles recompilent
quand meme : le fichier a change). Sans section (envs amont, bases) : la ligne commune, comme avant. Etat par env dans
%LOCALAPPDATA%\\outils_tasmota\\build\\cfg_holder.json, HORS depot ; absent ou illisible = increment. Banc :
test_cfg_holder.py.
"""
import hashlib
import json
import os
import re
from pathlib import Path

FICHIER_ETAT = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "outils_tasmota" / "build" / "cfg_holder.json"
CIBLES_FIRMWARE = {"upload", "erase_upload", "buildprog"}
LIGNE_CFG_HOLDER = re.compile(rb"^\s*#(define|undef)\s+CFG_HOLDER\b")


def construit_firmware(cibles):
    """Vrai si ce `pio run` compile le firmware : aucune cible, ou une cible d'envoi du firmware sans `nobuild`."""
    cibles = set(cibles)
    if "nobuild" in cibles:
        return False
    return not cibles or bool(cibles & CIBLES_FIRMWARE)


TETE_SECTION = re.compile(rb"^ {8}#(el)?if\b.*\bdefined\(FIRMWARE_")      # chaine des firmwares du .h
FIN_SECTION = re.compile(rb"^ {8}#(elif|else|endif)\b")
DEFINI = re.compile(rb"defined\((\w+)\)")
VALEUR = re.compile(rb"#define\s+CFG_HOLDER\s+(\d+)")


def defines(build_flags):
    """Noms des -D d'une liste de build_flags (« -DX », « -D X=1 »)."""
    return set(re.findall(r"-D\s*(\w+)", " ".join(build_flags)))


def sections(lignes):
    """[(debut, fin exclue, {defines du titre})] des sections par carte de la chaine #if defined(FIRMWARE_...)."""
    res, ouverte = [], None
    for i, l in enumerate(lignes):
        if ouverte and FIN_SECTION.match(l):
            res.append((ouverte[0], i, ouverte[1]))
            ouverte = None
        if TETE_SECTION.match(l):
            ouverte = (i, {d.decode() for d in DEFINI.findall(l)})
    return res


def _section(lignes, noms):
    return next(((d, f) for d, f, titre in sections(lignes) if titre & set(noms)), None)


def empreinte(chemin_h, noms=()):
    """sha1 de la partie commune du .h et de la section de l'env (`noms` : ses defines), lignes CFG_HOLDER exclues
    (fins de ligne normalisees : le pre-script reecrit le .h en mode texte)."""
    try:
        lignes = Path(chemin_h).read_bytes().replace(b"\r\n", b"\n").split(b"\n")
    except OSError:
        return ""
    sienne = _section(lignes, noms)
    autres = {i for d, f, _ in sections(lignes) if (d, f) != sienne for i in range(d, f)}
    return hashlib.sha1(b"\n".join(l for i, l in enumerate(lignes)
                                   if i not in autres and not LIGNE_CFG_HOLDER.match(l))).hexdigest()


def _empreinte_commune(chemin_h):
    """Empreinte de l'ancien etat commun (avant le CFG_HOLDER par env) : tout le .h sans les lignes `#define CFG_HOLDER`."""
    try:
        texte = Path(chemin_h).read_bytes().replace(b"\r\n", b"\n")
    except OSError:
        return ""
    return hashlib.sha1(b"\n".join(l for l in texte.split(b"\n") if not re.match(rb"^\s*#define\s+CFG_HOLDER\b", l))).hexdigest()


def incremente_section(chemin_h, noms):
    """CFG_HOLDER de la section de l'env + 1 (lignes posees au premier appel) -> (avant, apres) ; None sans section."""
    brut = Path(chemin_h).read_bytes()
    nl = b"\r\n" if b"\r\n" in brut else b"\n"
    lignes = brut.replace(b"\r\n", b"\n").split(b"\n")
    sienne = _section(lignes, noms)
    if not sienne:
        return None
    debut, fin = sienne
    ici = next((i for i in range(debut, fin) if VALEUR.search(lignes[i])), None)
    commun = next((int(m.group(1)) for l in lignes if (m := VALEUR.search(l))), 0)
    avant = int(VALEUR.search(lignes[ici]).group(1)) if ici is not None else commun
    apres = 1 if avant >= 65535 else avant + 1                     # uint16 : rebouclage, comme la ligne commune
    ligne = f"            #define CFG_HOLDER  {apres}    // propre a cet env, incremente par le pre-script (cfg_holder.py)".encode()
    if ici is None:
        lignes[debut + 1:debut + 1] = [b"            #undef CFG_HOLDER", ligne]
    else:
        lignes[ici] = ligne
    Path(chemin_h).write_bytes(nl.join(lignes))
    return avant, apres


def _lit_etat(fichier):
    try:
        etat = json.loads(Path(fichier).read_text(encoding="utf-8"))
        return etat if isinstance(etat, dict) else {}
    except (OSError, ValueError):
        return {}


def doit_incrementer(chemin_h, env, noms=(), fichier=FICHIER_ETAT):
    """(oui, motif) : motif lisible, affiche par le pre-script dans la sortie du build."""
    etat = _lit_etat(fichier)
    connus = etat.get("envs")
    connu = connus.get(env) if isinstance(connus, dict) else None
    if connu is None and etat.get("h") and etat["h"] == _empreinte_commune(chemin_h):
        enregistre(chemin_h, env, noms, fichier)               # ancien etat commun, .h inchange depuis : repris tel quel
        return False, "user_config_override.h n'a pas change depuis le dernier increment (etat commun repris pour cet env)"
    if connu is None:
        return True, "premier build connu de cet env"
    if connu != empreinte(chemin_h, noms):
        return True, "user_config_override.h modifie (partie commune ou section de cet env) depuis son dernier increment"
    return False, "ni la partie commune de user_config_override.h ni la section de cet env n'ont change"


def enregistre(chemin_h, env, noms=(), fichier=FICHIER_ETAT):
    """Memorise l'empreinte de l'env, APRES l'increment ; un echec d'ecriture vaut un increment au prochain build."""
    try:
        Path(fichier).parent.mkdir(parents=True, exist_ok=True)
        etat = _lit_etat(fichier)
        envs = etat.get("envs") if isinstance(etat.get("envs"), dict) else {}
        envs[env] = empreinte(chemin_h, noms)
        etat["envs"] = envs                                       # "h" (ancien etat commun) garde pour les envs non repris
        temporaire = Path(str(fichier) + ".tmp")
        temporaire.write_text(json.dumps(etat), encoding="utf-8")
        os.replace(temporaire, fichier)
    except OSError:
        pass
