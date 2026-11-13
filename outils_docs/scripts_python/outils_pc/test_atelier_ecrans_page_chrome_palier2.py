"""Sondes Chrome des objets du palier 2 (A14) et de la barre de navigation (A17) de l'atelier des ecrans.

Pas un banc a lancer seul : appelees par test_atelier_ecrans_page_chrome.py::main (meme Chrome, meme copie du depot),
qui leur passe son `verifie` et son `instantane`. Module separe pour garder la sonde sous 500 lignes.
"""
import json
import struct
import zlib

from test_build_page_chrome import attend      # noqa: E402

PAGES_JSONL = "var c = (E.fichiers.filter(function(f){return f.nom==='pages.jsonl'})[0]||{}).contenu || ''; "


def png_1x1():
    """Un vrai PNG 1 x 1 (le navigateur le decode : naturalWidth = 1)."""
    def bloc(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + bloc(b"IDAT", zlib.compress(b"\x00\xff\x00\x00")) + bloc(b"IEND", b""))


def erreurs_console(cdp):
    return [e for e in cdp.erreurs() if "carte-inconnue" not in e and "temoin_sonde" not in e]


def sonde_palier2(cdp, banc, verifie, instantane):
    """Objets du palier 2 (A14) : palette, dessin approche (PNG de la carte, QR code par qr-code-styling), editeur
    d'options, image choisie dans la liste, QR code carre, description valide, rien d'ecrit."""
    js = cdp.js
    (banc.racine / "data/bureau/tasmota32s3-ecran-debits-pac/pompe.png").write_bytes(png_1x1())
    avant = instantane(banc.racine)
    js("chargeImages(); E.page = 1; E.sel = null; dessineTout()")
    attend(cdp, "P2.images.length === 1", 10)
    verifie(js("document.querySelectorAll('#palette > div').length"), 12, "palette : 7 types du palier 1 + 5 du palier 2")
    js("['img','dropdown','switch','roller','qrcode'].forEach(function(t, i){ ajouteObjet(t, 16 + 150 * i, 300); })")
    verifie(js("['img','dropdown','switch','roller','qrcode'].map(function(t){ return document.querySelectorAll('#ecranCarte .t-' + t).length; }).join()"),
            "1,1,1,1,1", "palier 2 : un objet de chaque type dessine")
    verifie((js("!!document.querySelector('#ecranCarte .t-qrcode svg')"), js("!!document.querySelector('#ecranCarte .t-switch .bouton')"),
             js("document.querySelector('#ecranCarte .t-roller').children.length"),
             js("document.querySelector('#ecranCarte .t-dropdown').textContent")), (True, True, 3, "Option 1▾"),
            "dessin : QR code par qr-code-styling, bouton d'interrupteur, 3 lignes de roue, option choisie de la liste")
    js("var o = E.desc.objets.filter(function(x){ return x.type === 'img'; })[0]; E.sel = [o.page, o.id]; dessineTout()")
    opts = js("Array.from(document.querySelectorAll('#proprietes select[aria-label=Image] option')).map(function(x){ return x.value; }).join()")
    verifie(opts, "tasmota_logo,A:sd/images/PNG/pompe.png", "image : logo Tasmota ou PNG du dossier de la carte")
    js("var s = document.querySelector('#proprietes select[aria-label=Image]'); s.value = 'A:sd/images/PNG/pompe.png'; s.onchange()")
    verifie(attend(cdp, "var i = document.querySelector('#ecranCarte .t-img img'); i && i.complete && i.naturalWidth", 10), 1,
            "image : PNG de la carte affiche (GET /image)")
    js("var o = E.desc.objets.filter(function(x){ return x.type === 'dropdown'; })[0]; E.sel = [o.page, o.id]; dessineTout()")
    js("var t = document.querySelector('#proprietes textarea.lignes'); t.value = ' Auto\\n\\nMarche \\r\\nArret'; t.onchange()")
    verifie(js("E.desc.objets.filter(function(x){ return x.type === 'dropdown'; })[0].attributs.options"), "Auto\nMarche\nArret",
            "options : une par ligne, lignes vides et blancs retires")
    js("var o = E.desc.objets.filter(function(x){ return x.type === 'qrcode'; })[0]; modifie(function(){ var c = E.desc.objets.filter(function(x){ return x.type === 'qrcode'; })[0]; c.l = 200; borne(c); })")
    verifie(js("var o = E.desc.objets.filter(function(x){ return x.type === 'qrcode'; })[0]; [o.l, o.h].join()"), "200,200", "QR code : reste carre")
    gen = attend(cdp, PAGES_JSONL + "c.indexOf('\"qr_size\":200') >= 0 && c", 15)
    verifie((bool(gen), js("E.erreurs.join(' | ')")), (True, ""), "apercu : description valide, qr_size = l dans le pages.jsonl genere")
    verifie(instantane(banc.racine) == avant, True, "palier 2 : rien n'est ecrit")
    verifie(erreurs_console(cdp), [], "palier 2 : aucune erreur console")


def sonde_navigation(cdp, banc, verifie, instantane):
    """Barre de navigation (A17) : activee par le panneau de la page 0, boutons dessines aux places calculees par Python
    (atelier_ecrans_navigation.boutons), titre hors plan de base compte comme Python, une page sortie par sa case,
    nouvel objet de la page 0 hors des ids reserves."""
    import atelier_ecrans_navigation as nav
    js = cdp.js
    avant = instantane(banc.racine)
    js("E.page = 0; E.sel = null; dessineTout()")
    js("var c = document.querySelector('#proprietes input[aria-label=\"Barre de navigation construite\"]'); c.checked = true; c.onchange()")
    js("modifie(function(){ pageDesc(1).titre = 'Débits \\uD83D\\uDCA7'; })")      # goutte d'eau : 2 unites UTF-16, 1 caractere
    desc = json.loads(js("JSON.stringify(E.desc)"))
    attendu = [[o["id"], o["x"], o["y"], o["l"], o["h"], o["attributs"]["text"]] for o in nav.boutons(desc)]
    vu = json.loads(js("JSON.stringify(Array.from(document.querySelectorAll('#ecranCarte .o.nav')).map(function(d){ return ["
                       "+d.dataset.id, parseInt(d.style.left), parseInt(d.style.top), parseInt(d.style.width), parseInt(d.style.height), d.textContent]; }))"))
    verifie((len(attendu) > 0, vu), (True, attendu), "barre : boutons dessines aux places calculees par Python (titre avec emoji compris)")
    js("E.page = 2; E.sel = null; dessineTout()")
    js("var c = document.querySelector('#proprietes input[aria-label=\"Dans la barre de navigation\"]'); c.checked = false; c.onchange()")
    verifie((js("pageDesc(2).menu"), js("document.querySelectorAll('#ecranCarte .o.nav').length"), js("!!document.querySelector('#ecranCarte .o.nav[data-id=\"202\"]')")),
            (False, len(attendu) - 1, False), "page sortie de la barre : un bouton de moins")
    # temoin : un objet d'id 200 sur la page 0 ; sans la borne, le suivant serait 201 (id de la barre)
    i = js("E.desc.objets.push({id: 200, page: 0, type: 'label', x: 0, y: 0, l: 9, h: 9, attributs: {}}); "
           "E.page = 0; var i = nouvelId(0); E.desc.objets.pop(); i")
    verifie(isinstance(i, int) and i < 200, True, f"nouvel objet de la page 0 apres l'id 200 : {i}, hors de 201 a 254")
    gen = attend(cdp, PAGES_JSONL + "c.indexOf('\"id\":201') >= 0 && c", 15)
    verifie((bool(gen), js("E.erreurs.join(' | ')")), (True, ""), "apercu : barre dans le pages.jsonl genere, description valide")
    verifie(instantane(banc.racine) == avant, True, "barre : rien n'est ecrit")
    verifie(erreurs_console(cdp), [], "barre : aucune erreur console")
