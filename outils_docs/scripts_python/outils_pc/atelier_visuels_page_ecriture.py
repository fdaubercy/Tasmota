"""Ecriture de l'atelier des visuels dans le depot (A7) : « Ecrire dans le depot » = POST /ecriture/prevoit (le diff, rien n'est ecrit), puis
confirmation, puis POST /ecriture/ecrit avec l'empreinte du diff. Badge de suivi par carte (GET /suivi?env= : identique | differente | absente |
inconnue) et lien « Televerser » vers la page Build (port 7700, `?env=&depuis=visuel&fichiers=&redemarrer=1`).

Le fond doit avoir ete garde (« Garder ce fond ») : l'empreinte du fond part avec la demande. Toute erreur du serveur (400 validation, 404,
409 build en cours ou depot change depuis le diff) est affichee telle quelle dans la fenetre. Texte du depot toujours insere par textContent.
"""

CSS_ECRITURE = """
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
  function corps(extra) { return Object.assign({env: AV.env, description: AV.description(), empreinte_fond: AV.fond.empreinte}, extra || {}); }
  function ferme() { ouvert = false; $('ave-dlg').hidden = true; $('av-ecrire').focus(); }
  function etat(f) { return f.avant === null ? 'nouveau' : f.apres === null ? 'retiré' : 'modifié'; }
  function texte(v) { var t = typeof v === 'string' ? v : JSON.stringify(v); return t.length > 3000 ? t.slice(0, 3000) + '\n… (' + t.length + ' caractères)' : t; }
  function montre(r) {
    var d = $('ave-diff'); vide(d); prevu = r.empreinte;
    (r.diff || []).forEach(function (f) {
      var det = document.createElement('details'), sm = document.createElement('summary'), pre = document.createElement('pre');
      sm.textContent = f.chemin + ' : ' + etat(f); pre.textContent = f.apres === null ? '(retiré)' : texte(f.apres);
      det.appendChild(sm); det.appendChild(pre); d.appendChild(det);
    });
    $('ave-avert').textContent = (r.avertissements || []).join(' ; ');
    msg((r.diff || []).length + ' fichier(s) à écrire. Rien n’est écrit tant que vous ne confirmez pas.', false);
    $('ave-ok').hidden = !(r.diff || []).length; $('ave-ok').disabled = false;
  }
  $('av-ecrire').addEventListener('click', function () {
    $('ave-dlg').hidden = false; ouvert = true; vide($('ave-diff')); $('ave-avert').textContent = ''; $('ave-lien').hidden = true; $('ave-ok').hidden = true; prevu = null;
    $('ave-ferme').focus();
    if (!AV.fond || AV.fond.env !== AV.env) { msg('Gardez d’abord le fond (« Garder ce fond ») : il part avec la description.', true); return; }
    msg('Calcul du diff…', false);
    AV.api('POST', '/ecriture/prevoit', corps()).then(function (r) {
      if (!r.ok) { msg('Refusé : ' + (r.texte || r.status), true); return; }
      montre(r.json);
    }).catch(function () { msg('Serveur injoignable', true); });
  });
  $('ave-ok').addEventListener('click', function () {
    if (!prevu) return;
    var b = this; b.disabled = true; msg('Écriture…', false);
    AV.api('POST', '/ecriture/ecrit', corps({empreinte: prevu})).then(function (r) {
      if (!r.ok) { msg('Refusé : ' + (r.texte || r.status), true); b.disabled = false; return; }
      msg('Écrit : ' + (r.json.ecrits || []).join(', '), false); b.hidden = true; prevu = null;
      var a = $('ave-lien');
      a.href = 'http://' + location.hostname + ':7700/?env=' + encodeURIComponent(AV.env) + '&depuis=visuel&fichiers=visuel.json,visuel.' + AV.fond.type + '&redemarrer=1';
      a.hidden = false; AV.majSuivi();
    }).catch(function () { msg('Serveur injoignable', true); b.disabled = false; });
  });
  $('ave-ferme').addEventListener('click', ferme);
  document.addEventListener('keydown', function (e) { if (ouvert && e.key === 'Escape') ferme(); });
  $('av-ecrire').disabled = false; $('av-ecrire').removeAttribute('title');
  AV.majSuivi();
})();
"""
