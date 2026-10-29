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
from pathlib import Path

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
                                  "redemarrer": True}, "envoi : fichiers, jeton de l'image, options")

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
