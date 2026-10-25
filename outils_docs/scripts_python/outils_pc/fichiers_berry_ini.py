"""Lecture des .ini PlatformIO pour la page « Fichiers Berry par env » : listes de fichiers et provenance.

Pourquoi un lecteur ligne a ligne (et pas configparser comme build_envs) : pour reecrire une liste, il
faut savoir dans quel fichier, quelle section et a quelle LIGNE chaque entree est ecrite. configparser
rend la valeur, pas sa position. La syntaxe suivie est celle que lit PlatformIO (ConfigParser par defaut,
`inline_comment_prefixes=("#", ";")`, platformio/project/config.py:97) :
  - `option = valeur` en colonne 0 ouvre une option ; une ligne indentee la continue ;
  - une ligne de commentaire entiere (`;` ou `#`) ou une ligne vide n'interrompt PAS l'option : la
    ligne indentee suivante la continue encore ;
  - `;`/`#` precede d'un blanc commence un commentaire de fin de ligne (`opt =;x` vaut donc `;x`).
Resolution d'une option comme `walk_options` (platformio/project/config.py:170) : la section, puis ses
`extends` en profondeur, le DERNIER parent cite d'abord, puis la section `[env]` pour toute section `env:`.
Une meme section definie dans plusieurs fichiers est fusionnee option par option (le dernier fichier
de FICHIERS_INI l'emporte), comme PlatformIO avec ses extra_configs.

References developpees : `${env:X.option}` (option resolue par la chaine `extends` de X) et
`${section.option}` (section ordinaire, ex. `[berry_commun]`). Aucune ecriture ici.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from build_envs import FICHIER_CENV, FICHIERS_INI

ENTETE = re.compile(r"\[([^\]]+)\]\s*$")
OPTION = re.compile(r"([^\s=;#][^=]*?)\s*=(.*)$")
REFERENCE = re.compile(r"\$\{([^.}]+)\.([^}]+)\}$")
COMMENTAIRE_EN_LIGNE = re.compile(r"\s[;#]")
SANS_FICHIER = "no_files"      # valeur de l'amont qui veut dire « aucun fichier »


@dataclass
class Entree:
    chemin: str          # chemin tel qu'ecrit, separateurs normalises en /
    section: str         # section ou la ligne est ecrite (env:x, berry_commun...)
    option: str          # option ou la ligne est ecrite (socle, custom_berry_solidify...)
    fichier: str         # .ini qui porte la ligne
    ligne: int           # index (0) de la ligne dans ce fichier
    commentaire: str     # commentaire de fin de ligne, "" si aucun


@dataclass
class Option:
    fichier: str
    section: str
    nom: str
    debut: int                                   # index de la ligne `nom = ...`
    morceaux: list = field(default_factory=list)  # [(index de ligne, valeur, commentaire)]

    @property
    def fin(self):
        """Index de la derniere ligne qui porte une valeur (la ligne `nom =` si la valeur est vide)."""
        return self.morceaux[-1][0] if self.morceaux else self.debut


def decoupe(texte):
    """Lignes sans fin de ligne, coupees sur CRLF ou LF seulement (pas splitlines, qui coupe aussi sur
    \\x0c, \\x1c...) : l'ecriture (fichiers_berry_ecriture) recoud avec la meme regle, les index concordent.
    Un fichier termine par une fin de ligne donne une derniere ligne vide."""
    return re.split(r"\r?\n", texte)


def normalise(chemin):
    """Chemin compare entre listes : separateurs en /, sans / final (`data/bureau/<carte>/` dans le cenv)."""
    return chemin.replace("\\", "/").rstrip("/")


def _coupe_commentaire(texte):
    m = COMMENTAIRE_EN_LIGNE.search(texte)
    if not m:
        return texte.strip(), ""
    return texte[:m.start()].strip(), texte[m.end():].strip()


class Ini:
    def __init__(self, racine):
        self.racine = Path(racine)
        self.lignes = {}        # {fichier: [lignes sans fin de ligne]}
        self.sections = {}      # {section: {option: Option}}, fusion de tous les fichiers
        self.ordre_cenv = []    # sections env:* du cenv dans l'ordre du fichier

    def _lit(self, fichier):
        chemin = self.racine / fichier
        if not chemin.is_file():
            return
        lignes = decoupe(chemin.read_bytes().decode("utf-8", errors="surrogateescape"))
        self.lignes[fichier] = lignes
        section, courante = None, None
        for i, brute in enumerate(lignes):
            nette = brute.strip()
            if not nette or nette[0] in ";#":
                continue                                   # vide ou commentaire : l'option continue
            m = ENTETE.match(brute) if not brute[0].isspace() else None
            if m:
                section, courante = m.group(1).strip(), None
                self.sections.setdefault(section, {})
                if fichier == FICHIER_CENV and section.startswith("env:") and section not in self.ordre_cenv:
                    self.ordre_cenv.append(section)
                continue
            if section is None:
                continue
            if brute[0].isspace():
                if courante is not None:
                    valeur, commentaire = _coupe_commentaire(brute)
                    if valeur:
                        courante.morceaux.append((i, valeur, commentaire))
                continue
            m = OPTION.match(brute)
            if not m:
                courante = None
                continue
            courante = Option(fichier, section, m.group(1).strip(), i)
            valeur, commentaire = _coupe_commentaire(m.group(2))     # `=` juste avant : `opt =;x` vaut `;x`
            if valeur:
                courante.morceaux.append((i, valeur, commentaire))
            self.sections[section][courante.nom] = courante     # le dernier fichier l'emporte

    def chaine(self, env):
        """Sections consultees pour une option de l'env, dans l'ordre de PlatformIO (walk_options) : l'env, ses
        `extends` en profondeur (le dernier parent cite d'abord), puis `[env]`. Un cycle est coupe."""
        racine = "env:" + env if not env.startswith("env:") else env
        res, pile = [], ["env", racine]
        while pile:
            nom = pile.pop()
            if nom in res or nom not in self.sections:
                continue
            res.append(nom)
            ext = self.sections[nom].get("extends")
            parents = ext.morceaux[0][1] if ext and ext.morceaux else ""
            pile.extend(p.strip() for p in parents.split(",") if p.strip())
        return res

    def definie_dans(self, env, option):
        """Premiere section de la chaine de l'env qui definit l'option, None si aucune."""
        return next((s for s in self.chaine(env) if option in self.sections[s]), None)

    def envs_cenv(self):
        return [s[len("env:"):] for s in self.ordre_cenv]


def lit_sections(racine):
    ini = Ini(racine)
    for fichier in FICHIERS_INI:
        ini._lit(fichier)
    return ini


def _option_resolue(ini, section, option):
    """L'Option qui donne la valeur de `section.option` (chaine extends pour un env:), ou None."""
    if section.startswith("env:"):
        definie = ini.definie_dans(section, option)
        return ini.sections[definie][option] if definie else None
    return ini.sections.get(section, {}).get(option)


def _developpe(ini, section, option, pile, traverses, consultees=None):
    opt = _option_resolue(ini, section, option)
    if consultees is not None and section.startswith("env:"):
        ch = ini.chaine(section)                 # sections lues avant de trouver l'option (ou toutes)
        consultees.update(ch[:ch.index(opt.section) + 1] if opt else ch)
    if opt is None:
        return []
    cle = (opt.section, opt.nom)
    if cle in pile:
        raise ValueError(f"reference circulaire : {' -> '.join(s + '.' + o for s, o in pile + [cle])}")
    traverses.add(cle)
    res = []
    for i, valeur, commentaire in opt.morceaux:
        ref = REFERENCE.match(valeur)
        if ref:
            res += _developpe(ini, ref.group(1), ref.group(2), pile + [cle], traverses, consultees)
        elif valeur != SANS_FICHIER:
            res.append(Entree(normalise(valeur), opt.section, opt.nom, opt.fichier, i, commentaire))
    return res


def resout(ini, env, option):
    """Entrees de la valeur resolue de `option` pour l'env, references developpees. ValueError sur cycle."""
    return _developpe(ini, "env:" + env, option, [], set())


def traverses(ini, env, option):
    """Ensemble des (section, option) lus pour resoudre `option` de l'env."""
    vus = set()
    _developpe(ini, "env:" + env, option, [], vus)
    return vus


def heritiers(ini, env, option):
    """Envs du cenv dont la valeur de `option` changerait si on l'ecrivait dans la section de l'env : la
    resolution de leur option consulte cette section, par `extends` (avant la section qui la definit) ou
    par une reference `${env:<env>.option}`. Une base a donc ses cartes pour heritiers."""
    section, res = "env:" + env, []
    for autre in ini.envs_cenv():
        consultees = set()
        try:
            _developpe(ini, "env:" + autre, option, [], set(), consultees)
        except ValueError:
            continue
        if section in consultees:
            res.append(autre)
    return sorted(res)


def envs_touches(ini, section, option, options_env):
    """Envs du cenv dont la valeur resolue d'une des `options_env` (une option ou plusieurs) passe par
    `section.option`, tries : une liste de [berry_commun] peut servir a l'exclude d'un env et au solidify d'un
    autre. Un env dont la resolution boucle est ignore (il ne peut pas etre construit de toute facon)."""
    options_env = (options_env,) if isinstance(options_env, str) else tuple(options_env)
    res = []
    for env in ini.envs_cenv():
        for option_env in options_env:
            try:
                if (section, option) in traverses(ini, env, option_env):
                    res.append(env)
                    break
            except ValueError:
                continue
    return sorted(res)
