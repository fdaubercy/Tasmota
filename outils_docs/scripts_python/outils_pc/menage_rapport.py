"""Rapport de l'agent auditeur-menage : validation et nettoyage avant affichage dans la page « Menage du depot ».

Le rapport est un JSON ecrit par l'agent (modele : `outils_docs/schemas/menage_rapport.schema.json`). Cette validation
est la seule porte : tout ce qui vient de l'agent est une donnee, jamais une consigne. Rien n'est ecrit au depot.

    valide(texte_ou_dict, racine) -> (rapport_propre, erreurs)
        erreurs non vide = rapport refuse (rapport_propre vaut None).
    extrait_json(sortie) -> dict | None   : premier objet JSON de la sortie de l'agent (texte libre autour toleré).
"""

import json
import re
from pathlib import Path, PurePosixPath

CATEGORIES = ("orphelin", "reste", "hors_dossier", "doublon", "taille", "poids", "vide")
ACTIONS = ("supprimer", "archiver", "deplacer", "garder")
RISQUES = ("faible", "moyen", "eleve")
MAX_PROPOSITIONS = 500
MAX_TEXTE = 2000
# Valeurs ressemblant a un secret : masquees avant d'aller a la page (le rapport ne doit pas en porter, mais on ne s'y fie pas).
SECRET = re.compile(r"((?:ghp_|github_pat_|AKIA|AIza|xox[abp]-)[A-Za-z0-9_-]*|sk-[A-Za-z0-9]{16,}|BEGIN [A-Z ]*PRIVATE KEY|://[^/\s:@]+:[^/\s@]+@)")
CLE_SECRET = re.compile(r"(?:pass(?:word)?|pwd|mdp|token|secret|api[_-]?key)\w*[\"']?\s*[:=]\s*([\"'])", re.I)


def masque(texte):
    """Masque les motifs de secret connus et la valeur entre guillemets qui suit un nom de champ sensible."""
    texte = SECRET.sub("***", texte)
    spans, pos = [], 0
    while True:
        m = CLE_SECRET.search(texte, pos)
        if not m:
            break
        fin = texte.find(m.group(1), m.end())
        fin = len(texte) if fin == -1 else fin
        spans.append((m.end(), fin))
        pos = m.end()   # on rescanne DANS la valeur : elle peut contenir le nom du champ suivant
    dernier = len(texte) + 1
    for debut, fin in reversed(spans):
        if fin <= dernier:
            texte = texte[:debut] + "***" + texte[fin:]
            dernier = debut
    return texte


def chemin_sur(chemin, racine):
    """Chemin relatif au depot, sans '..', sans absolu, sans lecteur, qui reste dans la racine."""
    if not isinstance(chemin, str) or not chemin or "\x00" in chemin:
        return None
    p = PurePosixPath(chemin.replace("\\", "/"))
    if p.is_absolute() or re.match(r"^[A-Za-z]:", chemin) or ".." in p.parts or chemin.startswith(("/", "\\")):
        return None
    try:
        (Path(racine) / p).resolve().relative_to(Path(racine).resolve())
    except ValueError:
        return None
    return str(p)


def extrait_json(sortie):
    """Premier objet JSON equilibre de `sortie` (l'agent peut ecrire du texte autour)."""
    if isinstance(sortie, dict):
        return sortie
    debut = sortie.find("{")
    while debut != -1:
        profondeur, dans_chaine, echappe = 0, False, False
        for i in range(debut, len(sortie)):
            c = sortie[i]
            if dans_chaine:
                echappe = (c == "\\" and not echappe)
                if c == '"' and not echappe:
                    dans_chaine = False
                continue
            if c == '"':
                dans_chaine = True
            elif c == "{":
                profondeur += 1
            elif c == "}":
                profondeur -= 1
                if profondeur == 0:
                    try:
                        return json.loads(sortie[debut:i + 1])
                    except ValueError:
                        break
        debut = sortie.find("{", debut + 1)
    return None


def _texte(valeur, nom, erreurs, obligatoire=True):
    if valeur is None and not obligatoire:
        return ""
    if not isinstance(valeur, str):
        erreurs.append(f"{nom} : texte attendu")
        return ""
    return masque(valeur[:MAX_TEXTE])


def valide(rapport, racine):
    erreurs = []
    if isinstance(rapport, str):
        rapport = extrait_json(rapport)
    if not isinstance(rapport, dict):
        return None, ["rapport : objet JSON introuvable"]
    props = rapport.get("propositions")
    if not isinstance(props, list):
        return None, ["propositions : liste attendue"]
    if len(props) > MAX_PROPOSITIONS:
        return None, [f"propositions : {len(props)} au-dela de {MAX_PROPOSITIONS}"]
    propres, ids = [], set()
    for i, p in enumerate(props):
        nom = f"propositions[{i}]"
        if not isinstance(p, dict):
            erreurs.append(f"{nom} : objet attendu")
            continue
        ident = p.get("id")
        if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,40}", ident):
            erreurs.append(f"{nom}.id : identifiant simple attendu")
        elif ident in ids:
            erreurs.append(f"{nom}.id : doublon {ident}")
        else:
            ids.add(ident)
        for cle, permis in (("categorie", CATEGORIES), ("action", ACTIONS), ("risque", RISQUES)):
            if p.get(cle) not in permis:
                erreurs.append(f"{nom}.{cle} : {p.get(cle)!r} hors de {permis}")
        chemin = chemin_sur(p.get("chemin"), racine)
        if chemin is None:
            erreurs.append(f"{nom}.chemin : chemin refuse ({str(p.get('chemin'))[:60]!r})")
        if not isinstance(p.get("en_cours", False), bool):
            erreurs.append(f"{nom}.en_cours : booleen attendu")
        vers = p.get("vers")
        if vers is not None and chemin_sur(vers, racine) is None:
            erreurs.append(f"{nom}.vers : chemin refuse")
        propres.append({
            "id": ident, "categorie": p.get("categorie"), "chemin": chemin, "action": p.get("action"),
            "risque": p.get("risque"), "en_cours": bool(p.get("en_cours", False)),
            "vers": chemin_sur(vers, racine) if vers else None,
            "constat": _texte(p.get("constat"), f"{nom}.constat", erreurs),
            "preuve": _texte(p.get("preuve"), f"{nom}.preuve", erreurs),
            "casserait": _texte(p.get("casserait"), f"{nom}.casserait", erreurs),
        })
    resume = _texte(rapport.get("resume"), "resume", erreurs)
    non_verifie = _texte(rapport.get("non_verifie", ""), "non_verifie", erreurs, obligatoire=False)
    if erreurs:
        return None, erreurs
    return {"resume": resume, "non_verifie": non_verifie, "propositions": propres}, []
