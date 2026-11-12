"""Sonde Chrome de la page de l'atelier des ecrans (atelier_ecrans_page.PAGE), plan atelier-ecrans A6.

UTILISATION (a la main ; aucun pio, aucune carte ; Chrome headless ~30 s)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_ecrans_page_chrome.py [dossier]
    (dossier : y ecrire une capture de la page dans chaque theme)

Hermetique : serveur dans ce processus sur une COPIE du depot (test_atelier_ecrans_web.Banc), carte simulee par un faux
`get` (aucun acces reseau ; la capture rend un vrai BMP 4 x 2, 16 bits BI_BITFIELDS, comme lv.screenshot()).
Verifie : en-tete (carte, ecran de l'env, etat en ligne), apercu identique au depot, zoom 100 %, ajout par la palette
(DragEvent drop), deplacement a la souris (Input.dispatchMouseEvent) aimante a 8 px, annuler, refus d'une taille de
police absente, tableau, theme memorise, capture affichee, aucune erreur console (temoin `throw` detecte), copie du
depot inchangee. Chrome est arrete a la fin (profil temporaire `sonde_atelier_ecrans_*`).
Code de sortie 0 = vert.
"""
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_atelier_ecrans_web as taw                                              # noqa: E402
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre, tue_arbre     # noqa: E402

ENV = "tasmota32s3-bureau-ecran-debits-pac"
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)
    return ok


def bmp_4x2():
    """BMP 4 x 2, 16 bits RGB565, BI_BITFIELDS (en-tete 0x42 comme celui de lv.screenshot)."""
    pixels = struct.pack("<8H", 0xF800, 0x07E0, 0x001F, 0xFFFF, 0, 0xF800, 0x07E0, 0x001F)
    info = struct.pack("<IiiHHIIiiII", 40, 4, 2, 1, 16, 3, len(pixels), 2835, 2835, 0, 0) + struct.pack("<III", 0xF800, 0x07E0, 0x001F)
    tete = b"BM" + struct.pack("<IHHI", 14 + len(info) + len(pixels), 0, 0, 14 + len(info))
    return tete + info + pixels


class BancPage(taw.Banc):
    def get(self, ip, chemin, delai):
        if "download=" in chemin and "delete=" not in chemin:
            self.appels.append((ip, chemin))
            return bmp_4x2()
        return super().get(ip, chemin, delai)


def souris(cdp, genre, x, y):
    cdp.appel("Input.dispatchMouseEvent", type=genre, x=x, y=y, button="left", buttons=1 if genre != "mouseReleased" else 0, clickCount=1)


def sonde(cdp, banc):
    js = cdp.js
    pret = attend(cdp, "typeof E !== 'undefined' && E.fichiers.length === 3 && document.querySelectorAll('#ecranCarte .o').length > 0", 40)
    verifie(bool(pret), True, "page chargee : description dessinee et 3 fichiers generes")
    verifie(js("document.getElementById('carte').value"), ENV, "en-tete : carte demandee par ?env=")
    verifie(js("document.getElementById('ecran').value"), "ST7262_1024x600", "en-tete : ecran de l'env preselectionne")
    verifie("(celui de l'env)" in (js("document.getElementById('ecran').selectedOptions[0].textContent") or ""), True,
            "en-tete : ecran marque « celui de l'env »")
    verifie("en ligne" in (attend(cdp, "document.getElementById('etat').textContent.indexOf('en ligne') >= 0 && document.getElementById('etat').textContent", 10) or ""),
            True, "en-tete : carte simulee en ligne")
    verifie(js("document.getElementById('resumeFichiers').textContent"), "identique au dépôt", "apercu : fichiers generes identiques au depot")
    js("document.getElementById('zoom100').click()")
    verifie((js("document.getElementById('zoom').textContent"), js("document.getElementById('cadre').style.width")), ("100 %", "1024px"),
            "zoom 100 % : cadre de 1024 px")

    # ajout par la palette (drop) a 101,203 -> aimante a 104,200
    n0 = js("objets(1).length")
    js("(function(){var ec=document.getElementById('ecranCarte'),r=ec.getBoundingClientRect(),dt=new DataTransfer();dt.setData('text/plain','btn');"
       "ec.dispatchEvent(new DragEvent('drop',{dataTransfer:dt,clientX:r.left+101,clientY:r.top+203,bubbles:true,cancelable:true}));})()")
    o = js("JSON.stringify(choisi())")
    o = json.loads(o) if o else {}
    verifie((js("objets(1).length"), o.get("type"), o.get("x"), o.get("y")), (n0 + 1, "btn", 104, 200), "palette : bouton depose, aimante a 8 px")
    aj = attend(cdp, "E.fichiers.length === 3 && E.fichiers[0].ajouts", 15)
    verifie(bool(aj), True, "apercu : pages.jsonl montre l'ajout")

    # deplacement a la souris de +40,+24
    r = js("(function(){var d=document.querySelector('#ecranCarte .o.sel').getBoundingClientRect();return [d.left+d.width/2,d.top+d.height/2];})()")
    souris(cdp, "mousePressed", r[0], r[1])
    for k in range(1, 5):
        souris(cdp, "mouseMoved", r[0] + 10 * k, r[1] + 6 * k)
    souris(cdp, "mouseReleased", r[0] + 40, r[1] + 24)
    verifie(js("[choisi().x, choisi().y]"), [144, 224], "souris : objet deplace de 40,24")
    js("document.getElementById('annuler').click()")
    verifie(js("[choisi().x, choisi().y]"), [104, 200], "annuler : position d'avant le geste")

    # refus d'une taille absente (robotocondensed : 12, 16, 24 compilees)
    js("(function(){var s=document.querySelector('select[aria-label=Police]'),n=document.querySelector('input[aria-label=Taille]');"
       "s.value='robotocondensed';n.value='22';n.dispatchEvent(new Event('change'));})()")
    refus = js("Array.prototype.map.call(document.querySelectorAll('#proprietes .avert'),function(a){return a.hidden?'':a.textContent}).join(' ')")
    verifie("12, 16, 24" in (refus or ""), True, "police : taille 22 refusee avec les tailles possibles")
    verifie(js("choisi().attributs.text_font"), 24, "police : objet inchange apres le refus")

    js("document.querySelector('#vues button[data-vue=tableau]').click()")
    verifie(js("document.querySelectorAll('#tableau tr').length - 1 === objets(1).length && !document.getElementById('vueTableau').hidden"), True,
            "tableau : une ligne par objet de la page")
    js("document.querySelector('#vues button[data-vue=ecran]').click()")

    js("document.getElementById('retablir').click()")
    verifie(js("[choisi().x, choisi().y]"), [144, 224], "retablir : le geste annule revient")

    # meme id sur deux pages : page 1 id 12 = barre, page 2 id 12 = libelle
    js("selectionne(2, 12)")
    verifie(js("[E.page, choisi().type, document.querySelector('#ecranCarte .o.sel').getAttribute('data-page')]"), [2, "label", "2"],
            "cles (page, id) : id 12 de la page 2, pas celui de la page 1")
    js("selectionne(1, 12)")
    verifie(js("choisi().type"), "bar", "cles (page, id) : id 12 de la page 1")

    # texte piege : reste du texte
    js("selectionne(2, 12); modifie(function(){ choisi().attributs.text = '<img src=x onerror=\"window.__xss=1\">'; })")
    time.sleep(0.3)
    verifie(js("[document.querySelectorAll('#ecranCarte img, #objets img, #tableau img').length, window.__xss === undefined,"
               " document.getElementById('objets').textContent.indexOf('<img') >= 0]"), [0, True, True],
            "XSS : un libelle '<img onerror>' reste du texte")
    js("document.getElementById('annuler').click()")

    # autre ecran : lecture seule, rien ne bouge
    js("var s=document.getElementById('ecran'); s.value='ILI9488_480x320'; s.dispatchEvent(new Event('change'))")
    fige = js("JSON.stringify(E.desc)")
    js("ajouteObjet('btn', 16, 16); modifie(function(){ choisi().x = 0; })")
    verifie((js("lecture()"), js("JSON.stringify(E.desc)") == fige, js("document.querySelector('#proprietes input').disabled")),
            (True, True, True), "autre ecran : lecture seule, description intacte, champs desactives")
    verifie("lecture seule" in js("document.getElementById('bandeau').textContent"), True, "autre ecran : bandeau explicite")
    js("var s=document.getElementById('ecran'); s.value='ST7262_1024x600'; s.dispatchEvent(new Event('change'))")
    verifie((js("lecture()"), js("document.getElementById('bandeau').hidden")), (False, True), "retour a l'ecran de la carte : edition rendue")

    # echec de lecture d'une carte : la carte d'avant reste
    js("chargeCarte('carte-inconnue')")
    msg = attend(cdp, "document.getElementById('bandeau').textContent.indexOf('carte-inconnue') >= 0 && document.getElementById('bandeau').textContent", 10)
    verifie((bool(msg), js("E.env"), js("document.getElementById('carte').value")), (True, ENV, ENV),
            "echec de lecture : la carte d'avant reste affichee")

    avant = js("document.documentElement.getAttribute('data-theme')")
    js("document.getElementById('theme').click()")
    apres = js("document.documentElement.getAttribute('data-theme')")
    verifie((apres != avant, js("localStorage.getItem('atelier-ecrans-theme')")), (True, apres), "theme : bascule memorisee")

    js("document.getElementById('capture').click()")
    larg = attend(cdp, "!document.getElementById('captureBoite').hidden && document.getElementById('captureImg').naturalWidth", 30)
    verifie(larg, 4, "capture : BMP de la carte affiche par Chrome")
    verifie(any("download=" in c for _, c in banc.appels), True, "capture : fichier telecharge par le faux get")

    if len(sys.argv) > 1:                                  # capture d'ecran facultative : python ... <dossier>
        cdp.capture(Path(sys.argv[1]) / f"atelier_ecrans_{apres}.png")
        js("document.getElementById('theme').click()")
        cdp.capture(Path(sys.argv[1]) / f"atelier_ecrans_{avant}.png")
    erreurs = [e for e in cdp.erreurs() if "carte-inconnue" not in e]      # 400 voulu de l'echec de lecture
    verifie(erreurs, [], "aucune erreur console")
    js("setTimeout(function(){throw new Error('temoin_sonde')},0)")
    time.sleep(0.5)
    verifie(any("temoin_sonde" in e for e in cdp.erreurs()), True, "temoin : une exception est bien detectee")


def main():
    t = Path(tempfile.mkdtemp(prefix="sonde_atelier_ecrans_"))
    banc = chrome = None
    try:
        banc = BancPage(t)
        avant = taw.instantane(banc.racine)
        exe = next((c for c in CHROMES if c.is_file()), None)
        if exe is None:
            raise FileNotFoundError("chrome.exe introuvable")
        port = port_libre()
        chrome = subprocess.Popen([str(exe), "--headless=new", f"--remote-debugging-port={port}", "--remote-allow-origins=*",
                                   f"--user-data-dir={t / 'profil'}", "--no-first-run", "--no-default-browser-check",
                                   "--disable-extensions", "--window-size=1600,1100", "about:blank"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        limite, cibles = time.monotonic() + 20, None
        while cibles is None:
            try:
                cibles = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2).read())
            except OSError:
                if time.monotonic() > limite:
                    raise
                time.sleep(0.3)
        cdp = Cdp(next(c for c in cibles if c.get("type") == "page")["webSocketDebuggerUrl"])
        for d in ("Runtime.enable", "Log.enable", "Page.enable"):
            cdp.appel(d)
        cdp.appel("Page.navigate", url=f"http://127.0.0.1:{banc.port}/?env={ENV}")
        sonde(cdp, banc)
        verifie(taw.instantane(banc.racine) == avant, True, "copie du depot inchangee (rien n'est ecrit)")
    finally:
        tue_arbre(chrome)
        if banc:
            banc.ferme()
        time.sleep(0.5)
        shutil.rmtree(t, ignore_errors=True)
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)", flush=True)
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(main())
