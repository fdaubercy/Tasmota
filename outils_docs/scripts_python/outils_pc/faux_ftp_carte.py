"""Faux serveur FTP de carte Tasmota et fausse commande HTTP, pour les bancs de ftp_cartes_session. Aucun reseau reel.

Imite ESPFtpServer : un seul client a la fois, PASV seul (port de donnees choisi par le banc), commandes
USER PASS PWD CWD TYPE PASV MLSD LIST RETR STOR DELE MKD RMD RNFR RNTO NOOP QUIT. Les fichiers vivent dans un dossier
temporaire (`racine`). Ecoute sur 127.0.0.1 uniquement.

    with FauxFtpCarte(identifiants=("u", "pw")) as srv:   # srv.port = controle, srv.racine = dossier de la carte
        srv.coupe_client()        # la carte deconnecte le client (timeout de 5 min) : le serveur reste allume
        srv.coupe_apres(n)        # apres n commandes : client coupe ET carte perdue (plus aucun port ouvert)
        srv.perdre()              # carte perdue tout de suite

`FausseCommande` remplace `build_ota_http._commande(ip, cmnd, delai)` : journalise (ip, cmnd), repond `UfsFTP n` et `Ufs`.
"""
import re
import socket
import socketserver
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path


class FausseCommande:
    """Faux `commande(ip, cmnd, delai)`. `ufs` : texte rendu a `Ufs` (None = la carte ne repond pas)."""

    def __init__(self, ufs=None, echoue_sur=()):
        self.ufs = ufs
        self.echoue_sur = set(echoue_sur)       # commandes journalisees puis en delai depasse (la carte les a recues)
        self.journal = []                       # [(ip, cmnd)] dans l'ordre

    def __call__(self, ip, cmnd, delai):
        self.journal.append((ip, cmnd))
        if cmnd in self.echoue_sur:
            raise OSError("delai depasse")
        m = re.fullmatch(r"UfsFTP (\d)", cmnd)
        if m:
            return '{"UfsFTP":%s}' % m.group(1)
        if cmnd == "Ufs":
            if self.ufs is None:
                raise OSError("pas de reponse")
            return self.ufs
        raise OSError("commande inconnue : " + cmnd)

    def ufsftp(self):
        """Valeurs n des `UfsFTP n` envoyes, dans l'ordre."""
        return [(ip, int(c.split()[1])) for ip, c in self.journal if c.startswith("UfsFTP ")]


class _Handler(socketserver.StreamRequestHandler):
    def reponse(self, texte):
        self.wfile.write((texte + "\r\n").encode("utf-8"))
        self.wfile.flush()

    def chemin(self, arg):
        p = arg if arg.startswith("/") else (self.cwd.rstrip("/") + "/" + arg if arg else self.cwd)
        return p, self.srv.racine / p.lstrip("/")

    def donnees(self):
        sock, _ = self.pasv.accept()
        self.pasv.close()
        self.pasv = None
        return sock

    def handle(self):
        srv = self.srv = self.server.faux
        self.cwd, self.pasv, self.rnfr, self.connecte = "/", None, None, False
        srv.clients.append(self.request)
        try:
            self.reponse("220 faux serveur FTP de carte")
            while True:
                ligne = self.rfile.readline()
                if not ligne:
                    return
                cmd, _, arg = ligne.decode("utf-8").rstrip("\r\n").partition(" ")
                cmd = cmd.upper()
                srv.commandes.append((cmd, arg))
                if not self.commande(cmd, arg):
                    return
                srv.compte += 1
                if srv.coupe_a is not None and srv.compte >= srv.coupe_a:
                    srv.perdre()
                    return
        except OSError:
            pass
        finally:
            if self.connecte:
                srv.occupe.release()
            if self.pasv:
                self.pasv.close()

    def commande(self, cmd, arg):
        srv = self.srv
        if cmd == "USER":
            if not srv.occupe.acquire(timeout=1):
                self.reponse("421 un seul client a la fois")
                return False
            self.connecte, self.user = True, arg
            self.reponse("331 mot de passe ?")
        elif cmd == "PASS":
            if (self.user, arg) == srv.identifiants:
                self.reponse("230 ok")
            else:
                self.reponse("530 identifiants refuses")
        elif cmd == "PWD":
            self.reponse('257 "%s" est le dossier courant' % self.cwd)
        elif cmd == "CWD":
            p, reel = self.chemin(arg)
            if reel.is_dir():
                self.cwd = p
                self.reponse("250 ok")
            else:
                self.reponse("550 dossier absent")
        elif cmd in ("TYPE", "NOOP"):
            self.reponse("200 ok")
        elif cmd == "PASV":
            self.pasv = socket.socket()
            self.pasv.bind(("127.0.0.1", srv.port_donnees))
            self.pasv.listen(1)
            self.pasv.settimeout(5)
            port = self.pasv.getsockname()[1]
            self.reponse("227 Entering Passive Mode (127,0,0,1,%d,%d)" % (port >> 8, port & 255))
        elif cmd in ("MLSD", "LIST"):
            self.liste(cmd, arg)
        elif cmd == "RETR":
            _, reel = self.chemin(arg)
            if not reel.is_file():
                self.reponse("550 fichier absent")
            else:
                self.reponse("150 envoi")
                with self.donnees() as d:
                    d.sendall(reel.read_bytes())
                self.reponse("226 fini")
        elif cmd == "STOR":
            _, reel = self.chemin(arg)
            self.reponse("150 reception")
            tas = b""
            with self.donnees() as d:
                while True:
                    morceau = d.recv(65536)
                    if not morceau:
                        break
                    tas += morceau
            reel.write_bytes(tas)
            self.reponse("226 fini")
        elif cmd == "DELE":
            _, reel = self.chemin(arg)
            if reel.is_file():
                reel.unlink()
                self.reponse("250 ok")
            else:
                self.reponse("550 fichier absent")
        elif cmd == "MKD":
            _, reel = self.chemin(arg)
            try:
                reel.mkdir()
                self.reponse('257 "%s" cree' % arg)
            except OSError:
                self.reponse("550 impossible")
        elif cmd == "RMD":
            _, reel = self.chemin(arg)
            try:
                reel.rmdir()
                self.reponse("250 ok")
            except OSError:
                self.reponse("550 impossible")
        elif cmd == "RNFR":
            _, reel = self.chemin(arg)
            self.rnfr = reel if reel.exists() else None
            self.reponse("350 destination ?" if self.rnfr else "550 absent")
        elif cmd == "RNTO":
            _, reel = self.chemin(arg)
            if self.rnfr and reel.parent.is_dir():
                self.rnfr.rename(reel)
                self.reponse("250 ok")
            else:
                self.reponse("550 impossible")
        elif cmd == "QUIT":
            self.reponse("221 au revoir")
            return False
        else:
            self.reponse("502 commande inconnue")
        return True

    def liste(self, cmd, arg):
        _, reel = self.chemin(arg)
        if cmd == "MLSD" and self.srv.sans_mlsd:
            self.reponse("500 MLSD inconnu")
            return
        if not reel.is_dir():
            self.reponse("550 dossier absent")
            return
        lignes = []
        for f in sorted(reel.iterdir()):
            st = f.stat()
            dossier = f.is_dir()
            if cmd == "MLSD":
                quand = datetime.fromtimestamp(st.st_mtime).strftime("%Y%m%d%H%M%S")
                lignes.append("type=%s;size=%d;modify=%s; %s" % ("dir" if dossier else "file", st.st_size, quand, f.name))
            else:
                quand = datetime.fromtimestamp(st.st_mtime).strftime("%b %d %H:%M")
                lignes.append("%srw-rw-r-- 1 carte carte %d %s %s" % ("d" if dossier else "-", st.st_size, quand, f.name))
        for n in self.srv.noms_pieges:
            lignes.append(("type=file;size=1;modify=20260101000000; " if cmd == "MLSD" else "-rw-rw-r-- 1 carte carte 1 Jan 01 00:00 ") + n)
        self.reponse("150 liste")
        with self.donnees() as d:
            d.sendall("".join(x + "\r\n" for x in lignes).encode("utf-8"))
        self.reponse("226 fini")


class _Serveur(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class FauxFtpCarte:
    def __init__(self, identifiants=("u", "pw"), port_donnees=0, sans_mlsd=False, noms_pieges=()):
        self._tmp = tempfile.TemporaryDirectory()
        self.racine = Path(self._tmp.name)
        self.identifiants, self.port_donnees, self.sans_mlsd = identifiants, port_donnees, sans_mlsd
        self.noms_pieges = list(noms_pieges)    # noms hostiles ajoutes a chaque liste (../x, a\b...)
        self.commandes, self.clients, self.compte, self.coupe_a = [], [], 0, None
        self.occupe = threading.Semaphore(1)
        self._verrou_perdu = threading.Lock()   # perdre() : le fil est cree ET demarre avant que arrete() le joigne
        self.srv = _Serveur(("127.0.0.1", 0), _Handler)
        self.srv.faux = self
        self.port = self.srv.server_address[1]
        self.ouvert = True
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.arrete()

    def coupe_client(self):
        """Deconnecte les clients (la carte n'a plus de commande depuis 5 min) ; le serveur reste ouvert."""
        for s in self.clients:
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self.clients.clear()

    def coupe_apres(self, n):
        """Apres n commandes de plus : client coupe et carte perdue."""
        self.compte, self.coupe_a = 0, n

    def perdre(self):
        """Carte perdue : plus aucun port ouvert."""
        self.coupe_client()
        with self._verrou_perdu:
            if self.ouvert:
                self._fil = threading.Thread(target=self._ferme, daemon=True)
                self._fil.start()
                self.ouvert = False

    def _ferme(self):
        self.srv.shutdown()
        self.srv.server_close()

    def arrete(self):
        self.perdre()
        self._fil.join(5)                      # laisse le serveur se fermer avant d'effacer le dossier
        time.sleep(0.05)                       # et les gestionnaires finir leurs fichiers
        self._tmp.cleanup()
