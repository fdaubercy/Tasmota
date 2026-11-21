"""Menage du depot (page web, port 7995) : lancer l'agent auditeur-menage et lire ses propositions. LECTURE SEULE sur le depot.

UTILISATION
    python outils_docs/scripts_python/outils_pc/menage_web.py [--http 7995] [--local] [--sans-navigateur]
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

L'audit est en LECTURE SEULE (menage_lancement.py). Les seules ecritures : la liste « a garder » et le journal des applications, HORS depot, et, apres confirmation
explicite, l'application d'un lot (git rm / git mv, jamais de commit, ce PC seulement : menage_application.py, plan tasks/plans/menage-appliquer.md). L'audit lui-meme : menage_lancement.py (claude -p en lecture seule).

Routes (les POST exigent l'en-tete X-Menage: 1 et la meme origine ; client de ce PC : Host local, parade au DNS rebinding) :
    GET  /          la page (menage_page.PAGE)
    GET  /options   {zones, categories, modeles, efforts, defauts}  : les valeurs admises, pour la page
    GET  /etat[?depuis=n]  {etat: repos|en_cours|fini|echec, message, debut, fin, propositions, appels, progression (approximative, 0-100),
                    activite: actions de l'agent depuis la n-ieme (secrets masques)}
    GET  /rapport   le rapport valide, sans les propositions « ignorees cette fois » ni les chemins « a garder » ; 404 s'il n'y en a pas
    GET  /gardes    {gardes: [chemins]}
    GET  /appliquer/derniere  {application: n | null, faits: [{id, action, chemin}]} : la derniere application reelle (bouton « Annuler » de la page)
    GET  /rapports  {rapports: [{nom, date, propositions}]} : rapports sauvegardes hors depot, le plus recent d'abord (A4 du plan menage-appliquer)
    POST /rapports/ouvrir {nom}  -> {message} : rouvre un rapport DE LA LISTE (jamais un chemin libre), revalide et recontre-verifie par git ; 404 nom inconnu, 400 illisible, 409 audit en cours
    POST /lancer    {zone, categories, anciennete_jours, modele, effort}  -> {message}
    POST /arreter   {}
    POST /appliquer/apercu {ids}  -> {eligibles, refuses, empreinte} : apercu LECTURE SEULE d'un lot de deplacements (A1 du plan menage-appliquer)
    POST /appliquer {ids, empreinte, head, confirme:true | a_blanc:true}  -> {a_blanc, faits, echec, restants, renvois} : APPLIQUE le lot apercu (git rm / git mv, jamais commite) ; a_blanc = meme parcours en git -n, rien modifie
    POST /appliquer/annuler {application}  -> {retablis, echec, restants} : DEFAIT la derniere application (git restore / git mv inverse), ce PC seulement ; 409 si un commit a eu lieu depuis ou si le fichier a ete touche
    POST /garder    {chemin}    un chemin du rapport en cours seulement   -> memorise dans garde.json
    POST /degarder  {chemin}
    POST /ignorer   {id}        une proposition du rapport en cours ; oubliee au redemarrage de l'outil
Refus : 400 (saisie), 404 (pas de rapport, id ou chemin inconnu), 403 (acces), 409 (build en cours, audit deja en cours), 500 (inattendu).
Banc : test_menage_web.py.
"""

import argparse
import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import acces_web
from annuaire_outils import hote_autorise
import menage_application
import menage_lancement as ml
import menage_memoire
import menage_rapport

PORT_DEFAUT = 7995
DEPOT = Path(__file__).resolve().parents[3]
MAX_CORPS = 16 * 1024
ENTETE = "X-Menage"


class ServeurMenage(ThreadingHTTPServer):
    request_queue_size = 64          # defaut de Python : 5. La page lance 6 a 8 requetes d'un coup au chargement : sous charge, une connexion etait refusee
    allow_reuse_address = False      # HTTPServer l'active : sous Windows, deux instances se liaient alors au meme port

    def server_bind(self):
        # Windows : adresse exclusive (comme ftp_cartes_web.ServeurFtp et annuaire_outils.Serveur).
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def builds_en_cours_defaut():
    import build_serie                          # meme detection que la page build (garde_build du depot)
    return build_serie.builds_en_cours_defaut()


class Etat:
    """Ce que la page voit : l'audit, la liste « a garder » et les propositions ignorees pour cette fois."""

    def __init__(self, racine, builds_en_cours, programme=None, dossier=None, delai=ml.DELAI):
        dossier = Path(dossier) if dossier else acces_web.dossier_donnees() / "menage"
        self.racine = Path(racine)
        self.dossier = dossier
        self.memoire = menage_memoire.Memoire(dossier, racine)
        self.audit = ml.Audit(racine, builds_en_cours, programme=programme, delai=delai, gardes=self.memoire.charge, dossier_rapports=dossier / "rapports")
        self.ignorees = set()
        self._verrou = threading.Lock()
        self.applications = []                 # pile des applications REELLES de ce processus : {numero, head, faits} ; la page n'envoie jamais la liste a defaire
        self._numero = 0

    def rapport(self):
        """Rapport valide de l'audit fini, filtre ; None sans rapport."""
        r = self.audit.etat().get("rapport")
        if r is None:
            return None
        gardes, ignorees = set(self.memoire.charge()), set(self.ignorees)
        props = [p for p in r["propositions"] if p["chemin"] not in gardes and p["id"] not in ignorees]
        return {**r, "propositions": props}

    def lance(self, brut):
        params, erreurs = ml.parametres(brut)
        if erreurs:
            raise ValueError("parametres refuses : " + " ; ".join(erreurs))
        ok, message = self.audit.lance(params)
        if not ok:
            raise RuntimeError(message)
        with self._verrou:
            self.ignorees = set()
        return {"message": message}

    def ouvre(self, d):
        """Rouvre un rapport sauvegarde (nom pris dans la liste) : revalide, recontre-verifie ; « ignorees cette fois » repart de zero."""
        message = self.audit.ouvre_rapport(d.get("nom"))
        with self._verrou:
            self.ignorees = set()
        return {"message": message}

    def apercu(self, d):
        """Apercu (lecture seule) d'un lot de deplacements pris dans le rapport en cours : voir menage_application.previsualise."""
        menage_application.verifie_pas_de_build(self.audit.builds_en_cours, "apercu")
        r = self.rapport()
        if r is None:
            raise LookupError("pas de rapport")
        if not menage_application._VERROU.acquire(blocking=False):     # `git rm -n` prend le verrou d'index : il ferait echouer le lot en cours
            raise RuntimeError("une application ou un retour en arriere est en cours : apercu refuse")
        try:
            return menage_application.previsualise(d.get("ids"), r["propositions"], self.racine)
        finally:
            menage_application._VERROU.release()

    def derniere(self):
        """La derniere application REELLE de ce processus (bouton « Annuler » de la page, qui survit a un rechargement) ou {application: None}."""
        with self._verrou:
            if not self.applications:
                return {"application": None, "faits": []}
            a = self.applications[-1]
            return {"application": a["numero"], "faits": [{"id": f["id"], "action": f.get("action"), "chemin": f.get("chemin")} for f in a["faits"]]}

    def applique(self, d):
        """Application REELLE d'un lot (git rm / git mv, rien de commite) : exige la confirmation explicite, l'empreinte et le HEAD de l'apercu."""
        a_blanc = d.get("a_blanc", False)
        if not isinstance(a_blanc, bool):
            raise ValueError("a_blanc : booleen attendu")
        if not a_blanc and d.get("confirme") is not True:
            raise ValueError("confirmation explicite attendue (confirme: true), ou a_blanc: true pour une simulation")
        r = self.rapport()
        if r is None:
            raise LookupError("pas de rapport")
        res = menage_application.applique(d.get("ids"), d.get("empreinte"), d.get("head"), r["propositions"], self.racine,
                                          builds_en_cours=self.audit.builds_en_cours, journal=self.dossier / "applications.jsonl", a_blanc=a_blanc)
        if not a_blanc and res["faits"]:
            with self._verrou:
                self._numero += 1
                self.applications.append({"numero": self._numero, "head": d.get("head"), "faits": list(res["faits"])})
                res["application"] = self._numero
        return res

    def annule(self, d):
        """Retour en arriere de la DERNIERE application de ce processus (numero exige : la page ne defait que ce qu'elle affiche)."""
        with self._verrou:
            if not self.applications:
                raise LookupError("aucune application a defaire")
            derniere = self.applications[-1]
        if d.get("application") != derniere["numero"]:
            raise RuntimeError("ce n'est pas la derniere application : seule la derniere peut etre defaite")
        res = menage_application.annule(derniere["faits"], derniere["head"], self.racine, builds_en_cours=self.audit.builds_en_cours,
                                        journal=self.dossier / "applications.jsonl")
        with self._verrou:
            if not res["restants"]:
                if derniere in self.applications:         # remove, pas pop : une application empilee entre-temps (course) ne doit pas disparaitre a sa place
                    self.applications.remove(derniere)
            else:
                derniere["faits"] = [f for f in derniere["faits"] if f["id"] in set(res["restants"])]
        return res

    def garde(self, chemin, retire=False):
        if retire:
            ok, message = self.memoire.retire(chemin if isinstance(chemin, str) else "")
            if not ok:
                raise LookupError(message)
            return {"message": message}
        brut = self.audit.etat().get("rapport")
        propre = menage_rapport.chemin_sur(chemin, self.racine)
        if brut is None or propre is None or propre not in {p["chemin"] for p in brut["propositions"]}:
            raise LookupError("ce chemin n'est pas dans le rapport en cours")
        ok, message = self.memoire.ajoute(propre)
        if not ok:
            raise ValueError(message)
        return {"message": message}

    def ignore(self, ident):
        brut = self.audit.etat().get("rapport")
        if brut is None or ident not in {p["id"] for p in brut["propositions"]}:
            raise LookupError("cette proposition n'est pas dans le rapport en cours")
        with self._verrou:
            self.ignorees.add(ident)
        return {"message": "ignoree pour cette fois"}


def options():
    return {"zones": list(ml.ZONES), "categories": list(menage_rapport.CATEGORIES), "modeles": list(ml.MODELES),
            "efforts": list(ml.EFFORTS), "defauts": ml.parametres({})[0]}


def fabrique_gestionnaire(acces, etat):
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
            except (KeyError, IndexError) as erreur:
                self._texte(500, f"erreur inattendue : {type(erreur).__name__} : {erreur}")
            except LookupError as erreur:
                self._texte(404, erreur)
            except (ValueError, TypeError, RecursionError) as erreur:
                self._texte(400, erreur)
            except RuntimeError as erreur:
                self._texte(409, erreur)
            except Exception as erreur:
                self._texte(500, f"erreur inattendue : {type(erreur).__name__} : {erreur}")

        def do_GET(self):
            if self._admis():
                self._erreurs(self._get)

        def _get(self):
            chemin = urlsplit(self.path).path
            if chemin == "/":
                import menage_page
                self._envoie(200, acces.habille(menage_page.PAGE).encode("utf-8"), "text/html; charset=utf-8")
            elif chemin == "/options":
                self._json(options())
            elif chemin == "/etat":
                e = etat.audit.etat()
                r = etat.rapport()
                try:
                    depuis = int(parse_qs(urlsplit(self.path).query).get("depuis", ["0"])[0])
                except ValueError:
                    depuis = 0
                debut_liste = e["appels"] - len(e["activite"])          # rang absolu de la 1re entree gardee
                self._json({"etat": e["etat"], "message": e["message"], "debut": e["debut"], "fin": e["fin"],
                            "propositions": None if r is None else len(r["propositions"]),
                            "appels": e["appels"], "progression": e["progression"], "detail": e["detail"],
                            "activite": e["activite"][max(0, depuis - debut_liste):]})
            elif chemin == "/rapport":
                r = etat.rapport()
                if r is None:
                    raise LookupError("pas de rapport")
                self._json(r)
            elif chemin == "/gardes":
                self._json({"gardes": etat.memoire.charge()})
            elif chemin == "/appliquer/derniere":
                self._json(etat.derniere())
            elif chemin == "/rapports":
                self._json({"rapports": etat.audit.rapports()})
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
            if chemin == "/lancer":
                self._json(etat.lance(d))
            elif chemin == "/arreter":
                etat.audit.arrete()
                self._json({"message": "arret demande"})
            elif chemin == "/appliquer":
                if not acces_web.est_local(self.client_address):       # un geste qui ECRIT dans le depot : ce PC seulement, jamais un autre appareil (meme avec le jeton)
                    self._envoie(403, "geste reserve a ce PC".encode("utf-8"))
                    return
                self._json(etat.applique(d))
            elif chemin == "/rapports/ouvrir":
                self._json(etat.ouvre(d))
            elif chemin == "/appliquer/annuler":
                if not acces_web.est_local(self.client_address):
                    self._envoie(403, "geste reserve a ce PC".encode("utf-8"))
                    return
                self._json(etat.annule(d))
            elif chemin == "/appliquer/apercu":
                self._json(etat.apercu(d))
            elif chemin == "/garder":
                self._json(etat.garde(d.get("chemin")))
            elif chemin == "/degarder":
                self._json(etat.garde(d.get("chemin"), retire=True))
            elif chemin == "/ignorer":
                self._json(etat.ignore(d.get("id")))
            else:
                self._envoie(404, b"introuvable")

    return Gestionnaire


def principal():
    opt = argparse.ArgumentParser(description="Menage du depot : lancer l'audit de rangement et lire ses propositions (lecture seule).")
    opt.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(opt)
    args = opt.parse_args()
    acces = acces_web.Acces(args.http, args.local, "Menage du depot")
    try:
        serveur = ServeurMenage((acces.hote, args.http), fabrique_gestionnaire(acces, Etat(DEPOT, builds_en_cours_defaut)))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (le depot n'est modifie que par « Appliquer pour de bon », apres confirmation dans la page).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
