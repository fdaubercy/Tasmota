"""Bouton « Téléverser » de la page de l'atelier (plan atelier-destinations, A6, spec §5) : bloc du script, ajoute a la fin de
atelier_graphiques_page_js.JS (meme <script>, memes globales : $, etat, echappe, message).

Visible seulement apres une ecriture reussie (reponse de POST /ecrire : `televerser`, voir atelier_graphiques_televerse.plan) ;
masque par televerseCache() des que la page change (modifie, choisitEnv). Il ouvre la page Build dans un nouvel onglet ; si le
serveur a vu le port 7700 muet, il affiche le message « lancer la page Build par l'annuaire » au lieu d'ouvrir un onglet mort.
"""

JS_TV = r"""
// ---- bouton « Téléverser » ----
function televerseCache() { etat.tv = null; $('televerser').classList.add('cache'); $('tv-info').textContent = ''; }
function televerse(t) {
  etat.tv = t || null;
  $('televerser').classList.toggle('cache', !t);
  $('tv-info').textContent = t ? t.fichiers.length + ' fichier(s) à téléverser' + (t.redemarrer ? ' · redémarrage nécessaire' : '')
    + (t.notes.length ? ' · ' + t.notes.join(' ; ') : '') : '';
}
$('televerser').onclick = function () {
  var t = etat.tv;
  if (!t) return;
  if (!t.build_actif) { message(echappe(t.message), 'rouge'); return; }
  window.open(t.url, '_blank');
};
"""
