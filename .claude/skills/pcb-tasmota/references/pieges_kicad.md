# Pièges rencontrés — KiCad 10, génération et routage

Journal **append-only** : chaque entrée a coûté du temps une fois. La relire avant toute
génération de carte. Format : symptôme → cause vérifiée → parade (déjà intégrée ou à appliquer).

## API Python `pcbnew` (KiCad 10.0.3, hors interface graphique)

1. **Remplissage de zones = plantage du processus** (`Windows fatal exception: access violation`
   dans `ZONE_FILLER.Fill`), même après `BuildConnectivity()`. `pcbnew.LoadBoard()` échoue aussi
   (`assert "process" failed in Pgm()`).
   → Construire la carte en mémoire, `SaveBoard`, puis remplir par
   `kicad-cli pcb drc --refill-zones --save-board` (intégré à `Carte.enregistre`).
2. **Fichier illisible** (« Échec du chargement de la carte ») : `board.GetLayerID("F.SilkS")`
   rend `UNDEFINED` sur une carte neuve (le nom affiché est « F.Silkscreen ») et écrit
   `(layer "UNDEFINED")`. → Constantes `pcbnew.F_SilkS`… via `id_couche()`.
   Méthode de diagnostic qui a marché : **bissection** (générer la carte étape par étape et
   faire relire chaque variante par `kicad-cli pcb drc`).
3. Les erreurs de `kicad-cli` ne sont pas détaillées : un code retour 3 + « Échec du chargement »
   = fichier mal formé. Ne jamais capturer la sortie d'une étape sans en vérifier le code retour.

## Cohérence schéma ↔ PCB (`kicad-cli pcb drc --schematic-parity`)

4. **166 `net_conflict`** : un label **local** sur la feuille racine produit le net `/NOM`, pas
   `NOM`. → Labels **globaux** pour les alimentations (`+12V`, `GND`… : nom sans préfixe),
   labels locaux ailleurs, et le PCB nomme ses nets avec `nom_net_pcb()`.
5. **Broches non connectées** : KiCad leur attribue le net `unconnected-(J2-Pin_13-Pad13)`
   (`unconnected-(REF-Pad6)` si la broche n'a pas de nom). Le PCB doit porter le même nom.
6. `footprint_symbol_mismatch` « Exclure de la liste du matériel » : le symbole du trou de
   fixation doit être `bom=False`, comme l'empreinte.
7. ERC `lib_symbol_mismatch` sur un symbole dérivé (`extends`, ex. 74AHCT125) : bénin. Dans
   l'IHM, « Mettre à jour les symboles depuis la librairie » le lève.
8. ERC « La configuration actuelle n'inclut pas la librairie » ×100 : KiCad 10 jamais configuré
   sur le poste (aucune `sym-lib-table` dans `%APPDATA%\kicad\10.0`). → Le générateur écrit des
   tables **propres au projet** (`${KICAD10_SYMBOL_DIR}`, `${KICAD10_FOOTPRINT_DIR}`).
9. ERC `endpoint_off_grid` : symbole hors grille de 1,27 mm → positions arrondies à 2,54 mm.

## Placement

10. **Borniers Phoenix MKDS « Horizontal » : l'ouverture des fils est du côté +y de l'empreinte.**
    Je les avais d'abord tournés ouvertures vers l'intérieur. Vérifié sur un rendu 3D vu de dos
    (`--side back --zoom 3`) : la vue de face ne montre que le dos plein. Rotation 0 = ouverture
    vers le bas de la carte ; 270 = vers la gauche ; 90 = vers la droite ; 180 = vers le haut.
11. **Une rangée de barrette au pas de 2,54 mm est un mur** : une piste de 0,35 mm avec 0,25 mm
    d'isolement ne passe pas entre deux pastilles de 1,7 mm. Des LED placées en haut alors que
    leurs GPIO étaient sur la rangée du bas → pistes contournant tout le DevKit, LED enfermée,
    masse impossible à raccorder. → **Placer chaque composant du même côté de la rangée que sa
    broche GPIO.**
12. Courtyards qui se chevauchent : calculer l'emprise réelle après rotation (les courtyards
    MKDS débordent de 3 mm côté broche 1 et de 13 mm côté dernière broche selon la rotation).
13. Texte de sérigraphie : un accent (É) dépasse vers le haut et touche la sérigraphie voisine ;
    les repères de composants chevauchent les étiquettes → masquer le repère quand une étiquette
    explicite le remplace (`Carte.reperes(masques=...)`).

## Routage (routeur_grille.py)

14. **Violation d'isolement de 0,15 mm** malgré une marge : une diagonale passait entre un nœud
    libre et un nœud interdit. → Diagonale autorisée seulement si **les deux** voisins orthogonaux
    sont libres.
15. Agrandir la marge (0,12 → 0,2 mm) a fait chuter le routage de 34/34 à 30/34 : corriger la
    cause (point 14) plutôt que la marge.
16. Router la masse en pistes au milieu des signaux consomme la place : **router GND en dernier**,
    échec toléré, puis plans de masse 2 faces + vias de couture.
17. Via de couture tombé dans un îlot de cuivre isolé (`via_dangling`) → `retire_vias_isolees()`
    lit le JSON du DRC et retire les vias par uuid, puis remplit à nouveau.
18. `starved_thermal` sur les petites pastilles de masse cernées → règle `.kicad_dru`
    `min_resolved_spokes 1` (écrite par le générateur).
19. Durée : 3 à 8 min par génération complète (A* pur Python, 2 couches, grille 0,3175 mm, 10
    passes au plus). Itérer le placement **sans routage** (`--sans-routage`) et ne router qu'à la fin.

## Rendus de vérification

20. `kicad-cli pcb render --side top` = contrôle du placement en 20 s ; `--rotate "-50,0,20"
    --perspective` = vue d'ensemble ; une vue de dos zoomée pour l'orientation des connecteurs.
    Le rendu ne montre pas les pistes sous les modules : compléter par
    `kicad-cli pcb export svg` ou par le DRC.

## Dépôt Tasmota

21. **Ne jamais ranger un projet de PCB dans `data/<lieu>/<carte>/`** : ce dossier EST le
    `data_dir` du LittleFS (`pre_utilitaires_platformio.py:303` et `:528`) ; tout son contenu
    serait flashé dans l'ESP32.
22. Le `template.GPIO` d'un persist peut être périmé : `configModules.be:131-146` le réécrit au
    démarrage depuis les blocs `environnement` (code = `type + id - 1`). L'environnement fait foi.
23. Un persist décrit la configuration, pas le câblage : `alimentation_V`, un état `ON`, un
    `POWER ON` ne prouvent rien sur ce qui est soudé. Deux écrits du dépôt se sont contredits
    sur la tension de l'ADS1115 de la cuve : demander, ne pas trancher.

## kicad-cli (constatés par le sous-agent d'export, 2026-10-12)

24. Noms de couches de `kicad-cli pcb export gerbers -l` : KiCad 10 veut `F.Silkscreen` /
    `B.Silkscreen` ; `F.SilkS` (ancien nom court) est refusé.
25. `--exit-code-violations` renvoie un code non nul dès qu'un **avertissement** est inclus dans
    le rapport : pour bloquer seulement sur les erreurs, lire le JSON (`severity == "error"`).
26. Témoin négatif d'un DRC : modifier le net d'une piste dans le texte du `.kicad_pcb` ne sert à
    rien (KiCad recalcule le net d'après les pastilles touchées au chargement). Un vrai court-
    circuit s'obtient en déplaçant un composant sur un autre.
27. CPL : `kicad-cli pcb export pos` donne des Y négatifs (repère KiCad) : normal ; JLCPCB veut
    `Mid X`/`Mid Y` suffixés `mm`. Les plans de perçage (`*-drl_map.gbr`) restent hors du zip :
    un fabricant les prendrait pour une couche.
28. Les messages de kicad-cli sont localisés (français) : ne jamais les analyser, seulement les
    JSON et les codes retour.

## Revue 3D (revue_3d.py, 2026-10-12)

29. `kicad-cli pcb render --side back` / `--side front` sont des vues **par la tranche** (bord
    arrière / avant de la carte), pas la face dessous : la face dessous, c'est `--side bottom`.
    `back --zoom 2` montre l'ouverture des borniers du bord haut (piège 10).
30. Rendus en parallèle : 4 à la fois ≈ ×1,8 seulement (CPU partagé ; 75 s → 41 s sur la cuve).
31. SVG du cuivre cadré sur la carte : `kicad-cli pcb export svg --mode-single --page-size-mode 2
    --exclude-drawing-sheet -l F.Cu,Edge.Cuts`.
32. Dans le `.kicad_pcb`, la rotation de `(at x y rot)` est **absente** quand elle vaut 0 ; la
    face d'un composant vient de son `(layer "F.Cu"|"B.Cu")`.

## Électronique relevée par le bilan (2026-10-12)

33. Voyant **bleu** sur un GPIO 3,3 V avec 1 kΩ (cuve v0.1, LED1/R11) : (3,3 − 3,0) / 1 k =
    0,3 mA, à peine visible. Une même résistance ne convient pas à toutes les couleurs : la
    calculer par couleur (`electronique_tasmota.md` §3) ; `bilan_alimentation.py` affiche le
    courant de chaque LED, le relire.

## Bibliothèque Modules_Tasmota et modèles 3D (2026-10-12)

34. **Entraxe du DevKitC-1** : le plan officiel Espressif (DXF v1.1 du 2022-04-29) donne une carte
    de 25,40 × 62,865 mm, axes des broches à 1,27 mm des bords longs → **22,86 mm** ; un
    utilisateur KiCad et les clones (~28 mm de large) donnent **25,4**. Deux empreintes
    (`ESP32-S3-DevKitC-1_E22.86mm` / `_E25.40mm`) ; ne rien commander sans mesure.
35. **Modèle 3D introuvable = silence** : `kicad-cli pcb export step` et `pcb render` rendent 0
    même si `${PCB_TASMOTA_3D}` n'est pas résolu. Preuve : compter les `PRODUCT('<modèle>'` dans
    le STEP exporté (témoin : 1 solide sans la variable, 130 avec).
36. **Variable de projet pour les modèles 3D** : `text_variables` du `.kicad_pro` est lu par
    kicad-cli et peut contenir `${KIPRJMOD}` (expansion imbriquée, 10.0.3). `--save-board` ne
    touche pas au `.kicad_pro`.
37. pcbnew : `for m in fp.Models(): m.m_Filename = ...` ne modifie qu'une **copie**, sans erreur.
    Copier la liste, `fp.Models().clear()`, puis `fp.Add3DModel(m)`.
38. Un vrai saut de ligne dans une chaîne d'un `.kicad_mod` casse **toute** la bibliothèque
    (« Impossible de charger la librairie ») : écrire `\n` échappé.
39. `kicad-cli fp export svg -o <dossier absent>` : message d'échec mais **code retour 0**. Créer le
    dossier avant et vérifier les fichiers produits.
40. STEP généré en Python pur (`assets/generer_modules.py`) : OCCT accepte un AP214 de boîtes
    (MANIFOLD_SOLID_BREP + STYLED_ITEM) ; repère du modèle **y vers le haut** (inverse de
    l'empreinte). Un modèle utilisé deux fois n'est instancié qu'une fois : compter les produits.
41. Courtyard d'un module enfiché = **tout** le module (antenne, USB) : un composant placé
    dessous, même bas, donne `courtyards_overlap` (KiCad ignore les hauteurs) → la règle de
    placement 7 (« composants bas sous un module ») demande une exclusion justifiée en revue.
42. Antenne du DevKitC-1 : le WROOM-1 déborde de **6,3 mm** au-delà du bord du DevKit. L'empreinte
    porte une zone d'interdiction, mais `routeur_grille` ne la lit pas : garder `INTERDITS`.
43. Remplacer les PinSocket de la cuve par les empreintes de modules ne bouge aucune pastille
    (DevKit à la place de J2, pastilles 23-44 = ancien J3 ; ADS1115 rotation 90 → 0) ; mais un
    RS485 XY-017 (42,6 mm) en (80 ; 47) **dépasserait de 21 mm** la porteuse : identifier le
    module réellement acheté avant.

## Routage rapide et Freerouting (2026-10-12) — corrige la durée du piège 19

44. Mesurer un temps de routage **sans cProfile** (×5 sur une boucle Python : 382 s profilés
    contre 66-94 s réels) et comparer avant/après lancés en même temps. Durée réelle de la cuve
    après optimisation : ~47 s de routage + ~13 s d'enregistrement et remplissage (piège 19 :
    « 3 à 8 min » était l'ancienne mesure, sous charge).
45. `routeur_grille` : `poids=2` (A* pondéré) route la cuve en 12 s au lieu de 47, mais
    `poids=1.3` a laissé GND incomplet (1 non connecté) : jamais par défaut, toujours vérifier
    par le DRC.
46. `pcbnew.ExportSpecctraDSN(board, chemin)` et `ImportSpecctraSES(board, chemin)` fonctionnent
    **hors IHM** (10.0.3) ; kicad-cli n'a pas d'export DSN. L'import remplace toutes les pistes
    non verrouillées.
47. `CONNECTIVITY_DATA.GetConnectedPads(item)` ne rend que les voisins directs ; tout l'îlot :
    `GetConnectedItems(item)` après `board.BuildConnectivity()`.
48. `PCB_VIA.GetWidth()` sans couche : assert KiCad 10, puis le processus Python peut **se
    bloquer sans CPU**. Appeler `GetWidth(pcbnew.F_Cu)`.
49. Freerouting 2.5.0 : le CLI natif Windows (sans Java) plante et reste bloqué ; le jar exige
    **Java 25** (Java 21 → `UnsupportedClassVersionError`, class file 69).
50. DSN de KiCad pour Freerouting : une seule classe à 0,2 mm et une « neckdown » à 0,15 mm
    (`track_width` au DRC) → `routeur_freerouting.py` réécrit les classes, coupe la neckdown,
    ajoute une bande interdite de 0,6 mm au contour. `-inc <classe>` ne suffit pas à ignorer GND
    (arrêt prématuré « no improvement ») : **retirer le net du bloc `network`**.
51. Freerouting envoie des statistiques anonymes par défaut : toujours passer `-da` ;
    `disable_analytics: true` posé dans `%APPDATA%\freerouting\freerouting.json` (2026-10-12).

## Modules réels sur la cuve (2026-10-12)

52. **Un cadre d'encombrement dessiné à la main ment** : les PinSocket génériques + cadres
    Cmts.User de la cuve v0.1 donnaient DRC 0, mais les vraies empreintes Modules_Tasmota
    (courtyard = module entier) révèlent 16 conflits : le DevKit officiel (62,9 mm) recouvre U1
    et D1, et **U1 (TSR, haut) barre la prise USB-C** ; l'ADS1115 recouvre R11-R13. → Toujours
    placer avec les empreintes de modules, jamais avec un cadre.
53. `export_boitier.py` : le témoin négatif (carte copiée sans son `.kicad_pro`, donc sans
    `PCB_TASMOTA_3D`) rend bien le code 2 ; un `| tail` dans la commande masque ce code.

## FreeCAD (installé le 2026-10-12 : FreeCAD 1.1.4, %LOCALAPPDATA%\Programs\FreeCAD 1.1)

54. STEP de KiCad ouvert dans FreeCAD : chaque `Part::Feature` garde ses coordonnées **locales**,
    le placement est porté par l'assemblage parent → mesurer avec
    `s = o.Shape.copy(); s.Placement = o.getGlobalPlacement()`, sinon l'encombrement est faux
    (204 × 166 mm au lieu de 103 × 100). Filtrer aussi les formes sans solide (boîte invalide
    de ±1e100). Cuve v0.1 : 103,1 × 100 × 19,7 mm, DevKit le plus haut, queues −2,3 mm.
    Sans IHM : `"%LOCALAPPDATA%\Programs\FreeCAD 1.1\bin\FreeCADCmd.exe" script.py` (~40 s).
