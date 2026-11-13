"""Sonde Chrome de la page de l'atelier des visuels (atelier_visuels_page.PAGE) : depot d'une image fabriquee dans le navigateur,
recadrage, rotation, les deux modes de fond, poids affiche, theme, garde du fond (GET /fond == blob).

UTILISATION (a la main ; aucun pio, aucune carte, aucune photo reelle)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_visuels_page_chrome.py
Code de sortie 0 = vert. Serveur reel dans un processus fils (depot reel en lecture seule : rien n'est ecrit). Les attentes sont des
CONDITIONS, jamais des durees ; les Chrome sont arretes et on verifie qu'aucun `sonde_atelier_visuels_page_*` ne survit.
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
DOUBLURE_SVG = ("if(!window.AV.svg){window.AV.svg=function(){return '<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 10 10\">"
                "<path d=\"M0 0L9 9\" fill=\"#abc\"/></svg>';};window.AV.change();}")
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


def sonde(cdp):
    js = cdp.js
    verifie(js("document.title"), "Atelier des visuels", "titre de la page")
    verifie(js("document.querySelectorAll('main > div').length"), 3, "trois colonnes")
    verifie(condition(cdp, "document.querySelectorAll('#av-carte option').length > 0"), True, "cartes chargees dans le select")
    verifie(js("document.querySelectorAll('#av-carte optgroup').length > 0"), True, "cartes groupees par lieu")
    verifie(js("[document.getElementById('av-export').disabled, document.getElementById('av-export').title, document.getElementById('av-ecrire').disabled]"),
            [True, "a venir", True], "Exporter et Ecrire inactifs, info-bulle a venir")

    # theme : le clic bascule data-theme et change le fond de la page
    lit = "[document.documentElement.getAttribute('data-theme'), getComputedStyle(document.body).backgroundColor]"
    avant = js(lit)
    js("document.getElementById('av-theme').click()")
    apres = js(lit)
    verifie((avant[0] != apres[0], avant[1] != apres[1], apres[0] in ("sombre", "clair")), (True, True, True), "theme : le clic bascule data-theme et le fond")
    verifie(js("localStorage.getItem('atelier-visuels-theme')"), apres[0], "theme memorise dans localStorage")

    # doublure du dessin a plat si l'editeur de formes n'est pas la
    js(DOUBLURE_SVG)
    verifie(condition(cdp, "document.getElementById('av-poids').textContent.indexOf('Ko') > 0", 10), True, "mode dessin : poids affiche (depuis AV.svg)")
    verifie(js("document.getElementById('av-garder').disabled"), False, "mode dessin : Garder ce fond actif")

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
    # mode dessin garde (svg)
    js("document.getElementById('av-fond-plat').click()")
    condition(cdp, "document.getElementById('av-type').textContent === 'svg'", 10)
    js("window.AV.fond = null; document.getElementById('av-garder').click()")
    verifie(condition(cdp, "!!AV.fond && AV.fond.type === 'svg'"), True, "mode dessin : fond svg garde")
    # un fichier qui n'est pas une image
    js(FICHIER_TEXTE)
    verifie(condition(cdp, "document.getElementById('av-msg').className === 'mauvais'", 10), True, "fichier non image : message d'erreur")
    verifie(cdp.erreurs(), [], "aucune erreur dans la console de la page")


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
        sonde(cdp)
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
