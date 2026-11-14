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
# jamais upload / erase_upload : un envoi n'est pas relance (spec, « Ce qu'une reparation relance »)
ETAPES_VALIDES = {"compilation", "liens", "prebuild", "buildfs", ETAPES_TOUTES}
SECONDES_MAX = 3600


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
    if not isinstance(etapes, list) or not etapes or not all(e in ETAPES_VALIDES for e in etapes):
        raise ValueError(f"regle {id_} : « etapes » doit etre une liste non vide parmi {sorted(ETAPES_VALIDES)}")
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
            if isinstance(v, bool) or not isinstance(v, types) or not 0 <= v <= SECONDES_MAX:
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


def charge_catalogue_avec_avertissements(chemin_base, chemin_local):
    """(regles, avertissements). Base invalide = ValueError (bug du depot) ; local fautif = ignore et signale."""
    base = _lit(chemin_base, True)
    regles, avertissements = {}, []
    for d in base.get("regles", []):
        r = _valide(d)
        regles[r.id] = r
    try:
        local = _lit(chemin_local, False)
    except ValueError as e:
        return list(regles.values()), [str(e)]
    for d in local.get("regles", []):
        try:
            r = _valide(d)
        except ValueError as e:
            avertissements.append(f"regle locale ignoree : {e}")
            continue
        regles[r.id] = r
    sup = local.get("supprimees", [])
    if not isinstance(sup, list) or not all(isinstance(i, str) for i in sup):
        avertissements.append("« supprimees » du catalogue local ignore : liste de textes attendue")
        sup = []
    for id_ in sup:
        regles.pop(id_, None)
    return list(regles.values()), avertissements


def charge_catalogue(chemin_base, chemin_local):
    """Regles de base puis locales (une regle locale de meme id remplace celle de base), moins les « supprimees »."""
    return charge_catalogue_avec_avertissements(chemin_base, chemin_local)[0]


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


# Un secret = une CLE (STA_PASS1, MQTT_PASS, PASSWORD, WIFI_PW, token...) suivie de = ou : (ou d'un espace puis un guillemet,
# comme `#define STA_PASS1 "x"`), puis sa valeur ; ou le mot apres « Bearer ». Un mot libre (« pass through ») ne compte pas.
# Longueurs bornees : pas de retour arriere quadratique sur une ligne geante.
_SECRET = re.compile(r"""(\b\w{0,60}(?:PASS(?:WORD|WD)?|PWD|TOKEN|SECRET|(?<![A-Za-z0-9])PW|_PW)[0-9_]{0,10}["']?"""
                     r"""(?:\s{0,5}[:=]\s{0,5}|\s{1,5}(?=["'])))"""
                     r"""(\\"[^\n]{0,200}?\\"|"[^"\n]{0,200}"|'[^'\n]{0,200}'|[^\s,;]{1,200})""", re.IGNORECASE)
_BEARER = re.compile(r"(\bBearer\s+)[^\s,;]{1,200}", re.IGNORECASE)


def filtre_secrets(texte):
    """Masque la valeur qui suit un nom de mot de passe ou de jeton ; le nom reste lisible."""
    return _SECRET.sub(lambda m: m.group(1) + "***", _BEARER.sub(r"\1***", texte))
