r"""Controle de la charte des logs Berry (audit Berry P7.6) : AVERTISSEMENTS, jamais des erreurs.

Appele par verifie_berry.py (donc par le hook d'edition de Claude et la tache VS Code) ; utilisable seul :
  python charte_logs.py f1.be f2.be       avertissements de ces fichiers (code de sortie toujours 0)

La charte vit en tete de data/fs/logFonctions.be (copies : CLAUDE.md, outils_docs/README.md).
Format : data/fs/x.be:42: avertissement: [regle] message   (le problemMatcher "berry" de .vscode/tasks.json
ne lit que les lignes "erreur:" : ces avertissements ne vont pas dans l'onglet Problemes).

REGLES CONTROLEES
-----------------
  log-direct      log(), tasmota.log() ou print() dans un except : contourne le seuil du module (regle 1)
  niveau          niveau absent, ou ecrit en chiffre au lieu de LOG_LEVEL_* (regle 6)
  prefixe         message litteral qui ne commence pas par NOM_MAJ_SNAKE: (regle 2)
  erreur-prefixe  log de niveau erreur dans un except sans _ERREUR dans le prefixe (regle 2)
  info-frequent   info dans every_50ms/100ms/250ms/every_second/web_sensor/json_append (regle 4)
  non-garde       debug/detail qui construit json.dump ou tohex hors garde actif() (regle 5)

LIMITES (lecture du texte, rien n'est execute)
----------------------------------------------
- Un message passe par une variable (msg) n'est pas lu : ni prefixe ni _ERREUR verifies.
- Un niveau en variable (enrobeur xxxFonctions.log(msg, niveau), ternaire de LOG_LEVEL_*) est admis :
  les regles qui dependent du niveau sont alors sautees.
- Garde reconnue : un if/elif (ou une ternaire dans le message) dont la condition appelle actif(), ou
  nomme une variable affectee depuis actif() dans le fichier (var detail = logFonctions.actif(...)).
- log() direct admis dans un if/else dont la condition nomme logFonctions : repli quand le module
  n'est pas encore charge (demarrage.be).
- Les callbacks de reception (regles ModbusReceived, UDP...) ne sont pas reconnus par leur nom : la
  regle 4 n'y est pas controlee.
"""
import re
import sys
from pathlib import Path

# Callbacks appeles en boucle par Tasmota (regle 4)
FREQUENTS = {"every_50ms", "every_100ms", "every_250ms", "every_second", "web_sensor", "json_append"}
NIVEAUX = {"LOG_LEVEL_ERREUR": 1, "LOG_LEVEL_INFO": 2, "LOG_LEVEL_DEBUG": 3, "LOG_LEVEL_DEBUG_PLUS": 4}
OUVRANTS = {"if", "while", "for", "def", "class", "try", "do"}
# Le texte est lu tel qu'ecrit dans le source : une tabulation y est l'echappement \t (2 caracteres)
PREFIXE = re.compile(r"[A-Z][A-Z0-9_]*:(?:\s|\\[tn])")
# demarrage.be est compile (banc) avant que les LOG_LEVEL_* existent : ses niveaux en chiffre sont voulus
NIVEAU_CHIFFRE_ADMIS = {"demarrage.be"}
# La fonction de log commune est le seul log() direct legitime
LOG_DIRECT_ADMIS = {"logFonctions_log"}

LEXEME = re.compile(r"""
    (?P<blanc>[ \t\r]+)
  | (?P<nl>\n)
  | (?P<bloc>\#-.*?-\#)
  | (?P<comm>\#[^\n]*)
  | (?P<chaine>f?"(?:\\.|[^"\\\n])*"|f?'(?:\\.|[^'\\\n])*')
  | (?P<nombre>0x[0-9A-Fa-f]+|\d+(?:\.\d+)?)
  | (?P<ident>[A-Za-z_]\w*)
  | (?P<op>\S)
""", re.S | re.X)


def lexemes(source):
    """[(type, texte, ligne)] sans blancs ni commentaires ; le contenu des chaines est garde."""
    sortie, ligne = [], 1
    for m in LEXEME.finditer(source):
        genre, texte = m.lastgroup, m.group()
        if genre in ("ident", "nombre", "op", "chaine"):
            sortie.append((genre, texte, ligne))
        ligne += texte.count("\n")
    return sortie


def fin_parenthese(lex, i):
    """Indice de la ')' qui ferme la '(' en lex[i]."""
    prof = 0
    for j in range(i, len(lex)):
        if lex[j][1] in "([{":
            prof += 1
        elif lex[j][1] in ")]}":
            prof -= 1
            if prof == 0:
                return j
    return len(lex) - 1


def arguments(lex, i, j):
    """Arguments de premier niveau entre lex[i] = '(' et lex[j] = ')'."""
    args, courant, prof = [], [], 0
    for k in range(i + 1, j):
        t = lex[k][1]
        if t in "([{":
            prof += 1
        elif t in ")]}":
            prof -= 1
        if t == "," and prof == 0:
            args.append(courant)
            courant = []
        else:
            courant.append(lex[k])
    if courant:
        args.append(courant)
    return args


def texte_litteral(arg):
    """Chaine en tete du message (directe, ou dans string.format(...)/string.replace(...)), sinon None."""
    for genre, texte, _ in arg:
        if genre == "chaine":
            return texte[2:-1] if texte.startswith("f") else texte[1:-1]
        if texte not in ("string", "format", "replace", ".", "("):
            return None
    return None


def garde(lex, debut, fin, gardes):
    """Vrai si les lexemes [debut, fin) appellent actif() ou nomment une variable de garde."""
    return any(lex[k][1] == "actif" or lex[k][0] == "ident" and lex[k][1] in gardes for k in range(debut, fin))


def variables_de_garde(lex):
    """Noms affectes depuis actif() : var detail = logFonctions.actif(...)."""
    noms = set()
    for i, (genre, texte, ligne) in enumerate(lex):
        if texte == "=" and i > 0 and lex[i - 1][0] == "ident":
            k = i + 1
            while k < len(lex) and lex[k][2] == ligne and lex[k][1] != "actif":
                k += 1
            if k < len(lex) and lex[k][1] == "actif":
                noms.add(lex[i - 1][1])
    return noms


def condition(lex, i):
    """Bornes [i+1, fin) de la condition d'un if/elif/while en lex[i] : parenthese ou reste de la ligne."""
    if i + 1 < len(lex) and lex[i + 1][1] == "(":
        return i + 1, fin_parenthese(lex, i + 1) + 1
    k = i + 1
    while k < len(lex) and lex[k][2] == lex[i][2]:
        k += 1
    return i + 1, k


def controle(chemin, source):
    """Liste de (ligne, regle, message) pour un source Berry."""
    nom = Path(chemin).name
    lex = lexemes(source)
    gardes = variables_de_garde(lex)
    # Pile des blocs : [genre, nom_def, garde_courante, dans_except, condition_nomme_logFonctions]
    pile, avis = [], []

    def avertit(ligne, regle, message):
        avis.append((ligne, regle, message))

    i = 0
    while i < len(lex):
        genre, texte, ligne = lex[i]
        precedent = lex[i - 1][1] if i > 0 else ""
        if genre == "ident" and precedent != ".":
            if texte in OUVRANTS:
                nom_def = None
                if texte == "def" and i + 1 < len(lex) and lex[i + 1][0] == "ident":
                    nom_def = lex[i + 1][1]
                g, repli = False, False
                if texte in ("if", "while"):
                    a, b = condition(lex, i)
                    g = garde(lex, a, b, gardes)
                    repli = any(lex[k][1].strip("'\"") == "logFonctions" for k in range(a, b))
                pile.append([texte, nom_def, g, False, repli])
            elif texte == "end" and pile:
                pile.pop()
            elif texte == "elif" and pile and pile[-1][0] == "if":
                a, b = condition(lex, i)
                pile[-1][2] = garde(lex, a, b, gardes)
            elif texte == "else" and pile and pile[-1][0] == "if":
                pile[-1][2] = False
            elif texte == "except" and pile and pile[-1][0] == "try":
                pile[-1][3] = True

        appel = i + 1 < len(lex) and lex[i + 1][1] == "("
        if genre == "ident" and appel and precedent != "def":
            noms_def = {b[1] for b in pile if b[0] == "def"}
            en_except = any(b[0] == "try" and b[3] for b in pile)
            repli = any(b[0] == "if" and b[4] for b in pile)
            if texte == "log" and precedent != "." and not (noms_def & LOG_DIRECT_ADMIS) and not repli:
                avertit(ligne, "log-direct", "log() direct : passer par logFonctions.log(msg, niveau, cible)")
            elif texte == "log" and precedent == "." and i >= 2 and lex[i - 2][1] == "tasmota":
                avertit(ligne, "log-direct", "tasmota.log() direct : passer par logFonctions.log(msg, niveau, cible)")
            elif texte == "print" and precedent != "." and en_except:
                avertit(ligne, "log-direct", "print() dans un except : n'atteint ni le syslog ni MQTT, "
                                             "utiliser logFonctions.log(\"..._ERREUR: ...\", LOG_LEVEL_ERREUR)")
            elif texte == "log" and precedent == "." and i >= 2 and lex[i - 2][1].endswith("Fonctions"):
                j = fin_parenthese(lex, i + 1)
                args = arguments(lex, i + 1, j)
                verifie_appel(lex, i, j, args, nom, pile, gardes, en_except, avertit)
                i = j
        i += 1
    return avis


def verifie_appel(lex, i, j, args, nom, pile, gardes, en_except, avertit):
    """Regles d'un appel xxxFonctions.log(message, niveau [, cible])."""
    ligne = lex[i][2]
    if not args:
        return
    niveau = None
    if len(args) < 2:
        avertit(ligne, "niveau", "niveau absent : le preciser (LOG_LEVEL_ERREUR/INFO/DEBUG/DEBUG_PLUS)")
        niveau = 2
    elif len(args[1]) == 1 and args[1][0][1] in NIVEAUX:
        niveau = NIVEAUX[args[1][0][1]]
    elif len(args[1]) == 1 and args[1][0][0] == "nombre":
        niveau = int(args[1][0][1], 0) if not args[1][0][1].startswith("0x") else int(args[1][0][1], 16)
        if nom not in NIVEAU_CHIFFRE_ADMIS:
            avertit(ligne, "niveau", f"niveau ecrit en chiffre ({args[1][0][1]}) : utiliser la constante LOG_LEVEL_*")

    texte = texte_litteral(args[0])
    if texte is not None:
        m = PREFIXE.match(texte)
        if not m:
            avertit(ligne, "prefixe", f"prefixe absent ou hors NOM_MAJ_SNAKE: (\"{texte[:40]}\")")
        elif en_except and niveau == 1 and "_ERREUR" not in m.group():
            avertit(ligne, "erreur-prefixe", f"erreur dans un except sans _ERREUR dans le prefixe ({m.group().strip()})")

    noms_def = {b[1] for b in pile if b[0] == "def"}
    if niveau == 2 and noms_def & FREQUENTS:
        avertit(ligne, "info-frequent", f"info dans un callback frequent ({', '.join(sorted(noms_def & FREQUENTS))}) : "
                                        "passer en debug ou detail")
    if niveau in (3, 4):
        cout = any(lex[k][1] == "tohex" or lex[k][1] == "dump" and lex[k - 1][1] == "." and lex[k - 2][1] == "json"
                   for k in range(i, j))
        if cout and not any(b[2] for b in pile if b[0] in ("if", "while")) and not garde(lex, i + 2, j, gardes):
            avertit(ligne, "non-garde", "json.dump/tohex construit meme si le message est jete : "
                                        "garder par if logFonctions.actif(niveau, cible) ... end")


def controle_fichiers(racine, fichiers):
    """Lignes 'fichier:ligne: avertissement: [regle] message', triees par fichier puis ligne."""
    lignes = []
    for f in fichiers:
        try:
            source = Path(f).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(Path(f).relative_to(racine) if Path(f).is_relative_to(racine) else f).replace("\\", "/")
        for ligne, regle, message in sorted(controle(f, source)):
            lignes.append(f"{rel}:{ligne}: avertissement: [{regle}] {message}")
    return lignes


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    racine = Path.cwd()
    for l in controle_fichiers(racine, [Path(a) for a in sys.argv[1:]]):
        print(l)
    sys.exit(0)
