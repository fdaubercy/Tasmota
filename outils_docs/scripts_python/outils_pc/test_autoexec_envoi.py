#!/usr/bin/env python3
"""Banc d'autoexec_envoi.py (plan autoexec-bat, A7) : envoi OTA de l'autoexec.bat du depot a sa carte.

Carte SIMULEE (build_ota_carte_simulee.Carte, 127.0.0.1, port libre) ; depot temporaire (test_assistant_persist_autoexec
.depot : autoexec.bat ecrit avec un mot de passe INVENTE) ; sauvegardes dans OUTILS_TASMOTA_DOSSIER temporaire. Toute
connexion hors de 127.0.0.1 est refusee par le banc lui-meme (socket.create_connection garde) : jamais de vraie carte.
Temoins : des mutants du module (copie modifiee en dossier temporaire, banc relance avec AUTOEXEC_MUTANT=<dossier>)
doivent rendre le banc ROUGE. Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_autoexec_envoi.py
"""
import functools
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if os.environ.get("AUTOEXEC_MUTANT"):
    sys.path.insert(0, os.environ["AUTOEXEC_MUTANT"])

_connexion = socket.create_connection


def _locale(adresse, *args, **kw):
    if adresse[0] not in ("127.0.0.1", "localhost"):
        raise OSError(f"banc : connexion vers {adresse[0]} refusee (carte simulee seulement)")
    return _connexion(adresse, *args, **kw)


socket.create_connection = _locale

import autoexec_envoi as ae
import build_envs
import build_ota_maitre as bm
import fichiers_berry_sauvegarde as fbs
import test_assistant_persist_autoexec as taa
from build_ota_carte_simulee import Carte
from build_ota_fs import _identite

ICI = Path(__file__).resolve().parent
ENV, CARTE, MDP, FICHIER, ROUGES = taa.ENV, taa.CARTE, taa.MDP, taa.FICHIER.encode("utf-8"), taa.ROUGES
SUR_CARTE = f"Backlog SSId1 ReseauInvente; Password1 {MDP}\nWebLog 2\n".encode("utf-8")
ESCLAVE = "tasmota32s3-garage-capteurs-cuve-modbus"
RAPIDE = {"delai_retour": 5.0, "attente_min": 0.0, "sondage": 0.05, "delai_http": 3.0}
ECHECS = []
JOINTS = []
ADRESSE = [""]
COURANTE = [None]                      # carte simulee en service : joint_par_maitre note ce qu'elle a deja recu


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def erreur(appel, *args, **kw):
    """Type d'exception levee (None si aucune) et son message."""
    try:
        appel(*args, **kw)
    except (ValueError, RuntimeError, LookupError) as e:
        return type(e).__name__, str(e)
    return None, ""


def prepare(racine, builds=()):
    return ae.prepare(racine, ENV, lambda: list(builds))


def envoie(racine, jeton, rouges=ROUGES, redemarrer=False, builds=()):
    return ae.envoie(racine, ENV, jeton, rouges, redemarrer, lambda: list(builds))


def nouvelle_carte(hostname, fichier=SUR_CARTE):
    carte = Carte(coupure=0.2)
    carte.hostname = hostname
    if fichier is not None:
        carte.flash["/autoexec.bat"] = fichier
    ADRESSE[0], COURANTE[0] = carte.ip, carte
    return carte


def envois(carte):
    return carte.requetes("/ufsu?fsz")


def adresse(racine):
    attendu = {e.nom: e.ip for e in build_envs.liste_envs(racine)}
    verifie(ae._adresse(racine, ENV), attendu[ENV], "adresse : celle de la page build (build_envs.liste_envs)")
    verifie(":" in ae._adresse(racine, ESCLAVE), True, "adresse d'un esclave du range extender : IP:port du maitre")
    verifie(ae._adresse(racine, "tasmota32-nulle-part"), "", "adresse d'un env inconnu : vide")


def preparation(racine, hote):
    carte = nouvelle_carte(hote)
    r = prepare(racine)
    verifie(sorted(r), ["adresse", "ecart", "hostname_carte", "jeton", "sur_carte"], "prepare : les clefs du contrat")
    verifie((r["adresse"], r["hostname_carte"], r["ecart"]), (carte.ip, hote, True), "prepare : adresse, nom d'hote, ecart vu")
    verifie((MDP in json.dumps(r), r["sur_carte"].count("***"), "WebLog 2" in r["sur_carte"]), (False, 1, True),
            "prepare : fichier de la carte rendu MASQUE")
    verifie(JOINTS[-1:], [(carte.ip, 0)], "prepare : IP:port -> joint_par_maitre AVANT toute requete a la carte")
    verifie(carte.requetes("Status%205")[:1], [("GET", "/cm?cmnd=Status%205")], "prepare : Status 5 demande")
    verifie(envois(carte), [], "prepare : rien d'envoye")
    carte.flash["/autoexec.bat"] = FICHIER
    verifie(prepare(racine)["ecart"], False, "prepare : fichier de la carte identique -> pas d'ecart")
    del carte.flash["/autoexec.bat"]
    r = prepare(racine)
    verifie((r["sur_carte"], r["ecart"]), (None, True), "prepare : carte sans autoexec.bat -> sur_carte None")
    carte.ferme()


def identite(racine, hote):
    carte = nouvelle_carte(hote)
    jeton = prepare(racine)["jeton"]
    carte.hostname = "AUTRE-CARTE"
    verifie(erreur(prepare, racine)[0], "RuntimeError", "identite : nom d'hote different -> prepare refuse")
    verifie(erreur(envoie, racine, jeton)[0], "RuntimeError", "identite : nom d'hote different -> envoi refuse")
    carte.hostname = ""
    verifie(erreur(prepare, racine)[0], "RuntimeError", "identite : nom d'hote illisible -> refus")
    verifie((envois(carte), carte.flash["/autoexec.bat"]), ([], SUR_CARTE), "identite : rien d'envoye")
    carte.ferme()


def injoignable(racine, hote):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        ADRESSE[0] = f"127.0.0.1:{s.getsockname()[1]}"            # port ferme : personne n'ecoute
    t, msg = erreur(prepare, racine)
    verifie((t, "injoignable" in msg), ("RuntimeError", True), "carte injoignable -> erreur claire")
    ADRESSE[0] = ""
    t, msg = erreur(prepare, racine)
    verifie((t, "adresse" in msg), ("RuntimeError", True), "pas d'adresse OTA -> erreur claire")
    maitre, esclave = Carte(), nouvelle_carte(hote)
    ae.joint_par_maitre = functools.partial(bm.joint_par_maitre, maitre=maitre.ip, delai=2.0)
    try:
        t, msg = erreur(prepare, racine)
        verifie((t, "maître" in msg), ("RuntimeError", True), "esclave IP:port, maitre sans RoutageRangeExtender -> erreur claire")
        verifie(esclave.journal, [], "esclave sans maitre : aucune requete a l'esclave")
        maitre.maitre = True
        r = prepare(racine)
        verifie((r["hostname_carte"], maitre.requetes()[:1]), (hote, [("GET", "/cm?cmnd=RoutageRangeExtender")]),
                "esclave joint : redirection posee par le maitre d'abord")
        maitre.maitre = False
        verifie(erreur(envoie, racine, r["jeton"])[0], "RuntimeError", "envoi : maitre en echec -> refus")
        verifie(envois(esclave), [], "maitre en echec : rien d'envoye")
    finally:
        ae.joint_par_maitre = joint
        maitre.ferme()
        esclave.ferme()


def refus(racine, hote):
    carte = nouvelle_carte(hote)
    depot = racine / CARTE / "autoexec.bat"
    jeton = prepare(racine)["jeton"]
    n = len(carte.journal)
    for builds, libelle in ((["pio run -e x"], "build en cours"), (None, "build indetectable")):
        b = (lambda: None) if builds is None else (lambda: list(builds))
        verifie(erreur(ae.prepare, racine, ENV, b)[0], "RuntimeError", f"prepare, {libelle} -> refus")
        verifie(erreur(ae.envoie, racine, ENV, jeton, ROUGES, False, b)[0], "RuntimeError", f"envoi, {libelle} -> refus")
    verifie(len(carte.journal), n, "build : aucune requete a la carte")
    verifie(erreur(envoie, racine, jeton, rouges=ROUGES - 1)[0], "ValueError", "rouges non lus -> refus")
    verifie(erreur(envoie, racine, jeton, rouges=True)[0], "ValueError", "rouges_lus booleen -> refus")
    for valeur in ("oui", 1, None):
        verifie(erreur(envoie, racine, jeton, redemarrer=valeur)[0], "ValueError", f"redemarrer {valeur!r} -> refus")
    for faux in ("x", "", 5, None, jeton[:-1] + ("0" if jeton[-1] != "0" else "1")):
        verifie(erreur(envoie, racine, faux)[0] in ("RuntimeError", "ValueError"), True, f"jeton {faux!r} -> refus")
    maintenant = ae._maintenant
    ae._maintenant = lambda: maintenant() + ae.VALIDITE + 1
    try:
        verifie(erreur(envoie, racine, jeton)[0], "RuntimeError", "jeton de plus de 10 minutes -> refus")
    finally:
        ae._maintenant = maintenant
    carte.flash["/autoexec.bat"] = SUR_CARTE + b"WebLog 4\n"
    verifie(erreur(envoie, racine, jeton)[0], "RuntimeError", "fichier de la carte change depuis prepare -> refus")
    carte.flash["/autoexec.bat"] = SUR_CARTE
    depot.write_bytes(FICHIER + b"WebLog 1\n")
    verifie(erreur(envoie, racine, jeton)[0], "RuntimeError", "fichier du depot change depuis prepare -> refus")
    depot.write_bytes(FICHIER)
    verifie((envois(carte), carte.flash["/autoexec.bat"]), ([], SUR_CARTE), "refus : rien d'envoye")
    depot.unlink()
    verifie(erreur(prepare, racine)[0], "ValueError", "pas d'autoexec.bat au depot -> prepare refuse")
    verifie(erreur(envoie, racine, jeton)[0], "ValueError", "pas d'autoexec.bat au depot -> envoi refuse")
    depot.write_bytes(FICHIER)
    carte.ferme()


def envoi(racine, hote):
    carte = nouvelle_carte(hote)
    carte.echec_fichier = "autoexec.bat"
    t, _ = erreur(envoie, racine, prepare(racine)["jeton"])
    copies = sorted((fbs.dossier_sauvegardes() / "autoexec_cartes" / ENV).glob("*.bat"))
    verifie((t, [c.read_bytes() for c in copies]), ("RuntimeError", [SUR_CARTE]),
            "envoi refuse par la carte : copie de la carte sauvegardee AVANT l'envoi")
    carte.echec_fichier = None
    r = envoie(racine, prepare(racine)["jeton"])
    sauve = Path(r["sauvegarde"])
    verifie((r["envoye"], sauve.parent, sauve.read_bytes()), (True, fbs.dossier_sauvegardes() / "autoexec_cartes" / ENV, SUR_CARTE),
            "envoi : copie de la carte dans autoexec_cartes/<env>/")
    verifie(carte.flash["/autoexec.bat"], FICHIER, "envoi : la carte a les octets du depot")
    verifie((carte.requetes("Restart"), carte.requetes("BrRestart")), ([], []), "redemarrer=False : aucun Restart")
    ae.REGLAGES_ENVOI.update(RAPIDE)
    carte.flash["/autoexec.bat"] = SUR_CARTE
    envoie(racine, prepare(racine)["jeton"], redemarrer=True)
    verifie(carte.requetes("Restart"), [("GET", "/cm?cmnd=Restart%201")], "redemarrer=True : Restart 1")
    del carte.flash["/autoexec.bat"]
    r = envoie(racine, prepare(racine)["jeton"])
    verifie((r, carte.flash["/autoexec.bat"]), ({"envoye": True, "sauvegarde": None}, FICHIER),
            "carte sans fichier : envoye, rien a sauvegarder")
    carte.ferme()


def joint(adresse, persist, env, rapporte, **_):
    JOINTS.append((adresse, len(COURANTE[0].journal)))


def banc():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(tmp) / "donnees")
        racine = taa.depot(tmp)
        hote = _identite((racine / CARTE / "_persist.json").read_text(encoding="utf-8"))[0]
        adresse(racine)
        ae._adresse = lambda *_: ADRESSE[0]
        ae.joint_par_maitre = joint
        for etape in (preparation, identite, injoignable, refus, envoi):
            etape(racine, hote)


SAUVE = "    sauvegarde = _sauvegarde(env, carte) if carte is not None else None\n"
MUTANTS = [
    ("sans controle d'identite", "if not hote or hote.lower() != attendu.lower():", "if False:"),
    ("jeton jamais perime", "if not 0 <= _maintenant() - instant <= VALIDITE:", "if False:"),
    ("build ignore", "builds = builds_en_cours()", "builds = []"),
    ("rouges ignores", "if isinstance(rouges_lus, bool) or not isinstance(rouges_lus, int) or rouges_lus < rouges:", "if False:"),
    ("sans joint_par_maitre", "joint_par_maitre(adresse, persist, env, lambda _: None)", "None"),
    ("sauvegarde apres l'envoi", [(SAUVE, ""), ("    return {\"envoye\"", SAUVE + "    return {\"envoye\"")]),
    ("fichier de la carte non masque", "autoexec_fichier.masque(", "str("),
]


def temoins():
    source = (ICI / "autoexec_envoi.py").read_text(encoding="utf-8")
    for nom, *remplacements in MUTANTS:
        paires = remplacements[0] if len(remplacements) == 1 else [remplacements]
        mutant = source
        for ancien, nouveau in paires:
            verifie(mutant.count(ancien), 1, f"mutant {nom} : motif present une fois")
            mutant = mutant.replace(ancien, nouveau)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "autoexec_envoi.py").write_text(mutant, encoding="utf-8")
            p = subprocess.run([sys.executable, str(Path(__file__).resolve())], capture_output=True, text=True, encoding="utf-8",
                               env=dict(os.environ, AUTOEXEC_MUTANT=tmp, PYTHONIOENCODING="utf-8"))
        verifie(p.returncode != 0, True, f"temoin rouge : mutant {nom}")


if __name__ == "__main__":
    banc()
    if not os.environ.get("AUTOEXEC_MUTANT"):
        temoins()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1 if ECHECS else 0)
