"""JS de l'editeur de formes (atelier des visuels, mode dessin a plat) : logique pure `AV_FORMES` + liaison a `window.AV`.

La partie pure n'a besoin d'aucun DOM (banc `test_atelier_visuels_formes.mjs`) ; la liaison DOM (`atelier_visuels_page_formes_dom_js.py`)
ne s'execute que si `document` existe. Securite : textContent et setAttribute seulement, jamais d'innerHTML ni d'eval ;
ce qui vient de localStorage est revalide (`normalise`).
"""

JS_PUR = r"""
var AV_FORMES = (function () {
  var NS = 'http://www.w3.org/2000/svg', COUL = /^#[0-9a-fA-F]{6}$/, SEUIL = 8;
  // motifs repris des <pattern> de data/sd/js/volets.js (briques, lames) ; tuiles ajoute dans le meme esprit
  var MOTIFS = {
    briques: [16, 8, [['rect', {width: 16, height: 8, fill: '#c9b39c'}], ['rect', {x: 0.5, y: 0.5, width: 15, height: 3.2, fill: '#a5563f'}],
      ['rect', {x: -7.5, y: 4.5, width: 15, height: 3.2, fill: '#9a4c37'}], ['rect', {x: 8.5, y: 4.5, width: 15, height: 3.2, fill: '#ad5d45'}]]],
    tuiles: [12, 8, [['rect', {width: 12, height: 8, fill: '#9c4b3a'}], ['rect', {y: 6, width: 12, height: 2, fill: '#7a3829'}],
      ['rect', {x: 5.5, width: 1, height: 6, fill: '#85402f'}]]],
    lames: [10, 8, [['rect', {width: 10, height: 8, fill: '#9aa3ab'}], ['rect', {y: 6.5, width: 10, height: 1.5, fill: '#6f777e'}]]]
  };
  // taille par defaut et reglages de chaque gabarit
  var GAB = {
    mur: {l: 300, h: 160, motif: 'briques'}, toitMono: {l: 340, h: 40, motif: 'tuiles', pente: 16}, toitDeux: {l: 340, h: 70, motif: 'tuiles'},
    fenetre: {l: 50, h: 70, fill: '#2b2f33', battants: 2}, porte: {l: 50, h: 100, fill: '#f2f2f0'}, porteGarage: {l: 120, h: 100, motif: 'lames'},
    voletRoulant: {l: 50, h: 70, motif: 'lames'}, cheminee: {l: 30, h: 60, motif: 'briques'}, boite: {l: 16, h: 12, fill: '#3a5a8a'},
    numero: {l: 30, h: 20, fill: '#222222', texte: '12'}
  };
  function own(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
  function num(v, d) { return typeof v === 'number' && isFinite(v) ? v : d; }
  function r1(v) { return Math.round(v * 10) / 10; }
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function fusion(a, b) { var k; for (k in b) a[k] = b[k]; return a; }

  // noeud = [balise, attributs, enfants | texte] ; deux rendus : chaine (AV.svg) et DOM (editeur)
  function ser(n) {
    var s = '<' + n[0], k, a = n[1] || {}, c = n[2];
    for (k in a) s += ' ' + k + '="' + esc(a[k]) + '"';
    if (c === undefined) return s + '/>';
    return s + '>' + (typeof c === 'string' ? esc(c) : c.map(ser).join('')) + '</' + n[0] + '>';
  }
  function bati(n, doc) {
    var e = doc.createElementNS(NS, n[0]), k;
    for (k in n[1]) e.setAttribute(k, n[1][k]);
    if (typeof n[2] === 'string') e.textContent = n[2];
    else if (n[2]) n[2].forEach(function (f) { e.appendChild(bati(f, doc)); });
    return e;
  }

  // ---- geometrie
  function bbox(f) {
    if (f.type !== 'polygon') return {x: f.x, y: f.y, l: f.l, h: f.h};
    var xs = f.points.map(function (p) { return p[0]; }), ys = f.points.map(function (p) { return p[1]; });
    var x = Math.min.apply(null, xs), y = Math.min.apply(null, ys);
    return {x: x, y: y, l: Math.max.apply(null, xs) - x, h: Math.max.apply(null, ys) - y};
  }
  function dansPoly(x, y, pts) {
    var dedans = false, i, j;
    for (i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      if ((pts[i][1] > y) !== (pts[j][1] > y) && x < (pts[j][0] - pts[i][0]) * (y - pts[i][1]) / (pts[j][1] - pts[i][1]) + pts[i][0]) dedans = !dedans;
    }
    return dedans;
  }
  function deplace(f, dx, dy) {
    if (f.type === 'polygon') f.points = f.points.map(function (p) { return [p[0] + dx, p[1] + dy]; });
    else { f.x += dx; f.y += dy; }
  }
  // poignee 'nw'...'w' (forme rectangulaire) ou 'p<i>' (sommet d'un polygone) amenee en (px, py)
  function redim(f, hn, px, py) {
    if (f.type === 'polygon') { f.points[+hn.slice(1)] = [px, py]; return; }
    var x0 = f.x, x1 = f.x + f.l, y0 = f.y, y1 = f.y + f.h;
    if (hn.indexOf('w') >= 0) x0 = px;
    if (hn.indexOf('e') >= 0) x1 = px;
    if (hn.indexOf('n') >= 0) y0 = py;
    if (hn.indexOf('s') >= 0) y1 = py;
    f.x = Math.min(x0, x1); f.y = Math.min(y0, y1); f.l = Math.max(4, Math.abs(x1 - x0)); f.h = Math.max(4, Math.abs(y1 - y0));
  }
  function aimante(v, cibles, seuil) {
    var m = v, d = (seuil === undefined ? SEUIL : seuil) + 1e-9, i;
    for (i = 0; i < cibles.length; i++) if (Math.abs(cibles[i] - v) < d) { d = Math.abs(cibles[i] - v); m = cibles[i]; }
    return m;
  }
  // bord gauche/haut v d'une forme de longueur l : aimante celui des deux bords qui tombe le plus pres d'une cible
  function aimanteBord(v, l, cibles, seuil) {
    var a = aimante(v, cibles, seuil), b = aimante(v + l, cibles, seuil) - l;
    if (a === v && b === v) return v;
    if (a === v) return b;
    if (b === v) return a;
    return Math.abs(a - v) <= Math.abs(b - v) ? a : b;
  }
  function cibles(formes, sauf, larg, haut) {
    var c = {xs: [0, larg], ys: [0, haut]};
    formes.forEach(function (f) {
      if (f.id === sauf || f.zone) return;
      var b = bbox(f);
      c.xs.push(b.x, b.x + b.l); c.ys.push(b.y, b.y + b.h);
    });
    return c;
  }

  // ---- couleur mediane de la zone de photo recouverte (img = ImageData : data, width, height)
  function mediane(img, f) {
    var b = bbox(f), x0 = Math.max(0, Math.floor(b.x)), y0 = Math.max(0, Math.floor(b.y)), x1 = Math.min(img.width, Math.ceil(b.x + b.l)),
        y1 = Math.min(img.height, Math.ceil(b.y + b.h)), pas = Math.max(1, Math.floor(Math.sqrt(Math.max(1, (x1 - x0) * (y1 - y0)) / 2500))),
        c = [[], [], []], x, y, i, k;
    for (y = y0; y < y1; y += pas) for (x = x0; x < x1; x += pas) {
      if (f.type === 'polygon' && !dansPoly(x + 0.5, y + 0.5, f.points)) continue;
      i = (y * img.width + x) * 4;
      if (img.data[i + 3] < 8) continue;
      for (k = 0; k < 3; k++) c[k].push(img.data[i + k]);
    }
    if (!c[0].length) return null;
    return '#' + c.map(function (t) {
      t.sort(function (a, z) { return a - z; });
      return ('0' + t[Math.floor(t.length / 2)].toString(16)).slice(-2);
    }).join('');
  }

  // ---- historique : pile d'etats (chaines), l'etat courant est le dernier
  function historique(max, initial) {
    var pile = [initial], futur = [];
    return {
      pousse: function (s) { if (s === pile[pile.length - 1]) return false; pile.push(s); futur = []; if (pile.length > max + 1) pile.shift(); return true; },
      annule: function () { if (pile.length < 2) return null; futur.push(pile.pop()); return pile[pile.length - 1]; },
      retablit: function () { if (!futur.length) return null; var s = futur.pop(); pile.push(s); return s; },
      profondeur: function () { return pile.length - 1; }
    };
  }

  // ---- forme valide (a la creation et au rechargement du localStorage)
  function normalise(f) {
    try {
      if (!f || typeof f !== 'object' || (f.type !== 'rect' && f.type !== 'polygon' && f.type !== 'gabarit')) return null;
      var o = {id: num(f.id, 0), type: f.type, fill: COUL.test(f.fill) ? f.fill : '#888888', motif: own(MOTIFS, f.motif) ? f.motif : null,
               stroke: COUL.test(f.stroke) ? f.stroke : null, sw: Math.min(20, Math.max(0, num(f.sw, 0))),
               zone: f.zone === 'effacer' || f.zone === 'garder' ? f.zone : null};
      if (f.type === 'polygon') {
        if (!Array.isArray(f.points) || f.points.length < 3 || f.points.length > 200) return null;
        o.points = f.points.map(function (p) { return [num(p[0], 0), num(p[1], 0)]; });
      } else {
        o.x = num(f.x, 0); o.y = num(f.y, 0); o.l = Math.max(4, num(f.l, 4)); o.h = Math.max(4, num(f.h, 4));
      }
      if (f.type === 'gabarit') {
        if (typeof f.gabarit !== 'string' || !own(GAB, f.gabarit)) return null;
        o.gabarit = f.gabarit; o.pente = num(f.pente, 0); o.battants = f.battants == 1 ? 1 : 2; o.texte = String(f.texte === undefined ? '' : f.texte).slice(0, 8);
      }
      return o;
    } catch (e) { return null; }
  }
  function nouveauGabarit(nom, x, y, id) {
    var g = GAB[nom];
    return normalise({id: id, type: 'gabarit', gabarit: nom, x: x, y: y, l: g.l, h: g.h, fill: g.fill || '#888888', motif: g.motif || null,
                      pente: g.pente || 0, battants: g.battants || 2, texte: g.texte || ''});
  }

  // ---- dessin : noeuds d'une forme
  function fillOf(f) { return f.motif ? 'url(#avm_' + f.motif + ')' : f.fill; }
  function trait(f) { return f.stroke && f.sw > 0 ? {stroke: f.stroke, 'stroke-width': r1(f.sw)} : {}; }
  function R(x, y, w, h, extra) { return ['rect', fusion({x: r1(x), y: r1(y), width: r1(w), height: r1(h)}, extra)]; }
  function pts(p) { return p.map(function (q) { return r1(q[0]) + ',' + r1(q[1]); }).join(' '); }
  function prims(f) {
    var x = f.x, y = f.y, l = f.l, h = f.h, F = fillOf(f), T = trait(f), g = f.gabarit, p, o = [];
    if (f.type === 'polygon') return [['polygon', fusion({points: pts(f.points), fill: F}, T)]];
    if (f.type === 'rect' || g === 'mur') return [R(x, y, l, h, fusion({fill: F}, T))];
    if (g === 'toitMono') {
      p = Math.max(-h, Math.min(h, f.pente));
      return [['polygon', fusion({points: pts(p >= 0 ? [[x, y + p], [x + l, y], [x + l, y + h], [x, y + h]] : [[x, y], [x + l, y - p], [x + l, y + h], [x, y + h]]), fill: F}, T)]];
    }
    if (g === 'toitDeux') return [['polygon', fusion({points: pts([[x, y + h], [x + l / 2, y], [x + l, y + h]]), fill: F}, T)]];
    if (g === 'fenetre') {
      o.push(R(x, y, l, h, {fill: F, stroke: '#ffffff', 'stroke-width': 3}));
      if (f.battants === 2) o.push(['line', {x1: r1(x + l / 2), y1: r1(y), x2: r1(x + l / 2), y2: r1(y + h), stroke: '#ffffff', 'stroke-width': 2}]);
      return o;
    }
    if (g === 'porte') {
      return [R(x, y, l, h, {fill: F, stroke: '#c8c8c4', 'stroke-width': 2}), R(x + l * 0.12, y + h * 0.06, l * 0.76, h * 0.55, {fill: '#2b2f33', stroke: '#dddddd', 'stroke-width': 1.5}),
              R(x + l * 0.84, y + h * 0.5, 2.5, 12, {fill: '#9a9a9a', rx: 1})];
    }
    if (g === 'porteGarage') return [R(x, y, l, h, {fill: F, stroke: '#6f777e', 'stroke-width': 2})];
    if (g === 'voletRoulant') return [R(x, y, l, h, {fill: F, stroke: '#6f777e', 'stroke-width': 1}), R(x - 2, y - h * 0.12, l + 4, h * 0.14, {fill: '#6f777e'})];
    if (g === 'cheminee') return [R(x, y, l, h, {fill: F}), R(x - 3, y - 4, l + 6, 5, {fill: '#6b6b6b'})];
    if (g === 'boite') return [R(x, y, l, h, {fill: F, stroke: '#ffffff', 'stroke-width': 1}), ['line', {x1: r1(x + 2), y1: r1(y + h * 0.4), x2: r1(x + l - 2), y2: r1(y + h * 0.4), stroke: '#ffffff', 'stroke-width': 1}]];
    return [['text', {x: r1(x + l / 2), y: r1(y + h * 0.8), 'font-size': r1(h * 0.8), 'font-family': 'sans-serif', 'text-anchor': 'middle', fill: F}, f.texte]];
  }
  function defs(formes) {
    var vus = {}, d = [];
    formes.forEach(function (f) { if (f.motif) vus[f.motif] = 1; });
    Object.keys(vus).forEach(function (m) {
      d.push(['pattern', {id: 'avm_' + m, width: MOTIFS[m][0], height: MOTIFS[m][1], patternUnits: 'userSpaceOnUse'}, MOTIFS[m][2]]);
    });
    return d.length ? [['defs', {}, d]] : [];
  }
  // SVG propre : zones exclues, rien d'autre que formes et motifs
  function svgDe(formes, larg, haut) {
    var u = formes.filter(function (f) { return !f.zone; }), n = defs(u), s = '<svg xmlns="' + NS + '" viewBox="0 0 ' + larg + ' ' + haut + '" width="' + larg + '" height="' + haut + '">';
    u.forEach(function (f) { n = n.concat(prims(f)); });
    return s + n.map(ser).join('') + '</svg>';
  }
  return {GAB: GAB, MOTIFS: MOTIFS, SEUIL: SEUIL, ser: ser, bati: bati, bbox: bbox, dansPoly: dansPoly, deplace: deplace, redim: redim, aimante: aimante,
          aimanteBord: aimanteBord, cibles: cibles, mediane: mediane, historique: historique, normalise: normalise, nouveauGabarit: nouveauGabarit,
          prims: prims, defs: defs, svgDe: svgDe, fillOf: fillOf};
})();

// ---- partie AV (sans DOM) : formes, selection, historique, sauvegarde par carte, AV.svg()
(function () {
  var AV = (typeof window !== 'undefined') && window.AV, F = AV_FORMES, hist, ecouteurs = [];
  if (!AV) return;
  AV.formes = []; AV.selection = null;
  function cle() { return 'av.formes.' + (AV.carte || 'defaut'); }
  function instantane() { return JSON.stringify(AV.formes); }
  function restaure(s) {
    var t; try { t = JSON.parse(s); } catch (e) { t = []; }
    AV.formes = (Array.isArray(t) ? t : []).map(F.normalise).filter(Boolean);
    if (!AV.formes.some(function (f) { return f.id === AV.selection; })) AV.selection = null;
  }
  function sauve() { try { localStorage.setItem(cle(), instantane()); } catch (e) { /* stockage indisponible : le dessin reste en memoire */ } }
  function change() { sauve(); ecouteurs.forEach(function (fn) { fn(); }); if (AV.dessine) AV.dessine(); }
  AV.surFormes = function (fn) { ecouteurs.push(fn); };
  AV.commit = function () { if (hist.pousse(instantane())) change(); else if (AV.dessine) AV.dessine(); };
  AV.annule = function () { var s = hist.annule(); if (s !== null) { restaure(s); change(); } };
  AV.retablit = function () { var s = hist.retablit(); if (s !== null) { restaure(s); change(); } };
  AV.cherche = function (id) { return AV.formes.filter(function (f) { return f.id === id; })[0] || null; };
  AV.idSuivant = function () { return AV.formes.reduce(function (m, f) { return Math.max(m, f.id); }, 0) + 1; };
  AV.zones = function (type) { return AV.formes.filter(function (f) { return f.zone === type; }); };
  AV.svg = function () { return F.svgDe(AV.formes, AV.larg, AV.haut); };
  AV.poids = function () { return AV.svg().length; };
  // a rappeler quand AV.carte change : relit le dessin de cette carte
  AV.charge = function () {
    try { restaure(localStorage.getItem(cle()) || '[]'); } catch (e) { AV.formes = []; }
    hist = F.historique(100, instantane());
    if (AV.dessine) AV.dessine();
  };
  AV.charge();
})();
"""
