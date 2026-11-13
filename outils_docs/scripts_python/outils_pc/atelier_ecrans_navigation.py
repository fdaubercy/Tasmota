"""Barre de navigation construite d'apres les pages (atelier des ecrans, plan atelier-ecrans A17).

Cle `navigation` a la racine de la description : {"x", "y", "h", "ecart", "attributs": {style des boutons}, "actif"?:
{couleurs du bouton de la page courante}}. Une page n >= 1 y figure, sauf `"menu": false`. Bouton de la page n : objet `btn`
de la page 0, id 200 + n (201 a 254, reserves), texte = titre de la page (sinon « Page n »), toucher {"page": n}, largeur =
arrondi(longueur du titre x taille de police x 0,55) + h, places de gauche a droite separes de `ecart`.
`deroule` est appele par le validateur et par les deux generateurs ; la page de l'atelier fait le meme calcul
(atelier_ecrans_page_navigation.py::boutonsNav), compare par la sonde Chrome.
"""
import copy
import re

ID_BASE = 200
ID_MAX = 254
CHAMPS = ("x", "y", "h", "ecart")


def taille(v):
    """Taille d'une police text_font : entier = taille ; « <nom>-<taille> » ; 14 sinon (comme taillePolice de la page)."""
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    m = re.search(r"-(\d+)$", str(v or ""))
    return int(m.group(1)) if m else 14


def largeur(titre, police, h):
    return int(len(titre) * taille(police) * 0.55 + 0.5) + h        # arrondi au plus proche, comme Math.floor(v + 0.5)


def boutons(desc):
    """Objets btn de la page 0 tires de `navigation` (liste vide sans barre)."""
    nav = desc.get("navigation")
    if not isinstance(nav, dict):
        return []
    attrs = nav.get("attributs") or {}
    x, res = nav.get("x", 0), []
    for p in desc.get("pages", []):
        n = p.get("n")
        if not isinstance(n, int) or isinstance(n, bool) or n < 1 or p.get("menu") is False:
            continue
        titre = p.get("titre") or f"Page {n}"
        l = largeur(titre, attrs.get("text_font"), nav.get("h", 0))
        o = {"id": ID_BASE + n, "page": 0, "type": "btn", "x": x, "y": nav.get("y", 0), "l": l, "h": nav.get("h", 0),
             "attributs": {**attrs, "text": titre}, "toucher": {"page": n}}
        if nav.get("actif"):
            o["actif"] = dict(nav["actif"])
        res.append(o)
        x += l + nav.get("ecart", 0)
    return res


def deroule(desc):
    """Copie de la description, boutons de la barre ajoutes aux objets (apres ceux de l'utilisateur) ; sans barre : elle-meme."""
    if "navigation" not in desc:
        return desc
    d = copy.deepcopy(desc)
    d.pop("navigation")
    d["objets"] = d.get("objets", []) + boutons(desc)
    return d
