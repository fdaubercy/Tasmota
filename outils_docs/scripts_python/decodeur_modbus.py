"""Decodeur ModBus RTU du sniffeur (sniffeur_modbus.py) : la norme, puis les deux dialectes du parc.

Trois lectures d'une meme trame :
  1. la NORME ModBus RTU : champs octet par octet (adresse, fonction, registre, quantite,
     nombre d'octets, donnees, CRC) et exceptions ;
  2. la CARTE 16 RELAIS (driver modBus_Conn16channels.be ; PROTOCOLE_MODBUS.md section 8) :
     0x06 registre = canal, octet fort = ordre (01 Open .. 08 Close all), octet faible = tempo ;
     0x03 relit les 16 sorties (0x0001 = open = sortie au niveau BAS) ; 0x00FE debit, 0x00FF adresse ;
  3. les ESCLAVES ESP32 TASMOTA (driver modBus_TasmotaSlaveModBus.be ; cote esclave
     modbusFonctions.executeCmdModbus) : registre = code GPIO Tasmota + idModBus - 1
     (160 interrupteur, 224 relai, 1312 DS18B20...) ; 0x06 octet fort 0x02 = Power ON, 0x01 = OFF,
     octet faible = delai avant inversion ; 0x04 float / uint32 gros-boutiens sur 2 registres.
Qui est quoi : lu dans le _persist.json du MAITRE (drivers.ModBus.environnement -> adresse de chaque
esclave ; modules.*.environnement.* -> appareils 'virtuel' = 'ModBus_<module>', idModBus, type, nom).
Le decodage reproduit les conclusions du maitre (SwitchMode, Relais_i), pas une lecture a part.
"""

import json
import os
import re
import struct

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PERSIST_MAITRE = os.path.join(RACINE, "data", "garage", "tasmota32p4-serveur-modbus", "_persist.json")
TEMPLATE_GPIO = os.path.join(RACINE, "tasmota", "include", "tasmota_template.h")

FONCTIONS = {1: "Read Coils", 2: "Read Discrete Inputs", 3: "Read Holding Registers",
             4: "Read Input Registers", 5: "Write Single Coil", 6: "Write Single Register",
             15: "Write Multiple Coils", 16: "Write Multiple Registers", 0x11: "ISALIVE_ESCLAVE (maison)"}
EXCEPTIONS = {1: "fonction illegale", 2: "adresse de donnees illegale", 3: "valeur de donnees illegale",
              4: "defaillance de l'esclave", 5: "acquittement (traitement long)", 6: "esclave occupe",
              8: "erreur de parite memoire", 0x0A: "passerelle : chemin indisponible",
              0x0B: "passerelle : la cible ne repond pas"}
ORDRES_CONN16 = {1: "Open", 2: "Close", 3: "Toggle", 4: "Latch", 5: "Momentary", 6: "Delay",
                 7: "Open all", 8: "Close all"}
CODES_DEBIT = {0: "1200", 1: "2400", 2: "4800", 3: "9600", 4: "19200", 5: "retour usine"}
TYPES_DEFAUT = {32: "GPIO_KEY1", 160: "GPIO_SWT1", 192: "GPIO_SWT1_NP", 224: "GPIO_REL1",
                256: "GPIO_REL1_INV", 352: "GPIO_CNTR1", 1216: "GPIO_DHT22", 1312: "GPIO_DSB",
                1376: "GPIO_WS2812", 4704: "GPIO_ADC_INPUT"}
LIBELLES = {32: "bouton", 160: "interrupteur", 192: "interrupteur", 224: "relai",
            256: "relai inverse (Relais_i)", 352: "compteur", 1216: "DHT22", 1312: "DS18B20",
            1376: "LEDs WS2812", 4704: "entree analogique"}
FLOTTANTS, ENTIERS32 = (1216, 1312), (352, 4704)


# ------------------------------------------------------------------ outils
def crc16(donnees):
    c = 0xFFFF
    for octet in donnees:
        c ^= octet
        for _ in range(8):
            c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
    return c


def crc_ok(trame):
    return len(trame) >= 4 and crc16(trame[:-2]) == trame[-2] | (trame[-1] << 8)


def hx(octets):
    return " ".join(f"{o:02X}" for o in octets)


def lit_texte(texte):
    """Hexa libre, ou ligne de log 'ModbusPushUDP <seq> <hexa>' -> bytes ; ValueError si invalide."""
    t = texte.strip()
    if t.startswith("ModbusPushUDP"):
        mots = t.split()
        t = " ".join(mots[2:] if len(mots) >= 3 else mots[1:])     # retire l'enveloppe et le numero d'ordre
    t = re.sub(r"[\s,;:]|0x", "", t)
    if len(t) % 2 or not re.fullmatch(r"[0-9A-Fa-f]*", t):
        raise ValueError(f"hexa invalide : {texte!r}")
    return bytes.fromhex(t)


def charge_types_gpio(chemin=TEMPLATE_GPIO):
    """{code: 'GPIO_...'} depuis l'enum UserSelectablePins (code = rang x 32) ; defauts sinon."""
    try:
        s = open(chemin, encoding="utf-8", errors="replace").read()
        i = s.index("enum UserSelectablePins")
        corps = s[s.index("{", i) + 1:s.index("};", i)]
        corps = re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", corps), flags=re.S)
        noms = [n.split("=")[0].strip() for n in corps.split(",") if n.strip()]
        return {rang * 32: nom for rang, nom in enumerate(noms)} or dict(TYPES_DEFAUT)
    except (OSError, ValueError):
        return dict(TYPES_DEFAUT)


def lit_bus(chemin=PERSIST_MAITRE):
    """{debit, mode} du bus selon le persist du maitre (drivers.ModBus) ; debit 19200 par defaut."""
    try:
        with open(chemin, encoding="utf-8") as f:
            mb = json.load(f).get("drivers", {}).get("ModBus", {})
        return {"debit": int(mb.get("debit", 19200)), "mode": mb.get("mode", "8N1")}
    except (OSError, ValueError, TypeError):
        return {"debit": 19200, "mode": "8N1"}


def charge_carte(chemin=PERSIST_MAITRE):
    """{adresse: {id, nom, driver ('conn16'|'esp32'), module, appareils: {registre: fiche}}}."""
    try:
        with open(chemin, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return {}
    esclaves, par_module = {}, {}
    for groupe, modules in d.get("drivers", {}).get("ModBus", {}).get("environnement", {}).items():
        g = groupe.lower()
        driver = "conn16" if g.startswith("conn16") else ("esp32" if "slave" in g else None)
        if not driver or not isinstance(modules, dict):
            continue
        for nom_module, fiche in modules.items():
            if isinstance(fiche, dict) and isinstance(fiche.get("id"), int):
                e = {"id": fiche["id"], "nom": fiche.get("name", nom_module), "driver": driver,
                     "module": nom_module, "appareils": {}}
                esclaves[fiche["id"]] = par_module[nom_module] = e
    for module in d.get("modules", {}).values():
        if not isinstance(module, dict):
            continue
        for famille, appareils in module.get("environnement", {}).items():
            if not isinstance(appareils, dict):
                continue
            for cle, a in appareils.items():
                if not isinstance(a, dict) or not isinstance(a.get("type"), int) or "idModBus" not in a:
                    continue
                e = par_module.get(str(a.get("virtuel", ""))[len("ModBus_"):])
                if e is None:
                    continue
                reg = a["idModBus"] if e["driver"] == "conn16" else a["type"] + a["idModBus"] - 1
                e["appareils"][reg] = {"cle": cle, "nom": a.get("nom", cle), "famille": famille,
                                       "type": a["type"], "idModBus": a["idModBus"],
                                       "switchMode": a.get("SwitchMode") or 1, "activation": a.get("activation", "OFF")}
    return esclaves


# ------------------------------------------------------------------ norme
def nature(trame, attendue):
    """'requete', 'reponse', 'exception', 'ko' ou '?'. attendue : requete sans reponse (ou None),
    seule facon de distinguer une reponse 0x05/0x06 (echo de la requete) d'une nouvelle requete."""
    if not crc_ok(trame):
        return "ko"
    fc, d = trame[1], trame[2:-2]
    if fc & 0x80:
        return "exception"
    meme = attendue is not None and attendue[:2] == trame[:2]
    if fc in (1, 2, 3, 4):
        if d and len(d) == 1 + d[0] and (meme or len(d) != 4):
            return "reponse"
        return "requete" if len(d) == 4 else "?"
    if fc in (5, 6) and len(d) == 4:
        return "reponse" if meme and attendue == trame else "requete"
    if fc in (15, 16):
        if len(d) == 4:
            return "reponse"            # une requete 0x0F/0x10 porte au moins le nombre d'octets
        return "requete" if len(d) >= 5 and len(d) == 5 + d[4] else "?"
    return "?"


def _champ(liste, nom, octets, norme, metier=""):
    c = {"champ": nom, "hex": hx(octets), "norme": norme, "metier": metier}
    liste.append(c)
    return c


def _norme(trame, nat, requete, ch):
    """Champs standard ; rend (texte, registre vise, donnees de reponse [(adresse, mot, champ)])."""
    fc, d = trame[1], trame[2:-2]
    u16 = lambda i: d[i] << 8 | d[i + 1]                           # noqa: E731
    if nat == "exception":
        _champ(ch, "Code d'exception", d[:1], EXCEPTIONS.get(d[0], "inconnu") if d else "absent")
        return (f"EXCEPTION a la fonction 0x{fc & 0x7F:02X} : {EXCEPTIONS.get(d[0], 'code inconnu') if d else '?'}",
                (requete[2] << 8 | requete[3]) if requete and len(requete) >= 8 else None, [])
    if fc in (1, 2, 3, 4):
        unite = "bit(s)" if fc in (1, 2) else "registre(s)"
        if nat == "requete":
            _champ(ch, "Registre de depart", d[0:2], f"{u16(0)} (0x{u16(0):04X})")
            _champ(ch, "Quantite", d[2:4], f"{u16(2)} {unite}")
            return f"REQUETE : lire {u16(2)} {unite} a partir de {u16(0)} (0x{u16(0):04X})", u16(0), []
        _champ(ch, "Nombre d'octets", d[0:1], str(d[0]))
        depart = (requete[2] << 8 | requete[3]) if requete and len(requete) >= 8 else None
        if fc in (1, 2):
            nb = (requete[4] << 8 | requete[5]) if requete and len(requete) >= 8 else 8 * d[0]
            bits = [(d[1 + k // 8] >> (k % 8)) & 1 for k in range(min(nb, 8 * d[0]))]
            c = _champ(ch, "Donnees (bits, poids faible d'abord)", d[1:], " ".join(f"b{k}={b}" for k, b in enumerate(bits)))
            return f"REPONSE : {len(bits)} bit(s) = {''.join(map(str, bits))}", depart, [(depart, bits[0] if bits else 0, c)]
        regs = []
        for k in range(d[0] // 2):
            mot = u16(1 + 2 * k)
            nom = f"Registre {depart + k} (0x{depart + k:04X})" if depart is not None else f"Mot {k + 1}"
            regs.append(((depart + k) if depart is not None else None, mot,
                         _champ(ch, nom, d[1 + 2 * k:3 + 2 * k], str(mot))))
        return f"REPONSE : {len(regs)} registre(s) = {[r[1] for r in regs]}", depart, regs
    if fc in (5, 6) and len(d) == 4:
        sens = "ACCUSE (echo de la requete)" if nat == "reponse" else "REQUETE"
        _champ(ch, "Registre" if fc == 6 else "Coil", d[0:2], f"{u16(0)} (0x{u16(0):04X})")
        if fc == 5:
            v = {0xFF00: "ON", 0x0000: "OFF"}.get(u16(2), "valeur invalide (ni FF00 ni 0000)")
            _champ(ch, "Valeur", d[2:4], v)
            return f"{sens} : coil {u16(0)} <- {v}", u16(0), []
        _champ(ch, "Valeur (octet fort, octet faible)", d[2:4], f"{u16(2)} = {d[2]}, {d[3]}")
        return f"{sens} : registre {u16(0)} <- {u16(2)} (0x{u16(2):04X})", u16(0), []
    if fc in (15, 16) and len(d) >= 4:
        unite = "bit(s)" if fc == 15 else "registre(s)"
        _champ(ch, "Registre de depart", d[0:2], f"{u16(0)} (0x{u16(0):04X})")
        _champ(ch, "Quantite", d[2:4], f"{u16(2)} {unite}")
        if nat == "reponse":
            return f"ACCUSE : {u16(2)} {unite} ecrit(s) a partir de {u16(0)}", u16(0), []
        _champ(ch, "Nombre d'octets", d[4:5], str(d[4]) if len(d) > 4 else "?")
        regs = []
        if fc == 16:
            for k in range((len(d) - 5) // 2):
                mot = u16(5 + 2 * k)
                regs.append((u16(0) + k, mot, _champ(ch, f"Registre {u16(0) + k}", d[5 + 2 * k:7 + 2 * k], str(mot))))
        else:
            _champ(ch, "Donnees (bits)", d[5:], "")
        return f"REQUETE : ecrire {u16(2)} {unite} a partir de {u16(0)} (0x{u16(0):04X})", u16(0), regs
    _champ(ch, "Donnees", d, "")
    return f"fonction 0x{fc:02X} : {FONCTIONS.get(fc, 'non standard')}", None, []


# ------------------------------------------------------------------ dialectes
def _etat_conn16(ordre_ou_open, type_relai, est_ordre):
    """Etat du relai cote maitre (Relais_i 256 : sortie basse = 'open' = ON), cf. etatPourRegistre."""
    est_open = (ordre_ou_open == 1) if est_ordre else bool(ordre_ou_open)
    inverse = type_relai == 256
    return "ON" if est_open == inverse else "OFF"


def _conn16(e, fc, nat, d, reg, regs):
    if fc == 6 and len(d) == 4:
        accuse = "Accuse : " if nat == "reponse" else ""
        if reg == 0x00FE:
            return f"{accuse}reglage du debit : code {d[3]} = {CODES_DEBIT.get(d[3], '?')} bauds (effectif apres coupure d'alimentation)"
        if reg == 0x00FF:
            return f"{accuse}changement d'adresse -> {d[3]} (un seul equipement sur le bus !)"
        ordre, a = d[2], e["appareils"].get(reg)
        cible = "tous les canaux" if reg == 0 else f"canal {reg}" + (f" '{a['nom']}'" if a else "")
        texte = f"{accuse}carte relais, {cible} <- ordre {d[2]:02X} {ORDRES_CONN16.get(ordre, 'INVALIDE (la carte ne repond pas)')}"
        if ordre == 6:
            texte += f", tempo {d[3]} s"
        if ordre in (1, 2) and a:
            texte += f" -> relai {_etat_conn16(ordre, a['type'], True)} (type {a['type']})"
        return texte
    if fc == 3 and nat == "requete":
        return {0x00FE: "lecture du debit", 0x00FF: "lecture de l'adresse"}.get(
            reg, f"releve des sorties {reg} a {reg + (d[2] << 8 | d[3]) - 1}")
    if fc == 3 and nat == "reponse" and regs:
        if reg in (0x00FE, 0x00FF):
            v = regs[0][1]
            return f"debit actuel : {CODES_DEBIT.get(v, '?')} bauds" if reg == 0x00FE else f"adresse actuelle : {v}"
        allumes = []
        for k, (adr, mot, c) in enumerate(regs):
            canal = adr if adr is not None else k + 1
            a = e["appareils"].get(canal)
            etat = _etat_conn16(mot, a["type"] if a else 256, False)
            c["metier"] = f"canal {canal} {'open (sortie basse)' if mot else 'close'}" + (f" -> '{a['nom']}' {etat}" if a else "")
            if a and etat == "ON":
                allumes.append(a["nom"])
        return f"etat des {len(regs)} sorties ; relais ON : {', '.join(allumes) or 'aucun'}"
    return ""


def _appareil(e, reg, types):
    base, n = (reg // 32) * 32, reg % 32 + 1
    a = e["appareils"].get(reg)
    texte = f"{LIBELLES.get(base, types.get(base, f'type {base}'))} n{n} ({types.get(base, '?')})"
    return (texte + (f" '{a['nom']}'" if a else ""), base, a)


def _id_relai(reg):
    return reg - 223 if 224 <= reg < 256 else reg - 255 if 256 <= reg < 288 else reg


def _esp32(e, fc, nat, d, reg, regs, types):
    if reg is None:
        return ""
    desc, base, a = _appareil(e, reg, types)
    if fc == 1:
        if nat == "requete":
            return f"releve de l'etat reel du {desc} (Power{_id_relai(reg)})"
        bit = regs[0][1] if regs else 0
        texte = f"Power{_id_relai(reg)} = {'ON' if bit else 'OFF'}"
        return texte + (f" -> etat constate {'ON' if bit != (base == 256) else 'OFF'} (Relais_i)" if base == 256 else "")
    if fc == 2:
        if nat == "requete":
            return f"demande l'etat de : {desc}"
        mode = a["switchMode"] if a else 1
        actif = bool(regs[0][1]) if regs else False
        etat = ("ON" if actif else "OFF") if mode != 2 else ("OFF" if actif else "ON")
        return f"{desc} : bit {int(actif)} -> {etat} (SwitchMode {mode})"
    if fc == 4:
        if nat == "requete":
            return f"demande la valeur de : {desc}"
        brut = bytes(b for _, mot, _ in regs for b in (mot >> 8, mot & 0xFF))
        if base in FLOTTANTS:
            vals = [struct.unpack(">f", brut[i:i + 4])[0] for i in range(0, len(brut) - 3, 4)]
            noms = ["temperature (C)", "humidite (%)"] if base == 1216 else ["temperature (C)"]
            return f"{desc} : " + ", ".join(f"{noms[k] if k < len(noms) else 'valeur'} = {v:.2f}" for k, v in enumerate(vals))
        if base in ENTIERS32 and len(brut) >= 4:
            return f"{desc} : {int.from_bytes(brut[:4], 'big')}"
        return f"{desc} : mots {[m for _, m, _ in regs]}"
    if fc == 5 and len(d) == 4:
        return f"{'Accuse : ' if nat == 'reponse' else ''}Power{_id_relai(reg)} {'ON' if d[2] == 0xFF else 'OFF'}"
    if fc == 6 and len(d) == 4:
        power = {2: "ON", 1: "OFF"}.get(d[2], f"? (octet fort {d[2]:02X} : ni 01 ni 02)")
        texte = f"{'Accuse : ' if nat == 'reponse' else ''}{desc} -> Power{_id_relai(reg)} {power}"
        if d[3]:
            texte += f", inverse apres {d[3]} s"
        if base == 256 and d[2] in (1, 2):
            texte += f" (Relais_i : etat {'ON' if d[2] == 1 else 'OFF'} cote maitre)"
        return texte
    if fc == 16:
        if nat == "reponse":
            return f"Accuse : {desc}"
        mots = [m for _, m, _ in regs]
        if base == 1376 and len(mots) >= 3:
            return f"{desc} : couleur (teinte) {mots[0]}, saturation {mots[1]}, luminosite {mots[2]} (HSBColor)"
        brut = bytes(b for m in mots for b in (m >> 8, m & 0xFF))
        if base in FLOTTANTS and len(brut) >= 4:
            v = ", ".join(f"{struct.unpack('>f', brut[i:i + 4])[0]:.2f}" for i in range(0, len(brut) - 3, 4))
        elif base in ENTIERS32 and len(brut) >= 4:
            v = str(int.from_bytes(brut[:4], "big"))
        elif base in (32, 160, 192) and mots:            # interrupteur / bouton : 0x00FF = actif
            mode, actif = (a["switchMode"] if a else 1), bool(mots[0] & 1)
            v = f"bit 0 = {int(actif)} -> {('ON' if actif else 'OFF') if mode != 2 else ('OFF' if actif else 'ON')} (SwitchMode {mode})"
        else:
            v = f"mots {mots}"
        return f"PUSH esclave -> maitre (enveloppe UDP 'ModbusPushUDP <seq> <hexa>') : {desc} = {v}"
    return ""


def decode(trame, requete=None, carte=None, types=None):
    """-> {nature, norme, metier, champs: [{champ, hex, norme, metier}]}. requete : la requete
    a laquelle repond la trame (sinon le registre d'une reponse 0x01-0x04 est inconnu)."""
    carte, types = carte or {}, types or TYPES_DEFAUT
    nat = nature(trame, requete)
    res = {"nature": nat, "norme": "", "metier": "", "champs": []}
    ch = res["champs"]
    if len(trame) < 4:
        res["norme"] = "trame trop courte (4 octets minimum : adresse, fonction, CRC)"
        _champ(ch, "Octets", trame, "")
        return res
    ident, fc = trame[0], trame[1]
    e = carte.get(ident)
    _champ(ch, "Adresse esclave", trame[0:1], "diffusion" if ident in (0, 0xFF) else str(ident),
           f"{e['nom']} ({'carte 16 relais' if e['driver'] == 'conn16' else 'esclave ESP32'})" if e else "")
    _champ(ch, "Fonction", trame[1:2], ("EXCEPTION sur " if fc & 0x80 else "") + FONCTIONS.get(fc & 0x7F, "non standard"))
    if nat == "ko":                     # trame alteree : ses longueurs et compteurs ne sont pas fiables
        norme, reg, regs = "trame au CRC faux : champs non interpretes", None, []
        _champ(ch, "Donnees (brutes)", trame[2:-2], "")
    else:
        try:
            norme, reg, regs = _norme(trame, nat, requete, ch)
        except (IndexError, ValueError, struct.error) as erreur:      # trame mal formee mais au CRC juste
            norme, reg, regs = f"trame mal formee pour la fonction 0x{fc:02X} ({erreur})", None, []
    calc = crc16(trame[:-2])
    _champ(ch, "CRC (poids faible d'abord)", trame[-2:], "OK" if nat != "ko" else f"KO : attendu {calc & 0xFF:02X} {calc >> 8:02X}")
    res["norme"] = norme
    if nat == "ko":
        res["metier"] = "CRC faux : trame alteree (parasite, debit, A/B, terminaison) ou tronquee"
    elif nat == "exception":
        cible = f" sur {_appareil(e, reg, types)[0]}" if e and e["driver"] == "esp32" and reg is not None else ""
        res["metier"] = f"l'esclave refuse la requete{cible} ({EXCEPTIONS.get(trame[2], '?') if len(trame) > 4 else '?'})"
    elif e and nat == "reponse" and reg is None and fc in (1, 2, 3, 4) and e["driver"] == "esp32":
        res["metier"] = "reponse d'un esclave ESP32 : le registre lu est dans la requete, non vue (la decoder avec)"
    elif ident == 0xFF and fc == 3 and reg == 0x00FF:
        res["metier"] = "carte relais : lecture de l'adresse en diffusion (un seul equipement doit repondre)"
    elif e:
        try:
            res["metier"] = (_conn16(e, fc, nat, trame[2:-2], reg, regs) if e["driver"] == "conn16"
                             else _esp32(e, fc, nat, trame[2:-2], reg, regs, types))
        except (IndexError, ValueError, struct.error) as erreur:
            res["metier"] = f"lecture metier impossible ({erreur})"
    elif fc == 0x11:
        res["metier"] = "ISALIVE_ESCLAVE : code reserve, jamais cable"
    else:
        res["metier"] = f"adresse {ident} absente du persist du maitre"
    return res
