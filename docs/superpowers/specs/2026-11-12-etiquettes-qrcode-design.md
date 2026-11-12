# Étiquettes QR code des cartes (page 7970) : conception

Date : 2026-11-12. Statut : en attente de validation par l'utilisateur.

## 1. Intention

Devant un module installé, l'utilisateur veut retrouver son identité (au minimum le hostname et l'adresse IP) en
scannant une étiquette avec son téléphone. Le téléphone **affiche du texte** : le QR code ne contient pas de lien à
ouvrir.

Le même QR code doit pouvoir s'afficher sur une page de la carte elle-même : depuis le PC, on est sur la page de la
carte et on veut faire passer ses informations au téléphone.

Les cartes qui ont un écran tactile peuvent aussi l'afficher en surimpression sur appui d'un bouton.

## 2. Objectifs

1. Une page web de l'annuaire, « Étiquettes QR code », port **7970**, qui compose le QR code de chaque env personnel.
2. Le contenu est choisi par l'utilisateur : champs standards tirés du dépôt et champs **choisis dans le persist de la
   carte** (arbre de clés), chacun avec son libellé ; ordre des lignes réglable ; une ligne libre facultative.
3. La présentation du texte se règle : libellés, ordre, sauts de ligne, séparateur. C'est du texte brut : ni gras ni
   couleur dans ce que lit le téléphone.
4. Le dessin du QR code se règle : forme des points, forme des trois coins de repérage, couleurs, image au centre.
5. Un **gabarit commun** (champs, ordre, style, image) sert de point de départ à toutes les cartes ; chaque carte peut le
   surcharger.
6. La taille d'impression se règle (en mm). Un **verdict de lisibilité** (lisible, limite, trop dense) tient compte du
   nombre de caractères, de la taille imprimée et de la présence d'une image au centre (qui impose la correction
   d'erreur H). Le compteur de caractères est affiché en permanence.
7. Une fenêtre d'aperçu montre le QR code dessiné et, à côté, le texte exact que le téléphone affichera.
8. Impression par un bouton qui ouvre la fenêtre d'impression du navigateur (choix de l'imprimante, copies). La page
   imprimée respecte la taille en mm à l'échelle 100 %.
9. **Planche A4** : cocher plusieurs cartes et imprimer tous leurs QR codes sur une feuille, avec traits de coupe fins et,
   en option, un petit nom sous chaque code (pour ne pas coller la mauvaise étiquette).
10. **Export** PNG et SVG d'un QR code.
11. **Page de la carte** : un bouton sur l'accueil ouvre `/qrcode`, qui affiche exactement le QR code réglé dans l'outil
    (même texte, même style). Si l'IP réelle de la carte diffère de celle inscrite, une ligne d'avertissement s'affiche
    sous le code.
12. **Suivi des changements**, deux états par carte :
    - « étiquette à réimprimer » : le texte recalculé diffère du texte noté lors de la dernière impression ;
    - « carte à mettre à jour » : le fichier présent sur la carte diffère de celui du dépôt.
13. **Écran des cartes** : un bouton à l'écran affiche le QR code en surimpression pendant un délai réglable, puis il
    disparaît.

## 3. Non-objectifs

- Pas de lien cliquable dans le QR code (décision de l'utilisateur : affichage du texte).
- Pas de texte lisible à l'œil sur l'étiquette elle-même, hors l'option « petit nom » de la planche.
- Pas de choix d'imprimante dans la page ni d'impression sans fenêtre : la fenêtre du navigateur suffit.
- Pas de surveillance permanente des fichiers ni de bascule automatique vers la page QR.
- Pas de QR code « connexion Wi-Fi » du point d'accès : il mettrait le mot de passe en clair sur une étiquette.

## 4. Anti-objectifs (ce qui ferait échouer le projet même s'il marche)

- Un secret (mot de passe, clé, jeton) qui apparaît dans la page, dans un QR code, dans un fichier écrit ou dans une
  réponse HTTP. Les clés sensibles du persist ne sont **jamais proposées** dans l'arbre et leurs valeurs ne quittent pas
  le serveur (même règle que l'assistant persist, filtre au minimum `pass|pwd|mdp|key|token`, insensible à la casse).
- Une étiquette imprimée qu'un téléphone ne lit pas alors que la page l'annonçait « lisible ».
- Un QR code de la carte différent de celui de l'outil.
- Une impression qui modifie le FS de la carte (et la ferait passer « à mettre à jour » pour rien).

## 5. Contraintes du dépôt

- Outil PC dans `outils_docs/scripts_python/outils_pc/`, sur le modèle des autres pages (`acces_web.py`, tuile de
  l'annuaire groupe Maintenance, tâche VS Code, cible Custom détachée `build/cible_*.py` avec `NOM_CIBLE` ajouté à
  `CIBLES_OUTILS` de `.claude/hooks/garde_build.py`, `lieu=True` dans le registre, listes classées par lieu par
  `lieux.py::remplitParLieu`). Rien n'est écrit au dépôt sans geste explicite ; écriture refusée pendant un build ;
  écriture atomique avec empreinte, comme l'atelier des graphiques.
- Pages de carte : gabarit `data/sd/html`, CSS `data/sd/css`, JS `data/sd/js` ; bibliothèque tierce compressée en `.gz`
  et décompressée par la page, comme `echarts.min.js.gz`. Fichiers propres à la page **exclus des envs qui ne s'en
  servent pas** (liste de `[berry_commun]` dans le `custom_files_exclude` des autres envs).
- Berry : charte des logs (`logFonctions.log`), un module solidifié s'ajoute au `custom_berry_solidify` de chaque env
  concerné et à `globs` de `solidify_all_python.be`.
- `data/<lieu>/<carte>/` part en flash : seuls les fichiers utiles à la carte y vont.
- Fichiers de plus de 500 lignes : à éviter, découper par module comme les autres outils.
- Le persist et `user_config_override.h` se lisent par le serveur en masquant les secrets.

## 6. Ce qui a été décidé avec l'utilisateur

| Sujet | Décision |
|---|---|
| Contenu scanné | Texte affiché, pas de lien |
| Support | Feuille A4 ordinaire, découpée aux ciseaux, collée sur le boîtier |
| Étiquette | QR code seul ; petit nom en option sur la planche |
| Mise en forme | Celle des lignes lues par le téléphone, et le dessin du QR code (points, coins, image, couleurs) |
| Taille | Réglable dans la page |
| Impression | Bouton, fenêtre d'impression du navigateur |
| Page de la carte | Affiche exactement le QR code de l'outil |
| Suivi | Deux états : étiquette à réimprimer, carte à mettre à jour |
| Idées retenues | Planche A4, petit nom, gabarit commun, champs choisis dans le persist, export PNG/SVG, QR à l'écran par bouton pendant un délai |

## 7. Conception proposée

### 7.1 Fichiers

| Fichier | Rôle | Va sur la carte |
|---|---|---|
| `outils_docs/etiquettes_qr/gabarit.json` | Gabarit commun : champs, ordre, libellés, séparateur, style, taille | non |
| `outils_docs/etiquettes_qr/cartes/<env>.json` | Surcharges de la carte (ce qui diffère du gabarit) | non |
| `outils_docs/etiquettes_qr/impressions.json` | Par env : texte imprimé, date, taille | non |
| `outils_docs/etiquettes_qr/images/` | Images de centre disponibles | non |
| `data/<lieu>/<carte>/qrcode.json` | Fichier **généré** : texte résolu, style, image en data URI | oui |

Ce découpage reprend celui de l'atelier des écrans (`outils_docs/atelier_ecrans/cartes/<env>/ecran.json` comme
source, fichiers générés dans `data/<lieu>/<carte>/`). Le fichier de carte contient le texte **déjà résolu** : la carte
n'a rien à calculer et affiche exactement ce que l'outil a dessiné. Le suivi des impressions vit hors du dossier de la
carte, pour qu'imprimer ne touche pas son FS.

Le gabarit contient des champs par référence, pas des valeurs. Exemple de forme (indicative, à figer par le
constructeur) :

```json
{
  "lignes": [
    {"libelle": "Hostname", "source": "standard", "cle": "hostname"},
    {"libelle": "IP", "source": "standard", "cle": "ip"},
    {"libelle": "ModBus id", "source": "persist", "chemin": "drivers.ModBus.id"},
    {"libelle": "", "source": "libre", "texte": "Tableau du garage"}
  ],
  "separateur": " : ",
  "style": {"points": "rounded", "coins": "extra-rounded", "couleur": "#000000", "fond": "#ffffff", "image": "maison.png"},
  "taille_mm": 25
}
```

### 7.2 Champs standards

Lus dans le dépôt par le serveur, sans interroger la carte : hostname et topic (persist), IP (`WIFI_IP_ADDRESS` du
`.h`, ou `<ipMaître>:<port>` pour un esclave du range extender, comme `build_envs.py::adresse_par_maitre`), nom de l'env,
puce et lieu (`lieux.py`). Un champ dont la valeur est introuvable est signalé « introuvable » dans la page et n'est
pas écrit vide dans le QR code.

### 7.3 Champs du persist

Arbre des clés du `_persist.json` de la carte, construit par le serveur. Clés sensibles absentes de l'arbre. Seules les
valeurs scalaires (texte, nombre, booléen) sont sélectionnables. Le chemin choisi est enregistré ; si la clé disparaît
plus tard, le champ passe « introuvable ».

### 7.4 Dessin et lisibilité

Une même bibliothèque JavaScript de QR code stylé sert à la page de l'outil et à la page de la carte, pour un rendu
identique. Choix proposé : `qr-code-styling` (licence MIT : points, coins, couleurs, image au centre, export PNG/SVG),
version épinglée, copiée localement (pas de CDN) et compressée en `.gz` pour la carte. Le constructeur peut retenir une
autre bibliothèque si elle couvre les mêmes besoins.

Verdict de lisibilité : taille d'un module (carré élémentaire) = taille imprimée / (nombre de modules + marge
blanche). Seuils proposés, à confirmer par un essai réel d'impression et de scan : au moins 0,5 mm lisible, entre 0,35
et 0,5 mm limite, en dessous trop dense. Image au centre : correction H imposée. Sans image : correction M par défaut.

### 7.5 Page de l'outil (7970)

- En-tête : liste déroulante des envs (classés par lieu) pour changer de carte sans quitter la page, et bouton de
  bascule Sombre / Clair (choix mémorisé dans le navigateur). Changer d'env avec des modifications non écrites demande
  confirmation.
- Liste des envs personnels classés par lieu, avec les badges « étiquette à réimprimer », « fichier à régénérer »,
  « carte à mettre à jour », et une case par carte pour la planche.
- Panneau d'une carte : lignes (ajout depuis les champs standards, l'arbre du persist ou une ligne libre ; ordre par
  glisser ou flèches ; libellé), style, taille, aperçu (QR code + texte lu + compteur + verdict).
- Boutons : « Écrire dans le dépôt » (diff puis écriture du fichier de carte et des surcharges), « Imprimer », « Planche »,
  « PNG », « SVG », « Téléverser » (ouvre la page Build sur l'onglet Fichiers avec `?env=&depuis=qrcode&fichiers=`, sur
  le modèle de `build_page_atelier.py`).
- Gabarit commun modifiable dans un onglet à part.
- `?env=` à l'arrivée sélectionne la carte (lien depuis les autres outils).

### 7.6 Suivi des changements

Calcul à l'ouverture de la page et à la sélection d'une carte, jamais en tâche de fond :

- **à réimprimer** : texte recalculé différent du texte de `impressions.json` (impression notée au clic sur
  « Imprimer » ou « Planche », la page ne sachant pas si l'impression a réussi ; l'utilisateur peut annuler la note) ;
- **à régénérer** : `data/<lieu>/<carte>/qrcode.json` différent de ce que produirait le réglage actuel ;
- **carte à mettre à jour** : `/json/qrcode.json` lu sur la carte (HTTP, adresse par le maître pour un esclave du range
  extender) différent du fichier du dépôt. Lu à la sélection de la carte seulement ; carte hors ligne : état « inconnu ».

Seuls les champs utilisés par la carte entrent dans la comparaison.

Après une écriture d'identité, le message de fin de « Fichiers Berry » (renommage d'env) et de l'assistant persist
(modification) ajoute un lien « Étiquette QR à refaire » vers `http://127.0.0.1:7970/?env=<env>` si la carte a un
réglage QR.

### 7.7 Page de la carte

Route `/qrcode` servie par un petit module Berry (bouton d'accueil, sur le modèle de `/graphiques` ou `/cuve`), gabarit
`data/sd/html/qrcode.html`, script `data/sd/js/qrcode.js`, bibliothèque `.gz`. La page lit `/json/qrcode.json`, dessine
le code et compare l'IP inscrite à l'IP réelle fournie par la route (ligne d'avertissement si elles diffèrent). Fichiers
embarqués seulement sur les cartes qui ont un `qrcode.json` (liste `etiquette_qr` de `[berry_commun]`, voir §7.9).

### 7.8 Écran des cartes

HASPmota dessine un QR code nativement (`"obj":"qrcode"`, `qr_text`, `qr_size` : démo amont
`tasmota/berry/haspmota_src/haspmota_demo/pages.jsonl`) ; LVGL a `lv.qrcode`. Le QR code à l'écran devient un élément du
catalogue de l'atelier des écrans (plan `tasks/plans/atelier-ecrans.md`) : un bouton qui l'affiche en surimpression pendant
un délai réglable, texte lu dans `/json/qrcode.json`. Le style riche (image, coins) n'est pas reproduit à l'écran :
QR code standard noir sur blanc. **Dernière phase, dépend de l'avancement de l'atelier des écrans.**

### 7.9 Choix faits par Claude après la relecture (à contester par l'utilisateur)

1. **Cartes concernées.** L'étiquette papier vaut pour tous les envs personnels, ESP8266 compris. La page `/qrcode`
   n'existe que sur les cartes Berry (famille ESP32) dont le réglage coche « Page sur la carte » ; elles seules
   reçoivent `qrcode.json` et les fichiers de la liste `etiquette_qr`. Un ESP8266 n'a ni Berry ni la case.
2. **Module Berry solidifié**, comme les autres pages (`graphiquesFonctions`, `cuvePageFonctions`, `energieFonctions`) :
   ajouté à `custom_berry_solidify` des envs qui ont la page, firmware à recompiler une fois par la page Build. Il ne
   charge rien tant que `/qrcode.json` est absent.
3. **IP absente du dépôt** (`WIFI_IP_ADDRESS` à 0.0.0.0 sans maître résoluble) : la ligne est omise, la page affiche un
   avertissement orange, l'écriture et l'impression restent permises. La règle vaut pour tout champ introuvable.
4. **Fusion gabarit / carte.** La surcharge d'une carte remplace une section entière (`lignes`, `separateur`) ; pour
   `style`, clé par clé. Un changement du gabarit se répercute sur les cartes qui ne surchargent pas la section
   touchée, qui passent « à régénérer » par le calcul normal du §7.6.
5. **Planche A4** : une seule taille pour toute la planche, choisie dans la fenêtre de la planche (par défaut celle du
   gabarit) ; grille automatique, autant de pages que nécessaire.
6. **Secrets filtrés par clé et par valeur.** L'arbre exclut les clés sensibles et aussi toute valeur qui contient la
   valeur d'une clé sensible du même persist (URL avec jeton, chaîne composée). Contrôle repris à l'écriture du fichier
   de carte. Le banc a des mutants pour les deux filtres.
7. **`impressions.json`** ne garde qu'une empreinte (SHA-256) du texte imprimé, la date et la taille : pas de copie en
   clair dans le dépôt.

## 8. Laissé au constructeur

- Forme exacte des JSON, noms des modules Python et Berry.
- Bibliothèque de QR code (critères du §7.4), version épinglée.
- Disposition de la page (maquettes à proposer à l'utilisateur avant d'écrire la page, comme pour les autres outils).
- Taille maximale de l'image de centre (proposée : 8 Ko en data URI).
- Bancs : un banc Python par module, mutants pour le filtre des secrets, sonde Chrome de la page de l'outil et de la page
  de la carte, banc Berry de la route.

## 9. Ordre de réalisation proposé

1. Maquettes de la page 7970 (choix de l'utilisateur).
2. Modèle de données, champs standards, arbre du persist sans secrets (bancs).
3. Page 7970 : édition, aperçu, verdict, écriture au dépôt.
4. Impression unitaire, planche A4, export PNG/SVG ; essai réel d'impression et de scan pour caler les seuils.
5. Page `/qrcode` de la carte et téléversement par la page Build ; essai sur une carte.
6. Suivi des changements et liens depuis les autres outils.
7. QR code à l'écran (après l'atelier des écrans).
8. Documentation (`outils_docs/README.md`, carte des documents du `CLAUDE.md`).
