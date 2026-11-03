#!/usr/bin/env python3
"""Banc des ameliorations de l'onglet « Sauvegarde configuration » : liaison MQTT (build_sauvegarde_mqtt.py, carte
MQTT simulee qui suit xdrv_02_1_mqtt_file.ino), purge des sauvegardes automatiques, marques « reposé au démarrage ».
Aucun broker, aucune carte. Vrai decode-config (restauration relue). Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_build_sauvegarde_mqtt.py
"""
import base64
import hashlib
import json
import queue
import sys
import tempfile
import time
from pathlib import Path

import build_sauvegarde as bs
import build_sauvegarde_mqtt as bsm
import decode_config as dc
from test_build_sauvegarde import ENV, RETOUR, dmp, leve, verifie, ECHECS

RACINE = Path(__file__).resolve().parents[3]
TOPIC, MDP = "essai/carte", "mdp-essai"


class Message:
    def __init__(self, topic, payload):
        self.topic, self.payload = topic, payload


class CarteMqtt:
    """FileDownload / FileUpload de type 2 comme xdrv_02_1_mqtt_file.ino, sur une configuration en memoire."""

    def __init__(self, config):
        self.config, self.boite, self.recus = config, queue.Queue(), []
        self.muette = self.altere_md5 = self.refuse = False   # altere_md5 : lecture ; refuse : envoi
        self.bas, self.haut = None, None

    def _repond(self, commande, r):
        self.boite.put(Message(f"stat/{TOPIC}/{commande.upper()}", json.dumps(r).encode()))

    def recoit(self, topic, payload):
        self.recus.append((topic, payload))
        if self.muette or not topic.startswith(f"cmnd/{TOPIC}/"):
            return
        commande, texte = topic.rsplit("/", 1)[1], payload.decode()
        if texte == "0":
            self.bas = self.haut = None
            return self._repond(commande, {commande: "Aborted"})
        r = json.loads(texte) if len(texte) > 8 else {}
        if commande == "FileDownload":
            if "Type" in r:
                if r.get("Password") != MDP:
                    return self._repond(commande, {commande: "Error 1"})
                self.bas = {"id": 117, "pos": 0, "donnees": self.config}
                self._repond(commande, {commande: "Started"})
                return self._repond(commande, {"File": "Config.dmp", "Id": 117, "Type": 2, "Size": len(self.config)})
            b = self.bas
            if b["pos"] < len(b["donnees"]):
                morceau = b["donnees"][b["pos"]:b["pos"] + 700]
                b["pos"] += len(morceau)
                return self._repond(commande, {"Id": b["id"], "Data": base64.b64encode(morceau).decode()})
            md5 = "0" * 32 if self.altere_md5 else hashlib.md5(b["donnees"]).hexdigest()
            self._repond(commande, {"Id": b["id"], "Md5": md5})
            self.bas = None
            return self._repond(commande, {commande: "Done"})
        if "Type" in r:
            if r.get("Password") != MDP:
                return self._repond(commande, {commande: "Error 1"})
            self.haut = {"id": r["Id"], "taille": r["Size"], "donnees": b""}
            self._repond(commande, {commande: "Started"})
            return self._repond(commande, {"Id": r["Id"], "MaxSize": 500})
        h = self.haut
        if "Data" in r:
            h["donnees"] += base64.b64decode(r["Data"])[:h["taille"] - len(h["donnees"])]
            return self._repond(commande, {"Id": h["id"], "MaxSize": 500})
        if r.get("Md5") != hashlib.md5(h["donnees"]).hexdigest() or self.refuse:
            return self._repond(commande, {commande: "MD5 mismatch"})
        self.config, self.haut = h["donnees"], None      # SettingsConfigRestore puis redemarrage
        self._repond(commande, {commande: "Done"})


class Client:
    """ClientMQTT simule : publie() va droit a la carte, recoit() lit sa boite."""

    def __init__(self, carte):
        self.carte, self.abonnements, self.fermetures = carte, [], 0

    def connecte(self):
        pass

    def abonne(self, filtres):
        self.abonnements += filtres

    def publie(self, topic, payload, retain=False):
        self.carte.recoit(topic, payload.encode() if isinstance(payload, str) else payload)

    def recoit(self):
        try:
            return self.carte.boite.get(timeout=0.02)
        except queue.Empty:
            return None

    def entretient(self):
        pass

    def ferme(self):
        self.fermetures += 1


def test_mqtt(racine):
    carte = CarteMqtt(dmp())
    client = Client(carte)
    carte.boite.put(Message("stat/autre/FILEDOWNLOAD", b'{"Id":117,"Data":"AAAA"}'))   # bruit d'une autre carte
    verifie(bsm.lit(client, TOPIC, MDP), carte.config, "MQTT lit : octets de la carte, bruit d'une autre carte ignore")
    verifie((client.fermetures, carte.recus[0][1]), (1, b"0"), "MQTT lit : transfert remis a zero d'abord, client ferme")
    leve(lambda: bsm.lit(Client(carte), TOPIC, "faux"), RuntimeError, "MQTT lit : mauvais MqttPassword -> Error 1")
    carte.altere_md5 = True
    leve(lambda: bsm.lit(Client(carte), TOPIC, MDP), RuntimeError, "MQTT lit : MD5 faux refuse")
    carte.altere_md5 = False

    nouvelle = dmp(textes={8: "CARTE-MQTT"})
    bsm.ecrit(Client(carte), TOPIC, MDP, nouvelle)
    morceaux = sum(1 for t, p in carte.recus if t.endswith("FileUpload") and b'"Data"' in p)
    verifie((carte.config, morceaux), (nouvelle, -(-len(nouvelle) // 500)), "MQTT ecrit : fichier entier, par morceaux de MaxSize")
    carte.refuse = True
    carte.recus.clear()
    leve(lambda: bsm.ecrit(Client(carte), TOPIC, MDP, dmp()), RuntimeError, "MQTT ecrit : MD5 refuse par la carte")
    verifie((carte.config, carte.recus[-1][1]), (nouvelle, b"0"), "MQTT ecrit : refus -> rien de restaure, transfert abandonne")
    carte.refuse = False
    carte.muette, delai = True, bsm.DELAI
    bsm.DELAI = 0.3
    leve(lambda: bsm.lit(Client(carte), TOPIC, MDP), RuntimeError, "MQTT : carte muette -> pas de reponse, pas d'attente sans fin")
    bsm.DELAI, carte.muette = delai, False

    # -- restauration complete par l'adresse mqtt://<topic> : sauvegarde d'avant, envoi, relecture apres le retour
    bs._mqtt = lambda: (Client(carte), MDP)
    adresse = bs.MQTT + TOPIC
    f1 = bs.prend(racine, ENV, adresse, "manuelle")
    verifie(f1["adresse"], adresse, "MQTT prend : fiche avec l'adresse mqtt://<topic>")
    f2 = bs.copie(racine, ENV, f1["fichier"], {"hostname": "CARTE-RESTAUREE"})
    vues, etape = [], bs._etape
    bs._etape = lambda env, n: (vues.append((n, bs.liste_json(racine, env)["restauration"])), etape(env, n))
    res = bs.restaure(racine, ENV, f2["fichier"], adresse, bs.empreinte(racine, ENV, f2["fichier"]), retour=RETOUR)
    copie = (Path(racine) / bs.DOSSIER / ENV / f2["fichier"]).read_bytes()
    verifie((res["avant"]["origine"], res["ecarts"], carte.config), ("avant restauration", [], copie),
            "MQTT restaure : sauvegarde d'avant, copie sur la carte, aucun ecart relu")
    verifie(([n for n, _ in vues], vues[1][1]["etape"], len(vues[1][1]["etapes"]), bs.liste_json(racine, ENV)["restauration"]),
            ([0, 1, 2, 3], 0, 4, None), "restaure : 4 etapes suivies par la page, plus rien en cours a la fin")
    verifie(res["avant"]["fichier"] in [f["fichier"] for f in bs.liste(racine, ENV)], True, "MQTT restaure : sauvegarde d'avant gardee")
    carte.refuse = True
    try:
        bs.restaure(racine, ENV, f1["fichier"], adresse, bs.empreinte(racine, ENV, f1["fichier"]), retour=RETOUR)
        message = ""
    except RuntimeError as erreur:
        message = str(erreur)
    verifie(("MD5 mismatch" in message, "sauvegarde d'avant : " in message), (True, True),
            f"MQTT restaure : refus de la carte -> erreur qui nomme la sauvegarde d'avant ({message})")
    verifie(bs.EN_COURS, {}, "restaure en echec : plus rien en cours (la page ne suit pas une etape morte)")
    bs._etape = etape
    carte.refuse = False


def test_purge(racine):
    d = Path(racine) / bs.DOSSIER / "tasmota32-purge"
    d.mkdir(parents=True)
    noms = [f"202601{j:02d}-120000_avant-flash.dmp" for j in range(1, 9)]
    noms += [f"202601{j:02d}-120000_avant-restauration.dmp" for j in (1, 2, 3)]
    noms += [f"202610{j:02d}-120000_avant-restauration.dmp" for j in (1, 2, 3)]
    noms += ["20250101-120000_manuelle.dmp", "20250101-120000_modifiee.dmp"]
    for n in noms:
        (d / n).write_bytes(b"x")
        (d / n).with_suffix(".json").write_text("{}")
    verifie(bs.purge(racine, "tasmota32-purge", time.mktime((2026, 2, 1, 12, 0, 0, 0, 0, -1))), [],
            "purge : plus de 5 sauvegardes, mais aucune de plus de 90 jours -> rien d'efface")
    maintenant = time.mktime((2026, 11, 3, 12, 0, 0, 0, 0, -1))
    effacees = bs.purge(racine, "tasmota32-purge", maintenant)
    verifie(sorted(effacees), sorted(noms[:3] + ["20260101-120000_avant-restauration.dmp"]),
            "purge : au-dela des 5 plus recentes de chaque origine ET de plus de 90 jours")
    verifie(sorted(p.name for p in d.glob("*.dmp")) == sorted(set(noms) - set(effacees))
            and not any(d.glob("2026010[123]-120000_avant-flash.json")), True, "purge : .dmp et fiche effaces, le reste intact")
    verifie(sorted(p.name for p in d.glob("2025*.dmp")), ["20250101-120000_manuelle.dmp", "20250101-120000_modifiee.dmp"],
            "purge : manuelle et modifiee jamais effacees, meme anciennes")
    # -- case « purge automatique » de l'onglet (cochee par defaut, commune a toutes les cartes)
    verifie(bs.purge_auto(racine), True, "case de purge : cochee tant qu'elle n'a pas ete touchee")
    leve(lambda: bs.pose_purge_auto(racine, "non"), ValueError, "case de purge : autre chose que vrai/faux refuse")
    lit, bs.lit_carte = bs.lit_carte, lambda *_: dmp()
    avant = len(list(d.glob("*_avant-flash.dmp")))
    bs.traite_post("/sauvegarde/reglages", {"purge_auto": False}, None, racine, None, None)
    bs.prend(racine, "tasmota32-purge", "192.168.0.99", "avant-flash")
    verifie((bs.purge_auto(racine), len(list(d.glob("*_avant-flash.dmp")))), (False, avant + 1),
            "case decochee : sauvegarde automatique prise, rien d'efface")
    bs.pose_purge_auto(racine, True)
    bs.prend(racine, "tasmota32-purge", "192.168.0.99", "avant-flash")
    verifie(len(list(d.glob("*_avant-flash.dmp"))), bs.GARDE_NOMBRE, "case cochee : la purge reprend a la prise suivante")
    (Path(racine) / bs.REGLAGES).write_text("[illisible", encoding="utf-8")
    verifie(bs.purge_auto(racine), True, "reglage illisible : la purge reste active")
    bs.lit_carte = lit


def test_reposes():
    verifie((bs.commande("SO56"), bs.commande("SetOption56"), bs.commande("Timer3"), bs.commande("I2CDriver7")),
            ("SETOPTION56", "SETOPTION56", "TIMER", None), "commande : SO56 = SetOption56, Timer3 -> TIMER, illisible -> None")
    lignes = bs.commandes_lignes("SetOption56 ON\n; SetOption1 OFF\nBacklog SerialLog 3; WebLog 3;\n  SO57 1\nTimer3 {\"Enable\":1}")
    verifie(sorted(lignes), ["SERIALLOG", "SETOPTION56", "SETOPTION57", "TIMER", "WEBLOG"],
            "autoexec.bat : Backlog decoupe, ligne ; ignoree")
    persist = bs.commandes_persist((RACINE / bs.CONFIG_PERSIST).read_text(encoding="utf-8"))
    verifie({"HOSTNAME", "MQTTCLIENT", "TOPIC", "SETOPTION56", "TELEPERIOD"} <= set(persist), True,
            "persist : commandes de configGlobal.be (testeParam, liste MQTT)")
    commandes = dc.disposition()["commandes"]
    verifie((commandes.get("influxdb_token32"), commandes.get("timer"), "SETOPTION56" in commandes.get("flag3", [])),
            (["IFX"], ["TIMER"], True), "disposition : 1er mot de la commande seulement (pas « Password » d'InfluxDB)")
    auto, pers = bs._demarrage(RACINE, "tasmota32-bureau-interrupteur-energie")
    marques = bs.reposes(["flag3", "seriallog_level", "hostname", "influxdb_token32", "mqtt_pwd"], auto, pers)
    verifie(sorted(marques), ["flag3", "hostname", "seriallog_level"], "differentiel : marques attendues, pas le jeton InfluxDB")
    verifie(("autoexec.bat (SerialLog)" in marques["seriallog_level"], "persist (Hostname)" in marques["hostname"]), (True, True),
            "marque : source et commande telle qu'ecrite")
    verifie(bs.reposes(["flag3"], {}, {}), {}, "temoin : sans autoexec ni persist, aucune marque")


def banc():
    if not dc.utilisable():
        print("KO   decode-config absent : lancer outils_pc/decode_config.py")
        return 1
    with tempfile.TemporaryDirectory() as racine:
        test_mqtt(racine)
        test_purge(racine)
    test_reposes()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(banc())
