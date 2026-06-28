"""Bibliothèque de support pour les scripts pio-tools

Fournit également des fonctions pour remplacer certains paramètres, voir les
remplacements disponibles ci-dessous.

Les remplacements peuvent être définis via des variables d'environnement ou des
paramètres .ini pour contrôler les emplacements et formats des fichiers de sortie.

Pour définir une valeur via une variable d'environnement, préfixez la valeur avec "TASMOTA_"
et assurez-vous que la valeur entière est en MAJUSCULES, par exemple en bash :

      export TASMOTA_DISABLE_MAP_GZ=1

Pour définir une valeur dans votre fichier .ini, comme dans platformio_override.ini,
créez une section [tasmota] et placez la clé en minuscules, par exemple :

[tasmota]
disable_map_gz = 1
map_dir = /tmp/map_files/

Les valeurs des fichiers .ini remplacent les variables d'environnement

"""
import sys
import zlib
import pathlib
import os

# === REMPLACEMENTS DISPONIBLES ===
# si défini à 1, ne compresse pas du tout les fichiers bin en gzip
DISABLE_BIN_GZ = "disable_bin_gz"
# si défini à 1, compresse les fichiers bin esp32 en gzip
ENABLE_ESP32_GZ = "enable_esp32_gz"
# si défini, chemin alternatif pour les fichiers .bin générés, relatif au répertoire du projet
BIN_DIR = "bin_dir"
# si défini à 1, ne compresse pas les fichiers .map générés en gzip
DISABLE_MAP_GZ = "disable_map_gz"
# si défini, chemin alternatif pour les fichiers .map générés, relatif au répertoire du projet
MAP_DIR = "map_dir"
# if set to 1, copies output .bin/.bin.gz with build timestamp appended to the filename
APPEND_TIMESTAMP = "append_timestamp"

# === FIN DES REMPLACEMENTS DISPONIBLES ===


# Répertoire de sortie par défaut
OUTPUT_DIR = pathlib.Path("build_output")

def get_variant(env) -> str:
    """Obtient la variante de compilation actuelle."""
    return env["PIOENV"]


def get_final_bin_path(env) -> pathlib.Path:
    """Chemin vers la destination finale du fichier .bin

    Si le répertoire parent n'existe pas, il sera créé"""
    firmware_dir = get_override_path(BIN_DIR, env)
    firmware_dir.mkdir(parents=True, exist_ok=True)
    return firmware_dir / "{}.bin".format(get_variant(env))


def get_final_map_path(env) -> pathlib.Path:
    """Chemin vers la destination finale du fichier .map

    Si le répertoire parent n'existe pas, il sera créé"""
    map_dir = get_override_path(MAP_DIR, env)
    map_dir.mkdir(parents=True, exist_ok=True)
    return map_dir / "{}.map".format(get_variant(env))


def get_source_map_path(env) -> pathlib.Path:
    """Chemin vers le fichier .map compilé.

    Teste les emplacements potentiels, retourne le premier trouvé.
    Lève FileNotFoundError si aucun emplacement ne correspond"""
    fwmap_path = pathlib.Path("firmware.map")
    if fwmap_path.is_file():
        return fwmap_path

    # le firmware est peut-être dans le répertoire de build du projet
    # PIO env variables see: https://github.com/platformio/platformio-core/blob/develop/platformio/builder/main.py#L108:L128
    proj_build_dir = pathlib.Path(env["PROJECT_BUILD_DIR"])
    proj_dir = pathlib.Path(env["PROJECT_DIR"])
    map_name = proj_dir.parts[-1] + ".map"
    fwmap_path = proj_build_dir / get_variant(env) / map_name
    if fwmap_path.is_file():
        return fwmap_path

    map_name = "firmware.map"
    fwmap_path = proj_build_dir / get_variant(env) / map_name
    if fwmap_path.is_file():
        return fwmap_path

    raise FileNotFoundError


def get_tasmota_override_option(name: str, env):
    """Obtient une option de remplacement depuis un fichier .ini ou une variable d'env, None si aucune correspondance"""
    config = env.GetProjectConfig()
    override = config.get("tasmota", name.lower(), None)
    if override is not None:
        return override
    # Retourner la variable d'environnement si disponible
    return os.environ.get("TASMOTA_" + name.upper())


def get_override_path(pathtype: str, env) -> pathlib.Path:
    """
    Retourne un chemin vers le chemin de remplacement donné s'il est défini, sinon OUTPUT_DIR est utilisé.

    pathtype doit être MAP_DIR ou BIN_DIR.
    """
    override = get_tasmota_override_option(pathtype, env)
    if override:
        return pathlib.Path(override)
    if pathtype == BIN_DIR:
        return OUTPUT_DIR / "firmware"
    elif pathtype == MAP_DIR:
        return OUTPUT_DIR / "map"
    raise ValueError


def is_env_set(name: str, env):
    """Vrai si la variable d'environnement <name> est définie à `1`"""
    val = get_tasmota_override_option(name, env)
    if val:
        val = val.strip()
        return val == "1"
    return False

# ---------------------------------------------------------------------------
# Détection de la cible
#
# Les scripts Berry (dump-defines.py, gen-berry-defines.py,
# gen-berry-structures.py) s'exécutent pour *chaque* invocation PlatformIO,
# y compris pour des cibles qui ne compilent pas (upload, erase, monitor...).
#
# `is_non_build_target(env)` retourne True quand seules ces cibles non-compil.
# sont demandées, pour court-circuiter le pipeline Berry.
# ---------------------------------------------------------------------------

NON_BUILD_TARGETS = frozenset({
    # téléversements filesystem uniquement (sans compilation firmware)
    "uploadfs", "uploadfsota",
    # construction/téléchargement filesystem
    "buildfs", "downloadfs", "download_fs",
    # variantes d'effacement
    "erase", "erase_flash", "eraseflash",
    # info uniquement / sans opération
    "monitor", "nobuild", "envdump", "exec",
    "size", "sizedata", "metrics", "idedata", "compiledb",
    # nettoyages
    "clean", "fullclean", "cleanall",
    # cibles Tasmota personnalisées (voir pio-tools/custom_target.py)
    "reset_target", "factory_flash", "external_crashreport",
})

def is_non_build_target(env=None):
    """Retourne True si l'invocation PlatformIO ne demande que des cibles
    non-compilantes (upload, erase, monitor, ...).

    Retourne False pour la compilation par défaut et pour toute invocation
    qui mélange une cible liée à la compilation.
    """
    try:
        from SCons.Script import COMMAND_LINE_TARGETS
    except ImportError:
        COMMAND_LINE_TARGETS = []

    if COMMAND_LINE_TARGETS:
        return all(t in NON_BUILD_TARGETS for t in COMMAND_LINE_TARGETS)

    # COMMAND_LINE_TARGETS est vide (ex. VS Code / PlatformIO IDE).
    # Inspecter sys.argv pour les mots-clés de cibles non-build.
    argv_lower = [str(a).lower() for a in sys.argv]
    if any(t == arg for t in NON_BUILD_TARGETS for arg in argv_lower):
        return True

    return False  # compilation par défaut


def _compress_with_gzip(data, level=9):
    import zlib
    if   level < 0: level = 0
    elif level > 9: level = 9
    # en-tête gzip sans horodatage
    zobj = zlib.compressobj(level=level, wbits=16 + zlib.MAX_WBITS)
    return zobj.compress(data) + zobj.flush()

try:
    import zopfli

    # deux modules Python s'appellent `zopfli`, lequel est-ce ?
    if hasattr(zopfli, 'ZopfliCompressor'):
        # il semble qu'on ait zopflipy
        from zopfli import ZopfliCompressor, ZOPFLI_FORMAT_GZIP
        def _compress_with_zopfli(data, iterations=15, maxsplit=15, **kw):
            zobj = ZopfliCompressor(
                ZOPFLI_FORMAT_GZIP,
                iterations=iterations,
                block_splitting_max=maxsplit,
                **kw,
            )
            return zobj.compress(data) + zobj.flush()

    else:
        # il semble qu'on ait pyzopfli
        import zopfli.gzip
        def _compress_with_zopfli(data, iterations=15, maxsplit=15, **kw):
            return zopfli.gzip.compress(
                data,
                numiterations=iterations,
                blocksplittingmax=maxsplit,
                **kw,
            )

    # valeurs basées sur des tests manuels limités
    def _level_to_params(level):
        if   level == 10: return (15, 15)
        elif level == 11: return (15, 20)
        elif level == 12: return (15, 25)
        elif level == 13: return (15, 30)
        elif level == 14: return (15, 35)
        elif level == 15: return (33, 40)
        elif level == 16: return (67, 45)
        elif level == 17: return (100, 50)
        elif level == 18: return (500, 100)
        elif level >= 19: return (2500, 250)
        else:
            raise ValueError(f'Invalid level: {repr(level)}')

    def compress(data, level=None, *, iterations=None, maxsplit=None, **kw):
        if level is not None and (iterations is not None or maxsplit is not None):
            raise ValueError("L'argument `level` ne peut pas être utilisé avec `iterations` et/ou `maxsplit` !")

        # définir les paramètres selon le niveau ou par défaut
        if iterations is None and maxsplit is None:
            if level is None: level = 10
            elif level < 10: return _compress_with_gzip(data, level)
            iterations, maxsplit = _level_to_params(level)

        if maxsplit is not None:
            kw['maxsplit'] = maxsplit

        if iterations is not None:
            kw['iterations'] = iterations

        return _compress_with_zopfli(data, **kw)

except (ImportError, ModuleNotFoundError):
    def compress(data, level=9, **kw):
        return _compress_with_gzip(data, level)
