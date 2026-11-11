#!/usr/bin/env python3
"""Banc de interface_ecran.py : interface d'ecran choisie a la compilation (plan debits-deux-cartes, A8).

1. Vraie classe ProjectConfig de PlatformIO sur un ini temporaire (extends, ${berry_commun.x}, commentaires) :
   haspmota -> ecranLvgl.be exclu ; lvgl -> ecranHaspmota.be et pages.jsonl exclus ; option absente -> rien ;
   valeur inconnue -> arret (env.Exit). La liste est relue par l'expression de pio-tools/post_esp32.py
   (`GetProjectOption("custom_files_exclude").splitlines()`) sur l'instance que rend get_instance a un second lecteur.
2. Vraie image LittleFS (geometrie et version 2.0 de la plateforme) : la post-action retire les fichiers exclus de la
   racine, garde les autres octet pour octet et la version disque.
3. Depot reel, lecture seule : env d'affichage des debits (haspmota -> ecranLvgl.be) et acquisition (pages.jsonl et
   display.ini retires de son image).
4. Mutants (source modifiee en memoire) : chacun doit rendre le banc rouge.

    C:/Users/fdaub/.platformio/penv/Scripts/python.exe outils_docs/scripts_python/build/test_interface_ecran.py

Code de sortie 0 = vert, 1 = rouge. Rien du depot n'est ecrit.
"""
import os
import sys
import tempfile
import types

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.normpath(os.path.join(ICI, "..", "..", ".."))
SOURCE = os.path.join(ICI, "interface_ecran.py")
PRE_SCRIPT = os.path.join(ICI, "pre_utilitaires_platformio.py")
CARTE = "data/bureau/tasmota32s3-ecran-debits-pac"

INI = """[platformio]
default_envs = carte

[berry_commun]
page_cuve = data/fs/cuvePageFonctions.be

[env:base]
custom_files_exclude = ${berry_commun.page_cuve}

[env:carte]
extends = env:base
custom_files_exclude = ${berry_commun.page_cuve}
                       data/fs/controleLeds.be      ; commentaire en ligne
%s
"""
INTERFACES = f"""custom_interface_ecran_haspmota = {CARTE}/ecranHaspmota.be
                                  {CARTE}/pages.jsonl
custom_interface_ecran_lvgl = {CARTE}/ecranLvgl.be
"""


class FauxEnv(dict):
    def __init__(self, config, pioenv, dossier=""):
        super().__init__(PIOENV=pioenv)
        self.config, self.sortie, self.dossier = config, None, dossier

    def subst(self, chaine):
        assert chaine == "$PROJECT_DATA_DIR", chaine
        return self.dossier

    def GetProjectConfig(self):
        return self.config

    def GetProjectOption(self, option):
        return self.config.get("env:" + self["PIOENV"], option)

    def Exit(self, code):
        self.sortie = code
        raise SystemExit(code)


def charge(remplacements=()):
    texte = open(SOURCE, encoding="utf-8").read()
    for avant, apres in remplacements:
        assert avant in texte, f"mutant sans effet : {avant!r}"
        texte = texte.replace(avant, apres)
    module = types.ModuleType("interface_ecran")
    exec(compile(texte, SOURCE, "exec"), module.__dict__)
    return module


def config_temporaire(dossier, lignes):
    from platformio.project.config import ProjectConfig
    chemin = os.path.join(dossier, "platformio.ini")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(INI % lignes)
    ProjectConfig._instances.pop(chemin, None)
    return ProjectConfig.get_instance(chemin), chemin


def lu_par_post_esp32(chemin, pioenv):
    """Second lecteur : comme post_esp32.py, nouvelle demande d'instance puis GetProjectOption(...).splitlines()."""
    from platformio.project.config import ProjectConfig
    exclus = ProjectConfig.get_instance(chemin).get("env:" + pioenv, "custom_files_exclude").splitlines()
    return sorted(os.path.basename(s.strip()) for s in exclus if s.strip())


def image(fichiers, version=0x00020000):
    """Image LittleFS faite comme builder/main.py::build_fs_image (version 2.0 de [common] de platformio.ini)."""
    from littlefs import LittleFS
    fs = LittleFS(block_count=64, disk_version=version, mount=False, block_size=4096, read_size=1, prog_size=1,
                  cache_size=4096, lookahead_size=32, block_cycles=500, name_max=64)
    fs.format()
    fs.mount()
    for rel, contenu in fichiers.items():
        if "/" in rel:
            fs.makedirs(rel.rsplit("/", 1)[0], exist_ok=True)
        with fs.open(rel, "wb") as f:
            f.write(contenu)
    return bytes(fs.context.buffer)


def lit_image(donnees):
    from littlefs import LittleFS, UserContext
    fs = LittleFS(context=UserContext(buffer=bytearray(donnees)), block_count=len(donnees) // 4096, mount=False,
                  block_size=4096, read_size=1, prog_size=1, cache_size=4096, lookahead_size=32, name_max=64,
                  disk_version=0)                  # 0 = toute version lisible ; lecture seule, rien n'est reecrit
    fs.mount()
    contenus = {}
    for racine, _, noms in fs.walk("/"):
        for n in noms:
            rel = (racine.rstrip("/") + "/" + n).lstrip("/")
            with fs.open(rel, "rb") as f:
                contenus[rel] = f.read()
    return contenus, fs.fs_stat().disk_version


def lance(module, env):
    """applique, l'arret du build (env.Exit -> SystemExit) etant lu dans env.sortie."""
    try:
        module.applique(env)
    except SystemExit:
        pass


def essais(module):
    """Liste des libelles en echec."""
    echecs = []

    def verifie(obtenu, attendu, libelle):
        ok = obtenu == attendu
        print(("OK  " if ok else "KO  ") + libelle + ("" if ok else f"\n      obtenu  : {obtenu!r}\n      attendu : {attendu!r}"))
        if not ok:
            echecs.append(libelle)

    socle = ["controleLeds.be", "cuvePageFonctions.be"]
    with tempfile.TemporaryDirectory() as dossier:
        cas = (("haspmota", "custom_interface_ecran = haspmota\n" + INTERFACES, ["ecranLvgl.be"]),
               ("lvgl", "custom_interface_ecran = lvgl\n" + INTERFACES, ["ecranHaspmota.be", "pages.jsonl"]),
               ("option absente", INTERFACES, []))
        for libelle, lignes, exclus in cas:
            config, chemin = config_temporaire(dossier, lignes)
            env = FauxEnv(config, "carte")
            lance(module, env)
            verifie(env.sortie, None, f"{libelle} : le build continue")
            verifie(lu_par_post_esp32(chemin, "carte"), sorted(socle + exclus),
                    f"{libelle} : custom_files_exclude relu par post_esp32 = socle + {exclus}")

        # Interfaces declarees dans l'env parent : options() suit extends
        config, chemin = config_temporaire(dossier, "custom_interface_ecran = lvgl")
        config.set("env:base", "custom_interface_ecran_lvgl", f"{CARTE}/ecranLvgl.be")
        config.set("env:base", "custom_interface_ecran_haspmota", f"{CARTE}/pages.jsonl")
        verifie(module.exclusions(config, "env:carte"), ("lvgl", [f"{CARTE}/pages.jsonl"]),
                "interfaces declarees dans l'env parent (extends)")

        for libelle, lignes in (("valeur inconnue", "custom_interface_ecran = lgvl\n" + INTERFACES),
                                ("valeur sans aucune interface declaree", "custom_interface_ecran = haspmota")):
            config, chemin = config_temporaire(dossier, lignes)
            env = FauxEnv(config, "carte")
            lance(module, env)
            verifie(env.sortie, 1, f"{libelle} : build arrete (env.Exit(1))")
            verifie(lu_par_post_esp32(chemin, "carte"), socle, f"{libelle} : custom_files_exclude inchange")

        # Image du buildfs : post-action retire_exclus apres le choix haspmota
        config, chemin = config_temporaire(dossier, "custom_interface_ecran = haspmota\n" + INTERFACES)
        source = os.path.join(dossier, "carte")              # data_dir de l'env : fichiers de la racine de l'image
        env = FauxEnv(config, "carte", source)
        lance(module, env)
        fichiers = {"autoexec.be": b"import ecranHaspmota", "ecranHaspmota.be": b"h" * 5000, "pages.jsonl": b"{}",
                    "ecranLvgl.be": b"l" * 3000, "_persist.json": b"{\"a\": 1}", "sd/js/pages.js": b"js",
                    "sd/ecranLvgl.be": b"sous-dossier : hors regle de post_esp32"}
        for rel, contenu in fichiers.items():
            os.makedirs(os.path.dirname(os.path.join(source, rel)), exist_ok=True)
            with open(os.path.join(source, rel), "wb") as f:
                f.write(contenu)
        bin_ = os.path.join(dossier, "littlefs.bin")
        with open(bin_, "wb") as f:
            f.write(image(fichiers))
        avant, _ = lit_image(open(bin_, "rb").read())
        verifie("ecranLvgl.be" in avant, True, "temoin : sans la post-action, ecranLvgl.be est dans l'image")
        retour = module.retire_exclus([bin_], [], env)
        verifie(retour, None, "post-action : retour None (SCons lirait une valeur vraie comme un echec)")
        apres, version = lit_image(open(bin_, "rb").read())
        attendu = {k: v for k, v in fichiers.items() if k != "ecranLvgl.be"}
        verifie(apres, attendu, "image : ecranLvgl.be retire, autres fichiers identiques octet pour octet")
        verifie(hex(version), hex(0x00020000), "image : version disque 2.0 gardee")
        taille = os.path.getsize(bin_)
        verifie(module.retire_de_image(bin_, {"absent.be"}), [], "rien a retirer : image laissee telle quelle")
        verifie(os.path.getsize(bin_), taille, "rien a retirer : taille inchangee")
        # Aucun fichier exclu dans le dossier source : l'image n'est pas ouverte (ici illisible, aucune exception)
        os.remove(os.path.join(source, "ecranLvgl.be"))
        with open(bin_, "wb") as f:
            f.write(b"pas une image")
        verifie(module.retire_exclus([bin_], [], env), None, "aucun exclu a la racine du dossier : image pas ouverte")
        verifie(open(bin_, "rb").read(), b"pas une image", "aucun exclu a la racine du dossier : octets inchanges")

        # Depot reel, lecture seule (config en memoire)
        from platformio.project.config import ProjectConfig
        reel = ProjectConfig(os.path.join(DEPOT, "platformio.ini"))
        env = FauxEnv(reel, "tasmota32s3-bureau-ecran-debits-pac")
        verifie(module.exclusions(reel, "env:tasmota32s3-bureau-ecran-debits-pac"),
                ("haspmota", [f"{CARTE}/ecranLvgl.be"]), "depot : affichage des debits en haspmota, ecranLvgl.be exclu")
        lance(module, env)
        verifie(env.sortie, None, "depot : affichage, le build continue")
        env = FauxEnv(reel, "tasmota32s3-bureau-serveur-debits-pac",
                      os.path.join(DEPOT, "data", "bureau", "tasmota32s3-serveur-debits-pac"))
        with open(bin_, "wb") as f:
            f.write(image({"pages.jsonl": b"{}", "display.ini": b":H", "autoexec.be": b"x"}))
        module.retire_exclus([bin_], [], env)
        verifie(sorted(lit_image(open(bin_, "rb").read())[0]), ["autoexec.be"],
                "depot : acquisition, pages.jsonl et display.ini retires de son image")
    return echecs


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("== Code reel ==")
    echecs = essais(charge())

    texte = open(PRE_SCRIPT, encoding="utf-8").read()
    for attendu in ("interface_ecran.applique(env)", "interface_ecran.retire_exclus)"):
        ok = attendu in texte
        print(("OK  " if ok else "KO  ") + f"pre-script : {attendu}")
        if not ok:
            echecs.append(attendu)

    mutants = (("pas de set en memoire", [("config.set(section", "(lambda *a: None)(section")]),
               ("valeur inconnue toleree", [("        env.Exit(1)\n        return\n    if choix", "        return\n    if choix")]),
               ("rien retire de l'image", [("for n in retires:\n        fs.remove(n)", "for n in []:\n        fs.remove(n)")]),
               ("version disque non gardee", [("fs = monte(version)", "fs = monte(0)")]),
               ("autres interfaces ignorees", [("if nom != choix", "if nom == choix")]),
               ("image ouverte sans exclu dans le dossier", [("    if not noms:\n        return None\n    for n", "    for n")]))
    print("\n== Mutants (chacun doit etre rouge) ==")
    vivants = []
    for nom, remplacements in mutants:
        print(f"-- mutant : {nom}")
        try:
            vert = not essais(charge(remplacements))
        except Exception as e:                       # noqa: BLE001 - un mutant qui fait planter le banc est rouge
            print(f"KO  exception : {e!r}")
            vert = False
        if vert:
            vivants.append(nom)
    print()
    if vivants:
        print("KO  mutants restes verts : " + ", ".join(vivants))
    if echecs or vivants:
        print(f"BANC_INTERFACE_ECRAN : ROUGE ({len(echecs)} echec(s), {len(vivants)} mutant(s) vivant(s))")
        return 1
    print("BANC_INTERFACE_ECRAN : VERT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
