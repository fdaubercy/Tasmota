"""Banc de la page « Systeme » construite par l'atelier (atelier_ecrans_systeme.py, plan atelier-ecrans A19).

UTILISATION (Python de PlatformIO ; quelques secondes)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_ecrans_systeme.py
Verifie : lecture de CHAMPS et des boutons dans data/fs/ecranSysteme.be ; deroule (un texte par champ, une barre par barre,
libelles, titres, boutons 120 et 121 avec leur toucher, tout dans la zone entre bandeau et barre, aucun chevauchement, copie
sans `modele`, idempotent) ; validateur (description des debits valide ; refus : modele inconnu, page 0, deux pages, objet a
la main, CHAMPS illisible, id hors groupe, id au-dela de 199, collision d'ids, place insuffisante) ; pages.jsonl de la carte
(chaque objet ecrit par ecranSysteme existe avec le bon type, attributs connus du catalogue, aucune action sur 120 et 121) ;
apercu de la page web (objets deroules envoyes). Le cote LVGL est prouve par berry/banc_page_systeme.py. Code de sortie 0 = vert.
"""
import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atelier_ecrans_catalogue as cat          # noqa: E402
import atelier_ecrans_description as aed        # noqa: E402
import atelier_ecrans_haspmota as ah            # noqa: E402
import atelier_ecrans_lvgl as al                # noqa: E402
import atelier_ecrans_navigation as nav         # noqa: E402
import atelier_ecrans_systeme as aes            # noqa: E402
import atelier_ecrans_web as aew                # noqa: E402

RACINE = Path(__file__).resolve().parents[3]
ENV = "tasmota32s3-bureau-ecran-debits-pac"
CARTE = RACINE / "data/bureau/tasmota32s3-ecran-debits-pac"
ECHECS = []
C = cat.charge(RACINE)
DESC = aed.charge(RACINE, ENV)


def verifie(cond, libelle, detail=""):
    print(("OK   " if cond else "KO   ") + libelle + ("" if cond else f"  ({detail})"), flush=True)
    if not cond:
        ECHECS.append(libelle)


def page_systeme(d):
    return next(p["n"] for p in d["pages"] if p.get("modele") == aes.MODELE)


def test_lecture():
    lu = aes.lit()
    verifie(lu is not None and len(lu["champs"]) >= 30 and (lu["gc"], lu["redemarrer"]) == (120, 121)
            and lu["texte_redemarrer"] == "Redémarrer", "lit : CHAMPS, boutons 120 et 121, texte du redemarrage", lu and len(lu["champs"]))


def test_deroule():
    n = page_systeme(DESC)
    d = nav.deroule(DESC, C)
    lu = aes.lit()
    objs = {o["id"]: o for o in d["objets"] if o["page"] == n}
    manque = [c[0] for c in lu["champs"] if objs.get(c[3], {}).get("type") != "label"
              or (c[4] is not None and objs.get(c[4], {}).get("type") != "bar")]
    verifie(not manque, "un label par texte, une barre par barre de CHAMPS", manque)
    verifie(all(objs.get(aes.ID_LIBELLE + i, {}).get("attributs", {}).get("text") == c[1] for i, c in enumerate(lu["champs"])),
            "libelles 130 + rang dans CHAMPS")
    verifie([objs[aes.ID_TITRE + g]["attributs"]["text"] for g in range(len(aes.GROUPES))] == [g[0] for g in aes.GROUPES],
            "titres des groupes 180 a 188")
    b = [objs.get(i) for i in (120, 121)]
    verifie(all(o and o["type"] == "btn" and o["h"] >= 40 and o["toucher"] == {"fonction": "ecranSysteme.appui", "args": [o["id"]]}
                for o in b), "boutons 120 et 121 : btn de 40 px au moins, toucher ecranSysteme.appui(id)")
    verifie(max(objs) <= 199 and not any(aes.ID_ICONE <= i <= aes.ID_MAX for i in objs), "ids <= 199, icones (190-199) reservees, non emises")
    bandeau = max(o["y"] + o["h"] for o in DESC["objets"] if o["page"] == 0)
    dehors = [i for i, o in objs.items() if o["y"] < bandeau or o["y"] + o["h"] > DESC["navigation"]["y"] or o["x"] + o["l"] > 1024]
    verifie(not dehors, "tout entre le bas du bandeau et le haut de la barre de navigation", dehors)
    r = list(objs.values())
    chevauche = [(a["id"], c["id"]) for i, a in enumerate(r) for c in r[i + 1:]
                 if a["x"] < c["x"] + c["l"] and c["x"] < a["x"] + a["l"] and a["y"] < c["y"] + c["h"] and c["y"] < a["y"] + a["h"]]
    verifie(not chevauche, "aucun objet n'en chevauche un autre", chevauche[:5])
    verifie(all("modele" not in p for p in d["pages"]) and any("modele" in p for p in DESC["pages"]),
            "deroule : copie sans modele, description d'origine intacte")
    verifie(nav.deroule(d, C) == d, "deroule idempotent")
    verifie(aes.deroule({"pages": [{"n": 1}], "objets": []}) == {"pages": [{"n": 1}], "objets": []}, "sans page a modele : inchangee")
    police = {o["attributs"].get("text_font") for o in r if o["type"] != "bar"}
    verifie(police == {"A:sd/polices/RobotoCondensed-Regular.ttf-14"}, "style voisin : police de la barre, une taille", police)


def refus(f, attendu, libelle, source=None):
    d = copy.deepcopy(DESC)
    f(d)
    ancien = aes.SOURCE
    try:
        if source is not None:
            aes.SOURCE = source
        m = aed.valide(d, C)
    finally:
        aes.SOURCE = ancien
    verifie(any(attendu in x for x in m), f"refus : {libelle}", m[:3])


def test_validateur():
    verifie(aed.valide(DESC, C) == [], "description des debits (page 4 Systeme) valide", aed.valide(DESC, C)[:3])
    n = page_systeme(DESC)
    p = lambda d: next(x for x in d["pages"] if x["n"] == n)
    refus(lambda d: p(d).update(modele="autre"), "modèle « autre » inconnu", "modele inconnu")
    refus(lambda d: d["pages"][0].update(modele="systeme"), "page n >= 1", "page Systeme sur la page 0")
    refus(lambda d: d["pages"][1].update(modele="systeme"), "une seule page Système", "deux pages Systeme")
    refus(lambda d: d["objets"].append({"id": 1, "page": n, "type": "label", "x": 0, "y": 0, "l": 9, "h": 9, "attributs": {}}),
          "aucun objet à la main", "objet a la main sur la page")
    refus(lambda d: d.update(ecran="ILI9342_320x240"), "place insuffisante", "ecran trop petit")
    source = aes.SOURCE.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as t:
        for nom, avant, apres, attendu in [
                ("CHAMPS illisible", '    ["ramMin", "RAM libre minimale", "Ko", 2, nil],', '    ["ramMin", "RAM libre minimale",\n "Ko", 2, nil],', "illisible"),
                ("id hors des groupes", '"Ko", 2, nil]', '"Ko", 125, nil]', "hors des groupes"),
                ("bouton au-dela de 199", "ecranSysteme.BOUTON_GC = 120", "ecranSysteme.BOUTON_GC = 220", "au-delà de 199"),
                ("collision d'ids (texte = barre d'un autre champ)", '"Ko", 2, nil]', '"Ko", 4, nil]', "en double"),
                ("constante du bouton absente", "ecranSysteme.BOUTON_REDEMARRER = 121", "ecranSysteme.BOUTON_X = 121", "illisible")]:
            verifie(source.count(avant) == 1, f"temoin « {nom} » : texte a remplacer present une fois")
            f = Path(t) / f"{len(nom)}.be"
            f.write_text(source.replace(avant, apres), encoding="utf-8")
            refus(lambda d: None, attendu, nom, f)
        trop = source.replace('    ["erreur5", "Erreur précédente", "", 105, nil]]',
                              "".join(f'    ["x{i}", "x", "", {106 + i}, nil],\n' for i in range(12)) + '    ["erreur5", "Erreur précédente", "", 105, nil]]')
        f = Path(t) / "trop.be"
        f.write_text(trop, encoding="utf-8")
        refus(lambda d: None, "au-delà de 199", "plus de 50 champs : libelles au-dela de 179", f)


def test_pages_jsonl():
    """Chaque (objet, attribut) ecrit par ecranSysteme existe dans le pages.jsonl de la carte, avec le bon type."""
    persist = json.loads((CARTE / "_persist.json").read_text(encoding="utf-8"))
    n = persist["modules"]["ecranSysteme"]["page"]
    verifie(n == page_systeme(DESC), "page du persist (modules.ecranSysteme.page) = page Systeme de la description", n)
    lignes = {(l["page"], l.get("id")): l for l in map(json.loads, (CARTE / "pages.jsonl").read_text(encoding="utf-8").splitlines()) if "obj" in l}
    fautes = []
    for c in aes.lit()["champs"]:
        for i, t, attrs in ((c[3], "label", ("text", "text_color")), (c[4], "bar", ("val", "bg_color10"))):
            if i is None:
                continue
            l = lignes.get((n, i))
            if l is None or l["obj"] != t or not all(cat.attribut_connu(C, t, a) for a in attrs):
                fautes.append(f"p{n}b{i}")
    verifie(not fautes, "pages.jsonl : chaque texte et barre ecrits par ecranSysteme, type et attributs connus", fautes)
    b = [lignes.get((n, i), {}) for i in (120, 121)]
    verifie(all(x.get("obj") == "btn" and "action" not in x for x in b) and cat.attribut_connu(C, "btn", "text"),
            "pages.jsonl : boutons 120 et 121 sans action (un seul appel : la regle de controleEcranSysteme)")
    verifie(ah.genere(DESC, C) == (CARTE / "pages.jsonl").read_text(encoding="utf-8").replace("\r\n", "\n")
            and al.genere(DESC, C) == (CARTE / "ecranLvgl.be").read_text(encoding="utf-8").replace("\r\n", "\n"),
            "pages.jsonl et ecranLvgl.be de la carte = sortie des generateurs")
    haspmota = (CARTE / "ecranHaspmota.be").read_text(encoding="utf-8")
    verifie("ecranHaspmota.page " not in haspmota and "ecranHaspmota.page=" not in haspmota,
            "ecranHaspmota sans membre page : ecranSysteme y ecrit des couleurs #RRGGBB")


def test_apercu():
    r = aew.apercu(RACINE, ENV, DESC)
    n = page_systeme(DESC)
    attendu = [o for o in nav.deroule(DESC, C)["objets"] if o["page"] == n]
    verifie(not r["erreurs"] and r["systeme"] == attendu and len(attendu) > 50, "apercu : objets deroules de la page Systeme envoyes",
            r["erreurs"][:3])
    d = copy.deepcopy(DESC)
    for p in d["pages"]:
        p.pop("modele", None)
    verifie(aew.apercu(RACINE, ENV, d)["systeme"] == [], "apercu sans page a modele : aucun objet systeme")


for t in (test_lecture, test_deroule, test_validateur, test_pages_jsonl, test_apercu):
    try:
        t()
    except Exception as e:  # noqa: BLE001 - un test qui leve compte rouge, les suivants tournent
        verifie(False, f"{t.__name__} : exception", repr(e))
print(f"{len(ECHECS)} echec(s) : {'VERT' if not ECHECS else 'ROUGE'}")
sys.exit(1 if ECHECS else 0)
