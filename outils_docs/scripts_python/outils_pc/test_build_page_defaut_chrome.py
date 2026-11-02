"""Sonde Chrome de l'onglet « Envs par défaut » de la page Build et televersement (build_page_defaut.py).

UTILISATION (a la main ; Python de PlatformIO)
    python outils_docs/scripts_python/outils_pc/test_build_page_defaut_chrome.py [--capture DOSSIER]
Code de sortie 0 = vert.

Montage de test_build_page_chrome.py (vrai build_web.py dans un processus fils, faux pio, depot d'essai TEMPORAIRE :
le vrai depot n'est jamais ecrit) + un platformio_override.ini d'essai. Aucun lancement, aucun envoi.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import test_build_page_chrome as s

A, B, C, BASE = s.A, s.B, s.C, s.BASE
OVERRIDE = ("[platformio]\ndata_dir = data/sonde/tasmota32-a\n\ndefault_envs =\n; *** Safeboot\n    ; tasmota32-safeboot\n"
            f"; *** ESP32\n    {A}\n    ; {B}\n\n[tasmota]\n;build_flags =\n")
ETAT = """(() => { const t = id => document.getElementById(id);
  return {defaut: t('vue-defaut').hidden, build: t('vue-build').hidden, selection: t('onglet-defaut').getAttribute('aria-selected'),
          titres: [...document.querySelectorAll('.d-groupe .titre')].map(x => x.firstChild.textContent),
          comptes: [...document.querySelectorAll('.d-groupe .compte')].map(x => x.textContent),
          coches: [...document.querySelectorAll('#d-colonnes input:checked')].map(c => c.dataset.env),
          absents: [...document.querySelectorAll('.d-env')].filter(l => l.querySelector('.d-marque')).map(l => l.querySelector('.nom').textContent),
          total: t('d-total').textContent, resume: t('d-resume').textContent, messages: t('d-messages').textContent,
          enregistrer_off: t('d-enregistrer').disabled, lignes: document.querySelectorAll('#d-apercu .d-l').length,
          modif: [...document.querySelectorAll('#d-apercu .d-l.modif')].map(l => l.lastChild.textContent.trim()),
          ajout: [...document.querySelectorAll('#d-apercu .d-l.ajout')].map(l => l.lastChild.textContent.trim()),
          visible: t('d-apercu').scrollHeight > 0}; })()"""
COCHES_BUILD = "[...document.querySelectorAll('.env')].filter(l => l.querySelector('input[type=checkbox]').checked).map(l => l.querySelector('.nom').firstChild.textContent)"


def clic(cdp, selecteur):
    return cdp.js(f"(() => {{ const e = document.querySelector({json.dumps(selecteur)}); if (!e) return 'absent'; e.click(); return true; }})()")


def case(cdp, env):
    s.verifie(clic(cdp, f"#d-colonnes input[data-env='{env}']"), True, f"case de {env} presente")


def etat(cdp):
    time.sleep(0.2)
    return cdp.js(ETAT)


def sonde(m, capture):
    cdp, fichier = m.cdp, m.depot / "platformio_override.ini"
    fichier.write_text(OVERRIDE, encoding="utf-8", newline="")
    m.ouvre()
    clic(cdp, f"#liste .env input[type=checkbox]")          # selection de l'onglet Build, a remplacer par le report
    clic(cdp, "#onglet-aide")
    s.verifie(cdp.js("(() => { const v = document.getElementById('vue-aide'); return [v.hidden, document.getElementById('vue-build').hidden, v.textContent.includes('.drvset003')]; })()"), [False, True, True], "onglet Aide : affiche, Build masque")
    clic(cdp, "#onglet-defaut")
    s.attend(cdp, "document.querySelectorAll('#d-colonnes input').length > 0", 10)
    s.attend(cdp, "document.querySelectorAll('#d-apercu .d-l').length > 0", 10)
    e = etat(cdp)
    s.verifie((e["defaut"], e["build"], e["selection"]), (False, True, "true"), "onglet : vue affichee, Build masque")
    s.verifie(e["titres"], ["Safeboot", "ESP32", "ESP32-S3"], "colonnes par puce")
    s.verifie((e["coches"], e["total"]), ([A], "1"), "etat lu : seul A actif, total 1")
    s.verifie(sorted(e["absents"]), sorted([C, BASE]), "absents du bloc signales : carte et base")
    s.verifie((e["enregistrer_off"], "aucune modification" in e["resume"], e["lignes"]), (True, True, OVERRIDE.count("\n")),
              "apercu : fichier entier, rien a enregistrer")

    case(cdp, B)
    s.attend(cdp, "document.querySelectorAll('#d-apercu .d-l.modif').length === 1", 10)
    e = etat(cdp)
    s.verifie((e["modif"], e["total"], e["enregistrer_off"]), ([B], "2", False), "case B : ligne surlignee, total 2, Enregistrer actif")
    s.verifie(".pio/build" in e["messages"], True, "purge annoncee avant d'enregistrer")
    s.verifie(fichier.read_text(encoding="utf-8"), OVERRIDE, "apercu : fichier non ecrit")

    case(cdp, C)
    s.attend(cdp, "document.querySelectorAll('#d-apercu .d-l.ajout').length === 1", 10)
    e = etat(cdp)
    s.verifie((e["ajout"], e["lignes"]), ([C], OVERRIDE.count("\n") + 1), "absent coche : ajoute a l'apercu")
    if capture:
        cdp.capture(Path(capture) / "build-defaut.png")

    for env in (A, B, C):
        case(cdp, env)
    s.attend(cdp, "document.getElementById('d-messages').textContent.includes('tous les envs')", 10)
    s.verifie(etat(cdp)["enregistrer_off"], True, "liste vide : refusee, Enregistrer grise")
    for env in (B, C):
        case(cdp, env)
    s.attend(cdp, "document.querySelectorAll('#d-apercu .d-l.ajout').length === 1", 10)
    s.attend(cdp, "!document.getElementById('d-enregistrer').disabled", 10)

    clic(cdp, "#d-enregistrer")
    s.attend(cdp, "document.getElementById('d-messages').textContent.includes('Enregistré')", 10)
    ecrit = fichier.read_text(encoding="utf-8")
    s.verifie((f"    ; {A}\n" in ecrit, f"    {B}\n" in ecrit, f"\n    {C}\n" in ecrit), (True, True, True), "enregistre : fichier conforme")
    e = etat(cdp)
    s.verifie((e["enregistrer_off"], e["modif"], sorted(e["coches"])), (True, [], sorted([B, C])), "apres enregistrement : relu, rien en attente")

    case(cdp, "tasmota32-safeboot")                         # famille amont repliee : le report doit l'ouvrir
    time.sleep(0.5)
    clic(cdp, "#d-reporter")
    s.attend(cdp, "!document.getElementById('vue-build').hidden", 5)
    s.verifie(sorted(cdp.js(COCHES_BUILD)), sorted([B, C, "tasmota32-safeboot"]), "report : selection du Build remplacee par la liste")
    s.verifie(cdp.js("(() => { const i = [...document.querySelectorAll('.env')].find(l => l.querySelector('.nom').firstChild.textContent === 'tasmota32-safeboot'); return i.offsetParent !== null; })()"),
              True, "report : env de la famille repliee visible")

    clic(cdp, "#onglet-defaut")
    s.attend(cdp, "!document.getElementById('vue-defaut').hidden", 5)
    s.attend(cdp, "document.querySelectorAll('#d-apercu .d-l.modif').length === 1", 10)
    s.verifie("tasmota32-safeboot" in etat(cdp)["coches"], True, "retour sur l'onglet : case non enregistree gardee")
    m.ouvre()
    s.attend(cdp, "document.querySelectorAll('#d-colonnes input').length > 0", 10)
    s.verifie(etat(cdp)["defaut"], False, "rechargement : l'onglet est rouvert")
    s.verifie(cdp.erreurs(), [], "aucune erreur JS")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de l'onglet Envs par défaut de la page build.")
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
