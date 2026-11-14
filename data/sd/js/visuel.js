// visuel.js : visuel d'accueil de la carte (plan tasks/plans/atelier-visuels.md, A4). Injecte inline par
// visuelFonctions.html() apres window.VISUEL (la description visuel.json) ; relu a chaque ouverture de l'accueil : le garder petit.
// Meme dessin que les calques de l'atelier 7990 (classes av-v, av-l, av-val ; atelier_visuels_page_calques.py::JS_CALQUES) :
// l'apercu de l'outil et la carte restent identiques. Les icones d'un voyant sont des chemins inline de la description
// (style.icone_on|off|inconnu = {w, h, d}), pas de table ici. Une IIFE, sans balise fermante ni commentaire HTML dans ce texte.
// Rythme : desc.rafraichissement (defaut 2345 ms, la valeur par defaut de WebRefresh ; minimum 1000), requete suivante APRES la
// reponse, abandon a 4 s : dessin grise (opacite .45), voyants « inconnu », jamais d'exception.
(function () {
  var NS = 'http://www.w3.org/2000/svg', COUL = /^#[0-9a-fA-F]{6}$/, D = /^[MmLlHhVvCcSsQqTtAaZz0-9eE.,\s+-]{1,6000}$/;
  var CSS = '.av-v .s-on,.av-v .s-off,.av-v .s-inc{display:none}.av-v.on .s-on,.av-v.off .s-off,.av-v.inc .s-inc{display:inline}' +
    '.av-l line{stroke-width:3;stroke-linecap:round}' +
    '.av-l.active line{stroke:#3ddc84;stroke-dasharray:8 6;animation:avd 1s linear infinite}' +
    '.av-l.alerte line{stroke:#e5a50a;stroke-dasharray:8 6;animation:avd 2s linear infinite}' +
    '.av-l.muette line{stroke:#8a8f98;stroke-dasharray:2 6;opacity:.6}@keyframes avd{to{stroke-dashoffset:-14}}';
  function num(v, d, a, b) { return typeof v === 'number' && isFinite(v) ? Math.min(b, Math.max(a, v)) : d; }
  function r1(v) { return Math.round(v * 10) / 10; }
  function coul(v, d) { return COUL.test(v) ? v : d; }
  function icone(ic) {
    if (!ic || typeof ic !== 'object' || typeof ic.d !== 'string' || !D.test(ic.d)) return null;
    return {w: num(ic.w, 24, 1, 512), h: num(ic.h, 24, 1, 512), d: ic.d};
  }
  function noeud(doc, nom, a, parent, txt) {
    var e = doc.createElementNS(NS, nom), k;
    for (k in a) e.setAttribute(k, a[k]);
    if (txt !== undefined) e.textContent = txt;
    if (parent) parent.appendChild(e);
    return e;
  }
  function voyant(doc, el, parent) {
    var st = el.style || {}, t = num(st.taille, 14, 6, 80), g = noeud(doc, 'g', {'class': 'av-v inc', 'data-el': el.id}, parent);
    var cs = {on: coul(st.couleur_on, '#3ddc84'), off: coul(st.couleur_off, '#8a8f98'), inc: coul(st.couleur_inconnu, '#c9ccd1')};
    var ics = {on: icone(st.icone_on), off: icone(st.icone_off), inc: icone(st.icone_inconnu)};
    ['on', 'off', 'inc'].forEach(function (k) {
      var s = noeud(doc, 'g', {'class': 's-' + k}, g), ic = ics[k], f;
      if (ic) {
        f = t / Math.max(ic.w, ic.h);
        noeud(doc, 'path', {d: ic.d, fill: cs[k], transform: 'translate(' + r1(el.x - ic.w * f / 2) + ' ' + r1(el.y - ic.h * f / 2) + ') scale(' + Math.round(f * 1000) / 1000 + ')'}, s);
      } else if (st.forme === 'carre') {
        noeud(doc, 'rect', {x: r1(el.x - t / 2), y: r1(el.y - t / 2), width: t, height: t, fill: cs[k], stroke: '#ffffff', 'stroke-width': 1}, s);
      } else {
        noeud(doc, 'circle', {cx: r1(el.x), cy: r1(el.y), r: t / 2, fill: cs[k], stroke: '#ffffff', 'stroke-width': 1}, s);
      }
    });
    return {t: 'voyant', el: el, g: g};
  }
  function valeur(doc, el, parent) {
    var st = el.style || {}, t = num(st.taille, 14, 8, 60), g = noeud(doc, 'g', {'class': 'av-val', 'data-el': el.id}, parent);
    var fond = noeud(doc, 'rect', {x: el.x, y: r1(el.y - t * 0.8), width: 0, height: r1(t * 1.4), rx: 4, fill: '#1f1f1f', 'fill-opacity': 0.75}, g);
    var texte = noeud(doc, 'text', {x: r1(el.x), y: r1(el.y + t * 0.3), 'font-size': t, 'font-family': 'sans-serif', 'text-anchor': 'middle', fill: coul(st.couleur, '#ffffff')}, g, '');
    return {t: 'valeur', el: el, fond: fond, texte: texte, taille: t};
  }
  function liaison(doc, el, parent) {
    var g = noeud(doc, 'g', {'class': 'av-l muette', 'data-el': el.id}, parent);
    noeud(doc, 'line', {x1: r1(el.x), y1: r1(el.y), x2: r1(el.x2), y2: r1(el.y2), stroke: '#3ddc84'}, g);
    return {t: 'liaison', el: el, g: g};
  }
  // Dessine le fond (image) et un calque par element dans `conteneur` ; rend le svg. Element de type inconnu : ignore.
  function monte(conteneur, desc, urlFond) {
    var doc = conteneur.ownerDocument || document, f = desc.fond || {}, svg, refs = [];
    svg = noeud(doc, 'svg', {xmlns: NS, viewBox: '0 0 ' + f.largeur + ' ' + f.hauteur, style: 'width:100%;height:auto;display:block'});
    noeud(doc, 'style', {}, svg, CSS);
    noeud(doc, 'image', {href: urlFond, x: 0, y: 0, width: f.largeur, height: f.hauteur}, svg);
    var cal = noeud(doc, 'g', {'class': 'av-calques'}, svg);
    (desc.elements || []).forEach(function (el) {
      if (el.type === 'voyant') refs.push(voyant(doc, el, cal));
      else if (el.type === 'valeur') refs.push(valeur(doc, el, cal));
      else if (el.type === 'liaison') refs.push(liaison(doc, el, cal));
    });
    svg._vz = {refs: refs};
    conteneur.appendChild(svg);
    return svg;
  }
  function lis(sensor, chemin) {
    var v = sensor, i;
    for (i = 0; i < chemin.length; i++) {
      if (v === null || typeof v !== 'object') return undefined;
      v = v[chemin[i]];
    }
    return v;
  }
  // true / false, ou null (inconnu) quand la source n'est pas lisible
  function etatVoyant(s, etat) {
    var v, ok;
    if (s.type === 'relais') {
      v = etat.power && etat.power[s.n - 1];
      return v === undefined || v === null ? null : !!v;
    }
    v = lis(etat.sensor, s.chemin || []);
    if (v === undefined) return null;
    if (s.on !== undefined) return String(v) === String(s.on);
    if (s.on_min !== undefined) { ok = parseFloat(v); return isNaN(ok) ? null : ok >= s.on_min; }
    return v === 'ON' || v === true || parseFloat(v) > 0;
  }
  // 'active', 'alerte' ou 'muette' ; sans l'etat demande : muette
  function etatLiaison(s, etat, t) {
    var seuil = (s.seuil_s || 0) * 1000, ms, l, i;
    if (s.type === 'wifi') return etat.wifi === true ? 'active' : 'muette';
    if (s.type === 'modbus_serie' || s.type === 'modbus_esclave') {
      var m = etat.modbus || {};
      ms = s.type === 'modbus_serie' ? m.serie_ms : (m.esclaves || {})[String(s.id)];
      return typeof ms === 'number' && ms > 0 && t - ms < seuil ? 'active' : 'muette';
    }
    l = etat.reseau || [];
    for (i = 0; i < l.length; i++) {
      if (l[i].mac === s.mac) return l[i].etat === 'ok' ? 'active' : (l[i].etat === 'muet' || l[i].etat === 'ip') ? 'alerte' : 'muette';
    }
    return 'muette';
  }
  function texteValeur(el, etat) {
    var st = el.style || {}, v = lis(etat.sensor, (el.source || {}).chemin || []), n = parseFloat(v), s;
    if (v === undefined) s = '--';
    else if (!isNaN(n) && typeof v !== 'object') s = n.toFixed(num(st.decimales, 1, 0, 6));
    else s = String(v).slice(0, 12);
    return (st.texte_avant ? String(st.texte_avant).slice(0, 12) : '') + s + (st.unite ? ' ' + String(st.unite).slice(0, 6) : '');
  }
  // Met le dessin a jour d'apres l'etat de la carte ; etat null = carte muette (grise, rien n'est juge)
  function applique(svg, etat, t) {
    var inconnu = !etat || typeof etat !== 'object', tt = inconnu ? 0 : (t !== undefined ? t : etat.t);
    svg.setAttribute('opacity', inconnu ? 0.45 : 1);
    svg._vz.refs.forEach(function (r) {
      var s = r.el.source || {}, v, w;
      if (r.t === 'voyant') {
        v = inconnu ? null : etatVoyant(s, etat);
        r.g.setAttribute('class', 'av-v ' + (v === null ? 'inc' : v ? 'on' : 'off'));
      } else if (r.t === 'valeur') {
        r.texte.textContent = inconnu ? '--' : texteValeur(r.el, etat);
        w = Math.round(r.texte.textContent.length * r.taille * 0.6 + 10);
        r.fond.setAttribute('width', w);
        r.fond.setAttribute('x', r1(r.el.x - w / 2));
      } else {
        r.g.setAttribute('class', 'av-l ' + (inconnu ? 'muette' : etatLiaison(s, etat, tt)));
      }
    });
  }
  function empreinte(desc) {
    var s = JSON.stringify(desc), h = 0, i;
    for (i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
    return (h >>> 0).toString(16);
  }
  // Boucle de lecture de /visuel?f=etat : une requete a la fois, la suivante apres la reponse (ou l'abandon a 4 s)
  function demarre(conteneur, desc) {
    var svg = monte(conteneur, desc, '/visuel?f=fond&v=' + empreinte(desc)),
        delai = Math.max(1000, typeof desc.rafraichissement === 'number' ? desc.rafraichissement : 2345);
    function tour() {
      var fini = false, ctl = typeof AbortController === 'function' ? new AbortController() : null, minuterie;
      function fin(etat) {
        if (fini) return;
        fini = true; clearTimeout(minuterie);
        try { applique(svg, etat); } catch (e) { /* un dessin qui echoue ne doit pas arreter la boucle */ }
        setTimeout(tour, delai);
      }
      if (document.hidden) { fini = true; setTimeout(tour, delai); return; }
      minuterie = setTimeout(function () { if (ctl) ctl.abort(); fin(null); }, 4000);
      fetch('/visuel?f=etat', ctl ? {signal: ctl.signal, cache: 'no-store'} : {cache: 'no-store'})
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(fin, function () { fin(null); });
    }
    tour();
    return svg;
  }
  window.VisuelAccueil = {monte: monte, applique: applique, demarre: demarre, empreinte: empreinte};
  if (window.VISUEL && document.getElementById('vz')) demarre(document.getElementById('vz'), window.VISUEL);
})();
