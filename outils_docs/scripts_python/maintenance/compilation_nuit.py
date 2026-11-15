"""Compilation de nuit de tous les envs du fork, par la page « Build et televersement » (port 7700).

UTILISATION
    python outils_docs/scripts_python/maintenance/compilation_nuit.py [--port 7700] [--dossier D] [--dry-run]
    Lance par une tache planifiee Windows (plan tasks/plans/compilations-nuit.md, A2). Code de sortie :
        0 tout compile · 1 au moins un env en echec ou arret · 2 refuse ou page injoignable · 3 desactive.

CE QUE FAIT LE SCRIPT
    1. lit `config.json` (dossier de donnees) : {"actif": true, "envs_exclus": [], "port": 7700} ;
    2. verifie que la page repond, sinon la demarre detachee (comme build/cible_build_web.py) ;
    3. POST /lancer {actions: ["compiler"]} pour chaque env ecrivable du cenv (hors exclus). La page refuse
       (409) si un build tourne deja : le script n'attend pas, il note le refus et sort (code 2) ;
    4. attend la fin (GET /execution), relit les evenements `fin_env` (GET /flux) ;
    5. ecrit `resultat-AAAAMMJJ-HHMMSS.json` et `dernier.json` (ecriture atomique), purge au-dela de 30 jours.

ARRETER UNE COMPILATION EN COURS
    Bouton d'arret de la page Build (POST /arreter {immediat: true}), ou Ctrl+C dans la console de ce script
    (il envoie lui-meme l'arret immediat). Tuer le seul processus du script (tache planifiee « Arreter »)
    laisse la page finir le build : passer par la page ou par la tuile.

Banc : test_compilation_nuit.py (faux serveur de build).
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

PORT_DEFAUT = 7700
DELAI_MAX = 6 * 3600            # une nuit : au dela, le script rend la main (le build continue dans la page)
CONSERVE_JOURS = 30
CONFIG_DEFAUT = {"actif": True, "envs_exclus": [], "port": PORT_DEFAUT}
RACINE = Path(__file__).resolve().parents[3]
CREATE_BREAKAWAY_FROM_JOB, CREATE_NEW_PROCESS_GROUP, CREATE_NO_WINDOW = 0x01000000, 0x00000200, 0x08000000
DRAPEAUX = (CREATE_BREAKAWAY_FROM_JOB | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW) if os.name == "nt" else 0


def dossier_donnees():
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    force = os.environ.get("OUTILS_TASMOTA_DOSSIER")
    return (Path(force) if force else Path(base) / "outils_tasmota") / "compilations_nuit"


def lit_config(dossier):
    try:
        donnees = json.loads((Path(dossier) / "config.json").read_text(encoding="utf-8"))
        if not isinstance(donnees, dict):
            raise ValueError
    except (OSError, ValueError):
        donnees = {}
    config = {**CONFIG_DEFAUT, **donnees}
    config["envs_exclus"] = [str(e) for e in config["envs_exclus"]] if isinstance(config["envs_exclus"], list) else []
    return config


def ecrit_atomique(chemin, donnees):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    provisoire = chemin.with_name(chemin.name + ".tmp")
    provisoire.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(provisoire, chemin)


def appel(port, chemin, corps=None, delai=30):
    """GET, ou POST si `corps`. Rend (code, JSON ou texte). Page injoignable ou reponse illisible : (0, message)."""
    requete = urllib.request.Request(f"http://127.0.0.1:{port}{chemin}", method="POST" if corps is not None else "GET")
    donnees = None
    if corps is not None:
        donnees = json.dumps(corps).encode("utf-8")
        requete.add_header("Content-Type", "application/json")
        requete.add_header("X-Build", "1")
    try:
        with urllib.request.urlopen(requete, donnees, timeout=delai) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as e:                 # la page repond en texte brut aux refus (409, 400, 403)
        return e.code, e.read().decode("utf-8", errors="replace")
    except (OSError, ValueError) as e:                  # page tombee, delai, JSON invalide : jamais de traceback de nuit
        return 0, f"{type(e).__name__}: {e}"


def repond(port):
    """Deux essais : une page vivante mais occupee ne doit pas declencher un second build_web.py."""
    for _ in range(2):
        if appel(port, "/execution", delai=5)[0] == 200:
            return True
        time.sleep(1)
    return False


def python_page():
    """Python de PlatformIO (pyserial, comme les autres outils PC) s'il existe, sinon celui du script."""
    pio = Path.home() / ".platformio" / "penv" / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
    return str(pio) if pio.exists() else sys.executable


def demarre_page(port, dossier_journal, attente=60):
    """Demarre build_web.py detache (hors job, sans fenetre) et attend qu'il reponde."""
    Path(dossier_journal).mkdir(parents=True, exist_ok=True)
    commande = [python_page(), str(RACINE / "outils_docs" / "scripts_python" / "outils_pc" / "build_web.py"),
                "--http", str(port), "--sans-navigateur"]
    with open(Path(dossier_journal) / "build.log", "ab") as sortie:
        for drapeaux in (DRAPEAUX, DRAPEAUX & ~CREATE_BREAKAWAY_FROM_JOB):    # repli de cible_build_web : un job peut refuser BREAKAWAY
            try:
                subprocess.Popen(commande, cwd=str(RACINE), stdout=sortie, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                 creationflags=drapeaux, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                break
            except OSError:
                continue
        else:
            return False
    fin = time.monotonic() + attente
    while time.monotonic() < fin:
        if repond(port):
            return True
        time.sleep(1)
    return False


def evenements_fin(port, depuis, delai=30):
    """Rejoue /flux depuis l'evenement `depuis` (pas l'historique d'une serie precedente) jusqu'a `fin`."""
    lus = []
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/flux?depuis={int(depuis)}", timeout=delai) as r:
            for ligne in r:
                if ligne.startswith(b"data: "):
                    evenement = json.loads(ligne[6:].decode("utf-8"))
                    lus.append(evenement)
                    if evenement.get("type") == "fin":
                        break
    except (OSError, ValueError):
        pass
    return lus


def pid_vivant(pid):
    """True si le processus `pid` existe encore (Windows : STILL_ACTIVE = 259)."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        noyau = ctypes.windll.kernel32
        poignee = noyau.OpenProcess(0x1000, False, pid)           # PROCESS_QUERY_LIMITED_INFORMATION
        if not poignee:
            return False
        code = ctypes.c_ulong()
        ok = noyau.GetExitCodeProcess(poignee, ctypes.byref(code))
        noyau.CloseHandle(poignee)
        return bool(ok) and code.value == 259
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def en_cours(dossier):
    """Numero du compilation_nuit.py vivant (fichier `en_cours.json`), sinon None. Un fichier perime (processus mort) est ignore."""
    try:
        pid = int(json.loads((Path(dossier) / "en_cours.json").read_text(encoding="utf-8"))["pid"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return pid if pid_vivant(pid) else None


def purge(dossier, jours=CONSERVE_JOURS):
    limite = time.time() - jours * 86400
    for f in Path(dossier).glob("resultat-*.json"):
        try:
            if f.stat().st_mtime < limite:
                f.unlink()
        except OSError:
            pass


def execute(config, dossier, dry_run=False, maintenant=None, pause=10):
    """Une compilation de nuit. Rend (code de sortie, resultat ecrit)."""
    maintenant = maintenant or datetime.now()
    port = int(config["port"])
    resultat = {"debut": maintenant.isoformat(timespec="seconds"), "port": port, "envs": [], "refus": None, "fin": None}
    nom = f"resultat-{maintenant:%Y%m%d-%H%M%S}.json"

    verrou = {"pris": False}

    def termine(code, **champs):
        if verrou["pris"]:                                           # jamais le verrou d'un AUTRE lancement
            try:
                (Path(dossier) / "en_cours.json").unlink()
            except OSError:
                pass
        resultat.update(champs, code=code)
        ecrit_atomique(Path(dossier) / nom, resultat)
        ecrit_atomique(Path(dossier) / "dernier.json", resultat)
        purge(dossier)
        return code, resultat

    if not config["actif"]:
        return 3, {**resultat, "refus": "desactive"}                 # rien d'ecrit : une tache desactivee ne laisse pas de trace
    autre = en_cours(dossier)
    if autre and not dry_run:                                        # tache planifiee et lancement manuel ne tournent jamais ensemble
        return termine(2, refus=f"une compilation de nuit est deja en cours (processus {autre})")
    if not repond(port) and not demarre_page(port, Path(dossier).parent / "consoles"):
        return termine(2, refus="la page Build ne repond pas et n'a pas pu etre demarree")
    code, envs = appel(port, "/envs")
    if code != 200 or not isinstance(envs, dict):
        return termine(2, refus=f"/envs illisible (code {code}) : {envs}")
    exclus = set(config["envs_exclus"])
    choisis = [e["nom"] for e in envs.get("envs", []) if e.get("ecrivable") and e["nom"] not in exclus]
    resultat["envs_prevus"], resultat["envs_exclus"] = choisis, sorted(exclus)
    if not choisis:
        return termine(2, refus="aucun env a compiler")
    if dry_run:
        return 0, resultat
    ecrit_atomique(Path(dossier) / "en_cours.json", {"pid": os.getpid(), "debut": resultat["debut"]})
    verrou["pris"] = True
    code, etat = appel(port, "/execution")                           # numero du dernier evenement AVANT le lancement
    if code != 200 or not isinstance(etat, dict):
        return termine(2, refus=f"/execution illisible (code {code}) : {etat}")
    depuis = int(etat.get("numero") or 0)
    try:
        code, reponse = appel(port, "/lancer", {"lignes": [{"env": e, "methode": "ota", "port": "", "ip": ""} for e in choisis],
                                                "actions": ["compiler"]})
        if code != 200:
            return termine(2, refus=f"lancement refuse (code {code}) : {reponse}")
        debut, echecs_reseau = time.monotonic(), 0
        while True:
            if time.monotonic() - debut >= DELAI_MAX:
                return termine(1, fin="delai depasse : le build continue dans la page")
            time.sleep(pause)
            code, etat = appel(port, "/execution", delai=10)
            if code == 200 and isinstance(etat, dict):
                echecs_reseau = 0
                if not etat.get("en_cours"):
                    break
            else:
                echecs_reseau += 1
                if echecs_reseau >= 5:                               # page tombee en pleine nuit : on le note, pas de traceback
                    return termine(1, fin=f"page injoignable pendant l'attente : {etat}")
        lus = evenements_fin(port, depuis)
    except KeyboardInterrupt:
        appel(port, "/arreter", {"immediat": True})
        return termine(1, fin="arrete par Ctrl+C")
    resultat["envs"] = [{"env": e["env"], "resultat": e.get("resultat"), "secondes": e.get("secondes")}
                        for e in lus if e.get("type") == "fin_env"]
    fin = next((e for e in lus if e.get("type") == "fin"), {})
    resultat["fin"] = fin.get("resultat") or "inconnue"
    reussis = [e for e in resultat["envs"] if e["resultat"] == "succes"]
    ok = fin.get("resultat") == "termine" and len(reussis) == len(choisis)
    return termine(0 if ok else 1)


def main(argv=None):
    p = argparse.ArgumentParser(description="Compilation de nuit des envs du fork par la page Build")
    p.add_argument("--port", type=int)
    p.add_argument("--dossier", help="dossier de donnees (config.json, resultats)")
    p.add_argument("--dry-run", action="store_true", help="liste les envs prevus sans rien lancer")
    args = p.parse_args(argv)
    dossier = Path(args.dossier) if args.dossier else dossier_donnees()
    config = lit_config(dossier)
    if args.port:
        config["port"] = args.port
    code, resultat = execute(config, dossier, dry_run=args.dry_run)
    print(json.dumps({k: v for k, v in resultat.items() if k != "envs_prevus"}, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
