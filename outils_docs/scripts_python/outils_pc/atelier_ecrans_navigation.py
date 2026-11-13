"""Barre de navigation construite d'apres les pages (atelier des ecrans, plan atelier-ecrans A17).

Cle `navigation` a la racine de la description : {"x", "y", "h", "ecart", "attributs": {style des boutons}, "actif"?:
{couleurs du bouton de la page courante}}. Une page n >= 1 y figure, sauf `"menu": false`. Bouton de la page n : objet `btn`
de la page 0, id 200 + n (201 a 254, reserves), texte = titre de la page (sinon « Page n »), toucher {"page": n}, largeur =
arrondi(longueur du titre x taille de police x 0,55) + h, places de gauche a droite separes de `ecart`.
`deroule` est le POINT D'ENTREE UNIQUE du deroule (barre de navigation ET page Systeme, atelier_ecrans_systeme.deroule),
appele par le validateur, les deux generateurs et l'apercu de la page web ; la page de l'atelier refait le calcul de la barre
(atelier_ecrans_page_navigation.py::boutonsNav), compare par la sonde Chrome, et recoit du serveur les objets de la page Systeme.
"""
import copy
import re

import atelier_ecrans_systeme as aes

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


def deroule(desc, catalogue=None):
    """Copie de la description, objets de la page Systeme puis boutons de la barre ajoutes aux objets (apres ceux de
    l'utilisateur), cles `modele` et `navigation` retirees ; rien a derouler : elle-meme. `catalogue` : taille de l'ecran pour
    la page Systeme (None : catalogue du depot)."""
    d = aes.deroule(desc, catalogue)             # avant la barre : sa zone s'arrete au haut de la barre
    if "navigation" not in d:
        return d
    d = copy.deepcopy(d) if d is desc else d
    d.pop("navigation")
    d["objets"] = d.get("objets", []) + boutons(desc)
    return d
