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
    build_ota_http._get = fausse_carte
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
            sonde_temoin(m) if temoin else sonde_page(m, args.capture)
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
