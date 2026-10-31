r"""Banc de test du sniffeur I2C et de ses modules, sur PC, sans materiel.

UTILISATION
    %USERPROFILE%\.platformio\penv\Scripts\python.exe outils_docs/scripts_python/outils_pc/test_sniffeur_i2c.py
    (code de sortie 0 = vert ; Python de PlatformIO : il fournit pyserial)

CE QU'IL COUVRE
    protocole      chaque type de ligne, lignes illisibles (jamais d'exception), ligne coupee en deux lectures,
                   bornes des ordres ;
    decodeur       puces du parc sur des trames tirees des FICHES TECHNIQUES (PROVISOIRE : a remplacer par des
                   captures reelles du sniffeur, plan sniffeur-i2c A8), ambiguites d'adresse, puces d'une carte
                   lues dans un persist de TEST ecrit ici (le vrai depot n'est verifie que pour sa structure) ;
    alertes        NACK repetes, tronquee, debordement, pertes, bus bloque ;
    sniffeur       historique borne (100 000 lignes), rapprochement ordre <-> trame, trame non vue, carte
                   injoignable, un ordre a la fois, mode maitre (reponse, refus, port ferme), port perdu, journal ;
    sonde du port  un faux port qui repond « I » est retenu, un port muet ou fermé est ecarte ;
    HTTP           page, routes, en-tete X-Sniffeur, apercu sans envoi, ecriture non confirmee refusee.
Chaque groupe a ses TEMOINS (cas qui doivent echouer).

CE QU'IL NE TESTE PAS
    le firmware (banc C++ : outils_docs/firmware_sniffeur_i2c/banc/lance_banc.py), le bus reel, la page dans un
    navigateur (test_sniffeur_i2c_page_chrome.py).
"""

import json
import os
import socket
import sys
import tempfile
import threading
import time
import types
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["OUTILS_TASMOTA_DOSSIER"] = tempfile.mkdtemp(prefix="banc_sniffeur_i2c_")   # jamais le vrai dossier
import decodeur_i2c as di                                   # noqa: E402
import sniffeur_i2c as si                                   # noqa: E402
import sniffeur_i2c_carte as sc                             # noqa: E402
import sniffeur_i2c_protocole as proto                      # noqa: E402
from sniffeur_i2c_alertes import NACK_REPETES, Alertes      # noqa: E402
from sniffeur_i2c_http import fabrique_gestionnaire         # noqa: E402

ECHECS = []


def verifie(valeur, attendu, nom):
    if valeur != attendu:
        ECHECS.append(nom)
        print(f"  ECHEC {nom} : {valeur!r} au lieu de {attendu!r}")


def contient(texte, morceau, nom):
    if morceau not in str(texte):
        ECHECS.append(nom)
        print(f"  ECHEC {nom} : {morceau!r} absent de {texte!r}")


def X(a, rw, d="-", nack="-", fin="STOP", f="99.5", t=1000):
    return f"X t={t} a={a:02X} rw={rw} d={d} nack={nack} fin={fin} f={f}"


def tr(a, rw, d=b"", nack=None, fin="STOP"):
    return {"type": "X", "t": 0, "a": a, "rw": rw, "d": bytes(d), "nack": nack, "fin": fin, "f": 99.5, "trop": 0}


# ---------------------------------------------------------------------------------------------- protocole
def test_protocole():
    lu = proto.lit_ligne("X t=123 a=48 rw=W d=01C383 nack=- fin=STOP f=99.8")
    verifie((lu["a"], lu["rw"], lu["d"], lu["nack"], lu["fin"], lu["f"], lu["trop"]),
            (0x48, "W", b"\x01\xc3\x83", None, "STOP", 99.8, 0), "X complete")
    verifie(proto.lit_ligne("X t=1 a=77 rw=W d=- nack=0 fin=STOP f=0.0 trop=3")["trop"], 3, "X trop")
    verifie(proto.lit_ligne("X t=1 a=77 rw=W d=- nack=0 fin=STOP f=0.0")["nack"], 0, "X nack adresse")
    verifie(proto.lit_ligne("I v=1 puce=esp32s3 sda=4 scl=5 mode=ecoute ech=12")["ech"], 12, "I")
    verifie(proto.lit_ligne("P n=7"), {"type": "P", "n": 7}, "P")
    verifie(proto.lit_ligne("B sda=bas ms=60")["ms"], 60, "B")
    verifie(proto.lit_ligne("M ok=1 d=C383")["d"], b"\xc3\x83", "M ok")
    verifie(proto.lit_ligne("M ok=0 err=bus_actif")["err"], "bus_actif", "M refus")
    # TEMOINS : illisibles -> None, jamais d'exception
    for mauvaise in ("", "bonjour", "X t=1 a=48", "X t=1 a=80 rw=W d=- nack=- fin=STOP f=0",
                     "X t=1 a=48 rw=Q d=- nack=- fin=STOP f=0", "X t=1 a=48 rw=W d=0 nack=- fin=STOP f=0",
                     "X t=1 a=48 rw=W d=- nack=- fin=FIN f=0", "P n=x", "I v=1", "Xx t=1", "X t=1 a=48 rw"):
        verifie(proto.lit_ligne(mauvaise), None, f"illisible {mauvaise!r}")
    lignes = proto.Lignes()
    verifie(lignes.ajoute(b"X t=1 a=48 rw=W d=01 nack=- fi"), [], "ligne coupee : rien avant la fin")
    verifie(lignes.ajoute(b"n=STOP f=1\nP n=1\n\nP n="), ["X t=1 a=48 rw=W d=01 nack=- fin=STOP f=1", "P n=1"],
            "ligne coupee recollee")
    lignes.ajoute(b"z" * (proto.Lignes.LONGUEUR_MAX + 1))
    verifie(lignes.reste, b"", "flux sans fin de ligne jete")
    verifie(proto.ordre("?"), b"?\n", "ordre ?")
    verifie(proto.ordre("MWR", 0x48, b"\x01", 2), b"MWR a=48 d=01 n=2\n", "ordre MWR")
    for nom, a, d, n in (("MW", 0x02, b"\x01", 0), ("MW", 0x78, b"\x01", 0), ("MW", 0x48, b"", 0),
                         ("MR", 0x48, b"", 0), ("MR", 0x48, b"", 33), ("XX", 0x48, b"", 1)):
        try:
            proto.ordre(nom, a, d, n)
            ECHECS.append(f"ordre {nom} {a:02X} accepte")
            print(f"  ECHEC ordre {nom} 0x{a:02X} {d!r} {n} accepte")
        except ValueError:
            pass


# ---------------------------------------------------------------------------------------------- decodeur
PERSIST_TEST = {
    "drivers": {"I2C": {"environnement": {
        "ADS1115": {"activation": "OFF", "adresseI2C": "0x48"},
        "TCA9554": {"activation": "ON", "adresseI2C": "0x20"},
        "MCP23017": {"activation": "OFF", "adresseI2C": "0x20"},
        "DS3231": {"activation": "ON", "adresseI2C": "0x68"}}}},
    "modules": {"capteurs": [{"virtuel": "I2C_ADS1115"}, {"virtuel": "ONEWIRE"}]},
    "volets": {"1": {"inclinaison": {"adresse": "0x69"}}},
}


def test_decodeur():
    puces = di.puces_carte(PERSIST_TEST)
    verifie(sorted(puces), ["ADS1115", "DS3231", "MPU6050", "TCA9554"], "puces de la carte")
    verifie(puces["TCA9554"], [0x20], "adresse lue dans le persist")
    verifie(puces["ADS1115"], list(range(0x48, 0x4C)), "virtuel sans adresse : toutes les adresses de la puce")
    verifie(puces["MPU6050"], [0x69], "inclinaison : adresse du volet")
    verifie(di.candidats(0x20), (["MCP23017", "TCA9554"], True), "0x20 sans carte = ambigu")
    verifie(di.candidats(0x20, puces), (["TCA9554"], False), "0x20 avec la carte = TCA9554")
    verifie(di.candidats(0x68, puces), (["DS3231"], False), "0x68 avec la carte = DS3231")
    verifie(di.candidats(0x50, puces), ([], True), "adresse inconnue")
    verifie(di.candidats(0x18, puces), (["ES8311"], True), "puce non declaree sur la carte : a confirmer")

    d = di.Decodeur()                                       # ADS1115, fiche technique (PROVISOIRE)
    r = d.decode(tr(0x48, "W", b"\x01\xc3\x83"))
    verifie((r["puce"], r["ambigu"], r["registre"]), ("ADS1115", False, "Config"), "ADS1115 config")
    for morceau in ("AIN0-GND", "PGA=±4.096 V", "unique", "128 SPS", "comparateur=coupe"):
        contient(r["texte"], morceau, f"ADS1115 config {morceau}")
    verifie(d.decode(tr(0x48, "W", b"\x00"))["texte"], "pointeur -> Conversion", "ADS1115 pointeur")
    contient(d.decode(tr(0x48, "R", b"\x7f\xff"))["texte"], "32767 = 4095.9 mV", "ADS1115 conversion en mV")
    contient(d.decode(tr(0x48, "R", b"\x80\x00"))["texte"], "-32768", "ADS1115 conversion negative")
    contient(di.Decodeur().decode(tr(0x49, "R", b"\x12\x34"))["texte"], "registre inconnu", "lecture sans pointeur")

    d = di.Decodeur({"MCP23017": [0x20]})
    r = d.decode(tr(0x20, "W", b"\x12\x05\x80"))                # GPIOA puis GPIOB (auto-increment)
    contient(r["texte"], "GPIOA=0b00000101 -> haut : A0 A2", "MCP23017 GPIOA")
    contient(r["texte"], "GPIOB=0b10000000 -> haut : B7", "MCP23017 GPIOB auto-increment")
    contient(d.decode(tr(0x20, "W", b"\x00\xff"))["texte"], "entree : A0 A1 A2 A3 A4 A5 A6 A7", "MCP23017 IODIR")

    d = di.Decodeur({"TCA9554": [0x20]})
    contient(d.decode(tr(0x20, "W", b"\x01\x09"))["texte"], "Sorties=0b00001001 -> haut : P0 P3", "TCA9554 sorties")
    d.decode(tr(0x20, "W", b"\x00", fin="RESTART"))
    contient(d.decode(tr(0x20, "R", b"\x02\x02"))["texte"], "Entrees=0b00000010", "TCA9554 relu sans auto-increment")

    d = di.Decodeur({"DS3231": [0x68]})
    d.decode(tr(0x68, "W", b"\x00", fin="RESTART"))
    contient(d.decode(tr(0x68, "R", bytes([0x30, 0x59, 0x23, 0x05, 0x31, 0x10, 0x26])))["texte"],
             "2026-10-31 23:59:30", "DS3231 date 24 h")
    d.decode(tr(0x68, "W", b"\x00"))
    contient(d.decode(tr(0x68, "R", bytes([0, 0, 0x72, 1, 1, 1, 0x26])))["texte"], " 12:00:00", "DS3231 12 h midi")
    d.decode(tr(0x68, "W", b"\x00"))
    contient(d.decode(tr(0x68, "R", bytes([0, 0, 0x52, 1, 1, 1, 0x26])))["texte"], " 00:00:00", "DS3231 12 h minuit")
    d.decode(tr(0x68, "W", b"\x11"))
    contient(d.decode(tr(0x68, "R", b"\x19\x40"))["texte"], "temperature 25.25 °C", "DS3231 temperature")

    d = di.Decodeur({"MPU6050": [0x68]})
    contient(d.decode(tr(0x68, "W", b"\x6b\x00"))["texte"], "PWR_MGMT_1=0x00 (eveille)", "MPU6050 reveil")
    contient(d.decode(tr(0x68, "W", b"\x1c\x08"))["texte"], "±4 g", "MPU6050 plage accelerometre")
    d.decode(tr(0x68, "W", b"\x3b", fin="RESTART"))
    mesure = bytes([0x20, 0x00, 0, 0, 0xE0, 0x00, 0, 0, 0, 131, 0, 0, 0, 0])
    texte = d.decode(tr(0x68, "R", mesure))["texte"]
    for morceau in ("ax=1.000 g", "az=-1.000 g", "T=36.5 °C", "gx=1.0 °/s"):
        contient(texte, morceau, f"MPU6050 rafale {morceau}")
    d.decode(tr(0x68, "W", b"\x75", fin="RESTART"))
    contient(d.decode(tr(0x68, "R", b"\x68"))["texte"], "WHO_AM_I=0x68 = MPU6050", "MPU6050 WHO_AM_I")
    verifie(di.Decodeur().decode(tr(0x48, "W", nack=0))["texte"], "adresse non acquittee (rien ne repond)", "NACK adresse")
    contient(di.Decodeur().decode(tr(0x68, "R", b"\x00"))["texte"], "DS3231 ou MPU6050", "0x68 ambigu sans carte")
    verifie(di.Decodeur().decode(tr(0x50, "R", b"\x00"))["texte"], "puce inconnue a cette adresse", "puce inconnue")
    verifie(di.Decodeur().decode(tr(0x48, "W"))["texte"], "sonde (adresse seule)", "sonde")

    cartes = di.liste_cartes()                              # structure du vrai depot seulement
    verifie("data/cave/tasmota32s3-serveur-rly" in cartes, True, "vraie carte listee")
    verifie(any("sauvegarde" in c for c in cartes), False, "dossiers sauvegarde exclus")
    for mauvais in ("../../etc", "data/fs", "data/cave/inconnue"):
        try:
            di.charge_carte(di.RACINE, mauvais)
            ECHECS.append(f"carte {mauvais} acceptee")
        except ValueError:
            pass


# ---------------------------------------------------------------------------------------------- alertes
def test_alertes():
    al = Alertes()
    sorties = [al.transaction(tr(0x40, "W", nack=0)) for _ in range(NACK_REPETES + 2)]
    verifie([bool(s) for s in sorties], [False] * (NACK_REPETES - 1) + [True, False, False], "NACK repetes : une alerte")
    al.transaction(tr(0x40, "W", b"\x01"))
    verifie(bool(al.transaction(tr(0x40, "W", nack=0))), False, "NACK : compteur remis a zero par un ACK")
    contient(al.transaction(tr(0x41, "W", b"\x01", fin="TRONQUE")), "tronquee", "tronquee")
    contient(al.transaction(dict(tr(0x41, "W", b"\x01"), trop=5)), "5 octet", "debordement")
    contient(Alertes.pertes(3), "3 transaction", "pertes")
    contient(Alertes.bloque(60), "60 ms", "bus bloque")


# ---------------------------------------------------------------------------------------------- sniffeur
def nouveau_sniffeur(historique=100):
    return si.Sniffeur(types.SimpleNamespace(historique=historique, sans_journal=True, http=0, racine=di.RACINE))


class FauxPort:
    def __init__(self, reponses=None, panne=False):
        self.ecrit, self.reponses, self.panne, self.dtr, self.rts = [], list(reponses or []), panne, True, True

    def write(self, b):
        self.ecrit.append(b)

    def read(self, n):
        if self.panne:
            raise OSError("peripherique debranche")
        return self.reponses.pop(0) if self.reponses else b""

    @property
    def in_waiting(self):
        return 1

    def close(self):
        pass


def test_sniffeur():
    sn = nouveau_sniffeur(historique=50)
    sn.traite_lignes(["n'importe quoi", X(0x48, "W", "01C383"), "P n=2", "B sda=bas ms=70",
                      "I v=1 puce=esp32s3 sda=4 scl=5 mode=ecoute ech=12", "I v=9 puce=rp2040 sda=0 scl=1"])
    natures = [f["nature"] for f in sn.historique]
    verifie(natures, ["trame", "alerte", "alerte", "info", "alerte"], "natures des fiches")
    verifie((sn.illisibles, sn.perdues, sn.nb), (1, 2, 1), "compteurs")
    contient(sn.historique[-1]["texte"], "VERSION INCONNUE", "version de protocole inconnue")
    verifie(sn.stats[0x48]["ecritures"], 1, "statistiques par adresse")
    t0 = time.monotonic()
    for i in range(100):                                    # 100 000 lignes par lots de 1000
        sn.traite_lignes([X(0x20 + (j % 8), "R", "00", t=j) for j in range(1000)])
    verifie((len(sn.historique), sn.nb), (50, 100001), "historique borne, compteurs justes")
    verifie(sum(s["transactions"] for s in sn.stats.values()), 100001, "inventaire complet")
    print(f"  (100 000 lignes en {time.monotonic() - t0:.1f} s)")

    # rapprochement : la carte lit 0x48 registre 01 ; le bus montre la sonde, le pointeur, puis la lecture
    sn = nouveau_sniffeur()
    def carte_qui_lit(ip, commande):
        sn.traite_lignes([X(0x48, "W"), X(0x48, "W", "01", fin="RESTART"), X(0x48, "R", "C383")])
        return True, '{"Br":"50051"}'
    r = sn.ordre_carte("192.168.0.10", 0x48, 0x01, 2, envoie=carte_qui_lit)
    verifie((r["ok"], r["commande"]), (True, "Br (wire1.detect(0x48) ? wire1 : wire2).read(0x48, 0x01, 2)"), "ordre carte")
    vues = [f for f in sn.historique if f["nature"] == "reponse" and "trame vue" in f["texte"]]
    verifie(len(vues), 1, "trame vue (la sonde et le pointeur ne comptent pas)")
    contient(vues[0]["texte"] if vues else "", "[C3 83]", "trame vue : octets lus")
    # TEMOIN : lecture d'un AUTRE registre par le pilote de la carte -> pas de rapprochement, puis trame non vue
    sn = nouveau_sniffeur()
    sn.traite_lignes([X(0x48, "W", "00")])
    sn.ordre_carte("192.168.0.10", 0x48, 0x01, 2, envoie=lambda ip, c: (sn.traite_lignes([X(0x48, "R", "1234")]), (True, "ok"))[1])
    verifie(any("trame vue" in f["texte"] for f in sn.historique), False, "temoin : autre registre non rapproche")
    with sn.verrou:
        fiches = sn._expire(time.monotonic() + 3600)
    verifie(len(fiches), 1, "trame non vue")
    contient(fiches[0]["texte"] if fiches else "", "NON VUE", "trame non vue : texte")
    # carte injoignable
    ok, texte = sc.envoie("192.168.0.10", "Br 1", transport=lambda ip, c, d: (_ for _ in ()).throw(OSError("timed out")))
    verifie(ok, False, "carte injoignable : echec sans exception")
    contient(texte, "injoignable", "carte injoignable : texte")
    verifie(sc.envoie("192.168.0.999", "Br 1", transport=lambda *a: "x")[0], False, "IP invalide refusee")
    verifie(sc.verifie_ip("192.168.4.1:8081"), "192.168.4.1:8081", "IP:port du range extender")
    # un ordre a la fois
    sn.verrou_ordre.acquire()
    try:
        sn.ordre_carte("192.168.0.10", 0x48, 0, 2, envoie=lambda *a: (True, ""))
        ECHECS.append("deux ordres a la fois")
    except OSError:
        pass
    finally:
        sn.verrou_ordre.release()
    verifie(sc.commande_br(0x20, 0x01, 1, 0xFF), "Br (wire1.detect(0x20) ? wire1 : wire2).write(0x20, 0x01, 0xFF, 1)",
            "commande d'ecriture")
    for args in ((0x02, 0, 1, None), (0x48, 0x100, 1, None), (0x48, 0, 5, None), (0x48, 0, 1, 0x100)):
        try:
            sc.commande_br(*args)
            ECHECS.append(f"commande_br {args} acceptee")
        except ValueError:
            pass

    # mode maitre
    sn = nouveau_sniffeur()
    try:
        sn.ordre_maitre("MR", 0x48, n=2)
        ECHECS.append("ordre maitre port ferme accepte")
    except OSError:
        pass
    sn.port = FauxPort()
    threading.Timer(0.1, lambda: sn.traite_lignes(["M ok=1 d=C383"])).start()
    verifie(sn.ordre_maitre("MWR", 0x48, b"\x01", 2), {"ok": True, "d": "C3 83", "err": ""}, "ordre maitre : lecture")
    verifie(sn.port.ecrit, [b"MWR a=48 d=01 n=2\n"], "ordre maitre : trame ecrite")
    threading.Timer(0.1, lambda: sn.traite_lignes(["M ok=0 err=bus_actif"])).start()
    verifie(sn.ordre_maitre("MR", 0x48, n=1)["err"], "bus_actif", "ordre maitre : refus du firmware")

    # port perdu : la boucle ferme le port et le dit, sans s'arreter
    sn = nouveau_sniffeur()
    sn.port, sn.nom_port = FauxPort(panne=True), "COM99"
    threading.Thread(target=sn.boucle_lecture, daemon=True).start()
    for _ in range(50):
        if sn.port is None:
            break
        time.sleep(0.02)
    verifie(sn.port, None, "port perdu : ferme")
    contient(sn.erreur, "perdu", "port perdu : message")

    # journal : un fichier par jour, purge au-dela de 30 jours
    dossier = tempfile.mkdtemp(prefix="banc_journal_i2c_")
    vieux = os.path.join(dossier, "sniffeur_i2c_2000-01-01.log")
    open(vieux, "w").close()
    os.utime(vieux, (time.time() - 31 * 86400,) * 2)
    j = si.Journal(dossier)
    j.ecrit("essai")
    verifie(os.path.exists(vieux), False, "journal : vieux fichier purge")
    verifie(len(os.listdir(dossier)), 1, "journal : fichier du jour")


# ---------------------------------------------------------------------------------------------- sonde
def test_sonde():
    class Faux:
        def __init__(self, repond, panne=False):
            self.repond, self.panne, self.envoye = repond, panne, b""

        def open(self):
            if self.panne:
                raise OSError("acces refuse")

        def reset_input_buffer(self):
            pass

        def write(self, b):
            self.envoye += b

        def read(self, n):
            if self.repond and self.envoye == b"?\n":
                self.envoye = b"lu"
                return b"I v=1 puce=esp32s3 sda=4 scl=5 mode=ecoute ech=12\n"
            return b""

        def close(self):
            pass

    def fabrique(faux):
        return lambda *a, **k: faux

    verifie(si.sonde("COM1", fabrique(Faux(True))), True, "sonde : sniffeur reconnu")
    t0 = time.monotonic()
    verifie(si.sonde("COM2", fabrique(Faux(False))), False, "sonde : port muet ecarte")
    verifie(time.monotonic() - t0 < si.SONDE_S + 0.5, True, "sonde : attente bornee")
    verifie(si.sonde("COM3", fabrique(Faux(True, panne=True))), False, "sonde : port occupe ecarte")


# ---------------------------------------------------------------------------------------------- HTTP
def test_http():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    sn = nouveau_sniffeur()
    sn.args.http = port
    http = ThreadingHTTPServer(("127.0.0.1", port), fabrique_gestionnaire(sn))
    http.daemon_threads = True
    threading.Thread(target=http.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"

    def get(chemin):
        with urllib.request.urlopen(base + chemin, timeout=5) as r:
            return r.status, r.read().decode("utf-8")

    def post(chemin, corps, entete=True):
        req = urllib.request.Request(base + chemin, json.dumps(corps).encode(), method="POST",
                                     headers={"X-Sniffeur": "1"} if entete else {})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    try:
        statut, page = get("/")
        verifie(statut, 200, "page")
        contient(page, "<title>Sniffeur I2C</title>", "page : titre")
        contient(page, "Brancher le sniffeur", "page : aide inseree")
        verifie("data/cave/tasmota32s3-serveur-rly" in json.loads(get("/cartes")[1]), True, "/cartes")
        verifie(json.loads(get("/puces")[1])["ADS1115"]["registres"]["01"], "Config", "/puces")
        verifie(post("/raz", {}, entete=False)[0], 403, "POST sans X-Sniffeur refuse")
        statut, corps = post("/ordre", {"voie": "carte", "ip": "192.168.0.10", "a": "20", "reg": "01", "n": 1,
                                        "valeur": "FF", "apercu": True})
        verifie((statut, json.loads(corps).get("commande")),
                (200, "Br (wire1.detect(0x20) ? wire1 : wire2).write(0x20, 0x01, 0xFF, 1)"), "apercu sans envoi")
        verifie(len(sn.historique), 0, "apercu : rien envoye ni journalise")
        statut, corps = post("/ordre", {"voie": "carte", "ip": "192.168.0.10", "a": "20", "reg": "01", "n": 1, "valeur": "FF"})
        verifie(statut, 400, "ecriture non confirmee refusee")
        statut, corps = post("/ordre", {"voie": "maitre", "nom": "MR", "a": "48", "n": 2})
        verifie(statut, 400, "maitre sans « composant isole » refuse")
        contient(corps, "debranche", "maitre refuse : raison")
        statut, corps = post("/ordre", {"voie": "maitre", "nom": "MWR", "a": "48", "d": "01", "n": 2, "isole": True,
                                        "apercu": True})
        verifie(json.loads(corps).get("commande"), "MWR a=48 d=01 n=2", "apercu maitre")
        verifie(post("/ordre", {"voie": "maitre", "nom": "MR", "a": "48", "n": 2, "isole": True})[0], 409,
                "maitre port ferme : 409")
        statut, corps = post("/carte", {"carte": "data/cave/tasmota32s3-serveur-rly"})
        verifie("TCA9554" in json.loads(corps)["puces"], True, "/carte : puces de la carte")
        verifie(post("/carte", {"carte": "../secret"})[0], 400, "/carte hors depot refusee")
        sn.traite_lignes([X(0x20, "W", "0109")])
        contient(get("/export?format=txt")[1], "0x20 W [01 09]", "export txt")
        verifie(json.loads(get("/export?format=json")[1])[-1]["puce"], "TCA9554", "export json (carte choisie)")
    finally:
        http.shutdown()


def main():
    for groupe in (test_protocole, test_decodeur, test_alertes, test_sniffeur, test_sonde, test_http):
        print(groupe.__name__)
        groupe()
    print("ROUGE : " + ", ".join(ECHECS) if ECHECS else "VERT : sniffeur I2C")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
