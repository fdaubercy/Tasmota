"""Banc de l'import d'un pages.jsonl ecrit a la main (atelier_ecrans_import.py, plan atelier-ecrans A13, spec 2026-11-12 § 5).

UTILISATION (Python de PlatformIO ; quelques secondes)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_ecrans_import.py
Verifie : sur les six pages.jsonl du depot, import -> description VALIDE -> generation HASPmota = memes objets JSON que la
source, dans le meme ordre, lus comme HASPmota les lit (page courante heritee, lignes vides ignorees) ; ecran des debits
(genere par l'atelier) importe sans objet brut ; pieges un par un (classe inconnue, attribut hors catalogue, val_rule,
parentid, action autre que p<n>, hors ecran, id en double, {"page":n} seul, reglage de page apres un objet, ligne non JSON
signalee) ; aucune liaison ; LVGL pur : objets bruts absents et signales. Code de sortie 0 = vert.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atelier_ecrans_catalogue as cat      # noqa: E402
import atelier_ecrans_description as aed    # noqa: E402
import atelier_ecrans_haspmota as ah        # noqa: E402
import atelier_ecrans_import as aei         # noqa: E402
import atelier_ecrans_lvgl as al            # noqa: E402
import atelier_ecrans_remarques as aer      # noqa: E402

RACINE = Path(__file__).resolve().parents[3]
ECRAN = "ST7262_1024x600"
SOURCES = ["data/bureau/tasmota32s3-ecran-debits-pac/pages.jsonl", "data/bureau/tasmota32s3-serveur-debits-pac/pages.jsonl",
           "lib/libesp32_lvgl/LVGL_assets/fonts/pixel_perfect/pages.jsonl", "tasmota/berry/haspmota_src/haspmota_demo/pages.jsonl",
           "tasmota/berry/haspmota_src/haspmota_watch_480/pages.jsonl", "tasmota/berry/haspmota_src/pages.jsonl"]
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)


def bruts(desc):
    return [o for o in desc["objets"] if o["type"] == aed.BRUT]


def aller_retour(texte, catalogue, libelle):
    r = aei.importe(texte, ECRAN, catalogue)
    d = r["description"]
    verifie(aed.valide(d, catalogue), [], f"{libelle} : description importee valide")
    a, b = aei.lignes_effectives(texte), aei.lignes_effectives(ah.genere(d))
    ecart = next((f"ligne {i + 1} : {x} != {y}" for i, (x, y) in enumerate(zip(a, b)) if x != y), None) or \
        (None if len(a) == len(b) else f"{len(a)} lignes, {len(b)} generees")
    verifie(ecart, None, f"{libelle} : generation HASPmota = memes objets JSON, meme ordre ({len(a)} lignes)")
    return r


def test_depot(catalogue):
    for rel in SOURCES:
        r = aller_retour((RACINE / rel).read_text(encoding="utf-8"), catalogue, rel)
        d = r["description"]
        print(f"     {len(d['objets']) - len(bruts(d))} objets editables, {len(bruts(d))} bruts, {len(d['pages'])} pages")
        verifie([o for o in d["objets"] if "liaison" in o or "couleur_selon" in o], [], f"{rel} : aucune liaison importee")
    d = aei.importe((RACINE / SOURCES[0]).read_text(encoding="utf-8"), ECRAN, catalogue)["description"]
    verifie(len(bruts(d)), 0, "ecran des debits (genere par l'atelier) : tout est editable")
    r = aei.importe((RACINE / SOURCES[5]).read_text(encoding="utf-8"), ECRAN, catalogue)
    verifie(any("non JSON" in a for a in r["avertissements"]), True, "demo HASPmota : ligne « # {...} » signalee")


def test_pieges(catalogue):
    tete = '{"page":1,"comment":"Accueil"}\n{"page":1,"id":0,"bg_color":"#000000"}\n'
    ok = '{"page":1,"id":1,"obj":"label","x":10,"y":10,"w":100,"h":30,"text":"A"}\n'
    cas = [
        ('{"page":1,"id":2,"obj":"truc","x":0,"y":0,"w":10,"h":10}', "classe inconnue"),
        ('{"page":1,"id":2,"obj":"label","x":0,"y":0,"w":10,"h":10,"inconnu":1}', "attribut hors catalogue"),
        ('{"page":1,"id":2,"obj":"label","x":0,"y":0,"w":10,"h":10,"val_rule":"X#Y"}', "val_rule"),
        ('{"page":1,"id":2,"obj":"label","x":0,"y":0,"w":10,"h":10,"parentid":1}', "parentid"),
        ('{"page":1,"id":2,"obj":"btn","x":0,"y":0,"w":10,"h":10,"action":"next"}', "action next"),
        ('{"page":1,"id":2,"obj":"label","x":1000,"y":0,"w":100,"h":10}', "hors ecran"),
        ('{"page":1,"id":1,"obj":"label","x":0,"y":0,"w":10,"h":10}', "id en double"),
        ('{"page":1,"id":2,"obj":"label","x":0,"y":0,"w":10}', "sans h"),
        ('{"page":1,"id":0,"bg_color":"#112233"}', "reglage de page apres un objet"),
        ('{"page":2}', "page seule"),
        ('{"comment":"au milieu"}', "commentaire au milieu"),
    ]
    for ligne, libelle in cas:
        r = aller_retour(tete + ok + ligne + "\n", catalogue, f"piege {libelle}")
        verifie([o.get("ligne") for o in bruts(r["description"])], [json.loads(ligne)], f"piege {libelle} : ligne gardee en brut")
    p2 = '{"page":2,"id":1,"obj":"label","x":0,"y":0,"w":10,"h":10}\n'
    for ligne, libelle in (('{"page":2,"comment":"tard"}', "commentaire de page apres un objet"),
                           ('{"page":2,"id":0,"bg_color":"#112233"}', "reglage d'une page sans en-tete apres un objet")):
        r = aller_retour(tete + ok + p2 + ligne + "\n", catalogue, f"piege {libelle}")
        verifie([o.get("ligne") for o in bruts(r["description"])], [json.loads(ligne)], f"piege {libelle} : ligne gardee en brut")
    r = aller_retour(tete + ok + '{"page":3,"id":0}\n', catalogue, "piege reglage de page vide")
    verifie([o.get("ligne") for o in bruts(r["description"])], [{"page": 3, "id": 0}], "piege reglage de page vide : brut")
    r = aller_retour(tete + ok + "# {\"id\":0}\n", catalogue, "ligne non JSON")
    verifie(([o.get("texte") for o in bruts(r["description"])], any("non JSON" in a for a in r["avertissements"])),
            (['# {"id":0}'], True), "ligne non JSON : gardee telle quelle et signalee")
    d = aei.importe(tete + ok + '{"page":2,"comment":"Suite"}\n{"id":3,"obj":"btn","x":0,"y":0,"w":80,"h":40,"action":"p1"}\n',
                    ECRAN, catalogue)["description"]
    o = [x for x in d["objets"] if x["page"] == 2][0]
    verifie((o["type"], o.get("toucher"), [p["n"] for p in d["pages"]], d["pages"][0].get("attributs")),
            ("btn", {"page": 1}, [1, 2], {"bg_color": "#000000"}),
            "page heritee, action p1 -> toucher, reglage de page, pages dans l'ordre")
    mal = {"version": 1, "ecran": ECRAN, "pages": [{"n": 1}], "objets": [
        {"type": "brut", "page": 1, "id": None, "ligne": {"a": 1}, "texte": "x"}, {"type": "brut", "page": 1, "id": None},
        {"type": "brut", "page": 9, "id": None, "texte": "x"}, {"type": "brut", "page": 1, "id": None, "texte": "a\n{\"id\":1}"},
        {"type": "brut", "page": 1, "id": None, "texte": " "}]}
    verifie(len(aed.valide(mal, catalogue)), 5,
            "validateur : brut a ligne ET texte, sans rien, page inconnue, texte sur deux lignes, texte vide -> 5 erreurs")
    d = aei.importe(tete + ok + '{"page":1,"id":5,"obj":"truc","x":0,"y":0,"w":10,"h":10}\n', ECRAN, catalogue)["description"]
    for op, libelle in (({"op": "modifie", "page": 1, "id": 5, "attributs": {"text": "x"}}, "modifier"),
                        ({"op": "ajoute", "objet": {"page": 1, "id": 5, "type": "label", "x": 0, "y": 0, "l": 9, "h": 9,
                                                    "attributs": {}}}, "ajouter sur son id")):
        try:
            aer.applique(d, {"operations": [op]})
            refus = None
        except ValueError as e:
            refus = str(e)
        verifie(refus is not None, True, f"remarque : {libelle} un objet brut refuse ({refus})")
    lv = al.genere(aei.importe(tete + ok + '{"page":1,"id":2,"obj":"truc","x":0,"y":0,"w":10,"h":10}\n', ECRAN, catalogue)["description"])
    verifie(("p1b2" not in lv, "1 ligne brute" in lv), (True, True), "LVGL pur : objet brut absent et signale en tete")


def test_palier2(catalogue):
    tete = '{"page":1,"comment":"Accueil"}\n'
    lignes = ['{"page":1,"id":1,"obj":"img","x":0,"y":0,"w":64,"h":64,"src":"A:sd/images/PNG/pompe.png"}',
              '{"page":1,"id":2,"obj":"dropdown","x":0,"y":70,"w":120,"h":40,"options":"Auto\\nMarche","val":1}',
              '{"page":1,"id":3,"obj":"switch","x":0,"y":120,"w":60,"h":30,"val":true}',
              '{"page":1,"id":4,"obj":"roller","x":0,"y":160,"w":90,"h":90,"options":"1\\n2","val":0}',
              '{"page":1,"id":5,"obj":"qrcode","x":100,"y":0,"w":80,"h":80,"qr_size":80,"qr_text":"http://x"}']
    r = aller_retour(tete + "\n".join(lignes) + "\n", catalogue, "palier 2")
    d = r["description"]
    verifie((len(bruts(d)), [o["type"] for o in d["objets"]]), (0, ["img", "dropdown", "switch", "roller", "qrcode"]),
            "palier 2 : un objet de chaque type, tous editables")
    verifie("qr_size" in d["objets"][4]["attributs"], False, "palier 2 : qr_size retire (pose par le generateur)")
    for ligne, libelle in (('{"page":1,"id":6,"obj":"qrcode","x":0,"y":0,"w":80,"h":80,"qr_size":60,"qr_text":"x"}', "qr_size different de w"),
                           ('{"page":1,"id":6,"obj":"img","x":0,"y":0,"w":9,"h":9,"src":"A:/demo.tapp#fan.png"}', "image hors sd/images/PNG"),
                           ('{"page":1,"id":6,"obj":"switch","x":0,"y":0,"w":9,"h":9,"val":1}', "interrupteur a val entier"),
                           ('{"page":1,"id":6,"obj":"msgbox","x":0,"y":0,"w":9,"h":9}', "type de palier 3")):
        r = aller_retour(tete + ligne + "\n", catalogue, f"palier 2 {libelle}")
        verifie(len(bruts(r["description"])), 1, f"palier 2 {libelle} : ligne gardee en brut")


def main():
    catalogue = cat.charge(RACINE)
    test_depot(catalogue)
    test_pieges(catalogue)
    test_palier2(catalogue)
    print(f"\n{len(ECHECS)} echec(s) : " + ("VERT" if not ECHECS else "ROUGE"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
