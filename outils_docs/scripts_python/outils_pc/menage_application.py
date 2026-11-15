"""Application d'un lot de propositions de menage : DEPLACEMENTS (`git mv`) et SUPPRESSIONS (`git rm`) sans aucun renvoi (plan tasks/plans/menage-appliquer.md).

Cette etape (A1) ne fait que l'APERCU : aucun fichier n'est touche. Chaque proposition choisie est recontrolee par git a l'instant de l'apercu
(l'etat a pu changer depuis l'audit), jugee eligible ou refusee avec son motif, puis SIMULEE par git lui-meme (`git rm -n`, `git mv -n` : la
sortie reelle de git est montree, et un refus de git retire la ligne du lot). Jamais `-f` ni `-r`, jamais d'archivage, jamais un dossier d'un
coup, jamais de shell. Decision du 2026-11-15 : `git rm` autorise, mais dry-run obligatoire avant l'application.

    previsualise(ids, propositions, racine) -> {"eligibles": [...], "refuses": [...], "empreinte": str, "head": str}
        eligibles : {id, action, chemin, vers, commande, cree_dossier, dry_run: {ok, sortie}} ; refuses : {id, chemin, motif}
        empreinte : condense du lot (actions, chemins, HEAD), a representer a l'application pour prouver qu'elle suit l'apercu affiche.

Banc : test_menage_application.py.
"""
import hashlib
import json
import os
import subprocess
from pathlib import PurePosixPath

import menage_rapport
import menage_verification

MAX_LOT = 50
ACTIONS = ("deplacer", "supprimer")
PROTEGES = (".git", ".github", ".claude", ".vscode")   # jamais une destination ni une source : configuration de git, de l'IDE et de Claude
DELAI_GIT = 30


def motif_refus(p, verif, racine=None):
    """Premier motif qui interdit l'action, ou None. `p` est la proposition, `verif` sa contre-verification fraiche."""
    action = p.get("action")
    if action not in ACTIONS:
        return "seuls les deplacements et les suppressions sont appliques (archiver et garder restent manuels)"
    if p.get("en_cours"):
        return "travail en cours : a ne pas toucher"
    vers = p.get("vers")
    if action == "deplacer" and not vers:
        return "aucune destination exacte proposee"
    cibles = [p.get("chemin")] + ([vers] if action == "deplacer" else [])
    for chemin in cibles:
        if isinstance(chemin, str) and chemin.replace("\\", "/").split("/")[0].lower() in PROTEGES:
            return "dossier protege (.git, .github, .claude, .vscode)"
    if racine is not None and any(menage_rapport.chemin_sur(c, racine) is None for c in cibles):
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
    if action == "deplacer" and verif.get("destination_existe"):
        return "la destination existe deja"
    return None


def _est_dossier(racine, chemin):
    return os.path.isdir(os.path.join(str(racine), chemin))


def _cle(chemin):
    """Forme comparable : Windows ignore la casse et `a/./b` vaut `a/b`."""
    return os.path.normcase(os.path.normpath(chemin))


def argv_git(action, chemin, vers, simulation):
    """La commande git, en liste (jamais une chaine decoupee) ; `--` devant les chemins ; -n = simulation seulement."""
    base = ["git", "--no-optional-locks"]
    if action == "supprimer":
        return base + ["rm"] + (["-n"] if simulation else []) + ["--", chemin]
    return base + ["mv"] + (["-n"] if simulation else []) + ["--", chemin, vers]


def _dry_run(racine, action, chemin, vers):
    """Simulation par git (`-n`) : (ok, sortie). Un delai ou une erreur systeme donnent ok=False : jamais un faux « ca passera »."""
    env = dict(os.environ, GIT_LITERAL_PATHSPECS="1")
    try:
        r = subprocess.run(argv_git(action, chemin, vers, True), cwd=str(racine), capture_output=True, timeout=DELAI_GIT, env=env,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"git inutilisable : {type(e).__name__}"
    texte = (r.stdout + r.stderr).decode("utf-8", "replace").strip()
    return r.returncode == 0, texte[:300]


def _head(racine):
    try:
        return menage_verification._git(str(racine), ["rev-parse", "HEAD"], DELAI_GIT).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def previsualise(ids, propositions, racine):
    """Apercu du lot `ids` parmi `propositions` (celles du rapport en cours). Aucune ecriture : git n'est lance qu'avec -n."""
    if not isinstance(ids, list) or not ids or len(ids) > MAX_LOT or not all(isinstance(i, str) for i in ids):
        raise ValueError(f"ids : liste de 1 a {MAX_LOT} identifiants attendue")
    par_id = {p["id"]: p for p in propositions}
    refuses, vus, choisies = [], set(), []
    for ident in ids:
        if ident in vus:
            continue                              # un identifiant coche deux fois ne s'applique qu'une fois
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
            motif = "un dossier ne s'applique pas d'un coup"
        if motif is None and p["action"] == "deplacer" and _cle(p["vers"]) == _cle(p["chemin"]):
            motif = "destination identique au chemin"
        if motif is not None:
            refuses.append({"id": p["id"], "chemin": p["chemin"], "motif": motif})
        else:
            candidats.append(p)
    eligibles, destinations, sources = [], set(), set()
    for p in candidats:
        motif = None
        if _cle(p["chemin"]) in sources:
            motif = "meme fichier qu'une autre proposition du lot"
        elif p["action"] == "deplacer" and _cle(p["vers"]) in destinations:
            motif = "meme destination qu'une autre proposition du lot"
        dossier, absent = None, False
        if motif is None and p["action"] == "deplacer":
            dossier = str(PurePosixPath(p["vers"]).parent)
            absent = dossier != "." and not os.path.isdir(os.path.join(str(racine), dossier))
            if absent and os.path.lexists(os.path.join(str(racine), dossier)):
                motif = "le dossier de destination est un fichier"
        if motif is None:
            ok, sortie = _dry_run(racine, p["action"], p["chemin"], p.get("vers"))
            if not ok:
                motif = "git refuse (simulation -n) : " + sortie
        if motif is not None:
            refuses.append({"id": p["id"], "chemin": p["chemin"], "motif": motif})
            continue
        sources.add(_cle(p["chemin"]))
        if p["action"] == "deplacer":
            destinations.add(_cle(p["vers"]))
        eligibles.append({"id": p["id"], "action": p["action"], "chemin": p["chemin"], "vers": p.get("vers") if p["action"] == "deplacer" else None,
                          "commande": "git " + " ".join(argv_git(p["action"], p["chemin"], p.get("vers"), False)[2:]),
                          "cree_dossier": dossier if absent else None, "dry_run": {"ok": ok, "sortie": sortie}})
    head = _head(racine)
    condense = json.dumps([(e["id"], e["action"], e["chemin"], e["vers"]) for e in eligibles] + [head], ensure_ascii=False, sort_keys=True)
    return {"eligibles": eligibles, "refuses": refuses, "head": head, "empreinte": hashlib.sha256(condense.encode("utf-8")).hexdigest()[:16]}
