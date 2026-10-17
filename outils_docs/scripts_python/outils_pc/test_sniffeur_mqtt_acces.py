"""Banc de l'acces reseau du sniffeur MQTT (acces_web.py dans sniffeur_mqtt.py). Code de sortie 0 = vert.

Monte le VRAI gestionnaire HTTP du sniffeur (fabrique_gestionnaire) sur un port libre, SANS boucle
MQTT : aucune connexion a un broker, rien n'est publie. Configuration de test dans un dossier
temporaire (jamais %APPDATA%\\sniffeur_mqtt\\config.json) ; broker de test injoignable 127.0.0.1:1.
« Autre appareil » simule en appelant le serveur par l'IP reseau de ce PC (acces_web.ips_reseau()[0]).
Temoin : un controle qui laisse tout passer DOIT faire tomber les cas « refuse ».
"""

import argparse
import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acces_web                # noqa: E402
import sniffeur_mqtt            # noqa: E402
import sniffeur_mqtt_config     # noqa: E402

ECHECS = []
SECRET = "mdp-de-test-ne-doit-pas-sortir"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def requete(hote, port, methode="GET", chemin="/", entetes=None, corps=None):
    c = http.client.HTTPConnection(hote, port, timeout=5)
    donnees = json.dumps(corps).encode("utf-8") if corps is not None else (b"" if methode == "POST" else None)
    c.request(methode, chemin, body=donnees, headers=entetes or {})
    r = c.getresponse()
    if r.getheader("Content-Type", "").startswith("text/event-stream"):
        texte = r.read1(65536).decode("utf-8", "replace")      # flux sans fin : premier morceau seulement
    else:
        texte = r.read().decode("utf-8", "replace")
    c.close()
    return r.status, dict(r.getheaders()), texte


def monte(dossier):
    chemin = os.path.join(dossier, "config.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump({"brokers": [{"id": "b1", "nom": "test", "hote": "127.0.0.1", "port": 1, "tls": False,
                                "verifierCertificat": True, "utilisateur": "u", "motDePasse": SECRET}],
                   "actif": "b1", "abonnements": {}, "favoris": []}, f)
    configuration = sniffeur_mqtt_config.Configuration(
        {"nom": "Tasmota (test)", "hote": "127.0.0.1", "port": 1, "tls": False, "verifierCertificat": True,
         "utilisateur": "", "motDePasse": SECRET}, chemin)
    args = argparse.Namespace(abonnement=None, journal=None, historique=100, http=0, local=False)
    sniffeur = sniffeur_mqtt.Sniffeur(args, configuration)      # pas de boucle_mqtt : aucun broker contacte
    acces = acces_web.Acces(0, False, "Sniffeur MQTT (banc)")
    serveur = ThreadingHTTPServer((acces.hote, 0), sniffeur_mqtt.fabrique_gestionnaire(sniffeur, acces))
    serveur.daemon_threads = True
    port = serveur.server_address[1]
    acces.port, acces.cookie, args.http = port, f"jeton_{port}", port
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    return serveur, acces, port


def refus(ip, port, cookie_faux):
    """Cas qui doivent etre refuses depuis un autre appareil ; rend le nombre de 403 obtenus."""
    n = 0
    n += requete(ip, port)[0] == 403
    n += requete(ip, port, chemin="/flux")[0] == 403
    n += requete(ip, port, chemin="/brokers?jeton=faux")[0] == 403
    n += requete(ip, port, "POST", "/favoris", {"X-Sniffeur": "1", "Cookie": cookie_faux},
                 {"nom": "x", "filtre": "y"})[0] == 403
    return n


def principal():
    dossier = tempfile.mkdtemp(prefix="banc_sniffeur_mqtt_")
    serveur, acces, port = monte(dossier)
    favori = {"nom": "banc", "filtre": "tele/", "champ": "topic"}
    try:
        # -- ce PC : comme avant
        verifie(requete("127.0.0.1", port)[0], 200, "ce PC : page sans jeton")
        local = {"X-Sniffeur": "1", "Origin": f"http://127.0.0.1:{port}", "Content-Type": "application/json"}
        verifie(requete("127.0.0.1", port, "POST", "/favoris", local, favori)[0], 204, "ce PC : POST meme origine")
        verifie(requete("127.0.0.1", port, "POST", "/favoris", dict(local, **{"X-Sniffeur": "0"}), favori)[0], 403,
                "ce PC : POST sans X-Sniffeur refuse")
        verifie(requete("127.0.0.1", port, "POST", "/favoris",
                        dict(local, Origin=f"http://evil.example:{port}", Host=f"evil.example:{port}"), favori)[0],
                403, "ce PC : origine etrangere refusee meme si Host concorde (DNS rebinding)")

        # -- mots de passe : aucun GET ne doit les renvoyer
        sorties = "".join(requete("127.0.0.1", port, chemin=c)[2] for c in ("/brokers", "/etat", "/flux", "/"))
        verifie(SECRET in sorties, False, "GET /brokers, /etat, /flux, / : aucun mot de passe de broker")

        ips = acces_web.ips_reseau()
        if not ips:
            print("SAUTE  autre appareil : aucune adresse reseau sur ce PC")
        else:
            ip = ips[0]
            verifie(requete(ip, port)[0], 403, f"autre appareil ({ip}) : GET / sans jeton refuse")
            verifie(requete(ip, port, chemin="/flux")[0], 403, "autre appareil : flux SSE sans jeton refuse")
            verifie(requete(ip, port, chemin="/?jeton=faux")[0], 403, "autre appareil : mauvais jeton refuse")
            statut, entetes, _ = requete(ip, port, chemin=f"/?jeton={acces.jeton}")
            verifie(statut, 303, "autre appareil : ?jeton= valide -> 303")
            verifie(entetes.get("Location"), "/", "... vers / sans jeton")
            cookie = entetes.get("Set-Cookie", "")
            verifie(cookie.startswith(f"{acces.cookie}={acces.jeton};") and "HttpOnly" in cookie, True,
                    "... cookie HttpOnly pose")
            avec = {"Cookie": f"{acces.cookie}={acces.jeton}"}
            statut, _, page = requete(ip, port, entetes=avec)
            verifie((statut, "Sniffeur MQTT" in page), (200, True), "autre appareil : GET / avec cookie -> page")
            statut, entetes, texte = requete(ip, port, chemin="/flux", entetes=avec)
            verifie((statut, "event: etat" in texte), (200, True), "autre appareil : flux SSE avec cookie")
            reseau = dict(avec, **{"X-Sniffeur": "1", "Origin": f"http://{ip}:{port}",
                                   "Content-Type": "application/json"})
            verifie(requete(ip, port, "POST", "/favoris", reseau, favori)[0], 204,
                    "autre appareil : POST cookie + X-Sniffeur + Origin de l'hote vise accepte")
            verifie(requete(ip, port, "POST", "/favoris", dict(reseau, Origin="http://evil.example"), favori)[0],
                    403, "autre appareil : POST d'une origine etrangere refuse")
            verifie(requete(ip, port, "POST", "/favoris", dict(reseau, **{"X-Sniffeur": "0"}), favori)[0], 403,
                    "autre appareil : POST sans X-Sniffeur refuse")
            sorties = "".join(requete(ip, port, chemin=c, entetes=avec)[2] for c in ("/brokers", "/etat", "/flux"))
            verifie(SECRET in sorties, False, "autre appareil : aucun mot de passe de broker renvoye")
            cookie_faux = f"{acces.cookie}=faux"
            verifie(refus(ip, port, cookie_faux), 4, "les 4 cas de refus")

            # Temoin : un controle qui laisse tout passer doit faire tomber les refus.
            vrai = acces.controle
            acces.controle = lambda handler: True
            verifie(refus(ip, port, cookie_faux) < 4, True, "TEMOIN controle inactif : les refus tombent")
            acces.controle = vrai
    finally:
        serveur.shutdown()
        shutil.rmtree(dossier, ignore_errors=True)

    print()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
