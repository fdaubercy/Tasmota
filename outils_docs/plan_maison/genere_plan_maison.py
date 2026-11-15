"""Genere plan_maison.html : cartes Tasmota posees dans les pieces de la maison (vue plan) et schema reseau (vue reseau).
Les liens sont DERIVES des data/<lieu>/<dossier>/_persist.json : `serveur.rangeExtender.ipMaitre` (qui est l'esclave de qui),
`drivers.ModBus.typeComm` (Serial = bus RS485, UDP = commande et push), `rangeExtender.id` (numero d'esclave),
`serveur.mqtt.hote` (broker). Aucun mot de passe n'est lu.
placement.json donne les pieces, le placement, et les exceptions (ip_cartes, etiquettes, liens_manuels, broker).
Usage : python outils_docs/plan_maison/genere_plan_maison.py"""
import html
import json
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
DATA = ICI.parents[1] / "data"
PUCES = {"tasmota32": "ESP32", "tasmota32s3": "ESP32-S3", "tasmota32p4": "ESP32-P4", "tasmota": "ESP8266"}
PUCE_COUL = {"ESP32": "#64748b", "ESP32-S3": "#7c3aed", "ESP32-P4": "#0f9d58", "ESP8266": "#b45309"}
CW, CH, GAPX, GAPY, PAD, TITRE = 168, 38, 22, 18, 10, 26
COUL_SERIE, COUL_UDP, COUL_MQTT = "#d9480f", "#1f6feb", "#2f9e44"
NOMS = {"serie": "ModBus RS485 (série)", "udp": "UDP (commande et push)"}


def lit(cle):
    """Ce que le persist dit de la carte ; valeurs neutres si le dossier n'a pas de persist (ESP8266)."""
    r = {"hote": "", "topic": "", "ip": "", "mb": False, "mb_id": None, "serie": False, "udp": False,
         "re": False, "re_id": None, "ip_maitre": "", "mqtt": False, "mqtt_hote": "", "persist": False, "ssids": [], "debit": "", "mode": ""}
    try:
        d = json.loads((DATA / cle / "_persist.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return r
    s = d.get("serveur") or (d.get("parametres") or {}).get("serveur") or {}
    dr = d.get("drivers") if isinstance(d.get("drivers"), dict) else {}
    mb = dr.get("ModBus") if isinstance(dr.get("ModBus"), dict) else {}
    tc = mb.get("typeComm") if isinstance(mb.get("typeComm"), dict) else {}
    rx = s.get("rangeExtender") if isinstance(s.get("rangeExtender"), dict) else {}
    mq = s.get("mqtt") if isinstance(s.get("mqtt"), dict) else {}
    wf = s.get("wifi") if isinstance(s.get("wifi"), dict) else {}
    ssids = [str((wf.get(k) or {}).get("nomReseauWifi") or "") if isinstance(wf.get(k), dict) else "" for k in ("reseau1", "reseau2")]
    ip = (s.get("IP") or {}).get("IPAddress", "") if isinstance(s.get("IP"), dict) else ""
    r.update(persist=True, hote=s.get("hostname") or "", topic=mq.get("topic") or "", ip="" if ip == "0.0.0.0" else ip,
             mb=mb.get("activation") == "ON", mb_id=mb.get("id"), serie=tc.get("Serial") == "ON", udp=tc.get("UDP") == "ON",
             re=rx.get("activation") == "ON", re_id=rx.get("id"), ip_maitre=rx.get("ipMaitre") or "",
             ssids=ssids, debit=str(mb.get("debit") or ""), mode=str(mb.get("mode") or ""), mqtt=mq.get("activation") == "ON", mqtt_hote=f"{mq.get('hote') or ''}:{mq.get('port') or ''}".rstrip(":"))
    return r


def derive(conf, infos):
    """Liens maitre -> esclave et roles. Retourne (liens, maitres, esclaves) ; avertit sur ce qu'elle ne sait pas trancher."""
    par_ip = {}
    for cle, i in infos.items():
        if i["ip"]:
            par_ip.setdefault(i["ip"], []).append(cle)
    forces = conf.get("ip_cartes", {})
    for ip, cles in par_ip.items():
        if len(cles) > 1 and ip not in forces:
            print(f"AVERTISSEMENT : IP {ip} portee par plusieurs cartes ({', '.join(cles)}) : a trancher dans ip_cartes", file=sys.stderr)
    liens, maitres, esclaves = [], set(), {}
    for cle, i in infos.items():
        if not (i["re"] and i["ip_maitre"] and i["ip_maitre"] != i["ip"]):
            continue
        cibles = [forces[i["ip_maitre"]]] if i["ip_maitre"] in forces else par_ip.get(i["ip_maitre"], [])
        if len(cibles) != 1 or cibles[0] not in infos:
            print(f"AVERTISSEMENT : maitre {i['ip_maitre']} de {cle} introuvable ou ambigu", file=sys.stderr)
            continue
        m = cibles[0]
        esclaves[cle] = i["re_id"]
        maitres.add(m)
        for t, ok in (("serie", i["serie"] and infos[m]["serie"]), ("udp", i["udp"] and infos[m]["udp"])):
            if ok:
                liens.append({"type": t, "de": m, "vers": cle, "etiquette": f"id {i['re_id']}"})
    for ln in conf.get("liens_manuels", []):
        liens.append({**ln, "etiquette": ln.get("etiquette", "")})
        maitres.add(ln["de"])
        esclaves.setdefault(ln["vers"], None)
    return liens, maitres, esclaves


def derive_wifi(conf, infos):
    """Rattachements Wi-Fi : [{kind: ap|re, rang: 0 principal / 1 secours, de, vers, ssid}] d'apres serveur.wifi.reseau1/reseau2.
    ap = appareil du placement.json (par SSID), re = Range Extender du maitre (SSID '<hote>-GATEWAY'). Les SSID inconnus (telephone) sont ignores.
    wifi_manuel[carte] = {principal, secours} (id d'appareil ou 're:<carte maitre>') corrige la deduction."""
    wc = conf.get("wifi", {})
    par_ssid = {s: k for k, a in wc.get("appareils", {}).items() for s in a.get("ssid", [])}
    par_hote = {}
    for cle, i in infos.items():
        if i["hote"]:
            par_hote.setdefault(i["hote"].upper(), []).append(cle)
    res = []
    for cle, i in infos.items():
        man = wc.get("wifi_manuel", {}).get(cle, {})
        for rang, ssid in enumerate(i["ssids"]):
            cible = man.get(("principal", "secours")[rang])
            if cible is None and ssid.upper().endswith("-GATEWAY"):
                h = ssid[:-8].upper()
                cs = [wc["re_hotes"][h]] if h in wc.get("re_hotes", {}) else par_hote.get(h, [])
                if len(cs) != 1:
                    print(f"AVERTISSEMENT : Range Extender {ssid} de {cle} introuvable ou ambigu", file=sys.stderr)
                    continue
                cible = "re:" + cs[0]
            elif cible is None:
                cible = par_ssid.get(ssid)
            if not cible:
                continue
            if cible.startswith("re:"):
                if cible[3:] not in infos or cible[3:] == cle:
                    print(f"AVERTISSEMENT : Range Extender {cible} de {cle} invalide", file=sys.stderr)
                    continue
                res.append({"kind": "re", "rang": rang, "de": cible[3:], "vers": cle, "ssid": ssid})
            elif cible in wc.get("appareils", {}):
                res.append({"kind": "ap", "rang": rang, "de": "ap:" + cible, "vers": cle, "ssid": ssid})
            else:
                print(f"AVERTISSEMENT : appareil Wi-Fi {cible} inconnu ({cle})", file=sys.stderr)
    return res


def adresse(cle, infos, maitre_de):
    """Page web d'une carte : son IP si le persist en donne une, sinon (esclave derriere le NAPT d'un maitre) <IP maitre>:<8080 + id - 1>
    comme build_envs.py::adresse_par_maitre ; "" si inconnue."""
    ok = lambda ip: bool(re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", ip or ""))
    i = infos[cle]
    if ok(i["ip"]):
        return f"http://{i['ip']}/"
    m = maitre_de.get(cle)
    if m and ok(infos[m]["ip"]) and isinstance(i["re_id"], int) and i["re_id"] > 0:
        return f"http://{infos[m]['ip']}:{8080 + i['re_id'] - 1}/"
    return ""


def adresse_debits():
    """URL de la carte d'acquisition des debits (placement.json > chauffage.acquisition) ; "" si inconnue. Cible FIXE, jamais fournie par un client."""
    conf = json.loads((ICI / "placement.json").read_text(encoding="utf-8"))
    cle = conf.get("chauffage", {}).get("acquisition", "")
    if cle not in conf["cartes"]:
        return ""
    infos = {c: lit(c) for c in conf["cartes"]}
    liens, _, _ = derive(conf, infos)
    return adresse(cle, infos, {ln["vers"]: ln["de"] for ln in liens})


def triangle(x, y, dx, dy, t=8):
    """Pointe de fleche en (x, y) dirigee vers (dx, dy) (vecteur unitaire)."""
    px, py = -dy, dx
    return (f'<polygon points="{x:.0f},{y:.0f} {x - dx * t * 1.6 + px * t * .7:.0f},{y - dy * t * 1.6 + py * t * .7:.0f} '
            f'{x - dx * t * 1.6 - px * t * .7:.0f},{y - dy * t * 1.6 - py * t * .7:.0f}"/>')


def etiquette(pts, texte, lbl=None):
    """Texte au milieu du plus long segment (halo de la couleur du fond) ; rien si aucun segment n'a 20 px."""
    if lbl and texte:
        return f'<text class="lbl lg" x="{lbl[0]:.0f}" y="{lbl[1] + 3.5:.0f}">{html.escape(texte)}</text>'
    seg = max(zip(pts, pts[1:]), key=lambda s: abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1]))
    (a, b), (c, d) = seg
    if abs(a - c) + abs(b - d) < 20 or not texte:
        return ""
    return f'<text class="lbl" x="{(a + c) / 2:.0f}" y="{(b + d) / 2 + 3.5:.0f}" text-anchor="middle">{html.escape(texte)}</text>'


def svg_lien(ln, pts, liens, lbl=None, texte=None):
    """(ordre de dessin, svg) d'un lien le long de la polyligne pts ; le pointille clair passe au-dessus du trait plein."""
    d = "M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    n = max(1.0, ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** .5)
    pointe = triangle(x2, y2, (x2 - x1) / n, (y2 - y1) / n)
    (u1, v1), (u2, v2) = pts[1], pts[0]
    m = max(1.0, ((u2 - u1) ** 2 + (v2 - v1) ** 2) ** .5)
    retour = triangle(u2, v2, (u2 - u1) / m, (v2 - v1) / m, 6)
    attr = f'data-de="{html.escape(ln["de"])}" data-vers="{html.escape(ln["vers"])}"'
    if ln["type"] == "serie":
        return 0, f'<g class="lien serie" data-type="serie" {attr}><path d="{d}"/>{pointe}{etiquette(pts, ln["etiquette"] if texte is None else texte, lbl)}</g>'
    if any(k["type"] == "serie" and k["de"] == ln["de"] and k["vers"] == ln["vers"] for k in liens):
        return 2, f'<g class="lien udp sur-serie" data-type="udp" {attr}><path d="{d}"/>{retour}</g>'
    return 1, f'<g class="lien udp seul" data-type="udp" {attr}><path d="{d}"/>{pointe}{retour}{etiquette(pts, ln["etiquette"] if texte is None else texte, lbl)}</g>'


def colonne(a, b, salles):
    """Liens entre deux pieces empilees : tronc dans le couloir entre la 1re et la 2e colonne de pastilles, branches a angle droit.
    Retourne (points, position de l'etiquette) ou None si la geometrie ne s'y prete pas (pieces non alignees, 3e colonne)."""
    if a["piece"] == b["piece"] or a["col"] > 1 or b["col"] > 1:
        return None
    oa, ob = a["x"] - a["col"] * (CW + GAPX), b["x"] - b["col"] * (CW + GAPX)
    sa, sb = salles[a["piece"]], salles[b["piece"]]
    if abs(oa - ob) > 1 or not (sb["bas"] <= sa["haut"] or sa["bas"] <= sb["haut"]):
        return None
    xt = oa + CW + GAPX / 2
    ym = (sa["haut"] + sb["bas"]) / 2 if sb["bas"] <= sa["haut"] else (sa["bas"] + sb["haut"]) / 2
    pts = [(a["x"] + (CW if a["col"] == 0 else 0), a["cy"]), (xt, a["cy"]), (xt, b["cy"]), (b["x"] + (CW if b["col"] == 0 else 0), b["cy"])]
    return [p for k, p in enumerate(pts) if k == 0 or p != pts[k - 1]], (xt + 6, ym)


def route(a, b, salles):
    """Points d'une polyligne orthogonale du bord de la pastille a au bord de b, sans traverser de pastille quand c'est possible."""
    if a["piece"] == b["piece"]:
        dc, dr = b["col"] - a["col"], b["row"] - a["row"]
        if dr == 0 and abs(dc) == 1:
            return [(a["x"] + (CW if dc > 0 else 0), a["cy"]), (b["x"] + (0 if dc > 0 else CW), b["cy"])]
        if dc == 0 and abs(dr) == 1:
            return [(a["cx"], a["y"] + (CH if dr > 0 else 0)), (b["cx"], b["y"] + (0 if dr > 0 else CH))]
        if dc == 0:                                   # meme colonne, pastilles non voisines : contournement par la marge gauche
            xm = a["x"] - PAD / 2
            return [(a["x"], a["cy"]), (xm, a["cy"]), (xm, b["cy"]), (b["x"], b["cy"])]
        sens = 1 if dc > 0 else -1                    # colonnes et rangees differentes : coude dans le couloir entre colonnes
        xt = a["x"] + (CW + GAPX / 2 if sens > 0 else -GAPX / 2)
        return [(a["x"] + (CW if sens > 0 else 0), a["cy"]), (xt, a["cy"]), (xt, b["cy"]), (b["x"] + (0 if sens > 0 else CW), b["cy"])]
    sa, sb = salles[a["piece"]], salles[b["piece"]]
    if abs(a["cx"] - b["cx"]) > 600 or not (sb["bas"] <= sa["haut"] or sa["bas"] <= sb["haut"]):
        return [(a["cx"], a["cy"]), (b["cx"], b["cy"])]            # hors empilement vertical : trait droit
    haut = sb["bas"] <= sa["haut"]                                  # b est au-dessus de a
    ya, yb = (a["y"], b["y"] + CH) if haut else (a["y"] + CH, b["y"])
    ym = (sa["haut"] + sb["bas"]) / 2 if haut else (sa["bas"] + sb["haut"]) / 2
    pts = [(a["cx"], ya), (a["cx"], ym), (b["cx"], ym), (b["cx"], yb)]
    return [p for k, p in enumerate(pts) if k == 0 or p != pts[k - 1]]


def svg_carte(cle, x, y, m):
    """Pastille d'une carte en (x, y) ; m = meta calculee une fois pour les deux vues."""
    deco = ""
    if m["badge"] == "etoile":
        deco = f'<text class="etoile" x="{x + CW - 20}" y="{y + 17}">★</text>'
    elif m["badge"] == "vide":
        deco = f'<text class="etoile vide" x="{x + CW - 20}" y="{y + 17}">☆</text>'
    elif m["badge"] == "id":
        deco = (f'<circle class="idb" cx="{x + CW - 14}" cy="{y + 14}" r="9"/>'
                f'<text class="idt" x="{x + CW - 14}" y="{y + 18}">{html.escape(str(m["id"]))}</text>')
    if m.get("re_n"):
        deco += f'<text class="re" x="{x + CW - 40}" y="{y + CH - 5}" text-anchor="end">📶 RE ×{m["re_n"]}</text>'
    etat = f'<circle class="etat" cx="{x + CW - 9}" cy="{y + CH - 8}" r="4"/>' if m["url"] else ""
    if m["url"]:
        etat += (f'<a class="lk" href="{html.escape(m["url"])}" target="_blank" rel="noopener" aria-label="Ouvrir la page web de la carte">'
                 f'<title>Ouvrir la page web de la carte</title><circle cx="{x + CW - 27}" cy="{y + CH - 8}" r="8"/>'
                 f'<path d="M{x + CW - 30},{y + CH - 5} L{x + CW - 24},{y + CH - 11} M{x + CW - 29},{y + CH - 11} H{x + CW - 24} V{y + CH - 6}"/></a>')
    url = f' data-url="{html.escape(m["url"])}"' if m["url"] else ""
    return (f'<g class="{m["cls"]}" data-id="{html.escape(cle)}"{url} tabindex="0"><rect x="{x}" y="{y}" width="{CW}" height="{CH}" rx="5"/>'
            f'<rect x="{x + 3}" y="{y + 6}" width="4" height="{CH - 12}" rx="2" fill="{m["coul"]}"/>'
            f'<text class="t1" x="{x + 13}" y="{y + 16}">{html.escape(m["libelle"])}</text>'
            f'<text class="t2" x="{x + 13}" y="{y + 30}">{html.escape(m["sous"])}</text>{deco}{etat}</g>')


def vue_reseau(conf, metas, liens, maitres, broker, brokers_hotes):
    """SVG du schema reseau : broker MQTT en haut, un groupe par maitre (esclaves dessous), cartes autonomes a droite."""
    ordre = list(conf["cartes"])
    esc = {mm: [] for mm in maitres}
    for ln in liens:
        if ln["vers"] not in esc.get(ln["de"], []):
            esc[ln["de"]].append(ln["vers"])
    groupes = [mm for mm in ordre if mm in maitres]
    en_groupe = set(groupes) | {s for v in esc.values() for s in v}
    seuls = [c for c in ordre if c not in en_groupe]
    out, pos = [], {}
    y0 = 150
    for gi, mm in enumerate(groupes):
        mx = 40 + gi * 220
        pos[mm] = (mx, y0)
        sl = esc[mm]
        if sl:
            h = len(sl) * (CH + GAPY) - GAPY
            out.append(f'<rect class="wifi" x="{mx + 14}" y="{y0 + CH + 8}" width="{CW + 20}" height="{h + 34}" rx="8"/>'
                       f'<text class="nompiece" x="{mx + 22}" y="{y0 + CH + 8 + h + 28}">Wi-Fi du maître (Range Extender)</text>')
        for k, s in enumerate(sl):
            pos[s] = (mx + 24, y0 + (k + 1) * (CH + GAPY) + 6)
    bx = 700
    for k, c in enumerate(seuls):
        pos[c] = (bx + (k % 2) * (CW + GAPX), y0 + (k // 2) * (CH + GAPY + 0))
    liens_svg = []
    for ln in liens:
        (mx, my), (sx, sy) = pos[ln["de"]], pos[ln["vers"]]
        pts = [(mx + 8, my + CH), (mx + 8, sy + CH / 2), (sx, sy + CH / 2)]
        liens_svg.append(svg_lien(ln, pts, liens))
    # MQTT : un bus, des descentes par carte de tete (les esclaves passent par le Wi-Fi du maitre)
    xb = bx + CW + GAPX / 2
    tetes = [mm for mm in groupes] + seuls
    brx = 520
    bus = [f"M{brx},70 L{brx},110"]
    xs = [pos[mm][0] + CW / 2 for mm in groupes] + [xb]
    bus.append(f"M{min(xs):.0f},110 L{max(xs):.0f},110")
    lasty = max(pos[c][1] + CH / 2 for c in seuls) if seuls else 110
    bus.append(f"M{xb:.0f},110 L{xb:.0f},{lasty:.0f}")
    mq = [f'<path class="mqttbus" data-type="mqtt" d="{" ".join(bus)}"/>']
    for c in tetes:
        x, y = pos[c]
        if c in groupes:
            d = f"M{x + CW / 2:.0f},110 L{x + CW / 2:.0f},{y}"
        else:
            d = f"M{xb:.0f},{y + CH / 2:.0f} L{(x + (CW if x == bx else 0)):.0f},{y + CH / 2:.0f}"
        if metas[c]["mqtt"]:
            mq.append(f'<path class="lien mqtt" data-type="mqtt" data-de="broker" data-vers="{html.escape(c)}" d="{d}"/>')
    hote = brokers_hotes[0] if brokers_hotes else "?"
    nom = html.escape(broker.get("nom", "Broker MQTT"))
    nodes = (f'<g class="broker"><rect x="{brx - 130}" y="20" width="260" height="50" rx="8"/>'
             f'<text class="t1" x="{brx}" y="42" text-anchor="middle">Broker MQTT · {nom}</text>'
             f'<text class="t2" x="{brx}" y="59" text-anchor="middle">{html.escape(hote)}</text></g>')
    cartes = "".join(svg_carte(c, x, y, metas[c]) for c, (x, y) in pos.items())
    liens_svg = "".join(s for _, s in sorted(liens_svg, key=lambda t: t[0]))
    return (f'<svg class="reseau" viewBox="0 0 1120 480" role="img" aria-label="Schéma réseau">{"".join(out)}{"".join(mq)}{liens_svg}{nodes}{cartes}</svg>')


def construit():
    """(page HTML, resume) ; ne touche a aucun fichier. Les avertissements vont sur stderr."""
    conf = json.loads((ICI / "placement.json").read_text(encoding="utf-8"))
    sur_disque = {f"{p.parent.name}/{p.name}" for p in DATA.glob("*/*/") if p.is_dir() and "sauvegarde" not in p.name
                  and not p.parent.name.startswith(".") and p.parent.name not in ("sd", "fs", "json", "extensions")}
    for c in sorted(sur_disque - set(conf["cartes"])):
        print("AVERTISSEMENT : carte sans placement :", c, file=sys.stderr)
    for c in sorted(set(conf["cartes"]) - sur_disque):
        print("AVERTISSEMENT : placement d'une carte absente de data/ :", c, file=sys.stderr)
    infos = {cle: lit(cle) for cle in conf["cartes"]}
    liens, maitres, esclaves = derive(conf, infos)
    hotes = sorted({i["mqtt_hote"] for i in infos.values() if i["mqtt"] and i["mqtt_hote"]})
    if len(hotes) > 1:
        print("AVERTISSEMENT : plusieurs brokers MQTT dans les persist :", ", ".join(hotes), file=sys.stderr)

    wifi = derive_wifi(conf, infos)
    relie = {c for ln in liens for c in (ln["de"], ln["vers"])}
    maitre_de = {ln["vers"]: ln["de"] for ln in liens}
    metas = {}
    for cle, c in conf["cartes"].items():
        i = infos[cle]
        puce = PUCES.get(cle.split("/")[1].split("-")[0], "?")
        if cle in maitres:
            role, badge = "maître", "etoile"
        elif cle in esclaves:
            role, badge = (f"esclave id {esclaves[cle]}" if esclaves[cle] is not None else "esclave"), ("id" if esclaves[cle] is not None else "")
        elif i["mb"] and i["mb_id"] == 0:
            role, badge = "maître (sans esclave)", "vide"
        else:
            role, badge = "", ""
        etiq = conf.get("etiquettes", {}).get(cle, "")
        autonome = cle not in relie and not role
        sous = puce + (" · autonome" if autonome and not etiq else "") + (f" · {etiq.split(' (')[0]}" if etiq else "")
        metas[cle] = {"libelle": c["libelle"], "sous": sous, "badge": badge, "id": esclaves.get(cle), "role": role, "puce": puce,
                      "coul": PUCE_COUL.get(puce, "#888"), "etiq": etiq, "mqtt": i["mqtt"], "url": adresse(cle, infos, maitre_de),
                      "re_n": len({ln["vers"] for ln in liens if ln["de"] == cle}), "cls": "carte" + (" maitre" if badge == "etoile" else "") + (" autonome" if autonome else "")}

    pieces, ordre, pos, salles, out_p = {}, {}, {}, {}, []
    for niv in conf["niveaux"]:
        for p in niv["pieces"]:
            pieces[p["id"]] = (niv, p)
        if niv.get("titre"):
            out_p.append(f'<text class="titreetage" x="{niv["x"]}" y="{niv["y"] - 6}">{html.escape(niv["titre"])}</text>')
    for cle, c in conf["cartes"].items():
        ordre.setdefault(c["piece"], []).append(cle)
    for pid, (niv, p) in pieces.items():
        x0, y0, h = niv["x"] + p["x"], niv["y"], niv["h"]
        salles[pid] = {"haut": y0, "bas": y0 + h}
        cls = "piece tirets" if p.get("tirets") else "piece"
        out_p.append(f'<g><rect class="{cls}" x="{x0}" y="{y0}" width="{p["w"]}" height="{h}" rx="6"/>'
                     f'<text class="nompiece" x="{x0 + PAD}" y="{y0 + 17}">{html.escape(p["nom"])}</text></g>')
        cols = max(1, (p["w"] - 2 * PAD + GAPX) // (CW + GAPX))
        lignes = -(-len(ordre.get(pid, [])) // cols)
        haut_bloc = lignes * (CH + GAPY) - GAPY
        if TITRE + haut_bloc + PAD > h and ordre.get(pid):
            print("AVERTISSEMENT : la piece deborde :", p["nom"], file=sys.stderr)
        ytop = y0 + h - PAD - haut_bloc if p.get("ancrage") == "bas" else y0 + TITRE
        for k, cle in enumerate(ordre.get(pid, [])):
            col, row = k % cols, k // cols
            x, y = x0 + PAD + col * (CW + GAPX), ytop + row * (CH + GAPY)
            pos[cle] = {"piece": pid, "col": col, "row": row, "x": x, "y": y, "cx": x + CW / 2, "cy": y + CH / 2}

    out_l = []
    groupes_etiq = set()
    for ln in liens:
        if ln["de"] not in pos or ln["vers"] not in pos:
            print("AVERTISSEMENT : lien vers une carte non placee :", ln, file=sys.stderr)
            continue
        c = colonne(pos[ln["de"]], pos[ln["vers"]], salles)
        texte = None
        if c:        # une seule etiquette pour le tronc partage : « id 2 · id 4 »
            cle_g = (ln["de"], pos[ln["vers"]]["piece"], ln["type"])
            texte = "" if cle_g in groupes_etiq else " · ".join(k["etiquette"] for k in liens if k["type"] == ln["type"] and k["de"] == ln["de"]
                                                                  and k["vers"] in pos and pos[k["vers"]]["piece"] == cle_g[1])
            groupes_etiq.add(cle_g)
        out_l.append(svg_lien(ln, c[0] if c else route(pos[ln["de"]], pos[ln["vers"]], salles), liens, c[1] if c else None, texte))
    out_l = [s for _, s in sorted(out_l, key=lambda t: t[0])]
    out_c = [svg_carte(cle, p["x"], p["y"], metas[cle]) for cle, p in pos.items()]
    aps = conf.get("wifi", {}).get("appareils", {})
    app = {}
    for k, a in aps.items():
        niv, pc = pieces[a["piece"]]
        app[f"ap:{k}"] = (niv["x"] + pc["x"] + pc["w"] - 128, niv["y"] + 4, a)
    out_w = []
    for w in wifi:
        if w["vers"] not in pos or (w["de"] not in app and w["de"] not in pos):
            continue
        dest = pos[w["vers"]]
        dash = ' stroke-dasharray="7 5" opacity=".6"' if w["rang"] else ""
        if w["kind"] == "ap":
            ax, ay, a = app[w["de"]]
            tp = "wsec" if w["rang"] else "wap"
            out_w.append(f'<g class="lien wl{" off" if w["rang"] else ""}" data-type="{tp}" data-de="{w["de"]}" data-vers="{html.escape(w["vers"])}">'
                         f'<path d="M{ax + 59:.0f},{ay + 10:.0f} L{dest["cx"]:.0f},{dest["cy"]:.0f}" stroke="{a["coul"]}" stroke-width="2.2"{dash}/>'
                         f'<circle cx="{dest["cx"]:.0f}" cy="{dest["cy"]:.0f}" r="4.5" fill="{a["coul"]}"/></g>')
        else:
            d = "M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in route(pos[w["de"]], dest, salles))
            out_w.append(f'<g class="lien wl wre" data-type="wre" data-de="{html.escape(w["de"])}" data-vers="{html.escape(w["vers"])}">'
                         f'<path class="rail" d="{d}"{dash}/><path class="ame" d="{d}"/></g>')
    ch = conf.get("chauffage", {})
    out_ch, jch = [], {}
    if ch:
        for k, e in (("ch:pac", ch["pac"]), ("ch:nourrice", ch["nourrice"])):
            niv, pc = pieces[e["piece"]]
            jch[k] = (niv["x"] + pc["x"] + pc["w"] - (254 if e["piece"] in ("bureau", "cave") else 128), niv["y"] + 4, e)
        (px, py, _), (nx, ny, _) = jch["ch:pac"], jch["ch:nourrice"]
        out_ch.append(f'<g class="lien chl" data-de="ch:pac" data-vers="ch:nourrice"><path class="hyd" d="M{px + 59},{py + 10} L{nx + 59},{ny + 10}"/></g>')
        vus = {}
        for dep in ch.get("departs", []):
            for pid in dep["pieces"]:
                niv, pc = pieces[pid]
                k = vus.get(pid, 0)
                vus[pid] = k + 1
                ex, ey = niv["x"] + pc["x"] + pc["w"] / 2 + k * 30 - 15 * (vus[pid] > 1), niv["y"] + 12
                out_ch.append(f'<g class="lien chl" data-de="ch:nourrice" data-vers="{pid}"><path class="dep" d="M{nx + 59},{ny + 10} L{ex:.0f},{ey}"/>'
                              f'<circle cx="{ex:.0f}" cy="{ey}" r="9"/><text class="dn" x="{ex:.0f}" y="{ey + 3.5}" text-anchor="middle">{dep["debit"]}</text>'
                              f'<text class="dv" data-d="{dep["debit"]}" x="{ex + 13:.0f}" y="{ey + 4:.0f}"></text></g>')
        for k, (x, y, e) in jch.items():
            out_c.append(f'<g class="carte chn" data-id="{k}" tabindex="0"><rect x="{x}" y="{y}" width="118" height="20" rx="4"/>'
                         f'<text class="t2" x="{x + 59}" y="{y + 14}" text-anchor="middle" style="fill:var(--txt);font-weight:600">{html.escape("🔥 " + e["nom"])}</text></g>')
    for k, (x, y, a) in app.items():
        out_c.append(f'<g class="carte apn" data-id="{k}" tabindex="0"><rect x="{x}" y="{y}" width="118" height="20" rx="10" stroke="{a["coul"]}"/>'
                     f'<text class="t2" x="{x + 59}" y="{y + 14}" text-anchor="middle" style="fill:var(--txt);font-weight:600">'
                     f'{html.escape("📶 " + a["nom"])}</text></g>')

    fiches = {}
    for cle in pos:
        m, i = metas[cle], infos[cle]
        voisins = []
        for ln in liens:
            if cle in (ln["de"], ln["vers"]):
                autre = ln["vers"] if ln["de"] == cle else ln["de"]
                voisins.append(f'{NOMS[ln["type"]]} : {"vers" if ln["de"] == cle else "depuis"} {conf["cartes"][autre]["libelle"]} ({ln["etiquette"]})')
        fiches[cle] = {"libelle": m["libelle"], "dossier": "data/" + cle, "puce": m["puce"], "piece": pieces[conf["cartes"][cle]["piece"]][1]["nom"],
                       "hote": i["hote"], "topic": i["topic"], "ip": i["ip"] or "(DHCP ou derrière un maître)", "url": m["url"],
                       "role": m["role"] or "-", "mqtt": "oui" if i["mqtt"] else "non", "note": m["etiq"], "liens": voisins}
    for k, (x, y, a) in app.items():
        co = [w for w in wifi if w["de"] == k]
        fiches[k] = {"libelle": a["nom"], "dossier": "-", "puce": "Appareil Wi-Fi", "piece": pieces[a["piece"]][1]["nom"], "hote": "", "topic": "",
                     "ip": "-", "url": "", "role": "point d'accès Wi-Fi", "mqtt": "-",
                     "note": "SSID : " + (", ".join(a["ssid"]) or "aucun module identifié"),
                     "liens": [f'{"principal" if w["rang"] == 0 else "secours"} : {conf["cartes"][w["vers"]]["libelle"]}' for w in co]}
    for cle in pos:
        fiches[cle]["liens"] += [f'Wi-Fi {"principal" if w["rang"] == 0 else "secours"} : '
                                 + (aps[w["de"][3:]]["nom"] if w["kind"] == "ap" else f'Range Extender de {conf["cartes"][w["de"]]["libelle"]}')
                                 + f' ({w["ssid"]})' for w in wifi if w["vers"] == cle]
        fiches[cle]["liens"] += [f'Range Extender de cette carte : {conf["cartes"][w["vers"]]["libelle"]}'
                                 for w in wifi if w["kind"] == "re" and w["de"] == cle and w["rang"] == 0]
    for k, (x, y, e) in jch.items():
        acq = conf["cartes"].get(ch.get("acquisition", ""), {}).get("libelle", "")
        fiches[k] = {"libelle": e["nom"], "dossier": "-", "puce": "Chauffage", "piece": pieces[e["piece"]][1]["nom"], "hote": "", "topic": "", "ip": "-",
                     "url": "", "role": "chauffage central", "mqtt": "-", "note": ch.get("note", "") + (f" Débits mesurés par : {acq}." if k == "ch:nourrice" and acq else ""),
                     "liens": (["Débit " + str(d["debit"]) + " : " + ", ".join(pieces[q][1]["nom"] for q in d["pieces"]) for d in ch.get("departs", [])] if k == "ch:nourrice" else ["Eau chaude vers la nourrice"])}
    leg_puces = "".join(f'<span><i class="carre" style="background:{c}"></i>{n}</span>' for n, c in PUCE_COUL.items())
    legende = (LEGENDE.replace("@SERIE@", COUL_SERIE).replace("@UDP@", COUL_UDP).replace("@MQTT@", COUL_MQTT)
               .replace("@PUCES@", leg_puces))
    page = (MODELE.replace("@@PIECES@@", "".join(out_p)).replace("@@LIENS@@", "".join(out_l) + "".join(out_w) + "".join(out_ch)).replace("@@CARTES@@", "".join(out_c))
            .replace("@@RESEAU@@", vue_reseau(conf, metas, liens, maitres, conf.get("broker", {}), hotes))
            .replace("@@LEGENDE@@", legende).replace("@@COULS@@", COUL_SERIE).replace("@@COULU@@", COUL_UDP).replace("@@COULM@@", COUL_MQTT)
            .replace("@@FICHES@@", json.dumps(fiches, ensure_ascii=False).replace("</", "<\\/")))
    return page, f"plan_maison.html : {len(pos)} cartes, {len(liens)} traits de lien, {len(maitres)} maîtres, {len(esclaves)} esclaves"


def main():
    page, resume = construit()
    (ICI / "plan_maison.html").write_text(page, encoding="utf-8")
    print(resume)


LEGENDE = """<div class="legende">
<label class="l-comm"><input type="checkbox" checked data-type="serie"><svg width="46" height="12"><path d="M2,6 L36,6" stroke="@SERIE@" stroke-width="4"/><polygon fill="@SERIE@" points="44,6 36,2 36,10"/></svg>ModBus RS485 (maître vers esclave)</label>
<label class="l-comm"><input type="checkbox" checked data-type="udp"><svg width="46" height="12"><path d="M2,6 L36,6" stroke="@UDP@" stroke-width="2.6" stroke-dasharray="2 4" stroke-linecap="round"/><polygon fill="@UDP@" points="44,6 36,2 36,10"/></svg>UDP seul</label>
<span class="l-comm"><svg width="46" height="12"><path d="M2,6 L36,6" stroke="@SERIE@" stroke-width="4"/><path d="M2,6 L36,6" stroke="var(--carte)" stroke-width="1.4" stroke-dasharray="3 6"/></svg>RS485 + UDP actif, push en retour</span>
<label class="seul-reseau"><input type="checkbox" checked data-type="mqtt"><svg width="46" height="12"><path d="M2,6 L44,6" stroke="@MQTT@" stroke-width="2.6" stroke-dasharray="10 4 2 4"/></svg>MQTT (vers le broker)</label>
<span><b class="etoile">★</b> maître &nbsp; <b class="etoile vide">☆</b> maître sans esclave &nbsp; <b class="rond">3</b> esclave et son id</span>
<label class="seul-wifi"><input type="checkbox" checked data-type="wap"><svg width="46" height="12"><path d="M2,6 L36,6" stroke="#7048e8" stroke-width="2.2"/><circle cx="40" cy="6" r="4.5" fill="#7048e8"/></svg>vers un appareil Wi-Fi (couleur = appareil)</label>
<label class="seul-wifi"><input type="checkbox" data-type="wsec"><svg width="46" height="12"><path d="M2,6 L36,6" stroke="#7048e8" stroke-width="2.2" stroke-dasharray="7 5" opacity=".6"/></svg>pointillé = réseau de secours (masqué par défaut)</label>
<label class="seul-wifi"><input type="checkbox" checked data-type="wre"><svg width="46" height="12"><path d="M2,6 L44,6" stroke="#d6336c" stroke-width="6"/><path d="M2,6 L44,6" stroke="var(--carte)" stroke-width="2.2"/></svg>Range Extender du maître</label>
<span class="seul-chauffage" id="etat-debits" style="color:var(--doux)">Débits : « Lire les débits » les interroge sur la carte.</span>
<span class="seul-chauffage"><svg width="46" height="12"><path d="M2,6 L44,6" stroke="#1098ad" stroke-width="5"/></svg>eau chaude PAC vers la nourrice</span>
<span class="seul-chauffage"><svg width="46" height="12"><path d="M2,6 L44,6" stroke="#1098ad" stroke-width="2"/></svg>départs vers les pièces chauffées (rond numéroté = Débit n)</span>
<span class="puces l-comm">@PUCES@</span></div>"""

MODELE = """<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Plan de la maison</title><style>
:root{--fond:#f6f5f1;--carte:#fff;--piece:#eceae3;--trait:#8a8780;--txt:#222;--doux:#666;--accent:#1f6feb;--serie:@@COULS@@;--udp:@@COULU@@;--mqtt:@@COULM@@}
@media(prefers-color-scheme:dark){:root{--fond:#16181c;--carte:#252931;--piece:#20232a;--trait:#5b606b;--txt:#e8e8e8;--doux:#9aa0aa;--accent:#6ea8ff}}
body{margin:0;background:var(--fond);color:var(--txt);font:14px system-ui,sans-serif}
.haut{position:sticky;top:32px;z-index:50;background:var(--fond);border-bottom:1px solid var(--trait)}
header{padding:12px 16px;display:flex;gap:10px 22px;flex-wrap:wrap;align-items:center}h1{font-size:18px;margin:0}
.barre{display:flex;gap:8px;flex-wrap:wrap}.barre button{font:inherit;color:var(--txt);background:var(--carte);border:1px solid var(--trait);border-radius:6px;padding:5px 12px;cursor:pointer}
.barre button.actif{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent);font-weight:600}
.legende{display:flex;gap:8px 22px;flex-wrap:wrap;align-items:center;font-size:13px;padding:0 16px 8px}.legende>*{display:flex;align-items:center;gap:6px}.puces{gap:12px}.carre{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px}
label{cursor:pointer}.etoile{color:#e0a800}.etoile.vide{color:var(--doux)}.rond{display:inline-block;width:18px;height:18px;line-height:18px;border-radius:50%;background:var(--txt);color:var(--carte);text-align:center;font-size:11px}
main{display:flex;gap:16px;padding:0 16px 16px;flex-wrap:wrap}svg.plan,svg.reseau{flex:1 1 640px;max-width:1120px;height:auto}
body.v-plan .seul-reseau{display:none}
aside{flex:0 1 280px;background:var(--carte);border:1px solid var(--trait);border-radius:8px;padding:12px;align-self:flex-start}aside a{color:var(--accent)}
.piece{fill:var(--piece);stroke:var(--trait);stroke-width:1.2}.tirets{stroke-dasharray:5 4}.titreetage{fill:var(--txt);font-size:15px;font-weight:700}.nompiece{fill:var(--doux);font-size:12px;font-weight:600}
.wifi{fill:none;stroke:var(--trait);stroke-width:1.2;stroke-dasharray:5 4}
.broker rect{fill:var(--carte);stroke:var(--mqtt);stroke-width:2.6}.broker .t1{fill:var(--txt);font-size:13px;font-weight:700}.broker .t2{fill:var(--doux);font-size:11px}
.carte rect:first-child{fill:var(--carte);stroke:var(--trait);stroke-width:1.2;cursor:pointer}.carte.maitre rect:first-child{stroke:var(--txt);stroke-width:2.6}
.carte:hover rect:first-child,.carte:focus rect:first-child,.carte.sel rect:first-child{stroke:var(--accent);stroke-width:2.8}.carte.autonome{opacity:.8}.carte.apn rect{stroke-width:2;fill:var(--carte)}
.wl path{fill:none}.wl .rail{stroke:#d6336c;stroke-width:6;stroke-linejoin:round}.wl .ame{stroke:var(--carte);stroke-width:2.2;stroke-linejoin:round}
body:not(.v-wifi) .wl,body:not(.v-wifi) .apn,body:not(.v-wifi) .seul-wifi,body:not(.v-chauffage) .chl,body:not(.v-chauffage) .chn,body:not(.v-chauffage) .seul-chauffage{display:none}
.chl path{fill:none}.chl .hyd{stroke:#1098ad;stroke-width:5}.chl .dep{stroke:#1098ad;stroke-width:2}.chl .dv{fill:var(--txt);font-size:11px;font-weight:700;paint-order:stroke;stroke:var(--piece);stroke-width:3px}.chl circle.imp{fill:#e0a800}.chl circle.mut{fill:#c92a2a}.chl .dn{fill:#fff;font-size:10px;font-weight:700;pointer-events:none}.chl circle{fill:#1098ad}.carte.chn rect{stroke:#1098ad;stroke-width:2;fill:var(--carte)}
.lbl.lg{stroke:var(--fond)}.lbl{fill:var(--txt);font-size:10px;font-weight:700;paint-order:stroke;stroke:var(--piece);stroke-width:3px;pointer-events:none}.carte .re{fill:var(--doux);font-size:9.5px;pointer-events:none}
body.v-wifi .lien.serie,body.v-wifi .lien.udp,body.v-wifi svg.reseau,body.v-wifi .l-comm,body.v-wifi .seul-reseau,body.v-chauffage .lien.serie,body.v-chauffage .lien.udp,body.v-chauffage svg.reseau,body.v-chauffage .l-comm,body.v-chauffage .seul-reseau{display:none}
body.v-plan svg.reseau,body.v-reseau svg.plan{display:none}
.carte .t1{fill:var(--txt);font-size:12px;font-weight:600;pointer-events:none}.carte .t2{fill:var(--doux);font-size:10.5px;pointer-events:none}
.carte .etoile{fill:#e0a800;font-size:16px;pointer-events:none}.carte .etoile.vide{fill:var(--doux)}.idb{fill:var(--txt)}.idt{fill:var(--carte);font-size:11px;text-anchor:middle;font-weight:700;pointer-events:none}
.lk circle{fill:var(--carte);stroke:var(--accent);stroke-width:1.4;cursor:pointer}.lk path{fill:none;stroke:var(--accent);stroke-width:1.6;stroke-linecap:round;pointer-events:none}.lk:hover circle{fill:var(--accent)}.lk:hover path{stroke:var(--carte)}
.etat{fill:none}.carte.ok .etat{fill:#2f9e44}.carte.ko .etat{fill:#c92a2a}.carte.test .etat{fill:#e0a800}
.lien path,.mqttbus{fill:none}.lien.serie{fill:var(--serie)}.lien.serie path{stroke:var(--serie);stroke-width:4;stroke-linejoin:round}
.lien.udp.seul{fill:var(--udp)}.lien.udp.seul path{stroke:var(--udp);stroke-width:2.6;stroke-dasharray:2 5;stroke-linecap:round}
.lien.udp.sur-serie{fill:var(--serie)}.lien.udp.sur-serie path{stroke:var(--carte);stroke-width:1.4;stroke-dasharray:3 6}
.mqttbus,.lien.mqtt{fill:none;stroke:var(--mqtt);stroke-width:2.6;stroke-dasharray:10 4 2 4}
.off{display:none}.lien.fade{opacity:.12}.carte.fade{opacity:.35}
dt{color:var(--doux);font-size:12px;margin-top:8px}dd{margin:0;word-break:break-all}
@media print{.haut{position:static}:root{--fond:#fff;--carte:#fff;--piece:#f1efe9;--trait:#777;--txt:#111;--doux:#444}.barre,aside,.legende label input{display:none}main{padding:0}svg.plan,svg.reseau{max-width:none;width:100%}@page{size:landscape;margin:8mm}}
</style></head><body class="v-plan">
<div class="haut"><header><h1>Plan de la maison</h1><div class="barre"><button id="b-plan" class="actif">Vue plan</button><button id="b-reseau">Vue réseau</button><button id="b-wifi">Vue Wi-Fi</button><button id="b-chauffage">Vue chauffage</button>
<button id="b-test" title="Interroge l'IP connue de chaque carte, uniquement quand on clique">Tester les cartes</button><button id="b-debits" class="seul-chauffage" title="Lit les 6 débits sur la carte (au clic seulement)">Lire les débits</button><button id="b-print">Imprimer / PDF</button></div></header>
@@LEGENDE@@</div>
<main><svg class="plan" viewBox="0 0 1120 770" role="img" aria-label="Cartes Tasmota par pièce">@@PIECES@@@@LIENS@@@@CARTES@@</svg>@@RESEAU@@
<aside id="fiche"><b>Fiche</b><p style="color:var(--doux)">Clique sur une carte : fiche, voisines et liens.</p></aside></main>
<script>
const F=@@FICHES@@,$=s=>[...document.querySelectorAll(s)],e=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
$("input[data-type]").forEach(i=>i.addEventListener("change",()=>$("[data-type='"+i.dataset.type+"']:not(input)").forEach(p=>p.classList.toggle("off",!i.checked))));
function vue(v){document.body.className="v-"+v;$("#b-plan").forEach(b=>b.classList.toggle("actif",v=="plan"));$("#b-reseau").forEach(b=>b.classList.toggle("actif",v=="reseau"));$("#b-wifi").forEach(b=>b.classList.toggle("actif",v=="wifi"));$("#b-chauffage").forEach(b=>b.classList.toggle("actif",v=="chauffage"))}
document.getElementById("b-plan").onclick=()=>vue("plan");document.getElementById("b-reseau").onclick=()=>vue("reseau");document.getElementById("b-wifi").onclick=()=>vue("wifi");document.getElementById("b-chauffage").onclick=()=>vue("chauffage");document.getElementById("b-print").onclick=()=>window.print();
document.getElementById("b-debits").onclick=async()=>{const b=document.getElementById("b-debits"),s=document.getElementById("etat-debits");b.disabled=true;s.textContent="Lecture en cours…";
try{const r=await fetch("/debits",{cache:"no-store",signal:AbortSignal.timeout(9000)});const j=await r.json();if(!r.ok)throw new Error(j.erreur||("réponse "+r.status));
$(".chl circle").forEach(c=>c.classList.remove("imp","mut"));
j.debits.forEach((q,k)=>{const n=k+1,v=typeof q==="number"?q.toFixed(2).replace(".",",")+" L/min":"?";$(".dv[data-d='"+n+"']").forEach(t=>{t.textContent=v;const c=t.parentNode.querySelector("circle");c.classList.toggle("mut",!!(j.muets||[]).includes(n));c.classList.toggle("imp",!!(j.imprecis||[]).includes(n))})});
s.textContent="Débits lus à "+new Date().toLocaleTimeString("fr-FR")+(typeof j.total==="number"?" · total "+j.total.toFixed(2).replace(".",",")+" L/min":"")}
catch(e){s.textContent="Lecture impossible : "+(e&&e.message?e.message:e)+" (la page doit être ouverte par l'annuaire, port 7915)"}finally{b.disabled=false}};
document.getElementById("b-test").onclick=async()=>{const cs=$(".carte[data-url]");cs.forEach(c=>{c.classList.remove("ok","ko");c.classList.add("test")});
await Promise.all(cs.map(c=>fetch(c.dataset.url,{mode:"no-cors",signal:AbortSignal.timeout(2500)}).then(()=>{c.classList.remove("test");c.classList.add("ok")},()=>{c.classList.remove("test");c.classList.add("ko")})))};
let cur=null;function hl(id){if(!id){$(".lien,.carte").forEach(n=>n.classList.remove("fade","sel"));return}const v=new Set([id]);$(".lien").forEach(l=>{const m=l.dataset.de==id||l.dataset.vers==id;l.classList.toggle("fade",!m);if(m){v.add(l.dataset.de);v.add(l.dataset.vers)}});
$(".carte").forEach(c=>{c.classList.toggle("fade",!v.has(c.dataset.id));c.classList.toggle("sel",c.dataset.id==id)})}
function sel(id){cur=id;hl(id);const f=F[id];
document.getElementById("fiche").innerHTML="<b>"+e(f.libelle)+"</b><dl><dt>Rôle</dt><dd>"+e(f.role)+"</dd><dt>Pièce</dt><dd>"+e(f.piece)+"</dd><dt>Puce</dt><dd>"+e(f.puce)+"</dd><dt>Nom d'hôte</dt><dd>"+e(f.hote||"(pas de persist)")+"</dd><dt>IP</dt><dd>"+(f.url?'<a href="'+e(f.url)+'" target="_blank" rel="noopener">'+e(f.url)+"</a>":e(f.ip))+"</dd><dt>MQTT</dt><dd>"+e(f.mqtt)+" "+e(f.topic)+"</dd><dt>Dossier</dt><dd>"+e(f.dossier)+"</dd>"+(f.note?"<dt>Note</dt><dd>"+e(f.note)+"</dd>":"")+"<dt>Liens</dt><dd>"+(f.liens.map(e).join("<br>")||"aucun")+"</dd></dl>"}
$(".lk").forEach(a=>a.addEventListener("click",x=>x.stopPropagation()));
$(".carte").forEach(c=>{c.addEventListener("mouseenter",()=>hl(c.dataset.id));c.addEventListener("mouseleave",()=>hl(cur));c.addEventListener("click",()=>sel(c.dataset.id));c.addEventListener("keydown",k=>k.key=="Enter"&&sel(c.dataset.id))});
$("svg").forEach(s=>s.addEventListener("click",x=>{if(!x.target.closest(".carte")){cur=null;hl(null)}}));
</script></body></html>"""

if __name__ == "__main__":
    main()
