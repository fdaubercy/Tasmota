"""Catalogue des reparations de la page Build (plan build-reparations A1) : regles, correspondance, filtre des secrets.

Une regle = un motif cherche dans la FIN du journal d'un `pio run` rate + des actions d'une liste FERMEE (jamais une
commande libre). Ce module ne fait que lire et comparer : l'execution des actions est ailleurs (A2, A3).

    charge_catalogue(chemin_base, chemin_local) -> list[Regle]   (ValueError si une regle est invalide)
    cherche(regles, journal, etape, env)         -> Regle | None
    filtre_secrets(texte)                        -> texte sans valeur de mot de passe ni de jeton

Catalogue de base : outils_docs/schemas/reparations_build.json (suivi par git, jamais ecrit par la page). Catalogue local
(%LOCALAPPDATA%\\outils_tasmota\\build\\reparations.json) : regles ajoutees et cle "supprimees" (ids retires), il l'emporte.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

LIGNES_FIN = 50                       # la correspondance ne regarde que la fin du journal (borne le cout d'un motif lent)
# action -> parametres requis (nom -> type) ; toute autre action est refusee
ACTIONS = {"attendre": {"secondes": (int, float)}, "libere_verrou": {}, "vide_build": {}}
ETAPES_TOUTES = "toutes"


@dataclass
class Regle:
    id: str
    titre: str
    motif: str
    etapes: list
    actions: list
    origine: str = "base"
    ajoutee_le: str = ""
    _re: object = field(default=None, repr=False, compare=False)


def _valide(d):
    """Construit une Regle depuis un dict du fichier ou leve ValueError."""
    if not isinstance(d, dict):
        raise ValueError("regle : objet attendu")
    for cle in ("id", "titre", "motif"):
        if not isinstance(d.get(cle), str) or not d[cle]:
            raise ValueError(f"regle : « {cle} » manquant")
    id_ = d["id"]
    etapes = d.get("etapes")
    if not isinstance(etapes, list) or not etapes or not all(isinstance(e, str) and e for e in etapes):
        raise ValueError(f"regle {id_} : « etapes » doit etre une liste non vide")
    actions = d.get("actions")
    if not isinstance(actions, list) or not actions:
        raise ValueError(f"regle {id_} : « actions » doit etre une liste non vide")
    for a in actions:
        nom = a.get("action") if isinstance(a, dict) else None
        if nom not in ACTIONS:
            raise ValueError(f"regle {id_} : action « {nom} » hors de la liste")
        params = a.get("parametres", {})
        if not isinstance(params, dict):
            raise ValueError(f"regle {id_} : « parametres » doit etre un objet")
        for p, types in ACTIONS[nom].items():
            v = params.get(p)
            if isinstance(v, bool) or not isinstance(v, types) or v < 0:
                raise ValueError(f"regle {id_} : action {nom}, parametre « {p} » manquant ou invalide")
    try:
        motif = re.compile(d["motif"], re.MULTILINE)
    except re.error as e:
        raise ValueError(f"regle {id_} : motif invalide ({e})") from e
    return Regle(id_, d["titre"], d["motif"], etapes, actions, str(d.get("origine", "base")), str(d.get("ajoutee_le", "")), motif)


def _lit(chemin, obligatoire):
    chemin = Path(chemin)
    if not chemin.is_file():
        if obligatoire:
            raise ValueError(f"catalogue introuvable : {chemin}")
        return {}
    try:
        data = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"catalogue illisible : {chemin} ({e})") from e
    if not isinstance(data, dict) or not isinstance(data.get("regles", []), list):
        raise ValueError(f"catalogue mal forme : {chemin}")
    return data


def charge_catalogue(chemin_base, chemin_local):
    """Regles de base puis locales (une regle locale de meme id remplace celle de base), moins les « supprimees »."""
    base, local = _lit(chemin_base, True), _lit(chemin_local, False)
    regles = {}
    for d in base.get("regles", []) + local.get("regles", []):
        r = _valide(d)
        regles[r.id] = r
    for id_ in local.get("supprimees", []):
        regles.pop(id_, None)
    return list(regles.values())


def cherche(regles, journal, etape, env):
    """Premiere regle dont `etapes` contient `etape` (ou « toutes ») et dont le motif correspond a la fin du journal."""
    lignes = (journal or "").splitlines()
    fin = "\n".join(lignes[-LIGNES_FIN:])
    if not fin.strip():
        return None
    for r in regles:
        if (etape in r.etapes or ETAPES_TOUTES in r.etapes) and r._re.search(fin):
            return r
    return None


# nom de cle (STA_PASS1, MQTT_PASS, PASSWORD, "token"...) puis separateur eventuel, puis la valeur (entre guillemets ou mot)
_SECRET = re.compile(r"""(\b\w*(?:PASS(?:WORD|WD)?|PWD|TOKEN|SECRET)[0-9_]*["']?(?:\s*[:=]\s*|\s+))("[^"\n]*"|'[^'\n]*'|[^\s,;]+)""",
                     re.IGNORECASE)


def filtre_secrets(texte):
    """Masque la valeur qui suit un nom de mot de passe ou de jeton ; le nom reste lisible."""
    return _SECRET.sub(lambda m: m.group(1) + "***", texte)
