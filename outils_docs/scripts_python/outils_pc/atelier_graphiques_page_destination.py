"""Menu « Page » et destination « Graphiques » de la page de l'atelier (plan atelier-destinations, A5) : bloc du script,
ajoute a la fin de atelier_graphiques_page_js.JS (meme <script>, memes globales : $, etat, lis, echappe, ligneDiff, modifie).

etat.dest = 'pages' (defaut : pages dediees) ou 'graphiques' ; etat.compo = reponse de GET /composition?env= (lecture de la carte
par le serveur de l'atelier) ; etat.base = 'carte' | 'depot' (choix quand la composition de la carte differe du depot, spec §4.3).
Le menu propose les pages dediees, « Graphiques (/graphiques) » si la carte a l'historique, « Autre… » (nouvelle page).
"""

JS_DEST = r"""
// ---- menu « Page » et destination « Graphiques » ----
function chargeCompo() {
  var env = etat.env;
  return lis('/composition?env=' + encodeURIComponent(env)).then(function (c) { if (env === etat.env) etat.compo = c; },
    function () { if (env === etat.env) etat.compo = null; });
}
function dessinePages() {
  var sel = $('r-page'), v = etat.dest === 'graphiques' ? 'graphiques' : etat.page;
  sel.innerHTML = etat.desc.pages.map(function (p, i) {
    return '<option value="' + i + '">/' + echappe(p.id) + ' — « ' + echappe(p.titre) + ' »</option>';
  }).join('') + (etat.compo && etat.compo.historique ? '<option value="graphiques">Graphiques (/graphiques)</option>' : '') +
    '<option value="autre">Autre… (nouvelle page)</option>';
  sel.value = v;
}
$('r-page').addEventListener('change', function () {
  if (this.value === 'graphiques') etat.dest = 'graphiques';
  else {
    etat.dest = 'pages';
    if (this.value === 'autre') { etat.indexEcrit = null; etat.desc.pages.push(nouvellePage(etat.desc.pages.length)); etat.page = etat.desc.pages.length - 1; }
    else etat.page = +this.value;
    etat.graphe = 0;
  }
  modifie(true);
});
// Corps de /diff et /ecrire pour /graphiques : le graphique edite est ajoute (forme atelier, « moteur » pose par le serveur)
function corpsGraphiques() {
  var c = etat.compo, x = etat.indexEcrit, o = {env: etat.env, destination: 'graphiques', operation: 'ajoute', graphique: grapheCourant()};
  if (x && x.cle === cleEcrit()) { o.operation = 'remplace'; o.index = x.index; o.base = 'depot'; return o; }   // le depot porte deja ce graphique
  if (c && c.etat === 'differente' && etat.base) o.base = etat.base;
  return o;
}
function attendChoix() { return !!(etat.compo && etat.compo.etat === 'differente' && !etat.base); }
// Graphique deja ecrit pour cette carte, cette page et ce graphique : les ecritures suivantes le REMPLACENT (jamais de doublon)
function cleEcrit() { return etat.env + '|' + etat.page + '|' + etat.graphe; }
function oubliIndex(e) {
  if (!etat.indexEcrit || !/^index/.test(e.message)) return false;
  etat.indexEcrit = null;
  message('Le graphique écrit n\'existe plus dans la composition : il sera ajouté de nouveau.', '');
  verifieEtDiff();
  return true;
}
function apresEcriture(r) {
  if (etat.dest !== 'graphiques') { verifieEtDiff(); return; }
  if (typeof r.index === 'number') { etat.indexEcrit = {cle: cleEcrit(), index: r.index}; etat.base = 'depot'; }
  // pas de nouveau diff avant une modification
  etat.diff = null; dessineCode();
  chargeCompo().then(dessineDestination);
  $('resume').textContent = 'écrit dans le dépôt : modifier le graphique pour écrire à nouveau';
}
function dessineDestination() {
  var g = etat.dest === 'graphiques', c = etat.compo, h = '';
  document.querySelectorAll('.champ-page').forEach(function (e) { e.classList.toggle('cache', g); });
  $('suppr-page').classList.toggle('cache', g);
  if (g && c && c.etat === 'non_verifiee')
    h = '<div class="avert"><b>Composition de la carte non vérifiée</b><br>' + echappe((c.motif || '').replace(/^composition de la carte non verifiee\s*/i, '')
      .replace(/^\(|\)$/g, '') || 'carte injoignable') + '<br>Les changements faits sur la carte ne sont pas connus : l\'envoi les remplacerait.</div>';
  else if (g && c && c.etat === 'differente') {
    var radio = function (v, texte, off) {
      return '<label class="ch"><input type="radio" name="base" value="' + v + '"' + (etat.base === v ? ' checked' : '') + (off ? ' disabled' : '') + '> ' + texte + '</label>';
    };
    h = '<div class="avert"><b>La composition de /graphiques a changé sur la carte</b> depuis le dernier envoi (diff dépôt → carte).</div>' +
      '<pre class="code">' + c.diff.split('\n').map(ligneDiff).join('\n') + '</pre>' +
      radio('carte', 'Partir de la version de la carte', !c.carte_valide) +
      '<div class="petit" style="color:var(--rouge)">Les graphiques écrits dans le dépôt et pas encore téléversés seront perdus.</div>' +
      (c.carte_valide ? '' : '<div class="petit doux">Indisponible : ' + c.carte_motifs.map(echappe).join(' ; ') + '</div>') +
      radio('depot', 'Garder celle du dépôt') +
      '<div class="petit" style="color:var(--rouge)">Les changements faits sur la carte seront perdus à l\'envoi.</div>' +
      (etat.base ? '' : '<div class="petit doux">Sans choix, rien n\'est écrit.</div>');
  } else if (g && c && c.etat === 'identique') h = '<div class="petit doux">Composition de la carte identique à celle du dépôt.</div>';
  $('destination').innerHTML = h;
}
$('destination').addEventListener('change', function (e) {
  if (e.target.name !== 'base') return;
  etat.base = e.target.value; etat.indexEcrit = null; dessineDestination(); modifie(false);
});
"""
