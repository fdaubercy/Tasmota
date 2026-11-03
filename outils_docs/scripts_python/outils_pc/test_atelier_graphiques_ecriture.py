"""Banc de atelier_graphiques_ecriture (description, ligne d'autoexec et listes du cenv, plan A6).

Code de sortie 0 = vert. Lancer avec le Python de PlatformIO (ProjectConfig) depuis la racine du depot :
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_graphiques_ecriture.py
Chaque test travaille sur une COPIE temporaire : les .ini du vrai depot (cenv compris, avec ses commentaires),
l'autoexec de la cuve (avec historique) et du differentiel (sans historique), et un faux autoexec pour
tasmota32-rdc-vr-porte (exclusion heritee de sa base, pas de custom_files_exclude_solidified). Le vrai depot n'est
jamais ecrit ; les sauvegardes de Transaction vont dans un dossier temporaire (OUTILS_TASMOTA_DOSSIER).
"""

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import atelier_graphiques_ecriture as age
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
import fichiers_berry_sauvegarde as fbs

DEPOT = Path(fbi.__file__).resolve().parents[3]
INIS = ("platformio.ini", "platformio_tasmota32.ini", "platformio_tasmota_env.ini", "platformio_tasmota_env32.ini",
        "platformio_override.ini", fbi.FICHIER_CENV)
CUVE, BUREAU, PORTE = ("tasmota32s3-garage-capteurs-cuve-modbus", "tasmota32-bureau-interrupteur-energie",
                       "tasmota32-rdc-vr-porte")
AUTOEXEC_PORTE = "import demarrage\nif demarrage.prologue()\n    demarrage.charge([\"controleWeb\"])\nend\n"
NOMS = {Path(f).name for f in age.FICHIERS_MOTEUR}
SANS_BUILD = lambda: []
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def refuse(appel, exception, libelle, motif=""):
    try:
        appel()
    except exception as e:
        if motif in str(e):
            print("OK   " + libelle + f"  ({e})")
            return
        print("KO   " + libelle + f"  (motif {motif!r} absent de : {e})")
        ECHECS.append(libelle)
        return
    print("KO   " + libelle + "  (pas de refus)")
    ECHECS.append(libelle)


def description(style="cadran", titre="Volume"):
    return {"version": 1, "pages": [{"id": "tableau-cuve", "titre": "Cuve", "graphiques": [
        {"type": style, "titre": titre, "series": ["sensorsCuve.niveauCuve.volume"], "min": 0, "max": 6732}]}]}


def copie(dossier):
    racine = Path(dossier)
    for f in INIS:
        shutil.copy2(DEPOT / f, racine / f)
    for env in (CUVE, BUREAU):
        d = racine / fbe.dossier_carte(env)
        d.mkdir(parents=True)
        shutil.copy2(DEPOT / fbe.dossier_carte(env) / "autoexec.be", d / "autoexec.be")
    d = racine / fbe.dossier_carte(PORTE)
    d.mkdir(parents=True)
    (d / "autoexec.be").write_bytes(AUTOEXEC_PORTE.encode("utf-8"))
    p = age.prevoit_exclusions(racine)          # etat de depart : moteur exclu de tous les envs
    if p["fichiers"]:
        age.ecrit_exclusions(racine, p["empreinte"], SANS_BUILD)
    return racine


def instantane(racine):
    return {p.relative_to(racine).as_posix(): p.read_bytes() for p in sorted(racine.rglob("*")) if p.is_file()}


def meme_etat(racine, etat, libelle):
    """Copie identique octet pour octet a `etat` ; en cas d'ecart, seuls les chemins differents sont affiches."""
    maintenant = instantane(racine)
    ecarts = sorted(k for k in set(etat) | set(maintenant) if etat.get(k) != maintenant.get(k))
    verifie(ecarts, [], libelle)


def exclus(racine, env):
    return NOMS & {Path(e.chemin).name for e in fbi.resout(fbi.lit_sections(racine), env, fbe.EXCLUDE)}


def ecrit(racine, env, desc, solidifier=False):
    p = age.prevoit(racine, env, desc, solidifier)
    return age.ecrit(racine, env, desc, solidifier, p["empreinte"], SANS_BUILD)


def relu_par_platformio(racine, env, option):
    """Valeur de l'option lue par ProjectConfig, os.chdir dans la copie (lecon du 2026-11-01 : sinon extra_configs
    est resolu depuis le vrai depot)."""
    from platformio.project.config import ProjectConfig
    ici = os.getcwd()
    os.chdir(racine)
    try:
        conf = ProjectConfig(str(racine / "platformio.ini"))
        verifie(Path(conf.path).resolve().parent, racine.resolve(), "ProjectConfig lit bien la copie")
        brut = conf.get("env:" + env, option)
    finally:
        os.chdir(ici)
    lignes = brut.splitlines() if isinstance(brut, str) else list(brut)
    return {Path(fbi.normalise(x.strip())).name for x in lignes if x.strip()}


def test_exclusions(racine):
    envs = [e["nom"] for e in fbe.envs_proposes(racine)]
    verifie([e for e in envs if exclus(racine, e) != NOMS], [], "exclusions : les 6 fichiers exclus de tous les envs ESP32")
    verifie(age.prevoit_exclusions(racine)["fichiers"], [], "exclusions : une 2e passe ne change rien")
    for env in (CUVE, PORTE, "tasmota32-base"):
        verifie(NOMS <= relu_par_platformio(racine, env, fbe.EXCLUDE), True, f"exclusions relues par PlatformIO : {env}")


def test_premiere_page(racine):
    avant = (racine / fbi.FICHIER_CENV).read_text(encoding="utf-8")
    p = age.prevoit(racine, CUVE, description(), False)
    dossier = fbe.dossier_carte(CUVE)
    verifie(sorted(f["chemin"] for f in p["fichiers"]),
            sorted([fbi.FICHIER_CENV, dossier + "/autoexec.be", dossier + "/pages_graphiques.json"]),
            "1re page : cenv, autoexec et description")
    ecrits = age.ecrit(racine, CUVE, description(), False, p["empreinte"], SANS_BUILD)
    verifie(len(ecrits), 3, "1re page : 3 fichiers ecrits")
    verifie(exclus(racine, CUVE), set(), "1re page : la cuve embarque le moteur")
    verifie(exclus(racine, BUREAU), NOMS, "1re page : le differentiel l'exclut toujours")
    verifie(exclus(racine, PORTE), NOMS, "1re page : la porte l'exclut toujours")
    verifie(relu_par_platformio(racine, CUVE, fbe.EXCLUDE) & NOMS, set(), "1re page relue par PlatformIO : cuve sans exclusion")
    verifie(NOMS <= relu_par_platformio(racine, BUREAU, fbe.EXCLUDE), True, "1re page relue par PlatformIO : differentiel exclu")
    verifie(NOMS <= relu_par_platformio(racine, "tasmota32s3-garage-rideau-garage-modbus", fbe.EXCLUDE), True,
            "1re page relue par PlatformIO : rideau exclu")
    lignes = (racine / dossier / "autoexec.be").read_text(encoding="utf-8").splitlines()
    i = next(k for k, l in enumerate(lignes) if l.strip().startswith("demarrage.historique()"))
    verifie(lignes[i + 1], "    " + age.LIGNE_AUTOEXEC, "1re page : ligne d'autoexec juste apres historique()")
    verifie(json.loads((racine / dossier / "pages_graphiques.json").read_text(encoding="utf-8")), description(),
            "1re page : description ecrite telle quelle")
    commentaires = lambda t: [l for l in t.splitlines() if l.strip()[:1] in (";", "#")]
    apres = (racine / fbi.FICHIER_CENV).read_text(encoding="utf-8")
    verifie(commentaires(apres), commentaires(avant), "1re page : commentaires du cenv gardes, dans l'ordre")
    verifie("firmware a recompiler" in " ".join(p["signaux"]), False, "1re page non solidifiee : pas de firmware a recompiler")


def test_deuxieme_modification(racine):
    ecrit(racine, CUVE, description())
    p = age.prevoit(racine, CUVE, description(titre="Volume d'eau"), False)
    verifie([f["chemin"] for f in p["fichiers"]], [fbe.dossier_carte(CUVE) + "/pages_graphiques.json"],
            "2e modification : seule la description change")
    verifie(age.prevoit(racine, CUVE, description(), False)["fichiers"], [], "meme description : rien a ecrire")


def test_derniere_page(racine):
    etat = instantane(racine)
    ecrit(racine, CUVE, description())
    ecrit(racine, CUVE, None)
    meme_etat(racine, etat, "derniere page retiree : etat exclu retrouve octet pour octet")


def test_exclusion_heritee(racine):
    etat = instantane(racine)
    ecrit(racine, PORTE, description())
    verifie(exclus(racine, PORTE), set(), "exclusion heritee : la porte embarque le moteur")
    verifie(exclus(racine, "tasmota32-base"), NOMS, "exclusion heritee : la base l'exclut toujours")
    verifie(exclus(racine, "tasmota32-cave-serveur-rly"), NOMS, "exclusion heritee : les autres cartes de la base aussi")
    pio = relu_par_platformio(racine, PORTE, fbe.EXCLUDE)
    verifie((pio & NOMS, "cuvePageFonctions.be" in pio), (set(), True),
            "exclusion heritee relue par PlatformIO : moteur leve, page_cuve toujours exclue")
    ecrit(racine, PORTE, None)
    meme_etat(racine, etat, "exclusion heritee : retrait octet pour octet")


def test_sans_historique(racine):
    ecrit(racine, BUREAU, description())
    lignes = (racine / fbe.dossier_carte(BUREAU) / "autoexec.be").read_text(encoding="utf-8").splitlines()
    i = next(k for k, l in enumerate(lignes) if l.strip() == age.LIGNE_AUTOEXEC)
    verifie(lignes[i + 1].rstrip(), "end", "sans historique : ligne en fin de bloc prologue")


def test_liquide(racine):
    etat = instantane(racine)
    refuse(lambda: age.prevoit(racine, BUREAU, description("liquide"), False), ValueError,
           "liquide refuse sur un env qui exclut liquidfill")
    meme_etat(racine, etat, "liquide refuse : rien d'ecrit")
    verifie(len(age.prevoit(racine, CUVE, description("liquide"), False)["fichiers"]), 3, "liquide accepte sur la cuve")


def test_solidifie(racine):
    etat = instantane(racine)
    p = age.prevoit(racine, CUVE, description(), True)
    age.ecrit(racine, CUVE, description(), True, p["empreinte"], SANS_BUILD)
    solides = {Path(e.chemin).name for e in fbi.resout(fbi.lit_sections(racine), CUVE, fbe.SOLIDIFY)}
    verifie({"pagesGraphiques.be", "pagesGraphiquesValidation.be"} <= solides, True, "solidifie : moteur au solidify")
    verifie({"pagesGraphiques.be", "pagesGraphiquesValidation.be"} <= relu_par_platformio(racine, CUVE, fbe.SOLIDIFY),
            True, "solidifie relu par PlatformIO")
    verifie("firmware a recompiler" in " ".join(p["signaux"]), True, "solidifie : firmware a recompiler signale")
    texte = (racine / fbe.dossier_carte(CUVE) / "autoexec.be").read_text(encoding="utf-8")
    verifie((age.LIGNE_AUTOEXEC in texte, "demarrage.importe([\"pagesGraphiques\"])" in texte), (True, False),
            "solidifie : ligne demarrage.charge, jamais importe")
    p = age.prevoit(racine, CUVE, description(), False)
    verifie(sorted(f["chemin"] for f in p["fichiers"]), [fbi.FICHIER_CENV], "solidification retiree : le cenv seul change")
    ecrit(racine, CUVE, description(), True)
    ecrit(racine, CUVE, None)
    meme_etat(racine, etat, "solidifie puis retire : octet pour octet")
    refuse(lambda: age.prevoit(racine, PORTE, description(), True), ValueError,
           "solidifie refuse sans custom_files_exclude_solidified = ON")


def test_build_en_cours(racine):
    etat = instantane(racine)
    p = age.prevoit(racine, CUVE, description(), False)
    refuse(lambda: age.ecrit(racine, CUVE, description(), False, p["empreinte"], lambda: ["pio run cuve"]), RuntimeError,
           "build en cours : refus")
    refuse(lambda: age.ecrit(racine, CUVE, description(), False, p["empreinte"], lambda: None), RuntimeError,
           "build indetectable : refus")
    meme_etat(racine, etat, "build en cours : rien d'ecrit")


def test_empreinte_perimee(racine):
    p = age.prevoit(racine, CUVE, description(), False)
    cenv = racine / fbi.FICHIER_CENV
    cenv.write_bytes(cenv.read_bytes() + b"; ajout de l'utilisateur\r\n")
    etat = instantane(racine)
    refuse(lambda: age.ecrit(racine, CUVE, description(), False, p["empreinte"], SANS_BUILD), RuntimeError,
           "cenv modifie apres le diff : refus")
    meme_etat(racine, etat, "empreinte perimee : copie inchangee octet pour octet")
    p = age.prevoit(racine, CUVE, description(), False)
    auto = racine / fbe.dossier_carte(CUVE) / "autoexec.be"
    auto.write_bytes(auto.read_bytes() + b"# ajout\n")
    etat = instantane(racine)
    refuse(lambda: age.ecrit(racine, CUVE, description(), False, p["empreinte"], SANS_BUILD), RuntimeError,
           "autoexec modifie apres le diff : refus")
    meme_etat(racine, etat, "autoexec modifie : copie inchangee octet pour octet")
    refuse(lambda: age.ecrit(racine, CUVE, description("aire"), False, p["empreinte"], SANS_BUILD), RuntimeError,
           "description changee apres le diff : refus")


def test_exception_au_milieu(racine):
    etat = instantane(racine)
    vrai, appels = fbs._remplace, []

    def casse(chemin, octets):
        if chemin.name != fbs.MARQUE:
            appels.append(chemin.name)
            if len(appels) == 2:
                raise OSError("disque plein (simule)")
        vrai(chemin, octets)
    fbs._remplace = casse
    try:
        refuse(lambda: ecrit(racine, CUVE, description()), OSError, "exception au 2e fichier : remontee")
    finally:
        fbs._remplace = vrai
    meme_etat(racine, etat, "exception au milieu : tout est annule")


def edite_exclusion_cuve(racine, change):
    """Exclusion de la cuve editee « a la main » dans la copie : change(lignes de la section, indice de la ligne REF)."""
    cenv = racine / fbi.FICHIER_CENV
    texte = cenv.read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in texte else "\n"
    lignes = texte.split(eol)
    debut = lignes.index(f"[env:{CUVE}]")
    fin = next((i for i in range(debut + 1, len(lignes)) if lignes[i].startswith("[")), len(lignes))
    i = next(i for i in range(debut, fin) if lignes[i].strip() == age.REF)
    cenv.write_bytes(eol.join(lignes[:debut] + change(lignes[debut:fin], i - debut) + lignes[fin:]).encode("utf-8"))


def test_exclusion_a_la_main(racine):
    def literale(s, i):                              # les 6 chemins ecrits a la place de la liste
        indent = s[i][:len(s[i]) - len(s[i].lstrip())]
        return s[:i] + [indent + f for f in age.FICHIERS_MOTEUR] + s[i + 1:]
    edite_exclusion_cuve(racine, literale)
    etat = instantane(racine)
    refuse(lambda: age.prevoit(racine, CUVE, description(), False), ValueError,
           "exclusion ecrite sans la liste : refus", "introuvable")
    meme_etat(racine, etat, "exclusion ecrite sans la liste : rien d'ecrit")


def test_reference_sur_la_ligne_option(racine):
    def en_tete(s, i):                               # REF sur la ligne `custom_files_exclude =`, suivie d'autres valeurs
        o = next(k for k, l in enumerate(s) if l.split("=", 1)[0].strip() == fbe.EXCLUDE)
        valeur = s[o].split("=", 1)[1]
        decalage = len(s[o]) - len(valeur.lstrip())
        s = s[:i] + s[i + 1:]
        return s[:o] + [s[o][:decalage] + age.REF, " " * decalage + valeur.strip()] + s[o + 1:]
    edite_exclusion_cuve(racine, en_tete)
    etat = instantane(racine)
    refuse(lambda: age.prevoit(racine, CUVE, description(), False), ValueError,
           "liste sur la ligne de l'option : refus", "sur la ligne custom_files_exclude")
    meme_etat(racine, etat, "liste sur la ligne de l'option : rien d'ecrit")


def test_controle_refuse(racine):
    def doublon(s, i):                               # un fichier du moteur exclu aussi a la main
        return s[:i + 1] + [s[i].replace(age.REF, age.FICHIERS_MOTEUR[0])] + s[i + 1:]
    edite_exclusion_cuve(racine, doublon)
    etat = instantane(racine)
    refuse(lambda: age.prevoit(racine, CUVE, description(), False), ValueError,
           "moteur encore exclu apres la levee : refus du controle", "toujours exclu")
    meme_etat(racine, etat, "controle en echec : rien d'ecrit")


def test_annulation_suppression(racine):
    ecrit(racine, CUVE, description())
    etat = instantane(racine)
    vrai, appels = fbs._remplace, []

    def casse(chemin, octets):                       # ordre : autoexec, description SUPPRIMEE, puis cenv -> echec
        if chemin.name != fbs.MARQUE:
            appels.append(chemin.name)
            if chemin.name == fbi.FICHIER_CENV and len(appels) == 2:
                raise OSError("disque plein (simule)")
        vrai(chemin, octets)
    fbs._remplace = casse
    try:
        refuse(lambda: ecrit(racine, CUVE, None), OSError, "retrait : exception apres la suppression de la description")
    finally:
        fbs._remplace = vrai
    verifie(appels[:2], ["autoexec.be", fbi.FICHIER_CENV], "retrait : l'echec tombe bien apres la suppression")
    meme_etat(racine, etat, "retrait annule : description remise, tout restaure octet pour octet")


def test_invalide(racine):
    refuse(lambda: age.prevoit(racine, CUVE, {"version": 2, "pages": []}, False), ValueError, "description invalide : refus")
    refuse(lambda: age.prevoit(racine, "tasmota32-base", description(), False), LookupError, "env de base : refus")


TESTS = [test_exclusions, test_premiere_page, test_deuxieme_modification, test_derniere_page, test_exclusion_heritee,
         test_sans_historique, test_liquide, test_solidifie, test_build_en_cours, test_empreinte_perimee,
         test_exception_au_milieu, test_exclusion_a_la_main, test_reference_sur_la_ligne_option, test_controle_refuse,
         test_annulation_suppression, test_invalide]


if __name__ == "__main__":
    for test in TESTS:
        print(f"--- {test.__name__}")
        with tempfile.TemporaryDirectory() as t:
            os.environ["OUTILS_TASMOTA_DOSSIER"] = os.path.join(t, "outils")
            racine = Path(t) / "depot"
            racine.mkdir()
            try:
                test(copie(racine))
            except Exception as e:                                  # un test qui plante est un echec, pas un arret
                print(f"KO   {test.__name__} : {type(e).__name__} : {e}")
                ECHECS.append(test.__name__)
    print(f"\n{len(ECHECS)} echec(s)" + (" : " + ", ".join(ECHECS) if ECHECS else " : VERT"))
    sys.exit(1 if ECHECS else 0)
