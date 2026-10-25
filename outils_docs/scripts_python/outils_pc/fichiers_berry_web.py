"""Page web « Fichiers Berry par env » : etat des fichiers Berry de chaque env, ecriture du cenv, creation d'env.

UTILISATION
    python outils_docs/scripts_python/outils_pc/fichiers_berry_web.py [--http 7800] [--local] [--sans-navigateur]
    L'annuaire des outils (port 7600) la lance, ou la cible Custom « Fichiers Berry par env (page web) ».
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

Rien n'est ecrit sans « Enregistrer » (ou « Creer ») : couper la page ne laisse rien a moitie fait.
Toute ecriture est refusee pendant un build (meme detection que la page build : build_serie).

Routes (les POST exigent l'en-tete X-Fichiers-Berry: 1 et la meme origine ; JSON) :
    GET  /           la page (fichiers_berry_page.PAGE ; a defaut, une page provisoire)
    GET  /execution  {en_cours: false} : la cible Custom l'interroge pour savoir si la page tourne
    GET  /envs       {envs: [{nom, famille}]} : envs ESP32 du cenv
    GET  /etat       ?env=<env> : etat de chaque fichier (recensement refait a chaque appel) ; 404 env inconnu
    GET  /identite   ?base=&lieu=&nom= : {env, define, identite} proposes pour une creation
    POST /prepare    {env, demandes: [{chemin, etat, raison?, partage_accepte?}]} -> diff, empreinte,
                     confirmations (listes partagees), commentaires_cites, refus
    POST /enregistre {env, demandes, empreinte} -> {ecrit, diff} ; 409 si build, empreinte perimee, refus
    POST /creation/prepare {modele, base, lieu, nom, identite, define?} -> diff, empreinte, avertissements, refus
    POST /creation   {..., empreinte} -> {cree, env, dossier} ; 409 si build, empreinte perimee, refus
"""

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import acces_web
import fichiers_berry_creation as fbc
import fichiers_berry_ecriture as fbw
import fichiers_berry_etat as fbe

PORT_DEFAUT = 7800
DEPOT = Path(__file__).resolve().parents[3]
MAX_CORPS = 64 * 1024

PAGE_PROVISOIRE = ("<!doctype html><html lang=fr><meta charset=utf-8><title>Fichiers Berry par env</title>"
                   "<body style='font-family:sans-serif;margin:2em'><h1>Fichiers Berry par env</h1>"
                   "<p>Page en cours d'écriture (action A6). Le serveur répond déjà : /envs, /etat.</p>")


def page():
    try:
        import fichiers_berry_page              # A6 : remplace la page provisoire
        return fichiers_berry_page.PAGE
    except ImportError:
        return PAGE_PROVISOIRE


def builds_en_cours_defaut():
    import build_serie                          # meme detection que la page build (garde_build du depot)
    return build_serie.builds_en_cours_defaut()


def _chaine(demande, cle, defaut=None):
    v = demande.get(cle, defaut)
    if not isinstance(v, str):
        raise ValueError(f"{cle} : chaine attendue")
    return v


def demandes_de(demande):
    liste = demande.get("demandes")
    if not isinstance(liste, list) or not all(isinstance(d, dict) for d in liste):
        raise ValueError("demandes : liste d'objets attendue")
    return [fbw.Demande(_chaine(d, "chemin"), _chaine(d, "etat"), _chaine(d, "raison", ""),
                        bool(d.get("partage_accepte"))) for d in liste]


def creation_de(demande):
    identite = demande.get("identite")
    if not isinstance(identite, dict) or not all(isinstance(v, str) for v in identite.values()):
        raise ValueError("identite : objet de chaines attendu")
    return fbc.Creation(_chaine(demande, "modele"), _chaine(demande, "base"), _chaine(demande, "lieu"),
                        _chaine(demande, "nom"), {k: identite.get(k, "") for k in fbc.CHAMPS_IDENTITE},
                        _chaine(demande, "define", ""))


def fabrique_gestionnaire(acces, racine, builds_en_cours):
    def traite_post(chemin, demande):
        if chemin == "/prepare":
            return fbw.prepare(racine, _chaine(demande, "env"), demandes_de(demande))
        if chemin == "/enregistre":
            return fbw.enregistre(racine, _chaine(demande, "env"), demandes_de(demande),
                                  _chaine(demande, "empreinte"), builds_en_cours)
        if chemin == "/creation/prepare":
            return fbc.prepare_creation(racine, creation_de(demande))
        if chemin == "/creation":
            return fbc.cree(racine, creation_de(demande), _chaine(demande, "empreinte"), builds_en_cours)
        raise LookupError(chemin)

    def identite(params):
        base, lieu, nom = (params.get(k, [""])[0] for k in ("base", "lieu", "nom"))
        if not base or not fbc.LIEU.fullmatch(lieu) or not fbc.NOM.fullmatch(nom):
            raise ValueError("base, lieu (minuscules, chiffres) et nom (minuscules, chiffres, tirets) attendus")
        return {"env": fbc.nom_env(base, lieu, nom), "define": fbc.define(base, lieu, nom),
                "identite": fbc.identite_par_defaut(lieu, nom)}

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

        def _json(self, donnees, statut=200):
            self._envoie(statut, json.dumps(donnees, ensure_ascii=False).encode("utf-8"), "application/json")

        def do_GET(self):
            if not acces.controle(self):
                return
            url = urlsplit(self.path)
            params = parse_qs(url.query)
            try:
                if url.path == "/":
                    self._envoie(200, page().encode("utf-8"), "text/html; charset=utf-8")
                elif url.path == "/execution":
                    self._json({"en_cours": False})
                elif url.path == "/envs":
                    self._json({"envs": fbe.envs_proposes(racine)})
                elif url.path == "/etat":
                    self._json(fbe.etat_env(racine, params.get("env", [""])[0]))
                elif url.path == "/identite":
                    self._json(identite(params))
                else:
                    self._envoie(404, b"introuvable")
            except LookupError as erreur:
                self._envoie(404, str(erreur).encode("utf-8"))
            except ValueError as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))

        def do_POST(self):
            if not acces.controle(self):
                return
            if self.headers.get("X-Fichiers-Berry") != "1" or not acces.origine_autorisee(self):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return
            try:
                longueur = int(self.headers.get("Content-Length", "0") or 0)
                if longueur > MAX_CORPS:
                    self.close_connection = True              # corps non lu : la connexion ne doit pas resservir
                    self._envoie(413, "corps trop gros (64 Ko au plus)".encode("utf-8"))
                    return
                demande = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
                if not isinstance(demande, dict):
                    raise ValueError("corps JSON attendu")
                self._json(traite_post(urlsplit(self.path).path, demande))
            except LookupError as erreur:
                self._envoie(404, str(erreur).encode("utf-8"))
            except (ValueError, TypeError) as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))
            except RuntimeError as erreur:
                self._envoie(409, str(erreur).encode("utf-8"))

    return Gestionnaire


def principal():
    options = argparse.ArgumentParser(description="Page web des fichiers Berry par env (cenv) et creation d'env.")
    options.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(options)
    args = options.parse_args()

    # Nom de la fiche de presence, en litteral : identique a nom_acces de l'outil « fichiers_berry »
    # (annuaire_registre.py), sinon la tuile ne retrouve pas l'outil ; test_annuaire le verifie sur cette ligne.
    acces = acces_web.Acces(args.http, args.local, "Fichiers Berry par env")
    try:
        serveur = ThreadingHTTPServer((acces.hote, args.http), fabrique_gestionnaire(acces, DEPOT, builds_en_cours_defaut))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (rien n'est ecrit sans « Enregistrer »).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
