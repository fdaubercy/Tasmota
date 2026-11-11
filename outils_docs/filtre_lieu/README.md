# Classement des cartes par lieu : maquettes

Étude du 2026-11-10 : classer ou filtrer les cartes par emplacement dans la maison, sur la page « Build et
téléversement » (onglets Build et Fichiers) et sur les autres pages de l'annuaire qui font choisir une carte.

**Choix retenus le 2026-11-10 : D pour l'onglet Build, F pour l'onglet Fichiers, H pour les autres pages ; lieux,
ordre et piscine en « Extérieur » validés tels que dans la maquette.** Réalisé le 2026-11-11 (plan
`tasks/plans/classement-par-lieu.md`, spec `docs/superpowers/specs/2026-11-10-classement-par-lieu-design.md`) :
table des lieux et `remplitParLieu` dans `outils_pc/lieux.py` (banc `test_lieux.py`), modèle D dans
`outils_pc/build_page_lieux.py` (sonde `test_build_page_lieux_chrome.py`), modèle F dans
`build_page_fichiers.py::fichiersCartes`, modèle H dans les listes de carte des pages 7700 à 7980.

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

## Suite (2026-11-11) : lieu partagé depuis l'annuaire, syslog et sniffeur MQTT

`maquettes_lieu_suite.html` (`?m=J` à `?m=O`, `&t=clair`), images `modele-J.png` à `modele-O.png`. **Choix retenus le
2026-11-11 : J pour l'annuaire, mise en avant à l'arrivée (rien n'est caché), M pour le syslog, N et O pour le
sniffeur MQTT.** Réalisé le 2026-11-11 (plan `tasks/plans/lieu-partage-syslog-mqtt.md`, spec
`docs/superpowers/specs/2026-11-11-lieu-partage-syslog-mqtt-design.md`). J : `annuaire_page_lieux.py` ; M : `syslog_tasmota_web.py` ;
N et O : `sniffeur_mqtt_lieux.py` et `sniffeur_mqtt_panneaux.py` ; table hôte, topic et IP vers lieu : `lieux.py::identites`.

| Modèle | Où | Principe |
|---|---|---|
| J | Annuaire | Puces « Lieu de travail » ; chaque « Ouvrir ↗ » porte `?lieu=` ; bandeau « Lieu : Garage » sur la page ouverte |
| K | Annuaire | Une fiche par lieu : ses cartes, et un lien direct vers chaque outil pour CETTE carte (`?env=`) |
| L | Syslog | Barre des modules (noms d'hôte) rangée sous l'intertitre de leur lieu ; liste « module » groupée |
| M | Syslog | Puces de lieu (filtre, lignes et erreurs par lieu) ; étiquette de lieu sur chaque ligne |
| N | Sniffeur MQTT | Arborescence des topics rangée par lieu, l'env de chaque topic entre parenthèses |
| O | Sniffeur MQTT | Puces de lieu (filtre d'affichage) ; étiquette de lieu sur chaque message |

Conception commune : la table hôte → lieu et topic → lieu n'est PAS tenue à la main. Le `_persist.json` de chaque carte
porte `serveur.hostname` (le « module » du syslog) et `serveur.mqtt.topic` ; le nom d'env donne le lieu (`lieux.py`). Le
topic ne dit rien du lieu (la cuve publie en `jardin/cuve`, le différentiel en `bureau/pc`). Cartes sans persist
(`tasmota32-rdc-vr-porte`, `tasmota-pompe-piscine`) : IP de `user_config_override.h` (le syslog nomme un hôte inconnu
par son IP), à vérifier. Hôte ou topic inconnu du dépôt : groupe « Autres ». Deux cartes peuvent partager un nom d'hôte
(`SERVEUR-RLY-CAVE`, `SERVEUR-GARAGE`) : même lieu dans les deux cas.
