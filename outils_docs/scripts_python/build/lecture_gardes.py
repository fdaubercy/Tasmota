"""Lecture des gardes du preprocesseur pour verifie_lib_ignore.py : quels #include d'un fichier C/C++ sont
actifs pour un env, sous ses #if/#ifdef, en logique a trois valeurs (vrai, faux, incertain).

Separe de verifie_lib_ignore.py (limite des 500 lignes du depot) ; importe par lui, meme dossier.
Banc : test_verifie_lib_ignore.py.
"""

import re

# Macros dont les defines de l'env font foi : absentes = non definies (voir aussi Contexte).
FAIT_FOI = re.compile(r"^(USE_\w+|FIRMWARE_\w+|ESP8266|ARDUINO_ARCH_ESP8266|ARDUINO_ARCH_AVR|__AVR\w*)$")
INCLUDE = re.compile(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]')
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
    """Defines de l'env + `options` de configuration de Tasmota (CONFIG_TASMOTA) + `definies` (macros #define'es
    quelque part : tasmota/, bibliotheques lues, framework, chaine de compilation). Une macro absente des defines
    est fausse si FAIT_FOI, si c'est une option, ou si personne ne la definit (elle ne viendrait que d'un -D, et
    les -D sont dans les defines : VSCODE_DEV, SIMPLE_RES_TOUCH). Sinon incertaine : ESP_IDF_VERSION_MAJOR vient
    du framework, que le preprocesseur de defines_env ne lit pas (la croire fausse a laisse passer le P4)."""

    def __init__(self, defines, options=(), definies=None):
        self.defines, self.options, self.definies = defines, set(options), definies

    def fait_foi(self, nom):
        return (FAIT_FOI.match(nom) or nom in self.options
                or (self.definies is not None and nom not in self.definies))


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


# Un seul passage de gauche a droite, comme le compilateur : `//*****` est un commentaire de ligne, pas l'ouverture
# d'un bloc (le retirer en deux passes a efface xdrv_50_filesystem.ino jusqu'a son #include <ESPFtpServer.h>).
JETONS = re.compile(r'R"([^(\s]{0,16})\(.*?\)\1"|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|//[^\n]*|/\*.*?\*/', re.S)


def sans_commentaires(texte):
    """Texte sans commentaires, lignes continuees (\\) jointes ; meme nombre de lignes que l'original."""
    texte = JETONS.sub(lambda m: "\n" * m.group(0).count("\n") if m.group(0)[0] == "/" else m.group(0), texte)
    lignes, sortie, report = texte.split("\n"), [], 0
    for ligne in lignes:
        if sortie and sortie[-1].endswith("\\"):
            sortie[-1] = sortie[-1][:-1] + " " + ligne
            report += 1
            continue
        sortie += [""] * report + [ligne]
        report = 0
    return "\n".join(sortie + [""] * report)


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
