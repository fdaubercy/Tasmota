# Diagnostic UDP maître P4 <-> esclave S3 (cuve) — 2026-10-17

> **Suite donnée (même jour) — le corps de ce rapport est conservé tel qu'écrit le matin.**
> - **C1 à C6 appliqués, flashés et validés sur les cartes** (P4 COM4, cuve COM12), dans les deux modes,
>   Range Extender ET Wi-Fi classique (décision de l'utilisateur : ce sont deux vrais modes d'usage, donc
>   C3 complet + C4 + C5). Commits `37276e5dc` (C1, C2, C6) et `8a9a18333` (C3, C4, C5).
> - **C3 complété** (`197af338b`) : en plus de son point d'accès, le maître émet son multicast par sa STA,
>   mais **seulement si sa découverte connaît un esclave joignable par la box** (même groupTopic,
>   `Online`, IP du /24 de la STA hors du /24 de l'AP) ; sans point d'accès ni tel esclave, rien n'est
>   émis (`>>>> Non emis`). Mesuré : multicast P4 -> cuve en Wi-Fi classique 11/12 reçu par la box
>   (0 avant), 2/2 par l'AP en Range Extender.
> - Les résultats des essais sont dans `PROTOCOLE_MODBUS.md` §9 et `tasks/reprise-chantier-modbus-grenier.md`.
> - `tasks/correctif-udp-interface-2026-10-17.diff` (cité ci-dessous comme `correctif_berry.diff`) est
>   **historique** : le code de référence est `data/fs/udpFonctions.be`.
> - C7 codé le 2026-10-21 (`udpFonctions.ouvreEcoute` / `secoursSansMqtt`, `every_second` de `controleUDP.be`,
>   banc `test_discovery.be` section 21) : à flasher sur les 3 cartes. C8 et C9 restent refusés.

Analyse et propositions seulement : **rien n'a été modifié dans le dépôt**, rien n'a été flashé,
aucune configuration de carte n'a été changée. Les mesures du 2026-10-17 04:39-04:44 ont été
faites par le testeur UDP (http://127.0.0.1:7400, COM4 = P4, COM12 = cuve) avec des commandes
de lecture et des sockets Berry de test (ports 2996-2998), toutes refermées ensuite (liste au §6).

Légende : **PROUVÉ-M** = prouvé par une mesure de ce jour ; **PROUVÉ-C** = prouvé par lecture
du code (chemin et ligne) ; **PROBABLE** = cohérent avec le code et les mesures, pas isolé seul ;
**SUPPOSÉ** = hypothèse non vérifiée.

Sources lwIP lues : `~/.platformio/packages/framework-espidf/components/lwip/` (ESP-IDF 5.5.4,
même branche que les bibliothèques précompilées d'Arduino 3.3.x ; les options sont, elles, lues
dans le `sdkconfig` et le `lwipopts.h` précompilés de `framework-arduinoespressif32/tools/esp32-arduino-libs/esp32s3|esp32p4/`).
Les deux cibles ont les mêmes options lwIP : `CONFIG_LWIP_IPV4_NAPT=y` (donc `IP_NAPT 1`,
lwipopts.h:219-224), `CONFIG_LWIP_IP_FORWARD=y`, `CONFIG_LWIP_NETIF_LOOPBACK=y` (+ `LWIP_HAVE_LOOPIF 1`,
lwipopts.h:794-801), `CONFIG_LWIP_SO_REUSE=y`, `CONFIG_LWIP_SO_REUSE_RXTOALL=y`, `LWIP_IGMP 1`,
`LWIP_HOOK_IP4_ROUTE_SRC ip4_route_src_hook` (lwipopts.h:1354), `CONFIG_LWIP_IPV6=y`.
P4 : `CONFIG_ESP_HOSTED_ENABLED=y`, coprocesseur ESP32-C6 en SDIO.

---

## 1. Les mécanismes en jeu (ce que fait la pile, ligne par ligne)

1. **Choix de l'interface de sortie (unicast)** — `udp.c:596` : `netif = ip_route(&pcb->local_ip, dst)`.
   `ip4_route_src` (ip4.c:130-141) appelle d'abord le crochet ESP-IDF
   `ip4_route_src_hook` (`port/hooks/lwip_default_hooks.c:122-142`) : **si la socket est liée à une
   adresse précise, l'interface qui porte cette adresse est choisie**. Sinon `ip4_route` (ip4.c:153-228)
   prend **la première interface de `netif_list` dont le sous-réseau contient la destination**
   (ip4.c:171-178), puis à défaut `netif_default`.
2. **Ordre de `netif_list`** — `netif_add` insère **en tête** (netif.c:437-438). ESP-IDF appelle
   `netif_add` au démarrage de l'interface (`esp_netif_start_api` -> `esp_netif_lwip_add`,
   esp_netif_lwip.c:1173) et `netif_remove` à l'arrêt (:913-919). Tasmota ne démarre le point
   d'accès Range Extender qu'**après** la connexion de la STA (`xdrv_58_range_extender.ino:499`,
   « Setup only if WiFi in STA only mode », dans `FUNC_EVERY_SECOND`). L'AP est donc ajouté après
   la STA, et se retrouve **avant** elle dans la liste.
3. **Interface par défaut** — `route_prio` STA = 100, AP = 10 (`esp_netif_defaults.h:54/68`) :
   `netif_default` = STA. Tasmota n'appelle pas `setDefault` (aucune occurrence dans `tasmota/`).
4. **Pas de rebouclage vers sa propre adresse** — ip4.c:1061-1079 : avec `ESP_LWIP && IP_NAPT`,
   le bloc « Packet to self » est compilé **hors** (« doesn't work for external wifi interfaces »).
   Un envoi vers une adresse locale (autre que 127.0.0.1, servie par l'interface `lo`) part sur le
   réseau.
5. **Réception multi-interfaces** — ip4.c:616-636 : un datagramme unicast est accepté s'il vise
   l'adresse de N'IMPORTE QUELLE interface (modèle « hôte faible »). Multicast (ip4.c:592-607) :
   accepté seulement si **l'interface d'arrivée** a rejoint le groupe.
6. **Jonction IGMP** — `NetworkUDP::beginMulticast` (NetworkUdp.cpp:100-143) ouvre une socket
   AF_INET liée à 0.0.0.0:port et rejoint le groupe avec `imr_interface = INADDR_ANY` (:131) ;
   `igmp_joingroup` (igmp.c:455-480) ne joint que les interfaces **présentes à cet instant**, et
   `netif_remove` libère les groupes de l'interface (`igmp_stop`, netif.c:794).
7. **Socket d'écoute à double pile** — `be_udp_begin_ntv` (`xdrv_52_3_berry_udp.ino:45-55`) :
   `begin("")` -> `IPAddress(IPv6)` = `::` -> socket AF_INET6 liée à `[::]:port`, qui reçoit aussi
   l'IPv4. `begin("a.b.c.d")` -> socket AF_INET liée à cette adresse.
8. **Partage d'un port** — `SO_REUSEADDR` posé à chaque `begin` (NetworkUdp.cpp:57). En unicast,
   lwIP remet le datagramme à la **première** socket non connectée qui correspond (udp.c:267), en
   préférant une adresse précise à `::`/0.0.0.0 (udp.c:279-284) ; `udp_bind` met la socket en tête
   de liste (udp.c:298). `SO_REUSE_RXTOALL` ne copie qu'en broadcast/multicast (udp.c:377-400).
9. **Pas de transfert du multicast par le NAPT** — `ip4_canforward` (ip4.c:255-257) refuse tout
   multicast : un push 224.3.0.1 d'un esclave ne sort jamais de 192.168.4.0/24 (mémoire du 2026-10-10).
10. **Ouverture des sockets d'écoute** — sur `System#Boot` (`udpFonctions.be:415-422`), qui n'est
    levé qu'à la **première connexion MQTT** (`xdrv_02_9_mqtt.ino:1487`, ou `MqttReconnect`
    :1523-1525 si MQTT est désactivé). Broker injoignable au démarrage = **aucune socket d'écoute
    UDP** (PROUVÉ-C, non mesuré).

---

## 2. Mesures du 2026-10-17 04:39-04:44 (ce rapport)

Cartes : P4 uptime 8 h 45, cuve uptime 1 h 19 (Status 11). Cuve : `Status 5` = 192.168.4.2/24,
passerelle 192.168.4.1 ; `RgxState` = ON ; `RgxSSId` = CAPTEURS-CUVE-GATEWAY, **IPAddress
192.168.4.1, Subnetmask 255.255.255.0**. P4 : 192.168.0.43/24, passerelle 192.168.0.254.

| # | Essai | Résultat |
|---|---|---|
| A | Cuve, socket neuve `begin("",0)` -> 192.168.4.1:2997 ; P4 socket neuve `begin("",2997)` | **non reçu** (`LU-A nil`) |
| B | Cuve, socket neuve **liée à sa STA** `begin("192.168.4.2",0)` -> 192.168.4.1:2997 | **REÇU** par le P4, de 192.168.4.2:53558 |
| C | Cuve, socket `begin("",0)` -> **192.168.0.43**:2997 (IP STA du P4) | **REÇU**, de 192.168.4.2:53557 |
| I | Cuve, framework `ReglageUDP envoiUniCast 192.168.4.1 TESTUDP-I` | `ENVOI OK`, **rien côté P4** |
| J/K | Cuve, socket `begin("",0)` -> 192.168.4.1:2996 et 127.0.0.1:2996, écoute locale `begin("",2996)` | 127.0.0.1 reçu ; 192.168.4.1 **non rebouclé** |
| D/E | Cuve -> 224.3.0.1:2998 (liée STA, puis toutes interfaces) ; P4 `begin_multicast("224.3.0.1",2998)` neuve | **les deux REÇUS** de 192.168.4.2 |
| F, M | Cuve, framework `ReglageUDP envoiMultiCast TESTUDP-F` (224.3.0.1:4000) | **REÇU** par l'écoute du framework du P4 (`LIRE_UDP ... MultiCast reçues de '192.168.4.2' sur le port 4000`), aussi après fermeture des sockets de test (M) |
| G | P4, framework `ReglageUDP envoiMultiCast TESTUDP-G` | **REÇU** par la cuve (`... MultiCast reçues de '192.168.4.1' sur le port 61817`) |
| H1-H5 | P4, framework `ReglageUDP envoiUniCast 192.168.4.2 TESTUDP-Hn`, 5 envois à 0,4 s | **5/5 reçus** par la cuve |

Remarque : le P4 journalise `MBS: MBR Driver receive error 11` toutes les ~10 s pendant toute la
séance (pont ModBus) — hors périmètre, à noter.

---

## 3. Matrice attendue / constatée

Notations : P4 STA = 192.168.0.43 (box), P4 AP = 192.168.4.1/24 ; cuve STA = 192.168.4.2 (RE) ou
192.168.0.x (Wi-Fi classique) ; cuve AP = 192.168.4.1/24 (RgxState ON, réglage Tasmota en flash :
`controleRangeExtender` n'est PAS chargé sur la cuve ni le rideau, `autoexec.be:98` / `:93`, donc
le bloc `serveur.rangeExtender.AP` de leur persist n'est appliqué par aucun script).

### 3.1 Range Extender, esclave SANS AP propre (cas « normal »)

| Sens | Type | Doit marcher par | Code actuel | Verdict |
|---|---|---|---|---|
| P4 -> esclave | unicast | P4 : route 192.168.4.0/24 -> AP ; source 192.168.4.1 | `begin("",2000)`+`send(ip,2000)` (udpFonctions.be:479, :495) | OK (H1-H5) |
| P4 -> esclave | multicast | socket liée à 192.168.4.1 -> crochet -> AP | `begin(ipDestinataire="192.168.4.1",0)`+`send(224.3.0.1,4000)` (:485, :501) | OK (G) |
| esclave -> P4 | unicast | 192.168.4.1 dans le sous-réseau de la STA -> STA | `begin("",2000)` | OK attendu (pas d'autre interface en 192.168.4.0/24) |
| esclave -> P4 | multicast | 224.x hors sous-réseau -> `netif_default` = STA | `begin_multicast`+`send_multicast` (:488, :504) | OK attendu ; le P4 doit avoir joint le groupe sur son AP |

### 3.2 Range Extender, esclave AVEC son propre AP en 192.168.4.1/24 (configuration actuelle cuve et rideau)

| Sens | Type | Ce qui se passe | Verdict |
|---|---|---|---|
| P4 -> cuve | unicast | P4 sort par son AP ; la cuve reçoit sur sa STA (adresse de la STA) | **OK** (H1-H5) |
| P4 -> cuve | multicast | idem, la STA de la cuve a joint le groupe | **OK** (G) |
| cuve -> P4 | unicast, socket « toutes interfaces » (framework, E1 `repondUDP`) | 192.168.4.1 est dans le sous-réseau de l'AP de la cuve, 1er de la liste -> sortie par l'AP de la cuve, ARP pour sa propre adresse, perdu ; pas de rebouclage (§1.4) | **ÉCHEC** (A, I, J) |
| cuve -> P4 | unicast, socket **liée à la STA** | crochet -> STA -> P4 | **OK** (B) |
| cuve -> P4 | unicast vers **192.168.0.43** | pas de sous-réseau local -> `netif_default` STA -> passerelle 192.168.4.1 sur la STA ; le P4 accepte (hôte faible, ip4.c:616-636) | **OK** (C) |
| cuve -> P4 | multicast | `netif_default` = STA | **OK** (D, E, F) |

Conséquence directe : **toute réponse UDP d'un esclave à `Info.remote_ip` = 192.168.4.1 est
perdue** (E1 : `modbusFonctions.repondUDP`, `modbusFonctions.be:1546-1555` -> `envoiUDP("UniCast",
"192.168.4.1", ...)`). Le TCP n'est pas touché : une connexion acceptée est liée à l'adresse de
destination du SYN (192.168.4.2), le crochet choisit alors la STA (déduit du code, non mesuré).

### 3.3 Wi-Fi classique (esclave sur la box, `rangeExtender.activation` = OFF) — essai 2, NON mesuré

| Sens | Type | Doit marcher par | Code actuel | Attendu |
|---|---|---|---|---|
| P4 -> esclave | unicast | P4 : 192.168.0.x -> STA (box) | inchangé | OK |
| P4 -> esclave | multicast | il faudrait sortir par la STA du P4 | P4 lié à **192.168.4.1** -> sort par son AP seulement (:485) | **ÉCHEC par construction** : Timestamp, ipMaitre et `ModbusUDP` multicast (`modbusFonctions.be:1533`) n'atteignent pas un esclave sur la box |
| esclave -> P4 | unicast | 192.168.0.43 dans le sous-réseau de la STA ; l'AP de la cuve (s'il reste ON) est en 192.168.4.0/24, aucun chevauchement | inchangé | OK (y compris la réponse E1 à 192.168.0.43) |
| esclave -> P4 | multicast | STA -> box -> STA du P4 (si la box relaie le multicast entre clients Wi-Fi : **inconnu**) | **aucun envoi** : branches conditionnées à `activation == "ON"` (:483-490, :499-506) ; `ReglageUDP envoiMultiCast` n'appelle même pas envoiUDP (:233-240), sans erreur | **rien ne part** (ImAlive et push absents ; fiche par MQTT) |

`ReglageGlobal ModeConnexion` ne touche pas `RgxState` (`globalFonctions.be:643-704`) : l'AP de
la cuve reste probablement allumé en Wi-Fi classique, en 192.168.4.1/24 — sans effet sur l'UDP
puisque sa STA est alors en 192.168.0.x (PROBABLE, à lire par `RgxState` pendant l'essai 2).

### 3.4 Ce que disent les commentaires du code

- `controleUDP.be:16-19` : « l'esclave ne peut envoyer qu'en UniCast s'il est connecté par le
  RangeExtender ; en MultiCast sur un réseau wifi classique ». **Le code fait l'inverse** :
  multicast seulement si `activation == "ON"` (udpFonctions.be:483, :499), et l'unicast est
  identique dans les deux modes. Les mesures montrent que le multicast marche en RE (D-G) et que
  c'est l'unicast esclave -> maître qui casse, à cause du chevauchement et non du mode.
- `controleUDP.be:27` (« communications uniquement sur l'IP Wifi principale, pas 10.99.0.1 ») et
  `:32-33` (« port 3000 (MultiCast) ») sont périmés (4000 en réalité, `controleUDP.be:184`).

---

## 4. Causes racines

### Prouvées

**R1 — Chevauchement de sous-réseau sur l'esclave (cuve, et rideau par la même config)**.
L'AP de la cuve porte 192.168.4.1/24 (RgxSSId), sa STA 192.168.4.2/24. Un envoi depuis une
socket non liée vers 192.168.4.1 sort par l'AP de la cuve et se perd. Preuves : mesures A/I
(échec) vs B (socket liée à la STA : reçu) et C (vers 192.168.0.43 : reçu) ; J (pas de
rebouclage) ; code §1.1, §1.2, §1.4. L'hypothèse principale de l'orchestrateur est **confirmée**,
avec une précision : les envois ne « restent » pas chez la cuve (pas de rebouclage, ip4.c:1061),
ils partent sur son AP, où personne ne répond à l'ARP.
Mécanisme exact de l'ordre AP-avant-STA : PROBABLE (déduit de netif.c:437 et xdrv_58:499) ;
le résultat, lui, est mesuré. Indice non concluant : la cuve affiche `IP6Local ...%st2`
(interface STA numéro 2, donc redémarrée au moins une fois avant la création de l'AP).

**R2 — Le multicast du maître ne sort que par son AP** (udpFonctions.be:485 + crochet §1.1) :
PROUVÉ-C. Sans effet en RE (G), bloquant en Wi-Fi classique (§3.3).

**R3 — Aucun multicast esclave hors Range Extender** (udpFonctions.be:483-490, :499-506 ;
`reglageUDP` :233-240) : PROUVÉ-C, déjà consigné au §9 « Unicast / multicast ».

**R4 — Message UDP d'un seul mot = exception dans `lireUDP`** (`params[1]`, udpFonctions.be:592) :
PROUVÉ-C et par le banc (§18 du banc étendu : `index_error` sur l'ancien code). Un datagramme
« TESTUDP » sans espace lève dans `every_100ms`.

### Probables / latentes

**L1 — Socket d'émission liée au port d'écoute 2000** (udpFonctions.be:479) : pendant sa vie, elle
est en tête de `udp_pcbs` (udp.c:298) et capte un datagramme unicast entrant (udp.c:267), perdu à
sa fermeture. Fenêtre de quelques ms ; non observé. L'hypothèse « le port 2000 empêche
l'émission » est, elle, **écartée** (mesure du 2026-10-17 03:5x, consignée au §9).

**L2 — Écoute multicast du maître ouverte avant son AP** (§1.6 + System#Boot après MQTT, AP créé
dans la seconde qui suit la connexion Wi-Fi) : course possible au démarrage. **Écartée pour la
session de boot en cours** (F, M : l'écoute du P4 reçoit bien le 4000 sur son AP). Peut revenir à
un autre démarrage : à vérifier par l'essai F après chaque reboot du P4.

**L3 — Pas de socket d'écoute si MQTT ne se connecte pas** (§1.10) : PROUVÉ-C, non mesuré.

**L4 — `192.168.4.1` écrit en dur** dans 4 appels (udpFonctions.be:238, :327, :331 ;
modbusFonctions.be:1533) : juste aujourd'hui, faux le jour où l'AP du maître change d'adresse.

### Écartées ou non reproduites

- **Échecs P4 -> cuve unicast de 03:52-03:53** : non reproduits (H1-H5 : 5/5). Cause non établie.
  Piste la plus simple : biais du log série (cuve démarrée vers 03:23 d'après son uptime ->
  `SERIALLOG_TIMER` = 600 s, `tasmota.h:218` -> muette dès ~03:33, ce que le §9 note déjà) —
  SUPPOSÉ, car l'orchestrateur indique un log actif à ce moment-là. Autres pistes (ARP, veille
  modem, esp-hosted) : SUPPOSÉ, aucune trace.
- **Multicast dans les deux sens « jamais reçu »** (mesure 4 du matin) : **non reproduit** ce
  jour (D, E, F, G, M tous reçus). Même biais de log probable ; ou L2 lors d'un boot antérieur.
- **esp-hosted (P4) qui bloquerait l'AP ou le multicast** : écarté pour ce boot (G, H, F).

---

## 5. Corrections proposées

Toutes demandent l'accord de l'utilisateur : C1-C5 modifient `data/fs/udpFonctions.be` (fichier
de `data/fs`) ; C7-C8 touchent la configuration du point d'accès. `udpFonctions` est **solidifié**
dans tous les env : rebuild complet + flash des 3 cartes (P4, cuve, rideau) après
`solidifie_et_compile_berry.py` (non lancé ici : il écrit dans `lib/libesp32/berry_custom`).

| # | Correction (fichier) | Bénéfice | Risque | Réversible |
|---|---|---|---|---|
| **C1** | Esclave : socket d'émission **liée à l'IP de sa STA** (`tasmota.wifi()["ip"]`), unicast et multicast (envoiUDP) | Débloque esclave -> maître malgré R1 sans toucher à l'AP ; débloque E1 (`repondUDP`) ; mesuré en B | Un esclave ne peut plus joindre en UDP un client de SON propre AP (aucun aujourd'hui ; impossible de toute façon avec le chevauchement) ; STA changée entre lecture et envoi -> 2e essai sur toutes les interfaces | Oui (reflash) |
| **C2** | Port source **aléatoire** (0) pour toutes les émissions | Supprime L1 | Le port source vu par le destinataire n'est plus 2000 : aucun lecteur ne s'en sert (`remote_port` n'est que journalisé, udpFonctions.be:531, controleUDP.be:124) | Oui |
| **C3** | Maître : multicast lié à l'IP de l'AP **lue dans le persist** (`serveur.rangeExtender.AP.IPAddress`) ; sans AP, à sa STA | Supprime L4 dans envoiUDP ; un maître sans AP émet enfin | Aucun en RE (même adresse aujourd'hui) | Oui |
| **C4** | Esclave : multicast **aussi en Wi-Fi classique** (condition `activation` retirée ; `ReglageUDP envoiMultiCast` sans condition) | ImAlive et push peuvent atteindre le P4 par la box (si elle relaie le multicast) et le PC (`ecoute_udp.py`) | Trafic multicast sur le Wi-Fi maison (une trame par push / 5 min d'ImAlive) ; d'autres cartes de la maison qui écoutent 224.3.0.1:4000 le décodent (elles filtrent sur leur topic : `lireUDP` :610) | Oui |
| **C5** | Maître : réponse à ImAlive (`Timestamp`, `ipMaitre`) en **unicast à `IPAddress` de la fiche**, multicast par l'AP en repli si la fiche n'a pas d'IP | Marche en RE et en Wi-Fi classique ; trame acquittée par la radio 802.11 | Chaque esclave reçoit SA réponse (avant : tous recevaient celle de chacun) — sans conséquence, chacun envoie ImAlive toutes les 5 min | Oui |
| **C6** | `lireUDP` : message d'un seul mot sans exception | Supprime R4 | Aucun | Oui |
| C7 (codé le 2026-10-21) | Ouvrir les sockets d'écoute aussi sans MQTT (ex. au 1er `every_second` réseau monté si `System#Boot` n'est pas venu) | Supprime L3 | Double ouverture à garder (déjà ouverte -> ne rien faire) | Oui |
| C8 (config, option) | Sous-réseau propre à l'AP de chaque esclave (cuve 192.168.5.1/24, rideau 192.168.6.1/24) par `RgxAddress` | Supprime R1 à la source, rend possible le chaînage (aujourd'hui cassé : le DHCP de l'AP de la cuve distribuerait 192.168.4.2, sa propre IP STA) | **Refusé par l'utilisateur le 2026-10-03** (`lessons.md`, 2 entrées : « on annule B », ne plus proposer de toucher à l'AP). Rappelé ici seulement parce que la mesure B/A établit maintenant la cause ; C1 suffit sans lui. Commande `Rgx*` avec argument : interdite à l'agent ; sur la cuve et le rideau, le persist `AP` n'est appliqué par aucun script (`controleRangeExtender` non chargé). Impacts : NAPT (redirections `RgxPort` du P4 inchangées : elles visent la STA de l'esclave), DHCP de l'AP esclave, discovery (`routagePort` inchangé, `IPAddress` = STA inchangée), `routageMaitreIP`/`ipMaitre` inchangés | Oui (RgxAddress 192.168.4.1) |
| C9 (config, option) | `RgxState 0` sur la cuve et le rideau | Supprime R1 | Contredit le choix « maître ET esclaves peuvent être point d'accès » (`lessons.md` 2026-10-03) ; redémarrage | Oui |

**Recommandation** : C1 + C2 + C6 (sûrs, ciblés, C1 prouvé par la mesure B) ; C3 + C5 pour
l'essai 2 (Wi-Fi classique) ; C4 à trancher par l'utilisateur (c'est la question « push en
multicast ou en unicast », laissée « hors périmètre » au §9). Ni C8 ni C9 ne sont nécessaires.

Alternative à C1, plus étroite : remplacer, côté esclave, une destination égale à l'adresse de
son AP par `serveur.rangeExtender.ipMaitre` (192.168.0.43, mesure C). Moins bonne : dépend d'un
`ipMaitre` à jour, et ne corrige que ce cas.

Le diff `correctif_berry.diff` contient C1-C6 (C7 non codé) et la section 18 du banc.

### Ce qui a été testé, et comment

- Copie complète de `data/fs` dans `scratchpad/diag_udp/copie/fs` (correctif) et
  `scratchpad/diag_udp/ref/fs` (référence intacte).
- `test_discovery.be` du dépôt sur la référence : **143/143 OK**.
- Banc étendu `scratchpad/diag_udp/banc/test_discovery.be` (= banc du dépôt + bouchon
  `tasmota.wifi()` + bouchon `udp` qui note l'adresse liée, la destination et le port source +
  **section 18**, 17 tests) : correctif **160/160 OK** ; référence (témoin) **13 échecs**, tous
  dans la section 18 (liaison STA, port 0, multicast Wi-Fi classique, AP du persist, ImAlive
  unicast, message d'un mot). Les 4 autres passent aussi sur la référence : 3 comportements
  conservés exprès (STA inconnue sans exception, interface imposée par l'appelant, repli
  multicast par l'AP pour une fiche sans IP) et le compte « 1 envoi » du refus de liaison, qui
  n'est discriminant qu'avec le test de journal qui le suit (échoue sur la référence).
- Sans le bouchon `tasmota.wifi()`, le banc du dépôt échoue sur le correctif (5 échecs,
  `attribute_error ... 'wifi'`) : le diff ajoute donc ce bouchon au banc du dépôt.
- `banc_test_modbus.py` sur la copie : **238/238 OK** (il bouchonne udpFonctions ; vérifie
  seulement que rien d'autre n'a bougé).
- `git apply --check` du diff sur l'arbre de travail actuel : OK. `git status` identique à
  celui du début de session.
- **Non testé** : la solidification et la compilation du `.h` (script non lancé), le
  comportement réel du correctif sur carte (seule la primitive est mesurée : B, C, D).

---

## 6. Commandes envoyées aux cartes (2026-10-17, 04:39-04:44)

Toutes par `POST /cmd` du testeur. Lectures : `Status 5` (P4, cuve), `Status 11` (P4, cuve),
`RgxState` et `RgxSSId` sans argument (cuve ; le mot de passe de la réponse est masqué partout).
Envois de test : cuve `ReglageUDP envoiUniCast 192.168.4.1 TESTUDP-I framework-uni`, cuve
`ReglageUDP envoiMultiCast TESTUDP-F framework-4000` et `... TESTUDP-M apres-fermeture`, P4
`ReglageUDP envoiMultiCast TESTUDP-G maitre-mc`, P4 `ReglageUDP envoiUniCast 192.168.4.2
TESTUDP-H1..H5 uni`. Sockets Berry (`Br`) : P4 `global.tp` (2997), `global.tm`
(multicast 2998) ; cuve `global.tu` (port 0), `global.tv` (lié à 192.168.4.2, port 0),
`global.tl` (2996) ; envois TESTUDP-A..E, J, K vers 2996-2998 ; **toutes fermées** (`close()`
puis `nil`, « FERME-P4 », « FERME-CUVE » à 04:44:05). Aucune commande de configuration.

---

## 7. Plan de tests réels

Préalable aux deux essais : testeur ouvert sur COM4 (P4) et COM12 (cuve) ; il réapplique le
niveau de log série à l'ouverture (`SERIALLOG_TIMER`). Les lignes attendues sont celles du code
corrigé (`ENVOI_MSG_UDP: Données ... par '<interface>' ...`).

### Étape 0 — Avant tout flash : rejouer le diagnostic (5 min, sans risque)

1. Cuve `RgxSSId` -> noter `IPAddress`/`Subnetmask` (192.168.4.1 / 255.255.255.0 attendus).
2. Mesures A et B du §2 (sockets 2997, refermées) : A non reçu, B reçu. Si A est reçu, la
   cuve a perdu son AP ou changé d'adresse : refaire l'analyse avant de flasher.
3. Essai F (multicast cuve -> P4 framework) après chaque redémarrage du P4 : surveille L2.

### Essai 1 — Range Extender (P4 + cuve flashés avec C1-C6 ; P4 avec E1 ou non, au choix)

| Pas | Commande | Attendu côté émetteur | Attendu côté récepteur |
|---|---|---|---|
| 1 | cuve `ReglageUDP envoiUniCast 192.168.4.1 TESTUDP-1 cuve-uni` | `ENVOI_MSG_UDP: Données UniCast envoyées vers '192.168.4.1:2000' par '192.168.4.2' >>>> TESTUDP-1 cuve-uni >>>> OK` | P4 `LIRE_UDP: Données UDP UniCast reçues de '192.168.4.2' sur le port <aléatoire>` puis `LIRE_UDP: msg = TESTUDP-1 cuve-uni` |
| 2 | cuve `ReglageUDP envoiMultiCast TESTUDP-2 cuve-mc` | `... MultiCast envoyées vers '224.3.0.1:4000' par '192.168.4.2' ... OK` | P4 `... MultiCast reçues de '192.168.4.2' sur le port <aléatoire>` |
| 3 | P4 `ReglageUDP envoiUniCast 192.168.4.2 TESTUDP-3 p4-uni` | `... vers '192.168.4.2:2000' par 'toutes interfaces' ... OK` | cuve `... UniCast reçues de '192.168.4.1' ...` |
| 4 | P4 `ReglageUDP envoiMultiCast TESTUDP-4 p4-mc` | `... vers '224.3.0.1:4000' par '192.168.4.1' ... OK` | cuve `... MultiCast reçues de '192.168.4.1' ...` |
| 5 | **E1** : P4 `ReglageModbus envoiMessageUDP 192.168.4.2 ModbusUDP 17 020100E00001FC0F` | P4 `... UniCast envoyées vers '192.168.4.2:2000' ...` | cuve `REPOND_UDP: reponse a 192.168.4.1 : ModbusUDP 17 0201010051CC` (ou `...01900C` si POWER1 ON) puis `ENVOI_MSG_UDP: ... vers '192.168.4.1:2000' par '192.168.4.2' ... OK` ; **P4** `LIRE_UDP: ... reçues de '192.168.4.2'` et `LIRE_UDP: msg = ModbusUDP 17 0201010051CC` ; sniffeur RS485 : rien à cet instant |
| 6 | cuve `ReglageUDP forceEnvoiParams ON` | multicast `tele/jardin/cuve/ReglageUDP ImAlive {...}` par '192.168.4.2' | P4 : `LIRE_UDP ... MultiCast` ; si `typeReglageHeure` = UDP : P4 `... UniCast envoyées vers '192.168.4.2:2000' ... Timestamp ...` puis `... ipMaitre ...` ; cuve `LIRE_UDP ... UniCast reçues de '192.168.4.1'` (2 fois) |
| 7 | Témoin négatif : cuve, socket non liée `Br u=udp() u.begin("",0) u.send("192.168.4.1",2997,...)` vers une écoute P4 2997 | — | **non reçu** (prouve que le pas 1 marche par la liaison STA, pas par hasard) ; fermer les sockets |
| 8 | Rafale : 10 x pas 3, puis 10 x pas 1, à 2 s | — | 10/10 de chaque côté ; sinon noter l'heure et le `Status 11` des deux cartes |

### Essai 2 — Wi-Fi classique (cuve sur MAISON par `ReglageGlobal ModeConnexion WifiClassique`, à lancer par l'utilisateur)

Lire d'abord sur la cuve : `Status 5` (IP 192.168.0.x notée X), `RgxState` (ON probable).

| Pas | Commande | Attendu |
|---|---|---|
| 1 | cuve `ReglageUDP envoiUniCast 192.168.0.43 TESTUDP-5` | cuve `... par 'X' ... OK` ; P4 `... UniCast reçues de 'X'` |
| 2 | P4 `ReglageUDP envoiUniCast X TESTUDP-6` | cuve `... reçues de '192.168.0.43'` |
| 3 | **E1** : P4 `ReglageModbus envoiMessageUDP X ModbusUDP 18 020100E00001FC0F` | cuve `REPOND_UDP: reponse a 192.168.0.43 : ModbusUDP 18 ...` ; P4 `LIRE_UDP ... reçues de 'X'` |
| 4 | cuve `ReglageUDP envoiMultiCast TESTUDP-7` (C4) | cuve `... vers '224.3.0.1:4000' par 'X' ... OK` (avant C4 : aucune ligne `ENVOI_MSG_UDP`) ; P4 : reçu **seulement si la box relaie le multicast** — résultat à consigner tel quel ; le PC (`ecoute_udp.py`) doit le voir aussi |
| 5 | P4 `ReglageUDP envoiMultiCast TESTUDP-8` | P4 `... par '192.168.4.1'` ; cuve : **rien** (attendu : le multicast du maître reste sur son AP) |
| 6 | cuve `ReglageUDP forceEnvoiParams ON` | si 4 passe : ImAlive au P4, puis réponse **unicast** (C5) `Timestamp`/`ipMaitre` reçue par la cuve de '192.168.0.43' ; sinon, fiche par MQTT seulement |
| 7 | Retour : `ReglageGlobal ModeConnexion RangeExtender` (utilisateur) puis rejouer l'essai 1 pas 1-5 |
