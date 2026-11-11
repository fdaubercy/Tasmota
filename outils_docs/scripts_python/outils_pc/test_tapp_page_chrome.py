"""Sonde Chrome de la Fabrique d'extensions (tapp_page.PAGE) : le parcours complet sur la page reelle, de la premiere ouverture a l'envoi.

UTILISATION (a la main ; aucun pio, aucune carte ; Chrome tourne ~1 min par passage)
    python outils_docs/scripts_python/outils_pc/test_tapp_page_chrome.py [--sans-temoin]
Code de sortie 0 = vert : la page passe toutes les verifications ET chaque temoin (meme page, une ligne changee) est detecte par SON test.

Montage repris de test_assistant_persist_autoexec_chrome.py : serveur reel dans un processus fils, depot temporaire, cartes SIMULEES
dans ce processus (HTTP : build_ota_carte_simulee.Carte ; MQTT : carte de test_build_ota_mqtt, client en memoire), garde de
test_autoexec_envoi sur les connexions : rien hors de 127.0.0.1. ae.pousse note chaque envoi dans envoi.json a cote du depot.
Reponse perimee tenue COTE PAGE (fetch enrobe : window.__retenir retient la prochaine reponse de /envoi/prepare jusqu'a __lache()), sans
dependre du temps de reponse du serveur. Les 4xx du journal Chrome sont les refus voulus du scenario.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import test_assistant_persist_page_chrome as tpc                            # noqa: E402 - Montage, clic, saisit
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre           # noqa: E402

ECHECS = tpc.ECHECS
verifie = tpc.verifie
clic, saisit = tpc.clic, tpc.saisit
GENERATION = "perimee : la reponse depassee de la voie HTTP est ignoree"
TEMOINS = {                  # nom -> (texte de la page, remplacement, verification qui doit echouer)
    "generation": ("if (g !== S.nPrep) return;", "", GENERATION),
    "innerHTML": ("e.textContent = texte", "e.innerHTML = texte", "hostile : le message reste du texte, aucune balise creee"),
    "geste-saute": ('$("e-go").disabled = !(S.prep && $("e-vu").checked);', '$("e-go").disabled = !S.prep;', "geste : « Envoyer » grise tant que la case n'est pas cochee"),
    "redemarrage-force": ("redemarrer: redemarre", "redemarrer: true", "envoi : sans redemarrage par defaut"),
    "prep-apres-manifeste": ("annulePrep(); chargeListe(); verifie();", "chargeListe(); verifie();", "manifeste enregistre : la preparation tombe"),
    "lecture-sans-geste": ('if (voie() === "http") prepare();', 'prepare(); if (false) {}', "fabriquer en MQTT : pas de lecture de la carte sans geste"),
    "envoi-echoue": ('if (S.prep === p) annulePrep(); return; }', 'return; }', "envoi refuse : la preparation tombe"),
    "voie-a-l-ecran": ("transport: p.transport", "transport: voie()", "perimee : l'envoi part par la voie preparee"),
}
ENROBE = """window.__corps = []; window.__retenir = false; window.__lache = null; window.__prepares = 0;
(function () { var f = window.fetch; window.fetch = function (u) {
  if (String(u).indexOf('/envoi/prepare') >= 0) window.__prepares++;
  var p = f.apply(this, arguments).then(function (r) { r.clone().text().then(function (t) { window.__corps.push(t); }); return r; });
  if (window.__retenir && String(u).indexOf('/envoi/prepare') >= 0) { window.__retenir = false;
    return new Promise(function (ok) { window.__lache = function () { p.then(ok); }; }); }
  return p; }; })();"""


def mode_serveur(port, depot, temoin):
    import test_autoexec_envoi as tae                  # garde : connexions sur 127.0.0.1 seulement
    import autoexec_envoi as ae
    import tapp_page
    import tapp_web as tw
    from build_ota_carte_simulee import Carte
    from build_ota_fs import _identite
    import test_assistant_persist_autoexec as taa
    hote, topic = _identite((Path(depot) / taa.CARTE / "_persist.json").read_text(encoding="utf-8"))
    carte = Carte(coupure=0.2)
    carte.hostname = hote
    mqtt = tae.CarteMqtt(hote, topic, None)
    ae._adresse = lambda *_: carte.ip
    ae.joint_par_maitre = lambda *a, **k: None
    ae.coupe_sleep = lambda m, **_: (None, lambda: "")
    ae.CLIENT = lambda: tae.ClientFiltre(mqtt)
    ae.REGLAGES_ENVOI.update({"delai_retour": 5.0, "attente_min": 0.0, "sondage": 0.05, "delai_http": 3.0})
    ae.REGLAGES_MQTT.update({"delai": 1.0, "attente_morceau": 0.2, "delai_retour": 1.0})
    journal = Path(depot).parent / "envoi.json"
    vrai = ae.pousse

    def pousse(env, adresse, transport, dossier, fichier, redemarrer):
        vrai(env, adresse, transport, dossier, fichier, redemarrer)
        vus = json.loads(journal.read_text(encoding="utf-8")) if journal.is_file() else []
        recu = sorted(carte.flash) if transport == "http" else sorted(mqtt.fs)
        journal.write_text(json.dumps(vus + [{"transport": transport, "fichier": fichier, "redemarrer": redemarrer, "sur_carte": recu}]), encoding="utf-8")
    ae.pousse = pousse
    if temoin:
        avant, apres, _ = TEMOINS[temoin]
        assert tapp_page.PAGE.count(avant) == 1, f"texte du temoin introuvable dans la page : {avant}"
        tapp_page.PAGE = tapp_page.PAGE.replace(avant, apres)
    tw.DEPOT = Path(depot)
    tw.builds_en_cours_defaut = lambda: []
    sys.argv = ["tapp_web.py", "--http", str(port), "--local", "--sans-navigateur"]
    return tw.principal()


class Montage(tpc.Montage):
    """Le Montage de la sonde de la page (Chrome, arret), avec le depot de l'autoexec et ce script comme serveur."""

    def demarre(self, temoin):
        import test_assistant_persist_autoexec as taa
        self.depot = taa.depot(self.t)
        shutil.rmtree(Path(self.depot) / "data" / "extensions", ignore_errors=True)   # les exemples du depot (A8) : la sonde part d'une page vide
        self.journal = self.t / "envoi.json"
        environ = dict(os.environ, OUTILS_TASMOTA_DOSSIER=str(self.t / "outils"), PYTHONIOENCODING="utf-8")
        self.port = port_libre()
        self.url = f"http://127.0.0.1:{self.port}/"
        commande = ([sys.executable, "-u", str(Path(__file__).resolve()), "--serveur", str(self.port), str(self.depot)]
                    + (["--temoin", temoin] if temoin else []))
        self.serveur = subprocess.Popen(commande, env=environ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self._attend_http(self.url + "extensions", 30)
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

    def envois(self):
        return json.loads(self.journal.read_text(encoding="utf-8")) if self.journal.is_file() else []


def texte(cdp, ident):
    return cdp.js(f"document.getElementById({json.dumps(ident)}).textContent")


def cache(cdp, ident):
    return cdp.js(f"document.getElementById({json.dumps(ident)}).hidden")


def carte_choisie(cdp, env):
    return saisit(cdp, "e-carte", env, "change")


def sonde(m):
    import test_assistant_persist_autoexec as taa
    import test_assistant_persist_web as taw
    cdp = m.cdp
    env = taa.ENV
    cdp.appel("Page.navigate", url=m.url)
    # 1. premiere ouverture : un etat vide qui guide
    verifie(attend(cdp, "!document.getElementById('vide').hidden", 15), True, "premiere ouverture : l'etat vide s'affiche")
    verifie(attend(cdp, "document.querySelectorAll('#c-gabarits input').length === 2", 10), True, "premiere ouverture : les 2 modeles proposes")
    verifie((cache(cdp, "fiche"), "EXTENSIONS_TAPP.md" in cdp.js("document.body.textContent")), (True, True), "premiere ouverture : pas de fiche, le document nomme")
    verifie(attend(cdp, f"document.getElementById('e-carte').querySelector('option[value=\"{env}\"]') !== null", 10), True, "cartes : la liste est remplie")
    # A5 (modele H) : cartes groupees par lieu, option de tete gardee, valeur gardee apres rechargement de la liste
    verifie(cdp.js("[...document.querySelectorAll('#e-carte optgroup')].map(g => g.label)[0]"), "2e étage", "cartes par lieu : premier groupe = 2e étage")
    verifie(cdp.js(f"document.querySelector('#e-carte option[value=\"{env}\"]').parentNode.label"), "Bureau", "cartes par lieu : la carte bureau sous Bureau")
    verifie(cdp.js("document.getElementById('e-carte').firstChild.value"), "", "cartes par lieu : option de tete « (choisir une carte) » gardee")
    cdp.js(f"document.getElementById('e-carte').value = '{env}'; chargeCartes(); 1")
    verifie(attend(cdp, f"document.getElementById('e-carte').value === '{env}'", 10), True, "cartes par lieu : valeur gardee apres rechargement de la liste")
    # carte choisie qui a disparu du cenv (relecture du 2026-11-11) : retour sur « (choisir une carte) », jamais une liste vide
    cdp.js("var s = document.getElementById('e-carte'), o = document.createElement('option'); o.value = 'disparue'; s.appendChild(o);"
           " s.value = 'disparue'; chargeCartes(); 1")
    verifie((attend(cdp, "!document.querySelector('#e-carte option[value=\"disparue\"]')", 10),
             cdp.js("document.getElementById('e-carte').selectedIndex")), (True, 0), "cartes par lieu : carte disparue -> option de tete")
    cdp.js("document.getElementById('e-carte').value = ''; 1")
    # 2. creation : nom refuse, puis accepte
    saisit(cdp, "c-nom", "../mauvais")
    clic(cdp, "c-go")
    verifie(attend(cdp, "document.getElementById('c-retour').textContent.indexOf('lettres') >= 0", 10), True, "creer : nom hostile refuse, le message dit quoi faire")
    verifie(cache(cdp, "fiche"), True, "creer : nom hostile, pas de fiche")
    saisit(cdp, "c-nom", "ext_a")
    clic(cdp, "c-go")
    verifie(attend(cdp, "!document.getElementById('fiche').hidden && document.querySelectorAll('#v-points .bon').length === 4", 20), True, "creer : fiche ouverte, 4 points bons au chargement")
    verifie((texte(cdp, "f-chemin"), cdp.js("document.getElementById('m-name').value"), cache(cdp, "vide")), ("data/extensions/ext_a", "Reception FS MQTT", True), "fiche : chemin du dossier, manifeste du modele, plus d'etat vide")
    verifie("autoexec.be" in texte(cdp, "f-fichiers"), True, "fiche : fichiers listes")
    verifie(texte(cdp, "t-etat"), "Pas encore fabriqué.", "fiche : etat du .tapp")
    verifie(cdp.js("document.querySelector('#liste button').textContent"), "ext_a", "liste : l'extension")
    # 3. refus du manifeste : texte hostile affiche tel quel
    charge = '<img src=x onerror="window.__xss=1">'
    saisit(cdp, "m-version", charge)
    clic(cdp, "m-go")
    attend(cdp, "document.getElementById('m-retour').firstChild !== null", 10)
    time.sleep(0.3)
    verifie(("version" in texte(cdp, "m-retour"), "<img" in texte(cdp, "m-retour"), cdp.js("document.querySelectorAll('#m-retour img').length"), cdp.js("window.__xss === undefined")),
            (True, True, 0, True), "hostile : le message reste du texte, aucune balise creee")
    saisit(cdp, "m-version", "0x1B0B0701")
    saisit(cdp, "m-description", charge)
    clic(cdp, "m-go")
    verifie(attend(cdp, "document.getElementById('m-retour').textContent.indexOf('enregistré') >= 0", 10), True, "manifeste : enregistre")
    verifie((cdp.js("document.getElementById('m-description').value"), cdp.js("document.querySelectorAll('img').length")), (charge, 0), "hostile : la description relue, aucune balise")
    attend(cdp, "!document.getElementById('v-go').disabled", 15)
    # 4. envoi avant fabrication : refus qui dit quoi faire
    carte_choisie(cdp, env)
    verifie(attend(cdp, "document.getElementById('e-retour').textContent.indexOf('Fabriquer') >= 0", 15), True, "envoi avant fabrication : « Fabriquer d'abord »")
    verifie(cache(cdp, "e-panneau"), True, "envoi avant fabrication : pas de panneau d'envoi")
    # 5. fabriquer : la preparation repart seule
    clic(cdp, "t-go")
    verifie(attend(cdp, "document.getElementById('t-retour').textContent.indexOf('data/extensions/ext_a.tapp') >= 0", 20), True, "fabriquer : le .tapp nomme")
    verifie(attend(cdp, "!document.getElementById('e-panneau').hidden", 15), True, "fabriquer : la preparation repart, panneau ouvert")
    etat = texte(cdp, "e-etat")
    verifie(("identité vérifiée" in etat, "/.extensions/ext_a.tapp" in etat, "Aucun fichier de ce nom" in etat), (True, True, True), "preparation : identite, destination, presence sur la carte")
    # 6. geste explicite
    verifie((cdp.js("document.getElementById('e-go').disabled"), cdp.js("document.getElementById('e-vu').checked"), cdp.js("document.getElementById('e-redemarrer').checked")),
            (True, False, False), "geste : « Envoyer » grise tant que la case n'est pas cochee")
    clic(cdp, "e-go")
    time.sleep(0.3)
    verifie(m.envois(), [], "geste : clic sans la case, rien d'envoye")
    # 7. une preparation ouverte tombe si le manifeste change
    saisit(cdp, "m-name", "Autre nom")
    clic(cdp, "m-go")
    verifie(attend(cdp, "document.getElementById('e-panneau').hidden", 10), True, "manifeste enregistre : la preparation tombe")
    attend(cdp, "!document.getElementById('v-go').disabled", 15)
    clic(cdp, "t-go")
    attend(cdp, "!document.getElementById('e-panneau').hidden", 20)
    # 8. envoi HTTP, sans redemarrage
    clic(cdp, "e-vu")
    verifie(cdp.js("document.getElementById('e-go').disabled"), False, "geste : case cochee, « Envoyer » actif")
    clic(cdp, "e-go")
    verifie(attend(cdp, "document.getElementById('e-retour').textContent.indexOf('Envoyé') >= 0", 20), True, "envoi HTTP : confirme dans la page")
    vus = m.envois()
    verifie((len(vus), vus[0]["fichier"], vus[0]["transport"]) if vus else None, (1, ".extensions/ext_a.tapp", "http"), "envoi HTTP : le sous-dossier, la voie")
    verifie(vus[0]["redemarrer"] if vus else None, False, "envoi : sans redemarrage par defaut")
    verifie("/.extensions/ext_a.tapp" in (vus[0]["sur_carte"] if vus else []), True, "envoi HTTP : le fichier est sur la carte simulee")
    verifie((cache(cdp, "e-panneau"), cdp.js("document.getElementById('e-go').disabled")), (True, True), "envoi : la preparation est consommee, pas de second envoi")
    # 9. reponse perimee : H retenue par la page, M arrive d'abord, H lachee ensuite
    cdp.js("window.__retenir = true")
    saisit(cdp, "e-carte", "", "change")
    carte_choisie(cdp, env)
    verifie(attend(cdp, "window.__lache !== null", 10), True, "perimee : la reponse de la voie HTTP est retenue par la page")
    clic(cdp, "e-mqtt")
    verifie(attend(cdp, "document.getElementById('e-etat').textContent.indexOf('par MQTT') >= 0", 15), True, "perimee : la voie MQTT est preparee")
    jeton_vu = cdp.js("S.prep.jeton")
    cdp.js("window.__lache()")
    time.sleep(0.8)
    verifie(("par MQTT" in texte(cdp, "e-etat"), cdp.js("S.prep && S.prep.jeton") == jeton_vu), (True, True), GENERATION)
    clic(cdp, "e-vu")
    clic(cdp, "e-http")                                  # autre voie : la preparation tombe, rien ne part sur l'ancienne
    verifie(cdp.js("document.getElementById('e-go').disabled && S.prep === null"), True, "voie changee : « Envoyer » grise tout de suite")
    verifie(attend(cdp, "!document.getElementById('e-panneau').hidden && document.getElementById('e-etat').textContent.indexOf('adresse') >= 0", 15), True, "voie changee : nouvelle preparation")
    verifie(cdp.js("document.getElementById('e-vu').checked"), False, "voie changee : la case est a recocher")
    clic(cdp, "e-mqtt")
    attend(cdp, "!document.getElementById('e-panneau').hidden && document.getElementById('e-etat').textContent.indexOf('par MQTT') >= 0", 15)
    # fabriquer en MQTT : pas de lecture sans geste (elle annulerait un transfert en cours), puis « Lire la carte »
    lues = cdp.js("window.__prepares")
    clic(cdp, "t-go")
    verifie(attend(cdp, "document.getElementById('e-etat').textContent.indexOf('Lire la carte') >= 0", 20) and cache(cdp, "e-panneau")
            and cdp.js("window.__prepares") == lues, True, "fabriquer en MQTT : pas de lecture de la carte sans geste")
    clic(cdp, "e-lire")
    verifie(attend(cdp, "!document.getElementById('e-panneau').hidden && document.getElementById('e-etat').textContent.indexOf('par MQTT') >= 0", 15), True, "« Lire la carte » : la preparation repart")
    # envoi refuse (jeton perime) : la preparation tombe, « Lire la carte » la refait
    cdp.js("S.prep.jeton = 'perime'")
    clic(cdp, "e-vu")
    clic(cdp, "e-go")
    verifie(attend(cdp, "document.getElementById('e-retour').textContent.indexOf('Lire la carte') >= 0", 15) and cdp.js("S.prep === null && document.getElementById('e-go').disabled"), True, "envoi refuse : la preparation tombe")
    clic(cdp, "e-lire")
    attend(cdp, "!document.getElementById('e-panneau').hidden && document.getElementById('e-etat').textContent.indexOf('par MQTT') >= 0", 15)
    clic(cdp, "e-vu")
    # l'ecran change de voie sans evenement : l'envoi garde la voie preparee
    cdp.js("document.getElementById('e-http').checked = true")
    clic(cdp, "e-go")
    verifie(attend(cdp, "document.getElementById('e-retour').textContent.indexOf('Envoyé') >= 0", 20), True, "envoi MQTT : confirme dans la page")
    vus = m.envois()
    verifie(vus[-1]["transport"] if vus else None, "mqtt", "perimee : l'envoi part par la voie preparee")
    verifie("/.extensions/ext_a.tapp" in (vus[-1]["sur_carte"] if vus else []), True, "envoi MQTT : le fichier est sur la carte simulee")
    # 10. autre extension : rien de la precedente ne reste
    clic(cdp, "e-http")
    attend(cdp, "!document.getElementById('e-panneau').hidden", 15)
    saisit(cdp, "c-nom", "ext-b")
    cdp.js("document.getElementById('c-g-B').checked = true")
    clic(cdp, "c-go")
    verifie(attend(cdp, "document.getElementById('f-nom').textContent === 'ext-b' && document.querySelectorAll('#v-points .bon').length === 4", 20), True, "gabarit B : 4 points bons")
    verifie((cache(cdp, "e-panneau"), cdp.js("document.getElementById('e-carte').value"), cdp.js("S.prep")), (True, "", None), "autre extension : la preparation et la carte sont oubliees")
    verifie("mon_ext.be" in texte(cdp, "f-fichiers"), True, "gabarit B : ses fichiers")
    verifie(cdp.js("document.querySelectorAll('#liste button').length"), 2, "liste : deux extensions")
    # 11. mode sombre, telephone
    clair = cdp.js("getComputedStyle(document.body).backgroundColor")
    cdp.js("document.getElementById('theme').click()")
    sombre = cdp.js("getComputedStyle(document.body).backgroundColor")
    verifie(clair != sombre, True, "theme : l'interrupteur change le fond")
    cdp.appel("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=True)
    time.sleep(0.3)
    verifie(cdp.js("document.documentElement.scrollWidth <= window.innerWidth"), True, "telephone : pas de defilement horizontal")
    cdp.appel("Emulation.clearDeviceMetricsOverride")
    # 12. secrets et erreurs
    tout = cdp.js("document.documentElement.outerHTML + (window.__corps || []).join('\\n')") or ""
    verifie(sum(1 for v in taw.valeurs_reelles() if v in tout), 0, "aucun mot de passe du depot dans le DOM ni dans une reponse")
    erreurs = [e for e in cdp.erreurs() if not (e.startswith("journal Chrome") and (" 400 " in e or " 409 " in e))]
    verifie(erreurs, [], "aucune erreur JS (hors les 400 et 409 voulus du scenario)")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de la Fabrique d'extensions.")
    options.add_argument("--sans-temoin", action="store_true")
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
            verifie(TEMOINS[temoin][2] in vus, True, f"TEMOIN {temoin} : detecte par son test ({TEMOINS[temoin][2]})")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
