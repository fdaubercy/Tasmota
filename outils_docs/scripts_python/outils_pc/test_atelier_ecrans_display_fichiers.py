"""Banc des routes de l'onglet « display.ini » de l'atelier des ecrans (atelier_ecrans_display_fichiers, plan A12).

UTILISATION (Python de PlatformIO ; quelques secondes)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_ecrans_display_fichiers.py
Serveur du banc web (test_atelier_ecrans_web.Banc) devant une COPIE du depot. Verifie : liste des trois sources, lecture
expliquee, analyse et insertion, diff puis enregistrement dans la bibliotheque (catalogue regenere), copie d'un fichier
amont, notes datees ; refus : build en cours, empreinte perimee, nom hors bibliotheque ou chemin, fichier inconnu,
parametre inconnu ; amont et cartes jamais ecrits. Code de sortie 0 = vert.
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atelier_ecrans_catalogue as cat      # noqa: E402
import atelier_ecrans_display as adi        # noqa: E402
import test_atelier_ecrans_web as taw       # noqa: E402

AMONT = "ST7789_display.ini"
INI = taw.DEBITS


def test_lecture(b):
    s, r = b.requete("GET", "/display/liste")
    sources = {f["source"] for f in r["fichiers"]}
    carte = [f for f in r["fichiers"] if f["source"] == "carte" and f["nom"] == INI]
    taw.verifie((s, sources >= {"carte", "amont"}, len(carte), carte[0].get("bus") if carte else None),
                (200, True, 1, "RGB"), "GET /display/liste : cartes et amont, ecran de la carte des debits (RGB)")
    s, r = b.requete("GET", "/display/lire?source=carte&nom=" + INI)
    taw.verifie((s, r["modifiable"], r["analyse"]["bus"], r["analyse"]["erreurs"]), (200, False, "RGB", []),
                "GET /display/lire carte : analyse sans erreur, non modifiable")
    taw.verifie(b.requete("GET", "/display/lire?source=amont&nom=../../tasmota/user_config_override.h")[0], 404,
                "GET /display/lire amont : nom hors liste -> 404")
    taw.verifie(b.requete("GET", "/display/lire?source=perso&nom=../x")[0], 400, "GET /display/lire perso : chemin -> 400")
    taw.verifie(b.requete("GET", "/display/reference")[1]["bus"][0], "I2C", "GET /display/reference")
    s, r = b.requete("POST", "/display/analyse", {"texte": ":H,X,1,1,16,TRUC\n#\n"})
    taw.verifie((s, "bus" in " ".join(r["erreurs"])), (200, True), "POST /display/analyse : erreur de bus")
    s, r = b.requete("POST", "/display/inserer", {"texte": ":H,X,240,240,16,SPI,1,1,2,3,4,5,6,7,40\n#\n", "ligne": ":B"})
    taw.verifie((s, r["texte"].splitlines()[1][:3]), (200, ":B,"), "POST /display/inserer : :B apres :H")
    taw.verifie(b.requete("POST", "/display/inserer", {"texte": ":H\n", "ligne": ":Z"})[0], 400,
                "POST /display/inserer : parametre inconnu -> 400")


def test_ecriture(b):
    texte = b.requete("GET", "/display/lire?source=amont&nom=" + AMONT)[1]["texte"]
    avant = taw.instantane(b.racine)
    s, d = b.requete("POST", "/display/diff", {"nom": "mon-st7789", "texte": texte})
    taw.verifie((s, d["change"], d["empreinte"], d["rel"]), (200, True, None, cat.PERSO + "/mon-st7789.ini"),
                "POST /display/diff : copie d'un fichier amont vers la bibliotheque (fichier neuf)")
    taw.verifie(taw.instantane(b.racine), avant, "diff : rien n'est ecrit")
    b.builds = ["tasmota32-x"]
    taw.verifie(b.requete("POST", "/display/enregistrer", {"nom": "mon-st7789", "texte": texte, "empreinte": None})[0],
                409, "enregistrer pendant un build -> 409")
    b.builds = []
    taw.verifie(b.requete("POST", "/display/enregistrer", {"nom": "mon-st7789", "texte": texte, "empreinte": "x"})[0],
                409, "enregistrer avec une empreinte perimee -> 409")
    taw.verifie(b.requete("POST", "/display/enregistrer", {"nom": "../../data/x", "texte": texte, "empreinte": None})[0],
                400, "enregistrer hors bibliotheque -> 400")
    taw.verifie(taw.instantane(b.racine), avant, "refus : rien n'est ecrit")
    s, r = b.requete("POST", "/display/enregistrer", {"nom": "mon-st7789", "texte": texte, "empreinte": None})
    cle = [k for k, e in cat.charge(b.racine)["ecrans"].items() if e["display_ini"] == cat.PERSO + "/mon-st7789.ini"]
    taw.verifie((s, r["ecrits"][0], len(cle)), (200, cat.PERSO + "/mon-st7789.ini", 1),
                "enregistrer : fichier ecrit, ecran de la bibliotheque au catalogue")
    apres = taw.instantane(b.racine)
    hors = [k for k in apres if apres[k] != avant.get(k) and not k.startswith((cat.PERSO, cat.CATALOGUE))]
    taw.verifie(hors, [], "seuls la bibliotheque et le catalogue changent (amont et cartes intacts)")
    s, l = b.requete("GET", "/display/lire?source=perso&nom=mon-st7789")
    taw.verifie((s, l["modifiable"], l["texte"].splitlines() == texte.splitlines()), (200, True, True),
                "relecture du fichier de la bibliotheque (lignes identiques, fins de ligne LF)")
    s, d = b.requete("POST", "/display/diff", {"nom": "mon-st7789", "texte": texte.replace("#", ":B,40,34\n#", 1)})
    taw.verifie((d["empreinte"], d["ajouts"]), (l["empreinte"], 1), "diff d'une modification : empreinte du fichier, +1")
    s, n = b.requete("POST", "/display/notes", {"nom": "mon-st7789", "carte": INI, "texte": "rétroéclairage trop fort"})
    taw.verifie((s, "rétroéclairage trop fort" in n["notes"], f"({INI})" in n["notes"]), (200, True, True),
                "POST /display/notes : observation datee avec la carte")
    taw.verifie(b.requete("POST", "/display/notes", {"nom": "absent", "texte": "x"})[0], 404, "note sur un fichier absent -> 404")
    taw.verifie(b.requete("GET", "/display/lire?source=perso&nom=mon-st7789")[1]["notes"], n["notes"],
                "notes relues avec le fichier")


def main():
    with tempfile.TemporaryDirectory() as t:
        b = taw.Banc(t)
        (b.racine / adi.REFERENCE).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(taw.DEPOT / adi.REFERENCE, b.racine / adi.REFERENCE)
        try:
            test_lecture(b)
            test_ecriture(b)
        finally:
            b.ferme()
    print(f"\n{len(taw.ECHECS)} echec(s) : " + ("VERT" if not taw.ECHECS else "ROUGE"))
    return 1 if taw.ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
