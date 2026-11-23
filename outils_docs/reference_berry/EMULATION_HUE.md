# Émulation Hue pour Alexa

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Émulation Hue pour Alexa

La carte se présente sur le réseau local comme un pont Philips Hue : un Echo la découvre et commande à la voix les sorties choisies, sans cloud ni compte développeur. Cartes concernées : P4 du garage, cave S3, greniers du RDC et du 2e étage (liste `berry_commun.emulation_hue` du cenv, solidifiée chez elles, exclue des autres). Le transport est celui du firmware (`Emulation 2` : SSDP, `/description.xml`, `/api` sur le port 80). Le choix des appareils est en Berry : `data/fs/hueFonctions.be::appareils` (liste blanche, ids Hue, réponses JSON) et `data/fs/controleHue.be` (pont `global.hue_bridge`, réglage du firmware par `controleHue.be::regle`). Banc : `python outils_docs/scripts_python/berry/banc_hue.py` (persists réels des 4 cartes, mutants).

### Activer

- Bloc `serveur.emulationHue` du `_persist.json` : `{"activation": "OFF", "log": "info"}`. À `OFF` (valeur du dépôt sur les 4 cartes), rien n'est exposé et `Emulation` est remis à 0. À `ON`, les `FriendlyName1` à `8` reçoivent un `$` devant leur nom (les relais natifs disparaissent de la découverte), puis `Emulation 2` est posé.
- Chaque bascule redémarre la carte une fois : le firmware redémarre à chaque commande `Emulation`, le module compare donc avant d'envoyer (pas de boucle). Un nouveau `CFG_HOLDER` remet `Emulation` à 0 : à `ON`, un redémarrage de plus au démarrage suivant.
- Puis « Alexa, découvre mes appareils ». L'Echo et la carte doivent être sur le même réseau local (le SSDP passe en multicast) : un esclave derrière le NAPT d'un maître n'est pas joignable, c'est pourquoi aucun esclave n'embarque le module.
- Seuil des logs : `ReglageLog emulationHue <niveau>` (cible `emulationHue`, clé `log` du bloc). Une ligne `info` par commande reçue, une ligne `erreur` par refus.

### Choisir les sorties : clé `alexa`

Dans le bloc du relais (`modules.<m>.environnement.relais.<r>`) :

```json
"alexa": {"activation": "ON", "nom": "Projecteur du jardin", "type": "onoff"}
```

Un relais sans clé `alexa` n'est jamais exposé. Relais réel ou virtuel (ModBus, MQTT, TCA9554) : la commande passe par `tasmota.set_power`, puis par `controleGeneral.be::set_power_handler`, comme un appui sur la page web. Posées au dépôt : P4 relais 1 (LED de la cuve), 5 (projecteur du garage), 24 (projecteur du jardin), 26 (projecteur du barbecue) ; cave relais 2 (ventilation) et 3 (LED des machines). Les greniers n'exposent rien.

Refus fermés, même avec une clé `alexa` (journal `erreur`) : relais ou module inactif ; relais d'un volet (Shutter : `relais1` et `relais1+1` de chaque VR actif, soit 2 et 3 du rideau, 20 à 23 du portail sur le P4) ; id hors de 1 à 32 ; type autre que `onoff` ; nom vide ou de plus de 32 caractères ; nom (casse ignorée) ou relais déjà exposé. La pompe vide-cave et la pompe de la piscine (déjà en WeMo sur son ESP8266) ne sont pas exposées. Le refus des doublons ne joue que sur une carte : l'application Alexa voit les ponts de toutes les cartes ensemble, chaque nom vocal doit donc être unique dans toute la maison.

### Limites

- L'API Hue n'a aucune authentification : tout appareil du réseau local peut commander les sorties exposées. En émulation native, `PUT /api/x/lights/<n>/state` commande n'importe quel POWER, même masqué par `$` ; le module ferme cette porte : tout id hors liste reçoit une erreur Hue et rien ne commute.
- Fenêtre de démarrage : entre le démarrage du firmware et le chargement de `controleHue` (ou si ce chargement échoue), `Emulation 2` du démarrage précédent laisse l'API native répondre seule, sans liste blanche.
- `/api/<user>` sans chemin (configuration complète) ne liste pas les appareils Berry (limite amont de `xdrv_20_hue.ino::HueGlobalConfig`) ; Alexa passe par `/api/<user>/lights`.
- Les `FriendlyName` gardent leur `$` après un retour à `OFF` ; ils apparaissent ainsi dans `Status` et dans les intégrations qui les lisent.
- Seul `on` est traité (pas de variateur). Rien n'est poussé vers Alexa : l'application relit l'état quand elle le demande.
- Rien n'a encore été essayé sur une carte.
