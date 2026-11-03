#!/usr/bin/env python3
"""Banc de atelier_graphiques_description.py (plan atelier-graphiques, A1) : les cas partages avec le banc Berry
(`berry/bouchons_berry/pages_graphiques/cas_description.json`) donnent chacun le verdict attendu.

    <Python de PlatformIO> outils_docs/scripts_python/outils_pc/test_atelier_graphiques_description.py [dossier du module]

Le dossier du module (defaut : celui du banc) sert au temoin : une copie mutee, ailleurs. Code de sortie 0 = vert, 1 = rouge.
"""
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else str(ICI))
CAS = ICI.parent / "berry" / "bouchons_berry" / "pages_graphiques" / "cas_description.json"
echecs = []


def verifie(ok, quoi):
    print(("  ok  " if ok else "  ECHEC  ") + quoi)
    if not ok:
        echecs.append(quoi)


import atelier_graphiques_description as mod  # noqa: E402  (absent = banc rouge)

donnees = json.loads(CAS.read_text(encoding="utf-8"))
verifie(donnees["styles"] == list(mod.STYLES), "styles du fichier de cas = STYLES")
verifie(mod.BORNES == {"pages": 8, "graphiques": 8, "series": 12, "octets": 8192}, "BORNES")
verifie({"cs", "graphiques", "histo", "cuve", "energie", "pages"} <= mod.ROUTES_RESERVEES, "routes reservees")
valides = {g["type"] for c in donnees["cas"] if c["valide"] for p in c["description"].get("pages", [])
           for g in p["graphiques"]}
verifie(valides >= set(mod.STYLES), "au moins un cas valide par style : manque %s" % sorted(set(mod.STYLES) - valides))
for c in donnees["cas"]:
    motifs = mod.valide(c["description"])
    if c["valide"]:
        verifie(motifs == [], "%s : valide (motifs : %s)" % (c["nom"], motifs))
    else:
        verifie(bool(c["motif"]) and any(c["motif"] in x for x in motifs), "%s : refuse avec %r (motifs : %s)" % (c["nom"], c["motif"], motifs))
for f in ("(1", "1)", "min", "a;b", "x[0]", "a.constructor", "a__b", "f(1)", "1,2", "'a'", ""):
    verifie(mod.valide_formule(f) is not None, "formule refusee : %r" % f)
for f in ("6732 - a.b", "max(a, b) / 2", "round(abs(a.b - 1.5), 2)", "(a+b)*c"):
    verifie(mod.valide_formule(f) is None, "formule acceptee : %r" % f)
print("%d echec(s)" % len(echecs))
sys.exit(1 if echecs else 0)
