r"""Banc de la page /cuve (jauges du volume et du taux) : Berry (banc_cuve_page.be) puis rendu dans Chrome.

UTILISATION
-----------
    python outils_docs/scripts_python/berry/banc_cuve_page.py [--sans-navigateur] [--garde DOSSIER] [--sources DOSSIER]

Depuis n'importe quel dossier : la racine du depot, berry.exe et Chrome (ou Edge) sont deduits.
Code de sortie 0 si tout est vert, 1 sinon -> utilisable comme garde avant un televersement.
  --sans-navigateur  : seulement la partie Berry (le rendu n'est alors PAS verifie).
  --garde DOSSIER    : garde les fichiers produits (page, DOM de chaque scenario) dans DOSSIER.
  --sources DOSSIER  : (temoin) lit fs/ et sd/ dans DOSSIER au lieu de data/ ; sert a prouver que le banc mord,
                       en l'orientant vers une COPIE de data/ dont on a casse cuve.js (jamais le vrai fichier).

CE QU'IL FAIT
-------------
1. Lance `berry.exe banc_cuve_page.be <dossier>` depuis la racine : acces refuse, fichier de l'extension liquidfill
   (chemin, MIME), page /cuve (ordre css / html / window.CUVE / cuve.js, volumeMax, '</' echappe), dimensions par
   defaut, routes /cuve du maitre P4 (vrai CONTROLE_GARAGE, persist reel) et de la cuve. La page est generee par le
   VRAI cuvePageFonctions.page().
2. Compare octet par octet l'extension recue et data/sd/js/echarts-liquidfill.min.js.gz.
3. Sert cette page, les VRAIS ECharts (/graphiques?f=echarts.js.gz) et extension (/cuve?f=liquidfill.js.gz) et un
   /histo simule par scenario (un serveur par scenario, port libre, 127.0.0.1), la rend dans Chrome sans interface
   et juge ce que la page expose : data-volume et data-taux de #c_jauges, message #c_msg, SVG d'ECharts dessine
   dans #c_volume, requetes recues. Scenarios : normal, chemin du P4 prefixe, valeurs null, historique 404,
   historique inactif (aucune requete /histo), extension absente (le taux reste affiche), cadran des tensions
   (data-tension-brute / data-tension-sonde, sonde absente, tensions sans niveau).

MISE AU POINT DE CHROME (mesuree le 2026-10-31)
-----------------------------------------------
`--dump-dom` seul rend la page au chargement, AVANT les fetch : DOM vide. `--virtual-time-budget=N` fait avancer
le temps virtuel jusqu'a N ms, puis dumpe ; mais l'animation des vagues de liquidFill (requestAnimationFrame sans
fin) peut empecher Chrome sans fenetre de rendre la main. Le banc lance donc Chrome avec un budget court (6000 ms :
chargement, decompression des deux bibliotheques, une lecture /histo ; la relecture est a 10 s, hors budget), un
`timeout` de 60 s cote Python (un nouvel essai), et --user-data-dir neuf par scenario (localStorage vide : les bibliotheques sont
rechargees a chaque scenario, comme a la premiere visite). Un depassement du timeout est un ECHEC du scenario
(Chrome tue avec son arbre de processus), pas un blocage du banc. Chrome est lance avec
--force-prefers-reduced-motion : cuve.js coupe alors la vague (waveAnimation), seule animation sans fin ; sans cela,
le scenario « normal » depassait les 60 s quand la machine etait chargee (indexeur C/C++ a 100 %, 2026-10-31).

CE QU'IL NE TESTE PAS
---------------------
La vraie carte : ni le serveur web de Tasmota (Referer), ni la RAM, ni les vraies mesures. ECharts dessine ici en
SVG : le rendu de l'animation des vagues et les couleurs ne sont pas jugees (seules les valeurs tracees le sont).
Le format telephone n'est pas juge (Chrome sans interface ne descend pas sous 500 px de fenetre). Un banc vert ne
remplace pas l'essai sur la cuve et le P4.
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

BUDGET_MS = 6000       # temps virtuel de Chrome (voir l'en-tete)
DELAI_S = 60           # delai reel maximal d'un rendu (un nouvel essai si depasse : voir rend)


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


# ---- Reponses /histo simulees ------------------------------------------------------------------
NORMAL = ["sensorsCuve.niveauCuve.hauteurEau", "sensorsCuve.niveauCuve.tauxRemplissage", "sensorsCuve.niveauCuve.volume"]
P4 = ["garage." + s for s in NORMAL]
BRUTE = "sensorsCuve.valeursAnalogiques.valeurCapteurHauteur"       # mV a l'entree de l'ADS1115
SONDE = "sensorsCuve.valeursAnalogiques.tensionSonde_V"             # volts, sonde recalculee (absente sur le P4 aujourd'hui)


def direct(series, valeurs):
    return {"nom": "mesures", "series": series, "t": 1792230900, "valeurs": valeurs}


# scenario -> (page servie, statut /histo, corps /histo, liquidfill servi)
SCENARIOS = {
    "normal": ("page.html", 200, direct(NORMAL + [BRUTE, SONDE], [68, 0.62, 4174, 2000, 6.8]), True),
    "sans_tension_sonde": ("page.html", 200, direct(NORMAL + [BRUTE], [68, 0.62, 4174, 2000]), True),
    "tensions_sans_niveau": ("page.html", 200, direct(NORMAL + [BRUTE, SONDE], [None, None, None, 2000, 6.8]), True),
    "p4_prefixe": ("page.html", 200, direct(P4, [68, 0.62, 4174]), True),
    "valeurs_null": ("page.html", 200, direct(NORMAL, [None, None, None]), True),
    "histo_404": ("page.html", 404, {"erreur": "historique inconnu"}, True),
    "nom_vide": ("page_sans_nom.html", 200, direct(NORMAL, [68, 0.62, 4174]), True),
    "sans_extension": ("page.html", 200, direct(NORMAL, [68, 0.62, 4174]), False),
}


def serveur(scenario, pages, echarts_gz, liquid_gz):
    """Un serveur par scenario (port libre) : origine distincte, donc localStorage distinct."""
    page, statut, corps_histo, avec_extension = SCENARIOS[scenario]
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
            requetes.append(self.path)
            if u.path == "/cuve" and q.get("f") == "liquidfill.js.gz":
                if not avec_extension:
                    return self.envoie(404, "text/plain", "absent")
                return self.envoie(200, "application/octet-stream", liquid_gz)
            if u.path == "/cuve":
                return self.envoie(200, "text/html; charset=utf-8", pages[page])
            if u.path == "/graphiques" and q.get("f") == "echarts.js.gz":
                return self.envoie(200, "application/octet-stream", echarts_gz)
            if u.path == "/histo" and q.get("p") == "direct":
                return self.envoie(statut, "application/json", json.dumps(corps_histo))
            self.envoie(404, "text/plain", "?")

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Gestion)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, requetes


def rend(navigateur, url, profil, essai=1):
    """DOM de la page apres BUDGET_MS de temps virtuel ; chaine vide si Chrome ne rend pas la main deux fois de suite
    (ECHEC du scenario). Un seul nouvel essai, annonce : Chrome sans fenetre se bloque parfois sur un scenario pris au
    hasard (constate le 2026-10-31, machine saturee, jamais deux fois de suite), un defaut de la page bloquerait les deux."""
    try:
        r = subprocess.run([navigateur, "--headless=new", "--disable-gpu", "--no-first-run", "--lang=fr-FR",
                            "--force-prefers-reduced-motion",
                            f"--user-data-dir={profil}", f"--virtual-time-budget={BUDGET_MS}", "--dump-dom", url],
                           capture_output=True, timeout=DELAI_S)
    except subprocess.TimeoutExpired:
        if essai == 1:
            print(f"  (Chrome n'a pas rendu la main en {DELAI_S} s : nouvel essai, une seule fois)")
            return rend(navigateur, url, profil, 2)
        return ""
    return r.stdout.decode("utf-8", "replace")


def lis_dom(dom):
    """Ce que la page expose, scripts retires (le DOM contient le texte d'ECharts injecte)."""
    d = re.sub(r"<script\b[^>]*>.*?</script>", "", dom, flags=re.S)
    attr = lambda nom: html.unescape((re.search(r'<div id="c_jauges"[^>]*\sdata-%s="([^"]*)"' % nom, d) or [None, None])[1] or "") \
        if 'id="c_jauges"' in d else None
    msg = re.search(r'<p id="c_msg"[^>]*>(.*?)</p>', d, re.S)
    volume = re.search(r'<div id="c_volume"[^>]*>(.*?)</div>\s*<figcaption', d, re.S)
    return {"volume": attr("volume"), "taux": attr("taux"),
            "message": html.unescape(msg.group(1)) if msg else None,
            "svg": bool(volume) and "<svg" in volume.group(1),
            "t_brute": attr("tension-brute"), "t_sonde": attr("tension-sonde"),
            "texte_brute": (re.search(r'<b id="c_tBrute"[^>]*>(.*?)</b>', d) or [None, None])[1],
            "texte_sonde": (re.search(r'<b id="c_tSonde"[^>]*>(.*?)</b>', d) or [None, None])[1],
            "svg_tension": bool(re.search(r'<div id="c_tension"[^>]*>(?:(?!</figure>).)*<svg', d, re.S)),
            "arc": (re.search(r'<path id="c_arc"[^>]*stroke-dasharray="([^"]*)"', d) or [None, None])[1],
            "texte_taux": (re.search(r'<text id="c_tauxTexte"[^>]*>(.*?)</text>', d) or [None, None])[1]}


nb_histo = lambda r: sum(p.startswith("/histo") for p in r)
ATTENDUS = {
    "normal": [
        ("volume 4174 et taux 62 (fraction x 100, arrondi) exposés, message vide", lambda d, r: d["volume"] == "4174" and d["taux"] == "62" and d["message"] == ""),
        ("jauge liquide : un SVG ECharts est dessiné dans #c_volume (renderer svg)", lambda d, r: d["svg"]),
        ("demi-cercle : arc à 62 sur 100 et texte « 62 % »", lambda d, r: d["arc"] == "62 100" and d["texte_taux"] == "62 %"),
        ("cadran des tensions : brute 2000 mV -> data-tension-brute « 2.00 », sonde « 6.80 », textes « 2,00 » et « 6,80 »", lambda d, r: d["t_brute"] == "2.00" and d["t_sonde"] == "6.80"
         and d["texte_brute"] == "2,00" and d["texte_sonde"] == "6,80"),
        ("cadran des tensions : un SVG ECharts est dessiné dans #c_tension (renderer svg)", lambda d, r: d["svg_tension"]),
        ("une lecture /histo?p=direct du nom de l'historique, ECharts et l'extension chargés", lambda d, r: nb_histo(r) == 1 and "/histo?n=mesures&p=direct" in r
         and "/graphiques?f=echarts.js.gz" in r and "/cuve?f=liquidfill.js.gz" in r),
    ],
    "sans_tension_sonde": [
        ("tensionSonde_V absente (cas du P4) : brute tracée (2.00), sonde vide et « -,-- »", lambda d, r: d["t_brute"] == "2.00" and d["t_sonde"] == "" and d["texte_sonde"] == "-,--" and d["texte_brute"] == "2,00"),
        ("volume et taux inchangés, message vide, SVG du cadran dessiné", lambda d, r: d["volume"] == "4174" and d["taux"] == "62" and d["message"] == "" and d["svg_tension"]),
    ],
    "tensions_sans_niveau": [
        ("volume et taux null, tensions présentes : cadran tracé quand même (2.00 / 6.80), volume et taux vides", lambda d, r: d["volume"] == "" and d["taux"] == "" and d["t_brute"] == "2.00" and d["t_sonde"] == "6.80"),
    ],
    "p4_prefixe": [
        ("séries préfixées du P4 (garage.sensorsCuve...) trouvées par suffixe : 4174 et 62", lambda d, r: d["volume"] == "4174" and d["taux"] == "62" and d["message"] == ""),
    ],
    "valeurs_null": [
        ("valeurs null : data-volume et data-taux vides, « Mesure indisponible »", lambda d, r: d["volume"] == "" and d["taux"] == "" and d["message"] == "Mesure indisponible (capteur en erreur)."),
        ("demi-cercle vide : arc à 0 et texte « -,-- % »", lambda d, r: d["arc"] == "0 100" and d["texte_taux"] == "-,-- %"),
    ],
    "histo_404": [
        ("/histo 404 : message « Historique pas encore démarré », rien de tracé", lambda d, r: (d["message"] or "").startswith("Historique pas encore démarré") and d["volume"] == "" and d["taux"] == ""),
    ],
    "nom_vide": [
        ("nom d'historique vide : message « L'historique n'est pas actif », aucune requête /histo", lambda d, r: (d["message"] or "").startswith("L'historique n'est pas actif") and nb_histo(r) == 0),
    ],
    "sans_extension": [
        ("extension absente (404) : le taux reste affiché (62), message d'erreur", lambda d, r: d["taux"] == "62" and d["volume"] == "4174" and "absent de la carte (HTTP 404)" in (d["message"] or "")
         and "Le taux reste affiché" in (d["message"] or "")),
        ("demi-cercle tracé malgré l'absence de l'extension", lambda d, r: d["arc"] == "62 100" and d["texte_taux"] == "62 %"),
    ],
}


def partie_navigateur(navigateur, dossier, racine, sources):
    pages = {n: (dossier / n).read_bytes() for n in ("page.html", "page_sans_nom.html")}
    echarts_gz = (sources / "sd/js/echarts.min.js.gz").read_bytes()
    liquid_gz = (sources / "sd/js/echarts-liquidfill.min.js.gz").read_bytes()
    echecs = 0
    for scenario, verifs in ATTENDUS.items():
        srv, requetes = serveur(scenario, pages, echarts_gz, liquid_gz)
        url = f"http://127.0.0.1:{srv.server_address[1]}/cuve"
        try:
            dom = rend(navigateur, url, dossier / f"profil_{scenario}")
        finally:
            srv.shutdown()
            srv.server_close()
        (dossier / f"dom_{scenario}.html").write_text(dom, encoding="utf-8")
        lu = lis_dom(dom)
        print(f"{scenario}")
        if not dom:
            print(f"  ECHEC  Chrome n'a pas rendu la main en {DELAI_S} s")
            echecs += 1
            continue
        for description, test in verifs:
            try:
                ok = bool(test(lu, requetes))
            except (IndexError, KeyError, TypeError):
                ok = False
            print(("  OK     " if ok else "  ECHEC  ") + description)
            if not ok:
                echecs += 1
                print(f"         lu : {lu}")
    return echecs


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Banc de la page /cuve (Berry + rendu Chrome).")
    ap.add_argument("--sans-navigateur", action="store_true", help="seulement la partie Berry")
    ap.add_argument("--garde", metavar="DOSSIER", help="garder les fichiers produits dans DOSSIER")
    ap.add_argument("--sources", metavar="DOSSIER", help="temoin : dossier fs/ + sd/ a la place de data/")
    args = ap.parse_args()

    racine = trouve_racine()
    sources = Path(args.sources).resolve() if args.sources else racine / "data"
    berry = next((c for c in (racine / "lib/libesp32/berry/berry.exe", racine / "lib/libesp32/berry/berry") if c.exists()), None)
    if berry is None:
        sys.exit("ERREUR : berry.exe introuvable sous lib/libesp32/berry/.")
    if args.garde:
        dossier = Path(args.garde).resolve()
        dossier.mkdir(parents=True, exist_ok=True)
    else:
        temp = tempfile.TemporaryDirectory(prefix="banc_cuve_page_")
        dossier = Path(temp.name)

    print("=== Partie Berry (banc_cuve_page.be)")
    cmd = [str(berry), str(Path(__file__).with_suffix(".be")), str(dossier)]
    if args.sources:
        cmd.append(str(sources))
    r = subprocess.run(cmd, cwd=str(racine), capture_output=True, text=True, encoding="utf-8", errors="replace")
    sortie = (r.stdout or "") + (r.stderr or "")
    print(sortie, end="" if sortie.endswith("\n") else "\n")
    lignes = sortie.strip().splitlines()
    if r.returncode != 0 or not lignes or lignes[-1] != "BANC_CUVE_PAGE: OK":      # verdict = derniere ligne
        print(">>> Partie Berry en echec (ou verdict introuvable).\nBANC_CUVE_PAGE: ECHEC")
        return 1

    recu = dossier / "liquidfill_recu.js.gz"
    identique = recu.exists() and recu.read_bytes() == (sources / "sd/js/echarts-liquidfill.min.js.gz").read_bytes()
    print(("  OK     " if identique else "  ECHEC  ") + "extension recue identique au fichier du depot (octet par octet)")
    if not identique:
        print("BANC_CUVE_PAGE: ECHEC")
        return 1

    if args.sans_navigateur:
        print("\n>>> Rendu de la page NON verifie (--sans-navigateur).\nBANC_CUVE_PAGE: OK (Berry seul)")
        return 0
    navigateur = trouve_navigateur()
    if navigateur is None:
        print("\n>>> Chrome ou Edge introuvable : rendu non verifie. Relancer avec --sans-navigateur "
              "pour la seule partie Berry.\nBANC_CUVE_PAGE: ECHEC")
        return 1
    print(f"\n=== Rendu de la page ({Path(navigateur).name}, sans interface, budget {BUDGET_MS} ms)")
    echecs = partie_navigateur(navigateur, dossier, racine, sources)
    print("\nBANC_CUVE_PAGE: OK" if echecs == 0 else f"\nBANC_CUVE_PAGE: ECHEC ({echecs})")
    return 0 if echecs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
