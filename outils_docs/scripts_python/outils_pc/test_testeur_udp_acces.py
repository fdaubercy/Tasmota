"""Banc du testeur UDP, groupe « acces reseau » : jeton pour un autre appareil, ce PC inchange (acces_web.py).
Appele par test_testeur_udp.py, qui fournit verifie() et monte_testeur() (un seul decompte).

« Autre appareil » simule en appelant le serveur par l'IP reseau de ce PC : le client n'est alors plus
127.0.0.1. Sans adresse reseau (PC hors ligne), ces cas sont sautes et le banc le dit.
TEMOINS : un controle d'acces qui laisse tout passer, une origine toujours admise, DOIVENT faire tomber
les refus (tasks/lessons.md, regle 7).
"""

import http.client
import threading
from http.server import ThreadingHTTPServer

import acces_web
import testeur_udp_http


def requete(hote, port, methode="GET", chemin="/", entetes=None):
    """(statut, en-tetes, corps) ; les redirections ne sont PAS suivies."""
    c = http.client.HTTPConnection(hote, port, timeout=5)
    c.request(methode, chemin, body=b"{}" if methode == "POST" else None, headers=entetes or {})
    r = c.getresponse()
    if chemin.startswith("/flux") and r.status == 200:
        corps = r.readline()                        # premier evenement du flux SSE, puis on coupe
    else:
        corps = r.read()
    c.close()
    return r.status, dict(r.getheaders()), corps.decode("utf-8", "replace")


def groupe_acces(verifie, monte_testeur):
    t, _sims, _reseau, args = monte_testeur()
    acces = acces_web.Acces(0, False, "Testeur UDP")
    serveur = ThreadingHTTPServer((acces.hote, 0), testeur_udp_http.fabrique_gestionnaire(t, acces))
    serveur.daemon_threads = True
    port = args.http = acces.port = serveur.server_address[1]
    acces.cookie = f"jeton_{port}"
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    try:
        verifie(acces.hote, "0.0.0.0", "acces : ecoute sur tout le reseau par defaut")
        # -- ce PC : comme avant, sans jeton
        local = "127.0.0.1"
        statut, _, page = requete(local, port)
        verifie((statut, "Testeur UDP" in page), (200, True), "ce PC : page sans jeton")
        statut, _, debut = requete(local, port, chemin="/flux")
        verifie((statut, debut.startswith("data: ")), (200, True), "ce PC : /flux sans jeton")
        poste = {"X-Testeur": "1", "Content-Type": "application/json"}
        verifie(requete(local, port, "POST", "/raz", dict(poste, Origin=f"http://127.0.0.1:{port}"))[0], 200,
                "ce PC : POST de meme origine")
        verifie(requete(local, port, "POST", "/raz", dict(poste, Origin=f"http://evil.example:{port}",
                                                         Host=f"evil.example:{port}"))[0], 403,
                "ce PC : origine etrangere refusee meme si Host concorde (DNS rebinding)")
        verifie(requete(local, port, "POST", "/raz", {"Origin": f"http://127.0.0.1:{port}"})[0], 403,
                "ce PC : POST sans X-Testeur refuse")

        ips = acces_web.ips_reseau()
        if not ips:
            print("SAUTE  acces reseau, autre appareil : aucune adresse reseau sur ce PC")
            return
        ip = ips[0]
        meme = dict(poste, Origin=f"http://{ip}:{port}")

        def refus():
            """Les cas qui doivent etre refuses depuis un autre appareil ; rend le nombre de refus obtenus."""
            n = requete(ip, port)[0] == 403
            n += requete(ip, port, chemin="/flux")[0] == 403
            n += requete(ip, port, chemin="/etat?jeton=faux")[0] == 403
            n += requete(ip, port, "POST", "/raz", meme)[0] == 403
            n += requete(ip, port, "POST", "/raz", dict(poste, Cookie=f"{acces.cookie}={acces.jeton}",
                                                       Origin="http://evil.example"))[0] == 403
            return n

        verifie(requete(ip, port)[0], 403, f"autre appareil ({ip}) : page sans jeton refusee")
        verifie(requete(ip, port, chemin="/flux")[0], 403, "autre appareil : /flux sans jeton refuse")
        verifie(requete(ip, port, chemin="/?jeton=faux")[0], 403, "autre appareil : mauvais jeton refuse")
        statut, entetes, _ = requete(ip, port, chemin=f"/?jeton={acces.jeton}")
        cookie = entetes.get("Set-Cookie", "")
        verifie((statut, entetes.get("Location"), cookie.startswith(f"{acces.cookie}={acces.jeton};"),
                 "HttpOnly" in cookie), (303, "/", True, True), "autre appareil : ?jeton= -> 303 vers / + cookie")
        avec = {"Cookie": f"{acces.cookie}={acces.jeton}"}
        statut, _, page = requete(ip, port, entetes=avec)
        verifie((statut, "Testeur UDP" in page), (200, True), "autre appareil : page avec le cookie")
        statut, _, debut = requete(ip, port, chemin="/flux", entetes=avec)
        verifie((statut, debut.startswith("data: ")), (200, True), "autre appareil : /flux avec le cookie")
        verifie(requete(ip, port, chemin="/etat", entetes=avec)[0], 200, "autre appareil : GET /etat avec le cookie")
        verifie(requete(ip, port, "POST", "/raz", dict(meme, **avec))[0], 200,
                "autre appareil : POST cookie + X-Testeur + origine = hote vise, accepte")
        verifie(requete(ip, port, "POST", "/raz", dict(poste, Origin="http://evil.example", **avec))[0], 403,
                "autre appareil : POST d'une origine etrangere refuse")
        verifie(requete(ip, port, "POST", "/raz", dict(avec, Origin=f"http://{ip}:{port}"))[0], 403,
                "autre appareil : POST sans X-Testeur refuse")
        verifie(requete(ip, port, "POST", "/raz", meme)[0], 403, "autre appareil : POST sans jeton refuse")
        verifie(refus(), 5, "autre appareil : les 5 cas de refus")

        # TEMOINS : sans controle d'acces, ou avec une origine toujours admise, des refus DOIVENT tomber.
        controle, origine = acces.controle, acces.origine_autorisee
        acces.controle = lambda handler: True
        verifie(refus() < 5, True, "TEMOIN controle d'acces inactif : les refus tombent")
        acces.controle, acces.origine_autorisee = controle, (lambda handler: True)
        verifie(refus() < 5, True, "TEMOIN origine toujours admise : le refus de l'origine etrangere tombe")
        acces.origine_autorisee = origine
        verifie(refus(), 5, "controles remis : les 5 refus reviennent")
    finally:
        serveur.shutdown()
        serveur.server_close()
        t.arrete()
