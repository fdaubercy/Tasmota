"""Modification d'un env existant par l'assistant de persist (spec 2026-10-27 §10, page 7900).

Partie 1 : recenser les cartes du parc et relire les reponses d'une carte depuis son persist.
  cartes(racine)                -> [{env, dossier, puce}] : envs « cartes » dont le dossier porte un _persist.json.
  reponses_de_l_env(racine, env) -> Reponses relues (reponses_depuis_persist + base + define). LookupError : pas une
                                   carte ; ValueError : persist illisible ou reponses refusees (jamais une valeur du persist).
  charge_env(racine, env)       -> {env, reponses (sans mot de passe : Reponses n'en porte pas), reglages_propres,
                                   avertissements}. reglages_propres = chemins du vrai persist qui different de ce que
                                   l'assistant regenererait (cles propres, retouches) : conserves a la modification.
"""

import json
from dataclasses import asdict
from pathlib import Path

import assistant_persist_generation as gen
import assistant_persist_modele as apm
import assistant_persist_parc as parc
import assistant_persist_texte as texte
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
import fichiers_berry_renommage as fbr
import fichiers_berry_suppression as fbx

PUCES = {prefixe: puce for puce, prefixe in parc.PREFIXES.items()}


def cartes(racine):
    """Les cartes du parc : famille « cartes » du cenv avec un _persist.json dans leur dossier."""
    res = []
    for e in fbe.envs_proposes(racine):
        if e["famille"] != "cartes":
            continue
        dossier = fbe.dossier_carte(e["nom"])
        if (Path(racine) / dossier / "_persist.json").is_file():
            res.append({"env": e["nom"], "dossier": dossier, "puce": PUCES.get(e["nom"].split("-")[0], "")})
    return res


def _persist_de(racine, env):
    """(dict du persist de la carte, texte de son chemin) ; LookupError si l'env n'est pas une carte."""
    carte = next((c for c in cartes(racine) if c["env"] == env), None)
    if carte is None:
        raise LookupError(f"{env} n'est pas une carte du parc")
    try:
        donnees = json.loads((Path(racine) / carte["dossier"] / "_persist.json").read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"{carte['dossier']}/_persist.json illisible : {exc.strerror or exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{carte['dossier']}/_persist.json ligne {exc.lineno} : {exc.msg}") from exc
    if not isinstance(donnees, dict):
        raise ValueError(f"{carte['dossier']}/_persist.json : un objet JSON est attendu")
    return donnees


def _relit(racine, env):
    """(modele, persist, Reponses) ; toute cle manquante devient une ValueError qui nomme la cle seulement."""
    donnees = _persist_de(racine, env)
    modele = apm.charge_modele(racine)
    try:
        r = gen.reponses_depuis_persist(modele, donnees, env, racine)
    except (KeyError, TypeError, AttributeError, StopIteration) as exc:
        cle = f" (cle {exc.args[0]!r})" if isinstance(exc, KeyError) else ""
        raise ValueError(f"{env} : persist incomplet ou dont le role n'est pas decrit par le modele{cle}") from None
    ini = fbi.lit_sections(racine)
    r.base = fbr._base(ini, env)
    r.define = fbx.define_de(ini, env) or ""
    return modele, donnees, r


def reponses_de_l_env(racine, env):
    modele, _, r = _relit(racine, env)
    gen.variables(racine, r)                                  # ValueError : role, heure, ip ou maitre inadmissibles
    return r


def charge_env(racine, env):
    modele, donnees, r = _relit(racine, env)
    v = gen.variables(racine, r)
    A = gen.persist(modele, r, v, gen.secrets_reponses(racine, r))
    return {"env": env, "reponses": asdict(r), "reglages_propres": len(texte.ecart(A, donnees)),
            "avertissements": []}
