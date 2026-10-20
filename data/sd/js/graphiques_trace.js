// graphiques_trace.js - Trace ECharts d'un graphique de la page /graphiques (2026-10-19, plan graphiques-web A9)
// Charge AVANT graphiques.js (data/fs/graphiquesFonctions.be l'envoie en premier) : definit window.GraphiquesTrace,
// utilise par graphiques.js. Ne lit rien sur la carte : il recoit un bloc deja compose :
//   b.courbes : [{nom (chemin), legende, unite, couleur, type, moy, min, max}] ; b.x : instants (s) ;
//   b.titreVue : sous-titre ; b.suit : vrai si l'axe des temps va jusqu'a maintenant ; b.periode ; b.absentes.
// Types d'une courbe : courbe, barres, escalier, aire ; le type d'une serie prime sur celui du graphique
// (graphique combine). En vue mois, bande min-max pour les courbes et les aires ; barres et escalier sur la moyenne.
window.GraphiquesTrace = (function () {
  'use strict';
  var LARGEUR_AXE = 56;            // px reserves par axe Y
  var TYPES = ['courbe', 'barres', 'escalier', 'aire'];
  var fmtHeure = new Intl.DateTimeFormat('fr-FR', {hour: '2-digit', minute: '2-digit'});
  var fmtJour = new Intl.DateTimeFormat('fr-FR', {weekday: 'short', day: '2-digit', month: '2-digit'});
  var fmtComplet = new Intl.DateTimeFormat('fr-FR', {weekday: 'short', day: '2-digit', month: '2-digit',
                                                     hour: '2-digit', minute: '2-digit', second: '2-digit'});
  var fmtNombre = new Intl.NumberFormat('fr-FR', {maximumFractionDigits: 2});

  function echappe(s) {
    return String(s).replace(/[&<>"']/g, function (c) { return '&#' + c.charCodeAt(0) + ';'; });
  }

  function transparence(hex, alpha) {
    var n = parseInt(hex.slice(1), 16);
    return 'rgba(' + (n >> 16 & 255) + ',' + (n >> 8 & 255) + ',' + (n & 255) + ',' + alpha + ')';
  }

  // Couleur du theme Tasmota (variables CSS), pour que les axes restent lisibles en theme sombre
  function couleurTheme(variable, defaut) {
    try {
      var v = getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
      return v || defaut;
    } catch (e) { return defaut; }
  }

  // Echelle Y d'une unite : du min au max des valeurs de ses series (visibles, dans la fenetre zoomee), 5 % de
  // marge ; elle ne descend pas sous zero quand toutes les valeurs sont positives ; une valeur constante garde
  // une hauteur lisible
  function etendue(v) {
    if (!isFinite(v.min) || !isFinite(v.max)) return [0, 1];
    if (v.min === v.max) { var m = Math.abs(v.min) * 0.05 || 1; return [v.min - m, v.max + m]; }
    var marge = (v.max - v.min) * 0.05, bas = v.min - marge;
    return [(v.min >= 0 && bas < 0) ? 0 : bas, v.max + marge];
  }

  // Unites du graphique : les plus partagees d'abord, « sans unite » en dernier ; un axe Y chacune, alternativement a
  // gauche et a droite
  function unitesDe(courbes) {
    var unites = [], compte = {};
    courbes.forEach(function (c) {
      if (unites.indexOf(c.unite) < 0) unites.push(c.unite);
      compte[c.unite] = (compte[c.unite] || 0) + 1;
    });
    return unites.sort(function (a, b) {
      if ((a === '') !== (b === '')) return a === '' ? 1 : -1;
      return compte[b] - compte[a];
    });
  }

  // Series ECharts d'une courbe : son trace selon son type, puis la bande min-max (courbe et aire en vue mois)
  function seriesDe(c, k, axe, ms) {
    var points = ms.map(function (t, i) { return [t, c.moy[i]]; });
    var s = {id: 'courbe-' + k, name: c.legende, yAxisIndex: axe, color: c.couleur, data: points};
    if (c.type === 'barres') {
      s.type = 'bar';
      s.barMaxWidth = 14;
    } else {
      s.type = 'line';
      s.showSymbol = false;
      s.connectNulls = false;
      s.lineStyle = {width: 2};
      if (c.type === 'escalier') s.step = 'end';
      if (c.type === 'aire') s.areaStyle = {color: transparence(c.couleur, 0.25)};
    }
    var liste = [s];
    if (c.min && c.max && (c.type === 'courbe' || c.type === 'aire')) {
      // min empile avec l'ecart, meme nom : la legende masque les trois
      liste.push({id: 'bande-min-' + k, name: c.legende, type: 'line', yAxisIndex: axe, stack: 'bande' + k,
                  showSymbol: false, silent: true, lineStyle: {opacity: 0}, color: c.couleur,
                  data: ms.map(function (t, i) { return [t, c.min[i]]; })});
      liste.push({id: 'bande-ecart-' + k, name: c.legende, type: 'line', yAxisIndex: axe, stack: 'bande' + k,
                  showSymbol: false, silent: true, lineStyle: {opacity: 0}, color: c.couleur,
                  areaStyle: {color: transparence(c.couleur, 0.2)},
                  data: ms.map(function (t, i) {
                    return [t, (c.min[i] === null || c.max[i] === null) ? null : c.max[i] - c.min[i]];
                  })});
    }
    return liste;
  }

  // Infobulle : date complete puis une ligne par courbe (les series de la bande min-max sont omises)
  function infobulle(params) {
    if (!params || !params.length) return '';
    var lignes = [echappe(fmtComplet.format(new Date(params[0].axisValue)))];
    params.forEach(function (p) {
      if (String(p.seriesId).indexOf('bande-') === 0) return;
      var v = p.value ? p.value[1] : null;
      lignes.push(p.marker + ' ' + echappe(p.seriesName) + ' : ' + (v === null || v === undefined ? '--' : fmtNombre.format(v)));
    });
    return lignes.join('<br>');
  }

  // Options ECharts completes d'un bloc ; masquees = chemins decoches dans la legende
  function option(b, masquees) {
    var texte = couleurTheme('--c_txt', '#888'), grille = 'rgba(128,128,128,0.25)';
    var unites = b.unites = unitesDe(b.courbes);
    var gauche = Math.ceil(unites.length / 2), droite = Math.floor(unites.length / 2);
    var ms = b.x.map(function (t) { return t * 1000; });
    var series = [], selection = {};
    b.courbes.forEach(function (c, k) {
      selection[c.legende] = masquees.indexOf(c.nom) < 0;
      series = series.concat(seriesDe(c, k, unites.indexOf(c.unite), ms));
    });
    return {
      animation: false,
      title: {text: b.titreVue, left: 'center', top: 2, textStyle: {color: texte, fontSize: 13, fontWeight: 'normal'}},
      grid: {left: 16 + LARGEUR_AXE * gauche, right: 16 + LARGEUR_AXE * droite, top: 46, bottom: 58},
      tooltip: {trigger: 'axis', confine: true, formatter: infobulle},
      legend: {type: 'scroll', bottom: 0, data: b.courbes.map(function (c) { return c.legende; }), selected: selection,
               textStyle: {color: texte}},
      dataZoom: [{type: 'inside'}],
      xAxis: {type: 'time', max: b.suit ? function (v) { return Math.max(v.max, Date.now()); } : null,
              axisLine: {lineStyle: {color: texte}}, splitLine: {show: false},
              axisLabel: {color: texte, hideOverlap: true, formatter: function (v) {
                var d = new Date(v);
                return (d.getHours() === 0 && d.getMinutes() === 0) ? fmtJour.format(d) : fmtHeure.format(d);
              }}},
      yAxis: unites.map(function (unite, i) {
        return {type: 'value', name: unite, scale: true, position: i % 2 === 0 ? 'left' : 'right',
                offset: Math.floor(i / 2) * LARGEUR_AXE, alignTicks: false,
                min: function (v) { return etendue(v)[0]; }, max: function (v) { return etendue(v)[1]; },
                nameTextStyle: {color: texte}, axisLine: {show: true, lineStyle: {color: texte}},
                axisLabel: {color: texte, formatter: function (v) { return fmtNombre.format(v); }},
                splitLine: {show: i === 0, lineStyle: {color: grille}}};
      }),
      series: series
    };
  }

  var ATTRIBUTS = ['data-titre', 'data-legende', 'data-series', 'data-types', 'data-rendu', 'data-bandes', 'data-fin', 'data-points', 'data-echelles',
                   'data-derniers', 'data-axe-x', 'data-periode', 'data-absentes'];

  // Etat du trace, lisible dans le DOM (diagnostic, banc) : ECharts dessine dans un canvas
  function expose(b, masquees) {
    var t = b.trace;
    if (!b.graphique) {
      ATTRIBUTS.forEach(function (a) { t.removeAttribute(a); });
      return;
    }
    t.setAttribute('data-titre', b.titreVue);
    t.setAttribute('data-periode', b.periode);
    t.setAttribute('data-absentes', JSON.stringify(b.absentes || []));
    t.setAttribute('data-series', JSON.stringify(b.courbes.map(function (c) { return c.legende; })));
    t.setAttribute('data-types', JSON.stringify(b.courbes.map(function (c) { return c.type; })));
    // Ce qui est vraiment donne a ECharts : type de chaque courbe (line, line:step, line:area, bar) et bandes min-max
    var series = (b.option && b.option.series) || [];
    t.setAttribute('data-rendu', JSON.stringify(series.filter(function (s) { return s.id.indexOf('courbe-') === 0; })
      .map(function (s) { return s.type + (s.step ? ':step' : '') + (s.areaStyle ? ':area' : ''); })));
    t.setAttribute('data-bandes', String(series.filter(function (s) { return s.id.indexOf('bande-ecart-') === 0; }).length));
    t.setAttribute('data-legende', JSON.stringify(b.courbes.filter(function (c) {
      return masquees.indexOf(c.nom) < 0;
    }).map(function (c) { return c.legende; })));
    t.setAttribute('data-fin', String(b.x[b.x.length - 1]));
    t.setAttribute('data-points', String(b.x.length));
    var derniers = {};
    b.courbes.forEach(function (c) {
      for (var i = c.moy.length - 1; i >= 0; i--) if (c.moy[i] !== null) { derniers[c.legende] = c.moy[i]; break; }
    });
    t.setAttribute('data-derniers', JSON.stringify(derniers));
    var bornes = {}, axeX = null;
    try {
      var modele = b.graphique.getModel();
      b.unites.forEach(function (unite, i) {
        var e = modele.getComponent('yAxis', i).axis.scale.getExtent();
        bornes[unite] = [e[0], e[1]];
      });
      axeX = modele.getComponent('xAxis', 0).axis.scale.getExtent();
    } catch (e) { /* API interne d'ECharts indisponible : bornes non exposees */ }
    t.setAttribute('data-echelles', JSON.stringify(bornes));
    t.setAttribute('data-axe-x', JSON.stringify(axeX));
  }

  // Dessine (ou efface) le graphique d'un bloc ; surLegende(selection) appele a chaque clic dans la legende
  function dessine(b, masquees, surLegende) {
    if (!b.courbes.length) {
      if (b.graphique) { b.graphique.dispose(); b.graphique = null; }
    } else {
      if (!b.graphique) {
        b.graphique = echarts.init(b.trace, null, {renderer: 'canvas'});
        b.graphique.on('legendselectchanged', function (e) { surLegende(b, e.selected); });
      }
      b.option = option(b, masquees);
      b.graphique.setOption(b.option, {replaceMerge: ['series', 'yAxis']});
    }
    expose(b, masquees);
  }

  return {TYPES: TYPES, dessine: dessine, expose: expose, etendue: etendue, echappe: echappe};
})();
