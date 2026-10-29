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
import assistant_persist_modele as apm
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
    def __init__(self, t, ajouts=None, racine=None):
        self.racine = racine or tac.depot(t)
        self.ajouts = ajouts or []
        self.builds = []
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        acces = acces_web.Acces(self.port, True, "Assistant persist")
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port),
                                           apw.fabrique_gestionnaire(acces, self.racine, lambda: self.builds,
                                                                   lambda: apw.etat_modele(self.racine, self.ajouts)))
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
    statut, etat = b.requete("GET", "/modele/etat")
    verifie((statut, etat), (200, {"ajouts": [], "disparues": [], "divergentes": {}, "a_completer": [], "erreur": "", "valeurs": {}}),
            "GET /modele/etat : le contrat (modele relu, parc couvert)")
    verifie(b.requete("GET", "/interrompues"), (200, {"interrompues": []}), "GET /interrompues : rien")
    verifie(b.requete("GET", "/nulle-part")[0], 404, "GET route inconnue -> 404")
    statut, p = b.requete("GET", "/parc")
    verifie(statut, 200, "GET /parc : 200")
    reel = apm.ecarts(tac.RACINE, apm.charge_modele(tac.RACINE))
    verifie(reel["disparues"], [], "VRAI parc : aucune cle disparue (le bandeau ne reste pas affiche en permanence)")
    verifie(sorted(p), sorted(["puces", "bases", "base_defaut", "maitres", "ids_pris", "id_libre", "reseaux", "blocs", "erreur_modele",
                                      "broches", "erreur_broches", "groupes", "cartes"]),
            "GET /parc : les clefs du contrat")
    verifie(([g["id"] for g in p["groupes"]], p["broches"]["ESP32S3"][-1], "relai" in [g["singulier"] for g in p["groupes"]]),
            (["boutons", "interrupteurs", "relais", "capteurs", "compteurs", "thermometres", "analogiques"], 48, True),
            "GET /parc : groupes d'elements (gabarit, singulier) et broches de chaque puce")
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


def test_hote(b):
    """DNS rebinding : un Host etranger depuis ce PC est refuse (GET et POST), le Host local passe."""
    for chemin in ("/", "/parc", "/modele/etat", "/interrompues"):
        verifie(b.requete("GET", chemin, entetes={"Host": "evil.example"})[0], 403, f"hote : GET {chemin} Host etranger -> 403")
    verifie(b.requete("POST", "/apercu", {}, entetes={"X-Assistant-Persist": "1", "Host": "evil.example"})[0], 403,
            "hote : POST Host etranger -> 403")
    for hote in (f"127.0.0.1:{b.port}", f"localhost:{b.port}"):
        verifie(b.requete("GET", "/parc", entetes={"Host": hote})[0], 200, f"hote : GET /parc Host {hote} -> 200")


def test_demarrage_robuste(b):
    """Une exception autre qu'OSError a la fusion (ImportError...) reporte la fusion et reste lisible dans /modele/etat."""
    vrai = apm.fusionne_nouvelles
    def casse(*a):
        raise ImportError("module absent (essai)")
    apm.fusionne_nouvelles = casse
    try:
        ajouts, erreur = apw.demarre_sur(b.racine, lambda: [])
    finally:
        apm.fusionne_nouvelles = vrai
    verifie((ajouts, "module absent" in erreur), ([], True), "demarrage : ImportError rattrapee, message garde")
    verifie("module absent" in apw.etat_modele(b.racine, ajouts, erreur)["erreur"], True, "demarrage : message dans /modele/etat.erreur")


def test_post_securite(b):
    corps = {"reponses": reponses()}
    verifie(b.requete("POST", "/apercu", corps, entetes={})[0], 403, "POST sans en-tete -> 403")
    verifie(b.requete("POST", "/apercu", corps, entetes={"X-Assistant-Persist": "1", "Origin": "http://evil.example"})[0],
            403, "POST d'une autre origine -> 403")
    verifie(b.requete("POST", "/inconnue", {})[0], 404, "POST route inconnue -> 404")


def GROUPE_RELAIS(b):
    return next(g for g in b.requete("GET", "/parc")[1]["groupes"] if g["id"] == "relais")


def test_broches_illisibles(b):
    fichier = b.racine / "data/fs/configGlobal.be"
    texte = fichier.read_text(encoding="utf-8", errors="replace")
    fichier.write_text(texte.replace('== "ESP32S3")', '== "ESP32S3x")'), encoding="utf-8")
    ape_cache = __import__("assistant_persist_elements")._gpio_par_puce
    ape_cache.cache_clear()
    statut, p = b.requete("GET", "/parc")
    verifie((statut, sorted(p.get("erreur_broches", {})), p["broches"].get("ESP32S3"), len(p["broches"]["ESP32"]) > 0),
            (200, ["ESP32S3"], [], True), "configGlobal.be sans branche S3 : /parc repond 200, erreur_broches nomme la puce")
    verifie("configGlobal.be" in p["erreur_broches"]["ESP32S3"], True, "erreur_broches : nomme data/fs/configGlobal.be")
    _, a = b.requete("POST", "/apercu", {"reponses": dict(reponses(), elements={"relais": [{"nom": "R", "pin": 6, "activation": "ON"}]})})
    verifie(any("configGlobal.be" in x for x in a["refus"]), True, "apercu : element actif refuse avec le message, sans 500")


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
    relais = [dict(g["gabarit"], pin=p, nom=f"R{p}") for g in [GROUPE_RELAIS(b)] for p in (6, 7)]
    _, a6 = b.requete("POST", "/apercu", {"reponses": dict(reponses(), elements={"relais": relais})})
    verifie((list(json.loads(a6["persist"])["modules"]["piscine"]["environnement"]["relais"]), a6["refus"]),
            (["relai1", "relai2"], []), "apercu : 2 relais envoyes -> relai1, relai2 dans le persist, aucun refus")
    _, a7 = b.requete("POST", "/apercu", {"reponses": dict(reponses(), elements={"relais": [relais[0], dict(relais[0], nom="Autre")]})})
    verifie(any("broche 6" in x for x in a7["refus"]), True, "apercu : broche en double -> refus")
    for faux in ({"relais": {}}, {"voitures": []}, {"relais": [1]}, []):
        verifie(b.requete("POST", "/apercu", {"reponses": dict(reponses(), elements=faux)})[0], 400, f"elements de forme fausse {faux!r} -> 400")
    verifie(b.requete("POST", "/apercu", {"reponses": dict(reponses(), elements_groupe={"relais": []})})[0], 400,
            "elements_groupe : objet par groupe attendu -> 400")


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


def test_modification_suppression(b):
    """A6 : /parc.cartes, /env, /modification*, /suppression* sur une carte creee dans le depot d'essai."""
    _, p = b.requete("POST", "/prepare", {"reponses": reponses()})
    b.requete("POST", "/creation", {"reponses": reponses(), "empreinte": p["empreinte"]})
    cartes = b.requete("GET", "/parc")[1].get("cartes", [])
    verifie((tac.ENV in [c["env"] for c in cartes], sorted(cartes[0]) if cartes else None), (True, ["dossier", "env", "puce"]),
            "GET /parc : cartes (env, dossier, puce)")
    statut, e = b.requete("GET", "/env?nom=" + tac.ENV)
    verifie((statut, e.get("env") if isinstance(e, dict) else e, sorted(e.get("reponses", {})) == sorted(reponses()) if isinstance(e, dict) else None),
            (200, tac.ENV, True), "GET /env : reponses relues de la carte")
    verifie(b.requete("GET", "/env?nom=tasmota32s3-nulle-part")[0], 404, "GET /env : env inconnu -> 404")
    verifie(b.requete("GET", "/env")[0], 400, "GET /env : sans nom -> 400")
    rep = e["reponses"] if isinstance(e, dict) else reponses()
    # modification
    statut, m = b.requete("POST", "/modification/prepare", {"env": tac.ENV, "reponses": rep})
    verifie((statut, m.get("vide") if isinstance(m, dict) else m), (200, True), "modification/prepare : aucun ecart -> vide")
    verifie(b.requete("POST", "/modification", {"env": tac.ENV, "reponses": rep, "empreinte": m.get("empreinte", "x") if isinstance(m, dict) else "x"})[0],
            400, "modification sans ecart -> 400 (aucun changement)")
    neuf = dict(rep, ip="192.168.0.77")
    statut, m = b.requete("POST", "/modification/prepare", {"env": tac.ENV, "reponses": neuf})
    verifie((statut, m.get("vide"), bool(m.get("empreinte")), "chemins" in m, "192.168.0.77" in m.get("diff", "")),
            (200, False, True, True, True), "modification/prepare : ecart, empreinte, chemins, diff")
    verifie(b.requete("POST", "/modification/prepare", {"env": "tasmota32s3-nulle-part", "reponses": neuf})[0], 404, "modification/prepare : env inconnu -> 404")
    verifie(b.requete("POST", "/modification/prepare", {"env": tac.ENV})[0], 400, "modification/prepare : sans reponses -> 400")
    verifie(b.requete("POST", "/modification/prepare", {"reponses": neuf})[0], 400, "modification/prepare : sans env -> 400")
    verifie(b.requete("POST", "/modification/prepare", {"env": tac.ENV, "reponses": neuf}, entetes={})[0], 403, "modification/prepare sans en-tete -> 403")
    verifie(b.requete("POST", "/modification", {"env": tac.ENV, "reponses": neuf})[0], 400, "modification sans empreinte -> 400")
    verifie(b.requete("POST", "/modification", {"env": tac.ENV, "reponses": neuf, "empreinte": "0" * 64})[0], 409, "modification : empreinte perimee -> 409")
    b.builds = ["pio run -e x"]
    verifie(b.requete("POST", "/modification", {"env": tac.ENV, "reponses": neuf, "empreinte": m["empreinte"]})[0], 409, "modification pendant un build -> 409")
    b.builds = []
    statut, ok = b.requete("POST", "/modification", {"env": tac.ENV, "reponses": neuf, "empreinte": m["empreinte"]})
    verifie((statut, ok.get("modifie") if isinstance(ok, dict) else ok), (200, True), "POST /modification : ecrit")
    verifie("192.168.0.77" in (b.racine / tac.DOSSIER / "_persist.json").read_text(encoding="utf-8"), True, "modification : persist de la carte change")
    # IndexError dans une route GET : 500, pas un faux 404
    vrai = apw.apm2.charge_env
    def casse(*a):
        raise IndexError("liste vide (essai)")
    apw.apm2.charge_env = casse
    try:
        verifie(b.requete("GET", "/env?nom=" + tac.ENV)[0], 500, "GET /env : IndexError -> 500 (pas 404)")
    finally:
        apw.apm2.charge_env = vrai
    # suppression reservee aux cartes du parc
    base = next(e for e in b.requete("GET", "/parc")[1]["bases"]["ESP32S3"])
    avant = (b.racine / "platformio_tasmota_cenv.ini").read_bytes()
    for route in ("/suppression/prepare", "/suppression"):
        for env in (base, "tasmota32s3-nulle-part"):
            statut, msg = b.requete("POST", route, {"env": env, "empreinte": "0" * 64})
            verifie((statut, "7800" in msg), (404, True), f"{route} : {'base' if env == base else 'env inconnu'} -> 404 renvoyant a la page 7800")
    verifie((b.racine / "platformio_tasmota_cenv.ini").read_bytes(), avant, "suppression refusee : cenv intact")
    # suppression
    statut, s =b.requete("POST", "/suppression/prepare", {"env": tac.ENV})
    verifie((statut, s.get("refus"), bool(s.get("empreinte")), s.get("dossier_sauvegarde")), (200, [], True, tac.DOSSIER + "-sauvegarde"),
            "suppression/prepare : empreinte, dossier -sauvegarde")
    el = s.get("elements", [])
    verifie((isinstance(el, list) and len(el) >= 3, any(tac.DOSSIER + "-sauvegarde" in x for x in el), any(tac.ENV in x for x in el)),
            (True, True, True), "suppression/prepare : elements lisibles (cenv, .h, dossier)")
    verifie(b.requete("POST", "/suppression/prepare", {"env": "tasmota32s3-nulle-part"})[0], 404, "suppression/prepare : env inconnu -> 404")
    verifie(b.requete("POST", "/suppression/prepare", {})[0], 400, "suppression/prepare : sans env -> 400")
    verifie(b.requete("POST", "/suppression/prepare", {"env": tac.ENV}, entetes={})[0], 403, "suppression/prepare sans en-tete -> 403")
    verifie(b.requete("POST", "/suppression", {"env": tac.ENV})[0], 400, "suppression sans empreinte -> 400")
    verifie(b.requete("POST", "/suppression", {"env": tac.ENV, "empreinte": "0" * 64})[0], 409, "suppression : empreinte perimee -> 409")
    b.builds = ["pio run -e x"]
    verifie(b.requete("POST", "/suppression", {"env": tac.ENV, "empreinte": s["empreinte"]})[0], 409, "suppression pendant un build -> 409")
    b.builds = []
    statut, d = b.requete("POST", "/suppression", {"env": tac.ENV, "empreinte": s["empreinte"]})
    verifie((statut, d.get("supprime") if isinstance(d, dict) else d), (200, True), "POST /suppression : supprime")
    verifie(((b.racine / tac.DOSSIER).exists(), (b.racine / (tac.DOSSIER + "-sauvegarde")).is_dir()), (False, True), "suppression : dossier renomme")
    verifie((("[env:" + tac.ENV + "]") in (b.racine / "platformio_tasmota_cenv.ini").read_text(encoding="utf-8"),
             tac.ENV in [c["env"] for c in b.requete("GET", "/parc")[1]["cartes"]]), (False, False), "suppression : section du cenv retiree, carte disparue de /parc")


def echange_brut(b, entetes):
    """Requete POST ecrite a la main (http.client refuse un Content-Length negatif) : ligne d'etat de la reponse."""
    corps = b'{"reponses": {}}'
    requete = "POST /apercu HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nX-Assistant-Persist: 1\r\n%s\r\n\r\n" % (b.port, entetes)
    with socket.create_connection(("127.0.0.1", b.port), timeout=10) as s:
        s.sendall(requete.encode("ascii") + corps)
        donnees = b""
        try:
            while b"\r\n" not in donnees:
                bloc = s.recv(4096)
                if not bloc:
                    break
                donnees += bloc
        except OSError:
            pass
    return donnees.split(b"\r\n", 1)[0].decode("latin-1")


def test_content_length(b):
    """Ruling 11 (2) : un Content-Length negatif ou non entier est refuse en 400, sans attendre un corps."""
    for entete, libelle in (("Content-Length: -5", "negatif"), ("Content-Length: abc", "non entier")):
        verifie(" 400 " in echange_brut(b, entete), True, f"Content-Length {libelle} -> 400")
    verifie(" 413 " in echange_brut(b, "Content-Length: 99999999"), True, "Content-Length enorme -> 413 (inchange)")
    verifie(b.requete("POST", "/apercu", {"reponses": reponses()})[0], 200, "le serveur repond encore apres ces refus")


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
    for test in (test_get, test_hote, test_demarrage_robuste, test_post_securite, test_broches_illisibles, test_apercu, test_prepare_creation, test_modification_suppression, test_content_length, test_interrompues, test_erreur_inattendue):
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
