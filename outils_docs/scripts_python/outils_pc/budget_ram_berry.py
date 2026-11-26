"""Budget de RAM Berry par puce (plan tasks/plans/binomes-berry.md, A21) : cout estime d'un env contre la table
`puces.<puce>.budget` de outils_docs/schemas/modele_persist.json. Lecture seule, rien n'est ecrit.
Partage par l'assistant persist (7900 : avertissements de l'apercu, de la creation et de la modification) et par la
page Fichiers Berry (7800 : champ `budget` de GET /etat). Ni le cenv ni le firmware ne changent.

COUT D'UN ENV (meme echelle que le budget : voir la `source` de chaque puce dans le manifeste)
  .bec des .be charges et NON solidifies : `fichiers` des blocs coches et permis pour la puce, plus les .be du
  dossier de la carte (hors autoexec.be), moins custom_berry_solidify et custom_files_exclude (assistant : listes
  generees et celles du cenv si l'env y est deja ; page 7800 : celles du cenv seules). Le .bec est la ligne DU
  fichier dans le bloc TAILLE DU BINOME (mesure_binomes.lit_taille : le reste du binome peut etre solidifie) ; un .be
  sans bloc de taille compte la moitie
  de son .be (estime : .bec / .be = 0,39 a 0,51 mesure, plan A1). Un bloc de detection (sans cle d'activation :
  qrcode, fsMqtt...) n'est pas compte.
  + FACTEUR_PERSIST x le persist compact (tel que la carte le reecrit, sans indentation).
ESP8266 : pas de Berry, budget 0 ; absent de `puces` (pas de gabarit .h) et jamais propose par les deux pages :
aucun controle. ESP32 : le budget « sans PSRAM » (toute carte ESP32 du parc derive de tasmota32-base, sans PSRAM) ;
`avec_psram` est note dans le manifeste, jamais applique.
Banc : test_budget_ram_berry.py.
"""

import json
import sys
import threading
from pathlib import Path

import assistant_persist_generation as gen
import assistant_persist_modele as apm
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
import verifie_manifeste as vm

DOSSIER_MESURE = Path(__file__).resolve().parents[1] / "berry"
# RAM Berry par octet de persist compact : 1,4 sur la cave ESP32 (gc() -12 695 o pour -8 948 o, meme code, A5), le plus
# gros ecart mesure ; 1 a 2,3 sur le P4 (A1). Le budget ESP32 du manifeste est calibre avec ce facteur : changer les deux.
FACTEUR_PERSIST = 1.4


_VERROU = threading.Lock()
_MODULE = []


def _mesure():
    # Importe une fois, sous verrou : les deux serveurs sont des ThreadingHTTPServer, deux requetes croiseraient leur sys.path
    with _VERROU:
        if not _MODULE:
            sys.path.insert(0, str(DOSSIER_MESURE))     # exception a la regle du meme dossier : mesure_binomes est dans berry/
            try:
                import mesure_binomes
            finally:
                sys.path.remove(str(DOSSIER_MESURE))
            _MODULE.append(mesure_binomes)
        return _MODULE[0]


def bec_ko(racine, chemin):
    """(Ko du .bec, estime) d'un .be du depot."""
    p = Path(racine) / chemin
    x = next((x for x in (_mesure().lit_taille(p) or {}).get("fichiers", []) if x["nom"] == p.name), None)
    if x:
        return x["bec"], False
    try:
        return p.stat().st_size / 2048, True     # moitie du .be, en Ko
    except OSError:
        return 0.0, True


def cout(racine, fichiers, persist):
    """{"ko", "bec_ko", "persist_ko", "estimes": [noms des .be sans bloc de taille]} ; fichiers = .be charges non solidifies."""
    mesures = {f: bec_ko(racine, f) for f in dict.fromkeys(fichiers)}
    bec = sum(k for k, _ in mesures.values())
    p = FACTEUR_PERSIST * len(json.dumps(persist, separators=(",", ":"), ensure_ascii=False).encode("utf-8")) / 1024
    return {"ko": round(bec + p, 1), "bec_ko": round(bec, 1), "persist_ko": round(p, 1),
            "estimes": sorted(Path(f).name for f, (_, e) in mesures.items() if e)}


def budget(modele, puce):
    """La table `budget` de la puce, ou None (puce inconnue, table absente ou sans `ram_berry_ko` numerique)."""
    b = (modele.get("puces", {}).get(puce) or {}).get("budget")
    return b if isinstance(b, dict) and type(b.get("ram_berry_ko")) in (int, float) else None


def bilan(modele, puce, c):
    """{"cout", "budget" (Ko ou None), "a_confirmer", "depasse", "message"} ; message vide sous le budget."""
    b = budget(modele, puce)
    depasse = b is not None and c["ko"] > b["ram_berry_ko"]
    a_confirmer = bool(b and b.get("a_confirmer"))
    message = "" if not depasse else (
        f"RAM Berry : env estimé à {c['ko']} Ko (code non solidifié {c['bec_ko']} Ko + persist {c['persist_ko']} Ko), "
        f"au-delà du budget de {b['ram_berry_ko']} Ko de la puce {puce}" + (" (budget à confirmer par mesure)" if a_confirmer else "")
        + " : solidifier des modules ou alléger le persist (budget : puces." + puce + ".budget de modele_persist.json)")
    return {"cout": c, "budget": b["ram_berry_ko"] if b else None, "a_confirmer": a_confirmer, "depasse": depasse,
            "message": message}


def _listes_env(racine, env):
    """(solidifies, exclus) du cenv pour un env qui y existe deja ; deux ensembles vides sinon."""
    ini = fbi.lit_sections(racine)
    if not env or env not in ini.envs_cenv():
        return set(), set()
    return tuple({e.chemin for e in fbi.resout(ini, env, o)} for o in (fbe.SOLIDIFY, fbe.EXCLUDE))


def charges(racine, modele, r, env=None, reelles_seules=False):
    """.be charges et non solidifies de l'env decrit par les Reponses r (env : celui du cenv et du dossier, s'ils existent).
    reelles_seules : listes du cenv seules (page 7800, qui montre et change ces listes) ; sinon listes generees par
    l'assistant ET listes du cenv (creation, modification : le cenv recoit les listes generees)."""
    sol, exc = _listes_env(racine, env)
    hors = sol | exc
    if not reelles_seules:
        listes = gen.listes_cenv(modele, r)
        hors |= gen._en_flash(racine, listes["solidify"]) | set(map(fbi.normalise, listes["exclude"]))
    par_bloc, _ = vm.fichiers_blocs(modele["blocs"], vm.lit_listes(racine))
    res = [f for b, coche in gen._blocs_permis(modele, r) if coche for f in par_bloc.get(b["id"], []) if f.endswith(".be")]
    dossier = fbe.dossier_carte(env) if env else None
    if dossier and (Path(racine) / dossier).is_dir():
        res += [f"{dossier}/{p.name}" for p in sorted((Path(racine) / dossier).glob("*.be")) if p.name not in fbe.FIGES]
    return [f for f in dict.fromkeys(res) if f not in hors]


def avertissement(racine, modele, r, persist, env=None):
    """Message a ajouter aux avertissements de l'assistant ('' sous le budget ou si le cout est incalculable) ;
    persist = dict ou texte JSON."""
    try:
        persist = json.loads(persist) if isinstance(persist, str) else persist
        return bilan(modele, r.puce, cout(racine, charges(racine, modele, r, env), persist))["message"]
    except Exception as e:                                 # le budget n'empeche jamais l'assistant (refus deja ailleurs)
        print(f"budget_ram_berry : calcul impossible ({type(e).__name__})", file=sys.stderr)    # type seul, jamais de valeur
        return ""


def pour_carte(racine, env):
    """Bilan de la carte `env` (persist du depot) pour la page 7800 ; None pour une base ou un persist illisible."""
    import assistant_persist_modification as apm2          # ici : apm2 -> assistant_persist_creation -> ce module
    try:
        carte = next((c for c in apm2.cartes(racine) if c["env"] == env), None)
        if carte is None:
            return None
        modele, r = apm.charge_modele(racine), apm2.reponses_de_l_env(racine, env)
        persist = json.loads((Path(racine) / carte["dossier"] / "_persist.json").read_text(encoding="utf-8"))
        return bilan(modele, r.puce, cout(racine, charges(racine, modele, r, env, reelles_seules=True), persist))
    except Exception as e:                                 # le budget ne casse jamais GET /etat
        print(f"budget_ram_berry : calcul impossible pour {env} ({type(e).__name__})", file=sys.stderr)
        return None
