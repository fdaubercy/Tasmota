"""Sonde Chrome de la page « Assistant persist » (assistant_persist_page.PAGE) : la page s'execute-t-elle ?

UTILISATION (a la main ; aucun pio n'est lance, Chrome tourne ~40 s)
    python outils_docs/scripts_python/outils_pc/test_assistant_persist_page_chrome.py [--sans-temoin]
Code de sortie 0 = vert : la vraie page passe toutes les verifications ET le temoin (la meme page avec un
identifiant DOM casse, id="creer") est detecte par Runtime.exceptionThrown. Client DevTools repris de
test_build_page_chrome.py.

Montage : assistant_persist_web.py dans un processus fils (mode --serveur), devant un depot d'essai (copie des .ini,
du .h, des dossiers de carte, de data/fs, du modele et du schema) dans un dossier temporaire ; detection des builds
neutralisee ; OUTILS_TASMOTA_DOSSIER temporaire. Le vrai depot n'est jamais ecrit.
Scenario : chaque pastille affiche son etape ; changer le nom change le hostname de l'apercu ; Esclave -> liste des
maitres non vide ; RTC coche i2c d'office (grise, avec sa raison) ; historique grise sur ESP32 ; zero metier -> « Voir le
diff » grise ; apres le diff, « Creer l'env » actif, puis grise des qu'on saisit quoi que ce soit ; creation reelle dans
le depot d'essai (fichiers ecrits, liens, resume) ; aucun mot de passe du parc dans le DOM ; 0 erreur JS.
"""

import argparse
import json
import os
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
ENV = "tasmota32s3-garage-piscine"
DOSSIER = "data/garage/tasmota32s3-piscine"
CASSE = 'id="creer"'
CASSE_PAR = 'id="creer-casse"'
IP_CAVE_S3 = "192.168.0.243"                  # IPAddress du persist de data/cave/tasmota32s3-serveur-rly


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)
    return ok


def mode_serveur(port, depot, temoin):
    import assistant_persist_web as apw
    if temoin:
        import assistant_persist_page
        assert assistant_persist_page.PAGE.count(CASSE) == 1, "identifiant a casser introuvable dans la page"
        copie = assistant_persist_page.PAGE.replace(CASSE, CASSE_PAR)
        apw.page = lambda: copie
    apw.DEPOT = Path(depot)
    apw.builds_en_cours_defaut = lambda: []
    sys.argv = ["assistant_persist_web.py", "--http", str(port), "--local", "--sans-navigateur"]
    return apw.principal()


class Montage:
    def __init__(self):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_assistant_persist_"))
        self.serveur = self.chrome = None

    def demarre(self, temoin):
        import test_assistant_persist_creation as tac
        self.depot = tac.depot(self.t)
        import test_assistant_persist_fidelite as taf          # une cle nouvelle du parc : le demarrage la fusionne, bandeau present
        for rel in taf.deux_puces(self.depot):
            taf.pose(self.depot, rel, "serveur.udp.essai", 7)
        environ = dict(os.environ, OUTILS_TASMOTA_DOSSIER=str(self.t / "outils"), PYTHONIOENCODING="utf-8")
        self.port = port_libre()
        self.url = f"http://127.0.0.1:{self.port}/"
        commande = ([sys.executable, "-u", str(Path(__file__).resolve()), "--serveur", str(self.port), str(self.depot)]
                    + (["--temoin"] if temoin else []))
        self.serveur = subprocess.Popen(commande, env=environ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self._attend_http(self.url + "execution", 20)
        chrome = next((c for c in CHROMES if c.is_file()), None)
        if chrome is None:
            raise FileNotFoundError("chrome.exe introuvable (Program Files, LOCALAPPDATA)")
        self.port_cdp = port_libre()
        self.chrome = subprocess.Popen([str(chrome), "--headless=new", f"--remote-debugging-port={self.port_cdp}",
                                        "--remote-allow-origins=*", f"--user-data-dir={self.t / 'profil'}",
                                        "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                                        "--window-size=1280,1000", "about:blank"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cibles = self._attend_http(f"http://127.0.0.1:{self.port_cdp}/json/list", 20)
        page = next(c for c in json.loads(cibles) if c.get("type") == "page")
        self.cdp = Cdp(page["webSocketDebuggerUrl"])
        for domaine in ("Runtime.enable", "Log.enable", "Page.enable"):
            self.cdp.appel(domaine)

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
        import shutil
        shutil.rmtree(self.t, ignore_errors=True)


def clic(cdp, ident):
    return cdp.js(f"(function(){{var e=document.getElementById({json.dumps(ident)}); if(!e) return 'absent'; e.click(); return 'ok';}})()")


def saisit(cdp, ident, valeur, evenement="input"):
    return cdp.js("(function(){var e=document.getElementById(" + json.dumps(ident) + "); if(!e) return 'absent'; e.value=" +
                  json.dumps(valeur) + "; e.dispatchEvent(new Event(" + json.dumps(evenement) + ", {bubbles: true})); return 'ok';})()")


def visible(cdp, ident):
    return cdp.js(f"!document.getElementById({json.dumps(ident)}).classList.contains('cache')")


def sonde_page(m):
    import test_assistant_persist_web as taw
    cdp = m.cdp
    # page chargee sous un AUTRE hote que 127.0.0.1 (celui des liens du serveur) : les liens doivent suivre la page
    cdp.appel("Page.navigate", url=m.url.replace("127.0.0.1", "localhost"))
    verifie(attend(cdp, "document.getElementById('f-puce') && document.getElementById('f-puce').options.length === 3", 15), True,
            "chargement : les 3 puces dans la liste")
    verifie(attend(cdp, "document.getElementById('apercu').textContent.indexOf('\"serveur\"') >= 0", 15), True,
            "chargement : apercu du persist rempli")
    verifie(attend(cdp, "!document.getElementById('bandeau-modele').classList.contains('cache')", 10), True,
            "bandeau du modele : visible (une cle nouvelle fusionnee au demarrage)")
    verifie(cdp.js("document.getElementById('texte-modele').textContent.indexOf('1 clé ajoutée au modèle, à compléter') >= 0"), True,
            "bandeau du modele : « 1 clé ajoutée au modèle, à compléter »")
    verifie(cdp.js("document.getElementById('liste-modele').textContent"), "serveur.udp.essai = 7 Relue", "bandeau du modele : la cle, son defaut et « Relue »")
    verifie(cdp.js("document.getElementById('bandeau-erreur').classList.contains('cache')"), True, "modele lisible : pas de bandeau d'erreur")
    clic(cdp, "maj-modele")
    verifie(attend(cdp, "!document.getElementById('panneau-modele').classList.contains('cache') && (document.getElementById('diff-modele').textContent !== '' || document.getElementById('retours-modele').textContent !== '')", 10),
            True, "bouton « Mettre à jour le modèle » : proposition affichee (diff ou « rien a faire »)")
    clic(cdp, "annule-modele")
    verifie(visible(cdp, "panneau-modele"), False, "annulation : le panneau se referme")
    verifie(cdp.js("document.querySelectorAll('#liste-modele button').length"), 1, "« Relue » : un bouton visible pour la cle a completer")
    cdp.js("document.querySelector('#liste-modele button').click()")
    verifie(attend(cdp, "!document.getElementById('panneau-modele').classList.contains('cache') && document.getElementById('diff-modele').textContent.indexOf('serveur.udp.essai') >= 0", 10),
            True, "« Relue » : le diff du retrait est affiche")
    clic(cdp, "valide-modele")
    verifie(attend(cdp, "document.getElementById('bandeau-modele').classList.contains('cache') && document.getElementById('liste-modele').textContent === ''", 10),
            True, "« Relue » validee : le bandeau ne liste plus la cle")
    for i, ident in enumerate(("f-puce", "f-ip", "cases", "metiers", "voir-diff")):
        clic(cdp, f"pastille-{i}")
        verifie(cdp.js("[0,1,2,3,4].map(function(k){return !document.getElementById('etape-'+k).classList.contains('cache');})"),
                [k == i for k in range(5)], f"pastille {i + 1} : seule son etape est affichee")
        verifie(cdp.js(f"document.getElementById({json.dumps(ident)}) !== null && document.getElementById('etape-{i}').contains(document.getElementById({json.dumps(ident)}))"),
                True, f"pastille {i + 1} : ses champs sont dans l'etape")
    # etape Carte : le nom change le hostname de l'apercu
    clic(cdp, "pastille-0")
    saisit(cdp, "f-lieu", "garage")
    saisit(cdp, "f-nom", "bassin")
    verifie(attend(cdp, "document.getElementById('apercu').textContent.indexOf('BASSIN-GARAGE') >= 0", 10), True,
            "nom saisi : le hostname de l'apercu devient BASSIN-GARAGE")
    verifie(cdp.js("document.getElementById('f-hostname').value"), "BASSIN-GARAGE", "identite : hostname prerempli")
    saisit(cdp, "f-nom", "piscine")
    verifie(attend(cdp, "document.getElementById('apercu').textContent.indexOf('PISCINE-GARAGE') >= 0", 10), True,
            "nom change : l'apercu suit (PISCINE-GARAGE)")
    verifie(cdp.js("document.getElementById('f-client').value + '|' + document.getElementById('f-topic').value"),
            "PISCINE-GARAGE|garage/piscine", "identite : client et topic suivent le nom")
    saisit(cdp, "f-hostname", "MON-HOTE")
    saisit(cdp, "f-nom", "piscine")
    verifie(attend(cdp, "document.getElementById('apercu').textContent.indexOf('MON-HOTE') >= 0", 10), True,
            "hostname modifie a la main : garde, apercu a jour")
    saisit(cdp, "f-hostname", "")                              # vide -> retour au defaut
    # etape Reseau : esclave -> maitres
    clic(cdp, "pastille-1")
    clic(cdp, "role-esclave")
    verifie(attend(cdp, "document.getElementById('f-maitre').options.length > 0", 10), True, "esclave : liste des maitres non vide")
    verifie(cdp.js("document.getElementById('bloc-esclave').classList.contains('cache')"), False, "esclave : maitre et id visibles")
    verifie(cdp.js("document.getElementById('f-id').value > 0"), True, "esclave : id propose")
    saisit(cdp, "f-id", "4")
    verifie(attend(cdp, "document.getElementById('id-indice').textContent.indexOf('libre') >= 0", 5), True, "id 4 : indice « libre »")
    saisit(cdp, "f-id", "2")
    verifie(attend(cdp, "document.getElementById('id-indice').className.indexOf('av') >= 0", 5), True, "id 2 deja pris : avertissement")
    saisit(cdp, "f-id", "4")
    # etape Fonctions : dependances et cases grisees
    clic(cdp, "pastille-2")
    clic(cdp, "bloc-ads1115")
    verifie(cdp.js("[document.getElementById('bloc-i2c').checked, document.getElementById('bloc-i2c').disabled]"), [True, True],
            "ADS1115 : i2c coche d'office et grise")
    verifie(cdp.js("document.getElementById('note-deps').textContent.indexOf('i2c') >= 0"), True, "dependance expliquee")
    verifie(cdp.js("document.getElementById('bloc-i2c').parentNode.textContent.indexOf('requis par') >= 0"), True, "case grisee : raison affichee")
    clic(cdp, "bloc-ads1115")
    verifie(cdp.js("[document.getElementById('bloc-i2c').checked, document.getElementById('bloc-i2c').disabled]"), [False, False],
            "ADS1115 decoche : i2c libere")
    clic(cdp, "bloc-udp")
    clic(cdp, "bloc-modbus")
    saisit(cdp, "f-puce", "ESP32", "change")
    verifie(cdp.js("[document.getElementById('bloc-historique').disabled, document.getElementById('bloc-historique').parentNode.textContent.indexOf('non disponible') >= 0]"),
            [True, True], "ESP32 : historique grise avec sa raison")
    saisit(cdp, "f-puce", "ESP32S3", "change")
    verifie(cdp.js("document.getElementById('bloc-historique').disabled"), False, "ESP32S3 : historique de nouveau permis")
    saisit(cdp, "f-heure", "RTC", "change")
    verifie(cdp.js("[document.getElementById('bloc-ds3231').checked, document.getElementById('bloc-i2c').checked]"), [True, True],
            "heure RTC : DS3231 et i2c coches d'office")
    saisit(cdp, "f-heure", "NTP", "change")
    # etape Bloc metier : zero metier -> Voir le diff grise
    clic(cdp, "pastille-3")
    verifie(cdp.js("document.getElementById('voir-diff').disabled"), True, "zero metier : « Voir le diff » grise")
    verifie(visible(cdp, "avert-metier"), True, "zero metier : avertissement affiche")
    saisit(cdp, "metier-0", "piscine")
    verifie(cdp.js("[document.getElementById('voir-diff').disabled, document.getElementById('avert-metier').classList.contains('cache')]"),
            [False, True], "un metier : « Voir le diff » actif")
    # editeur des entrees/sorties (A7) : 2 relais ajoutes, l'apercu change ; broche en double -> refus ; retrait
    verifie(cdp.js("document.querySelectorAll('#elements details').length"), 7, "elements : un groupe par type d'element")
    verifie(attend(cdp, "(function(){try{return Object.keys(JSON.parse(document.getElementById('apercu').textContent).modules.piscine.environnement.relais).length===0}catch(e){return false}})()", 10),
            True, "elements : aucun relais avant l'ajout")
    clic(cdp, "ajout-relais")
    clic(cdp, "ajout-relais")
    verifie(cdp.js("document.querySelectorAll('#groupe-relais .ligne-el:not(.tete)').length"), 2, "elements : 2 relais dans le tableau")
    verifie(attend(cdp, "document.getElementById('apercu').textContent.indexOf('relai2') >= 0", 10), True,
            "elements : l'apercu montre relai1 et relai2")
    verifie(cdp.js("document.getElementById('el-relais-1-pin').options.length === 39"), True, "elements : la broche est une liste (GPIO de la puce)")
    saisit(cdp, "el-relais-0-pin", "6", "change")
    saisit(cdp, "el-relais-1-pin", "6", "change")
    verifie(attend(cdp, "document.getElementById('apercu-refus').textContent.indexOf('broche 6') >= 0", 10), True,
            "elements : deux relais sur la broche 6 -> refus affiche")
    saisit(cdp, "el-relais-1-pin", "7", "change")
    saisit(cdp, "el-relais-1-nom", "Filtre")
    verifie(attend(cdp, "document.getElementById('apercu-refus').textContent.indexOf('broche') < 0 && document.getElementById('apercu').textContent.indexOf('Filtre') >= 0", 10),
            True, "elements : broches 6 et 7, plus de refus, nom saisi dans l'apercu")
    # ids uniques : retirer le premier relais puis en ajouter un ne doit pas dupliquer id ni nom
    clic(cdp, "retire-relais-0")
    clic(cdp, "ajout-relais")
    verifie(cdp.js("Array.from(document.querySelectorAll('#groupe-relais [id$=-nom]')).map(function(e){return e.value;})"), ["Filtre", "Relais 3"],
            "elements : retrait du 1er puis ajout -> nom « Relais 3 » (pas de doublon)")
    verifie(attend(cdp, "(function(){try{var r=JSON.parse(document.getElementById('apercu').textContent).modules.piscine.environnement.relais;"
                        "return Object.keys(r).length===2 && r.relai1.id!==r.relai2.id}catch(e){return false}})()", 10), True,
            "elements : deux relais d'id differents dans l'apercu")
    verifie(cdp.js("document.getElementById('apercu-refus').textContent.indexOf('nom') < 0"), True, "elements : aucun refus de nom en double")
    clic(cdp, "ajout-boutons")
    clic(cdp, "retire-boutons-0")
    verifie(cdp.js("document.querySelectorAll('#groupe-boutons .ligne-el:not(.tete)').length"), 0, "elements : retrait d'un bouton")
    clic(cdp, "ajout-metier")
    verifie(cdp.js("document.querySelectorAll('[data-metier]').length"), 2, "ajout d'un second bloc metier")
    cdp.js("document.querySelector('[data-retire=\"1\"]').click(); 1")
    verifie(cdp.js("document.querySelectorAll('[data-metier]').length"), 1, "retrait du second bloc metier")
    # etape Verification : diff, bouton grise a la moindre saisie
    clic(cdp, "pastille-4")
    verifie(cdp.js("document.getElementById('creer').disabled"), True, "avant le diff : « Creer l'env » grise")
    clic(cdp, "voir-diff")
    verifie(attend(cdp, "document.getElementById('diff').textContent.indexOf('" + ENV + "') >= 0", 20), True, "diff affiche")
    verifie(cdp.js("document.querySelectorAll('#retours .avert.rouge').length"), 0, "diff sans refus")
    verifie(attend(cdp, "!document.getElementById('creer').disabled", 5), True, "apres le diff sans refus : « Creer l'env » actif")
    saisit(cdp, "f-ip", "192.168.0.77")
    verifie(cdp.js("[document.getElementById('creer').disabled, document.getElementById('panneau-diff').classList.contains('cache')]"),
            [True, True], "saisie apres le diff : « Creer l'env » grise, diff referme")
    saisit(cdp, "f-ip", "0.0.0.0")
    verifie(cdp.js("document.getElementById('creer').disabled"), True, "retour a la valeur d'origine mais diff referme : toujours grise")
    # refus precoce : reseau absent -> refus affiches, bouton reste grise
    clic(cdp, "pastille-1")
    clic(cdp, "role-autonome")
    cdp.js("var s=document.getElementById('f-reseau1'); var o=document.createElement('option'); o.value='RESEAU-INCONNU'; o.textContent='RESEAU-INCONNU'; s.appendChild(o); s.value='RESEAU-INCONNU'; s.dispatchEvent(new Event('change',{bubbles:true})); 1")
    clic(cdp, "pastille-4")
    clic(cdp, "voir-diff")
    verifie(attend(cdp, "document.querySelectorAll('#retours .avert.rouge').length > 0", 15), True, "refus de prepare affiches")
    verifie(cdp.js("document.getElementById('retours').textContent.indexOf('RESEAU-INCONNU') >= 0"), True, "refus : nomme le reseau")
    verifie(cdp.js("document.getElementById('creer').disabled"), True, "refus : « Creer l'env » reste grise")
    # creation reelle dans le depot d'essai (esclave du maitre P4)
    clic(cdp, "pastille-1")
    clic(cdp, "role-esclave")
    clic(cdp, "pastille-4")
    clic(cdp, "voir-diff")
    attend(cdp, "!document.getElementById('creer').disabled", 20)
    # Ruling 11 (1) : un 409 de /creation invalide le diff ; « Creer » ne se reactive pas sans nouveau « Voir le diff »
    cdp.js("window.__fetch0 = window.fetch; window.fetch = function(u, o){ if (String(u) === '/creation') "
           "return Promise.resolve(new Response('saisie changee depuis le diff', {status: 409})); return window.__fetch0(u, o); }; 1")
    clic(cdp, "creer")
    verifie(attend(cdp, "!!document.getElementById('creation-erreur')", 10), True, "409 de /creation : message affiche")
    verifie(cdp.js("[document.getElementById('creer').disabled, document.getElementById('panneau-diff').classList.contains('cache')]"),
            [True, True], "409 de /creation : diff invalide, « Creer l'env » reste grise")
    time.sleep(0.5)
    verifie(cdp.js("document.getElementById('creer').disabled"), True, "409 de /creation : toujours grise apres coup (nouveau diff exige)")
    cdp.js("window.fetch = window.__fetch0; 1")
    clic(cdp, "voir-diff")
    attend(cdp, "!document.getElementById('creer').disabled", 20)
    clic(cdp, "creer")
    verifie(attend(cdp, "!!document.getElementById('creation-ok')", 20), True, "creation : message de reussite")
    verifie(((m.depot / DOSSIER / "_persist.json").is_file(), (m.depot / DOSSIER / "controlePiscine.be").is_file()), (True, True),
            "creation : persist et squelettes ecrits dans le depot d'essai")
    verifie(all(x in (m.depot / DOSSIER / "_persist.json").read_text(encoding="utf-8") for x in ('"relai2"', '"Filtre"')), True,
            "creation : les 2 relais saisis sont dans le persist ecrit")
    verifie(cdp.js("location.hostname"), "localhost", "page chargee sous localhost (le serveur renvoie des liens en 127.0.0.1)")
    verifie(cdp.js("document.getElementById('lien-build').getAttribute('href')"), "http://localhost:7700/?env=" + ENV,
            "lien build : hote de la page, port 7700")
    verifie(cdp.js("document.getElementById('lien-fichiers').getAttribute('href')"), "http://localhost:7800/?env=" + ENV,
            "lien fichiers : hote de la page, port 7800")
    verifie(cdp.js("document.getElementById('resume').textContent.indexOf('" + ENV + "') >= 0"), True, "resume affiche")
    clic(cdp, "copier")
    verifie(attend(cdp, "document.getElementById('copier').textContent === 'Copié'", 5), True, "bouton « Copier » : confirmation")
    verifie(cdp.js("document.getElementById('creer').disabled"), True, "apres creation : « Creer l'env » grise")
    sonde_modification(m)
    html =cdp.js("document.documentElement.outerHTML + document.body.textContent")
    fuites = [i for i, s in enumerate(taw.valeurs_reelles()) if s in html]
    verifie(fuites, [], "aucun mot de passe du parc dans la page")
    verifie(cdp.erreurs(), [], "aucune erreur JS pendant toute la sonde")


def choisit_env(cdp, env):
    cdp.js("var s=document.getElementById('f-env'); s.value=" + json.dumps(env) + "; s.dispatchEvent(new Event('change',{bubbles:true})); 1")


def sonde_modification(m):
    """A10 : mode modification (charger, libelle, diff reactif), puis suppression verifiee. Depot d'essai seulement."""
    cdp = m.cdp
    verifie(cdp.js("(function(){var o=document.getElementById('f-env').options;return o.length>1&&o[0].value===''})()"), True,
            "liste Env : « (nouvel env) » puis les cartes")
    # diff_reactive_apres_creation : on reste sur l'env cree, en mode modification, et un parametre change reactive le diff
    verifie(attend(cdp, "document.getElementById('f-lieu').disabled && document.getElementById('f-env').value === '" + ENV + "'", 10),
            True, "apres creation : page en mode modification sur l'env cree (lieu grise)")
    verifie(cdp.js("document.getElementById('creer').textContent"), "Modifier l'environnement", "apres creation : bouton « Modifier l'environnement »")
    verifie(cdp.js("document.getElementById('voir-diff').disabled"), False, "apres creation : « Voir le diff » actif (env deja cree)")
    saisit(cdp, "f-ip", "192.168.0.78")
    clic(cdp, "pastille-4")
    clic(cdp, "voir-diff")
    verifie(attend(cdp, "document.getElementById('diff').textContent.indexOf('192.168.0.78') >= 0 && !document.getElementById('creer').disabled", 20),
            True, "modification : diff de l'IP affiche, bouton actif")
    saisit(cdp, "f-ip", "192.168.0.79")
    verifie(cdp.js("document.getElementById('creer').disabled"), True, "modification : toute saisie grise de nouveau le bouton")
    saisit(cdp, "f-ip", "192.168.0.78")
    clic(cdp, "voir-diff")
    attend(cdp, "!document.getElementById('creer').disabled", 20)
    clic(cdp, "creer")
    verifie(attend(cdp, "!!document.getElementById('modification-ok')", 20), True, "modification : message de reussite")
    verifie("192.168.0.78" in (m.depot / DOSSIER / "_persist.json").read_text(encoding="utf-8"), True, "modification : IP ecrite dans le persist d'essai")
    verifie(attend(cdp, "document.getElementById('f-ip').value === '192.168.0.78' && document.getElementById('f-lieu').disabled", 10), True,
            "modification : on reste en mode modification, reponses rechargees")
    clic(cdp, "voir-diff")
    verifie(attend(cdp, "document.getElementById('retours').textContent.indexOf('Aucun changement') >= 0", 20), True, "ecart vide : « Aucun changement »")
    verifie(cdp.js("document.getElementById('creer').disabled"), True, "ecart vide : bouton grise")
    # charger_env : une autre carte du parc
    clic(cdp, "pastille-0")
    choisit_env(cdp, "tasmota32s3-cave-serveur-rly")
    clic(cdp, "charger")
    verifie(attend(cdp, "document.getElementById('f-nom').value === 'serveur-rly' && document.getElementById('f-lieu').value === 'cave'", 15), True,
            "charger : lieu et nom relus de la carte")
    verifie(cdp.js("['f-lieu','f-nom','f-puce','f-base'].map(function(i){return document.getElementById(i).disabled})"), [True] * 4,
            "charger : lieu, nom, puce et base non modifiables")
    verifie(cdp.js("document.getElementById('f-puce').value + '|' + document.getElementById('f-ip').value"), "ESP32S3|" + IP_CAVE_S3,
            "charger : puce et IP relues")
    verifie(cdp.js("document.getElementById('metier-0').value !== ''"), True, "charger : bloc metier rempli")
    verifie(cdp.js("document.getElementById('creer').textContent"), "Modifier l'environnement", "charger : bouton « Modifier l'environnement »")
    # libelle_si_existe : retour en creation, lieu + nom d'une carte existante
    choisit_env(cdp, "")
    verifie(cdp.js("['f-lieu','f-nom','f-puce','f-base'].map(function(i){return document.getElementById(i).disabled})"), [False] * 4,
            "(nouvel env) : champs de nouveau modifiables")
    saisit(cdp, "f-lieu", "garage")
    saisit(cdp, "f-nom", "serveur-modbus")
    verifie(cdp.js("document.getElementById('creer').textContent"), "Modifier l'environnement", "env existant saisi : libelle « Modifier »")
    verifie(visible(cdp, "bandeau-existe"), True, "env existant saisi : bandeau « Cet env existe deja »")
    saisit(cdp, "f-nom", "inconnu-zz")
    verifie(cdp.js("[document.getElementById('creer').textContent, document.getElementById('bandeau-existe').classList.contains('cache')]"),
            ["Créer l'env", True], "env inexistant : libelle « Créer l'env », pas de bandeau")
    saisit(cdp, "f-nom", "serveur-modbus")
    clic(cdp, "charger-existe")
    verifie(attend(cdp, "document.getElementById('f-lieu').disabled && document.getElementById('f-env').value === 'tasmota32s3-garage-serveur-modbus'", 15),
            True, "bandeau : « Charger ses reglages » charge l'env")
    # suppression_verifiee : l'env cree par la sonde
    choisit_env(cdp, ENV)
    clic(cdp, "charger")
    verifie(attend(cdp, "document.getElementById('f-nom').value === 'piscine' && document.getElementById('f-nom').disabled", 15), True, "suppression : env d'essai charge")
    clic(cdp, "pastille-4")
    verifie(visible(cdp, "panneau-suppr"), False, "suppression : panneau ferme au depart")
    clic(cdp, "supprimer-env")
    verifie(attend(cdp, "document.querySelectorAll('#suppr-elements li').length > 0", 15), True, "suppression : elements listes")
    verifie(cdp.js("document.getElementById('suppr-elements').textContent.indexOf('" + ENV + "') >= 0"), True, "suppression : la section du cenv est nommee")
    verifie(cdp.js("document.getElementById('suppr-diff').textContent.length > 0"), True, "suppression : diff affiche")
    verifie(cdp.js("[document.getElementById('suppr-verifie').checked, document.getElementById('suppr-confirme').disabled]"), [False, True],
            "suppression : « Supprimer » grise tant que la case n'est pas cochee")
    clic(cdp, "suppr-verifie")
    verifie(cdp.js("document.getElementById('suppr-confirme').disabled"), False, "suppression : case cochee -> « Supprimer » actif")
    clic(cdp, "suppr-verifie")
    verifie(cdp.js("document.getElementById('suppr-confirme').disabled"), True, "suppression : case decochee -> grise de nouveau")
    clic(cdp, "suppr-verifie")
    clic(cdp, "suppr-confirme")
    verifie(attend(cdp, "!!document.getElementById('suppression-ok')", 20), True, "suppression : message de reussite")
    verifie((m.depot / DOSSIER).exists(), False, "suppression : dossier de la carte renomme dans le depot d'essai")
    verifie(cdp.js("[document.getElementById('f-lieu').disabled, document.getElementById('f-env').value, document.getElementById('creer').textContent]"),
            [False, "", "Créer l'env"], "suppression : retour au mode creation")
    verifie(cdp.js("Array.from(document.getElementById('f-env').options).some(function(o){return o.value==='" + ENV + "'})"), False,
            "suppression : la carte a disparu de la liste Env (parc relu)")
    verifie(visible(cdp, "panneau-suppr"), False, "suppression : panneau referme")


def sonde_temoin(m):
    m.cdp.appel("Page.navigate", url=m.url)
    time.sleep(3)
    verifie(len(m.cdp.erreurs()) > 0, True, "TEMOIN : l'identifiant DOM casse est detecte (exceptionThrown)")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de la page Assistant persist.")
    options.add_argument("--sans-temoin", action="store_true")
    options.add_argument("--serveur", nargs=2, metavar=("PORT", "DEPOT"), help=argparse.SUPPRESS)
    options.add_argument("--temoin", action="store_true", help=argparse.SUPPRESS)
    args = options.parse_args()
    if args.serveur:
        return mode_serveur(int(args.serveur[0]), args.serveur[1], args.temoin)
    for temoin in ([False] if args.sans_temoin else [False, True]):
        print(f"\n=== {'TEMOIN (identifiant DOM casse)' if temoin else 'page reelle'} ===", flush=True)
        m = None
        try:
            m = Montage()
            m.demarre(temoin)
            sonde_temoin(m) if temoin else sonde_page(m)
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
