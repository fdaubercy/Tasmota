// pages_graphiques_formule.js - Formules des valeurs calculees des pages de graphiques (atelier des graphiques, plan A3)
// Envoye AVANT pages_graphiques.js, dans le meme <script> (data/fs/pagesGraphiques.be::pagesGraphiques_page).
// Analyseur a LISTE BLANCHE, jamais d'evaluation dynamique : grammaire de reference dans le docstring de
// outils_docs/scripts_python/outils_pc/atelier_graphiques_description.py (meme verdict que valide_formule, verifie
// par le banc test_pages_graphiques.mjs sur chaque formule de cas_description.json).
//   expr := terme (('+'|'-') terme)* ; terme := facteur (('*'|'/') facteur)* ;
//   facteur := ['-'] (nombre | chemin | fonction '(' expr (',' expr)* ')' | '(' expr ')')
// PagesFormule.analyse(texte) -> {ok, series (chemins cites, sans doublon), erreur, arbre}
// PagesFormule.calcule(arbre, valeurs {chemin: nombre|null}) -> nombre, ou null si une serie manque, vaut null, ou si
// le resultat n'est pas fini (division par zero). round = Math.round (demi vers +infini).
var PagesFormule = (function () {
  'use strict';
  var FONCTIONS = ['min', 'max', 'abs', 'round'];
  var INTERDITS = ['constructor', 'prototype'];
  var JETON = /[ \t]*(?:([0-9]+(?:\.[0-9]+)?)|([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*)|([-+*/(),]))/y;

  function cheminOk(s) {
    return s.length <= 96 && s.indexOf('__') < 0 && s.split('.').every(function (seg) { return INTERDITS.indexOf(seg) < 0; });
  }

  function jetons(f) {
    var out = [], i = 0, m;
    while (f.slice(i).replace(/^[ \t]+|[ \t]+$/g, '') !== '') {
      JETON.lastIndex = i;
      m = JETON.exec(f);
      if (!m) return null;
      i = JETON.lastIndex;
      out.push(m[1] ? {g: 'n', t: m[1]} : m[2] ? {g: 'c', t: m[2]} : {g: 's', t: m[3]});
    }
    return out;
  }

  function analyse(f) {
    if (typeof f !== 'string' || f.replace(/^[ \t]+|[ \t]+$/g, '') === '' || new TextEncoder().encode(f).length > 200) {
      return {ok: false, series: [], erreur: 'formule vide, non textuelle ou trop longue', arbre: null};
    }
    var t = jetons(f);
    if (!t) return {ok: false, series: [], erreur: 'formule interdite : caractère hors liste blanche', arbre: null};
    var pos = 0, series = [];
    function suit(x) { return pos < t.length && t[pos].g === 's' && t[pos].t === x; }
    function refuse(motif) { throw new Error(motif); }
    function expr() {
      var a = terme();
      while (suit('+') || suit('-')) { var op = t[pos++].t; a = {op: op, g: a, d: terme()}; }
      return a;
    }
    function terme() {
      var a = facteur();
      while (suit('*') || suit('/')) { var op = t[pos++].t; a = {op: op, g: a, d: facteur()}; }
      return a;
    }
    function facteur() {
      var moins = suit('-');
      if (moins) pos++;
      if (pos >= t.length) refuse('opérande attendu en fin de formule');
      var j = t[pos++], n;
      if (j.g === 'n') n = {n: parseFloat(j.t)};
      else if (j.g === 'c') {
        if (!cheminOk(j.t)) refuse('chemin refusé ' + j.t);
        if (FONCTIONS.indexOf(j.t) >= 0) {
          if (!suit('(')) refuse('fonction ' + j.t + ' sans parenthèse');
          pos++;
          var args = [expr()];
          while (suit(',')) { pos++; args.push(expr()); }
          if (!suit(')')) refuse('parenthèse fermante attendue');
          pos++;
          var une = j.t === 'abs' || j.t === 'round';
          if (une ? args.length !== 1 : args.length < 2) refuse('arité de ' + j.t + ' : ' + args.length + ' argument(s)');
          n = {f: j.t, a: args};
        } else {
          if (series.indexOf(j.t) < 0) series.push(j.t);
          n = {c: j.t};
        }
      } else if (j.t === '(') {
        n = expr();
        if (!suit(')')) refuse('parenthèse fermante attendue');
        pos++;
      } else refuse('opérande attendu avant ' + j.t);
      return moins ? {neg: n} : n;
    }
    try {
      var arbre = expr();
      if (pos !== t.length) refuse('jeton inattendu ' + t[pos].t);
      return {ok: true, series: series, erreur: '', arbre: arbre};
    } catch (e) {
      return {ok: false, series: [], erreur: 'formule interdite : ' + e.message, arbre: null};
    }
  }

  function valeur(n, v) {
    if ('n' in n) return n.n;
    if ('c' in n) { var x = Object.prototype.hasOwnProperty.call(v, n.c) ? v[n.c] : null; return typeof x === 'number' ? x : null; }
    if ('neg' in n) { var y = valeur(n.neg, v); return y === null ? null : -y; }
    if ('f' in n) {
      var a = n.a.map(function (x) { return valeur(x, v); });
      if (a.indexOf(null) >= 0) return null;
      return n.f === 'abs' ? Math.abs(a[0]) : n.f === 'round' ? Math.round(a[0]) : Math[n.f].apply(null, a);
    }
    var g = valeur(n.g, v), d = valeur(n.d, v);
    if (g === null || d === null) return null;
    return n.op === '+' ? g + d : n.op === '-' ? g - d : n.op === '*' ? g * d : g / d;
  }

  function calcule(arbre, valeurs) {
    if (!arbre) return null;
    var r = valeur(arbre, valeurs || {});
    return (r === null || !isFinite(r)) ? null : r;
  }

  return {analyse: analyse, calcule: calcule, FONCTIONS: FONCTIONS};
})();
