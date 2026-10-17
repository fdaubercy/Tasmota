"""Testeur UDP maitre / esclave : deux ports serie, les logs Tasmota des deux cartes, des essais UDP.

Ouvre le maitre ModBus (ESP32-P4) et un esclave (ESP32-S3 cuve ou rideau) par leurs ports serie USB,
lit leurs logs, et sur sa page web (http://127.0.0.1:7400 ; depuis un autre appareil du reseau, le lien
avec jeton affiche par la console) permet d'envoyer des messages UDP unicast / multicast
dans les deux sens et de lire le verdict (RECU / EMIS NON RECU / NON EMIS) d'apres les logs des deux
cartes. L'esclave est soit en « Range Extender » (client du point d'acces du maitre, 192.168.4.x),
soit en « Wi-Fi classique » (sur le reseau maison) : la page lit et change ce mode.
Onglet « Aide » de la page : raccordement, commandes envoyees, lecture des verdicts.

Usage (Python de PlatformIO, qui fournit pyserial) :
    %USERPROFILE%\\.platformio\\penv\\Scripts\\python.exe outils_docs/scripts_python/outils_pc/testeur_udp.py
    options : --port-maitre COM11  --port-esclave COM12 (defaut vide = ferme)  --vitesse 115200
              --http 7400  --journal fichier.log  --persist-maitre <_persist.json du maitre>
              --local (127.0.0.1 seulement)  --sans-navigateur (page non ouverte au lancement)
Les ports se choisissent aussi depuis la page. « pont:7000 » (option ou liste de la page) : passe par
le pont serie (pont_serie.py --tcp 7000), qui garde le port COM ; sinon FERMER le pont / le moniteur avant.
Les ports sont ouverts SANS basculer DTR/RTS (pas de reset). A l'arret (Ctrl+C), les niveaux de
log modifies sur les cartes sont restaures. Le mot de passe Wi-Fi n'apparait ni dans la page ni
dans le journal (remplace par ***).

Modules voisins : testeur_udp_carte (serie), testeur_udp_essais (commandes, preuves, verdicts),
testeur_udp_http (routes), testeur_udp_web (page), testeur_udp_aide (onglet Aide).
"""

import argparse
import collections
import json
import os
import queue
import re
import sys
import threading
import time
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acces_web                    # noqa: E402
import testeur_udp_carte as tc      # noqa: E402
import testeur_udp_essais as te     # noqa: E402

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PERSIST_MAITRE = os.path.join(RACINE, "data", "garage", "tasmota32p4-serveur-modbus", "_persist.json")
IP_AP_MAITRE = "192.168.4.1"
NIVEAUX = ("erreur", "info", "debug", "detail")
MODES = ("RangeExtender", "WifiClassique")
ATTENTE_REDEMARRAGE = 120           # s : au-dela, on cesse d'afficher « redemarrage... »
RE_STATUS5 = re.compile(r"STATUS5 = (\{.*\})")
RE_LOG = re.compile(r'(\{\s*"ReglageLog"\s*:\s*\{.*\}\s*\})')
RE_MODE = re.compile(r'"modeConnexion"\s*:\s*"(\w+)"')
RE_REDEMARRAGE = re.compile(r'"redemarrage"\s*:\s*true')
RE_ERREUR_MODE = re.compile(r'"ReglageGlobal"\s*:\s*\{[^}]*"erreur"\s*:\s*"([^"]*)"')
RE_MODE_ABSENT = re.compile(r"sous-commande 'ModeConnexion' inconnue")
# Tasmota coupe le log serie 600 s apres le demarrage (SERIALLOG_TIMER, support_tasmota.ino:1186) sauf si une
# commande SerialLog arrive avant ; logFonctions.appliqueProfil n'en envoie pas quand le niveau est deja le bon
# (constate le 2026-10-17 : cuve muette des 03:33:21). On reapplique le niveau REGLE (inchange) : le compteur
# s'arrete et le log revient. Passe aussi quand le log est deja coupe (la commande s'execute, sans echo).
COMMANDE_REVEIL_SERIE = ('Br var r = tasmota.cmd("SerialLog", true).find("SerialLog") '
                         'if isinstance(r, map) for k: r.keys() tasmota.cmd("SerialLog " + k, true) end end')
RESEAU_AP_MAITRE = IP_AP_MAITRE.rsplit(".", 1)[0] + "."
RE_UDP = re.compile(r"ENVOI_MSG_UDP|LIRE_UDP|REPOND_UDP|POUSSE_ETAT|ENVOI_MSG_MODBUS")


def lit_wifi_persist(chemin):
    """(ssid, mot de passe) du reseau1 du maitre. ValueError si le persist est illisible ou incomplet."""
    try:
        with open(chemin, encoding="utf-8") as f:
            reseau = json.load(f)["serveur"]["wifi"]["reseau1"]
        return str(reseau["nomReseauWifi"]), str(reseau["mdpWifi"])
    except (OSError, ValueError, KeyError, TypeError) as erreur:
        raise ValueError(f"persist du maitre inutilisable ({chemin}) : {type(erreur).__name__}") from None


def premier_mot(valeur):
    """'info (actif : debug)' -> 'info'."""
    mots = str(valeur).split()
    return mots[0] if mots else ""


class Testeur:
    def __init__(self, args, fabrique=None):
        self.args = args
        self.masque = tc.Masque()
        self.ordre = ("maitre", "esclave")
        self.cartes = {r: tc.Carte(r, args.vitesse, self.masque, self.sur_ligne, self.sur_ouverture, self.sur_perte,
                                   self.sur_note, fabrique) for r in self.ordre}
        self.infos = {r: {"ip": "", "hostname": "", "mac": ""} for r in self.ordre}
        self.acquis = {r: {"ip": False, "logs": False, "mode": False} for r in self.ordre}
        self.logs = {r: {"originaux": None, "poses": {}} for r in self.ordre}
        self.mode_esclave = None
        self.mode_absent = False                   # firmware de l'esclave sans ReglageGlobal ModeConnexion
        self.redemarrage_depuis = None
        self.arret = False
        self.verrou = threading.Lock()
        self.verrou_essai = threading.Lock()
        self.essai = None                          # essai en cours (observateur)
        self.essais = []                           # historique des verdicts
        self.numero = 0
        self.clients = []
        self.historique = collections.deque(maxlen=4000)
        self.notes = collections.deque(maxlen=200)    # (role, texte) des messages de l'outil, deja masques
        self.journal = open(args.journal, "a", encoding="utf-8") if args.journal else None
        try:
            self.masque.ajoute(lit_wifi_persist(args.persist_maitre)[1])
        except ValueError as erreur:
            self.note(None, f"{erreur} : la bascule vers Wi-Fi classique sera refusee")

    # ------------------------------------------------------------------ diffusion vers les pages
    def diffuse(self, evenement, garde=True):
        donnees = ("data: " + json.dumps(evenement, ensure_ascii=False) + "\n\n").encode("utf-8")
        with self.verrou:
            if garde:
                self.historique.append(donnees)
            for file in list(self.clients):
                try:
                    file.put_nowait(donnees)
                except queue.Full:
                    self.clients.remove(file)

    def inscrit_web(self):
        file = queue.Queue(maxsize=8000)
        with self.verrou:
            file.put_nowait(("data: " + json.dumps({"k": "etat", **self.etat()}) + "\n\n").encode("utf-8"))
            for donnees in self.historique:
                file.put_nowait(donnees)
            self.clients.append(file)
        return file

    def desinscrit_web(self, file):
        with self.verrou:
            if file in self.clients:
                self.clients.remove(file)

    def pousse_etat(self):
        self.diffuse({"k": "etat", **self.etat()}, garde=False)

    def note(self, role, texte):
        """Message de l'outil (hors flux des cartes), masque, dans la page et le journal."""
        texte = self.masque.applique(texte)
        self.notes.append((role, texte))
        self.ecrit_journal(f"[outil{'/' + role if role else ''}] {texte}")
        self.diffuse({"k": "note", "c": role, "t": time.time(), "x": texte})

    def sur_note(self, role, texte):
        self.note(role, texte)

    def notes_esclave(self):
        return [texte for role, texte in self.notes if role == "esclave"]

    def ecrit_journal(self, ligne):
        if self.journal:
            self.journal.write(time.strftime("%H:%M:%S ") + ligne + "\n")
            self.journal.flush()

    # ------------------------------------------------------------------ etat
    def etat(self):
        cartes = {}
        for r, c in self.cartes.items():
            cartes[r] = {"port": c.nom_port or c.souhait, "ouvert": c.ouvert, "attente": c.perdu, "vitesse": c.vitesse,
                         "message": c.message, **self.infos[r], "logs": self.logs[r]["poses"],
                         "originaux": self.logs[r]["originaux"]}
        redemarrage = (self.redemarrage_depuis is not None
                       and time.time() - self.redemarrage_depuis < ATTENTE_REDEMARRAGE)
        ip_maitre = self.infos["maitre"]["ip"]
        # Esclave sur le reseau du point d'acces du maitre : c'est le Range Extender, meme si le mode n'a pas pu
        # etre lu (firmware sans ModeConnexion)
        sur_ap = self.infos["esclave"]["ip"].startswith(RESEAU_AP_MAITRE)
        defaut = IP_AP_MAITRE if self.mode_esclave == "RangeExtender" or sur_ap else (ip_maitre or IP_AP_MAITRE)
        return {"cartes": cartes, "mode_esclave": self.mode_esclave, "mode_absent": self.mode_absent,
                "redemarrage": redemarrage,
                "ip_ap_maitre": IP_AP_MAITRE, "ip_vers_maitre_defaut": defaut, "essai_en_cours": self.essai is not None}

    # ------------------------------------------------------------------ rappels des cartes
    def sur_ligne(self, role, texte, t):
        self.ecrit_journal(f"[{role}] {texte}")
        self.diffuse({"k": "ligne", "c": role, "t": t, "x": texte, "udp": bool(RE_UDP.search(texte))})
        essai = self.essai
        if essai is not None:
            essai.observe(role, texte, t)
        self.analyse(role, texte)

    def sur_ouverture(self, role, reouverte):
        self.acquis[role] = {"ip": False, "logs": False, "mode": False}
        self.infos[role].update(ip="", hostname="", mac="")
        if role == "esclave":
            self.mode_esclave, self.mode_absent = None, False
        carte = self.cartes[role]
        self.note(role, ("port rouvert automatiquement : " if reouverte else "") + carte.message)
        self.pousse_etat()
        threading.Thread(target=self.initialise, args=(role, carte.generation), daemon=True).start()

    def sur_perte(self, role):
        self.note(role, self.cartes[role].message)
        self.pousse_etat()

    # ------------------------------------------------------------------ initialisation d'une carte
    def initialise(self, role, generation):
        """Status 5, etat des logs (ReglageLog) et, pour l'esclave, mode de connexion : renvoyes toutes les
        3 s tant qu'une reponse manque (la carte peut etre en train de demarrer)."""
        carte = self.cartes[role]
        carte.ecrit(COMMANDE_REVEIL_SERIE)
        for _ in range(25):
            if carte.generation != generation or not carte.ouvert or self.arret:
                return
            manque = [k for k, v in self.acquis[role].items() if not v and (k != "mode" or role == "esclave")]
            if not manque:
                return
            if "ip" in manque:
                carte.ecrit("Status 5")
            if "logs" in manque:
                carte.ecrit("ReglageLog")
            if "mode" in manque:
                carte.ecrit("ReglageGlobal ModeConnexion")
            time.sleep(3)

    def relire(self, role):
        if role not in self.cartes:
            raise ValueError(f"carte inconnue : {role!r}")
        carte = self.cartes[role]
        if not carte.ouvert:
            raise OSError(f"port {role} ferme")
        self.acquis[role] = {"ip": False, "logs": False, "mode": False}
        threading.Thread(target=self.initialise, args=(role, carte.generation), daemon=True).start()

    # ------------------------------------------------------------------ analyse des reponses
    def analyse(self, role, texte):
        m = RE_STATUS5.search(texte)
        if m:
            try:
                net = json.loads(m.group(1))["StatusNET"]
                ip = str(net.get("IPAddress", ""))
                self.infos[role].update(ip="" if ip == "0.0.0.0" else ip, hostname=str(net.get("Hostname", "")),
                                        mac=str(net.get("Mac", "")))
                self.acquis[role]["ip"] = ip not in ("", "0.0.0.0")
                self.pousse_etat()
            except (ValueError, KeyError, TypeError, AttributeError):
                pass
        m = RE_LOG.search(texte)
        if m:
            try:
                self.traite_logs(role, json.loads(m.group(1))["ReglageLog"])
            except (ValueError, KeyError, TypeError, AttributeError):
                pass
        if role == "esclave" and RE_MODE_ABSENT.search(texte):
            # Firmware anterieur a ModeConnexion (2026-10-16) : ne plus la redemander toutes les 3 s
            self.acquis[role]["mode"] = True
            if not self.mode_absent:
                self.mode_absent = True
                self.note(role, "ReglageGlobal ModeConnexion absent du firmware de l'esclave : bascule impossible "
                                "avant de le reflasher (mode deduit de son IP)")
            self.pousse_etat()
        m = RE_MODE.search(texte)
        if m and role == "esclave" and m.group(1) in MODES:
            self.mode_esclave = m.group(1)
            erreur = RE_ERREUR_MODE.search(texte)
            if RE_REDEMARRAGE.search(texte):
                # Reponse a la bascule (globalFonctions.reglageModeConnexion) : la carte n'a pas encore
                # redemarre ; le mode sera RELU apres sa reconnexion (sur_ouverture / filet de 20 s).
                self.acquis[role]["mode"] = False
            else:
                self.acquis[role]["mode"] = True
                self.redemarrage_depuis = None
            if erreur:
                self.note(role, "bascule refusee par la carte : " + erreur.group(1))
            self.pousse_etat()

    def traite_logs(self, role, d):
        """Etat complet de ReglageLog : memorise l'origine (une seule fois), pose udp/modbus en detail et la
        sortie serie en debug au moins. JAMAIS mqtt / web / syslog (MqttLog debug fait planter un esclave
        derriere le NAPT)."""
        if not isinstance(d.get("sorties"), dict) or not isinstance(d.get("modules"), dict):
            return                                     # reponse a une commande de reglage, pas l'etat complet
        sorties = {k: premier_mot(v) for k, v in d["sorties"].items()}
        modules = {k: premier_mot(v) for k, v in d["modules"].items()}
        actuel = {"udp": modules.get("udp"), "modbus": modules.get("modbus"), "serie": sorties.get("serie")}
        etat = self.logs[role]
        if etat["originaux"] is None:
            etat["originaux"] = dict(actuel)
        cibles = {"udp": "detail", "modbus": "detail"}
        rang = NIVEAUX.index(actuel["serie"]) if actuel["serie"] in NIVEAUX else -1
        if rang < NIVEAUX.index("debug"):
            cibles["serie"] = "debug"
        carte = self.cartes[role]
        for cle, cible in cibles.items():
            if actuel.get(cle) is not None and actuel[cle] != cible:
                if carte.ecrit(f"ReglageLog {cle} {cible}"):
                    etat["poses"][cle] = cible
        self.acquis[role]["logs"] = True
        self.pousse_etat()

    def restaure_logs(self, role=None):
        """Remet les niveaux d'origine sur les cartes ouvertes. -> nombre de commandes envoyees."""
        n = 0
        for r in ([role] if role else self.ordre):
            etat, carte = self.logs[r], self.cartes[r]
            for cle in list(etat["poses"]):
                origine = (etat["originaux"] or {}).get(cle)
                if origine and carte.ecrit(f"ReglageLog {cle} {origine}"):
                    n += 1
                    del etat["poses"][cle]
        self.pousse_etat()
        return n

    # ------------------------------------------------------------------ mode de connexion de l'esclave
    def bascule_mode(self, mode):
        carte = self.cartes["esclave"]
        if not carte.ouvert:
            raise OSError("port de l'esclave ferme : l'ouvrir d'abord")
        if self.mode_absent:
            raise ValueError("le firmware de l'esclave ne connait pas ReglageGlobal ModeConnexion : le reflasher d'abord")
        if mode == "WifiClassique":
            ssid, mdp = lit_wifi_persist(self.args.persist_maitre)
            # La commande Berry prend le DERNIER mot pour le mot de passe : le SSID peut avoir des espaces
            if not ssid.strip() or not mdp or any(c.isspace() for c in mdp):
                raise ValueError("SSID vide, ou mot de passe vide ou contenant un espace : non pris en charge par la commande")
            self.masque.ajoute(mdp)
            commande = f"ReglageGlobal ModeConnexion WifiClassique {ssid} {mdp}"
        elif mode == "RangeExtender":
            commande = "ReglageGlobal ModeConnexion RangeExtender"
        else:
            raise ValueError(f"mode inconnu : {mode!r}")
        if not carte.ecrit(commande):
            raise OSError("ecriture impossible sur le port de l'esclave")
        self.redemarrage_depuis = time.time()
        self.acquis["esclave"]["mode"] = False
        self.pousse_etat()
        # La carte redemarre seule : le port se rouvre tout seul (sur_ouverture relit tout). Filet si le
        # port USB n'a pas ete perdu (pont UART) : relecture apres 20 s.
        threading.Timer(20, self._relance_si_redemarrage).start()

    def _relance_si_redemarrage(self):
        if self.redemarrage_depuis is not None and self.cartes["esclave"].ouvert and not self.acquis["esclave"]["mode"]:
            self.relire("esclave")

    # ------------------------------------------------------------------ essais
    def lance_essai(self, demande):
        """Execute un essai (bloquant, duree = fenetre d'attente). -> dict du verdict. ValueError / OSError."""
        delai = float(demande.get("delai", 3))
        if not 0.5 <= delai <= 30:
            raise ValueError("delai d'attente : 0,5 a 30 s")
        if not self.verrou_essai.acquire(blocking=False):
            raise OSError("un essai est deja en cours")
        try:
            self.numero += 1
            essai = te.construit_essai(self.numero, demande, self.mode_esclave)
            for r in (essai.emetteur, essai.recepteur):
                if not self.cartes[r].ouvert:
                    raise OSError(f"le port de la carte {r} est ferme : l'ouvrir d'abord")
            self.essai = essai
            self.pousse_etat()
            essai.t0 = time.time()
            self.note(essai.emetteur, f"essai {essai.numero} ({essai.type}, {essai.mode}) : {essai.emetteur} > {essai.recepteur}")
            if not self.cartes[essai.emetteur].ecrit(essai.commande):
                raise OSError("ecriture impossible sur le port de l'emetteur")
            fin = essai.t0 + delai
            while time.time() < fin and not essai.termine():
                time.sleep(0.05)
            time.sleep(0.15)                                 # la derniere ligne de log
            resultat = essai.conclut()
        finally:
            self.essai = None
            self.verrou_essai.release()
            self.pousse_etat()
        ligne = {"n": essai.numero, "heure": time.strftime("%H:%M:%S"), "sens": f"{essai.emetteur} > {essai.recepteur}",
                 "mode_connexion": self.mode_esclave or "inconnu", "type": essai.type, "mode": essai.mode,
                 "message": essai.message, **resultat}
        self.essais.append(ligne)
        self.note(None, f"essai {essai.numero} : {resultat['verdict']} {' ; '.join(resultat['details'])}")
        self.diffuse({"k": "essai", **ligne}, garde=False)
        return ligne

    def envoie_commande(self, role, commande):
        if role not in self.cartes:
            raise ValueError(f"carte inconnue : {role!r}")
        if not self.cartes[role].ecrit(commande):
            raise OSError(f"port {role} ferme")

    # ------------------------------------------------------------------ arret
    def arrete(self):
        """Restaure les logs puis libere les ports."""
        self.arret = True
        n = self.restaure_logs()
        if n:
            time.sleep(0.5)                          # laisse la carte traiter les commandes avant la fermeture
        for c in self.cartes.values():
            c.arrete()


def lit_options(argv=None):
    options = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    options.add_argument("--port-maitre", default="", help="port serie du maitre ModBus (ESP32-P4) ; vide = ferme")
    options.add_argument("--port-esclave", default="", help="port serie de l'esclave (ESP32-S3) ; vide = ferme")
    options.add_argument("--vitesse", type=int, default=115200)
    options.add_argument("--http", type=int, default=7400, help="port HTTP de la page")
    options.add_argument("--journal", help="journal des lignes des deux cartes (mot de passe masque)")
    options.add_argument("--persist-maitre", default=PERSIST_MAITRE,
                         help="_persist.json du maitre : reseau Wi-Fi utilise pour la bascule en Wi-Fi classique")
    acces_web.ajoute_options(options)
    return options.parse_args(argv)


def main():
    import testeur_udp_http
    args = lit_options()
    testeur = Testeur(args)
    acces = acces_web.Acces(args.http, args.local, "Testeur UDP")
    try:
        serveur = ThreadingHTTPServer((acces.hote, args.http), testeur_udp_http.fabrique_gestionnaire(testeur, acces))
    except OSError as erreur:
        sys.exit(f"Port HTTP {args.http} deja utilise ({erreur}) : un autre testeur tourne ? (sinon --http 7401)")
    serveur.daemon_threads = True
    for role, nom in (("maitre", args.port_maitre), ("esclave", args.port_esclave)):
        if nom:
            ok, message = testeur.cartes[role].ouvre(nom, args.vitesse)
            print(f"{role} : {message}" + ("" if ok else "  <-- AVERTISSEMENT"))
    acces.annonce(not args.sans_navigateur)
    print("   Ctrl+C pour arreter ; les logs modifies seront restaures", flush=True)
    try:
        serveur.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        print("\narret : restauration des niveaux de log, ports liberes")
    finally:
        serveur.server_close()
        testeur.arrete()


if __name__ == "__main__":
    main()
