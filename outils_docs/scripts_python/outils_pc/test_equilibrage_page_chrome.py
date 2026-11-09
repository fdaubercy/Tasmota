"""Sonde Chrome de la page d'equilibrage de la carte des debits (plan tasks/plans/equilibrage-par-la-carte.md, A4).

UTILISATION (a la main ; aucun pio, aucune carte ; Chrome tourne ~30 s)
    %USERPROFILE%\\.platformio\\penv\\Scripts\\python.exe outils_docs/scripts_python/outils_pc/test_equilibrage_page_chrome.py
        [--capture DOSSIER]
Code de sortie 0 = vert. Client DevTools repris de test_build_page_chrome.py.

Montage : un petit serveur HTTP local joue la carte. /equilibrage assemble la page comme
data/bureau/tasmota32s3-serveur-debits-pac/equilibragePage.be::equilibragePage_envoiePage (doctype, charset, viewport,
window.CARTE echappe '</', puis le fichier du depot) ; /equilibrage?f=debits rend des debits qui changent a chaque
lecture (voie 2 muette, voie 4 imprecise, voie 3 sans mesure). /seul sert le fichier SANS window.CARTE (artifact,
fichier local) : la page doit rester en saisie a la main. Polices Google bloquees : la sonde ne sort pas du PC.
Cas contraires : la meme page sans CARTE (zone de la carte cachee, aucune lecture), et des mesures en erreur 500
(« Lecture impossible »). Estimateur : type fonte (case « Elements » seule visible) et bouton « Reporter ».
Non teste : le mode sombre et les couleurs.
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

PAGE = RACINE / "data/bureau/tasmota32s3-serveur-debits-pac/equilibrage.html"
CODE = RACINE / "data/bureau/tasmota32s3-serveur-debits-pac/equilibrage_carte.js"
RELAIS = "location.replace('/equilibrage?r=1')"      # comme equilibragePage.be::equilibragePage_envoieRelais (favori sans Referer)
TETE = "<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
CARTE = {"noms": ["Salon </script>", "Cuisine", "Chambre", "Bureau", "Bain", "Entrée"], "fenetre": 2, "nom": "SERVEUR-DEBITS-PAC"}
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)
    return ok


class Carte(BaseHTTPRequestHandler):
    lectures = 0
    en_panne = False
    relais = 0                   # pages de relais servies (requete sans Referer)
    reglages = {"r1-type": "f3", "r1-e": "8", "p1": "700"}     # reglages gardes sur la carte

    def log_message(self, format, *args):
        pass

    def envoie(self, code, corps, mime):
        corps = corps.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
        fichier = PAGE.read_text(encoding="utf-8")
        if url.path == "/equilibrage" and q.get("f") == "debits":
            Carte.lectures += 1
            if Carte.en_panne:
                return self.envoie(500, "panne", "text/plain")
            n = Carte.lectures
            self.envoie(200, json.dumps({"debits": [2.5 + n, 0.0, None, 0.4, 3.0, 4.1], "total": 10.0 + n, "noms": CARTE["noms"],
                                         "muets": [False, True, False, False, False, False],
                                         "imprecis": [False, False, False, True, False, False], "fenetre": 2, "age_s": 3}),
                        "application/json")
        elif url.path == "/equilibrage" and q.get("f") == "reglages":
            self.envoie(200, json.dumps(Carte.reglages), "application/json")
        elif url.path == "/equilibrage" and not self.headers.get("Referer"):
            Carte.relais += 1
            self.envoie(200, "<!doctype html><meta charset='utf-8'><script>" + RELAIS + "</script>", "text/html")
        elif url.path == "/equilibrage":
            self.envoie(200, TETE + "<script>window.CARTE=" + json.dumps(CARTE).replace("</", "<\\/") + ";</script>" + fichier
                        + "<script>" + CODE.read_text(encoding="utf-8") + "</script>", "text/html")
        elif url.path == "/seul":
            self.envoie(200, TETE + fichier, "text/html")
        else:
            self.envoie(404, "inconnu", "text/plain")

    def do_POST(self):
        corps = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
        Carte.reglages = json.loads(urllib.parse.parse_qs(corps)["reglages"][0])
        self.envoie(200, '{"ok": true}', "application/json")


class Serveur(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        if not isinstance(sys.exc_info()[1], ConnectionError):
            super().handle_error(request, client_address)


class Montage:
    def __init__(self):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_equilibrage_"))
        self.port = port_libre()
        self.http = Serveur(("127.0.0.1", self.port), Carte)
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        chrome = next((c for c in CHROMES if c.is_file()), None)
        if chrome is None:
            raise FileNotFoundError("chrome.exe introuvable (Program Files, LOCALAPPDATA)")
        port_cdp = port_libre()
        self.chrome = subprocess.Popen([str(chrome), "--headless=new", f"--remote-debugging-port={port_cdp}",
                                        "--remote-allow-origins=*", f"--user-data-dir={self.t / 'profil'}",
                                        "--no-first-run", "--no-default-browser-check", "--disable-extensions", "about:blank"],
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
        for domaine in ("Runtime.enable", "Log.enable", "Page.enable", "Network.enable"):
            self.cdp.appel(domaine)
        self.cdp.appel("Network.setBlockedURLs", urls=["*fonts.googleapis.com*", "*fonts.gstatic.com*"])

    def ouvre(self, chemin, largeur=360):
        self.cdp.appel("Emulation.setDeviceMetricsOverride", width=largeur, height=900, deviceScaleFactor=1, mobile=largeur < 600)
        self.cdp.appel("Page.navigate", url=f"http://127.0.0.1:{self.port}{chemin}")

    def ferme(self):
        tue_arbre(self.chrome)
        self.http.shutdown()
        time.sleep(0.5)
        shutil.rmtree(self.t, ignore_errors=True)


JS_ETAT = """(() => {
  const v = id => document.getElementById(id).value, lab = id => document.querySelector(`label[for="${id}"]`).firstChild.textContent;
  const lignes = [...document.querySelectorAll('#resultat tbody tr')].map(t => t.children[0].textContent + ' | ' + t.children[3].textContent);
  return {zone: !document.getElementById('carte-zone').hidden, m: [1,2,3,4,5,6].map(k => v('m' + k)), pac: v('pac'),
          labelM1: lab('m1'), legende1: document.querySelector('#radiateurs legend').textContent, lignes,
          cibleTotale: (document.querySelector('#resultat tfoot td:nth-child(3)') || {}).textContent,
          etat: document.getElementById('carte-etat').textContent,
          pageLarge: document.documentElement.scrollWidth, fenetre: window.innerWidth};
})()"""


def sonde(m, capture):
    print("=== page servie par la carte (360 px) ===", flush=True)
    m.ouvre("/equilibrage")
    verifie(attend(m.cdp, "document.getElementById('m1') && document.getElementById('m1').value === '3,50'", 10), True,
            "lecture faite au chargement : départ 1 = 3,50 (1re lecture)")
    e = m.cdp.js(JS_ETAT)
    verifie(Carte.relais, 1, "ouverture sans Referer (favori) : page de relais, puis la page")
    verifie(e["zone"], True, "zone de la carte visible (bouton, case, état)")
    g = m.cdp.js("['r1-type', 'r1-e', 'p1'].map(id => document.getElementById(id).value)")
    verifie(g, ["f3", "8", "700"], "réglages gardés sur la carte relus au chargement (type, éléments, puissance)")
    verifie(e["m"], ["3,50", "0,00", "", "0,40", "3,00", "4,10"], "6 débits remplis, voie sans mesure vide")
    verifie(e["labelM1"], "Départ 1 (Salon </script>) : débit mesuré (L/min)", "nom du départ repris, texte brut (pas de HTML)")
    verifie(e["legende1"], "Radiateur 1 — Salon </script>", "nom repris dans l'estimateur")
    verifie(e["lignes"][0], "1 Salon </script> | 3,5", "tableau : nom échappé (affiché tel quel)")
    verifie(["muet ?" in e["lignes"][1], "imprécis" in e["lignes"][3]], [True, True], "départ 2 « muet ? », départ 4 « imprécis »")
    verifie((e["pac"], e["cibleTotale"]), ("", "11,0 L/min"), "PAC vide : cible totale = total mesuré (11,0 L/min)")
    verifie(e["etat"].startswith("Lu à ") and "il y a 3 s" in e["etat"] and "départ 2 muet ?" in e["etat"], True,
            f"état de la lecture ({e['etat']!r})")
    verifie(e["pageLarge"] <= e["fenetre"], True, f"360 px : page {e['pageLarge']} px <= fenêtre {e['fenetre']} px")
    if capture:
        m.cdp.capture(str(Path(capture) / "equilibrage_carte_360.png"))

    avant = Carte.lectures
    m.cdp.js("document.getElementById('suivre').click(); 1")
    time.sleep(4.6)
    verifie(Carte.lectures - avant >= 3, True, f"suivi en direct : lecture au clic puis toutes les 2 s ({Carte.lectures - avant} lectures)")
    verifie(m.cdp.js("document.getElementById('m1').value") == f"{2.5 + Carte.lectures:.2f}".replace(".", ","), True,
            "suivi en direct : valeurs mises à jour")
    sch = m.cdp.js("[document.getElementById('schema-texte').textContent,"
                   " document.querySelector('#schema text[y=\"170\"]').textContent, document.getElementById('m1').value]")
    verifie(sch[0].startswith("Débits réels") and sch[1] == f"{float(sch[2].replace(',', '.')):.1f}".replace(".", ","), True,
            f"suivi en direct : schéma sur les débits réels ({sch!r})")
    m.cdp.js("Object.defineProperty(document, 'hidden', {configurable: true, get: () => true});"
             " document.dispatchEvent(new Event('visibilitychange')); 1")
    avant = Carte.lectures
    time.sleep(4.5)
    verifie(Carte.lectures, avant, "onglet caché : aucune lecture")
    m.cdp.js("delete document.hidden; document.dispatchEvent(new Event('visibilitychange')); 1")
    time.sleep(1)
    verifie(Carte.lectures > avant, True, "onglet de nouveau visible : lecture reprise")
    m.cdp.js("document.getElementById('suivre').click(); 1")
    verifie(m.cdp.js("document.getElementById('schema-texte').textContent").startswith("Débits réels"), False,
            "suivi arrêté : retour à l'illustration de l'étape")
    erreurs =[x for x in m.cdp.erreurs() if "fonts.g" not in x and "favicon" not in x]
    verifie(erreurs, [], "mode carte : aucune erreur dans la console (hors polices bloquées)")

    # Estimateur : radiateur 1 en fonte 4 colonnes, 600 mm, 10 éléments = 90 W x 10 ; « Reporter » remplit le calculateur
    e = m.cdp.js("""(() => { const t = document.getElementById('r1-type'); t.value = 'f4'; t.dispatchEvent(new Event('input'));
      const n = document.getElementById('r1-e'); n.value = '10'; n.dispatchEvent(new Event('input'));
      const vis = id => !document.querySelector(`label[for="${id}"]`).hidden;
      const r = {elements: vis('r1-e'), longueur: vis('r1-l'), hauteur: vis('r1-h'), puissance: vis('r1-p')};
      document.getElementById('reporter').click();
      r.p1 = document.getElementById('p1').value; r.p2 = document.getElementById('p2').value;
      r.cible1 = document.querySelector('#resultat tbody tr td:nth-child(3)').textContent;
      r.q = document.querySelector('#resultat tfoot td:nth-child(3)').textContent; return r; })()""")
    verifie([e["elements"], e["hauteur"], e["longueur"], e["puissance"]], [True, True, False, False],
            "estimateur : fonte -> « Éléments » et hauteur visibles, longueur et puissance cachées")
    verifie((e["p1"], e["p2"]), ("900", "1320"), "« Reporter » : puissances catalogue dans le calculateur (900 W, 1 320 W)")
    q = float(e["q"].split()[0].replace(",", "."))      # PAC vide : total mesuré à cet instant
    attendu = f"{q * 900 / 9975:.1f}".replace(".", ",") + " L/min"     # 900 + 1320 + 1650 + 1815 + 1980 + 2310 W
    m.cdp.js("[...document.querySelectorAll('#carte-zone button')].find(b => b.textContent.startsWith('Garder')).click(); 1")
    attend(m.cdp, "document.getElementById('carte-etat').textContent.includes('gardés sur la carte')", 5)
    verifie((Carte.reglages.get("r1-type"), Carte.reglages.get("r1-e"), Carte.reglages.get("p1"), len(Carte.reglages)),
            ("f4", "10", "900", 46), "« Garder les puissances sur la carte » : 46 champs envoyés (radiateur 1 compris)")
    verifie(e["cible1"], attendu, f"« Reporter » : calcul refait (cible du départ 1 = {q} x 900 / 9 975 W)")

    Carte.en_panne = True
    m.cdp.js("document.getElementById('lire').click(); 1")
    verifie(attend(m.cdp, "document.getElementById('carte-etat').textContent.startsWith('Lecture impossible')", 5), True,
            "mesures en erreur 500 : « Lecture impossible », valeurs gardées")
    Carte.en_panne = False

    print("=== même fichier sans window.CARTE (artifact, fichier local) ===", flush=True)
    m.ouvre("/seul")
    attend(m.cdp, "document.getElementById('m1') && document.getElementById('m1').value !== ''", 10)
    avant = Carte.lectures
    time.sleep(1.5)
    e = m.cdp.js(JS_ETAT)
    verifie((e["zone"], e["m"][0], e["pac"]), (False, "4.9", "20"), "hors carte : zone cachée, exemple du guide, PAC 20")
    verifie(Carte.lectures, avant, "hors carte : aucune lecture de /equilibrage?f=debits")
    verifie(e["pageLarge"] <= e["fenetre"], True, f"hors carte, 360 px : page {e['pageLarge']} px <= fenêtre {e['fenetre']} px")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de la page d'équilibrage.")
    options.add_argument("--capture", metavar="DOSSIER")
    args = options.parse_args()
    if args.capture:
        Path(args.capture).mkdir(parents=True, exist_ok=True)
    m = None
    try:
        m = Montage()
        sonde(m, args.capture)
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
