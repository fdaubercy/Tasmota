r"""Banc de test du sniffeur ModBus et de ses modules, sur PC, sans materiel.

UTILISATION
    python outils_docs/scripts_python/test_sniffeur_modbus.py        (code de sortie 0 = vert)
    (Python de PlatformIO : il fournit pyserial)

CE QU'IL COUVRE
    decodeur_modbus     norme + dialectes carte 16 relais / ESP32, sur un persist de TEST ecrit ici
                        (les noms du vrai persist peuvent changer sans casser le banc) ; le vrai
                        persist du maitre n'est verifie que pour sa structure ;
    surveillance_modbus ecarts commande / releve (temps simule), collisions ;
    emulation_modbus    reponses des esclaves emules, valeurs editables ;
    debit_modbus        recherche puis correction sur un faux bus (carte a 9600 bauds, adresse 5) ;
    ecoute_udp          verdicts du numero d'ordre ; VRAI socket multicast, mais sur un groupe et un
                        port de TEST avec TTL 0 : rien ne sort du PC, 224.3.0.1:4000 n'est jamais vise
                        (un faux push y serait traite par le vrai maitre) ;
    sniffeur_modbus     echo local appris, accuse 0x06 garde, emulation, push UDP ;
    test_rs485_pc       CRC (exemples de PROTOCOLE_MODBUS.md), decoupage, loop:// ;
    tout le decodage    20 000 trames aleatoires et leurs troncatures : aucune exception.
Chaque groupe a ses TEMOINS, des cas qui doivent echouer (tasks/lessons.md, regle 7).

CE QU'IL NE TESTE PAS
    le bus reel et le convertisseur (timing, echo), la page web (JavaScript), le pare-feu Windows :
    voir l'onglet Aide du sniffeur, section « Essai sur le bus reel ».
"""

import json
import os
import random
import socket
import struct
import sys
import tempfile
import threading
import time
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import debit_modbus as db                   # noqa: E402
import decodeur_modbus as dm                # noqa: E402
import ecoute_udp as eu                     # noqa: E402
import emulation_modbus as em               # noqa: E402
import sniffeur_modbus as sm                # noqa: E402
import test_rs485_pc as rs                  # noqa: E402
from surveillance_modbus import Surveillance    # noqa: E402

RESULTATS = {"ok": 0, "ko": []}


def verifie(valeur, attendu, nom):
    if valeur == attendu:
        RESULTATS["ok"] += 1
    else:
        RESULTATS["ko"].append(f"{nom} : obtenu {valeur!r}, attendu {attendu!r}")


def c(texte):
    """Hexa sans CRC -> trame complete."""
    return rs.avec_crc(bytes.fromhex(texte.replace(" ", "")))


# ------------------------------------------------------------------ persist de test
def persist_de_test():
    def app(nom, typ, ident, id_modbus, virtuel, **plus):
        return dict(nom=nom, type=typ, id=ident, idModBus=id_modbus, virtuel=virtuel, activation="ON", **plus)
    relais = {f"relai{k + 4}": app(f"Sortie {k + 1}", 256, k + 4, k + 1, "ModBus_Conn16channel1") for k in range(16)}
    relais.update(relai1=app("LEDs", 1376, 1, 1, "ModBus_TasmotaSlaveModBus1"),
                  relai2=app("Porte", 256, 2, 1, "ModBus_TasmotaSlaveModBus2"))
    d = {"drivers": {"ModBus": {"debit": 19200, "mode": "8N1", "environnement": {
            "Conn16channels": {"log": "info", "Conn16channel1": {"id": 1, "name": "Carte relais"}},
            "TasmotaSlaveModBus": {"TasmotaSlaveModBus1": {"id": 2, "name": "Cuve"},
                                   "TasmotaSlaveModBus2": {"id": 3, "name": "Rideau"}}}}},
         "modules": {"garage": {"environnement": {
             "relais": relais,
             "interrupteurs": {"interrupteur1": app("Fin de course", 160, 1, 1, "ModBus_TasmotaSlaveModBus2", SwitchMode=2)},
             "thermometres": {"thermometre1": app("Eau", 1312, 1, 1, "ModBus_TasmotaSlaveModBus1")},
             "analogiques": {"analogique1": app("Niveau", 4704, 1, 1, "ModBus_TasmotaSlaveModBus1")}}}}}
    chemin = os.path.join(tempfile.mkdtemp(prefix="banc_sniffeur_"), "_persist.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(d, f)
    return chemin


PERSIST = persist_de_test()
CARTE, TYPES = dm.charge_carte(PERSIST), dm.charge_types_gpio()


def decode(trame, requete=None):
    return dm.decode(c(trame) if isinstance(trame, str) else trame, c(requete) if requete else None, CARTE, TYPES)


# ------------------------------------------------------------------ tests
def test_crc_et_cli():
    verifie(rs.hexa(c("01 06 00 01 01 00")), "01 06 00 01 01 00 D9 9A", "CRC : canal 1 Open (doc)")
    verifie(rs.hexa(c("01 03 00 01 00 10")), "01 03 00 01 00 10 15 C6", "CRC : releve 16 sorties (doc)")
    verifie(rs.hexa(c("FF 03 00 FF 00 01")), "FF 03 00 FF 00 01 A1 E4", "CRC : adresse en diffusion (doc)")
    verifie(dm.crc_ok(dm.lit_texte("ModbusPushUDP 5 0310 00A0 0001 02 00FF E7D0")), True, "CRC : push UDP (doc)")
    verifie(rs.crc_ok(bytes.fromhex("010600010100D99B")), False, "TEMOIN : CRC faux refuse")
    req, rep = c("01 03 00 01 00 10"), em.CarteRelaisEmuleeVue(CARTE[1], 19200).reponse(c("01 03 00 01 00 10"))
    verifie(rs.decoupe(req + rep), [req, rep], "decoupage d'une requete et d'une reponse collees")
    verifie(rs.decoupe(req + b"\x12\x34"), [req, b"\x12\x34"], "decoupage : residu rendu tel quel")
    port = rs.serial.serial_for_url("loop://", timeout=0)
    a = types.SimpleNamespace(attente=0.15, silence=0.02, repete=1, intervalle=0.05)
    verifie(rs.rafale(port, req, a), [], "CLI : echo local d'une lecture retire")
    verifie(rs.rafale(port, c("01 06 00 01 03 00"), a), [c("01 06 00 01 03 00")],
            "CLI : copie unique d'une 0x06 gardee comme accuse (bug d'echo corrige)")


def test_decodeur():
    verifie(sorted(CARTE), [1, 2, 3], "carte du persist de test")
    vraie = dm.charge_carte()
    verifie(bool(vraie) and all(e["driver"] in ("conn16", "esp32") for e in vraie.values()), True,
            "vrai persist du maitre : structure lisible")
    verifie(dm.lit_bus(PERSIST)["debit"], 19200, "debit du bus lu dans le persist")
    verifie("Sortie 3" in decode("01 06 00 03 01 00")["metier"], True, "carte : canal 3 nomme")
    verifie("relai ON" in decode("01 06 00 03 01 00")["metier"], True, "carte : Open = relai ON (Relais_i)")
    r = decode("01 03 20 " + " ".join("00 01" if k == 2 else "00 00" for k in range(16)), "01 03 00 01 00 10")
    verifie("Sortie 3" in r["metier"], True, "carte : releve, sortie 3 ON")
    verifie("INVALIDE" in decode("01 06 00 01 09 00")["metier"], True, "carte : ordre invalide signale")
    verifie("19200" in decode("01 03 02 00 04", "01 03 00 FE 00 01")["metier"], True, "carte : debit relu")
    verifie("Power1 ON" in decode("03 06 01 00 02 00")["metier"], True, "ESP32 : 0x06 02 = Power ON")
    b = bytes.fromhex("030601010100")
    r = dm.decode(b + dm.crc16(b).to_bytes(2, "little"), carte=vraie)["metier"]
    verifie("Power2 OFF (POWER3 du maitre)" in r, True, "ESP32 : Power de l'esclave + POWER du maitre (WS2812 comptee)")
    verifie("inverse apres 10 s" in decode("03 06 01 00 01 0A")["metier"], True, "ESP32 : delai d'inversion")
    verifie("OFF (SwitchMode 2)" in decode("03 02 01 01", "03 02 00 A0 00 01")["metier"], True, "ESP32 : SwitchMode 2")
    f = struct.pack(">f", 21.5).hex()
    verifie("21.50" in decode("02 04 04 " + f, "02 04 05 20 00 02")["metier"], True, "ESP32 : float gros-boutien")
    verifie("12345" in decode("02 04 04 00 00 30 39", "02 04 12 60 00 02")["metier"], True, "ESP32 : uint32")
    verifie("HSBColor" in decode("02 10 05 60 00 03 06 00 78 00 64 00 32")["metier"], True, "ESP32 : WS2812")
    verifie("PUSH" in dm.decode(dm.lit_texte("ModbusPushUDP 5 0310 00A0 0001 02 00FF E7D0"), None, CARTE, TYPES)["metier"],
            True, "push UDP colle depuis un log")
    verifie(decode("03 83 02", "03 03 00 01 00 01")["nature"], "exception", "exception")
    verifie("non vue" in decode("03 01 01 01")["metier"], True, "reponse sans sa requete")
    verifie(dm.decode(bytes.fromhex("010600010100D99B"), None, CARTE, TYPES)["nature"], "ko", "TEMOIN : CRC faux")
    verifie("absente" in decode("09 03 00 01 00 01")["metier"], True, "TEMOIN : adresse hors persist")


def test_fuzz():
    random.seed(1)
    for _ in range(20000):
        b = bytes([random.choice([1, 2, 3, 0xFF, random.randrange(256)]),
                   random.choice([1, 2, 3, 4, 5, 6, 15, 16, 0x83, 0x11, random.randrange(256)])])
        b += bytes(random.randrange(256) for _ in range(random.randrange(0, 38)))
        if random.random() < 0.7:
            b = rs.avec_crc(b)
        req = c(f"{b[0]:02X} {b[1] & 0x7F:02X} 00 {random.randrange(256):02X} 00 02") if random.random() < 0.5 else None
        for t in (b, b[:random.randrange(0, len(b) + 1)]):
            try:
                dm.decode(t, req, CARTE, TYPES)
            except Exception as erreur:
                RESULTATS["ko"].append(f"fuzz : {rs.hexa(t)} -> {erreur!r}")
                return
    RESULTATS["ok"] += 1


def suite(sv, trames, t0):
    """[(hexa ou bytes, source, dt)] -> alertes ; temps simule."""
    t, req, tout = t0, None, []
    for h, source, dt in trames:
        t += dt
        trame = c(h) if isinstance(h, str) else h
        nat = dm.nature(trame, req)
        req = trame if nat == "requete" else (None if nat in ("reponse", "exception") else req)
        tout += sv.observe(trame, nat, source, t)
    return tout


def test_surveillance():
    rel = lambda canal, v: "01 03 20 " + " ".join(("00 01" if v else "00 00") if k == canal - 1 else "00 00" for k in range(16))  # noqa: E731
    lit = "01 03 00 01 00 10"
    sv = Surveillance(CARTE, 1.0)
    suite(sv, [("01 06 00 03 01 00", "bus", 0), ("01 06 00 03 01 00", "bus", .05)], 0)
    verifie(suite(sv, [(lit, "bus", 0), (rel(3, 1), "bus", .05)], 5), [], "TEMOIN : releve conforme, pas d'ecart")
    a = suite(sv, [(lit, "bus", 0), (rel(3, 0), "bus", .05)], 35)
    verifie([x["type"] for x in a], ["ecart"], "ecart au 1er releve contraire")
    verifie(suite(sv, [(lit, "bus", 0), (rel(3, 0), "bus", .05)], 65), [], "ecart signale une seule fois")
    verifie([x["niveau"] for x in suite(sv, [(lit, "bus", 0), (rel(3, 1), "bus", .05)], 95)], ["info"], "retour conforme")
    verifie(suite(Surveillance(CARTE, 1.0), [("01 06 00 03 01 00", "bus", 0), (lit, "bus", 2), (rel(3, 0), "bus", .05)], 0),
            [], "commande non accusee : pas suivie")
    sv = Surveillance(CARTE, 1.0)
    suite(sv, [("01 06 00 05 06 02", "bus", 0), ("01 06 00 05 06 02", "bus", .05)], 0)
    verifie(suite(sv, [(lit, "bus", 0), (rel(5, 1), "bus", .05)], .5), [], "Delay : open avant la tempo")
    verifie(suite(sv, [(lit, "bus", 0), (rel(5, 1), "bus", .05)], 2), [], "Delay : pas de verdict pres de l'inversion")
    verifie(suite(sv, [(lit, "bus", 0), (rel(5, 0), "bus", .05)], 5), [], "Delay : close apres la tempo")
    sv = Surveillance(CARTE, 1.0)
    suite(sv, [("03 06 01 00 02 05", "bus", 0), ("03 06 01 00 02 05", "bus", .05)], 0)
    verifie(suite(sv, [("03 01 01 00 00 01", "bus", 0), ("03 01 01 01", "bus", .05)], 1), [], "ESP32 : ON avant le delai")
    verifie(len(suite(sv, [("03 01 01 00 00 01", "bus", 0), ("03 01 01 01", "bus", .05)], 8)), 1, "ESP32 : ON apres le delai -> ecart")
    collision = lambda trames: [x["type"] for x in suite(Surveillance(CARTE, 1.0), trames, 0)]      # noqa: E731
    verifie(collision([("02 04 05 20 00 02", "bus", 0), (lit, "bus", .1)]), ["collision"], "deux requetes sans reponse")
    verifie(collision([("02 04 05 20 00 02", "pc", 0), ("02 04 05 20 00 02", "pc", .1)]), [], "TEMOIN : rafale du PC seul")
    verifie(collision([("02 04 05 20 00 02", "bus", 0), (lit, "bus", 1.5)]), [], "TEMOIN : requete apres le delai")
    verifie(collision([("03 01 01 01", "bus", 0)]), ["collision"], "reponse sans requete")
    verifie(collision([("03 01 01 00 00 01", "bus", 0), ("02 01 01 01", "bus", .05)]), ["collision"], "reponse d'un autre esclave")
    ko = bytes.fromhex("0103000100101500")
    verifie(collision([(ko, "bus", 0)]), [], "TEMOIN : un seul CRC faux")
    verifie(collision([(ko, "bus", 0), (ko, "bus", .5)]), ["collision"], "rafale de CRC faux")


def test_emulation():
    emu = em.Emulation(CARTE, 19200)
    emu.active(1, True), emu.active(2, True), emu.active(3, True)
    emu.modifie(3, 160, "etat", "ON")
    verifie("-> ON" in dm.decode(emu.reponse(c("03 02 00 A0 00 01")), c("03 02 00 A0 00 01"), CARTE, TYPES)["metier"], True,
            "interrupteur ON + SwitchMode 2 : le maitre lit ON")
    emu.modifie(2, 1312, "valeur", "18.25")
    verifie("18.25" in dm.decode(emu.reponse(c("02 04 05 20 00 02")), c("02 04 05 20 00 02"), CARTE, TYPES)["metier"], True,
            "temperature editable")
    verifie(emu.reponse(c("03 06 01 00 02 01")), c("03 06 01 00 02 01"), "0x06 : echo")
    verifie(emu.reponse(c("03 01 01 00 00 01")), c("03 01 01 01"), "Power ON apres la commande")
    time.sleep(1.2)
    verifie(emu.reponse(c("03 01 01 00 00 01")), c("03 01 01 00"), "inversion apres le delai de 1 s")
    verifie(emu.reponse(c("03 01 01 05 00 01")), None, "TEMOIN : registre inconnu -> silence")
    verifie(emu.reponse(c("FF 03 00 FF 00 01")), c("01 03 02 00 01"), "diffusion -> carte relais emulee")
    try:
        emu.modifie(3, 160, "valeur", 3)
        RESULTATS["ko"].append("TEMOIN : champ non modifiable accepte")
    except ValueError:
        RESULTATS["ok"] += 1


class FauxBus:
    """Port serie : carte relais a 9600 bauds, adresse 5 ; ses reponses repassent par sniffeur.traite."""
    def __init__(self, sniffeur, echo=False, carte=True):
        self.baudrate, self.ecrit, self.sn, self.echo, self.carte = 19200, [], sniffeur, echo, carte
        sniffeur.port = self

    def write(self, b):
        b = bytes(b)
        self.ecrit.append((self.baudrate, b))
        rep = None
        if self.carte and self.baudrate == 9600:
            rep = {c("FF 03 00 FF 00 01"): c("05 03 02 00 05"), c("05 03 00 FE 00 01"): c("05 03 02 00 03")}.get(b)
            rep = b if b[:2] == bytes((5, 6)) else rep
        envois = ([b] if self.echo else []) + ([rep] if rep else [])
        if envois:
            threading.Timer(0.05, lambda: [self.sn.traite(x, "bus") for x in envois]).start()

    def flush(self):
        pass

    def reset_input_buffer(self):
        pass


def sniffeur(**options):
    a = dict(persist=PERSIST, journal=None, historique=500, debit=19200, delai=1.0, http=0, silence=0.02, echo="auto")
    a.update(options)
    return sm.Sniffeur(types.SimpleNamespace(**a))


def test_sniffeur_et_debit():
    sn = sniffeur()
    bus = FauxBus(sn)
    sn.envoie(c("01 03 00 01 00 10"))
    time.sleep(0.4)
    sn.verifie_attente()
    verifie(sn.echo_local, False, "echo local appris : absent")
    sn.envoie(c("02 06 00 01 02 00"))
    sn.traite(c("02 06 00 01 02 00"), "bus")
    verifie(sn.stats[2]["reponses"], 1, "accuse 0x06 identique a l'envoi : garde")
    sn2 = sniffeur()
    FauxBus(sn2, echo=True)
    sn2.envoie(c("01 03 00 01 00 10"))
    time.sleep(0.2)
    verifie(sn2.echo_local, True, "TEMOIN : echo local appris : present")
    cible = sn.cible_conn16()
    verifie(cible, {"debit": 19200, "id": 1}, "cible lue dans le persist")
    r = db.cherche(sn, cible)
    verifie((r["debit"], r["adresse"], r["code"], len(r["ecarts"])), (9600, 5, 3, 2), "carte trouvee a 9600, adresse 5")
    verifie(bus.baudrate, 19200, "debit restaure apres la recherche")
    bus.ecrit.clear()
    db.corrige(sn, r, cible)
    verifie([x for x in bus.ecrit], [(9600, c("05 06 00 FE 00 04")), (9600, c("05 06 00 FF 00 01"))],
            "correction : debit puis adresse, au debit et a l'adresse trouves")
    verifie(bus.baudrate, 19200, "debit restaure apres la correction")
    bus.carte = False
    verifie(db.cherche(sn, cible), None, "TEMOIN : aucune carte -> rien trouve")
    sn3 = sniffeur(echo="oui")
    bus3 = FauxBus(sn3)
    sn3.emulation.active(3, True)
    sn3.traite(c("03 02 00 A0 00 01"), "bus")
    verifie(bus3.ecrit[-1][1], c("03 02 01 01"), "emulation : le sniffeur repond a la place du rideau")
    verifie(sn3.stats[3]["reponses"], 1, "emulation : reponse appariee")


def test_udp():
    derniers = {}
    verifie(eu.juge_seq(derniers, 3, 5)[0], True, "seq : premier push accepte")
    verifie("perdu" in eu.juge_seq(derniers, 3, 8)[1], True, "seq : trou -> push perdus")
    verifie(eu.juge_seq(derniers, 3, 8)[0], False, "TEMOIN : doublon ecarte")
    verifie(eu.juge_seq(derniers, 3, 7)[0], False, "TEMOIN : datagramme en retard ecarte")
    verifie("redemarrage" in eu.juge_seq(derniers, 3, 1)[1], True, "seq 1 apres 8 : redemarrage")
    verifie(eu.analyse("ImAlive esclave3"), None, "autre message du groupe : pas un push")
    verifie(eu.analyse("ModbusPushUDP 031000A00001020 0FF")[0], None, "ancien format sans seq")
    sn = sniffeur(echo="oui")
    push = "ModbusPushUDP 4 " + c("03 10 00 A0 00 01 02 00 FF").hex().upper()
    # vrai socket : groupe et port de TEST, TTL 0 (le datagramme ne quitte pas le PC)
    port = random.randrange(40000, 60000)
    ecoute = eu.EcouteUDP(sn.traite_udp, "239.255.77.77", port, "127.0.0.1")
    if not ecoute.demarre():
        RESULTATS["ko"].append(f"UDP : {ecoute.erreur}")
        return
    emetteur = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    emetteur.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 0)
    emetteur.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton("127.0.0.1"))
    for message in (push, push, "ImAlive esclave3"):
        emetteur.sendto(message.encode(), ("239.255.77.77", port))
    fin = time.monotonic() + 3
    while time.monotonic() < fin and (sn.nb_push < 2 or len(sn.historique) < 4):
        time.sleep(0.05)
    ecoute.arrete()
    emetteur.close()
    verifie(sn.nb_push, 2, "UDP multicast recu (2 push)")
    verifie((sn.stats[3]["push"], sn.stats[3]["push_ecartes"]), (2, 1), "UDP : le doublon est compte ecarte")
    natures = [json.loads(p.decode().split("data: ", 1)[1])["nature"] for p in sn.historique]
    verifie(natures.count("push") == 2 and "udp" in natures, True, "UDP : push et autre message dans le fil")


def main():
    for groupe in (test_crc_et_cli, test_decodeur, test_fuzz, test_surveillance, test_emulation,
                   test_sniffeur_et_debit, test_udp):
        avant = len(RESULTATS["ko"])
        try:
            groupe()
        except Exception as erreur:
            RESULTATS["ko"].append(f"{groupe.__name__} : exception {erreur!r}")
        print(f"{groupe.__name__:28} {'OK' if len(RESULTATS['ko']) == avant else 'ECHEC'}")
    for echec in RESULTATS["ko"]:
        print("  ECHEC", echec)
    print(f"BANC_SNIFFEUR: {'OK' if not RESULTATS['ko'] else 'ECHEC'} ({RESULTATS['ok']} verifications, {len(RESULTATS['ko'])} echec(s))")
    sys.stdout.flush()
    os._exit(0 if not RESULTATS["ko"] else 1)       # fils des minuteries : sortie sans attendre


if __name__ == "__main__":
    main()
