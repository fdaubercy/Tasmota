#!/usr/bin/env python3
"""Banc du serveur de l'atelier des visuels (atelier_visuels_web.py) : anti-CSRF, Host, 413, types, SVG malveillant,
relecture octet pour octet, eviction du 21e fond. Vrai gestionnaire sur 127.0.0.1, port libre, arrete en fin de banc.
Depot reel en lecture seule (liste des cartes) ; rien n'est ecrit. Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_atelier_visuels_web.py
"""
import http.client
import json
import socket
import sys
import threading
from http.server import ThreadingHTTPServer

import acces_web
import atelier_visuels_web as avw
import lieux
import tapp_envoi

ECHECS = []
ENT = {"X-Atelier-Visuels": "1"}
NS = "http://www.w3.org/2000/svg"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def requete(port, methode, chemin, corps=None, entetes=None, hote=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    c.putrequest(methode, chemin, skip_host=True)
    c.putheader("Host", hote or f"127.0.0.1:{port}")
    for k, v in (entetes or {}).items():
        c.putheader(k, v)
    c.putheader("Content-Length", str(len(corps or b"")))
    c.endheaders(corps or b"")
    r = c.getresponse()
    octets = r.read()
    c.close()
    return r.status, octets


def main():
    racine = avw.DEPOT
    envs = tapp_envoi.cartes(racine)
    env = envs[0]
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    acces = acces_web.Acces(port, True, "Atelier des visuels")
    serveur = ThreadingHTTPServer(("127.0.0.1", port), avw.fabrique_gestionnaire(acces, racine))
    serveur.daemon_threads = True
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    try:
        poste = lambda corps, type_="svg", e=env, ent=ENT: requete(port, "POST", f"/fond?env={e}&type={type_}", corps, ent)
        svg = f'<svg xmlns="{NS}" viewBox="0 0 10 10"><path d="M0 0L9 9" fill="#abc"/></svg>'.encode()

        st, corps = requete(port, "GET", "/envs")
        d = json.loads(corps)
        verifie((st, [e["env"] for e in d["envs"]] == envs, bool(d["lieux"]), d["envs"][0]["lieu"] == lieux.lieu(env)), (200, True, True, True), "GET /envs : cartes, lieux, lieu de chaque carte")
        st, corps = requete(port, "GET", "/")
        verifie((st, b"<title>Atelier des visuels</title>" in corps, corps.count(b"<main>"), b'id="av-canevas"' in corps, b'id="av-garder"' in corps), (200, True, 1, True, True), "GET / : la page (titre, corps a trois colonnes, canevas, bouton Garder)")
        verifie(corps.count(b"</div></main>") + corps.count(b"<div>"), corps.count(b"</div>") and corps.count(b"<div>") + corps.count(b"</div></main>"), "GET / : page rendue en entier")
        st, corps = requete(port, "GET", "/lib.js")
        verifie((st, b"ImageTracer" in corps), (200, True), "GET /lib.js : la bibliotheque de vectorisation")
        st, _ = requete(port, "GET", "/visuel.js")
        verifie(st, 404 if not (racine / avw.VISUEL_JS).is_file() else 200, "GET /visuel.js : 404 tant que le fichier n'existe pas")

        verifie(poste(svg, ent={})[0], 403, "POST /fond sans en-tete X-... : 403")
        verifie(poste(svg, ent={**ENT, "Origin": "http://evil.example"})[0], 403, "POST /fond d'une autre origine : 403")
        verifie(requete(port, "POST", f"/fond?env={env}&type=svg", svg, ENT, hote="evil.example")[0], 403, "hote non local : 403")
        verifie(requete(port, "GET", "/envs", hote="evil.example:80")[0], 403, "GET /envs avec un hote non local : 403")
        verifie(poste(b"x" * (avw.MAX_CORPS + 1), "webp")[0], 413, "corps de 1 Mo + 1 : 413")
        verifie(poste(b"RIFF0000WEBP" + b"x" * (avw.MAX_CORPS - 12), "webp")[0], 400, "corps de 1 Mo exactement : pas un 413, mais refuse au poids (seuil de la puce)")
        st, corps = poste(svg, "bmp")
        verifie((st, b"inconnu" in corps), (400, True), "type inconnu : 400 avec message")
        st, corps = poste(b"<svg xmlns='" + NS.encode() + b"'><script>alert(1)</script></svg>")
        verifie(st, 200, "SVG avec script : accepte mais nettoye")
        emp = json.loads(corps)["empreinte"]
        verifie(b"script" in requete(port, "GET", f"/fond?env={env}&empreinte={emp}")[1], False, "le fond garde ne contient plus le script")
        st, corps = poste(b"<!DOCTYPE svg [<!ENTITY a 'b'>]><svg xmlns='" + NS.encode() + b"'/>")
        verifie((st, b"DOCTYPE" in corps), (400, True), "SVG a DOCTYPE : 400 avec le message")
        verifie(poste(b"pas du svg")[0], 400, "texte qui n'est pas du SVG : 400")
        verifie(poste(b"pas une image", "jpg")[0], 400, "jpg sans signature : 400")
        verifie(poste(svg, e="carte-inconnue")[0], 404, "carte inconnue : 404")

        st, corps = poste(svg)
        r = json.loads(corps)
        st2, relu = requete(port, "GET", f"/fond?env={env}&empreinte={r['empreinte']}")
        verifie((st, st2, r["octets"] == len(relu), relu.decode().startswith("<svg")), (200, 200, True, True), "fond garde relu par GET /fond, meme poids")
        verifie(requete(port, "GET", f"/fond?env={env}&empreinte={'0' * 64}")[0], 404, "empreinte inconnue : 404")
        jpg = b"\xff\xd8\xff\xe0" + bytes(range(256)) * 4
        r = json.loads(poste(jpg, "jpg")[1])
        verifie(requete(port, "GET", f"/fond?env={env}&empreinte={r['empreinte']}")[1], jpg, "fond binaire relu octet pour octet")

        # eviction : 21 fonds distincts, le premier part
        premier = json.loads(poste(jpg + b"0", "jpg")[1])["empreinte"]
        autres = [json.loads(poste(jpg + str(i).encode(), "jpg")[1])["empreinte"] for i in range(1, avw.MAX_FONDS + 1)]
        verifie(requete(port, "GET", f"/fond?env={env}&empreinte={premier}")[0], 404, "21e fond : le plus ancien est evince")
        verifie(requete(port, "GET", f"/fond?env={env}&empreinte={autres[-1]}")[0], 200, "21e fond : le dernier est garde")
        puces = [e for e in envs if lieux.puce(e) == "ESP32"]
        if puces:
            verifie(poste(b"RIFF\0\0\0\0WEBP" + b"x" * 70 * 1024, "webp", puces[0])[0], 400, "70 Ko sur ESP32 : refus 400")
    finally:
        serveur.shutdown()
        serveur.server_close()
    print("VERT" if not ECHECS else f"ROUGE : {ECHECS}")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
