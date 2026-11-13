"""Banc du generateur HASPmota de l'atelier des ecrans (description -> pages.jsonl). Code de sortie 0 = vert.
Python de PlatformIO. Lit le depot (ecran.json et pages.jsonl des debits), n'ecrit rien."""

import json
import sys
from pathlib import Path

import atelier_ecrans_description as desc
import atelier_ecrans_haspmota as hp

RACINE = Path(__file__).resolve().parents[3]
ENV = "tasmota32s3-bureau-ecran-debits-pac"
PAGES = RACINE / "data/bureau/tasmota32s3-ecran-debits-pac/pages.jsonl"
ECHECS = []


def verifie(ok, libelle, detail=""):
    if not ok:
        ECHECS.append(libelle)
        print(f"ECHEC {libelle} {detail}")


def mini(objets, pages=None):
    return {"version": 1, "ecran": "ST7262_1024x600", "orientation": 0, "modele": [],
            "pages": pages or [{"n": 0, "titre": "C"}, {"n": 1, "titre": "A"}, {"n": 2, "titre": "B"}], "objets": objets}


def test_debits_identique():
    d = desc.charge(RACINE, ENV)
    e = hp.ecarts(PAGES.read_text(encoding="utf-8"), hp.genere(d))
    verifie(e == [], "debits : pages.jsonl genere equivalent au depot", e[:5])


def test_texte_special():
    t = 'Débit "5" \ 100 %'
    s = hp.genere(mini([{"id": 1, "page": 1, "type": "label", "x": 0, "y": 0, "l": 10, "h": 10, "attributs": {"text": t}}]))
    lignes = [json.loads(x) for x in s.splitlines()]
    verifie(any(x.get("text") == t for x in lignes), "texte special relu a l'identique", s)
    verifie("Débit" in s, "UTF-8 non echappe")


def test_ecart_detecte():
    att = PAGES.read_text(encoding="utf-8")
    obt = att.replace('"text":"Débit 1"', '"text":"Debit 1"', 1)
    e = hp.ecarts(att, obt)
    verifie(len(e) == 1 and "text" in e[0] and "ligne" in e[0], "ecart nomme ligne et cle", e)
    verifie(hp.ecarts(att, att) == [], "identique : aucun ecart")
    verifie(len(hp.ecarts(att, att + '{"page":9}\n')) >= 1, "ligne en plus detectee")


def test_regles():
    o = [{"id": 1, "page": 0, "type": "btn", "x": 1, "y": 2, "l": 3, "h": 4, "attributs": {"bg_color": "#111"},
          "toucher": {"page": 2}, "actif": {"bg_color": "#222"}, "commentaire": "c"},
         {"id": 2, "page": 0, "type": "btn", "x": 1, "y": 2, "l": 3, "h": 4, "attributs": {"bg_color": "#111"},
          "toucher": {"page": 1}, "actif": {"bg_color": "#222"}},
         {"id": 3, "page": 0, "type": "btn", "x": 1, "y": 2, "l": 3, "h": 4, "attributs": {}, "toucher": {"fonction": "m.f", "args": [1]}},
         {"id": 4, "page": 0, "type": "btn", "x": 1, "y": 2, "l": 3, "h": 4, "attributs": {}, "toucher": {"commande": "Power 1"},
          "liaison": {"cle": "k", "attribut": "text"}}]
    l = {x["id"]: x for x in map(json.loads, hp.genere(mini(o)).splitlines()) if x.get("page") == 0 and "id" in x}
    verifie(l[1]["action"] == "p2" and l[1]["bg_color"] == "#111" and l[1]["comment"] == "c" and l[1]["w"] == 3,
            "bouton page inactif", l[1])
    verifie(l[2]["action"] == "p1" and l[2]["bg_color"] == "#222", "bouton de la page de demarrage actif", l[2])
    verifie("action" not in l[3] and "action" not in l[4] and "liaison" not in l[4], "fonction/commande/liaison hors pages.jsonl")
    verifie(hp.genere(mini([{"id": 1, "page": 1, "type": "inconnu", "x": 0, "y": 0, "l": 1, "h": 1, "attributs": {"zzz": 1}}])) != "",
            "objet hors catalogue : rendu tel quel")


def test_palier2():
    o = [{"id": 5, "page": 1, "type": "qrcode", "x": 0, "y": 0, "l": 80, "h": 80, "attributs": {"qr_text": "x"}},
         {"id": 6, "page": 1, "type": "switch", "x": 0, "y": 90, "l": 60, "h": 30, "attributs": {"val": True}},
         {"id": 7, "page": 1, "type": "dropdown", "x": 0, "y": 130, "l": 90, "h": 30, "attributs": {"options": "a" + chr(10) + "b"}}]
    l = {x["id"]: x for x in map(json.loads, hp.genere(mini(o)).splitlines()) if "id" in x}
    verifie(l[5].get("qr_size") == 80 and l[5]["w"] == 80, "QR code : qr_size = l (lvh_qrcode::set_qr_size)", l[5])
    verifie(l[6]["val"] is True and l[7]["options"] == "a" + chr(10) + "b", "interrupteur et options recopies", (l[6], l[7]))


for t in (test_debits_identique, test_texte_special, test_ecart_detecte, test_regles, test_palier2):
    t()
print("ECHECS : " + ", ".join(ECHECS) if ECHECS else "BANC_ECRANS_HASPMOTA: OK")
sys.exit(1 if ECHECS else 0)
