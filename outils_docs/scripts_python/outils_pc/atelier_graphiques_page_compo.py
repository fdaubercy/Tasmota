"""Graphiques deja presents dans la composition de /graphiques (plan atelier-destinations, A11 I3) : bloc du script, ajoute a la
fin de atelier_graphiques_page_js.JS (memes globales : $, etat, echappe, message, poste, modifie, dessine...).

Liste (zone #compo-liste, sous le menu « Page ») la composition du depot, ou celle de la carte si elle a ete choisie. Un graphique
de forme atelier (« moteur: pages ») a « Modifier » (le charge dans l'editeur, avec ses `calculees` ; la reecriture est un « remplace »
au meme rang, avec le temoin `attendu`) et « Retirer » (ecrit tout de suite : diff puis ecriture, meme temoin). Un graphique de forme
actuelle est en lecture seule. Sans « Modifier », le graphique edite est un NOUVEAU graphique : la page le dit.
"""

JS_COMPO = r"""
// ---- graphiques de la composition de /graphiques : lister, modifier, retirer ----
function copie(x) { return JSON.parse(JSON.stringify(x)); }
function baseListee() { return etat.base === 'carte' ? 'carte' : 'depot'; }
function composeListee() {
  var c = etat.compo;
  return !c ? [] : (etat.base === 'carte' && c.carte_valide ? c.carte : c.depot) || [];
}
function dessineCompo() {
  var z = $('compo-liste'), c = etat.compo, g = grapheCourant(), h = '';
  if (etat.dest !== 'graphiques' || !c) { z.innerHTML = ''; return; }
  var liste = composeListee(), choix = attendChoix(), x = etat.indexEcrit;
  var remplace = x && x.cle === cleEcrit() && grapheCourant();
  h = '<div class="petit"><b>Graphiques de /graphiques</b> <span class="doux">(' + (etat.base === 'carte' && c.carte_valide ? 'version de la carte' : 'dépôt') + ')</span></div>';
  h += liste.length ? '<ul class="compo">' + liste.map(function (e, i) {
    var atelier = e && e.moteur === 'pages', titre = echappe((e && e.titre) || '(sans titre)');
    return '<li><span class="' + (remplace && x.index === i ? 'sel' : '') + '">' + (i + 1) + '. ' + titre + ' <span class="doux">' + echappe((e && e.type) || '') + '</span></span> ' +
      (!atelier ? '<span class="doux petit">forme actuelle, lecture seule</span>' : choix ? '' :
        '<button class="btn mini" data-compo="modifier" data-i="' + i + '">Modifier</button> <button class="btn mini" data-compo="retirer" data-i="' + i + '">Retirer</button>') + '</li>';
  }).join('') + '</ul>' : '<div class="petit doux">Aucun graphique dans la composition.</div>';
  if (choix) h += '<div class="petit doux">Choisir d\'abord la version de départ de la composition pour modifier ou retirer un graphique.</div>';
  else if (g) h += remplace ? '<div class="petit doux">Ce graphique <b>remplace</b> le n° ' + (x.index + 1) + ' de la composition.</div>'
    : '<div class="petit doux">Ce graphique sera <b>ajouté</b> comme nouveau graphique de /graphiques. Pour en modifier un existant, utiliser « Modifier » ci-dessus.</div>';
  z.innerHTML = h;
}
$('compo-liste').addEventListener('click', function (e) {
  var a = e.target.getAttribute && e.target.getAttribute('data-compo');
  if (a) (a === 'modifier' ? modifieGraphique : retireGraphique)(+e.target.getAttribute('data-i'));
});
// Charge le graphique n° i dans l'editeur : `calculees` rangees dans la description (renommees si le nom est pris par une autre formule)
function modifieGraphique(i) {
  var liste = composeListee(), attendu = copie(liste[i]), g = copie(liste[i]);
  etat.desc.pages.forEach(function (q) {     // une seule copie : Modifier n° 1, n° 2, n° 1 ne doit pas en laisser 3, qu'une page dediee emporterait
    var k = q.graphiques.indexOf(etat.copieCompo);
    if (k >= 0) q.graphiques.splice(k, 1);
  });
  if (!etat.desc.pages.length) { etat.desc.pages.push(nouvellePage(0)); etat.page = 0; pageCourante().graphiques = []; }
  var p = pageCourante(), cc = g.calculees || {}, tout = etat.desc.calculees = etat.desc.calculees || {};
  delete g.moteur; delete g.calculees;
  Object.keys(cc).forEach(function (nom) {
    var n = nom, k = 1;
    while (tout[n] && JSON.stringify(tout[n]) !== JSON.stringify(cc[nom])) n = nom + '-' + (++k);
    tout[n] = cc[nom];
    if (n !== nom) g.series = g.series.map(function (s) {
      return cheminDe(s) !== 'calc:' + nom ? s : (typeof s === 'object' ? Object.assign({}, s, {chemin: 'calc:' + n}) : 'calc:' + n);
    });
  });
  p.graphiques.push(g); etat.copieCompo = g; etat.graphe = p.graphiques.length - 1;
  etat.indexEcrit = {cle: cleEcrit(), index: i, attendu: attendu, base: baseListee()};
  modifie(true);
}
function retireGraphique(i) {
  var g = composeListee()[i], corps = {env: etat.env, destination: 'graphiques', operation: 'retire', index: i, attendu: g, base: baseListee()};
  if (!confirm('Retirer « ' + ((g && g.titre) || '') + ' » de la composition de /graphiques ?\n\nLe dépôt est modifié tout de suite (graphiques.json).')) return;
  clearTimeout(minuterie);          // un diff differe verrait le depot deja change, sans `base`
  poste('/diff', corps).then(function (d) { return poste('/ecrire', Object.assign({empreinte: d.empreinte}, corps)); }).then(function (r) {
    etat.indexEcrit = null; etat.base = 'depot'; etat.diff = null;
    message('Retiré : ' + r.ecrits.map(echappe).join(', ') + '<br>Puis « Téléverser » pour la carte.', 'vert');
    televerse(r.televerser);
    return chargeCompo().then(function () { $('motifs').innerHTML = ''; dessineDestination(); dessineCode(); });     // un diff deja parti a pu etre refuse pour la meme raison
  }).catch(function (e) {
    message('Rien n\'est retiré : ' + echappe(e.message), 'rouge');
    chargeCompo().then(dessineDestination);
  });
}
"""
