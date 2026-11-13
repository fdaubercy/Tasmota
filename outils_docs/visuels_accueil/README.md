# Atelier des visuels d'accueil : essai de vectorisation (A0, 2026-11-13)

Photo d'essai : une facade de brique avec voiture, poteau et porte (IMG_0274, hors depot, c'est une photo du domicile).
Bibliotheque : ImageTracer.js 1.2.6 (`lib/LISEZMOI.md`). Image reduite a 480 x 360, calcul dans Chrome.

| Rendu | Reglages | SVG brut | gzip | Chemins | Temps |
|---|---|---|---|---|---|
| Aplats 8 couleurs, brut | sans lissage | 547 Ko | 108 Ko | 2103 | 1,6 s |
| Aplats 16 couleurs, brut | sans lissage | 843 Ko | 145 Ko | 3848 | 1,5 s |
| Trait, brut | Sobel seuil 70 | 690 Ko | 125 Ko | 2863 | 1,5 s |
| A : aplats 8 couleurs lisses | lissage 120 px, taches < 40 | 74 Ko | 22 Ko | 138 | 0,9 s |
| B : aplats 12 couleurs lisses | lissage 160 px, taches < 30 | 152 Ko | 40 Ko | 415 | 1,0 s |
| C : trait lisse | lissage 160 px, seuil 90 | 65 Ko | 19 Ko | 117 | 1,0 s |
| D : aplats 6 couleurs tres lisses | lissage 96 px, taches < 60 | 58 Ko | 17 Ko | 108 | 1,1 s |

Constats : sans lissage prealable, une facade de brique donne un SVG inutilisable (plus de 500 Ko). Avec une reduction
a 96-160 px avant tracage, le poids tombe a 58-74 Ko et le dessin reste reconnaissable. La carte sert le SVG brut (pas de
`Content-Encoding`), donc ce sont les poids bruts qui comptent : D passe sous le seuil ESP32 de 60 Ko, A le depasse.
Le lissage et la taille des taches sont donc des reglages de la page, avec le poids affiche en direct.

Decision (2026-11-13) : **voie 1, tout dans le navigateur, retenue**. L'utilisateur l'avait choisie avant l'essai et ne l'a pas
remise en cause apres ; il a ensuite demande un rendu a plat comme la maquette PNG de la facade du rez-de-chaussee (formes
unies, motifs briques et tuiles), donc un editeur de formes dans la page et non un trace automatique. vtracer n'est plus
necessaire ; ImageTracer ne sert qu'a l'aide facultative « pre-remplir » (6 couleurs, lissage 96 px).

## Recherche d'icones en ligne (2026-11-13)

Module `outils_docs/scripts_python/outils_pc/atelier_visuels_icones_web.py` (banc `test_atelier_visuels_icones_web.py`,
42 controles, faux `ouvre`, aucun reseau). API Iconify, hote fixe `https://api.iconify.design`, sans cle.

Format lu dans la documentation (iconify.design/docs/api/) puis confirme par un essai reel :

- `GET /search?query=<texte>&limit=<32..999>` : `{"icons": ["jeu:nom", ...], "total", "limit", "start", "collections":
  {"<jeu>": {"name", "author": {"name","url"}, "license": {"title","spdx","url"}, ...}}}`. Une seule requete donne donc la
  licence de chaque jeu rencontre. `query` absent = HTTP 400.
- `GET /collections?prefix=<jeu>` : `{"<jeu>": {...meme bloc...}}` (jeu inconnu : objet vide).
- `GET /<jeu>/<nom>.svg` : le SVG (`width="1em" height="1em"`, `fill="currentColor"`). Parametres facultatifs (`color`, `width`,
  `flip`...) non utilises : aucun parametre libre n'est envoye.
- Limites publiques : annoncees sans chiffres (« limits to prevent abuse »). Parade : cache fichier de 30 jours
  (`%LOCALAPPDATA%\outils_tasmota\atelier_visuels\icones\`), delai 6 s, reponse limitee a 64 Ko, aucune redirection suivie.

Regles du module : `jeu` et `nom` en `^[a-z0-9-]+$` (64 caracteres au plus), recherche de 1 a 40 caracteres (lettres, chiffres,
tiret, espace), valides AVANT toute requete. Licences par SPDX : MIT, Apache-2.0, ISC, CC0-1.0, Unlicense = permissives ;
CC-BY-* (hors NC, ND, SA) = attribution, `garde(..., confirme_attribution=True)` obligatoire ; le reste est masque de la
recherche et refuse par `svg()`. `garde()` ecrit `icones/<jeu>-<nom>.svg` (jamais d'ecrasement) et ajoute une ligne a
`icones/LICENCES.md`. Hors ligne : exception `HorsLigne` au message clair.

Essai reel (2026-11-13) : recherche « camera » = 47 icones sur 48 (11 jeux : mdi, material-symbols, tabler, ic, solar...,
une licence non permise ecartee) ; `svg("mdi","camera")` = 325 octets nettoyes, Apache-2.0, auteur Pictogrammers.

Non verifie : le plafond de debit de l'API publique (aucun chiffre publie), le comportement exact de l'erreur 404 d'une icone
inconnue (non documente ; le module la traite comme SVG inexploitable, `HorsLigne`), la fiabilite du champ `spdx` pour les
jeux a licence double. Les routes HTTP `GET /icones/recherche` et `/icones/svg` sont a brancher par l'integration.
