# Analyse des clés `adressMAC` / `adresseMAC` et `telePeriod` (2026-10-27)

> Document daté, en lecture seule : aucun code modifié. Les numéros de ligne sont ceux du 2026-10-27.
> Décision en vigueur : les clés restent en l'état. Ce document chiffre les options, l'utilisateur tranche.
> Périmètre : `data/` hors `*sauvegarde*`, `outils_docs/scripts_python/`, `tasmota/` (`*.be`, `*berry*`, aucun résultat).
> Les valeurs des MAC ne sont pas reproduites : « présente », « vide » ou « absente ».

## 1. Résumé

- `adressMAC` et `adresseMAC` sont **deux clés distinctes de `serveur`**, écrites par deux modules différents, à des moments différents ; **aucune ne double l'autre par construction**.
- Le parc ne porte que `adressMAC` (8 persists, toutes vides au dépôt). `adresseMAC` n'existe nulle part au dépôt : elle naît sur la carte, et seulement si `discoveryFonctions` tourne. **Aucun code ne lit `adressMAC`** (sauf le banc `banc_boot.be`) : la clé du modèle est une clé **écrite, jamais lue**.
- Incohérence prouvée : une carte avec `serveur.udp` ON et `serveur.discovery` OFF (le différentiel) lit `adresseMAC` dans `udpFonctions` alors que seule `adressMAC` est renseignée chez elle.
- `diverses.telePeriod` est la **seule `telePeriod` lue** (7 lecteurs + `configGlobal`). `serveur.udp.telePeriod` et `serveur.rangeExtender.telePeriod` sont **mortes** : aucun lecteur dans `data/`, `tasmota/` ni les outils PC.
- Recommandation : **retirer** les deux `telePeriod` imbriquées ; pour la MAC, **fusionner vers `adresseMAC`** (celle que le code lit), après décision sur le sort de `adressMAC` (§4.2).

## 2. `adressMAC` / `adresseMAC`

### 2.1 Écrivains et lecteurs

| Clé | Rôle | Fichier::fonction (ligne) | Moment |
|---|---|---|---|
| `adressMAC` | écrivain | `globalFonctions.be::globalFonctions_changementEtatDemarrage` (91) | `System#Boot` ; `Status 5` ; écrit seulement si la valeur diffère |
| `adressMAC` | lecteur | même fonction (87, 90) : compare avec la valeur lue, pour décider d'écrire | idem |
| `adressMAC` | lecteur | `banc_boot.be` (301) | banc seulement |
| `adressMAC` | persistance | même fonction : `persist.serveur = serveur` à `Save` | avant redémarrage |
| `adresseMAC` | écrivain | `discoveryFonctions.be::discoveryFonctions_changementEtatDemarrage` (253) puis `persist.save()` (255) | `Wifi#Connected` ; `Status 5` |
| `adresseMAC` | écrivain (fiche, autre objet) | même fonction (278) : champ `adresseMAC` des fiches de `discovery.json`, valeur issue de `Status 5` | `Wifi#Connected` |
| `adresseMAC` | lecteur | `discoveryFonctions_changementEtatDemarrage` (260, 264, 348-361, 389) : clé de rangement de `discovery.json` | `Wifi#Connected` |
| `adresseMAC` | lecteur | `discoveryFonctions.be::discoveryFonctions_purgeAnciennes` (148), `::discoveryFonctions_mqtt_discovery` (432) | réception MQTT discovery |
| `adresseMAC` | lecteur | `udpFonctions.be::udpFonctions_reglageUDP` (265) ; `::udpFonctions_esclavesBox` (660) | `ReglageUDP forceEnvoiParams` ; page d'accueil |
| `adresseMAC` | lecteur de fiche | `udpFonctions_reglageUDP` (306) : lit `adresseMAC` dans la fiche reçue, pas dans `serveur` | réception `ImAlive` |
| `adresseMAC` | lecteur | `modbusFonctions.be::modbusFonctions_reglageVoieCommandes` (549), `::modbusFonctions_fichesModbus` (1622) | commandes ModBus |
| `adressMAC` (commentaire) | aucun | `controleUDP.be` (11) : liste de champs dans un commentaire | sans effet |

Hors `data/` : `sniffeur_mqtt.py` (263) et `sniffeur_mqtt_panneaux.py` (49) lisent `adresseMAC` **dans les fiches de discovery**, pas dans le persist.
`genere_schema_persist.py` ne cite aucune des deux ; `persist.schema.json` (385, 775) déclare `adressMAC` obligatoire, sans `adresseMAC`.

### 2.2 Cartes porteuses (script de recensement, noms de dossier et présence seulement)

| Carte | `adressMAC` (ligne du persist) | `adresseMAC` | `serveur.discovery` | `serveur.udp` |
|---|---|---|---|---|
| interrupteur-differentiel | vide (50) | absente | OFF | ON |
| serveur-rly (cave) | vide (50) | absente | OFF | OFF |
| s3-serveur-rly (cave) | vide (60) | absente | ON | ON |
| s3-grenier | vide (60) | absente | ON | OFF |
| p4-serveur-modbus | vide (61) | absente | ON | ON |
| s3-capteurs-cuve-modbus | vide (61) | absente | ON | ON |
| s3-rideau-garage-modbus | vide (60) | absente | ON | ON |
| s3-serveur-modbus | vide (60) | absente | ON | ON |

Le modèle porte `adressMAC: ""` (`modele_persist.json`, 73). Les valeurs ci-dessus sont celles du **dépôt** ; sur une carte en service, `adressMAC` est remplie au premier `System#Boot` (corrigé le 2026-10-24 : affectation et non `insert`).
Je n'ai **pas lu** les persists vivants des cartes : « `adresseMAC` apparaît sur la carte avec `discovery` ON » est déduit du code (253), pas observé.

### 2.3 Incohérences

1. **Prouvée, effet limité :** le différentiel (`udp` ON, `discovery` OFF) n'exécute jamais la ligne 253 : sa `adresseMAC` reste absente. `udpFonctions_reglageUDP` (265) et `udpFonctions_esclavesBox` (660) lisent pourtant `adresseMAC` avec repli `"000000000000"` / `""`. `adressMAC` est renseignée chez lui, mais personne ne la lit. Gravité réelle : dépend de l'usage de `forceEnvoiParams` et des fiches sur cette carte (à confirmer ; `discovery.json` y est vraisemblablement absent).
2. **Prouvée, doublon d'écriture :** sur les 6 cartes à `discovery` ON, les deux clés sont renseignées par deux `Status 5` distincts (`System#Boot` et `Wifi#Connected`). Même valeur, deux copies dans le persist de la carte.
3. **Dérive de format possible :** `adressMAC` est comparée telle que renvoyée par `Status 5`, `adresseMAC` aussi (même source) ; aucune normalisation divergente trouvée.
4. **Schéma :** `persist.schema.json` rend `adressMAC` obligatoire, donc un persist « fusionné » vers `adresseMAC` échouerait au schéma tant qu'il n'est pas regénéré.

## 3. Les trois `telePeriod`

### 3.1 Valeurs par carte (toutes à 300)

| Carte | `diverses.telePeriod` | `serveur.udp.telePeriod` | `serveur.rangeExtender.telePeriod` |
|---|---|---|---|
| interrupteur-differentiel | 300 (14) | 300 (106) | absente |
| serveur-rly, s3-serveur-rly, s3-grenier, s3-serveur-modbus | 300 (14 ou 24) | absente | absente |
| p4-serveur-modbus | 300 (25) | absente | 300 (100) |
| s3-capteurs-cuve-modbus | 300 (25) | absente | 300 (99) |
| s3-rideau-garage-modbus | 300 (24) | absente | 300 (98) |

Modèle : `diverses.telePeriod` (37), `serveur.rangeExtender.telePeriod` (111), `serveur.udp.telePeriod` (130). Schéma : 161, 603, 668.
Le banc de l'assistant les range en TOLERANCES (`test_assistant_persist_generation.py`, 66-69) : « porté par le seul différentiel » / « par P4, cuve et rideau seulement ».

### 3.2 Lecteurs

| Clé | Lecteurs effectifs |
|---|---|
| `diverses.telePeriod` | `configGlobal.be::configGlobal_configGlobalByJson` (223-224, `data` = `diverses`, pose `TelePeriod` si différent) ; `globalFonctions.be::globalFonctions_changementEtatDemarrage` (143, réapplique `TelePeriod` à chaque `Time#Initialized`, toutes les heures) ; `udpFonctions.be::udpFonctions_reglageUDP` (293), `::udpFonctions_lanceCyclePresentation` (454), `::udpFonctions_perimeFiches` (902) ; `modbusFonctions.be::modbusFonctions_changementEtatDemarrage` (646), `::modbusFonctions_limiteFraicheur` (3192, 3 x telePeriod) |
| `serveur.udp.telePeriod` | **aucun** (aucun accès par chemin, par `find("telePeriod")` ni par `["telePeriod"]` hors `diverses`) |
| `serveur.rangeExtender.telePeriod` | **aucun** (idem) |

Piège constaté : la documentation parle de `ReglageUDP telePeriodClients` (`README.md` 812) ; **aucune** commande de ce nom dans `data/fs/*.be`. Probablement l'ancien nom de la clé morte `serveur.udp.telePeriod`.

### 3.3 Doublon avec la commande Tasmota `TelePeriod`

`diverses.telePeriod` est la source de vérité, appliquée trois fois à la commande native (`configGlobal` 223, `globalFonctions` 143, plus le firmware qui garde sa propre valeur en flash). Le commentaire de `globalFonctions` (142) explique le troisième appel : « corrige un bug sur enregistrement de `TelePeriod` dès le paramétrage du RangeExtender ». Les Berry lisent `diverses`, pas la commande : cohérent tant que les deux concordent.

## 4. Options

### 4.1 `telePeriod`

| | Laisser | Fusionner | Retirer (udp et rangeExtender) |
|---|---|---|---|
| Avantages | rien à faire ; aucun risque | — | clés mortes supprimées ; plus de question trompeuse dans l'assistant ; un seul réglage |
| Inconvénients | clés trompeuses (on croit régler le cycle UDP en la changeant) ; TOLERANCES à maintenir | sans objet : la fusion cible est `diverses.telePeriod`, déjà la seule lue | perte d'un emplacement si un cycle propre à UDP ou au RangeExtender est voulu un jour |
| Modèle | inchangé | = retirer | retirer 2 entrées (111, 130), schéma regénéré (`genere_schema_persist.py`) |
| Assistant | 2 TOLERANCES (66-69) restent | = retirer | TOLERANCES supprimées, le banc d'ordre/rejeu s'en trouve simplifié |
| Cartes en service | rien | = retirer | **sans risque fonctionnel** (aucun lecteur) ; une clé orpheline restant dans un vieux persist est ignorée |
| Bancs | inchangés | = retirer | `test_assistant_persist_generation.py` (retrait des 2 TOLERANCES), banc du schéma ; `persist.schema.json` : `additionalProperties` à vérifier |

### 4.2 `adressMAC` / `adresseMAC`

| | Laisser | Fusionner vers `adresseMAC` | Fusionner vers `adressMAC` | Retirer `adressMAC` seule |
|---|---|---|---|---|
| Avantages | zéro risque | orthographe correcte ; chemin que **11 lecteurs** utilisent déjà | — | supprime une clé jamais lue ; le code est déjà prêt |
| Inconvénients | deux clés, deux écritures, une jamais lue ; la cause du cas §2.3-1 | `globalFonctions` (87-91) à modifier ; `banc_boot.be` (301-302) à adapter ; schéma à regénérer | ~11 lignes de lecture à toucher dans 4 modules, dont le coeur ModBus ; mauvaise orthographe conservée | idem mais sans correction du cas du différentiel tant que `discovery` y est OFF |
| Modèle | inchangé | `adresseMAC: ""` à la place (73) | inchangé | retirer la ligne 73 |
| Assistant | rien | TOLERANCES/rejeu : le rejeu de l'ancien persist verrait un écart de clé sur les 8 cartes | rien | écart sur les 8 cartes à tolérer |
| Cartes en service | un persist déjà déployé garde les deux | l'ancienne clé `adressMAC` reste orpheline sur la carte (inoffensive) ; la nouvelle est reposée au 1er `System#Boot` (si `globalFonctions` l'écrit) : aucune migration à faire | forcerait `discoveryFonctions` à relire la clé que la carte n'a pas encore tant que `System#Boot` n'a pas tourné | aucune migration |
| Ordre de téléversement | indifférent | **module d'abord, persist ensuite** : un persist neuf avec un module ancien (qui lit `adresseMAC` déjà) reste correct | module et persist ensemble | indifférent |
| Carte non mise à jour | — | module ancien : écrit encore `adressMAC` (inoffensif), lit `adresseMAC` via `discovery` comme aujourd'hui | module ancien : lit `adresseMAC`, absente du persist neuf : repli `000000000000`, fiches `discovery` rangées sous la mauvaise clé | module ancien : inoffensif |
| Bancs | inchangés | `banc_boot.be`, `test_discovery.be` et `banc_test_modbus.be` utilisent déjà `adresseMAC` : à relancer ; seul `banc_boot.be` change | à réécrire en grande partie (17 occurrences `adresseMAC` dans les bancs) | `banc_boot.be` (301) |

Point clé de la fusion vers `adresseMAC` : `globalFonctions` doit **écrire** `adresseMAC` à `System#Boot` (aujourd'hui seul `discovery` le fait, au Wi-Fi). Cela corrige le cas du différentiel et supprime la seconde écriture de `discovery` (253) ou la rend inutile (le test à 252 devient faux si la MAC est déjà posée).

## 5. Recommandation (c'est une recommandation, pas une décision)

1. **`serveur.udp.telePeriod` et `serveur.rangeExtender.telePeriod` : retirer.** Zéro lecteur, zéro risque de service, simplification nette de l'assistant et du schéma. À défaut, **laisser** (aucune fusion utile).
2. **`adressMAC` / `adresseMAC` : fusionner vers `adresseMAC`**, en faisant écrire cette clé par `globalFonctions` au `System#Boot`, puis retirer `adressMAC` du modèle et du schéma. Ordre : modules d'abord (téléversement du FS), persist ensuite ; rien à migrer sur les cartes. Chantier à part, après l'assistant : touche le démarrage de toutes les cartes.
3. Si l'utilisateur préfère ne rien toucher à l'exécution : **laisser** les deux MAC, mais noter dans le modèle que `adressMAC` n'est lue par personne, et vérifier sur la carte du différentiel si `forceEnvoiParams` y est utilisé (§2.3-1).

## 6. Ce qui n'est pas prouvé

- Contenu des persists des cartes en service (seuls ceux du dépôt ont été lus, présence et valeur de ces clés uniquement).
- Que le différentiel émette un `forceEnvoiParams` (usage réel de la ligne 265 chez lui).
- Qu'aucun script PC externe au dépôt ne lise ces clés.
