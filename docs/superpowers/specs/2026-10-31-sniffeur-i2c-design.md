# Sniffeur I2C — conception

Date : 2026-10-31. Statut : à valider par l'utilisateur, puis plan au format `tasks/plans/_FORMAT.md`
(`tasks/plans/sniffeur-i2c.md`).

## 1. Intention

Un **outil d'atelier général**, sans panne précise à traquer : brancher trois fils sur le bus I2C de
n'importe quelle carte du parc et voir en direct ce qui y passe, décodé jusqu'au registre des puces
connues ; et pouvoir lire ou écrire un registre d'une puce. Il rejoint la famille des outils PC de
l'annuaire (http://127.0.0.1:7600), sur le modèle du sniffeur ModBus.

## 2. Décisions de l'utilisateur (2026-10-31)

| Sujet | Décision |
|---|---|
| Usage | Outil général, pas de cas précis. |
| Matériel | **Deux voies** : d'abord un **ESP32-S3 DevKit de rechange** (l'utilisateur en a un), plus tard un **Raspberry Pi Pico (RP2040)**, avec le **même protocole série** : l'outil PC ne change pas. |
| Décodage | Trames + composant nommé + **registres traduits** pour les puces du parc. |
| Fonctions | Filtres et pause ; inventaire et statistiques ; export et journal sur disque ; alertes ; **lecture/envoi vers les composants**. |
| Chemin d'envoi | **Les deux** : par la carte Tasmota (bus en service) et par le sniffeur devenu maître (composant isolé, au banc). |
| Annuaire | L'outil est **ajouté à l'annuaire**. |
| Si l'S3 ne tient pas 400 kHz | La voie S3 est **livrée pour 100 kHz**, limite affichée par l'outil ; le Pico reste « plus tard » (il n'entre pas dans le critère de fin de ce plan). |

### Choix tranchés après la relecture du réalisateur (*mes choix*, à contester)

1. **Envoi par la carte = Berry en ligne**, sans module à écrire : `Br wire1.read(<adr>, <reg>, <n>)` et
   `Br wire1.write(<adr>, <reg>, <val>, <n>)` (`wire2` si la puce est sur le 2e bus déclaré par le persist).
   Rien n'est ajouté aux cartes ni à `data/`.
2. **Rapprochement ordre ↔ trame** : première(s) transaction(s) de **même adresse et même sens** vues dans
   la seconde qui suit l'envoi ; au-delà, « trame non vue » (bus non relié au sniffeur, ou autre bus).
3. **Ordre des preuves** : les bancs du décodeur partent sur des trames tirées des fiches techniques,
   marquées provisoires ; elles sont **remplacées par des captures réelles** du sniffeur (action dédiée)
   avant de clore le plan.
4. **Détection du port** (« auto ») : chaque port USB candidat est ouvert sans DTR/RTS et reçoit `?` ; seul
   celui qui répond `I v=... puce=...` est retenu (une carte du parc branchée en USB est écartée).
5. **Puces** : toutes celles de l'inventaire du parc, une étape par famille, l'ossature d'abord.
6. **Broches** du sniffeur : constantes de build (`build_flags` du `platformio.ini` du firmware), défaut 4/5.
7. **500 lignes** : un fichier par rôle (comme le sniffeur ModBus) ; un dépassement se signale, il ne se
   compresse pas (leçon du 2026-10-18).

## 3. Constat technique (ce qui fonde le choix du matériel)

- **Tasmota ne peut pas écouter un bus I2C** : le contrôleur I2C de l'ESP32 est maître, ou esclave
  d'une seule adresse ; il n'a pas de mode « tout le trafic ». D'où un **firmware dédié** sur un ESP32
  qui n'est pas une carte du parc.
- Les adaptateurs USB-I2C courants (CH341A, MCP2221, FT232H) sont maîtres : ils n'écoutent pas.
- Une écoute par interruption sur chaque front perd des bits au-delà de ~100 kHz (latence d'ISR de
  l'ordre de la µs, un bit à 400 kHz dure 2,5 µs). Il faut une **boucle de lecture continue des
  broches** sur un cœur réservé. 100 kHz (défaut de Tasmota) est sûr ; **400 kHz est à prouver** par
  l'essai de l'action 1.
- Le Pico décode par ses blocs PIO jusqu'à 1 MHz : c'est la voie de secours si l'S3 ne tient pas
  400 kHz, et la voie 2 voulue de toute façon.

## 4. Matériel et câblage

- Sniffeur : ESP32-S3 DevKit, port **USB natif** (CDC) vers le PC.
- Trois fils vers le bus observé : **SDA, SCL, GND**. Broches du sniffeur : GPIO4 = SDA, GPIO5 = SCL
  (*mon choix*, à confirmer sur la sérigraphie du DevKit ; deux broches libres de toute fonction de
  démarrage, sur le même registre GPIO_IN pour une lecture simultanée).
- En écoute : entrées **sans tirage** (ni pull-up ni pull-down), haute impédance : le sniffeur ne doit
  rien changer au bus. Bus en **3,3 V uniquement** (les entrées de l'S3 ne tolèrent pas 5 V) ; le mode
  d'emploi le dit et l'outil le rappelle.
- Au banc (mode maître) : le composant isolé est alimenté par le DevKit (3,3 V) ; tirages par ceux du
  module breakout, sinon les tirages internes de l'S3 (faibles, 100 kHz seulement).

## 5. Firmware du sniffeur

Projet PlatformIO **séparé** : `outils_docs/firmware_sniffeur_i2c/` (vérifié : pas ignoré par git ; son
`.pio/` l'est). Framework Arduino-ESP32 (*mon choix* : déjà installé, `pio run -d <dossier> -t upload`).
Ce n'est **pas** un env de `platformio_tasmota_cenv.ini` et il ne touche à rien de Tasmota.

- **Cœur 1** : tâche épinglée, sans interruption ni watchdog de tâche sur ce cœur, qui lit en boucle
  le registre GPIO_IN et fait avancer une machine à états (START, bits, ACK/NACK, RESTART, STOP). Les
  transactions terminées vont dans un tampon circulaire.
- **Cœur 0** : vide le tampon vers l'USB, ligne par ligne ; compte les transactions perdues si le
  tampon déborde (jamais de blocage du cœur 1).
- **Mode maître** (banc) : sur ordre du PC, la tâche d'écoute s'arrête, le pilote Wire prend les mêmes
  broches, fait l'échange demandé, puis rend les broches à l'écoute. **Refus** si une activité du bus
  (front de SCL) a été vue dans les 2 dernières secondes : un autre maître est présent.
- Mesures embarquées : fréquence de SCL (sur la dernière transaction), SDA tenue basse (bus bloqué).

### Protocole série (commun ESP32 / Pico, versionné)

Lignes texte ASCII terminées par `\n`, un champ `clé=valeur` par mot (*mon choix* : lisible au
terminal du pont série, facile à simuler au banc). Proposition, à figer en A2 :

```
I v=1 puce=esp32s3 sda=4 scl=5 mode=ecoute          # identité, au démarrage et sur « ? »
X t=<µs> a=<hex2> rw=R|W d=<hex...> nack=<i|-> fin=STOP|RESTART|TRONQUE f=<kHz>   # une transaction
P n=<transactions perdues depuis le dernier P>
B sda=bas ms=<durée>                                 # bus bloqué
M ok=1|0 err=<texte> d=<hex...>                      # réponse à un ordre maître
```

Ordres du PC : `?`, `MW a=<hex2> d=<hex...>`, `MR a=<hex2> n=<octets>`, `MWR a=<hex2> d=<hex...> n=<octets>`
(écriture du pointeur de registre puis lecture après RESTART). Une transaction terminée par RESTART et
la suivante forment une paire « registre puis valeur » pour le décodeur.

Hors périmètre du firmware : adresses 10 bits (signalées « non décodé »), clock stretching mesuré,
1 MHz sur l'S3.

## 6. Outil PC

Fichiers dans `outils_docs/scripts_python/outils_pc/` (ils s'importent entre eux : même dossier), sur
le modèle de `sniffeur_modbus.py` + `sniffeur_modbus_web.py` + `sniffeur_modbus_http.py` +
`sniffeur_modbus_aide.py` + `decodeur_modbus.py` :

- `sniffeur_i2c.py` — lecture du port série (sans DTR/RTS, comme le sniffeur ModBus : pas de reset),
  historique, alertes, journal, ordres au sniffeur ; port de la page **7350** (*mon choix* : 7000 à
  7900 sont pris, 7350 range l'outil à côté du sniffeur ModBus).
- `sniffeur_i2c_web.py`, `sniffeur_i2c_http.py`, `sniffeur_i2c_aide.py` — page, routes, onglet Aide.
- `decodeur_i2c.py` — décodage par puce.
- Accès : `acces_web.py` (lien console, navigateur, jeton pour un autre appareil, en-tête et origine
  pour ce PC), comme les autres outils. Flux `/flux` (SSE, qui rejoue l'historique), `/etat`.

### Décodage

1. Trame : START, adresse 7 bits, R/W, octets, ACK/NACK, RESTART/STOP, durée, fréquence.
2. Composant : table adresse → puces possibles. Plusieurs puces partagent une plage (MCP23017 et
   TCA9554 sur 0x20-0x27) : l'utilisateur choisit dans la page **la carte observée** (liste des
   `data/<lieu>/<carte>/_persist.json`) et le décodeur prend les puces déclarées par son persist (clés
   `"virtuel": "I2C_<PUCE>"`, bloc `I2C`), comme `decodeur_modbus.py` prend le dialecte d'après le
   persist du maître. Sans carte choisie : toutes les puces possibles, marquées « ambigu ».
3. Registres : pour chaque puce du parc, nom des registres et traduction des valeurs (ex. ADS1115 :
   champs du registre de config, conversion ; MCP23017/TCA9554 : sens et état bit à bit des broches ;
   MPU6050 : accéléro/gyro en unités). **La liste exacte des puces est un inventaire de l'action A4**
   (persists + `I2CDriver` déclarés) ; une puce inconnue reste décodée au niveau trame.

### Fonctions de la page

- Fil en direct ; **filtres** (adresse/composant, lecture/écriture, NACK seulement, texte) ; **pause**.
- **Inventaire** des adresses vues (scan passif) et **statistiques** par composant : transactions,
  NACK, fréquence de SCL, dernière vue.
- **Export** .txt / .json de la capture ; **journal sur disque** continu dans
  `%LOCALAPPDATA%\outils_tasmota\sniffeur_i2c\` (purge au-delà de 30 jours, comme les journaux du build).
- **Alertes** dans le fil : NACK répétés sur une adresse, bus bloqué, trame tronquée, pertes du sniffeur.

### Lecture et écriture d'un registre

Un panneau : puce et adresse (prises dans l'inventaire ou la carte choisie), registre par son nom,
valeur ; la commande exacte est **affichée avant l'envoi**, une à la fois. Toute **écriture** demande une
confirmation (sur un bus en service, écrire dans l'extenseur commute un relais).

- **Par la carte Tasmota** (bus en service, aucun second maître) : HTTP `/cm?cmnd=Br ...` avec l'objet
  `wire` de Berry du bus de la puce, par l'aide existante `build_ota_http.py::_commande` (en-tête
  `Referer`, leçon du 2026-10-18). Adresse de la carte : `WIFI_IP_ADDRESS` de l'env, ou par le maître
  pour un esclave du range extender (`build_envs.py::adresse_par_maitre`). La trame doit ensuite
  apparaître dans le fil du sniffeur : l'outil la rapproche de l'ordre et l'affiche comme réponse.
- **Par le sniffeur** (composant isolé, au banc) : ordres `MW`/`MR`/`MWR` ; refus du firmware si le bus
  a vécu dans les 2 dernières secondes, et case « composant débranché de sa carte » à cocher dans la
  page.

## 7. Intégration

- **Annuaire** : une fiche `Outil` dans `annuaire_registre.py`, groupe « Bus et cartes », paramètres :
  port série (`com`, auto = le seul DevKit S3 présent) et port de la page (7350).
- **Cible Custom** `build/cible_sniffeur_i2c.py` (`NOM_CIBLE = "sniffeur_i2c"`), ajoutée à
  `CIBLES_OUTILS` de `.claude/hooks/garde_build.py` (le banc `test_garde_build.py` vérifie que la liste
  égale les `NOM_CIBLE`).
- **Tâche VS Code** « Outil : sniffeur I2C (http://127.0.0.1:7350) » dans `.vscode/tasks.json`,
  chemin par `${env:USERPROFILE}`, **lancée une fois** avant d'être annoncée (leçon du 2026-10-13).
- **Documentation** : section du mode d'emploi dans `outils_docs/README.md` (câblage, flash du
  firmware, limites de vitesse) ; ligne dans la carte des documents de `CLAUDE.md`.

## 8. Vérification

- Banc `outils_pc/test_sniffeur_i2c.py` (code de sortie 0 = vert) : lignes série simulées → décodage,
  paires registre/valeur, alertes, pertes, refus d'un ordre maître ; décodage figé sur des trames
  **réelles** capturées (pas dérivées des tables testées, leçon du 2026-10-29), avec témoins mutés.
- Page exécutée dans un vrai Chrome (sonde DevTools, flux SSE : leçons du 2026-10-16 et 2026-10-17).
- Sur matériel : une carte du parc fait `I2CScan` et une lecture connue ; le fil du sniffeur doit
  montrer les mêmes adresses et valeurs que le log de la carte. Mesure à 100 puis 400 kHz sur un bus
  réel, pertes = 0.

## 9. Non-objectifs et anti-objectifs

- Non-objectifs : SMBus/PMBus, adresses 10 bits, 1 MHz sur l'S3, intégration dans Tasmota, toute
  modification des cartes du parc ou de `data/`.
- Anti-objectifs (échec même si « ça marche ») : un sniffeur qui perturbe le bus en écoute (tirage,
  sortie active) ; un mode maître qui émet sur un bus en service ; une écriture envoyée sans que la
  commande ait été montrée et confirmée ; des pertes d'octets silencieuses.

## 10. Laissé au réalisateur

Structure interne du firmware et de l'outil PC, format exact de l'export, mise en page (sur le modèle
du sniffeur ModBus), seuils des alertes (NACK répétés, durée de bus bloqué).

## 11. Voie 2 — Pico (plus tard)

Firmware RP2040 (PIO) parlant le protocole du §5 ; l'outil PC le reconnaît à sa ligne `I puce=rp2040`.
Rien d'autre ne change. Planifiée en « Améliorations restantes [projet] ».
