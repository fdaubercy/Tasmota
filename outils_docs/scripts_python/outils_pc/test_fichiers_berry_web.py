"""Banc de fichiers_berry_web (routes HTTP de la page « Fichiers Berry par env »).

Code de sortie 0 = vert. Serveur dans un fil, sur un port libre, devant une COPIE du depot (les .ini, le .h,
les dossiers de carte et data/fs) dans un dossier temporaire ; la detection des builds est simulee.
"""

import http.client
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import acces_web
import fichiers_berry_ini as fbi
import fichiers_berry_web as fbweb
import test_fichiers_berry_creation as tfc

ECHECS = []
RIDEAU = "tasmota32s3-garage-rideau-garage-modbus"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


class Banc:
    def __init__(self, t):
        self.racine = tfc.depot_essai(t)
        shutil.copytree(tfc.RACINE / "data" / "fs", self.racine / "data" / "fs",
                        ignore=lambda d, noms: [n for n in noms if not n.endswith(".be")])
        self.builds = []
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        acces = acces_web.Acces(self.port, True, "Fichiers Berry par env")
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port),
                                           fbweb.fabrique_gestionnaire(acces, self.racine, lambda: self.builds))
        self.serveur.daemon_threads = True
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def requete(self, methode, chemin, corps=None, entetes=None):
        h = dict(entetes if entetes is not None else ({"X-Fichiers-Berry": "1"} if methode == "POST" else {}))
        donnees = json.dumps(corps).encode("utf-8") if corps is not None else None
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            c.request(methode, chemin, body=donnees, headers=h)
            r = c.getresponse()
            texte = r.read().decode("utf-8")
            try:
                return r.status, json.loads(texte)
            except ValueError:
                return r.status, texte
        finally:
            c.close()

    def ferme(self):
        self.serveur.shutdown()
        self.serveur.server_close()


def test_get(b):
    statut, page = b.requete("GET", "/")
    verifie((statut, "<html" in page.lower()), (200, True), "GET / : page html")
    verifie(b.requete("GET", "/execution"), (200, {"en_cours": False}), "GET /execution (lu par la cible)")
    statut, envs = b.requete("GET", "/envs")
    verifie((statut, {"nom": RIDEAU, "famille": "cartes"} in envs["envs"]), (200, True), "GET /envs : le rideau")
    statut, etat = b.requete("GET", f"/etat?env={RIDEAU}")
    f = {x["chemin"]: x for x in etat["fichiers"]}
    verifie((statut, f["data/garage/tasmota32s3-rideau-garage-modbus/controleRideau.be"]["etat"]), (200, "solidifie"),
            "GET /etat : controleRideau solidifie")
    verifie(b.requete("GET", "/etat?env=tasmota32s3-nulle-part")[0], 404, "GET /etat : env inconnu -> 404")
    verifie(etat.get("build_en_cours"), False, "GET /etat : build_en_cours faux sans build")
    b.builds = ["pio run -e x"]
    verifie(b.requete("GET", f"/etat?env={RIDEAU}")[1].get("build_en_cours"), True,
            "GET /etat : build_en_cours vrai pendant un build")
    b.builds = []
    statut, ident = b.requete("GET", "/identite?base=tasmota32s3-base-N16R8-sans-ecran&lieu=garage&nom=porte-test")
    verifie((statut, ident["env"], ident["define"], ident["identite"]["MQTT_TOPIC"]),
            (200, "tasmota32s3-garage-porte-test", "FIRMWARE_ESP32S3_GARAGE_PORTE_TEST", "garage/porte-test"),
            "GET /identite : valeurs proposees")


def test_post_sans_entete(b):
    corps = {"env": RIDEAU, "demandes": []}
    verifie(b.requete("POST", "/prepare", corps, entetes={})[0], 403, "POST sans en-tete -> 403")
    verifie(b.requete("POST", "/prepare", corps, entetes={"X-Fichiers-Berry": "1", "Origin": "http://evil.example"})[0],
            403, "POST d'une autre origine -> 403")


def demandes():
    return [{"chemin": "data/fs/loRaWanFonctions.be", "etat": "fs"}]


def test_post_enregistre(b):
    avant = (b.racine / fbi.FICHIER_CENV).read_bytes()
    statut, p = b.requete("POST", "/prepare", {"env": RIDEAU, "demandes": demandes()})
    verifie((statut, p["confirmations"], p["refus"], "-" in p["diff"]), (200, [], [], True), "POST /prepare : diff")
    statut, r = b.requete("POST", "/enregistre", {"env": RIDEAU, "demandes": demandes(), "empreinte": p["empreinte"]})
    verifie((statut, r.get("ecrit") if isinstance(r, dict) else r), (200, True), "POST /enregistre : ecrit")
    verifie((b.racine / fbi.FICHIER_CENV).read_bytes() != avant, True, "POST /enregistre : cenv modifie")


def test_post_pendant_build(b):
    _, p = b.requete("POST", "/prepare", {"env": RIDEAU, "demandes": demandes()})
    b.builds = ["pio run -e x"]
    statut, texte = b.requete("POST", "/enregistre", {"env": RIDEAU, "demandes": demandes(), "empreinte": p["empreinte"]})
    b.builds = []
    verifie((statut, "build" in texte), (409, True), "POST /enregistre pendant un build -> 409")


class Explose:
    """Detection de build qui casse (OSError) : erreur inattendue du point de vue du serveur."""
    def __bool__(self):
        raise OSError("panne simulee de la detection")


def test_erreur_inattendue(b):
    _, p = b.requete("POST", "/prepare", {"env": RIDEAU, "demandes": demandes()})
    b.builds = Explose()
    try:
        statut, texte = b.requete("POST", "/enregistre", {"env": RIDEAU, "demandes": demandes(), "empreinte": p["empreinte"]})
        verifie((statut, "panne simulee" in texte), (500, True), "POST, erreur inattendue -> 500 avec le message")
    except (OSError, http.client.HTTPException) as erreur:
        verifie(repr(erreur), "reponse 500", "POST, erreur inattendue -> 500 avec le message (connexion coupee)")
    b.builds = []
    origine = fbweb.fbe.etat_env

    def panne(racine, env):                          # fichier verrouille, disque plein... : OSError
        raise PermissionError("fichier verrouille (panne simulee)")
    fbweb.fbe.etat_env = panne
    try:
        statut, texte = b.requete("GET", "/etat?env=" + RIDEAU)
        verifie((statut, "verrouille" in texte), (500, True), "GET, erreur inattendue -> 500 avec le message")
    except (OSError, http.client.HTTPException) as erreur:
        verifie(repr(erreur), "reponse 500", "GET, erreur inattendue -> 500 avec le message (connexion coupee)")
    finally:
        fbweb.fbe.etat_env = origine


def test_post_empreinte_perimee(b):
    statut, _ = b.requete("POST", "/enregistre", {"env": RIDEAU, "demandes": demandes(), "empreinte": "0" * 64})
    verifie(statut, 409, "POST /enregistre avec une empreinte perimee -> 409")


def test_post_invalide(b):
    verifie(b.requete("POST", "/prepare", {"env": RIDEAU, "demandes": "x"})[0], 400, "demandes pas une liste -> 400")
    verifie(b.requete("POST", "/prepare", {"env": RIDEAU, "demandes": [{"chemin": 3, "etat": "fs"}]})[0], 400,
            "chemin pas une chaine -> 400")
    verifie(b.requete("POST", "/inconnue", {})[0], 404, "POST route inconnue -> 404")


def test_post_creation(b):
    _, ident = b.requete("GET", "/identite?base=tasmota32s3-base-N16R8-sans-ecran&lieu=garage&nom=porte-test")
    corps = {"modele": RIDEAU, "base": "tasmota32s3-base-N16R8-sans-ecran", "lieu": "garage", "nom": "porte-test",
             "identite": ident["identite"]}
    statut, p = b.requete("POST", "/creation/prepare", corps)
    verifie((statut, p["refus"]), (200, []), "POST /creation/prepare : aucun refus")
    statut, r = b.requete("POST", "/creation", dict(corps, empreinte=p["empreinte"]))
    verifie((statut, r.get("cree") if isinstance(r, dict) else r), (200, True), "POST /creation : cree")
    verifie((b.racine / "data/garage/tasmota32s3-porte-test/autoexec.be").is_file(), True, "POST /creation : dossier")
    statut, _ = b.requete("POST", "/creation", dict(corps, empreinte=p["empreinte"]))
    verifie(statut, 409, "POST /creation une 2e fois -> 409")


def test_post_renommage_puis_suppression(b):
    statut, ident = b.requete("GET", f"/identite?env={RIDEAU}&lieu=garage&nom=porte2")
    verifie((statut, ident.get("env") if isinstance(ident, dict) else ident), (200, "tasmota32s3-garage-porte2"),
            "GET /identite?env= : base de l'env, env propose")
    corps = {"env": RIDEAU, "lieu": "garage", "nom": "porte2", "identite": ident["identite"]}
    statut, p = b.requete("POST", "/renommage/prepare", corps)
    verifie((statut, p.get("refus") if isinstance(p, dict) else p), (200, []), "POST /renommage/prepare : aucun refus")
    statut, r = b.requete("POST", "/renommage", dict(corps, empreinte=p["empreinte"]))
    verifie((statut, r.get("env") if isinstance(r, dict) else r), (200, "tasmota32s3-garage-porte2"), "POST /renommage : renomme")
    statut, p = b.requete("POST", "/suppression/prepare", {"env": "tasmota32s3-garage-porte2"})
    verifie((statut, p.get("refus") if isinstance(p, dict) else p), (200, []), "POST /suppression/prepare : aucun refus")
    statut, r = b.requete("POST", "/suppression", {"env": "tasmota32s3-garage-porte2", "empreinte": p["empreinte"]})
    verifie((statut, r.get("dossier_sauvegarde") if isinstance(r, dict) else r),
            (200, "data/garage/tasmota32s3-porte2-sauvegarde"), "POST /suppression : dossier en -sauvegarde")
    statut, _ = b.requete("POST", "/suppression", {"env": "tasmota32s3-garage-porte2", "empreinte": p["empreinte"]})
    verifie(statut, 404, "POST /suppression d'un env deja supprime -> 404")
    statut, _ = b.requete("POST", "/suppression/prepare", {"env": "tasmota32s3-base-N16R8"})
    verifie(statut, 200, "POST /suppression/prepare d'une base -> 200 avec refus")


def principal():
    for test in (test_get, test_post_sans_entete, test_post_enregistre, test_post_pendant_build,
                 test_post_empreinte_perimee, test_post_invalide, test_post_creation, test_erreur_inattendue,
                 test_post_renommage_puis_suppression):
        with tempfile.TemporaryDirectory() as t:
            os.environ["OUTILS_TASMOTA_DOSSIER"] = os.path.join(t, "outils")    # sauvegardes hors du vrai dossier
            b = Banc(t)
            try:
                test(b)
            except Exception as exc:
                verifie(repr(exc), "pas d'exception", test.__name__)
            finally:
                b.ferme()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
