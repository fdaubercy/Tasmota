"""Regeneration de qrcode.json par le pre-script (plan etiquettes-qrcode A7, demande du 2026-11-12).

Avant chaque pio run d'une carte (hors cibles d'outils), le texte de l'etiquette (outils_docs/etiquettes_qr/cartes/<env>.json)
est recalcule contre le persist et le .h du moment ; s'il differe du qrcode.json du dossier de la carte, ce fichier est
reecrit, comme le ferait la page 7970, et part dans l'image du FS. Rien pour un env sans reglage ni pour une carte sans
qrcode.json (pas de page /qrcode). L'etiquette imprimee passe d'elle-meme « a reimprimer » dans la page 7970 (empreinte du
texte). Une erreur ne leve jamais : elle devient une ligne d'avertissement, le build continue.
"""

import json
import sys
from pathlib import Path

OUTILS_PC = Path(__file__).resolve().parent.parent / "outils_pc"


def regenere(racine, env):
    """Ligne a afficher dans la sortie de pio, ou None si rien n'est a faire."""
    try:
        # Env sans reglage (presque tous) : un test de fichier, sans les imports ni la lecture des envs (~6 s sur le P4)
        if not (Path(racine) / "outils_docs/etiquettes_qr/cartes" / f"{env}.json").is_file():
            return None
        if str(OUTILS_PC) not in sys.path:
            sys.path.insert(0, str(OUTILS_PC))
        import etiquettes_qr_ecriture as ecriture
        import etiquettes_qr_suivi as suivi
        racine = Path(racine)
        dossier = suivi.fbe.dossier_carte(env)
        chemin = racine / dossier / ecriture.FICHIER_CARTE if dossier else None
        if not suivi.modele.chemin_surcharge(racine, env).is_file() or chemin is None or not chemin.is_file():
            return None
        persist = suivi.build_envs.persist_carte(racine, env)
        if persist:                                  # persist_de lit un persist casse comme {} : ne pas ecraser un bon fichier
            json.loads(Path(persist).read_text(encoding="utf-8"))
        neuf = suivi.fichier_attendu(racine, env)
        if json.loads(chemin.read_text(encoding="utf-8")) == neuf:
            return None
        chemin.write_bytes(ecriture._json(neuf))
        return f"QR code de {env} : régénéré ({dossier}/{ecriture.FICHIER_CARTE}), étiquette à réimprimer"
    except Exception as e:                           # noqa: BLE001 - jamais d'arret du build pour une etiquette
        return f"⚠ QR code de {env} : non vérifié ({type(e).__name__} : {e})"


_CARTES = {}      # liste des envs lue UNE fois par processus pio (4,5 s a chaque lecture), pas a chaque env


def _cartes(racine):
    if str(racine) not in _CARTES:
        import build_envs
        _CARTES[str(racine)] = build_envs.liste_envs(racine)
    return _CARTES[str(racine)]


def fiche(racine, env):
    """A11 : ligne « fiche QR a republier » si la fiche en ligne de la carte ne correspond plus a son reglage (sans
    reseau : derniere pointe connue de la branche etiquettes), None sinon. Rien n'est envoye ; une erreur = avertissement."""
    try:
        if not (Path(racine) / "outils_docs/etiquettes_qr/cartes" / f"{env}.json").is_file():
            return None
        if str(OUTILS_PC) not in sys.path:
            sys.path.insert(0, str(OUTILS_PC))
        import etiquettes_qr_publication as publication
        if not publication.fiche_a_republier(Path(racine), env, _cartes(racine)):
            return None
        return (f"Fiche QR de {env} : à republier (page 7970, « Publier les fiches… », "
                "ou case « Publier les fiches QR » de la page Build)")
    except Exception as e:                           # noqa: BLE001
        return f"⚠ Fiche QR de {env} : non vérifiée ({type(e).__name__} : {e})"
