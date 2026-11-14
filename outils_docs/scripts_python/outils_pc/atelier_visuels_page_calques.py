"""Calques des points chauds de l'atelier des visuels (spec 2026-11-13 § 2.3-2.5) : modele AV.elements, etat simule AV.sim et rendu.

Le rendu rend des NOEUDS (comme AV_FORMES) : `ser` pour les exports (chaine), `bati` pour le DOM de l'editeur. Rien venu de
l'utilisateur n'est insere autrement que par attribut ou texte echappes. Un voyant porte trois groupes (s-on, s-off, s-inc) dont
la classe du parent (on / off / inc) montre un seul : le CSS est dans le SVG exporte, donc autonome. Une liaison est `active` ou `muette`.
Element : {id, type: voyant|valeur|liaison, x, y, [x2, y2], source, style}. Icone : {w, h, d} (tracé `path`, viewBox 0 0 w h).
Egalement ici : AV.fondPhoto() (photo avec les zones « effacer » remplies d'un aplat de la couleur mediane de leur bord).
"""

JS_CALQUES = r"""
var AV_CALQUES = (function () {
  var F = AV_FORMES, COUL = /^#[0-9a-fA-F]{6}$/, D = /^[MmLlHhVvCcSsQqTtAaZz0-9eE.,\s+-]{1,6000}$/;
  var CSS = '.av-v .s-on,.av-v .s-off,.av-v .s-inc{display:none}.av-v.on .s-on,.av-v.off .s-off,.av-v.inc .s-inc{display:inline}' +
    '.av-v,.av-l{cursor:pointer}.av-l line{stroke-width:3;stroke-linecap:round}' +
    '.av-l.active line{stroke:#3ddc84;stroke-dasharray:8 6;animation:avd 1s linear infinite}' +
    '.av-l.muette line{stroke:#8a8f98;stroke-dasharray:2 6;opacity:.6}@keyframes avd{to{stroke-dashoffset:-14}}';
  var SCRIPT = "(function(){var r=document.currentScript.parentNode;r.addEventListener('click',function(e){var t=e.target.closest?e.target:null,g=t&&t.closest('.av-v'),l=t&&t.closest('.av-l');" +
    "if(g){g.classList.toggle('on');g.classList.toggle('off');g.classList.remove('inc');}else if(l){l.classList.toggle('active');l.classList.toggle('muette');}});})();";
  function num(v, d, a, b) { return typeof v === 'number' && isFinite(v) ? Math.min(b, Math.max(a, v)) : d; }
  function r1(v) { return Math.round(v * 10) / 10; }
  function coul(v, d) { return COUL.test(v) ? v : d; }
  function icone(ic) {
    if (!ic || typeof ic !== 'object' || typeof ic.d !== 'string' || !D.test(ic.d)) return null;
    return {w: num(ic.w, 24, 1, 512), h: num(ic.h, 24, 1, 512), d: ic.d};
  }
  function poseIcone(ic, x, y, t, c) {
    var s = t / Math.max(ic.w, ic.h);
    return ['path', {d: ic.d, fill: c, transform: 'translate(' + r1(x - ic.w * s / 2) + ' ' + r1(y - ic.h * s / 2) + ') scale(' + Math.round(s * 1000) / 1000 + ')'}];
  }
  function etatVoyant(sim, id) { var e = sim && sim[id]; return e === 'on' || e === 'inc' ? e : 'off'; }
  function noeudVoyant(el, sim) {
    var st = el.style || {}, t = num(st.taille, 14, 6, 80), cs = {on: coul(st.couleur_on, '#3ddc84'), off: coul(st.couleur_off, '#8a8f98'), inc: coul(st.couleur_inconnu, '#c9ccd1')};
    var ics = {on: icone(st.icone_on), off: icone(st.icone_off), inc: icone(st.icone_inconnu)}, enf = [];
    ['on', 'off', 'inc'].forEach(function (k) {
      var forme = ics[k] ? poseIcone(ics[k], el.x, el.y, t, cs[k]) : st.forme === 'carre'
        ? ['rect', {x: r1(el.x - t / 2), y: r1(el.y - t / 2), width: t, height: t, fill: cs[k], stroke: '#ffffff', 'stroke-width': 1}]
        : ['circle', {cx: r1(el.x), cy: r1(el.y), r: t / 2, fill: cs[k], stroke: '#ffffff', 'stroke-width': 1}];
      enf.push(['g', {'class': 's-' + k}, [forme]]);
    });
    return ['g', {'class': 'av-v ' + etatVoyant(sim, el.id), 'data-el': el.id, role: 'img', 'aria-label': 'Voyant ' + el.id}, enf];
  }
  function noeudValeur(el) {
    var st = el.style || {}, txt = String(st.exemple === undefined ? '0' : st.exemple).slice(0, 12) + (st.unite ? ' ' + String(st.unite).slice(0, 6) : ''), t = num(st.taille, 14, 8, 60);
    var w = Math.round(txt.length * t * 0.6 + 10);
    return ['g', {'class': 'av-val', 'data-el': el.id}, [
      ['rect', {x: r1(el.x - w / 2), y: r1(el.y - t * 0.8), width: w, height: r1(t * 1.4), rx: 4, fill: '#1f1f1f', 'fill-opacity': 0.75}],
      ['text', {x: r1(el.x), y: r1(el.y + t * 0.3), 'font-size': t, 'font-family': 'sans-serif', 'text-anchor': 'middle', fill: coul(st.couleur, '#ffffff')}, txt]]];
  }
  function noeudLiaison(el, sim) {
    var a = sim && sim[el.id] === 'muette' ? 'muette' : 'active';
    return ['g', {'class': 'av-l ' + a, 'data-el': el.id}, [['line', {x1: r1(el.x), y1: r1(el.y), x2: r1(el.x2), y2: r1(el.y2), stroke: '#3ddc84'}]]];
  }
  function rendu(els, sim) {
    return [['style', {}, CSS], ['g', {'class': 'av-calques'}, (els || []).map(function (el) {
      return el.type === 'voyant' ? noeudVoyant(el, sim) : el.type === 'valeur' ? noeudValeur(el) : noeudLiaison(el, sim);
    })]];
  }
  return {CSS: CSS, SCRIPT: SCRIPT, icone: icone, rendu: rendu, etatVoyant: etatVoyant, num: num, coul: coul,
          chaine: function (els, sim) { return els && els.length ? rendu(els, sim).map(F.ser).join('') : ''; }};
})();

(function () {
  var AV = window.AV, F = AV_FORMES;
  if (!AV) return;
  AV.elements = []; AV.sim = {};
  // photo sur laquelle les zones « effacer » sont remplies d'un aplat de la couleur mediane de leur bord (anneau de 4 px)
  AV.fondPhoto = function () {
    var z = AV.zones('effacer');
    if (!z.length || typeof document === 'undefined') return AV.photo;
    var c = document.createElement('canvas'), g, im, W, H;
    c.width = W = AV.photo.width; c.height = H = AV.photo.height;
    g = c.getContext('2d'); g.drawImage(AV.photo, 0, 0);
    try { im = g.getImageData(0, 0, W, H); } catch (e) { return AV.photo; }
    z.forEach(function (f) {
      var b = F.bbox(f), m = 4, x0 = Math.max(0, Math.floor(b.x - m)), y0 = Math.max(0, Math.floor(b.y - m)), x1 = Math.min(W, Math.ceil(b.x + b.l + m)),
          y1 = Math.min(H, Math.ceil(b.y + b.h + m)), ch = [[], [], []], x, y, i, k, dedans, rgb;
      for (y = y0; y < y1; y++) for (x = x0; x < x1; x++) {
        dedans = f.type === 'polygon' ? F.dansPoly(x + 0.5, y + 0.5, f.points) : x >= b.x && x < b.x + b.l && y >= b.y && y < b.y + b.h;
        if (dedans) continue;
        i = (y * W + x) * 4;
        for (k = 0; k < 3; k++) ch[k].push(im.data[i + k]);
      }
      if (!ch[0].length) return;
      rgb = ch.map(function (t) { t.sort(function (a, z2) { return a - z2; }); return t[Math.floor(t.length / 2)]; });
      g.fillStyle = 'rgb(' + rgb.join(',') + ')';
      if (f.type === 'polygon') { g.beginPath(); f.points.forEach(function (p, j) { if (j) g.lineTo(p[0], p[1]); else g.moveTo(p[0], p[1]); }); g.closePath(); g.fill(); }
      else g.fillRect(b.x, b.y, b.l, b.h);
    });
    return c;
  };
  AV.calques = function () { return AV_CALQUES.chaine(AV.elements, AV.sim); };
})();
"""
