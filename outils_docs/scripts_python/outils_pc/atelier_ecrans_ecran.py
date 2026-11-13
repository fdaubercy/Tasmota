"""Changement d'ecran d'une carte dans l'atelier des ecrans (plan atelier-ecrans A8, spec § 5.6, decision 4).

`met_a_echelle` : la disposition passe au rapport des resolutions (positions, tailles, rayons), chaque police ramenee a
la taille compilee la plus proche (taille libre d'une .ttf : arrondie), et signale cible tactile sous 40 px, texte qui
deborde, objet hors ecran. `changement` : le `display.ini` de l'env est repris de celui d'un env qui porte deja l'ecran
(display.ini relus), les broches de l'ecran (ligne :H d'un ecran RGB) sont confrontees a celles du persist (conflit = refus
motive), avertissement si l'ecran est integre a sa carte (bus RGB) ou si la base de l'env differe de celle de l'env qui
porte l'ecran. L'ecriture passe par atelier_ecrans_ecriture.ecrit (meme transaction que les trois fichiers generes).
shortcut: broches d'un ecran SPI/I2C (`*` : modele Tasmota) non controlees, signalees ; base de l'env jamais modifiee.
"""
import copy
import json
import re
from pathlib import Path

import assistant_persist_elements as ape
import atelier_ecrans_catalogue as cat
import atelier_ecrans_description as aed
import atelier_ecrans_ecriture as aee
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi

CIBLE_TACTILE = 40
ECHELLE_ATTRS = re.compile(r"(radius|border_width|arc_width|pad_\w+)\d*")


def _proche(tailles, v):
    return min(tailles, key=lambda t: (abs(t - v), t))


def police_echelle(v, r, catalogue):
    """Ecriture de police mise a l'echelle `r` : taille compilee la plus proche, ou arrondie pour une taille libre."""
    polices = {p["nom"]: p for p in catalogue["polices"]}
    if isinstance(v, int) and not isinstance(v, bool):
        return _proche(polices["robotocondensed"]["tailles"], v * r)
    if isinstance(v, str):
        m = aed.POLICE_TTF.fullmatch(v)
        if m:
            p = next((p for p in catalogue["polices"] if p.get("fichier") == m.group(1)), None)
            n = int(m.group(2)) * r
            t = max(6, round(n)) if p is None or p.get("taille_libre") else _proche(p["tailles"], n)
            return f"A:sd/polices/{m.group(1)}-{t}"
        m = aed.POLICE_FIRMWARE.fullmatch(v)
        if m:
            return f"{m.group(1)}-{_proche(polices[m.group(1)]['tailles'], int(m.group(2)) * r)}"
    return v


def _taille(v):
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    m = re.search(r"-(\d+)$", v) if isinstance(v, str) else None
    return int(m.group(1)) if m else 16


def met_a_echelle(desc, cible, catalogue):
    """(description sur l'ecran `cible`, avertissements)."""
    ecrans = catalogue["ecrans"]
    src, dst = ecrans.get(desc.get("ecran")), ecrans.get(cible)
    if dst is None:
        raise ValueError(f"ecran inconnu du catalogue : {cible!r}")
    if src is None:
        raise ValueError(f"ecran de la description inconnu du catalogue ({desc.get('ecran')!r}) : mise a l'echelle impossible")
    L, H = dst["largeur"], dst["hauteur"]
    rx, ry = L / src["largeur"], H / src["hauteur"]
    rf = min(rx, ry)
    d, av = copy.deepcopy(desc), []
    d["ecran"] = cible
    for o in d.get("objets", []):
        qui = f"objet {o.get('id')} ({o.get('type')}, page {o.get('page')})"
        if o.get("type") == "brut":
            av.append(f"{qui} : ligne brute du pages.jsonl, gardee telle quelle (non mise a l'echelle)")
            continue
        o["x"], o["y"] = round(o["x"] * rx), round(o["y"] * ry)
        o["l"], o["h"] = max(1, round(o["l"] * rx)), max(1, round(o["h"] * ry))
        if o["x"] + o["l"] > L or o["y"] + o["h"] > H:
            av.append(f"{qui} : hors de l'ecran apres mise a l'echelle, ramene dedans")
            o["l"], o["h"] = min(o["l"], L), min(o["h"], H)
            o["x"], o["y"] = min(o["x"], L - o["l"]), min(o["y"], H - o["h"])
        for attrs in (o.get("attributs") or {}, o.get("actif") or {}):
            for k, v in list(attrs.items()):
                if ECHELLE_ATTRS.fullmatch(k) and isinstance(v, int) and not isinstance(v, bool):
                    attrs[k] = round(v * rf)
                elif k == "text_font":
                    attrs[k] = police_echelle(v, rf, catalogue)
        a = o.get("attributs") or {}
        if o.get("toucher") and min(o["l"], o["h"]) < CIBLE_TACTILE:
            av.append(f"{qui} : cible tactile de {min(o['l'], o['h'])} px (moins de {CIBLE_TACTILE})")
        texte = a.get("text")
        if isinstance(texte, str) and texte and len(texte) * _taille(a.get("text_font")) * 0.5 > o["l"]:
            av.append(f"{qui} : le texte « {texte[:30]} » deborde probablement ({o['l']} px de large)")
    return d, av


def broches_ecran(ini):
    """(broches de la ligne :H d'un ecran RGB, bus) ; ([], bus) si les broches viennent du modele Tasmota (`*`).
    :H,<pilote>,l,h,bits,RGB puis DE, VSYNC, HSYNC, PCLK, retroeclairage, 16 broches de donnees, frequence : les 21
    champs apres le bus sont des broches, le dernier n'en est pas une (uDisplay.cpp, branche "RGB" du parseur)."""
    ligne = next((l for l in ini.splitlines() if l.startswith(":H,")), "")
    champs = ligne.split(",")
    bus = champs[5] if len(champs) > 5 else ""
    if bus != "RGB":
        return [], bus
    return [int(c) for c in champs[6:6 + 5 + 16] if re.fullmatch(r"\d+", c.strip())], bus


def broches_persist(persist):
    """{broche: usage} : drivers actifs (assistant_persist_elements) et toute cle pin/gpio entiere d'un bloc actif."""
    res = {p: lib for lib, p in ape.broches_drivers(persist).items()}

    def parcourt(n, chemin):
        if isinstance(n, dict):
            if n.get("activation") == "OFF":
                return
            for k, v in n.items():
                if k.lower() in ("pin", "gpio", "broche") and isinstance(v, int) and not isinstance(v, bool) and v >= 0:
                    res.setdefault(v, chemin or k)
                else:
                    parcourt(v, f"{chemin}.{k}" if chemin else k)
        elif isinstance(n, list):
            for i, v in enumerate(n):
                parcourt(v, f"{chemin}[{i}]")
    parcourt(persist, "")
    return res


def _base(ini, env):
    s = ini.definie_dans(env, "extends")
    m = ini.sections[s]["extends"].morceaux if s else []
    return m[0][1].strip() if m else None


def changement(racine, env, cible, desc):
    """{"description" (a l'echelle), "avertissements", "refus", "fichiers", "empreinte", "extra"} sans rien ecrire."""
    racine, catalogue = Path(racine), cat.charge(racine)
    dst = catalogue["ecrans"].get(cible)
    if dst is None:
        raise ValueError(f"ecran inconnu du catalogue : {cible!r}")
    if not isinstance(desc, dict):
        raise ValueError("description : objet attendu")
    src_desc = dict(desc, ecran=desc.get("ecran") or cat.ecrans_des_envs(racine).get(env))
    sans_ecran = src_desc["ecran"] is None       # carte sans ecran : rien a mettre a l'echelle
    erreurs = aee.erreurs(dict(src_desc, ecran=cible) if sans_ecran else src_desc, catalogue)
    if erreurs:                                  # met_a_echelle suppose une description bien formee
        raise ValueError("description refusee : " + " ; ".join(erreurs[:5]))
    nouvelle, av = (dict(copy.deepcopy(desc), ecran=cible), []) if sans_ecran else met_a_echelle(src_desc, cible, catalogue)
    refus = []
    # env qui porte l'ecran AUJOURD'HUI (display.ini relus) : le chemin du catalogue a pu changer d'ecran depuis
    porteurs = [e for e, k in cat.ecrans_des_envs(racine).items() if k == cible and e != env]
    if porteurs:
        ini = (racine / fbe.dossier_carte(porteurs[0]) / "display.ini").read_bytes()
    elif dst.get("source") in ("perso", "amont"):             # ecran de la bibliotheque ou de tasmota/displaydesc
        ini = (racine / dst["display_ini"]).read_bytes()
        av.append(f"display.ini pris dans {dst['display_ini']} ("
                  + ("bibliotheque personnelle" if dst["source"] == "perso" else "description fournie par Tasmota, jamais "
                     "essayee sur une carte du depot") + ") : base de l'env (LVGL, tactile) a verifier")
    else:
        raise ValueError(f"aucune autre carte ne porte l'ecran {cible} : display.ini introuvable")
    broches, bus = broches_ecran(ini.decode("utf-8", errors="replace"))
    if bus == "RGB":
        av.insert(0, "ecran RGB : il est integre a sa carte (ex. Waveshare ESP32-S3-Touch-LCD-7B) et ne se branche pas sur "
                     "une autre carte ; l'env devrait etre cette carte")
    else:
        av.append(f"bus {bus or '?'} : broches de l'ecran prises au modele Tasmota de la carte, non controlees ici")
    dossier = fbe.dossier_carte(env)
    try:
        persist = json.loads((racine / dossier / "_persist.json").read_text(encoding="utf-8"))
        prises = broches_persist(persist)
        for b in broches:
            if b in prises:
                refus.append(f"broche GPIO{b} de l'ecran deja prise par le persist ({prises[b]})")
    except (OSError, ValueError) as e:
        av.append(f"persist de la carte illisible, broches non controlees : {type(e).__name__}")
    fini = fbi.lit_sections(racine)
    b_env, b_autre = _base(fini, env), _base(fini, porteurs[0]) if porteurs else None
    if porteurs and b_env != b_autre:
        av.append(f"base de l'env : {b_env} ; celle de {porteurs[0]}, qui porte cet ecran : {b_autre} "
                  "(pilote, LVGL, tactile) ; a verifier, non modifiee")
    extra = {f"{dossier}/display.ini": ini}
    p = aee.prevu(racine, env, nouvelle, extra)
    return {"description": nouvelle, "avertissements": av, "refus": refus, "fichiers": p["fichiers"],
            "empreinte": p["empreinte"], "extra": extra}


def change(racine, env, cible, desc, empreinte_lue, empreinte_description, builds_en_cours):
    """Ecrit display.ini, ecran.json, pages.jsonl et ecranLvgl.be en une transaction ; RuntimeError si refus."""
    c = changement(racine, env, cible, desc)
    if c["refus"]:
        raise RuntimeError("changement d'ecran refuse : " + " ; ".join(c["refus"]))
    r = aee.ecrit(racine, env, c["description"], empreinte_lue, empreinte_description, builds_en_cours,
                  extra=c["extra"], nature="atelier-ecrans-changement")
    r["avertissements"] = c["avertissements"]
    return r
