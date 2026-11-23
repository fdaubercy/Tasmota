# Portail de jardin : choix du module et alimentation (recherche du 2026-11-22)

Notes de recherche sur le matériel de l'esclave 4 (`tasmota32s3-garage-portail-jardin-modbus`, topic `jardin/portail`) et son raccordement à la motorisation **SCS Sentinel OpenGate 1**. Rien n'est essayé sur carte. Rien n'est modifié dans le persist ni dans le firmware.

Contexte du dépôt : `tasks/plans/voie-mqtt.md` A10, `tasks/plans/facade-garage-portail-commande.md`, `outils_docs/reference_berry/TASMOTA_VOLETS_ROULANTS.md`, `data/garage/tasmota32s3-portail-jardin-modbus/`.

## 1. Le besoin

D'après le persist de l'esclave 4 et `controlePortail.be` :

- un ESP32-S3 (l'env actuel est S3) ;
- 2 relais à contact sec, en impulsion de 1 s : un pour 1 vantail, un pour 2 vantaux ;
- 1 entrée à contact sec pour le capteur de fermeture (`interrupteur1`, type 160, contact fermé = portail fermé) ;
- du RS485 pour le ModBus ;
- une alimentation de 12 à 24 V, prise sur la motorisation ou à part.

Brochage actuel du persist : relais sur GPIO 41 et 42, capteur sur GPIO 47. Il serait à refaire pour tout autre module.

## 2. Module candidat : KinCony KC868-A2v3

Source : [fiche KinCony](https://www.kincony.com/esp32-s3-2-channel-relay-module.html).

| Point | Valeur lue |
|---|---|
| Processeur | ESP32-S3-WROOM-1 N16R8 |
| Relais | 2, 10 A, contacts COM, NO, NC |
| Entrées | 2 entrées à contact sec, isolées par optocoupleur |
| RS485 | présent, isolation non précisée |
| Alimentation | 12/24 V continu, protection contre l'inversion de polarité (plage exacte non précisée) |
| Boîtier | rail DIN, coque plastique, indice IP non précisé |
| Autres | Ethernet W5500, RTC DS3231, afficheur SSD1306, 2 sorties 1-wire, carte de 87 x 93 mm |
| Tasmota | la fiche dit que la carte le supporte, sans gabarit ni tableau de GPIO |

Brochage lu sur le [forum KinCony](https://www.kincony.com/forum/showthread.php?tid=7958) et sur l'[exemple ESPHome](https://devices.esphome.io/devices/KinCony-KC868-A2v3), qui concordent :

| Fonction | GPIO |
|---|---|
| Relais 1 / relais 2 | 40 / 39 |
| Entrée 1 / entrée 2 | 16 / 17 (inversées côté ESPHome) |
| RS485 RX / TX | 15 / 7 |
| I2C SDA / SCL | 48 / 47 |
| W5500 (SPI) | CLK 42, MOSI 43, MISO 44, CS 41, INT 2, RST 1 |

À vérifier avant d'acheter :

- aucune broche de direction RS485 (DE/RE) n'est indiquée : l'émetteur-récepteur est-il à direction automatique ?
- tension acceptée par les entrées, isolation du RS485, antenne interne ou externe : non précisées ;
- un 24 V de portail peut monter vers 28 V pendant la charge de la batterie, alors que la plage exacte du module n'est pas donnée ;
- sur ce module, GPIO 41 et 42 sont des broches du W5500 et GPIO 47 est l'I2C : le brochage du persist actuel ne s'y applique pas ;
- prix : non trouvé (boutique KinCony en erreur 429). Les autres cartes de la gamme sont à 45 à 80 dollars.

## 3. Alternatives

| Module | Ce qui va | Ce qui manque ou gêne |
|---|---|---|
| [Waveshare ESP32-S3-Relay-6CH](https://www.waveshare.com/product/iot-communication/wired-comm-converter/rs232-rs485-can-dali2/esp32-s3-relay-6ch.htm) | 7 à 36 V, RS485 isolé, rail DIN, environ 29 $ | 6 relais, aucune entrée numérique (le capteur irait sur un GPIO nu) |
| [Waveshare ESP32-S3-ETH-8DI-8RO](https://www.waveshare.com/esp32-s3-eth-8di-8ro.htm) | entrées de 5 à 36 V isolées, RS485 isolé, ESPHome confirmé | 8 relais, environ 45 à 50 $, surdimensionné |
| Shelly Plus 1 ou 2PM | forme adaptée à un portail | aucune source confirmant Tasmota |
| Module sans marque d'AliExpress | rien de vérifiable | fiches contradictoires |

## 4. AliExpress : état de la recherche

- Annonces visées : `1005009199524600` (KC868-A2v3) et `1005008994665818` (module non identifié).
- Les pages sont rendues en JavaScript : la lecture web ne rend que le pied de page. Titre, prix, vendeur, avis et livraison restent inconnus.
- L'extension Claude in Chrome n'était pas connectée pendant la session. Pour lire ces annonces, la connecter (même compte claude.ai que Claude Code) ou coller le texte de l'annonce dans la conversation.

### Si le module de l'annonce est un ESP32 classique

Il convient pour ce rôle, avec ces conséquences :

- il faut créer un nouvel env, un persist et une section de `user_config_override.h` (page « Assistant persist », 7900) ;
- sans PSRAM, `serveur.discovery` doit rester à OFF, sinon boucle de redémarrage (leçon du 2026-11-21) ;
- la façade du portail lit `/sd/js/volets.js` : prévoir une SD ou de la place en flash (4 Mo juste) ;
- relais et entrée hors des broches de démarrage (0, 2, 12, 15) et des broches 34 à 39 (lecture seule) ;
- exiger un ESP32-WROOM, pas un ESP32-C3.

## 5. Motorisation : SCS Sentinel OpenGate 1

Source : [notice OpenGate 1](https://manuals.plus/scs-sentinel/opengate-1-motorization-of-2-leaf-gate-manual.pdf), pages 8 à 12 (schéma « Wiring diagram »). Carte : **PCB 100**. Moteurs en 24 V continu, alimentation par transformateur 230 V~ avec fusible 2 AL 250 V, fusible de carte T20A 250 V, entrée batterie (BATT) et entrée panneau solaire (SO+, SO-).

### Entrées de commande

Le schéma indique « DRY CONTACT » pour un sélecteur à clé, un bouton poussoir ou un visiophone. Bornier noir :

| Borne | Repère | Usage |
|---|---|---|
| 4 | Total | ouverture des 2 vantaux |
| 5 | Piet | ouverture piéton (1 vantail) |
| 6 | BP | commun |

Câblage prévu : relais « 2 vantaux » entre Total et BP, relais « 1 vantail » entre Piet et BP, en parallèle de la télécommande. Les contacts COM et NO du module suffisent.

À confirmer :

- un forum parle de 4 et 5 pour le piéton ; la notice indique 5 et 6 (« branchement sur 5 et 6 »). La notice prime, à vérifier à l'essai ;
- le micro-interrupteur 1 de la carte doit être sur OFF pour que l'entrée piéton n'ouvre qu'un vantail ;
- une même entrée sert à ouvrir, arrêter et fermer (appui pendant le mouvement = arrêt, appui suivant = reprise, selon `outils_docs/visuels_accueil/CONSIGNES_VISUELS.md`). `TASMOTA_VOLETS_ROULANTS.md` signale que le mode 3 envoie alors deux impulsions de mise en phase : à régler à l'essai.

### Alimentation du module

La notice ne donne aucune sortie « accessoires » chiffrée. Lu sur le schéma :

- clignotant et serrure : 24 V continu ;
- bornier vert PH+ / CO / PH- : alimentation des photocellules (CO = contact de sécurité). C'est le seul 24 V permanent ;
- la notice dit qu'il n'est pas nécessaire de distinguer + et - pour les accessoires : à mesurer au multimètre (continu ou alternatif, volts).

Deux options :

1. **Prélever sur PH+ et PH-**, si la mesure montre du 24 V continu. Fusible de 0,5 A en série. Consommation estimée du module : environ 0,1 A sous 24 V (estimation, non mesurée). La marge de cette sortie n'est pas documentée.
2. **Alimenter le module à part** : alimentation 24 V sur rail DIN ou adaptateur dans le coffret. Carte du portail intacte, option la plus sûre.

Selon l'entrée du module :

| Entrée du module | Câblage |
|---|---|
| 12/24 V ou 7 à 36 V continu | direct, polarité respectée, fusible 0,5 à 1 A sur le + |
| même module, source en 24 V alternatif | pont de diodes et condensateur de 470 µF ou plus, ou module AC-DC |
| 5 V | abaisseur 24 V vers 5 V (MP1584 ou LM2596 réglé à 5 V avant branchement, ou module isolé type Mean Well DDR-15G-5) |
| relais en 12 V | un abaisseur est nécessaire, les relais 12 V grillent sur 24 V |

Précautions :

- diode TVS de 33 V (SMBJ33A) en entrée de l'abaisseur contre les pics des moteurs et de la batterie ;
- ne pas brancher l'USB d'un DevKit en même temps que l'alimentation, sans diode de séparation ;
- relier les contacts des relais uniquement aux entrées de commande (Total, Piet, BP), jamais le 24 V ;
- boîtier IP65 avec presse-étoupes ;
- le coffret contient du 230 V : câbler hors tension, batterie comprise. Faire vérifier par un électricien si doute ;
- garder les photocellules : la notice les exige quand la fermeture automatique est active.

## 6. Points ouverts

- [ ] Mesurer PH+ / PH- au multimètre : continu ou alternatif, tension, avec la carte sous tension.
- [ ] Vérifier la position du micro-interrupteur 1 (OFF = piéton sur un seul vantail).
- [ ] Lire l'annonce AliExpress du module visé (prix, vendeur, caractéristiques, livraison).
- [ ] Obtenir le brochage Tasmota du module retenu, ou le déduire à la main.
- [ ] Confirmer la direction du RS485 (DE/RE) si le module est un KinCony.
- [ ] Essai des entrées Total et Piet, en présence de l'utilisateur, un mouvement à la fois (plan A10).
