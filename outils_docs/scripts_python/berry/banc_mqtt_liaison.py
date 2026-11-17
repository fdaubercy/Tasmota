"""Banc des garde-fous de la voie MQTT (data/fs/mqttLiaisonFonctions.be, plan tasks/plans/voie-mqtt.md A3).

UTILISATION
    python outils_docs/scripts_python/berry/banc_mqtt_liaison.py [--sans-mutants]
Depuis n'importe quel dossier. Code de sortie 0 = vert : le vrai module passe banc_mqtt_liaison.be ET chaque mutant
(copie du module avec un garde-fou retire) le fait echouer ; sans ces temoins, un vert ne prouverait rien.
Ne teste pas le vrai MQTT : le module est pur (bouchons : bouchons_berry/liaison_mqtt/).
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

# (nom, texte du module, remplacement) : chaque mutant retire un garde-fou que le banc doit voir
MUTANTS = [
    ("limiteur par element retire (G4)", "if size(self.emis[cle]) >= self.max_element", "if false"),
    ("coupe-circuit global retire (G5)", "if size(self.totaux) >= self.max_total", "if false"),
    ("ordre identique a l'etat connu envoye (G3)", "if a == nil && self.etats.find(cle) == valeur", "if false"),
    ("accuse jamais reconnu (retour = evenement)", "if valeur == a[\"valeur\"]", "if false"),
    ("renvois sans limite", "if a[\"essais\"] >= self.essais_max", "if false"),
    ("ancien etat repete pris pour un evenement", "if ancien == valeur    return \"inchange\"    end              # ancien",
     "if false    return \"inchange\"    end              # ancien"),
    ("doublon d'ordre en attente renvoye", "if a != nil && a[\"valeur\"] == valeur    return \"attente\"    end", ""),
    ("quarantaine jamais levee", "if fin - t > 0    return \"quarantaine\"    end", "if true    return \"quarantaine\"    end"),
    ("coupe-circuit jamais referme", "if t - self.coupe_jusqua >= 0", "if false"),
    ("renvoi bloque : echec sans abandon de l'ordre", "elif self.bloque(cle, t) != nil", "elif false"),
    ("cle ou valeur invalide acceptee", "if type(cle) == \"string\" && size(cle) > 0 && valeur != nil    return true    end", "return true"),
    ("valeur non convertie en texte (demande)", "        valeur = str(valeur)                       # 1 et", "        # 1 et"),
    ("1er retour sans etat connu pris pour un evenement", "if !connu    return \"initial\"    end                         # 1er", "# 1er"),
]


def lance(berry, racine, sources):
    r = subprocess.run([str(berry), str(Path(__file__).with_suffix(".be")), str(sources)], cwd=str(racine),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser(description="Banc de data/fs/mqttLiaisonFonctions.be")
    ap.add_argument("--sans-mutants", action="store_true")
    args = ap.parse_args()
    racine = trouve_racine()
    berry = trouve_berry(racine)
    sortie = lance(berry, racine, "data/fs")
    print(sortie, end="" if sortie.endswith("\n") else "\n")
    vert = "BANC_MQTT_LIAISON: OK" in sortie
    if not args.sans_mutants:
        source = (racine / "data" / "fs" / "mqttLiaisonFonctions.be").read_text(encoding="utf-8")
        for nom, avant, apres in MUTANTS:
            if source.count(avant) != 1:
                print(f"KO   mutant '{nom}' : texte a muter introuvable (module modifie ?)")
                vert = False
                continue
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "mqttLiaisonFonctions.be").write_text(source.replace(avant, apres), encoding="utf-8")
                rouge = "BANC_MQTT_LIAISON: OK" not in lance(berry, racine, Path(tmp).as_posix())   # ECHEC ou plantage
            print(("OK   " if rouge else "KO   ") + f"mutant '{nom}' : banc rouge")
            vert = vert and rouge
    print("\n" + ("VERT" if vert else "ROUGE"))
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())
