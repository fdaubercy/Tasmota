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
custom_files_upload     = data/essai/{A}

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


def lit_flux(banc, chemin="/flux", entetes=None, nombre=1, delai=5):
    """Les `nombre` premiers evenements (id, objet) d'un flux SSE ; ceux recus en `delai` s si le flux se tait."""
    c = http.client.HTTPConnection("127.0.0.1", banc.port, timeout=delai)
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
    except TimeoutError:                                      # flux muet : le test compare ce qui est arrive
        pass
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
    verifie((env_a.get("port"), env_a.get("famille"), env_a.get("fs_avec_firmware")), ("COM12", "cartes", True),
            "routes_locales : champs de Env (fs_avec_firmware compris)")
    verifie(donnees["derniers"], {}, "routes_locales : derniers choix vides au depart")
    verifie(b.json("GET", "/execution"), (200, {"en_cours": False}), "routes_locales : GET /execution")
    verifie(b.requete("GET", "/nimporte")[0], 404, "routes_locales : route inconnue = 404")
    verifie(b.requete("POST", "/nimporte", {})[0], 404, "routes_locales : POST inconnu = 404")
    verifie(b.requete("GET", "/journal?env=../x")[0], 400, "routes_locales : journal, nom d'env invalide = 400")
    verifie(b.requete("GET", "/journal?env=" + A)[0], 200, "routes_locales : journal sans fichier = 200 vide")


# Ce que la page doit porter (spec objectifs 4 et 8, choix 4, 9, 13 et 15 ; brief A6)
ATTENDUS_PAGE = {
    "les 4 actions": ['value="compiler"', 'value="upload"', 'value="buildfs"', 'value="uploadfs"'],
    "les 3 familles": ["Mes cartes", "Mes bases", "Tasmota (amont)"],
    "les 4 sous-groupes amont": ["Safeboot", "ESP32", "Langues", "ESP8266"],
    "l'en-tete X-Build des POST": ['"X-Build": "1"'],
    "les routes": ['"/envs"', '"/execution"', '"/flux?depuis=0"', '"/journal?env="', '"/lancer"', '"/port"',
                   '"/arreter"'],
    "le bouton de lancement": ["l'un après l'autre"],
    "les deux arrets": ["Arrêter après cet env", "Arrêt immédiat", "data/&lt;lieu&gt;/&lt;carte&gt;"],
    "les mentions": ["repartira de zéro", "le file system (persist compris) sera aussi flashé",
                     "valable pour ce lancement seulement"],
}


def manques_page(texte):
    """Libelles des attendus absents de la page (liste vide = complete)."""
    manques = [f"{quoi} : {motif}" for quoi, motifs in ATTENDUS_PAGE.items() for motif in motifs if motif not in texte]
    for externe in ("http://", "https://", "//cdn", "@import"):
        if externe in texte:
            manques.append(f"aucune ressource externe : {externe}")
    return manques


def test_page_contient(b):
    statut, texte = b.requete("GET", "/")
    verifie((statut, manques_page(texte)), (200, []), "page_contient : actions, familles, X-Build, routes, mentions")
    verifie(texte == build_web.page(), True, "page_contient : GET / sert build_page.PAGE")
    # temoin : la page provisoire ne doit PAS passer le controle (sinon il ne mesure rien)
    verifie(len(manques_page(build_web.PAGE_PROVISOIRE)) > 10, True, "page_contient : temoin, page provisoire refusee")


def test_envs_fs_avec_firmware(b):
    """I1 : l'annonce « FS aussi flashe » depend de l'env (custom_files_upload), pas de littlefs.bin."""
    _, donnees = b.json("GET", "/envs")
    verifie({e["nom"]: e["fs_avec_firmware"] for e in donnees["envs"]}, {A: True, B: False, "tasmota32-essai-base": False},
            "envs_fs_avec_firmware : vrai pour l'env qui embarque des fichiers, sans aucun littlefs.bin (purge)")
    racine_build = b.racine / ".pio" / "build" / B
    racine_build.mkdir(parents=True)
    (racine_build / "littlefs.bin").write_bytes(b"x")              # temoin : un littlefs.bin ne change rien
    _, donnees = b.json("GET", "/envs")
    verifie((next(e["fs_avec_firmware"] for e in donnees["envs"] if e["nom"] == B),
             any("littlefs" in e for e in donnees["envs"])), (False, False),
            "envs_fs_avec_firmware : temoin, littlefs.bin present sans fichiers -> faux ; plus de champ littlefs")
    (racine_build / "littlefs.bin").unlink()


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


def test_port_refuse_pendant_build_externe(b):
    """M2 (spec 13 bis) : ecriture du port refusee pendant un build lance ailleurs (VS Code, cible Custom)."""
    texte_avant = (b.racine / "platformio_tasmota_cenv.ini").read_bytes()
    try:
        b.serie.builds_en_cours = lambda: ["pio run -e tasmota32-x (VS Code)"]
        statut, texte = b.requete("POST", "/port", {"env": A, "port": "COM14"})
        verifie((statut, "build" in texte and "tasmota32-x" in texte), (409, True),
                "port_refuse_pendant_build_externe : build en cours -> 409, motif cite le build")
        b.serie.builds_en_cours = lambda: None
        verifie(b.json("POST", "/port", {"env": A, "port": "COM14"})[0], 409,
                "port_refuse_pendant_build_externe : detection impossible -> 409")
        verifie((b.racine / "platformio_tasmota_cenv.ini").read_bytes(), texte_avant,
                "port_refuse_pendant_build_externe : cenv non modifie")
    finally:
        b.serie.builds_en_cours = lambda: []
    verifie(b.json("POST", "/port", {"env": A, "port": "COM12"})[0], 200,
            "port_refuse_pendant_build_externe : temoin, aucun build -> 200")


def test_journal_env_exact():
    """M3 : le journal d'un env ne melange pas celui d'un env dont le nom le prolonge (x-a / x-a-b)."""
    with tempfile.TemporaryDirectory() as t:
        jour = Path(t) / "journaux"
        jour.mkdir()
        for nom, texte in ((f"20261024-100000-{A}-compiler.log", "A1\n"), (f"20261024-100001-{A}-upload-2.log", "A2\n"),
                           (f"20261024-100002-{A}-b-compiler.log", "AB\n"), (f"20261024-100003-x{A}-buildfs.log", "XA\n"),
                           (f"20261024-100004-{A}-compiler.log.tmp", "TMP\n")):
            (jour / nom).write_text(texte, encoding="utf-8")
        verifie(build_web.journal_env(t, A, 0), "A1\nA2\n", "journal_env_exact : seuls les journaux de CET env")
        verifie(build_web.journal_env(t, A, float("inf")), "A2\n",
                "journal_env_exact : repli sur le dernier journal de CET env (pas celui de x-a-b)")
        verifie(build_web.journal_env(t, A + "-b", 0), "AB\n", "journal_env_exact : temoin, l'env x-a-b a le sien")


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
    # onglet reste ouvert sur un outil redemarre : son Last-Event-ID depasse la nouvelle numerotation
    trop = b.serie.numero + 1000
    _, recus = lit_flux(b, "/flux", entetes={"Last-Event-ID": str(trop)}, nombre=1)
    verifie([i for i, _ in recus], [1], "flux_rejoue_depuis : Last-Event-ID trop grand -> rejeu depuis le debut")
    _, recus = lit_flux(b, f"/flux?depuis={trop}", nombre=1)
    verifie([i for i, _ in recus], [1], "flux_rejoue_depuis : ?depuis trop grand -> rejeu depuis le debut")
    dernier = b.serie.numero
    b.serie._ajoute("attente", A, builds=[])                  # temoin : un numero egal au dernier n'est PAS remis a 0
    _, recus = lit_flux(b, "/flux", entetes={"Last-Event-ID": str(dernier)}, nombre=1)
    verifie([i for i, _ in recus], [dernier + 1], "flux_rejoue_depuis : Last-Event-ID = dernier numero -> suite seule")
    statut, texte = b.requete("GET", f"/journal?env={A}")
    verifie((statut, "--- pio run -e " + A in texte, "code de sortie 0" in texte), (200, True, True),
            "journal : texte du dernier journal de l'env")


def test_journal_dernier_lancement(b):
    """Journaux de plusieurs lancements : redemarrage -> le dernier seul ; refus -> lancement reel conserve."""
    jour = b.dossier / "journaux"
    ancien = jour / f"20200101-000000-{A}-compiler.log"
    ancien.write_text("ANCIEN\n", encoding="utf-8")
    os.utime(ancien, (1000000000, 1000000000))
    _, avant = b.requete("GET", f"/journal?env={A}")
    verifie(("ANCIEN" in avant, "code de sortie 0" in avant), (False, True), "journal : un ancien journal n'est pas servi")
    # (a) page redemarree : meme dossier, nouveau serveur, aucun lancement -> seul le dernier journal
    b2 = Banc.__new__(Banc)
    b2.__dict__.update(b.__dict__)
    b2.serveur = ThreadingHTTPServer(("127.0.0.1", 0), build_web.fabrique_gestionnaire(
        b.serie, b.acces, b.racine, b.dossier))
    b2.serveur.daemon_threads = True
    b2.port = b2.serveur.server_address[1]
    threading.Thread(target=b2.serveur.serve_forever, daemon=True).start()
    _, apres = b2.requete("GET", f"/journal?env={A}")
    b2.serveur.shutdown()
    b2.serveur.server_close()
    verifie(("ANCIEN" in apres, "code de sortie 0" in apres), (False, True),
            "journal : apres redemarrage, seul le dernier journal")
    # (b) lancement refuse pendant un lancement : les journaux du lancement reel restent servis
    Path(os.environ[faux.VAR_SCENARIO]).write_text(json.dumps({"*": {"build": {"lignes": ["@pause 3"]}}}),
                                                   encoding="utf-8")
    b.json("POST", "/lancer", {"lignes": [LIGNE_A], "actions": ["compiler"]})
    time.sleep(0.8)
    verifie(b.json("POST", "/lancer", {"lignes": [LIGNE_A], "actions": ["compiler"]})[0], 409,
            "journal : second lancement refuse pendant le lancement")
    b.attend_fin()
    _, apres = b.requete("GET", f"/journal?env={A}")
    verifie(("ANCIEN" in apres, "code de sortie 0" in apres), (False, True),
            "journal : un refus n'ecrase pas le debut du lancement reel")


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


class FausseSerie:
    """Serie dont l'envoi en cours dure `envois` sondages ; note chaque appel a arrete()."""

    def __init__(self, envois):
        self.envois, self.actif, self.appels = envois, True, []

    def en_cours(self):
        return self.actif

    def envoi_en_cours(self):
        self.envois -= 1
        return self.envois >= 0

    def arrete(self, immediat=False):
        self.appels.append((immediat, self.envois >= 0))         # (immediat, envoi encore en cours ?)
        if immediat:
            self.actif = False


def test_fermeture_attend_envoi():
    """M7 : a l'arret du serveur, un envoi vers une carte va a son terme ; le reste est tue."""
    s = FausseSerie(envois=3)
    build_web.arrete_serie(s, attente=2)
    verifie(((True, True) in s.appels, s.appels[-1:]), (False, [(True, False)]),
            "fermeture_attend_envoi : pas d'arret immediat tant que l'envoi dure, puis arret immediat")
    s = FausseSerie(envois=0)                                     # temoin : pas d'envoi -> tue tout de suite
    build_web.arrete_serie(s, attente=2)
    verifie(s.appels[-1:], [(True, False)], "fermeture_attend_envoi : temoin, sans envoi -> arret immediat")
    # vrai faux pio : upload par cable en pleine ecriture (etape Televersement) a l'arret du serveur
    ecriture = ["Processing {env}", "Compiling .pio/build/{env}/src/a.cpp.o", "Linking .pio/build/{env}/firmware.elf",
                "Uploading .pio/build/{env}/firmware.bin", "Writing at 0x00010000 (10 %)", "@pause 1.5",
                "Writing at 0x00020000 (100 %)", "[SUCCESS] Took 2 seconds"]
    with tempfile.TemporaryDirectory() as t:
        b = Banc(t, {"*": {"upload": {"lignes": ecriture}}})
        try:
            b.json("POST", "/lancer", {"lignes": [LIGNE_A], "actions": ["upload"]})
            limite = time.monotonic() + 10
            while time.monotonic() < limite and not any(e["type"] == "etape" and e.get("etape") == "Téléversement"
                                                        for e in b.serie.depuis(0, 0)):
                time.sleep(0.05)
            build_web.arrete_serie(b.serie)
            journal = [json.loads(l) for l in (Path(t) / "journal.jsonl").read_text(encoding="utf-8").splitlines()]
            verifie(([j.get("code") for j in journal if j["type"] == "fin"], b.serie.en_cours()), ([0], False),
                    "fermeture_attend_envoi : upload en cours mene a son terme (code 0), puis serie arretee")
        finally:
            b.ferme()


def principal():
    with tempfile.TemporaryDirectory() as t:
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "outils")
        b = Banc(Path(t))
        try:
            for test in (test_routes_locales, test_page_contient, test_envs_fs_avec_firmware, test_post_sans_entete_refuse, test_distant_sans_jeton_refuse,
                         test_corps_borne, test_port_ecrit_puis_relu, test_port_refuse_pendant_build_externe,
                         test_lancement, test_flux_et_journal, test_journal_dernier_lancement, test_arret):
                test(b)
        finally:
            b.ferme()
    test_journal_env_exact()
    test_fermeture()
    test_fermeture_attend_envoi()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
