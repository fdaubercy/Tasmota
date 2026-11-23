# Sniffeur MQTT

Port : 7100. Cible PlatformIO : `sniffeur_mqtt` (Custom). Tâche VS Code : « Outil : sniffeur MQTT (http://127.0.0.1:7100) ».

## Lancer

Aucune dépendance, tout Python 3.8 ou plus :

```
python outils_docs/scripts_python/outils_pc/sniffeur_mqtt.py --http 7100
```

Options (`sniffeur_mqtt.py::main`) :

- `--hote`, `--port`, `--utilisateur`, `--mot-de-passe` : broker par défaut. Sans option, ils viennent de la première définition de `MQTT_HOST`, `MQTT_PORT`, `MQTT_USER`, `MQTT_PASS` dans `tasmota/user_config_override.h` (`sniffeur_mqtt.py::lit_config_broker`).
- `--abonnement "#"` (répétable) : sinon l'abonnement mémorisé pour le broker, sinon `#`.
- `--http 7100`, `--journal fichier.log`, `--historique 5000`, `--config <fichier>`.
- `--local` (127.0.0.1 seulement), `--sans-navigateur`.

Pendant un build, lancer le script en Python direct, jamais la cible PlatformIO. Depuis un autre appareil, utiliser le lien à jeton de la console.

## Ce que fait la page

- Messages en direct, filtre d'affichage (texte ou regex), favoris de filtre, différences avec le message précédent du même topic, export `.txt` ou `.json`.
- Plusieurs brokers paramétrables (TLS possible), un seul actif, changé à chaud depuis la page.
- Abonnements gérés un par un (filtrage côté broker), mémorisés par broker.
- Publication en texte ou en hexa, retenue ou non. Un message vide retenu efface le retenu. Le bouton « Effacer les retenus affichés » agit selon le filtre d'affichage.
- Panneaux : audit discovery, connexions (LWT), console de logs par carte (`stat/<topic>/LOGGING`, sans occuper de port série), commande Tasmota avec sa réponse, arborescence des topics.
- Classement par lieu de travail : la page lit `?lieu=` (route `GET /lieux`).

Pour lire les logs d'une carte sans écrire : `GET /logs` liste les topics, `GET /logs?module=<topic>` rend les lignes (3000 au plus, en mémoire).

## Pièges

- Les brokers et leurs mots de passe sont dans `%APPDATA%\sniffeur_mqtt\config.json`, hors dépôt. Les mots de passe ne sont jamais affichés ni envoyés à la page.
- Le Client ID est unique (`sniffeur-<poste>-<pid>`) : le sniffeur ne déconnecte aucun module.
- Un message de log n'apparaît que s'il passe deux filtres : le seuil du module (`ReglageLog <cible> <niveau>`) et le seuil de la sortie `mqtt` du profil actif. En profil `normal`, `mqtt` est à `erreur` : `stat/<topic>/LOGGING` est quasi muet.
- Les esclaves derrière le NAPT du maître : garder `ReglageLog profil normal` sur eux. `MqttLog` en debug à travers le NAPT a fait redémarrer la cuve (chien de garde). Ne pas toucher à `USE_ESP32_WDT`.
- `POST /publier` (en-tête `X-Sniffeur: 1`) écrit dans une carte : jamais pour « lire des logs ». Changer un réglage de log envoie une commande à la carte, seulement sur demande.
- Une sortie à `detail` (niveau 4 du firmware) affiche aussi les `BRY: GC`.
- Sans `--journal`, rien n'est gardé sur disque (la cible PlatformIO écrit `%TEMP%\sniffeur_mqtt.log`).

## Bancs

```
PYPIO outils_docs/scripts_python/outils_pc/test_sniffeur_mqtt_acces.py
PYPIO outils_docs/scripts_python/outils_pc/test_sniffeur_mqtt_page_chrome.py
```

Le premier couvre l'accès (jeton, en-tête, origine). Le second est la sonde Chrome de la page (jamais pendant un build, Chrome arrêté en fin de sonde). Code de sortie 0 = vert.
