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
    GET  /assistant    analyse du cas et liste d'etapes (synchro_fork_assistant.analyse)
    GET  /trois-voies  ?chemin=<fichier touche des deux cotes ou en conflit> : diffs {mien, amont}
    POST /assistant/action  {action: bascule|ff-origin|merge|resout|ouvre|termine|abandonne|pousse,
                             chemin?, choix?, confirmation?} ; une seule a la fois (409), refusee pendant une
                             execution de la session ; abandonne et pousse exigent confirmation "oui"
"""

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

# acces_web et build_serie vivent avec les outils PC (outils_pc/) : seuls imports hors de ce dossier.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "outils_pc"))
import acces_web  # noqa: E402

import build_serie  # noqa: E402
import synchro_fork_assistant  # noqa: E402
import synchro_fork_etat  # noqa: E402  (importe synchronise_fork_tasmota : sortie standard en utf-8)
import synchro_fork_fusion  # noqa: E402
import synchro_fork_page  # noqa: E402
import synchro_fork_session  # noqa: E402

PORT_DEFAUT = 7500
VERROU = threading.Lock()      # une seule action d'assistant a la fois


def action_assistant(demande, racine, builds_en_cours):
    """Une action de synchro_fork_fusion ; rend le texte du resultat. Erreurs : ValueError (demande), RuntimeError."""
    nom, f = str(demande.get("action", "")), synchro_fork_fusion
    chemin, choix = str(demande.get("chemin", "")), str(demande.get("choix", ""))
    if nom in ("abandonne", "pousse") and demande.get("confirmation") != "oui":
        raise ValueError(f"{nom} exige confirmation = \"oui\"")
    actions = {"bascule": lambda: f.bascule(racine, builds_en_cours),
               "ff-origin": lambda: f.ff_origin(racine, builds_en_cours),
               "merge": lambda: f.lance_merge(racine, builds_en_cours),
               "resout": lambda: f.resout(racine, chemin, choix, builds_en_cours),
               "ouvre": lambda: f.ouvre(racine, chemin),
               "termine": lambda: f.termine(racine, builds_en_cours),
               "abandonne": lambda: f.abandonne(racine, builds_en_cours),
               "pousse": lambda: f.pousse(racine)}
    if nom not in actions:
        raise ValueError(f"action inconnue : {nom!r}")
    return actions[nom]()


def traite_post(chemin, demande, session, racine=synchro_fork_etat.REPO,
                builds_en_cours=build_serie.builds_en_cours_defaut, verrou=None):
    verrou = verrou or VERROU
    if chemin == "/assistant/action":
        if not verrou.acquire(blocking=False):
            raise RuntimeError("une action est déjà en cours")
        try:
            if session.en_cours():
                raise RuntimeError("une synchro est en cours : attends sa fin avant toute action de l'assistant")
            resultat = action_assistant(demande, racine, builds_en_cours)
            return {"ok": True, "resultat": resultat, "analyse": synchro_fork_assistant.analyse(racine, fetch=False)}
        finally:
            verrou.release()
    if chemin == "/lance":
        if not verrou.acquire(blocking=False):      # exclusion mutuelle avec les actions de l'assistant
            raise RuntimeError("une action de l'assistant est en cours")
        try:
            if synchro_fork_etat.operation_git(racine):
                raise RuntimeError(f"un {synchro_fork_etat.operation_git(racine)} est en cours dans le dépôt : le terminer "
                                   "ou l'annuler avant toute synchro")
            session.lance(str(demande.get("script", "")), bool(demande.get("simulation")))
        finally:
            verrou.release()
        return {"ok": True}
    if chemin == "/repond":
        session.repond(str(demande.get("valeur", "")), str(demande.get("confirmation", "")))
        return {"ok": True}
    if chemin == "/commit-journal":
        if session.en_cours():
            raise RuntimeError("une synchro est en cours : commite le journal après")
        return {"ok": True, "commit": synchro_fork_etat.commit_journal(racine)}
    raise LookupError(chemin)


def fabrique_gestionnaire(session, acces, racine=synchro_fork_etat.REPO,
                          builds_en_cours=build_serie.builds_en_cours_defaut):
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
                    self._envoie(200, synchro_fork_etat.diff(params.get("chemin", [""])[0], racine).encode("utf-8"))
                elif url.path == "/historique":
                    self._envoie(200, synchro_fork_etat.historique().encode("utf-8"))
                elif url.path == "/assistant":
                    self._json(synchro_fork_assistant.analyse(racine))
                elif url.path == "/trois-voies":
                    self._json(synchro_fork_assistant.trois_voies(racine, params.get("chemin", [""])[0],
                                                                   synchro_fork_assistant.autorises(racine)))
                elif url.path == "/aide":
                    self._json(synchro_fork_etat.aide())
                else:
                    self._envoie(404, b"introuvable")
            except ValueError as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))
            except RuntimeError as erreur:
                self._envoie(409, str(erreur).encode("utf-8"))

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
                self._json(traite_post(urlsplit(self.path).path, demande, session, racine, builds_en_cours))
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
