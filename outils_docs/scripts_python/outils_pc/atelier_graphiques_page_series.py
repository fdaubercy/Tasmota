"""Reglages par serie de la page de l'atelier des graphiques (plan A7b) : bloc du script, ajoute a la fin de
atelier_graphiques_page_js.JS (meme <script>, memes globales : $, etat, echappe, infoSerie, grapheCourant, modifie).

Une serie de graphique est une chaine (chemin) ou {chemin, libelle, unite, couleur}. Une serie ajoutee porte l'unite que
la carte donne (A4) si elle tient dans les 10 octets du schema (jamais tronquee : sinon la chaine, unite en suggestion) ;
vider tous les reglages la ramene a la chaine. La couleur est grisee pour les styles qui l'ignorent (chaleur, radar).
"""

JS_SERIES = r"""
// ---- reglages par serie (colonne de droite) ----
function nouvelleSerie(c) {
  var u = infoSerie(c).unite;
  return u && new TextEncoder().encode(u).length <= 10 ? {chemin: c, unite: u} : c;
}
// Une ligne par serie : libelle, unite (l'unite connue de la carte en suggestion), couleur (celle de la palette sans reglage)
function dessineSeries(g) {
  var sansCouleur = g.type === 'chaleur' || g.type === 'radar';
  $('r-series').innerHTML = g.series.map(function (s, i) {
    var o = s && typeof s === 'object' ? s : {chemin: s}, connue = infoSerie(o.chemin).unite || '';
    var champ = function (cle) { return ' data-serie-champ="' + cle + '" data-i="' + i + '"'; };
    // shortcut: rang dans la liste, pas parmi les series presentes (le moteur saute les absentes) ; a revoir si cela trompe
    var palette = PagesGraphiques.PALETTE[i % PagesGraphiques.PALETTE.length];
    return '<div class="serie"><div class="petit doux" title="' + echappe(o.chemin) + '">' + echappe(o.chemin) + '</div><div class="ligne">' +
      '<input type="text"' + champ('libelle') + ' maxlength="30" placeholder="libellé" value="' + echappe(o.libelle || '') + '">' +
      '<input type="text" class="unite"' + champ('unite') + ' maxlength="10" placeholder="' + echappe(connue || 'unité') +
      '" title="unité' + (connue ? ' (carte : ' + echappe(connue) + ')' : '') + '" value="' + echappe(o.unite || '') + '">' +
      '<input type="color"' + champ('couleur') + ' value="' + echappe(o.couleur || palette) + '"' +
      (sansCouleur ? ' disabled title="ce style n\'utilise pas la couleur des séries"' : '') + '>' +
      (sansCouleur ? '' : '<a href="#" data-serie-raz="' + i + '" title="couleur de la palette">✕</a>') + '</div></div>';
  }).join('') || '<div class="petit doux">aucune : cocher une série à gauche</div>';
}
// Pose (ou retire si vide) un reglage de la serie i ; sans reglage, la serie redevient la chaine de son chemin
function poseSerie(g, i, cle, v) {
  var o = g.series[i] && typeof g.series[i] === 'object' ? g.series[i] : {chemin: g.series[i]};
  if (v === '') delete o[cle]; else o[cle] = v;
  g.series[i] = Object.keys(o).length > 1 ? o : o.chemin;
}
$('r-series').addEventListener('input', function (e) {
  var cle = e.target.getAttribute('data-serie-champ'), g = grapheCourant();
  if (!cle || !g) return;
  poseSerie(g, +e.target.getAttribute('data-i'), cle, e.target.value);
  modifie(false);
});
$('r-series').addEventListener('click', function (e) {
  var i = e.target.getAttribute('data-serie-raz'), g = grapheCourant();
  if (i === null || !g) return;
  e.preventDefault();
  poseSerie(g, +i, 'couleur', '');
  modifie(true);
});
"""
