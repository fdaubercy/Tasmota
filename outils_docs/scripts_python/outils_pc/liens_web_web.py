"""Liens web (page web, port 7905) : liens cites dans le depot, liens ajoutes, archives PDF des fiches.

UTILISATION
    python outils_docs/scripts_python/outils_pc/liens_web_web.py [--http 7905] [--local] [--sans-navigateur]
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

Routes (client de ce PC : Host local, parade au DNS rebinding) :
    GET  /                   la page (liens_web_page.PAGE)
    GET  /liens              liens_web.construit(depot), recalcule a chaque appel
    GET  /archive/<fichier>  un PDF de l'index des archives (jamais un chemin libre)
    POST /ajouter /retirer /archiver /regenere   ECRIVENT dans le depot (ou telechargent) : ce PC seulement,
         en-tete X-Liens: 1 et meme origine. /archiver : hote public seulement (anti-SSRF, voir liens_web.verifie_hote).
Banc : test_liens_web.py.
"""

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import acces_web
import liens_web
from annuaire_outils import hote_autorise

PORT_DEFAUT = 7905
DEPOT = Path(__file__).resolve().parents[3]
ENTETE = "X-Liens"
MAX_CORPS = 8192
CSP = ("default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; "
       "connect-src 'self'; manifest-src 'self'; worker-src 'self'; base-uri 'none'; form-action 'none'")


def fabrique_gestionnaire(acces, racine):
    class Gestionnaire(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _envoie(self, statut, corps, type_mime="text/plain; charset=utf-8", csp=CSP):
            self.send_response(statut)
            self.send_header("Content-Type", type_mime)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", csp)
            self.end_headers()
            self.wfile.write(corps)

        def _json(self, donnees, statut=200):
            self._envoie(statut, json.dumps(donnees, ensure_ascii=False).encode("utf-8"), "application/json")

        def _admis(self):
            if not acces.controle(self):
                return False
            if not hote_autorise(self, acces.port):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return False
            return True

        def do_GET(self):
            if not self._admis():
                return
            chemin = urlsplit(self.path).path
            try:
                if chemin == "/":
                    import liens_web_page
                    self._envoie(200, acces.habille(liens_web_page.PAGE).encode("utf-8"), "text/html; charset=utf-8")
                elif chemin == "/liens":
                    self._json(liens_web.construit(racine))
                elif chemin.startswith("/archive/"):
                    pdf = liens_web.chemin_archive(racine, unquote(chemin[len("/archive/"):]))
                    self._envoie(200, pdf.read_bytes(), "application/pdf", "sandbox")
                else:
                    self._envoie(404, b"introuvable")
            except LookupError as erreur:
                self._envoie(404, str(erreur).encode("utf-8"))
            except Exception as erreur:
                self._envoie(500, f"erreur inattendue : {type(erreur).__name__} : {erreur}".encode("utf-8"))

        def do_POST(self):
            if not self._admis():
                return
            if (self.headers.get(ENTETE) != "1" or not acces.origine_autorisee(self)
                    or not acces_web.est_local(self.client_address)):    # ecrit et telecharge : ce PC seulement
                self.close_connection = True
                self._envoie(403, b"refuse")
                return
            try:
                longueur = int(self.headers.get("Content-Length", "0") or 0)
                if not 0 <= longueur <= MAX_CORPS:
                    self.close_connection = True
                    raise ValueError(f"Content-Length hors 0..{MAX_CORPS}")
                d = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
                if not isinstance(d, dict):
                    raise ValueError("corps JSON attendu")
                chemin = urlsplit(self.path).path
                if chemin == "/ajouter":
                    self._json(liens_web.ajoute(racine, d))
                elif chemin == "/retirer":
                    liens_web.retire(racine, str(d.get("id", "")))
                    self._json({"ok": True})
                elif chemin == "/archiver":
                    self._json(liens_web.archive(racine, str(d.get("url", ""))))
                elif chemin == "/regenere":
                    self._json({"lignes": liens_web.regenere_document(racine)})
                else:
                    self._envoie(404, b"introuvable")
            except (ValueError, KeyError) as erreur:
                self._envoie(400, str(erreur.args[0] if erreur.args else erreur).encode("utf-8"))
            except Exception as erreur:
                self._envoie(500, f"erreur inattendue : {type(erreur).__name__} : {erreur}".encode("utf-8"))

        def _refuse(self):
            self.close_connection = True
            self._envoie(405, b"methode refusee")

        do_PUT = do_DELETE = do_PATCH = _refuse

    return Gestionnaire


def principal():
    opt = argparse.ArgumentParser(description="Liens web du depot : liste, ajout, archivage PDF des fiches.")
    opt.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(opt)
    args = opt.parse_args()
    acces = acces_web.Acces(args.http, args.local, "Liens web")
    try:
        serveur = ThreadingHTTPServer((acces.hote, args.http), fabrique_gestionnaire(acces, DEPOT))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter. Ecrit dans outils_docs/liens_web/ (ajouts, archives) sur geste de la page.", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
