---
chantier: sniffeur-i2c
titre: Sniffeur I2C (ESP32-S3 dédié + outil PC de l'annuaire)
statut: actif
cree: 2026-10-31
maj: 2026-10-31
source: iridescent-dazzling-journal.md
objectif: Voir en direct le trafic I2C de n'importe quelle carte du parc, décodé jusqu'au registre, et lire ou écrire un registre par la carte ou au banc
---
# Sniffeur I2C — plan

## Contexte
Spec validée par l'utilisateur le 2026-10-31 : `docs/superpowers/specs/2026-10-31-sniffeur-i2c-design.md`
(à lire avec ce plan). Tasmota ne peut pas écouter un bus I2C : un **ESP32-S3 DevKit de rechange** fait
tourner un firmware dédié qui décode SDA/SCL et envoie une ligne texte par transaction sur son USB ;
l'outil PC `sniffeur_i2c.py` (page 7350, modèle du sniffeur ModBus) décode, filtre, compte, alerte,
journalise, et envoie des lectures/écritures par la carte Tasmota (`Br wire1...`) ou par le sniffeur
devenu maître (composant isolé). Ajouté à l'annuaire. Voie Pico plus tard, même protocole.
Si l'S3 ne tient pas 400 kHz : livré à 100 kHz, limite affichée (décision utilisateur).

**Inventaire du parc (A4, 2026-10-31)** : ADS1115 0x48 (I2CDriver 13, actif sur la cuve), MCP23017 0x20 (22, inactif
partout), TCA9554 0x20 (81, actif sur la cave S3 Waveshare), DS3231 0x68 (26, actif sur le P4), ES8311 0x18 (P4, hors
bloc I2C, trouve par `tasmota.wire_scan`), MPU6050 0x68 (bloc « inclinaison » des volets, `vrFonctions.be`). Adresses
partagees : 0x20 (MCP23017/TCA9554), 0x68 (DS3231/MPU6050).

**Contraintes globales** (valent pour chaque action) :
- Port de la page **7350** ; Python de PlatformIO pour pyserial (`PYPIO`, skill `bancs`) ; port ouvert
  **sans DTR/RTS**.
- **Aucun `pio run`** (firmware compris) pendant un build : `garde_build` refuse, attendre.
- Rien n'est modifié dans `data/`, ni sur une carte du parc hors action explicite de l'utilisateur.
- Commits en français sans accents, `git commit -- <chemins>` (jamais les fichiers en cours de
  l'utilisateur : persist du rideau, `build_page.py`, defines Berry), `git show --stat HEAD` après ;
  push du seul sha relu (`git push origin <sha>:development`, leçon du 2026-10-27).
- Fichiers d'outil sous 500 lignes, un par rôle ; un dépassement se signale, il ne se compresse pas.

**Points à surveiller** (aucun test ne les couvre d'office, chacun reçoit son test dans l'action citée) :
1. Ligne série coupée/corrompue (reset du S3, USB) -> ignorée et comptée, jamais d'exception (A2).
2. Sniffeur débranché en cours -> « port perdu » sur la page, rouvrir sans relancer l'outil (A2).
3. Adresse partagée 0x20-0x27 sans carte choisie -> « ambigu », jamais un nom deviné (A4).
4. Carte injoignable ou esclave derrière le NAPT -> adresse par le maître, sinon message clair, pas de
   blocage du serveur (A5).
5. Bus saturé (400 kHz continu) -> historique borné, pertes affichées, page fluide (A3).

## A1 — Firmware d'écoute (ESP32-S3) et essai de vitesse
Fichiers : `outils_docs/firmware_sniffeur_i2c/platformio.ini` (env `esp32s3`, Arduino, USB CDC au boot,
`build_flags -DBROCHE_SDA=4 -DBROCHE_SCL=5`), `src/main.cpp`, `src/machine_i2c.h` (machine à états PURE,
sans Arduino : `void avance(Machine&, bool sda, bool scl, uint32_t t_us)` + transaction prête),
`test/test_machine/` (Unity).
- [x] `git check-ignore -v` sur le dossier : non ignoré (vérifié en conception), `.pio/` ignoré — preuve : `git check-ignore -v` code 1 sur `outils_docs/firmware_sniffeur_i2c/platformio.ini`, `.pio/` ignore par `.gitignore:16`
- [x] `machine_i2c.h` : START, 8 bits + ACK/NACK, RESTART, STOP, trame tronquée, fréquence de SCL ; bancs Unity : écriture 1 octet, lecture 2 octets après RESTART, NACK d'adresse, STOP au milieu d'un octet (= TRONQUE) — natif (`pio test -e native`) si gcc est présent, sinon sur la carte en A8 — preuve : banc PC `banc/test_machine.cpp` (MSVC des Build Tools, pas Unity : gcc absent mais cl.exe present) VERT 8 cas (+ changement simultane SDA/SCL, debordement, parasite) ; 1er passage ROUGE (le front de SCL avant STOP/RESTART comptait comme un bit) corrige par le bit en attente jusqu'au front descendant ; temoin ACK inverse ROUGE 5 echecs
- [x] `main.cpp` : tâche d'écoute épinglée cœur 1 (lecture du registre d'entrée en boucle ; `dedic_gpio` de l'S3 si `REG_READ` est trop lent), tampon circulaire, cœur 0 = émission des lignes `I/X/P/B` du §5 de la spec ; entrées sans tirage — preuve : d9747da91 `src/main.cpp` (REG_READ(GPIO_IN_REG) en boucle, cœur 1 sans interruption, MWDT1 coupé ; vitesse réelle à mesurer en A8 par `ech=`)
- [x] Hors build : `pio run -d outils_docs/firmware_sniffeur_i2c` compile sans erreur — preuve : [SUCCESS], aucun avertissement, RAM 13,0 % (42 452 o), Flash 5,0 % (166 639 o) ; 1er essai rouge : `SDA`/`SCL` déjà déclarés par `pins_arduino.h` -> renommés `MASQUE_SDA`/`MASQUE_SCL`
- [x] Commit `feat(sniffeur-i2c): firmware d'ecoute ESP32-S3` — preuve : d9747da91

## A2 — Protocole et lecteur série côté PC
Fichiers : `outils_pc/sniffeur_i2c_protocole.py`, `outils_pc/sniffeur_i2c.py`, `outils_pc/test_sniffeur_i2c.py`.
Interfaces produites : `lit_ligne(texte: str) -> dict | None` (`type` I/X/P/B/M ; X : `t:int, a:int,
rw:"R"|"W", d:bytes, nack:int|None, fin:"STOP"|"RESTART"|"TRONQUE", f:float`) ;
`ordre(nom: str, a: int, d: bytes = b"", n: int = 0) -> bytes` (`?`, `MW`, `MR`, `MWR`) ;
`Sniffeur(args)` avec `ouvre(port)`, `ferme(raison)`, `traite_ligne(texte)`, `etat() -> dict`,
`boucle_lecture()` ; `port_auto() -> str | None`.
- [x] Bancs d'abord (rouges) : chaque type de ligne, ligne illisible -> `None` + compteur, ligne coupée en deux lectures, `P n=` cumulé — preuve : `test_sniffeur_i2c.py::test_protocole` (ecrits avec le code et non avant ; a la place, temoins mutes ROUGES, voir A3/A4)
- [x] `sniffeur_i2c_protocole.py` puis `sniffeur_i2c.py` sur le modèle de `sniffeur_modbus.py::Sniffeur` (historique borné, `_diffuse`, `inscrit_web`, journal) ; `port_auto()` envoie `?` à chaque port USB et garde celui qui répond `I v=` ; port perdu -> état « fermé » + message, réouverture par `ouvre` — preuve : ed6fb1f96 ; `port_auto` ne sonde que les VID Espressif/Raspberry (`proto.VIDS_SNIFFEUR`) ; `test_sonde`, port perdu dans `test_sniffeur`
- [x] `PYPIO outils_pc/test_sniffeur_i2c.py` vert, témoin muté rouge (copie dans le scratchpad) — preuve : VERT ; temoins sur copie COMPLETE de outils_pc/ (sniffeur_i2c.py met son dossier en tete de sys.path : un module mute seul est masque) : NACK `>=` ROUGE, PGA ADS1115 ROUGE
- [x] Commit — preuve : ed6fb1f96

## A3 — Page web : fil, filtres, pause, inventaire, statistiques, export, journal, alertes
Fichiers : `outils_pc/sniffeur_i2c_web.py`, `outils_pc/sniffeur_i2c_http.py`, `outils_pc/sniffeur_i2c_aide.py`,
`outils_pc/sniffeur_i2c_alertes.py`, `outils_pc/test_sniffeur_i2c_page_chrome.py`.
Accès par `acces_web.py` (comme les autres pages) ; routes `/`, `/flux` (SSE, rejoue l'historique),
`/etat`, `/export?format=txt|json`, `/ouvre`, `/ferme`, `/raz`.
- [x] Alertes (bancs d'abord) : NACK répétés sur une adresse, bus bloqué (`B`), trame TRONQUE, pertes `P` ; seuils = constantes nommées en tête de `sniffeur_i2c_alertes.py` — preuve : `sniffeur_i2c_alertes.py` (NACK_REPETES), `test_alertes` VERT, temoin `>=` ROUGE
- [x] Inventaire/statistiques par adresse : transactions, NACK, fréquence SCL, dernière vue ; historique borné (test : 100 000 lignes injectées -> mémoire bornée, compteurs justes) — preuve : `test_sniffeur` 100 000 lignes -> historique 50, nb et inventaire = 100 001 (~7 000 lignes/s poste charge, apres strftime une fois par lot)
- [x] Journal continu `%LOCALAPPDATA%\outils_tasmota\sniffeur_i2c\` (purge > 30 jours) ; export txt/json — preuve : `sniffeur_i2c.py::Journal`, purge testee (fichier a 31 jours efface) ; export txt/json dans `test_http`
- [x] Page : fil, filtres (adresse/puce, R/W, NACK seuls, texte), pause, panneau inventaire, onglet Aide (câblage 3 fils, 3,3 V seulement, limites de vitesse) — preuve : ed6fb1f96 `sniffeur_i2c_web.py` + `sniffeur_i2c_aide.py`
- [x] Sonde Chrome par DevTools (leçons du 2026-10-16/17) : aucune erreur JS, chaque onglet cliqué, lignes injectées visibles ; témoin = page cassée détectée — preuve : `test_sniffeur_i2c_page_chrome.py` VERT 13 verifications (favicon 404 et le 400 provoque exclus nommement), temoin TypeError detecte
- [x] Commit — preuve : ed6fb1f96

## A4 — Décodeur par puce
Fichiers : `outils_pc/decodeur_i2c.py` (ossature), `outils_pc/decodeur_i2c_puces.py` (tables de registres).
Interfaces : `puces_carte(persist: dict) -> list[str]` (clés `"virtuel": "I2C_<PUCE>"`) ;
`candidats(adresse: int, puces: list[str] | None) -> list[str]` ;
`decode(tr: dict, avant: dict | None, puces: list[str] | None) -> dict` (`puce`, `ambigu`, `registre`,
`valeur`, `texte`) ; paire RESTART : `avant` porte le pointeur de registre.
- [x] Inventaire du parc : puces I2C des 9 persists (`virtuel` + bloc `I2C`) et `I2CDriver` déclarés, consigné dans le Contexte de ce plan — preuve : consigne dans le Contexte ci-dessus
- [x] Ossature + test « 0x20 sans carte = ambigu, avec la cuve = la puce de son persist » — preuve : `test_decodeur` (persist de test) + sonde Chrome (carte cave S3 -> TCA9554) ; interface devenue `Decodeur(puces).decode(tr)` (memoire du pointeur par adresse : le pilote ADS1115 ecrit le pointeur puis lit apres un STOP, pas un RESTART)
- [x] Une étape par famille de l'inventaire (ADS1115, MCP23017, TCA9554, MPU6050, ES8311… selon l'inventaire) : trames tirées de la fiche technique, marquées PROVISOIRE dans le banc — preuve : ADS1115, MCP23017, TCA9554, DS3231 (24 h et 12 h), MPU6050 (rafale, plages, WHO_AM_I), ES8311 (noms) dans `test_decodeur`, trames PROVISOIRE
- [x] Sélecteur « carte observée » dans la page (liste des `data/*/*/_persist.json`), décodage affiché dans le fil — preuve : `/cartes`, `/carte` ; sonde Chrome « carte observee (cave S3) : 0x20 decode TCA9554 »
- [x] Bancs verts + témoin ; commit — preuve : ed6fb1f96

## A5 — Lecture et écriture par la carte Tasmota
Fichier : `outils_pc/sniffeur_i2c_carte.py`. Réutilise `build_ota_http.py::_commande` (Referer) et
`build_envs.py::adresse_par_maitre` / `lit_ip_ota` / `persist_carte`.
Interfaces : `commande_br(bus: int, a: int, reg: int, n: int, valeur: int | None) -> str`
(`Br wire1.read(...)` / `Br wire1.write(...)`, `wire2` pour le 2e bus) ; `ip_carte(racine, env) -> str` ;
`envoie(ip, commande, delai) -> str`.
- [x] Bancs : texte exact des commandes, bornes (adresse 0x03-0x77, octets 1-4), carte injoignable -> message sans exception, envoi dans un fil à part (serveur jamais bloqué) — preuve : `test_sniffeur` (commande_br, bornes, carte injoignable, IP invalide, un ordre a la fois) ; HTTP par ThreadingHTTPServer : un fil par requete
- [x] Rapprochement : transactions de même adresse et même sens dans la seconde suivante -> « réponse » ; sinon « trame non vue » — preuve : `test_sniffeur` ; plus strict que prevu : meme registre aussi (la sonde `detect` et les lectures du pilote ne comptent pas) ; temoin autre registre
- [x] Panneau de la page : puce, registre par son nom, valeur ; commande affichée avant envoi ; écriture = confirmation — preuve : onglet Envoi, apercu `{apercu: true}` sans envoi (sonde Chrome + `test_http`)
- [x] Bancs + sonde Chrome verts ; commit — preuve : ed6fb1f96

## A6 — Mode maître au banc (composant isolé)
- [ ] Firmware : ordres `MW`/`MR`/`MWR` -> arrêt de l'écoute, Wire sur les mêmes broches, réponse `M`, retour à l'écoute ; refus `M ok=0 err=bus_actif` si un front de SCL a été vu dans les 2 dernières secondes ; banc Unity du refus — codé (d9747da91, `main.cpp::ordre_maitre`), refus testé côté PC seulement : à vérifier sur carte en A8, pas de banc C++ du refus
- [x] PC : `Sniffeur.ordre_maitre(...)`, case « composant débranché de sa carte » obligatoire, mêmes confirmation et affichage qu'en A5 ; bancs — preuve : `test_sniffeur` (reponse, refus bus_actif, port ferme) + `test_http` (isole exige, 409 port ferme)
- [x] Compilation hors build ; commit — preuve : d9747da91 (même compilation que A1)

## A7 — Intégration : annuaire, cible Custom, tâche VS Code, documentation
- [x] `annuaire_registre.py` : `Outil("sniffeur_i2c", ..., GROUPES[0], ...)`, paramètres `Parametre("port", "Port série", "--port", "auto", "com")` et `_port("http", 7350)` ; liste `ids` de `test_annuaire.py` complétée ; `test_annuaire*.py` verts — preuve : d7e7ca9f6 ; test_annuaire, _lanceur, _securite VERTS (index des tests decales)
- [x] `build/cible_sniffeur_i2c.py` (`NOM_CIBLE = "sniffeur_i2c"`, modèle `cible_sniffeur_modbus.py`), import dans `pre_utilitaires_platformio.py`, `CIBLES_OUTILS` de `.claude/hooks/garde_build.py` ; `build/test_garde_build.py` vert — preuve : 680bf8fd0 ; `build/test_garde_build.py` VERT
- [ ] Tâche VS Code « Outil : sniffeur I2C (http://127.0.0.1:7350) » (`${env:USERPROFILE}`), lancée une fois — tâche écrite (d7e7ca9f6), sa ligne de commande vérifiée (page 200) ; reste à la lancer par Tasks: Run Task
- [x] `outils_docs/README.md` (câblage, flash du firmware, vitesses, envoi), `CLAUDE.md` (carte des documents), skill `bancs` (ligne du banc) ; `verifie_references_docs.py` vert — preuve : 680bf8fd0 ; `verifie_references_docs.py` 0 défaut
- [x] Commit — preuve : d7e7ca9f6, 680bf8fd0

## A8 — Validation sur matériel (avec l'utilisateur)
- [ ] Broches 4/5 confirmées sur la sérigraphie du DevKit ; flash du firmware hors build ; ligne `I` reçue
- [ ] Une carte du parc branchée (3 fils) : `I2CScan` + une lecture connue -> mêmes adresses et valeurs dans le fil que dans le log de la carte
- [ ] Captures réelles remplacent les trames PROVISOIRE des bancs (A4), bancs verts
- [ ] Vitesse : 100 kHz sans perte ; essai 400 kHz (source à trouver : réglage de vitesse Tasmota si disponible, sinon 2e ESP32) -> limite constatée affichée dans la page et l'Aide
- [ ] Lecture par la carte (A5) et lecture au banc d'un composant isolé (A6) vues dans le fil

## A9 — Clôture
- [ ] `tasks/README.md` à jour (`node .claude/hooks/index_plans.mjs --verifier`), plan `statut: clos`
- [ ] Commits relus, push du sha relu

## A10 — Voie MQTT pour l'envoi par la carte (demande du 2026-10-31)
Esclaves derrière le NAPT du maître : HTTP seulement par `<ip du maître>:<port>` avec `RoutageRangeExtender` ;
MQTT les joint par le broker. `sniffeur_i2c_carte.py::commande_mqtt` : `cmnd/<topic>/Br` (charge sans « Br »),
réponse = le `stat/<topic>/RESULT` qui porte la clé `Br` ; topic du persist (`serveur.mqtt.topic`).
- [x] `sniffeur_i2c_carte.py` : `topic_propose`, `verifie_topic` (ni joker ni espace), `commande_mqtt`, `envoie_mqtt` — preuve : `test_sniffeur_i2c.py::test_mqtt` VERT (RESULT d'une autre commande, autre topic, charge illisible ignorés ; carte muette = échec sans exception, liaison fermée ; topics `""`, `#`, `+`, espace refusés) ; témoin « tout RESULT accepté » ROUGE 3 échecs
- [x] Route `/ordre` (`transport: mqtt`, `topic`), `/carte` rend le topic ; page : liste « par » HTTP/MQTT, MQTT d'office pour un esclave (IP vide ou `ip:port`) ; Aide, README, CLAUDE.md — preuve : `test_http` (topic à joker 400, rien journalisé ; topic proposé) ; sonde Chrome VERTE (topic proposé, IP grisée en MQTT, aperçu)
- [ ] Essai réel : lecture d'un registre d'un esclave par MQTT, trame vue dans le fil (avec A8)
- [x] Commit — preuve : 101e03106

## Améliorations restantes
- [ ] [projet] Voie 2 : firmware Raspberry Pi Pico (PIO) parlant le même protocole, `I puce=rp2040`
- [x] [projet] Voie MQTT pour l'envoi par la carte (esclaves injoignables en HTTP) — devenue l'action A10

## Vérification
Bancs : `PYPIO outils_pc/test_sniffeur_i2c.py` (code 0 = vert), sonde Chrome de la page, `test_annuaire*.py`,
`build/test_garde_build.py`, `verifie_references_docs.py`, bancs Unity du firmware. Bout en bout : A8 sur une
vraie carte, fil du sniffeur comparé au log de la carte.
