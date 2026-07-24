# Protocole ModBus — référence du fork

> Doc créée le 2026-07-16. Couvre le ModBus **standard** (RTU/TCP), l'**implémentation
> maison** (3 transports Série/UDP/TCP), l'**extension esclave→maître**, et le **design de
> file d'attente (queue)** décidé pour le maître.
> Fichiers : `data/fs/modbusFonctions.be` (logique), `data/fs/controleModbus.be` (driver),
> `data/fs/modBus_TasmotaSlaveModBus.be` (Tasmota esclave), `data/fs/modBus_Conn16channels.be`
> (relais 16 canaux). Aide utilisateur : `data/fs/ModBus.help`.

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
  Un seul en vol, FIFO, timeout a nom unique, retry borne (`MAX_TENTATIVES=3`).
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

---

## 8. La carte 16 relais RS485 — carte des registres (2026-07-24)

Source : `outils_docs/Electronique/Connecteur ModBus/16 Channel Multifunction RS485
Module commamd.docx` et `... Manual.docx`. **Verifie dans la doc constructeur, pas deduit.**

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
| File FIFO | **oui**, un seul en vol | **jamais** |
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

