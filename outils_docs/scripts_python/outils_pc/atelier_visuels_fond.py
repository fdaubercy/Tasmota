"""Fond d'un visuel d'accueil (atelier des visuels, spec 2026-11-13 §6.5) : nettoyage du SVG et controle du poids.

Le SVG vient du navigateur de l'utilisateur mais peut avoir ete retouche : tout ce qui n'est pas une forme est retire.
Une seule exception, SUR DEMANDE (`images=True`, le fond envoye par la page) : UNE `<image>` `data:` bornee, le morceau de photo d'une zone
« gardee en photo » (spec § 2.3) : type webp, jpeg ou png annonce ET confirme par les octets, 150 Ko decodes au plus, enfant direct de <svg> ou <g>,
aucun autre attribut que sa position, sa taille et son opacite. Toute autre image, ou une seconde, REFUSE le fond (ValueError) ; sans `images=True`
une image est ecartee comme avant (icones, reponses d'IA).
"""

import base64
import binascii
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
IMAGE_MAX = 150 * 1024
IMAGE_HREF = re.compile(r"^data:image/(webp|jpeg|png);base64,([A-Za-z0-9+/]+={0,2})$")
IMAGE_SIGNATURES = {"webp": lambda o: o[:4] == b"RIFF" and o[8:12] == b"WEBP", "jpeg": lambda o: o[:3] == b"\xff\xd8\xff", "png": lambda o: o[:8] == b"\x89PNG\r\n\x1a\n"}
IMAGE_ATTRIBUTS = {"x", "y", "width", "height", "opacity", "preserveAspectRatio"}
SIGNATURES = {"webp": lambda o: o[:4] == b"RIFF" and o[8:12] == b"WEBP", "jpg": lambda o: o[:3] == b"\xff\xd8\xff"}

ET.register_namespace("", NS)


def _sain(valeur):
    """Pas de script ni de donnee en ligne ; url() seulement vers un motif du meme fichier (#id)."""
    v = valeur.lower()
    if "javascript:" in v or "data:" in v or "&" in v:
        return False
    return all(m.group(1).strip("'\" ").startswith("#") for m in URL.finditer(valeur))


PROFONDEUR_MAX = 64


def _image(el, parent, ctx):
    """<image> data: autorisee, nettoyee ; ValueError si elle sort des bornes."""
    if ctx["images"]:
        raise ValueError("SVG refuse : une seule image par fond")
    if parent.tag.split("}")[1] not in ("svg", "g"):
        raise ValueError("SVG refuse : l'image doit etre un enfant direct de <svg> ou <g>")
    m = IMAGE_HREF.match(el.attrib.get("href", ""))
    if not m:
        raise ValueError("SVG refuse : image non autorisee (data:image/webp, jpeg ou png en base64 seulement)")
    try:
        octets = base64.b64decode(m.group(2), validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("SVG refuse : image en base64 illisible") from None
    if len(octets) > IMAGE_MAX:
        raise ValueError(f"SVG refuse : image de {len(octets)} octets, {IMAGE_MAX} au plus")
    if not IMAGE_SIGNATURES[m.group(1)](octets):
        raise ValueError(f"SVG refuse : le contenu de l'image n'est pas du {m.group(1)}")
    ctx["images"] += 1
    nu = ET.Element(f"{{{NS}}}image")
    nu.set("href", el.attrib["href"])
    for cle, val in el.attrib.items():
        if cle in IMAGE_ATTRIBUTS and _sain(val):
            nu.set(cle, val)
    return nu


def _nettoie(el, prof=0, ctx=None):
    ctx = ctx or {"images": 0, "autorise": False}
    if prof > PROFONDEUR_MAX:
        raise ValueError(f"SVG refuse : imbrication au-dela de {PROFONDEUR_MAX} niveaux")
    nu = ET.Element(f"{{{NS}}}{el.tag.split('}')[-1]}")
    for cle, val in el.attrib.items():
        if cle in ATTRIBUTS and _sain(val):          # attribut a espace de noms (xlink:href), on*, style : ecartes
            nu.set(cle, val)
    nu.text = el.text if nu.tag.endswith("}text") else None
    for fils in el:
        if not (isinstance(fils.tag, str) and fils.tag.startswith(f"{{{NS}}}")):
            continue
        if fils.tag.split("}")[1] == "image" and ctx["autorise"]:
            nu.append(_image(fils, el, ctx))
        elif fils.tag.split("}")[1] in ELEMENTS:
            nu.append(_nettoie(fils, prof + 1, ctx))                # script, a, image, foreignObject, style : sous-arbre entier ecarte
    return nu


def nettoie_svg(texte, images=False):
    """SVG nettoye (texte). ValueError si ce n'est pas du SVG, s'il porte un DOCTYPE ou une entite, ou (images=True) une image hors bornes."""
    if DANGER.search(texte):
        raise ValueError("SVG refuse : DOCTYPE et entites interdits")
    try:
        racine = ET.fromstring(texte)
    except ET.ParseError as e:
        raise ValueError(f"SVG illisible : {e}") from None
    if racine.tag != f"{{{NS}}}svg":
        raise ValueError("SVG refuse : la racine doit etre <svg> de l'espace de noms SVG")
    return ET.tostring(_nettoie(racine, 0, {"images": 0, "autorise": images}), encoding="unicode")


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
