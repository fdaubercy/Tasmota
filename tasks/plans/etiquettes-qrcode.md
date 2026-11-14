---
chantier: etiquettes-qrcode
titre: Étiquettes QR code des cartes (page 7970) : impression, page de la carte, écran
objectif: Composer par env un QR code stylé qui affiche l identité de la carte (hostname, IP, clés du persist), l imprimer en étiquette ou en planche A4, l afficher sur une page de la carte et sur son écran, et signaler quand il est périmé
statut: actif
cree: 2026-11-12
maj: 2026-11-13
---
# Étiquettes QR code des cartes

## Contexte
Demande de l'utilisateur du 2026-11-12. **Spec validée le même jour :
`docs/superpowers/specs/2026-11-12-etiquettes-qrcode-design.md`** (à lire avant toute action ; décisions au § 6, choix
de Claude au § 7.9). En bref : le téléphone affiche du TEXTE (pas de lien) ; étiquette = QR code seul découpé dans une
feuille A4 ; contenu = champs standards du dépôt et clés choisies dans le persist, avec libellés et ordre ; style
(points, coins, couleurs, image au centre) ; gabarit commun surchargé par carte ; verdict de lisibilité selon le texte,
la taille en mm et l'image ; impression par la fenêtre du navigateur ; planche A4 ; export PNG/SVG ; page `/qrcode` de
la carte identique au QR code de l'outil ; suivi « à réimprimer », « à régénérer », « carte à mettre à jour » ; QR code à
l'écran sur appui d'un bouton, pendant un délai (dernière action, dépend de `tasks/plans/atelier-ecrans.md`).

Architecture : outil PC `etiquettes_qr_*` sur le modèle de l'atelier des graphiques (serveur `fabrique_gestionnaire`,
`acces_web`, `fichiers_berry_sauvegarde.Transaction`, `lieux.pour_page`, écriture en deux temps `prevoit`/`ecrit`). Le
réglage vit hors du dossier de la carte (`outils_docs/etiquettes_qr/`) ; seul le fichier GÉNÉRÉ
`data/<lieu>/<carte>/qrcode.json` (texte déjà résolu, style, image) part en flash. Une même bibliothèque JS dessine le
QR code dans l'outil et sur la carte.

### Contraintes globales
- Fichiers sous 500 lignes ; modules Python préfixés `etiquettes_qr_` dans `outils_docs/scripts_python/outils_pc/`.
- Aucune dépendance Python nouvelle. Une seule bibliothèque JS nouvelle : celle de l'A1, copiée dans le dépôt, version
  épinglée, intégrité vérifiée, jamais chargée d'un CDN.
- Python des bancs : `"$USERPROFILE/.platformio/penv/Scripts/python.exe"` ; bancs sur copies temporaires du dépôt.
- Compilation et FS par la page Build (:7700) seulement ; toute écriture au dépôt refusée pendant un build.
- Secrets : motif `assistant_persist_modele.SECRET` (seule définition, ne pas la recopier) sur les clés, plus le filtre
  par valeur du § 7.9-6 ; aucun secret dans une réponse HTTP, un fichier écrit, un QR code ou une sortie d'outil.
- `data/fs/qrcodePage.be` : création validée par la spec. Aucun autre `data/fs/*.be`, aucun `_persist.json`, ni
  `user_config_override.h` modifié par ce chantier.
- Fichiers de la page de carte exclus des envs qui ne l'ont pas (liste `etiquette_qr` de `[berry_commun]`).
- Logs Berry : charte du `CLAUDE.md`. Avant commit : agent `relecteur-berry` (Berry), `relecteur-pages-web` (pages).
- Rien n'est écrit au dépôt sans geste explicite dans la page (diff montré, puis confirmation).
- Commits en français, sans accents, sans trailer ; `git commit -- <chemins>` puis `git show --stat HEAD`.

### Points de vigilance (non couverts par la spec, un test chacun dans l'action indiquée)
1. Esclave derrière le range extender (IP inscrite `192.168.0.51:8081`) : la page de la carte ne signale pas de faux
   écart d'IP, la comparaison ne porte que sur une IP inscrite sans port (A6).
2. Texte avec accents, guillemets, barre oblique inverse, retour à la ligne : le verdict compte les OCTETS UTF-8, et
   le texte que dessine la bibliothèque est identique octet pour octet (A1, A2).
3. Image de centre trop lourde (> 8192 o en data URI) ou qui n'est pas PNG/SVG/JPEG : refusée avec un message, rien
   écrit (A2).
4. Persist ou réglage modifié dans le dépôt pendant que la page est ouverte : écriture refusée (empreinte périmée),
   rien écrasé (A3).
5. Carte injoignable : état « inconnu » rendu en moins de 3 s, page utilisable (A7).

## A0 — Maquettes de la page 7970 (choix de l'utilisateur)
Fichiers : créer `outils_docs/etiquettes_qr/maquettes_etiquettes_qr.html`, images `modele-A.png` à `modele-C.png`,
`README.md` (contraintes), sur le modèle de `outils_docs/atelier_graphiques/`.
- [x] Trois dispositions de la page et une de la planche A4, en clair et en sombre — preuve : maquettes_etiquettes_qr.html ;
  dispositions : en-tête avec liste des envs et bouton Sombre / Clair, liste des cartes, panneau des lignes, style, aperçu
  QR + texte lu + verdict ; `outils_docs/etiquettes_qr/maquettes_etiquettes_qr.html` (?m=A|B|C|P), captures `modele-A.png`, `modele-A-sombre.png`,
  `modele-B.png`, `modele-C.png`, `modele-P.png` relues ; constats pour l'A1 dans `README.md`
- [x] Choix de l'utilisateur noté dans `README.md` et ici — preuve : modèle A retenu le 2026-11-12 (trois colonnes),
  noté dans `outils_docs/etiquettes_qr/README.md` ; planche selon `modele-P.png`

## A1 — Bibliothèque de dessin du QR code
Fichiers : créer `outils_docs/etiquettes_qr/lib/qr-code-styling.min.js` (PC), `LICENSE-qr-code-styling.txt`,
`outils_docs/etiquettes_qr/lib/LISEZMOI.md` (paquet, version, licence, sha512 du registre, sha256 du `.js` et du futur
`.gz`). Le `.gz` des cartes (`data/sd/js/qr-code-styling.min.js.gz`) est écrit en A6, avec la liste `etiquette_qr` qui
l'exclut des autres envs (écrit avant, il partirait dans le FS de toutes les cartes).
Produit : bundle UMD autonome exposant `QRCodeStyling` (options `data`, `width`, `height`, `type: "svg"`,
`qrOptions.errorCorrectionLevel`, `dotsOptions`, `cornersSquareOptions`, `cornersDotOptions`, `backgroundOptions`,
`image`, `imageOptions`), `getRawData("png"|"svg")`.
- [x] Paquet npm `qr-code-styling` vérifié — preuve : 1.9.2 du 2025-04-11 (latest), MIT lue, sha512 du tarball = registre
  (INTEGRITE_OK), bundle sans `require` (`qrcode-generator` inclus), ids de clipPath par instance ; essai Chrome à
  plusieurs codes et à 75 px relu ; modules = table ISO (1 o -> 21 ... 63 o H -> 45)
- [x] Copie PC, licence et empreintes écrites — preuve : `outils_docs/etiquettes_qr/lib/` (`cmp` identique au tarball,
  sha256 du .js et du futur .gz notés dans `LISEZMOI.md`) ; `.gz` reporté en A6
- [x] Essai navigateur, scan confirmé par l'utilisateur le 2026-11-12 — preuve : essai2.png (64 octets, version 7, 45 modules, H, image) lu à l'identique au téléphone, barre oblique comprise ; 1er essai à 63 octets faux par ma page (barre oblique perdue, lessons.md) ; texte `Hostname : cuve\nIP : 192.168.0.60\nNote :
  « été » "x" \ 100 %` dessiné en points ronds, coins arrondis, image au centre, niveau H ; scanné par le téléphone de
  l'utilisateur, texte lu identique (vérification par l'utilisateur, notée en preuve)

## A2 — Modèle : gabarit, surcharge, champs, secrets, verdict
Fichiers : créer `outils_pc/etiquettes_qr_modele.py`, `outils_pc/etiquettes_qr_verdict.py`,
`outils_pc/test_etiquettes_qr_modele.py`, `outils_pc/test_etiquettes_qr_verdict.py`,
`outils_docs/etiquettes_qr/gabarit.json` (lignes Hostname, IP ; séparateur `" : "` ; points `rounded`, coins
`extra-rounded`, noir sur blanc, sans image ; `taille_mm` 25).
Consomme : `build_envs.persist_carte`, `build_envs.adresse_par_maitre`, `build_envs.lit_ip_ota`, `lieux.lieu`,
`lieux.puce`, `assistant_persist_modele.SECRET`.
Produit :
- `charge_reglage(racine, env) -> dict` : gabarit fusionné à `outils_docs/etiquettes_qr/cartes/<env>.json` s'il existe ;
- `fusionne(gabarit: dict, surcharge: dict) -> dict` : `lignes` et `separateur` remplacés en entier, `style` clé par clé,
  autres clés remplacées ;
- `valide_reglage(reglage: dict) -> list[str]` (messages en français, vide = valide) ;
- `champs_standards(racine, env) -> dict` : clés `hostname`, `ip`, `topic`, `env`, `puce`, `lieu`, valeur `str` ou
  `None` (introuvable) ;
- `arbre_persist(persist: dict) -> list[dict]` : `{"chemin": "a.b.c", "valeur": scalaire, "type": "texte"|"nombre"|
  "booleen"}`, scalaires seulement, ni clé `SECRET` ni valeur contenant la valeur d'une clé `SECRET` du même persist
  (valeurs de moins de 4 caractères ignorées par ce second filtre) ;
- `resout(racine, env, reglage) -> dict` : `{"texte": str, "lignes": [{"libelle", "valeur", "etat": "ok"|
  "introuvable"}], "avertissements": [str]}` ; ligne introuvable omise du texte ; lignes jointes par `"\n"` ;
- `fichier_carte(reglage, resolu) -> dict` : `{"version": 1, "texte", "style", "image", "correction", "ip_inscrite"}` ;
- `empreinte(texte: str) -> str` (SHA-256 hexadécimal) ;
- `verdict(texte: str, taille_mm: float, correction: str) -> dict` dans `etiquettes_qr_verdict.py` :
  `{"octets", "version", "modules", "module_mm", "niveau": "lisible"|"limite"|"trop_dense"|"trop_long"}` ; mode octet,
  table de capacité ISO/IEC 18004 versions 1 à 40 pour M et H ; `modules = 17 + 4 * version` ;
  `module_mm = taille_mm / (modules + 8)` (marge de 4 modules de chaque côté comprise dans la taille) ; seuils 0,5 et
  0,35 mm, à recaler en A5. Correction : `H` si image, sinon `M`.
Écarts à la réalisation (2026-11-12) : `valide_reglage(reglage, racine=None)` (avec `racine`, l'image est lue) ;
`champs_standards(racine, env, envs=None)` (`liste_envs` coûte plusieurs secondes : la passer une fois) ; `resout` délègue à
`resout_avec(reglage, champs, persist)` (pure) ; états `ok | introuvable | refuse` ; `fichier_carte(racine, reglage,
resolu)` ; `image_data_uri(racine, nom)` (PNG/JPEG/SVG du dossier `images/`, contenu vérifié, SVG sans script ni `on*=`,
8192 o au plus). Sans persist (ESP8266), hostname et topic lus dans le `config_decodee.json` du dossier de la carte
(`serveur_de_config`, ces deux clés seulement : ses mots de passe `sta_pwd`, `mqtt_pwd` échappent au motif SECRET) ; 16 cartes
sur 17 au 2026-11-12, `tasmota32-rdc-vr-porte` n'a encore ni persist ni config décodée.
**Entre les lignes (2026-11-12)** : l'appareil photo et l'appli « QR Code » de l'iPhone de l'utilisateur n'affichent aucun saut
de ligne (ni LF ni CR LF, essai4-lignes.png) : clé `entre_lignes` du réglage (`"
"`, `" · "`, `" | "`,
`ENTRE_LIGNES`), `" · "` par défaut dans le gabarit ; la page (A4) la propose à côté du séparateur.
**Encodage (découvert en A2)** : la bibliothèque ne code pas en UTF-8 (`255 & charCode`) ; la page (A4) et la carte (A6)
lui donnent `String.fromCharCode(...new TextEncoder().encode(texte))` avec `qrOptions.mode = "Byte"` ; la table
`CAPACITE` est alors exacte (80 cas sur 80, `lib/LISEZMOI.md`).
- [x] Scan du code UTF-8 par le téléphone de l'utilisateur — preuve : confirmé par l'utilisateur le 2026-11-12 (« l’œuf », « € », accents, barre oblique lus) ; sauts de ligne peu visibles, à éclaircir avant l'A4 (`essai3-utf8.png` du scratchpad : « l’œuf coûte 5 € », « été »,
  barre oblique) ; s'il lit mal, limiter le texte au Latin-1 (page et verdict)
- [x] Bancs — preuve : test_etiquettes_qr_verdict.py et test_etiquettes_qr_modele.py ; écrits APRÈS le module (écart au plan), leur pouvoir de détection est prouvé par les 4 mutants rouges ; cas prévus : `test_fusion` (surcharge de `lignes` remplace la liste, de `style.couleur` garde
  `style.points`), `test_secret_par_cle` (`serveur.wifi.mdp` absent de l'arbre), `test_secret_par_valeur` (une
  `url` contenant la valeur de `serveur.mqtt.password` absente), `test_introuvable` (`WIFI_IP_ADDRESS` 0.0.0.0 sans maître
  -> ligne IP omise, un avertissement), `test_esclave` (IP `<ipMaitre>:<8080+id-1>`), `test_image_refusee` (9000 o, puis
  un `data:text/html`), `test_verdict` (100 octets à 25 mm H -> attendu calculé à la main dans le test, un cas par
  niveau, 3000 octets -> `trop_long`), `test_octets_utf8` (« é » compte 2 octets) ; mutants : filtre par clé retiré,
  filtre par valeur retiré, seuil inversé -> chacun rouge
- [x] Modules ; bancs VERT, chaque mutant lu rouge — preuve : BANC_ETIQUETTES_QR_VERDICT: OK (mutants seuils inversés et table décalée rouges) ; BANC_ETIQUETTES_QR_MODELE: OK (filtre par clé retiré : 5 échecs, par valeur : 3) ; dépôt réel : 17 cartes, 13 persist, 24 valeurs secrètes surveillées par un motif indépendant, aucune proposée
- [x] Commit — preuve : commit « A2, modele et verdict » (git log)

## A3 — Écriture au dépôt
Fichiers : créer `outils_pc/etiquettes_qr_ecriture.py`, `outils_pc/test_etiquettes_qr_ecriture.py`.
Consomme : A2 ; réutilise la mécanique de `atelier_graphiques_ecriture.py` (`_exclut`, `_leve`, `_solidifie`,
`_autoexec`, `_controle`) en la paramétrant par la liste et la ligne d'autoexec, sans changer le comportement de
l'atelier (`test_atelier_graphiques_ecriture.py` VERT avant et après).
Produit :
- `prevoit(racine, env, reglage, page_carte: bool) -> dict` : `{"fichiers": {rel: texte|None}, "diffs": {rel: str},
  "empreinte": str, "avertissements": [str], "firmware_a_recompiler": bool}` ; écrit la surcharge
  `outils_docs/etiquettes_qr/cartes/<env>.json` (différence avec le gabarit seulement), et si `page_carte` :
  `data/<lieu>/<carte>/qrcode.json`, la ligne `demarrage.charge(["qrcodePage"])` de l'autoexec, le cenv (liste
  `etiquette_qr` levée pour l'env, exclue des autres envs ESP32 ; `qrcodePage.be` en fin de `custom_berry_solidify`) ;
  `page_carte` faux ou env ESP8266 : rien dans `data/` ni dans le cenv, et retrait propre si la page existait ;
- `ecrit(racine, env, reglage, page_carte, empreinte_lue, builds_en_cours) -> dict` (refus : empreinte périmée, build en
  cours) ;
- `ecrit_gabarit(racine, gabarit, empreinte_lue, builds_en_cours) -> dict` ;
- `note_impression(racine, envs: list[str], taille_mm: float) -> None` et `annule_impression(racine, env) -> None` sur
  `outils_docs/etiquettes_qr/impressions.json` : `{env: {"empreinte", "date", "taille_mm"}}`, jamais le texte.
Écarts à la réalisation (2026-11-12) : `prevoit` rend `{"fichiers": [{"chemin", "avant", "apres"}], "empreinte",
"signaux"}` (forme de l'atelier) ; `page_carte` touche 3 fichiers (cenv, autoexec, `qrcode.json`) en plus de la surcharge ;
refus de `page_carte` tant que `FICHIERS_PAGE` (A6) manque (la ligne d'autoexec chargerait un module absent) ; solidifié
seulement si `custom_files_exclude_solidified` est ON, sinon signal « reste sur le FS » ; `note_impression(racine, textes:
dict[env, texte], taille_mm)` ; en plus `prevoit_gabarit`, `prevoit_exclusions` / `ecrit_exclusions` (pour l'A6) ;
dossiers parents créés avant la Transaction (`cartes/` n'existait pas : défaut trouvé par le banc). `atelier_graphiques_ecriture`
reçoit des paramètres facultatifs (`texte`/`marque`, `solides`, `ligne`), défauts = ses constantes.
- [x] Bancs, copie temporaire — preuve : test_etiquettes_qr_ecriture.py, 34 vérifications ; écrit après le module (écart au plan), ses refus attendus (page sans A6, ESP8266, build, empreinte périmée, réglage invalide) échouent s'ils ne lèvent pas : surcharge minimale écrite ; `page_carte` -> fichiers touchés et
  `_controle` vert ; retour à `page_carte` faux -> cenv et autoexec octet pour octet d'avant ; empreinte périmée -> refus,
  rien écrit (vigilance 4) ; build en cours -> refus ; env ESP8266 + `page_carte` -> refus avec message ;
  `impressions.json` ne contient pas le texte
- [x] Module ; bancs VERT — preuve : BANC_ETIQUETTES_QR_ECRITURE: OK (34) ; test_atelier_graphiques_ecriture.py : même unique échec avant et après le paramétrage (« solidifie refuse sans custom_files_exclude_solidified = ON », préexistant, à signaler) ; `berry/banc_demarrage.py` sans objet (ni cenv ni autoexec du vrai dépôt modifiés)
- [x] Commit — preuve : commit « A3, ecriture au depot » (git log)

## A4 — Serveur et page 7970
Fichiers : créer `outils_pc/etiquettes_qr_web.py` (serveur, routes), `etiquettes_qr_page.py` (HTML, CSS),
`etiquettes_qr_page_js.py` (liste, lignes, arbre du persist, style, aperçu), `test_etiquettes_qr_web.py`,
`test_etiquettes_qr_page_chrome.py` ; `build/cible_etiquettes_qr.py` + `build/test_cible_etiquettes_qr.py` ; modifier
`annuaire_registre.py` (outil `etiquettes_qr`, groupe Maintenance, `_port("http", 7970)`, `lieu=True`),
`.claude/hooks/garde_build.py` (`CIBLES_OUTILS`), `.vscode/tasks.json` (tâche « Outil : étiquettes QR code »), cible
déclarée dans le pre-script comme les autres `cible_*.py`.
Consomme : A1 à A3. Produit, routes JSON : `GET /cartes` (envs par `lieux.pour_page`, badges vides jusqu'à l'A7),
`GET /gabarit`, `GET /reglage?env=` (+ empreinte), `GET /persist?env=` (`arbre_persist`), `POST /apercu` {env, reglage}
-> `resout` + `verdict` + `fichier_carte`, `POST /ecrire` {env, reglage, page_carte, empreinte}, `POST /gabarit`
{gabarit, empreinte}, `POST /impression` {envs, taille_mm}, `POST /impression/annule` {env}, `GET /lib.js` (A1).
`?env=` à l'arrivée sélectionne la carte.
- [x] Banc serveur — preuve : `test_etiquettes_qr_web.py` VERT ; routes ci-dessus ; env inconnu -> 404 (introuvable,
  pas 400) ; POST sans en-tête anti-CSRF -> 403 ; `GET /persist` de la cuve -> aucune de ses valeurs secrètes dans la
  réponse. Écart : banc écrit juste après le serveur, sans passage au rouge ; seul échec du 1er passage = cas « trop
  dense » mal construit par le banc, corrigé
- [x] Serveur et routes ; banc VERT — preuve : `test_etiquettes_qr_web.py` VERT (CSRF 403, autre origine 403, corps
  trop gros ou négatif 400, `/impression` élément nul 400, écriture 409 sur build et sur empreinte périmée)
- [x] En-tête — preuve : `test_etiquettes_qr_page_chrome.py` VERT (« changement de carte : confirmation demandee »,
  « interrupteur : sombre -> clair -> sombre ») ; liste déroulante des envs (`lieux.remplitParLieu`) qui change de
  carte sans recharger la page (URL `?env=` mise à jour ; modifications non écrites -> confirmation avant de changer) ;
  bouton Sombre / Clair, choix mémorisé par `localStorage` sous try/catch, thème du système par défaut
- [x] Page selon le modèle A — preuve : `test_etiquettes_qr_page_chrome.py` VERT et ses captures clair/sombre ; relue par l'agent relecteur-pages-web (2 défauts d'état corrigés : diff périmé retiré à toute modification, succès d'écriture jamais affiché comme refus). Écarts : flèches au lieu du glisser, filtre du persist en liste à plat (pas d'arbre), puce affichée après le nom (homonymes P4/S3), Imprimer/PNG/SVG en A5, Téléverser en A7 ;
  (`outils_docs/etiquettes_qr/modele-A.png`, `modele-A-sombre.png`) : aperçu dessiné par la bibliothèque, texte lu à côté, compteur d'octets,
  verdict coloré, ajout de ligne (standard, arbre du persist, libre), ordre par flèches, « Entre les lignes » (saut de ligne, « · », « | »), style, image (PNG/SVG/JPEG de
  `outils_docs/etiquettes_qr/images/`), case « Page sur la carte » (absente pour un ESP8266), onglet « Gabarit commun »,
  diff avant écriture
- [x] Sonde Chrome hermétique — preuve : `test_etiquettes_qr_page_chrome.py` VERT, 16 contrôles, 0 Chrome `sonde_qr_` vivant après ; en plus du prévu : XSS d'une ligne libre, diff retiré après modification, écriture complète dans la copie. Écart : ajout d'une clé du persist non cliqué par la sonde (route couverte par le banc) ;
  bascule Sombre / Clair par le bouton, changement d'env par la liste (réglage de
  l'autre carte affiché, confirmation si modifié), ajout d'une clé du persist, verdict qui change avec la taille,
  nombre de modules de la bibliothèque = `modules` de `verdict` pour trois textes, aucune erreur console, Chrome arrêté
  à la fin
- [x] Brique de l'annuaire (:7600) — preuve : bancs `test_annuaire.py` et `test_annuaire_lanceur.py` VERTS, tuile vue par l'utilisateur dans la page 7600 le 2026-11-12 ; outil `etiquettes_qr` dans `annuaire_registre.py` (titre « Étiquettes QR code »,
  description courte et longue sur le modèle des autres outils, groupe Maintenance, `_port("http", 7970)`, `lieu=True`,
  arrêt libre : rien n'est écrit sans « Écrire dans le dépôt ») ; la tuile lance l'outil, son lien « Ouvrir » porte
  `?lieu=` ; bancs `test_annuaire.py`, `test_annuaire_lanceur.py` VERT ; vérifié dans la page de l'annuaire
  (bancs VERTS le 2026-11-12, compte du banc passé à 14 outils ; reste : tuile vue dans la vraie page 7600)
- [x] Tâche VS Code et cible Custom détachée — preuve : `build/test_cible_etiquettes_qr.py` VERT, `build/test_garde_build.py` VERT ; barres obliques simples du sous-agent corrigées (tasks.json, docstring de la cible, `\f` de `annuaire_registre.py`)
- [x] Commit — preuve : `3c0bd2736`

## A5 — Impression, planche A4, export
Fichiers : créer `outils_pc/etiquettes_qr_page_impression.py` (JS et CSS `@media print`) ; modifier
`etiquettes_qr_page.py`, `test_etiquettes_qr_page_chrome.py`.
Consomme : A4 (`POST /impression`).
- [x] Bouton « Imprimer » — preuve : sonde « Imprimer : une feuille, un QR code de 25 mm, regle de 50 mm », « impression notee », « Annuler la note » ; media print mesuré à 94,5 px CSS = 25 mm ; page d'impression `@page { size: A4 }`, QR code en `mm`, consigne « échelle
  100 % » affichée ; `window.print()` ; impression notée par `POST /impression`, « Annuler la note » disponible.
  Ajouts : règle de 50 mm en bas de la 1re feuille ; fond blanc forcé à l'impression (le thème sombre peignait les marges) ;
  annuler la note d'une RÉimpression remet la note précédente (`note_impression` la rend, le serveur la garde en mémoire ;
  bancs `test_etiquettes_qr_ecriture.py` et `test_etiquettes_qr_web.py`), relevé par l'agent relecteur-pages-web
- [x] Planche — preuve : sonde « planche 12 cartes a 25 mm » (grille 6 × 7, 1 page) et « a 70 mm » (2 × 3, 2 pages), PDF `Page.printToPDF` relu ; cases des cartes, une taille pour toute la planche (celle du gabarit par défaut), grille automatique (marges 10 mm, espacement 5 mm,
  traits de coupe fins), petit nom en option, autant de pages que nécessaire ; sonde : 12 cartes à 25 mm -> nombre de
  pages et de codes attendu, sans impression réelle. Écarts : petit nom = nom d'env sans préfixe, puce ajoutée aux
  homonymes, sur 2 lignes (7 mm réservés) ; carte sans aucune ligne lisible refusée avec la raison, jamais un QR vide ;
  « Planche d'essai » ajoutée (carte affichée à 15, 20, 25, 30 mm, texte court et long, avec/sans image ; jamais notée)
- [x] Export PNG et SVG — preuve : sonde « export PNG et SVG de la cuve » (image/png, image/svg+xml) ; `getRawData`, nommé `qr_<env>.png|svg`, PNG à 300 points par pouce de la taille réglée
- [x] Essai réel avec l'utilisateur — preuve : « 15mm, c'est ok » (2026-11-12, iPhone, planche d'essai) ; seuils de
  `etiquettes_qr_verdict.py` recalés à 0,45 mm lisible (15 mm texte court = 25 modules) et 0,35 mm limite ;
  `test_etiquettes_qr_verdict.py` VERT avec le point d'essai. Planche aux tailles 15, 20, 25, 30 mm, texte court et texte long, avec et
  sans image ; scan au téléphone ; seuils de `verdict` recalés d'après le résultat (banc A2 mis à jour).
  Texte long (33 modules) : lu à 20 mm (0,49 mm), pas à 15 mm (0,37 mm) -> seuil « limite » relevé à 0,40 mm.
  Écart : entre 0,40 et 0,45 mm rien n'est essayé, la zone « limite » reste une estimation.
  Corrigé au passage : perte du focus à chaque lettre (l'aperçu redessinait les lignes ; `majValeursLignes`, sonde avec
  témoin rouge) ; champ standard « Range extender » (SSID du point d'accès, proposé si `rangeExtender.activation` = ON)
- [x] Commit — preuve : `6a0739ae4` (impression, planche, export), `17e83cb30` (focus, range extender), `93e24302f` (seuils)

## A6 — Page `/qrcode` de la carte
Fichiers : créer `data/fs/qrcodePage.be` (driver posé à l'import, route `/qrcode`, bouton d'accueil « QR code »,
`?f=lib.js.gz`, `?f=etat` -> `{"ip": <IP réelle>, "hostname"}` ; rien chargé si `/json/qrcode.json` est absent ;
solidifiable : aucun état dans le module), `data/sd/html/qrcode.html`, `data/sd/css/qrcode.css`, `data/sd/js/qrcode.js`,
`data/sd/js/qr-code-styling.min.js.gz` (`gzip -9 -n` du `.js` de l'A1, sha256 attendu dans `lib/LISEZMOI.md`) ;
`outils_docs/scripts_python/berry/banc_qrcode_page.py` + `.be` (+ bouchons) ; `outils_pc/test_qrcode_carte_chrome.py` ;
modifier `platformio_tasmota_cenv.ini` (liste `etiquette_qr` de `[berry_commun]` : les 4 fichiers de `data/sd` ;
exclue de tous les envs ESP32 ; entrée de `globs` de `solidify_all_python.be` si une globale est créée).
Consomme : `fichier_carte` (A2), A3 pour poser l'env d'essai.
- [x] Banc Berry d'abord (rouge) — preuve : `berry/banc_qrcode_page.py`, témoins rouges ; route servie avec `qrcode.json`
  présent ; absent -> pas de bouton, pas de route ; `?f=etat` rend l'IP du bouchon ; charte des logs sans avertissement ;
  23 contrôles Berry + bibliothèque reçue octet par octet, empreinte ; témoins `--sources` sur copie : sans `path.exists` dans init
  -> ECHEC (2), sans `check_privileged_access` -> ECHEC (3)
- [x] Module et page ; banc VERT ; `verifie_berry.py` VERT — preuve : `data/fs/qrcodePage.be` (routes `?f=lib.js.gz`,
  `?f=reglage` par morceaux, `?f=etat`), `data/sd/{html,css,js}/qrcode.*`, `qrcode_options.js` partagé avec l'outil
  (`etiquettes_qr_page_js.py::OPTIONS`) ; `BANC_QRCODE_PAGE: OK`, verifie_berry 0 erreur 0 avertissement ; relecteur-berry
  sans bloquant ; liste `etiquette_qr` posée et exclue des 19 envs ESP32 (`ecrit_exclusions`, second calcul vide),
  `banc_demarrage.py` VERT ; bancs `test_etiquettes_qr_*` et sonde de l'outil VERTS
- [x] Sonde Chrome de la page — preuve : `outils_pc/test_qrcode_carte_chrome.py` VERT ; serveur local imitant la carte :
  QR code dessiné avec le style du fichier ; IP inscrite différente sans port -> avertissement ; IP inscrite
  `192.168.0.51:8081` -> aucun avertissement (vigilance 1) ; mode sombre lisible (page du vrai module par
  `banc_qrcode_page.py --garde`, 15 contrôles : modules = verdict, couleur du style, IP .61 / IP:port / sans IP, texte
  hostile, bibliothèque demandée 1 fois en 5 chargements, thème sombre, réglage absent -> 404 affiché)
- [x] Essai sur une carte choisie par l'utilisateur — preuve : essai fait par l'utilisateur sur le P4 (tasmota32p4-garage-serveur-modbus), confirmé le 2026-11-12 et le 2026-11-13 ; vérifié sur la carte : bouton dans Outils, texte sur plusieurs lignes aligné sur le QR code, heap_free stable à 242 Ko ; réglage écrit par la page 7970, firmware recompilé et FS envoyé
  par la page Build, QR code de la carte scanné = QR code de l'outil ; RAM libre avant/après notée
- [x] Commit — preuve : commits 0794f504a, 0028bfa1a, e75b442e2, 8c7d0409f

## A7 — Suivi des changements, téléversement, liens des autres outils
Fichiers : créer `outils_pc/etiquettes_qr_suivi.py`, `test_etiquettes_qr_suivi.py` ; modifier
`etiquettes_qr_web.py` (`GET /etat?env=`, badges de `/cartes`), `etiquettes_qr_page_js.py` (badges, bouton
« Téléverser »), `build_page_atelier.py` (accepter `depuis=qrcode`), `fichiers_berry_renommage.py`,
`assistant_persist_modification.py` (message de fin).
Produit : `etats(racine, env, *, get=None) -> {"a_reimprimer": bool, "a_regenerer": bool, "carte": "a_jour"|
"a_mettre_a_jour"|"inconnu"|"sans_page"}` (lecture de `/json/qrcode.json` sur la carte, adresse par
`adresse_par_maitre` pour un esclave, délai 2 s) ; `lien_si_regle(racine, env) -> str | None`
(`http://127.0.0.1:7970/?env=<env>` si `cartes/<env>.json` existe).
- [x] Bancs d'abord (rouge) — preuve : test_etiquettes_qr_suivi.py (commit 8c7d0409f) ; hostname changé dans le persist -> `a_reimprimer` et `a_regenerer` ; topic changé et
  absent du gabarit -> aucun des deux ; carte simulée qui rend un autre `qrcode.json` -> `a_mettre_a_jour` ; carte muette
  -> `inconnu` en moins de 3 s (vigilance 5)
- [x] Module, routes, badges ; bancs VERT — preuve : commit 616280eea, bancs ecriture/web/suivi VERT, sonde test_etiquettes_qr_page_chrome.py VERT
- [x] « Téléverser » — preuve : commit 5865bff17, sondes test_etiquettes_qr_page_chrome.py VERT et test_build_page_fichiers_chrome.py (cas qrcode OK ; autres cas instables avant ce commit, attentes fixes de 2,5 s) ; chemin réel `fichiers=qrcode.json&redemarrer=1` (racine du FS, rangé dans /json/ au démarrage) ; URL de la page Build `?env=&depuis=qrcode&fichiers=/json/qrcode.json&redemarrer=0` (sur le modèle
  de `atelier_graphiques_televerse.url`) ; sonde `test_build_page_fichiers_chrome.py` VERT
- [x] Lien « Étiquette QR à refaire » — preuve : commit 24f099d11, test_fichiers_berry_renommage.py VERT, sonde test_fichiers_berry_page_chrome.py VERT, test_assistant_persist_modification.py (2 contrôles étiquette OK ; seul KO « cartes_du_parc : champs », antérieur, champ lieu) ; dans le message de fin d'un renommage (Fichiers Berry) et d'une modification
  (assistant persist) ; leurs bancs VERT
- [x] Régénération au build — preuve : commit 135af711a, build/test_qrcode_build.py VERT, buildfs du P4 par la page Build SUCCESS (qrcode.json inchangé, déjà à jour) (demande du 2026-11-12) : le pré-script (`build/pre_utilitaires_platformio.py`), avant
  chaque `buildfs` (et upload série qui écrit le FS), recalcule le texte de `cartes/<env>.json` contre le persist et le
  `.h` du moment ; s'il diffère du `qrcode.json` du dossier de la carte, il le réécrit (même `fichier_carte`) et
  l'étiquette passe « à réimprimer » ; une ligne `QR code de <env> : régénéré` dans la sortie de pio. Rien si l'env n'a
  pas de `cartes/<env>.json` ; une erreur de lecture n'arrête jamais le build (ligne d'avertissement). Module neuf
  `build/qrcode_build.py` (+ `test_qrcode_build.py`, rouge d'abord : persist changé -> réécrit ; inchangé -> fichier
  intact, date comprise ; env sans réglage -> rien ; persist illisible -> build continue)
- [x] Commit — preuve : commits 8c7d0409f, 616280eea, 5865bff17, 24f099d11, 135af711a

## A8 — QR code à l'écran des cartes (après l'atelier des écrans)
Fichiers : modifier `outils_docs/schemas/catalogue_ecran.json` (objet `qrcode`), les générateurs
`atelier_ecrans_haspmota.py` et `atelier_ecrans_lvgl.py`, leurs bancs.
Consomme : `tasks/plans/atelier-ecrans.md` A4 et A5 faits ; `/json/qrcode.json` (A6).
Décision du 2026-11-14 (utilisateur) : bouton en SURIMPRESSION ; la page « QR code » (page 5, A16 d'atelier-ecrans, déjà faite sur l'écran
des débits) est RETIRÉE une fois le bouton en place. Plan : aucun changement de générateur, l'objet `qrcode` existe (palier 2). Sur la page 0
(layer_top) : un bouton « QR code », un fond blanc et un `qrcode` cachés (`hidden`), visibilité pilotée par une valeur du modèle de la carte
(`qr.visible`, minuterie `delai_s` côté `ecranDebitsFonctions`), rendue par les deux interfaces. À faire builds arrêtés (écriture de `data/`).
- [ ] Objet `qrcode` du catalogue : bouton qui affiche le QR code en surimpression pendant `delai_s` (défaut 30), texte
  lu dans `/json/qrcode.json` à l'appui, noir sur blanc sans style riche ; HASPmota `"obj":"qrcode"` (`qr_text`,
  `qr_size`), LVGL `lv.qrcode`
- [ ] Bancs des deux générateurs VERT avec l'objet ; essai sur l'écran des débits, scan au téléphone
- [ ] Commit

## A9 — Documentation
- [x] `outils_docs/README.md` § « Étiquettes QR code (page web) » — preuve : commit 37e8bceb2, relu par la skill ecriture-naturelle ; usage, verdict, impression à 100 %, planche, page de
  la carte, suivi
- [x] `CLAUDE.md` (carte des documents) — preuve : commit 37e8bceb2, `verifie_references_docs.py` : 0 défaut ; modules `etiquettes_qr_*`, `qrcodePage.be`, liste `etiquette_qr`, bancs ;
  `verifie_references_docs.py` VERT
- [x] Commit — preuve : commit 37e8bceb2 ; plan laissé `statut: actif` tant que l'A8 et l'A10 restent ouvertes

## A10 — Fiches en ligne (GitHub Pages) et filtre durci
Décidé le 2026-11-12 : au choix par carte, le QR code contient le texte (défaut, hors réseau) OU un lien fixe vers une
fiche HTML publique, lisible partout (4G, carte éteinte, ESP8266 compris) et mise à jour sans réimprimer l'étiquette.
Fiches PUBLIQUES (accepté par l'utilisateur). Hébergement : branche orpheline `etiquettes` du dépôt Tasmota (aucun
fichier de Tasmota dedans, `development` et la synchro du fork intacts), servie par GitHub Pages :
`https://<propriétaire>.github.io/<dépôt>/<env>.html`, adresse tirée de `git remote get-url origin`.
Rien n'est stocké sur `development` en plus des réglages existants (`outils_docs/etiquettes_qr/cartes/*.json`) : les
fiches sont regénérées à chaque publication. Branche écrite par la plomberie git (`hash-object`, `mktree`,
`commit-tree`, `push origin <sha>:refs/heads/etiquettes`), sans checkout : l'arbre de travail n'est jamais touché.
Fichiers : créer `outils_pc/etiquettes_qr_publication.py`, `outils_pc/etiquettes_qr_filtre_public.py`,
`test_etiquettes_qr_publication.py`, `test_etiquettes_qr_filtre_public.py` ; modifier `etiquettes_qr_modele.py`
(clé `contenu`: `"texte"|"lien"` validée), `etiquettes_qr_web.py` (`POST /publication/diff`, `POST /publier`),
`etiquettes_qr_page_js.py` (réglage « Contenu du QR code », bouton « Publier… », adresse de la fiche),
`test_etiquettes_qr_web.py`, `test_etiquettes_qr_page_chrome.py`.
Produit : `controle_public(valeur: str) -> str | None` (raison du refus) ; `fiche_html(racine, env, reglage) -> str` ;
`url_fiche(racine, env) -> str` ; `prevoit_publication(racine, envs) -> {"fichiers", "refus", "empreinte"}` ;
`publie(racine, envs, empreinte, builds_en_cours) -> sha`.
- [x] Banc du filtre d'abord (rouge), avec mutants — preuve : `test_etiquettes_qr_filtre_public.py` VERT, 6 mutants rouges (un par règle) ; rouge d'abord sur `2a01:cb00::1:` et `sk-proj-…` ; refus d'une valeur portant des identifiants d'URL (`://x:y@`), un
  paramètre `token=`, `key=`, `apikey=`, `password=`, `pass=`, `pwd=`, `secret=`, `auth=`, `sig=` (casse indifférente) ;
  une IPv4 non privée (hors 10/8, 172.16/12, 192.168/16, 127/8, 169.254/16) ; une IPv6 globale ; un nom de domaine
  joignable (hors `.local`, `.lan`, `.home.arpa`, nom sans point) ; une chaîne de 20 caractères ou plus sans espace à
  allure de clé (base64 ou hexadécimal) ; acceptés : hostname, IP privée avec ou sans port, topic, valeurs ordinaires
- [x] Filtre ; banc VERT ; appliqué en plus du filtre de l'A2 (clé ET valeur), avertissement dans l'aperçu, refus à la publication avec la raison — preuve : `etiquettes_qr_publication.py::refus_de` (ligne nommée par son numéro, valeur jamais recopiée : défaut trouvé par le banc), avertissement de `etiquettes_qr_web.py::apercu` ; `test_etiquettes_qr_publication.py` et `test_etiquettes_qr_web.py` VERTS (ligne `token=` : refus, branche inchangée)
- [x] Fiche HTML autonome — preuve : (aucune ressource externe, CSS en ligne, clair/sombre par `prefers-color-scheme`,
  `<meta name="robots" content="noindex">`, textes échappés, date de publication ; `.nojekyll` ; banc : `<script>` dans
  une valeur libre rendu en texte) `etiquettes_qr_publication.py::fiche_html`, banc VERT (`&lt;script&gt;`, ni src ni href) ; même fiche un autre jour : gardée telle quelle (pas de nouvel envoi quotidien)
- [x] Réglage « Contenu du QR code » : en mode lien, QR code = `url_fiche` (verdict sur l'URL), proposé pour toute carte — preuve : `etiquettes_qr_modele.py::resout_avec` (adresse pour tous les appelants : écriture, suivi, build, impression ; origin hors GitHub = erreur, jamais un retour discret au texte), sélecteur « le QR code contient » (`etiquettes_qr_page_publication.py`) ; sonde Chrome VERTE deux fois (le téléphone lirait l'adresse)
- [x] Publication : diff des fiches avant envoi, bouton « Publier » distinct d'« Écrire », refus pendant un build — preuve : routes `POST /publication/diff` et `/publier`, bouton « Publier les fiches… » ; `test_etiquettes_qr_publication.py` VERT sur un origin nu local (URL lue github.com réécrite par `insteadOf`) : arbre de travail, index et `development` identiques, branche orpheline, fiche retirée au prochain envoi par-dessus la pointe ; entrée de git passée en octets (Windows changeait `\n` en `\r\n` dans l'arbre, défaut trouvé par le banc) ; sonde Chrome : écriture en lien puis publication complète ;
  banc sur un dépôt temporaire avec un `origin` nu : seule `refs/heads/etiquettes` change, `development` et l'arbre
  de travail identiques avant/après, carte retirée -> fiche retirée au prochain envoi
- [x] Relecture (agent relecteur-pages-web, opus) puis corrections — preuve : bloquant B1 corrigé (le filtre des secrets du persist voyait seulement les lignes `persist` : une ligne libre ou un texte « avant » portant un mot de passe partait sur la fiche ; désormais toute la ligne, `etiquettes_qr_publication.py::lignes_publiees`, témoins et mutants dans `test_etiquettes_qr_publication.py`) ; filtre élargi (access_token=, api_key=, JWT, jeton Telegram, AWS, Slack, mots annonciateurs : banc à 7 règles, 7 mutants rouges) ; raisons sans valeur ; titre de la fiche = env ; git sans invite d'identifiants, délai de 120 s, verrou de publication à part, jeton d'URL retiré des messages ; `update-ref` après push sans effet sur le résultat ; tests « branche bougée ailleurs » et « origin injoignable » ; mode d'emploi `outils_docs/README.md` § « Fiche en ligne (mode lien) »
- [x] Mise en service par l'utilisateur, une fois : Settings > Pages > Source « Deploy from a branch », branche
  `etiquettes`, dossier `/ (root)` — preuve : `GET /pages` de la page 7970 = actif, branche etiquettes ; fiche de la cuve en HTTP 200 sur fdaubercy.github.io le 2026-11-14
- [ ] Essai réel : une carte publiée, QR code en mode lien imprimé, scanné au téléphone en 4G
- [ ] Commit

## A11 — Publication des fiches automatisée (page 7970, build)
Demandé le 2026-11-13 (« automatiser sur la page dédiée, ou après une compilation si une case est cochée ») : les trois
pistes retenues par l'utilisateur, envoi après build compris malgré mon avis (public, sans diff).
Produit : `etiquettes_qr_publication.py::fiche_a_republier(racine, env, cartes=None) -> bool` (sans réseau : réf locale
`refs/remotes/origin/etiquettes`, date ignorée ; carte repassée en texte dont la fiche est en ligne = vrai),
`::etat_pages(racine) -> {"actif", "url"}` et `::active_pages(racine)` (par `gh api`, jamais d'invite),
`::publie_tout(racine, builds_en_cours) -> sha | None` (prévoit puis publie, refus = RuntimeError).
- [x] Bancs d'abord (rouge) : `fiche_a_republier` (fiche absente, identique, autre jour, contenu changé, carte repassée en texte), `publie_tout` (refus, rien à faire), `etat_pages`/`active_pages` avec un faux `gh` — preuve : `test_etiquettes_qr_publication.py` (`test_suivi_et_tout`, `test_pages`) rouge (fonctions absentes) puis VERT
- [x] Page 7970 : bouton « Activer GitHub Pages » tant que Pages est inactif ; après « Écrire » d'une carte en mode lien,
  enchaînement sur le diff des fiches ; badge « fiche à republier » (route `/suivi`) ; banc serveur et sonde Chrome — preuve : `test_etiquettes_qr_web.py` (`test_publication`) et `test_etiquettes_qr_page_chrome.py` (`sonde_publication`) VERTS le 2026-11-14, commit 9920699e9
- [x] Signal après build : `build/qrcode_build.py` écrit « Fiche QR de <env> à republier » dans la sortie de pio — preuve : `build/qrcode_build.py::fiche`, branché dans le pré-script (édité hors build, vérifié) ; `build/test_qrcode_build.py` VERT (4 cas fiche)
- [x] Envoi après build : case « Publier les fiches QR à la fin » de la page Build, publication après une série réussie,
  résultat dans le journal ; refus et erreurs n'échouent pas la série ; bancs de la page Build et sonde — preuve : `test_build_serie.py::test_publication_fiches` et `test_build_page_chrome.py` VERTS, commit 9920699e9
- [x] Relecture (agent) puis commit — preuve : relecture faite (correctifs : série non réussie, un seul fetch, builds indétectables = refus), commit 9920699e9

## Améliorations restantes

## Vérification
Fin du chantier : un QR code réglé dans la page 7970, imprimé sur planche et scanné au téléphone ; le même affiché par
`/qrcode` d'une carte et scanné ; un hostname changé dans le dépôt fait apparaître « à réimprimer » ; aucune valeur
secrète dans les réponses du serveur (banc A4).
