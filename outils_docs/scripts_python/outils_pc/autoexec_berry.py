#!/usr/bin/env python3
"""Commandes Berry du depot que l'autoexec.be d'une carte ne charge PAS (plan autoexec-mqtt-tapp, amelioration A).

`non_chargees(racine, env)` rend `{NOM_MAJUSCULES: [modules qui la declarent]}` pour l'env, ou None quand on ne sait pas
(autoexec.be absent, illisible, ou sans aucun module reconnu : forme ancienne non comprise) : l'analyse se tait alors.
Une commande Berry est `tasmota.add_cmd("Nom", ...)` dans un .be de data/fs ou du dossier de la carte. Un module est charge si
son nom apparait dans autoexec.be (chaine `"controleUDP"`, `"/controleUDP"`, `import x`), dans un module charge (meme regle,
fermeture transitive), ou par `demarrage.leds()` / `demarrage.historique()`. Une commande n'est signalee que si AUCUN des
modules qui la declarent n'est charge. On se trompe donc toujours du cote du silence : un nom cite dans un commentaire
ou une condition `OFF` du persist (module cite mais pas lance) compte comme charge.
Cache par (racine, env, empreinte des .be : nom, date, taille) : appelee a chaque frappe, sans relire les fichiers.
Banc : test_autoexec_berry.py.
"""

import os
import re
import threading
from pathlib import Path

import fichiers_berry_etat

ADD_CMD = re.compile(r"""add_cmd\(\s*['"](\w+)['"]""")
NOMS = re.compile(r"""\bimport\s+([A-Za-z_]\w*)|["']/?([A-Za-z_]\w*)(?:\.bec?)?["']""")
IMPLICITES = {"demarrage.leds(": ("controleLeds", "ledsFonctions"), "demarrage.historique(": ("historiqueFonctions",)}
_CACHE, _VERROU = {}, threading.Lock()


def _fichiers(dossier):
    """{module: chemin} des .be d'un dossier et leur empreinte ; vide si le dossier manque."""
    try:
        with os.scandir(dossier) as it:
            return {e.name[:-3]: (e.path, e.stat().st_mtime_ns, e.stat().st_size) for e in it if e.name.endswith(".be") and e.is_file()}
    except OSError:
        return {}


def _calcule(modules, source_de):
    """modules : {nom: chemin} (dossier de la carte prioritaire sur data/fs) ; None si autoexec.be n'est pas compris."""
    try:
        auto = source_de("autoexec")
    except (OSError, KeyError):
        return None
    charges = {n for t in NOMS.findall(auto) for n in t if n in modules and n != "autoexec"}
    charges |= {m for motif, noms in IMPLICITES.items() if motif in auto for m in noms if m in modules}
    if not charges:
        return None                                  # forme non comprise : ne rien dire
    pile = list(charges)
    while pile:
        for t in NOMS.findall(source_de(pile.pop())):
            for n in t:
                if n in modules and n != "autoexec" and n not in charges:
                    charges.add(n)
                    pile.append(n)
    declarent = {}
    for nom in modules:
        for cmd in ADD_CMD.findall(source_de(nom)):
            declarent.setdefault(cmd.upper(), set()).add(nom)
    return {cmd: sorted(mods) for cmd, mods in declarent.items() if not mods & charges}


def non_chargees(racine, env):
    try:
        dossier = fichiers_berry_etat.dossier_carte(env)
    except ValueError:
        return None
    if not dossier:
        return None
    fs, carte = _fichiers(os.path.join(racine, "data", "fs")), _fichiers(os.path.join(racine, dossier))
    modules = {**fs, **carte}
    cle = (str(racine), env, tuple(sorted((n, v[1], v[2]) for n, v in modules.items())))
    with _VERROU:
        if cle not in _CACHE:
            for ancienne in [k for k in _CACHE if k[:2] == cle[:2]]:
                del _CACHE[ancienne]
            lu = lambda nom: Path(modules[nom][0]).read_text(encoding="utf-8", errors="replace")
            try:
                _CACHE[cle] = _calcule({n: v[0] for n, v in modules.items()}, lu)
            except Exception as e:                   # noqa: BLE001 - jamais d'erreur vers la route
                print(f"autoexec_berry : modules Berry indisponibles pour {env} ({type(e).__name__})", flush=True)
                _CACHE[cle] = None
        return _CACHE[cle]
