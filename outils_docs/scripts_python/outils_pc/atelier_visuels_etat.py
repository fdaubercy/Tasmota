"""Etat reel d'une carte pour l'apercu de l'atelier des visuels (GET /etat) : relais, mesures, liaisons.

La carte rend `/visuel?f=etat` ({t, power, sensor, modbus, wifi, reseau}, voir data/fs/visuelFonctions.be). Ici on le reduit a ce
que l'apercu peut montrer, SANS secret : seules les mesures numeriques sortent (jamais un texte), les cles au nom sensible
(`assistant_persist_modele.SECRET`) sont ecartees a tout niveau, et `chemins` (facultatif, "ANALOG.A1,Switch1") limite les mesures
a celles que la description cite. Carte muette, route absente, reponse illisible : {"etat": "inconnu"}, jamais d'exception.
"""
import json

import assistant_persist_modele as apm

CHEMIN_CARTE = "/visuel?f=etat"
PROFONDEUR = 4


def _nombre(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _mesures(src, chemins, profondeur=0, prefixe=()):
    """Copie de `src` limitee aux feuilles numeriques ; `chemins` = ensemble de tuples autorises (None = tout)."""
    if not isinstance(src, dict) or profondeur >= PROFONDEUR:
        return {}
    sortie = {}
    for k, v in src.items():
        k = str(k)
        if apm.SECRET.match(k):
            continue
        chemin = prefixe + (k,)
        if chemins is not None and not any(c[:len(chemin)] == chemin or chemin[:len(c)] == c for c in chemins):
            continue
        if _nombre(v):
            sortie[k] = v
        elif isinstance(v, dict):
            sous = _mesures(v, chemins, profondeur + 1, chemin)
            if sous:
                sortie[k] = sous
    return sortie


def _relais(v):
    if isinstance(v, list):
        return [x if isinstance(x, bool) or _nombre(x) else None for x in v][:64]
    return v if isinstance(v, bool) or _nombre(v) else None


def _liaisons(d):
    """modbus (delais en ms), wifi (booleen), reseau (mac, etat, rssi) : rien d'autre ne sort."""
    res = {}
    m = d.get("modbus")
    if isinstance(m, dict):
        esc = m.get("esclaves") if isinstance(m.get("esclaves"), dict) else {}
        res["modbus"] = {"serie_ms": m["serie_ms"] if _nombre(m.get("serie_ms")) else None,
                         "esclaves": {str(a)[:16]: v for a, v in esc.items() if _nombre(v)}}
    if isinstance(d.get("wifi"), bool):
        res["wifi"] = d["wifi"]
    if isinstance(d.get("reseau"), list):
        res["reseau"] = [{"mac": str(r.get("mac", ""))[:12], "etat": str(r.get("etat", ""))[:16],
                          "rssi": r["rssi"] if _nombre(r.get("rssi")) else None} for r in d["reseau"] if isinstance(r, dict)][:64]
    return res


def etat(env, lecteur, chemins=None):
    """{"etat": "connu", "relais", "mesures", "liaisons"} ou {"etat": "inconnu"}. `lecteur(env, chemin)` : octets ou None (404)."""
    try:
        brut = lecteur(env, CHEMIN_CARTE)
        d = json.loads(brut) if brut is not None else None
    except Exception:                                # carte muette, eteinte, hors reseau, reponse qui n'est pas du JSON
        return {"etat": "inconnu"}
    if not isinstance(d, dict):
        return {"etat": "inconnu"}
    voulus = {tuple(c.split(".")) for c in chemins.split(",") if c.strip()} if chemins else None
    return {"etat": "connu", "relais": _relais(d.get("power")), "mesures": _mesures(d.get("sensor"), voulus),
            "liaisons": _liaisons(d)}
