"""Banc de verifie_lib_ignore.py (garde du lib_ignore au pre-build).

Code de sortie 0 = vert. Sans --reel : faux depot temporaire, aucun compilateur, aucun pio.
Avec --reel : le vrai env de la cuve (preprocesseur croise de PlatformIO, ~15 s) : sa liste passe, et
esp_wireguard_tasmota (incident du 2026-10-31) y est refusee.
Lancer : "%USERPROFILE%\\.platformio\\penv\\Scripts\\python.exe" -u test_verifie_lib_ignore.py [--reel]
"""

import os
import sys
import tempfile

import verifie_lib_ignore as v

ECHECS = []
V, F, U = v.VRAI, v.FAUX, v.INCERTAIN


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def test_evalue():
    ctx = v.Contexte({"USE_A": None, "N": "3", "H": "0x10", "S": '"txt"'}, options={"OPTION_CONFIG"})
    ev = lambda e: v.evalue(e, ctx, {})                                   # noqa: E731
    verifie(ev("defined(USE_A)"), V, "evalue : defined d'une macro de l'env")
    verifie(ev("defined USE_B"), F, "evalue : USE_* absente = fausse (fait foi)")
    verifie(ev("defined(USE_B) && INCONNUE >= 5"), F, "evalue : court-circuit, faux quel que soit l'inconnue")
    verifie(ev("defined(USE_A) && ESP_IDF_VERSION_MAJOR >= 5"), U,
            "evalue : macro du framework absente des defines -> incertaine (P4, xdrv_42_0, 2026-10-31)")
    verifie(ev("defined(USE_A) || INCONNUE"), V, "evalue : vrai || inconnue -> vrai")
    verifie(ev("N > 2 && H == 16"), V, "evalue : valeurs decimale et hexadecimale")
    verifie(ev("N > 5UL"), F, "evalue : suffixe UL")
    verifie(ev("!defined(USE_A)"), F, "evalue : negation")
    verifie(ev("defined(OPTION_CONFIG)"), F, "evalue : option de configuration Tasmota absente des defines -> fausse")
    verifie(ev("defined(SIMPLE_RES_TOUCH)"), U, "evalue : macro inconnue hors options -> incertaine")
    verifie(ev("ESP_IDF_VERSION_MAJOR >= ESP_IDF_VERSION_VAL(5, 0, 0)"), U, "evalue : macro fonction -> incertaine")
    ctx2 = v.Contexte({"USE_A": None}, definies={"ESP_IDF_VERSION_MAJOR", "LOCALE"})
    verifie(v.evalue("defined(VSCODE_DEV)", ctx2, {}), F, "evalue : macro definie nulle part -> fausse (xdrv_79, VSCODE_DEV)")
    verifie(v.evalue("defined(USE_A) && ESP_IDF_VERSION_MAJOR >= 5", ctx2, {}), U,
            "evalue : macro definie par le framework -> incertaine")
    verifie(v.evalue("defined(LOCALE)", ctx2, {}), U, "evalue : macro definie dans une source -> incertaine")
    verifie(ev("S == 1"), U, "evalue : valeur non numerique -> incertaine")


def test_commentaires():
    """Cuve, xdrv_50_filesystem.ino : `//*****` n'ouvre pas de bloc (incident du 2026-10-31)."""
    ctx = v.Contexte({"USE_A": None})
    texte = "\n".join(['//*********************', '#ifdef USE_A', '#include "a.h"', '#endif',
                       'const char *s = "x/*y";', '#include "b.h"',
                       'auto r = R"(// pas un commentaire /* non plus)";', '#include "c.h"',
                       "char c = '\"';", '#include "d.h"', '/* vrai', 'bloc */ #include "e.h"'])
    obtenu = [(i, l) for i, l, _ in v.includes_actifs(texte, ctx)]
    verifie(obtenu, [("a.h", 3), ("b.h", 6), ("c.h", 8), ("d.h", 10), ("e.h", 12)],
            "commentaires : // avant /*, chaines, chaine brute, caractere ; directive apres un bloc (comme gcc)")


def test_includes_actifs():
    ctx = v.Contexte({"USE_A": None, "ESP32": None})
    texte = "\n".join([
        '#include "toujours.h"',                    # 1
        "#ifdef USE_A",                             # 2
        '#include "a.h"',                           # 3
        "#elif defined(USE_B)",                     # 4
        '#include "b.h"',                           # 5
        "#else",                                    # 6
        '#include "c.h"',                           # 7
        "#endif",                                   # 8
        "#ifndef ESP32",                            # 9
        "  #include <esp8266.h>",                   # 10
        "#endif",                                   # 11
        "/* #include \"commente.h\"",               # 12
        "*/",                                       # 13
        "#define LOCAL",                            # 14
        "#ifdef LOCAL",                             # 15
        '#include "local.h"  // commentaire',      # 16
        "#endif",                                   # 17
        "#if defined(USE_Z) \\",                    # 18
        "    || defined(USE_A)",                    # 19
        '#include "suite.h"',                       # 20
        "#endif"])
    obtenu = [(i, l) for i, l, _ in v.includes_actifs(texte, ctx)]
    verifie(obtenu, [("toujours.h", 1), ("a.h", 3), ("local.h", 16), ("suite.h", 20)],
            "includes_actifs : branches, #ifndef, commentaire, #define local, ligne continuee")
    texte = "#ifdef MYSTERE\n#include \"m.h\"\n#else\n#include \"n.h\"\n#endif"
    obtenu = [(i, e) for i, _, e in v.includes_actifs(texte, v.Contexte({}))]
    verifie(obtenu, [("m.h", U), ("n.h", U)], "includes_actifs : garde incertaine -> les deux branches incertaines")


def ecrit(racine, chemin, texte):
    chemin = os.path.join(racine, chemin)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(texte)


def faux_depot(racine):
    ecrit(racine, "tasmota/a.ino", '#ifdef USE_A\n#include "liba.h"\n#endif\n#include <libb.h>\n'
                                   '#if defined(USE_X) && FOO > 2\n#include "libc.h"\n#endif\n#include <stdint.h>\n')
    ecrit(racine, "lib/default/LibA/library.json", '{"name": "Lib A"}')
    ecrit(racine, "lib/default/LibA/src/liba.h", '#include "libd.h"\n')
    ecrit(racine, "lib/default/LibB/libb.h", '#ifdef LIB_INTERNE\n#include "sous/libe.h"\n#endif\n')
    ecrit(racine, "lib/default/LibB/libb_config.h", "#define LIB_INTERNE 1\n")  # definie : garde incertaine
    ecrit(racine, "lib/default/LibC/src/libc.h", "")
    ecrit(racine, "lib/default/LibD/src/libd.h", "")
    ecrit(racine, "lib/default/LibE/src/sous/libe.h", "")
    ecrit(racine, "lib/default/LibE/src/stdint.h", "")                    # nom d'en-tete du systeme
    ecrit(racine, "lib/default/LibE/examples/ex.h", '#include "libc.h"\n')  # exemple : jamais compile
    ecrit(racine, "lib/default/LibF/src/libf.h", '#include "libd.h"\n')  # gardee mais incluse par personne
    ecrit(racine, "lib/default/Lib8266/library.json", '{"name": "Lib8266", "platforms": "espressif8266"}')
    ecrit(racine, "lib/default/Lib8266/libc.h", "")
    ecrit(racine, "paquets/framework-arduinoespressif32/cores/esp32/stdint.h", "")


def test_analyse():
    with tempfile.TemporaryDirectory() as racine:
        faux_depot(racine)
        vrais = v.PACKAGES, v.CACHE
        v.PACKAGES, v.CACHE = os.path.join(racine, "paquets"), os.path.join(racine, "cache")
        try:
            _analyse_faux_depot(racine)
        finally:
            v.PACKAGES, v.CACHE = vrais


def _analyse_faux_depot(racine):
    opts = {"plateforme": "espressif32", "mcu": "esp32s3", "lib_dirs": ["lib/default"], "lib_deps": []}
    a = v.Analyse(racine, opts, {"USE_A": None})
    verifie(sorted(sorted(b.noms) for b in a.libs)[0], ["Lib A", "LibA"], "analyse : nom du manifeste et du dossier")
    verifie(any("Lib8266" in b.noms for b in a.libs), False, "analyse : bibliotheque d'une autre plateforme ecartee")
    u = a.utilisations(["Lib A"])
    verifie((list(u), u.get("Lib A", [("", 0, "", F)])[0][1:]), (["Lib A"], (2, "liba.h", V)), "analyse : bibliotheque incluse sous garde vraie")
    verifie(a.utilisations(["LibC"]), {}, "analyse : incluse sous garde fausse (court-circuit) -> ignorable")
    verifie(list(a.utilisations(["LibD"])), ["LibD"], "analyse : chaine, incluse par une bibliotheque gardee")
    verifie(list(a.utilisations(["Lib A", "LibD"])), ["Lib A"],
            "analyse : chaine, incluse seulement par une ignoree ou une inatteignable (LibF) -> ignorable")
    u = a.utilisations(["LibE"])
    verifie((list(u), u.get("LibE", [("", 0, "", F)])[0][2:]), (["LibE"], ("sous/libe.h", U)),
            "analyse : chemin relatif, garde incertaine dans une bibliotheque -> utilisee")
    verifie(sorted(a.utilisations(["LibE", "LibB"])), ["LibB"],
            "analyse : stdint.h de LibE aussi fourni par le framework -> LibE pas utilisee")
    ignorables, raisons = a.propose()
    verifie(sorted(ignorables), ["LibC", "LibF"], "propose : LibC (garde fausse) et LibF (atteinte par personne)")
    verifie(sorted(raisons), ["Lib A", "LibB", "LibD", "LibE"], "propose : une raison pour chaque gardee")
    verifie(sorted(a.a_lister(ignorables)), ["LibC"],
            "a_lister : LibC tiree par le LDF (garde fausse lue quand meme), LibF atteinte par personne : inutile a nommer")


class FausseConfig:
    def __init__(self, sections):
        self.sections = sections

    def has_option(self, s, o):
        return o in self.sections.get(s, {})

    def get(self, s, o):
        return self.sections[s][o]


def test_ajouts_env():
    c = FausseConfig({"env:amont": {"lib_ignore": ["x", "y"]},
                      "env:base": {"extends": ["env:amont"], "lib_ignore": ["x", "y", "m"]},
                      "env:carte": {"extends": ["env:base"], "lib_ignore": ["x", "y", "m", "lvgl", "a/b.bec"]},
                      "env:sans": {"extends": ["amont"]}})
    perso = {"base", "carte", "sans"}
    verifie(v.ajouts_env(c, "carte", perso), ["m", "lvgl"],
            "ajouts_env : tout ce que le cenv ajoute a l'amont, base personnelle comprise")
    verifie(v.ajouts_env(c, "base", perso), ["m"], "ajouts_env : la base personnelle elle-meme")
    verifie(v.ajouts_env(c, "sans", perso), [], "ajouts_env : env sans lib_ignore propre -> rien a controler")


def test_reel():
    from platformio.project.config import ProjectConfig
    projet = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    os.chdir(projet)                                 # comme pio : extra_configs relatifs au depot
    config = ProjectConfig(os.path.join(projet, "platformio.ini"))
    # (env, bibliotheque a refuser, fichier, ligne, en-tete, etat) : les trois echecs de compilation du 2026-10-31
    refus = [("tasmota32s3-garage-capteurs-cuve-modbus", "esp_wireguard_tasmota", "xdrv_52_3_berry_crypto.ino", 27,
              "crypto/refc/poly1305-donna.h", V),
             ("tasmota32s3-garage-capteurs-cuve-modbus", "ESPFtpServer", "xdrv_50_filesystem.ino", 1912,
              "ESPFtpServer.h", V),
             ("tasmota32p4-garage-serveur-modbus", "ESP8266SAM", "xdrv_42_0_i2s_audio_idf51.ino", 23, "ESP8266SAM.h", U)]
    for nom in sorted({r[0] for r in refus}):
        opts = v.options_env(config, nom)
        a = v.Analyse(projet, opts, v.defines_env(projet, opts))
        ajouts = v.ajouts_env(config, nom, v.envs_personnels(projet))
        verifie(a.utilisations(ajouts), {}, f"reel : la liste de {nom} ({len(ajouts)}) passe")
        for _, lib, fichier, ligne, entete, etat in (r for r in refus if r[0] == nom):
            u = a.utilisations([lib]).get(lib, [])
            verifie([(os.path.basename(f), l, e, s) for f, l, e, s in u if os.path.basename(f) == fichier][:1],
                    [(fichier, ligne, entete, etat)], f"reel : {lib} refusee sur {nom} ({fichier}:{ligne})")


def principal():
    for t in (test_evalue, test_commentaires, test_includes_actifs, test_analyse, test_ajouts_env):
        t()
    if "--reel" in sys.argv:
        test_reel()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
