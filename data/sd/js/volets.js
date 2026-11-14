// volets.js - Facade des volets sous leurs curseurs, sur la page d'accueil de Tasmota (2026-11-11)
// Envoye par data/fs/vrPages.be::accueil apres <div id='vf'> et window.VOLETS (vrPages.be::facade) ; spec
// docs/superpowers/specs/2026-11-11-visuel-volets-reglage-durees-design.md (§3, §4) ; plan visuel-reglage-volets, A5.
// Insere tel quel dans un element script de la page : IIFE, seule globale window.Volets, aucun chevron ouvrant suivi de « / » ou de « ! » dans le texte.
// Position : curseur s27<id> (lu a chaque image : Tasmota le change par .value, sans evenement), inverse si 'inverse' vaut 1 ;
// trappe a MPU6050 actif : angle de la balise data-vi de la ligne d'inclinaison. Poursuite : le dessin rejoint la derniere
// valeur lue a la vitesse du volet, sans la depasser (retard d'au plus un rafraichissement). Bancs : test_volets.mjs, test_volets_chrome.py.
// Ouverture a 'source' (rideau du garage, controleRideau.be::route, 2026-11-12) : sans curseur, % d'ouverture lu a cette adresse
// ({ouverture, muet}) a chaque rafraichissement, requete suivante apres la reponse ; dessin laisse a la place de #vf, grise si muet.
// Facade du garage (2026-11-13, plan facade-garage-capteurs) : 'decor' de la facade (chevrefeuille, porte, pergola ; toit unPan seulement,
// absent = dessin inchange) et 'finsDeCourse' d'une ouverture a rideau (nom des deux interrupteurs) : deux pastilles sur le rail droit,
// verte = contact ferme (etat ON), rouge = ouvert (OFF), grise = inconnu. Etats lus dans la reponse de 'source' (cle 'capteurs', carte du
// rideau) sinon a /volets?f=capteurs (P4, au rythme de facade.rafraichissement). Une pastille clignote si, plus de 6 s, la position LUE
// la contredit (>= 99 % sans contact d'ouverture, <= 1 % sans contact de fermeture, ou les deux contacts fermes) ; un etat inconnu ne juge pas.
// Maison du RDC (decor 'maison', 2026-11-13, maquette maquette_maison) : toit en appentis, briques, arcs, porte blanche a vitrage,
// numero, boite aux lettres, compteur, applique, marches ; fenetre, trappe et porte a leur place (POS) ; rapporteur de la trappe
// (angle de la balise data-vi, « ?° » sans balise) ; 'camera' de la facade : voyant lu a /volets?f=capteurs (cle camera),
// clic = confirmation puis POST /volets action=camera.
// Projecteur du garage (2026-11-14) : 'lampe' de la facade (toit unPan), lanterne sous le toit cote pergola, voyant lu a /volets?f=capteurs (cle lampe),
// clic = confirmation puis POST /volets action=lampe.
(function () {
  var NS = 'http://www.w3.org/2000/svg';
  var ROUGE = '#e0453a';
  var VERT = '#3cb04a';
  var GRIS = '#8a8f94';
  var DELAI = 6000;                                        // ms d'incoherence avant le clignotement
  var LARG = {fenetre: 80, porte: 64, garage: 176, trappe: 60, trappeEchelle: 80};
  var POS = {fenetre: 100, trappe: 194, porte: 284};       // x des ouvertures dans la maison (decor 'maison')

  function borne(p) { return p < 0 ? 0 : (p > 100 ? 100 : p); }

  // Valeur du curseur -> % d'ouverture (ShutterInvert 1 : Tasmota affiche 100 - position)
  function ouverture(valeur, inverse) {
    var v = Number(valeur);
    return borne(inverse == 1 ? 100 - v : v);
  }

  // Angle (degres) -> % d'ouverture, comme vrFonctions.be::positionReelle (sans le 100 - p de ShutterInvert) ; null sans angle
  function ouvertureAngle(angle, incl) {
    if (angle === '' || angle == null || !incl || incl.ouvert == incl.ferme) return null;
    var a = Number(String(angle).replace(',', '.'));      // web_send_decimal : virgule du firmware fr_FR ('47,0')
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
  function ouvertureSvg(svg, g, o, x, plancher, marches, blanche) {
    var l = LARG[o.type] || 64, t = o.type;
    if (t == 'porte' && blanche) {                          // maison : porte blanche, grand vitrage ocre, poignee
      el(g, 'rect', {x: x, y: 88, width: l, height: 108, fill: '#f4f4f2', stroke: '#e6e6e6', 'stroke-width': 3});
      el(g, 'rect', {x: x + 8, y: 96, width: l - 20, height: 76, fill: '#c2902e', stroke: '#ddd', 'stroke-width': 1.5});
      el(g, 'rect', {x: x + l - 8, y: 140, width: 2.5, height: 12, fill: '#333'});
      el(g, 'rect', {x: x - 4, y: 80, width: l + 8, height: 9, fill: '#6b6b6b'});
      return [190, tablier(svg, g, o, x, 89, l, 107, 'vf_lames')];
    }
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

  // Hasard a graine fixe : le decor est le meme a chaque rafraichissement
  function hasard() {
    var graine = 7;
    return function () { graine = (graine * 9301 + 49297) % 233280; return graine / 233280; };
  }

  // Feuilles et fleurs semees dans [x0, x1] x [y0, y1]
  function feuilles(g, alea, x0, x1, y0, y1, n, fleurs, couleurFleur) {
    var verts = ['#3f7d3a', '#4f9444', '#356b31', '#6aa84f', '#8fb34a'], i, x, y;
    for (i = 0; i < n; i++) {
      x = x0 + alea() * (x1 - x0);
      y = y0 + alea() * (y1 - y0);
      el(g, 'ellipse', {cx: x, cy: y, rx: 3.4, ry: 2, fill: verts[Math.floor(alea() * 5)], transform: 'rotate(' + Math.floor(alea() * 180) + ' ' + x + ' ' + y + ')'});
    }
    for (i = 0; i < fleurs; i++)
      el(g, 'circle', {cx: x0 + 2 + alea() * (x1 - x0 - 4), cy: y0 + 2 + alea() * (y1 - y0 - 4), r: 1.6, fill: couleurFleur(i)});
  }

  // Treillis noir en losanges sur le mur, chevrefeuille dessus, coupe net au niveau du haut du rideau
  function chevrefeuille(svg, alea, x0, x1, yHaut, yBas) {
    var g = el(svg, 'g', {'data-decor': 'chevrefeuille'}), i, d;
    var clip = el(el(g, 'defs', {}), 'clipPath', {id: 'vf_treillis'});
    el(clip, 'rect', {x: x0, y: yHaut, width: x1 - x0, height: yBas - yHaut});
    el(g, 'rect', {x: x0, y: yHaut, width: x1 - x0, height: yBas - yHaut, fill: '#1c1c1c'});
    var losanges = el(g, 'g', {'clip-path': 'url(#vf_treillis)'});
    for (d = -120; d < 140; d += 9) {
      el(losanges, 'line', {x1: x0 + d, y1: yHaut, x2: x0 + d + (yBas - yHaut), y2: yBas, stroke: '#3a3a3a', 'stroke-width': 1.2});
      el(losanges, 'line', {x1: x0 + d, y1: yBas, x2: x0 + d + (yBas - yHaut), y2: yHaut, stroke: '#3a3a3a', 'stroke-width': 1.2});
    }
    el(g, 'rect', {x: x0, y: yHaut, width: x1 - x0, height: yBas - yHaut, fill: 'none', stroke: '#111', 'stroke-width': 2});
    for (i = 0; i < 3; i++) {
      var xs = x0 + 6 + i * (x1 - x0 - 12) / 2;
      el(g, 'path', {d: 'M' + xs + ',' + yBas + ' C' + (xs - 6) + ',' + (yBas - 40) + ' ' + (xs + 7) + ',' + (yBas - 70) + ' ' + (xs - 2) + ',' + (yHaut + 2),
        stroke: '#5b4a2e', 'stroke-width': 1.6, fill: 'none'});
    }
    feuilles(g, alea, x0 - 2, x1 + 2, yHaut + 2, yBas - 4, 110, 18, function (f) { return f % 3 ? '#f3e6a8' : '#f2b8c6'; });
  }

  // Porte blanche a grand vitrage, poignee a droite
  function portePleine(svg, px) {
    var g = el(svg, 'g', {'data-decor': 'porte'});
    el(g, 'rect', {x: px, y: 94, width: 50, height: 102, fill: '#f2f2f0', stroke: '#c8c8c4', 'stroke-width': 2});
    el(g, 'rect', {x: px + 6, y: 100, width: 36, height: 56, fill: '#2b2f33', stroke: '#ddd', 'stroke-width': 1.5});
    el(g, 'rect', {x: px + 6, y: 162, width: 36, height: 28, fill: 'none', stroke: '#d6d6d2', 'stroke-width': 1.5});
    el(g, 'rect', {x: px + 44, y: 150, width: 2.5, height: 12, rx: 1, fill: '#9a9a9a'});
  }

  // Pergola en bois (deux poteaux, traverse, treillis contre le mur) ; jasmin a fleurs blanches qui deborde du coin du mur sous le toit
  function pergola(svg, alea, xMur, yToit, yBas) {
    var g = el(svg, 'g', {'data-decor': 'pergola'}), xa = xMur + 6, xb = xMur + 58, y, x;
    el(g, 'rect', {x: xa - 2, y: 104, width: 18, height: yBas - 104, fill: 'none', stroke: '#8a5a3b', 'stroke-width': 1});
    for (y = 110; y < yBas; y += 8) el(g, 'line', {x1: xa - 2, y1: y, x2: xa + 16, y2: y, stroke: '#8a5a3b', 'stroke-width': 1});
    for (x = xa + 2; x < xa + 16; x += 6) el(g, 'line', {x1: x, y1: 104, x2: x, y2: yBas, stroke: '#8a5a3b', 'stroke-width': 1});
    el(g, 'rect', {x: xa + 16, y: 92, width: 5, height: yBas - 92, fill: '#7a5a43'});
    el(g, 'rect', {x: xb, y: 92, width: 5, height: yBas - 92, fill: '#7a5a43'});
    el(g, 'rect', {x: xa + 8, y: 88, width: xb - xa + 4, height: 5, fill: '#6e5038'});
    for (x = xa + 22; x < xb; x += 9) el(g, 'rect', {x: x, y: 86, width: 3, height: 9, fill: '#6e5038'});
    var blanc = function () { return '#fbfbf2'; };
    feuilles(g, alea, xMur - 22, xMur + 22, yToit + 4, 150, 120, 26, blanc);
    feuilles(g, alea, xa + 10, xb + 12, 78, 106, 70, 14, blanc);
    feuilles(g, alea, xa + 12, xa + 26, 100, yBas - 6, 50, 10, blanc);
    feuilles(g, alea, xb + 2, xb + 30, 60, yBas, 140, 8, blanc);
  }

  // Linteau en arc de briques de champ au-dessus d'une ouverture [x, x + l]
  function arc(svg, x, l, y) {
    el(svg, 'path', {d: 'M' + (x - 6) + ',' + (y + 7) + ' Q' + (x + l / 2) + ',' + (y - 4) + ' ' + (x + l + 6) + ',' + (y + 7) + ' L' + (x + l + 6) + ',' + (y + 1) +
      ' Q' + (x + l / 2) + ',' + (y - 10) + ' ' + (x - 6) + ',' + (y + 1) + ' Z', fill: 'url(#vf_soldat)', stroke: '#7d3f2d', 'stroke-width': 0.6});
  }

  // Maison (fond) : toit en appentis vu de face (rangs de tuiles resserres vers le haut), mur de briques, bande de briques de champ,
  // plancher du grenier, descente d'eau, trottoir, arcs, grille d'aeration, et pres de la porte : numero, boite aux lettres, compteur, applique
  function maisonFond(svg, W, pos) {
    var defs = el(svg, 'defs', {}), b = el(defs, 'pattern', {id: 'vf_brique', width: 16, height: 8, patternUnits: 'userSpaceOnUse'});
    el(b, 'rect', {width: 16, height: 8, fill: '#c9b39c'});
    [[0.5, 0.5, '#a5563f'], [-7.5, 4.5, '#9a4c37'], [8.5, 4.5, '#ad5d45']].forEach(function (r) { el(b, 'rect', {x: r[0], y: r[1], width: 15, height: 3.2, fill: r[2]}); });
    var so = el(defs, 'pattern', {id: 'vf_soldat', width: 4, height: 8, patternUnits: 'userSpaceOnUse'});
    el(so, 'rect', {width: 4, height: 8, fill: '#c9b39c'});
    el(so, 'rect', {x: 0.4, y: 0.4, width: 3.2, height: 7.2, fill: '#97503b'});
    var x0 = 6, x1 = W - 6, yH = 26, yB = 66, y = yB, pas = 7, x, r;
    el(svg, 'polygon', {points: (x0 + 6) + ',' + yH + ' ' + (x1 - 6) + ',' + yH + ' ' + x1 + ',' + yB + ' ' + x0 + ',' + yB, fill: '#3b3b3b', 'data-decor': 'maison'});
    while (y - pas > yH) {
      y -= pas;
      r = (y - yH) / (yB - yH);
      el(svg, 'line', {x1: x0 + 6 * (1 - r), y1: y, x2: x1 - 6 * (1 - r), y2: y, stroke: '#262626', 'stroke-width': 1.2});
      pas = Math.max(3, pas * 0.82);
    }
    for (x = x0 + 4; x < x1; x += 7) el(svg, 'line', {x1: x, y1: yB, x2: x + (x - (x0 + x1) / 2) * -0.03, y2: yH, stroke: '#4a4a4a', 'stroke-width': 0.8});
    [[x0 - 2, yB - 3, x1 - x0 + 4, 5, '#121212'], [10, 68, W - 20, 128, 'url(#vf_brique)'], [10, 150, W - 20, 7, 'url(#vf_soldat)'],
     [10, 66, W - 20, 6, '#c9b79c'], [14, 64, 5, 132, '#1d1d1d'], [0, 196, W, 18, '#8a8a88']].forEach(function (q) {
      el(svg, 'rect', {x: q[0], y: q[1], width: q[2], height: q[3], fill: q[4]});        // gouttiere, mur, bande, plancher, descente, trottoir
    });
    if (pos.fenetre != null) arc(svg, pos.fenetre, LARG.fenetre, 70);
    if (pos.trappe != null) el(svg, 'circle', {cx: pos.trappe + 27, cy: 92, r: 4, fill: '#d6c6a8', stroke: '#9b8a6b'});
    if (pos.porte == null) return;
    var px = pos.porte, pl = LARG.porte;
    arc(svg, px, pl, 72);
    el(svg, 'rect', {x: px - 16, y: 128, width: 12, height: 9, fill: '#f2f2f2', stroke: '#888', 'stroke-width': 0.6});
    el(svg, 'text', {x: px - 10, y: 135.5, 'font-size': 7, 'text-anchor': 'middle', style: 'fill:#222'}).textContent = '45';
    el(svg, 'rect', {x: px - 34, y: 150, width: 22, height: 17, fill: '#efe8d0', stroke: '#b8ad8c', 'stroke-width': 0.8});     // boite aux lettres
    el(svg, 'rect', {x: px - 32, y: 153, width: 18, height: 2, fill: '#b8ad8c'});
    el(svg, 'rect', {x: px - 40, y: 174, width: 15, height: 21, fill: '#c9a14a', stroke: '#8f7030', 'stroke-width': 0.8});     // compteur
    el(svg, 'rect', {x: px + pl + 16, y: 110, width: 7, height: 13, fill: '#2a2a2a'});                                          // applique
    el(svg, 'rect', {x: px + pl + 17.5, y: 113, width: 4, height: 7, fill: '#f0d78a'});
  }

  // Maison (devant les ouvertures) : appui a plantes sous la fenetre, marches devant la porte
  function maisonDevant(svg, pos) {
    var fx = pos.fenetre, px = pos.porte, pl = LARG.porte;
    if (fx != null) {
      el(svg, 'rect', {x: fx - 6, y: 148, width: LARG.fenetre + 12, height: 4, fill: '#ececec'});
      [[6, '#7fa86a'], [30, '#a7b98e'], [52, '#a7b98e'], [72, '#7fa86a']].forEach(function (q) {
        el(svg, 'circle', {cx: fx + q[0], cy: 144, r: 4, fill: q[1]});
        el(svg, 'rect', {x: fx + q[0] - 3, y: 145, width: 6, height: 3, fill: '#666'});
      });
    }
    if (px == null) return;
    el(svg, 'rect', {x: px - 6, y: 196, width: pl + 12, height: 5, fill: '#eeeeea', stroke: '#9a948a', 'stroke-width': 0.6});
    el(svg, 'rect', {x: px - 14, y: 201, width: pl + 28, height: 5, fill: '#e6e3dc', stroke: '#9a948a', 'stroke-width': 0.6});
  }

  // Rapporteur a droite de la trappe : 0 deg (fermee, horizontale) a 90 deg ; aiguille et texte posees par poseAngle
  function rapporteur(g, x) {
    var rp = {cx: x + LARG.trappe + 8, cy: 76, r: 12};
    el(g, 'path', {d: 'M' + (rp.cx + rp.r) + ',' + rp.cy + ' A' + rp.r + ',' + rp.r + ' 0 0 1 ' + rp.cx + ',' + (rp.cy + rp.r) + ' L' + rp.cx + ',' + rp.cy + ' Z',
      fill: 'rgba(30,30,30,0.75)', stroke: '#ddd', 'stroke-width': 1, 'data-rapporteur': ''});
    rp.aiguille = el(g, 'line', {x1: rp.cx, y1: rp.cy, x2: rp.cx + rp.r, y2: rp.cy, stroke: '#ffcc33', 'stroke-width': 2});
    rp.texte = el(g, 'text', {x: rp.cx + 8, y: rp.cy + 24, 'font-size': 10, 'text-anchor': 'middle', style: 'fill:var(--c_txt);stroke:var(--c_bg);stroke-width:3px;paint-order:stroke'});
    poseAngle(rp, null);
    return rp;
  }

  // Angle lu (texte de data-angle, virgule du firmware ; null ou vide = inconnu : aiguille cachee, « ?° ») ; DOM touche au changement
  function poseAngle(rp, angle) {
    var a = angle == null || angle === '' ? NaN : Number(String(angle).replace(',', '.')), k = isNaN(a) ? '?' : String(Math.round(a));
    if (rp.k === k) return;
    rp.k = k;
    var r = (isNaN(a) ? 0 : borne(a * 100 / 90) * 0.9) * Math.PI / 180;
    rp.aiguille.setAttribute('x2', rp.cx + rp.r * Math.cos(r));
    rp.aiguille.setAttribute('y2', rp.cy + rp.r * Math.sin(r));
    rp.aiguille.style.display = isNaN(a) ? 'none' : '';
    rp.texte.textContent = k + '°';
  }

  // Camera de facade (a gauche, sous le toit) : boitier, objectif, voyant ; clic = confirmation puis POST /volets action=camera
  function camera(svg, nom, dy) {
    var c = {g: el(svg, 'g', {'data-camera': '', style: 'cursor:pointer'}), nom: nom || 'Caméra de façade'};
    if (dy) c.g.setAttribute('transform', 'translate(0,' + dy + ')');             // garage : remontee sous le toit en appentis
    el(c.g, 'rect', {x: 24, y: 74, width: 10, height: 8, rx: 2, fill: '#e8e8e8'});
    el(c.g, 'circle', {cx: 29, cy: 84, r: 3, fill: '#333'});
    c.halo = el(c.g, 'circle', {cx: 37, cy: 76, r: 5, fill: 'rgba(60,176,74,0.35)', style: 'display:none'});
    c.voyant = el(c.g, 'circle', {cx: 37, cy: 76, r: 2.4, fill: '#777', stroke: '#eee', 'stroke-width': 0.6, style: 'transition:fill 0.3s'});
    c.titre = el(c.g, 'title', {});
    c.g.onclick = function () {
      if (c.s != 'allumée' && c.s != 'éteinte') { window.alert(c.nom + ' : état inconnu, commande impossible pour le moment'); return; }
      var allumer = c.s == 'éteinte';
      if (!window.confirm((allumer ? 'Allumer' : 'Éteindre') + ' : ' + c.nom + ' ?')) return;
      fetch('/volets', {method: 'POST', body: new URLSearchParams({action: 'camera', etat: allumer ? 'ON' : 'OFF'})})
        .then(function (r) { return r.json(); }).then(function (j) { if (j && !j.ok && window.alert) window.alert(j.message); },
          function () { window.alert(c.nom + ' : pas de réponse de la carte, commande non vérifiée'); });
    };
    poseCamera(c, null);
    return c;
  }

  // Etat de la camera : 'ON' (voyant vert et halo), 'OFF' (gris), autre = inconnu (gris) ; DOM touche au changement
  function poseCamera(c, etat) {
    var s = etat == 'ON' ? 'allumée' : (etat == 'OFF' ? 'éteinte' : 'état inconnu');
    if (c.s === s) return;
    c.s = s;
    c.voyant.style.fill = etat == 'ON' ? VERT : '#777';
    c.halo.style.display = etat == 'ON' ? '' : 'none';
    c.titre.textContent = c.nom + ' : ' + s + ' (clic pour ' + (etat == 'ON' ? 'éteindre' : 'allumer') + ')';
  }

  // Projecteur de facade (garage, sous le toit cote pergola, variante B validee le 2026-11-14) : lanterne suspendue par une tige ;
  // (x, y) = axe et dessous du toit ; allumee : globe jaune et halo ; clic = confirmation puis POST /volets action=lampe
  function lampe(svg, nom, x, y) {
    var c = {g: el(svg, 'g', {'data-lampe': '', style: 'cursor:pointer', transform: 'translate(' + (x - 318) + ',' + (y - 57) + ')'}), nom: nom || 'Projecteur de façade'};
    c.halo = el(c.g, 'circle', {cx: 318, cy: 75, r: 20, fill: 'rgba(255,213,74,0.30)', style: 'display:none'});
    el(c.g, 'line', {x1: 318, y1: 57, x2: 318, y2: 64, stroke: '#555', 'stroke-width': 1.5});
    el(c.g, 'path', {d: 'M311,64 h14 l-2,4 h-10 z', fill: '#3d3d3d'});
    c.globe = el(c.g, 'rect', {x: 312, y: 68, width: 12, height: 13, rx: 2, fill: '#a9adb0', stroke: '#555', 'stroke-width': 1.2});
    el(c.g, 'path', {d: 'M311,81 h14 l-2,3 h-10 z', fill: '#3d3d3d'});
    c.filament = el(c.g, 'circle', {cx: 318, cy: 74.5, r: 2.2, fill: '#fff', style: 'display:none'});
    c.titre = el(c.g, 'title', {});
    c.g.onclick = function () {
      if (c.s != 'allumé' && c.s != 'éteint') { window.alert(c.nom + ' : état inconnu, commande impossible pour le moment'); return; }
      var allumer = c.s == 'éteint';
      if (!window.confirm((allumer ? 'Allumer' : 'Éteindre') + ' : ' + c.nom + ' ?')) return;
      fetch('/volets', {method: 'POST', body: new URLSearchParams({action: 'lampe', etat: allumer ? 'ON' : 'OFF'})})
        .then(function (r) { return r.json(); }).then(function (j) { if (j && !j.ok && window.alert) window.alert(j.message); },
          function () { window.alert(c.nom + ' : pas de réponse de la carte, commande non vérifiée'); });
    };
    poseLampe(c, null);
    return c;
  }

  // Etat du projecteur : 'ON' (globe jaune et halo), 'OFF' (globe gris), autre = inconnu (gris) ; DOM touche au changement
  function poseLampe(c, etat) {
    var s = etat == 'ON' ? 'allumé' : (etat == 'OFF' ? 'éteint' : 'état inconnu');
    if (c.s === s) return;
    c.s = s;
    c.globe.style.fill = etat == 'ON' ? '#ffd54a' : '#a9adb0';
    c.halo.style.display = c.filament.style.display = etat == 'ON' ? '' : 'none';
    c.titre.textContent = c.nom + ' : ' + s + ' (clic pour ' + (etat == 'ON' ? 'éteindre' : 'allumer') + ')';
  }

  // Pastille d'un fin de course sur le rail droit : boitier + levier (pivot au bord gauche, pointe contre le rail) ; rend ses elements
  function capteur(g, cle, x, y, nom) {
    var c = {nom: nom || 'Capteur ' + cle, g: el(g, 'g', {'data-capteur': cle})};
    c.boitier = el(c.g, 'rect', {x: x - 4, y: y - 6, width: 8, height: 12, rx: 2, fill: GRIS, stroke: '#eee', 'stroke-width': 1.5, style: 'transition:fill 0.3s'});
    c.levier = el(c.g, 'line', {x1: x - 4, y1: y, x2: x - 10, y2: y, stroke: '#eee', 'stroke-width': 2, 'stroke-linecap': 'round',
      style: 'transition:transform 0.3s;transform-origin:' + (x - 4) + 'px ' + y + 'px'});
    c.titre = el(c.boitier, 'title', {});
    return c;
  }

  // Pose l'etat d'une pastille : 'ON' = contact ferme, 'OFF' = ouvert, autre = inconnu ; DOM touche seulement si l'etat change
  function poseCapteur(c, etat) {
    var s = etat == 'ON' ? 'ferme' : (etat == 'OFF' ? 'ouvert' : 'inconnu');
    if (c.s === s) return;
    c.s = s;
    c.boitier.style.fill = s == 'ferme' ? VERT : (s == 'ouvert' ? ROUGE : GRIS);
    c.levier.style.transform = 'rotate(' + (s == 'ferme' ? 0 : (s == 'ouvert' ? 35 : 18)) + 'deg)';
    c.titre.textContent = c.nom + ' : contact ' + (s == 'ferme' ? 'fermé' : (s == 'ouvert' ? 'ouvert' : 'inconnu'));
  }

  // etats : {ouverture, fermeture} ('ON'|'OFF', cle absente = inconnu) ou null (lecture en echec)
  function poseCapteurs(v, etats) {
    poseCapteur(v.capteurs.ouverture, etats && etats.ouverture);
    poseCapteur(v.capteurs.fermeture, etats && etats.fermeture);
  }

  // Etats a afficher pour v : reponse de sa 'source' si elle porte 'capteurs', sinon lecture /volets?f=capteurs (vf = {j: table par id ou null})
  function etatsCapteurs(v, vf) {
    if (v.o.source && v.lu && v.lu.capteurs) return v.lu.capteurs;
    if (v.o.source || !vf || !vf.j) return null;
    return vf.j[String(v.o.id)] || {};
  }

  // Coherence de la position LUE (% d'ouverture, null si inconnue) avec les contacts. suivi = {ouverture, fermeture} : instant de
  // debut de l'incoherence en cours (null sinon), tenu par l'appelant. Rend {ouverture, fermeture} : vrai si incoherent depuis plus de DELAI.
  // Un contact inconnu (absent ou lecture en echec) ne juge pas : seul un OFF contredit une position, seuls deux ON se contredisent.
  function coherence(suivi, position, etats, t) {
    var e = etats || {}, deux = e.ouverture == 'ON' && e.fermeture == 'ON', r = {};
    var cause = {
      ouverture: deux || (position != null && position >= 99 && e.ouverture == 'OFF'),
      fermeture: deux || (position != null && position <= 1 && e.fermeture == 'OFF')
    };
    ['ouverture', 'fermeture'].forEach(function (k) {
      if (!cause[k]) suivi[k] = null;
      else if (suivi[k] == null || t < suivi[k]) suivi[k] = t;
      r[k] = !!cause[k] && t - suivi[k] > DELAI;
    });
    return r;
  }

  // Clignotement a 2 Hz des pastilles en cause ; opacite rendue a la normale quand le verdict se leve
  function clignote(v, verdict, t) {
    ['ouverture', 'fermeture'].forEach(function (k) {
      var c = v.capteurs[k], voulue = verdict[k] ? (Math.floor(t / 250) % 2 ? '0.25' : '1') : '';
      if (c.op === voulue || (c.op == null && voulue === '')) return;
      c.op = voulue;
      c.g.style.opacity = voulue;
    });
  }

  // Dessine la facade dans 'conteneur' ; chaque ouverture : <g data-id data-ouverture>, son texte « nom NN % »
  function dessine(conteneur, facade) {
    var ouv = facade.ouvertures || [], toit = facade.toit, maison = toit == 'deuxPans' || toit == 'unPan';
    var somme = 40 * (ouv.length - 1);
    ouv.forEach(function (o) { somme += LARG[o.type] || 64; });
    var W = Math.max(maison ? 300 : 240, somme + 80), x = (W - somme) / 2;
    // Decor (toit unPan seulement) : rideau a x = 70 ; porte 20 apres le dernier volet ; mur arrete avant la pergola
    var listeDecor = Array.isArray(facade.decor) ? facade.decor : [];
    var decor = toit == 'unPan' ? listeDecor : [], porte = decor.indexOf('porte') >= 0, perg = decor.indexOf('pergola') >= 0;
    var xMur = W - 20, alea = hasard(), maisonD = listeDecor.indexOf('maison') >= 0, pos = {};
    if (maisonD) {
      decor = [];
      W = 400;
      ouv.forEach(function (o) { if (POS[o.type] != null) pos[o.type] = POS[o.type]; });
    }
    if (decor.length) {
      x = 70;
      xMur = perg ? 70 + somme + 20 + (porte ? 70 : 0) : W - 20;
      W = Math.max(420, perg ? xMur + 84 : 70 + somme + (porte ? 70 : 0) + 80);
      if (!perg) xMur = W - 20;
    }
    var plancher = maison ? [66, 72] : [30, 38];
    var marches = function (xm) { return 100 + 9 * Math.floor(xm / 24); };
    while (conteneur.firstChild) conteneur.removeChild(conteneur.firstChild);
    var svg = el(conteneur, 'svg', {viewBox: '0 0 ' + W + (maisonD ? ' 214' : ' 200'), width: '100%', style: 'display:block;margin:8px 0'});
    var defs = el(svg, 'defs', {});
    [['vf_lames', 10, 8, 6.5, 1.5, '#9aa3ab', '#6f777e'], ['vf_lamesG', 12, 10, 8, 2, '#b4bcc3', '#7d858c']].forEach(function (m) {
      var p = el(defs, 'pattern', {id: m[0], width: m[1], height: m[2], patternUnits: 'userSpaceOnUse'});
      el(p, 'rect', {width: m[1], height: m[2], fill: m[5]});
      el(p, 'rect', {y: m[3], width: m[1], height: m[4], fill: m[6]});
    });
    var trappe = ouv.some(function (o) { return o.type == 'trappe' || o.type == 'trappeEchelle'; });
    if (maisonD) {
      maisonFond(svg, W, pos);
    } else if (toit == 'deuxPans') {
      el(svg, 'polygon', {points: '10,66 ' + W / 2 + ',8 ' + (W - 10) + ',66', fill: '#9c4b3a'});
      el(svg, 'rect', {x: 20, y: 66, width: W - 40, height: 130, fill: '#d8cbb0'});
    } else if (toit == 'unPan') {
      if (perg) {                                           // mur et toit arretes avant la pergola
        var yd = 44 + 16 * (xMur - 20) / (W - 40);
        el(svg, 'polygon', {points: '20,44 ' + xMur + ',' + yd + ' ' + xMur + ',196 20,196', fill: '#d8cbb0'});
        el(svg, 'polygon', {points: '6,36 ' + (xMur + 12) + ',' + (yd - 8) + ' ' + (xMur + 12) + ',' + (yd + 1) + ' 6,45', fill: '#6e6e6e'});
      } else {
        el(svg, 'polygon', {points: '20,44 ' + (W - 20) + ',60 ' + (W - 20) + ',196 20,196', fill: '#d8cbb0'});
        el(svg, 'polygon', {points: '6,36 ' + (W - 6) + ',54 ' + (W - 6) + ',63 6,45', fill: '#6e6e6e'});
      }
    } else {
      el(svg, 'rect', {x: 0, y: 0, width: W, height: 30, fill: '#e8e1d4'});
      el(svg, 'rect', {x: 0, y: 38, width: W, height: 154, fill: '#3b3631'});
      el(svg, 'rect', {x: 0, y: 192, width: W, height: 8, fill: '#777'});
    }
    if (trappe && !maisonD) el(svg, 'rect', {x: maison ? 20 : 0, y: plancher[0], width: maison ? W - 40 : W, height: plancher[1] - plancher[0], fill: '#c9b79c'});
    if (ouv.some(function (o) { return o.type == 'trappeEchelle'; })) {       // escalier en bois fixe, de gauche (haut) a droite
      var pts = '';
      for (var xm = 0; xm < W; xm += 24) pts += xm + ',' + marches(xm) + ' ' + Math.min(W, xm + 24) + ',' + marches(xm) + ' ';
      el(svg, 'polygon', {points: pts + W + ',192 0,192', fill: '#8a5a3b', stroke: '#5e3c26'});
      el(svg, 'line', {x1: 0, y1: 96, x2: W, y2: marches(W - 1) - 4, stroke: '#6b4429', 'stroke-width': 3});      // rampe
    }
    if (decor.indexOf('chevrefeuille') >= 0) chevrefeuille(svg, alea, 26, 56, 84, 196);
    if ((maisonD || toit == 'unPan') && facade.camera) svg.camera = camera(svg, facade.camera.nom, maisonD ? 0 : -24);
    if (toit == 'unPan' && facade.lampe) {
      var lx = xMur - 18;
      svg.lampe = lampe(svg, facade.lampe.nom, lx, 45 + 16 * (lx - 20) / (W - 40));
    }
    svg.volets = ouv.map(function (o) {
      if (maisonD && POS[o.type] != null) x = POS[o.type];
      var g = el(svg, 'g', {'data-id': o.id, 'data-ouverture': ''});
      var r = ouvertureSvg(svg, g, o, x, plancher, marches, maisonD);
      var texte = el(svg, 'text', {x: x + (LARG[o.type] || 64) / 2, y: r[0], 'font-size': 11, 'text-anchor': 'middle',
        style: 'fill:var(--c_txt);stroke:var(--c_bg);stroke-width:3px;paint-order:stroke'});
      texte.textContent = String(o.nom || '').replace(/^volet( roulant)?\s+/i, '') + ' ';
      var pct = el(texte, 'tspan', {'class': 'vf_pct'}), cause = el(texte, 'tspan', {});
      var v = {o: o, g: g, pose: r[1], pct: pct, cause: cause};
      if (o.finsDeCourse && o.type == 'garage') {         // fins de course sur le rail droit : ouverture en haut, fermeture en bas
        var f = o.finsDeCourse, xr = x + LARG.garage + 12;
        v.capteurs = {ouverture: capteur(g, 'ouverture', xr, 102, f.ouverture), fermeture: capteur(g, 'fermeture', xr, 187, f.fermeture)};
        v.suivi = {};
      }
      if (maisonD && o.type == 'trappe') v.rapporteur = rapporteur(svg, x);
      x += (LARG[o.type] || 64) + 40;
      return v;
    });
    if (maisonD) maisonDevant(svg, pos);
    if (porte) portePleine(svg, x - 20);
    if (perg) pergola(svg, alea, xMur, 44 + 16 * (xMur - 20) / (W - 40), 196);
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
      v.pct.style.fill = v.cause.style.fill = bloque ? 'var(--c_txtwrn, ' + ROUGE + ')' : '';
      v.cause.textContent = bloque ? ' ' + (bloque == 'bloque' ? 'bloqué' : bloque) : '';
    }
    if (v.g.getAttribute('data-ouverture') !== String(n)) {
      v.g.setAttribute('data-ouverture', n);
      v.pct.textContent = n + ' %';
    }
  }

  // Ouverture a 'source' : derniere reponse dans v.lu ; erreur reseau, reponse illisible ou sans reponse en 4 s = muet, position
  // inconnue (le delai garde la chaine vivante si la carte ne repond jamais) ; ouverture non numerique = inconnue
  function interroge(v, periode) {
    var suite = function () { setTimeout(function () { interroge(v, periode); }, periode); };
    var options = {cache: 'no-store'};
    if (window.AbortSignal && AbortSignal.timeout) options.signal = AbortSignal.timeout(4000);
    fetch(v.o.source, options).then(function (r) { return r.json(); })
      .then(function (j) {
        var n = j && j.ouverture != null ? Number(j.ouverture) : NaN;
        v.lu = {ouverture: isNaN(n) ? null : n, muet: !!(j && j.muet), capteurs: j && j.capteurs && typeof j.capteurs == 'object' ? j.capteurs : null};
      }, function () { v.lu = {ouverture: null, muet: true}; }).then(suite, suite);
  }

  // Grise une ouverture a 'source' dont le maitre ne repond pas
  function grise(v, muet) {
    var t = muet ? ' (maître muet)' : '';
    if (v.cause.textContent === t) return;
    v.cause.textContent = t;
    v.g.style.opacity = muet ? '0.45' : '';
  }

  // Etats des fins de course du P4 : /volets?f=capteurs ({id du volet: {ouverture, fermeture}}), memes regles que interroge (delai de 4 s,
  // requete suivante apres la reponse) ; lecture.j reste null tant qu'elle n'a pas reussi, et le redevient en cas d'echec
  function lisCapteurs(lecture, periode) {
    var suite = function () { setTimeout(function () { lisCapteurs(lecture, periode); }, periode); };
    var options = {cache: 'no-store'};
    if (window.AbortSignal && AbortSignal.timeout) options.signal = AbortSignal.timeout(4000);
    fetch('/volets?f=capteurs', options).then(function (r) { return r.json(); })
      .then(function (j) { lecture.j = j && typeof j == 'object' ? j : null; }, function () { lecture.j = null; }).then(suite, suite);
  }

  // Position reelle lue d'une ouverture : [% d'ouverture, cause de blocage] ou null (ni angle, ni curseur)
  function lit(v) {
    var o = v.o, b = o.inclinaison && Number.isInteger(o.id) ? document.querySelector("[data-vi='" + o.id + "']") : null;   // table remplacee a chaque rafraichissement
    var a = b ? ouvertureAngle(b.getAttribute('data-angle'), o.inclinaison) : null, bloque = b ? b.getAttribute('data-bloque') || '' : '';
    if (a != null) return [a, bloque];
    var c = document.getElementById('s27' + o.id);
    return c ? [ouverture(c.value, o.inverse), bloque] : null;
  }

  // Une image d'une ouverture : position lue -> dessin (poursuite) ; pose v.lue
  function anime(v, dt) {
    if (v.o.source) {
      if (!v.lu) return;
      grise(v, v.lu.muet);
      if (v.lu.ouverture == null) {                         // position inconnue : dessin fige, « ? » a la place du %
        if (v.pct.textContent !== '?') {                    // une fois : DOM inchange ensuite
          if (v.dessinee == null) v.dessinee = 0;
          pose(v, v.dessinee, '');
          v.p = null;
          v.g.setAttribute('data-ouverture', '');
          v.pct.textContent = '?';
        }
        return;
      }
    }
    var l = v.o.source ? [borne(v.lu.ouverture), ''] : lit(v);
    if (!l) return;
    v.lue = l[0];
    v.dessinee = poursuit(v.dessinee, l[0], dt, v.o);
    pose(v, v.dessinee, l[1]);
  }

  // Angle brut de la balise data-vi de l'ouverture id (table remplacee a chaque rafraichissement), null sans balise
  function angleLu(id) {
    var b = Number.isInteger(id) ? document.querySelector("[data-vi='" + id + "']") : null;
    return b ? b.getAttribute('data-angle') : null;
  }

  // Pastilles d'une ouverture : etats lus, couleurs, clignotement si la position lue les contredit plus de 6 s
  function suitCapteurs(v, t, lecture) {
    var e = etatsCapteurs(v, lecture);
    poseCapteurs(v, e);
    clignote(v, coherence(v.suivi, v.lue, e, t), t);
  }

  // Insere le dessin juste apres la table des curseurs (#s271) et l'anime ; rien sans #s271, sauf ouverture a 'source' (dessin dans #vf)
  function demarre(facade) {
    var s1 = document.getElementById('s271'), table = s1 && s1.closest('table'), vf = document.getElementById('vf');
    if (!facade || !facade.ouvertures || !facade.ouvertures.length) return null;
    var source = facade.ouvertures.some(function (o) { return o.source; });
    if (!table && !(source && vf)) return null;
    if (table) {
      vf = vf || document.createElement('div');
      table.parentNode.insertBefore(vf, table.nextSibling);
    }
    var svg = dessine(vf, facade), avant = null;
    var periode = facade.rafraichissement > 0 ? facade.rafraichissement : 2345, lecture = {j: null};
    svg.volets.forEach(function (v) { if (v.o.source) interroge(v, periode); });
    if (svg.camera || svg.lampe || svg.volets.some(function (v) { return v.capteurs && !v.o.source; })) lisCapteurs(lecture, periode);
    function image() {
      requestAnimationFrame(image);                       // en tete : une exception de lit ou pose n'arrete pas l'animation
      var t = performance.now(), dt = avant == null ? 0 : t - avant;
      avant = t;
      svg.volets.forEach(function (v) {
        v.lue = null;                                       // position LUE (pas la dessinee), posee par anime
        try { anime(v, dt); } finally {
          if (v.capteurs) suitCapteurs(v, t, lecture);
          if (v.rapporteur) poseAngle(v.rapporteur, angleLu(v.o.id));
        }
      });
      if (svg.camera) poseCamera(svg.camera, lecture.j && lecture.j.camera);
      if (svg.lampe) poseLampe(svg.lampe, lecture.j && lecture.j.lampe);
    }
    image();
    return svg;
  }

  window.Volets = {ouverture: ouverture, ouvertureAngle: ouvertureAngle, poursuit: poursuit, dessine: dessine, demarre: demarre,
    coherence: coherence, poseCapteurs: poseCapteurs, clignote: clignote, etatsCapteurs: etatsCapteurs, poseAngle: poseAngle, poseCamera: poseCamera, poseLampe: poseLampe};
  if (typeof document !== 'undefined' && window.VOLETS) {
    try { demarre(window.VOLETS); } catch (e) { if (window.console) console.error('volets.js : ' + e.message); }
  }
})();
