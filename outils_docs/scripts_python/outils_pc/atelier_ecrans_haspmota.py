"""Generateur HASPmota de l'atelier des ecrans : description neutre (`ecran.json`) -> texte du `pages.jsonl`.

Regles : x, y, l, h -> x, y, w, h ; `attributs` recopies ; `commentaire` -> `comment` ; une ligne `{"page": n, "comment"}`
puis une ligne `{"page": n, "id": 0, <attributs de la page>}` precedent les objets de la page n.
toucher {"page": n} -> `"action": "p<n>"`. toucher `fonction` ou `commande` -> AUCUNE cle `action` : HASPmota ne sait que
changer de page (`lv_haspmota.be::page_show` : prev, next, back, p<n>) ; ces boutons sont cables par une regle Tasmota
`hasp#p<page>b<id>#event` (ecranHaspmota.BOUTONS pour les debits), pas par le pages.jsonl.
actif : le pages.jsonl porte l'etat de DEMARRAGE (page de demarrage = premiere page de contenu, n >= 1) : le bouton qui
mene a cette page prend les attributs `actif`. liaison, couleur_selon, couleurs, modele : dynamiques, appliques par
l'interface Berry, absents du fichier. QR code : `qr_size` = l (objet carre, atelier_ecrans_description).
`genere` ne valide pas (`atelier_ecrans_description.valide` avant) : un type ou un attribut hors catalogue est rendu tel quel."""

import json

import atelier_ecrans_navigation as nav

BRUT = "brut"           # atelier_ecrans_description.BRUT (import d'un pages.jsonl ecrit a la main)


def _ligne(d):
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))


def _objet(o, depart):
    attrs = dict(o.get("attributs", {}))
    t = o.get("toucher") or {}
    if "page" in t and t["page"] == depart:
        attrs.update(o.get("actif", {}))
    l = {"page": o["page"], "id": o["id"], "obj": o["type"], "x": o["x"], "y": o["y"], "w": o["l"], "h": o["h"], **attrs}
    if o["type"] == "qrcode":           # cote du code = largeur de l'objet (carre), jamais saisi dans la description
        l["qr_size"] = o["l"]
    if "page" in t:
        l["action"] = f"p{t['page']}"
    if "commentaire" in o:
        l["comment"] = o["commentaire"]
    return l


def genere(desc):
    """Texte du pages.jsonl : une ligne JSON par commentaire de page, reglage de page et objet (UTF-8) ; barre de
    navigation deroulee en boutons de la page 0 (atelier_ecrans_navigation)."""
    desc = nav.deroule(desc)
    contenu = [p["n"] for p in desc["pages"] if p["n"] >= 1]
    depart = min(contenu) if contenu else None
    lignes = []
    for p in desc["pages"]:
        if "commentaire" in p:
            lignes.append(_ligne({"page": p["n"], "comment": p["commentaire"]}))
        if p.get("attributs"):
            lignes.append(_ligne({"page": p["n"], "id": 0, **p["attributs"]}))
        for o in desc["objets"]:
            if o["page"] != p["n"]:
                continue
            if o["type"] == BRUT:            # ligne d'un pages.jsonl importe, reecrite telle quelle
                lignes.append(o["texte"] if "texte" in o else _ligne(o["ligne"]))
            else:
                lignes.append(_ligne(_objet(o, depart)))
    return "".join(l + "\n" for l in lignes)


def ecarts(attendu, obtenu):
    """Differences SEMANTIQUES entre deux pages.jsonl (ordre des cles libre, ordre des lignes compte)."""
    a, b = [json.loads(x) for x in attendu.splitlines() if x.strip()], [json.loads(x) for x in obtenu.splitlines() if x.strip()]
    msgs = []
    for i in range(max(len(a), len(b))):
        if i >= len(a):
            msgs.append(f"ligne {i + 1} : en trop dans le genere ({b[i]})")
        elif i >= len(b):
            msgs.append(f"ligne {i + 1} : manquante dans le genere ({a[i]})")
        elif a[i] != b[i]:
            for k in sorted(set(a[i]) | set(b[i])):
                if a[i].get(k, "<absent>") != b[i].get(k, "<absent>"):
                    msgs.append(f"ligne {i + 1} : clé « {k} » : attendu {a[i].get(k, '<absent>')!r}, obtenu {b[i].get(k, '<absent>')!r}")
    return msgs
