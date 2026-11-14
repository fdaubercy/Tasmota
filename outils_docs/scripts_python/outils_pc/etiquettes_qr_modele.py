"""Modele des etiquettes QR code : gabarit, surcharge par carte, champs, cles du persist, texte lu (plan etiquettes-qrcode A2).

Le reglage d'une carte = le gabarit commun (`outils_docs/etiquettes_qr/gabarit.json`) fusionne a sa surcharge
(`outils_docs/etiquettes_qr/cartes/<env>.json`) : `lignes` et `separateur` remplaces en entier, `style` cle par cle.
Une ligne vient d'un champ standard du depot (hostname, ip, topic, env, puce, lieu), d'une cle du persist de la carte
(chemin pointe, index de liste en chiffres) ou d'un texte libre. Ligne sans valeur : omise du texte, avertissement.

Secrets (spec §4 et §7.9-6) : une cle de nom secret (`assistant_persist_modele.SECRET`, seule definition) n'est jamais
proposee ni lue, ni rien sous elle ; une valeur qui contient la valeur d'une cle secrete du meme persist non plus (URL
avec jeton...). Les valeurs secretes de moins de 4 caracteres sont ignorees par ce second filtre (sinon « ON » cacherait
tout). Le controle est refait a la resolution : une ligne de reglage qui designe un secret est refusee, pas lue.

Le texte du QR code est encode en UTF-8 par la page et la carte (outils_docs/etiquettes_qr/lib/LISEZMOI.md).
"""

import base64
import copy
import functools
import hashlib
import json
import re
import subprocess
from pathlib import Path

import build_envs
import fichiers_berry_etat
import lieux
from assistant_persist_modele import SECRET

DOSSIER = Path("outils_docs/etiquettes_qr")
GABARIT = DOSSIER / "gabarit.json"
CHAMPS = ("hostname", "ip", "topic", "env", "puce", "lieu", "range_extender")
POINTS = ("square", "dots", "rounded", "classy", "classy-rounded", "extra-rounded")
COINS = ("square", "dot", "extra-rounded")
IMAGE_MAX = 8192                         # octets de l'image en data URI
TYPES_IMAGE = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml"}
# Entre deux lignes du texte : l'appareil photo et l'appli « QR Code » de l'iPhone n'affichent aucun saut de ligne
# (ni LF ni CR LF, essai du 2026-11-12) ; d'ou un separateur sur une seule ligne par defaut dans le gabarit.
ENTRE_LIGNES = ("\n", " · ", " | ")
NOM_ENV = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
COULEUR = re.compile(r"^#[0-9a-fA-F]{6}$")
SECRET_MIN = 4


# --- reglage ---------------------------------------------------------------------------------------------------------

def _env_valide(env):
    if not isinstance(env, str) or not NOM_ENV.match(env):
        raise ValueError(f"nom d'env invalide : {env!r}")
    return env


def chemin_surcharge(racine, env):
    return Path(racine) / DOSSIER / "cartes" / f"{_env_valide(env)}.json"


def fusionne(gabarit, surcharge):
    """Reglage effectif : `style` fusionne cle par cle, toute autre cle de la surcharge remplace celle du gabarit."""
    r = copy.deepcopy(gabarit)
    for cle, valeur in (surcharge or {}).items():
        if cle == "style" and isinstance(valeur, dict):
            r["style"] = {**(gabarit.get("style") or {}), **copy.deepcopy(valeur)}
        else:
            r[cle] = copy.deepcopy(valeur)
    return r


def charge_gabarit(racine):
    return json.loads((Path(racine) / GABARIT).read_text(encoding="utf-8"))


def charge_reglage(racine, env):
    chemin = chemin_surcharge(racine, env)
    surcharge = json.loads(chemin.read_text(encoding="utf-8")) if chemin.is_file() else {}
    return fusionne(charge_gabarit(racine), surcharge)


def valide_reglage(reglage, racine=None):
    """Messages en francais, liste vide = valide. Avec `racine`, l'image est aussi lue et controlee."""
    err = []
    if not isinstance(reglage, dict):
        return ["le réglage doit être un objet JSON"]
    lignes = reglage.get("lignes")
    if not isinstance(lignes, list) or not 1 <= len(lignes) <= 20:
        err.append("il faut de 1 à 20 lignes")
        lignes = []
    for i, l in enumerate(lignes, 1):
        if not isinstance(l, dict):
            err.append(f"ligne {i} : objet attendu")
            continue
        src, lib = l.get("source"), l.get("libelle", "")
        if not isinstance(lib, str) or len(lib) > 40:
            err.append(f"ligne {i} : libellé de 40 caractères au plus")
        if src == "standard" and l.get("cle") not in CHAMPS:
            err.append(f"ligne {i} : champ standard inconnu {l.get('cle')!r}")
        elif src == "persist" and (not isinstance(l.get("chemin"), str) or not l["chemin"].strip(".")):
            err.append(f"ligne {i} : chemin du persist manquant")
        elif src == "persist" and any(SECRET.match(s) for s in l["chemin"].split(".")):
            err.append(f"ligne {i} : clé sensible refusée")
        elif src == "libre" and (not isinstance(l.get("texte"), str) or len(l["texte"]) > 120):
            err.append(f"ligne {i} : texte libre de 120 caractères au plus")
        elif src not in ("standard", "persist", "libre"):
            err.append(f"ligne {i} : source inconnue {src!r}")
        for cle, nom in (("avant", "avant"), ("apres", "après")):     # colles a la valeur (unite, prefixe)
            v = l.get(cle, "")
            if not isinstance(v, str) or len(v) > 20 or "\n" in v or "\r" in v:
                err.append(f"ligne {i} : texte {nom} la valeur de 20 caractères au plus, sur une ligne")
    sep = reglage.get("separateur", " : ")
    if not isinstance(sep, str) or len(sep) > 5:
        err.append("séparateur de 5 caractères au plus")
    if reglage.get("entre_lignes", "\n") not in ENTRE_LIGNES:
        err.append("entre les lignes : saut de ligne, « · » ou « | »")
    style = reglage.get("style") or {}
    if not isinstance(style, dict):
        err.append("style : objet attendu")
        style = {}
    if style.get("points", "square") not in POINTS:
        err.append(f"forme des points inconnue {style.get('points')!r}")
    if style.get("coins", "square") not in COINS:
        err.append(f"forme des coins inconnue {style.get('coins')!r}")
    for cle in ("couleur", "fond"):
        if cle in style and not (isinstance(style[cle], str) and COULEUR.match(style[cle])):
            err.append(f"{cle} : couleur #rrvvbb attendue")
    taille = reglage.get("taille_mm", 25)
    if isinstance(taille, bool) or not isinstance(taille, (int, float)) or not 10 <= taille <= 100:
        err.append("taille de 10 à 100 mm")
    if not isinstance(reglage.get("petit_nom", False), bool):
        err.append("petit nom sous le code : vrai ou faux")
    if reglage.get("contenu", "texte") not in ("texte", "lien"):
        err.append("contenu du QR code : « texte » ou « lien »")
    if style.get("image") is not None:
        try:
            _nom_image(style["image"])
            if racine is not None:
                image_data_uri(racine, style["image"])
        except ValueError as e:
            err.append(str(e))
    return err


# --- image ------------------------------------------------------------------------------------------------------------

def _nom_image(nom):
    if not isinstance(nom, str) or "/" in nom or "\\" in nom or nom.startswith(".") or Path(nom).suffix.lower() not in TYPES_IMAGE:
        raise ValueError(f"image refusée {nom!r} : nom de fichier PNG, JPEG ou SVG du dossier images attendu")
    return nom


def image_data_uri(racine, nom):
    """data URI de `outils_docs/etiquettes_qr/images/<nom>` ; ValueError si type, contenu ou taille refuses."""
    chemin = Path(racine) / DOSSIER / "images" / _nom_image(nom)
    try:
        octets = chemin.read_bytes()
    except OSError:
        raise ValueError(f"image introuvable : {nom}") from None
    type_ = TYPES_IMAGE[chemin.suffix.lower()]
    debut = octets[:512].lower()
    bon = {"image/png": octets.startswith(b"\x89PNG\r\n\x1a\n"), "image/jpeg": octets.startswith(b"\xff\xd8\xff"),
           "image/svg+xml": b"<svg" in debut and b"<script" not in octets.lower() and not re.search(rb"\son\w+\s*=", octets.lower())}
    if not bon[type_]:
        raise ValueError(f"image refusée {nom} : le contenu n'est pas un {type_} sûr")
    uri = f"data:{type_};base64,{base64.b64encode(octets).decode('ascii')}"
    if len(uri) > IMAGE_MAX:
        raise ValueError(f"image trop lourde {nom} : {len(uri)} octets en data URI, {IMAGE_MAX} au plus")
    return uri


# --- champs et persist ------------------------------------------------------------------------------------------------

def champs_de(env, serveur, ip):
    """Champs standards d'une carte ; None = introuvable."""
    mqtt = serveur.get("mqtt") if isinstance(serveur.get("mqtt"), dict) else {}
    rex = serveur.get("rangeExtender") if isinstance(serveur.get("rangeExtender"), dict) else {}
    ap = rex.get("AP") if isinstance(rex.get("AP"), dict) else {}
    code = lieux.lieu(env)
    return {"hostname": str(serveur.get("hostname") or "") or None, "ip": ip or None,
            "topic": str(mqtt.get("topic") or "") or None, "env": env, "puce": lieux.puce(env),
            "lieu": dict(lieux.LIEUX).get(code or "", code),
            # nom du reseau Wi-Fi diffuse par la carte (« ...-GATEWAY »), seulement si son range extender est actif
            "range_extender": (str(ap.get("SSID") or "") or None) if str(rex.get("activation", "")).upper() == "ON" else None}


def persist_de(racine, env):
    chemin = build_envs.persist_carte(racine, env)
    try:
        return json.loads(chemin.read_text(encoding="utf-8")) if chemin else {}
    except (OSError, ValueError):
        return {}


def serveur_de_config(chemin):
    """Hostname et topic d'un `config_decodee.json` (decode-config, cartes sans Berry : ESP8266), sous la forme du bloc
    `serveur` d'un persist ; {} si absent ou illisible. Seules ces deux cles sont lues : les mots de passe de ce fichier
    (`sta_pwd`, `mqtt_pwd`...) echappent au motif SECRET, son arborescence n'est donc jamais proposee."""
    try:
        d = json.loads(Path(chemin).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {"hostname": d.get("hostname"), "mqtt": {"topic": d.get("mqtt_topic")}} if isinstance(d, dict) else {}


# shortcut: lu une fois par lancement de l'outil ; un origin change pendant qu'il tourne demande de le relancer
@functools.lru_cache(maxsize=None)
def _url_depot(racine):
    try:
        url = subprocess.run(["git", "-C", racine, "config", "--get", "remote.origin.url"], capture_output=True,
                             text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    # proprietaire et depot seulement : l'URL brute peut porter un jeton (https://jeton@github.com/...)
    m = re.match(r"^(?:https://(?:[^@/]*@)?github\.com/|git@github\.com:|ssh://git@github\.com/)([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", url)
    return f"https://{m.group(1).lower()}.github.io/{m.group(2)}/" if m else None


def url_depot(racine):
    """Racine GitHub Pages du depot (`https://<proprietaire>.github.io/<depot>/`), None si origin n'est pas sur GitHub."""
    return _url_depot(str(Path(racine).resolve()))


def url_fiche(racine, env):
    """Adresse publique de la fiche d'une carte (plan A10) ; ValueError si le depot n'est pas sur GitHub."""
    base = url_depot(racine)
    if not base:
        raise ValueError("adresse de la fiche introuvable : le remote origin du dépôt n'est pas sur GitHub")
    return f"{base}{_env_valide(env)}.html"


def champs_standards(racine, env, envs=None):
    """Champs lus dans le depot : persist (ou `config_decodee.json` d'une carte sans persist), `user_config_override.h`,
    maitre du range extender ; ValueError si l'env n'est pas une carte du cenv. `envs` : liste de `build_envs.liste_envs`
    deja lue (elle coute plusieurs secondes)."""
    e = next((x for x in (envs or build_envs.liste_envs(racine)) if x.nom == _env_valide(env)), None)
    if e is None or e.famille != "cartes":
        raise ValueError(f"carte inconnue : {env}")
    chemin = build_envs.persist_carte(racine, env)
    if chemin:
        serveur = lieux._serveur(chemin)
    else:
        dossier = fichiers_berry_etat.dossier_carte(env)
        serveur = serveur_de_config(Path(racine) / dossier / "config_decodee.json") if dossier else {}
    # base GitHub Pages, hors CHAMPS (jamais proposee comme ligne) : lue par resout_avec en mode lien
    return {**champs_de(env, serveur, e.ip), "url_depot": url_depot(racine)}


def _valeurs_secretes(obj, acc, sous_secret=False):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _valeurs_secretes(v, acc, sous_secret or bool(SECRET.match(str(k))))
    elif isinstance(obj, list):
        for v in obj:
            _valeurs_secretes(v, acc, sous_secret)
    elif sous_secret and obj is not None and len(str(obj)) >= SECRET_MIN:
        acc.add(str(obj))
    return acc


def _sensible(valeur, secrets):
    s = str(valeur)
    return s.startswith("@secret:") or any(x in s for x in secrets)


def _type(v):
    return "booleen" if isinstance(v, bool) else "nombre" if isinstance(v, (int, float)) else "texte"


def arbre_persist(persist):
    """Feuilles scalaires proposees a l'utilisateur : [{"chemin", "valeur", "type"}], sans aucun secret."""
    secrets = _valeurs_secretes(persist, set())
    res = []

    def parcourt(obj, chemin):
        items = obj.items() if isinstance(obj, dict) else enumerate(obj) if isinstance(obj, list) else ()
        for k, v in items:
            if isinstance(obj, dict) and SECRET.match(str(k)):
                continue
            c = f"{chemin}.{k}" if chemin else str(k)
            if isinstance(v, (dict, list)):
                parcourt(v, c)
            elif v is not None and not _sensible(v, secrets):
                res.append({"chemin": c, "valeur": v, "type": _type(v)})

    parcourt(persist, "")
    return res


def valeur_persist(persist, chemin):
    """(valeur, None) ou (None, raison) ; refuse une cle secrete, une valeur sensible ou non scalaire."""
    morceaux = chemin.split(".")
    if any(SECRET.match(m) for m in morceaux):
        return None, "clé sensible refusée"
    v = persist
    for m in morceaux:
        if isinstance(v, dict) and m in v:
            v = v[m]
        elif isinstance(v, list) and m.isdigit() and int(m) < len(v):
            v = v[int(m)]
        else:
            return None, "clé absente du persist"
    if v is None or isinstance(v, (dict, list)):
        return None, "pas une valeur simple"
    if _sensible(v, _valeurs_secretes(persist, set())):
        return None, "valeur sensible refusée"
    return v, None


# --- texte lu par le telephone ----------------------------------------------------------------------------------------

def _texte_valeur(v):
    if isinstance(v, bool):
        return "oui" if v else "non"
    return " ".join(str(v).splitlines())       # une valeur ne coupe jamais une ligne du QR code


def resout_avec(reglage, champs, persist):
    """{"texte", "lignes": [{"source", "cle", "libelle", "valeur", "etat"}], "avertissements"} ; etat : ok | introuvable
    | refuse. Pure : `champs` de `champs_de`, `persist` deja lu."""
    sep = reglage.get("separateur", " : ")
    lignes, avert, textes = [], [], []
    for l in reglage.get("lignes") or []:
        src, lib = l.get("source"), l.get("libelle", "")
        cle = l.get("cle") if src == "standard" else l.get("chemin") if src == "persist" else None
        valeur, raison, etat = None, None, "ok"
        if src == "standard":
            valeur = champs.get(cle)
            raison = None if valeur is not None else "introuvable dans le dépôt"
        elif src == "persist":
            valeur, raison = valeur_persist(persist, cle or "")
        else:
            valeur = l.get("texte") or None
            raison = None if valeur else "texte vide"
        if raison:
            etat = "refuse" if "refusée" in raison else "introuvable"
            avert.append(f"Ligne « {lib or cle or src} » : {raison}, omise du QR code")
        else:
            valeur = _texte_valeur(valeur)
            if src != "libre":
                valeur = f"{l.get('avant', '')}{valeur}{l.get('apres', '')}"
            textes.append(f"{lib}{sep}{valeur}" if lib else valeur)
        lignes.append({"source": src, "cle": cle, "libelle": lib, "valeur": valeur, "etat": etat})
    texte = reglage.get("entre_lignes", "\n").join(textes)
    if reglage.get("contenu") == "lien":
        # mode lien (A10) : le QR code porte l'adresse de la fiche, pour TOUS les appelants (ecriture, suivi, build,
        # impression) ; sans adresse, une erreur, jamais un retour discret au texte
        if not champs.get("url_depot"):
            raise ValueError("mode lien : adresse de la fiche introuvable (remote origin du dépôt hors GitHub)")
        texte = f"{champs['url_depot']}{_env_valide(champs['env'])}.html"
    return {"texte": texte, "lignes": lignes, "avertissements": avert}


def resout(racine, env, reglage):
    return resout_avec(reglage, champs_standards(racine, env), persist_de(racine, env))


def fichier_carte(racine, reglage, resolu):
    """Contenu de `data/<lieu>/<carte>/qrcode.json` : texte deja resolu, style, image en data URI."""
    import etiquettes_qr_verdict as verdict

    style = dict(reglage.get("style") or {})
    nom = style.pop("image", None)
    image = image_data_uri(racine, nom) if nom else None
    ip = next((l["valeur"] for l in resolu["lignes"]
               if l["source"] == "standard" and l["cle"] == "ip" and l["etat"] == "ok"), None)
    correction = verdict.correction(bool(image))
    # modules : la page /qrcode de la carte en tire la marge de 4 modules (et la sonde compare au QR code dessine) ;
    # entre_lignes : la page affiche le texte sous le QR code une ligne par champ (le QR code, lui, garde le separateur)
    return {"version": 1, "texte": resolu["texte"], "style": style, "image": image, "correction": correction,
            "modules": verdict.verdict(resolu["texte"], 25, correction)["modules"], "ip_inscrite": ip,
            "entre_lignes": reglage.get("entre_lignes", "\n")}


def empreinte(texte):
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()
