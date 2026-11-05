"""Banc de atelier_graphiques_graphiques (destination « Graphiques » : cle `graphiques` de graphiques.json, plan A4).

Code de sortie 0 = vert. Lancer avec le Python de PlatformIO depuis la racine du depot :
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_graphiques_graphiques.py
Copies temporaires du depot (copie() du banc A6 + le graphiques.json reel de la cuve) ; la carte est un `get` injecte
(aucune connexion reseau, aucune ecriture vers une carte).
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import atelier_graphiques_graphiques as agg
import test_atelier_graphiques_ecriture as tage

verifie, refuse, ECHECS = tage.verifie, tage.refuse, tage.ECHECS
CUVE, BUREAU, SANS_BUILD = tage.CUVE, tage.BUREAU, tage.SANS_BUILD
ACTUEL = {"titre": "Cuve", "periode": "jour", "type": "courbe", "series": ["sensorsCuve.niveauCuve.volume"]}   # forme actuelle


def atelier(titre="Volume", **plus):
    return {"moteur": "pages", "type": "deux-axes", "titre": titre, "periode": "jour", "largeur": "pleine",
            "series": [{"chemin": "sensorsCuve.niveauCuve.volume", "libelle": "Vol", "unite": "L", "couleur": "#ff0000"}], **plus}


def fichier(racine, env=CUVE):
    return Path(racine) / tage.fbe.dossier_carte(env) / "graphiques.json"


def prepare(racine, graphiques=None, reel=True):
    """graphiques.json de la cuve : le vrai (sans cle graphiques), plus `graphiques` si donne."""
    f = fichier(racine)
    if reel:
        shutil.copy2(tage.DEPOT / tage.fbe.dossier_carte(CUVE) / "graphiques.json", f)
        if graphiques is not None:
            d = json.loads(f.read_text(encoding="utf-8"))
            d["graphiques"] = graphiques
            f.write_text(json.dumps(d, ensure_ascii=False, indent="\t") + "\n", encoding="utf-8")


def carte(composition=None, mort=False):
    """`get` simulant la carte : /json/graphiques.json avec les reglages et `composition`."""
    appels = []

    def get(ip, chemin, delai):
        appels.append(chemin)
        if mort:
            raise OSError("pas de reponse")
        d = {"affichage": {}, "groupes": {}}
        if composition is not None:
            d["graphiques"] = composition
        return json.dumps(d).encode()
    get.appels = appels
    return get


def ecrit(racine, demande, get=None, env=CUVE):
    p = agg.prevoit(racine, env, demande, get=get)
    return agg.ecrit(racine, env, demande, p["empreinte"], SANS_BUILD, get=get)


def ajoute(g, **plus):
    return {"operation": "ajoute", "graphique": g, **plus}


def test_ajout_garde_le_reste(racine):
    prepare(racine)
    avant = fichier(racine).read_bytes()
    ecrit(racine, ajoute(atelier()))
    apres = fichier(racine).read_bytes()
    d, d0 = json.loads(apres), json.loads(avant)
    verifie(d["graphiques"], [atelier()], "ajout : graphique de forme atelier (moteur pages) ecrit")
    verifie({k: v for k, v in d.items() if k != "graphiques"}, d0, "ajout : autres cles intactes")
    verifie(list(d), list(d0) + ["graphiques"], "ajout : ordre des cles gardees, `graphiques` en fin")
    # le texte avant la cle ajoutee est le meme octet pour octet (indentation a tabulation)
    verifie(apres[:len(avant) - 3] == avant[:-3], True, "ajout : forme du texte conservee (tabulations) jusqu'a la cle ajoutee")


def test_ajout_sans_moteur_et_calculees(racine):
    prepare(racine)
    g = atelier(series=["calc:x"], calculees={"x": {"nature": "historique", "formule": "a.b + c.d"}})
    del g["moteur"]
    ecrit(racine, ajoute(g))
    lu = json.loads(fichier(racine).read_text(encoding="utf-8"))["graphiques"][0]
    verifie((lu["moteur"], list(lu)[0], "calculees" in lu), ("pages", "moteur", True), "moteur pose d'office, calculees gardees")
    refuse(lambda: agg.prevoit(racine, CUVE, ajoute({**g, "series": ["calc:inconnue"]})), ValueError, "calculee inconnue refusee", "calculee")


def test_quatre_styles_communs_en_forme_atelier(racine):
    prepare(racine)
    for style in ("courbe", "barres", "escalier", "aire"):
        ecrit(racine, ajoute(atelier(style, type=style)))
    verifie([g["type"] for g in json.loads(fichier(racine).read_text(encoding="utf-8"))["graphiques"]],
            ["courbe", "barres", "escalier", "aire"], "4 styles communs : tous en forme atelier")


def test_forme_actuelle_intacte(racine):
    prepare(racine, [ACTUEL, {"titre": "P", "type": "barres", "series": "autres"}])
    ecrit(racine, ajoute(atelier()))
    comp = json.loads(fichier(racine).read_text(encoding="utf-8"))["graphiques"]
    verifie(comp[:2], [ACTUEL, {"titre": "P", "type": "barres", "series": "autres"}], "forme actuelle : graphiques existants intacts")
    verifie(len(comp), 3, "forme actuelle : le graphique atelier est ajoute apres")
    ecrit(racine, {"operation": "remplace", "index": 2, "graphique": atelier("Autre")})
    comp = json.loads(fichier(racine).read_text(encoding="utf-8"))["graphiques"]
    verifie((comp[2]["titre"], len(comp)), ("Autre", 3), "remplace : le graphique est remplace en place")


def test_retire(racine):
    prepare(racine, [ACTUEL, atelier()])
    ecrit(racine, {"operation": "retire", "index": 1})
    verifie(json.loads(fichier(racine).read_text(encoding="utf-8"))["graphiques"], [ACTUEL], "retrait d'un graphique atelier")
    ecrit(racine, {"operation": "retire", "index": 0})
    d = json.loads(fichier(racine).read_text(encoding="utf-8"))
    verifie("graphiques" in d, False, "retrait du dernier : la cle disparait (comme Retablir), le reste est garde")
    verifie("affichage" in d and "groupes" in d, True, "retrait du dernier : affichage et groupes gardes")
    refuse(lambda: agg.prevoit(racine, CUVE, {"operation": "retire", "index": 0}), ValueError, "retrait sans composition : refus", "index")


def test_fichier_absent(racine):
    prepare(racine, reel=False)
    verifie(fichier(racine).exists(), False, "depart : pas de graphiques.json")
    p = agg.prevoit(racine, CUVE, ajoute(atelier()))
    verifie((len(p["fichiers"]), p["fichiers"][0]["avant"]), (1, None), "fichier absent : diff = creation")
    ecrit(racine, ajoute(atelier()))
    verifie(json.loads(fichier(racine).read_text(encoding="utf-8")), {"graphiques": [atelier()]}, "fichier absent : cree minimal")


def test_refus(racine):
    prepare(racine)
    refuse(lambda: agg.prevoit(racine, BUREAU, ajoute(atelier())), ValueError, "carte sans historique : refus", "historique")
    refuse(lambda: agg.prevoit(racine, "tasmota32-base", ajoute(atelier())), LookupError, "env de base : refus")
    refuse(lambda: agg.prevoit(racine, CUVE, ajoute(atelier(type="nimporte"))), ValueError, "style inconnu : refus", "style")
    refuse(lambda: agg.prevoit(racine, CUVE, ajoute(atelier(moteur="autre"))), ValueError, "moteur autre : refus", "atelier")
    refuse(lambda: agg.prevoit(racine, CUVE, {"operation": "x"}), ValueError, "operation inconnue : refus", "operation")
    refuse(lambda: agg.prevoit(racine, CUVE, ajoute(atelier(), base="autre")), ValueError, "base inconnue : refus", "base")
    refuse(lambda: agg.prevoit(racine, CUVE, ajoute(atelier(series=[f"a.s{i}" for i in range(13)]))), ValueError,
           "13 series : refus", "series")
    prepare(racine, [ACTUEL] * 8)
    refuse(lambda: agg.prevoit(racine, CUVE, ajoute(atelier())), ValueError, "9 graphiques : refus", "> 8")
    prepare(racine, [{**ACTUEL, "titre": "x" * 40}] * 3)
    gros = atelier(series=[f"capteur{i}.valeur.numero{j}" for i, j in zip(range(12), range(12))])
    gros["titre"] = "t" * 60
    comp = [{**gros, "titre": f"T{i}", "calculees": {f"c{k}": {"nature": "historique", "formule": "a.b + c.d + e.f + g.h"}
                                                  for k in range(14)}} for i in range(7)]
    prepare(racine, [{"moteur": "pages", **{k: v for k, v in c.items() if k != "moteur"}} for c in comp])
    refuse(lambda: agg.prevoit(racine, CUVE, ajoute(atelier())), ValueError, "corps > 8192 octets : refus", "octets")


def test_liquide(racine):
    prepare(racine)
    ecrit(racine, ajoute(atelier(type="liquide")))
    verifie(True, True, "liquide accepte sur la cuve (embarque liquidfill)")
    cave = "tasmota32s3-cave-serveur-rly"           # historique ON, liquidfill exclu de son FS (liste page_cuve)
    ini = tage.fbi.lit_sections(racine)
    verifie(agg.age.LIQUIDFILL in {Path(x.chemin).name for x in tage.fbi.resout(ini, cave, tage.fbe.EXCLUDE)}, True,
            "depart : la cave exclut liquidfill")
    refuse(lambda: agg.prevoit(racine, cave, ajoute(atelier(type="liquide"))), ValueError, "liquide refuse sur la cave", "liquide")
    agg.prevoit(racine, cave, ajoute(atelier(type="courbe")))
    verifie(True, True, "courbe acceptee sur la cave")


def test_empreinte_et_build(racine):
    prepare(racine)
    d = ajoute(atelier())
    p = agg.prevoit(racine, CUVE, d)
    fichier(racine).write_text(fichier(racine).read_text(encoding="utf-8").replace("Cuve", "Cuve2", 1), encoding="utf-8")
    refuse(lambda: agg.ecrit(racine, CUVE, d, p["empreinte"], SANS_BUILD), RuntimeError, "empreinte perimee : refus", "modifies")
    p = agg.prevoit(racine, CUVE, d)
    avant = tage.instantane(racine)
    refuse(lambda: agg.ecrit(racine, CUVE, d, p["empreinte"], lambda: ["pio run"]), RuntimeError, "build en cours : refus", "build")
    refuse(lambda: agg.ecrit(racine, CUVE, d, p["empreinte"], lambda: None), RuntimeError, "build indetectable : refus", "build")
    tage.meme_etat(racine, avant, "refus : rien n'est ecrit")
    refuse(lambda: agg.ecrit(racine, CUVE, ajoute(atelier("Autre")), p["empreinte"], SANS_BUILD), RuntimeError,
           "demande differente de celle du diff : refus", "modifies")


def test_etat_carte(racine):
    prepare(racine, [ACTUEL])
    e = agg.etat_carte(racine, CUVE, get=carte([ACTUEL]))
    verifie(e["etat"], "identique", "carte identique")
    e = agg.etat_carte(racine, CUVE, get=carte([{"series": ACTUEL["series"], "periode": "jour", "type": "courbe", "titre": "Cuve"}]))
    verifie(e["etat"], "identique", "ordre des cles ignore (cles triees)")
    e = agg.etat_carte(racine, CUVE, get=carte([ACTUEL, atelier()]))
    verifie((e["etat"], "atelier" in e["diff"] or "moteur" in e["diff"], e["carte_valide"]), ("differente", True, True), "carte differente : diff + valide")
    e = agg.etat_carte(racine, CUVE, get=carte(mort=True))
    verifie((e["etat"], "non verifiee" in e["motif"]), ("non_verifiee", True), "carte hors ligne : non verifiee + motif")
    e = agg.etat_carte(racine, CUVE, get=carte([ACTUEL, {"moteur": "pages", "type": "nimporte", "titre": "x", "series": ["a.b"]}]))
    verifie((e["etat"], e["carte_valide"], bool(e["carte_motifs"])), ("differente", False, True), "carte invalide : indisponible avec motifs")
    e = agg.etat_carte(racine, CUVE, get=carte())
    verifie(e["etat"], "differente", "carte sans composition mais depot avec : differente")


def test_partir_de_la_carte(racine):
    prepare(racine, [ACTUEL])
    sur_carte = [ACTUEL, atelier("Sur la carte")]
    get = carte(sur_carte)
    refuse(lambda: agg.prevoit(racine, CUVE, ajoute(atelier("Nouveau")), get=get), ValueError,
           "carte differente sans choix : jamais d'ecrasement implicite", "choisir base")
    refuse(lambda: agg.prevoit(racine, CUVE, ajoute(atelier("Nouveau"), base="carte"), get=carte(mort=True)), ValueError,
           "base=carte carte hors ligne : indisponible", "indisponible")
    refuse(lambda: agg.prevoit(racine, CUVE, ajoute(atelier("Nouveau"), base="carte"),
                               get=carte([{"moteur": "pages", "type": "z", "titre": "x", "series": ["a.b"]}])), ValueError,
           "base=carte carte invalide : indisponible avec motif", "style")
    ecrit(racine, ajoute(atelier("Nouveau"), base="carte"), get=get)
    comp = json.loads(fichier(racine).read_text(encoding="utf-8"))["graphiques"]
    verifie([g["titre"] for g in comp], ["Cuve", "Sur la carte", "Nouveau"], "partir de la carte : sa composition + l'ajout")
    prepare(racine, [ACTUEL])
    ecrit(racine, ajoute(atelier("Nouveau"), base="depot"), get=get)
    verifie([g["titre"] for g in json.loads(fichier(racine).read_text(encoding="utf-8"))["graphiques"]], ["Cuve", "Nouveau"],
            "garder le depot : la composition de la carte n'entre pas")
    verifie(all(not c.startswith(("/cm", "/up", "/u")) and c == "/json/graphiques.json" for c in get.appels), True,
            "la carte n'est jamais lue que par /json/graphiques.json")


def test_carte_change_entre_diff_et_ecriture(racine):
    prepare(racine, [ACTUEL])
    d = ajoute(atelier("N"), base="carte")
    p = agg.prevoit(racine, CUVE, d, get=carte([ACTUEL, atelier("A")]))
    refuse(lambda: agg.ecrit(racine, CUVE, d, p["empreinte"], SANS_BUILD, get=carte([ACTUEL, atelier("B")])), RuntimeError,
           "composition de la carte changee depuis le diff : refus", "modifies")


TESTS = [test_ajout_garde_le_reste, test_ajout_sans_moteur_et_calculees, test_quatre_styles_communs_en_forme_atelier,
         test_forme_actuelle_intacte, test_retire, test_fichier_absent, test_refus, test_liquide, test_empreinte_et_build,
         test_etat_carte, test_partir_de_la_carte, test_carte_change_entre_diff_et_ecriture]


if __name__ == "__main__":
    for test in TESTS:
        print(f"--- {test.__name__}")
        with tempfile.TemporaryDirectory() as t:
            os.environ["OUTILS_TASMOTA_DOSSIER"] = os.path.join(t, "outils")
            racine = Path(t) / "depot"
            racine.mkdir()
            try:
                test(tage.copie(racine))
            except Exception as e:
                print(f"KO   {test.__name__} : {type(e).__name__} : {e}")
                ECHECS.append(test.__name__)
    print(f"\n{len(ECHECS)} echec(s)" + (" : " + ", ".join(ECHECS) if ECHECS else " : VERT"))
    sys.exit(1 if ECHECS else 0)
