"""Sniffeur MQTT : ecoute un broker, publie sur des topics choisis, filtre les messages.

Principe : un client MQTT (client_mqtt.py, Python pur) s'abonne a '#' (reglable) et sert le flux
sur http://127.0.0.1:<http> (page : sniffeur_mqtt_web.py + sniffeur_mqtt_panneaux.py) :
    - plusieurs brokers parametrables, un seul actif (selection a chaud depuis la page) ;
    - messages en direct, filtre d'affichage (texte / regex), favoris de filtre, differences
      avec le message precedent du meme topic, export ;
    - abonnements (filtrage COTE BROKER) gerables un par un, memorises par broker ;
    - publication (texte ou hexa, retenu ou non ; vide + retenu = effacer un retenu) ;
    - panneaux : audit discovery, connexions (LWT), console de logs par carte (stat/<topic>/LOGGING),
      commande Tasmota avec sa reponse, arborescence des topics.

Brokers et favoris : sniffeur_mqtt_config.py (%APPDATA%\\sniffeur_mqtt\\config.json, HORS depot).
Broker par defaut : lu dans tasmota/user_config_override.h (1re definition de MQTT_HOST, MQTT_PORT,
MQTT_USER, MQTT_PASS), surchargeable en ligne de commande. Les mots de passe ne sont jamais affiches
ni envoyes a la page. Client ID unique (sniffeur-<poste>-<pid>) : ne deconnecte aucun module.

Usage (Python de PlatformIO ou tout Python 3.8+, aucune dependance) :
    python outils_docs/scripts_python/sniffeur_mqtt.py
    options : --hote 192.168.0.5 --port 1883 --utilisateur u --mot-de-passe m
              --abonnement "#" (repetable)  --http 7100  --journal fichier.log  --historique 5000
Depuis VS Code : pioarduino > Project Tasks > <env> > Custom > « Sniffeur MQTT (HTTP 127.0.0.1) »
(cible_sniffeur_mqtt.py). Arret : Ctrl+C dans le terminal de la tache (ou la corbeille).
"""

import argparse
import collections
import json
import os
import queue
import re
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import client_mqtt              # noqa: E402
import sniffeur_mqtt_config     # noqa: E402
import sniffeur_mqtt_panneaux   # noqa: E402
import sniffeur_mqtt_web        # noqa: E402

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG = os.path.join(RACINE, "tasmota", "user_config_override.h")
MAX_PAYLOAD_AFFICHE = 64 * 1024     # au-dela, le payload est tronque dans la page (pas dans le journal)
RE_DISCOVERY = re.compile(r"^tasmota/discovery/([0-9A-Fa-f]{12})/([^/]+)$")
RE_ROLE = re.compile(r"^(maitre|esclave[0-9]+|module[0-9]+)$")      # roles publies par discoveryFonctions.be
RE_LOGGING = re.compile(r"^[^/]+/(.+)/LOGGING$")                     # stat/<topic>/LOGGING (MqttLog)


def lit_config_broker(chemin=CONFIG):
    """1re definition de MQTT_HOST/PORT/USER/PASS dans user_config_override.h (bloc general)."""
    valeurs = {}
    try:
        texte = open(chemin, encoding="utf-8", errors="replace").read()
    except OSError:
        return valeurs
    for cle in ("MQTT_HOST", "MQTT_PORT", "MQTT_USER", "MQTT_PASS"):
        m = re.search(r'^\s*#define\s+' + cle + r'\s+("([^"]*)"|(\d+))', texte, re.M)
        if m:
            valeurs[cle] = m.group(2) if m.group(2) is not None else m.group(3)
    return valeurs


def decode_payload(octets):
    """(texte affichable, est_hexa) : UTF-8 lisible si possible, sinon hexadecimal."""
    try:
        texte = octets.decode("utf-8")
        if all(c.isprintable() or c in "\r\n\t" for c in texte):
            return texte, False
    except UnicodeDecodeError:
        pass
    return octets.hex(" ").upper(), True


def valide_filtre(filtre):
    """Filtre d'abonnement MQTT valide : '#' en dernier niveau seulement, '+' seul dans son niveau."""
    if not filtre or len(filtre) > 512:
        return False
    niveaux = filtre.split("/")
    for i, niveau in enumerate(niveaux):
        if "#" in niveau and (niveau != "#" or i != len(niveaux) - 1):
            return False
        if "+" in niveau and niveau != "+":
            return False
    return True


class Sniffeur:
    def __init__(self, args, configuration):
        self.args = args
        self.config = configuration
        self.client_id = f"sniffeur-{socket.gethostname()}-{os.getpid()}"
        self.broker = configuration.actif()
        self.client = self._nouveau_client(self.broker)
        self.abonnements = list(args.abonnement or configuration.abonnements(self.broker["id"]))
        self.connecte, self.erreur, self.changement = False, "", False
        self.journal = open(args.journal, "a", encoding="utf-8") if args.journal else None
        self.clients_web = []
        self.verrou = threading.Lock()
        self._remet_a_zero()

    def _nouveau_client(self, b):
        return client_mqtt.ClientMQTT(b.get("hote", ""), b.get("port", 1883), self.client_id, b.get("utilisateur", ""),
                                      b.get("motDePasse", ""), tls=b.get("tls", False),
                                      verifier_certificat=b.get("verifierCertificat", True))

    def _remet_a_zero(self):
        """Registres propres au broker courant (vides au demarrage et a chaque changement de broker)."""
        self.nb_recus = 0
        self.debut = time.strftime("%d/%m %H:%M:%S")
        self.historique = collections.deque(maxlen=self.args.historique)
        # Independants de l'historique (qui ne garde que les N derniers messages) :
        self.discovery = {}                                   # {(MAC, cle): fiche resumee} -> audit discovery
        self.lwt = collections.deque(maxlen=5000)             # evenements tele/<topic>/LWT -> connexions
        self.logs = {}                                        # {topic module: deque des lignes stat/<topic>/LOGGING}

    # ------------------------------------------------------------------ etat et diffusion
    def etat(self):
        b = self.broker
        return {"connecte": self.connecte, "broker": {"id": b["id"], "nom": b.get("nom", ""), "hote": b.get("hote", ""),
                                                      "port": b.get("port"), "tls": b.get("tls", False)},
                "hote": b.get("hote", ""), "port": b.get("port"), "utilisateur": b.get("utilisateur", ""),
                "clientId": self.client_id, "abonnements": self.abonnements, "recus": self.nb_recus,
                "erreur": self.erreur, "http": self.args.http, "depuis": self.debut}

    @staticmethod
    def _paquet(evenement, donnees):
        return f"event: {evenement}\ndata: {json.dumps(donnees)}\n\n".encode("utf-8")

    def diffuse(self, evenement, donnees, memorise=False, registre=None):
        """Envoie l'evenement aux pages ouvertes. 'registre' (fonction) met a jour un registre SOUS le
        meme verrou : une page qui s'inscrit voit soit l'ancien etat + l'evenement, soit le nouvel etat."""
        paquet = self._paquet(evenement, donnees)
        with self.verrou:
            if registre is not None:
                registre()
            if memorise:
                self.historique.append(paquet)
            for file in self.clients_web:
                file.put(paquet)

    def note(self, texte):
        print(texte)
        self.diffuse("note", {"t": time.strftime("%H:%M:%S"), "texte": texte}, memorise=True)

    def inscrit_web(self):
        file = queue.Queue()
        with self.verrou:
            file.put(self._paquet("etat", self.etat()))
            for entree in self.discovery.values():
                file.put(self._paquet("disco", entree))
            for evenement in self.lwt:
                file.put(self._paquet("lwt", evenement))
            for paquet in self.historique:
                file.put(paquet)
            self.clients_web.append(file)
        return file

    def desinscrit_web(self, file):
        with self.verrou:
            if file in self.clients_web:
                self.clients_web.remove(file)

    # ------------------------------------------------------------------ MQTT
    def boucle_mqtt(self):
        attente = 2
        while True:
            client = self.client
            self.changement = False          # demande prise en compte (ou attente interrompue par elle)
            try:
                if not client.hote:
                    raise client_mqtt.ErreurMQTT("aucun hote : choisir ou parametrer un broker")
                client.connecte()
                client.abonne(self.abonnements)
                self.connecte, self.erreur, attente = True, "", 2
                self.diffuse("etat", self.etat())
                self.note(f"connecte a {client.hote}:{client.port}{' (TLS)' if client.tls else ''} "
                          f"({self.client_id}), abonnements : {', '.join(self.abonnements) or 'aucun'}")
                while client is self.client:
                    message = client.recoit()
                    if message is not None and client is self.client:
                        self.recu(message)
                    client.entretient()
            except (OSError, client_mqtt.ErreurMQTT) as erreur:
                client.ferme()
                etait_connecte, self.connecte = self.connecte, False
                if self.changement:                   # changement de broker demande : pas d'attente
                    self.changement, attente = False, 2
                    continue
                self.erreur = str(erreur) or erreur.__class__.__name__
                self.diffuse("etat", self.etat())
                if etait_connecte or attente == 2:
                    self.note(f"liaison broker {client.hote or '?'} indisponible : {self.erreur} ; nouvel essai dans {attente} s")
                fin = time.time() + attente
                while time.time() < fin and not self.changement:
                    time.sleep(0.2)
                attente = min(attente * 2, 30)

    def change_broker(self, identifiant):
        broker = self.config.selectionne(identifiant)
        ancien = self.client
        with self.verrou:
            self.broker, self.changement = broker, True
            self.client = self._nouveau_client(broker)
            self.abonnements = self.config.abonnements(identifiant)
            self.connecte, self.erreur = False, ""
            self._remet_a_zero()
        ancien.ferme()                                # debloque la boucle MQTT (recv -> OSError)
        self.diffuse("reset", {})
        self.diffuse("etat", self.etat())
        self.note(f"broker selectionne : {broker.get('nom')} ({broker.get('hote')}:{broker.get('port')})")

    def recu(self, message):
        self.nb_recus += 1
        texte, est_hexa = decode_payload(message.payload)
        heure = time.strftime("%H:%M:%S", time.localtime(message.instant)) + f".{int(message.instant % 1 * 1000):03d}"
        if self.journal:
            self.journal.write(f"{heure} {'R ' if message.retain else ''}{message.topic} = {texte}\n")
            self.journal.flush()
        self.diffuse("msg", {"n": self.nb_recus, "t": heure, "topic": message.topic,
                             "payload": texte[:MAX_PAYLOAD_AFFICHE], "hex": est_hexa,
                             "tronque": len(texte) > MAX_PAYLOAD_AFFICHE, "retain": message.retain,
                             "qos": message.qos, "taille": len(message.payload)}, memorise=True)
        self.enregistre_discovery(message, texte, heure)
        if message.topic.endswith("/LWT"):
            evenement = {"topic": message.topic, "etat": texte, "t": heure, "ts": message.instant,
                         "retain": message.retain}
            self.diffuse("lwt", evenement, registre=lambda: self.lwt.append(evenement))
        m = RE_LOGGING.match(message.topic)
        if m and not est_hexa:
            with self.verrou:
                self.logs.setdefault(m.group(1), collections.deque(maxlen=3000)).append({"t": heure, "texte": texte})

    def enregistre_discovery(self, message, texte, heure):
        """tasmota/discovery/<MAC>/<maitre|esclaveN|moduleN|config> -> registre de l'audit discovery.
        Payload vide (effacement d'un retenu) : l'entree est retiree."""
        m = RE_DISCOVERY.match(message.topic)
        if not m:
            return
        mac, cle = m.group(1).upper(), m.group(2)
        if cle != "config" and not RE_ROLE.match(cle):
            return
        entree = {"mac": mac, "cle": cle, "topic": message.topic, "t": heure, "retain": message.retain,
                  "vide": not message.payload}
        if message.payload:
            try:
                fiche = json.loads(texte)
            except ValueError:
                fiche = None
            if not isinstance(fiche, dict):
                entree["invalide"] = True
            elif cle == "config":        # sous-ensemble utile : nom, topic, IP, hostname, format du topic complet
                entree.update({"dn": fiche.get("dn"), "tp": fiche.get("t"), "ip": fiche.get("ip"),
                               "hn": fiche.get("hn"), "ft": fiche.get("ft"), "tpx": fiche.get("tp")})
            else:
                entree.update({"id": fiche.get("id"), "nom": fiche.get("nom"), "tp": fiche.get("topic"),
                               "ip": fiche.get("IPAddress"), "macFiche": fiche.get("adresseMAC")})

        def maj():
            if entree["vide"]:
                self.discovery.pop((mac, cle), None)
            else:
                self.discovery[(mac, cle)] = entree
        self.diffuse("disco", entree, registre=maj)

    def change_abonnements(self, filtres):
        anciens, self.abonnements = self.abonnements, filtres
        self.config.memorise_abonnements(self.broker["id"], filtres)
        if self.connecte:
            self.client.desabonne([f for f in anciens if f not in filtres])
            self.client.abonne([f for f in filtres if f not in anciens])
        self.diffuse("etat", self.etat())
        self.note(f"abonnements : {', '.join(filtres) or 'aucun'}")

    def publie(self, topic, payload, retain):
        if not self.connecte:
            raise ConnectionError("broker non connecte")
        self.client.publie(topic, payload, retain)
        apercu = decode_payload(payload)[0] if payload else "(vide)"
        self.note(f"[publie{' retenu' if retain else ''}] {topic} = {apercu[:200]}")

    def lignes_logs(self, module):
        with self.verrou:
            if module is None:
                return {"modules": {m: len(d) for m, d in self.logs.items()}}
            return {"module": module, "lignes": list(self.logs.get(module, []))}


def fabrique_gestionnaire(sniffeur):
    class Gestionnaire(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def _envoie(self, statut, corps=b"", type_contenu="text/plain; charset=utf-8"):
            self.send_response(statut)
            self.send_header("Content-Type", type_contenu)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corps)

        def _json(self, donnees):
            self._envoie(200, json.dumps(donnees).encode("utf-8"), "application/json")

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == "/":
                self._envoie(200, sniffeur_mqtt_web.PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif url.path == "/panneaux.js":
                self._envoie(200, sniffeur_mqtt_panneaux.JS.encode("utf-8"), "text/javascript; charset=utf-8")
            elif url.path == "/etat":
                self._json(sniffeur.etat())
            elif url.path == "/brokers":
                self._json(sniffeur.config.liste_publique())
            elif url.path == "/favoris":
                self._json(sniffeur.config.favoris())
            elif url.path == "/logs":
                module = parse_qs(url.query).get("module", [None])[0]
                self._json(sniffeur.lignes_logs(module))
            elif url.path == "/flux":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                file = sniffeur.inscrit_web()
                try:
                    while True:
                        try:
                            self.wfile.write(file.get(timeout=15))
                        except queue.Empty:
                            self.wfile.write(b": veille\n\n")     # detecte un onglet ferme
                        self.wfile.flush()
                except OSError:
                    pass
                finally:
                    sniffeur.desinscrit_web(file)
            else:
                self._envoie(404, b"introuvable")

        def do_POST(self):
            # Contre une page web tierce visant 127.0.0.1 : en-tete personnalise + meme origine
            origine = self.headers.get("Origin", "")
            if self.headers.get("X-Sniffeur") != "1" or (origine and origine not in (
                    f"http://127.0.0.1:{sniffeur.args.http}", f"http://localhost:{sniffeur.args.http}")):
                self._envoie(403, b"refuse")
                return
            try:
                longueur = min(int(self.headers.get("Content-Length", "0") or 0), 256 * 1024)
                demande = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
                if not isinstance(demande, dict):
                    raise ValueError("corps JSON attendu")
                if self.path == "/publier":
                    topic = str(demande.get("topic", "")).strip()
                    if not topic or "#" in topic or "+" in topic or len(topic) > 512:
                        raise ValueError("topic invalide (non vide, sans # ni +)")
                    donnees = str(demande.get("payload", ""))
                    payload = bytes.fromhex(re.sub(r"[\s,;:]|0x", "", donnees)) if demande.get("format") == "hex" \
                        else donnees.encode("utf-8")
                    sniffeur.publie(topic, payload, bool(demande.get("retain")))
                elif self.path == "/abonnements":
                    # Liste vide permise : on peut retirer le dernier abonnement (plus rien n'est recu)
                    filtres = list(dict.fromkeys(str(f).strip() for f in demande.get("filtres", []) if str(f).strip()))
                    if len(filtres) > 50 or not all(valide_filtre(f) for f in filtres):
                        raise ValueError("filtre d'abonnement invalide (ex. #, tele/+/LWT, $SYS/#)")
                    sniffeur.change_abonnements(filtres)
                elif self.path == "/brokers":
                    action = demande.get("action")
                    if action == "enregistrer":
                        identifiant = sniffeur.config.enregistre(demande.get("broker") or {})
                        if identifiant == sniffeur.broker["id"]:        # broker actif modifie : on s'y reconnecte
                            sniffeur.change_broker(identifiant)
                        self._json({"id": identifiant})
                        return
                    if action == "supprimer":
                        actif = demande.get("id") == sniffeur.broker["id"]
                        sniffeur.config.supprime(demande.get("id"))
                        if actif:
                            sniffeur.change_broker(sniffeur_mqtt_config.ID_TASMOTA)
                    elif action == "selectionner":
                        sniffeur.change_broker(demande.get("id"))
                    else:
                        raise ValueError("action inconnue (enregistrer, supprimer, selectionner)")
                elif self.path == "/favoris":
                    if demande.get("action") == "supprimer":
                        sniffeur.config.supprime_favori(str(demande.get("nom", "")))
                    else:
                        sniffeur.config.ajoute_favori(demande)
                else:
                    self._envoie(404, b"introuvable")
                    return
            except (ValueError, TypeError) as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))
                return
            except OSError as erreur:
                self._envoie(409, str(erreur).encode("utf-8"))
                return
            self._envoie(204)

    return Gestionnaire


def main():
    # Console redirigee (tache VS Code, fichier) : cp1252 sous Windows -> un caractere non
    # representable ferait echouer une publication pourtant partie. On remplace au lieu de lever.
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    defaut = lit_config_broker()
    options = argparse.ArgumentParser(description="Sniffeur / publieur MQTT avec page web locale.")
    options.add_argument("--hote", default=defaut.get("MQTT_HOST", ""), help="broker par defaut (MQTT_HOST de user_config_override.h)")
    options.add_argument("--port", type=int, default=int(defaut.get("MQTT_PORT", 1883)))
    options.add_argument("--utilisateur", default=defaut.get("MQTT_USER", ""))
    options.add_argument("--mot-de-passe", dest="mot_de_passe", default=defaut.get("MQTT_PASS", ""))
    options.add_argument("--abonnement", action="append", help="filtre MQTT (repetable) ; defaut : memorise par broker, sinon '#'")
    options.add_argument("--http", type=int, default=7100, help="port de la page http://127.0.0.1:<http>")
    options.add_argument("--journal", help="copie des messages recus dans ce fichier")
    options.add_argument("--historique", type=int, default=5000, help="messages rejoues a l'ouverture de la page")
    options.add_argument("--config", help="fichier de configuration (defaut : %%APPDATA%%\\sniffeur_mqtt\\config.json)")
    args = options.parse_args()
    if args.abonnement and not all(valide_filtre(f) for f in args.abonnement):
        sys.exit("filtre d'abonnement invalide")

    configuration = sniffeur_mqtt_config.Configuration(
        {"nom": "Tasmota (user_config_override.h)", "hote": args.hote, "port": args.port, "tls": False,
         "verifierCertificat": True, "utilisateur": args.utilisateur, "motDePasse": args.mot_de_passe}, args.config)
    sniffeur = Sniffeur(args, configuration)
    try:
        serveur = ThreadingHTTPServer(("127.0.0.1", args.http), fabrique_gestionnaire(sniffeur))
    except OSError as erreur:
        sys.exit(f"port HTTP {args.http} indisponible ({erreur}) : --http <autre port>")
    serveur.daemon_threads = True
    threading.Thread(target=sniffeur.boucle_mqtt, daemon=True).start()
    b = sniffeur.broker
    print(f"sniffeur MQTT : broker '{b.get('nom')}' {b.get('hote')}:{b.get('port')} (utilisateur '{b.get('utilisateur', '')}', "
          f"mot de passe {'fourni' if b.get('motDePasse') else 'aucun'}) -> http://127.0.0.1:{args.http}/  "
          f"(configuration : {configuration.chemin})" + (f"  (journal : {args.journal})" if args.journal else ""))
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        sniffeur.client.ferme()


if __name__ == "__main__":
    main()
