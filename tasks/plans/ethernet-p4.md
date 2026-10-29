---
chantier: ethernet-p4
titre: Ethernet en option sur le maître ModBus P4 (SERVEUR-GARAGE)
objectif: Ajouter l'Ethernet en option sur le maître ModBus P4, le Wi-Fi restant le défaut
statut: actif
cree: 2026-10-26
maj: 2026-10-26
---
# Ethernet en option sur le maître ModBus P4 (SERVEUR-GARAGE)

## Contexte
Spec validée par l'utilisateur le 2026-10-26 : `docs/superpowers/specs/2026-10-26-ethernet-p4-design.md`
(à lire avant toute action : décisions, références `fichier:ligne`, pièges). En bref :
- Wi-Fi STA = défaut, garde **192.168.0.43** et le point d'accès des esclaves (il exige la STA,
  `xdrv_58_range_extender.ino:497-526`). Ethernet = **option**, IP fixe **192.168.0.50**, coupée par défaut.
- Bloc `serveur.ethernet` dans les 8 `_persist.json` qui portent `serveur`, `activation: "OFF"` partout.
- `configGlobal` applique le bloc au démarrage, **seulement sur une carte avec Ethernet** =
  `gpio.pin_used(gpio.ETH_PHY_MDC) && gpio.pin_used(gpio.ETH_PHY_MDIO)` (constantes :
  `tasmota/berry/include/be_gpio_defines.h:102-103`). Toutes les cartes compilent l'Ethernet et ont
  `Ethernet` = 1 par défaut (`settings.ino:1081`) : sans ce critère, toutes redémarreraient.
- `ReglageGlobal Ethernet [ON|OFF]` + bouton dans la page Configuration ; `/discovery` corrigée pour
  annoncer l'IP STA du maître.
- Pas de C amont modifié. Si la mesure du routage (A9) montre que le trafic reste sur la STA : on
  consigne et on s'arrête (décision de l'utilisateur).
- Seul le P4 est téléversé dans ce chantier.

Interfaces décidées (socle `berry_commun.socle`, solidifié dans toutes les cartes) :
- `configGlobal.carteAvecEthernet() -> bool` (critère ci-dessus).
- `configGlobal.configEthernet(ethernet: map|nil) -> nil` : appelé par `configGlobalByJson` avec
  `serveur.find("ethernet")` ; ne fait rien si `nil` ou si `!carteAvecEthernet()` ; sinon `testeParam`
  sur `EthType`/`EthAddress`/`EthIPAddress`/`EthGateway`/`EthSubnetmask`/`EthDNSServer` (si `ON`) puis
  `Ethernet` ← `activation`.
- `globalFonctions.reglageEthernet(arg: string) -> map` : `""` = état
  `{activation, carte, up, ip, mac}` ; `ON`/`OFF` (casse indifférente) = persist écrit et sauvé PUIS
  `Ethernet 1|0` différé (`tasmota.set_timer`, comme `reglageModeConnexion`) ; autre argument ou carte sans
  Ethernet = `{erreur: …}` sans rien écrire.
- `controleWeb` : `web_add_config_button` (bouton seulement si `carteAvecEthernet()`) + route
  `/ethernet` (GET = état, POST `bascule` = appelle `reglageEthernet`).

Règles du dépôt à appliquer à chaque action : charte des logs Berry (CLAUDE.md), jamais d'édition de
`data/` ni de `pio run` pendant un build (vérifier avant chaque série d'éditions), commit par
`git commit -- <chemins>` en français sans accents, fichiers réécrits par le build inclus (commit chore
séparé), pas de push sans demande, rien envoyé à une carte sans l'accord de l'utilisateur.

## Points de vigilance (Review Focus)
1. Persist ancien sans bloc `ethernet` → aucune commande Ethernet, aucun redémarrage (test A3).
2. Carte sans broches ETH avec un persist à `ON` (copie de persist) → aucune commande (test A3).
3. Boucle de redémarrage : après un premier alignement, un 2e démarrage doit n'envoyer **aucune**
   commande (formats de réponse `"ON"`, `"192.168.0.50 (192.168.0.50)"`, `"0.0.0.0 (ip DHCP)"`) (test A3).
4. Câble débranché option `ON` → P4 joignable en .43, pas de redémarrage par `surveilleWifi` (essai A9).
5. `ReglageGlobal Ethernet on`, `1`, `toto` → casse acceptée, `1`/`toto` refusés sans écriture (test A4).

## A1 — Essai sur table du PHY Ethernet, avant tout code
- [ ] Avec l'accord de l'utilisateur, P4 près de la box, câble branché : `Status 5` (état de départ) et `Ethernet` / `EthType` / `EthAddress` relevés
- [ ] `Ethernet 1` (redémarre) puis `Status 5` → bloc `StatusNET.Ethernet` avec une IP DHCP, `EthType` = 1
- [ ] .43 (STA) répond toujours, cuve et rideau joignables ; état remis comme au départ
- [ ] Résultat consigné dans la spec (§3) ; si le PHY ne monte pas : arrêt du chantier et diagnostic (`superpowers:systematic-debugging`)

## A2 — Bloc `serveur.ethernet` dans les persists
- [ ] Liste des 8 persists établie par `git ls-files | grep _persist.json` (hors `*-sauvegarde`), bloc inséré après `serveur.IP` avec les valeurs de la spec §5.1, fins de ligne de chaque fichier conservées
- [ ] Chaque fichier relu par `python -c "import json;json.load(open(...,encoding='utf-8'))"` ; `git diff --stat` = 8 fichiers
- [ ] `outils_docs/schemas/persist.schema.json` régénéré par `genere_schema_persist.py`, puis `--valide` vert
- [ ] Commit `feat(persist): bloc serveur.ethernet (OFF) dans les persists`

## A3 — `configGlobal` : critère de carte et application au démarrage
- [ ] Bouchons du banc de démarrage étendus : `gpio.pin_used` piloté par le cas (broches ETH ou non), réponses de `Ethernet`/`EthType`/`EthAddress`/`EthIPAddress`… au format Tasmota, journal des commandes envoyées
- [ ] Tests écrits AVANT le code (doivent échouer) : `ethernet_absent_rien_envoye`, `carte_sans_broches_on_rien_envoye`, `p4_off_drapeau_1_envoie_ethernet_off`, `p4_on_aligne_puis_ethernet_on`, `p4_deuxieme_boot_aucune_commande`
- [ ] `carteAvecEthernet` et `configEthernet` écrits dans `data/fs/configGlobal.be`, appel ajouté dans `configGlobalByJson` après le bloc `IP` (`configGlobal.be:136-147`)
- [ ] Tests verts + témoin : critère des broches neutralisé dans une copie → `carte_sans_broches_on_rien_envoye` échoue
- [ ] `banc_demarrage.py` : instantanés des 5 cartes sans PHY **identiques** ; celui du P4 relu, écart attendu (`Ethernet 0`) enregistré par `--enregistre --carte tasmota32p4-garage-serveur-modbus`. `banc_boot.py` vert
- [ ] Commit `feat(berry): configGlobal applique serveur.ethernet sur la seule carte a Ethernet`

## A4 — `ReglageGlobal Ethernet [ON|OFF]`
- [ ] Tests écrits avant : état sans argument (aucune écriture), `ON` → persist `ON` sauvé AVANT la commande différée `Ethernet 1`, `on` accepté, `1`/`toto` refusés sans écriture, carte sans Ethernet refusée
- [ ] `globalFonctions.reglageEthernet` + branche `ETHERNET` dans `reglageGlobal` (`globalFonctions.be:667`, réponse `{"ReglageGlobal": …}` comme `ModeConnexion`) + ligne d'aide
- [ ] Tests verts + témoin (ordre persist/commande inversé dans une copie → test rouge) ; `verifie_berry` sans avertissement de charte
- [ ] Commit `feat(berry): ReglageGlobal Ethernet ON|OFF`

## A5 — Bouton Ethernet dans la page Configuration
- [ ] `web_add_config_button` et route `/ethernet` dans `data/fs/controleWeb.be` (handlers `controleWeb.be:371`), bouton absent si `!carteAvecEthernet()`, confirmation JS « la carte va redémarrer » avant le POST
- [ ] Test au banc (ou bouchon webserver) : bouton émis sur le P4, absent sur une S3 ; POST `bascule` appelle `reglageEthernet`
- [ ] Commit `feat(web): bouton Ethernet dans Configuration`

## A6 — `/discovery` : IP STA du maître
- [ ] Test écrit avant (`test_discovery.be` ou banc voisin) : fiche `config` avec `ip` .50 et `hn` `SERVEUR-GARAGE-eth` + fiche `maitre` `IPAddress` .43 sous la même MAC → bouton vers .43, port distant 10043, `SERVEUR-GARAGE.local` ; sans fiche `maitre` → suffixe `-eth` retiré
- [ ] Correction dans `discoveryFonctions.be:743-749` ; test vert + témoin (ancien code → rouge)
- [ ] Inventaire en lecture des usages Berry de l'IP/nom réseau (`config.ip`, `config.hn`, `NetworkAddress`…) consigné dans la spec §5.6 ; corrections éventuelles → « Améliorations restantes »
- [ ] Relecture des `.be` modifiés par l'agent `relecteur-berry` ; commit `fix(berry): /discovery annonce l IP Wi-Fi du maitre quand l Ethernet est actif`

## A7 — Build et téléversement du P4, option à OFF
- [ ] Aucun build en cours ; build + téléversement du P4 par l'utilisateur (ou avec son accord, page Build :7700) ; fichiers réécrits par le build commités (chore)
- [ ] Un seul redémarrage dû à `Ethernet 0`, puis plus aucun (log syslog `CONTROLE_GENERAL`) ; `Ethernet` = OFF
- [ ] Non-régression : cuve et rideau joignables (8081/8082), `/discovery` correcte, ModBus vers la cuve OK sur 10 min (log `modbus`)

## A8 — Option à ON
- [ ] `ReglageGlobal Ethernet ON` (accord de l'utilisateur) → un seul redémarrage, `Status 5` : Ethernet .50, STA .43
- [ ] .43 et .50 répondent ; cuve et rideau joignables par le point d'accès et par `RgxPort` ; `/discovery` vers .43
- [ ] Bouton de la page Configuration : état affiché, bascule OFF puis ON confirmée

## A9 — Mesure du routage et débranchement du câble
- [ ] Instrument choisi (lecture seule) et témoin : interface de sortie de MQTT (.5) et syslog (.3) relevée sur 3 démarrages
- [ ] Câble débranché option ON : P4 joignable en .43, pas de redémarrage pendant 10 min ; câble rebranché : .50 revient
- [ ] Résultat consigné (spec §6 + README) ; si le trafic reste sur la STA ou varie : noté, chantier poursuivi sans correctif (décision du 2026-10-26)

## A10 — Documentation et remontage
- [ ] `outils_docs/README.md` : plan d'adressage (.50 = Ethernet du Serveur de Garage), mode d'emploi `ReglageGlobal Ethernet` et bouton, résultat de A9
- [ ] `CLAUDE.md` § « Carte des documents » : spec et plan ajoutés ; commit `docs: Ethernet du P4`
- [ ] P4 remonté au garage, état final (ON ou OFF) choisi par l'utilisateur ; `statut: clos`

## Améliorations restantes
- [ ] [projet] Correctif C (priorité de route de l'Ethernet / Range Extender sans STA) si A9 le montre utile — chantier à part

## Vérification
Chantier fini quand : les bancs Berry sont verts avec leurs témoins, les instantanés des 5 cartes sans PHY
sont inchangés, le P4 tourne option OFF et option ON sans redémarrage en boucle, la cuve et le rideau
restent joignables dans les deux états, et le résultat de la mesure du routage est consigné.
