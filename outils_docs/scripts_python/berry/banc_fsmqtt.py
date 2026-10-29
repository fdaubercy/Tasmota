"""Banc du recepteur de fichiers par MQTT des cartes (data/fs/fsMqtt.be, A16 de la page Build 7700).

UTILISATION
    python outils_docs/scripts_python/berry/banc_fsmqtt.py [--sans-mutants]
Depuis n'importe quel dossier. Code de sortie 0 = vert : le vrai module passe banc_fsmqtt.be ET chaque mutant
(copie du module avec un controle retire) le fait echouer ; sans ces temoins, un vert ne prouverait rien.
Ne teste ni le vrai MQTT, ni LittleFS, ni le vrai MD5 (bouchons : bouchons_berry/fsmqtt/).
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from banc_coprocesseur import trouve_berry, trouve_racine  # noqa: E402  (meme dossier : module voisin)

# (nom, texte du module, remplacement) : chaque mutant retire un controle que le banc doit voir
MUTANTS = [
    ("position non controlee", "if position == t[\"recus\"] && size(b) > 4", "if size(b) > 4"),
    ("MD5 non controle", "if md5 != t[\"md5\"]", "if false"),
    ("formatage sans controle de son resultat", "if !path.format(true)", "if path.format(true) && false"),
]


def lance(berry, racine, sources):
    r = subprocess.run([str(berry), str(Path(__file__).with_suffix(".be")), str(sources)], cwd=str(racine),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser(description="Banc de data/fs/fsMqtt.be")
    ap.add_argument("--sans-mutants", action="store_true")
    args = ap.parse_args()
    racine = trouve_racine()
    berry = trouve_berry(racine)
    sortie = lance(berry, racine, "data/fs")
    print(sortie, end="" if sortie.endswith("\n") else "\n")
    vert = "BANC_FSMQTT: OK" in sortie
    if not args.sans_mutants:
        source = (racine / "data" / "fs" / "fsMqtt.be").read_text(encoding="utf-8")
        for nom, avant, apres in MUTANTS:
            if source.count(avant) != 1:
                print(f"KO   mutant '{nom}' : texte a muter introuvable (module modifie ?)")
                vert = False
                continue
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "fsMqtt.be").write_text(source.replace(avant, apres), encoding="utf-8")
                rouge = "BANC_FSMQTT: OK" not in lance(berry, racine, Path(tmp).as_posix())   # ECHEC ou plantage
            print(("OK   " if rouge else "KO   ") + f"mutant '{nom}' : banc rouge")
            vert = vert and rouge
    print("\n" + ("VERT" if vert else "ROUGE"))
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())
