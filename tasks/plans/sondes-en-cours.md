---
chantier: sondes-en-cours
titre: Tuile « Sondes en cours » de l'annuaire : bancs et sondes Chrome de ce PC avec leur avancement réel
objectif: Voir en un coup d'œil quelles sondes et quels bancs tournent sur ce PC, où ils en sont (vérifications faites, dernier cas, échecs en direct) et arrêter un Chrome de sonde orphelin
statut: actif
cree: 2026-11-15
maj: 2026-11-15
famille: methode
liens: compilations-nuit
---
# Sondes en cours

## Contexte

Décisions de l'utilisateur : une tuile de l'annuaire (pas un mod Claude), et une colonne « avancée » qui montre l'avancement RÉEL des bancs, pas seulement la liste des processus.

- `outils_pc/suivi_sondes.py` : un banc appelle `suit()` en tête ; une enveloppe sur `sys.stdout` compte ses lignes `OK` / `KO` / `ECHEC` / `== phase` et écrit `%LOCALAPPDATA%\outils_tasmota\sondes\<pid>.json` (atomique, au plus toutes les 0,3 s, écriture différée par un fil pour que la dernière ligne ne reste pas en retard). `SUIVI_SONDES=0` le coupe.
- `outils_pc/sondes_scan.py` : un appel PowerShell par relevé (Chrome `sonde_` et python `test_*.py` / `banc_*.py`) joint par pid aux fichiers de suivi. États : en_cours, sans_suivi, termine, disparue, orpheline.
- `outils_pc/sondes_web.py` (+ `sondes_page.py`, `sondes_actions.py`), port 7910. Arrêt : `POST /arreter`, `taskkill /T /F`, seulement un pid du dernier relevé.
- Choix par défaut : un KO affiché pendant une phase `== temoin` ou `== mutant` est attendu, il compte comme fait mais pas comme échec (sauf `KO temoin ...`). Les termines et disparues ne sont gardés qu'une heure (10 terminés au plus). Le python du venv PlatformIO est un lanceur : le relevé garde le fils, qui écrit le suivi.
- Seuls les bancs de cette session et l'aide commune `test_build_page_chrome.py` (donc 33 sondes Chrome) sont branchés. Les autres bancs suivront au fil des usages : une ligne `suivi_sondes.suit()` en tête.

## A1 — Module de suivi `suivi_sondes.py`
- [x] `suit()`, `suit_si_script_test()`, `vivant()`, enveloppe de stdout, fichier atomique, purge de 2 jours, `SUIVI_SONDES=0` — preuve : outils_pc/suivi_sondes.py
- [x] Banc avec de vrais processus enfants (faits, échecs, phase, terminé, tué brutalement, écriture impossible ignorée, purge) — preuve : test_suivi_sondes.py code 0, 22 vérifications ; 3 mutants détectés (KO de témoin compté comme échec, écriture différée supprimée, erreur d'écriture propagée)

## A2 — Branchement des bancs
- [x] `test_build_page_chrome.py` (aide commune des sondes Chrome) : `suit_si_script_test()` après ses imports, ignoré avec `--serveur` — preuve : test_build_page_chrome.py (3 lignes) ; test_sondes_page_chrome.py, qui l'importe, passe vert et écrit son fichier de suivi
- [x] `test_compilation_nuit_tache.py` et `test_matrice_github.py` : une ligne `suit()` — preuve : les deux bancs code 0 après l'ajout
- [ ] Les autres bancs et sondes (test_taches_planifiees_*, test_compilation_nuit.py : fichiers tenus par d'autres sessions, laissés)

## A3 — Relevé et serveur
- [x] `sondes_scan.py` : jointure par pid, orpheline, disparue, sans_suivi, lanceur venv écarté, textes bornés — preuve : test_sondes_scan.py code 0, 18 vérifications, 2 mutants détectés (orpheline jamais, disparue prise pour en_cours)
- [x] `sondes_web.py` + `sondes_actions.py` : GET /, /etat, POST /arreter gardé (X-Sondes, origine, Host, client local), pid hors relevé refusé — preuve : test_sondes_web.py code 0, 30 vérifications, 6 mutants détectés (4 gardes d'accès, pid hors relevé, arrêt d'une sonde déjà finie)
- [x] Relevé PowerShell réel lancé une fois en lecture seule (aucune sonde en cours à ce moment) — preuve : lance_ps() rend 0 sonde sans erreur, 11 à 24 s sur ce PC chargé

## A4 — Page
- [x] Cartes, barre d'avancement, phase, dernier cas, échecs, bandeau, bouton d'arrêt à deux temps, bouton des orphelines, rafraîchie toutes les 2 s, mode sombre, 390 px, textContent — preuve : test_sondes_page_chrome.py code 0 (voir A6)

## A5 — Intégration
- [x] Tuile du registre de l'annuaire (groupe « Dépôt et références », 4 outils) et banc de l'annuaire mis à jour (21 outils) — preuve : test_annuaire.py code 0
- [x] Cible Custom `cible_sondes.py` (NOM_CIBLE `sondes`), banc, `pre_utilitaires_platformio.py`, `CIBLES_OUTILS` de garde_build — preuve : test_cible_sondes.py code 0 ; test_garde_build.py code 0 (liste alignée)
- [x] Tâche VS Code « Outil : sondes en cours » — preuve : .vscode/tasks.json (JSON valide)

## A6 — Sonde Chrome et témoins
- [x] Passage normal (22 vérifications) puis 3 témoins (innerHTML, deux-temps, en-tête X-Sondes) tous détectés — preuve : test_sondes_page_chrome.py code 0 ; son propre fichier de suivi réel : 91 vérifications, 0 échec, terminé (les KO attendus des témoins ne comptent pas)

## A7 — Essai réel
- [ ] Ouvrir la page pendant une vraie série de sondes de l'utilisateur et vérifier l'avancement affiché (non fait : aucun lancement hors de cette session)
- [ ] Mesurer le coût du relevé PowerShell sous charge et décider s'il faut un relevé en tâche de fond

## Améliorations restantes
- [ ] [projet] Brancher `suit()` dans les autres bancs `test_*.py` au fil des usages
- [ ] [projet] Afficher l'avancement d'un banc qui annonce son `total` (aujourd'hui la barre n'existe que si `suit(total=N)` est appelé)
