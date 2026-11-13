"""Import d'un pages.jsonl ecrit a la main vers une description de l'atelier des ecrans (plan atelier-ecrans A13, spec
2026-11-12 § 5).

Lecture comme HASPmota (`lv_haspmota.be`) : une ligne JSON par objet, la page courante change a chaque cle `page` et
s'herite sinon, lignes vides ignorees. Par page : son premier `{"page":n,"comment"}` -> commentaire (et titre) de la page,
son `{"id":0, ...}` place avant tout objet -> reglages de la page, s'ils sont des attributs connus de `obj`. Objet du
palier 1 ou 2 du catalogue, x, y, w, h entiers (QR code : qr_size = w = h), attributs connus et valides, `action` p<n> vers une page du fichier -> objet
EDITABLE (`toucher`). Tout le reste -> objet `brut` : la ligne d'origine gardee telle quelle (`ligne`, ou `texte` pour
une ligne non JSON, signalee), reecrite a l'identique par le generateur HASPmota, absente de l'interface LVGL pur.
Sur la carte (lu dans `lv_haspmota.be::HASPmota._load`, pas encore vu sur carte) : une ligne commencant par `#` est sautee
sans message, une autre ligne non JSON est sautee avec le log niveau 2 « HSP: invalid JSON line », le chargement continue.
Ecart connu : HASPmota part sans page courante (une premiere ligne sans `page` le fait echouer) ; l'import la range en
page 1, et la ligne regeneree a l'identique garde ce comportement.
Aucune liaison n'est importee (un ecran ecrit a la main est rempli par son Berry). Garantie (banc
test_atelier_ecrans_import.py) : generation HASPmota de la description importee = memes objets JSON que la source, meme
ordre, lus par `lignes_effectives`.
"""
import json
import re
from pathlib import Path

import atelier_ecrans_catalogue as cat
import atelier_ecrans_description as aed
import fichiers_berry_etat as fbe

BASE = {"page", "id", "obj", "x", "y", "w", "h", "action", "comment"}
ACTION_PAGE = re.compile(r"p(\d+)")
# comportement HASPmota sans equivalent dans l'interface LVGL pur (regles, Berry, parent) : la ligne reste brute
HASPMOTA_SEUL = re.compile(r"(val_rule|text_rule|berry_run|parentid)\w*")


def _entier(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _lignes(texte):
    """[(n, page courante, dict | None, texte)] dans l'ordre ; lignes vides ignorees, page courante de depart 1."""
    page, res = 1, []
    for n, brut in enumerate(texte.splitlines(), 1):
        s = brut.strip()
        if not s:
            continue
        try:
            d = json.loads(s)
        except ValueError:
            d = None
        if not isinstance(d, dict):
            res.append((n, page, None, s))
            continue
        if _entier(d.get("page")):
            page = d["page"]
        res.append((n, page, d, s))
    return res


def lignes_effectives(texte):
    """Ce que HASPmota lit : [{..., "page": page courante}] pour une ligne JSON, ["texte", ligne] sinon."""
    return [{**d, "page": p} if d is not None else ["texte", s] for _, p, d, s in _lignes(texte)]


def _editable(d, p, pages, ecran, catalogue, pris):
    """Objet editable tire de la ligne `d` (page courante p), ou None si la ligne doit rester brute."""
    t = d.get("obj")
    if not cat.dans_atelier(catalogue, t):
        return None
    if any(HASPMOTA_SEUL.fullmatch(k) for k in d):
        return None
    if not all(_entier(d.get(k)) for k in ("id", "x", "y", "w", "h")) or d["id"] < 1 or (p, d["id"]) in pris:
        return None
    o = {"id": d["id"], "page": p, "type": t, "x": d["x"], "y": d["y"], "l": d["w"], "h": d["h"],
         "attributs": {k: v for k, v in d.items() if k not in BASE}}
    if t == "qrcode" and d.get("qr_size") == d["w"] == d["h"]:      # pose par le generateur HASPmota d'apres l
        del o["attributs"]["qr_size"]
    if "action" in d:
        m = ACTION_PAGE.fullmatch(str(d["action"]))
        if not m or int(m.group(1)) not in pages:
            return None
        o["toucher"] = {"page": int(m.group(1))}
    if "comment" in d:
        if not isinstance(d["comment"], str):
            return None
        o["commentaire"] = d["comment"]
    essai = {"version": 1, "ecran": ecran, "pages": [{"n": n} for n in pages], "objets": [o]}
    return None if aed.valide(essai, catalogue) else o


def _reglages_page(d, ecran, catalogue):
    attrs = {k: v for k, v in d.items() if k not in ("page", "id")}
    if not attrs or "obj" in d:
        return None
    essai = {"version": 1, "ecran": ecran, "pages": [{"n": 0, "attributs": attrs}], "objets": []}
    return None if aed.valide(essai, catalogue) else attrs


def importe(texte, ecran, catalogue):
    """{"description", "avertissements", "editables", "bruts"} ; rien n'est ecrit."""
    lignes = _lignes(texte)
    ordre = []
    for _, p, _, _ in lignes:
        if not ordre or ordre[-1] != p:
            ordre.append(p)
    numeros = list(dict.fromkeys(ordre))
    av = [f"page {p} en plusieurs morceaux dans le fichier : ses lignes sont regroupees"
          for p in numeros if ordre.count(p) > 1]
    pages = {p: {"n": p, "titre": f"Page {p}"} for p in numeros}
    vue, objets, pris = set(), [], set()           # vue : pages dont une ligne autre que l'en-tete a ete lue
    for n, p, d, s in lignes:
        page = pages[p]
        if d is None:
            objets.append({"type": aed.BRUT, "page": p, "id": None, "texte": s})
            av.append(f"ligne {n} non JSON gardée telle quelle (commentaire) : {s[:60]}")
            vue.add(p)
            continue
        if set(d) - {"page"} == {"comment"} and isinstance(d["comment"], str) and p not in vue and "commentaire" not in page \
                and "attributs" not in page:
            page["commentaire"] = d["comment"]
            page["titre"] = d["comment"][:60] or page["titre"]
            continue
        if d.get("id") == 0 and p not in vue and "attributs" not in page:
            attrs = _reglages_page(d, ecran, catalogue)
            if attrs is not None:
                page["attributs"] = attrs
                continue
        vue.add(p)
        o = _editable(d, p, numeros, ecran, catalogue, pris)
        if o is None:
            o = {"type": aed.BRUT, "page": p, "id": d["id"] if _entier(d.get("id")) else None, "ligne": d}
        else:
            pris.add((p, o["id"]))
        objets.append(o)
    desc = {"version": 1, "ecran": ecran, "orientation": 0, "modele": [], "pages": list(pages.values()), "objets": objets}
    nb = sum(1 for o in objets if o["type"] == aed.BRUT)
    if nb:
        av.append(f"{nb} ligne(s) gardée(s) telles quelles (objets bruts : non éditables, absents de l'interface LVGL pur)")
    return {"description": desc, "avertissements": av, "editables": len(objets) - nb, "bruts": nb}


def depuis_carte(racine, env):
    """Import du pages.jsonl du dossier de la carte : importe(...) + {"source"} ; LookupError sans pages.jsonl,
    ValueError pour une carte sans ecran au catalogue. Rien n'est ecrit (l'ecriture passe par POST /diff puis /ecrire)."""
    rel = f"{fbe.dossier_carte(env)}/pages.jsonl"
    p = Path(racine) / rel
    if not p.is_file():
        raise LookupError(f"{rel} absent : rien a importer")
    ecran = cat.ecrans_des_envs(racine).get(env)
    if ecran is None:
        raise ValueError(f"{env} sans ecran au catalogue (display.ini absent ou exclu du FS) : import impossible")
    return {**importe(p.read_text(encoding="utf-8", errors="replace"), ecran, cat.charge(racine)), "source": rel}
