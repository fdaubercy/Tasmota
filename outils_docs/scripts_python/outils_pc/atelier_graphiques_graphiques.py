#!/usr/bin/env python3
"""Destination « Graphiques » de l'atelier : la cle `graphiques` de data/<lieu>/<carte>/graphiques.json (plan atelier-destinations A4).

Seule cette cle change ; `affichage`, `groupes`... et l'ordre des cles sont gardes, le fichier est reecrit en indentation
a tabulation (format du depot). Un graphique ecrit par l'atelier est toujours de forme atelier (`"moteur": "pages"`,
cle facultative `calculees` propre au graphique), meme pour les 4 styles communs ; les graphiques de forme actuelle deja
presents sont recopies tels quels. Fichier absent : la carte lit {} (graphiquesFonctions::lisReglages), donc un fichier
minimal {"graphiques": [...]} est cree.

Demande : {operation: ajoute|remplace|retire, graphique, index, attendu (remplace, retire), base: depot|carte}.
Composition de la carte (spec §4.3, §7.6) : `etat_carte` lit /json/graphiques.json (par /ufsu, apres path.exists) en LECTURE SEULE et compare la cle
`graphiques` au depot (JSON relu, cles triees). Composition differente : `base` est OBLIGATOIRE (depot = garder celle du
depot, la carte la perdra a l'envoi ; carte = partir de celle de la carte, validee ici). Jamais d'ecrasement implicite.
Refus : ValueError (400), LookupError (404), RuntimeError (409 : build, empreinte perimee).
"""

import difflib
import json
from pathlib import Path

import atelier_graphiques_description as agd
import atelier_graphiques_ecriture as age
import atelier_graphiques_series as ags
import atelier_graphiques_televerse as agt
import build_ota_http
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi

FICHIER = "graphiques.json"
MAX_GRAPHIQUES, MAX_CORPS = agd.BORNES["graphiques"], agd.BORNES["octets"]   # graphiquesFonctions.MAX_GRAPHIQUES / MAX_CORPS
OPERATIONS = ("ajoute", "remplace", "retire")


def motifs_graphique(g, numero=1):
    """Motifs de refus d'un graphique de forme atelier, par le validateur des pages (une page fictive le porte)."""
    if not isinstance(g, dict) or g.get("moteur") != "pages":
        return [f"graphique {numero} : objet avec \"moteur\": \"pages\" attendu"]
    page = {"id": "x", "titre": "x", "graphiques": [{k: v for k, v in g.items() if k not in ("moteur", "calculees")}]}
    d = {"version": 1, "pages": [page]}
    if "calculees" in g:
        d["calculees"] = g["calculees"]
    return [m.replace("page 1 graphique 1", f"graphique {numero}") for m in agd.valide(d)]


def motifs_bornes(c):
    """Bornes de la carte seules : nombre de graphiques et taille du corps compact."""
    m = [f"composition : {len(c)} graphiques > {MAX_GRAPHIQUES}"] if len(c) > MAX_GRAPHIQUES else []
    if len(json.dumps(c, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) > MAX_CORPS:
        m.append(f"composition : plus de {MAX_CORPS} octets")
    return m


def motifs_composition(c):
    """Bornes et validation des graphiques de forme atelier ; ceux de forme actuelle sont laisses a la carte."""
    if not isinstance(c, list) or not c:
        return ["composition : liste non vide attendue"]
    m = motifs_bornes(c)
    for i, g in enumerate(c, 1):
        if not isinstance(g, dict):
            m.append(f"graphique {i} : objet attendu")
        elif "moteur" in g:
            m += motifs_graphique(g, i)
    return m


def _arrondi(x):
    """Berry (json.dump) arrondit les reels a 6 chiffres (%g) : la carte rend 1234.57 pour 1234.5678. 5.0 et 5 : meme nombre."""
    if isinstance(x, float):
        v = float("%g" % x)
        return int(v) if v.is_integer() else v
    if isinstance(x, list):
        return [_arrondi(v) for v in x]
    return {k: _arrondi(v) for k, v in x.items()} if isinstance(x, dict) else x


def _norme(c):
    return json.dumps(_arrondi(c), sort_keys=True, ensure_ascii=False, indent=1)


def _depot(racine, env):
    """(rel, octets|None, reglages dict, composition|None) du depot."""
    rel = fbe.dossier_carte(env) + "/" + FICHIER
    octets = age._lit(racine, rel)
    if octets is None:
        return rel, None, {}, None
    try:
        reglages = json.loads(octets.decode("utf-8"))
    except ValueError as e:
        raise ValueError(f"{rel} illisible : {e}") from e
    if not isinstance(reglages, dict):
        raise ValueError(f"{rel} : objet JSON attendu")
    return rel, octets, reglages, reglages.get("graphiques")


def etat_carte(racine, env, *, get=None):
    """{etat: identique|differente|non_verifiee, motif, diff, depot, carte, carte_valide, carte_motifs, historique} ; lecture seule."""
    depot = _depot(racine, env)[3]
    res = {"etat": "non_verifiee", "motif": "", "diff": "", "depot": depot, "carte": None, "carte_valide": False,
           "carte_motifs": [], "historique": age.historique(racine, env)}
    ip = ags._carte(racine, env)[0]
    if not ip:
        res["motif"] = "composition de la carte non verifiee (adresse de la carte inconnue)"
        return res
    try:
        get = get or build_ota_http._get
        # /json/graphiques.json repond 404 (mesure du 2026-11-06) : le contenu passe par /ufsu, qui ne repond pas pour un fichier absent
        lu = ({} if not agt.existe_sur_carte(ip, "json/graphiques.json", get) else
              json.loads(get(ip, "/ufsu?dir=0&download=/json/graphiques.json", ags.DELAI).decode("utf-8", "replace")))
        if not isinstance(lu, dict):
            raise ValueError("reponse inattendue")
    except Exception as e:                  # hors ligne, 404, JSON tronque : meme verdict, jamais d'ecriture
        res["motif"] = f"composition de la carte non verifiee ({e})"
        return res
    carte = res["carte"] = lu.get("graphiques")
    if _norme(carte) == _norme(depot):
        res["etat"] = "identique"
    else:
        res["etat"] = "differente"
        res["diff"] = "\n".join(difflib.unified_diff(_norme(depot).splitlines(), _norme(carte).splitlines(),
                                                      "depot", "carte", lineterm=""))
    res["carte_motifs"] = motifs_composition(carte) if carte is not None else ["la carte n'a pas de composition"]
    res["carte_valide"] = not res["carte_motifs"]
    return res


def _base(etat, base, depot):
    """Composition de depart selon le choix `base` (spec §4.3) ; refus si la carte differe sans choix."""
    if etat["etat"] == "differente" and base is None:
        raise ValueError("la composition de la carte differe de celle du depot : choisir base=carte (partir de celle de "
                         "la carte) ou base=depot (celle de la carte sera perdue a l'envoi)")
    if base != "carte":
        return depot
    if etat["etat"] == "non_verifiee":
        raise ValueError("base=carte indisponible : " + etat["motif"])
    if not etat["carte_valide"]:
        raise ValueError("base=carte indisponible : " + " ; ".join(etat["carte_motifs"]))
    return etat["carte"]


def _calcule(racine, env, demande, get):
    """(lus, apres {rel: octets}, signaux)."""
    if env not in age._envs(fbi.lit_sections(racine)) or fbe.est_base(env):
        raise LookupError(f"env inconnu, non ESP32 ou de base : {env!r}")
    if not age.historique(racine, env):
        raise ValueError(f"{env} : carte sans historique (diverses.historique.activation != ON dans son _persist.json), "
                         "pas de page /graphiques")
    op, base, index, g = demande.get("operation"), demande.get("base"), demande.get("index"), demande.get("graphique")
    if op not in OPERATIONS:
        raise ValueError(f"operation : {' | '.join(OPERATIONS)} attendu")
    if base not in (None, "depot", "carte"):
        raise ValueError("base : depot ou carte attendu")
    rel, octets, reglages, depot = _depot(racine, env)
    persist = fbe.dossier_carte(env) + "/_persist.json"
    etat = etat_carte(racine, env, get=get)
    lus = {rel: octets, persist: age._lit(racine, persist),         # la composition de la carte entre dans l'empreinte
           "carte:graphiques": _norme(etat["carte"]).encode("utf-8") if etat["etat"] != "non_verifiee" else b"-"}
    comp = [dict(x) if isinstance(x, dict) else x for x in (_base(etat, base, depot) or [])]
    if op == "ajoute":
        index = len(comp)
        comp.append(None)
    elif not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(comp):
        raise ValueError(f"index : entier entre 0 et {len(comp) - 1} attendu" if comp else "index : aucune composition")
    motifs = []
    if op != "ajoute":                    # le rang ne suffit pas : le graphique a ce rang doit etre celui que la page croit (A11)
        if not isinstance(demande.get("attendu"), dict):
            raise ValueError(f"{op} : `attendu` (le graphique tel que la page le connait) obligatoire")
        if _norme(comp[index]) != _norme(demande["attendu"]):
            raise RuntimeError("index : le graphique a ce rang a change depuis son ecriture, rien n'est remplace ni retire")
    if op == "retire":
        del comp[index]
    else:
        if not isinstance(g, dict) or g.get("moteur", "pages") != "pages":
            raise ValueError("graphique : objet de forme atelier attendu (\"moteur\": \"pages\")")
        comp[index] = {"moteur": "pages", **{k: v for k, v in g.items() if k != "moteur"}}
        motifs += motifs_graphique(comp[index], index + 1)       # seul le graphique ecrit est valide
        if g.get("type") == "liquide" and age.LIQUIDFILL in {
                Path(x.chemin).name for x in fbi.resout(fbi.lit_sections(racine), env, fbe.EXCLUDE)}:
            raise ValueError(f"style liquide refuse sur {env} : {age.LIQUIDFILL} est exclu de son FS (liste page_cuve)")
    motifs += motifs_bornes(comp)                       # un retrait n'est refuse que s'il fait depasser les bornes
    if motifs:
        raise ValueError("composition invalide : " + " ; ".join(motifs))
    if comp:
        reglages["graphiques"] = comp
    else:
        reglages.pop("graphiques", None)                           # comme Retablir sur la carte
    nouveau = (json.dumps(reglages, ensure_ascii=False, indent="\t") + "\n").encode("utf-8")
    apres = {rel: nouveau} if nouveau != octets else {}
    return lus, apres, ["FS de la carte a reconstruire et televerser"] if apres else []


def prevoit(racine, env, demande, *, get=None):
    """{"fichiers": [{chemin, avant, apres}], "empreinte", "signaux"} sans rien ecrire."""
    lus, apres, signaux = _calcule(racine, env, demande, get)
    return {"fichiers": age._fichiers(lus, apres), "signaux": signaux, "empreinte": age._empreinte(lus, [env, demande])}


def index_ecrit(racine, env, demande):
    """(rang, graphique) que `demande` vient d'ecrire dans la composition, (None, None) pour un retrait : la page les retient,
    le graphique comme temoin `attendu` d'un futur « remplace »."""
    comp = _depot(racine, env)[3] or []
    rang = demande.get("index") if demande.get("operation") == "remplace" else len(comp) - 1 if demande.get("operation") == "ajoute" else None
    return (rang, comp[rang]) if rang is not None and 0 <= rang < len(comp) else (None, None)


def ecrit(racine, env, demande, empreinte_lue, builds_en_cours, *, get=None):
    """Chemins ecrits. RuntimeError : build, ou depot / composition de la carte / demande changes depuis le diff."""
    age._refuse_build(builds_en_cours)
    lus, apres, _ = _calcule(racine, env, demande, get)
    if age._empreinte(lus, [env, demande]) != empreinte_lue:
        raise RuntimeError("graphiques.json, persist ou composition de la carte modifies depuis le diff : refaire le diff, rien n'est ecrit")
    return age._ecrit_transaction(racine, apres, "atelier-graphiques-page") if apres else []
