"""Onglet Aide du sniffeur ModBus (sniffeur_modbus_web.py) : regles de formation des trames.

Sources : la norme ModBus RTU ; outils_docs/PROTOCOLE_MODBUS.md (section 8 : carte 16 relais,
section 9 : push UDP) ; le code des drivers modBus_Conn16channels.be et modBus_TasmotaSlaveModBus.be
et, cote esclave, modbusFonctions.executeCmdModbus / prepareTrame.
Les exemples sont calcules ici (CRC compris) : un clic dans la page les decode.
La section « Registres de votre installation » est remplie par la page, depuis GET /carte.
"""

import html

import decodeur_modbus as dm


def ex(trame, legende="", requete=""):
    """Exemple cliquable : trame complete (CRC calcule), requete associee pour une reponse."""
    def complete(h):
        b = bytes.fromhex(h.replace(" ", ""))
        c = dm.crc16(b)
        return dm.hx(b + bytes((c & 0xFF, c >> 8)))
    t, r = complete(trame), (complete(requete) if requete else "")
    return (f'<div class="exemple"><code class="ex" data-hex="{t}" data-req="{r}" title="cliquer pour decoder">{t}</code>'
            f' <span class="gris">{html.escape(legende)}</span></div>')


def push(trame, seq, legende):
    b = bytes.fromhex(trame.replace(" ", ""))
    c = dm.crc16(b)
    ligne = f"ModbusPushUDP {seq} {(b + bytes((c & 0xFF, c >> 8))).hex().upper()}"
    return f'<div class="exemple"><code class="ex" data-hex="{ligne}" data-req="">{ligne}</code> <span class="gris">{legende}</span></div>'


AIDE = f"""
<h2>1. Anatomie d'une trame ModBus RTU</h2>
<table>
<tr><th>Adresse</th><th>Fonction</th><th>Données</th><th>CRC</th></tr>
<tr><td>1 octet : 1 à 247 (0 = diffusion)</td><td>1 octet : 0x01 à 0x10</td><td>0 à 252 octets, selon la fonction</td>
<td>2 octets, <b>poids faible d'abord</b> (polynôme 0xA001, départ 0xFFFF)</td></tr>
</table>
<ul>
<li>Les valeurs sur 16 bits (registre, quantité, mot de donnée) sont écrites <b>poids fort d'abord</b> ; seul le CRC est inversé.</li>
<li>Une trame se termine par un silence d'au moins 3,5 caractères (≈ 2 ms à 19 200 bauds).</li>
<li>Seul le maître parle de lui-même ; un esclave ne répond qu'à une requête qui porte son adresse.</li>
<li>Un esclave qui refuse répond <b>fonction | 0x80</b> + un code d'exception. Une trame au CRC faux est ignorée sans réponse.</li>
</ul>

<h2>2. Les fonctions standard</h2>
<table>
<tr><th>Code</th><th>Fonction</th><th>Requête (après adresse et code)</th><th>Réponse</th></tr>
<tr><td>0x01</td><td>Lire des coils (sorties)</td><td>registre (2) + quantité de bits (2)</td>
<td>nb d'octets (1) + bits, 1er bit = bit 0 du 1er octet</td></tr>
<tr><td>0x02</td><td>Lire des entrées discrètes</td><td>registre (2) + quantité de bits (2)</td><td>idem 0x01</td></tr>
<tr><td>0x03</td><td>Lire des registres de maintien</td><td>registre (2) + quantité de registres (2)</td>
<td>nb d'octets (1) = 2 × quantité + registres de 2 octets</td></tr>
<tr><td>0x04</td><td>Lire des registres d'entrée</td><td>registre (2) + quantité de registres (2)</td><td>idem 0x03</td></tr>
<tr><td>0x05</td><td>Écrire un coil</td><td>coil (2) + FF 00 (ON) ou 00 00 (OFF)</td><td>écho de la requête</td></tr>
<tr><td>0x06</td><td>Écrire un registre</td><td>registre (2) + valeur (2)</td><td>écho de la requête</td></tr>
<tr><td>0x0F</td><td>Écrire des coils</td><td>registre (2) + quantité de bits (2) + nb d'octets (1) + bits</td><td>registre (2) + quantité (2)</td></tr>
<tr><td>0x10</td><td>Écrire des registres</td><td>registre (2) + quantité de registres (2) + nb d'octets (1) + registres</td><td>registre (2) + quantité (2)</td></tr>
</table>
<p>Codes d'exception : 01 fonction illégale · 02 adresse illégale · 03 valeur illégale · 04 défaillance de l'esclave ·
05 acquittement · 06 esclave occupé · 08 erreur de parité mémoire · 0A/0B passerelle.</p>
{ex("03 83 02", "exception : l'esclave 3 refuse une lecture 0x03 (adresse illégale)", "03 03 00 01 00 01")}

<h2>3. La carte 16 relais (driver modBus_Conn16channels)</h2>
<p>Usine : 9600 bauds, 8N1, adresse 1 ; bus du garage : <b>19 200</b> (à régler à la main, un seul équipement branché).</p>
<h3>Commander une sortie : fonction 0x06</h3>
<p><code>[adresse] 06 [canal : 00 01 à 00 10, 00 00 = tous] [ordre] [tempo] [CRC]</code> — l'octet fort de la valeur est
l'<b>ordre</b>, l'octet faible la <b>temporisation</b> (secondes, ordre Delay seulement). La carte renvoie l'écho.</p>
<table>
<tr><th>Ordre</th><td>01 Open</td><td>02 Close</td><td>03 Toggle</td><td>04 Latch</td><td>05 Momentary</td><td>06 Delay</td><td>07 Open all</td><td>08 Close all</td></tr>
</table>
{ex("01 06 00 01 01 00", "canal 1 : Open (sortie au niveau bas)")}
{ex("01 06 00 03 03 00", "canal 3 : Toggle")}
{ex("01 06 00 05 06 0A", "canal 5 : Delay de 10 s")}
{ex("01 06 00 00 08 00", "tous les canaux : Close all")}
<h3>Relire les 16 sorties : fonction 0x03</h3>
<p>Un registre par canal, à partir de 0x0001 : <b>0x0001 = open</b> (sortie au niveau bas), 0x0000 = close.</p>
{ex("01 03 00 01 00 10", "relève des 16 sorties (c'est le sondage périodique du maître)")}
{ex("01 03 20 " + " ".join("00 01" if k in (2, 5) else "00 00" for k in range(16)), "réponse : canaux 3 et 6 open", "01 03 00 01 00 10")}
<h3>Registres de configuration</h3>
<table>
<tr><th>Registre</th><th>Rôle</th><th>Valeurs</th></tr>
<tr><td>0x00FE</td><td>débit</td><td>0 : 1200 · 1 : 2400 · 2 : 4800 · 3 : 9600 · 4 : 19200 · 5 : retour usine (effectif après coupure d'alimentation)</td></tr>
<tr><td>0x00FF</td><td>adresse</td><td>1 à 247 (un seul équipement sur le bus pour la changer)</td></tr>
</table>
{ex("01 06 00 FE 00 04", "passer la carte à 19 200 bauds")}
{ex("01 03 00 FE 00 01", "lire le débit")}
{ex("FF 03 00 FF 00 01", "lire l'adresse en diffusion")}
<h3>Les pièges</h3>
<ul>
<li><b>Open = sortie au niveau BAS.</b> Les relais du garage sont déclarés Relais_i (type 256) : open ⇒ relai <b>ON</b> côté maître.
Le driver envoie donc ON = ordre 01, OFF = ordre 02 (et l'inverse pour un type 224). Le cavalier M0 inverse la polarité.</li>
<li>Une commande invalide ne reçoit <b>aucune</b> réponse : un silence n'est pas une carte absente.</li>
</ul>

<h2>4. Les esclaves ESP32 Tasmota (driver modBus_TasmotaSlaveModBus)</h2>
<p><b>Règle d'adressage : registre = code GPIO Tasmota de l'appareil + idModBus − 1.</b>
Le code GPIO est le rang dans <code>enum UserSelectablePins</code> × 32 (tasmota_template.h).</p>
<table>
<tr><th>Code</th><th>GPIO</th><th>Appareil</th><th>Lecture (relevé du maître)</th><th>Commande</th></tr>
<tr><td>32</td><td>GPIO_KEY1</td><td>bouton</td><td>0x02, 1 bit</td><td>—</td></tr>
<tr><td>160</td><td>GPIO_SWT1</td><td>interrupteur / capteur</td><td>0x02, 1 bit (SwitchMode 1 : 1 = ON ; 2 : 1 = OFF)</td><td>—</td></tr>
<tr><td>224</td><td>GPIO_REL1</td><td>relai</td><td>0x01, 1 bit = Power réel</td><td>0x06 : octet fort 02 = Power ON, 01 = OFF ; octet faible = délai (s) avant inversion</td></tr>
<tr><td>256</td><td>GPIO_REL1_INV</td><td>relai inversé (Relais_i)</td><td>0x01 (état maître = inverse du bit)</td><td>0x06, mêmes octets ; le maître envoie ON = 01</td></tr>
<tr><td>352</td><td>GPIO_CNTR1</td><td>compteur</td><td>0x04, 2 registres, uint32 poids fort d'abord</td><td>—</td></tr>
<tr><td>1216</td><td>GPIO_DHT22</td><td>DHT22</td><td>0x04, 4 registres = 2 float (température, humidité)</td><td>—</td></tr>
<tr><td>1312</td><td>GPIO_DSB</td><td>DS18B20</td><td>0x04, 2 registres = 1 float IEEE 754 poids fort d'abord</td><td>—</td></tr>
<tr><td>1376</td><td>GPIO_WS2812</td><td>LEDs WS2812</td><td>—</td><td>0x10, 3 registres : teinte, saturation, luminosité (HSBColor)</td></tr>
<tr><td>4704</td><td>GPIO_ADC_INPUT</td><td>entrée analogique</td><td>0x04, 2 registres, uint32</td><td>—</td></tr>
</table>
<p>Ici : cuve = adresse 2, rideau = adresse 3 (persist du maître). Le maître relit chaque appareil toutes les 30 s.</p>
{ex("03 06 01 00 02 00", "rideau, relai inversé n°1 (registre 256) : Power1 ON")}
{ex("03 06 01 00 01 0A", "Power1 OFF, puis retour à ON au bout de 10 s")}
{ex("03 01 01 00 00 01", "relève de l'état réel du relai")}
{ex("03 01 01 01", "réponse : Power1 = ON", "03 01 01 00 00 01")}
{ex("03 02 00 A0 00 01", "état de l'interrupteur n°1 (registre 160)")}
{ex("03 02 01 01", "réponse : bit à 1", "03 02 00 A0 00 01")}
{ex("02 04 05 20 00 02", "température du DS18B20 n°1 (registre 1312)")}
{ex("02 04 04 41 AC 00 00", "réponse : 21,5 °C", "02 04 05 20 00 02")}
{ex("02 04 12 60 00 02", "entrée analogique n°1 (registre 4704)")}
{ex("02 04 04 00 00 30 39", "réponse : 12345", "02 04 12 60 00 02")}
{ex("02 10 05 60 00 03 06 00 78 00 64 00 32", "LEDs WS2812 n°1 : teinte 120, saturation 100, luminosité 50")}
<h3>Le push esclave → maître (UDP, jamais sur le RS485)</h3>
<p>Sur un changement d'interrupteur, de bouton, de capteur ou de compteur, l'esclave envoie en UDP multicast
<code>ModbusPushUDP &lt;seq&gt; &lt;trame en hexa&gt;</code>. La trame est une 0x10 standard dont l'adresse est
<b>celle de l'esclave émetteur</b> : <code>[id] 10 [registre] 00 01 02 [valeur] [CRC]</code> (interrupteur : 00 FF = actif).
Le maître écarte un <code>seq</code> déjà vu ou plus ancien. Le sniffeur ne voit pas l'UDP, mais une ligne de log se colle
dans le décodeur ci-dessous.</p>
{push("03 10 00 A0 00 01 02 00 FF", 5, "rideau : interrupteur n°1 actif")}

<h2>5. Registres de votre installation</h2>
<p class="gris" id="sourceCarte">lecture du persist du maître...</p>
<table id="tableCarte"></table>

<h2 id="titreDecodeur">6. Décodeur manuel</h2>
<p>Une trame en hexa, avec son CRC (ou cocher « ajouter le CRC »), ou une ligne <code>ModbusPushUDP</code> des logs.
Pour une réponse 0x01 à 0x04, donner la requête : c'est elle qui porte le registre lu.</p>
<div class="barre plate">
 <input id="decHex" placeholder="trame, ex. 01 03 00 01 00 10 15 C6">
 <input id="decReq" placeholder="requête associée (facultatif)">
 <label><input type="checkbox" id="decCrc"> ajouter le CRC</label>
 <button id="decoder">Décoder</button>
</div>
<div id="decResultat"></div>

<h2>7. Essai sur le bus réel</h2>
<ol>
<li><b>Brancher le convertisseur</b> : A+ sur A, B- sur B, GND sur la masse du bus. Le repérer par <code>lister</code>
(débrancher / rebrancher : le port qui apparaît est le sien), puis l'ouvrir ici à <b>19 200</b> bauds. Le port est
ouvert sans DTR/RTS : choisir par erreur celui d'une carte ESP32 ne la redémarre pas.</li>
<li><b>Écouter sans rien émettre</b>, au moins 2 minutes : le P4 relit la carte relais et chaque appareil des
esclaves toutes les 30 s. Attendu : des paires requête / réponse au CRC juste, une latence par esclave,
aucune « PAS DE REPONSE », aucune alerte. Des trames coupées en deux ou collées → ajuster <code>--silence</code>.</li>
<li><b>Vérifier l'écho local</b> : la barre d'état indique « echo local oui / non » dès le premier envoi.</li>
<li><b>Push UDP</b> : basculer un interrupteur du rideau → une ligne UDP verte, « seq N accepte ». Rien ?
Le pare-feu Windows bloque l'UDP entrant de python.exe, ou le PC n'est pas sur le réseau des modules
(<code>--udp-interface</code>).</li>
<li><b>Lectures à la main</b>, et seulement après avoir suspendu la file du P4 (<code>test_liaison_modbus.be</code>)
ou débranché le P4 — sinon alerte « deux maîtres » et collisions : « Lire 16 sorties », puis les exemples de
lecture du tableau de l'installation (section 5), copiés dans le champ d'envoi par un clic.</li>
<li><b>Exporter</b> le fil (bouton Exporter) pour garder la trace de l'essai.</li>
</ol>
"""
