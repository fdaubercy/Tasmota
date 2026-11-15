"""Banc des gestes de la page « Taches planifiees » (POST /geste) : vrai serveur HTTP, fausses commandes, depot et dossier temporaires.

AUCUN vrai schtasks, AUCUN vrai gh, la fausse page Build remplace le port 7700, la racine du depot est un dossier temporaire : le vrai depot,
la vraie tache Windows et le vrai workflow ne sont jamais touches (le banc le verifie pour le fichier des envs GitHub).

    ~/.platformio/penv/Scripts/python.exe outils_docs/scripts_python/outils_pc/test_taches_planifiees_post.py    (code de sortie 0 = vert)
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
import acces_web
import taches_planifiees_web as tw
from test_taches_planifiees_web import faux_gh

ECHECS = []


def verifie(nom, condition):
    print(("OK   " if condition else "ECHEC"), nom)
    if not condition:
        ECHECS.append(nom)


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def gh_complet(journal):
    base = faux_gh()

    def gh(args, delai=0):
        journal.append(list(args))
        if args[:2] in (["run", "cancel"], ["workflow", "run"], ["workflow", "enable"], ["workflow", "disable"]):
            return 0, ""
        if args[:2] == ["run", "list"] and "--status" in args:
            return 0, json.dumps([{"databaseId": 7}] if args[args.index("--status") + 1] == "in_progress" else [])
        return base(args, delai)
    return gh


def faux_schtasks(journal):
    def executeur(*args):
        journal.append(args)
        return 0, '"Nom de la tâche","Statut de la tâche planifiée","Prochaine exécution"\r\n"\\Tasmota-CompilationNuit","Activé","16/11/2026 02:00:00"\r\n'
    return executeur


def fausse_page(journal, en_cours=False):
    def appel(port, chemin, corps=None, delai=30):
        journal.append((port, chemin, corps))
        if chemin == "/execution":
            return 200, {"en_cours": en_cours, "numero": 0}
        return 200, {"ok": True}
    return appel


REEL = Path(tw.tgest.matrice.RACINE) / tw.tgest.matrice.FICHIER_EXCLUS
reel_avant = REEL.exists()

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
    t = Path(t)
    racine = t / "depot"
    racine.mkdir()
    (racine / "platformio_tasmota_cenv.ini").write_text("[env:a]\n[env:b]\n[env:c]\n", encoding="utf-8")
    jgh, jst, jpage, jlance, jgit = [], [], [], [], []

    def faux_git(args, racine_git):                    # aucun vrai git : ni commit ni push du vrai depot
        jgit.append(list(args))
        if args[0] == "rev-parse":
            return 0, ("development" if "--abbrev-ref" in args else "f" * 40)
        return 0, ("0\t0" if args[0] == "rev-list" else "")
    etat = tw.Etat(gh_complet(jgh), faux_schtasks(jst), t / "c", t / "j", cache_s=60, appel=fausse_page(jpage),
                   lance=lambda c, **k: jlance.append(c), racine=racine, eteinte=lambda port: True, git=faux_git)
    port = port_libre()
    acces = acces_web.Acces(port, True, "Taches planifiees")
    serveur = ThreadingHTTPServer(("127.0.0.1", port), tw.fabrique_gestionnaire(acces, etat))
    threading.Thread(target=serveur.serve_forever, daemon=True).start()

    def req(methode, chemin, corps=None, entetes=None, brut=None):
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
        donnees = brut if brut is not None else (json.dumps(corps).encode("utf-8") if corps is not None else None)
        c.request(methode, chemin, body=donnees, headers=entetes or {})
        r = c.getresponse()
        return r.status, r.read().decode("utf-8", errors="replace")

    def geste(voie, nom, valeur=None, entetes=None):
        return req("POST", "/geste", {"voie": voie, "geste": nom, "valeur": valeur}, {"X-Taches": "1", **(entetes or {})})

    try:
        # -- garde d'acces : rien ne part sans les 4 conditions --------------------------------------
        st, _ = req("POST", "/geste", {"voie": "pc", "geste": "active"})
        verifie("sans X-Taches : 403, rien execute", st == 403 and not jst)
        st, _ = geste("pc", "active", entetes={"Origin": "http://evil.example"})
        verifie("origine etrangere : 403, rien execute", st == 403 and not jst)
        st, _ = geste("pc", "active", entetes={"Host": "evil.example"})
        verifie("Host etranger : 403 (DNS rebinding), rien execute", st == 403 and not jst)
        # Client distant MUNI D'UN JETON VALIDE : acces.controle() l'accepte, seule la garde propre aux gestes le refuse.
        vrai_local, vrai_controle = acces_web.est_local, acces.controle
        acces_web.est_local, acces.controle = (lambda adresse: False), (lambda handler: True)
        try:
            st, _ = geste("pc", "active")
            verifie("client distant avec jeton : 403 par la garde des gestes, rien execute", st == 403 and not jst)
        finally:
            acces_web.est_local, acces.controle = vrai_local, vrai_controle
        verifie("PUT et DELETE : aucune route", [req(m, "/geste", None, {"X-Taches": "1"})[0] for m in ("PUT", "DELETE")] == [501, 501])

        # -- entrees invalides -----------------------------------------------------------------------
        verifie("route inconnue : 404", req("POST", "/autre", {}, {"X-Taches": "1"})[0] == 404)
        verifie("JSON invalide : 400", req("POST", "/geste", None, {"X-Taches": "1"}, brut=b"{pas du json")[0] == 400)
        verifie("corps non objet : 400", req("POST", "/geste", None, {"X-Taches": "1"}, brut=b"[1]")[0] == 400)
        verifie("voie inconnue : 400", geste("nuage", "active")[0] == 400)
        verifie("geste inconnu : 400", geste("pc", "detruire")[0] == 400)
        verifie("geste d'une autre voie : 400", geste("pc", "envs_apercu", [])[0] == 400)
        verifie("geste non texte : 400", req("POST", "/geste", {"voie": "pc", "geste": ["a"]}, {"X-Taches": "1"})[0] == 400)
        verifie("corps trop gros : 413", req("POST", "/geste", None, {"X-Taches": "1", "Content-Length": str(10**6)}, brut=b"x")[0] in (413, 400))
        verifie("Content-Length negatif : 400", req("POST", "/geste", None, {"X-Taches": "1", "Content-Length": "-1"}, brut=b"x")[0] == 400)
        verifie("rien n'a ete execute par ces refus", not jst and not jgh and not jpage and not jlance)

        # -- gestes simultanes : un seul a la fois (memes .tmp, memes controles de serie) ---------------
        import time
        suivi, compte, original = {"actuel": 0, "max": 0}, threading.Lock(), etat.schtasks

        def lent(*args):
            with compte:
                suivi["actuel"] += 1
                suivi["max"] = max(suivi["max"], suivi["actuel"])
            time.sleep(0.15)
            with compte:
                suivi["actuel"] -= 1
            return original(*args)
        etat.schtasks = lent
        fils = [threading.Thread(target=lambda: geste("pc", "active")) for _ in range(4)]
        for f in fils:
            f.start()
        for f in fils:
            f.join()
        etat.schtasks = original
        verifie("4 gestes simultanes : jamais deux en meme temps", suivi["max"] == 1)
        del jst[:]

        # -- voie PC ---------------------------------------------------------------------------------
        st, corps = geste("pc", "desactive")
        verifie("PC desactive : schtasks /disable", st == 200 and any("/disable" in a for a in jst))
        st, corps = geste("pc", "heure", "03:15")
        verifie("PC heure : schtasks /st 03:15", st == 200 and any("/st" in a and "03:15" in a for a in jst))
        verifie("PC heure invalide : 400", geste("pc", "heure", "25:00")[0] == 400)
        st, corps = geste("pc", "arreter")
        verifie("PC arreter sans serie : 409, aucun /arreter envoye", st == 409 and not any(c == "/arreter" for _, c, _ in jpage))
        etat.appel = fausse_page(jpage, en_cours=True)
        st, corps = geste("pc", "arreter")
        verifie("PC arreter avec serie : /arreter immediat sur le port de la config", st == 200 and (7700, "/arreter", {"immediat": True}) in jpage)
        st, corps = geste("pc", "lancer")
        verifie("PC lancer pendant un build : 409, rien demarre", st == 409 and not jlance)
        etat.appel = fausse_page(jpage, en_cours=False)
        st, corps = geste("pc", "lancer")
        verifie("PC lancer : processus compilation_nuit.py", st == 200 and len(jlance) == 1 and jlance[0][1].endswith("compilation_nuit.py"))
        st, corps = geste("pc", "envs", ["b"])
        config = json.loads((t / "c" / "config.json").read_text(encoding="utf-8"))
        verifie("PC envs : config.json du dossier temporaire", st == 200 and config["envs_exclus"] == ["b"] and config["actif"] is True)
        verifie("PC envs inconnu : 400, config intacte", geste("pc", "envs", ["zzz"])[0] == 400
                and json.loads((t / "c" / "config.json").read_text(encoding="utf-8"))["envs_exclus"] == ["b"])

        # -- voie GitHub -----------------------------------------------------------------------------
        st, _ = req("GET", "/etat")
        n = len(jgh)
        req("GET", "/etat")
        verifie("cache de sante : 2e lecture sans gh", len(jgh) == n)
        st, corps = geste("github", "desactive")
        verifie("GitHub desactive : gh workflow disable", st == 200 and ["workflow", "disable", "Build_custom", "-R", "fdaubercy/Tasmota"] in jgh)
        n = len(jgh)
        req("GET", "/etat")
        verifie("apres un geste GitHub : le cache est vide, gh relance", len(jgh) > n)
        st, _ = geste("github", "lancer")
        verifie("GitHub lancer : gh workflow run", st == 200 and any(a[:3] == ["workflow", "run", "Build_custom"] for a in jgh))
        st, corps = geste("github", "arreter")
        verifie("GitHub arreter : run 7 annule", st == 200 and ["run", "cancel", "7", "-R", "fdaubercy/Tasmota"] in jgh)
        st, corps = geste("github", "envs_apercu", ["a"])
        d = json.loads(corps)["resultat"]
        verifie("GitHub apercu : rien d'ecrit", st == 200 and d["ajoutes"] == ["a"] and not (racine / tw.tgest.matrice.FICHIER_EXCLUS).exists())
        st, corps = geste("github", "envs", ["a", "c"])
        verifie("GitHub envs : fichier ecrit dans le depot TEMPORAIRE", st == 200 and tw.tgest.matrice.matrice(racine) == ["b"])
        verifie("GitHub envs : commit puis push du sha, par le faux git", json.loads(corps)["resultat"]["publie"] is True
                and ["push", "origin", "f" * 40 + ":development"] in jgit and any(c[0] == "commit" for c in jgit))
        verifie("GitHub envs inconnu : 400", geste("github", "envs", ["zzz"])[0] == 400)
        etat_json = json.loads(req("GET", "/etat?frais=1")[1])
        verifie("/etat : envs du cenv et exclusions GitHub", etat_json["envs"] == ["a", "b", "c"] and etat_json["github_exclus"] == ["a", "c"])
        (racine / tw.tgest.matrice.FICHIER_EXCLUS).write_text("{pas du json", encoding="utf-8")
        etat_json = json.loads(req("GET", "/etat?frais=1")[1])
        verifie("fichier d'exclusions illisible : signale, pas de panne", etat_json["github_exclus"] == [] and "illisible" in etat_json["github_exclus_erreur"])
    finally:
        serveur.shutdown()
        serveur.server_close()
    verifie("le vrai fichier d'exclusions du depot n'a pas ete touche", REEL.exists() == reel_avant)

print("\nVERT" if not ECHECS else f"\nROUGE : {ECHECS}")
sys.exit(1 if ECHECS else 0)
