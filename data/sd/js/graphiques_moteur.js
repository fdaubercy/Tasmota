// graphiques_moteur.js - Graphiques « moteur pages » de la page /graphiques (plan atelier-destinations, A3, 2026-11-05)
// Charge AVANT graphiques.js (data/fs/graphiquesFonctions.be l'envoie apres graphiques_edition.js) : window.GraphiquesMoteur.
// Un graphique de la composition marque "moteur": "pages" (schema des pages dediees, ecrit par l'atelier, valide par
// data/fs/pagesGraphiquesValidation.be) est trace par PagesGraphiques.optionDe, ce qui evite de dupliquer le trace :
//   - atelier(g) : vrai pour un tel graphique ;
//   - bloc(g, zone) : cree sa zone et rend un bloc pour graphiques.js (b.atelier, b.periode = lecture partagee 'jour' | 'mois') ;
//   - compose(b, etat) : met les donnees DEJA lues par graphiques.js (etat.donnees, etat.direct) a la forme {t, valeurs},
//     calcule les series « calc: » de la cle "calculees" du graphique (PagesFormule), trace. Rien n'est lu sur /pages.
// Le moteur (pages_graphiques_formule.js puis pages_graphiques.js, /graphiques?f=) n'est demande a la carte qu'au premier
// graphique de ce genre. Periode 'direct' (defaut des pages) : les valeurs directes de la page ; 'jour' : les 24 h ;
// 'mois' : le mois en cours (moyenne horaire). Largeur 'demi' ignoree : la page /graphiques est en une colonne.
window.GraphiquesMoteur = (function () {
  'use strict';
  var chargement = null, liquide = null;
  var G = window.GRAPHIQUES || {}, CLE_LIQUIDE = G.extension || 'liquidfill-3.1.0';

  function atelier(g) { return !!g && g.moteur === 'pages'; }

  function script(texte) {
    var s = document.createElement('script');
    s.textContent = texte;
    document.head.appendChild(s);
  }

  function moteur() {
    chargement = chargement || ['pages_graphiques_formule.js', 'pages_graphiques.js'].reduce(function (p, f) {
      return p.then(function () {
        return fetch('/graphiques?f=' + f).then(function (r) {
          if (!r.ok) throw new Error('moteur des pages absent de la carte (HTTP ' + r.status + ')');
          return r.text();
        }).then(script);
      });
    }, Promise.resolve());
    return chargement;
  }

  // Extension liquidfill (style « liquide »), comme pages_graphiques.js : localStorage versionne, sinon la carte (gzip)
  function extension() {
    liquide = liquide || new Promise(function (ok) {
      var t = null;
      try { t = localStorage.getItem(CLE_LIQUIDE); } catch (e) { t = null; }
      ok(t || fetch('/graphiques?f=liquidfill.js.gz').then(function (r) {
        if (!r.ok) throw new Error('le module liquidfill est absent de la carte (HTTP ' + r.status + ')');
        if (typeof DecompressionStream === 'undefined' || !r.body) throw new Error('navigateur trop ancien pour décompresser liquidfill');
        return new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).text();
      }).then(function (texte) {
        try { localStorage.setItem(CLE_LIQUIDE, texte); } catch (e) { /* redemande a la carte */ }
        return texte;
      }));
    }).then(script);
    return liquide;
  }

  function bloc(g, zone) {
    var div = document.createElement('div'), b = {def: g, atelier: true, zone: div, graphe: null, absentes: [],
      periode: g.periode === 'mois' ? 'mois' : 'jour', courbes: [g]};     // courbes non vide : bilan() ne crie pas « aucune mesure »
    div.className = 'g_atelier';
    div.style.height = (g.hauteur || 260) + 'px';
    zone.appendChild(div);
    b.graphique = {dispose: function () { if (b.graphe) b.graphe.dispose(); }, resize: function () { if (b.graphe) b.graphe.resize(); }};
    return b;
  }

  // Donnees {t, valeurs} du graphique, ou null tant que l'historique de sa periode n'est pas lu
  function donnees(g, etat, periode) {
    var d = etat.donnees[periode === 'mois' ? new Date().toISOString().slice(0, 7) : 'jour'], F = window.PagesFormule;
    if (!d) return null;
    var formules = {}, chemins = [];
    (g.series || []).forEach(function (s) {
      var c = typeof s === 'object' ? s.chemin : s;
      if (c.indexOf('calc:') !== 0) { chemins.push(c); return; }
      var def = (g.calculees || {})[c.slice(5)];
      formules[c] = F.analyse(def && def.formule);
      if (formules[c].ok) chemins = chemins.concat(formules[c].series);
    });
    var t, v = {};
    if (g.periode === 'mois' || g.periode === 'jour') {
      t = d.x;
      d.noms.forEach(function (n, i) { v[n] = d.moy[i]; });
    } else {
      var pts = etat.direct.slice(-360);
      t = pts.map(function (p) { return p.t; });
      chemins.forEach(function (c) { v[c] = pts.map(function (p) { return p.valeurs.hasOwnProperty(c) ? p.valeurs[c] : null; }); });
    }
    Object.keys(formules).forEach(function (nom) {
      var f = formules[nom];
      if (!f.ok) return;                                  // formule refusee : serie absente
      v[nom] = t.map(function (_, i) {
        var x = {};
        f.series.forEach(function (c) { x[c] = v[c] ? v[c][i] : null; });
        return F.calcule(f.arbre, x);
      });
    });
    return {t: t, valeurs: v};
  }

  function trace(b, etat) {
    var g = b.def, d = donnees(g, etat, b.periode), P = window.PagesGraphiques;
    if (!d) return;
    var texte = '#888';
    try { texte = getComputedStyle(b.zone).color || texte; } catch (e) { /* defaut */ }
    var o = P.optionDe(g, d, {texte: texte, grille: 'rgba(128,128,128,0.25)'});    // theme de la page (clair ou sombre)
    b.zone.setAttribute('data-style', g.type);
    b.zone.setAttribute('data-titre', o.svg !== undefined ? g.titre + (o.svg.indexOf('série absente') > 0 ? ' — série absente' : '') : o.title.text);
    b.zone.setAttribute('data-rendu', o.svg !== undefined ? 'svg' : (o.series && o.series[0] ? o.series[0].type : ''));
    if (o.svg !== undefined) { b.zone.innerHTML = o.svg; return; }
    if (!b.graphe) {
      b.zone.textContent = '';
      b.graphe = window.echarts.init(b.zone, null, {renderer: 'svg'});
      if (g.type === 'lies') { b.graphe.group = 'pg_lies'; window.echarts.connect('pg_lies'); }
    }
    b.graphe.setOption(o, true);
  }

  function compose(b, etat) {
    moteur().then(function () { return b.def.type === 'liquide' ? extension() : null; }).then(function () { trace(b, etat); }).catch(function (e) { b.zone.textContent = b.def.titre + ' : ' + e.message; });
  }

  return {atelier: atelier, bloc: bloc, compose: compose};
})();
