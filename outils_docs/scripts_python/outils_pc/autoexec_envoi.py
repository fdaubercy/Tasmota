#!/usr/bin/env python3
"""Envoi OTA de l'autoexec.bat du depot a sa carte (plan autoexec-bat, A7), onglet « autoexec.bat » de l'Assistant persist.
  prepare(racine, env, builds_en_cours)   {adresse, hostname_carte, sur_carte (masque ; None si absent), ecart, jeton}
  envoie(racine, env, jeton, rouges_lus, redemarrer, builds_en_cours)   {envoye: True, sauvegarde: chemin ou None, avertissement}
Deroule, comme la page build pour un envoi OTA du FS (build_serie.Serie._lance_ota) : refus pendant un build, avant toute
requete ; adresse de build_envs.liste_envs (IP du .h, ou `IP:port` d'un esclave joint par son maitre) ; `IP:port` ->
build_ota_maitre.joint_par_maitre d'abord ; puis Status 5 compare au serveur.hostname du persist du depot (different,
illisible, ou pas de persist : refus, rien envoye) ; autoexec.bat de la carte lu par /ufsu?dir=0&download=/autoexec.bat
(connexion fermee sans reponse = fichier absent, comme Tasmota). Envoye : les octets du fichier du DEPOT (celui
qu'ecrit autoexec_fichier.ecrit, jamais le texte de la page), par build_ota_fs.envoie_fs_ota sur un dossier temporaire
qui ne contient que lui (fichiers=["autoexec.bat"] : persist ni sauvegarde, ni relu, ni recharge ; Restart 1 seulement
si `redemarrer`).
Jeton : `<instant>-<HMAC>` de (instant, env, adresse, sha256 du fichier du depot, sha256 de celui de la carte), cle tiree
par processus ; refuse a l'envoi si l'un a change, apres VALIDITE secondes, ou s'il ne vient pas de prepare. Rien sur disque.
Copie de la carte (elle porte des secrets) : sauvegardee AVANT l'envoi, hors depot, dans
fichiers_berry_sauvegarde.dossier_sauvegardes()/autoexec_cartes/<env>/<AAAAMMJJ-HHMMSS>.bat.
Envoi vers `IP:port` : le maitre passe en `Sleep 0` (build_ota_maitre.coupe_sleep) AVANT joint_par_maitre et reprend
sa valeur a la fin, envoi reussi ou non (comme build_serie) : a Sleep 50 son relais fait des pauses de plus de 5 s,
l'esclave abandonne le POST et garderait un autoexec.bat tronque. Un echec de la remise est rendu dans `avertissement`
(ou ajoute au message d'erreur). Build recontrole juste avant l'envoi (la phase reseau peut durer).
Banc : test_autoexec_envoi.py.
"""

import hashlib
import hmac
import http.client
import json
import secrets
import tempfile
import time
from pathlib import Path

import autoexec_fichier
import build_envs
import build_ota_fs
import fichiers_berry_sauvegarde as fbs
from build_ota_http import _get
from build_ota_maitre import _commande_repetee, coupe_sleep, joint_par_maitre

FICHIER = "autoexec.bat"
DELAI = 8.0
VALIDITE = 600                 # secondes entre prepare et envoie
REGLAGES_ENVOI = {}            # options de build_ota_fs.envoie_fs_ota (le banc y pose des delais courts)
ERREURS_RESEAU = (OSError, http.client.HTTPException)
_CLE = secrets.token_bytes(32)
_maintenant = time.time


def _builds(builds_en_cours):
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("impossible de savoir si un build tourne : envoi refuse")
    if builds:
        raise RuntimeError("un build est en cours (" + ", ".join(builds) + ") : envoi refuse")


def _depot(racine, env):
    p = Path(racine) / autoexec_fichier.chemin(env)
    if not p.is_file():
        raise ValueError(f"pas d'autoexec.bat au depot pour {env} : l'enregistrer d'abord")
    return p.read_bytes()


def _adresse(racine, env):
    return next((e.ip for e in build_envs.liste_envs(racine) if e.nom == env), "")


def _adresse_requise(racine, env):
    adresse = _adresse(racine, env)
    if not adresse:
        raise RuntimeError(f"pas d'adresse OTA pour {env} (WIFI_IP_ADDRESS du .h, ou esclave du range extender) : "
                           "rien n'a ete envoye")
    return adresse


def _carte(racine, env, adresse):
    """(nom d'hote, octets de l'autoexec.bat de la carte ou None) ; RuntimeError, rien envoye, sinon."""
    persist = build_envs.persist_carte(racine, env)
    if not persist:
        raise RuntimeError(f"pas de _persist.json de {env} au depot : identite de la carte non controlable, rien n'a ete envoye")
    if ":" in adresse:
        joint_par_maitre(adresse, persist, env, lambda _: None)
    try:
        hote = str(json.loads(_commande_repetee(adresse, "Status 5", DELAI)).get("StatusNET", {}).get("Hostname") or "")
    except ERREURS_RESEAU as erreur:
        raise RuntimeError(f"carte {adresse} injoignable ({erreur}) : rien n'a ete envoye") from None
    except (ValueError, AttributeError):
        hote = ""
    attendu = build_ota_fs._identite(persist.read_text(encoding="utf-8"))[0]
    if not hote or hote.lower() != attendu.lower():
        raise RuntimeError(f"{adresse} repond {hote or '?'} a Status 5, pas {attendu} ({env}) : rien n'a ete envoye")
    carte = None
    for _ in range(2):                             # une connexion coupee par le relais ne doit pas faire croire a l'absence
        try:
            carte = _get(adresse, "/ufsu?dir=0&download=/" + FICHIER, DELAI)
            break
        except http.client.RemoteDisconnected:     # Tasmota ferme sans repondre quand le fichier n'existe pas
            pass
        except ERREURS_RESEAU as erreur:
            raise RuntimeError(f"autoexec.bat de {adresse} illisible ({erreur}) : rien n'a ete envoye") from None
    return hote, carte


def _signe(instant, env, adresse, depot, carte):
    empreintes = [hashlib.sha256(o).hexdigest() if o is not None else None for o in (depot, carte)]
    message = json.dumps([instant, env, adresse, *empreintes]).encode("utf-8")
    return f"{instant}-{hmac.new(_CLE, message, hashlib.sha256).hexdigest()}"


def _sauvegarde(env, octets):
    dossier = fbs.dossier_sauvegardes() / "autoexec_cartes" / env
    dossier.mkdir(parents=True, exist_ok=True)
    base = time.strftime("%Y%m%d-%H%M%S")
    chemin, n = dossier / f"{base}.bat", 1
    while chemin.exists():                         # deux envois dans la meme seconde
        n += 1
        chemin = dossier / f"{base}-{n}.bat"
    chemin.write_bytes(octets)
    return chemin


def prepare(racine, env, builds_en_cours):
    _builds(builds_en_cours)
    depot = _depot(racine, env)
    adresse = _adresse_requise(racine, env)
    hote, carte = _carte(racine, env, adresse)
    sur_carte = None
    if carte is not None:
        sur_carte = autoexec_fichier.masque(carte.decode("utf-8", "replace").lstrip("﻿").replace("\r\n", "\n"))
    return {"adresse": adresse, "hostname_carte": hote, "sur_carte": sur_carte, "ecart": carte != depot,
            "jeton": _signe(int(_maintenant()), env, adresse, depot, carte)}


def envoie(racine, env, jeton, rouges_lus, redemarrer, builds_en_cours):
    if not isinstance(redemarrer, bool):
        raise ValueError("redemarrer : vrai ou faux attendu")
    if not isinstance(jeton, str):
        raise ValueError("jeton : chaine attendue (relancer la preparation)")
    _builds(builds_en_cours)
    depot = _depot(racine, env)
    texte = autoexec_fichier._texte(depot)        # les octets signes au jeton, pas une seconde lecture
    rouges = sum(a["niveau"] == "rouge" for a in autoexec_fichier.avertissements(racine, env, texte))
    if isinstance(rouges_lus, bool) or not isinstance(rouges_lus, int) or rouges_lus < rouges:
        raise ValueError(f"{rouges} avertissement(s) rouge(s) : cocher « J'ai lu les {rouges} avertissements rouges »")
    debut = jeton.partition("-")[0]
    instant = int(debut) if debut.isascii() and debut.isdigit() else -1
    if not 0 <= _maintenant() - instant <= VALIDITE:
        raise RuntimeError("jeton perime (plus de 10 minutes) ou inconnu : relancer la preparation")
    adresse = _adresse_requise(racine, env)
    remet = None
    if ":" in adresse:
        _, remet = coupe_sleep(adresse.rsplit(":", 1)[0])
    try:
        sauvegarde = _envoie(racine, env, jeton, instant, redemarrer, builds_en_cours, depot, adresse)
    except Exception as erreur:
        echec = remet() if remet else ""
        if echec:
            raise RuntimeError(f"{erreur} ; {echec}") from None
        raise
    except BaseException:  # arret brutal (Ctrl+C, SystemExit) : le maitre ne doit pas rester en Sleep 0
        if remet:
            remet()
        raise
    return {"envoye": True, "sauvegarde": None if sauvegarde is None else str(sauvegarde),
            "avertissement": remet() if remet else ""}


def _envoie(racine, env, jeton, instant, redemarrer, builds_en_cours, depot, adresse):
    """Suite d'envoie une fois le Sleep du maitre coupe : rend le chemin de la copie de la carte (None si absente)."""
    carte = _carte(racine, env, adresse)[1]
    if not hmac.compare_digest(jeton.encode("utf-8"), _signe(instant, env, adresse, depot, carte).encode("utf-8")):
        raise RuntimeError("le fichier du depot, celui de la carte ou l'adresse ont change depuis la preparation : "
                           "relancer la preparation")
    _builds(builds_en_cours)                       # la phase reseau a pu durer
    sauvegarde = _sauvegarde(env, carte) if carte is not None else None
    with tempfile.TemporaryDirectory(prefix=f"autoexec-{env}-", ignore_cleanup_errors=True) as dossier:
        (Path(dossier) / FICHIER).write_bytes(depot)
        build_ota_fs.envoie_fs_ota(env, adresse, dossier, fbs.dossier_sauvegardes() / "autoexec_cartes" / env,
                                   lambda _: None, fichiers=[FICHIER], redemarrer=redemarrer,
                                   **{"delai_http": DELAI, **REGLAGES_ENVOI})
    return sauvegarde
