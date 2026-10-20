// graphiques.js - Page /graphiques des cartes ESP32-S3 et P4 (data/fs/graphiquesFonctions.be), 2026-10-18
// Trace l'historique de la carte (/histo, data/fs/historiqueFonctions.be) avec ECharts 6, en temps reel, dans une
// page COMPOSABLE (A9, 2026-10-19) : graphiques_trace.js dessine un graphique, graphiques_edition.js edite la
// composition ; tous deux sont envoyes avant ce fichier. La carte pose window.GRAPHIQUES :
//   - bibliotheque     : cle versionnee du cache localStorage d'ECharts ('echarts-6.1.0') ;
//   - nom              : nom de l'historique ('mesures') ;
//   - graphiques       : composition enregistree (graphiques.json), ou null = composition par defaut ;
//   - affichage        : {serie: {libelle, unite, facteur}} (graphiques.json), facultatif ;
//   - groupes          : {titre: [debuts de chemin]} : composition par defaut = « Mesures » + un graphique par groupe ;
//   - compteurs        : reglages des compteurs (persist), pour leur unite ;
//   - esclaves         : {TasmotaSlaveModBusN: nom} des esclaves ModBus, pour les libelles par defaut ;
//   - grafana          : URL du tableau Grafana de la carte (vide = pas de bouton) ;
//   - rafraichissement : periode de relecture de l'historique affiche (s) ;
//   - direct           : cadence par defaut des valeurs en temps reel (s, 0 = arret).
// Une serie s'appelle par son chemin dans le JSON SENSOR de la carte (ex. 'DS18B20.Temperature').
//
// Un graphique = {titre, periode ('jour' | 'mois' = mois en cours | 'AAAA-MM'), type, series ('autres' | [{chemin,
// type?}])}. Lectures mutualisees : une lecture de /histo par periode affichee, partagee par les graphiques qui
// l'utilisent ; temps reel : une lecture /histo?p=direct pour tous les graphiques qui suivent l'heure (24 h, mois en
// cours), toutes les « direct » secondes (liste de la page, choix garde par le navigateur). L'historique est relu
// toutes les « rafraichissement » secondes (mois en cours : 15 min). Rien n'est lu quand l'onglet est cache.
// ECharts (1,1 Mo) est envoye COMPRESSE par la carte (Berry ne peut pas poser Content-Encoding) : la page le
// decompresse (DecompressionStream) et le garde dans le localStorage, redemande seulement au changement de version.
// Toute lecture ou ecriture du localStorage est sous try/catch : sans stockage, la page marche sans rien retenir.
(function () {
  'use strict';
  var G = window.GRAPHIQUES || {}, T = window.GraphiquesTrace;
  var AFFICHAGE = G.affichage || {}, GROUPES = G.groupes || {}, COMPTEURS = G.compteurs || {};
  var ESCLAVES = G.esclaves || {};
  var PERIODE = Math.max(1, +G.rafraichissement || 60) * 1000, PERIODE_MOIS = 15 * 60000;
  var CADENCES = [0, 2, 5, 10, 30, 60];
  var COULEURS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#17becf',
                  '#bcbd22', '#7f7f7f', '#aec7e8', '#ffbb78'];
  var CLE_MASQUEES = 'graphiques-masquees', CLE_DIRECT = 'graphiques-direct';
  var fmtMois = new Intl.DateTimeFormat('fr-FR', {month: 'long', year: 'numeric'});

  // donnees : periode lue ('jour' | 'AAAA-MM') -> {titre, x (s), noms, moy, min, max, suit, vide} ; lectures : en cours
  var etat = {series: [], mois: [], composition: [], donnees: {}, lectures: {}, luA: {}, direct: [],
              masquees: lisListe(CLE_MASQUEES)};
  // Un bloc par graphique : {def, periode affichee, zone, titreEl, choix, noteEl, trace, graphique, courbes, x...}
  var blocs = [];

  function $(id) { return document.getElementById(id); }
  // garde : message de l'utilisateur (composition enregistree...), que bilan() n'efface pas
  function message(texte, erreur, garde) {
    etat.messageGarde = !!garde;
    var m = $('g_msg');
    m.textContent = texte || '';
    m.style.display = texte ? '' : 'none';
    m.style.color = erreur ? '#ff5661' : '';
  }
  function copie(v) { return JSON.parse(JSON.stringify(v)); }

  // ---- localStorage, sous try/catch ----------------------------------------------------------------
  function lis(cle) { try { return localStorage.getItem(cle); } catch (e) { return null; } }
  function ecris(cle, valeur) { try { localStorage.setItem(cle, valeur); } catch (e) { /* rien */ } }
  function lisListe(cle) {
    try { var v = JSON.parse(lis(cle) || '[]'); return Array.isArray(v) ? v : []; } catch (e) { return []; }
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

  function moisCourant() { return new Date().toISOString().slice(0, 7); }
  function cleLecture(periode) { return periode === 'mois' ? moisCourant() : (periode || 'jour'); }

  function libelleMois(m) {
    var texte = fmtMois.format(new Date(+m.slice(0, 4), +m.slice(5, 7) - 1, 1));
    return texte.charAt(0).toUpperCase() + texte.slice(1) + (m.length > 7 ? ' (ancienne liste de séries)' : '');
  }
  function libellePeriode(p) {
    return p === 'jour' ? '24 dernières heures' : p === 'mois' ? 'Mois en cours' : libelleMois(p);
  }
  function periodes() { return ['jour', 'mois'].concat(etat.mois.slice().reverse()); }

  // 24 h : tampon RAM de la carte, un point par pas (5 min par defaut), null = pas sans mesure, puis le pas en
  // cours (moyenne des mesures deja recues)
  function lisJour() {
    return lisHisto('p=jour').then(function (d) {
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
      return {titre: 'Dernières 24 h (pas de ' + Math.round(d.pas / 60) + ' min) et temps réel', x: x, noms: noms,
              moy: moy, min: null, max: null, suit: true,
              vide: x.length ? '' : 'Aucun pas de mesure encore clos depuis le démarrage : revenir dans quelques minutes.'};
    });
  }

  // Mois : une ligne par heure [t, min1, moy1, max1, ...] ; une heure absente devient un trou ; le mois en cours
  // (UTC) est prolonge par les valeurs directes
  function lisMois(m) {
    return lisHisto('p=mois&m=' + encodeURIComponent(m)).then(function (d) {
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
      var suit = m === moisCourant();
      return {titre: libelleMois(m) + ' (moyenne horaire, bande min-max)' + (suit ? ' et temps réel' : ''), x: x,
              noms: noms, moy: cols.map(function (c) { return c.moy; }), min: cols.map(function (c) { return c.min; }),
              max: cols.map(function (c) { return c.max; }), suit: suit,
              vide: x.length ? '' : 'Aucune heure enregistrée pour ce mois.'};
    });
  }

  // Lecture d'une periode, partagee : deux graphiques sur la meme periode font UNE requete
  function lit(cle) {
    if (etat.lectures[cle]) return etat.lectures[cle];
    var p = (cle === 'jour' ? lisJour() : lisMois(cle)).then(function (d) {
      etat.donnees[cle] = d;
      etat.luA[cle] = Date.now();
      return d;
    });
    etat.lectures[cle] = p;
    var fin = function () { delete etat.lectures[cle]; };
    p.then(fin, fin);
    return p;
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

  function uniteDe(nom) {
    var a = AFFICHAGE[nom] || {}, cpt = COMPTEURS[nom] || {};
    return (typeof a.unite === 'string') ? a.unite : (typeof cpt.unite === 'string') ? cpt.unite : devineUnite(nom);
  }
  function legendeDe(nom) {
    var unite = uniteDe(nom);
    return ((AFFICHAGE[nom] || {}).libelle || libelleDefaut(nom)) + (unite ? ' (' + unite + ')' : '');
  }

  // Une courbe : valeurs multipliees par le facteur (ex. taux 0-1 -> %), null conserve
  function courbe(nom, type, moy, min, max, k) {
    var a = AFFICHAGE[nom] || {};
    var f = (typeof a.facteur === 'number') ? a.facteur : 1;
    var echelle = function (v) { return (v === null || v === undefined) ? null : v * f; };
    var rang = etat.series.indexOf(nom);
    return {nom: nom, legende: legendeDe(nom), unite: uniteDe(nom), type: type,
            couleur: COULEURS[(rang < 0 ? k : rang) % COULEURS.length],
            moy: moy.map(echelle), min: min ? min.map(echelle) : null, max: max ? max.map(echelle) : null};
  }

  // ---- Composition --------------------------------------------------------------------------------
  function dansPrefixes(nom, prefixes) {
    return prefixes.some(function (p) { return nom === p || nom.indexOf(p + '.') === 0; });
  }

  // Par defaut : « Mesures » (series placees nulle part ailleurs) + un graphique par groupe, resolu sur les series de
  // la periode lue (un mois ancien a sa propre liste) ; 'prefixes' n'est jamais enregistre
  function compositionDefaut() {
    var c = [{titre: 'Mesures', periode: 'jour', type: 'courbe', series: 'autres'}];
    Object.keys(GROUPES).forEach(function (t) {
      if (Array.isArray(GROUPES[t])) c.push({titre: t, periode: 'jour', type: 'courbe', prefixes: GROUPES[t].map(String)});
    });
    return c;
  }

  // Composition explicite (pour l'edition et l'enregistrement) : les groupes deviennent des listes de series
  function explicite(composition) {
    return composition.map(function (g) {
      var e = {titre: g.titre, periode: g.periode, type: g.type, series: g.series};
      if (g.prefixes) {
        e.series = etat.series.filter(function (n) { return dansPrefixes(n, g.prefixes); })
                              .map(function (n) { return {chemin: n}; });
      }
      return copie(e);
    }).filter(function (g) { return g.series === 'autres' || g.series.length > 0; });
  }

  // Series d'un graphique pour une periode (noms = series de la periode lue) : [{chemin, type?}]
  function seriesDu(g, noms) {
    if (g.prefixes) return noms.filter(function (n) { return dansPrefixes(n, g.prefixes); }).map(function (n) { return {chemin: n}; });
    if (Array.isArray(g.series)) return g.series;
    return noms.filter(function (n) {           // 'autres' : placees dans aucun autre graphique
      return !etat.composition.some(function (o) {
        if (o === g) return false;
        if (o.prefixes) return dansPrefixes(n, o.prefixes);
        return Array.isArray(o.series) && o.series.some(function (s) { return s.chemin === n; });
      });
    }).map(function (n) { return {chemin: n}; });
  }

  // ---- Blocs : un graphique de la composition -----------------------------------------------------
  function construitBlocs() {
    blocs.forEach(function (b) { if (b.graphique) b.graphique.dispose(); });
    blocs = [];
    var zone = $('g_graphiques');
    zone.innerHTML = '';
    etat.composition.forEach(function (g) {
      var b = {def: g, periode: g.periode || 'jour', graphique: null, courbes: [], x: [], absentes: []};
      b.zone = document.createElement('div');
      b.zone.className = 'g_bloc';
      var entete = document.createElement('div');
      entete.className = 'g_entete';
      b.titreEl = document.createElement('h3');
      b.titreEl.textContent = g.titre;
      b.choix = document.createElement('select');
      b.choix.className = 'g_periode';
      b.choix.title = 'Période de ce graphique';
      periodes().forEach(function (p) {
        var o = document.createElement('option');
        o.value = p; o.textContent = libellePeriode(p);
        b.choix.appendChild(o);
      });
      if (periodes().indexOf(b.periode) < 0) {          // mois enregistre puis supprime de la carte
        var o = document.createElement('option');
        o.value = b.periode; o.textContent = libellePeriode(b.periode) + ' (absent)';
        b.choix.appendChild(o);
      }
      b.choix.value = b.periode;
      b.choix.onchange = function () { b.periode = b.choix.value; affiche([b]); };
      entete.appendChild(b.titreEl); entete.appendChild(b.choix);
      b.noteEl = document.createElement('p');
      b.noteEl.className = 'g_note';
      b.trace = document.createElement('div');
      b.trace.className = 'g_trace';
      b.zone.appendChild(entete); b.zone.appendChild(b.noteEl); b.zone.appendChild(b.trace);
      zone.appendChild(b.zone);
      blocs.push(b);
    });
  }

  // Assemble un bloc : historique de sa periode + valeurs directes posterieures (si la periode suit l'heure)
  function compose(b) {
    var d = etat.donnees[cleLecture(b.periode)];
    if (!d) return;
    var fin = d.x.length ? d.x[d.x.length - 1] : -Infinity;
    var ajout = d.suit ? etat.direct.filter(function (p) { return p.t > fin; }) : [];
    var x = d.x.concat(ajout.map(function (p) { return p.t; }));
    var vides = ajout.map(function () { return null; });
    var voulues = seriesDu(b.def, d.noms);
    b.x = x; b.suit = d.suit; b.titreVue = d.titre;
    b.absentes = voulues.filter(function (s) { return d.noms.indexOf(s.chemin) < 0; }).map(function (s) { return s.chemin; });
    b.courbes = x.length ? voulues.filter(function (s) { return d.noms.indexOf(s.chemin) >= 0; }).map(function (s, k) {
      var i = d.noms.indexOf(s.chemin);
      var moy = d.moy[i].concat(ajout.map(function (p) { return p.valeurs.hasOwnProperty(s.chemin) ? p.valeurs[s.chemin] : null; }));
      return courbe(s.chemin, T.TYPES.indexOf(s.type) >= 0 ? s.type : (b.def.type || 'courbe'), moy,
                    d.min ? d.min[i].concat(vides) : null, d.max ? d.max[i].concat(vides) : null, k);
    }) : [];
    var visible = b.courbes.length > 0 || (b.absentes.length > 0 && d.x.length > 0);
    b.zone.style.display = visible ? '' : 'none';
    b.noteEl.textContent = b.absentes.length ? 'Absente(s) de cette période : ' + b.absentes.map(legendeDe).join(', ') : '';
    b.noteEl.style.display = b.absentes.length ? '' : 'none';
    T.dessine(b, etat.masquees, changeMasquees);
  }

  // Message general : le premier motif d'absence de donnees quand aucun graphique n'a de courbe
  function bilan() {
    if (blocs.some(function (b) { return b.courbes.length > 0; })) { if (!etat.messageGarde) message(''); return; }
    var d = blocs.map(function (b) { return etat.donnees[cleLecture(b.periode)]; }).filter(Boolean)[0];
    if (d) message(d.vide || 'Aucune mesure à afficher pour cette composition.');
  }

  // Lit les periodes des blocs donnes (une requete par periode) puis les redessine
  function affiche(liste) {
    var cles = [];
    liste.forEach(function (b) { var c = cleLecture(b.periode); if (cles.indexOf(c) < 0) cles.push(c); });
    return Promise.all(cles.map(function (c) {
      return lit(c).then(function () {
        blocs.forEach(function (b) { if (cleLecture(b.periode) === c) compose(b); });
      });
    })).then(bilan).catch(function (e) { message(e.message, true); });
  }

  // Clic dans la legende : series masquees memorisees (par chemin, pas par libelle), dans tous les graphiques
  function changeMasquees(b, selection) {
    b.courbes.forEach(function (c) {
      etat.masquees = etat.masquees.filter(function (n) { return n !== c.nom; });
      if (selection[c.legende] === false) etat.masquees.push(c.nom);
    });
    ecris(CLE_MASQUEES, JSON.stringify(etat.masquees));
    T.expose(b, etat.masquees);
  }

  // Nouvelle composition (null = par defaut) : blocs recrees puis dessines
  function applique(composition) {
    etat.composition = Array.isArray(composition) ? copie(composition) : compositionDefaut();
    etat.estDefaut = !Array.isArray(composition);
    construitBlocs();
    return affiche(blocs);
  }

  // ---- Relecture periodique de l'historique affiche -----------------------------------------------
  function rafraichit() {
    if (document.hidden || !window.echarts) return;
    var cles = [];
    blocs.forEach(function (b) {
      var c = cleLecture(b.periode);
      if (cles.indexOf(c) >= 0 || etat.lectures[c]) return;
      if (c === 'jour' || (c === moisCourant() && Date.now() - (etat.luA[c] || 0) > PERIODE_MOIS)) cles.push(c);
    });
    cles.forEach(function (c) {
      lit(c).then(function () {
        blocs.forEach(function (b) { if (cleLecture(b.periode) === c) compose(b); });
        bilan();
      }).catch(function (e) { message(e.message, true); });
    });
  }

  // ---- Temps reel : valeurs actuelles (/histo?p=direct), une lecture pour toute la page ---------------
  var minuteurDirect = null, lectureDirect = false;

  function cadenceDirect() {
    var v = parseInt(lis(CLE_DIRECT), 10);
    if (CADENCES.indexOf(v) >= 0) return v;
    return CADENCES.indexOf(+G.direct) >= 0 ? +G.direct : 10;
  }

  function lisDirect() {
    if (document.hidden || lectureDirect) return;
    if (!blocs.some(function (b) { var d = etat.donnees[cleLecture(b.periode)]; return d && d.suit; })) return;
    lectureDirect = true;
    lisHisto('p=direct').then(function (d) {
      if (typeof d.t !== 'number' || !Array.isArray(d.valeurs)) return;
      var valeurs = {};
      (d.series || []).forEach(function (nom, i) { valeurs[nom] = d.valeurs[i]; });
      var dernier = etat.direct.length ? etat.direct[etat.direct.length - 1].t : 0;
      if (d.t > dernier) etat.direct.push({t: d.t, valeurs: valeurs});      // meme t = reponse en cache de la carte
      etat.direct = etat.direct.filter(function (p) { return p.t > d.t - 3 * 3600; }).slice(-2000);
      blocs.forEach(function (b) { var x = etat.donnees[cleLecture(b.periode)]; if (x && x.suit) compose(b); });
      bilan();
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

  // ---- Enregistrement de la composition sur la carte (POST /graphiques) --------------------------
  function enregistre(composition) {
    return fetch('/graphiques', {method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                                 body: 'composition=' + encodeURIComponent(JSON.stringify(composition))})
      .catch(function () { throw new Error('Carte injoignable : composition non enregistrée.'); })
      .then(function (r) {
        return r.text().then(function (t) {
          var d = null;
          try { d = JSON.parse(t); } catch (e) { d = null; }
          if (r.ok && d && d.ok) return d;
          throw new Error(d && d.erreur ? 'Refusé par la carte : ' + d.erreur : 'Enregistrement impossible (HTTP ' + r.status + ')');
        });
      });
  }

  // ---- Barre de commande : temps reel, Grafana -----------------------------------------------------
  function construitDirect() {
    var direct = $('g_direct');
    CADENCES.forEach(function (c) {
      var e = document.createElement('option');
      e.value = String(c);
      e.textContent = c === 0 ? 'Direct : arrêt' : 'Direct : ' + (c < 60 ? c + ' s' : '1 min');
      direct.appendChild(e);
    });
    direct.value = String(cadenceDirect());
    direct.onchange = function () { ecris(CLE_DIRECT, direct.value); demarreDirect(); };
  }

  // Bouton Grafana : pose avant toute lecture, utile meme si l'historique de la carte n'a pas demarre
  function construitGrafana() {
    if (!G.grafana) return;
    var b = $('g_grafana');
    b.style.display = '';
    b.onclick = function () { window.open(G.grafana, '_blank', 'noopener'); };
  }

  // Interface donnee a graphiques_edition.js
  var api = {
    TYPES: T.TYPES, message: function (t, e) { message(t, e, true); }, enregistre: enregistre, periodes: periodes, libellePeriode: libellePeriode,
    legende: legendeDe, series: function () { return etat.series.slice(); },
    composition: function () { return explicite(etat.composition); },
    defaut: function () { return explicite(compositionDefaut()); },
    estDefaut: function () { return !!etat.estDefaut; },
    applique: function (c) { return applique(c).then(demarreDirect); },
    montre: function (oui) { $('g_graphiques').style.display = oui ? '' : 'none'; }
  };

  function demarre() {
    construitGrafana();
    construitDirect();
    message('Chargement...');
    var redim = null;
    window.addEventListener('resize', function () {
      clearTimeout(redim);
      redim = setTimeout(function () { blocs.forEach(function (b) { if (b.graphique) b.graphique.resize(); }); }, 200);
    });
    chargeECharts().then(function () { return lisHisto('p=liste'); }).then(function (liste) {
      etat.series = liste.series || [];
      etat.mois = liste.mois || [];
      return applique(Array.isArray(G.graphiques) ? G.graphiques : null);
    }).then(function () {
      demarreDirect();
      setInterval(rafraichit, PERIODE);
      if (typeof window.GraphiquesEdition === 'function') window.GraphiquesEdition(api);
      document.documentElement.setAttribute('data-graphiques-pret', '1');
    }).catch(function (e) { message(e.message, true); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarre);
  else demarre();
})();
