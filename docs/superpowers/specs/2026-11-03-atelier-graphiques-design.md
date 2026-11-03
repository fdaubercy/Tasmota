# Atelier des graphiques — conception (2026-11-03)

Statut : conception validée question par question avec l'utilisateur le 2026-11-03 (13 réponses), relue par un
constructeur. Maquettes : `outils_docs/atelier_graphiques/` (**modèle B retenu, avec la grille du modèle C** pour
les pages dédiées).

## 1. Intention

Aujourd'hui, mettre un graphique sur une carte demande d'écrire à la main un module Berry, un gabarit, un script
ECharts et les listes du cenv (`/cuve` et `/energie` ont été faits ainsi). La page `/graphiques` des S3/P4 se
compose dans le navigateur, mais seulement en courbe, barres, escalier ou aire, à partir de l'historique.

L'atelier est un outil PC (page web locale, tuile de l'annuaire) qui :

1. lit les séries d'une carte (en ligne de préférence) ;
2. demande ce que l'utilisateur veut voir, et propose les 3 à 5 styles qui conviennent, avec leur raison ;
3. montre un aperçu avec les vraies valeurs, qui change à chaque réglage ;
4. affiche ce qui sera écrit dans les fichiers de la carte (diff), puis l'écrit dans le dépôt ;
5. renvoie vers la page Build pour l'envoi à la carte.

Réussite : un nouveau graphique (jauge, carte de chaleur, barres par jour…) apparaît sur la carte choisie sans
écrire une ligne de Berry ni de JS à la main, et on peut y revenir pour le modifier.

## 2. Objectifs, non-objectifs, anti-objectifs

**Objectifs**
- Destinations : page dédiée (plusieurs par carte), page `/graphiques` existante (étendue à de nouveaux types),
  encadré de l'accueil (SVG/CSS pur), ESP32 classiques sans PSRAM (SVG pur, sans ECharts).
- Données : séries de l'historique, toute valeur du JSON SENSOR, valeurs calculées (formule sur des séries),
  données en flash propres à un module (ex. kWh d'`energieFonctions.be`).
- Réglages par graphique : titre, libellés, unités, couleurs (lisibles en thème sombre) ; seuils et zones
  colorées ; période et cadence ; taille et disposition. **L'aperçu montre l'effet de chaque réglage.**
- Modifier ce que l'atelier a créé, et la composition de `/graphiques`.

**Non-objectifs**
- Envoyer lui-même les fichiers à la carte : c'est la page Build (onglet « Fichiers »).
- Remplacer Grafana ou l'historique du Pi.

**Anti-objectifs (échec même si « ça marche »)**
- Toucher aux pages écrites à la main (`/cuve`, `/energie`) ou aux drivers `controleXxx.be` des cartes.
- Générer du Berry par page, à relire et à tenir à jour (décision Q13 : moteur commun + description).
- Écrire pendant un build, ou laisser le dépôt à moitié écrit.
- Coûter de la RAM sur une carte tant que ses pages ne sont pas ouvertes.
- Embarquer les fichiers du moteur sur des cartes qui ne s'en servent pas (leçon du 2026-10-31).

## 3. Décisions de l'utilisateur (2026-11-03)

| # | Question | Réponse |
|---|---|---|
| 1 | Destinations | les quatre : page dédiée, `/graphiques`, encadré d'accueil, ESP32 classiques |
| 2 | Données | historique, JSON SENSOR, calculées, en flash |
| 3 | Séries et aperçu | carte en ligne (IP du cenv ou par le maître) ; sinon persist du dépôt et valeurs simulées, **signalé** |
| 4 | Conseil | intention de l'utilisateur × nature des séries → 3 à 5 styles classés, raison de chacun, écartés avec motif |
| 5 | Écriture | diff puis écriture atomique du dépôt, refus pendant un build ; lien vers l'onglet Fichiers de la page Build |
| 6 | Solidification | moteur sur le FS par défaut, case « Solidifier » (ajout à `custom_berry_solidify`) |
| 7 | Modification | ce que l'atelier a créé + composition de `/graphiques` ; jamais `/cuve`, `/energie` |
| 8 | Pages dédiées | plusieurs par carte, accès choisi par page : bouton d'accueil ou lien icône d'un encadré |
| 9 | `/graphiques` | à étendre au-delà des 4 types |
| 10 | Réglages | les quatre familles, avec aperçu de l'effet |
| 11 | Disposition | modèle B (trois colonnes) ; pour une page dédiée, le centre bascule sur la grille du modèle C |
| 12 | Ordre | 1) page dédiée S3/P4, 2) `/graphiques` étendue, 3) encadré d'accueil, 4) ESP32 classiques |
| 13 | Berry écrit | **un moteur commun** (écrit et testé une fois) + **une description JSON par carte** |

## 4. Architecture

```
PC : atelier_graphiques_web.py (:7950)          Carte S3/P4                       Carte ESP32 classique (palier 4)
  séries ← /histo?p=liste|jour|direct, Status 10   data/fs/pagesGraphiques.be        même moteur, rendu SVG seul
  conseil (règles, côté PC)                        + /sd/js/pages_graphiques.js
  aperçu = MÊME pages_graphiques.js que la carte   lit /json/pages_graphiques.json
  écrit : pages_graphiques.json, autoexec, cenv    routes, boutons, encadrés
```

### 4.1 Le moteur commun (sur la carte)

- `data/fs/pagesGraphiques.be` (écrit à la main, une fois, banc à l'appui) : un driver qui, au démarrage, lit
  **seulement l'index** de `/json/pages_graphiques.json` (routes, libellés de boutons, encadrés) — pas les
  graphiques — et déclare les routes (`webserver.on`) et les boutons (`web_add_main_button`). Les graphiques ne
  sont lus qu'à l'ouverture d'une page. Modèle à suivre : driver `HISTORIQUE_WEB` de
  `historiqueFonctions.be` (route déclarée, module importé à la première requête).
- Une page dédiée est servie par un gabarit commun (`/sd/html/pages_graphiques.html`, `/sd/css/pages_graphiques.css`)
  et `/sd/js/pages_graphiques.js`, qui reçoit la description de la page et trace chaque graphique.
- ECharts : le fichier déjà présent, `/graphiques?f=echarts.js.gz`, même clé de cache localStorage
  (`graphiquesFonctions.VERSION_BIBLIOTHEQUE`) ; extension liquidfill seulement si une page utilise le style
  « liquide » (servie par le moteur, fichier ajouté à la carte à ce moment-là).
- Valeurs : `/histo?p=direct|jour|mois` pour l'historique ; valeur instantanée du JSON SENSOR par une route du
  moteur (lecture de `tasmota.read_sensors()`, chemin demandé seulement) ; données en flash par un **adaptateur
  déclaré par module** (ex. `energieFonctions` : `f=donnees`), liste fermée dans le moteur.
- Valeurs calculées : dans le navigateur (`pages_graphiques.js`) pour les pages ; dans le Berry du moteur pour
  les encadrés d'accueil, qui n'exécutent aucun script. Formules restreintes : opérations `+ - * /`, constantes,
  séries nommées, fonctions `min max abs round`, cumul par période. **Jamais d'`eval` JS ni de `compile` Berry**
  sur une formule : petit analyseur à liste blanche, des deux côtés.
- Solidifiable : le moteur respecte les pièges 12 et suivants de `outils_docs/SOLIDIFICATION_BERRY.md` (aucun
  état dans la table du module, `import` de soi-même, appels par `pagesGraphiques.nom`). Sur le FS par défaut ;
  la case « Solidifier » l'ajoute à `custom_berry_solidify` de l'env (firmware à recompiler, signalé).
- Charte des logs Berry du `CLAUDE.md` (cible `serveurWeb`, `_ERREUR` dans les `except`).

### 4.2 La description (`data/<lieu>/<carte>/pages_graphiques.json` → `/json/pages_graphiques.json`)

Seul fichier que l'atelier réécrit à chaque modification. Hors persist (le persist est en RAM en permanence),
comme `graphiques.json`. Forme indicative (le constructeur fixe le schéma exact, avec validation des deux côtés) :

```json
{"version": 1,
 "pages": [{"id": "tableau-cuve", "titre": "Cuve et garage", "acces": "bouton",
            "graphiques": [{"type": "cadran", "titre": "Volume", "series": ["sensorsCuve.niveauCuve.volume"],
                            "min": 0, "max": 6732, "zones": [[0.2, "#c0392b"], [0.4, "#c27400"]],
                            "periode": "direct", "cadence": 10, "largeur": "demi", "hauteur": 180}]}],
 "encadres": [{"id": "taux-cuve", "type": "demi-cercle", "serie": "...", "lien": "tableau-cuve"}],
 "calculees": {"cuve.manque": "6732 - sensorsCuve.niveauCuve.volume"}}
```

Bornes, validées par la carte (refus explicite, page « description invalide ») et par l'atelier : nombre de
pages, de graphiques par page, de séries par graphique, taille du fichier (même esprit que
`graphiquesFonctions::valideComposition` : 8 graphiques, 12 séries, 8192 octets).

### 4.3 Ce que l'atelier écrit dans le dépôt

À la **première** page ou au premier encadré d'une carte :
- `autoexec.be` de la carte : une ligne `demarrage.charge(["pagesGraphiques"])` (ou `demarrage.importe` si
  solidifié), à la place indiquée par la liste ordonnée — après `historique()` si la carte en a un ;
- cenv : liste `pages_graphiques` dans `[berry_commun]` (moteur, gabarit, JS, CSS), ajoutée au
  `custom_files_upload` de l'env et au `custom_files_exclude` de **tous les autres** envs (règle du 2026-10-31) ;
  `custom_berry_solidify` si la case est cochée ;
- liquidfill : ajouté au FS de l'env seulement si un graphique « liquide » existe.

À chaque modification : `pages_graphiques.json` seul (et la composition de `graphiques.json` pour la destination
`/graphiques`). La suppression de la dernière page propose de retirer la ligne d'autoexec et l'env des listes.

Moteur d'écriture : `fichiers_berry_ini.py` (résolution des `${...}`, commentaires gardés) et
`fichiers_berry_sauvegarde.Transaction` (atomique, copie horodatée, marque d'opération interrompue) ;
refus pendant un build (`build_serie.builds_en_cours_defaut`) ; diff de chaque fichier affiché avant écriture,
empreinte vérifiée à l'écriture. Après écriture : `banc_demarrage.py` signalé à lancer (règle du 2026-11-01),
**jamais** `--enregistre` automatique.

### 4.4 L'atelier (PC)

- Modules dans `outils_docs/scripts_python/outils_pc/` (même dossier : ils s'importent entre eux) :
  `atelier_graphiques_web.py` (serveur, port 7950), `_page.py` (HTML/CSS/JS), `_series.py` (lecture carte ou
  dépôt), `_conseil.py` (règles de recommandation), `_ecriture.py` (diff et transaction). Sécurité et lien par
  `acces_web.py` (jeton pour un autre appareil, comme les autres outils).
- Annuaire : entrée dans `annuaire_registre.py`, groupe « Maintenance », arrêt libre (rien n'est écrit avant
  « Écrire dans le dépôt ») ; tâche VS Code « Outil : atelier des graphiques » ; cible Custom
  `build/cible_atelier_graphiques.py` démarrée **détachée** comme celle de la page Build.
- Adresse d'une carte : IP du cenv (`WIFI_IP_ADDRESS`), sinon esclave par le maître
  (`build_envs.adresse_par_maitre`, `build_ota_maitre.joint_par_maitre`). Lecture seule sur la carte :
  `/histo?p=liste|jour|direct`, `Status 10`, et la route du moteur si présent. Carte injoignable : séries
  déduites du persist et de l'historique du dépôt, valeurs simulées, bandeau « valeurs simulées ».
- **Aperçu = le vrai moteur** : la page charge `data/sd/js/pages_graphiques.js` du dépôt et lui passe la
  description en cours d'édition et les valeurs lues ; l'aperçu est donc exactement ce que la carte affichera.
  Bascules PC / téléphone / thème sombre de Tasmota.
- Disposition (modèle B) : gauche = carte + intention + séries (historique, JSON SENSOR, calculées, flash) ;
  centre = aperçu + styles proposés en vignettes ; droite = réglages ; bas = onglets du code (description
  JSON, autoexec, cenv, et pour la destination `/graphiques` le `graphiques.json`), boutons « Voir le diff
  complet », « Écrire dans le dépôt », « Envoyer par la page Build ↗ » (ouvre :7700, onglet Fichiers, `?env=`).
  Pour une page dédiée, le centre bascule sur la grille du modèle C (tuiles déplaçables, largeur demi/pleine).

### 4.5 Le conseil de style

Côté PC, règles explicites et testées (pas d'apprentissage) : entrée = intention (évolution, valeur actuelle face
à un seuil, comparaison, répartition, cumul, lien entre deux mesures, habitudes heure × jour) + nature des séries
(unité, nombre, bornes connues, cadence, état ON/OFF ou compteur) + destination possible (accueil et ESP32 :
styles SVG seulement). Sortie : 3 à 5 styles classés, une phrase de raison chacun, styles écartés avec motif.

Catalogue de départ (ECharts 6.1.0 natif sauf mention) : courbe, aire, escalier, barres, barres empilées, barres
par période (cumul), courbes deux axes, graphiques liés (curseur commun), ligne de seuil et zones, cadran
(`gauge`), anneau / camembert, carte de chaleur heure × jour, nuage de points, radar, liquide (extension
liquidfill), et en SVG pur les jauges D à H du catalogue `outils_docs/jauges/` (demi-cercle, barre à segments,
tube…) plus courbe et barres simples (comme `energie.js`).

### 4.6 Extension de `/graphiques` (palier 2)

`graphiques_trace.js` et `graphiquesFonctions::valideComposition` acceptent de nouveaux types temporels
(barres empilées, carte de chaleur heure × jour, nuage de points, seuils et zones) ; les compositions existantes
restent valides telles quelles. Concerne les 6 cartes à historique : renvoi du FS sur chacune, `banc_graphiques.py`
étendu.

## 5. Paliers (chacun utilisable seul)

1. **Page dédiée S3/P4** : moteur (`pagesGraphiques.be`, `pages_graphiques.js`, gabarit), atelier (séries,
   conseil, aperçu, écriture), tuile de l'annuaire, première page réelle sur le P4 ou la cuve.
2. **`/graphiques` étendue** : nouveaux types, composition lue et écrite par l'atelier.
3. **Encadré d'accueil** : jauges SVG dans l'accueil (rendu Berry côté carte, `web_sensor`), lien icône vers
   une page dédiée.
4. **ESP32 classiques** : moteur en rendu SVG seul (sans ECharts ni historique), mesure du tas et du FS sur la
   carte avant de déclarer la cible tenable (leçon du 2026-11-02, différentiel).

Valeurs calculées et adaptateurs « en flash » : au palier 1 pour les pages (navigateur), au palier 3 pour les
encadrés (Berry).

## 6. Contraintes

- Fichiers sous 500 lignes ; pas de nouvelle dépendance Python ni JS (ECharts et liquidfill déjà au dépôt).
- Bancs : un par module Python (`test_atelier_graphiques_*.py`, copies temporaires, jamais le vrai dépôt) ;
  banc Berry du moteur (`berry/banc_pages_graphiques.py`, avec `global.pagesGraphiques = module(...)` pour voir
  les pièges de solidification) ; sonde Chrome de la page de l'atelier et de la page générée (capture, largeur
  mesurée : leçon du 2026-10-31).
- Validation sur une vraie carte (journal web, chercher `_ERREUR`) avant de cocher un palier.
- Aucune compilation lancée par l'atelier ; les compilations de Claude passent par la page Build.
- Documents : mode d'emploi dans `outils_docs/README.md`, entrée dans la carte des documents du `CLAUDE.md`.

## 7. Choix de Claude après relecture (à contrôler par l'utilisateur)

Points soulevés par la relecture du constructeur, tranchés sans changer ce qui est construit :

1. **Adaptateurs « en flash »** : l'interface (liste fermée dans le moteur, route `?f=sources` qui dit lesquels
   sont présents sur la carte) est posée au palier 1, mais le seul module à données en flash (`energieFonctions`)
   vit sur le différentiel, un ESP32 classique : son adaptateur arrive donc au palier 4.
2. **Exclusions du cenv** : l'atelier ajoute `${berry_commun.pages_graphiques}` au `custom_files_exclude` de
   chaque env qui ne l'embarque pas (il en crée un si l'env n'en a pas) ; un env créé plus tard à partir d'une
   carte modèle hérite des listes du modèle (`fichiers_berry_creation`), à vérifier par un banc.
3. **Esclave derrière le NAPT** : lecture seule par l'adresse `IP:port` du maître (`build_envs.adresse_par_maitre`),
   **sans** `RoutageRangeExtender` ni `Sleep 0` (ce sont des écritures sur le maître) ; si la lecture échoue :
   valeurs simulées, bandeau « carte injoignable ».
4. **Moteur sans historique** : le moteur ne dépend pas de `historiqueFonctions` (son propre driver déclare
   routes et boutons ; `HISTORIQUE_WEB` n'est qu'un modèle). Sans historique sur la carte, seules les valeurs
   instantanées sont proposées, les styles temporels sont grisés avec la raison.
5. **Formules** : une formule combine des séries de même nature — instantanées entre elles, ou historiques sur
   la même période ; « cumul par période » ne s'applique qu'à une série de l'historique. Un mélange est refusé
   à la saisie, avec le motif.
6. **Moteur solidifié ou non** : l'atelier le lit dans `custom_berry_solidify` de l'env, `${...}` résolus par
   `fichiers_berry_ini.py`, et écrit `demarrage.importe` ou `demarrage.charge` en conséquence.

## 8. Laissé au constructeur

Schéma exact de la description et ses bornes ; noms des routes et des fonctions du moteur ; détail des règles de
conseil ; forme des diffs ; tests ; découpage des modules Python sous 500 lignes.
