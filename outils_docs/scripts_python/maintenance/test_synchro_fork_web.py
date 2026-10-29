"""Banc de la page de synchro du fork (synchro_fork_web.py et ses modules). Code de sortie 0 = vert.

Groupes :
  question  synchro_fork_question.demander : terminal, page (ligne balisee + echo), entree fermee ;
  session   un FAUX script (dossier temporaire) : questions, refus des reponses hors choix, push force
            sans le nom de la branche refuse, une seule execution a la fois, fermeture = reponse prudente ;
  http      serveur sur port libre : page, X-Synchro, erreurs, diff hors des fichiers modifies refuse,
            acces depuis l'IP reseau de ce PC sans jeton refuse ;
  assistant routes de l'assistant sur un faux depot : refus, 409 (session occupee, double clic), reponse ;
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
from threading import Event, Thread

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


def requete(hote, port, methode="GET", chemin="/", corps=None, entetes=None, delai=10):
    c = http.client.HTTPConnection(hote, port, timeout=delai)
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
    # onglet ouvert avant un redemarrage du serveur : EventSource se reconnecte avec l'ancien Last-Event-ID (60),
    # plus grand que tout ce que ce serveur a numerote -> il doit tout rejouer, sinon l'onglet ne recoit plus rien
    session._ajoute(type="debut", script="merge", simulation=True)
    session._ajoute(type="fin", script="merge", code=0)
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=20)     # sans rejeu : « : veille » au bout de 15 s
    c.request("GET", "/flux?depuis=0", headers={"Last-Event-ID": "60"})
    debut = c.getresponse().read1(4096).decode("utf-8", "replace")
    c.close()
    verifie(('"type": "debut"' in debut), True, "flux : Last-Event-ID d'un serveur precedent -> evenements rejoues")
    srv.shutdown()


def groupe_assistant(dossier):
    """Routes /assistant, /trois-voies, /assistant/action sur un faux depot (racine) et un faux script (session)."""
    print("\n== assistant (faux depot)")
    import faux_depot_synchro as fd
    with tempfile.TemporaryDirectory() as tmp:
        travail = fd.cree(Path(tmp))
        fd.commit_amont(tmp, {"a.txt": "amont\n"}, "amont change a")
        fd.git(travail, "fetch", "-q", "upstream")
        appels = []

        libere = Event()

        def builds():                                  # 1er appel bloque jusqu'au 409 du 2e clic : course deterministe
            appels.append(1)
            if len(appels) == 1:
                libere.wait(60)
            return []

        session = synchro_fork_session.Session(dossier=dossier)
        acces = acces_web.Acces(0, False, "banc")
        gest = synchro_fork_web.fabrique_gestionnaire(session, acces, racine=travail, builds_en_cours=builds)
        srv = ThreadingHTTPServer(("127.0.0.1", 0), gest)
        acces.port = port = srv.server_address[1]
        acces.cookie = f"jeton_{port}"
        Thread(target=srv.serve_forever, daemon=True).start()
        x = {"X-Synchro": "1", "Content-Type": "application/json"}
        action = "/assistant/action"
        statut, corps = requete("127.0.0.1", port, "GET", "/assistant", delai=60)
        verifie((statut, isinstance(json.loads(corps).get("etapes"), list)), (200, True), "GET /assistant : etapes")
        verifie(requete("127.0.0.1", port, "POST", action, {"action": "merge"})[0], 403, "POST sans X-Synchro refuse")
        verifie(requete("127.0.0.1", port, "POST", action, {"action": "rm"}, x)[0], 400, "action inconnue refusee")
        verifie(requete("127.0.0.1", port, "POST", action, {"action": "pousse"}, x)[0], 400,
                "pousse sans confirmation refusee")
        verifie(requete("127.0.0.1", port, "POST", action, {"action": "abandonne", "confirmation": "non"}, x)[0],
                400, "abandonne sans confirmation 'oui' refuse")
        verifie(requete("127.0.0.1", port, "GET", "/trois-voies?chemin=../../Windows/win.ini")[0], 400,
                "trois-voies hors liste refuse")
        verifie(len(appels), 0, "refus sans toucher aux builds")
        # session occupee (faux script en attente d'une question) -> 409
        session.lance("merge")
        attend(lambda: session.etat()["question"] is not None)
        verifie(requete("127.0.0.1", port, "POST", action, {"action": "bascule"}, x)[0], 409,
                "action pendant une execution de la session : 409")
        session.repond("n")
        attend(lambda: not session.en_cours())
        # double clic : exactement un 200 et un 409
        statuts = []

        def clic():
            try:
                statuts.append(requete("127.0.0.1", port, "POST", action, {"action": "merge"}, x, delai=60)[0])
            except Exception as e:  # noqa: BLE001  (une exception de thread serait invisible : on la note)
                statuts.append(repr(e))
        fils = [Thread(target=clic) for _ in range(2)]
        fils[0].start()
        attend(lambda: len(appels) >= 1, 30)            # le 1er clic tient le verrou, bloque dans builds()
        fils[1].start()
        attend(lambda: len(statuts) >= 1, 30)           # le 2e clic a recu son 409
        libere.set()
        for f in fils:
            f.join()
        verifie(sorted(statuts), [200, 409], "double clic sur merge : un 200 et un 409")
        synchro_fork_web.VERROU.acquire()               # une action de l'assistant tient le verrou : /lance refuse
        try:
            verifie(requete("127.0.0.1", port, "POST", "/lance", {"script": "merge"}, x)[0], 409,
                    "lancement d'un script pendant une action de l'assistant : 409")
        finally:
            synchro_fork_web.VERROU.release()
        statut, corps = requete("127.0.0.1", port, "POST", action, {"action": "abandonne", "confirmation": "oui"}, x)
        verifie((statut, json.loads(corps).get("ok") if statut == 200 else corps), (200, True), "abandonne confirme")
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
        groupe_assistant(dossier)
    if "--reel" in sys.argv:
        groupe_reel()
    print("\nVERT" if not ECHECS else f"\nROUGE : {len(ECHECS)} echec(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
