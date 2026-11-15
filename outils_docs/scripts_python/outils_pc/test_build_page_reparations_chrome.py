"""Sonde Chrome des reparations de la page Build (build_page_reparations.py, plan build-reparations A5).

UTILISATION (a la main ; Python de PlatformIO)
    python outils_docs/scripts_python/outils_pc/test_build_page_reparations_chrome.py [--capture DOSSIER]
Code de sortie 0 = vert.

Montage de test_build_page_chrome.py (vrai build_web.py dans un processus fils, FAUX pio, depot d'essai et dossier de donnees
TEMPORAIRES) + une regle LOCALE dont l'action est `attendre 8` : le faux pio echoue sur la ligne PANNE_SONDE, la serie applique
la regle (vrais evenements `reparation`), la page est rechargee PENDANT l'attente (etat reconstruit par le rejeu). Le choix
Fermer / Attendre / Annuler est injecte (evenement synthetique, fetch bouchonne) : le vrai ne se declenche que sur un
processus etranger qui tient un fichier. Aucune pause fixe hors rendu groupe : des conditions attendues.
"""

import argparse
import json
import sys
from pathlib import Path

import test_build_page_chrome as s

B = s.B
XSS = "<img src=x onerror=window.xss=1>"
REGLE = {"id": "panne_sonde", "titre": f"Panne {XSS} de sonde", "motif": "PANNE_SONDE",
         "etapes": ["prebuild", "compilation", "liens", "buildfs"], "origine": "ia", "ajoutee_le": "2026-11-15",
         "actions": [{"action": "attendre", "parametres": {"secondes": 8}}]}
BANDEAUX = ("(() => [...document.querySelectorAll('#rep-bandeaux .bandeau')].map(b => ({etat: b.dataset.etat || '', env: b.dataset.env,"
            " texte: b.textContent, choix: !!b.dataset.choixOuvert, boutons: [...b.querySelectorAll('button')].map(x => x.dataset.choix),"
            " off: [...b.querySelectorAll('button')].map(x => x.disabled)})))()")
REGLES = ("(() => [...document.querySelectorAll('#rep-corps .rep-regle')].map(r => ({id: r.dataset.id, texte: r.textContent,"
          " supprimer: !!r.querySelector('button[data-supprime]')})))()")


def ouvre_panneau(cdp):
    cdp.js("document.getElementById('rep-panneau').open = true")
    s.attend(cdp, "document.querySelectorAll('#rep-corps .rep-regle').length >= 2", 10)


def sonde(m, capture):
    cdp = m.cdp
    local = m.t / "outils" / "build" / "reparations.json"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(json.dumps({"regles": [REGLE]}), encoding="utf-8")
    m.ouvre()

    # panneau : base + locale, Supprimer sur la locale seulement, titre et motif en texte (jamais du HTML)
    ouvre_panneau(cdp)
    regles = {r["id"]: r for r in cdp.js(REGLES)}
    s.verifie(sorted(regles), ["panne_sonde", "verrou_fichier"], "panneau : regles de base et locales listees")
    s.verifie((regles["panne_sonde"]["supprimer"], regles["verrou_fichier"]["supprimer"]), (True, False),
              "panneau : Supprimer sur la regle locale seulement")
    s.verifie((XSS in regles["panne_sonde"]["texte"], cdp.js("document.querySelectorAll('#rep-corps img').length"),
               cdp.js("window.xss === undefined")), (True, 0, True), "panneau : titre de regle echappe (pas d'element, pas d'onerror)")

    # vraie serie : B echoue sur PANNE_SONDE, la regle attend 8 s ; rechargement PENDANT l'attente
    s.SCENARIO[B]["build"]["lignes"].insert(1, "PANNE_SONDE verrou fictif")
    (m.t / "scenario.json").write_text(json.dumps(s.SCENARIO), encoding="utf-8")
    for env in (s.A, B, s.C):
        s.coche(cdp, f"#env-{env}", env == B)
    for action in ("compiler", "upload", "erase_upload", "buildfs", "uploadfs"):
        s.coche(cdp, f'input[name=action][value="{action}"]', action == "compiler")
    cdp.js("document.getElementById('lancer').click()")
    texte = f"Réparation en cours : Panne {XSS} de sonde"
    s.attend(cdp, f"[...document.querySelectorAll('#rep-bandeaux .bandeau')].some(b => b.textContent.includes({json.dumps(texte)}))", 20)
    b = cdp.js(BANDEAUX)
    s.verifie((len(b), b[0]["env"], b[0]["etat"], "relance 1/2" in b[0]["texte"]), (1, B, "en_cours", True),
              "serie : bandeau « Réparation en cours : <titre> » sur l'env, relance annoncee")
    s.verifie((cdp.js("document.querySelectorAll('#rep-bandeaux img').length"), cdp.js("window.xss === undefined")), (0, True),
              "serie : titre du bandeau echappe")
    s.verifie("[réparation]" in (cdp.js(f"document.querySelector('.bloc[data-bloc=\"{B}\"]').textContent") or ""), True,
              "serie : ligne « [réparation] … » dans le journal de l'env")
    m.ouvre()                                                          # rechargement pendant la reparation
    s.attend(cdp, f"[...document.querySelectorAll('#rep-bandeaux .bandeau')].some(b => b.textContent.includes({json.dumps(texte)}))", 10)
    s.verifie(cdp.js(BANDEAUX)[0]["etat"] in ("en_cours", "reussie", "echouee"), True,
              "rechargement : bandeau reconstruit par les evenements rejoues")
    s.attend(cdp, "document.querySelector('#rep-bandeaux .bandeau[data-etat=echouee]')", 30)
    s.verifie("Réparation échouée" in cdp.js(BANDEAUX)[0]["texte"], True, "fin : relance rejetee (meme panne) -> bandeau « échouée »")
    s.attend(cdp, "!document.getElementById('lancer').disabled", 20)

    # case « Relancer apres reparation par l'IA » : decochee par defaut, memorisee (ce navigateur), envoyee dans le lancement
    CASE = "(() => { const c = document.getElementById('ia-auto'); return c ? c.checked : null; })()"
    s.verifie(cdp.js(CASE), False, "case IA : presente et decochee par defaut")
    cdp.js("(() => { const c = document.getElementById('ia-auto'); c.checked = true; c.dispatchEvent(new Event('change')); return true; })()")
    m.ouvre()
    s.attend(cdp, "document.getElementById('ia-auto')", 10)
    s.verifie(cdp.js(CASE), True, "case IA : cochee, memorisee apres rechargement")
    cdp.js("""(() => { const f0 = window.fetch; window._f0 = f0; window._lancers = [];
      window.fetch = function (u, o) { if (String(u) === '/lancer') { window._lancers.push(JSON.parse(o.body));
          return Promise.resolve(new Response('{"ok": true}', {status: 200})); } return f0.apply(this, arguments); }; return true; })()""")
    s.attend(cdp, "document.querySelector('#env-" + B + "')", 10)
    for env in (s.A, B, s.C):
        s.coche(cdp, f"#env-{env}", env == B)
    for action in ("compiler", "upload", "erase_upload", "buildfs", "uploadfs"):
        s.coche(cdp, f'input[name=action][value="{action}"]', action == "compiler")
    cdp.js("document.getElementById('lancer').click()")
    s.attend(cdp, "window._lancers.length === 1", 10)
    s.verifie(cdp.js("window._lancers[0].ia_auto"), True, "case IA : ia_auto vrai envoye dans POST /lancer")
    cdp.js("window.fetch = window._f0; document.getElementById('ia-auto').checked = false; "
           "document.getElementById('ia-auto').dispatchEvent(new Event('change')); true")
    m.ouvre()
    s.attend(cdp, "document.getElementById('ia-auto')", 10)
    s.verifie(cdp.js(CASE), False, "case IA : decochee, memorisee apres rechargement")

    # choix Fermer / Attendre / Annuler (evenement synthetique, POST /reparation bouchonne)
    cdp.js("""(() => { const f0 = window.fetch; window._f1 = f0; window._posts = []; window._refus = false;
      window.fetch = function (u, o) { if (String(u) === '/reparation') { window._posts.push(JSON.parse(o.body));
          return Promise.resolve(new Response(window._refus ? 'aucune demande ouverte' : '{"ok": true}', {status: window._refus ? 409 : 200})); }
        return f0.apply(this, arguments); }; return true; })()""")
    ligne = {"env": B, "methode": "com", "port": "", "ip": ""}
    s.injecte(cdp, [{"type": "debut", "env": None, "actions": ["compiler"], "lignes": [ligne]},
                    {"type": "debut", "env": B, "actions": ["compiler"], "methode": "com", "port": ""},
                    {"type": "reparation", "env": B, "action": "compiler", "regle": "verrou_fichier", "etat": "en_cours", "message": "x"},
                    {"type": "choix_reparation", "env": B, "regle": "verrou_fichier", "boutons": ["fermer", "attendre", "annuler"],
                     "texte": f"{XSS} notepad.exe (pid 4242) tient C:\\x\\modules.h"}])
    s.attend(cdp, "document.querySelector('#rep-bandeaux [data-choix-ouvert]')", 5)
    b = cdp.js(BANDEAUX)[0]
    s.verifie((b["choix"], b["boutons"], b["off"], XSS in b["texte"], "notepad.exe (pid 4242)" in b["texte"]),
              (True, ["fermer", "attendre", "annuler"], [False] * 3, True, True), "choix : trois boutons, texte du processus affiche en texte")
    s.verifie((cdp.js("document.querySelectorAll('#rep-bandeaux img').length"), cdp.js("window.xss === undefined")), (0, True),
              "choix : texte du processus echappe")
    cdp.js("window._refus = true; document.querySelector('#rep-bandeaux [data-choix=attendre]').click()")
    s.attend(cdp, "document.querySelector('#rep-bandeaux .bandeau .erreur')", 5)
    b = cdp.js(BANDEAUX)[0]
    s.verifie((cdp.js("window._posts"), b["off"], "Réponse refusée" in b["texte"]), ([{"env": B, "choix": "attendre"}], [False] * 3, True),
              "choix : 409 -> message, boutons rendus, rien de ferme")
    cdp.js("window._refus = false; document.querySelector('#rep-bandeaux [data-choix=fermer]').click()")
    s.attend(cdp, "window._posts.length === 2", 5)
    s.verifie(cdp.js("window._posts[1]"), {"env": B, "choix": "fermer"}, "choix : Fermer -> POST /reparation {env, choix}")
    s.injecte(cdp, [{"type": "reparation", "env": B, "action": "compiler", "regle": "verrou_fichier", "etat": "en_cours",
                     "message": "réponse : fermer (notepad.exe)"}])
    b = cdp.js(BANDEAUX)
    s.verifie((len(b), b[0]["choix"], b[0]["etat"]), (1, False, "en_cours"), "choix : evenement suivant -> boutons retires, bandeau d'avancement")
    if capture:
        cdp.capture(Path(capture) / "build-reparations.png")
    cdp.js("window.fetch = window._f1; true")

    # diagnostic par l'IA (fetch bouchonne : aucun claude) sur un env en echec sans reparation
    cdp.js("""(() => { const f0 = window.fetch; window._f2 = f0; window._ia = [];
      window.fetch = function (u, o) { const url = String(u);
        if (url === '/reparations/diagnostic' || url === '/reparations/appliquer') { window._ia.push([url, JSON.parse(o.body)]);
          return Promise.resolve(new Response(url.endsWith('diagnostic') ? JSON.stringify({ok: true, erreur: '', cause: '<img src=x onerror=window.xss=2>',
            explication: 'Le reseau est lent.', correctif_manuel: '', refus: '', regle: {titre: 'Delai uv', motif: 'timed out after',
            actions: [{action: 'attendre', parametres: {secondes: 5}}]}}) : '{"ok": true, "attend": false}', {status: 200})); }
        return f0.apply(this, arguments); }; return true; })()""")
    s.injecte(cdp, [{"type": "debut", "env": None, "actions": ["compiler"], "lignes": [ligne]},
                    {"type": "debut", "env": B, "actions": ["compiler"], "methode": "com", "port": ""},
                    {"type": "fin_env", "env": B, "resultat": "echec", "statuts": {"compiler": "echec"}, "secondes": 1}])
    s.attend(cdp, "document.querySelector('#rep-bandeaux [data-diagnostic]')", 5)
    s.verifie(cdp.js("document.querySelectorAll('#rep-bandeaux [data-applique]').length"), 0, "ia : bouton Diagnostiquer, pas encore Appliquer")
    cdp.js("document.querySelector('#rep-bandeaux [data-diagnostic]').click()")
    s.attend(cdp, "document.querySelector('#rep-bandeaux [data-applique]')", 5)
    s.verifie((cdp.js("window._ia"), cdp.js("document.querySelectorAll('#rep-bandeaux img').length"), cdp.js("window.xss === undefined"),
               "attendre 5 s" in cdp.js("document.querySelector('#rep-bandeaux .rep-ia').textContent")),
              ([["/reparations/diagnostic", {"env": B}]], 0, True, True), "ia : proposition affichee en texte (cause echappee), regle lisible")
    cdp.js("document.querySelector('#rep-bandeaux [data-applique]').click()")
    s.attend(cdp, "window._ia.length === 2", 5)
    s.verifie((cdp.js("window._ia[1][0]"), cdp.js("window._ia[1][1].env"), cdp.js("window._ia[1][1].regle.motif")),
              ("/reparations/appliquer", B, "timed out after"), "ia : Appliquer et relancer -> POST avec la regle proposee")
    s.attend(cdp, "!document.querySelector('#rep-bandeaux [data-applique]')", 5)
    cdp.js("window.fetch = window._f2; true")

    # mode sombre : le panneau suit le theme (variables de la page, aucune couleur figee)
    cdp.js("document.documentElement.setAttribute('data-theme', 'clair')")
    clair = cdp.js("getComputedStyle(document.querySelector('#rep-corps .rep-regle')).backgroundColor")
    cdp.js("document.documentElement.setAttribute('data-theme', 'sombre')")
    sombre = cdp.js("getComputedStyle(document.querySelector('#rep-corps .rep-regle')).backgroundColor")
    s.verifie((clair, sombre), ("rgb(255, 255, 255)", "rgb(29, 32, 37)"), "mode sombre : fond des regles suit le theme")
    cdp.js("document.documentElement.setAttribute('data-theme', 'clair')")

    # suppression : regle locale retiree du fichier, regle de base intacte
    cdp.js("document.querySelector('#rep-corps button[data-supprime=panne_sonde]').click()")
    s.attend(cdp, "document.querySelectorAll('#rep-corps .rep-regle').length === 1", 10)
    s.verifie(([r["id"] for r in cdp.js(REGLES)], [d["id"] for d in json.loads(local.read_text(encoding="utf-8")).get("regles", [])]),
              (["verrou_fichier"], []), "suppression : regle locale retiree de la page et du fichier, base gardee")
    # connexions refusees pendant la charge (serveur vivant, file d'attente d'ecoute pleine au rechargement sous pio) : tolerees,
    # la page les rattrape (appel() ne leve jamais, le flux se reconnecte) ; toute autre erreur reste un echec
    s.verifie([e for e in cdp.erreurs() if "ERR_CONNECTION_REFUSED" not in e], [], "aucune erreur JS")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome des reparations de la page Build.")
    options.add_argument("--capture", help="dossier ou ecrire les captures PNG")
    args = options.parse_args()
    m = None
    try:
        m = s.Montage()
        m.demarre(False)
        sonde(m, args.capture)
    except FileNotFoundError as erreur:
        print(f"BLOQUE : {erreur}")
        return 3
    except Exception as erreur:                              # noqa: BLE001
        s.verifie(repr(erreur), "pas d'exception de la sonde", "sonde : deroulement")
    finally:
        if m:
            m.ferme()
    print("\n" + ("VERT" if not s.ECHECS else f"ROUGE : {len(s.ECHECS)} echec(s) : {s.ECHECS}"))
    return 1 if s.ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
