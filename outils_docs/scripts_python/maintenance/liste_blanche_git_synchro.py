"""Liste blanche des commandes git de l'assistant de synchro du fork, pour le banc test_synchro_fork_fusion.py.

`espionne(asst)` enrobe `synchro_fork_assistant._git`, par ou passent TOUTES les commandes git de l'analyse et de la
voie B (synchro_fork_fusion._git y ajoute seulement --literal-pathspecs) ; `hors_liste()` rend celles qui ne sont
pas autorisees. Une ecriture absente de la liste (forcage, autre branche, commit -a, chemin multiple...) = echec.
"""

LECTURES = ("rev-parse", "rev-list", "log", "diff", "status", "merge-tree", "merge-base")
ECRITURES = {("switch", "development"), ("merge", "--ff-only", "origin/development"),
             ("merge", "--no-ff", "--no-commit", "upstream/development"), ("merge", "--abort"),
             ("commit", "--no-edit"), ("push", "origin", "development"),
             ("fetch", "-q", "upstream", "development"), ("fetch", "-q", "origin")}
APPELS = []


def sans_option_globale(args):
    return tuple(args[1:]) if args[:1] == ("--literal-pathspecs",) else tuple(args)


def autorise(args):
    args = sans_option_globale(args)
    if not args or any(a.startswith("--output") for a in args):
        return False
    if args[0] in LECTURES or args[:2] == ("remote", "get-url") or args in ECRITURES:
        return True
    if len(args) == 4 and args[0] == "checkout" and args[1] in ("--ours", "--theirs") and args[2] == "--":
        return True
    if len(args) >= 5 and args[:2] == ("commit", "-m") and args[3] == "--":    # fichiers coches de l'etape arbre
        return True
    return (len(args) == 3 and args[:2] == ("add", "--")) or (len(args) == 4 and args[:3] == ("rm", "-q", "--"))


def espionne(asst):
    vrai = asst._git

    def espion(racine, *args, delai=None):
        APPELS.append(args)
        return vrai(racine, *args, delai=delai)
    asst._git = espion


def hors_liste():
    return sorted({" ".join(a) for a in APPELS if not autorise(a)})


def vues():
    return {sans_option_globale(a) for a in APPELS}
