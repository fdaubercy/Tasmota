"""Banc de build_web (serveur de la page Build et televersement) : routes, refus, flux, arret.

Code de sortie 0 = vert. Le VRAI pio n'est jamais lance : BUILD_WEB_PIO est pose sur build_faux_pio.py.
Depot d'essai, donnees de l'outil (OUTILS_TASMOTA_DOSSIER) et journal du faux pio : dossiers
temporaires ; le serveur ecoute sur un port libre, en 127.0.0.1, sans fiche de presence.
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

ICI = Path(__file__).resolve().parent
os.environ["BUILD_WEB_PIO"] = str(ICI / "build_faux_pio.py")

import acces_web                                  # noqa: E402
import build_faux_pio as faux                    # noqa: E402
import build_serie as bs                         # noqa: E402  (apres BUILD_WEB_PIO)
import build_web                                 # noqa: E402

ECHECS = []
A, B = "tasmota32-essai-a", "tasmota32-essai-b"
CENV = f"""\
[env:tasmota32-essai-base]
extra_scripts           = pre:outils_docs/scripts_python/build/pre_utilitaires_platformio.py

[env:{A}]
extends                 = env:tasmota32-essai-base
upload_port             = COM12

[env:{B}]
extends                 = env:tasmota32-essai-base
"""
LIGNE_A = {"env": A, "methode": "com", "port": "COM12", "ip": ""}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


class Banc:
    """Depot d'essai + Serie sur faux pio + serveur HTTP dans un fil."""

    def __init__(self, t, scenario=None):
        t = Path(t)
        self.racine, self.dossier = t / "depot", t / "donnees"
        self.racine.mkdir()
        (self.racine / "platformio_tasmota_cenv.ini").write_text(CENV, encoding="utf-8")
        scen = t / "scenario.json"
        scen.write_text(json.dumps(scenario or {}), encoding="utf-8")
        os.environ[faux.VAR_SCENARIO] = str(scen)
        os.environ[faux.VAR_JOURNAL] = str(t / "journal.jsonl")
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.acces = acces_web.Acces(self.port, True, "Build et téléversement")
        self.serie = bs.Serie(self.racine, self.dossier, builds_en_cours=lambda: [],
                              port_libre=lambda p: "libre", ota_firmware=None, sondage=0.05)
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port), build_web.fabrique_gestionnaire(
            self.serie, self.acces, self.racine, self.dossier))
        self.serveur.daemon_threads = True
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def requete(self, methode, chemin, corps=None, entetes=None, brut=None):
        """(statut, texte) ; POST avec l'en-tete X-Build par defaut."""
        h = dict(entetes if entetes is not None else ({"X-Build": "1"} if methode == "POST" else {}))
        donnees = brut if brut is not None else (json.dumps(corps).encode("utf-8") if corps is not None else None)
        if donnees is not None:
            h["Content-Type"] = "application/json"
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            c.request(methode, chemin, body=donnees, headers=h)
            r = c.getresponse()
            return r.status, r.read().decode("utf-8")
        except (ConnectionError, OSError) as erreur:       # serveur qui coupe avant la fin du corps
            return 0, repr(erreur)
        finally:
            c.close()

    def json(self, methode, chemin, corps=None):
        statut, texte = self.requete(methode, chemin, corps)
        try:
            return statut, json.loads(texte)
        except ValueError:
            return statut, texte

    def attend_fin(self, delai=20.0):
        limite = time.monotonic() + delai
        while time.monotonic() < limite:
            if not self.serie.en_cours():
                return True
            time.sleep(0.05)
        ECHECS.append("delai depasse en attendant la fin du lancement")
        print("KO   delai depasse en attendant la fin du lancement")
        return False

    def ferme(self):
        self.serie.arrete(immediat=True)
        self.attend_fin(10)
        self.serveur.shutdown()
        self.serveur.server_close()


def lit_flux(banc, chemin="/flux", entetes=None, nombre=1):
    """Les `nombre` premiers evenements (id, objet) d'un flux SSE."""
    c = http.client.HTTPConnection("127.0.0.1", banc.port, timeout=10)
    c.request("GET", chemin, headers=entetes or {})
    r = c.getresponse()
    recus, id_ = [], None
    try:
        while len(recus) < nombre:
            ligne = r.readline().decode("utf-8").rstrip("\r\n")
            if ligne.startswith("id: "):
                id_ = int(ligne[4:])
            elif ligne.startswith("data: "):
                recus.append((id_, json.loads(ligne[6:])))
    finally:
        c.close()
    return r.status, recus


def test_routes_locales(b):
    statut, texte = b.requete("GET", "/")
    verifie((statut, "<html" in texte.lower()), (200, True), "routes_locales : GET / sert une page")
    statut, donnees = b.json("GET", "/envs")
    noms = [e["nom"] for e in donnees["envs"]] if statut == 200 else []
    verifie((statut, sorted(noms)), (200, sorted([A, B, "tasmota32-essai-base"])),
            "routes_locales : GET /envs liste les envs (famille bases comprise)")
    env_a = next((e for e in donnees["envs"] if e["nom"] == A), {})
    verifie((env_a.get("port"), env_a.get("famille"), env_a.get("littlefs")), ("COM12", "cartes", False),
            "routes_locales : champs de Env + littlefs")
    verifie(donnees["derniers"], {}, "routes_locales : derniers choix vides au depart")
    (b.racine / ".pio" / "build" / A).mkdir(parents=True)
    (b.racine / ".pio" / "build" / A / "littlefs.bin").write_bytes(b"x")
    _, donnees = b.json("GET", "/envs")
    verifie({e["nom"]: e["littlefs"] for e in donnees["envs"]}, {A: True, B: False, "tasmota32-essai-base": False},
            "routes_locales : littlefs vrai si littlefs.bin existe")
    verifie(b.json("GET", "/execution"), (200, {"en_cours": False}), "routes_locales : GET /execution")
    verifie(b.requete("GET", "/nimporte")[0], 404, "routes_locales : route inconnue = 404")
    verifie(b.requete("POST", "/nimporte", {})[0], 404, "routes_locales : POST inconnu = 404")
    verifie(b.requete("GET", "/journal?env=../x")[0], 400, "routes_locales : journal, nom d'env invalide = 400")
    verifie(b.requete("GET", "/journal?env=" + A)[0], 200, "routes_locales : journal sans fichier = 200 vide")


def test_post_sans_entete_refuse(b):
    corps = {"env": A, "port": "COM13"}
    verifie(b.requete("POST", "/port", corps, entetes={})[0], 403, "post_sans_entete_refuse : sans X-Build")
    verifie(b.requete("POST", "/port", corps, entetes={"X-Build": "1", "Origin": "http://evil.example"})[0], 403,
            "post_sans_entete_refuse : origine etrangere")
    verifie(b.requete("POST", "/port", corps, entetes={"X-Build": "1", "Origin": f"http://127.0.0.1:{b.port}"})[0],
            200, "post_sans_entete_refuse : origine propre acceptee")
    b.json("POST", "/port", {"env": A, "port": "COM12"})                     # remet le port d'origine


def test_distant_sans_jeton_refuse(b):
    vrai = acces_web.est_local
    acces_web.est_local = lambda adresse: False                              # le client « vient d'ailleurs »
    try:
        verifie([b.requete("GET", "/envs")[0], b.requete("POST", "/lancer", {})[0]], [403, 403],
                "distant_sans_jeton_refuse : GET et POST sans jeton")
        verifie(b.requete("GET", "/envs?jeton=" + b.acces.jeton)[0], 303, "distant_sans_jeton_refuse : jeton valide = 303")
    finally:
        acces_web.est_local = vrai


def test_corps_borne(b):
    statut, _ = b.requete("POST", "/port", brut=b" " * (64 * 1024 + 1))
    verifie(statut in (413, 0), True, "corps_borne : > 64 Ko refuse")
    verifie(b.requete("POST", "/port", brut=b"pas du json")[0], 400, "corps_borne : JSON invalide = 400")
    verifie(b.requete("POST", "/port", brut=b"[1]")[0], 400, "corps_borne : corps non objet = 400")
    verifie(b.json("GET", "/execution")[0], 200, "corps_borne : le serveur repond encore")


def test_port_ecrit_puis_relu(b):
    verifie(b.json("POST", "/port", {"env": A, "port": "COM13"})[0], 200, "port_ecrit_puis_relu : POST /port")
    _, donnees = b.json("GET", "/envs")
    verifie(next(e["port"] for e in donnees["envs"] if e["nom"] == A), "COM13", "port_ecrit_puis_relu : relu par /envs")
    verifie(b.json("POST", "/port", {"env": A, "port": "pas un port"})[0], 400, "port_ecrit_puis_relu : port invalide = 400")
    verifie(b.json("POST", "/port", {"env": "inconnu", "port": "COM1"})[0], 400, "port_ecrit_puis_relu : env inconnu = 400")
    b.json("POST", "/port", {"env": A, "port": "COM12"})


def test_lancement(b):
    lancement = {"lignes": [LIGNE_A], "actions": ["compiler"]}
    verifie(b.json("POST", "/lancer", {"lignes": [], "actions": ["compiler"]})[0], 409, "lancer : refus du serie = 409")
    statut, _ = b.json("POST", "/lancer", {"lignes": "x", "actions": []})
    verifie(statut, 400, "lancer : corps mal forme = 400")
    verifie(b.json("GET", "/envs")[1]["derniers"], {}, "lancer : un refus ne memorise rien")
    verifie(b.json("POST", "/lancer", lancement), (200, {"ok": True}), "lancer : lancement accepte")
    verifie(b.json("GET", "/execution"), (200, {"en_cours": True}), "execution_reflete_etat : en cours")
    statut, texte = b.requete("POST", "/lancer", brut=json.dumps(lancement).encode("utf-8"), entetes={"X-Build": "1"})
    verifie((statut, "déjà en cours" in texte), (409, True), "lancer_409_si_en_cours : second lancement refuse")
    verifie(b.json("POST", "/port", {"env": A, "port": "COM14"})[0], 409, "port_refuse_pendant_lancement : 409")
    _, donnees = b.json("GET", "/envs")
    verifie(next(e["port"] for e in donnees["envs"] if e["nom"] == A), "COM12", "port_refuse_pendant_lancement : rien ecrit")
    b.attend_fin()
    verifie(b.json("GET", "/execution"), (200, {"en_cours": False}), "execution_reflete_etat : termine")
    verifie(b.json("GET", "/envs")[1]["derniers"], {"lignes": [LIGNE_A], "actions": ["compiler"]},
            "lancer : derniers choix memorises")
    verifie(json.loads((b.dossier / "derniers.json").read_text(encoding="utf-8"))["actions"], ["compiler"],
            "lancer : derniers.json ecrit dans le dossier de la serie")


def test_flux_et_journal(b):
    statut, recus = lit_flux(b, "/flux?depuis=0", nombre=3)
    ids = [i for i, _ in recus]
    verifie((statut, ids), (200, [1, 2, 3]), "flux_rejoue_depuis : depuis=0 rejoue du debut")
    verifie(recus[0][1]["type"], "debut", "flux_rejoue_depuis : premier evenement = debut")
    _, recus = lit_flux(b, "/flux?depuis=2", nombre=2)
    verifie([i for i, _ in recus], [3, 4], "flux_rejoue_depuis : ?depuis=2 reprend a 3")
    _, recus = lit_flux(b, "/flux", entetes={"Last-Event-ID": "4"}, nombre=1)
    verifie([i for i, _ in recus], [5], "flux_rejoue_depuis : Last-Event-ID 4 reprend a 5")
    statut, texte = b.requete("GET", f"/journal?env={A}")
    verifie((statut, "--- pio run -e " + A in texte, "code de sortie 0" in texte), (200, True, True),
            "journal : texte du dernier journal de l'env")


def test_arret(b):
    lent = {"lignes": ["Processing {env}", "@pause 30"]}
    banc_scen = Path(os.environ[faux.VAR_SCENARIO])
    banc_scen.write_text(json.dumps({"*": {"build": lent}}), encoding="utf-8")
    b.json("POST", "/lancer", {"lignes": [LIGNE_A], "actions": ["compiler"]})
    time.sleep(1.0)
    verifie(b.json("POST", "/arreter", {"immediat": True}), (200, {"ok": True}), "arreter : POST /arreter")
    b.attend_fin(15)
    ev = b.serie.depuis(0, 0)
    verifie([e["resultat"] for e in ev if e["type"] == "fin"][-1:], ["arrete"], "arreter : lancement arrete")


def test_fermeture():
    """ferme(serie) tue l'arbre du fils pio d'un lancement en cours (pas de pio orphelin)."""
    with tempfile.TemporaryDirectory() as t:
        b = Banc(t, {"*": {"build": {"lignes": ["Processing {env}", "@pause 30"]}}})
        try:
            b.json("POST", "/lancer", {"lignes": [LIGNE_A], "actions": ["compiler"]})
            time.sleep(1.0)
            debut = time.monotonic()
            build_web.arrete_serie(b.serie)
            verifie((b.serie.en_cours(), time.monotonic() - debut < 15), (False, True),
                    "fermeture : lancement en cours tue a l'arret du serveur")
        finally:
            b.ferme()


def principal():
    with tempfile.TemporaryDirectory() as t:
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "outils")
        b = Banc(Path(t))
        try:
            for test in (test_routes_locales, test_post_sans_entete_refuse, test_distant_sans_jeton_refuse,
                         test_corps_borne, test_port_ecrit_puis_relu, test_lancement, test_flux_et_journal,
                         test_arret):
                test(b)
        finally:
            b.ferme()
    test_fermeture()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
