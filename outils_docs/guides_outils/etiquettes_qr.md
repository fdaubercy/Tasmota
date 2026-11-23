# Étiquettes QR code

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Étiquettes QR code (page web)

Page http://127.0.0.1:7970 pour composer, carte par carte, un QR code qui affiche l'identité de la carte au téléphone,
l'imprimer en étiquette ou en planche A4, et le montrer sur une page de la carte. Par défaut, le QR code contient du
texte et aucun lien : le téléphone l'affiche sans réseau, ce qui sert quand une carte ne répond plus (mode lien : voir
« Fiche en ligne » plus bas). Lancement : tuile « Étiquettes QR
code » de l'annuaire (groupe Ateliers), tâche VS Code « Outil : étiquettes QR code », ou cible Custom « Étiquettes QR
code (page web) » (`build/cible_etiquettes_qr.py`, page démarrée détachée ; `pio run` : jamais pendant un build). Arrêt
libre : rien n'est écrit sans « Écrire dans le dépôt », après le diff. Spec :
`docs/superpowers/specs/2026-11-12-etiquettes-qrcode-design.md` ; plan : `tasks/plans/etiquettes-qrcode.md`.

**Contenu.** Une ligne par information, dans l'ordre voulu, chacune avec son libellé :
- un champ standard du dépôt : `hostname`, `ip`, `topic`, `env`, `puce`, `lieu`, `range_extender` (point d'accès de la
  carte maître) ;
- une clé choisie dans le persist de la carte : les clés de mot de passe ne sont jamais proposées, ni une valeur qui
  contient celle d'une clé secrète du même persist (une URL avec jeton, par exemple) ;
- un texte libre (120 caractères au plus).

Une ligne standard ou persist accepte un texte avant et après sa valeur (20 caractères chacun). Exemple : la ligne
`hostname` avec `http://` avant et `.local` après donne l'adresse mDNS de la carte. Elle ne s'ouvre que si le firmware a
`USE_DISCOVERY` et `WEBSERVER_ADVERTISE`, si la carte a `SetOption55 1` (persist `"mDNS": "ON"`), et depuis le même
réseau : un esclave derrière le NAPT du maître n'est pas joignable ainsi.

**Style et gabarit.** Points, coins, couleurs, image au centre (PNG, JPEG ou SVG de 8 Ko au plus, rangée dans
`outils_docs/etiquettes_qr/images/`). Le gabarit commun (`outils_docs/etiquettes_qr/gabarit.json`) vaut pour toutes les
cartes ; une carte qui s'en écarte garde son réglage dans `outils_docs/etiquettes_qr/cartes/<env>.json` (pastille
« réglage propre »). Pour fixer des valeurs par défaut, régler une carte puis « Faire du réglage de cette carte le gabarit commun… » (onglet Gabarit commun) : lignes, style, taille, contenu texte ou lien et « petit nom sous le code » sont alors chargés à l'ouverture et repris par les autres programmes (build, atelier des écrans). Ces fichiers restent hors du FS des cartes.

**Verdict de lisibilité.** Il dépend du nombre d'octets du texte (UTF-8, accents compris), de la taille imprimée et de
l'image (une image au centre impose la correction H, qui grossit le code). Seuils calés le 2026-11-12 sur un essai réel :
un carré élémentaire de 0,45 mm au moins est « lisible », de 0,40 à 0,45 mm « limite », en dessous « illisible ». Un texte
court se lit encore à 15 mm, un texte long demande 20 mm.

**Impression.** « Imprimer » ouvre la fenêtre du navigateur avec le QR code seul : imprimer à 100 %, sans
ajustement à la page, puis vérifier sur la règle imprimée qu'elle mesure bien 50 mm. La planche A4 rassemble les cartes
cochées dans la liste, à une taille de 10 à 100 mm, avec un petit nom sous chaque code en option. Une carte sans ligne
lisible, ou au texte trop long, en est écartée avec sa raison ; une carte « limite » ou trop dense à cette taille est
signalée. « Planche d'essai » imprime la carte affichée à 15, 20, 25 et
30 mm, avec un texte court et un texte long, pour caler la taille sur votre imprimante et votre téléphone (non notée).
Exports PNG et SVG. Chaque impression est notée (empreinte du texte seulement, dans
`outils_docs/etiquettes_qr/impressions.json`) ; « Annuler la note » la retire.

**Page `/qrcode` de la carte** (ESP32 seulement). Case « page sur la carte » : l'écriture ajoute la liste `etiquette_qr`
au FS de l'env et solidifie `qrcodePage.be` (cenv), ajoute `demarrage.charge(["qrcodePage"])` à l'autoexec, et écrit
`data/<lieu>/<carte>/qrcode.json` (texte déjà résolu, style, image). La carte le range dans `/json/` au démarrage. Le
bouton « QR code » apparaît dans le menu Outils de la carte ; la page dessine le même QR code que l'outil (même
bibliothèque, `data/sd/js/qrcode_options.js`), avec le texte dessous, un retour à la ligne à chaque séparateur. Elle
avertit si l'IP inscrite diffère de celle de la carte (comparaison seulement pour une IP sans port, pas pour un esclave
en `IP:port`). Il faut recompiler le firmware une fois (module solidifié), puis envoyer le FS par la page Build.

**Suivi.** Dans la liste des cartes, des badges signalent :
- « à réimprimer » : le texte a changé depuis la dernière impression notée ;
- « à régénérer » : le `qrcode.json` du dépôt ne correspond plus au réglage, au persist et au `.h` du moment.

À l'ouverture d'une carte qui a la page, la page interroge la carte (2 s au plus) : « carte à jour », « carte à mettre à
jour » ou « carte injoignable ». Dans le cas « à mettre à jour », le lien « Téléverser » ouvre la page Build sur cette
carte, `qrcode.json` coché et le redémarrage demandé (le fichier n'est rangé dans `/json/` qu'au démarrage).
Ailleurs :
- chaque `pio run` d'une carte qui a un réglage recalcule son `qrcode.json` avant l'image du FS et le réécrit s'il a
  changé (ligne « QR code de … : régénéré » dans la sortie de pio ; `build/qrcode_build.py`) ;
- après le renommage d'un env (page Fichiers Berry), le réglage suit le nouveau nom ;
- après un renommage, ou une modification par l'assistant persist qui change le texte, un lien « Étiquette QR à
  refaire » ouvre cette page.

**Fiche en ligne (mode lien).** Le menu « le QR code contient » propose, carte par carte, le texte (par défaut, lu
sans réseau) ou un lien vers une fiche HTML PUBLIQUE, `https://<propriétaire>.github.io/<dépôt>/<env>.html` (adresse
tirée de `remote.origin.url`, sans le jeton qu'elle porterait). Le lien se lit partout (4G, carte éteinte, ESP8266) et
la fiche se met à jour sans réimprimer l'étiquette. Les lignes du réglage deviennent le contenu de la fiche ; le titre
est le nom de l'env.

Avant de paraître, chaque ligne entière (libellé, texte avant et après, valeur, ligne libre) passe deux filtres :
- celui des secrets du persist : aucune valeur d'une clé de mot de passe ou de jeton, même recopiée dans un texte libre ;
- celui des valeurs publiques (`etiquettes_qr_filtre_public.py`) : pas d'identifiants dans une URL, de paramètre
  `token=` ou `key=`, d'IPv4 publique, d'IPv6 globale, de nom de domaine joignable (`.local`, `.lan`, `.home.arpa` et
  noms sans point acceptés), de chaîne à allure de clé, ni de mot qui annonce un secret (mot de passe, mdp, WPA…).

L'aperçu signale chaque ligne refusée par son numéro, sans la recopier ; une seule ligne refusée bloque toute la
publication. Faux positifs connus : un numéro de version à quatre nombres (15.1.0.1), un nom de fichier (autoexec.be).

« Publier les fiches… » montre le diff des fiches, puis pousse la branche orpheline `etiquettes` du dépôt, sans
forcer. Seuls les réglages ÉCRITS comptent. Toutes les cartes en mode lien sont publiées ; une carte repassée en texte voit
sa fiche retirée. L'arbre de travail, l'index et `development` ne sont jamais touchés (plomberie git). Refus pendant un
build, si la branche a bougé ailleurs depuis le diff, ou sans réponse de GitHub en 120 s. Une fiche dont seul le jour
change n'est pas renvoyée. Mise en service, une fois : bouton « Activer GitHub Pages… » de la page (affiché tant que
Pages est inactif ; il passe par `gh`, connecté au compte), ou sur GitHub, Settings > Pages, source « Deploy from a
branch », branche `etiquettes`, dossier `/ (root)`. Jusqu'à la première publication, le QR code d'une carte en mode
lien mène à une page introuvable.

Trois aides à ne pas oublier de republier :
- après « Écrire » d'une carte en mode lien, la page enchaîne sur le diff des fiches : un clic « Publier » suffit ;
- le badge « fiche à republier » de la liste compare chaque fiche à la dernière version connue de la branche, sans
  réseau ;
- chaque `pio run` d'une carte en mode lien dont la fiche a changé écrit « Fiche QR de … : à republier » dans sa sortie
  (`build/qrcode_build.py::fiche`, rien n'est envoyé).

Enfin, la case « Publier les fiches QR à la fin (public) » de la page Build publie toutes les fiches après une série
réussie, sans diff (confirmation au lancement) ; le résultat, ou la raison d'un refus, s'affiche dans le récapitulatif
de la série, qui reste réussie même si la publication échoue.

### Bancs

`outils_pc/test_etiquettes_qr_modele.py`, `_verdict.py`, `_ecriture.py`, `_suivi.py`, `_web.py`, `_filtre_public.py`,
`_publication.py` (dépôt temporaire dont l'origin est un dépôt nu local : rien ne part sur le réseau), puis les sondes Chrome
`test_etiquettes_qr_page_chrome.py` (page de l'outil) et `test_qrcode_carte_chrome.py` (page de la carte, servie par un
serveur local qui imite la carte) ; `berry/banc_qrcode_page.py` (module de la carte) ; `build/test_qrcode_build.py`
(régénération au build) et `build/test_cible_etiquettes_qr.py`. Commandes exactes : skill `bancs`.
