---
chantier: audit-relais-cave-s3
titre: Suites de l'audit de l'env S3 du serveur relais de la cave
objectif: Rendre l'env tasmota32s3-cave-serveur-rly prêt à remplacer la carte de la cave en ligne, selon les propositions de l'audit
statut: en-pause
cree: 2026-10-31
maj: 2026-10-31
source: outils_docs/AUDIT_RELAIS_CAVE_S3_2026-10-31.md
---
# Suites de l'audit de l'env S3 du serveur relais de la cave

## Contexte
Plan d'action issu de `outils_docs/AUDIT_RELAIS_CAVE_S3_2026-10-31.md` (audit en lecture seule). Rien n'est décidé :
l'utilisateur choisit les actions. Règles : aucun `pio run` pendant un build de l'utilisateur, `git commit -- <chemins>`,
pas de `Co-Authored-By`, messages de commit en français sans accents.

## A1 — Prouver que l'env compile et tient en mémoire (P1)
- [ ] Aucun `pio run`/scons en cours juste avant (garde_build, Win32_Process)
- [ ] Env compilé via la page « Build et téléversement » (7700), sans téléversement
- [ ] Taille du firmware relevée contre la partition app de 3 904 Kio
- [ ] Après un premier flash : tas libre interne et PSRAM relevés (`Status 4`, `BRY: GC`)

## A2 — Ports et état de la bascule (P2, P4)
- [ ] `upload_port`/`monitor_port` de l'env changés (COM3 est la cuve) ou commentés
- [ ] État réel des relais de la carte en ligne relevé juste avant la bascule
- [ ] État voulu des relais au premier démarrage de la S3 décidé et appliqué après le flash

## A3 — Topics, consommateurs et messages retenus (P3, P8)
- [ ] Consommateurs de `cave/serveur-rly-cave` inventoriés sur le Pi (Node-RED, Grafana, Influx, autres)
- [ ] Flux Telegram importé et réglé (token, broker) pour `cave/serveur-rly-cave-v2`
- [ ] Messages retenus de l'ancien topic et LWT `-v2` effacés après la bascule
- [ ] Groupe `tasmotas/cave` : carte en ligne vérifiée ; commentaires de l'env corrigés

## A4 — Rôle réseau de la cave (P5)
- [ ] Décision : la cave est-elle « maître » UDP / Range Extender / discovery / FTP ?
- [ ] Si non : les 4 blocs à OFF dans `data/cave/tasmota32s3-serveur-rly/_persist.json`, banc de démarrage mis à jour
- [ ] Si oui : raison consignée dans le commentaire de l'env

## A5 — Alerte de la pompe (P6, P10)
- [ ] Capteurs de niveau câblés et activés (GPIO 2/15), ou limite consignée
- [ ] `EtatPompe`, `AcquittePompe` et `ALERTE_POMPE` essayés sur la carte
- [ ] Banc de la relance de sécurité écrit (`finTimerRelai`, `relanceRelai`, `acquitteRelance`)
- [ ] Une seule copie de `controlePompeVideCave.be` retenue

## A6 — Allègement de l'env (P7, P9, P11)
- [ ] Base `tasmota32s3-base-N16R8-sans-ecran` et `SET_ESP32_STACK_SIZE` essayés, taille comparée à A1
- [ ] `leds` retiré de la solidification, ou conservé par choix
- [ ] `fsMqtt` chargé par l'autoexec de la cave si l'envoi de fichiers par MQTT est voulu
- [ ] Persist nettoyé : `TasmotaSlaveModBus2`, `diverses.historique.grafana`, `ledPower`

## Améliorations restantes
- [ ] [projet] Vérifier si un 2e « maître » (id 0) perturbe la table discovery du P4
- [ ] [projet] Réduire la partition FS (11,3 Mo) pour la cave si l'écriture de l'image gêne

## Vérification
`python outils_docs/scripts_python/berry/banc_demarrage.py --carte tasmota32s3-cave-serveur-rly` (code 0 = vert), puis
`node .claude/hooks/index_plans.mjs --verifier`. Une étape ne se coche qu'avec sa preuve (sortie de banc, commit, mesure sur carte).
