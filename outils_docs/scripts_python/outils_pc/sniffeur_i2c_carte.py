"""Lecture / ecriture d'un registre I2C PAR LA CARTE Tasmota, maitre du bus (sniffeur_i2c.py).

La carte recoit une commande Berry en ligne, par HTTP (/cm, en-tete Referer : build_ota_http._commande) ou par
MQTT (cmnd/<topic>/Br, reponse {"Br": ...} sur stat/<topic>/RESULT, broker de user_config_override.h) :
    Br (wire1.detect(0x48) ? wire1 : wire2).read(0x48, 0x01, 2)
    Br (wire1.detect(0x20) ? wire1 : wire2).write(0x20, 0x01, 0xFF, 1)
`wire1`/`wire2` et non `tasmota.wire_scan` : wire_scan rend nil pour une adresse deja prise par un pilote C
(ADS1115, DS3231, MCP230xx de Tasmota). Le bus est trouve par `detect` (une sonde, visible dans le fil).
Aucun module a ajouter aux cartes. La trame doit ensuite apparaitre dans le fil du sniffeur (rapprochement
dans sniffeur_i2c.Sniffeur). Un `Br` n'est pas une lecture inoffensive : commande montree avant l'envoi,
une a la fois, et toute ecriture confirmee dans la page.
MQTT : pour un esclave derriere le NAPT du maitre (injoignable en HTTP sans RoutageRangeExtender) ; il joint le
broker par la sortie NAPT du maitre, comme fsMqtt.be (build_ota_mqtt.py).
"""

import json
import os
import time

import build_envs
import fichiers_berry_etat
import sniffeur_i2c_protocole as proto
from build_ota_http import _commande

DELAI_S = 5.0
OCTETS_MAX = 4                          # wire.read/write de Berry : un entier, 4 octets au plus


def commande_br(a, reg, n, valeur=None):
    """Texte de la commande Br ; ValueError si hors bornes (rien n'est envoye)."""
    if not proto.ADRESSE_MIN <= a <= proto.ADRESSE_MAX:
        raise ValueError(f"adresse 0x{a:02X} hors 0x{proto.ADRESSE_MIN:02X}..0x{proto.ADRESSE_MAX:02X}")
    if not 0 <= reg <= 0xFF:
        raise ValueError("registre 0x00..0xFF")
    if not 1 <= n <= OCTETS_MAX:
        raise ValueError(f"1 a {OCTETS_MAX} octets")
    bus = f"(wire1.detect(0x{a:02X}) ? wire1 : wire2)"
    if valeur is None:
        return f"Br {bus}.read(0x{a:02X}, 0x{reg:02X}, {n})"
    if not 0 <= valeur < 1 << (8 * n):
        raise ValueError(f"valeur hors 0..0x{(1 << (8 * n)) - 1:X} pour {n} octet(s)")
    return f"Br {bus}.write(0x{a:02X}, 0x{reg:02X}, 0x{valeur:0{2 * n}X}, {n})"


def ip_proposee(racine, carte):
    """IP de la carte « data/<lieu>/<carte> » d'apres le depot (WIFI_IP_ADDRESS, ou par le maitre), "" sinon."""
    try:
        for env in build_envs.liste_envs(racine):
            if env.famille == "cartes" and fichiers_berry_etat.dossier_carte(env.nom) == carte:
                return env.ip
    except (OSError, ValueError):
        pass
    return ""


def topic_propose(racine, carte):
    """Topic MQTT (serveur.mqtt.topic) du persist de « data/<lieu>/<carte> », "" sinon."""
    try:
        with open(os.path.join(racine, carte, "_persist.json"), encoding="utf-8") as f:
            return str(((json.load(f).get("serveur") or {}).get("mqtt") or {}).get("topic") or "")
    except (OSError, ValueError, AttributeError):
        return ""


def verifie_topic(topic):
    """Topic de carte sans joker ni espace ; ValueError sinon (le topic vient de la page)."""
    t = str(topic).strip().strip("/")
    if not t or len(t) > 100 or not t.isprintable() or any(c in t for c in "+# "):
        raise ValueError(f"topic MQTT invalide : {topic!r}")
    return t


def client_par_defaut():
    """Client (non connecte) du broker de user_config_override.h, comme le sniffeur MQTT."""
    import client_mqtt
    import sniffeur_mqtt
    cfg = sniffeur_mqtt.lit_config_broker()
    if not cfg.get("MQTT_HOST"):
        raise OSError("MQTT_HOST introuvable dans user_config_override.h")
    return client_mqtt.ClientMQTT(cfg["MQTT_HOST"], int(cfg.get("MQTT_PORT", 1883)), f"sniffeur-i2c-{os.getpid()}",
                                  cfg.get("MQTT_USER", ""), cfg.get("MQTT_PASS", ""))


def commande_mqtt(topic, commande, delai, fabrique=client_par_defaut):
    """Br par cmnd/<topic>/Br -> texte du RESULT qui porte la cle "Br" ; OSError si rien en `delai` s.

    shortcut: FullTopic suppose par defaut (%prefix%/%topic%/), celui de tout le parc ; a lire sur la carte sinon.
    """
    client = fabrique()
    client.connecte()
    try:
        retour = f"stat/{topic}/RESULT"
        client.abonne([retour])                   # le broker traite l'abonnement avant la publication qui suit
        client.publie(f"cmnd/{topic}/Br", commande.removeprefix("Br "))
        fin = time.monotonic() + delai
        while time.monotonic() < fin:
            m = client.recoit()
            if m is None or m.topic != retour:
                continue
            texte = m.payload.decode("utf-8", "replace")
            try:
                if "Br" in json.loads(texte):     # RESULT porte aussi les reponses des autres commandes
                    return texte
            except (ValueError, TypeError):
                pass
        raise OSError(f"aucune reponse sur {retour} en {delai:.0f} s : carte hors ligne, ou topic faux")
    finally:
        client.ferme()


def verifie_ip(ip):
    """IPv4 ou IPv4:port (esclave par le maitre) ; ValueError sinon (l'adresse vient de la page)."""
    hote, _, port = str(ip).strip().partition(":")
    morceaux = hote.split(".")
    if len(morceaux) != 4 or not all(m.isdigit() and 0 <= int(m) <= 255 for m in morceaux):
        raise ValueError(f"adresse IP invalide : {ip!r}")
    if port and not (port.isdigit() and 0 < int(port) < 65536):
        raise ValueError(f"port invalide : {ip!r}")
    return hote + (":" + port if port else "")


def envoie(cible, commande, delai=DELAI_S, transport=_commande, verifie=verifie_ip):
    """(ok, reponse texte) ; cible = IP (HTTP). Jamais d'exception : carte injoignable = (False, raison)."""
    try:
        return True, transport(verifie(cible), commande, delai)
    except ValueError as erreur:
        return False, str(erreur)
    except Exception as erreur:         # OSError, HTTPException, ErreurMQTT, delai : la carte ne repond pas
        return False, f"carte {cible} injoignable : {erreur}"


def envoie_mqtt(topic, commande, delai=DELAI_S, transport=commande_mqtt):
    """Comme envoie, par MQTT : cible = topic de la carte."""
    return envoie(topic, commande, delai, transport, verifie_topic)
