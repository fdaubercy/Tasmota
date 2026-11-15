"""Routes des reparations de la page Build (plan build-reparations A4) : lecture du catalogue, suppression d'une regle locale.

    liste(dossier, serie)    -> {regles: [... origine, supprimable], avertissements, historique}   (GET /reparations)
    supprime(dossier, id)    -> retire une regle LOCALE de <dossier>/reparations.json ; ValueError id inconnu,
                                RuntimeError regle de base (suivie par git, jamais ecrite par la page)

Les ecritures (POST /reparation, /reparations/supprime) sont reservees a ce PC par build_web ; la lecture est permise
aux clients distants (aucune ligne de commande de processus : les messages de l'historique sont deja filtres).
"""

import json
import os
from dataclasses import asdict
from pathlib import Path

import build_reparations as rep
import build_reparations_ia
import build_serie


def _regles(dossier):
    local = Path(dossier) / "reparations.json"
    regles, avert = rep.charge_catalogue_avec_avertissements(rep.BASE, local)
    base = {r.id for r in rep.charge_catalogue_avec_avertissements(rep.BASE, local.with_name("absent.json"))[0]}
    return regles, base, avert, local


def liste(dossier, serie):
    try:
        regles, base, avert, _ = _regles(dossier)
    except ValueError as erreur:                                  # base illisible : la page le dit, rien ne casse
        return {"regles": [], "avertissements": [rep.filtre_secrets(str(erreur))], "historique": serie.reparations()}
    sortie = [{**{k: v for k, v in asdict(r).items() if k != "_re"}, "origine": "base" if r.id in base else "locale",
               "supprimable": r.id not in base} for r in regles]
    return {"regles": sortie, "avertissements": avert, "historique": serie.reparations()}


def ia(chemin, demande, serie, racine, journal_de, diagnostique=build_reparations_ia.diagnostique):
    """POST /reparations/diagnostic {env} -> proposition ; POST /reparations/appliquer {env, regle} -> {ok, attend}
    (la regle est revalidee contre le journal, l'application tourne dans un fil). ValueError 400, RuntimeError 409.
    Ce PC seulement : le refus des clients distants est dans build_web."""
    env = str(demande.get("env") or "")
    if not build_serie.NOM_ENV.fullmatch(env):
        raise ValueError("environnement invalide")
    _, etape = build_reparations_ia.contexte(serie, env)
    journal = journal_de(env)
    if chemin.endswith("/diagnostic"):
        return diagnostique(racine, env, etape, journal)
    regle = build_reparations_ia.valide_regle(demande.get("regle"), journal, etape)
    build_reparations_ia.lance_application(serie, env, regle, journal)
    return {"ok": True, "attend": serie.en_cours()}


def supprime(dossier, id_):
    regles, base, _, local = _regles(dossier)
    if id_ in base:
        raise RuntimeError("une règle de base ne se supprime pas (outils_docs/schemas/reparations_build.json)")
    if id_ not in {r.id for r in regles}:
        raise ValueError(f"règle inconnue : {id_!r}")
    with rep.VERROU_CATALOGUE:
        donnees = rep._lit(local, False)
        donnees["regles"] = [d for d in donnees.get("regles", []) if not (isinstance(d, dict) and d.get("id") == id_)]
        provisoire = local.with_suffix(".tmp")
        provisoire.write_text(json.dumps(donnees, indent=1, ensure_ascii=False), encoding="utf-8")
        os.replace(provisoire, local)
