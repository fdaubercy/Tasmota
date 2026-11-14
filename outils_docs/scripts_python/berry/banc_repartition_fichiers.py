"""Banc de la repartition des fichiers au demarrage (data/fs/gestionFileFolder.be::listeEtRepartitLesFichiers).

UTILISATION
    python outils_docs/scripts_python/berry/banc_repartition_fichiers.py [--sans-mutants]
Depuis n'importe quel dossier. Code de sortie 0 = vert : le vrai module passe banc_repartition_fichiers.be ET chaque
mutant (copie du module avec une protection retiree) le fait echouer. Ne teste pas LittleFS (bouchons : bouchons_berry/fsmqtt/).
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from banc_coprocesseur import trouve_berry, trouve_racine  # noqa: E402  (meme dossier : module voisin)

# (nom, texte du module, remplacement)
MUTANTS = [
    ("taille de la copie non controlee", "if ecrits != taille", "if false"),
    ("original supprime avant la copie", "var entree, sortie, relu\n", "var entree, sortie, relu\n    path.remove(source)\n"),
    ("copie sans temporaire", 'var temporaire = destination + ".tmp"', "var temporaire = destination"),
    ("temporaire laisse apres une panne", "path.remove(temporaire)\n        logFonctions", "logFonctions"),
    ("nom qui contient .tapp", 'string.endswith(nameFile, ".tapp")', 'string.find(nameFile, ".tapp") > -1'),
    ("deplacement retarde d'un demarrage", 'if !path.exists("/.extensions") && !path.mkdir("/.extensions")',
     'if !path.exists("/.extensions") path.mkdir("/.extensions") return elif false'),
    ("image : nom qui contient .png", 'string.endswith(nameFile, ".png", true)', 'string.find(nameFile, ".png") > -1'),
    ("images non rangees", 'filePath = "/sd/images/" + extension + "/" + nameFile', 'filePath = ""'),
    ("images sans dossier par format", 'filePath = "/sd/images/" + extension + "/" + nameFile', 'filePath = "/sd/images/" + nameFile'),
    ("dossier du format en minuscules", 'string.toupper(nameFile[(string.endswith(nameFile, ".webp", true) ? -4 : -3) ..])',
     'nameFile[(string.endswith(nameFile, ".webp", true) ? -4 : -3) ..]'),
    ("webp : dossier EBP (3 dernieres lettres)", '".webp", true) ? -4 : -3) ..])', '".webp", true) ? -3 : -3) ..])'),
    ("svg non range", ' || string.endswith(nameFile, ".svg", true) ||', ' ||'),
    ("webp non range", ' || string.endswith(nameFile, ".webp", true)\n', '\n'),
    ("svg : nom qui contient .svg", 'string.endswith(nameFile, ".svg", true)', 'string.find(nameFile, ".svg") > -1'),
    ("homonyme remplace sans le dire", '"REPARTITION_FICHIERS: %s remplace', '"REPARTITION_FICHIERS: %s ecrit'),
]


def lance(berry, racine, sources):
    r = subprocess.run([str(berry), str(Path(__file__).with_suffix(".be")), str(sources)], cwd=str(racine),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser(description="Banc de la repartition des fichiers")
    ap.add_argument("--sans-mutants", action="store_true")
    args = ap.parse_args()
    racine = trouve_racine()
    berry = trouve_berry(racine)
    sortie = lance(berry, racine, "data/fs")
    print(sortie, end="" if sortie.endswith("\n") else "\n")
    vert = "BANC_REPARTITION: OK" in sortie
    if not args.sans_mutants:
        source = (racine / "data" / "fs" / "gestionFileFolder.be").read_text(encoding="utf-8").replace("\r\n", "\n")
        for nom, avant, apres in MUTANTS:
            if source.count(avant) != 1:
                print(f"KO   mutant '{nom}' : texte a muter introuvable (module modifie ?)")
                vert = False
                continue
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "gestionFileFolder.be").write_text(source.replace(avant, apres), encoding="utf-8")
                sortie_m = lance(berry, racine, Path(tmp).as_posix())
            rouge = "BANC_REPARTITION: OK" not in sortie_m
            premier = next((l for l in sortie_m.splitlines() if l.startswith("KO")), sortie_m.strip()[-70:])
            print(("OK   " if rouge else "KO   ") + f"mutant '{nom}' : banc rouge ({premier[:70]})")
            vert = vert and rouge
    print("\n" + ("VERT" if vert else "ROUGE"))
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())
