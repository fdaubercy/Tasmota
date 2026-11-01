---
chantier: lib-ignore-envs
titre: lib_ignore pour chaque env personnel, avec garde au pre-build
objectif: Etendre a tous les envs personnels le lib_ignore valide sur la cuve, chaque liste etablie et controlee par un script avant le scan des dependances
statut: actif
cree: 2026-10-31
maj: 2026-10-31
---
# lib_ignore pour chaque env personnel

## Contexte
Suite du plan `lib-ignore-cuve.md` (scan LDF de la cuve 21 min 42 → 7 min 36, firmware identique). Demande du
2026-10-31 : étendre à chaque env personnel, revoir les dépendances de chacun avant de poser son `lib_ignore`
(propre ou commun), et faire d'abord le petit script qui vérifie qu'une bibliothèque est ignorable sans risque.

Décisions :
- Script lancé **au pré-build seulement** (réponse du 2026-10-31) : `build/verifie_lib_ignore.py::controle`,
  appelé par `pre_utilitaires_platformio.py` avant le scan ; ne contrôle que les bibliothèques que le cenv ajoute
  au premier ancêtre de l'amont (`extends`, bases personnelles comprises), et seulement les envs de `platformio_tasmota_cenv.ini`. Les listes sont
  établies par Claude avec le même code (`--propose`).
- Signalé dans le terminal et sur la page build (détail de l'étape Pré-build, lignes ✗ dans l'extrait d'erreur).
- Matter, SendMail et KNX restent actifs : jamais d'`#undef` ; ils ne sont ignorés que là où ils sont déjà inactifs.
- Piscine (ESP8266) hors champ : son env ne charge pas le pré-script (bases ESP32 seulement).

## A1 — Script de vérification
- [x] `outils_docs/scripts_python/build/verifie_lib_ignore.py` : defines de l'env (préprocesseur croisé + vrai sdkconfig.h), includes sous gardes (logique à 3 valeurs, essais pour les inconnues), bibliothèques atteignables, en-têtes fournis ailleurs — preuve : cuve, liste actuelle → aucun défaut ; + esp_wireguard_tasmota → refusée (xdrv_52_3_berry_crypto.ino:27, garde active) ; ~11 s
- [x] Banc `build/test_verifie_lib_ignore.py` (faux dépôt + `--reel` sur la cuve) — preuve : VERT ; mutants court-circuit, atteignabilité, en-tête ailleurs tous tués
- [x] Branché au pré-build (`pre_utilitaires_platformio.py`, hors safeboot et hors cibles d'outils) — preuve : appel `verifie_lib_ignore.controle(env)` avant `adapteParametresPlatformio_override()`
- [x] Affichage sur la page build (`outils_pc/build_progression.py`, `_LIB_IGNORE`) + test — preuve : `test_build_progression.py` VERT (test_lib_ignore)
- [ ] Premier build réel avec la garde : ligne ✔ visible dans le terminal et dans le détail du Pré-build de la page
- [x] Correctifs après les échecs du 2026-10-31 (P4 : ESP8266SAM.h ; cuve : ESPFtpServer.h ; garde passée ✔ les deux fois) — preuve : causes tracées (1) commentaires retirés en deux passes, `//*****` ouvrait un bloc et effaçait xdrv_50 jusqu'à la ligne 1912 → découpage en un passage (`lecture_gardes.py::sans_commentaires`) ; (2) macro inconnue crue fausse dans tasmota/ (ESP_IDF_VERSION_MAJOR, du framework) → fausse seulement si option Tasmota ou définie nulle part (index des macros du framework en cache) ; (3) un défaut du contrôle ne bloque plus le build ; banc VERT avec les 3 échecs réels refusés en `--reel`, mutants tués
- [x] Module scindé sous 500 lignes — preuve : `verifie_lib_ignore.py` 398 lignes + `lecture_gardes.py` 167

## A2 — Revue des dépendances de chaque env
- [x] `--propose` lancé sur les 9 envs personnels (cuve, rideau, P4, S3 serveur garage, cave S3, cave ESP32, différentiel, VR porte, grenier) : bibliothèques à ajouter et raison de chaque gardée — preuve : `propose_<env>.txt` (scratchpad), 50 à 61 bibliothèques par env ; cas douteux relus (TM1638plus : seulement sous USE_DISPLAY_TM1637 ; esp-nimble-cpp : USE_IBEACON_ESP32 absent, iBeacon HM17)
- [x] Synthèse : bibliothèques ignorables partout (liste commune) / propres à un env ; Matter, SendMail, KNX vérifiés actifs — preuve : commun 50, sans_ecran 7 (tous sauf cave S3 et grenier), propres ESP8266Audio / BME8563 / Berry Animation Framework / Micro-RTSP / freetype ; Matter, Mail, KNX proposés nulle part
- [x] Listes validées par l'utilisateur avant édition du cenv — preuve : réponse du 2026-10-31 « Commun + sans écran + propres »

## A3 — Édition du cenv
- [x] Section commune `[lib_inutiles]` (si la synthèse en justifie une) + `lib_ignore` de chaque env = parent + commune + propres — preuve : `git diff platformio_tasmota_cenv.ini` +124/−26, contrôle « aucun build » dans la même commande, copie avant édition dans le scratchpad
- [x] Relu par `ProjectConfig` ; garde rejouée hors build sur chaque env (aucun défaut) — preuve : 9 envs, ajouts = propositions exactement (rien en plus, rien en moins), garde OK en 5 à 7 s chacun

## A4 — Validation par carte (un build à la fois, jamais pendant un build de l'utilisateur)
- [ ] Chaque env compile ; durée du scan relevée
  - [x] Listes recalculées avec le script corrigé et cenv corrigé — preuve : ESPFtpServer, ESP8266SAM, mp3_shine_esp32 retirées de `commun` (FTP actif sur 7 cartes, audio I2S sur le P4), remises en propres là où ignorables ; 9 envs = calcul exactement, garde OK
- [ ] Cartes flashées et vérifiées par l'utilisateur

## A5 — Bilan
- [ ] Gains par env consignés ; commit du cenv et des plans

## Améliorations restantes
- [ ] [projet] Piscine (ESP8266) : liste établie à la main avec `--propose` si un jour utile (pas de garde)
- [ ] [projet] Cache des inclusions par date de modification si les ~11 s du contrôle pèsent

## Vérification
Incident du 2026-10-31 (nuit) : P4 et cuve en échec de compilation (ESP8266SAM.h, ESPFtpServer.h) alors que la garde
affichait ✔ ; build du différentiel arrêté net à 04:00:57 sans sortie du pré-script, probablement pendant que je
modifiais `verifie_lib_ignore.py` (importé par le pré-script) — d'où le contrôle qui ne bloque plus jamais.

Avant (A1 de lib-ignore-cuve) : scan LDF de la cuve 21 min 42 sans lib_ignore, 7 min 36 avec 23 bibliothèques.
Listes posées le 2026-10-31 (lib_ignore résolu / ajouté par le cenv) :

| Env | Résolues | Ajoutées |
|---|---|---|
| différentiel, cave ESP32 | 66 | 61 |
| VR porte | 64 | 59 |
| cuve, rideau, S3 serveur garage | 65 | 58 |
| P4 | 62 | 56 |
| cave S3 | 57 | 50 |
| grenier | 56 | 49 |

(Résolues = ajoutées + héritées de l'amont ; tableau du 2026-11-01, après correction.)

