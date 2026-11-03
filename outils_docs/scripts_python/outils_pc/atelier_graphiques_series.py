"""Series d'une carte pour l'atelier des graphiques (plan atelier-graphiques, A4).

Lecture SEULE : trois routes de la carte (/histo?p=liste, /cm?cmnd=Status 10, /pages?f=sources), jamais
RoutageRangeExtender, Sleep ni Backlog (spec §7.3). Carte muette -> repli sur le persist et graphiques.json du depot,
valeurs simulees (deterministes, graine = chemin).
"""
import json
import random
import urllib.parse
from pathlib import Path

import build_envs
import build_ota_http

DELAI = 4
UNITES = (("temperature", "°C"), ("humidity", "%"), ("humidite", "%"), ("pressure", "hPa"), ("power", "W"),
          ("voltage", "V"), ("current", "A"), ("energy", "kWh"), ("taux", "%"))


def _json(octets):
    return json.loads(octets.decode("utf-8", "replace"))


def _feuilles(noeud, prefixe=""):
    """{chemin: valeur} des feuilles du JSON SENSOR (nombres et ON/OFF), sans l'horloge."""
    if isinstance(noeud, dict):
        res = {}
        for cle, v in noeud.items():
            if not prefixe and cle in ("Time", "TempUnit", "PressureUnit"):
                continue
            res.update(_feuilles(v, f"{prefixe}.{cle}" if prefixe else cle))
        return res
    if isinstance(noeud, bool) or not isinstance(noeud, (int, float, str)):
        return {}
    if isinstance(noeud, str) and noeud not in ("ON", "OFF"):
        return {}
    return {prefixe: noeud}


def _devine_unite(chemin):
    bas = chemin.lower()
    return next((u for mot, u in UNITES if mot in bas), "")


def _graphiques(dossier):
    try:
        return json.loads((dossier / "graphiques.json").read_text(encoding="utf-8")).get("affichage") or {}
    except (OSError, ValueError, AttributeError):
        return {}


def _serie(chemin, affichage, historique, valeur=None):
    a = affichage.get(chemin) or {}
    return {"chemin": chemin, "libelle": a.get("libelle") or chemin.rsplit(".", 1)[-1],
            "unite": a.get("unite", _devine_unite(chemin)), "historique": historique,
            "etat": isinstance(valeur, str) or chemin.upper().startswith("POWER") or ".POWER" in chemin.upper()}


def _carte(racine, env):
    """(adresse, dossier de donnees, persist) de l'env ; adresse "" si inconnue."""
    ip = next((e.ip for e in build_envs.liste_envs(racine) if e.nom == env), "")
    persist = build_envs.persist_carte(racine, env)
    return ip, (persist.parent if persist else None), persist


def _depot(dossier, persist, motif):
    affichage = _graphiques(dossier) if dossier else {}
    try:
        h = json.loads(persist.read_text(encoding="utf-8"))["diverses"]["historique"]
        actif = str(h.get("activation", "")).upper() == "ON"
        chemins = list(h.get("ajouts") or [])
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        actif, chemins = False, []
    chemins += [c for c in affichage if c not in chemins]
    return {"source": "depot", "motif": motif, "historique": actif,
            "series": [_serie(c, affichage, actif) for c in chemins]}


def series(racine, env, *, get=None):
    get = get or build_ota_http._get
    ip, dossier, persist = _carte(racine, env)
    if not ip:
        return _depot(dossier, persist, "adresse de la carte inconnue")
    try:
        liste = _json(get(ip, "/histo?n=mesures&p=liste", DELAI))
        sns = _json(get(ip, "/cm?cmnd=" + urllib.parse.quote("Status 10", safe=""), DELAI)).get("StatusSNS") or {}
    except Exception as e:   # HTTPException, JSON tronque : meme repli
        return _depot(dossier, persist, f"carte injoignable ({e})")
    try:
        historique = bool(_json(get(ip, "/pages?f=sources", DELAI)).get("historique"))
    except Exception:                       # 404 : carte sans le moteur de pages, pas une erreur
        historique = bool(liste.get("series"))
    enregistrees = set(liste.get("series") or [])
    affichage = _graphiques(dossier) if dossier else {}
    feuilles = _feuilles(sns)
    chemins = list(enregistrees) + [c for c in feuilles if c not in enregistrees]
    return {"source": "carte", "motif": "", "historique": historique,
            "series": [_serie(c, affichage, c in enregistrees, feuilles.get(c)) for c in chemins]}


def valeurs(racine, env, chemins, periode, *, get=None):
    """{"source", "valeurs": {chemin: nombre | "ON"/"OFF" | None}}. Instantane : `periode` n'est pas lue sur la carte
    (shortcut: pas de 4e route, l'historique sera lu par la page elle-meme)."""
    get = get or build_ota_http._get
    ip = _carte(racine, env)[0]
    if ip:
        try:
            sns = _json(get(ip, "/cm?cmnd=" + urllib.parse.quote("Status 10", safe=""), DELAI)).get("StatusSNS") or {}
            feuilles = _feuilles(sns)
            return {"source": "carte", "valeurs": {c: feuilles.get(c) for c in chemins}}
        except Exception:
            pass
    simulees = {}
    for c in chemins:
        alea = random.Random(f"{c}|{periode}")
        simulees[c] = alea.choice(("ON", "OFF")) if ".POWER" in c.upper() else round(alea.uniform(10, 90), 1)
    return {"source": "depot", "valeurs": simulees}
