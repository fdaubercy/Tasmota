---
chantier: visuel-reglage-volets
titre: Visuel des volets sur la page d'accueil et réglage des durées par les boutons
objectif: Dessiner sous les curseurs des volets une façade dont les tabliers suivent la position réelle en direct, et régler tempsMontee et tempsDescente depuis la page Configuration avec les boutons existants
statut: actif
cree: 2026-11-11
maj: 2026-11-11
---
# Visuel des volets et réglage des durées

> Pour l'exécutant : suivre les actions dans l'ordre, cocher chaque étape dès qu'elle est vérifiée, avec « — preuve : … ».
> Skill conseillée : superpowers:subagent-driven-development ou superpowers:executing-plans.

## Contexte

**But.** A12 et A13 du plan (appelé par son action A14 ; A9 ici ramène au plan d'origine) `tasks/plans/envs-grenier-rdc-sonoff-cave.md`. Spec validée par l'utilisateur le 2026-11-11 :
`docs/superpowers/specs/2026-11-11-visuel-volets-reglage-durees-design.md` (à lire en entier avant A1). Maquettes :
`outils_docs/volets_visuels/maquette_*.html`.

**Architecture.** Côté carte, deux modules Berry neufs et solidifiés, sans état dans leur table (piège 12) :
`data/fs/vrReglage.be` (machine du mode réglage, état dans `vrFonctions.etat()["reglage"]`) et `data/fs/vrPages.be`
(ajout de la page d'accueil, page de réglage, routes). Le driver `CONTROLE_VR` (`controleVoletRoulants.be`) les branche :
`web_add_main_button`, `web_add_config_button`, `web_add_handler`, `button_pressed`. Le dessin et l'animation sont faits par
le navigateur : `data/sd/js/volets.js`. La page de réglage : `data/sd/html/reglageVolets.html`, `data/sd/js/reglageVolets.js`,
`data/sd/css/reglageVolets.css`. Tout est livré par une liste `volets_pages` de `[berry_commun]`, exclue des envs sans façade.

**Pile.** Berry (Tasmota ESP32), JS sans bibliothèque (SVG), bancs `berry.exe`, Node pour les fonctions pures, Chrome sans
interface pour le rendu.

**Décisions de ce plan** (le constructeur les applique, l'utilisateur peut les revoir) :
- Bloc de façade : `drivers.voletRoulants.facade = {"activation": "ON", "toit": "deuxPans"|"unPan"|"aucun"}` et, dans chaque
  bloc VR, `"facade": {"type": "fenetre"|"porte"|"garage"|"trappe"|"trappeEchelle", "place": <1..n, de gauche à droite>}`.
  Bloc absent ou `activation` différent de `"ON"` : ni dessin, ni bouton « Réglage des volets », ni route. Le réglage suit donc la
  façade (les 3 cartes visées l'ont ; `tasmota32-rdc-vr-porte`, ESP32 classique remplacé par le grenier du RDC, ne l'a pas).
- Suspension des boutons d'un volet : `ShutterButton<id> 0`, puis renvoi des `ShutterButton` des AUTRES volets actifs.
  Raison : dans `xdrv_27_esp32_shutter.ino::CmndShutterButton`, la boucle de `ShutterButton<x> 0` n'a pas d'accolades ;
  `shutter_number = 0` et la remise des positions s'appliquent au bouton d'index `i` du compteur de jetons (0), donc au
  Button1, quel que soit son volet. Le renvoi des autres volets répare Button1 s'il ne fait pas partie du volet réglé.
  Remise à la sortie : `vrFonctions.configVRByJson()` entier (durées du persist et boutons de tous les volets).
- Un bouton retiré du volet n'est plus servi par le driver des volets (`FUNC_BUTTON_PRESSED` exige `enabled`) ; le driver
  Berry le reçoit par `button_pressed(cmd, idx)` (`xdrv_52_9_berry.ino`, idx = multipress<<24 | état<<16 | ancien état<<8 |
  index de bouton base 0 ; `PRESSED` = 0). `SetOption73` reste à 1 (posé par le driver des volets) : aucun relais basculé.
- Sens physique : une commande envoyée par Berry est inversée par Tasmota quand `ShutterInvert` vaut 1
  (`CmndShutterPosition`, seules série, page web et commande web en sont exemptées). Tout ordre de course ou de recalage
  passe par `vrFonctions.commandeSens(id, sens)`, qui reprend le croisement de `changementEtatCapteur`.
- Durées écrites en secondes entières arrondies (`int(ms / 1000.0 + 0.5)`) : `configVRByJson` les pose avec le type `int`.
- Toute étape du mode a 120 s (`DELAI_MS = 120000`), course allongée à 120 s (`COURSE_MAX = 120`). Mesure de moins de 2 s
  refusée (rien d'écrit). Un appui moins de 1 s après le précédent est ignoré (rebond, double clic page + bouton).
- Refus de commencer si un réglage est déjà actif, si le volet est inconnu ou inactif, ou s'il roule (`Direction` différent
  de 0 dans la réponse de `ShutterPosition<id>`).
- Fins de course neutralisées pour le volet en réglage : `vrFonctions.enReglage(id)` en tête de `changementEtatCapteur`.
- MPU6050 actif (réponses de l'utilisateur du 2026-11-11) : garde-fou seul pendant le réglage. `enReglage` coupe dans
  `releveInclinaison` l'arrêt en butée et l'appel de `changementEtatCapteur`, et coupe `positionReelle` ; la durée butée à
  butée (`suivi["durees"]`, vidé au début du réglage), `verifieSens` et `verifieBlocage` restent actifs. Un arrêt que le
  réglage n'a pas demandé (règle `Shutter<id>#Direction` 0 posée par `vrReglage` le temps du mode) l'arrête sans rien écrire,
  cause `bloque`, `sens inverse` (lues dans `suivi`) ou `arret`. La page affiche les durées du MPU à côté de la mesure.
- Dessin d'une trappe à MPU actif : l'angle est lu dans une balise `<span data-vi='<id>' data-angle='<a>' data-bloque='<cause>'>`
  ajoutée par `ligneWebInclinaison` (ligne déjà envoyée à chaque rafraîchissement), converti en % comme `positionReelle` ;
  ouverture en rouge avec « bloqué » ou « sens inverse » si `data-bloque` est posé ; sans angle, retour au curseur.
- Porte de garage (`drivers.voletRoulants.mode == 3`) : type `chrono`, aucune commande envoyée au volet, ni suspension de
  bouton, ni course allongée ; seuls les clics « Départ » / « Arrivée » de la page font avancer.
- Le dessin lit `eb('s27<n>').value` à chaque image (`requestAnimationFrame`) ; ouverture = `inverse == 1 ? 100 - v : v`.
  Poursuite (spec §4.2, décidée après la relecture d'A5, remplace l'extrapolation) : le dessin rejoint la dernière valeur lue
  à `100 / tempsMontee` %/s en montée, `100 / tempsDescente` en descente, sans la dépasser, puis s'arrête ; au chargement, il
  prend la valeur lue. Retard d'au plus un rafraîchissement. `inverse` absent du persist : 1 (`vrFonctions.inverse`).

**Contraintes globales** (valent pour chaque action) :
- Accord de l'utilisateur AVANT toute écriture dans `data/fs/*.be` et dans un `_persist.json` (demandé une fois en A1, pour
  tout le plan). `tasmota/user_config_override.h` : non touché.
- Charte des logs : `logFonctions.log` par `vrFonctions.log`, préfixe `VR_REGLAGE:` / `VR_PAGES:`, `_ERREUR` dans les
  `except`, pas d'`info` dans `button_pressed` hors d'un appui réel, messages coûteux gardés par `logFonctions.actif`.
- Fonctions des modules solidifiés appelées par `vrReglage.nom` / `vrPages.nom` / `vrFonctions.nom`, `import` du module
  dans chaque fonction qui le cite ; aucune nouvelle globale.
- Fichiers de moins de 500 lignes (`vrFonctions.be` en a 872 : rien de nouveau n'y entre hors A1).
- Compilation par la page Build (:7700) seulement, jamais en parallèle d'un build ; `banc_demarrage.py` après tout changement
  de `custom_berry_solidify` / `custom_files_upload` ; `--enregistre` seulement sans travail d'une autre session.
- Sondes Chrome : arrêter leurs Chrome en fin d'usage (vérifier qu'aucun `sonde_*` ne reste).
- Textes visibles en français avec accents ; commits en français sans accents, `git commit -- <chemins>`.

**Points à surveiller à la relecture** (non couverts par la spec, testés dans l'action indiquée) :
1. Rebond ou appui maintenu : une seule étape par appui (A3, test « rebond »).
2. Clic sur la page et appui physique presque ensemble : une seule étape (A3, même règle de 1 s).
3. Carte redémarrée ou injoignable pendant la page de réglage : la page dit « carte injoignable », ne montre jamais un
   résultat qu'elle n'a pas reçu (A6, scénario « injoignable »).
4. Volet déjà en course au clic « Régler les durées » : refus, rien de modifié (A3, test « en course »).
5. Curseur de la page d'accueil tiré à la main : la valeur visée est une cible comme une autre, le dessin la rejoint à la
   vitesse du volet et y reste quand Tasmota la renvoie (A5, scénario « curseur tiré » ; d'abord « ignorée », abandonné à
   la relecture : Tasmota ne renvoie pas une valeur égale à la dernière envoyée).

## A1 — Préparer vrFonctions : sens physique, boutons, neutralisation
Fichiers : `data/fs/vrFonctions.be`, `outils_docs/scripts_python/berry/banc_inclinaison.be` (section 19).
Produit : `vrFonctions.commandeSens(id, sens) -> string` (sens `"ouvre"`, `"ferme"`, `"posOuvert"`, `"posFerme"` ; volet
`inverse` 1 : `ShutterClose`, `ShutterOpen`, `ShutterSetClose`, `ShutterSetOpen` ; `inverse` 0 : l'inverse, suffixe `%i` = id),
`vrFonctions.configBoutons(vr)` (boucle des `ShutterButton` sortie de `configVRByJson`, qui l'appelle),
`vrFonctions.enReglage(id) -> bool` (vrai si `vrFonctions.etat().find("reglage")` est actif pour cet id) ;
`ligneWebInclinaison` complétée de la balise `data-vi` (voir Contexte).
- [x] Demander l'accord de l'utilisateur pour les écritures du plan dans `data/fs/*.be` et les trois `_persist.json` — preuve : accord « Oui, pour tout le plan » donné le 2026-11-11 dans la conversation
- [x] Section 19 du banc, écrite d'abord : `commandeSens` pour `inverse` 0 et 1 (4 sens), `configVRByJson` envoie toujours
  les mêmes `ShutterButton` qu'avant (liste comparée) ; pendant un réglage, `changementEtatCapteur` n'envoie rien, `releveInclinaison` n'arrête pas en
  butée et ne recale pas mais note la durée butée à butée, `positionReelle` n'envoie rien, `verifieSens` coupe toujours le
  moteur ; `ligneWebInclinaison` porte `data-vi`, `data-angle` et `data-bloque` ; lancée sur `data/fs` actuel : rouge — preuve : section 19 lancee sur data/fs avant ecriture : « attribute_error: module 'vrFonctions' has no member 'commandeSens' » (rouge)
- [x] Écrire les trois fonctions, faire passer `changementEtatCapteur` par `commandeSens`, ajouter les gardes `enReglage`
  et la balise de `ligneWebInclinaison` (section 9 du banc ajustée à la nouvelle ligne) — preuve : vrFonctions.be : configBoutons, commandeSens, enReglage, gardes et balise data-vi ; verifie_berry.py : 0 erreur, 0 avertissement de charte
- [x] `python outils_docs/scripts_python/berry/banc_inclinaison.py` : `BANC_INCLINAISON: OK`, sections 1 à 18 inchangées — preuve : sortie « BANC_INCLINAISON: OK », sections 1 a 19 vertes
- [x] Témoin : copie de `data/fs` sans la garde de `changementEtatCapteur` -> section 19 rouge — preuve : copie mutee (garde de changementEtatCapteur retiree) : « ECHEC pendant un reglage : changementEtatCapteur n'envoie rien », copie intacte OK
- [x] Commit `refactor(volets): sens physique, boutons et garde du reglage dans vrFonctions` — preuve : 9dd679373, relecture approuvée

## A2 — Décrire les façades dans les persists, le modèle et le schéma
Fichiers : `data/rdc/tasmota32s3-grenier/_persist.json`, `data/etage2/tasmota32s3-grenier/_persist.json`,
`data/garage/tasmota32p4-serveur-modbus/_persist.json`, `outils_docs/schemas/modele_persist.json`,
`outils_docs/schemas/persist.schema.json` (régénéré).
Valeurs : grenier du RDC `toit` `deuxPans`, VR2 cuisine `fenetre` place 1, VR3 trappe `trappe` place 2, VR1 porte `porte`
place 3 ; P4 du garage `toit` `unPan`, VR1 `garage` place 1 ; 2e étage `toit` `aucun`, VR1 `trappeEchelle` place 1. Modèle :
bloc `facade` à `"activation": "OFF"`, `toit` `deuxPans`, VR1 `fenetre` place 1.
- [x] Éditer le TEXTE des persists (tabulations et ordre gardés, script dans le scratchpad qui vérifie chaque remplacement
  puis relit le JSON), jamais de réécriture par `json.dump` — preuve : éditées en texte (script, 4 fichiers, 25 lignes ajoutées, 0 retirée), JSON relu : 3 persists et modèle portent les valeurs de la fiche
- [x] `python outils_docs/scripts_python/berry/genere_schema_persist.py` puis contrôle des persists : 0 erreur — preuve : genere_schema_persist.py puis --valide : 0 erreur sur tous les persists, schéma +37 lignes
- [x] Commit `feat(volets): facade decrite dans les persists des cartes a volets` — preuve : 30c747e28, relecture approuvée, schéma régénéré sans changement, persists 0 erreur

## A3 — Module du mode réglage `vrReglage.be` et son banc
Fichiers : `data/fs/vrReglage.be` (neuf), `outils_docs/scripts_python/berry/banc_reglage_volets.be` et `.py` (neufs, sur
le modèle de `banc_inclinaison.be/.py` : mêmes bouchons, horloge simulée, liste `tasmota.cmds`).
Consomme : `vrFonctions.commandeSens`, `configBoutons`, `configVRByJson`, `trouveVolet`, `suiviInclinaison`, `commandeArret`.
Produit :
- `vrReglage.debut(id) -> [bool, string]` ; `vrReglage.appui(id, source) -> [bool, string]` (source `"bouton"` ou `"page"`) ;
  `vrReglage.annule(motif) -> nil` (motif `"annule"` ou `"delai"`) ; `vrReglage.bouton(idx) -> bool` (appelé par
  `button_pressed`, vrai si l'appui est consommé) ; `vrReglage.etatPage() -> map`.
- `etatPage()` : `{"actif": bool, "id": int, "cle": "VR3", "nom": string, "type": "moteur"|"chrono",
  "etape": "pret"|"montee"|"haut"|"descente"|"fini"|"annule"|"delai"|"refus", "chrono_ms": int,
  "mesures": {"tempsMontee": int|nil, "tempsDescente": int|nil}, "avant": {"tempsMontee": int, "tempsDescente": int},
  "boutons": [ids Tasmota], "mpu": {"tempsMontee": real|nil, "tempsDescente": real|nil}|nil, "cause": string|nil,
  "message": string}` ; `{"actif": false, "etape": nil}` si aucun réglage n'a eu lieu.
Ordres envoyés (type `moteur`) : au début `ShutterOpenDuration<id> 120`, `ShutterCloseDuration<id> 120`, `ShutterButton<id> 0`,
`configBoutons` des autres volets, `commandeSens(id, "posFerme")` ; `pret`->`montee` : `commandeSens(id, "ouvre")` ;
`montee`->`haut` : `ShutterStop<id>`, `suiviInclinaison(id)["arret"] = millis`, `commandeArret(id, commandeSens(id, "posOuvert"))` ;
`haut`->`descente` : `commandeSens(id, "ferme")` ; `descente`->`fini` : `ShutterStop<id>`, écriture des deux durées
(`persist.drivers = drivers`, `persist.save(true)`), `commandeArret(id, commandeSens(id, "posFerme"))`, `configVRByJson()`.
Annulation ou délai : `ShutterStop<id>` si `montee` ou `descente`, `configVRByJson()`, rien d'écrit. Type `chrono` : aucun
de ces ordres, sauf `configVRByJson()` après l'écriture.
- [x] Banc écrit d'abord, un groupe par cas : déroulé complet 2 boutons (ordres exacts dans l'ordre, durées 14 et 13 s
  écrites, `save` appelé une fois) ; bouton unique `toggle` (même déroulé, sens imposé : `ShutterOpen` puis `ShutterClose`
  quoi que dise la fonction du bouton) ; `inverse` 1 (ordres croisés) ; annulation en montée (stop, rien d'écrit,
  `configVRByJson` rappelé) ; délai de 120 s (timer déclenché : stop, étape `delai`, une erreur au journal) ; rebond (deux
  appuis à 300 ms : une étape) ; mesure de 1,5 s refusée ; « en course » (`ShutterPosition` répond Direction 1 : refus,
  aucun ordre) ; second réglage pendant un premier : refus ; bouton d'un autre volet : non consommé ; chrono du garage
  (mode 3 : aucun ordre `Shutter*` ni `Power*`, durées écrites) ; arrêt inattendu en montée (règle Direction 0 jouée sans
  ordre du réglage, `suivi["cause"]` = « sens inverse ») : étape `annule`, cause rendue, rien d'écrit, règle retirée ;
  durées du MPU rendues dans `mpu` quand `suivi["durees"]` les porte ; lancé sans le module : rouge — preuve : banc_reglage_volets.be, 16 groupes (75 contrôles, + arrêt rapporté en retard, exception au début) ; sans le module : `import_error: module 'vrReglage' not found`, rc=1
- [x] Écrire `vrReglage.be` (en-tête de fichier : rôle, états, décisions de la section Contexte, bogue de `ShutterButton<x> 0`)
- [x] `python outils_docs/scripts_python/berry/banc_reglage_volets.py` : `BANC_REGLAGE_VOLETS: OK` — preuve : 75 ok, rc=0 ; banc_inclinaison.py reste OK
- [x] Témoin : copie de `data/fs` où `appui` suit la fonction du bouton au lieu de l'étape -> groupe « toggle » rouge — preuve : intacte OK ; mutée ECHEC (2) : « toggle : sens impose par l'etape » et « montee : ShutterOpen1 » (bouton down en montée)
- [x] `verifie_berry.py data/fs/vrReglage.be` : syntaxe OK, aucun écart de charte — preuve : 0 erreur, 0 avertissement de charte
- [x] Commit `feat(volets): mode reglage des durees (vrReglage) et son banc` — preuve : f5709e19d puis correction 8cbe2030e (direction lue dans read_sensors, faux arrêt au départ, recalage différé retiré), relectures approuvées

## A4 — Branchement dans le driver, pages côté carte, livraison par le cenv
Fichiers : `data/fs/vrPages.be` (neuf), `data/fs/controleVoletRoulants.be`, `platformio_tasmota_cenv.ini`,
`outils_docs/scripts_python/berry/banc_reglage_volets.be` (groupe « routes »), `banc_demarrage.py` et ses références.
Produit :
- `vrPages.facade() -> map|nil` : `{"toit", "rafraichissement": <WebRefresh ms>, "ouvertures": [{"id", "nom", "type",
  "place", "inverse", "tempsMontee", "tempsDescente", "inclinaison": {"ouvert", "ferme"}|nil}]}` trié par `place`
  (`inclinaison` posé si le MPU6050 du volet est actif), nil si façade inactive ;
- `vrPages.accueil()` : envoie `<div id='vf'></div><script>window.VOLETS=<json, "</" échappé>;</script><script>` + `/sd/js/volets.js`
  + `</script>` (rien si `facade()` est nil) ;
- `vrPages.route()` (GET `/volets` : page de réglage ; `?f=etat` : `etatPage()` en JSON) et `vrPages.ordre()` (POST `/volets`,
  `action` = `debut`|`appui`|`annuler`, `id`), tous deux derrière `webserver.check_privileged_access()`, réponse JSON
  `{"ok", "message", "etat"}`, 500 JSON sur exception (modèle : `graphiquesFonctions.enregistre`).
- Driver : `web_add_main_button` -> `vrPages.accueil()` ; `web_add_config_button` -> bouton « Réglage des volets » vers
  `/volets` si façade active ; `web_add_handler` -> les deux routes, appelé aussi à l'init (comme `controleEnergie_init`) ;
  `button_pressed(cmd, idx)` -> `vrReglage.bouton(idx)` si un réglage est actif, sinon false.
- cenv : liste `volets_pages = data/fs/vrReglage.be data/fs/vrPages.be data/sd/js/volets.js data/sd/html/reglageVolets.html
  data/sd/js/reglageVolets.js data/sd/css/reglageVolets.css` dans `[berry_commun]` ; `vrReglage.be` et `vrPages.be` ajoutés à
  `custom_berry_solidify` de `tasmota32s3-rdc-grenier`, `tasmota32s3-etage2-grenier`, `tasmota32p4-garage-serveur-modbus` ;
  `${berry_commun.volets_pages}` dans `custom_files_exclude` de tous les autres envs.
- [x] Groupe « routes » du banc d'abord : accès refusé sans Referer, `?f=etat` rend `etatPage()`, POST `debut` puis `appui`
  font avancer, action inconnue -> 400, façade inactive -> ni bouton de configuration ni contenu d'accueil ; rouge sans `vrPages` — preuve : groupe 17 de `banc_reglage_volets.be` ; sur `data/fs` de 8cbe2030e (sans `vrPages.be`) : 87 ok puis `attribute_error: 'CONTROLE_VR' object has no attribute 'web_add_handler'`, rc=1 ; témoins mutés : `route()` sans `check_privileged_access` -> ECHEC (1) « acces refuse », `ouverte` posé avant `etatPage()` -> ECHEC (1) « exception dans etatPage »
- [x] Écrire `vrPages.be` et les ajouts du driver ; banc vert — preuve : `banc_reglage_volets.py` BANC_REGLAGE_VOLETS: OK, 121 ok, rc=0 ; `banc_inclinaison.py` OK ; `verifie_berry.py` sur `vrPages.be` et `controleVoletRoulants.be` : 0 erreur, 0 avertissement de charte
- [x] cenv modifié ; `python outils_docs/scripts_python/berry/banc_demarrage.py` : les 3 envs à volets chargent les deux
  modules, les autres n'en voient aucun ; références mises à jour avec `--env <env> --enregistre` pour ces 3 envs seulement — preuve : cenv résolu par `fichiers_berry_ini.resout` : vrReglage et vrPages solidifiés par les 3 envs à volets (exclus 0), `volets_pages` (2 fichiers à A4) exclue de tous les autres envs à `custom_files_upload`, `tasmota32-rdc-vr-porte` compris ; `banc_demarrage.py` VERT sans `--enregistre` (modules solidifiés chargés à la demande : aucune rubrique de l'instantané ne les montre, rien à enregistrer)
- [x] Commit `feat(volets): pages du reglage et visuel branches dans le driver des volets` — preuve : ad355f288, relecture approuvée (cenv résolu sur les 19 envs)

## A5 — Le dessin de la façade `volets.js`
Fichiers : `data/sd/js/volets.js` (neuf), `outils_docs/scripts_python/outils_pc/test_volets.mjs` (neuf, Node, chargé par
`vm` comme `test_energie_rendu.mjs`), `outils_docs/scripts_python/outils_pc/test_volets_chrome.py` (neuf, sonde).
Produit (sur `window.Volets`) : `ouverture(valeur, inverse) -> 0..100` ; `ouvertureAngle(angle, incl) -> 0..100` ; `poursuit(dessinee, cible, dt, o) -> 0..100` (dt en ms,
o = ouverture de `window.VOLETS` ; remplace `avance(suivi, maintenant, o)` après la relecture) ; `dessine(conteneur, facade) -> SVGElement` ; `demarre(facade)` (insère
le dessin juste après la table qui contient `#s271`, boucle `requestAnimationFrame`). Chaque ouverture dessinée porte
`data-id` et `data-ouverture` (entier) ; le pourcentage affiché à côté est le même entier.
Rendu : celui des maquettes (`maquette_rdc_porte_cuisine.html`, `maquette_garage.html`, `maquette_trappes_rdc_2e.html`), couleurs
du thème sombre de Tasmota (`var(--c_bg)`, `var(--c_txt)`), largeur 100 % de la colonne.
- [x] `test_volets.mjs` d'abord : `ouverture(30, 0) == 30`, `ouverture(30, 1) == 70` ; `avance` à 15 s de course : +10 % en
  1,5 s, borné à 100, figé après `1,5 × rafraichissement` sans valeur nouvelle, sens de la dernière variation ; deux volets
  indépendants ; `ouvertureAngle(44, {ouvert: 85, ferme: 3})` = 50 (bornée à 0 et 100, montage inversé `ouvert` < `ferme`) ;
  rouge sans le fichier — preuve : sans `data/sd/js/volets.js`, `KO chargement ... ENOENT`, code 1 ; correction 1 (poursuite) :
  `poursuit` rejoint sans dépasser, vitesses montée/descente, immobile une fois atteinte, première lecture directe, bornée ;
  rouge sur le `volets.js` à extrapolation (`V.poursuit is not a function`), témoin qui dépasse : 4 KO
- [x] Écrire `volets.js` ; `node outils_docs/scripts_python/outils_pc/test_volets.mjs` : code 0 — preuve : « 0 echec(s) sur 28 verifications », code 0 ; après correction 1 : « 0 echec(s) sur 31 verifications » ; `volets.js` 198 lignes, ajouté à `volets_pages` du cenv (embarqué par les 3 envs à façade seulement, exclu des 14 autres envs à FS, résolu par `fichiers_berry_ini.resout`) ; `banc_boot.py` BANC_BOOT: OK, `banc_reglage_volets.py` OK, `banc_demarrage.py` VERT
- [x] Sonde Chrome écrite : page statique qui imite l'accueil de Tasmota (table de curseurs `s271`..`s273`, `window.VOLETS` des
  3 cartes), scénarios : position lue (`inverse` 0 et 1), poursuite entre deux valeurs (`data-ouverture` intermédiaire),
  jamais au-delà de la dernière valeur, curseur tiré (événement `input` puis `change` sur 80 : le dessin rejoint 80 et y reste
  quand Tasmota renvoie 80), dessin placé après la table des curseurs, aucun `s271` -> rien ; trappe à MPU : le dessin
  suit `data-angle` et non le curseur, retour au curseur sans balise, ouverture rouge « sens inverse » avec `data-bloque` ;
  Chrome arrêté à la fin — preuve : `test_volets_chrome.py` (pages rdc, garage, etage2, sans ; `--js`, `--capture`), Chrome tué par `tue_arbre` puis par son profil `sonde_volets_*` dans `Montage.ferme` (finally, et dans le constructeur s'il
  échoue après le lancement de Chrome : panne de CDP simulée, 0 Chrome du profil restant)
- [x] Sonde verte ; témoin : `volets.js` sans l'inversion -> scénario `inverse` 1 rouge ; aucun Chrome `sonde_*` restant — preuve : sonde VERT (25 OK), code 0 ; après correction 1 : VERT (26 OK), rouge (5) sur le `volets.js` à extrapolation, témoin
  qui dépasse la cible : 1 KO « jamais au-delà de la dernière valeur (80) » (82) ; témoin (`return borne(v)`) : ROUGE 5 échecs, tous `inverse 1` (garage, etage2), node : 3 KO `ouverture(.., 1)` ; `Get-CimInstance` : 0 chrome `sonde_*` après chaque passage
- [x] Commit `feat(volets): dessin de la facade sur la page d'accueil` — preuve : 4044f1dd7, b70c9fd1e, puis correction f3a0fbda2 (poursuite, sonde sans orphelin, inverse par défaut), relectures approuvées

## A6 — La page de réglage
Fichiers : `data/sd/html/reglageVolets.html`, `data/sd/js/reglageVolets.js`, `data/sd/css/reglageVolets.css` (neufs),
`outils_docs/scripts_python/outils_pc/test_reglage_volets_chrome.py` (neuf, sonde).
Contenu (spec §5.5) : choix du volet ; explications pas à pas selon le type (`moteur` à 1 ou 2 boutons, `chrono`) :
préparation (volet fermé), effet de chaque appui, annulation, ce qui est écrit ; étape en cours et chronomètre ; « le volet
monte-t-il ? Sinon, Annuler » (« descend » en descente) ; bouton « Étape suivante » (ou « Départ » / « Arrivée » en chrono),
bouton « Annuler » ; résultat : durées mesurées et précédentes, et les valeurs à recopier dans le persist du dépôt
(`drivers.voletRoulants.environnement.VRs.<cle>.tempsMontee` et `tempsDescente`), avec l'avertissement du flash série et de
l'envoi du FS ; durées du MPU6050 à côté quand `mpu` les porte ; cause d'un arrêt inattendu (« bloqué », « sens inverse »,
« arrêt »). Lecture de `?f=etat` toutes les 500 ms pendant un réglage, 3 s sinon ; ordres par POST `/volets`.
- [x] Sonde écrite d'abord, serveur simulé qui joue `etatPage()` : textes de chaque étape pour 1 bouton, 2 boutons, chrono ;
  POST envoyés (`action`, `id`) ; résultat et valeurs à recopier ; durées du MPU affichées ; arrêt « sens inverse » expliqué ; scénario « injoignable » (le serveur ne répond plus : message,
  aucun résultat affiché) ; mode sombre lisible ; Chrome arrêté à la fin — preuve : `test_reglage_volets_chrome.py` (405 lignes, `Montage` d'A5
  repris avec un gestionnaire et un profil `sonde_reglage_volets_*`), ROUGE sans les fichiers : 59 échecs ; aussi cadence 500 ms / 3 s, carte lente,
  500 après `debut` -> `pret`, aucun bouton, `bloque`/`arret`/`delai`/`refus`, nom à balise en texte, 320 px
- [x] Écrire les trois fichiers ; sonde verte ; témoin : page sans l'avertissement « Sinon, Annuler » -> rouge — preuve : sonde VERT (76 OK, dont l'ordre refusé ; lecture replanifiée avant l'affichage), code 0 ;
  témoin (`reglageVolets.js` sans « Sinon, Annuler ») : ROUGE 6 échecs, tous « question du sens » ; `test_volets_chrome.py` VERT ; `banc_reglage_volets`,
  `banc_boot`, `banc_demarrage` verts après l'ajout des 3 fichiers à `volets_pages` ; 0 Chrome `sonde_*` restant
- [x] Commit `feat(volets): page de reglage des durees` — preuve : 594616c2f et 824217c0e, relecture approuvée, sondes relancées par le contrôleur (VERT, 0 Chrome restant)

## A7 — Relectures, documentation, compilation
- [x] Agent `relecteur-berry` sur `vrFonctions.be`, `vrReglage.be`, `vrPages.be`, `controleVoletRoulants.be` ; agent
  `relecteur-pages-web` sur `volets.js` et la page de réglage ; corrections faites et bancs relancés — preuve : relecteur-berry et relecteur-pages-web (0 bloquant), 13 corrections C1 à C13 en 32351579b, relecture ciblée « tous adressés », bancs et sondes verts
- [x] `outils_docs/README.md` : mode d'emploi (façade dans le persist, réglage pas à pas, recopie des durées) ; ligne dans la
  « Carte des documents » de `CLAUDE.md` ; `python outils_docs/scripts_python/maintenance/verifie_references_docs.py` : code 0 — preuve : 6f6d88006 (README, CLAUDE.md, skill bancs), verifie_references_docs.py : 0 défaut, code 0
- [x] Compilation des 3 envs par la page Build (:7700), une à la fois, SUCCESS lu en fin de journal — preuve : journaux du 2026-11-12,
  `tasmota32s3-rdc-grenier` SUCCESS 01:24:34, `tasmota32s3-etage2-grenier` SUCCESS 01:47:36, `tasmota32p4-garage-serveur-modbus`
  SUCCESS 01:02:00 ; il a fallu déplacer `I2Cdevlib-Core` de `commun` vers `sans_mpu6050` dans le cenv (I2Cdev.h, requis par le MPU6050 des greniers)
- [ ] Commit `docs(volets): mode d'emploi du visuel et du reglage` (avec `platformio_override.ini` et
  `user_config_override.h` s'ils ont été réécrits par le build)

## A8 — Essais sur carte
- [ ] Grenier du 2e étage (`inverse` 1, bouton unique) : envoi par la page Build, dessin ouvert quand la trappe est ouverte,
  trappe qui bouge pendant la course, réglage complet par le bouton physique, durées relues dans le persist de la carte
- [ ] Trappe à MPU6050 actif (si le capteur est posé) : dessin qui suit l'angle, réglage sans arrêt en butée, durée du MPU
  affichée à côté ; sinon noter « MPU absent » et garder l'étape ouverte
- [ ] P4 du garage : dessin de la porte (`inverse` 1), chrono seul (journal : aucun `Shutter*` envoyé par le réglage)
- [ ] Grenier du RDC à sa mise en service (`inverse` 0, 2 boutons et bouton unique) : les 3 ouvertures, réglage de chaque volet
- [ ] Durées mesurées recopiées dans les persists du dépôt, si l'utilisateur le demande

## A9 — Revenir au plan d'origine `envs-grenier-rdc-sonoff-cave`
Ce plan est l'action A14 de `tasks/plans/envs-grenier-rdc-sonoff-cave.md`.
- [ ] Passer ce plan à `statut: clos`, puis cocher A14 et les étapes de réalisation d'A12 et d'A13 du plan d'origine, avec preuve
- [ ] Taper `/suivi suivre envs-grenier-rdc-sonoff-cave` et reprendre à sa prochaine étape

## Améliorations restantes
- [ ] [projet] Corriger en amont la boucle sans accolades de `CmndShutterButton` (`ShutterButton<x> 0`) : proposition à
  l'utilisateur, ce dépôt ne remonte pas chez arendst
- [ ] [projet] Façade du rideau si l'utilisateur la redemande (aujourd'hui : P4 seulement)

## Vérification
Bancs `banc_inclinaison.py`, `banc_reglage_volets.py`, `banc_demarrage.py`, `test_volets.mjs`, sondes
`test_volets_chrome.py` et `test_reglage_volets_chrome.py`, puis les essais d'A8. Un banc vert ne prouve ni la
solidification ni le rendu sur la vraie page de Tasmota : A8 tranche.
