#!/usr/bin/env python3
"""Banc du serveur de l'atelier des visuels (atelier_visuels_web.py) : anti-CSRF, Host, 413, types, SVG malveillant,
relecture octet pour octet, eviction du 21e fond. Vrai gestionnaire sur 127.0.0.1, port libre, arrete en fin de banc.
Depot reel en lecture seule (liste des cartes) ; rien n'est ecrit. Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_atelier_visuels_web.py
"""
import base64
import http.client
import json
import shutil
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from http.server import ThreadingHTTPServer

import acces_web
import atelier_visuels_ecriture as ave
import atelier_visuels_ia as ia
import atelier_visuels_icones_web as ico
import atelier_visuels_web as avw
import atelier_visuels_web_routes as avr
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


PNG = b"\x89PNG" + b"\0" * 40
CLE = "sk-SECRET-1234567890"
SVG_IA = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 4"><rect width="4" height="4"/></svg>'


class Faux(ia.Fournisseur):
    def __init__(self, id_, externe):
        super().__init__({})
        self.id, self.nom, self.externe, self.appels = id_, "Faux " + id_, externe, 0

    def demande(self, consigne, chemin_image, delai=600):
        self.appels += 1
        return SVG_IA


def serveur_sur(racine, **inj):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    acces = acces_web.Acces(port, True, "Atelier des visuels")
    srv = ThreadingHTTPServer(("127.0.0.1", port), avw.fabrique_gestionnaire(acces, racine, **inj))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def jpost(port, chemin, objet, ent=ENT):
    return requete(port, "POST", chemin, json.dumps(objet).encode(), ent)


def routes_modules(racine, env):
    tmp = Path(tempfile.mkdtemp(prefix="test_visuels_web_"))
    vus, builds, faux = [], [], {"local": Faux("local", False), "ext": Faux("ext", True)}
    icones = {
        "search": json.dumps({"icons": ["mdi:home", "x:sale"], "collections": {"mdi": {"license": {"spdx": "Apache-2.0"}},
                                                                                "x": {"license": {"spdx": "CC-BY-NC-4.0"}}}}).encode(),
        "collections": json.dumps({"mdi": {"license": {"spdx": "Apache-2.0", "url": "u"}, "author": {"name": "A"}}}).encode(),
        "svg": b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M0 0h24v24z"/></svg>'}

    def ouvre(url, delai, maxi):
        vus.append(url)
        return icones["search" if "/search" in url else "collections" if "/collections" in url else "svg"]

    def lecteur(e, c):
        raise OSError("carte muette")

    cfg_fic = tmp / "config.json"
    srv, port = serveur_sur(racine, builds_en_cours=lambda: list(builds), ouvre=ouvre, cache_icones=tmp / "cache",
                            config_fichier=cfg_fic, fabrique_ia=lambda c, r: faux, lecteur=lecteur)
    try:
        st, corps = requete(port, "GET", "/icones/recherche?q=maison")
        verifie((st, [i["nom"] for i in json.loads(corps)["icones"]]), (200, ["home"]), "GET /icones/recherche : licence NC masquee")
        verifie(requete(port, "GET", "/icones/recherche?q=" + "a" * 41)[0], 400, "recherche trop longue : 400")
        verifie(requete(port, "GET", "/icones/svg?jeu=mdi&nom=../x")[0], 400, "nom d'icone avec ../ : 400")
        st, corps = requete(port, "GET", "/icones/svg?jeu=mdi&nom=home")
        verifie((st, json.loads(corps)["licence"]), (200, "Apache-2.0"), "GET /icones/svg : svg et licence")
        verifie(all(u.startswith(ico.BASE + "/") for u in vus) and bool(vus), True, "toutes les requetes d'icones vont a l'hote Iconify fixe")
        verifie(jpost(port, "/icones/garde", {"jeu": "mdi", "nom": "home"}, {})[0], 403, "POST /icones/garde sans en-tete : 403")
        verifie(jpost(port, "/icones/garde", {"jeu": "mdi", "nom": "../home"})[0], 400, "garde : nom invalide 400")
        verifie(requete(port, "POST", "/icones/garde", b"{pas json", ENT)[0], 400, "garde : JSON illisible 400")

        st, corps = requete(port, "GET", "/ia/fournisseurs")
        verifie((st, sorted(f["id"] for f in json.loads(corps)["fournisseurs"])), (200, ["ext", "local"]), "GET /ia/fournisseurs")
        corps_ia = {"env": env, "fournisseur": "ext", "consigne": "dessine", "photo": base64.b64encode(PNG).decode()}
        st, corps = jpost(port, "/ia/demande", corps_ia)
        verifie((st, "externe" in json.loads(corps).get("erreur", ""), faux["ext"].appels), (200, True, 0), "fournisseur externe sans confirmation : refus, aucun appel")
        st, corps = jpost(port, "/ia/demande", {**corps_ia, "confirme": True})
        verifie((st, "svg" in json.loads(corps), faux["ext"].appels), (200, True, 1), "fournisseur externe confirme : svg rendu")
        st, corps = jpost(port, "/ia/demande", {**corps_ia, "fournisseur": "local"})
        verifie((st, "svg" in json.loads(corps)), (200, True), "fournisseur local : sans confirmation")
        verifie(jpost(port, "/ia/demande", {**corps_ia, "photo": "***"})[0], 400, "photo en base64 invalide : 400")
        verifie(jpost(port, "/ia/demande", {**corps_ia, "fournisseur": "nul"})[0], 404, "fournisseur inconnu : 404")
        verifie(jpost(port, "/ia/demande", corps_ia, {})[0], 403, "POST /ia/demande sans en-tete : 403")
        gros = json.dumps({**corps_ia, "photo": "A" * avr.MAX_CORPS_IA}).encode()
        verifie(requete(port, "POST", "/ia/demande", gros, ENT)[0], 413, "/ia/demande au-dessus de 10 Mo : 413")
        gros1 = b'{"fournisseur":"ext","cle":"' + b"a" * (avw.MAX_CORPS + 1) + b'"}'
        verifie(requete(port, "POST", "/ia/cle", gros1, ENT)[0], 413, "/ia/cle au-dessus de 1 Mo : 413 (10 Mo pour /ia/demande seul)")
        st, corps = jpost(port, "/ia/cle", {"fournisseur": "ext", "cle": CLE})
        verifie((st, CLE.encode() in corps, json.loads(corps)["cle"]["presente"]), (200, False, True), "POST /ia/cle : cle jamais renvoyee")
        verifie(CLE in cfg_fic.read_text(encoding="utf-8"), True, "la cle est ecrite dans le fichier de config hors depot")
        for chemin in ("/ia/fournisseurs", "/ia/quota?fournisseur=ext"):
            verifie(CLE.encode() in requete(port, "GET", chemin)[1], False, f"GET {chemin} : cle absente")
        verifie(CLE.encode() in jpost(port, "/ia/demande", {**corps_ia, "confirme": True})[1], False, "reponse de /ia/demande : cle absente")
        verifie(jpost(port, "/ia/cle", {"fournisseur": "ext", "cle": "a b"})[0], 400, "cle avec espace : 400")
        st, corps = requete(port, "GET", "/ia/quota?fournisseur=ext")
        verifie((st, json.loads(corps)["envois_jour"]), (200, 2), "GET /ia/quota : 2 envois comptes")
        verifie(requete(port, "GET", "/ia/quota?fournisseur=nul")[0], 404, "quota d'un fournisseur inconnu : 404")

        desc = {"version": 1, "fond": {"type": "svg", "largeur": 10, "hauteur": 10}, "elements": []}
        st, corps = jpost(port, "/ecriture/prevoit", {"env": env, "description": desc})
        pret = all((racine / f).is_file() for f in ave.FICHIERS_PAGE)       # fichiers de la page : plan A3/A4
        verifie((st, "empreinte" in json.loads(corps)) if pret else st, (200, True) if pret else 400, "POST /ecriture/prevoit : diff et empreinte (400 motive tant que les fichiers de la page manquent)")
        emp = json.loads(corps).get("empreinte", "x") if pret else "x"
        verifie(jpost(port, "/ecriture/prevoit", {"env": "inconnue", "description": desc})[0], 404, "prevoit : carte inconnue 404")
        verifie(jpost(port, "/ecriture/prevoit", {"env": env, "description": desc, "empreinte_fond": "0" * 64})[0], 404, "prevoit : fond inconnu 404")
        builds.append("pio run -e x")
        st, corps = jpost(port, "/ecriture/ecrit", {"env": env, "description": desc, "empreinte": emp})
        verifie((st, b"build" in corps, b"Traceback" in corps), (409, True, False), "ecriture pendant un build : 409, aucune trace Python")
        verifie(jpost(port, "/ecriture/ecrit", {"env": env, "description": desc})[0], 400, "ecrit sans empreinte du diff : 400")

        st, corps = requete(port, "GET", f"/suivi?env={env}")
        verifie((st, json.loads(corps)["carte"] in ("inconnue", "absente")), (200, True), "GET /suivi : carte muette ou sans visuel.json, jamais d'echec")
        verifie(requete(port, "GET", "/suivi?env=nulle")[0], 404, "suivi d'une carte inconnue : 404")
    finally:
        srv.shutdown()
        srv.server_close()
    # garde reelle dans une racine temporaire : le vrai depot n'est jamais ecrit
    srv2, port2 = serveur_sur(tmp, ouvre=ouvre, cache_icones=tmp / "cache2", config_fichier=cfg_fic)
    try:
        st, corps = jpost(port2, "/icones/garde", {"jeu": "mdi", "nom": "home"})
        verifie((st, (tmp / "outils_docs/visuels_accueil/icones/mdi-home.svg").is_file()), (200, True), "POST /icones/garde : icone rangee")
        verifie(jpost(port2, "/icones/garde", {"jeu": "mdi", "nom": "home"})[0], 409, "garde d'une icone deja gardee : 409")
    finally:
        srv2.shutdown()
        srv2.server_close()
    shutil.rmtree(tmp, ignore_errors=True)


def suivi_muet():
    """Lecteur HTTP reel contre une carte qui accepte puis ne repond jamais : echec en moins de 3,5 s."""
    ecoute = socket.socket()
    ecoute.bind(("127.0.0.1", 0))
    ecoute.listen(5)
    lecteur = avr.lecteur_http(avw.DEPOT, adresse_de=lambda e: f"127.0.0.1:{ecoute.getsockname()[1]}")
    t0 = time.monotonic()
    try:
        lecteur("x", "/json/visuel.json")
        leve = False
    except OSError:
        leve = True
    duree = time.monotonic() - t0
    ecoute.close()
    verifie((leve, duree < 3.5), (True, True), f"carte muette : lecteur en echec en {duree:.1f} s (< 3,5 s)")


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
    routes_modules(racine, env)
    suivi_muet()
    print("VERT" if not ECHECS else f"ROUGE : {ECHECS}")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
