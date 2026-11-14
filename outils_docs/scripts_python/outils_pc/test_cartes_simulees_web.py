"""Banc de cartes_simulees_web (routes, anti-CSRF, Host, carte en ligne refusee, lancement et arret reels). Code de sortie 0 = vert.

Serveur reel sur 127.0.0.1, port libre. La simulation du rideau est lancee pour de vrai (berry.exe requis) sur un port libre ;
la detection « en ligne » est remplacee par une fonction du banc (aucun reseau). Aucun build, rien n'est ecrit dans le depot.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_cartes_simulees_web.py
"""
import http.client
import json
import socket
import sys
import threading
from http.server import ThreadingHTTPServer

import acces_web
import cartes_simulees as cs
import cartes_simulees_web as web

ECHECS = []
RIDEAU = "tasmota32s3-garage-rideau-garage-modbus"
CUVE = "tasmota32s3-garage-capteurs-cuve-modbus"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


EN_LIGNE = {CUVE}            # la cuve « repond » ; le rideau non
cible = port_libre()          # port de la simulation du rideau (au lieu de 8082, que le banc ne doit pas occuper)
etat = web.Etat(test_en_ligne=lambda adresse: any(cs.inventaire()[e]["adresse"] == adresse for e in EN_LIGNE),
                fabrique=lambda env, port: cs.serveur(env, cible))
port = port_libre()
acces = acces_web.Acces(port, True, "Cartes simulees")
srv = ThreadingHTTPServer(("127.0.0.1", port), web.fabrique_gestionnaire(acces, etat))
srv.daemon_threads = True
threading.Thread(target=srv.serve_forever, daemon=True).start()


def req(methode, chemin, corps=None, entetes=None, brut=None):
    h = {"Content-Type": "application/json"}
    if methode == "POST":
        h[web.ENTETE] = "1"
    h.update(entetes or {})
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=40)
    c.request(methode, chemin, body=brut if brut is not None else (json.dumps(corps).encode() if corps is not None else None), headers=h)
    r = c.getresponse()
    t = r.read().decode("utf-8", "replace")
    c.close()
    return r.status, t


def simule(chemin):
    c = http.client.HTTPConnection("127.0.0.1", cible, timeout=40)
    c.request("GET", chemin)
    r = c.getresponse()
    t = r.read().decode("utf-8", "replace")
    c.close()
    return r.status, t


try:
    st, t = req("GET", "/")
    verifie([st, "Cartes simulées" in t and "textContent" in t and "innerHTML" not in t], [200, True], "GET / : la page (textContent, jamais innerHTML)")
    cartes = json.loads(req("GET", "/etat")[1])["cartes"]
    verifie(len(cartes) >= 13 and any(c["env"] == RIDEAU and c["berry"] and not c["lancee"] for c in cartes), True, "GET /etat : 13 cartes, rideau non lance")
    verifie(req("GET", "/inconnu")[0], 404, "route inconnue")
    verifie(req("POST", "/lance", {"env": RIDEAU}, {web.ENTETE: "0"})[0], 403, "POST sans l'en-tete X-Cartes-Simulees")
    verifie(req("POST", "/lance", {"env": RIDEAU}, {"Origin": "http://evil.example"})[0], 403, "POST d'une autre origine")
    verifie(req("GET", "/etat", None, {"Host": "evil.example"})[0], 403, "Host etranger (DNS rebinding)")
    verifie(req("POST", "/lance", brut=b"[1]")[0], 400, "corps JSON pas un objet")
    verifie(req("POST", "/lance", {"env": "../x"})[0], 404, "carte inconnue refusee")
    st, t = req("POST", "/lance", {"env": CUVE})
    verifie([st, "ne se simule pas" in t], [409, True], "carte EN LIGNE : refus 409, rien n'est lance")
    verifie(req("POST", "/arrete", {"env": RIDEAU})[0], 409, "arreter une carte non lancee : 409")

    st, t = req("POST", "/lance", {"env": RIDEAU})
    verifie([st, json.loads(t).get("url", "").startswith("http://127.0.0.1:")], [200, True], "rideau hors ligne : lance")
    verifie(req("POST", "/lance", {"env": RIDEAU})[0], 409, "deja lance : 409")
    verifie([c["lancee"] for c in json.loads(req("GET", "/etat")[1])["cartes"] if c["env"] == RIDEAU], [True], "/etat : rideau lance")
    st, corps = simule("/")
    verifie([st, "RIDEAU-GARAGE" in corps, "chevrefeuille" in corps], [200, True, True], "la carte lancee sert son accueil (nom d'hote, decor)")
    st, corps = simule("/cm?cmnd=Status%205")
    verifie(json.loads(corps)["StatusNET"]["Hostname"], "RIDEAU-GARAGE", "la carte lancee annonce le nom d'hote du persist")

    verifie(req("POST", "/arrete", {"env": RIDEAU})[0], 200, "arret")
    try:
        simule("/")
        ferme = False
    except OSError:
        ferme = True
    verifie(ferme, True, "apres l'arret, le port de la carte ne repond plus")
    verifie([c["lancee"] for c in json.loads(req("GET", "/etat")[1])["cartes"] if c["env"] == RIDEAU], [False], "/etat : rideau arrete")
    EN_LIGNE.add(RIDEAU)
    verifie(req("POST", "/lance", {"env": RIDEAU})[0], 409, "temoin : meme carte, si elle repond, est refusee")
finally:
    etat.arrete_tout()
    srv.shutdown()
    srv.server_close()
print("\n" + ("VERT" if not ECHECS else "ROUGE : " + "; ".join(ECHECS)))
sys.exit(1 if ECHECS else 0)
