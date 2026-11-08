---
chantier: historique-debits
titre: Historique et page /graphiques des 6 débits de la nourrice
objectif: Garder en flash l'historique des 6 débits et du total, et les voir en courbes sur la page /graphiques de la carte
statut: en-pause
cree: 2026-11-08
maj: 2026-11-08
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
- [ ] Pas de relevé (`pasMinutes`, défaut 5) et durée affichée (`dureeHeures`, défaut 24) choisis par l'utilisateur
- [ ] Séries : D1 à D6 et Total ; noms affichés = noms des départs (persist `debitmetres`/`compteurs`), à vérifier dans `graphiquesFonctions`

## A2 — Activation sur la carte
- [ ] **Accord demandé** avant de toucher au persist : `diverses.historique.activation` ON (et les réglages de A1)
- [ ] `autoexec.be` de la carte : `historiqueFonctions`, `historiqueSeries`, `graphiquesFonctions` importés et `demarrage.historique()` AVANT `controleDebits`, sur le patron de la cuve
- [ ] cenv : exclusions de l'historique et de `/graphiques` retirées de l'env (`custom_files_exclude`), `custom_berry_solidify` vérifié (règle : module de `data/fs` solidifié = présent dans la liste de l'env)
- [ ] `banc_demarrage.py --dossier data/bureau/tasmota32s3-serveur-debits-pac --env tasmota32s3-bureau-serveur-debits-pac` VERT ; banc de l'historique (`berry/banc_graphiques.py`, `banc_historique.be`) relancé
- [ ] Compilation par la page Build (:7700), SUCCESS et taille du FS lus en fin de journal

## A3 — Composition de la page /graphiques
- [ ] Composition préparée dans l'atelier des graphiques (7950) : un graphique « Débits par départ » (6 courbes) et un « Débit total » ; maquette PNG proposée avant écriture
- [ ] `graphiques.json` de la carte écrit par l'atelier (diff relu), banc de l'atelier vert

## A4 — Essai sur la carte
- [ ] Après 1 h : séries D1-D6 et Total présentes (`/histo`), courbes sur `/graphiques`, RAM et FS relevés
- [ ] Après un redémarrage : historique conservé, aucune erreur au journal (`ReglageLog` / syslog)

## Améliorations restantes
- [ ] [projet] Envoi vers Influx/Grafana du Pi (bouton « Historique (Grafana) » : clé `grafana` du persist)

## Vérification
- Bancs PC verts (démarrage, historique, atelier) ; sur carte : courbes réelles des 6 départs sur `/graphiques`.
