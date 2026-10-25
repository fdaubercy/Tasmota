"""Banc de fichiers_berry_ecriture (changements d'etat, diff, ecriture du cenv).

Code de sortie 0 = vert. Chaque test travaille sur un depot d'essai neuf (CRLF, comme le vrai cenv) ;
le vrai platformio_tasmota_cenv.ini n'est jamais ecrit. `relu_par_platformio` relit le cenv ecrit avec
ProjectConfig de PlatformIO (lancer ce banc avec le Python du penv).
"""

import os
import re
import sys
import tempfile
from pathlib import Path

import fichiers_berry_ecriture as fbw
import fichiers_berry_ini as fbi
from fichiers_berry_ecriture import Demande

ECHECS = []

ENV = """\
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

[env:tasmota32s3-base]
extends                 = env:tasmota32s3
custom_files_upload     = ${env:tasmota32s3.custom_files_upload}
custom_files_exclude    = data/fs/x.be
custom_berry_solidify   = ${berry_commun.socle}

; LoRaWan non charge par cette carte : loRaWanFonctions reste hors du FS.
[env:tasmota32s3-garage-carte]
extends                 = env:tasmota32s3-base
custom_berry_solidify   =   ${berry_commun.socle}
custom_files_exclude_solidified = ON
; loRaWanFonctions : non charge par cette carte (ligne commentee dans son autoexec).
custom_files_exclude    =   data/fs/loRaWanFonctions.be   ; essai (2026-10-01)
                            data/fs/b.be
custom_files_upload     =   ${env:tasmota32s3-base.custom_files_upload}
                            data/garage/tasmota32s3-carte

[env:tasmota32s3-cave-fille]
extends                 = env:tasmota32s3-base
custom_files_upload     =   ${env:tasmota32s3-base.custom_files_upload}
                            data/cave/tasmota32s3-fille

[env:tasmota32s3-cave-nue]
extends                 = env:tasmota32s3
"""

FICHIERS = ["data/fs/a.be", "data/fs/b.be", "data/fs/x.be", "data/fs/loRaWanFonctions.be", "data/fs/y.be",
            "data/garage/tasmota32s3-carte/autoexec.be", "data/cave/tasmota32s3-fille/autoexec.be",
            "tasmota/berry/modules/Partition_Manager.tapp", "tasmota/berry/modules/Webui_Status.tapp"]
SANS_BUILD = lambda: []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def depot_essai(dossier, cenv=CENV):
    racine = Path(dossier)
    (racine / "platformio_tasmota_env32.ini").write_bytes(ENV.replace("\n", "\r\n").encode("utf-8"))
    (racine / fbi.FICHIER_CENV).write_bytes(cenv.replace("\n", "\r\n").encode("utf-8"))
    for f in FICHIERS:
        (racine / f).parent.mkdir(parents=True, exist_ok=True)
        (racine / f).write_text("# essai\n", encoding="utf-8")
    return racine


def cenv(racine):
    return (racine / fbi.FICHIER_CENV).read_bytes().decode("utf-8")


def liste(racine, env, option):
    return [e.chemin for e in fbi.resout(fbi.lit_sections(racine), env, option)]


def ecrit(racine, env, demandes):
    p = fbw.prepare(racine, env, demandes)
    return fbw.enregistre(racine, env, demandes, p["empreinte"], SANS_BUILD)


def test_ecriture_ajout_exclu(racine):
    ecrit(racine, "tasmota32s3-garage-carte", [Demande("data/fs/y.be", "exclu")])
    verifie(liste(racine, "tasmota32s3-garage-carte", "custom_files_exclude"),
            ["data/fs/loRaWanFonctions.be", "data/fs/b.be", "data/fs/y.be"], "ajout exclu : en fin de liste propre")
    verifie("                            data/fs/y.be\r\n" in cenv(racine), True, "ajout exclu : indentation des voisines")


def test_ecriture_option_heritee(racine):
    p = fbw.prepare(racine, "tasmota32s3-cave-fille", [Demande("data/fs/y.be", "exclu")])
    verifie(p["confirmations"], [], "option heritee : un ajout ne demande pas de confirmation")
    fbw.enregistre(racine, "tasmota32s3-cave-fille", [Demande("data/fs/y.be", "exclu")], p["empreinte"], SANS_BUILD)
    verifie(liste(racine, "tasmota32s3-cave-fille", "custom_files_exclude"), ["data/fs/x.be", "data/fs/y.be"],
            "option heritee : l'heritage de la base est garde")
    verifie("${env:tasmota32s3-base.custom_files_exclude}" in cenv(racine), True, "option heritee : reference ecrite")
    verifie(liste(racine, "tasmota32s3-base", "custom_files_exclude"), ["data/fs/x.be"], "option heritee : base intacte")


def test_ecriture_option_absente(racine):
    ecrit(racine, "tasmota32s3-cave-fille", [Demande("data/fs/y.be", "solidifie")])
    verifie(liste(racine, "tasmota32s3-cave-fille", "custom_berry_solidify"),
            ["data/fs/a.be", "data/fs/b.be", "data/fs/y.be"], "solidifie sur option heritee de la base : socle garde")
    ecrit(racine, "tasmota32s3-cave-nue", [Demande("data/fs/y.be", "exclu"), Demande("data/fs/x.be", "exclu")])
    verifie(liste(racine, "tasmota32s3-cave-nue", "custom_files_exclude"), ["data/fs/y.be", "data/fs/x.be"],
            "option absente partout : creee une seule fois, avec les deux fichiers")
    verifie(cenv(racine).count("custom_files_exclude    "), 3, "option absente : une seule ligne `option =` ajoutee")


def test_ecriture_partage_confirme(racine):
    avant = cenv(racine)
    d = [Demande("data/fs/a.be", "fs")]
    p = fbw.prepare(racine, "tasmota32s3-garage-carte", d)
    verifie([(c["chemin"], c["section"], c["option"], c["envs"]) for c in p["confirmations"]],
            [("data/fs/a.be", "berry_commun", "socle",
              ["tasmota32s3-base", "tasmota32s3-cave-fille", "tasmota32s3-garage-carte"])],
            "partage : confirmation avec les envs touches")
    try:
        fbw.enregistre(racine, "tasmota32s3-garage-carte", d, p["empreinte"], SANS_BUILD)
        verifie("ecrit", "refus", "partage sans accord : refus")
    except RuntimeError:
        verifie(cenv(racine), avant, "partage sans accord : cenv inchange")
    ecrit(racine, "tasmota32s3-garage-carte", [Demande("data/fs/a.be", "fs", partage_accepte=True)])
    verifie(liste(racine, "tasmota32s3-cave-fille", "custom_berry_solidify"), ["data/fs/b.be"],
            "partage accepte : retire de [berry_commun], donc de tous les envs")


def test_ecriture_refuse_amont(racine):
    p = fbw.prepare(racine, "tasmota32s3-garage-carte", [Demande("tasmota/berry/modules/Partition_Manager.tapp",
                                                                  "absent", partage_accepte=True)])
    verifie(len(p["refus"]), 1, "amont : retirer une ligne de l'amont est refuse")
    verifie(p["diff"], "", "amont : aucun diff")
    ecrit(racine, "tasmota32s3-base", [Demande("tasmota/berry/modules/Webui_Status.tapp", "fs")])
    verifie(liste(racine, "tasmota32s3-base", "custom_files_upload"),
            ["tasmota/berry/modules/Partition_Manager.tapp", "tasmota/berry/modules/Webui_Status.tapp"],
            "amont : ajout dans l'option propre de la base")


def test_ecriture_retire_ligne_commentee(racine):
    ecrit(racine, "tasmota32s3-garage-carte", [Demande("data/fs/loRaWanFonctions.be", "fs")])
    t = cenv(racine)
    verifie("essai (2026-10-01)" in t, False, "retrait de la 1re ligne : son commentaire en ligne part avec elle")
    verifie(liste(racine, "tasmota32s3-garage-carte", "custom_files_exclude"), ["data/fs/b.be"],
            "retrait de la 1re ligne : la suite de la liste reste")
    verifie(re.search(r"^custom_files_exclude\s+=\s*\r\n\s+data/fs/b.be", t, re.M) is not None, True,
            "retrait de la 1re ligne : `option =` garde, valeur sur la continuation")


def test_ecriture_doublon_partage(racine):
    p = fbw.prepare(racine, "tasmota32s3-garage-carte", [Demande("data/fs/b.be", "exclu")])
    verifie([c["option"] for c in p["confirmations"]], ["socle"], "doublon : retrait du socle a confirmer")
    ecrit(racine, "tasmota32s3-garage-carte", [Demande("data/fs/b.be", "exclu", partage_accepte=True)])
    verifie((liste(racine, "tasmota32s3-garage-carte", "custom_berry_solidify"),
             liste(racine, "tasmota32s3-garage-carte", "custom_files_exclude").count("data/fs/b.be")),
            (["data/fs/a.be"], 1), "doublon : retire du socle, garde une seule fois en exclu")


def test_ecriture_garde_commentaires(racine):
    avant = [l for l in cenv(racine).split("\r\n") if l.lstrip().startswith(";")]
    ecrit(racine, "tasmota32s3-garage-carte", [Demande("data/fs/b.be", "fs", partage_accepte=True),
                                               Demande("data/fs/y.be", "exclu")])
    apres = [l for l in cenv(racine).split("\r\n") if l.lstrip().startswith(";")]
    verifie(apres, avant, "commentaires pleins tous gardes, dans l'ordre")


def test_ecriture_crlf(racine):
    ecrit(racine, "tasmota32s3-cave-fille", [Demande("data/fs/y.be", "exclu", raison="essai")])
    octets = (racine / fbi.FICHIER_CENV).read_bytes()
    verifie(octets.count(b"\n"), octets.count(b"\r\n"), "CRLF : aucune fin de ligne LF nue")
    verifie(octets.endswith(b"\r\n"), True, "CRLF : derniere fin de ligne gardee")


def test_ecriture_raison(racine):
    ecrit(racine, "tasmota32s3-garage-carte", [Demande("data/fs/y.be", "exclu", raison="trop gros")])
    ligne = next(l for l in cenv(racine).split("\r\n") if "data/fs/y.be" in l)
    verifie(re.search(r"data/fs/y\.be\s+; trop gros \(\d{4}-\d{2}-\d{2}\)$", ligne) is not None, True,
            "raison : commentaire de fin de ligne date")
    verifie(next(e for e in fbi.resout(fbi.lit_sections(racine), "tasmota32s3-garage-carte", "custom_files_exclude")
                 if e.chemin == "data/fs/y.be").commentaire[:9], "trop gros", "raison : relue comme commentaire")


def test_commentaires_cites(racine):
    p = fbw.prepare(racine, "tasmota32s3-garage-carte", [Demande("data/fs/loRaWanFonctions.be", "fs")])
    verifie([c["texte"] for c in p["commentaires_cites"]],
            ["; loRaWanFonctions : non charge par cette carte (ligne commentee dans son autoexec)."],
            "commentaires cites : celui de la section (pas celui d'une autre section)")


def test_refus_build(racine):
    d = [Demande("data/fs/y.be", "exclu")]
    for builds, libelle in ((lambda: ["pio run -e x"], "liste"), (lambda: None, "None")):
        p = fbw.prepare(racine, "tasmota32s3-garage-carte", d)
        try:
            fbw.enregistre(racine, "tasmota32s3-garage-carte", d, p["empreinte"], builds)
            verifie("ecrit", "refus", f"build en cours ({libelle}) : refus")
        except RuntimeError:
            verifie("data/fs/y.be" in cenv(racine), False, f"build en cours ({libelle}) : refus, cenv inchange")


def test_refus_empreinte(racine):
    d = [Demande("data/fs/y.be", "exclu")]
    p = fbw.prepare(racine, "tasmota32s3-garage-carte", d)
    (racine / fbi.FICHIER_CENV).write_bytes((racine / fbi.FICHIER_CENV).read_bytes() + b"; touche\r\n")
    try:
        fbw.enregistre(racine, "tasmota32s3-garage-carte", d, p["empreinte"], SANS_BUILD)
        verifie("ecrit", "refus", "empreinte perimee : refus")
    except RuntimeError:
        verifie("data/fs/y.be" in cenv(racine), False, "empreinte perimee : refus, cenv inchange")


def test_bak_et_diff(racine):
    avant = (racine / fbi.FICHIER_CENV).read_bytes()
    p = fbw.prepare(racine, "tasmota32s3-garage-carte", [Demande("data/fs/y.be", "exclu")])
    verifie("+                            data/fs/y.be" in p["diff"], True, "diff unifie : ligne ajoutee")
    ecrit(racine, "tasmota32s3-garage-carte", [Demande("data/fs/y.be", "exclu")])
    verifie((racine / (fbi.FICHIER_CENV + ".bak")).read_bytes(), avant, ".bak = cenv d'avant")


def test_demandes_invalides(racine):
    for d, attendu, libelle in (([Demande("data/fs/inconnu.be", "exclu")], LookupError, "fichier inconnu"),
                                ([Demande("data/garage/tasmota32s3-carte/autoexec.be", "solidifie")], ValueError,
                                 "autoexec fige"),
                                ([Demande("tasmota/berry/modules/Webui_Status.tapp", "solidifie")], ValueError,
                                 "amont non solidifiable")):
        try:
            fbw.prepare(racine, "tasmota32s3-garage-carte", d)
            verifie("accepte", attendu.__name__, libelle)
        except attendu:
            verifie(True, True, f"{libelle} : {attendu.__name__}")


def test_relu_par_platformio(racine):
    ecrit(racine, "tasmota32s3-garage-carte", [Demande("data/fs/b.be", "fs", partage_accepte=True),
                                               Demande("data/fs/y.be", "exclu", raison="essai")])
    from platformio.project.config import ProjectConfig
    (racine / "platformio.ini").write_text("[platformio]\nextra_configs = platformio_tasmota_env32.ini\n"
                                           "    " + fbi.FICHIER_CENV + "\n", encoding="utf-8")
    ici = os.getcwd()
    os.chdir(racine)
    try:
        conf = ProjectConfig(str(racine / "platformio.ini"))
        for option in ("custom_berry_solidify", "custom_files_exclude", "custom_files_upload"):
            brut = conf.get("env:tasmota32s3-garage-carte", option)
            lu = [fbi.normalise(x.strip()) for x in (brut.splitlines() if isinstance(brut, str) else brut)]
            verifie([x for x in lu if x and x != "no_files"], liste(racine, "tasmota32s3-garage-carte", option),
                    f"relu par PlatformIO : {option} identique a resout")
    finally:
        os.chdir(ici)


def principal():
    for test in (test_ecriture_ajout_exclu, test_ecriture_option_heritee, test_ecriture_option_absente,
                 test_ecriture_partage_confirme, test_ecriture_refuse_amont, test_ecriture_retire_ligne_commentee,
                 test_ecriture_doublon_partage, test_ecriture_garde_commentaires, test_ecriture_crlf,
                 test_ecriture_raison, test_commentaires_cites, test_refus_build, test_refus_empreinte,
                 test_bak_et_diff, test_demandes_invalides, test_relu_par_platformio):
        with tempfile.TemporaryDirectory() as t:
            try:
                test(depot_essai(t))
            except Exception as exc:
                verifie(repr(exc), "pas d'exception", test.__name__)
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
