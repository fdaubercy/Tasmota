# Historique long terme des capteurs (Raspberry Pi SERVEUR-BUREAU)

## But

Garder 5 ans de mesures des cartes Tasmota (niveau de cuve, temperatures, energie,
etat Wi-Fi...) et des agregats horaires sans limite de duree, consultables dans Grafana.

## Architecture

```
cartes Tasmota --MQTT tele/<topic>/SENSOR|STATE (toutes les 300 s)--> Mosquitto 192.168.0.5:1883
   --> Node-RED (onglet « Historique capteurs ») : aplatit le JSON en line protocol
   --> InfluxDB 1.8 : base Iot, RP capteurs_5ans (260 sem.) --CQ horaire--> RP capteurs_horaire (infinie)
   --> Grafana : tableau « Historique cuve »
```

- Measurement `capteurs` (SENSOR) et `etat` (STATE) ; tag `appareil` = topic de la carte.
- Champs : chaque feuille numerique, chemin joint par `_` (`sensorsCuve_niveauCuve_hauteurEau`,
  `DS18B20_Temperature`, `Wifi_RSSI`) ; `ON`/`OFF` -> 1/0 ; autres chaines ignorees.
- Tout est ecrit en float (pas de suffixe `i`) pour eviter les conflits de type de champ.
- Horodatage = heure de reception (le `Time` des cartes est local, sans fuseau).
- Les ecritures nomment EXPLICITEMENT `rp=capteurs_5ans` : cette RP n'est volontairement pas
  la RP par defaut, et `autogen` (positions OwnTracks) n'est pas touchee.

## Fichiers

| Fichier | Role |
|---|---|
| `installe_influx_historique.sh` | cree les 2 RP et la CQ (idempotent, `--dry-run`) |
| `flow-historique-capteurs.json` | flow Node-RED importable |
| `grafana-historique-cuve.json` | tableau de bord Grafana importable |
| `test_flow_historique.js` | banc local du code du noeud function (`node test_flow_historique.js`, `--temoin` pour les mutations) |
| `grafana/` | provisionnement Grafana : source `influxdb-iot`, fournisseur de tableaux, tableau a source figee |
| `fusion_flux_pi.py` | ajoute l'onglet au fichier de flux, Node-RED ARRETE, en le raccordant au broker existant `af2f0082.9c6d9` (idempotent) |

Etat sur le Pi (2026-10-13) : les 3 etapes FAITES. InfluxDB 1.8.10 sans authentification (par
l'API HTTP) ; Node-RED fusionne par `fusion_flux_pi.py` (sauvegarde
`flows_SERVEUR-BUREAU.json.avant-historique-20261013-060332`) ; Grafana 9.2.3 provisionne.
11 appareils historises des les 5 premieres minutes.
Editeur Node-RED : `http://192.168.0.5:1880/serveur-bureau/admin` (`httpAdminRoot`). Abonnement
unique `tele/#` : des cartes publient sur des topics a plusieurs niveaux (`tele/cave/serveur-rly-cave-v2/...`),
que `tele/+/SENSOR` ne capterait pas ; le tag `appareil` vaut tout le chemin entre `tele/` et `/SENSOR`.

## Installation pas a pas

1. **InfluxDB** : copier le dossier sur le Pi, puis
   `./installe_influx_historique.sh --dry-run` (relire), puis `./installe_influx_historique.sh`.
   Si l'authentification est active : `INFLUX_USER=... ./installe_influx_historique.sh`
   (le mot de passe est demande, ou variable `INFLUX_PASSWORD`). Jamais en dur.
2. **Node-RED**, par script depuis le PC (sauvegarde datee, arret ~30 s d'Alexa/HomeKit) :
   ```
   scp flow-historique-capteurs.json fusion_flux_pi.py SERVEUR-BUREAU:/tmp/
   ssh SERVEUR-BUREAU "cd ~/.node-red && cp -p flows_SERVEUR-BUREAU.json flows_SERVEUR-BUREAU.json.avant-historique && sudo systemctl stop nodered && python3 /tmp/fusion_flux_pi.py; sudo systemctl start nodered"
   ```
   Ou a la main : Menu > Import > coller `flow-historique-capteurs.json`.
   Ouvrir le noeud de config « Mosquitto Pi » et renseigner utilisateur / mot de passe MQTT.
   Si InfluxDB a l'authentification : double-clic sur l'onglet > Variables d'environnement :
   `INFLUX_USER`, `INFLUX_PASSWORD`. Puis Deploy. Si l'editeur n'est pas sur `/`
   (GET / = 404), `httpAdminRoot` est deplace : chercher le chemin dans `settings.js`.
3. **Grafana**, par provisionnement (fichiers du dossier `grafana/`, FAIT le 2026-10-13) :
   ```
   scp grafana/datasource-influxdb-iot.yaml grafana/dashboards-historique.yaml grafana/historique-cuve.json SERVEUR-BUREAU:/tmp/
   ssh SERVEUR-BUREAU "sudo install -m 644 -o root -g grafana /tmp/datasource-influxdb-iot.yaml /etc/grafana/provisioning/datasources/influxdb-iot.yaml && sudo install -m 644 -o root -g grafana /tmp/dashboards-historique.yaml /etc/grafana/provisioning/dashboards/historique.yaml && sudo install -d -o grafana -g grafana /var/lib/grafana/dashboards/historique && sudo install -m 644 -o grafana -g grafana /tmp/historique-cuve.json /var/lib/grafana/dashboards/historique/ && sudo systemctl restart grafana-server"
   ```
   Source « InfluxDB Iot » (uid `influxdb-iot`, par defaut), tableau « Historique cuve » dans le
   dossier « Domotique » : `http://192.168.0.5:3000/d/historique-cuve`. `grafana/historique-cuve.json`
   est la copie de `grafana-historique-cuve.json` avec la source figee (le provisionnement ne
   traite pas `__inputs`). Ou a la main : Dashboards > Import > `grafana-historique-cuve.json`,
   source InfluxDB (InfluxQL, base `Iot`) pour `DS_INFLUXDB`.
   Variable `appareil` : `jardin/cuve` par defaut (topic de la cuve), liste deroulante des autres.
   Le tableau a deux rangees : detail 5 min (`capteurs_5ans`, a regarder sur 30 jours au plus)
   et long terme horaire (`capteurs_horaire`, champs `mean_`/`min_`/`max_`).

## Verification

```
influx -database Iot -execute 'SELECT * FROM "capteurs_5ans"."capteurs" WHERE time > now() - 15m LIMIT 5'
influx -database Iot -execute 'SHOW RETENTION POLICIES'
influx -database Iot -execute 'SHOW CONTINUOUS QUERIES'
```

Premiers points : au plus 5 min + 10 s (lot) apres le deploiement. L'onglet Node-RED ne montre
rien dans le debug tant que tout va bien ; une erreur HTTP (code != 204) y apparait.
Apres une heure pleine : `SELECT * FROM "capteurs_horaire"."capteurs" LIMIT 3`.
La CQ ne traite que le futur ; pour rejouer le passe, lancer a la main le `SELECT ... INTO`
avec une clause `WHERE time >= ... AND time < ...`.

## Retour arriere

```
influx -execute 'DROP CONTINUOUS QUERY "cq_capteurs_horaire" ON "Iot"'
influx -execute 'DROP RETENTION POLICY "capteurs_horaire" ON "Iot"'   # efface les agregats
influx -execute 'DROP RETENTION POLICY "capteurs_5ans" ON "Iot"'      # efface le detail
```

Puis supprimer l'onglet « Historique capteurs » (et le noeud « Mosquitto Pi » s'il n'est plus
utilise) et le tableau Grafana. `autogen` et les positions OwnTracks ne sont jamais touchees.

## Volumetrie estimee

8 cartes x 2 measurements, ~20 champs au total par carte, 1 point / 5 min :
~2 300 points/jour/measurement, soit ~4,2 M points sur 5 ans par measurement, ~8 M au total
(~170 M de valeurs). Compression TSM : compter de l'ordre de 150 a 400 Mo sur 5 ans.
Agregats horaires : quelques dizaines de Mo, conserves sans limite. Negligeable pour un Pi,
mais verifier la taille du disque et la sauvegarde de `/var/lib/influxdb`.

## Test local

`node test_flow_historique.js` extrait le JS du noeud depuis le flow et le confronte a des
trames reelles (cuve, STATE avec POWER1/Wifi, message sans champ, cle a espace...).
`--temoin` applique des mutations : le banc doit alors echouer.
