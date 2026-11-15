"""Application d'un lot de propositions de menage : version 1 = DEPLACEMENTS sans aucun renvoi, par `git mv` (plan tasks/plans/menage-appliquer.md).

Cette etape (A1) ne fait que l'APERCU : aucun fichier n'est touche. Chaque proposition choisie est recontrolee par git a l'instant de l'apercu
(l'etat a pu changer depuis l'audit), puis jugee eligible ou refusee avec son motif. Rien d'autre qu'un `git mv` n'est jamais prevu : pas de
`git rm` (decision du 2026-11-15), pas d'archivage, pas de dossier d'un coup, pas de shell.

    previsualise(ids, propositions, racine) -> {"eligibles": [...], "refuses": [...], "empreinte": str}
        eligibles : {id, chemin, vers, commande, cree_dossier} ; refuses : {id, chemin, motif}
        empreinte : condense des deplacements eligibles, a representer a l'application pour prouver qu'elle suit l'apercu affiche.

Banc : test_menage_application.py.
"""
import hashlib
import json
import os
from pathlib import PurePosixPath

import menage_rapport
import menage_verification

MAX_LOT = 50
PROTEGES = (".git", ".github", ".claude", ".vscode")   # jamais une destination ni une source : configuration de git, de l'IDE et de Claude


def motif_refus(p, verif, racine=None):
    """Premier motif qui interdit le deplacement, ou None. `p` est la proposition, `verif` sa contre-verification fraiche."""
    if p.get("action") != "deplacer":
        return "seuls les deplacements sont appliques (les suppressions restent manuelles)"
    if p.get("en_cours"):
        return "travail en cours : a ne pas toucher"
    vers = p.get("vers")
    if not vers:
        return "aucune destination exacte proposee"
    for chemin in (p.get("chemin"), vers):
        if isinstance(chemin, str) and chemin.replace("\\", "/").split("/")[0].lower() in PROTEGES:
            return "dossier protege (.git, .github, .claude, .vscode)"
    if racine is not None and (menage_rapport.chemin_sur(p.get("chemin"), racine) is None or menage_rapport.chemin_sur(vers, racine) is None):
        return "chemin refuse : absolu, avec .. ou hors du depot"
    if not verif.get("disponible"):
        return "verification par git indisponible : " + str(verif.get("erreur") or "raison inconnue")
    if verif.get("perimee"):
        return "le chemin n'existe plus"
    if not verif.get("suivi"):
        return "fichier non suivi par git"
    if verif.get("modifie"):
        return "fichier modifie : en cours de travail"
    if verif.get("n_code") or verif.get("n_docs"):
        return f"cite par {verif.get('n_code', 0)} fichier(s) de code ou de config et {verif.get('n_docs', 0)} document(s)"
    if verif.get("destination_existe"):
        return "la destination existe deja"
    return None


def _est_dossier(racine, chemin):
    return os.path.isdir(os.path.join(str(racine), chemin))


def _cle(chemin):
    """Forme comparable : Windows ignore la casse et `a/./b` vaut `a/b`."""
    return os.path.normcase(os.path.normpath(chemin))


def previsualise(ids, propositions, racine):
    """Apercu du lot `ids` parmi `propositions` (celles du rapport en cours). Lecture seule."""
    if not isinstance(ids, list) or not ids or len(ids) > MAX_LOT or not all(isinstance(i, str) for i in ids):
        raise ValueError(f"ids : liste de 1 a {MAX_LOT} identifiants attendue")
    par_id = {p["id"]: p for p in propositions}
    refuses, vus, choisies = [], set(), []
    for ident in ids:
        if ident in vus:
            continue                              # un identifiant coche deux fois ne se deplace qu'une fois
        vus.add(ident)
        if ident not in par_id:
            refuses.append({"id": ident, "chemin": None, "motif": "proposition inconnue dans le rapport en cours"})
        else:
            choisies.append(dict(par_id[ident]))
    for p in choisies:                            # on agit sur la forme NORMALISEE, celle qui a ete controlee, jamais sur la brute
        p["chemin"] = menage_rapport.chemin_sur(p.get("chemin"), racine) or p.get("chemin")
        p["vers"] = (menage_rapport.chemin_sur(p.get("vers"), racine) or p.get("vers")) if p.get("vers") else p.get("vers")
    fraiches = menage_verification.enrichit(choisies, racine) if choisies else []
    candidats = []
    for p in fraiches:
        motif = motif_refus(p, p.get("verif") or {}, racine)
        if motif is None and _est_dossier(racine, p["chemin"]):
            motif = "un dossier ne se deplace pas d'un coup"
        if motif is None and _cle(p["vers"]) == _cle(p["chemin"]):
            motif = "destination identique au chemin"
        if motif is not None:
            refuses.append({"id": p["id"], "chemin": p["chemin"], "motif": motif})
        else:
            candidats.append(p)
    eligibles, destinations = [], set()
    for p in candidats:
        cle = _cle(p["vers"])
        motif = None
        if cle in destinations:
            motif = "meme destination qu'une autre proposition du lot"
        if motif is not None:
            refuses.append({"id": p["id"], "chemin": p["chemin"], "motif": motif})
            continue
        destinations.add(cle)
        dossier = str(PurePosixPath(p["vers"]).parent)
        absent = dossier != "." and not os.path.isdir(os.path.join(str(racine), dossier))
        if absent and os.path.lexists(os.path.join(str(racine), dossier)):
            refuses.append({"id": p["id"], "chemin": p["chemin"], "motif": "le dossier de destination est un fichier"})
            continue
        eligibles.append({"id": p["id"], "chemin": p["chemin"], "vers": p["vers"],
                          "commande": f"git mv -- {p['chemin']} {p['vers']}", "cree_dossier": dossier if absent else None})
    condense = json.dumps([(e["id"], e["chemin"], e["vers"]) for e in eligibles], ensure_ascii=False, sort_keys=True)
    return {"eligibles": eligibles, "refuses": refuses, "empreinte": hashlib.sha256(condense.encode("utf-8")).hexdigest()[:16]}
