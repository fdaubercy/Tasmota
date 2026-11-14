"""Sonde Chrome de la page 7990 contre un serveur AVEC FAUX (icones Iconify, fournisseurs d'IA, carte muette) et un depot COPIE
(le vrai depot n'est jamais ecrit) : recherche d'icones, icone par etat, points chauds et apercu simule, ecriture et lien Build, assistant IA.

UTILISATION (a la main ; aucun pio, aucune carte, aucun reseau)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_visuels_page_chrome_faux.py
Code de sortie 0 = vert. Appelee aussi par test_atelier_visuels_page_chrome.py. Les attentes sont des CONDITIONS, jamais des durees ;
seul le Chrome lance ici est arrete.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre, tue_arbre   # noqa: E402

ECHECS = []
CUVE = "tasmota32s3-garage-capteurs-cuve-modbus"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)
    return ok


def condition(cdp, expression, delai=15):
    return attend(cdp, expression, delai) is True


def http(url, delai):
    limite = time.monotonic() + delai
    while time.monotonic() < limite:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                return r.read()
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(url)


# ---------------------------------------------------------------- serveur avec faux
def mode_faux(port, depot):
    import acces_web
    import atelier_visuels_ia as ia
    import atelier_visuels_icones_web as ico
    import atelier_visuels_web as avw
    import test_atelier_visuels_ecriture as te
    from http.server import ThreadingHTTPServer

    racine = te.copie(Path(depot), True)
    tmp = Path(depot).parent / "faux"
    tmp.mkdir(exist_ok=True)
    svgs = {"camera": "M4 4h16v16H4z", "camera-off": "M2 2l20 20", "fleur": "M1 1h4v4z"}
    licences = {"mdi": ("Apache-2.0", "https://x/mdi"), "cc": ("CC-BY-4.0", "https://x/cc"), "x": ("CC-BY-NC-4.0", "")}

    def ouvre(url, delai, maxi):
        if "horsligne" in url:
            raise ico.HorsLigne("Iconify injoignable (faux) : recherche en ligne indisponible")
        if "/search" in url:
            return json.dumps({"icons": ["mdi:camera", "mdi:camera-off", "cc:fleur", "x:sale"],
                               "collections": {k: {"license": {"spdx": v[0]}} for k, v in licences.items()}}).encode()
        if "/collections" in url:
            jeu = url.split("prefix=")[1]
            return json.dumps({jeu: {"license": {"spdx": licences[jeu][0], "url": licences[jeu][1]}, "author": {"name": "Auteur"}}}).encode()
        nom = url.rsplit("/", 1)[1][:-4]
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="{svgs[nom]}"/></svg>'.encode()

    class Faux(ia.Fournisseur):
        def __init__(self, id_, externe):
            super().__init__({})
            self.id, self.nom, self.externe, self.gratuit, self.cle_requise = id_, "Faux " + id_, externe, "gratuit", externe

        def demande(self, consigne, chemin_image, delai=600):
            (tmp / "ia.log").open("a").write(f"{self.id} {Path(chemin_image).stat().st_size}\n")
            return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50"><rect x="0" y="0" width="100" height="50" fill="#336699"/>'
                    '<rect x="10" y="10" width="30" height="20" fill="#cc9933"/><script>alert(1)</script></svg>')

    faux = {"local": Faux("local", False), "ext": Faux("ext", True)}

    def lecteur(env, chemin):
        f = tmp / "carte.json"
        return f.read_bytes() if f.is_file() else None

    acces = acces_web.Acces(port, True, "Atelier des visuels")
    srv = ThreadingHTTPServer(("127.0.0.1", port), avw.fabrique_gestionnaire(
        acces, racine, builds_en_cours=lambda: [x for x in [(tmp / "build").exists() and "pio"] if x], ouvre=ouvre, cache_icones=tmp / "cache",
        config_fichier=tmp / "config.json", fabrique_ia=lambda c, r: faux, lecteur=lecteur))
    srv.daemon_threads = True
    srv.serve_forever()


# ---------------------------------------------------------------- bloc 2 : icones
SVG_IMPORT = ("(function(){var d=new DataTransfer();d.items.add(new File(['<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 10 10\">"
              "<script>alert(1)</script><path d=\"M0 0h10v10z\"/></svg>'],'mon.svg',{type:'image/svg+xml'}));"
              "var i=document.getElementById('avi-fichier');i.files=d.files;i.dispatchEvent(new Event('change',{bubbles:true}));})()")


def cherche(cdp, mot):
    cdp.js("var q=document.getElementById('avi-q');q.value=%s;document.getElementById('avi-cherche').click()" % json.dumps(mot))


def sonde_icones(cdp, depot):
    js = cdp.js
    cherche(cdp, "camera")
    verifie(condition(cdp, "document.querySelectorAll('#avi-res button').length === 3"), True, "icones : 3 resultats, la licence NC est masquee")
    verifie(js("[].map.call(document.querySelectorAll('#avi-res button'),function(b){return b.textContent;})"),
            ["mdi:camera · Apache-2.0", "mdi:camera-off · Apache-2.0", "cc:fleur · CC-BY-4.0 ⚠"], "icones : licence affichee sur chaque resultat")
    js("document.querySelectorAll('#avi-res button')[0].click()")
    verifie(condition(cdp, "document.querySelector('#avi-prev path') && document.querySelector('#avi-prev path').getAttribute('d') === 'M4 4h16v16H4z'"), True, "icones : apercu du tracé choisi")
    verifie(js("/Apache-2.0/.test(document.getElementById('avi-info').textContent)"), True, "icones : licence de l'icone choisie")
    js("document.getElementById('avi-pose').click()")
    verifie(js("[AV.elements.length, AV.elements[0].type, AV.elements[0].style.icone_on.d, AV.selEl]"), [1, "voyant", "M4 4h16v16H4z", "v1"], "icones : pose comme voyant avec le tracé")
    verifie(js("document.querySelectorAll('#avc-g .av-v path').length"), 3, "icones : l'icone est dessinee dans le canevas (3 etats)")
    cherche(cdp, "camera")
    condition(cdp, "document.querySelectorAll('#avi-res button').length === 3")
    js("document.querySelectorAll('#avi-res button')[1].click()")
    condition(cdp, "document.querySelector('#avi-prev path').getAttribute('d') === 'M2 2l20 20'")
    js("document.querySelector('[data-avi-etat=icone_off]').click()")
    verifie(js("[AV.elements[0].style.icone_on.d, AV.elements[0].style.icone_off.d]"), ["M4 4h16v16H4z", "M2 2l20 20"], "icones : icone_off distincte de icone_on")
    # l'icone change avec l'etat simule
    lit = ("(function(){var g=document.querySelector('#avc-g .av-v');return [g.getAttribute('class'),"
           "getComputedStyle(g.querySelector('.s-on')).display,getComputedStyle(g.querySelector('.s-off')).display];})()")
    js("AV.sim.v1='on';AV.dessine()")
    verifie(js(lit), ["av-v on", "inline", "none"], "icones : etat ON simule, icone ON visible")
    js("AV.sim.v1='off';AV.dessine()")
    verifie(js(lit), ["av-v off", "none", "inline"], "icones : etat OFF simule, icone OFF visible")
    js("var t=document.getElementById('avi-taille');t.value=40;t.dispatchEvent(new Event('input',{bubbles:true}))")
    verifie(js("AV.elements[0].style.taille"), 40, "icones : taille reglable")
    # persistance et revalidation
    js("localStorage.setItem('av.elements.'+AV.carte, JSON.stringify([{id:'v1',type:'voyant',x:5,y:5,source:{},style:{icone_on:{w:24,h:24,d:'M0 0<script>'},couleur_on:'url(x)'}},{id:'<b>',type:'valeur',x:1,y:1}]));AV.charge()")
    verifie(js("[AV.elements.length, !!AV.elements[0].style.icone_on, !!AV.elements[0].style.couleur_on]"), [1, False, False], "icones : elements du localStorage revalides")
    js("AV.elements=[];AV.sauveEls();AV.dessine()")
    # hors ligne
    cherche(cdp, "horsligne")
    verifie(condition(cdp, "/injoignable/.test(document.getElementById('avi-info').textContent) && document.getElementById('avi-info').className === 'mauvais'"), True, "icones : hors ligne = message clair")
    # garde : permissive, puis attribution avec confirmation
    cherche(cdp, "camera")
    condition(cdp, "document.querySelectorAll('#avi-res button').length === 3")
    js("document.querySelectorAll('#avi-res button')[0].click()")
    condition(cdp, "/Apache/.test(document.getElementById('avi-info').textContent)")
    js("document.getElementById('avi-garde').click()")
    ico = Path(depot) / "outils_docs" / "visuels_accueil" / "icones"
    verifie(condition(cdp, "/Gardée/.test(document.getElementById('avi-info').textContent)"), True, "icones : icone permissive gardee")
    verifie((ico / "mdi-camera.svg").is_file() and "mdi-camera.svg" in (ico / "LICENCES.md").read_text(encoding="utf-8"), True, "icones : fichier et ligne de licence au depot copie")
    js("document.querySelectorAll('#avi-res button')[2].click()")
    condition(cdp, "!document.getElementById('avi-attr-l').hidden")
    js("document.getElementById('avi-garde').click()")
    verifie(js("/Cochez/.test(document.getElementById('avi-info').textContent)"), True, "icones : attribution sans confirmation refusee par la page")
    verifie((ico / "cc-fleur.svg").exists(), False, "icones : rien ecrit sans confirmation")
    js("document.getElementById('avi-attr').click();document.getElementById('avi-garde').click()")
    verifie(condition(cdp, "/Gardée/.test(document.getElementById('avi-info').textContent)"), True, "icones : attribution confirmee, gardee")
    # import d'un .svg du PC, nettoye par le serveur
    js(SVG_IMPORT)
    verifie(condition(cdp, "document.querySelector('#avi-prev path') && document.querySelector('#avi-prev path').getAttribute('d') === 'M0 0h10v10z'"), True, "icones : .svg du PC importe, tracé retenu")
    verifie(js("/mon\\.svg/.test(document.getElementById('avi-info').textContent) && !window.__pwn"), True, "icones : import nomme, script ignore")



# ---------------------------------------------------------------- bloc 3 : points chauds
PT = ("window.__pt=function(t,x,y){var s=document.getElementById('avf-canevas'),b=s.getBoundingClientRect(),X=b.left+x*b.width/AV.larg,Y=b.top+y*b.height/AV.haut;"
      "var tg=t==='pointerdown'?document.elementFromPoint(X,Y):s;(tg||s).dispatchEvent(new PointerEvent(t,{clientX:X,clientY:Y,pointerId:1,bubbles:true}));};")


def champ(cdp, ident, valeur):
    cdp.js("(function(){var e=document.getElementById(%s);e.value=%s;e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));})()"
           % (json.dumps(ident), json.dumps(str(valeur))))


def sonde_points(cdp):
    js = cdp.js
    js("AV.elements=[];AV.sim={};AV.selEl=null;AV.sauveEls();AV.dessine()")
    verifie(condition(cdp, "document.getElementById('avp-note').textContent.length > 0"), True, "points : sans route /sources, saisie a la main annoncee")
    js(PT)
    js("document.querySelector('[data-avp-outil=voyant]').click()")
    js("__pt('pointerdown',144,81);__pt('pointerup',144,81)")
    verifie(js("[AV.elements.length, AV.elements[0].type, AV.elements[0].x, AV.elements[0].y, AV.selEl, document.getElementById('avp-panel').hidden]"),
            [1, "voyant", 144, 81, "v1", False], "points : un voyant pose au clic, selectionne, panneau ouvert")
    verifie(js("AV.elements[0].source"), {"type": "relais", "n": 1}, "points : source relais par defaut")
    champ(cdp, "avp-n", 3)
    verifie(js("AV.elements[0].source.n"), 3, "points : numero de relais saisi")
    champ(cdp, "avp-stype", "mesure")
    champ(cdp, "avp-chemin", "Switch1")
    verifie(js("AV.elements[0].source"), {"type": "mesure", "chemin": ["Switch1"]}, "points : entree (mesure) choisie")
    # valeur
    js("document.querySelector('[data-avp-outil=valeur]').click()")
    js("__pt('pointerdown',288,81);__pt('pointerup',288,81)")
    champ(cdp, "avp-unite", "cm")
    verifie(js("[AV.elements[1].id, AV.elements[1].type, AV.elements[1].source.chemin, AV.elements[1].style.unite]"), ["n1", "valeur", ["ANALOG", "A1"], "cm"], "points : valeur posee, unite")
    verifie(js("document.querySelector('#avc-g [data-el=n1] text').textContent"), "0 cm", "points : la valeur est dessinee avec son unite")
    # liaison en deux clics
    js("document.querySelector('[data-avp-outil=liaison]').click()")
    js("__pt('pointerdown',50,200);__pt('pointerup',50,200);__pt('pointerdown',300,220);__pt('pointerup',300,220)")
    verifie(js("[AV.elements[2].type, AV.elements[2].x, AV.elements[2].y, AV.elements[2].x2, AV.elements[2].y2, AV.elements[2].source]"),
            ["liaison", 50, 200, 300, 220, {"type": "modbus_serie", "seuil_s": 30}], "points : liaison posee en deux clics, seuil par defaut")
    verifie(js("document.querySelectorAll('#avc-g .avp-poignee').length"), 2, "points : deux poignees pour la liaison selectionnee")
    champ(cdp, "avp-stype", "modbus_esclave")
    verifie(js("/ModBus/.test(document.getElementById('avp-alerte').textContent)"), True, "points : identifiant d'esclave manquant signale")
    champ(cdp, "avp-id", 3)
    champ(cdp, "avp-seuil", 90)
    verifie(js("AV.elements[2].source"), {"type": "modbus_esclave", "seuil_s": 90, "id": 3}, "points : liaison vers un esclave ModBus, seuil_s")
    verifie(js("document.getElementById('avp-alerte').textContent"), "", "points : plus d'alerte")
    js("__pt('pointerdown',300,220);__pt('pointermove',200,150);__pt('pointerup',200,150)")
    verifie(js("[AV.elements[2].x2, AV.elements[2].y2]"), [200, 150], "points : poignee d'arrivee deplacee")
    # deplacement du voyant
    js("__pt('pointerdown',144,81);__pt('pointermove',184,101);__pt('pointerup',184,101)")
    verifie(js("[AV.elements[0].x, AV.elements[0].y, JSON.parse(localStorage.getItem('av.elements.'+AV.carte))[0].x]"), [184, 101, 184], "points : voyant deplace a la souris et enregistre")
    # apercu simule
    js("document.getElementById('avp-apercu').click()")
    js("__pt('pointerdown',184,101);__pt('pointerup',184,101)")
    verifie(js("[AV.sim.v1, document.querySelector('#avc-g [data-el=v1]').getAttribute('class')]"), ["on", "av-v on"], "apercu : un clic bascule le voyant en ON")
    js("__pt('pointerdown',184,101);__pt('pointerup',184,101)")
    verifie(js("document.querySelector('#avc-g [data-el=v1]').getAttribute('class')"), "av-v off", "apercu : second clic, OFF")
    js("document.getElementById('avp-apercu').click()")
    js("AV.selEl='l1';AV.dessine()")
    champ(cdp, "avp-etat", "muette")
    verifie(js("document.querySelector('#avc-g [data-el=l1]').getAttribute('class')"), "av-l muette", "apercu : liaison muette (etat simule du panneau)")
    champ(cdp, "avp-etat", "active")
    verifie(js("document.querySelector('#avc-g [data-el=l1]').getAttribute('class')"), "av-l active", "apercu : liaison active")
    # fleches et suppression au clavier
    js("AV.selEl='v1';AV.dessine();document.activeElement.blur&&document.activeElement.blur();document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}))")
    verifie(js("AV.elements[0].x"), 185, "points : fleche droite, 1 px")
    js("document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'Delete',bubbles:true}))")
    verifie(js("[AV.elements.length, AV.elements.some(function(e){return e.id==='v1';})]"), [2, False], "points : Suppr retire l'element")
    js("document.querySelector('[data-avp-outil=voyant]').click()")
    js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
    verifie(js("document.querySelector('[data-avp-outil=voyant]').getAttribute('aria-pressed')"), "false", "points : Echap quitte l'outil")


# ---------------------------------------------------------------- bloc 4 : ecriture, suivi, lien Build
def sonde_ecriture(cdp, depot):
    js = cdp.js
    faux = Path(depot).parent / "faux"
    dossier = Path(depot) / "data" / "garage" / "tasmota32s3-capteurs-cuve-modbus"
    visuels = list(Path(depot).glob("data/**/visuel.json"))
    verifie(visuels, [], "ecriture : aucun visuel.json au depot copie au depart")
    verifie(condition(cdp, "/Pas de visuel/.test(document.getElementById('ave-badge').textContent)"), True, "suivi : badge « pas de visuel » au depart")
    js("document.getElementById('av-ecrire').click()")
    verifie(condition(cdp, "/Gardez d/.test(document.getElementById('ave-msg').textContent)"), True, "ecriture : sans fond garde, la fenetre le demande")
    js("document.getElementById('ave-ferme').click()")
    verifie(js("document.getElementById('ave-dlg').hidden"), True, "ecriture : la fenetre se ferme")
    js("AV.formes.push(AV_FORMES.normalise({id:AV.idSuivant(),type:'rect',x:10,y:10,l:200,h:120,fill:'#336699'}));AV.commit()")
    condition(cdp, "!document.getElementById('av-garder').disabled")
    js("document.getElementById('av-garder').click()")
    verifie(condition(cdp, "!!AV.fond"), True, "ecriture : fond garde")
    js("document.getElementById('av-ecrire').click()")
    verifie(condition(cdp, "document.querySelectorAll('#ave-diff details').length >= 3 && !document.getElementById('ave-ok').hidden"), True, "ecriture : diff montre (fichiers a ecrire)")
    verifie(js("[].map.call(document.querySelectorAll('#ave-diff summary'),function(s){return s.textContent;}).filter(function(t){return /visuel\\.(json|svg)/.test(t);}).length"), 2, "ecriture : visuel.json et visuel.svg dans le diff")
    verifie(list(Path(depot).glob("data/**/visuel.json")), [], "ecriture : rien n'est ecrit avant la confirmation")
    # build en cours : refus affiche
    (faux / "build").write_text("x")
    js("document.getElementById('ave-ok').click()")
    verifie(condition(cdp, "/Refusé/.test(document.getElementById('ave-msg').textContent) && document.getElementById('ave-msg').className === 'mauvais'"), True, "ecriture : refus clair pendant un build")
    verifie(list(Path(depot).glob("data/**/visuel.json")), [], "ecriture : build en cours, rien d'ecrit")
    (faux / "build").unlink()
    js("document.getElementById('ave-ok').click()")
    verifie(condition(cdp, "/Écrit :/.test(document.getElementById('ave-msg').textContent)", 90), True, "ecriture : confirmation, fichiers ecrits")
    ecrits = list(Path(depot).glob("data/**/visuel.json"))
    verifie(len(ecrits), 1, "ecriture : visuel.json au depot copie")
    desc = json.loads(ecrits[0].read_text(encoding="utf-8"))
    verifie((desc["version"], desc["fond"]["type"], [e["id"] for e in desc["elements"]]), (1, "svg", ["n1", "l1"]), "ecriture : description = fond et elements de la page")
    verifie((ecrits[0].parent / "visuel.svg").is_file(), True, "ecriture : visuel.svg ecrit")
    verifie(js("document.getElementById('ave-lien').getAttribute('href')"),
            js("'http://' + location.hostname + ':7700/?env=' + encodeURIComponent(AV.env) + '&depuis=visuel&fichiers=visuel.json,visuel.svg&redemarrer=1'"), "ecriture : lien Televerser vers la page Build")
    verifie(js("document.getElementById('ave-lien').hidden"), False, "ecriture : le lien est visible apres l'ecriture")
    verifie(condition(cdp, "/différente/.test(document.getElementById('ave-badge').textContent)"), True, "suivi : carte differente apres l'ecriture")
    (faux / "carte.json").write_bytes(ecrits[0].read_bytes())
    js("AV.majSuivi()")
    verifie(condition(cdp, "/identique/.test(document.getElementById('ave-badge').textContent)"), True, "suivi : carte identique quand elle porte le meme fichier")
    js("document.getElementById('ave-ferme').click()")
    # description invalide : le serveur refuse, la page montre le motif
    js("AV.elements.push({id:'v9',type:'voyant',x:5,y:5,source:{type:'relais'},style:{}});AV.dessine()")
    js("document.getElementById('av-ecrire').click()")
    verifie(condition(cdp, "document.getElementById('ave-msg').className === 'mauvais' && /source\\.n/.test(document.getElementById('ave-msg').textContent)"), True, "ecriture : description invalide, motif du serveur affiche")
    js("document.getElementById('ave-ferme').click();AV.elements.pop();AV.sauveEls();AV.dessine()")


# ---------------------------------------------------------------- bloc 5 : assistant IA
def sonde_ia(cdp, depot, fabrique):
    js = cdp.js
    faux = Path(depot).parent / "faux"
    verifie(condition(cdp, "document.querySelectorAll('#avia-four option').length === 2"), True, "ia : les deux procedes proposes")
    js("document.getElementById('avia-four').value='ext';document.getElementById('avia-four').dispatchEvent(new Event('change',{bubbles:true}))")
    verifie(js("/Faux ext/.test(document.getElementById('avia-avert').textContent) && /externe/.test(document.getElementById('avia-avert').textContent)"), True, "ia : l'avertissement nomme le service externe")
    verifie(js("document.getElementById('avia-envoi').disabled"), True, "ia : envoi inactif sans photo")
    js(fabrique)
    condition(cdp, "!!AV.src")
    js("var c=document.getElementById('avia-consigne');c.value='dessine la facade';c.dispatchEvent(new Event('input',{bubbles:true}))")
    verifie(js("document.getElementById('avia-envoi').disabled"), True, "ia : service externe, envoi inactif sans confirmation")
    js("document.getElementById('avia-confirme').click()")
    verifie(js("document.getElementById('avia-envoi').disabled"), False, "ia : confirmation cochee, envoi actif")
    js("document.getElementById('avia-envoi').click()")
    verifie(condition(cdp, "!document.getElementById('avia-ouvre').hidden"), True, "ia : dessin recu")
    verifie(js("[document.getElementById('avia-confirme').checked, document.getElementById('avia-envoi').disabled]"), [False, True], "ia : la confirmation est a refaire a chaque envoi")
    verifie(js("/Envois aujourd/.test(document.getElementById('avia-quota').textContent) && /1/.test(document.getElementById('avia-quota').textContent)"), True, "ia : compteur de quota mis a jour")
    verifie(sum(1 for ligne in (faux / "ia.log").read_text().splitlines() if ligne.startswith("ext ")), 1, "ia : le faux fournisseur a recu exactement un envoi")
    n0 = js("AV.formes.length")
    js("document.getElementById('avia-ouvre').click()")
    verifie(js("[AV.formes.length - %s, AV.formes.slice(-2).map(function(f){return f.fill;}), Math.round(AV.formes[AV.formes.length-1].x)]" % n0), [2, ["#336699", "#cc9933"], 48],
            "ia : le dessin s'ouvre dans l'editeur (rect mis a l'echelle, SVG nettoye)")
    js("AV.annule()")
    verifie(js("AV.formes.length"), n0, "ia : l'ajout s'annule en une etape")
    # procede local : pas de confirmation requise
    js("document.getElementById('avia-four').value='local';document.getElementById('avia-four').dispatchEvent(new Event('change',{bubbles:true}))")
    verifie(js("[document.getElementById('avia-conf-l').hidden, document.getElementById('avia-envoi').disabled, document.getElementById('avia-cle-b').hidden]"), [True, False, True],
            "ia : procede local, pas de confirmation ni de cle")
    # cle : envoyee puis effacee du champ, jamais dans le DOM ni le stockage
    js("document.getElementById('avia-four').value='ext';document.getElementById('avia-four').dispatchEvent(new Event('change',{bubbles:true}))")
    js("var k=document.getElementById('avia-cle');k.value='sk-SECRET-987654321';document.getElementById('avia-cle-ok').click()")
    verifie(condition(cdp, "/se termine par/.test(document.getElementById('avia-cle-etat').textContent)"), True, "ia : cle enregistree, seule la fin est montree")
    verifie(js("[document.getElementById('avia-cle').value, document.documentElement.outerHTML.indexOf('SECRET-987654321') < 0, JSON.stringify(localStorage).indexOf('SECRET') < 0]"),
            ["", True, True], "ia : la cle n'est ni dans le champ, ni dans le DOM, ni dans le stockage")
    verifie(js("document.getElementById('avia-cle').type"), "password", "ia : champ de cle masque")

# ---------------------------------------------------------------- lancement
def lance(cdp, t):
    """Demarre le serveur a faux (depot copie dans t/depot), y amene `cdp`, joue les sondes. Rend la liste des echecs."""
    depot, port = t / "depot", port_libre()
    serveur = subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve()), "--faux", str(port), str(depot)],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        http(f"http://127.0.0.1:{port}/envs", 90)
        cdp.appel("Page.navigate", url=f"http://127.0.0.1:{port}/")
        attend(cdp, "document.readyState === 'complete' && !!window.AV && !!AV.env", 20)
        cdp.js("localStorage.clear()")
        cdp.js("AV.env = AV.carte = %s; document.getElementById('av-carte').value = %s; AV.charge()" % (json.dumps(CUVE), json.dumps(CUVE)))
        sonde_icones(cdp, depot)
        sonde_points(cdp)
        sonde_ecriture(cdp, depot)
        import test_atelier_visuels_page_chrome as principal
        sonde_ia(cdp, depot, principal.FABRIQUE)
        verifie([e for e in cdp.erreurs() if "horsligne" not in e and "/sources?" not in e and "/ecriture/" not in e], [], "faux : aucune erreur dans la console de la page")
    finally:
        tue_arbre(serveur)
    return ECHECS


def main():
    t = Path(tempfile.mkdtemp(prefix="sonde_atelier_visuels_page_faux_"))
    chrome = None
    try:
        exe = next((c for c in CHROMES if c.is_file()), None)
        cdp_port = port_libre()
        chrome = subprocess.Popen([str(exe), "--headless=new", f"--remote-debugging-port={cdp_port}", "--remote-allow-origins=*",
                                   f"--user-data-dir={t / 'profil'}", "--no-first-run", "--no-default-browser-check",
                                   "--disable-extensions", "--window-size=1400,1000", "about:blank"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cibles = json.loads(http(f"http://127.0.0.1:{cdp_port}/json/list", 20))
        cdp = Cdp(next(c for c in cibles if c.get("type") == "page")["webSocketDebuggerUrl"])
        for d in ("Runtime.enable", "Log.enable", "Page.enable"):
            cdp.appel(d)
        lance(cdp, t)
    finally:
        tue_arbre(chrome)
        shutil.rmtree(t, ignore_errors=True)
    print("VERT" if not ECHECS else f"ROUGE : {ECHECS}")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    if len(sys.argv) > 3 and sys.argv[1] == "--faux":
        sys.exit(mode_faux(int(sys.argv[2]), sys.argv[3]))
    sys.exit(main())
