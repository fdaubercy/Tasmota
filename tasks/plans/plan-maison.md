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
- [x] Pastille sur le milieu du lien : texte court (id ModBus, débit 19200 8N1) — preuve : étiquette « id N » au milieu des liens RS485 et UDP, relue en capture et testée par la sonde Chrome (ne mentionne pas le débit : tient dans la fiche)

## A4 — Symboles maître et esclave
- [x] Maître : couronne — preuve : `python outils_docs/plan_maison/genere_plan_maison.py` -> « 18 cartes, 10 traits de lien, 3 maîtres, 5 esclaves » sans avertissement, rendu relu en capture Chrome le 2026-11-15 ou étoile sur la pastille + bordure double ; esclave : badge rond numéroté (id ModBus)
- [x] Marque « Range Extender » (point d'accès NAPT) sur les cartes qui portent un réseau derrière elles — preuve : marque « 📶 RE ×N » sur les maîtres du plan, sonde Chrome « maitre P4 : marque Range Extender x3 »
- [x] Carte isolée — preuve : `python outils_docs/plan_maison/genere_plan_maison.py` -> « 18 cartes, 10 traits de lien, 3 maîtres, 5 esclaves » sans avertissement, rendu relu en capture Chrome le 2026-11-15 (aucun lien actif) : pastille estompée avec la mention « autonome »
- [x] Carte du dossier `-sauvegarde` — preuve : `python outils_docs/plan_maison/genere_plan_maison.py` -> « 18 cartes, 10 traits de lien, 3 maîtres, 5 esclaves » sans avertissement, rendu relu en capture Chrome le 2026-11-15 ou ancien code : marque « ancien code » (cave)

## A5 — Lisibilité des liens
- [x] Routage en coudes — preuve : `python outils_docs/plan_maison/genere_plan_maison.py` -> « 18 cartes, 10 traits de lien, 3 maîtres, 5 esclaves » sans avertissement, rendu relu en capture Chrome le 2026-11-15 orthogonaux depuis des ancres sur les bords, sans passer sous une pastille (cas P4 -> portail du garage)
- [x] Liens entre pièces et entre étages : faisceau par bus plutôt qu'une ligne par esclave — proposition C (colonne centrale) mise en place dans `genere_plan_maison.py::colonne` — preuve : capture Chrome du 2026-11-15 (tronc entre cuve et portail, étiquette « id 2 · id 4 »), `test_plan_maison.py` et `test_plan_maison_page_chrome.py` à 0 échec
- [x] Surbrillance au survol d'un maître : tout son réseau (esclaves et sens) ; clic : fiche avec liste des liens

## A6 — Autres informations sur la page
- [x] Bascule vue plan / vue réseau (topologie : broker MQTT, P4, esclaves, PC) sans changer de données — preuve : `genere_plan_maison.py` sans avertissement, vue réseau relue en capture Chrome le 2026-11-15 (broker 192.168.0.5:1883 lu dans les persist)
- [x] Nœud « Broker MQTT » et liens MQTT : topic de chaque carte, si le broker est confirmé par l'utilisateur — preuve : `genere_plan_maison.py` sans avertissement, vue réseau relue en capture Chrome le 2026-11-15 (broker 192.168.0.5:1883 lu dans les persist)
- [x] Badge de puce coloré (ESP32, S3, P4, ESP8266), IP et nom d'hôte sur la fiche, lien vers la page web de la carte (http://IP) quand elle est connue — preuve : `genere_plan_maison.py` sans avertissement, vue réseau relue en capture Chrome le 2026-11-15 (broker 192.168.0.5:1883 lu dans les persist)
- [x] État optionnel : en ligne ou hors ligne par ping, à la demande seulement (bouton), jamais au chargement — preuve : `genere_plan_maison.py` sans avertissement, vue réseau relue en capture Chrome le 2026-11-15 (broker 192.168.0.5:1883 lu dans les persist)
- [x] Export impression : PNG et PDF propres, thème clair imposé — preuve : `genere_plan_maison.py` sans avertissement, vue réseau relue en capture Chrome le 2026-11-15 (broker 192.168.0.5:1883 lu dans les persist)

## A7 — Qualité et documentation
- [x] Banc `test_plan_maison.py` : dérivation des liens sur des persist de test, avertissements (carte sans placement, lien orphelin), témoin négatif — preuve : `python outils_docs/plan_maison/test_plan_maison.py` -> 18 OK, 0 échec, sortie 0
- [x] Sonde Chrome de la page : pas de débordement de pièce, un lien par entrée du banc, filtres, légende — preuve : `python outils_docs/scripts_python/outils_pc/test_plan_maison_page_chrome.py` 33 OK, 0 échec ; témoins (survol et en-tête cassés) détectés par 3 KO ; aucun Chrome orphelin
- [x] Section du `outils_docs/README.md` et entrée de la carte des documents de `CLAUDE.md` (arrêt libre, hors build) — preuve : section « Plan de la maison » du README et ligne de la carte des documents de CLAUDE.md
- [x] Contrôle de secrets avant commit (la page affiche IP, topics, jamais de mot de passe) puis commit en français sans accents — preuve : agent controleur-secrets OK avant chaque commit (4 passages)

## A8 — Wi-Fi, box, relais et répéteurs, survol, tuile annuaire
- [x] Vue Wi-Fi : box, relais et répéteurs placés dans leurs pièces ; rattachement principal (reseau1) et secours (reseau2, masqué par défaut) lus dans les persist, SSID -> appareil — preuve : vue relue en capture Chrome le 2026-11-15, banc test_plan_maison.py (cas wifi)
- [x] Range Extender du maître : signalétique à part (rail rose double), SSID « <hote>-GATEWAY » -> carte maître — preuve : capture Chrome, 5 esclaves rattachés, banc test_plan_maison.py
- [x] Surbrillance au survol d'une carte (maître : tout son réseau), clic = fiche avec liens — preuve : fonctions hl/sel dans la page générée ; non testé au clic dans un navigateur
- [x] Tuile « Plan de la maison » dans l'annuaire (port 7915, lecture seule) — preuve : `python outils_docs/scripts_python/outils_pc/test_plan_maison_web.py` 5 OK, test_annuaire.py VERT (22 outils)
- [x] Confirmer avec l'utilisateur : l'appareil réel de MAISON — preuve : réponse de l'utilisateur le 2026-11-15, Freebox Server et répéteur du salon diffusent tous deux MAISON ; note dans `placement.json > wifi.defaut_ssid`
- [x] [projet] Rattacher chaque carte à son appareil MAISON réel — preuve : `Status 11` lu sur 8 cartes le 2026-11-15, deux BSSID ; P4 du garage = répéteur du salon dans `placement.json > wifi.wifi_manuel`, les 9 cartes éteintes ou sans adresse gardent le défaut Freebox (à relire quand elles seront allumées)

## A9 — Couche chauffage et débits
- [x] Vue chauffage : PAC (cave), nourrice (bureau), eau chaude PAC -> nourrice, départs vers les pièces chauffées (RDC, 1er hors bureau, chambres du 2e) — preuve : capture Chrome 2026-11-15, sonde « vue chauffage : PAC et nourrice, traits d'eau », données dans placement.json > chauffage (réponses de l'utilisateur)
- [x] Affecter Débit 1 à 6 à leur pièce — preuve : placement.json > chauffage.departs (liste de l'utilisateur du 2026-11-15), ronds numérotés relus en capture Chrome, banc test_plan_maison.py (2 cas chauffage)  ; D3 corrigé en salle de bain par l'utilisateur le 2026-11-15
- [x] Afficher les valeurs en direct des 6 débits (bouton « Lire les débits », à la demande, lecture serveur de `Status 10`) — preuve : `test_plan_maison_web.py` 6 cas /debits, sonde Chrome (valeurs, voie muette rouge, voie imprécise orange, carte muette) ; lecture réelle sur la carte non essayée

## A10 — Icône de lien et débits en direct
- [x] Icône ↗ de lien sur chaque pastille qui a une adresse (page web de la carte) — preuve : capture Chrome 2026-11-15, sonde Chrome (4 vérifications)
- [x] Bouton « Lire les débits » en vue chauffage : valeurs à côté des 6 ronds, total, voies muettes et imprécises signalées — preuve : sonde Chrome (6 vérifications) ; route GET /debits en lecture seule, cible fixe, 502 propre
- [ ] Essai réel de la lecture des débits sur la carte `tasmota32s3-serveur-debits-pac` (derrière le NAPT de l'écran, port 8080), non fait

## Améliorations restantes
- [x] [projet] Tuile « Plan de la maison » dans l'annuaire des outils (page servie sur un port libre, lecture seule)
- [ ] [projet] Dessiner un vrai plan à l'échelle des pièces (si l'utilisateur fournit les dimensions ou un plan)
- [ ] [projet] Clic sur une pièce -> sa page d'accueil ou sa façade animée (`volets.js`) ; les pastilles ont déjà leur icône de lien
- [x] [conversation] Confirmer la position de la cave (sous la maison) — preuve : confirmé par l'utilisateur le 2026-11-15
- [x] [projet] Vérifier l'en-tête fixe dans un navigateur avec la barre « Annuaire » — preuve : confirmé par l'utilisateur le 2026-11-15 (« le bandeau fonctionne »)
- [x] [projet] Pousser les commits du plan de la maison — preuve : poussé jusqu'à ec4ccf63b le 2026-11-15 ; le commit des débits est local
- [x] [projet] Lier le plan aux pages des cartes par une icône ↗ sur chaque pastille (IP de la carte ; esclave derrière un maître : IP du maître, port 8080 + id - 1) — preuve : sonde Chrome (adresses P4 et cuve, absente sans adresse, le clic n'ouvre pas la fiche) ; clic sur une pièce non fait
- [ ] [projet] Plan à l'échelle des pièces, si l'utilisateur fournit les dimensions ou un plan

## Vérification
Régénérer la page, la lire dans Chrome headless (capture) et dans un navigateur : toutes les cartes de `data/` placées, liens identiques à ceux des persist, légende cohérente avec les traits dessinés, rendu lisible en noir et blanc. Aucune compilation, aucun appel réseau, aucun fichier de `data/fs` touché.
