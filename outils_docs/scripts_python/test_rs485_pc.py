r"""Test d'un bus ModBus RTU (RS485) depuis le PC, par un convertisseur USB-RS485.

Materiel vise : Waveshare USB TO RS485 (CH343G + SP485EEN, direction automatique).
Bornes : A+ -> A du bus, B- -> B du bus, GND -> masse du bus.

UTILISATION (Python de PlatformIO, qui fournit pyserial) :
    %USERPROFILE%\.platformio\penv\Scripts\python.exe outils_docs/scripts_python/test_rs485_pc.py <commande> [options]

COMMANDES
    lister                   ports serie presents (pour --port)
    ecoute                   affiche toutes les trames du bus, n'emet RIEN : ce qu'emet
                             le maitre P4 et ce que repondent les esclaves
    envoi "01 03 00 01 00 10"    emet une trame (CRC ajoute, sauf --brut) et attend la reponse
    lire                     etat des 16 sorties de la carte relais (fonction 0x03)
    relais <canal> <ordre>   commande un canal (1-16, 0 = tous) ; ordre : open, close,
                             toggle, latch, momentary, delay (--tempo s), openall, closeall
    debit                    cherche le debit et l'adresse de la carte relais
    esclave                  se fait passer pour la carte 16 relais d'adresse --id :
                             pour tester l'emission ET la reception du P4 sans la carte

OPTIONS
    --port COMx|auto (defaut auto)    --debit 19200 (debit du bus)    --id 1
    --repete N --intervalle 0.5       rafale (pour voir clignoter les LED des XY-485)
    --attente 0.5                     delai max d'une reponse, en secondes
    --silence 0.02                    silence qui clot une trame (latence USB comprise)

UN SEUL MAITRE SUR LE BUS
    envoi / lire / relais / debit font du PC un MAITRE. Si le P4 sonde le bus en meme
    temps, les trames se percutent. Avant : charger test_liaison_modbus.be sur le P4 (il
    suspend la file ModBus), ou debrancher le P4. ecoute et esclave n'emettent pas d'eux-
    memes. Pour esclave : debrancher la vraie carte relais (ou prendre un autre --id),
    sinon deux reponses se superposent.

    La carte relais sort d'usine a 9600 bauds, adresse 1 ; le bus du garage est a 19200
    (outils_docs/PROTOCOLE_MODBUS.md, section 8).
"""

import argparse
import sys
import time

import serial
from serial.tools import list_ports

ORDRES = {"open": 1, "close": 2, "toggle": 3, "latch": 4, "momentary": 5,
          "delay": 6, "openall": 7, "closeall": 8}
NOMS_ORDRES = {v: k for k, v in ORDRES.items()}
CODES_DEBIT = {0: 1200, 1: 2400, 2: 4800, 3: 9600, 4: 19200}
DEBITS_ESSAYES = (19200, 9600, 4800, 2400, 1200, 38400, 57600, 115200)


# ------------------------------------------------------------------ trames
def crc16(donnees):
    """CRC ModBus RTU (polynome 0xA001, depart 0xFFFF)."""
    c = 0xFFFF
    for octet in donnees:
        c ^= octet
        for _ in range(8):
            c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
    return c


def avec_crc(donnees):
    """Trame + CRC, octet de poids faible en premier."""
    c = crc16(donnees)
    return bytes(donnees) + bytes((c & 0xFF, c >> 8))


def crc_ok(trame):
    return len(trame) >= 4 and crc16(trame[:-2]) == trame[-2] | (trame[-1] << 8)


def hexa(trame):
    return " ".join(f"{o:02X}" for o in trame)


def lit_hexa(texte):
    """'01 03 00 01' ou '01030001' -> bytes ; ValueError si invalide."""
    t = texte.replace(" ", "").replace(",", "").replace("0x", "")
    if len(t) % 2:
        raise ValueError(f"nombre impair de chiffres hexa : {texte!r}")
    return bytes.fromhex(t)


def decoupe(tampon):
    """Separe des trames collees (requete + reponse recues dans le meme silence).

    Prend a chaque fois le plus court prefixe dont le CRC est bon. Les octets qui ne
    forment aucune trame valide sont rendus en un seul morceau (CRC KO a l'affichage).
    """
    trames, i = [], 0
    while i < len(tampon):
        for fin in range(i + 4, len(tampon) + 1):
            if crc_ok(tampon[i:fin]):
                trames.append(tampon[i:fin])
                i = fin
                break
        else:
            trames.append(tampon[i:])
            break
    return trames


def decrit(trame):
    """Lecture en clair d'une trame ModBus (requete ou reponse)."""
    if len(trame) < 4:
        return "trame trop courte"
    ident, fc, d = trame[0], trame[1], trame[2:-2]
    texte = f"id {ident} fc 0x{fc:02X}"
    if fc & 0x80:
        return f"{texte} EXCEPTION code {d[0] if d else '?'}"
    if fc in (3, 4):
        if d and len(d) == 1 + d[0]:
            regs = [d[1 + 2 * k] << 8 | d[2 + 2 * k] for k in range(d[0] // 2)]
            return f"{texte} REPONSE {len(regs)} registre(s) : {regs}"
        if len(d) == 4:
            return f"{texte} REQUETE lecture de {d[2] << 8 | d[3]} registre(s) depuis 0x{d[0] << 8 | d[1]:04X}"
    if fc == 6 and len(d) == 4:
        reg = d[0] << 8 | d[1]
        if reg == 0x00FE:
            return f"{texte} ecriture debit code {d[3]} ({CODES_DEBIT.get(d[3], '?')} bauds)"
        if reg == 0x00FF:
            return f"{texte} ecriture adresse {d[3]}"
        canal = "tous" if reg == 0 else f"canal {reg}"
        return f"{texte} {canal} ordre {NOMS_ORDRES.get(d[2], d[2])} tempo {d[3]}"
    return f"{texte} donnees {hexa(d)}"


def affiche(sens, trame, t0):
    etat = "CRC OK" if crc_ok(trame) else "CRC KO"
    print(f"[{(time.monotonic() - t0) * 1000:8.0f} ms] {sens} {hexa(trame)}   ({etat}) {decrit(trame)}")


# ------------------------------------------------------------------ port serie
def choisit_port(nom):
    if nom != "auto":
        return nom
    ports = list(list_ports.comports())
    ch343 = [p for p in ports if p.vid == 0x1A86 and p.pid == 0x55D3]
    if len(ch343) == 1:
        return ch343[0].device
    if len(ports) == 1:
        return ports[0].device
    # Les cartes ESP32 portent souvent elles aussi un CH343 : debrancher/rebrancher le
    # convertisseur et relancer `lister` montre lequel est le sien.
    print("Port ambigu ou absent : preciser --port. Ports presents :")
    lister()
    sys.exit(1)


def ouvre(args, debit=None):
    # serial_for_url : accepte aussi loop:// (essai du script sans materiel)
    port = serial.serial_for_url(choisit_port(args.port), debit or args.debit, bytesize=8,
                                 parity=serial.PARITY_NONE, stopbits=1, timeout=0)
    port.reset_input_buffer()
    return port


def lit_trames(port, attente, silence):
    """Octets recus jusqu'a un silence de `silence` s, decoupes en trames ; [] si rien
    n'arrive avant `attente` s."""
    debut, tampon, dernier = time.monotonic(), bytearray(), 0.0
    while True:
        n = port.in_waiting
        maintenant = time.monotonic()
        if n:
            tampon += port.read(n)
            dernier = maintenant
        elif tampon and maintenant - dernier >= silence:
            return decoupe(bytes(tampon))
        elif not tampon and maintenant - debut >= attente:
            return []
        else:
            time.sleep(0.001)


def transaction(port, trame, args, t0):
    """Emet une trame, affiche et rend les trames recues en retour (echo local retire)."""
    port.reset_input_buffer()
    port.write(trame)
    port.flush()
    affiche("-->", trame, t0)
    recues = lit_trames(port, args.attente, args.silence)
    if recues and recues[0] == trame:
        recues = recues[1:]           # convertisseur qui renvoie son propre envoi
    for r in recues:
        affiche("<--", r, t0)
    if not recues:
        print(f"[{(time.monotonic() - t0) * 1000:8.0f} ms] <-- RIEN en {args.attente} s")
    return recues


def rafale(port, trame, args):
    """Emet la trame --repete fois ; bilan reponses / silences."""
    t0, nb_ok = time.monotonic(), 0
    derniere = []
    for k in range(args.repete):
        if k:
            time.sleep(args.intervalle)
        derniere = transaction(port, trame, args, t0)
        nb_ok += any(crc_ok(r) for r in derniere)
    if args.repete > 1:
        print(f"Bilan : {nb_ok}/{args.repete} reponse(s) valide(s)")
    return derniere


# ------------------------------------------------------------------ commandes
def lister(_args=None):
    for p in list_ports.comports():
        vidpid = f"{p.vid:04X}:{p.pid:04X}" if p.vid is not None else "----:----"
        print(f"  {p.device:8} {vidpid}  {p.description}")


def cmd_ecoute(args):
    port, t0 = ouvre(args), time.monotonic()
    print(f"Ecoute de {port.port} a {args.debit} bauds (Ctrl+C pour arreter)")
    try:
        while True:
            for trame in lit_trames(port, 3600, args.silence):
                affiche("   ", trame, t0)
    except KeyboardInterrupt:
        pass


def cmd_envoi(args):
    trame = lit_hexa(args.trame)
    rafale(ouvre(args), trame if args.brut else avec_crc(trame), args)


def cmd_lire(args):
    recues = rafale(ouvre(args), avec_crc(bytes((args.id, 3, 0, 1, 0, 16))), args)
    for r in recues:
        if crc_ok(r) and r[1] == 3 and len(r) == 5 + 32:
            etats = [r[3 + 2 * k] << 8 | r[4 + 2 * k] for k in range(16)]
            print("Sorties : " + " ".join(f"{k + 1}:{'open' if e else 'close'}" for k, e in enumerate(etats)))
            print("(open = sortie au niveau BAS, cavalier M0 deconnecte : PROTOCOLE_MODBUS.md 8, piege 1)")


def cmd_relais(args):
    if args.ordre not in ORDRES:
        sys.exit(f"Ordre inconnu {args.ordre!r} : {', '.join(ORDRES)}")
    if not 0 <= args.canal <= 16:
        sys.exit("Canal 0 (tous) a 16")
    req = bytes((args.id, 6, 0, args.canal, ORDRES[args.ordre], args.tempo))
    rafale(ouvre(args), avec_crc(req), args)


def cmd_debit(args):
    """Lecture d'adresse en diffusion (FF 03 00 FF 00 01) a chaque debit."""
    requete = avec_crc(bytes((0xFF, 3, 0, 0xFF, 0, 1)))
    t0, trouve = time.monotonic(), False
    for d in DEBITS_ESSAYES:
        print(f"--- {d} bauds")
        port = ouvre(args, d)
        for r in transaction(port, requete, args, t0):
            if crc_ok(r) and r[1] == 3 and len(r) == 7:
                print(f">>> Carte trouvee : {d} bauds, adresse {r[3] << 8 | r[4]}")
                trouve = True
        port.close()
    if not trouve:
        print("Aucune reponse : cablage A/B, masse, alimentation de la carte, ou plusieurs esclaves sur le bus.")


# ------------------------------------------------------------------ esclave emule
class CarteRelaisEmulee:
    """Repond comme la carte 16 relais (PROTOCOLE_MODBUS.md, section 8)."""

    def __init__(self, ident, debit):
        self.id = ident
        self.code_debit = next((c for c, d in CODES_DEBIT.items() if d == debit), 4)
        self.sorties = [0] * 16

    def reponse(self, trame):
        """Reponse a une requete, ou None (la vraie carte se tait sur l'invalide)."""
        if not crc_ok(trame) or len(trame) != 8:
            return None
        ident, fc, reg, val = trame[0], trame[1], trame[2] << 8 | trame[3], trame[4] << 8 | trame[5]
        if fc == 3 and ident == 0xFF and reg == 0x00FF:
            return avec_crc(bytes((self.id, 3, 2, 0, self.id)))
        if ident != self.id:
            return None
        if fc == 3:
            if reg in (0x00FE, 0x00FF) and val == 1:
                v = self.code_debit if reg == 0x00FE else self.id
                return avec_crc(bytes((self.id, 3, 2, 0, v)))
            if 1 <= reg and val >= 1 and reg + val - 1 <= 16:
                regs = b"".join(bytes((0, s)) for s in self.sorties[reg - 1:reg - 1 + val])
                return avec_crc(bytes((self.id, 3, 2 * val)) + regs)
            return None
        if fc == 6 and reg <= 16 and self.applique(reg, trame[4]):
            return bytes(trame)       # la carte renvoie la requete en echo
        return None

    def applique(self, canal, ordre):
        cibles = range(16) if canal == 0 else [canal - 1]
        if ordre in (7, 8):
            self.sorties = [1 if ordre == 7 else 0] * 16
        elif ordre == 4 and canal:                     # latch : seul ce canal ouvert
            self.sorties = [0] * 16
            self.sorties[canal - 1] = 1
        elif ordre in (1, 5, 6):                       # momentary / delay : vus ouverts
            for i in cibles:
                self.sorties[i] = 1
        elif ordre == 2:
            for i in cibles:
                self.sorties[i] = 0
        elif ordre == 3:
            for i in cibles:
                self.sorties[i] ^= 1
        else:
            return False
        return True


def cmd_esclave(args):
    port, t0 = ouvre(args), time.monotonic()
    carte = CarteRelaisEmulee(args.id, args.debit)
    print(f"Carte 16 relais emulee, adresse {args.id}, sur {port.port} a {args.debit} bauds (Ctrl+C pour arreter)")
    dernier_envoi = None
    try:
        while True:
            for trame in lit_trames(port, 3600, args.silence):
                if trame == dernier_envoi:
                    dernier_envoi = None      # echo de notre reponse : ne pas y repondre
                    continue
                affiche("<--", trame, t0)
                rep = carte.reponse(trame)
                if rep:
                    port.write(rep)
                    port.flush()
                    dernier_envoi = rep
                    affiche("-->", rep, t0)
                    print("            sorties : " + "".join(str(s) for s in carte.sorties))
    except KeyboardInterrupt:
        pass


def main():
    # Options communes rattachees a chaque commande : `lire --port COM12` comme `lire`.
    commun = argparse.ArgumentParser(add_help=False)
    commun.add_argument("--port", default="auto")
    commun.add_argument("--debit", type=int, default=19200)
    commun.add_argument("--id", type=int, default=1)
    commun.add_argument("--repete", type=int, default=1)
    commun.add_argument("--intervalle", type=float, default=0.5)
    commun.add_argument("--attente", type=float, default=0.5)
    commun.add_argument("--silence", type=float, default=0.02)
    p = argparse.ArgumentParser(description="Test ModBus RTU / RS485 depuis le PC (voir l'en-tete du script).")
    sous = p.add_subparsers(dest="commande", required=True)
    sous.add_parser("lister", parents=[commun]).set_defaults(f=lister)
    sous.add_parser("ecoute", parents=[commun]).set_defaults(f=cmd_ecoute)
    e = sous.add_parser("envoi", parents=[commun])
    e.add_argument("trame")
    e.add_argument("--brut", action="store_true", help="n'ajoute pas le CRC")
    e.set_defaults(f=cmd_envoi)
    sous.add_parser("lire", parents=[commun]).set_defaults(f=cmd_lire)
    r = sous.add_parser("relais", parents=[commun])
    r.add_argument("canal", type=int)
    r.add_argument("ordre")
    r.add_argument("--tempo", type=int, default=0)
    r.set_defaults(f=cmd_relais)
    sous.add_parser("debit", parents=[commun]).set_defaults(f=cmd_debit)
    sous.add_parser("esclave", parents=[commun]).set_defaults(f=cmd_esclave)
    args = p.parse_args()
    try:
        args.f(args)
    except serial.SerialException as exc:
        sys.exit(f"Port serie : {exc}")
    except ValueError as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
