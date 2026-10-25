"""Banc de fichiers_berry_ini (lecture des .ini, resolution des references, provenance des lignes).

Code de sortie 0 = vert. Les .ini d'essai sont ecrits dans un dossier temporaire (en CRLF, comme le
vrai cenv) ; le controle sur les vrais fichiers du depot est en lecture seule.
"""

import os
import sys
import tempfile
from pathlib import Path

import fichiers_berry_ini as fbi

ECHECS = []
RACINE = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))

# Fichier d'amont : la base commune, avec une liste de fichiers
ENV32 = """\
[env:tasmota32_base]
custom_files_upload     = no_files

[env:tasmota32s3]
extends                 = env:tasmota32_base
custom_files_upload     = ${env:tasmota32_base.custom_files_upload}
                          tasmota/berry/modules/Partition_Manager.tapp
"""

CENV = """\
[berry_commun]
; Socle : toutes les cartes.
socle   =   data/fs/a.be
            data/fs/b.be
modbus  =   data/fs/m.be

[env:tasmota32s3-base]
extends                 = env:tasmota32s3
custom_files_upload     = ${env:tasmota32s3.custom_files_upload}
; scripts tasmota Berry en option
                            tasmota/berry/modules/Partition_Wizard/partition_wizard.bec
custom_files_exclude    = data/fs/x.be
custom_berry_solidify   = ${berry_commun.socle}

[env:tasmota32s3-garage-carte]
extends                 = env:tasmota32s3-base
custom_berry_solidify   =   ${berry_commun.socle}
                            ${berry_commun.modbus}
                            data/garage/tasmota32s3-carte/controleCarte.be   ; raison (2026-10-25)
custom_files_upload     =   ${env:tasmota32s3-base.custom_files_upload}
                            data/garage/tasmota32s3-carte

[env:tasmota32s3-cave-autre]
extends                 = env:tasmota32s3-garage-carte

[env:tasmota32s3-cave-boucle]
extends                 = env:tasmota32s3-cave-boucle
custom_files_exclude    = ${env:tasmota32s3-cave-boucle2.custom_files_exclude}

[env:tasmota32s3-cave-boucle2]
extends                 = env:tasmota32s3-base
custom_files_exclude    = ${env:tasmota32s3-cave-boucle.custom_files_exclude}
"""


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def depot_essai(dossier, cenv=CENV):
    racine = Path(dossier)
    (racine / "platformio_tasmota_env32.ini").write_bytes(ENV32.replace("\n", "\r\n").encode("utf-8"))
    (racine / fbi.FICHIER_CENV).write_bytes(cenv.replace("\n", "\r\n").encode("utf-8"))
    return racine


def chemins(entrees):
    return [e.chemin for e in entrees]


def test_resout_socle_et_propre(racine):
    ini = fbi.lit_sections(racine)
    e = fbi.resout(ini, "tasmota32s3-garage-carte", "custom_berry_solidify")
    verifie(chemins(e), ["data/fs/a.be", "data/fs/b.be", "data/fs/m.be",
                         "data/garage/tasmota32s3-carte/controleCarte.be"], "resout_socle_et_propre : chemins")
    verifie([x.section for x in e], ["berry_commun", "berry_commun", "berry_commun", "env:tasmota32s3-garage-carte"],
            "resout_socle_et_propre : sections d'ecriture")
    verifie([x.option for x in e], ["socle", "socle", "modbus", "custom_berry_solidify"],
            "resout_socle_et_propre : options d'ecriture")
    verifie({x.fichier for x in e}, {fbi.FICHIER_CENV}, "resout_socle_et_propre : fichier")
    texte = (racine / fbi.FICHIER_CENV).read_bytes().decode("utf-8").splitlines()
    verifie(all(x.chemin in texte[x.ligne] for x in e), True, "resout_socle_et_propre : numeros de ligne exacts")


def test_resout_cascade_env(racine):
    ini = fbi.lit_sections(racine)
    e = fbi.resout(ini, "tasmota32s3-cave-autre", "custom_files_upload")   # 3 niveaux : carte -> base -> amont
    verifie(chemins(e), ["tasmota/berry/modules/Partition_Manager.tapp",
                         "tasmota/berry/modules/Partition_Wizard/partition_wizard.bec",
                         "data/garage/tasmota32s3-carte"], "resout_cascade_env : no_files ignore, ordre garde")
    verifie([x.fichier for x in e], ["platformio_tasmota_env32.ini", fbi.FICHIER_CENV, fbi.FICHIER_CENV],
            "resout_cascade_env : fichier de chaque ligne")
    # option heritee par extends, sans reference : la ligne est ecrite dans la base
    e = fbi.resout(ini, "tasmota32s3-cave-autre", "custom_files_exclude")
    verifie([(x.chemin, x.section) for x in e], [("data/fs/x.be", "env:tasmota32s3-base")],
            "resout_cascade_env : option heritee par extends")
    verifie(fbi.resout(ini, "tasmota32s3-base", "option_absente"), [], "resout : option absente -> []")


def test_resout_commentaire_entre_lignes(racine):
    ini = fbi.lit_sections(racine)
    e = fbi.resout(ini, "tasmota32s3-base", "custom_files_upload")
    verifie(chemins(e)[-1], "tasmota/berry/modules/Partition_Wizard/partition_wizard.bec",
            "commentaire plein entre deux lignes : la continuation reste dans l'option")


def test_lecture_commentaire_en_ligne(racine):
    ini = fbi.lit_sections(racine)
    e = fbi.resout(ini, "tasmota32s3-garage-carte", "custom_berry_solidify")[-1]
    verifie(e.chemin, "data/garage/tasmota32s3-carte/controleCarte.be", "commentaire en ligne : chemin sans commentaire")
    verifie(e.commentaire, "raison (2026-10-25)", "commentaire en ligne : texte garde")


def test_resout_cycle(racine):
    ini = fbi.lit_sections(racine)
    try:
        fbi.resout(ini, "tasmota32s3-cave-boucle", "custom_files_exclude")
        verifie("pas d'exception", "ValueError", "resout_cycle")
    except ValueError:
        verifie(True, True, "resout_cycle : ValueError")
    verifie(fbi.lit_sections(racine).chaine("tasmota32s3-cave-boucle"), ["env:tasmota32s3-cave-boucle"],
            "chaine : extends sur soi-meme sans boucle infinie")


def test_envs_touches(racine):
    ini = fbi.lit_sections(racine)
    verifie(fbi.envs_touches(ini, "berry_commun", "socle", "custom_berry_solidify"),
            ["tasmota32s3-base", "tasmota32s3-cave-autre", "tasmota32s3-cave-boucle2", "tasmota32s3-garage-carte"],
            "envs_touches socle (boucle2 herite du socle par sa base)")
    verifie(fbi.envs_touches(ini, "berry_commun", "modbus", "custom_berry_solidify"),
            ["tasmota32s3-cave-autre", "tasmota32s3-garage-carte"], "envs_touches modbus")
    # option d'une base heritee par extends : la base et ses filles (les boucles sont ignorees)
    verifie(fbi.envs_touches(ini, "env:tasmota32s3-base", "custom_files_exclude", "custom_files_exclude"),
            ["tasmota32s3-base", "tasmota32s3-cave-autre", "tasmota32s3-garage-carte"], "envs_touches option de base")
    verifie(fbi.lit_sections(racine).envs_cenv(),
            ["tasmota32s3-base", "tasmota32s3-garage-carte", "tasmota32s3-cave-autre", "tasmota32s3-cave-boucle",
             "tasmota32s3-cave-boucle2"], "envs_cenv : ordre du fichier")


def test_vrais_fichiers():
    ini = fbi.lit_sections(RACINE)
    e = fbi.resout(ini, "tasmota32p4-garage-serveur-modbus", "custom_berry_solidify")
    udp = [x for x in e if x.chemin == "data/fs/udpFonctions.be"]
    verifie([x.section for x in udp], ["berry_commun"], "vrais fichiers : udpFonctions du P4 vient de berry_commun")
    up = chemins(fbi.resout(ini, "tasmota32p4-garage-serveur-modbus", "custom_files_upload"))
    verifie("data/garage/tasmota32p4-serveur-modbus" in up, True, "vrais fichiers : dossier du P4 dans custom_files_upload")


def principal():
    with tempfile.TemporaryDirectory() as t:
        racine = depot_essai(t)
        for test in (test_resout_socle_et_propre, test_resout_cascade_env, test_resout_commentaire_entre_lignes,
                     test_lecture_commentaire_en_ligne, test_resout_cycle, test_envs_touches):
            try:
                test(racine)
            except Exception as exc:                       # un test qui plante est un echec, pas un arret
                verifie(repr(exc), "pas d'exception", test.__name__)
    try:
        test_vrais_fichiers()
    except Exception as exc:
        verifie(repr(exc), "pas d'exception", "test_vrais_fichiers")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
