"""Groupe « acces reseau » du banc du sniffeur ModBus, lance par test_sniffeur_modbus.py.

A part pour la regle des 500 lignes. Vrai gestionnaire HTTP du sniffeur (sniffeur_modbus_http) et vrai
acces_web.Acces, sur un port libre (jamais 7300) ; port serie loop:// (aucun vrai port COM ouvert).
« Autre appareil » = appel par l'IP reseau de ce PC : le client n'est plus 127.0.0.1. Sans IP reseau,
ces cas sont sautes et le banc le dit.
Chaque POST /envoi accepte emet une trame sur loop:// : le compteur sn.nb prouve qu'un refus n'a RIEN emis.
TEMOIN : acces.controle neutralise -> les refus « sans jeton » tombent et la trame part.
"""

import http.client
import json
import socket
import threading
import time
from http.server import ThreadingHTTPServer

import acces_web
from sniffeur_modbus_http import fabrique_gestionnaire

ENVOI = json.dumps({"hex": "01 06 00 01 01 00", "crc": True})     # canal 1 Open, sur loop:// seulement


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def requete(hote, port, methode="GET", chemin="/", entetes=None):
    """-> (statut, en-tetes, debut du corps). /flux : en-tetes seulement (le flux ne finit pas)."""
    c = http.client.HTTPConnection(hote, port, timeout=5)
    corps = ENVOI.encode() if methode == "POST" else None
    c.request(methode, chemin, body=corps, headers=dict({"Content-Type": "application/json"}, **(entetes or {})))
    r = c.getresponse()
    debut = b"" if chemin == "/flux" and r.status == 200 else r.read()[:4000]
    c.close()
    return r.status, dict(r.getheaders()), debut


def emis(sn, avant, attente):
    """Nombre de trames apparues depuis 'avant' (la rafale part dans un fil)."""
    fin = time.monotonic() + attente
    while time.monotonic() < fin and sn.nb == avant:
        time.sleep(0.02)
    time.sleep(0.05)
    return sn.nb - avant


def poste(sn, hote, port, entetes, attente=0.3):
    avant = sn.nb
    statut = requete(hote, port, "POST", "/envoi", entetes)[0]
    return statut, emis(sn, avant, 1.0 if statut == 200 else attente)


def groupe(verifie, sn):
    port = port_libre()
    sn.args.http = port
    acces = acces_web.Acces(port, False, "banc sniffeur")
    srv = ThreadingHTTPServer((acces.hote, port), fabrique_gestionnaire(sn, acces))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        sn.ouvre("loop://", 19200)
        x, local = {"X-Sniffeur": "1"}, f"http://127.0.0.1:{port}"
        # -- ce PC : inchange
        verifie(requete("127.0.0.1", port)[0], 200, "acces : ce PC, page sans jeton")
        verifie(poste(sn, "127.0.0.1", port, dict(x, Origin=local)), (200, 1), "acces : ce PC, POST /envoi emis")
        verifie(poste(sn, "127.0.0.1", port, {"Origin": local}), (403, 0), "acces : ce PC, POST sans X-Sniffeur refuse")
        verifie(poste(sn, "127.0.0.1", port, dict(x, Origin="http://evil.example")), (403, 0),
                "acces : ce PC, origine etrangere refusee")
        ips = acces_web.ips_reseau()
        if not ips:
            print("  SAUTE  acces reseau : aucune adresse reseau sur ce PC")
            return
        ip = ips[0]
        reseau = f"http://{ip}:{port}"
        verifie(poste(sn, "127.0.0.1", port, dict(x, Origin=reseau)), (403, 0),
                "acces : ce PC, origine = IP reseau refusee (127.0.0.1 / localhost seulement)")
        # -- autre appareil
        verifie(requete(ip, port)[0], 403, "acces : reseau, page sans jeton refusee")
        verifie(requete(ip, port, chemin="/flux")[0], 403, "acces : reseau, /flux sans jeton refuse")
        verifie(requete(ip, port, chemin="/?jeton=faux")[0], 403, "acces : reseau, mauvais jeton refuse")
        statut, entetes, _ = requete(ip, port, chemin=f"/?jeton={acces.jeton}")
        cookie = entetes.get("Set-Cookie", "")
        verifie((statut, entetes.get("Location")), (303, "/"), "acces : reseau, bon jeton -> 303 vers /")
        verifie(cookie.startswith(f"jeton_{port}={acces.jeton};") and "HttpOnly" in cookie, True,
                "acces : reseau, jeton pose en cookie HttpOnly")
        avec = {"Cookie": f"jeton_{port}={acces.jeton}"}
        statut, _, corps = requete(ip, port, entetes=avec)
        verifie((statut, b"Sniffeur ModBus" in corps), (200, True), "acces : reseau, page avec le cookie")
        statut, entetes, _ = requete(ip, port, chemin="/flux", entetes=avec)
        verifie((statut, entetes.get("Content-Type")), (200, "text/event-stream"), "acces : reseau, /flux avec le cookie")
        verifie(poste(sn, ip, port, dict(avec, Origin=reseau, **x)), (200, 1), "acces : reseau, POST cookie + meme origine emis")
        verifie(poste(sn, ip, port, dict(avec, Origin="http://evil.example", **x)), (403, 0),
                "acces : reseau, POST d'une origine etrangere refuse")
        verifie(poste(sn, ip, port, dict(avec, Origin=reseau)), (403, 0), "acces : reseau, POST sans X-Sniffeur refuse")
        verifie(poste(sn, ip, port, dict(x, Origin=reseau)), (403, 0), "acces : reseau, POST sans jeton refuse")
        # -- TEMOIN : sans acces.controle, les refus « sans jeton » doivent tomber
        acces.controle = lambda handler: True
        verifie((requete(ip, port)[0], poste(sn, ip, port, dict(x, Origin=reseau))), (200, (200, 1)),
                "TEMOIN : controle neutralise -> page et POST sans jeton passent")
        del acces.controle
        verifie(poste(sn, ip, port, dict(x, Origin=reseau)), (403, 0), "acces : controle retabli, refus revenu")
    finally:
        srv.shutdown()
        srv.server_close()
        sn.ferme()
