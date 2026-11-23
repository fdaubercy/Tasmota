# Sniffeur I2C

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Sniffeur I2C (page web)

Voir en direct ce qui passe sur le bus I2C de n'importe quelle carte du parc, décodé jusqu'au registre des puces
connues, et lire ou écrire un registre. Tasmota ne sait pas écouter un bus I2C (son contrôleur est maître, ou
esclave d'une seule adresse) : l'écoute est faite par un **ESP32-S3 DevKit dédié** (pas une carte du parc) qui
fait tourner un petit firmware et envoie une ligne par transaction sur son USB. Conception :
[docs/superpowers/specs/2026-10-31-sniffeur-i2c-design.md](../../docs/superpowers/specs/2026-10-31-sniffeur-i2c-design.md).

### Matériel et câblage

| Sniffeur (ESP32-S3) | Bus observé |
|---|---|
| GPIO4 | SDA |
| GPIO5 | SCL |
| GND | GND (indispensable) |

- **Bus en 3,3 V seulement** : les entrées de l'S3 ne supportent pas 5 V.
- Le sniffeur n'ajoute aucune résistance de tirage et n'émet rien en écoute : il ne change rien au bus.
- Au PC : le port **USB natif** du DevKit (marqué « USB »), pas le port « UART ».
- Broches à changer : `build_flags` (`BROCHE_SDA`, `BROCHE_SCL`) de
  [firmware_sniffeur_i2c/platformio.ini](../firmware_sniffeur_i2c/platformio.ini).

### Flasher le firmware (une fois)

```
pio run -d outils_docs/firmware_sniffeur_i2c -t upload --upload-port COMn
```

Projet PlatformIO **autonome** (même plateforme et même framework que Tasmota, déjà installés), mais c'est un
`pio run` : **jamais pendant un build Tasmota** (le hook `garde_build` le refuse). Le cœur 1 de l'S3 lit les
broches en continu, sans interruption ; c'est pourquoi le firmware coupe le chien de garde des interruptions du
cœur 1, et le commentaire de tête de `src/main.cpp` dit pourquoi. La machine à états I2C (`src/machine_i2c.h`)
a son banc sur PC : `python outils_docs/firmware_sniffeur_i2c/banc/lance_banc.py` (code 0 = vert ; g++ ou Build
Tools Visual Studio).

### Lancer la page

Tuile « Sniffeur I2C » de l'annuaire (groupe « Bus et cartes »), tâche VS Code « Outil : sniffeur I2C », cible
Custom « Sniffeur I2C (HTTP 127.0.0.1) », ou :

```
%USERPROFILE%\.platformio\penv\Scripts\python.exe outils_docs/scripts_python/outils_pc/sniffeur_i2c.py
```

`--port auto` (défaut) interroge par `?` les ports USB Espressif et Raspberry Pi, et ne garde que celui qui
répond comme un sniffeur : une carte Tasmota branchée en USB est écartée. Le port s'ouvre sans DTR/RTS.

### Vitesse

- **100 kHz** (défaut de Tasmota) : garanti.
- **400 kHz** : dépend de la vitesse d'échantillonnage affichée dans la barre du haut (en MHz ; il faut environ
  4 MHz). À vérifier sur le bus réel. Si des transactions sont **perdues** ou **tronquées** en nombre, l'S3 ne suit
  pas : rester à 100 kHz (le Pico, plus tard, tiendra 400 kHz avec le même protocole).

### Ce que montre la page

- **Fil** : adresse, W/R, octets, NACK, fin (STOP, RESTART, TRONQUE), fréquence de SCL, puce, registre et valeur
  traduite. Puces décodées : ADS1115, MCP23017, TCA9554, DS3231, MPU6050, ES8311 (noms seuls).
- **Carte observée** : deux puces partagent 0x20 (MCP23017, TCA9554) et 0x68 (DS3231, MPU6050). La carte choisie
  donne ses puces actives, lues dans son `_persist.json`. Sans carte, la trame est marquée ambiguë, jamais mal nommée.
- **Filtres** (adresse, écritures, lectures, NACK seuls, texte), **pause**, **inventaire** par adresse (transactions,
  NACK, fréquence), **alertes** (NACK répétés, trame tronquée, pertes du sniffeur, bus bloqué).
- **Journal** continu : `%LOCALAPPDATA%\outils_tasmota\sniffeur_i2c\sniffeur_i2c_<date>.log` (30 jours) ;
  **export** .txt / .json.

### Lire ou écrire un registre (onglet « Envoi »)

- **Par la carte** (bus en service) : la carte, seul maître du bus, reçoit par HTTP ou par MQTT
  `Br (wire1.detect(0x48) ? wire1 : wire2).read(0x48, 0x01, 2)` (ou `.write(...)`). `wire1`/`wire2` plutôt que
  `tasmota.wire_scan`, qui rend `nil` pour une puce déjà prise par un pilote C de Tasmota. L'IP est proposée
  d'après le dépôt (`WIFI_IP_ADDRESS`, ou `<ip du maître>:<port>` pour un esclave du range extender, qui exige le
  `RoutageRangeExtender` du maître). **Voie MQTT** (liste « par ») : `cmnd/<topic>/Br`, réponse lue sur
  `stat/<topic>/RESULT`, par le broker de `user_config_override.h` ; topic proposé d'après le `_persist.json` de la
  carte observée, et voie choisie d'office pour un esclave (il joint le broker par la sortie du maître). La commande
  est **montrée avant l'envoi**, une seule à la fois, et toute écriture demande une confirmation. Le fil dit
  ensuite « trame vue » ou « trame NON VUE » (sniffeur branché sur un autre bus).
- **Par le sniffeur** (au banc) : le sniffeur devient maître à 100 kHz, **uniquement sur un composant débranché de
  sa carte** (case à cocher). Le firmware refuse si le bus a vécu dans les 2 dernières secondes.

### Bancs

- `outils_pc/test_sniffeur_i2c.py` (Python de PlatformIO, code 0 = vert) : protocole, décodeur, alertes,
  rapprochement, mode maître, port perdu, journal, HTTP. Les trames du décodeur viennent des fiches techniques
  (marquées PROVISOIRE) en attendant des captures réelles.
- `outils_pc/test_sniffeur_i2c_page_chrome.py` : la page dans un vrai Chrome (faux sniffeur, aucun port COM).
- `firmware_sniffeur_i2c/banc/lance_banc.py` : la machine à états du firmware.

<hr></hr>
