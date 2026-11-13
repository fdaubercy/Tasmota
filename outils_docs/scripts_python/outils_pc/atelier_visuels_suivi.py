"""Suivi du visuel d'une carte (plan atelier-visuels A7) : visuel.json du depot compare a celui de la carte.

etat(...)["carte"] : identique | differente | absente (pas de visuel.json au depot : rien a comparer) | inconnue (carte muette).
`lecteur(env, "/json/visuel.json")` rend le contenu (octets ou texte) ou None si la carte n'a pas le fichier (-> differente) ;
une exception du lecteur = inconnue. Modele : etiquettes_qr_suivi.
"""

import json
from pathlib import Path

import fichiers_berry_etat as fbe

CHEMIN_CARTE = "/json/visuel.json"


def etat(racine, env, lecteur):
    try:
        depot = json.loads((Path(racine) / fbe.dossier_carte(env) / "visuel.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"carte": "absente"}
    try:
        lu = lecteur(env, CHEMIN_CARTE)
    except Exception:                                # carte muette, eteinte, hors reseau : jamais d'echec chez l'appelant
        return {"carte": "inconnue"}
    try:
        return {"carte": "identique" if lu is not None and json.loads(lu) == depot else "differente"}
    except (ValueError, TypeError):                  # reponse illisible : autre chose qu'un visuel.json
        return {"carte": "differente"}
