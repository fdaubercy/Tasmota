# Fin de build : affichage de l'occupation des partitions (maquettes)

Étude du 2026-11-15 pour l'onglet « Build et téléversement ». **Rien n'est réalisé** : choisir une variante avant la mise en place.

- `maquettes_fin_build.html` : les 4 variantes, interactives pour le thème (bouton Thème, sombre/clair), un seul fichier sans dépendance. Chaque variante montre une série de 3 envs et des alertes (orange dès 90 %, rouge dès 95 %).
- `variante-A.png` à `variante-D.png` : une capture par variante (Chrome headless, thème sombre).
- Données : le P4 du garage est un **relevé réel** (`%LOCALAPPDATA%\outils_tasmota\build\memoire\tasmota32p4-garage-serveur-modbus.json`, build du 2026-11-14 : app0 90,1 %, safeboot 94,3 %). La cuve et le S3 de la cave sont **plausibles** (aucun relevé lu). La colonne « vs précédent » est **plausible** : l'analyse enregistrée ne garde que le dernier build.

| Variante | Avantages | Inconvénients | Effort | Côté serveur |
|---|---|---|---|---|
| A. Fenêtre modale à la fin du lancement | Impossible à manquer, détail complet (ruban + tableau + RAM), onglets pour la série | Bloque la page, une modale par série (pas par env), gênante si on relance vite | Moyen | Un événement « série terminée » (ou fin d'env) ; `GET /memoire?env=` pour chaque env |
| B. Panneau repliable sous l'env | Aucune fenêtre, tout visible d'un coup dans la série, pastille d'alerte dans la ligne | Allonge la page avec plusieurs envs, panneaux à refermer | Faible à moyen | `GET /memoire?env=` suffit, appelé quand l'env passe à « réussi » (la page connaît déjà l'état par env) |
| C. Tiroir latéral | Jauges lisibles, alerte colorée, écart en Ko avec le build précédent, navigation env par env | Le plus de code (SVG des jauges), recouvre la droite de la page | Moyen à fort | `GET /memoire` + **conserver le build précédent** (nouveau champ `avant` enregistré par `build_memoire.enregistre`) |
| D. Pastille dans la ligne + détail au clic | Le plus économe en écran pour plusieurs envs, rien d'imposé, détail à la demande | Détail seulement si on clique, alerte moins voyante (pastille orange/rouge seulement) | Faible | `GET /memoire?env=` ou `build_memoire.resume` (app0, FS, DIRAM déjà fournis) ; pas de nouvel événement |

## Contraintes de mise en place

- `build_page.py` dépasse déjà 500 lignes (exception déclarée au CLAUDE.md) : le code irait dans un module neuf `build_page_fin_memoire.py` (CSS, HTML, JS insérés comme `build_page_memoire.py`), et on réutilise le rendu et les seuils de l'onglet Mémoire (barres orange 85 %, rouge 95 % là-bas ; ici 90 / 95 % à harmoniser).
- Thème : variables CSS de la page (`--piste`, `--vert`, `--orange`, `--rouge`, `--carte`, `--bord`), sombre et clair vérifiés.
- Tout texte venu du serveur (noms d'env, de partition, messages) passe par `textContent` ou un échappement, comme dans `build_page_memoire.py`.
- Pas de `pio run` : l'analyse relit le dernier journal (`build_memoire.analyse`). Le FS est estimé, à afficher comme tel. nvs et otadata n'ont pas de mesure (« non mesurable »).
- Constat du relevé réel : la partition `safeboot` du P4 est à 94,3 % et app0 à 90,1 %, donc l'alerte se déclencherait déjà.
- Un événement de fin d'env n'existe pas côté page : A en demande un pour la série, B et D se calent sur le passage de l'env à « réussi ».
