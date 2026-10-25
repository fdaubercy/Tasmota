"""Ecriture des listes de fichiers d'un env dans platformio_tasmota_cenv.ini (page « Fichiers Berry par env »).

Deux temps, comme la page : `prepare` calcule le diff sans rien ecrire, `enregistre` refait le calcul
et n'ecrit que si rien n'a change entre-temps (empreinte du cenv), si aucun build ne tourne, et si
toutes les listes partagees touchees ont ete acceptees. Regles (spec §2.5, §7.1, §7.5) :
  - un changement d'etat retire le fichier de TOUTES les listes ou il figure ;
  - une ligne ecrite hors de la section de l'env (liste partagee : [berry_commun], option d'une base)
    n'est retiree qu'avec l'accord de l'utilisateur (`partage_accepte`), apres avoir vu les envs touches ;
    une ligne ecrite dans un fichier de l'amont n'est jamais retiree ici ;
  - ajout : en fin de l'option propre de l'env ; option heritee -> `option = ${env:<ancetre>.option}`
    puis la ligne (l'heritage est garde) ; option absente partout -> `option = <chemin>` ;
  - les commentaires ne sont jamais touches ; seul celui de fin de ligne d'une ligne retiree part avec elle.
Le fichier est relu et reecrit ligne a ligne : fins de ligne et octets non UTF-8 gardes.
"""

import datetime
import difflib
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
import fichiers_berry_sauvegarde as fbs

CIBLES = {"exclu": fbe.EXCLUDE, "solidifie": fbe.SOLIDIFY}
ETATS = {"fs": ("fs", "exclu", "solidifie"), "carte": ("fs", "exclu", "solidifie"), "amont": ("fs", "absent"),
         "disparu": ("retire",)}            # ligne Berry vers un fichier disparu du disque
LARGEUR_CLE = 24        # `custom_files_exclude    = ` : alignement le plus courant du cenv


@dataclass
class Demande:
    chemin: str
    etat: str                       # "fs" | "exclu" | "solidifie" | "absent" (amont) | "retire" (disparu)
    raison: str = ""
    partage_accepte: bool = False


def empreinte(octets, demandes):
    """Cenv lu ET demandes : des demandes changees apres le diff ne sont pas ecrites sans nouveau diff."""
    vues = json.dumps(sorted((asdict(d) for d in demandes), key=lambda d: d["chemin"]), sort_keys=True,
                      ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(octets + b"\0" + vues).hexdigest()


def _lit(racine):
    octets = (Path(racine) / fbi.FICHIER_CENV).read_bytes()
    texte = octets.decode("utf-8", errors="surrogateescape")
    return octets, ("\r\n" if "\r\n" in texte else "\n"), fbi.decoupe(texte)


def _regions(lignes):
    """{section: (index de l'en-tete, index de fin exclu)} du cenv."""
    entetes = [(i, m.group(1).strip()) for i, l in enumerate(lignes) if l[:1] == "[" and (m := fbi.ENTETE.match(l))]
    return {nom: (i, entetes[k + 1][0] if k + 1 < len(entetes) else len(lignes)) for k, (i, nom) in enumerate(entetes)}


def _cible(groupe, etat):
    if groupe == "amont":
        return fbe.UPLOAD if etat == "fs" else None
    return CIBLES.get(etat)


def _indentation(lignes, opt):
    suite = [i for i, _, _ in opt.morceaux if i != opt.debut]
    if suite:
        l = lignes[suite[0]]
        return l[:len(l) - len(l.lstrip())]
    cle = lignes[opt.debut]
    m = re.match(r"[^=]*=\s*", cle)
    return " " * (len(m.group(0)) if opt.morceaux else cle.index("=") + 4)


def _ligne(indent, chemin, raison):
    if not raison:
        return indent + chemin
    propre = " ".join(raison.split())
    return f"{indent}{chemin}   ; {propre} ({datetime.date.today().isoformat()})"


def _calcule(racine, env, demandes):
    """(octets lus, fin de ligne, lignes avant, lignes apres, confirmations, refus, sections touchees, tiges)."""
    etat = fbe.etat_env(racine, env)                     # LookupError si l'env n'est pas modifiable
    fichiers = {f["chemin"]: f for f in etat["fichiers"]}
    ini = fbi.lit_sections(racine)
    octets, eol, lignes = _lit(racine)
    confirmations, refus, touchees, tiges = [], [], {"env:" + env}, []
    retraits, ajouts = set(), {}

    for d in demandes:
        chemin = fbi.normalise(d.chemin)
        f = fichiers.get(chemin)
        disparues = [x["provenance"] for x in etat["disparus"] if x["chemin"] == chemin and chemin.endswith(".be")]
        if f is None and disparues:                       # seule action : retirer la ou les lignes
            f = {"chemin": chemin, "groupe": "disparu", "figes": False, "provenances": disparues}
        if f is None:
            raise LookupError(f"fichier non propose pour {env} : {d.chemin!r}")
        if d.etat not in ETATS[f["groupe"]] or (f["figes"] and d.etat != "fs"):
            raise ValueError(f"etat {d.etat!r} impossible pour {f['chemin']}")
        cible = _cible(f["groupe"], d.etat)
        a_retirer = [p for p in f["provenances"] if p["option"] != cible]
        memes = [p for p in f["provenances"] if p["option"] == cible]
        if len(memes) > 1:                                # doublon : la ligne partagee (ou la 1re) reste
            garde = next((p for p in memes if p["partagee"] or p["amont"]), memes[0])
            a_retirer += [p for p in memes if p is not garde and not p["partagee"] and not p["amont"]]
        amont = [p for p in a_retirer if p["amont"]]
        if amont:
            refus += [f"{f['chemin']} : ligne de {p['section']} ecrite dans {p['fichier']} (liste de l'amont), "
                      "non modifiable ici" for p in amont]
            continue
        ajoute = bool(cible) and not any(p["option"] == cible for p in f["provenances"])
        if not d.partage_accepte:
            a_confirmer = {(p["section"], p["option_ecrite"]): p["envs"] for p in a_retirer if p["partagee"]}
            heritiers = etat["heritiers"][cible] if ajoute else [env]
            if set(heritiers) - {env}:                    # ajout dans une base : ses cartes en heritent
                a_confirmer.setdefault(("env:" + env, cible), heritiers)
            if a_confirmer:
                confirmations += [{"chemin": f["chemin"], "section": s, "option": o, "envs": envs}
                                  for (s, o), envs in a_confirmer.items()]
                continue
        retraits |= {p["ligne"] for p in a_retirer}
        touchees |= {p["section"] for p in a_retirer}
        if ajoute:
            ajouts.setdefault(cible, []).append((f["chemin"], d.raison))
        tiges.append(Path(f["chemin"]).stem)

    options = {}                                          # index de ligne -> Option du cenv
    for opts in ini.sections.values():
        for o in opts.values():
            if o.fichier == fbi.FICHIER_CENV:
                options.update({i: o for i, _, _ in o.morceaux})
    edits = []                                            # (index, ordre, action) ; ordre 1 = insertion apres
    for i in retraits:
        o = options[i]
        if i == o.debut:                                  # valeur sur la ligne `option =` : on la vide
            edits.append((i, 0, ("remplace", lignes[i][:lignes[i].index("=") + 1])))
        else:
            edits.append((i, 0, ("supprime", None)))
    section_env = ini.sections.get("env:" + env, {})
    for option, items in ajouts.items():
        propre = section_env.get(option)
        if propre is not None and propre.fichier == fbi.FICHIER_CENV:
            indent = _indentation(lignes, propre)
            edits.append((propre.fin, 1, ("insere", [_ligne(indent, c, r) for c, r in items])))
            continue
        indent = " " * len(f"{option:<{LARGEUR_CLE}}= ")
        cle = f"{option:<{LARGEUR_CLE}}= "
        ancetre = ini.definie_dans(env, option)
        if ancetre:
            nouvelles = [cle + "${" + ancetre + "." + option + "}"] + [_ligne(indent, c, r) for c, r in items]
        else:
            nouvelles = [_ligne(cle, items[0][0], items[0][1])] + [_ligne(indent, c, r) for c, r in items[1:]]
        fins = [o.fin for o in section_env.values() if o.fichier == fbi.FICHIER_CENV]
        edits.append((max(fins) if fins else _regions(lignes)["env:" + env][0], 1, ("insere", nouvelles)))

    apres = list(lignes)
    for i, _, (action, valeur) in sorted(edits, key=lambda e: (e[0], e[1]), reverse=True):
        if action == "insere":
            apres[i + 1:i + 1] = valeur
        elif action == "remplace":
            apres[i] = valeur
        else:
            del apres[i]
    return octets, eol, lignes, apres, confirmations, refus, touchees, tiges


def _cites(lignes, touchees, tiges):
    regions = _regions(lignes)
    res = []
    for section in sorted(touchees):
        debut, fin = regions.get(section, (0, 0))
        for i in range(debut, fin):
            l = lignes[i].strip()
            if l[:1] in (";", "#") and any(t in l for t in tiges):
                res.append({"ligne": i + 1, "texte": l})
    return res


def prepare(racine, env, demandes):
    """Diff du cenv pour ces demandes, sans rien ecrire (voir le docstring du module)."""
    octets, _, avant, apres, confirmations, refus, touchees, tiges = _calcule(racine, env, demandes)
    diff = "\n".join(difflib.unified_diff(avant, apres, fbi.FICHIER_CENV, fbi.FICHIER_CENV, lineterm="", n=2))
    return {"diff": diff, "empreinte": empreinte(octets, demandes), "confirmations": confirmations,
            "commentaires_cites": _cites(avant, touchees, tiges), "refus": refus}


def enregistre(racine, env, demandes, empreinte_lue, builds_en_cours):
    """Ecrit le cenv (copie horodatee avant, fichiers_berry_sauvegarde). RuntimeError (-> 409) : build en cours ou indetectable, cenv
    modifie depuis le diff, liste partagee non acceptee, ligne de l'amont."""
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("impossible de savoir si un build tourne : ecriture refusee")
    if builds:
        raise RuntimeError("un build est en cours (" + ", ".join(builds) + ") : ecriture refusee")
    octets, eol, avant, apres, confirmations, refus, _, _ = _calcule(racine, env, demandes)
    if empreinte(octets, demandes) != empreinte_lue:
        raise RuntimeError(f"{fbi.FICHIER_CENV} ou les modifications en attente ont change depuis le diff : "
                           "refaire « Voir le diff »")
    if confirmations or refus:
        raise RuntimeError("liste partagee non acceptee ou ligne de l'amont : rien n'est ecrit")
    diff = "\n".join(difflib.unified_diff(avant, apres, fbi.FICHIER_CENV, fbi.FICHIER_CENV, lineterm="", n=2))
    if apres == avant:
        return {"ecrit": False, "diff": ""}
    with fbs.Transaction(racine, "enregistrement") as tr:     # copie horodatee du cenv avant ecriture
        tr.ecrit(fbi.FICHIER_CENV, eol.join(apres).encode("utf-8", errors="surrogateescape"))
    return {"ecrit": True, "diff": diff, "sauvegarde": str(tr.dossier)}
