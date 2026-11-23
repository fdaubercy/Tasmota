# Sondes en cours

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Sondes en cours (page web)

Tuile « Sondes en cours » de l'annuaire (groupe Dépôt et références), page http://127.0.0.1:7910 ; tâche VS Code « Outil : sondes en cours » ou cible Custom détachée. Elle liste les bancs Python et les Chrome de sonde qui tournent sur ce PC, avec leur durée et leur **avancement réel** : nombre de vérifications faites, phase (`== temoin innerHTML`), dernier cas, échecs en direct. Un banc apparaît avec son avancement quand il appelle `suivi_sondes.suit()` (fichiers `%LOCALAPPDATA%\outils_tasmota\sondes\<pid>.json`) ; les 37 sondes Chrome qui importent `test_build_page_chrome.py` (lequel appelle `suit_si_script_test()`) sont couvertes d'un seul coup, les autres bancs s'affichent « sans suivi » (durée seulement). Un Chrome de sonde dont le banc parent n'existe plus est signalé **orphelin**, avec un bouton « Arrêter les orphelines ». Un banc qui n'annonce pas de total prend celui de sa dernière exécution sans échec (affiché « 12 / ~46 », barre comprise ; `sondes_historique.json`). Presque tous les bancs `test_*.py` et `banc_*.py` de `scripts_python` sont suivis : 199 sur 247 appellent `suit_si_script_test()` (3 lignes après le docstring), 8 appellent `suivi_sondes.suit()` en direct (les bancs des tâches planifiées et des sondes), les sondes Chrome passent par l'import ci-dessus, et 4 n'ont aucun suivi (`berry/banc_log_declare.py`, `berry/test_mesure_binomes.py`, `maintenance/test_synchro_fork_page_chrome.py`, `outils_pc/test_plan_maison_web.py`; comptage du 2026-11-23). `SUIVI_SONDES=0` coupe le suivi.

Cliquer sur l'en-tête d'une carte en déplie le détail du suivi : script, phases (début, vérifications faites, échecs) et journal des 200 dernières lignes `OK` / `KO` / `==` du banc, mis à jour toutes les 2 s ; un second clic le replie (route `GET /detail?pid=`, même règle que l'arrêt : seulement un numéro du dernier relevé).

Arrêter une sonde : bouton à deux clics, accepté seulement pour un numéro présent dans le dernier relevé (jamais un processus quelconque), arbre tué par `taskkill /T /F`. Mêmes contrôles d'accès que la page Tâches planifiées (`X-Sondes: 1`, origine, Host, ce PC seulement). Limite : un relevé PowerShell prend 11 à 24 s sous charge, la page peut afficher un relevé retardé. Plan `tasks/plans/sondes-en-cours.md`.

### Lancer, modules, bancs

- Sans l'annuaire : `python outils_docs/scripts_python/outils_pc/sondes_web.py [--http 7910] [--local] [--sans-navigateur]` ; cible Custom détachée `sondes` (`build/cible_sondes.py`, `pio run -e <env> -t sondes`, jamais pendant un build, port par `custom_sondes_http`).
- Dans un banc : `import suivi_sondes; suivi_sondes.suit(total=N)` en tête (le `total=` est facultatif, voir plus haut) ; le suivi ne lève jamais d'exception.
- Modules : `suivi_sondes.py` (écrit `<pid>.json`), `sondes_scan.py` (relevé PowerShell des processus joint aux fichiers de suivi ; états `en_cours`, `sans_suivi`, `termine`, `disparue`, `orpheline`), `sondes_actions.py` (arrêt), `sondes_page.py`, `sondes_web.py`.
- Bancs (`outils_pc/`, Python de PlatformIO) : `test_suivi_sondes.py`, `test_sondes_scan.py`, `test_sondes_web.py`, sonde Chrome `test_sondes_page_chrome.py` ; cible : `build/test_cible_sondes.py`.
