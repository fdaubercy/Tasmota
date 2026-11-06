# Atelier des graphiques : destination « Graphiques » et bouton « Téléverser » — conception

Date : 2026-11-04. Complète `2026-11-03-atelier-graphiques-design.md` (palier 1 clos le 2026-11-04) et en
remplace le §4.6 (« Extension de `/graphiques` », palier 2). L'encadré d'accueil (palier 3) est **abandonné**
(décision de l'utilisateur du 2026-11-04 : trop de contraintes).

## 1. Intention

Aujourd'hui, l'atelier (port 7950) ne sait écrire que des pages dédiées (`/pages?p=<id>`), et l'envoi à la carte se
fait à la main : construire le FS sur la page Build (7700), puis cocher les bons fichiers dans l'onglet « Fichiers ».
L'utilisateur veut :

1. poser un graphique **sur une page dédiée existante, sur la page `/graphiques` existante, ou sur une nouvelle
   page** — le tout depuis le menu « Page » ;
2. que `/graphiques` sache afficher **tous les styles de l'atelier** (15), pas seulement ses 4 actuels ;
3. après « Écrire dans le dépôt », un bouton **« Téléverser »** qui ouvre la page Build, y lance seule la
   construction du FS, coche seule les fichiers nécessaires, et dit pourquoi. **L'envoi attend le clic de
   l'utilisateur sur « Envoyer ».**

## 2. Objectifs, non-objectifs, anti-objectifs

Objectifs : les trois points ci-dessus ; les compositions `/graphiques` existantes restent valides et s'affichent
comme avant, octet pour octet de leur rendu actuel.

Non-objectifs : encadré d'accueil (abandonné) ; ESP32 classiques (palier 4, inchangé) ; envoi automatique à la carte.

Anti-objectifs (échec même si « ça marche ») :
- un envoi à la carte sans clic de l'utilisateur ;
- une composition éditée sur la carte (mode édition de `/graphiques`) écrasée sans avertissement par la version du
  dépôt ;
- une carte dont `/graphiques` affichait quelque chose et n'affiche plus rien (fichier JS manquant, validation plus
  stricte qu'avant) ;
- une page Build qui coche des fichiers sans dire que c'est l'atelier qui les a choisis.

## 3. Le menu « Page »

Entrées, dans cet ordre :
- les pages dédiées déjà décrites pour la carte (ex. « /tableau — « Tableau » ») ;
- **« Graphiques (/graphiques) »** — seulement si la carte a l'historique actif (`diverses.historique.activation`
  = ON) : sans historique, la page `/graphiques` n'existe pas sur la carte ;
- **« Autre… (nouvelle page) »** — remplace le bouton « + Page » : crée une page dédiée, champs « Adresse » et
  « Titre page » à remplir (règles d'adresse inchangées : a-z, 0-9, tirets).

Destination « Graphiques » : les champs « Adresse », « Titre page », « Accès » et la case « Solidifier » sont
masqués (sans objet). Les autres réglages restent.

## 4. `/graphiques` affiche tous les styles

### 4.1 Format

La composition (clé `graphiques` de `data/<lieu>/<carte>/graphiques.json`, publiée en `/json/graphiques.json`)
accepte **deux formes de graphique** :
- **forme actuelle** (`type` ∈ courbe, barres, escalier, aire ; `series` = liste ou `"autres"`) : validée et tracée
  exactement comme aujourd'hui (`graphiquesFonctions::valideComposition`, `graphiques_trace.js`) ;
- **forme atelier** : un objet graphique **au schéma des pages dédiées** (celui que valident
  `atelier_graphiques_description.py::valide` et `pagesGraphiquesValidation.be`), marqué par une clé
  `"moteur": "pages"`. Validé par le validateur des pages, tracé par le moteur des pages
  (`PagesGraphiques.optionDe`), avec ses valeurs calculées (`calc:`) s'il en a.

Tout graphique écrit par l'atelier vers `/graphiques` prend la forme atelier, **même pour les 4 styles communs** :
une seule voie d'écriture, et les réglages de l'atelier (libellés, unités, couleurs, bornes, zones) ne sont pas
perdus.

### 4.2 Côté carte

- `graphiques.js` délègue au moteur des pages tout graphique `"moteur": "pages"` ; il charge pour cela
  `pages_graphiques.js` (et `pages_graphiques_formule.js` si une valeur calculée sert).
- Ces deux fichiers JS, et `pagesGraphiquesValidation.be`, doivent donc être présents sur **toute carte à
  historique**, et plus seulement sur les cartes qui ont une page dédiée. La liste `pages_graphiques` de
  `[berry_commun]` est scindée : la part nécessaire à `/graphiques` suit l'historique ; le reste (route
  `/pages`, gabarit HTML/CSS de la page dédiée, `pagesGraphiques.be`) garde la règle actuelle.
- `POST /graphiques` (mode édition sur la carte) valide un graphique `"moteur": "pages"` par
  `pagesGraphiquesValidation`, chargé seulement le temps de la validation.
- Mode édition de la carte : un graphique `"moteur": "pages"` se **déplace et se retire**, mais ses réglages ne
  s'éditent que dans l'atelier (le mode édition de la carte garde ses 4 styles). La tuile le dit.

### 4.3 Composition de la carte et du dépôt

La composition peut avoir été modifiée **sur la carte** (mode édition) depuis le dernier envoi. Avant d'écrire
vers « Graphiques », l'atelier lit la composition de la carte en ligne par `/ufsu?dir=0&download=/json/graphiques.json` (mesure du 2026-11-06 : `/json/graphiques.json` répond 404, la page n'est pas servie ainsi), après `path.exists` (`/ufsu` ne répond pas pour un fichier absent : composition vide) :
- identique à celle du dépôt → rien à signaler ;
- différente → l'atelier l'affiche en diff et propose « Partir de la version de la carte » (recopiée dans le dépôt
  avant d'y ajouter le graphique) ou « Garder celle du dépôt » (les changements faits sur la carte seront perdus à
  l'envoi, dit en toutes lettres) ;
- carte hors ligne → bandeau « composition de la carte non vérifiée ».

## 5. Bouton « Téléverser »

- Apparaît dans l'atelier après une écriture réussie dans le dépôt ; ouvre (nouvel onglet)
  `http://127.0.0.1:7700/?env=<env>&depuis=atelier&fichiers=<liste>` — liste des chemins **dans le FS de la carte**
  à envoyer, calculée par l'atelier d'après ce qu'il vient d'écrire :
  - toujours le fichier de description touché (`/json/pages_graphiques.json` ou `/json/graphiques.json`) ;
  - `autoexec.be` s'il a été modifié ;
  - à la première page dédiée ou au premier graphique « moteur pages » de la carte : les fichiers du moteur qui
    viennent d'entrer dans son FS (`.be`, gabarits, JS).
- La page Build, ouverte ainsi :
  - sélectionne l'env, bascule sur l'onglet « Fichiers » ;
  - affiche un **bandeau** : « Fichiers sélectionnés automatiquement par l'Atelier des graphiques, pour téléverser
    un graphique nouveau ou modifié. Vérifiez puis cliquez sur « Envoyer ». » ;
  - lance la construction du FS de cet env (comme le bouton actuel), puis, l'image prête, coche exactement les
    fichiers de la liste ; un fichier de la liste absent de l'image est signalé dans le bandeau, jamais ignoré en
    silence ;
  - coche « Redémarrer » si l'autoexec ou la liste des pages dédiées a changé (l'index des pages n'est lu qu'au
    démarrage) ; sinon non ;
  - **n'envoie rien** : l'utilisateur clique « Envoyer ».
- Refus et cas limites : build déjà en cours → la page Build l'affiche comme aujourd'hui, la sélection se fait quand
  l'image est prête ; page Build non démarrée → l'atelier le dit et propose de la lancer par l'annuaire ; paramètres
  d'URL hostiles (env inconnu, chemins hors FS, `..`) → ignorés avec un message, rien de coché.

## 6. Contraintes

- Règles du dépôt (CLAUDE.md) : jamais deux `pio` à la fois ; builds par la page Build ; fichiers ≤ 500 lignes sauf
  exceptions déjà listées (`build_page.py` en est une : tout ajout y est noté dans l'exception) ; charte des logs
  Berry ; `data/fs/*.be` modifiés avec l'accord de l'utilisateur (accordé pour ce chantier en tant qu'il porte
  `graphiquesFonctions.be` et le moteur des pages).
- Mêmes en-têtes anti-CSRF que les autres outils (`acces_web.py`).
- Place du FS mesurée sur les 6 cartes à historique après ajout des JS du moteur (blocs de 4 Ko, leçon du
  2026-11-02).
- Validation sur une vraie carte (journal web sans `_ERREUR`) avant de cocher : la cuve, et une carte dont
  `/graphiques` a déjà une composition (P4).

## 7. Décisions du rédacteur (relecture constructeur du 2026-11-04)

Choix faits sans l'utilisateur, à vérifier par lui :

1. **Construction lancée à l'ouverture du lien** (« lancera automatiquement », demande de l'utilisateur) : les
   paramètres d'URL ne font que préremplir ; c'est le JS de la page Build qui appelle `POST /lancer` (action
   `buildfs`) avec ses en-têtes habituels. Un lien ouvert par un tiers ne peut donc lancer qu'un `buildfs`, qui ne
   touche aucune carte : accepté. L'image est toujours reconstruite (pas de test « image à jour »). Build déjà en
   cours : refus affiché comme aujourd'hui, et la page relance d'elle-même quand le build se termine (même flux SSE
   `/flux` que la série), puis coche à la fin du `buildfs`.
2. **Fichiers du moteur à joindre** : ceux qui entrent dans le FS de l'env par cette écriture (exclusion levée dans
   le cenv), **plus**, si la carte est en ligne, ceux du moteur qu'elle n'a pas (`Br path.exists`, déjà en usage dans
   l'atelier pour la lecture de la carte). Carte hors ligne : seulement la première règle, et le bandeau le dit.
3. **Listes du cenv** : `pages_graphiques` est scindée une fois, à la main, en `pages_graphiques_moteur`
   (`pages_graphiques.js`, `pages_graphiques_formule.js`, `graphiques_moteur.js`, `pagesGraphiquesValidation.be`) et `pages_graphiques`
   (le reste). `pages_graphiques_moteur` est exclue des envs **sans historique et sans page dédiée** ;
   `pages_graphiques` garde sa règle. L'atelier gère les deux listes avec la même logique d'exclusion levée/remise
   (retirer la dernière page remet l'état exclu octet pour octet, comme aujourd'hui). `pagesGraphiquesValidation.be`
   reste un `.be` du FS compilé à la demande : RAM prise le temps d'un `POST /graphiques` seulement.
4. **Critère « Graphiques » proposé** : `diverses.historique.activation == "ON"` dans le persist du dépôt (la route
   `/graphiques` est déclarée par le driver de l'historique : une carte « grafana seul » n'a pas `/graphiques`).
5. **Tracé sous `/graphiques`** : `PagesGraphiques.optionDe(g, donnees, theme)` est appelé tel quel ;
   `graphiques.js` lui passe ses données lues sur `/histo` (et `?p=direct`) mises à la forme `{t, valeurs}` du
   moteur, et calcule les `calc:` par `PagesFormule` comme `pages_graphiques.js::page`. Le moteur n'appelle pas
   `/pages` dans ce cas. Non-régression : `banc_graphiques.py` (rendu Chrome compris) reste vert **sans changer ses
   attendus** pour les compositions existantes.
6. **Comparaison carte/dépôt (§4.3)** : sur le JSON relu et normalisé (clés triées), pas octet par octet.
   « Partir de la version de la carte » reprend ses graphiques tels quels, après validation par le validateur du
   dépôt ; un graphique invalide rend ce choix indisponible, avec le motif.
7. **Paramètre `fichiers`** : liste de chemins séparés par des virgules (une dizaine au plus, moins de 1 Ko) ; la page
   Build la valide contre l'image (`build_fichiers.py::liste`) ; chemin inconnu ou hostile → signalé, non coché.
8. **« Redémarrer » coché** si `autoexec.be` change, ou si l'index des pages dédiées change (ids, titres, accès,
   comparés avant/après écriture) ; pas pour un simple changement de réglage d'un graphique.
9. **Validation sur carte** : dernière action du plan, bloquante pour la clore ; preuves = journal web sans
   `_ERREUR`, capture de `/graphiques` (P4, composition existante intacte + un graphique atelier) et de la cuve.
10. **Place du FS** : seuil d'arrêt = moins de 10 % de blocs libres sur une des 6 cartes après ajout ; dans ce cas,
    s'arrêter et demander (compression `.gz` à décider avec l'utilisateur).

## 8. Laissé au constructeur

Découpage des fichiers, noms de fonctions, forme exacte du paramètre `fichiers` (dans la limite d'une URL
raisonnable), ordre des tâches, bancs (un banc par module, sondes Chrome comme les existantes).
