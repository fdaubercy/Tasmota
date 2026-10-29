---
chantier: assistant-persist-modification
titre: Assistant persist — reprendre, modifier et supprimer un env existant (A10)
objectif: Reprendre un env existant dans la page 7900 pour le modifier sans perdre ses retouches, ou le supprimer après vérification
statut: actif
cree: 2026-10-29
maj: 2026-10-29
---
# Assistant persist — modification et suppression d'un env (A10)

> **Pour l'exécutant :** sous-skill requise : superpowers:subagent-driven-development (recommandée) ou
> superpowers:executing-plans. Cocher une étape seulement après vérification, avec « — preuve : … ».
> **Plan à valider par l'utilisateur avant toute exécution.**

## Contexte

Action A10 du plan `tasks/plans/assistant-persist.md`, détaillée ici. **Spec : §10 (avenant du 2026-10-29) de
`docs/superpowers/specs/2026-10-27-assistant-persist-design.md`**, à lire en entier avec les §5.2 et §9.

**Principe (spec §10.2) :** on ne régénère jamais une carte existante. On génère A (réponses relues de la carte) et
B (réponses de la page), et on applique au vrai fichier le seul écart A → B. Le reste du fichier ne bouge pas d'un
octet.

**Fichiers :**

| Fichier | Rôle | Action |
|---|---|---|
| `outils_pc/assistant_persist_texte.py` (neuf) | écart et édition d'un JSON **dans son texte** | A2 |
| `outils_pc/assistant_persist_delta.py` (neuf) | écart ligne à ligne appliqué à une zone d'un fichier | A3 |
| `outils_pc/assistant_persist_modification.py` (neuf) | `charge_env`, `prepare_modification`, `modifie` | A4, A5 |
| `outils_pc/assistant_persist_web.py` | routes `/env`, `/modification*`, `/suppression*` ; `cartes` dans `/parc` | A6 |
| `outils_pc/assistant_persist_page.py` | liste « Env », bandeau, panneau de suppression | A7 |
| `outils_pc/assistant_persist_page_js_env.py` (neuf) | JS du mode modification et de la suppression | A7 |
| `outils_pc/assistant_persist_page_js.py` | `majCreer` : « Voir le diff » réactivé, libellé du bouton | A7 |
| bancs `test_assistant_persist_{texte,delta,modification}.py` (neufs), `_web.py`, sonde Chrome | | A2-A7 |

Réutilisés **sans changement de comportement** (bancs `test_fichiers_berry_*.py` verts sans retoucher leurs
attentes) : `fichiers_berry_creation` (`_section_h(lignes, define)` = bornes, `_regions`, `_masque`, `_eol`,
`_encode`, `refus_identite`, `avertit_prises`), `fichiers_berry_coprocesseur._membres`,
`fichiers_berry_suppression` (`prepare_suppression`, `supprime`, `define_de`), `fichiers_berry_renommage._base`,
`fichiers_berry_sauvegarde.Transaction`. Côté assistant : `assistant_persist_creation` (`_section_h`,
`_section_cenv`, `_refus_metiers`, `_identite_h`), `assistant_persist_generation` (`reponses_depuis_persist`,
`persist`, `autoexec`, `listes_cenv`, `coherence`, `variables`, `secrets_reponses`).

### Contraintes globales

- Toutes celles du plan `assistant-persist.md` (port 7900, en-tête POST, aucun `pio run`, bancs sur dépôt d'essai,
  refus pendant un build, mots de passe jamais hors du serveur, fins de ligne du dépôt, `data/fs/*.be` intouché,
  fichiers < 500 lignes, textes de la page en français avec accents).
- **Rien n'est écrit pour un écart vide** : « Modifier » reste grisé et le serveur refuse (400 « aucun changement »).
- **Écart non applicable** (lignes de A introuvables dans le vrai fichier, retouché à la main) : **toute la
  modification est refusée** (409), le refus cite le fichier et les lignes concernées (masquées) — décision de
  l'utilisateur du 2026-10-29.
- Bancs : Python du penv, depuis la racine,
  `"$USERPROFILE/.platformio/penv/Scripts/python.exe" -u outils_docs/scripts_python/outils_pc/<banc>.py`, code 0 = vert.

## A1 — Spec et plan validés

- [x] Avenant §10 écrit dans la spec — preuve : `docs/superpowers/specs/2026-10-27-assistant-persist-design.md` §10
- [x] Spec §10 et ce plan validés par l'utilisateur (décision « écart non applicable » comprise) — preuve : « validé » de l'utilisateur, 2026-10-29

## A2 — Écart et édition d'un JSON dans son texte (`assistant_persist_texte.py`)

Interfaces produites :
- `ecart(a: dict, b: dict) -> list[tuple[tuple, str, object]]` : opérations `(chemin, "remplace"|"ajoute"|"retire",
  valeur)`. Deux objets se comparent clé par clé (récursif) ; toute autre valeur (liste comprise) se compare en bloc.
- `applique(texte: str, operations) -> str` : applique dans le texte. « remplace » : le texte de la valeur seule ;
  « ajoute » : membre inséré en fin d'objet, indentation et fin de ligne détectées sur ses voisins (comme
  `fbcp.adapte_persist`) ; « retire » : membre supprimé avec sa virgule. `LookupError` si le chemin parent manque.
  Valeurs écrites par `json.dumps(v, indent=<indent détecté>, ensure_ascii=False)`, réindentées à la profondeur.
- `ecart_applicable(texte, operations) -> list[str]` : chemins dont le parent n'existe pas dans le texte.

- [ ] Banc rouge `test_assistant_persist_texte.py` (modèle `ECHECS`/`verifie`/`principal`) :
  - `remplace_chaine`, `remplace_nombre`, `remplace_liste` : seuls les octets de la valeur changent (comparaison du
    texte avant/après hors de l'intervalle de la valeur) ;
  - `ajoute_tab_crlf`, `ajoute_4_espaces_lf` : indentation et fins de ligne du fichier respectées, `json.loads` OK ;
  - `retire_dernier`, `retire_milieu`, `retire_seul` : virgules correctes, `json.loads` OK ;
  - `objet_parcouru` : changer `a.b.c` garde la clé `a.b.propre` absente du modèle ;
  - `aller_retour` : `applique(applique(t, ecart(a, b)), ecart(b, a)) == t` ;
  - `accents` : `"é"` gardé non échappé ;
  - `vrais_persists` : pour chaque `data/*/*/_persist.json` (lecture seule), `applique(t, []) == t`.
- [ ] Lancer : ROUGE (module absent).
- [ ] Écrire le module (< 250 lignes), sur `fbcp._membres`.
- [ ] Lancer : VERT.
- [ ] Commit `feat(assistant-persist): ecart et edition d'un JSON dans son texte (A10)`.

## A3 — Écart ligne à ligne (`assistant_persist_delta.py`)

Interface produite :
- `applique_lignes(reel: list[str], a: list[str], b: list[str]) -> tuple[list[str], list[str]]` : les blocs
  `difflib.SequenceMatcher(None, a, b).get_opcodes()` autres que `equal` sont appliqués à `reel` ; un bloc
  `replace`/`delete` exige ses lignes de `a` présentes **une seule fois et contiguës** dans `reel` ; un `insert` se
  pose après la ligne de `a` qui le précède (elle-même trouvée une seule fois), ou avant la première ligne qui le
  suit. Renvoie `(nouvelles lignes, blocs non appliqués en texte)`. Comparaison sur `rstrip()` : espaces de fin et
  `\r` ignorés.

- [ ] Banc rouge `test_assistant_persist_delta.py` :
  - `ecart_vide` : `a == b` → `reel` rendu tel quel, aucun bloc ;
  - `ligne_ajoutee_a_la_main_gardee` : une ligne de `reel` absente de `a` survit ;
  - `insert_apres`, `insert_en_tete`, `delete`, `replace` ;
  - `bloc_introuvable` et `bloc_ambigu` (lignes présentes deux fois) → non appliqués, cités ;
  - `aller_retour` sur une section `.h` réelle (lecture seule).
- [ ] Lancer : ROUGE.
- [ ] Écrire le module (< 120 lignes).
- [ ] Lancer : VERT.
- [ ] Commit `feat(assistant-persist): ecart ligne a ligne d'un fichier genere (A10)`.

## A4 — Charger un env existant (`assistant_persist_modification.py`, partie 1)

Interfaces produites :
- `cartes(racine) -> list[dict]` : `[{env, dossier, puce}]`, envs de famille « cartes » (`fbe.envs_proposes`) dont
  `fbe.dossier_carte(env)/_persist.json` existe.
- `reponses_de_l_env(racine, env) -> Reponses` : `reponses_depuis_persist(modele, persist, env, racine)` complété de
  `base` (`fbr._base`) et `define` (`fbx.define_de`). `LookupError` si l'env n'est pas une carte ; `ValueError`
  (message sans secret) si le persist est illisible ou si les réponses ne passent pas `gen.variables`.
- `charge_env(racine, env) -> dict` : `{env, reponses (asdict, sans secret), reglages_propres: int, avertissements}`
  ; `reglages_propres` = nombre de chemins où le vrai persist diffère de A (conservés à la modification).

- [ ] Banc rouge `test_assistant_persist_modification.py`, groupe « charge » :
  - `cartes_du_parc` : les cartes du dépôt d'essai, pas les bases ;
  - `charge_carte_creee` : une carte créée par `apc.cree` se recharge avec les mêmes réponses (champs saisis) ;
  - `charge_inconnu` → `LookupError` ; `charge_persist_casse` → `ValueError` sans valeur secrète dans le message ;
  - `aucun_secret` : le témoin secret du dépôt d'essai n'apparaît pas dans `json.dumps(charge_env(...))`.
- [ ] Lancer : ROUGE.
- [ ] Écrire la partie 1.
- [ ] Lancer : VERT.
- [ ] Commit `feat(assistant-persist): chargement d'un env existant (A10)`.

## A5 — Préparer et écrire une modification (`assistant_persist_modification.py`, partie 2)

Interfaces produites :
- `prepare_modification(racine, env, r) -> dict` : `{env, dossier, diff (masqué), empreinte, avertissements, refus,
  vide: bool}`, rien d'écrit.
- `modifie(racine, env, r, empreinte_lue, builds_en_cours) -> dict` : `{modifie, env, diff, sauvegarde,
  avertissements}`. `RuntimeError` (→ 409) : build en cours ou inconnu, empreinte périmée, refus ; `ValueError`
  (→ 400) : écart vide.

Calcul (`_calcule(racine, env, r)`) :
1. Refus si lieu, nom, puce ou base de `r` diffèrent de ceux de l'env (« renommer : page 7800 »).
2. `a = reponses_de_l_env`, `b = r` ; `vars` et **vrais** secrets pour chacun (`gen.secrets_reponses`) ; une
   exception de secret devient un refus sans valeur.
3. Persist : `texte.applique(vrai, texte.ecart(gen.persist(A), gen.persist(B)))`.
4. Autoexec : `delta.applique_lignes(vrai, gen.autoexec(A), gen.autoexec(B))`.
5. Section cenv : bornes par `fbc._regions` ; `applique_lignes` sur la section, entre A et B générés par
   `apc._section_cenv` (+ `fbcp.adapte_cenv`).
6. Section `.h` : bornes par `fbc._section_h(l_h, define)` ; `applique_lignes` entre `apc._section_h` de A et de B.
7. Contrôles : `gen.coherence` sur B, schéma (`_erreurs_schema`), `_refus_metiers` pour les seuls métiers nouveaux,
   `fbc.refus_identite`, `fbc.avertit_prises` contre le `.h` **sans** la section de l'env.
8. Blocs non appliqués des étapes 4-6 → refus (décision de l'utilisateur du 2026-10-29).
9. Squelettes des métiers nouveaux : ajoutés seulement si le fichier n'existe pas.
10. Empreinte : sha256 de cenv, `.h`, modèle, persist, autoexec, env, `asdict(r)` triés.
Écriture : `fbs.Transaction(racine, "modification-assistant")`, `tr.ecrit` des seuls fichiers changés.

- [ ] Banc rouge, groupe « modification » (dépôt d'essai, carte créée par `apc.cree`) :
  - `rien_change_ecart_vide` : `vide` vrai, `modifie` → `ValueError` ;
  - `rejeu_parc_ecart_vide` : chaque carte du vrai parc copiée dans le dépôt d'essai, chargée puis préparée sans
    changement → `vide` vrai (sinon le chemin fautif est affiché, sans valeur) ;
  - `bloc_ajoute` / `bloc_retire` : persist, autoexec, listes du cenv et lignes du `.h` suivent ;
  - `identite_changee` : hostname/topic changés dans le persist et le `.h` ;
  - `reseau_change` : SSID et mot de passe changent ensemble (vérifié par égalité au mot de passe attendu, jamais
    imprimé) ;
  - `retouches_gardees` : clé propre ajoutée au persist, `upload_port = COM7` dans le cenv, ligne ajoutée au `.h` :
    toutes conservées ;
  - `aller_retour` : bloc ajouté puis retiré → fichiers identiques à l'origine, octet pour octet ;
  - `ligne_retouchee_refus` : ligne du `.h` touchée par l'écart modifiée à la main → refus qui cite la ligne masquée ;
  - `figes` : changer le nom ou la puce → refus ;
  - `empreinte_perimee`, `build_en_cours`, `build_inconnu` → `RuntimeError` ;
  - `metier_nouveau_squelettes`, `fichier_existant_non_ecrase` ;
  - `aucun_secret` dans toute sortie (diff, refus, erreurs).
- [ ] Lancer : ROUGE.
- [ ] Écrire la partie 2 (module total < 500 lignes, sinon le signaler).
- [ ] Lancer : VERT, et les bancs `test_assistant_persist_*.py` et `test_fichiers_berry_*.py` : VERT.
- [ ] Commit `feat(assistant-persist): modification d'un env existant par ecart (A10)`.

## A6 — Routes du serveur (`assistant_persist_web.py`)

| Route | Entrée | Sortie |
|---|---|---|
| GET `/parc` | | + `cartes` (`apm2.cartes`) |
| GET `/env?nom=` | | `charge_env` ; 404 inconnu, 400 illisible |
| POST `/modification/prepare` | `{env, reponses}` | `prepare_modification` |
| POST `/modification` | `{env, reponses, empreinte}` | `modifie` ; 409 / 400 |
| POST `/suppression/prepare` | `{env}` | `fbx.prepare_suppression` + `elements` (liste lisible : section du cenv, section du `.h` et define, `default_envs`/`data_dir`, dossier → nom `-sauvegarde`) |
| POST `/suppression` | `{env, empreinte}` | `fbx.supprime(..., builds_en_cours)` ; 409 |

- [ ] Banc rouge (ajouts à `test_assistant_persist_web.py`) : chaque route sur le dépôt d'essai ; 404/400/409 ;
  en-tête POST manquant → 403 ; aucun mot de passe réel dans aucune réponse, erreurs comprises ; suppression : dossier
  renommé, section du cenv et du `.h` retirées.
- [ ] Lancer : ROUGE.
- [ ] Ajouter les routes (`assistant_persist_web.py` < 500 lignes).
- [ ] Lancer : VERT.
- [ ] Commit `feat(assistant-persist): routes de modification et de suppression (A10)`.

## A7 — La page : mode modification et suppression vérifiée

Comportement (spec §10.4) :
- Étape « Carte » : liste « Env » (« (nouvel env) » + `parc.cartes`) et bouton « Charger » ; chargé → toutes les
  étapes remplies, lieu/nom/puce/base grisés, `manuel` posé pour l'identité relue.
- Lieu + nom + puce d'un env existant en mode création → libellé « Modifier l'environnement » et bandeau « Cet env
  existe déjà — Charger ses réglages ».
- `majCreer` : « Voir le diff » actif dès qu'un métier est nommé, **sans condition sur `cree`** ; toute saisie
  invalide le diff (déjà en place). Le bouton appelle `/prepare` + `/creation` ou `/modification/prepare` +
  `/modification` selon le mode. Après succès : mode modification sur cet env, réponses rechargées.
- Mode modification : bouton « Supprimer cet env… » → panneau : liste `elements`, refus en rouge, avertissements,
  diff masqué ; case « J'ai vérifié ces éléments » → active « Supprimer » ; après succès, retour au mode création
  et `cartes` relu.

- [ ] Sonde Chrome rouge (`test_assistant_persist_page_chrome.py`, aucun envoi réel hors dépôt d'essai) :
  - `charger_env` : champs remplis, lieu/nom/puce/base désactivés, bouton « Modifier l'environnement » ;
  - `diff_reactive_apres_creation` : créer, changer un paramètre → « Voir le diff » actif ;
  - `libelle_si_existe` : saisir lieu/nom d'une carte → libellé « Modifier », bandeau visible ;
  - `suppression_verifiee` : « Supprimer » désactivé tant que la case n'est pas cochée ; éléments listés ;
  - `temoin_id_casse` : le témoin existant reste rouge si un id DOM manque.
- [ ] Lancer : ROUGE.
- [ ] Écrire `assistant_persist_page_js_env.py` et les retouches (`_page.py`, `_page_js.py` < 500 lignes chacun).
- [ ] Lancer : VERT, plus tous les bancs `test_assistant_persist_*.py`.
- [ ] Commit `feat(assistant-persist): page en mode modification et suppression verifiee (A10)`.

## A8 — Documentation, relecture, fumée réelle

- [ ] `outils_docs/README.md` § « Assistant persist » : charger, modifier, supprimer ; limites (lignes retouchées).
- [ ] `CLAUDE.md` (carte des documents : modules neufs, A10 fait) et `.claude/skills/bancs/SKILL.md` (bancs neufs).
- [ ] `verifie_references_docs.py` : code 0.
- [ ] Relecture finale de la branche (modèle le plus capable), corrections.
- [ ] Fumée réelle **avec l'utilisateur** sur `tasmota32p4-cellier-controleur` : charger, ajouter un bloc, compiler
  par la page 7700, puis supprimer par la page 7900 en vérifiant chaque élément listé.
- [ ] Plan `assistant-persist.md` : A10 coché avec renvoi à ce plan.

## Améliorations restantes

- [ ] [projet] Changer de base ou de puce d'une carte existante (aujourd'hui : refus, créer une autre carte).
- [ ] [projet] Éléments des métiers 2 à N (non relus par `reponses_depuis_persist` : conservés mais non éditables).

## Vérification

Tous les bancs `test_assistant_persist_*.py` et `test_fichiers_berry_*.py` verts ; rejeu du parc à écart vide ;
aller-retour octet pour octet ; aucun mot de passe dans une sortie ; fumée réelle faite avec l'utilisateur.
