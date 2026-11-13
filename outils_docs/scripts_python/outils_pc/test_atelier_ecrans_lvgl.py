"""Banc du generateur LVGL pur de l'atelier des ecrans (description -> ecranLvgl.be). Code de sortie 0 = vert.
Python de PlatformIO. Lit le depot (ecran.json et ecranLvgl.be des debits), n'ecrit que dans un dossier temporaire.
Le comportement du module genere (objets, cache, couleurs, courbe, touchers) est verifie par berry/banc_ecran_lvgl.py."""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import atelier_ecrans_description as desc
import atelier_ecrans_lvgl as lvgl

RACINE = Path(__file__).resolve().parents[3]
ENV = "tasmota32s3-bureau-ecran-debits-pac"
FICHIER = RACINE / "data/bureau/tasmota32s3-ecran-debits-pac/ecranLvgl.be"
VERIFIE = RACINE / "outils_docs/scripts_python/berry/verifie_berry.py"
BERRY = RACINE / "lib/libesp32/berry/berry.exe"
BANC = "outils_docs/scripts_python/berry/banc_ecran_lvgl.be"
TEXTE = 'Débit "5" \\ 100 %'
ECHECS = []


def verifie(ok, libelle, detail=""):
    if not ok:
        ECHECS.append(libelle)
        print(f"ECHEC {libelle} {detail}")


def mini(objets, pages=None):
    return {"version": 1, "ecran": "ST7262_1024x600", "orientation": 0, "modele": [],
            "pages": pages or [{"n": 0, "titre": "C"}, {"n": 1, "titre": "A"}], "objets": objets}


def compile_berry(texte, dossier):
    """(code de sortie, sortie) de verifie_berry.py sur `texte` ecrit en ecranLvgl.be dans `dossier`."""
    f = Path(dossier) / "ecranLvgl.be"
    f.write_text(texte, encoding="utf-8", newline="\n")
    r = subprocess.run([sys.executable, str(VERIFIE), str(f)], cwd=RACINE, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    return r.returncode, r.stdout + r.stderr


def banc_mini(texte, dossier):
    """Sortie de banc_ecran_lvgl.be en mode mini sur `texte` (demarre, lignes TEXTE, touchers simules)."""
    f = Path(dossier) / "mini.be"
    f.write_text(texte, encoding="utf-8", newline="\n")
    (Path(dossier) / "banc").mkdir()
    r = subprocess.run([str(BERRY), BANC, str(Path(dossier) / "banc"), str(f), "mini"], cwd=RACINE, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=120, stdin=subprocess.DEVNULL)
    return r.stdout + r.stderr


def test_compile():
    with tempfile.TemporaryDirectory() as t:
        code, sortie = compile_berry(lvgl.genere(desc.charge(RACINE, ENV)), t)
        verifie(code == 0, "debits : le module genere compile", sortie[-800:])
        verifie(": avertissement:" not in sortie, "debits : charte des logs sans avertissement", sortie[-800:])
        code, sortie = compile_berry(lvgl.genere(desc.charge(RACINE, ENV)).replace("\nend\n", "\n", 1), t)
        verifie(code != 0, "temoin : un module casse ne compile pas (verifie_berry lit bien le fichier)", sortie[-300:])
        code, sortie = compile_berry(lvgl.genere(desc.charge(RACINE, ENV)).replace('"ECRAN_LVGL: ', '"ecran lvgl ', 1), t)
        verifie(": avertissement:" in sortie, "temoin : un prefixe de log hors charte est signale", sortie[-300:])


def test_texte_special():
    commande = 'Backlog Power1 "a\\b"; Dimmer 50%'
    d = mini([{"id": 1, "page": 1, "type": "label", "x": 1, "y": 2, "l": 30, "h": 10, "attributs": {"text": TEXTE}},
              {"id": 2, "page": 1, "type": "btn", "x": 0, "y": 20, "l": 60, "h": 40, "attributs": {"text": TEXTE},
               "toucher": {"commande": commande}},
              {"id": 3, "page": 0, "type": "btn", "x": 0, "y": 80, "l": 60, "h": 40, "attributs": {},
               "toucher": {"fonction": "ecranDebitsFonctions.ajuste", "args": ['x"y\\z', -1]}}])
    s = lvgl.genere(d)
    with tempfile.TemporaryDirectory() as t:
        code, sortie = compile_berry(s, t)
        verifie(code == 0 and ": avertissement:" not in sortie, "texte special : compile, sans avertissement", sortie[-500:])
        sortie = banc_mini(s, t)
        lignes = sortie.splitlines()
        verifie(f"TEXTE p1b1 {TEXTE}" in lignes and f"TEXTE p1b2 {TEXTE}" in lignes, "texte special restitue a l'identique",
                sortie[-800:])
        verifie(f"CLIC p1b2 CMD {commande}" in lignes, "commande restituee a l'identique et executee", sortie[-800:])
        verifie('CLIC p0b3 AJUSTE x"y\\z -1' in lignes, "fonction : arguments restitues", sortie[-800:])
        verifie("BANC_ECRAN_LVGL: OK" in sortie, "mini : demarre sans erreur", sortie[-800:])


def test_fichier_a_jour():
    verifie(FICHIER.is_file() and FICHIER.read_text(encoding="utf-8") == lvgl.genere(desc.charge(RACINE, ENV)),
            "ecranLvgl.be des debits = sortie du generateur (regenerer, ne pas editer)")


def test_taille():
    n = lvgl.genere(desc.charge(RACINE, ENV)).count("\n")
    verifie(n < 500, "debits : fichier genere sous 500 lignes", n)


def test_generique():
    s = lvgl.genere(mini([{"id": 1, "page": 1, "type": "label", "x": 0, "y": 0, "l": 9, "h": 9, "attributs": {"text": "a"}}]))
    for mot in ("ecranDebits", "L/min", "courbeMax", "voies", "historique"):
        verifie(mot not in s, f"generique : « {mot} » absent sans description des debits")


def test_courbe():
    d = mini([{"id": 7, "page": 1, "type": "chart", "x": 0, "y": 0, "l": 90, "h": 90, "attributs": {},
               "liaison": {"cle": "s", "attribut": "series", "points": "nb", "max": "a.haut", "couleurs": ["#010203", "#0A0B0C"]}},
              {"id": 8, "page": 1, "type": "label", "x": 0, "y": 0, "l": 9, "h": 9, "attributs": {},
               "liaison": {"cle": "v", "attribut": "text", "format": "%.1f bar", "echelle": 10}}])
    s = lvgl.genere(d)
    verifie('ecranLvgl.COURBE = ["p1b7", ["s"], ["nb"], [0x010203, 0x0A0B0C]]' in s, "courbe : series, compteur, couleurs lus dans la description",
            [l for l in s.splitlines() if "COURBE =" in l])
    verifie('["p1b7", ["a", "haut"], "y_max"' in s and '["p1b8", ["v"], "text", nil, nil, nil, "%.1f bar", 10]' in s,
            "courbe : haut d'axe et format lus dans la description")
    verifie("0x3FA7FF" not in s and "L/min" not in s, "courbe : aucune palette ni unite par defaut")
    series = re.search(r"SERIES = (\[.*\])", (RACINE / "data/bureau/tasmota32s3-ecran-debits-pac/ecranDebitsFonctions.be")
                       .read_text(encoding="utf-8")).group(1)
    li = next(o["liaison"] for o in desc.charge(RACINE, ENV)["objets"] if o.get("liaison", {}).get("attribut") == "series")
    verifie(li["couleurs"] == json.loads(series), "ecran.json : couleurs de la courbe = ecranDebitsFonctions.SERIES", series)


def test_palier2():
    """Un objet de chaque type du palier 2 : classe LVGL, appels du moteur (journal du bouchon lv), rappel VALUE_CHANGED ;
    l'action recoit la valeur choisie (fonction : dernier argument ; commande : %val%, interrupteur en 1 / 0)."""
    d = mini([{"id": 1, "page": 1, "type": "img", "x": 0, "y": 0, "l": 64, "h": 64, "attributs": {"src": "A:sd/images/PNG/pompe.png"}},
              {"id": 2, "page": 1, "type": "img", "x": 70, "y": 0, "l": 64, "h": 64, "attributs": {"src": "tasmota_logo"}},
              {"id": 3, "page": 1, "type": "dropdown", "x": 0, "y": 80, "l": 160, "h": 40,
               "attributs": {"options": "Auto\nMarche", "val": 1, "text": "Mode"},
               "toucher": {"fonction": "ecranDebitsFonctions.ajuste", "args": ["mode"]}},
              {"id": 4, "page": 1, "type": "switch", "x": 0, "y": 130, "l": 60, "h": 30, "attributs": {"val": True},
               "toucher": {"commande": "Power2 %val%"}},
              {"id": 5, "page": 1, "type": "switch", "x": 70, "y": 130, "l": 60, "h": 30, "attributs": {"val": False}},
              {"id": 6, "page": 1, "type": "roller", "x": 0, "y": 170, "l": 100, "h": 90, "attributs": {"options": "1\n2\n3", "val": 2},
               "toucher": {"fonction": "ecranDebitsFonctions.ajuste", "args": ["roue"]}},
              {"id": 7, "page": 1, "type": "qrcode", "x": 200, "y": 0, "l": 80, "h": 80,
               "attributs": {"qr_text": "http://x", "qr_dark_color": "#000000"}}])
    with tempfile.TemporaryDirectory() as t:
        sortie = banc_mini(lvgl.genere(d), t)
    lignes = sortie.splitlines()
    appels = [l for l in lignes if l.startswith(("APPEL ", "RAPPEL ", "OBJET ", "CLIC "))]
    for attendu in ("OBJET p1b1 image", "OBJET p1b3 dropdown", "OBJET p1b4 switch", "OBJET p1b6 roller", "OBJET p1b7 qrcode",
                    "APPEL p1b1 set_src ['A:sd/images/PNG/pompe.png']", "APPEL p1b2 set_tasmota_logo []",
                    "APPEL p1b3 set_options ['Auto\\nMarche']", "APPEL p1b3 set_text ['Mode']", "APPEL p1b3 set_selected [1]",
                    "APPEL p1b4 add_state [1]", "APPEL p1b5 remove_state [1]",
                    "APPEL p1b6 set_options ['1\\n2\\n3', 0]", "APPEL p1b6 set_selected [2, 0]",
                    "APPEL p1b7 set_size [80]", "RAPPEL p1b3 35", "RAPPEL p1b4 35",
                    "CLIC p1b3 AJUSTE mode 1", "CLIC p1b4 CMD Power2 1", "CLIC p1b6 AJUSTE roue 2"):
        verifie(any(l.startswith(attendu) for l in appels), f"palier 2 : {attendu}", sortie[-1500:])
    q = [l for l in appels if l.startswith("APPEL p1b7 ")]
    verifie([l.split()[2] for l in q][-1:] == ["update"] and "APPEL p1b7 update ['http://x', 8]" in q
            and any(" set_dark_color " in l for l in q), "palier 2 : QR code mis a jour apres taille et couleurs", q)
    verifie(not any(l.startswith("TEXTE p1b3") for l in lignes), "palier 2 : texte d'une liste deroulante sans label enfant")
    verifie("BANC_ECRAN_LVGL: OK" in sortie and "ERREUR" not in sortie, "palier 2 : demarre sans erreur", sortie[-800:])


def test_refus():
    for nom, o in (("fonction sans module", {"toucher": {"fonction": "ajuste"}}),
                   ("couleur mal formee", {"attributs": {"bg_color": "rouge"}}),
                   ("nom de fonction invalide", {"toucher": {"fonction": "a-b.c"}}),
                   ("type sans classe LVGL", {"type": "tab"}), ("conteneur fixed", {"type": "fixed"})):
        base = {"id": 1, "page": 1, "type": "btn", "x": 0, "y": 0, "l": 9, "h": 9, "attributs": {}}
        try:
            lvgl.genere(mini([{**base, **o}]))
            verifie(False, f"refus : {nom}")
        except ValueError:
            pass


for t in (test_compile, test_texte_special, test_fichier_a_jour, test_taille, test_generique, test_courbe, test_palier2, test_refus):
    try:
        t()
    except Exception as e:  # noqa: BLE001 - un test qui leve compte rouge, les suivants tournent
        verifie(False, f"{t.__name__} leve {type(e).__name__}", e)
print("ECHECS : " + ", ".join(ECHECS) if ECHECS else "BANC_ECRANS_LVGL: OK")
sys.exit(1 if ECHECS else 0)
