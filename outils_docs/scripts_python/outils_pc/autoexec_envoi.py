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
Voie MQTT (`transport="mqtt"`, A1 du plan autoexec-mqtt-tapp) : meme deroule, sans adresse IP ni Sleep du maitre (un esclave
joint le broker par la sortie NAPT de son maitre). Topic = serveur.mqtt.topic du persist du depot (`adresse` = "mqtt:<topic>") ;
identite par `cmnd/<topic>/Status 5` -> `stat/<topic>/STATUS5` (meme comparaison au nom d'hote) ; le module fsMqtt.be doit
repondre ; fichier de la carte lu par Canal.lit (« fichier absent » = None) ; envoi par build_ota_mqtt.envoie_fs_mqtt. Le
transport entre dans le jeton. `CLIENT` et `REGLAGES_MQTT` : le banc y pose son faux client et des delais courts.
Reutilise par tapp_envoi.py (meme identite, meme jeton, meme voie) : controle_builds, controle_transport, adresse_de, lit_carte,
signe, instant_du_jeton, avec_sleep_coupe, pousse.
Banc : test_autoexec_envoi.py.
"""

import hashlib
import hmac
import http.client
import json
import queue
import secrets
import tempfile
import time
from pathlib import Path

import autoexec_fichier
import build_envs
import build_ota_fs
import build_ota_mqtt
import fichiers_berry_sauvegarde as fbs
from build_ota_http import _get
from build_ota_maitre import _commande_repetee, coupe_sleep, joint_par_maitre

FICHIER = "autoexec.bat"
DELAI = 8.0
VALIDITE = 600                 # secondes entre prepare et envoie
REGLAGES_ENVOI = {}            # options de build_ota_fs.envoie_fs_ota (le banc y pose des delais courts)
REGLAGES_MQTT = {}              # options de build_ota_mqtt.envoie_fs_mqtt (delai, attente_morceau, delai_retour)
CLIENT = build_ota_mqtt.client_par_defaut   # un client MQTT non connecte par usage (le Canal le ferme)
TRANSPORTS = ("http", "mqtt")
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


def _carte(racine, env, adresse, chemin, illisible):
    """(nom d'hote, octets du fichier `chemin` de la carte ou None) ; RuntimeError, rien envoye, sinon. Voir lit_carte."""
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
    _controle_hote(hote, persist, adresse, env)
    carte = None
    if chemin is None:
        return hote, None
    for _ in range(2):                             # une connexion coupee par le relais ne doit pas faire croire a l'absence
        try:
            carte = _get(adresse, "/ufsu?dir=0&download=" + chemin, DELAI)
            break
        except http.client.RemoteDisconnected:     # Tasmota ferme sans repondre quand le fichier n'existe pas
            pass
        except ERREURS_RESEAU as erreur:
            if illisible is not None:
                return hote, illisible
            raise RuntimeError(f"{chemin[1:]} de {adresse} illisible ({erreur}) : rien n'a ete envoye") from None
    return hote, carte


def _controle_hote(hote, persist, adresse, env):
    attendu = build_ota_fs._identite(persist.read_text(encoding="utf-8"))[0]
    if not hote or hote.lower() != attendu.lower():
        raise RuntimeError(f"{adresse} repond {hote or '?'} a Status 5, pas {attendu} ({env}) : rien n'a ete envoye")


def _topic(racine, env):
    persist = build_envs.persist_carte(racine, env)
    if not persist:
        raise RuntimeError(f"pas de _persist.json de {env} au depot : identite de la carte non controlable, rien n'a ete envoye")
    topic = build_ota_fs._identite(persist.read_text(encoding="utf-8"))[1]
    if not topic:
        raise RuntimeError(f"pas de serveur.mqtt.topic dans le _persist.json de {env} : carte injoignable par MQTT, "
                           "rien n'a ete envoye")
    return topic


def _carte_mqtt(racine, env, topic, chemin, illisible):
    """Comme _carte, par MQTT : (nom d'hote, octets du fichier `chemin` de la carte ou None) ; RuntimeError, rien envoye, sinon."""
    persist = build_envs.persist_carte(racine, env)
    delai, adresse = REGLAGES_MQTT.get("delai", 15.0), f"mqtt:{topic}"
    try:
        canal = build_ota_mqtt.Canal(CLIENT(), topic)
    except OSError as erreur:
        raise RuntimeError(f"broker MQTT injoignable ({erreur}) : rien n'a ete envoye") from None
    try:
        canal.client.abonne([f"stat/{topic}/STATUS5"])     # le Canal n'ecoute que fsmqtt/<topic>/etat et /lu
        canal.client.publie(f"cmnd/{topic}/Status", "5")
        fin, hote = time.monotonic() + delai, None
        while hote is None:
            try:
                r = canal.reponses.get(timeout=max(0.0, fin - time.monotonic()))
            except queue.Empty:
                raise RuntimeError(f"{adresse} ne repond pas a Status 5 en {delai:g} s : carte hors ligne ou broker muet, "
                                   "rien n'a ete envoye") from None
            if isinstance(r, dict) and "StatusNET" in r:   # le reste (reponses de fsMqtt.be) ne nous concerne pas
                hote = str((r["StatusNET"] or {}).get("Hostname") or "")
        _controle_hote(hote, persist, adresse, env)
        try:
            canal.ordre("Connexion MQTT", "abandon", delai)
        except RuntimeError:
            raise RuntimeError(f"aucune reponse de fsMqtt.be sur fsmqtt/{topic} : carte hors ligne, ou fsMqtt.be pas charge "
                               "par son autoexec ; rien n'a ete envoye") from None
        if chemin is None:
            return hote, None
        try:
            return hote, canal.lit(f"Lecture de {chemin[1:]}", chemin, delai)
        except RuntimeError as erreur:
            if "fichier absent" in str(erreur):
                return hote, None
            if illisible is not None:
                return hote, illisible
            raise RuntimeError(f"{chemin[1:]} de {adresse} illisible ({erreur}) : rien n'a ete envoye") from None
    finally:
        canal.ferme()


def _signe(instant, env, adresse, depot, carte, transport="http"):
    empreintes = [hashlib.sha256(o).hexdigest() if o is not None else None for o in (depot, carte)]
    message = json.dumps([instant, env, adresse, *empreintes, transport]).encode("utf-8")
    return f"{instant}-{hmac.new(_CLE, message, hashlib.sha256).hexdigest()}"


signe, controle_builds = _signe, _builds


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


def controle_transport(transport):
    if transport not in TRANSPORTS:
        raise ValueError("transport : « http » ou « mqtt » attendu")


def lit_carte(racine, env, adresse, transport, chemin="/" + FICHIER, illisible=None):
    """Identite de la carte controlee, puis (nom d'hote, octets de `chemin` ou None si absent). `chemin` None : identite seule ;
    `illisible` : rendu a la place des octets si la lecture echoue, au lieu d'un refus."""
    if transport == "mqtt":
        return _carte_mqtt(racine, env, adresse.partition(":")[2], chemin, illisible)
    return _carte(racine, env, adresse, chemin, illisible)


def adresse_de(racine, env, transport):
    return f"mqtt:{_topic(racine, env)}" if transport == "mqtt" else _adresse_requise(racine, env)


def instant_du_jeton(jeton):
    """L'instant de signature d'un jeton de moins de VALIDITE secondes ; RuntimeError sinon."""
    debut = jeton.partition("-")[0]
    instant = int(debut) if debut.isascii() and debut.isdigit() else -1
    if not 0 <= _maintenant() - instant <= VALIDITE:
        raise RuntimeError("jeton perime (plus de 10 minutes) ou inconnu : relancer la preparation")
    return instant


def avec_sleep_coupe(adresse, transport, appel):
    """Lance appel(), le maitre d'un esclave `IP:port` en Sleep 0 (docstring du module) : (resultat, avertissement de la remise)."""
    remet = None
    if transport == "http" and ":" in adresse:
        _, remet = coupe_sleep(adresse.rsplit(":", 1)[0])
    try:
        resultat = appel()
    except Exception as erreur:
        echec = remet() if remet else ""
        if echec:
            raise RuntimeError(f"{erreur} ; {echec}") from None
        raise
    except BaseException:  # arret brutal (Ctrl+C, SystemExit) : le maitre ne doit pas rester en Sleep 0
        if remet:
            remet()
        raise
    return resultat, remet() if remet else ""


def pousse(env, adresse, transport, dossier, fichier, redemarrer):
    """Envoie le seul `fichier` (relatif a `dossier`) par la voie choisie ; persist ni sauvegarde, ni relu, ni recharge."""
    sauvegardes = fbs.dossier_sauvegardes() / "autoexec_cartes" / env
    if transport == "mqtt":
        build_ota_mqtt.envoie_fs_mqtt(env, adresse.partition(":")[2], dossier, sauvegardes, lambda _: None,
                                      fichiers=[fichier], redemarrer=redemarrer, recharger_berry=False, client=CLIENT(),
                                      **REGLAGES_MQTT)
    else:
        build_ota_fs.envoie_fs_ota(env, adresse, dossier, sauvegardes, lambda _: None, fichiers=[fichier],
                                   redemarrer=redemarrer, **{"delai_http": DELAI, **REGLAGES_ENVOI})


def prepare(racine, env, builds_en_cours, *, transport="http"):
    controle_transport(transport)
    _builds(builds_en_cours)
    depot = _depot(racine, env)
    adresse = adresse_de(racine, env, transport)
    hote, carte = lit_carte(racine, env, adresse, transport)
    sur_carte = None
    if carte is not None:
        sur_carte = autoexec_fichier.masque(carte.decode("utf-8", "replace").lstrip("﻿").replace("\r\n", "\n"))
    return {"adresse": adresse, "transport": transport, "hostname_carte": hote, "sur_carte": sur_carte,
            "ecart": carte != depot, "jeton": _signe(int(_maintenant()), env, adresse, depot, carte, transport)}


def envoie(racine, env, jeton, rouges_lus, redemarrer, builds_en_cours, *, transport="http"):
    controle_transport(transport)
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
    instant = instant_du_jeton(jeton)
    adresse = adresse_de(racine, env, transport)
    sauvegarde, avertissement = avec_sleep_coupe(adresse, transport, lambda: _envoie(
        racine, env, jeton, instant, redemarrer, builds_en_cours, depot, adresse, transport))
    return {"envoye": True, "sauvegarde": None if sauvegarde is None else str(sauvegarde), "avertissement": avertissement}


def _envoie(racine, env, jeton, instant, redemarrer, builds_en_cours, depot, adresse, transport):
    """Suite d'envoie une fois le Sleep du maitre coupe : rend le chemin de la copie de la carte (None si absente)."""
    carte = lit_carte(racine, env, adresse, transport)[1]
    if not hmac.compare_digest(jeton.encode("utf-8"), _signe(instant, env, adresse, depot, carte, transport).encode("utf-8")):
        raise RuntimeError("le fichier du depot, celui de la carte, l'adresse ou le transport ont change depuis la preparation : "
                           "relancer la preparation")
    _builds(builds_en_cours)                       # la phase reseau a pu durer
    sauvegarde = _sauvegarde(env, carte) if carte is not None else None
    with tempfile.TemporaryDirectory(prefix=f"autoexec-{env}-", ignore_cleanup_errors=True) as dossier:
        (Path(dossier) / FICHIER).write_bytes(depot)
        pousse(env, adresse, transport, dossier, FICHIER, redemarrer)
    return sauvegarde
