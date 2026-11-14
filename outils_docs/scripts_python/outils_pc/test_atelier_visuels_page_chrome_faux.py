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
            self.id, self.nom, self.externe, self.gratuit = id_, "Faux " + id_, externe, "gratuit"

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
        verifie([e for e in cdp.erreurs() if "horsligne" not in e], [], "faux : aucune erreur dans la console de la page")
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
