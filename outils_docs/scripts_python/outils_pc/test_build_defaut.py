#!/usr/bin/env python3
"""Banc de build_defaut.py (plan default-envs-page, A2) : faux depot temporaire pour les octets exacts, COPIE des vrais
platformio*.ini relue par ProjectConfig (le vrai depot n'est jamais ecrit), vraies fonctions du pre-script extraites de
son source. Sauvegardes dans un dossier temporaire (OUTILS_TASMOTA_DOSSIER). Puis chaque mutant de build_defaut.py doit
faire echouer au moins un cas.

    <Python de PlatformIO> outils_docs/scripts_python/outils_pc/test_build_defaut.py

Code de sortie 0 = vert, 1 = rouge.
"""
import ast
import os
import re
import shutil
import sys
import tempfile
import types
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
DEPOT = ICI.parents[2]
SOURCE = (ICI / "build_defaut.py").read_text(encoding="utf-8")
PRE_SCRIPT = ICI.parent / "build" / "pre_utilitaires_platformio.py"
S3_A, S3_B, S3_C = "tasmota32s3-garage-a", "tasmota32s3-garage-b", "tasmota32s3-garage-absent"
P4_A, BASE = "tasmota32p4-garage-a", "tasmota32s3-base-x"
OVERRIDE = (
    "; tete\r\n[platformio]\r\ndata_dir = data/garage/tasmota32s3-a\r\n\r\ndefault_envs            =\r\n"
    "; *** Safeboot\r\n                            ; tasmota32-safeboot       \r\n\r\n"
    "; *** ESP32S3\r\n"
    f"                            {S3_A}\r\n                            ; {S3_B}\r\n\t\r\n"
    "; *** ESP32P4   \r\n"
    f"                            ; {P4_A}\r\n                            ; ancien-env-disparu\r\n\r\n"
    "[tasmota]\r\n;build_flags =\r\n")
CENV = "".join(f"[env:{e}]\nextends = env:tasmota32_base\n\n" for e in (S3_A, S3_B, S3_C, P4_A, BASE))
ENV32 = "[env:tasmota32-safeboot]\nextends = env:tasmota32_base\n\n[env:tasmota32_base]\nboard = esp32\n"
MUTANTS = {
    "liste vide permise": ("if not coches:", "if False:"),
    "env inconnu permis": ("for c in coches if c not in connus]", "for c in coches if False]"),
    "empreinte ignoree": ('if p["empreinte"] != empreinte_lue:', "if False:"),
    "build ignore": ("    if builds:\n", "    if False:\n"),
    "detection impossible ignoree": ("if builds is None:", "if False:"),
    "absent ajoute meme non coche": ("for c in coches:\n            if c not in entrees:", "for c in [e.nom for e in envs]:\n            if c not in entrees:"),
    "ajout hors du groupe": ("return max(du_groupe) if du_groupe else", "return"),
    "fin de ligne perdue": ('"t": _bascule(lignes[i], m.group(3) in coches)', '"t": _bascule(lignes[i], m.group(3) in coches).rstrip()'),
    "commentaire traite comme env": ("(not m.group(2) or m.group(3) in connus)", "True"),
    "avertissement de purge retire": ('[] if inchange or erreurs else [PURGE]', "[]"),
}


def module(source):
    m = types.ModuleType("build_defaut_essai")
    exec(compile(source, "build_defaut.py", "exec"), m.__dict__)
    return m


def faux_depot(t, nom="depot", override=OVERRIDE):
    racine = Path(t) / nom
    racine.mkdir()
    (racine / "platformio_override.ini").write_bytes(override.encode("utf-8"))
    (racine / "platformio_tasmota_cenv.ini").write_text(CENV, encoding="utf-8")
    (racine / "platformio_tasmota_env32.ini").write_text(ENV32, encoding="utf-8")
    return racine


def fonctions_pre_script():
    """apply_rules_to_entire_file et ses aides, extraites du vrai pre-script (l'executer entier exigerait SCons)."""
    arbre = ast.parse(PRE_SCRIPT.read_text(encoding="utf-8"))
    espace = {"re": re}
    corps = [n for n in arbre.body if isinstance(n, ast.FunctionDef)]
    exec(compile(ast.Module(body=corps, type_ignores=[]), str(PRE_SCRIPT), "exec"), espace)
    return espace["apply_rules_to_entire_file"]


def cas(m):
    res = []

    def verifie(nom, ok):
        res.append((nom, bool(ok)))

    aucun_build = lambda: []
    with tempfile.TemporaryDirectory() as t:
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "outils")
        racine = faux_depot(t)
        chemin = racine / "platformio_override.ini"

        etat = m.lit(racine)
        verifie("lit : actif seul = la ligne non commentee", etat["actifs"] == [S3_A])
        groupes = {g["titre"]: g["envs"] for g in etat["groupes"]}
        verifie("lit : colonnes par puce", list(groupes) == ["Safeboot", "ESP32-S3", "ESP32-P4"])
        s3 = {e["nom"]: e for e in groupes["ESP32-S3"]}
        verifie("lit : absent du bloc signale, carte et base proposees", s3[S3_C]["absent"] and s3[BASE]["absent"] and not s3[S3_B]["absent"])
        verifie("lit : commentaire ou env disparu en commentaire pas pris pour un env",
                not any(e["nom"] in ("ancien-env-disparu", "ESP32S3", "Safeboot") for g in groupes.values() for e in g))
        verifie("lit : env amont du bloc montre, autres amont non", [e["nom"] for e in groupes["Safeboot"]] == ["tasmota32-safeboot"])
        verifie("lit : fichier actuel inchange, sans avertissement", etat["inchange"] and not etat["avertissements"])
        verifie("lit : apercu = fichier octet pour octet", "".join(a["t"] for a in etat["apercu"]) == OVERRIDE)

        p = m.prepare(racine, [S3_B, P4_A])
        verifie("prepare : rien n'est ecrit", chemin.read_bytes() == OVERRIDE.encode("utf-8"))
        attendu = OVERRIDE.replace(f"                            {S3_A}\r\n", f"                            ; {S3_A}\r\n") \
                          .replace(f"; {S3_B}\r\n", f"{S3_B}\r\n").replace(f"; {P4_A}\r\n", f"{P4_A}\r\n")
        verifie("prepare : seules les lignes visees changent (CRLF, retrait, commentaires gardes)", p["apres"] == attendu)
        verifie("prepare : lignes marquees modif", [a["t"].strip() for a in p["apercu"] if a["m"] == "modif"] == [f"; {S3_A}", S3_B, P4_A])
        verifie("prepare : purge annoncee", p["avertissements"] and ".pio/build" in p["avertissements"][0])

        p = m.prepare(racine, [S3_A, S3_C])
        i = p["apres"].index(S3_C)
        verifie("ajout : coche -> dans le groupe de sa puce, apres le dernier S3, meme retrait",
                p["apres"].index(S3_B) < i < p["apres"].index("; *** ESP32P4") and f"\r\n                            {S3_C}\r\n" in p["apres"])
        verifie("ajout : marque ajout", [a["t"].strip() for a in p["apercu"] if a["m"] == "ajout"] == [S3_C])
        verifie("ajout : non coche -> rien ajoute", BASE not in p["apres"])
        p = m.prepare(racine, [S3_A, S3_C, BASE])
        verifie("ajout : deux envs du meme groupe", p["apres"].count(S3_C) == 1 and p["apres"].count(BASE) == 1)

        verifie("refus : liste vide", any("tous les envs" in e for e in m.prepare(racine, [])["erreurs"]))
        verifie("refus : env inconnu", any("inconnu" in e for e in m.prepare(racine, [S3_A, "nexiste-pas"])["erreurs"]))
        verifie("refus : apercu inchange sur erreur", m.prepare(racine, [])["apres"] == OVERRIDE)
        try:
            m.prepare(racine, "pas une liste")
            verifie("refus : coches non liste -> ValueError", False)
        except ValueError:
            verifie("refus : coches non liste -> ValueError", True)

        def refuse(libelle, *args):
            avant = chemin.read_bytes()
            try:
                m.ecrit(racine, *args)
                verifie(libelle, False)
            except RuntimeError:
                verifie(libelle, chemin.read_bytes() == avant)

        bonne = m.prepare(racine, [S3_B])["empreinte"]
        refuse("ecrit : build en cours", [S3_B], bonne, lambda: ["pio run"])
        refuse("ecrit : detection impossible", [S3_B], bonne, lambda: None)
        refuse("ecrit : empreinte perimee", [S3_B], "x", aucun_build)
        refuse("ecrit : rien a ecrire", [S3_A], m.prepare(racine, [S3_A])["empreinte"], aucun_build)
        refuse("ecrit : liste vide", [], m.prepare(racine, [])["empreinte"], aucun_build)

        r = m.ecrit(racine, [S3_B], bonne, aucun_build)
        verifie("ecrit : fichier = apercu", chemin.read_bytes().decode("utf-8") == OVERRIDE.replace(
            f"                            {S3_A}\r\n", f"                            ; {S3_A}\r\n").replace(f"; {S3_B}\r\n", f"{S3_B}\r\n"))
        verifie("ecrit : copie d'origine sauvegardee", (Path(r["sauvegarde"]) / "platformio_override.ini").read_bytes() == OVERRIDE.encode("utf-8"))
        verifie("ecrit : relu actif", m.lit(racine)["actifs"] == [S3_B])

        abs_ = faux_depot(t, "sans_bloc", "[platformio]\r\n")
        verifie("bloc absent : refus sans plantage", m.lit(abs_)["erreurs"] and m.prepare(abs_, [S3_A])["erreurs"])
        val = faux_depot(t, "valeur", f"[platformio]\ndefault_envs = {S3_A}\n")
        verifie("valeur sur la ligne default_envs : refusee", any("elle-même" in e for e in m.prepare(val, [S3_A])["erreurs"]))
        lig = faux_depot(t, "virgule", f"[platformio]\ndefault_envs =\n  {S3_A}, {S3_B}\n")
        verifie("ligne a deux envs : refusee", any("non gérée" in e for e in m.prepare(lig, [S3_A])["erreurs"]))

        # Vrais fichiers du depot, copies : la liste relue par PlatformIO est celle cochee ; le pre-script garde le bloc
        vrai = Path(t) / "vrai"
        vrai.mkdir()
        for f in DEPOT.glob("platformio*.ini"):
            shutil.copy(f, vrai / f.name)
        origine = os.getcwd()
        os.chdir(vrai)      # PlatformIO cherche extra_configs depuis le dossier courant : sinon, il relirait le vrai depot
        try:
            from platformio.project.config import ProjectConfig
            reel = m.lit(vrai)
            verifie("reel : la copie est bien relue, et non vide", ProjectConfig(str(vrai / "platformio.ini")).default_envs() and vrai.samefile(os.getcwd()))
            verifie("reel : etat lu = default_envs de PlatformIO",
                    sorted(reel["actifs"]) == sorted(ProjectConfig(str(vrai / "platformio.ini")).default_envs()))
            toutes = [e["nom"] for g in reel["groupes"] for e in g["envs"]]
            cible = [n for n in toutes if n not in reel["actifs"]][:2] + reel["actifs"][:1] + [
                next(e["nom"] for g in reel["groupes"] for e in g["envs"] if e["absent"])]
            cible = sorted(set(cible))
            octets_avant = (vrai / "platformio_override.ini").read_bytes()
            m.ecrit(vrai, cible, m.prepare(vrai, cible)["empreinte"], aucun_build)
            verifie("reel : ProjectConfig relit exactement la liste cochee",
                    sorted(ProjectConfig(str(vrai / "platformio.ini")).default_envs()) == cible)
            lignes_apres = (vrai / "platformio_override.ini").read_bytes().decode("utf-8").splitlines(keepends=True)
            hors_bloc = lambda ls: [l for l in ls if not any(n in l for n in toutes)]
            verifie("reel : hors des lignes d'envs, aucun octet change",
                    hors_bloc(octets_avant.decode("utf-8").splitlines(keepends=True)) == hors_bloc(lignes_apres))
            applique = fonctions_pre_script()
            regles = {"platformio": {"data_dir": {"replace": ["data/autre/dossier"]}}}
            (vrai / "platformio_override.ini").write_text("".join(applique(lignes_apres, regles)), encoding="utf-8", newline="")
            apres_pre = ProjectConfig(str(vrai / "platformio.ini"))
            verifie("reel : la reecriture de data_dir par le pre-script garde la liste",
                    sorted(apres_pre.default_envs()) == cible and Path(apres_pre.get("platformio", "data_dir")).as_posix().endswith("data/autre/dossier"))
        finally:
            os.chdir(origine)
        del os.environ["OUTILS_TASMOTA_DOSSIER"]
    return res


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    echecs = 0
    for nom, ok in cas(module(SOURCE)):
        echecs += 0 if ok else 1
        print(("OK " if ok else "KO ") + nom)
    for nom, (avant, apres) in MUTANTS.items():
        if avant not in SOURCE:
            echecs += 1
            print(f"KO mutant « {nom} » : motif introuvable")
            continue
        try:
            tues = [n for n, ok in cas(module(SOURCE.replace(avant, apres, 1))) if not ok]
        except Exception as erreur:                                # noqa: BLE001 - un mutant qui plante est tue
            tues = [repr(erreur)]
        echecs += 0 if tues else 1
        print(("OK " if tues else "KO ") + f"mutant « {nom} » " + (f"tue par : {tues[0]}" if tues else "SURVIT"))
    print("VERT" if echecs == 0 else f"ROUGE : {echecs} echec(s)")
    return 0 if echecs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
