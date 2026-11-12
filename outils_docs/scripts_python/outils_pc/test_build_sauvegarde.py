#!/usr/bin/env python3
"""Banc de build_sauvegarde.py et decode_config.py : carte simulee, vrai decode-config, .dmp fabrique (aucun vrai
mot de passe). Code 0 = vert. Lent : chaque lecture de .dmp lance decode-config (5 a 10 s).

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_build_sauvegarde.py
Prealable : `python decode_config.py` (environnement de decode-config).
"""
import re
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import build_sauvegarde as bs
import decode_config as dc
from build_ota_carte_simulee import Carte

ECHECS = []
ENTETE = (Path(__file__).resolve().parents[3] / "tasmota" / "include" / "tasmota.h").read_text(encoding="utf-8")
ENV = "tasmota32-essai"
RETOUR = (5.0, 0.0, 0.05)
# Indices ESP32 de SettingsTextIndex (tasmota.h) : 95 = SET_SWITCH_TXT9, 126 = SET_APBSSID1 (inconnu de decode-config)
TEXTES = {6: "secret-wifi-1", 8: "CARTE-ESSAI", 15: "secret-mqtt", 53: "Relais 1", 95: "Inter 9", 118: "influxdb",
          122: "db", 126: "11:22:33:44:55:66"}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def leve(fonction, exception, libelle):
    try:
        fonction()
    except exception as erreur:
        verifie(True, True, f"{libelle} ({erreur})")
        return
    verifie("aucune exception", exception.__name__, libelle)


def dmp(version=0x10000002, plateforme=1, textes=None, drvset=b"\x01" * 536):
    """.dmp au format de settings.ino::SettingsConfigBackup : /.settings, Settings, /.drvset003, XOR."""
    s = bytearray(4096)
    struct.pack_into("<H", s, 2, 4096)
    struct.pack_into("<I", s, 8, version)
    s[0xF36] = plateforme
    t = {**TEXTES, **(textes or {})}
    s[0x17:0x17 + 699] = b"\0".join(t.get(i, "").encode() for i in range(129)).ljust(699, b"\0")[:699]
    struct.pack_into("<I", s, 0xFFC, zlib.crc32(bytes(s[:4092]), 0xFFFFFFFF))
    fichier = b"/.drvset003".ljust(14, b"\0") + struct.pack("<H", len(drvset)) + drvset.ljust((len(drvset) // 16) * 16 + 16, b"\0")
    corps = bytes(s) + fichier
    d = bytearray(b"/.settings".ljust(14, b"\0") + struct.pack("<H", 16 + len(corps)) + corps)
    for i in range(18, len(d)):
        d[i] ^= (dc.XOR + i) & 0xFF
    return bytes(d)


class Serie:
    def __init__(self, envoi=False):
        self.envoi = envoi

    def envoi_en_cours(self):
        return self.envoi


JOINTS = []


def controle_esp8266():
    """Reponses de carte simulees : 12.0.2 sans FS (.45), FS present, deux FS (JSON invalide), Zigbee, carte partie."""
    import build_sauvegarde_esp8266 as be
    fwr = '{"StatusFWR":{"Version":"12.0.2(tasmota)","BuildDateTime":"2022-06-20T12:45:43","Hardware":"ESP8285"}}'
    def carte(ufs='{"Command":"Unknown"}', pilotes="1,2,3,10"):
        rep = {"Status 2": fwr, "Ufs": ufs, "Status 4": '{"StatusMEM":{"Drivers":"%s"}}' % pilotes}
        return lambda _ip, cmnd, _delai: rep[cmnd]
    niveaux = lambda r: [m[0] for m in r["remarques"]]
    r = be.controle("192.168.0.45", 1, carte())
    verifie((niveaux(r), r["firmware"]), (["v", "v"], "12.0.2(tasmota) ESP8285 2022-06-20T12:45:43"),
            "esp8266 : sans FS ni Zigbee, rien a recuperer, firmware note")
    verifie(niveaux(be.controle("x", 1, carte(ufs='{"Ufs":{"Type":0,"Size":0,"Free":0}}'))), ["v", "v"],
            "esp8266 : FS de type 0 = pas de FS")
    verifie(niveaux(be.controle("x", 1, carte(ufs='{"Ufs":{"Type":2,"Size":1000,"Free":900}}')))[0], "o",
            "esp8266 : FS present signale")
    verifie(niveaux(be.controle("x", 1, carte(ufs='{"Ufs":{"Type":0,"Size":0,"Free":0},{"Type":2,"Size":9,"Free":9}}')))[0],
            "o", "esp8266 : deux FS (reponse qui n'est pas du JSON) : le second est vu")
    verifie(niveaux(be.controle("x", 1, carte(pilotes="1,2,23,45")))[0], "o", "esp8266 : pilote Zigbee signale")
    verifie(niveaux(be.controle("x", 1, carte(pilotes="1,2,123")))[0], "v", "esp8266 : 123 n'est pas le pilote 23")
    def partie(*_):
        raise OSError("timed out")
    r = be.controle("x", 1, partie)
    verifie((niveaux(r), "timed out" in r["remarques"][0][1]), (["o"], True), "esp8266 : carte partie, pas d'exception")
    verifie(niveaux(be.controle("mqtt://cave/lumiere", 1, partie)), ["o"], "esp8266 : par MQTT, controle non fait (signale)")


def banc():
    if not dc.utilisable():
        print("KO   decode-config absent : lancer outils_pc/decode_config.py")
        return 1

    bs.joint_par_maitre = lambda adresse, *_: JOINTS.append(adresse)   # carte simulee en 127.0.0.1:port, sans maitre

    with tempfile.TemporaryDirectory() as racine:
        carte = Carte()
        carte.config = dmp()

        # -- prise et liste
        f1 = bs.prend(racine, ENV, carte.ip, "manuelle")
        verifie((f1["version"], f1["editable"], f1["origine"], f1["taille"]), ("16.0.0.2", True, "manuelle", len(carte.config)),
                "prend : fiche (version, modifiable, origine, taille)")
        verifie((Path(racine) / bs.DOSSIER / ENV / f1["fichier"]).read_bytes(), carte.config, "prend : fichier = /dl de la carte")
        verifie(JOINTS, [carte.ip], "prend : adresse IP:port -> redirection du maitre posee d'abord")
        carte.config = b"<html>pas une configuration</html>"
        leve(lambda: bs.prend(racine, ENV, carte.ip, "manuelle"), RuntimeError, "prend : reponse qui n'est pas un .dmp refusee")
        carte.config = dmp()

        # -- parametres : groupes, mots de passe masques, fichiers des pilotes
        p = bs.parametres(racine, ENV, f1["fichier"])
        tout = {k: v for g in p["groupes"].values() for k, v in g.items()}
        verifie(tout.get("hostname"), "CARTE-ESSAI", "parametres : nom d'hote lu")
        verifie((tout.get("sta_pwd", [None])[0] if isinstance(tout.get("sta_pwd"), list) else tout.get("sta_pwd"),
                 tout.get("mqtt_pwd")), ("***", "***"), "parametres : mots de passe masques")
        verifie("secret" in repr(p), False, "parametres : aucun mot de passe en clair dans la reponse")
        verifie(p["fichiers"], {"/.drvset003": 536}, "parametres : fichier .drvset003 et sa taille")
        verifie("Wifi" in p["groupes"] and "MQTT" in p["groupes"], True, "parametres : groupes Wifi et MQTT")

        # -- copie modifiee
        origine = (Path(racine) / bs.DOSSIER / ENV / f1["fichier"]).read_bytes()
        f2 = bs.copie(racine, ENV, f1["fichier"], {"hostname": "CARTE-MODIFIEE", "mqtt_pwd": bs.MASQUE})
        relu = dc.decode(Path(racine) / bs.DOSSIER / ENV / f2["fichier"])
        verifie((f2["origine"], f2["source"], relu["hostname"]), ("modifiée", f1["fichier"], "CARTE-MODIFIEE"),
                "copie : nouvelle sauvegarde modifiee, valeur relue")
        verifie(relu["mqtt_pwd"], "secret-mqtt", "copie : mot de passe laisse a *** garde sa vraie valeur")
        verifie((relu["influxdb_host32"], relu["influxdb_bucket32"]), ("influxdb", "db"), "copie : champs non modifies intacts")
        verifie((Path(racine) / bs.DOSSIER / ENV / f1["fichier"]).read_bytes(), origine, "copie : l'originale n'est pas reecrite")
        # Texte commun ESP8266/ESP32 (button_text) et champ binaire (tele_period) : decode-config seul tronquerait la reserve
        f4 = bs.copie(racine, ENV, f1["fichier"], {"button_text": ["Autre"] + [""] * 15, "tele_period": 120})
        chemin4 = Path(racine) / bs.DOSSIER / ENV / f4["fichier"]
        relu = dc.decode(chemin4)
        verifie((relu["button_text"][0], relu["tele_period"], relu["influxdb_host32"]), ("Autre", 120, "influxdb"),
                "copie : texte commun et champ binaire ecrits, InfluxDB intact")
        bruts = dc.textes_bruts(chemin4.read_bytes())
        verifie((bruts[95], bruts[126]), (b"Inter 9", b"11:22:33:44:55:66"), "copie : textes d'interrupteur 9 et APBSSID1 intacts")
        leve(lambda: bs.copie(racine, ENV, f1["fichier"], {"hostname": "X" * 700}), ValueError, "copie : reserve de textes pleine refusee")
        # ESP8266 (config_version 0) : textes decales de 27 apres SET_ADC_PARAM1 (tasmota.h::SettingsTextIndex) ;
        # 80 = SET_SWITCH_TXT1, 89 = SET_RGX_SSID, 91 = SET_INFLUXDB_HOST, 95 = SET_INFLUXDB_BUCKET
        esp8266 = Path(racine) / bs.DOSSIER / "tasmota-essai" / "20261112-000000_manuelle.dmp"
        esp8266.parent.mkdir(parents=True)
        esp8266.write_bytes(dmp(version=0x0C000200, plateforme=0,
                                textes={118: "", 122: "", 126: "", 80: "Inter 1", 91: "influxdb", 95: "db"}))
        f5 = bs.copie(racine, "tasmota-essai", esp8266.name, {"rgx_ssid": "AP-ESSAI", "hostname": "SONOFF-ESSAI"})
        chemin5 = esp8266.parent / f5["fichier"]
        relu = dc.decode(chemin5)
        verifie((relu["rgx_ssid"], relu["hostname"], relu["influxdb_host"], relu["influxdb_bucket"]),
                ("AP-ESSAI", "SONOFF-ESSAI", "influxdb", "db"), "copie ESP8266 : textes ecrits a leur indice ESP8266")
        bruts = dc.textes_bruts(chemin5.read_bytes())
        verifie((bruts[80], bruts[89]), (b"Inter 1", b"AP-ESSAI"), "copie ESP8266 : interrupteur 1 intact, rgx_ssid en 89")
        # Meme nom sur les deux puces mais indice different (98 sur ESP8266, 125 sur ESP32), cle connue depuis 15.0 :
        # _pose_textes le placait en 125 et la relecture refusait la copie
        recent = esp8266.with_name("20261112-000001_manuelle.dmp")
        recent.write_bytes(dmp(plateforme=0, textes={118: "", 122: "", 126: "", 80: "Inter 1", 91: "influxdb", 95: "db"}))
        f6 = bs.copie(racine, "tasmota-essai", recent.name, {"telegram_fingerprint": "AB CD"})
        relu = dc.decode(esp8266.parent / f6["fichier"])
        verifie((relu["telegram_fingerprint"], relu["influxdb_host"]), ("AB CD", "influxdb"),
                "copie ESP8266 : telegram_fingerprint ecrit en 98, le reste intact")
        leve(lambda: bs.copie(racine, ENV, f1["fichier"], {"button_text": [""] * 17}), ValueError, "copie : texte multiple trop long refuse")
        avant = len(bs.liste(racine, ENV))
        ecrit = dc._pose_textes
        dc._pose_textes = lambda chemin, textes: ecrit(chemin, dict(textes, influxdb_host32=""))   # redacteur fautif
        leve(lambda: bs.copie(racine, ENV, f1["fichier"], {"hostname": "CARTE-FAUTIVE"}), RuntimeError,
             "copie : relecture qui s'ecarte de l'attendu -> refus")
        dc._pose_textes = ecrit
        verifie(len(bs.liste(racine, ENV)), avant, "copie : rien n'est garde quand la relecture s'ecarte")
        leve(lambda: bs.copie(racine, ENV, f1["fichier"], {"settings": {}}), ValueError, "copie : fichiers des pilotes non modifiables")
        leve(lambda: bs.copie(racine, ENV, f1["fichier"], {"inconnu": 1}), ValueError, "copie : parametre inconnu refuse")
        verifie([f["fichier"] for f in bs.liste(racine, ENV)], [f4["fichier"], f2["fichier"], f1["fichier"]],
                "liste : la plus recente d'abord")
        noms = re.findall(r"SET_[A-Z0-9_]+", re.sub(r"#ifdef ESP8266.*?#endif", "", ENTETE[ENTETE.index("enum SettingsTextIndex {"):
                                                                                        ENTETE.index("SET_MAX,")], flags=re.S))
        verifie(noms[:len(dc.disposition()["noms"])], dc.disposition()["noms"],
                "textes : indices ESP32 de decode-config = SettingsTextIndex de tasmota.h")
        verifie(noms[dc.TEXTES_CONNUS:], ["SET_APBSSID1", "SET_APBSSID2"], "textes : seuls APBSSID1/2 sont inconnus de decode-config")

        # -- noms hostiles
        leve(lambda: bs.parametres(racine, ENV, "../x.dmp"), ValueError, "nom de sauvegarde hostile refuse")
        leve(lambda: bs.liste(racine, "../.."), ValueError, "nom d'env hostile refuse")
        leve(lambda: bs.prend(racine, "..", carte.ip, "manuelle"), ValueError, "env « .. » refuse (rien hors de sauvegardes_cartes)")
        jetable = bs.prend(racine, ENV, carte.ip, "manuelle")["fichier"]
        leve(lambda: bs.supprime(racine, ENV, [jetable, "../x.dmp"]), ValueError, "supprime : un nom invalide dans la liste refuse")
        verifie((Path(racine) / bs.DOSSIER / ENV / jetable).is_file(), True, "supprime : refus -> rien n'est efface")
        verifie(bs.supprime(racine, ENV, [jetable])["supprimees"], [jetable], "supprime : sauvegarde effacee")
        verifie(sorted(x.name for x in (Path(racine) / bs.DOSSIER / ENV).glob(jetable[:-4] + ".*")), [], "supprime : .dmp et fiche effaces")
        leve(lambda: bs.supprime(racine, ENV, []), ValueError, "supprime : liste vide refusee")
        carte.config = b"<html>" + b"x" * 5000 + b"</html>"
        leve(lambda: bs.prend(racine, ENV, carte.ip, "manuelle"), RuntimeError, "prend : page HTML longue refusee (CRC)")
        carte.config = dmp()
        leve(lambda: bs.copie(racine, ENV, f1["fichier"], {"mqtt_pwd": bs.MASQUE}), ValueError,
             "copie : mots de passe laisses a *** seulement -> aucune modification")
        f5 = bs.copie(racine, ENV, f1["fichier"], {"sta_pwd": "nouveau-wifi"})
        verifie(dc.decode(Path(racine) / bs.DOSSIER / ENV / f5["fichier"])["sta_pwd"], ["nouveau-wifi", ""],
                "copie : mot de passe Wi-Fi saisi = 1er reseau, le 2e garde")
        verifie(sorted(k for k in dc.groupes() if bs.SECRET.search(k)),
                sorted(["influxdb_token", "influxdb_token32", "mqtt_pwd", "pn532_password", "rgx_pwassword",
                        "rgx_pwassword_esp32", "sta_pwd", "telegram_token", "web_password", "zb_precfgkey_h",
                        "zb_precfgkey_l"]), "secrets : toutes les cles sensibles connues de decode-config masquees")

        # -- version non verifiee : restaurable, pas lisible
        carte.config = dmp(version=0x10000003)
        f3 = bs.prend(racine, ENV, carte.ip, "manuelle")
        p3 = bs.parametres(racine, ENV, f3["fichier"])
        verifie((f3["editable"], p3["editable"], p3["groupes"], "non vérifiée" in p3["message"]), (False, False, {}, True),
                "version 16.0.0.3 : ni lue ni modifiable")
        leve(lambda: bs.copie(racine, ENV, f3["fichier"], {"hostname": "X"}), ValueError, "version 16.0.0.3 : copie refusee")

        # -- comparaison
        carte.config = dmp()
        verifie(bs.compare(racine, ENV, f1["fichier"], adresse=carte.ip)["ecarts"], [], "compare : aucun ecart avec la carte")
        ecarts = bs.compare(racine, ENV, f1["fichier"], autre=f2["fichier"])["ecarts"]
        verifie([e["cle"] for e in ecarts], ["hostname"], "compare : l'ecart de la copie")
        carte.config = dmp(textes={15: "autre-secret"})
        e = bs.compare(racine, ENV, f1["fichier"], adresse=carte.ip)["ecarts"]
        verifie((e[0]["cle"], e[0]["a"], e[0]["b"]) if e else None, ("mqtt_pwd", "***", "***"), "compare : mot de passe change, masque")

        # -- restauration
        carte.config = dmp(textes={8: "AVANT-RESTAURATION"})
        leve(lambda: bs.restaure(racine, ENV, f2["fichier"], carte.ip, "faux", retour=RETOUR), RuntimeError,
             "restaure : jeton faux refuse")
        verifie(carte.config, dmp(textes={8: "AVANT-RESTAURATION"}), "restaure : rien d'envoye sur un jeton faux")
        jeton = bs.empreinte(racine, ENV, f2["fichier"])
        res = bs.restaure(racine, ENV, f2["fichier"], carte.ip, jeton, retour=RETOUR)
        verifie(carte.config, (Path(racine) / bs.DOSSIER / ENV / f2["fichier"]).read_bytes(), "restaure : la carte a recu la sauvegarde")
        verifie(res["avant"]["origine"], "avant restauration", "restaure : sauvegarde de la carte prise d'abord")
        verifie(dc.decode(Path(racine) / bs.DOSSIER / ENV / res["avant"]["fichier"])["hostname"], "AVANT-RESTAURATION",
                "restaure : la sauvegarde d'avant porte l'ancienne config")
        verifie(res["ecarts"], [], "restaure : aucun ecart relu apres le redemarrage")
        verifie([m for m, c in carte.requetes("/rs") + carte.requetes("/u2")], ["GET", "POST"], "restaure : /rs puis /u2")
        carte.coupures_u2 = 1                              # la carte coupe /u2 en redemarrant
        res = bs.restaure(racine, ENV, f2["fichier"], carte.ip, jeton, retour=RETOUR)
        verifie((res["avant"]["origine"], carte.coupures_u2), ("avant restauration", 0),
                "restaure : /u2 coupe -> pas d'echec annonce, retour attendu et ecarts relus")
        carte.config = dmp(plateforme=2)
        envoye = carte.config
        leve(lambda: bs.restaure(racine, ENV, f2["fichier"], carte.ip, jeton, retour=RETOUR), RuntimeError,
             "restaure : sauvegarde d'une autre puce refusee")
        verifie(carte.config, envoye, "restaure : rien d'envoye a une autre puce")

        # -- avant un flash serie (build_serie.Serie._sauve_drvset) : calibrage ET configuration
        import types
        import build_serie
        carte.config = dmp()
        carte.flash["/.drvset003"] = b"\x07" * 536
        serie = build_serie.Serie.__new__(build_serie.Serie)
        evenements = []
        serie.racine, serie.dossier = Path(racine), Path(racine) / "outils"
        serie._ajoute = lambda *a, **k: evenements.append(k.get("detail", ""))
        reel = build_serie.build_envs.liste_envs
        build_serie.build_envs.liste_envs = lambda _: [types.SimpleNamespace(nom=ENV, ip=carte.ip)]
        deja = {f["fichier"] for f in bs.liste(racine, ENV)}
        drvset = serie._sauve_drvset(build_serie.Ligne(ENV, "com", "COM9", ""))
        nouvelles = [f["origine"] for f in bs.liste(racine, ENV) if f["fichier"] not in deja]
        verifie((drvset is not None, nouvelles), (True, ["avant flash"]), "avant flash : calibrage et configuration sauvegardes")
        verifie(any("configuration sauvegardée" in e for e in evenements), True, "avant flash : annonce dans le suivi")
        build_serie.build_envs.liste_envs = lambda _: [types.SimpleNamespace(nom=ENV, ip="")]
        verifie(serie._sauve_drvset(build_serie.Ligne(ENV, "com", "COM9", "")), None, "avant flash : sans adresse, rien de bloque")
        build_serie.build_envs.liste_envs = reel

        # -- ESP8266 : ce qui reste hors de Settings, lu sur la carte en ligne (build_sauvegarde_esp8266)
        controle_esp8266()
        carte.config = dmp(version=0x0C000200, plateforme=0)
        f8 = bs.prend(racine, ENV, carte.ip, "manuelle")
        verifie(("hors_config" in f8, "hors_config" in f1), (True, False), "prend : controle hors config pour un ESP8266 seulement")
        carte.config = dmp()

        # -- routes : refus pendant un envoi, verrou
        import threading
        verrou = threading.Lock()
        leve(lambda: bs.traite_post("/sauvegarde/prendre", {"env": ENV, "adresse": carte.ip}, Serie(True), racine, verrou,
                                    lambda d: d["adresse"]), RuntimeError, "routes : refus pendant un envoi de la serie")
        verrou.acquire()
        leve(lambda: bs.traite_post("/sauvegarde/prendre", {"env": ENV, "adresse": carte.ip}, Serie(), racine, verrou,
                                    lambda d: d["adresse"]), RuntimeError, "routes : une operation a la fois")
        verrou.release()
        verifie(bs.traite_post("/autre", {}, Serie(), racine, verrou, None), None, "routes : chemin etranger -> None")
        carte.ferme()

        # -- temoins rouges : sans ces gardes, le banc doit le voir
        sauve = bs.SECRET
        bs.SECRET = bs.re.compile(r"(?!)")                  # ne reconnait plus aucune cle
        verifie("secret" in repr(bs.parametres(racine, ENV, f1["fichier"])), True, "temoin : sans masquage, le secret se voit")
        bs.SECRET = sauve
        textes = dict(dc.disposition()["textes"])
        dc.disposition()["textes"].clear()                     # tout passe par decode-config : son defaut doit se voir
        leve(lambda: bs.copie(racine, ENV, f1["fichier"], {"hostname": "CARTE-SANS-PARADE"}), RuntimeError,
             "temoin : sans l'ecriture directe des textes, decode-config tronque la reserve (relecture en echec)")
        dc.disposition()["textes"].update(textes)

    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(banc())
