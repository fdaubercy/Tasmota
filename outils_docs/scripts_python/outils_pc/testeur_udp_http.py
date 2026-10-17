"""Couche HTTP du testeur UDP (testeur_udp.py) : routes de la page (http://127.0.0.1:7400 sur ce PC).

    GET  /          page (testeur_udp_web.PAGE)
    GET  /flux      Server-Sent Events : etat, lignes des cartes, notes, verdicts (historique rejoue)
    GET  /etat      etat des deux cartes, mode de l'esclave, IP, logs poses
    GET  /ports     ports serie presents
    GET  /essais    historique des verdicts
    POST /port      {carte: maitre|esclave, action: ouvrir|fermer, port, vitesse}
    POST /test      {type, sens, mode, texte, delai, ip_maitre, ip_esclave, adresse, tid, avec_tid}  (bloque
                    pendant la fenetre d'attente, rend le verdict en JSON)
    POST /mode      {mode: RangeExtender|WifiClassique, confirme: true}   (bascule de l'esclave)
    POST /relire    {carte}     Status 5, ReglageLog et mode de connexion de nouveau
    POST /restaure  rend aux cartes les niveaux de log d'origine
    POST /cmd       {carte, commande}   commande libre (une ligne)
    POST /raz       vide l'historique des verdicts
Acces (acces_web.py) : ce PC sans jeton ; un autre appareil du reseau doit avoir le jeton, controle en tete de
chaque GET et POST (/flux compris). Les POST exigent en plus l'en-tete X-Testeur: 1 et la meme origine
(127.0.0.1 / localhost ; depuis un autre appareil, l'hote qu'il a vise) : une page tierce ne doit pas pouvoir
commander les cartes (l'en-tete impose un pre-vol CORS auquel ce serveur ne repond pas).
"""

import json
import queue
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit

import serial
from serial.tools import list_ports

import testeur_udp_carte
import testeur_udp_web


def liste_ports():
    """Ponts serie d'abord (le port COM reste au pont, sa page reste utilisable), puis les ports COM."""
    ports = sorted(list_ports.comports(), key=lambda p: (p.vid is None, p.device))
    return testeur_udp_carte.liste_ponts() + [{"port": p.device, "description": p.description, "usb": p.vid is not None}
                                              for p in ports]


def traite_post(demande, testeur, chemin):
    """Execute une demande POST (dict). Rend un resultat JSON ou None ; LookupError, ValueError, OSError."""
    if chemin == "/port":
        role = str(demande.get("carte", ""))
        if role not in testeur.cartes:
            raise ValueError(f"carte inconnue : {role!r}")
        carte = testeur.cartes[role]
        if demande.get("action") == "fermer":
            if carte.ouvert:
                testeur.restaure_logs(role)
            carte.ferme()
            testeur.note(role, "port ferme")
            testeur.pousse_etat()
            return {"ok": True, "message": "port ferme"}
        nom, vitesse = str(demande.get("port", "")).strip(), int(demande.get("vitesse", 115200))
        if not nom or len(nom) > 200 or not 300 <= vitesse <= 3000000:
            raise ValueError("port vide ou vitesse hors bornes (300..3000000)")
        ok, message = carte.ouvre(nom, vitesse)
        if not ok:
            testeur.note(role, "AVERTISSEMENT : " + message)
        testeur.pousse_etat()
        return {"ok": ok, "message": message}
    if chemin == "/test":
        return testeur.lance_essai(demande)
    if chemin == "/mode":
        if demande.get("confirme") is not True:
            raise ValueError("bascule non confirmee")
        testeur.bascule_mode(str(demande.get("mode", "")))
        return {"ok": True}
    if chemin == "/relire":
        testeur.relire(str(demande.get("carte", "")))
    elif chemin == "/restaure":
        return {"commandes": testeur.restaure_logs()}
    elif chemin == "/cmd":
        commande = str(demande.get("commande", "")).strip()
        if not commande or len(commande) > 300:
            raise ValueError("commande vide ou trop longue")
        testeur.envoie_commande(str(demande.get("carte", "")), commande)
    elif chemin == "/raz":
        testeur.essais.clear()
    elif chemin == "/grille":
        action = demande.get("action")
        if action == "lancer":
            testeur.grille.lance(int(demande.get("test", 0)), demande.get("duree"))
        elif action == "repondre":
            testeur.grille.repond(str(demande.get("reponse", "")))
        elif action == "arreter":
            testeur.grille.arrete()
        else:
            raise ValueError(f"action inconnue : {action!r}")
        return testeur.grille.etat()
    else:
        raise LookupError(chemin)
    return {"ok": True}


def fabrique_gestionnaire(testeur, acces):
    """acces : acces_web.Acces (jeton des autres appareils, origines admises des POST)."""
    class Gestionnaire(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def handle(self):
            try:
                super().handle()
            except OSError:          # navigateur ferme en cours de requete : rien a signaler
                pass

        def _envoie(self, statut, corps=b"", type_contenu="text/plain; charset=utf-8"):
            self.send_response(statut)
            self.send_header("Content-Type", type_contenu)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corps)

        def _json(self, donnees, statut=200):
            self._envoie(statut, json.dumps(donnees, ensure_ascii=False).encode("utf-8"), "application/json")

        def do_GET(self):
            if not acces.controle(self):          # autre appareil sans jeton : 403 (ou 303 + cookie)
                return
            chemin = urlsplit(self.path).path
            if chemin == "/":
                self._envoie(200, testeur_udp_web.PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif chemin == "/etat":
                self._json(testeur.etat())
            elif chemin == "/ports":
                self._json(liste_ports())
            elif chemin == "/essais":
                self._json(testeur.essais)
            elif chemin == "/grille":
                self._json(testeur.grille.etat())
            elif chemin == "/flux":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                file = testeur.inscrit_web()
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
                    testeur.desinscrit_web(file)
            else:
                self._envoie(404, b"introuvable")

        def do_POST(self):
            if not acces.controle(self):
                self.close_connection = True      # corps non lu : la connexion ne doit pas resservir
                return
            if self.headers.get("X-Testeur") != "1" or not acces.origine_autorisee(self):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return
            try:
                longueur = min(int(self.headers.get("Content-Length", "0") or 0), 64 * 1024)
                demande = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
                if not isinstance(demande, dict):
                    raise ValueError("corps JSON attendu")
                resultat = traite_post(demande, testeur, urlsplit(self.path).path)
            except LookupError:
                self._envoie(404, b"introuvable")
                return
            except (ValueError, TypeError) as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))
                return
            except (OSError, serial.SerialException) as erreur:
                self._envoie(409, str(erreur).encode("utf-8"))
                return
            self._json(resultat if resultat is not None else {"ok": True})

    return Gestionnaire
