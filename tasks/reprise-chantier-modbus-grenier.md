# Reprise — Chantier ModBus du grenier (carte 16 relais + esclaves Tasmota)

> État au **2026-09-29** (encadré ci-dessous) ; le reste du document date du 2026-07-24.
> À lire en entier avant de reprendre.
> Document de reprise : le mettre à jour, ne pas en créer un second.
> Complément technique : `outils_docs/PROTOCOLE_MODBUS.md` §8 et §9.

---

# ⇒ MISE À JOUR DU 2026-09-29 — ce qui a changé depuis juillet

- **La branche `chantier-modbus-grenier` est fusionnée dans `development` et publiée sur
  `origin`** (vérifié : `d464c53db` est ancêtre de `origin/development`). Les mentions
  « aucun poussé » plus bas sont périmées.
- **2026-10-04 : branche `chantier-modbus-grenier` SUPPRIMÉE** (locale seulement, jamais
  poussée, aucun commit absent de `development` ; elle pointait sur `1400cea57`). Le chantier
  se poursuit sur `development`. Les mentions de la branche plus bas sont historiques.
- **`modbusFonctions.be` a encore bougé** (+174 lignes de diff depuis `d464c53db`), par le
  travail de septembre sur la cave : solidification généralisée, correctifs des globales des
  modules solidifiés (`f5efddf26`, `ecc73348f`). Les 3 garage n'ont **toujours jamais été
  flashés** avec ce code.
- **Build lancé par l'utilisateur le 2026-09-29** (`platformio_override.ini`) : P4 garage,
  cuve, rideau et cave S3. La grille « flasher et observer » ci-dessous reste LA prochaine
  action, à exécuter sur ce firmware.
- **Globales au boot — vérifiées statiquement le 2026-09-29, pas encore sur carte garage.**
  Audit des références par nom global dans chaque module solidifié, croisé avec l'autoexec de
  chaque env (témoin négatif OK : retirer `configGlobal` fait bien apparaître le manque).
  Résultat : **aucune globale manquante** sur P4, cuve, rideau, S3 garage, cave, grenier.
  Fournies par l'autoexec (niveau fichier) : `configGlobal`, `diversFonctions`,
  `gestionFileFolder`, `globalFonctions`, `webFonctions`, `modbusFonctions` ; par les `init()`
  des drivers : `udpFonctions`/`tcpFonctions`/`discoveryFonctions`/`rangeExtenderFonctions`
  (`controleXxx_init`), `controleGeneral`. **À confirmer au 1er boot** de chaque carte :
  `Br global.contains("modbusFonctions")` etc. — aucun `undeclared` ne doit apparaître au log.
- **✅ CORRIGÉ le 2026-09-29 — autoexec garage alignés sur la cave** (4 fichiers : P4,
  cuve, rideau, S3 serveur). `compileModule` et `import controleXxx` des services réseau
  **déjà actifs** passent sous `if serveur[…].find("activation", "OFF") == "ON"` ; ajout de
  l'avertissement « ne jamais compiler autoexec en `.bec` ». **Aucun service ajouté** :
  TCP et RangeExtender, commentés sur P4/cuve/rideau, le restent — bien que **tous les
  persist garage les aient à `ON`** (décommenter les activerait : choix à faire
  explicitement, pas par alignement). Comportement inchangé aujourd'hui (tout est `ON`) ;
  la garde ne mord que si un service passe à `OFF`. Syntaxe vérifiée au `berry.exe` avec
  témoin négatif.
- `compileModule` sur un module solidifié dont le `.be` est exclu du FS est **inoffensif**
  (`gestionFileFolder.be:388` : fichier absent → `return true`, rien d'autre).
- **Synchronisation esclaves → maître : options A + B mises en place le 2026-09-29**
  (détail : `outils_docs/PROTOCOLE_MODBUS.md` §9, « Mise en oeuvre retenue »). Commits
  `5ce683ec4` (0x10 standard), `852aac0c5` (push B émission), `1556d6b37` (réception),
  `e776309a2` (relevé A), `66c75a320` (`typeComm.UDP = ON`). Avant eux, 3 correctifs
  `4e49352aa`, `1d1cf336f`, `700b3510d`. Banc : **36 PASS, 0 bug connu**. Jamais sur bus réel.
  **Les firmwares compilés le 2026-09-29 au matin ne contiennent RIEN de tout cela :
  rebuild complet des 3 garage obligatoire** (tout est solidifié).
- **À ajouter à la grille d'observation** (log niveau 4) :
  | À vérifier | Chaîne de log |
  |---|---|
  | Relevé A armé (maître) | `Releve des esclaves arme (toutes les 30 s)` |
  | Relevé A actif | `MODBUS_TASMOTA_SLAVE_RELEVE: 2 demande(s)` (config actuelle : thermomètre cuve + interrupteurs rideau) |
  | Push B émis (esclave, sur changement d'interrupteur) | `POUSSE_ETAT: registre 160 = [255] -> maitre (UDP)` |
  | Push B reçu et appliqué (maître) | `Réception de l'état de l'interrupteur n°1: ON` sans requête en vol |
  | Push B n'acquitte rien | `APPARIE_REPONSE: trame automatique (telemetrie)` — n'apparaît que si une requête était en vol à l'arrivée du push |
  Les logs `RELEVE` et `POUSSE_ETAT` exigent le `debug` à `ON` (TasmotaSlaveModBus côté maître, ModBus côté esclave).
- **✅ Fait le 2026-09-29 (après A + B), le reste de la synchro** — détail dans
  `PROTOCOLE_MODBUS.md` §9 « Compléments » :
  `e2ee294a9` `typeComm.TCP = OFF` sur P4 et cuve (TCP cassé, hors chemin utile) ;
  `8c42ad056` l'esclave exécutait `Power<StartAddress>` (Power256) : **aucun relai d'esclave
  ne basculait** — corrigé ; `45d432257` relais d'esclaves commandé/constaté (lecture 0x01,
  log ECART, l'écho 0x06 n'écrase plus l'état commandé) ; `9e6331cf8` chien de garde par
  esclave (> 3 × 30 s sans contact → `etatConstate = "inconnu"`) ; `4532f12ec` `seq` sur le
  push ; `b5f23f7e5` **la cuve et le rideau ne chargeaient pas `controleModbus`** (commenté dans
  l'autoexec, exclu du LittleFS depuis `04dbda1a7`) : port série jamais ouvert, esclaves sourds
  au RS485 — seul le push UDP passait ; désormais solidifié et importé. Banc : **76 PASS**, témoins négatifs sur l'ancien code. Jamais sur bus réel ; **rebuild
  complet des 3 garage obligatoire**.
- **À ajouter à la grille d'observation** (compléments) :
  | À vérifier | Chaîne de log |
  |---|---|
  | Relais rideau relus (maître) | `MODBUS_TASMOTA_SLAVE_RELEVE: 6 demande(s)` (cuve : thermomètre + analogique ; rideau : 2 interrupteurs + 2 relais ; WS2812 non relues) |
  | Commande relai exécutée (esclave rideau) | le relai **bascule physiquement** ; log `EXECUTE_CMD_MODBUS: Commande le 1` |
  | Constat relai (maître) | `Etat constate du relai n°2: ON` ; **aucun** `MODBUS_TASMOTA_SLAVE_ECART` en régime établi |
  | Chien de garde | débrancher le rideau → `CHIEN_DE_GARDE: esclave TasmotaSlaveModBus2 (ID=3) muet` sous ~90-120 s ; rebrancher → `repond de nouveau` |
  | `seq` | `POUSSE_ETAT: ... (UDP, seq 1)` au 1er push après boot ; `ACCEPTE_SEQ: ... redemarre` côté maître après reboot d'un esclave |
  Les chaînes `CHIEN_DE_GARDE` et `ECART` passent par `log()` direct : visibles même `debug` OFF.

---

# ⇒ SI TU REPRENDS À FROID, LIS CES 30 LIGNES D'ABORD

**Le titre de ce document dit « grenier ». Le travail porte sur les 3 modules GARAGE.**
Ne pas repartir sur le grenier : c'est l'erreur commise le 2026-07-24 (332 lignes écrites
au mauvais endroit, annulées — voir `tasks/lessons.md`). Les 3 cibles sont
`tasmota32p4-garage-serveur-modbus`, `tasmota32s3-garage-capteurs-cuve-modbus`,
`tasmota32s3-garage-rideau-garage-modbus`.

> **ETAT AU 2026-10-17 SOIR — LIRE EN PREMIER.** ModBus FILAIRE P4 <-> cuve : **grille de l'audit (§6)
> VALIDEE**, tests 1 a 7, par le testeur (onglet « Grille ModBus ») - **decision de l'utilisateur : « tous
> les tests sont bons »**. Reserves connues, acceptees : test 6 rejoue sans manipulation fiable (la reception
> du P4 se coupait au moindre mouvement des cables : faux contact a fixer) ; 7d KO sur la seule fiche du
> rideau (ancien firmware). UDP maitre <-> esclave : C1-C6 valides dans les deux modes (detail plus bas).
> **E2 + E3 (commandes sans fil, cote P4) CODES le 2026-10-17, NON FLASHES** - detail et verification :
> `outils_docs/PROTOCOLE_MODBUS.md` §9, bloc « E2 + E3 ». Inertes tant qu'aucun esclave n'annonce UDP.
> **Reste a faire, dans l'ordre :** (1) fixer le cablage de reception du P4 ; (2) REBUILD COMPLET + flash du
> P4 (modbusFonctions, udpFonctions, controleModbus solidifies ; cuve et rideau aussi pour udpFonctions) ;
> (3) observer E2 : logs `ROUTE_ESCLAVE:` (voie Serial, IP de la cuve) - rien d'autre ne doit changer ;
> **(2) et (3) FAITS le 2026-10-17 soir** : P4 flashe (CfgHolder 1507), `ROUTE_ESCLAVE: esclave d'ID=2 : voie
> Serial, IP 192.168.4.2 (fiche)` ; etat `routesAnnoncees` = {2: Serial|192.168.4.2, 3: Serial|192.168.4.3}
> (la ligne du 3 a manque a l'historique du pont, l'etat fait foi) ; aucun envoi UDP, aucune erreur. Coupure du
> filaire 22:31:37 -> 22:39:30 (timeouts sur tous les esclaves, plus rien au sniffeur) = encore le faux contact
> du P4 : (1) reste a FIXER pour de bon avant (4) ;
> **(1) FAIT le 2026-10-18** : cablage repris, puis 62 min sans coupure (12:00-13:02) : sniffeur 126/126 (id 1)
> et 375/376 (id 2, derniere en vol), 0 sans reponse, receptions du P4 par MQTT identiques, aucun trou > 5 min.
> Plan suivi : `tasks/plans/modbus-garage.md` (A4 a 100 %). Prochaine action : (4).
> (4) activer E3 : `ReglageModbus VoieCommandes UDP` SUR LA CUVE, puis repasser la grille (attendu :
> `POMPE_QUEUE: envoi UDP`, plus rien de la cuve sur le RS485 au sniffeur ; retour : `... Serial`) ;
> (5) flasher le rideau (id 3, muet, fiche perimee, sans E1), lui passer la grille, puis E4
> (`VoieCommandes UDP` sur le rideau) ; (6) E5 : debrancher le cable, decision de l'utilisateur apres
> observation ; (7) C7 et le minuteur SerialLog de `logFonctions.appliqueProfil`, sur accord de l'utilisateur.
> **Minuteur SerialLog : REFUSE le 2026-10-21** (« laissons tasmota par defaut ») - ne pas le reproposer ;
> le log serie se coupe 600 s apres chaque demarrage, suivre une carte au-dela par MQTT / web / syslog.
> **ETAT AU 2026-10-21 MATIN** : (4) FAIT (cuve en UDP, `voieCommandes: "UDP"` aussi dans le persist du depot :
> un flash LittleFS l'avait remise en Serial) ; grille en UDP validee avec 2 reserves (5k : publication UDP
> avec `StartAddress: 0`, a trancher ; 7d : fiche perimee du rideau). Faux contact du P4 RETOMBE apres son
> flash du 20, cables repositionnes ~06:12 ; A4 re-prouvee 06:15-07:18 (carte relais 125/125, 0 sans reponse).
> (6) E5 FAIT POUR LA CUVE : cable debranche ~06:45, 06:46-07:49 VALIDE (375 receptions UDP, aucun trou,
> 0 abandon ; carte relais 126/126). **Prochaine action : (5) le rideau** ; puis C7 sur accord.
> **Capteurs de la cuve : PAS un defaut (tranche le 2026-10-17).** 2147483647 (registre 4704, niveau via
> ADS1115) et null (registre 1312, DS18B20 sur GPIO18) sont les SENTINELLES « pas de mesure »
> (`modbusFonctions.be:2801`) : l'ADS1115 et la sonde ne sont PAS branches (confirme par l'utilisateur ;
> `I2CScan` = « No devices found », pas de DS18B20 dans `Status 10`). Rien a corriger avant leur montage ;
> une fois branches : `I2CScan` doit montrer 0x48, `Status 10` le DS18B20 (pull-up 4,7 kohm sur GPIO18).

> **2026-10-17 — commandes ModBus sans fil (UDP), etat :** E1 code (cuve flashee avec, P4 non) ;
> `ReglageGlobal ModeConnexion` code (aucune carte flashee avec). Essai reel 1 : P4 -> cuve OK,
> cuve -> P4 perdu. Cause prouvee : AP de l'esclave en 192.168.4.1/24 (choix de l'utilisateur, NE PAS
> y toucher) -> envoi par la mauvaise interface ; corrige dans `udpFonctions.envoiUDP` (C1/C2/C6,
> socket liee a la STA de l'esclave), commite (37276e5dc), rebuild fait et cartes flashees le
> 2026-10-17 (avec la synchro de l'amont). **Essai 1 (Range Extender) VALIDE le 2026-10-17 10:30-10:40**
> par `outils_pc/testeur_udp.py` (P4 COM4, cuve COM12) : 6/6 RECU (unicast et multicast dans les deux
> sens, E1 `ModbusUDP` aller-retour, ImAlive) + 10/10 cuve -> P4 unicast (0,33-0,49 s), source
> 192.168.4.2 a port aleatoire : C1 et C2 prouves sur les vraies cartes. **Decide le 2026-10-17 : C3 COMPLET + C4 + C5**, car les deux modes (Range Extender
> ET Wi-Fi classique) sont de vrais modes d'usage. C3 complet = `ipAP()` lu dans le persist ET les 4
> `"192.168.4.1"` en dur passes a `""` (udpFonctions.be:238, :327, :331, modbusFonctions.be:1533 :
> une IP passee par l'appelant IMPOSE l'interface). **C3 complet + C4 + C5 CODES le 2026-10-17**
> (non flashes) : `udpFonctions.ipAP()`/`estIPv4()`, reponse ImAlive en unicast a l'IP de la fiche
> (multicast si IPv4 invalide), multicast esclave hors Range Extender, type d'envoi inconnu journalise.
> Verifie : `test_discovery.be` 170/170 (section 19 neuve, temoins : ancien code + 3 mutations echouent),
> `banc_test_modbus.be` OK, `solidifie_et_compile_berry.py` OK sur udpFonctions et modbusFonctions.
> **Flashes le 2026-10-17 et VALIDES sur les cartes (P4 COM4, cuve COM12)** :
> - essai 1 rejoue (Range Extender, 12:34-12:36) : 6/6 RECU + 11/11 cuve -> P4 unicast ; C5 : Timestamp et
>   ipMaitre partent en UniCast vers 192.168.4.2 et sont recus par la cuve ;
> - essai 2 (Wi-Fi classique, cuve en 192.168.0.6, 12:38-12:41) : unicast dans les deux sens RECU, E1 RECU
>   (reponse par la box), ImAlive RECU, C5 : Timestamp/ipMaitre en UniCast vers 192.168.0.6 recus ;
>   **multicast cuve -> P4 RECU : LA BOX RELAIE LE MULTICAST entre clients Wi-Fi** (C4 utile) ;
>   multicast P4 -> cuve EMIS NON RECU = limite connue (le maitre emet par son seul point d'acces).
> **Tranche le 2026-10-17 (regle de l'utilisateur)** : le multicast du maitre ne part par sa STA que si
> sa decouverte connait un esclave joignable par la box ; sinon il n'y est pas emis. Critere : fiche
> `esclaveN` d'une autre MAC, MEME groupTopic, `lwt` Online, IP dans le /24 de la STA et hors du /24 de
> l'AP. Multicast par l'AP INCHANGE. **CODE le 2026-10-17, NON solidifie, NON flashe** :
> `udpFonctions.interfacesMulticastMaitre()` / `esclavesBox()` (cache : table relue si sa date change ou
> apres 30 s) / `reseau24()` ; sans AP ni esclave box : log `>>>> Non emis` (lu par le testeur).
> Changement de comportement : maitre SANS point d'acces et sans esclave decouvert = plus de multicast
> (avant : par sa STA). Verifie : `test_discovery.be` 195/195 (section 20 neuve ; temoin ancien code :
> 9 echecs), `banc_test_modbus` 238/238, `test_testeur_udp` 155/155, `verifie_berry` 52/0.
> `solidifie_et_compile_berry.py` OK sur udpFonctions (16 closures, 0 anonyme, .h compile).
> **Flashe sur le P4 et VALIDE le 2026-10-17** :
> - essai 2 rejoue (Wi-Fi classique, 16:35-16:37) : ImAlive RECU, puis multicast P4 -> cuve **11/12
>   RECU** (avant : 0), source vue 192.168.0.43 = STA du P4 relayee par la box ; 1 perte = multicast
>   Wi-Fi sans acquittement ; cuve -> P4 multicast RECU ;
> - contre-essai (retour en Range Extender, 16:48-16:49) : `interfacesMulticastMaitre()` = ['192.168.4.1']
>   (regle desactivee), ImAlive RECU, multicast P4 -> cuve 2/2 RECU (source 192.168.4.1).
> **Cuve muette sur son port serie (2026-10-17, analyse corrigee)** : ce n'etait PAS la reouverture du
> testeur (elle avait marche : Status 5 relu a 16:38:21). COM12 est un pont **CH343** (pas l'USB natif).
> La cuve n'a plus ecrit une ligne de 16:39:11 (en plein echange ModBus, logs `detail`) a 16:47:09, alors
> qu'elle tournait (ImAlive UDP recu par le P4 a 16:44:26 ; P4 : « esclave 2, muet » en ModBus a 16:44:17) ;
> fermer/rouvrir le port (16:46:15) n'a RIEN change ; seul le reset de 16:47:09 (« Vbat power on reset »,
> bouton RST ?) l'a retablie. Pas SERIALLOG_TIMER (aucun « Serial logging disabled », 56 s apres le boot).
> **Cause sur la carte NON etablie** (syslog eteint : pas de trace). Piste : TasmotaSerial peut prendre
> l'UART0 de la console quand UART1/UART2 sont pris (`TasmotaSerial.cpp:168`) - non prouve. **Si ca se
> reproduit, AVANT le reset** : console web de la cuve (ou `cmnd/jardin/cuve/SerialLog` en MQTT) pour voir si
> elle logue encore, et lancer le serveur syslog. **Testeur corrige** : carte « muette » apres 10 s sans
> reponse a une commande (note, pastille rouge, relance du log serie), essais signales « aucune ligne recue
> de la carte » ; banc `test_testeur_udp_muette.py`.
> **ModBus filaire : le P4 ne recoit plus RIEN (diagnostic du 2026-10-17, 20:06-20:13)**. Sur le bus (sniffeur
> COM5, 19200) : carte relais id1 5/5 reponses (~2 ms), cuve id2 4/4 reponses valides (CRC OK, ~141 ms),
> rideau id3 0/4. Au meme moment, le P4 (pont 7000) : `MBR Recv timed out` + `Driver receive error 11` pour
> les TROIS esclaves ; journal du testeur 10:29-13:20 : cuve 121 reponses emises, P4 0 `ModbusReceived`.
> L'emission du P4 marche (les esclaves repondent a ses requetes) : c'est sa RECEPTION qui est coupee.
> **Le P4 recevait encore le 2026-10-12 jusqu'a 06:55** (syslog : 365 `ModbusReceived` id1, 1083 id2).
> Ecarte : template du P4 lu en direct (GPIO4 = 9440 ModBr Rx, GPIO5 = 9408 ModBr Tx, codes verifies dans
> `tasmota_template.h`), `ModbusBaudrate 19200`, `ModbusSerialConfig 8N1`, aucun `serial()` Berry sur le
> maitre (id 0), pilotes TasmotaSerial/TasmotaModbus/xdrv_63 et plateforme inchanges depuis `196b4ff3d`
> (`pins_arduino.h` du P4 : GPIO 4/5 non concernes). **Cause la plus probable : materielle, cote P4** -
> sortie RO de son transceiver -> GPIO4 (fil, connecteur), ou recepteur desactive (/RE). A verifier a la main
> AVANT tout changement de code ; test simple : debrancher le convertisseur du sniffeur et voir si le P4 recoit.
> **Re-test 20:18-20:19 : le P4 RECOIT de nouveau** (36 `ModbusReceived` en 70 s : carte relais id1 a chaque
> sondage /30 s, cuve id2 0x03 et 0x04) ; seuls timeouts : rideau id3. Aucun code ni reglage modifie entre
> les deux mesures (logiciel). **Cause confirmee par l'utilisateur : un cable debranche** sur les liaisons du
> P4, retouchees entre les deux mesures. Lecon : timeouts sur TOUS les esclaves + reponses visibles au sniffeur
> = verifier d'abord le cablage de reception du maitre.
> **Grille ModBus (testeur, cuve) le 2026-10-17, 20:21-20:44** : tests 1 a 5 VALIDES (5g « ECHEC » = faux echec
> du testeur : le P4 a ecrit `ACCEPTE_SEQ: esclave d'ID=2 redemarre (seq 1 apres 8)` a 20:33:52.965, AVANT
> l'etape 5f ; la cuve pousse son seq 1 des son demarrage). Test 6 : chien de garde OK (ID=2 muet apres 113 s),
> 6d ECHEC reel : pendant la manipulation, le P4 a perdu la RECEPTION de TOUS les esclaves (carte relais muette
> 20:38-20:43 alors que le sniffeur la voit repondre 82/82) ; cuve revue a 20:43:06, ~4 min apres le
> rebranchement. => faux contact probable sur le cablage de reception du P4 : a fixer, puis rejouer le test 6.
> Testeur corrige ensuite (banc 223/223, 4 mutations detectees) : 2b compte les requetes (en-tete
> `executeCmdModbus`) et non les lignes ; retour en AUTO PROUVE (releve avec mode 0 puis `RubanEsclave1` =
> AUTO, etapes 4j-4l / 5j-5l) ; 5g cherche depuis le Restart (option `depuis`) ; bouton de consigne qui
> restait affiche (reponse HTTP perimee : `version` + `repond()` attend la consigne retiree) ; decompte de
> l'etape qui attend sa preuve.
> **Test 7 (21:02)** : AP, ImAlive, fiche de la cuve, page /discovery OK. 7d d'abord faux echec (Br de 579 octets
> tronque par le P4, `Len 443` -> syntax_error) : le testeur envoie desormais les lignes longues par blocs de 64
> octets. Rejoue : `GRILLE_T7 KO DCB4D91B117C/esclave3 groupTopic=nil` = fiche du RIDEAU (Offline, ancien
> firmware sans groupTopic) : attendu tant que le rideau n'est pas reflashe.

## LA PROCHAINE ACTION — flasher et observer

> **2026-09-30 : la grille à suivre est désormais UNIQUE, dans
> `outils_docs/AUDIT_MODBUS_2026-09-29.md` section 6** (préparation, boot, régime normal,
> actions, pannes). Les grilles ci-dessous sont historiques.

**14 commits sont posés sur `chantier-modbus-grenier` (de `6a79ce3f4` à `367fedc94`),
fusionnés et publiés depuis (voir la mise à jour du 2026-09-29), et AUCUN n'a jamais été
exercé sur un bus réel.** Trois changent un
comportement observable, et un cron va désormais émettre une trame toutes les 30 s.

Continuer à coder avant d'observer rendrait tout échec indécidable (règle 7 de
`lessons.md`, tombée 2× le 2026-07-15 : toujours un témoin).

**Rebuild complet obligatoire** des 3 environnements garage : `modbusFonctions.be` est
désormais solidifié, il ne monte plus sur le LittleFS — un simple `uploadfs` ne suffit pas.

Puis, avec `ReglageLog profil debug` et `ReglageLog modbus detail` (ex-`ReglageGlobal logLevel 4`,
supprime le 2026-10-04 : voir la charte des logs dans CLAUDE.md). **Grille actionnable — chaînes de log exactes,
extraites du code le 2026-07-24 :**

| À vérifier | Quand | Chaîne de log à chercher (ou absence attendue) |
|---|---|---|
| Sondage 0x03 aboutit | auto : +15 s au boot, puis /30 s | ✅ doit apparaître : `MODBUS_RECUPERE_REPONSE_CONN16CHANNEL: Type de msg Modbus` |
| **Cavalier M0** (question n°1) | à la 1ʳᵉ réponse | `ECART voie %i (relai n°%i) : commande=…, constate=…` — **16 écarts d'un coup → M0 connecté**, poser `"cavalierM0":"connecte"` dans `drivers.ModBus.environnement.Conn16channels` du persist |
| Appariement pas trop strict | marche normale | ❌ ne doit **PAS** apparaître : `APPARIE_REPONSE: reponse hors-sequence rejetee` |
| Télémétrie préservée | à chaque push capteur | `APPARIE_REPONSE: trame automatique (telemetrie)` = normal ; les capteurs remontent quand même |
| Doublon TCP disparu | à chaque commande relais | ❌ ne doit **plus** apparaître vers la carte 16 : `ENVOI_MSG_MODBUS_TCP: Aucun client TCP` |
| Chien de garde (test : débrancher le RS485 ~90 s) | après 3×30 s | `MODBUS_CONN_16CH_CHIEN_DE_GARDE: … etats constates passes a 'inconnu'` |

⚠️ **L'émission** du sondage 0x03 est **silencieuse** (le code 0x03 n'a pas de libellé dans
la table de log de `envoiMsgModbus`). Ne pas chercher « j'envoie 0x03 » : c'est la
**réponse** (`MODBUS_RECUPERE_REPONSE_CONN16CHANNEL`) qui prouve l'aller-retour.

Test manuel immédiat, sans attendre les 30 s :
`ModBusSend {"deviceaddress":1,"functioncode":3,"startaddress":1,"type":"uint16","count":16}`

Vérifié le 2026-07-24 : le driver de la carte se **chargera** bien sur le P4
(`ModBus.activation=ON`, `Conn16channel1=ON`, 16 relais virtuels → garde `nbIOActives`
franchie), donc le cron de sondage s'armera.

## CE QUI RESTE À FAIRE, PAR ORDRE

1. **Flasher + observer** (ci-dessus) — utilisateur.
2. **`seq` / instantanés** — bloqué par une décision : la télémétrie est *différentielle*,
   il faut la convertir en *instantané* avant que `seq` ait un sens. Voir « Ce qui reste de
   la phase 4 » plus bas.
3. **Phase 3 (scission)** — à rediscuter, **ne pas lancer telle quelle** : sa frontière ne
   tient pas sur le garage (`lireMsgModbus` n'est pas purement esclave), son gain y tombe
   de 730 à ~120 lignes, et `modbusFonctions.be` étant maintenant solidifié, le découper
   obligerait à revoir les listes `custom_berry_solidify` et à re-vérifier chaque morceau.
4. **Défauts repérés, non corrigés** (hors périmètre, volontairement laissés) :
   - ✅ **CORRIGÉ le 2026-07-24 (`prepareTrame`, quantité de lecture doublée).** Le bloc
     d'allocation du tampon d'écriture faisait `nbRegistres *= 2` même pour une trame sans
     données, et les branchements 0x03/0x04 réutilisaient la variable comme quantité (16 →
     32). Corrigé par une garde `writeDataSize > 0` : une commande de lecture (`Values=[]`)
     saute le bloc, les écritures/réponses (données présentes) sont inchangées. Trouvé,
     corrigé et verrouillé par `banc_test_modbus` (TDD : le test échouait avant, passe
     après ; la trame de sondage vaut désormais le vecteur exact de la doc, CRC compris).
   - `modbusFonctions.be:286-292` — `clients[id]` est créé **avant** que `id` ne soit lu
     dans le JSON : le tableau se peuple avec un décalage d'une itération.
   - `modbusFonctions.be:608` — l'**UDP** porte le même défaut de symétrie que le TCP
     (corrigé, lui). Laissé car `typeComm.UDP = OFF` sur les 3 garage.
   - `modbusFonctions.be:1380` — `# TODO` du type `"bit"` dans l'empaquetage de `prepareTrame`.
   - Commentaire du bloc **grenier** dans `platformio_tasmota_cenv.ini` : voir la note
     « À traiter quand le ModBus du grenier sera activé » — sa condition n'est PAS remplie.

---

## En une phrase

Le grenier (`tasmota32s3-grenier`) doit piloter une **carte 16 relais RS485 ModBus RTU**
et **deux esclaves Tasmota** (cuve id 2, rideau id 3) sur le même bus. Le matériel et
l'architecture sont **tranchés** ; le code n'a **pas encore été touché**. La file FIFO
du maître, écrite le 2026-07-16, **n'a jamais été flashée** — c'est le verrou n°1.

> **Mise à jour du 2026-07-24** : le paragraphe ci-dessus décrit le **grenier**, resté
> intact. Le travail a basculé sur les **3 modules garage**, dont le code ModBus a lui
> beaucoup bougé (14 commits, ~460 lignes). Voir l'encadré en tête de document.

---

## Phase 0 du GRENIER — en sommeil, à ne pas confondre avec la prochaine action

> ⚠️ **Cette section ne s'applique PAS au travail en cours.** Elle décrit la mise en
> service du **grenier**, gelée depuis le 2026-07-24 : le chantier porte sur les 3 modules
> garage, dont le bus tourne déjà (la phase 0 y est sans objet). Conservée telle quelle
> pour le jour où le grenier sera monté — les cinq verrous restent exacts et vérifiés.
>
> Un **sixième verrou** a été découvert le 2026-07-24 et n'est pas dans la liste :
> `bouton1` du grenier occupe **GPIO 4**, que le RX ModBus doit prendre. Décision prise :
> le déplacer sur **GPIO 21** (recâblage physique), comme cela a été fait sur le maître P4.

**Phase 0 : valider la file FIFO sur banc, code strictement inchangé.**

Ne rien modifier avant : sans un comportement de référence observé, un échec ultérieur
devient indécidable (règle 7 de `lessons.md` — toujours un témoin).

Cinq verrous à lever avant le banc, **aucun n'est dans le Berry** :

1. **`USE_MODBUS` est commenté** pour le grenier — `tasmota/user_config_override.h:1937`.
   Sans lui, pas de `USE_MODBUS_BRIDGE`, donc pas de `ModBusSend`, donc `pompeQueue`
   échoue sur tout. Référence qui marche : le garage, ligne 2077. **Rebuild obligatoire.**
2. **Quatre bascules dans `data/etage2/tasmota32s3-grenier/_persist.json`** (tout est à
   `"OFF"`) : `drivers.ModBus.activation`, `typeComm.Serial`, `pinsModBus.RX/TX`
   (GPIO 4/5), `Conn16channels.Conn16channel1`.
3. **Garde `nbIOActives`** — `modBus_Conn16channels.be:324` ne charge le driver que si
   les relais *actifs* dépassent les relais *réels*. Déclarer les 16 relais virtuels
   **avant** que le driver ne puisse exister.
4. **Débit** : persist à 19200, carte d'usine à 9600. Aligner l'un sur l'autre
   (voir `PROTOCOLE_MODBUS.md` §8 — effectif seulement après coupure d'alimentation).
5. **Adresse esclave** : carte en id 1, esclaves Tasmota en 2 et 3. L'adressage de la
   carte exige **un seul module sur le bus** — le faire avant de câbler le reste.

Ce que la phase 0 doit prouver, avec `ReglageLog profil debug` et `ReglageLog modbus detail` :
- les envois partent **dans l'ordre**, un seul en vol ;
- `termineEnVol(true)` sur chaque réponse ;
- un timeout provoqué (débrancher le RS485) → 3 tentatives → abandon loggé ;
- le sondage d'état fonctionne :
  `ModBusSend {"deviceaddress":1,"functioncode":3,"startaddress":1,"type":"uint16","count":16}`

---

## Décisions tranchées (ne pas re-litiger)

| Sujet | Décision | Raison |
|---|---|---|
| Transport | **RS485 / ModBus RTU** | Distance grenier ↔ RDC. L'I²C ne se déporte pas (~1 m). Le nombre de relais n'était PAS le critère : MCP23xxx et xdrv_94 plafonnent tous deux à 32 sorties. |
| Câble | Belden 3106A (1 paire 22 AWG + fil de masse, 120 Ω) ; **Cat6 F/UTP 23 AWG rigide** accepté (100 Ω, écart sans effet à 19200 bauds) | Voir §8 pour le brochage |
| Driver natif `xdrv_94_modbus_relay` | **Écarté** | Il monopolise son propre UART (`GPIO_MODBUSRELAY_*` ≠ `GPIO_MBR_*`) : incompatible avec un bus multipoint carte + esclaves. Non plus déclaré dans `my_user_config.h`, jeu d'instructions 0x0F ≠ 0x06 de notre carte. |
| Réécriture du Berry | **Non — on part des fichiers existants** | 2 952 lignes contenant du savoir payé comptant (contournement timer P4, map registres, appariement). Et la file FIFO n'est pas validée : réécrire supprimerait le témoin. |
| Organisation | **La convention maison, appliquée plus loin** : une paire par rôle, pas une pour tout le protocole | Un fichier unique serait pire : perte de la règle des 500 lignes et du seul levier RAM (ne pas charger ce qu'on n'exécute pas). |
| MBAP / ModBus TCP standard | **Non** | Le push esclave→maître n'existe pas en ModBus standard : le MBAP n'apporterait que l'interopérabilité tierce, besoin absent. Le `Transaction Id` est sans objet en un-seul-en-vol. Dialecte texte maison assumé. |
| Télémétrie via MQTT | **Écartée** (mentionnée, non retenue) | Ajouterait une dépendance au broker (point de panne unique) et un second modèle de données. À reconsidérer si le broker devient central. |

---

## Le découpage cible

```
data/fs/
  modbusFonctions.be          socle : log, config, réglages, dispatch      ~590 l.
  modbusTrameFonctions.be     prepareTrame + crc16modbus                   ~270 l.
  modbusMaitreFonctions.be    queue, pompeQueue, termineEnVol, appariement ~120 l.
  modbusEsclaveFonctions.be   lireMsgModbus, executeCmdModbus, decrypteMSG ~460 l.
  controleModbus.be           le driver, inchangé                          322 l.
```

Chargement conditionnel depuis `autoexec.be`, sur `drivers.ModBus.id` :
- **Grenier** (maître, série) → socle + maître → **730 lignes jamais chargées**
- **Cuve / rideau** (esclaves) → socle + trame + esclave
- **Garage** (maître, TCP/UDP) → socle + trame + maître

Le nom `modbusFonctions` reste celui du socle : tous les `import modbusFonctions`
existants continuent de fonctionner, la scission est invisible aux appelants.

---

## Le plan en phases

> ⚠️ **Le plan ci-dessous a été écrit pour le GRENIER.** Depuis le 2026-07-24, le travail
> porte sur les **3 modules garage** (P4 maître, cuve, rideau). Plusieurs conclusions ne
> s'y transposent pas — voir « Ce qui change sur le garage » plus bas.

| Phase | Quoi | Qui |
|---|---|---|
| **0** | Valider la file FIFO + sondage 0x03 — série seul, **code inchangé** | Utilisateur (flash) — *sans objet sur le garage, dont le bus tourne déjà* |
| **1** | Code mort (~75 l.) + branches vides 0x01/0x03/0x0F de `prepareTrame` | ✅ **fait le 2026-07-24** (commits `c34cc558a` → `73adea014`) |
| **1 bis** | Rejet strict `apparieReponse` + code fonction télémétrie en liste blanche | ✅ **fait le 2026-07-24** (`9e828fc7a`) |
| **2** | Index inverse `{adresse: {registre: cible}}` + table d'inversion Open/Close | ✅ **fait le 2026-07-24** (`90647b94d`) — carte 16 relais seulement, voir ci-dessous |
| **3** | Scission par rôle | Claude |
| **4** | Instantanés : `seq`, commandé/constaté, chien de garde, réconciliation au boot | 🔶 **partielle, 2026-07-24** (`297dc4257`) — tout sauf `seq`, voir ci-dessous |

**L'ordre n'est pas négociable sur deux points** : la phase 0 précède tout (sinon plus de
témoin) ; la 1 bis précède l'activation du push (sinon on injecte une course dans un
système non validé).

Un commit par phase → chaque phase est un point de retour indépendant.

---

## Ce qui change sur le garage (établi le 2026-07-24, preuves à l'appui)

- **`typeComm.TCP = ON`** sur le **maître P4** et sur la **cuve** (`OFF` sur le rideau).
  Donc `prepareTrame` **est** sur leur chemin d'exécution — la conclusion « la phase 1
  n'est pas bloquante », vraie pour un maître série pur, **ne s'y transpose pas**.
- **Le transport TCP n'avait jamais pu émettre** : `envoiMsgModbusTCP` déclarait 3
  paramètres pour 2 passés par ses 5 appelants. Berry n'impose pas l'arité
  (`be_vm.c:1403-1405`), le décalage se propageait en silence jusqu'à un
  `Trame.get()` sur une string. Corrigé (`c34cc558a`).
- **Le TCP est désormais réservé au sens esclave → maître.** Série et TCP n'étaient pas
  exclusifs : une fois l'arité corrigée, chaque commande serait partie **deux fois**, et
  chaque ordre vers la carte 16 relais (sans IP) aurait produit une erreur. Corrigé
  (`366d5d530`). L'**UDP porte le même défaut**, laissé en l'état car `OFF` partout.
- **Phase 3 (scission) : la frontière ne tient pas sur le garage.** `lireMsgModbus` est
  classée « esclave » dans le découpage, mais le **maître** l'utilise aussi par la voie
  TCP (`tcpFonctions.be:199`, appel non gardé par le rôle). L'appliquer telle quelle
  reviendrait à la reconcevoir. Gain réel : ~120 l. sur les esclaves, faible sur le P4,
  contre 730 l. annoncées pour le grenier. **À rediscuter avant de lancer la phase 3.**
- **Défaut annexe repéré, non corrigé** : dans la création des clients TCP
  (`modbusFonctions.be:286-292`), `clients[id]` est créé **avant** que `id` ne soit lu
  dans le JSON — le tableau se peuple avec un décalage d'une itération.

## Ce qui reste de la phase 4 : le compteur `seq` — CADRAGE (2026-07-24)

Le reste de la phase 4 est en place pour la carte 16 relais : sondage périodique (T = 30 s),
réconciliation au boot (+15 s), séparation `etat` / `etatConstate`, chien de garde à 3×T.
Seul `seq` manque. Ce cadrage sert à le **décider**, pas à le coder à l'aveugle.

### Ce que fait `seq`, et ce qu'il présuppose

`seq` est un compteur monotone qui protège un flux d'**instantanés** contre le **désordre
et la perte UDP** : l'esclave l'incrémente à chaque changement, le maître **rejette tout
instantané de `seq <= au dernier reçu`**. Un `seq` retombé à 0 signale un reboot d'esclave.

Il ne vaut donc quelque chose que si **deux préalables** sont réunis. Aucun ne l'est
aujourd'hui — d'où « à décider », pas « à enchaîner ».

**Préalable 1 — le transport doit être UDP.** `seq` protège du réordonnancement. Or la
télémétrie actuelle part en **TCP** : les 4 sites (`globalFonctions.be:200/242/286/381`)
sont tous gardés par `if typeComm.TCP == "ON"`, et `typeComm.UDP = OFF` sur les 3 garage.
**Sur TCP, l'ordre et la livraison sont garantis — `seq` ne protège de rien.** Le §9
recommande justement de basculer la télémétrie en UDP (pour qu'un push ne puisse jamais
encombrer la file série), et c'est *cette bascule* qui crée le besoin de `seq`.

**Préalable 2 — le push doit être un instantané, pas un différentiel.** Aujourd'hui chaque
site émet **un datagramme par device qui change** : `Count=1`, une valeur, `StartAddress =
type + id - 1`. Codes `0x02|0x80` (entrées discrètes : boutons/interrupteurs/capteurs,
sites 190/232/276) et `0x04|0x80` (analogique, site 371). C'est un **différentiel** : « ce
device a changé ». Un `seq` par snapshot ne s'applique pas à des différentiels — rejeter un
différentiel « en retard » perdrait une transition définitivement.

### Le vrai chantier (dont `seq` n'est que le 3ᵉ tiers)

1. **Regrouper** les N devices d'une catégorie en **une** trame instantané (`Values` =
   tableau de N états), au lieu d'un datagramme par device. Un snapshot par catégorie
   (relais/positions ; analogique), aux rythmes du §9 (30 s / 5 min).
2. **Basculer** ces envois de TCP vers UDP (activer `typeComm.UDP`, garder le serveur/récep-
   tion UDP séparé pour ne pas toucher `enVol` — le §9 « blocage » est déjà corrigé côté
   réception en `297dc4257`).
3. **`seq`** : un champ dans la trame maison (à placer, p. ex. en tête de `Values`) ;
   `decrypteMSG` l'extrait ; une table `dernierSeq[DeviceAddress]` côté maître ; rejet si
   `seq <= dernierSeq`. `decrypteMSG` porte déjà le drapeau `Automatique` (`:1150-1155`),
   point d'ancrage naturel.

### Coût et rupture

~100-150 lignes, réparties sur `globalFonctions.be` (restructurer les 4 sites en
constructeurs de snapshot), `decrypteMSG` (extraire `seq`) et un nouveau contrôle de rejet
côté maître. **C'est un changement de format de trame** : maître et esclaves doivent être
reflashés **ensemble** — pas de déploiement partiel possible sur le bus.

### La question à trancher AVANT de coder

`seq` n'a de sens qu'avec la bascule télémétrie → UDP. **Cette bascule est-elle voulue ?**
Sur TCP, ordonné et fiable, le dispositif actuel converge déjà. Le §9 préfère l'UDP pour
protéger la file série — mais c'est un arbitrage (fiabilité TCP vs découplage UDP), pas une
évidence. Tant qu'il n'est pas tranché, écrire `seq` serait du code mort.

## Le code mort identifié (phase 1) — ✅ traité le 2026-07-24

- **`attenteReponse` n'est lu par personne** : écrit en `modbusFonctions.be:36, 427, 435,
  449, 466` et `controleModbus.be:117` — **aucune lecture**. Variable morte.
- **Boucle imbriquée à corps vide** : `modBus_Conn16channels.be:170-194`, exécutée à
  chaque réponse ModBus, avec `tasmota.yield()`, pour rien.
- **Branches vides / inatteignable dans `prepareTrame`** : `:1330` et `:1333` testent
  **deux fois** `LECTURE_ENTREES_DISCRETES` (la seconde est morte, la première devrait
  être `LECTURE_COILS` 0x01) ; corps vides pour `LECTURE_REGISTRES_HOLDER` `:1336` et
  `ECRITURE_COILS` `:1369`. Conséquence : sur TCP/UDP, 0x01/0x03/0x0F produisent une
  trame tronquée **silencieusement**.
- **17 lignes de `if/elif` qui ne choisissent qu'un texte de log** (`:539-555`), avec des
  constantes magiques 4704 / 352 / 1312 / 1216 → une table.
- **`prepareTrame:1211` rejette tout `FunctionCode > 0x06`** sauf 0x0F et 0x10 : le code
  de télémétrie devra y être ajouté explicitement.

⚠️ **La phase 1 n'est PAS bloquante pour le grenier.** Sur le maître série, `pompeQueue`
passe par `tasmota.cmd("ModBusSend …")` (`modbusFonctions.be:429`) : c'est Tasmota en C++
qui construit la trame. `prepareTrame` ne sert qu'aux transports TCP/UDP et au rôle
esclave. Le sondage 0x03 fonctionne donc **dès aujourd'hui**, sans modification.

---

## Questions encore ouvertes

1. **Position du cavalier M0** sur la carte, à noter au montage : il inverse la polarité
   des sorties et donc l'interprétation de la relecture (§8).
2. **Le module de contrôle est en 5 V et pilote une platine relais 5-24 V séparée** —
   vérifier ce que couvre l'annonce avant commande.
3. **Coquille probable de la doc constructeur** : « Read baud rate → Register address
   0x0003 » alors que tous les exemples utilisent `0x00FE` (le 3 est la *valeur*, 9600).
   À confirmer sur banc.
4. Période exacte de télémétrie par valeur (30 s pour les états, 5 min pour l'analogique
   retenu comme défaut).

## À traiter quand le ModBus du grenier sera activé

- **Commentaire périmé du bloc grenier dans `platformio_tasmota_cenv.ini`** (~l. 270) :
  « `modbusFonctions` retiré de la liste (le grenier ne l'utilise pas) ». C'est encore
  vrai **aujourd'hui** — `drivers.ModBus.activation` est à `OFF` dans le persist grenier —
  mais ça devient **faux dès que le verrou n°2 de la phase 0 est levé**. Le corriger à ce
  moment-là, et décider alors si `data/fs/modbusFonctions.be` entre aussi dans le
  `custom_berry_solidify` du grenier (il y a été volontairement **écarté** le 2026-07-24 :
  le chantier va réécrire ce module en phases 1-4, et un module solidifié n'est plus sur
  le LittleFS — donc plus de boucle courte `éditer → téléverser → BrRestart`).
  Les 3 environnements **garage** l'ont, eux, depuis le 2026-07-24.

  > **Note du 2026-07-24** : cette remarque était initialement classée « avant la phase 2 ».
  > La phase 2 est faite, mais **sa condition n'est toujours pas remplie** — le ModBus du
  > grenier reste à `OFF`, donc le commentaire demeure exact. Elle est requalifiée : ce qui
  > la déclenche n'est pas une phase du plan, c'est l'activation effective du ModBus sur le
  > grenier. Ne pas la traiter mécaniquement avant.

---

## Git

- Branche du chantier : **`chantier-modbus-grenier`**, créée depuis `development`.
- Point de retour : commit **`ce115398f`** (ancetre de `development`). Le tag local
  `avant-chantier-modbus` qui le designait a ete supprime le 2026-10-04.
- `development` reste la branche du parc en service (garage, cuve, rideau) pendant tout
  le chantier. Retour sur `development` seulement quand le banc est vert.
- ⚠️ **DÉROGATION du 2026-09-20 : `development` a été avancé (fast-forward) sur le HEAD du
  chantier (`d464c53db`) AVANT le banc vert, à la demande explicite de l'utilisateur.**
  La règle ci-dessus n'est donc plus respectée : `development` porte désormais le code
  ModBus garage **jamais exercé sur bus réel**. Conséquences à garder en tête :
  - La prochaine action (**flasher + observer**, en tête de ce document) reste entière —
    la fusion n'a rien validé, elle a seulement propagé le code.
  - `development` n'est plus la « dernière version bonne connue » du parc. Point de retour
    intact : `git branch -f development a9700ff91` (état d'avant fusion), tag
    `avant-chantier-modbus` (`ce115398f`) et branche `chantier-modbus-grenier` conservés.
  - **Synchro du fork finalisée le 2026-09-20** : les 142 commits d'upstream ont été mergés
    dans `development` (merge propre, sans conflit) et `development` a été **poussé sur
    `origin`** (HEAD `ea80274d7`). Le ModBus garage non éprouvé sur bus est donc désormais
    **publié** sur le fork. `chantier-modbus-grenier` (resté à `d464c53db`) est maintenant
    **en retard** sur `development` — le travail vit sur `development`.
  - Artefacts de build (`tasmota_defines_for_berry.{be,h}`, `user_config_override.h`,
    `modules.h`, `platformio_override.ini`) écartés avant le merge : régénérés au prochain
    build (rebuild complet obligatoire de toute façon pour flasher+observer).
- ⚠️ **Un retour en arrière git ne défait pas le matériel.** Les `.be` et le
  `_persist.json` vivent sur le LittleFS ; pour propager un changement du dépôt vers la
  puce, il faut **re-téléverser** le système de fichiers.
- ⚠️ **`erase_upload` ne « perd » pas le persist — il le remplace par celui du dépôt.**
  Le build joint `littlefs.bin` (qui embarque le `_persist.json` du dossier device) au
  flash lors d'un upload esptool (`pio-tools/post_esp32.py:385-392`), et `copy_fs_image`
  construit ce FS pour les cibles `buildfs`/`uploadfs`/`upload`/`erase_upload`
  (`pre_utilitaires_platformio.py:500`). Le vrai risque n'est donc **pas** un effacement
  sec mais un **dépôt en retard sur l'état vivant** : réglages faits en direct via
  l'interface web et non reportés, ou rollback git ramenant un `_persist.json` plus
  ancien — flasher les écraserait. **Règle : s'assurer que le `_persist.json` du dépôt
  est à jour avant de flasher.**
