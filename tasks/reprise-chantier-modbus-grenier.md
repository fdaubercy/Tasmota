# Reprise — Chantier ModBus du grenier (carte 16 relais + esclaves Tasmota)

> État au **2026-07-24, fin de session**. À lire en entier avant de reprendre.
> Document de reprise : le mettre à jour, ne pas en créer un second.
> Complément technique : `outils_docs/PROTOCOLE_MODBUS.md` §8 et §9.

---

# ⇒ SI TU REPRENDS À FROID, LIS CES 30 LIGNES D'ABORD

**Le titre de ce document dit « grenier ». Le travail porte sur les 3 modules GARAGE.**
Ne pas repartir sur le grenier : c'est l'erreur commise le 2026-07-24 (332 lignes écrites
au mauvais endroit, annulées — voir `tasks/lessons.md`). Les 3 cibles sont
`tasmota32p4-garage-serveur-modbus`, `tasmota32s3-garage-capteurs-cuve-modbus`,
`tasmota32s3-garage-rideau-garage-modbus`.

## LA PROCHAINE ACTION — flasher et observer

**14 commits sont posés sur `chantier-modbus-grenier` (de `6a79ce3f4` à `367fedc94`),
aucun poussé, et AUCUN n'a jamais été exercé sur un bus réel.** Trois changent un
comportement observable, et un cron va désormais émettre une trame toutes les 30 s.

Continuer à coder avant d'observer rendrait tout échec indécidable (règle 7 de
`lessons.md`, tombée 2× le 2026-07-15 : toujours un témoin).

**Rebuild complet obligatoire** des 3 environnements garage : `modbusFonctions.be` est
désormais solidifié, il ne monte plus sur le LittleFS — un simple `uploadfs` ne suffit pas.

Puis, avec `ReglageGlobal logLevel 4` :

| À vérifier | Ce qu'on doit voir |
|---|---|
| Pas de régression | Les relais du garage répondent comme avant |
| Doublon TCP disparu | Une commande → **un** envoi série, plus de tentative TCP vers la carte 16 |
| Appariement pas trop strict | Aucun `reponse hors-sequence rejetee` en marche normale |
| Télémétrie intacte | Les capteurs cuve/rideau remontent, sans déclencher `termineEnVol` |
| Sondage 0x03 abouti | Les 16 états reportés dans `etatConstate` toutes les 30 s |
| **Cavalier M0** | Si les 16 états reviennent **tous inversés** → M0 est connecté : poser `"cavalierM0": "connecte"` dans `drivers.ModBus.environnement.Conn16channels` du persist. C'est la question ouverte n°1, et ce sondage est le seul moyen de la trancher. |

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

Ce que la phase 0 doit prouver, avec `ReglageGlobal logLevel 4` :
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

## Ce qui reste de la phase 4 : le compteur `seq`

Le `seq` protège les **instantanés poussés par les esclaves** contre le désordre UDP.
Or ce push **n'existe pas** : la télémétrie actuelle (`globalFonctions.be:190/232/276/371`)
est **différentielle** — elle dit « ce capteur a changé », pas « voici l'état complet ».

Écrire le rejet `seq <= dernier reçu` côté maître serait donc du code mort. Le préalable
est de **convertir la télémétrie en instantané** (§9 : *« un push ne dit jamais le relai 3
a changé ; il dit voici l'état des 16 relais »*) — un chantier à part entière, à décider
plutôt qu'à glisser dans une phase.

Le reste de la phase 4 est en place pour la carte 16 relais : sondage périodique (T = 30 s),
réconciliation au boot (+15 s), séparation `etat` / `etatConstate`, chien de garde à 3×T.

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
- Point de retour : tag **`avant-chantier-modbus`** (commit `ce115398f`).
- `development` reste la branche du parc en service (garage, cuve, rideau) pendant tout
  le chantier. Retour sur `development` seulement quand le banc est vert.
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
