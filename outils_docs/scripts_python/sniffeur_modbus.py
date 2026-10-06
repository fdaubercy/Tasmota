r"""Sniffeur ModBus RTU (RS485) avec page web locale, par un convertisseur USB-RS485 branche sur le bus.

Materiel vise : Waveshare USB TO RS485 (CH343G + SP485EEN, direction automatique).
Bornes : A+ -> A du bus, B- -> B du bus, GND -> masse du bus.

Ce que fait ce serveur :
    - ecoute le bus SANS EMETTRE : chaque trame est decoupee (CRC), decodee (requete / reponse /
      exception, registres, ordres de la carte 16 relais) et servie en direct sur la page ;
    - apparie requetes et reponses : latence par esclave, requetes restees sans reponse
      (au-dela de --delai s), exceptions, trames CRC KO ;
    - depuis la page : choix du port et du debit (Ouvrir / Fermer : Fermer LIBERE le port), envoi
      d'une trame (CRC ajoute, rafale possible), raccourcis carte 16 relais (lire, commander un canal),
      emulation de la carte 16 relais (pour tester le maitre P4 sans elle) ;
    - journal fichier optionnel (--journal).
La logique ModBus (CRC, decoupage, decodage, carte emulee) est celle de test_rs485_pc.py.

UN SEUL MAITRE SUR LE BUS : envoyer depuis la page fait du PC un maitre. Si le P4 sonde le bus en
meme temps, les trames se percutent -> charger test_liaison_modbus.be sur le P4 (il suspend sa file)
ou le debrancher. L'ecoute seule ne perturbe rien. L'emulation : debrancher la vraie carte relais.

Usage (Python de PlatformIO, qui fournit pyserial) :
    %USERPROFILE%\.platformio\penv\Scripts\python.exe outils_docs/scripts_python/sniffeur_modbus.py
    options : --port auto|COM12|loop://|aucun  --debit 19200  --http 7300  --silence 0.02
              --delai 1.0  --journal fichier.log  --historique 5000
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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import serial
from serial.tools import list_ports

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sniffeur_modbus_web      # noqa: E402
import test_rs485_pc as rs      # noqa: E402

VID_PID_CH343 = (0x1A86, 0x55D3)
DELAI_ECHO = 0.5                # s : une trame identique a notre envoi, recue avant, est son echo


def port_auto():
    """Le seul port CH343 present, sinon None (les cartes ESP32 en portent souvent un aussi)."""
    ports = [p.device for p in list_ports.comports() if (p.vid, p.pid) == VID_PID_CH343]
    return ports[0] if len(ports) == 1 else None


def nature(trame, attendue):
    """'requete', 'reponse', 'exception', 'ko' ou '?'. attendue : requete sans reponse (ou None),
    seule facon de distinguer une reponse 0x05/0x06 (echo de la requete) d'une nouvelle requete."""
    if not rs.crc_ok(trame):
        return "ko"
    fc, d = trame[1], trame[2:-2]
    if fc & 0x80:
        return "exception"
    meme = attendue is not None and attendue[:2] == trame[:2]
    if fc in (1, 2, 3, 4):
        if len(d) == 1 + d[0] and (meme or len(d) != 4):
            return "reponse"
        return "requete" if len(d) == 4 else "?"
    if fc in (5, 6) and len(d) == 4:
        return "reponse" if meme and attendue == trame else "requete"
    if fc in (15, 16):
        if len(d) == 4:
            return "reponse"
        return "requete" if len(d) >= 5 and len(d) == 5 + d[4] else "?"
    return "?"


class Journal:
    def __init__(self, chemin):
        self.fichier = open(chemin, "a", encoding="utf-8")

    def ecrit(self, ligne):
        self.fichier.write(ligne + "\n")
        self.fichier.flush()


class Sniffeur:
    def __init__(self, args):
        self.args = args
        self.journal = Journal(args.journal) if args.journal else None
        self.verrou = threading.Lock()          # historique, statistiques, pages web
        self.verrou_port = threading.Lock()     # ouverture / fermeture / ecriture du port
        self.port = None
        self.nom_port, self.debit, self.erreur = "", args.debit, ""
        self.historique = collections.deque(maxlen=args.historique)
        self.clients_web = []
        self.stats = {}                         # {id: {id, requetes, reponses, sans_reponse, exceptions, lat, lat_max}}
        self.nb, self.nb_ko, self.t_prec = 0, 0, None
        self.attendue = None                    # (trame, instant) de la requete en attente de reponse
        self.dernier_envoi, self.t_envoi = None, 0.0
        self.emulation = None                   # rs.CarteRelaisEmulee ou None
        self.debut = time.strftime("%d/%m %H:%M:%S")

    # ------------------------------------------------------------------ diffusion vers les pages
    def etat(self):
        return {"port": self.nom_port, "debit": self.debit, "ouvert": self.port is not None,
                "erreur": self.erreur, "emulation": self.emulation.id if self.emulation else None,
                "nb": self.nb, "ko": self.nb_ko, "depuis": self.debut, "delai": self.args.delai}

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

    def diffuse_etat(self):
        with self.verrou:
            self._diffuse([self._paquet("etat", self.etat())])

    def message(self, texte):
        print(texte)
        with self.verrou:
            self._diffuse([self._paquet("message", {"texte": texte})])

    def inscrit_web(self):
        file = queue.Queue()
        with self.verrou:
            file.put(self._paquet("etat", self.etat()))
            file.put(self._paquet("stats", list(self.stats.values())))
            for paquet in self.historique:
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
                                             stopbits=1, timeout=0)
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

    def envoie(self, trame, source="pc"):
        with self.verrou_port:
            if self.port is None:
                raise OSError("port serie ferme : l'ouvrir d'abord")
            self.port.write(trame)
            self.port.flush()
            self.dernier_envoi, self.t_envoi = bytes(trame), time.monotonic()
        self.traite(trame, source)

    def rafale(self, trame, repete, intervalle):
        try:
            for k in range(repete):
                if k:
                    time.sleep(intervalle)
                self.envoie(trame)
        except (OSError, serial.SerialException) as erreur:
            self.message(f"envoi interrompu : {erreur}")

    # ------------------------------------------------------------------ trames
    def traite(self, trame, source):
        """Classe, compte, journalise et diffuse une trame ; emulation : repond a une requete du bus."""
        maintenant = time.monotonic()
        with self.verrou:
            if source == "bus" and trame == self.dernier_envoi and maintenant - self.t_envoi < DELAI_ECHO:
                self.dernier_envoi = None
                return
            nat = nature(trame, self.attendue[0] if self.attendue else None)
            fiche = {"t": time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}",
                     "dt": None if self.t_prec is None else round((maintenant - self.t_prec) * 1000),
                     "sens": source, "hex": rs.hexa(trame), "crc": nat != "ko", "nature": nat,
                     "id": trame[0] if trame else None, "fc": trame[1] if len(trame) > 1 else None,
                     "texte": rs.decrit(trame), "lat": None}
            self.t_prec = maintenant
            self.nb += 1
            if nat == "ko":
                self.nb_ko += 1
            else:
                s = self.stats.setdefault(trame[0], {"id": trame[0], "requetes": 0, "reponses": 0,
                                                     "sans_reponse": 0, "exceptions": 0, "lat": None, "lat_max": 0})
                if nat == "requete":
                    self._sans_reponse()
                    s["requetes"] += 1
                    self.attendue = (bytes(trame), maintenant)
                elif nat in ("reponse", "exception"):
                    s["reponses" if nat == "reponse" else "exceptions"] += 1
                    if self.attendue and self.attendue[0][0] == trame[0]:
                        s["lat"] = fiche["lat"] = round((maintenant - self.attendue[1]) * 1000)
                        s["lat_max"] = max(s["lat_max"], s["lat"])
                        self.attendue = None
            if self.journal:
                self.journal.ecrit(f"{time.strftime('%Y-%m-%d')} {fiche['t']} {source:<4} {fiche['hex']:<40} "
                                   f"{'CRC OK' if fiche['crc'] else 'CRC KO'} {fiche['texte']}")
            paquet = self._paquet("trame", fiche)
            self._diffuse([paquet, self._paquet("stats", list(self.stats.values()))], memorise=paquet)
            reponse = self.emulation.reponse(trame) if source == "bus" and nat == "requete" and self.emulation else None
        if reponse:
            try:
                self.envoie(reponse, "emul")
            except (OSError, serial.SerialException) as erreur:
                self.message(f"emulation : reponse non envoyee ({erreur})")

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
        fiche = {"t": time.strftime("%H:%M:%S"), "dt": None, "sens": "--", "hex": "", "crc": True,
                 "nature": "timeout", "id": trame[0], "fc": trame[1], "lat": None,
                 "texte": f"id {trame[0]} : PAS DE REPONSE ({attente} ms) a {rs.hexa(trame)}"}
        paquet = self._paquet("trame", fiche)
        self._diffuse([paquet, self._paquet("stats", list(self.stats.values()))], memorise=paquet)

    def verifie_attente(self):
        maintenant = time.monotonic()
        with self.verrou:
            if self.attendue and maintenant - self.attendue[1] > self.args.delai:
                self._sans_reponse(maintenant)

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
                    self.traite(trame, "bus")
                tampon.clear()
            self.verifie_attente()
            time.sleep(0.001)

    def raz(self):
        with self.verrou:
            self.stats, self.nb, self.nb_ko, self.attendue = {}, 0, 0, None
            self.historique.clear()
            self._diffuse([self._paquet("raz", {}), self._paquet("etat", self.etat()), self._paquet("stats", [])])


def lit_demande(demande, sniffeur, chemin):
    """Execute une demande POST (dict deja decode) ; ValueError si invalide."""
    if chemin == "/port":
        if demande.get("action") == "fermer":
            sniffeur.ferme()
            return
        nom = str(demande.get("port", "")).strip()
        debit = int(demande.get("debit", sniffeur.debit))
        if not nom or not 300 <= debit <= 3000000:
            raise ValueError("port vide ou debit hors bornes (300..3000000)")
        sniffeur.ouvre(nom, debit)
    elif chemin == "/envoi":
        trame = rs.lit_hexa(str(demande.get("hex", "")))
        if demande.get("crc", True):
            trame = rs.avec_crc(trame)
        repete, intervalle = int(demande.get("repete", 1)), float(demande.get("intervalle", 0.5))
        if not 2 <= len(trame) <= 256 or not 1 <= repete <= 1000 or not 0.05 <= intervalle <= 60:
            raise ValueError("trame 2..256 octets, repete 1..1000, intervalle 0.05..60 s")
        if sniffeur.port is None:
            raise OSError("port serie ferme : l'ouvrir d'abord")
        threading.Thread(target=sniffeur.rafale, args=(trame, repete, intervalle), daemon=True).start()
    elif chemin == "/emulation":
        ident = int(demande.get("id", 1))
        if not 1 <= ident <= 247:
            raise ValueError("adresse 1..247")
        sniffeur.emulation = rs.CarteRelaisEmulee(ident, sniffeur.debit) if demande.get("actif") else None
        sniffeur.diffuse_etat()
    elif chemin == "/raz":
        sniffeur.raz()
    else:
        raise LookupError(chemin)


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

        def do_GET(self):
            chemin = urlsplit(self.path).path
            if chemin == "/":
                self._envoie(200, sniffeur_modbus_web.PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif chemin == "/ports":
                ports = [{"port": p.device, "description": p.description,
                          "ch343": (p.vid, p.pid) == VID_PID_CH343} for p in list_ports.comports()]
                self._envoie(200, json.dumps(ports).encode("utf-8"), "application/json")
            elif chemin == "/flux":
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
            # Une page tierce pourrait viser 127.0.0.1 et commander des relais : en-tete personnalise
            # (impose un pre-vol CORS auquel ce serveur ne repond pas) + meme origine.
            origine = self.headers.get("Origin", "")
            if self.headers.get("X-Sniffeur") != "1" or (origine and origine not in (
                    f"http://127.0.0.1:{sniffeur.args.http}", f"http://localhost:{sniffeur.args.http}")):
                self._envoie(403, b"refuse")
                return
            try:
                longueur = min(int(self.headers.get("Content-Length", "0") or 0), 64 * 1024)
                demande = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
                if not isinstance(demande, dict):
                    raise ValueError("corps JSON attendu")
                lit_demande(demande, sniffeur, urlsplit(self.path).path)
            except LookupError:
                self._envoie(404, b"introuvable")
                return
            except (ValueError, TypeError) as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))
                return
            except (OSError, serial.SerialException) as erreur:
                self._envoie(409, str(erreur).encode("utf-8"))
                return
            self._envoie(200, b"ok")

    return Gestionnaire


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
    options.add_argument("--journal", help="copie des trames dans ce fichier")
    options.add_argument("--historique", type=int, default=5000, help="trames rejouees a l'ouverture de la page")
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
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        sniffeur.ferme()


if __name__ == "__main__":
    main()
