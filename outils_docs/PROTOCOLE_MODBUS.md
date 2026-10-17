# Protocole ModBus — référence du fork

> Doc créée le 2026-07-16. Couvre le ModBus **standard** (RTU/TCP), l'**implémentation
> maison** (3 transports Série/UDP/TCP), l'**extension esclave→maître**, et le **design de
> file d'attente (queue)** décidé pour le maître.
> Fichiers : `data/fs/modbusFonctions.be` (logique), `data/fs/controleModbus.be` (driver),
> `data/fs/modBus_TasmotaSlaveModBus.be` (Tasmota esclave), `data/fs/modBus_Conn16channels.be`
> (relais 16 canaux). Mode d'emploi (commandes d'exemple, trames detaillees par code de
> fonction) : [Aide/MODBUS.md](Aide/MODBUS.md) — ce document-ci est la reference de CONCEPTION.

---

## 1. ModBus classique — le socle

ModBus est un protocole **maître/esclave** (un seul maître, N esclaves adressés 1..247).
**Seul le maître initie** ; un esclave ne parle **que** pour répondre à une requête qui le
vise. C'est la limite que l'extension maison (§4) contourne.

**Codes fonction utilisés ici** (`modbusFonctions.be:42-51`) :

| Code | Nom | Usage dans le parc |
|---|---|---|
| 0x02 | Lecture entrées discrètes | état d'un interrupteur/bouton |
| 0x04 | Lecture registres d'entrée | analogique, compteur, thermomètre |
| 0x05 | Écriture coil unique | 1 relai |
| 0x06 | Écriture registre unique | relai module 16 sorties |
| 0x10 | Écriture registres multiples | LED WS2812 (couleur/saturation/lum.) |
| 0x11 | `ISALIVE_ESCLAVE` (**custom, inutilisé**) | keep-alive esclave — jamais câblé |

**Trame RTU** (série RS485) : `[adresse 1o][code 1o][données No][CRC16 2o]`.
Le CRC16 ModBus (poly `0xA001`, init `0xFFFF`, octets inversés) est réimplémenté en Berry :
`modbusFonctions.crc16modbus()` (`:1337`).

---

## 2. ModBus TCP — le standard (ce que tu voulais consigner)

ModBus **TCP** transporte les mêmes PDU (code fonction + données) mais **sur TCP/IP,
port 502**, avec deux différences majeures par rapport au RTU :

1. **Pas de CRC.** TCP garantit déjà l'intégrité → le CRC16 est supprimé.
2. **Un en-tête MBAP** (7 octets) préfixe la PDU, à la place de l'adresse+CRC :

```
+---------------------+----------------+-----------------+-------------+  PDU
| Transaction Id (2o) | Protocol Id(2o)| Length (2o)     | Unit Id(1o) | FnCode + data
+---------------------+----------------+-----------------+-------------+
  = n° de requête       = 0 (ModBus)     = octets qui       = adresse
    (corrélation)                          suivent            esclave
```

- **Transaction Id** : le maître le choisit, l'esclave le **recopie** dans sa réponse →
  permet de corréler réponse↔requête (et donc, en principe, d'avoir **plusieurs requêtes en
  vol**). ⚠️ L'implémentation maison n'exploite PAS ce champ (voir §5).
- **Protocol Id** : toujours 0.
- **Length** : nombre d'octets après ce champ (Unit Id inclus).
- **Unit Id** : l'adresse esclave (utile derrière une passerelle TCP→RTU).

**Modèle réseau standard** : le **maître est client TCP**, il ouvre la connexion vers
l'esclave (serveur, port 502) et envoie ses requêtes. L'esclave ne peut **jamais** initier.

---

## 3. L'implémentation maison — 3 transports en parallèle

Le framework ne s'appuie PAS sur la pile ModBus native de Tasmota seule : il gère
**trois transports** activables par `_persist.json > drivers.ModBus.typeComm`
(`Serial` / `TCP` / `UDP`), dispatché par `envoiMsgModbus()` (`:393`) :

- **Série (RS485)** : maître → `tasmota.cmd("ModBusSend {...}")` (pile native Tasmota) ;
  esclave → écrit la trame brute sur `serialModBus.write()` (`:508`).
- **TCP** : `envoiMsgModbusTCP()` (`:579`) — trame **préfixée texte** `"ModbusTCP " + trame`.
- **UDP** : `envoiMsgModbusUDP()` (`:518`) — même principe, non-standard (ModBus n'existe
  pas officiellement sur UDP).

**Réception** : les réponses reviennent par **règles Tasmota** (`controleModbus.be:29-33`) :
`ModbusReceived` (série) / `ModbusReceivedTCP` / `ModbusReceivedUDP` →
`controleModbus.recupereReponseModBus*()`.

> ⚠️ Le préfixe texte `"ModbusTCP "`/`"ModbusReceived"` est une **surcouche maison**, pas du
> ModBus TCP standard (pas de MBAP). Deux nœuds du parc se comprennent, mais un équipement
> ModBus TCP tiers **ne parlera pas** ce dialecte. À garder en tête si un jour on veut
> interopérer avec du matériel standard.

---

## 4. L'extension esclave→maître (le cœur de ton besoin)

**Problème** : en ModBus classique, un esclave (ex. un capteur qui détecte un événement)
**ne peut pas** prévenir le maître de lui-même ; il faut que le maître **interroge** (polling),
ce qui est lent et bavard.

**Solution maison** : sur les transports **TCP/UDP**, la connexion est **persistante et
bidirectionnelle**. L'esclave garde le socket ouvert avec le maître et **écrit dessus quand
il veut** (`envoiMsgModbusTCP`, branche `id > 0`, `:599-604` : `Client.write("ModbusTCP " +
trame)`). Le maître reçoit alors une trame **non sollicitée** via la règle `ModbusReceivedTCP`.
C'est un **push esclave→maître**, impossible en ModBus standard.

**État constaté / à confirmer ensemble** :
- Le canal TCP/UDP porte bien ce push (vérifié dans `envoiMsgModbusTCP`).
- Le code fonction custom `0x11 ISALIVE_ESCLAVE` existe mais est marqué **inutilisé**
  (`:51`) — candidat naturel pour un keep-alive/heartbeat esclave→maître si on formalise.
- Le chemin **série** (RS485 half-duplex) ne permet PAS ce push proprement : le bus est
  partagé, un esclave qui parle sans y être invité **collisionne**. À réviser : sur série,
  l'esclave→maître devrait rester du polling, ou passer par un time-slot.

---

## 5. Le mécanisme d'envoi actuel — et ses failles

**Modèle actuel** : un **unique booléen** `modbusFonctions.attenteReponse` = « une trame est
en vol, on attend sa réponse ». Posé/levé depuis **11 endroits dans 4 fichiers**.

Envoi (`envoiMsgModbusSerial`, `:441`) :
- si `attenteReponse == false` → envoie, met le flag à `true`, **arme un timer de timeout**
  (`reinitialiseFlagModBus`, `:1326`, défaut 1000 ms) qui remettra le flag à `false` ;
- si `attenteReponse == true` → **re-planifie l'envoi du MÊME message** dans ~1 s via un
  timer nommé `"envoiMsgEnCours_" + StartAddress` (`:478`).

**Failles identifiées :**

1. **Collision de nom de timer → perte de message.** Le timer d'attente est nommé par la
   seule `StartAddress` (`:478`, et `"resetFlagTimeout_" + StartAddress` en `:1326`). Deux
   messages différents (function code / valeur différents) vers la **même** StartAddress
   portent le **même** nom de timer → le second **écrase** le premier → un ordre est **perdu
   en silence**.
2. **Pas d'ordre garanti (FIFO).** Chaque message bloqué se re-planifie sur son propre timer.
   Quand le flag se libère, l'ordre de renvoi dépend de quel timer tire en premier → ni FIFO,
   ni équité, risque de **famine** d'un message.
3. **Flag levé par timeout, pas par la vraie fin.** `reinitialiseFlagModBus` remet le flag à
   `false` après 1 s **même si la réponse n'est pas arrivée**. Une réponse lente laisse alors
   partir la commande suivante → **collision sur le RS485**.
4. **État distribué.** `attenteReponse` posé/levé depuis 11 sites (`controleModbus`,
   `modBus_Conn16channels`, `modBus_TasmotaSlaveModBus`, `modbusFonctions`) → impossible à
   raisonner, source de courses.

---

## 6. Design proposé — file d'attente (queue) FIFO à un seul en-vol

Remplacer le booléen distribué par **une file + un slot « en vol »**, centralisés dans
`modbusFonctions`.

**État :**
```berry
modbusFonctions.queue      = []      # liste FIFO de {paramMSG, typeMsg, id, tentatives, transport}
modbusFonctions.enVol      = nil     # le message actuellement envoyé (nil = canal libre)
modbusFonctions.timeoutTid = nil     # id du timer de timeout du message en vol
```

**Émettre** (remplace l'appel direct à `envoiMsgModbus`) :
```berry
def enfileMsg(paramMSG, typeMsg, id)
    # dedup optionnel : ecraser un ordre pendant pour la meme cible (adresse+registre)
    modbusFonctions.queue.push({"paramMSG":paramMSG, "typeMsg":typeMsg, "id":id, "tentatives":0})
    modbusFonctions.pompeQueue()
end
```

**Pomper** (unique point d'envoi) :
```berry
def pompeQueue()
    if modbusFonctions.enVol != nil  return end          # un message est deja en vol
    if size(modbusFonctions.queue) == 0  return end       # rien a envoyer
    modbusFonctions.enVol = modbusFonctions.queue[0]      # FIFO : on prend la tete
    modbusFonctions.queue.remove(0)
    # envoi reel (serial/tcp/udp) ...
    # arme UN timer de timeout, nomme de facon UNIQUE (pas par StartAddress) :
    modbusFonctions.timeoutTid = tasmota.set_timer(TIMEOUT, /-> modbusFonctions.surTimeout(), "modbus_timeout")
end
```

**Terminer** (un seul chemin, appelé par la réception OU le timeout) :
```berry
def termineEnVol(ok)
    if !ok && modbusFonctions.enVol && modbusFonctions.enVol["tentatives"] < MAX_RETRIES
        modbusFonctions.enVol["tentatives"] += 1
        modbusFonctions.queue.insert(0, modbusFonctions.enVol)   # requeue en tete, bornee
    end
    modbusFonctions.enVol = nil
    modbusFonctions.pompeQueue()                                  # enchaine le suivant
end
```
- **Réception** (`recupereReponseModBus*`) → `termineEnVol(true)` (au lieu de poser le flag).
- **Timeout** → `termineEnVol(false)` (retry borné, puis abandon loggé — pas de perte muette).

**Ce que ça corrige :** FIFO garanti (1), plus de collision de nom de timer (1,2), un seul
timer de timeout unique, fin pilotée par la **vraie** réponse et non par l'horloge (3), état
centralisé en un lieu (4). Compatible avec les 3 transports (le `pompeQueue` choisit le
transport comme aujourd'hui).

**Option avancée (plus tard)** : exploiter le **Transaction Id** MBAP (§2) pour autoriser
**plusieurs requêtes en vol** corrélées par leur id — gain de débit, mais complexité accrue ;
à ne faire qu'après avoir mesuré que le FIFO à-un-en-vol est le goulot.

---

## 7. Etat d'implementation (2026-07-16) — FAIT

La file FIFO est **implementee** dans `modbusFonctions.be` et cablee dans les handlers.
Vérifié au xtensa-gcc (module solidifiable, 20 closures, 0 anonyme). **Reste a valider a
l'execution (flash + console).**

- **File** : `queue` / `enVol` + `enfileMsg` / `pompeQueue` / `termineEnVol` / `surTimeout`.
  Le maitre (`envoiMsgModbusSerial`, id==0) **enfile** au lieu de renvoyer par timer.
  Un seul en vol, timeout a nom unique, retry borne (`MAX_TENTATIVES=3`). FIFO a l'origine ;
  depuis le 2026-10-10, **priorite aux ecritures** et envoi differe (voir ci-dessous).
- **Acquittement** : les handlers de reponse (`controleModbus`, `modBus_Conn16channels`,
  `modBus_TasmotaSlaveModBus`) appellent `termineEnVol(true)` a la reception.
- **Appariement reponse<->requete** : `apparieReponse(msg)` injecte StartAddress/Count/type
  depuis `enVol` dans une reponse de LECTURE (la trame RTU ne les porte pas), et signale une
  reponse hors-sequence. `enVol` = « le tableau des commandes envoyees » reduit a 1 entree,
  car un-seul-en-vol (Tasmota ModBusSend ne memorise qu'une requete pendante).
- **Timer P4-safe** : `armeTimer` / `desarmeTimer` basculent sur `add_cron` si
  `diverses["typeESP"] == "ESP32P4"` (le maitre de garage), sinon `set_timer`. Absorbe
  l'ancien contournement de `relanceEnvoiMsgModbus` (supprimee, comme `reinitialiseFlagModBus`).

**A valider / faire ensuite :**
1. **Flash + test runtime** (surtout le maitre garage ESP32-P4) : ordre des envois, pas de
   message perdu, timeout/retry, appariement des lectures. Compile ≠ execution.
2. Activer le **rejet strict** dans `apparieReponse` (jeter une reponse non appariee) une fois
   le comportement observe sur banc.
3. Formaliser l'extension esclave→maître (heartbeat via `0x11`, cas serie RS485).
   → **Tranche le 2026-07-24**, voir §9.
4. Interop : garder le dialecte texte maison, ou ajouter un vrai mode ModBus TCP standard
   (MBAP) pour du materiel tiers.
   → **Tranche le 2026-07-24 : dialecte maison conserve, pas de MBAP.** Le push
   esclave→maitre n'existe PAS en ModBus standard : le MBAP n'apporterait que
   l'interoperabilite avec du materiel tiers, besoin absent du parc. Le `Transaction Id`
   est sans objet tant qu'on reste a un-seul-en-vol.

### Evolutions du 2026-10-10 — mesurees sur le bus reel (maitre P4, cuve, rideau)

Constat de depart : un clic sur un relai partait **~9 s** plus tard, et la cuve semblait
repondre en « 6 s ». Trois causes, trois corrections dans `modbusFonctions.be` :

1. **Reponses jetees par le pont Tasmota — l'envoi est desormais toujours differe.**
   `ModbusBridgeHandle` (`xdrv_63_modbus_bridge.ino`) publie `ModbusReceived`, donc execute nos
   regles, PUIS remet `modbusBridge.deviceAddress = 0` en sortant (l.652). Un `ModBusSend`
   lance depuis la regle (`termineEnVol(true)` -> `pompeQueue`) voyait son adresse effacee :
   sa reponse tombait en `nodataexpected`, rejetee **sans aucun log** parce que
   `USE_MODBUS_BRIDGE_TCP` est compile (`return` muet). Mesure : **61 reponses jetees pour 161
   decodees**, chacune payee d'un timeout (5 s) et d'un renvoi — les « 6 s » de la cuve, qui
   repond en realite en 0,3 s. Signature dans le log du maitre : un `SUR_TIMEOUT` **sans**
   `MBS: MBR Recv timed out` juste avant.
   Correction : `pompeQueue` ne fait plus qu'armer `envoieTete` par `armeTimer(0, ...)`
   (nom `modbus_envoi`) ; le `ModBusSend` part toujours apres la sortie du pont.
2. **Priorite aux ecritures** (`placeEnFile`). Une ecriture (commande de relai...) passe
   devant toutes les lectures en attente, dans l'ordre d'arrivee des ecritures entre elles.
   Renvoi d'une ecriture : en tete. Renvoi d'une lecture : devant les autres lectures, jamais
   devant une ecriture. Les regles `MAX_FILE` (une ecriture evince la plus ancienne lecture)
   et de dedoublonnage des lectures sont inchangees.
3. **Esclave muet, decide par la file** (`estMuet` / `noteAbandon` / `noteContactBus`,
   `SEUIL_MUET = 2`). Un esclave muet coutait **3 x 5,5 s = 16,5 s de bus par message**.
   - Declaration : 2 messages **de suite** abandonnes sans reponse (~33 s, au lieu des 90 a
     120 s du chien de garde). Ses lectures en attente sont retirees de la file.
   - Effet : **plus aucun renvoi**, lecture comme commande. Une commande part une seule fois :
     si l'esclave est revenu, elle s'execute et sa reponse leve l'etat. Le releve des ESP32
     n'envoie qu'une sonde par cycle a un muet (`releveEsclaves`).
   - Duree : jusqu'au premier contact — reponse appariee (`termineEnVol(true)`) ou push
     accepte (`TasmotaSlaveModBus.noteContact`).
   - Logs : `ESCLAVE_MUET: ... declare muet` en `erreur` (une fois), `... repond de nouveau`
     en `info`. Une commande perdue reste une `erreur` ; la sonde ratee d'un muet, `debug`.
   - Le chien de garde des drivers (§9) garde son seul role : passer les etats constates a
     `inconnu`.

Non change, volontairement : `timeoutReponse` = 5000 ms (la carte repond en 2-4 ms, la cuve
en 0,3-0,4 s ; a raccourcir une fois les corrections ci-dessus validees sur le bus).

---

## 8. La carte 16 relais RS485 — carte des registres (2026-07-24)

Source : `outils_docs/Electronique/Connecteur ModBus/16 Channel Multifunction RS485
Module commamd.docx` et `... Manual.docx`. **Verifie dans la doc constructeur, pas deduit.**

Commandes d'exemple pretes a l'emploi (trames et `ModBusSend`) : [Aide/MODBUS.md](Aide/MODBUS.md),
section « Exemples de commandes pour les Modules ModBus 16 channels ». ⚠️ Vocabulaire different, a
confirmer sur la carte : l'ordre `01` y est appele « Fermeture » (et `07` « Fermeture de tous »),
la ou le constructeur dit « Open » (« Open all ») — memes trames, sens physique a verifier.

Usine : **9600 bauds, 8N1, adresse 0x01**. Deux jeux de commandes reconnus automatiquement
(AT en ASCII, ModBus RTU en HEX) — on n'utilise que le ModBus.

### Ecriture — fonction 0x06

`[id][06][adresse 2o][ordre 1o][temporisation 1o][CRC 2o]`

- **adresse** = numero de canal, `0x0001`..`0x0010` (`0x0000` = tous)
- **ordre** : `01` Open · `02` Close · `03` Toggle · `04` Latch · `05` Momentary ·
  `06` Delay · `07` Open all · `08` Close all
- **temporisation** : 0-255 s, uniquement pour l'ordre Delay

Exemple : canal 1 Open → `01 06 00 01 01 00 D9 9A`.
C'est exactement ce que construit `modBus_Conn16channels.be` (`Values: [valueModBus, 0]`,
`type: "uint8"`, `Count: 1`).

### Relecture d'etat — fonction 0x03 (LE point cle)

**La carte sait relire l'etat de ses 16 sorties en une seule trame** — c'est ce qui rend
l'« etat constate » (§9) atteignable pour elle.

```
Requete  : 01 03 00 01 00 10 15 C6        -> 16 registres depuis 0x0001
Reponse  : 01 03 20 <32 octets> <CRC>     -> un registre 16 bits par canal
                                             0x0001 = open, 0x0000 = close
```

39 octets de reponse, une seule entree dans la file. Sur le maitre serie, ca fonctionne
**sans toucher a `prepareTrame`** : `pompeQueue` passe par `tasmota.cmd("ModBusSend …")`,
c'est Tasmota en C++ qui batit la trame.

```
ModBusSend {"deviceaddress":1,"functioncode":3,"startaddress":1,"type":"uint16","count":16}
```

### Registres de configuration

| Fonction | Registre | Valeurs |
|---|---|---|
| Debit | `0x00FE` | 0:1200 · 1:2400 · 2:4800 · 3:9600 · 4:19200 · 5:retour usine |
| Adresse esclave | `0x00FF` | 1..247 |
| Lire l'adresse (diffusion) | `FF 03 00 FF 00 01 A1 E4` | repond l'id courant |

Passer a 19200 : `01 06 00 FE 00 04` + CRC.

> **Reglage MANUEL, hors firmware (note du 2026-07-24).** Le debit de la carte 16 relais
> est configure **a la main par l'utilisateur AVANT son integration au bus** (usine 9600 ->
> 19200), un seul module connecte. Le firmware Tasmota **ne l'automatise pas** : ne pas
> chercher a faire regler le debit par le driver. Rappel : effectif seulement apres coupure
> d'alimentation (voir piege 3 ci-dessous).
>
> **Verifier le debit d'une carte (2026-10-04)** : `ReglageModbus TesteDebitConn16channels <id> [debit]`
> sur le maitre. Suspend la file, passe le bus au debit d'essai, lit `0x00FE` de l'esclave puis
> l'adresse par diffusion (`0x00FF`), revient au debit du bus et relance la file ; reponses
> journalisees en clair (`TESTE_DEBIT_CONN16:`). Ne PAS taper `ModbusBaudrate 9600 ModBusSend ...`
> sur une seule ligne : sans `Backlog`, seul `ModbusBaudrate` s'execute.
>
> **Aligner la carte sur le persist (2026-10-06)** : `ReglageModbus VerifieConn16channels [corrige]`
> sur le maitre (`modbusFonctions.verifieConn16`). Lit `0x00FE` a l'ID du persist au debit du bus ;
> sans reponse, balaie les 5 debits en lisant l'ID par diffusion. Compare a
> `Conn16channels.<carte>.id` et `drivers.ModBus.debit` ; avec `corrige`, ecrit le debit puis l'ID.
> Lancee aussi au boot (avec correction) si `verifieAuDemarrage: "ON"` dans le bloc de la carte.
> Un debit ecrit demande toujours la coupure d'alimentation de la carte (piege 3).

### Six pieges de cette carte

1. **« Open » veut dire niveau BAS.** Glossaire : `Open : control port output low level`.
   Avec des relais inverses (`type: 256`), un registre lu a `0x0001` (open) correspond a
   un relai **ON**. Table d'inversion a centraliser **une seule fois** (index inverse, §9).
2. **Le cavalier M0 inverse la polarite** : M0 deconnecte = sortie basse (defaut), M0
   connecte = sortie haute. Il change donc la table ci-dessus. **Noter sa position au
   montage** — sinon la relecture sera coherente et fausse.
3. **Le changement de debit ne prend effet qu'apres coupure d'alimentation.**
   Si rien ne change apres la commande, ce n'est pas un echec.
4. **Le changement d'adresse exige un bus mono-equipement.** Adresser la carte AVANT de
   cabler les esclaves Tasmota.
5. **Une commande invalide ne renvoie RIEN** (« instruction is invalid, no return »).
   Symptome cote file : timeout x3 puis abandon logge. Silence != carte absente.
6. **C'est un module de controle 5 V (10-15 mA), pas une platine relais.** Il pilote une
   platine 5-24 V separee. A verifier sur l'annonce avant commande.

### Cablage RS485 (rappel)

Transceiver **3,3 V** cote ESP32-S3 (MAX3485 / SP3485 / SN65HVD75 — **pas** un MAX485 5 V).
Cable : Belden 3106A (1 paire 22 AWG + fil de masse, 120 Ω) ou **Cat6 F/UTP 23 AWG rigide**
(100 Ω ; l'ecart d'impedance est sans effet a 19200 bauds sur quelques dizaines de metres).

En Cat6 : **A et B sur les deux fils d'une MEME paire** (bleue, broches 4-5) ; masse sur la
paire marron, les deux fils relies. Terminaison 120 Ω aux deux extremites, ecran a la terre
d'**un seul cote**. **Ne jamais faire passer le 12 V des bobines dans ce cable.**

---

## 9. Synchronisation maitre/esclave — architecture retenue (2026-07-24)

**Objectif reformule.** « 100 % synchronise a tout instant » est impossible sur un reseau
a pertes. Ce qui est atteignable, et suffisant :

> **Convergence bornee** — la copie du maitre egale celle de l'esclave au bout de T
> secondes maximum, **toujours**, quelles que soient les pertes.
> **Jamais faux en silence** — dans le doute, le maitre affiche « inconnu », jamais une
> vieille valeur presentee comme fraiche.

### Deux plans, jamais melanges

| | Plan **commande** | Plan **telemetrie** |
|---|---|---|
| Sens | maitre → esclave | esclave → maitre |
| Transport | RS485 serie | UDP |
| File (ecritures d'abord, §7) | **oui**, un seul en vol | **jamais** |
| Accuse | obligatoire (`termineEnVol`) | **aucun** |
| Perte | retry borne puis erreur | toleree, la suivante arrive |

La file ne serialise qu'un seul medium : le RS485. Un datagramme UDP n'y touche pas — donc
un push **ne peut structurellement pas encombrer la file**, a condition que la reception
soit separee (voir « le blocage » ci-dessous).

⚠️ **Ne PAS ajouter d'accuse sur la telemetrie.** C'est le reflexe naturel face a « 100 % »,
et c'est le piege : il recreerait la serialisation qu'on cherchait a eviter.

### Le mecanisme : l'instantane complet

**Un push ne dit jamais « le relai 3 a change ». Il dit « voici l'etat des 16 relais ».**

- Un message **differentiel** exige d'etre delivre : perdu, l'ecart est permanent.
- Un **instantane** est idempotent : perdu ou duplique, le suivant porte la verite entiere.

16 etats tiennent dans 2 octets. L'instantane ne coute rien de plus et supprime tout besoin
de fiabilite de transport. C'est ce qui rend la convergence **demontrable** plutot
qu'esperee.

### Trois complements obligatoires

1. **Compteur de version `seq`** contre le desordre : UDP peut reordonner, et un instantane
   ancien arrivant apres un recent reecrirait une valeur perimee. L'esclave incremente
   `seq` a chaque changement ; **le maitre rejette tout instantane de `seq` <= au dernier
   recu**. Bonus : un `seq` qui repart de zero signale un redemarrage d'esclave.
2. **Etat commande != etat constate.** L'accuse du plan commande confirme que la trame est
   passee, **pas que le relai a bouge**. La boucle ne se ferme qu'a la confirmation par
   l'instantane. Si `commande != constate` au-dela de T : renvoi, puis alarme.
3. **Reconciliation au demarrage.** Au boot, le maitre interroge chaque esclave (requete
   ponctuelle, plan commande) ; l'esclave, a la reconnexion, pousse spontanement. Les deux
   sont necessaires : l'un couvre le reboot du maitre, l'autre celui de l'esclave.

**Chien de garde** : pas d'instantane d'un esclave depuis plus de 3xT → cet esclave passe
en **« etat inconnu »**. C'est la clause « jamais faux en silence ».

### Le blocage actuel — verifie

Les trois chemins de reception acquittent **indistinctement** :
`controleModbus.be:261` (UDP), `controleModbus.be:181` (TCP, route vers
`recupereReponseModBus`), `modBus_Conn16channels.be:200`, `modBus_TasmotaSlaveModBus.be:405`
— tous appellent `modbusFonctions.termineEnVol(true)`.

**Consequence si on active le push tel quel** : un capteur qui pousse en UDP **acquitte la
commande serie en vol**. Le timeout se desarme, le message suivant part alors que la
reponse precedente est en transit → collision. C'est la faille n°3 du §5, ressuscitee par
une autre porte.

**Correctif — les deux crans, pas un :**
1. **Code fonction dedie** pour la trame non sollicitee (emplacement naturel :
   `0x11 ISALIVE_ESCLAVE`, reserve et jamais cable, `modbusFonctions.be:59`). Le handler le
   voit **avant** tout le reste et route vers un chemin qui ne touche jamais `enVol`.
   ⚠️ `prepareTrame:1211` rejette tout `FunctionCode > 0x06` sauf 0x0F et 0x10 : ce code
   doit y etre mis en **liste blanche**.
2. **Rejet strict dans `apparieReponse`** (`:524-527`) : la fonction detecte deja
   l'anomalie et se contente de la logguer. Si `DeviceAddress`/`FunctionCode` ne
   correspondent pas a `enVol`, ce n'est **pas** une reponse → ne pas acquitter.

Le 1 exprime l'intention, le 2 est le filet. Les deux, parce qu'un acquittement errone est
silencieux.

### Rythmes et budget

| Donnee | Source | T | Pourquoi |
|---|---|---|---|
| 16 relais (carte RS485) | **polling maitre 0x03** | 30 s | La carte ne peut rien pousser |
| Relais / positions (esclaves Tasmota) | push instantane | 30 s | Convergence garantie sous 30 s |
| Capteurs analogiques | push instantane | 5 min | Convergence lente acceptable |
| Changement d'etat | push immediat | ~instant | **Latence uniquement**, pas la garantie |

Budget mesure : 2 esclaves x 4 valeurs groupees en une trame = **2 datagrammes / 30 s**,
~23 octets chacun, soit ~45 octets/minute. Plus une lecture 0x03 de 39 octets toutes les
30 s dans la file (0,03 trame/s). **Negligeable** — le debit n'est pas le sujet.

**Le risque, ce sont les rafales**, pas la moyenne. Trois garde-fous :
1. le push periodique est la **source de verite**, l'evenementiel n'est qu'une optimisation
   de latence → une trame evenementielle perdue se repare seule au battement suivant ;
2. **plancher de periode** par valeur (~1 s) avec fusion : une rafale de 200 changements
   devient 1 trame ;
3. **hysteresis** sur les valeurs analogiques (delta minimal avant push).

**Un seul timer**, pas un par valeur : un tick unique (5 s) balaie une table plate et pousse
ce qui est du. Meme schema que l'index inverse. Et **decaler les esclaves entre eux**
(offset = id x quelques secondes) pour eviter que le handler mono-thread du maitre ne recoive
tout au meme instant.

### Mise en oeuvre retenue (2026-09-29) — options A + B

**A — releve periodique par le maitre = source de verite.** `releveEsclaves()`
(`modBus_TasmotaSlaveModBus.be`), cron `releve_TasmotaSlaveModBus` toutes les 30 s, maitre
seul. Une demande de lecture **par appareil virtuel** `ModBus_TasmotaSlaveModBus<n>`, au
protocole existant (`StartAddress = type + idModBus - 1`) : 0x02 (interrupteurs, capteurs,
boutons), 0x04 uint32 (analogiques, compteurs), 0x04 float (thermometres, 2 valeurs pour un
DHT22). Transport **RS485**, via la file du maitre. L'instantane « un bloc = tout l'etat » n'a
pas ete retenu : relire chaque appareil a chaque cycle donne la meme convergence (chaque
valeur est entierement relue) sans nouvelle carte de registres.

**B — push d'evenement de l'esclave = accelerateur.** `modbusFonctions.pousseEtat()`, appele
par `globalFonctions` sur changement d'interrupteur, bouton, capteur ou compteur (les
thermometres et analogiques ne poussent pas : trop variables, le releve A suffit).

```
UDP multicast : "ModbusPushUDP " + trame en hexa
trame        : [id esclave][0x10][registre 2][nb registres 2][nb octets 1][donnees][CRC]
exemple      : 03 10 00A0 0001 02 00FF E7D0     (rideau, interrupteur 1 = ON)
```

- **PDU standard** (Write Multiple Registers) : elle porte le registre, donc le maitre sait quel
  capteur a change. Le bit `0x80` (= exception en ModBus) n'est plus utilise pour le push.
- **L'enveloppe `ModbusPushUDP`** marque la trame non sollicitee : seul le maitre la traite
  (`udpFonctions.lireUDP`), comme `Automatique` ; elle **n'acquitte jamais** la requete en vol.
- `DeviceAddress` = **l'id de l'esclave emetteur** (et non la cible) : c'est ce qui route la
  trame vers la regle `ModbusReceivedUDP#DeviceAddress==<id>` du bon esclave.
- Ni accuse ni file : une perte est reparee par le releve A suivant (< 30 s).
- Avec le serie actif, **l'UDP ne porte que ce push** (`envoiMsgModbus`) : commandes et
  reponses restent sur le RS485, sinon doublons (double execution, acquittement errone).
- Etat d'un interrupteur lu sur le **bit 0** : `0x01` en reponse serie standard, `0x00FF` en push.

**Complements (2026-09-29, apres A + B)** — le reste du §9 est fait :

- **Numero d'ordre `seq`** (`4532f12ec`). Enveloppe devenue
  `"ModbusPushUDP <seq> <trame hexa>"` ; `seq` = 1 au premier push apres demarrage, +1 par
  push emis. Le maitre (`modbusFonctions.accepteSeq`, appele par `lireMsgModbus` avant
  publication) ecarte doublons et datagrammes arrives apres un plus recent. `seq == 1` apres
  un plus grand, ou recul de plus de `FENETRE_SEQ` (16) = **redemarrage de l'esclave**, accepte.
  L'ancien format sans `seq` reste lu, sans filtrage. Seuls les pushes sont filtres.
- **Chien de garde par esclave** (`9e6331cf8`), calque sur la carte 16 relais. Contact =
  reponse appariee ou push accepte (`noteContact`). Au cron du releve, un esclave actif sans
  contact depuis **plus de 3 x 30 s** est declare muet une seule fois
  (`MODBUS_TASMOTA_SLAVE_CHIEN_DE_GARDE: ... muet`) : `etatConstate = "inconnu"` sur ses
  appareils virtuels, `etat` (commande) intact. Retour journalise au contact suivant ; chaque
  appareil retrouve son constat a sa prochaine valeur (`"valide"` pour un capteur, ON/OFF pour
  un relai). Depuis le 2026-10-10, l'etat **muet de la file** (2 abandons de suite, §7) est
  distinct : il supprime les renvois ; le chien de garde, lui, ne fait que l'`inconnu`.
- **Relais d'esclaves : commande / constate** (`45d432257`). L'esclave repond a la lecture
  **0x01** (bit 0 = Power ON) ; le releve A lit en 0x01 les relais virtuels 224/256 (pas les
  WS2812 1376). `etatConstate` + `constateA`, ecart journalise
  (`MODBUS_TASMOTA_SLAVE_ECART: relai n°... commande=..., constate=...`), jamais corrige.
  Relais_i (256) : logique inversee (ON commande = relai physique au repos).
- Deux defauts trouves en chemin, corriges : l'esclave executait `Power<StartAddress>`
  (Power256...) au lieu de `Power<id>` — **aucun relai d'esclave ne pouvait basculer**
  (`8c42ad056`, `modbusFonctions.idRelai`) ; l'echo d'une commande 0x06 remettait l'etat
  commande du relai a OFF (`45d432257`).
- `typeComm.TCP = OFF` sur le P4 et la cuve (`e2ee294a9`) : transport TCP casse (le maitre lit
  un autre client que ceux qu'il connecte, `ImAlive` ne dit pas quel esclave se signale,
  aucune reconnexion) et hors de tout chemin utile.

Verifie au banc (`banc_test_modbus.be`, sections 8 a 15 : 76 PASS, temoins sur l'ancien code) ;
**pas encore sur bus reel**.

### Observer les push depuis le reseau maison — relais MQTT du maitre (2026-10-10)

Constate le 2026-10-10 : le sniffeur (PC sur le Wi-Fi maison, 192.168.0.x) ne voyait **aucun**
push. La cuve est cliente du point d'acces du maitre (`RgxClients` du P4 : `F0F5BD436BB0` en
192.168.4.2) ; le NAPT lwIP ne relaie **pas** le multicast, qui reste dans 192.168.4.0/24. Ecoute
du PC verifiee correcte (groupe rejoint sur l'interface Wi-Fi, pare-feu hors de cause).

- **Maitre** : `modbusFonctions.relaiePushMQTT`, appele par `udpFonctions.lireUDP` sur chaque
  `ModbusPushUDP` recu, republie le datagramme **brut**, quel que soit le verdict
  d'`accepteSeq`, sur `tele/<topic>/MODBUSPUSH` = `{"ip": ..., "msg": "ModbusPushUDP <seq> <hexa>"}`,
  non retenu. Garde : `drivers.ModBus.relaisPushMQTT` (**OFF** par defaut, cle presente dans tous
  les persists ModBus), reglee par `ReglageModbus RelaisPushMQTT ON|OFF` ; maitre (id 0) seulement.
  Un echec de publication est journalise et n'empeche jamais le traitement du push.
- **Observation seulement** : aucun module ne s'abonne a ce topic ; le plan telemetrie ne depend
  toujours pas du broker. Le relais montre ce que le **maitre** a recu : une perte entre l'esclave
  et le maitre reste invisible (pour la voir : PC sur le point d'acces du maitre).
- **Sniffeur** : `ecoute_udp.EcouteRelaisMQTT` s'abonne a `tele/+/MODBUSPUSH` et `tele/+/+/MODBUSPUSH`
  (broker de `user_config_override.h`, `--mqtt non` pour couper). Table de numeros d'ordre
  **separee** de celle de l'UDP : la copie MQTT d'un push deja entendu en UDP n'est pas un doublon.
  Fil de la page : sens `MQTT`.
- Bancs : `banc_test_modbus.be` §25, `test_discovery.be` §13 (branchement dans `lireUDP`),
  `test_sniffeur_modbus.py` `test_relais_mqtt` (faux broker local). **Pas encore observe sur la carte.**

### Capteur absent ou defaillant — la sentinelle (2026-10-10)

Avant : l'esclave repondait `find("value", 0.00)` ; sans mesure, le maitre lisait **0**,
indiscernable d'une vraie mesure (cause probable des 0 de la cuve, `DSB: Capteur trouve 0`).

**Pourquoi pas une exception ModBus (0x84)** : sur le maitre serie, le pont Tasmota la journalise
(`MBR Driver receive error 4`) et ne publie **pas** `ModbusReceived`
(`xdrv_63_modbus_bridge.ino:390`) : Berry n'y voit qu'un silence -> 3 renvois -> 2 abandons -> **tout
l'esclave declare muet** pour un seul capteur. La corriger toucherait un fichier amont.

**La sentinelle traverse le pont tel quel** :

| Type | Sentinelle emise | Recue par le maitre serie | Par UDP/TCP |
|---|---|---|---|
| `float` (thermometres 1312, 1216) | NaN | `null` dans `ModbusReceived` (`ext_printf.cpp` : `isnan` -> `"null"`) -> `nil` | NaN |
| `uint32` (analogiques 4704, compteurs 352) | `0x7FFFFFFF` | 2147483647 | 2147483647 |

`0x7FFFFFFF` est hors plage : ADC <= 4095, ADS1115 <= 32767, compteurs < 1e9. Une vraie mesure 0
reste 0.

- **Esclave — fraicheur, pas valeur.** Les mesures arrivent par regles Tasmota a chaque
  `TelePeriod` ; une sonde qui disparait ne declenche plus rien et sa derniere `value` reste en place
  (persist compris). `globalFonctions.noteMesureModbus` (branches thermometres, analogiques,
  compteurs) et `cuveFonctions` (ADS1115) appellent `modbusFonctions.noteMesure` a **chaque** mesure,
  meme inchangee. Sans mesure depuis **3 TelePeriod** (90 s au moins ; 15 min avec TelePeriod 300),
  `executeCmdModbus` repond la sentinelle. **Delai de grace** au demarrage : pendant cette meme duree
  apres le boot, la derniere valeur enregistree est encore servie. Journal : `CAPTEUR_SANS_MESURE`
  en `erreur` une fois, puis `info` au retour.
- **Maitre** : `modbusFonctions.estSansMesure` -> `etatConstate = "defaillant"`, valeur precedente
  gardee, requete **acquittee** normalement (l'esclave repond : chien de garde non concerne).
  `MODBUS_TASMOTA_SLAVE_CAPTEUR` en `erreur` une fois, `info` a la premiere vraie valeur. Une reponse
  sans valeur (`Values` vide) n'est pas une sentinelle : elle suit le chemin d'erreur.
- **Sniffeur** : `decodeur_modbus.py` affiche `SANS MESURE (capteur absent ou defaillant)`.
- **Limite** : un contact sec (0x02) coupe ressemble a un contact ouvert ; seule une resistance de fin
  de ligne le rendrait detectable.
- Bancs : `banc_test_modbus.be` §26 (temoin : esclave sans sentinelle -> 2 echecs),
  `test_sniffeur_modbus.py` `test_decodeur`. **Pas encore observe sur la carte.**


### Ruban WS2812 d'un esclave — registre 1376, modes AUTO / MANUEL (2026-10-13)

Le ruban de la cuve est **gere par l'esclave** (`ledsFonctions`) : en AUTO sa couleur suit le
niveau, en MANUEL elle est figee (30 min par defaut, ou jusqu'au double appui). Le maitre P4 le
commande sans lui retirer cette gestion.

- **Lecture 0x03, 5 registres** (`modbusFonctions.etatRuban`) : teinte 0-360, saturation 0-100,
  luminosite 0-100 (0 = eteint), animation 0-14, **mode** (0 = AUTO, n = MANUEL encore n min,
  `0xFFFF` = MANUEL sans fin). L'esclave rend autant de registres que demande, borne a 3..5 :
  un maitre pas a jour (3 ou 4) reste compris. Meme contenu dans le push 0x10 (`surveilleRubans`) :
  le mode decroissant d'une minute, il part une fois par minute en MANUEL.
- **Ecriture 0x06, `[code, 0]`** : 01/02 = Power OFF/ON, 03 = animation (octet faible),
  **04 = couleur suivante** de la palette, **05 = retour en AUTO**. 04/05 ne touchent pas a Power et
  sont renvoyes en echo. Toute commande du maitre (01/02/03/04, 0x05 coil, 0x10 HSBColor) passe
  le ruban en MANUEL (`modbusFonctions.actionRubanMaitre`) ; sans ruban gere
  (`drivers.leds.environnement.leds.ruban` OFF) elle s'execute sans mode, et 04/05 sont journalises
  en `erreur` puis ignores.
- **Maitre** (`modBus_TasmotaSlaveModBus`) : le mode est recopie dans le relai virtuel
  (`modeRuban`). Commande `RubanEsclave<n> etat|auto|suivante` (n = POWERn du ruban), suivie d'une
  relecture 0x03. Bouton du maitre : cle `"bouton": <n>` du relai virtuel (P4 : Button2, GPIO22),
  appui court = `Power<n> TOGGLE`, double = 05, appui long = 04 puis une couleur toutes les
  `appuiLong` dixiemes de s jusqu'au relachement (16 crans au plus). Page du maitre
  (`ledsPanelFonctions`) : ligne du mode sous les curseurs, boutons *Couleur suivante* / *Auto*,
  pastille d'aide dans le coin du bouton du relai.
- Bancs : `banc_test_modbus.be` §29 (temoin : 05 traite en MANUEL, mode non recopie -> 3 echecs),
  `test_sniffeur_modbus.py` (decodeur et emulation). **Pas encore observe sur la carte** : la cuve
  et le P4 doivent etre televerses ensemble.


### Commandes sans fil vers les esclaves — une voie par destinataire (2026-10-15)

> **Statut : CONCEPTION, rien n'est code.** But : pouvoir commander les esclaves ESP32 (cuve,
> rideau) sans le cable RS485, la carte 16 relais restant cablee au P4.
> **Le ModBus filaire est CONSERVE pendant toute la mise au point** (decide le 2026-10-15) :
> le cable reste branche, `Serial` reste ON partout, et revenir au serie pour un esclave ne
> demande qu'un reglage, sans rebrancher quoi que ce soit.

**Pourquoi l'UDP et pas le TCP** (decide le 2026-10-15). La file (§7) apporte deja ce que le
TCP vendrait : un seul message en vol, accuse applicatif, timeout, renvoi borne. Le TCP y
ajouterait ses propres renvois (1 a 3 s) qui s'additionnent a ceux de la file, un flux sans
frontiere de trame (le prefixe `"ModbusTCP "` n'en donne pas, contrairement au MBAP), et des
connexions a moitie fermees a rouvrir apres chaque reboot d'esclave ou chute de l'AP. L'UDP est
un datagramme = une trame, livree ou perdue : la semantique exacte du RS485. Les doublons sont
sans danger : 0x05/0x06/0x10 ecrivent une valeur **absolue**, jamais une bascule.

**Principe.** Serie et UDP peuvent etre actifs ENSEMBLE sur le maitre ; ce qui est interdit,
c'est d'envoyer la MEME commande au MEME esclave par les deux voies. Chaque destinataire a
**une** voie :

| Destinataire | Voie | Ou c'est decide |
|---|---|---|
| Carte 16 relais (`Conn16channels`) | `Serial`, toujours | elle n'a pas d'IP |
| Esclave ESP32 (`TasmotaSlaveModBusN`) | `"Serial"` (defaut) ou `"UDP"` | **par l'esclave lui-meme**, annonce au maitre dans sa fiche discovery |

#### Ce que fait le code aujourd'hui (verifie le 2026-10-15)

1. **Aiguillage global** (`envoiMsgModbus`, `modbusFonctions.be:1307-1328`) : `typeComm.Serial`
   ON -> tout part en serie ; l'UDP ne porte commandes et reponses que si `Serial` est coupe.
   Couper `Serial` sur le P4 pour liberer les esclaves lui ferait perdre la carte 16 relais.
2. **L'UDP du maitre contourne la file.** Seul `envoiMsgModbusSerial` appelle `enfileMsg` ;
   `envoiMsgModbusUDP` emet tout de suite : ni `enVol`, ni timeout, ni renvoi. Une reponse UDP
   arrive donc sans requete en vol a apparier (`apparieReponse` rend `false`).
3. **Le maitre emet en multicast** (224.3.0.1), la ligne UniCast est commentee, et l'IP
   resolue dans `discovery.json` ne sert pas. Repli sur une IP en dur (`192.168.4.2`). Or le
   multicast Wi-Fi n'a **pas d'accuse 802.11** ni de renvoi MAC, et part au debit le plus bas :
   c'est la forme la plus perdante du Wi-Fi.
4. **L'esclave repond selon SA config, pas selon la voie d'arrivee** : ses reponses passent
   par `envoiMsgModbus(paramMSG, "Reponse", ...)` (`:1864` a `:2038`), meme aiguillage global.
   Un rideau interroge en UDP avec `Serial` ON repondrait sur le RS485.
5. **Une reponse UDP en retard peut acquitter la requete SUIVANTE** du meme esclave :
   `apparieReponse` ne compare que `DeviceAddress` et `FunctionCode` (risque deja note en
   commentaire, `:1320-1325`).

#### Les modifications

**M0 — Esclave : il annonce sa voie dans sa fiche discovery** (decide le 2026-10-15 : c'est
l'esclave qui la declare, pas le persist du maitre). Nouvelle cle `drivers.ModBus.voieCommandes`
(`"Serial"` | `"UDP"`, defaut `"Serial"`) dans le persist de l'esclave ; `discoveryFonctions.be`
(seul ecrivain du bloc `ModBus` de la fiche, `:273-305`) la publie en
`fiche.ModBus.voieCommandes`. Elle arrive au maitre par la voie habituelle de la fiche
(`forceEnvoiParams` au demarrage, `ImAlive` toutes les 5 min). Pour basculer sans attendre :
sous-commande esclave `ReglageModbus VoieCommandes Serial|UDP`, qui enregistre le persist puis
renvoie aussitot la fiche (`forceEnvoiParams`).

**M1 — Maitre : voie par destinataire.** Nouvelle `modbusFonctions.voieDe(adresse)` : `"UDP"` si
la fiche discovery de l'esclave d'`ModBus.id == adresse` porte `voieCommandes: "UDP"` ; sinon
`"Serial"` — y compris fiche absente (maitre qui vient de redemarrer, esclave jamais annonce) :
le cable etant conserve, le serie est le repli **sur**. Carte 16 relais : toujours `"Serial"`.
`fichesModbus()` relit et parse `/json/discovery.json` a chaque appel : `voieDe` garde les voies
en cache dans `modbusFonctions.etat()`, relu au plus toutes les 60 s. Dans `envoiMsgModbus`,
branche maitre : **tout** message (serie comme UDP) passe par `enfileMsg`, l'item recoit
`"voie"`. Si `typeComm[voie]` est OFF sur le maitre : message rejete, log `erreur` (plus de repli
silencieux). Les branches esclave, TCP et push sont inchangees.

**M2 — Maitre : la file emet selon la voie de l'item.** `envoieTete` :
`Serial` -> `ModBusSend` comme aujourd'hui ; `UDP` -> `prepareTrame` puis envoi **UniCast** a
l'IP de l'esclave (regle ci-dessous). IP introuvable = echec d'envoi (meme chemin que
`ModbusSend=Failed` : renvoi borne avec backoff, log `erreur`) — **plus d'IP en dur**.

*Pourquoi UniCast* (point 6 de `ANALYSE_BERRY_MODBUS_DISCOVERY.md`) : seule une trame UniCast
est acquittee et renvoyee par la couche radio 802.11 ; le multicast part sans accuse, au debit
le plus bas, peut etre differe jusqu'a la balise DTIM de l'AP si l'esclave economise son Wi-Fi,
et fait decoder chaque commande par tous les esclaves.

*Quelle IP — la plus fraiche d'abord* :
1. **IP apprise** : a chaque trame UDP **valide** recue d'un esclave (push accepte par
   `accepteSeq`, ou reponse), le maitre note `ipEsclaves[DeviceAddress] = {ip: Info.remote_ip,
   ms: tasmota.millis()}` dans `modbusFonctions.etat()`. C'est l'adresse source reelle, revue
   toutes les ~30 s par les push. Retenue tant qu'elle a moins de **3xT = 90 s** (meme borne
   que le chien de garde : au-dela, l'esclave est deja « inconnu »).
2. **Sinon, la fiche `discovery.json`** (`fichesModbus()`, `IPAddress` du role), rafraichie par
   `ImAlive` toutes les 5 min.
3. **Sinon, echec d'envoi.**
Une trame en erreur (CRC, longueur) ou rejetee par `accepteSeq` n'apprend rien. Pas
d'authentification : un appareil de l'AP qui forgerait une trame d'adresse 2 detournerait les
commandes de la cuve — meme exposition qu'aujourd'hui (rien n'est signe), a garder en tete.

*Timeout et file* : nouvelle cle `drivers.ModBus.timeoutReponseUDP` (defaut 2000 ms ; la cuve repond en 0,3 s) au lieu des
5000 ms + `MARGE_TIMEOUT_MS` dimensionnes pour le pont serie. **Une seule file, un seul en vol
pour les deux voies** : le volume est negligeable (< 0,1 trame/s, voir « Rythmes et budget »)
et c'est l'invariant le plus eprouve du code. `pause` (test de debit) bloque aussi l'UDP :
accepte, c'est rare.

**M3 — Numero de transaction sur l'UDP.** Enveloppe `"ModbusUDP <tid> <trame hexa>"`, comme
`"ModbusPushUDP <seq> <hexa>"`. `tid` = 0..255, compteur du maitre, attribue a l'item a son
**premier** envoi et garde pour ses renvois : la reponse tardive au 1er essai acquitte le meme
item (meme requete, ecriture idempotente), celle d'un item precedent est rejetee.
- `udpFonctions.lireUDP` : 2 morceaux apres l'enveloppe -> `tid` + hexa ; 1 seul -> ancien
  format, `tid` absent. Le `tid` voyage dans `Info` (`{"remote_ip": ip, "transaction": tid}`),
  deja serialise par `lireMsgModbus` : pas de changement du format publie.
- `apparieReponse` : si l'item en vol porte un `tid`, la reponse doit porter le meme, sinon
  rejet (log `debug`). Un esclave pas a jour (sans `tid`) serait donc rejete : d'ou l'ordre de
  mise en oeuvre ci-dessous, **esclaves d'abord** (ils renvoient le `tid` avant que le maitre
  ne l'exige). Items serie : regle actuelle inchangee.

**M4 — Esclave : repondre par la voie d'arrivee.** La reponse reutilise la requete recue
(`paramMSG`), qui porte `Info.remote_ip` quand elle vient de l'UDP. Dans `envoiMsgModbus`,
`typeMsg == "Reponse"` : si `Info.remote_ip` existe -> reponse **UniCast** a cette IP avec
`"ModbusUDP <tid> <hexa>"` (le `tid` recu, renvoye tel quel), et **rien** sur le serie ni en
multicast ; sinon, comportement actuel. Corrige le point 4 meme pendant une migration ou
l'esclave garde `Serial` ON. Les push (`ModbusPushUDP`, `pousseEtat`) ne sont pas touches.

**M5 — Persists** (regle du 2026-10-06 : une nouvelle cle va dans TOUS les persists qui portent
le bloc) : `"voieCommandes": "Serial"` et `"timeoutReponseUDP": 2000` dans `drivers.ModBus` des
8 persists qui ont ce bloc (bureau, cave x2, grenier, S3 garage, P4, cuve, rideau) — chaque
module peut etre maitre ou esclave selon son `id`. Rien dans `TasmotaSlaveModBusN` du maitre.
`"UDP"` ne se pose que sur la cuve puis le rideau, aux etapes E3/E4, par `ReglageModbus`.

**M6 — Bancs.** `banc_test_modbus.be` : la verif « methode inchangee MultiCast|192.168.4.1 »
(§ envoiMsgModbusUDP) devient UniCast vers l'IP de la fiche ; nouvelles sections : aiguillage
(carte relais en serie + esclave en UDP dans la meme file), timeout UDP, IP absente -> renvoi,
choix de l'IP (apprise < 90 s prime sur la fiche ; apprise perimee -> fiche ; temoin : trame
en erreur CRC ou push rejete par `accepteSeq` -> l'IP apprise ne doit PAS changer),
appariement par `tid` (temoin : reponse au `tid` precedent -> doit etre rejetee), reponse
esclave par la voie d'arrivee (temoin : `Serial` ON + requete UDP -> rien sur le serie).
`test_discovery.be` §13 : enveloppe `ModbusUDP` a 2 et 3 morceaux ; fiche : `voieCommandes`
publiee (contrat ecrivain reel -> `voieDe`, regle du 2026-09-30 ; temoin : cle absente -> Serial).

#### Ordre de mise en oeuvre — chaque etape se flashe et s'observe seule (2026-10-15)

Le cable reste branche de bout en bout : a chaque etape, le retour arriere est un reglage.

| Etape | Cartes | Contenu | Effet visible | Retour arriere |
|---|---|---|---|---|
| **E1** | cuve, rideau | M0 (annonce, `Serial`), M4 (reponse par la voie d'arrivee), M3 cote esclave (lire et renvoyer le `tid`), M5 | **aucun** : le maitre envoie encore tout en serie | reflasher |
| **E2** | P4 | apprentissage des IP + `voieDe`, **en lecture seule** : log `info` de la voie annoncee et de l'IP retenue par esclave, envoi toujours en serie | les logs disent quelle IP et quelle voie le maitre utiliserait | reflasher |
| **E3** | P4 | M1 + M2 + M3 (file multi-voies, UniCast, `tid`, `timeoutReponseUDP`) ; puis `ReglageModbus VoieCommandes UDP` sur la **cuve** seule | commandes et releves de la cuve en UDP, rideau et carte relais en serie | `ReglageModbus VoieCommandes Serial` sur la cuve |
| **E4** | rideau | `ReglageModbus VoieCommandes UDP` | rideau en UDP | idem sur le rideau |
| E5 | — | debrancher le cable (decision a part, apres observation) | — | rebrancher |

**E1 — CODE le 2026-10-15, non flashe.** `discoveryFonctions.be` (M0), `udpFonctions.lireUDP`
(M3), `modbusFonctions.envoiMsgModbus` + `repondUDP` (M4), `ReglageModbus VoieCommandes`
(`reglageVoieCommandes`), 8 persists (M5), schema regenere. Bancs : `banc_test_modbus.be` §30
(238/238), `test_discovery.be` §7 (contrat) et §16 (121/121) ; temoins par mutation sur copie
complete de `data/fs` : M4 sans test de `Info.voie` -> echec du temoin « forme TCP » ; lireUDP
sans tid -> echec « tid 17 ». **Reste avant flash : `solidifie_et_compile_berry.py` sur les 3
modules (non lance : un build tournait).**

**Unicast / multicast selon Range Extender ou Wi-Fi classique** (remarque de l'utilisateur,
constatee par essais ; code relu le 2026-10-15, `udpFonctions.envoiUDP` `:466-512`) :
- **Multicast : les montages different, confirme par le code.** Il n'est emis QUE si
  `serveur.rangeExtender.activation` = ON : maitre (udp.id 0) -> socket lie a l'adresse de
  l'interface AP (`begin("192.168.4.1", 0)`) puis `send` vers 224.3.0.1:4000 ; esclave ->
  `begin_multicast` + `send_multicast`. **Range Extender OFF : aucune branche, rien ne part**
  (`resultatEnvoi` reste nil, sans log d'echec).
- **Unicast : aucune difference dans le code** (`begin("", 2000)` puis `send(ip, 2000)`, ecoute
  `begin("", 2000)` sur toutes les interfaces). En theorie la pile IP choisit l'interface par
  la destination (192.168.4.x -> AP du maitre, LAN -> STA), donc rien a distinguer — **a
  confirmer en reel**, l'experience de l'utilisateur disant le contraire. Point suspect a
  observer : le socket d'EMISSION se lie au port 2000, celui de l'ECOUTE ; une reponse qui
  arriverait pendant sa courte vie pourrait lui etre remise, puis perdue a sa fermeture.
- E1 ne s'appuie que sur l'unicast (reponse de l'esclave a `Info.remote_ip`).

**Essai reel E1** (intervention de l'utilisateur ; logs `ReglageLog modbus detail` et
`ReglageLog udp detail` sur les deux cartes) :
1. *Range Extender* (P4 + cuve, flashes avec E1 ; inerte pour le reste) : console du P4,
   `ReglageModbus envoiMessageUDP <IP cuve 192.168.4.x> ModbusUDP 17 020100E00001FC0F`
   (lecture 0x01 du relai 1 de la cuve). Attendu cote cuve : `REPOND_UDP: reponse a
   192.168.4.1 : ModbusUDP 17 02010101900C` (ou `...0051CC` si POWER1 OFF) ; cote P4 :
   `LIRE_UDP: Donnees UDP UniCast recues de '192.168.4.x'` avec ce message ; sniffeur ModBus du
   PC : **rien** sur le RS485 a cet instant. Temoin : meme commande sans `17` -> reponse sans tid.
2. *Wi-Fi classique* : seul le P4 y est (2026-10-15) ; la **cuve y passe le temps de l'essai**,
   par `ReglageGlobal ModeConnexion WifiClassique <ssid> <mdp>` (2026-10-16, `globalFonctions.be`) :
   reseaux d'origine memorises une fois (`serveur.wifi.sauvegardeRangeExtender`), `reseau1` =
   reseau maison, `reseau2` = `SERVEUR-GARAGE-GATEWAY` (filet), `rangeExtender.activation` = OFF,
   persist sauve, puis `Restart 1` differe d'1 s. Retour : `ReglageGlobal ModeConnexion
   RangeExtender` (restaure les reseaux memorises). Ni `RgxState` ni le point d'acces ne sont
   touches. Ecrit dans `ReglageGlobal` et non `ReglageRangeExtender` : `controleRangeExtender`
   n'est pas charge sur la cuve ni le rideau. L'outil `outils_pc/testeur_udp.py` envoie ces
   commandes par la serie. Banc : `test_discovery.be` §17 (temoins par mutation : garde de la
   sauvegarde, Restart differe).
   Pendant l'essai, **attendu et non une panne** : la cuve n'emet plus AUCUN multicast (pas de
   branche hors Range Extender, voir plus haut) -> ni `ImAlive` UDP ni push ; sa fiche arrive
   par MQTT (broker joint directement), ses mesures par le releve serie du maitre (cable branche).
3. Si 1 ou 2 echoue : relever l'adresse et le port source vus de chaque cote, puis essayer
   l'emission depuis le socket d'ecoute (hypothese du port 2000 ci-dessus) avant tout autre
   changement.

**Essai reel 1 — 2026-10-17** (testeur UDP ; P4 SANS E1, cuve AVEC E1 mais sans `ModeConnexion`) :
- **P4 -> cuve : OK.** `ModbusUDP 17 020100E00001FC0F` recu sur le port 2000, `REPOND_UDP: reponse a
  192.168.4.1 : ModbusUDP 17 0201010051CC` (tid garde, POWER1 OFF), aucune copie sur le RS485. M3/M4
  de l'esclave sont valides. Deux echecs P4 -> cuve a 03:52-03:53, puis plus aucun : non explique.
- **Cuve -> P4 (192.168.4.1) en unicast : rien n'arrive.** La reponse E1 ne revient donc pas.
  Explication complete et mesures : « Diagnostic UDP — 2026-10-17 » ci-dessous (premiere analyse
  « les envois restent chez elle » : FAUSSE, ils partent par la mauvaise interface). Le multicast,
  lui, passe dans les deux sens (echecs du matin non reproduits).
- Hypothese du port 2000 (ci-dessus) **ecartee** : un socket neuf lie a 2000 sur le P4 atteint la cuve.
- Piege de mesure : Tasmota coupe le log serie 600 s apres le demarrage (`SERIALLOG_TIMER`,
  `support_tasmota.ino:1186`) sauf commande `SerialLog` ; `logFonctions.appliqueProfil` n'en envoie
  pas si le niveau est deja le bon. Cuve muette des 03:33:21 : les essais suivants semblaient
  « non recus ». Le testeur reapplique desormais le niveau regle a l'ouverture du port.

**Diagnostic UDP — 2026-10-17, 04:39-04:44** (testeur UDP, P4 = COM4, cuve = COM12 ; sockets
Berry de test sur 2996-2998, toutes refermees ; aucune commande de configuration). Remplace
l'explication « restent chez elle » de l'essai reel 1 : les envois partent, mais par la mauvaise
interface.

*Mesures.* Cuve : `RgxState` ON, `RgxSSId` = 192.168.4.1 / 255.255.255.0 ; STA 192.168.4.2/24.

| Essai | Resultat |
|---|---|
| cuve, socket `begin("",0)` -> 192.168.4.1:2997 | non recu |
| cuve, socket `begin("192.168.4.2",0)` (liee a la STA) -> 192.168.4.1:2997 | **recu** par le P4 |
| cuve, socket `begin("",0)` -> 192.168.0.43:2997 (IP STA du P4) | **recu** |
| cuve, framework `ReglageUDP envoiUniCast 192.168.4.1 ...` | non recu |
| cuve -> 192.168.4.1:2996, ecoute locale sur 2996 | non reboucle (127.0.0.1 : reboucle) |
| multicast cuve -> P4, framework (4000) et socket neuve (2998) | **recu** |
| multicast P4 -> cuve, framework | **recu** |
| unicast P4 -> cuve, framework, 5 envois | **5/5** |

*Cause prouvee : chevauchement de sous-reseau sur l'esclave.* Une socket non liee choisit
l'interface par `ip4_route` : la 1re interface dont le sous-reseau contient la destination
(`lwip/src/core/ipv4/ip4.c:171-178`). L'AP de la cuve est demarre apres sa STA
(`xdrv_58_range_extender.ino:499`) ; `netif_add` le place en tete (`netif.c:437-438`). Le paquet
pour 192.168.4.1 sort donc par l'AP de la cuve : ARP vers sa propre adresse, perdu. Pas de
rebouclage : avec `IP_NAPT`, le bloc « packet to self » est compile hors (`ip4.c:1061-1079`).
Une socket liee a 192.168.4.2 passe par le crochet ESP-IDF `ip4_route_src_hook`
(`components/lwip/port/hooks/lwip_default_hooks.c:122-142`) : la STA est choisie. Vers
192.168.0.43, aucune interface ne correspond : sortie par `netif_default` (STA, `route_prio` 100,
`esp_netif_defaults.h:54`), le P4 accepte une adresse de son autre interface (`ip4.c:616-636`).
Sources lues : `framework-espidf` 5.5.4 ; options lues dans le `sdkconfig` et le `lwipopts.h`
precompiles (`CONFIG_LWIP_IPV4_NAPT=y`, `LWIP_HOOK_IP4_ROUTE_SRC`, identiques S3 et P4).

*Consequences.*
- Esclave -> maitre en unicast : perdu tant que l'esclave a son AP en 192.168.4.1/24 (cuve, et
  rideau par la meme config). La reponse E1 (`repondUDP`, `modbusFonctions.be:1546-1555`, vers
  `Info.remote_ip` = 192.168.4.1) ne peut pas revenir. Le TCP n'est pas touche (socket acceptee
  liee a 192.168.4.2 : deduit du code, non mesure).
- Le multicast marche en Range Extender dans les deux sens. Les echecs multicast du matin et
  P4 -> cuve de 03:52-03:53 ne sont pas reproduits ; piste : log serie de la cuve coupe
  (redemarree vers 03:23, `SERIALLOG_TIMER`), non prouve.
- Le commentaire `controleUDP.be:16-19` dit l'inverse du code et des mesures : ce n'est pas le
  mode (RE / Wi-Fi) qui decide, c'est le chevauchement.

*Defauts du code releves.*
- `udpFonctions.be:485` : le multicast du maitre est lie a 192.168.4.1 -> il ne sort que par son
  AP. En Wi-Fi classique, `Timestamp`, `ipMaitre` et `ModbusUDP` multicast
  (`modbusFonctions.be:1533`) n'atteignent pas un esclave sur la box.
- `udpFonctions.be:483-490`, `:499-506`, `:233-240` : aucun multicast esclave hors Range Extender
  (deja note plus haut).
- `udpFonctions.be:479` : socket d'emission liee au port d'ecoute 2000. Pendant sa vie, elle est
  en tete de `udp_pcbs` (`udp.c:298`) et capte un datagramme entrant (`udp.c:267`), perdu a sa
  fermeture. Non observe.
- `udpFonctions.be:592` : un message UDP d'un seul mot leve `index_error` (`params[1]`).
- Les sockets d'ecoute s'ouvrent sur `System#Boot`, leve a la 1re connexion MQTT
  (`xdrv_02_9_mqtt.ino:1487`) : broker injoignable au demarrage = carte sourde en UDP. Non mesure.
- L'ecoute multicast rejoint le groupe sur les interfaces presentes a l'instant
  (`NetworkUdp.cpp:131`, `igmp.c:455-480`) : si l'AP du maitre demarrait apres `System#Boot`,
  il serait sourd au multicast sur son AP. Non constate sur le boot en cours du P4.

*Corrections.* **C1, C2, C6 APPLIQUEES le 2026-10-17** (accord de l'utilisateur) dans
`udpFonctions.envoiUDP` / `ipSTA` / `emet` / `lireUDP` ; format du log `ENVOI_MSG_UDP: Donnees ...`
inchange (lu par le testeur), interface choisie dans une ligne `detail` a part. Banc
`test_discovery.be` §18 : 158/158 ; sur l'ancien `udpFonctions.be`, 7 echecs, tous en §18 (C1/C2/C6) ;
`banc_test_modbus` 238/238 ; `solidifie_et_compile_berry.py udpFonctions.be` : rc 0. **C3, C4, C5 NON
appliquees, a trancher** (leur code est dans le diff ci-dessous, qui reste la reference).
Proposition d'origine :
`tasks/correctif-udp-interface-2026-10-17.diff`, dans `udpFonctions.be` seulement.
- C1 : esclave, socket d'emission liee a l'IP de sa STA (`tasmota.wifi()["ip"]`), unicast et
  multicast ; 2e essai sur toutes les interfaces si la liaison est refusee.
- C2 : port source aleatoire (0) pour toutes les emissions.
- C3 : multicast du maitre lie a l'IP de l'AP du persist (`serveur.rangeExtender.AP.IPAddress`),
  sinon a sa STA ; plus de 192.168.4.1 en dur dans `envoiUDP`. Complete le 2026-10-17
  (`interfacesMulticastMaitre`) : par l'AP s'il est actif (inchange) ET par la STA, mais seulement si
  la decouverte connait un esclave joignable par la box (`esclavesBox` : meme groupTopic, Online, IP
  du /24 de la STA hors du /24 de l'AP) ; sans AP ni esclave box, rien n'est emis (`Non emis`).
- C4 : multicast esclave aussi en Wi-Fi classique (a trancher : c'est la question « push en
  multicast ou en unicast »).
- C5 : reponse a `ImAlive` (`Timestamp`, `ipMaitre`) en unicast a `IPAddress` de la fiche ;
  multicast par l'AP si la fiche n'a pas d'IP.
- C6 : `lireUDP` accepte un message d'un seul mot.
Aucun changement de point d'acces : le sous-reseau AP distinct par esclave a ete refuse le
2026-10-03 et n'est plus necessaire (C1 contourne le chevauchement, mesure a l'appui).
`udpFonctions` est solidifie : rebuild complet et flash des 3 cartes (P4 aussi : il n'a pas E1).
Bancs : `test_discovery.be` §18 (17 tests ; correctif 160/160, ancien code 13 echecs, tous en §18),
bouchon `tasmota.wifi()` ajoute ; `banc_test_modbus.be` 238/238 inchange.

*Essais apres flash.* Essai 1 (Range Extender) : cuve `ReglageUDP envoiUniCast 192.168.4.1
TESTUDP-1` -> P4 `LIRE_UDP: ... recues de '192.168.4.2'` ; E1 : P4 `ReglageModbus envoiMessageUDP
192.168.4.2 ModbusUDP 17 020100E00001FC0F` -> cuve `REPOND_UDP: reponse a 192.168.4.1 ...` puis
`ENVOI_MSG_UDP: ... par '192.168.4.2' ... OK` -> P4 `LIRE_UDP: msg = ModbusUDP 17 ...`. Temoin :
socket non liee depuis la cuve vers le P4 -> toujours non recu. Essai 2 (Wi-Fi classique) :
unicast dans les deux sens et E1 vers l'IP box de la cuve ; multicast cuve -> P4 recu seulement si
la box relaie le multicast (a consigner tel quel) ; multicast P4 -> cuve : rien (attendu).
Detail ligne par ligne : `outils_docs/DIAGNOSTIC_UDP_2026-10-17.md` §7.

Pourquoi cet ordre : E1 et E2 ne changent **aucun** comportement, on y verifie l'annonce et le
choix d'IP sur le vrai reseau avant qu'une seule commande en depende. Esclaves avant maitre :
le `tid` est renvoye avant d'etre exige (M3). La cuve avant le rideau : une commande perdue y
coute un ruban mal colore, pas une porte de garage.

#### Hors perimetre, a trancher plus tard

- Passer aussi les **push** esclave -> maitre en UniCast (meme defaut du multicast Wi-Fi) ;
  mais `ecoute_udp.py` et le relais MQTT du maitre s'appuient sur le groupe 224.3.0.1.
- Voie de **secours** (UDP puis serie pour un meme esclave) : exigerait un dedoublonnage par
  `tid` cote esclave. Non retenu.
- Sniffeur ModBus PC : ne voit plus que la carte 16 relais une fois les esclaves en UDP.
