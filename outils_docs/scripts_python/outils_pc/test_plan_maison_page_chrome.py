"""Sonde Chrome de la page « Plan de la maison » : vues, filtres, survol, clic, fiche, bouton de test, en-tete fixe, aucune erreur JS.

UTILISATION (a la main ; aucun pio, aucune carte ; Chrome tourne ~15 s)
    python outils_docs/scripts_python/outils_pc/test_plan_maison_page_chrome.py
Code de sortie 0 = vert. Serveur reel (plan_maison_web) dans ce processus, 127.0.0.1, port libre ; Chrome headless arrete a la fin.
Le bouton « Tester les cartes » est essaye avec un fetch remplace : aucune requete ne part vers une carte.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import acces_web                                                                # noqa: E402
import plan_maison_web as web                                                   # noqa: E402
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre, tue_arbre   # noqa: E402

ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def attente_http(url, delai):
    limite = time.monotonic() + delai
    while time.monotonic() < limite:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                return r.read().decode("utf-8")
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(url)


def DV(n):
    """Selecteur JS litteral du texte de debit n."""
    return json.dumps(".dv[data-d='%d']" % n)


def visible(cdp, sel):
    """Nombre d'elements du selecteur dont l'affichage calcule n'est pas none."""
    return cdp.js("[...document.querySelectorAll(" + json.dumps(sel) + ")].filter(function(e){return getComputedStyle(e).display!=='none'}).length")


def scenario(cdp, url):
    cdp.appel("Emulation.setDeviceMetricsOverride", width=1400, height=700, deviceScaleFactor=1, mobile=False)
    cdp.appel("Page.addScriptToEvaluateOnNewDocument", source="window.__e=[];window.addEventListener('error',function(e){__e.push(e.message)})")
    cdp.appel("Page.navigate", url=url)
    verifie(bool(attend(cdp, "document.querySelectorAll('svg.plan g.carte').length > 0", 15)), True, "page chargee")
    verifie(cdp.js("document.title"), "Plan de la maison", "titre")
    verifie(cdp.js("document.querySelectorAll('svg.plan g.carte:not(.apn):not(.chn)').length"), 18, "plan : une pastille par carte (18)")
    verifie(cdp.js("document.body.className"), "v-plan", "vue plan au depart")
    verifie((visible(cdp, "svg.plan"), visible(cdp, "svg.reseau"), visible(cdp, ".wl"), visible(cdp, ".chn")), (1, 0, 0, 0), "plan : seul le plan est visible")

    # vues
    cdp.js("document.getElementById('b-reseau').click()")
    verifie((visible(cdp, "svg.plan"), visible(cdp, "svg.reseau")), (0, 1), "vue reseau : le schema remplace le plan")
    verifie(cdp.js("document.querySelectorAll('svg.reseau g.broker').length"), 1, "vue reseau : le broker MQTT est dessine")
    cdp.js("document.getElementById('b-wifi').click()")
    verifie((visible(cdp, "svg.plan"), visible(cdp, ".apn"), visible(cdp, ".lien.serie")), (1, 5, 0), "vue Wi-Fi : 5 appareils, liens ModBus masques")
    verifie(visible(cdp, ".wl.wre") >= 1, True, "vue Wi-Fi : rail Range Extender visible")
    verifie(visible(cdp, ".wl[data-type=wsec]"), 0, "vue Wi-Fi : reseaux de secours masques au depart")
    cdp.js("document.querySelector('input[data-type=wsec]').click()")
    verifie(visible(cdp, ".wl[data-type=wsec]") > 0, True, "vue Wi-Fi : case secours -> pointilles visibles")
    cdp.js("document.getElementById('b-chauffage').click()")
    verifie((visible(cdp, ".chn"), visible(cdp, ".chl") > 0, visible(cdp, ".apn")), (2, True, 0), "vue chauffage : PAC et nourrice, traits d'eau")
    cdp.js("document.getElementById('b-plan').click()")
    verifie(visible(cdp, ".chn") + visible(cdp, ".wl"), 0, "retour au plan : couches Wi-Fi et chauffage masquees")

    # filtres
    n = visible(cdp, ".lien.serie")
    verifie(n > 0, True, "filtre : des liens RS485 au depart")
    cdp.js("document.querySelector('input[data-type=serie]').click()")
    verifie(visible(cdp, ".lien.serie"), 0, "filtre : RS485 decoche -> liens masques")
    cdp.js("document.querySelector('input[data-type=serie]').click()")
    verifie(visible(cdp, ".lien.serie"), n, "filtre : RS485 recoche -> liens revenus")

    # maitre : marque RE, etiquette, survol, fiche
    p4 = "garage/tasmota32p4-serveur-modbus"
    sel = "svg.plan g.carte[data-id='" + p4 + "']"
    verifie(cdp.js("document.querySelector(" + json.dumps(sel + " .re") + ").textContent.indexOf('×3') > 0"), True, "maitre P4 : marque Range Extender x3")
    verifie(cdp.js("document.querySelectorAll('svg.plan .lien.serie text.lbl').length > 0"), True, "etiquette (id) au milieu d'un lien")
    cdp.js("document.querySelector(" + json.dumps(sel) + ").dispatchEvent(new MouseEvent('mouseenter'))")
    verifie(cdp.js("document.querySelectorAll('svg.plan g.carte.fade').length > 0 && !document.querySelector(" + json.dumps(sel) + ").classList.contains('fade')"),
            True, "survol du maitre : les autres cartes sont estompees, lui non")
    verifie(cdp.js("document.querySelectorAll('svg.plan g.carte:not(.fade):not(.apn):not(.chn)').length"), 4, "survol du maitre : lui et ses 3 esclaves restent visibles")
    cdp.js("document.querySelector(" + json.dumps(sel) + ").dispatchEvent(new MouseEvent('mouseleave'))")
    verifie(cdp.js("document.querySelectorAll('svg.plan g.carte.fade').length"), 0, "fin du survol : tout revient")
    cdp.js("document.querySelector(" + json.dumps(sel) + ").dispatchEvent(new MouseEvent('click',{bubbles:true}))")
    fiche = cdp.js("document.getElementById('fiche').textContent")
    verifie(("maître" in fiche, "ESP32-P4" in fiche, "Capteurs cuve" in fiche), (True, True, True), "clic : fiche du maitre (role, puce, esclaves)")
    verifie(cdp.js("document.querySelectorAll('svg.plan g.carte.sel').length"), 1, "clic : une carte selectionnee")
    cdp.js("document.querySelector(" + json.dumps(sel) + ").dispatchEvent(new MouseEvent('mouseleave'))")
    verifie(cdp.js("document.querySelectorAll('svg.plan g.carte.fade').length > 0"), True, "apres le survol, la selection reste mise en evidence")
    cdp.js("document.querySelector('svg.plan').dispatchEvent(new MouseEvent('click',{bubbles:true}))")
    verifie(cdp.js("document.querySelectorAll('svg.plan g.carte.fade, svg.plan g.carte.sel').length"), 0, "clic dans le vide : selection levee")

    # texte hostile : une fiche n'interprete jamais de balise
    cdp.js("F['" + p4 + "'].libelle='<img src=x onerror=window.__pwn=1>';document.querySelector(" + json.dumps(sel) + ").dispatchEvent(new MouseEvent('click',{bubbles:true}))")
    verifie(cdp.js("window.__pwn === undefined && document.querySelectorAll('#fiche img').length"), 0, "fiche : le texte hostile reste du texte")

    # icone de lien vers la page de la carte : ouvre la bonne adresse, ne selectionne pas la carte
    verifie(cdp.js("document.querySelector(" + json.dumps(sel + " a.lk") + ").getAttribute('href')"), "http://192.168.0.43/", "icone de lien : adresse de la carte du maitre")
    verifie(cdp.js("[...document.querySelectorAll('svg.plan g.carte[data-id$=cuve-modbus] a.lk')].map(function(a){return a.getAttribute('href')}).join()"),
            "http://192.168.0.43:8081/", "icone de lien : esclave derriere le NAPT = IP du maitre, port 8080 + id - 1")
    verifie(cdp.js("document.querySelectorAll('svg.plan g.carte:not(.apn):not(.chn):not([data-url]) a.lk').length"), 0, "icone de lien : absente d'une carte sans adresse")
    cdp.js("document.querySelector('svg.plan').dispatchEvent(new MouseEvent('click',{bubbles:true}))")
    cdp.js("var a=document.querySelector(" + json.dumps(sel + " a.lk") + ");a.addEventListener('click',function(e){e.preventDefault()});a.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}))")
    verifie(cdp.js("document.querySelectorAll('svg.plan g.carte.sel').length"), 0, "icone de lien : le clic n'ouvre pas la fiche de la carte")

    # debits en direct : lecture remplacee dans le serveur (aucun reseau), valeurs a cote des ronds, voies a signaler
    cdp.js("document.getElementById('b-chauffage').click()")
    verifie(cdp.js("document.querySelectorAll('.dv').length > 0 && [...document.querySelectorAll('.dv')].every(function(t){return t.textContent===''})"), True, "debits : aucune valeur avant le clic")
    verifie(cdp.js("getComputedStyle(document.getElementById('b-debits')).display !== 'none'"), True, "debits : bouton visible en vue chauffage")
    cdp.js("document.getElementById('b-debits').click()")
    verifie(bool(attend(cdp, "document.querySelector(" + DV(1) + ").textContent.length > 0", 10)), True, "debits : valeurs affichees apres le clic")
    verifie(cdp.js("document.querySelector(" + DV(1) + ").textContent"), "1,50 L/min", "debits : D1 formate")
    verifie(cdp.js("[document.querySelector(" + DV(3) + ").parentNode.querySelector('circle').classList.contains('mut'), document.querySelector(" + DV(4) + ").parentNode.querySelector('circle').classList.contains('imp')]"),
            [True, True], "debits : voie muette en rouge, voie imprecise en orange")
    verifie(cdp.js("document.getElementById('etat-debits').textContent.indexOf('total 5,90') > 0"), True, "debits : total dans la ligne d'etat")
    web.lit_url = lambda u: (_ for _ in ()).throw(OSError("timed out"))
    cdp.js("document.getElementById('b-debits').click()")
    verifie(bool(attend(cdp, "document.getElementById('etat-debits').textContent.indexOf('injoignable') >= 0", 10)), True, "debits : carte muette -> message d'erreur lisible")
    cdp.js("document.getElementById('b-plan').click()")
    verifie(cdp.js("getComputedStyle(document.getElementById('b-debits')).display"), "none", "debits : bouton masque hors vue chauffage")

    # bouton de test : fetch remplace, aucune requete vers une carte
    cdp.js("window.__appels=[];window.fetch=function(u){window.__appels.push(u);return u.indexOf('192.168.0.43')>0?Promise.resolve():Promise.reject(new Error('ko'))}")
    cdp.js("document.getElementById('b-test').click()")
    verifie(bool(attend(cdp, "document.querySelectorAll('svg.plan g.carte.test').length === 0 && document.querySelectorAll('svg.plan g.carte.ok').length > 0", 8)), True,
            "test des cartes : l'etat revient")
    verifie(cdp.js("document.querySelector(" + json.dumps(sel) + ").classList.contains('ok')"), True, "test des cartes : carte joignable en vert")
    verifie(cdp.js("document.querySelectorAll('svg.plan g.carte.ko').length > 0"), True, "test des cartes : cartes muettes en rouge")

    # en-tete fixe
    cdp.js("window.scrollTo(0, 400)")
    time.sleep(0.4)
    verifie(cdp.js("getComputedStyle(document.querySelector('.haut')).position"), "sticky", "en-tete : position collante")
    verifie(cdp.js("document.querySelector('.haut').getBoundingClientRect().top < 40"), True, "en-tete : reste en haut apres defilement")

    verifie(cdp.js("window.__e.length"), 0, "aucune erreur JavaScript")


def main():
    t = Path(tempfile.mkdtemp(prefix="sonde_plan_maison_"))
    chrome = serveur = None
    try:
        port = port_libre()
        acces = acces_web.Acces(port, True, "Plan de la maison")
        serveur = ThreadingHTTPServer(("127.0.0.1", port), web.fabrique_gestionnaire(acces))
        serveur.daemon_threads = True
        threading.Thread(target=serveur.serve_forever, daemon=True).start()
        exe = next((c for c in CHROMES if c.is_file()), None)
        if exe is None:
            print("KO   chrome.exe introuvable")
            return 1
        pcdp = port_libre()
        chrome = subprocess.Popen([str(exe), "--headless=new", f"--remote-debugging-port={pcdp}", "--remote-allow-origins=*", f"--user-data-dir={t / 'profil'}",
                                   "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--window-size=1400,700", "about:blank"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cible = next(c for c in json.loads(attente_http(f"http://127.0.0.1:{pcdp}/json/list", 20)) if c.get("type") == "page")
        cdp = Cdp(cible["webSocketDebuggerUrl"])
        for d in ("Runtime.enable", "Page.enable"):
            cdp.appel(d)
        web.lit_url = lambda u: json.dumps({"StatusSNS": {"Time": "2026-11-15T20:00:00", "DEBITS": {"D1": 1.5, "D2": 2.0, "D3": None, "D4": 0.4, "D5": 1.1, "D6": 0.9,
                                                                                                    "Total": 5.9, "Imprecis": [4], "Muets": [3]}}})
        scenario(cdp, f"http://127.0.0.1:{port}/")
    finally:
        tue_arbre(chrome)
        cmd = ("$p = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'chrome.exe' -and $_.CommandLine -like '*" + t.name
               + "*' }); $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; $p.Count")
        for _ in range(8):
            if subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True).stdout.strip() == "0":
                break
            time.sleep(0.7)
        if serveur:
            serveur.shutdown()
            serveur.server_close()
        shutil.rmtree(t, ignore_errors=True)
    print(f"\n{len(ECHECS)} echec(s)")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
