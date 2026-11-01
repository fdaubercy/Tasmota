"""Sonde Chrome de l'onglet « Mémoire et partitions » de la page Build et televersement (A8, build_page_memoire.py).

UTILISATION (a la main, hors de tout build ; Python de PlatformIO)
    python outils_docs/scripts_python/outils_pc/test_build_page_memoire_chrome.py [--capture DOSSIER]
Code de sortie 0 = vert.

Montage de test_build_page_chrome.py (vrai build_web.py dans un processus fils, faux pio, depot d'essai TEMPORAIRE :
le vrai depot n'est jamais ecrit) + une vraie table de partitions/, un journal de compilation reussie de l'env A
(extrait d'un vrai journal S3) et deux fichiers dans son littlefs_data. L'ecriture de la table va donc jusqu'au bout,
dans le depot d'essai, puis l'OTA de A doit etre refusee par POST /lancer.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import build_partitions as bp
import test_build_page_chrome as s
from test_build_memoire import JOURNAL_S3

A = s.A
DEPOT = Path(__file__).resolve().parents[3]
TABLE = "partitions/esp32_partition_app3904k_fs11584k.csv"
AUTRE = "partitions/esp32_partition_app3904k_fs11392k.csv"
ETAT = """(() => { const t = id => document.getElementById(id);
  return {build: t('vue-build').hidden, fichiers: t('vue-fichiers').hidden, memoire: t('vue-memoire').hidden,
          selection: t('onglet-memoire').getAttribute('aria-selected'), env: t('m-env').value,
          envs: [...t('m-env').options].map(o => o.value),
          zones: [...document.querySelectorAll('#m-zones .m-zone')].map(z => z.querySelector('.tete').textContent),
          noms: [...document.querySelectorAll('#m-zones .m-zone b')].map(b => b.textContent),
          lignes: [...document.querySelectorAll('#m-parts tr')].map(r => r.children[1].querySelector('b').textContent),
          roles: [...document.querySelectorAll('#m-parts tr')].map(r => !!r.children[1].querySelector('.m-role').textContent),
          interdites: [...document.querySelectorAll('#m-parts tr')].map(r => r.querySelector('input[type=checkbox]').disabled),
          adresses: [...document.querySelectorAll('#m-parts tr')].map(r => r.children[2].textContent),
          messages: [...document.querySelectorAll('#m-messages div')].map(d => d.className + ':' + d.textContent),
          diff: t('m-diff-texte').textContent, ecrire_off: t('m-ecrire').disabled, date: t('m-date').textContent}; })()"""


def clic(cdp, selecteur):
    return cdp.js(f"(() => {{ const e = document.querySelector({json.dumps(selecteur)}); if (!e) return 'absent'; e.click(); return true; }})()")


def etat(cdp):
    time.sleep(0.4)
    return cdp.js(ETAT)


def champ(cdp, partition, valeur):
    cdp.js(f"""(() => {{ const c = document.querySelector("[aria-label='Taille de {partition} en Ko']");
      c.value = {valeur}; c.dispatchEvent(new Event('change')); }})()""")


def prepare_depot(m):
    """Table, flash, journal et FS de l'env A : le serveur relit ces fichiers a chaque requete."""
    cenv = m.depot / "platformio_tasmota_cenv.ini"
    cenv.write_text(cenv.read_text(encoding="utf-8").replace(
        "custom_files_upload     = no_files\n",
        f"custom_files_upload     = no_files\nboard_build.partitions  = {TABLE}\nboard_upload.flash_size = 16MB\n", 1),
        encoding="utf-8")
    (m.depot / "partitions").mkdir()
    (m.depot / TABLE).write_bytes((DEPOT / TABLE).read_bytes())
    (m.depot / AUTRE).write_bytes((DEPOT / AUTRE).read_bytes())
    journaux = m.t / "outils" / "build" / "journaux"
    journaux.mkdir(parents=True, exist_ok=True)
    (journaux / f"20261101-064021-{A}-compiler.log").write_text(JOURNAL_S3, encoding="utf-8")
    fs = m.depot / ".pio" / "build" / A / "littlefs_data"
    fs.mkdir(parents=True)
    (fs / "_persist.json").write_bytes(b"x" * 5000)
    (fs / "autoexec.be").write_bytes(b"x" * 10)


def sonde_onglet(m, capture):
    cdp = m.cdp
    m.ouvre()
    clic(cdp, "#onglet-memoire")
    s.attend(cdp, "document.querySelectorAll('#m-parts tr').length === 5", 10)
    e = etat(cdp)
    s.verifie((e["build"], e["fichiers"], e["memoire"], e["selection"]), (True, True, False, "true"),
              "onglet : clic -> vue Mémoire seule")
    s.verifie((e["env"], "tasmota32" in e["envs"]), (A, False), "env : A par defaut (premier env), pas d'env amont")
    s.verifie(e["noms"], ["Flash safeboot", "Flash app0", "Flash spiffs", "DIRAM", "IRAM", "RTC SLOW", "RTC FAST"],
              "zones : safeboot, app0, FS puis les 4 zones RAM du journal")
    s.verifie(["73,0 %" in z for z in e["zones"][:2]], [False, True], "zones : app0 a 73,0 % (ligne Flash du journal)")
    s.verifie("≈" in e["zones"][2], True, "zones : FS marque estime")
    s.verifie(e["lignes"], ["nvs", "otadata", "safeboot", "app0", "spiffs"], "table : les 5 partitions du CSV")
    s.verifie(e["roles"], [True] * 5, "table : utilite ecrite sous chaque partition")
    s.verifie(e["interdites"], [True, True, False, True, False], "table : nvs, otadata, app0 non supprimables")
    s.verifie(e["ecrire_off"], True, "ecrire : grise avant le diff")

    def choisit(valeur):
        cdp.js(f"""(() => {{ const c = document.getElementById('m-table'); c.value = {json.dumps(valeur)}; c.dispatchEvent(new Event('change')); }})()""")

    s.verifie(cdp.js("[...document.getElementById('m-table').options].map(o => o.value)"), ["", AUTRE, TABLE],
              "table existante : les tables de la flash proposees")
    choisit(AUTRE)
    clic(cdp, "#m-diff")
    s.attend(cdp, "document.getElementById('m-diff-texte').textContent.includes('board_build.partitions')", 10)
    e = etat(cdp)
    s.verifie((f"= {AUTRE}" in e["diff"], "env_" in e["diff"], e["ecrire_off"]), (True, False, False),
              "table existante : l'env pointe vers le fichier, aucun CSV d'env ; ecrire permis")
    choisit("")
    clic(cdp, "#m-diff")
    s.attend(cdp, "document.getElementById('m-messages').textContent.includes('déjà la table')", 10)
    s.verifie(etat(cdp)["ecrire_off"], True, "table actuelle : rien a ecrire, ecrire grise")

    champ(cdp, "app0", 3904 + 64)
    e = etat(cdp)
    s.verifie(e["adresses"][4], "0x4C0000", "curseur : app0 +64 Ko -> le FS recule en 0x4C0000")
    s.verifie(any(x.startswith("v:") for x in e["messages"]), True, "controles : table coherente")
    clic(cdp, "#m-diff")
    s.attend(cdp, "document.getElementById('m-diff-texte').textContent.includes('board_build.partitions')", 10)
    e = etat(cdp)
    s.verifie((f"partitions/env_{A}.csv" in e["diff"], "0x3E0000" in e["diff"], e["ecrire_off"]), (True, True, False),
              "diff : CSV de l'env et option du cenv ; ecrire permis")
    s.verifie(any("persist" in x for x in e["messages"]) and any("OTA" in x for x in e["messages"]), True,
              "diff : persist remplace et OTA bloquee annonces")

    cdp.js("window.proposes = []; window.confirm = t => { window.proposes.push(t); return true; }")
    parts = bp.build_memoire.lit_csv((m.depot / TABLE).read_text(encoding="utf-8"))
    for x in parts:
        x["taille"] += {"app0": 0x10000, "spiffs": -0x10000}.get(x["nom"], 0)
    (m.depot / "partitions" / "deja_la.csv").write_text(bp.texte_csv(bp.valide(parts, 0x1000000)[0]), encoding="utf-8")
    cdp.js("document.getElementById('m-nom').value = 'autre_nom'")
    clic(cdp, "#m-diff")
    s.attend(cdp, "window.proposes.length > 0", 10)
    s.attend(cdp, "document.getElementById('m-messages').textContent.includes('identique')", 10)
    s.verifie(("deja_la.csv" in cdp.js("window.proposes[0]"), "= partitions/deja_la.csv" in etat(cdp)["diff"]), (True, True),
              "table identique : fichier existant propose, l'env pointerait vers lui")
    cdp.js("window.proposes = []; window.confirm = t => { window.proposes.push(t); return false; }")
    clic(cdp, "#m-diff")
    s.attend(cdp, "document.getElementById('m-diff-texte').textContent.includes('autre_nom')", 10)
    s.verifie("= partitions/autre_nom.csv" in etat(cdp)["diff"], True, "proposition refusee : fichier au nom saisi")
    (m.depot / "partitions" / "deja_la.csv").unlink()
    cdp.js("document.getElementById('m-nom').value = ''; window.confirm = () => true")
    clic(cdp, "#m-diff")
    s.attend(cdp, f"document.getElementById('m-diff-texte').textContent.includes('env_{A}.csv')", 10)

    cdp.js("window.confirm = () => false")
    clic(cdp, "#m-ecrire")
    time.sleep(0.5)
    s.verifie((m.depot / "partitions" / f"env_{A}.csv").exists(), False, "ecrire : confirmation refusee -> rien d'ecrit")
    cdp.js("window.confirm = () => true")
    clic(cdp, "#m-ecrire")
    s.attend(cdp, "document.getElementById('m-messages').textContent.includes('Table écrite')", 10)
    cenv = (m.depot / "platformio_tasmota_cenv.ini").read_text(encoding="utf-8")
    s.verifie(((m.depot / "partitions" / f"env_{A}.csv").exists(), f"board_build.partitions  = partitions/env_{A}.csv" in cenv),
              (True, True), "ecrire : CSV de l'env ecrit, option posee dans sa section (depot d'essai)")

    clic(cdp, "#m-parts tr:nth-child(3) input[type=checkbox]")
    e = etat(cdp)
    s.verifie(any(x.startswith("r:Sans safeboot") for x in e["messages"]), True, "suppression safeboot : consequence dite")
    clic(cdp, "#m-diff")
    s.attend(cdp, "document.getElementById('m-diff-texte').textContent.includes('flash_extra_images')", 10)
    e = etat(cdp)
    s.verifie((any("Seul le câble" in x for x in e["messages"]), e["ecrire_off"]), (True, False),
              "suppression safeboot : acceptee, image videe dans le cenv, consequence rappelee")
    clic(cdp, "#m-annuler")
    cdp.js("document.getElementById('m-ajout-nom').value = 'vidage'")
    clic(cdp, "#m-ajouter")
    e = etat(cdp)
    s.verifie(e["lignes"], ["nvs", "otadata", "safeboot", "app0", "vidage", "spiffs"], "ajouter : avant le FS")
    cdp.js("window.__dl = []; window.mTelecharge = (n, t) => window.__dl.push([n, t])")
    clic(cdp, "#m-exporter")
    s.attend(cdp, "window.__dl.length === 1", 10)
    nom, texte = cdp.js("window.__dl[0]")
    s.verifie((nom, "vidage," in texte), (f"env_{A}.csv", True), "exporter : CSV de la table reglee")
    clic(cdp, "#m-annuler")
    cdp.js(f"mImporte({json.dumps(texte)})")
    s.attend(cdp, "document.querySelectorAll('#m-parts tr').length === 6", 10)
    s.verifie(etat(cdp)["lignes"][4], "vidage", "importer : le CSV exporte regle la table")
    cdp.js(f"mImporte({json.dumps(texte.replace('vidage,', 'nvs,'))})")
    s.attend(cdp, "document.getElementById('m-messages').textContent.includes('CSV refusé')", 10)
    s.verifie(len(etat(cdp)["lignes"]), 6, "importer : CSV refuse -> table inchangee, motif dit")
    clic(cdp, "#m-annuler")
    s.verifie(etat(cdp)["adresses"][2], "0x10000", "revenir : table de l'analyse")
    clic(cdp, "#m-analyser")
    s.attend(cdp, "document.getElementById('m-date').textContent.includes('analyse du')", 10)

    cdp.appel("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=True)
    time.sleep(0.8)
    s.verifie(cdp.js("document.documentElement.scrollWidth") <= 390, True, "telephone : pas de defilement horizontal")
    if capture:
        cdp.capture(Path(capture) / "build-memoire-telephone.png")
    cdp.appel("Emulation.setDeviceMetricsOverride", width=1280, height=1000, deviceScaleFactor=1, mobile=False)
    if capture:
        time.sleep(0.5)
        cdp.capture(Path(capture) / "build-memoire.png")
    m.ouvre()
    s.verifie(etat(cdp)["memoire"], False, "rechargement : onglet Mémoire retenu")
    s.verifie(cdp.erreurs(), [], "fin : aucune erreur JS")


def sonde_ota_bloquee(m):
    """Apres l'ecriture : POST /lancer d'une OTA de A refuse, motif nomme (build_serie.controle)."""
    import urllib.error
    import urllib.request
    corps = json.dumps({"lignes": [{"env": A, "methode": "ota", "port": "", "ip": "192.168.0.50"}], "actions": ["upload"]})
    demande = urllib.request.Request(m.url + "lancer", data=corps.encode("utf-8"), method="POST",
                                     headers={"X-Build": "1", "Content-Type": "application/json", "Origin": m.url.rstrip("/")})
    try:
        with urllib.request.urlopen(demande, timeout=10) as r:
            texte = f"{r.status} " + r.read().decode("utf-8")
    except urllib.error.HTTPError as erreur:
        texte = f"{erreur.code} " + erreur.read().decode("utf-8")
    s.verifie(texte.startswith("409") and "OTA bloquée" in texte, True, "lancer : OTA de A refusee apres l'ecriture de la table")


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de l'onglet Mémoire et partitions de la page build.")
    options.add_argument("--capture", help="dossier ou ecrire les captures PNG")
    args = options.parse_args()
    m = None
    try:
        m = s.Montage()
        m.demarre(False)
        prepare_depot(m)
        sonde_onglet(m, args.capture)
        sonde_ota_bloquee(m)
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
