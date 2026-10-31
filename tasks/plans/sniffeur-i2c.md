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
- [ ] `git check-ignore -v` sur le dossier : non ignoré (vérifié en conception), `.pio/` ignoré
- [ ] `machine_i2c.h` : START, 8 bits + ACK/NACK, RESTART, STOP, trame tronquée, fréquence de SCL ; bancs Unity : écriture 1 octet, lecture 2 octets après RESTART, NACK d'adresse, STOP au milieu d'un octet (= TRONQUE) — natif (`pio test -e native`) si gcc est présent, sinon sur la carte en A8
- [ ] `main.cpp` : tâche d'écoute épinglée cœur 1 (lecture du registre d'entrée en boucle ; `dedic_gpio` de l'S3 si `REG_READ` est trop lent), tampon circulaire, cœur 0 = émission des lignes `I/X/P/B` du §5 de la spec ; entrées sans tirage
- [ ] Hors build : `pio run -d outils_docs/firmware_sniffeur_i2c` compile sans erreur
- [ ] Commit `feat(sniffeur-i2c): firmware d'ecoute ESP32-S3`

## A2 — Protocole et lecteur série côté PC
Fichiers : `outils_pc/sniffeur_i2c_protocole.py`, `outils_pc/sniffeur_i2c.py`, `outils_pc/test_sniffeur_i2c.py`.
Interfaces produites : `lit_ligne(texte: str) -> dict | None` (`type` I/X/P/B/M ; X : `t:int, a:int,
rw:"R"|"W", d:bytes, nack:int|None, fin:"STOP"|"RESTART"|"TRONQUE", f:float`) ;
`ordre(nom: str, a: int, d: bytes = b"", n: int = 0) -> bytes` (`?`, `MW`, `MR`, `MWR`) ;
`Sniffeur(args)` avec `ouvre(port)`, `ferme(raison)`, `traite_ligne(texte)`, `etat() -> dict`,
`boucle_lecture()` ; `port_auto() -> str | None`.
- [ ] Bancs d'abord (rouges) : chaque type de ligne, ligne illisible -> `None` + compteur, ligne coupée en deux lectures, `P n=` cumulé
- [ ] `sniffeur_i2c_protocole.py` puis `sniffeur_i2c.py` sur le modèle de `sniffeur_modbus.py::Sniffeur` (historique borné, `_diffuse`, `inscrit_web`, journal) ; `port_auto()` envoie `?` à chaque port USB et garde celui qui répond `I v=` ; port perdu -> état « fermé » + message, réouverture par `ouvre`
- [ ] `PYPIO outils_pc/test_sniffeur_i2c.py` vert, témoin muté rouge (copie dans le scratchpad)
- [ ] Commit

## A3 — Page web : fil, filtres, pause, inventaire, statistiques, export, journal, alertes
Fichiers : `outils_pc/sniffeur_i2c_web.py`, `outils_pc/sniffeur_i2c_http.py`, `outils_pc/sniffeur_i2c_aide.py`,
`outils_pc/sniffeur_i2c_alertes.py`, `outils_pc/test_sniffeur_i2c_page_chrome.py`.
Accès par `acces_web.py` (comme les autres pages) ; routes `/`, `/flux` (SSE, rejoue l'historique),
`/etat`, `/export?format=txt|json`, `/ouvre`, `/ferme`, `/raz`.
- [ ] Alertes (bancs d'abord) : NACK répétés sur une adresse, bus bloqué (`B`), trame TRONQUE, pertes `P` ; seuils = constantes nommées en tête de `sniffeur_i2c_alertes.py`
- [ ] Inventaire/statistiques par adresse : transactions, NACK, fréquence SCL, dernière vue ; historique borné (test : 100 000 lignes injectées -> mémoire bornée, compteurs justes)
- [ ] Journal continu `%LOCALAPPDATA%\outils_tasmota\sniffeur_i2c\` (purge > 30 jours) ; export txt/json
- [ ] Page : fil, filtres (adresse/puce, R/W, NACK seuls, texte), pause, panneau inventaire, onglet Aide (câblage 3 fils, 3,3 V seulement, limites de vitesse)
- [ ] Sonde Chrome par DevTools (leçons du 2026-10-16/17) : aucune erreur JS, chaque onglet cliqué, lignes injectées visibles ; témoin = page cassée détectée
- [ ] Commit

## A4 — Décodeur par puce
Fichiers : `outils_pc/decodeur_i2c.py` (ossature), `outils_pc/decodeur_i2c_puces.py` (tables de registres).
Interfaces : `puces_carte(persist: dict) -> list[str]` (clés `"virtuel": "I2C_<PUCE>"`) ;
`candidats(adresse: int, puces: list[str] | None) -> list[str]` ;
`decode(tr: dict, avant: dict | None, puces: list[str] | None) -> dict` (`puce`, `ambigu`, `registre`,
`valeur`, `texte`) ; paire RESTART : `avant` porte le pointeur de registre.
- [ ] Inventaire du parc : puces I2C des 9 persists (`virtuel` + bloc `I2C`) et `I2CDriver` déclarés, consigné dans le Contexte de ce plan
- [ ] Ossature + test « 0x20 sans carte = ambigu, avec la cuve = la puce de son persist »
- [ ] Une étape par famille de l'inventaire (ADS1115, MCP23017, TCA9554, MPU6050, ES8311… selon l'inventaire) : trames tirées de la fiche technique, marquées PROVISOIRE dans le banc
- [ ] Sélecteur « carte observée » dans la page (liste des `data/*/*/_persist.json`), décodage affiché dans le fil
- [ ] Bancs verts + témoin ; commit

## A5 — Lecture et écriture par la carte Tasmota
Fichier : `outils_pc/sniffeur_i2c_carte.py`. Réutilise `build_ota_http.py::_commande` (Referer) et
`build_envs.py::adresse_par_maitre` / `lit_ip_ota` / `persist_carte`.
Interfaces : `commande_br(bus: int, a: int, reg: int, n: int, valeur: int | None) -> str`
(`Br wire1.read(...)` / `Br wire1.write(...)`, `wire2` pour le 2e bus) ; `ip_carte(racine, env) -> str` ;
`envoie(ip, commande, delai) -> str`.
- [ ] Bancs : texte exact des commandes, bornes (adresse 0x03-0x77, octets 1-4), carte injoignable -> message sans exception, envoi dans un fil à part (serveur jamais bloqué)
- [ ] Rapprochement : transactions de même adresse et même sens dans la seconde suivante -> « réponse » ; sinon « trame non vue »
- [ ] Panneau de la page : puce, registre par son nom, valeur ; commande affichée avant envoi ; écriture = confirmation
- [ ] Bancs + sonde Chrome verts ; commit

## A6 — Mode maître au banc (composant isolé)
- [ ] Firmware : ordres `MW`/`MR`/`MWR` -> arrêt de l'écoute, Wire sur les mêmes broches, réponse `M`, retour à l'écoute ; refus `M ok=0 err=bus_actif` si un front de SCL a été vu dans les 2 dernières secondes ; banc Unity du refus
- [ ] PC : `Sniffeur.ordre_maitre(...)`, case « composant débranché de sa carte » obligatoire, mêmes confirmation et affichage qu'en A5 ; bancs
- [ ] Compilation hors build ; commit

## A7 — Intégration : annuaire, cible Custom, tâche VS Code, documentation
- [ ] `annuaire_registre.py` : `Outil("sniffeur_i2c", ..., GROUPES[0], ...)`, paramètres `Parametre("port", "Port série", "--port", "auto", "com")` et `_port("http", 7350)` ; liste `ids` de `test_annuaire.py` complétée ; `test_annuaire*.py` verts
- [ ] `build/cible_sniffeur_i2c.py` (`NOM_CIBLE = "sniffeur_i2c"`, modèle `cible_sniffeur_modbus.py`), import dans `pre_utilitaires_platformio.py`, `CIBLES_OUTILS` de `.claude/hooks/garde_build.py` ; `build/test_garde_build.py` vert
- [ ] Tâche VS Code « Outil : sniffeur I2C (http://127.0.0.1:7350) » (`${env:USERPROFILE}`), lancée une fois
- [ ] `outils_docs/README.md` (câblage, flash du firmware, vitesses, envoi), `CLAUDE.md` (carte des documents), skill `bancs` (ligne du banc) ; `verifie_references_docs.py` vert
- [ ] Commit

## A8 — Validation sur matériel (avec l'utilisateur)
- [ ] Broches 4/5 confirmées sur la sérigraphie du DevKit ; flash du firmware hors build ; ligne `I` reçue
- [ ] Une carte du parc branchée (3 fils) : `I2CScan` + une lecture connue -> mêmes adresses et valeurs dans le fil que dans le log de la carte
- [ ] Captures réelles remplacent les trames PROVISOIRE des bancs (A4), bancs verts
- [ ] Vitesse : 100 kHz sans perte ; essai 400 kHz (source à trouver : réglage de vitesse Tasmota si disponible, sinon 2e ESP32) -> limite constatée affichée dans la page et l'Aide
- [ ] Lecture par la carte (A5) et lecture au banc d'un composant isolé (A6) vues dans le fil

## A9 — Clôture
- [ ] `tasks/README.md` à jour (`node .claude/hooks/index_plans.mjs --verifier`), plan `statut: clos`
- [ ] Commits relus, push du sha relu

## Améliorations restantes
- [ ] [projet] Voie 2 : firmware Raspberry Pi Pico (PIO) parlant le même protocole, `I puce=rp2040`
- [ ] [projet] Voie MQTT pour l'envoi par la carte (esclaves injoignables en HTTP)

## Vérification
Bancs : `PYPIO outils_pc/test_sniffeur_i2c.py` (code 0 = vert), sonde Chrome de la page, `test_annuaire*.py`,
`build/test_garde_build.py`, `verifie_references_docs.py`, bancs Unity du firmware. Bout en bout : A8 sur une
vraie carte, fil du sniffeur comparé au log de la carte.
