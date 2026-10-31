---
chantier: jauges-cuve
titre: Page dédiée « Niveau de la cuve » (jauges A, H et B), lien depuis l'encadré de la cuve
statut: actif
cree: 2026-10-31
maj: 2026-10-31
source: squishy-imagining-raven.md
objectif: Afficher volume (jauge A), taux (jauge H) et tensions brute et recalculée de la sonde (cadran B) de la cuve sur une page dédiée ouverte depuis son encadré, sur la cuve et le P4
---
# Page dédiée « Niveau de la cuve » (jauges A, H et B)

## Demandes ajoutées en cours de route (2026-10-31)
- Les fichiers de la page ne partent **que** sur les envs qui s'en servent (cuve, P4) : liste `berry_commun.page_cuve`.
- Les fichiers Berry sont destinés à être **solidifiés** (`cuvePageFonctions` dans le firmware de la cuve et du P4) ;
  les gabarits HTML/CSS/JS vont dans `data/sd`.
- Un **cadran B** (ECharts natif) montre la tension **brute** (entrée de l'ADS1115, après le pont) et la tension
  **recalculée** de la sonde (0-10 V = brute × rapport du pont).
- L'**encadré de l'accueil** montre aussi ces deux tensions.
- Sur le P4, la tension recalculée vient **de la cuve par ModBus** (choix de l'utilisateur, une seule source de vérité) :
  appareil `analogique5` de la cuve (id 5 -> registre 4708, mV entiers, sentinelle comprise), lu par l'`analogique2` du
  P4 (`idModBus 5`). Aucun module solidifié touché (exploration du 2026-10-31 : `modbusFonctions.executeCmdModbus` sert
  tout appareil analogique actif à `4704 + id - 1`).

## Contexte
Catalogue des jauges consigné le 2026-10-31 dans `outils_docs/jauges/` (commit `docs(jauges)`). Décision de
l'utilisateur : **premier essai** sur une page dédiée contenant les 2 jauges, **A** (liquide animé, ECharts +
echarts-liquidfill) pour le **volume en litres**, **H** (demi-cercle SVG) pour le **taux en %** ; un lien dans
l'encadré « niveau de cuve » de la page d'accueil ouvre cette page.

Ce que l'exploration a établi :
- L'encadré `data/sd/html/webSensorNiveauCuve.html` est rempli par `gestionFileFolder.readFileByLineReplaceAndWebSend`
  depuis deux cartes actives : la cuve (`controleCuve.be::CAPTEURS_CUVE.web_sensor`) et le maître P4
  (`data/garage/tasmota32p4-serveur-modbus/controleGarage.be::CONTROLE_GARAGE.web_sensor`, qui recalcule). Un
  `<a href>` y fonctionne ; un `<script>` non (zone remplacée par `innerHTML` toutes les ~2 s). Seul précédent de
  lien dans la zone capteurs : `controleCoprocesseur.be` (`/coprocesseur`).
- Les valeurs substituées sont des chaînes avec unité (`"53%"`, `"4174L"`) : la page dédiée prendra des nombres.
- **Source des valeurs** : `GET /histo?n=mesures&p=direct` (`historiqueFonctions::page`/`valeursDirectes`),
  déjà présente sur la cuve et le P4 (historique ON) : séries `…niveauCuve.volume`, `…niveauCuve.tauxRemplissage`
  (fraction, ×100). Réponse 404 pendant les 2 min qui suivent un démarrage.
- **ECharts 6.1.0** est déjà servi par `/graphiques?f=echarts.js.gz` (`graphiquesFonctions.FICHIERS`,
  `envoieFichier` par morceaux de 2 Ko), décompressé par la page (`graphiques.js::chargeECharts`, cache
  localStorage `echarts-6.1.0`). La nouvelle page réutilise la même URL et la même clé : ECharts n'est pas
  retéléchargé si `/graphiques` a déjà été ouvert.
- Dimensions : cuve `modules.cuve.dimensions` ; P4 `modules.garage.environnement.analogiques.analogique1.dimensions`.
  Le volume max (L × l × h / 1000) est injecté dans la page par Berry (`window.CUVE`), comme `window.GRAPHIQUES`.
- `pre_utilitaires_platformio.py` copie `data/sd` sur toutes les cartes ; les fichiers ECharts sont exclus des
  ESP32 classiques (cave, bureau) dans `platformio_tasmota_cenv.ini` : les nouveaux fichiers y seront ajoutés.
- Point ouvert : **echarts-liquidfill 3.1.0 vise ECharts 5** ; compatibilité avec la 6.1.0 à prouver d'abord (A1).

Choix de conception (minimum pour un essai) :
- Route **`/cuve`**, déclarée par les drivers des 2 cartes qui ont l'encadré (cuve, P4), module importé à la
  première requête seulement (pas de RAM au repos, pas d'ordre d'import dans l'autoexec).
- Page = `data/sd/html/cuve.html` + `data/sd/css/cuve.css` + `data/sd/js/cuve.js`, envoyés par
  `gestionFileFolder.readFileByLineAndContentSend` (règle du dépôt : pas de gabarit en chaînes dans un .be).
- Extension `data/sd/js/echarts-liquidfill.min.js.gz`, servie par une entrée de plus dans
  `graphiquesFonctions.FICHIERS` (`?f=liquidfill.js.gz`) : `envoieFichier` et le contrôle d'accès sont réutilisés.
- Rafraîchissement par `/histo?p=direct` toutes les 10 s (cadence par défaut de `/graphiques`).
- Lien dans le `<legend>` de l'encadré (pas de cellule ajoutée : leçon du 2026-10-31).

## A1 — Compatibilité echarts-liquidfill avec ECharts 6.1.0
- [x] Rendu Chrome sans fenêtre (scratchpad) : ECharts 6.1.0 décompressé de `data/sd/js/echarts.min.js.gz` + liquidfill 3.1.0 → série `liquidFill` dessinée, console sans erreur — preuve : `--dump-dom` du 2026-10-31, journal « echarts 6.1.0 / series liquidFill=1 / elements=9 / maj ok, elements=8 », aucun `ERREUR`, SVG des vagues et du libellé « 4174 L » présent
- [x] Si incompatible : s'arrêter et demander à l'utilisateur (repli possible : jauge liquide en SVG, modèle E du catalogue) — preuve : compatible (étape précédente), sans objet
- [x] `data/sd/js/echarts-liquidfill.min.js.gz` ajouté (taille notée), version dans une constante comme `VERSION_BIBLIOTHEQUE` — preuve : 3 429 o, archive npm 3.1.0 conforme au sha512 du registre, .min.js identique au fichier d'A1 ; `cuvePageFonctions.VERSION_EXTENSION = "liquidfill-3.1.0"`

## A2 — Module Berry de la page `/cuve`
- [x] `data/fs/cuvePageFonctions.be` : `route(dimensions)` (contrôle `check_privileged_access`), envoi de `cuve.css`, `cuve.html`, `window.CUVE` (volume max, hauteur, bibliothèques), `cuve.js` ; logs selon la charte — preuve : `data/fs/cuvePageFonctions.be::route`/`page`, hook `verifie_berry_edition` sans erreur ni écart
- [x] Extension servie par `/cuve?f=liquidfill.js.gz` — preuve : `cuvePageFonctions.FICHIERS` + `graphiquesFonctions.envoieFichier` réutilisé ; `graphiquesFonctions` est SOLIDIFIÉ (`berry_commun.historique`) : le modifier aurait imposé un nouveau firmware, il reste intact
- [x] Route `/cuve` déclarée dans `CAPTEURS_CUVE` (cuve) et `CONTROLE_GARAGE` (P4) avec leurs dimensions respectives — preuve : `controleCuve.be::CAPTEURS_CUVE.web_add_handler`/`pageCuve`, `controleGarage.be::CONTROLE_GARAGE.web_add_handler`/`pageCuve` (non solidifiés)
- [x] Hook `verifie_berry_edition` vert sur chaque .be modifié — preuve : aucune erreur ni avertissement renvoyé aux 4 éditions ; `banc_cuve.py` 142/142

- [x] Module solidifié dans le firmware de la cuve et du P4 — preuve : `#@ solidify:cuvePageFonctions`, ajouté au `custom_berry_solidify` des 2 envs (`ProjectConfig` : entrée lue sans commentaire) ; `solidifie_et_compile_berry.py` : 4 closures, 0 anonyme, « LE .h COMPILE »

## A3 — Page web (HTML, CSS, JS)
- [x] `cuve.html` + `cuve.css` : jauge A (litres) et jauge H (%), état « mesure indisponible » et « historique pas encore prêt (404) » — preuve : `banc_cuve_page.py` OK (61 contrôles, 8 scénarios Chrome : normal, valeurs null -> « Mesure indisponible », 404 -> « Historique pas encore démarré »)
- [x] `cuve.js` : chargement ECharts (même URL et clé de cache que `/graphiques`) puis liquidfill ; lecture `/histo?n=mesures&p=direct` toutes les 10 s ; séries trouvées par suffixe `niveauCuve.volume` / `niveauCuve.tauxRemplissage` ; seuils 20 % / 40 % ; valeurs tracées exposées en attributs `data-` pour la sonde — preuve : `banc_cuve_page.py` : volume/taux tracés = valeurs servies, chemin du P4 préfixé trouvé par suffixe, extension absente -> taux gardé ; témoin (`* 100` retiré dans une copie) -> ECHEC (6), code 1
- [ ] Bouton « Retour » vers l'accueil

## A4 — Lien depuis l'encadré
- [x] `<a href='/cuve'>` dans le `<legend>` de `webSensorNiveauCuve.html` — preuve : `data/sd/html/webSensorNiveauCuve.html` (lien « (jauges) » dans la légende, aucune cellule ajoutée) ; rendu à vérifier en A6
- [x] `banc_cuve.be` (contrôle du gabarit) mis à jour et vert — preuve : le banc bouchonne `gestionFileFolder` (seul le chemin du gabarit est contrôlé, inchangé) : rien à modifier ; `banc_cuve.py` « Controles : 142, echecs : 0 »

## A5 — Bancs
- [x] `outils_docs/scripts_python/berry/banc_cuve_page.py` sur le modèle de `banc_graphiques.py` : vraie `route()` sous bouchons, puis sonde Chrome (`--dump-dom`, serveur local qui imite `/histo`, `/graphiques?f=`) : volume et taux tracés = valeurs servies, cas 404 et `null` — preuve : `outils_docs/scripts_python/berry/banc_cuve_page.py` + `.be` : BANC_CUVE_PAGE: OK (61) ; Chrome lancé en mouvement réduit, un nouvel essai annoncé si Chrome sans fenêtre se bloque (machine saturée, scénario pris au hasard)
- [x] Témoin : un mutant (taux non multiplié par 100) fait échouer la sonde — preuve : copie de `cuve.js` sans `* 100` -> BANC_CUVE_PAGE: ECHEC (6), code 1 (run isolé du sous-agent)
- [x] `banc_graphiques.py` toujours vert — preuve : `banc_graphiques.py` (Chrome compris) : BANC_GRAPHIQUES: OK, 7 min 44

## A6 — Build et essai sur les cartes
- [x] Nouveaux fichiers exclus de TOUS les envs sauf cuve et P4 (demande de l'utilisateur du 2026-10-31 : une page ne part que sur les cartes qui s'en servent) — preuve : liste `berry_commun.page_cuve` ajoutée à 6 listes + 5 envs de base ; `ProjectConfig` : 13 envs « exclue », P4 et cuve « embarquée », piscine (ESP8266, sans pré-script, ne copie rien de data/)
- [ ] Persists de la cuve et du P4 sauvegardés depuis les cartes AVANT tout envoi (diff carte / dépôt relu)
- [ ] Firmware (module solidifié) ET FS de la cuve et du P4 envoyés (page build : compiler + téléverser + FS), aucun autre build en cours ; firmware plus récent que le dernier commit
- [ ] Relevé ModBus 4708 vu au sniffeur ou dans le log du P4 (valeur = tension de la sonde de la cuve en mV)
- [ ] Capture Chrome de l'accueil des 2 cartes : lien visible, largeur de page inchangée (mesurée avant/après)
- [ ] Capture Chrome de `/cuve` sur les 2 cartes : jauges A et H aux valeurs de l'encadré

## A7 — Documentation
- [x] `outils_docs/README.md` (mode d'emploi), `outils_docs/jauges/README.md` (A et H en service), carte des documents de `CLAUDE.md` ; `verifie_references_docs.py` code 0 — preuve : § « Les jauges du niveau de la cuve » (jauges A, H, B, tensions, ModBus), fiche du catalogue, carte des documents, `PROTOCOLE_MODBUS.md` ; `verifie_references_docs.py` : 0 défaut, code 0

## A8 — Tension recalculée sur la cuve et encadré de l'accueil
- [x] `cuveFonctions.montageSonde` (rapport du pont tiré de `i2c_ads1115.montage`, garde si le pilote n'a pas `montage`) et `sensorsCuve.valeursAnalogiques.tensionSonde_V` au centième — preuve : `banc_cuve.py` 148/148 (§ 9 bis : pont 24k/10k -> 3,4, shunt et pilote ancien -> absente) ; témoin (`/ 100` au lieu de `/ 10` dans une copie) -> « ECHEC … 1.02 V », code 1
- [x] Encadré de l'accueil (cuve) : lignes « Tension brute (ADS1115) » en mV et « Tension sonde (recalculée) » en V, affichées même en erreur de mesure — preuve : `controleCuve.be::CAPTEURS_CUVE.web_sensor`, gabarit `webSensorNiveauCuve.html` ; `banc_cuve.py` : « '-,--V' sans montage connu », « 6,8 V -> '6.80V' »
- [x] Encadré de l'accueil (P4) : mêmes lignes, tension recalculée lue par ModBus (A10) — preuve : `controleGarage.be::CONTROLE_GARAGE.tensionSonde` (web_sensor « %.2fV » ou « -,--V », json_append `tensionSonde_V`) ; `banc_cuve_page.py` § 4b : 6800 mV -> 6,8 V, défaillant -> nil, désactivée -> nil

## A9 — Cadran B des tensions sur la page `/cuve`
- [x] `cuve.html`/`cuve.css`/`cuve.js` : cadran ECharts à 2 anneaux (sonde 0..sondeMax_V, brute 0..entreeMax_V), valeurs en texte et en `data-tension-*` ; échelles de `cuveFonctions.montageSonde` dans `window.CUVE.sonde` (défaut 3,3 V / 10 V sur le P4) — preuve : `cuve.html`, `cuve.css`, `cuve.js::traceTensions` ; `cuveFonctions.montageSonde` passé par `controleCuve.pageCuve`, nil sur le P4
- [x] Banc `banc_cuve_page.py` : tensions tracées = valeurs servies, tension recalculée absente -> « -,-- » — preuve : `banc_cuve_page.py` : 2.00 / 6.80, textes « 2,00 »/« 6,80 », absente -> '' et « -,-- », tensions tracées sans volume ni taux, SVG dans `#c_tension`

## A10 — Tension recalculée transmise par ModBus (cuve -> P4)
- [x] Cuve : `analogique5` (id 5, type 4704, virtuel non ADS) au persist ; `cuveFonctions` y écrit la tension de la sonde en mV entiers et appelle `modbusFonctions.noteMesure(4708)` — preuve : persist de la cuve (`analogique5`, virtuel `Calcul_tensionSonde`) ; `banc_cuve.py` 151/151 : analogique5.value = 10200 mV, notes [4704, 4708] ; témoin (ancienne boucle) -> `key_error: analogique2`
- [x] P4 : `analogique2` -> `activation ON`, `virtuel ModBus_TasmotaSlaveModBus1`, `idModBus 5` ; `controleGarage.web_sensor` et `json_append` publient `tensionSonde_V` (V, au centième ; sentinelle -> « -,-- ») — preuve : persist du P4 (`analogique2` idModBus 5) ; `controleGarage.be::CONTROLE_GARAGE.tensionSonde` ; `banc_cuve_page.py` § 4b
- [x] Bancs : `banc_cuve.py` (valeur et noteMesure 4708), `banc_test_modbus.py` toujours vert ; décodeur du sniffeur : 4708 nommé — preuve : `banc_cuve.py` 151/151, `banc_test_modbus.py` BANC_MODBUS: OK, `test_sniffeur_modbus.py` 154/154 ; `decodeur_modbus.charge_carte()` nomme 4708 « Tension sonde (recalculée) » d'après le persist du P4
- [x] `PROTOCOLE_MODBUS.md` : registre 4708 de la cuve documenté — preuve : `PROTOCOLE_MODBUS.md` § sentinelle : paragraphe « Valeur calculée servie par l'esclave »

## Améliorations restantes
- [ ] [projet] Pleine échelle de l'ADS1115 : Tasmota remet ±6,144 V à chaque détection (`Ads1115Detect`) et le P4 suppose 6 144 mV en dur ; si `Sensor12 S1` est un jour posé, le P4 se trompe d'un facteur 1,5 (exploration du 2026-10-31)
- [ ] [projet] Ancien maître S3 gelé : son `controleGarage.be` ne remplit pas les 2 nouvelles lignes du gabarit partagé (`#…#` en clair s'il est rallumé)
- [ ] [projet] Factoriser le chargeur ECharts commun à `graphiques.js` et `cuve.js` si l'essai est adopté
- [ ] [projet] Le P4 ne borne pas le taux à 0..100 % et n'a pas le correctif de troncature de la cuve (`controleGarage.be`, constaté à l'exploration)
- [ ] [projet] Ancien maître S3 (`tasmota32s3-serveur-modbus`) : il partage l'encadré, le lien y mènera à une page absente
- [x] [projet] Solidifier `cuvePageFonctions` si l'essai est adopté — preuve : fait dès le premier essai, à la demande de l'utilisateur (A2)

## Vérification
- Bancs : `banc_cuve_page.py` (code 0, témoin rouge), `banc_cuve.py`, `banc_graphiques.py` (Python de PlatformIO, cf. skill `bancs`).
- Relecture : agent `relecteur-berry` sur les .be modifiés avant commit.
- Sur carte : captures Chrome de l'accueil et de `/cuve` (P4 et cuve) ; valeurs de la page = valeurs de l'encadré ; ouverture de `/cuve` puis `/graphiques` : ECharts non retéléchargé (cache commun).
