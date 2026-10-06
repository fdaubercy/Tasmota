"""Recherche et correction du debit / de l'adresse de la carte 16 relais, pour le sniffeur ModBus.

Meme demarche que modbusFonctions.verifieConn16 cote maitre (ReglageModbus VerifieConn16channels) :
  1. a chaque debit (celui du bus d'abord), lecture de l'adresse EN DIFFUSION : FF 03 00 FF 00 01 ;
     la carte repond avec son adresse -> debit et adresse trouves ;
  2. confirmation par la lecture du registre debit 0x00FE a l'adresse trouvee ;
  3. comparaison au persist du maitre : drivers.ModBus.debit et l'id du bloc Conn16channels ;
  4. correction (seulement sur demande, choix du 2026-10-06) : ecrit le debit (0x00FE) PUIS
     l'adresse (0x00FF), au debit ou la carte a repondu. Le nouveau debit n'est effectif qu'apres
     une COUPURE D'ALIMENTATION de la carte (PROTOCOLE_MODBUS.md section 8, piege 3).
Le PC emet : il doit etre le seul maitre (file du P4 suspendue, ou P4 debranche). La diffusion
exige que la carte soit le seul equipement a repondre a 0x00FF (les ESP32 ne repondent pas).
Le port du sniffeur revient toujours a son debit d'origine.
"""

import test_rs485_pc as rs

DEBITS = (19200, 9600, 4800, 2400, 1200)
CODES = {1200: 0, 2400: 1, 4800: 2, 9600: 3, 19200: 4}


def _lecture_adresse(trame):
    return len(trame) == 7 and trame[1] == 3 and trame[2] == 2


def cherche(sniffeur, cible):
    """cible = {"debit", "id"} attendus (persist). Rend {debit, adresse, code, attendu, ecarts} ou None."""
    origine = sniffeur.debit
    diffusion = rs.avec_crc(bytes((0xFF, 3, 0, 0xFF, 0, 1)))
    trouve = None
    try:
        for d in [origine] + [x for x in DEBITS if x != origine]:
            sniffeur.change_debit(d)
            sniffeur.message(f"recherche : essai a {d} bauds")
            rep = sniffeur.transaction(diffusion, _lecture_adresse, 0.6)
            if rep:
                adresse = rep[3] << 8 | rep[4]
                lu = sniffeur.transaction(rs.avec_crc(bytes((adresse, 3, 0, 0xFE, 0, 1))), _lecture_adresse, 0.6)
                trouve = {"debit": d, "adresse": adresse, "code": (lu[3] << 8 | lu[4]) if lu else None}
                break
    finally:
        sniffeur.change_debit(origine)
    if trouve is None:
        return None
    ecarts = []
    if trouve["debit"] != cible["debit"]:
        ecarts.append(f"debit {trouve['debit']} au lieu de {cible['debit']}")
    if trouve["adresse"] != cible["id"]:
        ecarts.append(f"adresse {trouve['adresse']} au lieu de {cible['id']}")
    if trouve["code"] is not None and trouve["code"] != CODES.get(trouve["debit"]):
        ecarts.append(f"registre debit = code {trouve['code']} : debit deja ecrit, en attente d'une coupure d'alimentation")
    return dict(trouve, attendu=cible, ecarts=ecarts)


def corrige(sniffeur, trouve, cible):
    """Ecrit le debit puis l'adresse du persist dans la carte. Rend la liste des etapes faites."""
    origine, faits = sniffeur.debit, []
    adresse = trouve["adresse"]
    echo = lambda attendue: (lambda t: t == attendue)          # noqa: E731 : 0x06 -> echo de la requete
    try:
        sniffeur.change_debit(trouve["debit"])
        if trouve["debit"] != cible["debit"] or (trouve["code"] is not None and trouve["code"] != CODES[cible["debit"]]):
            req = rs.avec_crc(bytes((adresse, 6, 0, 0xFE, 0, CODES[cible["debit"]])))
            if not sniffeur.transaction(req, echo(req), 0.6):
                raise OSError("pas d'accuse a l'ecriture du debit : rien d'autre n'a ete ecrit")
            faits.append(f"debit {cible['debit']} ecrit (effectif apres coupure d'alimentation de la carte)")
        if adresse != cible["id"]:
            req = rs.avec_crc(bytes((adresse, 6, 0, 0xFF, 0, cible["id"])))
            if not sniffeur.transaction(req, echo(req), 0.6):
                raise OSError("pas d'accuse a l'ecriture de l'adresse" + (" (le debit, lui, a ete ecrit)" if faits else ""))
            faits.append(f"adresse {adresse} -> {cible['id']}")
    finally:
        sniffeur.change_debit(origine)
    return faits
