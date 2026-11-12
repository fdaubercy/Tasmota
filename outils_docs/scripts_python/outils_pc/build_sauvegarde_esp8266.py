"""Ce qu'un ESP8266 garde hors de Settings, donc hors de son /dl (onglet Sauvegarde configuration, 2026-11-12).

Le /dl (settings.ino::SettingsConfigBackup) est une copie de Settings en RAM, plus les .drvset* si la carte a un FS :
Rules, timers, Mem, template, Wi-Fi, MQTT y sont, deja (verifie sur .42 et .45 : 9 timers et une Rule1 de 576 car.
decodes). La lecture en ligne n'y ajoute rien, et elle est moins sure : `Rule1` par /cm rend un JSON tronque pour une
Rule longue. La carte est donc interrogee pour le reste seulement :
  Status 2   identite du firmware : une sauvegarde se restaure sur cette version ou une plus recente
  Ufs        systeme de fichiers : ses fichiers (autoexec.bat, scripts, display.ini...) ne sont pas dans le /dl
  Status 4   pilote Zigbee (23) : ses appareils sont dans un secteur de flash a part
Var1-16 sont en RAM (perdues au redemarrage) : rien a sauvegarder. Banc : test_build_sauvegarde.py.
"""

import json
import re

from build_ota_http import _commande

ZIGBEE = "23"                        # xdrv_23_zigbee : appareils en flash hors Settings (z_flash)


def _json(texte):
    try:
        return json.loads(texte)
    except ValueError:
        return {}


def controle(adresse, delai, commande=_commande):
    """{firmware, remarques: [[niveau, texte]]} ; 'o' = a recuperer autrement. Jamais d'exception : la sauvegarde est prise."""
    if adresse.startswith("mqtt://"):
        return {"firmware": "", "remarques": [["o", "Contrôle hors configuration non fait par MQTT : le faire en HTTP."]]}
    try:
        fwr = _json(commande(adresse, "Status 2", delai)).get("StatusFWR", {})
        ufs = commande(adresse, "Ufs", delai)          # {"Ufs":{"Type":n,...}[,{...}]} : pas toujours du JSON valide
        pilotes = _json(commande(adresse, "Status 4", delai)).get("StatusMEM", {}).get("Drivers", "")
    except Exception as erreur:                          # noqa: BLE001 - carte partie entre le /dl et le controle
        return {"firmware": "", "remarques": [["o", f"Contrôle hors configuration impossible : {erreur}"]]}
    firmware = " ".join(filter(None, (fwr.get("Version"), fwr.get("Hardware"), fwr.get("BuildDateTime"))))
    remarques = []
    if re.search(r'"Type":[1-9]', ufs):              # 0 = pas de FS ; commande inconnue sans USE_UFILESYS
        # shortcut: signale sans recuperer ; aucun ESP8266 du parc n'a de FS (1 Mo), recuperer par /ufsd le jour ou un en aura
        remarques.append(["o", "Système de fichiers présent : ses fichiers (hors .drvset) ne sont pas dans la sauvegarde, "
                               "les récupérer par la page Gestion des fichiers de la carte."])
    if ZIGBEE in pilotes.split(","):
        remarques.append(["o", "Pilote Zigbee : les appareils appairés sont hors de la sauvegarde (secteur de flash à part)."])
    if not remarques:
        remarques.append(["v", "Rien hors configuration : Rules, timers et Mem sont dans la sauvegarde."])
    if firmware:
        remarques.append(["v", f"Firmware de la carte : {firmware} (restaurer sur cette version ou une plus récente)."])
    return {"firmware": firmware, "remarques": remarques}
