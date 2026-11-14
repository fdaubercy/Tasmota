"""Atelier des visuels d'accueil (page web, port 7990) : serveur du fond (nettoyage, poids) ; page et points chauds a venir.

UTILISATION
    python outils_docs/scripts_python/outils_pc/atelier_visuels_web.py [--http 7990] [--local] [--sans-navigateur]
    Regle d'acces : acces_web.py. Rien n'est ecrit au depot ; les fonds restent en memoire du serveur.

Routes (le POST exige l'en-tete X-Atelier-Visuels: 1 et la meme origine ; client local : Host local) :
    GET  /          la page          GET /envs     {envs: [{env, lieu, puce}], lieux}
    GET  /lib.js    ImageTracer      GET /visuel.js  data/sd/js/visuel.js (404 s'il n'existe pas encore)
    POST /fond?env=&type=svg|webp|jpg   corps binaire brut, 1 Mo au plus -> {empreinte, octets, avertissement}
    GET  /fond?env=&empreinte=          le fond garde (20 au plus, le plus ancien evince)
Routes des modules autonomes : atelier_visuels_web_routes.py (icones, IA, ecriture, suivi).
Refus : 400 (saisie, SVG dangereux, fond trop lourd), 403, 404, 408 (corps POST trop lent, 10 s), 409 (build, depot change), 413 (corps), 500, 503 (Iconify injoignable). Banc : test_atelier_visuels_web.py.
"""

import argparse
import hashlib
import json
import sys
import threading
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import acces_web
import atelier_visuels_fond as avf
from annuaire_outils import hote_autorise
import lieux
import tapp_envoi
import atelier_visuels_web_routes as routes

PORT_DEFAUT = 7990
DEPOT = Path(__file__).resolve().parents[3]
MAX_CORPS = 1024 * 1024
MAX_FONDS = 20
DELAI_SOCKET = 10
MIME = {"svg": "image/svg+xml", "webp": "image/webp", "jpg": "image/jpeg"}
LIB = Path("outils_docs/visuels_accueil/lib/imagetracer_v1.2.6.js")
VISUEL_JS = Path("data/sd/js/visuel.js")


def fabrique_gestionnaire(acces, racine, **injections):
    """injections (banc) : builds_en_cours, ouvre, cache_icones, config_fichier, fabrique_ia, lecteur."""
    fonds = OrderedDict()             # empreinte -> (type, octets)
    verrou = threading.Lock()
    route_get, route_post = routes.fabrique_routes(racine, fonds, verrou, **injections)

    def env_valide(env):
        if env not in tapp_envoi.cartes(racine):
            raise LookupError(f"carte inconnue : {env!r}")
        return env

    class Gestionnaire(BaseHTTPRequestHandler):
        timeout = DELAI_SOCKET            # un client lent ne garde pas un thread

        def log_message(self, *args):
            pass

        def _envoie(self, statut, corps, type_mime="text/plain; charset=utf-8", entetes=()):
            self.send_response(statut)
            for k, v in entetes:
                self.send_header(k, v)
            self.send_header("Content-Type", type_mime)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corps)

        def _erreurs(self, traitement):
            try:
                traitement()
            except LookupError as e:
                self._envoie(404, str(e).encode("utf-8"))
            except ValueError as e:
                self._envoie(400, str(e).encode("utf-8"))
            except RuntimeError as e:
                self._envoie(409, str(e).encode("utf-8"))
            except TimeoutError:
                self.close_connection = True
                self._envoie(408, b"corps trop lent")
            except routes.HorsLigne as e:
                self._envoie(503, str(e).encode("utf-8"))
            except Exception as e:
                self._envoie(500, f"erreur inattendue : {type(e).__name__} : {e}".encode("utf-8"))

        def _admis(self):
            if not acces.controle(self):
                return False
            if not hote_autorise(self, acces.port):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return False
            return True

        def do_GET(self):
            if self._admis():
                self._erreurs(self._get)

        def _get(self):
            url = urlsplit(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query, keep_blank_values=True).items()}
            if url.path == "/":
                import atelier_visuels_page
                self._envoie(200, atelier_visuels_page.PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif url.path == "/envs":
                envs = [{"env": e, "lieu": lieux.lieu(e), "puce": lieux.puce(e)} for e in tapp_envoi.cartes(racine)]
                self._envoie(200, json.dumps({"envs": envs, **lieux.pour_page()}, ensure_ascii=False).encode("utf-8"), "application/json")
            elif url.path in ("/lib.js", "/visuel.js"):
                f = racine / (LIB if url.path == "/lib.js" else VISUEL_JS)
                if not f.is_file():
                    raise LookupError("introuvable")
                self._envoie(200, f.read_bytes(), "text/javascript; charset=utf-8")
            elif url.path == "/fond":
                env_valide(q.get("env"))
                with verrou:
                    trouve = fonds.get(q.get("empreinte"))
                if trouve is None:
                    raise LookupError("fond inconnu")
                self._envoie(200, trouve[1], MIME[trouve[0]], (("Content-Security-Policy", "sandbox"), ("X-Content-Type-Options", "nosniff")))
            elif url.path in routes.ROUTES_GET:
                self._json(route_get(url.path, q))
            else:
                self._envoie(404, b"introuvable")

        def _json(self, objet):
            self._envoie(200, json.dumps(objet, ensure_ascii=False).encode("utf-8"), "application/json")

        def do_POST(self):
            if not self._admis():
                return
            if self.headers.get("X-Atelier-Visuels") != "1" or not acces.origine_autorisee(self):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return
            self._erreurs(self._post)

        def _post(self):
            url = urlsplit(self.path)
            if url.path != "/fond" and url.path not in routes.ROUTES_POST:
                raise LookupError("introuvable")
            maxi = routes.MAX_CORPS_IA if url.path in routes.CHEMINS_IA else MAX_CORPS
            try:
                longueur = int(self.headers.get("Content-Length", "0") or 0)
            except ValueError:
                longueur = -1
            if not 0 <= longueur <= maxi:
                self.close_connection = True              # corps non lu
                self._envoie(413, f"corps de plus de {maxi} octets".encode("utf-8"))
                return
            if url.path != "/fond":
                q = {k: v[0] for k, v in parse_qs(url.query, keep_blank_values=True).items()}
                self._json(route_post(url.path, q, self.rfile.read(longueur)))
                return
            q = {k: v[0] for k, v in parse_qs(url.query, keep_blank_values=True).items()}
            env, type_ = env_valide(q.get("env")), q.get("type")
            octets = self.rfile.read(longueur)
            if type_ == "svg":
                octets = avf.nettoie_svg(octets.decode("utf-8")).encode("utf-8")
            puce = lieux.puce(env)
            message = avf.controle_fond(type_, octets, puce)
            if avf.refuse(octets, puce):
                raise ValueError(message)
            empreinte = hashlib.sha256(octets).hexdigest()
            with verrou:
                fonds[empreinte] = (type_, octets)
                fonds.move_to_end(empreinte)
                while len(fonds) > MAX_FONDS:
                    fonds.popitem(last=False)
            self._envoie(200, json.dumps({"empreinte": empreinte, "octets": len(octets), "avertissement": message}).encode("utf-8"), "application/json")

    return Gestionnaire


def principal():
    options = argparse.ArgumentParser(description="Atelier des visuels d'accueil.")
    options.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(options)
    args = options.parse_args()
    acces = acces_web.Acces(args.http, args.local, "Atelier des visuels")
    try:
        serveur = ThreadingHTTPServer((acces.hote, args.http), fabrique_gestionnaire(acces, DEPOT))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (rien n'est ecrit au depot).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
