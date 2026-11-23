# Sniffeur ModBus

Port : 7300. Cible PlatformIO : `sniffeur_modbus` (Custom). Tâche VS Code : « Outil : sniffeur ModBus (http://127.0.0.1:7300) ».

## Lancer

Avec le Python de PlatformIO (`pyserial`) :

```
%USERPROFILE%\.platformio\penv\Scripts\python.exe outils_docs/scripts_python/outils_pc/sniffeur_modbus.py --port auto --debit 19200 --http 7300
```

Options (`sniffeur_modbus.py::main`) :

- `--port auto|COM12|loop://|aucun` : `auto` prend le seul convertisseur CH343 présent, sinon le port se choisit sur la page.
- `--debit 19200`, `--http 7300`, `--silence 0.02` (silence qui clôt une trame), `--delai 1.0` (au-delà, requête sans réponse).
- `--echo auto|oui|non`, `--journal fichier.log`, `--historique 5000`.
- `--persist p4|affichage|<chemin d'un _persist.json>` : maître du bus, pour décoder selon les adresses des esclaves.
- `--udp oui|non` (+ `--udp-groupe`, `--udp-port`, `--udp-interface`) et `--mqtt oui|non` (+ `--mqtt-hote`, `--mqtt-port`...) pour le push des esclaves.
- `--local`, `--sans-navigateur`.

Pendant un build, lancer le script en Python direct, jamais la cible PlatformIO. Depuis un autre appareil, utiliser le lien à jeton de la console.

## Ce que fait la page

- Écoute le bus RS485 sans émettre : chaque trame est découpée (CRC) et décodée champ par champ selon la norme, puis selon l'esclave visé (carte 16 relais ou ESP32 `TasmotaSlaveModBus`).
- Apparie requêtes et réponses : latence par esclave, requêtes sans réponse, exceptions, CRC faux.
- Surveille l'écart entre l'état commandé d'un relais et son relevé, et les collisions (deux maîtres, réponse non sollicitée, rafale de CRC faux) : alertes dans le fil.
- Port et débit réglables (Fermer libère le port), envoi de trames avec CRC ajouté, raccourcis de la carte 16 relais, recherche et correction de son débit et de son adresse.
- Émulation des esclaves du persist (carte relais, cuve, rideau) avec valeurs éditables.
- Écoute en lecture seule le push UDP `ModbusPushUDP` des esclaves et le juge comme le maître (accepté, écarté, perdu, redémarrage).
- Onglet Aide : règles de formation des trames, registres de l'installation, décodeur manuel.

## Pièges

- Un seul maître sur le bus : envoyer depuis la page fait du PC un maître. Si le P4 sonde en même temps, les trames se percutent. Charger `test_liaison_modbus.be` sur le P4 (il suspend sa file) ou le débrancher. Pour l'émulation, débrancher l'esclave réel émulé.
- Écho local : certains convertisseurs renvoient ce qu'ils émettent. Une réponse 0x05 ou 0x06 est la copie exacte de la requête, donc `--echo auto` l'apprend au premier envoi d'une trame qui n'est pas 0x05 ou 0x06.
- Les esclaves derrière le point d'accès du maître (NAPT) ne font pas arriver leur multicast au PC : leurs push passent par MQTT si `ReglageModbus RelaisPushMQTT ON` est posé sur le maître.
- Ne jamais émettre vers 224.3.0.1:4000 depuis un essai : le vrai maître traiterait un faux push. Le sniffeur n'émet rien vers ce groupe.
- Les POST de la page exigent l'en-tête `X-Sniffeur: 1`.
- Sans `--journal`, aucune trame n'est gardée sur disque (la cible PlatformIO écrit `%TEMP%\sniffeur_modbus.log`).

## Bancs

```
PYPIO outils_docs/scripts_python/outils_pc/test_sniffeur_modbus.py
```

Tous les groupes, dont un fuzz de 20 000 trames. Il appelle `test_sniffeur_modbus_acces.py`, qui n'est pas autonome. UDP sur un groupe et un port de test en TTL 0 : rien ne sort du PC. Code de sortie 0 = vert.

`test_rs485_pc.py` n'est pas un banc : c'est l'outil du bus réel, qui demande le convertisseur branché.
