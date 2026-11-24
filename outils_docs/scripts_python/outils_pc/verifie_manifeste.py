r"""Controle du manifeste des binomes : les `blocs` de modele_persist.json contre les listes `[berry_commun]` du cenv.

UTILISATION
-----------
  python outils_docs/scripts_python/outils_pc/verifie_manifeste.py --verifier [--racine DOSSIER]

Lecture seule : rien n'est ecrit (ni cenv, ni modele). Code de sortie : 0 = accord, 1 = au moins un ecart,
2 = lecture impossible (modele ou cenv absent, illisible ou incomplet, reference circulaire).

CE QUI EST COMPARE (plan tasks/plans/binomes-berry.md, A3)
----------------------------------------------------------
Un bloc porte `fichiers` (data/fs/...be) et `pages` (data/sd/html|css|js/...), en chemins litteraux ou en references
`${berry_commun.x}`. Chaque liste de [berry_commun] est developpee (references `${...}` suivies) puis :
  1. liste inconnue : aucun de ses fichiers n'est dans un bloc (hors la liste `socle`, qui reunit aussi des fichiers
     sans bloc : configGlobal, demarrage...) ;
  2. fichier de liste absent du bloc : la liste est portee par un ou plusieurs blocs, mais l'un de ses fichiers
     n'est dans aucun bloc (le message nomme les blocs correspondants, ceux qui portent les autres fichiers) ;
  3. bloc `detection: {"socle": true}` : chacun de ses fichiers doit etre dans la liste `socle` ;
  4. fichier d'un bloc (ou d'une liste) absent du disque ;
  5. reference `${berry_commun.x}` d'un bloc (fichiers, pages, solidify, exclude_si_inactif) vers une liste inconnue.
Un fichier qui n'est dans aucune liste (ex. loRaWanFonctions.be, cite en clair par les envs) n'est pas un ecart.
"""
import json
import sys
from pathlib import Path

import fichiers_berry_ini as fbi

RACINE = Path(__file__).resolve().parents[3]
MODELE = "outils_docs/schemas/modele_persist.json"
SECTION = "berry_commun"
SOCLE = "socle"


def lit_manifeste(racine):
    """[blocs] du modele ; ValueError (lecture impossible) si le fichier manque, est illisible ou sans liste `blocs`."""
    try:
        donnees = json.loads((Path(racine) / MODELE).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"{MODELE} illisible : {exc}") from exc
    blocs = donnees.get("blocs") if isinstance(donnees, dict) else None
    if not isinstance(blocs, list) or not all(isinstance(b, dict) and b.get("id") for b in blocs):
        raise ValueError(f"{MODELE} : liste `blocs` attendue (objets avec un `id`)")
    return blocs


def lit_listes(racine):
    """{liste: [fichiers]} des options de [berry_commun], references developpees ; ValueError si illisible."""
    ini = fbi.lit_sections(racine)
    section = ini.sections.get(SECTION)
    if not section:
        raise ValueError(f"[{SECTION}] absente du cenv ({fbi.FICHIER_CENV})")
    return {nom: [e.chemin for e in fbi._developpe(ini, SECTION, nom, [], set())] for nom in section}


def _developpe_bloc(valeurs, listes):
    """(fichiers, references inconnues) : un `${berry_commun.x}` devient les fichiers de la liste x."""
    fichiers, inconnues = [], []
    for v in valeurs:
        ref = fbi.REFERENCE.match(v)
        if not ref:
            fichiers.append(fbi.normalise(v))
        elif ref.group(1) == SECTION and ref.group(2) in listes:
            fichiers += listes[ref.group(2)]
        else:
            inconnues.append(v)
    return fichiers, inconnues


def fichiers_blocs(blocs, listes):
    """({bloc: [fichiers + pages]}, [ecarts de reference inconnue])."""
    res, ecarts = {}, []
    for b in blocs:
        fich, inc = _developpe_bloc(list(b.get("fichiers", [])) + list(b.get("pages", [])), listes)
        res[b["id"]] = fich
        ecarts += [f"bloc {b['id']} : reference {r} vers une liste inconnue" for r in inc]
        for cle in ("solidify", "exclude_si_inactif"):
            refs = [v for v in b.get(cle, []) if fbi.REFERENCE.match(v)]
            ecarts += [f"bloc {b['id']} : {cle} : reference {r} vers une liste inconnue"
                       for r in _developpe_bloc(refs, listes)[1]]
    return res, ecarts


def _listes_inconnues_ou_incompletes(listes, par_bloc):
    possede = {}
    for bloc, fichiers in par_bloc.items():
        for f in fichiers:
            possede.setdefault(f, []).append(bloc)
    ecarts = []
    for nom, fichiers in listes.items():
        if nom == SOCLE or not fichiers:
            continue
        portes = [f for f in fichiers if f in possede]
        if not portes:
            ecarts.append(f"liste [{SECTION}].{nom} inconnue du manifeste (aucun de ses {len(fichiers)} fichiers n'est dans un bloc)")
            continue
        blocs = sorted({b for f in portes for b in possede[f]})
        ecarts += [f"[{SECTION}].{nom} : {f} absent du bloc correspondant ({', '.join(blocs)})"
                   for f in fichiers if f not in possede]
    return ecarts


def _socle(blocs, listes, par_bloc):
    socle = set(listes.get(SOCLE, []))
    return [f"bloc {b['id']} : {f} absent de [{SECTION}].{SOCLE}"
            for b in blocs if (b.get("detection") or {}).get("socle")
            for f in par_bloc[b["id"]] if f not in socle]


def _disque(racine, blocs, listes, par_bloc):
    racine = Path(racine)
    ecarts = [f"bloc {b['id']} : {f} absent du disque" for b in blocs for f in dict.fromkeys(par_bloc[b["id"]])
              if not (racine / f).is_file()]
    return ecarts + [f"[{SECTION}].{nom} : {f} absent du disque" for nom, fichiers in listes.items()
                     for f in fichiers if not (racine / f).is_file()]


def ecarts(racine):
    """Liste des ecarts (messages) ; vide = accord. ValueError si le modele ou le cenv est illisible."""
    blocs, listes = lit_manifeste(racine), lit_listes(racine)
    par_bloc, res = fichiers_blocs(blocs, listes)
    return (res + _listes_inconnues_ou_incompletes(listes, par_bloc) + _socle(blocs, listes, par_bloc)
            + _disque(racine, blocs, listes, par_bloc))


def main(argv, racine=RACINE):
    args = list(argv)
    if "--racine" in args:
        i = args.index("--racine")
        if i + 1 >= len(args):
            print("ERREUR : --racine demande un dossier", file=sys.stderr)
            return 2
        racine = Path(args[i + 1])
        del args[i:i + 2]
    if args != ["--verifier"]:
        print(__doc__)
        return 2
    try:
        liste = ecarts(racine)
    except ValueError as exc:
        print(f"LECTURE IMPOSSIBLE : {exc}", file=sys.stderr)
        return 2
    for ligne in liste:
        print("ECART  " + ligne)
    print(f"{len(liste)} ecart(s)" if liste else "ACCORD : le manifeste et les listes [berry_commun] concordent")
    return 1 if liste else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
