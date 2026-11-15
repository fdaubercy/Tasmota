"""Banc de liens_web et liens_web_web : ajout, retrait, archivage (anti-SSRF), routes. Code de sortie 0 = vert.

Mini-depot temporaire ; les liens du vrai depot (genere_liens_web.collecte) et LIENS_WEB.md sont remplaces par des faux.
Le serveur de PDF est local : verifie_hote le refuse (temoin), puis il est neutralise pour tester le chemin d'archivage.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_liens_web.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import http.client
import json
import socket
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import acces_web
import genere_liens_web as gen
import liens_web as lw
import liens_web_web as web

ECHECS = []
PDF = b"%PDF-1.4\n" + b"x" * 300 + b"\n%%EOF\n"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def leve(f, *a):
    try:
        f(*a)
    except (ValueError, KeyError) as e:
        return type(e).__name__
    return None


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Fournisseur(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        corps, type_ = {"/f.pdf": (PDF, "application/pdf"), "/faux.pdf": (b"pas un pdf" * 30, "application/pdf"),
                        "/img.png": (b"\x89PNG" * 50, "image/png"), "/gros.pdf": (PDF * 400, "application/pdf")}.get(self.path, (b"", "text/plain"))
        self.send_response(200)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)


def principal():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
        racine = Path(t)
        gen.collecte = lambda: {"https://exemple-public.org/a.pdf": {"CLAUDE.md"}}
        gen.SORTIE = racine / "LIENS_WEB.md"
        gen.AJOUTES = racine / "outils_docs" / "liens_web" / "liens_ajoutes.json"

        # ---- ajout / retrait
        e = lw.ajoute(racine, {"url": "https://fiche-publique.org/p", "titre": "Fiche", "categorie": "PCB, fabrication, KiCad", "note": "n"})
        verifie(e["titre"], "Fiche", "ajoute : entree rendue")
        d = lw.construit(racine)
        verifie(sorted(l["url"] for l in d["liens"]), ["https://exemple-public.org/a.pdf", "https://fiche-publique.org/p"], "construit : lien cite + lien ajoute")
        verifie([l["ajoute"] for l in d["liens"]], [False, True], "construit : drapeau ajoute")
        lw.ajoute(racine, {"url": "https://fiche-publique.org/p", "titre": "Fiche 2"})
        verifie([l["titre"] for l in lw.construit(racine)["liens"] if l["ajoute"]], ["Fiche 2"], "ajoute deux fois la meme URL : mise a jour, pas de doublon")
        for mauvais in ("javascript:alert(1)", "http://192.168.0.5/x", "http://localhost/x", "https://u:p@site.org/x", "ftp://site.org/x", ""):
            verifie(leve(lw.ajoute, racine, {"url": mauvais}), "ValueError", f"ajoute refuse : {mauvais!r}")
        verifie(leve(lw.ajoute, racine, {"url": "https://site.org/x", "categorie": "Inconnue"}), "ValueError", "ajoute refuse : categorie inconnue")
        verifie(leve(lw.ajoute, racine, {"url": "https://site.org/x", "note": "a" * 301}), "ValueError", "ajoute refuse : note trop longue")
        verifie(leve(lw.retire, racine, lw.identifiant("https://exemple-public.org/a.pdf")), "KeyError", "retire refuse : lien cite dans un fichier")
        lw.retire(racine, lw.identifiant("https://fiche-publique.org/p"))
        verifie(len(lw.construit(racine)["liens"]), 1, "retire : lien ajoute retire")

        # ---- anti-SSRF
        for u in ("http://127.0.0.1/x", "http://localhost/x", "http://192.168.0.1/x", "http://[::1]/x", "http://169.254.169.254/x", "file:///c:/x", "https://u:p@site.org/"):
            verifie(leve(lw.verifie_hote, u), "ValueError", f"verifie_hote refuse : {u}")

        # ---- archivage
        fp = port_libre()
        srv = ThreadingHTTPServer(("127.0.0.1", fp), Fournisseur)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{fp}"
        try:
            verifie(leve(lw.archive, racine, base + "/f.pdf"), "ValueError", "archive : hote local refuse (temoin anti-SSRF intact)")
            reel = lw.verifie_hote
            lw.verifie_hote = lambda u: None            # neutralise pour tester la suite avec le serveur local
            try:
                a = lw.archive(racine, base + "/f.pdf")
                verifie((a["taille"], (racine / "outils_docs/liens_web/archives" / a["fichier"]).read_bytes()[:5]), (len(PDF), b"%PDF-"), "archive : PDF copie")
                verifie(lw.chemin_archive(racine, a["fichier"]).name, a["fichier"], "chemin_archive : fichier de l'index")
                try:
                    lw.chemin_archive(racine, "..\\..\\CLAUDE.md")
                    sortie = "accepte"
                except LookupError:
                    sortie = "refuse"
                verifie(sortie, "refuse", "chemin_archive : chemin hors index refuse")
                verifie(leve(lw.archive, racine, base + "/faux.pdf"), "ValueError", "archive : contenu qui n'est pas un PDF refuse")
                verifie(leve(lw.archive, racine, base + "/img.png"), "ValueError", "archive : type image refuse")
                lw.MAX_OCTETS = 1000
                verifie(leve(lw.archive, racine, base + "/gros.pdf"), "ValueError", "archive : fichier trop gros refuse")
                lw.MAX_OCTETS = 40 * 1024 * 1024
                verifie(sorted(p.name for p in (racine / "outils_docs/liens_web/archives").glob("*.tmp")), [], "archive : aucun .tmp restant")
            finally:
                lw.verifie_hote = reel
        finally:
            srv.shutdown()
            srv.server_close()

        # ---- routes
        port = port_libre()
        acces = acces_web.Acces(port, True, "Liens web")
        serveur = ThreadingHTTPServer(("127.0.0.1", port), web.fabrique_gestionnaire(acces, racine))
        serveur.daemon_threads = True
        threading.Thread(target=serveur.serve_forever, daemon=True).start()

        def req(methode, chemin, entetes=None, corps=None):
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
            c.request(methode, chemin, body=corps, headers=entetes or {})
            r = c.getresponse()
            donnees = r.read()
            h = {k.lower(): v for k, v in r.getheaders()}
            c.close()
            return r.status, h, donnees

        post = {"Content-Type": "application/json", "X-Liens": "1"}
        try:
            s, h, d = req("GET", "/")
            verifie((s, b"<title>Liens web</title>" in d, b"innerHTML" in d), (200, True, False), "GET / : la page, sans innerHTML")
            s, h, d = req("GET", "/liens")
            verifie((s, len(json.loads(d)["liens"])), (200, 1), "GET /liens : JSON, le lien cite")
            corps = json.dumps({"url": "https://route-publique.org/x", "titre": "R"}).encode()
            verifie(req("POST", "/ajouter", {"Content-Type": "application/json"}, corps)[0], 403, "POST sans X-Liens : refuse")
            verifie(req("POST", "/ajouter", {**post, "Origin": "http://evil.example"}, corps)[0], 403, "POST d'une autre origine : refuse")
            verifie(req("POST", "/ajouter", post, corps)[0], 200, "POST /ajouter : accepte")
            verifie(req("POST", "/ajouter", post, b'{"url": "http://10.0.0.1/x"}')[0], 400, "POST /ajouter : adresse privee 400")
            verifie(req("POST", "/archiver", post, b'{"url": "http://127.0.0.1:1/x.pdf"}')[0], 400, "POST /archiver : hote local 400 (anti-SSRF)")
            verifie(req("POST", "/retirer", post, json.dumps({"id": lw.identifiant("https://route-publique.org/x")}).encode())[0], 200, "POST /retirer : accepte")
            verifie(req("POST", "/inconnue", post, b"{}")[0], 404, "POST route inconnue : 404")
            verifie(req("GET", "/archive/..%2f..%2fCLAUDE.md")[0], 404, "GET /archive : traversee refusee")
            nom = next((racine / "outils_docs/liens_web/archives").glob("*.pdf")).name
            s, h, d = req("GET", "/archive/" + nom)
            verifie((s, h.get("content-type"), h.get("content-security-policy"), d[:5]), (200, "application/pdf", "sandbox", b"%PDF-"), "GET /archive/<nom> : PDF de l'index, sandbox")
            for m in ("PUT", "DELETE", "PATCH"):
                verifie(req(m, "/liens")[0], 405, f"{m} : 405")
            verifie(req("GET", "/", {"Host": "evil.example:80"})[0], 403, "Host hostile : refuse")
            verifie(req("POST", "/regenere", post, b"{}")[0], 200, "POST /regenere : accepte")
            verifie((racine / "LIENS_WEB.md").read_text(encoding="utf-8").startswith("# Liens web du depot"), True, "regenere : LIENS_WEB.md ecrit dans le faux depot")
        finally:
            serveur.shutdown()
            serveur.server_close()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
