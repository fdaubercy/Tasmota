# Découverte des cartes

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## La découverte des cartes : mode « annonce seule » (ESP32 sans PSRAM)

Le module `discovery` fait deux choses : il **annonce** la carte (sa fiche est construite à la connexion, rangée dans son
`/json/discovery.json`, publiée en retenu sur `tasmota/discovery/<MAC>/<rôle>`, et un esclave l'envoie à son maître par
ImAlive) et il **écoute** les autres cartes (abonnements `tasmota/discovery/+/#` et LWT, qui relisent et reparsent toute la
table à chaque message : ~14 Ko pour 13 cartes). L'écoute dépasse ce que tient un ESP32 sans PSRAM (limite Berry ~57 Ko :
redémarrages, constatés sur le différentiel le 2026-11-02 et sur le projecteur de barbecue le 2026-11-21).

`serveur.discovery.ecoute` règle l'écoute, sans toucher à l'annonce :

| Valeur | Effet |
|---|---|
| absente ou `"AUTO"` | écoute seulement si la carte a une PSRAM (`tasmota.memory()` porte la clé `psram`) : S3 et P4 inchangés |
| `"ON"` / `"OFF"` | impose le choix, PSRAM ou non |

En annonce seule, la carte reste listée sur la page `/discovery` des autres (fiche native de Tasmota, plus la fiche du
fork) ; sa propre page ne montre qu'elle. Un ESP32 sans PSRAM utilisé comme **esclave** (`serveur.udp.id` > 0) doit avoir
`serveur.discovery.activation` à `"ON"` : sans sa fiche, son maître ne le voit pas. Les projecteurs du jardin et du
barbecue sont réglés ainsi (`activation` `"ON"`, `ecoute` `"OFF"`). Code : `data/fs/discoveryFonctions.be::ecoute`,
`data/fs/controleDiscovery.be` ; banc `berry/test_discovery.be` (section 29).
