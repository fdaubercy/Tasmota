"""Banc de assistant_persist_web (routes HTTP de la page « Assistant persist », port 7900).

Code de sortie 0 = vert. Serveur dans un fil, sur un port libre, devant un depot d'essai (copie des .ini, du .h, des
dossiers de carte, de data/fs, du modele et du schema) ; la detection des builds est simulee.
Garde-fou : AUCUN des mots de passe reels du parc (lus en lecture seule) ne doit figurer dans une reponse HTTP,
erreurs comprises. Un echec n'affiche jamais une valeur.
Lancer : "%USERPROFILE%\\.platformio\\penv\\Scripts\\python.exe" -u outils_docs/scripts_python/outils_pc/test_assistant_persist_web.py
"""

import http.client
import json
import os
import socket
import sys
import tempfile
import threading
from dataclasses import asdict
from http.server import ThreadingHTTPServer
from pathlib import Path

import acces_web
import assistant_persist_web as apw
import test_assistant_persist_creation as tac

ECHECS = []
REPONSES_VUES = []          # texte de toutes les reponses, pour la recherche des mots de passe


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


class Banc:
    def __init__(self, t):
        self.racine = tac.depot(t)
        self.builds = []
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        acces = acces_web.Acces(self.port, True, "Assistant persist")
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port),
                                           apw.fabrique_gestionnaire(acces, self.racine, lambda: self.builds, lambda: {}))
        self.serveur.daemon_threads = True
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def requete(self, methode, chemin, corps=None, entetes=None):
        h = dict(entetes if entetes is not None else ({"X-Assistant-Persist": "1"} if methode == "POST" else {}))
        donnees = json.dumps(corps).encode("utf-8") if corps is not None else None
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        try:
            c.request(methode, chemin, body=donnees, headers=h)
            r = c.getresponse()
            texte = r.read().decode("utf-8")
            REPONSES_VUES.append(texte)
            try:
                return r.status, json.loads(texte)
            except ValueError:
                return r.status, texte
        finally:
            c.close()

    def ferme(self):
        self.serveur.shutdown()
        self.serveur.server_close()


def reponses(**kw):
    return asdict(tac.reponses(**kw))


def test_get(b):
    statut, page = b.requete("GET", "/")
    verifie((statut, "<html" in page.lower()), (200, True), "GET / : page html")
    verifie("127.0.0.1" in page, False, "page : aucune adresse en dur (liens d'apres l'hote)")
    verifie(b.requete("GET", "/execution"), (200, {"en_cours": False}), "GET /execution (lu par la cible)")
    verifie(b.requete("GET", "/modele/etat"), (200, {}), "GET /modele/etat : vide ici (A6)")
    verifie(b.requete("GET", "/interrompues"), (200, {"interrompues": []}), "GET /interrompues : rien")
    verifie(b.requete("GET", "/nulle-part")[0], 404, "GET route inconnue -> 404")
    statut, p = b.requete("GET", "/parc")
    verifie(statut, 200, "GET /parc : 200")
    verifie(sorted(p), sorted(["puces", "bases", "base_defaut", "maitres", "ids_pris", "id_libre", "reseaux", "blocs", "erreur_modele"]),
            "GET /parc : les clefs du contrat")
    verifie(p["puces"], ["ESP32", "ESP32S3", "ESP32P4"], "GET /parc : puces")
    verifie("tasmota32s3-base-N16R8" in p["bases"]["ESP32S3"], True, "GET /parc : bases par puce")
    verifie(p["base_defaut"]["ESP32S3"] in p["bases"]["ESP32S3"], True, "GET /parc : base par defaut parmi les bases")
    verifie(tac.MAITRE in [m["env"] for m in p["maitres"]], True, "GET /parc : le maitre P4 du garage")
    verifie((isinstance(p["id_libre"], int), p["id_libre"] >= 1, str(p["id_libre"]) in p["ids_pris"]),
            (True, True, False), "GET /parc : id libre, absent des ids pris")
    verifie("SERVEUR-GARAGE-GATEWAY" in p["reseaux"], True, "GET /parc : reseaux dont la passerelle du maitre")
    blocs = {x["id"]: x for x in p["blocs"]}
    verifie(sorted(blocs["ds3231"]), ["aide", "dependances", "id", "libelle", "puces"], "GET /parc : forme d'un bloc")
    verifie((blocs["ds3231"]["dependances"], blocs["ledRGB"]["puces"]), (["i2c"], ["ESP32S3"]),
            "GET /parc : dependances et puces des blocs (RTC -> i2c ; LED RGB S3)")


def test_post_securite(b):
    corps = {"reponses": reponses()}
    verifie(b.requete("POST", "/apercu", corps, entetes={})[0], 403, "POST sans en-tete -> 403")
    verifie(b.requete("POST", "/apercu", corps, entetes={"X-Assistant-Persist": "1", "Origin": "http://evil.example"})[0],
            403, "POST d'une autre origine -> 403")
    verifie(b.requete("POST", "/inconnue", {})[0], 404, "POST route inconnue -> 404")


def test_apercu(b):
    statut, a = b.requete("POST", "/apercu", {"reponses": reponses()})
    verifie((statut, sorted(a)), (200, ["autoexec", "avertissements", "persist", "refus"]), "POST /apercu : forme")
    pers = json.loads(a["persist"])
    verifie((pers["serveur"]["hostname"], pers["serveur"]["rangeExtender"]["id"]), ("PISCINE-GARAGE", 4),
            "apercu : hostname et id")
    verifie(a["persist"].count("***") >= 1 and "demarrage" in a["autoexec"], True, "apercu : mots de passe masques, autoexec")
    _, a2 = b.requete("POST", "/apercu", {"reponses": reponses(nom="bassin")})
    verifie(json.loads(a2["persist"])["serveur"]["hostname"], "BASSIN-GARAGE", "changer le nom change le hostname")
    _, a3 = b.requete("POST", "/apercu", {"reponses": reponses(hostname="MON-HOTE")})
    verifie(json.loads(a3["persist"])["serveur"]["hostname"], "MON-HOTE", "hostname saisi pris en compte")
    _, a4 = b.requete("POST", "/apercu", {"reponses": reponses(role="autonome", maitre="", id=0, reseau1="RESEAU-INCONNU", metiers=[])})
    verifie((a4["persist"] != "", isinstance(a4["refus"], list)), (True, True), "apercu autonome sans metier ni reseau connu : pas d'erreur")
    _, a5 = b.requete("POST", "/apercu", {"reponses": reponses(blocs=["modbusUdp"])})
    verifie(any("modbus" in x for x in a5["refus"]), True, "apercu : dependance non cochee -> refus de coherence")
    statut, e = b.requete("POST", "/apercu", {"reponses": reponses(puce="ESP99")})
    verifie((statut, "ESP99" in e), (400, True), "puce inconnue -> 400 lisible (pas 500)")
    verifie(b.requete("POST", "/apercu", {"reponses": reponses(role="chef")})[0] in (200, 400), True, "role inconnu : pas de 500")
    verifie(b.requete("POST", "/apercu", {"reponses": [1]})[0], 400, "reponses pas un objet -> 400")
    verifie(b.requete("POST", "/apercu", {"reponses": dict(reponses(), vide=1)})[0], 400, "champ inconnu -> 400")
    verifie(b.requete("POST", "/apercu", {"reponses": dict(reponses(), id="x")})[0], 400, "id pas un entier -> 400")
    verifie(b.requete("POST", "/apercu", {"reponses": dict(reponses(), blocs="udp")})[0], 400, "blocs pas une liste -> 400")
    verifie(b.requete("POST", "/apercu", {})[0], 400, "sans reponses -> 400")


def test_prepare_creation(b):
    statut, p = b.requete("POST", "/prepare", {"reponses": reponses()})
    verifie((statut, p["refus"], p["env"], bool(p["empreinte"])), (200, [], tac.ENV, True), "POST /prepare : sans refus, empreinte")
    verifie("***" in p["diff"], True, "prepare : diff masque")
    statut, p0 = b.requete("POST", "/prepare", {"reponses": reponses(metiers=[], squelettes=False)})
    verifie((statut, bool(p0["refus"]), p0["empreinte"]), (200, True, ""), "refus precoce (zero metier) : refus affiches, empreinte vide")
    statut, p1 = b.requete("POST", "/prepare", {"reponses": reponses(reseau1="RESEAU-INCONNU", role="autonome", maitre="", id=0)})
    verifie((statut, any("RESEAU-INCONNU" in x for x in p1["refus"])), (200, True), "reseau inconnu : refus nomme le reseau")
    verifie(b.requete("POST", "/creation", {"reponses": reponses()})[0], 400, "creation sans empreinte -> 400")
    verifie(b.requete("POST", "/creation", {"reponses": reponses(), "empreinte": "0" * 64})[0], 409, "empreinte perimee -> 409")
    b.builds = ["pio run -e x"]
    statut, texte = b.requete("POST", "/creation", {"reponses": reponses(), "empreinte": p["empreinte"]})
    b.builds = []
    verifie((statut, "build" in texte), (409, True), "creation pendant un build -> 409")
    b.builds = None
    verifie(b.requete("POST", "/creation", {"reponses": reponses(), "empreinte": p["empreinte"]})[0], 409,
            "build indetectable -> 409")
    b.builds = []
    r2 = reponses(ip="192.168.0.77")                       # saisie changee apres le diff
    verifie(b.requete("POST", "/creation", {"reponses": r2, "empreinte": p["empreinte"]})[0], 409, "saisie changee apres le diff -> 409")
    statut, c = b.requete("POST", "/creation", {"reponses": reponses(), "empreinte": p["empreinte"]})
    verifie((statut, c.get("cree") if isinstance(c, dict) else c, c.get("env") if isinstance(c, dict) else ""),
            (200, True, tac.ENV), "POST /creation : cree")
    verifie((b.racine / tac.DOSSIER / "_persist.json").is_file(), True, "creation : dossier ecrit dans le depot d'essai")
    verifie(sorted(c["liens"]), ["build", "fichiers"], "creation : liens build et fichiers")
    verifie(tac.ENV in c["resume"], True, "creation : resume")
    verifie(b.requete("POST", "/creation", {"reponses": reponses(), "empreinte": p["empreinte"]})[0], 409,
            "creation une 2e fois -> 409")


def test_interrompues(b):
    verifie(b.requete("POST", "/interrompue/acquitte", {"nom": "../x"})[0], 400, "acquitte nom invalide -> 400")
    verifie(b.requete("POST", "/interrompue/acquitte", {})[0], 400, "acquitte sans nom -> 400")


class Explose:
    def __bool__(self):
        raise OSError("panne simulee de la detection")


def test_erreur_inattendue(b):
    _, p = b.requete("POST", "/prepare", {"reponses": reponses()})
    b.builds = Explose()
    try:
        statut, texte = b.requete("POST", "/creation", {"reponses": reponses(), "empreinte": p["empreinte"]})
        verifie((statut, "panne simulee" in texte), (500, True), "erreur inattendue -> 500 avec le message")
    except (OSError, http.client.HTTPException) as erreur:
        verifie(repr(erreur), "reponse 500", "erreur inattendue -> 500 (connexion coupee)")
    b.builds = []


def valeurs_reelles():
    """Tous les mots de passe distincts du vrai parc (lecture seule), pour les chercher dans les reponses."""
    res = set(tac.secrets_reels())
    for reseau in tac.parc.reseaux(tac.RACINE):
        try:
            res.update(x for x in tac.parc.secrets(tac.RACINE, reseau, reseau).values() if x)
        except ValueError:
            pass
    return sorted(res)


def principal():
    for test in (test_get, test_post_securite, test_apercu, test_prepare_creation, test_interrompues, test_erreur_inattendue):
        with tempfile.TemporaryDirectory() as t:
            os.environ["OUTILS_TASMOTA_DOSSIER"] = os.path.join(t, "outils")    # sauvegardes hors du vrai dossier
            b = Banc(t)
            try:
                test(b)
            except Exception as exc:
                verifie(repr(exc), "pas d'exception", test.__name__)
            finally:
                b.ferme()
    secrets = valeurs_reelles()
    verifie(len(secrets) >= 2, True, f"garde-fou : {len(secrets)} valeurs distinctes de mot de passe a chercher (plusieurs cles partagent la meme)")
    fuites = [i for i, s in enumerate(secrets) if any(s in texte for texte in REPONSES_VUES)]
    verifie((len(REPONSES_VUES) > 30, fuites), (True, []),
            f"AUCUN mot de passe reel dans les {len(REPONSES_VUES)} reponses HTTP (erreurs comprises)")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
