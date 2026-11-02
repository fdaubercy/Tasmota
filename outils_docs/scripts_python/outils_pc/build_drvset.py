"""Sauvegarde et retablit /.drvset003 (calibrage et compteurs d'energie) autour d'un flash serie (page build).

Un upload ou erase_upload serie reecrit le FS : le fichier du pilote d'energie (xdrv_03_esp32_energy.ino,
tEnergySettings ; voir outils_docs/FICHIERS_DRVSET.md) disparaitrait, donc le calibrage et le Total.

  sauvegarde(env, ip, dossier)   lit le fichier par le reseau AVANT le flash ; None si la carte est injoignable ou
                                 n'a pas ce fichier (carte sans mesure d'energie) : le flash n'est pas bloque.
  retablit(ip, chemin)           attend la carte APRES le flash, renvoie le fichier, redemarre, relit le calibrage.

Le redemarrage est un `Restart 99` (sans sauvegarde) : `Restart 1` passe par EnergySettingsSave, qui ecraserait le
fichier avec la RAM de la carte neuve. Une courte fenetre reste entre l'envoi et le redemarrage : la relecture la couvre.
"""

import http.client
import struct
import time
from pathlib import Path

from build_ota_http import _attend_retour, _commande, _get, _page_en_echec, _poste

FICHIER = ".drvset003"
TAILLE_MIN = 100                     # jusqu'a current_calibration[0] de tEnergySettings
OFFSETS = {"PowerCal": 32, "VoltageCal": 64, "CurrentCal": 96}
ERREURS_RESEAU = (OSError, http.client.HTTPException)


def calibrage(donnees):
    """{PowerCal, VoltageCal, CurrentCal} de la phase 1 d'un fichier .drvset003."""
    return {nom: struct.unpack_from("<I", donnees, o)[0] for nom, o in OFFSETS.items()}


def sauvegarde(env, ip, dossier, delai=20.0):
    """Copie horodatee du fichier -> Path, ou None sans fichier lisible (rien n'est leve)."""
    try:
        donnees = _get(ip, f"/ufsd?dir=0&download=/{FICHIER}", delai)
    except ERREURS_RESEAU:
        return None
    if len(donnees) < TAILLE_MIN:
        return None
    dossier = Path(dossier) / "drvset"
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"{env}-{time.strftime('%Y%m%d-%H%M%S')}{FICHIER}"
    chemin.write_bytes(donnees)
    return chemin


def retablit(ip, chemin, delai_retour=180.0, attente_min=0.0, sondage=2.0, delai_http=30.0):
    """Renvoie le fichier et le prouve -> calibrage relu ; RuntimeError (la copie reste dans `chemin`)."""
    donnees = Path(chemin).read_bytes()
    attendu = calibrage(donnees)
    try:
        _attend_retour(ip, delai_retour, attente_min, sondage, delai_http)
        _get(ip, "/ufsd?dir=0", delai_http)      # dossier courant remis a /
        statut, texte = _poste(ip, f"/ufsu?fsz={len(donnees)}", "ufsu", FICHIER, donnees, delai_http)
        if _page_en_echec(statut, texte):
            raise RuntimeError(f"envoi refusé par la carte (HTTP {statut})")
        try:
            _commande(ip, "Restart 99", delai_http)
        except ERREURS_RESEAU:
            pass                                 # la carte redemarre sans repondre : la relecture juge
        _attend_retour(ip, delai_retour, 15.0 if attente_min else 0.0, sondage, delai_http)
        relu = calibrage(_get(ip, f"/ufsd?dir=0&download=/{FICHIER}", delai_http))
    except (RuntimeError, struct.error, *ERREURS_RESEAU) as erreur:
        raise RuntimeError(f"{FICHIER} non rétabli sur {ip} ({erreur}) ; copie gardée : {chemin}") from None
    if relu != attendu:
        raise RuntimeError(f"{FICHIER} relu différent sur {ip} : {relu} au lieu de {attendu} ; copie gardée : {chemin}")
    return relu
