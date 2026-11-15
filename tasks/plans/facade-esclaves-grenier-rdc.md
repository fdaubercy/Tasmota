---
chantier: facade-esclaves-grenier-rdc
titre: Façades adaptées aux modules de chaque carte : esclave 4 (portail), rideau du garage, grenier du RDC
objectif: Chaque page d'accueil montre seulement ce que sa carte dirige : portail seul (esclave 4), garage et porte seuls (rideau), fenêtre de cuisine, porte d'entrée et trappe (grenier du RDC)
statut: actif
cree: 2026-11-15
maj: 2026-11-15
famille: graphiques-ecrans
parent: facade-garage-portail-commande
liens: atelier-visuels, visuel-reglage-volets, facade-garage-capteurs
---
# Façades adaptées aux modules de chaque carte

## Contexte
Demande du 2026-11-15, à la suite du portail de jardin (plan `facade-garage-portail-commande`, A1 à A7). Le moteur de dessin est `data/sd/js/volets.js` ;
le décor et les ouvertures dessinés viennent du `decor` et des volets portant un bloc `facade` dans le persist de chaque carte.
Décisions de l'utilisateur :
- **Esclave 4** (portail de jardin) : sa page d'accueil montre le portail seul (poteaux, vantaux, feu orange, capteur de fermeture).
- **Rideau du garage** : sa page montre le garage et la petite porte seuls, sans portail.
- **Grenier du RDC** : sa page montre ce qu'il dirige aujourd'hui : volet roulant de la fenêtre de cuisine, porte d'entrée, trappe du grenier.
- À la fin de ce plan : retour au plan `atelier-visuels`.

Ce qu'on sait déjà (relevé du 2026-11-15) : le portail est dessiné sur le P4 quand le volet porte `type` `portail1` ou `portail2` et que `toit` vaut `unPan`
(le décor garage, la pergola du mur et la caméra partent alors avec lui). Le rideau a sa propre route `/rideau` et sa façade dans
`controleRideau.be::facade`. Le grenier du RDC a `facade.decor` = `["maison"]` et trois volets (`fenetre` place 1, `trappe` place 2, `porte` place 3).
L'esclave 4 n'a ni driver de volets ni page de façade : le Shutter du portail tourne sur le P4.

## A1 — Relever l'existant avant de dessiner
- [x] Capturer la page d'accueil du rideau (esclave) et celle du grenier du RDC telles qu'elles sont aujourd'hui (Chrome headless sur le vrai `volets.js`, persist du dépôt) — preuve : sonde `test_volets_chrome.py --capture` : facade_maison_camera.png (grenier du RDC) et facade_rideau_capteurs.png (rideau), montrées à l'utilisateur le 2026-11-15
- [ ] Lister ce qui est en trop ou faux sur chacune (par ex. éléments du garage ou du portail vus depuis le rideau, trappe ou porte du grenier mal placées)
- [ ] Demander à l'utilisateur une photo de la porte d'entrée, de la fenêtre de cuisine et de la trappe si l'ajustement du grenier du RDC l'exige

## A2 — Esclave 4 : la page montre le portail seul
> Suivi désormais dans `facade-garage-portail-commande` (action A8), à la demande de l'utilisateur du 2026-11-15. Les cases ci-dessous restent comme historique.

- [x] Décision de l'utilisateur (2026-11-15) : l'esclave 4 EST le portail (le serveur ne fait que lui envoyer des ordres) : sa page s'appuie sur son capteur de fermeture local (interrupteur1, GPIO 47), pas sur une lecture du P4 — preuve : réponse de l'utilisateur ; reste à décider comment représenter un portail ni fermé ni ouvert (le capteur ne donne que fermé ou non)
- [ ] Module de façade de l'esclave 4, sur le modèle de `controleRideau.be::facade` (route de position, page d'accueil, `volets.js`), sans driver de volets ; fichiers ajoutés à `custom_files_upload` de son env et exclus des autres
- [ ] Mode `portail seul` de `volets.js` : un décor sans maison ni garage, pergola à deux arches conservée, aucun volet de rangée ; banc `test_volets.mjs` et sonde Chrome
- [ ] Persist de l'esclave 4 : bloc `drivers.voletRoulants.facade` (`activation` ON, `decor`), volets portail 1 et 2 en lecture seule ; accord de l'utilisateur avant d'écrire le persist

## A3 — Rideau du garage : garage et porte seuls
- [x] Choix du `decor` du persist du rideau : `["chevrefeuille", "porte", "finition"]` (garage et porte seuls, sans pergola du mur, avec la nuit) et vérification que le rideau n'a aucun volet `portail1` ou `portail2` — preuve : persist du rideau, VR1 seul volet à bloc facade ; sonde `rideau nuit` : ni pergola ni portail
- [x] Rendu vu en capture : rideau, fins de course, petite porte fixe ; aucun élément du portail ; nuit selon le soleil — preuve : captures facade_rideau_jour.png et facade_rideau_nuit.png montrées à l'utilisateur le 2026-11-15 ; sonde Chrome « VERT » (scénario rideau nuit : 7 contrôles) ; banc banc_rideau_facade.py non relancé

## A4 — Grenier du RDC : adapter la représentation à ses modules
- [ ] Reprendre la façade `maison` d'après A1 : fenêtre de cuisine (volet roulant), porte d'entrée, trappe du grenier à leur place réelle, sans élément d'une autre carte
- [x] Nuit et ombrage selon l'heure du soleil de la carte, bouton Auto, Jour, Nuit (décor `maison` + `finition`, voile seul, sans cônes ni forêt) — preuve : volets.js (`nuitDecor`), images crépuscule et nuit validées par l'utilisateur le 2026-11-15 (« OK fais le »), persist du grenier du RDC `decor: ["maison", "finition"]`
- [x] Bancs `test_volets.mjs`, `banc_reglage_volets.py` et sonde `test_volets_chrome.py` (scénarios maison, trappe) verts ; capture avant et après montrée à l'utilisateur — preuve : test_volets.mjs « 0 echec(s) sur 176 verifications », banc_reglage_volets « OK », sonde Chrome « VERT » (scénario maison_nuit : 8 contrôles, dont voile > 0,28 à 17:20 et > 0,55 à 23:30, rouge avant sans voile)

## A5 — Mise en service
- [ ] Relecture : `controleur-secrets` (seul, avant commit), `relecteur-pages-web`, `verificateur-solidification` si un `.be` de `data/fs` change ; commit `feat(volets): ...`
- [ ] Compilation par la page Build (:7700) des envs touchés (esclave 4, rideau, grenier du RDC) et envoi des fichiers du FS ; rendu vu sur chaque carte

## A6 — Retour au plan atelier-visuels
- [ ] Reprendre `tasks/plans/atelier-visuels.md` (83 %) : étapes A4 (essai sur la cuve, fichiers d'essai retirés) et A5 (tests rouges à reprendre)

## Améliorations restantes
- [ ] [projet] Même démarche pour les autres cartes à volets (grenier du 2e étage)

## Vérification
Bancs : `node outils_docs/scripts_python/outils_pc/test_volets.mjs` (depuis la racine du dépôt), `berry/banc_reglage_volets.py`, `berry/banc_rideau_facade.py`,
sonde `test_volets_chrome.py`. Un banc PC ne prouve ni la solidification, ni le rendu sur la carte : essai sur chaque carte.
