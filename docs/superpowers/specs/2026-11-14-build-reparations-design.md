# Réparation automatique des pannes de la page Build (design)

Date : 2026-11-14. Demande de l'utilisateur, déclenchée par deux échecs consécutifs de la compilation du P4 du garage
sur `PermissionError: [Errno 13] ... lib\libesp32\berry_custom\src\modules.h` (fichier tenu un instant par un autre
processus), alors que les cinq autres envs de la même série avaient réussi.

## Intention

Quand un `pio run` de la page Build (http://127.0.0.1:7700) échoue pour une cause que la page sait décrire, elle la traite
et la corrige elle-même, le dit à l'utilisateur sur la page, puis relance la commande initiale. L'utilisateur ne doit plus
découvrir une panne reconnaissable au retour d'une série de plusieurs compilations. Quand la page ne connaît pas la panne,
elle propose de la faire diagnostiquer par une IA ; si le correctif proposé marche, il entre dans le catalogue des
réparations que la page rejoue ensuite seule.

Pourquoi : les séries de compilations durent des heures (6 envs ce soir, 2 h 30) ; une panne passagère coûte une
relance manuelle et un env raté sans que personne ne regarde.

## Objectifs

- Reconnaître une panne connue dans le journal d'un fils `pio` raté, la réparer, annoncer la réparation sur la page,
  relancer la même commande (même env, même action).
- Dans une série, ne passer à l'env suivant que si la panne n'est pas réparable (aucune règle, relances épuisées,
  utilisateur qui refuse).
- Panne de verrou de fichier (le cas d'aujourd'hui, `modules.h` ou n'importe quel fichier) : repérer le processus qui tient
  le fichier ; fermer seule la liste blanche ; pour tout autre processus, afficher son nom et demander (Fermer, Attendre,
  Annuler).
- Panne inconnue : proposer « Faire diagnostiquer par l'IA ». L'IA lit le journal et le dépôt en lecture seule et propose
  un correctif ; rien n'est appliqué sans le clic « Appliquer » de l'utilisateur.
- Un correctif qui a réussi s'ajoute au catalogue sous forme de règle (motif + actions), consultable et supprimable dans
  la page.

## Non-objectifs et anti-objectifs

- L'IA ne modifie aucun fichier, ne commite pas, ne pousse pas, ne touche à aucun secret. Elle propose.
- Aucune commande libre mémorisée puis rejouée : une règle du catalogue n'est qu'un motif et des actions d'une liste
  fermée. Une règle trop large qui se rejoue sans relecture serait pire que la panne (anti-objectif).
- Ne jamais tuer un processus qui n'est pas dans la liste blanche sans clic de l'utilisateur, ni la page elle-même, ni le
  `pio`/`scons` de la série en cours, ni un build d'une autre origine.
- Hors périmètre de la première version : les échecs d'envoi OTA (HTTP, MQTT), les échecs d'envoi série (port COM) et
  `buildfs`/`uploadfs` autrement que par le motif de verrou ; seul un échec d'un fils `pio` est traité.
- Ne remplace pas la lecture du journal : le journal complet reste intact et la réparation y est notée.

## Contraintes du dépôt

- La page est `build_web.py` (+ `build_page.py` en une seule constante HTML/CSS/JS), la série `build_serie.py`
  (`_execute_env`, `_lance_pio`, événements numérotés rejoués par `depuis`). Les trois sont des exceptions à la règle des
  500 lignes déjà actées dans `CLAUDE.md` ; ne pas les faire grossir : tout le nouveau code vit dans des modules neufs, le
  branchement dans `build_serie.py` et `build_page.py` tient en quelques lignes chacun.
- Précédent pour appeler une IA : `atelier_ecrans_remarques.py` lance `claude -p` en LECTURE SEULE (outils de lecture,
  hooks coupés, jamais `bypassPermissions`, depuis ce PC seulement). Même mécanisme, même garde.
- Fermeture d'un processus : la cause de l'échec de `tasmota.ino.cpp` (2026-07-15) a été nommée par le Restart Manager de
  Windows ; c'est le moyen retenu pour lister les processus qui tiennent un fichier (API Win32 `Rm*` par `ctypes`).
- Aucune cible PlatformIO pendant un build, aucun accès à `data/` : la réparation ne modifie jamais le code du dépôt.
- Les mots de passe ne doivent jamais figurer dans le journal envoyé à l'IA ni dans le catalogue : filtre appliqué à
  l'extrait envoyé (le `user_config_override.h` peut apparaître dans un journal de build).

## Approches considérées

- A. Module dans la série (retenue) : `build_serie.py::_execute_env` appelle un module de réparation quand un fils `pio`
  échoue. Tout est au même endroit, les messages passent par les événements existants.
- B. Surveillance extérieure du journal avec relance par `POST /lancer` : la série ne change pas, mais la relance
  interfère avec l'enchaînement des envs et l'affichage au bon endroit est difficile. Écartée.
- C. Dans le pré-script PlatformIO : ne voit pas les pannes survenues hors du pré-script, et la page ne peut rien dire.
  Écartée.

Choix de l'utilisateur : A.

## Décisions prises avec l'utilisateur

- Verrou de fichier : le processus qui le tient est repéré ; liste blanche fermée seule (l'indexeur C/C++ `cpptools-srv.exe`
  et `cpptools.exe` pour commencer) ; tout autre processus : nom affiché, demande Fermer / Attendre / Annuler.
- Panne inconnue : l'IA diagnostique et propose, l'utilisateur clique « Appliquer », la page relance.
- Catalogue : une règle = motif repéré dans le journal + actions d'une liste fermée (attendre, fermer un processus de la
  liste blanche, vider le dossier de build de l'env, relancer). Un correctif de l'IA qui ne rentre pas dans ces actions
  reste manuel (affiché à chaque fois) et l'utilisateur est invité à demander l'ajout d'une action au code.

## Design

### Où ça se branche

Dans `build_serie.py::_execute_env`, quand `_lance_pio` rend `ok` faux, avant d'écrire l'événement `echec` : appel de
`build_reparations.traite(...)` avec l'env, l'action, la cible, le motif, l'extrait d'erreur, l'étape et la fin du journal.
Résultat : `reparee` (la même étape est relancée, dans la même boucle) ou `non_reparee` (comportement actuel : `echec`,
env suivant). Au plus 2 relances par étape et par env ; une même règle ne s'applique pas deux fois de suite si la panne
revient identique (signature = règle + dernière ligne d'erreur). Un arrêt demandé par l'utilisateur prime sur tout.

### Catalogue

Fichier `outils_docs/schemas/reparations_build.json`, suivi par git. Règle :
`{id, titre, motif (expression régulière sur la fin du journal), etapes (compilation, liens, prebuild... ou toutes),
actions: [ {action, parametres} ... ], origine ("base" ou "ia"), ajoutee_le, essais, reussites}`.
Actions, liste fermée : `attendre {secondes}` ; `libere_verrou {fichier: "depuis le motif"}` (repère les processus par le
Restart Manager, ferme la liste blanche, demande pour les autres) ; `vide_build {}` (supprime `.pio/build/<env>` de l'env
raté, jamais un autre) ; `relance {}` (implicite en fin de règle). Règle de base livrée : verrou de fichier
(`PermissionError: [Errno 13]` ou « Permission denied » sur un chemin du dépôt) = `libere_verrou` puis `attendre 5` puis
relance. Pas d'autre règle de base tant qu'elle n'est pas prouvée sur un vrai journal.

Une règle est ajoutée seulement après qu'un correctif de l'IA appliqué par l'utilisateur a fait réussir la relance ;
l'utilisateur voit l'avis « Règle ajoutée au catalogue : … » et peut la supprimer dans le panneau « Réparations ».

### Messages et choix sur la page

Nouveaux événements de la série (même modèle que `attente_carte`, rejoués par `depuis`) :
`reparation` env, action, regle, etat (`en_cours` | `reussie` | `echouee`), message ; et `choix_reparation` env, regle,
texte, boutons (liste), jusqu'à la réponse `POST /reparation {choix}`. La série reste en pause tant qu'une demande est
ouverte (le cas typique : un processus hors liste blanche tient le fichier) ; sans réponse au bout de 10 minutes l'env
est déclaré en échec et la série continue, pour qu'une série lancée la nuit ne reste pas bloquée.
Côté page : bandeau d'env « Réparation en cours : <titre> », liste des réparations de la série dans le résumé, boutons du
choix ; une ligne « [réparation] … » est ajoutée au journal de l'env. L'état de la page se reconstruit au rechargement par
les événements rejoués (comme la pause « rebranchez la carte »).

### Correction par l'IA

Quand aucune règle ne s'applique et que l'échec est une compilation, la page affiche sur l'env en échec « Faire
diagnostiquer par l'IA ». Lancement de `claude -p` en lecture seule (mécanisme d'`atelier_ecrans_remarques.py`) avec la
fin du journal (secrets filtrés), l'étape et les fichiers du dépôt à lire. Réponse JSON attendue :
`{cause, explication, regle: {motif, actions}|null, correctif_manuel: texte|null}`. Si `regle` rentre dans la liste fermée
et que son motif correspond effectivement au journal fourni (vérifié par la page), la page affiche cause et règle avec
« Appliquer et relancer » ; sinon elle affiche cause et correctif manuel, sans bouton d'application. Pas de relance d'IA
automatique, un clic par diagnostic.

### Verrou de fichier

`build_reparations_verrou.py` : `fichier -> [processus]` par le Restart Manager (`RmStartSession`, `RmRegisterResources`,
`RmGetList`), nom d'exécutable et ligne de commande par `Win32_Process`. Liste blanche dans le catalogue. Jamais fermés :
la page elle-même, un `pio`/`scons`/`python` de la série en cours, `claude`. Un processus de la liste blanche est fermé
par `terminate`, puis on attend jusqu'à 5 s que le fichier soit libre (`open` exclusif). Aucun processus trouvé alors que
l'échec persiste : on attend puis on relance (verrou passager, comme aujourd'hui).

### Tests

- Faux `pio` (`build_faux_pio.py`) qui échoue une fois avec un journal de verrou puis réussit : la série relance et
  l'env réussit, l'événement `reparation` est émis, le journal de l'env le note ; deuxième échec identique : pas de
  boucle (2 relances au plus).
- Verrou réel : un processus de test garde un fichier ouvert en exclusif ; `libere_verrou` le trouve par son nom et le
  ferme s'il est dans la liste blanche (liste de test), demande sinon.
- Catalogue : règle invalide (action hors liste, motif qui ne compile pas) refusée ; règle IA dont le motif ne
  correspond pas au journal refusée.
- Mutants : retirer la relance, la liste blanche, la limite de relances, le filtre des secrets doit rendre un banc rouge.
- Sonde Chrome : bandeau de réparation, boutons du choix, état reconstruit au rechargement.

## Précisions après relecture (choix du rédacteur, à confirmer en relisant)

- **Ce qu'une réparation relance.** Une règle de catalogue relance seulement l'étape `pio` qui a échoué (compilation,
  liens, buildfs), dans la même boucle de `_execute_env`. Jamais une étape d'envoi : `upload` et `erase_upload` par COM ne
  sont ni réparés ni relancés (le `.drvset003` ne doit pas être sauvegardé deux fois, la carte serait déjà effacée), et un
  échec « Permission denied » sur un port COM est exclu du motif de base : seul un chemin dans le dépôt compte.
- **Réparation par l'IA, quand elle s'exécute.** Un échec inconnu est marqué `echec` et la série continue, comme
  aujourd'hui. Le diagnostic est proposé sur l'env en échec (bouton dans le résumé de la série, après coup). « Appliquer et
  relancer » exécute les actions de la règle puis lance une nouvelle série d'un seul env avec les actions qui n'avaient pas
  réussi ; si une série tourne encore, la demande attend sa fin (un seul `Serie` à la fois, comme le reste de la page).
- **Qui tenait `modules.h`.** Inconnu à ce jour (le fichier était libre au contrôle). Candidat sérieux : `scons __idedata`
  lancé par l'IDE (`CLAUDE.md`, « Vigilances de build »). Donc, pour un processus `pio`, `scons` ou `python` d'une autre
  origine qui tient le fichier, la page ne propose jamais « Fermer » : elle attend la fin de ce build (`_attend_builds`
  existe déjà) puis relance. « Fermer » ne s'offre que pour un processus qui n'est ni la page, ni la série, ni un
  `pio`/`scons`/`python`, ni `claude` (donc l'indexeur `cpptools` seul en liste blanche, un autre outil avec demande).
- **Où le catalogue est écrit.** Dans le dépôt, seules les règles de base (`reparations_build.json`, jamais écrit par la
  page). Les règles ajoutées par l'IA, les compteurs d'essais et de réussites et les suppressions vivent dans
  `%LOCALAPPDATA%\outils_tasmota\build\reparations.json`, comme les autres états de la page, pour ne jamais salir l'arbre de
  travail. Une règle IA qui a fait ses preuves peut être promue dans le dépôt par un commit de l'utilisateur.
- **Clients distants.** Un client d'un autre appareil du réseau (jeton) peut lire les réparations et les messages, mais ni
  répondre à une demande de fermeture de processus, ni lancer le diagnostic par l'IA, ni appliquer un correctif : ce
  sont des actions de ce PC, refusées côté serveur (`build_web.py`), comme l'IA de l'atelier des écrans.

## Laissé au constructeur

Nom exact des événements et champs de la page, structure du panneau « Réparations », forme du filtre de secrets du
journal, liste blanche initiale au-delà de `cpptools`, découpage en modules, emplacement du panneau (onglet de la page ou
section du résumé), documentation dans `outils_docs/README.md`.
