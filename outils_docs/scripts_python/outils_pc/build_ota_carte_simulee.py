"""Carte Tasmota simulee pour les bancs de build_ota_fs (serveur HTTP local, aucune vraie carte).

Petit serveur HTTP sur 127.0.0.1 (port libre) qui
imite ce que fait Tasmota (tasmota/tasmota_xdrv_driver/xdrv_50_filesystem.ino et
xdrv_01_9_webserver.ino) :
  - toute route autre que / sans `Referer: http://<ip>/` : connexion fermee sans reponse
    (HttpCheckPriviledgedAccess, SetOption128 0) ; idem pour un fichier absent a telecharger ;
  - GET /ufsd et /ufsu : dossier courant remis a / ; `dir=<n>` choisit le systeme de fichiers
    (1 = carte SD) ; `download=<chemin>` : dossier -> devient le dossier courant, fichier -> envoye ;
  - POST /ufsu (champ ufsu) : ecrit <dossier courant>/<nom> ; dossier absent -> page « Failed » ;
  - GET /up arme l'envoi du firmware ; POST /u2 sans /up : rien n'est ecrit mais la page dit
    « Successful » (Web.upload_file_type = UPL_NONE) ; octet magique ni 0xE9 ni 0x1F -> « Failed » ;
  - /cm?cmnd=Br ... path.mkdir("/x") cree un dossier (dans la flash, comme Berry) ; Restart 1 ->
    carte muette pendant `coupure` secondes (None = ne revient jamais) ; Status, Status 2, Status 5 -> JSON ;
    RoutageRangeExtender repond si `maitre` (Berry du maitre en marche), sinon commande inconnue ;
  - partition OTA unique + safeboot (`safeboot=True`, HandleSwitchBootPartition de xdrv_01_9) :
    GET /u4?u4=fct&api= repond « false » et redemarre en safeboot, puis « true » une fois en safeboot ;
    sans safeboot il repond « none ». Un POST /u2 sur l'appli en cours (partition unique) echoue.
    `safeboot_reel` : en safeboot, toute commande repond « Unknown » et la page d'accueil porte <h3>SAFEBOOT</h3>
    (le vrai safeboot de la cuve, 2026-10-28) ;
  - Sleep / Sleep <n> -> {"Sleep":{"<n>":{"Active":"<n>"}}} (forme du maitre P4), valeurs posees dans `sleeps`.
Aucune vraie carte n'est contactee.
"""

import json
import re
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import PurePosixPath

ANCIEN_PERSIST = b'{"serveur": {"ancien": true}}'


class Carte:
    def __init__(self, persist=ANCIEN_PERSIST, coupure=0.3, carte_sd=False, safeboot=False):
        self.flash = {"/_persist.json": persist} if persist is not None else {}
        self.sd = {}
        self.dossiers = {"/"}
        self.ufs_path = "/"
        self.ufs_dir = 1 if carte_sd else 0
        self.type_envoi = "aucun"                    # aucun | firmware | fichier
        self.firmware = None
        self.journal = []                            # (methode, chemin, referer)
        self.coupure = coupure
        self.muette_des = 0.0                        # carte muette de muette_des a revient_a
        self.revient_a = 0.0                         # (inf = ne revient jamais)
        self.retard = 0.0                            # la carte repond encore `retard` s apres l'ordre
        self.echec_fichier = None                    # nom de fichier dont l'envoi echoue
        self.altere_persist = False                  # ecrit un autre persist que celui recu
        self.persist_injoignable = False
        self.partition_unique = safeboot             # une seule partition OTA + safeboot (factory)
        self.mode = "app"                            # app | safeboot
        self.compilation = "2026-10-24T10:00:00"     # BuildDateTime de Status 2
        self.inchange = False                        # le firmware recu ne change pas la version
        self.apres_redemarrage = None                # transforme le persist a chaque redemarrage
        self.reste_en_safeboot = False               # apres l'envoi, la carte redemarre en safeboot
        self.echec_u2 = False                        # POST /u2 refuse (page « Failed ») quel que soit le mode
        self.hostname = "CAPTEURS-CUVE"              # Hostname de Status 5
        self.maitre = False                          # repond a RoutageRangeExtender (Berry du maitre en marche)
        self.safeboot_reel = False                   # safeboot comme le vrai : Status* « Unknown », page d'accueil SAFEBOOT
        self.nom = "Capteurs de Cuve"                # DeviceName, titre de la page d'accueil
        self.sleep = 50                              # Sleep (commande, sans effet ici)
        self.sleeps = []                             # valeurs posees par « Sleep <n> »
        carte = self

        class Gestion(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                carte.traite(self, "GET")

            def do_POST(self):
                carte.traite(self, "POST")

        self.serveur = ThreadingHTTPServer(("127.0.0.1", 0), Gestion)
        self.ip = f"127.0.0.1:{self.serveur.server_address[1]}"
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def ferme(self):
        self.serveur.shutdown()
        self.serveur.server_close()

    def fs(self):
        return self.sd if self.ufs_dir == 1 else self.flash

    @staticmethod
    def repond(h, corps, type_="text/html; charset=utf-8"):
        donnees = corps if isinstance(corps, bytes) else corps.encode("utf-8")
        h.send_response(200)
        h.send_header("Content-Type", type_)
        h.send_header("Content-Length", str(len(donnees)))
        h.end_headers()
        h.wfile.write(donnees)

    def traite(self, h, methode):
        corps = b""
        if methode == "POST":
            corps = h.rfile.read(int(h.headers.get("Content-Length") or 0))
        if self.muette_des <= time.monotonic() < self.revient_a:
            return                                   # en redemarrage : aucune reponse
        url = urllib.parse.urlsplit(h.path)
        args = dict(urllib.parse.parse_qsl(url.query, keep_blank_values=True))
        referer = h.headers.get("Referer")
        self.journal.append((methode, h.path, referer))
        if url.path != "/" and referer != f"http://{self.ip}/":
            return                                   # « HTP: Referer denied » : rien n'est renvoye
        if url.path == "/cm":
            return self.commande(h, args.get("cmnd", ""))
        if url.path in ("/ufsd", "/ufsu") and methode == "GET":
            return self.repertoire(h, args)
        if url.path == "/ufsu" and methode == "POST":
            self.type_envoi = "fichier"
            return self.recoit_fichier(h, corps)
        if url.path == "/up":
            self.type_envoi = "firmware"
            return self.repond(h, "<html>Mise a jour</html>")
        if url.path == "/u2" and methode == "POST":
            return self.recoit_firmware(h, corps)
        if url.path == "/u4" and "api" in args:
            return self.bascule(h, args.get("u4", ""))
        if self.safeboot_reel and self.mode == "safeboot":
            return self.repond(h, f"<html><title>{self.nom} Main Menu</title><h3>SAFEBOOT</h3><h3></h3></html>")
        return self.repond(h, f"<html><title>{self.nom} Main Menu</title>Accueil</html>")

    def commande(self, h, cmnd):
        if self.safeboot_reel and self.mode == "safeboot" and not cmnd.startswith("Br "):
            return self.repond(h, json.dumps({"Command": "Unknown", "Input": cmnd.upper()}), "application/json")
        sleep = re.fullmatch(r"Sleep(?: (\d+))?", cmnd)
        if sleep:
            if sleep.group(1):
                self.sleep = int(sleep.group(1))
                self.sleeps.append(self.sleep)
            return self.repond(h, json.dumps({"Sleep": {str(self.sleep): {"Active": str(self.sleep)}}}), "application/json")
        if cmnd == "Status 2":
            version = "15.0.1(safeboot)" if self.mode == "safeboot" else "15.0.1(tasmota)"
            return self.repond(h, json.dumps({"StatusFWR": {"Version": version, "BuildDateTime": self.compilation,
                                                            "Boot": 31, "Core": "3_1_3"}}), "application/json")
        if cmnd == "Status":
            return self.repond(h, '{"Status":{"Module":0}}', "application/json")
        if cmnd == "Status 5":
            return self.repond(h, json.dumps({"StatusNET": {"Hostname": self.hostname}}), "application/json")
        if cmnd == "RoutageRangeExtender" and self.maitre:
            return self.repond(h, '{"RoutageRangeExtender":{"commmande":"","status":"Succès"}}', "application/json")
        if cmnd == "Restart 1":
            self.repond(h, '{"Restart":"Restarting"}', "application/json")
            self.redemarre()
            return
        m = re.fullmatch(r'Br import path path\.mkdir\("([^"]+)"\)', cmnd)
        if m:
            chemin = m.group(1)
            ok = str(PurePosixPath(chemin).parent) in self.dossiers
            if ok:
                self.dossiers.add(chemin)
            return self.repond(h, json.dumps({"Br": "true" if ok else "false"}), "application/json")
        return self.repond(h, '{"Br":"nil"}' if cmnd.startswith("Br ") else '{"Command":"Unknown"}',
                           "application/json")

    def redemarre(self, mode="app"):
        self.muette_des = time.monotonic() + self.retard
        self.revient_a = float("inf") if self.coupure is None else self.muette_des + self.coupure
        self.ufs_path, self.type_envoi, self.mode = "/", "aucun", mode
        if self.apres_redemarrage and "/_persist.json" in self.flash:     # System#Save du redemarrage
            self.flash["/_persist.json"] = self.apres_redemarrage(self.flash["/_persist.json"])

    def bascule(self, h, u4):
        """HandleSwitchBootPartition en mode api : « none », « true » ou « false » + redemarrage."""
        if not self.partition_unique:
            reponse = "none"
        elif self.mode == "safeboot":
            reponse = "true"
        elif u4 == "fct":
            self.repond(h, "false", "text/plain")
            self.redemarre("safeboot")
            return
        else:
            reponse = "true"
        self.type_envoi = "firmware"                 # Web.upload_file_type = UPL_TASMOTA
        return self.repond(h, reponse, "text/plain")

    def repertoire(self, h, args):
        self.ufs_path = "/"
        if "dir" in args:
            self.ufs_dir = int(re.match(r"\d*", args["dir"]).group(0) or 0)   # atoi
        if "download" in args:
            chemin = args["download"]
            if chemin in self.dossiers:
                self.ufs_path = chemin
            elif chemin in self.fs() and not (chemin == "/_persist.json" and self.persist_injoignable):
                return self.repond(h, self.fs()[chemin], "application/octet-stream")
            else:
                return                               # fichier absent : connexion fermee
        return self.repond(h, "<html>Gestion du systeme de fichiers</html>")

    @staticmethod
    def multipart(h, corps):
        limite = h.headers.get("Content-Type", "").split("boundary=")[-1].encode()
        for partie in corps.split(b"--" + limite):
            tete, _, contenu = partie.partition(b"\r\n\r\n")
            m = re.search(rb'name="([^"]+)"; filename="([^"]*)"', tete)
            if m:
                return m.group(1).decode(), m.group(2).decode(), contenu[:-2]
        return None, None, b""

    def recoit_fichier(self, h, corps):
        champ, nom, contenu = self.multipart(h, corps)
        chemin = (self.ufs_path.rstrip("/") + "/" + nom) if nom else ""
        if champ != "ufsu" or not nom or str(PurePosixPath(chemin).parent) not in self.dossiers \
                or nom == self.echec_fichier:
            return self.repond(h, "<b>Upload <font>Failed</font></b>")
        if chemin == "/_persist.json" and self.altere_persist:
            contenu = contenu + b" "
        self.fs()[chemin] = contenu
        return self.repond(h, "<b>Upload <font>Successful</font></b>")

    def recoit_firmware(self, h, corps):
        champ, nom, contenu = self.multipart(h, corps)
        type_, self.type_envoi = self.type_envoi, "aucun"           # HandleUploadDone : UPL_NONE
        if type_ == "firmware":
            if champ != "file" or not nom or contenu[:1] not in (b"\xe9", b"\x1f"):
                return self.repond(h, "<b>Upload <font>Failed</font></b><br>Invalid file signature")
            if self.echec_u2:
                return self.repond(h, "<b>Upload <font>Failed</font></b><br>Flash write error")
            if self.partition_unique and self.mode == "app":     # l'appli ne s'ecrase pas elle-meme
                return self.repond(h, "<b>Upload <font>Failed</font></b><br>Not enough space")
            self.firmware = (nom, contenu)
            if not self.inchange:
                self.compilation = "2026-10-24T11:%02d:00" % (len(self.journal) % 60)
        self.repond(h, "<b>Upload <font>Successful</font></b><br>Restarting")
        self.redemarre("safeboot" if self.reste_en_safeboot else "app")

    # lecture du journal
    def requetes(self, motif=""):
        return [(m, c) for m, c, _ in self.journal if motif in c]
