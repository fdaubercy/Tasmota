# Ethernet en option sur le maître ModBus P4 (SERVEUR-GARAGE) — design

Date : 2026-10-26 · Statut : validé par l'utilisateur en conversation, à planifier.

## 1. Intention

Le maître ModBus `tasmota32p4-garage-serveur-modbus` (Waveshare ESP32-P4-Module-DEV-KIT, Wi-Fi par
coprocesseur ESP32-C6 en ESP-Hosted/SDIO) a un port RJ45 (PHY IP101) que personne n'utilise.
L'utilisateur veut pouvoir l'activer **à la demande** pour :

- fiabiliser le lien amont (MQTT, OTA, syslog, pages web) ;
- soulager la radio du C6, qui porte aujourd'hui la STA **et** le point d'accès des esclaves.

## 2. Objectifs, non-objectifs, anti-objectifs

**Objectifs**
- L'Ethernet est une **option**, coupée par défaut. Le fonctionnement actuel (Wi-Fi STA en
  192.168.0.43 + point d'accès `SERVEUR-GARAGE-GATEWAY` 192.168.4.1/24 avec NAPT) reste le défaut et
  ne change pas tant que l'option est coupée.
- Activation / désactivation par **`ReglageGlobal Ethernet ON|OFF`** et par un **bouton dans la page
  Configuration** du P4.
- Paramétrage dans le persist (bloc `serveur.ethernet`), appliqué au démarrage par `configGlobal`.
- Ethernet actif : **IP fixe 192.168.0.50** (décision de l'utilisateur ; .40 à .49 sont pris dans le
  plan d'adressage de `outils_docs/README.md` § des IP fixes, .44 = Serveur de Grenier RDC).
- Ethernet actif : la STA **reste connectée en 192.168.0.43** (elle est indispensable au point
  d'accès, voir §4.1). .43 reste l'adresse « officielle » du P4 (OTA, outils PC, `ipMaitre` envoyé
  aux esclaves, redirections de la box).

**Non-objectifs**
- Couper la STA (« Ethernet seul ») : rejeté, il imposerait de modifier le pilote C
  `xdrv_58_range_extender.ino` (§4.1). À reconsidérer seulement si la mesure du §6 le justifie.
- Bascule automatique Wi-Fi ↔ Ethernet sur panne (secours) : non demandé.
- Ethernet sur les autres cartes : aucune autre carte n'a de PHY. Elles reçoivent la clé (règle du
  dépôt) mais à `OFF`, et le code ne doit rien leur envoyer.
- Garantir que l'Ethernet porte le trafic sortant (décision de l'utilisateur, 2026-10-26) : si la
  mesure du §6.5 montre que MQTT / syslog restent sur la STA ou varient d'un démarrage à l'autre, **le
  chantier s'arrête là**, l'option est livrée telle quelle et son effet réel documenté. Un correctif C
  (priorité de route, Range Extender) serait un chantier à part.
- Reflasher les autres cartes : seul le P4 est téléversé dans ce chantier (mon choix) ; les autres
  prennent le nouveau socle à leur prochain build, `banc_demarrage` prouvant qu'il ne change rien
  pour elles.

**Anti-objectifs** (échec même si « ça marche »)
- Toucher au comportement des cartes sans Ethernet (S3, ESP32 classiques) : `configGlobal` est
  solidifié dans le socle commun de **toutes** les cartes.
- Perdre la cuve ou le rideau (point d'accès qui disparaît, NAPT cassé, redirections `RgxPort` HS).
- Un redémarrage en boucle (commande qui redémarre envoyée à chaque boot parce que la comparaison
  échoue).
- Modifier un fichier C amont.

## 3. État actuel (vérifié dans le code le 2026-10-26)

- **Ethernet déjà compilé** : `USE_ETHERNET` défini sans condition pour `FIRMWARE_TASMOTA32`
  (`tasmota/include/tasmota_configurations_ESP32.h:803`) ; `CONFIG_ETH_ENABLED=y` et
  `CONFIG_ETH_USE_ESP32_EMAC=y` dans le sdkconfig P4 du framework. Non vérifié sur binaire ni sur
  carte.
- **Broches déjà au template** (`tasmota/user_config_override.h:1739`) : GPIO31 = ETH MDC (5568),
  GPIO51 = ETH PHY POWER (5536, reset de l'IP101), GPIO52 = ETH MDIO (5600), et
  `"CMND":"ethtype 1|ethaddress -1"`. Les broches RMII (28, 29, 30, 34, 35, 49, 50) sont fixes et
  libres dans le template. Horloge RMII externe sur GPIO50 imposée par Tasmota sur P4
  (`xdrv_82_esp32_ethernet.ino:287-291`) : `EthClockMode` est sans effet.
- **Persist** : bloc `drivers.Ethernet` (mêmes broches) dans
  `data/garage/tasmota32p4-serveur-modbus/_persist.json:1061-1089`, utilisé seulement pour
  reconstruire le template. **Aucun code Berry n'envoie `Ethernet`, `EthType`, `EthAddress`,
  `EthIPAddress`…**
- **Le `CMND` du template est perdu** : `configGlobal` réapplique le template sans sa partie `CMND`.
  Après une remise à zéro des réglages, `EthType` retomberait à `ETH_TYPE 0` (LAN8720,
  `my_user_config.h:1265`) : mauvais PHY.
- **Commandes Tasmota** (`xdrv_82_esp32_ethernet.ino:397-477`) : `Ethernet 0|1`, `EthType`,
  `EthAddress` → redémarrage (`restart_flag=2`) ; `EthIPAddress`, `EthGateway`, `EthSubnetmask`,
  `EthDNSServer` → appliquées à chaud ~2 s plus tard. Réponse de l'IP : `"0.0.0.0 (ip DHCP)"`, ce
  que `configGlobal.testeParam` sait déjà comparer (coupe à `" ("`). Nom réseau Ethernet =
  `<Hostname>-eth`. Règles : `ETH#Connected`, `ETH#Disconnected`. `Status 5` : bloc
  `StatusNET.Ethernet`.
- Au démarrage, Tasmota remet `Wifi 1` de force si `Ethernet 0` (`tasmota/tasmota.ino:624-626`).
- Berry : `tasmota.eth()` → `up`, `mac`, `ip`, `ip6`, `ip6local` (`xdrv_52_3_berry_tasmota.ino:349-386`).

## 4. Contraintes

### 4.1 Le point d'accès exige la STA
`xdrv_58_range_extender.ino:497-526` ne monte le point d'accès que si `Wifi.status == WL_CONNECTED`
en mode STA, et redémarre la carte si le mode n'est plus `WIFI_AP_STA`. D'où la double attache
STA + Ethernet.

### 4.2 Deux IP dans 192.168.0.0/24
STA .43 et Ethernet .50 sont dans le même sous-réseau. lwIP prend la première interface de sa liste
dont le sous-réseau contient la destination ; l'ordre dépend de l'ordre de démarrage des interfaces
(`outils_docs/DIAGNOSTIC_UDP_2026-10-17.md` §1.1-1.2). Le trafic vers le broker (192.168.0.5), le
syslog (192.168.0.3) et la box peut donc sortir par l'une ou l'autre. Priorités par défaut
ESP-IDF : STA 100, ETH 50, AP 10 (`esp_netif_defaults.h:54/68/94`). **Non mesuré** : c'est l'objet
du §6.

### 4.3 Ce que Tasmota annonce quand l'Ethernet a une IP
- La découverte native (`xdrv_12_discovery.ino:35-43`) publie `config.ip` = IP Ethernet et
  `config.hn` = `SERVEUR-GARAGE-eth`. Or `discoveryFonctions.be:743-749` en tire le bouton du maître
  sur la page `/discovery` : port distant `10000 + 50` (la box redirige 10043) et
  `SERVEUR-GARAGE-eth.local` (le mDNS publie `SERVEUR-GARAGE`). **À corriger** : utiliser l'IP et le
  nom de la STA pour le maître quand l'Ethernet est actif.
- `NetworkAddress` / `NetworkHostname` (`support_network.ino:92-123`) préfèrent l'Ethernet ; à
  inventorier côté Berry (lecture seule pour l'instant).
- **Inchangés** (lisent la STA) : `Status 5` → `StatusNET.IPAddress` (`support_command.ino:1078`),
  donc `ipMaitre` envoyé aux esclaves (`udpFonctions.be:339`) et la fiche discovery du maître
  (`discoveryFonctions.be:251-330`) ; `ipSTA()` et le multicast (`udpFonctions.be:602-694`) ;
  `surveilleWifi` (`controleGeneral.be:65`) ; `RgxPort` (mémorise `WiFi.localIP()`,
  `xdrv_58:295`).

### 4.4 Déploiement
`configGlobal.be`, `globalFonctions.be`, `controleWeb.be`, `discoveryFonctions.be` sont dans
`berry_commun.socle` (`platformio_tasmota_cenv.ini:35-55`), solidifiés pour **toutes** les cartes :
la modification part en firmware (pas en OTA du FS seul) et doit être sans effet sur les cartes à
`OFF`.

### 4.5 Règles du dépôt qui s'appliquent
- Nouvelle clé de persist : dans **chaque** `_persist.json` suivi qui porte le bloc concerné, valeur
  explicite (`tasks/lessons.md`, 2026-10-06), fins de ligne de chaque fichier conservées. Régénérer
  `outils_docs/schemas/persist.schema.json` (`genere_schema_persist.py`).
- Commande qui redémarre la carte : **écrire le persist avant** de l'envoyer (leçon du 2026-09-27,
  `Topic`).
- Charte des logs Berry (CLAUDE.md § « Logs Berry ») ; contrôle `verifie_berry` à chaque édition.
- Jamais d'édition de `data/` ni de `pio run` pendant un build de l'utilisateur.
- Aucun `Br` ouvrant une socket sur une carte sans prévenir (leçon du 2026-10-25).

## 5. Ce qui a été décidé

### 5.1 Persist
Nouveau bloc `serveur.ethernet`, ajouté aux 8 `_persist.json` qui portent `serveur` (liste :
`git ls-files | grep _persist.json`, hors `*-sauvegarde`), **`"activation": "OFF"` partout, P4
compris** :

```json
"ethernet": {
    "activation": "OFF",
    "type": 1,
    "adresse": -1,
    "IP": {
        "IPAddress": "192.168.0.50",
        "IPGateway": "192.168.0.254",
        "Subnet": "255.255.255.0",
        "DNSServer": "192.168.0.254"
    }
}
```

Sur les cartes sans PHY, les valeurs `type` / `adresse` / `IP` sont celles du P4 ou neutres (choix du
builder) ; elles ne sont jamais envoyées tant que `activation` vaut `OFF`.

### 5.2 Application au démarrage (`configGlobal`)
**Piège relevé à la relecture (vérifié)** : toutes les cartes ESP32 du parc compilent le pilote
Ethernet (`FIRMWARE_TASMOTA32` sur toutes les bases, `platformio_tasmota_cenv.ini:86/119/152`) et
Tasmota met `Ethernet` à 1 par défaut (`settings.ino:1081`) ; sans broches ETH c'est sans effet
(`xdrv_82_esp32_ethernet.ino:257`). La réponse de la commande `Ethernet` ne distingue donc pas le P4.

- **Carte « avec Ethernet »** (mon choix) = broches ETH MDC **et** ETH MDIO présentes dans le template
  courant (en Berry, par ex. `gpio.pin_used(gpio.ETH_PHY_MDC)` et `gpio.ETH_PHY_MDIO`, à vérifier par
  le builder). Toute autre carte ne reçoit **aucune** commande Ethernet, quel que soit le persist ; son
  drapeau reste tel quel.
- Carte avec Ethernet, `activation` = `ON` : aligner `EthType` ← `type`, `EthAddress` ← `adresse`, `EthIPAddress` /
  `EthGateway` / `EthSubnetmask` / `EthDNSServer` ← `IP`, puis `Ethernet` ← `ON`, chacun par
  `testeParam` (rien n'est envoyé si la valeur est déjà la bonne).
- Carte avec Ethernet, `activation` = `OFF` : `Ethernet` ← `OFF` si Tasmota le donne actif. Sur le
  P4, c'est probablement le cas aujourd'hui (drapeau par défaut, broches au template) : **un
  redémarrage unique au premier déploiement**, accepté (le déploiement est un téléversement, donc
  déjà un redémarrage).
- Une carte dont le firmware ne connaît pas la commande `Ethernet` (réponse sans clé `Ethernet`) ne
  reçoit **aucune** commande Ethernet (garde de sûreté en plus du critère des broches).
- Les commandes qui redémarrent (`EthType`, `EthAddress`, `Ethernet`) ne doivent provoquer **qu'un**
  redémarrage, une seule fois : après lui, toutes les valeurs comparées sont égales.
- Les clés absentes (persist ancien) valent « option coupée » (`.find(…)` avec défaut).

### 5.3 Commande `ReglageGlobal Ethernet [ON|OFF]`
Sous-commande de `ReglageGlobal` (`globalFonctions.reglageGlobal`, `globalFonctions.be:667`) :
- `ON` / `OFF` : écrit `serveur.ethernet.activation`, `persist.save(true)`, **puis** envoie la
  commande Tasmota (qui redémarre la carte). Réponse JSON avant le redémarrage.
- Sans argument : état, sans rien changer — activation au persist, lien (`tasmota.eth()["up"]`), IP,
  MAC.
- Sur une carte sans Ethernet (critère du §5.2) : refus explicite, rien n'est écrit.
- Ajoutée à l'aide (`globalFonctions.aideReglageGlobal`).

### 5.4 Bouton dans la page Configuration
Bouton « Ethernet : activé / désactivé » dans le menu Configuration (`web_add_config_button`),
**uniquement sur une carte avec Ethernet** (critère du §5.2). Il affiche l'état et bascule après une
confirmation (« la carte va redémarrer »), par le même chemin que la commande (§5.3).

### 5.5 Correction de `/discovery`
Le bouton du maître (`discoveryFonctions.be:743-749`) prend l'IP et le nom de la STA, pas
`config.ip` / `config.hn`, quand ceux-ci sont ceux de l'Ethernet. `afficheDiscovery` est dans le
socle : la correction vaut pour la page `/discovery` de **toutes** les cartes (mon choix). Source :
la fiche `maitre` rangée sous la même MAC dans `/json/discovery.json` (son `IPAddress` vient de
`Status 5` → `StatusNET.IPAddress` = STA, `discoveryFonctions.be:251-330`) ; à défaut de fiche,
retirer le suffixe `-eth` du nom.

### 5.6 Inventaire de `NetworkAddress` / `NetworkHostname`
Lister les usages Berry qui liraient l'IP ou le nom Ethernet (en dehors de `/discovery`) ; **liste
seulement** (mon choix) : une correction éventuelle va dans « Améliorations restantes » du plan.

## 6. Essais (ordre décidé avec l'utilisateur)

1. **Sur table, près de la box, avant tout code** : câble branché, `Ethernet 1` à la main (redémarre),
   `Status 5` → bloc `Ethernet` avec une IP ; vérifier `EthType` = 1. Remettre `Ethernet 0` ensuite.
   Prouve que le PHY et le firmware fonctionnent.
2. Code et persist (§5), bancs Berry du dépôt (skill `bancs` : `banc_boot`, `banc_demarrage` dont
   les instantanés des 6 cartes doivent rester identiques pour les cartes à `OFF`), relecture.
3. Build + téléversement du P4 ; option à `OFF` : comportement identique à avant (grille ModBus,
   cuve et rideau joignables, `/discovery`).
4. Option à `ON` : `ReglageGlobal Ethernet ON` → un seul redémarrage, IP .50 ; .43 répond toujours ;
   cuve et rideau joignables par le point d'accès et par `RgxPort` (8081/8082) ; `/discovery`
   correcte.
5. **Mesure du routage** (§4.2) sur plusieurs démarrages : par quelle interface sortent MQTT,
   syslog, OTA. Instrument à choisir par le builder, en lecture seule (par ex. compteurs
   d'octets par interface, ou capture côté PC) ; un **témoin** (câble débranché) doit montrer
   l'autre interface. **Quel que soit le résultat**, il est consigné (README + spec) et le chantier
   continue au point 6 : pas de phase corrective dans ce chantier (§2).
6. Débrancher le câble Ethernet option active : le P4 reste joignable en .43, pas de redémarrage
   en boucle.
7. Remontage au garage.

## 7. Laissé au builder
- Valeurs neutres du bloc sur les cartes sans PHY.
- Libellés du bouton et de la réponse JSON, emplacement exact du code web (`controleWeb.be` ou
  autre module du socle).
- Instrument de mesure du routage (§6.5).
- Mise à jour de la doc (`outils_docs/README.md` : plan d'adressage avec .50, mode d'emploi de la
  commande) et de `CLAUDE.md` si un nouvel outil apparaît.
