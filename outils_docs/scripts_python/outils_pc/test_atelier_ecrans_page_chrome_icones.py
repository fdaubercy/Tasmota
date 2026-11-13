"""Sonde Chrome du panneau « Icones » de l'atelier des ecrans (plan atelier-ecrans A15).

Pas un banc a lancer seul : appelee par test_atelier_ecrans_page_chrome.py::main (meme Chrome, meme copie du depot), qui lui
passe son `verifie`. Verifie la grille (autant de boutons que le catalogue), la police locale chargee (aucun CDN), la recherche,
le clic dans un nouveau libelle puis dans un libelle choisi, le glyphe dessine dans l'ecran, les sites et l'absence d'erreur.
L'historique est defait en fin de sonde : la description reste celle du depot.
"""
import base64
import json

from test_build_page_chrome import attend      # noqa: E402
from test_atelier_ecrans_page_chrome_palier2 import erreurs_console   # noqa: E402
from test_atelier_ecrans_images import png   # noqa: E402


def sonde_icones(cdp, banc, verifie):
    js = cdp.js
    catalogue = json.loads((banc.racine / "outils_docs/schemas/icones_firmware.json").read_text(encoding="utf-8"))["icones"]
    avant, n0 = js("JSON.stringify(E.desc)"), js("E.histo.length")
    js("E.sel = null; dessineTout(); document.querySelector('#panneaux [data-panneau=icones]').click()")
    n = attend(cdp, "document.querySelectorAll('#icones .grilleIcones button').length", 15)
    verifie((n, js("document.getElementById('icones').hidden"), js("document.getElementById('proprietes').hidden")), (len(catalogue), False, True),
            "icones : onglet ouvert, une case par glyphe du catalogue")
    verifie(bool(attend(cdp, "document.fonts.check('28px MDI', String.fromCodePoint(0xF0335))", 15)), True, "icones : police MDI locale chargee (/lib/mdi.ttf)")
    js("var q=document.querySelector('#icones input'); q.value='pump'; q.dispatchEvent(new Event('input'))")
    noms = js("Array.prototype.map.call(document.querySelectorAll('#icones .grilleIcones .nom'), function(x){return x.textContent})")
    verifie((len(noms) >= 1, all("pump" in x for x in noms), "water-pump" in noms), (True, True, True), "icones : recherche par nom")
    js("var q=document.querySelector('#icones input'); q.value='lightbulb'; q.dispatchEvent(new Event('input'))")
    js("Array.prototype.filter.call(document.querySelectorAll('#icones .grilleIcones button'), function(b){return b.title.indexOf('lightbulb :') === 0})[0].click()")
    verifie((js("choisi().type"), js("choisi().attributs.text.charCodeAt(0)"), js("choisi().attributs.text_font")), ("label", 0xE335, "montserrat-28"),
            "icones : clic sans objet choisi -> nouveau libelle avec le glyphe en montserrat-28")
    dessine = attend(cdp, "var m = document.querySelector('#ecranCarte .o.sel .mdi, #ecranCarte .o .mdi'); m && m.textContent.codePointAt(0)", 10)
    verifie(dessine, 0xF0335, "icones : glyphe dessine dans l'ecran par la police MDI (U+E335 -> MDI F0335)")
    js("E.page = 0; selectionne(0, 1)")
    js("var q=document.querySelector('#icones input'); q.value='power'; q.dispatchEvent(new Event('input'))")
    js("Array.prototype.filter.call(document.querySelectorAll('#icones .grilleIcones button'), function(b){return b.title.indexOf('power :') === 0})[0].click()")
    verifie((js("objet(0, 1).attributs.text.charCodeAt(0)"), js("objet(0, 1).attributs.text_font")), (0xE425, "montserrat-28"),
            "icones : clic avec un libelle choisi -> son texte devient le glyphe")
    sites = js("Array.prototype.map.call(document.querySelectorAll('#icones a'), function(a){return a.getAttribute('href').slice(0, 8) + a.rel})")
    verifie(sites, ["https://noopener noreferrer"] * 7, "icones : 7 sites de l'annuaire, liens sortants sans opener")
    js("modifie(function(){ objet(0, 1).attributs.text = '<b id=\"intrus\">x</b>\uE335'; })")      # du HTML dans un libelle reste du texte
    verifie((js("!!document.querySelector('#ecranCarte #intrus')"), js("document.querySelectorAll('#ecranCarte .o .mdi').length > 0")), (False, True),
            "icones : <b> dans un libelle reste du texte, le glyphe a cote est dessine")
    for _ in range(10):                                     # borne : Annuler desactive ne doit pas boucler
        if js("E.histo.length") <= n0:
            break
        js("document.getElementById('annuler').click()")
    verifie(js("JSON.stringify(E.desc)") == avant, True, "icones : description du depot retrouvee apres annulation")
    js("document.querySelector('#panneaux [data-panneau=proprietes]').click()")
    sonde_import_png(cdp, banc, verifie)
    js("document.querySelector('#panneaux [data-panneau=icones]').click()")
    verifie(erreurs_console(cdp), [], "icones : aucune erreur console")


def sonde_import_png(cdp, banc, verifie):
    """Import d'un PNG par la page (File construit en JS : le selecteur de fichiers n'est pas pilotable) puis nettoyage de la copie."""
    js = cdp.js
    def donne(octets, nom):
        js("(function(){ var b = atob('%s'), u = new Uint8Array(b.length); for (var i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); "
           "analyseImage(new File([u], '%s', {type: 'image/png'})); })()" % (base64.b64encode(octets).decode(), nom))
    donne(bytes([0xFF, 0xD8, 0xFF, 0xE0]) + bytes(40), "faux.png")
    refus = attend(cdp, "document.getElementById('imageResultat').textContent.indexOf('Image refusée') === 0 && document.getElementById('imageResultat').textContent", 15)
    verifie((bool(refus), js("document.getElementById('imageImporter').disabled")), (True, True), "import PNG : fichier qui n'en est pas un refuse, bouton inactif")
    with cdp.condition:                     # le 400 du refus voulu ci-dessus n'est pas une erreur de la page
        cdp.evenements[:] = [e for e in cdp.evenements if "/images/analyse" not in str(e)]
    donne(png(8, 8), "sonde icone.png")
    ok = attend(cdp, "document.getElementById('imageResultat').textContent.indexOf('8 × 8') >= 0", 15)
    verifie((bool(ok), js("document.getElementById('imageImporter').disabled")), (True, True), "import PNG : dimensions affichees, bouton inactif sans origine ni licence")
    js("var o = document.getElementById('imageOrigine'); o.value = 'https://pictogrammers.com/'; o.dispatchEvent(new Event('input'))")
    js("var c = document.getElementById('imageLicence'); c.checked = true; c.dispatchEvent(new Event('change'))")
    verifie(js("document.getElementById('imageImporter').disabled"), False, "import PNG : bouton actif avec origine et licence")
    js("document.getElementById('imageImporter').click()")
    fait = attend(cdp, "document.getElementById('imageResultat').textContent.indexOf('Importée') === 0 && P2.images.indexOf('sonde-icone.png') >= 0", 20)
    dossier = banc.racine / "data/bureau/tasmota32s3-ecran-debits-pac"
    licence = banc.racine / "outils_docs/atelier_ecrans/images/tasmota32s3-bureau-ecran-debits-pac/sonde-icone.licence.txt"
    verifie((bool(fait), (dossier / "sonde-icone.png").is_file(), licence.is_file()), (True, True, True),
            "import PNG : ecrit dans la copie du depot, propose a l'objet image")
    (dossier / "sonde-icone.png").unlink()
    licence.unlink()
    js("chargeImages()")
