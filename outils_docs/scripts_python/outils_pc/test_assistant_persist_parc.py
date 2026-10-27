"""Banc de assistant_persist_parc (lecture du parc et regles des mots de passe).

Code de sortie 0 = vert. Lecture seule du vrai depot ; les cas d'echec (mot de passe ambigu, persist tronque)
se jouent dans une COPIE (depot_essai) dans un dossier temporaire. Aucune valeur de mot de passe n'est imprimee :
les comparaisons se font par egalite, et un echec n'affiche que des booleens.
A lancer avec le Python du penv (ProjectConfig).
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import assistant_persist_parc as parc
from test_fichiers_berry_creation import RACINE, depot_essai

ECHECS = []
MAITRES = {"data/cave/tasmota32s3-serveur-rly", "data/etage2/tasmota32s3-grenier",
           "data/garage/tasmota32p4-serveur-modbus", "data/garage/tasmota32s3-serveur-modbus"}
P4 = "data/garage/tasmota32p4-serveur-modbus/_persist.json"
BUREAU = "data/bureau/tasmota32-interrupteur-differentiel/_persist.json"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def lit(racine, rel):
    return json.loads((Path(racine) / rel).read_text(encoding="utf-8-sig"))


def refus(fonction, *args):
    """(message, ValueError ?) : le message d'un ValueError, '' si aucune exception."""
    try:
        fonction(*args)
    except ValueError as exc:
        return str(exc), True
    return "", False


def test_maitres_du_parc():
    ms = parc.maitres(RACINE)
    verifie({m["dossier"] for m in ms}, MAITRES, "maitres_du_parc : les 4 dossiers")
    p4 = next(m for m in ms if m["dossier"].endswith("p4-serveur-modbus"))
    verifie(sorted(p4), ["dossier", "env", "hostname", "id", "ip"], "maitre : cles")
    verifie((p4["env"], p4["hostname"], p4["ip"], p4["id"]),
            ("tasmota32p4-garage-serveur-modbus", "SERVEUR-GARAGE", "192.168.0.43", 0), "maitre P4 : env, hostname, ip, id")
    verifie(all(m["env"] for m in ms), True, "maitres : tous ont un env")


def test_ids_et_reseaux():
    verifie(sorted(parc.ids_pris(RACINE)), [0, 2, 3], "ids_pris : 0, 2, 3")
    verifie(len(parc.ids_pris(RACINE)[0]) >= 4 and len(parc.ids_pris(RACINE)[2]) == 1, True, "ids_pris : cartes par id")
    verifie(parc.id_libre(RACINE), 1, "id_libre_parc : 1")
    rs = parc.reseaux(RACINE)
    verifie(all(n in rs for n in ("MAISON", "Relai Wifi Cave", "SERVEUR-GARAGE-GATEWAY", "SERVEUR-GRENIER-2EME-GATEWAY")),
            True, "reseaux : noms connus et GATEWAY des maitres")
    verifie(len(rs), len(set(rs)), "reseaux : sans doublon")


def test_base_par_defaut():
    verifie(parc.base_par_defaut(RACINE, "ESP32S3"), "tasmota32s3-base-N16R8-sans-ecran", "base S3 : la plus utilisee")
    verifie(parc.base_par_defaut(RACINE, "ESP32P4"), "tasmota32p4-base-devkit", "base P4")
    verifie(parc.base_par_defaut(RACINE, "ESP32").startswith("tasmota32-base"), True, "base ESP32")


def test_secrets_esclave():
    s = parc.secrets(RACINE, "SERVEUR-GARAGE-GATEWAY", "SERVEUR-GARAGE-GATEWAY")
    p4 = lit(RACINE, P4)["serveur"]
    verifie(sorted(s), ["ap", "ftp", "mqtt", "wifi1", "wifi2"], "secrets : cles")
    verifie(s["wifi1"] == p4["rangeExtender"]["AP"]["mdp"], True, "secrets_esclave : wifi1 = AP.mdp du P4")
    verifie(s["wifi2"] == s["wifi1"], True, "secrets_esclave : wifi2 = wifi1")
    verifie((s["mqtt"] == p4["mqtt"]["mdp"], s["ap"] == p4["rangeExtender"]["AP"]["mdp"], s["ftp"] == p4["serveurFTP"]["mdp"]),
            (True, True, True), "secrets : mqtt, ap, ftp communs")
    m = parc.secrets(RACINE, "MAISON", "Relai Wifi Cave")
    verifie(m["wifi1"] == m["wifi2"] and m["wifi1"] == p4["wifi"]["reseau1"]["mdpWifi"], True, "secrets : MAISON = Relai Wifi Cave")
    verifie(m["wifi1"] != s["wifi1"], True, "secrets : les deux familles different")


def test_secret_ambigu(racine):
    d = lit(racine, BUREAU)
    ancien = d["serveur"]["wifi"]["reseau1"]["mdpWifi"]
    d["serveur"]["wifi"]["reseau1"]["mdpWifi"] = "valeur-differente-pour-l-essai"
    (Path(racine) / BUREAU).write_text(json.dumps(d, indent="\t", ensure_ascii=False), encoding="utf-8")
    msg, leve = refus(parc.secrets, racine, "MAISON", "MAISON_5GHz")
    verifie(leve, True, "secret_ambigu : ValueError")
    verifie("MAISON" in msg, True, "secret_ambigu : nomme le reseau")
    verifie(("valeur-differente-pour-l-essai" in msg) or (ancien in msg), False, "secret_ambigu : aucune valeur dans le message")


def test_reseau_inconnu(racine):
    msg, leve = refus(parc.secrets, racine, "MAISON", "RESEAU-QUI-N-EXISTE-PAS")
    verifie((leve, "RESEAU-QUI-N-EXISTE-PAS" in msg), (True, True), "reseau_inconnu : ValueError qui nomme le reseau")
    msg, leve = refus(parc.secrets, racine, "AUTRE-GATEWAY", "MAISON")
    verifie((leve, "AUTRE-GATEWAY" in msg), (True, True), "reseau_inconnu : GATEWAY sans maitre")
    d = lit(racine, BUREAU)
    d["serveur"]["mqtt"]["mdp"] = "autre-mdp-mqtt-pour-l-essai"
    (Path(racine) / BUREAU).write_text(json.dumps(d, indent="\t", ensure_ascii=False), encoding="utf-8")
    msg, leve = refus(parc.secrets, racine, "MAISON", "MAISON")
    verifie((leve, "mqtt" in msg, "autre-mdp-mqtt-pour-l-essai" in msg), (True, True, False), "cle commune ambigue : nomme la cle, sans valeur")


def test_persist_illisible(racine):
    f = Path(racine) / P4
    f.write_bytes(f.read_bytes()[:200])                       # persist tronque
    ms = parc.maitres(racine)
    verifie({m["dossier"] for m in ms}, MAITRES - {"data/garage/tasmota32p4-serveur-modbus"}, "persist_illisible : carte ignoree")
    verifie(sorted(parc.ids_pris(racine)), [0, 2, 3], "persist_illisible : ids_pris repond")
    verifie(parc.illisibles(racine), [P4], "persist_illisible : signale")
    verifie(parc.secrets(racine, "MAISON", "MAISON")["wifi1"] != "", True, "persist_illisible : secrets repond")


def principal():
    for test in (test_maitres_du_parc, test_ids_et_reseaux, test_base_par_defaut, test_secrets_esclave):
        try:
            test()
        except Exception as exc:
            verifie(type(exc).__name__, "pas d'exception", test.__name__)
    for test in (test_secret_ambigu, test_reseau_inconnu, test_persist_illisible):
        with tempfile.TemporaryDirectory() as t:
            os.environ["OUTILS_TASMOTA_DOSSIER"] = os.path.join(t, "outils")
            try:
                test(depot_essai(t))
            except Exception as exc:
                verifie(type(exc).__name__, "pas d'exception", test.__name__)
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
