---
name: pcb-tasmota
description: Use when designing, modifying, routing, checking or ordering a PCB (KiCad, Gerber, JLCPCB, PCBWay, carte porteuse, empreinte, routage, plan de masse, sérigraphie, BOM, CPL, boîtier, alimentation) for a module of the personal Tasmota fork, or when turning a _persist.json, a pinout or a wiring doc into a schematic, or when sizing a power supply or choosing parts (ESP32-S3 DevKit, ADS1115, RS485, WS2812/WS2815, DS18B20, relais, fins de course) for these boards.
---

# PCB pour les modules Tasmota (KiCad 10)

## Principe

Une **description Python unique** (composants, broches → nets, placement) génère le schéma
**et** le PCB liés, puis l'autorouteur, puis `kicad-cli` vérifie. Tout fait matériel vient de
l'utilisateur ou d'une mesure, jamais d'une valeur par défaut du persist.

Chemins (commandes lancées depuis la racine du dépôt) :
- `SK=.claude/skills/pcb-tasmota` ; Python de KiCad (`pcbnew`, `numpy`) :
  `"C:\Program Files\KiCad\10.0\bin\python.exe"` ; CLI : `"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"`.

## Avant de dessiner (rien n'est dessiné avant les réponses)

1. Lire `$SK/references/pieges_kicad.md` et `$SK/references/preferences_utilisateur.md`.
2. `python $SK/scripts/inventaire_materiel.py data/<lieu>/<carte>` → broches réelles.
3. Poser **une seule question groupée** (outil de question, options + recommandation) :
   architecture (porteuse + modules / CMS / intégré) ; tension d'entrée et ce qu'elle alimente ;
   modules **réellement achetés** (lien ou photo) et leur tension ; ce que commande chaque sortie
   (relais : quoi, quelle tension) ; nature de chaque entrée (contact sec, capteur, câble) ;
   périphériques présents ou non (ruban, ADS, sonde) ; dimensions du **boîtier** ; entraxe du
   DevKit mesuré ? Ne poser que ce que le persist et les docs ne tranchent pas.

## Flux

| Étape | Outil | Critère de sortie |
|---|---|---|
| Description | copier `$SK/exemples/generer_carte_cuve.py` dans le dossier du projet | chaque broche a un net ou `None` |
| Premier jet | sous-agent `placeur-pcb`, ou `<python KiCad> generer_xxx.py --sans-routage` | règles de `preferences_utilisateur.md` |
| Revue 3D **avec l'utilisateur** | `<python KiCad> $SK/scripts/revue_3d.py <x>.kicad_pcb [--rasante] [--svg-cuivre]` (~40 s) → planche PNG + page HTML autonome dans `<carte>/revue_3d/` ; lui donner leurs chemins | son accord avant de router |
| Bilan d'alimentation | `python $SK/scripts/bilan_alimentation.py <x>.kicad_sch --strict` (charges hors carte : `bilan.json` à côté, modèle `exemples/bilan_cuve.json` ; consommation d'un module : `champs={"Conso_mA": "30", "Rail": "5V"}`) | « À renseigner : Aucun », 0 alerte, calibre retenu donné à l'utilisateur |
| Routage + masse | même script sans option (~1 min, en arrière-plan) | « N/N nets routes » |
| Vérification | `kicad-cli sch erc --severity-all` ; `kicad-cli pcb drc --schematic-parity --severity-all` | 0 erreur, 0 non connecté, 0 écart |
| Relecture | sous-agent `relecteur-pcb` | rapport sans point bloquant |
| Export | `python $SK/scripts/export_fabrication.py <x>.kicad_pcb` | zip Gerber + rapport |
| Boîtier | `python $SK/scripts/export_boitier.py <x>.kicad_pcb` (~10 s) → `boitier/` : STEP complet, DXF du contour + trous + connecteurs du bord, fiche de cotes | code 0 (un modèle 3D absent du STEP → code 2) |
| Commande | `$SK/references/fabrication.md` (liste de contrôle) | encombrements **mesurés** |

## Scripts et ressources

- `scripts/kicad_gen.py` (`Schema`) et `scripts/kicad_carte.py` (`Carte`, `empreinte_libre`,
  `reperes`, `cadre`, `zone`, `interdiction`, `enregistre`) ; `scripts/routeur_grille.py`
  (`route_tout`, `route_net`, `coutures` ; `poids=2` = essai rapide à vérifier par le DRC ;
  `moteur="freerouting"` ou `PCB_ROUTEUR=freerouting` pour une carte que la grille ne finit pas,
  outils : `scripts/routeur_freerouting.py --verifier | --installer`) ; `scripts/inventaire_materiel.py` ;
  `scripts/export_fabrication.py`, `scripts/revue_3d.py`, `scripts/bilan_alimentation.py`,
  `scripts/export_boitier.py`
  (`--help`) ; consommations par défaut sourcées : `references/consommations.json`.
- `assets/Signature_Auteur.pretty` : signature « Frédéric - Au Bonheur des Asturies » + logo
  (croix asturienne), **sur chaque carte** (verso par défaut) ; `assets/generer_logo.py` la régénère.
- `assets/Modules_Tasmota.pretty` + `.3dshapes` (STEP) : DevKitC-1 (entraxe 22,86 / 25,40),
  ADS1115, RS485 XY-017 ; pastilles = barrettes femelles, modèle 3D complet pour la revue et le
  boîtier. Cotes en tête de `assets/generer_modules.py` (« à mesurer » / « mesurée le … ») :
  relancer après mesure. Le projet définit `PCB_TASMOTA_3D` dans son `.kicad_pro` (pièges 35-36).
- `exemples/generer_carte_cuve.py` : la carte de référence complète (cuve v0.1, DRC 0).

## Références

- `references/electronique_tasmota.md` : broches ESP32-S3, mesure du DevKit, interfaces
  (ruban, ADS, RS485, entrées TOR, relais), protection d'entrée, **bilan d'alimentation**.
- `references/fabrication.md` : règles JLCPCB/PCBWay, contrôles CEM, fichiers, commande.
- `references/outils_externes.md` : kicad-happy, MCP KiCad, extensions JLCPCB, Freerouting.
- Code Berry et persist : **REQUIRED SUB-SKILL : tasmota-berry**.

## Erreurs fréquentes

| Erreur | Parade |
|---|---|
| Croire le persist sur le matériel | demander ; le persist décrit la configuration |
| Ranger le projet sous `data/` | c'est le LittleFS flashé : `outils_docs/Schémas de branchement…/<lieu>/<carte>/PCB/` |
| `ZONE_FILLER`, `LoadBoard`, `GetLayerID` en Python | pièges 1-2 : kicad-cli et constantes |
| Labels locaux pour les alimentations | `net_conflict` en masse : labels globaux (piège 4) |
| Composant loin de la rangée de son GPIO | une barrette au pas de 2,54 est un mur (piège 11) |
| Router avant la revue 3D | itérer `--sans-routage`, router à la fin |
| Commander sans mesurer DevKit et modules | une porteuse décalée est perdue |
| Modèle 3D absent, sans erreur | variable `PCB_TASMOTA_3D` ; compter les `PRODUCT(` du STEP (piège 35) |

## Après chaque carte

Nouveaux pièges → `references/pieges_kicad.md` (ajout en fin, numéros stables) ; retours de
l'utilisateur → `references/preferences_utilisateur.md` ; ses corrections → `tasks/lessons.md`.
Un rôle qui revient → nouveau sous-agent dans `.claude/agents/`.
