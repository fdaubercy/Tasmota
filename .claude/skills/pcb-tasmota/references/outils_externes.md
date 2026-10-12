# Outils et skills externes (veille du 2026-10-11/12)

[V] = page lue ; le reste est à vérifier avant usage.

## Intégré dans cette skill (reformulé, source citée)

**aklofas/kicad-happy** — https://github.com/aklofas/kicad-happy — MIT, « Copyright (c) 2025
Andrew Klofas », KiCad 5 à 10, Python stdlib. [V] skills jlcpcb, pcbway, kicad, bom, emc.
Repris **sous forme de règles reformulées** (pas de copie de texte ni de code) dans
`fabrication.md` § Contrôles CEM et § Avant commande. Si un jour on copie un script ou un
passage substantiel, joindre le texte de licence MIT et la ligne de copyright (fichier
`THIRD_PARTY_NOTICES.md` dans la skill).
Non repris : distributeurs (clés API), assemblage CMS, 4 couches, SPICE, `fab_release_gate.py`
(dépend de leurs analyseurs ; il sort en code 0 même en échec : lire `overall_status`).
Installation complète possible : `npx skills add aklofas/kicad-happy` (non vérifié).

## Référencés (à utiliser au besoin)

| Outil | Usage | Statut |
|---|---|---|
| Bouni/kicad-jlcpcb-tools (MIT) | extension KiCad 7-10 : numéros LCSC, BOM/CPL, rotations | [V] ; utile seulement pour l'assemblage |
| bennymeg/Fabrication-Toolkit (Apache-2.0) | extension : Gerber + BOM + CPL au format JLCPCB | [V] ; compat. KiCad 10 non confirmée |
| uPesy/easyeda2kicad (AGPL-3.0) | importer symbole + empreinte d'une pièce LCSC : `python -m easyeda2kicad --full --lcsc_id=Cxxxx` | [V] ; **vérifier l'empreinte sur la fiche technique** |
| mixelpixx/KiCAD-MCP-Server (MIT) | serveur MCP : placement, routage, Freerouting, catalogue JLCPCB | [V] ; KiCad 9, KiCad 10 non démontré : ne pas en dépendre |
| lamaalrajih/kicad-mcp (MIT) | serveur MCP surtout en lecture (DRC, BOM, netlist) | [V] ; gain faible face à kicad-cli |
| INTI-CMNB/KiBot (AGPL-3.0) | chaîne d'export configurable | [V] ; kicad-cli suffit |
| Freerouting 2.5.0 (GPL-3.0) | autorouteur DSN/SES, option `Routeur(..., moteur="freerouting")` | **installé hors dépôt** (`%LOCALAPPDATA%\pcb-tasmota\outils\`, `scripts/routeur_freerouting.py --installer`, SHA-256 vérifiés) ; exige **Java 25** (Temurin 25.0.4.1+1 portable) ; sur la cuve : 33/33, DRC 0, mais pas plus rapide que la grille → pour une carte que la grille ne finit pas |
| FreeCAD 1.1.4 (LGPL) | ouvre le STEP et le DXF de `export_boitier.py` ; dessin du boîtier autour de la carte ; atelier KiCad StepUp (gestionnaire d'extensions) pour l'aller-retour avec KiCad | **installé** (winget, `%LOCALAPPDATA%\Programs\FreeCAD 1.1`) ; mesures en script : piège 54 |

## Bibliothèques d'empreintes

1. Bibliothèques officielles KiCad (communauté, dans l'installation) : toujours en premier.
   Absente au 2026-10-12 : l'ESP32-S3-DevKitC-1 → deux `PinSocket_1x22` à l'entraxe mesuré.
2. LCSC / EasyEDA via easyeda2kicad : pratique pour les pièces JLCPCB, à relire.
3. SnapEDA, Ultra Librarian, Component Search Engine : inscription requise, à relire.
4. Espressif `kicad-libraries` : son DevKitC-1 utilise 22,86 mm d'entraxe, contesté (25,4 mesuré).
