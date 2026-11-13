"""Suivi des etiquettes QR code (plan etiquettes-qrcode A7) : etiquette a reimprimer, page a regenerer, carte a jour.

- a_reimprimer : l'etiquette a ete imprimee (outils_docs/etiquettes_qr/impressions.json) et le texte du QR code calcule
  maintenant (reglage + persist + .h) n'a plus la meme empreinte ;
- a_regenerer : la carte a une page /qrcode (qrcode.json dans son dossier) et ce fichier differe de celui que l'outil
  ecrirait maintenant (texte, style, image...) ;
- carte : a_jour | a_mettre_a_jour | inconnu | sans_page. Lecture de /qrcode?f=reglage sur la carte (Referer de la
  carte : la route est a acces privilegie), comparee au qrcode.json du depot ; 404 = page absente de la carte. Adresse
  = celle de la page Build (Env.ip : IP du .h, ou <ipMaitre>:<port> pour un esclave du range extender). Delai 2 s.
"""

import json
import urllib.error
import urllib.request
from pathlib import Path

import build_envs
import etiquettes_qr_ecriture as ecriture
import etiquettes_qr_modele as modele
import fichiers_berry_etat as fbe

DELAI = 2
PAGE_OUTIL = "http://127.0.0.1:7970/?env="


def _get(url, entetes, delai):
    """(code HTTP, octets) ; OSError si la carte ne repond pas."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=entetes), timeout=delai) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as erreur:
        return erreur.code, b""


def _carte(adresse, depot, get, delai):
    if not adresse:
        return "inconnu"
    try:
        code, octets = get(f"http://{adresse}/qrcode?f=reglage", {"Referer": f"http://{adresse}/"}, delai)
        if code != 200:
            return "a_mettre_a_jour"                 # 404 : pas de page /qrcode sur la carte
        return "a_jour" if json.loads(octets) == depot else "a_mettre_a_jour"
    except ValueError:                               # reponse illisible : autre chose qu'un qrcode.json
        return "a_mettre_a_jour"
    except OSError:                                  # muette, eteinte, hors reseau (timeout compris)
        return "inconnu"


def etats(racine, env, *, envs=None, get=None, delai=DELAI):
    """{"a_reimprimer", "a_regenerer", "carte"} d'un env ; LookupError si ce n'est pas une carte du cenv."""
    racine = Path(racine)
    envs = envs if envs is not None else build_envs.liste_envs(racine)
    e = next((x for x in envs if x.nom == env and x.famille == "cartes"), None)
    if e is None:
        raise LookupError(f"carte inconnue : {env!r}")
    reglage = modele.charge_reglage(racine, env)
    resolu = modele.resout_avec(reglage, modele.champs_standards(racine, env, envs), modele.persist_de(racine, env))
    note = ecriture.lit_impressions(racine).get(env)
    a_reimprimer = isinstance(note, dict) and note.get("empreinte") != modele.empreinte(resolu["texte"])
    dossier = fbe.dossier_carte(env)
    try:
        depot = json.loads((racine / dossier / ecriture.FICHIER_CARTE).read_text(encoding="utf-8")) if dossier else None
    except (OSError, ValueError):
        depot = None
    if depot is None:
        return {"a_reimprimer": a_reimprimer, "a_regenerer": False, "carte": "sans_page"}
    try:
        a_regenerer = modele.fichier_carte(racine, reglage, resolu) != depot
    except ValueError:                               # image du reglage devenue illisible : a refaire dans l'outil
        a_regenerer = True
    return {"a_reimprimer": a_reimprimer, "a_regenerer": a_regenerer, "carte": _carte(e.ip, depot, get or _get, delai)}


def lien_si_regle(racine, env):
    """Lien vers la page 7970 de l'env s'il a un reglage d'etiquette, sinon None (message de fin des autres outils)."""
    return PAGE_OUTIL + env if modele.chemin_surcharge(racine, env).is_file() else None
