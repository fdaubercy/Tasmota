"""Applique l'ecart ligne a ligne de deux generations A -> B a la vraie section d'un fichier (A10, spec §10.2).

Ne touche aucun fichier : travaille sur des listes de lignes. Les lignes de `reel` hors des blocs appliques
ressortent identiques (memes objets) ; la comparaison `rstrip()` ne sert qu'a LOCALISER les lignes de A.
"""

import difflib


def _positions(reel, motif):
    """Index de debut des occurrences contigues de `motif` (rstrip) dans `reel`."""
    cle = [l.rstrip() for l in reel]
    m = [l.rstrip() for l in motif]
    return [p for p in range(len(cle) - len(m) + 1) if cle[p:p + len(m)] == m]


def _zone(reel, a, tag, i1, i2):
    """(debut, fin) dans reel du bloc, ou un message de refus."""
    if tag != "insert":
        trouve = _positions(reel, a[i1:i2])
        if len(trouve) != 1:
            return f"{'absentes' if not trouve else 'presentes %d fois' % len(trouve)} dans le fichier"
        return trouve[0], trouve[0] + i2 - i1
    if not a:
        return len(reel), len(reel)
    # repli par contexte : precedente seule, puis la paire precedente+suivante, puis suivante seule
    if i1 and not _positions(reel, a[i1 - 1:i1]):
        return "ancre absente dans le fichier"      # precedente retouchee : jamais de repli (spec §10.2)
    essais = [(a[i1 - 1:i1], 1)] * (i1 > 0) +[(a[i1 - 1:i1 + 1], 1)] * (0 < i1 < len(a)) + [(a[i1:i1 + 1], 0)] * (i1 < len(a))
    for motif, decalage in essais:
        trouve = _positions(reel, motif)
        if len(trouve) == 1:
            return (trouve[0] + decalage,) * 2
    return "ancre absente ou ambigue dans le fichier"


def _chevauche(z, y):
    (s1, e1), (s2, e2) = z, y
    if s1 == e1 and s2 == e2:
        return s1 == s2
    if s1 == e1:
        return s2 < s1 < e2
    if s2 == e2:
        return s1 < s2 < e1
    return max(s1, s2) < min(e1, e2)


def applique_lignes(reel, a, b):
    """(nouvelles lignes, blocs non appliques en texte). Un refus doit faire refuser toute la modification."""
    retenus, refus = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal":
            continue
        cite = "".join(a[i1:i2] if i2 > i1 else a[max(i1 - 1, 0):i1 + 1]).rstrip()
        zone = _zone(reel, a, tag, i1, i2)
        if isinstance(zone, str):
            refus.append(f"{tag} : lignes {zone} :\n{cite}")
        elif any(_chevauche(zone, z) for z, _ in retenus):
            refus.append(f"{tag} : zone deja visee par un autre bloc :\n{cite}")
        else:
            retenus.append((zone, b[j1:j2]))
    nouv = list(reel)
    for (debut, fin), lignes in sorted(retenus, key=lambda r: r[0], reverse=True):
        nouv[debut:fin] = lignes
    return nouv, refus
