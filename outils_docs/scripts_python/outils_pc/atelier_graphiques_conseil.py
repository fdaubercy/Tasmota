#!/usr/bin/env python3
"""Conseil de style de l'atelier des graphiques (plan atelier-graphiques, A5) : regles explicites, ni apprentissage ni hasard.

    propose(intention, series, destination, historique)
        -> {"proposes": [{"style", "raison"}], "ecartes": [{"style", "motif"}]}

Chaque style de STYLES figure exactement une fois dans l'une des deux listes. 3 a 5 styles proposes, classes, SAUF :
- destination "accueil" (SVG seul = demi-cercle) : un seul style possible, il est le seul propose ;
- destination "graphiques" : 4 styles seulement au palier 1, donc parfois moins de 3 proposes ;
- cas ou presque rien ne convient (ex. aucun historique et une seule serie non bornee) : on rend ce qui convient.

Etapes : (1) un style est ecarte s'il est impossible (destination, historique absent, nombre de series, bornes, unites) ;
(2) les styles restants sont pris dans l'ordre de preference de l'intention, 5 au plus ; (3) hors de la liste de
l'intention, ils sont ecartes ; sur la destination "page", si moins de 3 sont proposes, on complete avec les styles
possibles restants (raison generique).
"""
from atelier_graphiques_description import STYLES

INTENTIONS = ("evolution", "seuil", "comparaison", "repartition", "cumul", "lien", "habitudes")
PALIER1 = {"graphiques": ("courbe", "aire", "escalier", "barres"), "accueil": ("demi-cercle",)}
# Styles qui lisent des donnees datees (jour/mois ou serie dans le temps) : impossibles sans historique.
TEMPORELS = ("courbe", "aire", "escalier", "barres", "barres-empilees", "barres-periode", "deux-axes", "lies", "chaleur", "nuage")
BORNES_REQUISES = ("cadran", "liquide", "demi-cercle")
PREFERENCES = {
    "evolution": (("deux-axes", "deux grandeurs d'unités différentes sur un même temps, chacune sur son axe"),
                  ("courbe", "la lecture la plus directe d'une évolution dans le temps"),
                  ("aire", "montre l'évolution et le volume sous la courbe"),
                  ("escalier", "garde la valeur jusqu'au changement suivant, adapté aux états"),
                  ("lies", "superpose plusieurs séries sur la même échelle")),
    "seuil": (("cadran", "une aiguille sur une échelle bornée, le dépassement se voit d'un coup d'œil"),
              ("demi-cercle", "jauge compacte en SVG, utilisable aussi sur l'accueil"),
              ("liquide", "niveau rempli entre le minimum et le maximum"),
              ("courbe", "suit l'approche du seuil dans le temps"),
              ("aire", "suit l'approche du seuil dans le temps, avec le volume sous la courbe")),
    "comparaison": (("barres", "compare des valeurs côte à côte"),
                    ("radar", "compare plusieurs grandeurs d'un seul regard"),
                    ("courbe", "compare les séries au fil du temps"),
                    ("lies", "superpose les séries sur la même échelle"),
                    ("barres-empilees", "compare en montrant la part de chacune dans le total")),
    "repartition": (("anneau", "montre la part de chaque série dans un total"),
                    ("barres-empilees", "empile les parts pour les comparer dans le temps"),
                    ("radar", "compare le profil des grandeurs"),
                    ("barres", "compare les valeurs entre elles"),
                    ("liquide", "niveau rempli d'une grandeur par rapport à son maximum")),
    "cumul": (("barres-periode", "cumule par heure, jour ou mois"),
              ("barres", "une barre par période, le total se lit tout de suite"),
              ("aire", "l'aire donne le cumul sur la durée"),
              ("barres-empilees", "cumule en séparant les séries"),
              ("courbe", "suit la progression du cumul")),
    "lien": (("nuage", "une série contre l'autre, la corrélation se voit en nuage de points"),
             ("lies", "les deux séries sur la même échelle de temps"),
             ("deux-axes", "deux grandeurs d'unités différentes superposées"),
             ("courbe", "les séries tracées ensemble pour voir si elles bougent ensemble")),
    "habitudes": (("chaleur", "carte jour × heure : montre à quels moments la valeur est haute"),
                  ("courbe", "montre la répétition du motif au fil des jours"),
                  ("barres-periode", "une barre par heure ou par jour pour repérer le rythme"),
                  ("aire", "montre le motif et son volume dans le temps"),
                  ("barres", "compare les périodes entre elles")),
}


def _impossible(style, series, destination, historique):
    """Motif d'ecart si le style ne peut pas servir, sinon None."""
    n, unites = len(series), {s["unite"] for s in series if s.get("unite")}
    if style not in PALIER1.get(destination, STYLES):
        return "pas disponible pour cette destination (« %s »)" % destination
    if style in TEMPORELS and not historique:
        return "demande un historique que cette carte n'a pas"
    if style in BORNES_REQUISES and (n != 1 or "min" not in series[0] or "max" not in series[0]):
        return "demande une seule série bornée (minimum et maximum connus)"
    if style == "anneau" and n < 2:
        return "montre des parts d'un total : il faut au moins deux séries"
    if style == "radar" and n < 3:
        return "demande au moins trois séries"
    if style in ("lies", "barres-empilees") and n < 2:
        return "demande au moins deux séries"
    if style == "nuage" and n != 2:
        return "oppose exactement deux séries"
    if style == "deux-axes" and len(unites) < 2:
        return "demande deux séries d'unités différentes"
    return None


def propose(intention, series, destination, historique):
    if intention not in INTENTIONS:
        raise ValueError("intention inconnue : %r" % (intention,))
    if destination not in ("page", "graphiques", "accueil"):
        raise ValueError("destination inconnue : %r (page, graphiques ou accueil)" % (destination,))
    if not isinstance(series, list) or not all(isinstance(s, dict) for s in series):
        raise ValueError("series doit être une liste de séries (objets)")
    if not isinstance(historique, bool):
        raise ValueError("historique doit être vrai ou faux")
    ecartes, possibles = {}, {}
    for st in STYLES:
        m = _impossible(st, series, destination, historique)
        if m:
            ecartes[st] = m
        else:
            possibles[st] = True
    proposes = [{"style": st, "raison": r} for st, r in PREFERENCES[intention] if st in possibles][:5]
    pris = {p["style"] for p in proposes}
    if destination == "page" and len(proposes) < 3:
        for st in STYLES:
            if st in possibles and st not in pris and len(proposes) < 3:
                proposes.append({"style": st, "raison": "possible avec ces séries, mais moins adapté à cette intention"})
                pris.add(st)
    for st in possibles:
        if st not in pris:
            ecartes[st] = "moins adapté à cette intention que les styles proposés"
    return {"proposes": proposes, "ecartes": [{"style": st, "motif": ecartes[st]} for st in STYLES if st in ecartes]}
