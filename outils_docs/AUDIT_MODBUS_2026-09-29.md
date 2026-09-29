# Audit ModBus du garage — 2026-09-29

> Audit en **lecture seule**, mené pendant une compilation des environnements garage, après
> les chantiers A + B, chien de garde, `seq` et relais commandé/constaté.
> Périmètre : `modbusFonctions.be`, `modBus_TasmotaSlaveModBus.be`, `controleModbus.be`,
> `udpFonctions.be`, `controleUDP.be`, les appels `pousseEtat` de `globalFonctions.be`, les
> 4 autoexec garage, les 4 envs garage de `platformio_tasmota_cenv.ini`, les 4 `_persist.json`.
>
> Méthode : 3 auditeurs indépendants, lecture intégrale, tests `berry.exe` hors dépôt,
> recoupement avec le C du firmware (`xdrv_63_modbus_bridge.ino`, `be_module.c`, `be_vm.c`,
> `tasmota_class.be`). Constats les plus lourds revérifiés à la main (B1, G1, `ReglageModbus`,
> règle des compteurs, secrets). Banc `banc_test_modbus.be` : 76/76.
>
> Légende : **[V]** vérifié (code lu ou exécuté) · **[S]** supposé (mécanisme plausible,
> fréquence ou comportement firmware non mesurés).

---

## 1. À traiter avant de flasher

### B1 — `controleModbus` plantait à son `init()` sur les 4 cartes garage [V] — ✅ CORRIGÉ

- `controleModbus.be:123` écrivait `modbusFonctions.timeout_ReponseModBus_ms = ...`.
  `modbusFonctions` est solidifié dans les 4 envs : table **constante** →
  `be_module_setmember` refuse (`be_module.c`) → `attribute_error`.
- Effets : `init()` s'arrêtait avant `configModbusByJson()` → **port RS485 jamais ouvert**
  (esclaves sourds, annulait `b5f23f7e5`) ; sur le P4, règle UDP, `ReglageModbus` et règle
  System non posées ; l'exception remontait dans l'autoexec → `controleDiscovery` (et
  `controleES8311` sur le P4) non chargés.
- Correctif : ligne supprimée (valeur jamais relue ; la file lit
  `drivers["ModBus"]["timeoutReponse"]`). Seule écriture dans un module solidifié trouvée
  dans tout `data/fs` et les autoexec garage.
- ⚠️ Les firmwares compilés **avant** ce correctif le contiennent : recompiler les 4 envs.
- **Balayage des 29 modules solidifiés (tous envs), même journée** — aucun autre cas :
  - écriture `module.attr = ...` à l'exécution, depuis n'importe quel `.be` : seule B1 ;
  - écriture via alias (`import X as y`, `var y = X`) ou sur `m` dans les `init(m)` : aucune ;
  - modification d'un conteneur du module (`push`, `[k] = ...`, alias local) : les 5 tables de
    `modbusFonctions` (`tabErreur`, `tabFonctionsName`, `tabLibelleCommande`,
    `tabLibelleRegistre`, `tabType`) ne sont que lues ;
  - `introspect.set(controleGeneral, ...)` (7 appels, `globalFonctions.be:51-118`) : vise
    l'**instance** du driver (`global.controleGeneral`, posée par `controleGeneral_init`), dont
    les champs sont déclarés par `var` → modifiable, sans défaut ;
  - `static coeff_div` (`controleES8311.be:103`) : seulement lu ;
  - `data/cave/tasmota32-serveur-rly-sauvegarde/webFonctions.be:102` : copie de sauvegarde
    utilisée par aucun env, et qui vise elle aussi l'instance.
  - L'état modifiable des modules est bien tenu hors module (`global._etat...`, champs d'instance).

### S1 — Secrets en clair sur un dépôt GitHub public [V] — ⏳ décision utilisateur

- `fdaubercy/Tasmota` est **public**. Les 9 `_persist.json` suivis contiennent en clair :
  mots de passe Wi-Fi (2 réseaux), MQTT, FTP, point d'accès du range extender.
- **Aussi dans les sources du firmware** (constaté le même jour) : `tasmota/user_config_override.h`
  définit `STA_PASS1`, `STA_PASS2`, `WIFI_AP_PASSPHRASE`, `MQTT_PASS` en clair, et le build les
  recopie dans `tasmota/tasmota_defines_for_berry.h/.be` (suivis par git). Tout commit de ces
  fichiers les republie — les exclure ne suffit pas, ils sont déjà dans l'historique public.
- Présent depuis `04dbda1a7` (2026-05-17, réorganisation du dépôt) ; les commits du 2026-09-29
  n'ont rien exposé de nouveau (lignes seulement réordonnées par le build).
- À faire : **changer ces mots de passe**, puis sortir les secrets des fichiers suivis.
  Réécrire l'historique = décision irréversible, à prendre explicitement.

---

## 2. Défauts qui touchent le garage tel qu'il sera flashé

| # | Défaut | Où | Preuve | Correctif proposé |
|---|---|---|---|---|
| G1 | ✅ **corrigé `f5c88f53c`** — **Timeout aléatoire sur le P4.** `armeTimer` y utilise `add_cron("*/5 …")`, déclenché au prochain multiple de 5 s : délai réel dans ]0 ; 5] s. Renvoi prématuré → la réponse tardive acquitte le renvoi, la suivante est orpheline et peut acquitter la requête suivante de même adresse et même code (le relevé enchaîne interrupteur1 puis 2, relai2 puis 3) → valeur écrite sur le mauvais appareil, faux ECART. Sans RTC valide (avant NTP), les crons ne tournent pas → une réponse perdue au boot bloque la file. | `modbusFonctions.be:537-549` | [V] mécanisme, [S] fréquence | Échéance `tasmota.millis() + délai` testée par un cron 1 s ou un `every_100ms` ; ne pas dépendre de l'horloge murale |
| G2 | ✅ **corrigé `aa0df4054`** — **Réception série sans découpage de trames.** Tout le tampon lu toutes les 100 ms est traité comme **une** trame. Bus partagé (carte 16, cuve, rideau) : [réponse d'un autre][requête pour soi] → erreur CRC/longueur, requête perdue, timeout 5 s. | `lireMsgModbus` l.824-863, `controleModbus.every_100ms` | [V] mécanisme, [S] fréquence | Tampon cumulatif ; extraction trame par trame selon la longueur attendue par code fonction + CRC glissant |
| G3 | ✅ **corrigé `269021b5a`** — **File du maître sans plafond si un esclave se tait.** Le relevé ré-enfile toutes les 30 s les requêtes de l'esclave muet (rideau : 4 × jusqu'à 3 × 5 s = 60 s de bus par cycle de 30 s). Ni plafond ni dédoublonnage → RAM qui croît, commandes carte 16 retardées de minutes. | `releveEsclaves` | [V] calcul sur config réelle | Une seule sonde par cycle pour un esclave muet ; pas de doublon (adresse, code, registre) en file ; plafond |
| G4 | **Faux « muet ».** File engorgée (G3) → requêtes vers la cuve parties après plus de 90 s ; la cuve ne pousse rien (thermomètre, analogique) → « inconnu » à tort. | `verifieChienDeGarde` | [S] | Compter les abandons réels par esclave (`termineEnVol(false)`), ou mesurer depuis l'envoi effectif |
| G5 | ✅ **corrigé `20714d0b0`** — **Réponse jamais acquittée sur exception.** Accès directs (`["serialNumber"]`, `["Humidity"]`, `["value"]`, `["environnement"]`, `idModBus` absent) → exception → pas de `termineEnVol(true)` → 3 × 5 s perdus, règles suivantes du même événement coupées. | `recupereReponseModBus` l.436-668 | [V] | `try` autour du traitement, acquittement dans tous les chemins, `.find()` |
| G6 | **ECART bavards.** Lecture 0x01 enfilée avant une commande, relais temporisé ou piloté localement → ECART niveau ERREUR toutes les 30 s (la carte 16 journalise en INFO via `self.log`). | l.647-650 | [S] | Journaliser les transitions seulement, ou ignorer l'écart T s après une commande |
| G7 | ✅ **corrigé `be8ee6a4b`** — **WS2812 de la cuve « inconnu » pour toujours après une panne** : marquée par `passeInconnu`, jamais relue. | `passeInconnu` | [V] | L'exclure du chien de garde, ou la remettre « valide » au contact |
| G8 | **Push des compteurs inopérant.** Règle `Tele#COUNTER#C` qui ne correspond jamais à `C1` (clés exactes, `rule_matcher.be`) ; `device["etat"]` absent des compteurs → `key_error`. Sans impact : aucun compteur d'esclave actif. | `configDevices.be:332`, `globalFonctions.be:353` | [V] | Règle `COUNTER#C<id>`, `.find("etat")` |

---

## 3. Défauts latents (chemins inactifs aujourd'hui)

| # | Défaut | Où | Preuve |
|---|---|---|---|
| L1 | **Repli UDP/TCP (série coupé) inopérant** : `decrypteMSG` ne lit que des *requêtes* (exige 8 octets) → réponses 0x01-0x04 et écho 0x10 rejetés (Erreur 6) ; division par zéro possible (quantité 0, l.1282). | `modbusFonctions.be:1247-1297` | [V] |
| L2 | `envoiMsgModbusUDP` lit `/json/paramDiscovery.json`, qu'aucun module n'écrit → `nil.find` → le repli UDP plante. IP calculée jamais utilisée. | `modbusFonctions.be:714` | [V] |
| L3 | **Réponse 0x05 fausse** : `Count=2` → trame tronquée (`wrongnbValeurs` non testé à l'émission) ; `writeData[0] = 0xFF00` dans un octet → `00`. Personne n'envoie de 0x05. | l.1262, 1418, 1508 | [V] |
| L4 | **`ReglageModbus` : 3 sous-commandes cassées.** `split(payload, " ", 1)` ne laisse qu'un paramètre → `parametres[1]` = `index_error` ; commande sans espace → `parametres = false` → plantage. | l.250-258 | [V] |
| L5 | SwitchMode ni 1 ni 2 : push `"ON"` en uint16 → exception (esclave) ; état `0.0` (maître). Tout le garage est en SwitchMode 2. | `globalFonctions.be:212-284`, TasmotaSlave l.588-619 | [V] |
| L6 | `ReglageSlaveModBus id` à chaud : règles `#DeviceAddress==<ancien>` laissées en place. | TasmotaSlave l.145-162 | [V] |
| L7 | `accepteSeq` : désordre juste après un démarrage (seq 2 puis 1) pris pour un redémarrage ; redémarrage avec seq 1 perdu et ancien compteur ≤ 17 → jusqu'à 16 pushes écartés. | `modbusFonctions.be:1743` | [V] raisonnement |
| L8 | Chien de garde sur `rtc()["local"]` : saut à l'heure d'été / synchro NTP → tous muets une fois (même défaut sur la carte 16). | TasmotaSlave l.972, 990 | [S] |
| L9 | Timer du relais temporisé 0x06 non nommé : un ancien timer peut couper un relais recommandé entre-temps. | l.1095 | [V] |
| L10 | `pompeQueue` : `tasmota.cmd` qui renvoie nil → `reponse.find` lève, `enVol` posé sans timer → file bloquée. | l.484 | [S] |
| L11 | Gardes `&&` au lieu de `||` dans `envoiMsgModbusUDP/TCP` ; `pousseEtat` ne vérifie pas `rangeExtender` (log « → maître » alors que rien ne part). | l.710, 773, 1706 | [V] |
| L12 | `lireUDP` : un datagramme hors ModBus sans espace → `index_error` hors `try` dans `every_100ms` ; un seul datagramme lu par socket et par tick. | `udpFonctions.be:441-452`, `controleUDP.be:143` | [V] |
| L13 | Divers : faute `envoiMessagTCP` (branche inatteignable) ; `HSBColor` teste deux fois `idx == 2` ; ImAlive (TCP) lit l'id de l'entrée `"maitre"` ; un esclave Serial+TCP répondrait deux fois. | — | [V]/[S] |

---

## 4. Vérifié sain

- **Chargement** : 4/4 envs cohérents — chaque `import` vise un module solidifié, aucun `.be`
  exclu n'est chargé, `be_module.c` fait passer le natif avant un `.bec` résiduel. 4/4 JSON valides.
- **Correspondance maître ↔ esclaves** : 7/7 appareils (types, id, relais 224 ↔ 256 via
  `idRelai`, double SwitchMode 2 qui s'annule). Ids `udp`/`tcp`/`ModBus` alignés.
- **Trames** : CRC exact ; réponses esclave 0x01, 0x02, 0x04 (float, uint32, DHT22 = 8 octets),
  0x06, écho 0x10 conformes ; push 0x10 relu (21.5 °C) ; quantités des commandes correctes.
- **Relais** : table de vérité 224/256 × bit 0/1 vérifiée ; bit 0 cohérent avec la passerelle
  native (`xdrv_63:494-499`).
- **Push** : 4/4 appels `pousseEtat` conformes ; enveloppe avec et sans `seq` lue ; multicast
  soumis à `rangeExtender = ON` (ON sur les 3 garage).
- **Règles et solidification** : aucune règle écrasée, aucune closure capturant une variable
  de boucle, aucune fonction anonyme de niveau module, imports présents dans chaque méthode.

---

## 5. Améliorations et évolutions proposées (par priorité)

1. ~~B1~~ fait — **recompiler les 4 envs**.
2. ~~**Fiabilité du bus**~~ fait le 2026-09-29 : G1, G2, G3, G5 (+ G7). Voir « Suivi ».
3. **Supervision robuste** (reste) : chien de garde sur abandons réels et `millis()` (G4, L8),
   ECART sur transitions (G6).
4. **Sécurité** (S1) : rotation des mots de passe, secrets hors des fichiers suivis (fichier local
   ignoré par git, fusionné au build ou poussé depuis un dossier hors dépôt).
5. **Nettoyage** : soit supprimer le repli UDP et le TCP, soit les réparer (L1, L2, L13) ;
   `ReglageModbus` (L4), 0x05 (L3), push compteurs (G8).
6. **Évolutions** :
   - page/JSON de supervision par esclave (dernier contact, muet, ECART, taille de file,
     timeouts) via `json_append` → télémétrie MQTT / Node-RED ;
   - relevé groupé : un bloc de registres par esclave au lieu d'une requête par appareil
     (environ ÷ 4 d'occupation du bus) ;
   - réalignement au démarrage : remettre l'esclave dans l'état commandé grâce à la lecture 0x01
     (aujourd'hui `continue` au boot si l'état local égale `etat`) ;
   - `ReglageSlaveModBus id` qui ré-enregistre les règles ou impose un redémarrage.

---

## Suivi

| Date | Point | Statut | Commit |
|---|---|---|---|
| 2026-09-29 | B1 — écriture dans le module solidifié `modbusFonctions` | ✅ corrigé | `04d9bd865` |
| 2026-09-29 | G1 — timeout P4 : échéance `tasmota.millis()` testée par `verifieEcheances` (appelée par `controleModbus.every_100ms`) au lieu d'un cron `*/5` | ✅ corrigé, banc §16 (5 tests, témoin 4 échecs) | `f5c88f53c` |
| 2026-09-29 | G5 — traitement des réponses sous `try`, acquittement toujours atteint, `.find()` (serialNumber, environnement, idModBus, esclave inconnu) | ✅ corrigé, banc §17 (3 tests, témoin : requête restée en vol) | `20714d0b0` |
| 2026-09-29 | G3 — file : lecture identique (en file ou en vol) non ré-enfilée, plafond `MAX_FILE = 32` (lecture écartée, écriture prioritaire), une sonde par cycle pour un esclave muet | ✅ corrigé, banc §18 (8 tests, témoin : file non bornée) | `269021b5a` |
| 2026-09-29 | G7 — seuls les appareils relus (`demandeLecture` non nil) passent à « inconnu » | ✅ corrigé, banc §19 (3 tests, témoin : WS2812 marquée) | `be8ee6a4b` |
| 2026-09-29 | G2 — `extraitTrames` : découpage du flux RS485 (longueurs requête/réponse/exception, CRC, resynchronisation, attente, silence 100 ms) ; tampon `tamponSerie` borné à 512 octets | ✅ corrigé, banc §20 (9 tests, témoin : 0 publication) | `aa0df4054` |

**Banc après correctifs : 104/104.** Rien n'est encore testé sur bus réel : recompiler les 4 envs.
Restent ouverts : S1 (secrets, décision utilisateur), G4, G6, G8, latents L1-L13.

**À observer au premier flash** (log niveau 4) :
- `ENFILE_MSG: lecture deja en file` : attendu seulement si un esclave est lent ou muet ;
- `ENFILE_MSG: file pleine` : ne doit **jamais** apparaître en régime normal ;
- `MODBUS_TASMOTA_SLAVE_ERREUR` : signale un appareil virtuel incomplet dans le persist (à corriger dans la config) ;
- `SUR_TIMEOUT` sur le P4 : doit arriver ~5 s après l'envoi, plus au hasard ;
- côté esclave, plus aucun `Message ModBus reçu avec erreur` en rafale quand la carte 16 relais est interrogée.
