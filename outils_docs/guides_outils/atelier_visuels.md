# Atelier des visuels d'accueil

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Atelier des visuels d'accueil (page web)

Une page qui prépare le **visuel de la page d'accueil** d'une carte ESP32 : une image de fond (la façade d'une maison, un
schéma de cuve) sur laquelle on pose des points chauds qui montrent l'état en direct. La page écrit une description
`visuel.json` et un fond dans le dossier de la carte ; la carte les affiche sous les boutons de ses relais.
Conception : [spec](../../docs/superpowers/specs/2026-11-13-atelier-visuels-accueil-design.md) ; plan
`tasks/plans/atelier-visuels.md` ; maquettes `outils_docs/visuels_accueil/`.

### Lancer la page

Port **7985**. Tuile « Atelier des visuels » de l'annuaire (groupe Ateliers), tâche VS Code « Outil : atelier des visuels (http://127.0.0.1:7985) » et cible Custom « Atelier des visuels (page web) » (`build/cible_atelier_visuels.py`, page démarrée détachée, `pio run` : jamais pendant un build ; banc `build/test_cible_atelier_visuels.py`) :
- **Ligne de commande** : `python outils_docs/scripts_python/outils_pc/atelier_visuels_web.py` (`--http 7985`, `--local`,
  `--sans-navigateur`). Règle d'accès commune : `acces_web.py` (depuis un autre appareil, lien à jeton de la console).

Le port 7990 appartient à l'organigramme des plans (`organigramme_plans_web.py`, tuile de l'annuaire) : l'atelier des visuels a donc pris le 7985 (décidé le 2026-11-14).

### Utilisation

1. **Carte** : liste des cartes du parc, groupée par lieu.
2. **Fond**, deux modes au choix :
   - *photo* : la photo recadrée, réduite à la largeur de la page d'accueil et compressée (WebP, repli JPEG) ;
   - *dessin* : un dessin à plat de formes unies (rectangles, polygones, motifs briques ou tuiles), dont la couleur part
     de celle de la photo sous la forme. Des gabarits tout faits (mur, toit, fenêtre, porte, volet roulant...) se posent
     puis s'ajustent. Le fond est un SVG nettoyé : seuls `svg`, `g`, `path` et leurs attributs de forme et de couleur
     sont gardés.
   Une zone peut être **effacée** (ce qui n'est pas dessiné disparaît, une voiture garée par exemple) ou **gardée en photo**
   au milieu du dessin. Le poids du fond est affiché en permanence ; avertissement au-dessus de 40 Ko, refus d'écriture
   au-dessus de 60 Ko sur un ESP32 classique et de 200 Ko sur S3 et P4.
3. **Points chauds**, posés à la souris :
   - *voyant* : forme, couleurs ON et OFF, icône facultative ;
   - *valeur* : une mesure avec texte avant et après, unité, décimales ;
   - *liaison* : un trait entre deux points, animé quand la liaison est active.
   Sources : un **relais** (numéro Tasmota), une **mesure** du JSON SENSOR (les entrées passent par là), ou une
   **liaison** de type `modbus_serie`, `modbus_esclave` (id d'esclave), `esclave` (adresse MAC, UDP ou range extender) ou
   `wifi`. Les listes viennent du persist de la carte (lu en lecture seule, secrets jamais envoyés à la page) ; `GET /sources`.
   `seuil_s` règle l'âge au-delà duquel une liaison ModBus est dite muette.
   Aperçu en direct et contrôle : `GET /etat?env=&chemins=` lit `/visuel?f=etat` de la carte (délai de 3 s) et rend `{etat: "connu", relais, mesures, liaisons}`
   ou `{etat: "inconnu"}` (carte muette ou sans la route, en moins de 3,5 s) ; seules les mesures numériques sortent, jamais un texte ni une clé secrète ;
   `POST /valide {description, octets?, puce?}` rend `{erreurs: [...]}` (liste vide = valide, mêmes règles que `cas_visuel.json`). La page se replie sans ces routes.
4. **Icônes** : recherche en ligne sur Iconify (hôte fixe `api.iconify.design`), licence affichée ; les licences
   permissives passent, les CC BY demandent une confirmation d'attribution à la conservation, le reste est masqué.
5. **Export** : SVG à télécharger, code SVG, fragment HTML autonome (un petit script en ligne bascule l'état au clic),
   PNG. Rien n'est écrit au serveur ni au dépôt par l'export.
6. **Écrire dans le dépôt**, en deux temps : le diff (`/ecriture/prevoit`), puis l'écriture (`/ecriture/ecrit`) avec
   l'empreinte du diff. Refusée pendant un build, sur une empreinte périmée, ou si les fichiers de la page
   (`visuelFonctions.be`, `controleVisuel.be`, `visuel.js`) manquent au dépôt. Écrit `data/<lieu>/<carte>/visuel.json` et le
   fond (`visuel.svg`, `.webp` ou `.jpg`, un seul), la ligne `controleVisuel` en dernier de l'`autoexec.be`, et lève
   la liste `visuel_accueil` du cenv pour cet env. « Décocher » le visuel fait l'inverse (`/ecriture/prevoit_retire`,
   `/ecriture/retire`).
7. **Téléverser** : le lien mène à la page Build (7700, `?env=&depuis=visuel&fichiers=visuel.json,visuel.<type>&redemarrer=1`).
   Le **suivi** compare le `visuel.json` du dépôt à celui de la carte : identique, différente, absente ou inconnue (carte muette).
8. **Consignes** (2026-11-15, plan `atelier-visuels` A7) : le bouton « Consignes » de l'en-tête ouvre `outils_docs/visuels_accueil/CONSIGNES_VISUELS.md`
   (`GET /consignes`, texte seul, lecture seule). Un panneau « Consignes » rappelle les règles de l'élément sélectionné : un voyant montre celles du
   capteur de fermeture, du feu orange, de la lampe et de la caméra, une valeur celle du capteur de fermeture, une liaison celles du garage, du portail
   et de la commande par clic ; le jour et la nuit s'y ajoutent. Le fichier est **relu à chaque sélection** (`GET /consignes/regles`,
   `atelier_visuels_consignes.py`) : une règle ajoutée au fichier apparaît sans relancer l'outil. Les règles viennent du tableau de la section « Les organes
   et leurs règles » et des puces des sections « Commande par clic » et « Jour et nuit » : pour qu'un nouvel organe soit rappelé, il faut l'ajouter à
   `atelier_visuels_consignes.py::PAR_TYPE`. Bancs `test_atelier_visuels_consignes.py` et `sonde_consignes` de `test_atelier_visuels_page_chrome.py`.

### Assistant IA (facultatif)

Propose un dessin ou des opérations à partir d'une photo. Trois fournisseurs : `claude_local` (`claude -p` en lecture
seule), `ollama` (modèle local, rien ne sort du PC) et `api_externe` (API de type « chat completions », url, modèle et clé
de l'utilisateur). Un fournisseur externe n'est appelé qu'après un **avertissement confirmé** : la photo part chez un tiers,
même par l'abonnement Claude. La photo n'existe que dans un dossier temporaire hors dépôt. Les clés sont dans
`%APPDATA%\atelier_visuels\config.json`, hors dépôt, et ne reviennent jamais à la page. Un plafond d'envois par jour est
compté (`quota.json` à côté) ; une réponse « trop de requêtes » passe le quota au rouge et n'est jamais retentée.

### Côté carte

- `data/fs/visuelFonctions.be` (solidifié) : route `/visuel` (`?f=fond` : le fond ; `?f=etat` : un seul JSON d'état, chaque
  bloc n'existe que si la description a une source de ce type). `data/fs/controleVisuel.be` pose le driver seulement si
  `/json/visuel.json` existe et est valide. Moteur de dessin : `data/sd/js/visuel.js`.
- Liste `visuel_accueil` de `[berry_commun]` : exclue de tous les envs tant qu'aucune carte ne s'en sert, levée env par env
  par l'outil.
- **La description n'est relue qu'au redémarrage** de la carte (d'où `redemarrer=1` dans le lien de téléversement).
- Rythme : `rafraichissement` de la description, **2345 ms par défaut**, minimum 1000 ; la requête suivante part après la réponse.
- Le visuel et la façade des volets peuvent coexister ; le visuel vient dessous.

### Limites connues

- Pas encore essayé sur une carte réelle.
- `modbus_esclave` : côté maître, un esclave de la voie série n'a pas d'horodatage propre (`modbusFonctions.etat().ipsApprises`
  ne couvre que la voie UDP) ; il reste donc muet pour ce type. Seul `modbus_serie` s'appuie sur `derniereReponseSerie`.

Bancs : `outils_pc/test_atelier_visuels_*.py` (dont les sondes Chrome `_page_chrome.py` et `_page_chrome_faux.py`),
`outils_pc/test_atelier_visuels_formes.mjs`, `berry/banc_visuel.py`.

### Icône à la place d'un bouton de relais (étude)

Rapport du 2026-11-15, lecture du code seule, rien d'essayé sur carte : `ICONES_BOUTONS_RELAIS.md` (dans ce dossier). Cinq voies
comparées (caractère Unicode dans `WebButton`, script Berry sur le bouton natif, icône du visuel d'accueil, bouton Berry complet,
C++). Recommandation : ajouter le clic à `visuel.js` (voie C) pour une icône posée sur l'organe.
