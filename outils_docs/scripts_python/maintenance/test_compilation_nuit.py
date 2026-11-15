"""Banc de compilation_nuit.py : faux serveur de build (memes routes et formats que build_web.py), aucun pio.

    python outils_docs/scripts_python/maintenance/test_compilation_nuit.py     (code de sortie 0 = vert)
"""

import json
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compilation_nuit as cn

ENVS = [{"nom": "a", "ecrivable": True}, {"nom": "b", "ecrivable": True}, {"nom": "c", "ecrivable": True},
        {"nom": "amont", "ecrivable": False}]


class Faux:
    def __init__(self, resultats, refus=None, polls=1, ancienne=False, tombe=False):
        self.resultats, self.refus, self.polls, self.tombe = resultats, refus, polls, tombe
        # ancienne serie deja servie par la page : 3 evenements dont un `fin` ; les numeros de la nouvelle repartent apres
        self.ancienne = [{"n": 1, "type": "fin_env", "env": "vieux", "resultat": "echec", "secondes": 9.0},
                         {"n": 2, "type": "fin_env", "env": "vieux2", "resultat": "echec", "secondes": 9.0},
                         {"n": 3, "type": "fin", "env": None, "resultat": "arrete"}] if ancienne else []
        self.lance, self.arrets, self.n = None, 0, 0
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def rep(self, code, corps, type_="application/json"):
                donnees = (json.dumps(corps) if type_ == "application/json" else corps).encode()
                self.send_response(code)
                self.send_header("Content-Type", type_)
                self.send_header("Content-Length", str(len(donnees)))
                self.end_headers()
                self.wfile.write(donnees)

            def do_GET(self):
                if self.path == "/execution":
                    outer.n += 1
                    if outer.tombe and outer.lance is not None:
                        return self.connection.close()          # la page tombe pendant l'attente
                    self.rep(200, {"en_cours": outer.lance is not None and outer.n <= outer.polls,
                                   "numero": len(outer.ancienne), "pause": None})
                elif self.path == "/envs":
                    self.rep(200, {"envs": ENVS, "derniers": {}})
                elif self.path.startswith("/flux"):
                    base = len(outer.ancienne)
                    evts = outer.ancienne + [{"n": base + i + 1, "type": "fin_env", "env": e, "resultat": r, "secondes": 1.5}
                                              for i, (e, r) in enumerate(outer.resultats.items())]
                    evts.append({"n": base + 99, "type": "fin", "env": None, "resultat": "termine"})
                    depuis = int(self.path.split("depuis=")[1]) if "depuis=" in self.path else 0
                    corps = "".join(f"id: {e['n']}\ndata: {json.dumps(e)}\n\n" for e in evts if e["n"] > depuis)
                    self.rep(200, corps, "text/event-stream")
                else:
                    self.rep(404, "x", "text/plain")

            def do_POST(self):
                if self.headers.get("X-Build") != "1":
                    return self.rep(403, "refuse", "text/plain")
                corps = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path == "/lancer":
                    if outer.refus:
                        return self.rep(409, outer.refus, "text/plain")
                    outer.lance = corps
                    return self.rep(200, {"ok": True})
                if self.path == "/arreter":
                    outer.arrets += 1
                    return self.rep(200, {"ok": True})
                self.rep(404, "x", "text/plain")

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def ferme(self):
        self.srv.shutdown()


ECHECS = []


def verifie(nom, condition):
    print(("OK   " if condition else "ECHEC"), nom)
    if not condition:
        ECHECS.append(nom)


def lance(faux, **config):
    dossier = tempfile.mkdtemp()
    conf = {**cn.CONFIG_DEFAUT, "port": faux.port, **config}
    code, res = cn.execute(conf, dossier, pause=0.01)
    return code, res, Path(dossier)


# 1. nominal : seuls les envs ecrivables partent, en « compiler » seul, resultat ecrit
f = Faux({"a": "succes", "b": "succes", "c": "succes"})
code, res, d = lance(f)
verifie("nominal : code 0", code == 0)
verifie("nominal : 3 envs ecrivables, pas l'amont", [l["env"] for l in f.lance["lignes"]] == ["a", "b", "c"])
verifie("nominal : action compiler seule", f.lance["actions"] == ["compiler"])
verifie("nominal : resultat par env lu", [e["resultat"] for e in res["envs"]] == ["succes"] * 3)
verifie("nominal : dernier.json ecrit", json.loads((d / "dernier.json").read_text(encoding="utf-8"))["code"] == 0)
f.ferme()

# 2. un env en echec -> code 1, l'env fautif nomme
f = Faux({"a": "succes", "b": "echec", "c": "succes"})
code, res, d = lance(f)
verifie("echec : code 1", code == 1)
verifie("echec : env fautif relu", [e["env"] for e in res["envs"] if e["resultat"] == "echec"] == ["b"])
f.ferme()

# 3. exclusion d'un env
f = Faux({"a": "succes", "c": "succes"})
code, res, d = lance(f, envs_exclus=["b"])
verifie("exclusion : b non lance", [l["env"] for l in f.lance["lignes"]] == ["a", "c"] and res["envs_exclus"] == ["b"])
f.ferme()

# 4. page qui refuse (build deja en cours) : code 2, motif conserve, jamais d'attente
f = Faux({}, refus="un build est en cours (tasmota32-base)")
code, res, d = lance(f)
verifie("refus 409 : code 2 et motif", code == 2 and "un build est en cours" in res["refus"])
verifie("refus 409 : resultat ecrit", (d / "dernier.json").exists())
f.ferme()

# 5. desactive : code 3, aucun appel, aucune trace
f = Faux({"a": "succes"})
code, res, d = lance(f, actif=False)
verifie("desactive : code 3, rien lance, rien ecrit", code == 3 and f.lance is None and not (d / "dernier.json").exists())
f.ferme()

# 6. dry-run : liste les envs, ne lance rien
f = Faux({"a": "succes"})
dossier = tempfile.mkdtemp()
code, res = cn.execute({**cn.CONFIG_DEFAUT, "port": f.port}, dossier, dry_run=True)
verifie("dry-run : envs prevus, rien lance", code == 0 and res["envs_prevus"] == ["a", "b", "c"] and f.lance is None)
f.ferme()

# 7. Ctrl+C pendant l'attente : arret immediat envoye a la page
f = Faux({"a": "succes"}, polls=10**9)
original = cn.time.sleep
cn.time.sleep = lambda _s: (_ for _ in ()).throw(KeyboardInterrupt())
try:
    code, res, d = lance(f)
finally:
    cn.time.sleep = original
verifie("Ctrl+C : POST /arreter immediat, code 1", code == 1 and f.arrets == 1 and "Ctrl+C" in res["fin"])
f.ferme()

# 7b. la page a deja servi une serie : son `fin` et ses fin_env ne doivent pas entrer dans le bilan
f = Faux({"a": "succes", "b": "succes", "c": "succes"}, ancienne=True)
code, res, d = lance(f)
verifie("ancienne serie : ignoree, bilan de la seule serie", code == 0 and [e["env"] for e in res["envs"]] == ["a", "b", "c"])
f.ferme()

# 7c. la page tombe pendant l'attente : resultat ecrit, code 1, jamais de traceback
f = Faux({"a": "succes"}, polls=10**9, tombe=True)
code, res, d = lance(f)
verifie("page tombee : code 1, motif, resultat ecrit", code == 1 and "injoignable" in res["fin"] and (d / "dernier.json").exists())
f.ferme()

# 7d. page deja morte au depart et impossible a demarrer : code 2, pas de traceback
original_demarre = cn.demarre_page
cn.demarre_page = lambda *a, **k: False
try:
    dossier = tempfile.mkdtemp()
    code, res = cn.execute({**cn.CONFIG_DEFAUT, "port": 1}, dossier, pause=0.01)
finally:
    cn.demarre_page = original_demarre
verifie("page absente : code 2", code == 2 and "ne repond pas" in res["refus"])

# 7e. verrou : un autre compilation_nuit.py VIVANT -> refus sans rien lancer ; fichier perime -> ignore ; libere en fin de run
import subprocess
import os
enfant = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
try:
    f = Faux({"a": "succes"})
    dossier = tempfile.mkdtemp()
    Path(dossier, "en_cours.json").write_text(json.dumps({"pid": enfant.pid}), encoding="utf-8")
    code, res = cn.execute({**cn.CONFIG_DEFAUT, "port": f.port}, dossier, pause=0.01)
    verifie("verrou vivant : code 2, motif, rien lance", code == 2 and "deja en cours" in res["refus"] and f.lance is None)
    verifie("verrou vivant : le verrou de l'autre n'est PAS supprime", Path(dossier, "en_cours.json").exists()
            and json.loads(Path(dossier, "en_cours.json").read_text(encoding="utf-8"))["pid"] == enfant.pid)
    f.ferme()
finally:
    enfant.kill()
    enfant.wait()
f = Faux({"a": "succes", "b": "succes", "c": "succes"})
dossier = tempfile.mkdtemp()
Path(dossier, "en_cours.json").write_text(json.dumps({"pid": enfant.pid}), encoding="utf-8")   # pid maintenant mort
code, res = cn.execute({**cn.CONFIG_DEFAUT, "port": f.port}, dossier, pause=0.01)
verifie("verrou perime (processus mort) : ignore, la nuit tourne", code == 0 and f.lance is not None)
verifie("verrou libere en fin de run", not Path(dossier, "en_cours.json").exists())
f.ferme()
f = Faux({}, refus="un build est en cours")
dossier = tempfile.mkdtemp()
code, res = cn.execute({**cn.CONFIG_DEFAUT, "port": f.port}, dossier, pause=0.01)
verifie("verrou libere aussi apres un refus de la page", code == 2 and not Path(dossier, "en_cours.json").exists())
f.ferme()
verifie("pid_vivant : soi-meme oui, absurde non", cn.pid_vivant(os.getpid()) and not cn.pid_vivant(0) and not cn.pid_vivant("x") and not cn.pid_vivant(-4))

# 8. config absente ou illisible : valeurs par defaut
d = tempfile.mkdtemp()
(Path(d) / "config.json").write_text("{pas du json", encoding="utf-8")
verifie("config illisible : defauts", cn.lit_config(d) == cn.CONFIG_DEFAUT)
(Path(d) / "config.json").write_text(json.dumps({"actif": False, "envs_exclus": ["x"]}), encoding="utf-8")
verifie("config lue", cn.lit_config(d)["actif"] is False and cn.lit_config(d)["envs_exclus"] == ["x"])

print("\nVERT" if not ECHECS else f"\nROUGE : {ECHECS}")
sys.exit(1 if ECHECS else 0)
