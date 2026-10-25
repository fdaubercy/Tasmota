"""Banc de fichiers_berry_etat (recensement des fichiers Berry et etat de chacun dans un env).

Code de sortie 0 = vert. Depot d'essai dans un dossier temporaire ; le controle sur les vrais fichiers
du depot est en lecture seule.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi

ECHECS = []
RACINE = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))

ENV = """\
[env:tasmota]
build_flags             = -DESP8266

[env:tasmota32_base]
custom_files_upload     = no_files

[env:tasmota32s3]
extends                 = env:tasmota32_base
custom_files_upload     = ${env:tasmota32_base.custom_files_upload}
"""

CENV = """\
[berry_commun]
socle   =   data/fs/a.be
            data/fs/b.be

[env:tasmota32s3-base]
extends                 = env:tasmota32s3
custom_files_upload     = ${env:tasmota32s3.custom_files_upload}
                          tasmota/berry/modules/Partition_Wizard/partition_wizard.bec

[env:tasmota32s3-garage-carte]
extends                 = env:tasmota32s3-base
custom_berry_solidify   =   ${berry_commun.socle}
                            data/garage/tasmota32s3-carte/controleCarte.be
custom_files_exclude_solidified = ON
custom_files_exclude    =   data/fs/x.be
                            data/fs/b.be
                            data/sd/js/lourd.js.gz
                            data/fs/disparu.be
custom_files_upload     =   ${env:tasmota32s3-base.custom_files_upload}
                            data/garage/tasmota32s3-carte

[env:tasmota32s3-cave-sans]
extends                 = env:tasmota32s3-base
custom_berry_solidify   =   ${berry_commun.socle}

[env:tasmota-jardin-piscine]
extends                 = env:tasmota
"""

FICHIERS = ["data/fs/a.be", "data/fs/b.be", "data/fs/x.be", "data/fs/notes.txt", "data/sd/js/lourd.js.gz",
            "data/garage/tasmota32s3-carte/autoexec.be", "data/garage/tasmota32s3-carte/controleCarte.be",
            "data/garage/tasmota32s3-carte/a.be", "data/garage/tasmota32s3-carte-sauvegarde/vieux.be",
            "tasmota/berry/modules/Partition_Wizard/partition_wizard.bec",
            "tasmota/berry/modules/Partition_Wizard/autoexec.be", "tasmota/berry/modules/Webui_Status.tapp"]


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def depot_essai(dossier):
    racine = Path(dossier)
    (racine / "platformio_tasmota_env32.ini").write_bytes(ENV.replace("\n", "\r\n").encode("utf-8"))
    (racine / fbi.FICHIER_CENV).write_bytes(CENV.replace("\n", "\r\n").encode("utf-8"))
    for f in FICHIERS:
        (racine / f).parent.mkdir(parents=True, exist_ok=True)
        (racine / f).write_text(f"# essai {f}\n", encoding="utf-8")    # contenus distincts : un homonyme n'est pas une copie
    return racine


def par_chemin(etat):
    return {f["chemin"]: f for f in etat["fichiers"]}


def test_dossier_carte():
    verifie(fbe.dossier_carte("tasmota32p4-garage-serveur-modbus"), "data/garage/tasmota32p4-serveur-modbus",
            "dossier_carte P4 (regle de transform_name)")
    verifie(fbe.dossier_carte("tasmota32s3-cave-serveur-rly"), "data/cave/tasmota32s3-serveur-rly", "dossier_carte cave")
    verifie(fbe.dossier_carte("tasmota32s3-base-N16R8"), None, "dossier_carte : aucun pour une base")
    try:
        fbe.dossier_carte("sanstiret")
        verifie("pas d'exception", "ValueError", "dossier_carte sans tiret")
    except ValueError:
        verifie(True, True, "dossier_carte sans tiret : ValueError")


def test_recense_carte(racine):
    obtenu = [(f["chemin"], f["groupe"]) for f in fbe.recense(racine, "tasmota32s3-garage-carte")]
    verifie(obtenu, [("data/fs/a.be", "fs"), ("data/fs/b.be", "fs"), ("data/fs/x.be", "fs"),
                     ("data/garage/tasmota32s3-carte/a.be", "carte"),
                     ("data/garage/tasmota32s3-carte/autoexec.be", "carte"),
                     ("data/garage/tasmota32s3-carte/controleCarte.be", "carte"),
                     ("tasmota/berry/modules/Partition_Wizard/partition_wizard.bec", "amont"),
                     ("tasmota/berry/modules/Webui_Status.tapp", "amont")],
            "recense_carte : data/fs, carte, amont (ni .txt, ni sauvegarde, ni autoexec d'un module amont)")
    verifie([f["groupe"] for f in fbe.recense(racine, "tasmota32s3-base")].count("carte"), 0,
            "recense : aucun fichier de carte pour une base")


def test_etat_trois_etats(racine):
    f = par_chemin(fbe.etat_env(racine, "tasmota32s3-garage-carte"))
    verifie(f["data/fs/a.be"]["etat"], "solidifie", "etat : a.be solidifie (socle)")
    verifie(f["data/fs/x.be"]["etat"], "exclu", "etat : x.be exclu")
    verifie(f["data/garage/tasmota32s3-carte/autoexec.be"]["etat"], "fs", "etat : autoexec sur le FS")
    verifie(f["data/garage/tasmota32s3-carte/autoexec.be"]["figes"], True, "etat : autoexec fige")
    verifie(f["data/garage/tasmota32s3-carte/controleCarte.be"]["etat"], "solidifie", "etat : fichier de carte solidifie")
    p = f["data/fs/a.be"]["provenances"][0]
    verifie((p["option"], p["section"], p["option_ecrite"], p["partagee"], p["amont"]),
            ("custom_berry_solidify", "berry_commun", "socle", True, False), "provenance socle")
    verifie(p["envs"], ["tasmota32s3-cave-sans", "tasmota32s3-garage-carte"], "provenance socle : envs touches")
    p = f["data/fs/x.be"]["provenances"][0]
    verifie((p["partagee"], p["envs"]), (False, ["tasmota32s3-garage-carte"]), "provenance propre : non partagee")


def test_etat_amont_absent(racine):
    f = par_chemin(fbe.etat_env(racine, "tasmota32s3-garage-carte"))
    verifie(f["tasmota/berry/modules/Partition_Wizard/partition_wizard.bec"]["etat"], "fs", "amont liste : sur le FS")
    p = f["tasmota/berry/modules/Partition_Wizard/partition_wizard.bec"]["provenances"][0]
    verifie((p["section"], p["partagee"]), ("env:tasmota32s3-base", True), "amont liste : vient de la base")
    verifie(f["tasmota/berry/modules/Webui_Status.tapp"]["etat"], "absent", "amont non liste : absent")


def test_etat_doublon(racine):
    f = par_chemin(fbe.etat_env(racine, "tasmota32s3-garage-carte"))
    verifie(f["data/fs/b.be"]["incoherent"], True, "doublon : b.be solidifie ET exclu -> incoherent")
    verifie(f["data/fs/a.be"]["incoherent"], False, "doublon : a.be coherent")
    verifie(sorted(p["option"] for p in f["data/fs/b.be"]["provenances"]),
            ["custom_berry_solidify", "custom_files_exclude"], "doublon : deux provenances")


def test_etat_homonyme(racine):
    f = par_chemin(fbe.etat_env(racine, "tasmota32s3-garage-carte"))
    verifie(f["data/garage/tasmota32s3-carte/a.be"]["homonyme"], "data/fs/a.be", "homonyme : a.be de la carte")
    verifie(f["data/fs/a.be"]["homonyme"], "data/garage/tasmota32s3-carte/a.be", "homonyme : a.be de data/fs")
    verifie(f["data/fs/x.be"]["homonyme"], None, "homonyme : x.be seul")


def test_copie_temporaire(racine):
    """Un .be de la carte identique a data/fs/<meme nom> = copie temporaire d'un build (copy_fs_image)."""
    copie = racine / "data/garage/tasmota32s3-carte/x.be"
    shutil.copyfile(racine / "data/fs/x.be", copie)
    try:
        etat = fbe.etat_env(racine, "tasmota32s3-garage-carte")
        f = par_chemin(etat)
        verifie(("data/garage/tasmota32s3-carte/x.be" in f, f["data/fs/x.be"]["homonyme"]), (False, None),
                "copie temporaire : ni proposee, ni homonyme")
        verifie(etat["copies_temporaires"], ["data/garage/tasmota32s3-carte/x.be"], "copie temporaire : listee")
        verifie(f["data/garage/tasmota32s3-carte/a.be"]["homonyme"], "data/fs/a.be", "vrai homonyme (contenu different) : garde")
    finally:
        copie.unlink()


def test_etat_hors_perimetre_et_disparu(racine):
    e = fbe.etat_env(racine, "tasmota32s3-garage-carte")
    verifie([x["chemin"] for x in e["hors_perimetre"]], ["data/sd/js/lourd.js.gz"], "hors perimetre : le .js.gz")
    verifie([x["chemin"] for x in e["disparus"]], ["data/fs/disparu.be"], "disparu : ligne vers un fichier absent")
    verifie("data/garage/tasmota32s3-carte" in [x["chemin"] for x in e["hors_perimetre"] + e["disparus"]], False,
            "dossier de custom_files_upload : ni hors perimetre ni disparu")


def test_etat_sans_exclude_solidified(racine):
    verifie(fbe.etat_env(racine, "tasmota32s3-cave-sans")["exclude_solidified"], False, "exclude_solidified absent")
    verifie(fbe.etat_env(racine, "tasmota32s3-garage-carte")["exclude_solidified"], True, "exclude_solidified ON")


def test_envs_proposes(racine):
    verifie(fbe.envs_proposes(racine),
            [{"nom": "tasmota32s3-base", "famille": "bases"}, {"nom": "tasmota32s3-garage-carte", "famille": "cartes"},
             {"nom": "tasmota32s3-cave-sans", "famille": "cartes"}], "envs_proposes : ESP32 du cenv, sans ESP8266")


def test_env_inconnu(racine):
    try:
        fbe.etat_env(racine, "tasmota32s3-nulle-part")
        verifie("pas d'exception", "LookupError", "env inconnu")
    except LookupError:
        verifie(True, True, "env inconnu : LookupError")


def test_vrais_fichiers():
    ini = fbi.lit_sections(RACINE)
    for e in fbe.envs_proposes(RACINE):
        if e["famille"] != "cartes" or not (RACINE / fbe.dossier_carte(e["nom"])).is_dir():
            continue                       # ex. tasmota32-rdc-vr-porte : pas encore de dossier data/
        dossier = fbe.dossier_carte(e["nom"])
        up = [x.chemin for x in fbi.resout(ini, e["nom"], "custom_files_upload")]
        verifie(dossier in up, True, f"vrais fichiers : {e['nom']} -> {dossier} dans custom_files_upload")
    etat = par_chemin(fbe.etat_env(RACINE, "tasmota32p4-garage-serveur-modbus"))
    verifie(etat["data/fs/udpFonctions.be"]["etat"], "solidifie", "vrais fichiers : udpFonctions solidifie sur le P4")


def principal():
    test_dossier_carte()
    with tempfile.TemporaryDirectory() as t:
        racine = depot_essai(t)
        for test in (test_recense_carte, test_etat_trois_etats, test_etat_amont_absent, test_etat_doublon,
                     test_etat_homonyme, test_copie_temporaire, test_etat_hors_perimetre_et_disparu, test_etat_sans_exclude_solidified,
                     test_envs_proposes, test_env_inconnu):
            try:
                test(racine)
            except Exception as exc:
                verifie(repr(exc), "pas d'exception", test.__name__)
    try:
        test_vrais_fichiers()
    except Exception as exc:
        verifie(repr(exc), "pas d'exception", "test_vrais_fichiers")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
