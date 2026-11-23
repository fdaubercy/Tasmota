# Débits de la nourrice de chauffage

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Les débits de la nourrice de chauffage (carte Serveur Débits PAC)

Carte ESP32-S3 `tasmota32s3-bureau-serveur-debits-pac` (dossier `data/bureau/tasmota32s3-serveur-debits-pac/`), à la
nourrice de la PAC : elle mesure le débit des **6 départs de radiateur** par leurs débitmètres à impulsions (YF-B2,
K = 11 Hz par L/min) et les publie sur sa page web, dans son JSON SENSOR et par ModBus. L'écran est sur une seconde
carte, la carte d'affichage (ci-dessous). Plans `tasks/plans/debitmetres-chauffage.md` et `tasks/plans/debits-deux-cartes.md`,
analyse `outils_docs/historique/ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`. **Pas encore essayées sur des cartes réelles** (2026-11-11).

**Deux cartes depuis le 2026-11-09** : l'acquisition compte et calcule, la carte d'affichage montre les débits sur son écran.

- **Acquisition** `tasmota32s3-bureau-serveur-debits-pac` : esclave ModBus id 1, Range Extender id 1, derrière le point
  d'accès de l'affichage (`ECRAN-DEBITS-PAC-GATEWAY`), sans écran (`drivers.ecran` OFF). Elle sert les 6 débits et un
  mot d'états aux registres 4704 à 4710 (`modules.debits.modbus` ON) et les pousse en UDP à chaque fin de fenêtre. Sa
  page et sa page d'équilibrage se joignent depuis le Wi-Fi maison par le relais de l'affichage :
  `http://<ip>:8080/` et `http://<ip>:8080/equilibrage`.
- **Affichage** `tasmota32s3-bureau-ecran-debits-pac` (dossier `data/bureau/tasmota32s3-ecran-debits-pac/`, IP
  <ip>, topic `chauffage/pac/ecran`) : module Waveshare ESP32-S3-Touch-LCD-7B (écran 7″ 1024 × 600, tactile
  GT911, RS485 intégré), maître ModBus et Range Extender id 0 (`ecranDebitsFonctions.be`, `controleEcranDebits.be`). Il
  relit les 7 valeurs en une requête toutes les 10 s par RS485 (RX GPIO16, TX GPIO15, 19 200 bauds) et reçoit le push.
  Une voie sans nouvelles depuis 2 fenêtres est affichée « inconnu ». Brochage, expandeur d'E/S, `display.ini` et choix
  HASPmota ou LVGL : fiche `WAVESHARE_ESP32-S3-Touch-LCD-7B.md` du dossier de la carte dans
  `outils_docs/Schémas de branchement - Attribution des PINS des modules/bureau/` (plan `debits-deux-cartes`, A8, en cours).
  Interface de l'écran choisie à la compilation : `custom_interface_ecran = haspmota` (ou `lvgl`) dans la section de
  l'env de `platformio_tasmota_cenv.ini`. Les fichiers de chaque interface sont listés sous `custom_interface_ecran_<nom>`,
  et seuls ceux de l'interface choisie partent sur le LittleFS. Le build l'annonce par une ligne
  « Interface d'ecran : … ; exclus : … » et s'arrête sur une valeur inconnue.
- **Réglages de l'affichage** : `ReglageEcranDebits fenetre <s>` (la même que `ReglageDebits fenetre` sur
  l'acquisition, à recopier à la main), `ReglageEcranDebits veille <min>`.
- **Réglages ModBus** : `ReglageModbus PeriodeReleve <s>` sur l'affichage (5 à 300 s, 10 posé ; exacte si elle divise
  60 ; prise en compte au redémarrage) ; `ReglageModbus LectureGroupee ON` sur l'acquisition. Détail du protocole :
  `PROTOCOLE_MODBUS.md` § « Lecture groupée et push multi-valeurs ».
- **Déploiement** : flasher l'acquisition AVANT l'affichage.
- **Sniffeur** sur le bus des débits : `sniffeur_modbus.py --persist affichage`.

**Où changer les noms des voies.**
- Affichage : `data/bureau/tasmota32s3-ecran-debits-pac/_persist.json`, `modules.ecranDebits.environnement.analogiques`,
  `analogique1` à `analogique6`, champ `nom` (« Débit 1 » à « Débit 6 » aujourd'hui), relu par `ecranDebitsFonctions.be`
  à chaque rafraîchissement. Libellés affichés avant le premier rafraîchissement : `pages.jsonl` du même dossier.
- Acquisition : `data/bureau/tasmota32s3-serveur-debits-pac/_persist.json`, `modules.debits.environnement.debitmetres`
  (voies 1-2) et `compteurs` (voies 3-6), champ `nom` : JSON SENSOR, historique, page d'équilibrage. Les `nom` de
  `analogique1` à `analogique7` du même module sont les libellés des registres servis au maître.
- Sur une carte en service : modifier le persist, l'envoyer (page Build, onglet Fichiers), puis `Restart 1`.

**L'acquisition en détail :**

- **Voies** : voies 1-2 = `FlowRateMeter` de Tasmota (GPIO4, GPIO5 ; groupe `debitmetres` du persist, entrées
  `debitmetre1-2`) ; voies 3-6 = compteurs `Counter1-4` (GPIO6, 7, 15, 16 ; groupe `compteurs`), débit calculé en Berry
  sur une fenêtre glissante (10 s par défaut). Nom et K de chaque voie dans son entrée du persist (`nom`, `k`).
- **Sorties** : bloc `DEBITS` du JSON SENSOR (`D1` à `D6` et `Total` en L/min, `Imprecis` = voies entre 0 et 1 L/min, sous
  la plage du YF-B2 (1 à 25 L/min), en orange sur l'écran ; `Muets`) ; une ligne par départ sur la page d'accueil ; écran : page 1 = 6 barres, débit
  et part du total, page 2 = K de chaque voie (bouton « Détails »). Description de l'écran : `pages.jsonl` de la carte,
  lancée par le module (`haspmota.start("/json/pages.jsonl")`).
- **Capteur muet** : une voie à 0 L/min pendant 10 min (`modules.debits.muet`, en min) est signalée « muet » en rouge sur
  l'écran, « capteur muet ? » sur la page, et par `CAPTEUR_MUET_ERREUR` au journal (au passage seulement). Un départ
  fermé plus de 10 min est donc signalé lui aussi.
- **Écran** : le code d'écran de `debitsFonctions.be` (pages, veille `modules.debits.veille`) ne sert plus depuis que
  l'écran est sur la carte d'affichage (`drivers.ecran` OFF sur l'acquisition). Veille de l'écran : `ReglageEcranDebits
  veille` sur l'affichage.
- **Réglages**, tous gardés au persist :

  | Commande | Effet |
  |---|---|
  | `ReglageDebits` | état : fenêtre, veille, voies (nom, K), débits, capteurs muets, durée de la dernière écriture de l'écran (`ecran_ms`) |
  | `ReglageDebits k <voie> <Hz par L/min>` | facteur K d'une voie (0,1 à 1000). Étalonnage : K corrigé = K × débit affiché ÷ débit réel |
  | `ReglageDebits nom <voie> <texte>` | nom du départ (24 caractères au plus), repris par l'écran et la page |
  | `ReglageDebits fenetre <s>` | durée de mesure, 2 à 60 s ; plus longue = plus précise aux petits débits |
  | `ReglageDebits veille <min>` | veille de l'écran, 0 à 120 min, appliquée sans redémarrer |
  | `ReglageDebits aide [sujet]` | aide de la commande |

- **Historique** : actif (relevé toutes les 5 min, 24 h affichées) ; courbes des 6 débits et du total sur `/graphiques`,
  libellés et groupes dans `graphiques.json` de la carte (libellés à refaire si un départ est renommé). Voir
  « Les graphiques des mesures ».
- **Essai de charge** (avant la pose) : un second ESP32 sous Tasmota standard envoie des impulsions sur les 6 entrées ;
  `python outils_docs/scripts_python/outils_pc/essai_charge_debits.py --generateur <ip> --carte <ip>` compte ce que la
  carte a reçu à chaque palier (écart < 0,5 % attendu) ; montage et câblage dans sa docstring (`--help`).
- **Équilibrer la nourrice** : guide `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`, et sa version animée pas
  à pas (estimateur des puissances, calculateur des débits cibles), `data/bureau/tasmota32s3-serveur-debits-pac/equilibrage.html` :
  servie par la carte (bouton « Équilibrage » de l'accueil, `/equilibrage`, débits lus sur la carte), ou ouverte seule
  sur un téléphone ou un PC (débits tapés à la main). Sur la carte, la page reçoit en plus le code
  `equilibrage_carte.js` du même dossier. Avec « Suivre en direct », le schéma animé montre les débits réels, colorés selon
  les cibles du calculateur. Le bouton « Garder les puissances sur la carte » enregistre l'estimateur et les puissances
  dans `/json/equilibrage.json` (hors persist, effacé par un envoi du FS en image : à réenregistrer). Un favori du téléphone
  vers `/equilibrage` fonctionne : sans Referer, la carte renvoie une page vide qui se recharge, et le contrôle d'accès
  habituel s'applique.
- **Vérifier** : bancs hors carte `python outils_docs/scripts_python/berry/banc_debits.py` (calcul, JSON, écran, capteur
  muet, réglages, veille ; témoins) et `banc_demarrage.py --carte tasmota32s3-bureau-serveur-debits-pac` (code 0 = vert).

<hr></hr>
