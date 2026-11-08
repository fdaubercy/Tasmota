"""Sonde Chrome de la page « Energie (/energie) » de l'atelier des graphiques (plan energie-atelier A5, spec 2026-11-08 §4.3).

UTILISATION (a la main ; aucun pio, aucune carte, aucun envoi ; Chrome tourne ~1 min)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_energie_page_chrome.py
        [--capture FICHIER.png] [--sans-temoin] [--mutant archive|mobile|absent]
Code de sortie 0 = vert : la vraie page passe tout ET le temoin (erreur JS volontaire au chargement) est detecte.
`--mutant` = copie MUTEE de la page, qui doit sortir ROUGE : `archive` (l'avertissement « mois fixe sans archive » ne se declenche
plus, A5 « a surveiller » 2), `mobile` (la regle 390 px est retiree, « a surveiller » 5), `absent` (le module JS de la page n'est pas charge : etat de depart du TDD).

Montage : atelier_graphiques_web.py dans un processus fils devant une COPIE du depot (celle du banc test_atelier_graphiques_energie) ;
la carte est simulee en remplacant build_ota_http._get dans ce processus (aucun reseau) : `/energie?f=description` rend le fichier
`energie_desc.json` du dossier de la sonde (absent : 404 ; `energie_ancien` present : la page HTML en 200 = ancien firmware),
`Status 10` rend un bloc ENERGY, tout le reste est muet (apercu aux valeurs simulees). Detection des builds neutralisee.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre, tue_arbre

ECHECS = []
CUVE, BUREAU = "tasmota32s3-garage-capteurs-cuve-modbus", "tasmota32-bureau-interrupteur-energie"
MARQUE_TEMOIN = "var gabarit = '', apercuCtrl = null"
INJECTION_TEMOIN = "\n$('bouton-qui-n-existe-pas').onclick = null;   // TEMOIN : TypeError au chargement\n"
MUTANTS = {"archive": ("etat.en.archives[m] === 404", "etat.en.archives[m] === 405"),
           "absent": (None, ""),
           "mobile": ("@media (max-width:900px){.colonnes", "@media (max-width:1px){.colonnes")}
HTML = b"<!DOCTYPE html><html><body>Energie</body></html>"
ENERGY = {"Power": 1200, "Current": 5.2, "Factor": 0.98, "Voltage": 230, "Today": 3.1, "Total": 1234.5}
FICHIERS = ["energie_page.json", "sd/js/energie.js", "sd/html/energie.html", "sd/css/energie.css"]


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)
    return ok


def fausse_carte(ip, chemin, delai):
    dossier = Path(os.environ["OUTILS_TASMOTA_DOSSIER"])
    if chemin == "/energie?f=description":
        f = dossier / "energie_desc.json"
        if (dossier / "energie_ancien").exists():
            return HTML
        if f.is_file():
            return f.read_bytes()
        raise urllib.error.HTTPError("http://" + ip + chemin, 404, "Not Found", {}, None)
    if chemin.startswith("/cm?") and "Status" in chemin:
        return json.dumps({"StatusSNS": {"Time": "x", "ENERGY": ENERGY}}).encode()
    raise OSError("carte muette")


def mode_serveur(port, depot, mutant, temoin):
    import atelier_graphiques_page
    import atelier_graphiques_televerse as agt
    import atelier_graphiques_web as agw
    import build_ota_http
    if temoin:
        assert atelier_graphiques_page.PAGE.count(MARQUE_TEMOIN) == 1
        atelier_graphiques_page.PAGE = atelier_graphiques_page.PAGE.replace(MARQUE_TEMOIN, INJECTION_TEMOIN + MARQUE_TEMOIN)
    if mutant:
        ancien, nouveau = MUTANTS[mutant]
        if ancien is None:             # module de la page absent : la sonde doit etre rouge (TDD)
            from atelier_graphiques_page_energie import JS_ENERGIE
            ancien = JS_ENERGIE
        assert atelier_graphiques_page.PAGE.count(ancien) == 1, "marque du mutant introuvable dans la page"
        atelier_graphiques_page.PAGE = atelier_graphiques_page.PAGE.replace(ancien, nouveau)
    build_ota_http._get = fausse_carte
    agt.build_actif = lambda port=agt.PORT_BUILD: True
    agw.DEPOT = Path(depot)
    agw.builds_en_cours_defaut = lambda: []
    sys.argv = ["atelier_graphiques_web.py", "--http", str(port), "--local", "--sans-navigateur"]
    return agw.principal()


def monte_depot(t):
    import test_atelier_graphiques_energie as taeg
    import test_atelier_graphiques_web as taw
    depot = taeg.depot(t)
    for rel in taw.SD:
        (depot / "data/sd" / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(taw.DEPOT / "data/sd" / rel, depot / "data/sd" / rel)
    return depot


class Montage:
    def __init__(self, mutant=None):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_atelier_energie_"))
        self.mutant = mutant
        self.serveur = self.chrome = None

    def demarre(self, temoin):
        self.outils = self.t / "outils"
        self.outils.mkdir()
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(self.outils)
        self.depot = monte_depot(self.t)
        self.fichier = self.depot / "data/bureau/tasmota32-interrupteur-energie/energie_page.json"
        self.port = port_libre()
        self.url = f"http://127.0.0.1:{self.port}/"
        commande = [sys.executable, "-u", str(Path(__file__).resolve()), "--serveur", str(self.port), str(self.depot)]
        if temoin:
            commande.append("--temoin")
        if self.mutant:
            commande += ["--mutant", self.mutant]
        self.serveur = subprocess.Popen(commande, env=dict(os.environ, PYTHONIOENCODING="utf-8"), stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self._attend_http(self.url + "moteur/energie.js", 30)
        chrome = next((c for c in CHROMES if c.is_file()), None)
        if chrome is None:
            raise FileNotFoundError("chrome.exe introuvable (Program Files, LOCALAPPDATA)")
        self.port_cdp = port_libre()
        self.chrome = subprocess.Popen([str(chrome), "--headless=new", f"--remote-debugging-port={self.port_cdp}",
                                        "--remote-allow-origins=*", f"--user-data-dir={self.t / 'profil'}",
                                        "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                                        "--window-size=1400,1000", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cibles = self._attend_http(f"http://127.0.0.1:{self.port_cdp}/json/list", 20)
        page = next(c for c in json.loads(cibles) if c.get("type") == "page")
        self.cdp = Cdp(page["webSocketDebuggerUrl"])
        for domaine in ("Runtime.enable", "Log.enable", "Page.enable"):
            self.cdp.appel(domaine)
        self.large()
        self.cdp.appel("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"}])

    def large(self, largeur=1400):
        self.cdp.appel("Emulation.setDeviceMetricsOverride", width=largeur, height=1000, deviceScaleFactor=1, mobile=False)

    def _attend_http(self, url, delai):
        import urllib.request
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


def description(titre="Depuis la carte"):
    import atelier_energie_description as aed
    d = json.loads(json.dumps(aed.DEFAUT))
    d["elements"][0]["titre"] = titre
    return d


def ouvre(m, env=BUREAU):
    """Charge la page sur la cuve puis bascule sur le differentiel par le menu des cartes (le chemin d'un vrai changement d'env)."""
    cdp = m.cdp
    cdp.appel("Page.navigate", url=m.url + "?env=" + CUVE)
    attend(cdp, "!!window.etat && !!etat.desc && document.getElementById('relire').textContent.indexOf('lecture') < 0", 25)
    cdp.js("window.confirm = function(){ return true; }; window.ouverts = []; window.open = function(u, c){ window.ouverts.push([u, c]); return null; }; 1")
    cdp.js("var s = document.getElementById('env'); s.value = " + json.dumps(env) + "; s.dispatchEvent(new Event('change')); 1")
    attend(cdp, "etat.dest === 'energie' && !!document.querySelector('#a_grille[data-pret]') && !document.getElementById('ecrire').disabled || "
                "(etat.dest === 'energie' && !!document.querySelector('#energie-ed input[name=base-en]'))", 25)
    time.sleep(0.3)


def js_champ(cdp, selecteur, valeur, evenement="input"):
    cdp.js("var i = document.querySelector(" + json.dumps(selecteur) + "); i.value = " + json.dumps(valeur)
           + "; i.dispatchEvent(new Event(" + json.dumps(evenement) + ", {bubbles: true})); 1")


def erreurs(cdp, mois_404=False):
    """Erreurs de la page ; `mois_404` ecarte le journal Chrome des 404 de f=mois, seulement dans le scenario qui attend un mois sans archive."""
    return [e for e in cdp.erreurs() if not (mois_404 and "f=mois" in e and "404" in e)]


def clic(cdp, selecteur):
    cdp.js("document.querySelector(" + json.dumps(selecteur) + ").click(); 1")


def attend_apercu(cdp, delai=15):
    cdp.js("var g = document.getElementById('a_grille'); if (g) g.removeAttribute('data-pret'); 1")
    return attend(cdp, "!!document.querySelector('#a_grille[data-pret]') && !document.getElementById('ecrire').disabled", delai)


def sonde_edition(m, capture):
    cdp = m.cdp
    ouvre(m)
    options = cdp.js("Array.from(document.querySelectorAll('#r-page option')).map(function(o){ return o.textContent; })")
    verifie(options, ["Énergie (/energie)"], "menu « Page » : « Énergie (/energie) » seul")
    verifie(cdp.js("['intention', 'arbre', 'r-titre', 'r-periode', 'ajout-graphique', 'r-page-id'].map(function(i){ return document.getElementById(i).offsetParent === null; })"),
            [True] * 6, "reglages des pages de graphiques masques")
    verifie(cdp.js("etat.desc.elements.length + ' ' + document.querySelectorAll('#en-liste li').length + ' ' + document.querySelectorAll('#a_grille > *').length"),
            "8 8 8", "description de depart = DEFAUT : 8 elements dans la liste et dans la grille")
    verifie(cdp.js("JSON.stringify(etat.desc) === JSON.stringify(Energie.DEFAUT)"), True, "depart = Energie.DEFAUT (le depot n'a pas de fichier)")
    verifie(cdp.js("document.querySelectorAll('#a_grille svg').length > 0"), True, "apercu trace par energie.js (SVG present)")
    verifie(cdp.js("document.getElementById('e_grille')"), None, "aucun element e_grille : energie.js ne s'est pas lance seul")
    # un demi-cercle sur Power, couleur, hauteur grande, en tete
    clic(cdp, "#en-ajout")
    attend(cdp, "!!document.getElementById('en-type')", 5)
    js_champ(cdp, "#en-type", "demi-cercle", "change")
    attend(cdp, "!!document.getElementById('en-min')", 5)
    js_champ(cdp, "#en-titre", "Puissance (jauge)")
    js_champ(cdp, "#en-couleur", "#e03030", "change")
    js_champ(cdp, "#en-hauteur", "grande", "change")
    clic(cdp, "#en-liste li.sel [data-act=tete]")
    attend(cdp, "etat.desc.elements[0].titre === 'Puissance (jauge)'", 5)
    e0 = cdp.js("etat.desc.elements[0]")
    verifie(e0, {"type": "demi-cercle", "titre": "Puissance (jauge)", "source": {"direct": "Power"}, "unite": "W", "couleur": "#e03030",
                 "largeur": "demi", "hauteur": "grande", "min": 0, "max": 3000}, "demi-cercle sur Power, couleur, hauteur grande, en tete")
    verifie(cdp.js("document.querySelectorAll('#en-liste li').length + ' ' + document.querySelector('#en-liste li .lib').textContent"),
            "9 1. Puissance (jauge)", "liste : 9 elements, le nouveau en premier")
    attend_apercu(cdp)
    verifie(cdp.js("var a = document.querySelector('#a_grille #e_el0 .e_arc'); [!!document.querySelector('#a_grille #e_el0 .e_dem'), a && a.getAttribute('stroke')]"),
            [True, "#e03030"], "apercu : demi-cercle en tete, arc de la couleur choisie")
    verifie(cdp.js("getComputedStyle(document.getElementById('en-forme')).display"), "block", "formulaire de l'element visible")
    # graphique « jour » : mois precedent (archive presente), puis mois fixe sans archive
    clic(cdp, "#en-ajout")
    attend(cdp, "!!document.getElementById('en-source')", 5)
    js_champ(cdp, "#en-source", "f:jour:kWh", "change")
    attend(cdp, "!!document.getElementById('en-mois-mode')", 5)
    js_champ(cdp, "#en-mois-mode", "relatif", "change")
    attend(cdp, "!!document.getElementById('en-decalage')", 5)
    verifie(cdp.js("var e = etat.desc.elements[etat.en.sel]; [e.type, e.largeur, e.source]"), ["barres", "pleine", {"flash": "jour", "grandeur": "kWh", "decalage": 1}],
            "source historique « jour » : style barres, pleine largeur, decalage 1 (mois precedent)")
    verifie(cdp.js("Array.from(document.querySelectorAll('#en-type option')).map(function(o){ return o.value; })"), ["barres", "courbe", "aire", "escalier"],
            "styles restreints a ceux d'une source historique")
    attend_apercu(cdp)
    verifie(cdp.js("document.getElementById('alertes').textContent.indexOf('archive') >= 0"), False, "mois precedent : archive presente, pas d'avertissement")
    js_champ(cdp, "#en-mois-mode", "fixe", "change")
    attend(cdp, "!!document.getElementById('en-mois')", 5)
    js_champ(cdp, "#en-mois", "2020-01")
    attend_apercu(cdp)
    verifie(bool(attend(cdp, "document.getElementById('alertes').textContent.indexOf('2020-01') >= 0", 10)), True,
            "mois fixe sans archive (f=mois en 404) : avertissement avant l'ecriture")
    verifie(cdp.js("var e = etat.desc.elements[etat.en.sel]; e.source.mois"), "2020-01", "source : mois fixe 2020-01")
    js_champ(cdp, "#en-mois", "2020-13")
    verifie(bool(attend(cdp, "document.getElementById('motifs').textContent.indexOf('mois AAAA-MM') >= 0 && document.getElementById('ecrire').disabled", 10)), True,
            "mois mal forme : motif de la carte, Ecrire grise")
    js_champ(cdp, "#en-mois", "2020-01")
    attend_apercu(cdp)
    if capture:
        cdp.capture(capture)
    verifie(erreurs(cdp, True), [], "edition : aucune erreur JS (hors les 404 attendus de f=mois)")


def sonde_ecriture(m):
    cdp = m.cdp
    verifie(cdp.js("document.getElementById('televerser').offsetParent === null"), True, "Televerser absent avant l'ecriture")
    verifie(cdp.js("Array.from(document.querySelectorAll('#onglets button')).map(function(b){ return b.textContent; })")[0].startswith("energie_page.json"), True,
            "diff : energie_page.json")
    voulu = cdp.js("etat.desc")
    clic(cdp, "#ecrire")
    attend(cdp, "document.getElementById('message').textContent.indexOf('Écrit') === 0", 15)
    verifie(m.fichier.is_file() and json.loads(m.fichier.read_text(encoding="utf-8")) == voulu, True, "ecriture : energie_page.json du depot copie = la description")
    verifie(m.fichier.stat().st_size <= 4096, True, "ecriture : au plus 4096 octets")
    verifie(bool(attend(cdp, "document.getElementById('televerser').offsetParent !== null", 10)), True, "Televerser visible apres l'ecriture")
    verifie(cdp.js("etat.tv.fichiers"), FICHIERS, "Televerser : les 4 fichiers de la page Energie")
    clic(cdp, "#televerser")
    attend(cdp, "window.ouverts.length > 0", 10)
    u = cdp.js("window.ouverts[0] && window.ouverts[0][0]") or ""
    verifie(u.startswith("http://127.0.0.1:7700/?") and "energie_page.json" in u.replace("%2C", ","), True, "Televerser : ouvre la page Build avec les 4 fichiers")
    js_champ(cdp, "#en-titre", "Autre titre")
    verifie(bool(attend(cdp, "document.getElementById('televerser').offsetParent === null", 5)), True, "Televerser masque a la modification suivante")


def sonde_firmware(m):
    cdp = m.cdp
    (m.outils / "energie_ancien").write_text("x")
    ouvre(m)
    verifie(cdp.js("document.getElementById('energie-ed').textContent.indexOf('firmware') >= 0"), True, "ancien firmware : message avant toute ecriture")
    clic(cdp, "#en-ajout")
    attend_apercu(cdp)
    clic(cdp, "#ecrire")
    attend(cdp, "document.getElementById('message').textContent.indexOf('Écrit') === 0", 15)
    verifie(cdp.js("document.getElementById('televerser').offsetParent === null"), True, "ancien firmware : pas de bouton Televerser")
    verifie(cdp.js("document.getElementById('tv-info').textContent.indexOf('firmware') >= 0"), True, "ancien firmware : message firmware apres l'ecriture")
    (m.outils / "energie_ancien").unlink()


def sonde_difference(m):
    """Carte != depot : le choix « carte / depot » avant toute modification (spec §4.3)."""
    cdp = m.cdp
    carte = description("Depuis la carte")
    (m.outils / "energie_desc.json").write_text(json.dumps(carte, separators=(",", ":")), encoding="utf-8")
    ouvre(m)
    verifie(cdp.js("[document.querySelectorAll('input[name=base-en]').length, etat.desc, !!document.getElementById('en-forme'), !!document.getElementById('en-liste'), "
                   "document.getElementById('ecrire').disabled, document.querySelector('#energie-ed pre').textContent.length > 0]"),
            [2, None, False, False, True, True], "carte != depot : deux choix, diff affiche, ni liste ni formulaire, rien d'ecrit sans choix")
    clic(cdp, "input[name=base-en][value=carte]")
    attend(cdp, "!!etat.desc && !!document.getElementById('en-liste')", 10)
    verifie(cdp.js("[etat.base, etat.desc.elements[0].titre]"), ["carte", "Depuis la carte"], "choix « carte » : depart = la description de la carte")
    clic(cdp, "input[name=base-en][value=depot]")
    attend(cdp, "etat.base === 'depot'", 10)
    depot = json.loads(m.fichier.read_text(encoding="utf-8"))
    verifie(cdp.js("etat.desc.elements.length"), len(depot["elements"]), "choix « depot » : depart = le fichier du depot")
    verifie(erreurs(cdp), [], "carte != depot : aucune erreur JS")
    (m.outils / "energie_desc.json").unlink()


def carte_comme_depot(m):
    """La carte rend la description du depot (si le depot en a une) : etat « identique », pas de choix a faire."""
    f = m.outils / "energie_desc.json"
    f.unlink(missing_ok=True)
    if m.fichier.is_file():
        f.write_bytes(m.fichier.read_bytes())


def sonde_quitte(m):
    """Differentiel -> cuve : plus rien de la page Energie (liste, formulaire, etat), menu « Page » de la cuve, aucune erreur."""
    cdp = m.cdp
    carte_comme_depot(m)
    ouvre(m)
    n0 = len(cdp.erreurs())
    cdp.js("var s = document.getElementById('env'); s.value = " + json.dumps(CUVE) + "; s.dispatchEvent(new Event('change')); 1")
    attend(cdp, "etat.dest === 'pages' && !!etat.desc && !!etat.desc.pages && document.getElementById('relire').textContent.indexOf('lecture') < 0", 25)
    verifie(cdp.js("[document.getElementById('energie-ed').children.length, etat.en === null || etat.en === undefined, document.body.classList.contains('energie')]"),
            [0, True, False], "differentiel -> cuve : #energie-ed vide, etat Energie oublie, mode Energie retire")
    verifie(cdp.js("Array.from(document.querySelectorAll('#r-page option')).map(function(o){ return o.textContent.indexOf('Énergie') >= 0; }).some(Boolean)"),
            False, "differentiel -> cuve : menu « Page » de la cuve retabli")
    cdp.js("var b = document.getElementById('en-ajout'); if (b) b.click(); 1")
    time.sleep(0.5)
    verifie(cdp.erreurs()[n0:], [], "differentiel -> cuve : aucune erreur JS, meme apres un clic residuel sur « + Element »")


def sonde_mobile(m):
    cdp = m.cdp
    carte_comme_depot(m)
    ouvre(m)
    m.large(390)
    time.sleep(0.5)
    clic(cdp, "[data-vue=telephone]")
    attend_apercu(cdp)
    mesures = cdp.js("[document.documentElement.scrollWidth, document.documentElement.clientWidth, "
                     "getComputedStyle(document.getElementById('a_grille')).gridTemplateColumns.split(' ').length]")
    verifie(mesures[0] <= mesures[1], True, f"390 px : aucun defilement horizontal ({mesures[0]} / {mesures[1]})")
    verifie(mesures[2], 1, "390 px : apercu sur une colonne")
    m.large(1400)
    verifie(erreurs(cdp), [], "390 px : aucune erreur JS")


def sonde_sombre(m):
    cdp = m.cdp
    carte_comme_depot(m)
    ouvre(m)
    cdp.js("document.querySelector('label.theme').click(); 1")
    verifie(cdp.js("getComputedStyle(document.getElementById('en-titre')).backgroundColor"), "rgb(21, 23, 27)", "mode sombre de la page : champs du formulaire sombres")
    clic(cdp, "#sombre")
    verifie(cdp.js("document.getElementById('cadre').classList.contains('sombre')"), True, "theme sombre de l'apercu")
    cdp.js("document.querySelector('label.theme').click(); 1")


SONDES = {"edition": sonde_edition, "ecriture": sonde_ecriture, "firmware": sonde_firmware, "difference": sonde_difference,
          "quitte": sonde_quitte, "mobile": sonde_mobile, "sombre": sonde_sombre}


def sonde_temoin(m):
    m.cdp.appel("Page.navigate", url=m.url)
    fin = time.time() + 30
    while not m.cdp.erreurs() and time.time() < fin:
        time.sleep(0.5)
    verifie(len(m.cdp.erreurs()) > 0, True, "TEMOIN : l'erreur JS volontaire est detectee")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de la page Energie de l'atelier des graphiques.")
    options.add_argument("--sans-temoin", action="store_true")
    options.add_argument("--capture")
    options.add_argument("--mutant", choices=sorted(MUTANTS))
    options.add_argument("--seulement", nargs="+", choices=sorted(SONDES), help="ne lancer que ces sondes (mise au point)")
    options.add_argument("--serveur", nargs=2, metavar=("PORT", "DEPOT"), help=argparse.SUPPRESS)
    options.add_argument("--temoin", action="store_true", help=argparse.SUPPRESS)
    args = options.parse_args()
    sys.stdout.reconfigure(errors="replace")
    if args.serveur:
        return mode_serveur(int(args.serveur[0]), args.serveur[1], args.mutant, args.temoin)
    for temoin in ([False] if args.sans_temoin or args.mutant else [False, True]):
        print(f"\n=== {'TEMOIN (erreur JS volontaire)' if temoin else 'page ' + ('MUTEE ' + args.mutant if args.mutant else 'reelle')} ===", flush=True)
        m = None
        try:
            m = Montage(args.mutant)
            m.demarre(temoin)
            if temoin:
                sonde_temoin(m)
            else:
                for nom in args.seulement or SONDES:
                    SONDES[nom](m, args.capture) if nom == "edition" else SONDES[nom](m)
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
