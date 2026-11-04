"""Sonde Chrome de l'onglet « autoexec.bat » de l'Assistant persist (plan autoexec-bat, A6).

UTILISATION (a la main ; aucun pio, aucune carte ; Chrome tourne ~2 x 40 s)
    python outils_docs/scripts_python/outils_pc/test_assistant_persist_autoexec_chrome.py [--sans-temoin] [--capture F.png]
Code de sortie 0 = vert : l'onglet passe toutes les verifications ET chaque temoin est detecte : meme page, case
« redemarrer ensuite » ignoree (la page envoie redemarrer=true) ; meme page sans la garde qui ferme l'envoi quand le
texte change (l'ancien fichier du depot partirait).

Montage repris de test_assistant_persist_page_chrome.py : serveur dans un processus fils, depot d'essai temporaire (celui
de test_assistant_persist_autoexec.depot, autoexec.bat ecrit ici avec un mot de passe INVENTE). Envoi : jamais de
carte, autoexec_envoi.prepare et envoie remplaces dans le processus du serveur par des bouchons ; envoie note ses
arguments dans envoi.json a cote du depot. Reponses lues par la page : fetch enrobe avant le chargement (__corps).
Scenario : onglets ; carte choisie -> texte masque ; points de marge = liste = GET /autoexec ; survol d'un point =
message ; clic sur un avertissement -> sa ligne selectionnee ; « Corriger » ; minuterie inseree par le formulaire
(numero libre, heure, action) ; « Enregistrer… (diff) » ; ecriture refusee sans la case, rien d'ecrit, puis acceptee
(secret remis cote serveur) ; envoi : fichier de la carte montre, « redemarrer ensuite » decochee, bouchon appele
avec redemarrer=False, le jeton et les rouges lus ; « En faire un modele » -> banque ; « Annuler les modifications » ;
aucun secret dans le DOM ni dans une reponse ; aucune erreur JS (hors le 400 attendu de l'ecriture refusee).
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import test_assistant_persist_page_chrome as tpc                            # noqa: E402 - Montage, clic, saisit
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre           # noqa: E402

ECHECS = tpc.ECHECS
verifie = tpc.verifie
ENV = "tasmota32-bureau-interrupteur-energie"
CARTE = "data/bureau/tasmota32-interrupteur-energie"
MDP = "INVENTE_sonde_77"
FICHIER = ("; Essai de la sonde\nSetOption146 ON\nBacklog WifiPower 17; SSId1 ReseauInvente; Password1 " + MDP +
           "\nHostname DISJONCTEUR-ESSAI\nWebSesnor2 0\nPulseTime1 50\nTimers 1\n"
           'Timer1 {"Enable":1,"Mode":0,"Time":"08:00","Window":0,"Days":"1111111","Repeat":1,"Output":1,"Action":1}\n'
           ";MqttPassword " + MDP + "\n")
JETON = "jeton-sonde"
SUR_CARTE = "WebLog 2\nPassword1 ***\n"
SAUVEGARDE = r"C:\essai\autoexec_cartes\copie.bat"
TEMOINS = {                                             # nom -> (texte de la page, remplacement, verification qui doit echouer)
    "redemarrer": ('redemarrer: $("a-redemarrer").checked', "redemarrer: true", "envoi : le bouchon recoit redemarrer=False"),
    "garde-envoi": ("if (modifie()) fermeEnvoi();", "", "envoi : texte modifie apres l'ouverture -> panneau ferme ou « Envoyer » grise"),
}
ENROBE = """window.__corps = []; (function () { var f = window.fetch; window.fetch = function () {
  return f.apply(this, arguments).then(function (r) { r.clone().text().then(function (t) { window.__corps.push(t); }); return r; }); }; })();"""


def mode_serveur(port, depot, temoin):
    import assistant_persist_web as apw
    import autoexec_envoi
    journal = Path(depot).parent / "envoi.json"

    def prepare(racine, env, builds_en_cours):
        return {"adresse": "127.0.0.1:9", "hostname_carte": "ESSAI-SONDE", "sur_carte": SUR_CARTE, "ecart": True, "jeton": JETON}

    def envoie(racine, env, jeton, rouges_lus, redemarrer, builds_en_cours):
        journal.write_text(json.dumps({"env": env, "jeton": jeton, "rouges_lus": rouges_lus, "redemarrer": redemarrer}), encoding="utf-8")
        return {"envoye": True, "sauvegarde": SAUVEGARDE, "avertissement": "avertissement du bouchon"}

    autoexec_envoi.prepare, autoexec_envoi.envoie = prepare, envoie
    if temoin:
        import assistant_persist_page
        avant, apres, _ = TEMOINS[temoin]
        assert assistant_persist_page.PAGE.count(avant) == 1, f"texte du temoin introuvable dans la page : {avant}"
        copie = assistant_persist_page.PAGE.replace(avant, apres)
        apw.page = lambda: copie
    apw.DEPOT = Path(depot)
    apw.builds_en_cours_defaut = lambda: []
    sys.argv = ["assistant_persist_web.py", "--http", str(port), "--local", "--sans-navigateur"]
    return apw.principal()


class Montage(tpc.Montage):
    """Le Montage de la sonde de la page (Chrome, arret), avec le depot de l'autoexec et ce script comme serveur."""

    def demarre(self, temoin):
        import test_assistant_persist_autoexec as tpa
        self.depot = tpa.depot(self.t)
        (self.depot / CARTE / "autoexec.bat").write_bytes(FICHIER.encode("utf-8"))
        self.journal = self.t / "envoi.json"
        environ = dict(os.environ, OUTILS_TASMOTA_DOSSIER=str(self.t / "outils"), PYTHONIOENCODING="utf-8")
        self.port = port_libre()
        self.url = f"http://127.0.0.1:{self.port}/"
        commande = ([sys.executable, "-u", str(Path(__file__).resolve()), "--serveur", str(self.port), str(self.depot)]
                    + (["--temoin", temoin] if temoin else []))
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
        self.cdp.appel("Page.addScriptToEvaluateOnNewDocument", source=ENROBE)

    def get(self, chemin):
        with urllib.request.urlopen(self.url + chemin.lstrip("/"), timeout=10) as r:
            return r.read().decode("utf-8")


def js(cdp, code):
    return cdp.js("(function(){" + code + "})()")


def sonde(m):
    cdp, f = m.cdp, m.depot / CARTE / "autoexec.bat"
    cdp.appel("Page.navigate", url=m.url)
    verifie(attend(cdp, "document.getElementById('f-puce') && document.getElementById('f-puce').options.length === 3", 15), True,
            "chargement : la page de l'Assistant est la")
    verifie(js(cdp, "return [document.getElementById('onglet-persist').getAttribute('aria-selected'), document.getElementById('vue-persist').hidden, "
                    "document.getElementById('vue-autoexec').hidden]"), ["true", False, True], "onglets : « Persist » affiche au depart")
    verifie(js(cdp, "return [document.getElementById('onglet-persist').textContent, document.getElementById('onglet-autoexec').textContent]"),
            ["Persist (créer, modifier, supprimer)", "autoexec.bat"], "onglets : libelles de la spec")
    tpc.clic(cdp, "onglet-autoexec")
    verifie(js(cdp, "return [document.getElementById('vue-persist').hidden, document.getElementById('vue-autoexec').hidden]"), [True, False],
            "onglet autoexec.bat : affiche, l'autre cache")
    verifie(attend(cdp, f"Array.from(document.getElementById('a-env').options).some(function(o){{return o.value==={json.dumps(ENV)}}})", 10), True,
            "carte : l'env du differentiel dans la liste")
    tpc.saisit(cdp, "a-env", ENV, "change")
    verifie(attend(cdp, "document.getElementById('a-texte').value.indexOf('Hostname') >= 0", 10), True, "carte choisie : texte charge")
    verifie(js(cdp, "var v = document.getElementById('a-texte').value; return [v.indexOf('***') >= 0, v.split('***').length - 1]"), [True, 2],
            "texte : les 2 secrets en ***")
    lu = json.loads(m.get("/autoexec?env=" + ENV))
    avs = lu["avertissements"]
    attendu_points = sorted({a["ligne"] for a in avs})
    rouges_lignes = sorted({a["ligne"] for a in avs if a["niveau"] == "rouge"})
    verifie(attend(cdp, f"document.querySelectorAll('#a-avertissements [data-ligne]').length === {len(avs)}", 10), True,
            f"liste : {len(avs)} avertissements (ceux de GET /autoexec)")
    verifie(js(cdp, "return Array.from(document.querySelectorAll('#a-avertissements [data-ligne]')).map(function(e){return +e.getAttribute('data-ligne')})"),
            [a["ligne"] for a in avs], "liste : lignes dans l'ordre du serveur")
    verifie(js(cdp, "return Array.from(document.querySelectorAll('#a-marge .p.rouge, #a-marge .p.orange')).map(function(e){return +e.parentNode.getAttribute('data-ligne')})"),
            attendu_points, "marge : un point par ligne avertie, et seulement elles")
    verifie(js(cdp, "return Array.from(document.querySelectorAll('#a-marge .p.rouge')).map(function(e){return +e.parentNode.getAttribute('data-ligne')})"),
            rouges_lignes, "marge : point rouge sur les lignes a avertissement rouge")
    verifie(js(cdp, "return document.getElementById('a-titre-analyse').textContent"), f"Analyse : {len(avs)} avertissements", "liste : titre avec le compte")
    verifie(js(cdp, "return document.getElementById('a-info').textContent.indexOf('" + CARTE + "/autoexec.bat') >= 0 && "
                    "document.getElementById('a-info').textContent.indexOf('9 lignes') >= 0"), True, "en-tete : chemin et nombre de lignes")
    premier = avs[0]
    verifie(js(cdp, f"var p = document.querySelector('#a-marge [data-ligne=\"{premier['ligne']}\"] .p'); return p ? p.getAttribute('title').indexOf({json.dumps(premier['message'])}) >= 0 : 'absent'"),
            True, "survol d'un point : son title porte le message")
    # clic sur l'avertissement de Hostname -> la ligne 4 selectionnee
    ligne_h = next(a["ligne"] for a in avs if "Hostname" in a["message"])
    js(cdp, f"document.querySelector('#a-avertissements [data-ligne=\"{ligne_h}\"]').click()")
    verifie(js(cdp, "var t = document.getElementById('a-texte'); return [document.activeElement === t, t.value.slice(t.selectionStart, t.selectionEnd)]"),
            [True, "Hostname DISJONCTEUR-ESSAI"], "clic sur un avertissement : sa ligne est selectionnee dans le texte")
    verifie(js(cdp, "return document.getElementById('a-inserer').textContent"), f"Insérer à la ligne {ligne_h + 1}", "insertion : sous la ligne du curseur")
    verifie(js(cdp, "return !document.getElementById('a-proposition').hidden && document.getElementById('a-proposition').textContent.indexOf('Hostname') >= 0"),
            True, "ligne hors banque : « En faire un modele » propose")
    # Corriger WebSesnor2
    verifie(js(cdp, "var b = document.querySelector('#a-avertissements [data-corrige]'); if (!b) return 'absent'; b.click(); return 'ok'"), "ok",
            "« Corriger » present sur la commande inconnue")
    verifie(attend(cdp, "document.getElementById('a-texte').value.indexOf('\\nWebSensor2 0\\n') >= 0", 5), True, "« Corriger » : WebSesnor2 -> WebSensor2")
    verifie(attend(cdp, "!document.getElementById('a-avertissements').textContent.match(/WebSesnor2/)", 5), True,
            "analyse relancee a la frappe : plus d'avertissement sur WebSesnor2")
    verifie(js(cdp, "return document.getElementById('a-envoyer').disabled"), True, "envoi : grise tant que la page a des modifications non ecrites")
    # minuterie par le formulaire
    tpc.saisit(cdp, "a-recherche", "minuterie")
    verifie(attend(cdp, "!!document.querySelector('#a-resultats [data-nom=\"Timer\"]')", 5), True, "recherche « minuterie » : Timer propose")
    js(cdp, "document.querySelector('#a-resultats [data-nom=\"Timer\"]').click()")
    verifie(attend(cdp, "!!document.getElementById('a-c-heure')", 5), True, "Timer choisi : formulaire des champs")
    verifie(js(cdp, "return document.getElementById('a-c-n').value"), "2", "Timer : numero libre propose (Timer1 deja pris)")
    tpc.saisit(cdp, "a-c-heure", "22:30")
    tpc.saisit(cdp, "a-c-action", "0", "change")
    js(cdp, "var b = document.querySelector('#a-c-jours [data-jour=\"0\"]'); b.click()")       # dimanche decoche
    ligne_t = 'Timer2 {"Enable":1,"Mode":0,"Time":"22:30","Window":0,"Days":"0111111","Repeat":1,"Output":1,"Action":0}'
    verifie(js(cdp, "return document.getElementById('a-apercu').textContent"), ligne_t, "apercu : la ligne produite")
    tpc.saisit(cdp, "a-c-heure", "25:00")
    verifie(js(cdp, "return [document.getElementById('a-inserer').disabled, document.getElementById('a-ajout-erreur').textContent !== '']"), [True, True],
            "heure invalide : insertion grisee, motif affiche")
    tpc.saisit(cdp, "a-c-heure", "22:30")
    tpc.clic(cdp, "a-inserer")
    verifie(js(cdp, f"return document.getElementById('a-texte').value.split('\\n')[{ligne_h}]"), ligne_t, f"insertion : ligne {ligne_h + 1}")
    verifie(attend(cdp, "document.getElementById('a-info').textContent.indexOf('10 lignes') >= 0", 5), True, "en-tete : 10 lignes")
    # diff, ecriture refusee sans la case, puis acceptee
    avant = f.read_bytes()
    tpc.clic(cdp, "a-enregistrer")
    verifie(attend(cdp, "document.getElementById('a-diff').textContent.indexOf('+Timer2') >= 0", 10), True, "« Enregistrer… (diff) » : diff affiche")
    verifie(js(cdp, "return document.getElementById('a-diff').textContent.indexOf('-WebSesnor2 0') >= 0"), True, "diff : la correction y est")
    n = js(cdp, "var t = document.getElementById('a-rouges-texte').textContent.match(/les (\\d+) /); return t ? +t[1] : 0")
    verifie(js(cdp, "return [!document.getElementById('a-ligne-rouges').hidden, document.getElementById('a-rouges-lus').checked]"), [True, False],
            f"case « J'ai lu les {n} avertissements rouges » presente, decochee")
    if m.capture:
        m.cdp.capture(m.capture)
    tpc.clic(cdp, "a-ecrire")
    verifie(attend(cdp, "!!document.getElementById('a-ecrit-erreur')", 10), True, "ecriture sans la case : refusee, motif affiche")
    verifie(js(cdp, "return document.getElementById('a-ecrit-erreur').textContent.indexOf('cocher') >= 0"), True, "refus : le motif dit de cocher la case")
    verifie(f.read_bytes() == avant, True, "refus : fichier du depot d'essai inchange")
    tpc.clic(cdp, "a-rouges-lus")
    tpc.clic(cdp, "a-ecrire")
    verifie(attend(cdp, "!!document.getElementById('a-ecrit-ok')", 10), True, "ecriture avec la case : acceptee")
    ecrit = f.read_bytes().decode("utf-8")
    verifie((ligne_t in ecrit, MDP in ecrit, ecrit.count(MDP), "***" in ecrit), (True, True, 2, False), "fichier ecrit : minuterie, secrets remis cote serveur")
    verifie(attend(cdp, "!document.getElementById('a-envoyer').disabled", 10), True, "apres ecriture : « Envoyer a la carte (OTA)… » actif")
    # envoi (bouchons)
    rouges = sum(a["niveau"] == "rouge" for a in json.loads(m.get("/autoexec?env=" + ENV))["avertissements"])
    tpc.clic(cdp, "a-envoyer")
    verifie(attend(cdp, "document.getElementById('a-envoi-adresse').textContent.indexOf('ESSAI-SONDE') >= 0", 10), True, "envoi : carte et adresse affichees")
    verifie(js(cdp, "return document.getElementById('a-sur-carte').textContent"), SUR_CARTE, "envoi : fichier de la carte montre (ecart)")
    verifie(js(cdp, "return [document.getElementById('a-redemarrer').checked, document.getElementById('a-envoi-go').disabled]"), [False, True],
            "envoi : « redemarrer ensuite » decochee, « Envoyer » grise avant d'accepter l'ecart")
    tpc.clic(cdp, "a-ecart-vu")
    tpc.clic(cdp, "a-envoi-rouges-lus")
    tpc.clic(cdp, "a-envoi-go")
    verifie(attend(cdp, "!!document.getElementById('a-envoi-ok')", 10), True, "envoi : reussite affichee")
    verifie(js(cdp, "return document.getElementById('a-envoi-ok').textContent.indexOf('copie.bat') >= 0 && "
                    "document.getElementById('a-envoi-retours').textContent.indexOf('avertissement du bouchon') >= 0"), True,
            "envoi : copie de sauvegarde et avertissement affiches")
    recu = json.loads(m.journal.read_text(encoding="utf-8")) if m.journal.is_file() else {}
    verifie(recu.get("redemarrer"), False, "envoi : le bouchon recoit redemarrer=False")
    verifie((recu.get("jeton"), recu.get("rouges_lus"), recu.get("env")), (JETON, rouges, ENV), "envoi : jeton, rouges lus et env transmis")
    # panneau d'envoi ouvert puis texte modifie : l'ancien fichier du depot ne doit plus pouvoir partir
    tpc.clic(cdp, "a-envoyer")
    attend(cdp, "document.getElementById('a-envoi-adresse').textContent.indexOf('ESSAI-SONDE') >= 0", 10)
    tpc.clic(cdp, "a-ecart-vu")
    verifie(js(cdp, "return document.getElementById('a-envoi-go').disabled"), False, "envoi rouvert : « Envoyer » actif")
    js(cdp, "var t = document.getElementById('a-texte'); t.value += 'WebLog 1'; t.dispatchEvent(new Event('input', {bubbles: true}))")
    verifie(js(cdp, "return document.getElementById('a-panneau-envoi').hidden || document.getElementById('a-envoi-go').disabled"), True,
            TEMOINS["garde-envoi"][2])
    tpc.clic(cdp, "a-annuler")
    # « En faire un modele » depuis la ligne Hostname
    js(cdp, f"document.querySelector('#a-avertissements [data-ligne=\"{ligne_h}\"]').click()")
    tpc.clic(cdp, "a-en-modele")
    verifie(attend(cdp, "!document.getElementById('a-editeur').hidden", 5), True, "« En faire un modele » : editeur ouvert")
    verifie(js(cdp, "return [document.getElementById('m-nom').value, document.getElementById('m-modele').value]"), ["Hostname", "Hostname {valeur}"],
            "editeur : prerempli depuis la ligne")
    tpc.saisit(cdp, "m-nom", "MonHote")
    verifie(attend(cdp, "document.getElementById('m-apercu').textContent === 'Hostname DISJONCTEUR-ESSAI'", 5), True, "editeur : apercu de la ligne")
    tpc.clic(cdp, "m-enregistre")
    verifie(attend(cdp, "document.getElementById('a-perso').textContent.indexOf('Hostname DISJONCTEUR-ESSAI') >= 0", 10), True,
            "modele ajoute : visible dans « Tes commandes »")
    banque = json.loads((m.depot / "outils_docs/schemas/banque_autoexec.json").read_text(encoding="utf-8"))["entrees"]
    verifie([e["origine"] for e in banque if e["nom"] == "MonHote"], ["perso"], "modele ajoute : ecrit dans la banque du depot d'essai")
    # annuler les modifications
    tpc.saisit(cdp, "a-texte", "WebLog 1\n")
    verifie(js(cdp, "return document.getElementById('a-annuler').disabled"), False, "texte modifie : « Annuler » actif")
    tpc.clic(cdp, "a-annuler")
    verifie(js(cdp, "return document.getElementById('a-texte').value.indexOf('Timer2') >= 0 && document.getElementById('a-annuler').disabled"), True,
            "« Annuler les modifications » : texte du depot remis")
    time.sleep(1)
    verifie(js(cdp, f"return document.documentElement.outerHTML.indexOf({json.dumps(MDP)}) < 0 && document.getElementById('a-texte').value.indexOf({json.dumps(MDP)}) < 0"),
            True, "secret : absent du DOM et du texte")
    verifie(js(cdp, f"return [window.__corps.length > 5, window.__corps.some(function(t){{return t.indexOf({json.dumps(MDP)}) >= 0}})]"), [True, False],
            "secret : absent de toutes les reponses lues par la page")
    attendues = [e for e in cdp.erreurs() if e.startswith("journal Chrome") and "/autoexec/ecrit" in e and "400" in e]
    verifie([e for e in cdp.erreurs() if e not in attendues], [], "aucune erreur JS (hors le 400 de l'ecriture refusee)")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de l'onglet autoexec.bat de l'Assistant persist.")
    options.add_argument("--sans-temoin", action="store_true")
    options.add_argument("--capture", help="capture PNG de l'onglet rempli (avant l'ecriture)")
    options.add_argument("--serveur", nargs=2, metavar=("PORT", "DEPOT"), help=argparse.SUPPRESS)
    options.add_argument("--temoin", choices=sorted(TEMOINS), help=argparse.SUPPRESS)
    args = options.parse_args()
    if args.serveur:
        return mode_serveur(int(args.serveur[0]), args.serveur[1], args.temoin)
    for temoin in [None] + ([] if args.sans_temoin else sorted(TEMOINS)):
        print(f"\n=== {'TEMOIN ' + temoin if temoin else 'page reelle'} ===", flush=True)
        m, avant = None, len(ECHECS)
        try:
            m = Montage()
            m.capture = None if temoin else args.capture
            m.demarre(temoin)
            sonde(m)
        except FileNotFoundError as erreur:
            print(f"BLOQUE : {erreur}")
            return 3
        except Exception as erreur:
            verifie(repr(erreur), "pas d'exception de la sonde", "sonde : deroulement")
        finally:
            if m:
                m.ferme()
        if temoin:
            vus = ECHECS[avant:]
            del ECHECS[avant:]
            verifie(TEMOINS[temoin][2] in vus, True, f"TEMOIN {temoin} : detecte ({TEMOINS[temoin][2]})")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
