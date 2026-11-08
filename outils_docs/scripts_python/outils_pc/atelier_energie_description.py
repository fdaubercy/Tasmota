#!/usr/bin/env python3
"""Schema et validation de la description de la page /energie du differentiel (atelier des graphiques, plan energie-atelier A1).

La description est le fichier `energie_page.json` de la carte. Le rendu JS de la carte (`data/sd/js/energie.js`) doit rendre
le MEME verdict que `valide()` sur `cas_energie.json` (a cote de ce module).

Forme (toute cle inconnue est refusee) :
    {"version": 1, "elements": [{"type", "titre", "source", "unite"?, "couleur"?, "largeur"?, "hauteur"?, "min"?, "max"?, "total"?}]}

- version : entier 1.   elements : 1 a BORNES["elements"] (16) ; le JSON compact (UTF-8) ne depasse pas BORNES["octets"] (4096).
- type : un des TYPES. valeur, cadran, demi-cercle prennent une source `direct` ou `total` ; barres, courbe, aire, escalier une source `flash`.
- titre : texte de 1 a BORNES["titre"] (40) caracteres.  unite : texte de 1 a 10 caracteres.  couleur : "#rrggbb".
- largeur : "demi" | "pleine".   hauteur : "petite" | "moyenne" | "grande".
- min, max : nombres (pas booleens), obligatoires et min < max sur cadran et demi-cercle, refuses ailleurs.
- total : booleen, seulement sur une source flash heure, jour, mois ou an.
- source, exactement une des trois formes :
    {"direct": <un des CHAMPS_DIRECT>}
    {"total": "jour"|"mois"|"an", "grandeur": "kWh"|"euros"}
    {"flash": "minutes"}                                  (puissance en W : pas de grandeur)
    {"flash": "heure"|"jour"|"mois"|"an", "grandeur": "kWh"|"euros", ...}   avec, en option :
        jour : "mois": "AAAA-MM" (mois fixe) OU "decalage": 0..23 (0 = mois en cours), jamais les deux ;
        mois : "nombre": 1..24.
"""
import json
import re

TYPES = ("valeur", "cadran", "demi-cercle", "barres", "courbe", "aire", "escalier")
CHAMPS_DIRECT = ("Power", "Current", "Factor", "Frequency", "Voltage", "ApparentPower", "ReactivePower",
                 "Today", "Yesterday", "Total")
BORNES = {"elements": 16, "octets": 4096, "titre": 40}
GRANDEURS = ("kWh", "euros")
RE_COULEUR = re.compile(r"#[0-9a-fA-F]{6}")
RE_MOIS = re.compile(r"[0-9]{4}-(0[1-9]|1[0-2])")
CLES = {"version", "elements"}
CLES_ELEMENT = {"type", "titre", "source", "unite", "couleur", "largeur", "hauteur", "min", "max", "total"}
SOURCES_PAR_TYPE = {"valeur": ("direct", "total"), "cadran": ("direct", "total"), "demi-cercle": ("direct", "total")}


def _el(type, titre, source, **kw):
    return {"type": type, "titre": titre, "source": source, "couleur": "#4a9eda", "largeur": "demi", "hauteur": "petite", **kw}


def _large(type, titre, source, **kw):
    return _el(type, titre, source, largeur="pleine", hauteur="moyenne", **kw)


# La page d'aujourd'hui : repli de energie.js et point de depart de l'atelier (plan energie-atelier A1 ; cas_energie.json en miroir).
DEFAUT = {"version": 1, "elements": [
    _el("valeur", "Puissance", {"direct": "Power"}, unite="W"),
    _el("valeur", "Courant", {"direct": "Current"}, unite="A"),
    _el("cadran", "Facteur", {"direct": "Factor"}, min=0, max=1),
    _el("valeur", "Fréquence", {"direct": "Frequency"}, unite="Hz"),
    _large("barres", "Aujourd'hui par heure", {"flash": "heure", "grandeur": "kWh"}, total=True),
    _large("barres", "Ce mois par jour", {"flash": "jour", "grandeur": "kWh"}, total=True),
    _large("barres", "12 derniers mois", {"flash": "mois", "grandeur": "kWh", "nombre": 12}, total=True),
    _large("courbe", "Puissance sur 24 h", {"flash": "minutes"}),
]}


def _nombre(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _entier(x, bas, haut):
    return isinstance(x, int) and not isinstance(x, bool) and bas <= x <= haut


def _texte(x, haut):
    return isinstance(x, str) and 1 <= len(x) <= haut


def _source(s, type, ou, m):
    """Controle la source d'un element ; ajoute les motifs a `m` ; rend la periode flash (ou None)."""
    if not isinstance(s, dict):
        m.append("%s : source : objet attendu" % ou)
        return None
    genres = [k for k in ("direct", "total", "flash") if k in s]
    if len(genres) != 1:
        m.append("%s : source : une seule des cles direct, total, flash" % ou)
        return None
    genre = genres[0]
    permis = SOURCES_PAR_TYPE.get(type, ("flash",))
    if type in TYPES and genre not in permis:
        m.append("%s : source %s impossible pour le type %s" % (ou, genre, type))
    autres = {"direct": set(), "total": {"grandeur"}, "flash": {"grandeur", "mois", "decalage", "nombre"}}[genre]
    for k in sorted(set(s) - {genre} - autres, key=str):
        m.append("%s : source : cle %r refusee avec %s" % (ou, k, genre))
    v = s[genre]
    if genre == "direct":
        if v not in CHAMPS_DIRECT:
            m.append("%s : direct %r hors des champs ENERGY" % (ou, v))
        return None
    if genre == "total" and v not in ("jour", "mois", "an"):
        m.append("%s : total %r : jour, mois ou an attendu" % (ou, v))
    if genre == "flash" and v not in ("minutes", "heure", "jour", "mois", "an"):
        m.append("%s : flash %r : minutes, heure, jour, mois ou an attendu" % (ou, v))
        return None
    if genre == "flash" and v == "minutes":
        if "grandeur" in s:
            m.append("%s : grandeur refusee sur minutes (puissance en W)" % ou)
    elif s.get("grandeur") not in GRANDEURS:
        m.append("%s : grandeur kWh ou euros attendue" % ou)
    if genre == "flash":
        if "mois" in s and "decalage" in s:
            m.append("%s : mois et decalage ensemble" % ou)
        if "mois" in s and (v != "jour" or not isinstance(s["mois"], str) or not RE_MOIS.fullmatch(s["mois"])):
            m.append("%s : mois AAAA-MM attendu, sur un graphique jour seulement" % ou)
        if "decalage" in s and (v != "jour" or not _entier(s["decalage"], 0, 23)):
            m.append("%s : decalage 0..23 attendu, sur un graphique jour seulement" % ou)
        if "nombre" in s and (v != "mois" or not _entier(s["nombre"], 1, 24)):
            m.append("%s : nombre 1..24 attendu, sur un graphique mois seulement" % ou)
        return v
    return None


def _element(e, ou, m):
    if not isinstance(e, dict):
        m.append("%s : element : objet attendu" % ou)
        return
    for k in sorted(set(e) - CLES_ELEMENT, key=str):
        m.append("%s : cle inconnue %r" % (ou, k))
    type = e.get("type")
    if type not in TYPES:
        m.append("%s : type inconnu %r" % (ou, type))
    if not _texte(e.get("titre"), BORNES["titre"]):
        m.append("%s : titre de 1 a %d caracteres" % (ou, BORNES["titre"]))
    periode = _source(e.get("source"), type, ou, m)
    if "unite" in e and not _texte(e["unite"], 10):
        m.append("%s : unite de 1 a 10 caracteres" % ou)
    if "couleur" in e and not (isinstance(e["couleur"], str) and RE_COULEUR.fullmatch(e["couleur"])):
        m.append("%s : couleur mal formee %r" % (ou, e["couleur"]))
    if e.get("largeur", "demi") not in ("demi", "pleine"):
        m.append("%s : largeur demi ou pleine attendue" % ou)
    if e.get("hauteur", "petite") not in ("petite", "moyenne", "grande"):
        m.append("%s : hauteur petite, moyenne ou grande attendue" % ou)
    jauge = type in ("cadran", "demi-cercle")
    for k in ("min", "max"):
        if k in e and not (jauge and _nombre(e[k])):
            m.append("%s : %s : nombre, sur un cadran ou un demi-cercle seulement" % (ou, k))
        elif jauge and k not in e:
            m.append("%s : %s obligatoire sur %s" % (ou, k, type))
    if jauge and _nombre(e.get("min")) and _nombre(e.get("max")) and e["min"] >= e["max"]:
        m.append("%s : min >= max" % ou)
    if "total" in e and (not isinstance(e["total"], bool) or periode in (None, "minutes")):
        m.append("%s : total : booleen, sur un graphique heure, jour, mois ou an seulement" % ou)


def valide(d):
    """Liste des motifs de refus de la description `d` (vide = valide)."""
    if not isinstance(d, dict):
        return ["description : objet attendu"]
    m = []
    for k in sorted(set(d) - CLES, key=str):
        m.append("cle inconnue %r" % (k,))
    if d.get("version") != 1 or isinstance(d.get("version"), bool):
        m.append("version : doit valoir 1")
    els = d.get("elements")
    if not isinstance(els, list) or not els:
        m.append("elements : liste non vide attendue")
        els = []
    elif len(els) > BORNES["elements"]:
        m.append("elements : %d > %d" % (len(els), BORNES["elements"]))
    for i, e in enumerate(els):
        _element(e, "element %d" % (i + 1), m)
    taille = len(json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode("utf-8", "surrogatepass"))
    if taille > BORNES["octets"]:
        m.append("taille : %d octets > %d" % (taille, BORNES["octets"]))
    return m
