"""Banc de la page de synchro du fork (synchro_fork_web.py et ses modules). Code de sortie 0 = vert.

Groupes :
  question  synchro_fork_question.demander : terminal, page (ligne balisee + echo), entree fermee ;
  session   un FAUX script (dossier temporaire) : questions, refus des reponses hors choix, push force
            sans le nom de la branche refuse, une seule execution a la fois, fermeture = reponse prudente ;
  http      serveur sur port libre : page, X-Synchro, erreurs, diff hors des fichiers modifies refuse,
            acces depuis l'IP reseau de ce PC sans jeton refuse ;
  reel      (--reel) les VRAIS scripts en --dry-run par la session : lecture seule (GitHub, git fetch upstream).
Temoin : une session qui transmet toute reponse sans la valider DOIT faire echouer le groupe session.
"""

import http.client
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import synchro_fork_question  # noqa: E402
import synchro_fork_session  # noqa: E402
import synchro_fork_web  # noqa: E402  (ajoute outils_pc au chemin)
import acces_web  # noqa: E402

ECHECS = []

FAUX_SCRIPT = r'''
import sys
from synchro_fork_question import demander
print("\x1b[36mbonjour\x1b[0m", flush=True)
r = demander("Pousser en force ? [O/n] ", [("o", "Pousser en force"), ("n", "Ne pas pousser")], eof="n",
             confirme="development")
print("reponse=" + r, flush=True)
sys.exit(3 if r == "o" else 0)
'''


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def attend(predicat, delai=10.0):
    fin = time.monotonic() + delai
    while time.monotonic() < fin:
        if predicat():
            return True
        time.sleep(0.05)
    return False


def groupe_question():
    print("\n== question")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.pop(synchro_fork_question.VARIABLE, None)
    code = ("import synchro_fork_question as q; print('R=' + q.demander('Q ? ', [('o','Oui'),('n','Non')], eof='n'))")
    r = subprocess.run([sys.executable, "-c", code], cwd=ICI, input="", capture_output=True, text=True, env=env)
    verifie(r.stdout.strip().endswith("R=n"), True, "terminal, entree fermee : reponse prudente (eof)")
    env[synchro_fork_question.VARIABLE] = "1"
    r = subprocess.run([sys.executable, "-c", code], cwd=ICI, input="o\n", capture_output=True, text=True, env=env)
    lignes = r.stdout.splitlines()
    marque = [l for l in lignes if l.startswith(synchro_fork_question.MARQUE)]
    donnees = json.loads(marque[0][len(synchro_fork_question.MARQUE):]) if marque else {}
    verifie(donnees.get("choix"), [["o", "Oui"], ["n", "Non"]], "page : question balisee avec ses choix")
    verifie("Q ? o" in lignes and lignes[-1] == "R=o", True, "page : echo question + reponse, reponse rendue")
    r = subprocess.run([sys.executable, "-c", code], cwd=ICI, input="", capture_output=True, text=True, env=env)
    verifie(r.stdout.strip().endswith("R=n"), True, "page, entree fermee : reponse prudente (eof)")


def prepare_faux(dossier):
    shutil.copy(ICI / "synchro_fork_question.py", dossier)
    for nom in synchro_fork_session.SCRIPTS.values():
        (Path(dossier) / nom).write_text(FAUX_SCRIPT, encoding="utf-8")


def scenario_session(session):
    """Deroule le scenario ; rend la liste des resultats (booleens) dans un ordre fixe."""
    res = []
    session.lance("merge")
    res.append(attend(lambda: session.etat()["question"] is not None))
    try:
        session.lance("rebase")
        res.append(False)
    except RuntimeError:
        res.append(True)                              # une seule execution a la fois
    for valeur, confirmation in (("x", ""), ("o", ""), ("o", "Development")):
        try:
            session.repond(valeur, confirmation)
            res.append(False)
        except (ValueError, RuntimeError):
            res.append(True)                          # hors choix / confirmation absente / mauvaise casse
    session.repond("o", "development")
    res.append(attend(lambda: not session.en_cours()))
    evenements = session.depuis(0, 0)
    res.append([e["code"] for e in evenements if e["type"] == "fin"] == [3])
    res.append(any(e["type"] == "ligne" and e["texte"] == "reponse=o" for e in evenements))
    # fermeture pendant une question : entree standard fermee -> reponse prudente 'n' -> code 0
    session.lance("rebase")
    attend(lambda: session.etat()["question"] is not None)
    res.append(session.ferme(20) == 0)
    return res


def groupe_session(dossier):
    print("\n== session (faux script)")
    noms = ["question annoncee", "2e lancement refuse", "reponse hors choix refusee",
            "push force sans saisie refuse", "saisie de mauvaise casse refusee", "fin apres reponse",
            "code de sortie du script", "sortie du script relayee", "fermeture : reponse prudente"]
    for nom, ok in zip(noms, scenario_session(synchro_fork_session.Session(dossier=dossier))):
        verifie(ok, True, nom)

    class SessionNaive(synchro_fork_session.Session):          # TEMOIN : transmet tout sans valider
        def repond(self, valeur, confirmation=""):
            with self.verrou:
                proc, self.question = self.proc, None
            proc.stdin.write(valeur + "\n")
            proc.stdin.flush()

    try:
        temoin = scenario_session(SessionNaive(dossier=dossier))
    except Exception:
        temoin = [False]
    verifie(all(temoin), False, "TEMOIN session sans validation : le scenario echoue")


def requete(hote, port, methode="GET", chemin="/", corps=None, entetes=None):
    c = http.client.HTTPConnection(hote, port, timeout=10)
    c.request(methode, chemin, body=json.dumps(corps).encode() if corps is not None else None, headers=entetes or {})
    r = c.getresponse()
    donnees = r.read()
    c.close()
    return r.status, donnees.decode("utf-8", "replace")


def groupe_http(dossier):
    print("\n== http")
    session = synchro_fork_session.Session(dossier=dossier)
    acces = acces_web.Acces(0, False, "banc")
    srv = ThreadingHTTPServer(("0.0.0.0", 0), synchro_fork_web.fabrique_gestionnaire(session, acces))
    acces.port = port = srv.server_address[1]
    acces.cookie = f"jeton_{port}"
    Thread(target=srv.serve_forever, daemon=True).start()
    x = {"X-Synchro": "1", "Content-Type": "application/json"}
    statut, page = requete("127.0.0.1", port)
    verifie((statut, "<title>Synchro du fork</title>" in page), (200, True), "page servie")
    verifie(requete("127.0.0.1", port, "POST", "/lance", {"script": "merge"})[0], 403, "POST sans X-Synchro refuse")
    verifie(requete("127.0.0.1", port, "POST", "/lance", {"script": "rm"}, x)[0], 400, "script inconnu refuse")
    verifie(requete("127.0.0.1", port, "POST", "/repond", {"valeur": "o"}, x)[0], 409, "reponse sans question refusee")
    verifie(requete("127.0.0.1", port, "GET", "/diff?chemin=../../Windows/win.ini")[0], 400,
            "diff d'un fichier non modifie refuse")
    verifie(requete("127.0.0.1", port, "POST", "/lance", {"script": "merge"},
                    dict(x, Origin="http://evil.example"))[0], 403, "origine etrangere refusee")
    statut, aide = requete("127.0.0.1", port, "GET", "/aide")
    verifie(statut == 200 and "--dry-run" in json.loads(aide).get("merge", ""), True, "aide des scripts")
    ips = acces_web.ips_reseau()
    if ips:
        verifie(requete(ips[0], port)[0], 403, f"autre appareil ({ips[0]}) sans jeton refuse")
    srv.shutdown()


def groupe_reel():
    print("\n== reel (vrais scripts en --dry-run, lecture seule)")
    session = synchro_fork_session.Session(racine=ICI.parents[2])
    for script in ("merge", "rebase"):
        session.lance(script, simulation=True)
        attend(lambda: not session.en_cours(), 240)
        evenements = session.depuis(0, 0)
        fins = [e["code"] for e in evenements if e["type"] == "fin"]
        verifie(fins[-1:], [0], f"{script} --dry-run termine en 0")
        verifie(any(e["type"] == "question" for e in evenements), False, f"{script} --dry-run ne pose aucune question")


def principal():
    with tempfile.TemporaryDirectory() as dossier:
        prepare_faux(dossier)
        groupe_question()
        groupe_session(dossier)
        groupe_http(dossier)
    if "--reel" in sys.argv:
        groupe_reel()
    print("\nVERT" if not ECHECS else f"\nROUGE : {len(ECHECS)} echec(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
