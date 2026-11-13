"""Fond d'un visuel d'accueil (atelier des visuels, spec 2026-11-13 §6.5) : nettoyage du SVG et controle du poids.

Le SVG vient du navigateur de l'utilisateur mais peut avoir ete retouche : tout ce qui n'est pas une forme est retire.
"""

import re
import xml.etree.ElementTree as ET

import atelier_visuels_description as avd

NS = "http://www.w3.org/2000/svg"
ELEMENTS = {"svg", "g", "path", "rect", "polygon", "circle", "line", "text", "defs", "pattern"}
ATTRIBUTS = {"d", "fill", "stroke", "stroke-width", "opacity", "fill-opacity", "stroke-opacity", "stroke-linecap", "stroke-linejoin",
             "stroke-dasharray", "fill-rule", "transform", "viewBox", "width", "height", "x", "y", "cx", "cy", "r", "rx", "ry",
             "x1", "y1", "x2", "y2", "points", "id", "patternUnits", "patternTransform", "preserveAspectRatio",
             "font-size", "font-family", "text-anchor"}
DANGER = re.compile(r"<!\s*(DOCTYPE|ENTITY)", re.I)
URL = re.compile(r"url\(\s*([^)]*)\)", re.I)
SIGNATURES = {"webp": lambda o: o[:4] == b"RIFF" and o[8:12] == b"WEBP", "jpg": lambda o: o[:3] == b"\xff\xd8\xff"}

ET.register_namespace("", NS)


def _sain(valeur):
    """Pas de script ni de donnee en ligne ; url() seulement vers un motif du meme fichier (#id)."""
    v = valeur.lower()
    if "javascript:" in v or "data:" in v or "&" in v:
        return False
    return all(m.group(1).strip("'\" ").startswith("#") for m in URL.finditer(valeur))


PROFONDEUR_MAX = 64


def _nettoie(el, prof=0):
    if prof > PROFONDEUR_MAX:
        raise ValueError(f"SVG refuse : imbrication au-dela de {PROFONDEUR_MAX} niveaux")
    nu = ET.Element(f"{{{NS}}}{el.tag.split('}')[-1]}")
    for cle, val in el.attrib.items():
        if cle in ATTRIBUTS and _sain(val):          # attribut a espace de noms (xlink:href), on*, style : ecartes
            nu.set(cle, val)
    nu.text = el.text if nu.tag.endswith("}text") else None
    for fils in el:
        if isinstance(fils.tag, str) and fils.tag.startswith(f"{{{NS}}}") and fils.tag.split("}")[1] in ELEMENTS:
            nu.append(_nettoie(fils, prof + 1))                # script, a, image, foreignObject, style : sous-arbre entier ecarte
    return nu


def nettoie_svg(texte):
    """SVG nettoye (texte). ValueError si ce n'est pas du SVG ou s'il porte un DOCTYPE ou une entite."""
    if DANGER.search(texte):
        raise ValueError("SVG refuse : DOCTYPE et entites interdits")
    try:
        racine = ET.fromstring(texte)
    except ET.ParseError as e:
        raise ValueError(f"SVG illisible : {e}") from None
    if racine.tag != f"{{{NS}}}svg":
        raise ValueError("SVG refuse : la racine doit etre <svg> de l'espace de noms SVG")
    return ET.tostring(_nettoie(racine), encoding="unicode")


def _limite(puce):
    return avd.SEUILS_REFUS["esp32" if puce == "ESP32" else "autre"]


def refuse(octets, puce):
    return len(octets) > _limite(puce)


def controle_fond(type_, octets, puce):
    """Message (refus ou avertissement) ; None si le fond convient. ValueError si le type ou le contenu ne va pas avec."""
    if type_ not in avd.TYPES_FOND:
        raise ValueError(f"type de fond inconnu : {type_!r}")
    if type_ in SIGNATURES and not SIGNATURES[type_](octets):
        raise ValueError(f"le contenu n'est pas une image {type_}")
    if refuse(octets, puce):
        return f"fond de {len(octets)} octets : au-dessus du seuil de {_limite(puce)} pour cette puce"
    return avd.avertissement(len(octets))
