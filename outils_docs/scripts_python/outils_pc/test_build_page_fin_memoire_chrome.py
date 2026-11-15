"""Sonde Chrome de la pastille de fin de compilation (build_page_fin_memoire.py, plan build-fin-partitions).

UTILISATION (a la main ; Python de PlatformIO)
    python outils_docs/scripts_python/outils_pc/test_build_page_fin_memoire_chrome.py [--capture DOSSIER]
Code de sortie 0 = vert.

Montage de test_build_page_chrome.py (vrai build_web.py dans un processus fils, FAUX pio, depot et dossier de donnees
TEMPORAIRES). Les releves memoire sont des FICHIERS de test ecrits dans <donnees>/build/memoire/<env>.json (ce que la serie
enregistre a la fin d'une compilation), servis par le vrai GET /memoire?env= ; les evenements `fin_env` sont injectes dans la
page (aucune compilation, donc rien n'ecrase les releves). Aucune pause fixe hors rendu groupe : des conditions attendues.
"""

import argparse
import json
import sys
from pathlib import Path

import test_build_page_chrome as s

XSS = "<img src=x onerror=window.xss=1>"
A, B, C, SANS = s.A, s.B, s.C, s.BASE
Ko = 1024


def releve(env, app0, safeboot, fs, diram, nom_extra="coredump"):
    """Releve de test : app0 / safeboot / FS (octets utilises sur 1000 Ko, 800 Ko, 2000 Ko), DIRAM sur 400 Ko."""
    return {"env": env, "date": 1.0, "date_build": 1.0, "csv": "x.csv", "flash": 4 * 1024 * 1024, "notes": [], "journal": "",
            "partitions": [{"nom": "nvs", "type": "data", "sous_type": "nvs", "debut": 36864, "taille": 20 * Ko, "utilise": None, "estime": False},
                           {"nom": "safeboot", "type": "app", "sous_type": "factory", "debut": 65536, "taille": 800 * Ko, "utilise": safeboot, "estime": False},
                           {"nom": "app0", "type": "app", "sous_type": "ota_0", "debut": 900000, "taille": 1000 * Ko, "utilise": app0, "estime": False},
                           {"nom": nom_extra, "type": "data", "sous_type": "coredump", "debut": 2000000, "taille": 64 * Ko, "utilise": None, "estime": False},
                           {"nom": "spiffs", "type": "data", "sous_type": "spiffs", "debut": 3000000, "taille": 2000 * Ko, "utilise": fs, "estime": True}],
            "ram": [{"zone": "DIRAM", "utilise": diram, "total": 400 * Ko}, {"zone": "LP RAM", "utilise": 1 * Ko, "total": 16 * Ko}]}


PASTILLES = ("(() => Object.fromEntries([...document.querySelectorAll('.bloc')].map(b => [b.dataset.bloc,"
             " (p => p ? {texte: p.textContent, classe: p.className, couleur: getComputedStyle(p).color} : null)(b.querySelector('.fm-pastille'))])))()")
FENETRE = ("(() => { const f = document.querySelector('.fm-fenetre'); return !f ? null : {texte: f.textContent,"
           " partitions: [...f.querySelectorAll('.fm-ligne')].map(l => l.firstChild.textContent), alertes: [...f.querySelectorAll('.fm-alerte')].map(a => a.className + '|' + a.textContent),"
           " img: f.querySelectorAll('img').length, ruban: f.querySelectorAll('.fm-ruban span').length}; })()")


def sonde(m, capture):
    cdp = m.cdp
    dossier = m.t / "outils" / "build" / "memoire"
    dossier.mkdir(parents=True, exist_ok=True)
    for env, rel in ((A, releve(A, 500 * Ko, 400 * Ko, 100 * Ko, 130 * Ko, XSS)),            # tout vert
                     (B, releve(B, 920 * Ko, 400 * Ko, 100 * Ko, 130 * Ko)),                   # app0 92 % : orange
                     (C, releve(C, 500 * Ko, 780 * Ko, 100 * Ko, 130 * Ko))):                  # safeboot 97,6 % : rouge
        (dossier / f"{env}.json").write_text(json.dumps(rel), encoding="utf-8")
    m.ouvre()
    cdp.js("document.documentElement.setAttribute('data-theme', 'clair')")
    s.verifie(cdp.js("document.querySelectorAll('.fm-pastille').length"), 0, "avant tout build : aucune pastille")

    lignes = [{"env": e, "methode": "com", "port": "", "ip": ""} for e in (A, B, C, SANS)]
    evenements = [{"type": "debut", "env": None, "actions": ["compiler"], "lignes": lignes}]
    for e in (A, B, C, SANS):
        evenements.append({"type": "debut", "env": e, "actions": ["compiler"], "methode": "com", "port": ""})
        evenements.append({"type": "fin_env", "env": e, "resultat": "succes", "statuts": {"compiler": "succes"}, "secondes": 3})
    s.injecte(cdp, evenements)
    s.attend(cdp, "document.querySelectorAll('.fm-pastille').length === 3", 10)
    p = cdp.js(PASTILLES)
    s.verifie([p[A]["texte"], p[B]["texte"], p[C]["texte"]], ["Flash 50 % · RAM 33 %", "Flash 92 % · RAM 33 % ⚠", "Flash 50 % · RAM 33 % ⚠"],
              "serie : une pastille par env reussi, Flash = app0, RAM")
    s.verifie((p[SANS], [p[A]["classe"], p[B]["classe"], p[C]["classe"]]),
              (None, ["fm-pastille ", "fm-pastille o", "fm-pastille r"]), "env sans releve : pas de pastille ; vert, orange (90 %), rouge (95 %)")
    s.verifie([p[A]["couleur"], p[B]["couleur"], p[C]["couleur"]], ["rgb(42, 157, 74)", "rgb(194, 116, 0)", "rgb(192, 57, 43)"],
              "couleurs : variables --vert, --orange, --rouge de la page")

    # seuils : 89 % vert, 90 % orange, 94 % orange, 95 % rouge (partition la plus pleine)
    cas = {}
    for pc in (89, 90, 94, 95):
        env = f"seuil-{pc}"
        (dossier / f"{env}.json").write_text(json.dumps(releve(env, pc * 10 * Ko, 100 * Ko, 100 * Ko, 100 * Ko)), encoding="utf-8")
        s.injecte(cdp, [{"type": "debut", "env": None, "actions": ["compiler"], "lignes": [{"env": env, "methode": "com", "port": "", "ip": ""}]},
                        {"type": "debut", "env": env, "actions": ["compiler"], "methode": "com", "port": ""},
                        {"type": "fin_env", "env": env, "resultat": "succes", "statuts": {"compiler": "succes"}, "secondes": 1}])
        s.attend(cdp, f"document.querySelector('.bloc[data-bloc=\"{env}\"] .fm-pastille')", 10)
        cas[pc] = cdp.js(PASTILLES)[env]["classe"].split()[-1]
    s.verifie(cas, {89: "fm-pastille", 90: "o", 94: "o", 95: "r"}, "seuils : orange des 90 %, rouge des 95 %")
    # ESP32-S3 : IRAM 16384/16384 = cache d'instructions, jamais une alerte ; Flash = app0 ; FS exclu du niveau. ESP32 classique : IRAM pleine = rouge
    def serie_env(env):
        s.injecte(cdp, [{"type": "debut", "env": None, "actions": ["compiler"], "lignes": [{"env": env, "methode": "com", "port": "", "ip": ""}]},
                        {"type": "debut", "env": env, "actions": ["compiler"], "methode": "com", "port": ""},
                        {"type": "fin_env", "env": env, "resultat": "succes", "statuts": {"compiler": "succes"}, "secondes": 1}])
        s.attend(cdp, f"document.querySelector('.bloc[data-bloc=\"{env}\"] .fm-pastille')", 10)
        return cdp.js(PASTILLES)[env]
    for env, iram in (("s3-iram", 16384), ("classique-iram", 172032)):
        rel = releve(env, 870 * Ko, 747 * Ko + 205, 14 * Ko, 160 * Ko)
        rel["ram"].append({"zone": "IRAM", "utilise": iram, "total": iram if iram != 16384 else 16384})
        (dossier / f"{env}.json").write_text(json.dumps(rel), encoding="utf-8")
    p3 = serie_env("s3-iram")
    s.verifie((p3["texte"], p3["classe"].split()[-1]), ("Flash 87 % · RAM 40 % ⚠", "o"), "S3 : IRAM 16384/16384 ignoree, Flash = app0, safeboot 93,4 % = orange (pas rouge)")
    cdp.js("document.querySelector('.bloc[data-bloc=\"s3-iram\"] .fm-pastille').click()")
    s.attend(cdp, "document.querySelector('.fm-fenetre')", 5)
    f = cdp.js(FENETRE)
    s.verifie(("IRAM" in " ".join(f["partitions"]), any("IRAM" in a for a in f["alertes"]), any("safeboot" in a for a in f["alertes"]), True),
              (True, False, True, True), "S3 : ligne IRAM affichee, aucune alerte IRAM, alerte safeboot gardee")
    s.verifie(cdp.js("document.querySelector('.fm-fenetre .fm-ligne[title*=\"cache\"]') !== null"), True, "S3 : mention « cache d'instructions » sur la ligne IRAM")
    cdp.js("document.querySelector('.fm-voile').click()")
    s.attend(cdp, "!document.querySelector('.fm-fenetre')", 5)
    pc = serie_env("classique-iram")
    s.verifie(pc["classe"].split()[-1], "r", "ESP32 classique : IRAM reellement pleine = rouge")
    # ESP8266 : releve sans partitions, bilan de pio (bilan_flash + RAM) ; releve vide : pas de pastille
    base8266 = {"date": 1.0, "date_build": 1.0, "csv": "", "flash": None, "notes": [], "journal": "", "partitions": []}
    r8 = {}
    for env, bilan, ram in (("e8266-vert", (718867, 1023984), (43800, 81920)), ("e8266-orange", (940 * Ko, 1000 * Ko), (43800, 81920)),
                            ("e8266-rouge", (718867, 1023984), (78000, 81920)), ("e8266-vide", None, None)):
        rel = dict(base8266, env=env, ram=[{"zone": "RAM", "utilise": ram[0], "total": ram[1]}] if ram else [])
        if bilan:
            rel["bilan_flash"] = {"utilise": bilan[0], "taille": bilan[1]}
        (dossier / f"{env}.json").write_text(json.dumps(rel), encoding="utf-8")
        s.injecte(cdp, [{"type": "debut", "env": None, "actions": ["compiler"], "lignes": [{"env": env, "methode": "com", "port": "", "ip": ""}]},
                        {"type": "debut", "env": env, "actions": ["compiler"], "methode": "com", "port": ""},
                        {"type": "fin_env", "env": env, "resultat": "succes", "statuts": {"compiler": "succes"}, "secondes": 1}])
        if bilan:
            s.attend(cdp, f"document.querySelector('.bloc[data-bloc=\"{env}\"] .fm-pastille')", 10)
        else:
            s.attend(cdp, f"document.querySelector('.bloc[data-bloc=\"{env}\"]')", 10)
        r8[env] = cdp.js(PASTILLES)[env]
        if env == "e8266-vert":
            cdp.js("document.querySelector('.bloc[data-bloc=\"e8266-vert\"] .fm-pastille').click()")
            s.attend(cdp, "document.querySelector('.fm-fenetre')", 5)
            f = cdp.js(FENETRE)
            s.verifie((f["partitions"], f["ruban"]), (["firmware", "RAM"], 1), "ESP8266 : fenetre avec firmware et RAM, un seul bloc de ruban")
            cdp.js("document.querySelector('.fm-voile').click()")
            s.attend(cdp, "!document.querySelector('.fm-fenetre')", 5)
    s.verifie({e: (p and [p["texte"], p["classe"].split()[-1]]) for e, p in r8.items()},
              {"e8266-vert": ["Flash 70 % · RAM 53 %", "fm-pastille"], "e8266-orange": ["Flash 94 % · RAM 53 % ⚠", "o"],
               "e8266-rouge": ["Flash 70 % · RAM 95 % ⚠", "r"], "e8266-vide": None},
              "ESP8266 sans partitions : pastille d'apres le bilan de pio, seuils, releve vide sans pastille")
    # retour a la serie de A, B, C
    s.injecte(cdp, evenements)
    s.attend(cdp, "document.querySelectorAll('.fm-pastille').length === 3", 10)

    # clic -> fenetre : alertes, ruban, une ligne par partition et par zone de RAM
    cdp.js(f"document.querySelector('.bloc[data-bloc=\"{B}\"] .fm-pastille').click()")
    s.attend(cdp, "document.querySelector('.fm-fenetre')", 5)
    f = cdp.js(FENETRE)
    s.verifie((f["partitions"], f["ruban"], len(f["alertes"]), f["alertes"][0].startswith("fm-alerte |") or "fm-alerte o|" in f["alertes"][0],
               "app0 occupée à 92,0 %" in f["alertes"][0], B in f["texte"]),
              (["nvs", "safeboot", "app0", "coredump", "spiffs", "DIRAM", "LP RAM"], 5, 1, True, True, True),
              "clic : fenetre avec partitions, RAM, ruban et l'alerte de la partition pleine")
    s.verifie("non mesurable" in f["texte"], True, "fenetre : nvs et coredump « non mesurable »")
    if capture:
        cdp.capture(Path(capture) / "build-fin-partitions.png")
    cdp.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}))")
    s.attend(cdp, "!document.querySelector('.fm-fenetre')", 5)
    s.verifie(cdp.js(FENETRE), None, "Echap ferme la fenetre")
    cdp.js(f"document.querySelector('.bloc[data-bloc=\"{B}\"] .fm-pastille').click()")
    s.attend(cdp, "document.querySelector('.fm-fenetre')", 5)
    cdp.js("document.querySelector('.fm-voile').click()")                      # clic sur le voile (hors de la fenetre)
    s.attend(cdp, "!document.querySelector('.fm-fenetre')", 5)
    s.verifie(cdp.js(FENETRE), None, "clic dehors ferme la fenetre")
    cdp.js(f"document.querySelector('.bloc[data-bloc=\"{B}\"] .fm-pastille').click()")
    s.attend(cdp, "document.querySelector('.fm-fenetre')", 5)
    cdp.js("document.querySelector('.fm-fenetre').click()")                    # clic DANS la fenetre : reste ouverte
    s.verifie(cdp.js("!!document.querySelector('.fm-fenetre')"), True, "clic dans la fenetre : reste ouverte")
    cdp.js("[...document.querySelectorAll('.fm-pied button')].find(b => b.textContent === 'Fermer').click()")
    s.attend(cdp, "!document.querySelector('.fm-fenetre')", 5)

    # XSS : nom de partition venu du serveur
    cdp.js(f"document.querySelector('.bloc[data-bloc=\"{A}\"] .fm-pastille').click()")
    s.attend(cdp, "document.querySelector('.fm-fenetre')", 5)
    f = cdp.js(FENETRE)
    s.verifie((XSS in f["texte"], f["img"], cdp.js("window.xss === undefined")), (True, 0, True), "XSS : nom de partition affiche en texte, jamais en HTML")
    # un Echap seul ne doit plus rien faire une fois la fenetre fermee, et ne laisse pas d'ecouteur
    cdp.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}))")
    s.attend(cdp, "!document.querySelector('.fm-fenetre')", 5)

    # themes : la fenetre suit les variables de la page
    couleurs = []
    for theme in ("clair", "sombre"):
        cdp.js(f"document.documentElement.setAttribute('data-theme', '{theme}')")
        cdp.js(f"document.querySelector('.bloc[data-bloc=\"{B}\"] .fm-pastille').click()")
        s.attend(cdp, "document.querySelector('.fm-fenetre')", 5)
        couleurs.append(cdp.js("getComputedStyle(document.querySelector('.fm-fenetre')).backgroundColor"))
        if capture and theme == "sombre":
            cdp.capture(Path(capture) / "build-fin-partitions-sombre.png")
        cdp.js("document.querySelector('.fm-voile').click()")
        s.attend(cdp, "!document.querySelector('.fm-fenetre')", 5)
    s.verifie(couleurs, ["rgb(255, 255, 255)", "rgb(29, 32, 37)"], "themes clair et sombre : fond de la fenetre = --carte")
    cdp.js("document.documentElement.setAttribute('data-theme', 'clair')")

    # echec de compilation ou resultat sans compilation : pas de pastille meme avec un releve ancien
    s.injecte(cdp, [{"type": "debut", "env": None, "actions": ["upload"], "lignes": [{"env": B, "methode": "com", "port": "", "ip": ""}]},
                    {"type": "debut", "env": B, "actions": ["upload"], "methode": "com", "port": ""},
                    {"type": "fin_env", "env": B, "resultat": "succes", "statuts": {"upload": "succes"}, "secondes": 1}])
    s.verifie(cdp.js(PASTILLES)[B], None, "sans compilation reussie dans l'env : pas de pastille (releve d'un ancien build)")
    s.verifie([e for e in cdp.erreurs() if "ERR_CONNECTION_REFUSED" not in e], [], "aucune erreur JS")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de la pastille de fin de compilation.")
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
        import traceback; traceback.print_exc()
        s.verifie(repr(erreur), "pas d'exception de la sonde", "sonde : deroulement")
    finally:
        if m:
            m.ferme()
    print("\n" + ("VERT" if not s.ECHECS else f"ROUGE : {len(s.ECHECS)} echec(s) : {s.ECHECS}"))
    return 1 if s.ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
