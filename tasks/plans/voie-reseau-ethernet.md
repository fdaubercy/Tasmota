---
chantier: voie-reseau-ethernet
titre: Voie Ethernet complète — FTP, UDP, esclaves par le point d'accès, repli sur le Wi-Fi
objectif: Qu'une carte en voie Ethernet garde tous ses services et ses esclaves, et ne devienne jamais injoignable si le câble tombe
statut: actif
cree: 2026-11-02
maj: 2026-11-08
---
# Voie Ethernet complète — FTP, UDP, esclaves par le point d'accès, repli sur le Wi-Fi

## Contexte
Suite de `ReglageGlobal VoieReseau` (plan `cave-s3-waveshare`, non commité au 2026-11-02). Demande de l'utilisateur du
2026-11-02 : FTP sur les deux voies, trous de l'UDP et du Range Extender, esclaves en Wi-Fi quand le maître est en
Ethernet, repli automatique.

**Évaluation du NAPT, par lecture des sources seulement (IDF du dépôt PlatformIO), à prouver sur carte :**
- Le chemin n'est pas lié au Wi-Fi client : `ip4.c` choisit la sortie par `ip4_route`, puis `ip_napt_forward(p, iphdr, inp, outp)`
  réécrit la source avec l'IP de `outp`, quelle qu'elle soit ; le retour passe par `ip_napt_recv` si `!inp->napt`.
- Priorités de route (`esp_netif_defaults.h`) : STA 100, ETH 50, AP 10. Wi-Fi client coupé, la sortie par défaut est donc l'Ethernet.
- `CONFIG_LWIP_IP_FORWARD`, `CONFIG_LWIP_IPV4_NAPT` et `CONFIG_LWIP_IPV4_NAPT_PORTMAP` sont actifs sur S3 et P4.
- Ce qui bloque est dans `xdrv_58` : le point d'accès n'est monté que si `Wifi.status == WL_CONNECTED`, et `RgxPort` prend `WiFi.localIP()`.
- Wi-Fi client ET Ethernet actifs : le NAPT sortirait par le Wi-Fi (priorité 100), donc pas par le câble. Deux IP n'y changent rien :
  dans le même sous-réseau, `ip4_route` prend la première interface de la liste. Il faut garder le client coupé.

**Conséquence sur les deux adresses IP :** elles ne sont pas nécessaires au NAPT (le point d'accès a son propre réseau 192.168.4.x).
Leur seul apport est la fenêtre où le Wi-Fi de repli et l'Ethernet revenu coexistent (A5). D'où une clé FACULTATIVE : sans elle, même IP.

**Se connecter sans connaître l'IP :** par mDNS, `<hostname>.local` (`SERVEUR-RLY-CAVE.local`, `SERVEUR-GARAGE.local`) :
`MDNS_ENABLED` vrai dans `user_config_override.h`, `serveur.mDNS` ON sur ces deux cartes, `CONFIG_MDNS_PREDEF_NETIF_ETH=y` sur S3 et P4.
`StartMdns` publie `TasmotaGlobal.hostname`, donc le même nom sur les deux voies (le suffixe `-eth` n'est que le nom DHCP).
Limites : pas à travers le NAPT, et réseau local seulement. Secours : `Status 5` par MQTT sur le topic de la carte.

## A1 — FTP sur les deux voies
- [x] `globalFonctions.regleFTP` commune, appelée par `WIFI#Connected` et `ETH#Connected` ; règle `controleGeneral_Eth` — preuve : banc_boot.py cas 1-8 OK (rouge avant la correction)
- [x] `banc_demarrage.py` : références des 6 cartes réenregistrées, seule la nouvelle règle change — preuve : banc_demarrage.py VERT, diff limité à la ligne `regles` de chaque référence
- [ ] Sur carte : FTP joignable par l'IP Ethernet. Sources : écoute sur toutes les interfaces (`WiFiServer` sans adresse imposée). Essai possible sans flash : câble sur le P4 (`Ethernet` ON, `UfsFTP` 2, relevé du 2026-11-02 : IP Ethernet 0.0.0.0, donc pas de lien)
- [x] `ESPFtpServer.cpp`, commande PASV : `dataIp = WiFi.localIP()` annonce 0.0.0.0 quand le Wi-Fi client est coupé, donc transferts passifs en échec : utiliser l'IP locale de la connexion de contrôle (`client.localIP()`), après contrôle de sa forme (socket double pile : IPv4 attendue, `dataIp[0..3]`) — preuve : sous `#ifdef ESP32`, repli sur `WiFi.localIP()` si l'adresse n'est pas IPv4 ; compilation de la cave S3 par la page Build le 2026-11-08, `ESPFtpServer.cpp.o` compilé, SUCCESS (Flash 83,4 %)
- [ ] Sur carte, Wi-Fi client coupé : lister et transférer un fichier en mode passif, avec un client qui suit l'adresse annoncée

## A2 — Trous de l'UDP, du Range Extender et des autres modules en Ethernet
Relecture du 2026-11-02 : `controleUDP` et `controleRangeExtender` ne dépendent PAS de `Wifi#Connected` (règles `System` et `Time`, leurs
en-têtes sont périmés). Les vrais trous sont les suivants.
- [x] `System#Boot` (règles de l'UDP, du Range Extender et du TCP) part aussi en Ethernet — preuve : `xdrv_02_9_mqtt.ino:1487`, `rules_flag.system_boot = 1` posé à la connexion MQTT, quelle que soit l'interface ; l'UDP a en plus son secours sans MQTT (`tasmota.is_network_up()`)
- [x] `tcpFonctions` : pas de trou — preuve : sa branche `trigger == "Wifi"` est vide (`tcpFonctions.be::changementEtatDemarrage`), serveur et client créés sur `System#Boot`
- [ ] Une seule fonction « mon IP sur le LAN » : IP de la STA si posée, sinon IP Ethernet (`tasmota.eth()["ip"]`, `xdrv_52_3_berry_tasmota.ino:369`), 0.0.0.0 et nil = absente, utilisée par les trois points suivants
- [ ] `udpFonctions.interfacesMulticastMaitre` / `esclavesBox` : sans STA, liste vide donc multicast « non émis » pour un maître en Ethernet avec des esclaves sur le LAN
- [ ] `udpFonctions.ipSTA` chez un esclave en Ethernet : "" = « toutes les interfaces » (`udpFonctions.be::envoiUDP`) ; essai d'envoi réel à faire sur carte
- [ ] `rangeExtenderFonctions` : hôte de secours lu dans `tasmota.wifi()` : prendre l'IP du LAN
- [ ] `discoveryFonctions` : fiche publiée sous `trigger == "Wifi"` seulement, jamais en Ethernet : règle `Eth` dans `controleDiscovery`, et IP du LAN au lieu de `StatusNET.IPAddress` (0.0.0.0 Wi-Fi coupé)
- [ ] Ne jamais réécrire `serveur.adresseMAC` avec une MAC nulle (`globalFonctions` au boot, `discoveryFonctions`) : sur le P4, `Status 5` lit la MAC du C6 (`WiFiHelper_ESP32.cpp::macAddress`, `CONFIG_ESP_WIFI_REMOTE_ENABLED`), peut-être nulle Wi-Fi coupé ; les S3 lisent l'eFuse (stable) ; la carte changerait de clé dans la découverte
- [ ] En-têtes de `controleUDP.be` et `controleRangeExtender.be` corrigés
- [ ] Bancs : `banc_test_modbus.py`, `test_discovery.be`, `banc_demarrage.py`, cas Ethernet dans le faux firmware (`eth()` y répond toujours `up: false`)
- [ ] Agent `relecteur-berry` sur les modules touchés

## A3 — Esclaves en Wi-Fi quand le maître est en Ethernet
- [ ] `xdrv_58_range_extender.ino` : montage du point d'accès si `WL_CONNECTED` OU `EthernetHasIP()` ; DNS pris sur l'Ethernet ; `RgxPort` sur l'IP Ethernet si la STA est absente ; modification minimale (fichier de l'amont, conflit possible à la synchro)
- [ ] Ordre au démarrage : `WifiDisable` ne doit pas couper un point d'accès déjà monté (`WifiSetMode(WIFI_OFF)`, garde `wifi_down`)
- [ ] `configGlobal_voieReseau` : ne plus forcer le Range Extender à OFF, retirer `activationAvantEthernet` (annule la décision du 2026-11-02, à la demande de l'utilisateur) ; banc_boot cas 6-7 adaptés
- [ ] Compilation de la cave S3 et du P4 par la page Build
- [ ] Essai sur carte : un esclave sur le point d'accès joint le broker MQTT par le câble (trafic vu sortir par l'Ethernet, câble seul branché) ; `RgxPort` joignable depuis le LAN
- [ ] Essai P4 : le C6 tient-il le point d'accès avec le Wi-Fi client coupé ?

## A4 — Deux adresses IP facultatives et accès par le nom
- [ ] Clé facultative `serveur.IPEthernet` (même forme que `serveur.IP`) ; absente = même IP qu'en Wi-Fi ; schéma du persist régénéré
- [ ] `ReglageGlobal VoieReseau` sans argument : répond aussi l'IP en service et le nom `<hostname>.local`
- [ ] Page Build : OTA par `WIFI_IP_ADDRESS` (`build_envs.py`), donc une carte à IP Ethernet distincte n'est pas jointe : accepter le nom `.local` ou l'IP Ethernet
- [ ] Mode d'emploi dans `outils_docs/README.md`
- [ ] Essai : `ping SERVEUR-RLY-CAVE.local` depuis le PC, sur les deux voies

## A5 — Repli automatique sur le Wi-Fi si l'Ethernet tombe
Décisions : `voieReseau` n'est jamais réécrite par le repli ; `Ethernet 0` n'est jamais envoyé (il redémarrerait).
Limite relevée par `relecteur-berry` (2026-11-08) : pendant le repli, le Range Extender reste coupé (`configGlobal_voieReseau`), donc les esclaves du point d'accès restent sans réseau ; A3 lève cette coupure.
- [x] `controleGeneral.surveilleEthernet` (appelée par `every_second`) : drapeau tenu par `ETH#Connected` / `ETH#Disconnected`, faux au démarrage (un démarrage sans câble est couvert) ; PAS `tasmota.eth("up")`, peut-être vrai en IP fixe sans câble — preuve : `controleGeneral.be::surveilleEthernet`, `ethLien` posé par `globalFonctions.be::changementEtatDemarrage` (branche `Eth`) ; nil au démarrage, admis vrai si MQTT connecté Wi-Fi coupé (événement perdu : pas de faux repli sur la même IP) ; banc_boot cas 6 « aucun evenement mais MQTT connecte » OK
- [x] Après `serveur.delaiRepliWifi` secondes sans lien (défaut 60) : `Wifi 1` sans redémarrage, log `erreur` — preuve : banc_boot cas 6, pas de `Wifi 1` à 59 s, un seul à 61 s, `voieReseau` inchangée ; `delaiRepliWifi` 0 = jamais
- [x] Pendant le repli : `surveilleWifi` réactivé (sans Wi-Fi non plus : redémarrage au bout de `timerRebootSansWifi`, l'Ethernet est retenté) — preuve : garde `voieReseau == "ethernet" && !self.repliWifi` ; banc_boot « repli sans Wi-Fi non plus : redemarrage par surveilleWifi » OK, rouge sous mutant m1
- [x] Retour : lien stable depuis 30 s -> `Restart 1`, en fermant la fenêtre où deux interfaces portent la même IP (voir A4) — preuve : banc_boot « pas de redemarrage avant 30 s », « Restart 1 apres 30 s », « lien instable, pas de redemarrage » OK
- [x] Bancs : banc_boot avec témoins et mutants : démarrage sans câble, câble retiré, coupure brève sans repli, retour, double panne, aucune réécriture de `voieReseau` — preuve : banc_boot.py OK (cas 1-8, 11 contrôles de repli au cas 6, voie Wi-Fi au cas 7) ; 7 mutants (garde de surveilleWifi, admission MQTT, délai de retour, ethLien vrai/faux, drapeau de repli, garde de voie) tous rouges ; verifie_berry 0 erreur 0 avertissement ; banc_demarrage : 5 cartes OK, P4 rouge AVANT ce travail (référence du 2026-11-05, `pagesGraphiques` ajouté par `403850d73` le 2026-11-07)
- [ ] Essais sur carte : câble débranché puis rebranché (l'événement `ETH#Connected` vient-il en IP fixe ?), état des relais au retour (`PowerOnState`), point d'accès actif (redémarrage en plus par `xdrv_58`)

## Améliorations restantes
- [ ] [projet] `tasks/plans/cave-s3-waveshare.md` : l'essai de `VoieReseau` à réception de la carte reprend les essais de ce plan

## Vérification
Berry : bancs ci-dessus, `verifie_berry.py`, `relecteur-berry`. Firmware : compilation par la page Build seulement. NAPT, câble et mDNS : seule la carte le prouve.
