"""Sonde Chrome de la bascule « Classer par » Famille / Lieu / Puce de la page Build (build_page_lieux.py, modele D).

UTILISATION (a la main, hors de tout build : aucun pio n'est lance, Chrome tourne ~30 s)
    python outils_docs/scripts_python/outils_pc/test_build_page_lieux_chrome.py [--sans-temoin] [--capture DOSSIER]
Code de sortie 0 = vert : la vraie page passe toutes les verifications ET le temoin (la meme page sans le JS de
build_page_lieux, remplace par des branchements vides) echoue sur la premiere verification.

Montage repris de test_build_page_chrome.py (import du module voisin) : build_web.py dans un processus fils,
BUILD_WEB_PIO = build_faux_pio.py (le vrai pio n'est JAMAIS lance, garde de t.mode_serveur), depot d'essai
temporaire, ports COM neutralises. Le depot porte une carte par lieu de la table, 4 au garage, une ESP8266
(tasmota-pompe-piscine, exception rangee en Exterieur) et une carte hors table (tasmota32s3-jardin-essai).
Spec : docs/superpowers/specs/2026-11-10-classement-par-lieu-design.md §5.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import test_build_page_chrome as t

ICI = Path(__file__).resolve().parent
BASE = "tasmota32-sonde-base"
ETAGE2, RDC, CAVE = "tasmota32s3-etage2-grenier", "tasmota32-rdc-vr-porte", "tasmota32s3-cave-serveur-rly"
P4, G_S3, CUVE, RIDEAU = ("tasmota32p4-garage-serveur-modbus", "tasmota32s3-garage-serveur-modbus",
                          "tasmota32s3-garage-capteurs-cuve-modbus", "tasmota32s3-garage-rideau-garage-modbus")
BUREAU, PISCINE, JARDIN = "tasmota32-bureau-interrupteur-energie", "tasmota-pompe-piscine", "tasmota32s3-jardin-essai"
GARAGE = [P4, G_S3, CUVE, RIDEAU]
CARTES = [ETAGE2, RDC, CAVE] + GARAGE + [BUREAU, PISCINE, JARDIN]
CENV = f"""\
[env:{BASE}]
extra_scripts           = pre:outils_docs/scripts_python/build/pre_utilitaires_platformio.py
custom_files_upload     = no_files
""" + "".join(f"\n[env:{c}]\nextends                 = env:{BASE}\n" for c in CARTES if c != PISCINE) + f"""
[env:{PISCINE}]
build_flags             = -DFIRMWARE_POMPE_PISCINE
"""
LIEUX = ["2e étage", "Rez-de-chaussée", "Cave", "Garage", "Bureau", "Extérieur", "jardin"]
BOUCHON = ("function lieuxGroupes() { return false; }\nfunction lieuxMaj() {}\n"         # temoin : branchements vides
           "function lieuxOuverts() { return {}; }\nfunction lieuxRestaure() {}\n")
verifie = t.verifie

JS_GROUPES = """(() => [...document.querySelectorAll('#liste > details')].filter(d => !d.hidden).map(d => {
  const s = d.querySelector('summary');
  return {nom: 'groupe' in d.dataset ? s.children[1].textContent : s.firstChild.textContent, ouvert: d.open,
          groupe: 'groupe' in d.dataset};
}))()"""


class MontageLieux(t.Montage):
    def __init__(self, sans_lieux):
        super().__init__()
        self.sans_lieux = sans_lieux

    def lance_serveur(self):          # ce script en mode --serveur, pour pouvoir retirer le JS de build_page_lieux
        self.commande = ([sys.executable, "-u", str(Path(__file__).resolve()), "--serveur", str(self.port), str(self.depot)]
                         + (["--sans-lieux"] if self.sans_lieux else []))
        super().lance_serveur()


def mode_serveur(port, depot, sans_lieux):
    sys.path.insert(0, str(ICI))
    import build_page
    import build_page_lieux
    if sans_lieux:
        assert build_page.PAGE.count(build_page_lieux.JS) == 1, "JS de build_page_lieux introuvable dans la page"
        build_page.PAGE = build_page.PAGE.replace(build_page_lieux.JS, BOUCHON)
    return t.mode_serveur(port, depot, False)


def ouvre(m):
    m.ouvre()
    t.attend(m.cdp, "document.querySelectorAll('#liste .env').length", 15)     # Chrome froid : /envs plus lent


def groupes(cdp):
    g = cdp.js(JS_GROUPES)
    return g if isinstance(g, list) else []


def bascule(cdp, classement):
    cdp.js(f"document.querySelector('.l-barre button[data-classement={classement}]')?.click()")
    time.sleep(0.2)


def coches(cdp, noms):
    return cdp.js(f"{json.dumps(noms)}.map(n => document.getElementById('env-' + n).checked)")


def clic_reel(cdp, selecteur):
    """Vrai clic souris (Input.dispatchMouseEvent) au centre de l'element : le comportement du summary est le vrai."""
    r = cdp.js(f"""(() => {{ const e = document.querySelector({json.dumps(selecteur)}); e.scrollIntoView({{block: 'center'}});
      const b = e.getBoundingClientRect(); return [b.x + b.width / 2, b.y + b.height / 2]; }})()""")
    for genre in ("mousePressed", "mouseReleased"):
        cdp.appel("Input.dispatchMouseEvent", type=genre, x=r[0], y=r[1], button="left", clickCount=1)
    time.sleep(0.2)


def filtre(cdp, texte):
    r = cdp.js(f"(() => {{ const f = document.querySelector('.l-filtre'); f.value = {json.dumps(texte)};"
               f" f.dispatchEvent(new Event('input')); return f.value; }})()")
    assert r == texte, f"filtre non pose : {r!r}"


def premiere_verification(cdp):
    """Bascule sur Lieu : groupes de cartes dans l'ordre de la table, « jardin » en dernier, puis bases et amont."""
    for nom in (ETAGE2, P4, CUVE, RIDEAU):
        t.coche(cdp, f"#env-{nom}")
    bascule(cdp, "lieu")
    return [g["nom"] for g in groupes(cdp)], LIEUX + ["Mes bases", "Tasmota (amont)"]


def sonde(m, capture):
    cdp = m.cdp
    ouvre(m)
    obtenu, attendu = premiere_verification(cdp)
    verifie(obtenu, attendu, "Lieu : 7 groupes de cartes (table puis « jardin »), puis Mes bases, puis amont")
    verifie([g["ouvert"] for g in groupes(cdp)], [True, False, False, True, False, False, False, True, False],
            "Lieu : groupe ouvert s'il contient un coche, ferme sinon ; bases ouvertes, amont sans coche ferme")
    verifie(cdp.js("document.querySelector('.l-barre button[data-classement=lieu]').getAttribute('aria-pressed')"), "true",
            "Lieu : bouton enfonce")

    case = "details[data-groupe=garage] .l-case"
    etat = lambda: cdp.js(f"""(() => {{ const c = document.querySelector('{case}');
      return [c.checked, c.indeterminate, document.querySelector('details[data-groupe=garage]').open,
              document.querySelector('details[data-groupe=garage] .compte').textContent]; }})()""")
    verifie(etat(), [False, True, True, "(4 · 3 cochés)"], "garage 3 coches sur 4 : case a moitie (indeterminate), compteur")
    if capture:
        dossier = Path(capture)
        dossier.mkdir(parents=True, exist_ok=True)
        cdp.js("document.querySelector('details[data-groupe=bureau]').open = true")
        for theme in ("clair", "sombre"):
            cdp.js(f"document.documentElement.setAttribute('data-theme', '{theme}')")
            time.sleep(0.3)
            cdp.capture(dossier / f"build-lieux-{theme}.png")
        cdp.js("document.documentElement.setAttribute('data-theme', 'clair'); "
               "document.querySelector('details[data-groupe=bureau]').open = false")
    clic_reel(cdp, case)
    verifie((coches(cdp, GARAGE), etat()), ([True] * 4, [True, False, True, "(4 · 4 cochés)"]),
            "clic sur la case du garage : les 4 cochees, le groupe reste ouvert")

    bascule(cdp, "puce")
    verifie([g["nom"] for g in groupes(cdp) if g["groupe"]], ["ESP32", "ESP32-S3", "ESP32-P4", "ESP8266"],
            "Puce : ESP32, ESP32-S3, ESP32-P4, ESP8266, sans groupe vide")
    bascule(cdp, "lieu")

    clic_reel(cdp, case)                          # garage tout decoche
    t.coche(cdp, f"#env-{BUREAU}")
    cdp.js("document.querySelector('details[data-groupe=garage]').open = false")      # replie a la main avant le filtre
    filtre(cdp, "cuve")
    verifie(cdp.js(f"""[document.querySelector('details[data-groupe=garage]').open,
      document.querySelector('.env[data-env="{CUVE}"]').getBoundingClientRect().height > 0]"""), [True, True],
            "filtre « cuve » en Lieu : groupe Garage ouvert, ligne de la cuve a l'ecran")
    verifie([g["nom"] for g in groupes(cdp)], ["Garage"], "filtre « cuve » : seul le groupe du garage reste visible")
    verifie(cdp.js(f"[...document.querySelectorAll('details[data-groupe=garage] .env')].map(l => !l.hidden)"),
            [False, False, True, False], "filtre « cuve » : seule la ligne de la cuve visible")
    clic_reel(cdp, case)
    verifie(coches(cdp, GARAGE), [False, False, True, False], "filtre « cuve » + clic sur la case du garage : seule la cuve change")

    # vigilance 1 : envs coches masques par le filtre (2e etage, bureau) -> avertissement, et ils partent au lancement
    verifie(cdp.js("(() => { const a = document.querySelector('.l-masques'); return a.hidden ? null : a.textContent; })()"),
            "2 envs cochés masqués par le filtre partiront au lancement", "avertissement orange : 2 envs coches masques")
    verifie(cdp.js("getComputedStyle(document.querySelector('.l-masques')).color === "
                   "getComputedStyle(document.documentElement).getPropertyValue('--orange').trim().replace(/^#(..)(..)(..)$/, "
                   "(x, r, g, b) => `rgb(${parseInt(r, 16)}, ${parseInt(g, 16)}, ${parseInt(b, 16)})`)"), True,
            "avertissement : couleur --orange")
    t.coche(cdp, 'input[name=action][value="compiler"]')
    cdp.js("""window.__lancer = null; window.__fetch = window.fetch;
      window.fetch = (u, o) => { if (u === '/lancer') { window.__lancer = JSON.parse(o.body);
        return Promise.resolve(new Response('sonde : lancement intercepte', {status: 409})); } return window.__fetch(u, o); };""")
    cdp.js("document.getElementById('lancer').click()")
    corps = t.attend(cdp, "window.__lancer", 5, 0.1) or {}
    verifie(([l["env"] for l in corps.get("lignes", [])], corps.get("actions")), ([ETAGE2, CUVE, BUREAU], ["compiler"]),
            "POST /lancer intercepte : les envs coches masques par le filtre y sont, ordre de la liste")
    cdp.js("window.fetch = window.__fetch; document.getElementById('refus').textContent = ''")
    t.coche(cdp, 'input[name=action][value="compiler"]', False)
    filtre(cdp, "")
    verifie(cdp.js("document.querySelector('.l-masques').hidden"), True, "filtre vide : avertissement retire")
    verifie(cdp.js("document.querySelector('details[data-groupe=garage]').open"), False,
            "filtre vide : ouverture d'avant le filtre rendue (Garage replie)")

    # vigilance 2 : IP saisie, Famille -> Lieu -> Famille, IP intacte
    cdp.js(f"""(() => {{ const l = document.querySelector('.env[data-env="{CAVE}"]');
      l.querySelector('.methode button:nth-child(2)').click();
      const c = document.querySelector('.env[data-env="{CAVE}"] .champ'); c.value = '192.168.0.77';
      c.dispatchEvent(new Event('input')); c.dispatchEvent(new Event('change')); }})()""")
    for classement in ("famille", "lieu", "famille"):
        bascule(cdp, classement)
    verifie(cdp.js(f"""(() => {{ const l = document.querySelector('.env[data-env="{CAVE}"]');
      return [l.querySelector('.champ').value, l.querySelector('.methode button:nth-child(2)').getAttribute('aria-pressed')]; }})()"""),
            ["192.168.0.77", "true"], "IP saisie puis Famille -> Lieu -> Famille : IP et OTA intactes")
    filtre(cdp, "SONDE-BASE")                     # Famille aussi, sans casse : seule la famille des bases reste
    verifie([g["nom"] for g in groupes(cdp)], ["Mes bases"], "Famille + filtre « SONDE-BASE » : seule « Mes bases » visible")
    filtre(cdp, "")

    # amont et un sous-groupe ouverts a la main en Famille : la bascule Lieu les garde
    cdp.js("document.querySelector('details[data-famille=amont]').open = true; "
           "document.querySelector('details[data-sous-groupe=esp32]').open = true")
    bascule(cdp, "lieu")
    verifie(cdp.js("[document.querySelector('details[data-famille=amont]').open, "
                   "document.querySelector('details[data-sous-groupe=esp32]').open]"), [True, True],
            "amont et sous-groupe ESP32 ouverts a la main, bascule Lieu : toujours ouverts")

    # vigilance 5 : rechargement par chargeEnvs(true) en Lieu -> toujours Lieu, ouverture gardee
    cdp.js("document.querySelector('details[data-groupe=rdc]').open = true")
    cdp.js("chargeEnvs(true)")
    verifie((cdp.js("document.querySelector('.l-barre button[data-classement=lieu]').getAttribute('aria-pressed')"),
             [g["ouvert"] for g in groupes(cdp)][:4]), ("true", [True, True, False, True]),
            "chargeEnvs(true) en Lieu : toujours Lieu, Rez-de-chaussee ouvert a la main reste ouvert")

    ouvre(m)
    verifie([g["nom"] for g in groupes(cdp)][:len(LIEUX)], LIEUX, "page rechargee : toujours en Lieu (localStorage)")

    # largeur telephone : la barre passe a la ligne, pas de defilement horizontal
    cdp.appel("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=True)
    time.sleep(0.5)
    large = cdp.js("document.documentElement.scrollWidth")
    verifie(large <= 390, True, f"telephone : pas de defilement horizontal ({large} px)")
    cdp.appel("Emulation.clearDeviceMetricsOverride")

    verifie(cdp.erreurs(), [], "aucune erreur JS jusqu'ici")
    # vigilance 3 : localStorage.getItem qui leve -> page en Famille, sans erreur
    script = cdp.appel("Page.addScriptToEvaluateOnNewDocument",
                       source="Storage.prototype.getItem = function () { throw new Error('sonde : localStorage bloque'); };")
    ouvre(m)
    verifie(([g["nom"] for g in groupes(cdp)],
             cdp.js("document.querySelector('.l-barre button[data-classement=famille]').getAttribute('aria-pressed')")),
            (["Mes cartes", "Mes bases", "Tasmota (amont)"], "true"), "localStorage.getItem qui leve : page en Famille")
    verifie(cdp.erreurs(), [], "localStorage.getItem qui leve : aucune exception en console")
    cdp.appel("Page.removeScriptToEvaluateOnNewDocument", identifier=script["identifier"])


def sonde_temoin(m):
    ouvre(m)
    obtenu, attendu = premiere_verification(m.cdp)
    print(f"     temoin : obtenu {obtenu!r}", flush=True)
    print("     erreurs vues sur le temoin : " + (" | ".join(m.cdp.erreurs()) or "aucune"), flush=True)
    verifie(obtenu != attendu, True, "temoin : sans le JS de build_page_lieux, la premiere verification echoue")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome du classement Famille / Lieu / Puce de la page Build.")
    options.add_argument("--sans-temoin", action="store_true", help="ne pas rejouer la page sans le JS de build_page_lieux")
    options.add_argument("--capture", help="dossier ou ecrire les captures PNG (Lieu, clair et sombre)")
    options.add_argument("--serveur", nargs=2, metavar=("PORT", "DEPOT"), help=argparse.SUPPRESS)
    options.add_argument("--sans-lieux", action="store_true", help=argparse.SUPPRESS)
    args = options.parse_args()
    if args.serveur:
        return mode_serveur(int(args.serveur[0]), args.serveur[1], args.sans_lieux)

    t.CENV = CENV                     # lu par t.Montage.demarre au moment de l'appel
    for temoin in ([False] if args.sans_temoin else [False, True]):
        print(f"\n=== {'TEMOIN (sans le JS de build_page_lieux)' if temoin else 'page reelle'} ===", flush=True)
        m = None
        try:
            m = MontageLieux(temoin)
            m.demarre(False)
            sonde_temoin(m) if temoin else sonde(m, args.capture)
        except FileNotFoundError as erreur:
            print(f"BLOQUE : {erreur}")
            return 3
        except Exception as erreur:
            verifie(repr(erreur), "pas d'exception de la sonde", "sonde : deroulement")
        finally:
            if m:
                m.ferme()
    print("\n" + ("VERT" if not t.ECHECS else f"ROUGE : {len(t.ECHECS)} echec(s) : {t.ECHECS}"))
    return 1 if t.ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
