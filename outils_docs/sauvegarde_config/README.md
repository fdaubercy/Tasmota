# Onglet « Sauvegardes » de la page build : maquettes

Demande du 2026-11-02 : sauvegarder la configuration d'une carte de la liste des envs, la restaurer, modifier un fichier
de sauvegarde par paramètre. **Choix du modèle : en attente de l'utilisateur.** Rien n'est réalisé.

- `modele-A.png` : trois colonnes (cartes, sauvegardes, paramètres). Tout est visible d'un coup.
- `modele-B.png` : carte choisie en haut, historique à gauche, paramètres repliés par thème à droite.
- `modele-C.png` : assistant en 4 étapes.
- `maquettes_sauvegarde.html` : code des maquettes (`?modele=A|B|C`). Les valeurs sont des exemples.

## Contraintes retenues

- Fichiers rangés dans `outils_docs/sauvegardes_cartes/<env>/`, pas dans `data/<lieu>/<carte>/` : ce dossier-là part dans
  l'image du FS. Dossier ignoré par git : un `.dmp` contient les mots de passe Wi-Fi et MQTT, et le dépôt est public.
- Une modification crée une nouvelle sauvegarde : l'originale n'est jamais réécrite.
- Une restauration prend d'abord une sauvegarde de la carte, puis montre les écarts et demande confirmation.
- Format `/dl` (`tasmota/tasmota_support/settings.ino`) : XOR, Settings de 4096 o, puis fichiers du FS (`.drvset*`), CRC.
  La disposition de Settings dépend de la version : une version inconnue s'affiche sans édition, et reste restaurable.
- Mots de passe masqués dans la page ; recopiés côté serveur s'ils ne sont pas modifiés.
