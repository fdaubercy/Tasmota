"""Sonde Chrome du dessin de la facade des volets, data/sd/js/volets.js (plan visuel-reglage-volets, A5).

UTILISATION (a la main ; aucun pio, aucune carte ; Chrome tourne ~20 s)
    %USERPROFILE%\\.platformio\\penv\\Scripts\\python.exe outils_docs/scripts_python/outils_pc/test_volets_chrome.py
        [--js FICHIER] [--capture DOSSIER]
Code de sortie 0 = vert. --js : eprouve FICHIER au lieu de data/sd/js/volets.js (temoin : copie sans l'inversion du
curseur -> scenario « inverse 1 » rouge). Client DevTools repris de test_build_page_chrome.py ; Chrome tue en fin de sonde,
meme en echec (profil temporaire sonde_volets_*).

Montage : un serveur HTTP local (thread) joue la carte. Chaque page imite l'accueil de Tasmota : div l1 des capteurs, table
des curseurs s27<n> (xdrv_01_9_webserver.ino, bloc USE_SHUTTER), puis l'ajout de data/fs/vrPages.be::accueil tel quel
(div vf, window.VOLETS, volets.js dans son propre script), puis un bouton. Les curseurs sont changes par .value, comme
Tasmota (aucun evenement). window.VOLETS des 3 cartes : forme de vrPages.be::facade, 'inverse' comme Tasmota l'applique
(1 par defaut : garage et 2e etage, 0 au grenier du RDC) ; durees de course courtes (3 a 5 s) pour une sonde breve.
Scenarios : position lue (inverse 0 et 1), poursuite entre deux valeurs (intermediaire, puis arret SANS depassement de la
derniere valeur), curseur tire a la main (le dessin rejoint la valeur et y reste quand Tasmota la renvoie),
dessin place apres la table des curseurs, aucun s271 -> rien, trappe a MPU6050 (angle, retour au curseur, rouge « sens
inverse » et « bloqué »), echelle du 2e etage, aucune erreur dans la console.
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

ECHECS = []
R = 1000                     # WebRefresh annonce par les pages de la sonde (ms), sans effet sur la poursuite
INCL = {"ouvert": 85, "ferme": 3}
PAGES = {
    "rdc": ({"toit": "deuxPans", "rafraichissement": R, "ouvertures": [
        {"id": 2, "nom": "Volet cuisine", "type": "fenetre", "place": 1, "inverse": 0, "tempsMontee": 5, "tempsDescente": 5, "inclinaison": None},
        {"id": 3, "nom": "Trappe du grenier", "type": "trappe", "place": 2, "inverse": 0, "tempsMontee": 3, "tempsDescente": 3, "inclinaison": INCL},
        {"id": 1, "nom": "Volet porte d'entrée", "type": "porte", "place": 3, "inverse": 0, "tempsMontee": 5, "tempsDescente": 5, "inclinaison": None}]},
        {1: 30, 2: 40, 3: 0}),
    "garage": ({"toit": "unPan", "rafraichissement": R, "ouvertures": [
        {"id": 1, "nom": "Volet Roulant Garage", "type": "garage", "place": 1, "inverse": 1, "tempsMontee": 3, "tempsDescente": 3, "inclinaison": None}]},
        {1: 30}),
    "etage2": ({"toit": "aucun", "rafraichissement": R, "ouvertures": [
        {"id": 1, "nom": "Trappe de Grenier 2eme", "type": "trappeEchelle", "place": 1, "inverse": 1, "tempsMontee": 3, "tempsDescente": 3, "inclinaison": None}]},
        {1: 0}),
}
TETE = ("<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'/>"
        "<title>Accueil</title><style>:root{--c_bg:#252525;--c_txt:#eaeaea;--c_ttl:#eaeaea;--c_btn:#1fa3ec;--c_btntxt:#faffff}"
        "div,input{padding:5px;font-size:1em;}body{text-align:center;font-family:verdana,sans-serif;background:var(--c_bg);}"
        "td{padding:0px;}button{border:0;border-radius:0.3rem;background:var(--c_btn);color:var(--c_btntxt);line-height:2.4rem;"
        "font-size:1.2rem;width:100%;}</style><script>function lc(){}</script></head><body>"
        "<div style='background:var(--c_bg);text-align:left;display:inline-block;color:var(--c_txt);min-width:340px;'>"
        "<div style='text-align:center;color:var(--c_ttl);'><h3>Sonde</h3><h2>VOLETS</h2></div>"
        "<div id='l1'><table style='width:100%'></table></div>")
PIED = "<p></p><form id='bouton' action='/cn' method='get'><button>Configuration</button></form></div></body></html>"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)
    return ok


def page(nom, js):
    """Accueil imite ; nom 'sans' : ajout des volets present mais aucune table de curseurs (aucun s271)."""
    facade, valeurs = PAGES["rdc" if nom == "sans" else nom]
    curseurs = "" if nom == "sans" else ("<table style='width:100%'>" + "".join(
        f"<tr><td style='width:15%'><button>&#9660;</button></td><td style='width:70%'><div style='padding:0px 2px;text-align:center;"
        f"font-size:12px;'><span>Shutter {n}</span><input id='s27{n}' type='range' min='0' max='100' value='{v}' "
        f"onchange='lc(\"u\",{n},value)'></div></td><td style='width:15%'><button>&#9650;</button></td></tr>"
        for n, v in sorted(valeurs.items())) + "</table>")
    entre = "<div id='entre'><button>Autre bouton</button></div>"          # ajouts d'autres drivers avant celui des volets
    return (TETE + curseurs + entre + "<div id='vf'></div><script>window.VOLETS=" + json.dumps(facade).replace("</", "<\\/")
            + ";</script><script>" + js.read_text(encoding="utf-8") + "</script>" + PIED)


class Carte(BaseHTTPRequestHandler):
    js: Path | None = None

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        nom = urllib.parse.urlparse(self.path).path.strip("/")
        code, corps = (200, page(nom, Carte.js)) if nom in PAGES or nom == "sans" else (404, "inconnu")
        corps = corps.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)


class Serveur(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        if not isinstance(sys.exc_info()[1], ConnectionError):
            super().handle_error(request, client_address)


class Montage:
    def __init__(self, gestionnaire=None, prefixe="sonde_volets_"):
        """gestionnaire, prefixe : serveur et profil d'une autre sonde (test_reglage_volets_chrome.py)."""
        self.t = Path(tempfile.mkdtemp(prefix=prefixe))
        self.chrome = self.http = None
        try:                     # echec en cours de montage (CDP muet, aucune cible) : Chrome et serveur arretes ici
            self.port = port_libre()
            self.http = Serveur(("127.0.0.1", self.port), gestionnaire or Carte)
            threading.Thread(target=self.http.serve_forever, daemon=True).start()
            chrome = next((c for c in CHROMES if c.is_file()), None)
            if chrome is None:
                raise FileNotFoundError("chrome.exe introuvable (Program Files, LOCALAPPDATA)")
            port_cdp = port_libre()
            self.chrome = subprocess.Popen([str(chrome), "--headless=new", f"--remote-debugging-port={port_cdp}",
                                            "--remote-allow-origins=*", f"--user-data-dir={self.t / 'profil'}",
                                            "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                                            "--window-size=480,900", "about:blank"],
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
        except BaseException:
            self.ferme()
            raise

    def ouvre(self, nom):
        self.cdp.appel("Page.navigate", url=f"http://127.0.0.1:{self.port}/{nom}")
        return attend(self.cdp, "document.readyState === 'complete' && location.pathname === '/" + nom + "'", 10)

    def ferme(self):
        tue_arbre(self.chrome)
        # Processus de Chrome hors de l'arbre (constate : quelques-uns survivent ~10 s a taskkill /T) : arretes par leur
        # profil, jusqu'a ce qu'il n'en reste aucun (10 s au plus)
        subprocess.run(["powershell", "-NoProfile", "-Command", "for ($i = 0; $i -lt 20; $i++) { $p = @(Get-CimInstance "
                        "Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -like '*" + str(self.t) + "*' }); "
                        "if (-not $p.Count) { break }; $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force "
                        "-ErrorAction SilentlyContinue }; Start-Sleep -Milliseconds 500 }"], capture_output=True)
        if self.http:
            self.http.shutdown()
        time.sleep(0.5)
        shutil.rmtree(self.t, ignore_errors=True)


def ouv(m, id_):
    """[data-ouverture, texte du pourcentage, texte complet, remplissage calcule de l'element mobile] de l'ouverture id_."""
    return m.cdp.js(f"""(() => {{ const g = document.querySelector("#vf svg g[data-id='{id_}']"); if (!g) return null;
      const t = [...document.querySelectorAll('#vf svg text')].find(x => x.previousElementSibling === g);
      const mob = g.querySelector('[data-rouge]');
      return [g.getAttribute('data-ouverture'), t.querySelector('.vf_pct').textContent, t.textContent,
              mob ? getComputedStyle(mob).fill : null]; }})()""")


def pose(m, id_, valeur):
    m.cdp.js(f"document.getElementById('s27{id_}').value = '{valeur}'; 1")      # comme eb('s27<n>').value='<v>' de Tasmota


def balise(m, angle, bloque):
    m.cdp.js("document.getElementById('l1').innerHTML = \"<table style='width:100%'><tr><th>Trappe : inclinaison</th><td>"
             f"<span data-vi='3' data-angle='{angle}' data-bloque='{bloque}'></span></td></tr></table>\"; 1")


def max_pendant(m, id_, secondes):
    """Plus grande data-ouverture de l'ouverture id_, relevee toutes les 20 ms pendant 'secondes' (dans la page)."""
    return m.cdp.js("new Promise(r => { const g = document.querySelector(\"#vf svg g[data-id='" + str(id_) + "']\"); let x = 0;"
                    " const n = setInterval(() => { x = Math.max(x, +g.getAttribute('data-ouverture')); }, 20);"
                    f" setTimeout(() => {{ clearInterval(n); r(x); }}, {int(secondes * 1000)}); }})")


def sonde_rdc(m, capture):
    verifie(bool(m.ouvre("rdc")), True, "rdc : page chargée")
    time.sleep(0.3)
    place = m.cdp.js("(() => { const vf = document.getElementById('vf'), t = document.getElementById('s271').closest('table');"
                     " return [vf.previousElementSibling === t, !!vf.querySelector('svg'), vf.nextElementSibling.id,"
                     " Math.abs(vf.querySelector('svg').getBoundingClientRect().width - t.getBoundingClientRect().width) <= 12]; })()")
    verifie(place, [True, True, "entre", True], "rdc : dessin placé juste après la table des curseurs, de la largeur de la colonne (padding du div)")
    verifie(m.cdp.js("[...document.querySelectorAll('#vf svg g[data-id]')].map(g => g.getAttribute('data-id'))"), ["2", "3", "1"],
            "rdc : ouvertures de gauche à droite (place) : cuisine, trappe, porte")
    verifie(ouv(m, 1)[:2], ["30", "30 %"], "rdc (inverse 0) : porte à 30 % dès le chargement (curseur à 30), chiffre = data-ouverture")
    verifie(ouv(m, 2)[:2], ["40", "40 %"], "rdc (inverse 0) : cuisine à 40 %")
    if capture:
        m.cdp.capture(str(Path(capture) / "facade_rdc.png"))
    # Poursuite : 40 -> 80 a 5 s de course (20 %/s) : intermediaire, puis arrivee sur 80 sans jamais la depasser
    pose(m, 2, 80)
    time.sleep(0.5)
    milieu = int(ouv(m, 2)[0])
    verifie(41 <= milieu <= 79, True, f"rdc : poursuite 40 -> 80, intermédiaire 0,5 s plus tard ({milieu} %)")
    verifie(max_pendant(m, 2, 3.0), 80, "rdc : poursuite : jamais au-delà de la dernière valeur (80) pendant 3 s")
    verifie(ouv(m, 2)[:2], ["80", "80 %"], "rdc : arrivée sur 80 %, puis immobile")
    # Curseur tire a la main sur 80 : le dessin rejoint 80 et y reste quand Tasmota renvoie 80 (course finie avant le rafraichissement)
    m.cdp.js("(() => { const c = document.getElementById('s271'); c.value = '80'; c.dispatchEvent(new Event('input'));"
             " c.dispatchEvent(new Event('change')); return 1; })()")
    time.sleep(0.5)
    milieu = int(ouv(m, 1)[0])
    verifie(31 <= milieu <= 79, True, f"rdc : curseur tiré sur 80 : le dessin le rejoint ({milieu} % à 0,5 s)")
    time.sleep(2.5)
    pose(m, 1, 80)
    time.sleep(0.5)
    verifie(ouv(m, 1)[0], "80", "rdc : curseur tiré : dessin à 80 % et y reste quand Tasmota renvoie 80")
    # Trappe a MPU6050 (3 s de course) : l'angle et non le curseur (s273 = 0)
    balise(m, "44.0", "")
    time.sleep(0.5)
    milieu = int(ouv(m, 3)[0])
    verifie(1 <= milieu <= 49, True, f"rdc : trappe à MPU : poursuite vers l'angle ({milieu} % à 0,5 s)")
    time.sleep(1.5)
    verifie(ouv(m, 3)[:2], ["50", "50 %"], "rdc : trappe à MPU : 44° -> 50 % (curseur à 0)")
    balise(m, "", "")
    time.sleep(2.0)
    verifie(ouv(m, 3)[0], "0", "rdc : trappe sans angle (capteur muet) : retour au curseur, 0 %")
    balise(m, "44.0", "sens inverse")
    time.sleep(2.0)
    o = ouv(m, 3)
    verifie([o[0], "sens inverse" in o[2], o[3]], ["50", True, "rgb(224, 69, 58)"], "rdc : trappe « sens inverse » : panneau rouge et texte")
    if capture:
        m.cdp.capture(str(Path(capture) / "facade_rdc_trappe_sens_inverse.png"))
    balise(m, "44.0", "bloque")
    time.sleep(0.2)
    verifie("bloqué" in ouv(m, 3)[2], True, "rdc : trappe « bloque » affichée « bloqué »")
    balise(m, "44.0", "")
    time.sleep(0.2)
    o = ouv(m, 3)
    verifie(["bloq" in o[2] or "sens" in o[2], o[3] == "rgb(224, 69, 58)"], [False, False], "rdc : blocage levé : plus de rouge")


def sonde_garage(m, capture):
    verifie(bool(m.ouvre("garage")), True, "garage : page chargée")
    time.sleep(0.3)
    verifie(ouv(m, 1)[:2], ["70", "70 %"], "garage (inverse 1) : curseur à 30 -> porte ouverte à 70 %")
    pose(m, 1, 0)
    time.sleep(1.5)
    verifie(ouv(m, 1)[0], "100", "garage (inverse 1) : curseur à 0 -> porte ouverte à 100 %")
    pose(m, 1, 60)
    time.sleep(2.0)
    if capture:
        m.cdp.capture(str(Path(capture) / "facade_garage.png"))


def sonde_etage2(m, capture):
    verifie(bool(m.ouvre("etage2")), True, "etage2 : page chargée")
    time.sleep(0.3)
    verifie(ouv(m, 1)[:2], ["100", "100 %"], "etage2 (inverse 1) : curseur à 0 -> trappe ouverte à 100 %")
    barreaux = m.cdp.js("document.querySelectorAll(\"#vf svg g[data-id='1'] g line\").length")
    verifie(barreaux >= 6, True, f"etage2 : échelle descendue jusqu'à l'escalier ({barreaux} traits)")
    pose(m, 1, 100)
    time.sleep(3.5)
    verifie([ouv(m, 1)[0], m.cdp.js("document.querySelectorAll(\"#vf svg g[data-id='1'] g line\").length")], ["0", 0],
            "etage2 : trappe fermée : échelle rentrée")
    pose(m, 1, 30)
    time.sleep(2.5)
    if capture:
        m.cdp.capture(str(Path(capture) / "facade_etage2.png"))


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome du dessin de la façade des volets.")
    options.add_argument("--js", default=str(RACINE / "data/sd/js/volets.js"), help="volets.js à éprouver")
    options.add_argument("--capture", metavar="DOSSIER", help="dossier des captures des 3 façades")
    args = options.parse_args()
    Carte.js = Path(args.js)
    print(f"volets.js éprouvé : {Carte.js}", flush=True)
    if args.capture:
        Path(args.capture).mkdir(parents=True, exist_ok=True)
    m = None
    try:
        m = Montage()
        sonde_rdc(m, args.capture)
        sonde_garage(m, args.capture)
        sonde_etage2(m, args.capture)
        verifie(bool(m.ouvre("sans")), True, "sans curseur : page chargée")
        time.sleep(0.3)
        verifie(m.cdp.js("[document.getElementById('vf').childElementCount, document.querySelectorAll('svg').length,"
                         " typeof window.Volets.demarre]"), [0, 0, "function"], "aucun s271 : rien n'est dessiné")
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
