r"""Banc des graphiques de l'historique : Berry (banc_historique.be, banc_graphiques.be) puis rendu dans Chrome.

UTILISATION
-----------
    python outils_docs/scripts_python/berry/banc_graphiques.py [--sans-navigateur] [--garde DOSSIER]

Depuis n'importe quel dossier : la racine du depot, berry.exe et Chrome (ou Edge) sont deduits.
Code de sortie 0 si tout est vert, 1 sinon -> utilisable comme garde avant un televersement.
  --sans-navigateur  : seulement la partie Berry (le rendu n'est alors PAS verifie).
  --garde DOSSIER    : garde les fichiers produits (page, DOM de chaque scenario) dans DOSSIER.

CE QU'IL FAIT
-------------
0. Lance `berry.exe banc_historique.be <dossier>/historique` : choix des series (decouverte filtree du JSON
   SENSOR, exclues, ajouts, compteurs) et releve (redecouverte horaire, fichier du mois mis de cote).
1. Lance `berry.exe banc_graphiques.be <dossier>` depuis la racine : envoi d'ECharts compresse par morceaux, 404,
   acces refuse, URL Grafana (%topic%), page /graphiques (gabarit, window.GRAPHIQUES), filtre des faux
   zeros de la cuve du maitre P4. La page est generee par le VRAI graphiquesFonctions.page(), avec la
   configuration reelle du persist du P4.
2. Compare octet par octet ECharts recu et data/sd/js/echarts.min.js.gz.
3. Sert cette page et des reponses /histo fixes (un petit serveur par scenario, port libre, 127.0.0.1)
   et la rend dans Chrome sans interface (--dump-dom) : 24 h + temps reel, cache d'ECharts, mois avec trou,
   mois -a, series masquees, relecture periodique, cadence du direct (arret, 2 s), historique pas demarre,
   aucun pas clos, ECharts absent. ECharts dessine dans un canvas : la page expose ce qu'elle trace en
   attributs data- de chaque graphique (titre, series, legende visible, dernier instant, bornes des axes,
   dernieres valeurs), que le banc juge avec les listes, le bouton Grafana, le message et les requetes
   recues (Referer exige par Tasmota).

CE QU'IL NE TESTE PAS
---------------------
La vraie carte : ni le serveur web de Tasmota, ni la RAM, ni les vraies mesures. Le format telephone
n'est pas juge ici (Chrome sans interface ne descend pas sous 500 px de fenetre) : capture a la main
dans un cadre de 412 px. Un banc vert ne remplace pas l'essai sur le P4 (A6 du plan graphiques-web).
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

T0 = 1792230900                    # 2026-10-17 09:55 UTC : premier point de la vue 24 h
SEPTEMBRE = 1788220800             # 2026-09-01 00:00 UTC
# Series decouvertes sur le P4 (chemins du JSON SENSOR, A8) : 3 dans « Mesures », 3 dans le groupe « Cuve »
ESCLAVE = "TasmotaSlaveModBus.TasmotaSlaveModBus1.ANALOG.A1"
SERIES_P4 = ["DS18B20.Temperature", ESCLAVE, "sensorsCuve.niveauCuve.hauteurEau",
             "sensorsCuve.niveauCuve.tauxRemplissage", "sensorsCuve.niveauCuve.volume",
             "sensorsCuve.valeursAnalogiques.valeurCapteurHauteur"]


def trouve_racine() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    sys.exit("ERREUR : racine du depot introuvable.")


def trouve_navigateur():
    candidats = [Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
                 Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
                 Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
                 Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")]
    for c in candidats:
        if c.exists():
            return str(c)
    for nom in ("chrome", "google-chrome", "chromium", "msedge"):
        if shutil.which(nom):
            return shutil.which(nom)
    return None


# ---- Reponses /histo fixes ---------------------------------------------------------------------
def jour():
    """6 series du P4 ; l'entree de l'esclave avec un trou de 20 pas, la sonde entre 20 et 22 °C, le reste en rampe."""
    v = []
    for nom in SERIES_P4:
        if nom == ESCLAVE:
            v.append([None if 100 <= i < 120 else round(28 + (i % 50) / 25, 2) for i in range(288)])
        elif nom == "DS18B20.Temperature":
            v.append([round(20 + (i % 50) / 25, 2) for i in range(288)])
        else:
            v.append([round(i / 10, 2) for i in range(288)])
    # pas en cours (pas encore clos) : la page l'ajoute en dernier point
    encours = [29.0 if nom == ESCLAVE else 21.0 if nom == "DS18B20.Temperature" else 28.8 for nom in SERIES_P4]
    return {"nom": "mesures", "series": SERIES_P4, "pas": 300, "t0": T0, "valeurs": v,
            "tEncours": T0 + 288 * 300, "encours": encours}


# Unites devinees : une serie par cas, sans reglage 'affichage' sauf l'humidite (unite imposee, prioritaire)
SERIES_UNITES = ["DS18B20.Temperature", "AM2301.Humidity", "BMP280.Pressure", "BH1750.Illuminance", "ANALOG.A1",
                 "TasmotaSlaveModBus.TasmotaSlaveModBus1.ANALOG.A2", "ENERGY.Voltage", "sensorsCuve.niveauCuve.hauteurEau"]
AFFICHAGE_UNITES = {"AM2301.Humidity": {"unite": "%HR"}}
LEGENDES_UNITES = ["DS18B20 Temperature (°C)", "AM2301 Humidity (%HR)", "BMP280 Pressure (hPa)", "BH1750 Illuminance (lx)",
                   "ANALOG A1", "Capteurs Cuve ModBus ANALOG A2 (mV)", "ENERGY Voltage (V)",
                   "sensorsCuve niveauCuve hauteurEau (cm)"]


def jour_unites():
    return {"nom": "mesures", "series": SERIES_UNITES, "pas": 300, "t0": T0,
            "valeurs": [[round(10 + k + i / 100, 2) for i in range(288)] for k in range(len(SERIES_UNITES))]}


def mois(m):
    noms = ["ancienneSerie"] if m.endswith("-a") else ["DS18B20.Temperature", "sensorsCuve.niveauCuve.tauxRemplissage"]
    lignes = []
    for h in range(24 * 28):
        if 200 <= h < 230:                     # trou de 30 h
            continue
        ligne = [SEPTEMBRE + h * 3600]
        for k in range(len(noms)):
            moy = 28 + (h % 24) / 12 if k == 0 else 0.5 + (h % 100) / 400
            ligne += [round(moy - 0.5, 2), round(moy, 2), round(moy + 0.5, 2)]
        lignes.append(ligne)
    return {"nom": "mesures", "series": SERIES_P4, "seriesFichier": noms, "lignes": lignes}


LISTE = {"nom": "mesures", "series": SERIES_P4, "mois": ["2026-08-a", "2026-09"]}
VUE = {"mois": "m:2026-09", "mois_a": "m:2026-08-a"}
CADENCE = {"direct_arret": "0", "direct_rapide": "2"}       # choix de la liste « Direct » deja memorise
T_ENCOURS = T0 + 288 * 300         # pas en cours de la vue 24 h
TD = T_ENCOURS + 60                # premiere valeur directe, puis +10 s par lecture


def direct(n):
    """Valeurs actuelles (p=direct), n-ieme lecture : l'esclave a 29,5, la sonde absente, le reste a 28,9."""
    return {"nom": "mesures", "series": SERIES_P4, "t": TD + 10 * n,
            "valeurs": [29.5 if nom == ESCLAVE else None if nom == "DS18B20.Temperature" else 28.9 for nom in SERIES_P4]}


def serveur(scenario, page, echarts_gz):
    """Un serveur par scenario (port libre) : origine distincte, donc localStorage distinct."""
    requetes = []
    lectures_directes = [0]

    class Gestion(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def envoie(self, code, mime, corps):
            corps = corps if isinstance(corps, bytes) else corps.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

        def do_GET(self):
            u = urlparse(self.path)
            q = dict(parse_qsl(u.query))
            requetes.append((self.path, self.headers.get("Referer")))
            if u.path == "/graphiques" and q.get("f") == "echarts.js.gz":
                if scenario == "sans_echarts":
                    return self.envoie(404, "text/plain", "absent")
                return self.envoie(200, "application/octet-stream", echarts_gz)
            if u.path == "/graphiques":
                corps = page
                injecte = ""
                if scenario in VUE:
                    injecte += "localStorage.setItem('graphiques-vue', '%s');" % VUE[scenario]
                if scenario in CADENCE:
                    injecte += "localStorage.setItem('graphiques-direct', '%s');" % CADENCE[scenario]
                if scenario == "rafraichi":       # relecture chaque seconde au lieu de 60 s
                    corps = corps.replace(b'"rafraichissement":60', b'"rafraichissement":1')
                if scenario == "unites":           # reglages de la page remplaces : seule l'humidite a une unite imposee
                    debut = corps.index(b"window.GRAPHIQUES=")
                    fin = corps.index(b";</script>", debut)
                    corps = corps[:fin] + (";window.GRAPHIQUES.affichage=%s;window.GRAPHIQUES.groupes={}"
                                           % json.dumps(AFFICHAGE_UNITES)).encode() + corps[fin:]
                if scenario == "masquees":
                    injecte += "localStorage.setItem('graphiques-masquees', JSON.stringify(['%s', 'sensorsCuve.niveauCuve.volume']));" % ESCLAVE
                if injecte:
                    corps = corps.replace(b"<script>window.GRAPHIQUES", ("<script>" + injecte + "</script><script>window.GRAPHIQUES").encode())
                return self.envoie(200, "text/html; charset=utf-8", corps)
            if u.path == "/histo":
                if scenario == "absent":
                    return self.envoie(404, "application/json", '{"erreur":"historique inconnu","noms":[]}')
                p = q.get("p")
                if scenario == "unites" and p in ("liste", "jour"):
                    return self.envoie(200, "application/json", json.dumps(
                        {"nom": "mesures", "series": SERIES_UNITES, "mois": []} if p == "liste" else jour_unites()))
                if p == "liste":
                    return self.envoie(200, "application/json", json.dumps(LISTE))
                if p == "mois":
                    return self.envoie(200, "application/json", json.dumps(mois(q.get("m", ""))))
                if scenario == "vide":
                    return self.envoie(200, "application/json",
                                       '{"nom":"mesures","series":["a"],"pas":300,"t0":null,"valeurs":[[null,null]]}')
                if p == "direct":
                    lectures_directes[0] += 1
                    return self.envoie(200, "application/json", json.dumps(direct(lectures_directes[0] - 1)))
                return self.envoie(200, "application/json", json.dumps(jour()))
            self.envoie(404, "text/plain", "?")

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Gestion)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, requetes


def rend(navigateur, url, profil):
    r = subprocess.run([navigateur, "--headless=new", "--disable-gpu", "--no-first-run", "--lang=fr-FR",
                        f"--user-data-dir={profil}", "--virtual-time-budget=8000", "--dump-dom", url],
                       capture_output=True, timeout=90)
    return r.stdout.decode("utf-8", "replace")


def lis_dom(dom):
    """Ce que la page affiche, scripts retires (le DOM contient le texte d'ECharts injecte). Un graphique = une div
    .g_trace qui porte les attributs data- poses par graphiques.js (sans ces attributs = bloc sans serie)."""
    d = re.sub(r"<script\b[^>]*>.*?</script>", "", dom, flags=re.S)
    trouve = lambda motif: (re.search(motif, d, re.S) or [None, None])[1]
    graphiques = []
    for attrs in re.findall(r'<div class="g_trace"([^>]*)>', d):
        a = {k: html.unescape(v) for k, v in re.findall(r'data-([a-z-]+)="([^"]*)"', attrs)}
        if "series" not in a:
            continue
        graphiques.append({"titre": a.get("titre", ""), "series": json.loads(a["series"]),
                           "legende": json.loads(a.get("legende", "[]")), "fin": int(a.get("fin", "0")),
                           "points": int(a.get("points", "0")), "echelles": json.loads(a.get("echelles", "{}")),
                           "derniers": json.loads(a.get("derniers", "{}")), "axe_x": json.loads(a.get("axe-x", "null"))})
    grafana = trouve(r'<button id="g_grafana"([^>]*)>') or ""
    entetes = [html.unescape(t) for attr, t in re.findall(r'<h3([^>]*)>(.*?)</h3>', d, re.S) if "display: none" not in attr]
    return {"graphiques": graphiques, "nb": len(graphiques), "entetes": entetes,
            "canvas": d.count("<canvas"),
            "titre": graphiques[0]["titre"] if graphiques else "",
            "legendes": [g["legende"] for g in graphiques],
            "series": [g["series"] for g in graphiques],
            "fins": [g["fin"] for g in graphiques],
            "echelles": [g["echelles"] for g in graphiques],
            "options": [html.unescape(o) for o in re.findall(r"<option[^>]*>(.*?)</option>", d)],
            "grafana": "none" not in grafana,
            "message": html.unescape(trouve(r'<p id="g_msg"[^>]*>(.*?)</p>') or "")}


# Attendus par scenario : (description, fonction du DOM lu, des requetes et de l'instant du rendu (ms) -> vrai si conforme)
MESURES_P4 = ["Température de l'eau (°C)", "Capteurs Cuve ModBus ANALOG A1 (mV)", "Capteur de hauteur (mV)"]
CUVE_P4 = ["Hauteur d'eau (cm)", "Remplissage (%)", "Volume (L)"]
OPTIONS = ["24 dernières heures", "Septembre 2026", "Août 2026 (ancienne liste de séries)",
           "Direct : arrêt", "Direct : 2 s", "Direct : 5 s", "Direct : 10 s", "Direct : 30 s", "Direct : 1 min"]
FIN_SEPTEMBRE = SEPTEMBRE + (24 * 28 - 1) * 3600
nb_direct = lambda r: sum("p=direct" in p for p, _ in r)
ATTENDUS = {
    "jour": [
        ("deux graphiques titrés « Mesures » et « Cuve » (groupe de graphiques.json)", lambda d, r, t: d["nb"] == 2 and d["canvas"] >= 2 and d["entetes"] == ["Mesures", "Cuve"] and d["titre"] == "Dernières 24 h (pas de 5 min) et temps réel"),
        ("« Mesures » : libellés de graphiques.json, esclave ModBus nommé par le persist", lambda d, r, t: d["series"][0] == MESURES_P4 and d["legendes"][0] == MESURES_P4),
        ("« Cuve » : hauteur, remplissage (facteur 100), volume", lambda d, r, t: d["series"][1] == CUVE_P4),
        ("sélecteurs : 24 h + mois du plus récent au plus ancien, cadences du direct", lambda d, r, t: d["options"] == OPTIONS),
        ("cadence par défaut 10 s : une seule lecture directe en 8 s, tout de suite", lambda d, r, t: nb_direct(r) == 1),
        ("valeur directe tracée après le pas en cours (288 pas + en cours + direct)", lambda d, r, t: d["fins"] == [TD] * 2 and all(g["points"] == 290 for g in d["graphiques"])),
        ("dernières valeurs = valeurs directes (ANALOG 29,5 ; taux 28,9 x 100)", lambda d, r, t: d["graphiques"][0]["derniers"]["Capteurs Cuve ModBus ANALOG A1 (mV)"] == 29.5 and d["graphiques"][1]["derniers"]["Remplissage (%)"] == 2890),
        ("axe des temps prolongé jusqu'à l'heure du navigateur", lambda d, r, t: all(g["axe_x"][1] >= t - 2000 for g in d["graphiques"])),
        ("échelle Y ajustée aux valeurs (sonde 20-22 °C : bas > 19, pas 0)", lambda d, r, t: 19 < d["echelles"][0]["°C"][0] < 20 and 22 < d["echelles"][0]["°C"][1] < 23),
        ("échelle Y de valeurs positives qui partent de 0 : pas sous zéro", lambda d, r, t: d["echelles"][0]["mV"][0] == 0 and d["echelles"][1]["cm"][0] == 0),
        ("un axe Y par unité (Mesures : °C et mV, l'entrée ModBus partageant l'axe mV)", lambda d, r, t: sorted(d["echelles"][0]) == sorted(["°C", "mV"])),
        ("bouton Grafana visible, aucun message", lambda d, r, t: d["grafana"] and d["message"] == ""),
        ("Referer de la page sur chaque /histo (exigé par Tasmota)", lambda d, r, t: all(ref and ref.endswith("/graphiques") for p, ref in r if p.startswith("/histo"))),
    ],
    "cache": [
        ("2 affichages, ECharts demandé une seule fois (localStorage)", lambda d, r, t: d["nb"] == 2 and sum("f=echarts" in p for p, _ in r) == 1),
    ],
    "mois": [
        ("titre du mois, moyenne horaire, pas de temps réel (mois clos)", lambda d, r, t: d["titre"] == "Septembre 2026 (moyenne horaire, bande min-max)" and nb_direct(r) == 0),
        ("légendes sans les séries min/max de la bande, une série par graphique", lambda d, r, t: d["series"] == [["Température de l'eau (°C)"], ["Remplissage (%)"]]),
        ("échelle Y du mois ajustée à la bande min-max (°C 27,5-30,5)", lambda d, r, t: 27 < d["echelles"][0]["°C"][0] < 27.5 and 30.5 < d["echelles"][0]["°C"][1] < 31),
        ("axe des temps arrêté à la fin des données (mois clos)", lambda d, r, t: all(FIN_SEPTEMBRE * 1000 <= g["axe_x"][1] <= (FIN_SEPTEMBRE + 86400) * 1000 for g in d["graphiques"])),
    ],
    "mois_a": [
        ("mois -a tracé avec sa propre liste de séries", lambda d, r, t: d["series"] == [["ancienneSerie"]] and "ancienne liste de séries" in d["titre"]),
        ("un seul graphique non vide : « Cuve » masqué, pas de titre de bloc", lambda d, r, t: d["nb"] == 1 and d["entetes"] == []),
    ],
    "masquees": [
        ("séries masquées absentes de la légende visible, toutes encore listées", lambda d, r, t: d["series"] == [MESURES_P4, CUVE_P4] and d["legendes"] == [[l for l in MESURES_P4 if "ModBus" not in l], CUVE_P4[:2]]),
    ],
    "absent": [
        ("historique pas démarré : message, pas de graphique, pas de lecture directe", lambda d, r, t: d["nb"] == 0 and "pas encore démarré" in d["message"] and nb_direct(r) == 0),
        ("bouton Grafana quand même visible", lambda d, r, t: d["grafana"]),
    ],
    "rafraichi": [
        ("la vue 24 h est relue régulièrement sans recharger la page", lambda d, r, t: sum("p=jour" in p for p, _ in r) >= 2 and d["nb"] == 2),
    ],
    "direct_arret": [
        ("cadence « arrêt » mémorisée : aucune lecture directe, fin au pas en cours", lambda d, r, t: nb_direct(r) == 0 and d["fins"] == [T_ENCOURS] * 2),
    ],
    "direct_rapide": [
        ("cadence 2 s mémorisée : lectures répétées, points ajoutés au bout des courbes", lambda d, r, t: nb_direct(r) >= 3 and d["fins"][0] >= TD + 20 and d["graphiques"][0]["points"] >= 292),
    ],
    "unites": [
        ("unités devinées de la dernière clé, ANALOG ModBus en mV, ANALOG natif sans unité, 'affichage' prioritaire", lambda d, r, t: d["nb"] == 1 and d["series"][0] == LEGENDES_UNITES),
        ("un axe Y par unité devinée", lambda d, r, t: sorted(d["echelles"][0]) == sorted(["°C", "%HR", "hPa", "lx", "", "mV", "V", "cm"])),
    ],
    "vide": [
        ("aucun pas clos : message", lambda d, r, t: d["nb"] == 0 and d["message"].startswith("Aucun pas de mesure")),
    ],
    "sans_echarts": [
        ("ECharts absent : message HTTP 404", lambda d, r, t: d["nb"] == 0 and d["message"] == "ECharts absent de la carte (HTTP 404)"),
    ],
}


def partie_navigateur(navigateur, dossier, racine):
    page = (dossier / "page.html").read_bytes()
    echarts_gz = (racine / "data/sd/js/echarts.min.js.gz").read_bytes()
    echecs = 0
    for scenario, verifs in ATTENDUS.items():
        srv, requetes = serveur(scenario, page, echarts_gz)
        url = f"http://127.0.0.1:{srv.server_address[1]}/graphiques"
        profil = dossier / f"profil_{scenario}"
        instant = time.time() * 1000              # heure du navigateur au rendu : au moins celle-ci
        try:
            dom = rend(navigateur, url, profil)
            if scenario == "cache":
                dom = rend(navigateur, url, profil)       # deuxieme affichage, meme profil
        finally:
            srv.shutdown()
            srv.server_close()
        (dossier / f"dom_{scenario}.html").write_text(dom, encoding="utf-8")
        lu = lis_dom(dom)
        print(f"{scenario}")
        for description, test in verifs:
            try:
                ok = bool(test(lu, requetes, instant))
            except (IndexError, KeyError, TypeError):      # DOM inattendu (graphique manquant) = echec, pas plantage
                ok = False
            print(("  OK     " if ok else "  ECHEC  ") + description)
            if not ok:
                echecs += 1
                print(f"         lu : {lu}")
    return echecs


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Banc des graphiques de l'historique (Berry + rendu Chrome).")
    ap.add_argument("--sans-navigateur", action="store_true", help="seulement la partie Berry")
    ap.add_argument("--garde", metavar="DOSSIER", help="garder les fichiers produits dans DOSSIER")
    args = ap.parse_args()

    racine = trouve_racine()
    berry = next((c for c in (racine / "lib/libesp32/berry/berry.exe", racine / "lib/libesp32/berry/berry") if c.exists()), None)
    if berry is None:
        sys.exit("ERREUR : berry.exe introuvable sous lib/libesp32/berry/.")
    if args.garde:
        dossier = Path(args.garde).resolve()
        dossier.mkdir(parents=True, exist_ok=True)
    else:
        temp = tempfile.TemporaryDirectory(prefix="banc_graphiques_")
        dossier = Path(temp.name)

    print("=== Partie Berry (banc_historique.be)")
    (dossier / "historique").mkdir(exist_ok=True)
    r = subprocess.run([str(berry), str(Path(__file__).with_name("banc_historique.be")), str(dossier / "historique")],
                       cwd=str(racine), capture_output=True, text=True, encoding="utf-8", errors="replace")
    sortie = (r.stdout or "") + (r.stderr or "")
    print(sortie, end="" if sortie.endswith("\n") else "\n")
    lignes = sortie.strip().splitlines()
    if r.returncode != 0 or not lignes or lignes[-1] != "BANC_HISTORIQUE: OK":    # verdict = derniere ligne
        print(">>> Banc de l'historique en echec (ou verdict introuvable).")
        return 1

    print("=== Partie Berry (banc_graphiques.be)")
    r = subprocess.run([str(berry), str(Path(__file__).with_suffix(".be")), str(dossier)],
                       cwd=str(racine), capture_output=True, text=True, encoding="utf-8", errors="replace")
    sortie = (r.stdout or "") + (r.stderr or "")
    print(sortie, end="" if sortie.endswith("\n") else "\n")
    if r.returncode != 0 or "BANC_GRAPHIQUES: OK" not in sortie:
        print(">>> Partie Berry en echec (ou verdict introuvable).")
        return 1

    recu = dossier / "echarts_recu.js.gz"
    identique = recu.exists() and recu.read_bytes() == (racine / "data/sd/js/echarts.min.js.gz").read_bytes()
    print(("  OK     " if identique else "  ECHEC  ") + "ECharts recu identique au fichier du depot (octet par octet)")
    if not identique:
        return 1

    if args.sans_navigateur:
        print("\n>>> Rendu de la page NON verifie (--sans-navigateur).\nBANC_GRAPHIQUES: OK (Berry seul)")
        return 0
    navigateur = trouve_navigateur()
    if navigateur is None:
        print("\n>>> Chrome ou Edge introuvable : rendu non verifie. Relancer avec --sans-navigateur "
              "pour la seule partie Berry.\nBANC_GRAPHIQUES: ECHEC")
        return 1
    print(f"\n=== Rendu de la page ({Path(navigateur).name}, sans interface)")
    echecs = partie_navigateur(navigateur, dossier, racine)
    print("\nBANC_GRAPHIQUES: OK" if echecs == 0 else f"\nBANC_GRAPHIQUES: ECHEC ({echecs})")
    return 0 if echecs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
