"""Gestes de la page « Taches planifiees » (A4) : activer, desactiver, choisir les envs, lancer, arreter. Les ECRITURES.

Deux voies, memes gestes :
    PC     tache Windows `Tasmota-CompilationNuit` (maintenance/compilation_nuit_tache.py) et `config.json` de
           %LOCALAPPDATA%\\outils_tasmota\\compilations_nuit\\ (maintenance/compilation_nuit.py) ;
    GitHub workflow `Build_custom` par la CLI `gh`, envs exclus dans outils_docs/compilations_nuit/envs_github.json
           (lu par maintenance/matrice_github.py ; `publie_exclus_github` l'ecrit, le commite seul et le pousse, sans force, avec refus si des commits ne sont pas pousses).

Regles : ValueError = entree invalide (400), RuntimeError = refus (409). Toute ecriture de fichier est atomique. Les envs sont
verifies contre le cenv (jamais un nom inconnu ecrit). Chaque appel externe (schtasks, gh, HTTP, processus) est injectable : banc
test_taches_planifiees_gestes.py, aucune tache, aucun workflow ni aucun build reels.
`pc_arreter` arrete la serie EN COURS de la page Build, quelle qu'elle soit (la sienne comme un build lance a la main).
"""

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "maintenance"))
import compilation_nuit as nuit                                           # noqa: E402
import compilation_nuit_tache as tache                                    # noqa: E402
import matrice_github as matrice                                          # noqa: E402
from taches_planifiees_github import DEPOT, WORKFLOW, gh as gh_reel, panne  # noqa: E402

DELAI_GH = 30


def valide_envs(noms, racine=matrice.RACINE):
    """Liste de noms d'env connus du cenv, sans doublon, triee."""
    if not isinstance(noms, list) or not all(isinstance(n, str) for n in noms):
        raise ValueError("liste de noms d'env attendue")
    inconnus = sorted(set(noms) - set(matrice.envs_cenv(racine)))
    if inconnus:
        raise ValueError("env inconnu du cenv : " + ", ".join(inconnus))
    return sorted(set(noms))


# -- envs exclus --------------------------------------------------------------------------------------

def apercu_exclus_github(noms, racine=matrice.RACINE):
    """Ce que changerait l'ecriture de envs_github.json (rien n'est ecrit)."""
    apres = valide_envs(noms, racine)
    avant = sorted(matrice.lit_exclus(racine))
    return {"fichier": str(matrice.FICHIER_EXCLUS).replace("\\", "/"), "avant": avant, "apres": apres,
            "ajoutes": sorted(set(apres) - set(avant)), "retires": sorted(set(avant) - set(apres)),
            "inchange": avant == apres, "a_pousser": True}


def ecrit_exclus_github(noms, racine=matrice.RACINE):
    resultat = apercu_exclus_github(noms, racine)
    if not resultat["inchange"]:
        nuit.ecrit_atomique(Path(racine) / matrice.FICHIER_EXCLUS, {"exclus": resultat["apres"]})
    return resultat


def git_reel(args, racine):
    """(code, sortie) d'un `git` lance sans shell dans le depot ; l'echec de lancement est un code 1, pas une exception."""
    try:
        p = subprocess.run(["git", *args], cwd=str(racine), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=90)
    except (OSError, subprocess.SubprocessError) as e:
        return 1, str(e)
    return p.returncode, (p.stdout + p.stderr).strip()


def publie_exclus_github(noms, racine=matrice.RACINE, git=git_reel):
    """Ecrit envs_github.json, le commite SEUL (git commit -- <fichier>) et pousse CE commit vers origin/development.

    Jamais de force, jamais un autre fichier. Refus (RuntimeError) AVANT d'ecrire : autre branche, commits non pousses ou en retard sur
    origin (le push emporterait le travail d'une autre session), fichier deja modifie. Echec du push : le commit reste local, dit dans le message.
    """
    resultat = apercu_exclus_github(noms, racine)
    if resultat["inchange"]:
        return {**resultat, "publie": False}
    fichier = resultat["fichier"]
    code, branche = git(["rev-parse", "--abbrev-ref", "HEAD"], racine)
    if code or branche != "development":
        raise RuntimeError(f"branche courante {branche!r} : la publication se fait depuis development seulement")
    code, sortie = git(["fetch", "origin", "development"], racine)
    if code:
        raise RuntimeError("git fetch a echoue (reseau ?) : " + sortie[-200:])
    code, ecarts = git(["rev-list", "--left-right", "--count", "origin/development...HEAD"], racine)
    try:
        retard, avance = (int(x) for x in ecarts.split())
    except ValueError:
        raise RuntimeError("ecart avec origin illisible : " + ecarts[-200:])
    if code or retard or avance:
        raise RuntimeError(f"development a {avance} commit(s) non pousses et {retard} de retard sur origin : "
                           "pousser ou synchroniser d'abord, rien n'est ecrit")
    code, sale = git(["status", "--porcelain", "--", fichier], racine)
    if code or sale:
        raise RuntimeError(fichier + " est deja modifie dans l'arbre de travail : le commiter ou l'annuler d'abord, rien n'est ecrit")
    nuit.ecrit_atomique(Path(racine) / matrice.FICHIER_EXCLUS, {"exclus": resultat["apres"]})
    liste = ", ".join(resultat["apres"]) or "aucun"
    code, sortie = git(["commit", "-m", f"chore(ci): envs exclus de la compilation de nuit GitHub : {liste} (page Taches planifiees)", "--", fichier], racine)
    if code:
        raise RuntimeError("fichier ecrit mais commit refuse (hook ?) : " + sortie[-300:])
    code, sha = git(["rev-parse", "HEAD"], racine)
    code2, sortie = git(["push", "origin", f"{sha}:development"], racine)
    if code or code2:
        raise RuntimeError(f"fichier ecrit et commit {sha[:9]} fait EN LOCAL, push refuse : " + sortie[-300:])
    return {**resultat, "publie": True, "commit": sha[:9]}


def ecrit_exclus_pc(noms, dossier, racine=matrice.RACINE):
    """envs_exclus de config.json ; les autres cles (actif, port) sont gardees."""
    apres = valide_envs(noms, racine)
    config = nuit.lit_config(dossier)
    nuit.ecrit_atomique(Path(dossier) / "config.json", {**config, "envs_exclus": apres})
    return {"avant": sorted(config["envs_exclus"]), "apres": apres}


# -- voie PC ------------------------------------------------------------------------------------------

def pc_active(oui, executeur=tache.schtasks):
    if not tache.etat(executeur)["existe"]:
        raise RuntimeError("la tache planifiee n'existe pas : la creer d'abord (compilation_nuit_tache.py creer)")
    return tache.active(bool(oui), executeur)


def pc_heure(heure, executeur=tache.schtasks):
    if not tache.etat(executeur)["existe"]:
        raise RuntimeError("la tache planifiee n'existe pas : la creer d'abord (compilation_nuit_tache.py creer)")
    return tache.change_heure(heure, executeur)


def page_eteinte(port, delai=4.0):
    """True si rien n'ecoute sur le port (connexion refusee) ; une page lente (delai depasse) n'est PAS eteinte.
    Windows met ~2 s a signaler un refus sur un port local ferme (mesure du 2026-11-15) : le delai doit rester au-dessus."""
    try:
        socket.create_connection(("127.0.0.1", int(port)), timeout=delai).close()
        return False
    except ConnectionRefusedError:
        return True
    except OSError:
        return False


def _serie_en_cours(port, appel):
    code, etat = appel(port, "/execution", delai=5)
    if code != 200 or not isinstance(etat, dict):
        raise RuntimeError(f"la page Build ne repond pas sur le port {port}")
    return bool(etat.get("en_cours"))


def pc_arreter(port=nuit.PORT_DEFAUT, appel=nuit.appel):
    """Arrete IMMEDIATEMENT la serie en cours de la page Build (arbre du fils pio compris)."""
    if not _serie_en_cours(port, appel):
        raise RuntimeError("aucune compilation en cours sur la page Build")
    code, reponse = appel(port, "/arreter", {"immediat": True})
    if code != 200:
        raise RuntimeError(f"arret refuse (code {code}) : {reponse}")
    return {"arret": "immediat"}


def pc_lancer(port=nuit.PORT_DEFAUT, appel=nuit.appel, lance=subprocess.Popen, eteinte=page_eteinte, dossier=None):
    """Demarre compilation_nuit.py detache. Refuse si la page Build a deja une serie en cours, si une page lente ne repond pas, ou si un
    compilation_nuit.py tourne deja (jamais deux builds ensemble). Seule une page ETEINTE (connexion refusee) laisse partir le script."""
    autre = nuit.en_cours(dossier or nuit.dossier_donnees())
    if autre:
        raise RuntimeError(f"une compilation de nuit est deja en cours (processus {autre})")
    try:
        occupee = _serie_en_cours(port, appel)
    except RuntimeError:
        if not eteinte(port):
            raise RuntimeError(f"la page Build ne repond pas sur le port {port} (lente ou occupee) : reessayer dans un instant")
        occupee = False                                     # page eteinte : le script la demarre lui-meme
    if occupee:
        raise RuntimeError("une compilation est deja en cours sur la page Build")
    commande = [nuit_python(), str(Path(__file__).resolve().parents[1] / "maintenance" / "compilation_nuit.py")]
    try:
        lance(commande, cwd=str(nuit.RACINE), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
              creationflags=nuit.DRAPEAUX & ~nuit.CREATE_BREAKAWAY_FROM_JOB, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    except OSError as e:
        raise RuntimeError(f"lancement impossible : {e}")
    return {"lance": True}


def nuit_python():
    return nuit.python_page()


# -- voie GitHub --------------------------------------------------------------------------------------

def _gh(gh, args):
    code, sortie = gh(args, DELAI_GH)
    if code != 0:
        raise RuntimeError(panne(code, sortie))
    return sortie


def github_active(oui, gh=gh_reel):
    _gh(gh, ["workflow", "enable" if oui else "disable", WORKFLOW, "-R", DEPOT])
    try:                                                     # le geste est FAIT : une sortie illisible ne doit pas le faire passer pour un echec
        liste = json.loads(_gh(gh, ["workflow", "list", "-R", DEPOT, "--all", "--json", "name,state"]) or "[]")
    except ValueError:
        return {"etat": None, "actif": None, "avertissement": "geste envoye, etat non relu (reponse de gh illisible)"}
    etat = next((w.get("state") for w in liste if isinstance(w, dict) and w.get("name") == WORKFLOW), None)
    return {"etat": etat, "actif": etat == "active"}


def github_lancer(gh=gh_reel):
    _gh(gh, ["workflow", "run", WORKFLOW, "-R", DEPOT, "--ref", "development"])
    return {"lance": True}


def github_arreter(gh=gh_reel):
    """Annule les runs en cours ou en file de Build_custom ; rend leurs numeros."""
    ids = []
    for statut in ("in_progress", "queued"):
        sortie = _gh(gh, ["run", "list", "-R", DEPOT, "--workflow", WORKFLOW, "--status", statut, "--json", "databaseId"])
        try:
            ids += [int(r["databaseId"]) for r in json.loads(sortie or "[]")]
        except (ValueError, KeyError, TypeError):
            raise RuntimeError("reponse de gh illisible (liste des runs)")
    if not ids:
        raise RuntimeError("aucune compilation en cours sur GitHub")
    for i in ids:
        _gh(gh, ["run", "cancel", str(i), "-R", DEPOT])
    return {"annules": ids}
