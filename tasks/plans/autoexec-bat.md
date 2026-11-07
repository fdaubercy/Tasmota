---
chantier: autoexec-bat
titre: Onglet « autoexec.bat » de l'Assistant persist (modèle C)
objectif: Modifier ou ajouter des lignes à l'autoexec.bat d'une carte depuis l'Assistant persist, avec banque de commandes, avertissements (boucle de redémarrage, doublon persist, secret, commande inconnue) et envoi proposé à la carte
statut: actif
cree: 2026-11-03
maj: 2026-11-07
---
# Onglet « autoexec.bat » de l'Assistant persist

## Contexte
Spec validée par l'utilisateur le 2026-11-03 : `docs/superpowers/specs/2026-11-03-onglet-autoexec-bat-design.md` (à lire
avec ce plan). Maquettes : `outils_docs/autoexec_bat/` (**modèle C** + ajout du A). Plan d'origine :
`tasks/plans/energie-differentiel.md`, A14.

### Contraintes communes (valent pour chaque action)
- Python de PlatformIO (`~/.platformio/penv/Scripts/python.exe`), modules dans `outils_docs/scripts_python/outils_pc/`
  (même dossier que l'Assistant : imports voisins). Fichiers < 500 lignes. Un banc par module, code de sortie 0 = vert,
  témoin rouge sur mutant pour chaque règle de protection.
- Secrets **jamais envoyés à la page** (`***`), remis côté serveur. Écritures par `fichiers_berry_sauvegarde.Transaction`,
  refusées pendant un build (`builds_en_cours()` de l'Assistant : `None` ou non vide = refus).
- Fichier réécrit identique octet pour octet hors des lignes changées ; UTF-8 sans BOM ; fins de ligne d'origine.
- Ligne de plus de **510** caractères = avertissement (le firmware tronque, `xdrv_50_filesystem.ino::UfsExecuteCommandFileLoop`).
- Rouges (boucle de redémarrage, secret en clair) : **confirmation explicite** (« J'ai lu les N avertissements rouges »)
  à l'écriture ET à l'envoi ; oranges sans confirmation.
- Envoi : jamais pendant un build ; identité de la carte vérifiée avant ; jamais sans l'accord de l'utilisateur sur une
  vraie carte (A8). Renvois au code par `fichier::fonction` dans les documents durables.

### Points de vigilance (non couverts d'office, chacun a son test dans l'action qui le porte)
1. `Backlog` qui mêle un secret et d'autres commandes, l'utilisateur change une autre commande de la ligne → le secret
   est remis à sa place (A3).
2. Fichier en CRLF, ou sans fin de ligne finale → gardé tel quel à la réécriture (A3).
3. Secret dans une ligne en commentaire (`;Backlog … MqttPassword x`) → masqué, et avertissement « secret en clair » (A2, A3).
4. Fichier modifié sur disque (autre onglet, éditeur) entre la lecture et l'écriture → refus par empreinte, rien d'écrit (A3).
5. Carte injoignable, ou esclave `IP:port` derrière le maître → erreur claire, rien d'écrit sur la carte (A7).

## A1 — Commandes connues et commandes qui redémarrent (fichier figé + générateur)
Fichiers : créer `outils_pc/autoexec_commandes.py`, `outils_pc/test_autoexec_commandes.py`,
`outils_docs/schemas/commandes_tasmota.json`.
Produit : `charge(racine) -> {"connues": {NOM_MAJ: source}, "redemarrent": {NOM_MAJ: {"quand": "toujours"|"si-change",
"source": str}}}` ; `genere(racine, doc=None) -> dict` ; `verifie(racine) -> list[str]` (écarts entre le figé et le code).
Noms normalisés comme `build_sauvegarde::commande` (SO56 → SETOPTION56, chiffres finaux retirés sauf SetOption).
- [x] Banc rouge : `connues` contient HOSTNAME, TIMER, ADCPARAM, WEBSENSOR, SETOPTION146, REGLAGELOG (Berry, `tasmota.add_cmd` de `data/fs`) ; `redemarrent["HOSTNAME"]["quand"] == "toujours"` ; une commande des tables sans `restart_flag` (ex. TELEPERIOD) absente de `redemarrent` ; `verifie` sur une copie du figé amputée d'une commande → 1 écart
- [x] `genere` : noms des tables `k…Commands[] PROGMEM` (macros `D_CMND_…` résolues par `tasmota/include/i18n.h`, préfixes `D_PRFX_…`), fonction `Cmnd…` en regard (tableau de pointeurs dans le même ordre), `TasmotaGlobal.restart_flag = 2` dans son corps (sans condition → « toujours », sous un `if` → « si-change ») ; commandes Berry de `data/fs/*.be` ; doc `Commands.md` du dépôt `tasmota/docs` (`--doc` : téléchargée une fois, mentions restart/reboot croisées, source gardée) ; script `python autoexec_commandes.py --generer|--verifier`
- [x] Figé `commandes_tasmota.json` écrit, relu à la main pour HOSTNAME, TOPIC, SSID, IPADDRESS, TEMPLATE, MODULE, SETOPTION (classement vérifié dans le code) ; banc vert ; témoin : figé faux → `verifie` rouge — preuve : commits `7d786662a`, `53503d593` ; `test_autoexec_commandes.py` VERT (49 OK, dont 5 mutants rouges versionnés), `--verifier` code 0 ; figé : 1 145 connues, 81 qui redémarrent (72 « toujours », 9 « si-change ») ; HOSTNAME, SSID, PASSWORD, TEMPLATE, MODULE, RESTART, RESET « toujours », TOPIC et WIFITEST « si-change », IPADDRESS absent (ne redémarre pas) ; relecture : tous les constats traités

## A2 — Analyse d'un autoexec.bat
Fichiers : créer `outils_pc/autoexec_analyse.py`, `outils_pc/test_autoexec_analyse.py`.
Consomme : A1 `charge` ; `build_sauvegarde.commandes_posees(persist, texte_config)` et `build_sauvegarde.CONFIG_PERSIST`.
Produit : `lignes(texte) -> list[{"numero", "brut", "commentaire": bool, "commandes": [(nom_ecrit, valeur)]}]` (Backlog
découpé) ; `analyse(texte, persist, commandes, banque_noms=()) -> list[{"ligne": int, "type": "redemarrage"|"doublon"|
"secret"|"inconnue"|"longueur", "niveau": "rouge"|"orange", "message": str, "correction": str|None}]` ;
`SECRETS` (motif des commandes à secret).
- [x] Banc rouge sur le vrai `data/bureau/tasmota32-interrupteur-energie/autoexec.bat` + son persist : `SetOption146` → doublon orange (clé `diverses.affichageTempESP32`) ; lignes en commentaire `Password1` et `MqttPassword` → secret rouge ; aucune autre alerte sur `AdcParam1`, `WebSensor2 0`, les `Timer` ; ajout `Hostname X` → redémarrage rouge « toujours » ; `WebSesnor2 0` → inconnue orange, correction `WebSensor2` ; ligne de 511 caractères → longueur orange ; ligne propre → aucune entrée
- [x] Code : commentaires analysés pour les secrets seulement ; « si-change » → orange ; doublon d'après `commandes_posees` du persist de la carte ; commande la plus proche par `difflib.get_close_matches` sur `connues` + banque ; banc vert ; témoins rouges (secret en commentaire ignoré, doublon sans persist) — preuve : commit `fa67ed809` ; `test_autoexec_analyse.py` VERT (45 OK, 7 mutants rouges versionnés : secret en commentaire, doublon sans persist, « toujours » en orange, limite 511…) ; vrai `autoexec.bat` du différentiel : doublon SetOption146, secrets en commentaire, rien sur AdcParam1/WebSensor2/Timer ; relecture : approuvée

## A3 — Lecture masquée et écriture du fichier
Fichiers : créer `outils_pc/autoexec_fichier.py`, `outils_pc/test_autoexec_fichier.py`.
Consomme : A2 `lignes`, `SECRETS` ; `fichiers_berry_etat.dossier_carte(env)` ; `fichiers_berry_sauvegarde.Transaction`.
Produit : `lit(racine, env) -> {"texte": str (secrets en ***), "empreinte": str, "chemin": str, "existe": bool}` ;
`demasque(texte_page, texte_disque) -> str` (ValueError si un `***` n'a pas de valeur d'origine) ;
`diff(racine, env, texte_page) -> {"diff": str (masqué), "empreinte": str, "rouges": int}` ;
`ecrit(racine, env, texte_page, empreinte, rouges_lus: int, builds_en_cours) -> {"ecrit": True, "chemin": str}`.
- [x] Banc rouge (copie temporaire du dépôt) : aucun secret du vrai fichier dans `lit()["texte"]` ni dans `diff` ; aller-retour sans changement = octets identiques (CRLF et LF, avec et sans fin de ligne finale) ; vigilance 1 (`Backlog SSId1 A; Password1 ***` dont SSId1 change → Password1 d'origine remis) ; `***` nouveau sans origine → refus ; empreinte périmée → refus, rien d'écrit (vigilance 4) ; `rouges_lus` < rouges → refus ; build en cours → refus ; carte sans `autoexec.bat` → `existe: False`, création à l'écriture
- [x] Code : remise des secrets par commande et ordre d'apparition (spec, « Choix de Claude ») ; empreinte = sha256 du fichier sur disque ; écriture dans une `Transaction("autoexec")` ; banc vert ; témoins rouges (remise par position, masquage des commentaires retiré) — preuve : commits `66e0d745a`, `72600d9a0`, `7e550665e` ; `test_autoexec_fichier.py` VERT (112 OK, 17 mutants rouges versionnés), `test_autoexec_analyse.py` VERT ; remise par k-ième apparition de la commande (refus si des lignes portant un `***` sont ajoutées ou retirées), corps de `Rule`/`Br` et valeurs collées masqués, garde des `***` par ligne, empreinte HMAC à clé par processus ; 2 rondes de relecture, constats traités

## A4 — Banque de commandes (proposées et perso, modèles à champs)
Fichiers : créer `outils_pc/autoexec_banque.py`, `outils_pc/test_autoexec_banque.py`, `outils_docs/schemas/banque_autoexec.json`.
Produit : `charge(racine) -> list[entree]` ; `rend(entree, valeurs: dict) -> str` (ligne produite) ;
`valide_entree(entree) -> entree` (ValueError motivée) ; `ajoute(racine, entree, builds_en_cours) -> entree`.
Entrée : `{"nom", "categorie", "description", "modele": "Timer{n} {...}", "champs": [{"cle", "type":
"texte"|"nombre"|"liste"|"heure"|"jours"|"relais", "libelle", "defaut", "choix"?, "min"?, "max"?}], "origine":
"proposee"|"perso", "ajoutee": "AAAA-MM-JJ"}`.
- [x] Banc rouge : `rend(Timer, {n: 12, heure: "22:30", jours: "1111111", relais: 1, action: 0})` = la ligne `Timer12 {"Enable":1,"Mode":0,"Time":"22:30","Window":0,"Days":"1111111","Repeat":1,"Output":1,"Action":0}` ; heure `25:00` → ValueError ; entrée perso sans champ, nom en double, valeur par défaut secrète (motif `SECRETS`) → refus ; `ajoute` écrit en transaction, relu par `charge` — preuve : 884aed670 + 66fef3d01, test_autoexec_banque.py 222 OK, 17 temoins rouges, VERT ; re-revue sans reserve
- [x] Banque initiale : commandes de l'`autoexec.bat` du différentiel + SetOption (1, 55, 56, 57, 141, 146), Timer/Timers, AdcParam, WebSensor, LedPower/LedState/SetOption31, SerialLog/WebLog/MqttLog/SysLog, Latitude/Longitude, Timezone/TimeStd/TimeDst, PowerOnState ; chaque nom présent dans A1 `connues` (vérifié par le banc) ; banc vert — preuve : outils_docs/schemas/banque_autoexec.json (24 entrees, Latitude/Longitude vides), noms verifies dans connues par le banc

## A5 — Routes de l'Assistant
Fichiers : modifier `outils_pc/assistant_persist_web.py` (`fabrique_gestionnaire._traite_post`, `do_GET`, docstring des routes),
`outils_pc/test_assistant_persist_web.py`.
Routes : `GET /autoexec?env=` → A3 `lit` + A2 `analyse` ; `GET /autoexec/banque` ; `POST /autoexec/analyse {env, texte}` ;
`POST /autoexec/diff {env, texte}` ; `POST /autoexec/ecrit {env, texte, empreinte, rouges_lus}` ;
`POST /autoexec/banque/ajoute {entree}` ; `POST /autoexec/envoi/prepare {env}` et `POST /autoexec/envoi {env, jeton,
rouges_lus, redemarrer}` (A7). Env contrôlé (`_env_de` : env personnel du cenv seulement).
- [x] Banc rouge puis vert (`test_assistant_persist_web.py`) : chaque route répond, env hostile (`..`, inconnu) → 400, aucune réponse ne contient un secret du vrai fichier, écriture pendant un build simulé → refus ; bancs existants de l'Assistant toujours verts — preuve : commits `fbf8d05dc`, `e6591573f` ; routes dans `assistant_persist_autoexec.py` (serveur à ~434 lignes : délégation), banc `test_assistant_persist_autoexec.py` VERT (90 OK, 65 réponses sans le mot de passe inventé, 7 mutants rouges) ; nom mal formé → 400, env inconnu ou base → 404 (convention LookupError) ; envoi laissé à A7 ; banque absente tolérée (témoin) ; `test_assistant_persist_web.py` : 1 KO `GET /modele/etat` dû au `modele_persist.json` non commité de l'autre conversation ; relecture : approuvée

## A6 — Onglet de la page (modèle C + ajout du A)
Fichiers : créer `outils_pc/assistant_persist_page_autoexec.py` (CSS, HTML, JS de l'onglet) ; modifier
`outils_pc/assistant_persist_page.py` (barre d'onglets « Persist (créer, modifier, supprimer) » | « autoexec.bat »,
insertion par repères comme `build_page_defaut.py`) ; créer la sonde `outils_pc/test_assistant_persist_autoexec_chrome.py`.
- [x] Onglet : carte en haut (env, chemin, lignes, avertissements, Annuler, Enregistrer… (diff)) ; texte à gauche avec points de marge colorés (survol = détail) ; liste des avertissements dessous (clic → la ligne est sélectionnée dans le texte) ; analyse relancée à la frappe (anti-rebond 400 ms) ; ajout guidé à droite (recherche, formulaire des champs, aperçu, « Insérer à la ligne n ») ; « Tes commandes » + éditeur de modèle (nom, description, catégorie, ligne et champs typés, aperçu ; une ligne du texte absente de la banque propose « En faire un modèle », prérempli) ; à l'envoi, l'`autoexec.bat` de la carte s'il diffère est montré et confirmé (A7 `prepare`), case « redémarrer ensuite » décochée ; diff, case « J'ai lu les N avertissements rouges » quand N > 0, « Écrire dans le dépôt », puis « Envoyer à la carte (OTA)… » ; tout texte serveur par `textContent` — preuve : commits `56f55ea59`, `b36f28889` ; `assistant_persist_page_autoexec.py` (142 l.) + `assistant_persist_page_autoexec_js.py` (442 l.), barre d'onglets dans `assistant_persist_page.py` ; capture conforme à la maquette C ; aucun `innerHTML` (relecture) ; panneau d'envoi fermé dès que le texte change (relecture, 1 ronde)
- [x] Sonde Chrome verte (Python de PlatformIO, dépôt d'essai temporaire) : onglet affiché, points de marge et liste concordent, clic sur un avertissement → sa ligne, insertion d'une minuterie par formulaire, écriture refusée sans la case puis acceptée, aucun secret dans la page, aucune erreur JS ; bancs de la page de l'Assistant toujours verts — preuve : `test_assistant_persist_autoexec_chrome.py` ROUGE d'abord (51 échecs) puis VERT, témoins `garde-envoi` et `redemarrer` détectés ; `test_assistant_persist_autoexec.py` VERT (124 OK) ; `test_assistant_persist_page_chrome.py` 4 KO et `test_assistant_persist_web.py` 1 KO, tous dus à `serveur.voieReseau` absent du `modele_persist.json` commité (persist de la cave, commit `7812c349c`, antérieur à A6 ; vérifié en relecture)

## A7 — Envoi à la carte
Fichiers : créer `outils_pc/autoexec_envoi.py`, `outils_pc/test_autoexec_envoi.py`.
Consomme : `build_envs` (adresse de l'env, `adresse_par_maitre`), `build_ota_maitre.joint_par_maitre`, `build_ota_http._get`,
`build_ota_fs.envoie_fs_ota(env, ip, dossier, sauvegardes, rapporte, fichiers=["autoexec.bat"], redemarrer=...)`.
Produit : `prepare(racine, env) -> {"adresse", "hostname_carte", "sur_carte": str|None (masqué), "ecart": bool, "jeton"}` ;
`envoie(racine, env, jeton, rouges_lus, redemarrer, builds_en_cours) -> {"envoye": True, "sauvegarde": chemin}`.
- [x] Banc rouge (`build_ota_carte_simulee.py`) : nom d'hôte de la carte ≠ persist → refus sans envoi ; fichier de la carte différent → `ecart: True`, copie sauvegardée avant l'envoi ; carte injoignable et esclave `IP:port` sans maître → erreur claire, rien d'envoyé (vigilance 5) ; jeton périmé, build en cours ou rouges non lus → refus ; `redemarrer=False` → aucun `Restart` — preuve : `test_autoexec_envoi.py` rouge d'abord (ModuleNotFoundError ; banc des routes : 21 KO), puis VERT (79 OK, 11 témoins rouges : identité, jeton périmé, HMAC, build, build recontrôlé, rouges, joint_par_maitre, sauvegarde après envoi, sur_carte non masqué, Sleep 0 retiré, absent sans relecture) ; carte simulée sur 127.0.0.1 seulement
- [x] Code : `Status 5` comparé au hostname du persist ; `autoexec.bat` de la carte lu par `/ufsu?dir=0&download=/autoexec.bat` et gardé dans les sauvegardes de l'Assistant ; envoi par `envoie_fs_ota` sur un dossier temporaire ; banc vert ; témoin rouge sans contrôle d'identité — preuve : commits `ecdb76fae`, `874b8a712`, `7a8400e42` ; `autoexec_envoi.py` (prepare/envoie, jeton HMAC 10 min, copie de la carte dans `autoexec_cartes/<env>/` avant l'envoi, `Sleep 0` du maître pour `IP:port` remis sur tous les chemins), routes `/autoexec/envoi/prepare` et `/autoexec/envoi` dans `assistant_persist_autoexec.py` ; relecture : 1 ronde, puis approuvée

## A8 — Essai réel sur le différentiel (avec l'utilisateur)
- [x] Page relancée par l'annuaire ; lecture du vrai fichier : avertissements attendus (doublon SetOption146, secrets en commentaire), aucun secret dans la page ; ajout d'une ligne par formulaire, diff, écriture dans le dépôt relue — preuve : Assistant relancé à 19:45 le 2026-11-05 ; lecture réelle : 2 rouges, doublon `SetOption146`, 0 secret sur 2 dans la réponse ; **retrait** de `SetOption146 ON` et d'une ligne vide écrit par l'utilisateur dans la page à 19:47:06 (copie `20261105-194706-195807-autoexec`), `git diff` relu : 2 lignes `-`, aucune `+`, secrets intacts ; l'ajout par formulaire n'a été prouvé que par la sonde, sur dépôt d'essai ; fichier non commité
- [x] Après accord : envoi à la carte (192.168.0.49), fichier relu sur la carte identique, carte non redémarrée (case décochée) — preuve : **pas d'envoi réel, décision de l'utilisateur du 2026-11-05 (« N'envoie pas. Considérons que cela fonctionne »)** ; essai dans la page : refus au contrôle d'identité, la carte répond `DISJONCTEUR-DIFFERENTIEL-BUREAU` à `Status 5`, le persist du dépôt dit `DISJONCTEUR-DIFF-BUREAU` (nom raccourci par `bf319d048`, pas encore reçu par la carte), rien d'envoyé ; envoi prouvé seulement sur carte simulée (`test_autoexec_envoi.py`) ; fichier sur la carte non relu

## A11 — Commande déjà présente et suppression d'une ligne (demande du 2026-11-05, pendant A8)
- [x] Sonde rouge puis verte (`test_assistant_persist_autoexec_chrome.py`) : commande de la banque déjà dans le fichier → « Remplacer par la nouvelle » ou « Enlever l'existante » à la place d'« Insérer » ; dans une `Backlog`, seul son segment part et le secret reste remis à l'écriture ; « Enlever » sur un doublon du persist ; « Supprimer la ligne N » retire la bonne ligne ; panneau d'envoi fermé sur chaque nouveau chemin ; retrait d'une ligne à `***` alors qu'il en reste une : refus affiché au diff ; témoins rouges — preuve : `test_assistant_persist_autoexec_chrome.py` ROUGE d'abord puis VERT, 6 témoins détectés (`backlog-entiere`, `ligne-decalee`, `sans-achange`, `perso-direct`, `garde-envoi`, `redemarrer`) ; essai sur le vrai fichier par les fonctions JS (`Latitude` → `Backlog Longitude 3.085796;`), rien d'écrit ; « Insérer quand même » gardé après relecture (Delay, Publish se répètent)
- [x] Code : `assistant_persist_page_autoexec_lignes_js.py`, boutons dans `assistant_persist_page_autoexec.py`, `commande` dans les avertissements (`autoexec_analyse.py`) ; bancs `test_autoexec_analyse.py` et `test_assistant_persist_autoexec.py` verts — preuve : `assistant_persist_page_autoexec_lignes_js.py` (97 l.), `commande` dans `autoexec_analyse.analyse` ; `test_autoexec_analyse.py` et `test_assistant_persist_autoexec.py` VERTS ; relecteur-pages-web : 0 critique, 3 importants corrigés ; mineurs reportés : `splitlines` Python contre `\n` JS, boutons `Corriger` non désactivés pendant l'analyse

## A9 — Documentation et clôture
- [x] `outils_docs/README.md` (§ Assistant persist : onglet autoexec.bat), carte des documents de `CLAUDE.md`, tuile de l'annuaire (`annuaire_registre.py`), README des maquettes (réalisé) ; `verifie_references_docs.py` code 0 — preuve : § « Onglet « autoexec.bat » » du README, carte des documents de `CLAUDE.md`, tuile `annuaire_registre.py`, `outils_docs/autoexec_bat/README.md` ; `verifie_references_docs.py` code 0 ; `test_annuaire.py` VERT
- [x] A14 du plan `energie-differentiel` cochée avec renvoi ici ; commit — preuve : A14 cochée dans `tasks/plans/energie-differentiel.md`, avec renvoi ici

## A10 — Retour au plan d'origine « energie-differentiel »
- [ ] Reprendre `tasks/plans/energie-differentiel.md` : A14 cochée avec renvoi ici, puis ses étapes restantes (thermomètre A11, retour au plan « jauges-cuve » A10)

## Améliorations restantes
- [x] [projet] Envoi par MQTT (`build_ota_mqtt`) pour une carte injoignable en HTTP — preuve : fait par le plan `tasks/plans/autoexec-mqtt-tapp.md` A1 (commits 16c1a9e74, 2dcc05b54, ebcd460e3, eeb4a8306), test_autoexec_envoi.py et sonde test_assistant_persist_autoexec_chrome.py VERTS ; essai sur carte : A10 de ce plan-la
- [x] [projet] Commandes connues par env (gardes `USE_*` du firmware compilé), si les fausses alertes « inconnue » gênent — preuve : fait par `tasks/plans/autoexec-mqtt-tapp.md` A3 et A4 (alerte orange « absente », seulement si toutes les gardes sont fausses ; commits bb60907ce a d21cfea27, 367c5389f, 9a74435e2), test_autoexec_commandes.py, test_autoexec_gardes.py, test_autoexec_analyse.py VERTS

## Vérification
Bancs `test_autoexec_*.py`, `test_assistant_persist_web.py`, sonde `test_assistant_persist_autoexec_chrome.py`, puis tous les
`test_assistant_persist_*.py` (Python de PlatformIO, code 0 = vert). Sur la carte (A8) : fichier relu par
`/ufsu?download=/autoexec.bat`, `Status 2` inchangé (pas de redémarrage).
