"""Description neutre de l'ecran d'une carte (atelier des ecrans) : `outils_docs/atelier_ecrans/cartes/<env>/ecran.json`.

Forme : {"version": 1, "ecran": <cle du catalogue>, "orientation": 0|90|180|270,
         "modele": [{"cle", "type", "exemple", "longueur"?}],   valeurs liables (cles de ecranDebitsFonctions.modele) ;
                       longueur obligatoire pour une cle de liste (`voies[].debit`) : borne l'indice des liaisons
         "pages": [{"n", "titre", "attributs"?, "commentaire"?}],     page 0 = commun a toutes les pages
         "objets": [{"id", "page", "type", "x", "y", "l", "h", "attributs": {}, "liaison"?, "toucher"?, "commentaire"?}]}
  liaison : {"cle", "attribut", "indice"?}   indice (0 a longueur - 1) obligatoire pour une cle de liste (`voies[].debit`)
  liaison.table (facultatif) : la valeur du modele est un NOM, converti en couleur par `couleurs[table]` (pastille : "vert")
  liaison.format, liaison.echelle (facultatifs, attribut "text" seulement) : texte = format % (valeur / echelle) ; format a UNE
      directive de string.format (`"%d L/min"`), echelle nombre non nul, jamais sans format
  liaison d'un chart, attribut "series" : la valeur est une liste de series (listes de points, nil = inconnu), avec
      "points" : cle du modele qui compte les points ajoutes depuis le demarrage (seuls les nouveaux sont pousses),
      "max"    : cle du modele du haut de l'axe Y,
      "couleurs" : une #RRGGBB par serie, autant que la longueur de la cle liee ;
      ces trois cles sont obligatoires sur une courbe et interdites sur toute autre liaison
  couleur_selon : [regle] sur un objet, couleur d'un attribut recalculee a chaque rafraichissement d'apres une valeur du modele :
      {"attribut", "cle", "indice"?, "table", "sauf"?: {valeur: "#RRGGBB"}}     couleurs[table][valeur], sauf pour les valeurs de `sauf`
      {"attribut", "cle", "indice"?, "si": {valeur: "#RRGGBB"}, "sinon": "#RRGGBB"}
  actif : {attribut couleur: "#RRGGBB"} sur un bouton qui change de page : ces valeurs quand sa page est la page courante,
      sinon ses `attributs`
  couleurs (racine) : {table: {nom: "#RRGGBB"}}, p. ex. "etat" = ecranDebitsFonctions.COULEURS
  toucher : un seul de {"page": n} | {"commande": "<commande Tasmota>"} | {"fonction": "<module.fonction>", "args"?: [..]}
  objet brut (import d'un pages.jsonl ecrit a la main, atelier_ecrans_import) : {"type": "brut", "page", "id" | null,
      "ligne": {ligne JSON d'origine}} ou {..., "texte": "<ligne non JSON>"} ; reecrit tel quel par le generateur HASPmota,
      absent de l'interface LVGL pur, non editable ; seuls sa forme et sa page sont controlees
`valide` ne lit que la description et le catalogue (atelier_ecrans_catalogue) ; la section `modele` est comparee a la map
rendue par le module metier dans berry/banc_ecran_debits.py."""

import hashlib
import json
import re
from pathlib import Path

import atelier_ecrans_catalogue as cat

DOSSIER = "outils_docs/atelier_ecrans/cartes"
TYPES_MODELE = ("texte", "entier", "liste", "booleen")
ATTRIBUTS_LIAISON_SPECIAUX = ("series",)       # liaison sans attribut LVGL : les courbes d'un chart
TOUCHER = ("page", "commande", "fonction")
BRUT = "brut"
COULEUR = re.compile(r"#[0-9A-Fa-f]{6}")
POLICE_TTF = re.compile(r"A:sd/polices/(.+\.ttf)-(\d+)")
POLICE_FIRMWARE = re.compile(r"(montserrat|seg7)-(\d+)")
# Image d'un objet img : un PNG range par gestionFileFolder.be (le firmware ne decode que le PNG), ou le logo embarque
IMAGE = re.compile(r"A:sd/images/PNG/[^/\:*?\"<>|]+\.png", re.I)
DIRECTIVE = re.compile(r"%[-+ #0]*\d*(?:\.\d+)?[diouxXeEfgGsc]")


def chemin(racine, env):
    return Path(racine) / DOSSIER / env / "ecran.json"


def charge(racine, env):
    """Description de l'env, ou None (fichier absent ou illisible : jamais d'exception)."""
    try:
        d = json.loads(chemin(racine, env).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def empreinte(octets):
    return hashlib.sha256(octets).hexdigest()


def texte(d):
    """Texte de l'ecran.json a la mise en forme du depot : une cle par ligne, un element de liste par ligne (UTF-8, \\n)."""
    v = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))
    lignes = [f"{v(k)}:[\n" + ",\n".join(" " + v(e) for e in x) + "\n]" if isinstance(x, list) and x else f"{v(k)}:{v(x)}"
              for k, x in d.items()]
    return "{\n" + ",\n".join(lignes) + "\n}\n"


def _indice(cle, indice, modele, qui, quoi, msgs):
    """Indice d'une cle de liste : entier dans 0 .. longueur - 1 de la section modele."""
    if "[]" not in cle:
        return
    n = modele.get(cle)
    if not (_entier(indice) and indice >= 0):
        msgs.append(f"{qui} : {quoi} de liste « {cle} » sans indice")
    elif _entier(n) and indice >= n:
        msgs.append(f"{qui} : {quoi} : indice {indice} hors de la liste « {cle} » ({n} éléments)")


def _entier(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _type_attribut(catalogue, type_, cle):
    """Type de l'attribut `cle` de `type_` (None si inconnu) ; `%` final et chiffres de partie/etat (radius10) admis."""
    attrs = catalogue["objets"].get(type_, {}).get("attributs", {})
    if cle.endswith("%"):
        cle = cle[:-1]
    if cle in attrs:
        return attrs[cle]["type"]
    if len(cle) > 2 and cle[-2:].isdigit() and cle[:-2] in attrs:
        return attrs[cle[:-2]]["type"]
    return None


def _police(catalogue, v):
    """Message si la police `v` n'existe pas dans le catalogue (ecriture HASPmota), sinon None."""
    polices = {p["nom"]: p for p in catalogue["polices"]}
    if _entier(v):
        t = polices["robotocondensed"]["tailles"]
        return None if v in t else f"taille {v} de robotocondensed non compilée (disponibles : {', '.join(map(str, t))})"
    if isinstance(v, str):
        m = POLICE_TTF.fullmatch(v)
        if m:
            p = next((p for p in catalogue["polices"] if p.get("fichier") == m.group(1)), None)
            if p is None:
                return f"police {m.group(1)} absente du catalogue"
            n = int(m.group(2))
            if p.get("taille_libre"):
                return None if n > 0 else f"taille {n} invalide pour {m.group(1)}"
            return None if n in p["tailles"] else f"taille {n} absente de {m.group(1)}"
        m = POLICE_FIRMWARE.fullmatch(v)
        if m:
            n = int(m.group(2))
            t = polices[m.group(1)]["tailles"]
            return None if n in t else f"taille {n} absente de {m.group(1)} (disponibles : {', '.join(map(str, t))})"
    return f"police « {v} » absente du catalogue"


def _attributs(catalogue, type_, attrs, qui, msgs):
    for k, v in attrs.items():
        t = _type_attribut(catalogue, type_, k)
        if t is None:
            msgs.append(f"{qui} : attribut « {k} » inconnu du type {type_}")
        elif t == "couleur" and not (isinstance(v, str) and COULEUR.fullmatch(v)):
            msgs.append(f"{qui} : couleur « {v} » de {k} mal formée (attendu #RRGGBB)")
        elif t == "police":
            m = _police(catalogue, v)
            if m:
                msgs.append(f"{qui} : {k} : {m}")
        elif t == "entier" and not _entier(v):
            msgs.append(f"{qui} : {k} doit être un entier")
        elif t == "texte" and not isinstance(v, str):
            msgs.append(f"{qui} : {k} doit être un texte")
        elif t == "booleen" and not isinstance(v, bool):
            msgs.append(f"{qui} : {k} doit être un booléen (true ou false)")
        elif t == "liste" and not isinstance(v, list):
            msgs.append(f"{qui} : {k} doit être une liste")
        elif t == "lignes" and not (isinstance(v, str) and v.strip()):
            msgs.append(f"{qui} : {k} : texte non vide attendu, une option par ligne")
    if type_ == "img" and "src" in attrs and not (attrs["src"] == "tasmota_logo" or IMAGE.fullmatch(str(attrs["src"]))):
        msgs.append(f"{qui} : src « {attrs['src']} » : image PNG rangée sous A:sd/images/PNG/ attendue (ou tasmota_logo)")
    if type_ == "roller" and "text" in attrs:
        msgs.append(f"{qui} : text : refusé sur une roue (lvh_roller::set_text lève une erreur sur la carte)")
    if type_ == "qrcode" and "qr_size" in attrs:
        msgs.append(f"{qui} : qr_size : la taille du QR code est sa largeur l, posée par les générateurs")


def _couleur(v, qui, quoi, msgs):
    if not (isinstance(v, str) and COULEUR.fullmatch(v)):
        msgs.append(f"{qui} : couleur « {v} » de {quoi} mal formée (attendu #RRGGBB)")


def _regle(catalogue, t, regle, qui, cles, modele, tables, msgs):
    """Une regle de `couleur_selon` : attribut de type couleur, cle du modele (indice si liste), table, couleurs."""
    a = regle.get("attribut", "")
    if _type_attribut(catalogue, t, a) != "couleur":
        msgs.append(f"{qui} : couleur_selon : « {a} » n'est pas un attribut de couleur du type {t}")
    c = regle.get("cle")
    if c not in cles:
        msgs.append(f"{qui} : couleur_selon : clé « {c} » absente de la section modèle")
    else:
        _indice(c, regle.get("indice"), modele, qui, "couleur_selon : clé", msgs)
    if "table" in regle:
        if regle["table"] not in tables:
            msgs.append(f"{qui} : couleur_selon : table « {regle['table']} » absente de couleurs")
        for k, v in regle.get("sauf", {}).items():
            _couleur(v, qui, f"sauf[{k}]", msgs)
    elif "si" in regle and "sinon" in regle:
        for k, v in regle["si"].items():
            _couleur(v, qui, f"si[{k}]", msgs)
        _couleur(regle["sinon"], qui, "sinon", msgs)
    else:
        msgs.append(f"{qui} : couleur_selon : une règle porte « table » ou « si » et « sinon »")


def _courbe(li, qui, cles, modele, msgs):
    """Cles points, max, couleurs : obligatoires sur une liaison "series", interdites ailleurs."""
    if li.get("attribut") != "series":
        for k in ("points", "max", "couleurs"):
            if k in li:
                msgs.append(f"{qui} : liaison : « {k} » réservé à une courbe (attribut series)")
        return
    for k in ("points", "max"):
        if k not in li:
            msgs.append(f"{qui} : courbe sans « {k} » (clé du modèle)")
        elif li[k] not in cles:
            msgs.append(f"{qui} : courbe : {k} « {li[k]} » absent de la section modèle")
    c = li.get("couleurs")
    if not isinstance(c, list):
        msgs.append(f"{qui} : courbe sans couleurs (une #RRGGBB par série)")
        return
    for i, v in enumerate(c):
        _couleur(v, qui, f"couleurs[{i}]", msgs)
    n = modele.get(li.get("cle"))
    if _entier(n) and len(c) != n:
        msgs.append(f"{qui} : courbe : {len(c)} couleurs pour {n} séries")


def _format(li, qui, msgs):
    """format a une seule directive, echelle nombre non nul ; les deux sur l'attribut text seulement."""
    if "format" in li:
        f = li["format"]
        if li.get("attribut") != "text":
            msgs.append(f"{qui} : liaison : format réservé à l'attribut text")
        elif not (isinstance(f, str) and len(DIRECTIVE.findall(f)) == 1 and "%" not in DIRECTIVE.sub("", f).replace("%%", "")):
            msgs.append(f"{qui} : liaison : format « {f} » : une seule directive (%d, %s, %.1f...) attendue")
    if "echelle" in li:
        e = li["echelle"]
        if "format" not in li:
            msgs.append(f"{qui} : liaison : echelle sans format")
        elif isinstance(e, bool) or not isinstance(e, (int, float)) or e == 0:
            msgs.append(f"{qui} : liaison : echelle « {e} » : nombre non nul attendu")


def valide(d, catalogue):
    """Messages d'erreur en francais ; liste vide = description valide."""
    msgs = []
    if d.get("version") != 1:
        msgs.append(f"version {d.get('version')!r} non prise en charge (attendu 1)")
    ecran = catalogue["ecrans"].get(d.get("ecran"))
    if ecran is None:
        return msgs + [f"écran « {d.get('ecran')} » absent du catalogue"]
    if d.get("orientation", 0) not in (0, 90, 180, 270):
        msgs.append("orientation : 0, 90, 180 ou 270")
    L, H = ecran["largeur"], ecran["hauteur"]
    if d.get("orientation", 0) in (90, 270):
        L, H = H, L
    cles = []
    modele = {m.get("cle"): m.get("longueur") for m in d.get("modele", [])}
    for m in d.get("modele", []):
        if m.get("cle") in cles:
            msgs.append(f"modèle : clé « {m.get('cle')} » en double")
        cles.append(m.get("cle"))
        n = m.get("longueur")
        if ("[]" in str(m.get("cle")) or m.get("type") == "liste") and not (_entier(n) and n > 0):
            msgs.append(f"modèle : {m.get('cle')} est une liste, longueur entière positive obligatoire")
        if m.get("type") not in TYPES_MODELE:
            msgs.append(f"modèle : type « {m.get('type')} » de {m.get('cle')} inconnu ({', '.join(TYPES_MODELE)})")
    tables = d.get("couleurs", {})
    for nom, table in tables.items():
        for k, v in table.items():
            _couleur(v, f"couleurs[{nom}]", k, msgs)
    pages = []
    for p in d.get("pages", []):
        if p.get("n") in pages:
            msgs.append(f"page {p.get('n')} en double")
        pages.append(p.get("n"))
        _attributs(catalogue, "obj", p.get("attributs", {}), f"page {p.get('n')}", msgs)
    vus = set()
    for o in d.get("objets", []):
        qui = f"objet {o.get('page')}/{o.get('id')}"
        if o.get("page") not in pages:
            msgs.append(f"{qui} : page {o.get('page')} inconnue")
        if o.get("type") == BRUT:            # ligne gardee telle quelle : sa forme seulement
            if not ((isinstance(o.get("ligne"), dict) and "texte" not in o) or (isinstance(o.get("texte"), str) and "ligne" not in o)):
                msgs.append(f"{qui} : objet brut : une ligne JSON (ligne) ou un texte (texte), pas les deux")
            elif "texte" in o and (not o["texte"].strip() or "\n" in o["texte"] or "\r" in o["texte"]):
                msgs.append(f"{qui} : objet brut : texte d'une seule ligne, non vide")
            continue
        if (o.get("page"), o.get("id")) in vus:
            msgs.append(f"{qui} : identifiant en double sur la page")
        vus.add((o.get("page"), o.get("id")))
        t = o.get("type")
        if t not in catalogue["objets"]:
            msgs.append(f"{qui} : type « {t} » inconnu du catalogue")
        elif not cat.dans_atelier(catalogue, t):
            msgs.append(f"{qui} : type {t} de palier {catalogue['objets'][t]['palier']}, hors de l'atelier")
        else:
            _attributs(catalogue, t, o.get("attributs", {}), qui, msgs)
        x, y, l, h = (o.get(k) for k in ("x", "y", "l", "h"))
        if not all(_entier(v) for v in (x, y, l, h)) or x < 0 or y < 0 or l <= 0 or h <= 0 or x + l > L or y + h > H:
            msgs.append(f"{qui} : hors de l'écran {L} x {H} (x={x}, y={y}, l={l}, h={h})")
        if t == "qrcode" and l != h:
            msgs.append(f"{qui} : QR code carré attendu (l = h)")
        li = o.get("liaison")
        if li:
            if li.get("cle") not in cles:
                msgs.append(f"{qui} : liaison vers « {li.get('cle')} » absente de la section modèle")
            else:
                _indice(li["cle"], li.get("indice"), modele, qui, "liaison", msgs)
            if "table" in li:
                if li["table"] not in tables:
                    msgs.append(f"{qui} : liaison : table « {li['table']} » absente de couleurs")
                if _type_attribut(catalogue, t, li.get("attribut", "")) != "couleur":
                    msgs.append(f"{qui} : liaison : table de couleurs sur « {li.get('attribut')} », qui n'est pas une couleur")
            _courbe(li, qui, cles, modele, msgs)
            _format(li, qui, msgs)
            if li.get("attribut") not in ATTRIBUTS_LIAISON_SPECIAUX and \
                    (t not in catalogue["objets"] or _type_attribut(catalogue, t, li.get("attribut", "")) is None):
                msgs.append(f"{qui} : liaison vers l'attribut « {li.get('attribut')} » inconnu du type {t}")
        for regle in o.get("couleur_selon", []):
            _regle(catalogue, t, regle, qui, cles, modele, tables, msgs)
        for k, v in o.get("actif", {}).items():
            if _type_attribut(catalogue, t, k) != "couleur":
                msgs.append(f"{qui} : actif : « {k} » n'est pas un attribut de couleur du type {t}")
            _couleur(v, qui, f"actif[{k}]", msgs)
        if "actif" in o and "page" not in (o.get("toucher") or {}):
            msgs.append(f"{qui} : actif : réservé à un objet dont le toucher change de page")
        to = o.get("toucher")
        if to:
            cle = [k for k in TOUCHER if k in to]
            if len(cle) != 1 or set(to) - {cle[0], "args"} or ("args" in to and cle[0] != "fonction"):
                msgs.append(f"{qui} : toucher : une seule action parmi {', '.join(TOUCHER)} (args avec fonction seulement)")
            elif cle[0] == "page" and to["page"] not in pages:
                msgs.append(f"{qui} : toucher vers la page {to['page']} inconnue")
            elif cle[0] != "page" and not (isinstance(to[cle[0]], str) and to[cle[0]]):
                msgs.append(f"{qui} : toucher : {cle[0]} doit être un texte non vide")
    return msgs
