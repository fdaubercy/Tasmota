# Exceptions a la regle des 500 lignes

Tire de `CLAUDE.md` le 2026-11-23 (plan `binomes-berry`, A11). Avant de proposer de decouper un fichier
de plus de 500 lignes, le chercher ici : une exception listee est une decision de l'utilisateur. Nouvelle exception = une
entree ici, datee, avec la raison.

## Exception assumee a la regle des 500 lignes

`outils_docs/scripts_python/maintenance/synchronise_fork_tasmota.py` fait **560 lignes**, et
c'est **voulu** (decide le 2026-07-15, a 527 lignes ; +7 le 2026-10-12 pour le correctif
du blocage sur son propre journal ; +24 le 2026-10-17 pour la confirmation et le
controle d'arbre propre AVANT la synchro distante, et les questions de la page web ; +2 le
2026-10-27 pour le journal ecrit par l'assistant de la page web, `noter_historique(historique=)`).
Ne pas le decouper pour satisfaire le compteur.

Decomposition reelle : 345 lignes de code, 59 d'en-tete docstring (qui **est** la
sortie de `--help`), 105 vides, 49 de commentaires. La plus grosse fonction (`main`)
fait 92 lignes. L'esprit de la regle — un fichier qui n'en fait pas trop — est respecte ;
seul le total brut deborde, de 58 lignes de documentation et de blancs.

Extraire un module d'utilitaires partages avec `synchronise_upstream_tasmota.py`
reste possible **le jour ou un troisieme script apparaitra**, pas avant.

`outils_docs/exemples de scripts BERRY/test_liaison_modbus.be` fait **613 lignes**, et
c'est **voulu** (decide le 2026-10-04 : « laisse ce test comme il est »). Ne pas le
decouper : c'est UN fichier a televerser sur chaque carte, qui se prepare et s'explique
seul au chargement ; le scinder imposerait deux televersements par carte.

`data/fs/energieFonctions.be` fait **607 lignes**, et c'est **voulu** (decide le 2026-11-09 : exception plutot
qu'un decoupage ; 531 lignes avant le palier 4 de l'atelier, +57 pour les routes de lecture `f=description`, `f=mois`,
`f=direct`, +10 pour le relais par morceaux, +8 le 2026-11-12 pour `enregistre` : page sans enregistrement en flash). Module SOLIDIFIE du differentiel (sans PSRAM) : comptage, stockage et
routes de la page `/energie` restent ensemble (spec `2026-11-08-atelier-energie-differentiel-design.md` §6.3) ; un
second module solidifie ajouterait une entree de `custom_berry_solidify` et de l'autoexec pour rien.

`data/fs/vrFonctions.be` fait **910 lignes**, et c'est **voulu** (decide le 2026-11-12 : exception plutot qu'un
decoupage). Fonctions des volets roulants (sens physique, boutons, inclinaison MPU6050, facade, garde du reglage),
appelees par `controleVoletRoulants.be` et `vrReglage.be` (plan `tasks/plans/visuel-reglage-volets.md`).
Meme decision, meme jour, pour leurs bancs : `outils_docs/scripts_python/berry/banc_reglage_volets.be` (**875 lignes**,
+108 le 2026-11-13 : fins de course et camera de la facade) et `banc_inclinaison.be` (**729 lignes**) ; un banc par module,
chaque groupe lisible seul. Meme decision le 2026-11-13 (plan `tasks/plans/facade-garage-capteurs.md`) pour
`data/sd/js/volets.js` (**971 lignes**, +11 le 2026-11-15 : constantes NUIT et PORTAIL_DECALAGE (voile plus sombre, vantail droit 5 s avant le gauche), capteur de fermeture suivant le vantail gauche, cones elargis jusqu'au sol, cone de la camera de la maison, pourcentage masque ; +1 le 2026-11-15 : voile de nuit et bouton Auto, Jour, Nuit pour le decor `maison` avec `finition` ; +113 le 2026-11-15 : decor et perspective du portail d'apres la maquette validee, pergola a deux arches, haie, grillage ; +281 le 2026-11-15 : finition de la facade, cones de la camera et de la lampe, voile de nuit selon le soleil, portail de jardin, commande par clic ; decors garage et maison, fins de course, rapporteur de la trappe, camera ; le couper
ajouterait un fichier a `volets_pages` du cenv) et sa sonde `outils_pc/test_volets_chrome.py` (**754 lignes**, +20 le 2026-11-15 : captures de nuit et de crepuscule avec camera et lampe ; +50 le 2026-11-15 : scenarios maison et rideau avec la nuit ; +81 le 2026-11-15 : scénarios portail et soleil).

`data/fs/modbusFonctions.be` (**3389 lignes**), `modBus_TasmotaSlaveModBus.be` (**1536**), `udpFonctions.be` (**938**), `globalFonctions.be` (**890**)
et `discoveryFonctions.be` (**894**) depassent **500 lignes**, et c'est **voulu** (decide le 2026-11-14 : exceptions declarees plutot qu'un
decoupage). Modules SOLIDIFIES charges ensemble par les autoexec : les scinder ajouterait des entrees de `custom_berry_solidify` et de l'autoexec
de chaque env. Les copies de `lib/libesp32/berry_custom/src/embedded/` sont GENEREES et ignorees par git : ne pas les compter.
Meme decision le 2026-11-23 pour `data/fs/logFonctions.be` (**553 lignes** : 490 avant `logFonctions.declare`, plus le renvoi de taille du binome).
Meme decision le 2026-11-23 pour `data/fs/controleGeneral.be` (**800**), `ledsFonctions.be` (**672**), `historiqueFonctions.be`
(**645**) et `modBus_Conn16channels.be` (**583**), qui depassaient deja 500 lignes sans etre declares.
Comptes de `data/fs` mis a jour le 2026-11-23 apres les blocs « TAILLE DU BINOME » (plan binomes-berry, A11).

`data/bureau/tasmota32s3-ecran-debits-pac/ecranLvgl.be` depasse **500 lignes**, et c'est **voulu** (decide le 2026-11-13 :
exception plutot qu'un generateur tasse ; 496 lignes avant la page « Systeme » de l'A19, 618 le 2026-11-14). Fichier GENERE par l'atelier des
ecrans (`atelier_ecrans_lvgl.py`) d'apres `ecran.json` : ne pas le decouper ni l'editer a la main, le regenerer. Meme regle pour
l'`ecranLvgl.be` genere de toute autre carte a ecran.

`outils_docs/scripts_python/outils_pc/build_page.py` fait **1256 lignes**, et c'est **voulu**
(decide le 2026-10-24 a 788 lignes : exception acceptee plutot qu'un decoupage CSS/JS ; 813 apres la
vague de corrections finale du meme jour ; 935 le 2026-10-25 avec le panneau « Sortie » et « Effacer puis
televerser » ; 1038 le meme jour avec la pause « rebranchez la carte » et les panneaux refermes ; 1053 avec
l'envoi sans recompiler apres la pause et la pause rouverte ; 1062 avec le lien « fichiers » vers la page
Fichiers Berry par env ; 1083 le 2026-10-26 avec les cases FS grisees quand l'envoi serie du firmware ecrit
deja le FS ; 1131 le meme jour avec les sons de fin de lancement et de pause ; 1153 le 2026-10-29 avec le
branchement de l'onglet « Fichiers », dont le code vit dans `build_page_fichiers.py` ; 1154 le 2026-10-31 avec
les durees en heures au-dela de 60 min ; 1162 le 2026-11-01 avec le branchement de l'onglet « Mémoire et partitions », dont
le code vit dans `build_page_memoire.py` ; 1169 le meme jour avec le branchement de l'onglet « Env par défaut (Platformio override) », dont le
code vit dans `build_page_defaut.py` ; 1206 le meme jour avec le bouton de purge du cache et le resume memoire de chaque env ; 1210 le 2026-11-02 avec les couleurs du panneau « Sortie », dont le code vit dans `build_page_couleurs.py` ; 1215 le meme jour avec le branchement de l'onglet « Aide », dont le texte vit dans `build_page_aide.py` ; 1223 le 2026-11-03 avec le branchement de l'onglet « Sauvegarde configuration », dont le code vit dans `build_page_sauvegarde.py` ; 1223 encore le 2026-11-10 avec le branchement de la bascule « Classer par », dont le code vit dans `build_page_lieux.py` (qui reprend aussi la memoire d'ouverture de `chargeEnvs`) ; 1226 le 2026-11-11 avec le branchement de `lieux.JS`, commun aux listes de cartes ; 1233 le 2026-11-13 avec la case « Publier les fiches QR à la fin », etiquettes A11 ; 1250 le 2026-11-15 avec le branchement de l'onglet de réparations, dont le code vit dans `build_page_reparations.py` ; 1256 le meme jour avec la pastille Flash / RAM de fin de compilation, dont le code vit dans `build_page_fin_memoire.py`, et la case « Relancer apres reparation par l'IA », dont le code vit dans `build_page_reparations.py`). C'est la page
unique de l'outil « Build et televersement » (HTML + CSS + JS dans une seule constante
servie par `build_web.py`) : ne pas la decouper pour satisfaire le compteur.

Meme outil, meme decision (2026-10-25, exception acceptee par l'utilisateur plutot qu'un decoupage) :
`build_web.py` fait **530 lignes** (decide le 2026-11-15 : routes des reparations et de l'IA, +19 ; la logique vit dans `build_web_reparations.py`) ;
`build_serie.py` fait **879 lignes** (+4 le 2026-11-15 : case « Relancer apres reparation par l'IA », `Serie.lance(ia_auto=)` ; +13 le meme jour : réparation automatique des pannes, plan build-reparations ; +24 le 2026-11-14 : reparateur branche dans la serie, build-reparations A3 ; +20 le 2026-11-13 : publication des fiches QR apres une serie reussie, etiquettes A11 ; +2 le 2026-11-12 : ce qu'un ESP8266 garde hors de sa sauvegarde, dans le journal avant flash ; +9 le 2026-11-03 : sauvegarde « avant flash » de la configuration ; +18 le 2026-11-02 : sauvegarde et retablissement de `/.drvset003` autour d'un flash serie ; +14 le 2026-11-01 : table de partitions de l'env ; +19 le 2026-10-25 : total estime d'un env jamais compile ; +17 le 2026-10-26 : arret de pio sur solidification vide ; +8 le meme jour : FS fait par l'envoi serie du firmware ; +11 le 2026-10-27 : data_dir pose avant pio ; +3 le meme jour : identite de l'image du FS ; +7 le meme jour : duree des zones d'envoi memorisee, A13 ; +6 le 2026-10-28 : OTA par le maitre, A11 ; +9 le meme jour : Sleep 0 du maitre pendant l'envoi ; +30 le 2026-10-29 : action « fichiers » de l'onglet Fichiers ; +16 le meme jour : transport MQTT (A16) ; execution en serie des `pio run` : verrous, arret immediat, attente
d'un envoi au Ctrl+C, OTA, pause « rebranchez la carte » ; la couper separerait un etat partage sous le meme
verrou), et ses bancs `test_build_serie.py` (**1532**, +152 jusqu'au 2026-11-14 : cas des reparations de build ; +44 le 2026-11-13 : case « Publier les fiches QR »), `test_build_page_chrome.py` (**1103**),
`test_build_ota_fs.py` (**925**, +78 le 2026-11-09 : place, fichiers identiques, remplacement, A17), `test_build_web.py` (**865**, +38 le 2026-11-14 : routes des reparations ; +30 le 2026-11-15 : IA et case `ia_auto`), `test_atelier_graphiques_page_chrome.py` (**773**, sonde de la page de l'atelier, +28 le 2026-11-11 : arrivee par ?lieu= ; +5 le 2026-11-08 : lien « Envoyer par la page Build » et liste vide,
decision du 2026-11-05), `berry/banc_graphiques.py` (**571**, banc de la page /graphiques, decision du 2026-11-06), ainsi que `test_annuaire.py` (**535**,
banc de l'annuaire) : un banc par module, chaque test lisible seul. Ne pas les decouper pour satisfaire le
compteur.

`outils_docs/scripts_python/outils_pc/menage_page.py` fait **614 lignes** et son banc `test_menage_application.py` **577**, et c'est **voulu**
(decide le 2026-11-17 apres la relecture du plan `menage-appliquer`, exception plutot qu'un decoupage ; la page etait a 436 lignes avant le bloc
« Appliquer un lot », l'annulation et le resume des renvois ; son bloc « Rapports sauvegardes » vit deja dans `menage_page_rapports.py`). Page
unique de l'outil « Menage du depot » (HTML + CSS + JS dans des constantes servies par `menage_web.py`) ; le banc suit les gestes d'ecriture
(application, retour en arriere, mutants) un a un, chaque cas lisible seul. Ne pas les decouper pour satisfaire le compteur.

`outils_docs/scripts_python/outils_pc/test_annuaire.py` fait **535 lignes** (banc de l'annuaire, un cas lisible seul) et `test_ftp_cartes_web.py`
**521** (banc du serveur du navigateur FTP des cartes : un cas par geste), et c'est **voulu** (decide le 2026-11-21 : exceptions plutot qu'un
decoupage). Ne pas les decouper pour satisfaire le compteur.

`.claude/hooks/garde_lecture.py` fait **735 lignes**, et c'est **voulu** (decide le 2026-11-24, plan `binomes-berry` A16 : exception plutot
qu'un decoupage ; sortir la CLI le laisserait a ~580). Garde des secrets a la lecture : detection, hook Read/Grep/Bash/PowerShell et lecteur
masque partagent les memes detecteurs ; son banc `test_garde_lecture.py` (62 cas, 7 mutants) le couvre en entier. Ne pas le decouper pour
satisfaire le compteur.

`outils_docs/scripts_python/berry/carte_modules_berry.py` fait **584 lignes**, et c'est **voulu** (decide le 2026-11-25, plan `binomes-berry`
A3 : exception plutot qu'un decoupage ; il en avait deja 551 avant les colonnes Bloc et Cout). Generateur unique de `CARTE_MODULES_BERRY.md` :
lecture des modules, des autoexec, des persists, du cenv (ProjectConfig) et du manifeste ; banc `maintenance/test_verifie_references_docs.py`
(sortie deterministe). Ne pas le decouper pour satisfaire le compteur.

`outils_docs/scripts_python/berry/banc_pompe_cave.be` fait **514 lignes**, et c'est **voulu** (decide le 2026-11-26 : exception plutot
qu'un decoupage ; 501 lignes avant le scenario `delai_sans_mise_en_route_valide`, +13 pour le delai calcule depuis une heure non
synchronisee). Banc unique de la pompe vide-cave : tous les scenarios partagent le meme montage (`monte`, bouchon `TasmotaStub`, vrais
`controleGeneral.be` et `globalFonctions.be`) ; le couper dupliquerait ce montage. Ne pas le decouper pour satisfaire le compteur.
