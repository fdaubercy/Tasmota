"""Series d'une carte pour l'atelier des graphiques (plan atelier-graphiques, A4).

Lecture SEULE : trois routes de la carte (/histo?p=liste, /cm?cmnd=Status 10, /pages?f=sources), jamais
RoutageRangeExtender, Sleep ni Backlog (spec §7.3). Carte muette -> repli sur le persist et graphiques.json du depot,
valeurs simulees (deterministes, graine = chemin).
"""
import calendar
import json
import random
import time
import urllib.parse
from pathlib import Path

import build_envs
import build_ota_http

DELAI = 4
NOM = "mesures"                           # nom de l'historique (defaut de graphiquesFonctions)
MAX_DIRECT = 12                           # chemins par requete /pages?f=valeurs
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


# Adresses des envs : build_envs.liste_envs coute ~1,2 s (lecture des IP du .h), or l'apercu de l'atelier relit a chaque
# cadence. Gardees tant que le cenv, l'override et le .h n'ont pas change (date et taille).
# shortcut: un ipMaitre change dans le _persist.json d'un esclave n'invalide pas le cache ; relancer l'atelier.
FICHIERS_ADRESSES = ("platformio_tasmota_cenv.ini", "platformio_override.ini", "tasmota/user_config_override.h")
_ADRESSES = {}


def _empreinte_adresses(racine):
    res = []
    for f in FICHIERS_ADRESSES:
        try:
            st = (racine / f).stat()
            res.append((st.st_mtime_ns, st.st_size))
        except OSError:
            res.append(None)
    return tuple(res)


def _adresses(racine):
    racine = Path(racine).resolve()
    empreinte = _empreinte_adresses(racine)
    garde = _ADRESSES.get(racine)
    if not garde or garde[0] != empreinte:
        garde = _ADRESSES[racine] = (empreinte, {e.nom: e.ip for e in build_envs.liste_envs(racine)})
    return garde[1]


def _carte(racine, env):
    """(adresse, dossier de donnees, persist) de l'env ; adresse "" si inconnue."""
    ip = _adresses(racine).get(env, "")
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
        liste = _json(get(ip, f"/histo?n={NOM}&p=liste", DELAI))
        sns = _json(get(ip, "/cm?cmnd=" + urllib.parse.quote("Status 10", safe=""), DELAI)).get("StatusSNS") or {}
        enregistrees = liste.get("series") or []
        if not (isinstance(liste, dict) and isinstance(sns, dict) and isinstance(enregistrees, list)
                and all(isinstance(c, str) for c in enregistrees)):
            raise ValueError("reponse inattendue")
    except Exception as e:                  # HTTPException, JSON tronque ou d'un autre type : meme repli
        return _depot(dossier, persist, f"carte injoignable ({e})")
    try:
        historique = bool(_json(get(ip, "/pages?f=sources", DELAI)).get("historique"))
    except Exception:                       # 404 : carte sans le moteur de pages, pas une erreur
        historique = bool(enregistrees)
    affichage = _graphiques(dossier) if dossier else {}
    feuilles = _feuilles(sns)
    chemins = enregistrees + [c for c in feuilles if c not in enregistrees]
    return {"source": "carte", "motif": "", "historique": historique,
            "series": [_serie(c, affichage, c in enregistrees, feuilles.get(c)) for c in chemins]}


def _simule(chemins, periode, mois, nom):
    """Memes formes que la carte ; valeurs deterministes (graine = chemin)."""
    maintenant = int(time.time())

    def un(c, k=0):
        if ".POWER" in c.upper() or c.upper().startswith("POWER"):
            return random.Random(f"{c}|{k}").choice(("ON", "OFF"))
        return round(random.Random(f"{c}|{k}").uniform(10, 90), 1)

    if periode == "direct":
        return {"t": maintenant, "valeurs": {c: un(c) for c in chemins[:MAX_DIRECT]}}
    n, pas = 24, 300
    if periode == "jour":
        t0 = maintenant // pas * pas - n * pas
        return {"nom": nom, "series": list(chemins), "pas": pas, "t0": t0,
                "valeurs": [[un(c, k) for k in range(n)] for c in chemins],
                "tEncours": t0 + n * pas, "encours": [un(c, n) for c in chemins]}
    debut = int(calendar.timegm(time.strptime(mois + "-01", "%Y-%m-%d"))) if mois else maintenant - n * 3600
    lignes = []
    for k in range(n):
        ligne = [debut + k * 3600]
        for c in chemins:
            m = un(c, k)
            ligne += [m, m, m] if isinstance(m, str) else [m - 1, m, m + 1]
        lignes.append(ligne)
    return {"nom": nom, "series": list(chemins), "lignes": lignes}


def valeurs(racine, env, chemins, periode, *, get=None, nom=NOM, mois=None):
    """Forme de la reponse de la carte, plus "source" ("carte" | "depot") que lecteurCarte ignore :
    direct -> {"t", "valeurs": {chemin: valeur|null}} (/pages?f=valeurs, 12 chemins au plus, d'apres Status 10) ;
    jour / mois -> JSON brut de /histo?n=<nom>&p=jour | p=mois&m=AAAA-MM (mois UTC en cours par defaut).
    Carte muette ou reponse inattendue : memes formes, valeurs simulees."""
    get = get or build_ota_http._get
    ip = _carte(racine, env)[0]
    if ip:
        try:
            if periode == "direct":
                sns = _json(get(ip, "/cm?cmnd=" + urllib.parse.quote("Status 10", safe=""), DELAI)).get("StatusSNS") or {}
                f = _feuilles(sns)
                res = {"t": int(time.time()), "valeurs": {c: f.get(c) for c in chemins[:MAX_DIRECT]}}
            else:
                url = f"/histo?n={urllib.parse.quote(nom)}&p={periode}"
                if periode == "mois":
                    mois = mois or time.strftime("%Y-%m", time.gmtime())
                    url += "&m=" + mois
                res = _json(get(ip, url, DELAI))
                if not isinstance(res, dict):
                    raise ValueError("reponse inattendue")
            res["source"] = "carte"
            return res
        except Exception:
            pass
    return dict(_simule(chemins, periode, mois, nom), source="depot")
