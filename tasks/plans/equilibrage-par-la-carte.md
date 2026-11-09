---
chantier: equilibrage-par-la-carte
titre: Page d'équilibrage de la nourrice servie par la carte des débits, débits lus en direct
statut: actif
cree: 2026-11-09
maj: 2026-11-09
source: graceful-orbiting-pudding.md
objectif: Ouvrir le guide d'équilibrage depuis la carte des débits et y lire les 6 débits mesurés, sans les taper à la main
---
# Page d'équilibrage servie par la carte des débits

## Contexte
Le guide animé `outils_docs/chauffage/equilibrage_pas_a_pas.html` (artifact https://claude.ai/artifact/6oyWDPZEAhjo5btUxs6BL7)
fait taper à la main les 6 débits mesurés. Depuis claude.ai (HTTPS), le navigateur refuse d'interroger une carte du réseau
local en HTTP ; servie **par la carte elle-même**, la page lit ses débits sans CORS ni réglage réseau (choix de
l'utilisateur, 2026-11-09). Plan parent : `tasks/plans/debitmetres-chauffage.md`.

Décisions de conception (à contester avant le feu vert) :
- **Un seul fichier** pour l'artifact et la carte : déplacé dans le dossier de la carte, `equilibrage.html`. Au démarrage,
  `gestionFileFolder.be::listeEtRepartitLesFichiers` le range dans `/sd/html/` : il ne part que sur cette carte, aucune
  exclusion à ajouter aux autres envs. L'artifact est republié depuis ce chemin (même URL, `url` passé).
- **Page autonome**, pas dans le cadre de Tasmota : la route envoie `<!doctype html>`, charset, viewport et
  `window.CARTE`, puis le fichier. Sans `window.CARTE` (artifact, fichier local), la page reste celle d'aujourd'hui.
- **Module à part** `equilibragePage.be` (dossier de la carte, compilé en `.bec` par l'autoexec, importé à la première
  requête, sans état) : `debitsFonctions.be` fait déjà 452 lignes. Patron : `data/fs/cuvePageFonctions.be` (route,
  `webserver.check_privileged_access()`, `window.X` échappé `</`), `controleCuve.be::web_add_handler`,
  `controleEnergie.be::web_add_main_button`. Envoi du fichier par `gestionFileFolder.readFileByLineAndContentSend`.
- Aucune recompilation du firmware : modules du dossier de la carte, ni solidifiés ni dans `data/fs`. Envoi du FS seul.
- Polices Google : chargées par le téléphone s'il a Internet, sinon polices du système (déjà prévues en repli).

## A1 — Un seul fichier, déplacé dans le dossier de la carte
- [x] `git mv outils_docs/chauffage/equilibrage_pas_a_pas.html data/bureau/tasmota32s3-serveur-debits-pac/equilibrage.html` ; renvois mis à jour (`outils_docs/README.md`, `CLAUDE.md`, guide `EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`, plan des débits) ; `verifie_references_docs.py` 0 défaut — preuve : fichier déplacé (`git mv`), renvois du README, du `CLAUDE.md` et du guide `.md` mis à jour ; `verifie_references_docs.py` : 20 documents, 0 défaut ; la preuve du plan des débits garde l'ancien chemin (trace)
- [x] Artifact republié depuis le nouveau chemin, même URL — preuve : version 3 de https://claude.ai/artifact/6oyWDPZEAhjo5btUxs6BL7, publiée depuis `data/bureau/tasmota32s3-serveur-debits-pac/equilibrage.html`

## A2 — Route /equilibrage sur la carte
- [x] `equilibragePage.be` : `/equilibrage` → page (préfixe doctype + `window.CARTE` = noms des 6 départs, fenêtre de mesure, nom de la carte) ; `/equilibrage?f=debits` → JSON `{debits[6], total, noms[6], muets, imprecis, fenetre, age_s}` ; accès privilégié comme `/cuve` ; logs selon la charte (`debug` à la requête, `erreur` si `/sd/html/equilibrage.html` absent) — preuve : `data/bureau/tasmota32s3-serveur-debits-pac/equilibragePage.be` ; banc `banc_debits.py` section « page /equilibrage » (JSON, CARTE, 404, exception) VERT, 95 vérifications, 6 témoins de la page rouges
- [x] `controleDebits.be` : `web_add_handler` (route, import à la première requête) et bouton d'accueil « Équilibrage » — preuve : `controleDebits.be::web_add_handler`, `pageEquilibrage`, `web_add_main_button` ; banc : route déclarée et servie, bouton vers /equilibrage
- [x] `autoexec.be` de la carte : `equilibragePage` compilé avec `debitsFonctions` ; `banc_demarrage.py --carte` relu, référence ré-enregistrée (3 fichiers compilés, sur une copie de `data/fs` du commit) — preuve : `demarrage.compile(["debitsFonctions", "equilibragePage"], "modules.debits")` ; écart relu (compiles 3, +6 globales des fonctions du module, drivers et erreurs inchangés), référence ré-enregistrée sur une copie de `data/fs` du commit ; `--carte` VERT aussi sur le `data/fs` de travail

## A3 — La page en mode carte
- [x] Bouton « Lire les débits de la carte » : 6 débits mesurés remplis, noms des départs repris dans l'estimateur et le calculateur — preuve : `test_equilibrage_page_chrome.py` VERT : lecture au chargement et au clic, 6 débits remplis (voie sans mesure vide), noms repris en texte brut dans les libellés, l'estimateur et le tableau (`esc`)
- [x] Case « Suivre en direct » : relecture toutes les `fenetre` s, arrêtée onglet caché (`visibilitychange`), heure de la dernière mesure affichée ; capteur muet et débit imprécis signalés sur la ligne du départ — preuve : `test_equilibrage_page_chrome.py` VERT : lecture toutes les 2 s (fenêtre de la carte), aucune lecture onglet caché, reprise au retour ; « muet ? » et « imprécis » sur la ligne du départ et dans l'état ; erreur 500 → « Lecture impossible »
- [x] Débit de la PAC laissé vide = total mesuré des 6 départs (indiqué sous le champ) — preuve : `test_equilibrage_page_chrome.py` VERT : PAC vide → cible totale = total mesuré (11,0 L/min) ; note sous le champ
- [x] Hors carte (artifact, fichier local) : ni bouton ni case, page inchangée — preuve : `test_equilibrage_page_chrome.py` VERT : sans `window.CARTE`, zone cachée, exemple du guide, aucune lecture

## A4 — Bancs et relectures
- [x] Banc Berry de la route (`banc_debits.py` ou banc voisin, faux `webserver`) : JSON (valeurs, noms, capteur muet), préfixe de la page (`</` échappé), refus sans accès privilégié, fichier absent → erreur ; témoins rouges lus — preuve : `banc_debits.py` VERT, 96 vérifications (f=debits, page, CARTE échappé, 404, exception d'envoi, mesures illisibles → 500), 7 témoins de la page rouges
- [x] Sonde Chrome hermétique (faux serveur local qui sert la page et un faux `?f=debits`) : lecture, suivi direct, page à 360 px ; hors carte : aucun bouton — preuve : `outils_docs/scripts_python/outils_pc/test_equilibrage_page_chrome.py` VERT (18 vérifications, 360 px, polices Google bloquées) ; témoin : page sans sa lecture au chargement → 8 KO
- [x] `verifie_berry.py` sans erreur ni écart ; agents `relecteur-berry` et `relecteur-pages-web`, remarques traitées — preuve : `verifie_berry.py` 0 erreur 0 écart ; `relecteur-berry` : prêt, 1 point (JSON calculé avant d'ouvrir la réponse) corrigé ; `relecteur-pages-web` : 4 points corrigés (une lecture à la fois et délai de 5 s ; sonde : estimateur, erreurs par phase, largeur hors carte, docstring)
- [x] Commit et push — preuve : `1e9b6c9cf` (deplacement seul, par erreur) puis `9719c6ac0` (13 fichiers), pousses

## A5 — Sur la carte (avec le matériel)
- [ ] FS envoyé par la page Build ; bouton « Équilibrage » de l'accueil ouvert depuis le téléphone ; « Lire les débits » = valeurs de l'accueil ; suivi direct ; tas mesuré avant et après la première ouverture

## Améliorations restantes
- [ ] [projet] Schéma animé alimenté par les débits réels pendant le suivi direct
- [ ] [projet] Puissances des radiateurs gardées sur la carte (aujourd'hui dans le navigateur du téléphone)
- [ ] [projet] Signet du téléphone vers /equilibrage : refusé sans Referer par l'accès privilégié ; passer par l'accueil, ou alléger le contrôle pour cette page en lecture seule

## Vérification
- PC : banc Berry vert avec témoins, sonde Chrome verte, `banc_demarrage.py --carte tasmota32s3-bureau-serveur-debits-pac` vert.
- Carte : la page s'ouvre depuis l'accueil, les 6 débits lus sont ceux de l'accueil, le suivi se rafraîchit à la cadence de la fenêtre.
