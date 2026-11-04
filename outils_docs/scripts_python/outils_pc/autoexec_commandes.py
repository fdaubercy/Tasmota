#!/usr/bin/env python3
"""Commandes Tasmota connues, et celles qui redemarrent la carte (plan autoexec-bat, A1).

Une ligne d'autoexec.bat s'execute a chaque demarrage : une commande qui redemarre la carte a chaque passage cree une
boucle (cas vecu : `Hostname`, support_command.ino::CmndHostname). L'onglet autoexec.bat de l'Assistant persist lit
ici, par `charge`, le fichier fige outils_docs/schemas/commandes_tasmota.json :
  connues      {NOM: source}  noms des tables `DecodeCommand(kXxxCommands, XxxCommand[, synonymes])` du code du fork
               (macros D_CMND_/D_PRFX_ resolues, #ifdef compris : connue n'importe ou dans le fork), SetOption0..N
               (support_command.ino::SetoptionDecode), et `tasmota.add_cmd` des .be de data/fs
  redemarrent  {NOM: {"quand": "toujours"|"si-change", "source": ...}}  `TasmotaGlobal.restart_flag = 2` dans la
               fonction de la commande (meme rang dans le tableau de pointeurs que dans la chaine des noms)
  doc          {NOM: extrait}  mentions restart/reboot de Commands.md (depot tasmota/docs), croisees avec le code
Classement : « si-change » seulement si une condition qui entoure le redemarrage compare au reglage en place (!=,
strcmp...) ; une condition sur l'argument seul (data_len > 0, payload valide, case d'une SetOption) laisse « toujours »,
car la meme ligne revient, avec le meme argument, a chaque demarrage.
Noms normalises par build_sauvegarde::commande (SO56 -> SETOPTION56, Timer3 -> TIMER) ; un nom qu'elle ne lit pas
(I2CScan : chiffre au milieu) est garde en majuscules.

  --generer [--doc]  reecrit le fige (--doc : telecharge Commands.md une fois ; sinon reprend la doc du fige)
  --verifier         ecarts entre le fige et le code du fork, sans reseau ; code 1 s'il y en a
Banc : test_autoexec_commandes.py.
"""

import argparse
import datetime
import json
import re
import sys
import urllib.request
from pathlib import Path

from build_sauvegarde import commande

FIGE = Path("outils_docs/schemas/commandes_tasmota.json")
URL_DOC = "https://raw.githubusercontent.com/tasmota/docs/master/docs/Commands.md"
CHAINE = r'"(?:\\.|[^"\\\n])*"'
LEXEMES = re.compile(CHAINE + r"|'(?:\\.|[^'\\\n])*'|//[^\n]*|/\*.*?\*/", re.S)
# comparaison au reglage en place : seul cas ou la ligne ne redemarre qu'au premier passage
COMPARE = re.compile(r"\b(?:strn?(?:case)?cmp(?:_P)?|memcmp)\s*\(|(?:Settings|TasmotaGlobal)\S*\s*!=|!=\s*\S*(?:Settings|TasmotaGlobal)")
CONDITION = re.compile(r"\b(?:if|else|switch|case|for|while)\b|\?")


def _nom(brut):
    return commande(brut) or brut.upper()


def _premiere_branche(code):
    """Code sans les branches #else/#elif : les deux tableaux d'une table de commandes y restent alignes meme quand
    leurs #ifdef ne se repondent pas ligne a ligne (xdrv_39_thermostat.ino)."""
    lignes, pile = [], []
    for ligne in code.split("\n"):
        d = re.match(r"[ \t]*#[ \t]*(\w+)", ligne)
        mot = d.group(1) if d else ""
        if mot in ("if", "ifdef", "ifndef"):
            pile.append(True)
        elif mot in ("elif", "else") and pile:
            pile[-1] = False
        elif mot == "endif" and pile:
            pile.pop()
        lignes.append("" if d or not all(pile) else ligne)
    return "\n".join(lignes)


def _lit(fichier):
    """(code, code1, blanc, defines) : commentaires et directives retires ; `code1` = premiere branche des #if ;
    `blanc` = code aux chaines videes (accolades)."""
    texte = fichier.read_text(encoding="utf-8", errors="replace").replace("\\\r\n", " ").replace("\\\n", " ")
    code = LEXEMES.sub(lambda m: m.group(0) if m.group(0)[0] in "\"'" else " ", texte)
    jeton = "(?:" + CHAINE + r"|\w+\b)"   # \b : un mot ne se coupe pas (retour arriere exponentiel sinon)
    defines = {}
    for k, v in re.findall(r"(?m)^[ \t]*#[ \t]*define[ \t]+(\w+)[ \t]+(" + jeton + r"(?:[ \t]*" + jeton + r")*)[ \t]*$", code):
        defines.setdefault(k, v)
    code1 = _premiere_branche(code)
    code = re.sub(r"(?m)^[ \t]*#.*$", "", code)
    blanc = re.sub(CHAINE + r"|'(?:\\.|[^'\\\n])*'", lambda m: m.group(0)[0] + " " * (len(m.group(0)) - 2) + m.group(0)[0], code)
    return code, code1, blanc, defines


def _chaine(expr, locales, globales, pile=()):
    """Valeur d'une concatenation C de litteraux et de macros ; KeyError si une macro est inconnue."""
    res = ""
    for lit, ident in re.findall(r'(' + CHAINE + r')|(\w+)', expr):
        if lit:
            res += lit[1:-1].replace('\\"', '"')
        elif ident not in pile:
            res += _chaine(locales.get(ident) if ident in locales else globales[ident], locales, globales, pile + (ident,))
    return res


def _corps(blanc, debut):
    """Corps d'une fonction dont l'accolade ouvrante est a `debut` : accolades appariees, borne a la premiere `}` en
    colonne 0 (les deux branches d'un #ifdef, directives retirees, ouvrent chacune leur accolade)."""
    niveau, fin = 0, blanc.find("\n}", debut)
    blanc = blanc if fin < 0 else blanc[:fin + 2]
    for i in range(debut, len(blanc)):
        niveau += {"{": 1, "}": -1}.get(blanc[i], 0)
        if not niveau:
            return blanc[debut:i + 1]
    return blanc[debut:]


def _conditions(corps, pos):
    """Entetes des blocs qui entourent `pos` (if, else, switch...) et debut de l'instruction (if sans accolade, case)."""
    pile, debut = [], 0
    for m in re.finditer(r"[{};]", corps[:pos]):
        if m.group() == "{":
            pile.append(corps[debut:m.start()])
        elif m.group() == "}" and pile:
            pile.pop()
        debut = m.end()
    return [t for t in pile[1:] + [corps[debut:pos]] if CONDITION.search(t)]


def classe(corps):
    """None, "toujours" ou "si-change" selon les `restart_flag = 2` du corps de la fonction."""
    quand = None
    for m in re.finditer(r"restart_flag\s*=\s*2\s*;", corps):
        conds = _conditions(corps, m.start())
        if not any(COMPARE.search(c) for c in conds):
            return "toujours"
        quand = "si-change"
    return quand


def _setoptions(blanc, fonctions):
    """({SETOPTIONn: "toujours"|"si-change"}, nombre) depuis SetoptionDecode et les case de CmndSetoptionBase."""
    if "SetoptionDecode" not in fonctions or "CmndSetoptionBase" not in fonctions:
        return {}, 0
    decode = fonctions["SetoptionDecode"]
    nombre = int(re.search(r"index\s*<\s*(\d+)", decode).group(1))
    bases = {int(t): int(b or 0) for t, b in re.findall(r"\*ptype\s*=\s*(\d+)\s*;\s*\*pindex\s*=\s*index\s*(?:-\s*(\d+))?", decode)}
    enum = re.search(r"enum\s+SO32_49Index\s*\{([^}]*)\}", blanc)
    params = {n: i for i, n in enumerate(x.strip() for x in enum.group(1).split(","))} if enum else {}
    corps, res = fonctions["CmndSetoptionBase"], {}
    blocs = list(re.finditer(r"(\d+)\s*==\s*ptype", corps))
    for i, b in enumerate(blocs):
        bloc = corps[b.end():blocs[i + 1].start() if i + 1 < len(blocs) else len(corps)]
        base, cas, compare = bases.get(int(b.group(1)), 0), [], None
        for m in re.finditer(r"case\s+(\w+)\s*:|break\s*;|(\w+)\s*==\s*pindex|pindex\s*==\s*(\w+)|restart_flag\s*=\s*2\s*;", bloc):
            if m.group(1):
                cas.append(m.group(1))
            elif m.group(0).startswith("break"):
                cas = []
            elif m.group(2) or m.group(3):
                compare = m.group(2) or m.group(3)
            else:
                quand = classe("{" + bloc[:m.end()].rsplit("case", 1)[-1] + "}") if cas else "toujours"
                for c in cas or [compare]:
                    n = int(c) if c and c.isdigit() else params.get(c)
                    if n is not None:
                        res[f"SETOPTION{base + n}"] = quand
    return res, nombre


def _berry(racine, connues):
    for be in sorted((racine / "data" / "fs").glob("*.be")):
        for nom in re.findall(r"""tasmota\.add_cmd\(\s*['"](\w+)['"]""", be.read_text(encoding="utf-8", errors="replace")):
            connues.setdefault(_nom(nom), be.relative_to(racine).as_posix())


def extrait_doc(texte):
    """{NOM: extrait} des commandes de Commands.md dont la description parle de restart ou de reboot."""
    res = {}
    for nom, desc in re.findall(r'(?m)^([A-Za-z][^|<]*(?:<[^a][^>]*>)?[^|<]*)<a class="cmnd" id="[^"]*"></a>\|(.*)$', texte):
        m = re.search(r"restart|reboot", desc, re.I)
        cle = _nom(re.sub(r"<[^>]*>|\W", "", nom))
        if m and cle not in res:
            res[cle] = re.sub(r"<[^>]*>", " ", desc[max(0, m.start() - 80):m.end() + 40]).strip()
    return res


def genere(racine, doc=None):
    """Connues et redemarrent tires du code de `racine` ; `doc` = texte de Commands.md ou {NOM: extrait} deja tire."""
    racine = Path(racine)
    fichiers = [f for ext in ("*.ino", "*.h", "*.cpp") for f in sorted((racine / "tasmota").rglob(ext))
                if not f.name.endswith(".ino.cpp") and ("language" not in f.parts or f.name == "en_GB.h")]
    lus = {f: _lit(f) for f in fichiers}
    globales = {}
    for f in sorted(lus, key=lambda f: f.name != "i18n.h"):
        for k, v in lus[f][3].items():
            globales.setdefault(k, v)
    tables, tables1, pointeurs, synonymes, fonctions = {}, {}, {}, {}, {}
    for f, (code, code1, blanc, _) in lus.items():
        for dico, texte in ((tables, code), (tables1, code1)):
            for m in re.finditer(r"char\s+(\w+)\s*\[\s*\]\s*(?:PROGMEM\s*)?=\s*([^;{]*);", texte):
                dico.setdefault((f, m.group(1)), m.group(2))
        for m in re.finditer(r"\(\s*\*\s*(?:const\s+)?(\w+)\s*\[\s*\]\s*\)\s*\(\s*void\s*\)\s*(?:PROGMEM\s*)?=\s*\{([^}]*)\}", code1):
            pointeurs.setdefault((f, m.group(1)), [p.strip().lstrip("&").split("::")[-1] for p in m.group(2).split(",") if p.strip()])
        for m in re.finditer(r"SO_SYNONYMS\(\s*(\w+)\s*,([^)]*)\)", code):
            synonymes[m.group(1)] = [int(x) for x in re.findall(r"\d+", m.group(2))]
        for m in re.finditer(r"\bvoid\s+(?:\w+::)?(\w+)\s*\(\s*(?:void)?\s*\)\s*\{", blanc):
            fonctions.setdefault(m.group(1), []).append((f, _corps(blanc, m.end() - 1)))
        for m in re.finditer(r"\b(?:bool|void)\s+(SetoptionDecode|CmndSetoptionBase)\s*\([^)]*\)\s*\{", blanc):
            fonctions.setdefault(m.group(1), []).append((f, _corps(blanc, m.end() - 1)))

    def trouve(dico, f, nom):
        return dico.get((f, nom)) or next((v for (g, n), v in sorted(dico.items(), key=lambda x: str(x[0][0])) if n == nom), None)

    rel = lambda f: f.relative_to(racine).as_posix()
    connues, redemarrent, anomalies = {}, {}, []
    so, nombre = _setoptions("\n".join(b for c, c1, b, d in lus.values() if "SO32_49Index" in b),
                             {n: v[0][1] for n, v in fonctions.items()})
    for n in range(nombre):
        connues[f"SETOPTION{n}"] = "tasmota/tasmota_support/support_command.ino::SetoptionDecode"
    for nom, quand in so.items():
        redemarrent[nom] = {"quand": quand, "source": "tasmota/tasmota_support/support_command.ino::CmndSetoptionBase"}

    def noms(expr, defines):
        """(prefixe, noms) ; la derniere case vide d'une chaine finie par « | » n'est pas une commande."""
        prefixe, *res = _chaine(expr, defines, globales).split("|")
        return prefixe, res[:-1] if res and not res[-1] else res

    for f, (code, code1, blanc, defines) in lus.items():
        for t, p, s in re.findall(r"DecodeCommand\(\s*(?:\w+::)?(\w+)\s*,\s*(?:\w+::)?(\w+)\s*(?:,\s*(\w+)\s*)?\)", code):
            ptrs = trouve(pointeurs, f, p)
            try:
                prefixe, rangs = noms(trouve(tables1, f, t), defines)
                tous = noms(trouve(tables, f, t), defines)[1]
            except (KeyError, TypeError) as e:
                anomalies.append(f"{rel(f)}::{t} illisible ({e})")
                continue
            for brut in tous:                         # toutes les branches des #ifdef : connue n'importe ou
                if prefixe + brut:
                    connues.setdefault(_nom(prefixe + brut), f"{rel(f)}::{t}")
            syn = synonymes.get(s, [])
            if ptrs is None or len(rangs) - len(syn) != len(ptrs):
                anomalies.append(f"{rel(f)}::{t} : {len(rangs) - len(syn)} noms pour {len(ptrs or [])} fonctions")
                ptrs = []
            for i, brut in enumerate(rangs):
                if not prefixe + brut:
                    continue
                cle = _nom(prefixe + brut)
                if i < len(syn):
                    if f"SETOPTION{syn[i]}" in redemarrent:
                        redemarrent.setdefault(cle, redemarrent[f"SETOPTION{syn[i]}"])
                    continue
                fn = ptrs[i - len(syn)] if ptrs else None
                defs = sorted(fonctions.get(fn, []), key=lambda d: d[0] != f)
                quands = [q for q in (classe(c) for _, c in defs) if q]
                if quands and cle not in redemarrent:
                    redemarrent[cle] = {"quand": "toujours" if "toujours" in quands else "si-change",
                                        "source": f"{rel(defs[0][0])}::{fn}"}
    _berry(racine, connues)
    doc = extrait_doc(doc) if isinstance(doc, str) else dict(doc or {})
    for nom in doc:
        if nom in redemarrent:
            redemarrent[nom] = dict(redemarrent[nom], source=redemarrent[nom]["source"] + " ; doc Commands.md")
    return {"connues": dict(sorted(connues.items())), "redemarrent": dict(sorted(redemarrent.items())),
            "doc": dict(sorted(doc.items())), "anomalies": anomalies}


def charge(racine):
    """Le fige : {"connues": {...}, "redemarrent": {...}, "doc": {...}, ...}."""
    return json.loads((Path(racine) / FIGE).read_text(encoding="utf-8"))


def verifie(racine, fige=None):
    """Ecarts (un texte par nom) entre le fige et ce que donne le code de `racine`, la doc reprise du fige."""
    fige = json.loads(Path(fige or Path(racine) / FIGE).read_text(encoding="utf-8"))
    code = genere(racine, doc=fige.get("doc", {}))
    ecarts = []
    for cle in ("connues", "redemarrent"):
        a, b = fige.get(cle, {}), code[cle]
        for nom in sorted(set(a) | set(b)):
            if a.get(nom) != b.get(nom):
                ecarts.append(f"{cle} {nom} : fige {a.get(nom)!r}, code {b.get(nom)!r}")
    return ecarts


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--generer", action="store_true")
    p.add_argument("--doc", action="store_true", help="telecharger Commands.md (lecture d'une page publique)")
    p.add_argument("--verifier", action="store_true")
    a = p.parse_args()
    racine = Path(__file__).resolve().parents[3]
    if a.generer:
        ancien = charge(racine) if (racine / FIGE).exists() else {}
        source = ancien.get("doc_source")
        doc = ancien.get("doc", {})
        if a.doc:
            with urllib.request.urlopen(URL_DOC, timeout=60) as r:
                doc = r.read().decode("utf-8")
            source = {"url": URL_DOC, "date": datetime.date.today().isoformat()}
        res = dict(genere(racine, doc=doc), doc_source=source)
        (racine / FIGE).write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"{FIGE} : {len(res['connues'])} connues, {len(res['redemarrent'])} redemarrent, "
              f"{len(res['doc'])} mentions de la doc, {len(res['anomalies'])} anomalie(s)")
    if a.verifier:
        ecarts = verifie(racine)
        print("\n".join(ecarts) or "fige conforme au code")
        return 1 if ecarts else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
