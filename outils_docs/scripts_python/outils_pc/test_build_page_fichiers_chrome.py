"""Sonde Chrome de l'onglet « Fichiers » de la page Build et televersement (A15, build_page_fichiers.py).

UTILISATION (a la main, hors de tout build ; Python de PlatformIO : l'image d'essai demande littlefs)
    python outils_docs/scripts_python/outils_pc/test_build_page_fichiers_chrome.py [--capture DOSSIER]
Code de sortie 0 = vert.

Montage de test_build_page_chrome.py (vrai build_web.py dans un processus fils, faux pio, depot d'essai
temporaire) + une vraie image LittleFS pour l'env A. AUCUN envoi ne part : dans la page, appel() est
remplace pour les POST /lancer (corps capture, reponse 200 simulee) et l'avancement est nourri par des
evenements injectes dans traite(), comme le flux les enverrait. Le temoin d'erreur JS (page avec une
erreur volontaire detectee) est celui de test_build_page_chrome.py, meme client DevTools.
"""

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import quote

import test_build_page_chrome as s
from test_build_ota_fs import fabrique_image

A, B = s.A, s.B
IMAGE = {"_persist.json": json.dumps({"serveur": {"hostname": "sonde-a"}}).encode("utf-8"),
         "autoexec.be": b"print(1)", "controleX.be": b"print(2)", "json/graphiques.json": b"{}"}
IP = "192.168.0.50"
INTERCEPTE = """(() => { window.__corps = []; const vrai = appel;
  appel = async function (url, corps) {
    if (url === "/lancer") { window.__corps.push(corps); return {ok: true, statut: 200, donnees: {ok: true}, texte: ""}; }
    return vrai(url, corps); };
  return true; })()"""
ETAT = """(() => { const t = id => document.getElementById(id);
  return {build: t('vue-build').hidden, fichiers: t('vue-fichiers').hidden,
          selection: t('onglet-fichiers').getAttribute('aria-selected'),
          cartes: [...document.querySelectorAll('#f-cartes .f-carte')].map(c => c.textContent),
          lignes: [...document.querySelectorAll('#f-table tbody tr')].map(r => r.querySelector('label').textContent),
          dossiers: [...document.querySelectorAll('.f-dossier')].map(b => b.firstChild.textContent + (b.getAttribute('aria-pressed') === 'true' ? '*' : '')),
          panier: [...document.querySelectorAll('#f-panier li .chemin')].map(x => x.textContent),
          image: t('f-image').textContent, pourquoi: t('f-pourquoi').textContent, note: t('f-note').textContent,
          envoyer: t('f-envoyer').textContent, envoyer_off: t('f-envoyer').disabled,
          preparer: t('f-preparer').textContent, preparer_off: t('f-preparer').disabled,
          berry: t('f-berry').checked, berry_off: t('f-berry').disabled, tableau: t('f-table').textContent,
          suivi: t('f-suivi').hidden, titre: t('f-suivi-titre').textContent, pourcent: t('f-pourcent').textContent,
          largeur: t('f-barre').firstChild.style.width, barre: t('f-barre').className,
          valeur: t('f-barre').getAttribute('aria-valuenow'),
          journal: [...document.querySelectorAll('#f-journal li')].map(l => l.textContent)}; })()"""


def clic(cdp, selecteur):
    return cdp.js(f"(() => {{ const e = document.querySelector({json.dumps(selecteur)}); if (!e) return 'absent'; e.click(); return true; }})()")


def etat(cdp):
    time.sleep(0.3)
    return cdp.js(ETAT)


def sonde_onglet(m, capture):
    cdp = m.cdp
    m.ouvre()
    e = etat(cdp)
    s.verifie((e["build"], e["fichiers"], e["selection"]), (False, True, "false"), "onglet : Build affiche au chargement")
    clic(cdp, "#onglet-fichiers")
    e = etat(cdp)
    s.verifie((e["build"], e["fichiers"], e["selection"]), (True, False, "true"), "onglet : clic -> vue Fichiers, Build cachee")
    s.verifie(len(e["cartes"]), 3, "cartes : les 3 envs « Mes cartes » envoyables en OTA, ni base ni amont")
    s.verifie([B in c and "par le maître" in c for c in e["cartes"]], [False, True, False],
              "cartes : adresse de B par le maitre, provenance affichee (temoins : A et C)")
    s.verifie((e["envoyer_off"], e["preparer_off"], "choisir une carte" in e["pourquoi"]), (True, True, True),
              "cartes : rien de choisi -> boutons grises, raison dite")

    clic(cdp, f"#f-carte-{A}")
    s.attend(cdp, "document.querySelectorAll('#f-table tbody tr').length === 4", 10)
    e = etat(cdp)
    s.verifie(e["lignes"], sorted(IMAGE), "liste : les 4 fichiers de l'image, tries")
    s.verifie(("Image du FS du" in e["image"], e["dossiers"]), (True, ["Tous*", "/ (racine)", "json/"]),
              "liste : date de l'image ; dossiers Tous / racine / json")
    s.verifie("sauvegardé avant l'envoi" in e["tableau"], True, "liste : _persist.json annonce « sauvegardé avant l'envoi »")
    s.verifie(("adresse de la carte à saisir" in e["pourquoi"], e["envoyer_off"], e["preparer_off"]), (True, True, False),
              "liste : sans adresse -> envoi refuse, raison dite ; Preparer actif")
    cdp.js(f"""(() => {{ const c = document.querySelector('#f-cartes .champ[aria-label$="{A}"]');
      c.value = '{IP}'; c.dispatchEvent(new Event('input')); return true; }})()""")
    e = etat(cdp)
    s.verifie(("cocher des fichiers" in e["pourquoi"], e["envoyer"]), (True, "Envoyer 0 fichier"), "liste : adresse saisie -> reste a cocher")
    s.verifie(cdp.js(f"choix['{A}'].ip"), IP, "adresse : partagee avec l'onglet Build (choix[env].ip)")

    clic(cdp, 'input[data-chemin="autoexec.be"]')
    e = etat(cdp)
    s.verifie((e["panier"], e["envoyer"], e["envoyer_off"], e["berry"]), (["autoexec.be"], "Envoyer 1 fichier", False, True),
              "panier : un .be coche -> panier, bouton actif, « Recharger Berry » coche d'office")
    clic(cdp, ".f-dossier:nth-child(3)")                 # json/
    e = etat(cdp)
    s.verifie((e["lignes"], e["dossiers"][2]), (["json/graphiques.json"], "json/*"), "dossier : json/ -> ses seuls fichiers")
    clic(cdp, "#f-table thead input")
    clic(cdp, ".f-dossier:nth-child(1)")
    e = etat(cdp)
    s.verifie((len(e["lignes"]), e["panier"]), (4, ["autoexec.be", "json/graphiques.json"]),
              "dossier : « tout cocher » limite au dossier affiche, coches gardees en revenant a Tous")
    clic(cdp, 'input[data-chemin="_persist.json"]')
    e = etat(cdp)
    s.verifie(("persist de la carte est sauvegardé" in e["note"], e["envoyer"]), (True, "Envoyer 3 fichiers"),
              "panier : _persist.json -> note de sauvegarde et rechargement")
    clic(cdp, "#f-panier li:nth-child(3) button")
    e = etat(cdp)
    s.verifie(e["panier"], ["_persist.json", "autoexec.be"], "panier : « retirer » decoche le fichier")
    clic(cdp, "#f-restart")
    e = etat(cdp)
    s.verifie((e["berry_off"], "recharge aussi Berry" in e["note"]), (True, True), "options : redemarrer -> Recharger Berry grise")

    # envoi : corps de POST /lancer (intercepte, rien ne part)
    cdp.js(INTERCEPTE)
    clic(cdp, "#f-envoyer")
    time.sleep(0.3)
    corps = cdp.js("window.__corps")[-1]
    jeton = str((m.depot / ".pio" / "build" / A / "littlefs.bin").stat().st_mtime_ns)
    s.verifie((corps["actions"], corps["onglet"], corps["lignes"]),
              (["fichiers"], "fichiers", [{"env": A, "methode": "ota", "port": "", "ip": IP}]),
              "envoi : action « fichiers », une ligne OTA a l'adresse saisie, onglet fichiers")
    s.verifie(corps["fichiers"], {"liste": ["_persist.json", "autoexec.be"], "jeton": jeton, "recharger_berry": False,
                                  "redemarrer": True, "transport": "http", "effacer": False},
              "envoi : fichiers, jeton de l'image, options, transport http par defaut")

    # avancement : un lancement de l'onglet Build n'est pas suivi ici (temoin), celui des fichiers l'est
    s.injecte(cdp, [{"type": "debut", "env": None, "lignes": [{"env": B, "methode": "com", "port": "COM13", "ip": ""}],
                     "actions": ["compiler"]}, {"type": "fin", "resultat": "succes", "succes": [B], "echecs": []}])
    s.verifie(etat(cdp)["suivi"], True, "avancement : temoin, un build de l'onglet Build n'apparait pas ici")
    ligne = {"env": A, "methode": "ota", "port": "", "ip": IP}
    s.injecte(cdp, [{"type": "debut", "env": None, "lignes": [ligne], "actions": ["fichiers"]},
                    {"type": "debut", "env": A, "actions": ["fichiers"], "methode": "ota", "ip": IP},
                    {"type": "etape", "env": A, "action": "fichiers", "etape": "Sauvegarde du persist", "pourcent": None,
                     "detail": f"depuis {IP}"},
                    {"type": "etape", "env": A, "action": "fichiers", "etape": "Envoi du file system", "pourcent": 40,
                     "detail": "1/2 /_persist.json"}])
    e = etat(cdp)
    s.verifie((e["suivi"], e["pourcent"], e["largeur"], e["valeur"]), (False, "40 %", "40%", "40"),
              "avancement : barre a 40 %, valeur accessible")
    s.verifie(e["journal"], [f"Sauvegarde du persist · depuis {IP}", "Envoi du file system · 1/2 /_persist.json"],
              "avancement : journal des etapes et de leur detail")
    s.verifie(("Envoi des fichiers vers " + A in e["titre"], "en cours" in e["titre"], e["envoyer_off"]), (True, True, True),
              "avancement : titre en cours, envoi grise pendant le lancement")
    s.injecte(cdp, [{"type": "fin_env", "env": A, "resultat": "succes", "statuts": {"fichiers": "succes"}, "secondes": 3.2},
                    {"type": "fin", "resultat": "succes", "succes": [A], "echecs": []}])
    e = etat(cdp)
    s.verifie(("réussi" in e["titre"], e["pourcent"], e["barre"]), (True, "100 %", "barre succes"), "avancement : fin -> reussi, 100 %")
    s.verifie(cdp.js("document.getElementById('blocs').textContent.includes('Envoyer des fichiers')"), True,
              "suivi commun : ligne « Envoyer des fichiers » nommee")

    # echec : bandeau rouge dans l'onglet
    s.injecte(cdp, [{"type": "debut", "env": None, "lignes": [ligne], "actions": ["fichiers"]},
                    {"type": "echec", "env": A, "action": "fichiers", "motif": "carte injoignable"},
                    {"type": "fin_env", "env": A, "resultat": "echec", "statuts": {"fichiers": "echec"}},
                    {"type": "fin", "resultat": "echec", "succes": [], "echecs": [A]}])
    e = etat(cdp)
    s.verifie(("échec" in e["titre"], e["barre"], e["journal"]), (True, "barre echec", ["Échec : carte injoignable"]),
              "avancement : echec dit, journal du nouveau lancement seulement")

    # Preparer la liste : buildfs, puis relecture de la liste a la fin
    clic(cdp, "#f-preparer")
    time.sleep(0.3)
    corps = cdp.js("window.__corps")[-1]
    s.verifie((corps["actions"], corps["onglet"], corps["lignes"][0]["env"]), (["buildfs"], "fichiers", A),
              "preparer : buildfs de la carte choisie, onglet fichiers")
    s.verifie(etat(cdp)["preparer"], "Préparation…", "preparer : bouton occupe")
    cdp.js("window.__lectures = 0; const v2 = appel; appel = async (u, c) => { if (u.startsWith('/fichiers')) window.__lectures++; return v2(u, c); }")
    s.injecte(cdp, [{"type": "debut", "env": None, "lignes": [{"env": A, "methode": "com", "port": "", "ip": ""}], "actions": ["buildfs"]},
                    {"type": "etape", "env": A, "action": "buildfs", "etape": "Construction du FS", "pourcent": None},
                    {"type": "fin_env", "env": A, "resultat": "succes", "statuts": {"buildfs": "succes"}},
                    {"type": "fin", "resultat": "succes", "succes": [A], "echecs": []}])
    e = etat(cdp)
    s.verifie(("Préparation de la liste de " + A in e["titre"], e["preparer"], cdp.js("window.__lectures")),
              (True, "Préparer la liste", 1), "preparer : suivi dans l'onglet, liste relue a la fin")

    # A16 : transport MQTT (adresse inutile) et effacement de tout le FS (MQTT seulement, confirme)
    js = lambda x: cdp.js(f"(() => {{ const t = id => document.getElementById(id); return {x}; }})()")
    cdp.js(f"""(() => {{ const c = document.querySelector('#f-cartes .champ[aria-label$="{A}"]');
      c.value = ''; c.dispatchEvent(new Event('input')); return true; }})()""")
    s.verifie("adresse de la carte" in etat(cdp)["pourquoi"], True, "mqtt : temoin, en HTTP sans adresse -> envoi refuse")
    s.verifie(js("t('f-effacer').disabled"), True, "mqtt : « Effacer tout le FS » grise en HTTP")
    clic(cdp, "input[name=f-transport][value=mqtt]")
    e = etat(cdp)
    s.verifie((e["pourquoi"], e["envoyer"], e["envoyer_off"]), ("", "Envoyer 2 fichiers par MQTT", False),
              "mqtt : sans adresse, envoi possible")
    clic(cdp, "#f-effacer")
    e = etat(cdp)
    s.verifie((e["envoyer"], "Tout le FS de la carte sera supprimé" in e["note"]), ("Effacer puis envoyer 4 fichiers par MQTT", True),
              "effacer : toute l'image annoncee, avertissement")
    n = len(cdp.js("window.__corps"))
    cdp.js("window.confirm = () => false")
    clic(cdp, "#f-envoyer")
    time.sleep(0.3)
    s.verifie(len(cdp.js("window.__corps")), n, "effacer : confirmation refusee -> rien lance")
    cdp.js("window.confirm = () => true")
    clic(cdp, "#f-envoyer")
    time.sleep(0.3)
    corps = cdp.js("window.__corps")[-1]
    s.verifie((corps["fichiers"]["transport"], corps["fichiers"]["effacer"], corps["fichiers"]["liste"]),
              ("mqtt", True, sorted(IMAGE)), "effacer : corps transport mqtt, effacer, liste = toute l'image")
    s.injecte(cdp, [{"type": "fin", "resultat": "succes", "succes": [A], "echecs": []}])
    clic(cdp, "input[name=f-transport][value=http]")
    s.verifie((js("t('f-effacer').checked"), js("t('f-effacer').disabled")), (False, True), "retour en HTTP : effacement decoche et grise")

    # telephone, puis onglet retenu au rechargement
    cdp.appel("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=True)
    time.sleep(0.8)
    s.verifie(cdp.js("document.documentElement.scrollWidth") <= 390, True, "telephone : pas de defilement horizontal")
    if capture:
        cdp.capture(Path(capture) / "build-fichiers-telephone.png")
    cdp.appel("Emulation.setDeviceMetricsOverride", width=1280, height=1000, deviceScaleFactor=1, mobile=False)
    if capture:
        time.sleep(0.5)
        cdp.capture(Path(capture) / "build-fichiers.png")
    m.ouvre()
    s.verifie(etat(cdp)["fichiers"], False, "rechargement : onglet Fichiers retenu")
    clic(cdp, "#onglet-build")
    s.verifie(etat(cdp)["build"], False, "rechargement : retour a Build")
    s.verifie(cdp.erreurs(), [], "fin : aucune erreur JS")


# A7 (atelier-destinations) : arrivee par le lien de l'Atelier des graphiques. fetch est enrobe AVANT le script de
# la page (le buildfs part au chargement) : POST /lancer captures (en-tetes compris), reponses simulees, rien ne part.
BANDEAU = ("Fichiers sélectionnés automatiquement par l'Atelier des graphiques, pour téléverser un graphique nouveau ou "
           "modifié. Vérifiez puis cliquez sur « Envoyer ».")
ENROBE = """(() => { window.__corps = []; const cfg = CFG, vrai = window.fetch.bind(window);
  window.fetch = async (url, o) => { o = o || {};
    if (String(url) === "/lancer") {
      window.__corps.push({corps: JSON.parse(o.body), entetes: o.headers || {}, methode: o.method});
      const r = cfg.lancer.length ? cfg.lancer.shift() : {statut: 200, texte: '{"ok": true}'};
      if (!r.statut) throw new TypeError("coupure simulee");              // appel() : statut 0, comme un delai depasse
      return new Response(r.texte, {status: r.statut}); }
    if (String(url) === "/execution" && cfg.execution.length) { const x = cfg.execution.shift();   // null = panne, {} = vrai serveur
      if (x && x.delai) await new Promise(f => setTimeout(f, x.delai));
      if (x === null) return new Response("panne", {status: 500});
      if (x.en_cours !== undefined) return new Response(JSON.stringify(x), {status: 200}); }
    return vrai(url, o); };
  if (cfg.fluxDelai) { const VS = window.EventSource;                     // flux ouvert en retard : ordre force
    window.EventSource = function (u) { const moi = this; this.readyState = 0;
      setTimeout(() => { const r = new VS(u); r.onmessage = m => moi.onmessage && moi.onmessage(m); r.onerror = e => moi.onerror && moi.onerror(e);
        r.onopen = e => moi.onopen && moi.onopen(e); }, cfg.fluxDelai); };
    window.EventSource.CLOSED = 2; } })()"""
ETAT_AT = f"""(() => {{ const t = id => document.getElementById(id);
  return {{fichiers: t('vue-fichiers').hidden, carte: !!(t('f-carte-{A}') || {{}}).checked, bandeau: t('f-atelier').hidden,
          texte: t('f-atelier-texte').textContent, notes: [...document.querySelectorAll('#f-atelier-notes li')].map(l => l.textContent),
          panier: [...document.querySelectorAll('#f-panier li .chemin')].map(x => x.textContent), restart: t('f-restart').checked,
          berry_off: t('f-berry').disabled, search: location.search, corps: window.__corps || []}}; }})()"""
BUILDFS = [{"type": "debut", "env": None, "lignes": [{"env": A, "methode": "com", "port": "", "ip": ""}], "actions": ["buildfs"]},
           {"type": "etape", "env": A, "action": "buildfs", "etape": "Construction du FS", "pourcent": None},
           {"type": "fin_env", "env": A, "resultat": "succes", "statuts": {"buildfs": "succes"}},
           {"type": "fin", "resultat": "succes", "succes": [A], "echecs": []}]
FIN_AUTRE = [{"type": "fin", "resultat": "succes", "succes": [B], "echecs": []}]
ATTENDU_LANCER = {"lignes": [{"env": A, "methode": "com", "port": "", "ip": ""}], "actions": ["buildfs"], "onglet": "fichiers"}


def arrive(m, requete, execution=(), lancer=(), sans_enrobe=False, flux_delai=0, attente=2.5):
    """Ouvre la page par le lien de l'atelier (`requete` = chaine de requete), fetch enrobe ; renvoie l'etat.
    `execution`, `lancer` : reponses simulees, une par appel, puis le vrai serveur (/lancer : 200 simule)."""
    if sans_enrobe:                                     # vrai /lancer : le faux pio du montage tourne
        m.cdp.appel("Page.navigate", url=m.url + "?" + requete)
        time.sleep(2.5)
        return etat_at(m.cdp)
    cfg = json.dumps({"execution": list(execution), "lancer": list(lancer), "fluxDelai": flux_delai})
    ident = m.cdp.appel("Page.addScriptToEvaluateOnNewDocument", source=ENROBE.replace("CFG", cfg))["identifier"]
    m.cdp.appel("Page.navigate", url=m.url + "?" + requete)
    time.sleep(attente)
    m.cdp.appel("Page.removeScriptToEvaluateOnNewDocument", identifier=ident)
    return etat_at(m.cdp)


def etat_at(cdp):
    time.sleep(0.3)
    return cdp.js(ETAT_AT)


def lien(fichiers, redemarrer="1", env=A):
    return f"env={quote(env, safe='')}&depuis=atelier&fichiers={quote(fichiers, safe='')}&redemarrer={quote(redemarrer, safe='')}"


def envois(e):
    return [c for c in e["corps"] if c["corps"].get("actions") != ["buildfs"]]


def sonde_atelier(m):
    cdp = m.cdp
    # nominal : buildfs au chargement, rien de coche avant la fin, puis exactement la liste
    e = arrive(m, lien("autoexec.be,json/graphiques.json,sd/js/absent.js,constructor"))
    s.verifie((e["fichiers"], e["carte"], e["bandeau"], e["texte"]), (False, True, False, BANDEAU),
              "atelier : onglet Fichiers, carte de l'env choisie, bandeau exact de la spec")
    s.verifie([(c["corps"], c["entetes"].get("X-Build"), c["methode"]) for c in e["corps"]], [(ATTENDU_LANCER, "1", "POST")],
              "atelier : un seul POST /lancer buildfs de l'env, en-tete X-Build, onglet fichiers")
    s.verifie((e["panier"], e["restart"]), ([], False), "atelier : rien de coche avant la fin de l'image (ancienne image ignoree)")
    s.verifie(e["search"], f"?env={A}", "atelier : depuis/fichiers/redemarrer retires de l'URL une fois le lancement accepte")
    s.injecte(cdp, BUILDFS)
    s.attend(cdp, "document.querySelectorAll('#f-panier li').length > 0", 5)
    e = etat_at(cdp)
    s.verifie((e["panier"], e["restart"], e["berry_off"]), (["autoexec.be", "json/graphiques.json"], True, True),
              "atelier : image prete -> cochees exactement les fichiers presents de la liste, Redemarrer coche (redemarrer=1)")
    s.verifie([any(x in n and "Absent" in n for n in e["notes"]) for x in ("sd/js/absent.js", "constructor")], [True, True],
              "atelier : fichiers absents de l'image signales (« constructor » compris, pas pris pour present)")
    s.injecte(cdp, FIN_AUTRE)
    e = etat_at(cdp)
    s.verifie((len(e["corps"]), envois(e)), (1, []), "atelier : aucun envoi, et une autre fin ne relance rien")
    cdp.appel("Page.reload")
    time.sleep(2.5)
    e = etat_at(cdp)
    s.verifie((e["corps"], e["bandeau"], e["search"]), ([], True, f"?env={A}"), "atelier : rechargement -> aucun buildfs relance")

    # parametres hostiles : rien de lance, message
    for env in ("tasmota32", "../x", "tasmota32-inconnu"):
        e = arrive(m, lien("autoexec.be", env=env))
        s.verifie((e["corps"], e["texte"], any(env in n for n in e["notes"])), ([], "", True),
                  f"hostile : env {env!r} (amont, invalide ou inconnu) -> aucun POST, message, pas de bandeau de selection")
    hostiles = ["../x", "/abs.be", "C:\\w.be", "sd/../y", "a\\b"]
    e = arrive(m, lien(",".join(hostiles), redemarrer="oui"))
    s.verifie((e["corps"], e["panier"], e["restart"]), ([], [], False), "hostile : chemins tous refuses -> aucun POST, rien coche")
    s.verifie([any(h in n for n in e["notes"]) for h in hostiles] + [any("oui" in n for n in e["notes"])], [True] * 6,
              "hostile : chaque chemin refuse et la valeur de redemarrer signales")
    e = arrive(m, lien("", redemarrer="0"))
    s.verifie((e["corps"], any("aucun fichier" in n for n in e["notes"])), ([], True), "hostile : liste vide -> aucun POST, message")

    # build deja en cours : attente de sa fin (flux), puis un seul buildfs ; chemin refuse signale, Redemarrer non coche
    e = arrive(m, lien("autoexec.be,../z", redemarrer="0"), execution=[{"en_cours": True, "numero": 0, "pause": None}])
    s.verifie((e["corps"], e["texte"], any("en cours" in n for n in e["notes"])), ([], BANDEAU, True),
              "en cours : aucun POST pendant le lancement en cours, attente dite")
    s.injecte(cdp, FIN_AUTRE)
    e = etat_at(cdp)
    s.verifie([c["corps"] for c in e["corps"]], [ATTENDU_LANCER], "en cours : fin du lancement -> buildfs lance, une fois")
    s.injecte(cdp, BUILDFS)
    s.attend(cdp, "document.querySelectorAll('#f-panier li').length > 0", 5)
    e = etat_at(cdp)
    s.verifie((e["panier"], e["restart"], any("../z" in n for n in e["notes"]), envois(e)), (["autoexec.be"], False, True, []),
              "en cours : coche a la fin, Redemarrer non coche (0), chemin refuse signale, aucun envoi")

    # build externe (refus 409) : nouvel essai par minuterie ; buildfs en echec -> rien coche
    e = arrive(m, lien("autoexec.be"), lancer=[{"statut": 409, "texte": "un build est déjà en cours (pio run -e x (VS Code))"}])
    s.verifie((len(e["corps"]), any("VS Code" in n for n in e["notes"])), (1, True), "externe : refus affiche")
    s.attend(cdp, "window.__corps.length >= 2", 9)
    e = etat_at(cdp)
    s.verifie([c["corps"] for c in e["corps"]], [ATTENDU_LANCER] * 2, "externe : nouvel essai seul, accepte")
    s.injecte(cdp, BUILDFS[:2] + [{"type": "fin_env", "env": A, "resultat": "echec", "statuts": {"buildfs": "echec"}},
                                  {"type": "fin", "resultat": "termine", "succes": [], "echecs": [A]}])
    e = etat_at(cdp)
    s.verifie((e["panier"], any("échec" in n for n in e["notes"])), ([], True), "externe : buildfs en echec -> rien coche, dit")
    sonde_historique(m)
    s.verifie(cdp.erreurs(), [], "atelier : aucune erreur JS")
    # A2, en dernier (serveur coupe = erreurs reseau au journal de Chrome) : outil redemarre, aucun evenement ensuite
    arrive(m, lien("autoexec.be"))
    s.injecte(cdp, BUILDFS[:1])                          # debut en direct : sans lui, la fin de l'historique rejoue laisse enCours a faux
    m.redemarre_serveur()
    s.attend(cdp, "!AT", 20)
    e = etat_at(cdp)
    s.verifie((any("a redémarré" in n for n in e["notes"]), e["texte"], cdp.js("[AT, F.prepa, $('f-preparer').disabled, $('f-preparer').textContent]")),
              (True, "", [None, False, False, "Préparer la liste"]), "redemarrage : outil relance sans evenement -> abandon dit, bouton libre")


def poste(m, corps):
    requete = urllib.request.Request(m.url + "lancer", data=json.dumps(corps).encode("utf-8"), method="POST",
                                     headers={"X-Build": "1", "Content-Type": "application/json"})
    with urllib.request.urlopen(requete, timeout=10) as r:
        return r.status


def sonde_historique(m):
    """Correction tour 1 (B1) : le serveur a deja un lancement dans son flux, rejoue a l'ouverture de la page."""
    cdp = m.cdp
    s.verifie(poste(m, ATTENDU_LANCER), 200, "historique : vrai buildfs prealable (faux pio)")
    limite = time.monotonic() + 30
    while time.monotonic() < limite and json.loads(urllib.request.urlopen(m.url + "execution", timeout=5).read())["en_cours"]:
        time.sleep(0.3)
    e = arrive(m, lien("autoexec.be,json/graphiques.json"), sans_enrobe=True)
    s.attend(cdp, "document.querySelectorAll('#f-panier li').length > 0", 20)
    e = etat_at(cdp)
    s.verifie((e["panier"], e["restart"], e["search"]), (["autoexec.be", "json/graphiques.json"], True, f"?env={A}"),
              "historique : vrai buildfs apres un lancement rejoue -> fichiers coches, Redemarrer coche")
    # /execution en panne au chargement, ordres forces. Flux AVANT la relecture : l'ancien `fin` arrive en direct,
    # hors de tout rejeu, et ne doit ni abandonner ni cocher (tue le mutant sans `AT.n0 === undefined`).
    e = arrive(m, lien("autoexec.be"), execution=[None, {"delai": 1500}])
    s.verifie((len(e["corps"]), e["panier"], e["texte"], cdp.js("dernierN > 0 && AT.etat")), (1, [], BANDEAU, "prepa"),
              "ordre : flux avant la relecture -> ancien fin ignore, un buildfs, rien coche")
    s.injecte(cdp, BUILDFS)
    s.attend(cdp, "document.querySelectorAll('#f-panier li').length > 0", 5)
    s.verifie(etat_at(cdp)["panier"], ["autoexec.be"], "ordre : flux avant la relecture -> fin de NOTRE buildfs, coche")
    # Flux APRES le POST : F.prepa est deja vrai quand l'historique arrive (tue le mutant sans `rejeuJusqua = numero`)
    e = arrive(m, lien("autoexec.be"), execution=[None], flux_delai=1200)
    s.verifie((len(e["corps"]), e["panier"], cdp.js("dernierN > 0 && AT.etat")), (1, [], "prepa"),
              "ordre : flux apres le POST -> historique pris pour un rejeu, rien coche depuis l'ancien fin")
    s.injecte(cdp, BUILDFS)
    s.attend(cdp, "document.querySelectorAll('#f-panier li').length > 0", 5)
    s.verifie(etat_at(cdp)["panier"], ["autoexec.be"], "ordre : flux apres le POST -> fin de NOTRE buildfs, coche")
    # A1 : autre carte choisie pendant la relecture de /execution : jamais de buildfs sur la mauvaise carte
    arrive(m, lien("autoexec.be"), execution=[{}, {"delai": 1500}], attente=0.8)
    cdp.js(f"choisitCarte('{B}'); true")
    time.sleep(1.5)
    e = etat_at(cdp)
    s.verifie((e["corps"], any("Autre carte" in n for n in e["notes"]), e["texte"]), ([], True, ""),
              "carte : changee pendant /execution -> aucun buildfs, abandon dit, bandeau de selection retire")
    # S1 : le `fin` double la reponse « en cours » de /execution : la page ne reste pas bloquee, un seul buildfs ensuite
    arrive(m, lien("autoexec.be"), execution=[{}, {"delai": 1500, "en_cours": True, "numero": 0, "pause": None}], attente=0.8)
    s.injecte(cdp, FIN_AUTRE)
    s.attend(cdp, "window.__corps.length >= 1", 9)
    e = etat_at(cdp)
    s.verifie(([c["corps"] for c in e["corps"]], sum("en cours" in n for n in e["notes"])), ([ATTENDU_LANCER], 1),
              "fin doublee : nouvel essai seul -> un buildfs, attente dite une fois")
    # /fichiers en panne apres NOTRE buildfs : liste illisible dite, aucun fichier declare absent a tort
    arrive(m, lien("autoexec.be"))
    cdp.js("""(() => { const v = window.fetch; window.fetch = (u, o) => String(u).startsWith("/fichiers") ?
      Promise.resolve(new Response("panne", {status: 500})) : v(u, o); return true; })()""")
    s.injecte(cdp, BUILDFS)
    e = etat_at(cdp)
    s.verifie((e["panier"], any("illisible" in n for n in e["notes"]), any("Absent" in n for n in e["notes"])), ([], True, False),
              "liste : /fichiers en panne apres le buildfs -> illisible dit, pas « absent »")
    # A2 : renumerotation du flux (outil redemarre) pendant NOTRE buildfs : abandon dit, bandeau retire
    arrive(m, lien("autoexec.be"))
    s.injecte(cdp, [{"n": 1, "type": "debut", "env": None, "lignes": [{"env": B, "methode": "com", "port": "COM13", "ip": ""}], "actions": ["compiler"]}])
    e = etat_at(cdp)
    s.verifie((any("a redémarré" in n for n in e["notes"]), e["texte"], cdp.js("[AT, F.prepa]")), (True, "", [None, False]),
              "redemarrage : flux renumerote -> abandon dit, F.prepa remis a faux")
    # fin d'un autre lancement a la place du notre : abandon dit, jamais muet
    e = arrive(m, lien("autoexec.be"))
    s.injecte(cdp, [{"type": "debut", "env": None, "lignes": [{"env": B, "methode": "com", "port": "COM13", "ip": ""}],
                     "actions": ["compiler"]}] + FIN_AUTRE)
    e = etat_at(cdp)
    s.verifie((e["panier"], any("autre lancement" in n for n in e["notes"])), ([], True), "rejeu : fin non reconnue -> abandon dit")
    # delai depasse sur POST /lancer : resultat incertain, pas « refuse »
    e = arrive(m, lien("autoexec.be"), lancer=[{"statut": 0, "texte": ""}])
    refus = cdp.js("document.getElementById('f-refus').textContent")
    s.verifie((len(e["corps"]), any("incertain" in n for n in e["notes"]), "incertain" in refus, "refusé" in refus, e["search"]),
              (1, True, True, False, f"?env={A}"), "delai : resultat incertain dit (pas « refuse »), URL nettoyee")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de l'onglet Fichiers de la page build.")
    options.add_argument("--capture", help="dossier ou ecrire les captures PNG")
    args = options.parse_args()
    m = None
    try:
        m = s.Montage()
        m.demarre(False)
        fabrique_image(m.depot / ".pio" / "build" / A / "littlefs.bin", IMAGE)
        sonde_onglet(m, args.capture)
        sonde_atelier(m)
    except FileNotFoundError as erreur:
        print(f"BLOQUE : {erreur}")
        return 3
    except Exception as erreur:
        s.verifie(repr(erreur), "pas d'exception de la sonde", "sonde : deroulement")
    finally:
        if m:
            m.ferme()
    print("\n" + ("VERT" if not s.ECHECS else f"ROUGE : {len(s.ECHECS)} echec(s) : {s.ECHECS}"))
    return 1 if s.ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
