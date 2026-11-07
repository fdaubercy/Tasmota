"""Envoi d'un .tapp fabrique vers /.extensions/ d'une carte (Fabrique d'extensions), par HTTP (/ufsu) ou MQTT (fsMqtt.be).

  prepare(racine, env, nom, builds_en_cours, *, transport)   {adresse, transport, hostname_carte, chemin, taille, sur_carte, jeton}
  envoie(racine, env, nom, jeton, confirme, redemarrer, builds_en_cours, *, transport)   {envoye, chemin, avertissement}

Identite, Sleep du maitre, voie et jeton : ceux d'autoexec_envoi.py (son CLIENT et ses REGLAGES_* valent aussi ici). Le sous-dossier est
atteint par les fonctions existantes : HTTP, build_ota_fs.envoie_fs_ota cree /.extensions par path.mkdir et y pose le dossier courant de la
carte (xdrv_50_filesystem.ino::UfsDirectory, UfsUploadFileOpen) ; MQTT, l'ordre `debut` de fsMqtt.be recoit le chemin complet, cree le dossier
parent. Prouve sur cartes simulees (test_tapp_envoi.py) et par lecture du code ; pas encore essaye sur une vraie carte (A10).
`sur_carte` : absent, identique, different, ou inconnu si la lecture echoue (gros fichier par MQTT en moins de 15 s) : ce n'est pas un refus.
Jeton : (instant, env|nom, adresse, sha256 du .tapp, transport) ; la copie de la carte n'y entre pas : la relire jusqu'a 1 Mo par MQTT prendrait
deux minutes. L'identite est revue a l'envoi. Sans redemarrage par defaut : l'extension se lance au demarrage suivant, ou par /ext.
Banc : test_tapp_envoi.py.
"""

import hashlib
import hmac
import tempfile
from pathlib import Path

import assistant_persist_autoexec as apx
import assistant_persist_modification as apm2
import autoexec_envoi as ae
import tapp_sources

TAILLE_MAX_MQTT = 1048576       # data/fs/fsMqtt.be : TAILLE_MAX (test_tapp_envoi.py compare)
ILLISIBLE = b"\0illisible"


def cartes(racine):
    return [c["env"] for c in apm2.cartes(racine)]


def _archive(racine, nom, transport):
    octets = tapp_sources.archive(racine, nom)
    if transport == "mqtt" and len(octets) > TAILLE_MAX_MQTT:
        raise RuntimeError(f"{nom}.tapp fait plus de 1 Mo ({len(octets)} octets), la limite de fsMqtt.be : l'envoyer par Wi-Fi (HTTP)")
    return octets


def prepare(racine, env, nom, builds_en_cours, *, transport="http"):
    ae.controle_transport(transport)
    tapp_sources.dossier(racine, nom)
    apx._env(racine, {"env": env})
    ae.controle_builds(builds_en_cours)
    octets = _archive(racine, nom, transport)
    chemin = tapp_sources.DESTINATION.format(nom)
    adresse = ae.adresse_de(racine, env, transport)
    hote, carte = ae.lit_carte(racine, env, adresse, transport, chemin, illisible=ILLISIBLE)
    sur_carte = ("absent" if carte is None else "inconnu" if carte == ILLISIBLE else "identique" if carte == octets else "different")
    return {"adresse": adresse, "transport": transport, "hostname_carte": hote, "chemin": chemin, "taille": len(octets),
            "sur_carte": sur_carte, "jeton": ae.signe(int(ae._maintenant()), f"{env}|{nom}", adresse, octets, None, transport)}


def envoie(racine, env, nom, jeton, confirme, redemarrer, builds_en_cours, *, transport="http"):
    ae.controle_transport(transport)
    tapp_sources.dossier(racine, nom)
    apx._env(racine, {"env": env})
    if confirme is not True:
        raise ValueError("cocher la case de confirmation avant d'envoyer")
    if not isinstance(redemarrer, bool):
        raise ValueError("redemarrer : vrai ou faux attendu")
    if not isinstance(jeton, str):
        raise ValueError("jeton : chaine attendue (relancer la preparation)")
    ae.controle_builds(builds_en_cours)
    octets = _archive(racine, nom, transport)
    instant = ae.instant_du_jeton(jeton)
    adresse = ae.adresse_de(racine, env, transport)
    _, avertissement = ae.avec_sleep_coupe(adresse, transport, lambda: _envoie(
        racine, env, nom, jeton, instant, redemarrer, builds_en_cours, octets, adresse, transport))
    return {"envoye": True, "chemin": tapp_sources.DESTINATION.format(nom), "avertissement": avertissement}


def _envoie(racine, env, nom, jeton, instant, redemarrer, builds_en_cours, octets, adresse, transport):
    attendu = ae.signe(instant, f"{env}|{nom}", adresse, octets, None, transport)
    if not hmac.compare_digest(jeton.encode("utf-8"), attendu.encode("utf-8")):
        raise RuntimeError("l'archive, la carte, l'adresse ou la voie ont change depuis la preparation : relancer la preparation")
    ae.lit_carte(racine, env, adresse, transport, None)
    ae.controle_builds(builds_en_cours)
    with tempfile.TemporaryDirectory(prefix=f"tapp-{nom}-", ignore_cleanup_errors=True) as dossier:
        rel = f".extensions/{nom}.tapp"
        cible = Path(dossier) / rel
        cible.parent.mkdir()
        cible.write_bytes(octets)
        ae.pousse(env, adresse, transport, dossier, rel, redemarrer)
