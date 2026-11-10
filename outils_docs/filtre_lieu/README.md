# Classement des cartes par lieu : maquettes

Étude du 2026-11-10 : classer ou filtrer les cartes par emplacement dans la maison, sur la page « Build et
téléversement » (onglets Build et Fichiers) et sur les autres pages de l'annuaire qui font choisir une carte.

**Choix retenus le 2026-11-10 : D pour l'onglet Build, F pour l'onglet Fichiers, H pour les autres pages ; lieux,
ordre et piscine en « Extérieur » validés tels que dans la maquette.** Rien de réalisé.

- `maquettes_filtre_lieu.html` : 9 modèles (`?m=A` à `?m=I`, `&t=clair` pour le thème clair), avec les vraies cartes.
  Rien n'est écrit.
- `modele-A.png` à `modele-I.png` : une image par modèle (thème sombre).

Source du lieu : le 2e segment du nom d'env, comme `pre_utilitaires_platformio.py::transform_name` et
`fichiers_berry_etat.py::dossier_carte` (`tasmota32s3-garage-…` donne `garage`). Aucun champ à ajouter au cenv, sauf
pour `tasmota-pompe-piscine` (ESP8266 sans dossier, le 2e segment donne « pompe ») : rangé ici en « Extérieur ».
Libellés et ordre des lieux supposés, à confirmer.

| Modèle | Où | Principe |
|---|---|---|
| A | Build | Puces de lieu au-dessus de la liste (filtre), compte des cochés par lieu, avertissement des cochés masqués |
| B | Build | « Mes cartes » découpé en sous-groupes par lieu, case de lieu qui coche toutes ses cartes |
| C | Build | Plan de la maison cliquable (étages, annexes) au-dessus de la liste |
| D | Build | Bascule « Classer par » Famille / Lieu / Puce, un groupe repliable par lieu |
| E | Fichiers | Puces de lieu au-dessus de la liste des cartes destinataires |
| F | Fichiers | Intertitres de lieu dans la liste |
| G | Fichiers | Tuiles de lieu, puis les cartes du lieu choisi |
| H | Autres pages | Listes déroulantes groupées par lieu (`<optgroup>`) |
| I | Autres pages | Puces de lieu qui réduisent la liste déroulante |

Pages concernées (recensement du 2026-11-10) : Build (onglets Build, Fichiers, Mémoire et partitions, Sauvegarde
configuration), Fichiers Berry par env (7800), Assistant persist (7900, onglet autoexec.bat compris), Atelier des
graphiques (7950), Fabrique d'extensions (7980). Laissées telles quelles : onglet « Env par défaut » (classé par puce
comme le fichier), syslog (hôtes sans lieu), sniffeur MQTT (topics hors dossiers : la cuve publie en `jardin/cuve`),
sniffeur I2C (déjà trié par lieu), sniffeur ModBus, testeur UDP, pont série, synchro du fork.
