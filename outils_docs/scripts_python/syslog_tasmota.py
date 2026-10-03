"""Serveur syslog pour les modules Tasmota : recoit leurs logs en UDP et les sert sur une page locale.

Principe : Tasmota envoie chaque ligne de log en UDP (RFC5424) vers LogHost:LogPort, des que SysLog > 0.
Defauts de compilation : SYS_LOG_HOST / SYS_LOG_PORT / SYS_LOG_LEVEL de tasmota/user_config_override.h
(reappliques a chaque flash, CFG_HOLDER changeant a chaque build). A chaud : LogHost, LogPort, SysLog.
Format recu (tasmota_support/support.ino, SyslogAsync) :
    <PRI>1 2026-10-03T14:02:11.123000+02:00 <hostname> tasmota - - - BRY: message
    PRI = 128 + severite : 131 erreur, 134 info, 135 debug (Tasmota DEBUG et DEBUG_MORE confondus)
Les formats RFC3164 et anciens (« <PRI>hote TAG: msg ») sont aussi acceptes ; sinon la ligne brute
est gardee, avec l'IP source comme module.

Ce que fait ce serveur :
    - ecoute UDP <ecoute>:<port> (defaut 0.0.0.0:514 ; pas besoin d'etre administrateur sous Windows) ;
    - page http://127.0.0.1:<http> (syslog_tasmota_web.py) : direct, filtre module / severite / texte,
      pause, export ; registre des modules vus (IP, nombre de lignes, derniere reception) ;
    - journal fichier (une ligne par message, horodatage du PC), avec rotation a --journal-max Mo.
Aucun POST : la page ne fait que lire (rien a proteger contre une page tierce).

Usage (Python de PlatformIO ou tout Python 3.8+, aucune dependance) :
    python outils_docs/scripts_python/syslog_tasmota.py
    options : --port 514  --ecoute 0.0.0.0  --http 7200  --journal fichier.log  --journal-max 20
              --historique 5000
Depuis VS Code : pioarduino > Project Tasks > <env> > Custom > « Serveur syslog (HTTP 127.0.0.1) »
(cible_syslog_tasmota.py). Arret : Ctrl+C dans le terminal de la tache (ou la corbeille).
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
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import syslog_tasmota_web       # noqa: E402

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG = os.path.join(RACINE, "tasmota", "user_config_override.h")
TAILLE_MAX_DATAGRAMME = 65535

# <PRI>1 TIMESTAMP HOSTNAME APP-NAME PROCID MSGID STRUCTURED-DATA [MSG]  (RFC5424)
RE_5424 = re.compile(r"^<(\d{1,3})>1 (\S+) (\S+) (\S+) (\S+) (\S+) (-|(?:\[.*?\])+) ?(.*)$", re.S)
# <PRI>Mmm dd hh:mm:ss HOSTNAME TAG: MSG  (RFC3164)
RE_3164 = re.compile(r"^<(\d{1,3})>([A-Z][a-z]{2} [ \d]\d \d\d:\d\d:\d\d) (\S+) ([^:\s]+):? ?(.*)$", re.S)
# <PRI>HOSTNAME TAG: MSG  (ancien format Tasmota, jusqu'a v13.3.0.1)
RE_ANCIEN = re.compile(r"^<(\d{1,3})>(\S+) ([^:\s]+): ?(.*)$", re.S)
RE_CATEGORIE = re.compile(r"^([A-Z][A-Z0-9]{2}): ")             # « BRY: », « MQT: », « HTP: »...
SEVERITES = ("EMERG", "ALERT", "CRIT", "ERR", "WARN", "NOTICE", "INFO", "DEBUG")


def lit_config_syslog(chemin=CONFIG):
    """1re definition de SYS_LOG_HOST / SYS_LOG_PORT dans user_config_override.h (pour information)."""
    valeurs = {}
    try:
        texte = open(chemin, encoding="utf-8", errors="replace").read()
    except OSError:
        return valeurs
    for cle in ("SYS_LOG_HOST", "SYS_LOG_PORT"):
        m = re.search(r'^\s*#define\s+' + cle + r'\s+("([^"]*)"|(\d+))', texte, re.M)
        if m:
            valeurs[cle] = m.group(2) if m.group(2) is not None else m.group(3)
    return valeurs


def analyse(octets, ip):
    """Datagramme syslog -> dict {module, sev, horodatage, app, categorie, texte}. Ne leve jamais."""
    texte = octets.decode("utf-8", errors="replace").replace("\ufeff", "").rstrip("\r\n\0")
    fiche = {"module": ip, "sev": None, "horodatage": "", "app": "", "categorie": "", "texte": texte}
    m = RE_5424.match(texte)
    if m:
        fiche.update(sev=int(m.group(1)) & 7, horodatage=m.group(2), module=m.group(3), app=m.group(4),
                     texte=m.group(8))
    else:
        m = RE_3164.match(texte)
        if m:
            fiche.update(sev=int(m.group(1)) & 7, horodatage=m.group(2), module=m.group(3), app=m.group(4),
                         texte=m.group(5))
        else:
            m = RE_ANCIEN.match(texte)
            if m:
                fiche.update(sev=int(m.group(1)) & 7, module=m.group(2), app=m.group(3), texte=m.group(4))
    if fiche["horodatage"] == "-":
        fiche["horodatage"] = ""
    if fiche["module"] in ("-", ""):
        fiche["module"] = ip
    c = RE_CATEGORIE.match(fiche["texte"])
    if c:
        fiche["categorie"] = c.group(1)
    return fiche


class Journal:
    """Fichier texte en ajout, bascule en <fichier>.1 au-dela de 'max_octets' (un seul ancien garde)."""

    def __init__(self, chemin, max_octets):
        self.chemin, self.max_octets = chemin, max_octets
        self.fichier = open(chemin, "a", encoding="utf-8")

    def ecrit(self, ligne):
        self.fichier.write(ligne + "\n")
        self.fichier.flush()
        if self.max_octets and self.fichier.tell() > self.max_octets:
            self.fichier.close()
            try:
                os.replace(self.chemin, self.chemin + ".1")
            except OSError:
                pass                    # fichier verrouille (lu ailleurs) : on continue dans le meme
            self.fichier = open(self.chemin, "a", encoding="utf-8")


class Serveur:
    def __init__(self, args):
        self.args = args
        self.journal = Journal(args.journal, args.journal_max * 1024 * 1024) if args.journal else None
        self.nb_recus = 0
        self.debut = time.strftime("%d/%m %H:%M:%S")
        self.historique = collections.deque(maxlen=args.historique)
        self.modules = {}                                   # {nom: {module, ip, nb, dernier, erreurs}}
        self.clients_web = []
        self.verrou = threading.Lock()

    # ------------------------------------------------------------------ etat et diffusion
    def etat(self):
        return {"ecoute": f"{self.args.ecoute}:{self.args.port}", "recus": self.nb_recus, "depuis": self.debut,
                "http": self.args.http, "journal": self.args.journal or "", "logHost": self.args.loghost}

    @staticmethod
    def _paquet(evenement, donnees):
        return f"event: {evenement}\ndata: {json.dumps(donnees)}\n\n".encode("utf-8")

    def _diffuse(self, paquets, memorise=None):
        """Sous le verrou : une page qui s'inscrit voit soit l'ancien etat + l'evenement, soit le nouveau."""
        with self.verrou:
            if memorise is not None:
                self.historique.append(memorise)
            for file in self.clients_web:
                for paquet in paquets:
                    file.put(paquet)

    def inscrit_web(self):
        file = queue.Queue()
        with self.verrou:
            file.put(self._paquet("etat", self.etat()))
            for fiche in self.modules.values():
                file.put(self._paquet("module", fiche))
            for paquet in self.historique:
                file.put(paquet)
            self.clients_web.append(file)
        return file

    def desinscrit_web(self, file):
        with self.verrou:
            if file in self.clients_web:
                self.clients_web.remove(file)

    # ------------------------------------------------------------------ reception UDP
    def recu(self, octets, ip):
        fiche = analyse(octets, ip)
        maintenant = time.time()
        fiche["t"] = time.strftime("%H:%M:%S", time.localtime(maintenant)) + f".{int(maintenant * 1000) % 1000:03d}"
        fiche["ip"] = ip
        self.nb_recus += 1
        module = self.modules.setdefault(fiche["module"], {"module": fiche["module"], "nb": 0, "erreurs": 0})
        module.update(ip=ip, dernier=fiche["t"], nb=module["nb"] + 1)
        if fiche["sev"] is not None and fiche["sev"] <= 3:
            module["erreurs"] += 1
        if self.journal:
            sev = SEVERITES[fiche["sev"]] if fiche["sev"] is not None else "-"
            self.journal.ecrit(f"{time.strftime('%Y-%m-%d')} {fiche['t']} {ip:<15} {fiche['module']:<24} "
                               f"{sev:<5} {fiche['texte']}")
        paquet = self._paquet("log", fiche)
        self._diffuse([paquet, self._paquet("module", dict(module))], memorise=paquet)

    def boucle_udp(self, sock):
        while True:
            try:
                octets, (ip, _port) = sock.recvfrom(TAILLE_MAX_DATAGRAMME)
            except OSError:
                continue                # ICMP « port inaccessible » remonte en WinError 10054 : sans objet
            try:
                self.recu(octets, ip)
            except Exception as erreur:     # un paquet mal forme ne doit jamais arreter l'ecoute
                print(f"paquet de {ip} ignore : {erreur!r}")


def fabrique_gestionnaire(serveur):
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

        def do_GET(self):
            chemin = urlsplit(self.path).path
            if chemin == "/":
                self._envoie(200, syslog_tasmota_web.PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif chemin == "/etat":
                self._envoie(200, json.dumps(serveur.etat()).encode("utf-8"), "application/json")
            elif chemin == "/modules":
                with serveur.verrou:
                    corps = json.dumps(list(serveur.modules.values()))
                self._envoie(200, corps.encode("utf-8"), "application/json")
            elif chemin == "/flux":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                file = serveur.inscrit_web()
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
                    serveur.desinscrit_web(file)
            else:
                self._envoie(404, b"introuvable")

    return Gestionnaire


def main():
    # Console redirigee (tache VS Code, fichier) : cp1252 sous Windows -> on remplace au lieu de lever.
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    defaut = lit_config_syslog()
    options = argparse.ArgumentParser(description="Serveur syslog (UDP) pour modules Tasmota, avec page web locale.")
    options.add_argument("--port", type=int, default=int(defaut.get("SYS_LOG_PORT", 514)),
                         help="port UDP ecoute (defaut : SYS_LOG_PORT de user_config_override.h, sinon 514)")
    options.add_argument("--ecoute", default="0.0.0.0", help="adresse d'ecoute UDP (defaut : toutes)")
    options.add_argument("--http", type=int, default=7200, help="port de la page http://127.0.0.1:<http>")
    options.add_argument("--journal", help="copie des messages recus dans ce fichier")
    options.add_argument("--journal-max", dest="journal_max", type=int, default=20,
                         help="taille (Mo) au-dela de laquelle le journal bascule en .1 (0 : jamais)")
    options.add_argument("--historique", type=int, default=5000, help="lignes rejouees a l'ouverture de la page")
    args = options.parse_args()
    args.loghost = defaut.get("SYS_LOG_HOST", "")
    if not 0 < args.port < 65536 or not 0 < args.http < 65536 or args.historique < 0 or args.journal_max < 0:
        sys.exit("parametre hors bornes (ports 1..65535, historique et journal-max >= 0)")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # PAS de SO_REUSEADDR : sous Windows il laisserait deux serveurs se partager (se voler) le port.
    try:
        sock.bind((args.ecoute, args.port))
    except OSError as erreur:
        sys.exit(f"port UDP {args.port} indisponible ({erreur}) : un autre serveur syslog tourne-t-il deja ?")
    serveur = Serveur(args)
    try:
        http = ThreadingHTTPServer(("127.0.0.1", args.http), fabrique_gestionnaire(serveur))
    except OSError as erreur:
        sys.exit(f"port HTTP {args.http} indisponible ({erreur}) : --http <autre port>")
    http.daemon_threads = True
    threading.Thread(target=serveur.boucle_udp, args=(sock,), daemon=True).start()

    # IP de ce poste sur le reseau des modules : celle de l'interface qui sortirait vers LogHost
    # (connect UDP : aucun paquet emis). gethostbyname(gethostname()) peut rendre une carte virtuelle.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sonde:
            sonde.connect((args.loghost or "192.168.0.1", args.port))
            ip_poste = sonde.getsockname()[0]
    except OSError:
        ip_poste = "?"
    print(f"serveur syslog : UDP {args.ecoute}:{args.port} -> http://127.0.0.1:{args.http}/"
          + (f"  (journal : {args.journal})" if args.journal else ""))
    if args.loghost and args.loghost != ip_poste:
        print(f"  attention : SYS_LOG_HOST = {args.loghost} dans user_config_override.h, ce poste semble etre "
              f"{ip_poste} -> les modules n'enverront ici qu'avec 'LogHost <ip de ce poste>'.")
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()


if __name__ == "__main__":
    main()
