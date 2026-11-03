#!/usr/bin/env python3
"""Schema et validation de la description des pages de graphiques d'une carte (atelier des graphiques, plan A1).

La description est le fichier `pages_graphiques.json` d'une carte. Le moteur Berry de la carte (A2) et le traceur JS (A3)
doivent rendre le MEME verdict que `valide()` sur `berry/bouchons_berry/pages_graphiques/cas_description.json`.

Forme (toute cle inconnue est refusee) :
    {"version": 1,
     "pages": [{"id", "titre", "acces": "bouton"|"lien",
                "graphiques": [{"type", "titre", "series": [...], "min", "max", "zones": [[seuil, "#rrggbb"], ...],
                                "periode": "direct"|"jour"|"mois", "cadence", "largeur": "demi"|"pleine", "hauteur",
                                "cumul": "heure"|"jour"|"mois"}]}],
     "encadres": [{"id", "type", "serie", "lien"}],
     "calculees": {"nom": {"formule": "...", "nature": "direct"|"historique"}}}

Champs et bornes :
- version : entier 1.   pages : 1 a BORNES["pages"] (8) ; encadres : 0 a 8 ; calculees : 0 a 16.
- page.id : [a-z0-9-]{1,24}, unique, hors ROUTES_RESERVEES.  page.titre : texte de 1 a 60 octets UTF-8.  acces : defaut "bouton".
- graphique.type : un des STYLES.  titre : 1 a 60 octets.  series : 1 a BORNES["series"] (12) ; graphiques par page : 1 a 8.
  Une serie est un chemin du SENSOR `nom(.nom)*` ([A-Za-z_][A-Za-z0-9_]* puis segments [A-Za-z0-9_]+, sans "__",
  aucun segment constructor/prototype), ou `calc:<nom>` d'une calculee declaree. Le validateur ne sait pas si un chemin brut
  est historique : il l'accepte tel quel.
  Dans `graphique.series` (pas dans `encadre.serie`), un element est SOIT cette chaine, SOIT un objet
  {"chemin": <la chaine>, "libelle"?, "unite"?, "couleur"?} (formes melangeables) : chemin obligatoire, libelle texte de
  1 a 30 octets, unite texte de 1 a 10 octets, couleur "#rrggbb" ; aucune autre cle. Les regles sur les series (calculee
  connue, nature, cumul) portent sur `chemin` quelle que soit la forme. Aucune regle de doublon, dans l'une ou l'autre forme.
- min, max : nombres (pas booleens) ; si les deux sont donnes, min < max.  zones : liste de [seuil, "#rrggbb"], seuil dans [0, 1].
- periode : defaut "direct".  cadence : entier 1..3600 (secondes).  largeur : defaut "demi".  hauteur : entier 80..600.
- cumul : "heure"|"jour"|"mois", refuse sur une calculee de nature "direct".
- encadre : id [a-z0-9-]{1,24} unique parmi les encadres, type dans STYLES, serie (meme regle), lien facultatif = id d'une page.
- calculee : nom au format chemin (<= 48), formule <= 200 octets, nature obligatoire. Une calculee "direct" est refusee dans
  un graphique de periode jour/mois ; une "historique" dans un graphique de periode direct.
- taille : le JSON compact (separateurs "," et ":", UTF-8) ne depasse pas BORNES["octets"] (8192) octets.

Grammaire des formules (liste blanche, JAMAIS d'eval ; reference a re-implementer a l'identique en Berry et en JS) :
    expr    := terme (('+' | '-') terme)*
    terme   := facteur (('*' | '/') facteur)*
    facteur := ['-'] ( nombre | chemin | fonction '(' expr (',' expr)* ')' | '(' expr ')' )
    nombre  := [0-9]+ ('.' [0-9]+)?                         (chiffres ASCII seulement)
    chemin  := [A-Za-z_][A-Za-z0-9_]* ('.' [A-Za-z0-9_]+)*   ("__" et segments constructor/prototype refuses)
    fonction := min | max | abs | round                    (un chemin de ce nom DOIT etre suivi de '(')
Arite : abs et round exactement 1 argument ; min et max 2 arguments ou plus.
Seuls separateurs : l'espace et la tabulation (entre jetons). Toute la formule doit etre consommee ; tout autre caractere
la refuse. Un nom suivi de '(' qui n'est pas une fonction est refuse.

Longueurs de texte (titres, formules) : mesurees en OCTETS UTF-8 (Berry compte les octets ; JS utilisera TextEncoder).
"""
import json
import re

STYLES = ("courbe", "aire", "escalier", "barres", "barres-empilees", "barres-periode", "deux-axes", "lies",
          "cadran", "anneau", "chaleur", "nuage", "radar", "liquide", "demi-cercle")
BORNES = {"pages": 8, "graphiques": 8, "series": 12, "octets": 8192}
ROUTES_RESERVEES = frozenset("""cs cm cn in up u1 u2 u3 rs rt md mn sv cf dl upl ufsd ufsu graphiques histo cuve energie
pages coprocesseur discovery json sd""".split())
MAX_ENCADRES, MAX_CALCULEES = 8, 16
FONCTIONS = ("min", "max", "abs", "round")
INTERDITS = ("constructor", "prototype")
RE_ID = re.compile(r"[a-z0-9-]{1,24}")
RE_CHEMIN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)*")
RE_COULEUR = re.compile(r"#[0-9a-fA-F]{6}")
RE_JETON = re.compile(r"[ 	]*(?:([0-9]+(?:\.[0-9]+)?)|([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*)|([-+*/(),]))")
CLES = {
    "racine": {"version", "pages", "encadres", "calculees"},
    "page": {"id", "titre", "acces", "graphiques"},
    "graphique": {"type", "titre", "series", "min", "max", "zones", "periode", "cadence", "largeur", "hauteur", "cumul"},
    "encadre": {"id", "type", "serie", "lien"},
    "calculee": {"formule", "nature"},
    "serie": {"chemin", "libelle", "unite", "couleur"},
}


def _nombre(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _entier(x, bas, haut):
    return isinstance(x, int) and not isinstance(x, bool) and bas <= x <= haut


def _chemin_ok(s):
    return isinstance(s, str) and len(s) <= 96 and bool(RE_CHEMIN.fullmatch(s)) and "__" not in s \
        and not any(seg in INTERDITS for seg in s.split("."))


def _octets(t):
    return len(t.encode("utf-8", "surrogatepass"))


def _jetons(f):
    """Liste de (genre, texte) ou None si un caractere est hors liste blanche."""
    out, i = [], 0
    while f[i:].strip(" 	"):
        m = RE_JETON.match(f, i)
        if not m:
            return None
        i = m.end()
        out.append(("n", m.group(1)) if m.group(1) else ("c", m.group(2)) if m.group(2) else ("s", m.group(3)))
    return out


def valide_formule(f):
    """Motif de refus d'une formule, ou None si elle est acceptee (grammaire du docstring du module)."""
    if not isinstance(f, str) or not f.strip(" 	") or _octets(f) > 200:
        return "formule vide, non textuelle ou trop longue"
    t = _jetons(f)
    if t is None:
        return "formule interdite : caractere hors liste blanche"
    pos = [0]

    def suit(x):
        return pos[0] < len(t) and t[pos[0]] == ("s", x)

    def expr():
        terme()
        while suit("+") or suit("-"):
            pos[0] += 1
            terme()

    def terme():
        facteur()
        while suit("*") or suit("/"):
            pos[0] += 1
            facteur()

    def facteur():
        if suit("-"):
            pos[0] += 1
        if pos[0] >= len(t):
            raise ValueError("operande attendu en fin de formule")
        genre, texte = t[pos[0]]
        pos[0] += 1
        if genre == "n":
            return
        if genre == "c":
            if not _chemin_ok(texte):
                raise ValueError("chemin refuse %r" % texte)
            if texte in FONCTIONS:
                if not suit("("):
                    raise ValueError("fonction %s sans parenthese" % texte)
                pos[0] += 1
                n = 1
                expr()
                while suit(","):
                    pos[0] += 1
                    expr()
                    n += 1
                if not suit(")"):
                    raise ValueError("parenthese fermante attendue")
                pos[0] += 1
                if (texte in ("abs", "round") and n != 1) or (texte in ("min", "max") and n < 2):
                    raise ValueError("arite de %s : %d argument(s)" % (texte, n))
            return
        if (genre, texte) == ("s", "("):
            expr()
            if not suit(")"):
                raise ValueError("parenthese fermante attendue")
            pos[0] += 1
            return
        raise ValueError("operande attendu avant %r" % texte)

    try:
        expr()
        if pos[0] != len(t):
            raise ValueError("jeton inattendu %r" % (t[pos[0]][1],))
    except ValueError as e:
        return "formule interdite : %s" % e
    return None


def _serie(s, calculees):
    """Rend (motif, nature) ; nature = celle de la calculee citee, sinon None (chemin brut)."""
    if isinstance(s, str) and s.startswith("calc:"):
        c = calculees.get(s[5:])
        if not isinstance(c, dict) or c.get("nature") not in ("direct", "historique"):
            return "serie %r : calculee inconnue" % s, None
        return None, c["nature"]
    if not _chemin_ok(s):
        return "serie %r : chemin invalide" % (s,), None
    return None, None


def _serie_objet(s, ou, m):
    """Controle les cles de la forme objet d'une serie de graphique ; rend son chemin."""
    _cles(s, "serie", m)
    for cle, n in (("libelle", 30), ("unite", 10)):
        if cle in s and not (isinstance(s[cle], str) and 1 <= _octets(s[cle]) <= n):
            m.append("%s : %s de 1 a %d octets" % (ou, cle, n))
    if "couleur" in s and not (isinstance(s["couleur"], str) and RE_COULEUR.fullmatch(s["couleur"])):
        m.append("%s : couleur de serie mal formee %r" % (ou, s["couleur"]))
    if "chemin" not in s:
        m.append("%s : serie sans chemin" % ou)
    return s.get("chemin")


def _cles(obj, quoi, m):
    for k in sorted(set(obj) - CLES[quoi], key=str):
        m.append("%s : cle inconnue %r" % (quoi, k))


def _graphique(g, ou, calculees, m):
    if not isinstance(g, dict):
        m.append("%s : objet attendu" % ou)
        return
    _cles(g, "graphique", m)
    if g.get("type") not in STYLES:
        m.append("%s : style inconnu %r" % (ou, g.get("type")))
    if not isinstance(g.get("titre"), str) or not 1 <= _octets(g["titre"]) <= 60:
        m.append("%s : titre de 1 a 60 caracteres" % ou)
    periode = g.get("periode", "direct")
    if periode not in ("direct", "jour", "mois"):
        m.append("%s : periode %r invalide" % (ou, periode))
    if g.get("largeur", "demi") not in ("demi", "pleine"):
        m.append("%s : largeur invalide" % ou)
    if "cadence" in g and not _entier(g["cadence"], 1, 3600):
        m.append("%s : cadence hors 1..3600" % ou)
    if "hauteur" in g and not _entier(g["hauteur"], 80, 600):
        m.append("%s : hauteur hors 80..600" % ou)
    cumul = g.get("cumul")
    if "cumul" in g and cumul not in ("heure", "jour", "mois"):
        m.append("%s : cumul %r invalide" % (ou, cumul))
    for k in ("min", "max"):
        if k in g and not _nombre(g[k]):
            m.append("%s : %s doit etre un nombre" % (ou, k))
    if _nombre(g.get("min")) and _nombre(g.get("max")) and g["min"] >= g["max"]:
        m.append("%s : min >= max" % ou)
    zones = g.get("zones", [])
    if not isinstance(zones, list):
        m.append("%s : zones doit etre une liste" % ou)
    else:
        for z in zones:
            if not (isinstance(z, list) and len(z) == 2 and _nombre(z[0]) and isinstance(z[1], str)
                    and RE_COULEUR.fullmatch(z[1])):
                m.append("%s : zone mal formee %r" % (ou, z))
            elif not 0 <= z[0] <= 1:
                m.append("%s : zone hors [0, 1] : %r" % (ou, z[0]))
    series = g.get("series")
    if not isinstance(series, list) or not series:
        m.append("%s : series doit etre une liste non vide" % ou)
        return
    if len(series) > BORNES["series"]:
        m.append("%s : series : %d > %d" % (ou, len(series), BORNES["series"]))
    for s in series:
        if isinstance(s, dict):
            s = _serie_objet(s, ou, m)
        motif, nature = _serie(s, calculees)
        if motif:
            m.append("%s : %s" % (ou, motif))
        elif nature == "direct" and periode in ("jour", "mois"):
            m.append("%s : nature de la formule incompatible, %s (direct) sur periode %s" % (ou, s, periode))
        elif nature == "historique" and periode == "direct":
            m.append("%s : nature de la formule incompatible, %s (historique) sur periode direct" % (ou, s))
        if nature == "direct" and cumul in ("heure", "jour", "mois"):
            m.append("%s : cumul sur une serie instantanee, %s" % (ou, s))


def _id(v, vus, ou, m):
    if not isinstance(v, str) or not RE_ID.fullmatch(v):
        m.append("%s : id invalide %r (attendu [a-z0-9-]{1,24})" % (ou, v))
        return
    if v in ROUTES_RESERVEES:
        m.append("%s : id reserve %r (route existante)" % (ou, v))
    elif v in vus:
        m.append("%s : id en double %r" % (ou, v))
    vus.add(v)


def valide(d):
    """Liste des motifs de refus de la description `d` (vide = valide)."""
    if not isinstance(d, dict):
        return ["description : objet attendu"]
    m = []
    _cles(d, "racine", m)
    if d.get("version") != 1 or isinstance(d.get("version"), bool):
        m.append("version : doit valoir 1")
    calc = d.get("calculees", {})
    if not isinstance(calc, dict) or len(calc) > MAX_CALCULEES:
        m.append("calculees : objet de %d entrees au plus" % MAX_CALCULEES)
        calc = {}
    for nom, c in calc.items():
        if not _chemin_ok(nom) or len(nom) > 48:
            m.append("calculee %r : nom invalide" % nom)
        if not isinstance(c, dict):
            m.append("calculee %r : objet attendu" % nom)
            continue
        _cles(c, "calculee", m)
        if c.get("nature") not in ("direct", "historique"):
            m.append("calculee %r : nature direct ou historique attendue" % nom)
        motif = valide_formule(c.get("formule"))
        if motif:
            m.append("calculee %r : %s" % (nom, motif))
    pages = d.get("pages")
    ids = set()
    if not isinstance(pages, list) or not pages:
        m.append("pages : liste non vide attendue")
        pages = []
    elif len(pages) > BORNES["pages"]:
        m.append("pages : %d > %d" % (len(pages), BORNES["pages"]))
    for i, p in enumerate(pages):
        ou = "page %d" % (i + 1)
        if not isinstance(p, dict):
            m.append("%s : objet attendu" % ou)
            continue
        _cles(p, "page", m)
        _id(p.get("id"), ids, ou, m)
        if not isinstance(p.get("titre"), str) or not 1 <= _octets(p["titre"]) <= 60:
            m.append("%s : titre de 1 a 60 caracteres" % ou)
        if p.get("acces", "bouton") not in ("bouton", "lien"):
            m.append("%s : acces bouton ou lien attendu" % ou)
        gs = p.get("graphiques")
        if not isinstance(gs, list) or not gs:
            m.append("%s : graphiques doit etre une liste non vide" % ou)
            continue
        if len(gs) > BORNES["graphiques"]:
            m.append("%s : graphiques : %d > %d" % (ou, len(gs), BORNES["graphiques"]))
        for j, g in enumerate(gs):
            _graphique(g, "%s graphique %d" % (ou, j + 1), calc, m)
    encs = d.get("encadres", [])
    if not isinstance(encs, list) or len(encs) > MAX_ENCADRES:
        m.append("encadres : liste de %d au plus" % MAX_ENCADRES)
        encs = []
    vus = set()
    for i, e in enumerate(encs):
        ou = "encadre %d" % (i + 1)
        if not isinstance(e, dict):
            m.append("%s : objet attendu" % ou)
            continue
        _cles(e, "encadre", m)
        _id(e.get("id"), vus, ou, m)
        if e.get("type") not in STYLES:
            m.append("%s : style inconnu %r" % (ou, e.get("type")))
        motif, _ = _serie(e.get("serie"), calc)
        if motif:
            m.append("%s : %s" % (ou, motif))
        if "lien" in e and (not isinstance(e["lien"], str) or e["lien"] not in ids):
            m.append("%s : lien vers une page inconnue %r" % (ou, e["lien"]))
    taille = len(json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode("utf-8", "surrogatepass"))
    if taille > BORNES["octets"]:
        m.append("taille : %d octets > %d" % (taille, BORNES["octets"]))
    return m
