"""Script de la page de l'atelier des graphiques (plan A7) ; HTML et CSS dans atelier_graphiques_page.py.

Etat : la description en cours d'edition (schema de atelier_graphiques_description), la page et le graphique choisis.
Toute modification relance, apres 300 ms : l'apercu (PagesGraphiques.page, le moteur de la carte), le conseil de style
(POST /conseil), la validation (POST /valide) puis le diff (POST /diff). « Ecrire » n'est actif que si le diff affiche
correspond a la description du moment (meme corps que celui du diff, empreinte du serveur).
Series du graphique : chaine (chemin) ou objet {chemin, libelle, unite, couleur} (A7b) ; un objet dont tous les reglages
sont vides redevient la chaine. Les deux formes se lisent par cheminDe(). Les reglages par serie (dessineSeries,
nouvelleSerie) sont dans atelier_graphiques_page_series.py, le menu « Page » et la destination « Graphiques » (A5) dans
atelier_graphiques_page_destination.py, ajoutes a la fin de JS.
Lecteur de l'apercu : PagesGraphiques.lecteurCarte, celui de la carte, dont les fetch (faits pendant l'appel) sont
rediriges vers /valeurs?env= : la conversion des reponses de la carte est donc la sienne, pas une copie.
"""

from atelier_graphiques_page_destination import JS_DEST
from atelier_graphiques_page_series import JS_SERIES

JS = r"""
'use strict';
var $ = function (id) { return document.getElementById(id); };
var INTENTIONS = [['evolution', 'Une évolution dans le temps'], ['seuil', 'La valeur actuelle face à un seuil'],
  ['comparaison', 'Comparer plusieurs mesures'], ['repartition', 'Une répartition (parts d\'un total)'],
  ['cumul', 'Un cumul par heure, jour ou mois'], ['lien', 'Le lien entre deux mesures'], ['habitudes', 'Des habitudes (heure × jour)']];
var NOMS = {'courbe': 'Courbe', 'aire': 'Aire', 'escalier': 'Escalier', 'barres': 'Barres', 'barres-empilees': 'Barres empilées',
  'barres-periode': 'Barres par période', 'deux-axes': 'Courbes, 2 axes', 'lies': 'Graphiques liés', 'cadran': 'Cadran à aiguille',
  'anneau': 'Anneau', 'chaleur': 'Carte de chaleur', 'nuage': 'Nuage de points', 'radar': 'Radar', 'liquide': 'Liquide animé',
  'demi-cercle': 'Demi-cercle SVG'};
var etat = {envs: [], env: '', series: null, dest: 'pages', compo: null, base: null, indexEcrit: null, desc: null, page: 0, graphe: 0, solidifier: false, mode: 'graphique',
  vue: 'pc', sombre: false, conseil: null, motifs: [], diff: null, diffSig: '', onglet: '', source: ''};
var gabarit = '', apercuCtrl = null, minis = [], dernieres = {}, minuterie = null;

function echappe(s) { return String(s).replace(/[&<>"']/g, function (c) { return '&#' + c.charCodeAt(0) + ';'; }); }
function requete(methode, url, corps) {
  var o = {method: methode, headers: {}};
  if (corps !== undefined) { o.headers['X-Atelier-Graphiques'] = '1'; o.headers['Content-Type'] = 'application/json'; o.body = JSON.stringify(corps); }
  return fetch(url, o).then(function (r) {
    if (!r.ok) return r.text().then(function (t) { throw new Error(t || ('HTTP ' + r.status)); });
    return r.json();
  });
}
function lis(url) { return requete('GET', url); }
function poste(url, corps) { return requete('POST', url, corps); }
function message(texte, genre) { $('message').innerHTML = texte ? '<div class="avert ' + (genre || '') + '">' + texte + '</div>' : ''; }

function pageCourante() { return etat.desc.pages[etat.page]; }
function grapheCourant() { var p = pageCourante(); return p ? p.graphiques[etat.graphe] : null; }
function envCourant() { return etat.envs.filter(function (e) { return e.nom === etat.env; })[0] || {}; }
function infoSerie(c) {
  return (etat.series && etat.series.series || []).filter(function (s) { return s.chemin === c; })[0] || {chemin: c, unite: ''};
}
function cheminDe(s) { return s && typeof s === 'object' ? s.chemin : s; }
function nouveauGraphique() {
  var ss = (etat.series && etat.series.series) || [], h = etat.series && etat.series.historique;
  var s = ss.filter(function (x) { return x.historique; })[0] || ss[0];
  var g = {type: h ? 'courbe' : 'cadran', titre: s ? s.libelle : 'Nouveau graphique', series: s ? [nouvelleSerie(s.chemin)] : []};
  if (h) g.periode = 'jour';
  return g;
}
function nouvellePage(n) { return {id: 'tableau' + (n ? '-' + (n + 1) : ''), titre: 'Tableau', acces: 'bouton', graphiques: [nouveauGraphique()]}; }
function corpsEcriture() {
  if (etat.dest === 'graphiques') return corpsGraphiques();
  return {env: etat.env, description: etat.desc.pages.length ? etat.desc : null, solidifier: etat.solidifier};
}

// ---- carte et donnees (colonne de gauche) ----
function choisitEnv(env) {
  etat.env = env; etat.dest = 'pages'; etat.compo = null; etat.base = null; etat.indexEcrit = null;
  dernieres = {};
  history.replaceState(null, '', '?env=' + encodeURIComponent(env));
  $('nom-carte').textContent = env;
  $('lien-build').href = 'http://127.0.0.1:7700/?env=' + encodeURIComponent(env) + '#fichiers';
  message('');
  return Promise.all([lis('/description?env=' + encodeURIComponent(env)), litSeries(), chargeCompo()]).then(function (r) {
    if (env !== etat.env) return;                                  // reponse d'un env quitte entre-temps
    var d = r[0];
    etat.solidifier = d.solidifie;
    etat.desc = d.description || {version: 1, pages: [nouvellePage(0)]};
    if (!d.description) message(d.erreur ? echappe(d.erreur) + ' : proposition de départ à la place.' :
      'Aucune page de graphiques sur cette carte : proposition de départ (rien n\'est écrit avant « Écrire dans le dépôt »).');
    etat.page = 0; etat.graphe = 0;
    dessine(); actualise();
  }).catch(function (e) { if (env === etat.env) message('Lecture impossible : ' + echappe(e.message), 'rouge'); });
}
function litSeries() {
  var env = etat.env;
  $('relire').textContent = 'lecture de la carte…'; $('relire').className = 'pastille';
  return lis('/series?env=' + encodeURIComponent(env)).then(function (s) {
    if (env !== etat.env) return;
    etat.series = s; source(s.source, s.motif);
  });
}
function source(src, motif) {
  if (!src) return;
  etat.source = src;
  var ip = envCourant().ip, b = $('relire');
  b.textContent = src === 'carte' ? '● en ligne ' + ip : 'valeurs simulées';
  b.className = 'pastille ' + (src === 'carte' ? 'ok' : 'non');
  if (motif !== undefined) etat.motifSource = motif;
  $('bandeau').classList.toggle('cache', src === 'carte');
  $('bandeau').textContent = 'Valeurs simulées : ' + (etat.motifSource || 'carte injoignable') +
    '. L\'aperçu ne montre pas les vraies mesures ; l\'édition et l\'écriture restent possibles.';
  $('pastille-lib').textContent = 'ECharts ' + (window.echarts ? echarts.version : '?') + ' · historique ' +
    (etat.series && etat.series.historique ? 'actif' : 'absent');
}
function dessineArbre() {
  var g = grapheCourant() || {series: []}, ss = (etat.series && etat.series.series) || [], h = [];
  function ligne(s, classe) {
    return '<div class="' + classe + '"><label class="ch" title="' + echappe(s.chemin) + '"><input type="checkbox" data-serie="' +
      echappe(s.chemin) + '"' + (g.series.map(cheminDe).indexOf(s.chemin) >= 0 ? ' checked' : '') + '> ' + echappe(s.libelle || s.chemin) +
      ' <span class="doux petit">' + echappe(s.etat ? 'état' : (s.unite || '')) + '</span></label></div>';
  }
  function groupe(titre, liste) {
    h.push('<div class="gr"><b>' + titre + '</b></div>');
    var avant = null;
    liste.forEach(function (s) {
      var pref = s.chemin.split('.').slice(0, -1).join(' › ');
      if (pref && pref !== avant) h.push('<div class="n2">' + echappe(pref) + '</div>');
      avant = pref;
      h.push(ligne(s, pref ? 'n3' : 'n2'));
    });
  }
  var histo = ss.filter(function (s) { return s.historique; });
  groupe('Historique <span class="doux petit">(/histo, ' + histo.length + ' séries)</span>', histo);
  groupe('JSON SENSOR <span class="doux petit">(instantané)</span>', ss.filter(function (s) { return !s.historique; }));
  groupe('Calculées <a id="ajout-calc">+ ajouter une formule</a>', Object.keys(etat.desc.calculees || {}).map(function (n) {
    return {chemin: 'calc:' + n, libelle: n + ' (' + etat.desc.calculees[n].nature + ')', unite: ''};
  }));
  h.push('<div class="gr"><b>En flash</b> <span class="doux petit">(aucune sur cette carte)</span></div>');
  $('arbre').innerHTML = h.join('');
  $('ajout-calc').onclick = function () { $('form-calc').classList.remove('cache'); };
}
$('arbre').addEventListener('change', function (e) {
  var c = e.target.getAttribute('data-serie'), g = grapheCourant();
  if (!c || !g) return;
  if (e.target.checked) { if (g.series.map(cheminDe).indexOf(c) < 0) g.series.push(nouvelleSerie(c)); }
  else g.series = g.series.filter(function (x) { return cheminDe(x) !== c; });
  modifie(true);
});
$('calc-annuler').onclick = function () { $('form-calc').classList.add('cache'); };
$('calc-ajouter').onclick = function () {
  var nom = $('calc-nom').value.trim();
  if (!nom) return;
  etat.desc.calculees = etat.desc.calculees || {};
  etat.desc.calculees[nom] = {formule: $('calc-formule').value.trim(), nature: $('calc-nature').value};
  $('form-calc').classList.add('cache');
  modifie(true);
};

// ---- reglages (colonne de droite) ----
function nombreOuRien(g, cle, v) { if (v === '' || isNaN(+v)) delete g[cle]; else g[cle] = +v; }
function choixOuRien(g, cle, v, defaut) { if (v === '' || v === defaut) delete g[cle]; else g[cle] = v; }
var CHAMPS = {
  'r-titre': function (g, v) { g.titre = v; },
  'r-min': function (g, v) { nombreOuRien(g, 'min', v); },
  'r-max': function (g, v) { nombreOuRien(g, 'max', v); },
  'r-periode': function (g, v) { choixOuRien(g, 'periode', v, 'direct'); },
  'r-cadence': function (g, v) { nombreOuRien(g, 'cadence', v); },
  'r-cumul': function (g, v) { choixOuRien(g, 'cumul', v); },
  'r-largeur': function (g, v) { choixOuRien(g, 'largeur', v, 'demi'); },
  'r-hauteur': function (g, v) { nombreOuRien(g, 'hauteur', v); }
};
Object.keys(CHAMPS).forEach(function (id) {
  $(id).addEventListener(id === 'r-titre' || id === 'r-min' || id === 'r-max' ? 'input' : 'change', function () {
    var g = grapheCourant();
    if (!g) return;
    CHAMPS[id](g, $(id).value);
    if (id === 'r-min' || id === 'r-max') dessineZones(g);
    modifie(false);
  });
});
[['r-page-id', 'input', 'id'], ['r-page-titre', 'input', 'titre'], ['r-acces', 'change', 'acces']].forEach(function (c) {
  $(c[0]).addEventListener(c[1], function () {
    var p = pageCourante();
    if (!p) return;
    p[c[2]] = this.value; dessinePages(); modifie(false);
  });
});
$('r-solidifier').addEventListener('change', function () { etat.solidifier = this.checked; modifie(false); });
function approche(g, f) {
  return typeof g.min === 'number' && typeof g.max === 'number' ? ' ≈ ' + Math.round(g.min + f * (g.max - g.min)) : '';
}
function dessineZones(g) {
  $('r-zones').innerHTML = (g.zones || []).map(function (z, i) {
    var abs = approche(g, z[0]);
    return '<div class="zone"><input type="color" data-zone="' + i + '" value="' + echappe(z[1]) + '">jusqu\'à <input type="number" min="0" max="100" data-zone="' +
      i + '" value="' + Math.round(z[0] * 100) + '"> %<span class="doux">' + abs + '</span><a href="#" data-retire="' + i + '">✕</a></div>';
  }).join('') || '<div class="petit doux">aucun</div>';
}
$('r-zones').addEventListener('input', function (e) {
  var i = e.target.getAttribute('data-zone'), g = grapheCourant();
  if (i === null || !g) return;
  if (e.target.type === 'color') g.zones[i][1] = e.target.value;
  else {
    g.zones[i][0] = Math.max(0, Math.min(1, (+e.target.value || 0) / 100));
    e.target.parentNode.querySelector('.doux').textContent = approche(g, g.zones[i][0]);
  }
  modifie(false);
});
$('r-zones').addEventListener('click', function (e) {
  var i = e.target.getAttribute('data-retire'), g = grapheCourant();
  if (i === null || !g) return;
  e.preventDefault();
  g.zones.splice(+i, 1);
  if (!g.zones.length) delete g.zones;
  modifie(true);
});
$('r-ajout-zone').onclick = function (e) {
  e.preventDefault();
  var g = grapheCourant();
  if (!g) return;
  g.zones = g.zones || [];
  g.zones.push([g.zones.length ? 0.4 : 0.2, g.zones.length ? '#c27400' : '#c0392b']);
  modifie(true);
};
function dessineReglages() {
  var g = grapheCourant(), p = pageCourante(), h = etat.series && etat.series.historique;
  dessinePages();
  $('r-page-id').value = p ? p.id : ''; $('r-page-titre').value = p ? p.titre : ''; $('r-acces').value = p ? (p.acces || 'bouton') : 'bouton';
  $('r-solidifier').checked = etat.solidifier;
  ['r-page-id', 'r-page-titre', 'r-acces'].forEach(function (id) { $(id).disabled = !p; });
  ['r-titre', 'r-min', 'r-max', 'r-periode', 'r-cadence', 'r-cumul', 'r-largeur', 'r-hauteur', 'r-ajout-zone'].forEach(function (id) { $(id).disabled = !g; });
  if (!g) { $('r-zones').innerHTML = ''; $('r-series').innerHTML = ''; return; }
  $('r-titre').value = g.titre; $('r-min').value = g.min !== undefined ? g.min : ''; $('r-max').value = g.max !== undefined ? g.max : '';
  $('r-periode').value = g.periode || 'direct'; $('r-cadence').value = g.cadence || ''; $('r-cumul').value = g.cumul || '';
  $('r-largeur').value = g.largeur || 'demi'; $('r-hauteur').value = g.hauteur || '';
  ['jour', 'mois'].forEach(function (v) {
    var o = $('r-periode').querySelector('option[value=' + v + ']');
    o.disabled = !h; o.title = h ? '' : 'pas d\'historique sur cette carte';
  });
  $('ligne-cumul').classList.toggle('cache', g.type !== 'barres-periode');
  dessineZones(g);
  dessineSeries(g);
}
$('ajout-graphique').onclick = function () {
  oublieEcrit();
  var p = pageCourante();
  if (!p) return;
  p.graphiques.push(nouveauGraphique()); etat.graphe = p.graphiques.length - 1; modifie(true);
};
$('suppr-graphique').onclick = function () {
  oublieEcrit();
  var p = pageCourante();
  if (!p || !p.graphiques.length) return;
  p.graphiques.splice(etat.graphe, 1); etat.graphe = Math.max(0, etat.graphe - 1); modifie(true);
};
$('suppr-page').onclick = function () {
  if (!pageCourante()) return;
  oublieEcrit(); etat.desc.pages.splice(etat.page, 1); etat.page = Math.max(0, etat.page - 1); etat.graphe = 0;
  if (!etat.desc.pages.length) message('Plus aucune page : l\'écriture retire le moteur de cette carte (ligne d\'autoexec, listes du cenv).');
  modifie(true);
};
function dessineAlertes() {
  var e = envCourant(), types = {}, h = [];
  etat.desc.pages.forEach(function (p) { p.graphiques.forEach(function (g) { types[g.type] = true; }); });
  if (e.exclut_echarts && Object.keys(types).some(function (t) { return t !== 'demi-cercle'; }))
    h.push('ECharts est exclu du FS de ' + echappe(e.nom) + ' : sur la carte, seuls les demi-cercles s\'afficheront (l\'écriture reste possible).');
  if (e.exclut_liquidfill && types.liquide)
    h.push('liquidfill est exclu du FS de ' + echappe(e.nom) + ' : le style « liquide » sera refusé à l\'écriture.');
  $('alertes').innerHTML = h.map(function (t) { return '<div class="avert">' + t + '</div>'; }).join('');
}

// ---- apercu : le moteur de la carte ----
function lecteur(chemins, periode) {
  var vrai = window.fetch, env = etat.env;
  // Couplage : lecteurCarte (data/sd/js/pages_graphiques.js) lance ses fetch de facon synchrone pendant cet appel ; s'il les
  // differait, ils partiraient tels quels (/pages, /histo) vers l'atelier, qui les refuse (404) : l'apercu dirait « Lecture impossible ».
  window.fetch = function (url) {
    var u = String(url), q = u.split('?')[1] || '';
    if (!/^\/(pages\?f=valeurs&|histo\?)/.test(u)) return Promise.reject(new Error('lecture non prévue pour l’aperçu : ' + u.split('?')[0]));
    return vrai('/valeurs?env=' + encodeURIComponent(env) + '&c=' + chemins.map(encodeURIComponent).join(',') + '&' + q)
      .then(function (r) { if (env === etat.env) source(r.headers.get('X-Source')); return r; });
  };
  try {
    return PagesGraphiques.lecteurCarte('mesures', !!(etat.series && etat.series.historique))(chemins, periode)
      .then(function (d) {
        dernieres[env + '|' + periode + '|' + chemins.join(',')] = d;      // par env et par groupe de lecture
        if (env === etat.env && !etat.minisPleins) dessineConseil();
        return d;
      });
  } finally { window.fetch = vrai; }
}
function apercu() {
  if (apercuCtrl) apercuCtrl.arrete();
  apercuCtrl = null;
  var p = pageCourante(), g = grapheCourant(), cadre = $('cadre');
  cadre.className = 'cadre' + (etat.mode === 'page' ? ' page' : '') + (etat.vue === 'telephone' ? ' telephone' : '') + (etat.sombre ? ' sombre' : '');
  $('tete-carte').textContent = 'Tasmota · ' + etat.env; $('tete-titre').textContent = p ? p.titre : '';
  $('titre-apercu').textContent = etat.mode === 'page' ? 'Aperçu — page /' + (p ? p.id : '') : 'Aperçu — ' + (etat.source === 'carte' ? 'vraies valeurs de la carte' : 'valeurs simulées');
  $('apercu').innerHTML = gabarit;
  var zone = $('apercu').querySelector('#pg_page');
  if (!p || !g) { zone.innerHTML = '<p class="pg_msg">Aucun graphique : « + Graphique » ou le menu « Page ».</p>'; return; }
  var gs = etat.mode === 'page' ? p.graphiques : [Object.assign({}, g, {largeur: 'pleine'})];
  apercuCtrl = PagesGraphiques.page(zone, {page: {id: p.id, titre: p.titre, graphiques: gs}, calculees: etat.desc.calculees || {}}, lecteur);
  zone.querySelectorAll('.pg_tuile').forEach(function (t, i) {
    var j = etat.mode === 'page' ? i : etat.graphe;
    t.classList.toggle('sel', etat.mode === 'page' && j === etat.graphe);
    if (etat.mode !== 'page') return;
    t.draggable = true;
    t.title = 'Clic : régler ce graphique ; glisser : le déplacer dans la page';
    t.addEventListener('click', function () { etat.graphe = j; zone.querySelectorAll('.pg_tuile').forEach(function (x, k) { x.classList.toggle('sel', k === j); }); dessine(); demandeConseil(); });
    t.addEventListener('dragstart', function (e) { e.dataTransfer.setData('text/plain', String(j)); });
    t.addEventListener('dragover', function (e) { e.preventDefault(); t.classList.add('survol'); });
    t.addEventListener('dragleave', function () { t.classList.remove('survol'); });
    t.addEventListener('drop', function (e) {
      e.preventDefault();
      var de = e.dataTransfer.getData('text/plain');
      if (!/^\d+$/.test(de) || +de >= p.graphiques.length || +de === j) return;   // depot venu d'ailleurs : ignore
      de = +de; oublieEcrit();
      p.graphiques.splice(j, 0, p.graphiques.splice(de, 1)[0]); etat.graphe = j; modifie(true);
    });
  });
}
document.querySelectorAll('[data-mode]').forEach(function (b) { b.onclick = function () { etat.mode = b.getAttribute('data-mode'); bascules(); apercu(); }; });
document.querySelectorAll('[data-vue]').forEach(function (b) { b.onclick = function () { etat.vue = b.getAttribute('data-vue'); bascules(); apercu(); }; });
$('sombre').onclick = function () { etat.sombre = !etat.sombre; bascules(); apercu(); };
function bascules() {
  document.querySelectorAll('[data-mode]').forEach(function (b) { b.classList.toggle('actif', b.getAttribute('data-mode') === etat.mode); });
  document.querySelectorAll('[data-vue]').forEach(function (b) { b.classList.toggle('actif', b.getAttribute('data-vue') === etat.vue); });
  $('sombre').classList.toggle('actif', etat.sombre);
}

// ---- styles proposes (POST /conseil) ----
function demandeConseil() {
  var g = grapheCourant();
  if (!g) { $('vignettes').innerHTML = ''; return; }
  var series = g.series.map(function (x) {
    var c = cheminDe(x), o = {chemin: c, unite: (typeof x === 'object' && x.unite) || infoSerie(c).unite || ''};
    if (g.series.length === 1 && typeof g.min === 'number' && typeof g.max === 'number') { o.min = g.min; o.max = g.max; }
    return o;
  });
  poste('/conseil', {intention: $('intention').value, series: series, destination: 'page', historique: !!(etat.series && etat.series.historique)})
    .then(function (r) { etat.conseil = r; dessineConseil(); })
    .catch(function (e) { $('vignettes').innerHTML = '<div class="avert rouge">' + echappe(e.message) + '</div>'; });
}
// Dernieres valeurs lues pour ce graphique : celles d'un groupe de l'env courant, de sa periode, qui lit toutes ses series
function donneesDe(g) {
  var pref = etat.env + '|' + (g.periode || 'direct') + '|';
  var cle = Object.keys(dernieres).filter(function (k) {
    var lus = k.slice(pref.length).split(',');
    return k.indexOf(pref) === 0 && g.series.every(function (s) { return lus.indexOf(cheminDe(s)) >= 0; });
  })[0];
  return cle ? dernieres[cle] : null;
}
function mini(div, style, g) {
  var d = donneesDe(g);
  if (!d || !window.echarts) return;
  var o = PagesGraphiques.optionDe(Object.assign({}, g, {type: style}), d, {texte: '#666', grille: 'rgba(128,128,128,0.2)'});
  if (o.svg !== undefined) { div.innerHTML = o.svg; return; }
  o.title = {show: false}; o.legend = {show: false}; o.tooltip = {show: false}; o.dataZoom = []; o.animation = false;
  [].concat(o.xAxis || [], o.yAxis || [], o.visualMap || []).forEach(function (a) { a.show = false; });
  [].concat(o.grid || []).forEach(function (gr) { gr.left = gr.right = gr.top = gr.bottom = 2; });
  var c = echarts.init(div, null, {renderer: 'svg'});
  c.setOption(o);
  minis.push(c);
}
function dessineConseil() {
  var r = etat.conseil, g = grapheCourant();
  minis.forEach(function (c) { c.dispose(); });
  minis = [];
  if (!r || !g) return;
  etat.minisPleins = !!donneesDe(g);      // sinon : redessinees a la premiere lecture
  $('resume-styles').textContent = '— ' + g.series.length + ' série(s), ' + $('intention').selectedOptions[0].textContent.toLowerCase();
  $('vignettes').innerHTML = r.proposes.map(function (p, i) {
    return '<div class="vign' + (p.style === g.type ? ' choisie' : '') + '" data-style="' + p.style + '"><span class="rang">' + (i + 1) +
      '</span><div class="nom">' + echappe(NOMS[p.style] || p.style) + '</div><div class="mini"></div><div class="raison">' + echappe(p.raison) + '</div></div>';
  }).join('') || '<div class="petit doux">Aucun style ne convient à ces séries.</div>';
  $('vignettes').querySelectorAll('.vign').forEach(function (v) { mini(v.querySelector('.mini'), v.getAttribute('data-style'), g); });
  $('ecartes').querySelector('summary').textContent = 'Styles écartés (' + r.ecartes.length + ')';
  $('liste-ecartes').innerHTML = r.ecartes.map(function (e) { return '<div><b>' + echappe(NOMS[e.style] || e.style) + '</b> : ' + echappe(e.motif) + '</div>'; }).join('');
}
$('vignettes').addEventListener('click', function (e) {
  var v = e.target.closest('.vign'), g = grapheCourant();
  if (!v || !g) return;
  g.type = v.getAttribute('data-style');
  modifie(true);
});
$('intention').addEventListener('change', demandeConseil);

// ---- validation, diff et ecriture ----
function verifieEtDiff() {
  if (etat.dest === 'graphiques' && attendChoix()) {
    etat.diff = null; dessineCode(); $('motifs').innerHTML = '';
    $('resume').textContent = 'choisir la version de départ de la composition : rien n\'est écrit'; return;
  }
  var sig = JSON.stringify(corpsEcriture()), corps = JSON.parse(sig);     // copie figee : la saisie continue pendant les requetes
  var validation = corps.description ? poste('/valide', {description: corps.description}) : Promise.resolve({motifs: []});
  validation.then(function (r) {
    etat.motifs = r.motifs;
    dessineMotifs();
    if (r.motifs.length) { etat.diff = null; dessineCode(); return; }
    if (sig !== JSON.stringify(corpsEcriture())) return;            // modifiee pendant la validation : un autre passage suit
    return poste('/diff', corps).then(function (d) {
      if (sig !== JSON.stringify(corpsEcriture())) return;          // modifiee pendant le calcul : un autre diff suit
      etat.diff = d; etat.diffSig = sig; dessineCode();
    });
  }).catch(function (e) {
    if (oubliIndex(e)) return;
    etat.diff = null; dessineCode();
    $('motifs').innerHTML = '<div class="avert rouge">Refusé : ' + echappe(e.message) + '</div>';
  });
}
function dessineMotifs() {
  $('motifs').innerHTML = etat.motifs.length ? '<div class="avert rouge"><b>Description refusée :</b><br>' +
    etat.motifs.map(echappe).join('<br>') + '</div>' : '';
}
function ligneDiff(l) {
  var c = /^(\+\+\+|---|@@)/.test(l) ? 'c' : l[0] === '+' ? 'p' : l[0] === '-' ? 'm' : '';
  return c ? '<span class="' + c + '">' + echappe(l) + '</span>' : echappe(l);
}
function dessineCode() {
  var fs = etat.diff ? etat.diff.fichiers : [], o = $('onglets');
  if (!fs.some(function (f) { return f.chemin === etat.onglet; }) && etat.onglet !== '*') etat.onglet = fs.length ? fs[0].chemin : '';
  o.innerHTML = fs.map(function (f) {
    var nom = f.chemin === 'platformio_tasmota_cenv.ini' ? 'cenv' : f.chemin.split('/').pop();
    return '<button data-onglet="' + echappe(f.chemin) + '"' + (f.chemin === etat.onglet || etat.onglet === '*' ? ' class="actif"' : '') + '>' +
      echappe(nom) + ' (+' + f.ajouts + ' −' + f.retraits + ')</button>';
  }).join('') || '<button class="actif">pages_graphiques.json</button>';
  var montres = fs.filter(function (f) { return etat.onglet === '*' || f.chemin === etat.onglet; });
  $('code').innerHTML = montres.length ? montres.map(function (f) { return f.diff.split('\n').map(ligneDiff).join('\n'); }).join('\n\n')
    : echappe(JSON.stringify(etat.desc, null, 1)) + (etat.diff ? '\n\n' + '<span class="c">(le dépôt porte déjà cette description : rien à écrire)</span>' : '');
  $('code').classList.toggle('complet', etat.onglet === '*');
  $('voir-diff').textContent = etat.onglet === '*' ? 'Un fichier à la fois' : 'Voir le diff complet';
  $('resume').textContent = etat.diff ? fs.length + ' fichier(s) à écrire' + (fs.length && etat.diff.signaux.length ? ' · ' + etat.diff.signaux.join(' · ') : '')
    : (etat.motifs.length ? 'description refusée : rien ne peut être écrit' : 'diff en cours…');
  $('ecrire').disabled = !(etat.diff && fs.length && etat.diffSig === JSON.stringify(corpsEcriture()));
}
$('onglets').addEventListener('click', function (e) {
  var c = e.target.getAttribute('data-onglet');
  if (c) { etat.onglet = c; dessineCode(); }
});
$('voir-diff').onclick = function () { etat.onglet = etat.onglet === '*' ? '' : '*'; dessineCode(); };
$('ecrire').onclick = function () {
  var corps = corpsEcriture(), d = etat.diff;
  if (!d || etat.diffSig !== JSON.stringify(corps)) return;
  if (!confirm('Écrire ' + d.fichiers.length + ' fichier(s) dans le dépôt ?\n\n' + d.fichiers.map(function (f) { return f.chemin; }).join('\n'))) return;
  $('ecrire').disabled = true;
  poste('/ecrire', Object.assign({empreinte: d.empreinte}, corps)).then(function (r) {
    message('Écrit : ' + r.ecrits.map(echappe).join(', ') + (d.signaux.length ? '<br>À faire : ' + d.signaux.map(echappe).join(' ; ') : '') +
      '<br>Puis « Envoyer par la page Build ↗ » (onglet Fichiers) pour la carte.', 'vert');
    apresEcriture(r);
  }).catch(function (e) { message('Rien n\'est écrit : ' + echappe(e.message), 'rouge'); verifieEtDiff(); });
};

// ---- orchestration ----
function dessine() { dessineArbre(); dessineReglages(); dessineAlertes(); dessineDestination(); }
function modifie(structure) {
  etat.diff = null; dessineCode();
  if (structure) dessine(); else dessineAlertes();
  actualise();
}
function actualise() {
  clearTimeout(minuterie);
  minuterie = setTimeout(function () { apercu(); demandeConseil(); verifieEtDiff(); }, 300);
}
$('env').addEventListener('change', function () { choisitEnv(this.value); });
$('relire').onclick = function () { litSeries().then(function () { dessine(); actualise(); }); };
$('intention').innerHTML = INTENTIONS.map(function (i) { return '<option value="' + i[0] + '">' + i[1] + '</option>'; }).join('');
bascules();
Promise.all([lis('/envs'), fetch('/moteur/pages_graphiques.html').then(function (r) { return r.text(); })]).then(function (r) {
  etat.envs = r[0].envs; gabarit = r[1];
  $('env').innerHTML = etat.envs.map(function (e) { return '<option>' + echappe(e.nom) + '</option>'; }).join('');
  var voulu = new URLSearchParams(location.search).get('env');
  var env = etat.envs.some(function (e) { return e.nom === voulu; }) ? voulu : (etat.envs[0] || {}).nom;
  if (!env) { message('Aucune carte S3/P4 dans le cenv.', 'rouge'); return; }
  $('env').value = env;
  return choisitEnv(env);
}).catch(function (e) { message('Atelier injoignable : ' + echappe(e.message), 'rouge'); });
"""
JS += JS_SERIES + JS_DEST
