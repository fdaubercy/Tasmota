"""Navigateur FTP des cartes (page web, port 7450) : parcourir, telecharger, envoyer, supprimer les fichiers d'une carte par FTP.

UTILISATION
    python outils_docs/scripts_python/outils_pc/ftp_cartes_web.py [--http 7450] [--local] [--sans-navigateur]
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

Le FTP de la carte est allume a la demande (`UfsFTP`, ftp_cartes_session.py) et eteint a chaque fin de session : « Deconnecter », changement
de carte, fermeture de la DERNIERE page (sendBeacon sur /ferme ; registre d'onglets, ftp_cartes_onglets.py), onglet disparu sans le dire
(90 s sans sondage), 15 min sans action (fil d'horloge ci-dessous), arret de l'outil (atexit).
Les identifiants FTP restent cote serveur : jamais dans une reponse. Refus : texte brut (text/plain), jamais du JSON.

Routes (client de ce PC : Host local, parade au DNS rebinding ; les POST exigent l'en-tete X-Ftp-Cartes: 1 et la meme origine) :
    GET  /                       la page
    GET  /cartes                 ftp_cartes_liste.liste : {cartes, exclues}
    GET  /etat[?onglet=<id>]     {env, support, etat, message, sd} ; avec `onglet` : la page se signale (sondage de la page)
    GET  /execution              {en_cours: bool} : vrai tant que le FTP d'une carte est allume (l'annuaire refuse alors d'arreter l'outil)
    GET  /liste?chemin=          {chemin, entrees: [{nom, type, taille, date}]}
    GET  /telecharge?chemin=[&env=&support=]   le fichier, en piece jointe
    POST /ouvre {env, support[, onglet]}   allume le FTP de la carte (ce PC seulement) ; deja ouvert sur ce support : l'etat, sans reconnexion
    POST /ferme {[onglet]}       SEULE route sans l'en-tete X (sendBeacon ne peut pas le poser), origine verifiee. Avec un `onglet` valide
                                 (16 a 32 hexadecimaux) : n'eteint le FTP que si c'etait le dernier onglet ; sans identifiant (« Deconnecter »),
                                 corps absent, vide ou illisible : eteint toujours. Repond l'etat.
    POST /zip {chemins[, env, support]}   zip des fichiers et dossiers demandes
    POST /envoie?dossier=&nom=&ecraser=0|1   corps brut, 16 Mo au plus (413 avant toute ecriture) ; ce PC seulement
    POST /supprime {chemin, confirmations}   ce PC seulement ; un fichier protege ou un dossier qui en contient un : 2 confirmations
    Gestes de la page (/envoie, /supprime, /dossier, /deplace, /zip, /telecharge) : {env, support} facultatifs (parametres de requete pour
    /envoie et /telecharge) ; s'ils different de la session (autre onglet qui a change de carte ou de support) : 409, rien n'est ecrit.
    POST /dossier {chemin}                   ce PC seulement
    POST /deplace {source, cible[, confirmations]}   ce PC seulement ; confirmations entier (400 sinon), 1 par defaut ; 2 pour un fichier
                                 protege (source ou cible) ou un dossier qui en contient un ; cible deja existante : 409
Refus : 400 (saisie, chemin), 403 (acces), 404 (carte ou route inconnue), 409 (refus de la session ou de la carte), 413, 500 (inattendu).
Tout autre verbe : 405. Banc : test_ftp_cartes_web.py.
"""

import argparse
import atexit
import io
import json
import shutil
import socket
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

import acces_web
import ftp_cartes_liste
import ftp_cartes_session
from ftp_cartes_page import PAGE
from annuaire_outils import hote_autorise

PORT_DEFAUT = 7450
DEPOT = Path(__file__).resolve().parents[3]
MAX_CORPS = 16 * 1024                    # corps JSON
MAX_ENVOI = 16 * 1024 * 1024             # corps brut de /envoie
ENTETE = "X-Ftp-Cartes"
PERIODE_TIC = 10                         # s : appel de session.tic()
ECRITURES = ("/ouvre", "/envoie", "/supprime", "/dossier", "/deplace")     # allumage et ecritures : ce PC seulement
# 'self' pour le service worker de repli et le manifeste ajoutes par acces_web.habille ; aucune ressource externe.
CSP = ("default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; "
       "connect-src 'self'; manifest-src 'self'; worker-src 'self'; base-uri 'none'; form-action 'none'")


class ServeurFtp(ThreadingHTTPServer):
    request_queue_size = 64
    allow_reuse_address = False

    def server_bind(self):
        # Windows : adresse exclusive, sinon deux instances se lient au meme port (comme annuaire_outils.Serveur).
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def _corps_json(brut):
    d = json.loads(brut.decode("utf-8") or "{}")
    if not isinstance(d, dict):
        raise ValueError("corps JSON attendu")
    return d


def fabrique_gestionnaire(acces, racine, session):
    class Gestionnaire(BaseHTTPRequestHandler):
        timeout = 60                                 # un client qui annonce un corps puis se tait ne bloque pas un fil

        def log_message(self, *args):
            pass

        def _envoie(self, statut, corps, type_mime="text/plain; charset=utf-8", entetes=()):
            self.send_response(statut)
            self.send_header("Content-Type", type_mime)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", CSP)
            for nom, valeur in entetes:
                self.send_header(nom, valeur)
            self.end_headers()
            self.wfile.write(corps)

        def _json(self, donnees):
            self._envoie(200, json.dumps(donnees, ensure_ascii=False).encode("utf-8"), "application/json")

        def _fichier(self, tmp, nom, type_mime):
            """Rend le contenu d'un fichier temporaire en piece jointe (nom accentue : forme RFC 5987)."""
            taille = tmp.tell()
            tmp.seek(0)
            repli = "".join(c if c.isascii() and c.isalnum() or c in " ._-" else "_" for c in nom)
            self.send_response(200)
            for k, v in (("Content-Type", type_mime), ("Content-Length", str(taille)), ("Cache-Control", "no-store"),
                         ("X-Content-Type-Options", "nosniff"), ("Content-Security-Policy", CSP),
                         ("Content-Disposition", f"attachment; filename=\"{repli}\"; filename*=UTF-8''{quote(nom)}")):
                self.send_header(k, v)
            self.end_headers()
            shutil.copyfileobj(tmp, self.wfile)

        def _refuse(self, statut=403, message=b"refuse"):
            self.close_connection = True            # la connexion ne doit pas resservir
            try:                                    # corps petit vide d'abord : sinon le client Windows voit un reset (10053)
                longueur = int(self.headers.get("Content-Length") or 0)
                if 0 < longueur <= MAX_CORPS:
                    self.rfile.read(longueur)
            except (ValueError, OSError):
                pass
            self._envoie(statut, message)

        def _admis(self):
            if not acces.controle(self):
                return False
            if not hote_autorise(self, acces.port):
                self._refuse()
                return False
            return True

        def _erreurs(self, traitement):
            try:
                traitement()
            except ftp_cartes_session.RefusFtp as erreur:
                self._envoie(409, str(erreur).encode("utf-8"))
            except LookupError as erreur:
                self._envoie(404, str(erreur).encode("utf-8"))
            except (ValueError, TypeError, RecursionError) as erreur:         # ValueError : chemin ou saisie invalide, jamais un 500
                self._envoie(400, (str(erreur) or type(erreur).__name__).encode("utf-8"))
            except Exception as erreur:
                self._envoie(500, f"erreur inattendue : {type(erreur).__name__}".encode("utf-8"))   # jamais le message : il pourrait citer un secret

        def _requete(self):
            url = urlsplit(self.path)
            return url.path, {k: v[-1] for k, v in parse_qs(url.query).items()}

        # ---- GET -------------------------------------------------------------------------------------------------
        def do_GET(self):
            if self._admis():
                self._erreurs(self._get)

        def _get(self):
            chemin, q = self._requete()
            if chemin == "/":
                self._envoie(200, acces.habille(PAGE).encode("utf-8"), "text/html; charset=utf-8")
            elif chemin == "/cartes":
                self._json(ftp_cartes_liste.liste(racine))
            elif chemin == "/etat":
                session.onglets.vu(q.get("onglet"))                  # sondage de la page : l'onglet est vivant (identifiant invalide ignore)
                self._json(session.etat())
            elif chemin == "/execution":
                self._json({"en_cours": session.en_session()})       # lu par l'annuaire (annuaire_outils.route_occupee) avant un arret
            elif chemin == "/liste":
                dossier = q.get("chemin", "/")
                self._json({"chemin": dossier, "entrees": session.liste(dossier)})
            elif chemin == "/telecharge":
                cible = q.get("chemin", "")
                with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as tmp:
                    session.lit(cible, tmp, self._attendu(q))
                    self._fichier(tmp, cible.rstrip("/").rsplit("/", 1)[-1] or "carte", "application/octet-stream")
            else:
                self._envoie(404, b"introuvable")

        # ---- POST ------------------------------------------------------------------------------------------------
        def do_POST(self):
            if not self._admis():
                return
            chemin, q = self._requete()
            # /ferme : sendBeacon ne pose pas l'en-tete X ; l'origine reste verifiee (Origin absent ou celui de l'outil).
            if (chemin != "/ferme" and self.headers.get(ENTETE) != "1") or not acces.origine_autorisee(self):
                self._refuse()
                return
            if chemin in ECRITURES and not acces_web.est_local(self.client_address):
                self._refuse(403, "geste reserve a ce PC".encode("utf-8"))
                return
            self._erreurs(lambda: self._post(chemin, q))

        def _lit_corps(self, maximum):
            texte = self.headers.get("Content-Length")
            if texte is None or not texte.isdigit():
                self._refuse(411, b"Content-Length attendu")
                return None
            longueur = int(texte)
            if longueur > maximum:
                self._refuse(413, f"corps trop gros ({maximum} octets au plus)".encode("utf-8"))
                return None
            return self.rfile.read(longueur)

        @staticmethod
        def _attendu(src):
            """(env, support) que la page croit voir ; le controle se fait sous le verrou de la session (ftp_cartes_session._op) :
            ni ici ni avant, une ouverture de carte en cours pourrait encore changer la session entre le controle et le geste."""
            return (src.get("env"), src.get("support"))

        @staticmethod
        def _confirmations(d, defaut):
            n = d.get("confirmations", defaut)
            if not isinstance(n, int) or isinstance(n, bool):
                raise ValueError("confirmations : entier attendu")
            return n

        @staticmethod
        def _onglet(brut):
            """Identifiant d'onglet du corps de /ferme ; corps vide, illisible ou sans identifiant valide : None (on ferme comme avant)."""
            try:
                return _corps_json(brut).get("onglet")
            except (ValueError, RecursionError):      # corps tres imbrique : illisible, on ferme comme avant
                return None

        def _post(self, chemin, q):
            if chemin == "/envoie":
                brut = self._lit_corps(MAX_ENVOI)
                if brut is not None:
                    session.envoie(q.get("dossier", ""), q.get("nom", ""), io.BytesIO(brut), q.get("ecraser") == "1", self._attendu(q))
                    self._json({"message": "envoye"})
                return
            brut = self._lit_corps(MAX_CORPS)
            if brut is None:
                return
            if chemin == "/ferme":
                self._json(session.ferme_onglet(self._onglet(brut)))
                return
            d = _corps_json(brut)
            if chemin == "/ouvre":
                self._json(self._ouvre(d))
            elif chemin == "/zip":
                chemins = d.get("chemins")
                if not isinstance(chemins, list) or not chemins:
                    raise ValueError("chemins : liste non vide attendue")
                with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as tmp:
                    session.zip(chemins, tmp, self._attendu(d))
                    self._fichier(tmp, "carte.zip", "application/zip")
            elif chemin == "/supprime":
                session.supprime(d.get("chemin"), self._confirmations(d, 0), self._attendu(d))
                self._json({"message": "supprime"})
            elif chemin == "/dossier":
                session.cree_dossier(d.get("chemin"), self._attendu(d))
                self._json({"message": "dossier cree"})
            elif chemin == "/deplace":
                session.deplace(d.get("source"), d.get("cible"), self._attendu(d), confirmations=self._confirmations(d, 1))
                self._json({"message": "deplace"})
            else:
                self._envoie(404, b"introuvable")

        def _ouvre(self, d):
            env, support = d.get("env"), d.get("support")
            carte = next((c for c in ftp_cartes_liste.liste(racine)["cartes"] if c["env"] == env), None)
            if carte is None:
                raise LookupError("carte inconnue ou non joignable par FTP : %s" % env)
            return session.ouvre_ou_reprend(carte, support, d.get("onglet"))   # deuxieme onglet ou POST simultane : aucune reconnexion

        def _non(self):
            self._refuse(405, b"methode non permise")

        do_PUT = do_DELETE = do_PATCH = do_HEAD = do_OPTIONS = _non

    return Gestionnaire


def principal():
    opt = argparse.ArgumentParser(description="Navigateur FTP des cartes : le FTP de la carte est allume a la demande et eteint a la fin.")
    opt.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(opt)
    args = opt.parse_args()
    acces = acces_web.Acces(args.http, args.local, "Navigateur FTP des cartes")
    session = ftp_cartes_session.Session()
    try:
        serveur = ServeurFtp((acces.hote, args.http), fabrique_gestionnaire(acces, DEPOT, session))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    ftp_cartes_liste.prechauffe(DEPOT)                          # la premiere liste de /cartes ne se calcule pas a l'ouverture de la page
    atexit.register(session.ferme, "arret de l'outil")          # filet : le FTP de la carte ne reste jamais allume
    arret = threading.Event()

    def horloge():
        while not arret.wait(PERIODE_TIC):
            session.tic()

    threading.Thread(target=horloge, daemon=True).start()
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (le FTP de la carte est eteint a l'arret ; rien n'est ecrit dans le depot).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        arret.set()
        serveur.server_close()
        session.ferme("arret de l'outil")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
