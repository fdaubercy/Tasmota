"""Banc de build_ota_fs (envoi du firmware par /u2 et du file system par /ufsu) sur une carte simulee.

Code de sortie 0 = vert. La carte simulee est un petit serveur HTTP sur 127.0.0.1 (port libre) qui
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
    carte muette pendant `coupure` secondes (None = ne revient jamais) ; Status -> JSON.
Aucune vraie carte n'est contactee.
"""

import json
import re
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath

import build_ota_fs as bo

ECHECS = []
ANCIEN_PERSIST = b'{"serveur": {"ancien": true}}'
NOUVEAU_PERSIST = b'{"serveur": {"nouveau": true}, "diverses": {}}'
BR_RECHARGE = ("Br import persist persist.load() serveur = persist.serveur diverses = persist.diverses "
               "modules = persist.modules drivers = persist.drivers")
RAPIDE = {"delai_retour": 5.0, "attente_min": 0.0, "sondage": 0.05}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


# -- carte simulee ------------------------------------------------------------------------------------

class Carte:
    def __init__(self, persist=ANCIEN_PERSIST, coupure=0.3, carte_sd=False):
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
        return self.repond(h, "<html>Accueil</html>")

    def commande(self, h, cmnd):
        if cmnd == "Status":
            return self.repond(h, '{"Status":{"Module":0}}', "application/json")
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

    def redemarre(self):
        self.muette_des = time.monotonic() + self.retard
        self.revient_a = float("inf") if self.coupure is None else self.muette_des + self.coupure
        self.ufs_path, self.type_envoi = "/", "aucun"

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
            self.firmware = (nom, contenu)
        self.repond(h, "<b>Upload <font>Successful</font></b><br>Restarting")
        self.redemarre()

    # lecture du journal
    def requetes(self, motif=""):
        return [(m, c) for m, c, _ in self.journal if motif in c]


def fs_essai(t, persist=NOUVEAU_PERSIST):
    """littlefs_data d'essai : racine, json/, sd/js/, sd/css/."""
    d = Path(t) / "littlefs_data"
    for rel, contenu in {"autoexec.be": b"print(1)", "json/graphiques.json": b"{}",
                         "sd/js/graphiques.js": b"var x = 1;" * 50, "sd/css/graphiques.css": b"body{}"}.items():
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_bytes(contenu)
    if persist is not None:
        (d / "_persist.json").write_bytes(persist)
    sauvegardes = Path(t) / "persist"
    sauvegardes.mkdir()
    return d, sauvegardes


def envoie_fs(carte, t, **options):
    """Lance envoie_fs_ota ; renvoie (message d'erreur ou None, rapports, dossier des sauvegardes)."""
    d, sauvegardes = fs_essai(t)
    rapports = []
    try:
        bo.envoie_fs_ota("tasmota32-essai", carte.ip, d, sauvegardes, rapports.append, **{**RAPIDE, **options})
        return None, rapports, sauvegardes
    except RuntimeError as erreur:
        return str(erreur), rapports, sauvegardes


def genre(methode, chemin):
    """Requete du journal -> etape du deroule (pour verifier l'ordre)."""
    cmnd = urllib.parse.unquote(chemin.split("cmnd=", 1)[1]) if "cmnd=" in chemin else ""
    if "download=/_persist.json" in chemin:
        return "persist"
    if "path.mkdir" in cmnd:
        return "dossier"
    if chemin.startswith(("/ufsd", "/ufsu")):
        return "envoi"
    if cmnd.startswith("Br import persist"):
        return "rechargement"
    return {"Restart 1": "restart", "Status": "status"}.get(cmnd, chemin)


def compacte(liste):
    return [x for i, x in enumerate(liste) if i == 0 or x != liste[i - 1]]


# -- tests du file system -----------------------------------------------------------------------------

def test_ota_fs_ordre():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        erreur, _, _ = envoie_fs(carte, t)
        verifie(erreur, None, "ota_fs_ordre : envoi sans erreur")
        verifie(compacte([genre(m, c) for m, c in carte.requetes()]),
                ["persist", "dossier", "envoi", "persist", "rechargement", "restart", "status", "persist"],
                "ota_fs_ordre : sauvegarde -> dossiers -> envois -> relecture -> Br -> Restart 1 -> Status -> relecture")
        br = [urllib.parse.unquote(c.split("cmnd=", 1)[1]) for _, c in carte.requetes("cmnd=Br%20import%20persist")]
        verifie(br, [BR_RECHARGE], "ota_fs_ordre : commande Berry exacte de la spec (choix 10.5), URL-encodee")
        verifie(carte.flash["/_persist.json"], NOUVEAU_PERSIST, "ota_fs_ordre : persist de la carte remplace")
        carte.ferme()


def test_ota_fs_sauvegarde():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        _, _, sauvegardes = envoie_fs(carte, t)
        fichiers = sorted(p.name for p in sauvegardes.iterdir())
        verifie([bool(re.fullmatch(r"tasmota32-essai-\d{8}-\d{6}\.json", f)) for f in fichiers], [True],
                "ota_fs_sauvegarde : persist/<env>-<AAAAMMJJ-HHMMSS>.json")
        verifie((sauvegardes / fichiers[0]).read_bytes() if fichiers else None, ANCIEN_PERSIST,
                "ota_fs_sauvegarde : contenu = persist de la carte AVANT l'envoi")
        carte.ferme()


def test_ota_fs_persist_injoignable():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        carte.persist_injoignable = True
        erreur, _, sauvegardes = envoie_fs(carte, t)
        verifie((erreur or "").startswith("Sauvegarde du persist : "), True,
                "ota_fs_persist_injoignable : erreur 'Sauvegarde du persist'")
        verifie([c for m, c in carte.requetes() if m == "POST" or "mkdir" in c or "Restart" in c], [],
                "ota_fs_persist_injoignable : aucun /ufsu, aucun dossier cree, pas de Restart")
        verifie(list(sauvegardes.iterdir()), [], "ota_fs_persist_injoignable : aucune sauvegarde ecrite")
        carte.ferme()
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(persist=None)                  # carte sans _persist.json : meme refus
        erreur, _, _ = envoie_fs(carte, t)
        verifie((erreur or "").startswith("Sauvegarde du persist : "), True,
                "ota_fs_persist_injoignable : persist absent de la carte -> meme erreur")
        carte.ferme()


def test_ota_fs_relecture_differente():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        carte.altere_persist = True
        erreur, _, sauvegardes = envoie_fs(carte, t)
        sauvegarde = next(iter(sauvegardes.iterdir()), None)
        verifie((erreur or "").startswith("Relecture du persist : "), True,
                "ota_fs_relecture_differente : erreur 'Relecture du persist'")
        verifie(bool(sauvegarde) and str(sauvegarde) in (erreur or ""), True,
                "ota_fs_relecture_differente : chemin de la sauvegarde dans le message")
        verifie([c for _, c in carte.requetes() if "persist.load" in urllib.parse.unquote(c) or "Restart" in c], [],
                "ota_fs_relecture_differente : ni rechargement ni Restart")
        verifie(carte.flash["/_persist.json"] != ANCIEN_PERSIST, True,
                "ota_fs_relecture_differente : pas de restauration automatique")
        carte.ferme()


def test_ota_fs_sous_dossiers():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(carte_sd=True)                 # carte SD choisie dans la page : on vise la flash
        erreur, _, _ = envoie_fs(carte, t)
        verifie(erreur, None, "ota_fs_sous_dossiers : envoi sans erreur")
        verifie(sorted(carte.dossiers), ["/", "/json", "/sd", "/sd/css", "/sd/js"],
                "ota_fs_sous_dossiers : json/, sd/, sd/js/, sd/css/ crees (parent avant enfant)")
        verifie((carte.flash.get("/sd/js/graphiques.js"), carte.flash.get("/json/graphiques.json"),
                 carte.flash.get("/autoexec.be")), (b"var x = 1;" * 50, b"{}", b"print(1)"),
                "ota_fs_sous_dossiers : fichiers ecrits dans leur dossier, dans la flash")
        verifie(carte.sd, {}, "ota_fs_sous_dossiers : rien sur la carte SD")
        carte.ferme()
    # temoin : la carte simulee refuse un fichier dont le dossier n'existe pas
    carte = Carte()
    carte.ufs_path = "/absent"
    verifie("Failed" in bo._poste(carte.ip, "/ufsu?fsz=1", "ufsu", "x.js", b"x", 5.0)[1], True,
            "ota_fs_sous_dossiers : temoin, dossier absent -> 'Failed' sur la carte simulee")
    carte.ferme()


def test_ota_fs_referer():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        envoie_fs(carte, t)
        verifie({r for _, _, r in carte.journal}, {f"http://{carte.ip}/"},
                "ota_fs_referer : toutes les requetes portent Referer: http://<ip>/")
        verifie(len(carte.journal) > 10, True, "ota_fs_referer : le journal couvre tout le deroule")
        # temoin : sans Referer, la carte simulee ne repond pas (comme Tasmota)
        try:
            urllib.request.urlopen(f"http://{carte.ip}/cm?cmnd=Status", timeout=3).read()
            sans = "repondu"
        except Exception:
            sans = "muette"
        verifie(sans, "muette", "ota_fs_referer : temoin, requete sans Referer -> pas de reponse")
        carte.ferme()


def test_ota_fs_echec_ufsu():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        carte.echec_fichier = "graphiques.js"
        erreur, _, _ = envoie_fs(carte, t)
        verifie((erreur or "").startswith("Envoi des fichiers : ") and "sd/js/graphiques.js" in erreur, True,
                "ota_fs_echec_ufsu : page 'Failed' -> erreur qui nomme le fichier")
        verifie([c for _, c in carte.requetes("Restart")], [], "ota_fs_echec_ufsu : pas de Restart")
        verifie(carte.flash["/_persist.json"], ANCIEN_PERSIST,
                "ota_fs_echec_ufsu : persist envoye en dernier, donc intact apres l'echec")
        carte.ferme()


def test_ota_fs_pas_de_retour():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(coupure=None)
        debut = time.monotonic()
        erreur, _, _ = envoie_fs(carte, t, delai_retour=1.0)
        verifie((erreur or "").startswith("Redémarrage : "), True,
                "ota_fs_pas_de_retour : pas de reponse apres Restart 1 -> erreur 'Redemarrage'")
        verifie(time.monotonic() - debut < 6, True, "ota_fs_pas_de_retour : delai reduit par parametre respecte")
        carte.ferme()


def test_ota_fs_attente_retour():
    """Juste apres Restart 1 la carte repond encore : ce Status-la ne vaut pas retour."""
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(coupure=0.3)
        carte.retard = 0.6
        debut = time.monotonic()
        erreur, _, _ = envoie_fs(carte, t, attente_min=20.0)
        duree = time.monotonic() - debut
        verifie(erreur, None, "ota_fs_attente_retour : envoi sans erreur")
        verifie(duree > 0.9, True, "ota_fs_attente_retour : pas de retour accepte avant la coupure de la carte")
        verifie(duree < 10, True, "ota_fs_attente_retour : carte vue muette puis revenue -> pas d'attente de attente_min")
        carte.ferme()


def test_ota_fs_progression():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        _, rapports, _ = envoie_fs(carte, t)
        envois = [r for r in rapports if r.get("etape") == "Envoi des fichiers"]
        verifie([r["detail"].split(" ")[0] for r in envois], ["1/5", "2/5", "3/5", "4/5", "5/5"],
                "ota_fs_progression : un rapport par fichier, fichiers envoyes / total")
        verifie([r["pourcent"] for r in envois], [20, 40, 60, 80, 100], "ota_fs_progression : pourcentages")
        verifie(envois[-1]["detail"] if envois else "", "5/5 _persist.json",
                "ota_fs_progression : detail = n/total chemin (persist en dernier)")
        verifie("sd/js/graphiques.js" in [r["detail"].split(" ", 1)[1] for r in envois], True,
                "ota_fs_progression : chemin relatif avec ses dossiers")
        carte.ferme()


# -- tests du firmware --------------------------------------------------------------------------------

def build_essai(t, gz=False, magique=b"\xe9"):
    d = Path(t) / "build"
    d.mkdir()
    (d / "firmware.bin").write_bytes(magique + bytes(range(256)) * 400)
    if gz:
        (d / "firmware.bin.gz").write_bytes(b"\x1f\x8b" + b"z" * 5000)
    return d


def envoie_firmware(carte, dossier, **options):
    rapports = []
    try:
        bo.envoie_firmware_ota("tasmota32-essai", carte.ip, dossier, rapports.append, **{**RAPIDE, **options})
        return None, rapports
    except RuntimeError as erreur:
        return str(erreur), rapports


def test_ota_firmware_envoi():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        d = build_essai(t)
        erreur, rapports = envoie_firmware(carte, d)
        verifie(erreur, None, "ota_firmware_envoi : envoi sans erreur")
        verifie(carte.firmware, ("tasmota32-essai.bin", (d / "firmware.bin").read_bytes()),
                "ota_firmware_envoi : firmware.bin recu tel quel (GET /up avant POST /u2)")
        chemins = [c.split("?")[0] if "cmnd" not in c else c for _, c in carte.requetes()]
        verifie(compacte(chemins)[:3], ["/up", "/u2", "/cm?cmnd=Status"],
                "ota_firmware_envoi : /up -> POST /u2 -> attente du retour par Status")
        televersement = [r["pourcent"] for r in rapports if r.get("etape") == "Téléversement"]
        verifie((len(televersement) > 3, televersement == sorted(televersement), televersement[-1:]),
                (True, True, [100]), "ota_firmware_envoi : % = octets envoyes / taille, croissant jusqu'a 100")
        verifie(any(c.startswith(f"/u2?fsz={(d / 'firmware.bin').stat().st_size}") for _, c in carte.requetes()),
                True, "ota_firmware_envoi : fsz = taille du fichier")
        carte.ferme()


def test_ota_firmware_referer():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        envoie_firmware(carte, build_essai(t))
        verifie(({r for _, _, r in carte.journal}, len(carte.journal) >= 3), ({f"http://{carte.ip}/"}, True),
                "ota_firmware_referer : toutes les requetes portent Referer: http://<ip>/")
        carte.ferme()


def test_ota_firmware_gz_prefere():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        d = build_essai(t, gz=True)
        envoie_firmware(carte, d)
        verifie(carte.firmware, ("tasmota32-essai.bin.gz", (d / "firmware.bin.gz").read_bytes()),
                "ota_firmware_gz_prefere : firmware.bin.gz envoye de preference")
        carte.ferme()


def test_ota_firmware_echec():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        erreur, _ = envoie_firmware(carte, build_essai(t, magique=b"\x00"))
        verifie((erreur or "").startswith("Téléversement : "), True,
                "ota_firmware_echec : page 'Failed' (signature invalide) -> erreur 'Televersement'")
        verifie(carte.requetes("Status"), [], "ota_firmware_echec : pas d'attente de retour apres un echec")
        carte.ferme()
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        vide = Path(t) / "vide"
        vide.mkdir()
        erreur, _ = envoie_firmware(carte, vide)
        verifie(((erreur or "").startswith("Téléversement : "), carte.journal), (True, []),
                "ota_firmware_echec : firmware absent -> erreur, carte non contactee")
        carte.ferme()
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(coupure=None)
        erreur, _ = envoie_firmware(carte, build_essai(t), delai_retour=1.0)
        verifie((erreur or "").startswith("Redémarrage : "), True,
                "ota_firmware_echec : carte pas revenue -> erreur 'Redemarrage'")
        carte.ferme()
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        carte.serveur.shutdown()
        carte.serveur.server_close()                 # carte injoignable
        erreur, _ = envoie_firmware(carte, build_essai(t), delai_http=2.0)
        verifie((erreur or "").startswith("Téléversement : "), True,
                "ota_firmware_echec : carte injoignable -> erreur 'Televersement'")


def principal():
    for test in (test_ota_fs_ordre, test_ota_fs_sauvegarde, test_ota_fs_persist_injoignable,
                 test_ota_fs_relecture_differente, test_ota_fs_sous_dossiers, test_ota_fs_referer,
                 test_ota_fs_echec_ufsu, test_ota_fs_pas_de_retour, test_ota_fs_attente_retour,
                 test_ota_fs_progression,
                 test_ota_firmware_envoi, test_ota_firmware_referer, test_ota_firmware_gz_prefere,
                 test_ota_firmware_echec):
        try:
            test()
        except Exception as erreur:                  # un test qui plante ne masque pas les suivants
            ECHECS.append(f"{test.__name__} : {erreur!r}")
            print(f"KO   {test.__name__} : exception {erreur!r}")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
