# Atelier des graphiques — page « Énergie » du différentiel (palier 4)

Date : 2026-11-08. Remplace l'action A13 du plan `tasks/plans/atelier-graphiques.md` (« palier 4 : ESP32 classiques »).
Spec mère : `docs/superpowers/specs/2026-11-03-atelier-graphiques-design.md` (§4.1 adaptateurs en flash, §5 point 4,
§7.1). Page actuelle : `docs/superpowers/specs/2026-10-31-page-energie-differentiel-design.md`.

## 1. Intention

L'utilisateur veut que l'Atelier des graphiques (outil PC, port 7950) sache **reprendre et modifier la page `/energie`
existante du différentiel**, comme il le fait pour les pages dédiées du P4 et de la cuve : ajouter un élément, en
changer la couleur ou le type, changer l'échelle de temps, déplacer les éléments et changer leur taille, puis « Écrire
dans le dépôt » et « Téléverser ». C'est la même page (même adresse, même bouton d'accueil « Énergie »), pas une
seconde page à côté.

Le différentiel (env `tasmota32-bureau-interrupteur-energie`, dossier `data/bureau/tasmota32-interrupteur-energie`)
est un ESP32 classique **sans PSRAM** : FS de 320 Ko dont **52 Ko libres** (mesure du 2026-11-02,
`tasks/plans/energie-differentiel.md`), tas d'environ **52 Ko** (`Status 4`), ni ECharts, ni module d'historique.
Le moteur des pages du P4 (`pagesGraphiques.be` 17 Ko + `pagesGraphiquesValidation.be` 20 Ko + 42 Ko de JS + ECharts)
n'y tient pas : ce chantier fait un **moteur léger propre à `/energie`**, dans l'esprit de l'actuel `energie.js`
(107 lignes, SVG sans bibliothèque).

## 2. Buts, non-buts, anti-buts

**Buts**
- Tout ce que montre `/energie` devient un **élément** décrit dans un fichier, que l'atelier lit, modifie et écrit.
- Deux sortes d'éléments :
  - **valeur** : une grandeur affichée en chiffre seul, en **cadran** ou en **demi-cercle** ; source = une valeur
    instantanée du bloc ENERGY (`Power`, `Current`, `Factor`, `Frequency`, `Voltage`, `ApparentPower`,
    `ReactivePower`, `Today`, `Yesterday`, `Total`) ou un total tiré des données en flash (kWh ou euros du jour, du mois,
    de l'année) ;
  - **graphique** : une série en flash, en **barres, courbe, aire ou escalier**, avec une **échelle de temps** :
    - **minutes** : courbe de puissance sur 24 h (288 points au pas de 5 min, en W) ;
    - **heure** : les 24 heures d'aujourd'hui ;
    - **jour** : les jours d'un mois, celui en cours **ou un mois archivé** (choisi dans l'atelier) ;
    - **mois** : jusqu'à 24 mois ;
    - **an** : somme des mois par année (2 ans au plus).
    Heure, jour, mois et an s'affichent au choix en **kWh ou en euros**.
- Pour chaque élément : titre, couleur, **largeur** (demi ou pleine), **hauteur** (petite, moyenne ou grande ; décision
  de l'utilisateur : trois tailles au choix, pas de pixels), place dans la page (ordre, déplacé dans la grille de
  l'atelier).
- L'atelier propose le différentiel, une destination « Énergie (/energie) », les seules séries et les seuls styles
  possibles sur cette carte, un aperçu tracé par **le même fichier de rendu que la carte**, puis l'écriture et le
  bouton « Téléverser » existants.

**Non-buts**
- Aucun changement du **stockage** : profondeurs actuelles gardées (heures du jour seulement, 24 mois) — décision de
  l'utilisateur, « ces profondeurs me suffisent ».
- Pas de graphique d'une valeur instantanée dans le temps (aucun historique sur un ESP32 classique, leçon du
  2026-10-13) : une valeur instantanée ne donne qu'un chiffre, un cadran ou un demi-cercle.
- Pas d'ECharts, pas de liquide ni de radar, pas de formules calculées sur cette carte.
- Les autres ESP32 classiques (`tasmota32-serveur-rly`, `tasmota32-vr-porte`) : hors périmètre, aucun besoin exprimé.
- La sous-page « Tarifs » (`f=tarifs`, POST `/energie`) ne change pas ; le lien vers elle reste en bas de `/energie`.

**Anti-buts** (ce qui serait un échec même si « ça marche »)
- Toucher au **comptage** : `energieFonctions` (notes, bascule, purge, prix, fichiers `etat.json`, `mois-*.json`,
  `courbe.bin`) ne change pas, en dehors des deux routes de lecture du §4.2.
- Une description absente, illisible ou refusée qui **prive l'utilisateur de la page** : la page retombe alors sur la
  disposition d'aujourd'hui (4 valeurs puis 4 graphiques), avec une ligne qui dit pourquoi.
- Faire tomber le tas ou remplir le FS : aucune lecture de la description par Berry (elle est seulement relayée en
  flux vers le navigateur), budget FS mesuré sur la carte avant de déclarer la cible tenable.

## 3. Contraintes

- Fichiers sous 500 lignes (`CLAUDE.md`) ; `atelier_graphiques_page_js.py` est à 473 lignes : le code de la
  destination Énergie va dans un module neuf.
- `energieFonctions.be` et `controleEnergie.be` sont **solidifiés** sur le différentiel (`custom_berry_solidify`) :
  les routes du §4.2 demandent une **recompilation du firmware** et un envoi par la page Build (l'utilisateur lance la
  compilation ; aucune compilation lancée par l'atelier ni par Claude hors de la page Build). Pièges de solidification
  de `outils_docs/SOLIDIFICATION_BERRY.md` (aucun état dans la table du module, `import` de soi-même).
- Charte des logs Berry du `CLAUDE.md` (cible du module énergie, `_ERREUR` dans les `except`).
- FS : la description et le JS de rendu doivent tenir largement dans les 52 Ko libres ; borne de la description :
  **4 096 octets** (à confirmer par la mesure, §6).
- Sur cette carte, pas de gros fichier lu en entier ni de socket ouverte par `Br` (leçon du 2026-11-02) : la
  description et les archives sont **relayées par morceaux** (`webserver.content_send`), jamais chargées en entier.
- L'atelier n'écrit rien sur la carte : écriture dans le dépôt, puis « Téléverser » vers la page Build, qui attend le
  clic « Envoyer » (parcours de `tasks/plans/atelier-destinations.md`).

## 4. Ce qui est décidé

### 4.1 La description `energie_page.json`

Fichier `data/bureau/tasmota32-interrupteur-energie/energie_page.json`, posé dans `/json/` sur la carte comme les
autres `.json` du dossier de la carte. Forme :

```json
{"version": 1,
 "elements": [
   {"type": "valeur", "titre": "Puissance", "source": {"direct": "Power"}, "unite": "W",
    "couleur": "#4a9eda", "largeur": "demi", "hauteur": "petite"},
   {"type": "barres", "titre": "Aujourd'hui par heure", "source": {"flash": "heure", "grandeur": "kWh"},
    "couleur": "#4a9eda", "largeur": "pleine", "hauteur": "moyenne"}
 ]}
```

- `type` : `valeur`, `cadran`, `demi-cercle`, `barres`, `courbe`, `aire`, `escalier`. Les trois premiers prennent une
  source `direct` ou un total en flash (`{"total": "jour|mois|an", "grandeur": "kWh|euros"}`) ; cadran et demi-cercle
  ont `min` et `max`. Les quatre derniers prennent une source `{"flash": "minutes|heure|jour|mois|an", "grandeur":
  "kWh|euros"}` (`minutes` = puissance en W, sans `grandeur`). `jour` désigne son mois **au choix** (décision de
  l'utilisateur du 2026-11-08 : « pouvoir choisir l'un ou l'autre ») : `"mois": "AAAA-MM"` (mois fixe) ou
  `"decalage": 0..23` (relatif : 0 = mois en cours, 1 = mois précédent…) ; ni l'un ni l'autre = mois en cours. Un mois
  dont l'archive a été purgée s'affiche « archive effacée » (le graphique reste, vide), jamais une erreur.
  `mois` accepte `"nombre": 1..24` (défaut 12). `an` = **année civile**, somme des mois de `etat.a` ; l'année la plus
  ancienne, partielle, est marquée comme telle.
- Option `"total": true` sur heure, jour, mois et an : le titre porte le total de la période en kWh **et** en euros,
  comme aujourd'hui (`e_totalH`, `e_totalD`, `e_totalA`).
- L'ordre de la liste est l'ordre d'affichage (grille à deux colonnes : `demi` occupe une colonne, `pleine` les deux).
- Bornes : 16 éléments, 4 096 octets ; couleur `#rrggbb` ; titres de 40 caractères au plus.
- La **description par défaut** reproduit la page d'aujourd'hui : 4 valeurs (puissance, courant, facteur en cadran,
  fréquence) puis 4 graphiques (heure, jour du mois en cours, 12 mois, minutes). Elle est à la fois le repli de
  `energie.js` et le point de départ de l'atelier quand la carte n'a pas de description.

### 4.2 Côté carte

- `energie.js` devient un **rendu piloté par la description** : il lit `/energie?f=description`, valide à sa façon
  (tolérant : un élément inconnu ou mal formé est ignoré avec une ligne « élément n ignoré : motif »), puis trace
  chaque élément en SVG. Description absente, JSON illisible ou trop gros : disposition par défaut, et une ligne le dit.
  Cadences d'aujourd'hui gardées : `f=direct` toutes les 10 s, `f=donnees` toutes les 300 s.
- `energie.html` devient un gabarit vide (une zone pour la grille, le bas de page avec le lien « Tarifs ») ;
  `energie.css` porte la grille et les trois hauteurs.
- `f=direct` est **élargi** aux autres champs du bloc ENERGY du JSON SENSOR (`Voltage`, `ApparentPower`,
  `ReactivePower`, `Today`, `Yesterday`, `Total`), sous leur nom Tasmota ; les clés actuelles `p`, `i`, `f`, `hz`
  restent. Champ absent du bloc : absent de la réponse.
- Deux routes de **lecture** ajoutées à `energieFonctions.route` (rien d'autre ne change dans le module) :
  - `f=description` : relaie `/json/energie_page.json` par morceaux (`404` s'il est absent, refus au-delà de la borne
    sans le lire) ;
  - `f=mois&m=AAAA-MM` : relaie `mois-AAAA-MM.json` (jours d'un mois clos), `404` si absent ; `m` validé (format strict,
    pas de chemin).
  Ces routes ne sont lues que par le navigateur ; Berry ne parse jamais ces fichiers.
- Le même fichier de rendu sert l'aperçu de l'atelier (§4.3) : il ne dépend que de `fetch` d'URL relatives et du DOM,
  pas de Tasmota.

### 4.3 Côté atelier

- Le différentiel apparaît dans la liste des cartes : sont acceptés, en plus des S3/P4, les envs dont le FS embarque
  `page_energie` (non exclue du cenv).
- Pour une telle carte, le menu « Page » propose **« Énergie (/energie) »** (nouvelle destination `energie`). Les
  autres destinations n'y sont pas proposées pour un ESP32 classique.
- Séries proposées : le catalogue fixe du §4.1 (sources `flash` et `total`), plus les champs `direct` présents dans le
  bloc ENERGY lu par `Status 10` quand la carte répond (sinon la liste du §2).
- Styles proposés : ceux du §4.1 seulement, avec le conseil de style existant restreint à cette liste.
- Grille : celle des pages dédiées (déplacer, largeur demi/pleine), plus un réglage **hauteur petite/moyenne/grande**.
- Aperçu : `energie.js` servi par l'atelier (ajout à la liste fermée `/moteur/`), données lues sur la carte en ligne
  (`/energie?f=donnees|direct|mois`, par l'adresse de l'env) ; carte hors ligne : valeurs simulées, comme pour les
  autres cartes.
- Écriture : `energie_page.json` seulement (validé côté Python avant écriture, mêmes cas que le rendu), avec diff et
  empreinte comme aujourd'hui ; ni autoexec ni cenv à modifier (la page existe déjà sur la carte).
- « Téléverser » liste `energie_page.json` **et toujours** `energie.js`, `energie.html`, `energie.css` (≈ 10 Ko : on
  ne lit pas ces fichiers sur la carte pour comparer, leçon du 2026-11-02).
- **Firmware d'avant ce chantier** : il répond à `f=description` par la page HTML entière en 200 (branche `else` de
  `energieFonctions_route`). L'atelier le détecte (réponse qui n'est ni du JSON ni un 404) et **bloque** « Téléverser »
  avec « compilez et envoyez le firmware du différentiel par la page Build », comme `firmware_requis` pour `/graphiques`.
  Ordre de mise en service : firmware d'abord, puis FS.
- Choix du mois d'un graphique « jour » dans l'atelier : « mois en cours », « mois précédent » (et décalages suivants),
  ou un mois fixe pris dans `etat.a` ; un mois fixe sans archive sur la carte (`f=mois` en 404) est signalé dans
  l'atelier avant l'écriture.
- Reprise : à l'ouverture, l'atelier lit la description de la carte (`f=description`) si elle diffère du dépôt, avec le
  choix « carte / dépôt » déjà connu pour `/graphiques` ; sans description nulle part, il part de la description par
  défaut.

### 4.4 Mesures avant de déclarer la carte capable

Sur le vrai différentiel, après envoi : tas libre (`Status 4`) page fermée puis page ouverte, place FS libre
(`UfsFree`), et le journal web sans `_ERREUR`. Seuil : la page ne doit pas faire baisser le tas de façon durable, et il
doit rester au moins **16 Ko** libres sur le FS (`energieFonctions.SEUIL_KO`, en dessous l'énergie n'écrit plus).

## 5. Laissé au constructeur

- Le découpage exact des fichiers (module de description Python, module JS de la destination dans l'atelier, bancs).
- Le dessin précis des styles SVG (graduations, étiquettes, info-bulles), dans l'esprit de `energie.js` et des
  jauges D à H de `outils_docs/jauges/`.
- La forme de la validation commune Python / JS (cas partagés dans un fichier JSON, comme `cas_description.json` du
  palier 1).
- Les valeurs exactes des trois hauteurs (en pixels) et de la grille sur téléphone (une colonne).

## 6. Choix de Claude (à contrôler par l'utilisateur)

1. Fichier de description **séparé** (`energie_page.json`) plutôt qu'une page de `pages_graphiques.json` : la page
   `/energie` n'utilise pas le moteur `pagesGraphiques` (trop lourd pour la carte), et son schéma diffère (sources en
   flash, hauteurs nommées).
2. **Pas de validation côté Berry** : la carte relaie le fichier sans le lire (tas) ; la validation est faite par
   l'atelier avant écriture et par `energie.js` à l'affichage, avec repli sur la page d'aujourd'hui.
3. Les deux routes de lecture dans `energieFonctions` (module solidifié) plutôt qu'un nouveau module chargé du FS :
   un module de plus coûterait du tas sur une carte à 52 Ko. Conséquence : un firmware à recompiler et envoyer.
4. Cible de mesure FS : 16 Ko libres au moins, le seuil sous lequel `energieFonctions` cesse d'écrire.
5. `f=direct` élargi (troisième retouche du module solidifié, lecture seule) plutôt que lire `Status 10` toutes les
   10 s depuis le navigateur (réponse bien plus lourde pour la carte).
6. Option `"total"` dans le schéma v1, pour que la description par défaut reproduise exactement la page d'aujourd'hui.
7. `energie.js`, `.html`, `.css` toujours joints au téléversement (pas de comparaison de version sur la carte) ; ancien
   firmware détecté et bloquant.
8. « An » = année civile.
