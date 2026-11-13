"""Banc de atelier_ecrans_web (routes HTTP de l'atelier des ecrans, plan atelier-ecrans A6).

Code de sortie 0 = vert. Python de PlatformIO (ProjectConfig) :
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_ecrans_web.py
Serveur dans un fil, sur un port libre, devant une COPIE du depot (les .ini, le .h, le catalogue, les ecran.json, et de
chaque dossier de carte : display.ini, _persist.json, pages.jsonl, ecranLvgl.be, *.ttf) dans un dossier temporaire.
La carte est simulee par un `get` injecte (aucun reseau) qui note chaque adresse appelee.
"""

import http.client
import json
import os
import shutil
import socket
import struct
import sys
import tempfile
import threading
import urllib.parse
from http.server import ThreadingHTTPServer
from pathlib import Path

import acces_web
import atelier_ecrans_catalogue as cat
import atelier_ecrans_description as aed
import atelier_ecrans_web as aew
import fichiers_berry_ini as fbi

DEPOT = Path(__file__).resolve().parents[3]
DEBITS = "tasmota32s3-bureau-ecran-debits-pac"          # IP fixe du .h : 192.168.0.51
SANS_ECRAN = "tasmota32s3-rdc-grenier"                  # carte sans display.ini
POLICE = "RobotoCondensed-Regular"
DOSSIER_CARTE = ("display.ini", "_persist.json", "pages.jsonl", "ecranLvgl.be")
SNS = {"StatusSNS": {"Time": "x", "DEBITS": {"D1": 4.2}}}
NOM_BMP = "/screenshot-1762953600.bmp"
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def bmp():
    tete = (b"BM" + struct.pack("<III", 8 + 0x42, 0, 0x42)).ljust(0x42, b"\0")
    return tete + b"\1\2\3\4\5\6\7\x08"


def copie(racine):
    for f in (*fbi.FICHIERS_INI, "tasmota/user_config_override.h", cat.CATALOGUE):
        (racine / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DEPOT / f, racine / f)
    shutil.copytree(DEPOT / aed.DOSSIER, racine / aed.DOSSIER)
    for d in (cat.AMONT, cat.PERSO, "outils_docs/etiquettes_qr/lib"):    # display.ini cites par le catalogue ; lib du QR code
        if (DEPOT / d).is_dir():
            shutil.copytree(DEPOT / d, racine / d, dirs_exist_ok=True)
    for d in (DEPOT / "data").glob("*/*"):
        for f in [d / n for n in DOSSIER_CARTE] + list(d.glob("*.ttf")):
            if f.is_file():
                (racine / f.relative_to(DEPOT)).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, racine / f.relative_to(DEPOT))


def instantane(racine):
    return {p.relative_to(racine).as_posix(): p.read_bytes() for p in sorted(racine.rglob("*")) if p.is_file()}


class Banc:
    def __init__(self, t):
        self.racine = Path(t) / "depot"
        self.racine.mkdir()
        copie(self.racine)
        self.morte, self.appels = False, []
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        acces = acces_web.Acces(self.port, True, "Atelier des ecrans")
        self.builds = []
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port), aew.fabrique_gestionnaire(acces, self.racine, get=self.get,
                                                                                                builds_en_cours=lambda: self.builds))
        self.serveur.daemon_threads = True
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def get(self, ip, chemin, delai):
        self.appels.append((ip, urllib.parse.unquote(chemin)))
        if self.morte:
            raise OSError("timed out")
        if chemin.startswith("/cm?cmnd=Status"):
            return json.dumps(SNS).encode()
        if chemin.startswith("/cm?cmnd=Br"):
            return json.dumps({"Br": NOM_BMP}).encode()
        if "download=" in chemin and "delete=" not in chemin:
            return bmp()
        return b"<html>liste</html>"

    def requete(self, methode, chemin, corps=None, entetes=None):
        h = dict(entetes if entetes is not None else ({"X-Atelier-Ecrans": "1"} if methode == "POST" else {}))
        donnees = json.dumps(corps).encode("utf-8") if corps is not None else None
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            c.request(methode, chemin, body=donnees, headers=h)
            r = c.getresponse()
            brut = r.read()
            self.entetes, self.brut = dict(r.getheaders()), brut
            try:
                return r.status, json.loads(brut.decode("utf-8"))
            except ValueError:
                return r.status, brut.decode("utf-8", "replace")
        finally:
            c.close()

    def ferme(self):
        self.serveur.shutdown()
        self.serveur.server_close()


def brut(b, requete):
    """Statut HTTP d'une requete ecrite a la main (en-tetes que http.client refuse de forger)."""
    with socket.create_connection(("127.0.0.1", b.port), timeout=10) as s:
        s.sendall(requete.encode("ascii"))
        s.shutdown(socket.SHUT_WR)
        reponse = b""
        while b"\r\n" not in reponse:
            morceau = s.recv(4096)
            if not morceau:
                break
            reponse += morceau
    return int(reponse.split(b" ")[1]) if reponse else None


def test_page(b):
    statut, page = b.requete("GET", "/")
    verifie((statut, "<title>Atelier des écrans</title>" in page), (200, True), "GET / : la page (titre lu par la cible)")
    verifie(b.requete("GET", "/inconnu")[0], 404, "GET route inconnue -> 404")


def test_cartes(b):
    statut, r = b.requete("GET", "/cartes")
    noms = {c["nom"]: c for c in r["cartes"]}
    d = noms.get(DEBITS, {})
    verifie((statut, d.get("ecran"), d.get("ip"), d.get("lieu"), d.get("description"), d.get("interface")),
            (200, "ST7262_1024x600", "192.168.0.51", "bureau", True, "haspmota"), "GET /cartes : ecran, IP du cenv, lieu, description, interface")
    verifie((noms.get(SANS_ECRAN, {}).get("ecran", "absent"), noms.get(SANS_ECRAN, {}).get("description")), (None, False),
            "GET /cartes : carte sans display.ini -> ecran null, pas d'erreur")
    verifie(noms.get("tasmota32s3-bureau-serveur-debits-pac", {}).get("ecran", "absent"), None,
            "GET /cartes : serveur des debits sans ecran (display.ini exclu du FS)")
    verifie(any(c["nom"].startswith("tasmota32s3-base") for c in r["cartes"]), False, "GET /cartes : pas de base")
    verifie(len(r.get("lieux", [])) > 0, True, "GET /cartes : table des lieux (lieux.pour_page)")
    (b.racine / "data/bureau/tasmota32s3-ecran-debits-pac/display.ini").write_text("; sans ligne :H\n", encoding="utf-8")
    statut, r = b.requete("GET", "/cartes")
    verifie((statut, {c["nom"]: c for c in r["cartes"]}[DEBITS]["ecran"]), (200, None), "GET /cartes : display.ini sans :H -> ecran null")


def test_catalogue(b):
    statut, r = b.requete("GET", "/catalogue")
    verifie((statut, r), (200, cat.charge(b.racine)), "GET /catalogue : le catalogue du depot")


def test_ecriture_routes(b):
    desc = aed.charge(b.racine, DEBITS)
    verifie(b.requete("POST", "/diff", {"env": DEBITS, "description": desc}, entetes={})[0], 403, "POST /diff sans en-tete -> 403")
    verifie(b.requete("POST", "/diff", {"env": "inconnu", "description": desc})[0], 400, "POST /diff : env inconnu -> 400")
    s, r = b.requete("POST", "/diff", {"env": DEBITS, "description": desc})
    verifie((s, r["fichiers"]), (200, []), "POST /diff : description du depot, rien a ecrire")
    autre = dict(desc, ecran="ILI9488_480x320")
    verifie(b.requete("POST", "/ecrire", {"env": DEBITS, "description": autre, "empreinte": r["empreinte"],
                                          "empreinte_description": None})[0], 400, "POST /ecrire : autre ecran que celui de la carte -> 400")
    for builds, libelle in ((["upload"], "build en cours"), (None, "build indetectable")):
        b.builds = builds
        verifie(b.requete("POST", "/ecrire", {"env": DEBITS, "description": desc, "empreinte": r["empreinte"],
                                              "empreinte_description": aed.empreinte(aed.chemin(b.racine, DEBITS).read_bytes())})[0],
                409, f"POST /ecrire : {libelle} -> 409")
    b.builds = []
    s, r = b.requete("POST", "/ecran/diff", {"env": DEBITS, "ecran": "ILI9488_480x320", "description": desc})
    verifie((s, r["refus"], any(f["chemin"].endswith("display.ini") for f in r["fichiers"])), (200, [], True), "POST /ecran/diff")
    verifie(b.requete("POST", "/ecran/diff", {"env": DEBITS, "ecran": "INCONNU", "description": desc})[0], 400, "POST /ecran/diff : ecran inconnu -> 400")


def test_description(b):
    fichier = aed.chemin(b.racine, DEBITS)
    statut, r = b.requete("GET", f"/description?env={DEBITS}")
    verifie((statut, r["description"], r["empreinte"], r["erreurs"], r["ecran"]),
            (200, aed.charge(b.racine, DEBITS), aed.empreinte(fichier.read_bytes()), [], "ST7262_1024x600"),
            "GET /description : description, empreinte des octets du fichier, valide")
    statut, r = b.requete("GET", f"/description?env={SANS_ECRAN}")
    verifie((statut, {k: v for k, v in r.items() if k != "build"}, f"env={SANS_ECRAN}&" in r.get("build", "")),
            (200, {"description": None, "empreinte": None, "erreurs": [], "ecran": None}, True),
            "GET /description : aucune description (lien page Build de l'env)")
    fichier.write_text("{tronque", encoding="utf-8")
    statut, r = b.requete("GET", f"/description?env={DEBITS}")
    verifie((statut, r["description"], bool(r["erreurs"]), r["empreinte"]), (200, None, True, aed.empreinte(b"{tronque")),
            "GET /description : fichier illisible signale (erreurs), empreinte gardee")
    for q in ("env=tasmota32s3-nulle-part", "env=tasmota32s3-base-N16R8", "env=../../platformio.ini", ""):
        verifie(b.requete("GET", f"/description?{q}")[0], 400, f"GET /description?{q} : env inconnu -> 400")


def test_apercu(b):
    desc = aed.charge(b.racine, DEBITS)
    avant = instantane(b.racine)
    statut, r = b.requete("POST", "/apercu", {"env": DEBITS, "description": desc})
    fichiers = {f["nom"]: f for f in r.get("fichiers", [])}
    verifie((statut, r.get("erreurs"), sorted(fichiers)), (200, [], ["ecran.json", "ecranLvgl.be", "pages.jsonl"]),
            "POST /apercu : trois fichiers generes")
    verifie({n: f["diff"] for n, f in fichiers.items()}, {"ecran.json": "", "ecranLvgl.be": "", "pages.jsonl": ""},
            "POST /apercu : description du depot -> aucun ecart avec les trois fichiers du depot")
    verifie(fichiers["pages.jsonl"]["chemin"], "data/bureau/tasmota32s3-ecran-debits-pac/pages.jsonl", "POST /apercu : chemin du fichier")
    verifie(fichiers["pages.jsonl"]["contenu"], (b.racine / fichiers["pages.jsonl"]["chemin"]).read_text(encoding="utf-8"),
            "POST /apercu : contenu = fichier du depot")
    desc["objets"][0]["attributs"]["text"] = "Débits « 100 % » \\ test"
    statut, r = b.requete("POST", "/apercu", {"env": DEBITS, "description": desc})
    fichiers = {f["nom"]: f for f in r["fichiers"]}
    verifie(all("Débits « 100 % »" in fichiers[n]["diff"] and fichiers[n]["ajouts"] == 1 == fichiers[n]["retraits"]
                for n in ("pages.jsonl", "ecran.json", "ecranLvgl.be")), True, "POST /apercu : texte modifie -> une ligne dans chaque diff")
    verifie(instantane(b.racine), avant, "POST /apercu : rien n'est ecrit dans le depot")
    desc["objets"][0]["x"] = 5000
    statut, r = b.requete("POST", "/apercu", {"env": DEBITS, "description": desc})
    verifie((statut, any("hors de l'écran" in m for m in r["erreurs"]), r["fichiers"]), (200, True, []),
            "POST /apercu : description invalide -> erreurs, aucun fichier")
    for corps, libelle in (({"env": DEBITS, "description": []}, "description non objet"), ({"env": "inconnu", "description": desc}, "env inconnu"),
                           ({"description": desc}, "env absent")):
        verifie(b.requete("POST", "/apercu", corps)[0], 400, f"POST /apercu : {libelle} -> 400")


def test_acces(b):
    corps = {"env": DEBITS, "description": aed.charge(b.racine, DEBITS)}
    verifie(b.requete("POST", "/apercu", corps, entetes={})[0], 403, "POST sans en-tete X-Atelier-Ecrans -> 403")
    verifie(b.requete("POST", "/apercu", corps, entetes={"X-Atelier-Ecrans": "1", "Origin": "http://evil.example"})[0], 403,
            "POST d'une autre origine -> 403")
    verifie(b.requete("POST", "/capture", {"env": DEBITS}, entetes={})[0], 403, "POST /capture sans en-tete -> 403")
    verifie(b.appels, [], "requetes refusees : la carte n'est jamais appelee")
    verifie(b.requete("POST", "/inconnu", {})[0], 404, "POST route inconnue -> 404")
    for longueur in ("-1", "10000000"):
        verifie(brut(b, f"POST /apercu HTTP/1.1\r\nHost: x\r\nX-Atelier-Ecrans: 1\r\nContent-Length: {longueur}\r\n\r\n{{}}"),
                400, f"POST Content-Length {longueur} -> 400 sans lire le corps")


def test_valeurs(b):
    statut, r = b.requete("GET", f"/valeurs?env={DEBITS}&ip=10.0.0.66&adresse=10.0.0.66")
    modele = {m["cle"]: m["exemple"] for m in aed.charge(b.racine, DEBITS)["modele"]}
    verifie((statut, r["simule"], r["sensor"], r["modele"]), (200, False, SNS["StatusSNS"], modele),
            "GET /valeurs : carte en ligne -> JSON SENSOR (Status 10), exemples du modele")
    verifie(b.appels, [("192.168.0.51", "/cm?cmnd=Status 10")], "GET /valeurs : adresse du cenv, jamais celle de la requete")
    b.morte = True
    statut, r = b.requete("GET", f"/valeurs?env={DEBITS}")
    verifie((statut, r["simule"], r["sensor"], bool(r["motif"]), r["modele"]), (200, True, None, True, modele),
            "GET /valeurs : carte injoignable -> simule: true, motif, exemples du modele")
    n = len(b.appels)
    b.morte = False
    statut, r = b.requete("GET", f"/valeurs?env={DEBITS}")
    verifie((r["simule"], len(b.appels) - n), (True, 0), "GET /valeurs : carte muette il y a peu -> simule sans l'attendre")
    aew.SILENCE = 0
    statut, r = b.requete("GET", f"/valeurs?env={DEBITS}")
    verifie(r["simule"], False, "GET /valeurs : silence ecoule -> carte relue")
    n = len(b.appels)
    statut, r = b.requete("GET", f"/valeurs?env={DEBITS}&simule=1")
    verifie((r["simule"], len(b.appels) - n), (True, 0), "GET /valeurs?simule=1 : valeurs simulees au choix, carte non appelee")
    statut, r = b.requete("GET", f"/valeurs?env={SANS_ECRAN}&simule=1")
    verifie((statut, r["modele"]), (200, {}), "GET /valeurs : env sans description -> modele vide")
    verifie(b.requete("GET", "/valeurs?env=inconnu")[0], 400, "GET /valeurs : env inconnu -> 400")


def test_capture(b):
    statut, _ = b.requete("POST", "/capture", {"env": DEBITS, "ip": "10.0.0.66", "adresse": "10.0.0.66"})
    verifie((statut, b.entetes.get("Content-Type"), b.brut), (200, "image/bmp", bmp()), "POST /capture : le BMP de la carte, image/bmp")
    verifie({ip for ip, _ in b.appels}, {"192.168.0.51"}, "POST /capture : adresse du cenv, jamais celle du corps")
    verifie(b.appels[-1][1], f"/ufsd?dir=0&delete={NOM_BMP}", "POST /capture : fichier efface de la carte")
    b.morte = True
    statut, r = b.requete("POST", "/capture", {"env": DEBITS})
    verifie((statut, isinstance(r, str) and "injoignable" in r), (409, True), "POST /capture : carte hors ligne -> 409, message clair")
    verifie(b.requete("POST", "/capture", {"env": "inconnu"})[0], 400, "POST /capture : env inconnu -> 400")


def test_police(b):
    ttf = next((b.racine / "data").glob(f"*/*/{POLICE}.ttf"))
    statut, _ = b.requete("GET", f"/police?nom={POLICE}")
    verifie((statut, b.entetes.get("Content-Type"), b.brut == ttf.read_bytes()), (200, "font/ttf", True),
            "GET /police : .ttf du catalogue, octets du depot")
    for nom in (f"{POLICE}.ttf", "montserrat", "../platformio.ini", "%2e%2e%2fplatformio.ini", "", "data/bureau/tasmota32s3-ecran-debits-pac/" + POLICE):
        verifie(b.requete("GET", f"/police?nom={nom}")[0], 404, f"GET /police?nom={nom} : hors catalogue -> 404")


def test_images(b):
    """PNG du dossier de la carte (objet img, A14) : liste, octets, rien hors de ce dossier ; bibliotheque QR des etiquettes."""
    dossier = b.racine / "data/bureau/tasmota32s3-ecran-debits-pac"
    png = b"\x89PNG\r\n\x1a\n" + bytes(range(40))
    (dossier / "pompe.png").write_bytes(png)
    (dossier / "Fond.PNG").write_bytes(png)
    (dossier / "photo.jpg").write_bytes(b"\xff\xd8")
    (b.racine / "data/bureau/autre.png").write_bytes(png)
    statut, r = b.requete("GET", f"/images?env={DEBITS}")
    verifie((statut, r), (200, {"images": ["Fond.PNG", "pompe.png"]}), "GET /images : PNG du dossier de la carte, tries, sans JPG")
    statut, _ = b.requete("GET", f"/image?env={DEBITS}&nom=pompe.png")
    verifie((statut, b.entetes.get("Content-Type"), b.brut == png), (200, "image/png", True), "GET /image : octets du PNG")
    for nom in ("photo.jpg", "../autre.png", "..%2Fautre.png", "absent.png", "", "_persist.json"):
        verifie(b.requete("GET", f"/image?env={DEBITS}&nom={nom}")[0], 404, f"GET /image?nom={nom} : hors de la liste -> 404")
    verifie(b.requete("GET", "/images?env=inconnu")[0], 400, "GET /images : env inconnu -> 400")
    lib = DEPOT / aew.QR_LIB
    statut, _ = b.requete("GET", "/lib/qr.js")
    verifie((statut, "javascript" in b.entetes.get("Content-Type", ""), b.brut == lib.read_bytes()), (200, True, True),
            "GET /lib/qr.js : bibliotheque des etiquettes, octets du depot")


TESTS = [test_page, test_cartes, test_catalogue, test_ecriture_routes, test_description, test_apercu, test_acces, test_valeurs, test_capture, test_police,
         test_images]


if __name__ == "__main__":
    for test in TESTS:
        print(f"--- {test.__name__}")
        with tempfile.TemporaryDirectory() as t:
            os.environ["OUTILS_TASMOTA_DOSSIER"] = os.path.join(t, "outils")
            b = None
            silence = getattr(aew, "SILENCE", None)
            try:
                b = Banc(t)
                test(b)
            except Exception as e:                                  # un test qui plante est un echec, pas un arret
                print(f"KO   {test.__name__} : {type(e).__name__} : {e}")
                ECHECS.append(test.__name__)
            finally:
                if silence is not None:
                    aew.SILENCE = silence
                if b:
                    b.ferme()
    print(f"\n{len(ECHECS)} echec(s)" + (" : " + ", ".join(ECHECS) if ECHECS else " : VERT"))
    sys.exit(1 if ECHECS else 0)
