#!/usr/bin/env python3
"""Banc de tapp_envoi.py (Fabrique d'extensions, plan autoexec-mqtt-tapp A7) : un .tapp arrive sous /.extensions/ d'une carte SIMULEE.

Preuve du sous-dossier (HTTP) : build_ota_carte_simulee.Carte imite UfsDirectory et UfsUploadFileOpen (xdrv_50_filesystem.ino) : dossier
courant pose par download=, dossier absent -> « Failed ». MQTT : carte de test_build_ota_mqtt (recoit le chemin de l'ordre `debut`) ; ses
regles de chemin viennent de fsMqtt.be::chemin_valide, recopiees ici et comparees au fichier du depot.
Toute connexion hors de 127.0.0.1 est refusee (garde de test_autoexec_envoi). Aucun vrai broker, aucune vraie carte. Depot temporaire.
Temoins : mutants (TAPP_MUTANT=<dossier>) qui doivent passer KO sur LE test vise. Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_tapp_envoi.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

if os.environ.get("TAPP_MUTANT"):
    sys.path.insert(0, os.environ["TAPP_MUTANT"])
    sys.path.append(str(Path(__file__).resolve().parents[1] / "berry"))     # gen_tapp : le mutant n'est plus a cote de berry/

import test_autoexec_envoi as tae                        # garde les connexions sur 127.0.0.1, cartes simulees
import autoexec_envoi as ae
import build_ota_fs
import build_ota_maitre as bm
import tapp_envoi as te
import tapp_sources as ts
import test_build_ota_mqtt as tm
from build_ota_carte_simulee import Carte
from build_ota_fs import _identite
from test_tapp_web import ECHECS, Serveur, secrets_absents, taa, verifie

ICI = Path(__file__).resolve().parent
ENV, CARTE = taa.ENV, taa.CARTE
NOM = "ext_a"
CHEMIN = f"/.extensions/{NOM}.tapp"
RAPIDE = {"delai_retour": 5.0, "attente_min": 0.0, "sondage": 0.05, "delai_http": 3.0}


def erreur(appel, *args, **kw):
    try:
        appel(*args, **kw)
    except (ValueError, RuntimeError, LookupError) as e:
        return type(e).__name__, str(e)
    return None, ""


def carte_http(hote):
    carte = Carte(coupure=0.2)
    carte.hostname = hote
    ae._adresse = lambda *_: carte.ip
    return carte


def carte_mqtt(hote, topic):
    carte = tae.CarteMqtt(hote, topic, None)
    ae.CLIENT = lambda: tae.ClientFiltre(carte)
    return carte


def prepare(racine, transport="http", builds=(), nom=NOM, env=ENV):
    return te.prepare(racine, env, nom, lambda: list(builds), transport=transport)


def envoie(racine, jeton, transport="http", redemarrer=False, confirme=True, builds=(), nom=NOM, env=ENV):
    return te.envoie(racine, env, nom, jeton, confirme, redemarrer, lambda: list(builds), transport=transport)


def source(racine):
    ts.cree(racine, NOM, "A")
    return ts.fabrique(racine, NOM)


def octets(racine, nom=NOM):
    return (Path(racine) / "data" / "extensions" / f"{nom}.tapp").read_bytes()


def constantes():
    be = (ICI.parents[2] / "data" / "fs" / "fsMqtt.be").read_text(encoding="utf-8")
    verifie(int(re.search(r"static TAILLE_MAX = (\d+)", be).group(1)), te.TAILLE_MAX_MQTT, "TAILLE_MAX_MQTT = TAILLE_MAX de fsMqtt.be")
    verifie(int(re.search(r"static LONGUEUR_MAX = (\d+)", be).group(1)), build_ota_fs.LONGUEUR_MAX, "LONGUEUR_MAX de fsMqtt.be = celui de l'envoi HTTP")
    regle = re.search(r"def chemin_valide\(c\)(.*?)\n    end", be, re.S).group(1)
    for morceau in ('c[0] == "/"', 'c[-1] != "/"', 'string.find(c, "..") < 0'):
        verifie(morceau in regle, True, f"chemin_valide relu : {morceau}")
    verifie((CHEMIN.startswith("/"), ".." in CHEMIN, CHEMIN.endswith("/")), (True, False, False), "/.extensions/<nom>.tapp passe ces regles (un seul point apres le /)")
    with tempfile.TemporaryDirectory() as t:
        for n, attendu in ((31, True), (32, False)):
            rel = f".extensions/{'x' * n}.tapp"
            (Path(t) / rel).parent.mkdir(exist_ok=True)
            (Path(t) / rel).write_bytes(b"x")
            verifie(erreur(build_ota_fs._inventaire, Path(t), [rel])[0] is None, attendu, f"nom de {n} caracteres : {'accepte' if attendu else 'refuse'} par l'envoi HTTP")
    with tempfile.TemporaryDirectory() as t:
        rel = ".extensions/x.tapp"
        (Path(t) / rel).parent.mkdir()
        (Path(t) / rel).write_bytes(b"x")
        verifie(build_ota_fs._inventaire(Path(t), [rel]), ([rel], ["/.extensions"]), "inventaire : le dossier cache est vu, /.extensions a creer")


def http_prepare(racine, hote):
    carte = carte_http(hote)
    r = prepare(racine)
    verifie(sorted(r), ["adresse", "chemin", "hostname_carte", "jeton", "sur_carte", "taille", "transport"], "http prepare : les clefs du contrat")
    verifie((r["adresse"], r["hostname_carte"], r["chemin"], r["sur_carte"], r["taille"]), (carte.ip, hote, CHEMIN, "absent", len(octets(racine))), "http prepare : identite, destination, absent de la carte")
    verifie(carte.requetes("/ufsu?fsz"), [], "http prepare : rien d'envoye")
    carte.dossiers.add("/.extensions")
    carte.flash[CHEMIN] = octets(racine)
    verifie(prepare(racine)["sur_carte"], "identique", "http prepare : fichier identique sur la carte")
    carte.flash[CHEMIN] = b"autre"
    verifie(prepare(racine)["sur_carte"], "different", "http prepare : autre fichier de meme nom sur la carte")
    verifie(carte.flash[CHEMIN], b"autre", "http prepare : ne modifie rien")
    carte.ferme()


def http_envoi(racine, hote):
    """La preuve : le fichier arrive sous /.extensions/, dossier cree par path.mkdir, rien d'autre ne bouge."""
    carte = carte_http(hote)
    ae.REGLAGES_ENVOI.update(RAPIDE)
    persist = carte.flash["/_persist.json"]
    jeton = prepare(racine)["jeton"]
    r = envoie(racine, jeton)
    verifie((r["envoye"], r["chemin"]), (True, CHEMIN), "http envoi : accepte")
    verifie(carte.flash.get(CHEMIN), octets(racine), "http envoi : le .tapp est sous /.extensions/, octet pour octet")
    verifie("/.extensions" in carte.dossiers, True, "http envoi : le dossier cree par Berry")
    verifie([c for _, c in carte.requetes("/ufsd")][-1:], ["/ufsd?dir=0&download=/.extensions"], "http envoi : dossier courant pose avant l'envoi")
    verifie(("/ext_a.tapp" in carte.flash, carte.flash["/_persist.json"]), (False, persist), "http envoi : rien a la racine, persist intact")
    verifie(carte.requetes("Restart"), [], "http envoi : sans redemarrage par defaut")
    jeton = prepare(racine)["jeton"]
    envoie(racine, jeton, redemarrer=True)
    verifie(len(carte.requetes("Restart%201")), 1, "http envoi : Restart 1 seulement sur demande")
    time.sleep(0.3)
    carte.ferme()


def http_esclave(racine, hote):
    """Esclave en IP:port : maitre en Sleep 0 le temps de l'envoi, valeur remise, comme autoexec_envoi."""
    maitre, esclave = Carte(), carte_http(hote)
    maitre.maitre = True
    coupes = []
    vraie_coupe, vraie_jonction = ae.coupe_sleep, ae.joint_par_maitre
    ae.coupe_sleep = lambda m, **_: (coupes.append(m), bm.coupe_sleep(maitre.ip, delai=2.0))[1]
    ae.joint_par_maitre = lambda *a, **k: None
    try:
        jeton = prepare(racine)["jeton"]
        verifie(coupes, [], "esclave : la preparation ne touche pas au Sleep")
        r = envoie(racine, jeton)
        verifie((len(coupes), maitre.sleeps, r["avertissement"]), (1, [0, 50], ""), "esclave IP:port : maitre en Sleep 0 puis valeur remise")
        verifie(esclave.flash.get(CHEMIN), octets(racine), "esclave IP:port : fichier arrive")
    finally:
        ae.coupe_sleep, ae.joint_par_maitre = vraie_coupe, vraie_jonction
        maitre.ferme()
        esclave.ferme()


def mqtt_envoi(racine, hote, topic):
    carte = carte_mqtt(hote, topic)
    ae.REGLAGES_MQTT.update({"delai": 1.0, "attente_morceau": 0.2, "delai_retour": 1.0})
    r = prepare(racine, "mqtt")
    verifie((r["adresse"], r["transport"], r["sur_carte"], r["chemin"]), (f"mqtt:{topic}", "mqtt", "absent", CHEMIN), "mqtt prepare : topic, voie, absent, destination")
    verifie("debut" in carte.ordres, False, "mqtt prepare : rien d'envoye")
    r2 = envoie(racine, r["jeton"], "mqtt")
    verifie((r2["envoye"], carte.fs.get(CHEMIN)), (True, octets(racine)), "mqtt envoi : le .tapp est sous /.extensions/, octet pour octet (ordre debut)")
    verifie(("/ext_a.tapp" in carte.fs, carte.fs["/_persist.json"], "redemarre" in carte.ordres), (False, tm.ANCIEN, False), "mqtt envoi : rien a la racine, persist intact, sans redemarrage")
    verifie(prepare(racine, "mqtt")["sur_carte"], "identique", "mqtt prepare : fichier identique sur la carte")
    carte.fs[CHEMIN] = b"autre"
    verifie(prepare(racine, "mqtt")["sur_carte"], "different", "mqtt prepare : autre fichier de meme nom")
    vrai = ae.build_ota_mqtt.Canal.lit
    ae.build_ota_mqtt.Canal.lit = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("delai depasse"))
    try:
        verifie(prepare(racine, "mqtt")["sur_carte"], "inconnu", "mqtt prepare : lecture impossible (gros fichier) -> presence inconnue, pas un refus")
    finally:
        ae.build_ota_mqtt.Canal.lit = vrai
    jeton = prepare(racine, "mqtt")["jeton"]
    envoie(racine, jeton, "mqtt", redemarrer=True)
    verifie("redemarre" in carte.ordres, True, "mqtt envoi : redemarrage seulement sur demande")
    return carte


def refus_http(racine, hote):
    carte = carte_http(hote)
    fait = lambda: carte.requetes("/ufsu?fsz")
    jeton = prepare(racine)["jeton"]
    n = len(carte.journal)
    for builds, libelle in ((["pio run -e x"], "build en cours"), (None, "build indetectable")):
        b = (lambda: None) if builds is None else (lambda: list(builds))
        verifie(erreur(te.prepare, racine, ENV, NOM, b)[0], "RuntimeError", f"prepare, {libelle} -> refus")
        verifie(erreur(te.envoie, racine, ENV, NOM, jeton, True, False, b)[0], "RuntimeError", f"envoi, {libelle} -> refus")
    verifie(len(carte.journal), n, "build : aucune requete a la carte")
    verifie(erreur(envoie, racine, jeton, confirme=False)[0], "ValueError", "geste non confirme -> refus")
    for valeur in ("oui", 1, None):
        verifie(erreur(envoie, racine, jeton, confirme=valeur)[0], "ValueError", f"confirme {valeur!r} -> refus")
        verifie(erreur(envoie, racine, jeton, redemarrer=valeur)[0], "ValueError", f"redemarrer {valeur!r} -> refus")
    for faux in ("x", "", 5, None, jeton[:-1] + ("0" if jeton[-1] != "0" else "1")):
        verifie(erreur(envoie, racine, faux)[0] in ("RuntimeError", "ValueError"), True, f"jeton {faux!r} -> refus")
    maintenant = ae._maintenant
    ae._maintenant = lambda: maintenant() + ae.VALIDITE + 1
    verifie(erreur(envoie, racine, jeton)[0], "RuntimeError", "jeton de plus de 10 minutes -> refus")
    ae._maintenant = maintenant
    for transport in ("ftp", None, 5, "MQTT"):
        verifie(erreur(prepare, racine, transport)[0], "ValueError", f"transport {transport!r} -> refus")
    verifie(erreur(prepare, racine, env="tasmota32-inconnu-x")[0], "LookupError", "carte inconnue -> refus")
    verifie(erreur(prepare, racine, env="tasmota32s3-base-N16R8")[0], "LookupError", "env de base -> refus")
    verifie(erreur(prepare, racine, env="../x")[0], "ValueError", "env hostile -> refus")
    # autre extension, autre carte : le jeton ne vaut que pour ce qui a ete prepare
    ts.cree(racine, "ext_b", "B")
    ts.fabrique(racine, "ext_b")
    (Path(racine) / "data" / "extensions" / "ext_b.tapp").write_bytes(octets(racine))     # memes octets : seul le nom les distingue
    verifie(erreur(envoie, racine, jeton, nom="ext_b")[0], "RuntimeError", "jeton d'une autre extension -> refus")
    autre = next(c for c in te.cartes(racine) if c != ENV)
    verifie(erreur(envoie, racine, jeton, env=autre)[0], "RuntimeError", "jeton d'une autre carte -> refus")
    verifie(erreur(envoie, racine, jeton, "mqtt")[0] is not None, True, "jeton de la voie HTTP sur la voie MQTT -> refus")
    # nouvelle fabrication : le fichier a change
    d = Path(racine) / "data" / "extensions" / NOM
    tapp = d.parent / f"{NOM}.tapp"
    ts.ecrit_manifeste(racine, NOM, {"name": "Autre", "version": "2", "description": "", "min_tasmota": "1"})
    time.sleep(0.01)
    ts.fabrique(racine, NOM)
    t, msg = erreur(envoie, racine, jeton)
    verifie((t, "preparation" in msg), ("RuntimeError", True), "nouvelle fabrication apres la preparation -> refus, relancer")
    jeton = prepare(racine)["jeton"]
    # fabrique plus ancien que ses sources, ou absent
    avant = (d / "autoexec.be").stat().st_mtime_ns
    futur = tapp.stat().st_mtime_ns + 2_000_000_000
    os.utime(d / "autoexec.be", ns=(futur, futur))
    for appel, libelle in ((lambda: prepare(racine), "prepare"), (lambda: envoie(racine, jeton), "envoi")):
        t, msg = erreur(appel)
        verifie((t, "abriquer" in msg), ("RuntimeError", True), f"{libelle} : .tapp plus ancien que ses sources -> « Fabriquer d'abord »")
    os.utime(d / "autoexec.be", ns=(avant, avant))
    jeton = prepare(racine)["jeton"]
    garde = tapp.read_bytes()
    tapp.unlink()
    for appel, libelle in ((lambda: prepare(racine), "prepare"), (lambda: envoie(racine, jeton), "envoi")):
        t, msg = erreur(appel)
        verifie((t, "abriquer" in msg), ("RuntimeError", True), f"{libelle} : .tapp absent -> « Fabriquer d'abord »")
    tapp.write_bytes(garde)
    # identite
    jeton = prepare(racine)["jeton"]
    carte.hostname = "AUTRE-CARTE"
    t, msg = erreur(prepare, racine)
    verifie((t, "AUTRE-CARTE" in msg), ("RuntimeError", True), "http prepare : nom d'hote different -> refus")
    verifie(erreur(envoie, racine, jeton)[0], "RuntimeError", "http envoi : identite revue a l'envoi -> refus")
    carte.hostname = ""
    verifie(erreur(prepare, racine)[0], "RuntimeError", "http prepare : nom d'hote illisible -> refus")
    carte.hostname = hote
    verifie(fait(), [], "refus http : rien d'envoye")
    jeton = prepare(racine)["jeton"]
    reponses = iter([[], ["pio run -e x"]])
    t, msg = erreur(te.envoie, racine, ENV, NOM, jeton, True, False, lambda: next(reponses))
    verifie((t, "build" in msg, fait()), ("RuntimeError", True, []), "http envoi : build recontrole apres la lecture de la carte")
    carte.ferme()
    with tae.socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        ferme = f"127.0.0.1:{s.getsockname()[1]}"     # port ferme : personne n'ecoute
    ae._adresse = lambda *_: ferme
    t, msg = erreur(prepare, racine)
    verifie((t, "injoignable" in msg), ("RuntimeError", True), "http : carte muette -> refus clair")
    ae._adresse = lambda *_: ""
    t, msg = erreur(prepare, racine)
    verifie((t, "adresse" in msg), ("RuntimeError", True), "http : pas d'adresse -> refus clair, dit quoi faire")
    # sous-dossier refuse si la carte refuse
    carte = carte_http(hote)
    carte.echec_fichier = f"{NOM}.tapp"
    jeton = prepare(racine)["jeton"]
    t, msg = erreur(envoie, racine, jeton)
    verifie((t, "refusé" in msg, CHEMIN in carte.flash), ("RuntimeError", True, False), "http : la carte refuse le fichier -> erreur, pas de « envoye »")
    carte.ferme()


def refus_mqtt(racine, hote, topic, carte):
    jeton = prepare(racine, "mqtt")["jeton"]
    n = carte.ordres.count("debut")
    carte.hote = "AUTRE-CARTE"
    verifie(erreur(prepare, racine, "mqtt")[0], "RuntimeError", "mqtt prepare : nom d'hote different -> refus")
    verifie(erreur(envoie, racine, jeton, "mqtt")[0], "RuntimeError", "mqtt envoi : identite revue a l'envoi -> refus")
    carte.hote = hote
    carte.muette = True
    t, msg = erreur(prepare, racine, "mqtt")
    verifie((t, "Status 5" in msg), ("RuntimeError", True), "mqtt : carte muette -> refus clair")
    carte.muette = False
    carte.sans_fsmqtt = True
    t, msg = erreur(prepare, racine, "mqtt")
    verifie((t, "fsMqtt.be" in msg), ("RuntimeError", True), "mqtt : fsMqtt absent -> refus clair, dit quoi faire")
    carte.sans_fsmqtt = False
    verifie(erreur(envoie, racine, jeton, "http")[0] is not None, True, "jeton de la voie MQTT sur la voie HTTP -> refus")
    # 1 Mo : limite de fsMqtt.be
    d = Path(racine) / "data" / "extensions" / NOM
    (d / "gros.bin").write_bytes(b"x" * (te.TAILLE_MAX_MQTT + 1))
    ts.fabrique(racine, NOM)
    t, msg = erreur(prepare, racine, "mqtt")
    verifie((t, "Mo" in msg, "HTTP" in msg or "Wi-Fi" in msg), ("RuntimeError", True, True), "mqtt : archive de plus de 1 Mo -> refus, propose la voie HTTP")
    t, msg = erreur(envoie, racine, jeton, "mqtt")
    verifie((t, "Mo" in msg), ("RuntimeError", True), "mqtt envoi : archive de plus de 1 Mo -> refus")
    verifie(carte.ordres.count("debut"), n, "refus mqtt : rien d'envoye")
    (d / "gros.bin").unlink()
    ts.fabrique(racine, NOM)


def verrous(racine, hote):
    """Une lecture de carte (lente) ne bloque ni le controle ni la fabrication ; une seule a la fois par carte, sans gener une autre carte."""
    s = Serveur(racine)
    carte = carte_http(hote)
    vrai = ae._commande_repetee
    actifs, maxi, garde = {}, {}, threading.Lock()

    def lente(adresse, *a, **k):
        with garde:
            actifs[adresse] = actifs.get(adresse, 0) + 1
            maxi[adresse] = max(maxi.get(adresse, 0), actifs[adresse])
        time.sleep(2.0)
        try:
            return vrai(adresse, *a, **k)
        finally:
            with garde:
                actifs[adresse] -= 1
    ae._commande_repetee = lente
    resultats = []

    def prepare_http():
        resultats.append(s.requete("POST", "/envoi/prepare", {"nom": NOM, "env": ENV, "transport": "http"})[0])
    try:
        fils = [threading.Thread(target=prepare_http) for _ in range(2)]
        for t in fils:
            t.start()
        time.sleep(0.3)
        debut = time.monotonic()
        verifie(s.requete("POST", "/verifie", {"nom": NOM})[0], 200, "pendant une lecture de carte : le controle repond")
        verifie(time.monotonic() - debut < 3.0, True, "le controle n'attend pas la carte lente")
        debut = time.monotonic()
        verifie(s.requete("POST", "/fabrique", {"nom": NOM})[0], 200, "pendant une lecture de carte : la fabrication repond")
        verifie(time.monotonic() - debut < 3.0, True, "la fabrication n'attend pas la carte lente")
        for t in fils:
            t.join()
        verifie((resultats, maxi.get(carte.ip)), ([200, 200], 1), "deux lectures de la meme carte : l'une apres l'autre")
    finally:
        ae._commande_repetee = vrai
        carte.ferme()
        s.ferme()


def routes(racine, hote, topic, carte_m):
    s = Serveur(racine, lambda: [])
    carte = carte_http(hote)
    try:
        st, r = s.requete("POST", "/envoi/prepare", {"nom": NOM, "env": ENV, "transport": "http"})
        verifie((st, r["hostname_carte"], r["chemin"]), (200, hote, CHEMIN), "POST /envoi/prepare : identite et destination")
        for route in ("/envoi/prepare", "/envoi"):
            verifie(s.requete("POST", route, {"nom": NOM, "env": ENV, "transport": "ftp", "jeton": "x", "confirme": True, "redemarrer": False})[0], 400, f"POST {route}, transport inconnu -> 400")
            verifie(s.requete("POST", route, {"nom": NOM, "env": "tasmota32-inconnu-x", "transport": "http", "jeton": "x", "confirme": True, "redemarrer": False})[0], 404, f"POST {route}, carte inconnue -> 404")
        corps = {"nom": NOM, "env": ENV, "transport": "http", "jeton": r["jeton"], "redemarrer": False}
        verifie(s.requete("POST", "/envoi", corps)[0], 400, "POST /envoi sans confirme -> 400")
        verifie(carte.requetes("/ufsu?fsz"), [], "POST /envoi sans confirme : rien d'envoye")
        st, e = s.requete("POST", "/envoi", dict(corps, confirme=True))
        verifie((st, e["envoye"], CHEMIN in carte.flash), (200, True, True), "POST /envoi confirme : le fichier arrive")
        st, m = s.requete("POST", "/envoi/prepare", {"nom": NOM, "env": ENV, "transport": "mqtt"})
        verifie((st, m["adresse"]), (200, f"mqtt:{topic}"), "POST /envoi/prepare par MQTT : le topic, pas d'IP")
        persist = (Path(racine) / CARTE / "_persist.json").read_text(encoding="utf-8")
        verifie(_identite(persist)[0] in json.dumps(r), True, "la reponse porte le nom d'hote")
        for cle in ("ssid", "password", "mqtt_pass"):
            verifie(cle in json.dumps(r).lower(), False, f"la reponse ne porte pas de champ {cle}")
    finally:
        carte.ferme()
        s.ferme()
    b = Serveur(racine, lambda: ["pio run -e x"])
    try:
        st, msg = b.requete("POST", "/envoi/prepare", {"nom": NOM, "env": ENV, "transport": "http"})
        verifie((st, "build" in str(msg)), (409, True), "POST /envoi/prepare pendant un build -> 409")
    finally:
        b.ferme()


def banc():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(tmp) / "donnees")
        racine = taa.depot(tmp)
        hote, topic = _identite((racine / CARTE / "_persist.json").read_text(encoding="utf-8"))
        sleep = Carte()                                  # les adresses du banc portent un port : le maitre simule recoit les Sleep
        ae.joint_par_maitre = lambda *a, **k: None
        ae.coupe_sleep = lambda m, **_: bm.coupe_sleep(sleep.ip, delai=2.0)
        constantes()
        source(racine)
        http_prepare(racine, hote)
        http_envoi(racine, hote)
        http_esclave(racine, hote)
        carte_m = mqtt_envoi(racine, hote, topic)
        refus_http(racine, hote)
        refus_mqtt(racine, hote, topic, carte_m)
        verrous(racine, hote)
        routes(racine, hote, topic, carte_m)
        secrets_absents()


MUTANTS = [
    ("tapp_envoi.py", "geste non exige", "if confirme is not True:", "if False:", "geste non confirme -> refus"),
    ("tapp_envoi.py", "build ignore a la preparation", "    ae.controle_builds(builds_en_cours)\n    octets = _archive", "    octets = _archive", "prepare, build en cours -> refus"),
    ("tapp_envoi.py", "build non recontrole a l'envoi", "    ae.controle_builds(builds_en_cours)\n    with tempfile", "    with tempfile", "http envoi : build recontrole apres la lecture de la carte"),
    ("tapp_envoi.py", "limite MQTT ignoree", "if transport == \"mqtt\" and len(octets) > TAILLE_MAX_MQTT:", "if False:", "mqtt : archive de plus de 1 Mo -> refus, propose la voie HTTP"),
    ("tapp_envoi.py", "identite non revue a l'envoi", "    ae.lit_carte(racine, env, adresse, transport, None)\n", "", "http envoi : identite revue a l'envoi -> refus"),
    ("tapp_envoi.py", "jeton sans l'extension", 'f"{env}|{nom}"', "env", "jeton d'une autre extension -> refus"),
    ("tapp_envoi.py", "jeton non compare", "if not hmac.compare_digest(", "if False and not hmac.compare_digest(", "nouvelle fabrication apres la preparation -> refus, relancer"),
    ("tapp_envoi.py", "racine au lieu du sous-dossier", 'rel = f".extensions/{nom}.tapp"\n        cible = Path(dossier) / rel\n        cible.parent.mkdir()', 'rel = f"{nom}.tapp"\n        cible = Path(dossier) / rel', "http envoi : le .tapp est sous /.extensions/, octet pour octet"),
    ("tapp_envoi.py", "redemarrage force", "redemarrer)\n", "True)\n", "http envoi : sans redemarrage par defaut"),
    ("tapp_envoi.py", "sans Sleep 0 du maitre", "ae.avec_sleep_coupe(adresse, transport,", "(lambda a, t, f: (f(), \"\"))(adresse, transport,", "esclave IP:port : maitre en Sleep 0 puis valeur remise"),
    ("tapp_sources.py", "fabrique perime accepte", "if not etat[\"a_jour\"]:", "if False:", "prepare : .tapp plus ancien que ses sources -> « Fabriquer d'abord »"),
    ("tapp_web.py", "un seul verrou pour tout", "with verrou_carte(env):", "with ts.VERROU:", "le controle n'attend pas la carte lente"),
    ("tapp_web.py", "pas de verrou de carte", "with verrou_carte(env):", "if True:", "deux lectures de la meme carte : l'une apres l'autre"),
]


def temoins():
    for module, nom, ancien, nouveau, libelle in MUTANTS:
        source_m = (ICI / module).read_text(encoding="utf-8")
        if not verifie(source_m.count(ancien) >= 1, True, f"mutant {nom} : motif present"):
            continue
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / module).write_text(source_m.replace(ancien, nouveau), encoding="utf-8")
            p = subprocess.run([sys.executable, str(Path(__file__).resolve())], capture_output=True, text=True, encoding="utf-8",
                               env=dict(os.environ, TAPP_MUTANT=tmp, PYTHONIOENCODING="utf-8"))
        verifie(f"KO   {libelle}" in p.stdout, True, f"temoin rouge : {nom} tue par « {libelle} »")


if __name__ == "__main__":
    banc()
    if not os.environ.get("TAPP_MUTANT") and "--sans-temoin" not in sys.argv:
        temoins()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1 if ECHECS else 0)
