r"""Banc de test du testeur UDP et de ses modules, sur PC, SANS port serie reel.

UTILISATION
    python outils_docs/scripts_python/outils_pc/test_testeur_udp.py        (code de sortie 0 = vert)
    (Python de PlatformIO : il fournit pyserial)

CE QU'IL COUVRE
    testeur_udp_essais   CRC16 ModBus et trame 020100E00001FC0F, commandes de chaque essai, preuves et
                         verdicts (RECU / EMIS NON RECU / NON EMIS / ECHEC / PAS DE RUBAN) sur des lignes de
                         log exactes ; reception d'un AUTRE message refusee ; tid different refuse ;
    testeur_udp_carte    decoupage en lignes (accents), masque du mot de passe, reouverture automatique
                         apres perte du port, avertissement « deja ouvert par un autre programme » ;
    testeur_udp          deux CARTES SIMULEES (classe Sim : repondent a Status 5, ReglageLog, ModeConnexion,
                         ReglageUDP, ReglageModbus...) reliees par un faux reseau : initialisation,
                         logs poses puis restaures (jamais mqtt / web / syslog), essais de bout en bout,
                         bascule de mode, mot de passe absent de la page et du journal ;
    testeur_udp_http     routes GET / POST sur un vrai serveur HTTP local (port aleatoire) ;
    acces reseau         jeton exige d'un autre appareil, ce PC inchange (test_testeur_udp_acces.py).
Chaque groupe a ses TEMOINS, des cas qui doivent echouer (tasks/lessons.md, regle 7).

CE QU'IL NE TESTE PAS
    les vraies cartes (format exact des logs, delais Wi-Fi, NAPT), le vrai port USB qui disparait, le
    JavaScript de la page.
"""

import json
import os
import queue
import sys
import tempfile
import threading
import time
import types
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import serial

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import testeur_udp as tu                    # noqa: E402
import testeur_udp_carte as tc              # noqa: E402
import testeur_udp_essais as te             # noqa: E402
import testeur_udp_http                     # noqa: E402
import test_testeur_udp_pont  # noqa: E402  (groupe « pont » : liaison par le vrai pont_serie.py)
import test_testeur_udp_acces  # noqa: E402  (groupe « acces » : jeton depuis un autre appareil, acces_web.py)
import test_testeur_udp_muette  # noqa: E402  (groupe « muette » : carte qui ne repond plus sur son port)
import test_testeur_udp_grille  # noqa: E402  (groupe « grille » : onglet Grille ModBus, sans carte)
import acces_web                            # noqa: E402
from testeur_udp_sim import FauxSerie, Reseau, Sim   # noqa: E402,F401

RESULTATS = {"ok": 0, "ko": []}
MDP = "S3cr3tPW9"
from testeur_udp_sim import D, E, R           # noqa: E402


def verifie(valeur, attendu, nom):
    if valeur == attendu:
        RESULTATS["ok"] += 1
    else:
        RESULTATS["ko"].append(f"{nom} : obtenu {valeur!r}, attendu {attendu!r}")


def attend(condition, delai=6.0):
    fin = time.time() + delai
    while time.time() < fin:
        if condition():
            return True
        time.sleep(0.03)
    return condition()


# ====================================================================== lignes de log exactes
def l_envoi(mode, ip, msg, res="OK"):
    return f"12:00:01.000 ENVOI_MSG_UDP: {D} {mode} {E} vers '{ip}' >>>> {msg} >>>> {res}"


def l_entete(mode, ip, port=4000):
    return f"12:00:01.100 LIRE_UDP: {D} UDP {mode} {R} de '{ip}' sur le port {port}"


def l_msg(msg):
    return f"12:00:01.101 LIRE_UDP: msg = {msg}"


def nouvel_essai(type_essai, mode_connexion="RangeExtender", **plus):
    demande = {"type": type_essai, "sens": "esclave>maitre", "mode": "UniCast", "texte": "salut",
               "ip_maitre": "192.168.4.1", "ip_esclave": "192.168.4.2", **plus}
    return te.construit_essai(7, demande, mode_connexion)


def alimente(essai, role, lignes):
    for ligne in lignes:
        essai.observe(role, ligne, time.time())


# ====================================================================== 1. essais purs
def groupe_essais():
    verifie(hex(te.crc16(bytes.fromhex("020100E00001"))), "0xffc", "crc16 vecteur 020100E00001")
    verifie(te.trame_lecture_relai(2), "020100E00001FC0F", "trame par defaut adresse 2")
    verifie(te.trame_lecture_relai(5)[:12], "050100E00001", "trame adresse 5 : corps")
    verifie(te.trame_lecture_relai(5)[-4:] != "FC0F", True, "TEMOIN trame adresse 5 : CRC recalcule")
    verifie(te.crc16(bytes.fromhex("020100E00001")) == te.crc16(bytes.fromhex("020100E00002")), False,
            "TEMOIN crc16 depend des donnees")

    e = nouvel_essai("texte", mode="UniCast")
    verifie(e.commande, "ReglageUDP envoiUniCast 192.168.4.1 TESTUDP-7 salut", "commande texte unicast esclave>maitre")
    verifie(nouvel_essai("texte", mode="MultiCast").commande, "ReglageUDP envoiMultiCast TESTUDP-7 salut",
            "commande texte multicast")
    verifie(nouvel_essai("texte", sens="maitre>esclave").commande,
            "ReglageUDP envoiUniCast 192.168.4.2 TESTUDP-7 salut", "commande texte maitre>esclave")
    verifie(nouvel_essai("modbus", ip_esclave="192.168.4.2").commande,
            "ReglageModbus envoiMessageUDP 192.168.4.2 ModbusUDP 17 020100E00001FC0F", "commande modbus E1")
    verifie(nouvel_essai("modbus", avec_tid=False).commande,
            "ReglageModbus envoiMessageUDP 192.168.4.2 ModbusUDP 020100E00001FC0F", "commande modbus sans tid")
    verifie(nouvel_essai("imalive").commande, "ReglageUDP forceEnvoiParams ON", "commande imalive")
    verifie(nouvel_essai("push").commande, te.COMMANDE_PUSH, "commande push")
    for demande, nom in (({"type": "texte", "ip_maitre": "pas une ip"}, "ip invalide"),
                         ({"type": "texte", "ip_maitre": "999.1.1.1"}, "ip hors bornes"),
                         ({"type": "inconnu"}, "type inconnu"),
                         ({"type": "modbus", "ip_esclave": "1.2.3.4", "adresse": 0}, "adresse 0"),
                         ({"type": "modbus", "ip_esclave": "1.2.3.4", "tid": 70000}, "tid trop grand")):
        try:
            te.construit_essai(1, demande, None)
            verifie("accepte", "refuse", f"TEMOIN demande invalide ({nom})")
        except ValueError:
            verifie("refuse", "refuse", f"demande invalide ({nom})")

    # -- RECU : emission + reception du bon message
    e = nouvel_essai("texte")
    alimente(e, "esclave", [l_envoi("UniCast", "192.168.4.1", "TESTUDP-7 salut")])
    alimente(e, "maitre", [l_entete("UniCast", "192.168.4.2", 4001), l_msg("TESTUDP-7 salut")])
    r = e.conclut()
    verifie(r["verdict"], te.RECU, "texte : RECU")
    verifie(r["source"], "192.168.4.2:4001", "texte : source vue")
    verifie(e.termine(), True, "texte : termine des la reception")
    # TEMOIN : un AUTRE message recu ne vaut pas RECU
    e = nouvel_essai("texte")
    alimente(e, "esclave", [l_envoi("UniCast", "192.168.4.1", "TESTUDP-7 salut")])
    alimente(e, "maitre", [l_entete("UniCast", "192.168.4.9"), l_msg("TESTUDP-99 autre essai")])
    verifie(e.conclut()["verdict"], te.EMIS_NON_RECU, "TEMOIN texte : reception d'un autre message refusee")
    verifie(e.termine(), False, "TEMOIN texte : pas termine sur un autre message")
    # TEMOIN : TESTUDP-7 n'est pas TESTUDP-77
    e = nouvel_essai("texte")
    alimente(e, "maitre", [l_entete("UniCast", "1.1.1.1"), l_msg("TESTUDP-77 salut")])
    verifie(te.contient_marqueur("TESTUDP-77 x", "TESTUDP-7"), False, "TEMOIN marqueur : mot entier exige")
    verifie(e.conclut()["verdict"], te.NON_EMIS, "TEMOIN texte : TESTUDP-77 pour TESTUDP-7 + rien emis")
    # TEMOIN : ligne anterieure a l'envoi ignoree
    e = nouvel_essai("texte")
    e.observe("maitre", l_msg("TESTUDP-7 salut"), e.t0 - 5)
    verifie(e.conclut()["verdict"], te.NON_EMIS, "TEMOIN ligne anterieure a l'essai ignoree")
    # -- NON EMIS : Echec, nil, reseau non monte, aucune ligne
    for res in ("Echec", "nil"):
        e = nouvel_essai("texte")
        alimente(e, "esclave", [l_envoi("UniCast", "192.168.4.1", "TESTUDP-7 salut", res)])
        verifie(e.conclut()["verdict"], te.NON_EMIS, f"texte : emission {res} -> NON EMIS")
    e = nouvel_essai("texte")
    alimente(e, "esclave", ["12:00:01 ENVOI_MSG_UDP: Reseau non connecte, 'TESTUDP-7 salut' non envoye !"])
    r = e.conclut()
    verifie((r["verdict"], "reseau non connecte" in r["details"][0]), (te.NON_EMIS, True), "texte : reseau non monte")
    # -- multicast du maitre sans point d'acces ni esclave sur la box : "Non emis" (2026-10-17)
    e = nouvel_essai("texte", sens="maitre>esclave", mode="MultiCast")
    alimente(e, "maitre", [l_envoi("MultiCast", "", "TESTUDP-7 salut", "Non emis")])
    r = e.conclut()
    verifie((r["verdict"], any("aucun esclave joignable par la box" in d for d in r["details"])), (te.NON_EMIS, True),
            "multicast maitre Non emis : NON EMIS + explication")
    e = nouvel_essai("texte", sens="maitre>esclave", mode="MultiCast")
    alimente(e, "maitre", [l_envoi("MultiCast", "", "TESTUDP-7 salut", "Echec")])
    verifie(any("aucun esclave joignable par la box" in d for d in e.conclut()["details"]), False,
            "TEMOIN multicast maitre Echec : pas d'explication box")
    # -- cas connu : multicast depuis un esclave en Wi-Fi classique
    e = nouvel_essai("imalive", mode_connexion="WifiClassique")
    r = e.conclut()
    verifie((r["verdict"], any("cas connu" in d for d in r["details"])), (te.NON_EMIS, True),
            "imalive hors Range Extender : NON EMIS + explication")
    e = nouvel_essai("imalive", mode_connexion="RangeExtender")
    verifie(any("cas connu" in d for d in e.conclut()["details"]), False, "TEMOIN imalive Range Extender : pas d'explication")
    # -- imalive / push
    e = nouvel_essai("imalive")
    alimente(e, "maitre", [l_entete("MultiCast", "192.168.4.2"), l_msg("ImAlive {\"id\":2}")])
    verifie(e.conclut()["verdict"], te.RECU, "imalive : RECU")
    e = nouvel_essai("push")
    alimente(e, "esclave", ["12:00 POUSSE_ETAT: registre 1376 = 3", l_envoi("MultiCast", "224.3.0.1", "ModbusPushUDP 5 AA")])
    alimente(e, "maitre", [l_entete("MultiCast", "192.168.4.2"), l_msg("ModbusPushUDP 5 AA")])
    verifie(e.conclut()["verdict"], te.RECU, "push : RECU")
    e = nouvel_essai("push")
    alimente(e, "esclave", ["12:00 PAS_DE_RUBAN"])
    verifie((e.conclut()["verdict"], e.termine()), (te.PAS_DE_RUBAN, True), "push : PAS DE RUBAN")
    e = nouvel_essai("push")
    alimente(e, "maitre", [l_entete("MultiCast", "192.168.4.2"), l_msg("ImAlive")])
    verifie(e.conclut()["verdict"], te.NON_EMIS, "TEMOIN push : un ImAlive n'est pas un push")
    # -- modbus
    rep = "12:00 REPOND_UDP: reponse a 192.168.4.1 : ModbusUDP 17 020101FF2A00"
    e = nouvel_essai("modbus", sens="maitre>esclave")
    alimente(e, "maitre", [l_envoi("UniCast", "192.168.4.2", "ModbusUDP 17 020100E00001FC0F"),
                           l_entete("UniCast", "192.168.4.2"), l_msg("ModbusUDP 17 020101FF2A00")])
    alimente(e, "esclave", [l_entete("UniCast", "192.168.4.1"), l_msg("ModbusUDP 17 020100E00001FC0F"), rep])
    verifie((e.conclut()["verdict"], e.termine()), (te.RECU, False), "modbus : RECU (attend toute la fenetre)")
    # TEMOIN : reponse avec un AUTRE tid
    e = nouvel_essai("modbus")
    alimente(e, "esclave", [rep.replace("ModbusUDP 17", "ModbusUDP 18")])
    alimente(e, "maitre", [l_entete("UniCast", "192.168.4.2"), l_msg("ModbusUDP 18 020101FF2A00")])
    verifie(e.conclut()["verdict"] != te.RECU, True, "TEMOIN modbus : tid different refuse")
    # TEMOIN : la reponse UDP recopiee sur le RS485 par l'esclave
    e = nouvel_essai("modbus")
    alimente(e, "esclave", [rep, f"12:00 ENVOI_MSG_MODBUS: Message ModBus envoyé = 0x020101ff2a00"])
    alimente(e, "maitre", [l_entete("UniCast", "192.168.4.2"), l_msg("ModbusUDP 17 020101FF2A00")])
    verifie(e.conclut()["verdict"], te.ECHEC, "TEMOIN modbus : reponse recopiee sur le RS485 -> ECHEC")
    # une AUTRE trame RS485 (reponse au releve serie du maitre, cable branche) n'est pas un defaut d'E1
    e = nouvel_essai("modbus")
    alimente(e, "esclave", [rep, f"12:00 ENVOI_MSG_MODBUS: Message ModBus envoyé = 0x02030A000100020003000400050A1B"])
    alimente(e, "maitre", [l_entete("UniCast", "192.168.4.2"), l_msg("ModbusUDP 17 020101FF2A00")])
    r = e.conclut()
    verifie((r["verdict"], "ignorees" in " ".join(r["details"])), (te.RECU, True),
            "modbus : trame RS485 etrangere (releve du maitre) ignoree")
    # temoin sans tid
    e = nouvel_essai("modbus", avec_tid=False)
    alimente(e, "esclave", ["12:00 REPOND_UDP: reponse a 192.168.4.1 : ModbusUDP 020101FF2A00"])
    alimente(e, "maitre", [l_entete("UniCast", "192.168.4.2"), l_msg("ModbusUDP 020101FF2A00")])
    verifie(e.conclut()["verdict"], te.RECU, "modbus sans tid : RECU")
    e = nouvel_essai("modbus", avec_tid=False)
    alimente(e, "maitre", [l_entete("UniCast", "192.168.4.2"), l_msg("ModbusUDP 17 020101FF2A00")])
    verifie(e.conclut()["verdict"] != te.RECU, True, "TEMOIN modbus sans tid : une reponse AVEC tid est refusee")
    verifie(nouvel_essai("modbus").conclut()["verdict"], te.NON_EMIS, "modbus : rien -> NON EMIS")


def monte_testeur(avec_persist=True):
    dossier = tempfile.mkdtemp(prefix="test_testeur_udp_")
    persist = os.path.join(dossier, "_persist.json")
    with open(persist, "w", encoding="utf-8") as f:
        json.dump({"serveur": {"wifi": {"reseau1": {"nomReseauWifi": "MonReseau", "mdpWifi": MDP}}}}, f)
    reseau = Reseau()
    sims = {"COM_M": Sim("maitre", reseau, "192.168.1.50", "RangeExtender"),
            "COM_E": Sim("esclave", reseau, "192.168.4.2", "RangeExtender")}
    reseau.sims = {s.role: s for s in sims.values()}

    def fabrique(nom, vitesse):
        if nom == "COM_OCC":
            raise serial.SerialException("could not open port 'COM_OCC': PermissionError(13, 'Acces refuse.', None, 5)")
        return sims[nom].ouvre()
    args = types.SimpleNamespace(vitesse=115200, http=0, journal=os.path.join(dossier, "journal.log"),
                                 persist_maitre=persist if avec_persist else os.path.join(dossier, "absent.json"))
    return tu.Testeur(args, fabrique), sims, reseau, args


def groupe_carte():
    masque = tc.Masque()
    verifie(masque.applique("mot de passe " + MDP), "mot de passe " + MDP, "TEMOIN masque vide : le secret passe")
    masque.ajoute(MDP)
    verifie(masque.applique(f"a {MDP} b {MDP}"), "a *** b ***", "masque : toutes les occurrences")
    recu = []
    sim = Sim("esclave", Reseau(), "1.2.3.4")
    carte = tc.Carte("esclave", 115200, masque, lambda r, t, h: recu.append(t), lambda r, re_: recu.append(("ouv", re_)),
                     lambda r: recu.append("perte"), lambda r, t: None, lambda n, v: sim.ouvre())
    ok, _ = carte.ouvre("COM_X", 115200)
    sim.serie.q.put("12:00 Données reçues à {} {}\r\nsuite".format(MDP, "fin\n").encode("utf-8")[:20])
    sim.serie.q.put("étendu".encode("utf-8")[1:])      # morceau d'un octet multi-octets : jamais d'exception
    sim.serie.q.put(b"\n12:01 \x1b[32mvert\x1b[0m " + MDP.encode() + b"\n")
    attend(lambda: any(isinstance(x, str) and "vert" in x for x in recu))
    verifie([x for x in recu if isinstance(x, str) and "vert" in x], ["12:01 vert ***"], "lignes : ANSI retire, mot de passe masque")
    verifie(any(isinstance(x, str) and MDP in x for x in recu), False, "TEMOIN aucune ligne ne contient le secret")
    # perte puis reouverture automatique
    sim.redemarre(1.2)
    verifie(attend(lambda: "perte" in recu), True, "port perdu : detecte")
    verifie(attend(lambda: ("ouv", True) in recu, 8), True, "port perdu : rouvert automatiquement")
    verifie(carte.ouvert, True, "carte ouverte apres reouverture")
    carte.ferme()
    time.sleep(0.3)
    verifie(carte.ouvert or carte.perdu, False, "TEMOIN apres Fermer : plus de reouverture")
    carte.arret = True
    # port occupe
    def refuse(n, v):
        raise serial.SerialException("could not open port 'COM_OCC': PermissionError(13, 'Acces refuse.', None, 5)")
    c2 = tc.Carte("maitre", 115200, masque, lambda *a: None, lambda *a: None, lambda *a: None, lambda *a: None, refuse)
    ok, message = c2.ouvre("COM_OCC", 115200)
    verifie((ok, "deja ouvert par un autre programme" in message), (False, True), "port occupe : avertissement clair")
    time.sleep(1.3)
    verifie(c2.ouvert, False, "TEMOIN port occupe : pas de reouverture sauvage")
    c2.arret = True


# ====================================================================== testeur complet
def groupe_testeur():
    t, sims, reseau, args = monte_testeur()
    ok, _ = t.cartes["maitre"].ouvre("COM_M", 115200)
    ok2, _ = t.cartes["esclave"].ouvre("COM_E", 115200)
    verifie((ok, ok2), (True, True), "ouverture des deux cartes")
    verifie(attend(lambda: t.infos["esclave"]["ip"] == "192.168.4.2" and t.infos["maitre"]["ip"] == "192.168.1.50"), True,
            "Status 5 : IP des deux cartes")
    verifie(attend(lambda: t.mode_esclave == "RangeExtender"), True, "mode de l'esclave lu")
    verifie(t.etat()["ip_vers_maitre_defaut"], "192.168.4.1", "Range Extender : le maitre est a 192.168.4.1")
    verifie(attend(lambda: sims["COM_E"].niveaux["udp"] == "detail" and sims["COM_E"].niveaux["modbus"] == "detail"), True,
            "logs udp et modbus poses en detail")
    # info (actif : debug) -> premier mot 'info' < debug : le testeur pose debug
    verifie(attend(lambda: sims["COM_E"].niveaux["serie"] == "debug"), True, "sortie serie posee a debug (1er mot 'info')")
    verifie(t.logs["esclave"]["originaux"], {"udp": "info", "modbus": "info", "serie": "info"}, "valeurs d'origine memorisees")
    tout = [l for s in sims.values() for l in s.recus]
    verifie(any(l.startswith("ReglageLog") and ("mqtt" in l or "web" in l or "syslog" in l) for l in tout), False,
            "JAMAIS de ReglageLog mqtt / web / syslog")
    verifie(sims["COM_E"].niveaux["mqtt"], "erreur", "TEMOIN sortie mqtt inchangee")

    def essai(**d):
        return t.lance_essai({"delai": 0.6, **d})
    r = essai(type="texte", sens="esclave>maitre", mode="UniCast", texte="bonjour", ip_maitre="192.168.4.1")
    verifie((r["verdict"], r["source"]), ("RECU", "192.168.4.2:4000"), "bout en bout : texte unicast esclave>maitre")
    r = essai(type="texte", sens="maitre>esclave", mode="UniCast", texte="x", ip_esclave="192.168.4.2")
    verifie(r["verdict"], "RECU", "bout en bout : texte unicast maitre>esclave")
    r = essai(type="texte", sens="esclave>maitre", mode="MultiCast", texte="mc")
    verifie(r["verdict"], "RECU", "bout en bout : texte multicast esclave>maitre (Range Extender)")
    r = essai(type="modbus", ip_esclave="192.168.4.2", tid=21)
    verifie((r["verdict"], "aucune copie de la reponse sur le RS485" in " ".join(r["details"])), ("RECU", True),
            "bout en bout : ModbusUDP E1")
    r = essai(type="imalive")
    verifie(r["verdict"], "RECU", "bout en bout : ImAlive")
    r = essai(type="push")
    verifie(r["verdict"], "RECU", "bout en bout : push")
    sims["COM_E"].ruban = False
    verifie(essai(type="push")["verdict"], "PAS DE RUBAN", "bout en bout : esclave sans ruban")
    sims["COM_E"].ruban = True
    reseau.perte = True                                  # TEMOIN : le reseau perd tout
    r = essai(type="texte", sens="esclave>maitre", mode="UniCast", ip_maitre="192.168.4.1")
    verifie(r["verdict"], "EMIS NON RECU", "TEMOIN reseau coupe : EMIS NON RECU")
    reseau.perte = False
    sims["COM_E"].bug_rs485 = True
    verifie(essai(type="modbus", ip_esclave="192.168.4.2")["verdict"], "ECHEC", "TEMOIN esclave qui ecrit aussi sur RS485 : ECHEC")
    sims["COM_E"].bug_rs485 = False
    n_essais = len(t.essais)
    verifie(n_essais >= 9, True, "historique des verdicts alimente")
    try:
        essai(type="texte", ip_maitre="bidon")
        verifie("accepte", "refuse", "TEMOIN essai avec IP invalide")
    except ValueError:
        verifie("refuse", "refuse", "essai avec IP invalide refuse")

    # -- lecture des reponses a ModeConnexion (deterministe, sans thread) : la reponse a une bascule
    # porte "redemarrage": true -> l'attente continue et le mode sera RELU apres le redemarrage ; une
    # simple lecture du mode clot l'attente. Defaut corrige le 2026-10-16 (la reponse a la bascule
    # cloturait l'attente avant le redemarrage).
    sauve_mode = t.mode_esclave
    t.redemarrage_depuis = time.time()
    t.analyse("esclave", '12:00:00.000 RSL: RESULT = {"ReglageGlobal":{"modeConnexion":"WifiClassique","redemarrage":true}}')
    verifie((t.etat()["redemarrage"], t.acquis["esclave"]["mode"]), (True, False),
            "reponse a la bascule : attente maintenue, mode a relire")
    t.analyse("esclave", '12:00:00.000 RSL: RESULT = {"ReglageGlobal":{"modeConnexion":"WifiClassique"}}')
    verifie((t.etat()["redemarrage"], t.acquis["esclave"]["mode"]), (False, True),
            "TEMOIN simple lecture du mode : attente close")
    t.mode_esclave = sauve_mode

    # -- bascule vers Wi-Fi classique : mot de passe transmis a la carte, jamais affiche
    t.bascule_mode("WifiClassique")
    verifie(any(MDP in l and l.startswith("ReglageGlobal ModeConnexion WifiClassique MonReseau") for l in sims["COM_E"].recus),
            True, "la commande de bascule porte ssid et mot de passe")
    verifie(t.etat()["redemarrage"], True, "etat : redemarrage en cours")
    # La reponse immediate de la carte ("redemarrage": true) ne doit PAS clore l'attente : la carte
    # n'a pas encore redemarre. Temoin du defaut corrige le 2026-10-16 (le mode lu l'annulait).
    # La perte du port et sa reouverture se suivent de pres : echantillonner plutot qu'attendre.
    port_perdu, fin = False, time.time() + 4
    while time.time() < fin and not port_perdu:
        port_perdu = not t.cartes["esclave"].ouvert
        time.sleep(0.005)
    verifie(port_perdu, True, "le port de l'esclave disparait")
    verifie(attend(lambda: t.mode_esclave == "WifiClassique" and not t.etat()["redemarrage"], 15), True,
            "port rouvert seul, mode relu : Wi-Fi classique")
    verifie(t.etat()["cartes"]["esclave"]["ip"], "192.168.4.2", "IP relue apres redemarrage")
    r = essai(type="imalive")
    verifie((r["verdict"], any("cas connu" in d for d in r["details"])), ("NON EMIS", True),
            "Wi-Fi classique : ImAlive NON EMIS + cas connu explique")
    # Refus de la carte (retour sans reseaux memorises) : l'attente s'arrete et l'erreur est montree
    sims["COM_E"].refuse_bascule = True
    t.bascule_mode("RangeExtender")
    verifie(attend(lambda: not t.etat()["redemarrage"], 5), True, "refus de la carte : plus d'attente de redemarrage")
    verifie(any("aucun reseau memorise" in n for n in t.notes_esclave()), True, "refus de la carte : erreur affichee")
    verifie(t.mode_esclave, "WifiClassique", "TEMOIN refus : mode inchange")
    sims["COM_E"].refuse_bascule = False
    t.bascule_mode("RangeExtender")
    verifie(attend(lambda: t.mode_esclave == "RangeExtender" and sims["COM_E"].mode == "RangeExtender", 15), True,
            "retour en Range Extender")
    # secret absent des evenements et du journal
    historique = b"".join(t.historique).decode("utf-8")
    verifie(MDP in historique, False, "mot de passe absent de la page (historique SSE)")
    verifie("MonReseau" in historique, True, "TEMOIN la commande de bascule est bien dans l'historique (masquee)")
    with open(args.journal, encoding="utf-8") as f:
        journal = f.read()
    verifie(MDP in journal, False, "mot de passe absent du journal")
    verifie("***" in journal, True, "TEMOIN le journal contient le masque ***")
    # sans persist : bascule refusee
    t2, _, _, _ = monte_testeur(avec_persist=False)
    t2.cartes["esclave"].ouvre("COM_E", 115200)
    try:
        t2.bascule_mode("WifiClassique")
        verifie("acceptee", "refusee", "TEMOIN bascule sans persist")
    except ValueError:
        verifie("refusee", "refusee", "bascule sans persist lisible refusee")
    t2.arrete()

    # -- restauration des logs a l'arret
    t.arrete()
    time.sleep(0.2)
    verifie({k: sims["COM_E"].niveaux[k] for k in ("udp", "modbus")}, {"udp": "info", "modbus": "info"},
            "arret : niveaux udp / modbus restaures")
    verifie(sims["COM_E"].niveaux["serie"], "info", "arret : sortie serie restauree")
    verifie(t.cartes["maitre"].ouvert, False, "arret : ports fermes")
    return t


# ====================================================================== cuve du 2026-10-17
def groupe_firmware_ancien():
    """La cuve telle que trouvee le 2026-10-17 : log serie deja coupe par Tasmota (600 s apres le demarrage)
    et firmware sans ReglageGlobal ModeConnexion."""
    t, sims, reseau, args = monte_testeur()
    sims["COM_E"].serie_coupee, sims["COM_E"].sans_mode_connexion = True, True
    t.cartes["maitre"].ouvre("COM_M", 115200)
    t.cartes["esclave"].ouvre("COM_E", 115200)
    verifie(attend(lambda: t.infos["esclave"]["ip"] == "192.168.4.2"), True,
            "log serie coupe : relance a l'ouverture, IP de l'esclave lue")
    verifie(sims["COM_E"].reveils, 1, "SerialLog reapplique une fois par ouverture")
    verifie(attend(lambda: t.mode_absent), True, "ModeConnexion absent : reconnu")
    time.sleep(3.5)                                    # au-dela d'un tour de relance (3 s)
    demandes = sum(1 for l in sims["COM_E"].recus if l == "ReglageGlobal ModeConnexion")
    verifie(demandes, 1, "ModeConnexion absent : demande UNE fois, pas toutes les 3 s")
    verifie((t.mode_esclave, t.etat()["ip_vers_maitre_defaut"]), (None, "192.168.4.1"),
            "mode illisible mais esclave en 192.168.4.x : maitre par defaut a 192.168.4.1")
    verifie(sum(1 for texte in t.notes_esclave() if "absent du firmware" in texte), 1, "note affichee une seule fois")
    try:
        t.bascule_mode("RangeExtender")
        verifie("acceptee", "refusee", "TEMOIN bascule sur un firmware sans ModeConnexion")
    except ValueError:
        verifie("refusee", "refusee", "bascule refusee sur un firmware sans ModeConnexion")
    t.arrete()


# ====================================================================== HTTP
def groupe_http():
    t, sims, reseau, args = monte_testeur()
    acces = acces_web.Acces(0, True, "Testeur UDP")
    serveur = ThreadingHTTPServer(("127.0.0.1", 0), testeur_udp_http.fabrique_gestionnaire(t, acces))
    serveur.daemon_threads = True
    args.http = acces.port = serveur.server_address[1]
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{args.http}"

    def appel(chemin, corps=None, entetes=None):
        requete = urllib.request.Request(base + chemin, data=None if corps is None else json.dumps(corps).encode(),
                                         headers=entetes if entetes is not None else {"X-Testeur": "1"})
        try:
            with urllib.request.urlopen(requete, timeout=10) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as erreur:
            return erreur.code, erreur.read().decode("utf-8")
    code, page = appel("/")
    verifie((code, "Testeur UDP" in page and "vueAide" in page and "TESTUDP" in page), (200, True), "GET / : page et onglet Aide")
    verifie(appel("/etat")[0], 200, "GET /etat")
    verifie(isinstance(json.loads(appel("/ports")[1]), list), True, "GET /ports")
    verifie(appel("/essais")[1], "[]", "GET /essais vide")
    verifie(appel("/inconnu")[0], 404, "GET route inconnue : 404")
    verifie(appel("/raz", {})[0], 200, "POST /raz")
    verifie(appel("/raz", {}, {})[0], 403, "TEMOIN POST sans en-tete X-Testeur : refuse")
    verifie(appel("/raz", {}, {"X-Testeur": "1", "Origin": "http://evil.example"})[0], 403, "TEMOIN POST d'une autre origine : refuse")
    verifie(appel("/rien", {})[0], 404, "POST route inconnue : 404")
    code, texte = appel("/port", {"carte": "maitre", "action": "ouvrir", "port": "COM_OCC", "vitesse": 115200})
    verifie((code, "deja ouvert par un autre programme" in texte), (200, True), "POST /port occupe : avertissement")
    verifie(appel("/port", {"carte": "x", "action": "ouvrir", "port": "COM_M"})[0], 400, "POST /port carte inconnue : 400")
    verifie(appel("/test", {"type": "imalive"})[0], 409, "TEMOIN POST /test port ferme : 409")
    for role, nom in (("maitre", "COM_M"), ("esclave", "COM_E")):
        verifie(json.loads(appel("/port", {"carte": role, "action": "ouvrir", "port": nom, "vitesse": 115200})[1])["ok"], True,
                f"POST /port ouvre {role}")
    attend(lambda: t.mode_esclave and t.infos["maitre"]["ip"])
    code, texte = appel("/test", {"type": "texte", "sens": "esclave>maitre", "mode": "UniCast", "texte": "http",
                                  "ip_maitre": "192.168.4.1", "delai": 1})
    verifie((code, json.loads(texte)["verdict"]), (200, "RECU"), "POST /test texte")
    verifie(len(json.loads(appel("/essais")[1])), 1, "GET /essais apres un essai")
    verifie(appel("/mode", {"mode": "RangeExtender"})[0], 400, "TEMOIN POST /mode sans confirmation : 400")
    verifie(appel("/cmd", {"carte": "esclave", "commande": "Status 5"})[0], 200, "POST /cmd")
    verifie(appel("/relire", {"carte": "bidon"})[0], 400, "POST /relire carte inconnue : 400")
    verifie(appel("/restaure", {})[0], 200, "POST /restaure")
    attend(lambda: sims["COM_E"].niveaux["udp"] == "info")
    verifie(sims["COM_E"].niveaux["udp"], "info", "bouton Restaurer : niveau udp d'origine")
    flux = urllib.request.urlopen(base + "/flux", timeout=5)
    debut = flux.readline().decode("utf-8")
    verifie(debut.startswith("data: ") and '"k": "etat"' in debut, True, "GET /flux : premier evenement = etat")
    flux.close()
    serveur.shutdown()
    t.arrete()


def main():
    for nom, groupe in (("essais", groupe_essais), ("carte", groupe_carte), ("testeur", groupe_testeur),
                        ("ancien", groupe_firmware_ancien), ("pont", lambda: test_testeur_udp_pont.groupe_pont(verifie, attend)), ("http", groupe_http),
                        ("acces", lambda: test_testeur_udp_acces.groupe_acces(verifie, monte_testeur)),
                        ("muette", lambda: test_testeur_udp_muette.groupe_muette(verifie, attend, monte_testeur)),
                        ("grille", lambda: test_testeur_udp_grille.groupe_grille(verifie, attend, monte_testeur))):
        debut = time.time()
        try:
            groupe()
        except Exception as erreur:      # un groupe qui plante ne doit pas masquer les autres
            import traceback
            RESULTATS["ko"].append(f"groupe {nom} : exception {erreur!r}\n{traceback.format_exc()}")
        print(f"groupe {nom:8} {time.time() - debut:5.1f} s")
    print(f"{RESULTATS['ok']} verifications reussies, {len(RESULTATS['ko'])} echec(s)")
    for ko in RESULTATS["ko"]:
        print("  KO :", ko)
    sys.exit(1 if RESULTATS["ko"] else 0)


if __name__ == "__main__":
    main()
