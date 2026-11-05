"""Sonde Chrome de la page de l'atelier des graphiques (atelier_graphiques_page.PAGE), plan A7.

UTILISATION (a la main ; aucun pio, aucune carte ; Chrome tourne ~40 s)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_graphiques_page_chrome.py
        [--capture FICHIER.png] [--sans-temoin]
Code de sortie 0 = vert : la vraie page passe toutes les verifications ET le temoin (la meme page avec une erreur JS
volontaire au chargement) est detecte. Client DevTools repris de test_build_page_chrome.py.

Montage : atelier_graphiques_web.py dans un processus fils (mode --serveur), devant une COPIE du depot (meme montage
que test_atelier_graphiques_web.py) ; la carte est simulee en remplacant build_ota_http._get dans ce processus (aucun
reseau) : la cuve repond, le P4 (192.168.0.43 sans port) est muet. Detection des builds neutralisee ;
OUTILS_TASMOTA_DOSSIER temporaire. Fenetre de 1400 px (capture comparee a modele-B.png par l'utilisateur).
Mode sombre de la page : temoin manuel SONDE_SANS_INTERRUPTEUR=1 (l'interrupteur ne fait plus rien -> rouge attendu).
Destination « Graphiques » (A5, sonde_destination) : menu « Page » avec et sans historique, « + Page » retire, champs de page
masques, composition de la carte differente (diff, deux choix, perte dite, rien d'ecrit sans choix), non verifiee (bandeau),
choix « carte » indisponible (grise, motif), Diff et Ecrire vers graphiques.json de la copie.
Scenario : apercu trace par le vrai moteur, styles proposes, reglages par serie (libelle -> legende, couleur -> serie
de l'apercu, unite -> axe ; vides -> la serie redevient une chaine), un seuil ajoute puis change modifie le SVG de l'apercu,
bascules page / telephone / theme sombre, deplacement d'une tuile, carte muette -> bandeau « valeurs simulees »,
avertissement ECharts exclu, ecriture dans la copie, lien vers la page Build.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre, tue_arbre   # client DevTools stdlib

ECHECS = []
CUVE, P4 = "tasmota32s3-garage-capteurs-cuve-modbus", "tasmota32p4-garage-serveur-modbus"
MARQUE_TEMOIN = "var gabarit = '', apercuCtrl = null"
INJECTION_TEMOIN = "\n$('bouton-qui-n-existe-pas').onclick = null;   // TEMOIN : TypeError au chargement\n"
LENTEUR_P4 = 3
SERIES = ["sensorsCuve.niveauCuve.volume", "sensorsCuve.niveauCuve.tauxRemplissage", "DS18B20.Temperature"]


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)
    return ok


def fausse_carte(ip, chemin, delai):
    """Carte simulee : la cuve (IP:port) repond, le P4 ne repond pas, et lentement (course au changement d'env)."""
    if ip == "192.168.0.43":
        time.sleep(LENTEUR_P4)
        raise OSError("pas de reponse")
    if "p=liste" in chemin:
        return json.dumps({"nom": "mesures", "series": SERIES, "mois": []}).encode()
    if "p=jour" in chemin:
        t0 = int(time.time()) // 300 * 300 - 288 * 300
        return json.dumps({"nom": "mesures", "series": SERIES, "pas": 300, "t0": t0,
                           "valeurs": [[round(4300 - k * 1.5, 1) for k in range(288)], [round(0.64 - k * 0.0002, 4) for k in range(288)],
                                       [round(11.5 + 1.6 * ((k % 144) / 144), 2) for k in range(288)]],
                           "tEncours": t0 + 288 * 300, "encours": [3870, 0.58, 12.1]}).encode()
    if chemin.startswith("/json/graphiques.json"):             # composition /graphiques de la carte, pilotee par la sonde (A5)
        f = Path(os.environ["OUTILS_TASMOTA_DOSSIER"]) / "carte_graphiques.json"
        if f.is_file():
            if f.read_bytes() == b"HORSLIGNE":
                raise OSError("carte hors ligne")
            return f.read_bytes()
    if chemin.startswith("/cm"):
        return json.dumps({"StatusSNS": {"sensorsCuve": {"niveauCuve": {"volume": 3870, "tauxRemplissage": 0.58}},
                                         "DS18B20": {"Temperature": 12.1}}}).encode()
    return b'{"historique": true}'


def mode_serveur(port, depot, temoin):
    import atelier_graphiques_web as agw
    import build_ota_http
    if temoin:
        import atelier_graphiques_page
        assert atelier_graphiques_page.PAGE.count(MARQUE_TEMOIN) == 1, "marque du temoin introuvable dans la page"
        atelier_graphiques_page.PAGE = atelier_graphiques_page.PAGE.replace(MARQUE_TEMOIN, INJECTION_TEMOIN + MARQUE_TEMOIN)
    if os.environ.get("SONDE_SANS_INTERRUPTEUR"):     # temoin manuel du theme : l'interrupteur ne fait plus rien
        import atelier_graphiques_page
        assert atelier_graphiques_page.PAGE.count(atelier_graphiques_page.THEME_INTERRUPTEUR) == 1
        atelier_graphiques_page.PAGE = atelier_graphiques_page.PAGE.replace(atelier_graphiques_page.THEME_INTERRUPTEUR, "")
    build_ota_http._get = fausse_carte
    import atelier_graphiques_televerse as agt     # page Build simulee : active sauf si le fichier-temoin « build_arrete » existe
    agt.build_actif = lambda port=agt.PORT_BUILD: not (Path(os.environ["OUTILS_TASMOTA_DOSSIER"]) / "build_arrete").exists()
    agw.DEPOT = Path(depot)
    agw.builds_en_cours_defaut = lambda: []
    sys.argv = ["atelier_graphiques_web.py", "--http", str(port), "--local", "--sans-navigateur"]
    return agw.principal()


class Montage:
    def __init__(self):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_atelier_graphiques_"))
        self.serveur = self.chrome = None

    def demarre(self, temoin):
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(self.t / "outils")
        self.depot = monte_depot(self.t)
        environ = dict(os.environ, PYTHONIOENCODING="utf-8")
        self.port = port_libre()
        self.url = f"http://127.0.0.1:{self.port}/"
        commande = ([sys.executable, "-u", str(Path(__file__).resolve()), "--serveur", str(self.port), str(self.depot)]
                    + (["--temoin"] if temoin else []))
        self.serveur = subprocess.Popen(commande, env=environ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self._attend_http(self.url + "moteur/pages_graphiques.css", 30)
        chrome = next((c for c in CHROMES if c.is_file()), None)
        if chrome is None:
            raise FileNotFoundError("chrome.exe introuvable (Program Files, LOCALAPPDATA)")
        self.port_cdp = port_libre()
        self.chrome = subprocess.Popen([str(chrome), "--headless=new", f"--remote-debugging-port={self.port_cdp}",
                                        "--remote-allow-origins=*", f"--user-data-dir={self.t / 'profil'}",
                                        "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                                        "--window-size=1400,1000", "about:blank"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cibles = self._attend_http(f"http://127.0.0.1:{self.port_cdp}/json/list", 20)
        page = next(c for c in json.loads(cibles) if c.get("type") == "page")
        self.cdp = Cdp(page["webSocketDebuggerUrl"])
        for domaine in ("Runtime.enable", "Log.enable", "Page.enable"):
            self.cdp.appel(domaine)
        self.cdp.appel("Emulation.setDeviceMetricsOverride", width=1400, height=1000, deviceScaleFactor=1, mobile=False)
        systeme(self.cdp, "light")

    def _attend_http(self, url, delai):
        limite = time.monotonic() + delai
        while time.monotonic() < limite:
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    return r.read().decode("utf-8")
            except OSError:
                time.sleep(0.2)
        raise TimeoutError(f"{url} ne repond pas")

    def ferme(self):
        tue_arbre(self.chrome)
        tue_arbre(self.serveur)
        shutil.rmtree(self.t, ignore_errors=True)


def monte_depot(t):
    """Copie du depot du banc HTTP : .ini, .h, autoexec et persist utiles, fichiers du moteur."""
    import test_atelier_graphiques_web as taw
    depot = Path(t) / "depot"
    depot.mkdir()
    taw.tage.copie(depot)
    for rel in ("tasmota/user_config_override.h", taw.tage.fbe.dossier_carte(CUVE) + "/_persist.json",
                taw.tage.fbe.dossier_carte(P4) + "/autoexec.be", taw.tage.fbe.dossier_carte(P4) + "/_persist.json"):
        (depot / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(taw.DEPOT / rel, depot / rel)
    for rel in taw.SD:
        (depot / "data/sd" / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(taw.DEPOT / "data/sd" / rel, depot / "data/sd" / rel)
    return depot


def systeme(cdp, valeur):
    cdp.appel("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": valeur}])


def recharge(cdp):
    """Recharge la page et attend la carte lue, l'apercu trace et le diff pret."""
    cdp.appel("Page.reload")
    time.sleep(0.5)
    attend(cdp, "document.getElementById('relire') && document.getElementById('relire').textContent.indexOf('en ligne') >= 0"
                " && !!document.querySelector('#apercu .pg_tuile[data-rendu]') && !document.getElementById('ecrire').disabled", 25)


def sonde_theme(m, capture):
    """Interrupteur « Mode sombre » de la page (comme l'annuaire), independant du « thème sombre » de l'apercu."""
    cdp = m.cdp
    theme = "document.documentElement.getAttribute('data-theme')"
    fonds = ("[" + theme + ", getComputedStyle(document.body).backgroundColor, getComputedStyle(document.querySelector('.carte'))"
             ".backgroundColor, getComputedStyle(document.getElementById('r-titre')).color, document.getElementById('theme').checked]")
    apercu = ("[document.getElementById('cadre').classList.contains('sombre'), document.getElementById('sombre').classList.contains('actif'),"
              " getComputedStyle(document.getElementById('cadre')).backgroundColor]")
    verifie(cdp.js(fonds), ["clair", "rgb(246, 247, 249)", "rgb(255, 255, 255)", "rgb(34, 34, 34)", False],
            "page : mode clair par defaut (systeme clair), interrupteur decoche")
    cdp.js("document.querySelector('label.theme').click(); 1")
    verifie(cdp.js(fonds), ["sombre", "rgb(18, 20, 23)", "rgb(29, 32, 37)", "rgb(230, 230, 230)", True],
            "interrupteur : page en mode sombre (fond, cartes, texte des champs)")
    verifie(cdp.js(apercu), [False, False, "rgb(255, 255, 255)"], "mode sombre de la page : « thème sombre » de l'apercu inchange")
    if capture:
        time.sleep(1)
        cdp.capture(str(Path(capture).with_name(Path(capture).stem + "-sombre.png")))
    recharge(cdp)
    verifie(cdp.js(fonds)[0::4], ["sombre", True], "mode sombre garde au rechargement (localStorage)")
    cdp.js("document.getElementById('sombre').click(); 1")
    verifie(cdp.js("[" + theme + ", document.getElementById('cadre').classList.contains('sombre')]"), ["sombre", True],
            "« thème sombre » de l'apercu : ne change pas le mode de la page")
    cdp.js("document.getElementById('sombre').click(); document.querySelector('label.theme').click(); 1")
    verifie(cdp.js("[" + theme + ", localStorage.getItem('atelier-graphiques-theme')]"), ["clair", "clair"],
            "interrupteur : retour au mode clair, memorise")
    cdp.js("localStorage.removeItem('atelier-graphiques-theme'); 1")
    systeme(cdp, "dark")
    recharge(cdp)
    verifie(cdp.js(theme), "sombre", "sans choix memorise : systeme sombre -> page sombre (comme l'annuaire)")
    systeme(cdp, "light")
    recharge(cdp)
    verifie(cdp.js(theme), "clair", "sans choix memorise : systeme clair -> page claire")


def svg_apercu(cdp):
    return cdp.js("(document.querySelector('#apercu .pg_tuile') || {}).innerHTML || ''")


OPTION_APERCU = ("(function(){ var t = document.querySelector('#apercu .pg_tuile'), g = t && window.echarts && echarts.getInstanceByDom(t);"
                 " if (!g) return null; var o = g.getOption(); return [o.series[0].name, o.series[0].color, o.yAxis[0].name || '']; })()")


def saisit(cdp, selecteur, valeur):
    cdp.js("var i = document.querySelector(" + json.dumps(selecteur) + "); i.value = " + json.dumps(valeur) + ";"
           " i.dispatchEvent(new Event('input', {bubbles: true})); 1")


def sonde_series(cdp):
    """Reglages par serie : chaque champ change l'apercu (option ECharts relue), vider revient a la forme chaine."""
    vrai = lambda expr, d=10: bool(attend(cdp, expr, d))
    chemin = cdp.js("etat.desc.pages[0].graphiques[0].series[0]")
    verifie((isinstance(chemin, str), cdp.js("document.querySelectorAll('#r-series .serie').length")), (True, 1),
            "reglages : une ligne par serie du graphique (forme chaine au depart)")
    case = lambda c: "document.querySelector('#arbre input[data-serie=\"" + c + "\"]')"
    cdp.js(case("DS18B20.Temperature") + ".click(); 1")
    verifie(cdp.js("[etat.desc.pages[0].graphiques[0].series[1], document.querySelector('#r-series [data-serie-champ=unite][data-i=\"1\"]').value]"),
            [{"chemin": "DS18B20.Temperature", "unite": "°C"}, "°C"], "serie cochee : l'unite connue (A4) ecrite, et montree dans le champ")
    saisit(cdp, "#r-series [data-serie-champ=unite][data-i=\"1\"]", "")
    verifie(cdp.js("etat.desc.pages[0].graphiques[0].series[1]"), "DS18B20.Temperature", "unite videe : la serie redevient la chaine")
    taux = "sensorsCuve.niveauCuve.tauxRemplissage"
    a4 = "etat.series.series.filter(function(s){ return s.chemin === '" + taux + "'; })[0]"
    cdp.js("window.uniteA4 = " + a4 + ".unite; " + a4 + ".unite = 'kilowattheure'; " + case(taux) + ".click(); " + a4 + ".unite = window.uniteA4; 1")
    verifie(cdp.js("[etat.desc.pages[0].graphiques[0].series[2], document.querySelector('#r-series [data-serie-champ=unite][data-i=\"2\"]').placeholder]"),
            [taux, "kilowattheure"], "unite connue de plus de 10 octets : jamais tronquee, la chaine et l'unite en suggestion")
    cdp.js("etat.desc.pages[0].graphiques[0].type = 'radar'; dessineReglages(); 1")
    verifie(cdp.js("[].map.call(document.querySelectorAll('#r-series input[type=color]'), function(i){ return i.disabled; })"
                   ".concat([document.querySelectorAll('#r-series [data-serie-raz]').length])"), [True, True, True, 0],
            "radar : couleur des series grisee (style qui l'ignore)")
    cdp.js("etat.desc.pages[0].graphiques[0].type = 'courbe'; " + case(taux) + ".click(); " + case("DS18B20.Temperature") + ".click(); 1")
    verifie(cdp.js("JSON.stringify(etat.desc.pages[0].graphiques[0].series) + document.querySelectorAll('#r-series .serie').length"),
            json.dumps([chemin]) + "1", "series decochees : retour a la seule serie de depart")
    palette = cdp.js("PagesGraphiques.PALETTE[0]")
    verifie(cdp.js("document.querySelector('#r-series input[type=color]').value"), palette, "couleur affichee : celle de la palette")
    saisit(cdp, "#r-series [data-serie-champ=libelle]", "Niveau")
    verifie(vrai("JSON.stringify(" + OPTION_APERCU + ") === " + json.dumps(json.dumps(["Niveau", palette, ""], separators=(",", ":")))),
            True, "libelle saisi : la legende de l'apercu change")
    saisit(cdp, "#r-series [data-serie-champ=libelle]", "")
    verifie(vrai("etat.desc.pages[0].graphiques[0].series[0] === " + json.dumps(chemin)), True, "libelle vide : la serie redevient la chaine")
    saisit(cdp, "#r-series input[type=color]", "#ff00aa")
    verifie(vrai("(" + OPTION_APERCU + " || [])[1] === '#ff00aa' && /ff00aa|255,\\s*0,\\s*170/i.test(document.querySelector('#apercu .pg_tuile').innerHTML)"),
            True, "couleur changee : la serie de l'apercu prend la couleur (option et SVG)")
    cdp.js("document.querySelector('#r-series [data-serie-raz]').click(); 1")
    verifie(vrai("etat.desc.pages[0].graphiques[0].series[0] === " + json.dumps(chemin) + " && (" + OPTION_APERCU + " || [])[1] === '" + palette + "'"),
            True, "✕ : couleur de la palette, la serie redevient la chaine")
    saisit(cdp, "#r-series [data-serie-champ=libelle]", "Volume cuve")
    saisit(cdp, "#r-series [data-serie-champ=unite]", "L")
    saisit(cdp, "#r-series input[type=color]", "#ff00aa")
    verifie(vrai("JSON.stringify(" + OPTION_APERCU + ") === '[\"Volume cuve\",\"#ff00aa\",\"L\"]'"), True,
            "libelle, unite et couleur : legende, couleur et axe de l'apercu")
    verifie(cdp.js("etat.desc.pages[0].graphiques[0].series[0]"), {"chemin": chemin, "libelle": "Volume cuve", "unite": "L", "couleur": "#ff00aa"},
            "description : la serie en forme objet")
    verifie(vrai("!document.getElementById('ecrire').disabled && document.getElementById('motifs').textContent === ''", 15), True,
            "serie en forme objet : description valide, « Ecrire » actif")


def sonde_page(m, capture):
    cdp = m.cdp
    cdp.appel("Page.navigate", url=m.url + "?env=" + CUVE)
    attend(cdp, "document.getElementById('relire').textContent.indexOf('lecture') < 0", 20)
    verifie(cdp.js("document.getElementById('relire').textContent"), "● en ligne 192.168.0.43:8081",
            "chargement : carte en ligne, adresse par le maitre")
    verifie(cdp.js("document.getElementById('env').value"), CUVE, "?env= preselectionne la cuve")
    verifie(bool(attend(cdp, "(document.querySelector('#apercu .pg_tuile') || {}).getAttribute && "
                             "document.querySelector('#apercu .pg_tuile').getAttribute('data-rendu') === 'line'", 15)),
            True, "apercu : courbe tracee par le vrai moteur (data-rendu)")
    verifie(attend(cdp, "document.querySelectorAll('#vignettes .vign').length >= 3", 10), True, "styles proposes : 3 au moins")
    verifie(attend(cdp, "!document.getElementById('ecrire').disabled", 15), True, "diff calcule : « Ecrire » actif")
    verifie(cdp.js("[...document.querySelectorAll('#onglets button')].some(function(b){return b.textContent.indexOf('cenv') === 0;})"),
            True, "onglets du code : cenv")
    verifie(cdp.js("document.getElementById('lien-build').getAttribute('href')"),
            "http://127.0.0.1:7700/?env=" + CUVE + "#fichiers", "lien « Envoyer par la page Build »")
    verifie(cdp.js("document.getElementById('bandeau').classList.contains('cache')"), True, "carte en ligne : pas de bandeau")
    sonde_series(cdp)
    if capture:
        time.sleep(1)
        cdp.capture(capture)
    sonde_theme(m, capture)
    avant = svg_apercu(cdp)
    cdp.js("document.getElementById('r-ajout-zone').click(); 1")
    verifie(attend(cdp, "/c0392b|192,\\s*57,\\s*43/i.test((document.querySelector('#apercu .pg_tuile') || {}).innerHTML || '')", 10),
            True, "seuil ajoute : sa couleur apparait dans l'apercu")
    un = svg_apercu(cdp)
    cdp.js("var i=document.querySelector('#r-zones input[type=number]'); i.value='70'; i.dispatchEvent(new Event('input', {bubbles: true})); 1")
    attend(cdp, "JSON.stringify(etat.desc.pages[0].graphiques[0].zones) === '[[0.7,\"#c0392b\"]]'", 5)
    verifie(bool(attend(cdp, "(document.querySelector('#apercu .pg_tuile') || {}).innerHTML !== " + json.dumps(un)
                             + " && /c0392b|192,\\s*57,\\s*43/i.test(document.querySelector('#apercu .pg_tuile').innerHTML)", 10)),
            True, "seuil change (20 -> 70 %) : le SVG de l'apercu change")
    verifie(avant != un, True, "seuil : apercu different de celui d'avant le seuil")
    cdp.js("['r-min', 'r-max'].forEach(function(id, k){ var i=document.getElementById(id); i.value=k ? '5000' : '3000';"
           " i.dispatchEvent(new Event('input')); }); 1")
    cdp.js("var i=document.querySelector('#r-zones input[type=number]'); i.value='50'; i.dispatchEvent(new Event('input', {bubbles: true})); 1")
    verifie(cdp.js("document.querySelector('#r-zones .zone .doux').textContent"), " ≈ 4000", "seuil a 50 % de 3000..5000 : « ≈ 4000 » recalcule")
    verifie(cdp.js("(function(){ var v = PagesGraphiques.lecteurCarte; PagesGraphiques.lecteurCarte = function(){ return function(){ return fetch('/envs'); }; };"
                   " try { return lecteur(['a'], 'direct').then(function(){ return 'redirige'; }, function(e){ return 'refuse'; }); }"
                   " finally { PagesGraphiques.lecteurCarte = v; } })()"), "refuse",
            "lecteur : un fetch hors /pages?f=valeurs et /histo n'est pas redirige vers /valeurs")
    cdp.js("document.getElementById('ajout-graphique').click(); document.querySelector('[data-mode=page]').click(); 1")
    verifie(attend(cdp, "document.querySelectorAll('#apercu .pg_tuile').length === 2 && document.getElementById('cadre').classList.contains('page')", 10),
            True, "bascule « page » : la grille montre les 2 graphiques")
    cdp.js("var tt=document.querySelectorAll('#apercu .pg_tuile'), dt=new DataTransfer(); dt.setData('text/plain','1');"
           " tt[0].dispatchEvent(new DragEvent('drop', {dataTransfer: dt, bubbles: true, cancelable: true})); 1")
    verifie(attend(cdp, "etat.desc.pages[0].graphiques[1].zones && !etat.desc.pages[0].graphiques[0].zones", 5), True,
            "tuile deplacee : ordre des graphiques echange")
    cdp.js("var tt=document.querySelectorAll('#apercu .pg_tuile'), dt=new DataTransfer(); dt.setData('text/plain','une image');"
           " tt[1].dispatchEvent(new DragEvent('drop', {dataTransfer: dt, bubbles: true, cancelable: true})); 1")
    time.sleep(0.5)
    verifie(cdp.js("!!etat.desc.pages[0].graphiques[1].zones && !etat.desc.pages[0].graphiques[0].zones"), True,
            "depot venu d'ailleurs (pas un rang de tuile) : ordre inchange")
    cdp.js("document.getElementById('sombre').click(); 1")
    if capture:                                       # grille du modele C (theme sombre), a cote de la capture du modele B
        attend(cdp, "[...document.querySelectorAll('#apercu .pg_tuile')].every(function(t){return t.getAttribute('data-rendu');})"
                    " && !document.getElementById('ecrire').disabled", 15)
        time.sleep(1)
        cdp.capture(str(Path(capture).with_name(Path(capture).stem + "-page.png")))
    cdp.js("document.querySelector('[data-vue=telephone]').click(); 1")
    verifie(attend(cdp, "document.getElementById('cadre').getBoundingClientRect().width === 380 && "
                        "getComputedStyle(document.getElementById('cadre')).backgroundColor === 'rgb(37, 37, 37)'", 5),
            True, "bascules telephone (380 px) et theme sombre")
    cdp.js("document.getElementById('r-page-id').value='cs'; document.getElementById('r-page-id').dispatchEvent(new Event('input')); 1")
    verifie(attend(cdp, "document.getElementById('motifs').textContent.indexOf('reserve') >= 0 && document.getElementById('ecrire').disabled", 10),
            True, "adresse de page = route existante : motif affiche, « Ecrire » grise")
    cdp.js("document.getElementById('r-page-id').value='tableau-cuve'; document.getElementById('r-page-id').dispatchEvent(new Event('input')); 1")
    cdp.js("etat.envs.forEach(function(e){ e.exclut_echarts = true; }); dessineAlertes(); 1")
    verifie(cdp.js("document.getElementById('alertes').textContent.indexOf('ECharts est exclu') >= 0"), True,
            "env qui exclut ECharts : avertissement (pas un refus)")
    cdp.js("etat.envs.forEach(function(e){ e.exclut_echarts = false; }); dessineAlertes(); window.confirm = function(){ return true; }; 1")
    verifie(attend(cdp, "!document.getElementById('ecrire').disabled", 15), True, "adresse corrigee : « Ecrire » actif")
    cdp.js("document.getElementById('ecrire').click(); 1")
    verifie(attend(cdp, "document.querySelector('#message .avert.vert') !== null", 15), True, "ecriture : message de reussite")
    rel = "data/garage/tasmota32s3-capteurs-cuve-modbus/pages_graphiques.json"
    ecrit = json.loads((m.depot / rel).read_text(encoding="utf-8")) if (m.depot / rel).is_file() else {}
    verifie((ecrit.get("pages") or [{}])[0].get("id"), "tableau-cuve", "ecriture : description ecrite dans la copie")
    verifie(attend(cdp, "document.getElementById('resume').textContent.indexOf('0 fichier') === 0", 10), True,
            "apres ecriture : plus rien a ecrire")
    # Course : le P4 repond en LENTEUR_P4 s ; on repasse aussitot sur la cuve, sa reponse tardive ne doit rien ecraser
    cdp.js("var s=document.getElementById('env'); s.value='" + P4 + "'; s.dispatchEvent(new Event('change'));"
           " s.value='" + CUVE + "'; s.dispatchEvent(new Event('change')); 1")
    attend(cdp, "etat.series && etat.series.source === 'carte' && etat.desc.pages[0].id === 'tableau-cuve'", 10)
    verifie(attend(cdp, "performance.getEntriesByType('resource').some(function(e){ return e.name.indexOf('/series?env=" + P4 + "') >= 0; })", 30),
            True, "course : la reponse tardive du P4 est bien arrivee")
    time.sleep(1)
    verifie(cdp.js("[etat.env, etat.series.source, etat.desc.pages[0].id, corpsEcriture().env, document.getElementById('relire').textContent]"),
            [CUVE, "carte", "tableau-cuve", CUVE, "● en ligne 192.168.0.43:8081"],
            "course : reponse tardive du P4 ignoree, etat et diff restent ceux de la cuve")
    verifie(attend(cdp, "document.getElementById('resume').textContent.indexOf('0 fichier') === 0", 10), True,
            "course : diff de la cuve (rien a ecrire), pas la description du P4")
    verifie(cdp.js("Object.keys(dernieres).length > 0 && Object.keys(dernieres).every(function(k){ return k.indexOf('" + CUVE + "|') === 0; })"),
            True, "course : donnees des vignettes rangees par env (aucune du P4)")
    cdp.js("var s=document.getElementById('env'); s.value='" + P4 + "'; s.dispatchEvent(new Event('change')); 1")
    verifie(attend(cdp, "!document.getElementById('bandeau').classList.contains('cache') && "
                        "document.getElementById('relire').textContent === 'valeurs simulées'", 25),
            True, "carte muette (P4) : bandeau « valeurs simulees »")
    verifie(attend(cdp, "!!document.querySelector('#apercu .pg_tuile[data-rendu]')", 15), True,
            "carte muette : l'apercu trace quand meme (valeurs simulees)")
    cdp.js("document.getElementById('suppr-page').click(); 1")
    verifie(cdp.js("['r-page-id', 'r-page-titre', 'r-acces'].map(function(id){ return document.getElementById(id).disabled; })"),
            [True, True, True], "plus aucune page : adresse, titre et acces de page grises")
    verifie(cdp.erreurs(), [], "aucune erreur JS pendant toute la sonde")


ERREURS_ATTENDUES = []        # journal Chrome du seul scenario qui provoque un refus de /diff (409) ; rempli par ce scenario
COMPO_DEPOT = [{"titre": "Cuve", "type": "courbe", "series": ["sensorsCuve.niveauCuve.volume"]}]
COMPO_CARTE = [{"titre": "Cuve", "type": "aire", "series": ["sensorsCuve.niveauCuve.volume"]},
               {"titre": "Temperature", "type": "courbe", "series": ["DS18B20.Temperature"]}]
CACHES = "['r-page-id', 'r-page-titre', 'r-acces', 'r-solidifier'].map(function(id){ return document.getElementById(id).offsetParent === null; })"
REL_GRAPH = "data/garage/tasmota32s3-capteurs-cuve-modbus/graphiques.json"


def pose_depot(m, composition):
    f = m.depot / REL_GRAPH
    f.parent.mkdir(parents=True, exist_ok=True)
    d = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {"affichage": {"x.y": {"libelle": "garde"}}}
    d.pop("graphiques", None)
    if composition is not None:
        d["graphiques"] = composition
    f.write_text(json.dumps(d, indent="\t") + "\n", encoding="utf-8")


def pose_carte(m, composition):
    """composition : une liste, ou 'HORSLIGNE'."""
    f = m.t / "outils" / "carte_graphiques.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b"HORSLIGNE" if composition == "HORSLIGNE" else json.dumps({"graphiques": composition}).encode())


def historique(m, actif):
    f = m.depot / "data/garage/tasmota32s3-capteurs-cuve-modbus/_persist.json"
    ancien, nouveau = ('"activation": "ON"', '"activation": "OFF"') if not actif else ('"activation": "OFF"', '"activation": "ON"')
    f.write_text(f.read_text(encoding="utf-8").replace(ancien, nouveau, 1), encoding="utf-8")


def ouvre(cdp, url):
    cdp.appel("Page.navigate", url=url)
    attend(cdp, "document.getElementById('relire') && document.getElementById('relire').textContent.indexOf('lecture') < 0"
                " && !!etat.desc && !!document.querySelector('#apercu .pg_tuile[data-rendu]')", 25)
    cdp.js("window.confirm = function(){ return true; }; 1")
    time.sleep(0.3)


def choisit_page(cdp, valeur):
    cdp.js("var s = document.getElementById('r-page'); s.value = " + json.dumps(valeur) + "; s.dispatchEvent(new Event('change')); 1")


def sonde_destination(m, capture):
    cdp = m.cdp
    url = m.url + "?env=" + CUVE
    options = "[].map.call(document.querySelectorAll('#r-page option'), function(o){ return o.value + '|' + o.textContent; })"
    # 1. menu avec historique : pages dediees, Graphiques, Autre ; plus de « + Page »
    pose_depot(m, COMPO_DEPOT)
    pose_carte(m, COMPO_DEPOT)
    ouvre(cdp, url)
    verifie(cdp.js(options), ["0|/tableau-cuve — « Tableau »", "graphiques|Graphiques (/graphiques)", "autre|Autre… (nouvelle page)"],
            "menu Page avec historique : page dediee, Graphiques (/graphiques), Autre… (nouvelle page)")
    verifie(cdp.js("[!!document.getElementById('nouvelle-page'), [].some.call(document.querySelectorAll('button'), function(b){ return b.textContent === '+ Page'; })]"),
            [False, False], "bouton « + Page » retire")
    verifie(cdp.js(CACHES), [False] * 4, "page dediee : adresse, titre, acces et solidifier visibles")
    # 2. Autre… : nouvelle page dediee, comme l'ancien « + Page »
    choisit_page(cdp, "autre")
    verifie(cdp.js("[etat.desc.pages.length, etat.page, etat.dest, document.getElementById('r-page-id').value, document.getElementById('r-page').value]"),
            [2, 1, "pages", "tableau-2", "1"], "Autre… : nouvelle page dediee creee et choisie")
    choisit_page(cdp, "0")
    # 3. Graphiques, composition identique : champs de page masques, Diff vers graphiques.json
    choisit_page(cdp, "graphiques")
    verifie(cdp.js("var s = document.getElementById('r-page'), c = document.createElement('canvas').getContext('2d'); c.font = getComputedStyle(s).font;"
                   " c.measureText('Graphiques (/graphiques)').width + 40 <= s.clientWidth"), True,
            "select Page : « Graphiques (/graphiques) » entier, non tronque")
    verifie(cdp.js(CACHES + ".concat(document.getElementById('suppr-page').offsetParent === null)"), [True] * 5,
            "destination Graphiques : adresse, titre de page, acces, solidifier (et « Retirer la page ») masques")
    verifie(bool(attend(cdp, "!document.getElementById('ecrire').disabled", 15)), True, "composition identique : diff pret, « Ecrire » actif")
    verifie(cdp.js("[etat.diff.fichiers.map(function(f){ return f.chemin; }), document.getElementById('destination').textContent]"),
            [[REL_GRAPH], "Composition de la carte identique à celle du dépôt."], "Diff vers /graphiques : graphiques.json seul")
    cdp.js("window.confirm = function(){ return true; }; document.getElementById('ecrire').click(); 1")
    verifie(attend(cdp, "document.querySelector('#message .avert.vert') !== null", 15), True, "ecriture vers /graphiques : message de reussite")
    ecrit = json.loads((m.depot / REL_GRAPH).read_text(encoding="utf-8"))
    g = ecrit.get("graphiques", [])
    verifie((len(g), g[0] if g else None, g[-1].get("moteur"), g[-1].get("type"), g[-1].get("series"), sorted(k for k in ecrit if k != "graphiques")),
            (2, COMPO_DEPOT[0], "pages", "courbe", ["sensorsCuve.niveauCuve.volume"], ["affichage"]),
            "graphiques.json de la copie : graphique en forme atelier ajoute, existant et autres cles intacts")
    verifie(cdp.js("etat.diff"), None, "apres ecriture : pas de second diff (l'ajout serait double)")
    # 4. composition differente : diff + deux choix, perte dite, rien d'ecrit sans choix
    pose_depot(m, COMPO_DEPOT)
    pose_carte(m, COMPO_CARTE)
    ouvre(cdp, url)
    choisit_page(cdp, "graphiques")
    verifie(bool(attend(cdp, "document.querySelectorAll('#destination input[name=base]').length === 2", 10)), True, "composition differente : deux choix")
    verifie(cdp.js("[].map.call(document.querySelectorAll('#destination label'), function(l){ return l.textContent.trim(); })"),
            ["Partir de la version de la carte", "Garder celle du dépôt"], "libelles des deux choix")
    verifie(cdp.js("document.getElementById('destination').textContent.indexOf('graphiques écrits dans le dépôt et pas encore téléversés seront perdus') >= 0"), True,
            "« Partir de la version de la carte » dit que les graphiques non televerses seront perdus")
    verifie(cdp.js("document.getElementById('destination').textContent.indexOf('changements faits sur la carte seront perdus à l\\'envoi') >= 0"), True,
            "« Garder celle du dépôt » dit la perte des changements de la carte")
    verifie(cdp.js("var d = document.querySelector('#destination pre'); !!d && d.textContent.indexOf('+++ carte') >= 0 && d.querySelectorAll('.p').length > 0"), True,
            "diff depot -> carte affiche")
    time.sleep(0.8)
    verifie(cdp.js("[document.getElementById('ecrire').disabled, etat.diff, document.getElementById('resume').textContent]"),
            [True, None, "choisir la version de départ de la composition : rien n'est écrit"], "sans choix : pas de diff, pas d'ecriture")
    if capture:
        cdp.js("document.getElementById('destination').scrollIntoView({block: 'center'}); 1")
        time.sleep(0.8)
        cdp.capture(str(Path(capture).with_name(Path(capture).stem + "-destination.png")))
        cdp.js("document.querySelector('label.theme').click(); 1")
        time.sleep(0.8)
        cdp.capture(str(Path(capture).with_name(Path(capture).stem + "-destination-sombre.png")))
        cdp.js("document.querySelector('label.theme').click(); 1")
    cdp.js("document.querySelector('#destination input[value=depot]').click(); 1")
    verifie(bool(attend(cdp, "!document.getElementById('ecrire').disabled", 15)), True, "choix « depot » : diff pret")
    cdp.js("document.getElementById('ecrire').click(); 1")
    attend(cdp, "document.querySelector('#message .avert.vert') !== null", 15)
    g = json.loads((m.depot / REL_GRAPH).read_text(encoding="utf-8")).get("graphiques", [])
    verifie([x.get("type") for x in g], ["courbe", "courbe"], "base depot : composition du depot + le graphique (celle de la carte perdue)")
    # 5. base carte : la composition de la carte est recopiee avant l'ajout
    pose_depot(m, COMPO_DEPOT)
    ouvre(cdp, url)
    choisit_page(cdp, "graphiques")
    attend(cdp, "document.querySelectorAll('#destination input[name=base]').length === 2", 10)
    cdp.js("document.querySelector('#destination input[value=carte]').click(); 1")
    verifie(bool(attend(cdp, "!document.getElementById('ecrire').disabled", 15)), True, "choix « carte » : diff pret")
    cdp.js("document.getElementById('ecrire').click(); 1")
    attend(cdp, "document.querySelector('#message .avert.vert') !== null", 15)
    g = json.loads((m.depot / REL_GRAPH).read_text(encoding="utf-8")).get("graphiques", [])
    verifie([x.get("type") for x in g], ["aire", "courbe", "courbe"], "base carte : composition de la carte recopiee, puis le graphique")
    # 6. choix « carte » indisponible (composition de la carte invalide) : grise, motif affiche
    pose_depot(m, COMPO_DEPOT)
    pose_carte(m, [{"moteur": "pages", "titre": "X", "type": "nimporte", "series": ["a.b"]}])
    ouvre(cdp, url)
    choisit_page(cdp, "graphiques")
    attend(cdp, "document.querySelectorAll('#destination input[name=base]').length === 2", 10)
    verifie(cdp.js("[document.querySelector('#destination input[value=carte]').disabled, document.querySelector('#destination input[value=depot]').disabled,"
                   " document.getElementById('destination').textContent.indexOf('Indisponible : ') >= 0 && etat.compo.carte_motifs.length > 0]"),
            [True, False, True], "composition de la carte invalide : « Partir de la version de la carte » grise, motif affiche")
    # 6b. ecrire, modifier, reecrire : le graphique n'est qu'une fois dans graphiques.json, modifie ; index oublie -> « ajoute » signale
    pose_depot(m, COMPO_DEPOT)
    pose_carte(m, COMPO_DEPOT)
    ouvre(cdp, url)
    choisit_page(cdp, "graphiques")
    attend(cdp, "!document.getElementById('ecrire').disabled", 15)
    cdp.js("document.getElementById('ecrire').click(); 1")
    verifie(bool(attend(cdp, "etat.indexEcrit && etat.indexEcrit.index === 1", 10)), True, "ecriture : index du graphique ecrit retenu")
    saisit(cdp, "#r-titre", "Titre change")
    verifie(bool(attend(cdp, "!document.getElementById('ecrire').disabled", 15)), True, "apres modification : diff pret")
    verifie(cdp.js("[corpsEcriture().operation, corpsEcriture().index]"), ["remplace", 1], "reecriture : operation remplace a l'index retenu")
    cdp.js("document.getElementById('ecrire').click(); 1")
    attend(cdp, "document.querySelector('#message .avert.vert') !== null && etat.diff === null", 10)
    g = json.loads((m.depot / REL_GRAPH).read_text(encoding="utf-8")).get("graphiques", [])
    verifie([x.get("titre") for x in g], ["Cuve", "Titre change"], "ecrire, modifier, reecrire : le graphique une seule fois, modifie")
    pose_depot(m, COMPO_DEPOT + [{"moteur": "pages", "titre": "Autre", "type": "courbe", "series": ["sensorsCuve.niveauCuve.volume"]}])
    n0 = len(cdp.erreurs())                          # le graphique du depot a ce rang a change : 409 attendu, ce scenario seulement
    saisit(cdp, "#r-titre", "Encore")
    verifie(bool(attend(cdp, "etat.indexEcrit === null && document.getElementById('message').textContent.indexOf('sera ajouté de nouveau') >= 0", 15)),
            True, "index disparu : retour a « ajoute », signale")
    verifie(bool(attend(cdp, "!document.getElementById('ecrire').disabled && corpsEcriture().operation === 'ajoute'", 15)), True,
            "apres l'oubli : diff « ajoute » pret")
    ERREURS_ATTENDUES.extend(e for e in cdp.erreurs()[n0:] if "/diff" in e and "409" in e)
    choisit_page(cdp, "autre")
    verifie(cdp.js("etat.indexEcrit"), None, "choisir « Autre… » : index oublie")
    # 6c. ecrire, retirer le graphique, en ajouter un autre, ecrire : les deux graphiques sont dans la composition
    pose_depot(m, COMPO_DEPOT)
    ouvre(cdp, url)
    choisit_page(cdp, "graphiques")
    attend(cdp, "!document.getElementById('ecrire').disabled", 15)
    cdp.js("document.getElementById('ecrire').click(); 1")
    attend(cdp, "etat.indexEcrit", 10)
    cdp.js("document.getElementById('suppr-graphique').click(); document.getElementById('ajout-graphique').click(); 1")
    verifie(cdp.js("etat.indexEcrit"), None, "retirer / ajouter un graphique : index oublie")
    saisit(cdp, "#r-titre", "Second")
    verifie(bool(attend(cdp, "!document.getElementById('ecrire').disabled && corpsEcriture().operation === 'ajoute'", 15)), True, "second graphique : « ajoute »")
    cdp.js("document.getElementById('ecrire').click(); 1")
    attend(cdp, "etat.indexEcrit && etat.indexEcrit.index === 2", 10)
    g = json.loads((m.depot / REL_GRAPH).read_text(encoding="utf-8")).get("graphiques", [])
    verifie([x.get("titre") for x in g], ["Cuve", "volume", "Second"], "retirer puis ajouter : les deux graphiques ecrits, aucun ecrase")
    # 6d. carte hors ligne alors que la destination est Graphiques : l'option reste dans le menu
    pose_carte(m, "HORSLIGNE")
    cdp.js("chargeCompo().then(function(){ etat.compo = null; dessinePages(); }); 1")
    time.sleep(0.5)
    verifie(cdp.js("[document.getElementById('r-page').value, document.getElementById('r-page').selectedOptions.length]"), ["graphiques", 1],
            "compo inconnue pendant la destination Graphiques : option conservee, select jamais vide")
    pose_carte(m, COMPO_DEPOT)
    # 7. carte hors ligne : bandeau « non verifiee » avec le motif
    pose_carte(m, "HORSLIGNE")
    ouvre(cdp, url)
    choisit_page(cdp, "graphiques")
    verifie(bool(attend(cdp, "document.querySelector('#destination .avert') !== null", 10)), True, "carte hors ligne : bandeau")
    verifie(cdp.js("var t = document.getElementById('destination').textContent; [t.indexOf('Composition de la carte non vérifiée') >= 0, t.indexOf('carte hors ligne') >= 0,"
                   " document.querySelectorAll('#destination input').length]"), [True, True, 0], "bandeau « non verifiee » avec son motif, sans choix")
    verifie(bool(attend(cdp, "!document.getElementById('ecrire').disabled", 15)), True, "carte hors ligne : l'ecriture depuis le depot reste possible")
    # 8. sans historique : « Graphiques » absent du menu
    pose_carte(m, COMPO_DEPOT)
    historique(m, False)
    ouvre(cdp, url)
    verifie(cdp.js(options), ["0|/tableau-cuve — « Tableau »", "autre|Autre… (nouvelle page)"], "menu Page sans historique : pas de Graphiques")
    historique(m, True)
    verifie([e for e in cdp.erreurs() if e not in ERREURS_ATTENDUES], [], "destination : aucune erreur JS (hors le refus attendu du scenario « index change »)")


def sonde_televerse(m):
    """Bouton « Televerser » (A6) : absent avant l'ecriture, present apres, masque a la modification suivante ; ouvre l'URL de
    la page Build (window.open intercepte) ; page Build arretee -> message, aucun onglet."""
    cdp = m.cdp
    pose_carte(m, COMPO_DEPOT)
    arret = m.t / "outils" / "build_arrete"
    arret.unlink(missing_ok=True)
    ouvre(cdp, m.url + "?env=" + CUVE)
    cdp.js("window.ouverts = []; window.open = function(u, c){ window.ouverts.push([u, c]); return null; }; 1")
    cache = "document.getElementById('televerser').offsetParent === null"
    verifie(cdp.js(cache), True, "Televerser : bouton absent avant l'ecriture")
    saisit(cdp, "#r-titre", "Titre televerse")
    attend(cdp, "!document.getElementById('ecrire').disabled", 15)
    cdp.js("document.getElementById('ecrire').click(); 1")
    verifie(bool(attend(cdp, "!(" + cache + ")", 15)), True, "Televerser : bouton present apres l'ecriture")
    verifie(cdp.js("document.getElementById('tv-info').textContent.indexOf('fichier(s) à téléverser') > 0"), True,
            "Televerser : nombre de fichiers affiche")
    cdp.js("document.getElementById('televerser').click(); 1")       # sonde la page Build au clic (GET /build_actif)
    attend(cdp, "window.ouverts.length > 0", 10)
    ouverts = cdp.js("window.ouverts")
    voulu = {"env": [CUVE], "depuis": ["atelier"], "redemarrer": ["0"]}
    from urllib.parse import parse_qs, urlsplit
    u = urlsplit(ouverts[0][0]) if ouverts else None
    q = parse_qs(u.query) if u else {}
    fichiers = q.get("fichiers", [""])[0].split(",")
    verifie((len(ouverts), ouverts[0][1] if ouverts else None, u and u.netloc, {k: q.get(k) for k in voulu}), (1, "_blank", "127.0.0.1:7700", voulu),
            "Televerser : window.open(_blank) sur la page Build, env, depuis=atelier, redemarrer=0")
    verifie("pages_graphiques.json" in fichiers, True, "Televerser : pages_graphiques.json dans fichiers=")
    saisit(cdp, "#r-titre", "Autre titre")
    verifie(bool(attend(cdp, cache, 5)), True, "Televerser : masque de nouveau a la modification suivante")
    attend(cdp, "!document.getElementById('ecrire').disabled", 15)
    cdp.js("document.getElementById('ecrire').click(); 1")
    attend(cdp, "!(" + cache + ")", 15)
    arret.write_text("x")                                  # page Build arretee APRES l'ecriture : seule la sonde au clic le voit
    cdp.js("window.ouverts = []; document.getElementById('televerser').click(); 1")
    attend(cdp, "document.getElementById('message').textContent.indexOf('annuaire') >= 0", 10)
    verifie((cdp.js("window.ouverts.length"), cdp.js("document.getElementById('message').textContent.indexOf('annuaire') >= 0")), (0, True),
            "Televerser : page Build arretee -> message « lancer par l'annuaire », pas d'onglet")
    arret.unlink(missing_ok=True)
    verifie([e for e in cdp.erreurs() if e not in ERREURS_ATTENDUES], [], "Televerser : aucune erreur JS")


def sonde_temoin(m):
    m.cdp.appel("Page.navigate", url=m.url)
    time.sleep(4)
    verifie(len(m.cdp.erreurs()) > 0, True, "TEMOIN : l'erreur JS volontaire est detectee")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de la page de l'atelier des graphiques.")
    options.add_argument("--sans-temoin", action="store_true")
    options.add_argument("--capture", help="capture PNG de la page a 1400 px")
    options.add_argument("--serveur", nargs=2, metavar=("PORT", "DEPOT"), help=argparse.SUPPRESS)
    options.add_argument("--temoin", action="store_true", help=argparse.SUPPRESS)
    args = options.parse_args()
    sys.stdout.reconfigure(errors="replace")        # console cp1252 : un caractere hors table ne tue pas la sonde
    if args.serveur:
        return mode_serveur(int(args.serveur[0]), args.serveur[1], args.temoin)
    for temoin in ([False] if args.sans_temoin else [False, True]):
        print(f"\n=== {'TEMOIN (erreur JS volontaire)' if temoin else 'page reelle'} ===", flush=True)
        m = None
        try:
            m = Montage()
            m.demarre(temoin)
            sonde_temoin(m) if temoin else (sonde_page(m, args.capture), sonde_destination(m, args.capture), sonde_televerse(m))
        except FileNotFoundError as erreur:
            print(f"BLOQUE : {erreur}")
            return 3
        except Exception as erreur:
            verifie(repr(erreur), "pas d'exception de la sonde", "sonde : deroulement")
        finally:
            if m:
                m.ferme()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
