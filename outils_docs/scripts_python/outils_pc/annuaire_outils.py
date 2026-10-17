"""Annuaire des outils PC (port 7600) : liste, lance et arrete les outils de ce dossier depuis une page web.

    python outils_docs/scripts_python/outils_pc/annuaire_outils.py [--http 7600] [--local] [--sans-navigateur]

Acces : acces_web.py (ce PC sans jeton ; autre appareil avec le jeton du lien affiche). En plus, pour un
client de CE PC, l'en-tete Host doit etre 127.0.0.1:<port>, localhost:<port> ou [::1]:<port> (403 sinon) :
parade au DNS rebinding (une page dont le domaine se resout en 127.0.0.1 lirait sinon /etat et son jeton).
Le navigateur est ouvert HORS du Job Object (cmd /c start, CREATE_BREAKAWAY_FROM_JOB) : sinon il mourrait
avec l'annuaire.
Routes (toutes derriere acces.controle et le controle du Host) :
    GET  /          la page            GET /registre   le registre des outils (annuaire_registre.en_json)
    GET  /etat      etat des outils + derniers parametres lances + liens reseau (client local seulement)
    GET  /ports     ports serie detectes, avec l'outil qui le tient (tenu_par)
    GET  /console?id=<id>   dernieres lignes de la console de l'outil lance par l'annuaire
    POST /lance     {"id", "valeurs"}   POST /arrete   {"id"}
                    -> en-tete X-Annuaire: 1 et origine autorisee exiges (403 sinon)
Un second lancement sur le meme port sort en code 0 sans rien afficher (l'annuaire tourne deja).
"""

import argparse
import json
import http.client
import os
import socket
import subprocess
import sys
import threading
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import acces_web
import annuaire_presence as pre
import annuaire_registre as reg
from annuaire_page import PAGE
from annuaire_lanceur import (CREATE_BREAKAWAY_FROM_JOB, CREATE_NO_WINDOW, ERROR_ACCESS_DENIED, Lanceur,
                              rattache_au_job)

PORT_DEFAUT = 7600
NOM_ACCES = "Annuaire des outils"
RACINE = Path(__file__).resolve().parents[3]
GIT = RACINE / ".git"
SANS_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # 127.0.0.1 : jamais de proxy
TAILLE_MAX = 64 * 1024
MSG_SYNCHRO = "Une operation de synchro est en cours : arret refuse"
MSG_ARRET = "Arret non confirme : le processus vit encore"


class Serveur(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def server_bind(self):
        # Windows : adresse exclusive. Sans elle, un autre programme lie a 127.0.0.1:port n'empeche pas
        # ce bind sur 0.0.0.0, et SO_REUSEADDR laisserait deux annuaires sur le meme port.
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def liste_ports():
    """Ports serie presents ; [] si pyserial manque ou si la detection echoue (jamais d'exception)."""
    try:
        import pont_serie
        return pont_serie.liste_ports()
    except Exception:            # ImportError (pyserial absent) comme toute erreur de detection
        return []


def operation_git_en_cours(git=None):
    """True si le depot a une fusion ou un rebase en cours (MERGE_HEAD, rebase-merge/, rebase-apply/)."""
    git = Path(GIT if git is None else git)
    return (git / "MERGE_HEAD").exists() or (git / "rebase-merge").is_dir() or (git / "rebase-apply").is_dir()


def route_occupee(port, route, git=None):
    """True si GET 127.0.0.1:port+route repond en_cours: true.

    Si l'outil ne repond pas utilement (delai, erreur, reponse non JSON), on ne laisse pas arreter a
    l'aveugle : le depot tranche (operation_git_en_cours).
    """
    try:
        with SANS_PROXY.open(f"http://127.0.0.1:{int(port)}{route}", timeout=2) as r:
            return bool(json.loads(r.read().decode("utf-8")).get("en_cours"))
    except (OSError, ValueError, TypeError, AttributeError, http.client.HTTPException):
        return operation_git_en_cours(git)


def hote_autorise(handler, port):
    """Client de ce PC : Host doit nommer la boucle locale et notre port. Autre appareil : True (jeton)."""
    if not acces_web.est_local(handler.client_address):
        return True
    hote = (handler.headers.get("Host", "") or "").strip().lower()
    return hote in {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}


def ouvre_navigateur(url, popen=subprocess.Popen):
    """Ouvre url HORS du job de l'annuaire (cmd /c start + breakaway), sinon le navigateur, s'il demarre
    a cette occasion, mourrait avec l'annuaire. Job parent sans breakaway (erreur 5) : sans le drapeau."""
    if os.name != "nt":
        webbrowser.open(url)
        return
    commande = ["cmd", "/c", "start", "", url]
    options = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        try:
            popen(commande, creationflags=CREATE_BREAKAWAY_FROM_JOB | CREATE_NO_WINDOW, **options)
        except OSError as e:
            if getattr(e, "winerror", None) != ERROR_ACCESS_DENIED:
                raise
            popen(commande, creationflags=CREATE_NO_WINDOW, **options)
    except OSError as e:
        print(f"   (navigateur non ouvert : {e})", flush=True)


def fabrique_gestionnaire(lanceur, acces, git=None):
    verrou_lance = threading.Lock()      # verification "deja en marche" + validation + lancement : un a la fois

    class Gestionnaire(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def _envoie(self, statut, corps, type_mime="application/json"):
            self.send_response(statut)
            self.send_header("Content-Type", type_mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corps)

        def _json(self, donnees, statut=200):
            self._envoie(statut, json.dumps(donnees, ensure_ascii=False).encode("utf-8"))

        def _erreur(self, statut, message):
            self._json({"erreur": message}, statut)

        def _controle(self):
            """acces.controle, puis le Host d'un client local (DNS rebinding). False : reponse envoyee."""
            if not acces.controle(self):
                return False
            if not hote_autorise(self, acces.port):
                self.close_connection = True
                self._erreur(403, "Hote refuse")
                return False
            return True

        def _hote_client(self):
            if acces_web.est_local(self.client_address):
                return None
            return (self.headers.get("Host", "") or "").rsplit(":", 1)[0] or None

        def _etat(self):
            return pre.etat_outils(lanceur.lances, lanceur.derniers(), self._hote_client())

        def _ports(self):
            tenus = {}
            for id, info in list(lanceur.lances.items()):     # copie : un POST concurrent modifie lances
                if pre.pid_vivant(info.get("pid")):
                    for v in (info.get("valeurs") or {}).values():
                        tenus[str(v)] = reg.par_id(id).nom
            return [dict(p, tenu_par=tenus.get(p["port"])) for p in liste_ports()]

        def do_GET(self):
            if not self._controle():
                return
            url = urlsplit(self.path)
            if url.path == "/":
                self._envoie(200, PAGE.encode("utf-8"), "text/html")
            elif url.path == "/registre":
                self._json(reg.en_json())
            elif url.path == "/etat":
                local = acces_web.est_local(self.client_address)
                self._json({"outils": self._etat(), "liens_reseau": acces.liens_reseau() if local else [],
                            "derniers": lanceur.derniers()})
            elif url.path == "/ports":
                self._json(self._ports())
            elif url.path == "/console":
                id = parse_qs(url.query).get("id", [""])[0]
                try:
                    reg.par_id(id)
                except KeyError:
                    return self._erreur(404, "Outil inconnu")
                self._json({"lignes": lanceur.console(id)})
            else:
                self._erreur(404, "introuvable")

        def do_POST(self):
            if not self._controle():
                return
            if self.headers.get("X-Annuaire") != "1" or not acces.origine_autorisee(self):
                self.close_connection = True
                return self._erreur(403, "Refuse")
            chemin = urlsplit(self.path).path
            if chemin not in ("/lance", "/arrete"):
                return self._erreur(404, "introuvable")
            try:
                longueur = min(int(self.headers.get("Content-Length", "0") or 0), TAILLE_MAX)
                demande = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
                if not isinstance(demande, dict):
                    raise ValueError("corps JSON attendu")
            except (ValueError, UnicodeDecodeError):
                return self._erreur(400, "Corps JSON invalide")
            try:
                outil = reg.par_id(str(demande.get("id", "")))
            except KeyError:
                return self._erreur(404, "Outil inconnu")
            if chemin == "/lance":
                with verrou_lance:
                    self._lance(outil, demande.get("valeurs"))
            else:
                self._arrete(outil, next(e for e in self._etat() if e["id"] == outil.id))

        def _lance(self, outil, valeurs):
            tous = self._etat()          # une seule fois : etat et ponts viennent du meme instantane
            etat = next(e for e in tous if e["id"] == outil.id)
            if valeurs is None:
                valeurs = {}
            if not isinstance(valeurs, dict):
                return self._erreur(400, "valeurs : objet attendu")
            connu = lanceur.lances.get(outil.id)
            if etat["etat"] == "marche" or (connu and pre.pid_vivant(connu["pid"])):
                return self._erreur(409, f"{outil.nom} est deja en marche")
            ponts = [e["port"] for e in tous if e["id"] == "pont_serie" and e["etat"] == "marche"]
            try:
                args = reg.valide(outil, valeurs, [p["port"] for p in liste_ports()], ponts)
            except ValueError as e:
                return self._erreur(400, str(e))
            try:
                pid = lanceur.lance(outil, args, valeurs)
            except OSError as e:
                return self._erreur(500, f"Lancement impossible : {e}")
            self._json({"pid": pid})

        def _arrete(self, outil, etat):
            if not etat["peut_arreter"]:
                return self._erreur(409, f"{outil.nom} n'a pas ete lance par l'annuaire : "
                                         "l'arreter depuis son terminal")
            if outil.route_occupe and route_occupee(etat["port"], outil.route_occupe, git):
                return self._erreur(409, MSG_SYNCHRO)
            connu = lanceur.lances.get(outil.id)
            fiche = pre.lit_fiches().get(outil.nom_acces)
            pid = connu["pid"] if connu else (fiche or {}).get("pid")
            if not pid:
                return self._erreur(409, "PID introuvable")
            if not lanceur.arrete(outil, pid):
                return self._erreur(500, MSG_ARRET)
            self._json({"ok": True})

    return Gestionnaire


def annuaire_deja_actif(port):
    """True si la fiche du port est celle d'un annuaire vivant."""
    try:
        with open(acces_web.dossier_presence() / f"{port}.json", encoding="utf-8") as f:
            fiche = json.load(f)
        return fiche.get("nom") == NOM_ACCES and pre.pid_vivant(fiche.get("pid"))
    except (OSError, ValueError, AttributeError):
        return False


def principal():
    options = argparse.ArgumentParser(description="Annuaire des outils PC : liste, lance et arrete les outils.")
    options.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(options)
    args = options.parse_args()

    acces = acces_web.Acces(args.http, args.local, NOM_ACCES)
    lanceur = Lanceur(RACINE)
    rattache_au_job()
    try:
        serveur = Serveur((acces.hote, args.http), fabrique_gestionnaire(lanceur, acces))
    except OSError:
        if annuaire_deja_actif(args.http):
            # Deja demarre (tache VS Code) : sans --sans-navigateur (cible Custom, lancement a la
            # main), on ouvre sa page plutot que de rendre la main sans rien montrer.
            if not args.sans_navigateur:
                print(f"Annuaire deja demarre : {acces.lien_local()} ouvert dans le navigateur", flush=True)
                ouvre_navigateur(acces.lien_local())
            return 0
        print(f"Port {args.http} deja utilise par un autre programme", flush=True)
        return 1
    acces.annonce(False)                 # pas webbrowser.open : il ouvrirait le navigateur DANS le job
    if not args.sans_navigateur:
        ouvre_navigateur(acces.lien_local())
    print("Ctrl+C pour arreter (les outils lances par l'annuaire s'arretent avec lui).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
