"""Configuration d'une carte par MQTT, pour l'onglet « Sauvegarde configuration » (carte injoignable en HTTP).

Commandes FileDownload / FileUpload de type 2 (tasmota/tasmota_xdrv_driver/xdrv_02_1_mqtt_file.ino) : elles passent par
SettingsConfigBackup / SettingsConfigRestore, comme /dl et /u2, donc le meme fichier (Settings + .drvset*). Elles
demandent le MqttPassword de la carte ; reponses sur stat/<topic>/FILEDOWNLOAD et .../FILEUPLOAD.

  lit(client, topic, mot_de_passe)             -> octets de la configuration
  ecrit(client, topic, mot_de_passe, donnees)  -> la carte a accepte le fichier et redemarre
`client` : client_mqtt.ClientMQTT (ou son double du banc), ferme a la fin. Banc : test_build_sauvegarde.py.
"""

import base64
import hashlib
import json
import time

DELAI = 15.0
TYPE_CONFIG = 2
ERREURS = ("Error", "Aborted", "MD5", "Failed")      # ResponseCmndChar de MqttFileValidate, D_JSON_MD5_MISMATCH...


class Echange:
    """Une commande de la carte : publie sur cmnd/<topic>/<Commande>, attend la reponse voulue sur stat/<topic>/."""

    def __init__(self, client, topic, commande):
        self.client, self.commande = client, commande
        self.cmnd, self.stat = f"cmnd/{topic}/{commande}", f"stat/{topic}/{commande.upper()}"
        client.connecte()
        client.abonne([self.stat])

    def etat(self, r):
        """Valeur de {"FileUpload": "Done"} (cle de la commande, casse indifferente), None sinon."""
        return next((v for k, v in r.items() if k.lower() == self.commande.lower()), None)

    def demande(self, charge, voulue, refus=True):
        """Publie `charge`, rend la 1re reponse JSON pour laquelle voulue(r) est vrai ; une erreur de la carte leve."""
        delai = DELAI
        self.client.publie(self.cmnd, charge if isinstance(charge, str) else json.dumps(charge))
        fin = time.monotonic() + delai
        while time.monotonic() < fin:
            m = self.client.recoit()
            self.client.entretient()
            if m is None or m.topic != self.stat:
                continue
            try:
                r = json.loads(m.payload)
            except ValueError:
                continue
            if not isinstance(r, dict):
                continue
            if voulue(r):
                return r
            etat = str(self.etat(r) or "")
            if refus and etat.startswith(ERREURS):
                raise RuntimeError(f"la carte refuse {self.commande} : {etat}"
                                   + (" (MqttPassword de la carte différent de MQTT_PASS)" if etat == "Error 1" else ""))
        raise RuntimeError(f"pas de réponse de la carte à {self.commande} en {delai:.0f} s (carte hors ligne sur le broker ?)")

    def remet_a_zero(self):
        """« <Commande> 0 » : abandonne un transfert reste ouvert sur la carte (sinon elle ignore le suivant)."""
        self.demande("0", lambda r: self.etat(r) == "Aborted", refus=False)


def lit(client, topic, mot_de_passe):
    e = Echange(client, topic, "FileDownload")
    try:
        e.remet_a_zero()
        debut = e.demande({"Password": mot_de_passe, "Type": TYPE_CONFIG}, lambda r: "Size" in r and "Id" in r)
        ident, taille, donnees = debut["Id"], int(debut["Size"]), b""
        while True:
            r = e.demande("", lambda r: r.get("Id") == ident and ("Data" in r or "Md5" in r))
            if "Md5" in r:
                break
            donnees += base64.b64decode(r["Data"])
            if len(donnees) > taille:
                raise RuntimeError(f"la carte envoie plus que les {taille} o annoncés")
        if len(donnees) != taille or hashlib.md5(donnees).hexdigest() != str(r["Md5"]).lower():
            raise RuntimeError(f"configuration reçue incomplète ou altérée ({len(donnees)}/{taille} o, MD5)")
        return donnees
    finally:
        client.ferme()


def ecrit(client, topic, mot_de_passe, donnees, nom="config.dmp"):
    e = Echange(client, topic, "FileUpload")
    ident = 1 + int(time.time()) % 254                   # FMqtt.file_id est un uint8_t non nul
    try:
        e.remet_a_zero()
        r = e.demande({"Password": mot_de_passe, "File": nom, "Id": ident, "Type": TYPE_CONFIG, "Size": len(donnees)},
                      lambda r: r.get("Id") == ident and "MaxSize" in r)
        position = 0
        while position < len(donnees):
            morceau = donnees[position:position + max(1, int(r["MaxSize"]))]
            r = e.demande({"Id": ident, "Data": base64.b64encode(morceau).decode()},
                          lambda r: r.get("Id") == ident and "MaxSize" in r)
            position += len(morceau)
        e.demande({"Id": ident, "Md5": hashlib.md5(donnees).hexdigest()}, lambda r: e.etat(r) == "Done")
    except RuntimeError:
        try:
            client.publie(e.cmnd, "0")                   # rien de garde a moitie sur la carte
        except OSError:
            pass
        raise
    finally:
        client.ferme()
