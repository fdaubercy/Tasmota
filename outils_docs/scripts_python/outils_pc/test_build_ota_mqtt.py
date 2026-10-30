"""Banc de build_ota_mqtt.py (envoi du FS par MQTT, A16) : client MQTT simule relie a une carte simulee qui suit le
protocole de data/fs/fsMqtt.be (choix 25 et 26 de la spec ; le module Berry a son propre banc : berry/banc_fsmqtt.py).

Aucun broker, aucune carte : tout est en memoire. Code de sortie 0 = vert.
"""

import hashlib
import io
import json
import queue
import struct
import sys
import tempfile
from pathlib import Path

import build_ota_mqtt as bm

ECHECS = []
TOPIC = "garage/cuve"
BASE = f"fsmqtt/{TOPIC}/"
ANCIEN = json.dumps({"serveur": {"hostname": "cuve", "mqtt": {"topic": TOPIC}}, "ancien": True}).encode("utf-8")
IMAGE = {"_persist.json": json.dumps({"serveur": {"hostname": "cuve", "mqtt": {"topic": TOPIC}}}).encode("utf-8"),
         "autoexec.be": b"import demarrage\n" * 400, "json/graphiques.json": b"{}", "sd/html/a.html": bytes(range(256)) * 30}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


class Message:
    def __init__(self, topic, payload):
        self.topic, self.payload = topic, payload


class Carte:
    """fsMqtt.be en Python : FS en memoire, memes reponses. `perdre` : positions de morceaux jetees UNE fois ;
    `muette` : ne repond a rien ; `bloque_apres` : n'accepte plus aucun morceau au-dela de ce nombre d'octets."""

    def __init__(self, fs=None):
        self.fs = dict(fs if fs is not None else {"/_persist.json": ANCIEN, "/vieux.be": b"x", "/sd/html/vieux.html": b"1"})
        self.client, self.t, self.ordres, self.positions = None, None, [], []
        self.perdre, self.muette, self.bloque_apres, self.corrompt = set(), False, None, False

    def publie(self, topic, charge):
        self.client.boite.put(Message(BASE + topic, charge if isinstance(charge, bytes) else json.dumps(charge).encode()))

    def repond(self, o, ok=True, **autres):
        self.publie("etat", dict(autres, id=o.get("id"), op=o["op"], ok=ok))

    def recoit(self, topic, payload):
        if self.muette:
            return
        if topic == BASE + "morceau":
            position = struct.unpack(">I", payload[:4])[0]
            self.positions.append(position)
            if position in self.perdre:
                self.perdre.discard(position)
                return
            t = self.t
            if t is None:
                return
            if self.bloque_apres is not None and position >= self.bloque_apres:
                return
            if position == len(t["donnees"]):
                t["donnees"] += payload[4:] if not self.corrompt else payload[4:][::-1]
            self.publie("etat", {"id": t["id"], "op": "morceau", "ok": True, "octets": len(t["donnees"])})
            return
        o = json.loads(payload)
        self.ordres.append(o["op"])
        op = o["op"]
        if op == "abandon":
            self.t = None
            self.repond(o)
        elif op == "debut":
            self.t = {"id": o["id"], "chemin": o["chemin"], "taille": o["taille"], "md5": o["md5"], "donnees": b""}
            self.repond(o)
        elif op == "fin":
            t, self.t = self.t, None
            if hashlib.md5(t["donnees"]).hexdigest() != t["md5"]:
                return self.repond(o, False, erreur="MD5 différent")
            self.fs[t["chemin"]] = t["donnees"]
            self.repond(o, chemin=t["chemin"], octets=len(t["donnees"]))
        elif op == "lit":
            d = self.fs[o["chemin"]]
            for p in range(0, len(d), bm.CHARGE):
                self.publie("lu", struct.pack(">I", p) + d[p:p + bm.CHARGE])
            self.repond(o, chemin=o["chemin"], octets=len(d), md5=hashlib.md5(d).hexdigest())
        elif op == "efface":                                 # formatage : une seule reponse
            self.fs = {}
            self.repond(o)
        elif op in ("recharge", "berry", "redemarre"):
            self.repond(o)
            if op != "recharge":
                self.publie("etat", {"op": "pret", "version": 1})


class Client:
    """ClientMQTT simule : publie() va droit a la carte, recoit() lit la boite remplie par la carte."""

    def __init__(self, carte):
        self.carte, self.boite, self.abonnements = carte, queue.Queue(), []
        carte.client = self

    def connecte(self):
        pass

    def abonne(self, filtres):
        self.abonnements += filtres

    def publie(self, topic, payload, retain=False):
        self.carte.recoit(topic, payload.encode() if isinstance(payload, str) else payload)

    def recoit(self):
        try:
            return self.boite.get(timeout=0.05)
        except queue.Empty:
            return None

    def entretient(self):
        pass

    def ferme(self):
        pass


def image(t, fichiers=IMAGE):
    d = Path(t) / "fs"
    for rel, contenu in fichiers.items():
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_bytes(contenu)
    return d


def envoie(carte, dossier, sauvegardes, **options):
    etapes = []
    options = dict({"delai": 1.0, "attente_morceau": 0.2, "delai_retour": 1.0}, **options)
    try:
        bm.envoie_fs_mqtt("cuve", TOPIC, dossier, sauvegardes, etapes.append, client=Client(carte), **options)
        return "ok", etapes
    except RuntimeError as erreur:
        return str(erreur), etapes


def test_envoi_complet():
    with tempfile.TemporaryDirectory() as t:
        carte, sauvegardes = Carte(), Path(t) / "sauvegardes"
        r, etapes = envoie(carte, image(t), sauvegardes)
        verifie(r, "ok", "complet : envoi reussi")
        verifie({c: carte.fs.get("/" + c) for c in IMAGE}, {c: d for c, d in IMAGE.items()}, "complet : 4 fichiers identiques sur la carte")
        verifie([o for o in carte.ordres if o in ("debut", "lit", "recharge", "redemarre")][:1] + carte.ordres[-2:],
                ["lit", "recharge", "redemarre"], "complet : persist sauvegarde d'abord, recharge puis Restart a la fin")
        debuts = [i for i, o in enumerate(carte.ordres) if o == "debut"]
        verifie(len(debuts), 4, "complet : un debut par fichier")
        copies = list(sauvegardes.glob("cuve-*.json"))
        verifie([c.read_bytes() for c in copies], [ANCIEN], "complet : persist d'avant sauvegarde (relu par MQTT, octet pour octet)")
        envois = [e for e in etapes if e["etape"] == bm.ETAPE_ENVOI]
        verifie((envois[-1]["pourcent"], envois[-1]["detail"]), (100, "4/4 /_persist.json"), "complet : persist en dernier, 100 %")
        verifie(all(a["pourcent"] <= b["pourcent"] for a, b in zip(envois, envois[1:])), True, "complet : % croissant")
        verifie(carte.fs.get("/vieux.be"), b"x", "complet : sans effacement, les autres fichiers de la carte restent")


def test_perte_et_fenetre():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        carte.perdre = {bm.CHARGE}                           # 2e morceau de autoexec.be perdu une fois
        r, _ = envoie(carte, image(t), Path(t) / "s", fichiers=["autoexec.be"], redemarrer=False)
        verifie((r, carte.fs["/autoexec.be"]), ("ok", IMAGE["autoexec.be"]), "perte : renvoi depuis l'accuse, fichier identique")
        verifie(carte.positions.count(bm.CHARGE) >= 2, True, "perte : temoin, le morceau perdu a bien ete renvoye")
        verifie(max(carte.positions[:4]) == 3 * bm.CHARGE, True, "fenetre : 4 morceaux partent sans attendre d'accuse")
        carte = Carte()
        carte.bloque_apres = bm.CHARGE
        r, _ = envoie(carte, image(t), Path(t) / "s", fichiers=["autoexec.be"], redemarrer=False)
        verifie("accusé bloqué à 1896 o" in r and "après 3 renvois" in r, True, "carte qui n'accepte plus rien : abandon apres 3 renvois")


def test_refus_et_absences():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        carte.muette = True
        r, _ = envoie(carte, image(t), Path(t) / "s")
        verifie(("aucune réponse" in r, "rien n'a été envoyé" in r), (True, True), "carte muette : module absent dit, rien envoye")
        journal = io.StringIO()
        r, _ = envoie(Carte(), image(t), Path(t) / "s", fichiers=["autoexec.be"], redemarrer=False, journal=journal)
        trace = journal.getvalue()
        verifie((r, '-> ordre {"chemin": "/autoexec.be"' in trace, '<- etat {"id": 2, "op": "debut", "ok": true}' in trace,
                 "-> morceau position 0" in trace), ("ok", True, True, True), "journal : ordres, reponses et morceaux horodates")
        journal = io.StringIO()
        carte = Carte()
        carte.muette = True
        envoie(carte, image(t), Path(t) / "s", journal=journal)
        verifie("rien reçu pour « abandon » (id 1) en 1 s ; fil de lecture vivant" in journal.getvalue(), True,
                "journal : attente vaine notee, avec l'etat du fil de lecture")
        carte = Carte()
        carte.corrompt = True
        r, _ = envoie(carte, image(t), Path(t) / "s")
        verifie(("MD5 différent" in r, "sauvegarde du persist" in r), (True, True),
                "MD5 refuse par la carte : erreur, chemin de la sauvegarde rappele")
        r, _ = envoie(Carte(), image(t), Path(t) / "s", fichiers=["autoexec.be"], effacer=True)
        verifie("image ENTIÈRE" in r, True, "effacer avec un sous-ensemble : refuse avant toute liaison")
        carte = Carte({"/_persist.json": b"<html>pas du json"})
        r, _ = envoie(carte, image(t), Path(t) / "s")
        verifie(("JSON valide" in r, carte.ordres.count("debut")), (True, 0), "persist de la carte illisible : rien envoye")


def test_options_et_effacement():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        r, _ = envoie(carte, image(t), Path(t) / "s", fichiers=["autoexec.be"], redemarrer=False, recharger_berry=True)
        verifie((r, [o for o in carte.ordres if o != "debut" and o != "fin"]), ("ok", ["abandon", "berry"]),
                "sans persist : ni lecture ni recharge ; BrRestart demande, « pret » attendu")
        carte = Carte()
        r, _ = envoie(carte, image(t), Path(t) / "s", fichiers=["json/graphiques.json"], redemarrer=False)
        verifie(carte.ordres, ["abandon", "debut", "fin"], "aucune option : seulement l'ecriture")
        carte = Carte()
        r, etapes = envoie(carte, image(t), Path(t) / "s", effacer=True)
        verifie((r, "/vieux.be" in carte.fs, "/sd/html/vieux.html" in carte.fs, sorted(carte.fs)), ("ok", False, False, sorted("/" + c for c in IMAGE)),
                "effacer : anciens fichiers supprimes (/sd compris), puis toute l'image envoyee")
        verifie(carte.ordres.index("efface") < carte.ordres.index("debut") and carte.ordres.index("lit") < carte.ordres.index("efface"),
                True, "effacer : persist sauvegarde AVANT l'effacement, envoi APRES")
        eff = [e["pourcent"] for e in etapes if e["etape"] == bm.ETAPE_EFFACEMENT]
        verifie((eff[0], eff[-1]), (0, 100), "effacer : avancement 0 -> 100 %")
        envois = [e["detail"] for e in etapes if e["etape"] == bm.ETAPE_ENVOI]
        verifie(envois[0], f"1/{len(IMAGE)} /_persist.json",
                "effacer : persist envoye JUSTE APRES le formatage (un echec ensuite laisse la carte avec son persist)")
        r, etapes = envoie(Carte(), image(t), Path(t) / "s")
        verifie([e["detail"] for e in etapes if e["etape"] == bm.ETAPE_ENVOI][-2], f"{len(IMAGE)}/{len(IMAGE)} /_persist.json",
                "sans effacer : temoin, persist toujours en dernier")


def principal():
    for test in (test_envoi_complet, test_perte_et_fenetre, test_refus_et_absences, test_options_et_effacement):
        try:
            test()
        except Exception as erreur:
            ECHECS.append(f"{test.__name__} : {erreur!r}")
            print(f"KO   {test.__name__} : exception {erreur!r}")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
