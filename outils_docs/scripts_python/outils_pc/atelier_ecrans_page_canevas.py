"""JS de la page de l'atelier des ecrans : dessin de l'ecran, gestes, palette, zoom, clavier, demarrage.

Utilise l'etat et les fonctions de atelier_ecrans_page_js.py (E, el, vide, modifie, choisi, apercu...). Le dessin est un
apercu du navigateur (polices .ttf du depot par FontFace) ; les valeurs liees sont les exemples du modele de l'ecran.
Coordonnees : celles de l'ecran de la carte ; la souris est divisee par le zoom, aimantee a 8 px (grille), bornee a l'ecran.
"""

JS = r"""
/* ---------- dessin ---------- */
function dims() {
  var e = E.catalogue && E.catalogue.ecrans[E.ecran || (E.desc && E.desc.ecran)];
  return e ? { l: e.largeur, h: e.hauteur } : { l: 1024, h: 600 };
}
function couleur(v, defaut) { return typeof v === 'string' && /^#[0-9A-Fa-f]{6}$/.test(v) ? v : defaut; }
function formate(fmt, n) {
  return String(fmt).replace(/%(?:\.(\d+))?([dfs])/, function (_, p, t) {
    return t === 'd' ? String(Math.round(n)) : t === 'f' ? n.toFixed(p === undefined ? 6 : +p) : String(n);
  });
}
function valeurLiee(o) {
  var l = o.liaison; if (!l || !l.cle || l.attribut === 'series') return undefined;
  var m = (E.desc.modele || []).filter(function (x) { return x.cle === l.cle; })[0];
  if (!m || m.exemple === undefined || m.exemple === null) return undefined;
  var v = m.exemple;
  if (l.table) return ((E.desc.couleurs || {})[l.table] || {})[v];
  if (l.format && !isNaN(Number(v))) v = formate(l.format, Number(v) / (l.echelle || 1));
  return v;
}
function attributsVus(o) {
  var a = Object.assign({}, o.attributs || {}), v = valeurLiee(o);
  if (v !== undefined) a[o.liaison.attribut] = v;
  if (o.actif && o.toucher && o.toucher.page === E.page) Object.assign(a, o.actif);
  return a;
}
function famille(v) {
  var p = lisPolice(v), nom = p ? p.nom : 'robotocondensed';
  if (nom === 'robotocondensed') return '"RobotoCondensed-Regular","Roboto Condensed","Arial Narrow",sans-serif';
  if (nom === 'montserrat') return 'Montserrat,Arial,sans-serif';
  if (nom === 'seg7') return '"DSEG7 Classic",Consolas,monospace';
  return '"' + String(nom).replace(/["\\]/g, '') + '",sans-serif';
}
function taillePolice(v) { var p = lisPolice(v); return p ? p.taille : 14; }
function pourcent(a) {
  var mi = Number(a.min || 0), ma = Number(a.max === undefined ? 100 : a.max), v = Number(a.val || 0);
  return ma > mi ? Math.max(0, Math.min(100, (v - mi) * 100 / (ma - mi))) : 0;
}
function dessineObjet(o, commun) {
  var a = attributsVus(o), d = el('div', { class: 'o t-' + o.type + (commun ? ' commun' : ''), 'data-page': o.page, 'data-id': o.id });
  var s = d.style;
  s.left = o.x + 'px'; s.top = o.y + 'px'; s.width = o.l + 'px'; s.height = o.h + 'px';
  s.borderRadius = (a.radius || 0) + 'px';
  if (a.border_width) s.border = a.border_width + 'px solid ' + couleur(a.border_color, '#888888');
  s.color = couleur(a.text_color, '#FFFFFF');
  s.fontFamily = famille(a.text_font); s.fontSize = taillePolice(a.text_font) + 'px';
  if (o.type === 'btn' || o.type === 'obj') s.background = couleur(a.bg_color, o.type === 'btn' ? '#2196F3' : '#FFFFFF');
  else if (a.bg_color) s.background = couleur(a.bg_color, 'transparent');
  if (o.type === 'label') { s.textAlign = ['left', 'center', 'right'][a.align] || 'left'; d.textContent = a.text === undefined ? '' : String(a.text); }
  if (o.type === 'btn') { s.display = 'flex'; s.alignItems = 'center'; s.justifyContent = 'center'; d.textContent = a.text === undefined ? '' : String(a.text); }
  if (o.type === 'bar' || o.type === 'slider') {
    if (!a.bg_color) s.background = '#555555';
    var i = el('div', { class: 'indic' });
    i.style.width = pourcent(a) + '%'; i.style.background = couleur(a.bg_color10, '#2196F3'); i.style.borderRadius = (a.radius10 || 0) + 'px';
    d.appendChild(i);
  }
  if (o.type === 'arc') {
    s.borderRadius = '50%'; s.background = 'conic-gradient(from 225deg,' + couleur(a.arc_color, '#2196F3') + ' 0 '
      + (pourcent(a) * 2.7) + 'deg,' + couleur(a.bg_color, '#555555') + ' 0 270deg,transparent 0)';
  }
  if (o.type === 'chart') {
    if (!a.bg_color) s.background = '#202020';
    var n = Number(a.h_div_line_count || 0);
    for (var k = 1; k <= n; k++) { var g = el('div', { class: 'ligneDiv' }); g.style.top = (k * o.h / (n + 1)) + 'px'; g.style.background = couleur(a.line_color, '#444444'); d.appendChild(g); }
    var NS = 'http://www.w3.org/2000/svg', svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('width', o.l); svg.setAttribute('height', o.h); svg.style.position = 'absolute'; svg.style.left = '0'; svg.style.top = '0';
    ['#3FA7FF', '#3FD08A', '#FFA53F'].forEach(function (c, j) {
      var pts = [];
      for (var x = 0; x <= o.l; x += 16) pts.push(x + ',' + (o.h * (0.3 + 0.2 * j) + Math.sin(x / 50 + j) * o.h * 0.08).toFixed(1));
      var pl = document.createElementNS(NS, 'polyline');
      pl.setAttribute('points', pts.join(' ')); pl.setAttribute('fill', 'none'); pl.setAttribute('stroke', c); pl.setAttribute('stroke-width', '3');
      svg.appendChild(pl);
    });
    d.appendChild(svg);
  }
  return d;
}
function dessineEcran() {
  var D = dims(), ec = vide($('ecranCarte')), cadre = $('cadre');
  cadre.style.width = Math.round(D.l * E.zoom) + 'px'; cadre.style.height = Math.round(D.h * E.zoom) + 'px';
  ec.style.width = D.l + 'px'; ec.style.height = D.h + 'px'; ec.style.transform = 'scale(' + E.zoom + ')';
  ec.classList.toggle('grille', $('grille').checked);
  var pg = pageDesc(E.page === 0 ? 1 : E.page);
  ec.style.backgroundColor = couleur(pg && pg.attributs && pg.attributs.bg_color, '#000000');
  $('zoom').textContent = Math.round(E.zoom * 100) + ' %';
  objets(E.page).forEach(function (o) { ec.appendChild(dessineObjet(o, false)); });
  if (E.page !== 0) objets(0).forEach(function (o) { ec.appendChild(dessineObjet(o, true)); });   // layer_top
  dessineEpingles(ec);
  var o = choisi();
  if (!o || o.page !== E.page) return;
  var vu = ec.querySelector('.o[data-page="' + o.page + '"][data-id="' + o.id + '"]');
  if (vu) vu.classList.add('sel');
  [['nw', 0, 0], ['ne', 1, 0], ['sw', 0, 1], ['se', 1, 1]].forEach(function (c) {
    var p = el('div', { class: 'poi', 'data-coin': c[0], 'data-page': o.page, 'data-id': o.id });
    p.style.left = (o.x + c[1] * o.l - 6) + 'px'; p.style.top = (o.y + c[2] * o.h - 6) + 'px';
    p.style.cursor = c[0] + '-resize';
    ec.appendChild(p);
  });
}
function borne(o) {
  var D = dims();
  o.l = Math.max(4, Math.min(o.l, D.l)); o.h = Math.max(4, Math.min(o.h, D.h));
  o.x = Math.max(0, Math.min(o.x, D.l - o.l)); o.y = Math.max(0, Math.min(o.y, D.h - o.h));
}

/* ---------- zoom ---------- */
function zoomAjuste() {
  var w = $('vueEcran').clientWidth - 40;
  E.zoom = w > 0 ? Math.max(0.2, Math.min(1, Math.floor(w / dims().l * 20) / 20)) : 1;
}
function zoome(f) { E.zoom = Math.max(0.2, Math.min(3, Math.round(E.zoom * f * 20) / 20)); dessineEcran(); }

/* ---------- palette et ajout ---------- */
var NOMS_TYPES = { label: 'Libellé', btn: 'Bouton', bar: 'Barre', arc: 'Arc', chart: 'Courbe', slider: 'Curseur', obj: 'Cadre' };
var DEFAUTS = {
  label: [160, 32, { text: 'Texte', text_font: 24, text_color: '#E8EDF2' }],
  btn: [120, 46, { text: 'Bouton', text_font: 24, radius: 23, border_width: 0, bg_color: '#1F2B38', text_color: '#E8EDF2' }],
  bar: [300, 26, { min: 0, max: 100, val: 50, radius: 13, bg_color: '#1F2B38', bg_color10: '#3FA7FF', radius10: 13 }],
  slider: [300, 20, { min: 0, max: 100, val: 50 }],
  arc: [120, 120, { min: 0, max: 100, val: 50 }],
  chart: [400, 240, { point_count: 60, y_min: 0, y_max: 100, h_div_line_count: 4 }],
  obj: [100, 100, { radius: 8, border_width: 0, bg_color: '#1F2B38' }]
};
function nouvelId(page) {
  var pris = objets(page).map(function (o) { return o.id; }), max = pris.reduce(function (m, i) { return Math.max(m, i); }, 0);
  for (var i = max + 1; i <= 254; i++) if (pris.indexOf(i) < 0) return i;
  for (i = 1; i <= 254; i++) if (pris.indexOf(i) < 0) return i;
  return null;
}
function ajouteObjet(type, x, y) {
  if (lecture()) return;
  var id = nouvelId(E.page);
  if (id === null) { alert('Page ' + E.page + ' pleine : 254 objets au plus.'); return; }
  var d = DEFAUTS[type] || [100, 40, {}], attrs = {};
  Object.keys(d[2]).forEach(function (k) { if (typeAttr(type, k)) attrs[k] = d[2][k]; });   // seulement ce que le catalogue connait
  modifie(function () {
    var o = { id: id, page: E.page, type: type, x: x, y: y, l: d[0], h: d[1], attributs: attrs };
    borne(o); E.desc.objets.push(o); E.sel = [E.page, id];
  });
}
function dessinePalette() {
  var pa = vide($('palette'));
  Object.keys(E.catalogue.objets).filter(function (t) { return E.catalogue.objets[t].palier === 1; }).forEach(function (t) {
    var d = el('div', { draggable: 'true', tabindex: '0', role: 'button', title: 'Glisser sur l’écran, ou cliquer pour ajouter' });
    d.appendChild(el('span', null, NOMS_TYPES[t] || t)); d.appendChild(el('span', { class: 'doux' }, t));
    d.ondragstart = function (ev) { ev.dataTransfer.setData('text/plain', t); ev.dataTransfer.effectAllowed = 'copy'; };
    d.onclick = function () { ajouteObjet(t, 16, 16); };
    d.onkeydown = function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); ajouteObjet(t, 16, 16); } };
    pa.appendChild(d);
  });
}

/* ---------- gestes sur l'ecran ---------- */
var geste = null;
function pointEcran(ev) { var r = $('ecranCarte').getBoundingClientRect(); return { x: (ev.clientX - r.left) / E.zoom, y: (ev.clientY - r.top) / E.zoom }; }
function aimante(v) { return $('grille').checked ? Math.round(v / 8) * 8 : Math.round(v); }
function brancheEcran() {
  var ec = $('ecranCarte');
  ec.addEventListener('pointerdown', function (ev) {
    if (ev.button !== 0) return;
    var poi = ev.target.closest('.poi'), cible = poi || ev.target.closest('.o');
    if (!cible) { if (E.sel) { E.sel = null; dessineTout(); } return; }
    var page = +cible.getAttribute('data-page'), id = +cible.getAttribute('data-id');
    if (!(E.sel && E.sel[0] === page && E.sel[1] === id)) { E.sel = [page, id]; dessineTout(); }
    var o = choisi(); if (!o || lecture()) return;
    geste = { coin: poi ? poi.getAttribute('data-coin') : '', p0: pointEcran(ev), x: o.x, y: o.y, l: o.l, h: o.h, avant: JSON.stringify(E.desc) };
    ec.setPointerCapture(ev.pointerId); ev.preventDefault();
  });
  ec.addEventListener('pointermove', function (ev) {
    var p = pointEcran(ev);
    $('coords').textContent = 'x ' + Math.round(p.x) + ' · y ' + Math.round(p.y);
    var o = geste && choisi(); if (!o) return;
    var dx = p.x - geste.p0.x, dy = p.y - geste.p0.y, x2 = geste.x + geste.l, y2 = geste.y + geste.h;
    if (!geste.coin) { o.x = aimante(geste.x + dx); o.y = aimante(geste.y + dy); }
    else {
      if (geste.coin.indexOf('w') >= 0) { o.x = Math.min(aimante(geste.x + dx), x2 - 4); o.l = x2 - o.x; } else o.l = Math.max(4, aimante(x2 + dx) - o.x);
      if (geste.coin.indexOf('n') >= 0) { o.y = Math.min(aimante(geste.y + dy), y2 - 4); o.h = y2 - o.y; } else o.h = Math.max(4, aimante(y2 + dy) - o.y);
    }
    borne(o); dessineEcran();
  });
  var fin = function () {
    if (!geste) return;
    var avant = geste.avant; geste = null;
    if (JSON.stringify(E.desc) === avant) return;
    E.histo.push(avant); if (E.histo.length > 100) E.histo.shift(); E.futur = [];
    dessineTout(); apercu();
  };
  ec.addEventListener('pointerup', fin); ec.addEventListener('pointercancel', fin);
  ec.addEventListener('dragover', function (ev) { ev.preventDefault(); ev.dataTransfer.dropEffect = 'copy'; });
  ec.addEventListener('drop', function (ev) {
    ev.preventDefault();
    var t = ev.dataTransfer.getData('text/plain');
    var c = Object.prototype.hasOwnProperty.call(E.catalogue.objets, t) && E.catalogue.objets[t];   // texte glisse : externe
    if (!c || c.palier !== 1) return;
    var p = pointEcran(ev); ajouteObjet(t, aimante(p.x), aimante(p.y));
  });
}
document.addEventListener('keydown', function (ev) {
  if (/^(INPUT|SELECT|TEXTAREA)$/.test(ev.target.tagName)) return;
  var k = ev.key.toLowerCase();
  if ((ev.ctrlKey || ev.metaKey) && k === 'z' && !ev.shiftKey) { ev.preventDefault(); deplaceHisto(E.histo, E.futur); return; }
  if ((ev.ctrlKey || ev.metaKey) && (k === 'y' || (k === 'z' && ev.shiftKey))) { ev.preventDefault(); deplaceHisto(E.futur, E.histo); return; }
  if (!choisi()) return;
  if (ev.key === 'Delete') { ev.preventDefault(); supprimeChoisi(); return; }
  var pas = ev.shiftKey ? 8 : 1, dep = { arrowleft: [-pas, 0], arrowright: [pas, 0], arrowup: [0, -pas], arrowdown: [0, pas] }[k];
  if (dep) { ev.preventDefault(); modifie(function () { var c = choisi(); c.x += dep[0]; c.y += dep[1]; borne(c); }); }
});

/* ---------- demarrage ---------- */
function themeBouton() { $('theme').textContent = document.documentElement.getAttribute('data-theme') === 'sombre' ? '☀ Clair' : '☾ Sombre'; }
function demarre() {
  themeBouton();
  $('theme').onclick = function () {
    var t = document.documentElement.getAttribute('data-theme') === 'sombre' ? 'clair' : 'sombre';
    document.documentElement.setAttribute('data-theme', t); themeBouton();
    try { localStorage.setItem('atelier-ecrans-theme', t); } catch (e) {}
  };
  Array.prototype.forEach.call(document.querySelectorAll('#vues button'), function (b) {
    b.onclick = function () {
      Array.prototype.forEach.call(document.querySelectorAll('#vues button'), function (x) { x.classList.toggle('actif', x === b); });
      $('vueEcran').hidden = b.getAttribute('data-vue') !== 'ecran'; $('vueTableau').hidden = b.getAttribute('data-vue') !== 'tableau';
    };
  });
  Array.prototype.forEach.call(document.querySelectorAll('#panneaux button'), function (b) {
    b.onclick = function () {
      Array.prototype.forEach.call(document.querySelectorAll('#panneaux button'), function (x) { x.classList.toggle('actif', x === b); });
      ['proprietes', 'liaison', 'remarques'].forEach(function (id) { $(id).hidden = b.getAttribute('data-panneau') !== id; });
    };
  });
  $('zoomMoins').onclick = function () { zoome(1 / 1.25); };
  $('zoomPlus').onclick = function () { zoome(1.25); };
  $('zoom100').onclick = function () { E.zoom = 1; dessineEcran(); };
  $('grille').onchange = dessineEcran;
  $('annuler').onclick = function () { deplaceHisto(E.histo, E.futur); };
  $('retablir').onclick = function () { deplaceHisto(E.futur, E.histo); };
  $('ajoutPage').onclick = ajoutePage;
  $('relire').onclick = lisCarte;
  $('capture').onclick = capture;
  $('ecrire').onclick = prepareEcriture;
  $('carte').onchange = function () { chargeCarte($('carte').value); };
  $('ecran').onchange = function () { choisitEcran($('ecran').value); };
  brancheEcran();
  Promise.all([requete('GET', '/cartes'), requete('GET', '/catalogue')]).then(function (r) {
    E.cartes = r[0].cartes; E.lieux = r[0].lieux; E.catalogue = r[1];
    polices().forEach(function (p) {
      if (p.source !== 'sd' || !window.FontFace) return;
      try { var f = new FontFace(p.nom, 'url("/police?nom=' + encodeURIComponent(p.nom) + '")'); document.fonts.add(f); f.load().then(function () { if (E.desc) dessineEcran(); }, function () {}); } catch (e) {}
    });
    dessinePalette();
    var demande = new URLSearchParams(location.search).get('env');
    var parDefaut = E.cartes.filter(function (c) { return c.description; })[0];
    remplitParLieu($('carte'), E.cartes, E.lieux, demande || (parDefaut && parDefaut.nom));
    if ($('carte').value) chargeCarte($('carte').value); else bandeau('Aucune carte dans le cenv.');
  }).catch(function (e) { bandeau('Chargement impossible : ' + e.message); });
}
demarre();
"""
