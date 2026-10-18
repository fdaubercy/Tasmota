"""Onglet Aide du testeur UDP (testeur_udp_web.py) : usage, modes de connexion, verdicts, commandes envoyees.

Reference : outils_docs/PROTOCOLE_MODBUS.md, section 9, « Commandes sans fil vers les esclaves ».
Les commandes listees ici sont celles de testeur_udp_essais.py (construit_essai) et testeur_udp.py.
"""

AIDE = """
<h2>1. A quoi sert cet outil</h2>
<p>Il ouvre <b>deux ports série</b> : le <b>maître ModBus</b> (ESP32-P4) et <b>un esclave</b> (ESP32-S3 de la cuve ou du rideau),
lit leurs logs Tasmota et envoie des messages <b>UDP unicast et multicast dans les deux sens</b>. Pour chaque essai il cherche
la preuve dans les logs des <i>deux</i> cartes (émission puis réception) et affiche un verdict. Il ne remplace pas le pont série :
il en reprend la manière (port ouvert sans reset de l'ESP32).</p>

<h2>2. Raccordement et lancement</h2>
<ul>
<li>Deux câbles USB : un par carte. Deux façons de s'y brancher, dans la liste « Port » de chaque carte :
 <ul>
 <li><b>« Pont série 127.0.0.1:7000 »</b> (en tête de liste, conseillé) : l'outil passe par le <b>pont série</b>, qui garde le port COM ;
 sa page <code>http://127.0.0.1:7000</code> reste utilisable en même temps. <b>Démarrer d'abord le script « pont série »</b>
 (PlatformIO &gt; Custom &gt; « Pont serie (TCP/HTTP 127.0.0.1) », un pont par carte : 7000, puis « + Terminal » pour 7001)
 et y ouvrir le port COM de la carte. Sinon la page avertit : « aucun pont série sur 127.0.0.1:7000 : démarrez le script… »,
 ou « … son port COM est fermé : cliquez Démarrer ».</li>
 <li><b>Le port COM direct</b> : fermer alors le pont série et le moniteur série qui le tiennent (un port n'accepte qu'un programme).
 Si l'ouverture échoue, la page affiche « COMx est déjà ouvert par un autre programme ».</li>
 </ul></li>
<li>Le port de l'esclave disparaît quand il redémarre (USB natif) : l'outil le <b>rouvre tout seul</b> dès qu'il revient.
Par le pont, c'est l'outil qui le lui redemande (le pont seul ne rouvre pas un port perdu) ; après « Arrêter » dans la page du pont
(pour un flash), il ne redemande rien et reprend quand le port y est rouvert.</li>
<li>Lancement : PlatformIO &gt; Custom &gt; <b>« Testeur UDP maître/esclave »</b> ; ou <code>Ctrl+Maj+P</code> &gt; <i>Tasks: Run Task</i> &gt;
<b>« Outil : testeur UDP maitre/esclave (http://127.0.0.1:7400) »</b> ; ou en ligne de commande :
<pre>%USERPROFILE%\\.platformio\\penv\\Scripts\\python.exe -u outils_docs/scripts_python/outils_pc/testeur_udp.py --port-maitre COM11 --port-esclave COM12</pre></li>
<li><b>Restriction</b> : la cible Custom est un <code>pio run</code>. Ne jamais la lancer pendant un build (elle peut effacer <code>.pio/build</code>) :
lancer alors la tâche VS Code ou le script directement.</li>
<li>Au lancement, la page s'ouvre dans le navigateur (sauf <code>--sans-navigateur</code>) ; la console affiche son lien
(Ctrl+clic). <b>Depuis un autre appareil du réseau</b> (téléphone au garage) : ouvrir le lien « depuis un autre appareil du réseau »
de la console, qui contient un <b>jeton</b> (nouveau à chaque lancement) ; sans lui, la page est refusée. <code>--local</code> : ce PC seulement.
Les liens vers la page du pont série (<code>127.0.0.1:7000</code>) ne valent que sur ce PC.</li>
<li>Arrêt : Ctrl+C dans le terminal de la tâche. Les niveaux de log modifiés sont restaurés avant la fermeture des ports.</li>
</ul>

<h2>3. Les deux modes de connexion de l'esclave</h2>
<table>
<tr><th>Mode</th><th>Réseau</th><th>Ce qui change</th></tr>
<tr><td><b>Range Extender</b></td><td>l'esclave est client du point d'accès du maître (192.168.4.x)</td>
<td>Le maître est vu par l'esclave à <b>192.168.4.1</b> (son point d'accès), pas à son IP du réseau maison. L'esclave <b>émet</b> le multicast (ImAlive, push).</td></tr>
<tr><td><b>Wi-Fi classique</b></td><td>les deux cartes sont sur le réseau maison</td>
<td>Le maître est joignable à son IP du réseau (Status 5). Depuis la correction <b>C4</b> (2026-10-17),
l'esclave <b>émet</b> aussi son multicast (ImAlive, push) par sa STA ; il n'atteint le maître que si <b>la box relaie
le multicast</b> entre clients Wi-Fi (mesuré le 2026-10-17) : <b>EMIS NON RECU</b> mesure donc la box, pas l'outil.
Le multicast du maître part par son point d'accès s'il est actif, et <b>aussi par sa STA</b> si sa découverte connaît
un esclave joignable par la box (même groupTopic, <code>Online</code>, IP du réseau de la box) : faire d'abord un
<b>ImAlive</b> de l'esclave. Sans point d'accès ni esclave sur la box, il n'est pas émis (<b>NON EMIS</b>,
« Non emis » dans le log). L'heure et <code>ipMaitre</code>
(réponse à ImAlive) arrivent quand même, en unicast (correction <b>C5</b>). <b>NON EMIS</b> côté esclave = firmware
antérieur à C4.</td></tr>
</table>
<p><b>Bascule de mode</b> (menu « Mode de connexion », après confirmation) : l'outil envoie la commande, la carte répond puis <b>redémarre seule</b>.
La page affiche « redémarrage... », attend le retour du port, renvoie Status 5, met l'IP à jour et relit le mode.</p>
<ul>
<li>vers Wi-Fi classique : le SSID et le mot de passe sont lus dans le <code>_persist.json</code> du maître
(<code>serveur.wifi.reseau1.nomReseauWifi / mdpWifi</code>, option <code>--persist-maitre</code>) ;</li>
<li>vers Range Extender : l'esclave restaure seul ses réseaux mémorisés au retour.</li>
</ul>
<p>Le mot de passe n'apparaît <b>ni dans la page ni dans le journal de l'outil</b> (remplacé par ***). La carte, elle, le journalise
dans son propre log : c'est accepté.</p>

<h2>4. Lire les verdicts</h2>
<table>
<tr><th>Verdict</th><th>Signification</th></tr>
<tr><td style="color:#23d18b"><b>RECU</b></td><td>La carte réceptrice a loggé <code>LIRE_UDP: msg = ...</code> avec <b>le message attendu</b> (marqueur <code>TESTUDP-n</code>, tid, ImAlive...) dans le délai.
Un message d'un autre essai n'est jamais accepté.</td></tr>
<tr><td style="color:#f5f543"><b>EMIS NON RECU</b></td><td>L'émettrice a loggé <code>ENVOI_MSG_UDP ... &gt;&gt;&gt;&gt; OK</code> mais rien n'est arrivé : paquet perdu, mauvaise IP, multicast filtré (le NAPT du maître ne relaie pas tout).</td></tr>
<tr><td style="color:#f14c4c"><b>NON EMIS</b></td><td>Aucune ligne <code>ENVOI_MSG_UDP</code>, ou résultat <code>Echec</code>/<code>nil</code>/<code>Non emis</code>, ou « Reseau non connecte ». Multicast esclave en Wi-Fi classique : firmware antérieur à C4 ; multicast du maître « Non emis » : aucun esclave découvert sur la box (voir ci-dessus).</td></tr>
<tr><td style="color:#f14c4c"><b>ECHEC</b></td><td>Essai ModBus : l'esclave a aussi écrit la trame sur le RS485 (<code>ENVOI_MSG_MODBUS: Message ModBus envoyé = 0x</code>) alors que la réponse ne doit partir que par UDP.</td></tr>
<tr><td style="color:#d670d6"><b>PAS DE RUBAN</b></td><td>Essai Push : l'esclave n'a pas de ruban (<code>PAS_DE_RUBAN</code>) : rien à pousser.</td></tr>
</table>
<p><b>Carte muette</b> (pastille rouge, « CARTE MUETTE » à côté du port) : une commande est restée <b>10 s sans
aucune ligne</b> en retour, pas même l'écho <code>CMD:</code>, alors que le port est ouvert. L'outil relance une fois
le log série (<code>SerialLog</code>, coupé par Tasmota 600 s après un redémarrage qu'il n'a pas vu) ; si rien ne
revient, <b>reset de la carte</b> (bouton RST) : le 2026-10-17, la cuve s'est tue ainsi 8 min alors qu'elle tournait
(UDP reçu par le maître), et fermer/rouvrir le port n'a rien changé. Un essai pendant lequel une carte n'a rien écrit
le dit en tête des détails (« aucune ligne reçue de la carte ... ») : son verdict ne dit alors rien de l'UDP.</p>
<p>Le délai affiché va de l'envoi de la commande à la ligne de réception. « Source vue » = IP:port lus dans <code>LIRE_UDP: Données UDP ... reçues de '&lt;ip&gt;' sur le port &lt;n&gt;</code>.
Un essai ModBus attend toute la fenêtre (l'absence de trame RS485 ne se prouve qu'à la fin).</p>

<h2>5. Les logs posés et restaurés</h2>
<p>À l'ouverture d'un port, l'outil envoie <code>ReglageLog</code> et mémorise <code>modules.udp</code>, <code>modules.modbus</code> et <code>sorties.serie</code>.
Il pose ensuite <code>ReglageLog udp detail</code>, <code>ReglageLog modbus detail</code> et, si la sortie série est sous <i>debug</i>, <code>ReglageLog serie debug</code>.
Sur le <b>maître</b> seulement, il pose aussi <code>ReglageLog slaveModbus debug</code> et <code>ReglageLog conn16channels debug</code> (relevés,
chien de garde, carte 16 relais : l'onglet Grille ModBus en a besoin). Un niveau déjà plus haut est gardé : l'outil ne baisse jamais un niveau.
Il ne touche <b>jamais</b> aux sorties <b>mqtt, web, syslog</b> (MqttLog en debug fait planter un esclave derrière le NAPT). À l'arrêt, à la fermeture d'un port
et par le bouton « Restaurer les logs », il rend les valeurs d'origine (<code>ReglageLog udp &lt;niveau&gt;</code>...).</p>

<h2>6. Commandes envoyées sur les cartes</h2>
<table>
<tr><th>Moment / essai</th><th>Carte</th><th>Commande (une ligne terminée par \\n)</th></tr>
<tr><td>ouverture</td><td>les deux</td><td><code>Status 5</code> (IP, hostname, MAC), <code>ReglageLog</code> puis les <code>ReglageLog ...</code> ci-dessus</td></tr>
<tr><td>ouverture</td><td>esclave</td><td><code>ReglageGlobal ModeConnexion</code> (réponse <code>{"ReglageGlobal":{"modeConnexion":"RangeExtender"}}</code> ou <code>"WifiClassique"</code>)</td></tr>
<tr><td>bascule</td><td>esclave</td><td><code>ReglageGlobal ModeConnexion WifiClassique &lt;ssid&gt; &lt;mdp&gt;</code> ou <code>ReglageGlobal ModeConnexion RangeExtender</code></td></tr>
<tr><td>Texte, unicast</td><td>émettrice</td><td><code>ReglageUDP envoiUniCast &lt;ip destinataire&gt; TESTUDP-n &lt;texte&gt;</code></td></tr>
<tr><td>Texte, multicast</td><td>émettrice</td><td><code>ReglageUDP envoiMultiCast TESTUDP-n &lt;texte&gt;</code></td></tr>
<tr><td>Trame ModbusUDP (E1)</td><td>maître</td><td><code>ReglageModbus envoiMessageUDP &lt;ip esclave&gt; ModbusUDP &lt;tid&gt; &lt;trame&gt;</code>, trame par défaut
<code>020100E00001FC0F</code> = adresse 2, fonction 0x01, registre 0x00E0, 1 bit, CRC16 poids faible en premier. Preuves : <code>REPOND_UDP: reponse a &lt;ip maître&gt; : ModbusUDP &lt;tid&gt; &lt;hexa&gt;</code> avec le <b>même tid</b>
sur l'esclave, réception <code>ModbusUDP &lt;tid&gt; ...</code> sur le maître, et <b>aucune</b> trame RS485 sur l'esclave. Témoin « sans tid » : même envoi sans tid, réponse <code>ModbusUDP &lt;hexa&gt;</code> sans tid.</td></tr>
<tr><td>ImAlive</td><td>esclave</td><td><code>ReglageUDP forceEnvoiParams ON</code> ; preuve : <code>LIRE_UDP</code> avec « ImAlive » sur le maître</td></tr>
<tr><td>Push d'état</td><td>esclave</td><td><code>Br var h = modbusFonctions.etatRuban(1376) if h != nil modbusFonctions.pousseEtat(1376, "uint16", h) else print("PAS_DE_RUBAN") end</code>
(état réel du ruban de la cuve, sans effet de bord) ; preuves : <code>POUSSE_ETAT: registre 1376 = ...</code> puis <code>LIRE_UDP</code> « ModbusPushUDP ... » sur le maître</td></tr>
</table>
<p>Référence : <code>outils_docs/PROTOCOLE_MODBUS.md</code>, §9 « Commandes sans fil vers les esclaves ».</p>

<h2>7. Onglet Grille ModBus</h2>
<p>La grille de validation de <code>outils_docs/AUDIT_MODBUS_2026-09-29.md</code> §6, ramenée à <b>un seul esclave</b> : celui dont l'ID, le Power du P4 et le
registre sont lus dans le persist du maître (par défaut la cuve : ID 2, POWER1, registre 1376). Les deux cartes doivent être ouvertes (onglet Essais).
Un seul test à la fois ; chaque test envoie ses commandes, lit les logs des deux cartes et juge chaque ligne :</p>
<ul>
<li><b>OK</b> : la preuve attendue a été vue (elle s'affiche dans « Détail / preuve ») ; <b>ECHEC</b> : un log interdit est apparu, ou un compte est hors bornes ;
<b>NON VU</b> : la preuve n'est pas arrivée dans le délai ; <b>INFO</b> : relevé pour information, sans verdict.</li>
<li>Une <b>consigne</b> (bandeau violet) demande un geste ou une constatation : « C'est fait », ou « Oui » / « Non ». Le test attend la réponse.</li>
</ul>
<table>
<tr><th>Test</th><th>Ce qu'il fait</th></tr>
<tr><td>1</td><td>Démarrage : <code>controleModbus</code> chargé sur les deux cartes, port RS485 de l'esclave ouvert (<code>Br print(...)</code>), puis voie de ses commandes lue par
<code>ReglageModbus VoieCommandes</code> (lecture seule) : elle fixe le mode des tests 2 et 6, qui refusent de démarrer tant
qu'elle est inconnue. La voie s'affiche en tête de l'onglet.</td></tr>
<tr><td>2</td><td>Régime normal, rien à toucher (durée réglable, 300 s par défaut, décompte à côté du bouton « Lancer ») : compte les relevés
et les requêtes exécutées par l'esclave, puis les réponses <b>reçues</b> par le P4 (<code>ModbusReceived</code> de son adresse : une requête
exécutée ne prouve pas que la réponse arrive) ; échec sur message abandonné pour l'esclave testé (<code>TERMINE_EN_VOL ... (esclave 2</code>, <code>ESCLAVE_MUET</code>),
hors-séquence, file pleine, <code>SLAVE_ERREUR</code>, chien de garde, écart de relai, erreur Berry. Les <code>SUR_TIMEOUT</code> ne sont qu'une
information : ce log ne nomme pas l'esclave, et chaque esclave absent du bus (rideau, carte 16 relais) en produit un par relevé. Voie <b>UDP</b> : les requêtes doivent partir
par UDP (<code>POMPE_QUEUE: envoi UDP</code>), sans envoi refusé, IP inconnue ni réponse au mauvais numéro de transaction ;
voie <b>Serial</b> : aucune requête UDP vers l'esclave.</td></tr>
<tr><td>3</td><td>Carte 16 relais, si elle est branchée : relevés, pas de chien de garde ni d'écart de voie.</td></tr>
<tr><td>4</td><td><code>Power1 ON</code> puis <code>OFF</code> sur le P4 : publication, exécution sur l'esclave, push de l'état, constatation visuelle
du ruban, puis <code>RubanEsclave1 auto</code>.</td></tr>
<tr><td>5</td><td><code>Power1 TOGGLE</code> sur l'esclave → push reçu par le P4 ; <code>Restart 1</code> de l'esclave → le P4 voit le redémarrage
(<code>ACCEPTE_SEQ</code>) et accepte le push suivant.</td></tr>
<tr><td>6</td><td>Panne : débranchez le câble RS485 de l'esclave → chien de garde du maître (jusqu'à 150 s) ; rebranchez → l'esclave répond de nouveau.<br>
Voie <b>UDP</b> : le test s'inverse. Câble débranché, le P4 doit continuer de recevoir les réponses par UDP pendant
150 s d'observation (plus long que le chien de garde), sans esclave déclaré muet ni message abandonné, puis après le rebranchement.</td></tr>
<tr><td>7</td><td>Découverte : <code>RgxState</code>, <code>forceEnvoiParams</code>, paramètres reçus par le maître, forme de <code>/json/discovery.json</code>
contrôlée sur le P4, puis constatation de la page /discovery.</td></tr>
</table>
<p>Le cadre « Commande libre » envoie une commande Tasmota à l'une des cartes ; la réponse paraît dans le journal de la carte (onglet Essais).
« Arrêter le test en cours » annule les étapes restantes. Routes : <code>GET /grille</code>, <code>POST /grille</code> (<code>action</code> = lancer, repondre, arreter).</p>
"""
