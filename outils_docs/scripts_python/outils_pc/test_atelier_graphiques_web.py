"""Banc de atelier_graphiques_web (routes HTTP de l'atelier des graphiques, plan A7).

Code de sortie 0 = vert. Lancer avec le Python de PlatformIO (ProjectConfig) :
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_graphiques_web.py
Serveur dans un fil, sur un port libre, devant une COPIE du depot (copie() du banc A6 : .ini, autoexec de la cuve, du
bureau et de la porte ; plus le .h, le persist de la cuve et les 6 fichiers du moteur de data/sd) dans un dossier
temporaire. La carte est simulee par un `get` injecte (aucun reseau) ; la detection des builds aussi.
"""

import http.client
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import urllib.parse
from http.server import ThreadingHTTPServer
from pathlib import Path

import acces_web
import atelier_graphiques_web as agw
import test_atelier_graphiques_ecriture as tage

DEPOT = tage.DEPOT
CUVE, BUREAU, P4 = tage.CUVE, tage.BUREAU, "tasmota32p4-garage-serveur-modbus"
RIDEAU = "tasmota32s3-garage-rideau-garage-modbus"
SD = ("js/pages_graphiques.js", "js/pages_graphiques_formule.js", "js/echarts.min.js.gz",
      "js/echarts-liquidfill.min.js.gz", "html/pages_graphiques.html", "css/pages_graphiques.css")
SNS = {"StatusSNS": {"Time": "x", "sensorsCuve": {"niveauCuve": {"volume": 4174}}, "DS18B20": {"Temperature": 12.5}}}
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def description(style="cadran", ident="tableau-cuve"):
    return {"version": 1, "pages": [{"id": ident, "titre": "Cuve", "graphiques": [
        {"type": style, "titre": "Volume", "series": ["sensorsCuve.niveauCuve.volume"], "min": 0, "max": 6732}]}]}


class Banc:
    def __init__(self, t):
        self.racine = Path(t) / "depot"
        self.racine.mkdir()
        tage.copie(self.racine)
        for rel in ("tasmota/user_config_override.h", tage.fbe.dossier_carte(CUVE) + "/_persist.json",
                    tage.fbe.dossier_carte(RIDEAU) + "/autoexec.be"):
            (self.racine / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(DEPOT / rel, self.racine / rel)
        for rel in SD:
            (self.racine / "data/sd" / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(DEPOT / "data/sd" / rel, self.racine / "data/sd" / rel)
        self.builds, self.morte, self.appels, self.composition, self.build_actif = [], False, [], None, True
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        acces = acces_web.Acces(self.port, True, "Atelier des graphiques")
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port),
                                           agw.fabrique_gestionnaire(acces, self.racine, lambda: self.builds, get=self.get, sonde_build=lambda: self.build_actif))
        self.serveur.daemon_threads = True
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def get(self, ip, chemin, delai):
        self.appels.append(chemin)
        if self.morte:
            raise OSError("pas de reponse")
        if "p=liste" in chemin:
            return json.dumps({"nom": "mesures", "series": ["sensorsCuve.niveauCuve.volume"], "mois": []}).encode()
        if "p=jour" in chemin:
            return json.dumps({"nom": "mesures", "series": ["sensorsCuve.niveauCuve.volume"], "pas": 300, "t0": 0,
                               "valeurs": [[4100, 4174]]}).encode()
        if chemin.startswith("/cm?") and ("path.exists" in urllib.parse.unquote(chemin) or "graphiquesFonctions" in urllib.parse.unquote(chemin)):
            return b'{"Br":"true"}'
        if chemin == "/json/graphiques.json":
            raise OSError("HTTP 404")                   # mesure sur la vraie carte, 2026-11-06
        if chemin == "/ufsu?dir=0&download=/json/graphiques.json":
            return json.dumps({"affichage": {}, **({} if self.composition is None else {"graphiques": self.composition})}).encode()
        if chemin.startswith("/cm"):
            return json.dumps(SNS).encode()
        return b'{"historique": true}'

    def requete(self, methode, chemin, corps=None, entetes=None):
        h = dict(entetes if entetes is not None else ({"X-Atelier-Graphiques": "1"} if methode == "POST" else {}))
        donnees = json.dumps(corps).encode("utf-8") if corps is not None else None
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            c.request(methode, chemin, body=donnees, headers=h)
            r = c.getresponse()
            brut = r.read()
            self.entetes = dict(r.getheaders())
            try:
                return r.status, json.loads(brut.decode("utf-8"))
            except ValueError:
                return r.status, brut.decode("utf-8", "replace")
        finally:
            c.close()

    def ferme(self):
        self.serveur.shutdown()
        self.serveur.server_close()


def test_page_et_moteur(b):
    statut, page = b.requete("GET", "/")
    verifie((statut, "Atelier des graphiques" in page), (200, True), "GET / : la page")
    verifie("/moteur/pages_graphiques.js" in page and "/moteur/echarts.min.js" in page, True,
            "page : charge le vrai moteur et ECharts par /moteur/")
    verifie(('id="r-series"' in page, "data-serie-champ" in page), (True, True),
            "page : reglages par serie (libelle, unite, couleur)")
    statut, js = b.requete("GET", "/moteur/pages_graphiques.js")
    verifie((statut, "var PagesGraphiques" in js, b.entetes.get("Content-Type", "").startswith("application/javascript")),
            (200, True, True), "GET /moteur/pages_graphiques.js : le moteur du depot")
    statut, ec = b.requete("GET", "/moteur/echarts.min.js")
    verifie((statut, "echarts" in ec[:2000].lower()), (200, True), "GET /moteur/echarts.min.js : ECharts decompresse")
    verifie(b.requete("GET", "/moteur/echarts-liquidfill.min.js")[0], 200, "GET /moteur/ liquidfill decompresse")
    for nom in ("pages_graphiques.html", "pages_graphiques.css", "pages_graphiques_formule.js"):
        verifie(b.requete("GET", "/moteur/" + nom)[0], 200, f"GET /moteur/{nom}")
    for chemin in ("/moteur/../platformio_tasmota_cenv.ini", "/moteur/%2e%2e/platformio_tasmota_cenv.ini",
                   "/moteur/..%2f..%2fplatformio.ini", "/moteur/echarts.min.js.gz", "/moteur/autre.js", "/moteur/"):
        verifie(b.requete("GET", chemin)[0], 404, f"GET {chemin} : refuse (404)")


def test_envs(b):
    statut, r = b.requete("GET", "/envs")
    noms = {e["nom"]: e for e in r["envs"]}
    verifie((statut, CUVE in noms, P4 in noms, RIDEAU in noms), (200, True, True, True), "GET /envs : cartes S3 et P4")
    verifie((BUREAU in noms, "tasmota32s3-base-N16R8" in noms), (False, False), "GET /envs : ni ESP32 classique ni base")
    verifie((noms[CUVE]["exclut_echarts"], noms[CUVE]["exclut_liquidfill"]), (False, False), "cuve : ECharts et liquidfill")
    verifie(noms[RIDEAU]["exclut_liquidfill"], True, "rideau : liquidfill exclu")
    verifie(noms[CUVE]["ip"], "192.168.0.43:8081", "cuve : adresse par le maitre")


def test_series_valeurs(b):
    statut, s = b.requete("GET", f"/series?env={CUVE}")
    verifie((statut, s["source"], s["series"][0]["chemin"]), (200, "carte", "sensorsCuve.niveauCuve.volume"),
            "GET /series : carte en ligne")
    verifie(b.requete("GET", f"/series?env={BUREAU}")[0], 404, "GET /series : ESP32 classique -> 404")
    verifie(b.requete("GET", "/series?env=tasmota32s3-nulle-part")[0], 404, "GET /series : env inconnu -> 404")
    statut, v = b.requete("GET", f"/valeurs?env={CUVE}&c=sensorsCuve.niveauCuve.volume,absente&f=valeurs")
    verifie((statut, v["valeurs"], b.entetes.get("X-Source")),
            (200, {"sensorsCuve.niveauCuve.volume": 4174, "absente": None}, "carte"), "GET /valeurs direct : forme de la carte")
    statut, v = b.requete("GET", f"/valeurs?env={CUVE}&c=sensorsCuve.niveauCuve.volume&n=mesures&p=jour")
    verifie((statut, v["valeurs"]), (200, [[4100, 4174]]), "GET /valeurs jour : JSON de /histo")
    verifie(b.requete("GET", f"/valeurs?env={CUVE}&c=a&c=b,c&p=direct")[1]["valeurs"], {"b": None, "c": None},
            "GET /valeurs : le dernier c l'emporte (paquet du lecteur de la carte)")
    for q, motif in (("p=semaine&c=a", "periode"), ("p=mois&m=2026-13&c=a", "mois"), ("c=a.__proto__", "chemin"),
                     ("c=a&n=x/y", "nom"), ("c=" + ",".join(f"s{i}" for i in range(97)), "trop")):
        verifie(b.requete("GET", f"/valeurs?env={CUVE}&{q}")[0], 400, f"GET /valeurs : {motif} refuse (400)")
    b.morte = True
    statut, s = b.requete("GET", f"/series?env={CUVE}")
    verifie((statut, s["source"]), (200, "depot"), "GET /series : carte muette -> depot")
    avant = len(b.appels)
    statut, v = b.requete("GET", f"/valeurs?env={CUVE}&c=sensorsCuve.niveauCuve.volume&p=direct")
    verifie((statut, b.entetes.get("X-Source"), len(b.appels) - avant), (200, "depot", 0),
            "GET /valeurs : carte muette aux series -> simulees sans attendre la carte")
    b.morte = False
    b.requete("GET", f"/series?env={CUVE}")
    b.requete("GET", f"/valeurs?env={CUVE}&c=a&p=direct")
    verifie(b.entetes.get("X-Source"), "carte", "GET /valeurs : carte revenue apres une relecture des series")


def test_conseil_valide(b):
    statut, r = b.requete("POST", "/conseil", {"intention": "seuil", "destination": "page", "historique": True,
                                               "series": [{"chemin": "v", "unite": "L", "min": 0, "max": 10}]})
    verifie((statut, r["proposes"][0]["style"]), (200, "cadran"), "POST /conseil : cadran en tete pour un seuil")
    statut, r = b.requete("POST", "/conseil", {"intention": "rien", "destination": "page", "historique": True, "series": []})
    verifie((statut, "intention" in r), (400, True), "POST /conseil : intention inconnue -> 400")
    verifie(b.requete("POST", "/valide", {"description": description()}), (200, {"motifs": []}), "POST /valide : valide")
    statut, r = b.requete("POST", "/valide", {"description": description(ident="cs")})
    verifie((statut, any("reserve" in m for m in r["motifs"])), (200, True), "POST /valide : id de route reserve")
    d = description(style="courbe")
    d["pages"][0]["graphiques"][0]["series"] = [{"chemin": "sensorsCuve.niveauCuve.volume", "libelle": "Cuve", "unite": "L",
                                                 "couleur": "#c0392b"}, "DS18B20.Temperature"]
    verifie(b.requete("POST", "/valide", {"description": d}), (200, {"motifs": []}), "POST /valide : series objet et chaine melees")
    d["pages"][0]["graphiques"][0]["series"][0]["couleur"] = "rouge"
    statut, r = b.requete("POST", "/valide", {"description": d})
    verifie((statut, any("couleur de serie" in m for m in r["motifs"])), (200, True), "POST /valide : couleur de serie mal formee")


def test_acces(b):
    corps = {"description": description()}
    verifie(b.requete("POST", "/valide", corps, entetes={})[0], 403, "POST sans en-tete X-Atelier-Graphiques -> 403")
    verifie(b.requete("POST", "/valide", corps, entetes={"X-Atelier-Graphiques": "1", "Origin": "http://evil.example"})[0],
            403, "POST d'une autre origine -> 403")
    verifie(b.requete("POST", "/inconnu", {})[0], 404, "POST route inconnue -> 404")
    verifie(b.requete("GET", "/inconnu")[0], 404, "GET route inconnue -> 404")
    for longueur in ("-1", "10000000"):
        verifie(brut(b, f"POST /valide HTTP/1.1\r\nHost: x\r\nX-Atelier-Graphiques: 1\r\nContent-Length: {longueur}\r\n\r\n{{}}"),
                400, f"POST Content-Length {longueur} -> 400 sans lire le corps")
    profond = "[" * 30000 + "]" * 30000          # 60 Ko : sous le plafond du corps
    verifie(brut(b, "POST /valide HTTP/1.1\r\nHost: x\r\nX-Atelier-Graphiques: 1\r\nContent-Length: "
                    f"{len(profond)}\r\n\r\n{profond}"), 400, "POST JSON trop imbrique (RecursionError) -> 400, pas 409")


def brut(b, requete):
    """Statut HTTP d'une requete ecrite a la main (en-tetes que http.client refuse de forger)."""
    with socket.create_connection(("127.0.0.1", b.port), timeout=10) as s:
        s.sendall(requete.encode("ascii"))
        s.shutdown(socket.SHUT_WR)
        reponse = b""
        while b"\r\n" not in reponse:
            morceau = s.recv(4096)
            if not morceau:
                break
            reponse += morceau
    return int(reponse.split(b" ")[1]) if reponse else None


def test_description_diff_ecrire(b):
    verifie(b.requete("GET", f"/description?env={CUVE}"), (200, {"description": None, "solidifie": False, "erreur": ""}),
            "GET /description : aucune page encore")
    corps = {"env": CUVE, "description": description(), "solidifier": False}
    statut, d = b.requete("POST", "/diff", corps)
    chemins = [f["chemin"] for f in d["fichiers"]]
    rel = tage.fbe.dossier_carte(CUVE) + "/pages_graphiques.json"
    verifie((statut, rel in chemins, "platformio_tasmota_cenv.ini" in chemins), (200, True, True),
            "POST /diff : description, cenv (et autoexec) prevus")
    f = next(x for x in d["fichiers"] if x["chemin"] == rel)
    verifie((f["diff"].startswith("--- a/"), f["ajouts"] > 0, f["retraits"]), (True, True, 0), "POST /diff : diff unifie et compte")
    verifie((b.racine / rel).exists(), False, "POST /diff : rien d'ecrit")
    b.builds = ["pio run -e x"]
    statut, r = b.requete("POST", "/ecrire", dict(corps, empreinte=d["empreinte"]))
    verifie((statut, "build" in r, (b.racine / rel).exists()), (409, True, False), "POST /ecrire pendant un build -> 409, rien d'ecrit")
    b.builds = []
    statut, r = b.requete("POST", "/ecrire", dict(corps, empreinte="perimee"))
    verifie((statut, (b.racine / rel).exists()), (409, False), "POST /ecrire empreinte perimee -> 409, rien d'ecrit")
    statut, r = b.requete("POST", "/ecrire", dict(corps, empreinte=d["empreinte"]))
    verifie((statut, rel in r["ecrits"], (b.racine / rel).exists()), (200, True, True), "POST /ecrire : ecrit")
    t = r["televerser"]
    verifie(("pages_graphiques.json" in t["fichiers"], t["url"].startswith("http://127.0.0.1:7700/?env=")),
            (True, True), "POST /ecrire : `televerser` (fichiers, URL de la page Build)")
    statut, r = b.requete("GET", f"/description?env={CUVE}")
    verifie((statut, r["description"]), (200, description()), "GET /description : relue du depot")
    statut, r = b.requete("POST", "/diff", corps)
    verifie((statut, r["fichiers"]), (200, []), "POST /diff apres ecriture : rien a ecrire")
    statut, r = b.requete("POST", "/diff", dict(corps, description=None))
    verifie((statut, sorted(x["chemin"] for x in r["fichiers"]) == sorted(chemins)), (200, True),
            "POST /diff description null : derniere page retiree")
    statut, r = b.requete("POST", "/diff", {"env": RIDEAU, "description": description("liquide"), "solidifier": False})
    verifie((statut, "liquide" in r), (400, True), "POST /diff : liquide sur un env sans liquidfill -> 400 et motif")
    statut, r = b.requete("POST", "/diff", dict(corps, description=description(ident="cs")))
    verifie((statut, "description invalide" in r), (400, True), "POST /diff : description invalide -> 400")
    for mauvais in ({"env": CUVE, "description": [], "solidifier": False}, {"env": CUVE, "description": None, "solidifier": 1}):
        verifie(b.requete("POST", "/diff", mauvais)[0], 400, f"POST /diff : corps mal type refuse ({mauvais})")
    verifie(b.requete("POST", "/diff", dict(corps, env=BUREAU))[0], 404, "POST /diff : ESP32 classique -> 404")
    (b.racine / rel).write_text("{tronque", encoding="utf-8")
    statut, r = b.requete("GET", f"/description?env={CUVE}")
    verifie((statut, r["description"], bool(r["erreur"])), (200, None, True), "GET /description : JSON illisible signale")
    (b.racine / rel).write_text(json.dumps(description(ident="cs")), encoding="utf-8")
    statut, r = b.requete("GET", f"/description?env={CUVE}")
    verifie((statut, r["description"], "reserve" in r["erreur"]), (200, None, True),
            "GET /description : description invalide -> erreur avec le motif, proposition de depart")


def atelier_g(titre="Volume"):
    return {"moteur": "pages", "type": "courbe", "titre": titre, "periode": "jour",
            "series": [{"chemin": "sensorsCuve.niveauCuve.volume", "libelle": "Vol"}]}


def test_destination_graphiques(b):
    rel = tage.fbe.dossier_carte(CUVE) + "/graphiques.json"
    fichier = b.racine / rel
    base = json.dumps({"affichage": {"a.b": {"libelle": "A"}}, "groupes": {"G": ["a"]}}, indent=chr(9)) + chr(10)
    fichier.write_text(base, encoding="utf-8")
    corps = {"env": CUVE, "destination": "graphiques", "operation": "ajoute", "graphique": atelier_g()}
    statut, e = b.requete("GET", f"/composition?env={CUVE}")
    verifie((statut, e["etat"], e["historique"]), (200, "identique", True), "GET /composition : carte sans composition = depot")
    b.composition = [atelier_g("Sur la carte")]
    statut, e = b.requete("GET", f"/composition?env={CUVE}")
    verifie((statut, e["etat"], bool(e["diff"]), e["carte_valide"]), (200, "differente", True, True), "GET /composition : differente + diff")
    b.morte = True
    statut, e = b.requete("GET", f"/composition?env={CUVE}")
    verifie((statut, e["etat"], bool(e["motif"])), (200, "non_verifiee", True), "GET /composition : carte hors ligne -> non verifiee")
    b.morte = False
    fichier.write_text("{tronque", encoding="utf-8")
    statut, r = b.requete("GET", f"/composition?env={CUVE}")
    verifie((statut, "illisible" in r), (400, True), "GET /composition : graphiques.json du depot illisible -> 400 avec motif")
    fichier.write_text(base, encoding="utf-8")
    verifie(b.requete("GET", "/composition?env=inconnu")[0], 404, "GET /composition : env inconnu -> 404")
    statut, r = b.requete("POST", "/diff", corps)
    verifie((statut, "choisir base" in r), (400, True), "POST /diff graphiques : carte differente sans choix -> 400")
    corps["base"] = "carte"
    statut, d = b.requete("POST", "/diff", corps)
    f = d["fichiers"][0]
    verifie((statut, f["chemin"], f["ajouts"] > 0, fichier.read_text(encoding="utf-8")), (200, rel, True, base), "POST /diff graphiques : diff, rien d'ecrit")
    b.builds = ["pio run"]
    statut, r = b.requete("POST", "/ecrire", dict(corps, empreinte=d["empreinte"]))
    verifie((statut, fichier.read_text(encoding="utf-8")), (409, base), "POST /ecrire graphiques pendant un build -> 409")
    b.builds = []
    statut, r = b.requete("POST", "/ecrire", dict(corps, empreinte="perimee"))
    verifie(statut, 409, "POST /ecrire graphiques empreinte perimee -> 409")
    statut, r = b.requete("POST", "/ecrire", dict(corps, empreinte=d["empreinte"]))
    ecrit = json.loads(fichier.read_text(encoding="utf-8"))
    verifie((statut, r["ecrits"], r["index"], [g["titre"] for g in ecrit["graphiques"]], ecrit["groupes"]), (200, [rel], 1, ["Sur la carte", "Volume"], {"G": ["a"]}),
            "POST /ecrire graphiques : base carte + ajout, autres cles gardees")
    verifie(r["graphique"], ecrit["graphiques"][1], "POST /ecrire graphiques : le graphique ecrit est rendu (temoin `attendu`)")
    b.composition = None
    statut, r = b.requete("POST", "/diff", {"env": CUVE, "destination": "graphiques", "operation": "retire", "index": 0})
    verifie(statut, 400, "POST /diff graphiques : carte sans composition mais depot avec -> choix exige (400)")
    statut, r = b.requete("POST", "/diff", {"env": CUVE, "destination": "graphiques", "operation": "retire", "index": 0, "base": "depot", "attendu": json.loads(fichier.read_text(encoding="utf-8"))["graphiques"][0]})
    verifie(statut, 200, "POST /diff graphiques : retrait, base depot")
    statut, r = b.requete("POST", "/diff", {"env": BUREAU, "destination": "graphiques", "operation": "ajoute", "graphique": atelier_g()})
    verifie(statut, 404, "POST /diff graphiques : ESP32 classique -> 404")
    b.composition = None
    statut, r = b.requete("POST", "/diff", {"env": CUVE, "destination": "inconnue"})
    verifie(statut, 400, "POST /diff : destination inconnue -> 400")
    b.composition = [atelier_g("X")] * 9
    statut, r = b.requete("POST", "/diff", dict(corps, base="carte"))
    verifie((statut, "indisponible" in r), (400, True), "POST /diff graphiques base=carte invalide (9 graphiques) -> 400, motif")


def test_televerser_robuste(b):
    corps = {"env": CUVE, "description": description(), "solidifier": False}
    b.build_actif = True
    verifie(b.requete("GET", "/build_actif"), (200, {"actif": True}), "GET /build_actif : page Build qui repond")
    b.build_actif = False
    verifie(b.requete("GET", "/build_actif"), (200, {"actif": False}), "GET /build_actif : page Build muette")
    b.build_actif = True
    # le calcul de la liste ne doit jamais faire echouer /ecrire (fichiers deja ecrits) : 200 + erreur lisible
    reel, agw.agt.plan = agw.agt.plan, lambda *a, **k: 1 / 0
    try:
        statut, r = b.requete("POST", "/diff", dict(corps, description=description()))
        statut, r = b.requete("POST", "/ecrire", dict(corps, description=description(), empreinte=r["empreinte"]))
    finally:
        agw.agt.plan = reel
    verifie((statut, bool(r.get("ecrits")), "ZeroDivisionError" in r["televerser"]["erreur"]), (200, True, True),
            "POST /ecrire : liste a televerser en erreur -> 200, fichiers ecrits, erreur lisible")


TESTS = [test_page_et_moteur, test_envs, test_series_valeurs, test_conseil_valide, test_acces, test_description_diff_ecrire,
         test_destination_graphiques, test_televerser_robuste]


if __name__ == "__main__":
    for test in TESTS:
        print(f"--- {test.__name__}")
        with tempfile.TemporaryDirectory() as t:
            os.environ["OUTILS_TASMOTA_DOSSIER"] = os.path.join(t, "outils")
            b = None
            try:
                b = Banc(t)
                test(b)
            except Exception as e:                                  # un test qui plante est un echec, pas un arret
                print(f"KO   {test.__name__} : {type(e).__name__} : {e}")
                ECHECS.append(test.__name__)
            finally:
                if b:
                    b.ferme()
    print(f"\n{len(ECHECS)} echec(s)" + (" : " + ", ".join(ECHECS) if ECHECS else " : VERT"))
    sys.exit(1 if ECHECS else 0)
