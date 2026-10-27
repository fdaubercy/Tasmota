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
    cdp.appel("Page.navigate", url=m.url)
    verifie(attend(cdp, "document.getElementById('f-puce') && document.getElementById('f-puce').options.length === 3", 15), True,
            "chargement : les 3 puces dans la liste")
    verifie(attend(cdp, "document.getElementById('apercu').textContent.indexOf('\"serveur\"') >= 0", 15), True,
            "chargement : apercu du persist rempli")
    verifie(attend(cdp, "!document.getElementById('bandeau-modele').classList.contains('cache')", 10), True,
            "bandeau du modele : visible (une cle nouvelle fusionnee au demarrage)")
    verifie(cdp.js("document.getElementById('texte-modele').textContent.indexOf('1 clé ajoutée au modèle, à compléter') >= 0"), True,
            "bandeau du modele : « 1 clé ajoutée au modèle, à compléter »")
    verifie(cdp.js("document.getElementById('liste-modele').textContent"), "serveur.udp.essai", "bandeau du modele : la cle est nommee")
    verifie(cdp.js("document.getElementById('bandeau-erreur').classList.contains('cache')"), True, "modele lisible : pas de bandeau d'erreur")
    clic(cdp, "maj-modele")
    verifie(attend(cdp, "!document.getElementById('panneau-modele').classList.contains('cache') && (document.getElementById('diff-modele').textContent !== '' || document.getElementById('retours-modele').textContent !== '')", 10),
            True, "bouton « Mettre à jour le modèle » : proposition affichee (diff ou « rien a faire »)")
    clic(cdp, "annule-modele")
    verifie(visible(cdp, "panneau-modele"), False, "annulation : le panneau se referme")
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
    verifie(cdp.js("document.getElementById('lien-build').getAttribute('href')"), "http://127.0.0.1:7700/?env=" + ENV, "lien vers la page build")
    verifie(cdp.js("new URL(document.getElementById('lien-build').href).hostname === location.hostname && "
                   "new URL(document.getElementById('lien-fichiers').href).hostname === location.hostname"), True,
            "liens : l'hote de la page (pas une adresse en dur)")
    verifie(cdp.js("document.getElementById('lien-fichiers').getAttribute('href')"), "http://127.0.0.1:7800/?env=" + ENV,
            "lien vers Fichiers Berry")
    verifie(cdp.js("document.getElementById('resume').textContent.indexOf('" + ENV + "') >= 0"), True, "resume affiche")
    clic(cdp, "copier")
    verifie(attend(cdp, "document.getElementById('copier').textContent === 'Copié'", 5), True, "bouton « Copier » : confirmation")
    verifie(cdp.js("document.getElementById('creer').disabled"), True, "apres creation : « Creer l'env » grise")
    html = cdp.js("document.documentElement.outerHTML + document.body.textContent")
    fuites = [i for i, s in enumerate(taw.valeurs_reelles()) if s in html]
    verifie(fuites, [], "aucun mot de passe du parc dans la page")
    verifie(cdp.erreurs(), [], "aucune erreur JS pendant toute la sonde")


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
