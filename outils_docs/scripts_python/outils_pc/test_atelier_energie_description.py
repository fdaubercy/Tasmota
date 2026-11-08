#!/usr/bin/env python3
"""Banc de atelier_energie_description.py (plan energie-atelier, A1) : les cas partages avec le rendu JS de la carte
(`cas_energie.json`, a cote du module) donnent chacun le verdict attendu.

    <Python de PlatformIO> outils_docs/scripts_python/outils_pc/test_atelier_energie_description.py [dossier du module]

Le dossier du module (defaut : celui du banc) sert au temoin : une copie mutee, ailleurs. Code de sortie 0 = vert, 1 = rouge.
"""
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else str(ICI))
CAS = ICI / "cas_energie.json"
echecs = []


def verifie(ok, quoi):
    print(("  ok  " if ok else "  ECHEC  ") + quoi)
    if not ok:
        echecs.append(quoi)


def compact(d):
    return json.dumps(d, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


import atelier_energie_description as mod  # noqa: E402  (absent = banc rouge)

cas = json.loads(CAS.read_text(encoding="utf-8"))
verifie(mod.TYPES == ("valeur", "cadran", "demi-cercle", "barres", "courbe", "aire", "escalier"), "TYPES")
verifie(mod.CHAMPS_DIRECT == ("Power", "Current", "Factor", "Frequency", "Voltage", "ApparentPower", "ReactivePower",
                              "Today", "Yesterday", "Total"), "CHAMPS_DIRECT")
verifie(mod.BORNES == {"elements": 16, "octets": 4096, "titre": 40}, "BORNES")
verifie(mod.valide(mod.DEFAUT) == [], "DEFAUT valide : %s" % mod.valide(mod.DEFAUT))
verifie(len(compact(mod.DEFAUT)) <= 4096, "DEFAUT tient dans 4096 octets (%d)" % len(compact(mod.DEFAUT)))
verifie(cas[0]["nom"] == "defaut" and cas[0]["description"] == mod.DEFAUT, "premier cas = DEFAUT du module")
valides = [c["description"] for c in cas if not c["motif"]]
vus = {e["type"] for d in valides for e in d["elements"]}
verifie(vus >= set(mod.TYPES), "un cas valide par type : manque %s" % sorted(set(mod.TYPES) - vus))
vus = {k for d in valides for e in d["elements"] for k in e["source"]}
verifie(vus >= {"direct", "total", "flash"}, "un cas valide par source")
verifie({e["source"].get("direct") for d in valides for e in d["elements"]} >= set(mod.CHAMPS_DIRECT), "chaque champ direct")
verifie({e["source"].get("flash") for d in valides for e in d["elements"]} >= {"minutes", "heure", "jour", "mois", "an"}, "chaque flash")
verifie(any("mois" in e["source"] and e["source"].get("flash") == "jour" for d in valides for e in d["elements"]), "jour a mois fixe")
verifie(any("decalage" in e["source"] for d in valides for e in d["elements"]), "jour a decalage")
verifie(any("nombre" in e["source"] for d in valides for e in d["elements"]), "mois avec nombre")
verifie(any(e.get("total") for d in valides for e in d["elements"]), "cas avec total")
verifie(any(len(compact(c["description"])) > 4096 for c in cas if c["motif"]), "un cas refuse pour sa taille")
for c in cas:
    motifs = mod.valide(c["description"])
    if not c["motif"]:
        verifie(motifs == [], "%s : valide (motifs : %s)" % (c["nom"], motifs))
    else:
        verifie(any(c["motif"] in x for x in motifs), "%s : refuse avec %r (motifs : %s)" % (c["nom"], c["motif"], motifs))
print("%d echec(s)" % len(echecs))
sys.exit(1 if echecs else 0)
