# Débits de la nourrice sur deux cartes : acquisition esclave, affichage maître (conception du 2026-11-09)

Chantier : `tasks/plans/debitmetres-chauffage.md`, action A8. Étude de faisabilité : § 7 quinquies de
`outils_docs/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`.

## 1. Intention

Séparer la mesure et l'affichage des 6 débits de la nourrice de chauffage :
- la **carte d'acquisition** (la carte des débits existante, `data/bureau/tasmota32s3-serveur-debits-pac`) compte
  les impulsions, calcule les 6 débits et sert la page d'équilibrage ;
- une **carte d'affichage** neuve montre les 6 débits sur son écran TFT.

Pourquoi : isoler le comptage du firmware LVGL (le plus gros, le plus souvent mis à jour), libérer la flash de la
carte d'acquisition, et ne plus dépendre des broches libres d'un module d'affichage.

## 2. Décisions de l'utilisateur (2026-11-09)

| Sujet | Décision |
|---|---|
| Écran et délai | L'écran est près de la nourrice ; le nouveau débit doit y apparaître 1 à 2 s après la fin de chaque fenêtre de mesure |
| Lecture | **Une seule requête ModBus 0x04** relit les 6 débits |
| Push | L'acquisition **pousse les 6 débits en UDP** à chaque nouvelle mesure (fin de fenêtre) ; après 2 fenêtres sans nouvelles, l'écran affiche « inconnu » |
| Garage | Le nouveau comportement ne s'active **que si le persist le demande** ; le P4, la cuve et le rideau ne le voient jamais |
| Carte d'affichage | À créer (assistant persist) : S3 DevKitC-1 N16R8, TFT ILI9488 480×320 + tactile XPT2046, HASPmota, page du modèle B |
| Identité de l'affichage | Lieu bureau, nom « Écran Débits de PAC », env `tasmota32s3-bureau-ecran-debits-pac`, IP 192.168.0.51, topic `chauffage/pac/ecran` |
| Rôles | **Affichage = maître ModBus et maître Range Extender (id 0)**, avec le point d'accès `SERVEUR-DEBITS-PAC-GATEWAY` (repris tel quel) et le NAPT |
| Acquisition | **Esclave id 1**, Range Extender **laissé activé** (id 1), comme la cuve et le rideau du garage |
| Liaison | Relevé sur **RS485** par un module **à direction automatique, comme le XY-017 de la cuve**, sur chaque carte (pas de broche DE/RE), 19 200 bauds 8N1 pour commencer ; push sur le Wi-Fi |
| `user_config_override.h` | Accord donné pour la section de l'acquisition (`FIRMWARE_ESP32S3_BUREAU_SERVEUR_DEBITS_PAC`) et pour la nouvelle section de l'affichage |
| Sans Wi-Fi | `serveur.wifi.timerRebootSansWifi` à **0** sur l'acquisition, comme la cuve : elle ne redémarre pas quand l'affichage est absent |
| Page d'équilibrage | Reste sur la carte d'acquisition |

Limite acceptée par l'utilisateur : pendant un redémarrage de la carte d'affichage, la carte d'acquisition perd le
réseau (elle est derrière son point d'accès). Elle continue de compter ; page, MQTT et OTA reviennent avec l'affichage.

## 3. Objectifs, non-objectifs, anti-objectifs

Objectifs :
- les 6 débits, leur état (imprécis, muet) et le total sur l'écran de la carte d'affichage, au plus 2 s après la
  fin de chaque fenêtre de mesure de l'acquisition, quand le Wi-Fi passe ;
- par le seul RS485 (Wi-Fi coupé) : les mêmes valeurs, au rythme du relevé ;
- une valeur absente ou périmée est affichée « inconnu », jamais présentée comme fraîche.

Non-objectifs : commander l'acquisition depuis l'écran (réglages K, noms, fenêtre : toujours par `ReglageDebits`
sur l'acquisition) ; secours automatique d'une voie de commande à l'autre ; ModBus TCP ; afficher les débits sur
le P4 du garage.

Anti-objectifs (échec même si « ça marche ») :
- un changement de comportement, de trame ou de délai sur le bus du garage ;
- un débit faux affiché comme valide (par exemple les « 0 » d'une réponse mal remplie, § 5.1) ;
- une perte d'impulsions sur l'acquisition à cause du nouveau code.

## 4. Architecture

```
            Wi-Fi maison (box)                         point d'accès SERVEUR-DEBITS-PAC-GATEWAY (NAPT)
  PC, téléphone ── 192.168.0.51 ── AFFICHAGE (id 0) ── 192.168.4.1 ─────────── ACQUISITION (id 1), 192.168.4.x
                                   maître ModBus           RS485 (MAX3485)      esclave ModBus, Range Extender id 1
                                   maître Range Extender   ◄────── relevé ────  6 débitmètres, page d'équilibrage
                                   écran TFT HASPmota      ◄──── push UDP ────
```

- Accès à l'acquisition depuis le Wi-Fi maison : `http://192.168.0.51:8080/` (port relayé `8080 + id - 1` = 8080,
  `rangeExtenderFonctions.routageRangeExtender`), page d'équilibrage `http://192.168.0.51:8080/equilibrage`.
- Le push UDP part en multicast 224.3.0.1:4000 depuis l'acquisition et arrive à l'affichage par le réseau du point
  d'accès, comme la cuve vers le P4 (il ne traverse pas le NAPT vers la maison, c'est voulu).
- `controleRangeExtender.be::init` aligne `drivers.ModBus.id` et `serveur.udp.id` sur `serveur.rangeExtender.id` :
  ici les deux cartes ont des ids égaux partout (0 et 1), aucune exception à ajouter.

## 5. Protocole

### 5.1 Registres servis par l'acquisition

- 7 entrées analogiques virtuelles dans le persist de l'acquisition (groupe `analogiques`, aujourd'hui OFF) :
  `analogique1` à `analogique6` = débits des voies 1 à 6 (`virtuel` `Calcul_debit1` à `Calcul_debit6`),
  `analogique7` = **états** (`virtuel` `Calcul_etatsDebits`). Registres `4704 + id - 1` : **4704 à 4710**.
- Unité des débits : **centièmes de L/min**, entier arrondi (`int(q * 100 + 0.5)`), dans un uint32 (2 registres
  par valeur, convention actuelle de `prepareTrame`).
- États (`analogique7`) : bit `i` (0 à 5) = voie `i + 1` muette ; bit `6 + i` = voie `i + 1` imprécise (0 < q < 1).
- Sentinelle `0x7FFFFFFF` (`SENTINELLE_UINT32`) pour une voie sans mesure (`nil` dans `debitsFonctions.debits`) ou
  une valeur qui n'est plus fraîche.
- Fraîcheur : chaque nouvelle mesure appelle `noteMesure` pour les 7 registres. Pour ces registres, la limite de
  fraîcheur est **2 × la fenêtre** (20 s par défaut), pas la limite générale tirée de `TelePeriod` (900 s sur cette
  carte, trop lâche).
- Écriture des valeurs : à la fin de `debitsFonctions.mesure`, après `suitMuets`.
- Démarrage (choix de Claude) : les 7 registres sont **exclus du délai de grâce** de 60 s (`GRACE_DEMARRAGE_S`), qui
  renvoie la `value` gardée dans le persist comme si elle était fraîche ; ils valent la sentinelle jusqu'à la
  première mesure.

**Défaut latent à ne pas propager** (constaté le 2026-11-09, code du jour) : `executeCmdModbus` accepte une requête
de plusieurs valeurs mais n'en remplit qu'une ; `prepareTrame` complète par des zéros (réponse `[v, 0, 0, 0, 0, 0]`).
La lecture groupée ne doit jamais emprunter ce chemin : soit elle remplit les `Count` valeurs, soit elle répond une
exception ModBus. Le garage n'envoie jamais `Count` > 1 ; corriger le défaut pour tous ou seulement sous la clé est
laissé au constructeur, à condition que le garage reste identique octet pour octet (banc).

### 5.2 Lecture groupée (relevé du maître)

- Le maître relit les 7 valeurs en **une requête 0x04** `StartAddress 4704`, `Count 7` (uint32), au lieu d'une
  requête par appareil.
- Correspondance : la valeur `i` de la réponse va à l'appareil du maître dont le registre est `StartAddress + i`
  (`type + idModBus - 1`). Une sentinelle est traitée **valeur par valeur** (aujourd'hui seule `Values[0]` est lue).
- Côté maître, 7 entrées analogiques virtuelles (`virtuel` `ModBus_TasmotaSlaveModBus1`, `idModBus` 1 à 7) portent
  `value`, `etatConstate` et `constateA` comme aujourd'hui (`modBus_TasmotaSlaveModBus.be::recupereReponseModBus`).
- Période du relevé : réglable par une clé du maître, défaut **30 s** (valeur actuelle, garage inchangé) ; la carte
  d'affichage la pose à **10 s**, égale à la fenêtre par défaut, pour que le RS485 seul tienne « inconnu après
  2 fenêtres ». Le chien de garde garde sa règle (3 × période).

### 5.3 Push UDP

- À chaque nouvelle mesure, l'acquisition appelle `modbusFonctions.pousseEtat(4704, "uint32", [7 valeurs])` :
  trame 0x10 de 14 registres dans l'enveloppe `ModbusPushUDP <seq> <hexa>` existante (37 octets de trame).
- Le maître accepte le push comme les autres (`udpFonctions.lireUDP`, `accepteSeq`, `noteIP`, `noteContact`) puis
  **répartit les 7 valeurs** sur ses 7 appareils, avec la même règle que la lecture groupée (§ 5.2).
- Pas d'accusé, pas de renvoi : une perte est réparée par la mesure suivante ou le relevé (principe de
  `PROTOCOLE_MODBUS.md` § 9).

### 5.4 Activation par le persist (garage inchangé)

| Carte | Clé | Effet si absente ou OFF |
|---|---|---|
| Acquisition | une clé sous `modules.debits` (ou `drivers.ModBus`) qui active l'écriture des 7 registres et le push | aucun registre de débit servi, aucun push |
| Maître | une clé par esclave dans `drivers.ModBus.environnement.TasmotaSlaveModBus<n>` qui active la lecture groupée et la répartition des push multi-valeurs | une requête par appareil, seule `Values[0]` lue (comportement d'aujourd'hui) |
| Maître | une clé de période du relevé | 30 s |

Les noms exacts des clés et leur sous-commande `ReglageModbus` (sur le modèle de `relaisPushMQTT`) sont laissés au
constructeur. Les persists du garage ne reçoivent aucune de ces clés.

## 6. Affichage

- La carte d'affichage reprend le code d'écran de `debitsFonctions.be` (`debitsFonctions_ecran`,
  `debitsFonctions_demarreEcran`, veille `debitsFonctions_appliqueVeille`, page HASPmota `pages.jsonl` du modèle B),
  alimenté par les 7 valeurs reçues au lieu de la mesure locale : centièmes → L/min, sentinelle ou
  `etatConstate` ≠ `valide` → « inconnu », bits d'état → muet et imprécis.
- « Inconnu » : une voie dont la dernière mise à jour (`constateA`) a plus de 2 fenêtres. La fenêtre est connue du
  maître par une clé de son persist (défaut 10 s), recopiée à la main si on la change sur l'acquisition.
- Total (choix de Claude) : somme des voies valides, comme `debitsFonctions_total` aujourd'hui, mais marqué
  « partiel » dès qu'une voie est inconnue, et « inconnu » si aucune ne l'est pas.
- Noms des 6 départs : dans le persist de l'affichage (champ `nom` des 7 entrées), saisis à la création.
- Le code d'écran ne s'exécute plus sur l'acquisition : `drivers.ecran` passe à OFF et le firmware de l'acquisition
  revient sur une base **sans LVGL** (flash mesurée à 70,8 % sans écran, plan A3).
- Qu'on déplace ce code dans un module commun aux deux cartes ou qu'on le recopie dans le dossier de l'affichage
  est laissé au constructeur.

## 7. Réseau, persists et matériel

Affichage (nouvel env, assistant persist :7900) :
- `serveur.rangeExtender` : `activation` ON, `id` 0, point d'accès `SERVEUR-DEBITS-PAC-GATEWAY` (mot de passe
  recopié côté serveur depuis le persist actuel de l'acquisition, jamais affiché), `routeNAPT` ON ;
- `drivers.ModBus` : `activation` ON, `id` 0, `typeComm.Serial` ON, `typeComm.UDP` ON, 19 200 bauds 8N1 ;
- `drivers.ecran` : celui de l'acquisition d'aujourd'hui (Option A3 GPIO 21, SPI 10/11/12/13, DC 14, XPT2046 CS 41,
  rétroéclairage 40 en type 992, reset 42) ;
- RS485 : GPIO 17 (RX) et 18 (TX), libres sur les deux cartes avec ce brochage ; module à direction automatique
  (type XY-017), donc deux broches seulement.

Acquisition (persist existant, modifié) :
- `serveur.rangeExtender.id` 1 (point d'accès propre comme la cuve : nom laissé au constructeur), `ipMaitre`
  192.168.0.51, `serveur.wifi.reseau1` = `SERVEUR-DEBITS-PAC-GATEWAY` ;
- `drivers.ModBus` : `activation` ON, `id` 1, `typeComm.Serial` ON, `typeComm.UDP` ON, voie de commande `Serial`,
  broches RS485 17/18 (les broches 4/5 actuelles du bloc sont celles des débitmètres 1 et 2) ;
- `drivers.ecran` OFF, base sans LVGL ; autoexec : `controleModbus` et ses dépendances chargés ;
- `serveur.wifi.timerRebootSansWifi` 0.

Section `FIRMWARE_ESP32S3_BUREAU_SERVEUR_DEBITS_PAC` de `user_config_override.h` (accord du 2026-11-09) :
`WIFI_IP_ADDRESS` `0.0.0.0` (DHCP du point d'accès de l'affichage ; la page Build traduit en `192.168.0.51:8080`),
`STA_SSID1` = `SERVEUR-DEBITS-PAC-GATEWAY` (mot de passe recopié, jamais affiché), `WIFI_RGX_SSID` = un nom propre
à l'acquisition (laissé au constructeur), `USE_ILI9488` retiré ; base sans LVGL dans le cenv. Les réglages en flash
l'emportent sur le persist : un changement de `CFG_HOLDER` remet la carte à l'usine (leçon du 2026-11-09), à
prévoir au premier flash (la carte n'a encore jamais été flashée).

Fichiers soumis à l'accord de l'utilisateur avant écriture (règles du dépôt) : `data/fs/*.be`,
`tasmota/user_config_override.h`, les `_persist.json`. L'approbation de cette conception vaut accord pour les
fichiers qu'elle nomme ; tout autre fichier de `data/fs` est demandé à part.

## 8. Vérification

- `banc_test_modbus.py` : garage identique (témoin : sans clé, mêmes requêtes et mêmes trames qu'avant) ; lecture
  groupée de 7 valeurs remplie et répartie ; sentinelle sur une seule voie ; push de 7 valeurs réparti ; témoin
  rouge sur le défaut `[v, 0, 0, …]`.
- `banc_debits.py` : centièmes, sentinelle pour `nil`, bits d'état, `noteMesure` à chaque mesure.
- `banc_demarrage.py` : 6 cartes maintenues inchangées, référence de l'acquisition réenregistrée, carte d'affichage
  ajoutée.
- `decodeur_modbus.py` (sniffeur) : nomme les 7 registres d'une réponse groupée et d'un push.
- `relecteur-berry` sur les `.be` modifiés.
- Sur cartes : écran à jour ≤ 2 s après la fin d'une fenêtre ; Wi-Fi de l'acquisition coupé → valeurs par le RS485
  seul ; câble RS485 débranché → valeurs par le push seul ; les deux coupés → « inconnu » après 2 fenêtres ;
  équilibrage joignable par `192.168.0.51:8080/equilibrage` ; tas mesuré avant et après sur les deux cartes ;
  grille ModBus du garage repassée (`testeur_udp` onglet « Grille ModBus »).

## 9. Laissé au constructeur

Noms des clés du persist et sous-commandes ; découpage du code d'écran (module commun ou copie) ; correction du défaut
`Count` > 1 pour tous ou sous la clé (garage identique) ; nom du point d'accès propre de l'acquisition ; ordre des
travaux ; détail des bancs.
