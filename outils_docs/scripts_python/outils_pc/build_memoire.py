"""Occupation de la memoire d'un env, selon les capacites parametrees (plan temps-compilation, A7, 2026-11-01).

Rien n'est compile ni televerse : on relit ce que le dernier build a laisse.
  - table des partitions : le CSV de l'env (`board_build.partitions`, sinon celui de son board, `boards/<board>.json`) ;
  - `app0` : ligne « Flash: [...] (used N bytes ...) » du dernier journal de compilation reussie, sinon firmware.bin ;
  - `safeboot` : le binaire joint a l'upload (ligne « 0x10000 | ...safeboot.bin » du journal), sinon variants/tasmota/ ;
  - FS : fichiers de `.pio/build/<env>/littlefs_data` (ceux que post_esp32.py met dans l'image), arrondis au bloc ;
  - RAM : tableau « Memory Type Usage Summary » du journal (DIRAM, IRAM, RTC, LP...), ligne « RAM: [...] » en secours.
Le resultat est enregistre dans <dossier>/memoire/<env>.json avec sa date : .pio/build est purge a chaque changement
d'env, et une compilation sans changement ne reaffiche pas toujours le tableau memoire. `resume` : app0, FS et DIRAM de
chaque analyse enregistree, pour la liste des envs. `lit_carte` : FS reel, tas et PSRAM, lus sur la carte (A7), jamais
enregistres. Banc : test_build_memoire.py.
"""

import http.client
import json
import re
import time
from pathlib import Path

import build_envs
from build_ota_http import _commande
from build_ota_maitre import joint_par_maitre

DELAI_CARTE = 5.0
BLOC_FS = 4096
_TAILLE = re.compile(r"^(0x[0-9a-fA-F]+|\d+)([KkMm]?)$")
_FLASH = re.compile(r"^Flash:\s*\[[^\]]*\]\s*[\d.]+%\s*\(used (\d+) bytes from (\d+) bytes\)", re.M)
_RAM = re.compile(r"^RAM:\s*\[[^\]]*\]\s*[\d.]+%\s*\(used (\d+) bytes from (\d+) bytes\)", re.M)
_LIGNE_TABLE = re.compile(r"^│\s(\S.*?)\s*│\s*(\d+)\s*│\s*[\d.]*\s*│\s*(\d*)\s*│\s*(\d*)\s*│", re.M)
_SAFEBOOT = re.compile(r"^\s*-\s*0x10000\s*\|\s*(\S.*safeboot[^\s]*\.bin)\s*$", re.M)
_TAILLE_FLASH = re.compile(r"^(\d+)\s*MB$", re.I)


def taille(texte):
    """Taille d'une colonne de CSV de partitions en octets (0x..., decimal, suffixe K ou M) ; None si illisible."""
    m = _TAILLE.match(texte.strip())
    if not m:
        return None
    n = int(m.group(1), 0)
    return n * {"": 1, "k": 1024, "m": 1024 * 1024}[m.group(2).lower()]


def lit_csv(texte):
    """[{nom, type, sous_type, debut, taille}] ; une colonne Offset vide est calculee comme gen_esp32part.py."""
    parts, suivant = [], 0x9000
    for ligne in texte.splitlines():
        ligne = ligne.split("#", 1)[0].strip()
        if not ligne:
            continue
        cols = [c.strip() for c in ligne.split(",")]
        if len(cols) < 5:
            continue
        sz = taille(cols[4])
        if sz is None:
            raise ValueError(f"taille illisible : {ligne!r}")
        debut = taille(cols[3]) if cols[3] else None
        if debut is None:
            alignement = 0x10000 if cols[1] == "app" else 0x1000
            debut = -(-suivant // alignement) * alignement
        parts.append({"nom": cols[0], "type": cols[1], "sous_type": cols[2], "debut": debut, "taille": sz})
        suivant = debut + sz
    return parts


def lit_table_memoire(texte):
    """Zones de premier niveau du tableau de pioarduino : [{zone, utilise, total}] (lignes sans total ignorees)."""
    # l'expression exclut deja l'en-tete et les sous-sections indentees ; les zones sans total (Flash Code) sont ecartees
    return [{"zone": m.group(1), "utilise": int(m.group(2)), "total": int(m.group(4))}
            for m in _LIGNE_TABLE.finditer(texte) if m.group(4)]


def _options(racine, env):
    toutes, _ = build_envs._sections(Path(racine))
    if f"env:{env}" not in toutes:
        raise LookupError(f"environnement inconnu : {env!r}")
    return lambda option: build_envs._valeur(toutes, f"env:{env}", option).strip()


def _board(racine, nom):
    chemin = Path(racine) / "boards" / f"{nom}.json"
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def journal_compilation(journaux, env):
    """Dernier journal REUSSI de cet env qui contient le bilan memoire (une compilation, ou un upload qui a compile)."""
    candidats = sorted(Path(journaux).glob(f"*-{env}-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    for chemin in candidats:
        texte = chemin.read_text(encoding="utf-8", errors="replace")
        if _FLASH.search(texte) and "[SUCCESS]" in texte:
            return chemin, texte
    return None, ""


def _fs_utilise(dossier):
    """Octets occupes dans le FS d'apres les fichiers de littlefs_data, chacun arrondi au bloc ; None si absent.

    shortcut: estimation (metadonnees de LittleFS ignorees, fichiers ecrits par la carte depuis le flash inconnus) ;
    la valeur reelle se lit sur la carte (UfsSize / UfsFree). Controle du 2026-11-01 sur la cuve : 100 Ko estimes,
    27 blocs (108 Ko) occupes dans le vrai littlefs.bin, memes 6 fichiers.
    """
    dossier = Path(dossier)
    if not dossier.is_dir():
        return None
    return sum(-(-f.stat().st_size // BLOC_FS) * BLOC_FS for f in dossier.rglob("*") if f.is_file())


def analyse(racine, env, journaux):
    """Etat memoire de l'env (voir la docstring du module). LookupError : env inconnu ; ValueError : CSV illisible."""
    racine = Path(racine)
    opt = _options(racine, env)
    board = _board(racine, opt("board"))
    csv = opt("board_build.partitions") or board.get("build", {}).get("partitions", "")
    flash = opt("board_upload.flash_size") or board.get("upload", {}).get("flash_size", "")
    m = _TAILLE_FLASH.match(flash)
    res = {"env": env, "date": time.time(), "csv": csv, "flash": int(m.group(1)) * 1024 * 1024 if m else None,
           "partitions": [], "ram": [], "journal": "", "date_build": None, "notes": []}
    if not csv or not (racine / csv).is_file():
        res["notes"].append(f"table de partitions introuvable ({csv or 'non definie'})")
        return res
    res["partitions"] = lit_csv((racine / csv).read_text(encoding="utf-8", errors="replace"))
    chemin, texte = journal_compilation(journaux, env)
    build = racine / ".pio" / "build" / env
    if chemin:
        res["journal"], res["date_build"] = chemin.name, chemin.stat().st_mtime
        res["ram"] = lit_table_memoire(texte)
        if not res["ram"] and (r := _RAM.search(texte)):
            res["ram"] = [{"zone": "RAM", "utilise": int(r.group(1)), "total": int(r.group(2))}]
    else:
        res["notes"].append("aucun journal de compilation reussie : compiler l'env pour mesurer app0 et la RAM")
    for p in res["partitions"]:
        p["utilise"], p["estime"] = None, False
        if p["sous_type"] == "ota_0" and chemin:
            p["utilise"] = int(_FLASH.search(texte).group(1))
        elif p["sous_type"] == "ota_0" and (build / "firmware.bin").is_file():
            p["utilise"] = (build / "firmware.bin").stat().st_size
        elif p["sous_type"] == "factory":
            s = _SAFEBOOT.search(texte) if chemin else None
            fichier = Path(s.group(1)) if s else racine / "variants" / "tasmota" / f"tasmota{board.get('build', {}).get('mcu', '').replace('esp', '')}-safeboot.bin"
            p["utilise"] = fichier.stat().st_size if fichier.is_file() else None
        elif p["sous_type"] == "spiffs":
            p["utilise"], p["estime"] = _fs_utilise(build / "littlefs_data"), True
    return res


def enregistre(dossier, env, res):
    """Ecrit <dossier>/memoire/<env>.json (ecriture atomique)."""
    cible = Path(dossier) / "memoire" / f"{env}.json"
    cible.parent.mkdir(parents=True, exist_ok=True)
    provisoire = cible.with_suffix(".tmp")
    provisoire.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    provisoire.replace(cible)


def derniere(dossier, env):
    """Derniere analyse enregistree de l'env, None si aucune ou illisible."""
    try:
        return json.loads((Path(dossier) / "memoire" / f"{env}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def resume(dossier):
    """{env: {"app0": {u, t, estime}, "FS": ..., "DIRAM": ...}} des analyses enregistrees ; zone non mesuree absente."""
    res = {}
    for chemin in sorted((Path(dossier) / "memoire").glob("*.json")):
        a = derniere(dossier, chemin.stem)
        if not a:
            continue
        zones = {}
        for part in a.get("partitions", []):
            nom = {"ota_0": "app0", "spiffs": "FS"}.get(part.get("sous_type"))
            if nom and part.get("utilise") is not None:
                zones[nom] = {"u": part["utilise"], "t": part["taille"], "estime": bool(part.get("estime"))}
        ram = a.get("ram", [])
        diram = next((z for z in ram if z["zone"] == "DIRAM"), next((z for z in ram if z["zone"] == "RAM"), None))
        if diram:
            zones["DIRAM"] = {"u": diram["utilise"], "t": diram["total"], "estime": False}
        if zones:
            res[chemin.stem] = zones
    return res


def lit_carte(adresse, persist_env, env, commande=_commande, joint=joint_par_maitre):
    """FS reel, tas et PSRAM lus sur la carte (octets). Carte muette : joignable faux et message, pas d'exception.

    Esclave joint par le maitre (`IP:port`) : redirection posee et identite verifiee d'abord, comme pour un envoi."""
    res = {"joignable": False, "adresse": adresse, "date": time.time(), "message": "", "hote": "", "fs": None, "psram": None,
           "tas_libre": None}
    try:
        if ":" in adresse:
            joint(adresse, persist_env, env, lambda _: None)
        mem = json.loads(commande(adresse, "Status 4", DELAI_CARTE))["StatusMEM"]
        res["hote"] = str(json.loads(commande(adresse, "Status 5", DELAI_CARTE)).get("StatusNET", {}).get("Hostname") or "")
        taille = json.loads(commande(adresse, "UfsSize", DELAI_CARTE)).get("UfsSize")
        libre = json.loads(commande(adresse, "UfsFree", DELAI_CARTE)).get("UfsFree")
    except (OSError, http.client.HTTPException, RuntimeError, ValueError, KeyError, AttributeError) as erreur:
        res["message"] = f"carte muette ou en safeboot, rien n'est lu ({erreur})"
        return res
    res["joignable"] = True
    if taille and libre is not None:
        res["fs"] = {"u": (taille - libre) * 1024, "t": taille * 1024}
    if mem.get("PsrMax") and mem.get("PsrFree") is not None:
        res["psram"] = {"u": (mem["PsrMax"] - mem["PsrFree"]) * 1024, "t": mem["PsrMax"] * 1024}
    if mem.get("Heap") is not None:
        res["tas_libre"] = mem["Heap"] * 1024
    return res
