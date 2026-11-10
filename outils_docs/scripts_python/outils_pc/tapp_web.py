"""Fabrique d'extensions (page web, port 7980) : creer, verifier et fabriquer un .tapp, puis l'envoyer a une carte.

UTILISATION
    python outils_docs/scripts_python/outils_pc/tapp_web.py [--http 7980] [--local] [--sans-navigateur]
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

Sources dans data/extensions/<nom>/ (tapp_sources.py), archive <nom>.tapp a cote ; envoi (tapp_envoi.py) vers /.extensions/<nom>.tapp.
Rien n'est ecrit ni envoye sans un geste dans la page : l'arreter a tout moment.

Routes (les POST exigent l'en-tete X-Fabrique-Tapp: 1 et la meme origine ; client de ce PC : Host local, parade au DNS rebinding) :
    GET  /               la page (tapp_page.PAGE)
    GET  /extensions     {extensions: [{nom, tapp}], ignores, gabarits: [{id, libelle, explication}], dossier}
    GET  /extension      ?nom= : tapp_sources.detail
    GET  /cartes         {cartes: [{env}]} : les cartes du parc, rien de leur persist
    POST /creer          {nom, gabarit}
    POST /manifeste      {nom, name, version, description, min_tasmota}
    POST /verifie        {nom} -> {points, avertissements, bon} ; ne fabrique rien
    POST /fabrique       {nom} -> {tapp, avertissements}
    POST /envoi/prepare  {nom, env, transport} -> tapp_envoi.prepare
    POST /envoi          {nom, env, jeton, confirme, redemarrer, transport} -> tapp_envoi.envoie
Boutique locale de /ext, PUBLIQUE (une carte n'a pas de jeton), lecture seule, .tapp fabriques et a jour seulement :
    GET  /extensions/extensions.jsonl      une ligne JSON par extension (tapp_sources.depot)
    GET  /extensions/tapp/<nom>.tapp       l'archive ; tout autre chemin sous /extensions/ : 404
    Une carte la lit si son OtaUrl vaut http://<ce PC>:7980/... (extension_manager.be::load_manifest en deduit l'hote) ;
    elle revient au depot officiel si la page ne tourne pas. Ce meme OtaUrl sert a Upgrade par URL : a poser carte par carte.
Refus : 400 (saisie), 404 (extension ou carte inconnue), 403 (acces), 409 (build, jamais d'ecrasement, Fabriquer d'abord, identite, carte muette), 500 (inattendu).
Verrous : VERROU de tapp_sources pour le controle et la fabrication ; un verrou PAR CARTE pour ses lectures et envois, qui durent des
secondes et ne bloquent donc ni le controle ni la fabrication ni une autre carte. Risque restant : un envoi MQTT de l'onglet autoexec de
l'Assistant persist vers la meme carte au meme moment annulerait celui-ci (fsMqtt.be n'a qu'un transfert), autre processus.
Banc : test_tapp_web.py, test_tapp_envoi.py, sonde test_tapp_page_chrome.py.
"""

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import acces_web
from annuaire_outils import hote_autorise
import lieux
import tapp_envoi
import tapp_sources as ts

PORT_DEFAUT = 7980
DEPOT = Path(__file__).resolve().parents[3]
MAX_CORPS = 64 * 1024


def builds_en_cours_defaut():
    import build_serie                          # meme detection que la page build (garde_build du depot)
    return build_serie.builds_en_cours_defaut()


def fabrique_gestionnaire(acces, racine, builds_en_cours):
    verrous_carte = {}

    def verrou_carte(env):
        return verrous_carte.setdefault(env, threading.Lock())     # setdefault : atomique sous le GIL ; env deja controle (carte du parc)

    def traite_post(chemin, d):
        nom = d.get("nom")
        if chemin == "/creer":
            return ts.cree(racine, nom, d.get("gabarit"))
        if chemin == "/manifeste":
            return ts.ecrit_manifeste(racine, nom, d)
        if chemin == "/verifie":
            return ts.verifie(racine, nom)
        if chemin == "/fabrique":
            return ts.fabrique(racine, nom)
        if chemin in ("/envoi/prepare", "/envoi"):
            ts.dossier(racine, nom)
            env, transport = d.get("env"), d.get("transport", "http")
            tapp_envoi.apx._env(racine, {"env": env})   # valide avant de creer un verrou a son nom
            with verrou_carte(env):
                if chemin == "/envoi/prepare":
                    return tapp_envoi.prepare(racine, env, nom, builds_en_cours, transport=transport)
                return tapp_envoi.envoie(racine, env, nom, d.get("jeton"), d.get("confirme"), d.get("redemarrer"), builds_en_cours, transport=transport)
        raise LookupError(chemin)

    class Gestionnaire(BaseHTTPRequestHandler):
        def log_message(self, *args):
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

        def _texte(self, statut, erreur):
            self._envoie(statut, (str(erreur) or type(erreur).__name__).encode("utf-8"))

        def _admis(self):
            """acces.controle, puis le Host d'un client local (DNS rebinding). False : reponse envoyee."""
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
            except (KeyError, IndexError) as erreur:       # LookupError, mais un bogue : pas un « introuvable »
                self._texte(500, f"erreur inattendue : {type(erreur).__name__} : {erreur}")
            except LookupError as erreur:
                self._texte(404, erreur)
            except (ValueError, TypeError, RecursionError) as erreur:    # RecursionError : JSON trop imbrique
                self._texte(400, erreur)
            except RuntimeError as erreur:
                self._texte(409, erreur)
            except Exception as erreur:
                self._texte(500, f"erreur inattendue : {type(erreur).__name__} : {erreur}")

        def do_GET(self):
            chemin = urlsplit(self.path).path
            if chemin.startswith("/extensions/"):          # boutique de /ext : une carte n'a pas de jeton -> public, lecture seule
                self._boutique(chemin)
            elif self._admis():
                self._erreurs(self._get)

        def _boutique(self, chemin):
            """Seulement des .tapp fabriques et a jour (ts.depot, ts.archive) ; tout le reste, nom hostile compris : 404."""
            if chemin == "/extensions/extensions.jsonl":
                return self._envoie(200, ts.depot(racine).encode("utf-8"), "text/plain; charset=utf-8")
            nom = chemin[len("/extensions/tapp/"):-len(".tapp")] if chemin.startswith("/extensions/tapp/") and chemin.endswith(".tapp") else ""
            try:
                octets = ts.archive(racine, nom)
            except (ValueError, LookupError, RuntimeError, OSError):
                return self._envoie(404, b"introuvable")
            self._envoie(200, octets, "application/octet-stream")

        def _get(self):
            url = urlsplit(self.path)
            if url.path == "/":
                import tapp_page
                self._envoie(200, tapp_page.PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif url.path == "/extensions":
                gabarits = [{"id": k, "libelle": g["libelle"], "explication": g["explication"]} for k, g in ts.GABARITS.items()]
                self._json({**ts.liste(racine), "gabarits": gabarits, "dossier": ts.DOSSIER})
            elif url.path == "/extension":
                self._json(ts.detail(racine, parse_qs(url.query, keep_blank_values=True).get("nom", [None])[0]))
            elif url.path == "/cartes":
                self._json({"cartes": [{"env": e, "lieu": lieux.lieu(e)} for e in tapp_envoi.cartes(racine)], **lieux.pour_page()})
            else:
                self._envoie(404, b"introuvable")

        def do_POST(self):
            if not self._admis():
                return
            if self.headers.get("X-Fabrique-Tapp") != "1" or not acces.origine_autorisee(self):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return
            self._erreurs(self._post)

        def _post(self):
            longueur = int(self.headers.get("Content-Length", "0") or 0)
            if not 0 <= longueur <= MAX_CORPS:            # negatif : read(-1) lirait jusqu'a la fermeture
                self.close_connection = True              # corps non lu : la connexion ne doit pas resservir
                raise ValueError(f"Content-Length hors 0..{MAX_CORPS}")
            demande = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
            if not isinstance(demande, dict):
                raise ValueError("corps JSON attendu")
            self._json(traite_post(urlsplit(self.path).path, demande))

    return Gestionnaire


def principal():
    options = argparse.ArgumentParser(description="Fabrique d'extensions : creer, verifier, fabriquer et envoyer un .tapp.")
    options.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(options)
    args = options.parse_args()
    acces = acces_web.Acces(args.http, args.local, "Fabrique d'extensions")
    try:
        serveur = ThreadingHTTPServer((acces.hote, args.http), fabrique_gestionnaire(acces, DEPOT, builds_en_cours_defaut))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (rien n'est ecrit ni envoye sans un geste dans la page).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
