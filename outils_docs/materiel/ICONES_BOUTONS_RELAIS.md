# Remplacer un bouton de relais de la page web par une icône (rapport du 2026-11-15)

Étude de lecture du code, rien n'a été essayé sur carte. Question posée : remplacer le bouton d'un relais sur la page
d'accueil par une icône (dans le bouton ou seule), liée à l'organe commandé, dont l'apparence suit l'appui ou l'état.

Réponse courte : c'est faisable sans recompiler le firmware, par plusieurs voies. Le visuel d'accueil du dépôt couvre déjà
l'affichage de l'état ; il lui manque le clic.

## Comment fonctionne le bouton d'origine

- `tasmota/tasmota_xdrv_driver/xdrv_01_9_webserver.ino::HTTP_DEVICE_CONTROL` génère
  `<button id='o<n>' onclick='la("&o=<n>")'>texte</button>`. Le texte vient de `WebButton<n>`.
- Ce texte passe par `HtmlEscape` (dans `HandleRoot`) : pas de balise HTML ni de SVG. Un caractère Unicode ou un émoji passe.
- L'état est reporté à chaque rafraîchissement (`HandleRootStatusRefresh`) par
  `eb('o<n>').style.background='var(--c_btn)'` ou `var(--c_btnoff)`. Seule la couleur de fond change. Le bouton garde son id.
- Changer ce C++ impose une recompilation et des conflits à chaque synchro du fork.
- Les boutons de volets (flèches ▲ ▼) sont codés en dur dans le C++ : la voie A ne leur sert pas.

## Les voies possibles

### A. Un caractère Unicode dans `WebButton<n>`

- `WebButton1 💡`, `WebButton2 🔒`. La couleur du fond suit déjà l'état.
- Aucun code. Limites : le glyphe dépend de la police de l'appareil, un seul glyphe par bouton, pas d'icône vectorielle.
- Pour changer de glyphe selon l'état : une règle Berry réécrit `WebButton<n>` à chaque changement de `POWER`
  (visible après rechargement de la page seulement, le texte du bouton n'est pas rafraîchi).

### B. Un script Berry qui remplace le contenu du bouton natif par un SVG

- Le callback `web_add_main_button()` d'un driver est appelé à l'affichage de la page ; il envoie un `<script>` par
  `webserver.content_send` (déjà fait dans `data/fs/controleWeb.be::web_add_main_button`).
- Le script retrouve `#o<n>`, y met un SVG inline, et un `MutationObserver` (ou un `setInterval`) lit la couleur de fond
  (`--c_btn` ou `--c_btnoff`) pour basculer l'icône. Le clic reste le `onclick` d'origine.
- Sans recompilation, icône vectorielle, plusieurs états, animation CSS possible.
- Limites : le script ne s'exécute qu'au chargement ; le bouton d'origine doit rester dans le DOM ; dépend de la structure
  du HTML de l'amont. Ne pas passer par `web_sensor` : sa zone est remplacée toutes les ~2 s et n'exécute aucun script.

### C. Une icône posée sur le dessin de l'organe (visuel d'accueil, déjà en place)

- `data/fs/visuelFonctions.be` et `data/sd/js/visuel.js` : un fond (photo ou dessin) avec des points chauds `voyant`,
  `valeur`, `liaison`. Un `voyant` a trois états (`icone_on`, `icone_off`, `icone_inconnu`, chemins SVG) et lit l'état d'un
  relais (`source.type = "relais"`). Rafraîchi par `/visuel?f=etat` toutes les ~2,3 s. Placé depuis l'atelier des visuels (7985).
- Manque : `visuel.js` ne gère aucun clic. `data/sd/js/volets.js` sait déjà commander par clic avec confirmation
  (`outils_docs/visuels_accueil/CONSIGNES_VISUELS.md` § 5). Il faudrait un clic sur un `voyant` qui appelle
  `/cm?cmnd=Power<n> toggle`, avec confirmation si l'organe est dangereux.
- C'est la voie la plus proche de « icône seule en lien avec l'organe commandé ».

### D. Un bouton généré entièrement par un module Berry

- Le module émet son `<button>` avec un SVG ; le clic appelle `/cm?cmnd=Power<n> toggle` par `fetch`, un `fetch` périodique
  lit `Status 11` pour l'état ; les boutons natifs sont masqués par CSS.
- Contrôle total, mais on réimplémente rafraîchissement et authentification : plus de code et de RAM.

### E. Modifier le C++ (`HTTP_DEVICE_CONTROL`)

- Résultat le plus propre, mais dette de synchro avec l'amont. Non recommandé.

## Comparatif

| Voie | Recompilation | Icône vectorielle | Change selon l'état | Clic | Effort |
|---|---|---|---|---|---|
| A (Unicode) | non | non | couleur, ou glyphe via règle | natif | très faible |
| B (script sur le bouton natif) | non | oui | oui, lu sur la couleur | natif | moyen |
| C (visuel d'accueil) | non | oui | oui, 3 états | à ajouter | faible à moyen |
| D (bouton Berry complet) | non | oui | oui | à écrire | élevé |
| E (C++) | oui | oui | oui | natif | élevé, dette de synchro |

## Recommandation

- Icône sur le dessin d'une pièce ou d'un organe (garage, portail, lampe) : voie C, en ajoutant le clic à `visuel.js`.
- Remplacer seulement les boutons de la liste de l'accueil : voie B, avec une description par relais (une icône par état).
- Essai rapide : voie A.

Les voies B et D passent par un module Berry de `data/fs` : accord de l'utilisateur requis avant d'y toucher.

## Non vérifié

- Rien n'a été essayé sur carte. Le comportement d'un `MutationObserver` sur `#o<n>` et la persistance du script après un
  rafraîchissement sont déduits de la lecture du code.
- Liste complète des fonctions `webserver.*` du build non relue (`lib/libesp32/berry_tasmota/src/be_webserver_lib.c`).
