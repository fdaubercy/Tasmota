"""Banc de la facade du rideau du garage (controleRideau.be du dossier de la carte, plan visuel-reglage-volets, A10).

UTILISATION
    python outils_docs/scripts_python/berry/banc_rideau_facade.py [--sans-mutants] [--sources <dossier de controleRideau.be>]
Depuis n'importe quel dossier. Code de sortie 0 = vert : le vrai module passe banc_rideau_facade.be ET chaque mutant
(copie du module avec une regle retiree) le fait echouer. Ne teste ni le vrai serveur web, ni le reseau, ni le dessin
(sonde outils_pc/test_volets_chrome.py, scenario rideau).
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from banc_coprocesseur import trouve_berry, trouve_racine  # noqa: E402  (meme dossier : module voisin)

CARTE = Path("data") / "garage" / "tasmota32s3-rideau-garage-modbus"
# (nom, texte du module, remplacement) : chaque mutant retire une regle que le banc doit voir
MUTANTS = [
    ("inversion du curseur oubliee", "(vr.find(\"inverse\", 1) == 1 ? 100 - p : p)", "p"),
    ("repli sur les fins de course retire", "{\"ouverture\": self.positionCapteurs(vr), \"muet\": true}", "{\"ouverture\": nil, \"muet\": true}"),
    ("client HTTP jamais ferme", "try    cl.close()    except .. end", ""),
    ("une ligne d'erreur par requete", "if (muet != self.maitreMuet)", "if true"),
    ("</script> orphelin apres une exception", "if ouvert    webserver.content_send(\"</script>\")    end", "webserver.content_send(\"</script>\")"),
    ("route redeclaree", "if (self.routePosee || self.facade() == nil)", "if (self.facade() == nil)"),
    ("maitre muet interroge a chaque rafraichissement", "if (self.maitreMuet == true && self.essaiMaitre != nil", "if (false && self.essaiMaitre != nil"),
    ("route sans controle d'acces", "if (!webserver.check_privileged_access())    return nil    end", ""),
    ("fins de course : repli sur le persist retire", "            self.gpioEnPanne = true\n            return e\n",
     "            self.gpioEnPanne = true\n            return nil\n"),
    ("fins de course : SwitchMode ignore", "(n == 0) == (mode == 2)", "(n == 0)"),
    ("fins de course : une ligne d'erreur par requete", "if (!self.gpioEnPanne)", "if true"),
]


def lance(berry, racine, sources):
    r = subprocess.run([str(berry), str(Path(__file__).with_suffix(".be")), str(sources)], cwd=str(racine),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser(description="Banc de la facade du rideau du garage")
    ap.add_argument("--sans-mutants", action="store_true")
    ap.add_argument("--sources", help="dossier de controleRideau.be a eprouver (defaut : celui de la carte au depot)")
    args = ap.parse_args()
    racine = trouve_racine()
    berry = trouve_berry(racine)
    sources = Path(args.sources).resolve() if args.sources else racine / CARTE
    sortie = lance(berry, racine, sources.as_posix())
    print(sortie, end="" if sortie.endswith("\n") else "\n")
    vert = "BANC_RIDEAU_FACADE: OK" in sortie
    if not args.sans_mutants:
        source = (sources / "controleRideau.be").read_text(encoding="utf-8")
        for nom, avant, apres in MUTANTS:
            if source.count(avant) != 1:
                print(f"KO   mutant '{nom}' : texte a muter introuvable (module modifie ?)")
                vert = False
                continue
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "controleRideau.be").write_text(source.replace(avant, apres), encoding="utf-8")
                rouge = "BANC_RIDEAU_FACADE: OK" not in lance(berry, racine, Path(tmp).as_posix())   # ECHEC ou plantage
            print(("OK   " if rouge else "KO   ") + f"mutant '{nom}' : banc rouge")
            vert = vert and rouge
    print("\n" + ("VERT" if vert else "ROUGE"))
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())
