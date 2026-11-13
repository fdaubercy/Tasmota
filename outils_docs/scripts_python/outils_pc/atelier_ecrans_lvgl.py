"""Generateur LVGL pur de l'atelier des ecrans : description neutre (`ecran.json`) -> module Berry `ecranLvgl` (texte du
`ecranLvgl.be` de la carte), seconde interface interchangeable avec `ecranHaspmota.be` + `pages.jsonl`.

Forme du module genere : des TABLES tirees de la description (PAGES, OBJETS, LIAISONS, ACTIFS, COULEURS, COURBE, une
fonction nommee par toucher) et un MOTEUR fixe (atelier_ecrans_lvgl_moteur.py) qui les applique comme lv_haspmota.be le fait d'un
pages.jsonl : un ecran lv.obj(0) par page n >= 1, page 0 sur lv.layer_top() (fond sur lv.layer_bottom()), page de depart =
plus petite page n >= 1 ; attributs par setmember de HASPmota (text sur un label enfant centre hors label, text_font par
parse_font, align, min / max / val, y_min / y_max, divisions, suffixe a 2 chiffres = partie | etat, sinon set_<k> puis
set_style_<k>) ; couleurs #RRGGBB converties en entiers ici, lv.color a l'ecriture. affiche(modele) n'ecrit que ce qui a
change (cache "p1b13" -> {"text": valeur brute}). toucher page -> ecran charge ; commande -> tasmota.cmd ; fonction ->
<module>.<fonction>(args) ; tous differes par tasmota.defer (rien de long dans le rappel LVGL).

Courbe : liaison `attribut: "series"` d'un chart, avec `points`, `max` et `couleurs` (forme dans atelier_ecrans_description) ;
`format` et `echelle` d'une liaison texte sont appliques par affiche() : texte = format % (valeur / echelle).
`genere` ne valide pas la description (atelier_ecrans_description.valide avant) ; refuse (ValueError) seulement ce qui
ne peut s'ecrire en Berry : couleur hors #RRGGBB, fonction de toucher hors `module.fonction`, type de SANS_CLASSE."""

import re

from atelier_ecrans_lvgl_moteur import MOTEUR

COULEUR = re.compile(r"#[0-9A-Fa-f]{6}")
IDENT = re.compile(r"[A-Za-z_]\w*")
# Types HASPmota sans classe LVGL propre (_lv_class nil : sous-objets d'un parent) ou construits autrement qu'un objet LVGL
# nu (fixed, flex : lv.obj + styles de post_init ; scale_line : lv.line enfant d'un scale) : refuses. Les noms qui different
# de la classe LVGL (btn -> button, img -> image...) sont traduits par ecranLvgl.CLASSES du moteur.
SANS_CLASSE = ("dropdown_list", "scale_section", "span", "tab", "scr", "fixed", "flex", "scale_line")


def chaine(s):
    """Litteral Berry de `s` (UTF-8 garde tel quel ; \\ " et caracteres de controle echappes)."""
    sortie = []
    for c in s:
        if c in '\\"':
            sortie.append("\\" + c)
        elif c in "\n\r\t":
            sortie.append({"\n": "\\n", "\r": "\\r", "\t": "\\t"}[c])
        elif ord(c) < 0x20 or ord(c) == 0x7F:
            sortie.append(f"\\x{ord(c):02x}")
        else:
            sortie.append(c)
    return '"' + "".join(sortie) + '"'


def berry(v):
    """Litteral Berry d'une valeur JSON."""
    if v is None:
        return "nil"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return chaine(v)
    if isinstance(v, list):
        return "[" + ", ".join(berry(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{chaine(str(k))}: {berry(x)}" for k, x in v.items()) + "}"
    raise ValueError(f"valeur {v!r} sans equivalent Berry")


class Hexa(int):
    """Couleur : entier ecrit 0xRRGGBB dans le module genere."""


def couleur(v, qui):
    if not (isinstance(v, str) and COULEUR.fullmatch(v)):
        raise ValueError(f"{qui} : couleur « {v} » mal formée (attendu #RRGGBB)")
    return Hexa(int(v[1:], 16))


def lit(v):
    return f"0x{v:06X}" if isinstance(v, Hexa) else berry(v)


def table(v):
    """Litteral Berry, couleurs (Hexa) en 0xRRGGBB, a toute profondeur."""
    if isinstance(v, list):
        return "[" + ", ".join(table(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{chaine(str(k))}: {table(x)}" for k, x in v.items()) + "}"
    return lit(v)


def _est_couleur(k):
    k = k[:-1] if k.endswith("%") else k
    k = k[:-2] if len(k) > 2 and k[-2:].isdigit() else k
    return k.endswith("color")


def attributs(attrs, qui):
    """[[k, v]] dans l'ordre de la description, couleurs converties, `val` en dernier (post_config de HASPmota)."""
    r = [[k, couleur(v, f"{qui}.{k}") if _est_couleur(k) else v] for k, v in attrs.items()]
    return [a for a in r if a[0] != "val"] + [a for a in r if a[0] == "val"]


def chemin(cle, indice):
    """"voies[].debit", 0 -> ["voies", 0, "debit"] ; "reglages.fenetre" -> ["reglages", "fenetre"]."""
    r = []
    for s in cle.split("."):
        if s.endswith("[]"):
            r += [s[:-2], indice]
        else:
            r.append(s)
    return r


def couleurs_map(m, qui):
    return {k: couleur(v, f"{qui}[{k}]") for k, v in m.items()}


def _toucher(nom, t):
    """(nom de la fonction Berry, ligne de sa definition) d'un toucher."""
    f = f"ecranLvgl_{nom}"
    if "page" in t:
        corps = f"import ecranLvgl    ecranLvgl.montre({int(t['page'])})"
    elif "commande" in t:
        corps = f"tasmota.cmd({chaine(t['commande'])})"
    else:
        morceaux = str(t.get("fonction", "")).split(".")
        if len(morceaux) != 2 or not all(IDENT.fullmatch(x) for x in morceaux):
            raise ValueError(f"{nom} : toucher.fonction « {t.get('fonction')} » : forme module.fonction attendue")
        args = ", ".join(berry(a) for a in t.get("args", []))
        corps = f"import {morceaux[0]}    {morceaux[0]}.{morceaux[1]}({args})"
    return f, f"def {f}()    {corps}    end"


def genere(desc):
    """Texte du module Berry ecranLvgl (UTF-8, fins de ligne \\n)."""
    pages = [[p["n"], attributs(p.get("attributs", {}), f"page {p['n']}")] for p in desc["pages"]]
    contenu = [p["n"] for p in desc["pages"] if p["n"] >= 1]
    objets, groupes, actifs, touchers, courbe = [], [], [], [], None
    bruts = sum(1 for o in desc["objets"] if o["type"] == "brut")
    for o in desc["objets"]:
        if o["type"] == "brut":         # ligne d'un pages.jsonl importe : HASPmota seulement
            continue
        nom = f"p{o['page']}b{o['id']}"
        if o["type"] in SANS_CLASSE:
            raise ValueError(f"{nom} : type {o['type']} sans objet LVGL propre, non pris en charge en LVGL pur")
        f, liaisons = None, []
        if o.get("toucher"):
            f, ligne = _toucher(nom, o["toucher"])
            touchers.append(ligne)
        objets.append(f"[{o['page']}, {o['id']}, {chaine(o['type'])}, {o['x']}, {o['y']}, {o['l']}, {o['h']}, "
                      f"{table(attributs(o.get('attributs', {}), nom))}, {f or 'nil'}]")
        li = o.get("liaison")
        if li and li.get("attribut") == "series":
            courbe = [nom, chemin(li["cle"], li.get("indice")), chemin(li["points"], None),
                      [couleur(c, f"{nom}.couleurs") for c in li["couleurs"]]]
            liaisons.append([nom, chemin(li["max"], None), "y_max", None, None, None, None, None])
        elif li:
            liaisons.append([nom, chemin(li["cle"], li.get("indice")), li["attribut"], li.get("table"), None, None,
                             li.get("format"), li.get("echelle")])
        for r in o.get("couleur_selon", []):
            exceptions = couleurs_map(r.get("si", r.get("sauf", {})), f"{nom}.couleur_selon") or None
            sinon = couleur(r["sinon"], f"{nom}.sinon") if "sinon" in r else None
            liaisons.append([nom, chemin(r["cle"], r.get("indice")), r["attribut"], r.get("table"), exceptions, sinon, None, None])
        if o.get("actif") and "page" in (o.get("toucher") or {}):
            base = dict(attributs(o.get("attributs", {}), nom))
            actifs.append([nom, o["toucher"]["page"],
                           {k: [couleur(v, f"{nom}.actif"), base.get(k)] for k, v in o["actif"].items()}])
        if liaisons:
            groupes.append(", ".join(table(l) for l in liaisons))
    couleurs = {t: couleurs_map(m, f"couleurs[{t}]") for t, m in desc.get("couleurs", {}).items()}
    lignes = [ENTETE.format(ecran=desc.get("ecran"), pages=len(pages), objets=len(objets))] + (
        [f"# ATTENTION : {bruts} ligne brute(s) du pages.jsonl importe, absente(s) de cette interface (HASPmota seulement)."]
        if bruts else []) + [
              'var ecranLvgl = module("ecranLvgl")', "",
              "# ---- Touchers : une fonction nommee par objet tactile, executee par tasmota.defer ----"] + touchers + [
              "", "# ---- Tables tirees de la description ----",
              f"ecranLvgl.DEPART = {min(contenu) if contenu else 'nil'}",
              f"ecranLvgl.COULEURS = {table(couleurs)}",
              "ecranLvgl.PAGES = [" + ",\n    ".join(table(p) for p in pages) + "]",
              "# [page, id, type, x, y, l, h, [[attribut, valeur]], fonction du toucher]",
              "ecranLvgl.OBJETS = [\n    " + ",\n    ".join(objets) + "]",
              "# [objet, chemin dans le modele, attribut, table de couleurs, couleurs si / sauf, sinon, format, echelle] ;"
              " une ligne par objet",
              "ecranLvgl.LIAISONS = [\n    " + ",\n    ".join(groupes) + "]",
              "# [bouton, page menee, {attribut: [couleur page courante, couleur sinon]}]",
              f"ecranLvgl.ACTIFS = {table(actifs)}",
              "# [chart, chemin des series, chemin du compteur de points, couleurs des series]",
              f"ecranLvgl.COURBE = {table(courbe) if courbe else 'nil'}"]
    return "\n".join(lignes) + "\n" + MOTEUR


ENTETE = """# Interface LVGL pur de l'ecran (module ecranLvgl), GENEREE par outils_docs/scripts_python/outils_pc/atelier_ecrans_lvgl.py
# depuis la description ecran.json de l'atelier des ecrans (outils_docs/atelier_ecrans/cartes/<env>/) : NE PAS EDITER, modifier
# la description puis regenerer. Ecran {ecran}, {pages} pages, {objets} objets. Interchangeable avec ecranHaspmota.be +
# pages.jsonl (custom_interface_ecran du cenv). API (en tete du module metier) : demarre() -> true si l'ecran est
# pret ; affiche(modele) chaque seconde, n'ecrit que ce qui a change (cache par objet et attribut). Objets nommes p<page>b<id>
# comme HASPmota ; page 0 sur lv.layer_top() (toutes les pages), une page n >= 1 = un ecran lv.obj(0) charge par lv.screen_load.
# Logs : charte du CLAUDE.md (logFonctions.log, seuil `general`)."""
