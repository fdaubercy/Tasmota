"""Banc de la page « Taches planifiees » (github, pc, sante, routes) avec FAUX gh et FAUX schtasks. Code de sortie 0 = vert.

Aucun vrai gh, aucun vrai schtasks, aucun reseau : dossier de donnees temporaire, serveur reel sur 127.0.0.1 (port libre).
Temoins negatifs : chaque controle de sante retire dans une copie du module doit rendre le banc rouge.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_taches_planifiees_web.py
"""
import http.client
import json
import socket
import sys
import tempfile
import threading
import types
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

import acces_web
import suivi_sondes  # avancement reel sur la page Sondes en cours
suivi_sondes.suit()
import taches_planifiees_github as tg_original
import taches_planifiees_sante as ts_original
import taches_planifiees_web as tw

ECHECS = []
MAINTENANT = datetime(2026, 11, 16, 8, 0, tzinfo=timezone.utc)
HOSTILE = "<img src=x onerror=window.__pwn=1> & <b>gras</b>"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def iso(heures):
    return (MAINTENANT - timedelta(hours=heures)).strftime("%Y-%m-%dT%H:%M:%SZ")


def faux_gh(runs=None, workflow="active", permissions=True, jobs=None, code=0, sortie="", appels=None):
    """Faux gh. `code` != 0 : tout echoue avec `sortie`."""
    runs = runs if runs is not None else [{"databaseId": 1, "status": "completed", "conclusion": "success", "event": "schedule", "createdAt": iso(10), "url": "https://github.com/x/1"}]

    def gh(args, delai=0):
        if appels is not None:
            appels.append(list(args))
        if code:
            return code, sortie
        if args[0] == "run" and args[1] == "list":
            return 0, json.dumps(runs)
        if args[0] == "run" and args[1] == "view":
            return 0, json.dumps({"jobs": jobs or []})
        if args[0] == "workflow":
            return 0, json.dumps([{"name": "Build_custom", "state": workflow}, {"name": "Autre", "state": "disabled_inactivity"}])
        if args[0] == "api":
            return 0, json.dumps({"enabled": permissions})
        return 1, "commande inconnue"
    return gh


def faux_schtasks(existe=True):
    def executeur(*args):
        if not existe:
            return 1, "ERREUR : introuvable"
        return 0, '"Nom de la tâche","Statut de la tâche planifiée","Prochaine exécution"\r\n"\\Tasmota-CompilationNuit","Désactivé","N/A"\r\n'
    return executeur


def cas_github(tg, ts):
    """Les cas de sante GitHub contre les modules donnes (originaux ou mutants). Rend le nombre d'echecs ajoutes."""
    avant = len(ECHECS)
    pc = {"dernier": None}

    def bandeau(gh):
        return ts.bandeau(pc, tg.sante(gh, MAINTENANT))
    n, p = bandeau(faux_gh())
    verifie(n, "vert", "tout vert : bandeau vert")
    n, p = bandeau(faux_gh(code=127, sortie="gh introuvable"))
    verifie((n, "absente" in p, "non verifie" in p), ("orange", True, True), "gh absent : orange, le dit, et dit que GitHub n'est pas verifie")
    n, p = bandeau(faux_gh(code=124, sortie="delai depasse"))
    verifie((n, "injoignable" in p), ("orange", True), "gh hors ligne : orange et le dit")
    n, p = bandeau(faux_gh(code=1, sortie="To get started with GitHub CLI, please run:  gh auth login"))
    verifie((n, "connecte" in p), ("orange", True), "gh non connecte : orange et le dit")
    n, p = bandeau(faux_gh(workflow="disabled_inactivity", permissions=True))
    verifie((n, "disabled_inactivity" in p), ("rouge", True), "workflow desactive alors que permissions dit enabled true : rouge")
    n, p = bandeau(faux_gh(workflow="disabled_manually"))
    verifie(n, "rouge", "workflow desactive a la main : rouge")
    n, p = bandeau(faux_gh(permissions=False))
    verifie(n, "rouge", "Actions desactivees : rouge")
    ancien = [{"databaseId": 2, "status": "completed", "conclusion": "success", "event": "schedule", "createdAt": iso(40), "url": "https://github.com/x/2"}]
    n, p = bandeau(faux_gh(runs=ancien))
    verifie((n, "40.0" in p), ("rouge", True), "dernier run planifie de 40 h : rouge")
    manuel = [{"databaseId": 3, "status": "completed", "conclusion": "success", "event": "workflow_dispatch", "createdAt": iso(1), "url": "u"}]
    n, p = bandeau(faux_gh(runs=manuel))
    verifie(n, "rouge", "run recent mais aucun planifie : rouge")
    n, p = bandeau(faux_gh(runs=[]))
    verifie(n, "rouge", "aucun run du tout : rouge")
    jobs = [{"name": HOSTILE, "conclusion": "failure", "url": "https://github.com/x/1/job/9"}, {"name": "ok", "conclusion": "success", "url": "u"}]
    s = tg.sante(faux_gh(jobs=jobs), MAINTENANT)
    verifie([j["nom"] for j in s["echecs"]], [HOSTILE], "job en echec : seul l'echec est rendu, nom intact (l'echappement est fait par la page)")
    n, p = ts.bandeau(pc, s)
    verifie(n, "orange", "job en echec : orange")
    mixte = faux_gh()
    s = tg.sante(lambda a, delai=0: (124, "x") if a[0] == "api" else mixte(a), MAINTENANT)
    verifie((s["ok"], len(s["pannes"]), s["permissions"]), (True, 1, None), "permissions illisibles seules : panne partielle, le reste est lu")
    return len(ECHECS) - avant


def cas_pc():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
        import taches_planifiees_pc as tp
        d = Path(t) / "compilations_nuit"
        d.mkdir()
        (Path(t) / "build" / "journaux").mkdir(parents=True)
        (Path(t) / "build" / "journaux" / "20261115-043620-tasmota-cave-1.log").write_text("x", encoding="utf-8")
        r = tp.lit_pc(d, faux_schtasks(), Path(t) / "build" / "journaux")
        verifie((r["dernier"], r["historique"], r["tache"]["existe"], r["tache"]["actif"]), (None, [], True, False), "dossier de resultats vide : pas de dernier, tache desactivee lue")
        verifie(tp.lit_pc(d, faux_schtasks(False))["tache"]["existe"], False, "tache absente")
        (d / "dernier.json").write_text("{pas du json", encoding="utf-8")
        r = tp.lit_pc(d, faux_schtasks())
        verifie(r["dernier"], {"illisible": "dernier.json"}, "JSON corrompu : signale, pas de traceback")
        verifie(ts_original.bandeau(r, tg_original.sante(faux_gh(), MAINTENANT))[0], "orange", "JSON corrompu : bandeau orange")
        res = {"debut": "2026-11-15T02:00:00", "port": 7700, "code": 1, "refus": None, "fin": "termine", "envs_prevus": ["a", HOSTILE, "tasmota-cave-1"],
               "envs": [{"env": "a", "resultat": "succes", "secondes": 60}, {"env": HOSTILE, "resultat": "echec", "secondes": 30},
                        {"env": "tasmota-cave-1", "resultat": "echec", "secondes": 5}]}
        (d / "dernier.json").write_text(json.dumps(res), encoding="utf-8")
        (d / "resultat-20261115-020000.json").write_text(json.dumps(res), encoding="utf-8")
        r = tp.lit_pc(d, faux_schtasks(), Path(t) / "build" / "journaux")
        verifie([e["env"] for e in r["dernier"]["echecs"]], [HOSTILE, "tasmota-cave-1"], "env en echec : une entree par env, nom intact")
        verifie(r["dernier"]["echecs"][1]["journal"].endswith("20261115-043620-tasmota-cave-1.log"), True, "env en echec : chemin du journal local")
        verifie((r["dernier"]["nb_envs"], r["dernier"]["nb_prevus"], r["dernier"]["secondes"], len(r["historique"])), (3, 3, 95, 1), "resume : compteurs et duree")
        verifie(ts_original.bandeau(r, tg_original.sante(faux_gh(), MAINTENANT))[0], "orange", "derniere nuit en echec : orange")


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def cas_web():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
        appels = []
        etat = tw.Etat(faux_gh(appels=appels), faux_schtasks(), Path(t) / "c", Path(t) / "j", cache_s=60)
        port = port_libre()
        acces = acces_web.Acces(port, True, "Taches planifiees")
        serveur = ThreadingHTTPServer(("127.0.0.1", port), tw.fabrique_gestionnaire(acces, etat))
        threading.Thread(target=serveur.serve_forever, daemon=True).start()

        def req(methode, chemin, entetes=None):
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
            c.request(methode, chemin, headers=entetes or {})
            r = c.getresponse()
            return r.status, r.read()
        try:
            st, corps = req("GET", "/")
            verifie((st, "<title>Tâches planifiées</title>".encode("utf-8") in corps), (200, True), "GET / : la page")
            st, corps = req("GET", "/etat")
            d = json.loads(corps)
            verifie((st, d["niveau"], sorted(d)), (200, "vert", ["envs", "github", "github_exclus", "github_exclus_erreur", "instant", "niveau", "pc", "phrase"]), "GET /etat : bandeau, deux voies et choix des envs")
            n = len(appels)
            req("GET", "/etat")
            verifie(len(appels), n, "cache : une 2e ouverture n'appelle pas gh")
            req("GET", "/etat?frais=1")
            verifie(len(appels) > n, True, "?frais=1 : gh relance")
            verifie([req(m, "/etat", {"X-Menage": "1"})[0] for m in ("POST", "PUT", "DELETE")], [403, 501, 501], "POST sans X-Taches refuse (les gestes : test_taches_planifiees_post.py), PUT et DELETE sans route")
            verifie(req("GET", "/inconnu")[0], 404, "route inconnue : 404")
            st, _ = req("GET", "/etat", {"Host": "evil.example"})
            verifie(st, 403, "Host etranger : refuse (DNS rebinding)")
        finally:
            serveur.shutdown()
            serveur.server_close()


def mutant(module, ancien, nouveau):
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert source.count(ancien) == 1, ancien
    m = types.ModuleType(module.__name__ + "_mutant")
    m.__file__ = module.__file__
    exec(compile(source.replace(ancien, nouveau), module.__file__, "exec"), m.__dict__)
    return m


def temoins():
    ok = True
    for nom, module, ancien, nouveau in [
            ("workflow-desactive", tg_original, 'if wf.get("state") != "active":', "if False:"),
            ("age-planifie", tg_original, 'or r["age_planifie_h"] > SEUIL_PLANIFIE_H', "or False"),
            ("aucun-planifie", tg_original, "if plan is None:", "if False:"),
            ("permissions", tg_original, 'if perm.get("enabled") is False:', "if False:"),
            ("gh-absent", tg_original, "if code == 127:\n        return", "if False:\n        return"),
            ("bandeau-alertes", ts_original, 'if gh["alertes"]:', "if False:"),
            ("bandeau-gh-ko", ts_original, "if not gh[\"ok\"]:", "if False:")]:
        tg, ts = (mutant(module, ancien, nouveau), ts_original) if module is tg_original else (tg_original, mutant(module, ancien, nouveau))
        avant = len(ECHECS)
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                cas_github(tg, ts)
            except Exception:
                ECHECS.append("exception")
        detecte = len(ECHECS) > avant
        del ECHECS[avant:]
        print(("OK   " if detecte else "KO   ") + f"temoin {nom} detecte")
        ok = ok and detecte
    return ok


def principal():
    cas_github(tg_original, ts_original)
    cas_pc()
    cas_web()
    if not ECHECS and not temoins():
        ECHECS.append("temoin non detecte")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
