"""Cartes simulees (page web, port 7940) : lancer et arreter la simulation d'une carte du parc hors ligne.

UTILISATION
    python outils_docs/scripts_python/outils_pc/cartes_simulees_web.py [--http 7940] [--local] [--sans-navigateur]
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

Chaque carte lancee est un serveur de cartes_simulees.py sur 127.0.0.1 au port web de la vraie carte (8080 + id - 1 derriere un maitre,
8082 pour le rideau du garage). Rien n'est ecrit dans le depot. Une carte qui REPOND sur le reseau n'est jamais simulee (refus 409) :
la simulation sert les cartes hors ligne. MQTT n'est jamais connecte (cartes_simulees_reseau.py).

Routes (les POST exigent l'en-tete X-Cartes-Simulees: 1 et la meme origine) :
    GET  /          la page (cartes_simulees_page.PAGE)
    GET  /etat      {cartes: [{env, nom, adresse, berry, lancee, port, url}]}
    POST /lance     {env}   -> {message, url}
    POST /arrete    {env}
Refus : 400 (saisie), 403 (acces), 404 (carte inconnue), 409 (deja lancee, carte en ligne, port occupe), 500 (inattendu).
Banc : test_cartes_simulees_web.py.
"""

import argparse
import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import acces_web
import cartes_simulees as cs
from annuaire_outils import hote_autorise

PORT_DEFAUT = 7940
MAX_CORPS = 4 * 1024
ENTETE = "X-Cartes-Simulees"


def en_ligne(adresse, delai=1.5):
    """True si la carte repond (connexion TCP a son adresse du parc, IP ou IP:port, port 80 par defaut)."""
    hote, _, port = (adresse or "").partition(":")
    if not hote:
        return False
    try:
        socket.create_connection((hote, int(port or 80)), timeout=delai).close()
        return True
    except (OSError, ValueError):
        return False


class Etat:
    """Les cartes lancees par cette page : {env: serveur HTTP}."""

    def __init__(self, test_en_ligne=en_ligne, fabrique=None):
        self.lances = {}
        self.test_en_ligne = test_en_ligne
        self.fabrique = fabrique or cs.serveur            # (env, port) -> serveur ; remplacable par les bancs
        self._verrou = threading.Lock()

    def _carte(self, env):
        c = cs.inventaire().get(env) if isinstance(env, str) else None
        if c is None:
            raise LookupError("carte inconnue")
        return c

    def cartes(self):
        sortie = []
        for c in cs.liste():
            p = cs.profil_reseau(c["env"])
            srv = self.lances.get(c["env"])
            port = srv.server_address[1] if srv else p["port_web"]
            sortie.append({"env": c["env"], "nom": p["nom"] or c["env"], "adresse": c["adresse"], "berry": c["berry"],
                           "lancee": srv is not None, "port": port, "url": f"http://127.0.0.1:{port}/" if srv else None})
        return sortie

    def lance(self, env):
        c = self._carte(env)
        with self._verrou:
            if env in self.lances:
                raise RuntimeError("deja lancee")
            if self.test_en_ligne(c["adresse"]):
                raise RuntimeError(f"la carte repond sur {c['adresse']} : une carte en ligne ne se simule pas")
            port = cs.profil_reseau(env)["port_web"]
            try:
                srv = self.fabrique(env, port)
            except OSError as e:
                raise RuntimeError(f"port {port} indisponible : {e}") from e
            srv.daemon_threads = True
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            self.lances[env] = srv
        return {"message": "lancee", "url": f"http://127.0.0.1:{srv.server_address[1]}/"}

    def arrete(self, env):
        self._carte(env)
        with self._verrou:
            srv = self.lances.pop(env, None)
        if srv is None:
            raise RuntimeError("pas lancee")
        srv.shutdown()
        srv.server_close()
        return {"message": "arretee"}

    def arrete_tout(self):
        for env in list(self.lances):
            try:
                self.arrete(env)
            except (RuntimeError, LookupError):
                pass


def fabrique_gestionnaire(acces, etat):
    class Gestionnaire(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002
            pass

        def _envoie(self, statut, corps, type_mime="text/plain; charset=utf-8"):
            self.send_response(statut)
            self.send_header("Content-Type", type_mime)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corps)

        def _json(self, donnees):
            self._envoie(200, json.dumps(donnees, ensure_ascii=False).encode("utf-8"), "application/json")

        def _admis(self):
            if not acces.controle(self):
                return False
            if not hote_autorise(self, acces.port):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return False
            return True

        def _erreurs(self, traitement):
            try:
                traitement()
            except LookupError as e:
                self._envoie(404, str(e).encode("utf-8"))
            except (ValueError, TypeError) as e:
                self._envoie(400, str(e).encode("utf-8"))
            except RuntimeError as e:
                self._envoie(409, str(e).encode("utf-8"))
            except Exception as e:  # noqa: BLE001
                self._envoie(500, f"erreur inattendue : {type(e).__name__} : {e}".encode("utf-8"))

        def do_GET(self):
            if self._admis():
                self._erreurs(self._get)

        def _get(self):
            chemin = urlsplit(self.path).path
            if chemin == "/":
                import cartes_simulees_page
                self._envoie(200, acces.habille(cartes_simulees_page.PAGE).encode("utf-8"), "text/html; charset=utf-8")
            elif chemin == "/etat":
                self._json({"cartes": etat.cartes()})
            else:
                self._envoie(404, b"introuvable")

        def do_POST(self):
            if not self._admis():
                return
            if self.headers.get(ENTETE) != "1" or not acces.origine_autorisee(self):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return
            self._erreurs(self._post)

        def _post(self):
            longueur = int(self.headers.get("Content-Length", "0") or 0)
            if not 0 <= longueur <= MAX_CORPS:
                self.close_connection = True
                raise ValueError(f"Content-Length hors 0..{MAX_CORPS}")
            d = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
            if not isinstance(d, dict):
                raise ValueError("corps JSON attendu")
            chemin = urlsplit(self.path).path
            if chemin == "/lance":
                self._json(etat.lance(d.get("env")))
            elif chemin == "/arrete":
                self._json(etat.arrete(d.get("env")))
            else:
                self._envoie(404, b"introuvable")

    return Gestionnaire


def principal():
    opt = argparse.ArgumentParser(description="Cartes simulees : lancer et arreter la simulation d'une carte hors ligne.")
    opt.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(opt)
    args = opt.parse_args()
    acces = acces_web.Acces(args.http, args.local, "Cartes simulees")
    etat = Etat()
    try:
        serveur = ThreadingHTTPServer((acces.hote, args.http), fabrique_gestionnaire(acces, etat))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (les cartes lancees s'arretent avec l'outil ; rien n'est ecrit dans le depot).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        etat.arrete_tout()
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
