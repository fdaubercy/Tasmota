"""Onglet Aide de la page du sniffeur I2C (sniffeur_i2c_web.py), insere a la place de <!--AIDE-->."""

AIDE = """
<h2>Brancher le sniffeur</h2>
<p>Le sniffeur est un <b>ESP32-S3 DevKit dédié</b> (pas une carte du parc) avec le firmware
<code>outils_docs/firmware_sniffeur_i2c</code>. Il se branche au PC par son port <b>USB natif</b> (marqué « USB »,
pas « UART »), et au bus observé par <b>trois fils</b> :</p>
<table><tr><th>Sniffeur</th><th>Bus observé</th></tr>
<tr><td>GPIO4</td><td>SDA</td></tr><tr><td>GPIO5</td><td>SCL</td></tr><tr><td>GND</td><td>GND (indispensable)</td></tr></table>
<p><b>Bus en 3,3 V seulement</b> : les entrées de l'S3 ne supportent pas 5 V. Le sniffeur n'ajoute aucune résistance
de tirage et n'émet rien en écoute : il ne change rien au bus. Les broches se changent dans
<code>platformio.ini</code> du firmware (<code>BROCHE_SDA</code>, <code>BROCHE_SCL</code>).</p>
<h3>Flasher le firmware (une fois)</h3>
<p><code>pio run -d outils_docs/firmware_sniffeur_i2c -t upload --upload-port COMn</code>, <b>jamais pendant un build
Tasmota</b>. Au démarrage, le sniffeur envoie sa ligne d'identité : la barre du haut affiche sa puce et sa vitesse
d'échantillonnage (MHz).</p>

<h2>Vitesse du bus</h2>
<p><b>100 kHz</b> (vitesse par défaut de Tasmota) : garanti. <b>400 kHz</b> : dépend de la vitesse d'échantillonnage
affichée (il faut au moins une dizaine d'échantillons par bit, soit environ 4 MHz) ; à vérifier sur le bus réel. Si
des transactions sont <b>perdues</b> ou <b>tronquées</b> en grand nombre à 400 kHz, l'S3 ne suit pas : rester à 100 kHz.
La fréquence mesurée de SCL est affichée pour chaque trame et dans l'inventaire.</p>

<h2>Lire le fil</h2>
<p>Une ligne par transaction : adresse 7 bits, <b>W</b> (écriture) ou <b>R</b> (lecture), octets, fin
(<code>STOP</code>, <code>RESTART</code> = suivie d'une autre transaction sans relâcher le bus, <code>TRONQUE</code>),
fréquence, puce, registre et valeur traduite.</p>
<ul>
<li><b>NACK@0</b> : personne n'a répondu à l'adresse (puce absente, adresse fausse). Un <code>I2CScan</code> de Tasmota
en produit un par adresse sondée : c'est normal.</li>
<li><b>NACK@k</b> : le k-ième octet écrit n'a pas été acquitté. En lecture, le maître refuse toujours le dernier octet :
ce n'est pas signalé.</li>
<li><b>Écriture sans donnée</b> (« sonde ») : un maître vérifie qu'une puce répond.</li>
<li>Une lecture repart du <b>dernier registre écrit</b> à cette adresse. Si l'écoute a commencé après, le registre est
« inconnu » jusqu'à la prochaine écriture du pointeur.</li>
</ul>
<h3>Puces décodées</h3>
<table><tr><th>Puce</th><th>Adresses</th><th>Ce qui est traduit</th></tr>
<tr><td>ADS1115</td><td>0x48-0x4B</td><td>configuration (voie, plage, débit), conversion en mV (une fois la plage vue)</td></tr>
<tr><td>MCP23017</td><td>0x20-0x27</td><td>registres A/B, broches à 1 (sens, état, tirages)</td></tr>
<tr><td>TCA9554</td><td>0x20-0x27, 0x38-0x3F</td><td>entrées, sorties (relais de la Waveshare 8DI-8RO), configuration</td></tr>
<tr><td>DS3231</td><td>0x68</td><td>date et heure, température</td></tr>
<tr><td>MPU6050</td><td>0x68-0x69</td><td>accélérations (g), température, gyroscope, plages</td></tr>
<tr><td>ES8311</td><td>0x18-0x19</td><td>noms des registres</td></tr></table>
<p>Deux puces partagent 0x20 et 0x68 : choisir la <b>carte observée</b> en haut de la page. Ses puces actives sont lues
dans son <code>_persist.json</code>. Sans carte, une trame à adresse partagée est marquée <b>ambiguë</b> plutôt que
mal nommée.</p>

<h2>Alertes</h2>
<ul><li>NACK répétés : trois de suite sur la même adresse ;</li>
<li>transaction tronquée : STOP ou START au milieu d'un octet (parasite, câble trop long, maître redémarré) ;</li>
<li>pertes : le sniffeur n'a pas pu tout transmettre ;</li>
<li>bus bloqué : SDA tenue basse au repos, un esclave garde la ligne : couper son alimentation.</li></ul>

<h2>Lire ou écrire un registre (onglet Envoi)</h2>
<p><b>Par la carte</b> (bus en service) : la carte Tasmota, seul maître du bus, reçoit une commande Berry
<code>Br (wire1.detect(adr) ? wire1 : wire2).read(...)</code> ou <code>.write(...)</code> par HTTP. La commande est
<b>montrée avant l'envoi</b>, une à la fois ; une écriture demande une confirmation (écrire dans un extenseur commute
un relais). Le fil doit ensuite montrer la trame : « trame vue », sinon « trame non vue » (sniffeur sur un autre bus).
Pour un esclave derrière le point d'accès du maître, l'adresse proposée est <code>&lt;ip du maître&gt;:&lt;port&gt;</code>.</p>
<p><b>Par le sniffeur</b> (au banc) : le sniffeur devient maître à 100 kHz, <b>uniquement sur un composant débranché
de sa carte</b>, alimenté par le DevKit (3,3 V), avec les résistances de tirage de son module. Le firmware refuse
si le bus a vécu dans les 2 dernières secondes : un autre maître est présent.</p>

<h2>Journal et export</h2>
<p>Tout le fil est écrit dans <code>%LOCALAPPDATA%\\outils_tasmota\\sniffeur_i2c\\sniffeur_i2c_&lt;date&gt;.log</code>
(un fichier par jour, effacé après 30 jours). « Exporter » télécharge la capture en .txt ou .json.</p>
"""
