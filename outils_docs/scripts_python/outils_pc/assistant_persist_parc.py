"""Lecture du parc et regles des mots de passe (assistant de creation du persist, spec 2026-10-27 §5.1 et §5.6).

Tout vient des `data/*/*/_persist.json` du depot (via `assistant_persist_modele.persists_du_depot`) ; rien n'est ecrit.
Un persist illisible est IGNORE (la page continue) et signale par `illisibles()`.

REGLE DES SECRETS (§5.1) : les mots de passe ne sont PAS dans le modele, ils sont repris du parc.
  - un reseau Wi-Fi ordinaire : le mot de passe associe a ce NOM dans les `reseau1`/`reseau2` du parc ;
  - un reseau `<HOSTNAME>-GATEWAY` : le `rangeExtender.AP.mdp` de la carte dont le SSID est ce nom (jamais lu dans
    les reseau1/2 : un esclave y recopie le mot de passe de l'AP de son maitre, c'est l'AP qui fait foi) ;
  - `mqtt`, `ap`, `ftp` : la valeur commune a tout le parc.
Un nom absent du parc, ou associe a deux valeurs differentes, leve ValueError : le message NOMME le reseau ou la cle,
jamais une valeur.
"""

from collections import Counter
from pathlib import Path

import assistant_persist_modele as apm
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi

PREFIXES = {"ESP32": "tasmota32", "ESP32S3": "tasmota32s3", "ESP32P4": "tasmota32p4"}
SUFFIXE_AP = "-GATEWAY"


def _cartes(racine):
    """[(dossier, persist)] des persists lisibles."""
    return [(Path(rel).parent.as_posix(), d) for rel, d, _ in apm.persists_du_depot(racine) if isinstance(d, dict)]


def _serveur(persist):
    s = persist.get("serveur")
    return s if isinstance(s, dict) else {}


def _sous(obj, *cles):
    for c in cles:
        obj = obj.get(c) if isinstance(obj, dict) else None
    return obj


def illisibles(racine):
    """Chemins relatifs des persists que le depot contient mais que la lecture a rejetes."""
    return [rel for rel, d, _ in apm.persists_du_depot(racine) if not isinstance(d, dict)]


def _envs_par_dossier(racine):
    res = {}
    for env in fbi.lit_sections(racine).envs_cenv():
        try:
            dossier = fbe.dossier_carte(env)
        except ValueError:
            continue
        if dossier:
            res.setdefault(dossier, env)
    return res


def maitres(racine):
    """[{env, dossier, hostname, ip, id}] des cartes a rangeExtender.id == 0 et activation ON."""
    envs, res = _envs_par_dossier(racine), []
    for dossier, d in _cartes(racine):
        re_ = _sous(_serveur(d), "rangeExtender")
        if not isinstance(re_, dict) or re_.get("activation") != "ON" or re_.get("id") != 0:
            continue
        res.append({"env": envs.get(dossier), "dossier": dossier, "hostname": _serveur(d).get("hostname", ""),
                    "ip": _sous(_serveur(d), "IP", "IPAddress") or "", "id": 0})
    return res


def ids_pris(racine):
    """{id: [dossiers des cartes]} d'apres serveur.rangeExtender.id."""
    res = {}
    for dossier, d in _cartes(racine):
        i = _sous(_serveur(d), "rangeExtender", "id")
        if isinstance(i, int) and not isinstance(i, bool):
            res.setdefault(i, []).append(dossier)
    return res


def id_libre(racine):
    """Plus petit id >= 1 absent du parc."""
    pris, i = ids_pris(racine), 1
    while i in pris:
        i += 1
    return i


def _reseaux_wifi(racine):
    """[(nom, mot de passe)] de tous les reseau1/reseau2 lisibles."""
    res = []
    for _, d in _cartes(racine):
        for cle in ("reseau1", "reseau2"):
            r = _sous(_serveur(d), "wifi", cle)
            if isinstance(r, dict) and r.get("nomReseauWifi"):
                res.append((r["nomReseauWifi"], r.get("mdpWifi", "")))
    return res


def reseaux(racine):
    """Noms de reseau connus (reseau1/2 du parc), plus <hostname>-GATEWAY de chaque maitre ; sans doublon."""
    res = []
    for nom in [n for n, _ in _reseaux_wifi(racine)] + [m["hostname"] + SUFFIXE_AP for m in maitres(racine) if m["hostname"]]:
        if nom not in res:
            res.append(nom)
    return res


def base_par_defaut(racine, puce):
    """Base la plus utilisee par les cartes du cenv de cette puce (prefixe d'env) ; egalite -> ordre alphabetique ;
    "" si aucune carte. Prefixes en constante : le modele peut etre illisible sans que cela bloque la lecture du parc."""
    prefixe, ini, compte = PREFIXES[puce], fbi.lit_sections(racine), Counter()
    for env in ini.envs_cenv():
        if fbe.est_base(env) or env.split("-")[0] != prefixe:
            continue
        ext = ini.sections.get("env:" + env, {}).get("extends")
        parents = ext.morceaux[0][1] if ext and ext.morceaux else ""
        for p in (x.strip() for x in parents.split(",")):
            if p.startswith("env:") and fbe.est_base(p[4:]):
                compte[p[4:]] += 1
                break
    return min(compte, key=lambda b: (-compte[b], b)) if compte else ""


def _unique(valeurs, libelle):
    """La seule valeur de `valeurs` ; ValueError (libelle, sans valeur) si aucune ou si plusieurs."""
    distinctes = set(valeurs)
    if not distinctes:
        raise ValueError(f"mot de passe introuvable dans le parc : {libelle}")
    if len(distinctes) > 1:
        raise ValueError(f"mot de passe ambigu dans le parc : {libelle} ({len(distinctes)} valeurs differentes)")
    return distinctes.pop()


def _mdp_reseau(racine, nom):
    if nom.endswith(SUFFIXE_AP):
        aps = [_sous(_serveur(d), "rangeExtender", "AP") for _, d in _cartes(racine)]
        return _unique([a.get("mdp", "") for a in aps if isinstance(a, dict) and a.get("SSID") == nom],
                       f"reseau {nom!r} (point d'acces d'aucune carte du parc)")
    # un nom en -GATEWAY n'est jamais resolu par les reseau1/2 (copies de l'AP du maitre) : seul l'AP fait foi
    return _unique([mdp for n, mdp in _reseaux_wifi(racine) if n == nom and not n.endswith(SUFFIXE_AP)], f"reseau {nom!r}")


def secrets(racine, reseau1, reseau2):
    """{wifi1, wifi2, mqtt, ap, ftp} ; ValueError qui nomme le reseau ou la cle, jamais la valeur."""
    cartes = [_serveur(d) for _, d in _cartes(racine)]
    commun = {"mqtt": ("mqtt", "mdp"), "ap": ("rangeExtender", "AP", "mdp"), "ftp": ("serveurFTP", "mdp")}
    res = {"wifi1": _mdp_reseau(racine, reseau1), "wifi2": _mdp_reseau(racine, reseau2)}
    for cle, chemin in commun.items():
        res[cle] = _unique([v for v in (_sous(s, *chemin) for s in cartes) if isinstance(v, str) and v],
                           f"cle {cle!r} commune")
    return res
