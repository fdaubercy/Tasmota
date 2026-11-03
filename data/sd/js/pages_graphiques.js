// pages_graphiques.js - Trace commun des pages de graphiques d'une carte (atelier des graphiques, plan A3)
// Envoye APRES pages_graphiques_formule.js dans le meme <script> par data/fs/pagesGraphiques.be::pagesGraphiques_page,
// qui pose avant window.PAGE_GRAPHIQUES = {page, calculees, bibliotheque, extension, historique}. Le meme fichier sert
// l'apercu de l'atelier (spec 4.4 « Apercu = le vrai moteur ») : l'atelier appelle PagesGraphiques.page() lui-meme.
//
// PagesGraphiques.optionDe(graphique, donnees, theme) -> option ECharts, ou {svg: "..."} pour « demi-cercle » (pure : ni
//   DOM ni reseau, testee par test_pages_graphiques.mjs). graphique = un graphique de la description
//   (atelier_graphiques_description.py) ; donnees = {t: [instants epoch s], valeurs: {serie: [valeur|null par instant]}}
//   ou serie = chemin du SENSOR ou "calc:<nom>" deja calculee ; theme = {texte, grille}.
//   Serie ABSENTE = cle absente de valeurs, ou aucune valeur numerique : le titre est suffixe « série absente », les
//   autres series sont tracees. Styles instantanes (cadran, anneau, radar, liquide, demi-cercle) : le DERNIER point ; s'il
//   vaut null (capteur debranche, esclave muet), la serie est absente : une valeur perimee n'est jamais montree.
//   barres-periode : par periode (cumul heure|jour|mois, jour par defaut), somme des HAUSSES d'un compteur ; apres une
//   baisse (remise a zero) la nouvelle valeur compte depuis zero. chaleur : moyenne de la 1re serie par heure x jour. nuage : 1re serie en x, 2e en y.
//   Zones [[seuil 0..1, couleur]] : fractions de [min, max] (bornes des donnees si absentes) ; markArea + markLine sur les
//   styles temporels, axisLine du cadran, couleur de la jauge liquide et du demi-cercle.
// PagesGraphiques.page(element, description, lecteur) -> {arrete()} : grille des graphiques (largeur demi|pleine, hauteur),
//   une lecture par (periode, cadence) : lecteur(chemins, periode) -> Promise<donnees> ; en periode « direct » chaque
//   lecture ajoute un point (360 au plus). Valeurs « calc: » calculees ici par PagesFormule.calcule. Rien n'est lu quand
//   l'onglet est cache. Si window.echarts existe deja (atelier), rien n'est charge : l'hote fournit ECharts et liquidfill.
// PagesGraphiques.lecteurCarte(nomHistorique, historique) : lecteur de la carte, /pages?f=valeurs (direct, 12 chemins par
//   requete) et /histo?n=<nom>&p=jour|mois (mois = le mois UTC en cours). Le nom de l'historique n'est pas dans
//   window.PAGE_GRAPHIQUES : PAGE_GRAPHIQUES.nomHistorique s'il existe, sinon « mesures » (defaut de graphiquesFonctions).
var PagesGraphiques = (function () {
  'use strict';
  var STYLES = ['courbe', 'aire', 'escalier', 'barres', 'barres-empilees', 'barres-periode', 'deux-axes', 'lies',
                'cadran', 'anneau', 'chaleur', 'nuage', 'radar', 'liquide', 'demi-cercle'];
  var TEMPORELS = ['courbe', 'aire', 'escalier', 'barres', 'barres-empilees', 'deux-axes', 'lies'];
  var INSTANTANES = ['cadran', 'anneau', 'radar', 'liquide', 'demi-cercle'];
  var PALETTE = ['#1f7fc4', '#d68a12', '#2e9e5b', '#c8402f', '#8e5cc8', '#14a3a3', '#c25a9e', '#7f8c2d'];
  var DEFAUT = PALETTE[0];
  var CADENCES = {direct: 10, jour: 300, mois: 3600};    // secondes, si le graphique n'en donne pas
  var MAX_DIRECT = 360;
  var fmtNombre = new Intl.NumberFormat('fr-FR', {maximumFractionDigits: 2});
  var fmtHeure = new Intl.DateTimeFormat('fr-FR', {hour: '2-digit', minute: '2-digit'});
  var fmtJour = new Intl.DateTimeFormat('fr-FR', {weekday: 'short', day: '2-digit', month: '2-digit'});
  var fmtMois = new Intl.DateTimeFormat('fr-FR', {month: 'short', year: 'numeric'});

  function echappe(s) {
    return String(s).replace(/[&<>"']/g, function (c) { return '&#' + c.charCodeAt(0) + ';'; });
  }
  function nombre(v) { return typeof v === 'number' && isFinite(v) ? v : null; }
  function texteNombre(v) { return v === null ? '--' : fmtNombre.format(v); }
  // Libelle : dernier segment du chemin, ou les deux derniers si une autre serie du graphique finit de meme
  function libelle(serie, toutes) {
    if (serie.indexOf('calc:') === 0) return serie.slice(5);
    var s = serie.split('.'), fin = s[s.length - 1];
    return (toutes || []).some(function (x) { return x !== serie && x.split('.').pop() === fin; }) ? s.slice(-2).join('.') : fin;
  }
  // Presente : au moins une valeur ; pour un style instantane, le dernier point lui-meme (pas une valeur du tampon)
  function present(d, s, instantane) {
    var l = d.valeurs && Object.prototype.hasOwnProperty.call(d.valeurs, s) ? d.valeurs[s] : null;
    if (!Array.isArray(l)) return false;
    return instantane ? l.length > 0 && nombre(l[l.length - 1]) !== null : l.some(function (v) { return nombre(v) !== null; });
  }
  function derniere(l) {
    for (var i = (l || []).length - 1; i >= 0; i--) if (nombre(l[i]) !== null) return l[i];
    return null;
  }
  function etendue(d, series) {
    var bas = Infinity, haut = -Infinity;
    series.forEach(function (s) { d.valeurs[s].forEach(function (v) { if (nombre(v) !== null) { bas = Math.min(bas, v); haut = Math.max(haut, v); } }); });
    return isFinite(bas) ? [bas, haut] : [0, 1];
  }
  // Bornes [min, max] : celles du graphique, sinon defaut (instantanes) ou etendue des donnees (temporels)
  function bornes(g, defaut) {
    var b = [nombre(g.min) !== null ? g.min : defaut[0], nombre(g.max) !== null ? g.max : defaut[1]];
    return b[1] > b[0] ? b : [b[0], b[0] + 1];
  }
  function zones(g) {
    return (Array.isArray(g.zones) ? g.zones.slice() : []).sort(function (a, b) { return a[0] - b[0]; });
  }
  // Couleur de la zone qui contient la fraction (0..1), sinon la couleur par defaut
  function couleurZone(g, f) {
    var z = zones(g);
    for (var i = 0; i < z.length; i++) if (f <= z[i][0]) return z[i][1];
    return DEFAUT;
  }
  function fraction(v, b) { return v === null ? 0 : Math.max(0, Math.min(1, (v - b[0]) / (b[1] - b[0]))); }
  function alpha(hex, a) {
    var n = parseInt(hex.slice(1), 16);
    return 'rgba(' + (n >> 16 & 255) + ',' + (n >> 8 & 255) + ',' + (n & 255) + ',' + a + ')';
  }

  function base(g, th, absentes) {
    return {animation: false, color: PALETTE,
      title: {text: g.titre + (absentes.length ? ' — série absente' : ''), left: 'center', top: 0,
              textStyle: {color: th.texte, fontSize: 14, fontWeight: 'normal'}},
      tooltip: {trigger: 'item', confine: true}};
  }
  function axeTexte(th) {
    return {axisLine: {lineStyle: {color: th.texte}}, axisLabel: {color: th.texte, hideOverlap: true},
            nameTextStyle: {color: th.texte}, splitLine: {lineStyle: {color: th.grille}}};
  }
  function axeValeur(th, extra) {
    var a = axeTexte(th);
    a.type = 'value';
    a.scale = true;
    a.axisLabel.formatter = function (v) { return fmtNombre.format(v); };
    return Object.assign(a, extra || {});
  }
  function legende(th) { return {type: 'scroll', bottom: 0, textStyle: {color: th.texte}}; }
  // Axe des temps : heures, et le jour a minuit (format francais, comme graphiques_trace.js)
  function axeTemps(th) {
    var a = Object.assign(axeTexte(th), {type: 'time', splitLine: {show: false}});
    a.axisLabel.formatter = function (x) {
      var d = new Date(x);
      return (d.getHours() === 0 && d.getMinutes() === 0) ? fmtJour.format(d) : fmtHeure.format(d);
    };
    return a;
  }

  // Seuils : bandes (markArea) et lignes (markLine) sur la 1re serie tracee, en valeurs de l'axe Y
  function seuils(g, s, b) {
    var z = zones(g), prec = 0, aires = [], lignes = [];
    z.forEach(function (x) {
      var de = b[0] + prec * (b[1] - b[0]), a = b[0] + x[0] * (b[1] - b[0]);
      aires.push([{yAxis: de, itemStyle: {color: alpha(x[1], 0.12)}}, {yAxis: a}]);
      lignes.push({yAxis: a, lineStyle: {color: x[1], type: 'dashed'}});
      prec = x[0];
    });
    if (!z.length) return;
    s.markArea = {silent: true, data: aires};
    s.markLine = {silent: true, symbol: 'none', label: {show: false}, data: lignes};
  }

  function temporel(g, d, th, o, presentes) {
    var ms = d.t.map(function (t) { return t * 1000; });
    var barres = g.type === 'barres' || g.type === 'barres-empilees';
    var b = bornes(g, etendue(d, presentes));
    o.series = presentes.map(function (s, k) {
      var x = {name: libelle(s, g.series), type: barres ? 'bar' : 'line', color: PALETTE[k % PALETTE.length],
               data: ms.map(function (t, i) { return [t, nombre(d.valeurs[s][i])]; })};
      if (barres) x.barMaxWidth = 14;
      else { x.showSymbol = false; x.connectNulls = false; x.lineStyle = {width: 2}; }
      if (g.type === 'aire') x.areaStyle = {color: alpha(x.color, 0.25)};
      if (g.type === 'escalier') x.step = 'end';
      if (g.type === 'barres-empilees') x.stack = 'pile';
      if (g.type === 'deux-axes') x.yAxisIndex = k === 0 ? 0 : 1;
      return x;
    });
    if (o.series.length) seuils(g, o.series[0], b);
    var y = {min: nombre(g.min) !== null ? g.min : undefined, max: nombre(g.max) !== null ? g.max : undefined};
    o.yAxis = g.type === 'deux-axes' ? [axeValeur(th, y), axeValeur(th, {position: 'right', splitLine: {show: false}})] : axeValeur(th, y);
    o.xAxis = axeTemps(th);
    o.grid = {left: 56, right: g.type === 'deux-axes' ? 56 : 16, top: 36, bottom: 44};
    o.tooltip = {trigger: 'axis', confine: true};
    o.legend = legende(th);
  }

  // Cle et libelle de la periode d'un instant (heure UTC entiere ; jour et mois locaux)
  function periodeDe(t, cumul) {
    var d = new Date(t * 1000);
    if (cumul === 'heure') { d = new Date(Math.floor(t / 3600) * 3600000); return [d.getTime(), fmtJour.format(d) + ' ' + fmtHeure.format(d)]; }
    if (cumul === 'mois') { d = new Date(d.getFullYear(), d.getMonth(), 1); return [d.getTime(), fmtMois.format(d)]; }
    d = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    return [d.getTime(), fmtJour.format(d)];
  }

  function parPeriode(g, d, th, o, presentes) {
    var cles = [], noms = [], rang = {};
    d.t.forEach(function (t) {
      var p = periodeDe(t, g.cumul || 'jour');
      if (!(p[0] in rang)) { rang[p[0]] = cles.length; cles.push(p[0]); noms.push(p[1]); }
    });
    o.series = presentes.map(function (s, k) {
      var v = d.valeurs[s], somme = cles.map(function () { return 0; });
      for (var i = 1; i < d.t.length; i++) {
        var a = nombre(v[i - 1]), b = nombre(v[i]);
        if (a !== null && b !== null) somme[rang[periodeDe(d.t[i], g.cumul || 'jour')[0]]] += b >= a ? b - a : b;
      }
      return {name: libelle(s, g.series), type: 'bar', barMaxWidth: 24, color: PALETTE[k % PALETTE.length],
              data: somme.map(function (x) { return Math.round(x * 1000) / 1000; })};
    });
    o.xAxis = Object.assign(axeTexte(th), {type: 'category', data: noms});
    o.yAxis = axeValeur(th, {scale: false});
    o.grid = {left: 56, right: 16, top: 36, bottom: 44};
    o.tooltip = {trigger: 'axis', confine: true};
    o.legend = legende(th);
  }

  function cadran(g, d, th, o, s) {
    var v = s ? derniere(d.valeurs[s]) : null, b = bornes(g, [0, 100]);
    var couleurs = zones(g).map(function (z) { return [z[0], z[1]]; }).concat([[1, DEFAUT]]);
    var entier = b[1] - b[0] > 20;
    o.series = [{type: 'gauge', min: b[0], max: b[1], center: ['50%', '58%'], radius: '78%', startAngle: 200, endAngle: -20,
      splitNumber: 4,
      axisLine: {lineStyle: {width: 12, color: couleurs}}, pointer: {width: 4, itemStyle: {color: th.texte}},
      axisTick: {show: false}, splitLine: {length: 12, lineStyle: {color: th.texte, width: 1}},
      axisLabel: {color: th.texte, fontSize: 10, distance: 16, formatter: function (x) { return fmtNombre.format(entier ? Math.round(x) : x); }},
      title: {show: false}, anchor: {show: false},
      detail: {color: th.texte, fontSize: 20, offsetCenter: [0, '58%'], formatter: texteNombre(v)},
      data: [{value: v === null ? b[0] : v, name: s ? libelle(s) : ''}]}];
  }

  function chaleur(g, d, th, o, s) {
    var jours = [], rang = {}, somme = {}, compte = {};
    if (s) d.t.forEach(function (t, i) {
      var v = nombre(d.valeurs[s][i]);
      if (v === null) return;
      var p = periodeDe(t, 'jour'), h = new Date(t * 1000).getHours();
      if (!(p[0] in rang)) { rang[p[0]] = jours.length; jours.push(p[1]); }
      var k = rang[p[0]] + ':' + h;
      somme[k] = (somme[k] || 0) + v;
      compte[k] = (compte[k] || 0) + 1;
    });
    var data = Object.keys(somme).map(function (k) {
      var x = k.split(':');
      return [+x[1], +x[0], Math.round(somme[k] / compte[k] * 100) / 100];
    });
    var e = data.length ? [Math.min.apply(null, data.map(function (x) { return x[2]; })), Math.max.apply(null, data.map(function (x) { return x[2]; }))] : [0, 1];
    var b = bornes(g, e), heures = [];
    for (var h = 0; h < 24; h++) heures.push(h + ' h');
    o.xAxis = Object.assign(axeTexte(th), {type: 'category', data: heures, splitArea: {show: false}});
    o.yAxis = Object.assign(axeTexte(th), {type: 'category', data: jours});
    o.visualMap = {min: b[0], max: b[1], calculable: false, orient: 'horizontal', left: 'center', bottom: 0, itemHeight: 120,
                   textStyle: {color: th.texte}, inRange: {color: ['#1f7fc4', '#2e9e5b', '#d68a12', '#c8402f']}};
    o.grid = {left: 72, right: 16, top: 36, bottom: 56};
    o.series = [{type: 'heatmap', name: s ? libelle(s) : '', data: data}];
  }

  function nuage(g, d, th, o, presentes) {
    var x = presentes[0], y = presentes[1], data = [];
    d.t.forEach(function (t, i) {
      var a = x ? nombre(d.valeurs[x][i]) : null, b = y ? nombre(d.valeurs[y][i]) : null;
      if (y && a !== null && b !== null) data.push([a, b]);
      else if (!y && a !== null) data.push([t * 1000, a]);
    });
    o.xAxis = y ? axeValeur(th, {name: libelle(x)}) : axeTemps(th);
    o.yAxis = axeValeur(th, {name: y ? libelle(y) : (x ? libelle(x) : '')});
    o.grid = {left: 56, right: 24, top: 44, bottom: 32};
    o.series = [{type: 'scatter', symbolSize: 6, data: data}];
  }

  function radar(g, d, th, o, presentes) {
    var v = presentes.map(function (s) { return derniere(d.valeurs[s]); });
    o.radar = {radius: '62%', center: ['50%', '56%'], axisName: {color: th.texte},
      splitLine: {lineStyle: {color: th.grille}}, splitArea: {show: false},
      indicator: presentes.map(function (s, k) {
        return {name: libelle(s, g.series), min: nombre(g.min) !== null ? g.min : 0,
                max: nombre(g.max) !== null ? g.max : Math.max(1, Math.abs(v[k] || 0) * 1.25)};
      })};
    o.series = [{type: 'radar', data: [{name: g.titre, value: v.map(function (x) { return x === null ? 0 : x; }), areaStyle: {opacity: 0.25}}]}];
  }

  function liquide(g, d, th, o, s) {
    var v = s ? derniere(d.valeurs[s]) : null, b = bornes(g, [0, 100]), f = fraction(v, b), col = couleurZone(g, f);
    o.series = [{type: 'liquidFill', data: [f, f], radius: '78%', center: ['50%', '56%'], color: [col],
      backgroundStyle: {color: 'rgba(127,127,127,0.15)'}, waveAnimation: false,
      outline: {borderDistance: 3, itemStyle: {borderColor: col, borderWidth: 3, shadowBlur: 0}}, itemStyle: {shadowBlur: 0},
      label: {formatter: texteNombre(v), fontSize: 24, color: col, insideColor: '#fff'}}];
  }

  // Demi-cercle SVG (modele H de outils_docs/jauges/catalogue_jauges.html) : sans script, lisible aussi en accueil
  function demiCercle(g, d, th, s, titre) {
    var v = s ? derniere(d.valeurs[s]) : null, b = bornes(g, [0, 100]), f = fraction(v, b), col = couleurZone(g, f);
    var arc = 'd="M20 130 A80 80 0 0 1 180 130" fill="none" stroke-width="18"';
    return '<svg viewBox="0 0 200 150" role="img" aria-label="' + echappe(titre) + '" xmlns="http://www.w3.org/2000/svg">' +
      '<text x="100" y="11" text-anchor="middle" font-size="8.5" fill="' + th.texte + '">' + echappe(titre) + '</text>' +
      '<path ' + arc + ' stroke="rgba(127,127,127,0.25)"/>' +
      '<path ' + arc + ' stroke="' + col + '" pathLength="100" stroke-dasharray="' + Math.round(f * 1000) / 10 + ' 100"/>' +
      '<text x="100" y="118" text-anchor="middle" font-size="28" fill="' + th.texte + '">' + echappe(texteNombre(v)) + '</text>' +
      '<text x="20" y="147" text-anchor="middle" font-size="10" fill="' + th.texte + '">' + echappe(texteNombre(b[0])) + '</text>' +
      '<text x="180" y="147" text-anchor="middle" font-size="10" fill="' + th.texte + '">' + echappe(texteNombre(b[1])) + '</text></svg>';
  }

  function optionDe(g, donnees, theme) {
    var d = {t: (donnees && Array.isArray(donnees.t)) ? donnees.t : [], valeurs: (donnees && donnees.valeurs) || {}};
    var th = {texte: (theme && theme.texte) || '#888', grille: (theme && theme.grille) || 'rgba(128,128,128,0.25)'};
    var series = Array.isArray(g.series) ? g.series : [];
    var instantane = INSTANTANES.indexOf(g.type) >= 0;
    var presentes = series.filter(function (s) { return present(d, s, instantane); });
    var absentes = series.filter(function (s) { return presentes.indexOf(s) < 0; });
    var o = base(g, th, absentes), s = presentes[0];
    if (g.type === 'demi-cercle') return {svg: demiCercle(g, d, th, s, o.title.text)};
    if (TEMPORELS.indexOf(g.type) >= 0) temporel(g, d, th, o, presentes);
    else if (g.type === 'barres-periode') parPeriode(g, d, th, o, presentes);
    else if (g.type === 'cadran') cadran(g, d, th, o, s);
    else if (g.type === 'anneau') {
      o.series = [{type: 'pie', radius: ['42%', '62%'], center: ['50%', '55%'], label: {color: th.texte, formatter: '{b}\n{c}'},
        data: presentes.map(function (x) { return {name: libelle(x, series), value: derniere(d.valeurs[x])}; })}];
    } else if (g.type === 'chaleur') chaleur(g, d, th, o, s);
    else if (g.type === 'nuage') nuage(g, d, th, o, presentes);
    else if (g.type === 'radar') radar(g, d, th, o, presentes);
    else if (g.type === 'liquide') liquide(g, d, th, o, s);
    else o.title.text = g.titre + ' — style inconnu';
    return o;
  }

  // ---- Navigateur : chargement d'ECharts, lecture, grille ---------------------------------------------

  function lisStockage(cle) { try { return localStorage.getItem(cle); } catch (e) { return null; } }
  function memorise(cle, prefixe, texte) {
    try {
      for (var i = localStorage.length - 1; i >= 0; i--) {
        var k = localStorage.key(i);
        if (k && k.indexOf(prefixe) === 0 && k !== cle) localStorage.removeItem(k);
      }
      localStorage.setItem(cle, texte);
    } catch (e) { /* stockage indisponible ou plein : la bibliotheque sera redemandee a la carte */ }
  }
  // Bibliotheque compressee (comme cuve.js) : localStorage, sinon la carte, decompressee par DecompressionStream
  function charge(cle, prefixe, url, nom) {
    var texte = lisStockage(cle);
    var source = texte ? Promise.resolve(texte) : fetch(url).then(function (r) {
      if (!r.ok) throw new Error(nom + ' absent de la carte (HTTP ' + r.status + ').');
      if (typeof DecompressionStream === 'undefined' || !r.body) throw new Error('Navigateur trop ancien pour décompresser ' + nom + '.');
      return new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).text();
    }).then(function (t) { memorise(cle, prefixe, t); return t; });
    return source.then(function (t) {
      var s = document.createElement('script');
      s.textContent = t;
      document.head.appendChild(s);
    });
  }
  function chargeBibliotheques(desc, avecLiquide) {
    if (window.echarts) return Promise.resolve();
    var cle = desc.bibliotheque || 'echarts';
    return charge(cle, 'echarts-', '/graphiques?f=echarts.js.gz', 'ECharts').then(function () {
      if (!window.echarts) { try { localStorage.removeItem(cle); } catch (e) { /* rien */ } throw new Error('ECharts illisible : recharger la page.'); }
      if (avecLiquide) return charge(desc.extension || 'liquidfill', 'liquidfill-', '/pages?f=liquidfill.js.gz', 'Le module liquidfill');
    });
  }

  function lisJson(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error('lecture de ' + url.split('?')[0] + ' impossible (HTTP ' + r.status + ')');
      return r.json();
    });
  }

  function lecteurCarte(nomHistorique, historique) {
    return function (chemins, periode) {
      var vide = {t: [], valeurs: {}};
      if (!chemins.length || (periode !== 'direct' && !historique)) return Promise.resolve(vide);
      if (periode === 'direct') {
        var paquets = [];
        for (var i = 0; i < chemins.length; i += 12) paquets.push(chemins.slice(i, i + 12));
        return Promise.all(paquets.map(function (p) {
          return lisJson('/pages?f=valeurs&c=' + p.map(encodeURIComponent).join(','));
        })).then(function (rs) {
          var d = {t: [nombre(rs[0].t) !== null ? rs[0].t : Date.now() / 1000], valeurs: {}};
          rs.forEach(function (r) { Object.keys(r.valeurs || {}).forEach(function (c) { d.valeurs[c] = [r.valeurs[c]]; }); });
          return d;
        });
      }
      var maintenant = new Date(), url = '/histo?n=' + encodeURIComponent(nomHistorique) + '&p=' + periode;
      if (periode === 'mois') url += '&m=' + maintenant.getUTCFullYear() + '-' + ('0' + (maintenant.getUTCMonth() + 1)).slice(-2);
      return lisJson(url).then(function (r) {
        var d = {t: [], valeurs: {}}, noms = (periode === 'mois' && r.seriesFichier) || r.series || [];   // mois : colonnes du fichier
        var rangs = chemins.map(function (c) { return noms.indexOf(c); });
        if (periode === 'jour') {
          var n = Array.isArray(r.valeurs) && r.valeurs[0] ? r.valeurs[0].length : 0;
          for (var k = 0; k < n; k++) d.t.push(r.t0 + k * r.pas);
          chemins.forEach(function (c, j) { if (rangs[j] >= 0) d.valeurs[c] = r.valeurs[rangs[j]].slice(); });
          if (typeof r.tEncours === 'number' && Array.isArray(r.encours)) {
            d.t.push(r.tEncours);
            chemins.forEach(function (c, j) { if (rangs[j] >= 0) d.valeurs[c].push(r.encours[rangs[j]]); });
          }
        } else {
          (r.lignes || []).forEach(function (l) { d.t.push(l[0]); });
          chemins.forEach(function (c, j) {
            if (rangs[j] >= 0) d.valeurs[c] = (r.lignes || []).map(function (l) { return l[2 + 3 * rangs[j]]; });   // moyenne
          });
        }
        return d;
      });
    };
  }

  function themeDe(element) {
    var texte = '#888';
    try { texte = getComputedStyle(element).color || texte; } catch (e) { /* defaut */ }
    return {texte: texte, grille: 'rgba(128,128,128,0.25)'};
  }

  function page(element, description, lecteur) {
    var desc = description || {}, graphiques = (desc.page && desc.page.graphiques) || [];
    var formules = {}, groupes = {}, minuteries = [], arrete = false, erreurBibliotheque = '';
    Object.keys(desc.calculees || {}).forEach(function (nom) {
      var c = desc.calculees[nom];
      formules[nom] = window.PagesFormule.analyse(c && c.formule);
    });
    element.innerHTML = '';
    var msg = document.createElement('p'), grille = document.createElement('div');
    msg.className = 'pg_msg';
    grille.className = 'pg_grille';
    element.appendChild(msg);
    element.appendChild(grille);
    var tuiles = graphiques.map(function (g) {
      var div = document.createElement('div');
      div.className = 'pg_tuile' + (g.largeur === 'pleine' ? ' pg_pleine' : '');
      div.style.height = (g.hauteur || 260) + 'px';
      div.setAttribute('data-style', g.type);
      grille.appendChild(div);
      var periode = g.periode || 'direct', cadence = g.cadence || CADENCES[periode] || 10, cle = periode + '/' + cadence;
      var gr = groupes[cle] = groupes[cle] || {periode: periode, cadence: cadence, chemins: [], calc: [], tuiles: [], tampon: null};
      (g.series || []).forEach(function (s) {
        var deps = s.indexOf('calc:') === 0 ? (formules[s.slice(5)] && formules[s.slice(5)].series) || [] : [s];
        if (s.indexOf('calc:') === 0 && gr.calc.indexOf(s) < 0) gr.calc.push(s);
        deps.forEach(function (c) { if (gr.chemins.indexOf(c) < 0) gr.chemins.push(c); });
      });
      var t = {g: g, div: div, graphe: null, d: null};
      gr.tuiles.push(t);
      return t;
    });

    function dessine(t) {
      if (!t.d || arrete) return;
      var o = optionDe(t.g, t.d, themeDe(element));
      t.div.setAttribute('data-titre', o.svg !== undefined ? t.g.titre + (o.svg.indexOf('série absente') > 0 ? ' — série absente' : '') : o.title.text);
      t.div.setAttribute('data-rendu', o.svg !== undefined ? 'svg' : (o.series && o.series[0] ? o.series[0].type : ''));
      if (o.svg !== undefined) { t.div.innerHTML = o.svg; return; }
      if (!window.echarts) { t.div.textContent = t.g.titre + ' : ' + (erreurBibliotheque || 'chargement…'); return; }
      if (!t.graphe) {
        t.div.textContent = '';
        t.graphe = window.echarts.init(t.div, null, {renderer: 'svg'});
        if (t.g.type === 'lies') { t.graphe.group = 'pg_lies'; window.echarts.connect('pg_lies'); }
      }
      t.graphe.setOption(o, true);
    }

    // Ajoute les series calc: (formule evaluee a chaque instant) ; une formule refusee laisse la serie absente
    function calcule(gr, d) {
      gr.calc.forEach(function (s) {
        var f = formules[s.slice(5)];
        if (!f || !f.ok) return;
        d.valeurs[s] = d.t.map(function (_, i) {
          var v = {};
          f.series.forEach(function (c) { v[c] = d.valeurs[c] ? d.valeurs[c][i] : null; });
          return window.PagesFormule.calcule(f.arbre, v);
        });
      });
    }

    function accumule(gr, d) {
      var b = gr.tampon = gr.tampon || {t: [], valeurs: {}};
      d.t.forEach(function (t, i) {
        b.t.push(t);
        gr.chemins.forEach(function (c) {
          (b.valeurs[c] = b.valeurs[c] || b.t.slice(1).map(function () { return null; })).push(d.valeurs[c] ? d.valeurs[c][i] : null);
        });
      });
      var trop = b.t.length - MAX_DIRECT;
      if (trop > 0) { b.t.splice(0, trop); Object.keys(b.valeurs).forEach(function (c) { b.valeurs[c].splice(0, trop); }); }
      return {t: b.t.slice(), valeurs: Object.keys(b.valeurs).reduce(function (o, c) { o[c] = b.valeurs[c].slice(); return o; }, {})};
    }

    function lis(gr) {
      if (gr.enCours || arrete || document.hidden) return;
      gr.enCours = true;
      Promise.resolve().then(function () { return lecteur(gr.chemins, gr.periode); }).then(function (r) {
        var d = {t: (r && Array.isArray(r.t)) ? r.t : [], valeurs: (r && r.valeurs) || {}};
        if (gr.periode === 'direct') d = accumule(gr, d);
        calcule(gr, d);
        gr.tuiles.forEach(function (t) { t.d = d; dessine(t); });
        msg.textContent = erreurBibliotheque;
      }).catch(function (e) {
        msg.textContent = 'Lecture impossible : ' + e.message;
      }).then(function () { gr.enCours = false; });
    }
    function lisTout() { Object.keys(groupes).forEach(function (k) { lis(groupes[k]); }); }
    function redimensionne() { tuiles.forEach(function (t) { if (t.graphe) t.graphe.resize(); }); }

    var avecECharts = graphiques.some(function (g) { return g.type !== 'demi-cercle'; });
    var avecLiquide = graphiques.some(function (g) { return g.type === 'liquide'; });
    msg.textContent = avecECharts && !window.echarts ? 'Chargement…' : '';
    (avecECharts ? chargeBibliotheques(desc, avecLiquide) : Promise.resolve()).catch(function (e) {
      erreurBibliotheque = e.message + ' Les jauges en demi-cercle restent affichées.';
    }).then(function () {
      if (arrete) return;
      tuiles.forEach(dessine);
      lisTout();
      Object.keys(groupes).forEach(function (k) {
        minuteries.push(setInterval(function () { lis(groupes[k]); }, groupes[k].cadence * 1000));
      });
    });
    document.addEventListener('visibilitychange', lisTout);
    window.addEventListener('resize', redimensionne);
    return {arrete: function () {
      arrete = true;
      minuteries.forEach(clearInterval);
      document.removeEventListener('visibilitychange', lisTout);
      window.removeEventListener('resize', redimensionne);
      tuiles.forEach(function (t) { if (t.graphe) t.graphe.dispose(); });
    }};
  }

  // Sur la carte : demarrage automatique (l'atelier, sans PAGE_GRAPHIQUES, appelle page() lui-meme)
  if (typeof window !== 'undefined' && window.PAGE_GRAPHIQUES && typeof document !== 'undefined') {
    var C = window.PAGE_GRAPHIQUES, zone = document.getElementById('pg_page');
    if (zone) page(zone, C, lecteurCarte(C.nomHistorique || 'mesures', C.historique));
  }

  return {STYLES: STYLES, optionDe: optionDe, page: page, lecteurCarte: lecteurCarte};
})();
