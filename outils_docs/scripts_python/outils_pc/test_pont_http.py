"""Banc de la liaison HTTP du pont serie (pont_http.py, --ip de pont_serie.py). Code de sortie 0 = vert.

Une fausse console web Tasmota (/cs, format de xdrv_01_9_webserver.ino::HandleConsoleRefresh) tourne en
local sur un port libre : aucune carte, aucun COM, ni les ports 7000/7001 ne sont touches.
1. pont_http seul : adresse validee, index de log qui avance, commandes par ligne complete, 401 et
   serveur non Tasmota refuses a l'ouverture.
2. le VRAI pont_serie.py lance avec --ip http://... : /etat ouvert, commande de la page recue par la carte,
   case « Relancer le log serie » sans effet (aucun SerialLog ecrit), mode Hex refuse, logs de la carte
   rendus au client TCP brut.
Temoins : une lecture seule n'envoie aucune commande ; la 2e lecture ne rend PAS tout le tampon.
Lancer avec le Python de PlatformIO (pyserial, pour la partie 2).
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()

import http.client
import http.server
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.parse

import pont_http

ICI = os.path.dirname(os.path.abspath(__file__))
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class FausseCarte:
    """Console web Tasmota minimale : tampon de log numerote, commandes c1 notees (et loguees comme Tasmota)."""
    def __init__(self, statut=200, html=False, location=None, retard=0.0):
        self.lignes, self.commandes = [], []          # lignes[i] a l'index i+1
        self.statut, self.html, self.location = statut, html, location
        self.requetes, self.retard = 0, retard          # retard : s avant de repondre a une commande c1
        carte = self

        class Gestion(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                carte.requetes += 1
                url = urllib.parse.urlparse(self.path)
                args = dict(urllib.parse.parse_qsl(url.query))
                if carte.statut != 200:
                    self.send_response(carte.statut)
                    if carte.location:
                        self.send_header("Location", carte.location + self.path)
                    self.end_headers()
                    return
                if "c1" in args:
                    carte.commandes.append(args["c1"])
                    carte.log(f"CMD: {args['c1']}")
                    time.sleep(carte.retard)
                if carte.html:
                    corps = "<html>pas une console</html>"
                else:
                    depart = int(args.get("c2", "0") or 0)
                    nouvelles = carte.lignes[depart:]
                    corps = f"{len(carte.lignes)}}}1{1}}}1" + "\n".join(nouvelles) + "}1"
                donnees = corps.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Length", str(len(donnees)))
                self.end_headers()
                self.wfile.write(donnees)

            def log_message(self, *_):
                pass

        self.serveur = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Gestion)
        self.port = self.serveur.server_address[1]
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def log(self, texte):
        self.lignes.append(f"12:00:00.000 {texte}")

    def arrete(self):
        self.serveur.shutdown()


def lit_jusqua(liaison, delai=5.0):
    """read() repete jusqu'a recevoir quelque chose (ou le delai passe)."""
    limite = time.time() + delai
    while time.time() < limite:
        octets = liaison.read()
        if octets:
            return octets
    return b""


def cas_module():
    verifie(pont_http.normalise("192.168.1.50"), "http://192.168.1.50", "adresse : IP nue")
    verifie(pont_http.normalise(" http://carte.local:8080/ "), "http://carte.local:8080", "adresse : nom + port")
    for mauvaise in ("", "192.168.1.50/cs?c1=Restart", "admin:mdp@1.2.3.4", "1.2.3.4:0", "1.2.3.4:70000", "a b"):
        try:
            pont_http.normalise(mauvaise)
            verifie("acceptee", "refusee", f"adresse refusee : {mauvaise!r}")
        except ValueError:
            verifie("refusee", "refusee", f"adresse refusee : {mauvaise!r}")

    verifie([pont_http.est_boucle(u) for u in ("http://127.0.0.1:7700", "http://localhost", "http://169.254.1.1",
                                               "http://192.168.1.50", "COM3")],
            [True, True, True, False, False], "boucle locale reconnue (refusee depuis un autre appareil)")

    lente = FausseCarte(retard=pont_http.DELAI + 1)
    try:
        liaison = pont_http.LiaisonHttp(f"127.0.0.1:{lente.port}")
        try:
            liaison.write(b"Power TOGGLE\n")
            verifie("pas d'erreur", "pas d'erreur", "commande sans reponse dans le delai : pas d'echec annonce")
        except OSError as erreur:
            verifie(str(erreur), "pas d'erreur", "commande sans reponse dans le delai : pas d'echec annonce")
        verifie(lente.commandes, ["Power TOGGLE"], "commande sans reponse : executee une seule fois")
    finally:
        lente.arrete()

    carte = FausseCarte()
    carte.log("INF: premiere ligne")
    carte.log("INF: deuxieme ligne")
    try:
        liaison = pont_http.LiaisonHttp(f"127.0.0.1:{carte.port}")
        verifie(liaison.read(), b"12:00:00.000 INF: premiere ligne\n12:00:00.000 INF: deuxieme ligne\n",
                "ouverture : tout le tampon de log rendu au premier read")
        carte.log("INF: troisieme")
        verifie(lit_jusqua(liaison), b"12:00:00.000 INF: troisieme\n", "temoin : 2e lecture = la ligne neuve seule")
        verifie(carte.commandes, [], "temoin : lire n'envoie aucune commande")
        liaison.write(b"Status 0\n")
        verifie(carte.commandes, ["Status 0"], "commande envoyee par c1")
        liaison.write(b"Pow")
        verifie(carte.commandes, ["Status 0"], "ligne incomplete : rien n'est envoye")
        liaison.write(b"er 1\r\n\r\n")
        verifie(carte.commandes, ["Status 0", "Power 1"], "ligne completee : une seule commande, lignes vides ignorees")
        verifie(lit_jusqua(liaison), b"12:00:00.000 CMD: Status 0\n12:00:00.000 CMD: Power 1\n",
                "reponse des commandes relue par le log")
    finally:
        carte.arrete()

    cible = FausseCarte()   # vraie console : une redirection suivie ouvrirait la liaison sur elle
    for libelle, carte, attendu in (("401 (WebPassword)", FausseCarte(statut=401), "WebPassword"),
                                    ("serveur non Tasmota", FausseCarte(html=True), "pas la console web"),
                                    ("redirection non suivie", FausseCarte(statut=302, location=f"http://127.0.0.1:{cible.port}"),
                                     "HTTP 302")):
        try:
            pont_http.LiaisonHttp(f"127.0.0.1:{carte.port}")
            verifie("ouverte", "OSError", f"refus a l'ouverture : {libelle}")
        except OSError as erreur:
            verifie(attendu in str(erreur), True, f"refus a l'ouverture : {libelle}")
        finally:
            carte.arrete()
    verifie(cible.requetes, 0, "redirection : la cible n'a recu aucune requete")
    cible.arrete()


def requete(port, methode="GET", chemin="/", corps=b""):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    c.request(methode, chemin, body=corps or None, headers={"X-Pont": "1"} if methode == "POST" else {})
    r = c.getresponse()
    donnees = r.read()
    c.close()
    return r.status, donnees


def cas_pont():
    carte = FausseCarte()
    carte.log("INF: carte prete")
    tcp = port_libre()
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    proc = subprocess.Popen([sys.executable, "-u", os.path.join(ICI, "pont_serie.py"), "--ip", f"http://127.0.0.1:{carte.port}",
                             "--tcp", str(tcp), "--sans-couleurs", "--sans-navigateur", "--local"],
                            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, env=env)
    try:
        etat = None
        limite = time.time() + 15
        while time.time() < limite and etat is None:
            try:
                etat = json.loads(requete(tcp, chemin="/etat")[1])
            except OSError:
                time.sleep(0.2)
        verifie((etat or {}).get("ouvert"), True, "pont --ip : liaison ouverte")
        verifie((etat or {}).get("port"), f"http://127.0.0.1:{carte.port}", "pont --ip : port = l'URL de la carte")

        verifie(requete(tcp, "POST", "/relance", b'{"actif": true}')[0], 200, "page : case Relancer cochee")
        brut = socket.create_connection(("127.0.0.1", tcp), timeout=5)
        time.sleep(0.6)   # le pont met 0,3 s a classer un client TCP brut ; sans rejeu, une ligne diffusee avant serait perdue
        statut = requete(tcp, "POST", "/envoi", json.dumps({"mode": "texte", "donnees": "Status 5", "finLigne": "LF"}).encode())[0]
        verifie(statut, 204, "page : commande Texte acceptee")
        verifie(carte.commandes, ["Status 5"], "page : commande recue par la carte, aucun SerialLog (case cochee)")
        statut = requete(tcp, "POST", "/envoi", json.dumps({"mode": "hex", "donnees": "01 06"}).encode())[0]
        verifie(statut, 400, "page : mode Hex refuse en liaison HTTP")
        statut = requete(tcp, "POST", "/envoi", json.dumps({"mode": "texte", "donnees": "Status 4", "finLigne": "aucune"}).encode())[0]
        verifie((statut, carte.commandes), (400, ["Status 5"]), "page : fin de ligne Aucune refusee, rien de garde en tampon")
        recu, limite = b"", time.time() + 5
        while b"CMD: Status 5" not in recu and time.time() < limite:
            try:
                recu += brut.recv(4096)
            except socket.timeout:
                break
        brut.close()
        verifie(b"CMD: Status 5" in recu, True, "client TCP brut : log de la carte recu par HTTP")
    finally:
        proc.terminate()
        proc.wait(5)
        carte.arrete()


def principal():
    cas_module()
    cas_pont()
    print()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
