# Écran de la cave

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## L'écran de la cave (écran 7B esclave du serveur de la cave)

L'écran tactile Waveshare ESP32-S3-Touch-LCD-7B de la cave (env `tasmota32s3-cave-ecran`) montre l'état de la cave
et commande ses appareils. Il est l'**esclave** du serveur relais de la cave (`tasmota32s3-cave-serveur-rly`) :
les **touches** partent par ModBus (RS485 16/15 et push UDP par le point d'accès de la cave), l'**affichage** arrive
par MQTT. Plan `tasks/plans/ecran-cave-vues-commandes.md`, spec
`docs/superpowers/specs/2026-11-12-ecran-cave-vues-commandes-design.md`.

### Les pages

| Page | Ce qu'elle montre |
|---|---|
| Accueil | À gauche les capteurs : température, humidité, cuve (taux et volume), niveau du vide-cave. À droite les appareils, une tuile par touche avec son icône : lumières, lave-linge, pompe de la cuve, pompe du vide-cave, et la ventilation, dont l'icône tourne quand elle marche |
| Graphiques | Température et humidité des 30 dernières minutes |
| Cuve | Jauge de la cuve, flotteurs haut et bas du vide-cave, pompe du vide-cave (« Forcer la marche » / « Arrêter la marche ») |
| Réglages | Mise en veille, extinction, luminosité, par des boutons − et + |

Le bouton ☰ ouvre le menu : « Redémarrer le serveur » demande une confirmation avant d'agir. Une alerte (pannes des
flotteurs, marche forcée) s'affiche dans un bandeau rouge au-dessus de la navigation.

### Ce que fait une touche

| Touche | Appareil | Relais du serveur |
|---|---|---|
| 1 | Lumières | 3 |
| 2 | Lave-linge (relais « Lavage ») | 5 |
| 3 | Pompe de la cuve | 4 |
| 4 | Pompe du vide-cave, marche manuelle | 1 |
| 5 | Redémarrer le serveur (menu) | `Restart 1` |

- Une touche envoie l'**état voulu** (l'inverse de l'état affiché), jamais une bascule : un appui répété ou relancé
  ne fait pas clignoter le relais.
- **Valeur grisée = touche refusée** : tant que l'état de l'appareil n'est pas à jour, l'écran refuse l'appui et
  l'écrit dans la barre du haut (« touche refusée : état inconnu »).
- L'écran relance l'ordre toutes les 2 s, 5 fois au plus, jusqu'à ce que l'état reçu par MQTT confirme le relais.
  La touche 5 n'est **jamais** relancée : le serveur oublie ses ordres en redémarrant, une relance le ferait
  redémarrer en boucle.
- Pompe du vide-cave : un appui la force en marche et met les flotteurs en pause ; un second appui l'arrête, la
  minuterie de 120 s aussi ; les flotteurs reprennent à l'arrêt. Le forçage est permis même flotteurs « à sec ».

### Ce qui est grisé, et pourquoi

Chaque valeur garde l'heure de sa réception ; au-delà de 15 min sans message (`modules.ecranCave.peremption`,
900 s par source), elle est grisée. Sans broker MQTT, tout est grisé et l'horloge de la barre du haut est barrée.

### Pannes des flotteurs (serveur de la cave)

Le serveur publie une alerte (topic d'alerte de la pompe, effacée par `AcquittePompe`) quand :
- le flotteur haut est fermé alors que le bas est ouvert, pendant plus de `pompeVideCave.pannes.antiRebond` s ;
- la minuterie arrête la pompe `pompeVideCave.pannes.maxArretsMinuterie` fois de suite alors que le flotteur bas
  reste fermé (flotteur bas probablement bloqué).

### Mettre l'écran en service

1. Compiler et flasher `tasmota32s3-cave-ecran` par la page Build (le FS part avec le firmware).
2. Sur le **serveur de la cave** (S3, `tasmota32s3-serveur-rly`), vérifier que `drivers.ModBus.environnement.TasmotaSlaveModBus.TasmotaSlaveModBus1.activation`
   (l'esclave « ECRAN-CAVE ») et `modules.ecranCave.activation` sont à `ON` : c'est déjà le cas dans le `_persist.json` du dépôt,
   mais la carte garde son persist à elle tant qu'on ne l'a pas remplacé. À `OFF`, le serveur ne relève pas l'écran et
   n'exécute aucune touche (un esclave actif sans carte ferait tomber le relevé en timeout).
3. Vérifier sur l'écran : valeurs non grisées, une touche allume son relais, la tuile passe au bleu.

Fichiers : `data/cave/tasmota32s3-ecran/` (`ecranCaveFonctions.be` : modèle MQTT et touches ; `controleEcranCave.be` :
abonnements, veille, rafraîchissement ; `ecranCaveHaspmota.be` + `pages.jsonl` : interface HASPmota),
`data/cave/tasmota32s3-serveur-rly/controleCommandesEcran.be` (exécution des touches) et `controlePompeVideCave.be`
(pannes des flotteurs, état publié). La maquette se modifie dans l'atelier des écrans (page 7960), description
`outils_docs/atelier_ecrans/cartes/tasmota32s3-cave-ecran/ecran.json`. Icônes : glyphes Material Design du firmware
(`outils_docs/ICONES_IMAGES_SOURCES.md`). Bancs : `berry/banc_ecran_cave.py`, `banc_commandes_ecran.py`,
`banc_pompe_cave.py`.
