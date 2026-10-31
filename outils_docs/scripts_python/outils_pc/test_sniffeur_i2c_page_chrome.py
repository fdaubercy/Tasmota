"""Sonde Chrome de la page du sniffeur I2C (sniffeur_i2c_web.PAGE) : la page s'execute-t-elle ?

UTILISATION (a la main ; aucun pio, aucun port COM, aucune carte ; Chrome tourne ~30 s)
    %USERPROFILE%\\.platformio\\penv\\Scripts\\python.exe outils_docs/scripts_python/outils_pc/test_sniffeur_i2c_page_chrome.py
Code de sortie 0 = vert : la vraie page passe toutes les verifications ET le temoin (la meme page avec une
erreur JS volontaire au chargement) est detecte. Client DevTools repris de test_build_page_chrome.py.

Montage : le serveur du sniffeur dans un processus fils (mode --serveur), port serie FERME, un faux sniffeur
injecte des lignes toutes les 0,3 s (ADS1115, TCA9554/MCP23017 en 0x20, NACK) ; journal desactive ; le depot
n'est que LU (liste des cartes, persist de la carte choisie). Rien n'est envoye a une carte.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import types
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre, tue_arbre   # client DevTools stdlib

ECHECS = []
MARQUE_TEMOIN = "const flux = new EventSource"
INJECTION_TEMOIN = '$("bouton-qui-n-existe-pas").onclick = null;   // TEMOIN : TypeError au chargement\n'
CAVE = "data/cave/tasmota32s3-serveur-rly"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)
    return ok


def mode_serveur(port, temoin):
    from http.server import ThreadingHTTPServer
    import sniffeur_i2c as si
    import sniffeur_i2c_web
    from sniffeur_i2c_http import fabrique_gestionnaire
    if temoin:
        assert sniffeur_i2c_web.PAGE.count(MARQUE_TEMOIN) == 1, "marque du temoin introuvable dans la page"
        sniffeur_i2c_web.PAGE = sniffeur_i2c_web.PAGE.replace(MARQUE_TEMOIN, INJECTION_TEMOIN + MARQUE_TEMOIN)
    sn = si.Sniffeur(types.SimpleNamespace(historique=500, sans_journal=True, http=port, racine=None))
    http = ThreadingHTTPServer(("127.0.0.1", port), fabrique_gestionnaire(sn))

    def faux_sniffeur():
        sn.traite_lignes(["I v=1 puce=esp32s3 sda=4 scl=5 mode=ecoute ech=12",
                          "X t=1 a=48 rw=W d=01C383 nack=- fin=STOP f=99.6"])
        t = 2
        while True:
            t += 1
            sn.traite_lignes([f"X t={t} a=48 rw=W d=00 nack=- fin=RESTART f=99.6",
                              f"X t={t} a=48 rw=R d=7FFF nack=- fin=STOP f=99.6",
                              f"X t={t} a=20 rw=W d=0109 nack=- fin=STOP f=99.4",
                              f"X t={t} a=51 rw=W d=- nack=0 fin=STOP f=99.1"])
            time.sleep(0.3)

    threading.Thread(target=faux_sniffeur, daemon=True).start()
    http.serve_forever()


class Montage:
    def __init__(self):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_sniffeur_i2c_"))
        self.serveur = self.chrome = None

    def demarre(self, temoin):
        environ = dict(os.environ, OUTILS_TASMOTA_DOSSIER=str(self.t / "outils"), PYTHONIOENCODING="utf-8")
        self.port = port_libre()
        self.url = f"http://127.0.0.1:{self.port}/"
        commande = [sys.executable, "-u", str(Path(__file__).resolve()), "--serveur", str(self.port)] + (["--temoin"] if temoin else [])
        self.serveur = subprocess.Popen(commande, env=environ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self._attend_http(self.url + "cartes", 20)
        chrome = next((c for c in CHROMES if c.is_file()), None)
        if chrome is None:
            raise FileNotFoundError("chrome.exe introuvable (Program Files, LOCALAPPDATA)")
        self.port_cdp = port_libre()
        self.chrome = subprocess.Popen([str(chrome), "--headless=new", f"--remote-debugging-port={self.port_cdp}",
                                        "--remote-allow-origins=*", f"--user-data-dir={self.t / 'profil'}",
                                        "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                                        "--window-size=1280,1000", "about:blank"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cibles = self._attend_http(f"http://127.0.0.1:{self.port_cdp}/json/list", 20)
        page = next(c for c in json.loads(cibles) if c.get("type") == "page")
        self.cdp = Cdp(page["webSocketDebuggerUrl"])
        for domaine in ("Runtime.enable", "Log.enable", "Page.enable"):
            self.cdp.appel(domaine)

    @staticmethod
    def _attend_http(url, delai):
        limite = time.monotonic() + delai
        while time.monotonic() < limite:
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    return r.read().decode("utf-8")
            except OSError:
                time.sleep(0.2)
        raise TimeoutError(f"{url} ne repond pas")

    def ferme(self):
        tue_arbre(self.chrome)
        tue_arbre(self.serveur)


def clic(cdp, ident):
    return cdp.js(f"(function(){{var e=document.getElementById({json.dumps(ident)}); if(!e) return 'absent'; e.click(); return 'ok';}})()")


def nb_lignes(cdp):
    return cdp.js("document.getElementById('liste').childElementCount")


def sonde_page(m):
    cdp = m.cdp
    cdp.appel("Page.navigate", url=m.url)
    verifie(attend(cdp, "document.getElementById('etat').textContent.indexOf('esp32s3') >= 0", 15), True,
            "etat : identite du sniffeur affichee")
    verifie(attend(cdp, "document.getElementById('liste').textContent.indexOf('4095.9 mV') >= 0", 10), True,
            "fil : conversion ADS1115 decodee en mV")
    verifie(attend(cdp, "document.getElementById('stats').textContent.indexOf('0x48') >= 0", 10), True,
            "inventaire : adresse 0x48 listee")
    verifie(cdp.js("document.getElementById('liste').textContent.indexOf('MCP23017/TCA9554') >= 0"), True,
            "0x20 sans carte : ambigu, les deux puces nommees")
    cdp.js("var c=document.getElementById('nackSeuls'); c.checked=true; c.dispatchEvent(new Event('change')); 1")
    verifie(cdp.js("[...document.querySelectorAll('#liste .l.n-trame')].every(function(l){return l.textContent.indexOf('NACK@') >= 0;})"),
            True, "filtre « NACK seuls »")
    cdp.js("var c=document.getElementById('nackSeuls'); c.checked=false; c.dispatchEvent(new Event('change')); 1")
    clic(cdp, "pause")
    avant = nb_lignes(cdp)
    time.sleep(1.2)
    verifie(nb_lignes(cdp), avant, "pause : le fil ne bouge plus")
    clic(cdp, "pause")
    verifie(attend(cdp, f"document.getElementById('liste').childElementCount > {avant}", 5), True,
            "reprise : les lignes en attente arrivent")
    cdp.js(f"var s=document.getElementById('carte'); s.value={json.dumps(CAVE)}; s.dispatchEvent(new Event('change')); 1")
    verifie(attend(cdp, "[...document.querySelectorAll('#liste .l.n-trame')].slice(-4).some(function(l){"
                        "return l.textContent.indexOf('TCA9554 Sorties') >= 0;})", 10),
            True, "carte observee (cave S3) : 0x20 decode TCA9554")
    clic(cdp, "ongletEnvoi")
    verifie(cdp.js("!document.getElementById('vueEnvoi').classList.contains('cache')"), True, "onglet Envoi")
    verifie(attend(cdp, "document.getElementById('cTopic').value === 'cave/serveur-rly-cave-v2'", 10), True,
            "topic MQTT de la carte propose")
    cdp.js("var s=document.getElementById('cTransport'); s.value='mqtt'; s.dispatchEvent(new Event('change')); 1")
    verifie(cdp.js("[document.getElementById('cIp').disabled, document.getElementById('cTopic').disabled]"), [True, False],
            "voie MQTT : IP grisee, topic saisissable")
    clic(cdp, "cApercu")
    verifie(attend(cdp, "document.getElementById('cCommande').textContent.indexOf('Br (wire1.detect(0x') === 0", 10), True,
            "apercu de la commande Br (voie MQTT)")
    clic(cdp, "mApercu")
    verifie(attend(cdp, "document.getElementById('mResultat').textContent.indexOf('debranche') >= 0", 10), True,
            "sniffeur maitre sans « composant isole » : refus affiche")
    clic(cdp, "ongletAide")
    verifie(cdp.js("!document.getElementById('vueAide').classList.contains('cache') && "
                   "document.getElementById('vueAide').textContent.indexOf('Brancher le sniffeur') >= 0"), True, "onglet Aide")
    # attendus : pas de favicon, et le refus 400 provoque ci-dessus (maitre sans « composant isole »)
    attendues = ("favicon.ico", "status of 400 (Bad Request) http://127.0.0.1:%d/ordre" % m.port)
    verifie([e for e in cdp.erreurs() if not any(a in e for a in attendues)], [], "aucune erreur JS pendant toute la sonde")


def sonde_temoin(m):
    m.cdp.appel("Page.navigate", url=m.url)
    time.sleep(3)
    verifie(len(m.cdp.erreurs()) > 0, True, "TEMOIN : l'erreur JS volontaire est detectee")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de la page du sniffeur I2C.")
    options.add_argument("--sans-temoin", action="store_true")
    options.add_argument("--serveur", type=int, metavar="PORT", help=argparse.SUPPRESS)
    options.add_argument("--temoin", action="store_true", help=argparse.SUPPRESS)
    args = options.parse_args()
    if args.serveur:
        return mode_serveur(args.serveur, args.temoin)
    for temoin in ([False] if args.sans_temoin else [False, True]):
        print(f"\n=== {'TEMOIN (erreur JS volontaire)' if temoin else 'page reelle'} ===", flush=True)
        m = None
        try:
            m = Montage()
            m.demarre(temoin)
            sonde_temoin(m) if temoin else sonde_page(m)
        except FileNotFoundError as erreur:
            print(f"BLOQUE : {erreur}")
            return 3
        except Exception as erreur:
            verifie(repr(erreur), "pas d'exception de la sonde", "sonde : deroulement")
        finally:
            if m:
                m.ferme()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
