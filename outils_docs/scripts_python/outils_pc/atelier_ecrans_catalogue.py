"""Catalogue commun de l'atelier des ecrans : objets HASPmota, attributs, polices, ecrans (source unique).

Genere `outils_docs/schemas/catalogue_ecran.json` d'apres les SOURCES du depot (liste `SOURCES`) :
  objets   : classes `lvh_*` de lv_haspmota.be (setters et _attr_map, heritage resolu) + setters natifs LVGL a une
             valeur (lv_funcs.h) + attributs de style (`lv_obj_set_style_*`) ; palier 1 = les 7 types de l'atelier.
  polices  : polices EMBARQUEES activees dans tasmota_lv_conf.h / xdrv_52_3_berry_lvgl.ino, et `.ttf` des dossiers de cartes.
  ecrans   : ligne `:H` des `display.ini`, par priorite : cartes du depot (sauf display.ini exclu du FS de l'env),
             bibliotheque personnelle `PERSO`, descriptions amont `AMONT` (lecture seule) ; clef `<pilote>_<l>x<h>` au
             premier trouve, `<pilote>_<l>x<h>@<fichier>` pour les suivants (les clefs des cartes ne changent pas).

Usage : python atelier_ecrans_catalogue.py --generer | --verifier   (--verifier : code 1 si le fichier est en retard)."""

import json
import re
import sys
from pathlib import Path

import fichiers_berry_ini as fbi

CATALOGUE = "outils_docs/schemas/catalogue_ecran.json"
HASPMOTA = "lib/libesp32_lvgl/lv_haspmota/src/embedded/lv_haspmota.be"
LV_FUNCS = "lib/libesp32_lvgl/lv_binding_berry/mapping/lv_funcs.h"
LV_CONF = "tasmota/lvgl_berry/tasmota_lv_conf.h"
XDRV_LVGL = "tasmota/tasmota_xdrv_driver/xdrv_52_3_berry_lvgl.ino"
# Fichiers lus (hors data/*/*/{display.ini,pages.jsonl,*.ttf,_persist.json}) : le banc en copie ce qu'il faut.
SOURCES = [HASPMOTA, LV_FUNCS, LV_CONF, XDRV_LVGL]
PERSO = "outils_docs/atelier_ecrans/display"     # display.ini personnels (hors flash), plan atelier-ecrans A12/A15
AMONT = "tasmota/displaydesc"                    # descriptions fournies par Tasmota : jamais modifiees (synchro du fork)
TACTILES = (":UTI", ":TI", ":TS", ":TR")         # pilote universel, anciens GT911/FT5206/CST816S, XPT2046, resistif
PALIER1 = ("label", "btn", "bar", "obj", "chart", "arc", "slider")
# Grille de tailles proposee pour un .ttf : FreeType rend toute taille (cout RAM croissant), on ajoute celles deja utilisees.
TAILLES_TTF = (12, 14, 16, 20, 24, 28, 32, 36, 40, 48)
NON_ATTRIBUTS = {"delete", "tostring"}                 # set_delete : detruit l'objet ; pas un reglage d'apparence
BOOLEENS = {"hidden", "enabled", "click", "toggle", "adjustable", "line_rounded", "arc_rounded", "clip_corner",
            "border_post", "bg_image_tiled", "show_selected", "auto_size"}
TEXTES = {"text", "title", "options", "src", "raw", "points", "tag", "meta", "qr_text", "val_rule", "text_rule",
          "val_rule_formula", "text_rule_formula", "text_rule_format", "label_mode", "mode"}


def _lire(racine, rel):
    return (Path(racine) / rel).read_text(encoding="utf-8", errors="replace")


def _type_par_nom(nom):
    """Type d'un attribut Berry/style d'apres son nom."""
    if nom.endswith("color"):
        return "couleur"
    if nom.endswith("font"):
        return "police"
    if nom == "action":
        return "action"
    if nom in BOOLEENS:
        return "booleen"
    if nom in TEXTES or nom.endswith("_src"):
        return "texte"
    return "entier"


def _attr(nom, type_=None):
    a = {"type": type_ or _type_par_nom(nom)}
    if nom.endswith("opa") and a["type"] == "entier":
        a["min"], a["max"] = 0, 255
    return a


def _classes(racine):
    """{type: {"parent", "lv", "setters": set, "map": [..]}} pour chaque `class lvh_<type>` de lv_haspmota.be."""
    texte = _lire(racine, HASPMOTA)
    morceaux = re.split(r"(?m)^class (?=lvh_)", texte)[1:]
    res = {}
    for m in morceaux:
        t = re.match(r"lvh_(\w+)\s*(?::\s*lvh_(\w+))?", m)
        if not t:
            continue
        nom, parent = t.group(1), t.group(2)
        lv = re.search(r"static var _lv_class\s*=\s*lv\.(\w+)", m)
        setters = set(re.findall(r"(?m)^\s{2}def set_(\w+)\(", m))
        amap = re.search(r"static var _attr_map\s*=\s*\{(.*?)\n\s*\}", m, re.S)
        cles = re.findall(r'"(\w+)"\s*:', amap.group(1)) if amap else []
        res[nom] = {"parent": parent, "lv": lv.group(1) if lv else None, "setters": setters, "map": cles}
    return res


def _natifs(racine):
    """{classe lvgl: {attribut: type}} : setters natifs `lv_<classe>_set_<attr>(obj, valeur)` a UNE valeur."""
    res = {}
    for m in re.finditer(r"(?m)^\w[\w ]*?\blv_(\w+?)_set_(\w+)\(([^)]*)\)", _lire(racine, LV_FUNCS)):
        classe, attr, params = m.groups()
        args = [p.strip() for p in params.split(",")]
        if classe in ("obj", "style") or attr.startswith("style_") or len(args) != 2:
            continue
        p = args[1]
        t = ("texte" if "char" in p else "couleur" if "color" in p else "booleen" if p.startswith("bool")
             else "police" if "font" in p else None)
        res.setdefault(classe, {})[attr] = t or _type_par_nom(attr)
    return res


def _styles(racine):
    """Attributs de style communs a tous les objets : `lv_obj_set_style_<nom>` (hors tableaux/descripteurs)."""
    noms = re.findall(r"lv_obj_set_style_(\w+)\(", _lire(racine, LV_FUNCS))
    return [n for n in dict.fromkeys(noms) if not n.endswith(("_dsc_array", "_dsc"))]


def objets(racine):
    classes, natifs, styles = _classes(racine), _natifs(racine), _styles(racine)
    res = {}
    for nom in sorted(classes, key=lambda n: (n not in PALIER1, n)):
        if nom in ("root", "page"):
            continue
        chaine, c = [], nom
        while c:
            chaine.append(c)
            c = classes[c]["parent"] if c in classes else None
        attrs = {}
        for n in styles:
            attrs[n] = _attr(n)
        for c in reversed(chaine):
            info = classes.get(c, {"setters": set(), "map": [], "lv": None})
            for n in info["map"]:
                attrs.setdefault(n, _attr(n))
            for n in sorted(info["setters"] - NON_ATTRIBUTS):
                attrs[n] = _attr(n)
            for n, t in natifs.get(info["lv"] or "", {}).items():
                attrs.setdefault(n, _attr(n, t))
        for sans in ("id", "obj", "page", "comment", "parentid", "berry_run"):
            attrs.pop(sans, None)
        res[nom] = {"palier": 1 if nom in PALIER1 else 2, "attributs": dict(sorted(attrs.items()))}
    return res


def _cartes(racine):
    """[(env, dossier)] : une carte = data/<lieu>/<puce>-<reste>/ avec un _persist.json ; env = <puce>-<lieu>-<reste>."""
    res = []
    for p in sorted(Path(racine).glob("data/*/*/_persist.json")):
        d = p.parent
        if d.name.endswith("-sauvegarde") or "-" not in d.name:
            continue
        puce, reste = d.name.split("-", 1)
        res.append((f"{puce}-{d.parent.name}-{reste}", d))
    return res


def lit_ecran(chemin):
    """Ecran decrit par la ligne `:H` d'un display.ini : dict ou None (fichier absent, sans `:H`, illisible)."""
    try:
        for ligne in Path(chemin).read_text(encoding="utf-8", errors="replace").splitlines():
            if ligne.startswith(":H,"):
                c = ligne.split(",")
                return {"pilote": c[1], "largeur": int(c[2]), "hauteur": int(c[3]), "bpp": int(c[4]), "bus": c[5]}
    except (OSError, ValueError, IndexError):
        pass
    return None


def _tactile(chemin):
    try:
        return any(l.startswith(TACTILES) for l in Path(chemin).read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return False


def _exclu(ini, env, rel):
    """Vrai si `rel` est dans le custom_files_exclude resolu de l'env (cenv absent ou env inconnu : non exclu)."""
    if ini is None or "env:" + env not in ini.sections:
        return False
    try:
        return any(e.chemin == rel for e in fbi.resout(ini, env, "custom_files_exclude"))
    except ValueError:
        return False


def _fichiers(racine):
    """[(source, display.ini, [envs])] par priorite : cartes, bibliotheque personnelle, amont."""
    racine = Path(racine)
    try:
        ini = fbi.lit_sections(racine)
    except (OSError, ValueError):
        ini = None
    res = []
    for env, d in _cartes(racine):
        f = d / "display.ini"
        # shortcut: un env sans LVGL mais dont le display.ini part sur le FS reste rattache ; a revoir si le cas apparait
        if f.is_file() and not _exclu(ini, env, f.relative_to(racine).as_posix()):
            res.append(("carte", f, [env]))
    for source, dossier in (("perso", PERSO), ("amont", AMONT)):
        res += [(source, f, []) for f in sorted((racine / dossier).glob("*.ini"))]
    return res


def ecrans(racine):
    res = {}
    for source, f, envs in _fichiers(racine):
        e = lit_ecran(f)
        if not e:
            continue
        cle = f"{e['pilote']}_{e['largeur']}x{e['hauteur']}"
        if source == "carte" and res.get(cle, {}).get("source") == "carte":
            res[cle]["envs"] += envs                     # meme ecran sur plusieurs cartes : une entree
            continue
        if cle in res:
            cle += "@" + f.stem
        if cle in res:                                   # meme nom de fichier dans la bibliotheque et a l'amont
            cle += "-" + source
        res[cle] = {**e, "tactile": _tactile(f), "couleur": e["bpp"] > 1, "source": source,
                    "display_ini": f.relative_to(racine).as_posix(), "envs": envs}
    return res


def ecrans_des_envs(racine):
    """{env: cle d'ecran | None} pour chaque carte du depot ; None = aucun ecran (absent, illisible, exclu du FS)."""
    res = {env: None for env, _ in _cartes(racine)}
    for cle, e in ecrans(racine).items():
        if e["source"] == "carte":
            res.update({env: cle for env in e["envs"]})
    return res


def polices(racine):
    conf, xdrv = _lire(racine, LV_CONF), _lire(racine, XDRV_LVGL)
    roboto = sorted(int(n) for n in re.findall(r"(?m)^#define ROBOTOCONDENSED_REGULAR_(\d+)_LATIN1\s+1\b", conf))
    mont = sorted({int(n) for n in re.findall(r"(?m)^#define LV_FONT_MONTSERRAT_(?:TASMOTA_)?(\d+)\s+1\b", conf)})
    seg7 = sorted({int(n) for n in re.findall(r"&seg7_(\d+)\b", xdrv)})
    res = [{"nom": "robotocondensed", "tailles": roboto, "source": "firmware", "ecriture": "<taille> (entier)"},
           {"nom": "montserrat", "tailles": mont, "source": "firmware", "ecriture": "montserrat-<taille>"},
           {"nom": "seg7", "tailles": seg7, "source": "firmware", "ecriture": "seg7-<taille>"}]
    for ttf in sorted(Path(racine).glob("data/*/*/*.ttf")):
        utilises = set()
        for pj in Path(racine).glob("data/*/*/pages.jsonl"):
            utilises |= {int(n) for n in re.findall(re.escape(ttf.name) + r"-(\d+)", pj.read_text(encoding="utf-8"))}
        res.append({"nom": ttf.stem, "tailles": sorted(set(TAILLES_TTF) | utilises), "source": "sd",
                    "fichier": ttf.name, "taille_libre": True, "ecriture": f"A:sd/polices/{ttf.name}-<taille>"})
    return res


def genere(racine):
    return {"objets": objets(racine), "polices": polices(racine), "ecrans": ecrans(racine)}


def charge(racine):
    return json.loads((Path(racine) / CATALOGUE).read_text(encoding="utf-8"))


def attribut_connu(catalogue, type_, cle):
    """Vrai si `cle` est un attribut de `type_` ; `%` final (pourcentage) et deux chiffres de partie/etat (radius10) admis."""
    attrs = catalogue["objets"].get(type_, {}).get("attributs", {})
    if cle.endswith("%"):
        cle = cle[:-1]
    return cle in attrs or (len(cle) > 2 and cle[-2:].isdigit() and cle[:-2] in attrs)


def verifie(racine):
    """Ecarts entre le fichier et les sources ; liste vide = a jour."""
    try:
        fichier = charge(racine)
    except (OSError, ValueError) as e:
        return [f"{CATALOGUE} illisible : {e}"]
    neuf, ecarts = genere(racine), []
    for section in neuf:
        a, b = fichier.get(section), neuf[section]
        if a == b:
            continue
        if isinstance(b, dict):
            cles = sorted(k for k in set(a or {}) | set(b) if (a or {}).get(k) != b.get(k))
        else:
            cles = sorted(p["nom"] for p in b if p not in (a or [])) + sorted(p["nom"] for p in (a or []) if p not in b)
        ecarts.append(f"{section} : differe des sources ({', '.join(dict.fromkeys(cles))})")
    return ecarts


def _ecrit(cat):
    """JSON lisible et compact : une ligne par objet, par police et par ecran (les attributs de style se repetent)."""
    def un(v):
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    blocs = []
    for section, v in cat.items():
        lignes = [f" {un(k)}:{un(x)}" for k, x in v.items()] if isinstance(v, dict) else [f" {un(x)}" for x in v]
        o, f = ("{", "}") if isinstance(v, dict) else ("[", "]")
        blocs.append(un(section) + ":" + o + "\n" + ",\n".join(lignes) + "\n" + f)
    return "{\n" + ",\n".join(blocs) + "\n}\n"


def main(argv):
    racine = Path(__file__).resolve().parents[3]
    if "--generer" in argv:
        (racine / CATALOGUE).write_text(_ecrit(genere(racine)), encoding="utf-8")
        print(f"{CATALOGUE} ecrit")
        return 0
    if "--verifier" in argv:
        ecarts = verifie(racine)
        print("\n".join(ecarts) if ecarts else "catalogue a jour")
        return 1 if ecarts else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
