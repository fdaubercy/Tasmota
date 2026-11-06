#!/usr/bin/env python3
"""Banc des routes /autoexec* de l'Assistant persist (plan autoexec-bat, A5 et A7) : assistant_persist_autoexec.py, atteint
par le vrai serveur (assistant_persist_web) sur un depot temporaire, comme test_assistant_persist_web.py.

L'autoexec.bat de l'essai est ECRIT par le banc avec un mot de passe INVENTE (jamais celui du depot) : il ne doit
figurer dans le corps d'AUCUNE reponse (texte, avertissements, diff, banque, erreurs). Temoins : des mutants du module
(copie modifiee en dossier temporaire, banc relance avec AUTOEXEC_MUTANT=<dossier>) doivent rendre le banc ROUGE.
Routes d'envoi (A7) : carte SIMULEE (build_ota_carte_simulee, 127.0.0.1) ; adresse et joint_par_maitre
d'autoexec_envoi remplaces par le banc, jamais de vraie carte (la logique complete : test_autoexec_envoi.py).
Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_assistant_persist_autoexec.py
"""
import copy
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if os.environ.get("AUTOEXEC_MUTANT"):
    sys.path.insert(0, os.environ["AUTOEXEC_MUTANT"])

import autoexec_banque as ab
import autoexec_envoi
import build_ota_fs
from build_ota_carte_simulee import Carte
import test_assistant_persist_creation as tac
import test_assistant_persist_web as taw

ICI = Path(__file__).resolve().parent
ENV = "tasmota32-bureau-interrupteur-energie"
CARTE = "data/bureau/tasmota32-interrupteur-energie"
MDP = "INVENTE_mdp_42"
FICHIER = f"Backlog SSId1 ReseauInvente; Password1 {MDP}\nWebLog 3\nSetOption1 1\n;MqttPassword {MDP}\n"
PERSO = {"nom": "MaCommande", "categorie": "Perso", "description": "Un essai.", "modele": "WebLog {niveau}",
         "champs": [{"cle": "niveau", "type": "nombre", "libelle": "Niveau", "defaut": 2, "min": 0, "max": 4}]}
ROUGES = 4
ECHECS = taw.ECHECS
verifie = taw.verifie


def depot(t):
    racine = tac.depot(t)
    for rel in ("outils_docs/schemas/commandes_tasmota.json", ab.FICHIER):
        shutil.copyfile(tac.RACINE / rel, racine / rel)
    (racine / CARTE / "autoexec.bat").write_bytes(FICHIER.encode("utf-8"))
    return racine


def hostiles(b):
    for env in ("..", "../x", "a/b", "a\\b", "", ".", "x..y", 5, None, ["x"]):
        corps = {"env": env, "texte": "WebLog 1\n", "empreinte": "x", "rouges_lus": 0}
        if isinstance(env, str):
            verifie(b.requete("GET", "/autoexec?env=" + env.replace("\\", "%5C"))[0], 400, f"GET env hostile {env!r} -> 400")
        for route in ("/autoexec/analyse", "/autoexec/diff", "/autoexec/ecrit", "/autoexec/envoi/prepare", "/autoexec/envoi"):
            verifie(b.requete("POST", route, corps)[0], 400, f"POST {route} env hostile {env!r} -> 400")
    verifie(b.requete("GET", "/autoexec")[0], 400, "GET sans env -> 400")
    for env in ("tasmota32-inconnu-x", "tasmota32s3-base-N16R8"):
        verifie(b.requete("GET", "/autoexec?env=" + env)[0], 404, f"GET {env} (inconnu, ou base) -> 404")
        verifie(b.requete("POST", "/autoexec/analyse", {"env": env, "texte": ""})[0], 404, f"POST analyse {env} -> 404")


def lecture(b):
    s, g = b.requete("GET", "/autoexec?env=" + ENV)
    verifie(s, 200, "GET /autoexec : 200")
    verifie(sorted(g), ["avertissements", "chemin", "empreinte", "existe", "lignes", "texte"], "GET /autoexec : les clefs du contrat")
    verifie((g["existe"], g["chemin"], MDP in g["texte"], g["texte"].count("***")), (True, f"{CARTE}/autoexec.bat", False, 2),
            "GET /autoexec : fichier lu, secrets en ***")
    verifie([a["ligne"] for a in g["avertissements"] if a["type"] == "secret"], [1, 4], "GET /autoexec : 2 secrets en clair signales (lignes 1 et 4)")
    verifie(sum(a["niveau"] == "rouge" for a in g["avertissements"]), ROUGES, "GET /autoexec : rouges = 2 secrets + 2 redemarrages (SSId1, Password1)")
    verifie(len(g["lignes"]), 4, "GET /autoexec : une entree par ligne")
    s, banque = b.requete("GET", "/autoexec/banque")
    verifie((s, banque), (200, ab.charge(b.racine)), "GET /autoexec/banque : la banque")
    s, a = b.requete("POST", "/autoexec/analyse", {"env": ENV, "texte": g["texte"]})
    verifie((s, a), (200, {"avertissements": g["avertissements"]}), "POST analyse : meme resultat, sur le texte demasque")
    s, a = b.requete("POST", "/autoexec/analyse", {"env": ENV, "texte": g["texte"] + "Hostname x\n"})
    verifie(sum(x["niveau"] == "rouge" for x in a["avertissements"]), ROUGES + 1, "POST analyse : une boucle de redemarrage de plus")
    verifie(b.requete("POST", "/autoexec/analyse", {"env": ENV, "texte": "Password2 ***\n"})[0], 400, "POST analyse : *** sans origine -> 400")
    verifie(b.requete("POST", "/autoexec/analyse", {"env": ENV})[0], 400, "POST analyse sans texte -> 400")
    verifie(b.requete("POST", "/autoexec/diff", {"env": ENV, "texte": 5})[0], 400, "POST diff texte non chaine -> 400")
    s, d = b.requete("POST", "/autoexec/diff", {"env": ENV, "texte": g["texte"].replace("WebLog 3", "WebLog 2")})
    verifie((s, "+WebLog 2" in d["diff"], d["rouges"], d["empreinte"]), (200, True, ROUGES, g["empreinte"]), "POST diff : ligne changee, rouges comptes")
    verifie(b.requete("GET", "/autoexec/envoi/prepare")[0], 404, "GET /autoexec/envoi/prepare : route en POST seulement (404)")
    return g


def ecriture(b, g):
    page = g["texte"].replace("WebLog 3", "WebLog 2")
    corps = {"env": ENV, "texte": page, "empreinte": g["empreinte"], "rouges_lus": ROUGES}
    fichier = b.racine / CARTE / "autoexec.bat"
    b.builds = ["pio run -e x"]
    verifie(b.requete("POST", "/autoexec/ecrit", corps)[0], 409, "ecrit pendant un build -> 409")
    b.builds = None
    verifie(b.requete("POST", "/autoexec/ecrit", corps)[0], 409, "ecrit, build indetectable -> 409")
    verifie(fichier.read_bytes(), FICHIER.encode(), "build : rien d'ecrit")
    b.builds = []
    verifie(b.requete("POST", "/autoexec/ecrit", dict(corps, rouges_lus=1))[0], 400, "ecrit, rouges non lus -> 400")
    verifie(b.requete("POST", "/autoexec/ecrit", dict(corps, empreinte="autre"))[0], 409, "ecrit, empreinte perimee -> 409")
    verifie(b.requete("POST", "/autoexec/ecrit", dict(corps, empreinte=None))[0], 400, "ecrit, empreinte absente -> 400")
    s, r = b.requete("POST", "/autoexec/ecrit", corps)
    verifie((s, r), (200, {"ecrit": True, "chemin": f"{CARTE}/autoexec.bat"}), "ecrit : 200")
    verifie(fichier.read_bytes(), FICHIER.replace("WebLog 3", "WebLog 2").encode(), "ecrit : secrets remis cote serveur")
    verifie(b.requete("POST", "/autoexec/ecrit", corps)[0], 409, "ecrit rejoue (fichier change) -> 409")


def banque(b):
    avant = ab.charge(b.racine)
    b.builds = ["pio"]
    verifie(b.requete("POST", "/autoexec/banque/ajoute", {"entree": copy.deepcopy(PERSO)})[0], 409, "banque/ajoute pendant un build -> 409")
    verifie(ab.charge(b.racine), avant, "banque : rien d'ecrit pendant un build")
    b.builds = []
    verifie(b.requete("POST", "/autoexec/banque/ajoute", {"entree": 5})[0], 400, "banque/ajoute entree invalide -> 400")
    verifie(b.requete("POST", "/autoexec/banque/ajoute", {})[0], 400, "banque/ajoute sans entree -> 400")
    s, r = b.requete("POST", "/autoexec/banque/ajoute", {"entree": copy.deepcopy(PERSO)})
    verifie((s, r), (200, ab.charge(b.racine)), "banque/ajoute : la banque a jour")
    verifie((r[-1]["nom"], len(r)), ("MaCommande", len(avant) + 1), "banque/ajoute : entree perso en fin de banque")
    verifie(b.requete("POST", "/autoexec/banque/ajoute", {"entree": copy.deepcopy(PERSO)})[0], 400, "banque/ajoute : nom deja pris -> 400")
    verifie(b.requete("GET", "/autoexec/nulle-part")[0], 404, "route /autoexec/... inconnue -> 404")


def envoi(b, carte):
    hote = build_ota_fs._identite((b.racine / CARTE / "_persist.json").read_text(encoding="utf-8"))[0]
    carte.hostname, carte.flash["/autoexec.bat"] = hote, f"Password1 {MDP}\nWebLog 1\n".encode("utf-8")
    b.builds = ["pio"]
    verifie(b.requete("POST", "/autoexec/envoi/prepare", {"env": ENV})[0], 409, "envoi/prepare pendant un build -> 409")
    b.builds = []
    s, p = b.requete("POST", "/autoexec/envoi/prepare", {"env": ENV})
    verifie((s, p.get("hostname_carte"), p.get("ecart"), "***" in (p.get("sur_carte") or "")), (200, hote, True, True),
            "envoi/prepare : 200, fichier de la carte masque")
    corps = {"env": ENV, "jeton": p.get("jeton"), "rouges_lus": ROUGES, "redemarrer": False}
    for cle, valeur in (("jeton", 5), ("jeton", None), ("redemarrer", "oui"), ("redemarrer", 1), ("rouges_lus", True)):
        verifie(b.requete("POST", "/autoexec/envoi", dict(corps, **{cle: valeur}))[0], 400, f"envoi {cle}={valeur!r} -> 400")
    verifie(b.requete("POST", "/autoexec/envoi", dict(corps, jeton="1-x"))[0], 409, "envoi jeton inconnu -> 409")
    b.builds = ["pio"]
    verifie(b.requete("POST", "/autoexec/envoi", corps)[0], 409, "envoi pendant un build -> 409")
    b.builds = []
    verifie(carte.requetes("/ufsu?fsz"), [], "refus : rien d'envoye a la carte")
    s, r = b.requete("POST", "/autoexec/envoi", corps)
    verifie((s, r.get("envoye"), carte.flash["/autoexec.bat"]), (200, True, (b.racine / CARTE / "autoexec.bat").read_bytes()),
            "envoi : 200, la carte a le fichier du depot")


def transport(b):
    """La route transmet le transport demande (defaut http) ; un transport inconnu -> 400."""
    vus = []
    prepare, envoie = autoexec_envoi.prepare, autoexec_envoi.envoie
    autoexec_envoi.prepare = lambda *a, **k: vus.append(("prepare", k.get("transport"))) or {"jeton": "x"}
    autoexec_envoi.envoie = lambda *a, **k: vus.append(("envoie", k.get("transport"))) or {"envoye": True}
    try:
        corps = {"env": ENV, "jeton": "x", "rouges_lus": 0, "redemarrer": False}
        for route in ("/autoexec/envoi/prepare", "/autoexec/envoi"):
            for demande in (corps, dict(corps, transport="mqtt"), dict(corps, transport="http")):
                verifie(b.requete("POST", route, demande)[0], 200, f"{route} transport {demande.get('transport')!r} -> 200")
        verifie(vus, [(o, t) for o in ("prepare", "envoie") for t in ("http", "mqtt", "http")], "routes : le transport demande est transmis (http par defaut)")
    finally:
        autoexec_envoi.prepare, autoexec_envoi.envoie = prepare, envoie
    for route in ("/autoexec/envoi/prepare", "/autoexec/envoi"):
        for faux in ("ftp", None, 5, ["mqtt"]):
            verifie(b.requete("POST", route, dict(corps, transport=faux))[0], 400, f"{route} transport {faux!r} -> 400")


def banc():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(tmp) / "donnees")
        b = taw.Banc(tmp, racine=depot(tmp))
        carte = Carte()
        autoexec_envoi._adresse = lambda *_: carte.ip                   # jamais l'adresse reelle d'une carte du depot
        autoexec_envoi.joint_par_maitre = lambda *_a, **_k: None        # 127.0.0.1:port n'a pas de maitre
        autoexec_envoi.coupe_sleep = lambda *_a, **_k: ("50", lambda: "")   # ni son Sleep (test_autoexec_envoi l'exerce)
        try:
            hostiles(b)
            g = lecture(b)
            ecriture(b, g)
            banque(b)
            envoi(b, carte)
            transport(b)
        finally:
            carte.ferme()
            b.ferme()
    verifie(sum(MDP in r for r in taw.REPONSES_VUES), 0, f"AUCUNE des {len(taw.REPONSES_VUES)} reponses ne contient le mot de passe")
    verifie(len(taw.REPONSES_VUES) > 40, True, "le banc a bien joue ses requetes")


MUTANTS = [
    ("env hostile accepte", 'if not isinstance(valeur, str) or not NOM_ENV.fullmatch(valeur) or ".." in valeur:', "if False:"),
    ("env inconnu non refuse", "raise LookupError(f\"{valeur}", "return valeur  # "),
    ("build ignore a l'ecriture", """empreinte, demande.get("rouges_lus"), builds_en_cours)""",
     """empreinte, demande.get("rouges_lus"), lambda: [])"""),
    ("build ignore pour la banque", """demande.get("entree"), builds_en_cours)""",
     """demande.get("entree"), lambda: [])"""),
    ("build ignore pour la preparation", "_env(racine, demande), builds_en_cours,", "_env(racine, demande), lambda: [],"),
    ("build ignore pour l'envoi", """demande.get("redemarrer"), builds_en_cours,""", """demande.get("redemarrer"), lambda: [],"""),
    ("transport ignore par la route de preparation", """builds_en_cours,
                                      transport=demande.get("transport", "http"))""", "builds_en_cours)"),
    ("transport ignore par la route d'envoi", """builds_en_cours, transport=demande.get("transport", "http"))""", "builds_en_cours)"),
    ("texte non masque", '{**l, "avertissements"', '{**l, "texte": autoexec_fichier.texte_disque(racine, env), "avertissements"'),
    ("diff du texte brut", "autoexec_fichier.diff(racine, env, texte)", "{'diff': texte, 'empreinte': '', 'rouges': 0}"),
    ("analyse sur le texte masque", "autoexec_fichier.avertissements(racine, env, autoexec_fichier.demasque(texte, disque))",
     "autoexec_fichier.avertissements(racine, env, texte)"),
]


def temoins():
    source = (ICI / "assistant_persist_autoexec.py").read_text(encoding="utf-8")
    for nom, ancien, nouveau in MUTANTS:
        verifie(ancien in source, True, f"mutant {nom} : motif present")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "assistant_persist_autoexec.py").write_text(source.replace(ancien, nouveau), encoding="utf-8")
            p = subprocess.run([sys.executable, str(Path(__file__).resolve())], capture_output=True, text=True, encoding="utf-8",
                               env=dict(os.environ, AUTOEXEC_MUTANT=tmp, PYTHONIOENCODING="utf-8"))
        verifie(p.returncode != 0, True, f"temoin rouge : mutant {nom}")


if __name__ == "__main__":
    banc()
    if not os.environ.get("AUTOEXEC_MUTANT"):
        temoins()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1 if ECHECS else 0)
