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
import base64
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
    debut = time.monotonic()
    pret = s.attend(cdp, "document.getElementById('qr').querySelector('svg') !== null", 60)
    print(f"     chargement : {time.monotonic() - debut:.1f} s" + ("" if pret is True else
          f" ; bandeau {cdp.js(ETAT)['bandeau']!r} ; erreurs {cdp.erreurs()}"), flush=True)
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

    # Saisie au clavier dans un libelle : l'apercu revient entre les lettres, le champ doit garder le focus (2026-11-12)
    cdp.js("(() => { const i = document.querySelector('#lignes .lq input'); i.value = ''; i.dispatchEvent(new Event('input')); i.focus(); })()")
    for lettre in "Topic MQTT":
        cdp.appel("Input.insertText", text=lettre)
        time.sleep(0.35)                                   # plus que la minuterie de 250 ms : l'apercu a le temps de revenir
    s.attend(cdp, "document.getElementById('lu').textContent.indexOf('Topic MQTT') >= 0", 10)
    s.verifie(cdp.js("(() => { const i = document.querySelector('#lignes .lq input'); return [i.value, document.activeElement === i]; })()"),
              ["Topic MQTT", True], "saisie lettre par lettre : texte complet, focus garde malgre l'apercu")
    s.verifie("range_extender" in cdp.js("[...document.querySelectorAll('#ajout-standard option')].map(o => o.value)"), True,
              "cuve : champ « Range extender » propose (range extender actif)")
    cdp.js("(() => { const i = document.querySelector('#lignes .lq input'); i.value = 'Hostname'; i.dispatchEvent(new Event('input')); })()")
    # Texte apres la valeur (2026-11-12) : colle a la valeur dans le QR code, focus garde pendant la saisie
    cdp.js("document.querySelector('#lignes .lq .aa-apres').focus()")
    for lettre in ".local":
        cdp.appel("Input.insertText", text=lettre)
        time.sleep(0.35)
    s.attend(cdp, "document.getElementById('lu').textContent.indexOf('CAPTEURS-CUVE.local') >= 0", 10)
    s.verifie(cdp.js("(() => { const i = document.querySelector('#lignes .lq .aa-apres');"
                     " return [document.getElementById('lu').textContent.indexOf('Hostname : CAPTEURS-CUVE.local') >= 0,"
                     " document.activeElement === i, ETAT.reglage.lignes[0].apres]; })()"),
              [True, True, ".local"], "texte apres la valeur : « Hostname : CAPTEURS-CUVE.local », focus garde")
    cdp.js("(() => { const i = document.querySelector('#lignes .lq .aa-apres'); i.value = ''; i.dispatchEvent(new Event('input')); })()")
    s.verifie(cdp.js("'apres' in ETAT.reglage.lignes[0]"), False, "champ apres vide : cle retiree du reglage")
    # XSS : une ligne libre en HTML doit rester du texte, sans rien executer
    piege = '<img src=x onerror="window._xss=1">'
    cdp.js("(() => { ETAT.reglage.lignes.push({source: 'libre', texte: %s}); dessineLignes(); change(); })()" % json.dumps(piege))
    s.attend(cdp, "document.getElementById('lu').textContent.indexOf('<img') >= 0", 5)
    s.verifie((cdp.js("window._xss === undefined"), cdp.js("document.querySelectorAll('#lu img, #lignes img').length")), (True, 0),
              "ligne libre en HTML : affichee en texte, rien d'execute")
    # Diff puis modification : le diff affiche est retire (l'ancien reglage ne peut plus etre ecrit)
    cdp.js("document.getElementById('btn-ecrire').click()")
    # 60 s et verifie : un premier /diff a froid depasse parfois 10 s ; en retard, il serait confirme a la place du second
    s.verifie(s.attend(cdp, "document.querySelectorAll('#ecriture pre.diff').length > 0", 60), True, "premier diff affiche")
    cdp.js("(() => { const t = document.getElementById('separateur'); t.value = ' = '; t.dispatchEvent(new Event('input')); })()")
    s.verifie(cdp.js("document.querySelectorAll('#ecriture pre.diff').length"), 0, "modification apres le diff : diff retire")
    # Ecriture complete : diff, confirmation, fichier ecrit dans la copie, page relue sans modification en attente
    cdp.js("document.getElementById('btn-ecrire').click()")
    s.verifie(s.attend(cdp, "[...document.querySelectorAll('#ecriture button')].some(b => b.textContent.indexOf('Confirmer') === 0)", 60),
              True, "second diff affiche, bouton Confirmer")
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


IMPRESSION = """(() => { const z = document.getElementById('impression');
  return {feuilles: z.querySelectorAll('.feuille').length, cases: z.querySelectorAll('.etiq-case svg').length,
          noms: z.querySelectorAll('.etiq-nom').length, regle: z.querySelectorAll('.regle').length,
          largeur: (z.querySelector('.etiq-case svg') || {style: {}}).style.width, imprime: window._impressions || 0,
          messages: document.getElementById('impression-messages').textContent,
          grille: document.getElementById('planche-grille').textContent}; })()"""


def notes(banc):
    return sorted(tw.tqe.eqe.lit_impressions(banc.racine))


def sonde_impression(cdp, url, banc, capture):
    cdp.appel("Page.navigate", url=url + "?env=" + CUVE)
    s.attend(cdp, "document.getElementById('qr').querySelector('svg') !== null", 20)
    cdp.js("window.print = () => { window._impressions = (window._impressions || 0) + 1; }")   # pas de vraie fenetre
    avant = notes(banc)

    cdp.js("document.getElementById('btn-imprimer').click()")
    s.attend(cdp, "document.getElementById('impression-messages').textContent.indexOf('notée') >= 0", 20)
    e = cdp.js(IMPRESSION)
    s.verifie((e["imprime"], e["feuilles"], e["cases"], e["largeur"], e["regle"]), (1, 1, 1, "25mm", 1),
              "Imprimer : une feuille, un QR code de 25 mm, regle de 50 mm")
    s.verifie(notes(banc), sorted(set(avant) | {CUVE}), "Imprimer : impression notee pour la cuve")
    badge = "[...document.querySelectorAll('#liste-cartes button.env')].find(b => b.title === %s).textContent.indexOf('à réimprimer') >= 0" \
        % json.dumps(CUVE)
    s.verifie(s.attend(cdp, "ETAT.suivi[%s] !== undefined && !(%s)" % (json.dumps(CUVE), badge), 15), True,
              "suivi (A7) : cuve tout juste imprimee, pas de badge « à réimprimer »")
    cdp.js("""(async () => { const g = (await api('/gabarit')).gabarit; g.separateur = ' ~ ';
      const p = await api('/gabarit/diff', {gabarit: g}); await api('/gabarit/ecrire', {gabarit: g, empreinte: p.empreinte});
      await chargeSuivi(); })()""")
    s.verifie(s.attend(cdp, badge, 15), True, "suivi (A7) : separateur du gabarit change, badge « à réimprimer » sur la cuve")
    cdp.js("[...document.querySelectorAll('#impression-messages button')].find(b => b.textContent === 'Annuler la note').click()")
    s.attend(cdp, "document.getElementById('impression-messages').textContent.indexOf('annulée') >= 0", 10)
    s.verifie(notes(banc), avant, "Annuler la note : impression retiree")
    s.verifie(s.attend(cdp, "!(%s)" % badge, 15), True, "suivi (A7) : note annulee, plus de badge « à réimprimer »")
    lien = "(document.getElementById('televerser') || {}).href || null"
    cdp.js("ETAT.etatCarte = {env: %s, carte: 'a_jour'}; majPastilles();" % json.dumps(CUVE))
    s.verifie(cdp.js(lien), None, "Televerser (A7) : carte a jour, pas de lien")
    cdp.js("ETAT.etatCarte = {env: %s, carte: 'a_mettre_a_jour'}; majPastilles();" % json.dumps(CUVE))
    s.verifie(cdp.js(lien), "http://127.0.0.1:%s/?env=%s&depuis=qrcode&fichiers=qrcode.json&redemarrer=1"
              % (7700, CUVE), "Televerser (A7) : carte a mettre a jour, lien vers la page Build (qrcode.json, redemarrage)")

    cdp.js("""(() => { const c = [...document.querySelectorAll('#liste-cartes input[type=checkbox]')].slice(0, 12);
      c.forEach(x => { x.checked = true; x.dispatchEvent(new Event('change')); });
      const n = document.getElementById('petit-nom'); n.checked = true; n.dispatchEvent(new Event('change')); })()""")
    imprimes = 0
    for taille, grille in ((25, "6 × 7 par page, 1 page(s)"), (70, "2 × 3 par page, 2 page(s)")):
        cdp.js("(() => { const t = document.getElementById('planche-taille'); t.value = %d; t.dispatchEvent(new Event('input')); })()" % taille)
        s.verifie(cdp.js(IMPRESSION)["grille"], grille, f"planche {taille} mm : grille annoncee")
        n = cdp.js("window._impressions")
        cdp.js("document.getElementById('btn-planche').click()")
        s.attend(cdp, "window._impressions === %d && !document.getElementById('btn-planche').disabled" % (n + 1), 60)
        e = cdp.js(IMPRESSION)
        # la copie de test n'a ni persist ni IP pour certaines cartes : refusees (aucune ligne lisible), jamais un QR vide
        refus = e["messages"].count("absente de la planche")
        s.verifie((e["cases"] + refus, refus == e["messages"].count("aucune ligne lisible"), e["cases"] == e["noms"], e["largeur"]),
                  (12, True, True, f"{taille}mm"), f"planche 12 cartes a {taille} mm : {e['cases']} codes avec petit nom, {refus} refus motives")
        s.verifie(e["feuilles"], -(-e["cases"] // (42 if taille == 25 else 6)), f"planche {taille} mm : {e['feuilles']} page(s) pour {e['cases']} codes")
        noms = cdp.js("[...document.querySelectorAll('#impression .etiq-nom')].map(n => n.textContent)")
        s.verifie(len(noms) == len(set(noms)) and all(n.endswith(("(ESP32)", "(S3)", "(P4)")) for n in noms if "serveur-rly" in n),
                  True, f"planche {taille} mm : petits noms tous differents (puce des homonymes)")
        imprimes = e["cases"]
        if taille == 25:
            cdp.appel("Emulation.setEmulatedMedia", media="print")
            mesure = cdp.js("""(() => ({main: getComputedStyle(document.querySelector('main')).display,
              zone: getComputedStyle(document.getElementById('impression')).display,
              px: document.querySelector('#impression .etiq-case svg').getBoundingClientRect().width}))()""")
            cdp.appel("Emulation.setEmulatedMedia", media="")
            s.verifie((mesure["main"], mesure["zone"], round(mesure["px"], 1)), ("none", "block", round(25 / 25.4 * 96, 1)),
                      "media print : seule la planche, QR code de 25 mm (94,5 px CSS)")
            if capture:
                pdf = cdp.appel("Page.printToPDF", preferCSSPageSize=True, printBackground=True)
                (Path(capture) / "planche-25mm.pdf").write_bytes(base64.b64decode(pdf["data"]))
                print(f"     PDF : {Path(capture) / 'planche-25mm.pdf'}", flush=True)
    s.verifie(len(notes(banc)), len(set(avant)) + imprimes, f"planche : les {imprimes} cartes imprimees notees, pas les refusees")

    cdp.js("(() => { const n = document.getElementById('petit-nom'); n.checked = false; n.dispatchEvent(new Event('change')); })()")
    types = cdp.js("""(async () => { const p = await exporte('png'), v = await exporte('svg');
      return [p.type, p.size > 1000, v.type, v.size > 1000]; })()""")
    s.verifie(types, ["image/png", True, "image/svg+xml", True], "export PNG et SVG de la cuve")

    deja = notes(banc)
    n = cdp.js("window._impressions")
    cdp.js("document.getElementById('btn-essai').click()")
    s.attend(cdp, "window._impressions === %d" % (n + 1), 60)
    e = cdp.js(IMPRESSION)
    s.verifie((e["cases"], e["noms"], notes(banc)), (8, 8, deja), "planche d'essai : 4 tailles x texte court et long, non notee")
    if capture:
        cdp.appel("Emulation.setEmulatedMedia", media="print")
        cdp.capture(Path(capture) / "planche-essai.png")
        cdp.appel("Emulation.setEmulatedMedia", media="")
    s.verifie(cdp.erreurs(), [], "impression : aucune erreur JS")


def sonde_publication(cdp, url, banc, nu_dossier):
    """A10 : contenu « lien », ecriture, puis « Publier les fiches… » vers un origin nu local (rien ne part sur le reseau)."""
    import test_etiquettes_qr_publication as tpub
    nu = tpub.en_depot(banc.racine, nu_dossier)
    cdp.appel("Page.navigate", url=url + "?env=" + CUVE)
    s.attend(cdp, "document.getElementById('qr').querySelector('svg') !== null", 60)
    cdp.js("(() => { const c = document.getElementById('contenu'); c.value = 'lien'; c.dispatchEvent(new Event('change')); })()")
    s.verifie(s.attend(cdp, "document.getElementById('lu').textContent === %s" % json.dumps(tpub.URL), 15), True,
              "contenu « lien » : le telephone lirait l'adresse de la fiche")
    cdp.js("document.getElementById('btn-ecrire').click()")
    s.verifie(s.attend(cdp, "[...document.querySelectorAll('#ecriture button')].some(b => b.textContent.indexOf('Confirmer') === 0)", 60),
              True, "contenu « lien » : diff affiche")
    cdp.js("[...document.querySelectorAll('#ecriture button')].find(b => b.textContent.indexOf('Confirmer') === 0).click()")
    # A11 : l'ecriture d'une carte en lien enchaine d'elle-meme sur le diff des fiches (un clic « Publier » reste a faire)
    pret = s.attend(cdp, "[...document.querySelectorAll('#ecriture button')].some(b => b.textContent === 'Publier')", 90)
    texte = cdp.js("document.getElementById('ecriture').textContent")
    if "écrit(s)" not in texte:
        print("     zone #ecriture :", texte[:400], flush=True)
    s.verifie((pret, "écrit(s)" in texte, "PUBLIQUES" in texte, CUVE + ".html" in texte), (True, True, True, True),
              "Ecrire en mode lien : diff des fiches enchaine, ecriture confirmee au-dessus, avertissement public")
    s.verifie(s.attend(cdp, "document.getElementById('liste-cartes').textContent.indexOf('fiche à republier') >= 0", 30), True,
              "badge « fiche à republier » sur la cuve avant publication (A11)")
    cdp.js("[...document.querySelectorAll('#ecriture button')].find(b => b.textContent === 'Publier').click()")
    # le message vert de l'ecriture est deja la : attendre le resultat de l'envoi lui-meme
    s.attend(cdp, "/Fiches publiées|Refusé/.test(document.getElementById('ecriture').textContent)", 120)
    s.verifie(s.attend(cdp, "!document.getElementById('btn-pages').classList.contains('cache')", 30), True,
              "Pages inactif (faux gh) : bouton « Activer GitHub Pages » affiche (A11)")
    s.verifie((cdp.js("document.getElementById('ecriture').textContent").startswith("Fiches publiées"), tpub.arbre(nu)),
              (True, [".nojekyll", CUVE + ".html"]), "Publier : fiche poussee sur la branche etiquettes de l'origin nu")
    s.verifie(s.attend(cdp, "document.getElementById('liste-cartes').textContent.indexOf('fiche à republier') < 0", 60), True,
              "apres publication : badge « fiche à republier » retire")
    s.verifie(cdp.erreurs(), [], "publication : aucune erreur JS")


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
        sonde_impression(cdp, f"http://127.0.0.1:{banc.port}/", banc, args.capture)
        (t / "nu").mkdir()
        sonde_publication(cdp, f"http://127.0.0.1:{banc.port}/", banc, t / "nu")   # en dernier : la copie devient un depot git
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
