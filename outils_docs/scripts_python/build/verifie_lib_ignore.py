"""Garde du lib_ignore des envs personnels : refuse un build dont le lib_ignore ignore une bibliotheque utilisee.

Pourquoi : le LDF de PlatformIO (mode chain) tire toute bibliotheque dont un en-tete est inclus, meme sous un
#ifdef inactif ; l'ignorer (lib_ignore) allege le scan et la compilation (plan tasks/plans/lib-ignore-cuve.md :
scan de 21 min 42 a 7 min 36 sur la cuve). Mais ignorer une bibliotheque reellement incluse casse la
compilation 12 minutes plus tard (2026-10-31 : esp_wireguard_tasmota, dont poly1305-donna.h est inclus par
xdrv_52_3_berry_crypto.ino sous USE_BERRY seul). Ce controle tourne au pre-build, AVANT le scan.

Methode :
  1. defines actifs de l'env : preprocesseur croise de la puce (-E -dM), comme pio-tools/dump-defines.py, avec
     les -D des build_flags et le vrai sdkconfig.h du framework pour cette puce ;
  2. chaque #include de tasmota/ et des bibliotheques NON ignorees est evalue sous ses gardes #if/#ifdef
     (logique a trois valeurs : vrai, faux, incertain ; une macro inconnue = incertain) ;
  3. une bibliotheque ignoree est fautive si l'un de ses en-tetes est inclus sous une garde vraie ou incertaine
     et ne se trouve nulle part ailleurs (bibliotheque gardee, tasmota/, chaine de compilation, framework).

Controle (pre-script) : seulement les bibliotheques que l'env ignore EN PLUS de son parent (`extends`), et
seulement pour les envs de platformio_tasmota_cenv.ini. Erreur -> build arrete avec le fichier et la ligne.
Etablir une liste (Claude, a la main) : python verifie_lib_ignore.py <env> --propose
Banc : test_verifie_lib_ignore.py.
"""

import glob
import json
import os
import re
import subprocess
import sys
import time

PACKAGES = os.path.join(os.path.expanduser("~"), ".platformio", "packages")
EXT_SOURCES = (".h", ".hpp", ".c", ".cpp", ".ino")
DOSSIERS_IGNORES = {"examples", "example", "test", "tests", "extras", "docs", "doc", "tools", "generate"}
# Macros dont les defines de l'env font foi : absentes = non definies. Toute autre macro inconnue est incertaine
# (ESP_IDF_VERSION_MAJOR, SOC_*, macros propres d'une bibliotheque...).
FAIT_FOI = re.compile(r"^(USE_\w+|FIRMWARE_\w+|ESP8266|ARDUINO_ARCH_ESP8266|ARDUINO_ARCH_AVR|__AVR\w*)$")
INCLUDE = re.compile(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]')
INCLUDE_RAPIDE = re.compile(r'#\s*include\s*[<"]([^>"]+)[>"]')
DIRECTIVE = re.compile(r"^\s*#\s*(ifdef|ifndef|if|elif|else|endif|define|undef)\b\s*(.*)$")
VRAI, FAUX, INCERTAIN = True, False, None


# ---------- evaluation des gardes (logique a trois valeurs) ----------

def et(a, b):
    if a is FAUX or b is FAUX:
        return FAUX
    return VRAI if a is VRAI and b is VRAI else INCERTAIN


def ou(a, b):
    if a is VRAI or b is VRAI:
        return VRAI
    return FAUX if a is FAUX and b is FAUX else INCERTAIN


def non(a):
    return INCERTAIN if a is INCERTAIN else not a


class Contexte:
    """Defines de l'env + macros #define'es quelque part dans les sources (`connues`) : une macro absente des
    defines et definie nulle part est fausse si `sures` (sources de tasmota/), sinon seulement si FAIT_FOI."""

    def __init__(self, defines, connues=(), sures=False):
        self.defines, self.connues, self.sures = defines, set(connues), sures

    def fait_foi(self, nom):
        return FAIT_FOI.match(nom) or (self.sures and nom not in self.connues)


def est_defini(nom, ctx, locales):
    if nom in locales:
        return locales[nom]
    if nom in ctx.defines:
        return VRAI
    return FAUX if ctx.fait_foi(nom) else INCERTAIN


ESSAIS_DEFINED, ESSAIS_VALEUR = (0, 1), (0, 1, 5, 100000, -1)


def evalue(expr, ctx, locales):
    """Valeur d'une expression #if : VRAI, FAUX ou INCERTAIN. Chaque macro inconnue prend plusieurs valeurs
    d'essai ; un resultat identique pour toutes est sur (`0 && X >= 5` est faux quel que soit X)."""
    inconnues = []                                   # [(nom de variable python, valeurs d'essai)]

    def inconnue(essais):
        inconnues.append(("_u%d" % len(inconnues), essais))
        return " %s " % inconnues[-1][0]

    def remplace_defined(m):
        v = est_defini(m.group(1) or m.group(2), ctx, locales)
        return inconnue(ESSAIS_DEFINED) if v is INCERTAIN else (" 1 " if v else " 0 ")

    expr = re.sub(r"\bdefined\s*\(\s*(\w+)\s*\)|\bdefined\s+(\w+)", remplace_defined, expr)
    if re.search(r"[A-Za-z_]\w*\s*\(", expr):        # macro fonction (ESP_IDF_VERSION_VAL, __has_include...)
        return INCERTAIN

    def remplace_nom(m):
        nom = m.group(0)
        if nom.startswith("_u") and nom[2:].isdigit():
            return nom
        if nom in ("true", "false"):
            return " 1 " if nom == "true" else " 0 "
        if locales.get(nom) is FAUX:
            return " 0 "
        if nom not in ctx.defines:
            if locales.get(nom):
                return inconnue(ESSAIS_VALEUR)
            return " 0 " if ctx.fait_foi(nom) else inconnue(ESSAIS_VALEUR)
        valeur = ctx.defines[nom]
        if valeur is None:
            return " 1 "                             # defini sans valeur : rarement compare a un nombre
        nombre = re.fullmatch(r"\(?\s*(-?(?:0[xX][0-9a-fA-F]+|\d+))[uUlL]*\s*\)?", valeur.strip())
        return " %d " % int(nombre.group(1), 0) if nombre else inconnue(ESSAIS_VALEUR)

    expr = re.sub(r"\b(0[xX][0-9a-fA-F]+|\d+)[uUlL]+\b", r"\1", expr)
    expr = re.sub(r"\b[A-Za-z_]\w*\b", remplace_nom, expr)
    py = expr.replace("&&", " and ").replace("||", " or ").replace("/", "//")
    py = re.sub(r"!(?!=)", " not ", py)
    combinaisons = [{}]
    for nom, essais in inconnues:
        combinaisons = [dict(c, **{nom: e}) for c in combinaisons for e in essais]
        if len(combinaisons) > 500:
            return INCERTAIN
    resultats = set()
    try:
        for c in combinaisons:
            resultats.add(bool(eval(py, {"__builtins__": {}}, c)))  # noqa: S307 - nombres et operateurs seuls
    except Exception:                                # noqa: BLE001 - expression non comprise : incertain
        return INCERTAIN
    return resultats.pop() if len(resultats) == 1 else INCERTAIN


def sans_commentaires(texte):
    texte = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), texte, flags=re.S)
    return re.sub(r"//[^\n]*", "", texte).replace("\\\n", " ")


def includes_actifs(texte, ctx):
    """[(en-tete, numero de ligne, VRAI|INCERTAIN)] des #include dont la garde n'est pas fausse."""
    locales, pile, actif, resultat = {}, [], VRAI, []
    for numero, ligne in enumerate(sans_commentaires(texte).split("\n"), 1):
        if "#" not in ligne:
            continue
        m = INCLUDE.match(ligne)
        if m:
            if actif is not FAUX:
                resultat.append((m.group(1), numero, actif))
            continue
        d = DIRECTIVE.match(ligne)
        if not d:
            continue
        mot, reste = d.group(1), d.group(2).strip()
        if mot in ("ifdef", "ifndef", "if"):
            if mot == "if":
                cond = evalue(reste, ctx, locales)
            else:
                cond = est_defini(reste.split()[0] if reste else "", ctx, locales)
                cond = non(cond) if mot == "ifndef" else cond
            pile.append([actif, cond])                 # [actif du parent, une branche deja prise ?]
            actif = et(actif, cond)
        elif mot in ("elif", "else") and pile:
            parent, prise = pile[-1]
            cond = VRAI if mot == "else" else evalue(reste, ctx, locales)
            pile[-1][1] = ou(prise, cond)
            actif = et(parent, et(non(prise), cond))
        elif mot == "endif" and pile:
            actif = pile.pop()[0]
        elif mot in ("define", "undef") and actif is not FAUX and reste:
            nom = re.match(r"\w+", reste)
            if nom:
                locales[nom.group(0)] = (VRAI if actif is VRAI else INCERTAIN) if mot == "define" else FAUX
    return resultat


# ---------- bibliotheques et sources ----------

class Bibliotheque:
    def __init__(self, dossier):
        self.dossier = dossier
        self.noms = {os.path.basename(dossier)}
        self.nom = os.path.basename(dossier)          # nom vu par le LDF : celui du manifeste s'il y en a un
        self.plateformes = None
        manifeste = os.path.join(dossier, "library.json")
        proprietes = os.path.join(dossier, "library.properties")
        if os.path.isfile(manifeste):
            try:
                with open(manifeste, encoding="utf-8", errors="ignore") as f:
                    donnees = json.load(f)
                self.nom = donnees.get("name", "").strip() or self.nom
                self.noms.add(self.nom)
                p = donnees.get("platforms")
                self.plateformes = None if p in (None, "*") else ([p] if isinstance(p, str) else p)
            except ValueError:
                pass
        elif os.path.isfile(proprietes):
            with open(proprietes, encoding="utf-8", errors="ignore") as f:
                texte = f.read()
            m = re.search(r"^name\s*=\s*(.+)$", texte, re.M)
            if m:
                self.nom = m.group(1).strip()
                self.noms.add(self.nom)
            m = re.search(r"^architectures\s*=\s*(.+)$", texte, re.M)
            if m and "*" not in m.group(1):
                self.plateformes = ["espressif32" if "esp32" in a else "espressif8266" if "esp8266" in a else a
                                    for a in (x.strip() for x in m.group(1).split(","))]
        self.noms.discard("")
        self.fichiers = list(sources(dossier))
        self.entetes = [os.path.relpath(f, dossier).replace("\\", "/") for f in self.fichiers
                        if f.endswith((".h", ".hpp"))]

    def compatible(self, plateforme):
        return self.plateformes is None or plateforme in self.plateformes

    def fournit(self, include):
        """Vrai si `include` (chaine d'un #include) designe un en-tete de cette bibliotheque."""
        return any(e == include or e.endswith("/" + include) for e in self.entetes)


def sources(dossier):
    for racine, dossiers, fichiers in os.walk(dossier):
        dossiers[:] = [d for d in dossiers if d.lower() not in DOSSIERS_IGNORES and not d.startswith(".")]
        for f in fichiers:
            if f.endswith(EXT_SOURCES):
                yield os.path.join(racine, f)


def bibliotheques(projet, dossiers_lib):
    """Toutes les bibliotheques : chaque sous-dossier des dossiers de bibliotheques de l'env."""
    vues = []
    for d in dossiers_lib:
        d = os.path.join(projet, d)
        if os.path.isdir(d):
            vues += [Bibliotheque(os.path.join(d, s)) for s in sorted(os.listdir(d))
                     if os.path.isdir(os.path.join(d, s))]
    return vues


def lit(fichier):
    with open(fichier, encoding="utf-8", errors="ignore") as f:
        return f.read()


# ---------- configuration de l'env ----------

def options_env(config, nom_env):
    """Options utiles de l'env, resolues par ProjectConfig."""
    s = "env:" + nom_env
    def liste(opt):
        return config.get(s, opt) if config.has_option(s, opt) else []
    plateforme = "espressif8266" if "8266" in config.get(s, "platform") else "espressif32"
    dossiers = [config.get("platformio", "lib_dir")] if config.has_option("platformio", "lib_dir") else ["lib"]
    with open(os.path.join(os.path.dirname(config.path), "boards", config.get(s, "board") + ".json"),
              encoding="utf-8") as f:
        build = json.load(f)["build"]
    return {"plateforme": plateforme, "mcu": build.get("mcu", "esp32"),
            "memoire": (build.get("arduino") or {}).get("memory_type", ""), "build_flags": liste("build_flags"),
            "lib_ignore": liste("lib_ignore"), "lib_deps": liste("lib_deps"),
            "lib_dirs": dossiers + [d for d in liste("lib_extra_dirs") if d]}


def compilateur(mcu):
    if mcu == "esp8266":
        return os.path.join(PACKAGES, "toolchain-xtensa", "bin", "xtensa-lx106-elf-g++.exe")
    if mcu in ("esp32", "esp32s2", "esp32s3"):
        return os.path.join(PACKAGES, "toolchain-xtensa-esp-elf", "bin", f"xtensa-{mcu}-elf-g++.exe")
    return os.path.join(PACKAGES, "toolchain-riscv32-esp", "bin", "riscv32-esp-elf-g++.exe")


def defines_env(projet, opts):
    """{nom: valeur ou None} des macros actives de l'env (preprocesseur croise, comme dump-defines.py)."""
    mcu = opts["mcu"]
    flags = re.findall(r"-D\s*\S+", " ".join(opts["build_flags"]))
    inc = ["-I" + os.path.join(projet, d) for d in ("include", os.path.join("tasmota", "include"), "tasmota")]
    if mcu == "esp8266":
        flags.append("-DESP8266")
    else:
        flags.append("-DESP32")
        memoire = opts["memoire"]
        sdk = sorted(glob.glob(os.path.join(PACKAGES, "framework-arduinoespressif32", "tools", "esp32-arduino-libs",
                                            mcu, "*", "include", "sdkconfig.h")),
                     key=lambda p: (memoire not in p, p))
        inc = (["-I" + os.path.dirname(sdk[0])] if sdk else []) + inc
    commande = [compilateur(mcu), "-E", "-dM", "-x", "c++"] + flags + inc
    for h in ("tasmota/include/tasmota.h", "tasmota/my_user_config.h", "include/tasmota_options.h",
              "tasmota/include/i18n.h"):
        commande += ["-include", os.path.join(projet, h)]
    sortie = subprocess.run(commande + ["-"], input="", capture_output=True, text=True, timeout=120).stdout
    defines = {m.group(1): m.group(2) for m in re.finditer(r"^#define (\w+)(?:\([^)]*\))?(?: (.*))?$", sortie, re.M)}
    if "USE_WEBSERVER" not in defines and "USE_LIGHT" not in defines:
        raise RuntimeError(f"preprocesseur sans les defines de Tasmota ({commande[0]})")
    return defines


# ---------- analyse ----------

class Analyse:
    """Inclusions actives des sources compilees (tasmota/ + bibliotheques gardees) d'un env."""

    def __init__(self, projet, opts, defines):
        self.projet, self.opts = projet, opts
        self.libs = [b for b in bibliotheques(projet, opts["lib_dirs"]) if b.compatible(opts["plateforme"])]
        self.tasmota = list(sources(os.path.join(projet, "tasmota")))
        self._noms = {}                              # fichier -> noms de base des en-tetes inclus (sans gardes)
        connues = set()
        for f in self.tasmota:
            connues.update(re.findall(r"^\s*#\s*define\s+(\w+)", lit(f), re.M))
        self.ctx_tasmota = Contexte(defines, connues, sures=True)
        self.ctx_lib = Contexte(defines)
        self._systeme = None
        self._par_nom = {}                           # nom de base d'en-tete -> bibliotheques qui le fournissent
        for b in self.libs:
            for e in b.entetes:
                self._par_nom.setdefault(os.path.basename(e), []).append(b)

    def atteignables(self, gardees):
        """Bibliotheques gardees que le LDF peut atteindre depuis tasmota/ (toute inclusion compte, gardes
        ignorees : sur-ensemble prudent du graphe). Une bibliotheque tiree seulement par une ignoree n'y est pas."""
        gardees, vues = set(gardees), set()
        a_lire = list(self.tasmota)
        while a_lire:
            for nom in self.noms_inclus(a_lire.pop()):
                for b in self._par_nom.get(nom, ()):
                    if b in gardees and b not in vues:
                        vues.add(b)
                        a_lire += b.fichiers
        return vues

    def ignoree(self, lib, ignores):
        return bool(lib.noms & set(ignores))

    def noms_inclus(self, fichier):
        noms = self._noms.get(fichier)
        if noms is None:
            noms = self._noms[fichier] = {os.path.basename(i) for i in INCLUDE_RAPIDE.findall(lit(fichier))}
        return noms

    def ailleurs(self, include, gardees):
        """Vrai si l'en-tete se trouve hors des bibliotheques ignorees (gardees, tasmota/, chaine, framework)."""
        if any(b.fournit(include) for b in gardees):
            return True
        if any(os.path.isfile(os.path.join(self.projet, d, include))
               for d in ("include", "tasmota", os.path.join("tasmota", "include"))):
            return True
        if self._systeme is None:
            # shortcut: index par nom de fichier, sans les chemins d'inclusion reels ; suffit pour stdint.h & co
            self._systeme = set()
            fw = os.path.join(PACKAGES, "framework-arduinoespressif32")
            for d in [os.path.dirname(os.path.dirname(compilateur(self.opts["mcu"]))), os.path.join(fw, "cores"),
                      os.path.join(fw, "libraries"), os.path.join(fw, "tools", "esp32-arduino-libs", self.opts["mcu"])]:
                for _, _, fichiers in os.walk(d):
                    self._systeme.update(f for f in fichiers if f.endswith((".h", ".hpp")) or "." not in f)
        return os.path.basename(include) in self._systeme

    def utilisations(self, ignores):
        """{nom de bibliotheque ignoree: [(fichier, ligne, en-tete, etat)]} des inclusions qui la rendent necessaire."""
        visees = [b for b in self.libs if self.ignoree(b, ignores)]
        gardees = [b for b in self.libs if not self.ignoree(b, ignores)]
        filtre = {os.path.basename(e) for b in visees for e in b.entetes}
        trouve = {}
        fichiers = [(f, self.ctx_tasmota) for f in self.tasmota] + [
            (f, self.ctx_lib) for b in self.atteignables(gardees) for f in b.fichiers]
        for fichier, ctx in fichiers:
            if not self.noms_inclus(fichier) & filtre:
                continue
            for include, ligne, etat in includes_actifs(lit(fichier), ctx):
                if os.path.basename(include) not in filtre:
                    continue
                for b in visees:
                    if b.fournit(include) and not self.ailleurs(include, gardees):
                        nom = sorted(b.noms & set(ignores))[0]
                        trouve.setdefault(nom, []).append((os.path.relpath(fichier, self.projet), ligne, include, etat))
        return trouve

    def propose(self):
        """Plus grand ensemble ignorable : on part de toutes les bibliotheques, on retire celles qu'une source
        gardee inclut, jusqu'a stabilite. Renvoie (ignorables, {gardee: premiere raison})."""
        deps = {re.split(r"[@=\s]", d)[0].split("/")[-1] for d in self.opts["lib_deps"]}
        candidats = {b.nom for b in self.libs if not b.noms & deps}
        raisons = {}
        while True:
            u = self.utilisations(sorted(candidats))
            if not u:
                return candidats, raisons
            for nom, lignes in u.items():
                candidats.discard(nom)
                raisons[nom] = lignes[0]

    def a_lister(self, ignorables):
        """Les ignorables que le LDF tirerait (incluses, gardes ignorees, par tasmota/ ou une gardee atteignable) :
        une ignorable atteinte seulement par une autre ignorable n'a pas besoin d'etre nommee."""
        gardees = [b for b in self.libs if b.nom not in ignorables]
        noms = set()
        for f in self.tasmota + [f for b in self.atteignables(gardees) for f in b.fichiers]:
            noms |= self.noms_inclus(f)
        return {b.nom for b in self.libs if b.nom in ignorables and any(os.path.basename(e) in noms for e in b.entetes)}


# ---------- garde du pre-build ----------

def ajouts_env(config, nom_env, personnels=()):
    """Bibliotheques que le cenv ajoute au lib_ignore de l'env : par rapport au premier ancetre (`extends`) qui
    n'est pas un env personnel, pour qu'une liste posee sur une base personnelle soit controlee aussi."""
    s = "env:" + nom_env
    propres = config.get(s, "lib_ignore") if config.has_option(s, "lib_ignore") else []
    herites, courant, vus = set(), s, set()
    while config.has_option(courant, "extends") and courant not in vus:
        vus.add(courant)
        parent = config.get(courant, "extends")[0]
        parent = parent if parent.startswith("env:") else "env:" + parent
        if parent[4:] not in personnels:
            herites = set(config.get(parent, "lib_ignore")) if config.has_option(parent, "lib_ignore") else set()
            break
        courant = parent
    return [n for n in propres if n not in herites and "/" not in n]


def envs_personnels(projet):
    with open(os.path.join(projet, "platformio_tasmota_cenv.ini"), encoding="utf-8") as f:
        return set(re.findall(r"^\[env:([^\]]+)\]", f.read(), re.M))


def controle(env):
    """Pre-script : arrete le build si le lib_ignore de l'env (ajouts au parent) ignore une bibliotheque utilisee."""
    from colorama import Fore
    projet, nom_env = env.subst("$PROJECT_DIR"), env.subst("$PIOENV")
    personnels = envs_personnels(projet)
    if nom_env not in personnels:
        return
    config = env.GetProjectConfig()
    ajouts = ajouts_env(config, nom_env, personnels)
    if not ajouts:
        return
    # Les lignes « lib_ignore de <env> : » sont lues par la page build (outils_pc/build_progression.py) :
    # detail de l'etape Pre-build, et les lignes ✗ dans l'extrait d'erreur.
    print(Fore.CYAN + f"… lib_ignore de {nom_env} : controle de {len(ajouts)} bibliotheque(s)…", flush=True)
    debut = time.monotonic()
    try:
        opts = options_env(config, nom_env)
        trouve = Analyse(projet, opts, defines_env(projet, opts)).utilisations(ajouts)
    except (OSError, RuntimeError, subprocess.SubprocessError, KeyError) as e:
        print(Fore.YELLOW + f"⚠ lib_ignore de {nom_env} : controle impossible ({e}), build laisse continuer")
        return
    duree = f"{time.monotonic() - debut:.0f} s"
    if not trouve:
        print(Fore.GREEN + f"✔ lib_ignore de {nom_env} : {len(ajouts)} bibliotheque(s) ignoree(s), aucune utilisee"
                           f" ({duree})")
        return
    for nom, lignes in sorted(trouve.items()):
        for fichier, ligne, include, etat in lignes[:3]:
            garde = "garde active" if etat is VRAI else "garde incertaine"
            print(Fore.RED + f"✗ lib_ignore de {nom_env} : {nom} ignoree mais utilisee - {fichier}:{ligne} "
                             f"#include \"{include}\" ({garde})")
    print(Fore.RED + f"✗ lib_ignore de {nom_env} : retirer {', '.join(sorted(trouve))} du lib_ignore de l'env "
                     "(platformio_tasmota_cenv.ini), sinon la compilation echouerait")
    env.Exit(1)


def main(arguments):
    from platformio.project.config import ProjectConfig
    projet = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    os.chdir(projet)
    config = ProjectConfig(os.path.join(projet, "platformio.ini"))
    nom_env = arguments[0]
    opts = options_env(config, nom_env)
    analyse = Analyse(projet, opts, defines_env(projet, opts))
    if "--propose" in arguments:
        ignorables, raisons = analyse.propose()
        deja = set(opts["lib_ignore"])
        utiles = analyse.a_lister(ignorables) - deja
        print(f"== {nom_env} : {len(ignorables)} ignorables, a ajouter au lib_ignore (tirees par le LDF) : {len(utiles)}")
        for n in sorted(utiles):
            print("  +", n)
        print("== gardees (premiere inclusion active)")
        for n, (fichier, ligne, include, etat) in sorted(raisons.items()):
            print(f"  {n} <- {fichier}:{ligne} {include}{'' if etat is VRAI else ' (incertain)'}")
        return 0
    trouve = analyse.utilisations(ajouts_env(config, nom_env, envs_personnels(projet)))
    for nom, lignes in sorted(trouve.items()):
        for l in lignes[:3]:
            print(nom, l)
    return 1 if trouve else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
