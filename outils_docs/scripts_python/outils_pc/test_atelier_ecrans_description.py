"""Banc de la description neutre de l'atelier des ecrans (`ecran.json`) : validateur a mutants, charge, chemin, empreinte.
Code de sortie 0 = vert. Python de PlatformIO. Lit le catalogue et l'ecran.json du depot, n'ecrit rien dans le depot."""

import copy
import json
import sys
import tempfile
from pathlib import Path

import atelier_ecrans_catalogue as cat
import atelier_ecrans_description as desc

RACINE = Path(__file__).resolve().parents[3]
ENV = "tasmota32s3-bureau-ecran-debits-pac"
ECHECS = []


def verifie(ok, libelle, detail=""):
    if not ok:
        ECHECS.append(libelle)
        print(f"ECHEC {libelle} {detail}")


REFERENCE = {
    "version": 1, "ecran": "ST7262_1024x600", "orientation": 0,
    "modele": [{"cle": "voies[].debit", "type": "texte", "exemple": "4,20"},
               {"cle": "voies[].barre", "type": "entier", "exemple": 62},
               {"cle": "total", "type": "texte", "exemple": "Total 17,9 L/min"}],
    "pages": [{"n": 0, "titre": "Commun"}, {"n": 1, "titre": "Debits", "attributs": {"bg_color": "#10161E"}}],
    "objets": [
        {"id": 1, "page": 0, "type": "label", "x": 24, "y": 14, "l": 210, "h": 40,
         "attributs": {"text": "Titre", "text_font": "A:sd/polices/RobotoCondensed-Regular.ttf-32", "text_color": "#E8EDF2"}},
        {"id": 91, "page": 0, "type": "btn", "x": 24, "y": 540, "l": 110, "h": 46,
         "attributs": {"text": "Debits", "radius": 23, "text_font": 16}, "toucher": {"page": 1}},
        {"id": 11, "page": 1, "type": "label", "x": 24, "y": 86, "l": 180, "h": 32,
         "attributs": {"text": "Debit 1", "text_font": 24}, "liaison": {"cle": "voies[].debit", "indice": 0, "attribut": "text"}},
        {"id": 12, "page": 1, "type": "bar", "x": 212, "y": 89, "l": 532, "h": 26,
         "attributs": {"min": 0, "max": 100, "radius10": 13, "bg_color10": "#3FA7FF"},
         "liaison": {"cle": "voies[].barre", "indice": 0, "attribut": "val"}, "commentaire": "barre relative"},
        {"id": 13, "page": 1, "type": "label", "x": 400, "y": 14, "l": 400, "h": 40,
         "attributs": {"text": "Total", "text_font": "A:sd/polices/RobotoCondensed-Regular.ttf-36"},
         "liaison": {"cle": "total", "attribut": "text"}},
    ],
}


def mutant(f):
    d = copy.deepcopy(REFERENCE)
    f(d)
    return d


def objet(d, i):
    return d["objets"][i]


# (nom, fonction de mutation, fragment attendu dans un message)
MUTANTS = [
    ("objet hors ecran (x + l > largeur)", lambda d: objet(d, 4).update(x=700, l=400), "hors de l'écran"),
    ("objet hors ecran (y + h > hauteur)", lambda d: objet(d, 0).update(y=580, h=40), "hors de l'écran"),
    ("objet de largeur nulle", lambda d: objet(d, 0).update(l=0), "hors de l'écran"),
    ("police absente (ttf inconnue)", lambda d: objet(d, 0)["attributs"].update(text_font="A:sd/polices/Inconnue.ttf-20"), "police"),
    ("police absente (forme inconnue)", lambda d: objet(d, 0)["attributs"].update(text_font="comic"), "police"),
    ("taille absente (22 non compilee)", lambda d: objet(d, 2)["attributs"].update(text_font=22), "taille 22"),
    ("taille absente (montserrat-11)", lambda d: objet(d, 2)["attributs"].update(text_font="montserrat-11"), "taille 11"),
    ("taille de ttf nulle", lambda d: objet(d, 0)["attributs"].update(text_font="A:sd/polices/RobotoCondensed-Regular.ttf-0"), "taille 0"),
    ("attribut inconnu du type", lambda d: objet(d, 0)["attributs"].update(zorglub=1), "zorglub"),
    ("attribut d'un autre type (point_count sur un label)", lambda d: objet(d, 0)["attributs"].update(point_count=3), "point_count"),
    ("type de palier 2", lambda d: objet(d, 0).update(type="dropdown"), "palier 2"),
    ("type inconnu", lambda d: objet(d, 0).update(type="machin"), "type"),
    ("liaison vers une cle absente de modele", lambda d: objet(d, 2)["liaison"].update(cle="voies[].nom"), "liaison"),
    ("liaison vers un attribut inconnu", lambda d: objet(d, 2)["liaison"].update(attribut="zorglub"), "liaison"),
    ("liaison de liste sans indice", lambda d: objet(d, 2)["liaison"].pop("indice"), "indice"),
    ("id en double sur une meme page", lambda d: objet(d, 3).update(id=11), "en double"),
    ("page inconnue", lambda d: objet(d, 2).update(page=7), "page 7"),
    ("toucher vers une page inconnue", lambda d: objet(d, 1).update(toucher={"page": 9}), "page 9"),
    ("toucher a deux actions", lambda d: objet(d, 1).update(toucher={"page": 1, "commande": "Restart 1"}), "toucher"),
    ("version inconnue", lambda d: d.update(version=2), "version"),
    ("ecran inconnu du catalogue", lambda d: d.update(ecran="XXX_1x1"), "écran"),
    ("page en double", lambda d: d["pages"].append({"n": 1, "titre": "Bis"}), "page 1"),
    ("couleur mal formee", lambda d: objet(d, 0)["attributs"].update(text_color="rouge"), "couleur"),
    ("cle de modele en double", lambda d: d["modele"].append({"cle": "total", "type": "texte", "exemple": "x"}), "total"),
    ("attribut de page inconnu", lambda d: d["pages"][1]["attributs"].update(zorglub=1), "zorglub"),
]


def test_reference(c):
    verifie(desc.valide(REFERENCE, c) == [], "reference valide", desc.valide(REFERENCE, c))
    # une taille libre de ttf et un montserrat du catalogue sont acceptes
    d = mutant(lambda d: objet(d, 0)["attributs"].update(text_font="A:sd/polices/RobotoCondensed-Regular.ttf-27"))
    verifie(desc.valide(d, c) == [], "taille libre d'un ttf acceptee", desc.valide(d, c))
    d = mutant(lambda d: objet(d, 0)["attributs"].update(text_font="montserrat-14"))
    verifie(desc.valide(d, c) == [], "montserrat-14 accepte", desc.valide(d, c))


def test_mutants(c):
    for nom, f, fragment in MUTANTS:
        msgs = desc.valide(mutant(f), c)
        verifie(bool(msgs), f"mutant refuse : {nom}")
        verifie(any(fragment in m for m in msgs), f"mutant refuse avec son message : {nom}", f"attendu « {fragment} », recu {msgs}")


def test_fichier(c):
    p = desc.chemin(RACINE, ENV)
    verifie(p == RACINE / "outils_docs/atelier_ecrans/cartes" / ENV / "ecran.json", "chemin de l'ecran.json", p)
    d = desc.charge(RACINE, ENV)
    verifie(d is not None and desc.valide(d, c) == [], "ecran.json des debits valide", desc.valide(d, c) if d else "absent")
    verifie(desc.charge(RACINE, "env-qui-n-existe-pas") is None, "charge : env sans description -> None")
    with tempfile.TemporaryDirectory() as t:
        r = Path(t)
        q = desc.chemin(r, "x")
        q.parent.mkdir(parents=True)
        q.write_text("{pas du json", encoding="utf-8")
        verifie(desc.charge(r, "x") is None, "charge : fichier illisible -> None, sans exception")
    verifie(desc.empreinte(b"abc") == desc.empreinte(b"abc") and desc.empreinte(b"abc") != desc.empreinte(b"abd"),
            "empreinte stable et sensible au contenu")
    if d:
        # 1. l'ecran.json couvre le pages.jsonl : memes objets, memes coordonnees
        lignes = [json.loads(l) for l in (RACINE / "data/bureau/tasmota32s3-ecran-debits-pac/pages.jsonl").read_text(encoding="utf-8").splitlines()]
        pj = {(l["page"], l["id"]): l for l in lignes if "obj" in l}
        ec = {(o["page"], o["id"]): o for o in d["objets"]}
        verifie(set(pj) == set(ec), "ecran.json : memes objets que pages.jsonl", sorted(set(pj) ^ set(ec)))
        ecarts = [k for k in pj if k in ec and (pj[k]["x"], pj[k]["y"], pj[k]["w"], pj[k]["h"]) != (ec[k]["x"], ec[k]["y"], ec[k]["l"], ec[k]["h"])]
        verifie(not ecarts, "ecran.json : memes coordonnees que pages.jsonl", ecarts)
        verifie(sum(o["page"] == 0 for o in d["objets"]) == 7 and {p["n"] for p in d["pages"]} == {0, 1, 2, 3},
                "ecran.json : pages Commun, Debits, Courbes, Reglages")


def main():
    c = cat.charge(RACINE)
    test_reference(c)
    test_mutants(c)
    test_fichier(c)
    print("BANC_ATELIER_ECRANS_DESCRIPTION:", "ECHEC" if ECHECS else "OK", f"({len(MUTANTS)} mutants)")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
