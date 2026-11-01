#!/usr/bin/env python3
"""Banc de build_partitions.py (plan temps-compilation, A9) : faux depot temporaire (cenv relu par ProjectConfig), vraies
tables de partitions/ lues seulement ; sauvegardes de la Transaction dans un dossier temporaire
(OUTILS_TASMOTA_DOSSIER). Puis chaque mutant de build_partitions.py doit faire echouer au moins un cas.

    <Python de PlatformIO> outils_docs/scripts_python/outils_pc/test_build_partitions.py

Code de sortie 0 = vert, 1 = rouge.
"""
import os
import re
import sys
import tempfile
import types
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
DEPOT = ICI.parents[2]
SOURCE = (ICI / "build_partitions.py").read_text(encoding="utf-8")
ENV = "tasmota32s3-garage-essai-partitions"
REL = f"partitions/env_{ENV}.csv"
M16 = 16 * 1024 * 1024
CENV = f"""; cenv d'essai\r
[env:base-essai]\r
board                   = esp32s3-qio_opi\r
board_build.partitions  = partitions/esp32_partition_app3904k_fs11584k.csv\r
board_upload.flash_size = 16MB\r
\r
[env:{ENV}]\r
extends                 = env:base-essai\r
build_flags             = -DESSAI\r
\r
[env:heritier-essai]\r
extends                 = env:{ENV}\r
"""
ENV32 = "[env:amont-seul]\nboard = esp32s3-qio_opi\nboard_build.partitions = partitions/esp32_partition_app3904k_fs11584k.csv\nboard_upload.flash_size = 16MB\n"
MUTANTS = {
    "64 Ko ignores": ("elif sz % PAS or debut % PAS:", "elif False:"),
    "fin de flash ignoree": ("elif debut != flash:", "elif False:"),
    "safeboot deplacable": ('p["sous_type"] == "factory" and p["debut"] != PAS', "False"),
    "upload par cable permis": ('"upload" in actions and methode == "com" and a_fs and len(parts) != 5', "False"),
    "OTA sans safeboot permise": ('"upload" in actions and methode == "ota" and not any', 'False and not any'),
    "image safeboot gardee": ("vide=sans_safeboot", "vide=False"),
    "trou accepte a l'import": ("if not erreurs and _forme(table) != _forme(parts):", "if False:"),
    "contenu ignore": ("if sz < (occupes.get(nom) or 0):", "if False:"),
    "FS dernier ignore": ('and parts[-1].get("sous_type") != "spiffs"', "and False"),
    "nvs deplacable": ("if (debut, sz) != TETE[nom][:2]:", "if False:"),
    "empreinte ignoree": ('if p["empreinte"] != empreinte_lue:', "if False:"),
    "build en cours ignore": ("    if builds:\n", "    if False:\n"),
    "OTA jamais liberee": ("_blocages(dossier, lambda b: b.pop(env, None))", "pass"),
    "colonnes non alignees": ("{adresse:<9}", "{adresse}"),
    "inchange ignore": ('_forme(table) == _forme(mem["partitions"])', "False"),
    "table existante ignoree": ('if _forme(t) == _forme(table)]', "if False]"),
    "env_ proposes": ('if chemin.name.startswith("env_") and not env_aussi:', "if False:"),
    "fichier nomme reecrit": ('[f"{rel} existe déjà avec une autre table : choisir un autre nom"]', "[]"),
    "env_ partage reecrit": ('if autres else []', "if False else []"),
    "doublon ignore": ('"" if doublon or not identiques', '"" if not identiques'),
    "flash des tables ignoree": ('if parts and parts[-1]["debut"] + parts[-1]["taille"] == mem["flash"]]', "]"),
}


def module(source):
    import build_memoire
    m = types.ModuleType("build_partitions_essai")
    exec(compile(source, "build_partitions.py", "exec"), m.__dict__)
    return m, build_memoire


def table_reelle(bm, nom):
    octets = (DEPOT / "partitions" / nom).read_bytes()
    parts = bm.lit_csv(octets.decode("utf-8"))
    return octets, [{k: p[k] for k in ("nom", "type", "sous_type", "taille")} for p in parts]


def cas(m, bm):
    res = []

    def verifie(nom, ok):
        res.append((nom, bool(ok)))

    def erreurs(parts, flash=M16, occupes=None):
        return m.valide(parts, flash, occupes)[1]

    for nom, flash in (("esp32_partition_app3904k_fs11584k.csv", M16), ("esp32_partition_app2752k_fs448k.csv", 4 * 1024 * 1024)):
        octets, parts = table_reelle(bm, nom)
        table, err = m.valide(parts, flash)
        eol = "\r\n" if b"\r\n" in octets else "\n"
        verifie(f"{nom} : valide, sans erreur", not err)
        verifie(f"{nom} : CSV produit identique octet pour octet", m.texte_csv(table, eol).encode("utf-8") == octets)

    _, base = table_reelle(bm, "esp32_partition_app3904k_fs11584k.csv")
    modif = [dict(p) for p in base]
    modif[3]["taille"] += 0x10000
    modif[4]["taille"] -= 0x10000
    table, err = m.valide(modif, M16)
    verifie("app0 +64 Ko, FS -64 Ko : accepte, FS deplace en 0x4C0000", not err and table[4]["debut"] == 0x4C0000)
    impair = [dict(p) for p in base]
    impair[3]["taille"] += 0x1000
    impair[4]["taille"] -= 0x1000
    verifie("taille hors pas de 64 Ko : refusee", any("64 Ko" in e for e in erreurs(impair)))
    court = [dict(p) for p in base]
    court[4]["taille"] -= 0x10000
    verifie("table qui ne finit pas a la fin de la flash : refusee", any("la flash fait" in e for e in erreurs(court)))
    sans_safeboot = [dict(p) for p in modif if p["nom"] != "safeboot"]
    sans_safeboot[2]["taille"] += 0xD0000
    verifie("4 partitions sans safeboot : acceptee, app0 en 0x10000",
            not erreurs(sans_safeboot) and m.valide(sans_safeboot, M16)[0][2]["debut"] == 0x10000)
    mal = [dict(p) for p in base]
    mal[2], mal[3] = mal[3], mal[2]
    verifie("safeboot hors de 0x10000 : refuse", any("safeboot doit rester" in x for x in erreurs(mal)))
    six = [dict(p) for p in base]
    six[4]["taille"] -= 0x10000
    six.insert(4, {"nom": "coredump", "type": "data", "sous_type": "coredump", "taille": 0x10000})
    verifie("6 partitions : acceptee", not erreurs(six))
    fs_milieu = [base[0], base[1], base[4], base[2], base[3]]
    verifie("FS pas en dernier : refuse", any("dernière partition" in x for x in erreurs(fs_milieu)))
    nvs = [dict(p) for p in base]
    nvs[0]["taille"], nvs[1]["taille"] = 0x6000, 0x1000
    verifie("nvs redimensionnee : refusee", any("nvs doit rester" in x for x in erreurs(nvs)))
    sans_app0 = [dict(p) for p in base]
    sans_app0[3]["sous_type"] = "ota_1"
    verifie("sans app0 (ota_0) : refusee", any("obligatoire" in x for x in erreurs(sans_app0)))
    verifie("app0 plus petite que le firmware : refusee",
            any("moins que" in x for x in erreurs(modif, occupes={"app0": modif[3]["taille"] + 1})))
    verifie("flash inconnue : refusee", any("flash inconnue" in x for x in erreurs(base, flash=None)))
    double = [dict(p) for p in base]
    double[2]["nom"] = "app0"
    verifie("nom en double : refuse", any("double" in x for x in erreurs(double)))
    verifie("taille booleenne : refusee", any("taille invalide" in x for x in erreurs([dict(base[0])] + [dict(p, taille=True) for p in base[1:]])))

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(d / "outils")
        racine, dossier = d / "depot", d / "outils" / "build"
        (racine / "partitions").mkdir(parents=True)
        for nom in ("esp32_partition_app3904k_fs11584k.csv",):
            (racine / "partitions" / nom).write_bytes((DEPOT / "partitions" / nom).read_bytes())
        (racine / "platformio_tasmota_cenv.ini").write_bytes(CENV.encode("utf-8"))
        (racine / "platformio_tasmota_env32.ini").write_text(ENV32, encoding="utf-8")
        (racine / "platformio.ini").write_text("[platformio]\nextra_configs = platformio_tasmota_env32.ini\n"
                                               "  platformio_tasmota_cenv.ini\n", encoding="utf-8")

        p = m.prepare(racine, dossier, ENV, modif)
        verifie("prepare : aucune erreur, diff du cenv et du CSV", not p["erreurs"] and f"+board_build.partitions  = {REL}" in p["diff"]
                and "+app0,     app,  ota_0,   0xE0000, 0x3E0000," in p["diff"])
        verifie("prepare : heritier signale, persist et OTA rappeles",
                any("heritier-essai" in a for a in p["avertissements"]) and any("persist" in a for a in p["avertissements"])
                and any("OTA" in a for a in p["avertissements"]))
        verifie("prepare : rien d'ecrit", not (racine / REL).exists())
        verifie("env hors du cenv : refuse", m.prepare(racine, dossier, "amont-seul", modif)["erreurs"])

        def jamais():
            return []

        actuelle = [dict(q) for q in base]
        i = m.prepare(racine, dossier, ENV, actuelle)
        verifie("table actuelle : inchangee, rien a ecrire", i["inchange"] and not i["diff"] and not i["avertissements"]
                and i["cenv"] == CENV)
        try:
            m.ecrit(racine, dossier, ENV, actuelle, i["empreinte"], jamais)
            verifie("table actuelle : ecriture refusee", False)
        except RuntimeError:
            verifie("table actuelle : ecriture refusee, OTA pas bloquee", m.ota_bloquee(dossier, ENV) == "")
        (racine / "partitions" / "esp32_autre_essai.csv").write_text(
            m.texte_csv(m.valide(modif, M16)[0]), encoding="utf-8")
        e2 = m.prepare(racine, dossier, ENV, modif)
        verifie("table identique a un fichier existant : l'env pointe vers lui, aucun CSV cree",
                e2["csv"] == "partitions/esp32_autre_essai.csv" and not e2["cree_csv"] and not e2["inchange"]
                and "+board_build.partitions  = partitions/esp32_autre_essai.csv" in e2["diff"])
        t = {x["csv"]: x for x in m.tables(racine, dossier, ENV)}
        verifie("tables : fichiers a la taille de la flash proposes", set(t) == {
            "partitions/esp32_autre_essai.csv", "partitions/esp32_partition_app3904k_fs11584k.csv"}
            and not t["partitions/esp32_autre_essai.csv"]["erreurs"])
        verifie("identique : proposition rendue, nom saisi ignore", m.prepare(racine, dossier, ENV, modif, "ma_table")["proposition"]
                == "partitions/esp32_autre_essai.csv" and not (racine / "partitions" / "ma_table.csv").exists())
        d = m.prepare(racine, dossier, ENV, modif, "ma_table", doublon=True)
        verifie("proposition refusee : le fichier nomme serait cree", d["csv"] == "partitions/ma_table.csv" and d["cree_csv"]
                and not d["proposition"] and not d["erreurs"])
        d = m.prepare(racine, dossier, ENV, modif, "esp32_autre_essai.csv", doublon=True)
        verifie("nom d'un fichier identique : pas de proposition, rien de cree", d["csv"] == "partitions/esp32_autre_essai.csv"
                and not d["cree_csv"] and not d["proposition"])
        (racine / "partitions" / "esp32_autre_essai.csv").unlink()
        (racine / "partitions" / "env_autre_env.csv").write_text(m.texte_csv(m.valide(modif, M16)[0]), encoding="utf-8")
        verifie("identique a l'env_ d'un autre env : propose aussi", m.prepare(racine, dossier, ENV, modif)["proposition"]
                == "partitions/env_autre_env.csv")
        (racine / "partitions" / "env_autre_env.csv").unlink()
        for mauvais in ("../evil", "a/b", "a b", "env_x", "CON", "x" * 65):
            verifie(f"nom refuse : {mauvais[:10]!r}", any("invalide" in e for e in m.prepare(racine, dossier, ENV, modif, mauvais)["erreurs"]))
        verifie("nom d'un fichier existant, autre table : refus", any("existe déjà" in e for e in m.prepare(
            racine, dossier, ENV, modif, "esp32_partition_app3904k_fs11584k")["erreurs"]))
        n = m.prepare(racine, dossier, ENV, modif, "ma_table.csv")
        verifie("nom saisi : fichier a ce nom, extension toleree", n["csv"] == "partitions/ma_table.csv" and n["cree_csv"]
                and "= partitions/ma_table.csv" in n["diff"] and n["empreinte"] != p["empreinte"])
        try:
            m.ecrit(racine, dossier, ENV, modif, p["empreinte"], jamais, "ma_table")
            verifie("empreinte d'un autre nom : refus", False)
        except RuntimeError:
            verifie("empreinte d'un autre nom : refus", not (racine / "partitions" / "ma_table.csv").exists())
        (racine / "partitions" / "esp32_4mo_essai.csv").write_bytes((DEPOT / "partitions" / "esp32_partition_app2752k_fs448k.csv").read_bytes())
        (racine / "partitions" / f"env_{ENV}x.csv").write_bytes((DEPOT / "partitions" / "esp32_partition_app3904k_fs11584k.csv").read_bytes())
        verifie("tables : autre flash et env_* ecartes", {x["csv"] for x in m.tables(racine, dossier, ENV)} == {
            "partitions/esp32_partition_app3904k_fs11584k.csv"})
        (racine / "partitions" / "esp32_4mo_essai.csv").unlink()
        (racine / "partitions" / f"env_{ENV}x.csv").unlink()

        for nom, args in (("build en cours : refus", (p["empreinte"], lambda: ["pio run"])),
                          ("empreinte perimee : refus", ("faux", jamais)),
                          ("table invalide : refus", (m.prepare(racine, dossier, ENV, court)["empreinte"], jamais))):
            try:
                m.ecrit(racine, dossier, ENV, court if "invalide" in nom else modif, *args)
                verifie(nom, False)
            except RuntimeError:
                verifie(nom, not (racine / REL).exists())

        r = m.ecrit(racine, dossier, ENV, modif, p["empreinte"], jamais)
        cenv = (racine / "platformio_tasmota_cenv.ini").read_bytes().decode("utf-8")
        verifie("ecrit : CSV de l'env ecrit, fins de ligne du cenv", r["ecrit"] and (racine / REL).read_bytes()
                == p["texte_csv"].encode("utf-8") and "\r\n" in p["texte_csv"])
        verifie("ecrit : section de l'env seule changee", cenv.count("board_build.partitions") == 2
                and "board_build.partitions  = partitions/esp32_partition_app3904k_fs11584k.csv" in cenv)
        ici = os.getcwd()
        os.chdir(racine)                                           # extra_configs : relatifs au dossier courant
        try:
            from platformio.project.config import ProjectConfig
            conf = ProjectConfig(str(racine / "platformio.ini"))
            verifie("ProjectConfig : table de l'env et de l'heritier, base inchangee",
                    conf.get(f"env:{ENV}", "board_build.partitions") == REL
                    and conf.get("env:heritier-essai", "board_build.partitions") == REL
                    and conf.get("env:base-essai", "board_build.partitions").endswith("app3904k_fs11584k.csv"))
        except ImportError:
            verifie("ProjectConfig importable (lancer avec le Python de PlatformIO)", False)
        finally:
            os.chdir(ici)
        verifie("OTA bloquee apres ecriture, motif nomme", "OTA bloquée" in m.ota_bloquee(dossier, ENV)
                and m.ota_bloquee(dossier, "heritier-essai") == "")
        m.libere(dossier, ENV)
        verifie("OTA liberee apres l'effacement", m.ota_bloquee(dossier, ENV) == "")

        verifie("5 partitions : aucun envoi refuse", not m.motifs_envoi(racine, ENV, ["upload", "buildfs"], "com")
                and not m.motifs_envoi(racine, ENV, ["upload"], "ota"))
        fichier_cenv = racine / "platformio_tasmota_cenv.ini"
        cenv_avant = fichier_cenv.read_bytes()
        fichier_cenv.write_bytes(cenv_avant + f"\n[env:un_autre]\nboard_build.partitions = {REL}\n".encode())
        verifie("env_ qui sert aussi a un autre env : refus, un nom est demande", any(
            "sert aussi à un_autre" in e for e in m.prepare(racine, dossier, ENV, sans_safeboot)["erreurs"]))
        fichier_cenv.write_bytes(cenv_avant)
        p4 = m.prepare(racine, dossier, ENV, sans_safeboot)
        verifie("sans safeboot : image videe dans la section, consequences dites",
                not p4["erreurs"] and re.search(r"^\+board_upload\.arduino\.flash_extra_images\s*=\s*$", p4["diff"], re.M)
                and any("sans safeboot" in a for a in p4["avertissements"]))
        m.ecrit(racine, dossier, ENV, sans_safeboot, p4["empreinte"], jamais)
        os.chdir(racine)
        try:
            conf = ProjectConfig(str(racine / "platformio.ini"))
            verifie("ProjectConfig : image vide pour l'env seul", conf.get(f"env:{ENV}", m.IMAGES) == ""
                    and not conf.has_option("env:base-essai", m.IMAGES))
            from platformio.platform.board import PlatformBoardConfig
            carte = PlatformBoardConfig(str(DEPOT / "boards" / "esp32s3-qio_opi.json"))
            avant = carte.get("upload.arduino.flash_extra_images", [])
            carte.update("upload.arduino.flash_extra_images", conf.get(f"env:{ENV}", m.IMAGES))
            verifie("carte PlatformIO : image du safeboot retiree par l'option vide", avant
                    and not carte.get("upload.arduino.flash_extra_images", []))
        finally:
            os.chdir(ici)
        verifie("4 partitions : upload par cable refuse, erase_upload permis", m.motifs_envoi(racine, ENV, ["upload"], "com")
                and not m.motifs_envoi(racine, ENV, ["erase_upload"], "com"))
        verifie("sans safeboot : OTA du firmware refusee, OTA du FS permise", m.motifs_envoi(racine, ENV, ["upload"], "ota")
                and not m.motifs_envoi(racine, ENV, ["uploadfs"], "ota"))
        retour = m.prepare(racine, dossier, ENV, modif)
        verifie("retour avec safeboot : option retiree", not retour["erreurs"] and m.IMAGES not in retour["cenv"].split(f"[env:{ENV}]")[1].split("[env:")[0])
        sans_fs = [dict(q) for q in base if q["nom"] != "spiffs"]
        sans_fs[3]["taille"] += base[4]["taille"]
        verifie("sans FS : acceptee, consequence dite", not m.valide(sans_fs, M16)[1]
                and any("sans FS" in a for a in m.prepare(racine, dossier, ENV, sans_fs)["avertissements"]))
        csv_ok = m.texte_csv(m.valide(six, M16)[0])
        verifie("import : 6 partitions lues, sans erreur", (lambda r: len(r[0]) == 6 and not r[1])(m.lit_import(racine, dossier, ENV, csv_ok)))
        fin = m.valide(six, M16)[0][-1]["debut"]
        verifie("import : trou d'adresses refuse", any("contiguës" in x for x in m.lit_import(
            racine, dossier, ENV, csv_ok.replace(f"0x{fin:X},", f"0x{fin + 0x10000:X},", 1))[1]))
        verifie("import : drapeaux refuses", any("Flags" in x for x in m.lit_import(
            racine, dossier, ENV, csv_ok.rstrip() + " encrypted\n")[1]))
        verifie("import : illisible ou vide refuse", m.lit_import(racine, dossier, ENV, "x,y,z,0,pas_une_taille,")[1]
                and m.lit_import(racine, dossier, ENV, "# rien\n")[1])
        del os.environ["OUTILS_TASMOTA_DOSSIER"]
    return res


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    echecs = 0
    for nom, ok in cas(*module(SOURCE)):
        echecs += 0 if ok else 1
        print(("OK " if ok else "KO ") + nom)
    for nom, (avant, apres) in MUTANTS.items():
        if avant not in SOURCE:
            echecs += 1
            print(f"KO mutant « {nom} » : motif introuvable")
            continue
        try:
            tues = [n for n, ok in cas(*module(SOURCE.replace(avant, apres, 1))) if not ok]
        except Exception as erreur:                                # noqa: BLE001 - un mutant qui plante est tue
            tues = [repr(erreur)]
        echecs += 0 if tues else 1
        print(("OK " if tues else "KO ") + f"mutant « {nom} » " + (f"tue par : {tues[0]}" if tues else "SURVIT"))
    print("VERT" if echecs == 0 else f"ROUGE : {echecs} echec(s)")
    return 0 if echecs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
