"""Banc de ftp_cartes_liste (cartes joignables par FTP). Code de sortie 0 = vert.

Mini-depot temporaire avec un FAUX mot de passe ; `cas_depot_reel` lit le vrai depot en lecture seule et ne
compare les identifiants que par OK/KO (aucune valeur secrete n'est imprimee).
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_ftp_cartes_liste.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import json
import re
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

import build_envs
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
    verifie(fl.est_esclave_rgx(p), False, "tolerant aux caracteres de controle dans une chaine : lu (strict=False)")
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


# FIRMWARE_* de l'amont qu'on sait sans effet sur une carte du depot (ni generiques ni propres a une carte). Vide au 2026-11-21.
AMONT_SANS_EFFET = ()


def inconnus(racine):
    """FIRMWARE_* qu'`ftp_cartes_liste._defini` jugerait faux a tort : -D de la chaine d'un env « cartes » (hors son propre
    firmware, le dernier) qui ne sont pas dans GENERIQUES, et FIRMWARE_* du .h qui ne sont ni generiques ni propres a une carte."""
    racine = Path(racine)
    toutes, _ = build_envs._sections(racine)
    cartes = [e for e in build_envs.liste_envs(racine) if e.famille == "cartes"]
    connus = set(fl.GENERIQUES) | set(AMONT_SANS_EFFET)
    trouves = {}
    for e in cartes:
        for section in build_envs._chaine(toutes, "env:" + e.nom):
            flags = build_envs._valeur(toutes, section, "build_flags")     # `${env:X.build_flags}` suivis
            for f in re.findall(r"-D\s*(FIRMWARE_\w+)", flags):
                if f != e.firmware and f not in connus:
                    trouves.setdefault(f, f"build_flags de {section} (chaine de {e.nom})")
    propres = {e.firmware for e in cartes}
    for f in sorted(set(re.findall(r"FIRMWARE_\w+", fl._lit_h(racine)))):
        if f not in connus and f not in propres:
            trouves.setdefault(f, "user_config_override.h")
    return trouves




def cas_concordance_generiques():
    trouves = inconnus(RACINE)
    for f, ou in trouves.items():
        print(f"     {f} ({ou}) : ajouter a GENERIQUES ou a une section du .h")
    verifie(sorted(trouves), [], "GENERIQUES couvre les FIRMWARE_* des bases du cenv et du .h (depot reel)")
    # temoin : un -DFIRMWARE_INCONNU ajoute a une COPIE du cenv est nomme
    d = Path(tempfile.mkdtemp(prefix="banc_ftp_conc_"))
    (d / "tasmota").mkdir()
    for f in (*build_envs.FICHIERS_INI, "tasmota/user_config_override.h"):
        if (RACINE / f).is_file():
            shutil.copy(RACINE / f, d / f)
    cenv = d / build_envs.FICHIER_CENV
    cenv.write_text(cenv.read_text(encoding="utf-8") + "\n[env:tasmota32s3-cave-mutant]\nextends = env:tasmota32s3\n"
                    "build_flags = ${env:tasmota32s3.build_flags} -DFIRMWARE_INCONNU -DFIRMWARE_MUTANT_PROPRE\n", encoding="utf-8")
    verifie(sorted(inconnus(d)), ["FIRMWARE_INCONNU"], "temoin : -DFIRMWARE_INCONNU d'une base est nomme (le dernier est le propre de l'env)")
    shutil.rmtree(d, ignore_errors=True)


def cas_cache():
    env = "tasmota32s3-cave-a"
    d = depot(sec("FIRMWARE_A"), {env: persist("carte1")}, {env: "FIRMWARE_A"})
    appels = []
    vraie = build_envs.liste_envs

    def espion(racine):
        appels.append(1)
        time.sleep(0.2)
        return vraie(racine)

    build_envs.liste_envs = espion
    try:
        res = fl.liste(d)
        verifie(fl.liste(d) is res and len(appels), 1, "cache : 2e appel sans changement = meme objet, liste_envs appele une fois")
        fils = [threading.Thread(target=fl.liste, args=(d,)) for _ in range(4)]
        [f.start() for f in fils]
        [f.join() for f in fils]
        verifie(len(appels), 1, "cache : appels simultanes sans changement, toujours un seul calcul")
        # persist modifie (taille differente : la date seule peut etre identique sur une ecriture rapprochee)
        p = d / "data/cave/tasmota32s3-a/_persist.json"
        p.write_text(persist("carte-renommee"), encoding="utf-8")
        res2 = fl.liste(d)
        verifie((len(appels), [c["hote"] for c in res2["cartes"]]), (2, ["carte-renommee"]), "cache : persist modifie = recalcul")
        # .h modifie
        h = d / "tasmota" / "user_config_override.h"
        h.write_text(h.read_text(encoding="utf-8").replace("#if defined(FIRMWARE_A)\n",
                                                           '#if defined(FIRMWARE_A)\n#define WIFI_IP_ADDRESS "192.168.0.50"\n'), encoding="utf-8")
        res_h = fl.liste(d)
        verifie((len(appels), [c["adresse"] for c in res_h["cartes"]]), (3, ["192.168.0.50"]), "cache : user_config_override.h modifie = recalcul")
        # fichier ini modifie
        ini = d / "platformio_tasmota_cenv.ini"
        ini.write_text(ini.read_text(encoding="utf-8") + "\n[env:tasmota32s3-cave-b]\nextends = env:tasmota32_base\nbuild_flags = -DFIRMWARE_B\n",
                       encoding="utf-8")
        fl.liste(d)
        verifie(len(appels), 4, "cache : ini modifie = recalcul")
        # persist ajoute
        (d / "data/cave/tasmota32s3-b").mkdir(parents=True)
        (d / "data/cave/tasmota32s3-b/_persist.json").write_text(persist("b"), encoding="utf-8")
        res3 = fl.liste(d)
        verifie((len(appels), sorted(c["env"] for c in res3["cartes"])), (5, [env, "tasmota32s3-cave-b"]), "cache : persist ajoute = recalcul")
        fl.liste(d)
        verifie(len(appels), 5, "cache : et de nouveau stable ensuite")
        # prechauffage : un fil qui remplit le cache, sans lever pour un depot absent
        d2 = depot(sec("FIRMWARE_A"), {env: persist("p")}, {env: "FIRMWARE_A"})
        n = len(appels)
        fl.prechauffe(d2).join()
        res4 = fl.liste(d2)
        verifie((len(appels) - n, bool(res4["cartes"])), (1, True), "prechauffe : un calcul, la premiere liste suivante n'en refait pas")
        fl.prechauffe(Path("/depot-inexistant")).join()
        verifie(True, True, "prechauffe : depot absent, aucune exception")
    finally:
        build_envs.liste_envs = vraie


if __name__ == "__main__":
    for cas in (cas_esclave, cas_persist_illisible, cas_sans_use_ftp, cas_puce, cas_adresse, cas_identifiants,
                cas_concordance_generiques, cas_cache, cas_depot_reel):
        print(f"-- {cas.__name__}")
        cas()
    print("\nECHECS : " + (", ".join(ECHECS) if ECHECS else "aucun"))
    sys.exit(1 if ECHECS else 0)
