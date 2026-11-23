# Carte des documents (detail des outils et fonctions)

Tire de `CLAUDE.md` le 2026-11-23 (plan `binomes-berry`, A11). A FONDRE dans `outils_docs/guides_outils/`
(un guide par outil) et `outils_docs/reference_berry/` a l'action A20 du meme plan. L'aiguillage est `outils_docs/INDEX.md`.

## Carte des documents de ce depot

Pour ne pas chercher : ce qui a ete produit et ou.

Dans les documents durables (ce fichier, `outils_docs/README.md`, `SOLIDIFICATION_BERRY.md`,
`PROTOCOLE_MODBUS.md`, `CARTE_MODULES_BERRY.md`, `.claude/skills`, `agents`, `commands`), renvoyer au code par
`fichier::fonction`, jamais par numero de ligne : un numero se decale a chaque modification. Controle :
`python outils_docs/scripts_python/maintenance/verifie_references_docs.py` (code 1 = renvoi faux). Les documents
dates (audits, diagnostics, specs, `ANALYSE_*`) gardent leurs numeros : ce sont des traces.

- `CLAUDE.md` (ce fichier) — regles du depot, synchro du fork, montage d'un nouveau poste,
  PermissionError.
- `.claude/hooks/verifie_synchro_fork.sh` — hook `SessionStart` : signale le retard du fork
  sur l'amont (detecteur seul, ne synchronise pas). Declare dans `.claude/settings.json`.
- `.claude/hooks/garde_build.sh` + `garde_build.py` — hook `PreToolUse` (Bash, PowerShell) : refuse un
  `pio run` si un `platformio run` ou un `scons` tourne (`pio home` ignore). Filtre `if` : ne se lance
  que si la commande contient `pio`/`platformio`. Un chemin vers `pio.exe`/`platformio` passe en ARGUMENT
  (enrobeur, script de mesure) compte comme un `pio run` (`garde_build.py::est_pio`, incident du 2026-10-31). Un `pio run` (et son scons) dont TOUTES les cibles sont des
  cibles d'outils (`CIBLES_OUTILS` = les `NOM_CIBLE` des `build/cible_*.py`) n'est PAS un build : l'outil vit
  tant que la cible vit, la page de build l'attendrait sans fin. `__idedata`, une cible melee ou un scons sans
  cible lisible restent des builds ; lancer une cible d'outil pendant un vrai build reste refuse. Une cible
  d'outil qui DEMARRE compte comme un build pendant ses 30 premieres secondes (son demarrage peut purger
  `.pio/build`) : age par `CreationDate` dans la meme requete PowerShell. Banc
  `outils_docs/scripts_python/build/test_garde_build.py` (verifie aussi que la liste = les `NOM_CIBLE`).
- `.claude/hooks/reprise_limite.py` — hook `StopFailure` (`rate_limit`), demande du 2026-11-01 : a la limite
  d'utilisation, demarre une veille detachee qui retente `claude -p --resume <session>` toutes les 15 min (8 jours au
  plus, abandon apres 3 echecs qui ne sont pas des limites), dans le mode de la conversation (jamais bypassPermissions).
  Ne change jamais de compte. Jamais de session en double (2026-11-13) : rien n'est lance tant qu'un processus Claude
  vivant tient la conversation (registre `~/.claude/sessions/<pid>.json`, onglet VS Code compris) ; arret si le
  transcript a recu une vraie reponse depuis la limite. Journal `%LOCALAPPDATA%\outils_tasmota\reprise_limite\journal.log` ; banc
  `.claude/hooks/test_reprise_limite.py` (ne prouve pas le declenchement reel).
- `.claude/hooks/rappel_apres_compactage.sh` — hook `SessionStart` (`compact`) : rappelle de mettre
  a jour la reprise.
- `.claude/hooks/verifie_berry_edition.sh` + `.py` — hook `PostToolUse` (Edit, Write, MultiEdit) : apres
  chaque edition d'un `data/**/*.be` par Claude (hors `*sauvegarde*`), `verifie_berry.py <fichier>` (~0,8 s) ;
  erreur Berry ou verification impossible -> code 2, l'erreur revient a Claude ; ecarts a la charte des logs
  seuls -> code 0, avertissements renvoyes en `additionalContext` (audit P7.6). Filtre `sh` : rien n'est lance
  pour un autre fichier. Banc hors depot (faux depot + temoin verificateur absent) ; partie 5 de
  `berry/test_verifie_berry_charte.py` (faux depot : erreur, ecarts, fichier propre).
- `.claude/skills/bancs/` — skill : quel banc lancer pour quel fichier modifie, commande exacte (Python de
  PlatformIO pour `outils_pc/`, pyserial), lecture vert/rouge, pieges (bancs Berry sans code de sortie,
  `test_rs485_pc.py` n'est pas un banc, `--reel` = reseau).
- `.claude/agents/relecteur-berry.md` — sous-agent de relecture des `.be` modifies avant commit : syntaxe,
  charte des logs, RAM, regles du depot, bancs Berry lances. Ne modifie rien.
- `.claude/agents/relecteur-pages-web.md` — sous-agent de relecture des pages web (pages des outils PC generees par Python,
  pages servies par les cartes `data/sd`) avant commit : securite (XSS, anti-CSRF, SSRF), etat de la page, JS valide, mode sombre,
  sondes Chrome hermetiques. Ne modifie rien.
- `.claude/agents/` (2026-11-14) — 7 autres sous-agents de lecture seule : `verificateur-solidification` (module `data/fs` solidifiable :
  builtin masque, `custom_berry_solidify`, `globs`), `controleur-secrets` (avant commit ou push, n'affiche jamais une valeur),
  `relecteur-outils-python`, `verificateur-plans` (preuves des cases cochees), `analyste-journaux-build`, `diagnostic-synchro-fork`
  (ne synchronise jamais), `relecteur-docs`, `auditeur-menage` (commande `/menage`, propositions de rangement), `preparateur-push` (verdict avant tout push), plus `relecteur-pcb` et
  `placeur-pcb`. Huit ont `memory: local` (dossier `.claude/agent-memory-local/`, ignore par git). Liste complete, modeles et quand les
  lancer : `outils_docs/SOUS_AGENTS.md`.
- `.claude/skills/pcb-tasmota/` — skill PCB KiCad des cartes du fork (schema, placement, routage, fabrication) ; agents `placeur-pcb` et `relecteur-pcb`.
- `build/cible_pont_serie.py` — cible Custom « Pont serie » (`pont_serie.py`), importee par le pre-script ou posee en `extra_scripts` d'un env ESP8266.
- Atelier des visuels d'accueil, http://127.0.0.1:7985 (2026-11-13, plan `tasks/plans/atelier-visuels.md`, spec `docs/superpowers/specs/2026-11-13-atelier-visuels-accueil-design.md`) :
  `outils_pc/atelier_visuels_web.py` (+ `atelier_visuels_web_routes.py`, `_icones_web.py`, `_ia.py`, `_fond.py`, `_description.py`, `_ecriture.py`, `_suivi.py`, `_consignes.py` (lien et rappel des consignes, 2026-11-15), `_page*.py`) ;
  photo ou dessin vectorise en fond, points chauds (voyant, valeur, liaison), ecrits dans `data/<lieu>/<carte>/visuel.json` + fond. Cote carte : `data/fs/visuelFonctions.be`
  + `controleVisuel.be`, moteur `data/sd/js/visuel.js`. Maquettes `outils_docs/visuels_accueil/`. Bancs `berry/banc_visuel.py`, `test_atelier_visuels_*.py`. Mode d'emploi : `outils_docs/README.md` § « Atelier des visuels d'accueil (page web) ». Tuile de l'annuaire (groupe Ateliers), tache VS Code « Outil : atelier des visuels » et cible Custom detachee `build/cible_atelier_visuels.py` (`NOM_CIBLE` atelier_visuels, banc `build/test_cible_atelier_visuels.py`). Le bouton « Televerser » arrive sur la page Build par `depuis=visuel` (`build_page_atelier.py::AT_ORIGINES`). Port 7985 (le 7990 est a l'organigramme des plans, decide le 2026-11-14).
- `.claude/commands/commite.md`, `.claude/commands/fin-de-session.md` — commandes `/commite`,
  `/fin-de-session` ; `.claude/skills/logs-cartes/` — skill de lecture des logs.
- `tasks/export-session-*.md` — mini-exports de passation ecrits par `/fin-de-session`.
- `.claude/mods/` — marketplace locale `mods-tasmota` ; mod `meteo-contexte` : UNE barre coloree de
  remplissage du contexte et cout de la session, au-dessus du prompt (terminal, et panneau VS Code 2.1.301 :
  la bande y est dessinee, contrairement a la doc ; a defaut, ligne de statut + pane). Au-dela de 45 %, le
  bouton « Preparer la passation » (`/fin-de-session`) est **toujours** visible ; toast unique. Sans processus
  ni reseau. Banc hors depot (hote simule). Modifier le mod = monter `version` dans `plugin.json`, puis
  `claude.cmd plugin marketplace update mods-tasmota` et `claude.cmd plugin update meteo-contexte@mods-tasmota`.
  Installation : `/plugin marketplace add <depot>/.claude/mods` puis `/plugin install meteo-contexte@mods-tasmota`.
- `.claude/mods/suivi-sous-agents/` — mod, portee UTILISATEUR (installe pour tous les projets, pas seulement ce depot) : volet
  de progression des sous-agents (tache en cours, % d'apres leur liste TodoWrite, duree). Une consigne TodoWrite est ajoutee a chaque lancement de
  sous-agent ; le volet montre aussi le journal des outils et les remarques de chaque agent en cours. Commande `/sous-agents` (rouvre le volet).
  Banc : `claude plugin test .claude/mods/suivi-sous-agents`. Mise a jour comme `meteo-contexte` : monter `version` dans `plugin.json`, puis
  `claude.cmd plugin marketplace update mods-tasmota` et `claude.cmd plugin update suivi-sous-agents@mods-tasmota`.
- `.claude/mods/suivi-plan/` — mod : recopie le plan valide (ExitPlanMode) dans `tasks/plans/`, ligne
  d'avancement (`$.ui.status`), resume du plan actif injecte a chaque conversation, `/suivi`, fichier signal
  `%USERPROFILE%\.claude\suivi-plan\signal.json` qui ouvre la vue. Parseur partage avec l'extension :
  `hooks/parseur-plan.mjs` (banc `node .claude/mods/suivi-plan/tests/test_parseur.mjs`, avec mutants).
  Plan PAR CONVERSATION (0.2.0, 2026-10-18) : rattache par ExitPlanMode, edition d'un plan, `/suivi ouvrir`,
  `/suivi suivre <chantier>` ; `/suivi detacher` le lache. Ecrit `...\suivi-plan\conversations\<session>.json`,
  et a chaque message un signal `ouvrir: false` (ecrit AVANT le traitement du message). Depuis 0.3.0, la
  ligne d'avancement et le bloc injecte montrent d'abord le plan de la conversation.
  Banc : `claude.cmd plugin test .claude/mods/suivi-plan`.
- `outils_docs/vscode/suivi-plan/` — extension VS Code `fdaubercy.suivi-plan` : vue du plan a droite (%
  par action, ameliorations restantes), barre d'etat. Installation : `maintenance/installe_suivi_plan.py`.
  Suit l'onglet de conversation Claude actif (`conversations.js` : libelle d'onglet = titre du transcript
  tronque comme l'extension Claude 2.1.301 ; banc `test_conversations.js`) ; plans et conversations gardes en memoire
  entre deux bascules (0.4.3, 2026-11-13 : ~400 ms de blocage de l'hote par bascule ; banc `test_cache.js`) ; journal « Suivi du plan »
  (panneau Sortie) : une ligne par bascule. Libelles en collision : les conversations NON rattachees des
  30 derniers jours comptent (ambiguite affichee, pas de plan devine) ; un message envoye depuis un onglet
  lui apprend sa conversation ; un signal d'une autre conversation que l'onglet actif est ignore.
  Panneau Claude en barre laterale : aucune API ne dit quelle conversation y est affichee -> seuls le
  signal « message envoye » et la ligne d'avancement de la conversation le couvrent.
  Depuis 0.4.0 (reglage `suiviPlan.ouvrirAvecConversation`, vrai par defaut) : la vue S'OUVRE d'elle-meme quand
  la conversation active suit un plan (message envoye ou bascule vers son onglet), une fois par conversation et
  par fenetre ; refermee a la main, elle ne se rouvre pas pour cette conversation (`C.ouvrirPourConversation`).
- `tasks/plans/` — un plan suivi par chantier ; format et regles de calcul dans `_FORMAT.md`.
- `tasks/README.md` — index des plans (demande du 2026-10-29) : objectif (cle `objectif:` de l'en-tete),
  statut, % de chaque plan. **A tenir a jour a chaque progression d'un plan** : le tableau est regenere par
  `node .claude/hooks/index_plans.mjs` (parseur du mod, memes % que la vue de droite), automatiquement par le
  hook `PostToolUse` `index_plans_edition.sh` quand Claude edite un `tasks/plans/*.md`, et par l'extension
  `suivi-plan` (>= 0.4.1, `extension.js::regenereIndex`) a TOUTE modification d'un plan tant que VS Code est ouvert
  (Bash, main, recopie par le mod a ExitPlanMode) ; `--verifier` = code 1 si en retard.
  Nouveau plan : lui donner une cle `objectif:`. Banc `node .claude/hooks/test_index_plans.mjs`.
- `tasks/lessons.md` — journal des erreurs et regles.
- `tasks/reprise-modbus-garage.md` — reste du chantier ModBus garage (rideau, BUS_SERIE_MUET, cuve) ; anciennes reprises
  (ModBus « grenier », solidification) dans `tasks/archive/`.
- Firmware du coprocesseur Wi-Fi ESP32-C6 des P4 (2026-10-26) : `data/fs/controleCoprocesseur.be` (solidifie sur le P4,
  exclu des autres envs comme `controleES8311.be`), bloc persist `serveur.coprocesseur`. Au demarrage seulement : `Hosted`
  lu en local (C6 a jour -> aucun acces reseau) ; en retard -> ligne d'alerte sur l'accueil + UNE requete `Range` de
  512 o sur `<url>/v<Host>/network_adapter_<MCU>.bin` (version lue dans l'en-tete d'image), nouvel essai horaire, 6 au
  plus. Page `/coprocesseur` (gabarit `data/sd/html/coprocesseur.html`), bouton -> `HostedOta <URL complete>` ;
  resultat suivi par une regle `HostedOta`/`HostedLoad` : `Failed <code>` -> « echec » sur l'accueil et la page, bouton
  « Reessayer » ; `Failed 5379` = C6 BLOQUE (bug esp-hosted-mcu #143, flash serie seul remede) : cle persist
  `serveur.coprocesseur.bloque`, ni bouton ni requete, ligne d'accueil la 1re minute apres le demarrage seulement. Cle posee dans
  le persist du DEPOT (un flash serie reecrit le FS) : P4 du garage, et toute nouvelle carte P4 par
  `fichiers_berry_coprocesseur.VERSION_BLOQUEE` (regle du 2026-10-27). Version visee = `Host` (bibliotheque du firmware P4), PAS le fichier par defaut du serveur (en retard). Option `"mqtt": "ON"`
  (ON sur le P4) : `tele/<topic>/COPROCESSEUR` RETENU, a chaque changement d'etat et a chaque `Mqtt#Connected` (le JSON
  SENSOR n'est pas touche). Nouvel env : `outils_pc/fichiers_berry_coprocesseur.py` (appele par
  `fichiers_berry_creation._calcule`) pose ou neutralise l'alerte selon la PUCE de la base (persist, autoexec, cenv).
  Bancs `berry/banc_coprocesseur.py` (+ rendu Chrome), `outils_pc/test_fichiers_berry_creation.py`. Mode d'emploi :
  `outils_docs/README.md` ; plan `tasks/plans/alerte-firmware-c6.md`.
- Graphiques des cartes S3/P4 (2026-10-18) : page `/graphiques` (bouton d'accueil) servie par
  `data/fs/graphiquesFonctions.be` (route et bouton declares par le driver `HISTORIQUE_WEB` de
  `historiqueFonctions.be`), gabarit `data/sd/html/graphiques.html` + `data/sd/css/graphiques.css`, logique
  `data/sd/js/graphiques.js` (+ `graphiques_trace.js` : trace ECharts d'un graphique, `graphiques_edition.js` : mode
  edition ; page COMPOSABLE (A9) : composition enregistree par `POST /graphiques` dans la cle `graphiques` de
  `/json/graphiques.json`, `graphiquesFonctions.enregistre`/`valideComposition`), ECharts 6 COMPRESSE `data/sd/js/echarts.min.js.gz` (Berry ne pose pas Content-Encoding :
  la page le decompresse, cache localStorage versionne) ; temps reel par `/histo?p=direct` (cadence de la liste
  « Direct » de la page, 10 s par defaut) ; series DECOUVERTES dans le JSON SENSOR
  par `data/fs/historiqueSeries.be` (ni relais, ni entrees, ni volets, ni internes ; persist : `exclues`, `ajouts`,
  `compteurs`) ; reglages de la page (`affichage`, `groupes`, `rafraichissement`, `direct`) dans `data/<lieu>/<carte>/graphiques.json` -> `/json/`,
  HORS persist (le persist est en RAM en permanence) ; `diverses.historique.grafana` reste au persist ; sans historique actif, la cle `.grafana` donne un bouton
  « Historique (Grafana) » sur l'accueil (`controleWeb.boutonGrafana`, solidifie, toutes les cartes). Mode d'emploi : `outils_docs/README.md` § « Les graphiques
  des mesures » ; banc `berry/banc_graphiques.py` (+ `.be`, `banc_historique.be`, `bouchons_berry/graphiques/` et `historique/`) ; plan `tasks/plans/graphiques-web.md`.
- `outils_docs/Schémas de branchement - Attribution des PINS des modules/<lieu>/<env>/Brochage GPIO - <env>.xlsx` — un
  classeur par carte (2026-11-08) : image de la carte, une ligne Excel par broche (cases fusionnees A:B / D:E, Arial,
  pointilles), usages tires du `_persist.json` (blocs actifs) puis COMPLETES A LA MAIN ; cartes a borniers : colonnes a
  texte vertical. Generateurs `outils_pc/genere_brochage_excel.py` (cartes `CARTES` : S3 DevKitC-1, DevKitC V4, P4) et
  `genere_brochage_horizontal.py` (ESP32 Relay x8, Waveshare 8DI-8RO), par Excel (pywin32, Python systeme) ; ne
  reecrivent jamais un classeur existant. Banc `outils_pc/test_genere_brochage.py`.
  **Disposition imposee (2026-11-22)** : la photo de la carte est vue de dessus (tournee et rognee au besoin : `rotation`, `crop`, `agrandit`
  de l'entree de `genere_brochage_horizontal.py::CARTES`), chaque vis a sa case en face d'elle (haut ou bas de l'image, texte vertical, nom de la
  vis, GPIO et usage du persist). Borniers en haut et en bas : texte vertical (`genere_brochage_horizontal.py`) ; borniers sur les cotes : image tournee
  pour que les intitules soient HORIZONTAUX (`genere_brochage_lateral.py`, cles `gauche` et `droite`). Seuls les GPIO ABSENTS de l'image vont dans le tableau a part « GPIO hors bornier ». Jamais de tableau
  general a cote de la photo ; ce qui n'est pas verifie (ordre des vis, numerotation) est dit dans la case et dans `notes`. Exemple : carte
  `esp32-relay-x4-modbus` (portail de jardin).
- Classement des cartes par lieu (2026-11-11, plan `tasks/plans/classement-par-lieu.md`, maquettes `outils_docs/filtre_lieu/`) :
  `outils_pc/lieux.py` = SEULE table des lieux (2e segment du nom d'env ; `EXCEPTIONS` vide depuis le 2026-11-12), `puce()`, et le JS
  `remplitParLieu` (listes `<optgroup>` des pages 7700 a 7980) ; banc `test_lieux.py`. Les routes `/envs`, `/parc`, `/cartes`
  ajoutent `lieu` (et `puce` pour la page Build) et `lieux`. Bascule « Classer par » de l'onglet Build : `build_page_lieux.py`,
  sonde `test_build_page_lieux_chrome.py` ; intertitres de l'onglet Fichiers : `build_page_fichiers.py::fichiersCartes`.
  Nouveau lieu : une ligne dans `lieux.LIEUX`, rien d'autre.
  Lieu partage (2026-11-11, plan `tasks/plans/lieu-partage-syslog-mqtt.md`) : `lieux.py::identites` et `::pour_page_identites` (hote, topic
  et IP propre de chaque carte -> lieu, lus dans les persist) ; fonctions JS communes `lieuDeHote`, `lieuDeTopic`, `lieuDemande`,
  `bandeauLieu` (banc `test_lieux_js.mjs`). Puces « Lieu de travail » de l'annuaire : `annuaire_page_lieux.py` ; `?lieu=` mis en avant
  sur les pages 7700 a 7980 ; routes `GET /lieux` du syslog et du sniffeur MQTT (`sniffeur_mqtt_lieux.py`, `sniffeur_mqtt_panneaux.py`).
  Sondes `test_annuaire_lieux_chrome.py`, `test_syslog_page_chrome.py`, `test_sniffeur_mqtt_page_chrome.py`.
- `outils_docs/jauges/` — catalogue de 8 jauges pour afficher une mesure de capteur (2026-10-31) : images
  `jauge-A.png` a `jauge-H.png`, code `catalogue_jauges.html`, fiche `README.md`. **Choix retenu : A (liquide
  anime ECharts) ou H (demi-cercle SVG)**. Un gabarit `webSensor*.html` n'execute aucun script (zone remplacee
  toutes les ~2 s) : seuls les modeles SVG/CSS (D a H) s'y posent tels quels.
- `outils_docs/partitions/` — maquettes de l'onglet « Mémoire et partitions » de la page build (2026-11-01) : images
  `modele-A.png` à `modele-D.png`, code `maquettes_partitions.html`, contraintes `README.md`. **Choix retenu : B**. Pas
  encore réalisé : plan `tasks/plans/temps-compilation.md`, A7 à A10.
- Page `/cuve` (2026-10-31, premier essai, plan `tasks/plans/jauges-cuve.md`) : jauges A (volume en L) et H (taux en %)
  de la cuve, lien « (jauges) » dans la legende de `webSensorNiveauCuve.html`. Module `data/fs/cuvePageFonctions.be`
  (route declaree par `controleCuve.be::CAPTEURS_CUVE` et `controleGarage.be::CONTROLE_GARAGE` du P4), page
  `data/sd/{html,css,js}/cuve.*`, extension `data/sd/js/echarts-liquidfill.min.js.gz` ; valeurs par `/histo?p=direct`.
  Fichiers embarques sur la cuve et le P4 SEULEMENT : liste `page_cuve` de `[berry_commun]` dans le
  `custom_files_exclude` de tous les autres envs (regle : une page ne part que sur les cartes qui s'en servent).
  Banc `berry/banc_cuve_page.py`. Mode d'emploi : `outils_docs/README.md`.
- Page `/energie` du differentiel (2026-11-02, plan `tasks/plans/energie-differentiel.md`) : kWh et couts par heure, jour, mois gardes en flash, courbe de puissance 24 h ; `data/fs/energieFonctions.be` + `controleEnergie.be` (SOLIDIFIES, charges par l'autoexec, garde `diverses.energie`), `data/sd/{html,css,js}/energie.*` et `energieTarifs.*` (sous-page de Configuration : tarifs Base ou HC/HP) ; liste `page_energie` de `[berry_commun]` exclue de tous les autres envs. Banc `berry/banc_energie.py`. Mode d'emploi : `outils_docs/README.md`.
  Depuis le 2026-11-08 (palier 4 de l'atelier, spec `docs/superpowers/specs/2026-11-08-atelier-energie-differentiel-design.md`, plan `tasks/plans/energie-atelier.md`) la page se dessine d'apres `/json/energie_page.json` (routes `f=description`, `f=mois`, `f=direct` elargi ; repli sur la page d'avant si absente ou refusee ; 16 elements, 4096 o) ; ecrite par la destination « Energie » de l'atelier (`outils_pc/atelier_energie_description.py`, `atelier_graphiques_energie.py`, `atelier_graphiques_page_energie.py`, `cas_energie.json`) ; `energieFonctions` etant solidifie, firmware a recompiler une fois par la page Build. Bancs `berry/banc_energie_routes.py`, `banc_energie_description.py`, `outils_pc/test_energie_rendu.mjs`, `test_atelier_energie_description.py`, `test_atelier_graphiques_energie.py`, sonde `test_atelier_energie_page_chrome.py`.
- Visuel des volets et réglage de leurs durées (2026-11-11, spec `docs/superpowers/specs/2026-11-11-visuel-volets-reglage-durees-design.md`, plan `tasks/plans/visuel-reglage-volets.md`, maquettes `outils_docs/volets_visuels/`) : façade dessinée sous les curseurs de la page d'accueil (grenier du RDC, P4 du garage, grenier du 2e étage ; rideau du garage depuis le 2026-11-12, position lue chez le P4 par `controleRideau.be::route`, banc `berry/banc_rideau_facade.py`), qui rejoint la position lue du curseur `s27<n>` (ou l'angle du MPU6050 d'une trappe) à la vitesse du volet ; page `/volets` (Configuration > « Réglage des volets ») qui mesure `tempsMontee` et `tempsDescente` par les appuis (sens imposé par l'étape, porte de garage en chronomètre). Modules `data/fs/vrReglage.be` et `vrPages.be` (SOLIDIFIÉS, utilisés si `drivers.voletRoulants.facade.activation` vaut `ON`), `vrFonctions.be::commandeSens`, `::configBoutons`, `::enReglage`, appelés par `controleVoletRoulants.be` ; page `data/sd/js/volets.js`, `data/sd/{html,css,js}/reglageVolets.*` ; liste `volets_pages` de `[berry_commun]`, exclue des envs sans volets ; description dans la clé `facade` du persist (bloc du driver et de chaque VR). Bancs `berry/banc_reglage_volets.py`, `berry/banc_inclinaison.py`, `outils_pc/test_volets.mjs`, sondes `outils_pc/test_volets_chrome.py` et `test_reglage_volets_chrome.py`. Mode d'emploi : `outils_docs/README.md` § « Visuel des volets et réglage de leurs durées ».
- Debits de la nourrice de chauffage sur DEUX cartes (2026-11-09, plans `tasks/plans/debitmetres-chauffage.md` et
  `tasks/plans/debits-deux-cartes.md`, spec `docs/superpowers/specs/2026-11-09-debits-deux-cartes-design.md`, pas encore essayees sur carte). Acquisition `tasmota32s3-bureau-serveur-debits-pac`
  (esclave ModBus id 1, Range Extender id 1, sans ecran) : `debitsFonctions.be` + `controleDebits.be` du DOSSIER de la carte
  (pas `data/fs`), 6 voies (2 `FlowRateMeter` groupe `debitmetres`, 4 `Counter` groupe `compteurs` ; `nom` et `k` dans l'entree
  de chaque voie), bloc `DEBITS` du JSON SENSOR, capteur muet, commande `ReglageDebits` ; registres 4704 a 4710 (6 debits en
  centiemes de L/min, mot d'etats, bit 12 toujours a 1) et push UDP (`modules.debits.modbus`). Affichage
  `tasmota32s3-bureau-ecran-debits-pac` (maitre ModBus et Range Extender id 0, IP 192.168.0.51) sur un Waveshare
  ESP32-S3-Touch-LCD-7B (1024x600 RGB, GT911, RS485 16/15 ; fiche `WAVESHARE_ESP32-S3-Touch-LCD-7B.md` et docs constructeur dans
  `outils_docs/Schémas de branchement - Attribution des PINS des modules/bureau/tasmota32s3-ecran-debits-pac/`, A8 en cours : expandeur I2C 0x24 par `preinit.be`, HASPmota ou LVGL au choix du cenv, `custom_interface_ecran` et listes `custom_interface_ecran_<nom>` : fichiers des autres interfaces exclus du FS par `build/interface_ecran.py::applique`, banc `build/test_interface_ecran.py`) :
  `ecranDebitsFonctions.be` + `controleEcranDebits.be` du dossier de la carte, veille, commande `ReglageEcranDebits`. Lecture
  groupee et push multi-valeurs : `modbusFonctions.be::sertGroupe`, `modBus_TasmotaSlaveModBus.be::demandeGroupee` et
  `::eclateGroupe`, cles `drivers.ModBus.lectureGroupee`, `drivers.ModBus.periodeReleve` (`PROTOCOLE_MODBUS.md` § 9). Sniffeur :
  `sniffeur_modbus.py --persist affichage`. Historique et `/graphiques` (plan `tasks/plans/historique-debits.md`). Bancs
  `berry/banc_debits.py`, `banc_ecran_debits.py`, `banc_preinit_7b.py` (expandeur 0x24 du 7B), `banc_test_modbus.py`, `banc_demarrage.py`, `outils_pc/test_sniffeur_modbus.py`,
  essai de charge `outils_pc/essai_charge_debits.py`. Guide d'equilibrage `outils_docs/chauffage/` (texte) ; page animee
  `equilibrage.html` du dossier de l'acquisition, servie en `/equilibrage` par `equilibragePage.be` (joignable par
  `http://192.168.0.51:8080/equilibrage`) avec le code du mode carte `equilibrage_carte.js` (debits en direct, reglages gardes
  dans `/json/equilibrage.json`, relais pour un favori sans Referer ; plan `tasks/plans/equilibrage-par-la-carte.md`). Mode
  d'emploi : `outils_docs/README.md`.
- `outils_docs/EXTENSIONS_TAPP.md` — extensions Tasmota `.tapp` (2026-11-07) : format, cycle de vie, cas d'utilisation, gabarits
  A et B, envoi sur une carte, pieges (compilation avant `/autoexec.be`, formatage, image du FS). Essais sur carte : § 9, a faire (A10).
- `outils_docs/MODELES_ESP.md` — puces Espressif (ESP32, S2, S3, C2 a C61, H2 a H21, P4, S31, E22, ESP8266/8285/8089) au
  2026-11-11 : processeur, memoire et PSRAM, competences, montages a plusieurs ESP sur un typon, compatibilite Tasmota lue
  dans les envs ; P4 v1.x / v3.x (P4R3) et comment les distinguer ; modele Tasmota du Waveshare 8DI-8RO.
- `outils_docs/PLC_OPENPLC.md` — cours PLC (automate programmable) et OpenPLC (2026-11-15) : cycle de scrutation, langages IEC 61131-3,
  comparaison avec Tasmota/Berry, interet pour ce depot, listes de sites, lectures et videos (adresses NON verifiees, de memoire).
- `outils_docs/ECRAN_TACTILE_ESP32P4.md` — ecran tactile MIPI-DSI sur ESP32-P4 (recherche du 2026-11-11, rien d'essaye) :
  pilote uDisplay `DSI` (WIP), descriptions `EK79007_P4ev_DSI.ini` et `JD9165_DSI.ini`, envs P4 SANS affichage (pas de
  `FIRMWARE_LVGL`), RAM interne et correctifs de la discussion arendst #24448, Waveshare ESP32-P4-WIFI6-Touch-LCD-7B (EK79007
  + GT911, ecarts a l'`.ini` Espressif), dalles DSI du kit du garage, kits P4 avec ecran ou relais (aucun P4 a 8 relais).
- `outils_docs/FICHIERS_DRVSET.md` — inventaire des fichiers `.drvset*`/`.snsset*` du firmware : role, contenu, chargement, sauvegarde, effacement (2026-11-02).
- `outils_docs/sauvegarde_config/` — maquettes de l'onglet « Sauvegardes » de la page build (2026-11-02) : `modele-A.png` a `modele-C.png`, code `maquettes_sauvegarde.html`, contraintes `README.md`. Choix en attente, rien de realise.
- `outils_docs/SOLIDIFICATION_BERRY.md` — mecanisme, verification (§5), parametres, 13 pieges.
- `outils_docs/PROTOCOLE_MODBUS.md` — ModBus RTU/TCP standard, implementation maison (3 transports
  Serie/UDP/TCP), extension esclave->maitre, failles du mecanisme d'envoi, design de queue FIFO,
  carte des registres de la carte 16 relais (§8), architecture de synchronisation (§9).
- `outils_docs/ANALYSE_BERRY_MODBUS_DISCOVERY.md` — **historique** (etat du 2026-09-22, encadre de tete :
  numeros de ligne perimes, defauts du §2.3 corriges depuis le 2026-09-30) — fonctionnement des programmes ModBus
  Berry (3 transports, carte 16 relais, ESP32<->ESP32, push esclave->maitre) + audit de la
  table `/json/discovery.json` : formes ecrites/lues, 3 defauts bloquants la resolution
  d'IP en UDP, et tableau des elements restant a parametrer (importance/priorite/difficulte).
  §2.6 : cycle `forceEnvoiParams` -> `ImAlive` (presentation esclave -> maitre, usages de la
  table cote maitre, piege de la carte reaffectee) ; resume en tete de `data/fs/udpFonctions.be`.
- `outils_docs/DIAGNOSTIC_UDP_2026-10-17.md` — diagnostic UDP maitre <-> esclave (Range Extender /
  Wi-Fi classique) : matrice attendue, cause prouvee (AP de l'esclave en 192.168.4.1/24 -> ses envois
  vers le maitre partent par son AP), corrections C1-C7, plan des essais. Resume dans
  `PROTOCOLE_MODBUS.md` §9 (avec les resultats des essais). C1 a C6 appliques et valides sur les cartes le
  2026-10-17, dans les deux modes ; multicast du maitre par la box seulement si un esclave y est decouvert.
  La reference est `data/fs/udpFonctions.be` (le diff d'origine, supprime le 2026-11-23, reste dans l'historique git).
- Voie MQTT maitre/esclaves (2026-11-16, plan `tasks/plans/voie-mqtt.md`, analyse `outils_docs/ANALYSE_VOIE_MQTT_2026-11-16.md`) : le P4 du garage commande des esclaves Tasmota natifs (projecteur LED, pompe, cuve) par `cmnd/<topic>/...` avec garde-fous (G3 compare-avant-agir, G4 quarantaine, G5 coupe-circuit, accuses et renvois, alerte broker). `data/fs/mqttLiaisonFonctions.be` (SOLIDIFIE, pur, sans MQTT) et `controleMqttLiaison.be` (bloc `drivers.liaisonMqtt`, commande `ReglageMqttLiaison`), elements virtuels `MQTT_<nom>` dans `controleGeneral.be::set_power_handler`. Banc `berry/banc_mqtt_liaison.py` (mutants). Essais sur carte (2026-11-20 et 21) : ordres (A6, `recu` rend true), coupure du broker et alerte (A7), pompe de piscine ESP8266 sans Berry et bouton du maitre recale sur l'etat reel de l'esclave (A9, `controleMqttLiaison.be::recale`), lignes « perime » ; reste l'essai du portail de jardin (A10, jamais sans l'utilisateur) et la montee intermittente de la memoire Berry du P4 (cause inconnue, non reproduite le 2026-11-20, sonde relancee le 2026-11-21). Esclaves MQTT sans fiche ModBus (projecteur, pompe) : aucun repli (`PROTOCOLE_MODBUS.md` § 11). Mode d'emploi : `outils_docs/README.md` § « Voie MQTT maitre/esclaves ».
- Emulation Hue pour Alexa (2026-11-22) : `data/fs/hueFonctions.be::appareils` (liste blanche des sorties a cle `alexa`, Shutters refuses, ids natifs) et `controleHue.be` (pont `global.hue_bridge`, une chaine pour tout id ; `controleHue.be::regle` : FriendlyName masques puis `Emulation 2`, compares avant envoi) ; persist `serveur.emulationHue` (OFF au depot), cible de log `emulationHue`, liste `berry_commun.emulation_hue` (P4 du garage, cave S3, deux greniers). Banc `berry/banc_hue.py` (mutants). Pas essaye sur carte. Mode d'emploi : `outils_docs/README.md` § « Émulation Hue pour Alexa ».
- `outils_docs/AUDIT_MODBUS_2026-09-29.md` — audit complet ModBus garage (B1 corrige, secrets
  en clair sur depot public, defauts G1-G8 actifs, L1-L13 latents, ameliorations par priorite).
- `outils_docs/Electronique/Connecteur ModBus/` — docs constructeur de la carte 16 relais
  (`... commamd.docx` = jeu de commandes, `... Manual.docx` = caracteristiques).
- `docs/superpowers/specs/2026-07-15-solidification-berry-verdict.md` — verdict Q1/Q2/Q3.
- `outils_docs/scripts_python/`, range par usage le 2026-10-12. **Des scripts qui s'importent
  entre eux restent dans le MEME dossier** (import d'un module voisin) : ne pas les separer.
  - `build/` — charges par PlatformIO : `pre_utilitaires_platformio.py` (pre-script ; importe les
    `cible_*.py` voisins), `post_lto_parallele.py`, les 22 `cible_*.py` (cibles Custom, qui lancent
    `outils_pc/`), `ota-files-uploader.py`, `update_idf55_framework.py` (appele par le pre-script),
    `ino_stable.py` (banc `test_ino_stable.py`), `test_scons_cache.py` (banc des reglages SCons du pre-script),
    `cfg_holder.py` (decide si le pre-script incremente `CFG_HOLDER`, banc `test_cfg_holder.py` ; plan
    `tasks/plans/temps-compilation.md`),
    `interface_ecran.py` (`applique` : interface d'ecran `custom_interface_ecran` du cenv, fichiers des autres
    interfaces ajoutes en memoire a `custom_files_exclude`, valeur inconnue = arret ; `retire_exclus` : post-action de
    `littlefs.bin`, retire de l'image du buildfs les fichiers exclus a la racine, dossier de la carte compris, comme
    post_esp32 ; banc `test_interface_ecran.py`),
    `qrcode_build.py` (`regenere` : avant chaque `pio run` d'une carte qui a un reglage d'etiquette QR, recalcule son
    `qrcode.json` et le reecrit s'il a change ; persist illisible = avertissement, fichier garde, build continue ;
    banc `test_qrcode_build.py`),
    `verifie_lib_ignore.py` (garde du pre-script, AVANT le scan des dependances : arrete le build si le `lib_ignore`
    qu'un env personnel ajoute a son parent ignore une bibliotheque incluse sous une garde vraie ou incertaine ;
    ~11 s ; ligne « lib_ignore de <env> : » lue par la page build ; `--propose <env>` = liste ignorable de l'env ;
    lecture des gardes dans le module voisin `lecture_gardes.py` ; un defaut du controle ne bloque jamais le build ;
    banc `test_verifie_lib_ignore.py [--reel]` ; plan `tasks/plans/lib-ignore-envs.md`).
  - `berry/` — `verifie_berry.py` (syntaxe de data/, tache VS Code de surveillance ; avertissements de
    charte des logs par `charte_logs.py`, banc `test_verifie_berry_charte.py`),
    `solidifie_et_compile_berry.py` (module solidifiable en ~10 s, compile le .h ; REFUSE pendant un build : il vide
    `berry_custom/src/embedded`, dont le build a besoin, incident du 2026-11-01),
    `nomme_fonctions_berry.py` (fonctions anonymes -> nommees), `carte_modules_berry.py`
    (-> `outils_docs/CARTE_MODULES_BERRY.md`, sortie deterministe : ni date ni ordre de hachage), `genere_schema_persist.py`
    (-> `outils_docs/schemas/persist.schema.json`), `gen_tapp.py` (dossier -> `.tapp` sans compression ; refuse un nom du
    framework nu, `LOG_LEVEL_*` compris, car la carte compile l'extension avant `/autoexec.be` ; banc `test_gen_tapp.py` ;
    exemple `data/extensions/fsMqtt/`, banc `banc_tapp_fsmqtt.{py,be}` sous `berry.exe -g -s` ; doc `outils_docs/EXTENSIONS_TAPP.md`),
    `banc_repartition_fichiers.{py,be}` (`gestionFileFolder.be::listeEtRepartitLesFichiers` : un fichier deplace au demarrage
    n'est jamais perdu, `.tapp` vers `/.extensions/`), et les bancs
    `banc_test_modbus.{py,be}`, `banc_leds.{py,be}` (ruban AUTO/MANUEL, bouton, LED du dev-kit),
    `banc_veille_drivers.be` (veille des drivers inactifs sur LittleFS neuf, `bouchons_berry/veille/`),
    `banc_boot.{py,be}` (autoexec ENTIER du P4 sur faux firmware `bouchons_berry/boot/` : persist reel, `{}`,
    sans `serveur.wifi`, ES8311 absent, telemetrie sans COUNTER ; timers de reboot P5.1 ; B1, B2, B3, MAC et ES8311 corriges, plus aucun defaut `CONNU`),
    `banc_demarrage.{py,be}` (autoexec ENTIER des 6 cartes maintenues, instantane compare a `bouchons_berry/demarrage/<env>.txt` ;
    les autoexec ne gardent que la liste ordonnee de leurs modules, le deroule commun est dans `data/fs/demarrage.be`, P4.2),
    `test_discovery.be` avec leurs `bouchons_berry/` (`bouchons_berry/leds/` : bouchon de
    `ledsFonctions`, ajoute par le seul banc ModBus ; dans `bouchons_berry/`, il masquerait le vrai
    module a `banc_leds`).
  - `maintenance/` — `purge_cache_build.py` (vide les objets du cache `.cache` inutilises depuis N jours, defaut 30 ;
    `--dry-run` ; refus pendant un build ; aussi bouton de la page build ; banc `test_purge_cache_build.py`), `exclusions_defender.ps1` (exclusions
    Defender des dossiers de build, en administrateur, `-Verifier`),
    `synchronise_fork_tasmota.py` (synchro du fork : merge, jamais de force-push),
    `synchronise_upstream_tasmota.py` (variante rebase), `corrige_reglages_vscode.py` (pose et
    prouve les reglages VS Code du PermissionError), `verifie_references_docs.py` (renvois au code des
    documents durables : `fichier::fonction`, jamais `fichier:ligne` ; chemins et fonctions cites verifies ;
    banc `test_verifie_references_docs.py`). Page web de la synchro : `synchro_fork_web.py`
    (serveur, port 7500) + `synchro_fork_session.py` (script lance en processus enfant, questions),
    `synchro_fork_etat.py` (bandeau, diff, journal), `synchro_fork_page.py`, `synchro_fork_question.py`
    (importe par les deux scripts) ; banc `test_synchro_fork_web.py` (`--reel` : vrais scripts en
    --dry-run) ; cible `build/cible_synchro_fork.py`. Assistant pas a pas (2026-10-27) :
    `synchro_fork_assistant.py` (analyse en lecture seule hors fetch, prevision `git merge-tree`, liste
    d'etapes), `synchro_fork_fusion.py` (voie B : merge local, resolution, termine, abandonne, pousse ;
    marque `.git/synchro-fork-assistant`), `synchro_fork_page_assistant.py` (bloc, style et script de la
    page) ; bancs `test_synchro_fork_assistant.py`, `test_synchro_fork_fusion.py`,
    `test_synchro_fork_fusion_suite.py` (faux depot `faux_depot_synchro.py` : amont et origin nus + clone ;
    commandes git d'ecriture limitees par `liste_blanche_git_synchro.py`), sonde Chrome
    `test_synchro_fork_page_chrome.py`. Spec `docs/superpowers/specs/2026-10-27-assistant-synchro-fork-design.md`,
    plan `tasks/plans/assistant-synchro-fork.md`. **Exceptions a la regle du meme dossier** : `outils_pc/build_web.py` importe
    `maintenance/purge_cache_build.py` (bouton de purge de la page build), et
    `synchro_fork_web.py` importe `outils_pc/acces_web.py` et `outils_pc/build_serie.py` (detection
    d'un build en cours) par un `sys.path` explicite ; de meme `outils_pc/autoexec_gardes.py` importe
    `build/verifie_lib_ignore.py` (macros d'un env), et `outils_pc/tapp_sources.py` importe `berry/gen_tapp.py`.
  - `sauvegarde/` — `genere_sauvegarde_tasmota.py`, `restaure_sauvegarde_tasmota.py` et leur
    interface Tk `interface_sauvegarde_restauration_tasmota.py`.
  - `reseau/` — petits outils autonomes : `comm_udp_*.py`, `envoi_message_udp.py`,
    `simple-server.py`, `multi_server_explorer.py`, `image_base64.py`.
  - `outils_pc/` — les outils PC autour des cartes, qui s'importent entre eux (`ecoute_udp.py`
    importe le sniffeur MQTT ; le sniffeur ModBus, 7 modules voisins) : `pont_serie.py`
    (+ `pont_serie_web.py`) et ceux-ci :
  - `acces_web.py` (banc `test_acces_web.py`) — commun aux pages des outils (pont serie, testeur UDP,
    sniffeurs MQTT et ModBus, syslog, synchro du fork), decide le 2026-10-17 : au lancement, lien
    cliquable dans la console (Ctrl+clic) et navigateur ouvert (`--sans-navigateur` pour l'eviter) ;
    ecoute sur tout le reseau (`--local` = 127.0.0.1 seulement). **Depuis ce PC : sans jeton**,
    protection d'avant (en-tete `X-...` + origine 127.0.0.1/localhost). **Depuis un autre appareil :
    jeton obligatoire**, tire a chaque lancement, dans le lien « depuis un autre appareil du reseau »
    de la console ; pose en cookie HttpOnly SameSite=Strict (un nom par port) puis retire de l'URL.
    Le flux TCP brut du pont serie reste reserve a ce PC. Pare-feu Windows : autoriser Python sur
    les reseaux prives au premier lancement, sinon les autres appareils n'atteignent pas la page.
    Ecrit aussi la fiche de presence de l'outil (`%LOCALAPPDATA%\outils_tasmota\presence\`), lue par l'annuaire.
    Jeton COMMUN (2026-11-14) : l'annuaire passe son jeton aux outils qu'il lance (`OUTILS_TASMOTA_JETON`), le cookie d'un
    outil frere ouvre les autres ; un outil lance a la main garde son jeton propre. Un seul secret ouvre tous les outils
    (reseau prive seulement) ; la variable est retiree de l'environnement des la lecture ; l'annuaire emet le jeton et
    accepte le cookie d'un outil ; un outil survivant a un redemarrage accepte le nouveau jeton (`jeton_commun.json`).
    Barre commune (`acces_barre.py`, `/_barre.json`) : liste des outils en cours, signal de fin d'un outil occupe. Application : `habille()` ajoute a toute
    page manifeste, icones PNG (`acces_icone.py`), `theme-color`, barre « Annuaire » et service worker de repli quand l'outil
    est arrete (`acces_repli.py`, `/sw.js`, contexte securise seulement) ; routes publiques sans secret. Sondes
    `test_acces_repli_chrome.py` (installabilite jugee par Chrome, repli, barre) et `test_annuaire_lieux_chrome.py` (etat
    memorise) ; banc REEL `test_jeton_reel.py` (annuaire isole 17600 + vrai outil Build 17700, requetes depuis l'adresse reseau).
  - `sonde_hermetique.py` (banc `test_sonde_hermetique.py`, 2026-11-21) : aide des sondes Chrome dont la page est habillee par `acces_web.habille()` :
    `neutralise_barre()` coupe la barre commune (fiches de presence reelles, requete vers la vraie page Build :7700) et rend `restaure()`. Appelee par 7 sondes
    (`test_acces_repli_chrome.py`, `test_atelier_visuels_page_chrome.py`, `test_cartes_simulees_page_chrome.py`, `test_icones_catalogue_page_chrome.py`, `test_sondes_page_chrome.py`, `test_plan_maison_page_chrome.py`, `test_taches_planifiees_page_chrome.py`) ;
    les autres sondes d'une page habillee sont deja hermetiques par un `OUTILS_TASMOTA_DOSSIER` temporaire.
  - `test_rs485_pc.py` — test du bus ModBus depuis le PC par un convertisseur USB-RS485
    (Waveshare CH343) : ecoute du bus, envoi brut, lecture/commande de la carte 16 relais,
    recherche de son debit, emulation de la carte (pour tester le maitre P4 sans elle).
  - `sniffeur_modbus.py` (+ `sniffeur_modbus_web.py`, `sniffeur_modbus_aide.py`, `decodeur_modbus.py`,
    `build/cible_sniffeur_modbus.py`) — meme convertisseur, page http://127.0.0.1:7300 : trames du bus en direct,
    appariement requete/reponse (latence, sans reponse, exceptions par esclave), envoi et raccourcis carte
    16 relais, emulation de la carte. `decodeur_modbus.py` decode chaque trame selon la norme (champ par
    champ, clic sur la trame) puis selon le dialecte de l'esclave vise : carte 16 relais (Conn16channels)
    ou ESP32 (TasmotaSlaveModBus : registre = code GPIO Tasmota + idModBus - 1), d'apres le persist du
    maitre P4. Onglet Aide : regles de formation des trames, registres de l'installation, decodeur manuel
    (accepte une ligne `ModbusPushUDP <seq> <hexa>`). Modules : `sniffeur_modbus_http.py` (routes),
    `surveillance_modbus.py` (ecart commande/releve d'un relais, collisions -> alertes dans le fil),
    `emulation_modbus.py` (le PC repond a la place de la carte relais, de la cuve, du rideau ; valeurs
    editables dans la page ; temperature et analogiques peuvent onduler : ± ecart, periode en min), `debit_modbus.py` (trouve puis corrige, sur confirmation, le debit et
    l'adresse de la carte relais, comme `verifieConn16`), `ecoute_udp.py` (rejoint 224.3.0.1:4000 en
    ecoute seule : push `ModbusPushUDP` des esclaves decodes et juges comme `accepteSeq` du maitre ;
    s'abonne aussi a `tele/+/MODBUSPUSH`, ou le maitre recopie les push qu'il recoit si
    `ReglageModbus RelaisPushMQTT ON` : les esclaves sont derriere son point d'acces NAPT, leur
    multicast n'atteint jamais le PC sur le Wi-Fi maison).
    Echo local du convertisseur appris au 1er envoi (`--echo auto`) : un accuse 0x05/0x06 est la copie
    exacte de la requete, il ne doit pas etre jete. Port ouvert sans DTR/RTS (pas de reset d'un ESP32).
    Banc : `test_sniffeur_modbus.py` (code de sortie 0 = vert ; persist de test ; UDP sur un groupe et un
    port de test en TTL 0 - ne JAMAIS emettre de faux push vers 224.3.0.1:4000, le vrai maitre le traiterait). Cible PlatformIO « Sniffeur ModBus » dans Custom
    (port : `custom_sniffeur_modbus_port`, defaut auto = le seul CH343 present).
  - `sniffeur_i2c.py` (+ `sniffeur_i2c_web.py`, `sniffeur_i2c_http.py`, `sniffeur_i2c_aide.py`, `sniffeur_i2c_protocole.py`,
    `sniffeur_i2c_alertes.py`, `sniffeur_i2c_carte.py`, `decodeur_i2c.py`, `decodeur_i2c_puces.py`,
    `build/cible_sniffeur_i2c.py`) — page http://127.0.0.1:7350 (2026-10-31) : trafic d'un bus I2C par un ESP32-S3
    DEDIE (firmware autonome `outils_docs/firmware_sniffeur_i2c/`, PAS un env Tasmota ; SDA GPIO4, SCL GPIO5, GND,
    3,3 V seulement ; coeur 1 sans interruption, chien de garde des interruptions du coeur 1 coupe). Une ligne texte
    par transaction (protocole v=1, `sniffeur_i2c_protocole.py`, commun au futur Pico). Decodage jusqu'au registre
    (ADS1115, MCP23017, TCA9554, DS3231, MPU6050, ES8311) ; adresses partagees (0x20, 0x68) levees par la carte
    observee (puces actives de son persist), sinon « ambigu ». Envoi : par la carte, en HTTP ou en MQTT (`cmnd/<topic>/Br`,
    reponse `stat/<topic>/RESULT` : esclaves derriere le NAPT) (`Br (wire1.detect(a) ? wire1 :
    wire2).read/write`, pas `tasmota.wire_scan` qui rend nil pour une puce prise par un pilote C ; apercu avant envoi,
    ecriture confirmee, rapprochement de la trame) ou par le sniffeur maitre (composant isole, refus si le bus a vecu
    dans les 2 s). Journal `%LOCALAPPDATA%\outils_tasmota\sniffeur_i2c\` (30 jours). Bancs : `test_sniffeur_i2c.py`,
    sonde `test_sniffeur_i2c_page_chrome.py`, machine du firmware `firmware_sniffeur_i2c/banc/lance_banc.py` (MSVC ou
    g++). Spec `docs/superpowers/specs/2026-10-31-sniffeur-i2c-design.md` ; plan `tasks/plans/sniffeur-i2c.md`.
  - `sniffeur_mqtt.py` (+ `sniffeur_mqtt_web.py`, `sniffeur_mqtt_panneaux.py`, `sniffeur_mqtt_config.py`,
    `client_mqtt.py`, `build/cible_sniffeur_mqtt.py`) — sniffeur / publieur MQTT sur http://127.0.0.1:7100 :
    plusieurs brokers parametrables (TLS possible) et selectionnables, abonnements gerables un par
    un et memorises par broker, filtre d'affichage + favoris, differences avec le message precedent
    du meme topic, export .txt/.json, publication (retenu ou non). Panneaux : audit discovery,
    connexions LWT, logs par carte (`stat/<topic>/LOGGING`, sans occuper les ports serie), commande
    Tasmota avec sa reponse, arborescence des topics. Broker par defaut lu dans
    `user_config_override.h` ; les autres (mots de passe compris) dans
    `%APPDATA%\sniffeur_mqtt\config.json`, HORS depot. Cible PlatformIO « Sniffeur MQTT » dans Custom.
  - `syslog_tasmota.py` (+ `syslog_tasmota_web.py`, `build/cible_syslog_tasmota.py`) — serveur syslog :
    ecoute UDP 514, page http://127.0.0.1:7200 (filtre module / severite / texte), journal
    `%TEMP%/syslog_tasmota.log`. Cible PlatformIO « Serveur syslog » dans Custom. Les modules
    envoient a `SYS_LOG_HOST` (`user_config_override.h`) = **192.168.0.3, ce PC** (le NAS
    192.168.0.2 est eteint) : IP figee par une reservation DHCP sur la box (MAC Wi-Fi
    DC-85-DE-D9-CA-1D, confirmee le 2026-10-24 ; Windows reste en DHCP, c'est normal).
  - `testeur_udp.py` (+ `testeur_udp_carte.py`, `testeur_udp_essais.py`, `testeur_udp_http.py`,
    `testeur_udp_web.py`, `testeur_udp_aide.py`, `testeur_udp_grille.py`, `testeur_udp_grille_web.py`,
    `build/cible_testeur_udp.py`) — page
    http://127.0.0.1:7400 pour tester l'UDP maitre <-> esclave : ouvre les 2 ports serie (maitre et
    esclave, reglables dans la page), envoie texte libre / trames `ModbusUDP` (E1) / push / `ImAlive`
    en unicast ou multicast et juge chaque essai (RECU, EMIS NON RECU, NON EMIS...). Bascule le mode
    de l'esclave par `ReglageGlobal ModeConnexion RangeExtender|WifiClassique <ssid> <mdp>` (Wi-Fi lu
    dans le persist du maitre du depot ; l'esclave memorise ses reseaux d'origine et redemarre).
    Pose les logs `udp`/`modbus` le temps des essais puis les restaure. Chaque carte se branche soit sur
    son port COM, soit par le pont serie (`pont:7000`, TCP brut ; avertit si le pont n'est pas demarre ;
    redemande au pont un port perdu, jamais apres « Arreter »). Onglet « Grille ModBus » : les 7 tests de
    la grille de `AUDIT_MODBUS_2026-09-29.md` §6 pour UN esclave (ID/Power/registre lus dans le persist du
    maitre, defaut cuve), juges sur les logs des deux cartes, consignes a valider dans la page ; pose
    aussi `slaveModbus`/`conn16channels` en debug sur le maitre. Onglet Aide. Cible PlatformIO
    « Testeur UDP maitre/esclave » dans Custom, et tache VS Code (Ctrl+Maj+P > Run Task). Banc :
    `test_testeur_udp.py` (cartes simulees par `testeur_udp_sim.py` ; groupe « pont » dans
    `test_testeur_udp_pont.py`, sur le vrai `pont_serie.py` en loop:// ; groupe « muette » dans
    `test_testeur_udp_muette.py` : carte qui ne repond plus sur son port ; groupe « grille » dans
    `test_testeur_udp_grille.py`, avec pannes simulees ; code de sortie 0 = vert).
  - `annuaire_outils.py` (+ `annuaire_registre.py`, `annuaire_presence.py`, `annuaire_lanceur.py`,
    `annuaire_page.py`) — annuaire des outils PC, page http://127.0.0.1:7600 : liste les outils (fiches de
    presence sous `%LOCALAPPDATA%\outils_tasmota\`, consoles dans `consoles\<id>.log`), les lance et les arrete.
    Demarre seul avec VS Code (tache « Outil : annuaire des outils », `runOn: folderOpen`) et ouvre sa page dans
    le navigateur a chaque ouverture de VS Code (decide le 2026-10-17 ; deja demarre -> ouvre seulement la page).
    Aussi cible Custom « Annuaire des outils (page web) » (`build/cible_annuaire.py`, `pio run` : jamais pendant
    un build) : si l'annuaire tourne deja, ouvre seulement sa page ; sinon le demarre (il s'arrete alors avec la cible).
    Les outils lances depuis l'annuaire s'arretent avec lui (job object Windows), SAUF la synchro du fork
    (hors job, console cachee propre, survit a la fermeture de VS Code ; arret refuse pendant un merge, rebase
    ou push ; synchro muette : refus si MERGE_HEAD ou rebase en cours dans `.git`). Tuile « liee a
    l'annuaire » si Windows a refuse de detacher la synchro. Client de ce PC : Host 127.0.0.1/localhost/[::1]
    exige (DNS rebinding). Autre appareil : lien a jeton de la console / de la page sur le PC. Bancs :
    `test_annuaire.py`, `test_annuaire_lanceur.py`, `test_annuaire_securite.py`.
    Spec : `docs/superpowers/specs/2026-10-17-annuaire-outils-design.md`.
  - `build_web.py` (+ `build_page.py`, `build_serie.py`, `build_envs.py`, `build_progression.py`, `build_ota_fs.py` (FS ; firmware : `build_ota_firmware.py` ; maitre :
    `build_ota_maitre.py` ; transport HTTP : `build_ota_http.py`, decoupe le 2026-10-29 ; FS par MQTT : `build_ota_mqtt.py`,
    A16), `build_fichiers.py`, `build_page_fichiers.py`, `build_memoire.py` (occupation memoire de l'env, relue du dernier
    build, `GET /memoire`, `POST /memoire/analyser`), `build_page_memoire.py` (onglet « Mémoire et partitions », modele B ;
    sonde `test_build_page_memoire_chrome.py`), `build_partitions.py` (table de partitions de l'env : validation,
    `partitions/env_<env>.csv`, OTA bloquee jusqu'au prochain effacement ; `POST /partitions/diff|ecrire` ; plan
    `tasks/plans/temps-compilation.md` A7 a A10), `build_defaut.py` (bloc `default_envs` de `platformio_override.ini`, ce que
    compile un `pio run` sans -e : `GET /defaut`, `POST /defaut/diff|ecrire` ; banc `test_build_defaut.py`), `build_page_defaut.py`
    (onglet « Env par défaut (Platformio override) », modele B + futur fichier dessous ; sonde `test_build_page_defaut_chrome.py` ; maquettes
    `outils_docs/default_envs/` ; plan `tasks/plans/default-envs-page.md` ; case de creation d'env : `fichiers_berry_creation.py::ajoute_default_envs`),
    `build_solidification.py`, `build_drvset.py` (copie `/.drvset003` par le reseau avant un upload ou erase_upload serie, la renvoie apres, `Restart 99` puis relecture du calibrage ; copie dans `drvset/` du dossier de donnees de la page ; banc `test_build_drvset.py`), `build_page_aide.py` (onglet « Aide », texte fixe : fichiers `.drvset`), `build_page_couleurs.py` (codes ANSI du journal -> couleurs du terminal de VS Code dans le panneau « Sortie »), `build_sauvegarde.py` + `build_page_sauvegarde.py` + `build_sauvegarde_mqtt.py` (liaison MQTT : FileDownload/FileUpload ; banc `test_build_sauvegarde_mqtt.py`, avec la purge (case de l'onglet, `reglages.json`), les étapes de restauration et les marques « reposé au démarrage ») (onglet « Sauvegarde configuration », modele B : `/dl` de chaque carte dans `outils_docs/sauvegardes_cartes/<env>/`, ignore par git ; parametres, copie modifiee, comparaison, restauration ; « avant flash » prise par la serie ; banc `test_build_sauvegarde.py`, sonde `test_build_page_sauvegarde_chrome.py` ; plan `tasks/plans/sauvegarde-config-cartes.md`), `decode_config.py` (+ `decode_config_groupes.py` : decode-config 16.0.0.0 dans `%LOCALAPPDATA%\outils_tasmota\decode_config\`, hors depot et hors Python de PlatformIO ; textes ecrits par l'outil, decode-config tronquant la reserve d'un ESP32), et pour les bancs `build_faux_pio.py`, `build_ota_carte_simulee.py`) — page « Build et televersement »
    http://127.0.0.1:7700 (tuile de l'annuaire, groupe Déploiement, hors job : l'annuaire refuse de l'arreter pendant
    un lancement ; tache VS Code « Outil : build et televersement » ; cible Custom « Build et televersement (page web) »
    (`build/cible_build_web.py`, banc `build/test_cible_build_web.py`) qui DEMARRE LA PAGE DETACHEE puis rend la
    main : une cible est un `pio run`, vivante elle serait vue comme un build en cours ; `pio run` : jamais
    pendant un build). On coche des envs (Mes cartes / Mes bases / amont) et des actions (compiler, televerser le firmware
    OU effacer puis televerser, construire le FS, televerser le FS), COM ou OTA par ligne ; les `pio run` s'enchainent
    un a un (jamais deux ensemble ; attente si un build apparait ailleurs ; refus si port tenu ou absent), avec
    etape, % et durees en direct, et la **sortie de pio en direct** par env (panneau « Sortie » : journal de l'env
    lu par increments par `GET /sortie`, barres d'esptool contenues ; referme quand l'env reussit sauf geste de
    l'utilisateur, pas rouvert au rechargement pour un env reussi). **Pause « rebranchez la carte »** (choix 11
    revise) : deux envois sur le meme port COM sont acceptes ; avant l'envoi d'un env dont le port a deja servi dans
    la serie (compilation faite avant, en un `pio run` a part), bandeau « Branchez la carte X sur COMn » +
    Continuer / Passer cet env (`POST /continuer`), port reverifie a la reprise. Journaux tries par date de
    modification (pas l'heure du nom : heure d'hiver), purges au demarrage au-dela de 30 jours. « Effacer puis televerser » =
    `-t erase_upload --upload-port COMn`, COM seulement, exclusive avec l'upload, confirmation avant (persist et
    reglages de la carte remplaces par ceux du depot), etape « Effacement de la flash ». `data_dir` de `platformio_override.ini`
    pose sur le dossier de l'env AVANT chaque `pio run` d'une carte (`build_envs.py::ecrit_data_dir`) : pio lit ce fichier
    avant le pre-script, qui pose aussi `PROJECT_DATA_DIR` pour le lancement en cours (banc `build/test_data_dir.py`) ; sans
    cela, un buildfs seul prenait le dossier de l'env precedent (P4 avec le FS de la cuve, 2026-10-26). Port COM lu dans `platformio_tasmota_cenv.ini` et REECRIT dans la section de l'env
    (`.bak` ; **change l'empreinte -> le build suivant repart de zero**) ; IP OTA lue dans `WIFI_IP_ADDRESS`
    (0.0.0.0 -> esclave du range extender du maitre : `<ipMaitre>:<8080 + id - 1>` tire du persist,
    `build_envs.py::adresse_par_maitre` ; sinon saisie pour le lancement). Vers une adresse `IP:port`, AVANT tout envoi :
    `RoutageRangeExtender` sur le maitre puis `Status 5` compare au nom d'hote du persist (`build_ota_maitre.py::joint_par_maitre`),
    refus sinon ; maitre en `Sleep 0` le temps de l'envoi (`build_ota_maitre.py::coupe_sleep`, a `Sleep 50` son relais
    coupe l'envoi) ; carte deja en safeboot reconnue a sa page d'accueil (`build_ota_http.py::_page_safeboot`), envoi relance. OTA du firmware envoyee par la page (`/up`, `/u2`, safeboot `/u4`, preuve
    par `Status 2`) : aucun script de `build/` modifie. OTA du FS : fichiers extraits de `littlefs.bin` (image du `buildfs`,
    PAS `littlefs_data`, perime) par `/ufsu` apres controle d'identite (`build_ota_fs.py::verifie_identite` : nom d'hote et topic du persist de
    l'image = ceux du persist de l'env au depot, sinon rien n'est envoye), persist de
    la carte sauvegarde avant dans `%LOCALAPPDATA%\outils_tasmota\build\persist\`, relu, Berry recharge, `Restart 1`.
    Un upload (ou erase_upload) serie du firmware flashe AUSSI le FS (persist compris) a chaque fois pour les envs a
    `custom_files_upload` (post_esp32 reconstruit `littlefs.bin` a chaque edition des liens) : la page l'annonce, grise
    « Construire / Televerser le FS » si tous les envs coches sont dans ce cas, et sinon le serveur ne lance ni buildfs ni
    uploadfs pour eux (statut de l'envoi, `build_serie.py::Serie._plan`). Journaux de chaque `pio run` dans
    `%LOCALAPPDATA%\outils_tasmota\build\journaux\`. Chaque lancement reecrit `platformio_override.ini` et
    `user_config_override.h` (a commiter). Bancs : `test_build_*.py` (+ sonde `test_build_page_chrome.py`).
    Onglet « Fichiers » (A15, en cours, spec choix 24) : `GET /fichiers?env=` (`build_fichiers.py::liste` : fichiers de
    l'image du dernier buildfs, jeton = date de l'image) puis action `fichiers` de la serie (une carte OTA, fichiers
    choisis, refus si l'image a change depuis la liste ; `build_ota_fs.py::envoie_fs_ota` avec `fichiers=`). Page :
    `build_page_fichiers.py` (CSS/HTML/JS de l'onglet, maquette E, inseres dans `build_page.PAGE` ; avancement en % et
    journal des etapes dans l'onglet) ; sonde `test_build_page_fichiers_chrome.py` (Python de PlatformIO, aucun envoi).
    Transport MQTT (A16, spec choix 25 a 28) : `build_ota_mqtt.py::envoie_fs_mqtt` -> module carte `data/fs/fsMqtt.be`
    (topics `fsmqtt/<topic du persist>/ordre|morceau|etat|lu`, fichier temporaire + MD5, effacement = formatage
    `path.format`, bloquant : watchdog de 5 s ; SOLIDIFIE dans `berry_commun.socle`, charge par l'autoexec du P4 et de la cuve). Bancs `berry/banc_fsmqtt.py` (mutants),
    `test_build_ota_mqtt.py` (carte MQTT simulee).
    Arrivee depuis l'atelier des graphiques (2026-11-05, plan `tasks/plans/atelier-destinations.md` A7) : `?env=&depuis=atelier&fichiers=&redemarrer=`,
    code dans le module neuf `build_page_atelier.py` (JS seul, ajoute a la fin de celui de `build_page_fichiers.py`) : bandeau, `buildfs` lance seul, fichiers
    coches a la fin, rien d'envoye ; sonde `test_build_page_fichiers_chrome.py::sonde_atelier`.
    Mode d'emploi : `outils_docs/README.md` § « Build et televersement (page web) » (onglet : « Onglet « Fichiers » :
    envoyer quelques fichiers du FS »). Spec :
    `docs/superpowers/specs/2026-10-24-page-build-televersement-design.md` ; plan :
    `tasks/plans/page-build-televersement.md`.
  - Reparation automatique des pannes de la page Build (2026-11-15, plan `tasks/plans/build-reparations.md`, spec `docs/superpowers/specs/2026-11-14-build-reparations-design.md`) :
    `build_reparations.py` (catalogue, `cherche`, `filtre_secrets`, `Reparateur` branche dans `build_serie.py::Serie._execute_env`), `build_reparations_verrou.py`
    (Restart Manager : quel processus tient un fichier, liste blanche, fermeture), `build_reparations_ia.py` (diagnostic par `claude -p` en lecture seule, application),
    `build_web_reparations.py` (routes `/reparations*`, `/reparation`), `build_page_reparations.py` (bandeaux, choix, panneau, case de l'IA) ; catalogue de base
    `outils_docs/schemas/reparations_build.json`. Bancs `test_build_reparations.py`, `_verrou.py`, `_ia.py`, groupes de `test_build_serie.py` et `test_build_web.py`, sonde
    `test_build_page_reparations_chrome.py`. Mode d'emploi : `outils_docs/README.md` § « Réparation automatique des pannes ». Meme page, plan `tasks/plans/build-fin-partitions.md` :
    `build_page_fin_memoire.py` (pastille « Flash 87 % · RAM 32 % » dans la ligne de l'env a la fin d'une compilation, fenetre de detail des partitions ; lit `GET /memoire?env=`),
    sonde `test_build_page_fin_memoire_chrome.py`.
  - `fichiers_berry_web.py` (+ `fichiers_berry_page.py`, `fichiers_berry_ini.py`, `fichiers_berry_etat.py`,
    `fichiers_berry_ecriture.py`, `fichiers_berry_creation.py`, `fichiers_berry_suppression.py`, `fichiers_berry_renommage.py`,
    `fichiers_berry_sauvegarde.py`, `fichiers_berry_page_envs.py`, `fichiers_berry_coprocesseur.py`) — page « Fichiers Berry par env » http://127.0.0.1:7800
    (tuile de l'annuaire, groupe Configuration des cartes, arret libre : rien n'est ecrit avant « Enregistrer » ; tache VS Code
    « Outil : fichiers Berry par env » ; cible Custom « Fichiers Berry par env (page web) », `build/cible_fichiers_berry.py`,
    banc `build/test_cible_fichiers_berry.py`, page demarree detachee comme celle du build ; lien « fichiers » sur chaque
    env personnel de la page build, `?env=` dans les deux sens). Par env : chaque `.be` (data/fs, dossier de la carte,
    modules amont `tasmota/berry/modules`, recenses a chaque chargement) sur le FS, exclu ou solidifie, ecrit dans
    `custom_files_upload` / `custom_files_exclude` / `custom_berry_solidify` du cenv : resolution des `${...}` avec
    provenance (`fichiers_berry_ini.py`), liste partagee -> envs touches nommes puis « Modifier (N envs) » ou « Annuler »,
    option heritee -> `${env:<base>.opt}` + ligne, commentaires jamais touches (ceux qui citent le fichier signales),
    raison facultative `; raison (date)`, diff puis ecriture avec empreinte, refus pendant un build. Creation
    d'un env a partir d'une carte modele (`fichiers_berry_creation.py`) : section du cenv, dossier `data/<lieu>/<puce>-<nom>`
    (identite remplacee dans le `_persist.json`, texte garde octet pour octet), section `#elif` de `user_config_override.h` ;
    refus si env/dossier/define/IP/topic/client deja pris ; secrets masques dans le diff. Renommage d'un env
    (`fichiers_berry_renommage.py`, identite reproposee, dossier DEPLACE) et suppression (`fichiers_berry_suppression.py` :
    section du cenv et du `.h` retirees, `default_envs` de `platformio_override.ini`, dossier renomme en `…-sauvegarde`) ;
    panneaux dans `fichiers_berry_page_envs.py`. Toute ecriture est ATOMIQUE (`fichiers_berry_sauvegarde.Transaction` :
    annulation sur exception, copie horodatee dans `%LOCALAPPDATA%\outils_tasmota\fichiers_berry\sauvegardes\`, 30 jours ;
    plus de `.bak` ; POST un par un ; marque `en_cours.json` restee = operation interrompue, bandeau dans la page).
    Identite deja portee par une autre carte = avertissement (carte remplacee), pas un refus. Copies temporaires d'un build (`.be` de la carte identique a `data/fs`) ni proposees ni recopiees ;
    exception inattendue -> 500 avec son message. Bancs `test_fichiers_berry_*.py`
    (copies temporaires, jamais le vrai depot ; `_ecriture` relu par `ProjectConfig`) + sonde Chrome
    `test_fichiers_berry_page_chrome.py`. Mode d'emploi : `outils_docs/README.md` § « Fichiers Berry par env (page web) ».
    Spec : `docs/superpowers/specs/2026-10-25-page-fichiers-berry-design.md` (§9 suppression, §10 renommage) ; plans :
    `tasks/plans/fichiers-berry-env.md`, `tasks/plans/fichiers-berry-suppression.md`.
  - `assistant_persist_web.py` (+ `assistant_persist_page.py`, `assistant_persist_page_js.py`, `assistant_persist_modele.py`,
    `assistant_persist_parc.py`, `assistant_persist_generation.py`, `assistant_persist_elements.py`,
    `assistant_persist_creation.py`, `assistant_persist_texte.py`, `assistant_persist_delta.py`,
    `assistant_persist_modification.py`, `assistant_persist_page_js_env.py`) — page « Assistant persist » http://127.0.0.1:7900 (tuile de l'annuaire, groupe
    Maintenance, arret libre : rien n'est ecrit avant « Creer l'env » ; tache VS Code « Outil : assistant persist » ;
    cible Custom « Assistant persist (page web) », `build/cible_assistant_persist.py`, banc
    `build/test_cible_assistant_persist.py`). Pose des questions et en tire le `_persist.json` d'une NOUVELLE carte, son
    autoexec, la section du cenv et la section `#elif` du `.h`, d'apres le modele `outils_docs/schemas/modele_persist.json`
    (se met a jour du parc : fusion des cles nouvelles a l'ouverture, bouton « Mettre a jour le modele » avec diff,
    sauvegardes horodatees). Editeur des entrees/sorties du bloc metier (broches de `data/fs/configGlobal.be`, refus des
    doublons et des broches ModBus/I2C/LEDs). Mots de passe JAMAIS envoyes a la page : recopies cote serveur, `***` dans
    l'apercu et le diff. Creation en une transaction, moteur de `fichiers_berry_creation.py` reutilise ; refusee pendant
    un build. Limites : seuls activation, nom, broche et type s'editent ; bloc metier principal seulement. Modification
    d'un env existant par ecart (A -> B, le reste intact) et suppression verifiee : faites (spec §10,
    `tasks/plans/assistant-persist-modification.md`). Bancs `test_assistant_persist_*.py` (dont `_texte`, `_delta`,
    `_modification`, ce dernier lent) + sonde Chrome
    `test_assistant_persist_page_chrome.py`. Mode d'emploi : `outils_docs/README.md` § « Assistant persist (page web) ».
    Spec : `docs/superpowers/specs/2026-10-27-assistant-persist-design.md` ; plan : `tasks/plans/assistant-persist.md` ;
    analyse en attente de decision : `outils_docs/ANALYSE_CLES_MAC_TELEPERIOD_2026-10-27.md`.
    Onglet « autoexec.bat » (2026-11-05, modele C de `outils_docs/autoexec_bat/`) : `assistant_persist_autoexec.py` (routes),
    `autoexec_fichier.py` (lecture masquee, diff, ecriture), `autoexec_analyse.py` (avertissements), `autoexec_commandes.py`
    (fige `outils_docs/schemas/commandes_tasmota.json` ; `--verifier`, `--generer`), `autoexec_banque.py`
    (`outils_docs/schemas/banque_autoexec.json`), `autoexec_envoi.py` (HTTP `/ufsu` ou MQTT par `fsMqtt` de la carte,
    `build_ota_mqtt.py` ; nom d'hote de la carte = persist du depot, sinon refus ; verrou par carte), `autoexec_gardes.py`
    (alerte orange « absente » : commande dont TOUTES les gardes `USE_*` sont fausses pour l'env, cle `gardes` de
    `commandes_tasmota.json` ; calcul dans un processus fils, cache par env), `autoexec_berry.py` (même alerte pour une commande
    Berry dont l'`autoexec.be` de la carte ne charge pas le module ; banque marquée par `GET /autoexec/marques`), page `assistant_persist_page_autoexec.py`, `_autoexec_js.py`, `_autoexec_lignes_js.py` (commande deja presente,
    suppression de ligne). Mode d'emploi : `outils_docs/README.md` § « Onglet « autoexec.bat » » ; spec
    `docs/superpowers/specs/2026-11-03-onglet-autoexec-bat-design.md` ; plans `tasks/plans/autoexec-bat.md`, `tasks/plans/autoexec-mqtt-tapp.md`.
  - `tapp_web.py` (+ `tapp_page.py`, `tapp_sources.py`, `tapp_envoi.py`, `build/cible_tapp.py`) — page « Fabrique d'extensions »
    http://127.0.0.1:7980 (2026-11-07 ; tuile de l'annuaire, groupe Ateliers, arret libre ; tache VS Code ; cible Custom detachee,
    `NOM_CIBLE` fabrique_tapp). Sources dans `data/extensions/<nom>/` (gabarits A et B de `outils_docs/EXTENSIONS_TAPP.md`), manifeste,
    controle et fabrication par `berry/gen_tapp.py`, `.tapp` a cote du dossier (ignore par git) ; envoi HTTP ou MQTT vers
    `/.extensions/<nom>.tapp` par `autoexec_envoi.py` (identite, refus pendant un build, geste explicite ; en MQTT, lecture de la
    carte au seul clic « Lire la carte ») ; boutique locale de `/ext` (`GET /extensions/...`, publique, `tapp_sources.py::depot`) pour une carte dont
    l'`OtaUrl` pointe sur ce PC. Bancs `test_tapp_web.py`, `test_tapp_envoi.py`, sonde `test_tapp_page_chrome.py`,
    `build/test_cible_tapp.py`. Mode d'emploi : `outils_docs/README.md` § « Fabrique d'extensions (page web) ». Non essaye sur carte (A10).
  - `atelier_graphiques_web.py` (+ `atelier_graphiques_page.py`, `_page_js.py`, `_page_series.py`, `_description.py`, `_series.py`,
    `_conseil.py`, `_ecriture.py`, `build/cible_atelier_graphiques.py`) — page « Atelier des graphiques » http://127.0.0.1:7950 (2026-11-04, palier 1 ;
    tuile de l'annuaire, groupe Ateliers, arret libre : rien n'est ecrit avant « Ecrire dans le depot » ; tache VS Code « Outil : atelier des
    graphiques » ; cible Custom detachee, `NOM_CIBLE` atelier_graphiques ; modele B de `outils_docs/atelier_graphiques/`). Prepare les pages de graphiques d'une carte
    S3/P4 (series de l'historique, du JSON SENSOR ou calculees ; conseil de style ; apercu par le VRAI moteur de la carte, valeurs de la carte en ligne sinon
    persist du depot et valeurs simulees). Ecrit `data/<lieu>/<carte>/pages_graphiques.json` (valide par `_description.py::valide`), la ligne
    `demarrage.charge(["pagesGraphiques"])` de l'autoexec et le cenv : deux listes de `[berry_commun]`, `pages_graphiques` (gabarit, `.be` du moteur ; exclue de tout env sans page)
    et `pages_graphiques_moteur` (`pagesGraphiquesValidation.be`, `pages_graphiques.js`, `pages_graphiques_formule.js`, `graphiques_moteur.js` ; exclue des envs sans historique ET sans page : suit
    l'historique ou une page dediee) ;
    diff puis ecriture atomique, refusee pendant un build ou sur empreinte perimee ; `--exclusions` = application au vrai depot. Moteur cote carte :
    `data/fs/pagesGraphiques.be` + `pagesGraphiquesValidation.be` (route `/pages?p=<id>`, `?f=valeurs`, `?f=sources`, description `/json/pages_graphiques.json`),
    `data/sd/{html,css,js}/pages_graphiques.*` + `pages_graphiques_formule.js`. Premiere page : la cuve (`/pages?p=tableau`, courbe « Hauteur d'eau »).
    `ReglageCuve simulation <ON|OFF|minutes>` (`cuveFonctions.be::reglageCuve`) : hauteur d'eau simulee sans sonde, RAM seulement. Bancs
    `test_atelier_graphiques_*.py`, `test_pages_graphiques.mjs`, `test_pages_graphiques_chrome.py`, `berry/banc_pages_graphiques.py` (cas partages
    avec le validateur Python), `build/test_cible_atelier_graphiques.py`. Mode d'emploi : `outils_docs/README.md` ; spec
    `docs/superpowers/specs/2026-11-03-atelier-graphiques-design.md` ; plan `tasks/plans/atelier-graphiques.md`.
    **Destination « Graphiques » et bouton « Televerser »** (2026-11-05, spec `docs/superpowers/specs/2026-11-04-atelier-destinations-televersement-design.md`,
    plan `tasks/plans/atelier-destinations.md`) : menu « Page » (pages dediees, « Graphiques (/graphiques) » si l'historique est actif, « Autre… »). Modules neufs :
    `atelier_graphiques_graphiques.py` (ecriture de la cle `graphiques` de `graphiques.json`, graphiques `"moteur": "pages"` ; composition de la carte comparee au depot,
    choix `base=carte|depot`, jamais d'ecrasement implicite), `atelier_graphiques_televerse.py` (liste des fichiers a envoyer, URL de la page Build),
    `atelier_graphiques_page_destination.py` et `atelier_graphiques_page_televerse.py` (JS de la page). Bancs `test_atelier_graphiques_graphiques.py`
    et `test_atelier_graphiques_televerse.py`. Cote carte : `data/sd/js/graphiques_moteur.js` (trace d'un graphique `moteur` par `PagesGraphiques.optionDe`) ;
    `graphiquesFonctions.be::valideComposition` accepte `"moteur": "pages"` (valide par `pagesGraphiquesValidation.be`). Mode d'emploi : `outils_docs/README.md`.
  - `atelier_ecrans_web.py` (+ `atelier_ecrans_page.py`, `_page_js.py`, `_page_canevas.py`, `_page_remarques.py`, `_page_ecriture.py`,
    `_page_polices.py`, `_catalogue.py`, `_description.py`, `_haspmota.py`, `_lvgl.py`, `_lvgl_moteur.py`, `_ecriture.py`, `_ecran.py`,
    `_remarques.py`, `_polices.py`, `_capture.py`, `build/cible_atelier_ecrans.py`) — page « Atelier des ecrans » http://127.0.0.1:7960
    (2026-11-12, palier 1 ; tuile de l'annuaire, groupe Ateliers, arret libre ; tache VS Code ; cible Custom detachee, `NOM_CIBLE`
    atelier_ecrans). Ecran tactile d'une carte dessine d'apres une description neutre `outils_docs/atelier_ecrans/cartes/<env>/ecran.json`
    (hors flash, avec `remarques.json`), catalogue `outils_docs/schemas/catalogue_ecran.json` ; deux interfaces generees dans le dossier
    de la carte, `pages.jsonl` (HASPmota) et `ecranLvgl.be` (LVGL pur), choisies par `custom_interface_ecran` (`build/interface_ecran.py`).
    Ecriture atomique, refusee pendant un build ou sur empreinte perimee ; changement d'ecran par proposition mise a l'echelle
    (`display.ini` repris d'un env qui porte l'ecran, conflit de broches = refus) ; remarques epinglees et traitees par `claude -p` en
    LECTURE SEULE (outils de lecture, hooks coupes, jamais bypassPermissions ; depuis ce PC seulement) ; import d'une police `.ttf`
    (licence confirmee, Latin-1 complet, licence dans `outils_docs/atelier_ecrans/polices/`) ; images `.png/.jpg/.bmp` rangees sous
    `/sd/images/PNG|JPG|BMP/` par `gestionFileFolder.be::listeEtRepartitLesFichiers`. Capture `lv.screenshot()` pas encore essayee sur carte.
    Dossiers `outils_docs/atelier_ecrans/display/`, `polices/` et `images/<env>/` : CREES A L'USAGE (premiere bibliotheque `.ini`, premiere police, premier PNG), absents d'un depot neuf, c'est normal.
    Onglet « display.ini » (A12, 2026-11-13) : `_display.py` (analyse comme `uDisplay.cpp::uDisplay::uDisplay`, insertion par rang ;
    reference `outils_docs/schemas/display_ini_parametres.json`, banc de concordance rouge si une synchro ajoute une section),
    `_display_fichiers.py` (cartes et `tasmota/displaydesc` en lecture ; bibliotheque `outils_docs/atelier_ecrans/display/<nom>.ini`
    + `<nom>.notes.md`), `_page_display.py` ; « Appliquer a la carte » = changement d'ecran. Essai sur carte a faire.
    Import d'un pages.jsonl ecrit a la main (A13) : `_import.py` (lecture comme HASPmota ; lignes non reprises = objets `brut`
    reecrits tels quels, absents de `ecranLvgl.be`), `_page_import.py`, route `POST /importer`.
    Objets du palier 2 (A14 : img PNG sous `/sd/images/PNG/`, dropdown, switch, roller, qrcode) : `_page_palier2.py`, routes
    `GET /images`, `/image`, `/lib/qr.js`. Barre de navigation construite d'apres les pages (A17) : cle `navigation` de la
    description, page `"menu": false` hors barre, boutons ids 201 a 254 deroules par `_navigation.py::deroule` pour le
    validateur et les deux generateurs ; panneau de la page 0 : `_page_navigation.py`. Sondes Chrome du palier 2 et de la
    barre : `test_atelier_ecrans_page_chrome_palier2.py`, appelees par la sonde principale.
    Page « Systeme » des cartes a ecran (A19, en cours) : `atelier_ecrans_systeme.py` (page `"modele": "systeme"` deroulee comme la
    barre de navigation, d'apres `CHAMPS` ; refus si l'ecran est trop petit) ; `data/fs/ecranSysteme.be` (table `CHAMPS` = seule reference des
    donnees et des ids d'objets) + `controleEcranSysteme.be` (garde `modules.ecranSysteme`), 5 dernieres erreurs gardees par
    `logFonctions.be::dernieresErreurs` ; liste `berry_commun.ecran_systeme` du cenv, exclue de tous les envs tant qu'aucun
    autoexec ne la charge (chargee par celui de l'ecran des debits) ; bancs `berry/banc_ecran_systeme.py`, `berry/banc_page_systeme.py` (vrai
    `ecranLvgl.be` genere : chaque ecriture trouve son objet, un appui = un appel), `outils_pc/test_atelier_ecrans_systeme.py`.
    Panneau « Icones » (A15, 2026-11-13) : `atelier_ecrans_icones.py` (routes `GET /icones`, `/lib/mdi.ttf`), `atelier_ecrans_page_icones.py` (grille,
    recherche, glyphes dessines par la police MDI locale), catalogue `outils_docs/schemas/icones_firmware.json` genere d'apres `gen.sh` par
    `outils_pc/genere_icones_firmware.py` (Python systeme, fontTools ; `--verifier` apres une synchro du fork), sonde `test_atelier_ecrans_page_chrome_icones.py`.
    Import d'un PNG (A15) : `atelier_ecrans_images.py` (routes `POST /images/analyse|importer`, PNG dans le dossier de la carte, licence dans
    `outils_docs/atelier_ecrans/images/<env>/`), banc `test_atelier_ecrans_images.py`.
    Bancs `test_atelier_ecrans_*.py`, sonde `test_atelier_ecrans_page_chrome.py`, `build/test_cible_atelier_ecrans.py`. Mode d'emploi :
    `outils_docs/README.md` ; spec `docs/superpowers/specs/2026-11-11-atelier-ecrans-design.md` ; plan `tasks/plans/atelier-ecrans.md`.
  - `etiquettes_qr_web.py` (+ `etiquettes_qr_page.py`, `_page_js.py`, `_page_impression.py`, `_modele.py`, `_verdict.py`, `_ecriture.py`,
    `_suivi.py`, `_filtre_public.py`, `_publication.py`, `_page_publication.py`, `build/cible_etiquettes_qr.py`) — page « Etiquettes QR
    code » http://127.0.0.1:7970 (2026-11-12 ; tuile de l'annuaire,
    groupe Ateliers, arret libre ; tache VS Code ; cible Custom detachee, `NOM_CIBLE` etiquettes_qr). QR code d'identite de
    chaque carte (du TEXTE par defaut ; mode lien, A10 : adresse d'une fiche PUBLIQUE sur GitHub Pages, branche orpheline
    `etiquettes` poussee par la plomberie git sans toucher l'arbre de travail, `etiquettes_qr_publication.py::publie` ; chaque
    ligne passe le filtre des secrets du persist puis `etiquettes_qr_filtre_public.py::controle_public`) : lignes standard (`etiquettes_qr_modele.CHAMPS`), cle du persist (jamais un secret, ni une
    valeur qui en contient un) ou texte libre, texte avant/apres ; style ; verdict de lisibilite (`etiquettes_qr_verdict.py`, seuils
    cales sur l'essai du 2026-11-12) ; impression a 100 %, planche A4, planche d'essai, export PNG/SVG ; notes d'impression
    (`outils_docs/etiquettes_qr/impressions.json`, empreinte seule). Reglages hors flash : `outils_docs/etiquettes_qr/gabarit.json` et
    `cartes/<env>.json`. Page de la carte (ESP32) : `data/fs/qrcodePage.be` (SOLIDIFIE, bouton dans le menu Outils, route
    `/qrcode`), `data/sd/{html,css,js}/qrcode.*`, `qrcode_options.js` (options communes a l'outil et a la carte),
    `qr-code-styling.min.js.gz` ; liste `etiquette_qr` de `[berry_commun]`, exclue des envs sans page ; fichier GENERE
    `data/<lieu>/<carte>/qrcode.json`, range dans `/json/` au demarrage. Suivi (`etiquettes_qr_suivi.py::etats`) : badges
    « a reimprimer », « a regenerer », etat de la carte, lien « Televerser » vers la page Build (`build_page_atelier.py`,
    `depuis=qrcode`) ; lien « Etiquette QR a refaire » apres un renommage (`fichiers_berry_renommage.py`, le reglage suit le
    nouveau nom) ou une modification de l'assistant persist. Bancs `test_etiquettes_qr_*.py`, sondes `test_etiquettes_qr_page_chrome.py`
    et `test_qrcode_carte_chrome.py`, `berry/banc_qrcode_page.py`, `build/test_qrcode_build.py`, `build/test_cible_etiquettes_qr.py`.
    Mode d'emploi : `outils_docs/README.md` ; spec `docs/superpowers/specs/2026-11-12-etiquettes-qrcode-design.md` ; plan
    `tasks/plans/etiquettes-qrcode.md`.
  - `maintenance/organigramme_plans.py` (+ `organigramme_pptx.mjs`, `outils_pc/organigramme_plans_web.py`) — organigramme des plans
    de `tasks/plans/` (2026-11-14) : lit les clés `famille:`, `parent:`, `liens:`, `spec:` de l'en-tête de chaque plan (format :
    `tasks/plans/_FORMAT.md`) et les dates git ; écrit `outils_docs/organigramme_plans/` (`plans.json`, `index.html` = vue arbre avec
    détail au clic, `organigramme-plans.pptx` = synthèse + une diapo par famille, nécessite `pptxgenjs` hors dépôt dans
    `%LOCALAPPDATA%\outils_tasmota\organigramme`). Régénéré par le hook `index_plans_edition.sh` à chaque édition d'un plan ;
    `--verifier` (code 1 si en retard), `--publier` (GitHub Pages : `https://fdaubercy.github.io/Tasmota/organigramme.html`, branche
    `etiquettes`, IPv4 masquées, jamais de force ; la publication des étiquettes QR garde ce fichier). Tuile « Organigramme des plans »
    de l'annuaire, page http://127.0.0.1:7990 en lecture seule, banc `outils_pc/test_organigramme_plans_web.py`.
  - `menage_web.py` (+ `menage_page.py`, `menage_lancement.py`, `menage_memoire.py`, `menage_rapport.py`, `build/cible_menage.py`) — page « Ménage du dépôt »
    http://127.0.0.1:7995 (2026-11-14, plan `tasks/plans/menage-page.md`, v1 lecture seule ; tuile de l'annuaire, groupe Dépôt et références, arrêt libre ; tâche VS Code ; cible
    Custom détachée, `NOM_CIBLE` menage). Lance `claude -p --agent auditeur-menage` (outils de lecture, jamais d'écriture), valide le rapport JSON
    (`outils_docs/schemas/menage_rapport.schema.json`) et montre les propositions triées par risque ; refus pendant un build. Seule écriture : la liste « à garder »
    hors dépôt (`%LOCALAPPDATA%\outils_tasmota\menage\garde.json`). `menage_verification.py` (A9) : contre-vérification des propositions par git, faite par la page et non par l'agent (existe, suivi, modifié = « en cours », renvois documents ou code, risque relevé). Couverture de l'audit (A10) : `couverture`, `limites`, `ecartes` du rapport (`menage_rapport.py`), carte dédiée de `menage_page.py` ; défaut `sonnet` effort `max`. Appliquer un lot (plan `menage-appliquer`) : `menage_application.py` (aperçu par `git rm -n` / `git mv -n`, application réelle ou à blanc, jamais de commit, noms Windows courts et `.git*` protégés), routes `/appliquer/apercu`, `/appliquer`, `/appliquer/annuler` (retour en arrière de la dernière application, `menage_application.py::annule`, refusé après un commit ou si le fichier a été touché) et `/appliquer/derniere` de `menage_web.py` (écritures : ce PC seulement), bloc « Appliquer un lot » de `menage_page.py` ; rapports d'audit sauvegardés hors dépôt, rouverts sans nouvel audit (`/rapports`, `/rapports/ouvrir`, `menage_page_rapports.py`, `menage_lancement.py::ouvre_rapport`) ; `menage_verification.py` donne aussi la ligne et l'extrait de chaque renvoi dans un document. Bancs `test_menage_*.py`, sonde `test_menage_page_chrome.py`, `build/test_cible_menage.py`.
  - `cartes_simulees_web.py` (+ `cartes_simulees.py`, `cartes_simulees_reseau.py`, `cartes_simulees_page.py`, `berry/simule_carte_rideau.be`, `build/cible_cartes_simulees.py`) — page
    « Cartes simulées » http://127.0.0.1:7940 (2026-11-14, plan `tasks/plans/cartes-simulees.md` ; tuile de l'annuaire, groupe Bus et cartes, arrêt libre ; tâche VS Code ; cible
    Custom détachée, `NOM_CIBLE` cartes_simulees). Simule hors ligne une carte du parc : serveur local au port web de la vraie carte, identité réseau lue dans son persist,
    rideau du garage rejoué par les vrais modules Berry (`berry.exe`, bouchons) avec la position du P4 lue en lecture seule (`Status 10`). Une carte qui répond (le P4)
    n'est JAMAIS simulée (409) ; MQTT jamais connecté ; pas d'alias d'IP. Rien n'est écrit dans le dépôt. Bancs `test_cartes_simulees.py`, `test_cartes_simulees_web.py`,
    sonde `test_cartes_simulees_page_chrome.py`, `build/test_cible_cartes_simulees.py`. Mode d'emploi : `outils_docs/README.md` § « Cartes simulées (page web) ».
  - `icones_catalogue_web.py` (+ `icones_catalogue.py`, `icones_catalogue_page.py`, `build/cible_icones_catalogue.py`) — page « Catalogue d'icônes » http://127.0.0.1:7930
    (2026-11-15, plan `tasks/plans/atelier-ecrans.md` A18 ; tuile de l'annuaire, groupe Dépôt et références, lecture seule, aucune route POST ; tâche VS Code ; cible Custom détachée,
    `NOM_CIBLE` icones_catalogue). Glyphes MDI du firmware (`outils_docs/schemas/icones_firmware.json`, police locale), usages relevés dans `ecran.json`, `pages.jsonl` et les `.be`,
    PNG de `data/` et `outils_docs/atelier_ecrans/images/`, sources de `ICONES_IMAGES_SOURCES.md`, codes absents du firmware. Bancs `test_icones_catalogue.py` (18 mutants),
    `test_icones_catalogue_web.py`, sonde `test_icones_catalogue_page_chrome.py`, `build/test_cible_icones_catalogue.py`. Mode d'emploi : `outils_docs/README.md` § « Catalogue d'icônes (page web) ».
  - `ftp_cartes_web.py` (+ `ftp_cartes_liste.py`, `ftp_cartes_session.py`, `ftp_cartes_chemins.py` (fonctions pures : chemins, noms FAT, fichiers protégés), `ftp_cartes_onglets.py`, `ftp_cartes_page.py`, `build/cible_ftp_cartes.py`) : page « Navigateur FTP des cartes » http://127.0.0.1:7450
    (2026-11-21, plan `tasks/plans/navigateur-ftp-cartes.md`, spec `docs/superpowers/specs/2026-11-20-navigateur-ftp-cartes-design.md` ; tuile de l'annuaire, groupe Configuration des cartes ;
    tâche VS Code ; cible Custom détachée, `NOM_CIBLE` ftp_cartes). Parcourt les fichiers de la Flash ou de la SD d'une carte par FTP : téléchargement (zip compris), envoi, dossier, déplacement,
    suppression. ÉCRIT sur les cartes, depuis ce PC seulement, jamais dans le dépôt ; fichiers protégés (`autoexec.be`, `_persist.json`, `.bec`, `.drvset*`, `/sd`, `/json`, ou un dossier qui en contient un) : deux confirmations pour les supprimer, les déplacer ET les écraser par un envoi ; noms comparés comme FatFs (casse, points et espaces finaux), `\` refusé, type vu par la page contrôlé avant suppression ou déplacement (2026-11-22).
    Le FTP de la carte est allumé à la demande (`UfsFTP`) et éteint à la fin de session (Déconnecter, autre carte, fermeture du DERNIER onglet, 15 min sans action, arrêt de l'outil) ;
    chaque onglet a un identifiant (`ftp_cartes_onglets.py`, sondage `GET /etat?onglet=`, `sendBeacon` sur `/ferme`) et un onglet disparu sans le dire est oublié après 90 s ; `/zip` et `/telecharge` portent la paire env/support (409 si la session a changé) ; GET à effet refusés d'une autre origine (`Sec-Fetch-Site`, `Origin`) ; `UfsFTP 0` non confirmé : retenté, session gardée « en cours » ; liste `GET /cartes` en cache, préchauffée ;
    persist `serveur.serveurFTP.activation` à `OFF` (les 15 persist du dépôt qui portent le bloc) et filet `data/fs/globalFonctions.be::regleFTP`. Esclaves du Range Extender absents (FTP injoignable).
    Outil lancé HORS du job de l'annuaire (`dans_job=False`, `route_occupe="/execution"`) : « Arrêter » est REFUSÉ pendant une session ouverte (cliquer « Déconnecter » d'abord) ; un arrêt brutal hors annuaire laisse le FTP allumé (`atexit` ne passe pas). Rien essayé sur une vraie
    carte (plan A7). Bancs `test_ftp_cartes_liste.py`, `test_ftp_cartes_session.py` (lent), `test_ftp_cartes_session_garde.py`, `test_ftp_cartes_session_relecture.py`, `test_ftp_cartes_session_p4.py` (carte qui ignore le chemin de `MLSD`, constaté sur le P4), `test_ftp_cartes_onglets.py`, `test_ftp_cartes_web.py`, `test_ftp_cartes_web_relecture.py`, sonde `test_ftp_cartes_page_chrome.py` (appelle `test_ftp_cartes_page_chrome_onglets.py` et `_corrections.py`), faux serveur `faux_ftp_carte.py`,
    `build/test_cible_ftp_cartes.py`. Mode d'emploi : `outils_docs/README.md` § « Navigateur FTP des cartes (page web) ».
  - `taches_planifiees_web.py` (+ `taches_planifiees_page.py`, `_page_gestes.py`, `_github.py`, `_pc.py`, `_sante.py`, `_gestes.py`, `_actions.py`, `build/cible_taches_planifiees.py`) — page « Tâches planifiées » http://127.0.0.1:7920 (2026-11-15, plan `tasks/plans/compilations-nuit.md` ; tuile de l'annuaire, groupe Déploiement ; tâche VS Code ; cible Custom détachée, `NOM_CIBLE` taches_planifiees). Montre et pilote les compilations de nuit des envs perso, voie PC et voie GitHub : bandeau de santé recalculé à chaque ouverture (permissions, état du workflow, âge du dernier run planifié, car `actions/permissions` dit `enabled: true` même quand GitHub a désactivé le fork), gestes `POST /geste` (activer, heure, envs, lancer, arrêter ; jamais depuis un autre appareil, `X-Taches: 1`, un geste à la fois par verrou, lancer et arrêter en deux clics). Arrêter la voie PC arrête la série en cours de la page Build **même lancée à la main**. Bancs `test_taches_planifiees_{web,gestes,post}.py` (faux `gh`, faux `schtasks`, fausse page Build, dépôt temporaire), sonde `test_taches_planifiees_page_chrome.py` (hermétique, 5 témoins), `build/test_cible_taches_planifiees.py`. Mode d'emploi : `outils_docs/README.md` § « Compilations de nuit et tâches planifiées ».
  - `maintenance/compilation_nuit.py` (+ `compilation_nuit_tache.py`, `matrice_github.py`) — compilation de nuit (2026-11-15) : le script pilote la page Build (:7700, « compiler » seul, refus si un build ou un autre `compilation_nuit.py` tourne, verrou `en_cours.json`, bilan de SA série seulement) ; `compilation_nuit_tache.py` gère la tâche Windows `Tasmota-CompilationNuit` (créée **désactivée**, 02:00, sans réveil ni rattrapage) ; `matrice_github.py` calcule la matrice du workflow `.github/workflows/build_custom.yml` (cenv moins `outils_docs/compilations_nuit/envs_github.json`, fichier écrit, commité et poussé par le bouton de la page, qui refuse si des commits sont non poussés ou en retard). Résultats dans `%LOCALAPPDATA%\outils_tasmota\compilations_nuit\`. Bancs `test_compilation_nuit.py`, `test_compilation_nuit_tache.py`, `test_matrice_github.py` (mutants).
  - `suivi_sondes.py` (+ `sondes_web.py`, `sondes_page.py`, `sondes_scan.py`, `sondes_actions.py`, `build/cible_sondes.py`) — page « Sondes en cours » http://127.0.0.1:7910 (2026-11-15, plan `tasks/plans/sondes-en-cours.md` ; tuile de l'annuaire, groupe Dépôt et références ; tâche VS Code ; cible Custom détachée, `NOM_CIBLE` sondes). Bancs et Chrome de sonde en cours, avec avancement RÉEL (vérifications faites, phase, dernier cas, échecs) pour les bancs qui appellent `suivi_sondes.suit()` ; `test_build_page_chrome.py` l'appelle pour les 33 sondes Chrome. Orphelins signalés, arrêt à deux clics d'un numéro présent dans le relevé seulement. Bancs `test_suivi_sondes.py`, `test_sondes_scan.py`, `test_sondes_web.py`, sonde `test_sondes_page_chrome.py`, `build/test_cible_sondes.py`. Mode d'emploi : `outils_docs/README.md` § « Sondes en cours ».
- `outils_docs/plan_maison/` (2026-11-15, plan `tasks/plans/plan-maison.md`) : `genere_plan_maison.py` + `placement.json` -> `plan_maison.html`, plan de la maison avec les cartes dans leurs pièces et vue réseau ; liens et rôles maître/esclave dérivés des `_persist.json`. Banc `test_plan_maison.py`. Mode d'emploi : `outils_docs/README.md` § « Plan de la maison ».
