"""Banc de atelier_graphiques_televerse (liste des fichiers a televerser, drapeau « redemarrer », URL de la page Build ; A6).

Code de sortie 0 = vert. Lancer avec le Python de PlatformIO depuis la racine du depot :
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_graphiques_televerse.py
COPIE temporaire du depot (comme le banc d'ecriture) ; carte simulee par un `get` injecte qui repond a `Br path.exists`.
Aucun reseau : la sonde du port 7700 est injectee aussi.
"""

import json
import os
import re
import shutil
import sys
import tempfile
import traceback
import urllib.parse
from pathlib import Path

import atelier_graphiques_ecriture as age
import atelier_graphiques_graphiques as agg
import atelier_graphiques_televerse as agt
import test_atelier_graphiques_ecriture as tage

verifie, ECHECS = tage.verifie, tage.ECHECS
CUVE, BUREAU = tage.CUVE, tage.BUREAU
TOUS = {agt.nom_fs(f) for f in age.FICHIERS_MOTEUR}


class Carte:
    """get injecte : repond aux `Br path.exists("/<fs>")` selon `presents` ; `morte` = hors ligne."""
    def __init__(self, presents=(), morte=False):
        self.presents, self.morte, self.appels = set(presents), morte, []

    def __call__(self, ip, chemin, delai):
        self.appels.append(chemin)
        if self.morte:
            raise OSError("pas de reponse")
        cmnd = urllib.parse.unquote(chemin.split("cmnd=", 1)[1])
        m = re.fullmatch(r'Br import path path\.exists\("/([^"]+)"\)', cmnd)
        assert m, f"commande inattendue (ecriture ?) : {cmnd!r}"
        return json.dumps({"Br": "true" if m.group(1) in self.presents else "false"}).encode()


def ecrit_pages(racine, env, desc, solidifier=False):
    avant = agt.etat_avant(racine, env)
    prevu = age.prevoit(racine, env, desc, solidifier)
    return avant, age.ecrit(racine, env, desc, solidifier, prevu["empreinte"], tage.SANS_BUILD, )


def plan(racine, env, destination, ecrits, avant, carte, actif=True):
    return agt.plan(racine, env, destination, ecrits, avant, get=carte, sonde=lambda: actif)


def depot(t):
    racine = Path(t) / "depot"
    racine.mkdir()
    tage.copie(racine)
    return racine


def cuve_avec_page(t):
    racine = depot(t)
    ecrit_pages(racine, CUVE, tage.description())
    return racine


def test_description_seule(t):
    racine = cuve_avec_page(t)
    avant, ecrits = ecrit_pages(racine, CUVE, tage.description(titre="Autre"))
    carte = Carte(presents=TOUS)
    p = plan(racine, CUVE, "pages", ecrits, avant, carte)
    verifie((p["fichiers"], p["redemarrer"], p["verification"]), (["pages_graphiques.json"], 0, "carte"),
            "description seule : liste reduite a ce fichier, redemarrer=0")
    verifie(len(carte.appels) > 0, True, "description seule : presence du moteur verifiee sur la carte")


def test_premiere_page(t):
    racine = depot(t)
    avant, ecrits = ecrit_pages(racine, BUREAU, tage.description())
    p = plan(racine, BUREAU, "pages", ecrits, avant, Carte(presents=["autoexec.be"]))
    verifie(("pages_graphiques.json" in p["fichiers"], "autoexec.be" in p["fichiers"], p["redemarrer"]), (True, True, 1),
            "premiere page : description et autoexec, redemarrer=1")
    verifie({"pagesGraphiques.be", "sd/js/pages_graphiques.js", "sd/html/pages_graphiques.html"} <= set(p["fichiers"]), True,
            "premiere page : fichiers du moteur et de la page entres dans le FS")
    verifie(len(p["fichiers"]) == len(set(p["fichiers"])), True, "premiere page : aucun doublon")


def test_absent_de_la_carte(t):
    racine = cuve_avec_page(t)
    avant, ecrits = ecrit_pages(racine, CUVE, tage.description(titre="Autre"))
    p = plan(racine, CUVE, "pages", ecrits, avant, Carte(presents=TOUS - {"sd/js/pages_graphiques.js"}))
    verifie(p["fichiers"], ["pages_graphiques.json", "sd/js/pages_graphiques.js"], "fichier du moteur absent de la carte : dans la liste")
    p = plan(racine, CUVE, "pages", ecrits, avant, Carte(presents=TOUS))
    verifie(p["fichiers"], ["pages_graphiques.json"], "moteur present sur la carte : pas dans la liste")


def test_hors_ligne(t):
    racine = cuve_avec_page(t)
    avant, ecrits = ecrit_pages(racine, CUVE, tage.description(titre="Autre"))
    p = plan(racine, CUVE, "pages", ecrits, avant, Carte(morte=True))
    verifie((p["fichiers"], p["verification"], bool(p["notes"])), (["pages_graphiques.json"], "hors_ligne", True),
            "carte hors ligne : pas de verification, dite")
    avant, ecrits = ecrit_pages(racine, BUREAU, tage.description())
    p = plan(racine, BUREAU, "pages", ecrits, avant, Carte(morte=True))
    verifie(("sd/js/pages_graphiques.js" in p["fichiers"], p["verification"]), (True, "hors_ligne"),
            "carte hors ligne : les fichiers entres dans le FS restent listes")


def test_graphiques(t):
    racine = depot(t)
    persist = racine / tage.fbe.dossier_carte(CUVE) / "_persist.json"
    persist.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tage.DEPOT / tage.fbe.dossier_carte(CUVE) / "_persist.json", persist)    # historique ON + adresse de la carte
    d = {"operation": "ajoute", "base": "depot",
         "graphique": {"type": "courbe", "titre": "V", "series": ["sensorsCuve.niveauCuve.volume"]}}
    muette = Carte(morte=True)
    avant = agt.etat_avant(racine, CUVE)
    ecrits = agg.ecrit(racine, CUVE, d, agg.prevoit(racine, CUVE, d, get=muette)["empreinte"], tage.SANS_BUILD, get=muette)
    p = plan(racine, CUVE, "graphiques", ecrits, avant, Carte(presents=TOUS - {"sd/js/graphiques_moteur.js"}))
    verifie((p["fichiers"], p["redemarrer"]), (["graphiques.json", "sd/js/graphiques_moteur.js"], 0),
            "destination graphiques : graphiques.json + moteur absent de la carte, redemarrer=0")


def test_url_et_build(t):
    u = agt.url("tasmota32s3-x", ["pages_graphiques.json", "sd/js/a b.js"], 1)
    q = urllib.parse.urlsplit(u)
    verifie((u.startswith("http://127.0.0.1:7700/?"), urllib.parse.parse_qs(q.query)),
            (True, {"env": ["tasmota32s3-x"], "depuis": ["atelier"], "fichiers": ["pages_graphiques.json,sd/js/a b.js"],
                    "redemarrer": ["1"]}), "URL : env, depuis=atelier, fichiers, redemarrer")
    verifie((" " in u, "/" in q.query), (False, False), "URL : valeurs encodees")
    racine = depot(t)
    avant, ecrits = ecrit_pages(racine, BUREAU, tage.description())
    p = plan(racine, BUREAU, "pages", ecrits, avant, Carte(), actif=False)
    verifie((p["build_actif"], "annuaire" in p["message"]), (False, True), "page Build arretee : message « lancer par l'annuaire »")
    verifie(agt.build_actif(1), False, "sonde reelle : port 1 muet")


def test_nom_fs(t):
    verifie((agt.nom_fs("data/fs/x.be"), agt.nom_fs("data/sd/js/x.js")), ("x.be", "sd/js/x.js"), "nom_fs : chemins du FS de la carte")
    try:
        agt.nom_fs("platformio.ini")
        verifie(True, False, "nom_fs : refuse hors data")
    except ValueError:
        verifie(True, True, "nom_fs : refuse hors data")


TESTS = [test_description_seule, test_premiere_page, test_absent_de_la_carte, test_hors_ligne, test_graphiques, test_url_et_build,
         test_nom_fs]

if __name__ == "__main__":
    for test in TESTS:
        print(f"--- {test.__name__}")
        with tempfile.TemporaryDirectory() as t:
            os.environ["OUTILS_TASMOTA_DOSSIER"] = os.path.join(t, "outils")
            try:
                test(t)
            except Exception as e:
                traceback.print_exc()
                print(f"KO   {test.__name__} : {type(e).__name__} : {e}")
                ECHECS.append(test.__name__)
    print(f"\n{len(ECHECS)} echec(s)" + (" : " + ", ".join(ECHECS) if ECHECS else " : VERT"))
    sys.exit(1 if ECHECS else 0)
