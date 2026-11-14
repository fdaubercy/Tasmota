---
chantier: historique-debits
titre: Historique et page /graphiques des 6 débits de la nourrice
objectif: Garder en flash l'historique des 6 débits et du total, et les voir en courbes sur la page /graphiques de la carte
statut: actif
cree: 2026-11-08
maj: 2026-11-09
famille: debits-energie
parent: debitmetres-chauffage
liens: debitmetres-chauffage
---
# Historique et page /graphiques des 6 débits de la nourrice

## Contexte
Suite du plan `tasks/plans/debitmetres-chauffage.md` (amélioration [projet], demandée « à planifier » le 2026-11-08).
Carte `tasmota32s3-bureau-serveur-debits-pac` (ESP32-S3 N16R8, PSRAM : l'historique y est permis).

Rien à inventer, le framework existe et sert déjà la cuve :
- `data/fs/historiqueFonctions.be` (relevé toutes les `pasMinutes`, fichiers par mois, `moisConserves`) ;
- `data/fs/historiqueSeries.be` : séries **découvertes** dans le JSON SENSOR. Le bloc `DEBITS` publié par
  `debitsFonctions_json` donne `DEBITS.D1` à `D6` et `DEBITS.Total` (feuilles numériques : 7 séries, sous
  `seriesMax` 12) ; `Imprecis` et `Muets` sont des listes, pas des séries ; `COUNTER.C1-C4` sont écartés
  (pas de réglage `compteurs`), ce qui est voulu : les débits sont déjà dans `DEBITS` ;
- `data/fs/graphiquesFonctions.be` + `data/sd/{html,css,js}/graphiques.*` : page `/graphiques` composable,
  composition dans `graphiques.json` du dossier de la carte (déjà présent, créé par l'assistant persist) ;
- atelier des graphiques (page 7950) pour préparer et écrire la composition.

État de la carte : `diverses.historique.activation` = OFF dans le persist ; les fichiers de l'historique et de
`/graphiques` sont **exclus** de l'env dans `platformio_tasmota_cenv.ini` (`custom_files_exclude`).

Points à trancher avec l'utilisateur (A1) : pas de relevé (5 min par défaut, un débit varie lentement), et si la
série `Débit.Rate` du FlowRateMeter (liste) doit être exclue explicitement.

## A1 — Décisions
- [x] Pas de relevé (`pasMinutes`, défaut 5) et durée affichée (`dureeHeures`, défaut 24) choisis par l'utilisateur — preuve : réponse du 2026-11-08 « 5 min, 24 h » = valeurs déjà au persist de la carte (`diverses.historique`)
- [x] Séries : D1 à D6 et Total ; libellés : `graphiquesFonctions` ne lit pas les noms des départs, il prend `affichage.<chemin>.libelle` de `graphiques.json` (sinon le chemin `DEBITS.D1`) ⇒ libellés = noms des départs du persist, à refaire si un départ est renommé — preuve : accord de l'utilisateur du 2026-11-08 (« oui ») ; `graphiques.json` de la carte : `affichage` D1-D6 (« Debit 1 » à « Debit 6 », L/min) et Total

## A2 — Activation sur la carte
- [x] **Accord demandé** avant de toucher au persist : `diverses.historique.activation` ON (et les réglages de A1) — preuve : accord du 2026-11-08, `_persist.json` `diverses.historique.activation` = ON (pas 5 min, 24 h inchangés)
- [x] `autoexec.be` de la carte : `historiqueFonctions`, `historiqueSeries`, `graphiquesFonctions` importés et `demarrage.historique()` AVANT `controleDebits`, sur le patron de la cuve — preuve : `data/bureau/tasmota32s3-serveur-debits-pac/autoexec.be`
- [x] cenv : exclusions de l'historique et de `/graphiques` retirées de l'env (`custom_files_exclude`), `custom_berry_solidify` vérifié (règle : module de `data/fs` solidifié = présent dans la liste de l'env) — preuve : section de l'env, `${berry_commun.historique}` ajouté à la solidification ; 9 exclusions retirées et `${berry_commun.pages_graphiques_moteur}` (règle : embarqué quand l'historique est ON) ; `pages_graphiques` reste exclu (pas de page dédiée)
- [x] `banc_demarrage.py --dossier data/bureau/tasmota32s3-serveur-debits-pac --env tasmota32s3-bureau-serveur-debits-pac` VERT — preuve : 4 drivers (dont `HISTORIQUE_WEB`), cron `majHistorique`, 0 erreur ; modules de l'historique non modifiés, leurs bancs non relancés
- [x] Compilation par la page Build (:7700), SUCCESS lu en fin de journal — preuve : journal `20261108-200019-…-compiler.log`, SUCCESS en 57 min 52 s, RAM 23,7 %, Flash 88,2 % (3 525 103 / 3 997 696 o, +35 892 o pour l'historique) ; taille du FS à relever au buildfs (A4)

## A3 — Composition de la page /graphiques
- [x] Composition par défaut : un graphique « Débits par départ » (6 courbes) et un « Débit total » — preuve : `groupes` de `graphiques.json` (composition par défaut de `graphiques.js`, sans passer par l'atelier : rien à concevoir) ; rendu à juger sur la carte (A4)

## A4 — Essai sur la carte
- [ ] Après 1 h : séries D1-D6 et Total présentes (`/histo`), courbes sur `/graphiques`, RAM et FS relevés
- [ ] Après un redémarrage : historique conservé, aucune erreur au journal (`ReglageLog` / syslog)

## Améliorations restantes
- [ ] [projet] Envoi vers Influx/Grafana du Pi (bouton « Historique (Grafana) » : clé `grafana` du persist)

## Vérification
- Bancs PC verts (démarrage, historique, atelier) ; sur carte : courbes réelles des 6 départs sur `/graphiques`.
