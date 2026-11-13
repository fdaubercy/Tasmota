"""Liaison DOM de l'editeur de formes : canevas SVG d'edition, outils, poignees, palette et panneau de l'element selectionne.

Le canevas est cree dans l'element `#av-canevas` de la page (a defaut, dans `<body>`). Rien de ce qui vient de l'utilisateur
n'entre dans le DOM autrement que par setAttribute / textContent / value.
"""

JS_DOM = r"""
(function () {
  var AV = (typeof window !== 'undefined') && window.AV, F = AV_FORMES, NS = 'http://www.w3.org/2000/svg';
  if (!AV || typeof document === 'undefined') return;
  var S = {outil: 'sel', zone: null, temp: null, poly: null, souris: null, drag: null, urlPhoto: null, img: null}, svg, gFond, gFormes, gSur;
  var POIGNEES = {nw: [0, 0], n: [0.5, 0], ne: [1, 0], e: [1, 0.5], se: [1, 1], s: [0.5, 1], sw: [0, 1], w: [0, 0.5]};
  function $(id) { return document.getElementById('avf-' + id); }
  function noeud(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag), k;
    for (k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function vide(e) { while (e.firstChild) e.removeChild(e.firstChild); }

  // ---- photo : copie en data-URI et pixels, relues a chaque changement de photo
  function urlPhoto() {
    if (!AV.photo) return null;
    if (!S.urlPhoto) { try { S.urlPhoto = AV.photo.toDataURL('image/jpeg', 0.7); } catch (e) { S.urlPhoto = null; } }
    return S.urlPhoto;
  }
  function pixels() {
    if (!AV.photo) return null;
    if (!S.img) { try { S.img = AV.photo.getContext('2d').getImageData(0, 0, AV.photo.width, AV.photo.height); } catch (e) { S.img = null; } }
    return S.img;
  }
  function couleurPhoto(f) { var im = pixels(); return im ? F.mediane(im, f) : null; }

  // ---- dessin du canevas
  function construit() {
    var cont = document.getElementById('av-canevas') || document.body;
    svg = noeud('svg', {id: 'avf-canevas', 'class': 'avf-canevas'}, cont);
    gFond = noeud('g', {}, svg); gFormes = noeud('g', {}, svg); gSur = noeud('g', {}, svg);
    svg.addEventListener('pointerdown', bas); svg.addEventListener('pointermove', bouge); svg.addEventListener('pointerup', haut);
    svg.addEventListener('dblclick', ferme);
  }
  function zoneVisuel(f, el) {
    var c = f.zone === 'effacer' ? '#d93025' : '#1e8e3e';
    el.setAttribute('fill', c); el.setAttribute('fill-opacity', 0.25); el.setAttribute('stroke', c); el.setAttribute('stroke-dasharray', '6 4');
  }
  AV.dessine = function () {
    if (!svg) construit();
    svg.setAttribute('viewBox', '0 0 ' + AV.larg + ' ' + AV.haut);
    vide(gFond); vide(gFormes); vide(gSur);
    var u = urlPhoto(), op = $('opacite') ? +$('opacite').value : 0.4;
    if (u) noeud('image', {href: u, x: 0, y: 0, width: AV.larg, height: AV.haut, opacity: op, 'pointer-events': 'none'}, gFond);
    var tous = AV.formes.concat(S.temp ? [S.temp] : []);
    F.defs(tous.filter(function (f) { return !f.zone; })).forEach(function (n) { gFormes.appendChild(F.bati(n, document)); });
    tous.forEach(function (f) {
      var g = noeud('g', {}, gFormes);
      g.setAttribute('data-id', f.id);
      if (f.zone) {
        var b = F.bbox(f), z = f.type === 'polygon' ? noeud('polygon', {points: f.points.join(' ')}, g) : noeud('rect', {x: b.x, y: b.y, width: b.l, height: b.h}, g);
        zoneVisuel(f, z);
      } else F.prims(f).forEach(function (n) { g.appendChild(F.bati(n, document)); });
    });
    poignees();
    if (S.poly) {
      var p = S.poly.concat(S.souris ? [S.souris] : []);
      noeud('polyline', {points: p.join(' '), fill: 'none', stroke: '#1a73e8', 'stroke-width': 1.5, 'stroke-dasharray': '4 3', 'pointer-events': 'none'}, gSur);
    }
    panneau();
    var po = $('poids'); if (po) po.textContent = (AV.poids() / 1024).toFixed(1) + ' Ko';
  };
  function poignees() {
    var f = AV.cherche(AV.selection), b, k;
    if (!f) return;
    b = F.bbox(f);
    noeud('rect', {x: b.x, y: b.y, width: b.l, height: b.h, fill: 'none', stroke: '#1a73e8', 'stroke-width': 1, 'pointer-events': 'none'}, gSur);
    function p(nom, x, y) { noeud('rect', {x: x - 4, y: y - 4, width: 8, height: 8, fill: '#ffffff', stroke: '#1a73e8', 'data-poignee': nom, 'class': 'avf-poignee'}, gSur); }
    if (f.type === 'polygon') f.points.forEach(function (q, i) { p('p' + i, q[0], q[1]); });
    else for (k in POIGNEES) p(k, b.x + b.l * POIGNEES[k][0], b.y + b.h * POIGNEES[k][1]);
  }

  // ---- pointeur
  function pt(e) {
    var r = svg.getBoundingClientRect();
    return [(e.clientX - r.left) * AV.larg / r.width, (e.clientY - r.top) * AV.haut / r.height];
  }
  function aimant(p, sauf) { var c = F.cibles(AV.formes, sauf, AV.larg, AV.haut); return [F.aimante(p[0], c.xs), F.aimante(p[1], c.ys)]; }
  function remonte(e, attr) {
    var n = e.target;
    while (n && n !== svg) { if (n.getAttribute && n.getAttribute(attr) !== null) return n; n = n.parentNode; }
    return null;
  }
  function nouvelle(type, extra) {
    var f = F.normalise(Object.assign({id: AV.idSuivant(), type: type, fill: '#888888', zone: S.zone}, extra));
    return f;
  }
  function bas(e) {
    var p = pt(e), h, g, f;
    if (S.outil === 'polygon') { (S.poly = S.poly || []).push(aimant(p, null)); AV.dessine(); return; }
    if (S.outil === 'rect') {
      p = aimant(p, null);
      S.drag = {mode: 'creer', x0: p[0], y0: p[1]};
      S.temp = nouvelle('rect', {x: p[0], y: p[1], l: 4, h: 4});
      svg.setPointerCapture(e.pointerId); return;
    }
    h = remonte(e, 'data-poignee');
    if (h) { S.drag = {mode: 'redim', nom: h.getAttribute('data-poignee')}; svg.setPointerCapture(e.pointerId); return; }
    g = remonte(e, 'data-id');
    if (!g) { AV.selection = null; AV.dessine(); return; }
    // le clic prend la forme la plus haute sous le pointeur : le <g> cible est deja celle-la
    AV.selection = +g.getAttribute('data-id'); f = AV.cherche(AV.selection);
    S.drag = {mode: 'deplace', x0: p[0], y0: p[1], orig: JSON.parse(JSON.stringify(f))};
    svg.setPointerCapture(e.pointerId); AV.dessine();
  }
  function bouge(e) {
    var p = pt(e), d = S.drag, f, o, c, dx, dy, b;
    S.souris = p;
    if (!d) { if (S.poly) AV.dessine(); return; }
    if (d.mode === 'creer') {
      p = aimant(p, null);
      S.temp.x = Math.min(d.x0, p[0]); S.temp.y = Math.min(d.y0, p[1]); S.temp.l = Math.max(4, Math.abs(p[0] - d.x0)); S.temp.h = Math.max(4, Math.abs(p[1] - d.y0));
    } else if (d.mode === 'redim') {
      f = AV.cherche(AV.selection); p = aimant(p, f.id); F.redim(f, d.nom, p[0], p[1]);
    } else {
      f = AV.cherche(AV.selection); o = d.orig; c = F.cibles(AV.formes, f.id, AV.larg, AV.haut); b = F.bbox(o);
      dx = F.aimanteBord(b.x + p[0] - d.x0, b.l, c.xs) - b.x; dy = F.aimanteBord(b.y + p[1] - d.y0, b.h, c.ys) - b.y;
      Object.assign(f, JSON.parse(JSON.stringify(o))); F.deplace(f, dx, dy);
    }
    AV.dessine();
  }
  function haut() {
    var d = S.drag, f;
    S.drag = null;
    if (!d) return;
    if (d.mode === 'creer') { f = S.temp; S.temp = null; ajoute(f); return; }
    AV.commit();
  }
  function ajoute(f) {
    var c;
    if (!f.zone) { c = couleurPhoto(f); if (c) f.fill = c; }
    AV.formes.push(f); AV.selection = f.id; S.outil = 'sel'; outils(); AV.commit();
  }
  function ferme() {
    if (S.outil !== 'polygon' || !S.poly) return;
    S.poly.pop();                                     // le double-clic a pose deux fois le meme sommet
    var f = S.poly.length >= 3 ? nouvelle('polygon', {points: S.poly}) : null;
    S.poly = null;
    if (f) ajoute(f); else AV.dessine();
  }

  // ---- palette et panneau
  function outils() {
    document.querySelectorAll('[data-avf-outil]').forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-avf-outil') === S.outil ? 'true' : 'false'); });
  }
  function pose(nom) {
    var g = F.nouveauGabarit(nom, Math.round(AV.larg / 2 - F.GAB[nom].l / 2), Math.round(AV.haut / 2 - F.GAB[nom].h / 2), AV.idSuivant()), c;
    if (!g.motif) { c = couleurPhoto(g); if (c && nom !== 'fenetre') g.fill = c; }
    g.zone = null; AV.formes.push(g); AV.selection = g.id; AV.commit();
  }
  function ordre(haut) {
    var f = AV.cherche(AV.selection), i;
    if (!f) return;
    i = AV.formes.indexOf(f); AV.formes.splice(i, 1);
    if (haut) AV.formes.push(f); else AV.formes.unshift(f);
    AV.commit();
  }
  function supprime() {
    var f = AV.cherche(AV.selection);
    if (!f) return;
    AV.formes.splice(AV.formes.indexOf(f), 1); AV.selection = null; AV.commit();
  }
  function panneau() {
    var f = AV.cherche(AV.selection), p = $('sel'), g;
    if (!p) return;
    p.hidden = !f;
    if (!f) return;
    $('fill').value = f.fill; $('motif').value = f.motif || ''; $('trait').checked = !!f.stroke; $('trait-c').value = f.stroke || '#ffffff';
    $('sw').value = f.sw || 2; $('zone').value = f.zone || ''; $('texte').value = f.texte || ''; $('pente').value = f.pente || 0; $('battants').value = f.battants || 2;
    g = f.gabarit;
    $('l-pente').hidden = g !== 'toitMono'; $('l-battants').hidden = g !== 'fenetre'; $('l-texte').hidden = g !== 'numero';
    $('l-fill').hidden = !!f.zone;
    $('titre-sel').textContent = f.zone ? 'Zone ' + f.zone : (g || f.type);
  }
  function applique(champ) {
    var f = AV.cherche(AV.selection), v;
    if (!f) return;
    if (champ === 'fill') { f.fill = $('fill').value; f.motif = null; }
    else if (champ === 'motif') f.motif = $('motif').value || null;
    else if (champ === 'trait' || champ === 'trait-c' || champ === 'sw') { f.stroke = $('trait').checked ? $('trait-c').value : null; f.sw = +$('sw').value || 0; }
    else if (champ === 'zone') f.zone = $('zone').value || null;
    else if (champ === 'texte') f.texte = $('texte').value.slice(0, 8);
    else if (champ === 'pente') f.pente = +$('pente').value || 0;
    else if (champ === 'battants') f.battants = +$('battants').value === 1 ? 1 : 2;
    v = F.normalise(f); if (v) Object.assign(f, v);
    AV.dessine();
  }

  function demarre() {
    var racine = $('racine');
    if (!racine) return;
    racine.addEventListener('click', function (e) {
      var b = e.target.closest ? e.target.closest('button') : null, a;
      if (!b) return;
      a = b.getAttribute('data-avf-outil');
      if (a) { S.outil = a; S.poly = null; S.temp = null; outils(); return; }
      a = b.getAttribute('data-avf-gab'); if (a) { pose(a); return; }
      a = b.getAttribute('data-avf-act');
      if (a === 'annule') AV.annule(); else if (a === 'retablit') AV.retablit(); else if (a === 'avant') ordre(true); else if (a === 'arriere') ordre(false);
      else if (a === 'supprime') supprime();
      else if (a === 'repique') { var f = AV.cherche(AV.selection), c = f && couleurPhoto(f); if (c) { f.fill = c; f.motif = null; AV.commit(); } }
    });
    ['fill', 'motif', 'trait', 'trait-c', 'sw', 'zone', 'texte', 'pente', 'battants'].forEach(function (c) {
      var el = $(c);
      if (!el) return;
      el.addEventListener('input', function () { applique(c); });
      el.addEventListener('change', function () { applique(c); AV.commit(); });
    });
    if ($('zone-outil')) $('zone-outil').addEventListener('change', function () { S.zone = $('zone-outil').value || null; });
    if ($('opacite')) $('opacite').addEventListener('input', AV.dessine);
    document.addEventListener('keydown', function (e) {
      var t = e.target && e.target.tagName, k = e.key;
      if (t === 'INPUT' || t === 'SELECT' || t === 'TEXTAREA') return;
      if ((e.ctrlKey || e.metaKey) && (k === 'z' || k === 'Z')) { e.preventDefault(); if (e.shiftKey) AV.retablit(); else AV.annule(); }
      else if ((e.ctrlKey || e.metaKey) && (k === 'y' || k === 'Y')) { e.preventDefault(); AV.retablit(); }
      else if (k === 'Delete' || k === 'Backspace') { if (AV.selection !== null) { e.preventDefault(); supprime(); } }
      else if (k === 'Escape') { S.poly = null; S.temp = null; S.drag = null; AV.dessine(); }
    });
    outils();
  }
  if (AV.surChangement) AV.surChangement(function () { S.urlPhoto = null; S.img = null; AV.dessine(); });
  demarre();
  AV.dessine();
})();
"""
