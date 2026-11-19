# Carte des modules Berry par carte

> Fichier GENERE par carte_modules_berry.py - ne pas editer a la main.
> Sortie deterministe (ni date, ni ordre de hachage) : regeneree sans changement de fond, elle ne
> donne aucun diff. La date de generation est celle du commit.

74 modules (54 dans `data/fs`, 20 propres a une carte), 14 cartes.

## Tableau

Legende : **S** solidifie dans l'env (`custom_berry_solidify`) - **I** importe par l'autoexec - **C** `compileModule` / `loadBerryFile` - **D** charge indirectement (importe par un module charge sur la carte) - **#** reference seulement commentee - **P** fichier propre a la carte - puis la garde d'activation evaluee sur le `_persist.json` de la carte : **ON** / **OFF** / **?** (non evaluable). Pas d'etat = pas de garde. Cellule vide = rien.

| Module | Famille | bureau<br>tasmota32-interrupteur-energie | bureau<br>tasmota32s3-ecran-debits-pac | bureau<br>tasmota32s3-serveur-debits-pac | cave<br>tasmota32-serveur-rly | cave<br>tasmota32s3-ecran | cave<br>tasmota32s3-serveur-rly | etage2<br>tasmota32s3-grenier | garage<br>tasmota32p4-serveur-modbus | garage<br>tasmota32s3-capteurs-cuve-modbus | garage<br>tasmota32s3-portail-jardin-modbus | garage<br>tasmota32s3-rideau-garage-modbus | garage<br>tasmota32s3-serveur-modbus | jardin<br>tasmota32-projecteur-led | rdc<br>tasmota32s3-grenier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `configDevices` | Socle | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON |
| `configGlobal` | Socle | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON |
| `configModules` | Socle | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON |
| `controleGeneral` | Socle | S I | S I | S I | S I | S I | S I | S I | S I | S I | S I | S I | S I | S I | S I |
| `controleLedTemoin` | Socle | S | S I | S I | S I | S I | S I | S I | S I | S I | S I | S I | S I | S | S I |
| `controleWeb` | Socle | S I | S I | S I | S I | S I | S I | S I | S I | S I | S I | S I | S I | S I | S I |
| `diversFonctions` | Socle | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON |
| `gestionFileFolder` | Socle | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON |
| `globalFonctions` | Socle | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON |
| `logFonctions` | Socle | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON |
| `webFonctions` | Socle | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON |
| `controleDiscovery` | Reseau | S I OFF | S | S I ON | S I OFF | S I ON | S I ON | S I ON | S I ON | S I ON | S I ON | S I ON | S I ON | S I ON | S I ON |
| `controleRangeExtender` | Reseau | S | S I ON | S I ON | S I OFF | S I ON | S I ON | S I ON | S I ON | S | S | S | S I ON | S I ON | S I ON |
| `controleTCP` | Reseau | S | S | S | S I OFF | S | S I OFF | S I OFF | S | S | S | S | S I ON | S | S I OFF |
| `controleUDP` | Reseau | S | S I ON | S I ON | S I OFF | S I ON | S I ON | S I OFF | S I ON | S I ON | S I ON | S I ON | S I ON | S | S I ON |
| `discoveryFonctions` | Reseau | S C OFF | S D | S D | S D | S D | S D | S D | S C ON | S C ON | S C ON | S C ON | S C ON | S C ON | S D |
| `rangeExtenderFonctions` | Reseau | S D | S C ON | S D | S D C OFF | S C ON | S C ON | S C ON | S D | S D | S D | S D | S C ON | S C ON | S C ON |
| `tcpFonctions` | Reseau | S D | S D | S D | S D C OFF | S D | S C OFF | S C OFF | S D | S D | S D | S D | S C ON | S D | S C OFF |
| `udpFonctions` | Reseau | S D | S C ON | S C ON | S D C OFF | S C ON | S C ON | S C OFF | S C ON | S C ON | S C ON | S C ON | S C ON | S D | S C ON |
| `controleModbus` | ModBus |  | S I ON | S I ON | # | S I ON | S I ON |  | S I ON | S I ON | S I ON | S I ON | S I ON |  | S I ON |
| `modBus_Conn16channels` | ModBus |  | S I ON | S I ON | # | S I ON | S I ON |  | S I ON | S I ON | S I ON | S I ON | S I ON |  | S I ON |
| `modBus_TasmotaSlaveModBus` | ModBus |  | S I ON | S I ON | # | S I ON | S I ON |  | S I ON | S I ON | S I ON | S I ON | S I ON |  | S I ON |
| `modbusFonctions` | ModBus | D | S I | S I | D | S I | S I | D | S I | S I | S I | S I | S I C ON | D | S I |
| `controleES8311` | Peripheriques |  |  |  |  |  |  |  | S I ON |  |  |  |  |  |  |
| `controleLeds` | Peripheriques |  |  |  |  |  | S I C OFF | S I C OFF |  | S I C ? | S I C OFF | S I C OFF | S I C OFF |  | S I C ? |
| `controleLoRaWan` | Peripheriques |  |  |  | # |  |  | S I OFF |  |  |  |  | S I ON |  |  |
| `controleVoletRoulants` | Peripheriques |  |  |  | # |  |  | S I ON | S I ON |  |  |  | S I OFF |  | S I ON |
| `i2c_ads1115` | Peripheriques |  | S I ON | S I ON | # | S I ON | S I ON |  | S I ON | S I ON | S I OFF | S I OFF | S I ON |  | S I ON |
| `i2c_mcp23017` | Peripheriques |  | S I ON | S I ON | # | S I ON | S I ON |  | S I ON | S I ON | S I OFF | S I OFF | S I ON |  | S I ON |
| `ledsFonctions` | Peripheriques | D | D | D | D | D | S D C OFF | S D C OFF | D | S I C ON | S D C OFF | S D C OFF | S D C OFF | D | S C ON |
| `ledsPanelFonctions` | Peripheriques | S D | S D | S D | S D | S D | S D | S D | S D | S D | S D | S D | S D | S D | S D |
| `loRaWanFonctions` | Peripheriques |  |  |  | # |  |  | S C OFF |  |  |  |  | S C ON |  |  |
| `vrFonctions` | Peripheriques |  |  |  | # |  |  | S C ON | S D |  |  |  | S C OFF |  | S D |
| `vrPages` | Peripheriques |  |  |  |  |  |  | S D | S D |  |  |  | D |  | S D |
| `vrReglage` | Peripheriques |  |  |  |  |  |  | S D | S D |  |  |  | D |  | S D |
| `controleCommandesEcran` | Carte |  |  |  |  |  | P C ON |  |  |  |  |  |  |  |  |
| `controleCuve` | Carte |  |  |  |  |  |  |  |  | P C ON |  |  |  |  |  |
| `controleDebits` | Carte |  |  | P C ON |  |  |  |  |  |  |  |  |  |  |  |
| `controleEcranCave` | Carte |  |  |  |  | P C ON |  |  |  |  |  |  |  |  |  |
| `controleEcranDebits` | Carte |  | P C ON |  |  |  |  |  |  |  |  |  |  |  |  |
| `controleGarage` | Carte |  |  |  |  |  |  |  | P C ON |  |  |  | P C ON |  |  |
| `controleGrenier` | Carte |  |  |  | # |  |  | P C ON |  |  |  |  |  |  |  |
| `controlePompeVideCave` | Carte |  |  |  | P C ON |  | P C ON |  |  |  |  |  |  |  |  |
| `controlePortail` | Carte |  |  |  |  |  |  |  |  |  | S P I ON |  |  |  |  |
| `controleRideau` | Carte |  |  |  |  |  |  |  |  |  |  | S P I ON |  |  |  |
| `cuveFonctions` | Carte |  |  |  |  |  |  |  |  | P C ON |  |  |  |  |  |
| `debitsFonctions` | Carte |  |  | P C ON |  |  |  |  |  |  |  |  |  |  |  |
| `ecranCaveFonctions` | Carte |  |  |  |  | P C ON |  |  |  |  |  |  |  |  |  |
| `ecranCaveHaspmota` | Carte |  |  |  |  | P C ON |  |  |  |  |  |  |  |  |  |
| `ecranDebitsFonctions` | Carte |  | P C ON |  |  |  |  |  |  |  |  |  |  |  |  |
| `ecranHaspmota` | Carte |  | P C ON |  |  |  |  |  |  |  |  |  |  |  |  |
| `ecranLvgl` | Carte |  | P C ON |  |  |  |  |  |  |  |  |  |  |  |  |
| `equilibragePage` | Carte |  |  | P C ON |  |  |  |  |  |  |  |  |  |  |  |
| `garageFonctions` | Carte |  |  |  |  |  |  |  | P C ON |  |  |  | P C ON |  |  |
| `preinit` | Carte |  | P |  |  | P |  |  |  |  |  |  |  |  |  |
| `controleCoprocesseur` | Autres |  |  |  |  |  |  |  | S I ON |  |  |  |  |  |  |
| `controleEcranSysteme` | Autres |  | C ON |  |  |  |  |  |  |  |  |  |  |  |  |
| `controleEnergie` | Autres | S I ON |  |  |  |  |  |  |  |  |  |  |  | S I ON |  |
| `controleMqttLiaison` | Autres |  |  |  |  |  |  |  | S I ON |  |  |  |  |  |  |
| `controleVisuel` | Autres |  |  |  |  |  |  |  |  | S I |  |  |  |  |  |
| `cuvePageFonctions` | Autres |  |  |  |  |  |  |  | S D | S D |  |  |  |  |  |
| `demarrage` | Autres | S I | S I | S I | S | S I | S I | S I | S I | S I | S I | S I | S | S I | S I |
| `ecranFonctions` | Autres |  | S D |  |  | S D |  |  |  |  |  |  |  |  |  |
| `ecranSysteme` | Autres |  | C ON |  |  |  |  |  |  |  |  |  |  |  |  |
| `energieFonctions` | Autres | S D |  |  |  |  |  |  |  |  |  |  |  | S D |  |
| `fsMqtt` | Autres | S | S I | S I | S | S I | S | S | S I | S I | S I | S I | S | S | S I |
| `graphiquesFonctions` | Autres |  |  | S I |  |  | S I | S I | S I | S I | S I | S I | S I |  | S I |
| `historiqueFonctions` | Autres |  |  | S I C ON |  |  | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON | S I C ON |  | S I C ON |
| `historiqueSeries` | Autres |  |  | S I |  |  | S I | S I | S I | S I | S I | S I | S I |  | S I |
| `mqttLiaisonFonctions` | Autres |  |  |  |  |  |  |  | S D |  |  |  |  |  |  |
| `pagesGraphiques` | Autres |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| `pagesGraphiquesValidation` | Autres |  |  | D |  |  | D | D | D | D | D | D | D |  | D |
| `qrcodePage` | Autres |  | S I |  |  |  |  |  | S I |  |  |  |  |  |  |
| `visuelFonctions` | Autres |  |  |  |  |  |  |  |  | S D |  |  |  |  |  |

Envs : `bureau/tasmota32-interrupteur-energie` = `tasmota32-bureau-interrupteur-energie` ; `bureau/tasmota32s3-ecran-debits-pac` = `tasmota32s3-bureau-ecran-debits-pac` ; `bureau/tasmota32s3-serveur-debits-pac` = `tasmota32s3-bureau-serveur-debits-pac` ; `cave/tasmota32-serveur-rly` = `tasmota32-cave-serveur-rly` ; `cave/tasmota32s3-ecran` = `tasmota32s3-cave-ecran` ; `cave/tasmota32s3-serveur-rly` = `tasmota32s3-cave-serveur-rly` ; `etage2/tasmota32s3-grenier` = `tasmota32s3-etage2-grenier` ; `garage/tasmota32p4-serveur-modbus` = `tasmota32p4-garage-serveur-modbus` ; `garage/tasmota32s3-capteurs-cuve-modbus` = `tasmota32s3-garage-capteurs-cuve-modbus` ; `garage/tasmota32s3-portail-jardin-modbus` = `tasmota32s3-garage-portail-jardin-modbus` ; `garage/tasmota32s3-rideau-garage-modbus` = `tasmota32s3-garage-rideau-garage-modbus` ; `garage/tasmota32s3-serveur-modbus` = `tasmota32s3-garage-serveur-modbus` ; `jardin/tasmota32-projecteur-led` = `tasmota32-jardin-projecteur-led` ; `rdc/tasmota32s3-grenier` = `tasmota32s3-rdc-grenier`

## Incoherences detectees

Constats factuels, sans jugement : un module peut etre volontairement dans cet etat.

- L'env `tasmota32-rdc-vr-porte` definit `custom_berry_solidify` mais son dossier `data/rdc/tasmota32-vr-porte` n'existe pas.
- `bureau/tasmota32-interrupteur-energie` : `controleLedTemoin` solidifie, jamais importe ni charge par l'autoexec.
- `bureau/tasmota32-interrupteur-energie` : `controleRangeExtender` solidifie, jamais importe ni charge par l'autoexec.
- `bureau/tasmota32-interrupteur-energie` : `controleTCP` solidifie, jamais importe ni charge par l'autoexec.
- `bureau/tasmota32-interrupteur-energie` : `controleUDP` solidifie, jamais importe ni charge par l'autoexec.
- `bureau/tasmota32-interrupteur-energie` : `fsMqtt` solidifie, jamais importe ni charge par l'autoexec.
- `bureau/tasmota32s3-ecran-debits-pac` : `controleDiscovery` solidifie, jamais importe ni charge par l'autoexec.
- `bureau/tasmota32s3-ecran-debits-pac` : `controleTCP` solidifie, jamais importe ni charge par l'autoexec.
- `bureau/tasmota32s3-ecran-debits-pac` : `preinit.be` est dans le dossier de la carte mais l'autoexec ne le charge pas.
- `bureau/tasmota32s3-serveur-debits-pac` : `controleTCP` solidifie, jamais importe ni charge par l'autoexec.
- `cave/tasmota32-serveur-rly` : `demarrage` solidifie, jamais importe ni charge par l'autoexec.
- `cave/tasmota32-serveur-rly` : `fsMqtt` solidifie, jamais importe ni charge par l'autoexec.
- `cave/tasmota32s3-ecran` : `controleTCP` solidifie, jamais importe ni charge par l'autoexec.
- `cave/tasmota32s3-ecran` : `preinit.be` est dans le dossier de la carte mais l'autoexec ne le charge pas.
- `cave/tasmota32s3-serveur-rly` : `fsMqtt` solidifie, jamais importe ni charge par l'autoexec.
- `etage2/tasmota32s3-grenier` : `fsMqtt` solidifie, jamais importe ni charge par l'autoexec.
- `garage/tasmota32p4-serveur-modbus` : `controleTCP` solidifie, jamais importe ni charge par l'autoexec.
- `garage/tasmota32s3-capteurs-cuve-modbus` : `controleRangeExtender` solidifie, jamais importe ni charge par l'autoexec.
- `garage/tasmota32s3-capteurs-cuve-modbus` : `controleTCP` solidifie, jamais importe ni charge par l'autoexec.
- `garage/tasmota32s3-portail-jardin-modbus` : `controleRangeExtender` solidifie, jamais importe ni charge par l'autoexec.
- `garage/tasmota32s3-portail-jardin-modbus` : `controleTCP` solidifie, jamais importe ni charge par l'autoexec.
- `garage/tasmota32s3-rideau-garage-modbus` : `controleRangeExtender` solidifie, jamais importe ni charge par l'autoexec.
- `garage/tasmota32s3-rideau-garage-modbus` : `controleTCP` solidifie, jamais importe ni charge par l'autoexec.
- `garage/tasmota32s3-serveur-modbus` : `demarrage` solidifie, jamais importe ni charge par l'autoexec.
- `garage/tasmota32s3-serveur-modbus` : `fsMqtt` solidifie, jamais importe ni charge par l'autoexec.
- `jardin/tasmota32-projecteur-led` : `controleLedTemoin` solidifie, jamais importe ni charge par l'autoexec.
- `jardin/tasmota32-projecteur-led` : `controleTCP` solidifie, jamais importe ni charge par l'autoexec.
- `jardin/tasmota32-projecteur-led` : `controleUDP` solidifie, jamais importe ni charge par l'autoexec.
- `jardin/tasmota32-projecteur-led` : `fsMqtt` solidifie, jamais importe ni charge par l'autoexec.
- `data/fs/pagesGraphiques.be` : reference par aucune carte.
- `data/fs/pagesGraphiquesValidation.be` : reference par aucune carte.
- `data/etage2/tasmota32s3-grenier/controleGrenier.be` : fichier vide.

### Informations (normal ou voulu, listees pour memoire)

- `bureau/tasmota32-interrupteur-energie` : `controleDiscovery` : import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute).
- `bureau/tasmota32-interrupteur-energie` : `discoveryFonctions` : charge alors que sa garde vaut OFF.
- `bureau/tasmota32s3-ecran-debits-pac` : `controleEcranSysteme` charge depuis `data/fs` sans etre solidifie (copie sur le FS, compile au demarrage).
- `bureau/tasmota32s3-ecran-debits-pac` : `ecranSysteme` charge depuis `data/fs` sans etre solidifie (copie sur le FS, compile au demarrage).
- `cave/tasmota32-serveur-rly` : `controleDiscovery` : import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute).
- `cave/tasmota32-serveur-rly` : `controleRangeExtender` : import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute).
- `cave/tasmota32-serveur-rly` : `controleTCP` : import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute).
- `cave/tasmota32-serveur-rly` : `controleUDP` : import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute).
- `cave/tasmota32-serveur-rly` : `rangeExtenderFonctions` : charge alors que sa garde vaut OFF.
- `cave/tasmota32-serveur-rly` : `tcpFonctions` : charge alors que sa garde vaut OFF.
- `cave/tasmota32-serveur-rly` : `udpFonctions` : charge alors que sa garde vaut OFF.
- `cave/tasmota32s3-serveur-rly` : `controleTCP` : import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute).
- `cave/tasmota32s3-serveur-rly` : `tcpFonctions` : charge alors que sa garde vaut OFF.
- `cave/tasmota32s3-serveur-rly` : `controleLeds` : import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute).
- `cave/tasmota32s3-serveur-rly` : `ledsFonctions` : charge alors que sa garde vaut OFF.
- `etage2/tasmota32s3-grenier` : `controleTCP` : import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute).
- `etage2/tasmota32s3-grenier` : `controleUDP` : import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute).
- `etage2/tasmota32s3-grenier` : `tcpFonctions` : charge alors que sa garde vaut OFF.
- `etage2/tasmota32s3-grenier` : `udpFonctions` : charge alors que sa garde vaut OFF.
- `etage2/tasmota32s3-grenier` : `controleLeds` : import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute).
- `etage2/tasmota32s3-grenier` : `controleLoRaWan` : import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute).
- `etage2/tasmota32s3-grenier` : `ledsFonctions` : charge alors que sa garde vaut OFF.
- `etage2/tasmota32s3-grenier` : `loRaWanFonctions` : charge alors que sa garde vaut OFF.
- `garage/tasmota32s3-portail-jardin-modbus` : `controleLeds` : import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute).
- `garage/tasmota32s3-portail-jardin-modbus` : `i2c_ads1115` : charge alors que sa garde vaut OFF.
- `garage/tasmota32s3-portail-jardin-modbus` : `i2c_mcp23017` : charge alors que sa garde vaut OFF.
- `garage/tasmota32s3-portail-jardin-modbus` : `ledsFonctions` : charge alors que sa garde vaut OFF.
- `garage/tasmota32s3-rideau-garage-modbus` : `controleLeds` : import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute).
- `garage/tasmota32s3-rideau-garage-modbus` : `i2c_ads1115` : charge alors que sa garde vaut OFF.
- `garage/tasmota32s3-rideau-garage-modbus` : `i2c_mcp23017` : charge alors que sa garde vaut OFF.
- `garage/tasmota32s3-rideau-garage-modbus` : `ledsFonctions` : charge alors que sa garde vaut OFF.
- `garage/tasmota32s3-serveur-modbus` : `controleLeds` : import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute).
- `garage/tasmota32s3-serveur-modbus` : `controleVoletRoulants` : charge alors que sa garde vaut OFF.
- `garage/tasmota32s3-serveur-modbus` : `ledsFonctions` : charge alors que sa garde vaut OFF.
- `garage/tasmota32s3-serveur-modbus` : `vrFonctions` : charge alors que sa garde vaut OFF.
- `rdc/tasmota32s3-grenier` : `controleTCP` : import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute).
- `rdc/tasmota32s3-grenier` : `tcpFonctions` : charge alors que sa garde vaut OFF.

## Diagrammes

Un diagramme par carte (tout dans un seul serait illisible). Modules **charges** par l'autoexec (import / compileModule / loadBerryFile non commentes). Fleche pleine = garde ON ou sans garde ; pointillee = garde OFF ou non evaluable (?).

### bureau/tasmota32-interrupteur-energie

```mermaid
flowchart LR
    CARTE(["bureau/tasmota32-interrupteur-energie"])
    subgraph g_Socle["Socle"]
        m_configDevices["configDevices"]
        m_configGlobal["configGlobal"]
        m_configModules["configModules"]
        m_controleGeneral["controleGeneral"]
        m_controleWeb["controleWeb"]
        m_diversFonctions["diversFonctions"]
        m_gestionFileFolder["gestionFileFolder"]
        m_globalFonctions["globalFonctions"]
        m_logFonctions["logFonctions"]
        m_webFonctions["webFonctions"]
    end
    subgraph g_Reseau["Reseau"]
        m_controleDiscovery["controleDiscovery"]
        m_discoveryFonctions["discoveryFonctions"]
        m_rangeExtenderFonctions["rangeExtenderFonctions"]
        m_tcpFonctions["tcpFonctions"]
        m_udpFonctions["udpFonctions"]
    end
    subgraph g_ModBus["ModBus"]
        m_modbusFonctions["modbusFonctions"]
    end
    subgraph g_Peripheriques["Peripheriques"]
        m_ledsFonctions["ledsFonctions"]
        m_ledsPanelFonctions["ledsPanelFonctions"]
    end
    subgraph g_Autres["Autres"]
        m_controleEnergie["controleEnergie"]
        m_demarrage["demarrage"]
        m_energieFonctions["energieFonctions"]
    end
    CARTE --> m_configDevices
    CARTE --> m_configGlobal
    CARTE --> m_configModules
    CARTE --> m_controleGeneral
    CARTE --> m_controleWeb
    CARTE --> m_diversFonctions
    CARTE --> m_gestionFileFolder
    CARTE --> m_globalFonctions
    CARTE --> m_logFonctions
    CARTE --> m_webFonctions
    CARTE -.-> m_controleDiscovery
    CARTE -.-> m_discoveryFonctions
    m_controleWeb -.->|import| m_rangeExtenderFonctions
    m_discoveryFonctions -.->|import| m_rangeExtenderFonctions
    m_modbusFonctions -.->|import| m_tcpFonctions
    m_modbusFonctions -.->|import| m_udpFonctions
    m_controleGeneral -.->|import| m_modbusFonctions
    m_globalFonctions -.->|import| m_modbusFonctions
    m_rangeExtenderFonctions -.->|import| m_modbusFonctions
    m_tcpFonctions -.->|import| m_modbusFonctions
    m_udpFonctions -.->|import| m_modbusFonctions
    m_modbusFonctions -.->|import| m_ledsFonctions
    m_controleWeb -.->|import| m_ledsPanelFonctions
    m_ledsFonctions -.->|import| m_ledsPanelFonctions
    m_rangeExtenderFonctions -.->|import| m_ledsPanelFonctions
    CARTE --> m_controleEnergie
    CARTE --> m_demarrage
    m_controleEnergie -.->|import| m_energieFonctions
```

### bureau/tasmota32s3-ecran-debits-pac

```mermaid
flowchart LR
    CARTE(["bureau/tasmota32s3-ecran-debits-pac"])
    subgraph g_Socle["Socle"]
        m_configDevices["configDevices"]
        m_configGlobal["configGlobal"]
        m_configModules["configModules"]
        m_controleGeneral["controleGeneral"]
        m_controleLedTemoin["controleLedTemoin"]
        m_controleWeb["controleWeb"]
        m_diversFonctions["diversFonctions"]
        m_gestionFileFolder["gestionFileFolder"]
        m_globalFonctions["globalFonctions"]
        m_logFonctions["logFonctions"]
        m_webFonctions["webFonctions"]
    end
    subgraph g_Reseau["Reseau"]
        m_controleRangeExtender["controleRangeExtender"]
        m_controleUDP["controleUDP"]
        m_discoveryFonctions["discoveryFonctions"]
        m_rangeExtenderFonctions["rangeExtenderFonctions"]
        m_tcpFonctions["tcpFonctions"]
        m_udpFonctions["udpFonctions"]
    end
    subgraph g_ModBus["ModBus"]
        m_controleModbus["controleModbus"]
        m_modBus_Conn16channels["modBus_Conn16channels"]
        m_modBus_TasmotaSlaveModBus["modBus_TasmotaSlaveModBus"]
        m_modbusFonctions["modbusFonctions"]
    end
    subgraph g_Peripheriques["Peripheriques"]
        m_i2c_ads1115["i2c_ads1115"]
        m_i2c_mcp23017["i2c_mcp23017"]
        m_ledsFonctions["ledsFonctions"]
        m_ledsPanelFonctions["ledsPanelFonctions"]
    end
    subgraph g_Carte["Carte"]
        m_controleEcranDebits["controleEcranDebits"]
        m_ecranDebitsFonctions["ecranDebitsFonctions"]
        m_ecranHaspmota["ecranHaspmota"]
        m_ecranLvgl["ecranLvgl"]
    end
    subgraph g_Autres["Autres"]
        m_controleEcranSysteme["controleEcranSysteme"]
        m_demarrage["demarrage"]
        m_ecranFonctions["ecranFonctions"]
        m_ecranSysteme["ecranSysteme"]
        m_fsMqtt["fsMqtt"]
        m_qrcodePage["qrcodePage"]
    end
    CARTE --> m_configDevices
    CARTE --> m_configGlobal
    CARTE --> m_configModules
    CARTE --> m_controleGeneral
    CARTE --> m_controleLedTemoin
    CARTE --> m_controleWeb
    CARTE --> m_diversFonctions
    CARTE --> m_gestionFileFolder
    CARTE --> m_globalFonctions
    CARTE --> m_logFonctions
    CARTE --> m_webFonctions
    CARTE --> m_controleRangeExtender
    CARTE --> m_controleUDP
    m_udpFonctions -.->|import| m_discoveryFonctions
    CARTE --> m_rangeExtenderFonctions
    m_modbusFonctions -.->|import| m_tcpFonctions
    CARTE --> m_udpFonctions
    CARTE --> m_controleModbus
    CARTE --> m_modBus_Conn16channels
    CARTE --> m_modBus_TasmotaSlaveModBus
    CARTE --> m_modbusFonctions
    CARTE --> m_i2c_ads1115
    CARTE --> m_i2c_mcp23017
    m_modbusFonctions -.->|import| m_ledsFonctions
    m_controleWeb -.->|import| m_ledsPanelFonctions
    m_ledsFonctions -.->|import| m_ledsPanelFonctions
    m_rangeExtenderFonctions -.->|import| m_ledsPanelFonctions
    CARTE --> m_controleEcranDebits
    CARTE --> m_ecranDebitsFonctions
    CARTE --> m_ecranHaspmota
    CARTE --> m_ecranLvgl
    CARTE --> m_controleEcranSysteme
    CARTE --> m_demarrage
    m_controleEcranDebits -.->|import| m_ecranFonctions
    m_ecranDebitsFonctions -.->|import| m_ecranFonctions
    m_ecranSysteme -.->|import| m_ecranFonctions
    CARTE --> m_ecranSysteme
    CARTE --> m_fsMqtt
    CARTE --> m_qrcodePage
```

### bureau/tasmota32s3-serveur-debits-pac

```mermaid
flowchart LR
    CARTE(["bureau/tasmota32s3-serveur-debits-pac"])
    subgraph g_Socle["Socle"]
        m_configDevices["configDevices"]
        m_configGlobal["configGlobal"]
        m_configModules["configModules"]
        m_controleGeneral["controleGeneral"]
        m_controleLedTemoin["controleLedTemoin"]
        m_controleWeb["controleWeb"]
        m_diversFonctions["diversFonctions"]
        m_gestionFileFolder["gestionFileFolder"]
        m_globalFonctions["globalFonctions"]
        m_logFonctions["logFonctions"]
        m_webFonctions["webFonctions"]
    end
    subgraph g_Reseau["Reseau"]
        m_controleDiscovery["controleDiscovery"]
        m_controleRangeExtender["controleRangeExtender"]
        m_controleUDP["controleUDP"]
        m_discoveryFonctions["discoveryFonctions"]
        m_rangeExtenderFonctions["rangeExtenderFonctions"]
        m_tcpFonctions["tcpFonctions"]
        m_udpFonctions["udpFonctions"]
    end
    subgraph g_ModBus["ModBus"]
        m_controleModbus["controleModbus"]
        m_modBus_Conn16channels["modBus_Conn16channels"]
        m_modBus_TasmotaSlaveModBus["modBus_TasmotaSlaveModBus"]
        m_modbusFonctions["modbusFonctions"]
    end
    subgraph g_Peripheriques["Peripheriques"]
        m_i2c_ads1115["i2c_ads1115"]
        m_i2c_mcp23017["i2c_mcp23017"]
        m_ledsFonctions["ledsFonctions"]
        m_ledsPanelFonctions["ledsPanelFonctions"]
    end
    subgraph g_Carte["Carte"]
        m_controleDebits["controleDebits"]
        m_debitsFonctions["debitsFonctions"]
        m_equilibragePage["equilibragePage"]
    end
    subgraph g_Autres["Autres"]
        m_demarrage["demarrage"]
        m_fsMqtt["fsMqtt"]
        m_graphiquesFonctions["graphiquesFonctions"]
        m_historiqueFonctions["historiqueFonctions"]
        m_historiqueSeries["historiqueSeries"]
        m_pagesGraphiquesValidation["pagesGraphiquesValidation"]
    end
    CARTE --> m_configDevices
    CARTE --> m_configGlobal
    CARTE --> m_configModules
    CARTE --> m_controleGeneral
    CARTE --> m_controleLedTemoin
    CARTE --> m_controleWeb
    CARTE --> m_diversFonctions
    CARTE --> m_gestionFileFolder
    CARTE --> m_globalFonctions
    CARTE --> m_logFonctions
    CARTE --> m_webFonctions
    CARTE --> m_controleDiscovery
    CARTE --> m_controleRangeExtender
    CARTE --> m_controleUDP
    m_controleDiscovery -.->|import| m_discoveryFonctions
    m_udpFonctions -.->|import| m_discoveryFonctions
    m_controleRangeExtender -.->|import| m_rangeExtenderFonctions
    m_controleWeb -.->|import| m_rangeExtenderFonctions
    m_discoveryFonctions -.->|import| m_rangeExtenderFonctions
    m_modbusFonctions -.->|import| m_tcpFonctions
    CARTE --> m_udpFonctions
    CARTE --> m_controleModbus
    CARTE --> m_modBus_Conn16channels
    CARTE --> m_modBus_TasmotaSlaveModBus
    CARTE --> m_modbusFonctions
    CARTE --> m_i2c_ads1115
    CARTE --> m_i2c_mcp23017
    m_modbusFonctions -.->|import| m_ledsFonctions
    m_controleWeb -.->|import| m_ledsPanelFonctions
    m_ledsFonctions -.->|import| m_ledsPanelFonctions
    m_rangeExtenderFonctions -.->|import| m_ledsPanelFonctions
    CARTE --> m_controleDebits
    CARTE --> m_debitsFonctions
    CARTE --> m_equilibragePage
    CARTE --> m_demarrage
    CARTE --> m_fsMqtt
    CARTE --> m_graphiquesFonctions
    CARTE --> m_historiqueFonctions
    CARTE --> m_historiqueSeries
    m_graphiquesFonctions -.->|import| m_pagesGraphiquesValidation
```

### cave/tasmota32-serveur-rly

```mermaid
flowchart LR
    CARTE(["cave/tasmota32-serveur-rly"])
    subgraph g_Socle["Socle"]
        m_configDevices["configDevices"]
        m_configGlobal["configGlobal"]
        m_configModules["configModules"]
        m_controleGeneral["controleGeneral"]
        m_controleLedTemoin["controleLedTemoin"]
        m_controleWeb["controleWeb"]
        m_diversFonctions["diversFonctions"]
        m_gestionFileFolder["gestionFileFolder"]
        m_globalFonctions["globalFonctions"]
        m_logFonctions["logFonctions"]
        m_webFonctions["webFonctions"]
    end
    subgraph g_Reseau["Reseau"]
        m_controleDiscovery["controleDiscovery"]
        m_controleRangeExtender["controleRangeExtender"]
        m_controleTCP["controleTCP"]
        m_controleUDP["controleUDP"]
        m_discoveryFonctions["discoveryFonctions"]
        m_rangeExtenderFonctions["rangeExtenderFonctions"]
        m_tcpFonctions["tcpFonctions"]
        m_udpFonctions["udpFonctions"]
    end
    subgraph g_ModBus["ModBus"]
        m_modbusFonctions["modbusFonctions"]
    end
    subgraph g_Peripheriques["Peripheriques"]
        m_ledsFonctions["ledsFonctions"]
        m_ledsPanelFonctions["ledsPanelFonctions"]
    end
    subgraph g_Carte["Carte"]
        m_controlePompeVideCave["controlePompeVideCave"]
    end
    CARTE --> m_configDevices
    CARTE --> m_configGlobal
    CARTE --> m_configModules
    CARTE --> m_controleGeneral
    CARTE --> m_controleLedTemoin
    CARTE --> m_controleWeb
    CARTE --> m_diversFonctions
    CARTE --> m_gestionFileFolder
    CARTE --> m_globalFonctions
    CARTE --> m_logFonctions
    CARTE --> m_webFonctions
    CARTE -.-> m_controleDiscovery
    CARTE -.-> m_controleRangeExtender
    CARTE -.-> m_controleTCP
    CARTE -.-> m_controleUDP
    m_udpFonctions -.->|import| m_discoveryFonctions
    m_controleWeb -.->|import| m_rangeExtenderFonctions
    m_discoveryFonctions -.->|import| m_rangeExtenderFonctions
    m_modbusFonctions -.->|import| m_tcpFonctions
    m_modbusFonctions -.->|import| m_udpFonctions
    m_controleGeneral -.->|import| m_modbusFonctions
    m_globalFonctions -.->|import| m_modbusFonctions
    m_rangeExtenderFonctions -.->|import| m_modbusFonctions
    m_tcpFonctions -.->|import| m_modbusFonctions
    m_udpFonctions -.->|import| m_modbusFonctions
    m_modbusFonctions -.->|import| m_ledsFonctions
    m_controleWeb -.->|import| m_ledsPanelFonctions
    m_ledsFonctions -.->|import| m_ledsPanelFonctions
    m_rangeExtenderFonctions -.->|import| m_ledsPanelFonctions
    CARTE --> m_controlePompeVideCave
```

### cave/tasmota32s3-ecran

```mermaid
flowchart LR
    CARTE(["cave/tasmota32s3-ecran"])
    subgraph g_Socle["Socle"]
        m_configDevices["configDevices"]
        m_configGlobal["configGlobal"]
        m_configModules["configModules"]
        m_controleGeneral["controleGeneral"]
        m_controleLedTemoin["controleLedTemoin"]
        m_controleWeb["controleWeb"]
        m_diversFonctions["diversFonctions"]
        m_gestionFileFolder["gestionFileFolder"]
        m_globalFonctions["globalFonctions"]
        m_logFonctions["logFonctions"]
        m_webFonctions["webFonctions"]
    end
    subgraph g_Reseau["Reseau"]
        m_controleDiscovery["controleDiscovery"]
        m_controleRangeExtender["controleRangeExtender"]
        m_controleUDP["controleUDP"]
        m_discoveryFonctions["discoveryFonctions"]
        m_rangeExtenderFonctions["rangeExtenderFonctions"]
        m_tcpFonctions["tcpFonctions"]
        m_udpFonctions["udpFonctions"]
    end
    subgraph g_ModBus["ModBus"]
        m_controleModbus["controleModbus"]
        m_modBus_Conn16channels["modBus_Conn16channels"]
        m_modBus_TasmotaSlaveModBus["modBus_TasmotaSlaveModBus"]
        m_modbusFonctions["modbusFonctions"]
    end
    subgraph g_Peripheriques["Peripheriques"]
        m_i2c_ads1115["i2c_ads1115"]
        m_i2c_mcp23017["i2c_mcp23017"]
        m_ledsFonctions["ledsFonctions"]
        m_ledsPanelFonctions["ledsPanelFonctions"]
    end
    subgraph g_Carte["Carte"]
        m_controleEcranCave["controleEcranCave"]
        m_ecranCaveFonctions["ecranCaveFonctions"]
        m_ecranCaveHaspmota["ecranCaveHaspmota"]
    end
    subgraph g_Autres["Autres"]
        m_demarrage["demarrage"]
        m_ecranFonctions["ecranFonctions"]
        m_fsMqtt["fsMqtt"]
    end
    CARTE --> m_configDevices
    CARTE --> m_configGlobal
    CARTE --> m_configModules
    CARTE --> m_controleGeneral
    CARTE --> m_controleLedTemoin
    CARTE --> m_controleWeb
    CARTE --> m_diversFonctions
    CARTE --> m_gestionFileFolder
    CARTE --> m_globalFonctions
    CARTE --> m_logFonctions
    CARTE --> m_webFonctions
    CARTE --> m_controleDiscovery
    CARTE --> m_controleRangeExtender
    CARTE --> m_controleUDP
    m_controleDiscovery -.->|import| m_discoveryFonctions
    m_udpFonctions -.->|import| m_discoveryFonctions
    CARTE --> m_rangeExtenderFonctions
    m_modbusFonctions -.->|import| m_tcpFonctions
    CARTE --> m_udpFonctions
    CARTE --> m_controleModbus
    CARTE --> m_modBus_Conn16channels
    CARTE --> m_modBus_TasmotaSlaveModBus
    CARTE --> m_modbusFonctions
    CARTE --> m_i2c_ads1115
    CARTE --> m_i2c_mcp23017
    m_modbusFonctions -.->|import| m_ledsFonctions
    m_controleWeb -.->|import| m_ledsPanelFonctions
    m_ledsFonctions -.->|import| m_ledsPanelFonctions
    m_rangeExtenderFonctions -.->|import| m_ledsPanelFonctions
    CARTE --> m_controleEcranCave
    CARTE --> m_ecranCaveFonctions
    CARTE --> m_ecranCaveHaspmota
    CARTE --> m_demarrage
    m_controleEcranCave -.->|import| m_ecranFonctions
    m_ecranCaveHaspmota -.->|import| m_ecranFonctions
    CARTE --> m_fsMqtt
```

### cave/tasmota32s3-serveur-rly

```mermaid
flowchart LR
    CARTE(["cave/tasmota32s3-serveur-rly"])
    subgraph g_Socle["Socle"]
        m_configDevices["configDevices"]
        m_configGlobal["configGlobal"]
        m_configModules["configModules"]
        m_controleGeneral["controleGeneral"]
        m_controleLedTemoin["controleLedTemoin"]
        m_controleWeb["controleWeb"]
        m_diversFonctions["diversFonctions"]
        m_gestionFileFolder["gestionFileFolder"]
        m_globalFonctions["globalFonctions"]
        m_logFonctions["logFonctions"]
        m_webFonctions["webFonctions"]
    end
    subgraph g_Reseau["Reseau"]
        m_controleDiscovery["controleDiscovery"]
        m_controleRangeExtender["controleRangeExtender"]
        m_controleTCP["controleTCP"]
        m_controleUDP["controleUDP"]
        m_discoveryFonctions["discoveryFonctions"]
        m_rangeExtenderFonctions["rangeExtenderFonctions"]
        m_tcpFonctions["tcpFonctions"]
        m_udpFonctions["udpFonctions"]
    end
    subgraph g_ModBus["ModBus"]
        m_controleModbus["controleModbus"]
        m_modBus_Conn16channels["modBus_Conn16channels"]
        m_modBus_TasmotaSlaveModBus["modBus_TasmotaSlaveModBus"]
        m_modbusFonctions["modbusFonctions"]
    end
    subgraph g_Peripheriques["Peripheriques"]
        m_controleLeds["controleLeds"]
        m_i2c_ads1115["i2c_ads1115"]
        m_i2c_mcp23017["i2c_mcp23017"]
        m_ledsFonctions["ledsFonctions"]
        m_ledsPanelFonctions["ledsPanelFonctions"]
    end
    subgraph g_Carte["Carte"]
        m_controleCommandesEcran["controleCommandesEcran"]
        m_controlePompeVideCave["controlePompeVideCave"]
    end
    subgraph g_Autres["Autres"]
        m_demarrage["demarrage"]
        m_graphiquesFonctions["graphiquesFonctions"]
        m_historiqueFonctions["historiqueFonctions"]
        m_historiqueSeries["historiqueSeries"]
        m_pagesGraphiquesValidation["pagesGraphiquesValidation"]
    end
    CARTE --> m_configDevices
    CARTE --> m_configGlobal
    CARTE --> m_configModules
    CARTE --> m_controleGeneral
    CARTE --> m_controleLedTemoin
    CARTE --> m_controleWeb
    CARTE --> m_diversFonctions
    CARTE --> m_gestionFileFolder
    CARTE --> m_globalFonctions
    CARTE --> m_logFonctions
    CARTE --> m_webFonctions
    CARTE --> m_controleDiscovery
    CARTE --> m_controleRangeExtender
    CARTE -.-> m_controleTCP
    CARTE --> m_controleUDP
    m_controleDiscovery -.->|import| m_discoveryFonctions
    m_udpFonctions -.->|import| m_discoveryFonctions
    CARTE --> m_rangeExtenderFonctions
    CARTE -.-> m_tcpFonctions
    CARTE --> m_udpFonctions
    CARTE --> m_controleModbus
    CARTE --> m_modBus_Conn16channels
    CARTE --> m_modBus_TasmotaSlaveModBus
    CARTE --> m_modbusFonctions
    CARTE -.-> m_controleLeds
    CARTE --> m_i2c_ads1115
    CARTE --> m_i2c_mcp23017
    m_modbusFonctions -.->|import| m_ledsFonctions
    m_controleWeb -.->|import| m_ledsPanelFonctions
    m_ledsFonctions -.->|import| m_ledsPanelFonctions
    m_rangeExtenderFonctions -.->|import| m_ledsPanelFonctions
    CARTE --> m_controleCommandesEcran
    CARTE --> m_controlePompeVideCave
    CARTE --> m_demarrage
    CARTE --> m_graphiquesFonctions
    CARTE --> m_historiqueFonctions
    CARTE --> m_historiqueSeries
    m_graphiquesFonctions -.->|import| m_pagesGraphiquesValidation
```

### etage2/tasmota32s3-grenier

```mermaid
flowchart LR
    CARTE(["etage2/tasmota32s3-grenier"])
    subgraph g_Socle["Socle"]
        m_configDevices["configDevices"]
        m_configGlobal["configGlobal"]
        m_configModules["configModules"]
        m_controleGeneral["controleGeneral"]
        m_controleLedTemoin["controleLedTemoin"]
        m_controleWeb["controleWeb"]
        m_diversFonctions["diversFonctions"]
        m_gestionFileFolder["gestionFileFolder"]
        m_globalFonctions["globalFonctions"]
        m_logFonctions["logFonctions"]
        m_webFonctions["webFonctions"]
    end
    subgraph g_Reseau["Reseau"]
        m_controleDiscovery["controleDiscovery"]
        m_controleRangeExtender["controleRangeExtender"]
        m_controleTCP["controleTCP"]
        m_controleUDP["controleUDP"]
        m_discoveryFonctions["discoveryFonctions"]
        m_rangeExtenderFonctions["rangeExtenderFonctions"]
        m_tcpFonctions["tcpFonctions"]
        m_udpFonctions["udpFonctions"]
    end
    subgraph g_ModBus["ModBus"]
        m_modbusFonctions["modbusFonctions"]
    end
    subgraph g_Peripheriques["Peripheriques"]
        m_controleLeds["controleLeds"]
        m_controleLoRaWan["controleLoRaWan"]
        m_controleVoletRoulants["controleVoletRoulants"]
        m_ledsFonctions["ledsFonctions"]
        m_ledsPanelFonctions["ledsPanelFonctions"]
        m_loRaWanFonctions["loRaWanFonctions"]
        m_vrFonctions["vrFonctions"]
        m_vrPages["vrPages"]
        m_vrReglage["vrReglage"]
    end
    subgraph g_Carte["Carte"]
        m_controleGrenier["controleGrenier"]
    end
    subgraph g_Autres["Autres"]
        m_demarrage["demarrage"]
        m_graphiquesFonctions["graphiquesFonctions"]
        m_historiqueFonctions["historiqueFonctions"]
        m_historiqueSeries["historiqueSeries"]
        m_pagesGraphiquesValidation["pagesGraphiquesValidation"]
    end
    CARTE --> m_configDevices
    CARTE --> m_configGlobal
    CARTE --> m_configModules
    CARTE --> m_controleGeneral
    CARTE --> m_controleLedTemoin
    CARTE --> m_controleWeb
    CARTE --> m_diversFonctions
    CARTE --> m_gestionFileFolder
    CARTE --> m_globalFonctions
    CARTE --> m_logFonctions
    CARTE --> m_webFonctions
    CARTE --> m_controleDiscovery
    CARTE --> m_controleRangeExtender
    CARTE -.-> m_controleTCP
    CARTE -.-> m_controleUDP
    m_controleDiscovery -.->|import| m_discoveryFonctions
    m_udpFonctions -.->|import| m_discoveryFonctions
    CARTE --> m_rangeExtenderFonctions
    CARTE -.-> m_tcpFonctions
    CARTE -.-> m_udpFonctions
    m_controleGeneral -.->|import| m_modbusFonctions
    m_globalFonctions -.->|import| m_modbusFonctions
    m_rangeExtenderFonctions -.->|import| m_modbusFonctions
    m_tcpFonctions -.->|import| m_modbusFonctions
    m_udpFonctions -.->|import| m_modbusFonctions
    CARTE -.-> m_controleLeds
    CARTE -.-> m_controleLoRaWan
    CARTE --> m_controleVoletRoulants
    m_modbusFonctions -.->|import| m_ledsFonctions
    m_controleWeb -.->|import| m_ledsPanelFonctions
    m_ledsFonctions -.->|import| m_ledsPanelFonctions
    m_rangeExtenderFonctions -.->|import| m_ledsPanelFonctions
    CARTE -.-> m_loRaWanFonctions
    CARTE --> m_vrFonctions
    m_controleVoletRoulants -.->|import| m_vrPages
    m_controleVoletRoulants -.->|import| m_vrReglage
    m_vrPages -.->|import| m_vrReglage
    CARTE --> m_controleGrenier
    CARTE --> m_demarrage
    CARTE --> m_graphiquesFonctions
    CARTE --> m_historiqueFonctions
    CARTE --> m_historiqueSeries
    m_graphiquesFonctions -.->|import| m_pagesGraphiquesValidation
```

### garage/tasmota32p4-serveur-modbus

```mermaid
flowchart LR
    CARTE(["garage/tasmota32p4-serveur-modbus"])
    subgraph g_Socle["Socle"]
        m_configDevices["configDevices"]
        m_configGlobal["configGlobal"]
        m_configModules["configModules"]
        m_controleGeneral["controleGeneral"]
        m_controleLedTemoin["controleLedTemoin"]
        m_controleWeb["controleWeb"]
        m_diversFonctions["diversFonctions"]
        m_gestionFileFolder["gestionFileFolder"]
        m_globalFonctions["globalFonctions"]
        m_logFonctions["logFonctions"]
        m_webFonctions["webFonctions"]
    end
    subgraph g_Reseau["Reseau"]
        m_controleDiscovery["controleDiscovery"]
        m_controleRangeExtender["controleRangeExtender"]
        m_controleUDP["controleUDP"]
        m_discoveryFonctions["discoveryFonctions"]
        m_rangeExtenderFonctions["rangeExtenderFonctions"]
        m_tcpFonctions["tcpFonctions"]
        m_udpFonctions["udpFonctions"]
    end
    subgraph g_ModBus["ModBus"]
        m_controleModbus["controleModbus"]
        m_modBus_Conn16channels["modBus_Conn16channels"]
        m_modBus_TasmotaSlaveModBus["modBus_TasmotaSlaveModBus"]
        m_modbusFonctions["modbusFonctions"]
    end
    subgraph g_Peripheriques["Peripheriques"]
        m_controleES8311["controleES8311"]
        m_controleVoletRoulants["controleVoletRoulants"]
        m_i2c_ads1115["i2c_ads1115"]
        m_i2c_mcp23017["i2c_mcp23017"]
        m_ledsFonctions["ledsFonctions"]
        m_ledsPanelFonctions["ledsPanelFonctions"]
        m_vrFonctions["vrFonctions"]
        m_vrPages["vrPages"]
        m_vrReglage["vrReglage"]
    end
    subgraph g_Carte["Carte"]
        m_controleGarage["controleGarage"]
        m_garageFonctions["garageFonctions"]
    end
    subgraph g_Autres["Autres"]
        m_controleCoprocesseur["controleCoprocesseur"]
        m_controleMqttLiaison["controleMqttLiaison"]
        m_cuvePageFonctions["cuvePageFonctions"]
        m_demarrage["demarrage"]
        m_fsMqtt["fsMqtt"]
        m_graphiquesFonctions["graphiquesFonctions"]
        m_historiqueFonctions["historiqueFonctions"]
        m_historiqueSeries["historiqueSeries"]
        m_mqttLiaisonFonctions["mqttLiaisonFonctions"]
        m_pagesGraphiquesValidation["pagesGraphiquesValidation"]
        m_qrcodePage["qrcodePage"]
    end
    CARTE --> m_configDevices
    CARTE --> m_configGlobal
    CARTE --> m_configModules
    CARTE --> m_controleGeneral
    CARTE --> m_controleLedTemoin
    CARTE --> m_controleWeb
    CARTE --> m_diversFonctions
    CARTE --> m_gestionFileFolder
    CARTE --> m_globalFonctions
    CARTE --> m_logFonctions
    CARTE --> m_webFonctions
    CARTE --> m_controleDiscovery
    CARTE --> m_controleRangeExtender
    CARTE --> m_controleUDP
    CARTE --> m_discoveryFonctions
    m_controleRangeExtender -.->|import| m_rangeExtenderFonctions
    m_controleWeb -.->|import| m_rangeExtenderFonctions
    m_discoveryFonctions -.->|import| m_rangeExtenderFonctions
    m_modbusFonctions -.->|import| m_tcpFonctions
    CARTE --> m_udpFonctions
    CARTE --> m_controleModbus
    CARTE --> m_modBus_Conn16channels
    CARTE --> m_modBus_TasmotaSlaveModBus
    CARTE --> m_modbusFonctions
    CARTE --> m_controleES8311
    CARTE --> m_controleVoletRoulants
    CARTE --> m_i2c_ads1115
    CARTE --> m_i2c_mcp23017
    m_modbusFonctions -.->|import| m_ledsFonctions
    m_controleWeb -.->|import| m_ledsPanelFonctions
    m_ledsFonctions -.->|import| m_ledsPanelFonctions
    m_rangeExtenderFonctions -.->|import| m_ledsPanelFonctions
    m_controleVoletRoulants -.->|import| m_vrFonctions
    m_vrPages -.->|import| m_vrFonctions
    m_vrReglage -.->|import| m_vrFonctions
    m_controleVoletRoulants -.->|import| m_vrPages
    m_controleVoletRoulants -.->|import| m_vrReglage
    m_vrPages -.->|import| m_vrReglage
    CARTE --> m_controleGarage
    CARTE --> m_garageFonctions
    CARTE --> m_controleCoprocesseur
    CARTE --> m_controleMqttLiaison
    m_controleGarage -.->|import| m_cuvePageFonctions
    CARTE --> m_demarrage
    CARTE --> m_fsMqtt
    CARTE --> m_graphiquesFonctions
    CARTE --> m_historiqueFonctions
    CARTE --> m_historiqueSeries
    m_controleMqttLiaison -.->|import| m_mqttLiaisonFonctions
    m_graphiquesFonctions -.->|import| m_pagesGraphiquesValidation
    CARTE --> m_qrcodePage
```

### garage/tasmota32s3-capteurs-cuve-modbus

```mermaid
flowchart LR
    CARTE(["garage/tasmota32s3-capteurs-cuve-modbus"])
    subgraph g_Socle["Socle"]
        m_configDevices["configDevices"]
        m_configGlobal["configGlobal"]
        m_configModules["configModules"]
        m_controleGeneral["controleGeneral"]
        m_controleLedTemoin["controleLedTemoin"]
        m_controleWeb["controleWeb"]
        m_diversFonctions["diversFonctions"]
        m_gestionFileFolder["gestionFileFolder"]
        m_globalFonctions["globalFonctions"]
        m_logFonctions["logFonctions"]
        m_webFonctions["webFonctions"]
    end
    subgraph g_Reseau["Reseau"]
        m_controleDiscovery["controleDiscovery"]
        m_controleUDP["controleUDP"]
        m_discoveryFonctions["discoveryFonctions"]
        m_rangeExtenderFonctions["rangeExtenderFonctions"]
        m_tcpFonctions["tcpFonctions"]
        m_udpFonctions["udpFonctions"]
    end
    subgraph g_ModBus["ModBus"]
        m_controleModbus["controleModbus"]
        m_modBus_Conn16channels["modBus_Conn16channels"]
        m_modBus_TasmotaSlaveModBus["modBus_TasmotaSlaveModBus"]
        m_modbusFonctions["modbusFonctions"]
    end
    subgraph g_Peripheriques["Peripheriques"]
        m_controleLeds["controleLeds"]
        m_i2c_ads1115["i2c_ads1115"]
        m_i2c_mcp23017["i2c_mcp23017"]
        m_ledsFonctions["ledsFonctions"]
        m_ledsPanelFonctions["ledsPanelFonctions"]
    end
    subgraph g_Carte["Carte"]
        m_controleCuve["controleCuve"]
        m_cuveFonctions["cuveFonctions"]
    end
    subgraph g_Autres["Autres"]
        m_controleVisuel["controleVisuel"]
        m_cuvePageFonctions["cuvePageFonctions"]
        m_demarrage["demarrage"]
        m_fsMqtt["fsMqtt"]
        m_graphiquesFonctions["graphiquesFonctions"]
        m_historiqueFonctions["historiqueFonctions"]
        m_historiqueSeries["historiqueSeries"]
        m_pagesGraphiquesValidation["pagesGraphiquesValidation"]
        m_visuelFonctions["visuelFonctions"]
    end
    CARTE --> m_configDevices
    CARTE --> m_configGlobal
    CARTE --> m_configModules
    CARTE --> m_controleGeneral
    CARTE --> m_controleLedTemoin
    CARTE --> m_controleWeb
    CARTE --> m_diversFonctions
    CARTE --> m_gestionFileFolder
    CARTE --> m_globalFonctions
    CARTE --> m_logFonctions
    CARTE --> m_webFonctions
    CARTE --> m_controleDiscovery
    CARTE --> m_controleUDP
    CARTE --> m_discoveryFonctions
    m_controleWeb -.->|import| m_rangeExtenderFonctions
    m_discoveryFonctions -.->|import| m_rangeExtenderFonctions
    m_modbusFonctions -.->|import| m_tcpFonctions
    CARTE --> m_udpFonctions
    CARTE --> m_controleModbus
    CARTE --> m_modBus_Conn16channels
    CARTE --> m_modBus_TasmotaSlaveModBus
    CARTE --> m_modbusFonctions
    CARTE -.-> m_controleLeds
    CARTE --> m_i2c_ads1115
    CARTE --> m_i2c_mcp23017
    CARTE --> m_ledsFonctions
    m_controleWeb -.->|import| m_ledsPanelFonctions
    m_ledsFonctions -.->|import| m_ledsPanelFonctions
    m_rangeExtenderFonctions -.->|import| m_ledsPanelFonctions
    CARTE --> m_controleCuve
    CARTE --> m_cuveFonctions
    CARTE --> m_controleVisuel
    m_controleCuve -.->|import| m_cuvePageFonctions
    CARTE --> m_demarrage
    CARTE --> m_fsMqtt
    CARTE --> m_graphiquesFonctions
    CARTE --> m_historiqueFonctions
    CARTE --> m_historiqueSeries
    m_graphiquesFonctions -.->|import| m_pagesGraphiquesValidation
    m_controleVisuel -.->|import| m_visuelFonctions
```

### garage/tasmota32s3-portail-jardin-modbus

```mermaid
flowchart LR
    CARTE(["garage/tasmota32s3-portail-jardin-modbus"])
    subgraph g_Socle["Socle"]
        m_configDevices["configDevices"]
        m_configGlobal["configGlobal"]
        m_configModules["configModules"]
        m_controleGeneral["controleGeneral"]
        m_controleLedTemoin["controleLedTemoin"]
        m_controleWeb["controleWeb"]
        m_diversFonctions["diversFonctions"]
        m_gestionFileFolder["gestionFileFolder"]
        m_globalFonctions["globalFonctions"]
        m_logFonctions["logFonctions"]
        m_webFonctions["webFonctions"]
    end
    subgraph g_Reseau["Reseau"]
        m_controleDiscovery["controleDiscovery"]
        m_controleUDP["controleUDP"]
        m_discoveryFonctions["discoveryFonctions"]
        m_rangeExtenderFonctions["rangeExtenderFonctions"]
        m_tcpFonctions["tcpFonctions"]
        m_udpFonctions["udpFonctions"]
    end
    subgraph g_ModBus["ModBus"]
        m_controleModbus["controleModbus"]
        m_modBus_Conn16channels["modBus_Conn16channels"]
        m_modBus_TasmotaSlaveModBus["modBus_TasmotaSlaveModBus"]
        m_modbusFonctions["modbusFonctions"]
    end
    subgraph g_Peripheriques["Peripheriques"]
        m_controleLeds["controleLeds"]
        m_i2c_ads1115["i2c_ads1115"]
        m_i2c_mcp23017["i2c_mcp23017"]
        m_ledsFonctions["ledsFonctions"]
        m_ledsPanelFonctions["ledsPanelFonctions"]
    end
    subgraph g_Carte["Carte"]
        m_controlePortail["controlePortail"]
    end
    subgraph g_Autres["Autres"]
        m_demarrage["demarrage"]
        m_fsMqtt["fsMqtt"]
        m_graphiquesFonctions["graphiquesFonctions"]
        m_historiqueFonctions["historiqueFonctions"]
        m_historiqueSeries["historiqueSeries"]
        m_pagesGraphiquesValidation["pagesGraphiquesValidation"]
    end
    CARTE --> m_configDevices
    CARTE --> m_configGlobal
    CARTE --> m_configModules
    CARTE --> m_controleGeneral
    CARTE --> m_controleLedTemoin
    CARTE --> m_controleWeb
    CARTE --> m_diversFonctions
    CARTE --> m_gestionFileFolder
    CARTE --> m_globalFonctions
    CARTE --> m_logFonctions
    CARTE --> m_webFonctions
    CARTE --> m_controleDiscovery
    CARTE --> m_controleUDP
    CARTE --> m_discoveryFonctions
    m_controleWeb -.->|import| m_rangeExtenderFonctions
    m_discoveryFonctions -.->|import| m_rangeExtenderFonctions
    m_modbusFonctions -.->|import| m_tcpFonctions
    CARTE --> m_udpFonctions
    CARTE --> m_controleModbus
    CARTE --> m_modBus_Conn16channels
    CARTE --> m_modBus_TasmotaSlaveModBus
    CARTE --> m_modbusFonctions
    CARTE -.-> m_controleLeds
    CARTE -.-> m_i2c_ads1115
    CARTE -.-> m_i2c_mcp23017
    m_modbusFonctions -.->|import| m_ledsFonctions
    m_controleWeb -.->|import| m_ledsPanelFonctions
    m_ledsFonctions -.->|import| m_ledsPanelFonctions
    m_rangeExtenderFonctions -.->|import| m_ledsPanelFonctions
    CARTE --> m_controlePortail
    CARTE --> m_demarrage
    CARTE --> m_fsMqtt
    CARTE --> m_graphiquesFonctions
    CARTE --> m_historiqueFonctions
    CARTE --> m_historiqueSeries
    m_graphiquesFonctions -.->|import| m_pagesGraphiquesValidation
```

### garage/tasmota32s3-rideau-garage-modbus

```mermaid
flowchart LR
    CARTE(["garage/tasmota32s3-rideau-garage-modbus"])
    subgraph g_Socle["Socle"]
        m_configDevices["configDevices"]
        m_configGlobal["configGlobal"]
        m_configModules["configModules"]
        m_controleGeneral["controleGeneral"]
        m_controleLedTemoin["controleLedTemoin"]
        m_controleWeb["controleWeb"]
        m_diversFonctions["diversFonctions"]
        m_gestionFileFolder["gestionFileFolder"]
        m_globalFonctions["globalFonctions"]
        m_logFonctions["logFonctions"]
        m_webFonctions["webFonctions"]
    end
    subgraph g_Reseau["Reseau"]
        m_controleDiscovery["controleDiscovery"]
        m_controleUDP["controleUDP"]
        m_discoveryFonctions["discoveryFonctions"]
        m_rangeExtenderFonctions["rangeExtenderFonctions"]
        m_tcpFonctions["tcpFonctions"]
        m_udpFonctions["udpFonctions"]
    end
    subgraph g_ModBus["ModBus"]
        m_controleModbus["controleModbus"]
        m_modBus_Conn16channels["modBus_Conn16channels"]
        m_modBus_TasmotaSlaveModBus["modBus_TasmotaSlaveModBus"]
        m_modbusFonctions["modbusFonctions"]
    end
    subgraph g_Peripheriques["Peripheriques"]
        m_controleLeds["controleLeds"]
        m_i2c_ads1115["i2c_ads1115"]
        m_i2c_mcp23017["i2c_mcp23017"]
        m_ledsFonctions["ledsFonctions"]
        m_ledsPanelFonctions["ledsPanelFonctions"]
    end
    subgraph g_Carte["Carte"]
        m_controleRideau["controleRideau"]
    end
    subgraph g_Autres["Autres"]
        m_demarrage["demarrage"]
        m_fsMqtt["fsMqtt"]
        m_graphiquesFonctions["graphiquesFonctions"]
        m_historiqueFonctions["historiqueFonctions"]
        m_historiqueSeries["historiqueSeries"]
        m_pagesGraphiquesValidation["pagesGraphiquesValidation"]
    end
    CARTE --> m_configDevices
    CARTE --> m_configGlobal
    CARTE --> m_configModules
    CARTE --> m_controleGeneral
    CARTE --> m_controleLedTemoin
    CARTE --> m_controleWeb
    CARTE --> m_diversFonctions
    CARTE --> m_gestionFileFolder
    CARTE --> m_globalFonctions
    CARTE --> m_logFonctions
    CARTE --> m_webFonctions
    CARTE --> m_controleDiscovery
    CARTE --> m_controleUDP
    CARTE --> m_discoveryFonctions
    m_controleWeb -.->|import| m_rangeExtenderFonctions
    m_discoveryFonctions -.->|import| m_rangeExtenderFonctions
    m_modbusFonctions -.->|import| m_tcpFonctions
    CARTE --> m_udpFonctions
    CARTE --> m_controleModbus
    CARTE --> m_modBus_Conn16channels
    CARTE --> m_modBus_TasmotaSlaveModBus
    CARTE --> m_modbusFonctions
    CARTE -.-> m_controleLeds
    CARTE -.-> m_i2c_ads1115
    CARTE -.-> m_i2c_mcp23017
    m_modbusFonctions -.->|import| m_ledsFonctions
    m_controleWeb -.->|import| m_ledsPanelFonctions
    m_ledsFonctions -.->|import| m_ledsPanelFonctions
    m_rangeExtenderFonctions -.->|import| m_ledsPanelFonctions
    CARTE --> m_controleRideau
    CARTE --> m_demarrage
    CARTE --> m_fsMqtt
    CARTE --> m_graphiquesFonctions
    CARTE --> m_historiqueFonctions
    CARTE --> m_historiqueSeries
    m_graphiquesFonctions -.->|import| m_pagesGraphiquesValidation
```

### garage/tasmota32s3-serveur-modbus

```mermaid
flowchart LR
    CARTE(["garage/tasmota32s3-serveur-modbus"])
    subgraph g_Socle["Socle"]
        m_configDevices["configDevices"]
        m_configGlobal["configGlobal"]
        m_configModules["configModules"]
        m_controleGeneral["controleGeneral"]
        m_controleLedTemoin["controleLedTemoin"]
        m_controleWeb["controleWeb"]
        m_diversFonctions["diversFonctions"]
        m_gestionFileFolder["gestionFileFolder"]
        m_globalFonctions["globalFonctions"]
        m_logFonctions["logFonctions"]
        m_webFonctions["webFonctions"]
    end
    subgraph g_Reseau["Reseau"]
        m_controleDiscovery["controleDiscovery"]
        m_controleRangeExtender["controleRangeExtender"]
        m_controleTCP["controleTCP"]
        m_controleUDP["controleUDP"]
        m_discoveryFonctions["discoveryFonctions"]
        m_rangeExtenderFonctions["rangeExtenderFonctions"]
        m_tcpFonctions["tcpFonctions"]
        m_udpFonctions["udpFonctions"]
    end
    subgraph g_ModBus["ModBus"]
        m_controleModbus["controleModbus"]
        m_modBus_Conn16channels["modBus_Conn16channels"]
        m_modBus_TasmotaSlaveModBus["modBus_TasmotaSlaveModBus"]
        m_modbusFonctions["modbusFonctions"]
    end
    subgraph g_Peripheriques["Peripheriques"]
        m_controleLeds["controleLeds"]
        m_controleLoRaWan["controleLoRaWan"]
        m_controleVoletRoulants["controleVoletRoulants"]
        m_i2c_ads1115["i2c_ads1115"]
        m_i2c_mcp23017["i2c_mcp23017"]
        m_ledsFonctions["ledsFonctions"]
        m_ledsPanelFonctions["ledsPanelFonctions"]
        m_loRaWanFonctions["loRaWanFonctions"]
        m_vrFonctions["vrFonctions"]
        m_vrPages["vrPages"]
        m_vrReglage["vrReglage"]
    end
    subgraph g_Carte["Carte"]
        m_controleGarage["controleGarage"]
        m_garageFonctions["garageFonctions"]
    end
    subgraph g_Autres["Autres"]
        m_graphiquesFonctions["graphiquesFonctions"]
        m_historiqueFonctions["historiqueFonctions"]
        m_historiqueSeries["historiqueSeries"]
        m_pagesGraphiquesValidation["pagesGraphiquesValidation"]
    end
    CARTE --> m_configDevices
    CARTE --> m_configGlobal
    CARTE --> m_configModules
    CARTE --> m_controleGeneral
    CARTE --> m_controleLedTemoin
    CARTE --> m_controleWeb
    CARTE --> m_diversFonctions
    CARTE --> m_gestionFileFolder
    CARTE --> m_globalFonctions
    CARTE --> m_logFonctions
    CARTE --> m_webFonctions
    CARTE --> m_controleDiscovery
    CARTE --> m_controleRangeExtender
    CARTE --> m_controleTCP
    CARTE --> m_controleUDP
    CARTE --> m_discoveryFonctions
    CARTE --> m_rangeExtenderFonctions
    CARTE --> m_tcpFonctions
    CARTE --> m_udpFonctions
    CARTE --> m_controleModbus
    CARTE --> m_modBus_Conn16channels
    CARTE --> m_modBus_TasmotaSlaveModBus
    CARTE --> m_modbusFonctions
    CARTE -.-> m_controleLeds
    CARTE --> m_controleLoRaWan
    CARTE -.-> m_controleVoletRoulants
    CARTE --> m_i2c_ads1115
    CARTE --> m_i2c_mcp23017
    m_modbusFonctions -.->|import| m_ledsFonctions
    m_controleWeb -.->|import| m_ledsPanelFonctions
    m_ledsFonctions -.->|import| m_ledsPanelFonctions
    m_rangeExtenderFonctions -.->|import| m_ledsPanelFonctions
    CARTE --> m_loRaWanFonctions
    CARTE -.-> m_vrFonctions
    m_controleVoletRoulants -.->|import| m_vrPages
    m_controleVoletRoulants -.->|import| m_vrReglage
    m_vrPages -.->|import| m_vrReglage
    CARTE --> m_controleGarage
    CARTE --> m_garageFonctions
    CARTE --> m_graphiquesFonctions
    CARTE --> m_historiqueFonctions
    CARTE --> m_historiqueSeries
    m_graphiquesFonctions -.->|import| m_pagesGraphiquesValidation
```

### jardin/tasmota32-projecteur-led

```mermaid
flowchart LR
    CARTE(["jardin/tasmota32-projecteur-led"])
    subgraph g_Socle["Socle"]
        m_configDevices["configDevices"]
        m_configGlobal["configGlobal"]
        m_configModules["configModules"]
        m_controleGeneral["controleGeneral"]
        m_controleWeb["controleWeb"]
        m_diversFonctions["diversFonctions"]
        m_gestionFileFolder["gestionFileFolder"]
        m_globalFonctions["globalFonctions"]
        m_logFonctions["logFonctions"]
        m_webFonctions["webFonctions"]
    end
    subgraph g_Reseau["Reseau"]
        m_controleDiscovery["controleDiscovery"]
        m_controleRangeExtender["controleRangeExtender"]
        m_discoveryFonctions["discoveryFonctions"]
        m_rangeExtenderFonctions["rangeExtenderFonctions"]
        m_tcpFonctions["tcpFonctions"]
        m_udpFonctions["udpFonctions"]
    end
    subgraph g_ModBus["ModBus"]
        m_modbusFonctions["modbusFonctions"]
    end
    subgraph g_Peripheriques["Peripheriques"]
        m_ledsFonctions["ledsFonctions"]
        m_ledsPanelFonctions["ledsPanelFonctions"]
    end
    subgraph g_Autres["Autres"]
        m_controleEnergie["controleEnergie"]
        m_demarrage["demarrage"]
        m_energieFonctions["energieFonctions"]
    end
    CARTE --> m_configDevices
    CARTE --> m_configGlobal
    CARTE --> m_configModules
    CARTE --> m_controleGeneral
    CARTE --> m_controleWeb
    CARTE --> m_diversFonctions
    CARTE --> m_gestionFileFolder
    CARTE --> m_globalFonctions
    CARTE --> m_logFonctions
    CARTE --> m_webFonctions
    CARTE --> m_controleDiscovery
    CARTE --> m_controleRangeExtender
    CARTE --> m_discoveryFonctions
    CARTE --> m_rangeExtenderFonctions
    m_modbusFonctions -.->|import| m_tcpFonctions
    m_modbusFonctions -.->|import| m_udpFonctions
    m_controleGeneral -.->|import| m_modbusFonctions
    m_globalFonctions -.->|import| m_modbusFonctions
    m_rangeExtenderFonctions -.->|import| m_modbusFonctions
    m_tcpFonctions -.->|import| m_modbusFonctions
    m_udpFonctions -.->|import| m_modbusFonctions
    m_modbusFonctions -.->|import| m_ledsFonctions
    m_controleWeb -.->|import| m_ledsPanelFonctions
    m_ledsFonctions -.->|import| m_ledsPanelFonctions
    m_rangeExtenderFonctions -.->|import| m_ledsPanelFonctions
    CARTE --> m_controleEnergie
    CARTE --> m_demarrage
    m_controleEnergie -.->|import| m_energieFonctions
```

### rdc/tasmota32s3-grenier

```mermaid
flowchart LR
    CARTE(["rdc/tasmota32s3-grenier"])
    subgraph g_Socle["Socle"]
        m_configDevices["configDevices"]
        m_configGlobal["configGlobal"]
        m_configModules["configModules"]
        m_controleGeneral["controleGeneral"]
        m_controleLedTemoin["controleLedTemoin"]
        m_controleWeb["controleWeb"]
        m_diversFonctions["diversFonctions"]
        m_gestionFileFolder["gestionFileFolder"]
        m_globalFonctions["globalFonctions"]
        m_logFonctions["logFonctions"]
        m_webFonctions["webFonctions"]
    end
    subgraph g_Reseau["Reseau"]
        m_controleDiscovery["controleDiscovery"]
        m_controleRangeExtender["controleRangeExtender"]
        m_controleTCP["controleTCP"]
        m_controleUDP["controleUDP"]
        m_discoveryFonctions["discoveryFonctions"]
        m_rangeExtenderFonctions["rangeExtenderFonctions"]
        m_tcpFonctions["tcpFonctions"]
        m_udpFonctions["udpFonctions"]
    end
    subgraph g_ModBus["ModBus"]
        m_controleModbus["controleModbus"]
        m_modBus_Conn16channels["modBus_Conn16channels"]
        m_modBus_TasmotaSlaveModBus["modBus_TasmotaSlaveModBus"]
        m_modbusFonctions["modbusFonctions"]
    end
    subgraph g_Peripheriques["Peripheriques"]
        m_controleLeds["controleLeds"]
        m_controleVoletRoulants["controleVoletRoulants"]
        m_i2c_ads1115["i2c_ads1115"]
        m_i2c_mcp23017["i2c_mcp23017"]
        m_ledsFonctions["ledsFonctions"]
        m_ledsPanelFonctions["ledsPanelFonctions"]
        m_vrFonctions["vrFonctions"]
        m_vrPages["vrPages"]
        m_vrReglage["vrReglage"]
    end
    subgraph g_Autres["Autres"]
        m_demarrage["demarrage"]
        m_fsMqtt["fsMqtt"]
        m_graphiquesFonctions["graphiquesFonctions"]
        m_historiqueFonctions["historiqueFonctions"]
        m_historiqueSeries["historiqueSeries"]
        m_pagesGraphiquesValidation["pagesGraphiquesValidation"]
    end
    CARTE --> m_configDevices
    CARTE --> m_configGlobal
    CARTE --> m_configModules
    CARTE --> m_controleGeneral
    CARTE --> m_controleLedTemoin
    CARTE --> m_controleWeb
    CARTE --> m_diversFonctions
    CARTE --> m_gestionFileFolder
    CARTE --> m_globalFonctions
    CARTE --> m_logFonctions
    CARTE --> m_webFonctions
    CARTE --> m_controleDiscovery
    CARTE --> m_controleRangeExtender
    CARTE -.-> m_controleTCP
    CARTE --> m_controleUDP
    m_controleDiscovery -.->|import| m_discoveryFonctions
    m_udpFonctions -.->|import| m_discoveryFonctions
    CARTE --> m_rangeExtenderFonctions
    CARTE -.-> m_tcpFonctions
    CARTE --> m_udpFonctions
    CARTE --> m_controleModbus
    CARTE --> m_modBus_Conn16channels
    CARTE --> m_modBus_TasmotaSlaveModBus
    CARTE --> m_modbusFonctions
    CARTE -.-> m_controleLeds
    CARTE --> m_controleVoletRoulants
    CARTE --> m_i2c_ads1115
    CARTE --> m_i2c_mcp23017
    CARTE --> m_ledsFonctions
    m_controleWeb -.->|import| m_ledsPanelFonctions
    m_ledsFonctions -.->|import| m_ledsPanelFonctions
    m_rangeExtenderFonctions -.->|import| m_ledsPanelFonctions
    m_controleVoletRoulants -.->|import| m_vrFonctions
    m_vrPages -.->|import| m_vrFonctions
    m_vrReglage -.->|import| m_vrFonctions
    m_controleVoletRoulants -.->|import| m_vrPages
    m_controleVoletRoulants -.->|import| m_vrReglage
    m_vrPages -.->|import| m_vrReglage
    CARTE --> m_demarrage
    CARTE --> m_fsMqtt
    CARTE --> m_graphiquesFonctions
    CARTE --> m_historiqueFonctions
    CARTE --> m_historiqueSeries
    m_graphiquesFonctions -.->|import| m_pagesGraphiquesValidation
```

## Comment regenerer

```
python outils_docs/scripts_python/berry/carte_modules_berry.py
```

Lecture seule : aucun build, aucune ecriture sous `data/`. La config PlatformIO est lue par l'API `ProjectConfig` dans le Python de PlatformIO (`~/.platformio/penv`).
