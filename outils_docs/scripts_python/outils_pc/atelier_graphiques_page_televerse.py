"""Bouton « Téléverser » de la page de l'atelier (plan atelier-destinations, A6, spec §5) : bloc du script, ajoute a la fin de
atelier_graphiques_page_js.JS (meme <script>, memes globales : $, etat, echappe, message).

Visible seulement apres une ecriture reussie (reponse de POST /ecrire : `televerser`, voir atelier_graphiques_televerse.plan ; `{erreur}` = liste non calculee, texte sans bouton ;
`firmware_requis` = firmware de la carte d'avant la fonction : texte rouge, sans bouton, c'est la page Build qui doit compiler) ;
masque par televerseCache() des que la page change (modifie, choisitEnv). Il ouvre la page Build dans un nouvel onglet ; si le
serveur (GET /build_actif, au clic) voit le port 7700 muet, il affiche le message « lancer la page Build par l'annuaire » au lieu d'ouvrir un onglet mort.
"""

JS_TV = r"""
// ---- bouton « Téléverser » ----
function televerseCache() { etat.tv = null; $('televerser').classList.add('cache'); $('tv-info').textContent = ''; }
function televerse(t) {
  etat.tv = t || null;
  $('televerser').classList.toggle('cache', !t || !!t.erreur || !!t.firmware_requis || !t.fichiers.length);   // vide : la page Build construirait le FS pour rien
  $('tv-info').style.color = t && t.firmware_requis ? 'var(--rouge)' : '';
  $('tv-info').textContent = t && t.firmware_requis ? 'Le firmware de cette carte est antérieur à cette fonction : compilez et envoyez le firmware et le FS par la page Build.'
    : t && t.erreur ? 'Écrit, mais ' + t.erreur : t ? t.fichiers.length + ' fichier(s) à téléverser' + (t.redemarrer ? ' · redémarrage nécessaire' : '')
    + (t.notes.length ? ' · ' + t.notes.join(' ; ') : '') : '';
}
$('televerser').onclick = function () {
  var t = etat.tv;
  if (!t || t.erreur) return;
  lis('/build_actif').then(function (r) {                     // sondee au clic : la page Build a pu etre lancee ou arretee depuis l'ecriture
    if (r.actif) window.open(t.url, '_blank');
    else message("La page Build ne répond pas : lancer la page Build par l'annuaire (http://127.0.0.1:7600), puis cliquer de nouveau.", 'rouge');
  }).catch(function (e) { message('Atelier injoignable : ' + echappe(e.message), 'rouge'); });
};
"""
