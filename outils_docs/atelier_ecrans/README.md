# Atelier des écrans : maquettes (2026-11-12)

Outil PC (tuile de l'annuaire, page 7960) : modifier la disposition d'un écran tactile de carte, y épingler des
remarques, puis générer de la même description le `pages.jsonl` de HASPmota et le code LVGL pur en Berry. Plan
`tasks/plans/atelier-ecrans.md`, action A1.

**Choix de l'utilisateur (2026-11-12) : A, avec le fil de remarques de C, le zoom 100 % de B, la fenêtre basse de C
(fichier généré en onglets : `pages.jsonl`, `ecranLvgl.be`, `ecran.json`, différences colorées) et le tableau de D en
onglet à côté de l'écran.** Un bouton « Traiter les remarques (Claude) » près du fil lance le traitement des remarques
de l'écran affiché : Claude écrit ses propositions dans le fichier des remarques, la page les affiche avec Appliquer /
Refuser. Maquette : `modele-retenu.png`, `modele-retenu-sombre.png` (`?m=R`).

## Décisions de l'utilisateur (2026-11-12)

1. Bouton « Traiter les remarques (Claude) » : la page lance une session Claude en arrière-plan (`claude -p`), qui lit
   le dépôt, la skill `lvgl-haspmota` et le catalogue, et n'écrit QUE dans le fichier des remarques de l'écran affiché.
   Seul « Appliquer » modifie la description. Un seul traitement à la fois, état « en cours » affiché.
2. En-tête : l'env se choisit dans une liste déroulante (classée par lieu, comme les autres pages), on peut en changer
   sur la page. Le type d'écran se met à jour d'après celui paramétré dans l'env choisi : une seconde liste déroulante
   donne tous les écrans connus des envs personnels, présélectionnée sur celui de l'env.
3. Choisir un autre écran que celui de l'env permet aussi de CHANGER l'écran déclaré par l'env (pas seulement un
   aperçu). Aujourd'hui l'écran d'un env tient surtout dans le `display.ini` de son dossier (ligne `:H` : pilote,
   résolution, bus, broches) ; la base de l'env (LVGL, tactile) et les broches du persist peuvent aussi être touchées.
   Passage par diff et confirmation ; firmware à recompiler par la page Build.
4. Disposition existante quand l'écran change : mise à l'échelle PROPOSÉE (positions et tailles au rapport des
   résolutions, police ramenée à la taille compilée la plus proche), objets trop petits pour le doigt (< 40 px environ)
   et textes qui débordent signalés ; résultat vu sur le canevas et dans le diff avant écriture, corrigé à la main ou
   par une remarque.

- Images : `modele-A.png` à `modele-D.png` (1440 × 900), `modele-A-sombre.png` (même page en mode sombre).
- Code : `maquettes_atelier_ecrans.html?m=A|B|C|D`, `&theme=sombre` pour le mode sombre ; le bouton « Sombre / Clair »
  de l'en-tête bascule la page (demande de l'utilisateur du 2026-11-12, valable pour tous les modèles).
- Écran dessiné : page « Débits » de `tasmota32s3-ecran-debits-pac` (Waveshare 7B, 1024 × 600), coordonnées reprises de
  son `pages.jsonl`. Le bouton « Purge » est un objet en cours d'ajout ; les pastilles numérotées sont des remarques
  (orange : ouverte, vert : traitée) ; le cadre pointillé orange est une remarque sur une zone.

| | Disposition | Pour qui, pour quoi |
|---|---|---|
| A | Trois colonnes : pages, objets et palette à gauche ; écran à 80 % au centre ; propriétés, liaison et remarques en onglets à droite | Éditeur classique, tout visible d'un coup |
| B | Écran à taille réelle (100 %), barre d'outils en haut, vignettes des pages dessous, propriétés et remarques à droite | Juger la lisibilité réelle (taille des textes, cibles tactiles) |
| C | Remarques d'abord : écran à 72 %, fil des remarques à droite (proposition de Claude, Appliquer / Refuser), différences du fichier généré sous l'écran ; l'édition passe par « Mode édition » | Relire et annoter, laisser Claude faire les modifications |
| D | Écran à 60 % et propriétés en haut, tableau de tous les objets de la page dessous, modifiable case par case | Réglages au pixel près, vue d'ensemble des liaisons |
