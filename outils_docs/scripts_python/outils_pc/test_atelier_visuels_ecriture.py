"""Banc de atelier_visuels_ecriture (visuel.json, fond, ligne d'autoexec, liste `visuel_accueil` du cenv). Code de sortie 0 = vert.

Lancer avec le Python de PlatformIO depuis la racine du depot :
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_visuels_ecriture.py
Tout se passe dans une COPIE temporaire (.ini dont le cenv, user_config_override.h, dossiers de la cuve et de la porte). Le cenv
est teste SANS la liste `visuel_accueil` (etat du depot avant A4) puis AVEC elle (apres l'exclusion). Les trois fichiers de la
page sont simules. Le vrai depot n'est jamais ecrit ; les sauvegardes de Transaction vont dans un dossier temporaire.
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
os.environ["OUTILS_TASMOTA_DOSSIER"] = tempfile.mkdtemp(prefix="banc_visuels_")   # avant l'import du module d'ecriture
import atelier_visuels_ecriture as eve                # noqa: E402

INIS = ("platformio.ini", "platformio_tasmota32.ini", "platformio_tasmota_env.ini", "platformio_tasmota_env32.ini",
        "platformio_override.ini", fbi.FICHIER_CENV)
CUVE, PORTE = "tasmota32s3-garage-capteurs-cuve-modbus", "tasmota32-rdc-vr-porte"
AUTOEXEC = "import demarrage\nif demarrage.prologue()\n    demarrage.charge([\"controleWeb\"])\n    demarrage.historique()\nend\n"
SANS_BUILD = lambda: []
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'
WEBP = b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"\0" * 8
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


def description(type_fond="svg", **autres):
    return {"version": 1, "fond": {"type": type_fond, "largeur": 480, "hauteur": 360}, "elements": [], **autres}


def copie(dossier, avec_liste, avec_page=True):
    racine = Path(dossier)
    for f in INIS + ("tasmota/user_config_override.h",):
        (racine / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DEPOT / f, racine / f)
    d = racine / fbe.dossier_carte(CUVE)
    d.mkdir(parents=True)
    (d / "autoexec.be").write_text(AUTOEXEC, encoding="utf-8")
    shutil.copy2(DEPOT / fbe.dossier_carte(CUVE) / "_persist.json", d / "_persist.json")
    d = racine / fbe.dossier_carte(PORTE)
    d.mkdir(parents=True)
    (d / "autoexec.be").write_text(AUTOEXEC, encoding="utf-8")
    if avec_page:
        for f in eve.FICHIERS_PAGE:
            (racine / f).parent.mkdir(parents=True, exist_ok=True)
            (racine / f).write_text("# simule par le banc\n", encoding="utf-8")
    if avec_liste:                                    # etat apres l'A4 : liste creee et page exclue de tous les envs
        octets, eol, lignes = eve.age._lit_cenv(racine)
        lignes = eve._exclut(racine, eve._assure_liste(racine, lignes), set())
        (racine / fbi.FICHIER_CENV).write_bytes(eol.join(lignes).encode("utf-8"))
    return racine


def instantane(racine):
    return {p.relative_to(racine).as_posix(): p.read_bytes() for p in sorted(racine.rglob("*")) if p.is_file()}


def exclus(racine, env):
    return eve.NOMS & {Path(e.chemin).name for e in fbi.resout(fbi.lit_sections(racine), env, fbe.EXCLUDE)}


def ecrit(racine, env, desc, fond, type_fond="svg"):
    p = eve.prevoit(racine, env, desc, fond, type_fond)
    eve.ecrit(racine, env, desc, fond, type_fond, p["empreinte"], SANS_BUILD)
    return p


def test_ecriture(racine, avec_liste):
    etiquette = "avec" if avec_liste else "sans"
    envs = [e["nom"] for e in fbe.envs_proposes(racine)]
    avant = instantane(racine)
    p = ecrit(racine, CUVE, description(), SVG)
    dossier = fbe.dossier_carte(CUVE)
    verifie(sorted(f["chemin"] for f in p["diff"]),
            sorted([fbi.FICHIER_CENV, dossier + "/autoexec.be", dossier + "/visuel.json", dossier + "/visuel.svg"]),
            f"{etiquette} liste : 4 fichiers dans le diff")
    verifie(json.loads((racine / dossier / "visuel.json").read_text(encoding="utf-8")), description(), "visuel.json = description")
    verifie((racine / dossier / "visuel.svg").read_bytes(), SVG, "visuel.svg ecrit")
    lignes = [l.strip() for l in (racine / dossier / "autoexec.be").read_text(encoding="utf-8").splitlines()]
    verifie(lignes[-2:], [eve.LIGNE_AUTOEXEC, "end"], "ligne d'autoexec en derniere position du bloc (apres historique)")
    verifie(lignes.count(eve.LIGNE_AUTOEXEC), 1, "ligne posee une fois")
    verifie(exclus(racine, CUVE), set(), "la cuve embarque le visuel")
    verifie([e for e in envs if e != CUVE and exclus(racine, e) != eve.NOMS], [], "tous les autres envs l'excluent")
    verifie(eve.LISTE in fbi.lit_sections(racine).sections["berry_commun"], True, "liste visuel_accueil dans [berry_commun]")
    verifie(eve.prevoit(racine, CUVE, description(), SVG, "svg")["diff"], [], "2e passe identique, rien a ecrire")
    verifie(eve.prevoit(racine, CUVE, description(), None, "svg")["diff"], [], "fond None = fond du depot garde")
    # webp remplace svg, le diff le montre
    desc_w = description("webp")
    p = eve.prevoit(racine, CUVE, desc_w, WEBP, "webp")
    chemins = {f["chemin"]: f for f in p["diff"]}
    verifie((chemins[dossier + "/visuel.svg"]["apres"], "octets" in chemins[dossier + "/visuel.webp"]["apres"]), (None, True),
            "webp: le diff montre le svg retire et le webp cree")
    ecrit(racine, CUVE, desc_w, WEBP, "webp")
    verifie(((racine / dossier / "visuel.svg").exists(), (racine / dossier / "visuel.webp").read_bytes()), (False, WEBP),
            "fond webp remplace le svg")
    # retrait : depot identique octet pour octet
    p = eve.prevoit_retire(racine, CUVE)
    eve.retire(racine, CUVE, p["empreinte"], SANS_BUILD)
    apres = instantane(racine)
    verifie(sorted(k for k in set(avant) | set(apres) if avant.get(k) != apres.get(k)),
            [] if avec_liste else [fbi.FICHIER_CENV],
            "retire : depot identique" + ("" if avec_liste else " (le cenv garde la liste creee et l'exclusion, comme etiquettes_qr)"))
    verifie(exclus(racine, CUVE), eve.NOMS, "retire : le visuel est de nouveau exclu")


def test_porte_heritee(racine):
    ecrit(racine, PORTE, description(), SVG)
    verifie(exclus(racine, PORTE), set(), "porte (exclusion heritee de sa base) : levee")
    p = eve.prevoit_retire(racine, PORTE)
    eve.retire(racine, PORTE, p["empreinte"], SANS_BUILD)
    verifie(exclus(racine, PORTE), eve.NOMS, "porte : visuel retire, exclusion revenue")


def test_refus(racine):
    avant = instantane(racine)
    p = eve.prevoit(racine, CUVE, description(), SVG, "svg")
    refuse(lambda: eve.ecrit(racine, CUVE, description(), SVG, "svg", p["empreinte"], lambda: ["tasmota32p4"]), RuntimeError,
           "build en cours : refus", "build")
    refuse(lambda: eve.ecrit(racine, CUVE, description(), SVG, "svg", p["empreinte"], lambda: None), RuntimeError,
           "build indetectable : refus", "build")
    refuse(lambda: eve.ecrit(racine, CUVE, description(), SVG, "svg", "perimee", SANS_BUILD), RuntimeError,
           "empreinte perimee : refus", "refaire le diff")
    chemin = racine / fbe.dossier_carte(CUVE) / "autoexec.be"
    chemin.write_text(AUTOEXEC + "-- modifie\n", encoding="utf-8")
    avant[chemin.relative_to(racine).as_posix()] = chemin.read_bytes()
    refuse(lambda: eve.ecrit(racine, CUVE, description(), SVG, "svg", p["empreinte"], SANS_BUILD), RuntimeError,
           "depot modifie depuis le diff : refus", "refaire le diff")
    refuse(lambda: eve.prevoit(racine, CUVE, {**description(), "version": 2}, SVG, "svg"), ValueError,
           "description invalide : refus avec le message du validateur", "version")
    refuse(lambda: eve.prevoit(racine, CUVE, description("webp"), SVG, "svg"), ValueError, "type de fond different : refus",
           "fond.type")
    refuse(lambda: eve.prevoit(racine, CUVE, description("webp"), SVG, "webp"), ValueError, "contenu qui n'est pas un webp : refus",
           "webp")
    refuse(lambda: eve.prevoit(racine, CUVE, description(), b"x" * 300000, "svg"), ValueError, "fond trop lourd : refus", "seuil")
    refuse(lambda: eve.prevoit(racine, CUVE, description(), None, "svg"), ValueError, "pas de fond au depot : refus", "aucun fond")
    refuse(lambda: eve.prevoit(racine, "tasmota32-base", description(), SVG, "svg"), LookupError, "base refusee", "carte inconnue")
    verifie(instantane(racine) == avant, True, "refus : rien ecrit")


def test_module_absent(racine):
    refuse(lambda: eve.prevoit(racine, CUVE, description(), SVG, "svg"), ValueError, "fichiers de la page absents : refus",
           "pas encore disponibles")


TESTS = [(test_ecriture, False), (test_ecriture, True), (test_porte_heritee, True), (test_refus, True), (test_module_absent, True)]

if __name__ == "__main__":
    for t, avec_liste in TESTS:
        with tempfile.TemporaryDirectory(prefix="visuels_") as d:
            print(f"--- {t.__name__} (liste {'presente' if avec_liste else 'absente'})")
            if t is test_ecriture:
                t(copie(d, avec_liste), avec_liste)
            elif t is test_module_absent:
                t(copie(d, avec_liste, avec_page=False))
            else:
                t(copie(d, avec_liste))
    print("BANC_VISUELS_ECRITURE:", f"ECHEC {len(ECHECS)} : " + " ; ".join(ECHECS) if ECHECS else "OK")
    sys.exit(1 if ECHECS else 0)
