#!/usr/bin/env python3
"""Gardes de compilation des commandes Tasmota, evaluees pour l'env d'une carte (plan autoexec-mqtt-tapp, A4).

`etat(racine, env)` rend une fonction `nom -> [chemin, ...]` (chemin = [(condition, VRAI|FAUX|INCERTAIN), ...], d'apres la
cle `gardes` de commandes_tasmota.json), ou None si le preprocesseur n'est pas disponible : l'analyse ne leve alors aucune
alerte « absente ». Une garde que le preprocesseur ne tranche pas reste INCERTAIN (une fausse alerte est pire qu'une
alerte manquee). Le calcul tourne dans un processus fils (pas de chdir dans la page, serveur a plusieurs fils) ; les macros de l'env
(STA_PASS1, MQTT_PASS...) n'en sortent jamais : seuls vrai/faux/incertain reviennent.
Cache en memoire par (racine, env, empreinte du cenv et de user_config_override.h), None compris, sous verrou : une
frappe ne relance jamais le preprocesseur (~1 s) une fois le cache pose. Echec quelconque -> None et une ligne en console.
Exception documentee (A9) : import de ../build/ par sys.path explicite, comme synchro_fork_web.py.
Banc : test_autoexec_gardes.py.
"""

import fnmatch
import hashlib
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "build"))

import autoexec_commandes  # noqa: E402

# Tout ce qui change les macros d'un env ou les gardes : (dossier, motif) relatifs a la racine. Empreinte = (nom, mtime_ns,
# taille) lus dans le listing du dossier (os.scandir : pas de stat par fichier, ~10 ms de moins sous Windows), contenu jamais relu.
# platformio_override.ini est reecrit par chaque build : un build = un recalcul.
FICHIERS = (("", "platformio.ini"), ("", "platformio_override.ini"), ("", "platformio_tasmota32.ini"),
            ("", "platformio_tasmota_env*.ini"), ("", "platformio_tasmota_cenv.ini"),
            ("tasmota", "my_user_config.h"), ("tasmota/include", "tasmota_configurations*.h"),
            ("tasmota", "user_config_override.h"), ("boards", "*.json"), ("outils_docs/schemas", "commandes_tasmota.json"))
_CACHE = {}
_VERROU = threading.Lock()


def _evalue(racine, env):
    """{nom: [[(condition, vrai|faux|None)]]} pour l'env. Tourne dans le processus fils : le chdir (extra_configs de
    platformio.ini se resolvent depuis le dossier courant) n'y touche personne. Contexte(defines) sans options : seuls
    USE_*, FIRMWARE_*... font foi, le reste reste incertain (decision du controleur : aucune macro hors famille n'est fausse)."""
    from platformio.project.config import ProjectConfig
    import verifie_lib_ignore as v
    from lecture_gardes import Contexte, evalue

    os.chdir(racine)
    defines = v.defines_env(str(racine), v.options_env(ProjectConfig(os.path.join(racine, "platformio.ini")), env))
    ctx = Contexte(defines)
    return {nom: [[(c, evalue(c, ctx, {})) for c in chemin] for chemin in chemins]
            for nom, chemins in autoexec_commandes.charge(racine).get("gardes", {}).items()}


def _calcule(racine, env):
    """Fonction `nom -> chemins evalues` ; leve si le fils echoue. Seules les valeurs vrai/faux/incertain reviennent :
    les macros de l'env (mots de passe compris) restent dans le fils."""
    p = subprocess.run([sys.executable, str(Path(__file__).resolve()), str(racine), env], cwd=racine, capture_output=True,
                       text=True, timeout=45, stdin=subprocess.DEVNULL)
    if p.returncode:
        raise RuntimeError(f"processus fils code {p.returncode}")
    table = json.loads(p.stdout)
    return lambda nom: table.get(nom)


def _empreinte(racine):
    listings, h = {}, hashlib.sha256()
    for dossier, motif in FICHIERS:
        if dossier not in listings:
            try:
                with os.scandir(os.path.join(racine, dossier)) as it:
                    listings[dossier] = sorted(it, key=lambda e: e.name)
            except FileNotFoundError:
                listings[dossier] = []
        for e in listings[dossier]:
            if fnmatch.fnmatch(e.name, motif) and e.is_file():
                st = e.stat()
                h.update(f"{dossier}/{e.name}|{st.st_mtime_ns}|{st.st_size}\n".encode())
    return h.hexdigest()


def etat(racine, env):
    try:
        cle = (str(racine), env, _empreinte(racine))
    except OSError:
        return None
    with _VERROU:
        if cle not in _CACHE:
            for ancienne in [k for k in _CACHE if k[:2] == cle[:2]]:     # une entree par (racine, env) : chaque build change l'empreinte
                del _CACHE[ancienne]
            try:
                _CACHE[cle] = _calcule(racine, env)
            except Exception as e:                   # noqa: BLE001 - jamais d'erreur vers la route
                print(f"autoexec_gardes : verification par carte indisponible pour {env} ({type(e).__name__})", flush=True)
                _CACHE[cle] = None
        return _CACHE[cle]


if __name__ == "__main__":                           # processus fils de _calcule : JSON sur la sortie standard
    print(json.dumps(_evalue(sys.argv[1], sys.argv[2])))
