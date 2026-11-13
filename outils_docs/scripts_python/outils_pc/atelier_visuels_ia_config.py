"""Cles et reglages des fournisseurs de l'assistant IA de l'atelier des visuels (plan atelier-visuels A9, spec § 2.10).

Fichier : %APPDATA%\atelier_visuels\config.json (Linux/macOS : ~/.config/atelier_visuels/config.json). HORS DU DEPOT : il
contient des cles d'API en clair (outil local, poste personnel), comme `sniffeur_mqtt_config.py`.
    {"fournisseurs": {"<id>": {"cle"?, "url"?, "modele"?, "plafond"?: envois/jour, "confirme"?: avertissement memorise}}}
La cle ne quitte JAMAIS ce module vers la page : `pour_page` ne rend que `masque(cle)`.
Le dict rendu par `lit` porte `_chemin` (le fichier lu) : les compteurs et le journal vivent a cote ; `ecrit` ne l'ecrit pas.
"""
import json
import os
from pathlib import Path


def chemin():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return Path(base) / "atelier_visuels" / "config.json"


def lit(fichier=None):
    f = Path(fichier or chemin())
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except FileNotFoundError:
        d = {}
    if not isinstance(d, dict) or not isinstance(d.get("fournisseurs", {}), dict):
        raise ValueError(f"{f} : {{\"fournisseurs\": {{...}}}} attendu")
    d.setdefault("fournisseurs", {})
    d["_chemin"] = str(f)
    return d


def ecrit(config, fichier=None):
    f = Path(fichier or config.get("_chemin") or chemin())
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps({k: v for k, v in config.items() if k != "_chemin"}, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    os.replace(tmp, f)


def regle(config, fournisseur_id, **champs):
    """Pose des champs (cle, url, modele, plafond, confirme) ; None retire le champ. N'ecrit pas : `ecrit` ensuite."""
    f = config.setdefault("fournisseurs", {}).setdefault(fournisseur_id, {})
    for k, v in champs.items():
        if v is None:
            f.pop(k, None)
        else:
            f[k] = v


def masque(cle):
    cle = cle if isinstance(cle, str) else ""
    return {"presente": bool(cle), "fin": cle[-4:] if len(cle) >= 8 else ""}


def pour_page(config):
    """Reglages montres a la page : tout sauf la cle, rendue par `masque`."""
    return {i: {**{k: v for k, v in f.items() if k != "cle"}, "cle": masque(f.get("cle"))}
            for i, f in config.get("fournisseurs", {}).items() if isinstance(f, dict)}
