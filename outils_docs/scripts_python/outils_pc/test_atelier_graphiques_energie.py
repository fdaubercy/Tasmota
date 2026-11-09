"""Banc de atelier_graphiques_energie (destination « Energie » du differentiel, cote serveur, plan energie-atelier A4).

Code de sortie 0 = vert. Lancer avec le Python de PlatformIO depuis la racine du depot :
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_graphiques_energie.py
Copies temporaires du depot (copie() du banc A6 + le .h des adresses) ; la carte est un `get` injecte (aucun reseau,
aucun envoi) ; le serveur de l'atelier tourne dans un fil devant la copie (Banc du banc web).
"""

import json
import os
import shutil
import sys
import datetime
import io
import tempfile
import urllib.error
import urllib.parse
from pathlib import Path

import atelier_energie_description as aed
import atelier_graphiques_energie as ageg
import atelier_graphiques_web as agw
import test_atelier_graphiques_ecriture as tage
import test_atelier_graphiques_web as tagw

verifie, refuse, ECHECS = tage.verifie, tage.refuse, tage.ECHECS
tagw.ECHECS = ECHECS
BUREAU, PORTE, CUVE, SANS_BUILD = tage.BUREAU, tage.PORTE, tage.CUVE, tage.SANS_BUILD
FICHIER = tage.fbe.dossier_carte(BUREAU) + "/energie_page.json"
SD = ("js/energie.js", "html/energie.html", "css/energie.css")
HTML = b"<!DOCTYPE html><html><body>Energie</body></html>"      # ancien firmware : la page entiere, en 200
ENERGY = {"Power": 1200, "Current": 5.2, "Factor": 0.98, "Voltage": 230, "Today": 3.1, "Total": 1234.5, "Period": 0}


def desc(titre="Puissance"):
    d = json.loads(json.dumps(aed.DEFAUT))
    d["elements"][0]["titre"] = titre
    return d


def compact(d):
    return json.dumps(d, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def carte(mode="json", description=None, energy=ENERGY, mort=False):
    """`get` simulant le differentiel : /energie?f=description (json | 404 | 413 | html), Status 10."""
    appels = []

    def get(ip, chemin, delai):
        appels.append(chemin)
        if mort:
            raise OSError("pas de reponse")
        if chemin == "/energie?f=description":
            if mode in ("404", "413"):
                raise urllib.error.HTTPError("http://" + ip + chemin, int(mode), "Not Found", {}, None)    # ce que leve urlopen en production
            if mode in ("vide", "tronque"):
                return b"" if mode == "vide" else compact(desc())[:20]
            return HTML if mode == "html" else compact(description if description is not None else desc())
        if chemin.startswith("/cm?") and urllib.parse.unquote(chemin.split("cmnd=", 1)[1]) == "Status 10":
            return json.dumps({"StatusSNS": {"Time": "x", "ENERGY": energy} if energy is not None else {"Time": "x"}}).encode()
        raise AssertionError("requete inattendue : " + chemin)
    get.appels = appels
    return get


def depot(t):
    racine = Path(t) / "depot"
    racine.mkdir()
    tage.copie(racine)
    for rel in ["tasmota/user_config_override.h"] + ["data/sd/" + s for s in SD]:
        (racine / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tage.DEPOT / rel, racine / rel)
    return racine


def test_cartes(racine):
    noms = agw.cartes(racine)[1]
    verifie((BUREAU in noms, PORTE in noms, CUVE in noms), (True, False, True), "cartes() : le differentiel y est (page_energie dans son FS), pas la porte, la cuve toujours")
    verifie(ageg.page_energie(agw.cartes(racine)[0], CUVE), False, "page_energie : la cuve exclut la page")


def test_etat_carte(racine):
    d = desc("Lue sur la carte")
    verifie(ageg.etat_carte(racine, BUREAU, get=carte(description=d)), {"description": d, "firmware_requis": False, "motif": ""},
            "etat_carte : description de la carte lue")
    verifie(ageg.etat_carte(racine, BUREAU, get=carte("404")), {"description": None, "firmware_requis": False, "motif": ""},
            "etat_carte : 404 = pas de description, rien d'anormal")
    r = ageg.etat_carte(racine, BUREAU, get=carte("html"))
    verifie((r["description"], r["firmware_requis"], "firmware" in r["motif"]), (None, True, True),
            "etat_carte : la page HTML en 200 = ancien firmware (firmware_requis)")
    for mode in ("vide", "tronque"):
        r = ageg.etat_carte(racine, BUREAU, get=carte(mode))
        verifie((r["description"], r["firmware_requis"], "illisible" in r["motif"]), (None, False, True),
                "etat_carte : description " + mode + " sur la carte = illisible, Televerser reste permis")
    r = ageg.etat_carte(racine, BUREAU, get=carte(mort=True))
    verifie((r["description"], r["firmware_requis"], bool(r["motif"])), (None, False, True), "etat_carte : carte muette = non verifie, pas d'accusation du firmware")
    r = ageg.etat_carte(racine, BUREAU, get=carte("413"))
    verifie((r["description"], r["firmware_requis"], "grosse" in r["motif"]), (None, False, True), "etat_carte : 413 = description trop grosse")
    r = ageg.etat_carte(racine, BUREAU, get=carte(description={"version": 2, "elements": []}))
    verifie((r["description"], r["firmware_requis"], "version" in r["motif"]), (None, False, True), "etat_carte : description invalide sur la carte = motif, pas de description")


def test_ecriture(racine):
    f, d = racine / FICHIER, desc()
    p = ageg.prevoit(racine, BUREAU, d)
    verifie(([x["chemin"] for x in p["fichiers"]], p["fichiers"][0]["avant"], p["fichiers"][0]["apres"], f.exists()),
            ([FICHIER], None, compact(d).decode(), False), "prevoit : energie_page.json compact, rien d'ecrit")
    refuse(lambda: ageg.ecrit(racine, BUREAU, d, p["empreinte"], lambda: ["pio run"]), RuntimeError, "ecrit : refuse pendant un build", "build")
    refuse(lambda: ageg.ecrit(racine, BUREAU, d, p["empreinte"], lambda: None), RuntimeError, "ecrit : refuse si les builds sont indetectables", "build")
    refuse(lambda: ageg.ecrit(racine, BUREAU, d, "perimee", SANS_BUILD), RuntimeError, "ecrit : empreinte perimee refusee", "modifie")
    verifie(f.exists(), False, "refus : rien n'est ecrit")
    refuse(lambda: ageg.prevoit(racine, BUREAU, {"version": 1, "elements": []}), ValueError, "prevoit : description invalide refusee", "elements")
    gros = desc()
    gros["elements"] = [dict(gros["elements"][0], titre="\U0001F600" * 40) for _ in range(16)]
    refuse(lambda: ageg.prevoit(racine, BUREAU, gros), ValueError, "prevoit : plus de 4096 octets compacts refuse", "taille")
    refuse(lambda: ageg.prevoit(racine, CUVE, d), LookupError, "prevoit : env sans page Energie (cuve) refuse")
    refuse(lambda: ageg.prevoit(racine, "inconnu", d), LookupError, "prevoit : env inconnu refuse")
    verifie(ageg.ecrit(racine, BUREAU, d, p["empreinte"], SANS_BUILD), [FICHIER], "ecrit : chemin ecrit")
    verifie((f.read_bytes(), len(f.read_bytes()) <= 4096), (compact(d), True), "ecrit : JSON compact UTF-8, taille brute <= 4096")
    p2 = ageg.prevoit(racine, BUREAU, d)
    verifie((p2["fichiers"], ageg.ecrit(racine, BUREAU, d, p2["empreinte"], SANS_BUILD)), ([], []), "meme description : rien a ecrire")
    p3 = ageg.prevoit(racine, BUREAU, desc("Autre"))
    f.write_bytes(compact(desc("Retouche a la main")))
    refuse(lambda: ageg.ecrit(racine, BUREAU, desc("Autre"), p3["empreinte"], SANS_BUILD), RuntimeError, "ecrit : fichier modifie depuis le diff -> refus", "modifie")
    verifie(ageg.description_de(racine, BUREAU)["description"]["elements"][0]["titre"], "Retouche a la main", "description_de : lit le depot")
    f.write_text("{tronque", encoding="utf-8")
    r = ageg.description_de(racine, BUREAU)
    verifie((r["description"], "illisible" in r["erreur"]), (None, True), "description_de : fichier illisible = erreur lisible")
    f.unlink()


def test_plan(racine):
    f = racine / FICHIER
    f.write_bytes(compact(desc()))
    p = ageg.plan(racine, BUREAU, get=carte())
    verifie((p["fichiers"], p["redemarrer"], p["firmware_requis"]),
            (["energie_page.json", "sd/js/energie.js", "sd/html/energie.html", "sd/css/energie.css"], 0, False), "plan : description + 3 fichiers de la page, pas de redemarrage")
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(p["url"]).query)
    verifie((q["env"], q["depuis"], q["fichiers"], q["redemarrer"]), ([BUREAU], ["atelier"], [",".join(p["fichiers"])], ["0"]), "plan : url de la page Build (depuis=atelier)")
    p = ageg.plan(racine, BUREAU, get=carte("html"))
    verifie((p["firmware_requis"], p["url"], bool([n for n in p["notes"] if "firmware" in n])), (True, None, True), "plan : ancien firmware -> pas d'url, note firmware")
    p = ageg.plan(racine, BUREAU, get=carte(mort=True))
    verifie((p["firmware_requis"], p["url"] is not None, bool(p["notes"])), (False, True, True), "plan : carte muette -> url quand meme, note 'non verifie'")
    f.unlink()
    verifie(ageg.plan(racine, BUREAU, get=carte())["fichiers"][0], "sd/js/energie.js", "plan : sans description au depot, seuls les fichiers de la page")


def test_catalogue(racine):
    c = ageg.catalogue(racine, BUREAU, get=carte())
    directs = [s["direct"] for s in c["sources"] if "direct" in s]
    verifie((c["origine"], directs), ("carte", ["Power", "Current", "Factor", "Voltage", "Today", "Total"]), "catalogue : champs direct = ceux du bloc ENERGY de Status 10 (dans l'ordre du schema, Period ignore)")
    verifie(c["styles"], list(aed.TYPES), "catalogue : styles = TYPES")
    for muette in (carte(mort=True), carte(energy=None)):
        m = ageg.catalogue(racine, BUREAU, get=muette)
        verifie(([s["direct"] for s in m["sources"] if "direct" in s], m["origine"]), (list(aed.CHAMPS_DIRECT), "defaut"), "catalogue : carte muette / sans ENERGY = liste de la spec §2")
    flash = [s for s in c["sources"] if "flash" in s]
    verifie(sorted({s["flash"] for s in flash}), sorted(["minutes", "heure", "jour", "mois", "an"]), "catalogue : toutes les echelles flash")
    verifie([s for s in c["sources"] if "total" in s][0], {"total": "jour", "grandeur": "kWh"}, "catalogue : totaux jour/mois/an en kWh et euros")
    verifie(len([s for s in c["sources"] if "total" in s]), 6, "catalogue : 3 totaux x 2 grandeurs")
    verifie(all(not aed.valide({"version": 1, "elements": [{"type": "valeur" if "direct" in s or "total" in s else "barres", "titre": "t", "source": s}]}) for s in c["sources"]), True,
            "catalogue : chaque source est acceptee par le validateur")
    verifie({"flash": "minutes"} in c["sources"], True, "catalogue : minutes sans grandeur")


NOW = int(datetime.datetime(2026, 11, 8, 12).timestamp())    # midi, heure locale
REF_DONNEES = {"aujourdhui": str, "etat": dict, "wCourant": int, "prix": list, "courbe": list}      # banc_energie.py / envoieDonnees
REF_ETAT = {"w": int, "u": int, "l": int, "j": str, "h": list, "he": list, "m": str, "d": list, "de": list, "a": list}
REF_DIRECT = {"p": int, "i": float, "f": float, "hz": int}                                          # banc_energie.py : direct
REF_DIRECT_PLUS = ("Voltage", "ApparentPower", "ReactivePower", "Today", "Yesterday", "Total")      # energieFonctions.CHAMPS_DIRECT


def hors_ligne(ip, chemin, delai):
    raise OSError("pas de reponse")


def table(reponses):
    """`get` de l'apercu : chemin -> octets, ou code HTTP (HTTPError avec son corps)."""
    def get(ip, chemin, delai):
        r = reponses[chemin]
        if isinstance(r, int):
            raise urllib.error.HTTPError("http://" + ip + chemin, r, "x", {}, io.BytesIO(b'{"erreur":"absent"}'))
        return r
    return get


def test_apercu(racine):
    rel = {"/energie?f=donnees": b'{"aujourdhui":"2026-11-08"}', "/energie?f=direct": b'{"p":1}', "/energie?f=mois&m=2026-10": b'{"d":[1],"de":[2]}',
           "/energie?f=mois&m=2020-01": 404}
    g = table(rel)
    verifie(ageg.apercu(racine, BUREAU, "donnees", get=g), (200, b'{"aujourdhui":"2026-11-08"}', "carte"), "apercu : donnees relayees telles quelles")
    verifie(ageg.apercu(racine, BUREAU, "direct", get=g), (200, b'{"p":1}', "carte"), "apercu : direct relaye")
    verifie(ageg.apercu(racine, BUREAU, "mois", "2026-10", get=g), (200, b'{"d":[1],"de":[2]}', "carte"), "apercu : mois relaye")
    verifie(ageg.apercu(racine, BUREAU, "mois", "2020-01", get=g), (404, b'{"erreur":"absent"}', "carte"), "apercu : 404 d'un mois absent relaye (pas de simulation)")
    for f, m in (("tarifs", None), ("../x", None), ("mois", None), ("mois", "2026-13"), ("mois", "2026-1"), ("mois", "2026-10&x=1"), ("mois", "../etc"), ("mois", "٢٠٢٦-10")):
        refuse(lambda: ageg.apercu(racine, BUREAU, f, m, get=g), ValueError, f"apercu : f={f!r} m={m!r} refuse (400)")
    refuse(lambda: ageg.apercu(racine, CUVE, "direct", get=g), LookupError, "apercu : env sans page Energie -> 404")
    verifie(ageg.apercu(racine, BUREAU, "direct", muette=True, get=g)[2], "simulee", "apercu : carte muette (marquee) -> simulee, sans requete")
    vieux = lambda ip, chemin, delai: HTML          # ancien firmware : la page HTML en 200 pour tout ?f=
    verifie(ageg.apercu(racine, BUREAU, "donnees", get=vieux)[2], "simulee", "apercu : ancien firmware (HTML en 200) -> simulee, pas de HTML sous type JSON")
    s, corps, src = ageg.apercu(racine, BUREAU, "direct", get=hors_ligne)
    d = json.loads(corps)
    verifie((s, src, {k: type(d[k]) for k in REF_DIRECT}, all(k in d for k in REF_DIRECT_PLUS)), (200, "simulee", REF_DIRECT, True), "apercu : direct simule = formes du banc Berry")
    s, corps, src = ageg.apercu(racine, BUREAU, "donnees", get=hors_ligne, maintenant=NOW)
    d = json.loads(corps)
    verifie({k: type(d[k]) for k in REF_DONNEES}, REF_DONNEES, "apercu : donnees simulees, cles et types de envoieDonnees")
    e = d["etat"]
    verifie(({k: type(e[k]) for k in REF_ETAT}, len(e["h"]), len(e["he"]), len(e["d"]), len(e["de"]), len(d["courbe"])), (REF_ETAT, 24, 24, 31, 31, 288), "apercu : etat simule, tailles de la carte")
    verifie((all(isinstance(x, int) for x in e["h"] + e["he"] + e["d"] + e["de"]), all(x is None or isinstance(x, int) for x in d["courbe"]),
             all(isinstance(a[0], str) and isinstance(a[1], int) and isinstance(a[2], int) for a in e["a"]), e["a"][-1][0], d["aujourdhui"], d["prix"][0][1]),
            (True, True, True, "2026-10", "2026-11-08", 2000), "apercu : entiers (Wh, dix-milliemes), courbe int|null, archives [mois, Wh, euros], dernier mois clos")
    for m, attendu in (("2026-10", 200), ("2024-11", 200), ("2024-10", 404), ("2026-12", 404), ("2026-11", 200)):
        s, corps, _ = ageg.apercu(racine, BUREAU, "mois", m, get=hors_ligne, maintenant=NOW)
        d = json.loads(corps)
        verifie((s, sorted(d) if s == 200 else d, len(d.get("d", [0] * 31)) if s == 200 else 31), (attendu, ["d", "de"] if attendu == 200 else {"erreur": "absent"}, 31), f"apercu : mois simule {m} -> {attendu}")


class BancEnergie(tagw.Banc):
    def __init__(self, t):
        super().__init__(t)
        for rel in tuple("data/sd/" + s for s in SD):
            (self.racine / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(tage.DEPOT / rel, self.racine / rel)
        self.mode, self.carte_desc = "json", None

    def get(self, ip, chemin, delai):
        if chemin.startswith("/energie") or (chemin.startswith("/cm?") and "Status%2010" in chemin):
            return carte(self.mode, self.carte_desc, mort=self.morte)(ip, chemin, delai)
        return super().get(ip, chemin, delai)


def test_web(b):
    f = b.racine / FICHIER
    statut, r = b.requete("GET", "/envs")
    noms = {e["nom"]: e for e in r["envs"]}
    verifie((statut, BUREAU in noms, PORTE in noms, noms[BUREAU].get("energie"), noms[CUVE].get("energie")), (200, True, False, True, False), "GET /envs : le differentiel, marque energie")
    for s in SD:
        verifie(b.requete("GET", "/moteur/" + Path(s).name)[0], 200, "GET /moteur/" + Path(s).name)
    statut, c = b.requete("GET", f"/series?env={BUREAU}")
    verifie((statut, c.get("styles"), c.get("origine")), (200, list(aed.TYPES), "carte"), "GET /series : catalogue pour le differentiel")
    statut, c = b.requete("GET", f"/series?env={CUVE}")
    verifie((statut, "series" in c), (200, True), "GET /series : la cuve garde ses series")
    corps = {"env": BUREAU, "destination": "energie", "description": desc()}
    statut, d = b.requete("POST", "/diff", corps)
    verifie((statut, d["fichiers"][0]["chemin"], d["fichiers"][0]["ajouts"] > 0, f.exists()), (200, FICHIER, True, False), "POST /diff energie : diff, rien d'ecrit")
    statut, r = b.requete("POST", "/diff", dict(corps, description={"version": 1, "elements": []}))
    verifie((statut, "elements" in r), (400, True), "POST /diff energie : description invalide -> 400")
    statut, r = b.requete("POST", "/diff", dict(corps, env=CUVE))
    verifie(statut, 404, "POST /diff energie : env sans page Energie -> 404")
    b.builds = ["pio run"]
    statut, r = b.requete("POST", "/ecrire", dict(corps, empreinte=d["empreinte"]))
    verifie((statut, f.exists()), (409, False), "POST /ecrire energie pendant un build -> 409")
    b.builds = []
    verifie(b.requete("POST", "/ecrire", dict(corps, empreinte="perimee"))[0], 409, "POST /ecrire energie : empreinte perimee -> 409")
    verifie(b.requete("POST", "/ecrire", corps)[0], 400, "POST /ecrire energie : empreinte absente -> 400")
    statut, r = b.requete("POST", "/ecrire", dict(corps, empreinte=d["empreinte"]))
    t = r["televerser"]
    verifie((statut, r["ecrits"], f.read_bytes(), t["redemarrer"], t["fichiers"][0], t["firmware_requis"]), (200, [FICHIER], compact(desc()), 0, "energie_page.json", False),
            "POST /ecrire energie : ecrit, liste a televerser")
    verifie("depuis=atelier" in t["url"], True, "POST /ecrire energie : url Build")
    b.mode = "html"
    autre = dict(corps, description=desc("Autre titre"))
    empreinte = b.requete("POST", "/diff", autre)[1]["empreinte"]
    statut, r = b.requete("POST", "/ecrire", dict(autre, empreinte=empreinte))
    verifie((statut, r["televerser"]["firmware_requis"], r["televerser"]["url"]), (200, True, None), "POST /ecrire energie : ancien firmware -> televerser bloque")
    statut, r = b.requete("GET", f"/composition?env={BUREAU}")
    verifie((statut, r["etat"], r["firmware_requis"]), (200, "non_verifiee", True), "GET /composition energie : ancien firmware -> non verifiee")
    b.mode, b.carte_desc = "json", desc("Autre titre")
    statut, r = b.requete("GET", f"/composition?env={BUREAU}")
    verifie((statut, r["etat"], r["carte_valide"]), (200, "identique", True), "GET /composition energie : carte = depot -> identique")
    b.carte_desc = desc("Sur la carte")
    statut, r = b.requete("GET", f"/composition?env={BUREAU}")
    verifie((statut, r["etat"], bool(r["diff"]), r["carte"]["elements"][0]["titre"], r["depot"]["elements"][0]["titre"]), (200, "differente", True, "Sur la carte", "Autre titre"),
            "GET /composition energie : carte differente du depot, diff")
    b.mode = "404"
    statut, r = b.requete("GET", f"/composition?env={BUREAU}")
    verifie((statut, r["etat"], r["carte"]), (200, "differente", None), "GET /composition energie : carte sans description, depot avec -> differente")
    statut, r = b.requete("GET", f"/description?env={BUREAU}")
    verifie((statut, r["description"]["elements"][0]["titre"]), (200, "Autre titre"), "GET /description energie : celle du depot")
    b.mode, b.morte = "json", True
    statut, r = b.requete("GET", f"/energie/{BUREAU}?f=direct")
    verifie((statut, b.entetes.get("X-Source"), "p" in r), (200, "simulee", True), "GET /energie/<env> : carte hors ligne -> simulee, X-Source")
    b.morte = False
    statut, r = b.requete("GET", f"/energie/{BUREAU}?f=mois&m=2026-1")
    verifie(statut, 400, "GET /energie/<env> : mois invalide -> 400")
    verifie(b.requete("GET", f"/energie/{BUREAU}?f=tarifs")[0], 400, "GET /energie/<env> : f hors liste -> 400")
    verifie(b.requete("GET", f"/energie/{CUVE}?f=direct")[0], 404, "GET /energie/<cuve> : env non Energie -> 404")
    verifie(b.requete("GET", "/energie/..%2Fplatformio.ini?f=direct")[0], 404, "GET /energie/<chemin libre> -> 404")
    for destination in ("pages", "graphiques"):
        statut, r = b.requete("POST", "/diff", {"env": BUREAU, "destination": destination, "description": tagw.description(), "solidifier": False,
                                                 "operation": "ajoute", "graphique": tagw.atelier_g()})
        verifie(statut, 404, f"POST /diff {destination} sur le differentiel -> 404")
    f.unlink()


if __name__ == "__main__":
    for test in (test_cartes, test_etat_carte, test_ecriture, test_plan, test_catalogue, test_apercu):
        print(f"--- {test.__name__}")
        with tempfile.TemporaryDirectory() as t:
            os.environ["OUTILS_TASMOTA_DOSSIER"] = os.path.join(t, "outils")
            try:
                test(depot(t))
            except Exception as e:
                print(f"KO   {test.__name__} : {type(e).__name__} : {e}")
                ECHECS.append(test.__name__)
    print("--- test_web")
    with tempfile.TemporaryDirectory() as t:
        os.environ["OUTILS_TASMOTA_DOSSIER"] = os.path.join(t, "outils")
        b = None
        try:
            b = BancEnergie(t)
            test_web(b)
        except Exception as e:
            print(f"KO   test_web : {type(e).__name__} : {e}")
            ECHECS.append("test_web")
        finally:
            if b:
                b.ferme()
    print(f"\n{len(ECHECS)} echec(s)" + (" : " + ", ".join(ECHECS) if ECHECS else " : VERT"))
    sys.exit(1 if ECHECS else 0)
