---
chantier: plan-maison
titre: Plan de la maison, liens, rôles maître/esclave et vue réseau
statut: actif
cree: 2026-11-15
maj: 2026-11-15
source: tingly-popping-harbor.md
objectif: Document visuel qui place chaque carte Tasmota dans sa pièce et montre qui parle à qui, par quel moyen et qui commande
famille: modbus-reseau
liens: debits-deux-cartes, cartes-simulees
---
# Plan de la maison, liens, rôles maître/esclave et vue réseau

## Contexte
Première version (vue A) livrée le 2026-11-15 : `outils_docs/plan_maison/genere_plan_maison.py` + `placement.json` -> `plan_maison.html` (18 cartes, 6 lieux, pièces décrites par l'utilisateur, 5 liens ModBus saisis à la main, fiche au clic, filtre de liens).
Corrections demandées ce jour et déjà appliquées : VR porte devant les WC (à côté de la cuisine), portail de jardin au Jardin devant le garage, grenier du 2e au-dessus des chambres du 2e.

Données déjà dans les `_persist.json`, donc dérivables sans saisie : `drivers.ModBus.typeComm` (Serial, UDP, MQTT, TCP à ON/OFF), `drivers.ModBus.id` (0 = maître du bus), `serveur.rangeExtender` (`id`, `ipMaitre` : esclave Wi-Fi derrière le NAPT du maître), `serveur.mqtt.topic`, `serveur.IP`.
Constats : cuve, rideau, portail et « serveur niveau » du garage pointent `ipMaitre` vers le P4 (192.168.0.43) ; l'écran de la cave pointe vers `serveur-rly` (.243) ; le serveur de débits PAC vers l'écran de débits (.51). Le « serveur niveau » du garage (ModBus id 0, UDP OFF) est ambigu : à confirmer avec l'utilisateur.

Décisions de conception (mes choix, à corriger) :
- Le sens d'un lien n'est jamais seulement une couleur (daltonisme, impression noir et blanc) : style de trait + forme du symbole + couleur.
- Source des liens = les persist (dérivation automatique), `placement.json` ne garde que les exceptions et les confirmations.
- Une seule page, deux vues (plan / réseau), même données.

## A1 — Corrections de placement
- [x] VR porte dans les WC, portail dans le Jardin, grenier 2e sur les chambres — preuve : `python outils_docs/plan_maison/genere_plan_maison.py` -> « 18 cartes, 5 liens », sans avertissement
- [x] Confirmé par l'utilisateur : « serveur niveau » du garage = maître id 0, capteurs cuve sous le jardin, bureau du 1er étage = cartes PAC — preuve : message du 2026-11-15 ; cuve placée au Jardin. La cave reste sous la maison (question restée sans réponse)

## A2 — Liens dérivés des persist
- [x] Fonction de dérivation — preuve : `python outils_docs/plan_maison/genere_plan_maison.py` -> « 18 cartes, 10 traits de lien, 3 maîtres, 5 esclaves » sans avertissement, rendu relu en capture Chrome le 2026-11-15 : types de lien (ModBus série, ModBus/push UDP, Wi-Fi Range Extender, MQTT, TCP) lus dans `typeComm` et `rangeExtender`
- [x] Rôle de chaque carte — preuve : `python outils_docs/plan_maison/genere_plan_maison.py` -> « 18 cartes, 10 traits de lien, 3 maîtres, 5 esclaves » sans avertissement, rendu relu en capture Chrome le 2026-11-15 : maître si `rangeExtender.id` = 0 et esclaves rattachés, esclave si `ipMaitre` ou `id` > 0 ; résolution de l'IP du maître vers la carte (table IP -> carte tirée des persist)
- [ ] Exceptions et confirmations manuelles dans `placement.json` : `ip_cartes`, `etiquettes`, `liens_manuels` faits ; reste l'avertissement quand la dérivation et la saisie divergent
- [x] Remplacer les 5 liens saisis — preuve : `python outils_docs/plan_maison/genere_plan_maison.py` -> « 18 cartes, 10 traits de lien, 3 maîtres, 5 esclaves » sans avertissement, rendu relu en capture Chrome le 2026-11-15 par les liens dérivés et comparer à la liste actuelle

## A3 — Symboles des types de communication
- [x] Un trait par type — preuve : `python outils_docs/plan_maison/genere_plan_maison.py` -> « 18 cartes, 10 traits de lien, 3 maîtres, 5 esclaves » sans avertissement, rendu relu en capture Chrome le 2026-11-15 : ModBus série = plein épais (bus RS485), UDP/Wi-Fi = pointillé, MQTT = tiret-point, TCP = double trait ; couleur en renfort seulement
- [x] Légende complète — preuve : `python outils_docs/plan_maison/genere_plan_maison.py` -> « 18 cartes, 10 traits de lien, 3 maîtres, 5 esclaves » sans avertissement, rendu relu en capture Chrome le 2026-11-15 de la page (trait, symbole, signification), cases de filtre par type
- [x] Flèches — preuve : `python outils_docs/plan_maison/genere_plan_maison.py` -> « 18 cartes, 10 traits de lien, 3 maîtres, 5 esclaves » sans avertissement, rendu relu en capture Chrome le 2026-11-15 : maître -> esclave pour la commande ; flèche inverse fine pour le push esclave -> maître (`ModbusPushUDP`) quand l'UDP est actif
- [ ] Pastille sur le milieu du lien : texte court (id ModBus, débit 19200 8N1)

## A4 — Symboles maître et esclave
- [x] Maître : couronne — preuve : `python outils_docs/plan_maison/genere_plan_maison.py` -> « 18 cartes, 10 traits de lien, 3 maîtres, 5 esclaves » sans avertissement, rendu relu en capture Chrome le 2026-11-15 ou étoile sur la pastille + bordure double ; esclave : badge rond numéroté (id ModBus)
- [ ] Marque « Range Extender » (point d'accès NAPT) sur les cartes qui portent un réseau derrière elles
- [x] Carte isolée — preuve : `python outils_docs/plan_maison/genere_plan_maison.py` -> « 18 cartes, 10 traits de lien, 3 maîtres, 5 esclaves » sans avertissement, rendu relu en capture Chrome le 2026-11-15 (aucun lien actif) : pastille estompée avec la mention « autonome »
- [x] Carte du dossier `-sauvegarde` — preuve : `python outils_docs/plan_maison/genere_plan_maison.py` -> « 18 cartes, 10 traits de lien, 3 maîtres, 5 esclaves » sans avertissement, rendu relu en capture Chrome le 2026-11-15 ou ancien code : marque « ancien code » (cave)

## A5 — Lisibilité des liens
- [x] Routage en coudes — preuve : `python outils_docs/plan_maison/genere_plan_maison.py` -> « 18 cartes, 10 traits de lien, 3 maîtres, 5 esclaves » sans avertissement, rendu relu en capture Chrome le 2026-11-15 orthogonaux depuis des ancres sur les bords, sans passer sous une pastille (cas P4 -> portail du garage)
- [ ] Liens entre pièces et entre étages : faisceau par bus plutôt qu'une ligne par esclave
- [x] Surbrillance au survol d'un maître : tout son réseau (esclaves et sens) ; clic : fiche avec liste des liens

## A6 — Autres informations sur la page
- [x] Bascule vue plan / vue réseau (topologie : broker MQTT, P4, esclaves, PC) sans changer de données — preuve : `genere_plan_maison.py` sans avertissement, vue réseau relue en capture Chrome le 2026-11-15 (broker 192.168.0.5:1883 lu dans les persist)
- [x] Nœud « Broker MQTT » et liens MQTT : topic de chaque carte, si le broker est confirmé par l'utilisateur — preuve : `genere_plan_maison.py` sans avertissement, vue réseau relue en capture Chrome le 2026-11-15 (broker 192.168.0.5:1883 lu dans les persist)
- [x] Badge de puce coloré (ESP32, S3, P4, ESP8266), IP et nom d'hôte sur la fiche, lien vers la page web de la carte (http://IP) quand elle est connue — preuve : `genere_plan_maison.py` sans avertissement, vue réseau relue en capture Chrome le 2026-11-15 (broker 192.168.0.5:1883 lu dans les persist)
- [x] État optionnel : en ligne ou hors ligne par ping, à la demande seulement (bouton), jamais au chargement — preuve : `genere_plan_maison.py` sans avertissement, vue réseau relue en capture Chrome le 2026-11-15 (broker 192.168.0.5:1883 lu dans les persist)
- [x] Export impression : PNG et PDF propres, thème clair imposé — preuve : `genere_plan_maison.py` sans avertissement, vue réseau relue en capture Chrome le 2026-11-15 (broker 192.168.0.5:1883 lu dans les persist)

## A7 — Qualité et documentation
- [x] Banc `test_plan_maison.py` : dérivation des liens sur des persist de test, avertissements (carte sans placement, lien orphelin), témoin négatif — preuve : `python outils_docs/plan_maison/test_plan_maison.py` -> 18 OK, 0 échec, sortie 0
- [ ] Sonde Chrome de la page : pas de débordement de pièce, un lien par entrée du banc, filtres, légende
- [x] Section du `outils_docs/README.md` et entrée de la carte des documents de `CLAUDE.md` (arrêt libre, hors build) — preuve : section « Plan de la maison » du README et ligne de la carte des documents de CLAUDE.md
- [ ] Contrôle de secrets avant commit (la page affiche IP, topics, jamais de mot de passe) puis commit en français sans accents

## A8 — Wi-Fi, box, relais et répéteurs, survol, tuile annuaire
- [x] Vue Wi-Fi : box, relais et répéteurs placés dans leurs pièces ; rattachement principal (reseau1) et secours (reseau2, masqué par défaut) lus dans les persist, SSID -> appareil — preuve : vue relue en capture Chrome le 2026-11-15, banc test_plan_maison.py (cas wifi)
- [x] Range Extender du maître : signalétique à part (rail rose double), SSID « <hote>-GATEWAY » -> carte maître — preuve : capture Chrome, 5 esclaves rattachés, banc test_plan_maison.py
- [x] Surbrillance au survol d'une carte (maître : tout son réseau), clic = fiche avec liens — preuve : fonctions hl/sel dans la page générée ; non testé au clic dans un navigateur
- [x] Tuile « Plan de la maison » dans l'annuaire (port 7915, lecture seule) — preuve : `python outils_docs/scripts_python/outils_pc/test_plan_maison_web.py` 5 OK, test_annuaire.py VERT (22 outils)
- [ ] Confirmer avec l'utilisateur : l'appareil réel de MAISON pour chaque module (déduit : Freebox Server), répéteur salon sans SSID identifié

## Améliorations restantes
- [x] [projet] Tuile « Plan de la maison » dans l'annuaire des outils (page servie sur un port libre, lecture seule)
- [ ] [projet] Dessiner un vrai plan à l'échelle des pièces (si l'utilisateur fournit les dimensions ou un plan)
- [ ] [projet] Lier la page aux façades animées (`volets.js`) : clic sur une pièce -> sa page d'accueil
- [ ] [conversation] Confirmer les placements incertains de A1

## Vérification
Régénérer la page, la lire dans Chrome headless (capture) et dans un navigateur : toutes les cartes de `data/` placées, liens identiques à ceux des persist, légende cohérente avec les traits dessinés, rendu lisible en noir et blanc. Aucune compilation, aucun appel réseau, aucun fichier de `data/fs` touché.
