# Mémoire et partitions : maquettes et contraintes

Étude du 2026-11-01 pour un onglet de la page « Build et téléversement ». **Rien n'est encore réalisé** : le travail
est décrit dans `tasks/plans/temps-compilation.md`, actions A7 à A10.

- `maquettes_partitions.html` : les 4 modèles, interactifs, avec les vraies tables du P4, de la cuve et de la cave
  (taille du FS estimée). Les boutons de diff, d'écriture et d'analyse ne font rien.
- `modele-A.png` à `modele-D.png` : une image par modèle.

**Choix retenu : modèle B** (un curseur par partition), mesures dans un onglet + résumé sur la page d'accueil.

## Contraintes relevées dans le code

| Fait | Où | Conséquence |
|---|---|---|
| `boot_app0.bin` est écrit en 0xE000 (journal de flash) | sortie d'upload | `nvs` et `otadata` ne bougent pas |
| Le FS absorbe la flash non attribuée au premier démarrage | `xdrv_52_7_berry_embedded.ino`, `partition_core.be::resize_fs_to_max` | les curseurs répartissent toute la flash |
| Le FS est supposé en 5e position quand la table est corrigée | `pio-tools/post_esp32.py::patch_partitions_bin` | à vérifier avant d'ajouter une partition |
| Sans `safeboot`, plus d'OTA du firmware | envoi par la page (`/u4`) et Tasmota | suppression avec confirmation |
| Une OTA n'écrit jamais `partitions.bin` | adresse 0x8000, flash série seulement | OTA bloquée tant que la nouvelle table n'est pas flashée |
| Le tableau mémoire est affiché quand le firmware est relié | sortie du build | dernière mesure enregistrée hors de `.pio/build` |
