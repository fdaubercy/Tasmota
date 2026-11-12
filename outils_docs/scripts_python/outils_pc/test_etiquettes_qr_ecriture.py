"""Banc de etiquettes_qr_ecriture (surcharge, page /qrcode : cenv, autoexec, qrcode.json ; impressions). Code de sortie 0 = vert.

Lancer avec le Python de PlatformIO depuis la racine du depot :
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_etiquettes_qr_ecriture.py
Tout se passe dans une COPIE temporaire : .ini (cenv compris), user_config_override.h, dossiers de la cuve (persist, autoexec),
du volet de la porte (sans persist, faux autoexec, exclusion heritee de sa base) et de la TV (ESP8266, config decodee), gabarit.
Les fichiers de la page de carte (A6) y sont simules quand un test en a besoin. Le vrai depot n'est jamais ecrit ; les sauvegardes
de Transaction vont dans un dossier temporaire (OUTILS_TASMOTA_DOSSIER).
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi

DEPOT = Path(fbi.__file__).resolve().parents[3]
os.environ["OUTILS_TASMOTA_DOSSIER"] = tempfile.mkdtemp(prefix="banc_etiquettes_qr_")   # avant l'import des modules d'ecriture
import etiquettes_qr_ecriture as eqe                  # noqa: E402
import etiquettes_qr_modele as modele                 # noqa: E402

INIS = ("platformio.ini", "platformio_tasmota32.ini", "platformio_tasmota_env.ini", "platformio_tasmota_env32.ini",
        "platformio_override.ini", fbi.FICHIER_CENV)
CUVE, PORTE, TV = "tasmota32s3-garage-capteurs-cuve-modbus", "tasmota32-rdc-vr-porte", "tasmota-rdc-tv-salon"
AUTOEXEC_PORTE = "import demarrage\nif demarrage.prologue()\n    demarrage.charge([\"controleWeb\"])\nend\n"
SANS_BUILD = lambda: []
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def refuse(appel, exception, libelle, motif=""):
    try:
        appel()
    except exception as e:
        verifie(motif in str(e), True, f"{libelle}  ({e})")
        return
    verifie("pas de refus", motif, libelle)


def copie(dossier):
    racine = Path(dossier)
    for f in INIS + ("tasmota/user_config_override.h",):
        (racine / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DEPOT / f, racine / f)
    for env, fichiers in ((CUVE, ("_persist.json", "autoexec.be")), (TV, ("config_decodee.json",))):
        d = racine / fbe.dossier_carte(env)
        d.mkdir(parents=True)
        for f in fichiers:
            shutil.copy2(DEPOT / fbe.dossier_carte(env) / f, d / f)
    texte = (racine / fbe.dossier_carte(CUVE) / "autoexec.be").read_text(encoding="utf-8")
    (racine / fbe.dossier_carte(CUVE) / "autoexec.be").write_text(eqe.age._autoexec(texte, False, ligne=eqe.LIGNE_AUTOEXEC),
                                                                 encoding="utf-8")
    d = racine / fbe.dossier_carte(PORTE)
    d.mkdir(parents=True)
    (d / "autoexec.be").write_text(AUTOEXEC_PORTE, encoding="utf-8")
    (racine / modele.DOSSIER).mkdir(parents=True)
    shutil.copy2(DEPOT / modele.GABARIT, racine / modele.GABARIT)
    return racine


def fichiers_page(racine):
    for f in eqe.FICHIERS_PAGE:
        (racine / f).parent.mkdir(parents=True, exist_ok=True)
        (racine / f).write_text("# simule par le banc\n", encoding="utf-8")
    p = eqe.prevoit_exclusions(racine)              # etat de depart de l'A6 : page exclue de tous les envs
    eqe.ecrit_exclusions(racine, p["empreinte"], SANS_BUILD)


def instantane(racine):
    return {p.relative_to(racine).as_posix(): p.read_bytes() for p in sorted(racine.rglob("*")) if p.is_file()}


def exclus(racine, env):
    return eqe.NOMS & {Path(e.chemin).name for e in fbi.resout(fbi.lit_sections(racine), env, fbe.EXCLUDE)}


def ecrit(racine, env, reglage, page):
    p = eqe.prevoit(racine, env, reglage, page)
    eqe.ecrit(racine, env, reglage, page, p["empreinte"], SANS_BUILD)
    return p


def test_surcharge(racine):
    g = modele.charge_gabarit(racine)
    r = {**g, "style": {**g["style"], "couleur": "#1b2a4a"}, "entre_lignes": "\n"}
    p = ecrit(racine, CUVE, r, False)
    rel = (modele.DOSSIER / "cartes" / f"{CUVE}.json").as_posix()
    verifie([f["chemin"] for f in p["fichiers"]], [rel], "surcharge seule ecrite (pas de page)")
    verifie(json.loads((racine / rel).read_text(encoding="utf-8")), {"entre_lignes": "\n", "style": {"couleur": "#1b2a4a"}},
            "surcharge = ecart au gabarit seulement")
    verifie(modele.charge_reglage(racine, CUVE), r, "gabarit + surcharge = reglage demande")
    ecrit(racine, CUVE, g, False)
    verifie((racine / rel).exists(), False, "retour au gabarit : surcharge supprimee")


def test_page_refusee_sans_fichiers(racine):
    refuse(lambda: eqe.prevoit(racine, CUVE, modele.charge_gabarit(racine), True), ValueError,
           "page refusee tant que les fichiers de l'A6 manquent", "pas encore disponible")


def test_page(racine):
    fichiers_page(racine)
    envs =[e["nom"] for e in fbe.envs_proposes(racine)]
    verifie([e for e in envs if exclus(racine, e) != eqe.NOMS], [], "exclusions : page exclue de tous les envs ESP32")
    verifie(eqe.prevoit_exclusions(racine)["fichiers"], [], "exclusions : une 2e passe ne change rien")
    avant = instantane(racine)
    g = modele.charge_gabarit(racine)
    p = ecrit(racine, CUVE, g, True)
    dossier = fbe.dossier_carte(CUVE)
    verifie(sorted(f["chemin"] for f in p["fichiers"]),
            sorted([fbi.FICHIER_CENV, dossier + "/autoexec.be", dossier + "/" + eqe.FICHIER_CARTE]), "page : 3 fichiers")
    verifie(exclus(racine, CUVE), set(), "page : la cuve embarque la page")
    verifie([e for e in envs if e != CUVE and exclus(racine, e) != eqe.NOMS], [], "page : tous les autres l'excluent")
    auto = (racine / dossier / "autoexec.be").read_text(encoding="utf-8")
    verifie(auto.count(eqe.LIGNE_AUTOEXEC), 1, "page : ligne d'autoexec posee une fois")
    qr = json.loads((racine / dossier / eqe.FICHIER_CARTE).read_text(encoding="utf-8"))
    verifie((qr["version"], "CAPTEURS-CUVE" in qr["texte"], qr["correction"]), (1, True, "M"), "qrcode.json : texte resolu")
    persist = (DEPOT / dossier / "_persist.json").read_text(encoding="utf-8")
    secrets = modele._valeurs_secretes(json.loads(persist), set())
    verifie([s for s in secrets if s in json.dumps(qr, ensure_ascii=False)], [], "qrcode.json sans secret")
    verifie(any("firmware" in s or "non solidifié" in s for s in p["signaux"]), True, "page : solidification signalee")
    verifie(eqe.prevoit(racine, CUVE, g, True)["fichiers"], [], "page : 2e passe identique, rien a ecrire")
    ecrit(racine, CUVE, g, False)
    apres = instantane(racine)
    verifie(sorted(k for k in set(avant) | set(apres) if avant.get(k) != apres.get(k)), [],
            "page retiree : depot identique octet pour octet a l'etat d'avant")


def test_porte_heritee(racine):
    fichiers_page(racine)
    g = modele.charge_gabarit(racine)
    ecrit(racine, PORTE, g, True)
    verifie(exclus(racine, PORTE), set(), "porte (exclusion heritee de sa base) : page levee")
    verifie(exclus(racine, "tasmota32-base") if "tasmota32-base" in [e["nom"] for e in fbe.envs_proposes(racine)] else eqe.NOMS,
            eqe.NOMS, "la base garde l'exclusion pour ses autres cartes")
    qr = json.loads((racine / fbe.dossier_carte(PORTE) / eqe.FICHIER_CARTE).read_text(encoding="utf-8"))
    verifie("Hostname" in qr["texte"], False, "porte sans persist : ligne Hostname omise")
    ecrit(racine, PORTE, g, False)
    verifie(exclus(racine, PORTE), eqe.NOMS, "porte : page retiree, exclusion revenue")


def test_refus(racine):
    fichiers_page(racine)
    g = modele.charge_gabarit(racine)
    refuse(lambda: eqe.prevoit(racine, TV, g, True), ValueError, "ESP8266 : page refusee", "ESP8266")
    p = eqe.prevoit(racine, TV, {**g, "taille_mm": 30}, False)
    verifie([f["chemin"] for f in p["fichiers"]], [(modele.DOSSIER / "cartes" / f"{TV}.json").as_posix()],
            "ESP8266 : surcharge seule, cenv jamais touche")
    refuse(lambda: eqe.prevoit(racine, CUVE, {**g, "taille_mm": 5}, False), ValueError, "reglage invalide refuse", "taille")
    refuse(lambda: eqe.prevoit(racine, "tasmota32-base", g, False), LookupError, "base refusee", "carte inconnue")
    avant = instantane(racine)
    p = eqe.prevoit(racine, CUVE, g, True)
    refuse(lambda: eqe.ecrit(racine, CUVE, g, True, p["empreinte"], lambda: ["tasmota32p4"]), RuntimeError,
           "build en cours : refus", "build")
    refuse(lambda: eqe.ecrit(racine, CUVE, g, True, p["empreinte"], lambda: None), RuntimeError,
           "build indetectable : refus", "build")
    chemin = racine / fbe.dossier_carte(CUVE) / "_persist.json"
    d = json.loads(chemin.read_text(encoding="utf-8"))
    d["serveur"]["hostname"] = "CUVE-RENOMMEE"
    chemin.write_text(json.dumps(d), encoding="utf-8")
    avant[chemin.relative_to(racine).as_posix()] = chemin.read_bytes()
    refuse(lambda: eqe.ecrit(racine, CUVE, g, True, p["empreinte"], SANS_BUILD), RuntimeError,
           "persist modifie depuis le diff : refus", "refaire le diff")
    verifie(instantane(racine) == avant, True, "refus : rien ecrit")


def test_impressions(racine):
    eqe.note_impression(racine, {CUVE: "Hostname : CUVE · IP : 192.168.0.60"}, 25)
    brut = (racine / eqe.IMPRESSIONS).read_text(encoding="utf-8")
    d = json.loads(brut)
    verifie((d[CUVE]["empreinte"], d[CUVE]["taille_mm"]), (modele.empreinte("Hostname : CUVE · IP : 192.168.0.60"), 25),
            "impression notee : empreinte et taille")
    verifie("192.168" in brut, False, "impressions.json sans le texte")
    eqe.annule_impression(racine, CUVE)
    verifie(eqe.lit_impressions(racine), {}, "impression annulee")
    refuse(lambda: eqe.note_impression(racine, {"../x": "t"}, 25), ValueError, "env invalide refuse", "invalide")


def test_gabarit(racine):
    g = modele.charge_gabarit(racine)
    refuse(lambda: eqe.prevoit_gabarit(racine, {**g, "lignes": []}), ValueError, "gabarit invalide refuse", "lignes")
    p = eqe.prevoit_gabarit(racine, {**g, "taille_mm": 30})
    eqe.ecrit_gabarit(racine, {**g, "taille_mm": 30}, p["empreinte"], SANS_BUILD)
    verifie(modele.charge_gabarit(racine)["taille_mm"], 30, "gabarit ecrit")


TESTS = [test_surcharge, test_page_refusee_sans_fichiers, test_page, test_porte_heritee, test_refus, test_impressions,
         test_gabarit]

if __name__ == "__main__":
    for t in TESTS:
        with tempfile.TemporaryDirectory(prefix="etiquettes_qr_") as d:
            print(f"--- {t.__name__}")
            t(copie(d))
    print("BANC_ETIQUETTES_QR_ECRITURE:", f"ECHEC {len(ECHECS)} : " + " ; ".join(ECHECS) if ECHECS else "OK")
    sys.exit(1 if ECHECS else 0)
