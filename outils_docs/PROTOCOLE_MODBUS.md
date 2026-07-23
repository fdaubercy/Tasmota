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
4. Interop : garder le dialecte texte maison, ou ajouter un vrai mode ModBus TCP standard
   (MBAP) pour du materiel tiers.
