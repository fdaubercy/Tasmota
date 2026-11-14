"""Ecriture de l'atelier des visuels dans le depot (A7) : « Ecrire dans le depot » = POST /ecriture/prevoit (le diff, rien n'est ecrit), puis
confirmation, puis POST /ecriture/ecrit avec l'empreinte du diff. Badge de suivi par carte (GET /suivi?env= : identique | differente | absente |
inconnue) et lien « Televerser » vers la page Build (port 7700, `?env=&depuis=visuel&fichiers=&redemarrer=1`).

Le fond doit avoir ete garde (« Garder ce fond ») : l'empreinte du fond part avec la demande. Toute erreur du serveur (400 validation, 404,
409 build en cours ou depot change depuis le diff) est affichee telle quelle dans la fenetre. Texte du depot toujours insere par textContent.
"""

CSS_ECRITURE = """
.ave-diffl{background:var(--champ);border-radius:4px;max-height:200px;overflow:auto;font:12px Consolas,monospace;white-space:pre-wrap;word-break:break-all}
.ave-p{color:var(--bon)}.ave-m{color:var(--mauvais)}.ave-c{color:var(--doux)}
#ave-dlg{position:fixed;inset:0;background:var(--voile);display:flex;align-items:center;justify-content:center;z-index:20}
#ave-dlg[hidden]{display:none}
#ave-boite{background:var(--carte);color:var(--texte);border:1px solid var(--bord);border-radius:8px;padding:14px;width:min(720px,94vw);max-height:86vh;overflow:auto}
#ave-boite pre{background:var(--champ);padding:6px;border-radius:4px;max-height:160px;overflow:auto;white-space:pre-wrap;word-break:break-all;font-size:12px}
#ave-boite h2{margin:0 0 8px;font-size:15px}
"""

HTML_ECRITURE = (
    "<div id='ave-dlg' hidden><div id='ave-boite' role='dialog' aria-modal='true' aria-labelledby='ave-titre'>"
    "<h2 id='ave-titre'>Écrire dans le dépôt</h2><div id='ave-msg' role='status' class='doux'></div>"
    "<div id='ave-diff'></div><div id='ave-avert' class='alerte'></div>"
    "<div class='row'><a id='ave-lien' class='btn' hidden target='_blank' rel='noopener'>Téléverser (page Build)</a><span class='sp'></span>"
    "<button type='button' id='ave-ok'>Écrire ces fichiers</button><button type='button' id='ave-ferme'>Fermer</button></div>"
    "</div></div>"
)

HTML_BADGE = "<span id='ave-badge' class='doux' title='État du visuel de la carte par rapport au dépôt' role='status'></span>"

JS_ECRITURE = r"""
(function () {
  var AV = window.AV, $ = function (i) { return document.getElementById(i); }, prevu = null, ouvert = false;
  var BADGE = {identique: ['Carte : identique au dépôt', 'bon'], differente: ['Carte : différente du dépôt', 'alerte'], absente: ['Pas de visuel au dépôt', 'doux'], inconnue: ['Carte : état inconnu (muette)', 'doux']};
  function vide(e) { while (e.firstChild) e.removeChild(e.firstChild); }
  function msg(t, mauvais) { var m = $('ave-msg'); m.textContent = t; m.className = mauvais ? 'mauvais' : 'doux'; }
  AV.majSuivi = function () {
    var env = AV.env;
    if (!env) return;
    AV.api('GET', '/suivi?env=' + encodeURIComponent(env)).then(function (r) {
      if (env !== AV.env) return;
      var b = (r.ok && r.json && BADGE[r.json.carte]) || BADGE.inconnue;
      $('ave-badge').textContent = b[0]; $('ave-badge').className = b[1];
    }).catch(function () { $('ave-badge').textContent = BADGE.inconnue[0]; $('ave-badge').className = 'doux'; });
  };
  var c0 = AV.charge;
  AV.charge = function () { c0(); AV.majSuivi(); };
  AV.description = function () {
    return {version: 1, fond: {type: AV.fond.type, largeur: AV.larg, hauteur: AV.haut}, elements: JSON.parse(JSON.stringify(AV.elements))};
  };
  // corps EXACT envoye a prevoit, renvoye tel quel a ecrit : la page peut changer (clavier, fond invalide) pendant que la fenetre est ouverte
  var prevuCorps = null;
  function corps() { return {env: AV.env, description: AV.description(), empreinte_fond: AV.fond.empreinte}; }
  function focalisables() { return [].filter.call($('ave-boite').querySelectorAll('button,a[href],summary'), function (e) { return !e.hidden && !e.disabled && e.offsetParent !== null; }); }
  function ferme() { ouvert = false; AV.modal = false; $('ave-dlg').hidden = true; $('av-ecrire').focus(); }
  function etat(f) { return f.avant === null ? 'nouveau' : f.apres === null ? 'retiré' : 'modifié'; }
  function texte(v) { return typeof v === 'string' ? v : JSON.stringify(v); }
  // diff ligne a ligne : prefixe et suffixe communs retires, plus longue sous-suite commune sur le milieu (2000 x 2000 au plus), 3 lignes de contexte
  AV.diffLignes = function (avant, apres) {
    var a = avant.split('\n'), b = apres.split('\n'), p = 0, s = 0, ops = [], i, j, n, m, T, k;
    while (p < a.length && p < b.length && a[p] === b[p]) p++;
    while (s < a.length - p && s < b.length - p && a[a.length - 1 - s] === b[b.length - 1 - s]) s++;
    var ma = a.slice(p, a.length - s), mb = b.slice(p, b.length - s);
    for (i = 0; i < p; i++) ops.push([' ', a[i]]);
    n = ma.length; m = mb.length;
    if (n * m > 4000000) { ma.forEach(function (l) { ops.push(['-', l]); }); mb.forEach(function (l) { ops.push(['+', l]); }); }
    else {
      T = []; for (i = 0; i <= n; i++) T.push(new Uint16Array(m + 1));
      for (i = n - 1; i >= 0; i--) for (j = m - 1; j >= 0; j--) T[i][j] = ma[i] === mb[j] ? T[i + 1][j + 1] + 1 : Math.max(T[i + 1][j], T[i][j + 1]);
      i = 0; j = 0;
      while (i < n && j < m) {
        if (ma[i] === mb[j]) { ops.push([' ', ma[i]]); i++; j++; }
        else if (T[i + 1][j] >= T[i][j + 1]) { ops.push(['-', ma[i]]); i++; } else { ops.push(['+', mb[j]]); j++; }
      }
      for (; i < n; i++) ops.push(['-', ma[i]]);
      for (; j < m; j++) ops.push(['+', mb[j]]);
    }
    for (i = a.length - s; i < a.length; i++) ops.push([' ', a[i]]);
    // on ne garde que les lignes changees et 3 lignes de contexte ; « … » entre deux blocs
    var garde = new Array(ops.length).fill(false), out = [], dernier = -1;
    ops.forEach(function (o, q) { if (o[0] !== ' ') for (k = Math.max(0, q - 3); k <= Math.min(ops.length - 1, q + 3); k++) garde[k] = true; });
    ops.forEach(function (o, q) {
      if (!garde[q]) return;
      if (dernier >= 0 && q - dernier > 1) out.push(['…', '']);
      out.push(o); dernier = q;
    });
    return out;
  };
  function rendDiff(f) {
    var box = document.createElement('div'), pet = f.apres !== null && texte(f.apres).length <= 4000, lignes;
    box.className = 'ave-diffl'; box.setAttribute('tabindex', '0'); box.setAttribute('role', 'region'); box.setAttribute('aria-label', 'Différences de ' + f.chemin);
    if (f.apres === null) lignes = texte(f.avant).split('\n').slice(0, 40).map(function (l) { return ['-', l]; });
    else if (f.avant === null) lignes = texte(f.apres).split('\n').slice(0, pet ? 4000 : 60).map(function (l) { return ['+', l]; });
    else lignes = AV.diffLignes(texte(f.avant), texte(f.apres));
    if (!lignes.length) lignes = [[' ', '(aucune ligne différente)']];
    lignes.forEach(function (o) {
      var l = document.createElement('div');
      l.className = o[0] === '+' ? 'ave-p' : o[0] === '-' ? 'ave-m' : 'ave-c';
      l.textContent = (o[0] === '…' ? '…' : o[0] + ' ' + o[1]);
      box.appendChild(l);
    });
    if (f.avant === null && !pet) { var r = document.createElement('div'); r.className = 'ave-c'; r.textContent = '… (début seulement : ' + texte(f.apres).length + ' caractères)'; box.appendChild(r); }
    return box;
  }
  function montre(r) {
    var d = $('ave-diff'); vide(d); prevu = r.empreinte;
    (r.diff || []).forEach(function (f) {
      var det = document.createElement('details'), sm = document.createElement('summary');
      sm.textContent = f.chemin + ' : ' + etat(f); det.appendChild(sm); det.appendChild(rendDiff(f));
      det.open = f.avant === null || texte(f.apres === null ? '' : f.apres).length <= 4000 || (r.diff || []).length === 1;
      d.appendChild(det);
    });
    $('ave-avert').textContent = (r.avertissements || []).join(' ; ');
    msg((r.diff || []).length + ' fichier(s) à écrire. Rien n’est écrit tant que vous ne confirmez pas.', false);
    $('ave-ok').hidden = !(r.diff || []).length; $('ave-ok').disabled = false;
  }
  $('av-ecrire').addEventListener('click', function () {
    $('ave-dlg').hidden = false; ouvert = true; AV.modal = true; vide($('ave-diff')); $('ave-avert').textContent = ''; $('ave-lien').hidden = true; $('ave-ok').hidden = true; prevu = null; prevuCorps = null;
    $('ave-ferme').focus();
    if (!AV.fond || AV.fond.env !== AV.env) { msg('Gardez d’abord le fond (« Garder ce fond ») : il part avec la description.', true); return; }
    var envoi = corps();
    msg('Calcul du diff…', false);
    AV.api('POST', '/ecriture/prevoit', envoi).then(function (r) {
      if (!r.ok) { msg('Refusé : ' + (r.texte || r.status), true); return; }
      prevuCorps = envoi; montre(r.json);
    }).catch(function () { msg('Serveur injoignable', true); });
  });
  $('ave-ok').addEventListener('click', function () {
    if (!prevu || !prevuCorps) return;
    var b = this, envoi = Object.assign({}, prevuCorps, {empreinte: prevu}), env = envoi.env, type = envoi.description.fond.type;   // rien relu dans la page apres l'envoi
    b.disabled = true; msg('Écriture…', false);
    AV.api('POST', '/ecriture/ecrit', envoi).then(function (r) {
      if (!r.ok) { msg('Refusé : ' + (r.texte || r.status), true); b.disabled = false; return; }
      msg('Écrit : ' + (r.json.ecrits || []).join(', '), false); b.hidden = true; prevu = null; prevuCorps = null;
      var a = $('ave-lien'), h = location.hostname;
      if (h.indexOf(':') >= 0 && h.charAt(0) !== '[') h = '[' + h + ']';
      a.href = 'http://' + h + ':7700/?env=' + encodeURIComponent(env) + '&depuis=visuel&fichiers=visuel.json,visuel.' + type + '&redemarrer=1';
      a.hidden = false; AV.majSuivi();
    }).catch(function () { msg('Serveur injoignable', true); b.disabled = false; });
  });
  $('ave-ferme').addEventListener('click', ferme);
  document.addEventListener('keydown', function (e) {
    var t = e.target && e.target.tagName, f, k, i;
    if (!ouvert) return;
    if (e.key === 'Escape') { if (t !== 'INPUT' && t !== 'TEXTAREA' && t !== 'SELECT') ferme(); return; }
    if (e.key === 'Tab') {
      f = focalisables(); if (!f.length) return;
      k = f.indexOf(document.activeElement); i = e.shiftKey ? (k <= 0 ? f.length - 1 : k - 1) : (k < 0 || k === f.length - 1 ? 0 : k + 1);
      e.preventDefault(); f[i].focus();
    }
  });
  $('av-ecrire').disabled = false; $('av-ecrire').removeAttribute('title');
  AV.majSuivi();
})();
"""
