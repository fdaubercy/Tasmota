---
chantier: sauvegarde-config-cartes
titre: Onglet « Sauvegarde configuration » de la page build (modèle B)
statut: actif
cree: 2026-11-03
maj: 2026-11-03
source: squishy-imagining-raven.md
objectif: Sauvegarder, comparer, modifier paramètre par paramètre et restaurer la configuration (/dl : Settings + .drvset*) de chaque carte depuis la page build
---
# Onglet « Sauvegarde configuration » de la page build

## Contexte
Demande du 2026-11-02, reprise en A12 du plan `energie-differentiel` : sauvegarder la configuration d'une carte de la
liste des envs, la restaurer, modifier un fichier de sauvegarde par paramètre. Décisions de l'utilisateur du 2026-11-03 :
**modèle B** (`outils_docs/sauvegarde_config/modele-B.png` : carte en haut, historique à gauche, paramètres repliés par
thème à droite avec filtre) ; onglet nommé **« Sauvegarde configuration »**.

Établi pendant l'étude :
- `/dl` (`tasmota/tasmota_support/settings.ino::SettingsConfigBackup`) = en-tête `/.settings`, Settings 4 096 o, puis
  les `/.drvsetNNN` (en-têtes de 16 o), le tout XORé ; restauration par `GET /rs?` puis `POST /u2` (fichier).
- **decode-config** (tasmota/decode-config, LGPL-3.0, PyPI `16.0.0.0`, dépendances `requests`, `configargparse`,
  `paho-mqtt`) fait tout hors ligne : `.dmp` → JSON (groupes Wifi, Mqtt, Timer, Rules, Sensor, Power, Management…,
  fichiers `.drvset*` gardés en hexa dans la clé `settings`), JSON modifié + `.dmp` source → nouveau `.dmp` (XOR, CRC).
  Il refuse une version plus récente que la sienne sauf `--ignore-warnings`. La disposition de Settings n'a pas bougé
  depuis 15.6.0.3 (`tasmota_types.h` identique entre 16.0.0.1 et 16.0.0.2 du fork) : ce drapeau n'est passé que pour
  une liste de versions vérifiées.
- `configargparse` et `paho` manquent au Python de PlatformIO : decode-config vivra dans un **environnement Python dédié**
  (`%LOCALAPPDATA%\outils_tasmota\decode_config\`), version épinglée, appelé en sous-processus. Rien n'est ajouté au
  Python de PlatformIO ni au dépôt (l'amont a sorti decode-config de son dépôt).
- Une sauvegarde contient les mots de passe en clair : dossier `outils_docs/sauvegardes_cartes/<env>/`, ignoré par git.
- Le persist et l'`autoexec.bat` reposent une partie des réglages à chaque démarrage : une valeur qu'ils portent,
  restaurée par l'onglet, sera réécrite au démarrage suivant (dit dans l'aide de l'onglet).

## A1 — decode-config éprouvé (aucune écriture sur une carte)
- [x] `outils_pc/decode_config.py` (et non `maintenance/` : la page build l'importe, même dossier) : crée l'environnement dédié, installe `decode-config==16.0.0.0`, `--verifier` (code 0 si utilisable) — preuve : environnement créé dans `%LOCALAPPDATA%\outils_tasmota\decode_config\venv`, `utilisable()` vrai (2026-11-03)
- [x] Sur la sauvegarde `/dl` du différentiel : `AdcParam1` modifié → relu modifié dans le nouveau `.dmp` ; `.drvset003` (calibrage 310/15963/124194) présent et intact — preuve : `decode_config.ecrit_copie` sur le `/dl` du 2026-11-03 (4 800 o, 16.0.0.2) : 6 octets changés (texte + CRC), calibrage relu 310/15963/124194. **Défaut de decode-config trouvé** : restaurer le JSON COMPLET efface `influxdb_host32` et `influxdb_bucket32` (cause : la clé `button_text`, trouvée par dichotomie) ; d'où écriture des seules clés modifiées, relecture comparée à l'attendu et contrôle des textes bruts inconnus du paquet (`SET_APBSSID1/2`, ajoutés en 15.5) ; une modification de `button_text` est refusée et rien n'est gardé (essayé). Copie sans modification = simple copie du fichier
- [x] Version vérifiée (16.0.0.2) décodée avec le drapeau ; version inconnue refusée en lecture des paramètres — preuve : `decode_config.VERSIONS_VERIFIEES` ; liste vidée → `ValueError` « version 16.0.0.2 non vérifiée » (essai du 2026-11-03)

## A2 — Module serveur `outils_pc/build_sauvegarde.py`
- [x] Prise d'une sauvegarde par `/dl` (`build_ota_http._get`, adresse `IP` ou `IP:port` résolue comme les envois OTA) ; fichier `AAAAMMJJ-HHMMSS_<origine>.dmp` + fiche `.json` (version, origine, adresse, taille) dans `outils_docs/sauvegardes_cartes/<env>/` ; ligne dans `.gitignore` — preuve : `build_sauvegarde.prend` ; sur la vraie carte, `20261103-053032_manuelle.dmp` (4 800 o, 16.0.0.2) ; `.gitignore` : `outils_docs/sauvegardes_cartes/` (`git check-ignore` le confirme) ; banc : IP:port → redirection du maître d'abord
- [x] Liste des sauvegardes d'un env (date, version, origine) ; paramètres d'une sauvegarde rangés par groupe decode-config, mots de passe remplacés par `***` — preuve : vraie carte : 22 groupes, `sta_pwd`/`mqtt_pwd` à `***`, `/.drvset000` et `/.drvset003` listés ; banc : aucun mot de passe en clair dans la réponse, témoin rouge sans masquage
- [x] Copie modifiée : nouveau `.dmp` (origine « modifiée ») écrit par decode-config, les `***` remplacés côté serveur par les vraies valeurs ; l'original n'est jamais réécrit ; version non vérifiée → refus — preuve : banc VERT (texte commun, champ binaire, InfluxDB et interrupteur 9 intacts, mot de passe `***` gardé, originale intacte, relecture fautive refusée) ; vrai `.dmp` : hostname, `button_text` et `tele_period` modifiés, aucun autre écart, calibrage intact. **Défaut corrigé en route** : decode-config tronque la réserve de textes d'un ESP32 en écrivant un texte commun (cause réelle de la perte InfluxDB) → textes écrits par `decode_config._pose_textes` à l'indice ESP32, CRC16/CRC32 recalculés (formules vérifiées sur le vrai fichier) ; témoin rouge sans cette écriture
- [x] Comparaison de deux sauvegardes, ou d'une sauvegarde et de la carte en ligne (`/dl` pris dans un fichier temporaire) : liste des écarts par paramètre — preuve : vraie carte : 0 écart (10,9 s) ; banc : écart d'une copie, mot de passe changé affiché masqué
- [x] Restauration : sauvegarde « avant restauration » d'abord, écarts montrés, empreinte confirmée, puis `GET /rs?` + `POST /u2`, retour de la carte attendu (`build_ota_http._attend_retour`), relecture et comparaison ; refusée pendant un envoi de la série (409) — preuve : banc sur carte simulée : jeton faux refusé sans envoi, `/rs` puis `/u2`, sauvegarde d'avant portant l'ancienne config, 0 écart relu, autre puce refusée sans envoi

- [x] Relecture par un sous-agent, défauts réels corrigés — preuve : 10 corrigés le 2026-11-03 : clé réseau Zigbee `zb_precfgkey_*` (non vide sur la vraie carte) et variantes ESP8266 envoyées EN CLAIR à la page → masquage par motif `build_sauvegarde.SECRET` (11 clés, contrôlées par le banc) ; env « .. » refusé ; coupure de `/u2` au redémarrage plus annoncée comme échec, sauvegarde d'avant nommée dans toute erreur ; page HTML refusée (CRC32 exigé) ; capacité de la réserve de textes comptée comme la carte ; caractère nul refusé ; mot de passe Wi-Fi saisi = 1er réseau ; délai de 120 s sur decode-config ; échec de la sauvegarde « avant flash » écrit au suivi ; alerte « autre carte » quand le nom d'hôte diffère ; copie identique refusée. `test_build_sauvegarde.py` VERT (54 contrôles), sonde Chrome VERTE

## A3 — Routes de `build_web.py`
- [x] `GET /sauvegardes?env=`, `GET /sauvegarde?env=&fichier=`, `POST /sauvegarde/prendre`, `/sauvegarde/comparer`, `/sauvegarde/copier`, `/sauvegarde/restaurer` ; nom de fichier contrôlé (pas de `..`, dossier de l'env seulement) ; docstring des routes à jour — preuve : `build_web.py` (500 lignes, traitement dans `build_sauvegarde.traite_post`) ; `test_build_web.py` VERT 139/139 (deux essais) ; banc : refus pendant un envoi, une opération à la fois, noms hostiles refusés

## A4 — Onglet de la page (modèle B)
- [x] `outils_pc/build_page_sauvegarde.py` (CSS, HTML, JS de l'onglet), inséré dans `build_page.PAGE` par des repères comme `build_page_defaut.py` ; bouton « Sauvegarde configuration » dans la barre d'onglets ; exception des lignes de `build_page.py` mise à jour dans `CLAUDE.md` — preuve : `build_page.py` 1 223 lignes (exception de `CLAUDE.md` mise à jour) ; sonde Chrome VERTE
- [x] Carte choisie en haut (adresse, version, en ligne), « Sauvegarder maintenant », « Restaurer la sélection » ; historique à gauche (Copier, Comparer à la carte ou à une autre sauvegarde) ; paramètres repliés par thème à droite (libellés français, compte, filtre, modifiés surlignés) — preuve : sonde Chrome VERTE (historique, thèmes français repliés, filtre, modifié surligné, copie, comparaison) ; capture du 2026-11-03
- [x] Restauration : fenêtre de confirmation avec la liste des écarts ; avancement et résultat dans l'onglet ; texte d'aide (persist et `autoexec.bat` reposent leurs valeurs au démarrage) — preuve : `<dialog>` des écarts (paramètre, carte, après restauration, marque « ↻ démarrage », alerte de nom d'hôte, Annuler/Échap) ; bloc d'avancement sur les étapes du serveur (`build_sauvegarde::EN_COURS`, relu par `GET /sauvegardes`) puis résultat ; sonde Chrome VERTE (Annuler = rien envoyé, étapes « fait, fait, cours », résultat nommant la sauvegarde d'avant) ; banc MQTT : 4 étapes suivies, rien en cours après un échec. En route : `decode_config.utilisable` lançait un sous-processus à chaque relecture de la liste (> 1 s), gardé une fois vrai

## A5 — Sauvegarde « avant flash »
- [x] Un upload ou un erase_upload série prend aussi une sauvegarde `/dl` d'origine « avant flash », à côté de la copie de `/.drvset003` (`build_drvset.sauvegarde`) ; carte injoignable = rien de bloqué — preuve : `build_serie.Serie._sauve_drvset` ; banc : calibrage ET configuration « avant flash », sans adresse rien de bloqué

## A6 — Bancs
- [x] `outils_pc/test_build_sauvegarde.py` : carte simulée (`build_ota_carte_simulee.py` + `/dl`, `/rs`, `/u2` de configuration), vrai decode-config ; masquage et remise des mots de passe, refus d'une version non vérifiée, sauvegarde prise avant restauration, nom de fichier hostile refusé ; témoins rouges sur mutants — preuve : VERT (3 min) ; témoins rouges : masquage, écriture directe des textes
- [x] Sonde Chrome `outils_pc/test_build_page_sauvegarde_chrome.py` (rendu, thèmes repliés, filtre, modifié surligné, confirmation) ; bancs existants de la page build toujours verts — preuve : VERTE ; `test_build_web.py`, `test_build_ota_fs.py`, `test_build_drvset.py`, `test_build_page_defaut_chrome.py` VERTS

## A7 — Essai sur le différentiel (avec l'utilisateur)
- [x] Sauvegarde manuelle, comparaison à la carte (aucun écart attendu), copie modifiée relue — preuve : sur le différentiel (192.168.0.49) : `20261103-062936_manuelle.dmp`, 0 écart avec la carte (8,6 s) ; copie modifiée (hostname, `button_text`, `tele_period`) relue sans autre écart, calibrage 310/15963/124194 intact ; page Build relancée, `GET /sauvegardes` sert les sauvegardes réelles
- [x] Restauration de la sauvegarde d'origine sur la carte, après accord : carte revenue, calibrage 310/15963/124194 et Total relus intacts, minuteries présentes — preuve : 2026-11-03 06:33-06:34, par les routes de la page (`/sauvegarde/comparer` 0 écart, `/sauvegarde/restaurer` en 27 s) : sauvegarde `20261103-063400_avant-restauration.dmp` prise d'abord, carte revenue, PowerCal 310, VoltageCal 15963, CurrentCal 124194, Total 564,246, 11 minuteries actives. Écarts relus après le redémarrage : `SetOption1`, `use_wifi_scan`, niveaux de log série et web (reposés par l'`autoexec.bat`, attendu), et **relais revenu ON** alors que la sauvegarde le portait OFF et que les minuteries le tiennent OFF jusqu'à 08:00 (`PowerOnState 3`) : remis à OFF à la main

## A10 — Remarques de l'utilisateur du 2026-11-03
- [x] Paramètres plus longs que leur zone affichés sur plusieurs lignes ; valeur JSON : une icône à côté du champ propose la vue formatée — preuve : champs en `textarea` à la hauteur de leur contenu (`sAjuste`), icône `{ }` sur les listes et objets (vue formatée, retour sur une ligne, pas une modification) ; sonde Chrome VERTE (`flag3` sur 199 px, icône aller-retour), capture du 2026-11-03
- [x] Historique : cases pour choisir les sauvegardes à supprimer du dépôt (`.dmp` et fiche `.json`), suppression confirmée (demande du 2026-11-03) — preuve : case par ligne et « tout choisir », « Supprimer la sélection (n) » confirmé, `POST /sauvegarde/supprimer` (`build_sauvegarde.supprime` : tous les noms contrôlés avant d'effacer) ; banc VERT (59 contrôles : nom invalide → rien d'effacé) ; sonde Chrome VERTE
- [x] Choix de la sauvegarde à restaurer explicite (demande du 2026-11-03) : le bouton nomme la sauvegarde choisie (date · origine), clic sur une ligne pour en changer ; distinct des cases de suppression — preuve : bouton « Restaurer : 02/11/2026 10:00 · avant flash », change au clic sur une autre ligne ; aide sous le titre de l'historique ; sonde Chrome VERTE
- [x] Relais revenu ON après la restauration (sauvegarde OFF, `PowerOnState 3`, minuteries OFF jusqu'à 08:00) : cause à trouver ; en attendant, la confirmation de la restauration prévient que l'état des relais peut changer au redémarrage — preuve : recherche abandonnée à la demande de l'utilisateur (2026-11-03), cause non trouvée ; l'avertissement de la confirmation reste

## A8 — Documentation et clôture
- [x] `outils_docs/README.md` (mode d'emploi de l'onglet), carte des documents de `CLAUDE.md`, onglet Aide, texte de la tuile de l'annuaire (`annuaire_registre.py`) ; `verifie_references_docs.py` code 0 — preuve : § « Onglet « Sauvegarde configuration » » du README, carte des documents et exceptions de `CLAUDE.md`, onglet Aide, tuile `annuaire_registre.py` ; `verifie_references_docs.py` 0 défaut ; commit `6e15fc934`
- [x] A12 du plan `energie-differentiel` cochée avec renvoi à ce plan ; commit — preuve : A12 de `energie-differentiel.md` cochée avec renvoi ici ; onglet commité `6e15fc934`

## A9 — Retour au plan « energie-differentiel »
- [ ] Reprendre `tasks/plans/energie-differentiel.md` : thermomètre (A11), A14 (outil de l'`autoexec.bat` : endroit et questions à l'utilisateur), A10 (retour au plan « jauges-cuve »)

## A11 — Les trois améliorations du projet (demande du 2026-11-03)
- [x] Paramètres reposés au démarrage par le persist ou l'`autoexec.bat` marqués « ↻ démarrage » dans la page (survol : source et commande) — preuve : commande Tasmota de chaque paramètre tirée des définitions de decode-config (`decode_config_groupes.py`, 1er mot seulement : `influxdb_token32` → `IFX`, pas `Password`), comparée aux lignes de l'`autoexec.bat` et aux commandes de `configGlobal.be` (`build_sauvegarde::reposes`) ; page relancée : 34 marques sur le différentiel (`seriallog_level` : `autoexec.bat (SerialLog)`, `hostname` : `persist (Hostname)`) ; banc `test_build_sauvegarde_mqtt.py` VERT, témoin sans autoexec ni persist
- [x] Liaison MQTT pour une carte injoignable en HTTP : prise, comparaison et restauration par `FileDownload` / `FileUpload` de type 2 (`xdrv_02_1_mqtt_file.ino`), choix « Liaison » dans le bandeau — preuve : `build_sauvegarde_mqtt.py` ; banc VERT sur carte MQTT simulée (mauvais mot de passe, MD5 faux, refus de la carte, carte muette, restauration complète relue) ; mutant sans contrôle du MD5 vu ROUGE ; vraie carte (différentiel, `mqtt://bureau/pc`) : lecture de 4 800 o en 2,1 s, CRC valide, seul écart l'état du relais. **Restauration réelle par MQTT pas essayée** (écrit sur la carte : à faire avec l'utilisateur)
- [x] Purge automatique : sauvegardes « avant flash » et « avant restauration » de plus de 90 jours effacées au-delà des 5 plus récentes de chaque origine, à chaque prise automatique ; jamais une manuelle ni une modifiée — preuve : `build_sauvegarde::purge` ; banc VERT (rien d'effacé sous 90 jours, compte gardé, manuelle et modifiée anciennes intactes) ; mutant sans la règle des 90 jours vu ROUGE
- [ ] Restauration réelle par MQTT sur une carte, avec l'accord de l'utilisateur

## A12 — Remarques de l'utilisateur du 2026-11-03 (suite)
- [x] Purge automatique seulement si une case dédiée de l'onglet reste cochée (cochée par défaut, commune à toutes les cartes) — preuve : case sous l'historique, `POST /sauvegarde/reglages`, `build_sauvegarde::purge_auto` (fichier `reglages.json` du dossier des sauvegardes, illisible = purge active) ; banc MQTT VERT (décochée : rien d'effacé ; recochée : la purge reprend) ; mutant sans la case vu ROUGE ; sonde Chrome VERTE (case cochée par défaut, aller-retour enregistré)
- [x] Onglet « Envs par défaut » renommé « Env par défaut (Platformio override) » — preuve : `build_page.py` (bouton), README, docstrings ; `test_build_page_defaut_chrome.py` VERT
- [ ] Limite de la marque « ↻ démarrage » (tout `configGlobal.be` compté dès qu'un persist existe) : solutions proposées à l'utilisateur, choix en attente

## Vérification
- A1 : sorties de decode-config sur le vrai `.dmp` du différentiel (comparaison d'octets, valeurs relues).
- Bancs : `test_build_sauvegarde.py`, `test_build_page_sauvegarde_chrome.py`, puis `test_build_web.py`, `test_build_page_chrome.py`, `test_build_serie.py` (A5) ; Python de PlatformIO, code de sortie 0 = vert.
- Sur la carte (A7) : `Status 2`, `VoltageCal/CurrentCal/PowerCal`, `EnergyTotal`, `Timers` avant et après la restauration.
- Page build relancée par l'annuaire, jamais pendant un build.
