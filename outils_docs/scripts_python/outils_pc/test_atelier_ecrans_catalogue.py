"""Banc du catalogue de l'atelier des ecrans (objets, attributs, polices, ecrans). Code de sortie 0 = vert.
Python de PlatformIO. Le temoin travaille sur une copie temporaire des sources, jamais sur le depot."""

import json
import shutil
import sys
import tempfile
from pathlib import Path

import atelier_ecrans_catalogue as cat
import fichiers_berry_ini as fbi

RACINE = Path(__file__).resolve().parents[3]
ECHECS = []


def verifie(ok, libelle, detail=""):
    if not ok:
        ECHECS.append(libelle)
        print(f"ECHEC {libelle} {detail}")


def copie_sources(dest):
    """Copie ce que lit le catalogue (SOURCES, data/*/*/{display.ini,pages.jsonl,*.ttf,_persist.json}, catalogue)."""
    rels = list(cat.SOURCES) + [cat.CATALOGUE] + list(fbi.FICHIERS_INI)
    for motif in ("display.ini", "pages.jsonl", "*.ttf", "_persist.json"):
        rels += [p.relative_to(RACINE).as_posix() for p in RACINE.glob(f"data/*/*/{motif}")]
    rels += [p.relative_to(RACINE).as_posix() for p in RACINE.glob(f"{cat.AMONT}/*.ini")]
    rels += [p.relative_to(RACINE).as_posix() for p in RACINE.glob(f"{cat.PERSO}/*.ini")]
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
    a = e.get("ST7262_1024x600", {})
    verifie(a.get("bus") == "RGB" and a.get("tactile") is True and (a.get("largeur"), a.get("hauteur")) == (1024, 600), "ST7262", a)
    verifie((a.get("source"), a.get("bpp"), a.get("couleur")) == ("carte", 16, True), "ST7262 : carte, 16 bpp, couleur", a)
    verifie({"tasmota32s3-bureau-ecran-debits-pac", "tasmota32s3-cave-ecran"} <= set(a.get("envs", [])), "envs du 7B", a.get("envs"))
    verifie(a.get("display_ini", "").startswith("data/") and a["display_ini"].endswith("display.ini"), "chemin display.ini")
    serveur = "tasmota32s3-bureau-serveur-debits-pac"
    verifie(not any(serveur in x.get("envs", []) for x in e.values()), "display.ini exclu du FS : ecran non rattache a la carte")
    amont = [k for k, x in e.items() if x.get("source") == "amont"]
    verifie(len(amont) >= 50 and all(e[k]["display_ini"].startswith(cat.AMONT + "/") for k in amont), "ecrans amont lus", len(amont))
    verifie(e.get("ILI9488_480x320", {}).get("source") == "amont", "ILI9488 : pris a l'amont", e.get("ILI9488_480x320"))
    doublons = [k for k in e if "@" in k]
    verifie(len(doublons) >= 4 and all(k.split("@")[1] == Path(e[k]["display_ini"]).stem for k in doublons),
            "collision : <pilote>_<l>x<h>@<fichier>", doublons[:6])
    par_fichier = {Path(x["display_ini"]).stem: x for x in e.values()}
    verifie(par_fichier.get("WT32_SC01_Plus", {}).get("tactile") is True, "tactile par :TI (WT32_SC01_Plus)")
    verifie(par_fichier.get("ILI9488_XPT2046_display", {}).get("tactile") is True, "tactile par :TS (ILI9488_XPT2046)")
    verifie(par_fichier.get("SSD1306_128x64_display", {}).get("couleur") is False, "SSD1306 : bpp 1, pas couleur",
            par_fichier.get("SSD1306_128x64_display"))


def test_bibliotheque_perso():
    with tempfile.TemporaryDirectory() as t:
        copie = Path(t)
        copie_sources(copie)
        perso = copie / cat.PERSO
        perso.mkdir(parents=True, exist_ok=True)
        (perso / "Mon7B.ini").write_text(":H,ST7262,1024,600,16,RGB,40,41,39,42,2,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,14\n#\n",
                                          encoding="utf-8")
        (perso / "Rond.ini").write_text(":H,GC9A01X,240,240,16,SPI,1,10,11,12,13,14,-1,-1,40\n:UTI,CST816S,I1,15,-1,-1\n#\n",
                                         encoding="utf-8")
        (perso / "Rond.notes.md").write_text("notes\n", encoding="utf-8")
        e = cat.ecrans(copie)
        verifie(e.get("ST7262_1024x600", {}).get("source") == "carte", "carte prioritaire sur la bibliotheque")
        verifie(e.get("ST7262_1024x600@Mon7B", {}).get("source") == "perso", "bibliotheque : collision suffixee")
        r = e.get("GC9A01X_240x240", {})
        verifie((r.get("source"), r.get("tactile"), r.get("display_ini")) == ("perso", True, f"{cat.PERSO}/Rond.ini"),
                "bibliotheque : ecran neuf, tactile :UTI", r)
        verifie(not any("notes" in x["display_ini"] for x in e.values()), "notes de terrain ignorees")


def test_env_sans_ecran():
    m = cat.ecrans_des_envs(RACINE)
    verifie(m.get("tasmota32s3-bureau-ecran-debits-pac") == "ST7262_1024x600", "cle d'ecran de l'env")
    verifie(m.get("tasmota32s3-cave-serveur-rly") is None, "env sans display.ini -> None", m.get("tasmota32s3-cave-serveur-rly"))
    verifie(m.get("tasmota32s3-bureau-serveur-debits-pac", "absent") is None, "display.ini exclu du FS -> None",
            m.get("tasmota32s3-bureau-serveur-debits-pac", "absent"))
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
    test_bibliotheque_perso()
    test_env_sans_ecran()
    test_temoin_police_retiree()
    test_fichier_a_jour()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1 if ECHECS else 0)
