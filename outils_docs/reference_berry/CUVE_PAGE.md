# Jauges de la cuve

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Les jauges du niveau de la cuve (page `/cuve`, cuve et P4)

Premier essai du 2026-10-31. L'**icône de cadran** dans le titre de l'encadré du niveau de la cuve, sur la page
d'accueil de la cuve et du maître P4, ouvre `/cuve` : une **jauge liquide** pour le volume disponible en litres
(modèle A du catalogue `outils_docs/jauges/`, ECharts + extension echarts-liquidfill), un **demi-cercle** pour
le taux de remplissage en % (modèle H, SVG) et un **cadran des tensions** (modèle B, ECharts) : anneau extérieur =
tension de la sonde **recalculée** (0-10 V), anneau intérieur = tension **brute** à l'entrée de l'ADS1115, après le
pont diviseur. Rouge sous 20 %, orange sous 40 %, bleu au-delà.

- **Tensions** : la cuve recalcule la tension de la sonde (mV d'entrée × rapport du pont, tiré du montage de la voie,
  `ReglageAna cablage`) dans `sensorsCuve.valeursAnalogiques.tensionSonde_V`. L'encadré de l'accueil montre les deux
  lignes « Tension brute (ADS1115) » et « Tension sonde (recalculée) », même en erreur de mesure (elles servent à la
  diagnostiquer). Le P4 reçoit la tension recalculée **par ModBus** (registre 4708 de la cuve, voir
  `PROTOCOLE_MODBUS.md`) : il ne connaît pas le pont ; « -,-- V » tant que la cuve ne l'a pas servie.

- **Valeurs** : celles de l'historique de la carte, `/histo?p=direct`, relues toutes les 10 s. Sans historique
  actif (`diverses.historique.activation`), la page le dit et n'affiche rien ; dans les 2 min qui suivent un
  démarrage, elle attend l'historique. Volume maximal tiré des dimensions de la cuve : `modules.cuve.dimensions`
  sur la cuve, `dimensions` de l'entrée analogique de la cuve (esclave ModBus 1) sur le P4.
- **Bibliothèques** : ECharts vient de `/graphiques?f=echarts.js.gz`, avec la même clé de cache que la page des
  graphiques (pas de second téléchargement) ; l'extension (3,4 Ko compressée) de `/cuve?f=liquidfill.js.gz`.
  Sans elle, le taux reste affiché.
- **Fichiers** : `data/fs/cuvePageFonctions.be` (importé à la première ouverture), `data/sd/html/cuve.html`,
  `data/sd/css/cuve.css`, `data/sd/js/cuve.js`, `data/sd/js/echarts-liquidfill.min.js.gz`. Ils ne partent **que**
  sur la cuve et le P4 : liste `page_cuve` de `[berry_commun]`, ajoutée au `custom_files_exclude` de tous les
  autres envs. Une nouvelle carte qui en aurait besoin la retire de sa liste.
- **Vérifier** : banc hors carte `python outils_docs/scripts_python/berry/banc_cuve_page.py` (code 0 = vert).

<hr></hr>
