# Préférences de l'utilisateur pour ses PCB

But : produire un **premier jet de placement** qui lui ressemble, sans tout redemander.
Chaque retour de l'utilisateur sur une carte s'ajoute ici (date + carte), puis la règle
générale qui en découle. Statut : **[validé]** = dit ou confirmé par lui ;
**[proposé]** = mon choix, pas encore commenté (à confirmer sur la vue 3D).

## Décisions générales [validé]

- **Étiquettes de sérigraphie en français** (2026-10-12).
  Détails **[validé 2026-10-12]** : « GND » s'écrit « 0V » ; les sigles imprimés sur les
  composants et modules (DI, BI, DQ, SCL, SDA, TX, RX, GPIO, A0…) restent tels quels pour câbler
  sans erreur.
- **Comment appliquer un [proposé]** : l'appliquer au premier jet (c'est ce qu'il a vu et pas
  contesté), et le signaler en une ligne dans le compte rendu pour qu'il puisse le corriger.
- **Signature sur chaque carte** : « Frédéric - Au Bonheur des Asturies » + son logo
  (bibliothèque `assets/Signature_Auteur.pretty`). Même logo pour tous ses PCB (2026-10-12).
- **Simple ou double face** : décidé selon la place, le boîtier qui contiendra la carte et le
  coût de fabrication (2026-10-12). Chez JLCPCB, 1 et 2 couches ont le même prix jusqu'à
  100 × 100 mm → double face par défaut ; simple face seulement s'il y a un vrai gain.
- **Bilan d'alimentation** avec marge de sécurité, pour choisir l'alimentation du boîtier
  (2026-10-12). Méthode : `electronique_tasmota.md` § Bilan.
- **Carte porteuse + modules du commerce** (DevKit, ADS1115, RS485… sur barrettes femelles),
  composants traversants, soudure maison, pas d'assemblage chez le fabricant (2026-10-11, cuve).
- **Ordre de travail** : premier jet de placement → ajustements sur la **vue 3D** avec lui →
  seulement ensuite les étapes suivantes. Ne pas enchaîner jusqu'à la commande sans ce passage.
- **Sous-agents bienvenus** pour accélérer, avec modèle et niveau d'effort adaptés à la tâche
  (2026-10-12).
- **Rangement [validé 2026-10-12]** : projet KiCad d'une carte dans `outils_docs/Schémas de
  branchement - Attribution des PINS des modules/<lieu>/<carte>/PCB/` (nom de carte = celui du
  dossier `data/<lieu>/<carte>`) ; skill et sous-agents dans `.claude/` (suivi par git).
  **Jamais** sous `data/` (flashé).
- **Retenir ses erreurs** : chaque piège va dans `pieges_kicad.md`, chaque correction de
  l'utilisateur dans `tasks/lessons.md` du dépôt (2026-10-12).

## Règles de placement du premier jet [proposé — carte cuve v0.1, à confirmer]

1. Carte ≤ 100 × 100 mm (palier le moins cher), 4 trous M3 dans les coins.
2. **Borniers sur les bords, ouvertures vers l'extérieur** ; un groupe de bornes par fonction.
   Étiquette de chaque borne juste à côté, côté carte.
3. **Alimentation en haut à gauche**, dans l'ordre du courant : bornier → fusible réarmable →
   diode série → TVS + condensateur → régulateur → 5 V.
4. **Module ESP32 en haut à droite**, antenne au ras du bord avec zone d'exclusion cuivre ;
   aucun composant haut sur le trajet du câble USB.
5. **Conditionnement analogique aligné au-dessus de son bornier** (une colonne par voie),
   bornes des capteurs regroupées sur un même bord.
6. **Voyants hors de l'emprise du DevKit** (visibles) et du même côté de la rangée que leurs GPIO.
7. Les composants bas (résistances couchées) peuvent passer sous un module enfiché surélevé.
8. Modules enfichés placés avec leurs empreintes `Modules_Tasmota` (contour, courtyard et
   modèle 3D réels, cotes « à mesurer » tant qu'elles ne sont pas relevées) ; un cadre en
   couche commentaires seulement pour un module pas encore dans la bibliothèque (piège 52).

## Historique des retours

- 2026-10-12 — cuve v0.1 : étiquettes en français ; signature + logo ; placement à revoir
  ensemble sur la vue 3D.
- 2026-10-12 — cuve v0.1 : étiquettes « 0V » + sigles conservés validés ; rangement validé.
  Améliorations de la skill retenues : routage accéléré, revue 3D en une commande, bilan
  d'alimentation automatique, export 3D/contour pour le boîtier, sous-agent de premier jet de
  placement, bibliothèque des modules mesurés avec modèles 3D.
