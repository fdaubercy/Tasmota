"""Banc de la barre de navigation construite d'apres les pages (atelier_ecrans_navigation.py, plan atelier-ecrans A17).

UTILISATION (Python de PlatformIO ; quelques secondes)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_ecrans_navigation.py
Verifie : un bouton par page n >= 1 du menu (ordre des pages, `menu: false` exclu, id 200 + n, texte = titre, largeur
d'apres le titre et la police, ecart), validateur (forme, ids reserves, debordement, `menu` booleen), deux generateurs
(action p<n> et couleurs `actif` de la page de depart dans le pages.jsonl ; touchers et ACTIFS dans l'interface LVGL),
description sans `navigation` inchangee. Code de sortie 0 = vert.
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atelier_ecrans_catalogue as cat          # noqa: E402
import atelier_ecrans_description as aed        # noqa: E402
import atelier_ecrans_haspmota as ah            # noqa: E402
import atelier_ecrans_lvgl as al                # noqa: E402
import atelier_ecrans_navigation as nav         # noqa: E402

RACINE = Path(__file__).resolve().parents[3]
ECHECS = []
POLICE = "A:sd/polices/RobotoCondensed-Regular.ttf-20"
BASE = {"version": 1, "ecran": "ST7262_1024x600", "orientation": 0, "modele": [],
        "pages": [{"n": 0, "titre": "Commun"}, {"n": 1, "titre": "Débits"}, {"n": 2, "titre": "Courbes"},
                  {"n": 3, "titre": "Réglages"}, {"n": 4, "titre": "Confirmation", "menu": False}],
        "objets": [{"id": 1, "page": 1, "type": "label", "x": 0, "y": 0, "l": 100, "h": 30, "attributs": {"text": "a"}}],
        "navigation": {"x": 24, "y": 540, "h": 46, "ecart": 12,
                       "attributs": {"radius": 23, "border_width": 0, "text_font": POLICE, "bg_color": "#1F2B38", "text_color": "#E8EDF2"},
                       "actif": {"bg_color": "#3FA7FF", "text_color": "#06121F"}}}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)


def mutant(f):
    d = copy.deepcopy(BASE)
    f(d)
    return d


def test_boutons():
    b = nav.boutons(BASE)
    verifie([(o["id"], o["page"], o["type"], o["attributs"]["text"], o["toucher"]) for o in b],
            [(201, 0, "btn", "Débits", {"page": 1}), (202, 0, "btn", "Courbes", {"page": 2}), (203, 0, "btn", "Réglages", {"page": 3})],
            "un bouton par page du menu, dans l'ordre des pages, page de confirmation exclue")
    verifie([(o["x"], o["y"], o["l"], o["h"]) for o in b], [(24, 540, 112, 46), (148, 540, 123, 46), (283, 540, 134, 46)],
            "largeur = titre x police x 0,55 + h (arrondi au plus proche), ecart de 12 px")
    verifie((b[0]["actif"], b[0]["attributs"]["bg_color"]), ({"bg_color": "#3FA7FF", "text_color": "#06121F"}, "#1F2B38"),
            "style et couleurs actif recopies")
    sans = mutant(lambda d: d.pop("navigation"))
    verifie(nav.deroule(sans), sans, "sans navigation : description inchangee")
    d = nav.deroule(BASE)
    verifie(("navigation" in BASE, len(d["objets"]), BASE["objets"] == mutant(lambda x: None)["objets"]), (True, 4, True),
            "deroule : copie, la description d'origine n'est pas touchee")
    p = mutant(lambda d: d["pages"][2].pop("titre"))
    verifie(nav.boutons(p)[1]["attributs"]["text"], "Page 2", "page sans titre : « Page n »")
    verifie((nav.taille(24), nav.taille("montserrat-28"), nav.taille(POLICE), nav.taille(None)), (24, 28, 20, 14),
            "taille : entier, nom-taille, ttf-taille, 14 par defaut")


MUTANTS = [
    ("navigation sans h", lambda d: d["navigation"].pop("h"), "navigation"),
    ("navigation : ecart negatif", lambda d: d["navigation"].update(ecart=-1), "navigation"),
    ("navigation : attribut inconnu d'un bouton", lambda d: d["navigation"]["attributs"].update(zorglub=1), "zorglub"),
    ("navigation : couleur actif mal formee", lambda d: d["navigation"]["actif"].update(bg_color="bleu"), "actif"),
    ("navigation : barre trop large", lambda d: d["navigation"].update(x=800), "barre de navigation"),
    ("navigation : barre sous l'ecran", lambda d: d["navigation"].update(y=580), "barre de navigation"),
    ("navigation : id reserve pris par un objet", lambda d: d["objets"].append(
        {"id": 202, "page": 0, "type": "label", "x": 0, "y": 0, "l": 9, "h": 9, "attributs": {}}), "réservé"),
    ("page : menu non booleen", lambda d: d["pages"][4].update(menu=0), "menu"),
    ("navigation : page 55 hors des ids reserves", lambda d: d["pages"].append({"n": 55, "titre": "x"}), "55"),
    ("navigation : aucune page dans le menu", lambda d: [p.update(menu=False) for p in d["pages"]], "aucune page"),
]


def test_validateur(c):
    verifie(aed.valide(BASE, c), [], "description avec barre de navigation valide")
    for nom, f, fragment in MUTANTS:
        msgs = aed.valide(mutant(f), c)
        verifie(any(fragment in m for m in msgs), True, f"mutant refuse : {nom} ({msgs[:2]})")


def test_generateurs():
    lignes = [json.loads(x) for x in ah.genere(BASE).splitlines() if x.strip()]
    b = [x for x in lignes if x.get("page") == 0 and x.get("id", 0) > 200]
    verifie([(x["id"], x["action"], x["text"], x["bg_color"]) for x in b],
            [(201, "p1", "Débits", "#3FA7FF"), (202, "p2", "Courbes", "#1F2B38"), (203, "p3", "Réglages", "#1F2B38")],
            "pages.jsonl : boutons de la barre, page de depart en couleurs actif")
    s = al.genere(BASE)
    verifie(all(f"def ecranLvgl_p0b20{i}()" in s for i in (1, 2, 3)) and '["p0b201", 1, {' in s, True,
            "ecranLvgl.be : un toucher par bouton, couleurs actif dans ACTIFS")


def test_echelle(c):
    import atelier_ecrans_ecran as aee
    cible = next(k for k, e in c["ecrans"].items() if (e["largeur"], e["hauteur"]) == (480, 320))
    d = mutant(lambda d: d["objets"].append({"id": 9, "page": 1, "type": "qrcode", "x": 0, "y": 0, "l": 120, "h": 120,
                                             "attributs": {"qr_text": "x"}}))
    e, _ = aee.met_a_echelle(d, cible, c)
    q = [o for o in e["objets"] if o["type"] == "qrcode"][0]
    verifie((e["navigation"]["x"], e["navigation"]["y"], e["navigation"]["h"], e["navigation"]["ecart"], q["l"] == q["h"]),
            (11, 288, 25, 6, True), f"changement d'ecran ({cible}) : barre mise a l'echelle, QR code reste carre")


def main():
    c = cat.charge(RACINE)
    for t in (test_boutons, lambda: test_validateur(c), test_generateurs, lambda: test_echelle(c)):
        try:
            t()
        except Exception as e:      # noqa: BLE001 - un test qui leve compte rouge, les suivants tournent
            verifie(f"{type(e).__name__} : {e}", None, getattr(t, "__name__", "test"))
    print(f"\n{len(ECHECS)} echec(s) : " + ("VERT" if not ECHECS else "ROUGE"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
