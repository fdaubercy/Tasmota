r"""Banc de l'interface LVGL pur GENEREE de l'ecran des debits (data/bureau/tasmota32s3-ecran-debits-pac/ecranLvgl.be,
produite par outils_pc/atelier_ecrans_lvgl.py depuis outils_docs/atelier_ecrans/cartes/<env>/ecran.json).

    python outils_docs/scripts_python/berry/banc_ecran_lvgl.py

banc_ecran_lvgl.be sur des objets LVGL simules (bouchons_berry/ecran_lvgl/), puis :
- chaque objet cree (lignes OBJET) a le type, la position, la taille et la page de la description ;
- temoins : copies modifiees du fichier genere, chacune doit rendre le banc rouge.
Code de sortie 0 si tout est vert. Ne prouve ni le rendu sur la dalle, ni la RAM, ni le tactile reel (essai sur carte,
plan debits-deux-cartes A8).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
BERRY = RACINE / "lib/libesp32/berry/berry.exe"
BANC = "outils_docs/scripts_python/berry/banc_ecran_lvgl.be"
INTERFACE = RACINE / "data/bureau/tasmota32s3-ecran-debits-pac/ecranLvgl.be"
ECRAN_JSON = RACINE / "outils_docs/atelier_ecrans/cartes/tasmota32s3-bureau-ecran-debits-pac/ecran.json"
VERT = "BANC_ECRAN_LVGL: OK"

# (nom, texte du moteur genere, remplacement) : chaque mutant doit rendre le banc rouge
MUTANTS = [
    ("courbe gelee apres un compteur remis a zero", "    if (p != nil && p < ecranLvgl.points)    ecranLvgl.points = 0    end", "    if (false)    end"),
    ("police nil sans log", "        if (p == nil)    raise \"io_error\", \"chargement sans police\"    end", ""),
    ("cache ignore : tout reecrit chaque seconde", "    if (c.find(k) == v)    return    end\n", ""),
    ("position decalee", "    o.set_pos(d[3], d[4])\n", "    o.set_pos(d[3] + 1, d[4])\n"),
    ("taille oubliee", "    else    o.set_size(d[5], d[6])    end", "    end"),
    ("texte de bouton sans label enfant", "        t = lv.label(ecranLvgl.objets[nom])\n", "        t = ecranLvgl.objets[nom]\n"),
    ("couleur_selon (sauf, si) ignoree", "var c = (v != nil && l[4] != nil) ? l[4].find(v) : nil", "var c = nil"),
    ("page courante jamais suivie", "    ecranLvgl.page = n\n", ""),
    ("historique entier repousse a chaque seconde", "var n = (p == nil ? 0 : p) - ecranLvgl.points", "var n = (p == nil ? 0 : p)"),
    ("trou de la courbe trace a 0", "v == nil ? lv.CHART_POINT_NONE : v", "v == nil ? 0 : v"),
    ("police rechargee pour chaque objet", "    if (ecranLvgl.polices.contains(f))    return ecranLvgl.polices[f]    end\n", ""),
    ("toucher execute dans le rappel LVGL", "tasmota.defer(ecranLvgl.execute)", "ecranLvgl.execute()"),
    ("suffixe de partie ignore (bg_color10)", "    return parties[n / 10] | etats[n % 10]\n", "    return 0\n"),
    ("ecran non demarre ignore", "if (!display.started())", "if (false)"),
    ("classe LVGL = nom HASPmota (lv.btn absent du firmware)", "var o = lv.(ecranLvgl.CLASSES.find(d[2], d[2]))(", "var o = lv.(d[2])("),
    ("valeur de barre avant sa plage", '    for a: d[7]    ecranLvgl.ecris(nom, a[0], a[1])    end\n',
     '    for a: d[7]    ecranLvgl.ecris(nom, a[0], a[1])    end\n    if (d[2] == "bar")    o.set_range(0, 0)    end\n'),
]


def lance(dossier, interface="-", mini=False):
    args = [str(BERRY), BANC, str(dossier), str(interface)] + (["mini"] if mini else [])
    try:
        r = subprocess.run(args, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return "BLOQUE : berry.exe arrete apres 120 s"
    return r.stdout + r.stderr


def objets_lus(sortie):
    """{nom: (type, x, y, l, h, parent)} des lignes OBJET."""
    r = {}
    for l in sortie.splitlines():
        if l.startswith("OBJET "):
            _, nom, t, x, y, w, h, parent = l.split(" ")
            if t == "qrcode" and h == "nil":        # lv.qrcode est carre : le moteur ne pose que la largeur (le validateur refuse l != h)
                h = w
            r[nom] = (t, x, y, w, h, parent)
    return r


# Classe LVGL attendue d'un type HASPmota : copie de lv_haspmota.be (lvh_btn._lv_class = lv.button), pas du generateur
CLASSES_LVGL = {"btn": "button", "img": "image", "btnmatrix": "buttonmatrix", "cpicker": "colorwheel"}


def objets_decrits(desc):
    return {f"p{o['page']}b{o['id']}": (CLASSES_LVGL.get(o["type"], o["type"]), str(o["x"]), str(o["y"]), str(o["l"]), str(o["h"]), f"page{o['page']}")
            for o in desc["objets"]}


def ecarts_objets(sortie, desc):
    lus, decrits = objets_lus(sortie), objets_decrits(desc)
    return [f"{n} : decrit {decrits.get(n)}, cree {lus.get(n)}" for n in sorted(set(lus) | set(decrits)) if lus.get(n) != decrits.get(n)]


def vert(sortie, desc):
    return VERT in sortie and not ecarts_objets(sortie, desc)


def main():
    sys.path.insert(0, str(RACINE / "outils_docs/scripts_python/outils_pc"))
    import atelier_ecrans_navigation as nav     # boutons de la barre construite = objets decrits (banc de nav : leurs places)
    desc = nav.deroule(json.loads(ECRAN_JSON.read_text(encoding="utf-8")))
    ok = True
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        (tmp / "banc").mkdir()
        sortie = lance(tmp / "banc")
        print("\n".join(l for l in sortie.splitlines() if not l.startswith(("OBJET ", "TEXTE "))))
        ecarts = ecarts_objets(sortie, desc)
        print(f"--- objets crees contre ecran.json : {len(objets_lus(sortie))} lus, {len(desc['objets'])} decrits, "
              f"ecarts : {ecarts[:5] or 'aucun'}")
        ok = VERT in sortie and not ecarts
        faux = json.loads(json.dumps(desc))
        faux["objets"][0]["x"] += 1
        rouge = bool(ecarts_objets(sortie, faux))
        print(f"  {'OK   ' if rouge else 'ECHEC'} temoin : objet deplace dans la description")
        ok = ok and rouge
        print("--- Temoins (chaque mutant du fichier genere doit etre rouge)")
        texte = INTERFACE.read_text(encoding="utf-8").replace("\r\n", "\n")
        for i, (nom, avant, apres) in enumerate(MUTANTS):
            if texte.count(avant) != 1:
                print(f"  ECHEC temoin « {nom} » : texte absent ou ambigu")
                ok = False
                continue
            d = tmp / f"mutant{i}"
            d.mkdir()
            copie = d / "ecranLvgl.be"
            copie.write_text(texte.replace(avant, apres), encoding="utf-8")
            (d / "banc").mkdir()
            rouge = not vert(lance(d / "banc", copie), desc)
            print(f"  {'OK   ' if rouge else 'ECHEC'} {nom}")
            ok = ok and rouge
    print("BANC_ECRAN_LVGL (enveloppe):", "VERT" if ok else "ROUGE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
