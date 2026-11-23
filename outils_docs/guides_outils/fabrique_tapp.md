# Fabrique d'extensions (.tapp)

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Fabrique d'extensions (page web)

Page http://127.0.0.1:7980 pour fabriquer une extension Tasmota (`.tapp`) et l'envoyer à une carte. Ce qu'est une
extension, quand s'en servir et ses pièges : [EXTENSIONS_TAPP.md](../reference_berry/EXTENSIONS_TAPP.md). Lancement : tuile « Fabrique
d'extensions » de l'annuaire (groupe Ateliers), tâche VS Code « Outil : fabrique d'extensions », ou cible Custom
« Fabrique d'extensions (page web) » (`build/cible_tapp.py`, page démarrée détachée ; `pio run` : jamais pendant un build).
Arrêt libre : rien n'est écrit ni envoyé sans un geste dans la page, aucune source n'est supprimée. La liste des
cartes destinataires est groupée par lieu de la maison (`outils_pc/lieux.py`).

Cinq étapes :

1. **Créer depuis un modèle** : un dossier `data/extensions/<nom>/` (31 caractères au plus, lettres sans accent,
   chiffres, `-` et `_`). Modèle A : charger un module déjà dans le firmware (exemple : `fsMqtt`) ; modèle B : un module
   embarqué, qu'on peut arrêter depuis `/ext`. Un dossier existant n'est jamais écrasé.
2. **Manifeste** : nom, version, description, `min_tasmota` ; les autres clés du fichier sont gardées.
3. **Vérifier puis fabriquer** : noms des fichiers, manifeste, compilation Berry (avec la charte des logs en
   avertissements), point par point. « Fabriquer le .tapp » écrit `data/extensions/<nom>.tapp` à côté du dossier (archive
   sans compression, comme l'exige le firmware ; non versionnée). En ligne de commande : `berry/gen_tapp.py <dossier>`.
   **Piège** : l'extension est compilée par la carte avant `/autoexec.be`, quand `LOG_LEVEL_*` et `logFonctions`
   n'existent pas encore. Un `LOG_LEVEL_INFO` nu empêche l'extension de se lancer : écrire `global.LOG_LEVEL_INFO`, et
   `import logFonctions` dans la fonction. La vérification le refuse en le disant.
4. **Envoyer à une carte** : choisir la carte et la voie (Wi-Fi HTTP ou MQTT, comme l'onglet « autoexec.bat »), vers
   `/.extensions/<nom>.tapp`. Nom d'hôte de la carte comparé au persist du dépôt, refus pendant un build, case à cocher
   avant « Envoyer », pas de redémarrage par défaut (l'extension se lance au démarrage suivant, ou par `/ext`). En MQTT,
   la carte n'est lue qu'au clic sur « Lire la carte » : une lecture ouvre un échange avec `fsMqtt`, qui annulerait un
   transfert en cours.
5. **Boutique locale de `/ext`** : tant que la page tourne, elle sert les `.tapp` fabriqués et à jour comme un dépôt
   d'extensions (`/extensions/extensions.jsonl` et `/extensions/tapp/<nom>.tapp`, publics car une carte n'a pas de jeton,
   lecture seule). Une carte les propose dans sa boutique (`/ext`, « Online Store ») si son `OtaUrl` pointe sur ce PC,
   par exemple `OtaUrl http://<ip-du-pc>:7980/` : la carte en déduit `http://<ip-du-pc>:7980/extensions/`. Elle revient
   au dépôt officiel si la page ne répond pas ; sinon, seules nos extensions y figurent. **Attention** : `OtaUrl` sert
   aussi à `Upgrade` par URL, qui ne trouverait plus le firmware officiel sur cette carte. À poser carte par carte, à la
   main ; la page doit écouter sur le réseau (pas `--local`), et le pare-feu Windows autoriser Python sur le réseau privé.

Un `.tapp` envoyé n'est pas dans l'image du FS : un formatage ou un flash série l'efface. Envoi MQTT, chargement avant
`/autoexec.be`, Running/Stop et désinstallation **essayés sur la cuve le 2026-11-09** (`EXTENSIONS_TAPP.md` § 9) ; la
boutique locale et l'envoi HTTP ne l'ont pas encore été (plan `tasks/plans/autoexec-mqtt-tapp.md`). Bancs (`outils_pc/`, Python de PlatformIO) : `test_tapp_web.py`,
`test_tapp_envoi.py`, sonde Chrome `test_tapp_page_chrome.py` ; `berry/test_gen_tapp.py`, `berry/banc_tapp_fsmqtt.py`
(l'exemple) ; cible : `build/test_cible_tapp.py`.
