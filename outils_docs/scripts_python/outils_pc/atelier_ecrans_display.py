"""Analyse d'un display.ini (pilote universel uDisplay) pour l'onglet « display.ini » de l'atelier des ecrans (plan A12).

`analyse(texte, ref)` lit le fichier comme le firmware (lib/lib_display/UDisplay/src/uDisplay.cpp::uDisplay::uDisplay,
tasmota/tasmota_xdsp_display/xdsp_17_universal.ino::Init_uDisplay) et rend, ligne par ligne, la section, les arguments
nommes et expliques d'apres la reference `REFERENCE`, et les erreurs / avertissements (conception
docs/superpowers/specs/2026-11-12-atelier-ecrans-ameliorations-design.md § 6.4). `insere(texte, ligne, ref)` ajoute une
ligne de parametre a sa place (rang de la reference). Banc : test_atelier_ecrans_display.py.
"""
import json
import re
from pathlib import Path

REFERENCE = "outils_docs/schemas/display_ini_parametres.json"
HEX = re.compile(r"(0[xX])?[0-9A-Fa-f]+")
DEC = re.compile(r"-?\d+")
CUMULEES = {":I", ":IC", ":IS", ":II", ":f", ":p", ":L", ":l"}     # leurs lignes s'ajoutent (donnees en hexadecimal)
SCRIPTS = {":UTI", ":UTT", ":UTX", ":UTY"}                         # opcodes separes par une espace : non controles
SANS_ETOILE = {"RGB", "QSPI", "DSI"}                               # `*` non remplace par xdsp_17::replacepin
MOTS_BUS = {"I2C": "I2C", "SPI": ",SPI,", "PAR": "PAR,"}            # cherches partout par xdsp_17, commentaires compris


def charge_reference(racine):
    return json.loads((Path(racine) / REFERENCE).read_text(encoding="utf-8"))


def _par_ligne(ref):
    return {s["ligne"]: s for s in ref["sections"]}


def section_de(ligne, ref):
    """Section `:X` d'une ligne d'en-tete (la plus longue qui convient : :UTI avant :U, :TI1 -> :TI, :L1 -> :L), ou None."""
    for nom in sorted((s["ligne"] for s in ref["sections"] if s["ligne"] != "#"), key=len, reverse=True):
        suite = ligne[len(nom):len(nom) + 1]
        if ligne.startswith(nom) and (suite in ("", ",") or (suite.isdigit() and nom in (":TI", ":L"))):
            return nom
    return None


def _valeurs(ligne, nom):
    reste = ligne[len(nom):]
    colle = ""
    if reste and reste[0] != ",":                  # :TI1,... ou :L1,... : chiffre colle au nom de la section
        colle, _, reste = reste.partition(",")
        reste = "," + reste
    v = reste[1:].split(",") if reste.startswith(",") else []
    return ([colle] if colle else []) + v


def _modele_args(sec, bus, refs):
    """Arguments attendus de la section pour le bus (variante, ou ceux de la section designee par `comme`)."""
    if sec.get("comme"):
        sec = refs[sec["comme"]]
    var = sec.get("variantes", {})
    if sec["ligne"] == ":H":
        return sec["arguments"] + var.get(bus, [])
    return var.get(bus, sec["arguments"])


def nomme(args, valeurs):
    """[{nom, valeur, base, explication...}] : arguments repetes developpes, valeurs en trop signalees."""
    res, i = [], 0
    for k, a in enumerate(args):
        rep = a.get("repete")
        if rep is None:
            n = 1
        elif rep.isdigit():
            n = int(rep)
        elif "largeur_bus" in rep:
            n = next((int(r["valeur"]) for r in res if r["nom"] == "largeur_bus" and DEC.fullmatch(r["valeur"])), 8)
        else:                                       # nombre variable : tout ce que laissent les arguments suivants
            n = max(len(valeurs) - i - (len(args) - k - 1), 0)
        for _ in range(n):
            if i >= len(valeurs):
                return res
            res.append({**a, "valeur": valeurs[i]})
            i += 1
    res += [{"nom": "(en trop)", "base": "texte", "valeur": v, "explication": "valeur non lue par le pilote"} for v in valeurs[i:]]
    return res


def _requis(args):
    return sum(int(a["repete"]) if (a.get("repete") or "").isdigit() else 1 for a in args
               if not a.get("facultatif") and not (a.get("repete") and not a["repete"].isdigit() and "largeur_bus" not in a["repete"]))


def _controle_valeurs(args, bus):
    msgs = []
    for a in args:
        v, base = a["valeur"].strip(), a.get("base")
        if v == "" or (v.endswith(";") and HEX.fullmatch(v[:-1]) and base in ("hex", "dec")):
            continue                                # « 0; » : strtol/atoi s'arretent au ; (signale par analyse)
        if base == "hex" and not HEX.fullmatch(v):
            msgs.append(f"{a['nom']} : « {v} » n'est pas un nombre hexadécimal")
        elif base == "dec" and not DEC.fullmatch(v) and not (v == "*" and a.get("etoile")):
            msgs.append(f"{a['nom']} : « {v} » n'est pas un nombre décimal")
        elif base == "broche" and v == "*" and bus in SANS_ETOILE:
            msgs.append(f"{a['nom']} : * n'est pas remplacé par une broche sur le bus {bus} (écrire le numéro)")
        elif base == "broche" and v != "*" and not DEC.fullmatch(v):
            msgs.append(f"{a['nom']} : « {v} » n'est pas une broche (numéro, -1 ou *)")
    return msgs


def analyse(texte, ref):
    """{"bus", "lignes": [{n, texte, section, arguments, erreurs, avertissements}], "erreurs", "avertissements"}."""
    refs, lignes, erreurs, avert = _par_ligne(ref), [], [], []
    bus, section, fini, premiere, vus = None, None, False, None, {}
    for n, brut in enumerate(texte.splitlines(), 1):
        t = brut.strip()
        L = {"n": n, "texte": brut, "section": None, "arguments": [], "erreurs": [], "avertissements": []}
        lignes.append(L)
        if fini:
            L["avertissements"].append("après # : ignorée par le pilote")
            continue
        if len(brut) >= 256:
            L["erreurs"].append(f"ligne de {len(brut)} caractères : 256 ou plus, ignorée par le pilote sans message")
        if not t:
            continue
        if t.startswith("#"):
            fini, L["section"] = True, "#"
            continue
        if t.startswith(";"):
            for b, mot in MOTS_BUS.items():
                if mot in t and b != bus:
                    L["avertissements"].append(f"le mot {mot.strip(',')} dans un commentaire déclenche à tort la lecture du bus {b}")
            if " " in t and section and section not in SCRIPTS:
                L["avertissements"].append(f"commentaire avec espace : la suite est lue comme des données de {section}")
            continue
        if t == ":" or t.startswith(": "):            # section « espace » du pilote : ligne et suite ignorees
            section = None
            continue
        tete, _, reste = t.partition(" ")
        if reste.lstrip().startswith(";"):
            L["avertissements"].append("commentaire en fin de ligne : le pilote coupe à chaque espace et relit les mots "
                                       "après « ; » comme une ligne de données")
            t = tete
        if re.search(r"[0-9A-Fa-f];(,|$)", t):
            L["avertissements"].append("« ; » collé à une valeur : ignoré par le pilote, à retirer")
        if premiere is None:
            premiere = t
            if not t.startswith(":H"):
                L["erreurs"].append("première ligne : :H attendu (en-tête de l'écran)")
        if t.startswith(":"):
            nom = section_de(t, ref)
            if nom is None:
                L["avertissements"].append(f"section {t.split(',')[0]} inconnue du pilote : ignorée")
                section = None
                continue
            section = L["section"] = nom
            vus.setdefault(nom, n)
            if nom in SCRIPTS:
                continue
            valeurs = _valeurs(t, nom)
        else:
            L["section"] = section
            if section in SCRIPTS or section is None:
                continue
            valeurs = t.split(",")
            if section in CUMULEES:                 # octets cumules : une espace coupe la ligne, la suite s'ajoute pareil
                valeurs = re.split(r"[ ,]+", t)
                L["arguments"] = [{"nom": "octet", "base": "hex", "valeur": v} for v in valeurs]
                L["erreurs"] += _controle_valeurs(L["arguments"], bus)
                continue
        if " " in t:
            L["erreurs"].append("espace dans la ligne : le pilote lit la suite comme une nouvelle ligne")
        sec = refs[L["section"]]
        if L["section"] == ":H" and len(valeurs) > 4:
            bus = re.sub(r"^I2C\d$", "I2C", valeurs[4])
            if bus not in ref["bus"]:
                L["erreurs"].append(f"bus {valeurs[4]} inconnu : {', '.join(ref['bus'])} attendu")
                bus = None
        args = _modele_args(sec, bus, refs)
        L["arguments"] = nomme(args, valeurs)
        if L["section"] == ":H" and bus:
            requis = _requis(args)
            if bus == "PAR":
                requis += next((int(a["valeur"]) for a in L["arguments"] if a["nom"] == "largeur_bus"
                                and DEC.fullmatch(a["valeur"])), 8) - 1
            if len(valeurs) == requis - 1 and args[-1]["nom"] == "frequence":
                L["avertissements"].append("fréquence absente : le pilote lit 255 (next_val sans valeur)")
            elif len(valeurs) < requis:
                L["erreurs"].append(f"{bus} : {len(valeurs) - 5} valeurs après le bus, {requis - 5} attendues "
                                    "(broches et fréquence)")
        if L["section"] == ":B" and len(valeurs) < 2:
            L["avertissements"].append(":B sans drapeaux : ils valent 255, tous les bits actifs (échange de couleurs, "
                                       "inversion, PSRAM...)")
        L["erreurs"] += _controle_valeurs(L["arguments"], bus)
    for avant, apres in ((":F", ":A"), (":I", ":f"), (":f", ":p")):
        if avant in vus and apres in vus and vus[avant] > vus[apres]:
            erreurs.append(f"{avant} (ligne {vus[avant]}) doit précéder {apres} (ligne {vus[apres]})")
    if not fini:
        avert.append("pas de # final : à ajouter en dernière ligne")
    erreurs += [f"ligne {L['n']} : {m}" for L in lignes for m in L["erreurs"]]
    avert += [f"ligne {L['n']} : {m}" for L in lignes for m in L["avertissements"]]
    return {"bus": bus, "lignes": lignes, "erreurs": erreurs, "avertissements": avert}


def modele_ligne(ligne, bus, ref):
    """Ligne neuve d'un parametre : ses arguments a leur valeur par defaut (sinon 0)."""
    refs = _par_ligne(ref)
    if ligne == "#":
        return "#"
    vals = []
    for a in _modele_args(refs[ligne], bus, refs):
        d = str(a.get("defaut", "")).split(" ")[0]
        vals += [d if DEC.fullmatch(d) else "0"] * (int(a["repete"]) if (a.get("repete") or "").isdigit() else 1)
    return ligne + ("," + ",".join(vals) if vals else "")


def insere(texte, ligne, ref):
    """Texte avec la ligne du parametre ajoutee apres la derniere ligne de rang inferieur ou egal (avant `#`)."""
    refs = _par_ligne(ref)
    a = analyse(texte, ref)
    rang = refs[ligne]["rang"]
    nouvelle = modele_ligne(ligne, a["bus"], ref)
    pos = 0
    for L in a["lignes"]:
        s = L["section"]
        if s == "#":
            break
        if s and refs.get(s, {}).get("rang", 0) <= rang:
            pos = L["n"]
    lignes = texte.splitlines()
    fin = "\r\n" if "\r\n" in texte else "\n"
    return fin.join(lignes[:pos] + [nouvelle] + lignes[pos:]) + fin
