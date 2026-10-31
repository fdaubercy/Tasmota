"""Couche HTTP du sniffeur I2C (sniffeur_i2c.py) : routes de la page (port 7350 par defaut).

    GET  /  /flux (Server-Sent Events)  /ports  /cartes  /puces  /export?format=txt|json
    POST /port   {action: ouvrir|fermer, port}
    POST /carte  {carte: "data/<lieu>/<carte>" | ""}           carte observee (puces, IP proposee)
    POST /ordre  {voie: "carte", ip, a, reg, n, valeur|null, confirme}
                 {voie: "maitre", nom: MW|MR|MWR, a, d (hexa), n, isole, confirme}
    POST /raz
{apercu: true} en plus : rend {commande} SANS RIEN ENVOYER (la page la montre avant l'envoi).
Une ecriture (valeur, MW, MWR) exige confirme = true ; la voie maitre exige isole = true (composant
debranche de sa carte). Acces (acces_web.py) : ce PC sans jeton, autre appareil avec jeton ; les POST
exigent l'en-tete X-Sniffeur: 1 et la meme origine, comme le sniffeur ModBus.
"""

import json
import queue
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlsplit

import serial
from serial.tools import list_ports

import acces_web
import decodeur_i2c as di
import sniffeur_i2c_web
import sniffeur_i2c_carte as carte_i2c
import sniffeur_i2c_protocole as proto
from decodeur_i2c_puces import PUCES


def _entier(demande, cle, base=10):
    valeur = demande.get(cle)
    return int(valeur, base) if isinstance(valeur, str) else int(valeur)


def lit_ordre(demande, sniffeur):
    if demande.get("voie") == "carte":
        valeur = demande.get("valeur")
        valeur = None if valeur in (None, "") else _entier(demande, "valeur", 16)
        a, reg, n = _entier(demande, "a", 16), _entier(demande, "reg", 16), _entier(demande, "n")
        if demande.get("apercu") is True:
            return {"commande": carte_i2c.commande_br(a, reg, n, valeur)}
        if valeur is not None and demande.get("confirme") is not True:
            raise ValueError("ecriture non confirmee : rien n'a ete envoye")
        return sniffeur.ordre_carte(carte_i2c.verifie_ip(demande.get("ip", "")), a, reg, n, valeur)
    if demande.get("voie") == "maitre":
        nom = str(demande.get("nom", ""))
        if demande.get("isole") is not True:
            raise ValueError("cocher « composant debranche de sa carte » : rien n'a ete envoye")
        ecriture = nom in ("MW", "MWR")
        d = bytes.fromhex(str(demande.get("d", "")).replace(" ", "")) if ecriture else b""
        n = _entier(demande, "n") if nom in ("MR", "MWR") else 0
        a = _entier(demande, "a", 16)
        if demande.get("apercu") is True:
            return {"commande": proto.ordre(nom, a, d, n).decode("ascii").strip()}
        if ecriture and demande.get("confirme") is not True:
            raise ValueError("ecriture non confirmee : rien n'a ete envoye")
        return sniffeur.ordre_maitre(nom, a, d, n)
    raise ValueError("voie : carte ou maitre")


def lit_demande(demande, sniffeur, chemin):
    """Execute une demande POST (dict deja decode) ; rend un resultat JSON ou None ; ValueError si invalide."""
    if chemin == "/port":
        if demande.get("action") == "fermer":
            sniffeur.ferme()
            return None
        nom = str(demande.get("port", "")).strip()
        if not nom:
            raise ValueError("port vide")
        sniffeur.ouvre(nom)
    elif chemin == "/carte":
        return sniffeur.choisit_carte(str(demande.get("carte", "")))
    elif chemin == "/ordre":
        return lit_ordre(demande, sniffeur)
    elif chemin == "/raz":
        sniffeur.raz()
    else:
        raise LookupError(chemin)
    return None


def fabrique_gestionnaire(sniffeur, acces=None):
    """acces : acces_web.Acces du serveur ; absent, ce PC seulement (tout autre client refuse sans jeton)."""
    acces = acces or acces_web.Acces(sniffeur.args.http, local=True, nom="sniffeur I2C")

    class Gestionnaire(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def _envoie(self, statut, corps=b"", type_contenu="text/plain; charset=utf-8", entetes=()):
            self.send_response(statut)
            self.send_header("Content-Type", type_contenu)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            for cle, valeur in entetes:
                self.send_header(cle, valeur)
            self.end_headers()
            self.wfile.write(corps)

        def _json(self, donnees):
            self._envoie(200, json.dumps(donnees).encode("utf-8"), "application/json")

        def do_GET(self):
            if not acces.controle(self):
                return
            url = urlsplit(self.path)
            if url.path == "/":
                self._envoie(200, sniffeur_i2c_web.PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif url.path == "/ports":
                self._json([{"port": p.device, "description": p.description, "sniffeur": p.vid in proto.VIDS_SNIFFEUR}
                            for p in list_ports.comports()])
            elif url.path == "/cartes":
                self._json(di.liste_cartes(sniffeur.racine))
            elif url.path == "/puces":
                self._json({p: {"nom": f["nom"], "adresses": list(f["adresses"]), "taille": f["taille"],
                                "registres": {f"{r:02X}": nom for r, nom in sorted(f["registres"].items())}}
                            for p, f in PUCES.items()})
            elif url.path == "/export":
                format_ = (parse_qs(url.query).get("format") or ["txt"])[0]
                texte, type_contenu = sniffeur.export("json" if format_ == "json" else "txt")
                nom = f"sniffeur_i2c.{'json' if format_ == 'json' else 'txt'}"
                self._envoie(200, texte.encode("utf-8"), type_contenu,
                             [("Content-Disposition", f'attachment; filename="{nom}"')])
            elif url.path == "/flux":
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
                    self.close_connection = True
                    sniffeur.desinscrit_web(file)
            else:
                self._envoie(404, b"introuvable")

        def do_POST(self):
            if not acces.controle(self):
                self.close_connection = True        # corps non lu : la connexion ne peut pas resservir
                return
            if self.headers.get("X-Sniffeur") != "1" or not acces.origine_autorisee(self):
                self.close_connection = True
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
