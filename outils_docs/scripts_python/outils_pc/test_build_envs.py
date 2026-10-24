"""Banc de build_envs (liste, classement, port COM, IP OTA) sur des .ini et un .h d'essai.

Code de sortie 0 = vert. Aucune lecture de pio ; les ecritures se font dans un dossier temporaire.
Le controle sur les vrais fichiers du depot est en lecture seule.
"""

import os
import re
import sys
import tempfile
from pathlib import Path

import build_envs as be

ECHECS = []
RACINE = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))

CENV = """\
[env:tasmota32-base]
extends                 = env:tasmota32_base        ; heriter
build_flags             = ${env:tasmota32_base.build_flags}
                           -D FIRMWARE_TASMOTA32

[env:tasmota32s3-base-N16R8]
extends                 = env:tasmota32s3
upload_port             = COM11
build_flags             = ${env:tasmota32s3.build_flags}

[env:tasmota-pompe-piscine]
extends                 =   env:tasmota
build_flags             =   ${env:tasmota.build_flags}
                            -D FIRMWARE_ESP8266_POMPE_PISCINE

[env:tasmota32-cave]
extends                 = env:tasmota32-base
; Upload OTA
upload_port             = COM3          ; <- commente pour passer en OTA
monitor_port            = COM3
build_flags             = ${env:tasmota32-base.build_flags}
                           -D FIRMWARE_CAVE ; perso

[env:tasmota32s3-garage]
; upload_port             = COM10
extends                 = env:tasmota32s3-base-N16R8
build_flags             = ${env:tasmota32s3-base-N16R8.build_flags}
                           -D FIRMWARE_GARAGE
monitor_port            = COM11

[env:tasmota32c6-idf]
extends                 = env:tasmota32_idf55_base,
                          env:tasmota32-base
build_flags             = -D FIRMWARE_C6
monitor_port            = COM5

[env:tasmota32s3-sans-port]
extends                 = env:tasmota32-base
build_flags             = ${env:tasmota32-base.build_flags}
                           -D FIRMWARE_SANSPORT
"""
ENV32 = """\
[env:tasmota32_base]
board                   = esp32
extra_scripts           = ${esp32_defaults.extra_scripts}

[env:tasmota32c3-safeboot]
extends                 = env:tasmota32_base
build_flags             = ${env:tasmota32_base.build_flags}
                          -DFIRMWARE_SAFEBOOT

[env:tasmota32s3]
extends                 = env:tasmota32_base
build_flags             = ${env:tasmota32_base.build_flags}
                         -DFIRMWARE_TASMOTA32

[env:tasmota32p4]
extends                 = env:tasmota32_idf55_base
build_flags             = -DFIRMWARE_P4

[env:tasmota32-FR]
extends                 = env:tasmota32
build_flags             = ${env:tasmota32.build_flags} -DMY_LANGUAGE=fr_FR
"""
ENV8266 = """\
[env:tasmota]
build_flags             = -DFIRMWARE_TASMOTA

[env:tasmota-lite]
extends                 = env:tasmota
build_flags             = ${env:tasmota.build_flags} -DFIRMWARE_LITE
"""
OVERRIDE = """\
[env]
;upload_port             = COM4

[env:tasmota32_base]
monitor_speed           = 115200
extra_scripts           =
                            pre:outils_docs/scripts_python/build/pre_utilitaires_platformio.py
                            post:outils_docs/scripts_python/build/post_lto_parallele.py

[env:tasmota32_idf55_base]
monitor_speed           = 115200
extra_scripts           =
                            pre:outils_docs/scripts_python/build/pre_utilitaires_platformio.py
"""
ENTETE_H = """\
#define WIFI_IP_ADDRESS "0.0.0.0"
#if defined(FIRMWARE_CAVE) || defined(FIRMWARE_CAVE2)
    #ifdef WIFI_IP_ADDRESS
        #undef WIFI_IP_ADDRESS
    #endif
    #define WIFI_IP_ADDRESS "192.168.0.243"
#elif defined(FIRMWARE_GARAGE)
    #if 1
    #endif
    #define WIFI_IP_ADDRESS "0.0.0.0"
#elif defined(FIRMWARE_SIMPLE)
    #define WIFI_IP_ADDRESS "10.0.0.5"
#endif
"""


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def depot_essai(dossier):
    d = Path(dossier)
    for nom, texte in (("platformio_tasmota_cenv.ini", CENV), ("platformio_tasmota_env32.ini", ENV32),
                       ("platformio_tasmota_env.ini", ENV8266), ("platformio_override.ini", OVERRIDE)):
        (d / nom).write_bytes(texte.encode("utf-8"))
    (d / "tasmota").mkdir()
    (d / "tasmota" / "user_config_override.h").write_text(ENTETE_H, encoding="utf-8")
    return d


def refuse(racine, env, port):
    try:
        be.ecrit_port(racine, env, port)
    except ValueError:
        return True
    return False


def section(racine, env):
    """Texte de la section `env` du cenv d'essai."""
    texte = (racine / be.FICHIER_CENV).read_bytes().decode("utf-8")
    morceau = texte.split(f"[env:{env}]", 1)[1]
    return morceau.split("\n[", 1)[0]


def test_liste(racine):
    envs = {e.nom: e for e in be.liste_envs(racine)}
    verifie(envs["tasmota32-cave"].famille, "cartes", "classement : env cenv sans -base -> cartes")
    verifie(envs["tasmota32s3-base-N16R8"].famille, "bases", "classement : -base -> bases")
    verifie((envs["tasmota32-FR"].famille, envs["tasmota32-FR"].sous_groupe), ("amont", "langues"),
            "classement : tasmota32-FR -> amont/langues")
    verifie((envs["tasmota32c3-safeboot"].famille, envs["tasmota32c3-safeboot"].sous_groupe),
            ("amont", "safeboot"), "classement : safeboot -> amont/safeboot")
    verifie((envs["tasmota-lite"].famille, envs["tasmota-lite"].sous_groupe), ("amont", "esp8266"),
            "classement : tasmota-lite -> amont/esp8266")
    verifie(envs["tasmota32s3"].sous_groupe, "esp32", "classement : tasmota32s3 -> amont/esp32")
    verifie(("tasmota32_base" in envs, "tasmota32_idf55_base" in envs), (False, False),
            "classement : les bases PlatformIO sont absentes de la liste")
    verifie(envs["tasmota32-cave"].ecrivable and not envs["tasmota32s3"].ecrivable, True,
            "ecrivable : cenv seulement")
    verifie(envs["tasmota32-cave"].firmware, "FIRMWARE_CAVE", "firmware : dernier -D FIRMWARE_*")
    verifie(envs["tasmota32s3-garage"].firmware, "FIRMWARE_GARAGE", "firmware : derive d'une base")
    verifie((envs["tasmota32-cave"].port, envs["tasmota32-cave"].port_herite), ("COM3", False),
            "port_direct (commentaire en fin de ligne ignore)")
    verifie((envs["tasmota32s3-garage"].port, envs["tasmota32s3-garage"].port_herite), ("COM11", True),
            "port_herite via extends, ligne ';' ignoree")
    verifie((envs["tasmota32s3-sans-port"].port, envs["tasmota32s3-sans-port"].port_herite), ("", False),
            "port_absent")
    verifie(envs["tasmota32-cave"].ip, "192.168.0.243", "ip_bloc_ou (defined(A) || defined(B))")
    verifie(envs["tasmota32s3-garage"].ip, "", "ip_dhcp_vide (0.0.0.0)")
    verifie(envs["tasmota32s3-sans-port"].ip, "", "ip : firmware sans bloc -> vide")
    verifie((envs["tasmota-pompe-piscine"].ota_possible, envs["tasmota-lite"].ota_possible,
             envs["tasmota32-cave"].ota_possible, envs["tasmota32s3"].ota_possible),
            (False, False, True, True), "ota_esp8266_grise")


def test_ota_idf55():
    with tempfile.TemporaryDirectory() as t:
        envs = {e.nom: e for e in be.liste_envs(depot_essai(t))}
    verifie(envs["tasmota32p4"].ota_possible, True, "ota : env qui n'herite que de tasmota32_idf55_base")
    verifie(envs["tasmota32c6-idf"].ota_possible, True, "ota : extends multiple")
    with tempfile.TemporaryDirectory() as t:
        r = depot_essai(t)
        p = r / "platformio_override.ini"
        p.write_bytes(p.read_bytes().replace(b"pre:outils_docs/scripts_python/build/pre_utilitaires_platformio.py",
                                             b"post:autre.py"))
        envs = {e.nom: e for e in be.liste_envs(r)}
    verifie(envs["tasmota32s3"].ota_possible, False, "ota : sans pre-script dans les extra_scripts -> faux")


def test_ip_comme_original():
    """lit_ip_ota doit donner, sur le vrai .h, le meme resultat que ota-files-uploader.py."""
    src = (RACINE / "outils_docs" / "scripts_python" / "build" / "ota-files-uploader.py").read_text(encoding="utf-8")
    debut = src.index("def _lire_ip_override")
    fin = src.index("def _configurer_upload_ota")
    ns = {"re": re, "Path": Path}
    exec(src[debut:fin], ns)
    texte = (RACINE / "tasmota" / "user_config_override.h").read_text(encoding="utf-8", errors="ignore")
    defines = sorted(set(re.findall(r"defined\s*\(\s*(FIRMWARE_\w+)\s*\)", texte)))
    ecarts = []
    for d in defines:
        attendu = ns["_lire_ip_override"](str(RACINE), d)
        attendu = "" if attendu in (None, "0.0.0.0") else attendu
        if be.lit_ip_ota(texte, d) != attendu:
            ecarts.append(d)
    verifie((len(defines) > 10, ecarts), (True, []), f"ip : identique a l'original sur {len(defines)} defines du vrai .h")


def test_ip():
    verifie(be.lit_ip_ota(ENTETE_H, "FIRMWARE_SIMPLE"), "10.0.0.5", "ip_bloc_simple")
    verifie(be.lit_ip_ota(ENTETE_H, "FIRMWARE_CAVE2"), "192.168.0.243", "ip_bloc_ou : second define")
    verifie(be.lit_ip_ota(ENTETE_H, "FIRMWARE_INCONNU"), "", "ip : define inconnu")
    verifie(be.lit_ip_ota(ENTETE_H, ""), "", "ip : firmware vide")


def test_ecriture():
    with tempfile.TemporaryDirectory() as t:
        r = depot_essai(t)
        be.ecrit_port(r, "tasmota32s3-base-N16R8", "COM7")
        verifie("upload_port             = COM7\n" in section(r, "tasmota32s3-base-N16R8"), True,
                "ecrit_port_modifie")
        verifie((r / (be.FICHIER_CENV + ".bak")).read_bytes().decode(), CENV,
                "ecrit_port_sauvegarde (.bak = ancien contenu)")
        verifie([e.port for e in be.liste_envs(r) if e.nom == "tasmota32s3-base-N16R8"], ["COM7"],
                "ecrit_port_modifie : relu par liste_envs")
    with tempfile.TemporaryDirectory() as t:
        r = depot_essai(t)
        be.ecrit_port(r, "tasmota32s3-sans-port", "COM9")
        s = section(r, "tasmota32s3-sans-port")
        verifie(s.splitlines()[2], "upload_port             = COM9", "ecrit_port_ajoute : apres extends")
    with tempfile.TemporaryDirectory() as t:
        r = depot_essai(t)
        be.ecrit_port(r, "tasmota32s3-garage", "COM21")
        s = section(r, "tasmota32s3-garage")
        verifie(("; upload_port             = COM10" in s, s.count("\nupload_port             = COM21\n")),
                (True, 1), "ecrit_port_herite : ligne ';' intacte, ligne active ajoutee")
        e = [x for x in be.liste_envs(r) if x.nom == "tasmota32s3-garage"][0]
        verifie((e.port, e.port_herite), ("COM21", False), "ecrit_port_herite : relu, plus herite")
    with tempfile.TemporaryDirectory() as t:
        r = depot_essai(t)
        be.ecrit_port(r, "tasmota32c6-idf", "COM8")
        s = section(r, "tasmota32c6-idf")
        verifie(s.splitlines()[1:5], ["extends                 = env:tasmota32_idf55_base,",
                                      "                          env:tasmota32-base",
                                      "upload_port             = COM8", "build_flags             = -D FIRMWARE_C6"],
                "ecrit_port_ajoute : apres un extends multi-ligne")
    with tempfile.TemporaryDirectory() as t:
        r = depot_essai(t)
        be.ecrit_port(r, "tasmota32-cave", "COM15")
        verifie("upload_port             = COM15          ; <- commente pour passer en OTA\n"
                in section(r, "tasmota32-cave"), True, "ecrit_port_garde_commentaire")
    with tempfile.TemporaryDirectory() as t:
        r = depot_essai(t)
        be.ecrit_port(r, "tasmota32-cave", "")
        s = section(r, "tasmota32-cave")
        verifie(("upload_port" in s, "monitor_port            = COM3" in s), (False, True),
                "ecrit_port_vide_supprime")
        be.ecrit_port(r, "tasmota32-cave", "")
        verifie("monitor_port" in section(r, "tasmota32-cave"), True, "ecrit_port_vide : sans ligne = rien")
    with tempfile.TemporaryDirectory() as t:
        r = depot_essai(t)
        avant = (r / be.FICHIER_CENV).read_bytes()
        verifie(refuse(r, "tasmota32s3", "COM3"), True, "ecrit_port_refuse_amont")
        verifie(refuse(r, "inexistant", "COM3"), True, "ecrit_port_refuse_env_inconnu")
        for mauvais in ("COM3\n[env:x]", "COM", "COM1234", "com3", "/dev/ttyACM0", "COM3 ", "COM3\n"):
            verifie(refuse(r, "tasmota32-cave", mauvais), True, f"ecrit_port_refuse_injection {mauvais!r}")
        verifie((r / be.FICHIER_CENV).read_bytes(), avant, "refus : fichier intact")
    with tempfile.TemporaryDirectory() as t:
        r = depot_essai(t)
        p = r / be.FICHIER_CENV
        p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
        be.ecrit_port(r, "tasmota32s3-sans-port", "COM9")
        brut = p.read_bytes()
        verifie((b"\r\n" in brut, brut.replace(b"\r\n", b"").count(b"\n")), (True, 0),
                "ecrit_port : fins de ligne CRLF gardees")


FS_CENV = """\
[env:tasmota32-base]
extends                 = env:tasmota32_base
custom_files_upload     =   ${env:tasmota32_base.custom_files_upload}

[env:tasmota32s3-base-N16R8]
extends                 = env:tasmota32s3
custom_files_upload     = ${env:tasmota32s3.custom_files_upload}
; scripts tasmota Berry en option
                            tasmota/berry/modules/Partition_Wizard/partition_wizard.bec

[env:tasmota32-cave]
extends                 = env:tasmota32-base
custom_files_upload     =   ${env:tasmota32-base.custom_files_upload}
                            data/cave/tasmota32-cave              ; scripts du module

[env:tasmota32s3-garage]
extends                 = env:tasmota32s3-base-N16R8

[env:tasmota32-sans-fichier]
extends                 = env:tasmota32-base

[env:tasmota-pompe]
extends                 = env:tasmota
custom_files_upload     = data/piscine
"""
FS_ENV32 = """\
[env:tasmota32_base]
extra_scripts           = pre:outils_docs/scripts_python/build/pre_utilitaires_platformio.py
custom_files_upload     = no_files

[env:tasmota32s3]
extends                 = env:tasmota32_base
"""
FS_ENV8266 = """\
[env:tasmota]
build_flags             = -DFIRMWARE_TASMOTA
"""


def test_fs_avec_firmware():
    """I1 : un upload firmware par cable flashe aussi le FS des que custom_files_upload resolu a des fichiers.

    post_esp32.py:139-245 reconstruit littlefs.bin a chaque edition des liens (CFG_HOLDER change a chaque
    run : toujours une edition des liens), puis :419-440 l'ajoute a la commande esptool.
    """
    with tempfile.TemporaryDirectory() as t:
        r = Path(t)
        for nom, texte in (("platformio_tasmota_cenv.ini", FS_CENV), ("platformio_tasmota_env32.ini", FS_ENV32),
                           ("platformio_tasmota_env.ini", FS_ENV8266)):
            (r / nom).write_text(texte, encoding="utf-8")
        envs = {e.nom: getattr(e, "fs_avec_firmware", None) for e in be.liste_envs(r)}
    verifie(envs.get("tasmota32-cave"), True, "fs_avec_firmware : ${env:...} resolu + dossier de la carte")
    verifie(envs.get("tasmota32s3-base-N16R8"), True,
            "fs_avec_firmware : no_files herite + fichier sur une ligne de suite (apres un commentaire)")
    verifie(envs.get("tasmota32s3-garage"), True, "fs_avec_firmware : option heritee par extends")
    verifie((envs.get("tasmota32-sans-fichier"), envs.get("tasmota32-base"), envs.get("tasmota32s3")),
            (False, False, False), "fs_avec_firmware : no_files seul -> faux")
    verifie(envs.get("tasmota-pompe"), False, "fs_avec_firmware : ESP8266 (pas de post_esp32) -> faux")


def test_vrais_fichiers():
    """Lecture seule des vrais .ini."""
    envs = {e.nom: e for e in be.liste_envs(RACINE)}
    # Independant du nombre d'envs (l'utilisateur en ajoute) : au moins 15, et ceux cites ici presents.
    cites = ["tasmota32s3-garage-capteurs-cuve-modbus", "tasmota32s3-garage-serveur-modbus", "tasmota-pompe-piscine",
             "tasmota32-cave-serveur-rly", "tasmota32p4-garage-serveur-modbus", "tasmota32"]
    verifie((len([e for e in envs.values() if e.ecrivable]) >= 15, [c for c in cites if c not in envs]), (True, []),
            "reel : au moins 15 envs cenv listes, envs cites presents")
    if any(c not in envs for c in cites):
        return
    verifie(envs["tasmota32s3-garage-capteurs-cuve-modbus"].port, "COM12", "reel : cuve -> COM12")
    e = envs["tasmota32s3-garage-serveur-modbus"]
    verifie((e.port, e.port_herite), ("COM11", True), "reel : serveur-modbus -> COM11 herite")
    verifie(envs["tasmota-pompe-piscine"].ota_possible, False, "reel : pompe piscine (ESP8266) sans OTA")
    verifie(envs["tasmota32-cave-serveur-rly"].port, "COM11", "reel : cave -> COM11 (commentaire de fin)")
    verifie((getattr(envs["tasmota32s3-garage-capteurs-cuve-modbus"], "fs_avec_firmware", None),
             getattr(envs["tasmota32p4-garage-serveur-modbus"], "fs_avec_firmware", None),
             getattr(envs["tasmota32"], "fs_avec_firmware", None),
             getattr(envs["tasmota-pompe-piscine"], "fs_avec_firmware", None)),
            (True, True, False, False), "reel : FS flashe avec le firmware pour cuve et P4, pas pour tasmota32 ni la pompe")


def principal():
    with tempfile.TemporaryDirectory() as t:
        test_liste(depot_essai(t))
    test_ota_idf55()
    test_ip()
    test_ip_comme_original()
    test_ecriture()
    test_fs_avec_firmware()
    test_vrais_fichiers()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
