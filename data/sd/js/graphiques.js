// graphiques.js - Page /graphiques des cartes ESP32-S3 et P4 (data/fs/graphiquesFonctions.be), 2026-10-18
// Trace l'historique de la carte (/histo, data/fs/historiqueFonctions.be) avec uPlot.
// La carte pose avant ce script window.GRAPHIQUES = {uplot, nom, affichage, grafana, groupes, compteurs, esclaves} :
//   - uplot     : cle versionnee du cache localStorage d'uPlot ('uPlot-1.6.30') ;
//   - nom       : nom de l'historique ('mesures') ;
//   - affichage : {serie: {libelle, unite, facteur}} du persist (diverses.historique.affichage), facultatif ;
//   - grafana   : URL du tableau Grafana de la carte (vide = pas de bouton) ;
//   - groupes   : {titre: [debuts de chemin]} (diverses.historique.groupes) : un graphique par groupe, les
//                 autres series dans « Mesures » ;
//   - compteurs : reglages des compteurs (diverses.historique.compteurs), pour leur unite ;
//   - esclaves  : {TasmotaSlaveModBusN: nom} des esclaves ModBus, pour les libelles par defaut.
// Une serie s'appelle par son chemin dans le JSON SENSOR de la carte (ex. 'DS18B20.Temperature').
// uPlot est garde dans le localStorage : la carte ne le renvoie (49 Ko, sans cache HTTP possible depuis
// Berry) qu'au premier affichage ou au changement de version. Vues : 24 h (RAM de la carte, un point par
// pas) et mois (une ligne par heure en flash : moyenne + bande min/max). Toute lecture ou ecriture du
// localStorage est sous try/catch : sans stockage, la page marche, elle ne retient simplement rien.
(function () {
  'use strict';
  var G = window.GRAPHIQUES || {};
  var AFFICHAGE = G.affichage || {}, GROUPES = G.groupes || {}, COMPTEURS = G.compteurs || {};
  var ESCLAVES = G.esclaves || {};
  var COULEURS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#17becf',
                  '#bcbd22', '#7f7f7f', '#aec7e8', '#ffbb78'];
  var CLE_MASQUEES = 'graphiques-masquees', CLE_VUE = 'graphiques-vue';
  var fmtHeure = new Intl.DateTimeFormat('fr-FR', {hour: '2-digit', minute: '2-digit'});
  var fmtJour = new Intl.DateTimeFormat('fr-FR', {weekday: 'short', day: '2-digit', month: '2-digit'});
  var fmtComplet = new Intl.DateTimeFormat('fr-FR', {weekday: 'short', day: '2-digit', month: '2-digit',
                                                     hour: '2-digit', minute: '2-digit'});
  var fmtMois = new Intl.DateTimeFormat('fr-FR', {month: 'long', year: 'numeric'});
  var fmtNombre = new Intl.NumberFormat('fr-FR', {maximumFractionDigits: 2});

  var etat = {series: [], vue: 'jour', courbes: [], x: [], titre: '', masquees: lisListe(CLE_MASQUEES)};
  // Un bloc par graphique : {titre, prefixes (null = « Mesures », les series d'aucun groupe), zone, trace, cases, uplot}
  var blocs = [];

  function $(id) { return document.getElementById(id); }

  function message(texte, erreur) {
    var m = $('g_msg');
    m.textContent = texte || '';
    m.style.display = texte ? '' : 'none';
    m.style.color = erreur ? '#ff5661' : '';
  }

  // ---- localStorage, sous try/catch ----------------------------------------------------------------
  function lis(cle) { try { return localStorage.getItem(cle); } catch (e) { return null; } }
  function ecris(cle, valeur) { try { localStorage.setItem(cle, valeur); } catch (e) { /* rien */ } }
  function lisListe(cle) {
    try { var v = JSON.parse(lis(cle) || '[]'); return Array.isArray(v) ? v : []; } catch (e) { return []; }
  }

  // Couleur du theme Tasmota (variables CSS), pour que les axes restent lisibles en theme sombre
  function couleurTheme(variable, defaut) {
    try {
      var v = getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
      return v || defaut;
    } catch (e) { return defaut; }
  }

  function transparence(hex, alpha) {
    var n = parseInt(hex.slice(1), 16);
    return 'rgba(' + (n >> 16 & 255) + ',' + (n >> 8 & 255) + ',' + (n & 255) + ',' + alpha + ')';
  }

  // ---- uPlot : localStorage, sinon la carte -------------------------------------------------------
  function memorise(cle, texte) {
    try {
      for (var i = localStorage.length - 1; i >= 0; i--) {
        var k = localStorage.key(i);
        if (k && k.indexOf('uPlot-') === 0 && k !== cle) localStorage.removeItem(k);
      }
      localStorage.setItem(cle, texte);
    } catch (e) { /* stockage indisponible ou plein : uPlot sera redemande a la carte */ }
  }

  function chargeUplot() {
    if (window.uPlot) return Promise.resolve();
    var cle = G.uplot || 'uPlot';
    var texte = lis(cle);
    var source = texte ? Promise.resolve(texte) :
      fetch('/graphiques?f=uplot.js').then(function (r) {
        if (!r.ok) throw new Error('uPlot absent de la carte (HTTP ' + r.status + ')');
        return r.text();
      }).then(function (t) { memorise(cle, t); return t; });
    return source.then(function (t) {
      var s = document.createElement('script');
      s.textContent = t;
      document.head.appendChild(s);
      if (!window.uPlot) {
        try { localStorage.removeItem(cle); } catch (e) { /* rien */ }
        throw new Error('uPlot illisible : recharger la page.');
      }
    });
  }

  // ---- Lecture de /histo -------------------------------------------------------------------------
  function lisHisto(parametres) {
    return fetch('/histo?n=' + encodeURIComponent(G.nom || '') + '&' + parametres).then(function (r) {
      return r.text().then(function (t) {
        var d = null;
        try { d = JSON.parse(t); } catch (e) { d = null; }
        if (r.status === 404 && d && d.erreur) {
          throw new Error('Historique pas encore démarré sur la carte (les séries sont découvertes ' +
                          '2 min après le démarrage). Revenir dans quelques minutes.');
        }
        if (!r.ok || !d) throw new Error('Lecture de /histo impossible (HTTP ' + r.status + ')');
        return d;
      });
    });
  }

  // ---- Libelles, unites, couleurs ----------------------------------------------------------------
  // Unite devinee quand le persist n'en donne pas (affichage, compteurs) : d'abord la derniere cle du chemin
  // (noms de Tasmota : Temperature, Humidity...), puis le nom entier (valeurs des modules : hauteurEau...)
  var UNITES_TASMOTA = {Temperature: '°C', DewPoint: '°C', Humidity: '%', Pressure: 'hPa', SeaPressure: 'hPa',
                        Illuminance: 'lx', Power: 'W', ApparentPower: 'VA', ReactivePower: 'var', Voltage: 'V',
                        Current: 'A', Total: 'kWh', Today: 'kWh', Yesterday: 'kWh', Frequency: 'Hz', CarbonDioxide: 'ppm',
                        eCO2: 'ppm', TVOC: 'ppb', Distance: 'mm'};
  function devineUnite(nom) {
    var cle = nom.split('.').pop();
    if (UNITES_TASMOTA.hasOwnProperty(cle)) return UNITES_TASMOTA[cle];
    var n = nom.toLowerCase();
    if (/temp/.test(n)) return '°C';
    if (/mv$|_mv\b/.test(n)) return 'mV';
    if (/hauteur|niveau/.test(n)) return 'cm';
    if (/volume/.test(n)) return 'L';
    if (/humid|taux|pourcent/.test(n)) return '%';
    if (/rssi/.test(n)) return 'dBm';
    if (/press/.test(n)) return 'hPa';
    if (/heap/.test(n)) return 'o';
    return '';
  }

  // Libelle par defaut d'un chemin : esclave ModBus nomme par le persist, segments separes par des espaces
  // ('TasmotaSlaveModBus.TasmotaSlaveModBus1.ANALOG.A1' -> 'Capteurs Cuve ModBus ANALOG A1')
  function libelleDefaut(nom) {
    var s = nom.split('.');
    if (s[0] === 'TasmotaSlaveModBus' && s.length > 2) s = [ESCLAVES[s[1]] || s[1]].concat(s.slice(2));
    return s.join(' ');
  }

  // Une courbe : valeurs multipliees par le facteur (ex. taux 0-1 -> %), null conserve
  function courbe(nom, moy, min, max) {
    var a = AFFICHAGE[nom] || {}, cpt = COMPTEURS[nom] || {};
    var f = (typeof a.facteur === 'number') ? a.facteur : 1;
    var echelle = function (v) { return v === null ? null : v * f; };
    var rang = etat.series.indexOf(nom);
    return {
      nom: nom,
      libelle: a.libelle || libelleDefaut(nom),
      unite: (typeof a.unite === 'string') ? a.unite : (typeof cpt.unite === 'string') ? cpt.unite : devineUnite(nom),
      couleur: COULEURS[(rang < 0 ? etat.courbes.length : rang) % COULEURS.length],
      moy: moy.map(echelle), min: min ? min.map(echelle) : null, max: max ? max.map(echelle) : null
    };
  }

  // ---- Axe des temps en francais -----------------------------------------------------------------
  function valeursTemps(u, reperes, axe, espace, pas) {
    return reperes.map(function (s, i) {
      var d = new Date(s * 1000);
      if (pas >= 86400) return fmtJour.format(d);
      var h = fmtHeure.format(d);
      return (i === 0 || (d.getHours() === 0 && d.getMinutes() === 0)) ? h + '\n' + fmtJour.format(d) : h;
    });
  }

  // ---- Trace -------------------------------------------------------------------------------------
  function largeur() { return Math.max(300, Math.min(window.innerWidth - 40, 1000)); }
  function hauteur() { return window.innerWidth < 600 ? 240 : 320; }

  // ---- Blocs : « Mesures » puis un graphique par groupe du persist -----------------------------------
  function construitBlocs() {
    var zone = $('g_graphiques');
    var defs = [{titre: 'Mesures', prefixes: null}];
    Object.keys(GROUPES).forEach(function (t) {
      if (Array.isArray(GROUPES[t])) defs.push({titre: t, prefixes: GROUPES[t].map(String)});
    });
    defs.forEach(function (d) {
      var b = {titre: d.titre, prefixes: d.prefixes, uplot: null, courbes: []};
      b.zone = document.createElement('div');
      b.entete = document.createElement('h3');
      b.entete.textContent = d.titre;
      b.entete.style.cssText = 'margin:16px 0 4px';
      b.trace = document.createElement('div');
      b.cases = document.createElement('div');
      b.cases.className = 'g_series';
      b.zone.appendChild(b.entete); b.zone.appendChild(b.trace); b.zone.appendChild(b.cases);
      zone.appendChild(b.zone);
      blocs.push(b);
    });
  }

  function dansGroupe(nom, b) {
    return b.prefixes.some(function (p) { return nom === p || nom.indexOf(p + '.') === 0; });
  }

  // Bloc d'une serie : le premier groupe qui la contient, sinon « Mesures »
  function blocDe(nom) {
    for (var i = 1; i < blocs.length; i++) if (dansGroupe(nom, blocs[i])) return blocs[i];
    return blocs[0];
  }

  function detruit(b) { if (b.uplot) { b.uplot.destroy(); b.uplot = null; } }

  // Repartit les courbes de la vue entre les blocs ; un bloc sans serie est masque ; le titre du bloc n'est
  // affiche que s'il y a plusieurs graphiques
  function trace() {
    blocs.forEach(function (b) { b.courbes = []; });
    etat.courbes.forEach(function (c) { blocDe(c.nom).courbes.push(c); });
    var nbVisibles = blocs.filter(function (b) { return b.courbes.length > 0; }).length;
    blocs.forEach(function (b) {
      b.zone.style.display = (b.courbes.length || (b === blocs[0] && nbVisibles === 0)) ? '' : 'none';
      b.entete.style.display = nbVisibles > 1 ? '' : 'none';
      traceBloc(b);
    });
  }

  function traceBloc(b) {
    var visibles = b.courbes.filter(function (c) { return etat.masquees.indexOf(c.nom) < 0; });
    detruit(b);
    if (!b.courbes.length) return;
    if (!visibles.length) { b.trace.textContent = 'Aucune série cochée.'; return; }
    b.trace.textContent = '';

    var texte = couleurTheme('--c_txt', '#888'), grille = 'rgba(128,128,128,0.25)';
    // Unites des series visibles : les deux axes vont aux unites les plus partagees, « sans unite » en dernier
    var unites = [], compte = {};
    visibles.forEach(function (c) {
      if (unites.indexOf(c.unite) < 0) unites.push(c.unite);
      compte[c.unite] = (compte[c.unite] || 0) + 1;
    });
    unites.sort(function (a, b) {
      if ((a === '') !== (b === '')) return a === '' ? 1 : -1;
      return compte[b] - compte[a];
    });

    var scales = {x: {time: true}}, donnees = [etat.x], bandes = [], cachees = [];
    var series = [{label: etat.vue === 'jour' ? 'Heure' : 'Date',
                   value: function (u, v) { return v === null ? '--' : fmtComplet.format(new Date(v * 1000)); }}];
    var valeur = function (u, v) { return v === null ? '--' : fmtNombre.format(v); };
    visibles.forEach(function (c) {
      var echelle = 'u' + unites.indexOf(c.unite);
      var libelle = c.libelle + (c.unite ? ' (' + c.unite + ')' : '');
      scales[echelle] = {};
      series.push({label: libelle, stroke: c.couleur, width: 2, scale: echelle, spanGaps: false, value: valeur});
      donnees.push(c.moy);
      if (c.min && c.max) {
        series.push({label: libelle + ' max', stroke: 'transparent', scale: echelle, points: {show: false}});
        donnees.push(c.max);
        series.push({label: libelle + ' min', stroke: 'transparent', scale: echelle, points: {show: false}});
        donnees.push(c.min);
        bandes.push({series: [series.length - 2, series.length - 1], fill: transparence(c.couleur, 0.2)});
        cachees.push(series.length - 2, series.length - 1);
      }
    });

    var axes = [{stroke: texte, grid: {stroke: grille}, ticks: {stroke: grille}, values: valeursTemps, space: 60}];
    unites.slice(0, 2).forEach(function (unite, i) {     // deux axes visibles ; les unites suivantes sans axe
      axes.push({scale: 'u' + i, side: i === 0 ? 3 : 1, label: unite, stroke: texte, ticks: {stroke: grille},
                 grid: i === 0 ? {stroke: grille} : {show: false}});
    });

    b.uplot = new uPlot({
      title: etat.titre, width: largeur(), height: hauteur(),
      scales: scales, series: series, axes: axes, bands: bandes,
      cursor: {drag: {x: false, y: false}}
    }, donnees, b.trace);
    var lignes = b.uplot.root.querySelectorAll('.u-legend .u-series');
    cachees.forEach(function (i) { if (lignes[i]) lignes[i].style.display = 'none'; });   // min/max hors legende
    message('');
  }

  // Cases a cocher, une par serie de la vue, sous le graphique de la serie, memorisees (les series
  // nouvelles sont cochees par defaut)
  function construitCases() {
    blocs.forEach(function (b) { b.cases.innerHTML = ''; });
    etat.courbes.forEach(function (c) {
      var zone = blocDe(c.nom).cases;
      var l = document.createElement('label');
      l.style.cssText = 'display:inline-block;margin:2px 12px 2px 0;white-space:nowrap;border-left:4px solid ' +
                        c.couleur + ';padding-left:4px';
      var b = document.createElement('input');
      b.type = 'checkbox';
      b.checked = etat.masquees.indexOf(c.nom) < 0;
      b.onchange = function () {
        etat.masquees = etat.masquees.filter(function (n) { return n !== c.nom; });
        if (!b.checked) etat.masquees.push(c.nom);
        ecris(CLE_MASQUEES, JSON.stringify(etat.masquees));
        traceBloc(blocDe(c.nom));
      };
      l.appendChild(b);
      l.appendChild(document.createTextNode(' ' + c.libelle));
      zone.appendChild(l);
    });
  }

  function affiche(titre, x, courbes) {
    etat.titre = titre; etat.x = x; etat.courbes = courbes;
    trace();
    construitCases();
  }

  // ---- Vues --------------------------------------------------------------------------------------
  // 24 h : tampon RAM de la carte, un point par pas (5 min par defaut), null = pas sans mesure
  function vueJour() {
    return lisHisto('p=jour').then(function (d) {
      if (d.t0 === null || !d.valeurs || !d.valeurs.length) {
        affiche('', [], []);
        message('Aucun pas de mesure encore clos depuis le démarrage : revenir dans quelques minutes.');
        return;
      }
      var x = d.valeurs[0].map(function (_, i) { return d.t0 + i * d.pas; });
      affiche('Dernières 24 h (pas de ' + Math.round(d.pas / 60) + ' min)', x,
              d.series.map(function (nom, i) { return courbe(nom, d.valeurs[i]); }));
      if (d.valeurs.every(function (c) { return c.every(function (v) { return v === null; }); })) {
        message('Aucune mesure enregistrée sur les dernières 24 h.');
      }
    });
  }

  // Mois : une ligne par heure [t, min1, moy1, max1, ...] ; une heure absente devient un trou
  function vueMois(m) {
    return lisHisto('p=mois&m=' + encodeURIComponent(m)).then(function (d) {
      var noms = d.seriesFichier || d.series || [], lignes = d.lignes || [];
      if (!lignes.length) { affiche('', [], []); message('Aucune heure enregistrée pour ce mois.'); return; }
      var x = [], cols = noms.map(function () { return {min: [], moy: [], max: []}; }), prec = null;
      lignes.forEach(function (l) {
        if (prec !== null && l[0] - prec > 3600) {
          x.push(prec + 3600);
          cols.forEach(function (c) { c.min.push(null); c.moy.push(null); c.max.push(null); });
        }
        x.push(l[0]);
        cols.forEach(function (c, i) { c.min.push(l[1 + 3 * i]); c.moy.push(l[2 + 3 * i]); c.max.push(l[3 + 3 * i]); });
        prec = l[0];
      });
      affiche(libelleMois(m) + ' (moyenne horaire, bande min-max)', x,
              noms.map(function (nom, i) { return courbe(nom, cols[i].moy, cols[i].min, cols[i].max); }));
    });
  }

  function libelleMois(m) {
    var texte = fmtMois.format(new Date(+m.slice(0, 4), +m.slice(5, 7) - 1, 1));
    return texte.charAt(0).toUpperCase() + texte.slice(1) + (m.length > 7 ? ' (ancienne liste de séries)' : '');
  }

  function montreVue(vue) {
    etat.vue = vue;
    ecris(CLE_VUE, vue);
    message('Chargement...');
    var p = (vue === 'jour') ? vueJour() : vueMois(vue.slice(2));
    return p.catch(function (e) { message(e.message, true); });
  }

  // ---- Barre de commande : vue, Grafana ----------------------------------------------------------
  function construitBarre(mois) {
    var choix = $('g_vue');
    var options = [['jour', '24 dernières heures']].concat(mois.slice().reverse().map(function (m) {
      return ['m:' + m, libelleMois(m)];
    }));
    options.forEach(function (o) {
      var e = document.createElement('option');
      e.value = o[0]; e.textContent = o[1];
      choix.appendChild(e);
    });
    var memo = lis(CLE_VUE);
    choix.value = options.some(function (o) { return o[0] === memo; }) ? memo : 'jour';
    choix.onchange = function () { montreVue(choix.value); };
    return choix.value;
  }

  // Bouton Grafana : pose avant toute lecture, utile meme si l'historique de la carte n'a pas demarre
  function construitGrafana() {
    if (!G.grafana) return;
    var b = $('g_grafana');
    b.style.display = '';
    b.onclick = function () { window.open(G.grafana, '_blank', 'noopener'); };
  }

  function demarre() {
    construitGrafana();
    construitBlocs();
    message('Chargement...');
    var redim = null;
    window.addEventListener('resize', function () {
      clearTimeout(redim);
      redim = setTimeout(function () {
        blocs.forEach(function (b) { if (b.uplot) b.uplot.setSize({width: largeur(), height: hauteur()}); });
      }, 200);
    });
    chargeUplot().then(function () { return lisHisto('p=liste'); }).then(function (liste) {
      etat.series = liste.series || [];
      return montreVue(construitBarre(liste.mois || []));
    }).catch(function (e) { message(e.message, true); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarre);
  else demarre();
})();
