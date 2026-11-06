#!/usr/bin/env python3
"""Commandes Tasmota connues, et celles qui redemarrent la carte (plan autoexec-bat, A1).

Une ligne d'autoexec.bat s'execute a chaque demarrage : une commande qui redemarre la carte a chaque passage cree une
boucle (cas vecu : `Hostname`, support_command.ino::CmndHostname). L'onglet autoexec.bat de l'Assistant persist lit
ici, par `charge`, le fichier fige outils_docs/schemas/commandes_tasmota.json :
  connues      {NOM: source}  noms des tables `DecodeCommand(kXxxCommands, XxxCommand[, synonymes])` du code du fork
               (macros D_CMND_/D_PRFX_ resolues, #ifdef compris : connue n'importe ou dans le fork), SetOption0..N
               (support_command.ino::SetoptionDecode), et `tasmota.add_cmd` des .be de data/fs
  redemarrent  {NOM: {"quand": "toujours"|"si-change", "source": ...}}  affectation non nulle de `restart_flag`
               (2, 211, 210 + payload...) dans la fonction de la commande (meme rang dans le tableau de pointeurs que
               dans la chaine des noms) ; RELUES (relues a la main) ; puis la doc : une commande connue que la doc dit
               redemarrer (AFFIRME) sans que le code le montre entre en « toujours », « doc Commands.md seulement »
  gardes       {NOM: [chemin, ...]}  conditions du preprocesseur sous lesquelles la commande est compilee (plan autoexec-mqtt-tapp,
               A3) ; chemin = [condition, ...] autour de la table et de sa ligne, telle que lecture_gardes.evalue la lit :
               #ifdef X -> defined(X), #ifndef X -> !defined(X), #else -> !(E), #elif F -> !(E) puis F. Un chemin par presence
               du nom (tables, fichiers, branches). Pas de cle = aucune garde connue, donc aucune alerte possible : commande
               toujours compilee, Berry, SetOption. Dans le doute, moins de garde (voir _chemins_table) ; condition sur une
               macro posee hors des en-tetes que lit le preprocesseur de l'env : retiree (voir genere)
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
from functools import lru_cache
from pathlib import Path

from build_sauvegarde import commande

FIGE = Path("outils_docs/schemas/commandes_tasmota.json")
URL_DOC = "https://raw.githubusercontent.com/tasmota/docs/master/docs/Commands.md"
TABLE = r"char\s+(\w+)\s*\[\s*\]\s*(?:PROGMEM\s*)?=\s*([^;{]*);"
CHAINE = r'"(?:\\.|[^"\\\n])*"'
LEXEMES = re.compile(CHAINE + r"|'(?:\\.|[^'\\\n])*'|//[^\n]*|/\*.*?\*/", re.S)
# comparaison au reglage en place : seul cas ou la ligne ne redemarre qu'au premier passage
COMPARE = re.compile(r"\b(?:strn?(?:case)?cmp(?:_P)?|memcmp)\s*\(|(?:Settings|TasmotaGlobal)\S*\s*!=|!=\s*\S*(?:Settings|TasmotaGlobal)")
CONDITION = re.compile(r"\b(?:if|else|switch|case|for|while)\b|\?")
# restart_flag non nul : 1..5 = redemarrage differe, 2 = Restart 1, 21x = Reset (support_tasmota.ino::Every250mSeconds)
REDEMARRE = r"restart_flag\s*=\s*[1-9][^;]*;"
# la doc dit que la commande redemarre la carte (et non « apres un redemarrage », « faire suivre de Restart 1 »)
AFFIRME = re.compile(r"\band (?:restart|reboot)\b|forces? (?:a )?(?:restart|reboot)|causes? a (?:restart|reboot)"
                     r"|\b(?:restart|reboot)s? (?:the )?(?:device|tasmota)\b", re.I)
# redemarrages par une autre voie que restart_flag, relus dans le code (pris seulement si la commande est connue)
RELUES = {
    "UPGRADE": ("toujours", "tasmota/tasmota_support/support_command.ino::CmndUpgrade (ota_state_flag = 3 : OTA puis "
                "redemarrage ; relu a la main)"),
    "UPLOAD": ("toujours", "tasmota/tasmota_support/support_command.ino::CmndUpgrade (meme fonction qu'Upgrade ; relu a la "
               "main)"),
    "WIFITEST": ("si-change", "tasmota/tasmota_support/support_command.ino::CmndWifiTest (sans effet hors du gestionnaire "
                 "Wi-Fi ; redemarre une fois apres un test reussi, par support_wifi.ino ; relu a la main)"),
}
EXCLUES = {"BRRESTART"}   # relance la machine Berry, pas la carte


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
    """(code, code1, blanc, defines, brut) : commentaires et directives retires ; `code1` = premiere branche des #if ;
    `blanc` = code aux chaines videes (accolades) ; `brut` = directives gardees, memes lignes que `code`."""
    texte = fichier.read_text(encoding="utf-8", errors="replace").replace("\\\r\n", " ").replace("\\\n", " ")
    code = LEXEMES.sub(lambda m: m.group(0) if m.group(0)[0] in "\"'" else " ", texte)
    jeton = "(?:" + CHAINE + r"|\w+\b)"   # \b : un mot ne se coupe pas (retour arriere exponentiel sinon)
    defines = {}
    for k, v in re.findall(r"(?m)^[ \t]*#[ \t]*define[ \t]+(\w+)[ \t]+(" + jeton + r"(?:[ \t]*" + jeton + r")*)[ \t]*$", code):
        defines.setdefault(k, v)
    code1, brut = _premiere_branche(code), code
    code = re.sub(r"(?m)^[ \t]*#.*$", "", code)
    blanc = re.sub(CHAINE + r"|'(?:\\.|[^'\\\n])*'", lambda m: m.group(0)[0] + " " * (len(m.group(0)) - 2) + m.group(0)[0], code)
    return code, code1, blanc, defines, brut


def _chaine(expr, locales, globales, pile=()):
    """Valeur d'une concatenation C de litteraux et de macros ; KeyError si une macro est inconnue."""
    res = ""
    for lit, ident in re.findall(r'(' + CHAINE + r')|(\w+)', expr):
        if lit:
            res += lit[1:-1].replace('\\"', '"')
        elif ident not in pile:
            res += _chaine(locales.get(ident) if ident in locales else globales[ident], locales, globales, pile + (ident,))
    return res


@lru_cache(maxsize=None)
def _piles(brut):
    """Conditions autour de chaque ligne de `brut`, du dehors vers le dedans (voir l'en-tete pour leur ecriture). `#ifndef X`
    suivi de `#define X` (garde d'inclusion) n'est pas une condition. #if desequilibres (#if dans une chaine brute) : aucune
    condition sur tout le fichier, une pile fausse donnerait une fausse garde."""
    pile, res, equilibre, attente = [], [], True, None      # pile : [[negations des branches passees, condition en cours], ...]
    for ligne in brut.split("\n"):
        d = re.match(r"[ \t]*#[ \t]*(\w+)(.*)", ligne)
        mot, reste = (d.group(1), " ".join(d.group(2).split())) if d else ("", "")
        if mot in ("elif", "else", "endif") and not pile:
            equilibre = False
        elif mot in ("if", "ifdef", "ifndef"):
            pile.append([[], {"if": reste, "ifdef": f"defined({reste})", "ifndef": f"!defined({reste})"}[mot]])
        elif mot == "endif":
            pile.pop()
        elif mot in ("elif", "else"):
            prec, cour = pile[-1]
            if cour:
                prec.append(f"!({cour})")
            pile[-1][1] = reste if mot == "elif" else None
        elif mot == "define" and attente and reste.split()[:1] == [attente]:
            pile[-1][1] = None
        if d:
            attente = reste if mot == "ifndef" else None
        res.append(tuple(c for prec, cour in pile for c in prec + ([cour] if cour else [])))
    return res if equilibre and not pile else [()] * len(res)


def _chemins_table(nommes, emplacements, lit):
    """{NOM: {chemin}} d'une table, `emplacements` = [(match de TABLE dans code, code, piles)], `nommes` = ses noms en lecture
    globale, `lit` = valeur d'une ligne. Le prefixe (1er champ) s'applique a chaque nom. Dans le doute, moins de garde, jamais une
    garde inventee : nom a cheval sur deux piles, prefixe seul, nom qu'aucune ligne n'apporte ou emplacement illisible -> garde
    de la table seule."""
    res, tables = {n: set() for n in nommes}, set()
    for m, code, piles in emplacements:
        table = piles[code.count("\n", 0, m.start())]
        tables.add(table)
        champs = [[]]                                       # [[(morceau, pile de sa ligne), ...], ...] : un par case de la chaine
        try:
            for i, ligne in enumerate(m.group(2).split("\n"), code.count("\n", 0, m.start(2))):
                for j, bout in enumerate(lit(ligne).split("|")):
                    if j:
                        champs.append([])
                    if bout:
                        champs[-1].append((bout, piles[i]))
        except (KeyError, TypeError):
            for n in nommes:
                res[n].add(table)
            continue
        prefixe, champs = "".join(b for b, _ in champs[0]), champs[1:]
        if champs and not champs[-1]:                       # comme `noms` : la case vide finale n'est pas une commande
            champs.pop()
        for champ in champs:
            brut = prefixe + "".join(b for b, _ in champ)
            if brut:
                piles_nom = {p for _, p in champ}
                chemin = piles_nom.pop() if len(piles_nom) == 1 else table
                nom = _nom(brut)
                res.setdefault(nom, set()).add(chemin)
    for chemins in res.values():
        if not chemins:
            chemins.update(tables)
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
    """None, "toujours" ou "si-change" selon les affectations non nulles de `restart_flag` du corps de la fonction."""
    quand = None
    for m in re.finditer(REDEMARRE, corps):
        conds = _conditions(corps, m.start())
        if not any(COMPARE.search(c) for c in conds):
            return "toujours"
        quand = "si-change"
    return quand


def _setoptions(blanc, fonctions):
    """({SETOPTIONn: (quand, condition)}, nombre) depuis SetoptionDecode et les case de CmndSetoptionBase ;
    `condition` = le `if` qui garde le redemarrage dans son case (SO55 : seulement si la valeur est 0), ou ""."""
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
        for m in re.finditer(r"case\s+(\w+)\s*:|break\s*;|(\w+)\s*==\s*pindex|pindex\s*==\s*(\w+)|" + REDEMARRE, bloc):
            if m.group(1):
                cas.append(m.group(1))
            elif m.group(0).startswith("break"):
                cas = []
            elif m.group(2) or m.group(3):
                compare = m.group(2) or m.group(3)
            else:
                segment = bloc[:m.end()].rsplit("case", 1)[-1] if cas else ""
                quand = classe("{" + segment + "}") if cas else "toujours"
                si = re.search(r"\bif\s*\((.*)\)", segment)
                si = " ".join(si.group(1).split()) if si else ""
                valeur = re.fullmatch(r"\(?(\d+)\s*==\s*XdrvMailbox\.payload\)?", si)
                si = f"la valeur est {valeur.group(1)}" if valeur else si
                for c in cas or [compare]:
                    n = int(c) if c and c.isdigit() else params.get(c)
                    if n is not None:
                        res[f"SETOPTION{base + n}"] = (quand, si)
    return res, nombre


def _berry(racine, connues):
    """Ajoute les `add_cmd` des .be a `connues` ; rend leurs noms (un homonyme C y garde sa source C)."""
    noms = set()
    for be in sorted((racine / "data" / "fs").glob("*.be")):
        for nom in re.findall(r"""tasmota\.add_cmd\(\s*['"](\w+)['"]""", be.read_text(encoding="utf-8", errors="replace")):
            noms.add(_nom(nom))
            connues.setdefault(_nom(nom), be.relative_to(racine).as_posix())
    return noms


def extrait_doc(texte):
    """{NOM: extrait} des commandes de Commands.md dont la description parle de restart ou de reboot."""
    res = {}
    for nom, desc in re.findall(r'(?m)^([A-Za-z][^|<]*(?:<[^a][^>]*>)?[^|<]*)<a class="cmnd" id="[^"]*"></a>\|(.*)$', texte):
        m = AFFIRME.search(desc) or re.search(r"restart|reboot", desc, re.I)   # extrait autour de l'affirmation
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
    tables, tables1, pointeurs, synonymes, fonctions, lieux = {}, {}, {}, {}, {}, {}
    for f, (code, code1, blanc, _, _) in lus.items():
        for dico, texte in ((tables, code), (tables1, code1)):
            for m in re.finditer(TABLE, texte):
                dico.setdefault((f, m.group(1)), m.group(2))
        for m in re.finditer(TABLE, code):                    # tous les emplacements d'un nom : branches #if/#else
            lieux.setdefault(m.group(1), {}).setdefault(f, []).append(m)
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
    chemins = {}
    so, nombre = _setoptions("\n".join(v[2] for v in lus.values() if "SO32_49Index" in v[2]),
                             {n: v[0][1] for n, v in fonctions.items()})
    for n in range(nombre):
        connues[f"SETOPTION{n}"] = "tasmota/tasmota_support/support_command.ino::SetoptionDecode"
    for nom, (quand, si) in so.items():
        redemarrent[nom] = {"quand": quand, "source": "tasmota/tasmota_support/support_command.ino::CmndSetoptionBase"
                            + (f" (redemarre seulement si {si})" if si else "")}

    def noms(expr, defines):
        """(prefixe, noms) ; la derniere case vide d'une chaine finie par « | » n'est pas une commande."""
        prefixe, *res = _chaine(expr, defines, globales).split("|")
        return prefixe, res[:-1] if res and not res[-1] else res

    for f, (code, code1, blanc, defines, _) in lus.items():
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
            ici = lieux[t] if f not in lieux[t] else {f: lieux[t][f]}   # table d'un autre fichier : comme `trouve`, tous ses emplacements
            emplacements = [(m, lus[g][0], _piles(lus[g][4])) for g, ms in ici.items() for m in ms]
            for nom, ch in _chemins_table({_nom(prefixe + b) for b in tous if prefixe + b}, emplacements,
                                          lambda ligne: _chaine(ligne, defines, globales)).items():
                chemins.setdefault(nom, set()).update(ch)
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
    berry = _berry(racine, connues)
    # une macro posee par un .ino (USE_MQTT_FILE, USE_I2S_MP3...) ou tasmota_globals.h (USE_TIMEPROP) echappe au preprocesseur de
    # verifie_lib_ignore::defines_env, qui la croirait absente (fausse alerte « non compilee ») : sa condition est retiree
    locales = {m for f, v in lus.items() if f.suffix != ".h" or f.name == "tasmota_globals.h"
               for m in re.findall(r"(?m)^[ \t]*#[ \t]*define[ \t]+(\w+)", v[4])}
    chemins = {n: {tuple(c for c in chemin if not locales & set(re.findall(r"\w+", c))) for chemin in ch} for n, ch in chemins.items()}
    gardes = {n: [list(c) for c in sorted(ch)] for n, ch in sorted(chemins.items())
              if n in connues and () not in ch and n not in berry and not re.fullmatch(r"SETOPTION\d*", n)}
    for nom, (quand, source) in RELUES.items():
        if nom in connues:
            redemarrent[nom] = {"quand": quand, "source": source}
    doc = extrait_doc(doc) if isinstance(doc, str) else dict(doc or {})
    for nom, extrait in doc.items():
        if nom in redemarrent:
            redemarrent[nom] = dict(redemarrent[nom], source=redemarrent[nom]["source"] + " ; doc Commands.md")
        elif nom in connues and nom not in EXCLUES and AFFIRME.search(extrait):
            redemarrent[nom] = {"quand": "toujours", "source": "doc Commands.md seulement"}
    return {"connues": dict(sorted(connues.items())), "redemarrent": dict(sorted(redemarrent.items())), "gardes": gardes,
            "doc": dict(sorted(doc.items())), "anomalies": anomalies}


def charge(racine):
    """Le fige : {"connues": {...}, "redemarrent": {...}, "doc": {...}, ...}."""
    return json.loads((Path(racine) / FIGE).read_text(encoding="utf-8"))


def verifie(racine, fige=None):
    """Ecarts (un texte par nom) entre le fige et ce que donne le code de `racine`, la doc reprise du fige."""
    fige = json.loads(Path(fige or Path(racine) / FIGE).read_text(encoding="utf-8"))
    code = genere(racine, doc=fige.get("doc", {}))
    ecarts = []
    for cle in ("connues", "redemarrent", "gardes"):
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
        print(f"{FIGE} : {len(res['connues'])} connues, {len(res['redemarrent'])} redemarrent, {len(res['gardes'])} gardees, "
              f"{len(res['doc'])} mentions de la doc, {len(res['anomalies'])} anomalie(s)")
    if a.verifier:
        ecarts = verifie(racine)
        print("\n".join(ecarts) or "fige conforme au code")
        return 1 if ecarts else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
