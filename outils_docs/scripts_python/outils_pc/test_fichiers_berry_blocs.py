"""Banc de fichiers_berry_blocs (regroupement des fichiers d'un env par bloc du manifeste, lecture seule).

Code de sortie 0 = vert. Lit les vrais modele_persist.json et cenv du depot (jamais ecrits, jamais affiches) ;
la route GET /etat tourne devant une COPIE du depot dans un dossier temporaire. Temoins : un depot sans
manifeste, et un regroupement volontairement casse, doivent faire echouer le controle.
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import fichiers_berry_blocs as fbb
import fichiers_berry_etat as fbe
import test_fichiers_berry_creation as tfc
import test_fichiers_berry_web as tfw
import verifie_manifeste as vm

ECHECS = []
RACINE = tfc.RACINE
RIDEAU = tfc.RIDEAU
VOLETS = ["data/fs/vrFonctions.be", "data/fs/controleVoletRoulants.be"]


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def cout_volets():
    """Cout attendu du bloc voletRoulants, par mesure_binomes.cout_bloc sur SES fichiers du manifeste (suit les remesures)."""
    bloc = next(b for b in vm.lit_manifeste(RACINE) if b["id"] == "voletRoulants")
    return fbb._cout_bloc(RACINE, bloc["fichiers"])


def regroupe_volets(groupes, chemins_env):
    """Le controle du regroupement : les deux fichiers des volets de l'env sont dans UN groupe « voletRoulants », avec son cout."""
    g = [x for x in groupes if x["ids"] == ["voletRoulants"]]
    if not g or not all(f in chemins_env for f in VOLETS):
        return False
    attendu = cout_volets()
    return (all(f in g[0]["fichiers"] for f in VOLETS) and bool(g[0]["cout"]) and attendu["solidifie"] > 0
            and g[0]["cout"]["solidifie"] == attendu["solidifie"])


def test_donnees_reelles():
    groupes = fbb.groupes(RACINE)
    env = [f["chemin"] for f in fbe.etat_env(RACINE, RIDEAU)["fichiers"]]          # un env reel, lecture seule
    verifie(regroupe_volets(groupes, env), True, "env reel : vrFonctions + controleVoletRoulants sous voletRoulants, cout du bloc")
    g, attendu = next(x for x in groupes if x["ids"] == ["voletRoulants"]), cout_volets()
    verifie((g["cout"]["be"], g["cout"]["bec"], g["libelles"]), (attendu["be"], attendu["bec"], ["Volets roulants"]),
            "voletRoulants : Ko .be et .bec du bloc, libelle")
    leds = [x for x in groupes if "ruban" in x["ids"]]
    verifie([x["ids"] for x in leds], [["ruban", "ledRGB"]], "fichier dans deux blocs : un seul groupe « ruban, ledRGB »")
    verifie(sorted(leds[0]["fichiers"]), ["data/fs/controleLeds.be", "data/fs/ledsFonctions.be"], "ruban, ledRGB : ses deux fichiers")
    tous = [f for x in groupes for f in x["fichiers"]]
    verifie((len(tous) == len(set(tous)), "data/fs/configGlobal.be" in tous), (True, False),
            "un fichier dans un seul groupe ; configGlobal (socle, aucun bloc) sans groupe -> « Sans bloc »")
    verifie(all(f in {x["chemin"] for x in fbe.recense(RACINE, RIDEAU)} for f in tous if f.startswith("data/fs/")), True,
            "chaque fichier d'un groupe est un fichier recense de l'env")
    verifie(sorted(set().union(*[x.keys() for x in groupes])), ["cout", "fichiers", "ids", "libelles"],
            "seuls ids, libelles, fichiers et cout partent vers la page (pas le reste du modele)")
    blocs = vm.lit_manifeste(RACINE)
    verifie([i for x in groupes for i in x["ids"] if i in {b["id"] for b in blocs if not any(f.endswith(".be") for f in b.get("fichiers", []))}],
            [], "un bloc sans .be (i2c, sd...) n'a pas de groupe")


def test_temoins():
    with tempfile.TemporaryDirectory() as t:
        vide = tfc.depot_essai(Path(t) / "d")                                      # cenv, mais ni manifeste ni data/fs
        verifie(fbb.groupes(vide), [], "depot sans manifeste : [] (la page garde sa liste a plat), sans exception")
        env = list(VOLETS)
        verifie(regroupe_volets(fbb.groupes(vide), env), False, "TEMOIN : sans regroupement, le controle des volets echoue")
        casse = [dict(g, fichiers=[f for f in g["fichiers"] if f != VOLETS[0]]) for g in fbb.groupes(RACINE)]
        verifie(regroupe_volets(casse, env), False, "TEMOIN : vrFonctions sorti de son groupe, le controle echoue")
        verifie(regroupe_volets(fbb.groupes(RACINE), ["data/fs/x.be"]), False, "TEMOIN : fichiers absents de l'env, le controle echoue")


def test_route(t):
    b = tfw.Banc(t)
    try:
        dest = b.racine / vm.MODELE
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RACINE / vm.MODELE, dest)                                  # dans la copie seulement
        statut, etat = b.requete("GET", f"/etat?env={RIDEAU}")
        verifie(statut, 200, "GET /etat avec manifeste : 200")
        verifie(regroupe_volets(etat.get("groupes", []), [f["chemin"] for f in etat["fichiers"]]), True,
                "GET /etat : « groupes » regroupe les volets, cout du bloc")
        verifie(sorted(set().union(*[x.keys() for x in etat["groupes"]])), ["cout", "fichiers", "ids", "libelles"],
                "GET /etat : groupes sans autre champ du modele")
        dest.unlink()
        statut, etat = b.requete("GET", f"/etat?env={RIDEAU}")
        verifie((statut, etat.get("groupes")), (200, []), "GET /etat sans manifeste : 200 et groupes vide")
    finally:
        b.ferme()


def principal():
    for test in (test_donnees_reelles, test_temoins):
        try:
            test()
        except Exception as exc:
            verifie(repr(exc), "pas d'exception", test.__name__)
    with tempfile.TemporaryDirectory() as t:
        try:
            test_route(t)
        except Exception as exc:
            verifie(repr(exc), "pas d'exception", "test_route")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
