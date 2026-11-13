"""Sonde Chrome de la page de l'atelier des ecrans (atelier_ecrans_page.PAGE), plan atelier-ecrans A6.

UTILISATION (a la main ; aucun pio, aucune carte ; Chrome headless ~30 s)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_ecrans_page_chrome.py [dossier]
    (dossier : y ecrire une capture de la page dans chaque theme)

Hermetique : serveur dans ce processus sur une COPIE du depot (test_atelier_ecrans_web.Banc), carte simulee par un faux
`get` (aucun acces reseau ; la capture rend un vrai BMP 4 x 2, 16 bits BI_BITFIELDS, comme lv.screenshot()).
Verifie : en-tete (carte, ecran de l'env, etat en ligne), apercu identique au depot, zoom 100 %, ajout par la palette
(DragEvent drop), deplacement a la souris (Input.dispatchMouseEvent) aimante a 8 px, annuler, refus d'une taille de
police absente, tableau, theme memorise, capture affichee, onglet display.ini (A12), palier 2, barre de navigation et page Systeme construite (A14, A17, A19 :
test_atelier_ecrans_page_chrome_palier2.py), aucune erreur console (temoin `throw` detecte), copie du
depot inchangee. Chrome est arrete a la fin (profil temporaire `sonde_atelier_ecrans_*`).
Code de sortie 0 = vert.
"""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atelier_ecrans_catalogue as cat                                              # noqa: E402
import atelier_ecrans_import as aei                                                 # noqa: E402
import atelier_ecrans_remarques as aer                                              # noqa: E402
import atelier_ecrans_web as aew                                                    # noqa: E402
import test_atelier_ecrans_remarques as tar                                         # noqa: E402
import test_atelier_ecrans_page_chrome_palier2 as tp2                               # noqa: E402
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


def instantane(racine):
    return {k: v for k, v in taw.instantane(racine).items() if not k.startswith(".git/") and not k.endswith("/remarques.json")}


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


def bouton_texte(debut):
    return ("Array.prototype.filter.call(document.querySelectorAll('#remarques button'),function(b){return b.textContent.indexOf("
            + json.dumps(debut) + ")===0})[0]")


def ecrit_rq(js, texte):
    js("(function(){var t=document.getElementById('rqTexte');t.value=" + json.dumps(texte) + ";t.dispatchEvent(new Event('input'));})()")
    js(bouton_texte("Épingler") + ".click()")


def sonde_remarques(cdp, banc):
    js = cdp.js
    js("document.querySelector('#panneaux button[data-panneau=remarques]').click()")
    verifie(js("!document.getElementById('remarques').hidden && document.getElementById('proprietes').hidden"), True, "onglet Remarques affiche")
    js("E.page = 1; selectionne(1, 11)")
    ecrit_rq(js, "Noms trop petits de loin, passer en 28 ?")
    n = attend(cdp, "R.liste.length === 1 && JSON.stringify(R.liste[0].cible)", 10)
    verifie(n, '{"page":1,"objet":11}', "epingle sur l'objet choisi (page, id)")
    verifie((js("document.querySelector('#ecranCarte .epingle').textContent"), js("document.getElementById('pastilleRemarques').hidden")), ("1", False),
            "epingle dessinee sur l'ecran, pastille de l'en-tete")
    fige = js("JSON.stringify(E.desc)")
    js(bouton_texte("▭ Tracer") + ".click()")
    r = js("(function(){var r=document.getElementById('ecranCarte').getBoundingClientRect();return [r.left, r.top];})()")
    z = js("E.zoom")
    souris(cdp, "mousePressed", r[0] + 100 * z, r[1] + 495 * z)
    souris(cdp, "mouseMoved", r[0] + 250 * z, r[1] + 520 * z)
    souris(cdp, "mouseReleased", r[0] + 400 * z, r[1] + 540 * z)
    zone = js("R.zone")
    verifie((zone is not None and abs(zone[0] - 100) <= 2 and abs(zone[2] - 300) <= 2, js("JSON.stringify(E.desc)") == fige), (True, True),
            f"zone tracee a la souris ({zone}), aucun objet deplace")
    ecrit_rq(js, "<b>gras</b><img src=x onerror=\"window.__xss2=1\">")
    attend(cdp, "R.liste.length === 2", 10)
    verifie((js("'zone' in R.liste[1].cible"), js("document.querySelectorAll('#remarques img, #remarques b.x').length"), js("window.__xss2 === undefined")),
            (True, 0, True), "remarque sur la zone ; texte piege affiche comme du texte")
    js(bouton_texte("▶ Traiter") + ".click()")
    prop = attend(cdp, "R.liste[0].etat === 'proposee' && R.liste[0].proposition.texte", 40)
    verifie(prop, "Police 28 pour le nom de la voie.", "traitement (faux claude) : proposition affichee")
    verifie("text_font" in (js("document.getElementById('remarques').textContent") or ""), True, "operations de la proposition listees")
    h = js("E.histo.length")
    js(bouton_texte("Appliquer") + ".click()")
    attend(cdp, "R.appliquees.hasOwnProperty(1)", 10)
    verifie((js("objet(1, 11).attributs.text_font"), js("E.histo.length"), js("R.liste[0].etat"),
             "sur le canevas" in (js("document.getElementById('remarques').textContent") or ""), js("!!" + bouton_texte("Appliquer"))),
            (tar.POLICE_28, h + 1, "proposee", True, False),
            "Appliquer : description modifiee, une entree d'historique, remarque encore proposee (appliquee a l'ecriture)")
    js("document.getElementById('annuler').click()")
    verifie((js("objet(1, 11).attributs.text_font"), js("R.appliquees.hasOwnProperty(1)"), js("!!" + bouton_texte("Appliquer"))), (24, False, True),
            "Annuler apres Appliquer : police d'avant, bouton Appliquer rendu")
    erreurs = [e for e in cdp.erreurs() if "carte-inconnue" not in e and "temoin_sonde" not in e]
    verifie(erreurs, [], "remarques : aucune erreur console")


def sonde_ecriture(cdp, banc):
    js = cdp.js
    serveur = "tasmota32s3-bureau-serveur-debits-pac"
    js("modifie(function(){ objet(0, 1).attributs.text = 'Debits du chauffage'; })")
    js(bouton_texte("Appliquer") + ".click()")
    attend(cdp, "R.appliquees.hasOwnProperty(1)", 10)
    js("document.getElementById('ecrire').click()")
    n = attend(cdp, "!document.getElementById('confirmation').hidden && document.querySelectorAll('#confirmation li').length", 15)
    verifie(n, 3, "Ecrire : confirmation avec les trois fichiers")
    js("document.getElementById('confirmer').click()")
    msg = attend(cdp, "document.getElementById('ecritureMessage').textContent.indexOf('Écrit') === 0 && document.getElementById('ecritureMessage').textContent", 20)
    verifie(bool(msg), True, f"Ecrire : ecrit dans la copie du depot ({msg})")
    ej = (banc.racine / "outils_docs/atelier_ecrans/cartes" / ENV / "ecran.json").read_text(encoding="utf-8")
    pj = (banc.racine / "data/bureau/tasmota32s3-ecran-debits-pac/pages.jsonl").read_text(encoding="utf-8")
    verifie(("Debits du chauffage" in ej, "Debits du chauffage" in pj), (True, True), "Ecrire : ecran.json et pages.jsonl de la copie modifies")
    rq = json.loads((banc.racine / "outils_docs/atelier_ecrans/cartes" / ENV / "remarques.json").read_text(encoding="utf-8"))
    verifie((js("R.liste[0].etat"), rq[0]["etat"], js("Object.keys(R.appliquees).length")), ("appliquee", "appliquee", 0),
            "Ecrire apres Appliquer : remarque appliquee dans la page et dans remarques.json")
    verifie("fichiers=pages.jsonl" in (js("document.querySelector('#ecritureMessage a').href") or ""), True, "lien page Build avec le fichier de l'interface")
    js("document.getElementById('ecrire').click()")
    vide = attend(cdp, "!document.getElementById('confirmation').hidden && document.getElementById('confirmation').textContent.indexOf('Rien') >= 0", 15)
    verifie(bool(vide), True, "Ecrire une seconde fois (bouton rendu actif) : rien a ecrire")
    js("Array.prototype.filter.call(document.querySelectorAll('#confirmation button'),function(b){return b.textContent==='Fermer'})[0].click()")

    js("var s=document.getElementById('ecran'); s.value='ILI9488_480x320'; s.dispatchEvent(new Event('change'))")
    verifie(js("!document.getElementById('changement').hidden && !!document.getElementById('proposeChangement')"), True, "autre ecran : bouton Proposer le changement")
    js("document.getElementById('proposeChangement').click()")
    refus0 = attend(cdp, "!document.getElementById('confirmation').hidden && document.getElementById('confirmation').textContent.indexOf('refusé') >= 0", 20)
    verifie((bool(refus0), js("!!document.getElementById('confirmer')"), js("document.getElementById('confirmation').textContent.indexOf('systeme') >= 0")),
            (True, False, True), "page Systeme trop grande pour 480 x 320 : refus affiche, pas de bouton de confirmation")
    js("var s=document.getElementById('ecran'); s.value=E.ecranEnv; s.dispatchEvent(new Event('change'))")     # retour a l'ecran de la carte : edition possible
    js("modifie(function(){ E.desc.pages = E.desc.pages.filter(function(p){ return !p.modele; }); })")     # le reste de la sonde part sans elle
    js("var s=document.getElementById('ecran'); s.value='ILI9488_480x320'; s.dispatchEvent(new Event('change'))")
    js("document.getElementById('proposeChangement').click()")
    ok = attend(cdp, "!!document.getElementById('confirmer') && E.desc.ecran === 'ILI9488_480x320'", 20)
    verifie((bool(ok), js("E.fichiers.some(function(f){return f.chemin.slice(-11)==='display.ini'})"),
             js("E.desc.navigation.h")), (True, True, 25), "proposition : description a l'echelle dessinee, display.ini au diff")
    verifie(js("document.getElementById('confirmation').textContent.indexOf('cible tactile') >= 0"), True, "proposition : boutons trop petits signales")
    js("document.getElementById('confirmer').click()")
    fin = attend(cdp, "E.ecranEnv === 'ILI9488_480x320' && document.getElementById('ecritureMessage').textContent.indexOf('Écran changé') === 0", 30)
    verifie(bool(fin), True, "changement d'ecran ecrit, page rechargee sur le nouvel ecran")
    ini = (banc.racine / "data/bureau/tasmota32s3-ecran-debits-pac/display.ini").read_text(encoding="utf-8")
    verifie(ini.startswith(":H,ILI9488"), True, "display.ini de la carte repris de l'ILI9488")

    js(f"var c=document.getElementById('carte'); c.value='{serveur}'; c.dispatchEvent(new Event('change'))")
    attend(cdp, f"E.env === '{serveur}'", 15)
    avant = (banc.racine / "data/bureau/tasmota32s3-serveur-debits-pac/display.ini").read_bytes()
    js("var s=document.getElementById('ecran'); s.value='ST7262_1024x600'; s.dispatchEvent(new Event('change'))")
    js("document.getElementById('proposeChangement').click()")
    refus = attend(cdp, "!document.getElementById('confirmation').hidden && document.getElementById('confirmation').textContent.indexOf('refusé') >= 0", 20)
    verifie((bool(refus), js("!!document.getElementById('confirmer')")), (True, False), "conflit de broches : refus affiche, pas de bouton de confirmation")
    js("var s=document.getElementById('ecran'); s.value=''; s.dispatchEvent(new Event('change'))")
    verifie((js("lecture()"), js("document.getElementById('confirmation').hidden"), js("E.desc.ecran")), (False, True, None),
            "retour a la carte sans ecran : proposition oubliee")
    verifie(js("Array.prototype.some.call(document.querySelectorAll('#ecran optgroup'), function(g){return g.label==='Fournis par Tasmota'})"
               " && !document.querySelector('#ecran option[value=\"SSD1306_128x64\"]')"), True,
            "liste des ecrans : groupe Tasmota, ecran monochrome absent")
    verifie((banc.racine / "data/bureau/tasmota32s3-serveur-debits-pac/display.ini").read_bytes(), avant, "refus : display.ini intact")
    erreurs = [e for e in cdp.erreurs() if "carte-inconnue" not in e and "temoin_sonde" not in e]
    verifie(erreurs, [], "ecriture et changement : aucune erreur console")


def sonde_polices(cdp, banc):
    js = cdp.js
    for rel in cat.SOURCES:                              # sources du firmware lues par cat.genere a l'import
        (banc.racine / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(taw.DEPOT / rel, banc.racine / rel)
    ttf = banc.racine.parent / "Essai-Sonde.ttf"         # hors de la copie : nom neuf, octets de la police du depot
    shutil.copy2(banc.racine / "data/bureau/tasmota32s3-ecran-debits-pac/RobotoCondensed-Regular.ttf", ttf)
    js(f"var c=document.getElementById('carte'); c.value='{ENV}'; c.dispatchEvent(new Event('change'))")
    attend(cdp, f"E.env === '{ENV}' && !lecture()", 15)     # sonde_ecriture finit sur la carte serveur
    js("document.getElementById('importPolice').open = true")
    noeud = cdp.appel("DOM.querySelector", nodeId=cdp.appel("DOM.getDocument")["root"]["nodeId"], selector="#policeFichier")["nodeId"]
    cdp.appel("DOM.setFileInputFiles", nodeId=noeud, files=[str(ttf)])
    js("document.getElementById('policeFichier').dispatchEvent(new Event('change'))")
    pret = attend(cdp, "!!document.getElementById('policeImporter') && document.getElementById('policeResultat').textContent", 20)
    verifie(("Apache" in (pret or ""), js("document.getElementById('policeImporter').disabled")), (True, True),
            f"police choisie : licence lue, Importer grise avant la case ({(pret or '')[:60]})")
    js("var c=document.getElementById('policeLicence'); c.checked=true; c.dispatchEvent(new Event('change'))")
    js("document.getElementById('policeImporter').click()")
    fin = attend(cdp, "document.getElementById('policeResultat').textContent.indexOf('Importée') === 0 && "
                      "E.catalogue.polices.some(function(p){return p.nom==='Essai-Sonde'})", 30)
    importee = banc.racine / "data/bureau/tasmota32s3-ecran-debits-pac/Essai-Sonde.ttf"
    verifie((bool(fin), importee.is_file() and importee.read_bytes() == ttf.read_bytes()),
            (True, True), "Importer : police dans le dossier de la carte, catalogue relu par la page")
    erreurs = [e for e in cdp.erreurs() if "carte-inconnue" not in e and "temoin_sonde" not in e]
    verifie(erreurs, [], "import de police : aucune erreur console")


def sonde_display(cdp, banc):
    """Onglet display.ini : liste, analyse expliquee, erreur en direct, Ajouter a sa place, enregistrement, note."""
    js = cdp.js
    ref = banc.racine / aew.adi.REFERENCE
    ref.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(taw.DEPOT / aew.adi.REFERENCE, ref)
    ini = "data/bureau/tasmota32s3-ecran-debits-pac/display.ini"        # sonde_ecriture l'a change en ILI9488 (PAR)
    shutil.copy2(taw.DEPOT / ini, banc.racine / ini)
    js("document.querySelector('#modes button[data-mode=display]').click()")
    n = attend(cdp, "!document.getElementById('vueDisplay').hidden && document.getElementById('vueInterface').hidden && D.liste.length", 20)
    verifie((n or 0) >= 60, True, f"bascule display.ini : {n} fichiers listes, vue Interface masquee")
    js(f"ouvreDisplay('carte', '{ENV}')")
    lignes = attend(cdp, "D.fichier && D.fichier.source === 'carte' && document.querySelectorAll('#diLignes tr').length", 15)
    titre = js("document.querySelector('#diLignes .arg').title")
    params = js("Array.prototype.map.call(document.querySelectorAll('#diParams .rq b'), function(b){return b.textContent}).join(' ')")
    verifie(((lignes or 0) > 5, js("document.getElementById('diErreurs').hidden"), js("document.getElementById('diBus').textContent"),
             titre.startswith("nom"), " :IS " in f" {params} ", " :A " in f" {params} "), (True, True, "RGB", True, True, False),
            "fichier de la carte : lignes expliquees, sans erreur, parametres du bus RGB seulement")
    js("var t=document.getElementById('diTexte'); t.value=t.value.replace(':S,2,', ':S,2, '); t.dispatchEvent(new Event('input'))")
    e = attend(cdp, "!document.getElementById('diErreurs').hidden && document.getElementById('diErreurs').textContent", 10)
    verifie("espace" in (e or ""), True, f"frappe : erreur affichee en direct ({(e or '')[:60]})")
    js("var t=document.getElementById('diTexte'); t.value=t.value.replace(':S,2, ', ':S,2,'); t.dispatchEvent(new Event('input'))")
    attend(cdp, "document.getElementById('diErreurs').hidden", 10)
    js("Array.prototype.filter.call(document.querySelectorAll('#diParams .rq'), function(r){return r.querySelector('b').textContent === ':B'})[0]"
       ".querySelector('button').click()")
    ajout = attend(cdp, "document.getElementById('diTexte').value.indexOf(':B,') >= 0 && document.getElementById('diTexte').value", 10)
    l = (ajout or "").splitlines()
    verifie((l[l.index(":3,03") + 1].startswith(":B,") if ":3,03" in l else None), True, "Ajouter :B : ligne inseree apres :3 (rang)")
    js("document.getElementById('diNom').value = 'essai-sonde'; document.getElementById('diEnregistrer').click()")
    c = attend(cdp, "!document.getElementById('diConfirmation').hidden && document.getElementById('diConfirmation').textContent", 10)
    verifie((c or "").startswith("Créer " + cat.PERSO + "/essai-sonde.ini"), True, "Enregistrer : diff a confirmer (creation)")
    js("document.getElementById('diNom').dispatchEvent(new Event('input'))")
    verifie((js("document.getElementById('diConfirmation').hidden"), js("D.prevu")), (True, None),
            "frappe apres le diff : confirmation perimee retiree")
    js("document.getElementById('diEnregistrer').click()")
    attend(cdp, "!document.getElementById('diConfirmation').hidden && !!document.querySelector('#diConfirmation .btn.prim')", 10)
    js("document.querySelector('#diConfirmation .btn.prim').click()")
    attend(cdp, "D.fichier && D.fichier.source === 'perso' && D.fichier.nom === 'essai-sonde' && "
                "document.getElementById('diMessage').textContent.indexOf('Enregistré') === 0", 15)
    time.sleep(1)
    verifie(js("document.getElementById('diMessage').textContent.indexOf('Enregistré') === 0"), True,
            "message « Enregistré » garde apres la relecture du fichier")
    fichier = banc.racine / cat.PERSO / "essai-sonde.ini"
    verifie((fichier.is_file() and fichier.read_text(encoding="utf-8").splitlines() == l,
             js("document.getElementById('diNotesBoite').hidden")), (True, False),
            "fichier ecrit dans la bibliotheque, rouvert avec ses notes")
    js("document.getElementById('diNote').value = 'luminosite trop forte'; document.getElementById('diAjoutNote').click()")
    attend(cdp, "document.getElementById('diNotes').textContent.indexOf('luminosite trop forte') >= 0", 10)
    notes = banc.racine / cat.PERSO / "essai-sonde.notes.md"
    verifie(notes.is_file() and "luminosite trop forte" in notes.read_text(encoding="utf-8"), True, "note de terrain ecrite")
    js("document.getElementById('diAppliquer').click()")
    p = attend(cdp, "!document.getElementById('vueInterface').hidden && !!W.changement && !document.getElementById('confirmation').hidden && "
                    "document.getElementById('confirmation').textContent", 30)
    verifie(("display.ini" in (p or ""), "refusé" in (p or "")), (True, False),
            f"Appliquer a la carte : proposition de changement d'ecran avec le display.ini ({(p or '')[:70]})")
    js("document.getElementById('confirmer').click()")
    attend(cdp, "document.getElementById('ecritureMessage').textContent.indexOf('Écran changé') === 0", 30)
    ini_carte = (banc.racine / ini).read_text(encoding="utf-8").splitlines()
    verifie(ini_carte == fichier.read_text(encoding="utf-8").splitlines(), True, "display.ini de la carte = fichier de la bibliotheque")
    js("document.querySelector('#modes button[data-mode=interface]').click()")
    verifie((js("document.getElementById('vueInterface').hidden"), js("document.getElementById('vueDisplay').hidden")), (False, True),
            "retour a l'interface")
    erreurs = [e for e in cdp.erreurs() if "carte-inconnue" not in e and "temoin_sonde" not in e]
    verifie(erreurs, [], "onglet display.ini : aucune erreur console")


def sonde_import(cdp, banc):
    """Import d'un pages.jsonl ecrit a la main : description remplacee (Annuler la rend), ligne brute hachuree, apercu
    HASPmota = memes objets que la source, rien d'ecrit."""
    js = cdp.js
    rel = "data/bureau/tasmota32s3-ecran-debits-pac/pages.jsonl"
    brute = '{"id":200,"obj":"label","x":10,"y":10,"w":100,"h":30,"text":"r","val_rule":"X#Y"}\n'    # herite la page 3
    lignes = (taw.DEPOT / rel).read_text(encoding="utf-8").splitlines(keepends=True)
    i4 = next(i for i, l in enumerate(lignes) if l.startswith('{"page":4,'))        # avant la page Systeme : la ligne reste a la page 3
    source = "".join(lignes[:i4]) + brute + "".join(lignes[i4:])
    (banc.racine / rel).write_text(source, encoding="utf-8")
    avant = instantane(banc.racine)
    attend(cdp, f"E.env === '{ENV}' && !document.getElementById('importBoite').hidden", 15)
    js("modifie(function(){ E.desc.objets[0].x += 8; }); document.getElementById('ecrire').click()")   # un diff a confirmer
    attend(cdp, "!document.getElementById('confirmation').hidden", 15)
    js("document.getElementById('importer').click()")
    av = attend(cdp, "document.getElementById('importMessage').textContent.indexOf('déjà une description') >= 0", 10)
    verifie((bool(av), js("document.getElementById('confirmation').hidden"), js("E.desc.objets.some(function(o){return o.type==='brut'})")),
            (True, True, False), "import sur une carte decrite : confirmation demandee, diff d'ecriture ferme, rien d'importe")
    js("document.getElementById('importer').click()")
    m = attend(cdp, "document.getElementById('importMessage').textContent.indexOf('Importé') === 0 && "
                    "document.getElementById('importMessage').textContent", 20)
    js("E.page = 3; dessineTout()")
    verifie(("1 ligne(s) gardée(s)" in (m or ""), js("bruts(3).length"), js("document.querySelectorAll('#ecranCarte .o.brut').length"),
             js("document.querySelectorAll('#objets .brut').length")), (True, 1, 1, 1),
            f"import : ligne val_rule gardee brute, hachuree et listee ({(m or '')[:70]})")
    gen = attend(cdp, "var c = (E.fichiers.filter(function(f){return f.nom==='pages.jsonl'})[0]||{}).contenu || ''; "
                     "c.indexOf('val_rule') >= 0 && c", 15)
    a, b = aei.lignes_effectives(source), aei.lignes_effectives(gen or "")
    ecart = next((f"ligne {i + 1} : {x} != {y}" for i, (x, y) in enumerate(zip(a, b)) if x != y), None) or \
        (None if len(a) == len(b) else f"{len(a)} lignes, {len(b)} generees")
    verifie(ecart, None, "apercu HASPmota = memes objets que la source")
    js("document.getElementById('annuler').click()")
    verifie(js("E.desc.objets.some(function(o){return o.type==='brut'})"), False, "Annuler : description d'avant l'import")
    verifie(instantane(banc.racine) == avant, True, "import : rien n'est ecrit")
    erreurs = [e for e in cdp.erreurs() if "carte-inconnue" not in e and "temoin_sonde" not in e]
    verifie(erreurs, [], "import : aucune erreur console")


def main():
    t = Path(tempfile.mkdtemp(prefix="sonde_atelier_ecrans_"))
    banc = chrome = None
    try:
        faux = t / "faux_claude.py"
        faux.write_text(tar.FAUX, encoding="utf-8")
        os.environ.update(FAUX_CLAUDE="ok", FAUX_CLAUDE_ARGV=str(t / "argv.json"), OUTILS_TASMOTA_DOSSIER=str(t / "donnees"))
        vrai = aer.Traitement
        aew.aer.Traitement = lambda racine: vrai(racine, programme=[sys.executable, str(faux)])     # jamais le vrai claude
        aew._builds_defaut = lambda: []                                     # aucun build : pas de requete aux processus
        banc = BancPage(t)
        tar.etat_depart(banc.racine)         # hermetique : sans les remarques du vrai depot, voie 1 en police 24
        for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "copie"]):
            tar.git(banc.racine, *args)
        avant = instantane(banc.racine)
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
        tp2.sonde_systeme(cdp, banc, verifie, ENV)
        sonde_remarques(cdp, banc)
        verifie(instantane(banc.racine) == avant, True, "copie du depot inchangee hors remarques.json (ecran.json non ecrit)")
        sonde_ecriture(cdp, banc)
        sonde_polices(cdp, banc)
        sonde_display(cdp, banc)
        sonde_import(cdp, banc)
        tp2.sonde_palier2(cdp, banc, verifie, instantane)
        tp2.sonde_navigation(cdp, banc, verifie, instantane)
    finally:
        tue_arbre(chrome)
        # tue_arbre manque parfois un fils de Chrome : balayage par le profil temporaire de cette passe
        subprocess.run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
                        f"Where-Object {{ $_.CommandLine -like '*{t.name}*' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"],
                       capture_output=True, timeout=60)
        if banc:
            banc.ferme()
        time.sleep(0.5)
        shutil.rmtree(t, ignore_errors=True)
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)", flush=True)
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(main())
