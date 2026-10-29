"""Envoi du file system d'une carte par MQTT (« MQTT pousse », A16 de la page Build), vers data/fs/fsMqtt.be.

  envoie_fs_mqtt(env, topic, dossier_fs, sauvegardes, rapporte, *, fichiers=None, recharger_berry=False,
                 redemarrer=True, effacer=False)
      meme role et meme deroule que build_ota_fs.envoie_fs_ota (dossier extrait de littlefs.bin, persist en
      dernier, sauvegarde du persist de la carte s'il part, rechargement, redemarrage ou BrRestart), par le
      broker de user_config_override.h au lieu de HTTP. `topic` = serveur.mqtt.topic du persist de l'env.
      `effacer` : le FS de la carte est d'abord FORMATE (path.format, /sd de la flash compris) ; seulement avec
      l'image ENTIERE. fsMqtt.be, solidifie, survit ; le formatage bloque la carte (watchdog de la boucle : 5 s).

Protocole (choix 25 a 28 de docs/superpowers/specs/2026-10-24-page-build-televersement-design.md) : ordres JSON sur
fsmqtt/<topic>/ordre, reponses sur .../etat ; morceaux = 4 octets de position + donnees sur .../morceau, `FENETRE`
morceaux en vol, accuse cumule ; sans progres de l'accuse pendant `attente_morceau`, renvoi depuis l'accuse
(au plus `REPRISES` fois de suite). Essai A14 : 14 a 18 Ko/s vers la cuve par le maitre, sans coupure.
Esclave du range extender : il joint le broker par la sortie NAPT du maitre, ni redirection ni Sleep 0.

Erreurs : RuntimeError("<étape> : <motif>"). `rapporte` recoit {"etape", "pourcent", "detail"}.
"""

import hashlib
import json
import os
import queue
import struct
import threading
import time
from pathlib import Path

from build_ota_fs import PERSIST, _inventaire, _sauvegarde
from build_ota_http import ETAPE_BERRY, ETAPE_ENVOI, ETAPE_RECHARGEMENT, ETAPE_REDEMARRAGE, ETAPE_SAUVEGARDE

ETAPE_CONNEXION_MQTT = "Connexion MQTT"
ETAPE_EFFACEMENT = "Effacement du FS"
CHARGE = 1896                    # 1900 o par message (MQTT_MAX_PACKET_SIZE 2048 - topic - en-tete) - 4 de position
FENETRE = 4
REPRISES = 3


def client_par_defaut():
    """Client du broker de user_config_override.h (comme le sniffeur MQTT), non connecte."""
    import client_mqtt
    import sniffeur_mqtt
    cfg = sniffeur_mqtt.lit_config_broker()
    if not cfg.get("MQTT_HOST"):
        raise RuntimeError(f"{ETAPE_CONNEXION_MQTT} : MQTT_HOST introuvable dans user_config_override.h ; rien n'a été envoyé")
    return client_mqtt.ClientMQTT(cfg["MQTT_HOST"], cfg.get("MQTT_PORT", 1883), f"build-web-{os.getpid()}",
                                  cfg.get("MQTT_USER", ""), cfg.get("MQTT_PASS", ""))


class Canal:
    """Liaison avec fsMqtt.be d'une carte : un fil lit le broker, les reponses attendent dans une file."""

    def __init__(self, client, topic):
        self.client, self.base = client, f"fsmqtt/{topic}/"
        self.reponses = queue.Queue()
        self.accuses, self.lus = {}, []                  # accuses[id] = octets ; lus = [(position, donnees)]
        self.refus_morceau = None
        self.change = threading.Condition()
        self.ouvert, self.id = True, 0
        client.connecte()
        client.abonne([self.base + "etat", self.base + "lu"])
        self.fil = threading.Thread(target=self._lit, daemon=True)
        self.fil.start()

    def _lit(self):
        while self.ouvert:
            try:
                m = self.client.recoit()
                self.client.entretient()
            except OSError:
                return
            if m is None:
                continue
            if m.topic == self.base + "lu" and len(m.payload) >= 4:
                with self.change:
                    self.lus.append((struct.unpack(">I", m.payload[:4])[0], m.payload[4:]))
                    self.change.notify_all()
                continue
            try:
                r = json.loads(m.payload)
            except ValueError:
                continue
            if r.get("op") == "morceau":
                with self.change:
                    if r.get("ok"):
                        self.accuses[r.get("id")] = max(self.accuses.get(r.get("id"), 0), int(r.get("octets", 0)))
                    else:
                        self.refus_morceau = r.get("erreur", "morceau refusé")
                    self.change.notify_all()
            else:
                self.reponses.put(r)

    def ferme(self):
        self.ouvert = False
        self.client.ferme()

    def publie_ordre(self, op, **champs):
        self.id += 1
        self.client.publie(self.base + "ordre", json.dumps(dict(champs, op=op, id=self.id)))
        return self.id

    def attend(self, etape, op, id=None, delai=15.0):
        """Prochaine reponse `op` (de l'ordre `id` s'il est donne) ; RuntimeError si rien dans `delai`."""
        fin = time.monotonic() + delai
        while True:
            try:
                r = self.reponses.get(timeout=max(0.0, fin - time.monotonic()))
            except queue.Empty:
                raise RuntimeError(f"{etape} : pas de réponse « {op} » de la carte en {delai:g} s") from None
            if r.get("op") == op and (id is None or r.get("id") == id):
                return r

    def ordre(self, etape, op, delai=15.0, **champs):
        r = self.attend(etape, op, self.publie_ordre(op, **champs), delai)
        if not r.get("ok"):
            raise RuntimeError(f"{etape} : {op} refusé par la carte : {r.get('erreur', '?')}")
        return r

    def lit(self, etape, chemin, delai=15.0):
        """Contenu d'un fichier de la carte (ordre lit), controle par sa taille et son MD5."""
        with self.change:
            self.lus = []
        r = self.ordre(etape, "lit", delai, chemin=chemin)
        with self.change:          # les morceaux precedent la reponse ; marge si le broker les a doubles
            self.change.wait_for(lambda: sum(len(d) for _, d in self.lus) >= r["octets"], timeout=2.0)
            morceaux = sorted(self.lus)
        contenu = b"".join(d for _, d in morceaux)
        if len(contenu) != r["octets"] or hashlib.md5(contenu).hexdigest() != r.get("md5"):
            raise RuntimeError(f"{etape} : {chemin} relu incomplet ou altéré ({len(contenu)} o sur {r['octets']})")
        return contenu

    def envoie(self, etape, chemin, donnees, progression, fenetre=FENETRE, attente_morceau=5.0, delai=15.0):
        """Un fichier : debut, morceaux (fenetre, retour arriere sur perte), fin controlee par la carte."""
        id = self.ordre(etape, "debut", delai, chemin=chemin, taille=len(donnees), md5=hashlib.md5(donnees).hexdigest())["id"]
        envoye = acquitte = reprises = 0
        dernier_progres = time.monotonic()
        while acquitte < len(donnees):
            with self.change:
                if self.refus_morceau:
                    raise RuntimeError(f"{etape} : {chemin} : {self.refus_morceau}")
                nouveau = self.accuses.get(id, 0)
                if nouveau == acquitte and (envoye - acquitte >= fenetre * CHARGE or envoye >= len(donnees)):
                    self.change.wait(0.05)
                    nouveau = self.accuses.get(id, 0)
            if nouveau > acquitte:
                acquitte, reprises, dernier_progres = nouveau, 0, time.monotonic()
                progression(acquitte)
            elif time.monotonic() - dernier_progres > attente_morceau:
                reprises += 1
                if reprises > REPRISES:
                    raise RuntimeError(f"{etape} : {chemin} : accusé bloqué à {acquitte} o sur {len(donnees)} "
                                       f"après {REPRISES} renvois")
                envoye, dernier_progres = acquitte, time.monotonic()      # retour arriere
            if envoye - acquitte < fenetre * CHARGE and envoye < len(donnees):
                self.client.publie(self.base + "morceau", struct.pack(">I", envoye) + donnees[envoye:envoye + CHARGE])
                envoye += len(donnees[envoye:envoye + CHARGE])
        self.ordre(etape, "fin", 2 * delai)


def envoie_fs_mqtt(env, topic, dossier_fs, sauvegardes, rapporte, *, fichiers=None, recharger_berry=False,
                   redemarrer=True, effacer=False, delai_retour=90.0, client=None, fenetre=FENETRE,
                   attente_morceau=5.0, delai=15.0):
    """Voir la docstring du module. `client` : ClientMQTT non connecte (defaut : broker du dépôt) ; `delai` : attente
    de chaque reponse de la carte."""
    dossier_fs, sauvegardes = Path(dossier_fs), Path(sauvegardes)
    if effacer and fichiers is not None:
        raise RuntimeError(f"{ETAPE_EFFACEMENT} : effacer le FS demande d'envoyer l'image ENTIÈRE (persist compris) ; "
                           "rien n'a été envoyé")
    fichiers, _ = _inventaire(dossier_fs, fichiers)
    avec_persist = PERSIST in fichiers
    rapporte({"etape": ETAPE_CONNEXION_MQTT, "pourcent": None, "detail": f"fsmqtt/{topic}"})
    try:
        canal = Canal(client or client_par_defaut(), topic)
    except OSError as erreur:
        raise RuntimeError(f"{ETAPE_CONNEXION_MQTT} : broker injoignable ({erreur}) ; rien n'a été envoyé") from None
    sauve = ""
    try:
        try:                                        # ordre sans effet : le module repond-il ?
            canal.ordre(ETAPE_CONNEXION_MQTT, "abandon", delai)
        except RuntimeError:
            raise RuntimeError(f"{ETAPE_CONNEXION_MQTT} : aucune réponse sur fsmqtt/{topic} : carte hors ligne, ou "
                               "fsMqtt.be pas chargé par son autoexec ; rien n'a été envoyé") from None
        if avec_persist:
            rapporte({"etape": ETAPE_SAUVEGARDE, "pourcent": None, "detail": f"par MQTT ({topic})"})
            ancien = canal.lit(ETAPE_SAUVEGARDE, "/" + PERSIST, delai)
            try:
                json.loads(ancien)
            except ValueError as erreur:
                raise RuntimeError(f"{ETAPE_SAUVEGARDE} : {PERSIST} de la carte n'est pas du JSON valide ({erreur}) : "
                                   "pas de sauvegarde possible ; rien n'a été envoyé") from None
            sauve = f" ; sauvegarde du persist : {_sauvegarde(env, ancien, sauvegardes)}"
        if effacer:
            rapporte({"etape": ETAPE_EFFACEMENT, "pourcent": 0, "detail": "formatage de tout le FS (/sd compris)"})
            canal.ordre(ETAPE_EFFACEMENT, "efface", delai)
            rapporte({"etape": ETAPE_EFFACEMENT, "pourcent": 100, "detail": "FS formaté"})
        total = sum((dossier_fs / rel).stat().st_size for rel in fichiers) or 1
        faits, dernier = 0, [-1]
        for i, rel in enumerate(fichiers, 1):
            detail = f"{i}/{len(fichiers)} /{rel}"
            rapporte({"etape": ETAPE_ENVOI, "pourcent": faits * 100 // total, "detail": detail})

            def progression(octets, detail=detail, faits=faits):
                pourcent = min(99, (faits + octets) * 100 // total)
                if pourcent != dernier[0]:
                    dernier[0] = pourcent
                    rapporte({"etape": ETAPE_ENVOI, "pourcent": pourcent, "detail": detail})

            donnees = (dossier_fs / rel).read_bytes()
            canal.envoie(ETAPE_ENVOI, "/" + rel, donnees, progression, fenetre, attente_morceau, delai)
            faits += len(donnees)
        rapporte({"etape": ETAPE_ENVOI, "pourcent": 100, "detail": f"{len(fichiers)}/{len(fichiers)} /{fichiers[-1]}"
                  if fichiers else "aucun fichier"})
        if avec_persist:            # le persist vit en RAM : sans ceci, le System#Save d'un redemarrage l'ecraserait
            rapporte({"etape": ETAPE_RECHARGEMENT, "pourcent": None, "detail": "persist.load()"})
            canal.ordre(ETAPE_RECHARGEMENT, "recharge", delai)
        if redemarrer or recharger_berry:
            etape, op = (ETAPE_REDEMARRAGE, "redemarre") if redemarrer else (ETAPE_BERRY, "berry")
            rapporte({"etape": etape, "pourcent": None, "detail": f"{'Restart 1' if redemarrer else 'BrRestart'}, "
                                                                  f"attente de « prêt » de fsMqtt.be"})
            canal.ordre(etape, op, delai)
            canal.attend(etape, "pret", delai=delai_retour)
    except RuntimeError as erreur:
        raise RuntimeError(f"{erreur}{sauve}") from None
    finally:
        canal.ferme()
