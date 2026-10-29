"""Esclave du range extender joint par la redirection de son maitre (A11 de la page Build) : joint_par_maitre
pose la redirection et verifie l'identite de la carte jointe, coupe_sleep met le maitre en `Sleep 0` le temps
de l'envoi. Appeles par build_serie.Serie avant tout envoi vers une adresse `IP:port`.

Erreurs : RuntimeError("<étape> : <motif>"), toujours avec « rien n'a été envoyé ».
"""

import http.client
import json
import re
from pathlib import Path

from build_ota_fs import PERSIST, _identite
from build_ota_http import ETAPE_CONNEXION, _commande, _page_safeboot, _resume

ESSAIS_MAITRE = 3   # liaison du maitre P4 irreguliere : 2 requetes sur 40 au-dela de 8 s, 15 % de ping perdus (2026-10-29)


def _commande_repetee(ip, cmnd, delai, essais=ESSAIS_MAITRE):
    """_commande rejouee jusqu'a `essais` fois sans reponse : seulement pour une commande sans effet si rejouee."""
    for _ in range(essais - 1):
        try:
            return _commande(ip, cmnd, delai)
        except (OSError, http.client.HTTPException):
            pass
    return _commande(ip, cmnd, delai)


def joint_par_maitre(adresse, persist_env, env, rapporte, *, maitre=None, delai=8.0):
    """Esclave joint par le maitre (`<ip maitre>:<port>`) : redirection posee, puis identite de la carte verifiee.

    La table RgxPort du maitre se vide a son redemarrage (constat du 2026-10-26) : on lui fait poser ses
    redirections (RoutageRangeExtender, d'apres sa table de decouverte), puis on demande son nom d'hote a la
    carte jointe par `adresse` (Status 5). Une redirection absente ou vers une autre carte -> RuntimeError,
    rien n'est envoye. `maitre` : adresse HTTP du maitre (defaut : l'IP de `adresse`, port 80).
    """
    maitre = maitre or adresse.rsplit(":", 1)[0]
    rapporte({"etape": ETAPE_CONNEXION, "pourcent": None, "detail": f"redirection posée par le maître {maitre}"})
    try:
        reponse = _commande_repetee(maitre, "RoutageRangeExtender", delai)
    except (OSError, http.client.HTTPException) as erreur:
        raise RuntimeError(f"{ETAPE_CONNEXION} : maître {maitre} injoignable après {ESSAIS_MAITRE} essais ({erreur}) ; "
                           f"rien n'a été envoyé") from None
    if "RoutageRangeExtender" not in reponse:
        raise RuntimeError(f"{ETAPE_CONNEXION} : le maître {maitre} ne connaît pas RoutageRangeExtender (Berry arrêté ?) : "
                           f"{_resume(reponse)} ; rien n'a été envoyé")
    try:
        hote = str(json.loads(_commande_repetee(adresse, "Status 5", delai)).get("StatusNET", {}).get("Hostname") or "")
    except (OSError, http.client.HTTPException, ValueError, AttributeError) as erreur:
        raise RuntimeError(f"{ETAPE_CONNEXION} : aucune carte derrière {adresse} ({erreur}) : esclave hors ligne pour le "
                           f"maître (fiche Offline de sa découverte) ? rien n'a été envoyé") from None
    # Safeboot : pas de Status 5, on compare le DeviceName du titre de sa page a serveur.nom du persist.
    nom = None if hote else _page_safeboot(adresse, delai)
    if not persist_env or not Path(persist_env).is_file():
        return f"carte jointe : {hote or nom or '?'} (identité non contrôlée : pas de {PERSIST} de {env} au dépôt)"
    texte = Path(persist_env).read_text(encoding="utf-8")
    if nom is not None:
        attendu = str((json.loads(texte).get("serveur") or {}).get("nom") or "")
        if nom.lower() != attendu.lower():
            raise RuntimeError(f"{ETAPE_CONNEXION} : {adresse} mène à une carte en safeboot nommée {nom or '?'}, pas à "
                               f"{env} ({attendu}) ; rien n'a été envoyé")
        return f"carte jointe par le maître : {nom} (en safeboot)"
    attendu = _identite(texte)[0]
    if hote.lower() != attendu.lower():
        raise RuntimeError(f"{ETAPE_CONNEXION} : {adresse} mène à {hote or '?'}, pas à {env} ({attendu}) ; "
                           f"rien n'a été envoyé")
    return f"carte jointe par le maître : {hote}"


def coupe_sleep(maitre, delai=8.0):
    """`Sleep 0` sur le maitre le temps d'un envoi par sa redirection -> (valeur d'avant, fonction qui la remet).

    Mesure du 2026-10-28 (1 Mo vers la cuve par la redirection) : `Sleep 50` -> pauses du relais NAPT jusqu'a
    7,8 s, au-dela des 5 s ou le serveur web de l'esclave abandonne un envoi (HTTP_MAX_POST_WAIT) ; `Sleep 0` ->
    74 a 102 Ko/s, aucune pause. La fonction rendue remet la valeur et rend "" ou le message d'echec.
    """
    try:
        valeur = re.search(r'"Sleep"\D*(\d+)', _commande_repetee(maitre, "Sleep", delai))   # {"Sleep":{"50":{"Active":"50"}}}
        if valeur is None:
            raise ValueError("réponse de Sleep illisible")
        _commande_repetee(maitre, "Sleep 0", delai)
    except (OSError, http.client.HTTPException) as erreur:
        raise RuntimeError(f"{ETAPE_CONNEXION} : Sleep du maître {maitre} non coupé après {ESSAIS_MAITRE} essais ({erreur}) ; "
                           f"rien n'a été envoyé") from None
    except ValueError as erreur:
        raise RuntimeError(f"{ETAPE_CONNEXION} : Sleep du maître {maitre} non coupé ({erreur}) ; rien n'a été envoyé") from None
    valeur = valeur.group(1)

    def remet():
        try:
            _commande_repetee(maitre, f"Sleep {valeur}", delai)
            return ""
        except (OSError, http.client.HTTPException) as erreur:
            return f"Sleep {valeur} NON remis sur le maître {maitre} ({erreur}) : le remettre à la main"
    return valeur, remet
