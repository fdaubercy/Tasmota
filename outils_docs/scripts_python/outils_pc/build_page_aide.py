"""Onglet « Aide » de la page Build et televersement : texte fixe, CSS et HTML inseres dans build_page.PAGE a la place
des marques /*CSS_AIDE*/ et <!--VUE_AIDE-->. Le changement d'onglet est dans build_page_fichiers.py (montreOnglet).

Le detail des fichiers .drvset, avec ses renvois au code, est dans outils_docs/FICHIERS_DRVSET.md.
"""

CSS = r"""
  #vue-aide h2{margin-top:0}
  #vue-aide h3{margin:12px 0 4px;font-size:14px}
  #vue-aide p,#vue-aide ul{margin:4px 0 8px}
  .a-table{overflow-x:auto}
  .a-table table{border-collapse:collapse;width:100%;font-size:13px}
  .a-table th,.a-table td{border-bottom:1px solid var(--bord);padding:4px 8px;text-align:left;vertical-align:top}
  .a-table th{color:var(--doux);font-weight:500}
"""

HTML = r"""
  <div id="vue-aide" role="tabpanel" aria-labelledby="onglet-aide" hidden>
    <div class="carte">
      <h2>Les fichiers cachés <code>.drvset</code> d'une carte</h2>
      <p>Certains pilotes de Tasmota gardent leurs réglages dans un petit fichier caché du file system, à côté du
      <code>_persist.json</code>, et non dans les réglages généraux. Le numéro est celui du pilote. Le fichier est une copie
      binaire de ses réglages, sauf <code>.drvset000</code>, qui est du JSON.</p>
      <div class="a-table"><table>
        <tr><th>Fichier</th><th>Rôle</th><th>Sur nos cartes</th></tr>
        <tr><td><code>.drvset000</code></td><td>JSON partagé, une clé par pilote : Domoticz, LoRa, DALI, BLE</td><td>créé par le premier pilote qui y écrit</td></tr>
        <tr><td><code>.drvset003</code></td><td>Énergie : calibrage, compteurs, seuils, tarifs (536 o)</td><td>carte énergie du bureau ; ailleurs seulement si un capteur d'énergie est détecté</td></tr>
        <tr><td><code>.drvset027</code></td><td>Volets natifs de Tasmota : positions, courses</td><td>envs avec <code>USE_SHUTTER</code></td></tr>
        <tr><td><code>.drvset042</code></td><td>Audio I2S : horloge, gains</td><td>P4, si une broche I2S est configurée</td></tr>
        <tr><td><code>.drvset086</code></td><td>Sonoff SPM</td><td>inactif sans ce matériel</td></tr>
        <tr><td><code>.drvset087</code>, <code>.drvset122</code></td><td>Afficheur TM1621 Sonoff, pilotes de démonstration</td><td>absents</td></tr>
        <tr><td><code>.snsset083</code>, <code>.snsset114</code></td><td>NeoPool, capteur de pression AMSx915</td><td>absents ; jamais dans la sauvegarde <code>/dl</code></td></tr>
      </table></div>
      <h3>Cycle de vie</h3>
      <ul>
        <li><b>Chargement :</b> au démarrage, par le pilote : valeurs par défaut, puis le fichier s'il existe.</li>
        <li><b>Écriture :</b> à chaque sauvegarde des réglages (toutes les <code>SaveData</code> secondes et au redémarrage), si le contenu a changé.</li>
        <li><b>Sauvegarde de la configuration (<code>/dl</code>) :</b> les <code>.drvset</code> y sont inclus.</li>
        <li><b>Effacement :</b> <code>Reset 4</code>, <code>5</code> ou <code>6</code>, et un flash par câble, qui remplace tout le file system. <code>Reset 1</code> et un changement de <code>CFG_HOLDER</code> les conservent.</li>
      </ul>
    </div>
    <div class="carte">
      <h2><code>.drvset003</code> : énergie</h2>
      <p><b>Contenu :</b> calibrage par phase (puissance, tension, courant, fréquence), compteurs (aujourd'hui, hier, total, export),
      <code>PowerDelta</code>, seuils d'alerte et de coupure, tarifs, affichage de la page d'accueil.</p>
      <h3>Quand le modifier</h3>
      <ul>
        <li><b>Calibrage :</b> après un changement de carte, ou si la mesure s'écarte d'un appareil de référence.</li>
        <li><b>Compteur :</b> pour le remettre à la bonne valeur après une perte.</li>
      </ul>
      <h3>Comment</h3>
      <ul>
        <li><b>Par la console, le plus simple :</b> <code>PowerCal</code>, <code>VoltageCal</code>, <code>CurrentCal</code> posent une valeur ; <code>PowerSet</code>, <code>VoltageSet</code>, <code>CurrentSet</code> la calculent d'après une charge connue ; <code>EnergyTotal</code> règle le compteur. Écrit dans le fichier à la sauvegarde suivante.</li>
        <li><b>Par le fichier :</b> le téléverser, puis redémarrer par <code>Restart 99</code>. Un <code>Restart 1</code> réécrirait le fichier avec les valeurs en mémoire.</li>
      </ul>
      <h3>Autour d'un flash par câble</h3>
      <p>La page copie ce fichier par le réseau avant l'envoi, le renvoie après, redémarre et relit le calibrage (étape « Calibrage »).
      Carte injoignable ou sans ce fichier : le flash a lieu quand même, sans rétablissement.
      Copies : <code>%LOCALAPPDATA%\outils_tasmota\build\drvset\</code>. En OTA, le file system n'est pas remplacé : rien à faire.</p>
      <h3>Sauvegarde complète</h3>
      <p>L'onglet « Sauvegarde configuration » garde le fichier <code>/dl</code> entier de la carte : Settings et fichiers <code>.drvset*</code> ensemble.
      Il compare, modifie paramètre par paramètre (dans une nouvelle sauvegarde) et restaure.</p>
    </div>
  </div>
"""
