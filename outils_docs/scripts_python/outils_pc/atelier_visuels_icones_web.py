"""Recherche d'icones en ligne pour l'atelier des visuels (spec 2026-11-13 § 2.4) : API Iconify, hote FIXE.

Module autonome : fonctions pures + client HTTP injectable (`ouvre=`). Aucun parametre libre vers le reseau :
`q` (1 a 40 caracteres), `jeu` et `nom` (`^[a-z0-9-]+$`) sont valides AVANT toute requete. Licences : permissives
d'office, CC BY avec confirmation a la conservation, le reste masque.
"""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import atelier_visuels_fond as fond

BASE = "https://api.iconify.design"
DELAI = 6
MAX_OCTETS = 64 * 1024
DUREE_CACHE = 30 * 86400
LIMITE = 48                       # l'API impose un minimum de 32
PERMISSIVES = {"MIT", "APACHE-2.0", "ISC", "CC0-1.0", "UNLICENSE"}
RE_Q = re.compile(r"^[A-Za-z0-9 -]{1,40}$")
RE_ID = re.compile(r"^[a-z0-9-]+$")
LONG_ID = 64


class HorsLigne(Exception):
    """Reseau absent, hote injoignable, delai depasse ou reponse inexploitable."""


def cache_defaut():
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".cache")
    return Path(base) / "outils_tasmota" / "atelier_visuels" / "icones"


def licences_ok(licence):
    """'permissive' | 'attribution' | 'masquee' d'apres l'identifiant SPDX."""
    s = (licence or "").upper()
    if s in PERMISSIVES:
        return "permissive"
    ok = s.startswith("CC-BY") and not any(x in s for x in ("-NC", "-ND", "-SA"))
    return "attribution" if ok else "masquee"


class _SansRedirection(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def ouvre_reel(url, delai=DELAI, maxi=MAX_OCTETS):
    """Octets de la reponse (https, sans redirection), au plus maxi + 1. HorsLigne sur toute erreur reseau."""
    try:
        requete = urllib.request.Request(url, headers={"User-Agent": "atelier-visuels"})
        with urllib.request.build_opener(_SansRedirection).open(requete, timeout=delai) as r:
            return r.read(maxi + 1)
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise HorsLigne(f"Iconify injoignable ({getattr(e, 'reason', e)}) : recherche en ligne indisponible, "
                        "les icones deja gardees restent utilisables") from None


def _get(url, ouvre, cache):
    if not url.startswith(BASE + "/"):
        raise ValueError("hote non permis")
    fic = Path(cache) / (hashlib.sha256(url.encode()).hexdigest() + ".bin") if cache else None
    if fic and fic.is_file() and time.time() - fic.stat().st_mtime < DUREE_CACHE:
        return fic.read_bytes()
    donnees = (ouvre or ouvre_reel)(url, DELAI, MAX_OCTETS)
    if len(donnees) > MAX_OCTETS:
        raise HorsLigne("reponse d'Iconify trop grosse : refusee")
    if fic:
        try:
            fic.parent.mkdir(parents=True, exist_ok=True)
            fic.write_bytes(donnees)
        except OSError:
            pass                                # le cache est un confort
    return donnees


def _json(url, ouvre, cache):
    try:
        v = json.loads(_get(url, ouvre, cache))
    except ValueError:
        raise HorsLigne("reponse d'Iconify illisible") from None
    if not isinstance(v, dict):
        raise HorsLigne("reponse d'Iconify inattendue")
    return v


def _id(valeur, role):
    if not isinstance(valeur, str) or len(valeur) > LONG_ID or not RE_ID.match(valeur):
        raise ValueError(f"{role} invalide (minuscules, chiffres et tirets)")


def recherche(q, ouvre=None, cache=None):
    """Icones trouvees, licences non permises ecartees : [{jeu, nom, licence, permissive, attribution}]."""
    if not isinstance(q, str) or not q.strip() or not RE_Q.match(q.strip()):
        raise ValueError("recherche invalide (1 a 40 caracteres : lettres, chiffres, tiret, espace)")
    url = f"{BASE}/search?" + urllib.parse.urlencode({"query": q.strip(), "limit": LIMITE})
    rep = _json(url, ouvre, cache)
    jeux = rep.get("collections") if isinstance(rep.get("collections"), dict) else {}
    sortie = []
    for ident in rep.get("icons") or []:
        jeu, _, nom = str(ident).partition(":")
        if not (RE_ID.match(jeu) and RE_ID.match(nom)):
            continue
        spdx = ((jeux.get(jeu) or {}).get("license") or {}).get("spdx", "")
        classe = licences_ok(spdx)
        if classe != "masquee":
            sortie.append({"jeu": jeu, "nom": nom, "licence": spdx,
                           "permissive": classe == "permissive", "attribution": classe == "attribution"})
    return sortie


def svg(jeu, nom, ouvre=None, cache=None):
    """{svg (nettoye), licence, auteur, origine}. ValueError : identifiant invalide ou licence masquee."""
    _id(jeu, "jeu")
    _id(nom, "nom")
    info = _json(f"{BASE}/collections?" + urllib.parse.urlencode({"prefix": jeu}), ouvre, cache).get(jeu) or {}
    spdx = (info.get("license") or {}).get("spdx", "")
    if licences_ok(spdx) == "masquee":
        raise ValueError(f"licence {spdx or 'inconnue'} non permise pour le jeu {jeu}")
    texte = _get(f"{BASE}/{jeu}/{nom}.svg", ouvre, cache).decode("utf-8", "replace")
    try:
        propre = fond.nettoie_svg(texte)
    except ValueError as e:
        raise HorsLigne(f"icone {jeu}:{nom} inexploitable ({e})") from None
    return {"svg": propre, "licence": spdx, "auteur": (info.get("author") or {}).get("name", ""),
            "origine": (info.get("license") or {}).get("url") or (info.get("author") or {}).get("url", "")}


def garde(racine, jeu, nom, info, confirme_attribution=False):
    """Range l'icone dans outils_docs/visuels_accueil/icones/ et note sa licence. Retourne le chemin ecrit."""
    _id(jeu, "jeu")
    _id(nom, "nom")
    classe = licences_ok(info.get("licence"))
    if classe == "masquee":
        raise ValueError("licence non permise : icone non gardee")
    if classe == "attribution" and not confirme_attribution:
        raise ValueError("licence a attribution : confirmation requise")
    dossier = Path(racine) / "outils_docs" / "visuels_accueil" / "icones"
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"{jeu}-{nom}.svg"
    with open(chemin, "x", encoding="utf-8") as f:         # FileExistsError : jamais d'ecrasement silencieux
        f.write(info["svg"])
    registre = dossier / "LICENCES.md"
    entete = "" if registre.is_file() else ("# Licences des icones gardees\n\n"
                                           "| Fichier | Licence | Auteur | Origine |\n|---|---|---|---|\n")
    with open(registre, "a", encoding="utf-8") as f:
        f.write(f"{entete}| {chemin.name} | {info['licence']} | {info.get('auteur', '')} | {info.get('origine', '')} |\n")
    return chemin
