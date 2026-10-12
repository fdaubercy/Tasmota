#!/usr/bin/env python3
"""Bilan d'alimentation d'une carte KiCad et recommandation de l'alimentation.

Lit le .kicad_sch (symboles, valeurs, empreintes, champs, nets par etiquettes/fils) et,
si present, un fichier bilan.json (charges hors carte, rendements, marge, taux de charge).
Les consommations par defaut (pire cas, sources citees) sont dans
references/consommations.json. Rien n'est ignore en silence : les composants non
reconnus sont listes « a renseigner ».

Declarer une consommation dans le schema (priorite maximale), par exemple en Python :
    s.composant(ref, lib_id, valeur, empreinte, pos, nets,
                champs={"Conso_mA": "30", "Rail": "5V"})

Le calcul : consommations par rail (3V3, 5V, 12V...) ramenees a l'entree via les
rendements (3V3 = regulateur lineaire du DevKit, meme courant cote 5 V ; 5V = abaisseur
a decoupage, rendement 0,9 par defaut), controle des fusibles reinitialisables (maintien
declasse a 50 C), marge, puissance minimale et calibre standard recommande.

Exemple :
    python bilan_alimentation.py carte.kicad_sch --bilan exemples/bilan_cuve.json --md bilan.md
"""
import argparse
import json
import math
import re
import sys
from collections import deque
from pathlib import Path

REF_JSON = Path(__file__).resolve().parent.parent / "references" / "consommations.json"


# ------------------------------------------------------------------ S-expression
def lire_sexp(texte):
    pile, cur = [], []
    for t in re.finditer(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+', texte):
        t = t.group(0)
        if t == "(":
            pile.append(cur)
            cur = []
        elif t == ")":
            f, cur = cur, pile.pop()
            cur.append(f)
        else:
            cur.append(t[1:-1].replace('\\"', '"') if t[0] == '"' else t)
    return cur[0]


def enf(n, nom):
    return [c for c in n if isinstance(c, list) and c and c[0] == nom]


def pt(x, y):
    return (round(float(x), 2), round(float(y), 2))


def rail_de(net):
    """'+12V_CAPT' -> '12V' ; '+3V3' -> '3V3' ; autre -> None."""
    m = re.match(r"^\+(\d+)V(\d*)(?:_|$)", net or "")
    return f"{m.group(1)}V{m.group(2)}" if m else None


def ohms(txt):
    m = re.match(r"^\s*(\d+(?:[.,]\d+)?)\s*([kKmMR]?)(\d*)", txt or "")
    if not m:
        return None
    v = float((m.group(1) + ("." + m.group(3) if m.group(3) else "")).replace(",", "."))
    return v * {"k": 1e3, "K": 1e3, "m": 1e6, "M": 1e6}.get(m.group(2), 1)


def fr(x, n=2):
    return f"{x:.{n}f}".replace(".", ",")


# ------------------------------------------------------------------ schema -> composants + nets
def lire_schema(chemin):
    arbre = lire_sexp(Path(chemin).read_text(encoding="utf-8"))
    lib = {}
    for s in enf(enf(arbre, "lib_symbols")[0], "symbol"):
        pins = {}
        for sous in enf(s, "symbol"):
            m = re.match(r"^.*_(\d+)_(\d+)$", sous[1])
            if not m or int(m.group(2)) > 1:
                continue
            for p in enf(sous, "pin"):
                at = enf(p, "at")[0]
                num = str(enf(p, "number")[0][1])
                pins.setdefault(int(m.group(1)), []).append((num, float(at[1]), float(at[2])))
        lib[s[1]] = pins
    parent = {}

    def trouve(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def lie(a, b):
        parent[trouve(a)] = trouve(b)

    etiq, comps, ptpin = [], {}, []
    for w in enf(arbre, "wire"):
        xy = [pt(*c[1:3]) for c in enf(enf(w, "pts")[0], "xy")]
        lie(xy[0], xy[1])
    for k in ("label", "global_label", "hierarchical_label"):
        for e in enf(arbre, k):
            a = enf(e, "at")[0]
            etiq.append((pt(a[1], a[2]), e[1]))
    for s in enf(arbre, "symbol"):
        if not enf(s, "lib_id"):
            continue
        lid = enf(s, "lib_id")[0][1]
        a = enf(s, "at")[0]
        x0, y0, rot = float(a[1]), float(a[2]), int(float(a[3])) if len(a) > 3 else 0
        mir = enf(s, "mirror")[0][1] if enf(s, "mirror") else ""
        unite = int(enf(s, "unit")[0][1]) if enf(s, "unit") else 1
        props = {p[1]: p[2] for p in enf(s, "property")}
        ref, pins = props.get("Reference", "?"), []
        for u in (0, unite):
            for num, px, py in lib.get(lid, {}).get(u, []):
                if mir == "x":
                    py = -py
                elif mir == "y":
                    px = -px
                c, sn = round(math.cos(math.radians(rot))), round(math.sin(math.radians(rot)))
                pins.append((num, pt(x0 + px * c - py * sn, y0 - (px * sn + py * c))))
        if lid.startswith("power:"):
            for _, p in pins:
                etiq.append((p, props.get("Value", "?")))
            continue
        if ref.startswith("#"):
            continue
        c = comps.setdefault(ref, {"ref": ref, "lib_id": lid, "valeur": props.get("Value", ""),
                                   "empreinte": props.get("Footprint", ""), "champs": {}, "pins": {}})
        for k, v in props.items():
            if k not in ("Reference", "Value", "Footprint", "Datasheet", "Description") and v not in ("", "~"):
                c["champs"][k] = v
        for num, p in pins:
            c["pins"][num] = p
            trouve(p)
    noms = {}
    for p, n in etiq:
        noms.setdefault(trouve(p), n)
    for c in comps.values():
        c["nets"] = {num: noms.get(trouve(p), f"(sans nom {abs(hash(trouve(p))) % 9999})")
                     for num, p in c["pins"].items()}
    return comps


# ------------------------------------------------------------------ outils reseau
def chemin_fusibles(comps, racine):
    """Pour chaque net : liste des fusibles traverses depuis l'entree (parcours en largeur)."""
    adj = {}
    for c in comps.values():
        serie = re.search(r"Polyfuse|^Fuse:", c["lib_id"]) or re.search(r"^Device:(D|D_Schottky)$", c["lib_id"])
        if serie and len(c["nets"]) == 2:
            a, b = list(c["nets"].values())
            if a != b and "GND" not in (a, b):
                adj.setdefault(a, []).append((b, c))
                adj.setdefault(b, []).append((a, c))
    res, file = {racine: []}, deque([racine])
    while file:
        n = file.popleft()
        for m, c in adj.get(n, []):
            if m not in res:
                res[m] = res[n] + ([c["ref"]] if re.search(r"Polyfuse|^Fuse:", c["lib_id"]) else [])
                file.append(m)
    return res


def trouve_racine(comps, v_in):
    for c in comps.values():
        for n in c["nets"].values():
            if n.endswith("_IN") and rail_de(n):
                return n
    for c in comps.values():
        for n in c["nets"].values():
            if rail_de(n) == f"{v_in}V":
                return n
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 add_help=False, usage="%(prog)s schema.kicad_sch [options]")
    ap.add_argument("-h", "--help", action="help", help="affiche cette aide")
    ap.add_argument("schema", help="fichier .kicad_sch de la carte")
    ap.add_argument("--bilan", help="bilan.json (defaut : bilan.json a cote du schema, s'il existe)")
    ap.add_argument("--md", help="ecrit aussi le rapport dans ce fichier Markdown")
    ap.add_argument("--strict", action="store_true", help="code de sortie 1 s'il reste des alertes ou des composants a renseigner")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ref = json.loads(REF_JSON.read_text(encoding="utf-8"))
    bp = Path(a.bilan) if a.bilan else Path(a.schema).parent / "bilan.json"
    bilan = json.loads(bp.read_text(encoding="utf-8")) if bp.exists() else {}
    if a.bilan and not bp.exists():
        sys.exit(f"bilan introuvable : {bp}")
    d = ref["defauts"]
    cfg = lambda k: bilan.get(k, d[k])           # noqa: E731
    v_in, marge, taux = cfg("tension_entree_V"), cfg("marge"), cfg("taux_charge_max")
    decl_alim, decl_ptc = cfg("declassement_alim"), d["declassement_ptc_50C"]
    entree = f"{v_in:g}V"
    volt = dict(ref["tensions_rails_V"])
    volt[entree] = float(v_in)
    comps = lire_schema(a.schema)
    alertes, charges, regul, non_reconnus, ignores, absorbes = [], [], {}, [], [], set()

    def rail_norm(r):
        r = (r or "").strip().upper().replace(" ", "").lstrip("+")
        return {"5": "5V", "3.3V": "3V3", "3,3V": "3V3", "12": "12V"}.get(r, r)

    def rail_auto(c, defaut):
        rs = [rail_de(n) for n in c["nets"].values() if rail_de(n)]
        return max(rs, key=lambda r: volt.get(r, 0)) if rs else defaut

    def ajoute(c, nom, rail, ma, src, net=None, hors=False):
        charges.append({"ref": c["ref"] if c else "-", "nom": nom, "rail": rail, "mA": ma, "src": src,
                        "net": net, "hors": hors, "comp": c})

    # --- reseau d'alimentation (rendements)
    reseau = {k: dict(v) for k, v in d["reseau"].items()}
    for r, e in bilan.get("rendements", {}).items():
        reseau.setdefault(r, {"source": entree, "type": "decoupage"})["rendement"] = e
    for r in reseau.values():
        if r["source"] == "ENTREE":
            r["source"] = entree
    deja = set()
    for ref_, c in sorted(comps.items()):
        sur = bilan.get("composants", {}).get(ref_)
        if ref_ in bilan.get("ignorer", []):
            ignores.append((ref_, c["valeur"], "ignore par bilan.json"))
            continue
        champ = c["champs"].get("Conso_mA")
        regle = next((r for r in ref["composants"] if (not r.get("lib_id") or re.search(r["lib_id"], c["lib_id"]))
                      and not (r.get("lib_exclu") and re.search(r["lib_exclu"], c["lib_id"]))
                      and (not r.get("valeur") or re.search(r["valeur"], c["valeur"]))
                      and (r.get("lib_id") or r.get("valeur"))), None)
        if champ is not None or sur:
            try:
                ma = float(str(champ if champ is not None else sur["conso_mA"]).replace(",", "."))
            except (ValueError, KeyError):
                non_reconnus.append((ref_, c["valeur"], f"Conso_mA illisible : {champ!r}"))
                continue
            rr = c["champs"].get("Rail") or (sur or {}).get("rail")
            rail = rail_norm(rr) if rr else rail_auto(c, None)
            if not rail:
                non_reconnus.append((ref_, c["valeur"], "Conso_mA donne mais Rail absent et non deductible"))
                continue
            ajoute(c, c["valeur"], rail, ma, "champ Conso_mA" if champ is not None else "bilan.json")
        elif regle and regle.get("type") == "regulateur":
            rn = regle["rail_sortie"]
            reseau.setdefault(rn, {"source": entree, "type": "decoupage"}).update(
                {"rendement": bilan.get("rendements", {}).get(rn, regle["rendement"]), "i_max_mA": regle["i_max_mA"],
                 "note": regle["source"]})
            regul[rn] = (ref_, c["nets"].get(regle["pin_entree"]))
            ignores.append((ref_, c["valeur"], f"regulateur {rn} : rendement {regle['rendement']} (voir reseau)"))
        elif regle and regle.get("type") == "led":
            r_s = next((r for r in comps.values() if r["lib_id"].endswith(":R") and set(r["nets"].values()) & set(c["nets"].values())
                        and "GND" not in set(r["nets"].values()) & set(c["nets"].values())), None)
            vf = next((v for k, v in ref["vf_led_V"].items() if re.search(k, c["valeur"], re.I)), 2.0)
            if r_s and ohms(r_s["valeur"]):
                comun = (set(r_s["nets"].values()) & set(c["nets"].values()))
                autre = next(n for n in r_s["nets"].values() if n not in comun)
                rl = rail_de(autre)
                v = volt.get(rl, 0) if rl else ref["tension_gpio_V"]
                rl = rl or "3V3"
                absorbes.add(r_s["ref"])
                ajoute(c, f"{c['valeur']} via {r_s['ref']} {r_s['valeur']}", rl, max(0.0, (v - vf) / ohms(r_s["valeur"]) * 1e3),
                       f"I=({fr(v, 1)}-{fr(vf, 1)})/{r_s['valeur']}")
            else:
                ajoute(c, c["valeur"], "3V3", d["led_sans_resistance_mA"], "estime : resistance serie non identifiee")
                alertes.append(f"{ref_} : resistance serie non identifiee, {d['led_sans_resistance_mA']} mA par defaut")
        elif regle:
            if regle.get("groupe") and regle["groupe"] in deja:
                ignores.append((ref_, c["valeur"], f"deja compte avec le groupe {regle['groupe']}"))
                continue
            deja.add(regle.get("groupe"))
            rail = rail_auto(c, regle.get("rail_defaut")) if regle["rail"] == "auto" else regle["rail"]
            ajoute(c, regle["designation"], rail, regle["conso_mA"], regle["source"])
        else:
            ig = next((i for i in ref["ignores"] if re.search(i["lib_id"], c["lib_id"])), None)
            (ignores if ig else non_reconnus).append((ref_, c["valeur"], ig["raison"] if ig else f"inconnu ({c['lib_id']})"))
    ignores = [i for i in ignores if i[0] not in absorbes] + [(r, comps[r]["valeur"], "resistance de LED (comptee dans la LED)") for r in sorted(absorbes)]

    # --- charges externes (bilan.json)
    for ch in bilan.get("charges_externes", []):
        t = ref["charges_externes_types"].get(ch.get("type"), {})
        ma = ch.get("courant_mA", t.get("mA"))
        rail = rail_norm(ch.get("rail", t.get("rail")))
        if ma is None or not rail:
            alertes.append(f"charge externe '{ch.get('nom')}' : courant_mA/rail manquants -> ignoree")
            continue
        ajoute(None, ch.get("nom", "?"), rail, ma * ch.get("qte", 1),
               f"{ch.get('qte', 1)} x {fr(ma, 0)} mA" + (f" ({t['source']})" if t else ""),
               net=ch.get("net"), hors=ch.get("hors_carte", False))

    # --- ramener a l'entree
    def facteur(rail):
        """courant a l'entree par ampere sur ce rail."""
        if rail == entree:
            return 1.0
        r = reseau.get(rail)
        if not r:
            return None
        k = 1.0 if r["type"] == "lineaire" else volt.get(rail, 0) / volt[r["source"]] / r.get("rendement", 0.9)
        f = facteur(r["source"])
        return k * f if f is not None else None

    par_rail, total_in, separes = {}, 0.0, []
    for c in charges:
        f = facteur(c["rail"])
        if f is None:
            separes.append(c)
            alertes.append(f"rail {c['rail']} sans source connue : '{c['nom']}' ({fr(c['mA'], 0)} mA) exclu du total (a alimenter a part ou declarer 'rendements')")
            continue
        c["in"] = c["mA"] / 1000 * f
        par_rail.setdefault(c["rail"], []).append(c)
        total_in += c["in"]

    def courant_rail(rail):
        i = sum(c["mA"] for c in par_rail.get(rail, [])) / 1000
        for r2, e in reseau.items():
            if e["source"] == rail and r2 != rail:
                i += courant_rail(r2) * (1.0 if e["type"] == "lineaire" else volt[r2] / volt[rail] / e.get("rendement", 0.9))
        return i

    # --- fusibles
    racine = trouve_racine(comps, v_in)
    amont = chemin_fusibles(comps, racine) if racine else {}
    i_fus = {}
    for c in charges:
        if c.get("in") is None or c["hors"]:
            continue
        net = c["net"]
        if not net and c["rail"] != entree:
            net = next(iter(regul.values()), (None, None))[1]       # entree du regulateur
        if not net and c["comp"]:
            net = next((n for n in c["comp"]["nets"].values() if rail_de(n) == entree), None)
        for f in amont.get(net, []):
            i_fus[f] = i_fus.get(f, 0) + c["in"]
    fus = []
    for r, c in sorted(comps.items()):
        if not re.search(r"Polyfuse|^Fuse:", c["lib_id"]):
            continue
        m = re.search(r"MF-R\d{3}", c["valeur"])
        h = ref["ptc_maintien_A"].get(m.group(0)) if m else None
        if h is None:
            mm = re.search(r"(\d+[.,]\d+)\s*A", c["valeur"])
            h = float(mm.group(1).replace(",", ".")) if mm else None
        fus.append((r, c["valeur"], h, i_fus.get(r, 0.0)))
        if h is None:
            alertes.append(f"{r} : maintien inconnu ('{c['valeur']}'), a renseigner")
        elif i_fus.get(r, 0) > h * decl_ptc:
            alertes.append(f"{r} : charge {fr(i_fus.get(r, 0))} A > maintien declasse {fr(h * decl_ptc)} A -> calibre superieur")
    for rn, e in reseau.items():
        if e.get("i_max_mA") and courant_rail(rn) * 1000 > e["i_max_mA"]:
            if True:
                alertes.append(f"rail {rn} : {fr(courant_rail(rn))} A > capacite du regulateur ({fr(e['i_max_mA'] / 1000)} A)")

    # --- rapport
    L = [f"# Bilan d'alimentation - {Path(a.schema).stem}", "",
         f"Entree {entree}, marge {fr(marge * 100, 0)} %, charge max {fr(taux * 100, 0)} %, "
         f"declassement alimentation {fr(decl_alim)}. Schema : `{Path(a.schema).name}`" + (f", bilan : `{bp.name}`" if bilan else ", pas de bilan.json"), ""]
    L += ["## Consommateurs (pire cas)", "", "| Ref | Designation | Rail | Courant (mA) | A l'entree (A) | Origine |", "|---|---|---|---|---|---|"]
    for c in sorted(charges, key=lambda c: (-volt.get(c["rail"], 0), c["ref"], c["nom"])):
        L.append(f"| {c['ref']} | {c['nom']}{' (hors carte)' if c['hors'] else ''} | {c['rail']} | {fr(c['mA'], 1)} | "
                 f"{fr(c['in'], 3) if 'in' in c else 'exclu'} | {c['src']} |")
    L += ["", "## Bilan par rail", "", "| Rail | Courant du rail (A) | Puissance (W) | Ramene a l'entree (A) | Remarque |", "|---|---|---|---|---|"]
    for rn in sorted(set(list(par_rail) + [r for r in reseau if courant_rail(r) > 0]), key=lambda r: volt.get(r, 0)):
        i = courant_rail(rn)
        f = facteur(rn)
        e = reseau.get(rn, {})
        rem = "alimente par le DevKit : deja compte dans le 5V" if e.get("type") == "lineaire" else (
            f"rendement {fr(e['rendement'], 2)}" if e.get("rendement") else "direct")
        L.append(f"| {rn} | {fr(i)} | {fr(i * volt.get(rn, 0), 1)} | {fr(i * f) if f else '-'} | {rem} |")
    L += ["", f"**Total a l'entree {entree} : {fr(total_in)} A = {fr(total_in * v_in, 0)} W** (pire cas, tout allume).", ""]

    i_marge = total_in * (1 + marge)
    i_min = i_marge / (taux * decl_alim)
    p_std = [x * 12 for x in ref["calibres_alim_12V_A"]]
    std = next((p for p in p_std if p / v_in >= i_min - 1e-9), None)
    L += ["## Recommandation d'alimentation", "",
          f"- Avec {fr(marge * 100, 0)} % de marge : {fr(i_marge)} A.",
          f"- Chargee a {fr(taux * 100, 0)} % max : **{entree} >= {fr(i_min)} A** ({fr(i_min * v_in, 0)} W minimum)."]
    if std:
        L.append(f"- Calibre standard retenu : **{entree} {fr(std / v_in, 1).rstrip('0').rstrip(',')} A ({fr(std, 0)} W)**, "
                 f"charge a regime ~ {fr(total_in / (std / v_in) * 100, 0)} %.")
    else:
        L.append("- Aucun calibre standard assez grand dans la table : alimentation sur mesure.")
    hors = [c for c in charges if c["hors"] and "in" in c]
    for c in hors:
        cal = next((x for x in ref["calibres_fusible_A"] if x >= 1.5 * c["in"]), None)
        L.append(f"- Fusible cote charge externe '{c['nom']}' ({fr(c['in'])} A) : **{fr(cal, 2).rstrip('0').rstrip(',')} A temporise** entre l'alimentation et la charge.")
    if fus:
        L += ["", "## Fusibles reinitialisables", "", f"| Ref | Valeur | Maintien (A) | Declasse {fr(decl_ptc, 1)} (A) | Courant (A) | Charge | Verdict |", "|---|---|---|---|---|---|---|"]
        for r, v, h, i in fus:
            ok = "inconnu" if h is None else ("OK" if i <= h * decl_ptc else "TROP FAIBLE")
            L.append(f"| {r} | {v} | {fr(h) if h else '?'} | {fr(h * decl_ptc) if h else '?'} | {fr(i)} | "
                     f"{fr(i / (h * decl_ptc) * 100, 0) + ' %' if h else '?'} | {ok} |")
    L += ["", "## A renseigner (non reconnus, NON comptes)", ""]
    L += [f"- `{r}` ({v}) : {m}. Ajouter un champ Conso_mA + Rail au symbole, ou une entree 'composants' dans bilan.json." for r, v, m in non_reconnus] or ["Aucun."]
    if non_reconnus:
        alertes.append(f"{len(non_reconnus)} composant(s) non reconnu(s) : le total est sous-estime")
    L += ["", "## Alertes", ""] + ([f"- {x}" for x in alertes] or ["Aucune."])
    L += ["", "## Composants sans consommation propre (liste explicite)", ""]
    L += ["- " + ", ".join(f"`{r}` ({m})" if False else f"`{r}`" for r, _, m in ignores if m == k) + f" : {k}"
          for k in dict.fromkeys(m for _, _, m in ignores)]
    texte = "\n".join(L) + "\n"
    print(texte)
    if a.md:
        Path(a.md).write_text(texte, encoding="utf-8")
    return 1 if a.strict and (alertes or non_reconnus) else 0


if __name__ == "__main__":
    sys.exit(main())
