# Plan de la maison

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Plan de la maison (page HTML générée)

`outils_docs/plan_maison/` : `python outils_docs/plan_maison/genere_plan_maison.py` écrit `plan_maison.html`, une page autonome (SVG, clair ou sombre) qui place chaque carte de `data/<lieu>/<carte>/` dans sa pièce. Deux vues : plan (pièces par étage, jardin et garage à part) et réseau (broker MQTT, un groupe par maître avec ses esclaves derrière son Wi-Fi). Les liens et les rôles sont DÉRIVÉS des `_persist.json` : `serveur.rangeExtender.ipMaitre` (qui est l'esclave de qui), `drivers.ModBus.typeComm` (trait plein = RS485, pointillé = UDP), `rangeExtender.id` (rond numéroté), `serveur.mqtt.hote` (broker). Aucun mot de passe n'est lu.

`placement.json` porte ce que les persist ne disent pas : pièces et position, carte -> pièce, libellés, `ip_cartes` (arbitre une IP portée par deux cartes), `etiquettes`, `liens_manuels`, nom du broker. Une carte de `data/` sans placement, un lien orphelin, une pièce qui déborde ou une IP ambiguë sont signalés sur stderr. Le bouton « Tester les cartes » interroge les IP au clic seulement. Aucun appel réseau à la génération, jamais pendant un build.

Vue Wi-Fi : `placement.json` > `wifi.appareils` (box, relais, répéteurs placés dans leurs pièces, SSID -> appareil). Le réseau principal (`reseau1`) est un trait plein de la couleur de l'appareil, le secours (`reseau2`) un pointillé masqué par défaut, le Range Extender du maître (SSID `<hote>-GATEWAY`) un rail rose double. MAISON est diffusé par plusieurs points d'accès : le persist ne dit pas lequel, la Freebox Server est le défaut, `wifi.wifi_manuel` corrige. Le survol d'une carte met en évidence ses voisines.

Marque « 📶 RE ×N » sur chaque maître (esclaves derrière son Range Extender) et étiquette « id N » au milieu des liens. Vue chauffage : PAC, nourrice et départs d'après `placement.json` > `chauffage` (affectation Débit 1 à 6 -> pièce encore inconnue, traits en pointillé). Sonde Chrome : `python outils_docs/scripts_python/outils_pc/test_plan_maison_page_chrome.py` (vues, filtres, survol, fiche, bouton de test avec fetch remplacé, en-tête fixe).

Tuile « Plan de la maison » de l'annuaire (groupe Dépôt et références, port 7915, `outils_pc/plan_maison_web.py`, lecture seule, page régénérée à chaque ouverture, banc `outils_pc/test_plan_maison_web.py`).

Icône ↗ sur chaque pastille : ouvre la page web de la carte (IP du persist ; esclave derrière un maître : IP du maître, port 8080 + id - 1). Vue chauffage : bouton « Lire les débits » (au clic seulement) -> `GET /debits` de `outils_pc/plan_maison_web.py` lit `Status 10` de la carte d'acquisition (cible fixe de `placement.json` > `chauffage.acquisition`, lecture seule) et affiche les 6 débits, le total et les voies muettes ou imprécises ; la page doit être ouverte par l'annuaire. Comparaison des façons de tracer les liens entre pièces : `outils_docs/plan_maison/propositions_faisceau.html`.

Banc : `python outils_docs/plan_maison/test_plan_maison.py` (code 0 = vert). Plan : `tasks/plans/plan-maison.md`. Suite en cours (plan actif) : plan à l'échelle, étage par étage, éditable dans une page web, `tasks/plans/plan-maison-echelle.md` ; cotes à relever avant : `outils_docs/plan_maison/mesures_a_saisir.md`.
