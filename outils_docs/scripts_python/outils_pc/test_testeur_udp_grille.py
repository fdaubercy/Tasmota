"""Groupe « grille » du banc test_testeur_udp.py : onglet Grille ModBus (testeur_udp_grille.py), sans carte.

Deux cartes simulees repondent aux commandes de la grille par les lignes de log du vrai firmware ; les delais
sont reduits par 'echelle'. Chaque verdict positif a son temoin negatif (la meme etape doit echouer quand la
preuve manque ou qu'un motif interdit apparait).
"""

import os
import threading
import time

import testeur_udp_grille as tg
import testeur_udp_http

ECHELLE = 0.01
PERSIST_P4 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "garage",
                          "tasmota32p4-serveur-modbus", "_persist.json")


class Cartes:
    """Reponses des deux cartes aux commandes de la grille. 'pannes' : comportements fautifs a simuler."""

    def __init__(self, pannes=(), voie="Serial"):
        self.grille, self.pannes, self.envoyees, self.voie = None, set(pannes), [], voie
        self.mode, self.seq = "MANUEL", 6           # ruban de la cuve ; numero d'ordre de ses push

    def dit(self, role, *lignes):
        def emet():
            for ligne in lignes:
                self.grille.observe(role, "12:00:00.000 " + ligne)
        threading.Timer(0.02, emet).start()

    def ecrit(self, role, commande):
        self.envoyees.append((role, commande))
        if "ferme" in self.pannes:
            return False
        if commande.startswith("Br import global"):
            marqueur = "GRILLE_T1_MAITRE" if role == "maitre" else "GRILLE_T1_ESCLAVE"
            self.dit(role, f"CMD: {commande}", f"{marqueur} true")
        elif commande.startswith('Br print("GRILLE_T1_RS485"'):
            self.dit(role, f"GRILLE_T1_RS485 {'false' if 'rs485' in self.pannes else 'true'}")
        elif commande == "ReglageModbus VoieCommandes" and role == "esclave":
            # Reponse reelle de la cuve (2026-10-18) ; panne 'voie_muette' : firmware sans la sous-commande
            if "voie_muette" not in self.pannes:
                self.dit(role, f'MQT: stat/jardin/cuve/RESULT = "ReglageModbus: voieCommandes={self.voie}, OK"')
        elif commande in ("Power1 ON", "Power1 OFF") and role == "maitre":
            lum = "0" if commande.endswith("OFF") or "ruban" in self.pannes else "40"
            self.dit("maitre", "GESTION_RELAIS: Publie sur le réseau ModBus pour le relai n°1 !")
            self.dit("esclave", "EXECUTE_CMD_MODBUS: DeviceAddress = 0x02",
                     f"POUSSE_ETAT: registre 1376 = [10, 20, {lum}, 0] -> maitre (UDP, seq 5) : 0210")
            self.dit("maitre", "LIRE_UDP: msg = ModbusPushUDP 5 0210")
        elif commande == "RubanEsclave1 auto":
            # Reponses reelles (2026-10-17) : la reponse donne le mode du DERNIER etat recu ; le mode 0 arrive
            # au releve suivant. Panne 'auto_ko' : la cuve reste en MANUEL (30 min).
            mode = 30 if "auto_ko" in self.pannes else 0
            self.mode = "MANUEL" if mode else "AUTO"
            self.dit("maitre", f"CMD: {commande}",
                     'RSL: RESULT = {"RubanEsclave1":{"Mode":"MANUEL","Reste":30,"Ordre":"auto"}}',
                     'MQT: tele/garage/RESULT = {"ModbusReceived":{"DeviceAddress":2,"FunctionCode":3,"StartAddress":1376,'
                     f'"Length":15,"Count":5,"Values":[0,0,0,0,{mode}]}}}}')
        elif commande == "RubanEsclave1":
            reste = "30" if self.mode == "MANUEL" else "null"
            self.dit("maitre", f"CMD: {commande}", f'RSL: RESULT = {{"RubanEsclave1":{{"Mode":"{self.mode}","Reste":{reste}}}}}')
        elif commande == "Power1 TOGGLE" and role == "esclave":
            self.seq += 1
            self.dit("esclave", f"POUSSE_ETAT: registre 1376 = [0, 0, 10, 0, 0] -> maitre (UDP, seq {self.seq}) : 0210")
            self.dit("maitre", f"LIRE_UDP: msg = ModbusPushUDP {self.seq} 0210")
        elif commande == "Restart 1" and role == "esclave":
            # La cuve pousse son seq 1 DES SON DEMARRAGE : le P4 voit le redemarrage avant toute autre etape
            ancien, self.seq = self.seq, 1
            self.dit("esclave", "CMD: Restart 1")
            if "sans_redemarrage" not in self.pannes:
                self.dit("maitre", f"ACCEPTE_SEQ: esclave d'ID=2 redemarre (seq 1 apres {ancien})")
            self.dit("esclave", 'MQT: tele/jardin/cuve/INFO3 = {"Info3":{"RestartReason":"Software reset CPU","BootCount":9}}')
        elif commande.startswith("Br import json"):
            self.dit("maitre", "GRILLE_T7 KO cle esclave2" if "discovery" in self.pannes else "GRILLE_T7 OK ")
        return True


def nouvelle(pannes=(), reponses=None, voie="Serial"):
    """voie : celle que le test 1 aurait lue sur la cuve (None = test 1 jamais lance)."""
    cartes = Cartes(pannes, voie or "Serial")
    evenements = []
    g = tg.Grille(cartes.ecrit, evenements.append, echelle=ECHELLE)
    cartes.grille = g
    if voie is not None:
        g.regle_voie(voie)
    if reponses is not None:            # repond aux consignes, dans l'ordre
        def repondeur():
            file = list(reponses)
            while file:
                if g.consigne is not None:
                    try:
                        g.repond(file.pop(0))
                    except OSError:
                        pass
                    time.sleep(0.05)
                time.sleep(0.01)
        threading.Thread(target=repondeur, daemon=True).start()
    return g, cartes, evenements


def statuts(g, num):
    test = next(t for t in g.etat()["tests"] if t["num"] == num)
    return {v["cle"]: v["statut"] for v in test["verifs"]}


def groupe_grille(verifie, attend, monte_testeur):
    # -- cible lue dans le persist du P4 du depot
    verifie(tg.cible_depuis_persist(PERSIST_P4), {"id": 2, "power": 1, "registre": 1376},
            "cible : cuve ID 2, ruban POWER1, registre 1376 (persist du P4)")
    verifie(tg.cible_depuis_persist("absent.json"), tg.PERSIST_DEFAUT, "TEMOIN persist absent : valeurs par defaut")
    verifie(len(tg.BR_DISCOVERY) < 790, True, "commande discovery < 800 octets (tampon serie de Tasmota)")

    # -- test 1 : demarrage
    g, cartes, _ = nouvelle(voie=None)
    verifie(g.etat()["voie"], None, "voie inconnue tant que le test 1 n'a pas tourne")
    for num in tg.TESTS_SELON_VOIE:
        try:
            g.lance(num)
            verifie("lance", "refuse", f"TEMOIN test {num} sans voie connue")
        except ValueError:
            verifie("refuse", "refuse", f"test {num} refuse tant que la voie est inconnue (lancez le test 1)")
    g.lance(1)
    attend(lambda: g.en_cours is None, 5)
    verifie(statuts(g, 1), {"1a": "OK", "1b": "OK", "1c": "OK", "1d": "OK"}, "test 1 : cartes conformes -> 4 OK")
    verifie([r for r, _ in cartes.envoyees], ["maitre", "esclave", "esclave", "esclave"], "test 1 : commandes sur la bonne carte")
    verifie((g.voie, g.etat()["voie"]), ("Serial", "Serial"), "1d : voie Serial lue sur la cuve et exposee a la page")
    g, cartes, _ = nouvelle(voie=None)
    cartes.voie = "UDP"
    g.lance(1)
    attend(lambda: g.en_cours is None, 5)
    titre6 = next(t["titre"] for t in g.etat()["tests"] if t["num"] == 6)
    verifie((g.voie, "UDP" in titre6), ("UDP", True), "1d : voie UDP lue -> test 6 reconstruit dans sa variante UDP")
    g, _, _ = nouvelle(pannes={"voie_muette"}, voie=None)
    g.lance(1)
    attend(lambda: g.en_cours is None, 5)
    verifie((statuts(g, 1)["1d"], g.voie), ("ECHEC", None), "TEMOIN cuve sans VoieCommandes : 1d ECHEC, voie toujours inconnue")
    try:
        g.regle_voie("RS485")
        verifie("accepte", "refuse", "TEMOIN voie inconnue")
    except ValueError:
        verifie("refuse", "refuse", "regle_voie : seulement Serial ou UDP")
    g, _, _ = nouvelle(pannes={"rs485"})
    g.lance(1)
    attend(lambda: g.en_cours is None, 5)
    verifie(statuts(g, 1)["1c"], "ECHEC", "TEMOIN port RS485 ferme (false) -> 1c ECHEC")
    g, _, _ = nouvelle(pannes={"ferme"})
    g.lance(1)
    attend(lambda: g.en_cours is None, 5)
    verifie(statuts(g, 1)["1a"], "ECHEC", "TEMOIN port ferme : commande non envoyee -> ECHEC")

    # -- test 2 : surveillances (fenetre 300 s x 0,01 = 3 s)
    g, _, _ = nouvelle()
    verifie(g.etat()["reste"], None, "decompte : rien avant le lancement")
    g.lance(2)
    attend(lambda: g.etat()["reste"] is not None, 2)
    reste = g.etat()["reste"]
    verifie(isinstance(reste, int) and 0 < reste <= 300, True, f"decompte du test 2 en secondes reelles (reste = {reste})")
    for _ in range(10):
        g.observe("maitre", "MODBUS_TASMOTA_SLAVE_RELEVE: 3 demande(s) de lecture placee(s) dans la file")
        g.observe("esclave", "EXECUTE_CMD_MODBUS: -------------------- executeCmdModbus -------------------")
        for detail in ("DeviceAddress = 0x02", "StartAddress = 0x0560", "FunctionCode = 0x03", "Count = 5"):
            g.observe("esclave", "EXECUTE_CMD_MODBUS: " + detail)
        g.observe("maitre", 'MQT: tele/garage/RESULT = {"ModbusReceived": {"Trame": "02030A", "DeviceAddress": 2, "FunctionCode": 3}}')
    for _ in range(6):
        g.observe("maitre", "SUR_TIMEOUT: pas de reponse dans le delai imparti")
        g.observe("maitre", "TERMINE_EN_VOL: abandon d'un message sans reponse apres 1 tentative(s) (esclave 3, muet)")
    attend(lambda: g.en_cours is None, 8)
    s = statuts(g, 2)
    verifie((s["2a"], s["2b"], s["2c"], s["2e"], s["2k"]), ("OK", "OK", "OK", "OK", "INFO"),
            "test 2 : releves, cuve servie, 6 timeouts du rideau absent (esclave 3) -> 2c OK ; note = INFO")
    verifie((s["2m"], s["2n"], s["2o"]), ("INFO", "INFO", "OK"),
            "timeouts et abandons des autres esclaves : notes INFO ; reponses de la cuve recues : 2o OK")
    verifie((s["2p"], s["2q"], s["2r"]), ("OK", "OK", "OK"), "voie Serial : aucun envoi UDP vers la cuve, ni refus, ni tid rejete")
    detail_2b = next(v["detail"] for t in g.etat()["tests"] for v in t["verifs"] if v["cle"] == "2b")
    verifie(detail_2b, "10 fois", "2b compte les REQUETES executees (10), pas les 50 lignes EXECUTE_CMD_MODBUS")
    verifie(g.etat()["reste"], None, "decompte efface a la fin du test")
    g, _, _ = nouvelle()
    g.lance(2)
    g.observe("maitre", "ENFILE_MSG: file pleine, lecture ecartee")
    attend(lambda: statuts(g, 2)["2e"] == "ECHEC", 2)
    verifie((statuts(g, 2)["2e"], g.en_cours), ("ECHEC", 2), "TEMOIN file pleine : ECHEC aussitot, test toujours en cours")
    g.observe("maitre", "TERMINE_EN_VOL: abandon d'un message sans reponse apres 3 tentative(s) (esclave 2)")
    for _ in range(60):
        g.observe("esclave", "EXECUTE_CMD_MODBUS: DeviceAddress = 0x02")
    attend(lambda: g.en_cours is None, 8)
    s = statuts(g, 2)
    verifie((s["2a"], s["2c"], s["2o"]), ("ECHEC", "ECHEC", "ECHEC"),
            "TEMOIN aucun releve, message de la cuve abandonne, aucune reponse recue -> 2a, 2c et 2o ECHEC")
    verifie(s["2b"], "ECHEC", "TEMOIN 60 lignes de detail EXECUTE_CMD_MODBUS sans en-tete : 0 requete -> 2b ECHEC")

    # -- test 2 en voie UDP : envois UDP comptes, refus / IP inconnue / tid rejete interdits
    g, _, _ = nouvelle(voie="UDP")
    g.lance(2)
    for n in range(10):
        g.observe("maitre", "MODBUS_TASMOTA_SLAVE_RELEVE: 3 demande(s) de lecture placee(s) dans la file")
        g.observe("maitre", f"POMPE_QUEUE: envoi UDP a l'esclave d'ID=2 (apprise, IP 192.168.4.2) : ModbusUDP {n} 0203")
        g.observe("esclave", "EXECUTE_CMD_MODBUS: -------------------- executeCmdModbus -------------------")
        g.observe("maitre", 'MQT: tele/garage/RESULT = {"ModbusReceivedUDP": {"Trame": "02030A", "Info": {"voie":"UDP"}, '
                            '"DeviceAddress": 2, "FunctionCode": 3}}')
    attend(lambda: g.en_cours is None, 8)
    s = statuts(g, 2)
    verifie((s["2o"], s["2p"], s["2q"], s["2r"]), ("OK", "OK", "OK", "OK"),
            "voie UDP : 10 envois UDP et 10 ModbusReceivedUDP -> 2o, 2p OK ; rien d'interdit")
    g, _, _ = nouvelle(voie="UDP")
    g.lance(2)
    for _ in range(10):
        g.observe("maitre", 'MQT: tele/garage/RESULT = {"ModbusReceived": {"Trame": "02030A", "DeviceAddress": 2}}')
    g.observe("maitre", "POMPE_QUEUE: aucune IP connue pour l'esclave d'ID=2 (voie UDP) : message non envoye")
    g.observe("maitre", "APPARIE_REPONSE: reponse UDP de tid 4 rejetee (attendu 5, esclave 2)")
    attend(lambda: g.en_cours is None, 8)
    s = statuts(g, 2)
    verifie((s["2p"], s["2q"], s["2r"]), ("ECHEC", "ECHEC", "ECHEC"),
            "TEMOIN voie UDP mais requetes par le RS485, IP inconnue, tid rejete -> 2p, 2q, 2r ECHEC")
    g, _, _ = nouvelle(voie="Serial")
    g.lance(2)
    g.observe("maitre", "POMPE_QUEUE: envoi UDP a l'esclave d'ID=2 (fiche, IP 192.168.4.2) : ModbusUDP 1 0203")
    attend(lambda: statuts(g, 2)["2p"] == "ECHEC", 2)
    verifie(statuts(g, 2)["2p"], "ECHEC", "TEMOIN voie Serial mais un envoi UDP vers la cuve -> 2p ECHEC aussitot")
    g.arrete()
    attend(lambda: g.en_cours is None, 3)

    # -- test 6 en voie UDP : cable debranche, le P4 recoit toujours ; chien de garde interdit
    def flux_udp(g, arret, panne=None):
        """Reponses UDP de la cuve toutes les 50 ms ; panne : 'coupe' = plus rien apres 6a, 'muet' = chien de garde."""
        while not arret.is_set():
            if not (panne == "coupe" and statuts(g, 6).get("6a") == "OK"):
                g.observe("maitre", 'MQT: tele/garage/RESULT = {"ModbusReceivedUDP": {"Info": {"voie":"UDP"}, "DeviceAddress": 2}}')
            if panne == "muet" and statuts(g, 6).get("6p") == "en cours":
                g.observe("maitre", "MODBUS_TASMOTA_SLAVE_CHIEN_DE_GARDE: esclave Capteurs Cuve (ID=2) muet depuis 90 s")
            time.sleep(0.05)
    tout_ok = {"6x": "OK", "6z": "OK", "6y": "OK", "6a": "OK", "6b": "OK", "6p": "OK", "6q": "OK", "6c": "OK", "6d": "OK"}
    for panne, attendu, libelle in (
            (None, tout_ok, "test 6 en UDP : cable debranche 150 s, reponses toujours recues, aucun muet -> tout OK"),
            ("coupe", "6b", "TEMOIN plus aucune reponse UDP apres le debranchement -> 6b ECHEC"),
            ("muet", "6x", "TEMOIN chien de garde pendant l'observation -> 6x ECHEC")):
        g, _, _ = nouvelle(reponses=["fait", "fait"], voie="UDP")
        arret = threading.Event()
        threading.Thread(target=flux_udp, args=(g, arret, panne), daemon=True).start()
        g.lance(6)
        if panne is None:
            attend(lambda: statuts(g, 6).get("6p") == "en cours", 3)
            e = g.etat()
            verifie((e["reste_genre"], isinstance(e["reste"], int) and 0 < e["reste"] <= 150), ("etape", True),
                    f"pause 6p : decompte en secondes reelles (reste = {e['reste']})")
        attend(lambda: g.en_cours is None, 10)
        arret.set()
        s = statuts(g, 6)
        if isinstance(attendu, dict):
            verifie(s, attendu, libelle)
        else:
            verifie(s[attendu], "ECHEC", libelle)

    # -- test 3 : la carte 16 relais absente n'est pas un echec
    g, _, _ = nouvelle()
    g.lance(3)
    attend(lambda: g.en_cours is None, 5)
    verifie(statuts(g, 3)["3a"], "NON VU", "test 3 : carte 16 relais absente -> NON VU (optionnel), pas ECHEC")

    # -- test 4 : commande du ruban, consignes Oui
    g, cartes, _ = nouvelle(reponses=["oui", "oui"])
    g.lance(4)
    attend(lambda: g.en_cours is None, 8)
    s = statuts(g, 4)
    verifie(sorted(set(s.values())), ["OK"], "test 4 : ruban commande, pousse, vu, rendu en AUTO -> tout OK")
    verifie([c for r, c in cartes.envoyees], ["Power1 ON", "Power1 OFF", "RubanEsclave1 auto", "RubanEsclave1"],
            "test 4 : commandes envoyees au P4, ruban rendu en AUTO a la fin puis mode relu")
    g, _, _ = nouvelle(pannes={"auto_ko"}, reponses=["oui", "oui"])
    g.lance(4)
    attend(lambda: g.en_cours is None, 8)
    s = statuts(g, 4)
    verifie((s["4j"], s["4k"], s["4l"]), ("OK", "ECHEC", "ECHEC"),
            "TEMOIN ordre AUTO envoye mais ruban reste en MANUEL : la reponse a l'ordre ne suffit plus -> 4k, 4l ECHEC")

    # -- test 5 : le push de demarrage (seq 1) precede le changement local ; preuve cherchee depuis le Restart
    g, cartes, _ = nouvelle()
    g.lance(5)
    attend(lambda: g.en_cours is None, 8)
    s = statuts(g, 5)
    verifie(sorted(set(s.values())), ["OK"], "test 5 : push, redemarrage vu par le P4 (avant 5f), ruban en AUTO -> tout OK")
    verifie(s["5g"], "OK", "5g : ACCEPTE_SEQ emis AVANT le changement local de 5f, trouve depuis le Restart (5d)")
    g, _, _ = nouvelle(pannes={"sans_redemarrage"})
    g.lance(5)
    attend(lambda: g.en_cours is None, 8)
    verifie(statuts(g, 5)["5g"], "ECHEC", "TEMOIN le P4 ne voit pas le redemarrage -> 5g ECHEC")
    g, _, _ = nouvelle(pannes={"ruban"}, reponses=["non", "oui"])
    g.lance(4)
    attend(lambda: g.en_cours is None, 8)
    s = statuts(g, 4)
    verifie((s["4c"], s["4e"], s["4g"]), ("ECHEC", "ECHEC", "OK"),
            "TEMOIN ruban reste eteint : push allume absent et reponse Non -> ECHEC")
    g, _, _ = nouvelle(reponses=["oui", "oui"])
    g.lance(4)
    g.observe("maitre", "MODBUS_TASMOTA_SLAVE_ECART: relai n°1 (LEDs Cuve) : commande=ON, constate=OFF")
    attend(lambda: g.en_cours is None, 8)
    verifie(statuts(g, 4)["4i"], "ECHEC", "TEMOIN ecart commande / constate -> 4i ECHEC")

    # -- test 7 : discovery.json verifie sur le P4
    g, _, _ = nouvelle(pannes={"discovery"}, reponses=["oui"])
    g.lance(7)
    attend(lambda: g.en_cours is None, 8)
    s = statuts(g, 7)
    verifie(s["7d"], "ECHEC", "TEMOIN discovery.json non conforme (GRILLE_T7 KO) -> ECHEC sans attendre le delai")
    detail = next(v["detail"] for t in g.etat()["tests"] for v in t["verifs"] if v["cle"] == "7d")
    verifie("cle esclave2" in detail, True, "TEMOIN discovery : la raison du KO est dans le detail")

    # -- consigne, arret, garde-fous
    g, _, evenements = nouvelle()
    g.lance(6)
    verifie(attend(lambda: g.consigne is not None, 3), True, "test 6 : consigne affichee (debrancher le RS485)")
    verifie(g.etat()["consigne"]["boutons"], ["fait"], "consigne d'action : un seul bouton « C'est fait »")
    try:
        g.lance(1)
        verifie("lance", "refuse", "TEMOIN 2e test pendant le 1er")
    except OSError:
        verifie("refuse", "refuse", "un seul test a la fois")
    g.arrete()
    attend(lambda: g.en_cours is None, 3)
    s = statuts(g, 6)
    verifie((g.en_cours, g.consigne, s["6a"], s["6x"]), (None, None, "annule", "annule"),
            "arret pendant une consigne : test annule, consigne retiree")
    verifie(any(e.get("k") == "grille" for e in evenements), True, "etat de la grille diffuse a la page")
    for appel, nom in ((lambda: g.lance(99), "test inconnu"), (lambda: g.lance(2, duree=30), "duree hors bornes"),
                       (lambda: g.repond("peut-etre"), "reponse inconnue")):
        try:
            appel()
            verifie("accepte", "refuse", f"TEMOIN {nom}")
        except ValueError:
            verifie("refuse", "refuse", f"{nom} : refuse")
    # Reponse a une consigne : l'etat renvoye a la page est deja SANS la consigne (sinon le bouton restait
    # affiche, 2026-10-17), puis decompte de l'etape qui attend sa preuve (6b : 150 s)
    g, _, _ = nouvelle()
    g.lance(6)
    attend(lambda: g.consigne is not None, 3)
    version = g.etat()["version"]
    g.repond("fait")
    e = g.etat()
    verifie((e["consigne"], e["version"] > version), (None, True),
            "« C'est fait » : etat renvoye sans consigne, version plus recente (la page ecarte l'ancien)")
    attend(lambda: g.etat()["reste_genre"] == "etape", 2)
    e = g.etat()
    verifie((e["reste_genre"], isinstance(e["reste"], int) and 0 < e["reste"] <= 150), ("etape", True),
            f"decompte de l'etape 6b en secondes reelles (reste = {e['reste']})")
    g.arrete()
    attend(lambda: g.en_cours is None, 3)
    verifie((g.etat()["reste"], g.etat()["reste_genre"]), (None, None), "decompte efface apres l'arret")
    try:
        g.repond("fait")
        verifie("accepte", "refuse", "TEMOIN reponse sans consigne")
    except OSError:
        verifie("refuse", "refuse", "reponse sans consigne en attente : refusee")
    g.lance(2, duree=120)
    verifie(next(t["titre"] for t in g.etat()["tests"] if t["num"] == 2).startswith("Regime normal (120 s"), True,
            "duree du test 2 reglable (120 s)")
    g.arrete()
    attend(lambda: g.en_cours is None, 3)

    _integration(verifie, attend, monte_testeur)


def _integration(verifie, attend, monte_testeur):
    """La grille dans le vrai testeur : logs poses sur le maitre, lignes recues, route /grille."""
    t, sims, reseau, args = monte_testeur()
    sims["COM_M"].niveaux.update(slaveModbus="info", conn16channels="detail")
    sims["COM_E"].niveaux["slaveModbus"] = "info"
    t.cartes["maitre"].ouvre("COM_M", 115200)
    t.cartes["esclave"].ouvre("COM_E", 115200)
    attend(lambda: t.acquis["maitre"]["logs"] and t.acquis["esclave"]["logs"])
    attend(lambda: sims["COM_M"].niveaux["slaveModbus"] == "debug", 3)
    verifie((sims["COM_M"].niveaux["slaveModbus"], sims["COM_M"].niveaux["conn16channels"]), ("debug", "detail"),
            "maitre : slaveModbus monte a debug, conn16channels deja plus haut garde (jamais baisse)")
    verifie(sims["COM_E"].niveaux["slaveModbus"], "info", "TEMOIN esclave : slaveModbus non touche (seulement le maitre)")
    t.restaure_logs()
    verifie(attend(lambda: sims["COM_M"].niveaux["slaveModbus"] == "info", 3), True, "restauration : slaveModbus rendu")
    # Ligne longue (discovery.json, 579 octets) : envoyee par blocs, sinon le P4 en perd (Len 443, 2026-10-17)
    serie = sims["COM_M"].serie
    blocs, ecrit_origine = [], serie.write
    serie.write = lambda octets: (blocs.append(len(octets)), ecrit_origine(octets))[1]
    t.cartes["maitre"].ecrit(tg.BR_DISCOVERY)
    verifie(attend(lambda: tg.BR_DISCOVERY in sims["COM_M"].recus, 3), True, "commande discovery recue ENTIERE par la carte")
    verifie((len(blocs) > 1, max(blocs) <= 64), (True, True), f"commande longue envoyee par blocs de 64 octets au plus ({blocs})")
    blocs.clear()
    t.cartes["maitre"].ecrit("Status 5")
    verifie(blocs, [9], "TEMOIN commande courte : un seul envoi")
    serie.write = ecrit_origine
    try:
        testeur_udp_http.traite_post({"action": "lancer", "test": 2, "duree": 60}, t, "/grille")
        verifie("lance", "refuse", "TEMOIN POST /grille test 2 sans voie connue")
    except ValueError:
        verifie("refuse", "refuse", "POST /grille lancer test 2 : refuse tant que le test 1 n'a pas lu la voie")
    t.grille.regle_voie("Serial")
    etat = testeur_udp_http.traite_post({"action": "lancer", "test": 2, "duree": 60}, t, "/grille")
    verifie(etat["en_cours"], 2, "POST /grille lancer : test 2 en cours")
    sims["COM_M"].dit("MODBUS_TASMOTA_SLAVE_RELEVE: 3 demande(s) de lecture placee(s) dans la file")
    verifie(attend(lambda: any("RELEVE" in texte for _, texte in t.grille.lignes), 3), True,
            "les lignes des cartes parviennent a la grille")
    testeur_udp_http.traite_post({"action": "arreter"}, t, "/grille")
    verifie(attend(lambda: t.grille.en_cours is None, 5), True, "POST /grille arreter : test arrete")
    try:
        testeur_udp_http.traite_post({"action": "bidon"}, t, "/grille")
        verifie("accepte", "refuse", "TEMOIN action inconnue")
    except ValueError:
        verifie("refuse", "refuse", "POST /grille : action inconnue refusee")
    t.arrete()
