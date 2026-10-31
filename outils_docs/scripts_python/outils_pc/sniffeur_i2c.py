r"""Sniffeur I2C avec page web locale, par un ESP32-S3 DEDIE (firmware outils_docs/firmware_sniffeur_i2c).

Materiel : un ESP32-S3 DevKit qui n'est PAS une carte du parc, port USB natif vers ce PC ; trois fils vers le
bus observe : SDA -> GPIO4, SCL -> GPIO5, GND -> GND. Bus en 3,3 V SEULEMENT, aucun tirage cote sniffeur.
Conception : docs/superpowers/specs/2026-10-31-sniffeur-i2c-design.md ; protocole : sniffeur_i2c_protocole.py.

Ce que fait ce serveur :
    - lit les lignes du sniffeur : une transaction I2C par ligne, decodee (decodeur_i2c.py) jusqu'au registre
      pour les puces du parc ; la carte observee (choisie dans la page) leve les ambiguites d'adresse ;
    - inventaire et statistiques par adresse, alertes (sniffeur_i2c_alertes.py), journal continu sur disque
      (%LOCALAPPDATA%\outils_tasmota\sniffeur_i2c\, un fichier par jour, purge au-dela de 30 jours), export ;
    - lecture / ecriture d'un registre : par la CARTE Tasmota (sniffeur_i2c_carte.py, bus en service) ou par le
      SNIFFEUR devenu maitre (composant debranche de sa carte, au banc ; refuse par le firmware si le bus vit).
Routes HTTP : sniffeur_i2c_http.py ; page : sniffeur_i2c_web.py (+ sniffeur_i2c_aide.py).

Usage (Python de PlatformIO, qui fournit pyserial) :
    %USERPROFILE%\.platformio\penv\Scripts\python.exe outils_docs/scripts_python/outils_pc/sniffeur_i2c.py
    options : --port auto|COM12|loop://|aucun  --http 7350  --historique 5000  --sans-journal
              --local (127.0.0.1 seulement)  --sans-navigateur
    --port auto (defaut) : sonde par « ? » les ports USB Espressif / Raspberry Pi et garde le SEUL qui repond
    comme un sniffeur (une carte Tasmota branchee en USB est ecartee) ; sinon demarre port ferme.
Depuis VS Code : pioarduino > Project Tasks > <env> > Custom > « Sniffeur I2C (HTTP 127.0.0.1) »
(cible_sniffeur_i2c.py), ou l'annuaire des outils (http://127.0.0.1:7600). Arret : Ctrl+C.
"""

import argparse
import collections
import json
import os
import queue
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

import serial
from serial.tools import list_ports

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acces_web                                            # noqa: E402
import decodeur_i2c as di                                   # noqa: E402
import sniffeur_i2c_carte as carte_i2c                      # noqa: E402
import sniffeur_i2c_protocole as proto                      # noqa: E402
from sniffeur_i2c_alertes import Alertes                    # noqa: E402

SONDE_S = 0.8                           # attente de la ligne I apres « ? »
JOURS_JOURNAL = 30
ATTENTE_MAITRE_S = 2.0
RAPPROCHEMENT_S = 1.0                   # une trame de meme adresse et meme sens dans ce delai = la reponse
PERIODE_STATS_S = 0.5


def maintenant_texte():
    return time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"


def sonde(nom, ouvre=serial.serial_for_url):
    """True si le port repond a « ? » par une ligne I (ouvert sans DTR/RTS, puis referme)."""
    try:
        port = ouvre(nom, 115200, timeout=0.05, do_not_open=True)
        port.dtr, port.rts = False, False
        port.open()
    except (serial.SerialException, ValueError, OSError):
        return False
    try:
        port.reset_input_buffer()
        port.write(proto.ordre("?"))
        lignes, fin = proto.Lignes(), time.monotonic() + SONDE_S
        while time.monotonic() < fin:
            for ligne in lignes.ajoute(port.read(256)):
                lu = proto.lit_ligne(ligne)
                if lu and lu["type"] == "I":
                    return True
        return False
    except (serial.SerialException, OSError):
        return False
    finally:
        port.close()


def port_auto():
    trouves = [p.device for p in list_ports.comports() if p.vid in proto.VIDS_SNIFFEUR and sonde(p.device)]
    return trouves[0] if len(trouves) == 1 else None


class Journal:
    """Journal continu : sniffeur_i2c_<date>.log dans `dossier`, purge au-dela de JOURS_JOURNAL jours."""

    def __init__(self, dossier):
        self.dossier = Path(dossier)
        self.dossier.mkdir(parents=True, exist_ok=True)
        self.jour, self.fichier = None, None
        self.purge()

    def purge(self, maintenant=None):
        limite = (maintenant or time.time()) - JOURS_JOURNAL * 86400
        for f in self.dossier.glob("sniffeur_i2c_*.log"):
            try:
                if f.stat().st_mtime < limite:
                    f.unlink()
            except OSError:
                pass

    def ecrit(self, texte):
        jour = time.strftime("%Y-%m-%d")
        if jour != self.jour:
            if self.fichier:
                self.fichier.close()
            self.fichier, self.jour = open(self.dossier / f"sniffeur_i2c_{jour}.log", "a", encoding="utf-8"), jour
        self.fichier.write(f"{maintenant_texte()} {texte}\n")
        self.fichier.flush()


def texte_fiche(f):
    """Une fiche du fil -> une ligne de texte (journal, export .txt)."""
    if f["nature"] != "trame":
        return f"[{f['nature']}] {f['texte']}"
    nack = "" if f["nack"] is None else f" NACK@{f['nack']}"
    return (f"0x{f['a']:02X} {f['rw']} [{f['hex'] or '-'}]{nack} {f['fin']} {f['f']:.1f} kHz "
            f"{f['puce'] or '?'}{'?' if f['ambigu'] else ''} {f['registre']} {f['texte']}").rstrip()


class Sniffeur:
    def __init__(self, args):
        self.args = args
        self.racine = getattr(args, "racine", None) or di.RACINE
        self.verrou = threading.Lock()          # historique, statistiques, pages web
        self.verrou_port = threading.Lock()     # ouverture / fermeture / ecriture du port
        self.verrou_ordre = threading.Lock()    # un ordre a la fois (carte ou maitre)
        self.port, self.nom_port, self.erreur, self.identite = None, "", "", None
        self.historique = collections.deque(maxlen=args.historique)
        self.clients_web = []
        self.seq, self.nb, self.illisibles, self.perdues, self.nb_alertes = 0, 0, 0, 0, 0
        self.stats = {}                         # adresse -> statistiques (inventaire passif du bus)
        self.alertes = Alertes()
        self.carte = ""
        self.decodeur = di.Decodeur()
        self.journal = None if args.sans_journal else Journal(acces_web.dossier_donnees() / "sniffeur_i2c")
        self.attentes = []                      # ordres envoyes a la carte, en attente de leur trame
        self.reponse_maitre, self.evt_maitre = None, threading.Event()
        self.sale, self.t_stats = False, 0.0
        self.h_lot = None                       # heure du lot en cours : strftime coute cher, une fois par lot
        self.debut = time.strftime("%d/%m %H:%M:%S")

    # ------------------------------------------------------------------ diffusion vers les pages
    def etat(self):
        return {"port": self.nom_port, "ouvert": self.port is not None, "erreur": self.erreur,
                "identite": self.identite, "nb": self.nb, "illisibles": self.illisibles, "perdues": self.perdues,
                "alertes": self.nb_alertes, "depuis": self.debut, "carte": self.carte,
                "puces": self.decodeur.puces, "journal": str(self.journal.dossier) if self.journal else ""}

    @staticmethod
    def _paquet(evenement, donnees):
        return f"event: {evenement}\ndata: {json.dumps(donnees)}\n\n".encode("utf-8")

    def _diffuse(self, paquets):
        """SOUS self.verrou."""
        for file in self.clients_web:
            for paquet in paquets:
                file.put(paquet)

    def _stats_et_etat(self):
        """SOUS self.verrou."""
        self.sale, self.t_stats = False, time.monotonic()
        return [self._paquet("stats", list(self.stats.values())), self._paquet("etat", self.etat())]

    def diffuse_etat(self):
        with self.verrou:
            self._diffuse([self._paquet("etat", self.etat())])

    def inscrit_web(self):
        file = queue.Queue()
        with self.verrou:
            for paquet in (*self._stats_et_etat(), self._paquet("lot", list(self.historique))):
                file.put(paquet)
            self.clients_web.append(file)
        return file

    def desinscrit_web(self, file):
        with self.verrou:
            if file in self.clients_web:
                self.clients_web.remove(file)

    def _fiche(self, nature, texte, **champs):
        """SOUS self.verrou : nouvelle fiche du fil (memorisee, journalisee) ; a diffuser par l'appelant."""
        self.seq += 1
        fiche = {"n": self.seq, "h": self.h_lot or maintenant_texte(), "nature": nature, "texte": texte, **champs}
        self.historique.append(fiche)
        if nature == "alerte":
            self.nb_alertes += 1
        if self.journal:
            self.journal.ecrit(texte_fiche(fiche))
        return fiche

    def message(self, nature, texte):
        """Fiche hors bus (info, ordre, reponse, alerte), diffusee aussitot."""
        print(texte)
        with self.verrou:
            self._diffuse([self._paquet("lot", [self._fiche(nature, texte)]), *self._stats_et_etat()])

    # ------------------------------------------------------------------ lignes du sniffeur
    def traite_lignes(self, lignes):
        """Un lot de lignes lues sur le port -> fiches du fil, diffusees en un seul evenement."""
        if not lignes:
            return
        with self.verrou:
            fiches, self.h_lot = [], maintenant_texte()
            for ligne in lignes:
                lu = proto.lit_ligne(ligne)
                if lu is None:
                    self.illisibles += 1
                elif lu["type"] == "X":
                    fiches += self._transaction(lu)
                elif lu["type"] == "P":
                    self.perdues += lu["n"]
                    fiches.append(self._fiche("alerte", Alertes.pertes(lu["n"])))
                elif lu["type"] == "B":
                    fiches.append(self._fiche("alerte", Alertes.bloque(lu["ms"])))
                elif lu["type"] == "I":
                    self.identite = lu
                    texte = (f"sniffeur {lu['puce']} (protocole v{lu['v']}) : SDA=GPIO{lu['sda']} SCL=GPIO{lu['scl']}, "
                             f"echantillonnage {lu['ech']} MHz")
                    fiches.append(self._fiche("info" if lu["v"] == proto.VERSION else "alerte",
                                              texte if lu["v"] == proto.VERSION else texte + " : VERSION INCONNUE"))
                else:
                    self.reponse_maitre = lu
                    self.evt_maitre.set()
                self.sale = True
            fiches += self._expire()
            self.h_lot = None
            paquets = [self._paquet("lot", fiches)] if fiches else []
            if self.sale and time.monotonic() - self.t_stats >= PERIODE_STATS_S:
                paquets += self._stats_et_etat()
            self._diffuse(paquets)

    def _transaction(self, tr):
        """SOUS self.verrou."""
        self.nb += 1
        ptr_avant = self.decodeur.memoire.get(tr["a"], {}).get("ptr")
        dec = self.decodeur.decode(tr)
        s = self.stats.setdefault(tr["a"], {"a": tr["a"], "transactions": 0, "lectures": 0, "ecritures": 0,
                                            "nack": 0, "f": 0.0, "f_max": 0.0, "derniere": "", "puce": ""})
        s["transactions"] += 1
        s["lectures" if tr["rw"] == "R" else "ecritures"] += 1
        s["nack"] += tr["nack"] is not None
        if tr["f"]:
            s["f"], s["f_max"] = tr["f"], max(s["f_max"], tr["f"])
        s["derniere"], s["puce"] = self.h_lot, dec["puce"] or "/".join(dec["candidats"])
        fiches = [self._fiche("trame", dec["texte"], a=tr["a"], rw=tr["rw"], hex=tr["d"].hex(" ").upper(),
                              nack=tr["nack"], fin=tr["fin"], f=tr["f"], tu=tr["t"], puce=dec["puce"],
                              ambigu=dec["ambigu"], candidats=dec["candidats"], registre=dec["registre"])]
        fiches += [self._fiche("alerte", texte) for texte in self.alertes.transaction(tr)]
        for attente in self.attentes:
            # meme adresse, meme sens, meme registre (la sonde « detect », sans donnee, ne compte pas)
            if attente["vue"] or attente["a"] != tr["a"] or attente["rw"] != tr["rw"]:
                continue
            if (tr["d"][:1] == bytes([attente["reg"]])) if tr["rw"] == "W" else (ptr_avant == attente["reg"]):
                attente["vue"] = True
                fiches.append(self._fiche("reponse", f"trame vue pour « {attente['commande']} » : "
                                                     f"[{tr['d'].hex(' ').upper() or '-'}] {dec['texte']}"))
                break
        return fiches

    def _expire(self, maintenant=None):
        """SOUS self.verrou : ordres a la carte dont la trame n'a pas ete vue a temps."""
        maintenant, fiches = maintenant or time.monotonic(), []
        for attente in [a for a in self.attentes if a["vue"] or maintenant > a["jusqua"]]:
            self.attentes.remove(attente)
            if not attente["vue"]:
                fiches.append(self._fiche("alerte", f"trame NON VUE pour « {attente['commande']} » : bus de la carte "
                                                    f"non relie au sniffeur, ou autre bus (wire2)"))
        return fiches

    # ------------------------------------------------------------------ carte observee
    def choisit_carte(self, carte):
        puces = di.charge_carte(self.racine, carte) if carte else None
        with self.verrou:
            self.carte, self.decodeur = carte, di.Decodeur(puces)
            self._diffuse([self._paquet("etat", self.etat())])
        return {"carte": carte, "puces": puces, "ip": carte_i2c.ip_proposee(self.racine, carte) if carte else ""}

    # ------------------------------------------------------------------ port serie
    def ouvre(self, nom):
        self.ferme()
        with self.verrou_port:
            try:
                port = serial.serial_for_url(nom, 115200, timeout=0, do_not_open=True)
                port.dtr, port.rts = False, False   # USB natif de l'S3 : pas de reset a l'ouverture
                port.open()
                port.reset_input_buffer()
                port.write(proto.ordre("?"))        # la ligne I confirme que c'est bien un sniffeur
                self.port, self.erreur, self.identite = port, "", None
            except (serial.SerialException, ValueError) as erreur:
                self.erreur = f"ouverture de {nom} impossible : {erreur}"
            self.nom_port = nom
        self.diffuse_etat()
        if self.erreur:
            raise OSError(self.erreur)
        print(f"port {nom} ouvert")

    def ferme(self, raison=""):
        with self.verrou_port:
            port, self.port = self.port, None
            if port is not None:
                try:
                    port.close()
                except (serial.SerialException, OSError):
                    pass
            if raison:
                self.erreur = raison
        if port is not None:
            self.diffuse_etat()

    def boucle_lecture(self):
        lignes = proto.Lignes()
        while True:
            port = self.port
            if port is None:
                lignes = proto.Lignes()
                time.sleep(0.1)
                continue
            try:
                morceau = port.read(port.in_waiting or 1)
            except Exception as erreur:         # sniffeur debranche, ou port ferme par la page entre-temps
                if self.port is port:
                    self.ferme(f"port {self.nom_port} perdu : {erreur} (rebrancher puis Ouvrir)")
                continue
            try:
                self.traite_lignes(lignes.ajoute(morceau))
            except Exception as erreur:         # une ligne mal formee ne doit jamais arreter l'ecoute
                self.message("alerte", f"lot ignore : {erreur!r}")
            if not morceau:
                time.sleep(0.005)
                with self.verrou:
                    fiches = self._expire()
                    paquets = [self._paquet("lot", fiches)] if fiches else []
                    if self.sale and time.monotonic() - self.t_stats >= PERIODE_STATS_S:
                        paquets += self._stats_et_etat()
                    self._diffuse(paquets)

    # ------------------------------------------------------------------ ordres
    def ordre_carte(self, ip, a, reg, n, valeur=None, envoie=carte_i2c.envoie):
        """Lecture (valeur None) ou ecriture d'un registre par la carte Tasmota ; rend {ok, commande, reponse}."""
        commande = carte_i2c.commande_br(a, reg, n, valeur)
        if not self.verrou_ordre.acquire(blocking=False):
            raise OSError("un ordre est deja en cours : attendre sa reponse")
        try:
            with self.verrou:
                self.attentes.append({"a": a, "reg": reg, "rw": "R" if valeur is None else "W", "commande": commande,
                                      "jusqua": time.monotonic() + RAPPROCHEMENT_S + carte_i2c.DELAI_S, "vue": False})
            self.message("ordre", f"carte {ip} : {commande}")
            ok, reponse = envoie(ip, commande)
            self.message("reponse" if ok else "alerte", f"carte {ip} : {reponse}")
            if not ok:
                with self.verrou:
                    self.attentes = [x for x in self.attentes if x["commande"] != commande]
            return {"ok": ok, "commande": commande, "reponse": reponse}
        finally:
            self.verrou_ordre.release()

    def ordre_maitre(self, nom, a, d=b"", n=0):
        """Ordre au sniffeur devenu maitre (composant isole) ; rend la reponse M (dict) ou leve OSError."""
        trame = proto.ordre(nom, a, d, n)
        if not self.verrou_ordre.acquire(blocking=False):
            raise OSError("un ordre est deja en cours : attendre sa reponse")
        try:
            with self.verrou_port:
                if self.port is None:
                    raise OSError("port serie ferme : l'ouvrir d'abord")
                self.evt_maitre.clear()
                self.reponse_maitre = None
                self.port.write(trame)
            self.message("ordre", f"sniffeur maitre : {trame.decode().strip()}")
            if not self.evt_maitre.wait(ATTENTE_MAITRE_S):
                self.message("alerte", "sniffeur maitre : pas de reponse")
                raise OSError("le sniffeur n'a pas repondu")
            r = self.reponse_maitre
            self.message("reponse" if r["ok"] else "alerte",
                         f"sniffeur maitre : {'[' + r['d'].hex(' ').upper() + ']' if r['ok'] else 'refus ' + r['err']}")
            return {"ok": r["ok"], "d": r["d"].hex(" ").upper(), "err": r["err"]}
        finally:
            self.verrou_ordre.release()

    def export(self, format_):
        with self.verrou:
            fiches = list(self.historique)
        if format_ == "json":
            return json.dumps(fiches, ensure_ascii=False, indent=1), "application/json"
        return "".join(f"{f['h']} {texte_fiche(f)}\n" for f in fiches), "text/plain; charset=utf-8"

    def raz(self):
        with self.verrou:
            self.stats, self.nb, self.illisibles, self.perdues, self.nb_alertes = {}, 0, 0, 0, 0
            self.alertes, self.attentes = Alertes(), []
            self.historique.clear()
            self._diffuse([self._paquet("raz", {}), *self._stats_et_etat()])


def main():
    from sniffeur_i2c_http import fabrique_gestionnaire
    for flux in (sys.stdout, sys.stderr):       # console redirigee (tache VS Code) : cp1252 sous Windows
        try:
            flux.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    options = argparse.ArgumentParser(description="Sniffeur I2C (ESP32-S3 dedie) avec page web locale.")
    options.add_argument("--port", default="auto", help="auto | COM12 | loop:// | aucun (choisi sur la page)")
    options.add_argument("--http", type=int, default=7350, help="port HTTP de la page (defaut 7350)")
    options.add_argument("--historique", type=int, default=5000, help="fiches rejouees a l'ouverture de la page")
    options.add_argument("--sans-journal", dest="sans_journal", action="store_true", help="pas de journal sur disque")
    acces_web.ajoute_options(options)
    args = options.parse_args()
    if not 0 < args.http < 65536 or args.historique < 0:
        sys.exit("parametre hors bornes")

    sniffeur = Sniffeur(args)
    acces = acces_web.Acces(args.http, args.local, "sniffeur I2C")
    try:
        http = ThreadingHTTPServer((acces.hote, args.http), fabrique_gestionnaire(sniffeur, acces))
    except OSError as erreur:
        sys.exit(f"port HTTP {args.http} indisponible ({erreur}) : un sniffeur tourne-t-il deja ? (--http <autre>)")
    http.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    if sniffeur.journal:
        print(f"journal : {sniffeur.journal.dossier}")

    nom = port_auto() if args.port == "auto" else (None if args.port == "aucun" else args.port)
    if nom:
        try:
            sniffeur.ouvre(nom)
        except OSError as erreur:
            print(f"{erreur} -> demarrage port ferme, a ouvrir depuis la page")
    elif args.port == "auto":
        print("aucun sniffeur trouve (zero ou plusieurs) -> port a ouvrir depuis la page")
    else:
        print("port a ouvrir depuis la page")
    threading.Thread(target=sniffeur.boucle_lecture, daemon=True).start()
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        sniffeur.ferme()


if __name__ == "__main__":
    main()
