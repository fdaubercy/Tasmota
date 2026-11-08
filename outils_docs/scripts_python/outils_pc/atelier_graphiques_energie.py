#!/usr/bin/env python3
"""Destination « Energie » de l'atelier : la page /energie du differentiel (plan energie-atelier A4, spec 2026-11-08).

Seul `data/<lieu>/<carte>/energie_page.json` s'ecrit (ni autoexec ni cenv : la page existe deja sur la carte). Le fichier est
ecrit en JSON COMPACT UTF-8 : la carte compare sa TAILLE BRUTE a 4 096 octets (energieFonctions). Le dossier de la carte arrive
a la racine du FS, puis gestionFileFolder::listeEtRepartitLesFichiers deplace les .json vers /json/ (comme pages_graphiques.json).

Une « carte Energie » est un env du cenv dont le FS embarque energie.js (liste page_energie non exclue) : le differentiel seul.
Lecture de la carte en LECTURE SEULE (`/energie?f=description`, `Status 10`), par un `get` injecte. L'ANCIEN firmware ne connait pas
`f=description` et rend la page HTML en 200 : un 200 qui n'est pas du JSON = `firmware_requis` (Televerser bloque).
Refus : ValueError (400), LookupError (404), RuntimeError (409 : build, empreinte perimee).
"""

import difflib
import json
from pathlib import Path

import atelier_energie_description as aed
import atelier_graphiques_ecriture as age
import atelier_graphiques_series as ags
import atelier_graphiques_televerse as agt
import build_ota_http
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi

FICHIER = "energie_page.json"
PAGE = ("data/sd/js/energie.js", "data/sd/html/energie.html", "data/sd/css/energie.css")   # toujours joints au televersement
NOM_PAGE = Path(PAGE[0]).name
SONDE = "/energie?f=description"
MOTIF_FIRMWARE = "firmware d'avant la page Energie pilotee par description : compilez et envoyez le firmware du differentiel par la page Build"


def page_energie(ini, env):
    """Vrai si le FS de l'env embarque energie.js (liste page_energie non exclue)."""
    return NOM_PAGE not in {Path(x.chemin).name for x in fbi.resout(ini, env, fbe.EXCLUDE)}


def _env(racine, env):
    ini = fbi.lit_sections(racine)
    if env not in [e["nom"] for e in fbe.envs_proposes(racine) if e["famille"] == "cartes"] or not page_energie(ini, env):
        raise LookupError(f"env inconnu ou sans page Energie : {env!r}")
    return fbe.dossier_carte(env) + "/" + FICHIER


def compact(d):
    return json.dumps(d, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def description_de(racine, env):
    """{description (None si aucune ou refusee), erreur} du depot."""
    octets = age._lit(racine, _env(racine, env))
    if octets is None:
        return {"description": None, "erreur": ""}
    try:
        d = json.loads(octets.decode("utf-8"))
    except (ValueError, RecursionError) as e:
        return {"description": None, "erreur": f"{FICHIER} illisible : {e}"}
    motifs = aed.valide(d)
    return {"description": None, "erreur": f"{FICHIER} invalide : " + " ; ".join(motifs)} if motifs else {"description": d, "erreur": ""}


def etat_carte(racine, env, *, get=None):
    """{description (None : absente, refusee ou non lue), firmware_requis, motif} ; lecture seule."""
    ip = ags._carte(racine, env)[0]
    res = {"description": None, "firmware_requis": False, "motif": ""}
    if not ip:
        res["motif"] = "description de la carte non verifiee (adresse de la carte inconnue)"
        return res
    try:
        corps = (get or build_ota_http._get)(ip, SONDE, ags.DELAI)
    except Exception as e:                  # hors ligne, 404 (aucune description), 413 (trop grosse)
        texte = str(e)
        if "HTTP 404" not in texte:
            res["motif"] = "description de la carte trop grosse (HTTP 413)" if "HTTP 413" in texte else f"description de la carte non verifiee ({texte})"
        return res
    try:
        d = json.loads(corps.decode("utf-8"))
    except (ValueError, RecursionError):
        res["firmware_requis"], res["motif"] = True, MOTIF_FIRMWARE
        return res
    motifs = aed.valide(d)
    if motifs:
        res["motif"] = "description de la carte invalide : " + " ; ".join(motifs)
    else:
        res["description"] = d
    return res


def composition(racine, env, *, get=None):
    """{etat: identique|differente|non_verifiee, motif, diff, depot, carte, carte_valide, firmware_requis} : carte et depot comparees."""
    depot, carte = description_de(racine, env), etat_carte(racine, env, get=get)
    res = {"etat": "non_verifiee", "motif": depot["erreur"] or carte["motif"], "diff": "", "depot": depot["description"],
           "carte": carte["description"], "carte_valide": carte["description"] is not None, "firmware_requis": carte["firmware_requis"]}
    if carte["motif"] and not carte["description"]:
        return res
    norme = lambda d: json.dumps(d, sort_keys=True, ensure_ascii=False, indent=1)
    if norme(depot["description"]) == norme(carte["description"]):
        res["etat"] = "identique"
    else:
        res["etat"] = "differente"
        res["diff"] = "\n".join(difflib.unified_diff(norme(depot["description"]).splitlines(), norme(carte["description"]).splitlines(),
                                                      "depot", "carte", lineterm=""))
    return res


def _calcule(racine, env, description):
    rel = _env(racine, env)
    motifs = aed.valide(description)
    if motifs:
        raise ValueError("description invalide : " + " ; ".join(motifs))
    octets = age._lit(racine, rel)
    nouveau = compact(description)
    return {rel: octets}, ({rel: nouveau} if nouveau != octets else {})


def prevoit(racine, env, description):
    """{"fichiers": [{chemin, avant, apres}], "empreinte"} sans rien ecrire."""
    lus, apres = _calcule(racine, env, description)
    return {"fichiers": age._fichiers(lus, apres), "empreinte": age._empreinte(lus, [env, description])}


def ecrit(racine, env, description, empreinte_lue, builds_en_cours):
    """Chemins ecrits. RuntimeError : build (ou indetectable), fichier ou demande changes depuis le diff."""
    age._refuse_build(builds_en_cours)
    lus, apres = _calcule(racine, env, description)
    if age._empreinte(lus, [env, description]) != empreinte_lue:
        raise RuntimeError(f"{FICHIER} modifie depuis le diff : refaire le diff, rien n'est ecrit")
    return age._ecrit_transaction(racine, apres, "atelier-energie") if apres else []


def plan(racine, env, *, get=None):
    """{fichiers, redemarrer: 0, notes, firmware_requis, url} : la description et la page, toujours (pas de comparaison sur la carte)."""
    fichiers = [FICHIER] if (Path(racine) / _env(racine, env)).is_file() else []
    fichiers += [agt.nom_fs(f) for f in PAGE]
    etat = etat_carte(racine, env, get=get)
    notes = [etat["motif"]] if etat["motif"] else []
    return {"fichiers": fichiers, "redemarrer": 0, "notes": notes, "firmware_requis": etat["firmware_requis"],
            "url": None if etat["firmware_requis"] else agt.url(env, fichiers, False)}


def catalogue(racine, env, *, get=None):
    """{sources, styles, origine}. Sources : les champs `direct` du bloc ENERGY de `Status 10` (sinon la liste de la spec §2,
    origine « defaut »), les totaux et les echelles en flash."""
    _env(racine, env)
    champs, origine = aed.CHAMPS_DIRECT, "defaut"
    ip = ags._carte(racine, env)[0]
    if ip:
        try:
            sns = json.loads((get or build_ota_http._get)(ip, "/cm?cmnd=Status%2010", ags.DELAI).decode("utf-8", "replace")).get("StatusSNS") or {}
            presents = [c for c in aed.CHAMPS_DIRECT if c in (sns.get("ENERGY") or {})]
            if presents:
                champs, origine = presents, "carte"
        except Exception:                   # carte muette ou reponse illisible : la liste de la spec
            pass
    grandeurs = ("kWh", "euros")
    sources = [{"direct": c} for c in champs] + [{"total": p, "grandeur": g} for p in ("jour", "mois", "an") for g in grandeurs] + \
              [{"flash": "minutes"}] + [{"flash": p, "grandeur": g} for p in ("heure", "jour", "mois", "an") for g in grandeurs]
    return {"sources": sources, "styles": list(aed.TYPES), "origine": origine}
