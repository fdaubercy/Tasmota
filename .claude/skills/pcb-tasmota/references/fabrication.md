# Fabrication : règles, fichiers, commande

Sources lues le 2026-10-11 : https://jlcpcb.com/capabilities/pcb-capabilities ,
https://jlcpcb.com/help/article/how-to-generate-the-bom-and-centroid-file-from-kicad ,
https://www.pcbway.com/capabilities.html , https://docs.kicad.org/10.0/en/cli/cli.html .
Les prix et options changent : **revérifier sur le site au moment de commander.**

## Règles de conception (2 couches, 1 oz)

| Règle | Minimum JLCPCB | PCBWay | **Retenu ici** (`Carte.regles`) |
|---|---|---|---|
| Piste / isolement | 0,10 / 0,10 mm | 0,10 mm | isolement 0,2 ; piste min 0,2 ; signal 0,35 ; puissance 0,8-1,0 |
| Via : perçage / diamètre | 0,15 (0,2 conseillé) / 0,25 | 0,15 | 0,4 / 0,8 |
| Anneau traversant | 0,18 (0,25 conseillé) | 0,15 | 0,15 min (empreintes KiCad ≥ 0,4) |
| Trou non métallisé | 0,50 | — | trous M3 3,2 |
| Sérigraphie : hauteur / trait | 1,0 / 0,15 | 0,8 / 0,15 | 1,0 / 0,15 |
| Cuivre au bord (fraisé) | 0,2 (0,4 en V-cut) | 0,25 ? | 0,5 |
| Trou à trou | — | — | 0,5 |

L'autorouteur ajoute sa propre réserve (isolement 0,25 + marge 0,12 mm). Le DRC de KiCad fait foi.

## Fichiers à envoyer

`python scripts/export_fabrication.py <carte>.kicad_pcb --fabricant jlcpcb` : contrôles
bloquants (ERC + DRC avec parité), Gerber, perçages Excellon, **zip à téléverser**, BOM et CPL
au format du fabricant, PDF du schéma et du PCB, rendus 3D. `--help` pour le détail.

- **Carte nue** (le cas courant ici) : seul le **zip Gerber + perçages** est envoyé.
- **Assemblage** (CMS posés par le fabricant) : + BOM `Comment,Designator,Footprint,JLCPCB Part #`
  + CPL `Designator,Mid X,Mid Y,Layer,Rotation` (mm). Les rotations du CPL sont souvent fausses
  chez JLCPCB : contrôler l'aperçu en ligne, ou passer par les extensions kicad-jlcpcb-tools /
  Fabrication Toolkit (voir `outils_externes.md`).

## Options de commande conseillées (carte nue, prototype)

| Option | Choix | Raison |
|---|---|---|
| Couches | 2 | même prix que 1 couche ≤ 100 × 100 mm |
| Matériau / épaisseur | FR-4, 1,6 mm | standard, rigide pour des borniers à vis |
| Cuivre | 1 oz | suffit pour 2-3 A avec des pistes de 1 mm courtes |
| Finition | HASL sans plomb | soudure maison facile ; ENIG inutile en traversant |
| Couleur | verte | la moins chère et la plus rapide |
| Quantité | 5 | minimum courant, même prix que 2 |
| Numéro de commande sérigraphié | « Specify location » ou option de retrait, selon l'offre du moment | sinon il est imprimé n'importe où |

## Contrôles CEM et mécaniques (d'après kicad-happy, skills emc et kicad, reformulé)

- Plan de masse continu sous chaque signal ; aucun signal qui traverse un vide de plan ;
  au plus 3 îlots de masse ; masse le long du pourtour.
- Découplage à moins de 5 mm du circuit intégré (critique au-delà de 8 mm).
- Connecteurs externes (RS485, entrées capteurs, ruban) : TVS ou filtre à moins de 15-25 mm du
  connecteur, avec vias de masse à moins de 3 mm de la patte de masse du TVS.
- Antenne ESP32 : exclusion cuivre de 5 à 10 mm au-delà de l'élément rayonnant, toutes couches ;
  idéalement l'antenne dépasse du bord de carte.
- Distances au bord : traversant 2 mm (sauf borniers volontairement au bord), trous de
  fixation à 3 mm du composant le plus proche, cuivre ≥ 0,3 mm (0,5 retenu).
- Largeur de piste (1 oz, +10 °C) : < 0,1 A → 0,2 mm ; 0,1-1 A → 0,3-0,5 mm ; 1-5 A → 0,5-1 mm.
- Électrolytiques et MLCC : tension de service ≤ 80 % de la nominale.
- Remplir les zones **juste avant** d'exporter (le générateur et l'export le font).

## Liste de contrôle avant commande

1. ERC 0 erreur ; DRC 0 erreur, 0 pastille non connectée, 0 écart schéma/PCB.
2. **Encombrements mesurés** : entraxe des rangées du DevKit, modules (ADS1115, RS485), trous
   de fixation du boîtier. Une carte porteuse fausse de 2,5 mm est perdue.
3. Brochage de chaque module vérifié sur le module **acheté** (pas sur une photo générique).
4. Orientation des borniers (ouvertures vers l'extérieur), polarités (diodes, électrolytiques,
   LED), repère broche 1 des circuits intégrés.
5. Vue 3D relue avec l'utilisateur ; étiquettes en français ; signature présente.
6. Ouvrir le zip dans la visionneuse Gerber du fabricant avant de payer.
