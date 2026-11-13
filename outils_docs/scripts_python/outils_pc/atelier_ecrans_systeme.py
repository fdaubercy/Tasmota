"""Page « Systeme » construite par l'atelier des ecrans (plan atelier-ecrans A19), comme la barre de navigation (A17).

Une page de la description porte `"modele": "systeme"` (une seule, n >= 1, sans objet saisi a la main). Ses objets sont
DEROULES ici d'apres la table `ecranSysteme.CHAMPS` de data/fs/ecranSysteme.be (seule reference des donnees, une entree par
ligne : ["cle", "libelle", "unite", id du texte, id de la barre ou nil]) et ses constantes BOUTON_GC, BOUTON_REDEMARRER,
TEXTE_REDEMARRER ; le module Berry n'ecrit que les VALEURS (text, text_color, val et bg_color10 des barres) sur ces ids.
Ids de la page : 1 a 119 = textes et barres de CHAMPS ; 120, 121 = boutons (toucher {"fonction": "ecranSysteme.appui",
"args": [id]} : le LVGL genere l'appelle ; HASPmota n'en tire aucune action, les regles hasp#p<n>b<id>#event sont posees
par controleEcranSysteme) ; 130 a 179 = libelles (130 + rang dans CHAMPS) ; 180 a 188 = titres des groupes (180 + rang) ;
190 a 198 reserves aux icones des groupes (190 + rang, rien d'emis tant que les actions A15 et A18 ne sont pas faites).
Groupes par dizaines d'ids du texte (GROUPES) : un id hors de toute dizaine connue est refuse (un champ ajoute plus tard ne
disparait pas en silence). Mise en page : zone entre le bas du bandeau de la page 0 et le haut de la barre de navigation,
colonnes d'au moins COLONNE_MIN px remplies dans l'ordre des groupes (la plus haute au plus bas), journal (pleine largeur) en bas, boutons au pied de la
colonne la moins remplie ; police et couleurs tirees de la barre de navigation et des libelles des autres pages.
`deroule` est appele par atelier_ecrans_navigation.deroule (point d'entree unique : validateur, deux generateurs, apercu de
la page web) ; `erreurs` par le validateur (atelier_ecrans_description.valide)."""
import collections
import copy
import itertools
import re
from pathlib import Path

import atelier_ecrans_catalogue as cat

RACINE = Path(__file__).resolve().parents[3]
SOURCE = RACINE / "data/fs/ecranSysteme.be"     # lu a chaque appel (les bancs le remplacent par une copie modifiee)
MODELE = "systeme"
# Une entree de CHAMPS par ligne : ["cle", "libelle", "unite", id du texte, id de la barre ou nil]
ENTREE = re.compile(r'^\s*\["(\w+)", "([^"]*)", "([^"]*)", (\d+), (\d+|nil)\],?\]?\s*$')
# (titre, premier id, dernier id, pleine largeur) : dizaines des ids du texte de CHAMPS
GROUPES = [("Mémoire", 1, 19, False), ("Flash", 20, 29, False), ("Charge", 30, 39, False), ("Redémarrages", 40, 49, False),
           ("Réseau", 50, 69, False), ("ModBus", 70, 79, False), ("Écran", 80, 89, False), ("Firmware", 90, 99, False),
           ("Journal", 100, 119, True)]
ID_LIBELLE, ID_LIBELLE_MAX, ID_TITRE, ID_ICONE, ID_MAX = 130, 179, 180, 190, 199
TEXTE_GC = "Lancer le GC"
MARGE_X, MARGE_Y, GOUTTIERE, ECART_GROUPE = 24, 10, 16, 6
COLONNE_MIN, LIGNE_MAX, LIGNE_MIN, BOUTON_H = 300, 24, 18, 44
DEFAUT = {"police": 14, "texte": "#E8EDF2", "secondaire": "#9FB3C8", "fond": "#1F2B38", "accent": "#3FA7FF"}


def champs(texte):
    """Entrees de ecranSysteme.CHAMPS : [(cle, libelle, unite, texte, barre)] ; [] si la table est illisible."""
    m = re.search(r"^ecranSysteme\.CHAMPS = \[\n(.*?)\]\]\s*$", texte, re.M | re.S)
    if not m:
        return []
    lues = [ENTREE.match(l) for l in (m.group(1) + "]]").splitlines()]
    if not all(lues):
        return []
    return [(x[1], x[2], x[3], int(x[4]), None if x[5] == "nil" else int(x[5])) for x in lues]


def lit(source=None):
    """{"champs", "gc", "redemarrer", "texte_redemarrer"} lus dans ecranSysteme.be ; None si illisible ou incomplet."""
    try:
        t = Path(source or SOURCE).read_text(encoding="utf-8")
    except OSError:
        return None
    gc, red = (re.search(rf"^ecranSysteme\.{k} = (\d+)\s*$", t, re.M) for k in ("BOUTON_GC", "BOUTON_REDEMARRER"))
    txt = re.search(r'^ecranSysteme\.TEXTE_REDEMARRER = "([^"]+)"\s*$', t, re.M)
    c = champs(t)
    if not (c and gc and red and txt):
        return None
    return {"champs": c, "gc": int(gc[1]), "redemarrer": int(red[1]), "texte_redemarrer": txt[1]}


def pages_modele(desc):
    return [p for p in desc.get("pages", []) if isinstance(p, dict) and "modele" in p]


def groupe(id_):
    """Rang du groupe de l'id du texte, None hors de toute dizaine connue."""
    return next((i for i, g in enumerate(GROUPES) if g[1] <= id_ <= g[2]), None)


def _style(desc):
    """Police et couleurs des objets voisins : barre de navigation (police, texte, fond, accent), libelles des autres pages
    (couleur secondaire la plus frequente) ; DEFAUT sinon."""
    nav = desc.get("navigation") if isinstance(desc.get("navigation"), dict) else {}
    a, actif = nav.get("attributs") or {}, nav.get("actif") or {}
    s = dict(DEFAUT, texte=a.get("text_color", DEFAUT["texte"]), fond=a.get("bg_color", DEFAUT["fond"]),
             accent=actif.get("bg_color", DEFAUT["accent"]))
    f = a.get("text_font") or next((o["attributs"]["text_font"] for o in desc.get("objets", [])
                                    if o.get("type") == "label" and "text_font" in o.get("attributs", {})), None)
    if isinstance(f, str) and re.search(r"-\d+$", f):
        s["police"] = re.sub(r"-\d+$", "", f) + "-{}"
    autres = collections.Counter(o["attributs"]["text_color"] for o in desc.get("objets", []) if o.get("type") == "label"
                                 and o.get("attributs", {}).get("text_color") not in (None, s["texte"], s["accent"]))
    if autres:
        s["secondaire"] = autres.most_common(1)[0][0]
    return s


def zone(desc, catalogue):
    """(x, haut, largeur, bas) utiles, ou None si l'ecran est absent du catalogue."""
    e = catalogue["ecrans"].get(desc.get("ecran"))
    if e is None:
        return None
    L, H = (e["hauteur"], e["largeur"]) if desc.get("orientation", 0) in (90, 270) else (e["largeur"], e["hauteur"])
    p0 = [o for o in desc.get("objets", []) if o.get("page") == 0 and all(isinstance(o.get(k), int) for k in ("y", "h"))]
    haut = max([o["y"] + o["h"] for o in p0 if o["y"] + o["h"] <= H // 2], default=0) + MARGE_Y
    nav = desc.get("navigation")
    bas = nav["y"] if isinstance(nav, dict) and isinstance(nav.get("y"), int) else \
        min([o["y"] for o in p0 if o["y"] >= H // 2], default=H)
    return MARGE_X, haut, L - 2 * MARGE_X, bas - MARGE_Y


def _colonnes(groupes, n):
    """Groupes repartis DANS L'ORDRE sur n colonnes au plus, la plus haute (en lignes) la plus basse possible."""
    tailles = [len(g[1]) + 1 for g in groupes]
    n = min(n, len(groupes))
    coupes = min(itertools.combinations(range(1, len(groupes)), n - 1),
                 key=lambda c: max(sum(tailles[a:b]) for a, b in zip((0,) + c, c + (len(groupes),))))
    return [groupes[a:b] for a, b in zip((0,) + coupes, coupes + (len(groupes),))]


def plan(desc, catalogue, page, lu=None):
    """(objets, messages) de la page Systeme numero `page` ; objets vides si un message."""
    lu = lu or lit()
    if lu is None:
        return [], [f"page {page} (systeme) : ecranSysteme.CHAMPS illisible dans {SOURCE.name}"]
    z = zone(desc, catalogue)
    if z is None:
        return [], [f"page {page} (systeme) : écran « {desc.get('ecran')} » absent du catalogue"]
    msgs, par_groupe = [], collections.defaultdict(list)
    for rang, c in enumerate(lu["champs"]):
        g = groupe(c[3])
        if g is None:
            msgs.append(f"page {page} (systeme) : champ « {c[0]} » (id {c[3]}) hors des groupes connus "
                        f"({', '.join(f'{t} {a}-{b}' for t, a, b, _ in GROUPES)})")
        par_groupe[g].append((rang, c))
    ids = [i for c in lu["champs"] for i in (c[3], c[4]) if i is not None] + [lu["gc"], lu["redemarrer"]]
    if ID_LIBELLE + len(lu["champs"]) - 1 > ID_LIBELLE_MAX or any(i > ID_MAX for i in ids):
        msgs.append(f"page {page} (systeme) : ids au-delà de {ID_MAX} (libellés {ID_LIBELLE} à {ID_LIBELLE_MAX})")
    if msgs:
        return [], msgs
    x0, haut, larg, bas = z
    groupes = [(g, par_groupe[g]) for g in range(len(GROUPES)) if par_groupe[g]]
    cols = [g for g in groupes if not GROUPES[g[0]][3]]
    pleine = [g for g in groupes if GROUPES[g[0]][3]]
    ncol = max(1, min(len(cols) or 1, (larg + GOUTTIERE) // (COLONNE_MIN + GOUTTIERE)))
    colonnes = _colonnes(cols, ncol) if cols else []
    lignes = max([sum(len(g[1]) + 1 for g in c) for c in colonnes], default=0) + sum(len(g[1]) + 1 for g in pleine)
    ecarts = max([len(c) for c in colonnes], default=0) * ECART_GROUPE + len(pleine) * ECART_GROUPE
    h = min(LIGNE_MAX, (bas - haut - ecarts) // max(1, lignes))
    if h < LIGNE_MIN:
        return [], [f"page {page} (systeme) : place insuffisante ({bas - haut} px de haut pour {lignes} lignes)"]
    s = _style(desc)
    taille = max([x for x in cat.TAILLES_TTF if x <= h - 4], default=cat.TAILLES_TTF[0])   # une taille de la grille
    police = s["police"].format(taille) if isinstance(s["police"], str) else taille
    lw = (larg - (len(colonnes) - 1) * GOUTTIERE) // max(1, len(colonnes))
    objets = []

    def label(id_, x, y, l, texte, couleur, align=0):
        a = {"text": texte, "text_font": police, "text_color": couleur}
        if align:
            a["align"] = align
        objets.append({"id": id_, "page": page, "type": "label", "x": x, "y": y, "l": l, "h": h, "attributs": a})

    def bloc(g, x, y, l, libelle_l):
        label(ID_TITRE + g[0], x, y, l, GROUPES[g[0]][0], s["accent"])
        y += h
        for rang, c in g[1]:
            label(ID_LIBELLE + rang, x, y, libelle_l, c[1], s["secondaire"])
            reste = l - libelle_l
            if c[4] is not None:            # barre au milieu, valeur courte a droite
                bl = reste * 2 // 5
                objets.append({"id": c[4], "page": page, "type": "bar", "x": x + libelle_l, "y": y + h // 4, "l": bl - 8,
                               "h": h // 2, "attributs": {"min": 0, "max": 100, "val": 0, "radius": h // 4, "bg_color": s["fond"],
                                                          "radius10": h // 4, "bg_color10": s["accent"]}})
                label(c[3], x + libelle_l + bl, y, reste - bl, "--", s["texte"], 2)
            else:
                label(c[3], x + libelle_l, y, reste, "--", s["texte"], 0 if GROUPES[g[0]][3] else 2)
            y += h
        return y + ECART_GROUPE

    fins = []
    for i, c in enumerate(colonnes):
        x, y = x0 + i * (lw + GOUTTIERE), haut
        for g in c:
            y = bloc(g, x, y, lw, lw // 2)
        fins.append(y)
    y = max(fins, default=haut)
    for g in pleine:
        y = bloc(g, x0, y, larg, min(lw // 2, 200))
    # boutons au pied de la colonne la moins remplie (pleine largeur sous le journal s'il n'y a pas de colonne)
    i = min(range(len(fins)), key=lambda k: fins[k]) if fins else None
    bx, by, bl = (x0 + i * (lw + GOUTTIERE), max(fins) - ECART_GROUPE - BOUTON_H, lw) if i is not None else (x0, y, larg)
    if i is not None and by < fins[i]:
        return [], [f"page {page} (systeme) : place insuffisante pour les boutons ({BOUTON_H} px)"]
    if i is None and by + BOUTON_H > bas:
        return [], [f"page {page} (systeme) : place insuffisante pour les boutons ({BOUTON_H} px)"]
    l2 = (bl - GOUTTIERE) // 2
    for k, (id_, texte) in enumerate(((lu["gc"], TEXTE_GC), (lu["redemarrer"], lu["texte_redemarrer"]))):
        objets.append({"id": id_, "page": page, "type": "btn", "x": bx + k * (l2 + GOUTTIERE), "y": by, "l": l2, "h": BOUTON_H,
                       "attributs": {"radius": BOUTON_H // 2, "border_width": 0, "text": texte, "text_font": police,
                                     "bg_color": s["fond"], "text_color": s["texte"]},
                       "toucher": {"fonction": "ecranSysteme.appui", "args": [id_]}})
    return objets, []


def erreurs(desc, catalogue):
    """Messages du validateur pour les pages a modele (description BRUTE, avant deroule) ; [] sans page a modele."""
    pm = pages_modele(desc)
    msgs = []
    for p in pm:
        if p["modele"] != MODELE:
            msgs.append(f"page {p.get('n')} : modèle « {p['modele']} » inconnu (connu : {MODELE})")
        elif not (isinstance(p.get("n"), int) and p["n"] >= 1):
            msgs.append(f"page {p.get('n')} : la page Système est une page n >= 1")
    sys_ = [p for p in pm if p["modele"] == MODELE]
    if len(sys_) > 1:
        msgs.append("une seule page Système (ecranSysteme écrit sur la page modules.ecranSysteme.page du persist)")
    for o in desc.get("objets", []):
        if any(o.get("page") == p.get("n") for p in pm):
            msgs.append(f"objet {o.get('page')}/{o.get('id')} : page construite par l'atelier (modèle), aucun objet à la main")
    if msgs:
        return msgs
    for p in sys_:
        msgs += plan(desc, catalogue, p["n"])[1]
    return msgs


def deroule(desc, catalogue=None):
    """Copie de la description, objets de la page Systeme ajoutes et cle `modele` retiree (deroule une seule fois) ;
    sans page a modele : elle-meme. Description refusee par `erreurs` : page laissee vide."""
    pm = pages_modele(desc)
    if not pm:
        return desc
    catalogue = catalogue or cat.charge(RACINE)
    d = copy.deepcopy(desc)
    for p in d["pages"]:
        if p.pop("modele", None) == MODELE and isinstance(p.get("n"), int):
            d["objets"] = d.get("objets", []) + plan(desc, catalogue, p["n"])[0]
    return d
