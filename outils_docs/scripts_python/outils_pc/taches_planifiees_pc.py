"""Voie PC de la page « Taches planifiees » : tache Windows `Tasmota-CompilationNuit` et resultats de compilation_nuit.py (LECTURE SEULE).

Format lu : `dernier.json` et `resultat-*.json` de %LOCALAPPDATA%\\outils_tasmota\\compilations_nuit\\ (maintenance/compilation_nuit.py::execute),
`config.json` (actif, envs_exclus, port). Un JSON corrompu est signale (`illisible`), jamais une exception.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "maintenance"))
import compilation_nuit as nuit                                           # noqa: E402
import compilation_nuit_tache as tache                                    # noqa: E402


def _lit(chemin):
    try:
        d = json.loads(Path(chemin).read_text(encoding="utf-8"))
    except OSError:
        return None
    except ValueError:
        return {"illisible": Path(chemin).name}
    return d if isinstance(d, dict) else {"illisible": Path(chemin).name}


def _resume(d):
    if d is None or "illisible" in d:
        return d
    envs = d.get("envs") if isinstance(d.get("envs"), list) else []
    envs = [e for e in envs if isinstance(e, dict)]
    echecs = [{"env": str(e.get("env")), "resultat": str(e.get("resultat"))} for e in envs if e.get("resultat") != "succes"]
    return {"debut": d.get("debut"), "code": d.get("code"), "refus": d.get("refus"), "fin": d.get("fin"), "nb_envs": len(envs),
            "nb_prevus": len(d["envs_prevus"]) if isinstance(d.get("envs_prevus"), list) else None,
            "secondes": sum(e["secondes"] for e in envs if isinstance(e.get("secondes"), (int, float))),
            "echecs": echecs}


def journal_de(env, dossier_journaux):
    """Chemin du journal local le plus recent d'un env (page Build), ou None."""
    try:
        trouves = sorted(Path(dossier_journaux).glob(f"*-{env}*"), key=lambda p: p.stat().st_mtime)
    except (OSError, ValueError):
        return None
    return str(trouves[-1]) if trouves else None


def lit_pc(dossier=None, executeur=tache.schtasks, journaux=None):
    dossier = Path(dossier) if dossier else nuit.dossier_donnees()
    journaux = Path(journaux) if journaux else dossier.parent / "build" / "journaux"
    try:
        t = tache.etat(executeur)
    except Exception as e:                                                # schtasks absent ou sortie inattendue
        t = {"existe": False, "actif": False, "erreur": f"{type(e).__name__}: {e}"}
    config = nuit.lit_config(dossier)
    dernier = _resume(_lit(dossier / "dernier.json"))
    if dernier and "echecs" in dernier:
        for e in dernier["echecs"]:
            e["journal"] = journal_de(e["env"], journaux)
    historique = []
    for f in sorted(dossier.glob("resultat-*.json"), reverse=True)[:7]:
        s = _resume(_lit(f))
        if s:
            historique.append({**s, "fichier": f.name})
    return {"tache": t, "config": {"actif": config["actif"], "envs_exclus": config["envs_exclus"], "port": config["port"]},
            "dossier": str(dossier), "dernier": dernier, "historique": historique}
