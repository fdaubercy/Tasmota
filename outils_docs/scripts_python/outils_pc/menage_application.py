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
import re
import subprocess
import sys
import threading
import time
from pathlib import Path, PurePosixPath

import menage_rapport
import menage_verification

MAX_LOT = 50
ACTIONS = ("deplacer", "supprimer")
PROTEGES = (".git", ".claude", ".vscode")   # jamais une destination ni une source : configuration de git (tout « .git* » aussi), de l'IDE et de Claude
DELAI_GIT = 30


def _protege(chemin, racine=None):
    """Vrai si le chemin vise un dossier protege, y compris par un nom qui y mene sans lui ressembler : nom court Windows (`CLAUDE~1`),
    point ou espace en fin de segment (`.claude.`), ou chemin resolu qui retombe dans un dossier protege."""
    segments = [x for x in chemin.replace("\\", "/").split("/") if x]
    for x in segments:
        if x != x.rstrip(" .") or re.search(r"~\d", x):
            return True
    premier = segments[0].lower() if segments else ""
    if premier in PROTEGES or premier.startswith(".git"):
        return True
    if racine is not None:
        try:
            resolu = Path(str(racine), chemin).resolve().relative_to(Path(str(racine)).resolve()).parts
        except (OSError, ValueError):
            return True                              # qui sort du depot ou ne se resout pas : jamais applique
        if resolu and (resolu[0].lower() in PROTEGES or resolu[0].lower().startswith(".git")):
            return True
    return False


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
        if isinstance(chemin, str) and _protege(chemin, racine):
            return "dossier protege (.git*, .claude, .vscode) ou nom de segment ambigu (nom court 8.3, point ou espace final)"
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


def _imbriques(a, b):
    """Vrai si l'un des deux chemins normalises est un ancetre de l'autre."""
    return a.startswith(b + os.sep) or b.startswith(a + os.sep)


def _cle(chemin):
    """Forme comparable : Windows ignore la casse et `a/./b` vaut `a/b`."""
    return os.path.normcase(os.path.normpath(chemin))


def argv_git(action, chemin, vers, simulation):
    """La commande git, en liste (jamais une chaine decoupee) ; `--` devant les chemins ; -n = simulation seulement."""
    base = ["git", "--no-optional-locks"]
    if action == "supprimer":
        return base + ["rm"] + (["-n"] if simulation else []) + ["--", chemin]
    return base + ["mv"] + (["-n"] if simulation else []) + ["--", chemin, vers]


def argv_annule(action, chemin, vers):
    """La commande qui DEFAIT une ligne appliquee : un `git rm` se restaure (index et arbre), un `git mv` se refait a l'envers."""
    base = ["git", "--no-optional-locks"]
    if action == "supprimer":
        return base + ["restore", "--staged", "--worktree", "--", chemin]
    return base + ["mv", "--", vers, chemin]


def _lance(racine, argv):
    """Lance git (liste d'arguments, jamais de shell) : (ok, sortie). Un delai ou une erreur systeme donnent ok=False : jamais un faux « ca passera »."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}     # GIT_DIR, GIT_WORK_TREE... : git agirait ailleurs
    env["GIT_LITERAL_PATHSPECS"] = "1"
    try:
        r = subprocess.run(argv, cwd=str(racine), capture_output=True, timeout=DELAI_GIT, env=env,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"git inutilisable : {type(e).__name__}"
    texte = (r.stdout + r.stderr).decode("utf-8", "replace").strip()
    return r.returncode == 0, texte[:300]


def _lance_git(racine, action, chemin, vers, simulation):
    return _lance(racine, argv_git(action, chemin, vers, simulation))


def _dry_run(racine, action, chemin, vers):
    """Simulation par git (`-n`)."""
    return _lance_git(racine, action, chemin, vers, True)


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
        elif p["action"] == "deplacer" and any(_imbriques(_cle(p["vers"]), d) for d in destinations):
            motif = "destination imbriquee dans (ou contenant) celle d'une autre proposition du lot : git mv rangerait DEDANS"
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


_VERROU = threading.Lock()
SCRIPT_RENVOIS = os.path.join("outils_docs", "scripts_python", "maintenance", "verifie_references_docs.py")


def verifie_renvois(racine):
    """Lance le controle des renvois des documents apres une application : {code, sortie}. Lecture seule ; ne corrige jamais rien."""
    try:
        r = subprocess.run([sys.executable, os.path.join(str(racine), SCRIPT_RENVOIS)], cwd=str(racine), capture_output=True, timeout=120,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError) as e:
        return {"code": None, "sortie": f"controle des renvois impossible : {type(e).__name__}"}
    return {"code": r.returncode, "sortie": (r.stdout + r.stderr).decode("utf-8", "replace").strip()[-1500:]}


def _journalise(journal, ligne):
    if not journal:
        return
    try:
        os.makedirs(os.path.dirname(str(journal)), exist_ok=True)
        with open(journal, "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(ligne, t=time.strftime("%Y-%m-%d %H:%M:%S")), ensure_ascii=False) + "\n")
    except OSError:
        pass                                      # un journal illisible ne doit jamais empecher ni masquer l'application


def _statut(racine, *chemins):
    """Premieres colonnes de `git status --porcelain` pour ces chemins (« D  », « R  »...), « » si rien. Un renommage ne se reconnait que si les DEUX
    chemins sont donnes (la destination seule apparait comme un ajout)."""
    try:
        s = menage_verification._git(str(racine), ["status", "--porcelain", "--"] + list(chemins), DELAI_GIT)
    except (OSError, subprocess.SubprocessError):
        return None
    return s[:3] if s.strip() else ""


def motif_non_annulable(fait, racine):
    """Pourquoi cette ligne ne peut PAS etre defaite sans risque (l'utilisateur a touche au fichier depuis), ou None."""
    absent = lambda c: not os.path.lexists(os.path.join(str(racine), c))
    if _protege(fait["chemin"], racine) or (fait["action"] == "deplacer" and _protege(fait["vers"] or "", racine)):
        return "chemin protege"
    if fait["action"] == "supprimer":
        if not absent(fait["chemin"]):
            return "le fichier existe de nouveau : il a ete recree depuis"
        if _statut(racine, fait["chemin"]) != "D  ":
            return "la suppression n'est plus l'etat indexe tel qu'elle a ete faite"
        return None
    if absent(fait["vers"]):
        return "le fichier deplace n'est plus a sa nouvelle place"
    if not absent(fait["chemin"]):
        return "un fichier occupe de nouveau l'ancienne place"
    if _statut(racine, fait["chemin"], fait["vers"]) != "R  ":
        return "le deplacement n'est plus l'etat indexe tel qu'il a ete fait (fichier modifie depuis ?)"
    return None


def annule(faits, head, racine, builds_en_cours, journal=None):
    """Defait, DANS L'ORDRE INVERSE, les lignes d'une application de ce processus : `git restore --staged --worktree` pour un rm, `git mv` a l'envers
    pour un mv. Refuse si un commit a eu lieu depuis (HEAD different : `git revert` alors) ou si l'utilisateur a touche au fichier ; s'arrete a la
    premiere erreur. Rend {retablis, echec, restants} ; leve RuntimeError (build, application en cours, HEAD change)."""
    if not _VERROU.acquire(blocking=False):
        raise RuntimeError("une application ou un retour en arriere est deja en cours")
    try:
        enc = builds_en_cours()
        if enc:
            raise RuntimeError("un build est en cours (" + ", ".join(str(e) for e in list(enc)[:3]) + ") : retour en arriere refuse")
        if not head or _head(racine) != head:
            raise RuntimeError("un commit a eu lieu depuis l'application : le retour en arriere automatique est refuse (utilisez git revert)")
        retablis, echec = [], None
        for fait in reversed(faits):
            motif = motif_non_annulable(fait, racine)
            ok, sortie = (False, motif) if motif else (None, "")
            if motif is None:
                _journalise(journal, {"id": fait["id"], "retour": True, "intention": True, "action": fait["action"], "chemin": fait["chemin"], "vers": fait["vers"]})
                try:
                    if fait["action"] == "deplacer":
                        os.makedirs(os.path.dirname(os.path.join(str(racine), fait["chemin"])), exist_ok=True)     # l'ancien dossier a pu disparaitre
                    ok, sortie = _lance(racine, argv_annule(fait["action"], fait["chemin"], fait["vers"]))
                except OSError as erreur:
                    ok, sortie = False, f"{type(erreur).__name__} : {erreur}"[:300]
            _journalise(journal, {"id": fait["id"], "retour": True, "ok": ok, "sortie": sortie, "chemin": fait["chemin"]})
            if not ok:
                echec = {"id": fait["id"], "chemin": fait["chemin"], "motif": sortie}
                break
            for dossier in fait.get("dossiers_crees") or []:           # dossiers que l'application avait crees pour ce deplacement : retires s'ils sont vides
                try:
                    os.rmdir(os.path.join(str(racine), dossier))
                except OSError:
                    break
            retablis.append({"id": fait["id"], "action": fait["action"], "chemin": fait["chemin"]})
        faits_restants = [f["id"] for f in faits if f["id"] not in {r["id"] for r in retablis}]
        return {"retablis": retablis, "echec": echec, "restants": faits_restants}
    finally:
        _VERROU.release()


def applique(ids, empreinte, head, propositions, racine, builds_en_cours, verifie_refs=verifie_renvois, journal=None, a_blanc=False):
    """Applique le lot `ids` : l'apercu est REFAIT a cet instant et doit avoir la meme empreinte et le meme HEAD que celui montre a l'utilisateur.
    git est lance un fichier a la fois (argv_git sans -n), on s'arrete a la premiere erreur. Rien n'est jamais commite ni force.
    `a_blanc=True` : meme parcours, memes controles, mais chaque git tourne avec -n et aucun dossier n'est cree : rien n'est modifie, le journal le note.
    Rend {a_blanc, faits, echec, restants, renvois} ; leve RuntimeError (build, lot deja en cours, apercu perime) ou ValueError (saisie)."""
    if not isinstance(empreinte, str) or not empreinte or not isinstance(head, str) or not head:
        raise ValueError("empreinte et head de l'apercu attendus")
    if not _VERROU.acquire(blocking=False):
        raise RuntimeError("une application est deja en cours")
    try:
        enc = builds_en_cours()
        if enc:
            raise RuntimeError("un build est en cours (" + ", ".join(str(e) for e in list(enc)[:3]) + ") : application refusee")
        r = previsualise(ids, propositions, racine)
        if r["head"] != head or r["empreinte"] != empreinte:
            raise RuntimeError("l'apercu n'est plus a jour (le depot ou le lot a change) : refaire l'apercu, rien n'a ete applique")
        if not r["eligibles"]:
            raise ValueError("aucune ligne eligible dans ce lot")
        faits, echec = [], None
        for e in r["eligibles"]:
            enc = builds_en_cours()                  # un build peut demarrer pendant le lot : on revoit la garde a CHAQUE ligne
            if enc and faits:
                echec = {"id": e["id"], "chemin": e["chemin"], "motif": "un build a demarre pendant l'application : arret"}
                break
            cree = []
            try:
                if e["action"] == "deplacer" and (os.path.lexists(os.path.join(str(racine), e["vers"])) or _protege(e["vers"], racine)):
                    raise OSError("la destination existe ou est devenue protegee depuis l'apercu")   # TOCTOU : dossier, lien ou jonction apparu entre-temps
                if e["action"] == "deplacer" and e["cree_dossier"] and _protege(e["cree_dossier"], racine):
                    raise OSError("le dossier a creer est devenu protege ou sort du depot")
                if e["action"] == "deplacer" and e["cree_dossier"] and not a_blanc:
                    cible = os.path.join(str(racine), e["cree_dossier"])
                    niveau, borne = cible, os.path.normcase(os.path.abspath(str(racine)))
                    while not os.path.isdir(niveau) and os.path.normcase(os.path.abspath(niveau)) != borne:
                        cree.append(niveau)           # du plus profond au plus haut : l'ordre du retrait si git echoue
                        niveau = os.path.dirname(niveau)
                    if cree:
                        os.makedirs(cible)
                _journalise(journal, {"id": e["id"], "action": e["action"], "chemin": e["chemin"], "vers": e["vers"], "intention": True, "a_blanc": bool(a_blanc)})
                ok, sortie = _lance_git(racine, e["action"], e["chemin"], e["vers"], bool(a_blanc))
            except OSError as erreur:
                ok, sortie = False, f"{type(erreur).__name__} : {erreur}"[:300]
            _journalise(journal, {"id": e["id"], "action": e["action"], "chemin": e["chemin"], "vers": e["vers"], "ok": ok, "sortie": sortie, "a_blanc": bool(a_blanc)})
            if not ok:
                for dossier in cree:              # dossiers crees pour rien : on ne laisse pas de dossiers vides
                    try:
                        os.rmdir(dossier)
                    except OSError:
                        break
                echec = {"id": e["id"], "chemin": e["chemin"], "motif": sortie}
                break
            faits.append({"id": e["id"], "action": e["action"], "chemin": e["chemin"], "vers": e["vers"], "commande": e["commande"],
                          "dossiers_crees": [os.path.relpath(d, str(racine)).replace(os.sep, "/") for d in cree]})
        restants = [e["id"] for e in r["eligibles"] if e["id"] not in {f["id"] for f in faits} and (not echec or e["id"] != echec["id"])]
        return {"a_blanc": bool(a_blanc), "faits": faits, "echec": echec, "restants": restants, "renvois": verifie_refs(racine) if faits and not a_blanc else None}
    finally:
        _VERROU.release()
