"""Onglet « Grille ModBus » du testeur UDP : la grille d'observation du garage (AUDIT_MODBUS_2026-09-29.md §6),
adaptee a UN esclave - la cuve - et jugee sur les logs des deux cartes (decide le 2026-10-17).

Un test = une suite d'ETAPES (commande envoyee puis preuve attendue, consigne a l'utilisateur, preuve attendue)
et des SURVEILLANCES qui courent pendant tout le test (compte d'occurrences, motif interdit, simple note).
Rien ici ne touche un port serie : la grille recoit les lignes (observe) et ecrit par le rappel 'ecrit', ce
qui la rend testable sans carte (test_testeur_udp_grille.py).

Genres :
  commande  ecrit 'commande' sur 'carte', puis attend 'motif' (sur 'carte_motif', defaut 'carte') dans 'delai' s
  attendu   attend 'motif' sur 'carte' dans 'delai' s, compte depuis la derniere commande ou consigne
  consigne  affiche 'consigne' ; boutons « C'est fait » (puis 'motif' attendu dans 'delai' s) ou Oui / Non
  compte    surveillance : nombre d'occurrences de 'motif' entre 'mini' et 'maxi' sur toute la duree du test
  interdit  surveillance : ECHEC des que 'motif' apparait
  note      surveillance : relevee seulement (INFO), jamais un echec
'optionnel' : un echec devient « NON VU » (jaune), pour ce qui depend du materiel branche.
'depuis'    : (attendu) cle d'une etape anterieure : la preuve se cherche depuis cette etape, pas la derniere.
"""

import json
import re
import threading
import time

OK, ECHEC, NON_VU, INFO, ATTENTE, EN_COURS, CONSIGNE, ANNULE = (
    "OK", "ECHEC", "NON VU", "INFO", "attente", "en cours", "consigne", "annule")
SURVEILLANCES = ("compte", "interdit", "note")
PERSIST_DEFAUT = {"id": 2, "power": 1, "registre": 1376}
DUREE_REGIME = 300                       # s : test 2 (regime normal), reglable dans la page (60-900)
ERREURS_BERRY = r"attribute_error|undeclared|writable attribute"

# Forme de /json/discovery.json, verifiee SUR le P4 (une ligne Berry < 800 octets, tampon serie de Tasmota) :
# cles = MAC de 12 hexa, fiches esclaveN du meme groupTopic que le maitre. Validee au berry.exe le 2026-10-17.
BR_DISCOVERY = ('Br import json import re var f=open("/json/discovery.json") var t=json.load(f.read()) f.close() '
                'var ko=[] var g=serveur["mqtt"].find("groupTopic1","") if !isinstance(t,map) ko.push("table illisible") '
                'else for k:t.keys() if size(k)!=12 || re.match("^[0-9A-Fa-f]+$",k)==nil ko.push("cle "+k) '
                'elif isinstance(t[k],map) for r:t[k].keys() if re.match("^esclave[0-9]+$",r)!=nil && '
                'isinstance(t[k][r],map) && t[k][r].find("groupTopic")!=g ko.push(k+"/"+r+" groupTopic="+'
                'str(t[k][r].find("groupTopic"))) end end end end end '
                'print("GRILLE_T7", size(ko)==0 ? "OK" : "KO", ko.concat(" | "))')


def cible_depuis_persist(chemin):
    """Persist du maitre -> {id, power, registre} de l'esclave a ruban virtuel (la cuve) ; defaut si illisible."""
    try:
        with open(chemin, encoding="utf-8") as f:
            persist = json.load(f)
        esclaves = persist["drivers"]["ModBus"]["environnement"]["TasmotaSlaveModBus"]
        for module in persist.get("modules", {}).values():
            for relai in module.get("environnement", {}).get("relais", {}).values():
                virtuel = str(relai.get("virtuel", ""))
                if relai.get("type") == 1376 and virtuel.startswith("ModBus_TasmotaSlaveModBus"):
                    esclave = esclaves[virtuel[len("ModBus_"):]]
                    return {"id": int(esclave["id"]), "power": int(relai["id"]),
                            "registre": 1376 + int(relai.get("idModBus", 1)) - 1}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return dict(PERSIST_DEFAUT)


def construit_grille(cible, duree_regime=DUREE_REGIME):
    """Les 7 tests, pour l'esclave 'cible' ({id, power, registre})."""
    i, p, reg = cible["id"], cible["power"], cible["registre"]
    n_releves = max(1, int(duree_regime) // 30 - 1)
    pousse = rf"POUSSE_ETAT: registre {reg} = "
    publie = rf"Publie sur le r.{{1,2}}seau ModBus pour le relai n.{{1,2}}{p}\b"
    ecart = rf"MODBUS_TASMOTA_SLAVE_ECART: relai n.{{1,2}}{p}\b"

    def v(cle, carte, libelle, genre, **plus):
        return dict(cle=cle, carte=carte, libelle=libelle, genre=genre, **plus)

    def retour_auto(t):
        """Ruban rendu en AUTO, PROUVE : la reponse a « RubanEsclave auto » donne le mode du dernier etat recu
        (constate le 2026-10-17 : {"Mode":"MANUEL","Reste":30,"Ordre":"auto"}) ; le mode 0 n'apparait qu'au
        releve suivant (toutes les 30 s), puis la commande sans argument le confirme."""
        return [
            v(f"{t}j", "maitre", f"ordre AUTO envoye au ruban (RubanEsclave{p} auto)", "commande",
              commande=f"RubanEsclave{p} auto", motif=rf'"RubanEsclave{p}"\s*:.*"Ordre"\s*:\s*"auto"', delai=6),
            v(f"{t}k", "maitre", "le P4 relit le ruban en AUTO (mode = 0 au releve suivant)", "attendu", delai=45,
              motif=rf'"StartAddress"\s*:\s*{reg}\s*,.*"Values"\s*:\s*\[\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*0\s*\]'),
            v(f"{t}l", "maitre", "le ruban est bien en mode AUTO", "commande", commande=f"RubanEsclave{p}",
              motif=rf'"RubanEsclave{p}"\s*:\s*\{{\s*"Mode"\s*:\s*"AUTO"', motif_echec=r'"Mode"\s*:\s*"MANUEL".*', delai=6)]

    return [
        {"num": 1, "titre": "Demarrage : modules ModBus charges, port RS485 de la cuve ouvert", "fenetre": 0, "verifs": [
            v("1a", "maitre", "controleModbus charge sur le P4", "commande",
              commande='Br import global print("GRILLE_T1_MAITRE", global.contains("controleModbus"))',
              motif=r"GRILLE_T1_MAITRE true", delai=8),
            v("1b", "esclave", "controleModbus charge sur la cuve", "commande",
              commande='Br import global print("GRILLE_T1_ESCLAVE", global.contains("controleModbus"))',
              motif=r"GRILLE_T1_ESCLAVE true", delai=8),
            v("1c", "esclave", "port RS485 ouvert (serialModBus non nil)", "commande",
              commande='Br print("GRILLE_T1_RS485", modbusFonctions.etat()["serialModBus"] != nil)',
              motif=r"GRILLE_T1_RS485 true", delai=8)]},
        {"num": 2, "titre": f"Regime normal ({int(duree_regime)} s sans rien toucher)", "fenetre": int(duree_regime), "verifs": [
            v("2a", "maitre", f"releve des esclaves toutes les 30 s (au moins {n_releves})", "compte",
              motif=r"MODBUS_TASMOTA_SLAVE_RELEVE: \d+ demande", mini=n_releves),
            # Une requete executee ecrit 6 lignes EXECUTE_CMD_MODBUS (constate le 2026-10-17 : « 180 fois » pour
            # 30 requetes) : seule la ligne d'en-tete compte une requete.
            v("2b", "esclave", f"la cuve recoit et execute les requetes (au moins {n_releves} executeCmdModbus)", "compte",
              motif=r"EXECUTE_CMD_MODBUS: -+ executeCmdModbus", mini=n_releves),
            # La cuve peut executer sans que sa reponse arrive (constate le 2026-10-17 : 60 EXECUTE, 0 recu
            # par le P4). Preuve cote maitre : la publication ModbusReceived du pont (sauf SetOption158), ou
            # le detail de slaveModbus.
            v("2o", "maitre", f"le P4 recoit les reponses de la cuve (au moins {n_releves} ModbusReceived d'adresse {i})",
              "compte", mini=n_releves,
              motif=rf"""ModbusReceived.*"DeviceAddress": ?{i}[,}}]|RECUPERE_REPONSE_TASMOTA_SLAVE_MODBUS: value = .*'DeviceAddress': {i}[,}}]"""),
            # SUR_TIMEOUT ne dit pas l'esclave : un esclave absent du bus (rideau, carte 16 relais) en produit un
            # par releve (constate le 2026-10-17 : 6 en 300 s, cuve servie 60 fois). Seul l'abandon le nomme.
            v("2c", "maitre", f"aucun message abandonne pour la cuve (TERMINE_EN_VOL esclave {i}, ESCLAVE_MUET)", "interdit",
              motif=rf"TERMINE_EN_VOL: abandon .*\(esclave {i}[,)]|ESCLAVE_MUET: esclave d'ID={i} "),
            v("2d", "maitre", "jamais de reponse hors-sequence", "interdit", motif=r"reponse hors-sequence rejetee"),
            v("2e", "maitre", "jamais de file pleine", "interdit", motif=r"ENFILE_MSG: file pleine"),
            v("2f", "maitre", "persist complet (aucun MODBUS_TASMOTA_SLAVE_ERREUR)", "interdit",
              motif=r"MODBUS_TASMOTA_SLAVE_ERREUR"),
            v("2g", "maitre", f"la cuve (ID={i}) n'est jamais declaree muette", "interdit",
              motif=rf"CHIEN_DE_GARDE: esclave .*\(ID={i}\) muet"),
            v("2h", "maitre", "aucun ecart commande / constate sur le ruban", "interdit", motif=ecart),
            v("2i", "maitre", "aucune erreur Berry sur le P4", "interdit", motif=ERREURS_BERRY),
            v("2j", "esclave", "aucune erreur Berry sur la cuve", "interdit", motif=ERREURS_BERRY),
            v("2k", "maitre", "temperature de la cuve recue (seulement si elle change)", "note",
              motif=r"nouvelle valeur du thermom"),
            v("2l", "maitre", "niveau de la cuve recu (seulement s'il change)", "note",
              motif=r"nouvelle valeur de l'entr.{1,2}e analogique"),
            v("2m", "maitre", "SUR_TIMEOUT, tous esclaves confondus (un par releve pour chaque esclave absent du bus)",
              "note", motif=r"SUR_TIMEOUT: pas de reponse"),
            v("2n", "maitre", "esclaves sans reponse (messages abandonnes, autres esclaves compris)", "note",
              motif=r"TERMINE_EN_VOL: abandon")]},
        {"num": 3, "titre": "Carte 16 relais (si elle est branchee)", "fenetre": 40, "verifs": [
            v("3a", "maitre", "sondage de la carte 16 relais", "compte",
              motif=r"MODBUS_RECUPERE_REPONSE_CONN16CHANNEL", mini=1, optionnel=True),
            v("3b", "maitre", "pas de chien de garde de la carte 16 relais", "interdit",
              motif=r"MODBUS_CONN_16CH_CHIEN_DE_GARDE"),
            v("3c", "maitre", "ECART voie (16 d'un coup a la 1re reponse = cavalier M0 connecte)", "note",
              motif=r"ECART voie")]},
        {"num": 4, "titre": f"Commande du ruban de la cuve depuis le P4 (Power{p})", "fenetre": 0, "verifs": [
            v("4i", "maitre", "aucun ecart commande / constate sur le ruban", "interdit", motif=ecart),
            v("4a", "maitre", f"Power{p} ON publie sur le reseau ModBus", "commande", commande=f"Power{p} ON",
              motif=publie, delai=6),
            v("4b", "esclave", "la cuve execute la commande", "attendu", motif=r"EXECUTE_CMD_MODBUS", delai=6),
            v("4c", "esclave", "la cuve pousse son ruban allume", "attendu", motif=pousse + r"\[\d+, \d+, [1-9]", delai=6),
            v("4d", "maitre", "le P4 recoit le push", "attendu", motif=r"msg = ModbusPushUDP", delai=6),
            v("4e", "esclave", "le ruban de la cuve est-il ALLUME ?", "consigne", reponse="ouinon",
              consigne="Regardez le ruban de la cuve : est-il ALLUME ?"),
            v("4f", "maitre", f"Power{p} OFF publie sur le reseau ModBus", "commande", commande=f"Power{p} OFF",
              motif=publie, delai=6),
            v("4g", "esclave", "la cuve pousse son ruban eteint", "attendu", motif=pousse + r"\[\d+, \d+, 0\b", delai=6),
            v("4h", "esclave", "le ruban de la cuve est-il ETEINT ?", "consigne", reponse="ouinon",
              consigne="Regardez le ruban de la cuve : est-il ETEINT ?")] + retour_auto(4)},
        {"num": 5, "titre": "Push spontane de la cuve vers le P4, puis redemarrage de la cuve (seq)", "fenetre": 0, "verifs": [
            v("5a", "esclave", "changement local du ruban (Power1 TOGGLE sur la cuve) pousse", "commande",
              commande="Power1 TOGGLE", motif=pousse + r".*seq \d+", delai=6),
            v("5b", "maitre", "le P4 recoit le push sans attendre le releve", "attendu", motif=r"msg = ModbusPushUDP", delai=4),
            v("5c", "esclave", "retour a l'etat d'origine (Power1 TOGGLE), pousse aussi", "commande",
              commande="Power1 TOGGLE", motif=pousse, delai=6),
            v("5d", "esclave", "redemarrage de la cuve (Restart 1)", "commande", commande="Restart 1",
              motif=r"Restart", delai=6),
            v("5e", "esclave", "la cuve a redemarre", "attendu", motif=r"Nb\. de boot|RestartReason", delai=90),
            v("5f", "esclave", "nouveau changement local apres le redemarrage", "commande", commande="Power1 TOGGLE",
              motif=pousse, delai=20),
            # La cuve pousse son seq 1 DES SON DEMARRAGE, avant le changement local de 5f (constate le 2026-10-17 :
            # ACCEPTE_SEQ a 20:33:52.965, 5f a 20:33:55) : la preuve se cherche depuis le Restart (5d).
            v("5g", "maitre", f"le P4 voit le redemarrage (ACCEPTE_SEQ ... ID={i} redemarre)", "attendu",
              motif=rf"ACCEPTE_SEQ: esclave d'ID={i} redemarre", delai=10, depuis="5d"),
            v("5h", "esclave", "retour a l'etat d'origine", "commande", commande="Power1 TOGGLE", motif=pousse, delai=6),
            ] + retour_auto(5)},
        {"num": 6, "titre": "Panne : cable RS485 de la cuve debranche puis rebranche", "fenetre": 0, "verifs": [
            v("6x", "maitre", f"chien de garde declenche UNE seule fois", "compte",
              motif=rf"CHIEN_DE_GARDE: esclave .*\(ID={i}\) muet", mini=1, maxi=1),
            v("6y", "maitre", "jamais de file pleine", "interdit", motif=r"ENFILE_MSG: file pleine"),
            v("6a", "maitre", "cable RS485 de la cuve debranche", "consigne", reponse="fait",
              consigne="Debranchez le cable RS485 de la cuve (laissez-la alimentee), puis cliquez « C'est fait ». "
                       "Le chien de garde du P4 doit reagir sous 90 a 120 s."),
            v("6b", "maitre", f"le P4 declare la cuve (ID={i}) muette", "attendu",
              motif=rf"CHIEN_DE_GARDE: esclave .*\(ID={i}\) muet", delai=150),
            v("6c", "maitre", "cable RS485 rebranche", "consigne", reponse="fait",
              consigne="Rebranchez le cable RS485 de la cuve, puis cliquez « C'est fait »."),
            v("6d", "maitre", f"le P4 voit la cuve repondre de nouveau", "attendu",
              motif=rf"l'esclave d'ID={i} repond de nouveau", delai=90)]},
        {"num": 7, "titre": "Decouverte : point d'acces, ImAlive, forme de discovery.json", "fenetre": 0, "verifs": [
            v("7x", "maitre", "jamais d'ImAlive illisible", "interdit", motif=r"ImAlive illisible"),
            v("7a", "maitre", "point d'acces du P4 actif (RgxState ON)", "commande", commande="RgxState",
              motif=r'"RgxState"\s*:\s*"ON"', delai=6),
            v("7b", "esclave", "la cuve envoie son ImAlive", "commande", commande="ReglageUDP forceEnvoiParams ON",
              motif=r"forceEnvoiParams|ReglageUDP", delai=6),
            v("7c", "maitre", "le P4 range la fiche de la cuve", "attendu",
              motif=r"a re.{1,2}u les param.{1,2}tres de l'esclave", delai=15),
            v("7d", "maitre", "discovery.json : cles MAC, groupTopic des esclaves", "commande", commande=BR_DISCOVERY,
              motif=r"GRILLE_T7 OK", motif_echec=r"GRILLE_T7 KO.*", delai=10),
            v("7e", "maitre", "page /discovery complete", "consigne", reponse="ouinon",
              consigne="Ouvrez http://<IP du P4>/discovery : la page est-elle complete (boutons en bas) ?")]},
    ]


class Grille:
    """Execute un test a la fois, dans un thread. ecrit(role, commande) -> bool ; diffuse(evenement)."""

    def __init__(self, ecrit, diffuse, cible=None, echelle=1.0):
        self.ecrit, self.diffuse, self.echelle = ecrit, diffuse, echelle
        self.cible = dict(cible or PERSIST_DEFAUT)
        self.duree_regime = DUREE_REGIME
        self.tests = construit_grille(self.cible, self.duree_regime)
        self.resultats = {}                 # cle -> {"statut", "detail"}
        self.cond = threading.Condition()
        self.lignes = []                    # (role, texte) depuis le debut du test en cours
        self.en_cours, self.consigne, self.reponse, self.arret = None, None, None, False
        self.ancre = 0                      # index de la derniere commande / consigne
        self.ancres = {}                    # cle d'etape -> son ancre (option 'depuis')
        self.vues = {}                      # surveillance : cle -> [index deja lu, lignes vues]
        self.fin_fenetre = None             # time.monotonic() de fin de la fenetre d'observation (decompte de la page)
        self.fin_etape = None               # idem, fin du delai de l'etape qui attend sa preuve
        self.version = 0                    # croit a chaque changement : la page ecarte un etat plus ancien
        self.instance = f"{time.time():.3f}"  # distingue un testeur relance (sa version repart de 0)

    # ------------------------------------------------------------------ entrees
    def observe(self, role, texte, t=None):
        with self.cond:
            if self.en_cours is not None:
                self.lignes.append((role, texte))
                self.cond.notify_all()

    def lance(self, num, duree=None):
        with self.cond:
            if self.en_cours is not None:
                raise OSError(f"le test {self.en_cours} est deja en cours")
            if duree is not None:
                duree = int(duree)
                if not 60 <= duree <= 900:
                    raise ValueError("duree du test 2 : 60 a 900 s")
                self.duree_regime = duree
                self.tests = construit_grille(self.cible, duree)
            test = next((t for t in self.tests if t["num"] == int(num)), None)
            if test is None:
                raise ValueError(f"test inconnu : {num!r}")
            self.en_cours, self.lignes, self.ancre, self.reponse, self.arret = test["num"], [], 0, None, False
            self.ancres = {}
        threading.Thread(target=self._execute, args=(test,), daemon=True).start()

    def repond(self, reponse):
        if reponse not in ("fait", "oui", "non"):
            raise ValueError(f"reponse inconnue : {reponse!r}")
        with self.cond:
            if self.consigne is None:
                raise OSError("aucune consigne en attente")
            self.reponse = reponse
            self.cond.notify_all()
            # L'etat renvoye a la page doit deja etre SANS la consigne : sinon cette reponse HTTP, arrivee apres
            # les mises a jour diffusees, reaffichait le bouton jusqu'au changement suivant (2026-10-17, test 6).
            self.cond.wait_for(lambda: self.consigne is None or self.arret, timeout=2)

    def arrete(self):
        with self.cond:
            self.arret = True
            self.cond.notify_all()

    def etat(self):
        fin, genre = (self.fin_fenetre, "fenetre") if self.fin_fenetre is not None else (self.fin_etape, "etape")
        reste = None if fin is None else max(0, round((fin - time.monotonic()) / self.echelle))
        return {"cible": self.cible, "duree_regime": self.duree_regime, "en_cours": self.en_cours,
                "consigne": self.consigne, "reste": reste, "reste_genre": genre if reste is not None else None,
                "version": self.version, "instance": self.instance,
                "tests": [{"num": t["num"], "titre": t["titre"],
                           "verifs": [{"cle": v["cle"], "carte": v["carte"], "libelle": v["libelle"], "genre": v["genre"],
                                       **self.resultats.get(v["cle"], {"statut": ATTENTE, "detail": ""})}
                                      for v in t["verifs"]]} for t in self.tests]}

    # ------------------------------------------------------------------ execution
    def _note(self, v, statut, detail=""):
        self.resultats[v["cle"]] = {"statut": statut, "detail": detail[:220]}
        self.version += 1
        self.diffuse({"k": "grille", **self.etat()})

    def _trouve(self, motif, carte, depuis=0):
        """-> la 1re ligne de 'carte' qui contient 'motif' a partir de l'index 'depuis', ou None."""
        rx = re.compile(motif)
        for role, texte in self.lignes[depuis:]:
            if role == carte and rx.search(texte):
                return texte
        return None

    def _attend(self, motif, carte, delai, depuis, motif_echec=None):
        """-> (ligne trouvee, ligne d'echec) ; (None, None) au bout du delai ou sur arret."""
        fin = time.monotonic() + delai * self.echelle
        with self.cond:
            while not self.arret:
                trouve = self._trouve(motif, carte, depuis)
                if trouve:
                    return trouve, None
                if motif_echec:
                    rate = self._trouve(motif_echec, carte, depuis)
                    if rate:
                        return None, rate
                reste = fin - time.monotonic()
                if reste <= 0:
                    return None, None
                self.cond.wait(min(reste, 0.5))
        return None, None

    def _echec(self, v, detail):
        self._note(v, NON_VU if v.get("optionnel") else ECHEC, detail)

    def _etape(self, v):
        genre = v["genre"]
        if genre == "consigne":
            boutons = ["fait"] if v.get("reponse") == "fait" else ["oui", "non"]
            with self.cond:
                self.reponse, self.consigne = None, {"cle": v["cle"], "texte": v["consigne"], "boutons": boutons}
            self._note(v, CONSIGNE, v["consigne"])
            with self.cond:
                while self.reponse is None and not self.arret:
                    self.cond.wait(0.5)
                reponse, self.consigne, self.ancre = self.reponse, None, len(self.lignes)
                self.ancres[v["cle"]] = self.ancre
                self.cond.notify_all()                       # libere repond(), qui attend la consigne retiree
            if reponse is None:
                return
            self._note(v, ECHEC if reponse == "non" else OK, f"reponse : {reponse}")
            return
        if genre == "commande":
            with self.cond:
                self.ancre = self.ancres[v["cle"]] = len(self.lignes)
            if not self.ecrit(v["carte"], v["commande"]):
                self._echec(v, f"port de la carte {v['carte']} ferme : commande non envoyee")
                return
        delai = v.get("delai", 10)
        depuis = self.ancres.get(v["depuis"], self.ancre) if v.get("depuis") else self.ancre
        self.fin_etape = time.monotonic() + delai * self.echelle      # decompte de la page
        self._note(v, EN_COURS)
        carte = v.get("carte_motif", v["carte"])
        trouve, rate = self._attend(v["motif"], carte, delai, depuis, v.get("motif_echec"))
        self.fin_etape = None
        if trouve:
            self._note(v, OK, trouve)
        elif rate:
            self._echec(v, rate)
        elif not self.arret:
            self._echec(v, f"rien vu en {delai} s sur la carte {carte} (attendu : {v['motif']})")

    def _surveille(self, v, final):
        """Surveillance : -> True si son verdict est definitif."""
        rx = re.compile(v["motif"])
        suivi = self.vues.setdefault(v["cle"], [0, []])       # incremental : le test 2 cumule des milliers de lignes
        suivi[1] += [texte for role, texte in self.lignes[suivi[0]:] if role == v["carte"] and rx.search(texte)]
        suivi[0] = len(self.lignes)
        vues = suivi[1]
        n = len(vues)
        if v["genre"] == "interdit":
            if n:
                self._echec(v, "vu : " + vues[0])
                return True
            if final:
                self._note(v, OK, "jamais vu pendant le test")
            return final
        if v["genre"] == "note":
            if final:
                self._note(v, INFO, f"{n} fois" + (" ; derniere : " + vues[-1] if n else ""))
            return final
        mini, maxi = v.get("mini", 0), v.get("maxi")
        if maxi is not None and n > maxi:
            self._echec(v, f"{n} fois (au plus {maxi}) ; derniere : {vues[-1]}")
            return True
        if final:
            if n >= mini:
                self._note(v, OK, f"{n} fois")
            else:
                self._echec(v, f"{n} fois (au moins {mini} attendu(s))")
        return final

    def _execute(self, test):
        etapes = [v for v in test["verifs"] if v["genre"] not in SURVEILLANCES]
        surveillances = [v for v in test["verifs"] if v["genre"] in SURVEILLANCES]
        for v in test["verifs"]:
            self.resultats.pop(v["cle"], None)
            self.vues.pop(v["cle"], None)
        for v in surveillances:
            self._note(v, EN_COURS)
        debut = time.monotonic()
        tranchees = set()
        for v in etapes:
            if self.arret:
                break
            self._etape(v)
            with self.cond:
                for s in surveillances:
                    if s["cle"] not in tranchees and self._surveille(s, False):
                        tranchees.add(s["cle"])
        fin = debut + test["fenetre"] * self.echelle
        if test["fenetre"] and not self.arret:
            self.fin_fenetre = fin
            self.version += 1
            self.diffuse({"k": "grille", **self.etat()})      # la page demarre son decompte
        with self.cond:
            while not self.arret and time.monotonic() < fin:
                for s in surveillances:
                    if s["cle"] not in tranchees and self._surveille(s, False):
                        tranchees.add(s["cle"])
                self.cond.wait(min(1.0, max(0.0, fin - time.monotonic())))
            for s in surveillances:
                if s["cle"] not in tranchees:
                    if self.arret:
                        self._note(s, ANNULE, "test arrete")
                    else:
                        self._surveille(s, True)
            for v in etapes:
                if self.arret and self.resultats.get(v["cle"], {}).get("statut") in (None, ATTENTE, EN_COURS, CONSIGNE):
                    self.resultats[v["cle"]] = {"statut": ANNULE, "detail": "test arrete"}
            self.en_cours, self.consigne, self.fin_fenetre, self.fin_etape = None, None, None, None
            self.version += 1
        self.diffuse({"k": "grille", **self.etat()})
