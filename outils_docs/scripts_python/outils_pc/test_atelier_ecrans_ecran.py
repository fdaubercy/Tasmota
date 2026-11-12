"""Banc du changement d'ecran de l'atelier des ecrans (atelier_ecrans_ecran.py), plan atelier-ecrans A8.

UTILISATION (copie temporaire du depot ; ~10 s)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_ecrans_ecran.py
Verifie : mise a l'echelle 1024 x 600 -> 480 x 320 (positions et tailles au rapport, polices ramenees a une taille
compilee, bouton de 46 px -> 25 px signale) ; changement de l'ecran des debits vers l'ILI9488 : diff du display.ini,
ecriture des quatre fichiers, ecran de l'env relu ; carte de l'ILI9488 vers le 7B : conflit de broches refuse, rien
d'ecrit ; ecran inconnu refuse. Code de sortie 0 = vert.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atelier_ecrans_catalogue as cat     # noqa: E402
import atelier_ecrans_description as aed   # noqa: E402
import atelier_ecrans_ecran as aec         # noqa: E402
import test_atelier_ecrans_web as taw      # noqa: E402

ENV = "tasmota32s3-bureau-ecran-debits-pac"
SERVEUR = "tasmota32s3-bureau-serveur-debits-pac"
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)


def objet(d, page, id_):
    return next(o for o in d["objets"] if o["page"] == page and o["id"] == id_)


def main():
    with tempfile.TemporaryDirectory(prefix="banc_atelier_ecran_") as t:
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "donnees")
        racine = Path(t) / "depot"
        racine.mkdir()
        taw.copie(racine)
        catalogue, desc = cat.charge(racine), aed.charge(racine, ENV)

        d, av = aec.met_a_echelle(desc, "ILI9488_480x320", catalogue)
        b = objet(d, 0, 91)
        verifie((d["ecran"], b["x"], b["y"], b["l"], b["h"]), ("ILI9488_480x320", 11, 288, 52, 25), "bouton 91 : position et taille au rapport")
        verifie(any("objet 91" in a and "25 px" in a for a in av), True, "bouton de 46 px -> 25 px signale (cible tactile)")
        verifie(objet(d, 1, 11)["attributs"]["text_font"], 12, "police robotocondensed 24 -> 12 (taille compilee la plus proche)")
        verifie(objet(d, 1, 13)["attributs"]["text_font"], "A:sd/polices/RobotoCondensed-Regular.ttf-17", "police .ttf de taille libre arrondie (36 -> 17)")
        verifie(aec.police_echelle("montserrat-28", 0.469, catalogue), "montserrat-14", "montserrat 28 -> 14")
        verifie(aed.valide(d, catalogue), [], "description mise a l'echelle valide pour le nouvel ecran")
        verifie(objet(desc, 0, 91)["h"], 46, "description d'origine intacte")

        c = aec.changement(racine, ENV, "ILI9488_480x320", desc)
        rels = [f["rel"] for f in c["fichiers"]]
        dini = f"data/bureau/tasmota32s3-ecran-debits-pac/display.ini"
        verifie((c["refus"], dini in rels), ([], True), "debits -> ILI9488 : pas de conflit, display.ini au diff")
        ini = next(f for f in c["fichiers"] if f["rel"] == dini)
        verifie((ini["avant"].startswith(":H,ST7262"), ini["apres"].startswith(":H,ILI9488")), (True, True), "display.ini repris de l'env qui porte l'ILI9488")
        emp_desc = aed.empreinte(aed.chemin(racine, ENV).read_bytes())
        r = aec.change(racine, ENV, "ILI9488_480x320", desc, c["empreinte"], emp_desc, lambda: [])
        verifie((len(r["ecrits"]), cat.ecrans_des_envs(racine).get(ENV), aed.charge(racine, ENV)["ecran"]), (4, "ILI9488_480x320", "ILI9488_480x320"),
                "changement ecrit : 4 fichiers, ecran de l'env et de la description relus")

        avant = (racine / "data/bureau/tasmota32s3-serveur-debits-pac/display.ini").read_bytes()
        vide = {"version": 1, "ecran": "ILI9488_480x320", "orientation": 0, "modele": [], "couleurs": {},
                "pages": [{"n": 0, "titre": "Commun"}, {"n": 1, "titre": "P1"}], "objets": []}
        c = aec.changement(racine, SERVEUR, "ST7262_1024x600", vide)
        verifie((any("GPIO18" in x and "ModBus TX" in x for x in c["refus"]), any("integre" in a for a in c["avertissements"])), (True, True),
                "ILI9488 -> 7B : broche ModBus TX prise refusee, ecran integre signale")
        try:
            aec.change(racine, SERVEUR, "ST7262_1024x600", vide, c["empreinte"], None, lambda: [])
            verifie("ecrit", "refus", "conflit de broches : ecriture refusee")
        except RuntimeError as e:
            verifie("refuse" in str(e), True, "conflit de broches : ecriture refusee")
        verifie((racine / "data/bureau/tasmota32s3-serveur-debits-pac/display.ini").read_bytes(), avant, "conflit : display.ini intact")
        verifie(aec.broches_ecran(":H,ST7262,1024,600,16,RGB,5,3,46,7,-1,48,47,21,1,2,42,41,40,14,38,18,17,10,39,0,45,30")[0][-3:],
                [39, 0, 45], "ligne :H RGB : la frequence (30) n'est pas une broche")
        try:
            aec.changement(racine, ENV, "ILI9488_480x320", {"objets": "pas une liste"})
            verifie("accepte", "refus", "description mal formee refusee (ValueError, pas d'exception brute)")
        except ValueError:
            verifie(True, True, "description mal formee refusee (ValueError, pas d'exception brute)")
        try:
            aec.changement(racine, ENV, "ECRAN_INCONNU", desc)
            verifie("accepte", "refus", "ecran inconnu refuse")
        except ValueError:
            verifie(True, True, "ecran inconnu refuse")
    print(f"\n{len(ECHECS)} echec(s) : " + ("VERT" if not ECHECS else "ROUGE"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
