"""Sonde Chrome du gabarit commun des pages de graphiques (atelier des graphiques, plan A3).

UTILISATION (a la main ; aucun pio, aucune carte ; Chrome tourne ~40 s)
    %USERPROFILE%\\.platformio\\penv\\Scripts\\python.exe outils_docs/scripts_python/outils_pc/test_pages_graphiques_chrome.py
        [--capture DOSSIER] [--sans-temoin]
Code de sortie 0 = vert : la page passe toutes les verifications ET le temoin (meme page, erreur JS volontaire au
chargement) est detecte. Client DevTools repris de test_build_page_chrome.py.

Montage : un petit serveur HTTP local (thread) joue la carte. /pages?p=demo assemble la page EXACTEMENT comme
data/fs/pagesGraphiques.be::pagesGraphiques_page (style du theme sombre de Tasmota, <style> + CSS, gabarit HTML,
window.PAGE_GRAPHIQUES, puis les deux JS dans un seul <script>), avec les fichiers du depot (data/sd/...).
/pages?f=valeurs et /histo?p=jour rendent des valeurs fixes ; ECharts et liquidfill sont servis COMPRESSES
(data/sd/js/*.gz), comme par la carte : la page les decompresse (1er chargement) puis les relit du localStorage.
Description : 5 graphiques (cadran, demi-cercle sur une calculee, liquide, courbe 24 h en pleine largeur dont la 1re serie
est en forme objet {chemin, libelle, unite, couleur}, anneau dont une serie est absente), validee par
atelier_graphiques_description.valide. Courbe : libelle en legende, couleur de la serie, unite sur l'axe et dans
l'infobulle (showTip, texte affiche par ECharts). Captures en 1400 et 380 px.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
sys.path.insert(0, str(ICI))
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre, tue_arbre   # client DevTools stdlib
import atelier_graphiques_description

SD = RACINE / "data" / "sd"
ECHECS = []
DESCRIPTION = {
    "version": 1,
    "pages": [{"id": "demo", "titre": "Cuve et garage", "graphiques": [
        {"type": "cadran", "titre": "Volume de la cuve", "series": ["sensorsCuve.niveauCuve.volume"], "min": 0, "max": 6732,
         "zones": [[0.2, "#c0392b"], [0.4, "#c27400"]], "cadence": 2},
        {"type": "demi-cercle", "titre": "Manque à remplir", "series": ["calc:cuve.manque"], "min": 0, "max": 6732, "cadence": 2},
        {"type": "liquide", "titre": "Taux de remplissage", "series": ["sensorsCuve.niveauCuve.tauxRemplissage"], "min": 0,
         "max": 1, "zones": [[0.2, "#c0392b"]], "cadence": 2},
        {"type": "courbe", "titre": "Températures (24 h)", "series": [
            {"chemin": "DS18B20.Temperature", "libelle": "Cuve", "unite": "°C", "couleur": "#ff00aa"},
            {"chemin": "ESP32.Temperature", "unite": "°C"}],
         "periode": "jour", "largeur": "pleine", "hauteur": 260, "min": 0, "max": 60, "zones": [[0.5, "#c27400"]]},
        {"type": "anneau", "titre": "Entrées analogiques", "series": ["ANALOG.A1", "capteur.debranche"], "cadence": 2}]}],
    "calculees": {"cuve.manque": {"formule": "6732 - sensorsCuve.niveauCuve.volume", "nature": "direct"}}}
VALEURS = {"sensorsCuve.niveauCuve.volume": 4000, "sensorsCuve.niveauCuve.tauxRemplissage": 0.59, "ANALOG.A1": 1234}
T0 = 1762128000
JOUR = {"nom": "mesures", "series": ["DS18B20.Temperature", "ESP32.Temperature"], "pas": 300, "t0": T0,
        "valeurs": [[round(20 + 8 * ((k % 96) / 96), 2) for k in range(288)], [round(41 + (k % 12) / 4, 2) for k in range(288)]],
        "tEncours": T0 + 288 * 300, "encours": [22.5, 43]}
# Debut de page de Tasmota (HTTP_HEAD_STYLE1/2/3 et couleurs du theme sombre de my_user_config.h), resume
TETE = ("<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' "
        "content='width=device-width,initial-scale=1,user-scalable=no'/><title>{titre}</title><style>"
        ":root{--c_bg:#252525;--c_frm:#4f4f4f;--c_ttl:#eaeaea;--c_txt:#eaeaea;--c_btn:#1fa3ec;--c_btntxt:#faffff;"
        "--c_btnhvr:#0e70a4;--c_in:#dddddd;--c_intxt:#000000}"
        "div,fieldset,input,select{padding:5px;font-size:1em;}p{margin:0.5em 0;}"
        "body{text-align:center;font-family:verdana,sans-serif;background:var(--c_bg);}"
        "button{border:0;border-radius:0.3rem;background:var(--c_btn);color:var(--c_btntxt);line-height:2.4rem;"
        "font-size:1.2rem;width:100%;cursor:pointer;}a{color:var(--c_btn);text-decoration:none;}</style></head><body>"
        "<div style='background:var(--c_bg);text-align:left;display:inline-block;color:var(--c_txt);min-width:340px;"
        "position:relative;'><div style='text-align:center;color:var(--c_ttl);'><h3>ESP32-P4</h3><h2>SERVEUR-GARAGE</h2></div>")
PIED = "<p></p><form action='/' method='get'><button>Menu principal</button></form></div></body></html>"
TEMOIN = "document.getElementById('absent-du-gabarit').onclick = null;   // TEMOIN : TypeError au chargement\n"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)
    return ok


def page_carte(temoin):
    """La page telle que pagesGraphiques_page l'envoie (ordre et echappement '</' -> '<\\/' compris)."""
    config = {"page": DESCRIPTION["pages"][0], "calculees": DESCRIPTION["calculees"], "bibliotheque": "echarts-6.1.0",
              "extension": "liquidfill-3.1.0", "historique": True}
    lis = lambda p: (SD / p).read_text(encoding="utf-8")
    return (TETE.replace("{titre}", "Cuve et garage") + "<style>" + lis("css/pages_graphiques.css") + "</style>"
            + lis("html/pages_graphiques.html")
            + "<script>window.PAGE_GRAPHIQUES=" + json.dumps(config).replace("</", "<\\/") + ";</script><script>"
            + (TEMOIN if temoin else "") + lis("js/pages_graphiques_formule.js") + "\n" + lis("js/pages_graphiques.js") + "\n"
            + "</script>" + PIED)


class Carte(BaseHTTPRequestHandler):
    temoin = False
    lectures = []           # chemins demandes a /pages?f=valeurs, dans l'ordre

    def log_message(self, format, *args):        # silence : la sonde n'affiche que ses verifications
        pass

    def envoie(self, code, corps, mime):
        corps = corps.encode("utf-8") if isinstance(corps, str) else corps
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
        if url.path == "/pages" and q.get("f") == "valeurs":
            chemins = q.get("c", "").split(",")
            Carte.lectures.append(chemins)
            self.envoie(200, json.dumps({"t": int(time.time()), "valeurs": {c: VALEURS.get(c) for c in chemins}}), "application/json")
        elif url.path == "/pages" and q.get("f") == "liquidfill.js.gz":
            self.envoie(200, (SD / "js/echarts-liquidfill.min.js.gz").read_bytes(), "application/octet-stream")
        elif url.path == "/pages" and q.get("p") == "demo":
            self.envoie(200, page_carte(Carte.temoin), "text/html; charset=utf-8")
        elif url.path == "/graphiques" and q.get("f") == "echarts.js.gz":
            self.envoie(200, (SD / "js/echarts.min.js.gz").read_bytes(), "application/octet-stream")
        elif url.path == "/histo" and q.get("n") == "mesures" and q.get("p") == "jour":
            self.envoie(200, json.dumps(JOUR), "application/json")
        else:
            self.envoie(404, '{"erreur": "inconnu"}', "application/json")


class Serveur(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):     # connexion coupee par Chrome a sa fermeture : sans interet
        if not isinstance(sys.exc_info()[1], ConnectionError):
            super().handle_error(request, client_address)


class Montage:
    def __init__(self, temoin):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_pages_graphiques_"))
        Carte.temoin, Carte.lectures = temoin, []
        self.port = port_libre()
        self.http = Serveur(("127.0.0.1", self.port), Carte)
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.port}/pages?p=demo"
        chrome = next((c for c in CHROMES if c.is_file()), None)
        if chrome is None:
            raise FileNotFoundError("chrome.exe introuvable (Program Files, LOCALAPPDATA)")
        port_cdp = port_libre()
        self.chrome = subprocess.Popen([str(chrome), "--headless=new", f"--remote-debugging-port={port_cdp}",
                                        "--remote-allow-origins=*", f"--user-data-dir={self.t / 'profil'}",
                                        "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                                        "--window-size=1400,1000", "about:blank"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        limite = time.monotonic() + 20
        while True:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port_cdp}/json/list", timeout=2) as r:
                    cibles = json.loads(r.read().decode("utf-8"))
                break
            except OSError:
                if time.monotonic() > limite:
                    raise
                time.sleep(0.2)
        self.cdp = Cdp(next(c for c in cibles if c.get("type") == "page")["webSocketDebuggerUrl"])
        for domaine in ("Runtime.enable", "Log.enable", "Page.enable"):
            self.cdp.appel(domaine)

    def ouvre(self, largeur):
        self.cdp.appel("Emulation.setDeviceMetricsOverride", width=largeur, height=1000, deviceScaleFactor=1,
                       mobile=largeur < 600)
        self.cdp.appel("Page.navigate", url=self.url)

    def ferme(self):
        tue_arbre(self.chrome)
        self.http.shutdown()
        time.sleep(0.5)
        shutil.rmtree(self.t, ignore_errors=True)


JS_ETAT = """(() => {
  const t = [...document.querySelectorAll('#pg_page .pg_tuile')];
  const modele = el => { try { const g = echarts.getInstanceByDom(el); return g ? g.getModel().getSeries().map(s => s.subType) : null; }
                         catch (e) { return 'erreur ' + e.message; } };
  return {titres: t.map(e => e.getAttribute('data-titre')), rendus: t.map(e => e.getAttribute('data-rendu')),
          modeles: t.map(modele), pleine: t.map(e => e.classList.contains('pg_pleine')),
          hauts: t.map(e => Math.round(e.getBoundingClientRect().top)), larges: t.map(e => Math.round(e.getBoundingClientRect().width)),
          demi: (t[1] && t[1].querySelector('svg')) ? t[1].querySelector('svg').textContent.replace(/\\s/g, '') : '',
          zones: (() => { try { return echarts.getInstanceByDom(t[3]).getOption().series[0].markArea.data.length; } catch (e) { return -1; } })(),
          courbe: (() => { try { const o = echarts.getInstanceByDom(t[3]).getOption();
                                 return [o.series.map(s => s.name), o.series[0].color, o.yAxis[0].name, o.legend[0].data || null]; }
                           catch (e) { return 'erreur ' + e.message; } })(),
          pageLarge: document.documentElement.scrollWidth, fenetre: window.innerWidth,
          cache: Object.keys(localStorage).sort(), msg: (document.querySelector('.pg_msg') || {}).textContent};
})()"""


def sonde_largeur(m, largeur, capture):
    m.ouvre(largeur)
    pret = attend(m.cdp, "document.querySelectorAll('#pg_page .pg_tuile[data-titre]').length === 5 && "
                         "!!window.echarts && document.querySelectorAll('#pg_page .pg_tuile svg').length === 5", 30)
    verifie(pret, True, f"{largeur} px : 5 graphiques traces")
    time.sleep(1.5)                                       # fin de mise en page d'ECharts avant mesure et capture
    e = m.cdp.js(JS_ETAT)
    verifie([("série absente" in (x or "")) for x in e["titres"]], [False, False, False, False, True],
            f"{largeur} px : « série absente » sur l'anneau seul (les autres graphiques tracés)")
    verifie(e["rendus"], ["gauge", "svg", "liquidFill", "line", "pie"], f"{largeur} px : style de chaque tuile")
    verifie(e["modeles"], [["gauge"], None, ["liquidFill"], ["line", "line"], ["pie"]],
            f"{largeur} px : séries réellement créées par ECharts (liquidfill chargé)")
    verifie("2732" in e["demi"], True, f"{largeur} px : demi-cercle = calculée 6732 - 4000 ({e['demi']!r})")
    verifie(e["zones"], 1, f"{largeur} px : zone de la courbe en markArea")
    verifie(e["courbe"][:3], [["Cuve", "Temperature"], "#ff00aa", "°C"],
            f"{largeur} px : courbe : libelle, couleur de la serie objet, unite commune sur l'axe")
    infobulle = m.cdp.js("(() => { const t = document.querySelectorAll('#pg_page .pg_tuile')[3], g = echarts.getInstanceByDom(t);"
                         " g.dispatchAction({type: 'showTip', seriesIndex: 0, dataIndex: 100});"
                         " return new Promise(r => setTimeout(() => r(t.innerText), 400)); })()")
    verifie(isinstance(infobulle, str) and "Cuve" in infobulle and "°C" in infobulle, True,
            f"{largeur} px : infobulle de la courbe : libelle et unite affiches ({infobulle!r})")
    m.cdp.js("echarts.getInstanceByDom(document.querySelectorAll('#pg_page .pg_tuile')[3]).dispatchAction({type: 'hideTip'}); 1")
    verifie(e["pageLarge"] <= e["fenetre"], True, f"{largeur} px : page {e['pageLarge']} px <= fenêtre {e['fenetre']} px")
    deux_colonnes = e["hauts"][0] == e["hauts"][1] and e["larges"][3] > e["larges"][0] * 1.5
    verifie(deux_colonnes, largeur >= 700, f"{largeur} px : {'deux colonnes, courbe en pleine largeur' if largeur >= 700 else 'une colonne'}")
    verifie(e["cache"], ["echarts-6.1.0", "liquidfill-3.1.0"], f"{largeur} px : bibliothèques en cache localStorage")
    if capture:
        m.cdp.capture(str(Path(capture) / f"pages_graphiques_{largeur}.png"))


def sonde_onglet_cache(m):
    """Onglet cache : aucune lecture ; de nouveau visible : lecture immediate."""
    m.cdp.js("Object.defineProperty(document, 'hidden', {configurable: true, get: () => true}); 1")
    time.sleep(0.5)
    avant = len(Carte.lectures)
    time.sleep(4.5)                                       # deux cadences de 2 s
    verifie(len(Carte.lectures), avant, "onglet caché : aucune lecture de /pages?f=valeurs")
    m.cdp.js("delete document.hidden; document.dispatchEvent(new Event('visibilitychange')); 1")
    time.sleep(1.5)
    verifie(len(Carte.lectures) > avant, True, "onglet de nouveau visible : lecture reprise")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome des pages de graphiques.")
    options.add_argument("--capture", metavar="DOSSIER", help="dossier des captures 1400 et 380 px")
    options.add_argument("--sans-temoin", action="store_true")
    args = options.parse_args()
    verifie(atelier_graphiques_description.valide(DESCRIPTION), [], "description de la sonde valide (valide() de A1)")
    if args.capture:
        Path(args.capture).mkdir(parents=True, exist_ok=True)
    for temoin in ([False] if args.sans_temoin else [False, True]):
        print(f"\n=== {'TEMOIN (erreur JS volontaire)' if temoin else 'page servie comme par la carte'} ===", flush=True)
        m = None
        try:
            m = Montage(temoin)
            if temoin:
                m.ouvre(1400)
                time.sleep(3)
                verifie(len(m.cdp.erreurs()) > 0, True, "TEMOIN : l'erreur JS volontaire est détectée")
                continue
            sonde_largeur(m, 1400, args.capture)
            sonde_onglet_cache(m)
            sonde_largeur(m, 380, args.capture)
            verifie(sorted({tuple(c) for c in Carte.lectures if len(c) > 12}), [], "jamais plus de 12 chemins par requête")
            verifie([x for x in m.cdp.erreurs() if "favicon.ico" not in x], [], "aucune erreur dans la console")
        except FileNotFoundError as erreur:
            print(f"BLOQUE : {erreur}")
            return 3
        except Exception as erreur:
            verifie(repr(erreur), "pas d'exception de la sonde", "sonde : déroulement")
        finally:
            if m:
                m.ferme()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
