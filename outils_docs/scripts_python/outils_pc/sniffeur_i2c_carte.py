"""Lecture / ecriture d'un registre I2C PAR LA CARTE Tasmota, maitre du bus (sniffeur_i2c.py).

La carte recoit une commande Berry en ligne, par HTTP (/cm, en-tete Referer : build_ota_http._commande) :
    Br (wire1.detect(0x48) ? wire1 : wire2).read(0x48, 0x01, 2)
    Br (wire1.detect(0x20) ? wire1 : wire2).write(0x20, 0x01, 0xFF, 1)
`wire1`/`wire2` et non `tasmota.wire_scan` : wire_scan rend nil pour une adresse deja prise par un pilote C
(ADS1115, DS3231, MCP230xx de Tasmota). Le bus est trouve par `detect` (une sonde, visible dans le fil).
Aucun module a ajouter aux cartes. La trame doit ensuite apparaitre dans le fil du sniffeur (rapprochement
dans sniffeur_i2c.Sniffeur). Un `Br` n'est pas une lecture inoffensive : commande montree avant l'envoi,
une a la fois, et toute ecriture confirmee dans la page.
"""

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


def verifie_ip(ip):
    """IPv4 ou IPv4:port (esclave par le maitre) ; ValueError sinon (l'adresse vient de la page)."""
    hote, _, port = str(ip).strip().partition(":")
    morceaux = hote.split(".")
    if len(morceaux) != 4 or not all(m.isdigit() and 0 <= int(m) <= 255 for m in morceaux):
        raise ValueError(f"adresse IP invalide : {ip!r}")
    if port and not (port.isdigit() and 0 < int(port) < 65536):
        raise ValueError(f"port invalide : {ip!r}")
    return hote + (":" + port if port else "")


def envoie(ip, commande, delai=DELAI_S, transport=_commande):
    """(ok, reponse texte). Jamais d'exception : carte injoignable = (False, raison)."""
    try:
        return True, transport(verifie_ip(ip), commande, delai)
    except ValueError as erreur:
        return False, str(erreur)
    except Exception as erreur:         # OSError, HTTPException, delai : la carte ne repond pas
        return False, f"carte {ip} injoignable : {erreur}"
