"""Banc de l'emulation Hue pour Alexa (data/fs/hueFonctions.be et data/fs/controleHue.be).

UTILISATION
    python outils_docs/scripts_python/berry/banc_hue.py [--sans-mutants]
Depuis n'importe quel dossier. Code de sortie 0 = vert : les vrais modules passent banc_hue.be ET chaque mutant (copie d'un
module avec une garde retiree) le fait echouer ; sans ces temoins, un vert ne prouverait rien.
Ne teste ni le vrai firmware (SSDP, /api, redemarrage) ni Alexa : faux tasmota, bouchons dans bouchons_berry/hue/.
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

# (fichier, nom, texte du module, remplacement)
MUTANTS = [
    ("controleHue.be", "interception retiree : id hors liste blanche rendu au natif (nil)",
     "                return hueFonctions.erreur(id, 3,", "                return nil #"),
    ("controleHue.be", "exception de la commande non rattrapee (main rendue au natif)",
     "            # un import rate ou un log qui leve ne doit jamais rendre la main au natif (il commuterait n'importe quel relais)\n",
     "            raise e, m\n"),
    ("controleHue.be", "set_power nil pris pour un succes (Alexa entend fait sans commutation)",
     "if tasmota.set_power(a[\"n\"] - 1, on) == nil", "tasmota.set_power(a[\"n\"] - 1, on)\n            if false"),
    ("controleHue.be", "MAC illisible journalisee a chaque requete (inondation du syslog)",
     "if !self.macKo    hueFonctions.log", "if true    hueFonctions.log"),
    ("controleHue.be", "etat d'un id hors liste rendu au natif (nil)",
     "if a == nil    return hueFonctions.erreur(id, 3, \"resource, /lights/\" + str(id) + \", not available\")    end",
     "if a == nil    return nil    end"),
    ("controleHue.be", "comparaison avant reglage retiree (redemarrage a chaque demarrage)",
     "if configGlobal.testeParam(\"Emulation\", cible, \"int\")", "if tasmota.cmd(\"Emulation \" + str(cible), boolMute) != nil"),
    ("controleHue.be", "ordre FriendlyName / Emulation inverse",
     "        var cible = 0\n        if actif\n",
     "        var cible = 0\n        configGlobal.testeParam(\"Emulation\", actif ? 2 : 0, \"int\")\n        if actif\n"),
    ("controleHue.be", "masquage des FriendlyName non verifie", "if masques == 8", "if true"),
    ("controleHue.be", "groupe 0 double (chaine rendue)", "    def groups()\n        return nil", "    def groups()\n        return \"\\\"1\\\"\""),
    ("controleHue.be", "garde d'activation retiree", "var actif = isinstance(b, map) && b.find(\"activation\", \"OFF\") == \"ON\"",
     "var actif = isinstance(b, map)"),
    ("controleHue.be", "MAC figee a la premiere lecture (ids jamais recalcules)", "if mac != self.mac", "if self.mac == nil"),
    ("controleHue.be", "MAC nulle acceptee", " || mac == \"00:00:00:00:00:00\"", ""),
    ("hueFonctions.be", "garde Shutter retiree", "if volets.contains(id)", "if false"),
    ("hueFonctions.be", "bit 28 oublie", "if r > 15    id = id | (1 << 28)    end", "if false    id = id | (1 << 28)    end"),
    ("hueFonctions.be", "relais 32 non code 0", "var r = n >= 32 ? 0 : n", "var r = n"),
    ("hueFonctions.be", "nom en double accepte", "(noms.contains(cle) ?", "(false ?"),
    ("hueFonctions.be", "relais inactif accepte", "if m.find(\"activation\", \"OFF\") != \"ON\" || r.find(\"activation\", \"OFF\") != \"ON\"", "if false"),
    ("hueFonctions.be", "nom de plus de 32 caracteres accepte", "|| size(nom) > 32", ""),
    ("hueFonctions.be", "corps sans booleen accepte", "return type(on) == \"bool\" ? on : nil", "return on"),
    ("hueFonctions.be", "volet inactif refuse quand meme", "if !isinstance(v, map) || v.find(\"activation\", \"OFF\") != \"ON\" ||", "if !isinstance(v, map) ||"),
]
MODULES = ("hueFonctions.be", "controleHue.be")


def lance(berry, racine, sources):
    r = subprocess.run([str(berry), str(Path(__file__).with_suffix(".be")), str(sources)], cwd=str(racine),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser(description="Banc de l'emulation Hue (hueFonctions.be, controleHue.be)")
    ap.add_argument("--sans-mutants", action="store_true")
    args = ap.parse_args()
    racine = trouve_racine()
    berry = trouve_berry(racine)
    sortie = lance(berry, racine, "data/fs")
    print(sortie, end="" if sortie.endswith("\n") else "\n")
    vert = "BANC_HUE: OK" in sortie
    if not args.sans_mutants:
        textes = {nom: (racine / "data" / "fs" / nom).read_text(encoding="utf-8") for nom in MODULES}
        for fichier, nom, avant, apres in MUTANTS:
            if textes[fichier].count(avant) != 1:
                print(f"KO   mutant '{nom}' : texte a muter introuvable ou multiple ({fichier} modifie ?)")
                vert = False
                continue
            with tempfile.TemporaryDirectory() as tmp:
                for autre, texte in textes.items():               # les DEUX modules, dont un seul est mute
                    (Path(tmp) / autre).write_text(texte.replace(avant, apres) if autre == fichier else texte, encoding="utf-8")
                rouge = "BANC_HUE: OK" not in lance(berry, racine, Path(tmp).as_posix())   # ECHEC ou plantage
            print(("OK   " if rouge else "KO   ") + f"mutant '{nom}' : banc rouge")
            vert = vert and rouge
    print("\n" + ("VERT" if vert else "ROUGE"))
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())
