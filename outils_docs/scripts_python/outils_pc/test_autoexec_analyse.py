#!/usr/bin/env python3
"""Banc de autoexec_analyse.py : avertissements d'un autoexec.bat (plan autoexec-bat, A2).

Lit le vrai autoexec.bat et le vrai persist de data/bureau/tasmota32-interrupteur-energie (lecture seule) ; aucun secret
n'apparait dans les libelles. Temoins : des mutants du module (copie modifiee en dossier temporaire, banc relance avec
AUTOEXEC_MUTANT=<dossier>) doivent rendre le banc ROUGE. Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_autoexec_analyse.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if os.environ.get("AUTOEXEC_MUTANT"):
    sys.path.insert(0, os.environ["AUTOEXEC_MUTANT"])

import autoexec_analyse as aa
import autoexec_commandes

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
CARTE = RACINE / "data" / "bureau" / "tasmota32-interrupteur-energie"
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def resume(avertissements):
    return [(a["ligne"], a["type"], a["niveau"]) for a in avertissements]


def noms_secrets():
    return all(aa.SECRETS.search(n) for n in ("Password1", "MqttPassword", "WebPassword", "Pwd", "StaPwd", "Token", "ApiKey", "Key")) \
        and not any(aa.SECRETS.search(n) for n in ("Timer1", "Hostname", "WebSensor2", "SetOption146"))


def banc():
    texte = (CARTE / "autoexec.bat").read_text(encoding="utf-8")
    if "SetOption146" not in texte:     # le vrai fichier evolue (retiree par l'onglet le 2026-11-05) : le cas reste teste
        texte = "SetOption146 ON\n" + texte
    persist = json.loads((CARTE / "_persist.json").read_text(encoding="utf-8"))
    commandes = autoexec_commandes.charge(RACINE)
    cfg = (RACINE / aa.CONFIG_PERSIST).read_text(encoding="utf-8")
    ls = aa.lignes(texte)
    num = lambda debut: next((l["numero"] for l in ls if l["brut"].startswith(debut)), 0)
    ana = lambda t, p=persist: aa.analyse(t, p, commandes, texte_config=cfg)

    # lignes()
    bl = next(l for l in ls if l["brut"].startswith("Backlog Latitude"))
    verifie([c[0] for c in bl["commandes"]], ["Latitude", "Longitude"], "lignes : Backlog decoupe sur ;")
    com = next(l for l in ls if l["commentaire"] and "MqttPassword" in l["brut"])
    verifie(com["commentaire"] and "MqttPassword" in [c[0] for c in com["commandes"]], True,
            "lignes : un commentaire garde les commandes apres ;")
    verifie([l["numero"] for l in ls[:3]], [1, 2, 3], "lignes : numeros 1..")
    verifie(aa.lignes("Backlog0 A 1; B 2")[0]["commandes"], [("A", "1"), ("B", "2")], "lignes : Backlog0")

    # fichier reel
    res = ana(texte)
    par_type = lambda t: [a for a in res if a["type"] == t]
    verifie(resume(par_type("secret")), [(num(";Backlog WifiPower"), "secret", "rouge"), (num(";Backlog MqttHost"), "secret", "rouge")],
            "reel : Password1 et MqttPassword en commentaire -> secret rouge")
    verifie(all("MqttUser" not in a["message"] and "MAISON" not in a["message"] for a in par_type("secret")), True,
            "reel : le message ne cite aucune valeur")
    d = par_type("doublon")
    verifie([(a["ligne"], a["niveau"]) for a in d if "SetOption146" in a["message"]], [(num("SetOption146"), "orange")],
            "reel : SetOption146 -> doublon orange")
    verifie(any("diverses.affichageTempESP32" in a["message"] and '"ON"' in a["message"] for a in d), True,
            "reel : doublon nomme la cle du persist et sa valeur")
    verifie([a["commande"] for a in d if "SetOption146" in a["message"]], ["SetOption146"], "doublon : porte le nom de sa commande (bouton Enlever)")
    verifie({a["commande"] for a in par_type("secret")}, {None}, "secret : pas de commande a enlever depuis la liste")
    verifie([a for a in res if a["type"] not in ("secret", "doublon")], [],
            "reel : ni redemarrage ni inconnue ni longueur (AdcParam1, WebSensor2 0, Timer, Backlog)")
    verifie({a["ligne"] for a in d} <= {num("SetOption146"), num("SetOption1 "), num("SetOption56"), num("SetOption55"),
                                        num("SetOption141"), num("Backlog Latitude"), num("Backlog Timezone"), num("DeviceName"),
                                        num("Backlog IPAddress1"), num("Backlog SerialLog")}, True,
            "reel : doublons seulement sur des lignes que le persist repose")

    # ajouts
    verifie(resume(ana("Hostname X")), [(1, "redemarrage", "rouge"), (1, "doublon", "orange")],
            "Hostname -> redemarrage rouge (toujours)")
    si = [k for k, v in commandes["redemarrent"].items() if v["quand"] == "si-change"]
    verifie(bool(si), True, "donnees : une commande si-change existe")
    verifie([a["niveau"] for a in ana(si[0].title() + " 1") if a["type"] == "redemarrage"], ["orange"], "si-change -> orange")
    r = ana("WebSesnor2 0")
    verifie(resume(r), [(1, "inconnue", "orange")], "WebSesnor2 -> inconnue orange")
    verifie(r[0]["correction"], "WebSensor2", "WebSesnor2 -> correction WebSensor2 (chiffres et casse gardes)")
    verifie(ana("WebSensor2 0"), [], "WebSensor2 0 -> propre")
    verifie(aa.analyse("WebSesnor2 0", persist, commandes, banque_noms=["WEBSESNOR"], texte_config=cfg), [],
            "banque_noms : nom connu de la banque")
    verifie(resume(ana("Delay 1\nBacklog " + "Delay 1; " * 60)), [(2, "longueur", "orange")], "ligne longue -> longueur orange")
    verifie(ana("; " + "a" * 600), [], "commentaire long : rien")
    verifie(ana("Delay " + "1" * 504), [], "ligne de 510 : pas de longueur")
    verifie(resume(ana("Delay " + "1" * 505)), [(1, "longueur", "orange")], "ligne de 511 -> longueur orange")
    verifie(ana("; Hostname X\n; WebSesnor2 0\n; SetOption146 ON"), [], "commentaire : ni redemarrage, ni inconnue, ni doublon")
    verifie([a for a in ana("MqttPassword abc") if a["type"] == "secret"][0]["niveau"], "rouge", "secret hors commentaire -> rouge")
    verifie([a["type"] for a in ana("SetOption55 ON")], ["doublon"], "redemarre seulement si la valeur est 0 : ON -> pas de redemarrage")
    verifie([a["type"] for a in ana("SetOption55 OFF")], ["redemarrage", "doublon"], "SetOption55 OFF -> redemarrage")
    verifie(ana("Password1"), [], "commande sans valeur (interrogation) : rien")
    verifie([(x["type"], x["niveau"]) for x in ana("Password1=abc") if x["type"] == "secret"], [("secret", "rouge")],
            "Password1=x (= separe commande et valeur pour le firmware) -> secret rouge")
    verifie(aa.lignes("Backlog Password2 = abc; WebLog=2")[0]["commandes"], [("Password2", "abc"), ("WebLog", "2")],
            "lignes : nom et valeur separes par =")
    verifie(ana("\n; une ligne propre\nDelay 1\n"), [], "ligne propre -> aucune entree")
    verifie(resume(ana("SetOption146 ON", {"diverses": {}})), [(1, "doublon", "orange")], "persist vide : SetOption146 reste pose (defaut OFF)")
    verifie(ana("SetOption56 ON", {}), [], "persist vide : SetOption56 non pose -> pas de doublon")
    verifie(resume(ana("SetOption56 ON")), [(1, "doublon", "orange")], "persist rempli : SetOption56 -> doublon")
    verifie(noms_secrets(), True, "SECRETS : noms a secret")


MUTANTS = [
    ("secret en commentaire ignore", 'if SECRETS.search(ecrit) and valeur:', 'if SECRETS.search(ecrit) and valeur and not l["commentaire"]:'),
    ("doublon sans persist", 'commandes_posees(persist or {},', 'commandes_posees({},'),
    ("toujours traite en orange", 'if redemarrent[nom]["quand"] == "toujours":', 'if False:'),
    ("commentaire analyse en entier", "if l[\"commentaire\"]:\n                continue", "if False:\n                continue"),
    ("limite 511", "> LIMITE:", "> LIMITE + 1:"),
    ("condition sur la valeur ignoree", "return bool(m) and", "return False and"),
    ("casse perdue", "if ecrit.isupper():", "if True:"),
]


def temoins():
    source = (ICI / "autoexec_analyse.py").read_text(encoding="utf-8")
    for nom, ancien, nouveau in MUTANTS:
        verifie(ancien in source, True, f"mutant {nom} : motif present")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "autoexec_analyse.py").write_text(source.replace(ancien, nouveau, 1), encoding="utf-8")
            p = subprocess.run([sys.executable, str(Path(__file__).resolve())], capture_output=True, text=True, encoding="utf-8",
                               env=dict(os.environ, AUTOEXEC_MUTANT=tmp, PYTHONIOENCODING="utf-8"))
        verifie(p.returncode != 0, True, f"temoin rouge : mutant {nom}")


if __name__ == "__main__":
    banc()
    if not os.environ.get("AUTOEXEC_MUTANT"):
        temoins()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1 if ECHECS else 0)
