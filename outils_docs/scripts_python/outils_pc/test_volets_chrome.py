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
inverse » et « bloqué », texte en --c_txtwrn, angle a virgule du firmware fr_FR, id non entier sans selecteur), echelle du
2e etage, animation vivante apres une exception dans une image, aucune erreur dans la console.
Rideau du garage (2026-11-12, controleRideau.be) : aucun curseur, position lue a 'source' (reponse JSON de la sonde) : dessin
laisse a la place de #vf, position suivie, maitre muet grise, position inconnue « ? », reponse illisible = muet, requetes
jamais simultanees (reponse lente). Temoin : volets.js d'avant le mode source -> scenario rideau rouge.
Facade du garage (2026-11-13, plan facade-garage-capteurs) : scenario « p4 » (decor, pastilles des fins de course lues a
/volets?f=capteurs : couleurs, titres, fondu, gris si la route echoue, clignotement d'incoherence au bout de 6 s) et « rideauc »
(carte du rideau : etats dans la reponse de la source, aucune requete a /volets?f=capteurs).
Maison du RDC (2026-11-13) : scenario « maison » (decor 'maison', rapporteur de la trappe suivant la balise data-vi, voyant de la
camera lu a /volets?f=capteurs, clic confirme -> POST /volets action=camera, clic refuse -> rien, gris si la route echoue).
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
PANNE = "panne simulee de la sonde"      # exception injectee dans une image (sonde_garage), seule erreur toleree
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
RIDEAU = {"toit": "unPan", "rafraichissement": 300, "ouvertures": [
    {"id": 1, "nom": "Volet Roulant Garage", "type": "garage", "place": 1, "inverse": 1, "tempsMontee": 3, "tempsDescente": 3,
     "inclinaison": None, "source": "/rideau?f=position&id=1"}]}
FINS = {"module": "garage", "ouverture": "Capteur Ouverture Rideau Garage", "fermeture": "Capteur Fermeture Rideau Garage"}
PAGES["p4"] = ({"toit": "unPan", "rafraichissement": R, "decor": ["chevrefeuille", "porte", "pergola"], "ouvertures": [
    {"id": 1, "nom": "Volet Roulant Garage", "type": "garage", "place": 1, "inverse": 1, "tempsMontee": 3, "tempsDescente": 3,
     "inclinaison": None, "finsDeCourse": {"ouverture": FINS["ouverture"], "fermeture": FINS["fermeture"]}}]}, {1: 30})
PAGES["maison"] = (dict(PAGES["rdc"][0], decor=["maison"], camera={"nom": "Caméra de façade", "id": 7}), {1: 30, 2: 40, 3: 0})
RIDEAU_C = {"toit": "unPan", "rafraichissement": 300, "decor": ["chevrefeuille", "porte", "pergola"], "ouvertures": [
    {"id": 1, "nom": "Volet Roulant Garage", "type": "garage", "place": 1, "inverse": 1, "tempsMontee": 3, "tempsDescente": 3,
     "inclinaison": None, "source": "/rideau?f=position&id=1", "finsDeCourse": {"ouverture": "Capteur Ouverture", "fermeture": "Capteur Fermeture"}}]}
TETE = ("<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'/>"
        "<title>Accueil</title><style>:root{--c_bg:#252525;--c_txt:#eaeaea;--c_txtwrn:#ff5661;--c_ttl:#eaeaea;--c_btn:#1fa3ec;--c_btntxt:#faffff}"
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
    facade, valeurs = (RIDEAU, {}) if nom == "rideau" else (RIDEAU_C, {}) if nom == "rideauc" else PAGES["rdc" if nom == "sans" else nom]
    curseurs = "" if nom in ("sans", "rideau", "rideauc") else ("<table style='width:100%'>" + "".join(
        f"<tr><td style='width:15%'><button>&#9660;</button></td><td style='width:70%'><div style='padding:0px 2px;text-align:center;"
        f"font-size:12px;'><span>Shutter {n}</span><input id='s27{n}' type='range' min='0' max='100' value='{v}' "
        f"onchange='lc(\"u\",{n},value)'></div></td><td style='width:15%'><button>&#9650;</button></td></tr>"
        for n, v in sorted(valeurs.items())) + "</table>")
    entre = "<div id='entre'><button>Autre bouton</button></div>"          # ajouts d'autres drivers avant celui des volets
    return (TETE + curseurs + entre + "<div id='vf'></div><script>window.VOLETS=" + json.dumps(facade).replace("<", "\\u003c")
            + ";</script><script>" + js.read_text(encoding="utf-8") + "</script>" + PIED)


class Carte(BaseHTTPRequestHandler):
    js: Path | None = None
    position = {"ouverture": 30, "muet": False}       # reponse de /rideau?f=position ; None : reponse illisible (500 en texte)
    verrou = threading.Lock()
    simultanees = 0
    max_simultanees = 0
    requetes = 0
    capteurs: dict | None = None                      # reponse de /volets?f=capteurs ; None : 500 en texte
    posts: list = []                                  # corps des POST /volets recus (camera)
    req_capteurs = 0

    def log_message(self, format, *args):
        pass

    def position_rideau(self):
        """Comme controleRideau.be::route, reponse lente (0,5 s > rafraichissement de 0,3 s) pour voir un chevauchement."""
        with Carte.verrou:
            Carte.simultanees += 1
            Carte.requetes += 1
            Carte.max_simultanees = max(Carte.max_simultanees, Carte.simultanees)
        time.sleep(0.5)
        with Carte.verrou:
            Carte.simultanees -= 1
        p = Carte.position
        return (500, "panne", "text/plain") if p is None else (200, json.dumps(p), "application/json")

    def do_POST(self):
        corps = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8")
        args = dict(urllib.parse.parse_qsl(corps))
        Carte.posts.append(args)
        if args.get("action") == "camera" and isinstance(Carte.capteurs, dict):
            Carte.capteurs = dict(Carte.capteurs, camera=args.get("etat"))
        reponse = json.dumps({"ok": True, "message": "Caméra de façade", "etat": {}}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(reponse)))
        self.end_headers()
        self.wfile.write(reponse)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        nom, type_ = url.path.strip("/"), "text/html; charset=utf-8"
        if nom in ("rideau", "rideauc") and url.query:
            code, corps, type_ = self.position_rideau()
        elif nom == "volets" and url.query == "f=capteurs":
            Carte.req_capteurs += 1
            code, corps, type_ = ((500, "panne", "text/plain") if Carte.capteurs is None
                                  else (200, json.dumps(Carte.capteurs), "application/json"))
        else:
            code, corps = (200, page(nom, Carte.js)) if nom in PAGES or nom in ("sans", "rideau", "rideauc") else (404, "inconnu")
        corps = corps.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", type_)
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
    # comme eb('s27<n>').value='<v>' de Tasmota ; querySelector : getElementById est piege par sonde_garage (panne du 1er appel)
    m.cdp.js(f"document.querySelector('#s27{id_}').value = '{valeur}'; 1")


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
    balise(m, "44,0", "")            # virgule : web_send_decimal du firmware fr_FR
    time.sleep(0.5)
    milieu = int(ouv(m, 3)[0])
    verifie(1 <= milieu <= 49, True, f"rdc : trappe à MPU : poursuite vers l'angle ({milieu} % à 0,5 s)")
    time.sleep(1.5)
    verifie(ouv(m, 3)[:2], ["50", "50 %"], "rdc : trappe à MPU : '44,0' (virgule) -> 50 % (curseur à 0)")
    balise(m, "", "")
    time.sleep(2.0)
    verifie(ouv(m, 3)[0], "0", "rdc : trappe sans angle (capteur muet) : retour au curseur, 0 %")
    balise(m, "44.0", "sens inverse")
    time.sleep(2.0)
    o = ouv(m, 3)
    verifie([o[0], "sens inverse" in o[2], o[3]], ["50", True, "rgb(224, 69, 58)"], "rdc : trappe « sens inverse » : panneau rouge et texte")
    verifie(m.cdp.js("getComputedStyle(document.querySelector(\"#vf svg g[data-id='3']\").nextElementSibling.querySelector('.vf_pct')).fill"),
            "rgb(255, 86, 97)", "rdc : texte « sens inverse » en --c_txtwrn de Tasmota")
    if capture:
        m.cdp.capture(str(Path(capture) / "facade_rdc_trappe_sens_inverse.png"))
    balise(m, "44.0", "bloque")
    time.sleep(0.2)
    verifie("bloqué" in ouv(m, 3)[2], True, "rdc : trappe « bloque » affichée « bloqué »")
    balise(m, "44.0", "")
    time.sleep(0.2)
    o = ouv(m, 3)
    verifie(["bloq" in o[2] or "sens" in o[2], o[3] == "rgb(224, 69, 58)"], [False, False], "rdc : blocage levé : plus de rouge")
    # Identifiant non entier : aucun sélecteur [data-vi] construit (il lèverait à chaque image)
    n0 = len(m.cdp.erreurs())
    f = {"toit": "aucun", "ouvertures": [dict(PAGES["rdc"][0]["ouvertures"][1], id="1']")]}
    verifie(m.cdp.js("Volets.demarre(" + json.dumps(f) + ") ? 1 : 0"), 1, "rdc : demarre avec un id non entier")
    time.sleep(0.5)
    verifie(m.cdp.erreurs()[n0:], [], "rdc : id non entier : aucune erreur (pas de sélecteur construit)")


def sonde_garage(m, capture):
    verifie(bool(m.ouvre("garage")), True, "garage : page chargée")
    time.sleep(0.3)
    verifie(ouv(m, 1)[:2], ["70", "70 %"], "garage (inverse 1) : curseur à 30 -> porte ouverte à 70 %")
    # Une exception dans une image (lecture du curseur) n'arrête pas l'animation : erreur attendue, ignorée en fin de sonde
    m.cdp.js("(() => { const g = document.getElementById.bind(document); let n = 0;"
             " document.getElementById = id => { if (id === 's271' && !n++) throw new Error('" + PANNE + "'); return g(id); }; return 1; })()")
    pose(m, 1, 0)
    attend(m.cdp, "document.querySelector(\"#vf svg g[data-id='1']\").getAttribute('data-ouverture') === '100'", 5)
    verifie([ouv(m, 1)[0], any(PANNE in x for x in m.cdp.erreurs())], ["100", True],
            "garage (inverse 1) : curseur à 0 -> porte ouverte à 100 % (animation vivante après l'exception levée dans une image)")
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


def etat_rideau(m):
    """[data-ouverture, texte du pourcentage, « maître muet » affiche, opacite] de la porte du rideau."""
    o = ouv(m, 1)
    return [o[0], o[1], "maître muet" in o[2], m.cdp.js("document.querySelector(\"#vf svg g[data-id='1']\").style.opacity")]


def jusqua(condition, secondes):
    """Attend une condition (jamais une duree fixe, lecon du 2026-11-13) ; rend son dernier resultat."""
    fin = time.monotonic() + secondes
    while time.monotonic() < fin:
        if condition():
            return True
        time.sleep(0.1)
    return False


def releve(m, lecture, fin_cond, secondes):
    """Releve toutes les valeurs lues jusqu'a fin_cond (ou le delai) : une etape intermediaire n'est jamais manquee."""
    vus, fin = [], time.monotonic() + secondes
    while time.monotonic() < fin:
        v = lecture()
        vus.append(v)
        if fin_cond(v):
            break
        time.sleep(0.05)
    return vus


def sonde_rideau(m, capture):
    Carte.position, Carte.max_simultanees, Carte.requetes = {"ouverture": 30, "muet": False}, 0, 0
    verifie(bool(m.ouvre("rideau")), True, "rideau : page chargée")
    time.sleep(1.2)
    place = m.cdp.js("(() => { const vf = document.getElementById('vf'); return [vf.previousElementSibling.id, !!vf.querySelector('svg')]; })()")
    verifie(place, ["entre", True], "rideau : aucun curseur : dessin laissé à la place de #vf")
    verifie(etat_rideau(m), ["30", "30 %", False, ""], "rideau : position lue à 'source' (30 %), sans grisé")
    Carte.position = {"ouverture": 90, "muet": False}
    vus = [int(v) for v in releve(m, lambda: ouv(m, 1)[0], lambda v: int(v) >= 90, 8)]
    verifie(any(31 <= v <= 89 for v in vus), True, f"rideau : poursuite 30 -> 90 (positions vues : {sorted(set(vus))})")
    jusqua(lambda: etat_rideau(m) == ["90", "90 %", False, ""], 8)
    verifie(etat_rideau(m), ["90", "90 %", False, ""], "rideau : arrivée sur 90 %")
    Carte.position = {"ouverture": 100, "muet": True}
    jusqua(lambda: etat_rideau(m) == ["100", "100 %", True, "0.45"], 8)
    verifie(etat_rideau(m), ["100", "100 %", True, "0.45"], "rideau : maître muet, fin de course ouverte : 100 %, grisé, « maître muet »")
    if capture:
        m.cdp.capture(str(Path(capture) / "facade_rideau_muet.png"))
    Carte.position = {"ouverture": None, "muet": True}
    jusqua(lambda: etat_rideau(m) == ["", "?", True, "0.45"], 8)
    verifie(etat_rideau(m), ["", "?", True, "0.45"], "rideau : maître muet entre les fins de course : « ? », grisé")
    Carte.position = {"ouverture": 20, "muet": False}
    jusqua(lambda: etat_rideau(m) == ["20", "20 %", False, ""], 8)
    verifie(etat_rideau(m), ["20", "20 %", False, ""], "rideau : maître revenu : 20 %, plus de grisé")
    Carte.position = None
    jusqua(lambda: etat_rideau(m)[1:] == ["?", True, "0.45"], 8)
    verifie(etat_rideau(m)[1:], ["?", True, "0.45"], "rideau : réponse illisible (500 en texte) : muet, « ? »")
    Carte.position = {"ouverture": 40, "muet": False}
    time.sleep(2.5)
    Carte.position = {"ouverture": "abc", "muet": False}
    time.sleep(1.2)
    verifie(etat_rideau(m)[:2], ["", "?"], "rideau : ouverture non numérique : « ? », jamais « NaN »")
    Carte.position = {"ouverture": 20, "muet": False}
    time.sleep(1.2)
    verifie([Carte.max_simultanees, Carte.requetes >= 8], [1, True],
            f"rideau : requêtes jamais simultanées malgré une réponse lente ({Carte.requetes} requêtes)")


def pastille(m, cle):
    """[remplissage calcule du boitier, titre, transition du boitier, opacite du groupe] de la pastille cle."""
    return m.cdp.js(f"""(() => {{ const g = document.querySelector("#vf [data-capteur='{cle}']"); if (!g) return null;
      const b = g.querySelector('rect'); return [getComputedStyle(b).fill, g.querySelector('title').textContent,
      b.style.transition, g.style.opacity]; }})()""")


def opacites(m, cle, secondes):
    """Valeurs distinctes de l'opacite de la pastille cle, relevees toutes les 50 ms pendant 'secondes' (dans la page)."""
    return sorted(m.cdp.js("new Promise(r => { const g = document.querySelector(\"#vf [data-capteur='" + cle + "']\"); const s = new Set();"
                           " const n = setInterval(() => s.add(g.style.opacity), 50);"
                           f" setTimeout(() => {{ clearInterval(n); r([...s]); }}, {int(secondes * 1000)}); }})"))


VERT_RGB, ROUGE_RGB, GRIS_RGB = "rgb(60, 176, 74)", "rgb(224, 69, 58)", "rgb(138, 143, 148)"


def vrai(v):
    """Resultat d'attend() : True seulement si l'expression a rendu true (une exception JS rend un dict, vrai pour bool())."""
    return v is True


def couleurs(fo, ff):
    """Expression JS : les deux pastilles ont fini leur fondu sur les couleurs fo (ouverture) et ff (fermeture)."""
    return ("(() => { const c = k => { const b = document.querySelector(\"#vf [data-capteur='\" + k + \"'] rect\");"
            f" return b && getComputedStyle(b).fill; }}; return c('ouverture') === '{fo}' && c('fermeture') === '{ff}'; }})()")


def debut_clignotement(m, cle, delai_ms):
    """Ms entre l'appel et la premiere opacite 0.25 de la pastille cle (mesure dans la page, toutes les 20 ms) ; None sinon."""
    return m.cdp.js("new Promise(r => { const g = document.querySelector(\"#vf [data-capteur='" + cle + "']\"), t0 = performance.now();"
                    " const n = setInterval(() => { const dt = performance.now() - t0;"
                    " if (g.style.opacity === '0.25') { clearInterval(n); r(Math.round(dt)); }"
                    f" else if (dt > {delai_ms}) {{ clearInterval(n); r(null); }} }}, 20); }})")


def sonde_p4(m, capture):
    Carte.capteurs, Carte.req_capteurs = {"1": {"ouverture": "OFF", "fermeture": "ON"}}, 0
    verifie(bool(m.ouvre("p4")), True, "p4 : page chargée")
    verifie(vrai(attend(m.cdp, couleurs(ROUGE_RGB, VERT_RGB), 6)), True, "p4 : pastilles lues (ouverture OFF rouge, fermeture ON verte)")
    verifie(m.cdp.js("[...document.querySelectorAll('#vf [data-decor]')].map(g => g.getAttribute('data-decor'))"),
            ["chevrefeuille", "porte", "pergola"], "p4 : décor posé : chevrefeuille, porte, pergola")
    verifie(m.cdp.js("document.querySelector('#vf svg').getAttribute('viewBox')"), "0 0 420 200", "p4 : dessin élargi pour le décor")
    o, f = pastille(m, "ouverture"), pastille(m, "fermeture")
    verifie([o[1], f[1]], [FINS["ouverture"] + " : contact ouvert", FINS["fermeture"] + " : contact fermé"],
            "p4 : titres « nom : contact ouvert|fermé »")
    verifie("fill" in o[2] and "0.3s" in o[2], True, "p4 : fondu CSS du remplissage (fill 0.3s)")
    verifie(m.cdp.js("(() => { const a = document.querySelector(\"#vf [data-capteur='ouverture'] rect\").getBoundingClientRect(),"
                     " b = document.querySelector(\"#vf [data-capteur='fermeture'] rect\").getBoundingClientRect(),"
                     " r = document.querySelector(\"#vf g[data-id='1'] rect\").getBoundingClientRect(); return [a.top < b.top, a.left > r.right - 1]; })()"),
            [True, True], "p4 : ouverture en haut, fermeture en bas, sur le rail droit du rideau")
    verifie(Carte.req_capteurs >= 1, True, "p4 : /volets?f=capteurs lu")
    if capture:
        m.cdp.capture(str(Path(capture) / "facade_p4_decor_capteurs.png"))
    Carte.capteurs = {"1": {"ouverture": "ON", "fermeture": "OFF"}}
    verifie(vrai(attend(m.cdp, couleurs(VERT_RGB, ROUGE_RGB), 6)), True, "p4 : états inversés : les couleurs suivent")
    Carte.capteurs = {"1": {"ouverture": "ON"}}
    verifie(vrai(attend(m.cdp, couleurs(VERT_RGB, GRIS_RGB), 6)) and pastille(m, "fermeture")[1], FINS["fermeture"] + " : contact inconnu",
            "p4 : état absent de la réponse : pastille grise « contact inconnu »")
    Carte.capteurs = None
    verifie(vrai(attend(m.cdp, couleurs(GRIS_RGB, GRIS_RGB), 6)), True, "p4 : la route échoue (500) : les deux pastilles grises")
    # Incoherence : rideau ouvert a 100 % (curseur 0, inverse 1) sans contact d'ouverture : clignote au-dela de 6 s, pas avant
    Carte.capteurs = {"1": {"ouverture": "OFF", "fermeture": "OFF"}}
    verifie(vrai(attend(m.cdp, couleurs(ROUGE_RGB, ROUGE_RGB), 6)), True, "p4 : deux contacts ouverts, rideau à mi-course : rouges")
    pose(m, 1, 0)
    dt = debut_clignotement(m, "ouverture", 9000)
    # mesure lancee ~0,2 s apres pose() (aller-retour CDP) : borne basse a 5,5 s
    verifie(dt is not None and 5500 < dt < 8000, True, f"p4 : ouvert à 100 % sans contact : clignote après plus de 6 s ({dt} ms)")
    vus = opacites(m, "ouverture", 1.5)
    verifie([x in vus for x in ("1", "0.25")] + [opacites(m, "fermeture", 0.5)], [True, True, [""]],
            "p4 : la pastille d'ouverture clignote (opacités 1 et 0.25), pas celle de fermeture")
    if capture:
        m.cdp.capture(str(Path(capture) / "facade_p4_incoherence.png"))
    Carte.capteurs = {"1": {"ouverture": "ON", "fermeture": "OFF"}}
    verifie(vrai(attend(m.cdp, "document.querySelector(\"#vf [data-capteur='ouverture']\").style.opacity === ''", 6)), True,
            "p4 : contact d'ouverture revenu : le clignotement s'arrête")
    verifie(opacites(m, "ouverture", 1.0), [""], "p4 : plus de clignotement ensuite")


def sonde_rideau_capteurs(m, capture):
    Carte.position, Carte.max_simultanees, Carte.requetes = {"ouverture": 100, "muet": False, "capteurs": {"ouverture": "ON", "fermeture": "OFF"}}, 0, 0
    Carte.capteurs = {"1": {"ouverture": "OFF", "fermeture": "OFF"}}
    verifie(bool(m.ouvre("rideauc")), True, "rideau + capteurs : page chargée")
    verifie(vrai(attend(m.cdp, couleurs(VERT_RGB, ROUGE_RGB), 6)), True, "rideau + capteurs : états lus dans la réponse de la source (clé « capteurs »)")
    Carte.req_capteurs = 0                       # requete du scenario precedent encore en vol a la navigation : ne compte pas
    verifie([pastille(m, "ouverture")[1], pastille(m, "fermeture")[1]], ["Capteur Ouverture : contact fermé", "Capteur Fermeture : contact ouvert"],
            "rideau + capteurs : titres")
    Carte.position = {"ouverture": 0, "muet": False, "capteurs": {"ouverture": "OFF", "fermeture": "ON"}}
    verifie(vrai(attend(m.cdp, couleurs(ROUGE_RGB, VERT_RGB), 6)), True, "rideau + capteurs : rideau fermé, les pastilles suivent")
    verifie(Carte.req_capteurs, 0, "rideau + capteurs : aucune requête à /volets?f=capteurs (une seule requête par rafraîchissement)")
    Carte.position = {"ouverture": 50, "muet": True}
    verifie(vrai(attend(m.cdp, couleurs(GRIS_RGB, GRIS_RGB), 6)), True, "rideau + capteurs : source muette sans capteurs : gris")
    Carte.position = {"ouverture": 100, "muet": False, "capteurs": {"ouverture": "OFF", "fermeture": "OFF"}}
    verifie(vrai(attend(m.cdp, couleurs(ROUGE_RGB, ROUGE_RGB), 6)), True, "rideau + capteurs : deux contacts ouverts lus")
    dt = debut_clignotement(m, "ouverture", 10000)
    verifie(dt is not None, True, f"rideau + capteurs : ouvert à 100 % sans contact d'ouverture : clignote ({dt} ms)")
    if capture:
        m.cdp.capture(str(Path(capture) / "facade_rideau_capteurs.png"))


def voyant(m):
    """[remplissage calcule du voyant de la camera, halo affiche, titre]."""
    return m.cdp.js("(() => { const g = document.querySelector('#vf [data-camera]'); if (!g) return null; const c = g.querySelectorAll('circle');"
                    " return [getComputedStyle(c[2]).fill, getComputedStyle(c[1]).display !== 'none', g.querySelector('title').textContent]; })()")


def attend_post(n, delai):
    limite = time.monotonic() + delai
    while time.monotonic() < limite and len(Carte.posts) < n:
        time.sleep(0.05)
    return len(Carte.posts)


GRIS_CAMERA = "rgb(119, 119, 119)"


def sonde_maison(m, capture):
    Carte.capteurs, Carte.posts = {"camera": "OFF"}, []
    verifie(bool(m.ouvre("maison")), True, "maison : page chargée")
    verifie(vrai(attend(m.cdp, "!!(document.querySelector('#vf [data-decor=maison]') && document.querySelector('#vf [data-camera]'))", 5)), True,
            "maison : toit de la maison et caméra dessinés")
    verifie(m.cdp.js("document.querySelector('#vf svg').getAttribute('viewBox')"), "0 0 400 214", "maison : viewBox 400 x 214")
    verifie(vrai(attend(m.cdp, "document.querySelector('#vf [data-camera] title').textContent.indexOf('éteinte') > 0", 6)), True, "maison : caméra OFF lue")
    verifie(voyant(m), [GRIS_CAMERA, False, "Caméra de façade : éteinte (clic pour allumer)"], "maison : caméra éteinte : voyant gris, sans halo")
    verifie(vrai(attend(m.cdp, "document.querySelector(\"#vf svg g[data-id='2']\").getAttribute('data-ouverture') === '40'", 5)), True,
            "maison : volet de la cuisine animé comme avant (40 %)")
    verifie(m.cdp.js("(() => { const t = [...document.querySelectorAll('#vf svg text')].find(x => /°$/.test(x.textContent)); return t && t.textContent; })()"),
            "?°", "maison : rapporteur sans balise d'angle : « ?° »")
    balise(m, "47,0", "")
    verifie(vrai(attend(m.cdp, "[...document.querySelectorAll('#vf svg text')].some(x => x.textContent === '47°')", 5)), True,
            "maison : rapporteur suit la balise data-vi (47,0 -> 47°)")
    Carte.capteurs = {"camera": "ON"}
    verifie(vrai(attend(m.cdp, "document.querySelector('#vf [data-camera] title').textContent.indexOf('allumée') > 0", 6)), True, "maison : caméra ON lue")
    verifie(vrai(attend(m.cdp, "getComputedStyle(document.querySelectorAll('#vf [data-camera] circle')[2]).fill === '" + VERT_RGB + "'", 3)), True,
            "maison : caméra allumée : voyant vert")
    verifie(voyant(m), [VERT_RGB, True, "Caméra de façade : allumée (clic pour éteindre)"], "maison : halo affiché, titre « clic pour éteindre »")
    if capture:
        m.cdp.capture(str(Path(capture) / "facade_maison_camera.png"))
    m.cdp.js("window.confirm = () => false; document.querySelector('#vf [data-camera]').dispatchEvent(new MouseEvent('click', {bubbles: true})); 1")
    verifie(attend_post(1, 1.5), 0, "maison : clic refusé à la confirmation : aucun POST")
    m.cdp.js("window.confirm = q => (window.question = q, true); document.querySelector('#vf [data-camera]').dispatchEvent(new MouseEvent('click', {bubbles: true})); 1")
    verifie(attend_post(1, 5), 1, "maison : clic confirmé : un POST /volets")
    verifie([Carte.posts[0] if Carte.posts else None, m.cdp.js("window.question")], [{"action": "camera", "etat": "OFF"}, "Éteindre : Caméra de façade ?"],
            "maison : caméra allumée -> action=camera, etat=OFF, question « Éteindre »")
    verifie(vrai(attend(m.cdp, "document.querySelector('#vf [data-camera] title').textContent.indexOf('éteinte') > 0", 6)), True,
            "maison : état relu après la commande : éteinte")
    Carte.capteurs = None
    verifie(vrai(attend(m.cdp, "document.querySelector('#vf [data-camera] title').textContent.indexOf('état inconnu') > 0", 6)), True,
            "maison : la route échoue : « état inconnu », voyant gris")


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
        sonde_rideau(m, args.capture)
        sonde_p4(m, args.capture)
        sonde_rideau_capteurs(m, args.capture)
        sonde_maison(m, args.capture)
        verifie(bool(m.ouvre("sans")), True, "sans curseur : page chargée")
        time.sleep(0.3)
        verifie(m.cdp.js("[document.getElementById('vf').childElementCount, document.querySelectorAll('svg').length,"
                         " typeof window.Volets.demarre]"), [0, 0, "function"], "aucun s271 : rien n'est dessiné")
        verifie([x for x in m.cdp.erreurs() if "favicon.ico" not in x and PANNE not in x and not (("rideau?f=position" in x or "volets?f=capteurs" in x) and "500" in x)],
                [], "aucune erreur dans la console (hors le 500 voulu du rideau)")
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
