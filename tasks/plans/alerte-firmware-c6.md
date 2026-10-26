---
chantier: alerte-firmware-c6
titre: Alerte web « firmware du coprocesseur ESP32-C6 pas à jour » sur les P4
statut: actif
cree: 2026-10-26
maj: 2026-10-26
source: dynamic-floating-cosmos.md
---
# Alerte web « firmware du coprocesseur ESP32-C6 pas à jour » sur les P4

## Contexte
Sur le P4, le Wi-Fi passe par un coprocesseur ESP32-C6 (esp_hosted, en SDIO). Constaté le 2026-10-26 sur 192.168.0.43 :
le C6 est en **2.6.6**, alors que la bibliothèque esp_hosted compilée dans le firmware P4 est en **2.12.13**. Rien ne
le signale à l'utilisateur. Tasmota ne fait qu'afficher la version sur la page Information (`xdrv_01_9_webserver.ino`).

Décisions de conception (l'utilisateur m'a laissé choisir le déclenchement) :
- **Version visée = la version « Host »** de la commande `Hosted` (`xdrv_84_esp32_hosted.ino::CmndHosted`), c'est-à-dire
  la bibliothèque compilée dans le P4. Le C6 doit avoir la même version que l'hôte. Le fichier sans numéro de version
  du serveur est en retard (2.12.6) : on ne s'y fie pas. On vise `…/coprocessor/v<Host>/network_adapter_<MCU>.bin`.
- **« Publiée » est vérifié sur le serveur**, en lisant les 512 premiers octets du fichier (requête `Range`). Le champ
  `esp_app_desc_t.version` se trouve à l'offset 0x30 et donne la version réelle (méthode validée au terminal :
  v2.12.13 → « 2.12.13 »). Si le fichier par défaut est **plus récent** que l'hôte, la page l'indique seulement :
  il faudrait alors recompiler le P4.
- **Déclenchement au démarrage, sans vérification périodique.** Les deux versions comparées ne changent qu'au
  redémarrage (un OTA du C6 redémarre le P4). Une vérification régulière ne détecterait donc rien de plus.
  - Comparaison **locale** dès que `Hosted` répond : C6 à jour → **aucun accès réseau**, rien n'est affiché.
  - C6 en retard → **une** requête au serveur 3 min après le démarrage (Wi-Fi stabilisé). En cas d'échec réseau,
    nouvel essai toutes les heures, 6 essais au plus. Une socket est ouverte une seule fois, et seulement s'il
    y a un retard (leçon du 2026-10-25 : un socket sur une carte de production n'est pas anodin).
- **Affichage** : une ligne d'alerte en tête de l'accueil (`web_sensor`, chaîne précalculée, sans log), avec un lien
  vers la page `/coprocesseur`. Cette page montre les versions, l'URL et l'avertissement de coupure du Wi-Fi
  (point d'accès des esclaves compris), puis un bouton « Mettre à jour » (POST + confirmation). Le POST lance
  `HostedOta <URL complète>` (jamais la forme courte, qui dépend d'`OtaUrl`) et renvoie à l'accueil après 90 s.
  Aucune URL n'est reçue du navigateur : seule la version calculée par la carte est utilisée.
- **Un seul fichier Berry**, module et driver ensemble, sur le modèle de `historiqueFonctions.be::HISTORIQUE_WEB`,
  dans `data/fs` et **solidifié sur le P4** (comme `controleES8311.be`). Activé par `serveur.coprocesseur.activation`
  et inerte si `Hosted` ne répond pas (carte sans coprocesseur). Logs sur la cible `general` : créer une nouvelle
  cible aurait obligé à modifier `logFonctions.be`, solidifié dans le socle de toutes les cartes.
- Gabarit de page dans `data/sd/html/coprocesseur.html` (leçon du 2026-10-18 : pas de gabarit en chaînes dans un .be).

## A1 — Banc d'abord (TDD)
- [x] `outils_docs/scripts_python/berry/banc_coprocesseur.{py,be}` + bouchons (`tasmota.cmd("Hosted")`, `webclient` qui renvoie un en-tête réel 206/404/erreur, `webserver`) : cas à jour (0 requête, 0 ligne), en retard + publié (ligne + bouton), en retard + 404 (ligne sans bouton), réseau KO (ligne « non vérifiée » + nouvel essai, 6 au plus), en-tête invalide, carte sans coprocesseur (rien), POST → `HostedOta https://…/v2.12.13/network_adapter_esp32c6.bin` — preuve : `banc_coprocesseur.be` §1 à §13, 67 vérifications Berry (+ 7 de rendu Chrome)
- [x] Comparaison numérique des versions testée (2.6.6 < 2.12.13 : piège de la comparaison de chaînes) — preuve : §2 du banc + mutant `self.c6 >= self.hote` sur une copie de data/fs → rc=1, 5 ECHEC
- [x] Banc lancé ROUGE avant le module (témoin) — preuve : rc=1, `import_error: module 'controleCoprocesseur' not found`

## A2 — Module `data/fs/controleCoprocesseur.be`
Renommé à l'écriture : module + classe `COPROCESSEUR` + `init()` sur le modèle de `controleWeb.be`. Toute la logique est dans la classe, si bien qu'aucune globale n'est nécessaire (pas de `demarrage.importe`). Les fermetures à l'intérieur des méthodes sont acceptées par la solidification.
- [x] Lecture de `Hosted` (Host / Hosted / MCU), version → entier, comparaison — preuve : `controleCoprocesseur.be::COPROCESSEUR.verifieLocal`, banc §2, §5 à §7
- [x] Vérification serveur : `webclient` + `Range: bytes=0-511` + `set_timeouts` courts, sous `try/except` (USE_BERRY_TIMEOUT 4 s), lecture de la version dans l'en-tête, timer 3 min puis nouvel essai toutes les heures (6 au plus) — preuve : `COPROCESSEUR.lisEnTete`/`verifieServeur`, banc §3, §8, §11 à §13
- [x] Driver `COPROCESSEUR` : `web_sensor` (ligne précalculée), routes GET/POST `/coprocesseur` — preuve : banc §1, §8 à §10 ; solidifieur : 15 closures, 0 anonyme
- [x] `data/sd/html/coprocesseur.html` (gabarit, confirmation JS, retour automatique) — preuve : partie R du banc (rendu Chrome, 7/7)
- [x] Charte des logs respectée (hook `verifie_berry_edition` sans avertissement) — preuve : `verifie_berry.py` → 0 erreur, 0 avertissement de charte
- [x] Banc A1 vert — preuve : `banc_coprocesseur.py` rc=0, `BANC_COPROCESSEUR_COMPLET: OK`

## A3 — Branchement sur le P4
- [x] `_persist.json` du P4 : bloc `serveur.coprocesseur` `{"activation":"ON","url":"https://ota.tasmota.com/tasmota32/coprocessor"}` — preuve : json.load OK
- [x] `autoexec.be` du P4 : `demarrage.charge(["controleCoprocesseur"], "serveur.coprocesseur")` (pas d'`importe` : aucune globale) — preuve : banc_demarrage P4 OK (driver COPROCESSEUR, minuterie coprocesseur)
- [x] `platformio_tasmota_cenv.ini` (env P4) : module ajouté à `custom_berry_solidify` ; exclu des 7 autres listes `custom_files_exclude` à côté de `controleES8311.be` — preuve : banc_demarrage, les 5 autres cartes sans le fichier
- [x] `solidifie_et_compile_berry.py` sur le module : .h compilé, 0 anonyme ; globale ajoutée à `solidify_all_python.be` si besoin — preuve : « LE .h COMPILE », 15 closures, 0 anonyme ; aucune globale nouvelle
- [x] `banc_demarrage.py` : instantané du P4 mis à jour, les 5 autres cartes inchangées — preuve : VERT 6/6 ; `banc_boot.py` BANC_BOOT: OK
- [x] `genere_schema_persist.py` relancé si le schéma du persist le demande — preuve : `--valide` du persist P4 → 0 erreur, pas de régénération nécessaire

## A4 — Rendu et documentation
- [x] Page `/coprocesseur` rendue dans Chrome sans interface (leçon du 2026-10-16), sans erreur JS — preuve : partie R du banc, ERREURS=0. La ligne d'accueil est jugée sur son contenu (banc §8) : elle s'affiche dans le tableau de Tasmota, qui n'est pas rendu hors carte
- [x] `outils_docs/README.md` : section « Firmware du coprocesseur Wi-Fi des P4 » ; `CLAUDE.md` : entrée dans la carte des documents — preuve : sections ajoutées
- [x] `verifie_references_docs.py` vert — preuve : 1 seul défaut, antérieur et sans rapport (`CLAUDE.md:277`, `tasmota/tasmota.ino.cpp`, fichier généré par le build, absent hors build) ; mes renvois sont valides

## A5 — Essai sur le P4 (avec l'utilisateur, qui lance les builds)
- [x] Build P4 + FS par l'utilisateur ; heure du firmware postérieure au commit — preuve : `Status 2` BuildDateTime 2026-10-26T19:32:36, commit `5638b27ac` à 07:41
- [x] Alerte visible sur l'accueil, page `/coprocesseur` cohérente (2.6.6 → 2.12.13, publiée), une seule requête au serveur — preuve : `/?m=1` « v2.6.6 → v2.12.13 (disponible) » ; `window.COPRO` essais 1, publiee true, defaut 2.12.6 ; console `/cs` 20:04:38 « Version v2.12.13 publiee » (syslog arrêté : console web à la place)
- [x] Mise à jour lancée par le bouton, au moment choisi par l'utilisateur — preuve : message retenu lu sur le broker le 2026-10-26 à 21:33 avec `"Lancee":true` (seul le POST de la page le pose) ; transfert complet (1 222 736 o) puis `HST: ota_end failed 5379` : le C6 refuse l'image (bug esp-hosted-mcu #143, voir A8)
- [x] `tele/garage/COPROCESSEUR` retenu — preuve : abonnement au broker 192.168.0.5 le 2026-10-26 à 21:33 → `retain=True`, `{"Lancee":true,"Attendue":"2.12.13","AJour":false,"Publiee":true,"MCU":"esp32c6","Version":"2.6.6"}` ; avant : console `/cs` 20:04:38 « (persistant) »

## A6 — Alerte par MQTT (décidé le 2026-10-26 : topic dédié retenu, ON sur le P4)
- [x] Option `"mqtt"` du bloc `serveur.coprocesseur` (absente = OFF) ; `tele/<topic>/COPROCESSEUR` retenu à chaque changement d'état et à chaque `Mqtt#Connected` — preuve : `controleCoprocesseur.be::COPROCESSEUR.publie`, banc §14 (14 vérifications)
- [x] Témoin : publication sans « retenu » → banc rouge — preuve : mutant `json.dump(etat), false)` → rc=1, « retard publie, sur le bon topic, RETENU » en ECHEC
- [x] `"mqtt": "ON"` dans le persist du P4 — preuve : json.load → `{'activation': 'ON', 'url': …, 'mqtt': 'ON'}`
- [x] Solidification et démarrage — preuve : « LE .h COMPILE », 16 closures, 0 anonyme ; banc_demarrage VERT (règle `Mqtt#Connected` dans la référence P4), banc_boot OK

## A7 — Future carte P4 : alerte posée par l'outil de création (décidé le 2026-10-26)
Les envs `tasmota32p4-base-*` n'ont ni dossier `data/` ni autoexec du framework : une carte P4 naîtra d'un modèle, par la page « Fichiers Berry par env ».
- [x] `outils_pc/fichiers_berry_coprocesseur.py` : selon la puce de la base, persist (bloc ajouté ou `activation` → OFF, texte gardé octet pour octet), autoexec (ligne ajoutée dans le bloc `if demarrage.prologue()`), cenv (exclusion retirée, ou solidification retirée + exclusion ajoutée) — preuve : essai sur les persists de la cuve, du rideau, de la cave S3 et du P4 (reste identique)
- [x] Branché dans `fichiers_berry_creation._calcule` (diff de l'autoexec compris) et `cree` (autoexec écrit) — preuve : `test_fichiers_berry_creation.py` VERT, 110 vérifications (P4 depuis S3, P4 depuis P4, S3 depuis P4, S3 depuis S3, cas limites)
- [x] Témoin : adaptations neutralisées → banc rouge — preuve : rc=1, 10 KO
- [x] Bancs voisins inchangés — preuve : renommage, suppression, web VERT

## A8 — Échec de la mise à jour et C6 bloqué (décidé le 2026-10-26)
Le C6 refuse toute image (`Failed 5379` = ESP_ERR_OTA_VALIDATE_FAILED, avec 2.12.13 comme avec 2.12.6) : bug esp-hosted-mcu #143, bootloader d'usine en DIO + application 2.6.6 en QIO reçue par OTA. Seul un flash série du C6 (version ≥ 2.9) le débloque.
- [x] Échec affiché et nouvel essai : règle `HostedOta`/`HostedLoad` → `resultatOta` ; `Failed <code>` → ligne « échec », bloc « Échec » de la page (code, cause), bouton « Réessayer », `Echec` en MQTT — preuve : banc §15, rendu Chrome « apres un echec »
- [x] `Failed 5379` → état « bloqué » : version notée dans `serveur.coprocesseur.bloque` (persist sauvé), plus de bouton ni de requête au serveur ; ligne d'accueil seulement pendant la 1re minute après le démarrage ; page `/coprocesseur` (lien #143, flash série) et MQTT `Bloque: true` gardent l'information ; une autre version lue sur le C6 efface la clé — preuve : banc §16, rendu Chrome « bloque », `banc_coprocesseur.py` COMPLET OK
- [x] Solidification et démarrage — preuve : « LE .h COMPILE » ; banc_demarrage VERT (règles `HostedOta`, `HostedLoad` dans la référence P4) ; banc_boot OK
- [ ] Sur le P4, après build + FS par l'utilisateur et un `HostedOta` refusé : état « bloqué » sur la page, `Bloque: true` retenu ; au redémarrage suivant, ligne d'accueil visible puis effacée à 60 s, aucune requête au serveur
- [ ] Après un flash série du C6 en 2.12.13 (accord et matériel de l'utilisateur) : `Hosted` = 2.12.13, clé `bloque` effacée, alerte disparue, `AJour: true` retenu

## Améliorations restantes
- [x] [projet] Même alerte pour une future carte P4 (`ESP32P4_BASE_WIFI6`) : bloc persist + ligne d'autoexec — preuve : A7
- [x] [projet] Signaler aussi l'alerte par MQTT (télémétrie) si l'utilisateur le souhaite — preuve : A6

## Vérification
Bancs : `banc_coprocesseur.py` (code 0), `banc_demarrage.py`, `solidifie_et_compile_berry.py`, `verifie_references_docs.py`.
Sur carte : syslog (skill logs-cartes) pour l'unique requête et le résultat, `Hosted` avant et après.
Aucun build ni téléversement de ma part : l'utilisateur les lance. Un build ne doit pas tourner pendant l'édition de `data/`.
