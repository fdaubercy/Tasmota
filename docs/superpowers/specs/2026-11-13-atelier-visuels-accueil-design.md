# Atelier des visuels d'accueil (page 7990) : conception

Date : 2026-11-13. Statut : validé par l'utilisateur le 2026-11-13 (« OK on y va »). Restent ouverts : la photo de
l'essai du palier 1 (à fournir), l'accord explicite pour la règle de rangement du § 6.4 (repli : fond lu à la racine).

## 1. Intention

L'utilisateur veut que la page d'accueil d'un module Tasmota montre son installation telle qu'elle est : une image du
tableau, de la cuve, du volet, sur laquelle on voit vivre l'état des relais et des entrées, les mesures des capteurs et
l'activité des liaisons (ModBus série, UDP, Wi-Fi, range extender). Aujourd'hui seule la façade des volets fait cela,
et c'est un dessin SVG écrit à la main dans `data/sd/js/volets.js`.

Le point de départ est une **photo réelle**. Une page de l'annuaire la transforme, au choix de l'utilisateur, soit en
**photo recadrée et allégée**, soit en **dessin dérivé** (vectorisation en aplats de couleurs, ou tracé au trait), puis
laisse poser dessus des **points chauds** reliés aux états de la carte. Le résultat part sur la carte par la page Build.

Pourquoi un dessin plutôt que la photo : l'utilisateur veut les deux, dans la même page, et choisit par carte. Le
dessin donne un style homogène avec la façade des volets, pèse moins, et ne montre pas le local tel quel.

## 2. Objectifs

1. Une page web de l'annuaire, « Atelier des visuels », port **7990**, groupe Maintenance, arrêt libre : rien n'est
   écrit avant « Écrire dans le dépôt ». Disposition A (trois colonnes) retenue par l'utilisateur le 2026-11-13, avec un
   **bouton Sombre / Clair** comme les autres pages de l'annuaire (variables CSS, mémorisé, défaut = réglage du système).
2. On choisit une carte du parc (par lieu, comme les autres pages), on dépose une photo depuis le PC, on la recadre.
   Le **recadrage** fixe le sujet : pour la maison du rez-de-chaussée, la photo a été coupée au bord haut du toit noir (rien au
   dessus : ni mur gris, ni parabole). Le rectangle de recadrage mémorise sa position et son rapport hauteur/largeur par
   carte, pour reprendre une photo plus récente du même sujet sans le retracer.
3. **Deux modes de fond**, au choix par un sélecteur :
   - *photo* : la photo recadrée, réduite à la largeur de la page d'accueil, compressée (WebP, repli JPEG) ;
   - *dessin* : un **dessin à plat** dans le style de la façade des volets (formes géométriques unies, quelques
     couleurs, contours blancs pour les ouvertures), construit dans l'outil. **Changement du 2026-11-13** : l'essai A0
     a montré qu'un tracé automatique (ImageTracer) donne des taches organiques, pas ce rendu ; l'utilisateur veut le
     rendu à plat de la façade du garage. L'utilisateur pose des rectangles et polygones par-dessus la photo
     (affichée en transparence) ; chaque forme prend d'office la **couleur médiane de la zone de photo qu'elle
     recouvre** (modifiable), avec en option un contour. Ordre des formes réglable (fond vers premier plan).
     Les formes sont enregistrées dans `visuel.svg` (`rect`, `polygon`, `path`) et dans le réglage de l'outil pour
     être reprises. Le tracé automatique reste, en option, comme aide : « pré-remplir » propose des formes
     grossières (6 couleurs) que l'on corrige ou supprime.
     **Référence réelle (précision de l'utilisateur, 2026-11-13)** : le rendu de la page de la carte du rez-de-chaussée,
     `outils_docs/visuels_accueil/rendu-cible-page-reelle.png`, est plus fidèle que n'importe quelle maquette : la maison
     seule sous son toit noir. Tout ce qui l'entoure sur la photo a été retiré à sa demande (voiture, poteau, mur voisin,
     parabole, maison de droite). Un tel retrait est donc le cas normal, pas l'exception : l'éditeur part d'une photo brute et
     l'utilisateur ne dessine que ce qu'il garde, avec des zones « effacer » faciles à tracer sur les éléments gênants.
     **Rendu cible, retenu par l'utilisateur (maquette PNG du 2026-11-12, confirmé le 2026-11-13)** : la façade du rez-de-chaussée de `outils_docs/volets_visuels/maquette_rdc_porte_cuisine.html`
     (maquette du 2026-11-12, d'après la photo de la maison : briques et tuiles en motifs, ouvertures à contour blanc,
     objets simples comme la boîte aux lettres, le numéro, la caméra). Les formes de l'éditeur acceptent donc, en plus
     d'une couleur unie, un **motif** (briques, tuiles, lames), repris des `<pattern>` de `volets.js` (`dessine()`).
     **Éléments tout faits** (demande du 2026-11-13 : « façade de maison avec fenêtre, toit légèrement incliné ») : une
     palette de gabarits que l'on pose puis ajuste à la souris : mur de façade, toit monopente à pente réglable
     (comme le garage) ou à deux pans, fenêtre (un ou deux battants, contour blanc), porte, porte de garage, volet
     roulant, cheminée, boîte aux lettres, numéro. Chaque gabarit est une petite forme composée dont la taille, la
     pente et les couleurs se règlent ; les couleurs partent de celles échantillonnées sur la photo.
   Le poids du fond est affiché en permanence (un dessin à plat de 20 formes pèse 1 à 3 Ko).
   **Décors réels à garder ou à effacer** (demande du 2026-11-13) : ce qui n'est pas dessiné est effacé (une voiture
   garée, une maison voisine disparaissent) ; en mode dessin, une zone peut aussi être **gardée en photo** (morceau de
   photo posé sur le dessin) pour un appareil ou un bornier que des formes rendraient illisible. En mode photo, une
   zone *effacée* est remplie d'un aplat de la couleur moyenne de son bord.
4. **Points chauds** posés à la souris sur le fond, de trois sortes :
   - *voyant* : un relais ou une entrée ; allumé ou éteint ; forme et couleurs réglables ; une icône facultative ;
   - *valeur* : une mesure du JSON SENSOR (chemin de clés), avec unité, décimales, position du texte ;
   - *liaison* : un trait entre deux points du fond, qui s'anime quand la voie échange, grisé quand elle est muette ;
     sources : voie série ModBus, un esclave ModBus (par id), une carte UDP (par MAC ou nom), un client du range
     extender, le Wi-Fi de la carte.
   **Icônes et images** (demande du 2026-11-13) : l'utilisateur règle la **taille** de chaque icône, et l'icône peut
   **changer selon l'état** (caméra allumée / éteinte, porte ouverte / fermée, lumière) : un voyant porte `icone_on`,
   `icone_off` et, pour un état inconnu ou muet, `icone_inconnu`, avec une couleur par état. La **banque** est celle déjà
   constituée pour les écrans : le catalogue des icônes du firmware (`outils_docs/schemas/icones_firmware.json`, chargé par
   `atelier_ecrans_icones.charge`, environ 130 icônes Material Design) et les sources de `outils_docs/ICONES_IMAGES_SOURCES.md`
   (Pictogrammers MDI, Material Symbols, Tabler, Lucide, Phosphor, Simple Icons). Un SVG de la carte ne peut pas utiliser la
   police des glyphes : l'outil convertit chaque icône choisie en **tracé vectoriel** (`path`, jeu `@mdi/js` ou SVG de la
   collection, Apache 2.0 pour MDI, licence notée à côté du fichier) et l'intègre au SVG du fond ou à la description. L'utilisateur
   **Recherche en ligne** (demande du 2026-11-13, comme pour les écrans) : un champ de recherche interroge, depuis le serveur
   de l'outil, le moteur multi-collections de `ICONES_IMAGES_SOURCES.md` § 2 (Iconify : un seul point d'accès pour MDI,
   Material Symbols, Tabler, Lucide, Phosphor, Simple Icons). Seul le **mot cherché** quitte le PC, jamais la photo ni le
   projet. Garde-fous : hôte fixe et paramètres validés (aucune URL fournie par la page n'est suivie), SVG reçu passé par
   `nettoie_svg`, **licence lue avec la collection** et affichée sur chaque résultat, seules les licences permissives
   (MIT, Apache 2.0, ISC, CC0) sont proposées d'office, les licences à attribution (CC BY) sont signalées et demandent la
   confirmation de l'utilisateur, les autres sont masquées ; cache local hors dépôt ; licence et origine notées dans un
   fichier à côté de l'icône gardée (`outils_docs/visuels_accueil/icones/LICENCES.md`). Hors ligne, la banque locale
   (firmware et icônes déjà gardées) reste utilisable. Le format de l'API et ses limites sont **à vérifier** à l'implémentation.
   peut aussi **importer** un `.svg` d'une autre collection (nettoyé par `nettoie_svg`, licence confirmée comme pour les polices
   de l'atelier des écrans). Un voyant sans icône garde sa forme (rond, carré).
   Chaque point chaud est relié à une source choisie dans une liste tirée du **persist de la carte au dépôt** (relais et
   entrées nommés, esclaves ModBus, fiches discovery) et, si la carte est en ligne, de son JSON SENSOR réel.
5. **Export pour l'utilisateur** (demande du 2026-11-13) : depuis la page, l'utilisateur obtient son visuel hors de la
   carte : l'**image vectorielle** (fichier `.svg` à télécharger, copie du code SVG) et le **code HTML** correspondant
   (un fragment autonome : le SVG avec ses calques et le petit script d'animation de `visuel.js`, collable dans une
   autre page, sans dépendance), avec en plus un PNG de la vue courante. Ces exports ne touchent ni le dépôt ni la
   carte. Le SVG exporté est celui du fond avec les points chauds posés, dans leur état simulé choisi.
6. **Aperçu** dans l'outil par le vrai moteur de la carte (`visuel.js`), avec l'état réel si la carte est en ligne,
   sinon un état simulé que l'on bascule à la main (relais ON/OFF, liaison active/muette).
7. **Écriture dans le dépôt** en deux temps (diff puis écriture atomique) : la description, le fond, la ligne de
   l'autoexec, les listes du cenv. Refus pendant un build ou sur empreinte périmée. Puis un lien « Téléverser » vers la
   page Build, les fichiers déjà cochés.
8. **Page de la carte** : sous la zone des capteurs de l'accueil, le fond avec ses calques, mis à jour à une cadence
   réglable (défaut 2345 ms, le `WebRefresh` de Tasmota, comme la façade des volets ; requête suivante seulement après
   la réponse de la précédente, coupée à 4 s : donnée « inconnue », dessin grisé), sur toutes les cartes qui portent une description. Aucun bouton ni page de plus.
9. **Suivi** : la page signale, par carte, si le fichier présent sur la carte diffère de celui du dépôt (comme les
   étiquettes QR).

10. **Assistant IA facultatif** (demande du 2026-11-13) : un panneau de la page où l'utilisateur écrit une consigne
    (« la maison seule, briques et tuiles, sans voiture ni poteau ») et envoie la photo recadrée à l'IA de son choix, qui
    rend un SVG. Le résultat est nettoyé (`nettoie_svg`) puis proposé comme **point de départ** : il s'ouvre dans l'éditeur
    de formes, où l'on corrige, efface, ajoute les gabarits et les points chauds.
    - **Procédé au choix** (liste de fournisseurs, extensible) : *Claude Code local* (`claude -p` en lecture seule sur un
      fichier image, sans clé, sur l'abonnement de l'utilisateur : précédent de l'atelier des écrans) ; une API externe
      avec la clé de l'utilisateur (Anthropic, Google Gemini et son niveau gratuit, Mistral... à confirmer à l'A9) ; un modèle
      local (Ollama) qui ne fait sortir aucune image du PC. Les modalités de chaque offre gratuite (limites, usage des
      données pour l'entraînement) sont lues dans sa documentation à l'A9, pas supposées ici.
    - **Modèle déjà en service : les remarques de l'atelier des écrans** (`atelier_ecrans_remarques.py`, plan
      atelier-ecrans A7, options vérifiées le 2026-11-12). Le fournisseur *Claude Code local* le reprend tel quel :
      `claude -p` lancé dans le dépôt en lecture seule (`--tools Read,Grep,Glob`, `--permission-mode dontAsk`,
      `--strict-mcp-config`, `--no-session-persistence`, `--disable-slash-commands`, `--output-format json`), sans les hooks
      de l'utilisateur (`--settings` avec `disableAllHooks`, fonction `reglages_sans_hooks`), consigne par l'entrée
      standard, délai de 10 min, arrêt de l'arbre de processus (`taskkill /T /F`), journal de chaque appel. Claude
      **propose**, c'est l'outil qui valide et écrit ; les fichiers du dépôt changés pendant le traitement sont signalés par
      un avertissement. Depuis ce PC seulement. Pour les images, la photo recadrée est déposée dans un dossier temporaire
      hors dépôt passé par `--add-dir`, que Claude lit avec son outil de lecture.
    - **Remarques épinglées sur la photo** (même idée que l'atelier des écrans) : l'utilisateur épingle une remarque sur une
      zone (« efface la voiture », « garde la porte en photo », « briques en motif ») ; l'IA les traite par lots et
      répond par des opérations sur les formes (`ajoute`, `efface`, `motif`, `garde`), appliquées après validation dans
      l'éditeur, comme les propositions de l'atelier des écrans (états ouverte, proposée, appliquée, refusée).
    - **Avertissement avant chaque envoi** : « Cette photo va être envoyée à <service> », case à cocher mémorisable par
      fournisseur. Aucune clé ni consigne n'est envoyée à la page : les clés sont gardées côté serveur, hors dépôt
      (`%APPDATA%\atelier_visuels\config.json`, précédent de `sniffeur_mqtt_config.py`), masquées partout.
    - **Quota** : compteur local par fournisseur (envois du jour) ; l'outil lit les en-têtes de limite quand le service en
      donne, et traite un refus de type « trop de requêtes » (HTTP 429, message de dépassement de `claude -p`) par un
      avertissement clair avec l'heure de reprise connue, sans réessai automatique. Avertissement orange à 80 % d'un
      plafond saisi par l'utilisateur, rouge au dépassement.
    - **Essais** : dans l'ordre de moindre coût et de moindre fuite : Ollama local, `claude -p`, un niveau gratuit d'API.
      Le premier essai se fait sur l'image de l'utilisateur seulement avec son accord pour le fournisseur testé.
    - Le résultat d'une IA n'est jamais écrit tel quel dans le dépôt ni sur la carte : il passe par le nettoyage SVG, le
      contrôle de poids, l'éditeur, puis le diff habituel.

## 3. Non-objectifs et anti-objectifs

Non-objectifs (pas dans ce chantier, possibles ensuite) :
- commander un relais en cliquant son voyant (le visuel est en lecture seule) ;
- plusieurs visuels par carte, ou un visuel sur une autre page que l'accueil ;
- afficher le visuel sur les écrans HASPmota ou LVGL ;
- retoucher la photo au-delà du recadrage et de la rotation par quarts de tour ;
- un rendu « redessiné » par un modèle d'IA.

Anti-objectifs (ce qui rendrait le résultat mauvais même s'il marche) :
- la photo ne quitte le PC que par un geste explicite de l'utilisateur, vers l'assistant IA qu'il a choisi (§ 2.10), après un
  avertissement qui nomme le service ; jamais par défaut, jamais en arrière-plan ;
- aucune modification du `_persist.json`, de `user_config_override.h` ni d'un `.be` de `data/fs` par l'outil (la seule
  exception, la règle de rangement du § 6.4, est une édition faite une fois, à la main, avec l'accord de l'utilisateur) ;
- rien ne doit alourdir la page d'accueil quand la carte n'a pas de visuel : pas de requête, pas de script ;
- jamais une photo de plusieurs centaines de Ko sur une carte : le poids est montré, et bloqué au-delà d'un seuil.

## 4. Contraintes (lues dans le dépôt le 2026-11-13)

- **Zone `web_sensor` sans script** : remplacée par `innerHTML` toutes les ~2 s, elle n'exécute aucun `<script>` et
  relance toute animation CSS. Le visuel passe donc par `web_add_main_button`, injecté une fois, comme la façade
  (`data/fs/vrPages.be::vrPages_accueil`).
- **Aucune image servie aujourd'hui** par une carte : ni fichier image sous `data/`, ni route générique de fichiers
  statiques. Les `.gz` passent par des routes `?f=` à liste blanche, par morceaux de 2048 octets
  (`data/fs/graphiquesFonctions.be::envoieFichier`).
- **Rangement du FS** : `data/fs/gestionFileFolder.be::listeEtRepartitLesFichiers` range `.png|.jpg|.bmp` vers
  `/sd/images/<EXT>/`, `.html|.js|.css` vers `/sd/...`, tout nom contenant `.json` vers `/json/`. Ni `.svg` ni `.webp`
  ne sont connus.
- **Flash** : FS de 320 Ko sur ESP32 classique (448 Ko sur la cave), 11 584 Ko sur S3 et P4. L'espace réellement libre
  se compte en blocs de 4 Ko (leçon du 2026-11-02), pas en somme de tailles.
- **Pas de Pillow** dans le Python de PlatformIO : tout traitement d'image se fait dans le navigateur.
- **Routes de la carte** derrière `webserver.check_privileged_access()`.
- **Script injecté** : une IIFE, sans `</` ni `<!` dans son texte (en-tête de `volets.js`) ; le JSON inséré échappe `<`
  (`vrPages.be::vrPages_json`).
- **État disponible côté Berry** : `tasmota.get_power()` ; `tasmota.read_sensors()` ; `modbusFonctions.etat()`
  (`derniereReponseSerie`, `ipsApprises`) ; `udpFonctions.etat()["presence"]` (MAC vers millis du dernier ImAlive) ;
  `discoveryFonctions.etatReseau(table, rgx)` (états `ok|muet|ip|absent|fantome|box|inconnu`, rssi). Aucune route JSON
  ne les réunit ; `/histo?p=direct` ne donne que les mesures et n'existe que sur S3/P4.
- **Règles du dépôt** : charte des logs Berry ; module solidifié appelé par `xxxFonctions.nom` ; nouveau fichier propre
  à quelques cartes exclu des autres envs ; aucun fichier hors firmware dans `data/<lieu>/<carte>/` ; commits en
  français sans accents ; images et ressources sous `/sd` (consigne du 2026-11-11).

## 5. Approches considérées

1. **Tout dans le navigateur** (retenue). Recadrage et compression de la photo par le canvas ; dessin par une
   bibliothèque JS de vectorisation libre embarquée dans la page (ImageTracer.js, licence libre, un seul fichier) pour
   les aplats, filtre de contours par le canvas pour le trait. Aucune dépendance Python : l'outil marche sur tout poste
   dès le clone. Limite : tracé moyen sur une photo chargée ou mal éclairée ; quelques secondes sur un grand cliché.
2. **Vectorisation sur le PC** : Pillow pour la photo, vtracer (binaire Rust par pip) pour le SVG. Tracé plus propre,
   plus de réglages ; mais deux dépendances à installer sur chaque poste et un banc qui dépend d'un binaire. La chaîne
   vers la carte ne change pas : c'est le palier de repli si le tracé de la voie 1 déçoit sur les photos réelles.
3. **Redessin par IA** : écartée comme voie par défaut (photo du domicile envoyée dehors, coût, non reproductible) ; **ajoutée le
   2026-11-13 comme option choisie par l'utilisateur** (§ 2.10), en plus de l'éditeur manuel.

Choix de l'utilisateur le 2026-11-13 : voie 1. Maintenue après l'essai A0 (voir `outils_docs/visuels_accueil/README.md`) : le rendu voulu étant à plat (§ 2.3), la voie 2 (vtracer) n'a plus d'objet.

## 6. Ce qui a été décidé

### 6.1 Fichiers sur la carte

Dans `data/<lieu>/<carte>/` (donc à plat à la racine du FS, puis rangés au démarrage) :

- `visuel.json` : la description (§ 6.2), rangée en `/json/visuel.json`.
- le fond, un seul des deux : `visuel.svg` (mode dessin, SVG texte, 5 à 40 Ko) ou `visuel.webp` (mode photo, 15 à
  40 Ko ; `visuel.jpg` si le navigateur ne produit pas de WebP). Rangé en `/sd/images/SVG/` ou `/sd/images/WEBP/`
  (§ 6.4).

Dans `data/fs/`, communs à toutes les cartes et solidifiés :

- `visuelFonctions.be` : lecture de la description, route `/visuel`, injection sur l'accueil, état unifié.
- `controleVisuel.be` : driver (garde `web_add_main_button`, `web_add_handler`), chargé par l'autoexec des seules cartes
  qui ont un visuel.

Dans `data/sd/js/` : `visuel.js`, le moteur de dessin des calques, commun à la carte et à l'aperçu de l'outil.

Cenv : une liste `visuel_accueil` dans `[berry_commun]` (`visuelFonctions.be`, `controleVisuel.be`, `visuel.js`),
exclue de tout env sans visuel, levée par l'outil pour l'env qui en reçoit un, et `custom_berry_solidify` tenu à jour
comme le fait `etiquettes_qr_ecriture.py`. Les fichiers `visuel.*` du dossier de la carte ne sont jamais recopiés
ailleurs.

### 6.2 La description `visuel.json`

Une seule version de schéma, champ `version: 1`. Contenu :

- `fond` : `{type: "svg"|"webp"|"jpg", largeur, hauteur}` (dimensions en pixels du fond, repère des points chauds) ;
- `rafraichissement` : millisecondes entre deux lectures d'état (défaut 2345, minimum 1000) ;
- `elements` : liste ordonnée, chaque élément ayant `id`, `type` (`voyant`, `valeur`, `liaison`), `x`, `y` (et `x2`,
  `y2` pour une liaison), `source`, et un objet `style` propre au type (forme, couleurs ON/OFF, taille, icône parmi un
  petit jeu de chemins SVG MDI gardés dans `visuel.js`, texte avant/après, unité, décimales, épaisseur et couleur du
  trait).

`source` désigne l'état lu :

- `{"type": "relais", "n": 1}` (numéro Tasmota de `tasmota.get_power()`, le nom vient du persist pour la liste) ;
- `{"type": "mesure", "chemin": ["ANALOG", "A1"]}` dans le JSON SENSOR. **Les entrées (boutons, contacts) passent par
  là** : `controleGeneral.be::json_append` les publie déjà dans le SENSOR, il n'y a pas de type `entree` à part. Un
  *voyant* accepte une source `mesure` avec une condition `{"on": valeur}` ou `{"on_min": seuil}` (décision du
  relecteur, 2026-11-13 : une seule voie de lecture, pas d'API Berry de plus) ;
- liaisons (révisé le 2026-11-13 d'après `discoveryFonctions.etatReseau` et la page `/discovery`) :
  `{"type": "modbus_serie"}` et `{"type": "modbus_esclave", "id": 3}` avec un `seuil_s` (défaut 3 × `drivers.ModBus.periodeReleve`,
  30 s si absent, soit 90 s ; actif si l'âge de la dernière réponse est sous le seuil) ;
  `{"type": "esclave", "mac": "..."}` pour UDP ET range extender : l'état vient de la ligne de `etatReseau` de cette MAC,
  sans seuil (la fiche passe « Offline » après 2 × telePeriod, `udpFonctions.perimeFiches`). Actif si `etat` vaut `ok` ;
  « en alerte » (orange) si `muet` ou `ip` ; muet (rouge ou grisé) si `absent`, `fantome` ou `inconnu` ; `box` : actif si le
  détail dit UDP vivant. Les couleurs reprennent celles de `/discovery` (`ok` vert, `muet` et `ip` orange, `absent` et
  `fantome` rouge, `box` et `inconnu` gris). `{"type": "wifi"}` : liaison de la carte à la box, `up` de `tasmota.wifi()`.
  Les types `udp` et `rgx` de la première version sont supprimés ; la liste des MAC vient de `/json/discovery.json` du
  maître en ligne, ou se saisit à la main (le fichier n'est pas dans le dépôt).
- **Esclaves de la voie série ModBus** (précision de l'utilisateur, 2026-11-13) : un esclave (cuve, rideau...) porte le
  visuel de la même façon que le maître, sur sa propre page d'accueil, et lit ses états chez lui : relais et mesures réelles
  par `tasmota.get_power()` et le JSON SENSOR, aucune requête vers le maître. Sa liaison ModBus se juge sur ce que
  `modbusFonctions.etat()` tient côté esclave : fraîcheur de chaque mesure (`mesures`, registre vers millis de la dernière
  mesure, `limites`, `sansMesure`) et numéro du dernier push (`seqPush`). `derniereReponseSerie` et `muets` ne concernent que
  le maître. Source à ajouter à la liste : `{"type": "modbus_mesure", "registre": n}`, active si l'âge de la mesure est sous sa
  limite ; à confirmer au palier 2 par la lecture de `declareMesure` et `noteMesure`. Un esclave derrière le range extender
  se joint par `IP:port` (1er esclave `<ipMaitre>:8080`) : l'outil l'utilise pour l'aperçu réel.
- **Commandes lourdes** : `RgxClients` (donc `etatReseau`) n'est pas appelé à chaque lecture. `f=etat` met ce bloc en
  cache 30 s, comme `ecranSysteme.LENT` (30 000 ms : chaque réponse de commande part aussi en MQTT).

### 6.3 Côté carte : `visuelFonctions.be`, `controleVisuel.be`, `visuel.js`

- **Injection** : `web_add_main_button` envoie `<div id='vz'></div><script>window.VISUEL=<description échappée></script>
  <script>` + `visuel.js` + `</script>`, sur le modèle exact de `vrPages_accueil`. Si `/json/visuel.json` est absent ou
  invalide : rien n'est envoyé, une ligne `erreur` dans le journal, et le driver ne se réabonne pas.
- **Route `/visuel`**, `check_privileged_access`, actions par `?f=` à liste blanche :
  - `f=fond` : le fond. SVG : envoyé par `readFileByLineAndContentSend` en `image/svg+xml`. WebP ou JPEG : par morceaux
    de 2048 octets en `rb`, sur le modèle d'`envoieFichier`, avec le bon `Content-Type` et un `Cache-Control` long
    (le fond change seulement par un téléversement ; le JS ajoute l'empreinte de la description à l'URL pour forcer la
    relecture après un envoi) ;
  - `f=etat` : l'état unifié, un seul JSON : `{"t": millis, "power": [bool...], "entrees": {...}, "sensor": {...},
    "modbus": {"serie_ms": n, "esclaves": {"3": ms}}, "udp": {"<mac>": ms}, "reseau": [...]}`. Chaque bloc n'est
    construit que si la description a au moins une source de ce type (lue une fois au chargement), pour épargner la
    RAM des ESP32 classiques ; `sensor` est réduit aux chemins demandés. Les modules absents (ModBus non chargé, pas de
    range extender) donnent un bloc vide, jamais une exception.
- **`visuel.js`** : une IIFE. Dessine un `<svg viewBox="0 0 largeur hauteur">` avec le fond en
  `<image href="/visuel?f=fond&v=<empreinte>">`, **pour les deux types de fond** (un seul chemin de code ; un SVG chargé
  par `<image>` n'exécute rien, le nettoyage du § 6.5 reste pour le poids et par précaution), puis un calque par
  élément. Toutes les `rafraichissement` secondes, `fetch('/visuel?f=etat')` et mise à jour des attributs (classe
  `on`/`off`, texte, animation du trait par `stroke-dashoffset`). Une liaison est « active » si l'âge de son horodatage
  est sous son `seuil_s` (§ 6.2) ; « muette » sinon. Le bloc `reseau` de `f=etat` est la liste rendue par
  `discoveryFonctions.etatReseau` (`mac`, `nom`, `etat`, `rssi`) réduite aux MAC demandées. Le tout vit hors de la zone
  `web_sensor` : rien à redessiner après ses remplacements. Largeur : celle de la page d'accueil (le `viewBox` suit,
  hauteur proportionnelle).
- **Place sur l'accueil** : celle de `web_add_main_button`, c'est-à-dire **sous les boutons et curseurs des relais, au
  dessus des boutons de menu** (`xdrv_01_9_webserver.ino::HandleRoot`, zone `l1` puis boutons puis
  `FUNC_WEB_ADD_MAIN_BUTTON`), exactement là où la façade des volets se dessine. Façade et visuel **peuvent coexister**
  sur une même carte (le P4 du garage) : chaque driver ajoute son bloc, dans l'ordre de chargement de l'autoexec ;
  l'outil écrit la ligne `controleVisuel` **en dernier**, le visuel vient donc sous la façade. Le validateur n'interdit
  rien.
- **Logs** : charte du dépôt, cible `visuel`, préfixe `VISUEL:`. Dans `/visuel?f=etat` (appel fréquent) : `debug` ou
  `detail` seulement.
- **RAM** : la description est lue une fois au démarrage et gardée (moins de 4 Ko) ; l'état est construit à la demande
  et jeté. Sur un ESP32 classique, mesurer le tas avant et après un chargement de l'accueil (journal avec `BRY: GC`).

### 6.4 Rangement des nouveaux types d'image

`gestionFileFolder.be::listeEtRepartitLesFichiers` reçoit `.svg` et `.webp` dans la règle des images
(`/sd/images/SVG/`, `/sd/images/WEBP/`). C'est la seule édition d'un `.be` de `data/fs` hors des deux modules neufs, et
c'est un fichier de l'utilisateur : **à faire une fois, à la main, après son accord explicite**, et à couvrir par
`banc_repartition_fichiers`. Tant qu'elle n'est pas faite, le lecteur Berry cherche le fond d'abord au chemin rangé, puis
à la racine.

### 6.5 L'outil PC (port 7990)

Modules, dans `outils_docs/scripts_python/outils_pc/`, selon le squelette de `tapp_web.py` :

- `atelier_visuels_web.py` : serveur, routes ; `atelier_visuels_page.py` + `_page_js.py` : la page (HTML, CSS, JS) ;
  `atelier_visuels_description.py` : validateur de `visuel.json` et listes de sources tirées du persist ;
  `atelier_visuels_ecriture.py` : `prevoit` / `ecrit` (Transaction, cenv, autoexec), calqué sur
  `etiquettes_qr_ecriture.py` ; `atelier_visuels_suivi.py` : comparaison dépôt / carte.
- `build/cible_atelier_visuels.py`, `NOM_CIBLE = "atelier_visuels"`, page lancée détachée ; enregistrée dans
  `pre_utilitaires_platformio.py` ; tuile dans `annuaire_registre.OUTILS` ; tâche VS Code « Outil : atelier des visuels
  (http://127.0.0.1:7990) » ; `visuel` ajouté à `build_page_atelier.AT_ORIGINES`.
- La page sert `visuel.js` (le même fichier que la carte) et la bibliothèque de vectorisation, rangée dans le dépôt à
  côté de l'outil avec sa licence, jamais envoyée sur la carte.
- **Traitement d'image dans le navigateur** : la photo est lue par `FileReader`, affichée dans un canvas, recadrée par un
  rectangle à poignées, tournée par quarts de tour ; mode photo : `canvas.toBlob('image/webp', qualité)` à la largeur
  cible (défaut 480 px, réglable 320 à 800), repli `image/jpeg` ; mode dessin : la bibliothèque produit un SVG depuis
  les pixels du canvas réduit (largeur de travail 480 px pour tenir le temps de calcul), ou un tracé au trait par un
  filtre de Sobel sur le canvas puis la même vectorisation en deux couleurs. Les SVG produits sont **nettoyés** avant
  toute écriture : seuls `svg`, `g`, `path` et leurs attributs de forme et de couleur sont gardés ; tout le reste est
  retiré (le fond est inliné dans la page de la carte, il ne doit porter aucun script ni lien).
- **Éditeur de points chauds** : logique de glisser copiée et allégée de `atelier_ecrans_page_canevas.py` (pointeurs,
  zoom, aimantation, poignées), le fond en arrière-plan ; un panneau par élément sélectionné ; annuler/rétablir.
- **Poids** : affiché pour le fond et la description. Seuils : avertissement orange au-dessus de 40 Ko de fond, refus
  d'écriture au-dessus de 60 Ko sur un ESP32 classique (puce lue par `lieux.puce()`), 200 Ko sur S3/P4. Ces seuils sont
  des constantes nommées de l'outil, pas des réglages.
- **Sources** : relais et entrées nommés d'après le persist de la carte (bloc métier, broches de `configGlobal.be`),
  esclaves ModBus d'après `drivers.ModBus`, cartes UDP d'après `discovery.json` du dépôt ; si la carte répond, les clés du
  SENSOR réel complètent la liste. Persist lu en lecture seule, secrets jamais envoyés à la page (même filtre que
  l'assistant persist).
- **Transport du fond** : le navigateur envoie le fond en **corps binaire brut** (`POST /fond?env=&type=svg|webp|jpg`,
  `Content-Type` de l'image), gardé en mémoire du serveur sous une empreinte que la route d'écriture cite ensuite ; cette
  route seule accepte 1 Mo, les routes JSON gardent leur `MAX_CORPS` habituel. Pas de base64 (décision du relecteur).
- **Sécurité de la page** : POST avec en-tête `X-...` et origine 127.0.0.1 ; jeton pour un autre appareil (`acces_web`) ;
  la photo d'origine ne quitte jamais le navigateur ; noms de fichiers à liste blanche ; aucune URL fournie par la page
  n'est contactée par le serveur hors des IP du parc.

### 6.6 Bancs et preuves

- Python : `test_atelier_visuels_description.py` (validateur, cas partagés avec le banc Berry), `test_atelier_visuels_ecriture.py`
  (copie temporaire du dépôt, jamais le vrai ; relecture par `ProjectConfig`), `test_atelier_visuels_web.py` (routes,
  refus pendant un build, 403 sans en-tête), sonde `test_atelier_visuels_page_chrome.py` (photo de test **fabriquée par
  la sonde** dans le navigateur, formes colorées sur un canvas : aucune photo réelle dans le dépôt ; les deux modes, un
  point chaud de chaque type, SVG nettoyé ; attend des conditions, jamais une durée ; arrête ses Chrome),
  `test_visuel_js.mjs` (moteur : états, liaison active ou muette).
- Berry : `berry/banc_visuel.{py,be}` (description valide et invalide, état unifié avec modules absents, HTML injecté
  sans `</` dans le JSON) ; `banc_demarrage.py` après la modification du cenv ; `banc_repartition_fichiers` pour § 6.4.
- `build/test_cible_atelier_visuels.py`, `test_garde_build.py` (la liste des cibles d'outils).
- Sur carte : compilation par la page Build, accueil chargé, capture Chrome de la vraie page avec largeur mesurée avant
  et après (leçon du 2026-10-31), tas lu avant et après sur un ESP32 classique.

### 6.7 Documentation

`outils_docs/README.md` § « Atelier des visuels (page web) » ; une ligne dans la carte des documents de `CLAUDE.md` ;
`tasks/plans/atelier-visuels.md` avec clé `objectif:` ; une entrée de `outils_docs/ICONES_IMAGES_SOURCES.md` pour la
bibliothèque de vectorisation (licence).

### 6.8 Leçons de la façade des volets (transcripts des 11 au 13 novembre, relus le 2026-11-13)

- **Rythme** : la période n'est pas dans le persist mais lue sur la carte par `tasmota.cmd("WebRefresh")` (repli 2345 ms,
  `vrPages.be::vrPages_facade`). Le visuel fait pareil : `rafraichissement` de `visuel.json` est facultatif et, absent,
  vaut le `WebRefresh` de la carte.
- **Poursuite, pas extrapolation** : un élément animé rejoint la valeur lue à sa vitesse ; l'extrapolation dépassait la
  valeur finale. Le dessin des liaisons ne devine donc rien entre deux lectures.
- **Carte muette** : requête coupée à 4 s, dessin grisé (opacité 0,45), jamais d'exception ; un état inconnu ne juge pas.
  Un maître qui ne répond pas est réessayé seulement toutes les 10 s côté carte (sinon chaque lecture bloque le serveur web
  0,6 à 1,4 s).
- **Une requête par rafraîchissement au plus**, état regroupé dans une seule réponse (`f=etat`).
- **Script injecté inline à chaque ouverture de l'accueil**, donc jamais mis en cache : `volets.js` pèse 35 Ko. Le
  `visuel.js` doit rester petit ; le fond, lui, est servi à part et mis en cache.
- **Pièges déjà payés** : fichier du moteur exclu par erreur du FS d'un env (vérifier chaque env qui reçoit le visuel),
  route enregistrée plusieurs fois, `</script>` orphelin après une exception (mutants au banc), clic de commande qui
  échoue en silence.
- **Fabrication de l'image** : la façade du rez-de-chaussée a été dessinée à la main d'après la photo, motifs `<pattern>`
  briques et tuiles, par itérations (voiture, poteau, voisin retirés à la demande) puis validée sur maquette. Aucun
  tracé automatique. Rendu de référence : `outils_docs/visuels_accueil/rendu-cible-facade-rdc.png`.

## 7. Paliers

1. **Essai jetable** : vectoriser une vraie photo de l'utilisateur (chemin fourni par lui) dans une page HTML de test,
   sortir trois rendus PNG (aplats 8 couleurs, aplats 16 couleurs, trait) à choisir sur pièces, liens cliquables dans le
   message. L'utilisateur tranche : la voie 1 tient, ou l'on passe à vtracer (§ 5, voie 2) pour le palier 3 seulement.
   **Le palier 2 ne l'attend pas** : le côté carte ne dépend pas de la façon dont le fond est fabriqué.
2. Côté carte : description, `visuelFonctions.be`, `controleVisuel.be`, `visuel.js`, bancs Berry, essai sur une carte
   avec un `visuel.json` et un SVG écrits à la main. La liste `visuel_accueil` du cenv est **exclue de tous les envs**
   à ce palier (comme `etiquette_qr` l'était avant sa première carte), `banc_demarrage.py` relancé ; seul l'env de la
   première carte la lève au palier 6.
3. Outil : import, recadrage, deux modes, poids, nettoyage SVG, aperçu par `visuel.js` en état simulé.
4. Points chauds et sources, aperçu en état réel si la carte est en ligne.
5. Écriture dans le dépôt, lien vers Build, suivi dépôt / carte, cible, tuile, tâche, README, plan.
6. Première carte réelle : **la cuve** (`tasmota32s3-garage-capteurs-cuve-modbus`, proposition : S3 au FS large, pas
   de façade à côté, esclave ModBus et UDP à montrer), puis le P4 (cohabitation avec la façade), puis un ESP32 classique
   pour mesurer flash et RAM.

## 8. Laissé au constructeur

- La bibliothèque exacte de vectorisation et ses réglages par défaut, après l'essai du palier 1.
- Le jeu d'icônes MDI embarqué dans `visuel.js` (une dizaine : ampoule, pompe, ventilateur, prise, porte, antenne…),
  choisi dans `outils_docs/ICONES_IMAGES_SOURCES.md`.
- L'aspect exact des voyants, valeurs et traits, à proposer sur maquette image avant de coder la page (règle du
  dépôt : un choix visuel se présente sur une image).
- La forme des messages d'erreur et des avertissements de la page.
- L'ordre des paliers 3 et 4 s'il est plus simple de poser les points chauds avant les deux modes de fond.
