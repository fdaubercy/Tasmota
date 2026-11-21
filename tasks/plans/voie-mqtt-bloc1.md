---
chantier: voie-mqtt-bloc1
titre: Voie MQTT, bloc 1 (bureau) et relevés de mémoire du P4
statut: actif
cree: 2026-11-21
maj: 2026-11-21
source: cheeky-noodling-abelson.md
objectif: Finir le travail de bureau du plan voie-mqtt (recalage, schéma, modèle, documentation) et relancer la surveillance de la mémoire Berry du P4
famille: voie-mqtt
parent: voie-mqtt
---
## Contexte

Plan `tasks/plans/voie-mqtt.md` à 87 %. L'utilisateur a demandé le bloc 1 (travail de bureau sans risque) et les relevés mémoire du P4.

Déjà fait dans cette conversation, rien n'est commité :
- `data/fs/controleMqttLiaison.be::etat` : un `POWER` valide reçu marque l'esclave en ligne (`self.en_ligne[nom] = true`) avant le recalage. Avant, si un LWT `Offline` ancien restait, le recalage finissait en « hors_ligne ». Banc `banc_mqtt_liaison` vert, avec un nouveau cas et un mutant (« etat recu sans remettre l'esclave en ligne »). Le mutant « recalage pendant un ordre en attente » est adapté au nouveau texte. `verifie_berry.py` : 0 erreur.
- `outils_docs/schemas/persist.schema.json` régénéré : +3 lignes (`required: commande` sous `relais.mqtt`). La dérive de 460 lignes a déjà été absorbée. `--valide` : 14 persists OK, code 0.
- `outils_docs/schemas/modele_persist.json` : bloc `drivers.liaisonMqtt` posé dans `puces.ESP32P4.ajouts`, avec `activation` OFF, `esclaves` vide et les seuils `garde` du P4. Il est écrit par `assistant_persist_modele.ecrit_modele` (sauvegarde horodatée). `ecarts()` : plus aucune clé `liaisonMqtt` nouvelle, 0 disparue, 0 divergente. Ce n'est pas la fusion automatique, qui aurait recopié les esclaves du P4 avec `activation` ON, ainsi que des clés d'autres chantiers.
- Bancs de l'assistant (`test_assistant_persist_modele`, `_generation`, `_fidelite`) : rouges AVANT ma modification (modèle de HEAD) avec les mêmes vérifications en échec. Cause : clés d'autres chantiers (volets, portail, écrans, `_incertain` du persist du portail) et parc passé à 14 persists. `_creation` est vert. Je n'y touche pas, je le signale.
- Build du P4 lancé par la page Build (compiler + upload COM4) à environ 05:55, encore en cours au passage en mode plan.

## A1 — Valider le firmware du P4

- [x] Fin du build lue sur `GET /execution` et à la fin du journal de l'env (SUCCESS, aucune erreur) — preuve : build lancé par la page Build à ~05:55, `/execution` `en_cours: false` (numéro 15993), journal `20261121-060030-tasmota32p4-garage-serveur-modbus-upload.log` : « Build/upload réussi », `[SUCCESS] Took 1973.31 seconds`
- [x] Heure de `firmware.bin` postérieure à la modification de `controleMqttLiaison.be`, et P4 redémarré (`Status 11`, uptime court) — preuve : `firmware.bin` 06:31:27 contre `controleMqttLiaison.be` 05:58:48 ; P4 à 06:34, `Status 11` uptime 17 s, version 16.0.0.5 (Serveur de Garage)
- [x] Sur carte : `ReglageMqttLiaison` répond, les 3 esclaves sont en ligne, `relais_lies` lu par `Br` (`pompe/POWER1` -> 25, `projecteur/POWER1` -> 24) — preuve : `ReglageMqttLiaison` répond ; `en_ligne` = pompe true, projecteur true, cuve false (la cuve est hors ligne, comme les jours précédents) ; `relais_lies` lu après le premier état reçu (table construite à la demande, nil avant) : `{'pompe/POWER1': [25], 'projecteur/POWER1': [24]}`
- [x] Recalage toujours bon : un cycle local de la pompe (ON puis OFF par HTTP, pompe branchée), `POWER25` du P4 suit, 0 `cmnd` publié (`essai_echo_pompe.py` du scratchpad) — preuve : `essai_echo_pompe.py` à 06:35 : pompe ON puis OFF par HTTP, `POWER25` du P4 ON puis OFF, 0 `cmnd` publié après chaque changement, « BILAN OK aucun echo »

## A2 — Relevés de mémoire Berry du P4 (lecture seule)

- [x] `sonde_fuite.py` du scratchpad relancée en arrière-plan juste après le démarrage dû au flash, sortie dans un nouveau journal (`sonde_fuite_20261121.log`), 8 h — preuve : lancée à 06:34:54, 77 s après le démarrage du P4 flashé ; journal `scratchpad/sonde_fuite_20261121.log` ; à 06:45:10 reprise en processus DÉTACHÉ (PID 9524, hors conversation, survit à la fermeture de VS Code) : script `%LOCALAPPDATA%\outils_tasmota\mesures_mqtt\sonde_fuite_p4.py`, journaux `sonde_fuite_p4_20261121.log` (relevés 06:34 à 06:45 repris) puis `sonde_fuite_p4_sortie.log`, 8 h (fin vers 14:45) ; ancienne tâche de fond arrêtée, un seul processus de sonde en vie
- [x] Premier relevé lu (berry, obj, tas, pente) pour confirmer que la sonde tourne — preuve : 06:34:54 `up=77 berry=120 obj=2010 tas=247 pente=0.00` ; 06:35:24 `up=107 berry=120 obj=2016 tas=246 pente=0.00`
- [ ] Bilan rendu à l'utilisateur au fil de l'eau : pente, captures déclenchées (seuil 0,2 Ko/s), redémarrages détectés. Rien n'est corrigé sans son accord

## A3 — Documentation

- [x] `outils_docs/CARTE_MODULES_BERRY.md` régénéré par `berry/carte_modules_berry.py` (sortie déterministe), diff relu — preuve : `carte_modules_berry.py` relancé le 2026-11-21 (74 modules, 14 cartes), `git diff` vide : la carte contenait déjà `liaisonMqtt` (4 mentions)
- [x] `outils_docs/PROTOCOLE_MODBUS.md` : court paragraphe sur la voie MQTT, avec renvoi au README § « Voie MQTT maître/esclaves » (les esclaves MQTT n'ont ni repli ModBus ni fiche) — preuve : § 11 ajouté à `PROTOCOLE_MODBUS.md` (cadre, absence de repli, recalage, réglage `ButtonTopic`/`SwitchTopic`)
- [x] `CLAUDE.md` du dépôt, entrée « Voie MQTT maître/esclaves » : état au 2026-11-21 (A7 et A9 validés sur carte, recalage, pompe, mémoire Berry non reproduite le 20/11). Mes passages seulement, indexés par hunks — preuve : entrée « Voie MQTT maitre/esclaves » de `CLAUDE.md` réécrite (la phrase « essais NON termines au 2026-11-19 » était périmée) ; fichier sans autre modification en cours
- [x] `python outils_docs/scripts_python/maintenance/verifie_references_docs.py` : 0 défaut — preuve : « 31 document(s), 0 defaut(s) » le 2026-11-21, code 0
- [x] Caractères de contrôle absents des fichiers touchés (`grep -c -P` x00-x08, x0b, x0c, x0e-x1f), d'après la leçon du 2026-11-15 — preuve : `grep -c -P` = 0 sur `CLAUDE.md`, `PROTOCOLE_MODBUS.md`, ce plan (à refaire sur les fichiers ajoutés ensuite)
- [x] `tasks/lessons.md` : leçons d'A9 (écho Node-RED à chercher appareil par appareil ; fusion du modèle qui recopierait des esclaves actifs) — preuve : 3 entrées du 2026-11-21 ajoutées en fin de `tasks/lessons.md` (écho Node-RED, fusion du modèle, LWT Offline ancien)

## A4 — Plan voie-mqtt et commit

- [x] `tasks/plans/voie-mqtt.md` : A4 ligne 63 et A10 (doc, références, firmware validé, leçons) cochés avec preuves, `maj: 2026-11-21`, index régénéré — preuve : `voie-mqtt.md` du 2026-11-21 : étape schéma/modèle d'A4 et 3 des 5 étapes d'A10 (documentation, références, firmware) cochées avec preuves, `maj: 2026-11-21` ; reste en A10 le portail et les leçons du portail (laissées ouvertes)
- [x] Agents `controleur-secrets` et `verificateur-solidification` (un `.be` de `data/` dans le lot), `relecteur-docs` au jugement ; rapports lus — preuve : `controleur-secrets` : aucun bloquant, 10 fichiers du lot ; `verificateur-solidification` : solidifiable, aucun bloquant ; `relecteur-docs` : 2 corrections retenues (cuve et projecteur ont du Berry, limite du LWT à l'arrêt du broker), appliquées à `PROTOCOLE_MODBUS.md` § 11, `verifie_references_docs.py` 0 défaut après correction ; 3 points écartés après vérification (S2X cité par `tasks/plans/envs-grenier-rdc-sonoff-cave.md`, lignes 31 et 40 du README = sommaire non touché, `ButtonTopic` à 0 = règle et non constat)
- [x] Commit proposé à l'utilisateur (fichiers nommés un par un, hunks pour les fichiers partagés) ; push seulement s'il le demande, après `preparateur-push` — preuve : commit `5394eb2c9` (10 fichiers nommés un par un, accord de l'utilisateur « oui commite, sans pousser »), `tasks/README.md`, organigramme, persist de la cave et fichiers FTP laissés hors du commit ; non poussé

## A5 — Retour au plan d'avant (`voie-mqtt`)

- [ ] Résultat de ce bloc reporté dans `tasks/plans/voie-mqtt.md` : note datée du 2026-11-21 (recalage corrigé, schéma et modèle à jour, sonde mémoire relancée), étapes concernées cochées avec preuves, `maj:` à jour
- [x] Conversation rattachée de nouveau à `voie-mqtt` (`/suivi suivre voie-mqtt`), puis `/suivi detacher` sur ce plan-ci ; la barre d'avancement montre `voie-mqtt` en premier — preuve : `/suivi` n'est pas lançable par moi ; rattachement obtenu en éditant `tasks/plans/voie-mqtt.md` avec l'outil Edit (lien `voie-mqtt-bloc1` ajouté à `liens:`), ce qui rattache la conversation à ce plan ; `~/.claude/suivi-plan/conversations/dca3c399-….json` donne `fichier: tasks/plans/voie-mqtt.md` le 2026-11-21 ~06:47
- [ ] Ce plan passé en `statut: clos` quand A1 à A4 sont cochées, index `tasks/README.md` régénéré (`node .claude/hooks/index_plans.mjs`)
- [ ] Reste de `voie-mqtt` relu et proposé à l'utilisateur, dans l'ordre : mémoire Berry du P4 (résultat de la sonde d'A2), essai du portail de jardin et du volet 3 en sa présence, puis A10 (documentation, firmware validé, leçons). Rien du portail n'est lancé sans lui

## Vérification

- `banc_mqtt_liaison.py` vert (mutants compris), `verifie_berry.py` à 0 erreur, `genere_schema_persist.py --valide` code 0.
- Firmware : journal de la page Build en SUCCESS, puis essai sur carte A1.
- Docs : `verifie_references_docs.py` à 0 défaut.
- Mémoire : journal de la sonde lu, pente chiffrée.

## Améliorations restantes

- [ ] [projet] Bancs de l'assistant persist rouges avant ce lot (clés des volets, du portail, des écrans, `_incertain` du persist du portail) : à traiter par leurs chantiers
- [ ] [projet] Essai du portail de jardin et du volet 3 en présence de l'utilisateur (A10 du plan voie-mqtt)
- [ ] [conversation] Si la sonde capture une montée : diagnostic (systematic-debugging) avant toute correction
