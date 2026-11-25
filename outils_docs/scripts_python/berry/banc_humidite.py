r"""Banc de la page /humidite et de la commande ReglageHumidite (data/cave/<carte>/controleHumidite.be, banc_humidite.be).

UTILISATION
    python outils_docs/scripts_python/berry/banc_humidite.py [--sans-mutants] [--source CHEMIN]
Depuis n'importe quel dossier. Code de sortie 0 = vert : les vrais modules des deux caves passent banc_humidite.be ET chaque mutant (copie du
module ESP32 avec un defaut reintroduit) le fait echouer ; sans ces temoins, un vert ne prouverait rien. --source : module a tester et a muter
a la place de celui du depot (verifier un correctif avant de l'ecrire dans data/).
Ne teste ni le vrai firmware (HTTP, persist, solidification) ni les tuiles de l'accueil : faux tasmota, bouchons dans bouchons_berry/humidite/.
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from banc_coprocesseur import trouve_berry, trouve_racine  # noqa: E402  (meme dossier : module voisin)

MODULE = "data/cave/tasmota32-serveur-rly/controleHumidite.be"
BANC = "tasmota32-serveur-rly"
# (nom, texte du module, remplacement) : chaque texte doit exister UNE fois dans le module du depot
MUTANTS = [
    ("regex {1,3} sur la borne basse (la panne du 2026-11-23 : exception 'error in regex')",
     're.match("^[0-9][0-9]?[0-9]?$", str(bas))', 're.match("^[0-9]{1,3}$", str(bas))'),
    ("regex {1,3} sur la borne haute",
     're.match("^[0-9][0-9]?[0-9]?$", str(haut))', 're.match("^[0-9]{1,3}$", str(haut))'),
    ("persist.save() sans true (modif imbriquee non ecrite)", "        persist.save(true)      #", "        persist.save()      #"),
    ("ecart minimum de 5 points retire", "|| h - b < 5)", ")"),
    ("borne haute au-dela de 100 acceptee", "if (h > 100 ||", "if ("),
    ("bornes inversees a l'ecriture", 'th["limites"] = [b, h]', 'th["limites"] = [h, b]'),
    ("page : succes affiche meme en cas d'erreur", 'erreur == nil ? "Bornes enregistrées." : erreur', '"Bornes enregistrées."'),
    ("route POST retiree", 'webserver.on("/humidite", / -> self.enregistre(), webserver.HTTP_POST)', "pass"),
    ("valeurs non numeriques acceptees", 'if (re.match("^[0-9][0-9]?[0-9]?$", str(bas)) == nil ||', "if (false ||"),
]


def lance(berry, racine, module):
    cmd = [str(berry), str(Path(__file__).with_suffix(".be"))] + ([module] if module else [])
    r = subprocess.run(cmd, cwd=str(racine), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser(description="Banc de la page /humidite (controleHumidite.be)")
    ap.add_argument("--sans-mutants", action="store_true")
    ap.add_argument("--source", help="module a tester et a muter, a la place de celui du depot")
    args = ap.parse_args()
    racine = trouve_racine()
    berry = trouve_berry(racine)
    source = Path(args.source) if args.source else racine / MODULE
    sortie = lance(berry, racine, source.as_posix() if args.source else None)
    print(sortie, end="" if sortie.endswith("\n") else "\n")
    vert = "BANC_HUMIDITE: OK" in sortie
    if not args.sans_mutants:
        texte = source.read_text(encoding="utf-8")
        for nom, avant, apres in MUTANTS:
            if texte.count(avant) != 1:
                print(f"KO   mutant '{nom}' : texte a muter introuvable ou multiple ({source.name} modifie ?)")
                vert = False
                continue
            with tempfile.TemporaryDirectory() as tmp:
                muté = Path(tmp) / "controleHumidite.be"
                muté.write_text(texte.replace(avant, apres), encoding="utf-8")
                rouge = "BANC_HUMIDITE: OK" not in lance(berry, racine, muté.as_posix())   # ECHEC ou plantage
            print(("OK   " if rouge else "KO   ") + f"mutant '{nom}' : banc rouge")
            vert = vert and rouge
    print("\n" + ("VERT" if vert else "ROUGE"))
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())
