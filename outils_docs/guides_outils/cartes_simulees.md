# Cartes simulées

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Cartes simulées (page web)

Tuile « Cartes simulées » de l'annuaire (groupe Bus et cartes), page http://127.0.0.1:7940 ; tâche VS Code « Outil : cartes simulees » ou cible Custom détachée. Elle simule hors ligne une carte du parc : « Lancer » démarre un serveur local sur `127.0.0.1`, au port web de la vraie carte (8082 pour le rideau du garage, 8080 + id − 1 derrière un maître), « Ouvrir » affiche sa page d'accueil, « Arrêter » la coupe.

Le rideau rejoue ses vrais modules Berry (`controleRideau.be`) par `berry.exe` sur les bouchons de `scripts_python/berry/bouchons_berry/` et lit sa position chez le P4 par un seul `GET /cm?cmnd=Status 10` (lecture seule). Les autres cartes simulables (15 au 2026-11-23, sur 16 : les cartes du cenv dont le dossier a un `_persist.json`) n'ont que leur identité réseau et un accueil générique. Nom d'hôte, passerelle, masque, DNS, MQTT et port viennent du `_persist.json`.

Limites : une carte qui répond sur le réseau n'est jamais simulée (refus 409), le P4 du garage (maître) en fait partie ; MQTT n'est jamais connecté (un second client du même nom ferait tomber la vraie carte) ; pas d'alias d'IP ; les pages natives du C++ (Configuration, Console) sont en 404. Rien n'est écrit dans le dépôt. Pour que « Arrêter » apparaisse dans l'annuaire, lancer l'outil depuis sa tuile ou la cible Custom, pas à la main. Bancs : `test_cartes_simulees.py`, `test_cartes_simulees_web.py`, sonde `test_cartes_simulees_page_chrome.py`, `build/test_cible_cartes_simulees.py`.

### Lancer sans l'annuaire, scénario, bancs

- Page : `python outils_docs/scripts_python/outils_pc/cartes_simulees_web.py [--http 7940] [--local] [--sans-navigateur]` ; cible Custom détachée `cartes_simulees` (`build/cible_cartes_simulees.py`, `pio run -e <env> -t cartes_simulees`, port par `custom_cartes_simulees_http`, jamais pendant un build).
- Une seule carte, sans page : `python outils_docs/scripts_python/outils_pc/cartes_simulees.py <env> [--port N]` ; `--liste` donne les cartes simulables et dit lesquelles rejouent leurs modules Berry.
- Panneau de scénario du rideau : `/__sim` sur la carte simulée (position du P4 simulée ou lue sur le vrai P4, P4 muet, curseur, fins de course ; préréglages `ouvert`, `ferme`, `maitre_muet`, `incoherent`). Moteur : `berry/simule_carte_rideau.be` (lancé par `berry.exe`).
- Une carte de plus à rejouer : une entrée de `MODULES_BERRY` dans `outils_pc/cartes_simulees.py`, avec son script et ses routes.
