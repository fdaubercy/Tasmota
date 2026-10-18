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
1. Lance `berry.exe banc_graphiques.be <dossier>` depuis la racine : envoi d'uPlot par morceaux, 404,
   acces refuse, URL Grafana (%topic%), page /graphiques (gabarit, window.GRAPHIQUES), filtre des faux
   zeros de la cuve du maitre P4. La page est generee par le VRAI graphiquesFonctions.page(), avec la
   configuration reelle du persist du P4.
2. Compare octet par octet uPlot recu et data/sd/js/uPlot.iife.min.js.
3. Sert cette page et des reponses /histo fixes (un petit serveur par scenario, port libre, 127.0.0.1)
   et la rend dans Chrome sans interface (--dump-dom) : 24 h, cache d'uPlot, mois avec trou, mois -a,
   series masquees, historique pas demarre, aucun pas clos, uPlot absent. Juge le DOM (titre, legende,
   cases, selecteur, bouton Grafana, message) et les requetes recues (Referer exige par Tasmota).

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
    """6 series du P4 ; l'entree de l'esclave avec un trou de 20 pas, la sonde absente, le reste en rampe."""
    v = []
    for nom in SERIES_P4:
        if nom == ESCLAVE:
            v.append([None if 100 <= i < 120 else round(28 + (i % 50) / 25, 2) for i in range(288)])
        elif nom == "DS18B20.Temperature":
            v.append([None] * 288)
        else:
            v.append([round(i / 10, 2) for i in range(288)])
    return {"nom": "mesures", "series": SERIES_P4, "pas": 300, "t0": T0, "valeurs": v}


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


def serveur(scenario, page, uplot, css):
    """Un serveur par scenario (port libre) : origine distincte, donc localStorage distinct."""
    requetes = []

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
            if u.path == "/graphiques" and q.get("f") == "uplot.js":
                if scenario == "sans_uplot":
                    return self.envoie(404, "text/plain", "absent")
                return self.envoie(200, "application/javascript", uplot)
            if u.path == "/graphiques" and q.get("f") == "uplot.css":
                return self.envoie(200, "text/css", css)
            if u.path == "/graphiques":
                corps = page
                injecte = ""
                if scenario in VUE:
                    injecte += "localStorage.setItem('graphiques-vue', '%s');" % VUE[scenario]
                if scenario == "masquees":
                    injecte += "localStorage.setItem('graphiques-masquees', JSON.stringify(['%s', 'sensorsCuve.niveauCuve.volume']));" % ESCLAVE
                if injecte:
                    corps = corps.replace(b"<script>window.GRAPHIQUES", ("<script>" + injecte + "</script><script>window.GRAPHIQUES").encode())
                return self.envoie(200, "text/html; charset=utf-8", corps)
            if u.path == "/histo":
                if scenario == "absent":
                    return self.envoie(404, "application/json", '{"erreur":"historique inconnu","noms":[]}')
                p = q.get("p")
                if p == "liste":
                    return self.envoie(200, "application/json", json.dumps(LISTE))
                if p == "mois":
                    return self.envoie(200, "application/json", json.dumps(mois(q.get("m", ""))))
                if scenario == "vide":
                    return self.envoie(200, "application/json",
                                       '{"nom":"mesures","series":["a"],"pas":300,"t0":null,"valeurs":[[null,null]]}')
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
    """Ce que la page affiche, scripts retires (le DOM contient le texte d'uPlot injecte)."""
    d = re.sub(r"<script\b[^>]*>.*?</script>", "", dom, flags=re.S)
    trouve = lambda motif: (re.search(motif, d, re.S) or [None, None])[1]
    legende = [html.unescape(l) for attr, l in
               re.findall(r'<tr class="u-series"([^>]*)>.*?class="u-label"[^>]*>(.*?)</div>', d, re.S)
               if "display: none" not in attr]
    grafana = trouve(r'<button id="g_grafana"([^>]*)>') or ""
    graphiques = []
    for morceau in d.split('<div class="uplot')[1:]:
        graphiques.append([html.unescape(l) for attr, l in
                           re.findall(r'<tr class="u-series"([^>]*)>.*?class="u-label"[^>]*>(.*?)</div>', morceau, re.S)
                           if "display: none" not in attr])
    entetes = [html.unescape(t) for attr, t in re.findall(r'<h3([^>]*)>(.*?)</h3>', d, re.S) if "display: none" not in attr]
    return {"canvas": d.count("<canvas"), "graphiques": graphiques, "entetes": entetes,
            "titre": html.unescape(trouve(r'class="u-title"[^>]*>(.*?)</div>') or ""),
            "legende": legende,
            "cases": len(re.findall(r'<input type="checkbox"', d)),
            "options": [html.unescape(o) for o in re.findall(r"<option[^>]*>(.*?)</option>", d)],
            "grafana": "none" not in grafana,
            "message": html.unescape(trouve(r'<p id="g_msg"[^>]*>(.*?)</p>') or "")}


# Attendus par scenario : (description, fonction du DOM lu et des requetes -> vrai si conforme)
MESURES_P4 = ["Heure", "Température de l'eau (°C)", "Capteurs Cuve ModBus ANALOG A1", "Capteur de hauteur (mV)"]
CUVE_P4 = ["Heure", "Hauteur d'eau (cm)", "Remplissage (%)", "Volume (L)"]
OPTIONS = ["24 dernières heures", "Septembre 2026", "Août 2026 (ancienne liste de séries)"]
ATTENDUS = {
    "jour": [
        ("deux graphiques titrés « Mesures » et « Cuve » (groupe de graphiques.json)", lambda d, r: d["canvas"] == 2 and d["entetes"] == ["Mesures", "Cuve"] and d["titre"] == "Dernières 24 h (pas de 5 min)"),
        ("« Mesures » : libellés de graphiques.json, esclave ModBus nommé par le persist", lambda d, r: d["graphiques"][0] == MESURES_P4),
        ("« Cuve » : hauteur, remplissage (facteur 100), volume", lambda d, r: d["graphiques"][1] == CUVE_P4),
        ("6 cases, sélecteur 24 h + mois du plus récent au plus ancien", lambda d, r: d["cases"] == 6 and d["options"] == OPTIONS),
        ("bouton Grafana visible, aucun message", lambda d, r: d["grafana"] and d["message"] == ""),
        ("Referer de la page sur chaque /histo (exigé par Tasmota)", lambda d, r: all(ref and ref.endswith("/graphiques") for p, ref in r if p.startswith("/histo"))),
    ],
    "cache": [
        ("2 affichages, uPlot demandé une seule fois (localStorage)", lambda d, r: d["canvas"] == 2 and sum("f=uplot.js" in p for p, _ in r) == 1),
    ],
    "mois": [
        ("titre du mois, moyenne horaire", lambda d, r: d["titre"] == "Septembre 2026 (moyenne horaire, bande min-max)"),
        ("légendes sans les séries min/max de la bande, une série par graphique", lambda d, r: d["graphiques"] == [["Date", "Température de l'eau (°C)"], ["Date", "Remplissage (%)"]]),
    ],
    "mois_a": [
        ("mois -a tracé avec sa propre liste de séries", lambda d, r: d["legende"] == ["Date", "ancienneSerie"] and "ancienne liste de séries" in d["titre"]),
        ("un seul graphique non vide : « Cuve » masqué, pas de titre de bloc", lambda d, r: d["canvas"] == 1 and d["entetes"] == []),
    ],
    "masquees": [
        ("séries décochées absentes du tracé, 6 cases", lambda d, r: d["cases"] == 6 and d["graphiques"] == [[l for l in MESURES_P4 if "ModBus" not in l], CUVE_P4[:3]]),
    ],
    "absent": [
        ("historique pas démarré : message, pas de graphique", lambda d, r: d["canvas"] == 0 and "pas encore démarré" in d["message"]),
        ("bouton Grafana quand même visible", lambda d, r: d["grafana"]),
    ],
    "vide": [
        ("aucun pas clos : message", lambda d, r: d["canvas"] == 0 and d["message"].startswith("Aucun pas de mesure")),
    ],
    "sans_uplot": [
        ("uPlot absent : message HTTP 404", lambda d, r: d["canvas"] == 0 and d["message"] == "uPlot absent de la carte (HTTP 404)"),
    ],
}


def partie_navigateur(navigateur, dossier, racine):
    page = (dossier / "page.html").read_bytes()
    uplot = (racine / "data/sd/js/uPlot.iife.min.js").read_bytes()
    css = (racine / "data/sd/css/uPlot.min.css").read_bytes()
    echecs = 0
    for scenario, verifs in ATTENDUS.items():
        srv, requetes = serveur(scenario, page, uplot, css)
        url = f"http://127.0.0.1:{srv.server_address[1]}/graphiques"
        profil = dossier / f"profil_{scenario}"
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
                ok = bool(test(lu, requetes))
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

    recu = dossier / "uplot_recu.js"
    identique = recu.exists() and recu.read_bytes() == (racine / "data/sd/js/uPlot.iife.min.js").read_bytes()
    print(("  OK     " if identique else "  ECHEC  ") + "uPlot recu identique au fichier du depot (octet par octet)")
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
