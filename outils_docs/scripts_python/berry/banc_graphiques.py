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
   mois -a (periode choisie dans le graphique), series masquees, relecture periodique, cadence du direct
   (arret, 2 s), historique pas demarre, aucun pas clos, ECharts absent, page composable (A9 : 4 graphiques de
   types et periodes differents, combine, lectures mutualisees ; edition puis enregistrement, Retablir, refus
   de la carte, saisie invalide : clics simules par un script injecte, POST capture par le serveur du banc). ECharts dessine dans un canvas : la page expose ce qu'elle trace en
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
# Compositions enregistrees (window.GRAPHIQUES.graphiques) par scenario
TAUX = "sensorsCuve.niveauCuve.tauxRemplissage"
COMPOSITIONS = {
    "mois": [{"titre": "Mesures", "periode": "2026-09", "type": "courbe", "series": "autres"},
             {"titre": "Cuve", "periode": "2026-09", "type": "courbe", "series": [{"chemin": TAUX}]}],
    "composition": [
        {"titre": "Capteur", "periode": "jour", "type": "barres",
         "series": [{"chemin": "sensorsCuve.valeursAnalogiques.valeurCapteurHauteur"}]},
        {"titre": "Combiné", "periode": "jour", "type": "courbe",
         "series": [{"chemin": "sensorsCuve.niveauCuve.volume", "type": "barres"},
                    {"chemin": "sensorsCuve.niveauCuve.hauteurEau"}, {"chemin": "inconnu.serie"}]},
        {"titre": "Septembre", "periode": "2026-09", "type": "aire", "series": "autres"},
        {"titre": "Escalier", "periode": "2026-09", "type": "escalier", "series": [{"chemin": TAUX}]}],
    "retablir": [{"titre": "Seul", "periode": "jour", "type": "courbe", "series": [{"chemin": "DS18B20.Temperature"}]}],
}
# Clics simules, une fois la page tracee (attribut data-graphiques-pret)
AIDE_ACTIONS = ("function attends(f){var i=setInterval(function(){if(document.documentElement.getAttribute('data-graphiques-pret'))"
                "{clearInterval(i);f();}},50);}function clic(id){document.getElementById(id).click();}"
                "function derniere(){var c=document.querySelectorAll('.g_ed_graphique');return c[c.length-1];}")
ACTIONS = {
    "mois_a": "attends(function(){Array.prototype.forEach.call(document.querySelectorAll('.g_periode'),function(s){"
              "s.value='2026-08-a';s.dispatchEvent(new Event('change'));});});",
    "edition": "attends(function(){clic('g_modifier');clic('g_ed_ajouter');var d=derniere();"
               "d.querySelector('.g_ed_titre').value='Nouveau';d.querySelector('.g_ed_type').value='barres';"
               "d.querySelector('.g_ed_serie[data-chemin=\"DS18B20.Temperature\"] input').checked=true;"
               "clic('g_ed_enregistrer');});",
    "retablir": "attends(function(){clic('g_modifier');clic('g_ed_retablir');});",
    "refus": "attends(function(){clic('g_modifier');clic('g_ed_enregistrer');});",
    "injoignable": "attends(function(){clic('g_modifier');clic('g_ed_enregistrer');});",
    "invalide": "attends(function(){clic('g_modifier');document.querySelector('.g_ed_titre').value='';clic('g_ed_enregistrer');});",
}

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
    envois = []                        # corps des POST /graphiques (composition decodee)

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

        def do_POST(self):
            longueur = int(self.headers.get("Content-Length") or 0)
            corps = dict(parse_qsl(self.rfile.read(longueur).decode("utf-8")))
            requetes.append(("POST " + self.path, self.headers.get("Referer")))
            composition = json.loads(corps.get("composition", "\"\""))
            envois.append(composition)
            if scenario == "injoignable":      # connexion coupee sans reponse : le fetch de la page echoue
                self.close_connection = True
                self.connection.shutdown(2)
                return
            if scenario == "refus":
                return self.envoie(400, "application/json", '{"erreur":"titre trop long"}')
            return self.envoie(200, "application/json", json.dumps({"ok": True, "graphiques": composition}))

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
                if scenario in CADENCE:
                    injecte += "localStorage.setItem('graphiques-direct', '%s');" % CADENCE[scenario]
                if scenario == "rafraichi":       # relecture chaque seconde au lieu de 60 s
                    corps = corps.replace(b'"rafraichissement":60', b'"rafraichissement":1')
                if scenario in COMPOSITIONS:       # composition enregistree sur la carte
                    debut = corps.index(b"window.GRAPHIQUES=")
                    fin = corps.index(b";</script>", debut)
                    corps = corps[:fin] + (";window.GRAPHIQUES.graphiques=%s" % json.dumps(COMPOSITIONS[scenario])).encode() + corps[fin:]
                if scenario in ACTIONS:            # clics simules une fois la page tracee
                    corps = corps.replace(b"</body>", ("<script>" + AIDE_ACTIONS + ACTIONS[scenario] + "</script></body>").encode())
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
    return srv, requetes, envois


def rend(navigateur, url, profil):
    r = subprocess.run([navigateur, "--headless=new", "--disable-gpu", "--no-first-run", "--lang=fr-FR",
                        f"--user-data-dir={profil}", "--virtual-time-budget=8000", "--dump-dom", url],
                       capture_output=True, timeout=90)
    return r.stdout.decode("utf-8", "replace")


def lis_dom(dom):
    """Ce que la page affiche, scripts retires (le DOM contient le texte d'ECharts injecte). Un bloc .g_bloc par
    graphique de la composition ; son trace .g_trace porte les attributs data- poses par graphiques_trace.js (sans
    ces attributs = graphique sans courbe)."""
    d = re.sub(r"<script\b[^>]*>.*?</script>", "", dom, flags=re.S)
    trouve = lambda motif, texte=d: (re.search(motif, texte, re.S) or [None, None])[1]
    graphiques, entetes, notes = [], [], []
    for morceau in re.split(r'(?=<div class="g_bloc")', d)[1:]:
        ouverture = morceau[:morceau.index(">")]
        visible = "display: none" not in ouverture
        if visible:
            entetes.append(html.unescape(trouve(r"<h3[^>]*>(.*?)</h3>", morceau) or ""))
            note = trouve(r'<p class="g_note"[^>]*>(.*?)</p>', morceau) or ""
            if note:
                notes.append(html.unescape(note))
        attrs = trouve(r'<div class="g_trace"([^>]*)>', morceau) or ""
        a = {k: html.unescape(v) for k, v in re.findall(r'data-([a-z-]+)="([^"]*)"', attrs)}
        if "series" not in a:
            continue
        graphiques.append({"titre": a.get("titre", ""), "series": json.loads(a["series"]),
                           "types": json.loads(a.get("types", "[]")), "periode": a.get("periode", ""),
                           "rendu": json.loads(a.get("rendu", "[]")), "bandes": int(a.get("bandes", "0")),
                           "absentes": json.loads(a.get("absentes", "[]")),
                           "legende": json.loads(a.get("legende", "[]")), "fin": int(a.get("fin", "0")),
                           "points": int(a.get("points", "0")), "echelles": json.loads(a.get("echelles", "{}")),
                           "derniers": json.loads(a.get("derniers", "{}")), "axe_x": json.loads(a.get("axe-x", "null"))})
    edition = trouve(r'<div id="g_edition"([^>]*)>') or ""
    modifier = trouve(r'<button id="g_modifier"([^>]*)>') or ""
    grafana = trouve(r'<button id="g_grafana"([^>]*)>') or ""
    return {"graphiques": graphiques, "nb": len(graphiques), "entetes": entetes, "notes": notes,
            "canvas": d.count("<canvas"),
            "titre": graphiques[0]["titre"] if graphiques else "",
            "legendes": [g["legende"] for g in graphiques],
            "series": [g["series"] for g in graphiques],
            "types": [g["types"] for g in graphiques],
            "fins": [g["fin"] for g in graphiques],
            "echelles": [g["echelles"] for g in graphiques],
            "options": [html.unescape(o) for o in re.findall(r"<option[^>]*>(.*?)</option>", d)],
            "grafana": "none" not in grafana,
            "modifier": bool(modifier) and "none" not in modifier,
            "edition": bool(edition) and "none" not in edition,
            "msg_edition": html.unescape(trouve(r'<p id="g_ed_msg"[^>]*>(.*?)</p>') or ""),
            "message": html.unescape(trouve(r'<p id="g_msg"[^>]*>(.*?)</p>') or "")}


# Attendus par scenario : (description, fonction du DOM lu, des requetes, de l'instant du rendu (ms) et des
# compositions envoyees par POST -> vrai si conforme)
MESURES_P4 = ["Température de l'eau (°C)", "Capteurs Cuve ModBus ANALOG A1 (mV)", "Capteur de hauteur (mV)"]
CUVE_P4 = ["Hauteur d'eau (cm)", "Remplissage (%)", "Volume (L)"]
DIRECT = ["Direct : arrêt", "Direct : 2 s", "Direct : 5 s", "Direct : 10 s", "Direct : 30 s", "Direct : 1 min"]
PERIODES = ["24 dernières heures", "Mois en cours", "Septembre 2026", "Août 2026 (ancienne liste de séries)"]
FIN_SEPTEMBRE = SEPTEMBRE + (24 * 28 - 1) * 3600
nb_direct = lambda r: sum("p=direct" in p for p, _ in r)
nb_lectures = lambda r, motif: sum(p.startswith("/histo") and motif in p for p, _ in r)
CUVE_EXPLICITE = [{"chemin": c} for c in ["sensorsCuve.niveauCuve.hauteurEau", TAUX, "sensorsCuve.niveauCuve.volume"]]
ATTENDUS = {
    "jour": [
        ("deux graphiques titrés « Mesures » et « Cuve » (composition par défaut tirée des groupes)", lambda d, r, t, e: d["nb"] == 2 and d["canvas"] >= 2 and d["entetes"] == ["Mesures", "Cuve"] and d["titre"] == "Dernières 24 h (pas de 5 min) et temps réel"),
        ("« Mesures » : libellés de graphiques.json, esclave ModBus nommé par le persist", lambda d, r, t, e: d["series"][0] == MESURES_P4 and d["legendes"][0] == MESURES_P4),
        ("« Cuve » : hauteur, remplissage (facteur 100), volume ; tout en courbes", lambda d, r, t, e: d["series"][1] == CUVE_P4 and d["types"] == [["courbe"] * 3] * 2),
        ("sélecteurs : cadences du direct, puis une période par graphique (24 h, mois en cours, mois du plus récent au plus ancien)", lambda d, r, t, e: d["options"] == DIRECT + PERIODES * 2),
        ("cadence par défaut 10 s : une seule lecture directe en 8 s, tout de suite", lambda d, r, t, e: nb_direct(r) == 1),
        ("une seule lecture de p=jour pour les deux graphiques (mutualisée)", lambda d, r, t, e: nb_lectures(r, "p=jour") == 1),
        ("valeur directe tracée après le pas en cours (288 pas + en cours + direct)", lambda d, r, t, e: d["fins"] == [TD] * 2 and all(g["points"] == 290 for g in d["graphiques"])),
        ("dernières valeurs = valeurs directes (ANALOG 29,5 ; taux 28,9 x 100)", lambda d, r, t, e: d["graphiques"][0]["derniers"]["Capteurs Cuve ModBus ANALOG A1 (mV)"] == 29.5 and d["graphiques"][1]["derniers"]["Remplissage (%)"] == 2890),
        ("axe des temps prolongé jusqu'à l'heure du navigateur", lambda d, r, t, e: all(g["axe_x"][1] >= t - 2000 for g in d["graphiques"])),
        ("échelle Y ajustée aux valeurs (sonde 20-22 °C : bas > 19, pas 0)", lambda d, r, t, e: 19 < d["echelles"][0]["°C"][0] < 20 and 22 < d["echelles"][0]["°C"][1] < 23),
        ("échelle Y de valeurs positives qui partent de 0 : pas sous zéro", lambda d, r, t, e: d["echelles"][0]["mV"][0] == 0 and d["echelles"][1]["cm"][0] == 0),
        ("un axe Y par unité (Mesures : °C et mV, l'entrée ModBus partageant l'axe mV)", lambda d, r, t, e: sorted(d["echelles"][0]) == sorted(["°C", "mV"])),
        ("boutons Grafana et « Modifier » visibles, aucun message", lambda d, r, t, e: d["grafana"] and d["modifier"] and not d["edition"] and d["message"] == ""),
        ("Referer de la page sur chaque /histo (exigé par Tasmota)", lambda d, r, t, e: all(ref and ref.endswith("/graphiques") for p, ref in r if p.startswith("/histo"))),
    ],
    "cache": [
        ("2 affichages, ECharts demandé une seule fois (localStorage)", lambda d, r, t, e: d["nb"] == 2 and sum("f=echarts" in p for p, _ in r) == 1),
    ],
    "mois": [
        ("composition enregistrée en septembre : titre du mois, pas de temps réel (mois clos)", lambda d, r, t, e: d["titre"] == "Septembre 2026 (moyenne horaire, bande min-max)" and nb_direct(r) == 0),
        ("légendes sans les séries min/max de la bande ; « autres » = séries du mois placées nulle part ailleurs", lambda d, r, t, e: d["series"] == [["Température de l'eau (°C)"], ["Remplissage (%)"]]),
        ("une seule lecture du mois pour les deux graphiques, aucune de p=jour", lambda d, r, t, e: nb_lectures(r, "p=mois") == 1 and nb_lectures(r, "p=jour") == 0),
        ("échelle Y du mois ajustée à la bande min-max (°C 27,5-30,5)", lambda d, r, t, e: 27 < d["echelles"][0]["°C"][0] < 27.5 and 30.5 < d["echelles"][0]["°C"][1] < 31),
        ("axe des temps arrêté à la fin des données (mois clos)", lambda d, r, t, e: all(FIN_SEPTEMBRE * 1000 <= g["axe_x"][1] <= (FIN_SEPTEMBRE + 86400) * 1000 for g in d["graphiques"])),
    ],
    "mois_a": [
        ("période changée dans chaque graphique : mois -a tracé avec sa propre liste de séries", lambda d, r, t, e: d["series"] == [["ancienneSerie"]] and "ancienne liste de séries" in d["titre"] and d["graphiques"][0]["periode"] == "2026-08-a"),
        ("groupe « Cuve » sans série ce mois-là : masqué", lambda d, r, t, e: d["nb"] == 1 and d["entetes"] == ["Mesures"]),
    ],
    "masquees": [
        ("séries masquées absentes de la légende visible, toutes encore listées", lambda d, r, t, e: d["series"] == [MESURES_P4, CUVE_P4] and d["legendes"] == [[l for l in MESURES_P4 if "ModBus" not in l], CUVE_P4[:2]]),
    ],
    "absent": [
        ("historique pas démarré : message, pas de graphique, pas de lecture directe", lambda d, r, t, e: d["nb"] == 0 and "pas encore démarré" in d["message"] and nb_direct(r) == 0),
        ("bouton Grafana quand même visible, pas de « Modifier »", lambda d, r, t, e: d["grafana"] and not d["modifier"]),
    ],
    "rafraichi": [
        ("la vue 24 h est relue régulièrement sans recharger la page", lambda d, r, t, e: nb_lectures(r, "p=jour") >= 2 and d["nb"] == 2),
    ],
    "direct_arret": [
        ("cadence « arrêt » mémorisée : aucune lecture directe, fin au pas en cours", lambda d, r, t, e: nb_direct(r) == 0 and d["fins"] == [T_ENCOURS] * 2),
    ],
    "direct_rapide": [
        ("cadence 2 s mémorisée : lectures répétées, points ajoutés au bout des courbes", lambda d, r, t, e: nb_direct(r) >= 3 and d["fins"][0] >= TD + 20 and d["graphiques"][0]["points"] >= 292),
    ],
    "unites": [
        ("unités devinées de la dernière clé, ANALOG ModBus en mV, ANALOG natif sans unité, 'affichage' prioritaire", lambda d, r, t, e: d["nb"] == 1 and d["series"][0] == LEGENDES_UNITES),
        ("un axe Y par unité devinée", lambda d, r, t, e: sorted(d["echelles"][0]) == sorted(["°C", "%HR", "hPa", "lx", "", "mV", "V", "cm"])),
    ],
    "composition": [
        ("4 graphiques dans l'ordre enregistré", lambda d, r, t, e: d["nb"] == 4 and d["entetes"] == ["Capteur", "Combiné", "Septembre", "Escalier"]),
        ("types : barres, combiné (barres + courbe, type de la série prioritaire), aire, escalier", lambda d, r, t, e: d["types"] == [["barres"], ["barres", "courbe"], ["aire"], ["escalier"]]),
        ("rendu ECharts : bar, bar + line, line:area, line:step", lambda d, r, t, e: [g["rendu"] for g in d["graphiques"]] == [["bar"], ["bar", "line"], ["line:area"], ["line:step"]]),
        ("vue mois : bande min-max pour l'aire, pas pour l'escalier ; aucune en 24 h", lambda d, r, t, e: [g["bandes"] for g in d["graphiques"]] == [0, 0, 1, 0]),
        ("séries de chaque graphique ; « autres » de septembre = la seule série placée nulle part ailleurs", lambda d, r, t, e: d["series"] == [["Capteur de hauteur (mV)"], ["Volume (L)", "Hauteur d'eau (cm)"], ["Température de l'eau (°C)"], ["Remplissage (%)"]]),
        ("périodes propres à chaque graphique", lambda d, r, t, e: [g["periode"] for g in d["graphiques"]] == ["jour", "jour", "2026-09", "2026-09"]),
        ("lectures mutualisées : une de p=jour, une du mois, pour 4 graphiques", lambda d, r, t, e: nb_lectures(r, "p=jour") == 1 and nb_lectures(r, "p=mois") == 1),
        ("série inconnue signalée « absente », le graphique reste tracé", lambda d, r, t, e: d["graphiques"][1]["absentes"] == ["inconnu.serie"] and any("Absente" in n and "inconnu serie" in n for n in d["notes"])),
    ],
    "edition": [
        ("« Ajouter », titre, type, une série, « Enregistrer » : un POST avec la composition explicite", lambda d, r, t, e: e == [[
            {"titre": "Mesures", "periode": "jour", "type": "courbe", "series": "autres"},
            {"titre": "Cuve", "periode": "jour", "type": "courbe", "series": CUVE_EXPLICITE},
            {"titre": "Nouveau", "periode": "jour", "type": "barres", "series": [{"chemin": "DS18B20.Temperature"}]}]]),
        ("POST avec le Referer de la page (exigé par Tasmota)", lambda d, r, t, e: any(p.startswith("POST /graphiques") and ref and ref.endswith("/graphiques") for p, ref in r)),
        ("page redessinée avec la composition renvoyée : 3 graphiques, « Mesures » sans la série déplacée", lambda d, r, t, e: d["entetes"] == ["Mesures", "Cuve", "Nouveau"] and d["series"][0] == MESURES_P4[1:] and d["types"][2] == ["barres"]),
        ("édition fermée, message de confirmation", lambda d, r, t, e: not d["edition"] and d["modifier"] and d["message"] == "Composition enregistrée sur la carte."),
    ],
    "retablir": [
        ("« Rétablir » : POST de null, retour à la composition par défaut", lambda d, r, t, e: e == [None] and d["entetes"] == ["Mesures", "Cuve"] and d["message"] == "Composition par défaut rétablie."),
    ],
    "refus": [
        ("refus de la carte : message de la carte, édition restée ouverte", lambda d, r, t, e: len(e) == 1 and d["edition"] and d["msg_edition"] == "Refusé par la carte : titre trop long"),
    ],
    "injoignable": [
        ("carte injoignable à l'enregistrement : message clair, édition restée ouverte", lambda d, r, t, e: len(e) == 1 and d["edition"] and d["msg_edition"] == "Carte injoignable : composition non enregistrée."),
    ],
    "invalide": [
        ("titre vide : rien n'est envoyé, message immédiat", lambda d, r, t, e: e == [] and d["edition"] and d["msg_edition"].startswith("Graphique 1 : titre de 1 à 60")),
    ],
    "vide": [
        ("aucun pas clos : message", lambda d, r, t, e: d["nb"] == 0 and d["message"].startswith("Aucun pas de mesure")),
    ],
    "sans_echarts": [
        ("ECharts absent : message HTTP 404", lambda d, r, t, e: d["nb"] == 0 and d["message"] == "ECharts absent de la carte (HTTP 404)"),
    ],
}


def partie_navigateur(navigateur, dossier, racine):
    page = (dossier / "page.html").read_bytes()
    echarts_gz = (racine / "data/sd/js/echarts.min.js.gz").read_bytes()
    echecs = 0
    for scenario, verifs in ATTENDUS.items():
        srv, requetes, envois = serveur(scenario, page, echarts_gz)
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
                ok = bool(test(lu, requetes, instant, envois))
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
