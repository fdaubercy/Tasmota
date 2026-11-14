"""Sonde Chrome de la page de l'atelier des visuels (atelier_visuels_page.PAGE) : depot d'une image fabriquee dans le navigateur,
recadrage, rotation, les deux modes de fond, poids affiche, theme, garde du fond (GET /fond == blob).

UTILISATION (a la main ; aucun pio, aucune carte, aucune photo reelle)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_visuels_page_chrome.py
Code de sortie 0 = vert. Serveur reel dans un processus fils (depot reel en lecture seule : rien n'est ecrit). Les attentes sont des
CONDITIONS, jamais des durees ; les Chrome sont arretes et on verifie qu'aucun `sonde_atelier_visuels_page_*` ne survit.
"""

import json
import re
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
PREFIXE = "sonde_atelier_visuels_page_"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)
    return ok


def mode_serveur(port):
    import atelier_visuels_web as avw
    sys.argv = ["atelier_visuels_web.py", "--http", str(port), "--local", "--sans-navigateur"]
    return avw.principal()


def http(url, delai):
    limite = time.monotonic() + delai
    while time.monotonic() < limite:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                return r.read()
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(url)


# Image de test fabriquee dans le navigateur : 600 x 300, moitie gauche rouge, droite bleue, un carre jaune a gauche.
FABRIQUE = """(function(){var c=document.createElement('canvas');c.width=600;c.height=300;var x=c.getContext('2d');
x.fillStyle='#d03030';x.fillRect(0,0,300,300);x.fillStyle='#3050d0';x.fillRect(300,0,300,300);x.fillStyle='#f0d020';x.fillRect(20,20,80,80);
return new Promise(function(ok){c.toBlob(function(b){var f=new File([b],'essai.png',{type:'image/png'});var d=new DataTransfer();d.items.add(f);
var i=document.getElementById('av-fichier');i.files=d.files;i.dispatchEvent(new Event('change',{bubbles:true}));ok('ok');},'image/png');});})()"""
SVG_SANS_DIMENSIONS = ("(function(){var d=new DataTransfer();d.items.add(new File(['<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"0\" height=\"0\"></svg>'],'v.svg',{type:'image/svg+xml'}));"
                       "var i=document.getElementById('av-fichier');i.files=d.files;i.dispatchEvent(new Event('change',{bubbles:true}));})()")
FICHIER_GROS = ("(function(){var d=new DataTransfer();d.items.add(new File([new Uint8Array(31*1048576)],'gros.png',{type:'image/png'}));"
                "var i=document.getElementById('av-fichier');i.files=d.files;i.dispatchEvent(new Event('change',{bubbles:true}));})()")
# POST /fond retenu jusqu'a __lache() : la reponse arrive apres un changement de carte
POST_RETENU = ("window.__lache = null; (function(){var f=window.fetch;window.fetch=function(u,o){var p=f.apply(this,arguments);"
               "if(o&&o.method==='POST'&&String(u).indexOf('/fond')===0)return p.then(function(r){return new Promise(function(ok){window.__lache=function(){ok(r);};});});return p;};})()")
CONTRASTE = r"""(function(){function lum(c){var m=c.match(/[\d.]+/g).map(Number).slice(0,3).map(function(x){x/=255;return x<=0.03928?x/12.92:Math.pow((x+0.055)/1.055,2.4);});
  return 0.2126*m[0]+0.7152*m[1]+0.0722*m[2];}
  function ratio(q){var s=getComputedStyle(document.querySelector(q)),a=lum(s.color),b=lum(s.backgroundColor);return (Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);}
  var r=getComputedStyle(document.documentElement);
  return {theme:document.documentElement.getAttribute('data-theme'),ac:r.getPropertyValue('--ac').trim()===r.getPropertyValue('--acc').trim()&&r.getPropertyValue('--ac').trim()!=='',
    ratios:['#av-fond-plat','#av-garder','[data-avf-outil][aria-pressed=true]'].map(ratio)};})()"""
TOUCHE = "document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',shiftKey:%s,bubbles:true}))"
POISON = r"""(function(){var e=AV.env,a=[];for(var i=1;i<=600;i++)a.push({id:i,type:'rect',x:i%50,y:i%40,l:20,h:10,fill:'#112233'});
  a[0]={id:1,type:'gabarit',gabarit:'numero',x:10,y:10,l:30,h:20,fill:'url(javascript:alert(1))',texte:'</script><b x="1">&amp;'};
  a[1]={id:2,type:'rect',x:'a',y:1,l:20,h:10,fill:'#abcdef'};
  localStorage.setItem('av.formes.'+e,JSON.stringify(a));localStorage.setItem('av.rec.'+e,JSON.stringify({x:1e9,y:-5,w:1,h:1,r:1e9}));
  localStorage.setItem('av.env',e);return e;})()"""
MOTS_SANS_ACCENT = re.compile(r"Facade|Retablir|Arriere-plan|Cheminee|Numero|Photo chargee|Selection|Fenetre|Boite aux|refuse :|Fond garde|a venir|Element<|"
                              r"zone a effacer|gardee en photo|Aimantation a ")


def recharge(cdp, port):
    cdp.js("window.__ancien = 1")
    cdp.appel("Page.navigate", url=f"http://127.0.0.1:{port}/")
    return condition(cdp, "!window.__ancien && document.readyState === 'complete' && !!window.AV && !!AV.env", 20)


BLOB_ENVOYE = "window.__blob = null; (function(){var f=window.fetch;window.fetch=function(u,o){if(o&&o.body)window.__blob=o.body;return f.apply(this,arguments);};})()"
COMPARE = ("(async function(){var b=window.__blob,m=new Uint8Array(await b.arrayBuffer());"
           "var q=await fetch('/fond?env='+encodeURIComponent(AV.env)+'&empreinte='+AV.fond.empreinte);"
           "var s=new Uint8Array(await q.arrayBuffer());var egal=s.length===m.length;for(var i=0;egal&&i<s.length;i++)if(s[i]!==m[i])egal=false;"
           "return [q.status,egal,AV.fond.octets===m.length,AV.fond.type];})()")
GLISSE = """(function(){var c=document.getElementById('av-crop'),b=c.getBoundingClientRect();
  var ev=function(t,x,y){c.dispatchEvent(new PointerEvent(t,{clientX:b.left+x*b.width,clientY:b.top+y*b.height,pointerId:1,bubbles:true}));};
  c.setPointerCapture=function(){};ev('pointerdown',1,1);ev('pointermove',0.5,1);ev('pointerup',0.5,1);})()"""
SOURIS = """(function(){var c=document.getElementById('avf-canevas');c.setPointerCapture=function(){};
  window.__souris=function(t,x,y){var b=c.getBoundingClientRect();var X=b.left+x*b.width,Y=b.top+y*b.height;(t==='pointerdown'?document.elementFromPoint(X,Y):c).dispatchEvent(new PointerEvent(t,{clientX:X,clientY:Y,pointerId:1,bubbles:true}));};})()"""
POSE_SVG = ("(async function(){var r=await fetch('/fond?env='+encodeURIComponent(AV.env)+'&type=svg',{method:'POST',headers:{'X-Atelier-Visuels':'1'},body:AV.svg()});"
            "return r.status;})()")
FICHIER_TEXTE = ("(function(){var d=new DataTransfer();d.items.add(new File(['x'],'a.txt',{type:'text/plain'}));"
                 "var i=document.getElementById('av-fichier');i.files=d.files;i.dispatchEvent(new Event('change',{bubbles:true}));})()")


def condition(cdp, expression, delai=15):
    return attend(cdp, expression, delai) is True


def sonde(cdp, port):
    js = cdp.js
    verifie(js("document.title"), "Atelier des visuels", "titre de la page")
    verifie(js("document.querySelectorAll('main > div').length"), 3, "trois colonnes")
    verifie(condition(cdp, "document.querySelectorAll('#av-carte option').length > 0"), True, "cartes chargees dans le select")
    verifie(js("document.querySelectorAll('#av-carte optgroup').length > 0"), True, "cartes groupees par lieu")
    verifie(js("[document.getElementById('av-export').disabled, document.getElementById('av-ecrire').disabled]"), [False, True],
            "Exporter actif, Écrire encore inactif")

    # theme : le clic bascule data-theme et change le fond de la page
    lit = "[document.documentElement.getAttribute('data-theme'), getComputedStyle(document.body).backgroundColor]"
    avant = js(lit)
    js("document.getElementById('av-theme').click()")
    apres = js(lit)
    verifie((avant[0] != apres[0], avant[1] != apres[1], apres[0] in ("sombre", "clair")), (True, True, True), "theme : le clic bascule data-theme et le fond")
    verifie(js("localStorage.getItem('atelier-visuels-theme')"), apres[0], "theme memorise dans localStorage")

    # dessin a plat sans forme : poids affiche, mais rien a garder
    verifie(condition(cdp, "document.getElementById('av-poids').textContent.indexOf('Ko') > 0", 10), True, "mode dessin : poids affiche (depuis AV.svg)")
    verifie(js("document.getElementById('av-garder').disabled"), True, "dessin a plat sans forme : Garder ce fond inactif")

    # accessibilite : import au clavier, noms accessibles, label du curseur
    verifie(js("(function(){var i=document.getElementById('av-fichier'),b=document.getElementById('av-importe'),n=0;"
               "i.click=function(){n++;};if(b)b.click();return [i.hasAttribute('hidden'),!!b&&b.tagName==='BUTTON',n];})()"), [False, True, 1],
            "import de photo : bouton reel qui declenche l'input, input sans hidden")
    verifie(js("['av-crop','avf-canevas'].map(function(i){var e=document.getElementById(i);return !!e&&!!e.getAttribute('aria-label')&&!!e.getAttribute('role');})"),
            [True, True], "aria-label et role sur le recadrage et sur le canevas")
    verifie(js("document.getElementById('avf-canevas').getAttribute('tabindex')"), "0", "canevas atteignable au clavier")
    verifie(js("!!document.querySelector('label[for=av-larg]')"), True, "label for sur le curseur de largeur")

    # photo anormale : message, page intacte
    js(SVG_SANS_DIMENSIONS)
    verifie(condition(cdp, "document.getElementById('av-msg').className === 'mauvais' && /illisible/.test(document.getElementById('av-msg').textContent)", 10), True,
            "image SVG de dimensions nulles : Image illisible")
    verifie(js("!AV.src && !AV.img"), True, "image sans dimensions : rien d'accepte")
    js(FICHIER_GROS)
    verifie(condition(cdp, "/30 Mo/.test(document.getElementById('av-msg').textContent)", 10), True, "photo de plus de 30 Mo : refusee avec un message")
    verifie(js("!AV.src && !AV.img"), True, "photo trop grosse : rien d'accepte")

    # depot de l'image, rotation, recadrage
    js(FABRIQUE)
    verifie(condition(cdp, "!!AV.src && AV.photo.width === 480 && AV.photo.height === 240", 10), True, "photo deposee : 600x300 ramenee a 480 x 240")
    px = js("(function(){var g=AV.photo.getContext('2d'),d=g.getImageData(10,200,1,1).data,e=g.getImageData(470,200,1,1).data;"
            "return [d[0]>180&&d[2]<80,e[2]>180&&e[0]<80];})()")
    verifie(px, [True, True], "pixels de la photo : rouge a gauche, bleu a droite")
    js("document.getElementById('av-rot').click()")
    verifie(condition(cdp, "AV.rot === 1 && AV.src.width === 300 && AV.src.height === 600 && AV.photo.height === 960", 10), True, "rotation d'un quart de tour")
    for _ in range(3):
        js("document.getElementById('av-rot').click()")
    verifie(condition(cdp, "AV.rot === 0 && AV.photo.height === 240", 10), True, "4 quarts de tour : retour a l'origine")
    js(GLISSE)
    verifie(condition(cdp, "Math.abs(AV.rec.w - 0.5) < 0.02 && AV.photo.height === 480", 10), True, "recadrage a la poignee : moitie gauche")
    verifie(js("(function(){var d=AV.photo.getContext('2d').getImageData(470,100,1,1).data;return d[0]>180&&d[2]<80;})()"), True, "recadre : tout est rouge")
    verifie(js("JSON.parse(localStorage.getItem('av.rec.' + AV.env)).w > 0.4"), True, "rectangle de recadrage memorise par carte")

    # editeur de formes : rectangle pose sur la photo recadree (toute rouge), couleur mediane, deplacement, annulation, SVG accepte
    js(SOURIS)
    js("document.querySelector('[data-avf-outil=rect]').click()")
    js("__souris('pointerdown',0.2,0.2);__souris('pointermove',0.6,0.6);__souris('pointerup',0.6,0.6)")
    verifie(condition(cdp, "AV.formes.length === 1 && AV.formes[0].type === 'rect'", 10), True, "editeur : un rectangle pose")
    verifie(js("(function(){var f=AV.formes[0],c=parseInt(f.fill.slice(1),16);return [(c>>16)>180,(c&255)<80];})()"), [True, True], "editeur : couleur mediane de la zone = rouge de la photo")
    x0 = js("AV.formes[0].x")
    js("__souris('pointerdown',0.4,0.4);__souris('pointermove',0.5,0.4);__souris('pointerup',0.5,0.4)")
    verifie(condition(cdp, "AV.formes[0].x > " + str(x0) + " + 5", 10), True, "editeur : rectangle deplace")
    js("AV.annule()")
    verifie(condition(cdp, "Math.abs(AV.formes[0].x - " + str(x0) + ") < 0.01", 10), True, "editeur : annuler ramene la position")
    verifie(condition(cdp, "document.getElementById('av-poids').textContent.indexOf('Ko') > 0"), True, "poids du fond mis a jour apres modification des formes")
    verifie(js(POSE_SVG), 200, "AV.svg() de l'editeur accepte par POST /fond")
    verifie(js("document.getElementById('av-garder').disabled"), False, "dessin a plat avec une forme : Garder ce fond actif")

    # clic sans glisser : pas de rectangle minuscule ; fleches : 1 px, 8 px avec Maj
    js("document.querySelector('[data-avf-outil=rect]').click()")
    n0 = js("AV.formes.length")
    js("__souris('pointerdown',0.8,0.8);__souris('pointerup',0.8,0.8)")
    verifie(js("AV.formes.length"), n0, "clic sans glisser : aucun rectangle cree")
    js("document.querySelector('[data-avf-outil=sel]').click(); AV.selection = AV.formes[0].id; AV.dessine()")
    x1 = js("AV.formes[0].x")
    js(TOUCHE % "false")
    verifie(js("Math.round((AV.formes[0].x - %s) * 10) / 10" % x1), 1, "fleche droite : 1 px")
    js(TOUCHE % "true")
    verifie(js("Math.round((AV.formes[0].x - %s) * 10) / 10" % x1), 9, "Maj + fleche droite : 8 px de plus")

    sonde_export(cdp)

    # mode photo allegee
    js("document.getElementById('av-fond-photo').click()")
    verifie(condition(cdp, "['webp','jpg'].indexOf(document.getElementById('av-type').textContent) >= 0"), True, "mode photo : type webp (ou jpg en repli)")
    poids1 = js("document.getElementById('av-poids').textContent")
    js("var q=document.getElementById('av-qualite');q.value=95;q.dispatchEvent(new Event('input',{bubbles:true}))")
    verifie(condition(cdp, "document.getElementById('av-poids').textContent !== " + json.dumps(poids1), 10), True, "poids recalcule quand la qualite change")
    js(BLOB_ENVOYE)
    js("document.getElementById('av-garder').click()")
    verifie(condition(cdp, "!!AV.fond"), True, "Garder ce fond : reponse du serveur recue")
    verifie(js(COMPARE)[:3], [200, True, True], "GET /fond rend exactement le blob envoye")
    # mode dessin garde (svg) ; toute modification invalide l'empreinte affichee
    verifie(js("document.getElementById('av-empreinte').textContent.length > 0"), True, "empreinte affichee apres Garder ce fond")
    js("document.getElementById('av-fond-plat').click()")
    verifie(js("[AV.fond, document.getElementById('av-empreinte').textContent]"), [None, ""], "changement de mode : fond et empreinte invalides")
    condition(cdp, "document.getElementById('av-type').textContent === 'svg'", 10)
    js("document.getElementById('av-garder').click()")
    verifie(condition(cdp, "!!AV.fond && AV.fond.type === 'svg'"), True, "mode dessin : fond svg garde")
    js("document.querySelector('[data-avf-gab=boite]').click()")
    verifie(js("[AV.fond, document.getElementById('av-empreinte').textContent]"), [None, ""], "modification d'une forme : fond et empreinte invalides")
    condition(cdp, "!document.getElementById('av-garder').disabled", 10)
    js("document.getElementById('av-garder').click()")
    condition(cdp, "!!AV.fond")
    js("var q=document.getElementById('av-larg');q.value=500;q.dispatchEvent(new Event('input',{bubbles:true}))")
    verifie(js("[AV.fond, document.getElementById('av-empreinte').textContent]"), [None, ""], "changement de largeur : fond et empreinte invalides")
    # reponse d'un POST arrivee apres un changement de carte : ignoree
    condition(cdp, "!document.getElementById('av-garder').disabled", 10)
    js(POST_RETENU)
    js("document.getElementById('av-garder').click()")
    verifie(condition(cdp, "typeof window.__lache === 'function'"), True, "POST /fond en vol")
    js("(function(){var s=document.getElementById('av-carte'),o=[].slice.call(s.options).filter(function(x){return x.value!==s.value;})[0];s.value=o.value;s.dispatchEvent(new Event('change',{bubbles:true}));})()")
    js("window.__lache()")
    verifie(condition(cdp, "/obsol/.test(document.getElementById('av-msg').textContent)", 10), True, "reponse tardive signalee comme obsolete")
    verifie(js("[AV.fond, document.getElementById('av-empreinte').textContent]"), [None, ""], "changement de carte pendant un POST : empreinte non affichee")
    # un fichier qui n'est pas une image
    js(FICHIER_TEXTE)
    verifie(condition(cdp, "document.getElementById('av-msg').className === 'mauvais'", 10), True, "fichier non image : message d'erreur")
    # theme : variable --ac et contraste du bouton actif (>= 4,5:1) dans les deux themes
    for _ in range(2):
        c = js(CONTRASTE)
        verifie((c["ac"], min(c["ratios"]) >= 4.5), (True, True), f"theme {c['theme']} : --ac = --acc, contraste des boutons actifs {[round(r, 2) for r in c['ratios']]}")
        js("document.getElementById('av-theme').click()")
    page = http(f"http://127.0.0.1:{port}/", 5).decode("utf-8")
    verifie(sorted(set(MOTS_SANS_ACCENT.findall(page))), [], "libelles de l'interface : accents")
    verifie("#1a73e8" in page or "Style = '#" in page, False, "couleurs d'interface en dur absentes (variables du theme)")

    # donnees empoisonnees du localStorage : relues et bornees, rien n'est execute
    js(POISON)
    verifie(recharge(cdp, port), True, "rechargement avec localStorage empoisonne")
    verifie(js("[AV.formes.length, AV.formes[0].fill, AV.formes[0].texte]"), [500, "#888888", "</script"], "formes relues : 500 au plus, fill et texte revalides")
    verifie(js("document.querySelectorAll('#av-canevas b, #av-canevas script').length + (window.__pwn ? 1 : 0)"), 0, "texte hostile : aucun element injecte")
    verifie(js("/&lt;\\/script/.test(AV.svg()) && AV.svg().indexOf('<b') < 0"), True, "texte hostile echappe dans AV.svg()")
    verifie(js(POSE_SVG), 200, "le SVG du texte hostile passe POST /fond")
    verifie(js("[AV.rec.x, AV.rec.w, AV.haut]"), [0, 1, 270], "rectangle de recadrage absurde du localStorage rejete")
    js("localStorage.setItem('av.env', '<img src=x onerror=window.__pwn=1>')")
    verifie(recharge(cdp, port), True, "rechargement avec une carte memorisee inconnue")
    verifie(js("[].slice.call(document.querySelectorAll('#av-carte option')).some(function(o){return o.value===AV.env;}) && !window.__pwn"), True, "carte inconnue : repli sur une carte de la liste")
    js("localStorage.clear()")
    verifie(cdp.erreurs(), [], "aucune erreur dans la console de la page")


EXPORT_PREP = ("window.__tel=[];window.__cop=[];AV.telecharge=function(n,b){window.__tel.push({n:n,t:b.type,s:b.size,b:b});};"
               "AV.presse=function(t){window.__cop.push(t);return Promise.resolve();};"
               "AV.elements=[{id:'v1',type:'voyant',x:60,y:60,source:{type:'relais',n:1},style:{}},{id:'l1',type:'liaison',x:10,y:10,x2:100,y2:80,source:{type:'wifi'}}];"
               "AV.sim={v1:'on',l1:'muette'};AV.change();")
FRAGMENT = ("(async function(){var h=AV.fragmentHtml(),f=document.createElement('iframe');f.srcdoc='<!doctype html><body>'+h;document.body.appendChild(f);"
            "await new Promise(function(ok){f.onload=ok;});var d=f.contentDocument,g=d.querySelector('.av-v'),a=g.getAttribute('class');"
            "g.querySelector('circle').dispatchEvent(new MouseEvent('click',{bubbles:true}));var b=g.getAttribute('class');"
            "var l=d.querySelector('.av-l'),la=l.getAttribute('class');l.querySelector('line').dispatchEvent(new MouseEvent('click',{bubbles:true}));"
            "var r=[a,b,la,l.getAttribute('class'),/visuel\.js|fetch|XMLHttpRequest| src=/.test(h)];f.remove();return r;})()")
ZONE = ("(function(){var g=AV.photo.getContext('2d');g.fillStyle='#0000ff';g.fillRect(100,100,40,40);"
        "AV.formes.push(AV_FORMES.normalise({id:AV.idSuivant(),type:'rect',x:90,y:90,l:60,h:60,zone:'effacer'}));var c=AV.fondPhoto().getContext('2d').getImageData(110,110,1,1).data,"
        "o=AV.photo.getContext('2d').getImageData(110,110,1,1).data;AV.formes.pop();return [c[0]>180&&c[2]<80,o[2]>180&&o[0]<80];})()")


def sonde_export(cdp):
    js = cdp.js
    js(EXPORT_PREP)
    js("document.getElementById('av-export').click()")
    verifie(js("document.getElementById('avx-panel').hidden"), False, "export : le panneau s'ouvre")
    js("document.getElementById('avx-svg').click()")
    verifie(js("[__tel.length, __tel[0].n.slice(-4), __tel[0].t]"), [1, ".svg", "image/svg+xml"], "export : SVG telecharge")
    verifie(js("(async function(){var t=await __tel[0].b.text();return [/av-v on/.test(t),/av-l muette/.test(t),/<style>/.test(t),t.indexOf('visuel.js')<0];})()"),
            [True, True, True, True], "export : SVG avec calques dans l'etat simule, CSS integre")
    js("document.getElementById('avx-copie-svg').click()")
    verifie(condition(cdp, "__cop.length === 1 && /^<svg/.test(__cop[0])"), True, "export : code SVG copie")
    js("document.getElementById('avx-copie-html').click()")
    verifie(condition(cdp, "__cop.length === 2 && /^<div class=\"av-visuel\"/.test(__cop[1]) && __cop[1].indexOf('<script>') > 0"), True, "export : code HTML copie")
    verifie(js(FRAGMENT), ["av-v on", "av-v off", "av-l muette", "av-l active", False],
            "export : le fragment HTML s'affiche seul, le voyant et la liaison changent d'etat sans carte ni requete")
    js("document.getElementById('avx-png').click()")
    verifie(condition(cdp, "__tel.length === 2 && __tel[1].t === 'image/png' && __tel[1].s > 100 && /\.png$/.test(__tel[1].n)", 15), True, "export : PNG telecharge")
    verifie(js("(async function(){var u=new Uint8Array(await __tel[1].b.slice(0,4).arrayBuffer());return [u[0],u[1],u[2],u[3]];})()"), [137, 80, 78, 71], "export : signature PNG")
    verifie(js(ZONE), [True, True], "photo : zone a effacer = aplat de la couleur du bord (la photo d'origine intacte)")
    js("AV.elements=[];AV.sim={};AV.change();document.getElementById('av-export').click()")


def sondes_vivantes(tue=False):
    """Nombre de chrome.exe dont la ligne de commande porte le prefixe de la sonde ; `tue` : les arrete d'abord (orphelins du profil)."""
    action = " | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" if tue else ""
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "$p = @(Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -like '*" + PREFIXE + "*' } | Where-Object { $g = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue; $g -and -not $g.HasExited });"
                        " $p" + action + "; $p.Count"], capture_output=True, text=True)
    return int((r.stdout or "0").strip().splitlines()[-1] or 0)


def main():
    t = Path(tempfile.mkdtemp(prefix=PREFIXE))
    serveur = chrome = None
    try:
        port = port_libre()
        serveur = subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve()), "--serveur", str(port)],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        http(f"http://127.0.0.1:{port}/envs", 30)
        exe = next((c for c in CHROMES if c.is_file()), None)
        if exe is None:
            raise FileNotFoundError("chrome.exe introuvable")
        cdp_port = port_libre()
        chrome = subprocess.Popen([str(exe), "--headless=new", f"--remote-debugging-port={cdp_port}", "--remote-allow-origins=*",
                                   f"--user-data-dir={t / 'profil'}", "--no-first-run", "--no-default-browser-check",
                                   "--disable-extensions", "--window-size=1400,1000", "about:blank"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cibles = json.loads(http(f"http://127.0.0.1:{cdp_port}/json/list", 20))
        cdp = Cdp(next(c for c in cibles if c.get("type") == "page")["webSocketDebuggerUrl"])
        for d in ("Runtime.enable", "Log.enable", "Page.enable"):
            cdp.appel(d)
        cdp.appel("Page.navigate", url=f"http://127.0.0.1:{port}/")
        attend(cdp, "document.readyState === 'complete' && !!window.AV", 20)
        sonde(cdp, port)
    finally:
        tue_arbre(chrome)
        tue_arbre(serveur)
        shutil.rmtree(t, ignore_errors=True)
    limite = time.monotonic() + 15            # condition : plus aucun Chrome de sonde (au plus 15 s)
    sondes_vivantes(tue=True)                 # filet : un orphelin du profil temporaire
    vivantes = sondes_vivantes()
    while vivantes and time.monotonic() < limite:
        time.sleep(0.5)
        vivantes = sondes_vivantes()
    verifie(vivantes, 0, f"aucun Chrome `{PREFIXE}*` ne survit")
    print("VERT" if not ECHECS else f"ROUGE : {ECHECS}")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--serveur":
        sys.exit(mode_serveur(int(sys.argv[2])))
    sys.exit(main())
