---
chantier: classement-par-lieu
titre: Classement des cartes par lieu dans les pages des outils PC
objectif: Retrouver les cartes par emplacement dans la maison sur la page Build (bascule Famille/Lieu/Puce, intertitres de l'onglet Fichiers) et dans les listes de carte des autres pages
statut: clos
cree: 2026-11-10
maj: 2026-11-11
---
# Classement des cartes par lieu — plan de mise en œuvre

> Pour l'exécutant : skill superpowers:subagent-driven-development (recommandée) ou superpowers:executing-plans,
> action par action. Cocher chaque étape dès qu'elle est vérifiée, avec « — preuve : … ».

**But** : classer ou regrouper par lieu les cartes des pages Build (7700), Fichiers Berry (7800), Assistant persist
(7900), Atelier des graphiques (7950) et Fabrique d'extensions (7980).

**Architecture** : un module Python `lieux.py` tire le lieu et la puce du nom d'env et porte la table des lieux, ainsi
qu'un petit morceau de JavaScript commun qui remplit une liste déroulante groupée par lieu. Chaque serveur ajoute `lieu`
à ses cartes et `lieux` à sa réponse. Le JavaScript des pages ne contient aucun libellé de lieu.

**Pile** : Python 3 stdlib (`http.server`), JavaScript sans bibliothèque dans des constantes Python, sondes Chrome par
DevTools (modèle `test_build_page_chrome.py`), bancs scripts (code de sortie 0 = vert) lancés avec le Python de
PlatformIO (`~/.platformio/penv/Scripts/python.exe`).

**Spec** : `docs/superpowers/specs/2026-11-10-classement-par-lieu-design.md` (à lire avant toute action). Maquettes :
`outils_docs/filtre_lieu/` (modèles D, F, H retenus).

## Contexte

Choix de l'utilisateur du 2026-11-10 : modèle D pour l'onglet Build (bascule « Classer par » Famille / Lieu / Puce,
case de groupe par lieu), F pour l'onglet Fichiers (intertitres), H pour les listes déroulantes (`<optgroup>`) ; lieux,
ordre et piscine en « Extérieur » validés ; groupes de lieu ouverts à l'arrivée seulement s'ils contiennent une carte
cochée. Décisions de Claude, listées dans la spec : groupe « Autres », case de groupe sur les cartes visibles seulement,
classement mémorisé (`localStorage`, défaut Famille), bases de l'onglet Mémoire en bas, module `build_page_lieux.py`.

### Contraintes globales
- Table des lieux, dans cet ordre : `etage2` « 2e étage », `rdc` « Rez-de-chaussée », `cave` « Cave », `garage`
  « Garage », `bureau` « Bureau », `exterieur` « Extérieur ». Exception : `tasmota-pompe-piscine` → `exterieur`.
  Segment hors table → groupe « Autres » (libellé = code brut), en dernier.
- Puces : `tasmota32` → `ESP32`, `tasmota32s3` → `ESP32-S3`, `tasmota32p4` et `tasmota32p4r3` → `ESP32-P4`,
  `tasmota` → `ESP8266`.
- Le classement est un affichage : ni les cases cochées, ni COM/OTA, ni un port ou une IP saisis, ni `POST /lancer` ne
  changent quand on bascule.
- Thèmes clair et sombre par les variables de `build_page.py`, aucune couleur en dur. Accès à `localStorage` dans un
  try/catch.
- `build_page.py` (1223 lignes) ne grossit que du branchement ; sinon, mettre à jour sa ligne dans `CLAUDE.md`.
- Commits en français, sans accents, sans `Co-Authored-By`, `git commit -- <chemins>`, relire `git show --stat HEAD`.
- Aucun `pio run` : rien ici ne touche au firmware.

### Points de vigilance (non couverts par les tests de la spec, un test chacun ci-dessous)
1. Un env coché, masqué par le filtre par nom → avertissement orange visible, et l'env reste dans le corps de
   `POST /lancer` (testé en A3).
2. Une IP saisie dans le champ OTA d'une carte, puis bascule Famille → Lieu → Famille → l'IP est toujours dans le champ
   (A3).
3. `localStorage` qui lève une exception → la page s'ouvre en Famille, sans erreur dans la console (A3).
4. Une carte au lieu hors table (env `tasmota32s3-jardin-essai` du faux dépôt) → groupe « Autres » en dernier sur la
   page Build, dans l'onglet Fichiers et dans une liste déroulante (A1, A3, A4, A5).
5. Rechargement de la liste (`chargeEnvs` après `POST /port`) en classement Lieu → la page reste en Lieu, la règle
   d'ouverture est recalculée (A3).

---

## A1 — Module `lieux.py` et son banc

Fichiers : créer `outils_docs/scripts_python/outils_pc/lieux.py` et `test_lieux.py`.

Interfaces produites (utilisées par A2 à A5) :
- `LIEUX: list[tuple[str, str]]` (code, libellé), dans l'ordre des contraintes ; `EXCEPTIONS: dict[str, str]`.
- `lieu(env: str) -> str | None` : `None` si `fichiers_berry_etat.est_base(env)` ou nom sans tiret ; sinon exception
  ou 2e segment, tel quel s'il est hors table. À n'appeler que sur des cartes.
- `puce(env: str) -> str` : selon le 1er segment ; 1er segment inconnu → le segment tel quel.
- `pour_page() -> dict` : `{"lieux": [[code, libellé], ...]}`.
- `JS: str` : fonction JavaScript `remplitParLieu(select, cartes, lieux, choisi, bases)` qui vide `select`, ajoute un
  `<optgroup>` par lieu présent (ordre de `lieux`, puis « Autres » pour un `lieu` hors table, libellé = code), les
  options dans l'ordre reçu, puis un `<optgroup label="Mes bases">` si `bases` n'est pas vide, et sélectionne `choisi`.
  `cartes` et `bases` : tableaux `{nom, lieu}` ; texte posé par `textContent`, jamais par `innerHTML`.

- [x] Écrire `test_lieux.py` (style `test_build_envs.py` : `verifie(obtenu, attendu, libelle)`, code de sortie) : — preuve : test_lieux.py (74bf64124)
  - les 11 cartes réelles (`build_envs.liste_envs(RACINE)`, famille `cartes`) ont un lieu de `LIEUX` ;
    `lieu("tasmota32s3-garage-capteurs-cuve-modbus") == "garage"`, `lieu("tasmota-pompe-piscine") == "exterieur"` ;
  - les 6 bases → `None` ; `lieu("tasmota32s3-jardin-essai") == "jardin"` ; `lieu("sanstiret") is None` ;
  - `puce` : `tasmota32-rdc-vr-porte` → `ESP32`, `tasmota32s3-etage2-grenier` → `ESP32-S3`,
    `tasmota32p4r3-base-devkit` → `ESP32-P4`, `tasmota-pompe-piscine` → `ESP8266` ;
  - `pour_page()["lieux"][0] == ["etage2", "2e étage"]` et 6 entrées ;
  - `JS` contient `function remplitParLieu(` et ne contient pas `innerHTML`.
- [x] Le lancer avant le module : échec à l'import attendu. — preuve : RED ModuleNotFoundError lieux (rapport A1)
- [x] Écrire `lieux.py` ; banc vert (`python test_lieux.py`, sortie 0). — preuve : test_lieux.py sortie 0, relecture approuvee
- [x] Commit `feat(lieux): table des lieux et puces tirees du nom d'env, banc test_lieux`. — preuve : 74bf64124

## A2 — Les serveurs servent `lieu` et `lieux`

Interfaces consommées : `lieux.lieu`, `lieux.puce`, `lieux.pour_page` (A1).
Interfaces produites : dans chaque réponse ci-dessous, chaque carte porte `lieu` (str ou null) et la réponse porte
`lieux` ; `/envs` de la page Build porte aussi `puce` sur chaque env.

| Route | Fichier | Banc existant à étendre |
|---|---|---|
| `GET /envs` | `build_web.py::liste_envs_json` (+ `puce`, `lieu` sur la famille `cartes`, `null` ailleurs) | `test_build_web.py` |
| `GET /envs` | `fichiers_berry_web.py` | `test_fichiers_berry_web.py` |
| `GET /parc` | `assistant_persist_web.py` (cartes) | `test_assistant_persist_web.py` |
| `GET /envs` | `atelier_graphiques_web.py` | `test_atelier_graphiques_web.py` |
| `GET /cartes` | `tapp_web.py` | `test_tapp_web.py` |

- [x] Pour chaque route : ajouter au banc l'assertion « une carte du garage a `lieu == "garage"` et la réponse a
  `lieux` de 6 entrées » ; la voir échouer.
- [x] Ajouter les champs (une ligne par route, par `lieux.lieu` / `lieux.pour_page`) ; les 5 bancs verts. — preuve : 5 bancs verts (rapport A2), relecture approuvee
- [x] Commit `feat(lieux): lieu de chaque carte dans les reponses des pages 7700 a 7980`. — preuve : 8265a763f

## A3 — Onglet Build : modèle D

Fichiers : créer `outils_pc/build_page_lieux.py` (`CSS`, `JS`) ; brancher dans `build_page.py` (marques
`/*CSS_LIEUX*/` et `/*JS_LIEUX*/`, comme `build_page_memoire`) ; créer la sonde `test_build_page_lieux_chrome.py`, qui
réutilise le serveur et le client DevTools de `test_build_page_chrome.py` (import du module voisin), avec un faux dépôt
qui contient en plus `tasmota32s3-jardin-essai`.

Interfaces consommées : `/envs` avec `lieu`, `puce`, `lieux` (A2) ; dans `build_page.py` : `construitListe`,
`ligneEnv`, `majComptes`, `chargeEnvs`, `FAMILLES`, l'état `choix`.
Interfaces produites : `classement` (`"famille" | "lieu" | "puce"`), clé `localStorage` `build.classement`.

Comportement (spec §5) : barre « Classer par » [Famille | Lieu | Puce] + champ « Filtrer par nom… » au-dessus de la
liste ; en Lieu ou Puce, les cartes vont dans un `details` par groupe, « Mes bases » et l'amont suivent tels
qu'aujourd'hui ; case d'en-tête par groupe (cartes visibles seulement, `indeterminate`, compteur sur tout le groupe, le
clic ne replie pas) ; groupe ouvert s'il contient une carte cochée ; la bascule redessine par `construitListe`, l'état
vit dans `choix`.

- [x] Écrire la sonde, rouge d'abord, avec ces vérifications : — preuve : test_build_page_lieux_chrome.py (03e1748c2, 6e3457f67), 26 vérifications vertes, témoin rouge
  - bascule sur Lieu : 7 groupes de cartes dans l'ordre 2e étage … Extérieur puis « Autres » (jardin), puis Mes bases,
    puis amont ; un groupe sans coché est fermé, un groupe avec coché est ouvert ;
  - Puce : groupes ESP32, ESP32-S3, ESP32-P4, ESP8266, sans groupe vide ;
  - case du garage avec 3 cochés sur 4 → `indeterminate` ; clic → les 4 cochés, le groupe reste ouvert ;
  - filtre « cuve » puis clic sur la case du garage décochée → seule la cuve change ;
  - (vigilance 1) env coché masqué par le filtre → avertissement visible ; `POST /lancer` intercepté le contient ;
  - (vigilance 2) IP saisie, Famille → Lieu → Famille → IP intacte ;
  - (vigilance 3) `localStorage.getItem` remplacé par une fonction qui lève → page en Famille, aucune exception en
    console ;
  - (vigilance 5) en Lieu, rechargement par `chargeEnvs(true)` → toujours Lieu ;
  - classement Lieu choisi, page rechargée → toujours Lieu ;
  - témoin négatif : sans `build_page_lieux.JS` branché, la sonde échoue sur la première vérification.
- [x] Écrire `build_page_lieux.py` et le branchement ; sonde verte ; `test_build_page_chrome.py` toujours vert. — preuve : 03e1748c2, 6e3457f67 ; test_build_page_chrome.py VERT 101/101 le 2026-11-11, machine calme (un passage précédent : 1 KO ERR_EMPTY_RESPONSE de sonde_redemarrage, course de la sonde qui tue le serveur pendant POST /lancer, fichier inchangé depuis 53958588c)
- [x] Capture d'écran claire et sombre en Lieu, comparée à `outils_docs/filtre_lieu/modele-D.png`. — preuve : captures build-lieux-clair/sombre.png du scratchpad, conformes au modèle D
- [x] Commit `feat(build): bascule Classer par famille, lieu ou puce dans l'onglet Build`. — preuve : 03e1748c2, bdfa46462, 6e3457f67

## A4 — Onglet Fichiers : modèle F

Fichiers : `build_page_fichiers.py::fichiersCartes` (+ CSS de l'intertitre), sonde `test_build_page_fichiers_chrome.py`.
Interfaces consommées : `envs` de la page avec `lieu` et `lieux` (A2).

- [x] Ajouter à la sonde, rouge d'abord : intertitres « 2E ÉTAGE · 1 » … dans l'ordre de la table, « Autres » en — preuve : sonde_lieux (8ce312c97), détail en fin d'étape
  dernier (vigilance 4) ; l'arrivée `?env=tasmota32s3-garage-capteurs-cuve-modbus&depuis=atelier`
  (`sonde_atelier`) sélectionne toujours la cuve. — preuve : test_build_page_fichiers_chrome.py::sonde_lieux, rouge (obtenu []) puis vert ; lieu hors table « jardin » en dernier
- [x] Insérer les intertitres (`textContent`, couleur `--doux`) ; sonde verte. — preuve : build_page_fichiers.py (8ce312c97), sonde verte, relecture approuvée
- [x] Commit `feat(build): intertitres de lieu dans la liste des cartes de l'onglet Fichiers`. — preuve : 8ce312c97

## A5 — Listes déroulantes : modèle H

Interfaces consommées : `lieux.JS` (`remplitParLieu`), `lieu` et `lieux` des réponses (A2). Chaque page insère
`lieux.JS` dans son script, une fois.

| Liste | Fichier::fonction | Sonde existante à étendre |
|---|---|---|
| `#m-env` | `build_page_memoire.py::mEnvs` (bases dans « Mes bases », en bas) | `test_build_page_memoire_chrome.py` |
| `#s-env` | `build_page_sauvegarde.py::sEnvs` | `test_build_page_sauvegarde_chrome.py` |
| `#env`, `c-modele` | `fichiers_berry_page.py::chargeEnvs` (« Mes bases » gardé ; `c-base` inchangé) | `test_fichiers_berry_page_chrome.py` |
| `#f-env`, `#a-env` | `assistant_persist_page_js_env.py::dessineListeEnv` et le remplissage de `#a-env` | `test_assistant_persist_page_chrome.py` |
| `#env` | fin de `atelier_graphiques_page_js.py` (`#r-page` non touché) | `test_atelier_graphiques_page_chrome.py` |
| `#e-carte` | `tapp_page.py` | `test_tapp_page_chrome.py` |

- [x] Pour chaque liste, ajouter à sa sonde, rouge d'abord : premier `optgroup` « 2e étage » (ou le premier lieu — preuve : 79932b773, rouge puis vert sur 6 sondes ; #f-env : rouge non observé (voir étape suivante)
  présent pour l'atelier), la cuve sous « Garage », valeur choisie conservée après rechargement de la liste.
- [x] Remplacer chaque remplissage par `remplitParLieu` ; les 6 sondes vertes. — preuve : 79932b773 ; sondes Fichiers Berry, Mémoire, Sauvegarde, Atelier, Tapp, autoexec VERT ; #f-env vérifié par script jetable, test_assistant_persist_page_chrome.py bloqué avant l'assertion par 11 KO dus à modele_persist.json modifié par une autre session
- [x] Commit `feat(lieux): listes de cartes groupees par lieu sur les pages 7700 a 7980`. — preuve : 79932b773

## A6 — Documentation, relecture, essai réel

- [x] `outils_docs/README.md` : une ligne par page concernée, aux sections existantes ; `outils_docs/filtre_lieu/README.md` : — preuve : 4142445d2 ; verifie_references_docs.py code 0
  « réalisé » et les fichiers ; `CLAUDE.md` (carte des documents) : `lieux.py`, `build_page_lieux.py`, la sonde ;
  `python outils_docs/scripts_python/maintenance/verifie_references_docs.py` → code 0.
- [x] Agent `relecteur-pages-web` sur les commits de A3 à A5 ; corriger ce qu'il confirme. — preuve : relecture sans bloquant ; défaut « liste vide si la carte choisie a disparu » corrigé en fd96dbdad (rouge puis vert) ; mineur lieuxTable vérifié sans défaut (posée par construitListe avant mEnvs/sEnvs)
- [x] Essai réel : page Build sur :7700 dans Chrome, bascule Lieu, les 11 vraies cartes rangées comme la maquette D, — preuve : 2026-11-11, 5 vraies pages sur le dépôt réel (Chrome sans fenêtre) : 12 cartes en 6 lieux, 8 cochés identiques avant/après Lieu et Puce, intertitres Fichiers, listes 7800/7900/7950/7980 groupées ; capture reel-build-lieu.png du scratchpad conforme au modèle D
  rien coché ni décoché par la bascule ; une liste de chaque autre page vue groupée.
- [x] Commit `docs(lieux): mode d'emploi et carte des documents du classement par lieu`. — preuve : 4142445d2

## Améliorations restantes
- [x] [projet] Lieu transmis d'une page à l'autre depuis l'annuaire (écarté de cette version, spec §2). — preuve : plan `lieu-partage-syslog-mqtt` (clos le 2026-11-11), commits 335e4493b à 12dcee5b3
- [x] [projet] Table hôte → lieu pour le syslog et le sniffeur MQTT, si le besoin revient. — preuve : plan `lieu-partage-syslog-mqtt` (clos le 2026-11-11), commits 335e4493b à 12dcee5b3

## Vérification
Bancs : `test_lieux.py`, les 5 bancs web de A2, `test_build_page_lieux_chrome.py`, et les sondes de A4 et A5, tous à
code de sortie 0 avec le Python de PlatformIO. Essai réel de A6.
