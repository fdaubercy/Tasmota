"""Banc de bout en bout de l'atelier des graphiques vers la carte (plan atelier-destinations, A11).

Cause racine des raccords manques jusque-la : chaque banc simulait SON cote. Ici les noms rendus par
`atelier_graphiques_televerse.plan` (cote atelier) traversent `build_fichiers.liste` (onglet Fichiers de la page Build) puis
l'envoi partiel `build_ota_fs.envoie_fs_ota` vers la carte simulee, et on verifie les chemins ECRITS sur la carte.
Lancer : "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_destinations_bout_en_bout.py
Copie temporaire du depot ; aucune carte reelle.
"""

import shutil
import sys
import tempfile
from pathlib import Path

import atelier_graphiques_graphiques as agg
import atelier_graphiques_televerse as agt
import build_fichiers
import build_ota_fs
import test_atelier_graphiques_televerse as tt
import test_atelier_graphiques_ecriture as tage
import test_build_ota_fs as tof
from build_ota_carte_simulee import Carte

verifie, ECHECS = tage.verifie, tage.ECHECS
CUVE = tage.CUVE


def test_graphiques_jusqu_a_la_carte(t):
    racine = tt.depot(t)
    dossier = tage.fbe.dossier_carte(CUVE)
    shutil.copy2(tage.DEPOT / dossier / "_persist.json", racine / dossier / "_persist.json")
    d = {"operation": "ajoute", "base": "depot",
         "graphique": {"type": "courbe", "titre": "V", "series": ["sensorsCuve.niveauCuve.volume"]}}
    muette = tt.Carte(morte=True)
    avant = agt.etat_avant(racine, CUVE)
    ecrits = agg.ecrit(racine, CUVE, d, agg.prevoit(racine, CUVE, d, get=muette)["empreinte"], tage.SANS_BUILD, get=muette)
    p = agt.plan(racine, CUVE, "graphiques", ecrits, avant, get=tt.Carte(presents=tt.TOUS - {"sd/js/graphiques_moteur.js"}))
    noms = p["fichiers"]
    verifie(noms[0], "graphiques.json", "plan : le fichier de la carte est nomme a la racine de l'image")
    # image de FS realiste : fichiers de la carte a la racine, sd/js/... dessous
    fabrique = {nom: (racine / dossier / nom).read_bytes() if (racine / dossier / nom).is_file() else b"// " + nom.encode() for nom in noms}
    image = build_fichiers.image(racine, CUVE)
    tof.fabrique_image(image, fabrique)
    liste = build_fichiers.liste(racine, CUVE)
    verifie(set(noms) <= {f["chemin"] for f in liste["fichiers"]}, True, "onglet Fichiers : tous les noms du plan sont dans la liste de l'image")
    carte = Carte()
    sauvegardes = Path(t) / "persist"
    sauvegardes.mkdir()
    fs = Path(t) / "fs"
    build_ota_fs.extrait_image(image, fs)
    build_ota_fs.envoie_fs_ota(CUVE, carte.ip, fs, sauvegardes, lambda r: None, fichiers=noms, redemarrer=False, **tof.RAPIDE)
    ecrits_carte = sorted(carte.flash)
    verifie("/json/graphiques.json" in ecrits_carte and "/graphiques.json" not in ecrits_carte, True,
            f"carte : graphiques.json ecrit dans /json/ (obtenu {ecrits_carte})")
    verifie(all(("/" + n) in ecrits_carte for n in noms if n != "graphiques.json"), True, "carte : /sd/js/graphiques_moteur.js et la page /graphiques ecrits la ou ils sont lus")
    carte.ferme()


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as t:
        test_graphiques_jusqu_a_la_carte(t)
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    sys.exit(1 if ECHECS else 0)
