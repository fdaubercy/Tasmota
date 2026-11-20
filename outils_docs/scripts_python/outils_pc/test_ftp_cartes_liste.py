"""Banc de ftp_cartes_liste (cartes joignables par FTP). Code de sortie 0 = vert.

Mini-depot temporaire avec un FAUX mot de passe ; `cas_depot_reel` lit le vrai depot en lecture seule et ne
compare les identifiants que par OK/KO (aucune valeur secrete n'est imprimee).
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_ftp_cartes_liste.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import json
import sys
import tempfile
from pathlib import Path

import ftp_cartes_liste as fl

ECHECS = []
FAUX_MDP = "faux-mdp-de-banc-123"
RACINE = Path(__file__).resolve().parents[3]


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


COMMUN = f'''#ifndef _USER_CONFIG_OVERRIDE_H_
#define _USER_CONFIG_OVERRIDE_H_
#ifdef USER_CONFIG_OVERRIDE_FIRMWARES_PERSONNALISES
    #ifdef USE_FTP
        #undef USE_FTP
    #endif
    #define USE_FTP
    #define USER_FTP "admin"
    #define PW_FTP "{FAUX_MDP}"
'''
FIN = "#endif\n#endif\n"


def depot(sections, persists, envs=None, commun=COMMUN):
    """Mini-depot : sections = texte des sections du .h ; persists = {env: texte du persist} ; envs = {env: firmware}."""
    d = Path(tempfile.mkdtemp(prefix="banc_ftp_"))
    (d / "tasmota").mkdir()
    (d / "tasmota" / "user_config_override.h").write_text(commun + sections + FIN, encoding="utf-8")
    ini = ""
    for env, fw in (envs or {}).items():
        ini += f"[env:{env}]\nextends = env:tasmota32_base\nbuild_flags = -D{fw}\n\n"
    (d / "platformio_tasmota_cenv.ini").write_text(ini, encoding="utf-8")
    for env, texte in persists.items():
        m = env.split("-")
        dossier = d / "data" / m[1] / "-".join([m[0]] + m[2:])
        dossier.mkdir(parents=True)
        (dossier / "_persist.json").write_text(texte, encoding="utf-8")
    return d


def persist(hote="carte1", esclave=False, ip_maitre="192.168.0.9"):
    re_ = {"activation": "ON", "id": 2, "ipMaitre": ip_maitre} if esclave else {"activation": "OFF", "id": 0}
    return json.dumps({"serveur": {"hostname": hote, "rangeExtender": re_}})


def sec(fw, corps=""):
    return f"#if defined({fw})\n{corps}#endif\n"


def exclues(res):
    return {x["env"]: x["raison"] for x in res["exclues"]}


def cas_esclave():
    env = "tasmota32s3-cave-a"
    d = depot(sec("FIRMWARE_A"), {env: persist(esclave=True)}, {env: "FIRMWARE_A"})
    res = fl.liste(d)
    verifie(res["cartes"], [], "esclave : aucune carte")
    verifie("Range Extender" in exclues(res).get(env, ""), True, "esclave : raison cite le Range Extender")
    p = d / "data/cave/tasmota32s3-a/_persist.json"
    verifie(fl.est_esclave_rgx(p), True, "est_esclave_rgx : esclave")
    p.write_text(persist(esclave=False), encoding="utf-8")
    verifie(fl.est_esclave_rgx(p), False, "est_esclave_rgx : maitre")


def cas_persist_illisible():
    env = "tasmota32s3-cave-a"
    d = depot(sec("FIRMWARE_A"), {env: "{ casse"}, {env: "FIRMWARE_A"})
    p = d / "data/cave/tasmota32s3-a/_persist.json"
    verifie(fl.est_esclave_rgx(p), None, "persist casse : None")
    verifie(env in exclues(fl.liste(d)), True, "persist casse : carte exclue")
    p.write_text('{"serveur": {"hostname": "a\tb", "rangeExtender": {"activation": "OFF"}}}', encoding="utf-8")
    verifie(fl.est_esclave_rgx(p), False, "caractere de controle dans une chaine : lu (strict=False)")
    verifie(fl.est_esclave_rgx(d / "absent.json"), None, "persist absent : None")


def cas_sans_use_ftp():
    h = "#if defined(FIRMWARE_X)\n    #ifdef USE_FTP\n        #undef USE_FTP\n    #endif\n#endif\n"
    verifie(fl.ftp_retire(COMMUN + h + FIN, "FIRMWARE_X"), True, "#undef USE_FTP dans la section : retire")
    verifie(fl.ftp_retire(COMMUN + h + FIN, "FIRMWARE_Y"), False, "section d'un autre firmware : non retire")
    verifie(fl.ftp_retire(COMMUN + "#if defined(FIRMWARE_X)\n#define Z 1\n#endif\n" + FIN, "FIRMWARE_X"), False,
            "section sans #undef : gardee")
    nie = "#if defined(FIRMWARE_X) || defined(FIRMWARE_Y)\n#if !defined(FIRMWARE_X)\n#undef USE_FTP\n#endif\n#endif\n"
    verifie(fl.ftp_retire(COMMUN + nie + FIN, "FIRMWARE_X"), False, "#undef sous #if !defined(FIRMWARE_X) : gardee pour X")
    verifie(fl.ftp_retire(COMMUN + nie + FIN, "FIRMWARE_Y"), True, "meme section : retire pour un autre env Y")
    verifie(fl.ftp_retire(COMMUN + "#if defined(FIRMWARE_X)\n#if SOME_VALUE > 2\n#undef USE_FTP\n#endif\n#endif\n" + FIN,
                          "FIRMWARE_X"), None, "condition non evaluable autour du #undef : doute")
    inconnu = "#if defined(FIRMWARE_X)\n#if defined(MACRO_INCONNUE)\n#undef USE_FTP\n#endif\n#endif\n"
    verifie(fl.ftp_retire(COMMUN + inconnu + FIN, "FIRMWARE_X"), None, "#undef sous macro inconnue : doute")
    ou = "#if defined(FIRMWARE_Y) || defined(FIRMWARE_X)\n#undef USE_FTP\n#endif\n"
    verifie(fl.ftp_retire(COMMUN + ou + FIN, "FIRMWARE_X"), True, "section a plusieurs firmwares : retire")
    elif_ = "#if defined(FIRMWARE_Y)\n#undef USE_FTP\n#elif defined(FIRMWARE_X)\n#define Z 1\n#endif\n"
    verifie(fl.ftp_retire(COMMUN + elif_ + FIN, "FIRMWARE_X"), False, "#elif : le #undef du if voisin ne compte pas")
    d = depot(h + "#if defined(FIRMWARE_B)\n#endif\n",
              {"tasmota32s3-cave-a": persist(), "tasmota32s3-cave-b": persist("b")},
              {"tasmota32s3-cave-a": "FIRMWARE_X", "tasmota32s3-cave-b": "FIRMWARE_B"})
    res = fl.liste(d)
    verifie([c["env"] for c in res["cartes"]], ["tasmota32s3-cave-b"], "liste : seule la carte avec FTP reste")
    verifie("USE_FTP" in exclues(res).get("tasmota32s3-cave-a", ""), True, "liste : raison cite USE_FTP")


def cas_puce():
    env = "tasmota-cave-lampe"
    d = depot(sec("FIRMWARE_A"), {env: persist()}, {env: "FIRMWARE_A"})
    res = fl.liste(d)
    verifie(res["cartes"], [], "ESP8266 : aucune carte")
    verifie("ESP8266" in exclues(res).get(env, ""), True, "ESP8266 : raison cite la puce")


def cas_adresse():
    envs = {"tasmota32s3-cave-a": "FIRMWARE_A", "tasmota32s3-cave-b": "FIRMWARE_B", "tasmota32s3-cave-c": "FIRMWARE_C"}
    h = (sec("FIRMWARE_A", '#define WIFI_IP_ADDRESS "192.168.0.77"\n') + sec("FIRMWARE_B", '#define WIFI_IP_ADDRESS "0.0.0.0"\n')
         + sec("FIRMWARE_C"))
    d = depot(h, {e: persist("hote-" + e[-1]) for e in envs}, envs)
    par_env = {c["env"]: c for c in fl.liste(d)["cartes"]}
    verifie(par_env["tasmota32s3-cave-a"]["adresse"], "192.168.0.77", "adresse : IP du .h")
    verifie(par_env["tasmota32s3-cave-b"]["adresse"], "hote-b.local", "adresse : 0.0.0.0 donne <Hostname>.local")
    verifie(par_env["tasmota32s3-cave-c"]["adresse"], "hote-c.local", "adresse : IP absente donne <Hostname>.local")
    c = par_env["tasmota32s3-cave-c"]
    verifie((c["lieu"], c["puce"], c["hote"], c["nom"], c["firmware"]),
            ("cave", "ESP32-S3", "hote-c", "tasmota32s3-cave-c", "FIRMWARE_C"), "champs lieu, puce, hote, nom, firmware")


def cas_identifiants():
    fw = "FIRMWARE_X"
    verifie(fl.identifiants(Path("/inexistant"), fw), ("", ""), "depot sans .h : identifiants vides")
    d = depot(sec(fw), {"tasmota32s3-cave-a": persist()}, {"tasmota32s3-cave-a": fw})
    verifie(fl.identifiants(d, fw), ("admin", FAUX_MDP), "identifiants de la partie commune")
    redef = '#undef USER_FTP\n#define USER_FTP "autre"\n#undef PW_FTP\n#define PW_FTP "autre-mdp"\n'
    d2 = depot(sec(fw, redef), {"tasmota32s3-cave-a": persist()}, {"tasmota32s3-cave-a": fw})
    verifie(fl.identifiants(d2, fw), ("autre", "autre-mdp"), "identifiants redefinis dans la section de l'env")
    verifie(fl.identifiants(d2, "FIRMWARE_Y"), ("admin", FAUX_MDP), "autre firmware : identifiants communs")
    verifie(FAUX_MDP in json.dumps(fl.liste(d)), False, "liste() ne contient pas le mot de passe")
    verifie("autre-mdp" in json.dumps(fl.liste(d2)), False, "liste() ne contient pas le mot de passe redefini")


def cas_depot_reel():
    res = fl.liste(RACINE)
    pris = {c["env"] for c in res["cartes"]}
    ex = exclues(res)
    for env in ("tasmota32s3-garage-capteurs-cuve-modbus", "tasmota32s3-garage-rideau-garage-modbus",
                "tasmota32s3-garage-portail-jardin-modbus"):
        verifie(env in ex and "Range Extender" in ex.get(env, ""), True, f"reel : {env} exclu comme esclave")
    # serveur-debits-pac : esclave (rangeExtender ON, id 1, ipMaitre = l'ecran) ; c'est l'ecran (maitre, id 0) qui est liste.
    verifie("Range Extender" in ex.get("tasmota32s3-bureau-serveur-debits-pac", ""), True,
            "reel : tasmota32s3-bureau-serveur-debits-pac exclu comme esclave (id 1)")
    for env in ("tasmota32p4-garage-serveur-modbus", "tasmota32s3-bureau-ecran-debits-pac"):
        verifie(env in pris, True, f"reel : {env} present")
    for env in ("tasmota32-cave-serveur-rly", "tasmota32-bureau-interrupteur-energie", "tasmota32-jardin-projecteur-led"):
        verifie(env in ex and env not in pris, True, f"reel : ESP32 sans PSRAM {env} exclu")
    verifie("tasmota32s3-cave-serveur-rly" in pris, True, "reel : cave S3 listee (FTP garde par !defined de sa section)")
    verifie("tasmota32-cave-serveur-rly" in ex and "USE_FTP" in ex["tasmota32-cave-serveur-rly"], True,
            "reel : ESP32 de la cave exclu (USE_FTP retire)")
    p4 = next((c for c in res["cartes"] if c["env"] == "tasmota32p4-garage-serveur-modbus"), None)
    ident = fl.identifiants(RACINE, p4["firmware"] if p4 else "")
    verifie(bool(ident[0]) and bool(ident[1]), True, "reel : identifiants du P4 trouves (valeurs non affichees)")
    verifie(bool(ident[1]) and ident[1] in json.dumps(res), False, "reel : le mot de passe n'est pas dans liste()")
    for c in res["cartes"]:
        verifie(sorted(c), ["adresse", "env", "firmware", "hote", "lieu", "nom", "puce"], f"reel : champs de {c['env']}")


if __name__ == "__main__":
    for cas in (cas_esclave, cas_persist_illisible, cas_sans_use_ftp, cas_puce, cas_adresse, cas_identifiants,
                cas_depot_reel):
        print(f"-- {cas.__name__}")
        cas()
    print("\nECHECS : " + (", ".join(ECHECS) if ECHECS else "aucun"))
    sys.exit(1 if ECHECS else 0)
