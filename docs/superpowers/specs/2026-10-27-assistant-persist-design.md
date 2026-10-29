# Assistant de création du persist d'un nouvel env — conception

Date : 2026-10-27 · Statut : à valider par l'utilisateur · Décisions : conversation du 2026-10-27, questions 1 à 16 ; choix du rédacteur au §5.6.

## 1. Intention

Créer une carte aujourd'hui, c'est copier le dossier d'une carte voisine puis corriger le `_persist.json` à la main.
La page « Fichiers Berry par env » (port 7800, `fichiers_berry_creation.py`) automatise la copie : section du cenv,
section `#elif` du `.h`, dossier `data/<lieu>/<puce>-<nom>`. Mais elle recopie **tout** le persist du modèle et n'en
remplace que 8 clés d'identité (`fichiers_berry_creation::CLES_PERSIST`).

Ce qu'elle ne fait pas :
- choisir les fonctions de la carte ;
- adapter le rôle réseau (un esclave copié d'un maître garde le Wi-Fi et la passerelle du maître) ;
- changer l'id ModBus/UDP/TCP/Range Extender (une copie de la cuve garde l'id 2) ;
- mettre en cohérence l'autoexec et les listes `custom_berry_solidify` / `custom_files_exclude` avec ce qui est activé.

L'assistant répond à ce manque. On décrit la carte par des questions ; la page en déduit un persist **cohérent**,
avec l'autoexec, la section du cenv et la section du `.h` qui vont avec. Les questions, les valeurs par défaut et
les règles de cohérence vivent dans un **JSON modèle** qui suit l'évolution des persists du dépôt.

Succès : on crée une carte nouvelle sans ouvrir un persist existant. Elle démarre du premier coup avec les bons
modules, sur le bon réseau, avec un id libre.

## 2. Décisions de l'utilisateur

| # | Sujet | Décision |
|---|---|---|
| 1 | Emplacement | **Nouvelle page, port 7900** : tuile « Maintenance » de l'annuaire, cible Custom, tâche VS Code. Elle réutilise le moteur de création existant (cenv, `.h`, dossier, transaction), sans le dupliquer. |
| 2 | Point de départ | **JSON modèle + questions.** Pas de préremplissage depuis une carte existante (la page 7800 garde ce rôle). |
| 3 | Tenue du modèle | **Écrit à la main + banc de couverture**, complété par la mise à jour des décisions 14-15. |
| 4 | Entrées/sorties | **Éditeur d'éléments en 2e étape du plan.** Version 1 : bloc métier créé avec un `environnement` vide. |
| 5 | Fonction métier nouvelle | **Squelettes sur demande** (case à cocher) : `controleXxx.be` + `xxxFonctions.be` minimaux dans le dossier de la carte. |
| 6 | Rôle réseau | Autonome / maître / esclave. Un esclave **choisit son maître** dans la liste des maîtres du dépôt. Id **proposé libre**, doublon = avertissement. Le même id va dans `serveur.rangeExtender.id`, `serveur.udp.id`, `serveur.tcp.id`, `drivers.ModBus.id`. |
| 7 | Mots de passe | **Recopiés côté serveur** depuis un persist existant, jamais envoyés à la page, masqués dans le diff. |
| 8 | Autres fichiers | `autoexec.be` **généré à partir des blocs activés** ; `graphiques.json` si l'historique est activé ; historique **refusé sur ESP32 classique** (S3 et P4 seulement). |
| 9 | Périmètre | Création. La **modification d'un env existant** est la dernière action du plan, à déclencher plus tard. |
| 10 | Schéma | **Corriger** `outils_docs/schemas/persist.schema.json` et **valider** chaque persist généré contre lui avant l'écriture. |
| 11 | Après création | **Liens** vers la page build (`?env=`) et « Fichiers Berry par env », plus un **résumé à copier**. Ni build, ni commit, ni `default_envs`. |
| 12 | cenv et `.h` | **Générés à partir des réponses** : gabarit par puce dans le modèle, listes solidify/exclude déduites des blocs activés (même source que l'autoexec), `.h` rempli avec l'identité et le rôle. |
| 13 | Mise en page | **A : assistant par étapes** (Carte → Réseau → Fonctions → Bloc métier → Vérification) avec **l'aperçu du persist à droite**, mis à jour à chaque saisie. Maquette validée (onglet A ; données fictives) : `docs/superpowers/specs/2026-10-27-assistant-persist-maquette.html`. |
| 14 | Fidélité du modèle | **Bouton « Mettre à jour le modèle »** dans la page + **mise à jour automatique** : les clés nouvelles sont ajoutées sans validation (défaut = valeur la plus fréquente) ; les questions restent à compléter à la main. |
| 15 | Moment de la mise à jour automatique | **À l'ouverture de la page** (démarrage du serveur 7900). |
| 16 | Plusieurs blocs métier | **Plusieurs blocs `modules.<x>` par carte, un seul « principal »** : lui seul reçoit les squelettes `controleXxx.be` / `xxxFonctions.be` et la ligne `chargeFichier` ; les autres sont des blocs de données lus par le principal (comme `pompeVideCave`, `Thermo-Hygrometre`, `autres` sur la cave). |

## 3. Objectifs, non-objectifs, anti-objectifs

**Objectifs**
- Un JSON modèle versionné qui décrit tout persist du parc :
  - le socle commun ;
  - l'identité et ses dérivations ;
  - les blocs optionnels avec leurs conditions ;
  - les questions ;
  - les gabarits cenv/`.h` par puce ;
  - le lien bloc → modules Berry à charger.
- Une page 7900 qui produit les fichiers suivants, et les écrit dans une seule transaction après diff et validation :
  - `_persist.json`, `autoexec.be`, éventuellement `graphiques.json` et les squelettes `.be` ;
  - la section du cenv ;
  - la section du `.h`.
- Un modèle qui ne se périme pas en silence : fusion automatique des clés nouvelles à l'ouverture, bouton à la
  demande, banc qui échoue si un persist du dépôt n'est pas couvert.
- Un schéma JSON à jour, qui valide les 8 persists existants et chaque persist généré.

**Non-objectifs (version 1)**
- Préremplir depuis une carte existante (la page 7800 le fait par copie).
- Saisir les relais/boutons/capteurs (action « éditeur d'éléments » du plan).
- Modifier un env existant (dernière action du plan, en pause).
- Lancer un build, commiter, toucher `default_envs`.
- Corriger les anomalies relevées pendant l'exploration :
  - `serveur.adressMAC` (dans le persist) et `serveur.adresseMAC` (ajoutée à l'exécution) coexistent ;
  - `udp.telePeriod` et `rangeExtender.telePeriod` n'ont pas de lecteur.
  Décision du 2026-10-27 : **ces clés sont laissées telles quelles** (le modèle les porte comme les persists), et
  le plan prévoit une **analyse en lecture seule** (lecteurs, écrivains, effet d'un retrait ou d'une fusion), rendue à
  l'utilisateur qui décidera.

**Anti-objectifs (ce qui serait un échec même si « ça marche »)**
- Un mot de passe qui transite par la page, apparaît dans un diff non masqué, ou s'écrit dans un fichier hors dépôt
  (sauvegardes de transaction exceptées).
- Un persist généré qui active un bloc dont le module est **exclu** du LittleFS ou absent de l'autoexec, ou l'inverse.
- Une modification du comportement de la page 7800 ou de ses bancs.
- Une écriture pendant un build (`builds_en_cours()` vrai ou `None` = refus).
- L'historique proposé sur un ESP32 sans PSRAM (règle du 2026-10-13).
- Une modification de `data/fs/*.be` (fichiers de l'utilisateur, à ne pas toucher sans accord).
- Une page annoncée prête sans avoir tourné dans un vrai navigateur (leçon du 2026-10-16).

## 4. Constat sur les persists (exploration du 2026-10-27)

Huit persists suivis hors `*sauvegarde*`. Analyse par JSON, preuves dans la conversation.

**Racine**
- Ordre stable des blocs : `diverses, serveur, template, modules, drivers`.
- L'ordre des clés à l'intérieur de chaque bloc est stable aussi ; le générateur doit le respecter (ordre du modèle).

**Format texte**
- UTF-8 sans BOM, accents non échappés.
- Tabulations, mais pas homogènes. Aucun fichier n'est un `json.dumps` canonique.
- Fins de ligne CRLF dans l'arbre de travail (`core.autocrlf=true`). Le persist de la cuve a l'attribut git `text` désactivé.
- Un persist **généré** peut être sérialisé proprement : tabulation, `ensure_ascii=False`, fin de ligne du dépôt.

**Clés constantes sur les 8**
- `diverses` : logs, profils, `telePeriod`, fuseau horaire, localisation.
- `serveur.mqtt` : hôte, port, utilisateur.
- `serveur.IP` : sous-réseau, DNS.
- `serveur.rangeExtender.AP` : adresse et sous-réseau.
- `udp.port`.
- Les mots de passe forment **deux familles** (comparées par empreinte le 2026-10-27, jamais affichées) :
  - le mot de passe du Wi-Fi de la maison ;
  - un second, commun à `mqtt.mdp`, `rangeExtender.AP.mdp` et `serveurFTP.mdp` sur les 8 cartes.
  Le Wi-Fi d'un esclave est le point d'accès de son maître : ses `reseau1`/`reseau2.mdpWifi` valent donc le second.
  Le `reseau2` du P4 aussi.

**Identité et ses dérivations**
- `typeESP` ∈ {ESP32, ESP32S3, ESP32P4}. Il fixe la longueur de `template.GPIO` : 36, 38 ou 55.
- `template.GPIO` est **recalculé au démarrage** (`configGlobal::configGlobalByJson`). Le générateur écrit un tableau
  de `1` de la bonne longueur ; le `USER_TEMPLATE` du `.h` reprend le même tableau.
- `serveur.nom`, `serveur.hostname`, `template.NAME`.
- `mqtt.client` = hostname ; `mqtt.groupTopic1` = `tasmotas/<lieu du dossier>` (vrai sur les 8).
- `mqtt.topic` **ne suit pas** le dossier : `jardin/cuve` pour une carte rangée dans `garage`, `garage` seul pour le
  P4, `garage/niveau` pour le serveur-modbus S3. C'est donc une **saisie**, avec `<lieu>/<nom>` comme défaut
  (comme `fichiers_berry_creation::identite_par_defaut`).
- `rangeExtender.AP.SSID` = hostname + `-GATEWAY`.
- `IP.IPAddress` (`0.0.0.0` = DHCP), `IP.IPGateway`.
- `wifi.reseau1` / `reseau2` et leur nom de réseau, `wifi.power`, `wifi.timerRebootSansWifi`.
- `fuseauHoraire.typeReglageHeure` ∈ {NTP, RTC, UDP}. RTC ⇒ `drivers.I2C.environnement.DS3231.activation` à ON.

**Rôle** (constat : différentiel et cave ESP32 en id 0 avec Range Extender OFF ; cave S3, grenier, P4,
serveur-modbus S3 en id 0 avec Range Extender ON ; cuve et rideau en id 2 et 3)
- Autonome : id 0, `rangeExtender.activation` OFF, Wi-Fi choisi parmi les réseaux connus du dépôt.
- Maître : id 0, `rangeExtender.activation` ON, même choix de Wi-Fi. Seules ces cartes apparaissent dans la liste
  des maîtres d'un esclave.
- Esclave (cuve, rideau) :
  - id ≥ 1 ;
  - `wifi.reseau1` = `<HOSTNAME DU MAÎTRE>-GATEWAY` ;
  - passerelle 192.168.4.1 ;
  - `rangeExtender.ipMaitre` renseigné ;
  - `wifi.power` et `timerRebootSansWifi` à 0.
  La même chose côté `.h` : `STA_SSID1`, `WIFI_GATEWAY`, `WIFI_DNS`.

**Blocs optionnels**
- `diverses.historique` : 6 cartes sur 8.
- `serveur.coprocesseur` : P4 seulement, déjà géré par `fichiers_berry_coprocesseur.py`.
- Drivers :
  - `I2S`, `Ethernet`, `voletRoulants` ;
  - `HostedESPC6`, broches LoRaWan (P4 seulement) ;
  - `leds.ledRGB` ;
  - les entrées `TasmotaSlaveModBusN`.
- Activations : `serveur.udp`, `tcp`, `discovery`, `rangeExtender` ; `drivers.ModBus`, `I2C`, `ADS1115`, `LoRaWan`,
  `voletRoulants`, `leds.ruban`, `SD`.

**Bloc métier `modules.<fonction>`**
- Forme commune : `name, activation, reglage, log, [logs], environnement{boutons, interrupteurs, relais,
  analogiques, capteurs, compteurs, thermometres}`.
- Lecteur : `controleXxx.be` du dossier de la carte, chargé par `demarrage.chargeFichier("controleXxx", "modules.xxx")`.

**Lien persist → démarrage**
- `data/fs/demarrage.be::demarrage_activation` lit `<bloc>.activation` ; un bloc absent vaut « OFF ».
- Les autoexec à jour ne contiennent que la liste ordonnée des appels `demarrage.*` (exemple :
  `data/garage/tasmota32s3-capteurs-cuve-modbus/autoexec.be`).
- Deux autoexec gardent l'ancien style `chargeModule` : cave ESP32 et serveur-modbus S3. Le modèle ne s'en inspire pas.

**Solidification**
- Listes partagées `[berry_commun]` du cenv : `socle`, `modbus`, `historique`.
- Chaque env compose `custom_berry_solidify` à partir d'elles, plus ses modules propres ; il exclut par
  `custom_files_exclude` ce qu'il ne charge pas.

**Schéma existant**
- `outils_docs/schemas/persist.schema.json` est **inféré** par `berry/genere_schema_persist.py`.
- Il est périmé : `serveur.coprocesseur` absent.
- `--valide` échoue sur le différentiel et la cave ESP32. La règle « `required` si présent dans ≥ 50 % des parents »
  rend obligatoires `diverses.historique` et `leds.ledRGB`.
- Il ne contient ni défaut, ni `pattern`, ni `enum` pour `typeESP`, ni règle de cohérence.

## 5. Ce qui est construit

### 5.1 Le JSON modèle — `outils_docs/schemas/modele_persist.json`

Écrit à la main, versionné, lu par la page et par les bancs. Contenu attendu (la forme exacte est laissée au
constructeur, §8) :

- **Socle** : chaque chemin de clé constant, avec sa valeur. Les 5 chemins de mots de passe sont marqués
  `secret` : leur valeur est **absente du modèle**. Au moment de générer, le serveur la reprend d'un persist du
  dépôt selon une règle fixe :
  - le mot de passe d'un réseau Wi-Fi est celui que le dépôt associe déjà à ce **nom de réseau** ;
  - pour `<HOSTNAME>-GATEWAY`, c'est le `rangeExtender.AP.mdp` du maître ;
  - `mqtt.mdp`, `AP.mdp` et `serveurFTP.mdp` : valeur commune du parc.
  - Un réseau inconnu du dépôt ou une valeur commune absente donnent un **refus** explicite (pas de devinette).
  - Le `.h` (`STA_PASS1/2`, `WIFI_RGX_PASSWORD`) suit la même règle.
- **Identité** : les questions (puce, lieu, nom, IP, réglage de l'heure) et les **dérivations** listées au §4. Les
  règles de nommage (`nom_env`, `define`, dossier) sont celles de `fichiers_berry_creation` et de `transform_name`.
- **Rôles** : pour chaque rôle, les valeurs imposées, dans le persist **et** dans le `.h`.
- **Blocs optionnels** :
  - la question (libellé, aide) et les puces permises (historique : S3/P4) ;
  - les dépendances (ADS1115 ⇒ I2C ; RTC ⇒ DS3231 ; UDP du ModBus ⇒ `serveur.udp`) ;
  - le contenu du bloc (activé et désactivé) ;
  - les **modules Berry** qu'il fait solidifier, exclure et charger, avec leur **place** dans l'autoexec.
    L'ordre de chargement compte, voir les commentaires de l'autoexec de la cuve : `controleGeneral` avant
    `i2c_ads1115`, `demarrage.leds()` et `demarrage.historique()` avant le module métier.
- **Bloc métier** : gabarit de `modules.<fonction>` à `environnement` vide, et gabarits des squelettes `.be`.
- **Gabarits par puce** :
  - base PlatformIO proposée par défaut ;
  - longueur de `GPIO` ;
  - gabarit de section cenv : `extends`, `build_flags` avec `-D FIRMWARE_…`, les trois listes, `custom_files_upload` ;
  - gabarit de section `#elif` du `.h` : `CODE_IMAGE_STR`, `PROJECT`, `USER_TEMPLATE`, Wi-Fi, passerelle, DNS,
    `STA_SSID1/2`, Range Extender, MQTT. Les mots de passe y sont des marqueurs remplis côté serveur.
- **Marques « à compléter »** : une clé ajoutée par la mise à jour automatique porte une marque que la page affiche
  (pas de question, défaut deviné).

### 5.2 Le moteur de génération (Python, `outils_docs/scripts_python/outils_pc/`)

- Il prend les **réponses** (JSON envoyé par la page, sans secret) et le modèle, et rend sans rien écrire :
  - le texte du persist, ordre des clés du modèle ;
  - l'autoexec, avec l'en-tête de commentaire des autoexec actuels ;
  - `graphiques.json` si l'historique est activé ;
  - les squelettes `.be` si demandés ;
  - la section cenv et la section `.h` ;
  - les avertissements et les refus ;
  - le diff (masqué par `fichiers_berry_creation::_masque`) ;
  - l'empreinte.
- **Refus** : ceux de `fichiers_berry_creation::_refus` (env, dossier, define déjà pris ; noms invalides ; base
  inconnue), plus :
  - historique sur ESP32 ;
  - esclave sans maître ;
  - dépendance non satisfaite ;
  - persist généré invalide pour le schéma ;
  - nom de fonction métier invalide, ou déjà porté par un `controleXxx.be` de `data/fs`.
- **Avertissements** : id, IP, topic ou client déjà pris (`_prises`, à étendre aux ids).
- **Écriture** : `fichiers_berry_sauvegarde.Transaction`, refus pendant un build, contrôle d'empreinte. Mêmes règles
  que `fichiers_berry_creation::cree`, dont la section cenv et la section `.h` réutilisent l'insertion
  (`_insere_cenv`, insertion dans le `.h`).
- **Réutilisation** : le moteur actuel suppose une carte modèle (`_calcule` copie cenv, `.h` et dossier). Le
  constructeur choisit comment partager le code sans changer le comportement de la page 7800 : extraire des
  fonctions communes, ou appeler les fonctions existantes avec du contenu généré.
  Contrainte : **tous les bancs `test_fichiers_berry_*.py` restent verts sans modification de leurs attentes.**
- **Contrôle de cohérence** sur le résultat, avant le diff :
  - tout bloc à « ON » a ses modules dans l'autoexec et sur le FS ou en flash ;
  - tout module chargé par l'autoexec n'est pas dans `custom_files_exclude` ;
  - l'id est le même dans les 4 blocs.

### 5.3 La page 7900

- **Disposition A** (maquette validée) :
  - pastilles d'étapes cliquables : Carte, Réseau, Fonctions, Bloc métier, Vérification ;
  - formulaire à gauche ;
  - aperçu du `_persist.json` à droite, recalculé à chaque saisie, par le serveur ou en local à partir du modèle
    (au choix du constructeur ; aucun secret dans l'aperçu).
- **Étape Réseau**, pour un esclave :
  - liste des maîtres du dépôt (cartes à id 0 avec Range Extender activé, lues dans les persists) ;
  - id proposé : le plus petit libre, la liste des ids pris affichée ;
  - un doublon est un avertissement (carte remplaçante).
- **Étape Fonctions** : cases par bloc optionnel. Celles interdites pour la puce sont grisées, avec la raison. Les
  dépendances cochent ou expliquent.
- **Étape Vérification** :
  - fichiers qui seront écrits ;
  - validation du schéma ;
  - avertissements ;
  - autoexec généré ;
  - diff complet masqué ;
  - bouton « Créer l'env ». Il est grisé dès qu'une saisie change après le diff, comme sur la 7800.
- **Après création** :
  - liens vers `http://127.0.0.1:7700/?env=<env>` et `http://127.0.0.1:7800/?env=<env>` ;
  - **résumé à copier** : env, dossier, define, rôle, id, IP, topic, blocs activés, fichiers écrits.
- **Mise à jour du modèle** : bandeau au chargement si l'ouverture a ajouté des clés (§5.4), et bouton « Mettre à
  jour le modèle ».
- **Socle commun** : `acces_web.py` (jeton, lien console, `--local`, `--sans-navigateur`), en-tête `X-…` sur les POST,
  POST un par un sous verrou, codes d'erreur comme `fichiers_berry_web::fabrique_gestionnaire`, bandeau des
  opérations interrompues (`fichiers_berry_sauvegarde.interrompues`).
- **Intégration**, sur le modèle de la page 7800 :
  - `annuaire_registre.py::OUTILS` : groupe Maintenance, port 7900, arrêt libre ;
  - id ajouté à la liste figée de `test_annuaire.py` ;
  - cible Custom `build/cible_assistant_persist.py`, page démarrée détachée ;
  - enregistrement dans `pre_utilitaires_platformio.py` et `CIBLES_HORS_BUILD` ;
  - `.claude/hooks/garde_build.py::CIBLES_OUTILS` ;
  - tâche `.vscode/tasks.json`. Exception à la règle « ne pas toucher `.vscode/` » : les tâches des outils y sont
    déjà, selon le précédent des autres pages.
  - Mode d'emploi dans `outils_docs/README.md` ; entrée dans la carte des documents de `CLAUDE.md`.

### 5.4 La fidélité du modèle

- **Moteur de comparaison** : chemins de clés des persists suivis hors `*sauvegarde*` ↔ chemins du modèle. Il rend :
  - les clés **nouvelles** (dans au moins un persist, pas dans le modèle) ;
  - les clés **disparues** (dans le modèle, dans aucun persist) ;
  - les **défauts divergents** (constante du modèle ≠ valeur commune à tous les persists) ;
  - les **blocs** apparus.
- **À l'ouverture de la page** (décision 15), automatiquement :
  - les clés nouvelles sont ajoutées au modèle ;
  - défaut = valeur la plus fréquente, sauf secret (marqué `secret`, sans valeur) ;
  - marque « à compléter » ;
  - écriture par `Transaction` (sauvegarde) ;
  - bandeau listant les ajouts.
  Les clés disparues et les défauts divergents sont **signalés, pas appliqués**.
- **Bouton « Mettre à jour le modèle »** : même comparaison à la demande. Il propose aussi le retrait des clés
  disparues et l'alignement des défauts, avec un diff, et n'écrit qu'après validation.
- **Banc de couverture** : échoue si un persist du dépôt contient un chemin absent du modèle, et si une clé du modèle
  est encore « à compléter » (un modèle mis à jour en automatique doit être relu).
- Un build ou une synchro du fork n'a pas à attendre l'assistant : le modèle se rattrape à la prochaine ouverture.

### 5.5 Le schéma

- `genere_schema_persist.py` est corrigé : la règle `required` ne doit plus rendre obligatoires des blocs optionnels
  (`diverses.historique`, `leds.ledRGB`…). Le constructeur choisit de quelle façon ; le modèle peut lui fournir la
  liste des blocs optionnels.
- Le schéma est régénéré, `serveur.coprocesseur` compris. `--valide` passe sur les 8 persists.
- Le moteur de génération valide chaque persist produit contre ce schéma : un échec est un refus.
- Les secrets n'ont pas de valeur dans le schéma.

### 5.6 Choix du rédacteur (après la relecture du 2026-10-27, à contester si besoin)

Ces points n'ont pas été tranchés par l'utilisateur. Ils sont fixés ici pour que le plan ne devine pas.

- **Wi-Fi d'une carte autonome ou maître** : choisi dans la liste des noms de réseau connus du dépôt (`MAISON`,
  `Relai Wifi Cave`…). Pour un esclave : `reseau1` et `reseau2` = `<HOSTNAME DU MAÎTRE>-GATEWAY`, comme la cuve et
  le rideau. Mots de passe : règle du §5.1.
- **Ids** : maître et autonome à 0 ; esclave ≥ 1, défaut = le plus petit id ≥ 1 non pris dans le parc. Un seul
  maître par réseau, donc pas de maître hors id 0.
- **`rangeExtender.AP.SSID`** est toujours écrit (`<HOSTNAME>-GATEWAY`), même Range Extender OFF : le `.h` en a
  besoin (`WIFI_RGX_SSID`), et c'est ce que font le différentiel et la cave ESP32.
- **Base PlatformIO** : choisie dans la liste des bases de la puce (`fichiers_berry_etat::envs_proposes`, famille
  « bases »). Par défaut, la base la plus utilisée par les cartes de cette puce. L'historique dépend de la **puce**
  (S3/P4), comme la règle du 2026-10-13. Les bases S3 du dépôt sont toutes N16R8, donc avec PSRAM.
- **Structure de l'autoexec**, calquée sur celui de la cuve :
  - `demarrage.importe([...])` ;
  - `demarrage.compileSocle()` ;
  - `demarrage.compile([...], "<bloc>")` par bloc ;
  - lignes `demarrage.charge([...])` **inconditionnelles du socle** : `controleGeneral`, `controleLedTemoin`,
    `controleWeb`, plus les modules dont `init()` porte la garde. Le modèle les liste ; elles ne dépendent pas d'un
    bloc ;
  - lignes conditionnées par un bloc ;
  - `demarrage.leds()` et `demarrage.historique()` avant le module métier ;
  - `demarrage.chargeFichier("controle<Principal>", "modules.<principal>")` en dernier.
  
  L'ordre vient du modèle (rang par ligne), pas de l'ordre des cases cochées.
- **Module métier** : `xxxFonctions.be` et `controleXxx.be` restent dans le dossier de la carte, **non solidifiés**,
  comme `cuveFonctions` et `controleCuve` : `demarrage.compile(["xxxFonctions"], "modules.xxx")` puis
  `chargeFichier`. Rien n'est ajouté à `custom_berry_solidify` pour eux.
- **Noms de bloc métier** : `[a-z][a-zA-Z0-9]*` (camelCase, comme `pompeVideCave`), car le nom sert aussi au nom
  des fichiers `.be`. Les noms historiques à tiret (`Thermo-Hygrometre`) restent valides dans les persists existants
  et dans le modèle ; ils ne sont simplement pas proposés à la création.
- **Section `.h`** : gabarit par puce, qui reprend les lignes communes des sections existantes de cette puce, dont
  `SET_ESP32_STACK_SIZE` (24 Ko sur les S3 depuis l'audit P2.1).
- **Environnement vide** : avant la page, le moteur doit prouver qu'un persist généré avec un `environnement` vide
  et des squelettes démarre. Pour cela, un instantané de démarrage d'un env généré est ajouté au banc
  `berry/banc_demarrage.py` (`bouchons_berry/demarrage/<env>.txt`). Si `controleGeneral` ou `configModules` refusent un
  `environnement` vide, le gabarit du bloc métier porte les sous-objets vides attendus (`boutons: {}`…), qu'il
  porte déjà.

## 6. Ordre du plan (actions)

1. **Modèle + banc de couverture + schéma** : modèle écrit à partir des 8 persists, schéma corrigé et régénéré.
2. **Moteur de génération** : persist, autoexec, `graphiques.json`, squelettes, cenv, `.h`, cohérence, diff,
   écriture transactionnelle. Bancs sur une copie temporaire du dépôt (comme `test_fichiers_berry_creation.py::depot_essai`).
3. **Page 7900, disposition A** : intégration annuaire, cible Custom, tâche VS Code, sonde Chrome.
4. **Fidélité du modèle** : comparaison, fusion à l'ouverture, bouton, bandeau.
5. **Éditeur d'éléments** (décision 4) :
   - relais, boutons, interrupteurs, capteurs, compteurs, thermomètres, analogiques : nom, broche, type,
     `relaisLie`, `idModBus` ;
   - contrôle des conflits de broches et de la plage de la puce.
6. **Documentation** : README, `CLAUDE.md`, mémoire.
7. **Modification d'un env existant** (décision 9) : en pause, déclenchée par l'utilisateur.

Chaque action se termine par ses bancs verts, un témoin qui doit échouer (règle 7 de `tasks/lessons.md`) et un
commit `git commit -- <chemins>`.

## 7. Vérification attendue

- **Rejeu du parc** : pour chaque carte au format actuel (hors autoexec à l'ancien style), on déduit les réponses de
  son persist, on régénère, on compare au vrai persist sur les clés couvertes par le modèle.
  - Les écarts doivent être expliqués : environnement métier vide, `template.GPIO` à `1`, clés « à compléter ».
  - C'est la preuve que le modèle décrit le parc.
  - Témoin : une clé retirée du modèle doit faire échouer le rejeu.
- **Cohérence croisée** : un persist généré + son autoexec + ses listes cenv passent le contrôle de §5.2. Témoin : un
  bloc activé dont le module est exclu doit être refusé.
- **Secrets** : aucun mot de passe dans les réponses HTTP de la page (banc qui cherche les 5 valeurs réelles dans
  toutes les réponses). Diff masqué.
- **Page** : sonde Chrome (modèle `test_fichiers_berry_page_chrome.py`) ; chaque étape s'affiche ; aucune erreur JS ;
  la saisie met l'aperçu à jour ; le bouton « Créer » est grisé après une saisie.
- **Pas de régression** : `test_fichiers_berry_*.py`, `test_annuaire*.py`, `build/test_garde_build.py`,
  `genere_schema_persist.py --valide`.
- **Fumée réelle** (avec l'utilisateur) : création d'un env de test, `pio run -e <env>` par la page build hors
  d'un autre build, puis suppression de l'env par la page 7800.

## 8. Laissé au constructeur

- La forme exacte du JSON modèle (clés, imbrication), tant qu'il porte tout ce que liste le §5.1.
- Le découpage en modules Python et le partage de code avec `fichiers_berry_creation.py`, sous la contrainte du §5.2.
- Le calcul de l'aperçu : côté serveur ou côté navigateur.
- Le contenu du `graphiques.json` initial (un `{"affichage": {}, "groupes": {}}` minimal est acceptable) et celui
  des squelettes `.be` (charte des logs du `CLAUDE.md`, compilés par `berry/verifie_berry.py` dans le banc).
- Les fins de ligne des fichiers générés : celles du dépôt (CRLF dans l'arbre de travail), comme le fait
  `fichiers_berry_creation::_eol`.

## 9. Contraintes du dépôt rappelées

- Ne jamais écrire pendant un build. Aucune cible PlatformIO lancée par le constructeur pendant un build de
  l'utilisateur.
- Commits en français sans accents, `git commit -- <chemins>`, pas de push sans demande.
- Fichiers < 500 lignes, sauf exception décidée par l'utilisateur. Ne jamais compresser des commentaires pour tenir
  la limite (leçon du 2026-10-18).
- `data/fs/*.be` non modifiés.

## 10. Avenant du 2026-10-29 — reprendre, modifier et supprimer un env existant (action A10)

Déclenché par l'utilisateur le 2026-10-29. Il lève, pour la page 7900, la décision 2 (« pas de préremplissage
depuis une carte existante ») et les non-objectifs « Préremplir depuis une carte existante » et « Modifier un env
existant ». Le reste de la spec s'applique tel quel (mots de passe, build en cours, transaction, `data/fs/*.be`).

### 10.1 Demandes de l'utilisateur

1. Reprendre un env existant dans la page et le modifier.
2. Toute modification d'un paramètre, dans n'importe quel onglet, réactive « Voir le diff », y compris après une
   création ou une modification réussie.
3. « Créer l'environnement » devient « Modifier l'environnement » quand l'env renseigné existe déjà.
4. Supprimer un env depuis la page : sa section du cenv, sa section de `user_config_override.h` et le dossier créé.
   **Le dossier est renommé `…-sauvegarde`** (choix du 2026-10-29, comme la page 7800), rien n'est effacé.
5. Avant une suppression, la page présente **chacun des éléments touchés** et l'utilisateur les vérifie avant de
   valider.

### 10.2 Principe de la modification : appliquer un écart, jamais régénérer

Les fichiers d'une carte ont pu être retouchés à la main (clés propres, ports dans le cenv, lignes du `.h`). On ne
les régénère donc jamais. On génère deux fois :
- **A** = ce que l'assistant produirait à partir des réponses **relues** de la carte (`reponses_depuis_persist`) ;
- **B** = ce qu'il produirait à partir des réponses **modifiées** dans la page.

Seul l'écart A → B est appliqué au vrai fichier ; tout ce qui n'est pas dans l'écart reste octet pour octet.
- **Persist** : écart par chemin JSON (valeur changée, clé ajoutée, clé retirée), appliqué dans le texte. Les
  objets sont parcourus, jamais remplacés en bloc : une clé propre à la carte, absente du modèle, survit.
- **Autoexec, section du cenv, section du `.h`** : écart ligne à ligne (blocs de `difflib` entre A et B), appliqué
  seulement si les lignes de A concernées se retrouvent telles quelles dans la vraie section. Sinon (ligne retouchée
  à la main), **toute la modification est refusée**, et le refus cite le fichier et les lignes, mots de passe masqués
  (décision de l'utilisateur du 2026-10-29).
- A et B sont générés avec les **vrais** mots de passe, côté serveur : un changement de réseau Wi-Fi change aussi
  le mot de passe. Aperçu, diff et erreurs restent masqués (`***`).
- **Propriété attendue** : sans aucun changement dans la page, l'écart est vide et rien n'est écrit, pour chaque
  carte du parc.

### 10.3 Ce qui se modifie, ce qui est figé

- Figés : lieu, nom, puce et base (renommer est le rôle de la page 7800 ; changer de puce ou de base, c'est créer
  une autre carte).
- Modifiables : tout le reste des questions (réseau, rôle, heure, identité, blocs, métiers, éléments).
- Un métier ajouté suit les règles de la création (squelettes) ; un fichier déjà présent dans le dossier n'est
  jamais écrasé. `graphiques.json` et les autres fichiers du dossier ne sont pas touchés.
- Contrôles « déjà pris » : l'env, son dossier et son define ne sont pas contrôlés contre eux-mêmes ; l'identité
  (IP, topic, client) l'est contre les **autres** cartes (avertissement, comme à la création).
- Empreinte : cenv, `.h`, modèle, persist et autoexec de la carte, env et saisie.

### 10.4 La page

- Étape « Carte » : liste « Env » = « (nouvel env) » + les cartes existantes ; « Charger » remplit toutes les
  étapes avec les réponses relues. Lieu, nom, puce et base deviennent non modifiables.
- Si lieu + nom (+ puce) saisis correspondent à un env existant, le bouton devient « Modifier l'environnement » et
  un bandeau propose « Charger ses réglages ».
- Après une création ou une modification réussie, la page reste sur cet env en mode modification.
- « Supprimer cet env… » (mode modification) : panneau listant section du cenv, section du `.h` (define),
  `default_envs` / `data_dir`, dossier renommé (nouveau nom), refus (envs dépendants), avertissements et diff ;
  une case « J'ai vérifié ces éléments » active « Supprimer ». Moteur : `fichiers_berry_suppression.py`, inchangé.

### 10.5 Vérification attendue

- Rejeu du parc : chaque carte chargée puis préparée sans changement donne un écart vide.
- Aller-retour : une modification puis la modification inverse redonnent les fichiers d'origine, octet pour octet.
- Clé propre à une carte, port du cenv, ligne ajoutée à la main dans le `.h` : conservés après une modification.
- Mots de passe : jamais dans une réponse HTTP, diff, erreur ou sortie de banc.
- Fumée réelle avec l'utilisateur sur l'env de test `tasmota32p4-cellier-controleur` : modifier, compiler, supprimer.
