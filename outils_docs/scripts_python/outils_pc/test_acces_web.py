"""Banc de acces_web.py (acces des outils PC depuis le reseau). Code de sortie 0 = vert.

« Autre appareil » simule en appelant le serveur par l'IP reseau de ce PC : le client n'est alors
plus 127.0.0.1. Sans adresse reseau (PC hors ligne), ces cas sont sautes et le banc le dit.
Temoin : un Acces dont controle() laisse tout passer DOIT faire echouer les cas « refuse ».
"""

import http.client
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import acces_web

ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def serveur(acces):
    class Gestionnaire(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"           # comme les outils : connexions maintenues

        def log_message(self, *a):
            pass

        def _rep(self, statut, corps=b"ok"):
            self.send_response(statut)
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

        def do_GET(self):
            if acces.controle(self):
                self._rep(200)

        def do_POST(self):
            if not acces.controle(self):
                return
            self._rep(200 if acces.origine_autorisee(self) else 403)

    srv = ThreadingHTTPServer(("0.0.0.0", 0), Gestionnaire)
    acces.port = srv.server_address[1]
    acces.cookie = f"jeton_{acces.port}"
    Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def requete(hote, port, methode="GET", chemin="/", entetes=None):
    c = http.client.HTTPConnection(hote, port, timeout=5)
    c.request(methode, chemin, body=b"" if methode == "POST" else None, headers=entetes or {})
    r = c.getresponse()
    r.read()
    c.close()
    return r.status, dict(r.getheaders())


def cas_refus(acces, ip, port):
    """Les cas qui doivent etre refuses ; rend le nombre de refus obtenus."""
    refus = 0
    refus += requete(ip, port)[0] == 403
    refus += requete(ip, port, chemin="/?jeton=faux")[0] == 403
    refus += requete(ip, port, "POST", "/x")[0] == 403
    refus += requete(ip, port, entetes={"Cookie": f"{acces.cookie}=faux"})[0] == 403
    return refus


def keep_alive_apres_refus(ip, port):
    """POST refuse avec un corps « GET /pirate ... », puis une 2e requete sur la meme connexion.
    Attendu : connexion fermee. Sinon le corps non lu serait servi comme requete suivante."""
    import socket
    corps = b"GET /pirate HTTP/1.1\r\nHost: x\r\n\r\n"
    with socket.create_connection((ip, port), timeout=5) as s:
        s.sendall(b"POST /x HTTP/1.1\r\nHost: x\r\nContent-Length: %d\r\n\r\n" % len(corps) + corps)
        recu = b""
        try:
            while True:
                morceau = s.recv(4096)
                if not morceau:
                    break
                recu += morceau
        except socket.timeout:
            return "ouverte"
    return "fermee" if recu.count(b"HTTP/1.") == 1 else "resservie"


def principal():
    acces = acces_web.Acces(0, False, "banc")
    srv = serveur(acces)
    port = acces.port
    ips = acces_web.ips_reseau()

    verifie(acces.hote, "0.0.0.0", "par defaut : ecoute sur tout le reseau")
    verifie(acces_web.Acces(7100, True).hote, "127.0.0.1", "--local : 127.0.0.1 seulement")
    verifie(acces_web.Acces(7100, True).liens_reseau(), [], "--local : aucun lien reseau")
    verifie(acces_web.est_local(("::ffff:127.0.0.1", 1)), True, "IPv4 projetee en IPv6 = ce PC")
    verifie(acces_web.est_local(("192.168.0.3", 1)), False, "IP du reseau = autre appareil")

    # -- ce PC : comme avant
    verifie(requete("127.0.0.1", port)[0], 200, "ce PC : page sans jeton")
    verifie(requete("127.0.0.1", port, "POST", "/x", {"Origin": f"http://127.0.0.1:{port}"})[0], 200,
            "ce PC : POST de meme origine")
    verifie(requete("127.0.0.1", port, "POST", "/x", {"Origin": f"http://evil.example:{port}",
                                                      "Host": f"evil.example:{port}"})[0], 403,
            "ce PC : origine etrangere refusee meme si Host concorde (DNS rebinding)")

    if not ips:
        print("SAUTE  autre appareil : aucune adresse reseau sur ce PC")
    else:
        ip = ips[0]
        verifie(requete(ip, port)[0], 403, f"autre appareil ({ip}) : page sans jeton refusee")
        verifie(requete(ip, port, chemin="/?jeton=faux")[0], 403, "autre appareil : mauvais jeton refuse")
        statut, entetes = requete(ip, port, chemin=f"/?a=1&jeton={acces.jeton}")
        verifie(statut, 303, "autre appareil : bon jeton -> redirection")
        verifie(entetes.get("Location"), "/?a=1", "... vers l'adresse sans jeton, autres parametres gardes")
        cookie = entetes.get("Set-Cookie", "")
        verifie(cookie.startswith(f"{acces.cookie}={acces.jeton};") and "HttpOnly" in cookie
                and "SameSite=Strict" in cookie, True, "... jeton pose en cookie HttpOnly SameSite=Strict")
        avec = {"Cookie": f"autre=1; {acces.cookie}={acces.jeton}"}
        verifie(requete(ip, port, entetes=avec)[0], 200, "autre appareil : page avec le cookie")
        verifie(requete(ip, port, "POST", "/x", dict(avec, Origin=f"http://{ip}:{port}"))[0], 200,
                "autre appareil : POST avec cookie, origine = hote vise")
        verifie(requete(ip, port, "POST", "/x", dict(avec, Origin="http://evil.example"))[0], 403,
                "autre appareil : POST d'une origine etrangere refuse")
        verifie(requete(ip, port, "POST", "/x")[0], 403, "autre appareil : POST sans jeton refuse")
        verifie(requete(ip, port, entetes={"Cookie": "jeton_1=" + acces.jeton})[0], 403,
                "autre appareil : cookie d'un autre outil (autre port) ignore")
        verifie(cas_refus(acces, ip, port), 4, "les 4 cas de refus")
        verifie(keep_alive_apres_refus(ip, port), "fermee", "HTTP/1.1 : POST refuse (corps non lu) -> connexion fermee")

        # Temoin : un controle qui laisse tout passer doit faire tomber les cas de refus.
        acces.controle = lambda handler: True
        verifie(cas_refus(acces, ip, port) < 4, True, "TEMOIN controle inactif : les refus tombent")
    srv.shutdown()

    print()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
