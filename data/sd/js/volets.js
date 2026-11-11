// volets.js - Facade des volets sous leurs curseurs, sur la page d'accueil de Tasmota (2026-11-11)
// Envoye par data/fs/vrPages.be::accueil apres <div id='vf'> et window.VOLETS (vrPages.be::facade) ; spec
// docs/superpowers/specs/2026-11-11-visuel-volets-reglage-durees-design.md (§3, §4) ; plan visuel-reglage-volets, A5.
// Insere tel quel dans un element script de la page : IIFE, seule globale window.Volets, aucun chevron dans le texte.
// Position : curseur s27<id> (lu a chaque image : Tasmota le change par .value, sans evenement), inverse si 'inverse' vaut 1 ;
// trappe a MPU6050 actif : angle de la balise data-vi de la ligne d'inclinaison. Poursuite : le dessin rejoint la derniere
// valeur lue a la vitesse du volet, sans la depasser (retard d'au plus un rafraichissement). Bancs : test_volets.mjs, test_volets_chrome.py.
(function () {
  var NS = 'http://www.w3.org/2000/svg';
  var ROUGE = '#e0453a';
  var LARG = {fenetre: 80, porte: 64, garage: 176, trappe: 60, trappeEchelle: 80};

  function borne(p) { return p < 0 ? 0 : (p > 100 ? 100 : p); }

  // Valeur du curseur -> % d'ouverture (ShutterInvert 1 : Tasmota affiche 100 - position)
  function ouverture(valeur, inverse) {
    var v = Number(valeur);
    return borne(inverse == 1 ? 100 - v : v);
  }

  // Angle (degres) -> % d'ouverture, comme vrFonctions.be::positionReelle (sans le 100 - p de ShutterInvert) ; null sans angle
  function ouvertureAngle(angle, incl) {
    if (angle === '' || angle == null || !incl || incl.ouvert == incl.ferme) return null;
    var a = Number(angle);
    if (isNaN(a)) return null;
    return borne((a - incl.ferme) * 100 / (incl.ouvert - incl.ferme));
  }

  // Poursuite : de 'dessinee' vers 'cible' (%) en dt ms, a 100 / tempsMontee %/s en montee, 100 / tempsDescente en descente,
  // sans jamais depasser la cible ; premiere lecture (dessinee nulle) ou duree inconnue : la cible directement
  function poursuit(dessinee, cible, dt, o) {
    var d = cible - dessinee, duree = d > 0 ? o.tempsMontee : o.tempsDescente;
    if (dessinee == null || !(duree > 0)) return borne(cible);
    var pas = (dt > 0 ? dt : 0) / 10 / duree;                         // 100 % en 'duree' s : dt ms * 100 / (1000 * duree)
    return borne(Math.abs(d) <= pas ? cible : dessinee + (d > 0 ? pas : -pas));
  }

  function el(parent, nom, attributs) {
    var e = document.createElementNS(NS, nom);
    for (var k in attributs) e.setAttribute(k, attributs[k]);
    parent.appendChild(e);
    return e;
  }

  // Tablier a lames dans [x, x + l] x [y, y + h], qui remonte quand le volet s'ouvre
  function tablier(svg, g, o, x, y, l, h, motif) {
    var clip = el(g, 'clipPath', {id: 'vfc' + o.id});
    el(clip, 'rect', {x: x, y: y, width: l, height: h});
    var mob = el(el(g, 'g', {'clip-path': 'url(#vfc' + o.id + ')'}), 'rect', {x: x, y: 0, width: l, height: h, fill: 'url(#' + motif + ')'});
    return function (f) { mob.setAttribute('transform', 'translate(0,' + (y - h * f) + ')'); return mob; };
  }

  // Dessin d'une ouverture ; rend la fonction qui la pose a la fraction f (0 ferme, 1 ouvert) et rend l'element a rougir
  function ouvertureSvg(svg, g, o, x, plancher, marches) {
    var l = LARG[o.type] || 64, t = o.type;
    if (t == 'fenetre') {
      el(g, 'rect', {x: x, y: 86, width: l, height: 62, fill: '#bfe3f7', stroke: '#eee', 'stroke-width': 3});
      el(g, 'line', {x1: x + l / 2, y1: 86, x2: x + l / 2, y2: 148, stroke: '#eee', 'stroke-width': 3});
      el(g, 'rect', {x: x - 4, y: 78, width: l + 8, height: 9, fill: '#6b6b6b'});
      return [164, tablier(svg, g, o, x, 87, l, 61, 'vf_lames')];
    }
    if (t == 'porte') {
      el(g, 'rect', {x: x, y: 88, width: l, height: 108, fill: '#8a5a3b', stroke: '#eee', 'stroke-width': 3});
      el(g, 'rect', {x: x + 10, y: 98, width: l - 20, height: 40, fill: '#bfe3f7'});
      el(g, 'circle', {cx: x + l - 8, cy: 146, r: 3.5, fill: '#e0c060'});
      el(g, 'rect', {x: x - 4, y: 80, width: l + 8, height: 9, fill: '#6b6b6b'});
      return [190, tablier(svg, g, o, x, 89, l, 107, 'vf_lames')];
    }
    if (t == 'garage') {
      el(g, 'rect', {x: x, y: 94, width: l, height: 102, fill: '#3a3a3a', stroke: '#eee', 'stroke-width': 3});
      el(g, 'rect', {x: x - 6, y: 84, width: l + 12, height: 11, fill: '#6b6b6b'});
      return [80, tablier(svg, g, o, x, 95, l, 101, 'vf_lamesG')];
    }
    // Trappe : le panneau se baisse face a l'observateur (hauteur vue = longueur x sin(angle)) ; trappeEchelle : puis l'echelle
    // descend du HAUT de la trappe, devant le panneau, et repose sur les marches de l'escalier fixe
    var y0 = plancher[0], y1 = plancher[1], echelle = t == 'trappeEchelle';
    el(g, 'rect', {x: x, y: y0, width: l, height: y1 - y0, fill: '#2a2420'});
    var pan = el(g, 'polygon', {fill: '#a8916f', stroke: '#7a6548'});
    var ech = el(g, 'g', {});
    return [echelle ? 20 : y0 - 4, function (f) {
      var h = (echelle ? 70 : 40) * Math.sin(Math.PI / 2 * Math.min(1, echelle ? f * 1.6 : f));
      pan.setAttribute('points', x + ',' + y1 + ' ' + (x + l) + ',' + y1 + ' ' + (x + l + 4) + ',' + (y1 + h) + ' ' + (x - 4) + ',' + (y1 + h));
      if (echelle) {
        while (ech.firstChild) ech.removeChild(ech.firstChild);
        var k = Math.max(0, f - 0.4) / 0.6, xg = x + 12, xd = x + l - 12;
        var pg = y0 + (marches(xg) - y0) * k, pd = y0 + (marches(xd) - y0) * k;
        if (k > 0) {
          el(ech, 'line', {x1: x + 15, y1: y0, x2: xg, y2: pg, stroke: '#ddd', 'stroke-width': 3});
          el(ech, 'line', {x1: x + l - 15, y1: y0, x2: xd, y2: pd, stroke: '#ddd', 'stroke-width': 3});
          for (var y = y0 + 12; y < Math.min(pg, pd); y += 14) el(ech, 'line', {x1: x + 14, y1: y, x2: x + l - 14, y2: y, stroke: '#ddd', 'stroke-width': 2});
        }
      }
      return pan;
    }];
  }

  // Dessine la facade dans 'conteneur' ; chaque ouverture : <g data-id data-ouverture>, son texte « nom NN % »
  function dessine(conteneur, facade) {
    var ouv = facade.ouvertures || [], toit = facade.toit, maison = toit == 'deuxPans' || toit == 'unPan';
    var somme = 40 * (ouv.length - 1);
    ouv.forEach(function (o) { somme += LARG[o.type] || 64; });
    var W = Math.max(maison ? 300 : 240, somme + 80), x = (W - somme) / 2;
    var plancher = maison ? [66, 72] : [30, 38];
    var marches = function (xm) { return 100 + 9 * Math.floor(xm / 24); };
    while (conteneur.firstChild) conteneur.removeChild(conteneur.firstChild);
    var svg = el(conteneur, 'svg', {viewBox: '0 0 ' + W + ' 200', width: '100%', style: 'display:block;margin:8px 0'});
    var defs = el(svg, 'defs', {});
    [['vf_lames', 10, 8, 6.5, 1.5, '#9aa3ab', '#6f777e'], ['vf_lamesG', 12, 10, 8, 2, '#b4bcc3', '#7d858c']].forEach(function (m) {
      var p = el(defs, 'pattern', {id: m[0], width: m[1], height: m[2], patternUnits: 'userSpaceOnUse'});
      el(p, 'rect', {width: m[1], height: m[2], fill: m[5]});
      el(p, 'rect', {y: m[3], width: m[1], height: m[4], fill: m[6]});
    });
    var trappe = ouv.some(function (o) { return o.type == 'trappe' || o.type == 'trappeEchelle'; });
    if (toit == 'deuxPans') {
      el(svg, 'polygon', {points: '10,66 ' + W / 2 + ',8 ' + (W - 10) + ',66', fill: '#9c4b3a'});
      el(svg, 'rect', {x: 20, y: 66, width: W - 40, height: 130, fill: '#d8cbb0'});
    } else if (toit == 'unPan') {
      el(svg, 'polygon', {points: '20,44 ' + (W - 20) + ',60 ' + (W - 20) + ',196 20,196', fill: '#d8cbb0'});
      el(svg, 'polygon', {points: '6,36 ' + (W - 6) + ',54 ' + (W - 6) + ',63 6,45', fill: '#6e6e6e'});
    } else {
      el(svg, 'rect', {x: 0, y: 0, width: W, height: 30, fill: '#e8e1d4'});
      el(svg, 'rect', {x: 0, y: 38, width: W, height: 154, fill: '#3b3631'});
      el(svg, 'rect', {x: 0, y: 192, width: W, height: 8, fill: '#777'});
    }
    if (trappe) el(svg, 'rect', {x: maison ? 20 : 0, y: plancher[0], width: maison ? W - 40 : W, height: plancher[1] - plancher[0], fill: '#c9b79c'});
    if (ouv.some(function (o) { return o.type == 'trappeEchelle'; })) {       // escalier en bois fixe, de gauche (haut) a droite
      var pts = '';
      for (var xm = 0; xm < W; xm += 24) pts += xm + ',' + marches(xm) + ' ' + Math.min(W, xm + 24) + ',' + marches(xm) + ' ';
      el(svg, 'polygon', {points: pts + W + ',192 0,192', fill: '#8a5a3b', stroke: '#5e3c26'});
      el(svg, 'line', {x1: 0, y1: 96, x2: W, y2: marches(W - 1) - 4, stroke: '#6b4429', 'stroke-width': 3});      // rampe
    }
    svg.volets = ouv.map(function (o) {
      var g = el(svg, 'g', {'data-id': o.id, 'data-ouverture': ''});
      var r = ouvertureSvg(svg, g, o, x, plancher, marches);
      var texte = el(svg, 'text', {x: x + (LARG[o.type] || 64) / 2, y: r[0], 'font-size': 11, 'text-anchor': 'middle',
        style: 'fill:var(--c_txt);stroke:var(--c_bg);stroke-width:3px;paint-order:stroke'});
      texte.textContent = String(o.nom || '').replace(/^volet( roulant)?\s+/i, '') + ' ';
      var pct = el(texte, 'tspan', {'class': 'vf_pct'}), cause = el(texte, 'tspan', {});
      x += (LARG[o.type] || 64) + 40;
      return {o: o, g: g, pose: r[1], pct: pct, cause: cause};
    });
    return svg;
  }

  // Pose une ouverture a p % ; 'bloque' : '', 'bloque' ou 'sens inverse' (MPU6050)
  function pose(v, p, bloque) {
    if (v.p === p && v.b === bloque) return;              // immobile : DOM inchange (accueil ouvert des jours sur une tablette)
    v.p = p;
    v.b = bloque;
    var n = Math.round(p), mob = v.pose(p / 100);
    if (mob.getAttribute('data-rouge') !== bloque) {
      mob.setAttribute('data-rouge', bloque);
      mob.style.fill = bloque ? ROUGE : '';
      v.pct.style.fill = v.cause.style.fill = bloque ? ROUGE : '';
      v.cause.textContent = bloque ? ' ' + (bloque == 'bloque' ? 'bloqué' : bloque) : '';
    }
    if (v.g.getAttribute('data-ouverture') !== String(n)) {
      v.g.setAttribute('data-ouverture', n);
      v.pct.textContent = n + ' %';
    }
  }

  // Position reelle lue d'une ouverture : [% d'ouverture, cause de blocage] ou null (ni angle, ni curseur)
  function lit(v) {
    var o = v.o, b = o.inclinaison ? document.querySelector("[data-vi='" + o.id + "']") : null;   // table des capteurs remplacee a chaque rafraichissement
    var a = b ? ouvertureAngle(b.getAttribute('data-angle'), o.inclinaison) : null, bloque = b ? b.getAttribute('data-bloque') || '' : '';
    if (a != null) return [a, bloque];
    var c = document.getElementById('s27' + o.id);
    return c ? [ouverture(c.value, o.inverse), bloque] : null;
  }

  // Insere le dessin juste apres la table des curseurs (#s271) et l'anime ; rien sans #s271
  function demarre(facade) {
    var s1 = document.getElementById('s271'), table = s1 && s1.closest('table');
    if (!table || !facade || !facade.ouvertures || !facade.ouvertures.length) return null;
    var vf = document.getElementById('vf') || document.createElement('div');
    table.parentNode.insertBefore(vf, table.nextSibling);
    var svg = dessine(vf, facade), avant = null;
    function image() {
      var t = performance.now(), dt = avant == null ? 0 : t - avant;
      avant = t;
      svg.volets.forEach(function (v) {
        var l = lit(v);
        if (!l) return;
        v.dessinee = poursuit(v.dessinee, l[0], dt, v.o);
        pose(v, v.dessinee, l[1]);
      });
      requestAnimationFrame(image);
    }
    image();
    return svg;
  }

  window.Volets = {ouverture: ouverture, ouvertureAngle: ouvertureAngle, poursuit: poursuit, dessine: dessine, demarre: demarre};
  if (typeof document !== 'undefined' && window.VOLETS) {
    try { demarre(window.VOLETS); } catch (e) { if (window.console) console.error('volets.js : ' + e.message); }
  }
})();
