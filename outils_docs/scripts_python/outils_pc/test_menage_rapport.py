"""Banc de menage_rapport (validation du rapport de l'agent auditeur-menage), avec mutants. Code de sortie 0 = vert."""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()

import copy
import json
import os
import sys
from pathlib import Path

import menage_rapport as mr

ECHECS = []
RACINE = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))


def verifie(obtenu, attendu, libelle):
    if obtenu != attendu:
        ECHECS.append(libelle)
        print(f"ECHEC {libelle} : obtenu {obtenu!r}, attendu {attendu!r}")


def prop(**kw):
    p = {"id": "P1", "categorie": "reste", "chemin": "tasks/README.md", "constat": "ancien", "preuve": "git log", "action": "archiver",
         "casserait": "rien", "risque": "faible", "en_cours": False}
    p.update(kw)
    return p


def rapport(*props):
    return {"resume": "1 proposition", "non_verifie": "", "propositions": list(props)}


def refuse(r, libelle):
    propre, err = mr.valide(r, RACINE)
    verifie((propre is None, bool(err)), (True, True), libelle)


# 1. rapport valide
propre, err = mr.valide(rapport(prop()), RACINE)
verifie(err, [], "rapport valide : aucune erreur")
verifie(propre["propositions"][0]["chemin"], "tasks/README.md", "chemin conserve")
verifie(propre["propositions"][0]["en_cours"], False, "en_cours conserve")
propre, err = mr.valide(rapport(prop(vers="")), RACINE)
verifie((err, propre and propre["propositions"][0]["vers"]), ([], None), "vers vide : pas de destination, pas une erreur")
for libelle, texte in [("avec commentaire", "outils_docs/analyses/ (dossier à créer ; les 7 fichiers)"), ("avec marqueur", "outils_docs/maquettes/<nom du dossier>")]:
    propre, err = mr.valide(rapport(prop(action="deplacer", vers=texte, constat="raison")), RACINE)
    p0 = propre and propre["propositions"][0]
    verifie((err, p0 and p0["vers"], p0 and "destination non exacte" in p0["constat"] and texte[:20] in p0["constat"]), ([], None, True),
            f"vers en texte libre ({libelle}) : rapport garde, destination ecartee et recopiee dans constat")
propre, err = mr.valide(rapport(prop(action="deplacer", vers="outils_docs/archive")), RACINE)
verifie((err, propre and propre["propositions"][0]["vers"]), ([], "outils_docs/archive"), "deplacement vers un dossier a creer")

# 1b. couverture, limites, ecartes : structure lisible par la page
def avec(**kw):
    r = rapport(prop())
    r.update(kw)
    return r


propre, err = mr.valide(avec(couverture=[{"controle": "taille", "etat": "non_fait", "note": "wc non lance"},
                                         {"controle": "reste", "etat": "fait", "note": ""},
                                         {"controle": "doublon", "etat": "partiel", "note": "dossier data/ seulement"}],
                            limites=["Un Glob a expire"], ecartes=["Les plans clos"]), RACINE)
verifie(err, [], "couverture valide : aucune erreur")
verifie([(c["controle"], c["etat"]) for c in propre["couverture"]], [("taille", "non_fait"), ("reste", "fait"), ("doublon", "partiel")], "couverture conservee")
verifie((propre["limites"], propre["ecartes"]), (["Un Glob a expire"], ["Les plans clos"]), "limites et ecartes conserves")
propre, err = mr.valide(rapport(prop()), RACINE)
verifie((err, propre["couverture"], propre["limites"], propre["ecartes"]), ([], [], [], []), "sans couverture : listes vides, rapport valide (ancien format)")
for libelle, kw in [("controle inconnu", {"couverture": [{"controle": "tout", "etat": "fait", "note": ""}]}),
                    ("etat inconnu", {"couverture": [{"controle": "taille", "etat": "peut-etre", "note": ""}]}),
                    ("controle en double", {"couverture": [{"controle": "taille", "etat": "fait", "note": ""}, {"controle": "taille", "etat": "non_fait", "note": ""}]}),
                    ("couverture pas une liste", {"couverture": "taille"}),
                    ("element pas un objet", {"couverture": ["taille"]}),
                    ("limites pas des textes", {"limites": [1, 2]}),
                    ("trop de limites", {"limites": ["x"] * 40})]:
    refuse(avec(**kw), f"couverture invalide refusee : {libelle}")
propre, err = mr.valide(avec(couverture=[{"controle": "taille", "etat": "non_fait", "note": "ghp_" + "a" * 36}], limites=["mdp = \"secret123\""]), RACINE)
verifie(("ghp_" + "a" * 36 in json.dumps(propre), "secret123" in json.dumps(propre)), (False, False), "secrets masques dans la couverture et les limites")

# 2. JSON entoure de texte libre, accolades dans une chaine
sortie = 'Voici le rapport :\n' + json.dumps(rapport(prop(constat="a } b { c"))) + '\nfin'
propre, err = mr.valide(sortie, RACINE)
verifie((err, propre and propre["propositions"][0]["constat"]), ([], "a } b { c"), "JSON extrait d'un texte libre")
verifie(mr.extrait_json("pas de json"), None, "sortie sans JSON")

# 3. refus : champs et chemins
for libelle, p in [
    ("chemin avec ..", prop(chemin="../hors/depot.txt")),
    ("chemin absolu posix", prop(chemin="/etc/passwd")),
    ("chemin absolu Windows", prop(chemin="C:\\Windows\\system32")),
    ("chemin avec .. en anti-slash", prop(chemin="tasks\\..\\..\\x")),
    ("chemin vide", prop(chemin="")),
    ("chemin octet nul", prop(chemin="a\x00b")),
    ("categorie inconnue", prop(categorie="autre")),
    ("action inconnue", prop(action="formater")),
    ("risque inconnu", prop(risque="critique")),
    ("id invalide", prop(id="a b/c")),
    ("en_cours non booleen", prop(en_cours="oui")),
    ("destination hors depot", prop(vers="../ailleurs")),
    ("constat absent", {k: v for k, v in prop().items() if k != "constat"}),
]:
    refuse(rapport(p), libelle)
refuse(rapport(prop(), prop()), "id en double")
refuse({"resume": "x"}, "propositions absentes")
refuse({"resume": "x", "propositions": "pas une liste"}, "propositions pas une liste")
refuse(rapport(*[prop(id=f"P{i}") for i in range(mr.MAX_PROPOSITIONS + 1)]), "trop de propositions")
refuse("[1, 2]", "racine pas un objet")

# 4. secrets masques
r = rapport(prop(preuve='grep -n STA_PASS1 : "STA_PASS1" = "hunter2secret" et ghp_abcdefghijklmnopqrstuvwxyz0123456789',
                 constat="url http://admin:motdepasse@10.0.0.1/x"))
propre, err = mr.valide(r, RACINE)
sortie_page = json.dumps(propre)
verifie(("hunter2secret" in sortie_page, "ghp_abcdef" in sortie_page, "motdepasse" in sortie_page), (False, False, False), "secrets masques")

# 5. texte tronque
propre, err = mr.valide(rapport(prop(constat="x" * 5000)), RACINE)
verifie(len(propre["propositions"][0]["constat"]), mr.MAX_TEXTE, "texte tronque")

# 6. mutants : le banc doit devenir rouge si la validation est affaiblie
def mutant(libelle, patch, cas):
    sauve = copy.copy(mr.__dict__)
    patch()
    try:
        propre, err = mr.valide(cas, RACINE)
        detecte = not (propre is None)
    finally:
        mr.__dict__.update(sauve)
    verifie(detecte, True, f"mutant {libelle} accepte le cas hostile (preuve que le banc le voit)")


mutant("chemin_sur toujours ok", lambda: setattr(mr, "chemin_sur", lambda c, r: c), rapport(prop(chemin="../hors/depot.txt")))
mutant("masque neutre", lambda: setattr(mr, "masque", lambda t: t), rapport(prop(preuve="ghp_abcdefghijklmnopqrstuvwxyz0123456789")))
propre, err = mr.valide(rapport(prop(preuve="ghp_abcdefghijklmnopqrstuvwxyz0123456789")), RACINE)
verifie("ghp_abcdef" in json.dumps(propre), False, "apres mutants : masque restaure")
propre, err = mr.valide(rapport(prop(chemin="../hors/depot.txt")), RACINE)
verifie(propre, None, "apres mutants : chemin_sur restaure")

if ECHECS:
    print(f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1)
print("VERT : menage_rapport")
