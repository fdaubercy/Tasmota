"""Configuration persistante du sniffeur MQTT : brokers, abonnements par broker, favoris de filtre.

Fichier : %APPDATA%\\sniffeur_mqtt\\config.json (Linux/macOS : ~/.config/sniffeur_mqtt/config.json).
HORS DU DEPOT : il contient des mots de passe de brokers, en clair (outil local, poste personnel).

Broker « tasmota » : VIRTUEL, jamais ecrit dans le fichier. Ses parametres sont relus a chaque
lancement dans tasmota/user_config_override.h (MQTT_HOST/PORT/USER/PASS), ou pris dans la ligne de
commande (--hote...). Ni modifiable ni supprimable depuis la page : on en cree un autre.

Forme du fichier :
    {"brokers": [{"id": "b1", "nom": "...", "hote": "...", "port": 1883, "tls": false,
                  "verifierCertificat": true, "utilisateur": "...", "motDePasse": "..."}],
     "actif": "tasmota" | "b1",
     "abonnements": {"tasmota": ["#"], "b1": ["tele/#"]},
     "favoris": [{"nom": "...", "filtre": "...", "champ": "tout|topic|payload", "regex": false}]}
"""

import json
import os
import re
import threading

ID_TASMOTA = "tasmota"
CHAMPS_FAVORI = ("tout", "topic", "payload")


def chemin_config():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "sniffeur_mqtt", "config.json")


class Configuration:
    def __init__(self, broker_tasmota, chemin=None):
        self.chemin = chemin or chemin_config()
        self.verrou = threading.Lock()
        self.tasmota = dict(broker_tasmota, id=ID_TASMOTA)
        self.donnees = {"brokers": [], "actif": ID_TASMOTA, "abonnements": {}, "favoris": []}
        try:
            with open(self.chemin, encoding="utf-8") as f:
                lu = json.load(f)
            if isinstance(lu, dict):
                self.donnees.update({k: lu[k] for k in self.donnees if k in lu})
        except (OSError, ValueError):
            pass
        if self.broker(self.donnees.get("actif")) is None:
            self.donnees["actif"] = ID_TASMOTA

    def _sauve(self):
        os.makedirs(os.path.dirname(self.chemin), exist_ok=True)
        temporaire = self.chemin + ".tmp"
        with open(temporaire, "w", encoding="utf-8") as f:
            json.dump(self.donnees, f, ensure_ascii=False, indent=1)
        os.replace(temporaire, self.chemin)

    # ------------------------------------------------------------------ brokers
    def broker(self, identifiant):
        if identifiant == ID_TASMOTA:
            return self.tasmota
        return next((b for b in self.donnees["brokers"] if b.get("id") == identifiant), None)

    def actif(self):
        return self.broker(self.donnees["actif"])

    def liste_publique(self):
        """Brokers SANS mot de passe (seulement s'il en existe un) : ce qui part vers la page."""
        sortie = []
        for b in [self.tasmota] + self.donnees["brokers"]:
            p = {k: v for k, v in b.items() if k != "motDePasse"}
            p["aMotDePasse"] = bool(b.get("motDePasse"))
            p["fige"] = b["id"] == ID_TASMOTA
            sortie.append(p)
        return {"brokers": sortie, "actif": self.donnees["actif"]}

    def enregistre(self, demande):
        """Cree (sans 'id') ou modifie un broker. Mot de passe vide = inchange, sauf 'effacerMotDePasse'."""
        nom = str(demande.get("nom", "")).strip()
        hote = str(demande.get("hote", "")).strip()
        try:
            port = int(demande.get("port", 1883))
        except (TypeError, ValueError):
            raise ValueError("port invalide")
        if not nom or len(nom) > 60:
            raise ValueError("nom obligatoire (60 caracteres au plus)")
        if not re.fullmatch(r"[A-Za-z0-9.\-:\[\]]{1,253}", hote):
            raise ValueError("hote invalide (nom DNS ou adresse IP)")
        if not 1 <= port <= 65535:
            raise ValueError("port hors limites (1-65535)")
        with self.verrou:
            identifiant = demande.get("id")
            if identifiant == ID_TASMOTA:
                raise ValueError("le broker de user_config_override.h n'est pas modifiable : en creer un autre")
            if identifiant:
                broker = self.broker(identifiant)
                if broker is None:
                    raise ValueError("broker inconnu")
            else:
                numeros = [int(b["id"][1:]) for b in self.donnees["brokers"] if re.fullmatch(r"b\d+", b.get("id", ""))]
                broker = {"id": f"b{max(numeros, default=0) + 1}"}
                self.donnees["brokers"].append(broker)
            broker.update({"nom": nom, "hote": hote, "port": port, "tls": bool(demande.get("tls")),
                           "verifierCertificat": bool(demande.get("verifierCertificat", True)),
                           "utilisateur": str(demande.get("utilisateur", "")).strip()})
            mot_de_passe = str(demande.get("motDePasse", ""))
            if mot_de_passe:
                broker["motDePasse"] = mot_de_passe
            elif demande.get("effacerMotDePasse"):
                broker.pop("motDePasse", None)
            self._sauve()
            return broker["id"]

    def supprime(self, identifiant):
        with self.verrou:
            if identifiant == ID_TASMOTA:
                raise ValueError("le broker de user_config_override.h ne se supprime pas")
            avant = len(self.donnees["brokers"])
            self.donnees["brokers"] = [b for b in self.donnees["brokers"] if b.get("id") != identifiant]
            if len(self.donnees["brokers"]) == avant:
                raise ValueError("broker inconnu")
            self.donnees["abonnements"].pop(identifiant, None)
            if self.donnees["actif"] == identifiant:
                self.donnees["actif"] = ID_TASMOTA
            self._sauve()

    def selectionne(self, identifiant):
        with self.verrou:
            if self.broker(identifiant) is None:
                raise ValueError("broker inconnu")
            self.donnees["actif"] = identifiant
            self._sauve()
            return self.broker(identifiant)

    # ------------------------------------------------------------------ abonnements memorises
    def abonnements(self, identifiant):
        return list(self.donnees["abonnements"].get(identifiant) or ["#"])

    def memorise_abonnements(self, identifiant, filtres):
        with self.verrou:
            self.donnees["abonnements"][identifiant] = list(filtres)
            self._sauve()

    # ------------------------------------------------------------------ favoris de filtre
    def favoris(self):
        return list(self.donnees["favoris"])

    def ajoute_favori(self, demande):
        nom, filtre = str(demande.get("nom", "")).strip(), str(demande.get("filtre", ""))
        champ = demande.get("champ", "tout")
        if not nom or len(nom) > 60 or not filtre or len(filtre) > 500 or champ not in CHAMPS_FAVORI:
            raise ValueError("favori invalide (nom et filtre obligatoires)")
        with self.verrou:
            self.donnees["favoris"] = [f for f in self.donnees["favoris"] if f.get("nom") != nom]
            self.donnees["favoris"].append({"nom": nom, "filtre": filtre, "champ": champ,
                                            "regex": bool(demande.get("regex"))})
            self._sauve()

    def supprime_favori(self, nom):
        with self.verrou:
            self.donnees["favoris"] = [f for f in self.donnees["favoris"] if f.get("nom") != nom]
            self._sauve()
