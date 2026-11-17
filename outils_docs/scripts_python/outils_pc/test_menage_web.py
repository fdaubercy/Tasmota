"""Banc de menage_web (routes, anti-CSRF, Host, jeton, build, rapport filtre, a garder). Code de sortie 0 = vert.

Serveur reel sur 127.0.0.1, port libre, faux `claude`, depot et dossier de donnees temporaires. Aucun vrai claude, aucun build.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_menage_web.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import http.client
import json
import os
import socket
import sys
import tempfile
import threading
import time
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
        self.serveur = mw.ServeurMenage(("127.0.0.1", self.port), mw.fabrique_gestionnaire(self.acces, self.etat))
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
verifie(s.req("POST", "/appliquer/apercu", {"ids": ["M1"]})[0], 404, "apercu sans rapport")
verifie(s.req("POST", "/appliquer", {"ids": ["M1"], "empreinte": "x", "head": "y", "confirme": True})[0], 404, "appliquer sans rapport")

# client distant sans jeton
vrai = acces_web.est_local
acces_web.est_local = lambda adresse: False
try:
    verifie(s.req("GET", "/etat")[0], 403, "client distant sans jeton : GET refuse")
    verifie(s.req("POST", "/lancer", {})[0], 403, "client distant sans jeton : POST refuse")
    verifie(json.loads(s.req("GET", f"/etat?jeton={s.acces.jeton}")[1] or "{}") if False else s.req("GET", f"/etat?jeton={s.acces.jeton}")[0], 303, "client distant avec jeton : redirection")
finally:
    acces_web.est_local = vrai

# etat : activite et progression (curseur ?depuis=)
e0 = json.loads(s.req("GET", "/etat")[1])
verifie((e0["appels"], e0["progression"], e0["activite"]), (0, 0, []), "etat : pas d'activite au repos")
s.etat.audit._etat.update(appels=7, progression=19, activite=[{"t": i, "outil": "Grep", "detail": f"a{i}"} for i in (5, 6, 7)])   # 3 gardees sur 7 : les 3 dernieres, rangs 4 a 6 (base 0)
verifie([x["t"] for x in json.loads(s.req("GET", "/etat")[1])["activite"]], [5, 6, 7], "etat : tout le journal sans curseur")
verifie([x["t"] for x in json.loads(s.req("GET", "/etat?depuis=6")[1])["activite"]], [7], "etat : curseur depuis=6 (6 deja recues), seulement la 7e")
verifie(json.loads(s.req("GET", "/etat?depuis=abc")[1])["progression"], 19, "etat : curseur illisible ignore")
s.etat.audit._etat.update(appels=0, progression=0, activite=[])

# audit complet
st, t = s.req("POST", "/lancer", {"zone": ["tasks"], "anciennete_jours": 2})
verifie(st, 200, "lancer")
s.attend()
e = json.loads(s.req("GET", "/etat")[1])
verifie((e["etat"], e["propositions"]), ("fini", 2), "audit fini, 2 propositions")
r = json.loads(s.req("GET", "/rapport")[1])
verifie([p["id"] for p in r["propositions"]], ["M1", "M2"], "rapport : 2 propositions")

# apercu d'un lot de deplacements : lecture seule, refus de ce qui n'est pas un deplacement
st, t = s.req("POST", "/appliquer/apercu", {"ids": ["M1", "M2", "M9"]})
ap = json.loads(t) if st == 200 else {}
verifie((st, sorted(x["id"] for x in ap.get("refuses", [])), ap.get("eligibles")), (200, ["M1", "M2", "M9"], []), "apercu : archiver, supprimer et inconnue refuses, rien d'eligible")
verifie(s.req("POST", "/appliquer/apercu", {"ids": []})[0], 400, "apercu : lot vide refuse")
# application REELLE : seulement des refus ici (RACINE est le vrai depot, une application reussie y toucherait a de vrais fichiers)
verifie(s.req("POST", "/appliquer", {"ids": ["M2"], "empreinte": "x", "head": "y"})[0], 400, "appliquer sans confirmation explicite : refuse")
verifie(s.req("POST", "/appliquer", {"ids": ["M2"], "empreinte": "x", "head": "y", "confirme": "oui"})[0], 400, "appliquer : confirme doit etre le booleen true")
_est_local = mw.acces_web.est_local
mw.acces_web.est_local = lambda adresse: False
verifie(s.req("POST", "/appliquer", {"ids": ["M2"], "empreinte": "0" * 16, "head": "inconnu", "a_blanc": True})[0], 403, "appliquer depuis un autre appareil : 403, meme a blanc")
mw.acces_web.est_local = _est_local
verifie(s.req("POST", "/appliquer/apercu", {"ids": ["M2"]})[0], 200, "l'apercu (lecture seule) reste permis, lui")
# retour en arriere : la page n'envoie qu'un numero, le serveur defait SA derniere application (RACINE : faux depot, annule() simule)
verifie(s.req("POST", "/appliquer/annuler", {"application": 1})[0], 404, "annuler sans aucune application : 404")
verifie(s.req("POST", "/appliquer/annuler", {"application": 1}, {mw.ENTETE: "0"})[0], 403, "annuler sans l'en-tete X-Menage : 403")
mw.acces_web.est_local = lambda adresse: False
verifie(s.req("POST", "/appliquer/annuler", {"application": 1})[0], 403, "annuler depuis un autre appareil : 403")
mw.acces_web.est_local = _est_local
s.etat.applications.extend([{"numero": 1, "head": "h", "faits": [{"id": "A"}]}, {"numero": 2, "head": "h", "faits": [{"id": "B"}, {"id": "C"}]}])
st, tx = s.req("GET", "/appliquer/derniere")
verifie((st, json.loads(tx)["application"], [f["id"] for f in json.loads(tx)["faits"]]), (200, 2, ["B", "C"]), "GET /appliquer/derniere : la derniere application de la pile (le bouton survit a un rechargement)")
mw.menage_application._VERROU.acquire()
try:
    st, tx = s.req("POST", "/appliquer/apercu", {"ids": ["M2"]})
    verifie((st, "en cours" in tx), (409, True), "apercu refuse pendant une application (git -n prendrait le verrou d'index du lot)")
finally:
    mw.menage_application._VERROU.release()
verifie(s.req("POST", "/appliquer/annuler", {"application": 1})[0], 409, "annuler une application qui n'est pas la derniere : 409")
verifie(s.req("POST", "/appliquer/annuler", {})[0], 409, "annuler sans numero : 409")
vrai_annule = mw.menage_application.annule
appels = []
mw.menage_application.annule = lambda faits, head, racine, builds_en_cours, journal=None: (appels.append([f["id"] for f in faits]),
    {"retablis": [{"id": "C", "action": "supprimer", "chemin": "c"}], "echec": {"id": "B", "chemin": "b", "motif": "x"}, "restants": ["B"]})[1]
st, t = s.req("POST", "/appliquer/annuler", {"application": 2})
verifie((st, json.loads(t)["restants"], appels, [f["id"] for f in s.etat.applications[-1]["faits"]]), (200, ["B"], [["B", "C"]], ["B"]), "annulation partielle : la pile garde les lignes non defaites")
mw.menage_application.annule = lambda faits, head, racine, builds_en_cours, journal=None: {"retablis": [{"id": "B", "action": "supprimer", "chemin": "b"}], "echec": None, "restants": []}
verifie(s.req("POST", "/appliquer/annuler", {"application": 2})[0], 200, "annulation terminee : 200")
verifie([a["numero"] for a in s.etat.applications], [1], "annulation terminee : la derniere application sort de la pile")
mw.menage_application.annule = vrai_annule
s.etat.applications.clear()
verifie(json.loads(s.req("GET", "/appliquer/derniere")[1])["application"], None, "GET /appliquer/derniere : rien quand la pile est vide")
verifie(s.req("POST", "/appliquer", {"ids": ["M2"], "empreinte": "0" * 16, "head": "inconnu", "a_blanc": True})[0], 409, "a blanc : sans confirmation, mais meme refus d'un apercu perime (409)")
verifie(s.req("POST", "/appliquer", {"ids": ["M2"], "empreinte": "x", "head": "y", "a_blanc": "oui"})[0], 400, "a_blanc doit etre un booleen")
verifie(s.req("POST", "/appliquer", {"ids": ["M2"], "confirme": True})[0], 400, "appliquer sans empreinte ni head : refuse")
verifie(s.req("POST", "/appliquer", {"ids": ["M2"], "empreinte": "0" * 16, "head": "inconnu", "confirme": True})[0], 409, "appliquer avec une empreinte qui n'est pas celle de l'apercu : 409, rien applique")
verifie(s.req("POST", "/appliquer/apercu", {"ids": "M1"})[0], 400, "apercu : ids pas une liste")

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
st, t = s2.req("POST", "/appliquer/apercu", {"ids": ["M1"]})
verifie((st, "build" in t), (409, True), "apercu pendant un build : 409")
s2.ferme()

# rouvrir un rapport sauvegarde (A4 de menage-appliquer) : audit, « redemarrage » de la page, puis ouverture
s4 = Serveur()
verifie(s4.req("POST", "/lancer", {})[0], 200, "rapports : un audit pour avoir un rapport sauvegarde")
s4.attend(30)
time.sleep(0.5)
s4.ferme()
s5 = Serveur()                                                   # meme dossier de donnees, etat neuf : la page redemarree
verifie(s5.req("GET", "/rapport")[0], 404, "page redemarree : pas de rapport en memoire")
st, t = s5.req("GET", "/rapports")
liste = json.loads(t)["rapports"] if st == 200 else []
verifie((st, len(liste) >= 1, liste and liste[0]["propositions"]), (200, True, 2), "GET /rapports : le rapport sauvegarde est liste (le plus recent d'abord)")
nom = liste[0]["nom"]
verifie(s5.req("POST", "/rapports/ouvrir", {"nom": nom}, {mw.ENTETE: "0"})[0], 403, "ouvrir sans l'en-tete X-Menage : 403")
verifie(s5.req("POST", "/rapports/ouvrir", {"nom": nom}, {"Origin": "http://evil.example"})[0], 403, "ouvrir d'une autre origine : 403")
for hostile in ["../donnees/rapports/" + nom, "rapport-inconnu.json", "", None, 7]:
    verifie(s5.req("POST", "/rapports/ouvrir", {"nom": hostile})[0], 404, f"ouvrir un nom hors liste : {hostile!r} : 404")
verifie(s5.req("POST", "/rapports/ouvrir", {})[0], 404, "ouvrir sans nom : 404")
verifie(s5.req("GET", "/rapport")[0], 404, "refus : toujours pas de rapport en memoire")
st, t = s5.req("POST", "/rapports/ouvrir", {"nom": nom})
verifie((st, "rouvert" in t), (200, True), "ouvrir un rapport de la liste : 200")
st, t = s5.req("GET", "/rapport")
verifie((st, st == 200 and len(json.loads(t)["propositions"])), (200, 2), "le rapport rouvert est celui de la page")
verifie(s5.req("POST", "/ignorer", {"id": "M1"})[0], 200, "ignorer M1 sur le rapport rouvert")
verifie(len(json.loads(s5.req("GET", "/rapport")[1])["propositions"]), 1, "M1 ignoree : absente")
verifie(s5.req("POST", "/rapports/ouvrir", {"nom": nom})[0], 200, "rouvrir le meme rapport")
verifie(len(json.loads(s5.req("GET", "/rapport")[1])["propositions"]), 2, "rouvrir remet a zero les « ignorees cette fois »")
dossier_r = TMP / "donnees" / "rapports"
(dossier_r / "rapport-zz-illisible.json").write_text("pas du json", encoding="utf-8")
verifie(s5.req("POST", "/rapports/ouvrir", {"nom": "rapport-zz-illisible.json"})[0], 400, "rapport illisible : 400")
verifie(len(json.loads(s5.req("GET", "/rapport")[1])["propositions"]), 2, "rapport illisible : le rapport de la page reste en place")
os.environ["FAUX_LENT"] = "1"
verifie(s5.req("POST", "/lancer", {})[0], 200, "rapports : audit lent pour le refus pendant un audit")
time.sleep(1)
verifie(s5.req("POST", "/rapports/ouvrir", {"nom": nom})[0], 409, "ouvrir pendant un audit : 409")
s5.req("POST", "/arreter", {})
s5.attend(20)
del os.environ["FAUX_LENT"]
s5.ferme()

# mutant : si l'origine n'etait pas controlee, une origine etrangere passerait (le banc le voit)
s3 = Serveur()
s3.acces.origine_autorisee = lambda handler: True
verifie(s3.req("POST", "/lancer", {"zone": ["/etc"]}, {"Origin": "http://evil.example"})[0], 400, "mutant sans controle d'origine : passe jusqu'a la validation (donc le banc 403 etait discriminant)")
s3.ferme()

if ECHECS:
    print(f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1)
print("VERT : menage_web")
