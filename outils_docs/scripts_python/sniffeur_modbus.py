r"""Sniffeur ModBus RTU (RS485) avec page web locale, par un convertisseur USB-RS485 branche sur le bus.

Materiel vise : Waveshare USB TO RS485 (CH343G + SP485EEN, direction automatique).
Bornes : A+ -> A du bus, B- -> B du bus, GND -> masse du bus.

Ce que fait ce serveur :
    - ecoute le bus SANS EMETTRE : chaque trame est decoupee (CRC) et decodee (decodeur_modbus.py) :
      la norme ModBus champ par champ, puis le sens metier selon l'esclave vise - carte 16 relais
      (modBus_Conn16channels) ou ESP32 Tasmota (modBus_TasmotaSlaveModBus), d'apres le persist du maitre ;
    - apparie requetes et reponses : latence par esclave, requetes restees sans reponse
      (au-dela de --delai s), exceptions, trames CRC KO ;
    - surveille (surveillance_modbus.py) : ecart entre l'etat commande d'un relais et son releve,
      collisions (deux maitres, reponse non sollicitee, rafale de CRC faux) -> alertes dans le fil ;
    - depuis la page : port et debit (Fermer LIBERE le port), envoi de trames (CRC ajoute, rafale),
      raccourcis carte 16 relais, recherche / correction de son debit et de son adresse
      (debit_modbus.py), emulation des esclaves du persist avec valeurs editables (emulation_modbus.py) ;
    - ecoute aussi le PUSH UDP des esclaves (ecoute_udp.py, multicast 224.3.0.1:4000, rien n'est emis) :
      le plan telemetrie ne passe pas par le RS485 ; chaque push est decode et juge comme le maitre
      (numero d'ordre : accepte, ecarte, push perdus, redemarrage) ;
    - onglet Aide : regles de formation des trames, registres de l'installation, decodeur manuel,
      procedure d'essai sur le bus reel ;
    - journal fichier optionnel (--journal).
Routes HTTP : sniffeur_modbus_http.py ; page : sniffeur_modbus_web.py (+ sniffeur_modbus_aide.py).

UN SEUL MAITRE SUR LE BUS : envoyer depuis la page (trames, recherche du debit) fait du PC un maitre.
Si le P4 sonde le bus en meme temps, les trames se percutent -> charger test_liaison_modbus.be sur le
P4 (il suspend sa file) ou le debrancher. L'emulation : debrancher l'esclave reel emule.

ECHO LOCAL : certains convertisseurs renvoient ce qu'ils emettent. Une reponse 0x05/0x06 etant l'echo
exact de la requete, on ne peut pas jeter « toute trame identique a l'envoi » : --echo auto (defaut)
l'apprend au premier envoi d'une trame qui n'est pas 0x05/0x06 ; --echo oui | non pour l'imposer.

Usage (Python de PlatformIO, qui fournit pyserial) :
    %USERPROFILE%\.platformio\penv\Scripts\python.exe outils_docs/scripts_python/sniffeur_modbus.py
    options : --port auto|COM12|loop://|aucun  --debit 19200  --http 7300  --silence 0.02  --delai 1.0
              --echo auto|oui|non  --journal fichier.log  --historique 5000  --persist <persist du maitre>
              --udp oui|non  --udp-groupe 224.3.0.1  --udp-port 4000  --udp-interface <ip locale>
    --port auto (defaut) : le SEUL port CH343 present ; sinon demarre port ferme, a choisir sur la page.
Depuis VS Code : pioarduino > Project Tasks > <env> > Custom > « Sniffeur ModBus (HTTP 127.0.0.1) »
(cible_sniffeur_modbus.py). Arret : Ctrl+C dans le terminal de la tache (ou la corbeille).
"""

import argparse
import collections
import json
import os
import queue
import sys
import threading
import time
from http.server import ThreadingHTTPServer

import serial
from serial.tools import list_ports

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import debit_modbus                                         # noqa: E402
import decodeur_modbus as dm                                # noqa: E402
import ecoute_udp                                           # noqa: E402
import emulation_modbus                                     # noqa: E402
import test_rs485_pc as rs                                  # noqa: E402
from sniffeur_modbus_http import VID_PID_CH343, fabrique_gestionnaire      # noqa: E402
from surveillance_modbus import Surveillance               # noqa: E402

DELAI_ECHO = 0.5                # s : fenetre ou une trame identique a notre envoi peut en etre l'echo
SONDE_ECHO = 0.3                # s : sans echo dans ce delai, le convertisseur n'en produit pas


def port_auto():
    """Le seul port CH343 present, sinon None (les cartes ESP32 en portent souvent un aussi)."""
    ports = [p.device for p in list_ports.comports() if (p.vid, p.pid) == VID_PID_CH343]
    return ports[0] if len(ports) == 1 else None


def maintenant_texte():
    return time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"


class Sniffeur:
    def __init__(self, args):
        self.args = args
        self.journal = open(args.journal, "a", encoding="utf-8") if args.journal else None
        self.verrou = threading.Lock()          # historique, statistiques, pages web
        self.verrou_port = threading.Lock()     # ouverture / fermeture / ecriture / debit du port
        self.port = None
        self.nom_port, self.debit, self.erreur = "", args.debit, ""
        self.historique = collections.deque(maxlen=args.historique)
        self.clients_web = []
        self.stats = {}                         # {id: {id, requetes, reponses, sans_reponse, exceptions, lat, lat_max}}
        self.nb, self.nb_ko, self.nb_alertes, self.t_prec = 0, 0, 0, None
        self.attendue = None                    # (trame, instant) de la requete en attente de reponse
        self.dernier_envoi, self.t_envoi = None, 0.0
        self.echo_local = {"oui": True, "non": False}.get(args.echo)     # None = a apprendre
        self.sonde_echo = None                  # (trame, instant) d'un envoi qui revelera l'echo
        self.capture = None                     # (predicat, evenement, boite) d'une transaction en cours
        self.tache, self.resultat_debit = None, None
        self.derniers_seq, self.nb_push, self.udp_texte = {}, 0, "non ecoute"     # push UDP (ecoute_udp.py)
        self.carte = dm.charge_carte(args.persist)      # qui est quoi, lu dans le persist du maitre
        self.bus = dm.lit_bus(args.persist)
        self.types = dm.charge_types_gpio()
        self.emulation = emulation_modbus.Emulation(self.carte, args.debit)
        self.surveillance = Surveillance(self.carte, args.delai)
        self.debut = time.strftime("%d/%m %H:%M:%S")

    # ------------------------------------------------------------------ diffusion vers les pages
    def etat(self):
        return {"port": self.nom_port, "debit": self.debit, "ouvert": self.port is not None,
                "erreur": self.erreur, "emulation": sorted(self.emulation.actifs), "nb": self.nb, "ko": self.nb_ko,
                "alertes": self.nb_alertes, "push": self.nb_push, "udp": self.udp_texte, "depuis": self.debut, "delai": self.args.delai, "tache": self.tache,
                "echo": {None: "?", True: "oui", False: "non"}[self.echo_local],
                "persist": os.path.relpath(self.args.persist, dm.RACINE), "esclaves": len(self.carte)}

    @staticmethod
    def _paquet(evenement, donnees):
        return f"event: {evenement}\ndata: {json.dumps(donnees)}\n\n".encode("utf-8")

    def _diffuse(self, paquets, memorise=None):
        """Appelee SOUS self.verrou."""
        if memorise is not None:
            self.historique.append(memorise)
        for file in self.clients_web:
            for paquet in paquets:
                file.put(paquet)

    def evenement(self, nom, donnees):
        with self.verrou:
            self._diffuse([self._paquet(nom, donnees)])

    def diffuse_etat(self):
        self.evenement("etat", self.etat())

    def diffuse_emulation(self):
        self.evenement("emulation", self.emulation.etat())

    def message(self, texte):
        print(texte)
        self.evenement("message", {"texte": texte})

    def inscrit_web(self):
        file = queue.Queue()
        with self.verrou:
            for paquet in (self._paquet("etat", self.etat()), self._paquet("stats", list(self.stats.values())),
                           self._paquet("emulation", self.emulation.etat()), *self.historique):
                file.put(paquet)
            self.clients_web.append(file)
        return file

    def desinscrit_web(self, file):
        with self.verrou:
            if file in self.clients_web:
                self.clients_web.remove(file)

    # ------------------------------------------------------------------ port serie
    def ouvre(self, nom, debit):
        self.ferme()
        with self.verrou_port:
            try:
                port = serial.serial_for_url(nom, debit, bytesize=8, parity=serial.PARITY_NONE,
                                             stopbits=1, timeout=0, do_not_open=True)
                port.dtr, port.rts = False, False   # comme pont_serie : un port d'ESP32 choisi par erreur ne le resette pas
                port.open()
                port.reset_input_buffer()
                self.port, self.erreur = port, ""
            except (serial.SerialException, ValueError) as erreur:
                self.erreur = f"ouverture de {nom} impossible : {erreur}"
            self.nom_port, self.debit = nom, debit
        self.diffuse_etat()
        if self.erreur:
            raise OSError(self.erreur)
        print(f"port {nom} ouvert a {debit} bauds")

    def ferme(self, raison=""):
        with self.verrou_port:
            port, self.port = self.port, None
            if port is not None:
                try:
                    port.close()
                except (serial.SerialException, OSError):
                    pass
            if raison:
                self.erreur = raison
        if port is not None:
            self.diffuse_etat()

    def change_debit(self, debit):
        """Debit du port ouvert, a chaud (recherche du debit de la carte relais)."""
        with self.verrou_port:
            if self.port is None:
                raise OSError("port serie ferme")
            self.port.baudrate = debit
            self.port.reset_input_buffer()
            self.debit = debit
        self.diffuse_etat()

    def envoie(self, trame, source="pc"):
        with self.verrou_port:
            if self.port is None:
                raise OSError("port serie ferme : l'ouvrir d'abord")
            self.port.write(trame)
            self.port.flush()
            self.dernier_envoi, self.t_envoi = bytes(trame), time.monotonic()
            if self.echo_local is None and self.sonde_echo is None and len(trame) > 1 and trame[1] not in (5, 6):
                self.sonde_echo = (bytes(trame), self.t_envoi)     # aucun esclave ne renvoie cette trame a l'identique
        self.traite(trame, source)

    def transaction(self, trame, predicat, attente):
        """Emet une trame et attend une trame du bus qui satisfait predicat ; la rend, ou None."""
        evenement, boite = threading.Event(), {}
        with self.verrou:
            self.capture = (predicat, evenement, boite)
        try:
            self.envoie(trame)
            evenement.wait(attente + self.args.silence + 0.1)
            return boite.get("trame")
        finally:
            with self.verrou:
                self.capture = None

    def rafale(self, trame, repete, intervalle):
        try:
            for k in range(repete):
                if k:
                    time.sleep(intervalle)
                self.envoie(trame)
        except (OSError, serial.SerialException) as erreur:
            self.message(f"envoi interrompu : {erreur}")

    # ------------------------------------------------------------------ carte relais : debit et adresse
    def cible_conn16(self):
        cartes = [e for e in self.carte.values() if e["driver"] == "conn16"]
        if not cartes:
            raise ValueError("aucune carte 16 relais dans le persist du maitre")
        return {"debit": self.bus["debit"], "id": cartes[0]["id"]}

    def lance_debit(self, action):
        if action not in ("chercher", "corriger"):
            raise ValueError("action chercher ou corriger")
        if self.port is None:
            raise OSError("port serie ferme : l'ouvrir d'abord")
        if self.tache:
            raise OSError(f"{self.tache} deja en cours")
        if action == "corriger" and not (self.resultat_debit and self.resultat_debit["ecarts"]):
            raise ValueError("rien a corriger : lancer d'abord la recherche")
        cible = self.cible_conn16()
        self.tache = action
        threading.Thread(target=self._tache_debit, args=(action, cible), daemon=True).start()

    def _tache_debit(self, action, cible):
        try:
            if action == "chercher":
                self.resultat_debit = debit_modbus.cherche(self, cible)
                self.evenement("debit", {"action": action, "resultat": self.resultat_debit, "cible": cible})
            else:
                faits = debit_modbus.corrige(self, self.resultat_debit, cible)
                self.resultat_debit = None
                self.evenement("debit", {"action": action, "faits": faits, "cible": cible})
        except (OSError, serial.SerialException, ValueError) as erreur:
            self.evenement("debit", {"action": action, "erreur": str(erreur), "cible": cible})
        finally:
            self.tache = None
            self.diffuse_etat()

    # ------------------------------------------------------------------ trames
    def _fiche(self, nature, texte, ident=None, sens="!!"):
        return {"t": maintenant_texte(), "dt": None, "sens": sens, "hex": "", "crc": True, "nature": nature,
                "id": ident, "fc": None, "lat": None, "texte": texte}

    def traite(self, trame, source):
        """Classe, compte, surveille, journalise et diffuse une trame ; emulation : repond au bus."""
        maintenant = time.monotonic()
        with self.verrou:
            copie_envoi = False
            if source == "bus":
                if self.sonde_echo and trame == self.sonde_echo[0]:
                    self.echo_local, self.sonde_echo, self.dernier_envoi = True, None, None
                    self._diffuse([self._paquet("message", {"texte": "le convertisseur renvoie ses emissions : echo local filtre"})])
                    return
                if trame == self.dernier_envoi and maintenant - self.t_envoi < DELAI_ECHO:
                    if self.echo_local:
                        self.dernier_envoi = None       # echo du convertisseur
                        return
                    copie_envoi = True                  # accuse 0x05/0x06 d'un esclave : on le garde
                if self.capture and self.capture[0](trame):
                    self.capture[2]["trame"] = bytes(trame)
                    self.capture[1].set()
            requete = self.attendue[0] if self.attendue else None
            nat = dm.nature(trame, requete)
            dec = dm.decode(trame, requete, self.carte, self.types)
            fiche = {"t": maintenant_texte(), "dt": None if self.t_prec is None else round((maintenant - self.t_prec) * 1000),
                     "sens": source, "hex": rs.hexa(trame), "crc": nat != "ko", "nature": nat,
                     "id": trame[0] if trame else None, "fc": trame[1] if len(trame) > 1 else None,
                     "texte": dec["metier"] or dec["norme"], "norme": dec["norme"], "metier": dec["metier"],
                     "champs": dec["champs"], "lat": None}
            self.t_prec = maintenant
            self.nb += 1
            if nat == "ko":
                self.nb_ko += 1
            else:
                s = self._stat(trame[0])
                if nat == "requete":
                    self._sans_reponse()
                    s["requetes"] += 1
                    self.attendue = (bytes(trame), maintenant)
                elif nat in ("reponse", "exception"):
                    s["reponses" if nat == "reponse" else "exceptions"] += 1
                    if self.attendue and self.attendue[0][0] in (trame[0], 0xFF):
                        s["lat"] = fiche["lat"] = round((maintenant - self.attendue[1]) * 1000)
                        s["lat_max"] = max(s["lat_max"], s["lat"])
                        self.attendue = None
            paquets = [self._paquet("trame", fiche)]
            self._ecrit_journal(f"{source:<4} {fiche['hex']:<40} {'CRC OK' if fiche['crc'] else 'CRC KO'} "
                                f"{fiche['norme']} | {fiche['metier']}")
            self._diffuse(paquets, memorise=paquets[0])
            for alerte in self.surveillance.observe(trame, nat, source, maintenant):
                self.nb_alertes += alerte["niveau"] == "alerte"
                f = self._fiche("alerte" if alerte["niveau"] == "alerte" else "info", alerte["texte"],
                                trame[0] if trame else None)
                self._ecrit_journal(f"!!   {alerte['texte']}")
                p = self._paquet("trame", f)
                self._diffuse([p], memorise=p)
            # 'etat' aussi : la barre d'etat de la page compte trames, CRC KO et alertes en direct
            self._diffuse([self._paquet("stats", list(self.stats.values())), self._paquet("etat", self.etat())])
            reponse = (self.emulation.reponse(trame)
                       if source == "bus" and nat == "requete" and not copie_envoi and self.emulation.actifs else None)
        if reponse:
            try:
                self.envoie(reponse, "emul")
                self.diffuse_emulation()
            except (OSError, serial.SerialException) as erreur:
                self.message(f"emulation : reponse non envoyee ({erreur})")

    def _stat(self, ident):
        return self.stats.setdefault(ident, {"id": ident, "requetes": 0, "reponses": 0, "sans_reponse": 0, "exceptions": 0,
                                             "lat": None, "lat_max": 0, "push": 0, "push_ecartes": 0})

    def traite_udp(self, texte, ip):
        """Un datagramme du groupe multicast (fil d'ecoute UDP) : push decode et juge, ou autre message."""
        with self.verrou:
            f, alertes, ident, accepte = ecoute_udp.fiche(texte, ip, self.carte, self.types, self.derniers_seq,
                                                          maintenant_texte())
            if ident is not None:
                self.nb_push += 1
                s = self._stat(ident)
                s["push"] += 1
                s["push_ecartes"] += not accepte
            paquets = [self._paquet("trame", f)]
            self._ecrit_journal(f"udp  {f['hex']:<40} {f['texte']}")
            for alerte in alertes:
                self.nb_alertes += alerte["niveau"] == "alerte"
                paquets.append(self._paquet("trame", self._fiche("alerte" if alerte["niveau"] == "alerte" else "info",
                                                                 alerte["texte"], ident)))
            for p in paquets:
                self._diffuse([p], memorise=p)
            self._diffuse([self._paquet("stats", list(self.stats.values())), self._paquet("etat", self.etat())])

    def _ecrit_journal(self, ligne):
        if self.journal:
            self.journal.write(f"{time.strftime('%Y-%m-%d')} {maintenant_texte()} {ligne}\n")
            self.journal.flush()

    def _sans_reponse(self, maintenant=None):
        """SOUS self.verrou : la requete en attente n'aura pas de reponse (timeout ou requete suivante)."""
        if not self.attendue:
            return
        trame, instant = self.attendue
        self.attendue = None
        s = self.stats.get(trame[0])
        if s:
            s["sans_reponse"] += 1
        attente = round(((maintenant or time.monotonic()) - instant) * 1000)
        fiche = self._fiche("timeout", f"id {trame[0]} : PAS DE REPONSE ({attente} ms) a {rs.hexa(trame)}", trame[0], "--")
        paquet = self._paquet("trame", fiche)
        self._diffuse([paquet, self._paquet("stats", list(self.stats.values()))], memorise=paquet)

    def verifie_attente(self):
        maintenant = time.monotonic()
        with self.verrou:
            if self.attendue and maintenant - self.attendue[1] > self.args.delai:
                self._sans_reponse(maintenant)
            if self.sonde_echo and maintenant - self.sonde_echo[1] > SONDE_ECHO:
                self.echo_local, self.sonde_echo = False, None
                self._diffuse([self._paquet("etat", self.etat())])

    def boucle_lecture(self):
        tampon, dernier = bytearray(), 0.0
        while True:
            port = self.port
            if port is None:
                tampon.clear()
                time.sleep(0.1)
                continue
            try:
                n = port.in_waiting
                if n:
                    tampon += port.read(n)
                    dernier = time.monotonic()
                    continue
            except Exception as erreur:         # port debranche, ou ferme par la page entre-temps
                if self.port is port:
                    self.ferme(f"port {self.nom_port} perdu : {erreur}")
                continue
            if tampon and time.monotonic() - dernier >= self.args.silence:
                for trame in rs.decoupe(bytes(tampon)):
                    try:
                        self.traite(trame, "bus")
                    except Exception as erreur:     # une trame mal formee ne doit jamais arreter l'ecoute
                        self.message(f"trame {rs.hexa(trame)} ignoree : {erreur!r}")
                tampon.clear()
            self.verifie_attente()
            time.sleep(0.001)

    def raz(self):
        with self.verrou:
            self.stats, self.nb, self.nb_ko, self.nb_alertes, self.attendue = {}, 0, 0, 0, None
            self.derniers_seq, self.nb_push = {}, 0
            self.surveillance = Surveillance(self.carte, self.args.delai)
            self.historique.clear()
            self._diffuse([self._paquet("raz", {}), self._paquet("etat", self.etat()), self._paquet("stats", [])])


def main():
    for flux in (sys.stdout, sys.stderr):       # console redirigee (tache VS Code) : cp1252 sous Windows
        try:
            flux.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    options = argparse.ArgumentParser(description="Sniffeur ModBus RTU (RS485) avec page web locale.")
    options.add_argument("--port", default="auto", help="auto | COM12 | loop:// | aucun (choisi sur la page)")
    options.add_argument("--debit", type=int, default=19200, help="debit du bus (defaut 19200)")
    options.add_argument("--http", type=int, default=7300, help="port de la page http://127.0.0.1:<http>")
    options.add_argument("--silence", type=float, default=0.02, help="silence (s) qui clot une trame")
    options.add_argument("--delai", type=float, default=1.0, help="au-dela (s), une requete est sans reponse")
    options.add_argument("--echo", choices=("auto", "oui", "non"), default="auto",
                         help="le convertisseur renvoie-t-il ses emissions ? (defaut : appris au 1er envoi)")
    options.add_argument("--journal", help="copie des trames dans ce fichier")
    options.add_argument("--historique", type=int, default=5000, help="trames rejouees a l'ouverture de la page")
    options.add_argument("--udp", choices=("oui", "non"), default="oui", help="ecoute du push UDP des esclaves")
    options.add_argument("--udp-groupe", dest="udp_groupe", default=ecoute_udp.GROUPE)
    options.add_argument("--udp-port", dest="udp_port", type=int, default=ecoute_udp.PORT)
    options.add_argument("--udp-interface", dest="udp_interface", default="0.0.0.0",
                         help="IP locale de la carte reseau des modules (defaut : celle du systeme)")
    options.add_argument("--persist", default=dm.PERSIST_MAITRE,
                         help="_persist.json du maitre : adresses des esclaves et appareils (decodage metier)")
    args = options.parse_args()
    if not 0 < args.http < 65536 or args.historique < 0 or args.silence <= 0 or args.delai <= 0:
        sys.exit("parametre hors bornes")

    sniffeur = Sniffeur(args)
    try:
        http = ThreadingHTTPServer(("127.0.0.1", args.http), fabrique_gestionnaire(sniffeur))
    except OSError as erreur:
        sys.exit(f"port HTTP {args.http} indisponible ({erreur}) : un sniffeur tourne-t-il deja ? (--http <autre>)")
    http.daemon_threads = True
    print(f"sniffeur ModBus -> http://127.0.0.1:{args.http}/")

    nom = port_auto() if args.port == "auto" else (None if args.port == "aucun" else args.port)
    if nom:
        try:
            sniffeur.ouvre(nom, args.debit)
        except OSError as erreur:
            print(f"{erreur} -> demarrage port ferme, a ouvrir depuis la page")
    else:
        print("aucun port choisi (zero ou plusieurs CH343) -> a ouvrir depuis la page")
    threading.Thread(target=sniffeur.boucle_lecture, daemon=True).start()
    if args.udp == "oui":
        udp = ecoute_udp.EcouteUDP(sniffeur.traite_udp, args.udp_groupe, args.udp_port, args.udp_interface)
        sniffeur.udp_texte = f"{args.udp_groupe}:{args.udp_port}" if udp.demarre() else udp.erreur
        print(f"push UDP : {sniffeur.udp_texte}")
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        sniffeur.ferme()


if __name__ == "__main__":
    main()
