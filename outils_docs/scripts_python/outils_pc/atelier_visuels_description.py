"""Description `visuel.json` d'une carte (atelier des visuels, spec 2026-11-13 §6.2) : validateur et sources du persist.

Les cas de `outils_docs/schemas/cas_visuel.json` sont partages avec le lecteur Berry (banc de l'A3) : memes regles.
Persist lu en lecture seule ; toute cle de nom secret (assistant_persist_modele.SECRET) est ignoree.
"""

import json
from pathlib import Path

import assistant_persist_modele as apm
import fichiers_berry_etat as fbe

SEUIL_AVERT = 40 * 1024
SEUILS_REFUS = {"esp32": 60 * 1024, "autre": 200 * 1024}
TYPES_FOND = ("svg", "webp", "jpg")
TYPES_ELEMENT = ("voyant", "valeur", "liaison")
LIAISONS = ("modbus_serie", "modbus_esclave", "udp", "rgx", "wifi")
AVEC_SEUIL = ("modbus_serie", "modbus_esclave", "udp")      # rgx (etat ok) et wifi (up) n'ont pas d'age
REFRAICHISSEMENT_MIN = 2


def _nombre(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _entier(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _source(p, el, err):
    s = el.get("source")
    t = el["type"]
    if not isinstance(s, dict):
        err.append(f"{p} : source absente")
        return
    st = s.get("type")
    permis = {"voyant": ("relais", "mesure"), "valeur": ("mesure",), "liaison": LIAISONS}[t]
    if st not in permis:
        err.append(f"{p} : source de type {st!r} inconnue pour un {t}")
        return
    if st == "relais" and not (_entier(s.get("n")) and s["n"] >= 1):
        err.append(f"{p} : source.n absent ou invalide (entier >= 1)")
    if st == "mesure":
        ch = s.get("chemin")
        if not (isinstance(ch, list) and ch and all(isinstance(c, str) and c for c in ch)):
            err.append(f"{p} : source.chemin vide ou invalide")
        for cle in ("on", "on_min"):
            if cle in s and (t != "voyant" or (cle == "on_min" and not _nombre(s[cle]))):
                err.append(f"{p} : condition {cle} refusee ici")
    if st == "modbus_esclave" and not (_entier(s.get("id")) and s["id"] >= 1):
        err.append(f"{p} : source.id absent ou invalide (entier >= 1)")
    if st in ("udp", "rgx") and not (isinstance(s.get("mac"), str) and s["mac"]):
        err.append(f"{p} : source.mac absent")
    if "seuil_s" in s and not (_nombre(s["seuil_s"]) and s["seuil_s"] > 0):
        err.append(f"{p} : seuil_s doit etre un nombre positif")
    elif st in AVEC_SEUIL and "seuil_s" not in s:
        err.append(f"{p} : seuil_s absent")


def valide(desc, octets_fond, puce):
    """Erreurs (francais) de la description ; liste vide = valide. `octets_fond` : poids du fond, None s'il n'est pas connu."""
    if not isinstance(desc, dict):
        return ["description : objet attendu"]
    err = []
    if desc.get("version") != 1:
        err.append("version : 1 attendue")
    fond = desc.get("fond")
    larg = haut = 0
    if not isinstance(fond, dict) or fond.get("type") not in TYPES_FOND:
        err.append("fond.type : svg, webp ou jpg attendu")
    if isinstance(fond, dict):
        larg, haut = fond.get("largeur"), fond.get("hauteur")
        if not all(_entier(v) and v > 0 for v in (larg, haut)):
            err.append("fond : largeur et hauteur entieres positives attendues")
            larg = haut = 0
    if "rafraichissement" in desc:
        r = desc["rafraichissement"]
        if not _nombre(r) or r < REFRAICHISSEMENT_MIN:
            err.append(f"rafraichissement : nombre >= {REFRAICHISSEMENT_MIN} attendu")
    els = desc.get("elements")
    if not isinstance(els, list):
        err.append("elements : liste attendue")
        els = []
    ids = set()
    for i, el in enumerate(els):
        p = f"elements[{i}]"
        if not isinstance(el, dict):
            err.append(f"{p} : objet attendu")
            continue
        if not isinstance(el.get("id"), str) or not el["id"]:
            err.append(f"{p} : id absent")
        elif el["id"] in ids:
            err.append(f"{p} : id {el['id']!r} en double")
        else:
            ids.add(el["id"])
        if el.get("type") not in TYPES_ELEMENT:
            err.append(f"{p} : type {el.get('type')!r} inconnu")
            continue
        coords = ["x", "y"] + (["x2", "y2"] if el["type"] == "liaison" else [])
        for c in coords:
            v, maxi = el.get(c), (larg if c.startswith("x") else haut)
            if not _nombre(v):
                err.append(f"{p} : {c} absent")
            elif maxi and not 0 <= v <= maxi:
                err.append(f"{p} : {c} hors du fond (0 a {maxi})")
        _source(p, el, err)
    if octets_fond is not None:
        limite = SEUILS_REFUS["esp32" if puce == "ESP32" else "autre"]
        if octets_fond > limite:
            err.append(f"fond : {octets_fond} octets, au-dessus du seuil de {limite} pour cette puce")
    return err


def avertissement(octets_fond):
    """Texte d'avertissement (orange) si le fond depasse SEUIL_AVERT, sinon None."""
    if octets_fond is not None and octets_fond > SEUIL_AVERT:
        return f"fond de {octets_fond} octets : au-dessus de {SEUIL_AVERT}, a alleger si possible"
    return None


def _lit(chemin):
    try:
        return json.loads(Path(chemin).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def _utiles(obj):
    """Le dict sans ses cles secretes ({} si ce n'est pas un dict)."""
    return {k: v for k, v in obj.items() if not apm.SECRET.match(str(k))} if isinstance(obj, dict) else {}


def _actifs(groupe):
    """Entrees `activation == ON` d'un groupe du persist qui portent un id entier."""
    return [e for e in _utiles(groupe).values()
            if isinstance(e, dict) and e.get("activation") == "ON" and _entier(e.get("id"))]


def sources(racine, env):
    """Sources proposables pour la carte `env`, d'apres son persist et son discovery.json au depot."""
    res = {"relais": [], "mesures": [], "esclaves": [], "udp": [], "rgx": [], "periodeReleve": None, "telePeriod": None}
    try:
        dossier = fbe.dossier_carte(env)
    except ValueError:
        dossier = None
    base = Path(racine) / dossier if dossier else None
    d = _lit(base / "_persist.json") if base else None
    if isinstance(d, dict):
        tele = _utiles(d.get("diverses")).get("telePeriod")
        res["telePeriod"] = tele if _nombre(tele) else None
        for m in _utiles(d.get("modules")).values():
            env_ = _utiles(_utiles(m).get("environnement"))
            for r in _actifs(env_.get("relais")):
                res["relais"].append({"n": r["id"], "nom": str(r.get("nom", ""))})
            for groupe, prefixe in (("boutons", "Button"), ("interrupteurs", "Switch")):
                for e in _actifs(env_.get(groupe)):
                    res["mesures"].append({"chemin": [prefixe + str(e["id"])], "nom": str(e.get("nom", ""))})
        mb = _utiles(_utiles(d.get("drivers")).get("ModBus"))
        if _nombre(mb.get("periodeReleve")):
            res["periodeReleve"] = mb["periodeReleve"]
        envmb = _utiles(mb.get("environnement"))
        for fam in ("TasmotaSlaveModBus", "Conn16channels"):
            for e in _actifs(envmb.get(fam)):
                res["esclaves"].append({"id": e["id"], "nom": str(e.get("name", ""))})
    table = _lit(base / "discovery.json") if base else None
    for mac, entree in (table.items() if isinstance(table, dict) else []):
        if not isinstance(entree, dict):
            continue
        fiche = next((v for k, v in entree.items() if k.startswith("esclave") and isinstance(v, dict)), None)
        if fiche is None:
            continue
        cfg = entree.get("config")
        nom = str(fiche.get("nom") or (cfg.get("dn") if isinstance(cfg, dict) else "") or mac)
        # shortcut: rgx et udp viennent du meme fichier (le persist ne garde pas les clients du point d'acces), a separer si besoin
        res["udp"].append({"mac": mac, "nom": nom})
        res["rgx"].append({"mac": mac, "nom": nom})
    return res


def defauts_seuils(src):
    """Seuils par defaut de `seuil_s` (spec §6.2) : ModBus 3 x periodeReleve (30 s sinon), udp 2 x telePeriod."""
    modbus = 3 * src["periodeReleve"] if src.get("periodeReleve") else 30
    d = {"modbus_serie": modbus, "modbus_esclave": modbus}
    if src.get("telePeriod"):
        d["udp"] = 2 * src["telePeriod"]
    return d
