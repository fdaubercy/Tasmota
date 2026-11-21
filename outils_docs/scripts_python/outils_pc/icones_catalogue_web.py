"""Catalogue d'icones (page web, port 7930) : glyphes du firmware, PNG du depot, sites de l'annuaire. LECTURE SEULE : aucune route POST, rien n'est ecrit.

UTILISATION
    python outils_docs/scripts_python/outils_pc/icones_catalogue_web.py [--http 7930] [--local] [--sans-navigateur]
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

Routes (GET seulement ; client de ce PC : Host local, parade au DNS rebinding) :
    GET /           la page (icones_catalogue_page.PAGE)
    GET /catalogue  icones_catalogue.construit(depot), recalcule a chaque appel
    GET /lib/mdi.ttf  la police MDI du depot (dessine les glyphes, aucun CDN)
Tout autre verbe : 405. Banc : test_icones_catalogue_web.py.
"""

import argparse
import json
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import acces_web
import atelier_ecrans_icones as ic
import icones_catalogue
from annuaire_outils import hote_autorise

PORT_DEFAUT = 7930
DEPOT = Path(__file__).resolve().parents[3]
# 'self' pour le service worker de repli et le manifeste ajoutes par acces_web.habille ; aucune ressource externe.
CSP = ("default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
       "connect-src 'self'; manifest-src 'self'; worker-src 'self'; base-uri 'none'; form-action 'none'")


class ServeurIcones(ThreadingHTTPServer):
    allow_reuse_address = False      # HTTPServer l'active : sous Windows, deux instances se liaient alors au meme port

    def server_bind(self):
        # Windows : adresse exclusive (comme ftp_cartes_web.ServeurFtp et annuaire_outils.Serveur).
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def fabrique_gestionnaire(acces, racine):
    class Gestionnaire(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _envoie(self, statut, corps, type_mime="text/plain; charset=utf-8"):
            self.send_response(statut)
            self.send_header("Content-Type", type_mime)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", CSP)
            self.end_headers()
            self.wfile.write(corps)

        def do_GET(self):
            if not acces.controle(self):
                return
            if not hote_autorise(self, acces.port):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return
            chemin = urlsplit(self.path).path
            try:
                if chemin == "/":
                    import icones_catalogue_page
                    self._envoie(200, acces.habille(icones_catalogue_page.PAGE).encode("utf-8"), "text/html; charset=utf-8")
                elif chemin == "/catalogue":
                    self._envoie(200, json.dumps(icones_catalogue.construit(racine), ensure_ascii=False).encode("utf-8"), "application/json")
                elif chemin == "/lib/mdi.ttf":
                    self._envoie(200, ic.police(racine), "font/ttf")
                else:
                    self._envoie(404, b"introuvable")
            except LookupError as erreur:
                self._envoie(404, str(erreur).encode("utf-8"))
            except Exception as erreur:
                self._envoie(500, f"erreur inattendue : {type(erreur).__name__} : {erreur}".encode("utf-8"))

        def _refuse(self):
            self.close_connection = True
            self._envoie(405, b"lecture seule")

        do_POST = do_PUT = do_DELETE = do_PATCH = _refuse

    return Gestionnaire


def principal():
    opt = argparse.ArgumentParser(description="Catalogue d'icones : glyphes du firmware, PNG du depot, sites (lecture seule).")
    opt.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(opt)
    args = opt.parse_args()
    acces = acces_web.Acces(args.http, args.local, "Catalogue d'icones")
    try:
        serveur = ServeurIcones((acces.hote, args.http), fabrique_gestionnaire(acces, DEPOT))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (rien n'est ecrit dans le depot).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
