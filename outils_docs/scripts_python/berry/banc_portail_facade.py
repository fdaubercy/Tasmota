"""Banc de la page de l'esclave 4 : le portail seul (controlePortail.be du dossier de la carte, plan facade-garage-portail-commande, A8).

UTILISATION
    python outils_docs/scripts_python/berry/banc_portail_facade.py [--sans-mutants] [--sources <dossier de controlePortail.be>]
Depuis n'importe quel dossier. Code de sortie 0 = vert : le vrai module passe banc_portail_facade.be ET chaque mutant
(copie du module avec une regle retiree) le fait echouer. Ne teste ni le vrai serveur web, ni le reseau, ni le dessin
(banc test_volets.mjs et sonde outils_pc/test_volets_chrome.py, scenario portail seul).
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

CARTE = Path("data") / "garage" / "tasmota32s3-portail-jardin-modbus"
# (nom, texte du module, remplacement) : chaque mutant retire une regle que le banc doit voir
MUTANTS = [
    ("contact non ferme lu comme ferme", '(etat == "ON" ? 0 : (etat == "OFF" ? 100 : nil))', "0"),
    ("SwitchMode ignore", "(n == 0) == (mode == 2)", "(n == 0)"),
    ("repli sur le persist retire", "            self.gpioEnPanne = true\n            return e\n",
     "            self.gpioEnPanne = true\n            return nil\n"),
    ("une ligne d'erreur par requete", "if (!self.gpioEnPanne)", "if true"),
    ("</script> orphelin apres une exception", 'if ouvert    webserver.content_send("</script>")    end', 'webserver.content_send("</script>")'),
    ("route redeclaree", "if (self.routePosee || self.facade() == nil)", "if (self.facade() == nil)"),
    ("route sans controle d'acces", "if (!webserver.check_privileged_access())    return nil    end", ""),
    ("page non en lecture seule", '"lectureSeule": true', '"lectureSeule": false'),
    ("facade inactive quand meme servie", 'f.find("activation", "OFF") != "ON"', "false"),
    ("duree de course laissee a la page", '"tempsMontee": 0, "tempsDescente": 0', '"tempsMontee": 30, "tempsDescente": 30'),
]


def lance(berry, racine, sources):
    r = subprocess.run([str(berry), str(Path(__file__).with_suffix(".be")), str(sources)], cwd=str(racine),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser(description="Banc de la page de l'esclave 4 (portail)")
    ap.add_argument("--sans-mutants", action="store_true")
    ap.add_argument("--sources", help="dossier de controlePortail.be a eprouver (defaut : celui de la carte au depot)")
    args = ap.parse_args()
    racine = trouve_racine()
    berry = trouve_berry(racine)
    sources = Path(args.sources).resolve() if args.sources else racine / CARTE
    sortie = lance(berry, racine, sources.as_posix())
    print(sortie, end="" if sortie.endswith("\n") else "\n")
    vert = "BANC_PORTAIL_FACADE: OK" in sortie
    if not args.sans_mutants:
        source = (sources / "controlePortail.be").read_text(encoding="utf-8")
        for nom, avant, apres in MUTANTS:
            if source.count(avant) != 1:
                print(f"KO   mutant '{nom}' : texte a muter introuvable (module modifie ?)")
                vert = False
                continue
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "controlePortail.be").write_text(source.replace(avant, apres), encoding="utf-8")
                rouge = "BANC_PORTAIL_FACADE: OK" not in lance(berry, racine, Path(tmp).as_posix())   # ECHEC ou plantage
            print(("OK   " if rouge else "KO   ") + f"mutant '{nom}' : banc rouge")
            vert = vert and rouge
    print("\n" + ("VERT" if vert else "ROUGE"))
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())
