---
chantier: cartes-simulees
titre: Cartes simulées hors ligne, au choix pour tout env du parc (page dans l'annuaire)
statut: actif
cree: 2026-11-14
maj: 2026-11-14
source: inherited-snuggling-pond.md
objectif: Simuler n'importe quelle carte du parc hors ligne (pages réelles, routes Berry réelles, valeurs rejouées ou de scénario), choisie sur une page de l'annuaire, avec l'IP de la carte sous garde
famille: build
liens: visuel-reglage-volets, menage-page
---
# Cartes simulées hors ligne

## Contexte
Décisions de l'utilisateur (2026-11-14) :
- Le « vrai firmware » dans QEMU est limité à l'ESP32 classique (QEMU n'émule pas le Wi-Fi des S3 et du P4). Les S3 et P4 passent par la simulation des réponses HTTP.
- Tout env du parc doit être simulable, au choix sur une page dédiée de l'annuaire (port 7600).
- Périmètre voulu : tout le site de la carte. Limite à dire : les pages natives Tasmota en C++ (Configuration, Console...) ne sont rejouables que depuis une capture de la vraie carte. Le rideau n'est pas sur le réseau (esclave derrière le NAPT du P4), donc sans capture.
- IP : prise sous garde (carte éteinte vérifiée avant, retrait dès son retour). Les esclaves derrière le NAPT du P4 sont servis sur un port, sans alias d'IP.
- Aide du Berry du dépôt : `berry.exe` (lib/libesp32/berry/) exécute les vrais modules sur les bouchons de `outils_docs/scripts_python/berry/bouchons_berry/`.
- 2026-11-14 : le P4 (192.168.0.43) est EN LIGNE et ne se simule pas ; seul le rideau est hors ligne et passe en premier. Son adresse du parc, 192.168.0.43:8082, est celle du P4 (NAPT) : pas d'alias d'IP pour lui, la simulation écoute le port 8082 du PC.
- Détails à confirmer après le rapport de l'agent d'exploration (réutilisations exactes).

## A1 — Inventaire des envs simulables
- [ ] Liste des envs, dossier `data/<lieu>/<carte>`, IP, hostname, topic, puce (réutiliser `outils_pc/build_envs.py` et `lieux.py::identites`)
- [ ] Pour chaque env : modules Berry chargés (autoexec) et routes déclarées
- [x] Banc de l'inventaire — preuve : outils_pc/test_cartes_simulees.py section 4 VERT (13 cartes avec persist, hote et topic relus en brut, accueil générique ; 45 contrôles)

## A2 — Moteur Berry (routes réelles)
- [x] Exécuter par `berry.exe` le module de la carte (ex. `controleRideau.be::web_add_main_button`) sur les bouchons et capturer le HTML — preuve : berry/simule_carte_rideau.be accueil -> window.VOLETS avec decor [chevrefeuille, porte, pergola] ; route /rideau : curseur P4 30 -> 70 %, P4 muet + contact ON -> 100 % muet (sortie lue 2026-11-14)
- [ ] Bouchons manquants (`tasmota`, `webserver`, `persist` du dossier de la carte, `path`)
- [ ] Banc : la sortie du rideau contient `window.VOLETS` avec le décor

## A3 — Serveur de la carte simulée
- [ ] Serveur HTTP par carte : fichiers `/sd`, routes Berry (A2), `/cm?cmnd=` de base, 404 net pour le C++ natif non capturé
- [x] Identité réseau identique au persist : hôte, IP, passerelle, masque, DNS, MQTT (affiché, jamais connecté), port web = 8080 + id - 1 derrière un maître, répondus par `/cm Status 5` et `Status 6` — preuve : outils_pc/test_cartes_simulees.py VERT (valeurs relues en lecture brute du persist, témoin négatif)
- [x] Le rideau simulé lit la vraie position du P4 en ligne (Status 10, GET en lecture seule) ou un scénario au choix — preuve : outils_pc/test_cartes_simulees.py section 5 VERT (faux P4 local : 20 -> 80 %, une seule requête, P4 coupé -> maître muet)
- [ ] Valeurs de scénario (ouvert, fermé, maître muet, incohérence) ; position lue par `/rideau?f=position&id=`
- [ ] Banc avec témoin négatif

## A4 — Capture et rejeu
- [ ] Capture d'une carte en ligne (GET uniquement) rangée hors dépôt, secrets masqués
- [ ] Rejeu des pages natives capturées, avec la date de la capture affichée
- [ ] Banc sur une carte simulée (jamais le vrai P4 en essai automatique)

## A5 — Adresse et garde « carte en ligne » (réduit le 2026-11-14)
Plus d'alias d'IP : le rideau, seule carte simulée, n'a pas d'IP propre sur le LAN (son adresse du parc est celle du P4, 192.168.0.43:8082). L'alias `netsh` (administrateur) revient seulement si une carte à IP propre doit un jour être simulée (voir Améliorations restantes).
- [x] Port dédié du PC, sans alias : port web de la vraie carte (8080 + id - 1 derrière un maître) — preuve : test_cartes_simulees.py VERT (port web = 8080 + id - 1)
- [x] Une carte qui répond sur le réseau n'est jamais simulée (connexion TCP à son adresse du parc, refus 409) — preuve : test_cartes_simulees_web.py VERT (carte EN LIGNE refusée, témoin)

## A6 — Page « Cartes simulées » dans l'annuaire
- [x] Page : liste des envs, source (scénario/capture), IP, simuler/arrêter, lien vers la page simulée — preuve : outils_pc/test_cartes_simulees_web.py VERT (19 contrôles : lancer et arrêter le rideau pour de vrai, carte en ligne refusée, anti-CSRF, Host) ; capture de la page lue
- [x] Tuile (groupe Ateliers, comme le ménage : l'annuaire n'a pas de groupe Maintenance), tâche VS Code, cible Custom détachée, `garde_build` (`CIBLES_OUTILS`) — preuve : build/test_cible_cartes_simulees.py VERT, build/test_garde_build.py VERT, registre chargé (annuaire_registre.par_id). Pas de refus pendant un build : l'outil ne lit que le dépôt
- [ ] Sonde Chrome (thème, téléphone)

## A7 — Vrai firmware ESP32 classique (essai)
- [ ] Choisir l'env ESP32 de l'essai ; QEMU via WSL2 ou `idf_tools.py`
- [ ] Boot du firmware compilé par la page Build (:7700), jamais par `pio` direct
- [ ] Documenter les limites (S3/P4 non couverts)

## A8 — Documentation
- [ ] Entrée dans la Carte des documents de CLAUDE.md et section de `outils_docs/README.md`
- [ ] Exceptions de longueur déclarées si un fichier dépasse 500 lignes

## Améliorations restantes
- [ ] [projet] Wokwi pour S3/P4 si le réseau y devient utilisable
- [ ] [projet] Alias d'IP (`netsh`, administrateur, retrait à l'arrêt, garde ping/ARP/LWT MQTT) pour simuler une carte à IP propre hors ligne
- [ ] [projet] Simuler le NAPT du maître pour joindre le rideau simulé en 192.168.0.43:8082 depuis un autre appareil (le P4 est en ligne : jamais en alias)

## Vérification
Banc de chaque module, sonde Chrome de la page, puis essai à la main : ouvrir la page simulée du rideau et voir la façade avec arbustes et la porte qui bouge. Aucun build ni flash pendant les essais.
