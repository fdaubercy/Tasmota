"""Sonde Chrome de la page « Fichiers Berry par env » (fichiers_berry_page.PAGE) : la page s'execute-t-elle ?

UTILISATION (a la main ; aucun pio n'est lance, Chrome tourne ~30 s)
    python outils_docs/scripts_python/outils_pc/test_fichiers_berry_page_chrome.py [--sans-temoin]
Code de sortie 0 = vert : la vraie page passe toutes les verifications ET le temoin (la meme page avec une
erreur JS volontaire au chargement) est detecte. Client DevTools repris de test_build_page_chrome.py.

Montage : fichiers_berry_web.py dans un processus fils (mode --serveur), devant une COPIE du depot (les
.ini, le .h, les dossiers de carte, data/fs) dans un dossier temporaire ; detection des builds neutralisee ;
OUTILS_TASMOTA_DOSSIER temporaire. Le vrai cenv n'est jamais ecrit.
Scenario : ?env= preselectionne le rideau ; un fichier du socle ouvre la fenetre « liste partagee »,
Annuler ne laisse rien en attente ; un fichier propre passe en attente, diff, enregistrement (cenv de la
copie modifie) ; le formulaire de creation se preremplit.
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
RIDEAU = "tasmota32s3-garage-rideau-garage-modbus"
BASE = "tasmota32s3-base-N16R8"
DISPARU = "data/fs/controleVoletRoulants.be"      # dans le custom_files_exclude propre du rideau
MARQUE_TEMOIN = 'var envs = [], etat = null, attente = {}'
INJECTION_TEMOIN = '\n$("bouton-qui-n-existe-pas").onclick = null;   // TEMOIN : TypeError au chargement\n'


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)
    return ok


def mode_serveur(port, depot, temoin):
    import fichiers_berry_web as fbweb
    if temoin:
        import fichiers_berry_page
        assert fichiers_berry_page.PAGE.count(MARQUE_TEMOIN) == 1, "marque du temoin introuvable dans la page"
        fichiers_berry_page.PAGE = fichiers_berry_page.PAGE.replace(MARQUE_TEMOIN, INJECTION_TEMOIN + MARQUE_TEMOIN)
    fbweb.DEPOT = Path(depot)
    fbweb.builds_en_cours_defaut = lambda: []
    sys.argv = ["fichiers_berry_web.py", "--http", str(port), "--local", "--sans-navigateur"]
    return fbweb.principal()


class Montage:
    def __init__(self):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_fichiers_berry_"))
        self.serveur = self.chrome = None

    def demarre(self, temoin):
        import test_fichiers_berry_creation as tfc
        self.depot = tfc.depot_essai(self.t / "depot")
        shutil.copytree(tfc.RACINE / "data" / "fs", self.depot / "data" / "fs",
                        ignore=lambda d, noms: [n for n in noms if not n.endswith(".be")])
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
        shutil.rmtree(self.t, ignore_errors=True)


def clic(cdp, ident):
    return cdp.js(f"(function(){{var e=document.getElementById({json.dumps(ident)}); if(!e) return 'absent'; e.click(); return 'ok';}})()")


def choisit(cdp, chemin, etat):
    return cdp.js("(function(){var s=document.getElementById('fichier'); s.value=" + json.dumps(chemin) +
                  "; s.dispatchEvent(new Event('change')); var r=document.getElementById('etat-" + etat +
                  "'); if(!r) return 'pas de radio'; r.checked=true; r.dispatchEvent(new Event('change')); return s.value;})()")


def sonde_page(m):
    cdp = m.cdp
    cenv = m.depot / "platformio_tasmota_cenv.ini"
    avant = cenv.read_bytes()
    (m.depot / DISPARU).unlink()                 # ligne propre de custom_files_exclude du rideau -> « disparue »
    marque = m.t / "outils/fichiers_berry/sauvegardes/20261025-120000-000000-suppression/en_cours.json"
    marque.parent.mkdir(parents=True)            # operation arretee en plein vol (processus tue)
    marque.write_text(json.dumps({"nature": "suppression", "debut": "2026-10-25T12:00:00",
                                  "etapes": ["platformio_tasmota_cenv.ini a remettre"]}), encoding="utf-8")
    cdp.appel("Page.navigate", url=m.url + "?env=" + RIDEAU)
    verifie(attend(cdp, "document.getElementById('col-solidifie') && document.getElementById('col-solidifie').textContent.indexOf('controleRideau.be') >= 0", 15),
            True, "chargement : colonne Solidifie remplie (controleRideau.be)")
    verifie(attend(cdp, "!!document.querySelector('#interrompues .avert.rouge') && document.getElementById('interrompues').textContent.indexOf('platformio_tasmota_cenv.ini') >= 0", 10),
            True, "operation interrompue : bandeau rouge au chargement, etapes nommees")
    cdp.js("document.querySelector('#interrompues button').click(); 1")
    verifie(attend(cdp, "!document.querySelector('#interrompues .avert')", 10), True, "« J'ai verifie » : bandeau retire")
    verifie((marque.exists(), marque.parent.is_dir()), (False, True), "acquittee : marque retiree, sauvegarde gardee")
    verifie(cdp.js("document.getElementById('env').value"), RIDEAU, "?env= preselectionne l'env")
    verifie(cdp.js("(function(){var b=document.querySelector('[data-retirer=\"" + DISPARU + "\"]'); if(!b) return 'absent';"
                   " b.click(); return document.querySelector('[data-attente=\"" + DISPARU + "\"]') ? 'en attente' : 'non';})()"),
            "en attente", "disparu : « retirer la ligne » le met en attente")
    cdp.js("document.querySelector('[data-attente=\"" + DISPARU + "\"] button').click(); 1")
    verifie(choisit(cdp, "data/fs/udpFonctions.be", "fs"), "data/fs/udpFonctions.be", "choix d'un fichier du socle")
    clic(cdp, "appliquer")
    verifie(cdp.js("!document.getElementById('fenetre-partage').classList.contains('cache')"), True,
            "socle : fenetre « liste partagee » ouverte")
    verifie(cdp.js("document.getElementById('partage-envs').children.length > 1"), True, "socle : plusieurs envs nommes")
    verifie(cdp.js("/Modifier la liste partag.e \\(\\d+ envs\\)/.test(document.getElementById('partage-modifier').textContent)"),
            True, "socle : bouton « Modifier la liste partagee (N envs) »")
    clic(cdp, "partage-annuler")
    verifie(cdp.js("document.querySelectorAll('[data-attente]').length"), 0, "Annuler : rien en attente")
    choisit(cdp, "data/fs/loRaWanFonctions.be", "fs")
    clic(cdp, "appliquer")
    verifie(cdp.js("document.querySelectorAll('[data-attente]').length"), 1, "fichier propre : une modification en attente")
    clic(cdp, "voir-diff")
    verifie(attend(cdp, "document.getElementById('diff').textContent.indexOf('loRaWanFonctions') >= 0", 10), True,
            "diff affiche")
    verifie(cdp.js("document.getElementById('panneau-diff').classList.contains('cache')"), False,
            "panneau du diff visible (le bouton Enregistrer est cliquable a la main)")
    choisit(cdp, "data/fs/vrFonctions.be", "fs")             # modification APRES le diff : il ne vaut plus
    clic(cdp, "appliquer")
    verifie(cdp.js("[document.getElementById('panneau-diff').classList.contains('cache'), document.getElementById('enregistrer').disabled]"),
            [True, True], "modification apres le diff : diff referme, Enregistrer grise")
    cdp.js("document.querySelector('[data-attente=\"data/fs/vrFonctions.be\"] button').click(); 1")
    clic(cdp, "voir-diff")
    attend(cdp, "!document.getElementById('panneau-diff').classList.contains('cache')", 10)
    clic(cdp, "enregistrer")
    verifie(attend(cdp, "!!document.getElementById('message-ok')", 10), True, "enregistrement : message de reussite")
    verifie(cenv.read_bytes() != avant, True, "enregistrement : cenv de la copie modifie")
    verifie(cdp.js("document.getElementById('message-ok').textContent.indexOf(" + json.dumps(str(m.t / "outils")) + ") >= 0"),
            True, "enregistrement : chemin de la sauvegarde horodatee affiche")
    verifie(cdp.js("document.getElementById('lien-build').getAttribute('href')"), "http://127.0.0.1:7700/?env=" + RIDEAU,
            "lien vers la page build avec l'env")
    cdp.js("var s=document.getElementById('env'); s.value='" + BASE + "'; s.dispatchEvent(new Event('change')); 1")
    attend(cdp, "etat && etat.env === '" + BASE + "'", 10)
    # ajout dans l'option propre d'une base : un data/fs sans aucune ligne, passe en Exclu
    libre = cdp.js("(etat.fichiers.filter(function(f){return f.groupe==='fs' && !f.provenances.length;})[0] || {}).chemin || ''")
    verifie(bool(libre) and choisit(cdp, libre, "exclu") == libre, True, "base : un fichier sans ligne est choisi")
    clic(cdp, "appliquer")
    verifie(cdp.js("[!document.getElementById('fenetre-partage').classList.contains('cache'),"
                   " document.getElementById('partage-envs').children.length > 1]"), [True, True],
            "base : un ajout ouvre la fenetre « liste partagee » avec ses cartes")
    clic(cdp, "partage-annuler")
    clic(cdp, "creer")
    cdp.js("document.getElementById('c-lieu').value='garage'; document.getElementById('c-nom').value='porte-test';"
           "document.getElementById('c-base').value='tasmota32s3-base-N16R8-sans-ecran'; 1")
    clic(cdp, "c-proposer")
    verifie(attend(cdp, "document.getElementById('c-MQTT_TOPIC').value", 10), "garage/porte-test", "creation : identite proposee")
    clic(cdp, "c-prepare")
    attend(cdp, "!document.getElementById('c-creer').disabled", 10)
    cdp.js("var i=document.getElementById('c-WIFI_IP_ADDRESS'); i.value='192.168.0.251'; i.dispatchEvent(new Event('input', {bubbles: true})); 1")
    verifie(cdp.js("document.getElementById('c-creer').disabled"), True, "creation : saisie changee apres le diff -> Creer grise")
    sonde_renommer_supprimer(m)


def sonde_renommer_supprimer(m):
    """Creer un env d'essai, le renommer, puis le supprimer ; refus de supprimer une base."""
    cdp, essai, renomme = m.cdp, "tasmota32s3-garage-porte-test", "tasmota32s3-garage-porte-test2"
    clic(cdp, "c-prepare")
    attend(cdp, "!document.getElementById('c-creer').disabled", 10)
    clic(cdp, "c-creer")
    verifie(attend(cdp, "!!document.getElementById('c-ok') && document.getElementById('env').value === '" + essai + "'", 15),
            True, "creation : env d'essai cree et choisi")
    verifie(clic(cdp, "renommer"), "ok", "bouton « Renommer cet env… »")
    cdp.js("document.getElementById('r-lieu').value='garage'; document.getElementById('r-nom').value='porte-test2'; 1")
    clic(cdp, "r-proposer")
    verifie(attend(cdp, "document.getElementById('r-MQTT_TOPIC') && document.getElementById('r-MQTT_TOPIC').value", 10),
            "garage/porte-test2", "renommage : identite reproposee")
    clic(cdp, "r-prepare")
    verifie(attend(cdp, "!document.getElementById('r-renommer').disabled", 10), True, "renommage : diff sans refus")
    clic(cdp, "r-renommer")
    verifie(attend(cdp, "!!document.getElementById('r-ok') && document.getElementById('env').value === '" + renomme + "'", 15),
            True, "renommage : env renomme et choisi")
    verifie(((m.depot / "data/garage/tasmota32s3-porte-test2/autoexec.be").is_file(),
             (m.depot / "data/garage/tasmota32s3-porte-test").exists()), (True, False), "renommage : dossier deplace")
    verifie(clic(cdp, "supprimer"), "ok", "bouton « Supprimer cet env… »")
    clic(cdp, "s-prepare")
    verifie(attend(cdp, "!document.getElementById('s-supprimer').disabled", 10), True, "suppression : diff sans refus")
    clic(cdp, "s-supprimer")
    verifie(attend(cdp, "!!document.getElementById('s-ok')", 15), True, "suppression : message de reussite")
    verifie(attend(cdp, "![...document.getElementById('env').options].some(function(o){return o.value==='" + renomme + "';})", 10),
            True, "suppression : env retire de la liste")
    verifie((m.depot / "data/garage/tasmota32s3-porte-test2-sauvegarde/autoexec.be").is_file(), True,
            "suppression : dossier renomme en -sauvegarde")
    cdp.js("var s=document.getElementById('env'); s.value='" + BASE + "'; s.dispatchEvent(new Event('change')); 1")
    attend(cdp, "etat && etat.env === '" + BASE + "'", 10)
    clic(cdp, "supprimer")
    clic(cdp, "s-prepare")
    verifie(attend(cdp, "!!document.querySelector('#s-retours .avert.rouge')", 10), True, "base : refus affiche")
    verifie(cdp.js("document.getElementById('s-supprimer').disabled"), True, "base : Supprimer reste grise")
    verifie(cdp.erreurs(), [], "aucune erreur JS pendant toute la sonde")


def sonde_temoin(m):
    m.cdp.appel("Page.navigate", url=m.url)
    time.sleep(3)
    verifie(len(m.cdp.erreurs()) > 0, True, "TEMOIN : l'erreur JS volontaire est detectee")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de la page Fichiers Berry par env.")
    options.add_argument("--sans-temoin", action="store_true")
    options.add_argument("--serveur", nargs=2, metavar=("PORT", "DEPOT"), help=argparse.SUPPRESS)
    options.add_argument("--temoin", action="store_true", help=argparse.SUPPRESS)
    args = options.parse_args()
    if args.serveur:
        return mode_serveur(int(args.serveur[0]), args.serveur[1], args.temoin)
    for temoin in ([False] if args.sans_temoin else [False, True]):
        print(f"\n=== {'TEMOIN (erreur JS volontaire)' if temoin else 'page reelle'} ===", flush=True)
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
