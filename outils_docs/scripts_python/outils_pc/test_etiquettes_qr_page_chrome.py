"""Sonde Chrome de la page « Etiquettes QR code » (etiquettes_qr_page.py, plan A4).

UTILISATION (a la main ; Python de PlatformIO)
    python outils_docs/scripts_python/outils_pc/test_etiquettes_qr_page_chrome.py [--capture DOSSIER]
Code de sortie 0 = vert, 3 = Chrome introuvable.

Serveur dans un fil devant la copie temporaire du banc des routes (test_etiquettes_qr_web.Banc : le vrai depot n'est jamais
ecrit), Chrome headless (profil « sonde_qr_* », arrete a la fin) et client DevTools de test_build_page_chrome. Verifie : la
page charge la cuve de ?env=, dessine le QR code avec le texte lu et le verdict ; pour 3 textes, la version du QR code dessine
par optionsQR (octets UTF-8, mode Byte) = celle du verdict du serveur ; modifications signalees, changement de carte confirme,
theme sombre, aucune erreur JS.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import test_build_page_chrome as s
import test_etiquettes_qr_web as tw
import etiquettes_qr_verdict as verdict

CUVE, TV = tw.CUVE, tw.TV
TEXTES = ["Hostname : CUVE", "Hostname : CAPTEURS-CUVE · IP : 192.168.0.43:8081 · Lieu : Garage été €",
          " · ".join(["Ligne libre numéro %d : réglage ModBus 19200 bauds" % i for i in range(8)])]
ETAT = """(() => { const t = id => document.getElementById(id);
  return {env: t('choix-env').value, lu: t('lu').textContent, verdict: t('verdict').className, svg: !!t('qr').querySelector('svg'),
          modules: t('qr').dataset.modules, cartes: document.querySelectorAll('#liste-cartes .env').length,
          lignes: document.querySelectorAll('#lignes .lq').length, pastilles: t('pastilles').textContent,
          bandeau: t('bandeau').textContent, theme: document.documentElement.getAttribute('data-theme'),
          page_off: t('page-carte').disabled}; })()"""


def modules_page(cdp, texte):
    """Nombre de modules du QR code que la page dessinerait pour `texte` (memes options que l'apercu)."""
    return cdp.js("(() => { const q = new QRCodeStyling(optionsQR(%s, {}, 'M', null, 100, 0)); return q._qr.getModuleCount(); })()"
                  % json.dumps(texte))


def sonde(cdp, url, banc, capture):
    cdp.appel("Page.navigate", url=url + "?env=" + CUVE)
    s.attend(cdp, "document.getElementById('qr').querySelector('svg') !== null", 20)
    e = cdp.js(ETAT)
    s.verifie((e["env"], e["svg"], e["verdict"]), (CUVE, True, "verdict lisible"), "?env= : cuve ouverte, QR code dessine, lisible")
    s.verifie((e["lu"], e["lignes"], e["cartes"] >= 3), ("Hostname : CAPTEURS-CUVE · IP : 192.168.0.43:8081", 2, True),
              "texte lu, 2 lignes, liste des cartes")
    s.verifie(e["modules"], str(verdict.verdict(e["lu"], 25, "M")["modules"]), "QR dessine : nombre de modules = verdict")
    for texte in TEXTES:
        attendu = verdict.verdict(texte, 25, "M")["modules"]
        s.verifie(modules_page(cdp, texte), attendu, f"optionsQR : {len(texte.encode('utf-8'))} octets UTF-8 -> {attendu} modules (verdict)")
    if capture:
        cdp.capture(Path(capture) / "etiquettes-qr-cuve.png")

    # XSS : une ligne libre en HTML doit rester du texte, sans rien executer
    piege = '<img src=x onerror="window._xss=1">'
    cdp.js("(() => { ETAT.reglage.lignes.push({source: 'libre', texte: %s}); dessineLignes(); change(); })()" % json.dumps(piege))
    s.attend(cdp, "document.getElementById('lu').textContent.indexOf('<img') >= 0", 5)
    s.verifie((cdp.js("window._xss === undefined"), cdp.js("document.querySelectorAll('#lu img, #lignes img').length")), (True, 0),
              "ligne libre en HTML : affichee en texte, rien d'execute")
    # Diff puis modification : le diff affiche est retire (l'ancien reglage ne peut plus etre ecrit)
    cdp.js("document.getElementById('btn-ecrire').click()")
    s.attend(cdp, "document.querySelectorAll('#ecriture pre.diff').length > 0", 10)
    cdp.js("(() => { const t = document.getElementById('separateur'); t.value = ' = '; t.dispatchEvent(new Event('input')); })()")
    s.verifie(cdp.js("document.querySelectorAll('#ecriture pre.diff').length"), 0, "modification apres le diff : diff retire")
    # Ecriture complete : diff, confirmation, fichier ecrit dans la copie, page relue sans modification en attente
    cdp.js("document.getElementById('btn-ecrire').click()")
    s.attend(cdp, "[...document.querySelectorAll('#ecriture button')].some(b => b.textContent.indexOf('Confirmer') === 0)", 10)
    cdp.js("[...document.querySelectorAll('#ecriture button')].find(b => b.textContent.indexOf('Confirmer') === 0).click()")
    s.attend(cdp, "document.querySelectorAll('#ecriture .avert.vert, #ecriture .avert.rouge').length > 0", 60)   # ~4 s mesurees
    fichier = banc.racine / tw.eqw.modele.DOSSIER / "cartes" / (CUVE + ".json")
    ecrit = fichier.is_file() and json.loads(fichier.read_text(encoding="utf-8"))
    s.verifie((bool(ecrit) and ecrit.get("separateur"), "modifications non écrites" in cdp.js(ETAT)["pastilles"]), (" = ", False),
              "ecriture : surcharge de la cuve ecrite, page relue")
    fichier.unlink()                                       # la suite part d'un depot sans surcharge

    cdp.js("(() => { const r = document.getElementById('taille'); r.value = 40; r.dispatchEvent(new Event('input')); })()")
    s.attend(cdp, "document.getElementById('verdict').textContent.indexOf('module de 0,') >= 0 && document.getElementById('mm').textContent === '40 mm'", 5)
    s.verifie("modifications non écrites" in cdp.js(ETAT)["pastilles"], True, "taille changee : modifications signalees")
    cdp.js("(() => { const c = document.getElementById('choix-env'); c.value = %s; c.dispatchEvent(new Event('change')); })()" % json.dumps(TV))
    e = cdp.js(ETAT)
    s.verifie((e["env"], "ne sont pas écrites" in e["bandeau"]), (CUVE, True), "changement de carte : confirmation demandee, cuve gardee")
    cdp.js("[...document.querySelectorAll('#bandeau button')][0].click()")
    s.attend(cdp, "document.getElementById('lu').textContent.startsWith('Hostname : TV')", 10)
    e = cdp.js(ETAT)
    s.verifie((e["env"], e["page_off"], e["lu"].startswith("Hostname : TV")), (TV, True, True), "TV ouverte : hostname lu, page /qrcode grisee")
    s.verifie(list(banc.racine.joinpath(tw.eqw.modele.DOSSIER, "cartes").glob("*.json")), [], "changement de carte : rien ecrit au depot")

    avant = cdp.js(ETAT)["theme"]                          # headless suit le theme de Windows : le depart varie
    for _ in range(2):
        cdp.js("document.getElementById('theme').click()")
        apres = cdp.js(ETAT)["theme"]
        s.verifie((avant in ("clair", "sombre"), apres), (True, "clair" if avant == "sombre" else "sombre"), f"interrupteur : {avant} -> {apres}")
        if capture:
            cdp.capture(Path(capture) / f"etiquettes-qr-{apres}.png")
        avant = apres
    s.verifie(cdp.erreurs(), [], "aucune erreur JS")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de la page Etiquettes QR code.")
    options.add_argument("--capture", help="dossier ou ecrire les captures PNG")
    args = options.parse_args()
    chrome = next((c for c in s.CHROMES if c.is_file()), None)
    if chrome is None:
        print("BLOQUE : chrome.exe introuvable")
        return 3
    t = Path(tempfile.mkdtemp(prefix="sonde_qr_"))
    banc, proc = tw.Banc(t / "depot"), None
    try:
        port_cdp = s.port_libre()
        proc = subprocess.Popen([str(chrome), "--headless=new", f"--remote-debugging-port={port_cdp}", "--remote-allow-origins=*",
                                 f"--user-data-dir={t / 'profil'}", "--no-first-run", "--no-default-browser-check",
                                 "--disable-extensions", "--window-size=1280,1000", "about:blank"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        limite, cibles = time.monotonic() + 20, None
        while cibles is None and time.monotonic() < limite:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port_cdp}/json/list", timeout=2) as r:
                    cibles = json.loads(r.read())
            except OSError:
                time.sleep(0.2)
        cdp = s.Cdp(next(c for c in cibles if c.get("type") == "page")["webSocketDebuggerUrl"])
        for domaine in ("Runtime.enable", "Log.enable", "Page.enable"):
            cdp.appel(domaine)
        sonde(cdp, f"http://127.0.0.1:{banc.port}/", banc, args.capture)
    except Exception as erreur:                              # noqa: BLE001
        s.verifie(repr(erreur), "pas d'exception de la sonde", "sonde : deroulement")
    finally:
        s.tue_arbre(proc)                                    # jamais de Chrome headless orphelin : l'arbre, puis tout le profil
        motif = t.name
        for _ in range(3):
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -match '%s' }"
                            " | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" % motif],
                           capture_output=True, timeout=60)
            time.sleep(0.5)
        banc.ferme()
        time.sleep(0.5)
        shutil.rmtree(t, ignore_errors=True)
    print("\n" + ("VERT" if not s.ECHECS else f"ROUGE : {len(s.ECHECS)} echec(s) : {s.ECHECS}"))
    return 1 if s.ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
