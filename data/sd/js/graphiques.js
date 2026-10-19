// graphiques.js - Page /graphiques des cartes ESP32-S3 et P4 (data/fs/graphiquesFonctions.be), 2026-10-18
// Trace l'historique de la carte (/histo, data/fs/historiqueFonctions.be) avec ECharts 6 (decide le 2026-10-18 a
// la place d'uPlot), en temps reel. La carte pose avant ce script window.GRAPHIQUES :
//   - bibliotheque     : cle versionnee du cache localStorage d'ECharts ('echarts-6.1.0') ;
//   - nom              : nom de l'historique ('mesures') ;
//   - affichage        : {serie: {libelle, unite, facteur}} (graphiques.json de la carte), facultatif ;
//   - groupes          : {titre: [debuts de chemin]} : un graphique par groupe, les autres series dans « Mesures » ;
//   - compteurs        : reglages des compteurs (persist), pour leur unite ;
//   - esclaves         : {TasmotaSlaveModBusN: nom} des esclaves ModBus, pour les libelles par defaut ;
//   - grafana          : URL du tableau Grafana de la carte (vide = pas de bouton) ;
//   - rafraichissement : periode de relecture de l'historique affiche (s) ;
//   - direct           : cadence par defaut des valeurs en temps reel (s, 0 = arret).
// Une serie s'appelle par son chemin dans le JSON SENSOR de la carte (ex. 'DS18B20.Temperature').
//
// Temps reel : toutes les « direct » secondes (liste de la page, choix garde par le navigateur), la page lit les
// valeurs actuelles (/histo?p=direct) et les ajoute au bout des courbes de la vue 24 h et du mois en cours.
// L'historique (pas clos + pas en cours, ou lignes horaires) est relu toutes les « rafraichissement » secondes (mois
// en cours : 15 min) et remplace les points directs qu'il couvre. Rien n'est lu quand l'onglet est cache.
// ECharts (1,1 Mo) est envoye COMPRESSE par la carte (Berry ne peut pas poser Content-Encoding) : la page le
// decompresse (DecompressionStream) et le garde dans le localStorage, redemande seulement au changement de version.
// Toute lecture ou ecriture du localStorage est sous try/catch : sans stockage, la page marche sans rien retenir.
(function () {
  'use strict';
  var G = window.GRAPHIQUES || {};
  var AFFICHAGE = G.affichage || {}, GROUPES = G.groupes || {}, COMPTEURS = G.compteurs || {};
  var ESCLAVES = G.esclaves || {};
  var PERIODE = Math.max(1, +G.rafraichissement || 60) * 1000, PERIODE_MOIS = 15 * 60000;
  var CADENCES = [0, 2, 5, 10, 30, 60];
  var COULEURS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#17becf',
                  '#bcbd22', '#7f7f7f', '#aec7e8', '#ffbb78'];
  var CLE_MASQUEES = 'graphiques-masquees', CLE_VUE = 'graphiques-vue', CLE_DIRECT = 'graphiques-direct';
  var LARGEUR_AXE = 56;            // px reserves par axe Y
  var fmtHeure = new Intl.DateTimeFormat('fr-FR', {hour: '2-digit', minute: '2-digit'});
  var fmtJour = new Intl.DateTimeFormat('fr-FR', {weekday: 'short', day: '2-digit', month: '2-digit'});
  var fmtComplet = new Intl.DateTimeFormat('fr-FR', {weekday: 'short', day: '2-digit', month: '2-digit',
                                                     hour: '2-digit', minute: '2-digit', second: '2-digit'});
  var fmtMois = new Intl.DateTimeFormat('fr-FR', {month: 'long', year: 'numeric'});
  var fmtNombre = new Intl.NumberFormat('fr-FR', {maximumFractionDigits: 2});

  // base = derniere lecture de l'historique : {titre, x (s), noms, moy, min, max, direct (vrai si la vue suit l'heure)}
  var etat = {series: [], vue: 'jour', base: null, direct: [], x: [], courbes: [], titre: '',
              masquees: lisListe(CLE_MASQUEES)};
  // Un bloc par graphique : {titre, prefixes (null = « Mesures »), zone, entete, trace, graphique, courbes, unites}
  var blocs = [];

  function $(id) { return document.getElementById(id); }

  function message(texte, erreur) {
    var m = $('g_msg');
    m.textContent = texte || '';
    m.style.display = texte ? '' : 'none';
    m.style.color = erreur ? '#ff5661' : '';
  }

  function echappe(s) {
    return String(s).replace(/[&<>"']/g, function (c) { return '&#' + c.charCodeAt(0) + ';'; });
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

  // ---- ECharts : localStorage, sinon la carte (compresse) -------------------------------------------
  function memorise(cle, texte) {
    try {
      for (var i = localStorage.length - 1; i >= 0; i--) {
        var k = localStorage.key(i);
        if (k && (k.indexOf('echarts-') === 0 || k.indexOf('uPlot-') === 0) && k !== cle) localStorage.removeItem(k);
      }
      localStorage.setItem(cle, texte);
    } catch (e) { /* stockage indisponible ou plein : ECharts sera redemande a la carte */ }
  }

  function chargeECharts() {
    if (window.echarts) return Promise.resolve();
    var cle = G.bibliotheque || 'echarts';
    var texte = lis(cle);
    var source = texte ? Promise.resolve(texte) :
      fetch('/graphiques?f=echarts.js.gz').then(function (r) {
        if (!r.ok) throw new Error('ECharts absent de la carte (HTTP ' + r.status + ')');
        if (typeof DecompressionStream === 'undefined' || !r.body) {
          throw new Error('Navigateur trop ancien : il ne sait pas décompresser ECharts (DecompressionStream).');
        }
        return new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).text();
      }).then(function (t) { memorise(cle, t); return t; });
    return source.then(function (t) {
      var s = document.createElement('script');
      s.textContent = t;
      document.head.appendChild(s);
      if (!window.echarts) {
        try { localStorage.removeItem(cle); } catch (e) { /* rien */ }
        throw new Error('ECharts illisible : recharger la page.');
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
  // Entree analogique relayee par ModBus (TasmotaSlaveModBus.<esclave>.ANALOG.A<n>) : entier lu sur l'esclave, en mV
  // (ADS1115) ; l'ANALOG natif de la carte (ANALOG.A<n>) est une valeur brute de l'ADC, sans unite (decide le 2026-10-19)
  function devineUnite(nom) {
    var s = nom.split('.'), cle = s[s.length - 1];
    if (s[0] === 'TasmotaSlaveModBus' && s[s.length - 2] === 'ANALOG' && /^A\d+$/.test(cle)) return 'mV';
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
    var echelle = function (v) { return (v === null || v === undefined) ? null : v * f; };
    var rang = etat.series.indexOf(nom);
    var libelle = a.libelle || libelleDefaut(nom);
    var unite = (typeof a.unite === 'string') ? a.unite : (typeof cpt.unite === 'string') ? cpt.unite : devineUnite(nom);
    return {
      nom: nom, libelle: libelle, unite: unite, legende: libelle + (unite ? ' (' + unite + ')' : ''),
      couleur: COULEURS[(rang < 0 ? etat.courbes.length : rang) % COULEURS.length],
      moy: moy.map(echelle), min: min ? min.map(echelle) : null, max: max ? max.map(echelle) : null
    };
  }

  // ---- Blocs : « Mesures » puis un graphique par groupe du persist -----------------------------------
  function construitBlocs() {
    var zone = $('g_graphiques');
    var defs = [{titre: 'Mesures', prefixes: null}];
    Object.keys(GROUPES).forEach(function (t) {
      if (Array.isArray(GROUPES[t])) defs.push({titre: t, prefixes: GROUPES[t].map(String)});
    });
    defs.forEach(function (d) {
      var b = {titre: d.titre, prefixes: d.prefixes, graphique: null, courbes: [], unites: []};
      b.zone = document.createElement('div');
      b.entete = document.createElement('h3');
      b.entete.textContent = d.titre;
      b.entete.style.cssText = 'margin:16px 0 4px';
      b.trace = document.createElement('div');
      b.trace.className = 'g_trace';
      b.zone.appendChild(b.entete); b.zone.appendChild(b.trace);
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

  // Echelle Y d'une unite : du min au max des valeurs de ses series (visibles, dans la fenetre zoomee), 5 % de
  // marge ; elle ne descend pas sous zero quand toutes les valeurs sont positives ; une valeur constante garde
  // une hauteur lisible
  function etendue(v) {
    if (!isFinite(v.min) || !isFinite(v.max)) return [0, 1];
    if (v.min === v.max) { var m = Math.abs(v.min) * 0.05 || 1; return [v.min - m, v.max + m]; }
    var marge = (v.max - v.min) * 0.05, bas = v.min - marge;
    return [(v.min >= 0 && bas < 0) ? 0 : bas, v.max + marge];
  }

  // Repartit les courbes entre les blocs ; un bloc sans serie est masque ; le titre du bloc n'est affiche que
  // s'il y a plusieurs graphiques
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
    if (!b.courbes.length) {
      if (b.graphique) { b.graphique.dispose(); b.graphique = null; }
      ['data-titre', 'data-legende', 'data-series', 'data-fin', 'data-points', 'data-echelles', 'data-derniers',
       'data-axe-x'].forEach(function (a) {
        b.trace.removeAttribute(a);
      });
      return;
    }
    if (!b.graphique) {
      b.graphique = echarts.init(b.trace, null, {renderer: 'canvas'});
      b.graphique.on('legendselectchanged', function (e) { changeMasquees(b, e.selected); });
    }
    b.graphique.setOption(option(b), {replaceMerge: ['series', 'yAxis']});
    expose(b);
  }

  // Unites du bloc : les plus partagees d'abord, « sans unite » en dernier ; un axe Y chacune, alternativement a
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

  function option(b) {
    var texte = couleurTheme('--c_txt', '#888'), grille = 'rgba(128,128,128,0.25)';
    var unites = b.unites = unitesDe(b.courbes);
    var gauche = Math.ceil(unites.length / 2), droite = Math.floor(unites.length / 2);
    var ms = etat.x.map(function (t) { return t * 1000; });
    var suitMaintenant = etat.base && etat.base.direct;
    var series = [], selection = {};
    b.courbes.forEach(function (c, k) {
      var axe = unites.indexOf(c.unite);
      selection[c.legende] = etat.masquees.indexOf(c.nom) < 0;
      series.push({id: 'courbe-' + c.nom, name: c.legende, type: 'line', yAxisIndex: axe, showSymbol: false,
                   connectNulls: false, color: c.couleur, lineStyle: {width: 2},
                   data: ms.map(function (t, i) { return [t, c.moy[i]]; })});
      if (c.min && c.max) {       // bande min-max : min empile avec l'ecart, meme nom (la legende masque les trois)
        series.push({id: 'bande-min-' + c.nom, name: c.legende, type: 'line', yAxisIndex: axe, stack: 'bande' + k,
                     showSymbol: false, silent: true, lineStyle: {opacity: 0}, color: c.couleur,
                     data: ms.map(function (t, i) { return [t, c.min[i]]; })});
        series.push({id: 'bande-ecart-' + c.nom, name: c.legende, type: 'line', yAxisIndex: axe, stack: 'bande' + k,
                     showSymbol: false, silent: true, lineStyle: {opacity: 0}, color: c.couleur,
                     areaStyle: {color: transparence(c.couleur, 0.2)},
                     data: ms.map(function (t, i) {
                       return [t, (c.min[i] === null || c.max[i] === null) ? null : c.max[i] - c.min[i]];
                     })});
      }
    });
    return {
      animation: false,
      title: {text: etat.titre, left: 'center', top: 2, textStyle: {color: texte, fontSize: 13, fontWeight: 'normal'}},
      grid: {left: 16 + LARGEUR_AXE * gauche, right: 16 + LARGEUR_AXE * Math.max(droite, 0), top: 46, bottom: 58},
      tooltip: {trigger: 'axis', confine: true, formatter: infobulle},
      legend: {type: 'scroll', bottom: 0, data: b.courbes.map(function (c) { return c.legende; }), selected: selection,
               textStyle: {color: texte}},
      dataZoom: [{type: 'inside'}],
      xAxis: {type: 'time', max: suitMaintenant ? function (v) { return Math.max(v.max, Date.now()); } : null,
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

  // Clic dans la legende : series masquees memorisees (par chemin, pas par libelle)
  function changeMasquees(b, selection) {
    b.courbes.forEach(function (c) {
      etat.masquees = etat.masquees.filter(function (n) { return n !== c.nom; });
      if (selection[c.legende] === false) etat.masquees.push(c.nom);
    });
    ecris(CLE_MASQUEES, JSON.stringify(etat.masquees));
    expose(b);
  }

  // Etat du trace, lisible dans le DOM (diagnostic, banc) : ECharts dessine dans un canvas
  function expose(b) {
    var t = b.trace;
    t.setAttribute('data-titre', etat.titre);
    t.setAttribute('data-series', JSON.stringify(b.courbes.map(function (c) { return c.legende; })));
    t.setAttribute('data-legende', JSON.stringify(b.courbes.filter(function (c) {
      return etat.masquees.indexOf(c.nom) < 0;
    }).map(function (c) { return c.legende; })));
    t.setAttribute('data-fin', String(etat.x[etat.x.length - 1]));
    t.setAttribute('data-points', String(etat.x.length));
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

  // ---- Assemblage : historique + valeurs directes ------------------------------------------------
  // Les points directs posterieurs au dernier point de l'historique prolongent chaque courbe (vue qui suit l'heure)
  function compose() {
    var b = etat.base;
    if (!b) return;
    var fin = b.x.length ? b.x[b.x.length - 1] : -Infinity;
    var ajout = b.direct ? etat.direct.filter(function (p) { return p.t > fin; }) : [];
    var x = b.x.concat(ajout.map(function (p) { return p.t; }));
    var vides = ajout.map(function () { return null; });
    etat.titre = b.titre;
    etat.x = x;
    etat.courbes = x.length ? b.noms.map(function (nom, i) {
      var moy = b.moy[i].concat(ajout.map(function (p) { return p.valeurs.hasOwnProperty(nom) ? p.valeurs[nom] : null; }));
      return courbe(nom, moy, b.min ? b.min[i].concat(vides) : null, b.max ? b.max[i].concat(vides) : null);
    }) : [];
    trace();
    if (x.length) message('');
  }

  // ---- Vues --------------------------------------------------------------------------------------
  // 24 h : tampon RAM de la carte, un point par pas (5 min par defaut), null = pas sans mesure, puis le pas en
  // cours (moyenne des mesures deja recues)
  function vueJour() {
    var vue = etat.vue;
    return lisHisto('p=jour').then(function (d) {
      if (etat.vue !== vue) return;          // l'utilisateur a change de vue pendant la lecture
      var noms = d.series || [];
      var clos = d.t0 !== null && Array.isArray(d.valeurs) && d.valeurs.length > 0;
      var moy = clos ? d.valeurs.map(function (c) { return c.slice(); }) : noms.map(function () { return []; });
      var x = clos ? d.valeurs[0].map(function (_, i) { return d.t0 + i * d.pas; }) : [];
      if (typeof d.tEncours === 'number' && Array.isArray(d.encours) && d.encours.length === noms.length) {
        var fin = x.length ? x[x.length - 1] : null;
        if (fin !== null && d.tEncours - fin > d.pas) {           // pas sautes (coupure) : un trou, pas un trait
          x.push(fin + d.pas);
          moy.forEach(function (c) { c.push(null); });
        }
        if (fin === null || d.tEncours > fin) {
          x.push(d.tEncours);
          moy.forEach(function (c, i) { c.push(d.encours[i]); });
        }
      }
      etat.base = {titre: 'Dernières 24 h (pas de ' + Math.round(d.pas / 60) + ' min) et temps réel', x: x, noms: noms,
                   moy: moy, min: null, max: null, direct: true};
      compose();
      if (!etat.x.length) {
        message('Aucun pas de mesure encore clos depuis le démarrage : revenir dans quelques minutes.');
      } else if (moy.every(function (c) { return c.every(function (v) { return v === null; }); })) {
        message('Aucune mesure enregistrée sur les dernières 24 h.');
      }
    });
  }

  function moisCourant() { return new Date().toISOString().slice(0, 7); }

  // Mois : une ligne par heure [t, min1, moy1, max1, ...] ; une heure absente devient un trou ; le mois en cours
  // (UTC) est prolonge par les valeurs directes
  function vueMois(m) {
    var vue = etat.vue;
    return lisHisto('p=mois&m=' + encodeURIComponent(m)).then(function (d) {
      if (etat.vue !== vue) return;
      dernierMois = Date.now();
      var noms = d.seriesFichier || d.series || [], lignes = d.lignes || [];
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
      var direct = m === moisCourant();
      etat.base = {titre: libelleMois(m) + ' (moyenne horaire, bande min-max)' + (direct ? ' et temps réel' : ''), x: x,
                   noms: noms, moy: cols.map(function (c) { return c.moy; }), min: cols.map(function (c) { return c.min; }),
                   max: cols.map(function (c) { return c.max; }), direct: direct};
      compose();
      if (!etat.x.length) message('Aucune heure enregistrée pour ce mois.');
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

  // ---- Relecture periodique de l'historique affiche -----------------------------------------------
  var dernierMois = 0, relectureEnCours = false;
  function rafraichit() {
    if (document.hidden || relectureEnCours || !window.echarts) return;
    var p = null;
    if (etat.vue === 'jour') p = vueJour();
    else if (etat.vue.slice(2) === moisCourant() && Date.now() - dernierMois > PERIODE_MOIS) p = vueMois(etat.vue.slice(2));
    if (!p) return;
    relectureEnCours = true;
    p.catch(function (e) { message(e.message, true); }).then(function () { relectureEnCours = false; });
  }

  // ---- Temps reel : valeurs actuelles (/histo?p=direct) ------------------------------------------
  var minuteurDirect = null, lectureDirect = false;

  function cadenceDirect() {
    var v = parseInt(lis(CLE_DIRECT), 10);
    if (CADENCES.indexOf(v) >= 0) return v;
    return CADENCES.indexOf(+G.direct) >= 0 ? +G.direct : 10;
  }

  function lisDirect() {
    if (document.hidden || lectureDirect || !etat.base || !etat.base.direct) return;
    lectureDirect = true;
    lisHisto('p=direct').then(function (d) {
      if (typeof d.t !== 'number' || !Array.isArray(d.valeurs)) return;
      var valeurs = {};
      (d.series || []).forEach(function (nom, i) { valeurs[nom] = d.valeurs[i]; });
      var dernier = etat.direct.length ? etat.direct[etat.direct.length - 1].t : 0;
      if (d.t > dernier) etat.direct.push({t: d.t, valeurs: valeurs});      // meme t = reponse en cache de la carte
      etat.direct = etat.direct.filter(function (p) { return p.t > d.t - 3 * 3600; }).slice(-2000);
      compose();
    }).catch(function (e) { message(e.message, true); }).then(function () { lectureDirect = false; });
  }

  function demarreDirect() {
    clearInterval(minuteurDirect);
    minuteurDirect = null;
    var c = cadenceDirect();
    if (c > 0) {
      lisDirect();
      minuteurDirect = setInterval(lisDirect, c * 1000);
    }
  }

  // ---- Barre de commande : vue, temps reel, Grafana ------------------------------------------------
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
    choix.onchange = function () { montreVue(choix.value).then(demarreDirect); };

    var direct = $('g_direct');
    CADENCES.forEach(function (c) {
      var e = document.createElement('option');
      e.value = String(c);
      e.textContent = c === 0 ? 'Direct : arrêt' : 'Direct : ' + (c < 60 ? c + ' s' : '1 min');
      direct.appendChild(e);
    });
    direct.value = String(cadenceDirect());
    direct.onchange = function () { ecris(CLE_DIRECT, direct.value); demarreDirect(); };
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
      redim = setTimeout(function () { blocs.forEach(function (b) { if (b.graphique) b.graphique.resize(); }); }, 200);
    });
    chargeECharts().then(function () { return lisHisto('p=liste'); }).then(function (liste) {
      etat.series = liste.series || [];
      return montreVue(construitBarre(liste.mois || []));
    }).then(function () {
      demarreDirect();
      setInterval(rafraichit, PERIODE);
    }).catch(function (e) { message(e.message, true); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarre);
  else demarre();
})();
