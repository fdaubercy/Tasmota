"""Consignes de creation des visuels d'accueil, lues dans outils_docs/visuels_accueil/CONSIGNES_VISUELS.md (reference unique).

Le fichier est RELU A CHAQUE APPEL : une regle ajoutee au fichier apparait dans la page sans relancer l'outil. Aucune ecriture.

    texte(racine)   -> le fichier en texte (LookupError s'il manque)
    regles(racine)  -> {"organes": [{nom, regle}], "jour_nuit": [ligne], "clic": [ligne], "par_type": {voyant|valeur|liaison: [nom d'organe]}}

Organes : lignes du tableau de la section « 4. Les organes et leurs regles ». jour_nuit et clic : puces des sections « Jour et nuit » et
« Commande par clic ». par_type dit quels organes concernent chaque type de point chaud de l'atelier ; un nom absent du fichier est ignore.
"""
import re
from pathlib import Path

FICHIER = Path("outils_docs/visuels_accueil/CONSIGNES_VISUELS.md")
# Point chaud de l'atelier -> organes de la section 4 qu'il peut representer (voyant d'un organe, valeur lue, liaison/commande)
PAR_TYPE = {
    "voyant": ["Capteur de fermeture", "Feu orange", "Lampe du garage", "Caméra"],
    "valeur": ["Capteur de fermeture"],
    "liaison": ["Grande porte du garage", "Portail de jardin"],
}


def texte(racine):
    f = Path(racine) / FICHIER
    if not f.is_file():
        raise LookupError("consignes introuvables : " + FICHIER.as_posix())
    return f.read_text(encoding="utf-8")


def _section(lignes, motif):
    """Lignes de la section dont le titre (## ...) contient motif, jusqu'au titre suivant."""
    sortie, dedans = [], False
    for l in lignes:
        if l.startswith("## "):
            dedans = motif.lower() in l.lower()
            continue
        if dedans:
            sortie.append(l)
    return sortie


def _puces(lignes):
    """Puces (« - ») d'une section, avec leurs lignes de suite jointes."""
    sortie = []
    for l in lignes:
        if l.startswith("- "):
            sortie.append(l[2:].strip())
        elif l.startswith("  ") and sortie and l.strip():
            sortie[-1] += " " + l.strip()
    return sortie


def _organes(lignes):
    sortie = []
    for l in lignes:
        if not l.startswith("|"):
            continue
        c = [x.strip() for x in l.strip().strip("|").split("|", 1)]
        if len(c) == 2 and c[0] and not re.fullmatch(r"-+", c[0]) and c[0] != "Organe":
            sortie.append({"nom": c[0], "regle": c[1]})
    return sortie


def regles(racine):
    lignes = texte(racine).splitlines()
    organes = _organes(_section(lignes, "organes et leurs"))
    noms = {o["nom"] for o in organes}
    return {"organes": organes,
            "jour_nuit": _puces(_section(lignes, "Jour et nuit")),
            "clic": _puces(_section(lignes, "Commande par clic")),
            "par_type": {t: [n for n in ns if n in noms] for t, ns in PAR_TYPE.items()}}
