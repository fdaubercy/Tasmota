// Page /cuve (data/fs/cuvePageFonctions.be) : jauge liquide ECharts (volume en litres) et demi-cercle SVG
// (taux de remplissage en %), modeles A et H du catalogue outils_docs/jauges/.
// Valeurs : /histo?n=<nom>&p=direct toutes les 10 s, series ...niveauCuve.volume et ...niveauCuve.tauxRemplissage
// (taux en fraction 0..1). Rien n'est lu quand l'onglet est cache.
// ECharts : meme URL (/graphiques?f=echarts.js.gz) et meme cle localStorage que la page des graphiques ; extension
// echarts-liquidfill : /cuve?f=liquidfill.js.gz. Les deux sont envoyes COMPRESSES, decompresses par la page.
// Cadran des tensions (modele B, ECharts natif) : series ...valeursAnalogiques.valeurCapteurHauteur (mV a l'entree de
// l'ADS1115) et ...valeursAnalogiques.tensionSonde_V (sonde recalculee par la cuve) ; echelles dans window.CUVE.sonde.
// Valeurs tracees exposees en data-volume, data-taux, data-tension-brute et data-tension-sonde de #c_jauges (sonde du banc).
(function () {
  'use strict';
  var C = window.CUVE || {};
  var PERIODE = 10000;
  var zone = document.getElementById('c_jauges'), msg = document.getElementById('c_msg');
  var graphe = null, cadran = null, lecture = false;

  function lis(cle) { try { return localStorage.getItem(cle); } catch (e) { return null; } }

  // Garde le texte sous cle et purge les anciennes versions (cles de meme prefixe)
  function memorise(cle, prefixe, texte) {
    try {
      for (var i = localStorage.length - 1; i >= 0; i--) {
        var k = localStorage.key(i);
        if (k && k.indexOf(prefixe) === 0 && k !== cle) localStorage.removeItem(k);
      }
      localStorage.setItem(cle, texte);
    } catch (e) { /* stockage indisponible ou plein : la bibliotheque sera redemandee a la carte */ }
  }

  // Bibliotheque compressee : localStorage, sinon la carte ; injectee par <script>
  function charge(cle, prefixe, url, nom) {
    var texte = lis(cle);
    var source = texte ? Promise.resolve(texte) :
      fetch(url).then(function (r) {
        if (!r.ok) throw new Error(nom + ' absent de la carte (HTTP ' + r.status + ').');
        if (typeof DecompressionStream === 'undefined' || !r.body) {
          throw new Error('Navigateur trop ancien : il ne sait pas décompresser ' + nom + ' (DecompressionStream).');
        }
        return new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).text();
      }).then(function (t) { memorise(cle, prefixe, t); return t; });
    return source.then(function (t) {
      var s = document.createElement('script');
      s.textContent = t;
      document.head.appendChild(s);
    });
  }

  function chargeECharts() {
    var cle = C.bibliotheque || 'echarts';
    return (window.echarts ? Promise.resolve() : charge(cle, 'echarts-', '/graphiques?f=echarts.js.gz', 'ECharts')).then(function () {
      if (!window.echarts) {
        try { localStorage.removeItem(cle); } catch (e) { /* rien */ }
        throw new Error('ECharts illisible : recharger la page.');
      }
      return charge(C.extension || 'liquidfill', 'liquidfill-', '/cuve?f=liquidfill.js.gz', 'Le module liquidfill d\'ECharts');
    });
  }

  function couleur(taux) { return taux < 20 ? '#c8402f' : taux < 40 ? '#d68a12' : '#1f7fc4'; }

  // volume en litres, taux en % (nombres, ou null si la mesure manque)
  function trace(volume, taux) {
    zone.setAttribute('data-volume', volume == null ? '' : String(volume));
    zone.setAttribute('data-taux', taux == null ? '' : String(taux));
    var t = taux != null ? taux : (volume != null && C.volumeMax > 0 ? volume / C.volumeMax * 100 : null);
    var col = couleur(t == null ? 100 : t);

    var arc = document.getElementById('c_arc');
    arc.setAttribute('stroke-dasharray', (t == null ? 0 : Math.max(0, Math.min(100, t))) + ' 100');
    arc.style.stroke = col;
    document.getElementById('c_tauxTexte').textContent = (taux == null ? '-,--' : taux) + ' %';

    if (!graphe) return;
    var f = t == null ? 0 : Math.max(0, Math.min(1, t / 100));
    var calme = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    graphe.setOption({series: [{type: 'liquidFill', data: [f, f], radius: '88%', color: [col],
      waveAnimation: !calme, backgroundStyle: {color: 'rgba(127,127,127,0.15)'},
      outline: {borderDistance: 3, itemStyle: {borderColor: col, borderWidth: 3, shadowBlur: 0}},
      itemStyle: {shadowBlur: 0},
      label: {formatter: function () { return volume == null ? '-,-- L' : volume.toLocaleString('fr-FR') + ' L'; },
              fontSize: 28, color: col, insideColor: '#fff'}}]});
    if (!graphe.getModel().getSeriesByType('liquidFill').length) {
      try { localStorage.removeItem(C.extension || 'liquidfill'); } catch (e) { /* rien */ }
      graphe.dispose();
      graphe = null;
      msg.textContent = 'Extension liquidfill illisible : recharger la page.';
    }
  }

  // Cadran des tensions (modele B) : anneau exterieur = sonde recalculee (0..sondeMax_V), anneau interieur = brute a
  // l'entree de l'ADS1115 (0..entreeMax_V). Volts, ou null si la mesure manque.
  function traceTensions(brute, sonde) {
    var deux = function (v) { return v == null ? '' : v.toFixed(2); };
    zone.setAttribute('data-tension-brute', deux(brute));
    zone.setAttribute('data-tension-sonde', deux(sonde));
    document.getElementById('c_tBrute').textContent = brute == null ? '-,--' : deux(brute).replace('.', ',');
    document.getElementById('c_tSonde').textContent = sonde == null ? '-,--' : deux(sonde).replace('.', ',');
    if (!cadran) return;
    var S = C.sonde || {}, texte = getComputedStyle(document.body).color;
    var anneau = function (max, rayon, largeur, col, valeur, chiffres) {
      return {type: 'gauge', min: 0, max: max, radius: rayon, center: ['50%', '55%'], splitNumber: chiffres,
        axisLine: {lineStyle: {width: largeur, color: [[1, col]]}}, pointer: {width: largeur / 2, itemStyle: {color: col}},
        axisTick: {show: false}, splitLine: {length: largeur, lineStyle: {color: texte, width: 1}},
        axisLabel: {color: texte, fontSize: 9, distance: largeur + 3, formatter: function (v) { return +v.toFixed(1); }},
        detail: {show: false}, title: {show: false}, anchor: {show: false}, data: [{value: valeur == null ? 0 : valeur}]};
    };
    cadran.setOption({series: [anneau(S.sondeMax_V || 10, '95%', 10, '#1f7fc4', sonde, 10),
                               anneau(S.entreeMax_V || 3.3, '55%', 7, '#d68a12', brute, 3)]});
  }

  // Index de la serie dont le chemin finit par suffixe ('niveauCuve.volume'...) ; -1 si absente
  function serie(series, suffixe) {
    for (var i = 0; i < series.length; i++) {
      if (series[i] === suffixe || series[i].slice(-suffixe.length - 1) === '.' + suffixe) return i;
    }
    return -1;
  }

  function lisDirect() {
    if (document.hidden || lecture) return;
    lecture = true;
    fetch('/histo?n=' + encodeURIComponent(C.nom) + '&p=direct').then(function (r) {
      return r.text().then(function (t) {
        var d = null;
        try { d = JSON.parse(t); } catch (e) { d = null; }
        if (r.status === 404 && d && d.erreur) {
          throw new Error('Historique pas encore démarré sur la carte (2 min après le démarrage). Nouvel essai dans 10 s.');
        }
        if (!r.ok || !d || !Array.isArray(d.series) || !Array.isArray(d.valeurs)) {
          throw new Error('Lecture de /histo impossible (HTTP ' + r.status + ')');
        }
        return d;
      });
    }).then(function (d) {
      var iv = serie(d.series, 'niveauCuve.volume'), it = serie(d.series, 'niveauCuve.tauxRemplissage');
      var ib = serie(d.series, 'valeursAnalogiques.valeurCapteurHauteur'), is = serie(d.series, 'valeursAnalogiques.tensionSonde_V');
      var nombre = function (i) { return i >= 0 && typeof d.valeurs[i] === 'number' ? d.valeurs[i] : null; };
      traceTensions(nombre(ib) == null ? null : nombre(ib) / 1000, nombre(is));
      if (iv < 0 && it < 0) throw new Error('Aucune mesure de la cuve dans l\'historique de cette carte.');
      var volume = iv >= 0 && typeof d.valeurs[iv] === 'number' ? Math.round(d.valeurs[iv]) : null;
      var taux = it >= 0 && typeof d.valeurs[it] === 'number' ? Math.round(d.valeurs[it] * 100) : null;
      trace(volume, taux);
      if (graphe || !window.echarts) msg.textContent = (volume == null && taux == null) ? 'Mesure indisponible (capteur en erreur).' : '';
      document.getElementById('c_maj').textContent = 'Mis à jour à ' + new Date().toLocaleTimeString('fr-FR');
    }).catch(function (e) {
      msg.textContent = e.message;
    }).then(function () { lecture = false; });
  }

  if (!C.nom) {
    msg.textContent = 'L\'historique n\'est pas actif sur cette carte : la page ne peut pas lire le niveau de la cuve.';
    return;
  }
  chargeECharts().then(function () {
    graphe = window.echarts.init(document.getElementById('c_volume'), null, {renderer: 'svg'});
    cadran = window.echarts.init(document.getElementById('c_tension'), null, {renderer: 'svg'});
    msg.textContent = '';
  }).catch(function (e) {
    msg.textContent = e.message + ' Le taux reste affiché.';
  }).then(function () {
    lisDirect();
    setInterval(lisDirect, PERIODE);
    document.addEventListener('visibilitychange', lisDirect);
  });
})();
