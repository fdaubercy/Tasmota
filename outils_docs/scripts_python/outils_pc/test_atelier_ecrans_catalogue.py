"""Banc du catalogue de l'atelier des ecrans (objets, attributs, polices, ecrans). Code de sortie 0 = vert.
Python de PlatformIO. Le temoin travaille sur une copie temporaire des sources, jamais sur le depot."""

import json
import shutil
import sys
import tempfile
from pathlib import Path

import atelier_ecrans_catalogue as cat

RACINE = Path(__file__).resolve().parents[3]
ECHECS = []


def verifie(ok, libelle, detail=""):
    if not ok:
        ECHECS.append(libelle)
        print(f"ECHEC {libelle} {detail}")


def copie_sources(dest):
    """Copie ce que lit le catalogue (SOURCES, data/*/*/{display.ini,pages.jsonl,*.ttf,_persist.json}, catalogue)."""
    rels = list(cat.SOURCES) + [cat.CATALOGUE]
    for motif in ("display.ini", "pages.jsonl", "*.ttf", "_persist.json"):
        rels += [p.relative_to(RACINE).as_posix() for p in RACINE.glob(f"data/*/*/{motif}")]
    for rel in rels:
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(RACINE / rel, dest / rel)


def test_objets_palier(c):
    for t in ("label", "btn", "bar", "obj", "chart", "arc", "slider"):
        verifie(c["objets"].get(t, {}).get("palier") == 1, f"palier 1 : {t}")
    autres = [t for t, o in c["objets"].items() if t not in cat.PALIER1]
    verifie(len(autres) >= 10 and all(c["objets"][t]["palier"] == 2 for t in autres), "autres classes en palier 2", autres)
    for t in ("dropdown", "roller", "img", "switch"):
        verifie(t in c["objets"], f"classe {t} presente")


def test_attributs_pages_debits(c):
    n = 0
    for f in RACINE.glob("data/bureau/*debits-pac/pages.jsonl"):
        for ligne in f.read_text(encoding="utf-8").splitlines():
            if not ligne.startswith("{"):
                continue
            j = json.loads(ligne)
            type_ = j.get("obj", "scr")                      # sans "obj" : l'objet 0 de la page (fond)
            for k in j:
                if k in ("page", "id", "obj", "comment"):
                    continue
                n += 1
                verifie(cat.attribut_connu(c, type_, k), f"attribut {k} de {type_} ({f.parent.name})")
    verifie(n > 50, "pages.jsonl des debits lus", n)
    verifie(c["objets"]["btn"]["attributs"]["action"]["type"] == "action", "type action")
    verifie(c["objets"]["label"]["attributs"]["text_color"]["type"] == "couleur", "type couleur")
    verifie(c["objets"]["label"]["attributs"]["text_font"]["type"] == "police", "type police")
    verifie(not cat.attribut_connu(c, "label", "inexistant_xyz"), "attribut inconnu refuse")


def test_polices(c):
    ttf = [p for p in c["polices"] if p["source"] == "sd" and p.get("fichier") == "RobotoCondensed-Regular.ttf"]
    verifie(len(ttf) == 1, "ttf RobotoCondensed de la carte")
    if ttf:
        verifie({20, 24, 32, 36} <= set(ttf[0]["tailles"]), "tailles ttf 20 24 32 36", ttf[0]["tailles"])
        verifie("A:sd/polices/" in ttf[0]["ecriture"], "ecriture ttf reconnaissable")
    emb = [p for p in c["polices"] if p["nom"] == "robotocondensed"]
    verifie(len(emb) == 1 and emb[0]["source"] == "firmware" and 24 in emb[0]["tailles"], "robotocondensed embarquee 24")
    verifie(emb and 36 not in emb[0]["tailles"], "36 non compilee en embarque (donc ttf)")
    verifie(any(p["nom"] == "montserrat" for p in c["polices"]), "montserrat presente")


def test_ecrans(c):
    e = c["ecrans"]
    verifie(set(e) == {"ST7262_1024x600", "ILI9488_480x320"}, "deux ecrans", sorted(e))
    a, b = e.get("ST7262_1024x600", {}), e.get("ILI9488_480x320", {})
    verifie(a.get("bus") == "RGB" and a.get("tactile") is True and (a.get("largeur"), a.get("hauteur")) == (1024, 600), "ST7262", a)
    verifie(b.get("bus") == "SPI" and b.get("tactile") is True, "ILI9488", b)
    verifie("tasmota32s3-bureau-ecran-debits-pac" in a.get("envs", []), "env de l'ecran des debits")
    verifie(a.get("display_ini", "").endswith("display.ini"), "chemin display.ini")


def test_env_sans_ecran():
    m = cat.ecrans_des_envs(RACINE)
    verifie(m.get("tasmota32s3-bureau-ecran-debits-pac") == "ST7262_1024x600", "cle d'ecran de l'env")
    verifie(m.get("tasmota32s3-cave-serveur-rly") is None, "env sans display.ini -> None", m.get("tasmota32s3-cave-serveur-rly"))
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / "display.ini"
        verifie(cat.lit_ecran(f) is None, "fichier absent -> None")
        f.write_text(":S,2,1,1,0,40,20\n:I\n", encoding="utf-8")
        verifie(cat.lit_ecran(f) is None, "sans :H -> None")
        f.write_text(":H,ILI9488,abc\n", encoding="utf-8")
        verifie(cat.lit_ecran(f) is None, ":H illisible -> None")


def test_temoin_police_retiree():
    with tempfile.TemporaryDirectory() as t:
        copie = Path(t)
        copie_sources(copie)
        verifie(cat.verifie(copie) == [], "copie intacte : a jour", cat.verifie(copie))
        for ttf in copie.glob("data/*/*/*.ttf"):
            ttf.unlink()
        ecarts = cat.verifie(copie)
        verifie(any("polices" in e for e in ecarts), "ttf retire -> ecart polices", ecarts)
        copie_sources(copie)
        conf = copie / cat.LV_CONF
        conf.write_text(conf.read_text(encoding="utf-8").replace(
            "ROBOTOCONDENSED_REGULAR_24_LATIN1  1", "ROBOTOCONDENSED_REGULAR_24_LATIN1  0"), encoding="utf-8")
        ecarts = cat.verifie(copie)
        verifie(any("polices" in e for e in ecarts), "police embarquee retiree -> ecart", ecarts)


def test_fichier_a_jour():
    verifie(cat.verifie(RACINE) == [], "catalogue du depot a jour", cat.verifie(RACINE))


if __name__ == "__main__":
    try:
        c = cat.genere(RACINE)
    except Exception as e:                                   # noqa: BLE001 : le banc doit afficher la cause
        print("ECHEC genere :", repr(e))
        sys.exit(1)
    test_objets_palier(c)
    test_attributs_pages_debits(c)
    test_polices(c)
    test_ecrans(c)
    test_env_sans_ecran()
    test_temoin_police_retiree()
    test_fichier_a_jour()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1 if ECHECS else 0)
