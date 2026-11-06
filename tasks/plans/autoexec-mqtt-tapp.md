---
chantier: autoexec-mqtt-tapp
titre: Envoi MQTT de l'autoexec.bat, commandes par carte, extensions .tapp (document, script, page)
statut: actif
cree: 2026-11-05
maj: 2026-11-06
source: squishy-imagining-raven.md
objectif: Envoyer l'autoexec.bat par MQTT, signaler une commande non compilée pour la carte, et savoir fabriquer un .tapp (document, script, page de l'annuaire)
---
# Envoi MQTT, commandes par carte, extensions .tapp

## Contexte
Demandes du 2026-11-05, à la fin du plan `autoexec-bat` (améliorations restantes), puis sur l'Extension Manager.

Décisions de l'utilisateur :
- fsMqtt chargé sur le **rideau** par une ligne d'autoexec, **et** un exemple `fsMqtt.tapp` documenté ;
- commande non compilée pour la carte : **alerte orange « absente »**, seulement si c'est certain ;
- défaut de `data/fs/gestionFileFolder.be` : **signalé dans le document, pas corrigé** ;
- un script de construction, et une aide à la création dans l'annuaire.

Établi pendant l'étude :
- `build_ota_mqtt.py` sait déjà tout faire (`Canal.lit`, `envoie_fs_mqtt(fichiers=, redemarrer=)`, `client_par_defaut`). `fsMqtt` est solidifié dans le socle de toutes les cartes, mais seuls le P4 et la cuve le chargent. Le différentiel, joignable en HTTP, reste comme il est.
- Aucune fausse alerte « inconnue » aujourd'hui (le seul `autoexec.bat` du parc n'en a aucune). Le vrai défaut : une commande du fork non compilée pour la carte ne déclenche rien.
- `verifie_lib_ignore.py::defines_env` donne les macros d'un env en **0,8 s** sans compiler (mesuré sur le différentiel) ; `lecture_gardes.py::evalue` évalue une garde en trois valeurs (vrai, faux, incertain).
- `.tapp` : ZIP **sans compression** (`Zip-readonly-FS/src/ZipReadFS.cpp` refuse le reste), à plat, `manifest.json` (`name` obligatoire), `autoexec.be` avec `tasmota.add_extension`, lancé **avant** `/autoexec.be` (`berry_tasmota/src/embedded/tapp.be`), arrêt par `unload()`. `outils_docs/scripts_python/berry/gen_tapp.py` est interactif et compresse (`ZIP_DEFLATED`) : ses archives seraient refusées.

Règles : rien n'est écrit sur une vraie carte sans geste ou accord de l'utilisateur ; bancs sans réseau 192.168.x ; pas de `pio` direct ; `data/fs/*.be` non touchés.

## A1 — Envoi de l'autoexec.bat par MQTT
- [x] Banc rouge (`test_autoexec_envoi.py`, carte MQTT simulée de `test_build_ota_mqtt.py` + réponse à `Status 5`) : `transport="mqtt"` prépare et envoie sans adresse IP ; nom d'hôte différent, carte muette ou fsMqtt absent : refus, rien d'envoyé, message qui le dit ; fichier absent de la carte : `sur_carte` None ; `redemarrer=False` : aucun `redemarre` ; jeton HTTP refusé en MQTT ; témoins rouges — preuve : test_autoexec_envoi.py VERT (115 OK, temoins rouges dont identite MQTT retiree et jeton sans transport) ; rouge d'abord (AttributeError REGLAGES_MQTT), commits 16c1a9e74 + 2dcc05b54 (ronde 1 : banc MQTT filtre/ferme, generation de preparation)
- [x] `autoexec_envoi.py` : `prepare(..., transport)` et `envoie(..., transport)`, jeton signé avec le transport, identité par `cmnd/<topic>/Status 5` puis `stat/<topic>/STATUS5`, topic lu au persist du dépôt, copie de la carte par `Canal.lit` avant l'envoi, envoi par `envoie_fs_mqtt(fichiers=["autoexec.bat"])` ; routes `/autoexec/envoi*` ; transport inconnu → 400 — preuve : autoexec_envoi.py prepare/envoie(transport=), routes transmettent le transport (400 sinon) ; test_assistant_persist_autoexec.py VERT (143 OK, temoins transport ignore par la route) ; commits 16c1a9e74 + 2dcc05b54 (ronde 1 : banc MQTT filtre/ferme, generation de preparation)
- [x] Onglet : choix « Wi-Fi (HTTP) / MQTT » dans le panneau d'envoi, HTTP par défaut, changer de voie relance la préparation ; sonde Chrome verte, témoin sur le transport transmis — preuve : test_assistant_persist_autoexec_chrome.py VERT (806 OK, temoins transport-ecran et voie-ignoree detectes) ; commits 16c1a9e74 + 2dcc05b54 (ronde 1 : banc MQTT filtre/ferme, generation de preparation)

## A2 — fsMqtt sur le rideau
- [ ] `demarrage.charge(["fsMqtt"])` dans `data/garage/tasmota32s3-rideau-garage-modbus/autoexec.be`, comme la cuve ; `banc_demarrage` : instantané du rideau mis à jour et relu, seul écart attendu ; agent `relecteur-berry` — preuve : banc_demarrage.py VERT sur les 6 cartes ; écart relu avant enregistrement : règle `Mqtt#Connected` et globale `fsMqttRecepteur`, rien d'autre ; relecteur-berry : rien de bloquant (fsMqtt dans le socle du rideau, topic `garage/rideau` au persist) ; pas encore essayé sur la carte (A10)

## A3 — Commandes par carte : les gardes dans le fichier figé
- [x] Banc rouge (`test_autoexec_commandes.py`) : `gardes["ZBSEND"]` porte `USE_ZIGBEE`, `gardes["I2CSCAN"]` `USE_I2C` (garde à l'intérieur d'une table) ; une commande définie dans deux branches a deux chemins ; `HOSTNAME` sans garde ; `--verifier` voit un écart — preuve : rouge d'abord (28 KO puis KeyError 'gardes'), puis VERT 141 OK dont 13 témoins de gardes rouges, commits bb60907ce + b39bb94b1 ; `HOSTNAME` absent de `gardes` : sa garde réelle `!defined(FIRMWARE_MINIMAL)` (support_command.ino::kTasmotaCommands) est retirée, aucune carte du parc n'étant un firmware intermédiaire
- [x] `autoexec_commandes.py` : clé `gardes` `{NOM: [chemin, ...]}`, un chemin = les conditions `#if`/`#ifdef` qui entourent la table et l'entrée ; ligne de table illisible → garde de la table seule, jamais de garde inventée ; fichier figé régénéré par `--generer`, sans téléchargement — preuve : commits bb60907ce + b39bb94b1, 805 gardées sur 1145 connues, `--verifier` « fige conforme au code », `connues`/`redemarrent`/`doc`/`anomalies` identiques au figé d'avant A3 (comparaison clé par clé) ; ajout : conditions sur une macro posée par un .ino ou tasmota_globals.h retirées (fausse alerte sinon sur I2SPlay)

## A4 — Commandes par carte : l'alerte « absente »
- [ ] `autoexec_gardes.py` : macros de l'env par `verifie_lib_ignore.py::defines_env`, mises en cache (mémoire) selon l'empreinte du cenv et de `user_config_override.h` ; `etat(nom)` : vrai, faux ou incertain par `lecture_gardes.py::evalue` ; préprocesseur indisponible → aucune alerte, jamais d'erreur
- [ ] `autoexec_analyse.py::analyse` : type `absente`, orange, « X n'est pas compilée pour cette carte (USE_Y non défini) », seulement si **tous** les chemins sont faux ; commandes Berry et SetOption non concernées ; libellé dans la page et, si le préprocesseur manque, une ligne discrète « vérification par carte indisponible »
- [ ] Bancs : `ZbSend` sur le différentiel → alerte ; garde incertaine → rien ; **aucune alerte sur le vrai `autoexec.bat` du différentiel** ; toutes les commandes de la banque essayées sur chaque carte maintenue, résultat relu un par un (faux positifs) ; temps de frappe inchangé (analyse sans sous-processus une fois le cache posé)

## A5 — Document sur les extensions
- [ ] `outils_docs/EXTENSIONS_TAPP.md` : caractéristiques (format, manifeste, cycle de vie, emplacement, activation, RAM), intérêts et limites, cas d'utilisation, processus de codage pas à pas avec gabarits (module déjà solidifié ; module embarqué avec `unload()`), règles du dépôt (charte des logs, `do ... end` pour ne pas créer de globale), envoi sur une carte, pièges : ordre avant `/autoexec.be`, formatage, envoi d'image qui ignore `/.extensions/`, défaut signalé de `data/fs/gestionFileFolder.be`. Chaque fait renvoie à sa source en `fichier::fonction` ; ce qui n'a pas été essayé sur carte est marqué comme tel

## A6 — Script de construction
- [ ] Banc rouge `test_gen_tapp.py` : archive en ZIP_STORED et à plat (relue par `zipfile`, comparée à `Wifi_Heap_Sticker.tapp` pour la forme), `manifest.json` invalide ou sans `name`, `autoexec.be` absent, sous-dossier, nom trop long, Berry qui ne compile pas → refus avec motif, rien d'écrit ; témoin sur `ZIP_DEFLATED`
- [ ] `berry/gen_tapp.py` réécrit, sans question ni colorama : `gen_tapp.py <dossier> [--sortie x.tapp]`, fonction `construit` réutilisable, syntaxe vérifiée par le moteur de `verifie_berry.py`, code de sortie 0 ou 1

## A7 — Page « Fabrique d'extensions » dans l'annuaire
- [ ] Serveur et page `outils_pc/tapp_web.py` + `tapp_page.py`, port 7980, `acces_web.py`, sources dans `data/extensions/<nom>/` : créer depuis un gabarit (deux modèles de A5), formulaire du manifeste (nom, version, description, `min_tasmota`), fichiers listés, contrôle en direct, « Fabriquer » → `.tapp` à côté du dossier ; noms hostiles refusés ; pas de suppression de source
- [ ] « Envoyer à une carte » : vers `/.extensions/<nom>.tapp`, nom d'hôte vérifié, geste explicite, refus pendant un build ; d'abord vérifier sur carte simulée et dans le code que `/ufsu` écrit dans ce sous-dossier ; sinon l'envoi part en amélioration restante et la page le dit
- [ ] Tuile `annuaire_registre.py` (groupe Maintenance), tâche VS Code, cible Custom détachée `build/cible_tapp.py` et sa liste `CIBLES_OUTILS` ; banc `test_tapp_web.py`, sonde Chrome (Python de PlatformIO, dépôt temporaire) ; agent `relecteur-pages-web`

## A8 — Exemple `fsMqtt.tapp`
- [ ] `data/extensions/fsMqtt/` (manifeste, `autoexec.be` de 3 lignes : `import fsMqtt` sous `do ... end`, `tasmota.add_extension`) ; banc Berry sur bouchons : charge sans globale créée, et sans `logFonctions` déjà initialisé ; archive produite par le script ; non embarqué dans une image

## A9 — Documentation et clôture
- [ ] `outils_docs/README.md` (voie MQTT de l'onglet, alerte « absente », fabrique d'extensions), carte des documents de `CLAUDE.md` (exceptions d'import `sys.path` vers `build/`), maquettes non requises ; `verifie_references_docs.py` sans défaut, `test_annuaire.py` et `build/test_garde_build.py` VERTS
- [ ] Améliorations du plan `autoexec-bat` cochées avec renvoi ici ; ses A10 et le retour à `energie-differentiel` restent ouverts

## A10 — Essai réel (avec l'utilisateur)
- [ ] Après accord : FS du rideau envoyé par la page Build, `fsmqtt/garage/rideau/etat` lu au démarrage, `autoexec.bat` envoyé par MQTT sur une carte choisie par l'utilisateur et relu identique, sans redémarrage
- [ ] Après accord : `fsMqtt.tapp` installé sur une carte de test, vu dans `/ext`, arrêté, relancé ; ordre avant le prologue constaté dans les journaux, tas mesuré avant et après ; résultat consigné dans `EXTENSIONS_TAPP.md`

## A11 — Retour au plan antérieur « autoexec-bat »
- [ ] Reprendre `tasks/plans/autoexec-bat.md` : son A10 (retour à `tasks/plans/energie-differentiel.md` : thermomètre A11, retour au plan « jauges-cuve » A10), après le compte rendu de ce plan à l'utilisateur

## Améliorations restantes
- [ ] [projet] Corriger le déplacement des `.tapp` dans `data/fs/gestionFileFolder.be` (condition qui semble inversée), si l'utilisateur le décide
- [ ] [projet] Commandes Berry par carte (modules réellement chargés), et alias `SO146` reconnus dans le choix remplacer/enlever
- [ ] [projet] Marquer dans la banque les commandes non compilées pour la carte choisie
- [ ] [projet] Dépôt d'extensions local pour la boutique de `/ext` (`OtaUrl`)

## Vérification
- Bancs (Python de PlatformIO, code de sortie 0 = vert) : `test_autoexec_envoi.py`, `test_autoexec_commandes.py`, `test_autoexec_analyse.py`, `test_assistant_persist_autoexec.py`, sonde `test_assistant_persist_autoexec_chrome.py`, `test_gen_tapp.py`, `test_tapp_web.py`, `berry/banc_demarrage.py`, `test_annuaire.py`, `build/test_garde_build.py`. Les 5 échecs connus liés à `serveur.voieReseau` restent hors sujet.
- Faux positifs de l'alerte : lecture un par un des résultats de la banque sur chaque carte, avant de cocher A4.
- Sur carte (A10) : seulement avec accord, journal web sans `_ERREUR`, fichier relu identique, tas mesuré.
- Aucun `pio run` direct ; un build éventuel par la page Build :7700.
