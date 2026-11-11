---
chantier: atelier-ecrans
titre: Atelier des écrans (page 7960) : une description d'écran, deux interfaces générées
objectif: Modifier sur le PC la disposition d'un écran tactile de carte (objets, boutons, pages) et y épingler des remarques, puis générer de la même description le pages.jsonl de HASPmota et le code LVGL pur en Berry
statut: actif
cree: 2026-11-11
maj: 2026-11-11
---
# Atelier des écrans

## Contexte
Demande de l'utilisateur du 2026-11-11, version **C** retenue parmi trois (A : remarques seules ; B : éditeur HASPmota ;
C : description neutre dont on génère les deux interfaces). Ce plan est l'action A9 du plan
`tasks/plans/debits-deux-cartes.md` ; l'écran des débits (Waveshare 7B, 1024 × 600, pages A « Débits », D « Courbes »
et « Réglages ») est son premier cas réel.

**Architecture visée** (à confirmer par la spec de A1) :
- une **description d'écran** neutre par carte, `data/<lieu>/<carte>/ecran.json` : écran visé (résolution, orientation,
  tactile), pages, objets (type, position, taille, style, police, texte), liaison de chaque objet à une valeur du
  modèle d'écran (API de `ecranDebitsFonctions.be`, en tête du module), actions des boutons ;
- deux **générateurs** sur le PC : description → `pages.jsonl` (HASPmota) et description → `ecranLvgl.be` (LVGL pur,
  même API d'interface que `ecranHaspmota.be`) ; l'interface envoyée reste choisie par `custom_interface_ecran` du cenv
  (`build/interface_ecran.py`) ;
- un **catalogue** au dépôt, `outils_docs/schemas/catalogue_ecran.json` : objets et attributs gérés, polices et tailles
  compilées dans le firmware, écrans connus ; extrait des sources Tasmota par un script, vérifié par un banc ;
- la **page web** (port 7960, modèle des autres outils : annuaire, tâche VS Code, cible Custom détachée, `acces_web.py`) :
  canevas à la taille réelle de l'écran, glisser-déposer, palette, propriétés, pages, remarques ; diff puis écriture
  atomique ; envoi par la page Build.

**Lien avec la skill globale `lvgl-haspmota`** (demande du 2026-11-11 : « cette interface web pourra utiliser la
skill ») : la skill et l'atelier partagent la même connaissance. Le catalogue du dépôt est la source unique des objets,
attributs et polices ; la skill y renvoie et décrit l'atelier ; les remarques épinglées dans la page sont traitées par
Claude avec cette skill (vues proposées pour l'écran en cours, polices du firmware, ressources sous `/sd` choisies avec
l'utilisateur, code générique solidifiable).

**Sources : ouvertes seulement.** LVGL (MIT), Tasmota, HASPmota et la liaison Berry (GPL) suffisent : les attributs et
le rendu se lisent dans `lib/libesp32_lvgl/`. Pas de rétro-ingénierie d'éditeurs propriétaires (SquareLine Studio,
LVGL Pro) : leurs licences l'interdisent et leur format (C, XML) ne sert pas sur nos cartes.

**Question ouverte, à trancher en A1** : l'interface LVGL pur de l'écran des débits (A8 de `debits-deux-cartes`,
sous-étape non commencée) s'écrit-elle à la main maintenant, ou est-elle produite par le générateur de A5 ?

### Contraintes globales
- Fichiers sous 500 lignes ; aucune nouvelle dépendance Python ni JS sans accord.
- Python des bancs `outils_pc/` : `"$USERPROFILE/.platformio/penv/Scripts/python.exe"` ; bancs sur copies temporaires.
- Compilation et FS par la page Build (:7700) seulement ; écriture refusée pendant un build.
- `data/fs/*.be` et `_persist.json` : accord de l'utilisateur avant modification.
- Ressources d'écran (images, fonds, polices ajoutées) sous `/sd`, choisies AVEC l'utilisateur.
- Logs Berry : charte du `CLAUDE.md` ; avant commit : `relecteur-berry` (Berry) et `relecteur-pages-web` (page).

## A0 — Plan précédent : débits sur deux cartes
Plan d'origine de ce chantier : [tasks/plans/debits-deux-cartes.md](debits-deux-cartes.md), action A9.
- [ ] Rouvrir le plan précédent dans la vue de droite : taper `/suivi suivre debits-deux-cartes` (la conversation suit
  alors ce plan) ; revenir à celui-ci : `/suivi suivre atelier-ecrans`. À cocher quand l'aller-retour a été fait une
  fois et que la vue a basculé dans les deux sens.

## A1 — Conception avec l'utilisateur
- [ ] Maquettes de l'atelier : 3 ou 4 dispositions de la page en images (`outils_docs/atelier_ecrans/`, comme
  `outils_docs/ecran_debits_7B/`), choix de l'utilisateur
- [ ] Questions tranchées : contenu de la description (objets gérés au premier palier), forme des remarques (objet,
  zone, page ; états), aperçu (navigateur seul, ou capture de la carte si la skill en a trouvé une), question ouverte
  du Contexte (LVGL de l'écran des débits)
- [ ] Spec `docs/superpowers/specs/2026-11-11-atelier-ecrans-design.md` validée par l'utilisateur ; actions A2 à A10
  détaillées (fichiers, interfaces, tests) d'après elle

## A2 — Catalogue commun (objets, attributs, polices, écrans)
- [ ] `outils_docs/schemas/catalogue_ecran.json` et son script d'extraction depuis `lib/libesp32_lvgl/` (classes
  `lvh_*` de `lv_haspmota.be`, polices compilées et leurs tailles, gardes du firmware) ; banc qui compare le catalogue
  aux sources (témoin rouge sur une police retirée)
- [ ] Skill `lvgl-haspmota` : ses références renvoient au catalogue (source unique) et décrivent l'atelier

## A3 — Description neutre de l'écran
- [ ] Format `ecran.json` et validateur Python (refus : objet hors écran, police absente du catalogue, liaison vers
  une valeur inconnue du modèle d'écran, identifiant en double) ; banc à mutants
- [ ] Premier cas : description de l'écran des débits, équivalente au `pages.jsonl` actuel (pages A, D, Réglages)

## A4 — Générateur HASPmota
- [ ] Description → `pages.jsonl` ; banc : la description des débits redonne le `pages.jsonl` du dépôt (écart nul ou
  listé et justifié) ; `banc_ecran_debits.py` VERT sur le fichier généré

## A5 — Générateur LVGL pur
- [ ] Description → `ecranLvgl.be` (API d'interface de `ecranDebitsFonctions.be`) ; compilé par `verifie_berry.py`,
  banc Berry à objets LVGL simulés ; `banc_demarrage` de la variante `lvgl` VERT

## A6 — Page web de l'atelier (port 7960)
- [ ] Serveur et page : canevas à la taille de l'écran, palette du catalogue, glisser-déposer, redimensionnement,
  propriétés, pages, polices du firmware seules ; sonde Chrome hermétique
- [ ] Tuile de l'annuaire (groupe Maintenance), tâche VS Code, cible Custom détachée, `acces_web.py` (jeton hors PC)

## A7 — Remarques épinglées
- [ ] Remarque sur un objet, une zone ou une page, gardée dans un fichier près de la description, avec état (ouverte,
  traitée) ; lue et traitée par Claude avec la skill `lvgl-haspmota` ; banc

## A8 — Écriture dans le dépôt et envoi
- [ ] Diff puis écriture atomique (description + fichiers générés de l'interface choisie), empreinte périmée refusée,
  refus pendant un build ; lien vers la page Build pour l'envoi (FS ou fichiers choisis)

## A9 — Ressources sous `/sd`
- [ ] Liste des ressources utiles (fonds, icônes, polices ajoutées) proposée à l'utilisateur, choix fait ; règle de
  rangement des images dans `data/fs/gestionFileFolder.be::listeEtRepartitLesFichiers` (accord pour `data/fs`)

## A10 — Documentation, relecture, essai réel
- [ ] `outils_docs/README.md` (mode d'emploi), carte des documents du `CLAUDE.md`, `verifie_references_docs.py` 0 défaut
- [ ] `relecteur-pages-web` et `relecteur-berry` sur le chantier ; corrections confirmées faites
- [ ] Essai avec l'utilisateur : un bouton ajouté à l'écran des débits par l'atelier, généré dans les deux interfaces,
  envoyé par la page Build, vu et touché sur la carte
- [ ] Retour au plan `debits-deux-cartes` : cocher son action A9 avec la preuve, passer ce plan en `statut: clos`

## Améliorations restantes
- [ ] [projet] Écrans des autres cartes (ILI9488 SPI, petits OLED) ajoutés au catalogue
- [ ] [projet] Reprise d'un `pages.jsonl` existant écrit à la main (import vers la description)

## Vérification
Bancs du catalogue, de la description et des deux générateurs VERT avec témoins rouges lus ; sonde Chrome de la page ;
essai réel de A10 sur la carte d'affichage des débits. Un banc PC ne prouve pas le rendu : seul l'écran fait foi.
