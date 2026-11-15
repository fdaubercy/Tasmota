"""Banc de sondes_web.py (routes, garde d'acces, arret) : vrai serveur HTTP, FAUX PowerShell, FAUX taskkill, dossier de suivi temporaire.

Aucun processus reel n'est lu ni arrete : `tue` est un enregistreur. Le banc prouve en particulier qu'aucun arret ne part sans un POST complet
(X-Sondes, meme origine, Host, client de ce PC) et qu'un pid hors du dernier releve est refuse (404).

    ~/.platformio/penv/Scripts/python.exe outils_docs/scripts_python/outils_pc/test_sondes_web.py    (code de sortie 0 = vert)
"""

import http.client
import json
import socket
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acces_web  # noqa: E402
import sondes_web as sw  # noqa: E402
import suivi_sondes  # noqa: E402
import sondes_actions as sa  # noqa: E402
import os  # noqa: E402

suivi_sondes.suit()
ECHECS = []
CHROME = "C:\\chrome.exe --headless=new --user-data-dir=C:\\Temp\\sonde_page_ab12 about:blank"


def verifie(nom, condition):
    print(("OK   " if condition else "ECHEC"), nom)
    if not condition:
        ECHECS.append(nom)


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def monte(t, procs, vivants, fichiers=()):
    """Serveur sur un dossier de suivi temporaire. Rend (req, journal_tue, etat, arret)."""
    dossier = t / "sondes"
    dossier.mkdir(exist_ok=True)
    for f in fichiers:
        (dossier / f"{f['pid']}.json").write_text(json.dumps(f), encoding="utf-8")
    tues = []
    # `relit` : relecture NEUVE du processus juste avant l'arret ; ici la liste du banc (rien de reel n'est lu), modifiable par un cas de course
    etat = sw.Etat(ps=lambda: procs, vivant=lambda pid: pid in vivants, dossier=dossier, cache_s=0, tue=lambda pid: (tues.append(pid) or True, "ok"),
                   relit=lambda pid: next((dict(p) for p in procs if p["pid"] == pid), None))
    port = port_libre()
    acces = acces_web.Acces(port, True, "Sondes en cours")
    serveur = ThreadingHTTPServer(("127.0.0.1", port), sw.fabrique_gestionnaire(acces, etat))
    threading.Thread(target=serveur.serve_forever, daemon=True).start()

    def req(methode, chemin, corps=None, entetes=None, brut=None):
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
        donnees = brut if brut is not None else (json.dumps(corps).encode("utf-8") if corps is not None else None)
        c.request(methode, chemin, body=donnees, headers=entetes or {})
        r = c.getresponse()
        return r.status, r.read().decode("utf-8", errors="replace")

    def arret():
        serveur.shutdown()
        serveur.server_close()
    return req, tues, etat, acces, arret


def un_proc(pid, parent, nom, ligne):
    return {"pid": pid, "parent": parent, "nom": nom, "ligne": ligne, "debut": 1}


def fichier(pid, nom, etat="en_cours", echecs=()):
    return {"pid": pid, "parent": 1, "nom": nom, "script": "", "debut": 1, "maj": 2**31, "total": 10, "faits": 4, "echecs": list(echecs), "phase": "p", "dernier": "d", "etat": etat}


PROCS = [un_proc(10, 5, "chrome.exe", CHROME), un_proc(20, 6, "python.exe", "python.exe C:\\x\\test_alpha.py"), un_proc(21, 6, "python.exe", "python.exe C:\\x\\banc_beta.py")]
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
    t = Path(t)
    # Chrome 10 orphelin (parent 5 mort), banc 20 avec suivi, banc 21 sans suivi, fichier 30 disparu
    req, tues, etat, acces, arret = monte(t, PROCS, {6, 10, 20, 21}, [fichier(20, "test_alpha"), fichier(30, "mort")])
    ENT = {"X-Sondes": "1"}
    try:
        # -- lecture ----------------------------------------------------------------------------
        st, corps = req("GET", "/")
        verifie("GET / : la page, titre Sondes en cours", st == 200 and "<title>Sondes en cours</title>" in corps)
        st, corps = req("GET", "/etat")
        j = json.loads(corps)
        etats = {s["pid"]: s["etat"] for s in j["sondes"]}
        verifie("GET /etat : etats orpheline / en_cours / sans_suivi / disparue", etats == {10: "orpheline", 20: "en_cours", 21: "sans_suivi", 30: "disparue"})
        verifie("GET /etat : bandeau rouge (orpheline) et phrase", j["niveau"] == "rouge" and "orphelin" in j["phrase"])
        verifie("GET /etat : l'avancement reel (4 / 10) est transmis", next(s for s in j["sondes"] if s["pid"] == 20)["faits"] == 4)
        # -- detail d'une sonde ---------------------------------------------------------------
        (t / "sondes").mkdir(exist_ok=True)
        ok20 = dict(fichier(20, "test_alpha"), script="C:/x/test_alpha.py", phases=[{"nom": "p1", "t": 1.5, "faits": 3, "echecs": 1}, "mauvais", {"nom": "x", "faits": "abc", "echecs": [1]}],
                    journal=[[1.0, "phase", "== p1"], [2.0, "ko", "KO  x"], "mauvais", [3, "ok", "<b>OK</b>"]])
        (t / "sondes" / "20.json").write_text(json.dumps(ok20), encoding="utf-8")
        st, corps = req("GET", "/detail?pid=20")
        d = json.loads(corps) if st == 200 else {}
        verifie("GET /etat : total_estime faux par defaut ; vrai quand le fichier de suivi le dit",
                next(x for x in json.loads(req("GET", "/etat")[1])["sondes"] if x["pid"] == 20)["total_estime"] is False)
        (t / "sondes" / "20.json").write_text(json.dumps(dict(fichier(20, "test_alpha"), total_estime=True)), encoding="utf-8")
        etat._cache = (0.0, None)
        verifie("total_estime vrai transmis a la page", next(x for x in json.loads(req("GET", "/etat")[1])["sondes"] if x["pid"] == 20)["total_estime"] is True)
        verifie("GET /detail?pid=20 : fiche, script, phases et journal (entrees mal formees ecartees, texte brut)",
                st == 200 and d["sonde"]["pid"] == 20 and d["script"].endswith("test_alpha.py") and [(p["nom"], p["faits"], p["echecs"]) for p in d["phases"]] == [("p1", 3, 1), ("x", 0, 0)]
                and [l[1] for l in d["journal"]] == ["phase", "ko", "ok"] and d["journal"][2][2] == "<b>OK</b>")
        st, corps = req("GET", "/detail?pid=21")
        d = json.loads(corps) if st == 200 else {}
        verifie("GET /detail?pid=21 (sans suivi) : 200, phases et journal vides", st == 200 and d["phases"] == [] and d["journal"] == [])
        verifie("GET /detail : pid absent du releve -> 404 ; pid absent ou non entier -> 400",
                req("GET", "/detail?pid=999")[0] == 404 and req("GET", "/detail")[0] == 400 and req("GET", "/detail?pid=abc")[0] == 400)
        verifie("GET inconnu : 404 ; GET ne tue rien", req("GET", "/arreter")[0] == 404 and req("GET", "/autre")[0] == 404 and not tues)
        verifie("PUT et DELETE : aucune route", [req(m, "/arreter", None, ENT)[0] for m in ("PUT", "DELETE")] == [501, 501])

        # -- garde d'acces : rien ne part sans les 4 conditions -------------------------------------
        st, _ = req("POST", "/arreter", {"pid": 20})
        verifie("sans X-Sondes : 403, rien arrete", st == 403 and not tues)
        st, _ = req("POST", "/arreter", {"pid": 20}, {"X-Taches": "1"})
        verifie("mauvais en-tete (X-Taches) : 403, rien arrete", st == 403 and not tues)
        st, _ = req("POST", "/arreter", {"pid": 20}, {**ENT, "Origin": "http://evil.example"})
        verifie("origine etrangere : 403, rien arrete", st == 403 and not tues)
        st, _ = req("POST", "/arreter", {"pid": 20}, {**ENT, "Host": "evil.example"})
        verifie("Host etranger (DNS rebinding) : 403, rien arrete", st == 403 and not tues)
        vrai_local, vrai_controle = acces_web.est_local, acces.controle
        acces_web.est_local, acces.controle = (lambda adresse: False), (lambda handler: True)       # client distant MUNI d'un jeton valide
        try:
            st, _ = req("POST", "/arreter", {"pid": 20}, ENT)
            verifie("client distant avec jeton : 403 par la garde propre au POST, rien arrete", st == 403 and not tues)
        finally:
            acces_web.est_local, acces.controle = vrai_local, vrai_controle
        verifie("aucun taskkill par tous ces refus", tues == [])

        # -- entrees invalides ----------------------------------------------------------------------
        req("GET", "/etat")
        verifie("route POST inconnue : 404", req("POST", "/autre", {}, ENT)[0] == 404)
        verifie("JSON invalide : 400", req("POST", "/arreter", None, ENT, brut=b"{pas du json")[0] == 400)
        verifie("corps non objet : 400", req("POST", "/arreter", None, ENT, brut=b"[1]")[0] == 400)
        verifie("pid texte, booleen ou absent : 400", [req("POST", "/arreter", {"pid": v}, ENT)[0] for v in ("20", True)] == [400, 400] and req("POST", "/arreter", {}, ENT)[0] == 400)
        verifie("corps trop gros : 413 ou 400", req("POST", "/arreter", None, {**ENT, "Content-Length": str(10**6)}, brut=b"x")[0] in (413, 400))
        verifie("rien arrete par ces refus", tues == [])

        # -- pid hors du releve : 404 ---------------------------------------------------------------
        req("GET", "/etat")
        for pid in (1, 4, 99999, 5, 6, 30):
            st, _ = req("POST", "/arreter", {"pid": pid}, ENT)
            verifie(f"pid {pid} (hors releve, parent, ou disparue) : 404, rien arrete", st == 404 and not tues)
        import os
        st, _ = req("POST", "/arreter", {"pid": os.getpid()}, ENT)
        verifie("pid du banc lui-meme : 404", st == 404 and not tues)

        # -- arret accepte ----------------------------------------------------------------------------
        # -- pid REUTILISE par Windows entre le releve et l'arret : on ne tue rien --------------------
        req("GET", "/etat")
        sauve = [dict(p) for p in PROCS]
        for p in PROCS:
            if p["pid"] == 21:
                p["debut"] = 999                              # meme numero, autre heure de creation : un AUTRE processus
        st, corps = req("POST", "/arreter", {"pid": 21}, ENT)
        verifie("pid reutilise (autre heure de creation) : rien tue, echec explicite", st == 200 and not tues and json.loads(corps)["arretes"] == []
                and "reutilise" in json.loads(corps)["echecs"][0]["message"])
        for p in PROCS:
            if p["pid"] == 21:
                p["nom"], p["ligne"] = "notepad.exe", "notepad.exe"      # meme numero, autre programme
        req("GET", "/etat")
        st, corps = req("POST", "/arreter", {"pid": 21}, ENT)
        verifie("numero repris par un autre programme (releve neuf le montre absent) : 404 ou rien tue", st in (200, 404) and not tues)
        PROCS[:] = sauve
        req("GET", "/etat")
        gone = [p for p in PROCS if p["pid"] == 21][0]
        PROCS.remove(gone)
        st, corps = req("POST", "/arreter", {"pid": 21}, ENT)
        verifie("processus disparu entre le releve et l'arret : rien tue", not tues)
        PROCS.append(gone)

        # -- gardes de sondes_actions, appelees directement (sans HTTP) --------------------------------
        base = {"nature": "banc", "etat": "en_cours", "parent": 1, "proc_debut": 1, "pid": 4242, "nom": "x"}
        verifie("releve sans heure de creation : on ne tue pas a l'aveugle", sa.meme_processus({**base, "proc_debut": None}, lambda pid: {**next(p for p in PROCS if p["pid"] == 21), "debut": None}) is False)
        verifie("relecture qui plante (PowerShell en panne) : on ne tue pas", sa.meme_processus(base, lambda pid: (_ for _ in ()).throw(OSError("ps"))) is False)
        verifie("relecture vide (processus disparu) : on ne tue pas", sa.meme_processus(base, lambda pid: None) is False)
        moi, pere = os.getpid(), os.getppid()
        releve = [{**base, "pid": moi, "parent": 7000}, {**base, "pid": 7000, "parent": 7001}, {**base, "pid": 7001, "parent": 1}, {**base, "pid": 8000, "parent": 1}]
        pids = [c["pid"] for c in sa._cibles(releve, orphelines=False, pid=7000)] + [c["pid"] for c in sa._cibles(releve, pid=7001)] + [c["pid"] for c in sa._cibles(releve, pid=moi)]
        verifie("le serveur et TOUS ses ancetres du releve sont inarretables (taskkill /T tuerait le serveur)", pids == [])
        verifie("un processus etranger a l'arbre du serveur reste arretable", [c["pid"] for c in sa._cibles(releve, pid=8000)] == [8000])
        releve2 = [{**base, "pid": 6000, "parent": 1}, {**base, "pid": pere, "parent": 6000}]
        verifie("le parent reel du serveur et son propre parent sont proteges", sa._cibles(releve2, pid=pere) == [] and sa._cibles(releve2, pid=6000) == [])

        req("GET", "/etat")
        st, corps = req("POST", "/arreter", {"pid": 21}, ENT)
        verifie("pid d'un banc du releve : 200, taskkill sur ce seul pid", st == 200 and tues == [21] and json.loads(corps)["arretes"] == [21])
        req("GET", "/etat")
        st, corps = req("POST", "/arreter", {"orphelines": True}, ENT)
        verifie("orphelines : seul le Chrome orphelin (10) est arrete", st == 200 and tues == [21, 10])
        st, corps = req("POST", "/arreter", {"pid": 10}, ENT)
        verifie("apres un arret, le cache est vide : le releve suivant est a refaire (pid 10 hors du releve vide -> 404)", st == 404)
    finally:
        arret()

    # -- relevé PowerShell impossible : la page reste servie ------------------------------------------
    def ps_mort():
        raise OSError("PowerShell absent")
    etat2 = sw.Etat(ps=ps_mort, vivant=lambda p: False, dossier=t / "vide", cache_s=0)
    j = etat2.complet()
    verifie("PowerShell en panne : orange, erreur dite, liste vide, pas d'exception", j["niveau"] == "orange" and "PowerShell absent" in j["erreur"] and j["sondes"] == [])
    verifie("bandeau vert sans sonde", sw.bandeau([])[0] == "vert")

print("\nVERT" if not ECHECS else f"\nROUGE : {ECHECS}")
sys.exit(1 if ECHECS else 0)
