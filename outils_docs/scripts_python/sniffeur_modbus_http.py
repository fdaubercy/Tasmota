"""Couche HTTP du sniffeur ModBus (sniffeur_modbus.py) : routes de la page http://127.0.0.1:7300.

    GET  /  /flux (Server-Sent Events)  /ports  /carte
    POST /port      {action: ouvrir|fermer, port, debit}
    POST /envoi     {hex, crc, repete, intervalle}
    POST /emulation {id, actif}  ou  {id, registre, champ, valeur}   (valeurs editables)
    POST /debit     {action: chercher|corriger}                      (carte 16 relais)
    POST /raz       POST /decode {hex, requete, crc}
Les POST exigent l'en-tete X-Sniffeur: 1 et la meme origine : une page tierce visant 127.0.0.1 ne
doit pas pouvoir commander des relais (l'en-tete impose un pre-vol CORS auquel ce serveur ne repond pas).
"""

import json
import queue
import threading
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit

import serial
from serial.tools import list_ports

import decodeur_modbus as dm
import sniffeur_modbus_web
import test_rs485_pc as rs

VID_PID_CH343 = (0x1A86, 0x55D3)


def lit_demande(demande, sniffeur, chemin):
    """Execute une demande POST (dict deja decode) ; rend un resultat JSON ou None ; ValueError si invalide."""
    if chemin == "/port":
        if demande.get("action") == "fermer":
            sniffeur.ferme()
            return None
        nom = str(demande.get("port", "")).strip()
        debit = int(demande.get("debit", sniffeur.debit))
        if not nom or not 300 <= debit <= 3000000:
            raise ValueError("port vide ou debit hors bornes (300..3000000)")
        sniffeur.ouvre(nom, debit)
    elif chemin == "/envoi":
        trame = rs.lit_hexa(str(demande.get("hex", "")))
        if demande.get("crc", True):
            trame = rs.avec_crc(trame)
        repete, intervalle = int(demande.get("repete", 1)), float(demande.get("intervalle", 0.5))
        if not 2 <= len(trame) <= 256 or not 1 <= repete <= 1000 or not 0.05 <= intervalle <= 60:
            raise ValueError("trame 2..256 octets, repete 1..1000, intervalle 0.05..60 s")
        if sniffeur.port is None:
            raise OSError("port serie ferme : l'ouvrir d'abord")
        threading.Thread(target=sniffeur.rafale, args=(trame, repete, intervalle), daemon=True).start()
    elif chemin == "/emulation":
        ident = int(demande.get("id", 0))
        if "actif" in demande:
            sniffeur.emulation.active(ident, bool(demande["actif"]))
        else:
            sniffeur.emulation.modifie(ident, int(demande.get("registre", -1)), str(demande.get("champ", "")),
                                       demande.get("valeur"))
        sniffeur.diffuse_emulation()
    elif chemin == "/debit":
        sniffeur.lance_debit(str(demande.get("action", "")))
    elif chemin == "/raz":
        sniffeur.raz()
    elif chemin == "/decode":
        # Decodage manuel (onglet Aide) : rien n'est emis. 'requete' donne le registre d'une reponse.
        trame = dm.lit_texte(str(demande.get("hex", "")))
        requete = dm.lit_texte(str(demande.get("requete", ""))) or None
        if demande.get("crc"):
            trame, requete = rs.avec_crc(trame), (rs.avec_crc(requete) if requete else None)
        if not 1 <= len(trame) <= 256:
            raise ValueError("trame vide ou trop longue")
        return dm.decode(trame, requete, sniffeur.carte, sniffeur.types)
    else:
        raise LookupError(chemin)
    return None


def fabrique_gestionnaire(sniffeur):
    class Gestionnaire(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def _envoie(self, statut, corps=b"", type_contenu="text/plain; charset=utf-8"):
            self.send_response(statut)
            self.send_header("Content-Type", type_contenu)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corps)

        def _json(self, donnees):
            self._envoie(200, json.dumps(donnees).encode("utf-8"), "application/json")

        def do_GET(self):
            chemin = urlsplit(self.path).path
            if chemin == "/":
                self._envoie(200, sniffeur_modbus_web.PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif chemin == "/carte":
                self._json({"persist": sniffeur.args.persist, "types": {str(k): v for k, v in sniffeur.types.items()},
                            "bus": sniffeur.bus,
                            "esclaves": [dict(e, appareils=[dict(a, registre=r) for r, a in sorted(e["appareils"].items())])
                                         for _, e in sorted(sniffeur.carte.items())]})
            elif chemin == "/ports":
                self._json([{"port": p.device, "description": p.description,
                             "ch343": (p.vid, p.pid) == VID_PID_CH343} for p in list_ports.comports()])
            elif chemin == "/flux":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                file = sniffeur.inscrit_web()
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
                    sniffeur.desinscrit_web(file)
            else:
                self._envoie(404, b"introuvable")

        def do_POST(self):
            origine = self.headers.get("Origin", "")
            if self.headers.get("X-Sniffeur") != "1" or (origine and origine not in (
                    f"http://127.0.0.1:{sniffeur.args.http}", f"http://localhost:{sniffeur.args.http}")):
                self._envoie(403, b"refuse")
                return
            try:
                longueur = min(int(self.headers.get("Content-Length", "0") or 0), 64 * 1024)
                demande = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
                if not isinstance(demande, dict):
                    raise ValueError("corps JSON attendu")
                resultat = lit_demande(demande, sniffeur, urlsplit(self.path).path)
            except LookupError:
                self._envoie(404, b"introuvable")
                return
            except (ValueError, TypeError) as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))
                return
            except (OSError, serial.SerialException) as erreur:
                self._envoie(409, str(erreur).encode("utf-8"))
                return
            if resultat is not None:
                self._json(resultat)
            else:
                self._envoie(200, b"ok")

    return Gestionnaire
