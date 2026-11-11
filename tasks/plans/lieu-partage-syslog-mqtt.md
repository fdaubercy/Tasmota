---
chantier: lieu-partage-syslog-mqtt
titre: Lieu partagé depuis l'annuaire, lieu dans le syslog et le sniffeur MQTT
objectif: Choisir un lieu une fois dans l'annuaire et le retrouver dans les pages ouvertes, et ranger par lieu les lignes du syslog et les messages du sniffeur MQTT
statut: actif
cree: 2026-11-11
maj: 2026-11-11
---
# Lieu partagé, syslog et sniffeur MQTT — plan de mise en œuvre

> Pour l'exécutant : skill superpowers:subagent-driven-development (choisie par l'utilisateur), action par action.
> Cocher chaque étape dès qu'elle est vérifiée, avec « — preuve : … ».

**But** : modèle J dans l'annuaire (7600), mise en avant à l'arrivée sur les pages 7700 à 7980 et 7100/7200, modèle M
dans le syslog (7200), modèles N et O dans le sniffeur MQTT (7100).

**Architecture** : `lieux.py` gagne `identites(racine)` (nom d'hôte, topic, IP de chaque carte, lus dans son persist et
dans le `.h`) et quatre fonctions JavaScript pures dans `lieux.JS` : reconnaître le lieu d'une ligne syslog et d'un topic,
lire `?lieu=`, poser le bandeau. L'annuaire porte `?lieu=` dans ses liens ; chaque page lit le paramètre au premier
chargement. Syslog et sniffeur MQTT servent `GET /lieux` et rangent leurs lignes dans le navigateur.

**Pile** : Python 3 stdlib (`http.server`), JavaScript sans bibliothèque dans des constantes Python, Node pour les
fonctions JS pures, sondes Chrome par DevTools (modèle `test_build_page_chrome.py` : `Cdp`, `attend`, `port_libre`,
`tue_arbre`), bancs à code de sortie 0 = vert, lancés avec le Python de PlatformIO (`~/.platformio/penv/Scripts/python.exe`).

**Spec** : `docs/superpowers/specs/2026-11-11-lieu-partage-syslog-mqtt-design.md` (à lire avant toute action). Maquettes :
`outils_docs/filtre_lieu/modele-J.png`, `modele-M.png`, `modele-N.png`, `modele-O.png`.

## Contexte

Suite du plan clos `tasks/plans/classement-par-lieu.md` (module `lieux.py`, `remplitParLieu`, bascule de la page Build
dans `build_page_lieux.py`). Choix de l'utilisateur du 2026-11-11 : J, mise en avant (rien n'est caché), M, N et O.

### Contraintes globales
- Seule table des lieux : `lieux.LIEUX` (`etage2`, `rdc`, `cave`, `garage`, `bureau`, `exterieur`). Aucun libellé de lieu
  en dur dans une page. Hôte ou topic sans carte → « Autres ».
- `?lieu=` n'est lu qu'au PREMIER chargement d'une page et seulement s'il est un code de la table. Il ne coche, ne
  décoche, ne change aucun port ni IP, n'ouvre aucun mode modification, ne réécrit pas le classement mémorisé de la
  page Build. Page ouverte sans `?lieu=` : comportement d'aujourd'hui.
- Bandeau commun : « Lieu : <libellé> (depuis l'annuaire) · Tous les lieux ✕ ». « ✕ » retire le paramètre
  (`history.replaceState`) et le bandeau, ne change aucune liste ; la page Build revient à son classement mémorisé.
- Le lieu choisi dans le syslog ou le sniffeur MQTT n'est pas mémorisé d'une visite à l'autre ; le filtre MQTT ne
  touche pas aux abonnements.
- Texte venu d'une carte, d'un broker ou de l'adresse : `textContent`, propriétés, ou l'échappement existant de la page
  (`esc` du syslog, `echappe` du sniffeur MQTT). `localStorage` dans un try/catch.
- Fichiers sous 500 lignes : `annuaire_page.py` (468) ne grossit que du branchement ; code neuf dans des modules voisins.
- Aucun `pio run`, aucune émission vers le vrai broker ni vers le vrai syslog (514) pendant les bancs.
- Commits en français, sans accents, sans `Co-Authored-By`, `git commit -- <chemins>`, relire `git show --stat HEAD`.
  Ne jamais commiter `tasks/README.md` ni un fichier d'une autre session.

### Points de vigilance (un test chacun, dans l'action indiquée)
1. Nom d'hôte reçu dans une autre casse (`capteurs-cuve`) → Garage (A1).
2. `tele/garage/niveau/STATE` → topic `garage/niveau` ; `tele/garagex/STATE` → aucun lieu (préfixe suivi de `/`) (A1).
3. `?lieu=inconnu` ou `?lieu=<b>x</b>` → ignoré, aucun bandeau, aucune balise créée (A1, A4).
4. Esclave derrière le NAPT : nom d'hôte `RIDEAU-GARAGE` arrivant de l'IP du maître → Garage par son nom, pas par l'IP
   (A1) ; ligne d'un hôte inconnu venant de `192.168.0.46` → Rez-de-chaussée par l'IP (A1, A5).
5. Visite avec `?lieu=garage` puis réouverture sans paramètre → syslog et MQTT sur « Tous », page Build sur son
   classement mémorisé (A3, A5, A6).

---

## A0 — Plan précédent : classement par lieu

Plan d'origine de ce chantier, clos le 2026-11-11 : [tasks/plans/classement-par-lieu.md](classement-par-lieu.md)
(spec `docs/superpowers/specs/2026-11-10-classement-par-lieu-design.md`).

- [ ] Rouvrir le plan précédent dans la vue de droite : taper `/suivi suivre classement-par-lieu` (la conversation suit
  alors ce plan, qui reste clos et inchangé) ; revenir à celui-ci : `/suivi suivre lieu-partage-syslog-mqtt`. À cocher
  quand l'aller-retour a été fait une fois et que la vue a basculé dans les deux sens.

## A1 — `lieux.py` : identités des cartes et fonctions JS communes

Fichiers : modifier `outils_docs/scripts_python/outils_pc/lieux.py`, `test_lieux.py` ; créer `test_lieux_js.mjs`.

Interfaces produites :
- `identites(racine) -> list[dict]` : un dict `{"env", "lieu", "hote", "topic", "ip"}` par carte (famille `cartes` de
  `build_envs.liste_envs(racine)`, dans son ordre) ; `hote` = `serveur.hostname`, `topic` = `serveur.mqtt.topic` du
  persist (`build_envs.persist_carte`), "" si persist absent ou illisible ; `ip` = `Env.ip` si `Env.ip_source == "h"`,
  sinon "".
- `pour_page_identites(racine) -> dict` : `{"lieux": [[code, libellé], ...], "cartes": identites(racine)}` (réponse de
  `GET /lieux`).
- Dans `lieux.JS`, en plus de `remplitParLieu` :
  - `lieuDeHote(module, ipSource, cartes) -> string|null` : `hote` égal sans casse à `module`, sinon `ip` égale à
    `ipSource` ; 1re carte trouvée dans l'ordre reçu.
  - `lieuDeTopic(topic, cartes, nu) -> string|null` : sans `nu`, 1er segment retiré ; puis carte au `topic` le plus long
    égal au reste ou préfixe du reste suivi de `/`. Rend le code du lieu ; `cartes` sans `topic` ignorées.
  - `lieuDemande(lieux) -> string|null` : `?lieu=` de `location.search` s'il est un code de `lieux`, sinon `null`.
  - `bandeauLieu(parent, libelle, surFermeture)` : insère en tête de `parent` un `div.bandeau-lieu` (texte par
    `textContent`) avec un bouton « Tous les lieux ✕ » qui retire `lieu` de l'adresse, retire le bandeau, appelle
    `surFermeture()`. Rend l'élément. Style : à la charge de chaque page (classe `bandeau-lieu`).

- [x] Ajouter à `test_lieux.py`, rouge d'abord : `identites(RACINE)` contient la cuve
  `{"env": "tasmota32s3-garage-capteurs-cuve-modbus", "lieu": "garage", "hote": "CAPTEURS-CUVE", "topic": "jardin/cuve", "ip": ""}`
  (esclave : `ip_source` ≠ `h`) ; toutes les cartes ont `lieu` dans la table ; `tasmota-pompe-piscine` a `hote == ""` ;
  `pour_page_identites(RACINE)["lieux"][0] == ["etage2", "2e étage"]`. — preuve : commit 52a21d1ee, test_lieux.py VERT (temoin : ip sans filtre ip_source -> ECHEC cuve)
- [x] Écrire `test_lieux_js.mjs` (Node, sans DOM : évalue `lieux.JS` lu par `python -c "import lieux; print(lieux.JS)"`
  ou extrait du fichier), rouge d'abord, avec une table de 5 cartes copiée du dépôt (grenier, P4 `garage`, S3 `garage/niveau`,
  cuve `jardin/cuve`, rideau `garage/rideau`, porte `rdc` avec `hote` "" et `ip` `192.168.0.46`) : vigilances 1, 2, 4 ;
  `lieuDeTopic("stat/jardin/cuve/RESULT")` → `garage` ; `lieuDeTopic("garage/rideau", cartes, true)` → `garage` ;
  `lieuDeTopic("zigbee2mqtt/bridge/state")` → `null`. `lieuDemande` testé avec un faux `location` global :
  `?lieu=cave` → `cave`, `?lieu=inconnu` et `?lieu=%3Cb%3Ex` → `null` (vigilance 3). Code de sortie 1 sur échec. — preuve : commit 52a21d1ee, test_lieux_js.mjs VERT (temoins : prefixe sans / et casse -> ECHEC)
- [x] Écrire `identites`, `pour_page_identites` et les quatre fonctions JS ; `test_lieux.py` et `test_lieux_js.mjs` verts ;
  sondes qui insèrent `lieux.JS` toujours vertes : `test_fichiers_berry_page_chrome.py`, `test_tapp_page_chrome.py`. — preuve : commit 52a21d1ee, test_lieux.py et test_lieux_js.mjs VERT, sondes test_fichiers_berry_page_chrome.py et test_tapp_page_chrome.py VERT
- [x] Commit `feat(lieux): identites des cartes et fonctions communes du lieu partage`. — preuve : commit 52a21d1ee

## A2 — Annuaire : modèle J

Fichiers : modifier `annuaire_registre.py` (champ `lieu` de `Outil`, `en_json`), `annuaire_page.py` (branchement seul) ;
créer `annuaire_page_lieux.py` (CSS + JS) et la sonde `test_annuaire_lieux_chrome.py`.

Interfaces consommées : `lieux.LIEUX`, `lieux.lieu`, `build_envs.liste_envs`. Produites : `Outil.lieu: bool = False`,
vrai pour Build, Fichiers Berry, Assistant persist, Atelier, Fabrique, syslog, sniffeur MQTT ; `en_json()` ajoute
`"lieux": [[code, libellé, nombre d'envs de cartes], ...]` et `"lieu": bool` à chaque outil.

- [x] Sonde neuve, rouge d'abord (annuaire lancé sur un port libre, `--local --sans-navigateur`, fiche de présence d'un
  outil simulée en marche si la page l'exige, sinon contrôle de l'adresse construite par la fonction de lien) : rangée
  « Lieu de travail » = `Tous` + 6 puces dans l'ordre de la table, Garage avec son nombre ; clic Garage → lien d'un
  outil marqué = `…/?lieu=garage`, lien avec `?jeton=x` → `…?jeton=x&lieu=garage`, outil non marqué (Pont série)
  inchangé ; rechargement → Garage toujours choisi ; `localStorage.getItem` qui lève → page sur Tous, aucune exception ;
  témoin : sans le module branché, la 1re vérification échoue. — preuve : test_annuaire_lieux_chrome.py : temoin (page sans le module) KO sur la rangee, page reelle 17 OK ; mutant `&` -> `?` KO
- [x] Écrire le champ, `en_json`, `annuaire_page_lieux.py` et le branchement ; sonde verte ; `test_annuaire.py`,
  `test_annuaire_lanceur.py`, `test_annuaire_securite.py` verts. — preuve : sonde VERT ; test_annuaire, test_annuaire_lanceur, test_annuaire_securite, test_lieux, test_lieux_js.mjs VERT
- [x] Commit `feat(annuaire): lieu de travail porte par les liens des outils`. — preuve : commit feat(annuaire) (voir git log)

## A3 — Arrivée sur la page Build (7700)

Fichiers : modifier `build_page_lieux.py` (classement de la visite, ouverture, bandeau), `build_page_fichiers.py`
(`fichiersCartes`, choix initial), `build_page_memoire.py::mEnvs`, `build_page_sauvegarde.py::sEnvs` ; sonde
`test_build_page_lieux_chrome.py`.

Interfaces consommées : `lieuDemande`, `bandeauLieu` (A1) ; `lieuxTable`, `classement` de `build_page_lieux.py`.

- [x] Ajouter à la sonde, rouge d'abord : page ouverte en `?lieu=garage` avec le classement mémorisé Famille →
  classement Lieu affiché, `localStorage` toujours « famille », groupe Garage ouvert et les autres groupes de lieu fermés,
  cases cochées et corps de `POST /lancer` identiques à une ouverture sans paramètre ; bandeau présent ; onglet Fichiers :
  1re carte du garage choisie ; liste `#m-env` : 1re carte cochée du garage ; « ✕ » → classement Famille, bandeau retiré,
  `location.search` sans `lieu`, `#m-env` inchangée ; réouverture sans paramètre → Famille (vigilance 5) ; `?env=` de
  l'atelier + `?lieu=cave` → la carte de `?env=` gagne dans l'onglet Fichiers. — preuve : test_build_page_lieux_chrome.py::sonde_arrivee, rouge d'abord (lieuxFichiers inconnu au temoin) puis 17 verifications vertes, 5 temoins negatifs rouges (voir task-3-report.md)
- [x] Écrire ; sonde verte ; `test_build_page_chrome.py`, `test_build_page_fichiers_chrome.py`,
  `test_build_page_memoire_chrome.py`, `test_build_page_sauvegarde_chrome.py` verts. — preuve : sondes lieux, chrome, fichiers, memoire, sauvegarde : code de sortie 0
- [x] Commit `feat(build): lieu venu de l'annuaire mis en avant dans la page Build`. — preuve : commit feat(build) A3 (SHA dans task-3-report.md)

## A4 — Arrivée sur les pages 7800, 7900, 7950, 7980

Fichiers : `fichiers_berry_page.py` (`chargeEnvs`, 1er appel seulement), `assistant_persist_page_js_env.py` (bandeau),
`atelier_graphiques_page_js.py` (choix initial), `tapp_page.py` (bandeau) ; leurs sondes.

- [ ] Ajouter à chaque sonde, rouge d'abord, une ouverture en `?lieu=garage` : 7800 `#env` = 1re carte du garage,
  puis `chargeEnvs()` rappelé avec une autre carte choisie → choix gardé (le lieu ne rejoue pas), `?env=` + `?lieu=`
  → `?env=` gagne ; 7900 `#f-env` et `#a-env` sur leur option de tête, bandeau présent ; 7950 `#env` = 1re carte S3/P4 du
  garage, et `?lieu=rdc` (aucune S3/P4) → liste comme sans paramètre + bandeau « aucune carte de ce lieu ici » ; 7980
  `#e-carte` sur « (choisir une carte) », bandeau ; une page en `?lieu=%3Cb%3Ex` → aucun bandeau, aucun `<b>` créé
  (vigilance 3).
- [ ] Écrire ; les 4 sondes vertes (7900 : si `test_assistant_persist_page_chrome.py` reste bloquée par
  `modele_persist.json` d'une autre session, vérifier le bandeau par la sonde autoexec et le noter dans la preuve).
- [ ] Commit `feat(lieux): lieu venu de l'annuaire sur les pages 7800 a 7980`.

## A5 — Syslog : modèle M

Fichiers : `syslog_tasmota.py` (route `GET /lieux`), `syslog_tasmota_web.py` (puces, étiquettes, filtre, `?lieu=`) ;
`test_syslog_acces.py` ; créer `test_syslog_page_chrome.py`.

Interfaces consommées : `pour_page_identites(RACINE)`, `lieuDeHote`, `lieuDemande`, `bandeauLieu`.

- [ ] Banc d'accès : `GET /lieux` répond 200 en JSON depuis ce PC, avec la même protection que `/modules` depuis un
  autre appareil (rouge d'abord).
- [ ] Sonde neuve, rouge d'abord : vrai `syslog_tasmota.py` sur un port UDP et un port HTTP libres (`--port`, `--http`,
  `--local`), datagrammes RFC5424 envoyés par la sonde à 127.0.0.1 : `CAPTEURS-CUVE` (info), `RIDEAU-GARAGE` (sévérité 3),
  `SERVEUR-GRENIER-2EME`, `tasmota-4F2A1C`. Puces : Garage 2 lignes et 1 erreur, 2e étage 1, Autres 1 ; étiquettes
  « Garage », « Autres » en tête des lignes ; clic Garage → 2 lignes, barre des modules réduite au garage ; filtre texte
  combiné ; `?lieu=garage` → puce Garage active dès l'ouverture, bandeau ; ouverture sans paramètre après celle-ci →
  Tous (vigilance 5) ; hôte `<b>x</b>` → aucune balise créée. Hôte inconnu reconnu par l'IP : la sonde ne pouvant pas
  émettre depuis `192.168.0.46`, ce cas reste au banc Node de A1.
- [ ] Écrire ; banc d'accès et sonde verts.
- [ ] Commit `feat(syslog): lignes rangees et filtrees par lieu`.

## A6 — Sniffeur MQTT : modèles N et O

Fichiers : `sniffeur_mqtt.py` (route `GET /lieux`), `sniffeur_mqtt_web.py` (puces, étiquettes, `?lieu=`),
`sniffeur_mqtt_panneaux.py` (arborescence par lieu, `#logModule` et `#cmdModule` groupées) ; `test_sniffeur_mqtt_acces.py` ;
créer `test_sniffeur_mqtt_page_chrome.py`.

Interfaces consommées : `pour_page_identites`, `lieuDeTopic` (avec `nu` pour les listes), `remplitParLieu`,
`lieuDemande`, `bandeauLieu`.

- [ ] Banc d'accès : `GET /lieux` comme en A5 (rouge d'abord).
- [ ] Sonde neuve, rouge d'abord : vrai serveur sans broker joignable (hôte de broker sur un port fermé), messages
  injectés par `Sniffeur.recu` dans un mode serveur de la sonde (comme `--serveur` des autres sondes) : `tele/jardin/cuve/SENSOR`,
  `stat/garage/rideau/RESULT`, `tele/etage2/grenier/STATE`, `zigbee2mqtt/bridge/state`. Puces : Garage 2, 2e étage 1,
  Autres 1 ; étiquettes ; clic Garage → 2 messages, abonnements (`/etat`) inchangés ; arborescence : 1er niveau
  `2e étage`, `Garage`, `Autres` dans cet ordre, `jardin/cuve` sous Garage avec son env ; `#logModule` et `#cmdModule` ont
  un `optgroup` Garage ; `?lieu=garage` → puce active, bandeau ; réouverture sans paramètre → Tous ; topic `<b>x</b>` →
  aucune balise.
- [ ] Écrire ; banc d'accès, sonde et `test_build_ota_mqtt.py` (client MQTT partagé) verts.
- [ ] Commit `feat(sniffeur-mqtt): messages et arborescence ranges par lieu`.

## A7 — Documentation, relecture, essai réel

- [ ] `outils_docs/README.md` : une phrase par page (annuaire, syslog, sniffeur MQTT, arrivée avec `?lieu=` dans la
  section Build) ; `outils_docs/filtre_lieu/README.md` : suite réalisée ; `CLAUDE.md` (carte des documents, entrée du
  classement par lieu) : `identites`, `annuaire_page_lieux.py`, les trois sondes neuves ;
  `maintenance/verifie_references_docs.py` → code 0.
- [ ] Agent `relecteur-pages-web` sur les commits de A1 à A6 ; corriger ce qu'il confirme.
- [ ] Essai réel, sans rien envoyer : annuaire, syslog et sniffeur MQTT sur le vrai dépôt (ports libres), lignes et
  messages réels s'il y en a ; un lien de l'annuaire en Garage ouvre la page Build en Lieu, groupe Garage ouvert.
- [ ] Commit `docs(lieux): mode d'emploi du lieu partage, du syslog et du sniffeur MQTT`.

## Améliorations restantes

## Vérification
Bancs : `test_lieux.py`, `node test_lieux_js.mjs`, `test_annuaire*.py`, `test_syslog_acces.py`,
`test_sniffeur_mqtt_acces.py`, les sondes de A2 à A6 et celles des pages déjà classées par lieu, tous à code 0 avec le
Python de PlatformIO ; essai réel de A7.
