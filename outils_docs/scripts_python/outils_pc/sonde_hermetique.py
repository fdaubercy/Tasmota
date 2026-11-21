"""Aide des sondes Chrome dont la page est servie par acces_web.habille() (module de test, jamais importe par un outil).

La barre commune lit les vraies fiches de presence (%LOCALAPPDATA%/outils_tasmota/presence) et interroge la vraie page Build
(127.0.0.1:7700/execution) : une sonde qui ne la neutralise pas depend des outils lances sur le PC. Banc : test_sonde_hermetique.py.
"""
import acces_barre


def neutralise_barre():
    """Barre sans outil vivant, sans requete reseau et sans cache ; rend restaure(), qui remet l'etat d'avant l'appel."""
    avant = (acces_barre.outils_vivants, acces_barre._occupe, dict(acces_barre._CACHE))
    acces_barre.outils_vivants = lambda: []
    acces_barre._occupe = lambda *a: False
    acces_barre._CACHE["donnees"] = None

    def restaure():
        acces_barre.outils_vivants, acces_barre._occupe = avant[0], avant[1]
        acces_barre._CACHE.clear()
        acces_barre._CACHE.update(avant[2])
    return restaure
