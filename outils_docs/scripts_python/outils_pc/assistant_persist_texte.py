"""Ecart entre deux dicts JSON et edition d'un JSON DANS SON TEXTE (assistant persist, modification d'une carte).

`ecart(a, b)` donne des operations (chemin, "remplace"|"ajoute"|"retire", valeur) ; `applique(texte, ops)` ne
touche que les octets concernes : le reste du fichier (ordre, indentation, fins de ligne, cles absentes du
modele) ne bouge pas. Les chemins sont des tuples de cles d'objets ; une liste est une valeur atomique.
Aucun mot de passe n'apparait dans les messages d'erreur : seulement des chemins.
"""

import json

from fichiers_berry_coprocesseur import _membres


def ecart(a, b, chemin=()):
    """Operations qui font passer a (dict) a b (dict) : cles de b dans l'ordre, puis les retraits."""
    ops = []
    for cle, vb in b.items():
        c = chemin + (cle,)
        if cle not in a:
            ops.append((c, "ajoute", vb))
        elif isinstance(a[cle], dict) and isinstance(vb, dict):
            ops += ecart(a[cle], vb, c)
        elif a[cle] != vb:
            ops.append((c, "remplace", vb))
    ops += [(chemin + (cle,), "retire", None) for cle in a if cle not in b]
    return ops


def _nom(chemin):
    return ".".join(chemin)


def _prefixe(texte, i):
    """Blancs entre le debut de la ligne et l'indice i ('' si autre chose precede sur la ligne)."""
    p = texte[texte.rfind("\n", 0, i) + 1:i]
    return p if not p.strip() else ""


def _parent(texte, chemin):
    """Indice du '{' de l'objet qui contient chemin[-1] ; LookupError si un parent manque."""
    debut = texte.index("{")
    for k in chemin[:-1]:
        m = next((m for m in _membres(texte, debut) if m[0] == k), None)
        if m is None or texte[m[2]] != "{":
            raise LookupError(f"chemin absent du fichier : {_nom(chemin)}")
        debut = m[2]
    return debut


def _unite(texte):
    """Indentation d'un niveau, lue sur le premier membre de la racine (4 espaces par defaut)."""
    membres = _membres(texte, texte.index("{"))
    ind = _prefixe(texte, membres[0][1]) if membres else ""
    return "\t" if ind.startswith("\t") else (len(ind) or 4)


def _ecrit(valeur, ind, unite, eol):
    """Texte de la valeur ; les lignes apres la premiere sont decalees de ind."""
    s = json.dumps(valeur, indent=unite, ensure_ascii=False)
    return s.replace("\n", eol + ind)


def _un(texte, chemin, op, valeur):
    eol = "\r\n" if "\r\n" in texte else "\n"
    debut = _parent(texte, chemin)
    membres = _membres(texte, debut)
    cle = chemin[-1]
    i = next((i for i, m in enumerate(membres) if m[0] == cle), None)
    if op == "retire":
        if i is None:
            return texte
        if len(membres) == 1:
            return texte[:debut + 1] + texte[texte.index("}", membres[0][3]):]
        if i < len(membres) - 1:
            return texte[:membres[i][1]] + texte[membres[i + 1][1]:]
        return texte[:membres[i - 1][3]] + texte[membres[i][3]:]
    unite = _unite(texte)
    if i is not None:                                     # remplace (ou ajoute d'une cle deja la)
        _, k, v, fin = membres[i]
        return texte[:v] + _ecrit(valeur, _prefixe(texte, k), unite, eol) + texte[fin:]
    pas = unite if isinstance(unite, str) else " " * unite
    nom = json.dumps(cle, ensure_ascii=False)
    if membres:
        ind = _prefixe(texte, membres[-1][1])
        fin = membres[-1][3]
        return texte[:fin] + f",{eol}{ind}{nom}: {_ecrit(valeur, ind, unite, eol)}" + texte[fin:]
    ligne = texte[texte.rfind("\n", 0, debut) + 1:debut]  # objet vide : un membre sur sa ligne
    base = ligne[:len(ligne) - len(ligne.lstrip(" \t"))]
    ind = base + pas
    fermant = texte.index("}", debut)
    return (texte[:debut + 1] + f"{eol}{ind}{nom}: {_ecrit(valeur, ind, unite, eol)}{eol}{base}"
            + texte[fermant:])


def applique(texte, operations):
    """Texte apres les operations ; LookupError (chemin seul) si un objet parent manque."""
    for chemin, op, valeur in operations:
        texte = _un(texte, chemin, op, valeur)
    return texte


def ecart_applicable(texte, operations):
    """Chemins (a.b.c) des operations dont l'objet parent n'existe pas dans le texte."""
    refus = []
    for chemin, _, _ in operations:
        try:
            _parent(texte, chemin)
        except LookupError:
            refus.append(_nom(chemin))
    return refus
