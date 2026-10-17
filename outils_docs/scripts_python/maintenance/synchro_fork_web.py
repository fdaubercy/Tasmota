"""Page web de la synchro du fork : tout ce que font synchronise_fork_tasmota.py (merge) et
synchronise_upstream_tasmota.py (rebase), plus l'etat du fork, les fichiers modifies, le journal.

UTILISATION
    python outils_docs/scripts_python/maintenance/synchro_fork_web.py [--http 7500] [--local] [--sans-navigateur]
    Tache VS Code « Outil : synchro du fork », ou cible PlatformIO Custom « Synchro du fork ».
    La console affiche le lien (Ctrl+clic) et ouvre la page ; un 2e lien, avec jeton, sert depuis un
    autre appareil du reseau (regle d'acces : outils_pc/acces_web.py).

Les scripts tournent tels qu'au terminal (synchro_fork_session.py) : leurs questions deviennent des
boutons. Le push force du rebase exige de saisir le nom de la branche (verifie ici, pas seulement
dans la page).

Routes (les POST exigent l'en-tete X-Synchro: 1 et la meme origine) :
    GET  /             page (synchro_fork_page.PAGE)
    GET  /etat         branche, avance/retard, commits de l'amont, fichiers modifies, journal
    GET  /execution    execution en cours, question en attente
    GET  /flux         Server-Sent Events : sortie du script et questions (rejouees depuis ?depuis=n)
    GET  /diff         ?chemin=<fichier suivi modifie>
    GET  /historique   journal des synchros (outils_docs/HISTORIQUE_SYNCHRO_FORK.md)
    GET  /aide         --help des deux scripts
    POST /lance        {script: merge|rebase, simulation: bool}
    POST /repond       {valeur, confirmation}
    POST /commit-journal
"""

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

# acces_web vit avec les outils PC qui l'utilisent aussi (outils_pc/) : seul import hors de ce dossier.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "outils_pc"))
import acces_web  # noqa: E402

import synchro_fork_etat  # noqa: E402  (importe synchronise_fork_tasmota : sortie standard en utf-8)
import synchro_fork_page  # noqa: E402
import synchro_fork_session  # noqa: E402

PORT_DEFAUT = 7500


def traite_post(chemin, demande, session):
    if chemin == "/lance":
        if synchro_fork_etat.operation_git():
            raise RuntimeError(f"un {synchro_fork_etat.operation_git()} est en cours dans le depot : le terminer "
                               "ou l'annuler avant toute synchro")
        session.lance(str(demande.get("script", "")), bool(demande.get("simulation")))
        return {"ok": True}
    if chemin == "/repond":
        session.repond(str(demande.get("valeur", "")), str(demande.get("confirmation", "")))
        return {"ok": True}
    if chemin == "/commit-journal":
        if session.en_cours():
            raise RuntimeError("une synchro est en cours : commiter le journal apres")
        return {"ok": True, "commit": synchro_fork_etat.commit_journal()}
    raise LookupError(chemin)


def fabrique_gestionnaire(session, acces):
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

        def _flux(self, depuis):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                while True:
                    evenements = session.depuis(depuis)
                    for e in evenements:
                        self.wfile.write(f"id: {e['n']}\ndata: {json.dumps(e, ensure_ascii=False)}\n\n".encode("utf-8"))
                        depuis = e["n"]
                    if not evenements:
                        self.wfile.write(b": veille\n\n")     # detecte un onglet ferme
                    self.wfile.flush()
            except OSError:
                pass

        def do_GET(self):
            if not acces.controle(self):
                return
            url = urlsplit(self.path)
            params = parse_qs(url.query)
            try:
                if url.path == "/":
                    self._envoie(200, synchro_fork_page.PAGE.encode("utf-8"), "text/html; charset=utf-8")
                elif url.path == "/etat":
                    self._json(synchro_fork_etat.etat())
                elif url.path == "/execution":
                    self._json(session.etat())
                elif url.path == "/flux":
                    depuis = self.headers.get("Last-Event-ID") or params.get("depuis", ["0"])[0]
                    self._flux(int(depuis) if str(depuis).isdigit() else 0)
                elif url.path == "/diff":
                    self._envoie(200, synchro_fork_etat.diff(params.get("chemin", [""])[0]).encode("utf-8"))
                elif url.path == "/historique":
                    self._envoie(200, synchro_fork_etat.historique().encode("utf-8"))
                elif url.path == "/aide":
                    self._json(synchro_fork_etat.aide())
                else:
                    self._envoie(404, b"introuvable")
            except ValueError as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))

        def do_POST(self):
            if not acces.controle(self):
                return
            if self.headers.get("X-Synchro") != "1" or not acces.origine_autorisee(self):
                self._envoie(403, b"refuse")
                return
            try:
                longueur = min(int(self.headers.get("Content-Length", "0") or 0), 64 * 1024)
                demande = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
                if not isinstance(demande, dict):
                    raise ValueError("corps JSON attendu")
                self._json(traite_post(urlsplit(self.path).path, demande, session))
            except LookupError:
                self._envoie(404, b"introuvable")
            except (ValueError, TypeError) as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))
            except RuntimeError as erreur:
                self._envoie(409, str(erreur).encode("utf-8"))

    return Gestionnaire


def principal():
    options = argparse.ArgumentParser(description="Page web de la synchro du fork Tasmota (merge et rebase).")
    options.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(options)
    args = options.parse_args()

    acces = acces_web.Acces(args.http, args.local, "Synchro du fork")
    session = synchro_fork_session.Session(racine=synchro_fork_etat.REPO)
    try:
        serveur = ThreadingHTTPServer((acces.hote, args.http), fabrique_gestionnaire(session, acces))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (une synchro en cours recoit alors les reponses prudentes : ne pas pousser,"
          " annuler le rebase).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
        if session.en_cours():
            print("synchro en cours : fermeture de son entree standard, attente de sa fin...", flush=True)
            code = session.ferme()
            print(f"script termine (code {code})" if code is not None else "script toujours actif apres 2 min",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
