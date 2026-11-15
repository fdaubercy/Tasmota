---
chantier: facade-garage-portail-commande
titre: Façade du garage et du portail de jardin : finition, commande par clic, jour et nuit selon le soleil
objectif: Une façade du P4 plus fidèle (finition, cônes de la caméra et de la lampe), commandable par clic (rideau, portail), avec nuit selon le soleil réel
statut: actif
cree: 2026-11-15
maj: 2026-11-15
famille: graphiques-ecrans
parent: facade-garage-capteurs
liens: atelier-visuels, visuel-reglage-volets
---
# Façade du garage et du portail : finition, clics, soleil

## Contexte
Demande du 2026-11-15 : s'inspirer du rendu d'une scène produite par Gemini (dégradés, ombres, arrière-plan) pour la façade du P4, en gardant
nos organes codés (rideau et fins de course, petite porte fixe, portail de jardin 1 ou 2 vantaux avec feu orange et capteur de fermeture, lampe et
caméra du dépôt). Rendu validé par l'utilisateur le 2026-11-15 (« OK ça marche ») : `outils_docs/volets_visuels/garage_propositions.html`
(proposition A retenue : finition dans `volets.js`). Consignes générales : `outils_docs/visuels_accueil/CONSIGNES_VISUELS.md`.

Décisions :
- Nuit selon le lever et le coucher réels du soleil (persist : `localisation`, `fuseauHoraire`), fondu de 35 min, profondeur qui suit l'heure
  (crépuscule bleu léger, nuit noire vers le milieu). Repli sur l'heure du navigateur si la carte ne répond pas, signalé à l'écran.
- Portail : deux zones de clic distinctes (vantail droit = un vantail, vantail gauche = les deux) ; arrêt sans confirmation, toute ouverture,
  fermeture ou reprise avec confirmation et rappel de sécurité. Rideau : clic = ouvrir ou fermer après confirmation. Petite porte : aucun clic.
- Sécurité de la commande par clic (2026-11-15) : le P4 n'a pas de mot de passe web (WEB_PASSWORD vide) et `apiHTTP` vaut ON (contrôle du Referer retiré) ; une page tierce du réseau local peut donc envoyer `POST /volets action=volet`. Décision de l'utilisateur : **ne rien changer** (risque accepté, déjà vrai pour la lampe et la caméra). Aucun ordre réel au portail ou au rideau lancé par Claude sans accord explicite de l'utilisateur.
- La lampe n'est pas liée à la nuit : elle reste commandée à la main.
- Piste pour l'heure du soleil sans toucher au Berry solidifié : `Status 7` de la carte donne `Sunrise` et `Sunset` (à confirmer sur la carte avant de s'y fier).

## A1 — Maquette validée
- [x] Maquettes A et B, page de comparaison, clics, nuit selon le soleil et profondeur — preuve : outils_docs/volets_visuels/garage_propositions.html, maquette_garage_a.html, maquette_garage_b.html (captures Chrome du 2026-11-15)
- [x] Notes de construction rangées pour d'autres lieux — preuve : outils_docs/visuels_accueil/CONSIGNES_VISUELS.md
- [x] Rendu validé par l'utilisateur — preuve : « OK ça marche » (2026-11-15)

## A2 — Finition de la façade dans `volets.js`
- [x] Bancs rouges d'abord : `test_volets.mjs` (forêt et ombre déclarées par le décor, cônes seulement si l'appareil est allumé, profondeur de nuit) — preuve : test_volets.mjs rouge sur le volets.js d'avant (KO sur la finition, minutesDe absent), 0 echec sur 129 verifications apres (2026-11-15)
- [x] Forêt d'automne derrière le toit, ombre douce sous le portail et les piliers, mur plus sombre vers le bas, déclarés par `decor` — preuve : volets.js::foret, degrades vf_mur et vf_debord, test_volets.mjs « finition declaree : une foret, une couche de nuit, deux cones » ; rendu du vrai moteur vu en capture Chrome (scratchpad rendu_finition.html)
- [x] Cônes de couverture de la caméra et de la lampe (zones élargies), fondu 0,5 s, dessinés sous les organes — preuve : volets.js (cones sous poseCamera et poseLampe), test_volets.mjs « camera ON : son cone seulement », « lampe ON : son cone aussi » ; capture Chrome jour et nuit
- [x] Couche de nuit : opacité et teinte selon la profondeur ; `volets.js` reste une exception déclarée au compteur de lignes (CLAUDE.md à mettre à jour) — preuve : volets.js::nuitEtat, minutesDe, poseNuit ; test_volets.mjs 10 cas (00:30 = 0,62 et rgb(4,7,15), coucher = 0,15, jour = 0) ; CLAUDE.md : volets.js 676 lignes ; sonde test_volets_chrome.py VERT

## A3 — Portail de jardin dans la façade
- [x] Lire ce que `vrPages.be::facade` transmet pour VR2 et VR3 (portail 1 vantail, 2 vantaux, mode 3) et la forme des capteurs de fermeture — preuve : lecture du 2026-11-15 de vrPages.be::facade (id, nom, type, place, temps, finsDeCourse {module, ouverture, fermeture} ; volets inactifs ou sans bloc facade ignorés) et du persist du P4 : VR2 « Portail 1 vantail » (bouton 3) et VR3 « Portail 2 vantaux » (bouton 4), activation OFF, sans bloc facade, capteurFerme « Interrupteur3 »
- [x] Décor `portail` : un ou deux vantaux animés d'après la position lue, feu orange qui clignote pendant le mouvement, capteur de fermeture — preuve : volets.js (types portail1 et portail2, vantaux, feu, capteur de fermeture), test_volets.mjs « 0 echec(s) sur 146 verifications » (rouge avant : V.vantaux absent), capture Chrome du vrai moteur (scratchpad rendu_portail.html)
- [x] Côté carte : `vrPages.be::facade` transmet déjà VR2 et VR3 sans modification (type et finsDeCourse lus tels quels, capteur de fermeture seul accepté) — preuve : banc_reglage_volets.py « BANC_REGLAGE_VOLETS: OK » avec 4 vérifications portail ajoutées (aucun changement de Berry, donc pas de recompilation pour cette étape ; témoin rouge non fait)

## A4 — Commande par clic
- [x] Vérifier ce que `POST /volets action=appui` fait pour un volet en mode 3 (portail) et pour le rideau ; décider si une action est à ajouter — preuve : lecture de vrPages.be::ordre : appui, debut et annuler sont l'assistant de réglage des durées, pas une commande ; action ajoutée `volet` (ouvre, ferme, toggle, stop) dans vrPages::commandeVolet, banc_reglage_volets 17e « BANC_REGLAGE_VOLETS: OK » (5 ECHEC avant, 13 vérifications ensuite) ; Berry solidifié : firmware à recompiler
- [x] Zones de clic : rideau, vantail droit (simple), vantail gauche (double), caméra, lampe ; confirmation avec rappel de sécurité ; arrêt sans confirmation — preuve : volets.js::ordreClic, brancheClics ; test_volets.mjs « 0 echec(s) sur 161 verifications » (confirmation, arrêt sans confirmation, rappel de sécurité du portail)
- [x] Refus si l'état est inconnu ou si la carte est muette ; page non ouverte par un autre appareil que ceux autorisés (accès existant de la carte) — preuve : ordreClic renvoie null sans position lue (test_volets.mjs) ; côté carte : volet inactif, sans bloc façade, id inconnu, ordre inconnu, en réglage, accès non privilégié refusés (banc 17e) — l'accès par autre appareil reste celui de check_privileged_access
- [x] Sonde Chrome : clic, confirmation, ordre envoyé à une carte simulée — preuve : test_volets_chrome.py scénario « portail » (16 contrôles : cônes, capteur de fermeture, clic refusé = aucun POST, vantail droit = volet 2 toggle, gauche = volet 3, rideau = ouvre, arrêt en mouvement sans confirmation), sonde entière « VERT » le 2026-11-15 ; vrPages.be solidifié « LE .h COMPILE »

## A5 — Jour et nuit selon le soleil
- [x] Lire `Sunrise` et `Sunset` sur la carte (`Status 7` ou lecture ajoutée à `?f=capteurs`) ; comparer à la maquette (08:01 et 17:04 le 15 novembre) — preuve : lecture du firmware : la commande Sunrise n'est que l'angle de l'aube ; Status 7 (support_command.ino, xdrv_09_timers.ino::GetSun) donne StatusTIM {Local, Sunrise, Sunset} ; volets.js::lisSoleil lit /cm?cmnd=Status 7 toutes les 5 min, aucun Berry modifié ; comparaison à la valeur réelle de la carte : à faire à l'essai (A6)
- [x] Mode Auto, Jour, Nuit forcés ; repli sur l'heure du navigateur signalé ; test avec heure simulée — preuve : test_volets.mjs « 0 echec(s) sur 171 verifications » (soleilDe, modeSuivant, poseMode) ; sonde Chrome scénario « soleil » : midi = pas de voile, 23:30 = voile > 0,55, clic = Jour forcé, mode gardé, carte muette = pas de nuit ; sonde entière VERT. Écart au plan : sans lecture le repli est « jour », pas l'heure du navigateur (le lever dépend du lieu)

## A6 — Essai sur carte
- [ ] Compilation par la page Build (:7700), jamais par pio direct ; contrôler que les fichiers `volets.js` et la page sont bien dans l'image
- [ ] Rendu vu sur le P4 : façade, clics, nuit ; tas et `UfsFree` relevés ; aucune commande réelle du portail sans accord de l'utilisateur

## A7 — Documentation et commit
- [ ] `outils_docs/README.md`, `CLAUDE.md` (carte des documents, exception des lignes de `volets.js`), `CONSIGNES_VISUELS.md` (journal des affinements) ; `verifie_references_docs.py` vert
- [ ] Agents avant commit : `controleur-secrets`, `relecteur-pages-web` ; commit `feat(volets): ...`

## A8 — Retour au plan atelier-visuels
- [ ] Une fois A7 close, reprendre le plan `atelier-visuels` (tasks/plans/atelier-visuels.md, 83 %) : prochaines étapes A4 (essai sur la cuve, fichiers d'essai retirés) et A5 (tests rouges à reprendre)

## Améliorations restantes
- [ ] [projet] Brancher la page de l'atelier des visuels sur les consignes (plan atelier-visuels, A7)
- [ ] [projet] Même façade animée pour la carte du rideau et l'accueil d'autres lieux

## Vérification
Bancs : `node outils_docs/scripts_python/outils_pc/test_volets.mjs`, `berry/banc_reglage_volets.py`, sondes `test_volets_chrome.py` et
`test_reglage_volets_chrome.py`. Un banc PC ne prouve ni la solidification, ni le rendu sur la carte, ni la commande réelle : essai sur le P4.
