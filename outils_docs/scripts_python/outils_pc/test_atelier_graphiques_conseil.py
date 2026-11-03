#!/usr/bin/env python3
"""Banc de atelier_graphiques_conseil.py (plan atelier-graphiques, A5). Cas figes a la main, jamais derives des regles.

    <Python de PlatformIO> outils_docs/scripts_python/outils_pc/test_atelier_graphiques_conseil.py

Code de sortie 0 = vert, 1 = rouge.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atelier_graphiques_conseil as c
from atelier_graphiques_description import STYLES

ECHECS = []


def verifie(ok, nom):
    print(("ok   " if ok else "ECHEC"), nom)
    if not ok:
        ECHECS.append(nom)


def S(chemin, unite="", borne=False):
    d = {"chemin": chemin, "libelle": chemin, "unite": unite, "historique": True, "etat": False}
    return {**d, "min": 0, "max": 100} if borne else d


def noms(r, cle="proposes"):
    return [x["style"] for x in r[cle]]


def motif(r, style):
    return next(x["motif"] for x in r["ecartes"] if x["style"] == style)


def complet(r, nom):
    tous = noms(r) + noms(r, "ecartes")
    verifie(sorted(tous) == sorted(STYLES), nom + " : chaque style une seule fois")
    verifie(all(x["raison"] for x in r["proposes"]) and all(x["motif"] for x in r["ecartes"]), nom + " : textes non vides")


verifie(c.INTENTIONS == ("evolution", "seuil", "comparaison", "repartition", "cumul", "lien", "habitudes"), "intentions")

r = c.propose("seuil", [S("a.b", "L", True)], "page", True)
complet(r, "seuil")
verifie(noms(r)[0] == "cadran" and 3 <= len(r["proposes"]) <= 5, "seuil + 1 serie bornee : cadran premier")

r = c.propose("seuil", [S("a.b", "L")], "page", True)
verifie("cadran" in noms(r, "ecartes") and "bornée" in motif(r, "cadran"), "seuil sans bornes : cadran ecarte (borne)")

r = c.propose("evolution", [S("a.t", "C"), S("a.v", "L")], "page", True)
complet(r, "evolution")
verifie(noms(r)[0] == "deux-axes" and 3 <= len(r["proposes"]) <= 5, "evolution + 2 unites : deux-axes premier")

r = c.propose("evolution", [S("a.t", "C"), S("a.u", "C")], "page", True)
verifie("deux-axes" in noms(r, "ecartes") and noms(r)[0] == "courbe", "evolution, 1 seule unite : courbe premiere")

r = c.propose("repartition", [S("a.b", "L")], "page", True)
complet(r, "repartition")
verifie("anneau" in noms(r, "ecartes") and "parts d'un total" in motif(r, "anneau"), "repartition + 1 serie : anneau ecarte")
r = c.propose("repartition", [S("a", "W"), S("b", "W"), S("c", "W")], "page", True)
verifie(noms(r)[0] == "anneau", "repartition + 3 series : anneau premier")

r = c.propose("habitudes", [S("a.b", "W")], "page", False)
complet(r, "habitudes sans historique")
verifie("chaleur" in noms(r, "ecartes") and "historique" in motif(r, "chaleur"), "habitudes sans historique : chaleur ecarte")
verifie("courbe" in noms(r, "ecartes") and "historique" in motif(r, "courbe"), "sans historique : courbe ecartee")
r = c.propose("habitudes", [S("a.b", "W")], "page", True)
verifie(noms(r)[0] == "chaleur", "habitudes avec historique : chaleur premiere")

r = c.propose("seuil", [S("a.b", "L", True)], "accueil", True)
complet(r, "accueil")
verifie(noms(r) == ["demi-cercle"], "accueil : seul demi-cercle propose")
verifie("accueil" in motif(r, "courbe"), "accueil : courbe ecartee pour la destination")

r = c.propose("evolution", [S("a.b", "C")], "graphiques", True)
complet(r, "graphiques")
verifie(set(noms(r)) <= {"courbe", "aire", "escalier", "barres"} and noms(r)[0] == "courbe", "graphiques : 4 styles du palier 1")

r = c.propose("seuil", [S("a.b", "L", True)], "page", False)
verifie(noms(r)[0] == "cadran" and "courbe" in noms(r, "ecartes"), "seuil sans historique : cadran garde, courbe ecartee")

try:
    c.propose("inconnue", [S("a")], "page", True)
    verifie(False, "intention inconnue refusee")
except ValueError:
    verifie(True, "intention inconnue refusee")

print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
sys.exit(1 if ECHECS else 0)
