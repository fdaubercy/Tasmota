# Consignes de création des visuels d'accueil (tous lieux, toutes cartes)

Notes du 2026-11-15, tirées de la maquette du garage et du portail de jardin (propositions A et B, comparées avec une scène
produite par Gemini). À relire avant de dessiner la façade d'un autre lieu. Maquettes : `outils_docs/volets_visuels/garage_propositions.html`
(page de comparaison), `maquette_garage_a.html` (notre façade + finition), `maquette_garage_b.html` (scène de Gemini + nos organes).

## 1. Qui fait quoi

- **Le fond statique** (mur, toit, végétation, sol, ciel) peut venir de Gemini ou de n'importe quel générateur de SVG, à partir d'une photo.
- **Les organes** (ouvrant, voyant, lampe, caméra, capteur) sont toujours codés par nous : ils doivent suivre l'état réel de la carte. Les animations CSS
  d'un SVG de Gemini (interrupteur `.is-open`) ne lisent aucune carte : ne pas les garder.
- Un SVG de Gemini est un bloc unique : avant de l'utiliser, retirer portes animées, badges d'état, boutons et feuille Tailwind ; garder le décor
  statique, regroupé par `id` (calques).

## 2. Ce qui rend le rendu de Gemini meilleur (à reprendre)

- Un dégradé par matière (mur, panneaux, piliers, ciel), jamais d'aplat.
- Une ombre portée douce (`feDropShadow`, décalage 3 à 6, flou 3 à 6, opacité 0,3) sous le bâtiment et sous les éléments de premier plan.
- Un arrière-plan : forêt d'automne (troncs sombres, touffes ocre, olive, doré à 0,5 à 0,9 d'opacité) derrière le toit.
- Des motifs en `pattern` (treillis noir en losange, treillis bois carré), des feuillages tirés au sort avec une graine fixe (même image à chaque ouverture),
  des détails d'échelle (lames, caissons, joints de pierre).
- Un mur un peu plus sombre vers le bas (dégradé `#fff` transparent vers `#5a4a30` à 0,22).
- Poids : tout en vectoriel, sans image intégrée, de l'ordre de 25 Ko. Limite de l'atelier : 150 Ko.

## 3. Ordre des calques (du fond vers l'avant)

1. ciel (dégradé jour ; la nuit est un calque à part, pas un second ciel)
2. forêt ou arrière-plan
3. clôture ou palissade, mur voisin
4. bâtiment (ombre portée), bandeau de toit, treillis, plantes grimpantes
5. grande porte (cadre, intérieur sombre, tablier ou rideau clippé, fins de course)
6. petite porte
7. pergola, treillis bois, buisson
8. sol (allée)
9. calque nuit (rectangle sombre, opacité 0,5 à 0,55)
10. cônes de couverture (caméra, lampe), sous les organes
11. organes éclairables : caméra, lampe (au-dessus de la nuit, pour rester vifs)
12. premier plan : piliers, vantaux du portail, feu orange, capteur de fermeture (avec ombre portée) : au-dessus de la nuit, assombris par le même calque si on les place avant lui

Dans la maquette B, le premier plan est rangé **avant** le calque nuit, pour que le portail s'assombrisse aussi ; cônes et organes viennent après.

## 4. Les organes et leurs règles (décisions de l'utilisateur)

| Organe | Règle |
|---|---|
| Grande porte du garage | C'est un **rideau à lames**, pas une porte sectionnelle (ne pas copier la porte de Gemini). Tablier clippé qui monte, barre finale foncée. Deux fins de course sur le rail droit : « ouverture » en haut, « fermeture » en bas. **Vert = contact fermé**, rouge = contact ouvert. Fermé : fermeture verte, ouverture rouge. Clignote si l'état lu contredit la position plus de 6 s. |
| Petite porte | **Fixe**, jamais motorisée, jamais animée, aucun clic. Cadre blanc, vitrage sombre avec reflet, soubassement, poignée. |
| Portail de jardin | Un ou deux vantaux motorisés, **un moteur par vantail**. Deux boutons : « simple » (vantail droit seul), « double » (droit, puis gauche après le décalage, 3 s par défaut). Appui pendant le mouvement = arrêt, appui suivant = reprise. Ouvert ou partiellement ouvert et à l'arrêt : un appui ferme, le gauche d'abord après le décalage. Durée d'ouverture d'un vantail 15 s. |
| Capteur de fermeture | Anneau et point au joint central, texte « fermé ✔ » vert quand les deux vantaux sont fermés, « ouvert » orange sinon. |
| Feu orange | Sur le flanc du pilier droit, un peu sous le sommet. **Clignote pendant tout mouvement** (1 s allumé, 1 s éteint), dans les deux sens. Dessin seul : aucun relais du serveur de garage ne le commande. |
| Lampe du garage | **La nôtre** (pas celle de Gemini) : lanterne suspendue par une tige sous le toit, côté pergola ; globe gris éteint, jaune `#ffd54a` et halo allumé. |
| Caméra | Boîtier blanc sous le toit, côté treillis gauche, objectif noir, voyant gris éteint, **vert allumé**. |
| Cônes de couverture | Un cône par appareil allumé (caméra bleu `#38bdf8`, lampe jaune `#fde047`), dégradé vertical opaque vers transparent, **plus large qu'avant** : environ 700 de large pour la caméra et 660 pour la lampe sur une scène de 1200. Pas de cône éteint. Fondu 0,5 s. |

## 5. Commande par clic (proposé, pas encore réalisé)

- Caméra et lampe : déjà cliquables dans `volets.js` (confirmation puis `POST /volets` action `camera` ou `lampe`).
- Rideau : un clic envoie l'appui `toggle` ; le sens est décidé par la carte.
- Portail : clic sur le vantail droit = « simple », clic sur le vantail gauche = « double » ; clic en mouvement = arrêt.
- Petite porte : aucun clic.
- Toujours une confirmation indiquant ce qui va bouger (portail = sécurité physique), refus si l'état est inconnu ou la carte muette.

## 6. Jour et nuit automatiques (demande du 2026-11-15, pas encore réalisé)

- Source : la carte, pas l'horloge du navigateur. Le persist porte `localisation` (latitude, longitude) et `fuseauHoraire` (heure d'été et d'hiver) ;
  Tasmota calcule lever et coucher du soleil avec ces valeurs (à confirmer sur la carte par `Status 7`, `Sunrise`, `Sunset`).
- Fondu progressif de 30 à 40 minutes autour du coucher et du lever. Bouton Jour, Nuit, Auto pour l'essai.
- Sans réponse de la carte : repli sur l'heure du navigateur, signalé à l'écran.
- La nuit n'allume pas la lampe : elle reste commandée à la main.

## 7. Paramètres propres à un lieu (à relever pour chaque nouvelle façade)

1. Photo de référence du lieu et cadrage (frontal, trois quarts).
2. Forme du toit (appentis ou deux pans), position du bandeau.
3. Ouvrants : type (rideau, porte sectionnelle, battant, trappe), motorisés ou non, nombre de vantaux, capteurs (fins de course, fermeture).
4. Où se trouvent la caméra et la lampe (côté, hauteur sous le toit) et leurs relais.
5. Décor : treillis, plantes, pergola, clôture, végétation voisine, saison de la photo.
6. Position géographique et fuseau (déjà au persist).
7. Quels organes sont **décoratifs seulement** (petite porte, fenêtres).

## 8. Coordonnées utiles de la scène de Gemini (viewBox 1200 x 900)

- Bâtiment : `128,180 945,252 945,665 128,665` ; bandeau de toit `122,170 952,244 952,256 122,183`.
- Ouverture de la grande porte : x 225 à 645, y 388 à 653 ; cadre 220,382, 430 x 273.
- Petite porte : cadre 680,382, 136 x 273.
- Treillis noir : 142,385, 70 x 275 ; treillis bois : 832,365, 95 x 295.
- Piliers : gauche x 0 à 96, droit x 1094 à 1200, haut à y 565, base à 900 ; vantaux de y 650 à 895, joint central x 595.
- Caméra : environ (258, 205 à 236) ; lampe : sous le toit vers x = 800, y = 252 à 302 ; cônes à 820 de profondeur.

Façade du dépôt (`volets.js`, viewBox 540 x 320) : caméra vers (29, 52), lampe vers (382, 78), sol à y = 196, mur de x = 33 à 399.

## 9. Gemini ou nous

- **Gemini** : fond statique d'un nouveau lieu à partir d'une photo, quand le dessin à la main serait long. L'envoi d'une photo à un service externe se fait
  avec avertissement et accord (voir `FOURNISSEURS_IA.md`).
- **Nous** (`volets.js`, atelier des visuels) : tout ce qui bouge ou lit un état. C'est la décision du 2026-11-15 (proposition A recommandée).

## 10. Statut de ce document et lien avec la page de l'atelier

- Ce fichier est la **référence unique** des consignes de création d'un visuel d'accueil (tous lieux, toutes cartes). Il ne se limite pas au garage.
- La page de l'atelier des visuels (http://127.0.0.1:7985, `atelier_visuels_*.py`) doit **s'y référer** : lien vers ce fichier et rappel des
  règles qui concernent l'élément en cours d'édition (à réaliser, pas encore fait).
- Les consignes **s'affinent au fil du temps** : ajouter chaque nouvelle règle ici, avec sa date et sa raison, dans le journal ci-dessous, sans
  supprimer les anciennes (barrer ou marquer « remplacée par »).

### Journal des affinements

- 2026-11-15 : création d'après le garage et le portail de jardin (sections 1 à 9). Décisions : nuit selon le lever et le coucher réels du soleil
  (persist : localisation et fuseau) ; portail avec deux zones de clic distinctes (vantail droit = ouvrir un vantail, vantail gauche = ouvrir les deux) ;
  l'arrêt du portail par clic se fait sans confirmation, toute ouverture ou fermeture demande une confirmation.
- 2026-11-15 (soir) : affinements demandes par l'utilisateur sur le garage, le rideau et le grenier du RDC. Nuit plus sombre et unique pour toutes les
  cartes, en dur dans `volets.js` (constantes `NUIT` : base 0,5, profonde 0,4, teinte du crepuscule ; voile maximal 0,9) et non dans un persist, pour que le
  reglage reste identique partout. Cones de la camera et de la lampe elargis et descendus jusqu'au sol, camera de la maison comprise. Aucun pourcentage
  d'ouverture sur l'image. Portail a deux vantaux : le vantail droit part 5 s avant le gauche (`PORTAIL_DECALAGE`), le capteur de fermeture suit le vantail
  gauche. Rideau : garage et petite porte seuls, sans pergola du mur. Grenier du RDC : decor `maison` avec `finition` pour la nuit seulement.
