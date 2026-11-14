"""Banc de menage_web (routes, anti-CSRF, Host, jeton, build, rapport filtre, a garder). Code de sortie 0 = vert.

Serveur reel sur 127.0.0.1, port libre, faux `claude`, depot et dossier de donnees temporaires. Aucun vrai claude, aucun build.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_menage_web.py
"""
import http.client
import json
import os
import socket
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

import acces_web
import menage_web as mw

ECHECS = []
TMP = Path(tempfile.mkdtemp())
RACINE = TMP / "depot"
(RACINE / "tasks").mkdir(parents=True)
(RACINE / "tasks" / "README.md").write_text("x", encoding="utf-8")
(RACINE / "tasks" / "autre.md").write_text("x", encoding="utf-8")
FAUX = TMP / "faux_claude.py"
FAUX.write_text('''
import json, sys, time
sys.stdin.buffer.read()
props = [{"id": "M1", "categorie": "reste", "chemin": "tasks/README.md", "constat": "c", "preuve": "p", "action": "archiver",
          "casserait": "rien", "risque": "faible", "en_cours": False},
         {"id": "M2", "categorie": "orphelin", "chemin": "tasks/autre.md", "constat": "c", "preuve": "p", "action": "supprimer",
          "casserait": "rien", "risque": "moyen", "en_cours": False}]
import os
if os.environ.get("FAUX_LENT"):
    time.sleep(60)
print(json.dumps({"is_error": False, "result": json.dumps({"resume": "2", "propositions": props})}))
''', encoding="utf-8")


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Serveur:
    def __init__(self, builds=lambda: []):
        self.port = port_libre()
        self.acces = acces_web.Acces(self.port, True, "Menage du depot")
        self.etat = mw.Etat(RACINE, builds, programme=[sys.executable, str(FAUX)], dossier=TMP / "donnees", delai=20)
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port), mw.fabrique_gestionnaire(self.acces, self.etat))
        self.serveur.daemon_threads = True
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def req(self, methode, chemin, corps=None, entetes=None, brut=None):
        h = {"Content-Type": "application/json"}
        if methode == "POST":
            h[mw.ENTETE] = "1"
        h.update(entetes or {})
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        data = brut if brut is not None else (json.dumps(corps).encode("utf-8") if corps is not None else None)
        c.request(methode, chemin, body=data, headers=h)
        r = c.getresponse()
        texte = r.read().decode("utf-8", "replace")
        c.close()
        return r.status, texte

    def attend(self, delai=30):
        t = time.time()
        while self.etat.audit.etat()["etat"] == "en_cours" and time.time() - t < delai:
            time.sleep(0.05)

    def ferme(self):
        self.serveur.shutdown()
        self.serveur.server_close()


s = Serveur()
verifie(s.req("GET", "/")[0], 200, "GET / : la page")
st, t = s.req("GET", "/options")
verifie((st, "sonnet" in t and "orphelin" in t), (200, True), "GET /options")
verifie(json.loads(s.req("GET", "/etat")[1])["etat"], "repos", "etat au depart")
verifie(s.req("GET", "/rapport")[0], 404, "pas de rapport au depart")
verifie(s.req("GET", "/inconnu")[0], 404, "route inconnue")

# anti-CSRF, Host, corps
verifie(s.req("POST", "/lancer", {}, {mw.ENTETE: "0"})[0], 403, "POST sans l'en-tete X-Menage")
verifie(s.req("POST", "/lancer", {}, {"Origin": "http://evil.example"})[0], 403, "POST d'une autre origine")
verifie(s.req("GET", "/etat", None, {"Host": "evil.example"})[0], 403, "Host etranger (DNS rebinding)")
verifie(s.req("POST", "/lancer", brut=b"[1,2]")[0], 400, "corps JSON pas un objet")
verifie(s.req("POST", "/lancer", brut=b"{pas du json")[0], 400, "JSON invalide")
verifie(s.req("POST", "/lancer", None, {"Content-Length": str(mw.MAX_CORPS + 1)}, brut=b"{}")[0] in (400, 403), True, "corps trop grand")
for libelle, corps in [("zone hors liste blanche", {"zone": ["/etc"]}), ("modele hostile", {"modele": "opus --x"}),
                       ("anciennete texte", {"anciennete_jours": "3; rm"})]:
    verifie(s.req("POST", "/lancer", corps)[0], 400, f"parametre refuse : {libelle}")
verifie(s.req("POST", "/garder", {"chemin": "tasks/README.md"})[0], 404, "garder sans rapport")
verifie(s.req("POST", "/ignorer", {"id": "M1"})[0], 404, "ignorer sans rapport")

# client distant sans jeton
vrai = acces_web.est_local
acces_web.est_local = lambda adresse: False
try:
    verifie(s.req("GET", "/etat")[0], 403, "client distant sans jeton : GET refuse")
    verifie(s.req("POST", "/lancer", {})[0], 403, "client distant sans jeton : POST refuse")
    verifie(json.loads(s.req("GET", f"/etat?jeton={s.acces.jeton}")[1] or "{}") if False else s.req("GET", f"/etat?jeton={s.acces.jeton}")[0], 303, "client distant avec jeton : redirection")
finally:
    acces_web.est_local = vrai

# audit complet
st, t = s.req("POST", "/lancer", {"zone": ["tasks"], "anciennete_jours": 2})
verifie(st, 200, "lancer")
s.attend()
e = json.loads(s.req("GET", "/etat")[1])
verifie((e["etat"], e["propositions"]), ("fini", 2), "audit fini, 2 propositions")
r = json.loads(s.req("GET", "/rapport")[1])
verifie([p["id"] for p in r["propositions"]], ["M1", "M2"], "rapport : 2 propositions")

# ignorer, garder, degarder
verifie(s.req("POST", "/ignorer", {"id": "M9"})[0], 404, "ignorer : id inconnu")
verifie(s.req("POST", "/ignorer", {"id": "M1"})[0], 200, "ignorer M1")
verifie([p["id"] for p in json.loads(s.req("GET", "/rapport")[1])["propositions"]], ["M2"], "M1 absente du rapport")
verifie(s.req("POST", "/garder", {"chemin": "tasks/inconnu.md"})[0], 404, "garder : chemin hors rapport")
verifie(s.req("POST", "/garder", {"chemin": "../hors.txt"})[0], 404, "garder : chemin .. refuse")
verifie(s.req("POST", "/garder", {"chemin": "tasks/autre.md"})[0], 200, "garder tasks/autre.md")
verifie(json.loads(s.req("GET", "/gardes")[1])["gardes"], ["tasks/autre.md"], "GET /gardes")
verifie(json.loads(s.req("GET", "/rapport")[1])["propositions"], [], "M2 gardee : absente du rapport")
verifie(s.req("POST", "/degarder", {"chemin": "tasks/autre.md"})[0], 200, "degarder")
verifie(s.req("POST", "/degarder", {"chemin": "tasks/autre.md"})[0], 404, "degarder : absent")
verifie([p["id"] for p in json.loads(s.req("GET", "/rapport")[1])["propositions"]], ["M2"], "M2 de retour apres degarder")

# relancer : les « ignorees » sont oubliees
s.req("POST", "/lancer", {})
s.attend()
verifie([p["id"] for p in json.loads(s.req("GET", "/rapport")[1])["propositions"]], ["M1", "M2"], "relance : M1 revient")

# double lancement, arret
os.environ["FAUX_LENT"] = "1"
verifie(s.req("POST", "/lancer", {})[0], 200, "lancer (audit lent)")
time.sleep(1)
verifie(s.req("POST", "/lancer", {})[0], 409, "2e lancement : 409")
verifie(s.req("POST", "/arreter", {})[0], 200, "arreter")
s.attend(20)
verifie(json.loads(s.req("GET", "/etat")[1])["etat"], "echec", "audit arrete")
del os.environ["FAUX_LENT"]
s.ferme()

# build en cours
s2 = Serveur(builds=lambda: ["pio run -e x"])
st, t = s2.req("POST", "/lancer", {})
verifie((st, "build" in t), (409, True), "build en cours : 409")
s2.ferme()

# mutant : si l'origine n'etait pas controlee, une origine etrangere passerait (le banc le voit)
s3 = Serveur()
s3.acces.origine_autorisee = lambda handler: True
verifie(s3.req("POST", "/lancer", {"zone": ["/etc"]}, {"Origin": "http://evil.example"})[0], 400, "mutant sans controle d'origine : passe jusqu'a la validation (donc le banc 403 etait discriminant)")
s3.ferme()

if ECHECS:
    print(f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1)
print("VERT : menage_web")
