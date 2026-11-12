"""JS de l'onglet « Remarques » de l'atelier des ecrans (plan atelier-ecrans A7, spec § 5.7).

Fil des remarques de la carte (GET /remarques), epinglage sur l'objet choisi, une zone tracee sur l'ecran ou la page
(POST /remarques), Appliquer (POST /remarques/appliquer : la description modifiee revient, rejouee par `modifie` donc
annulable ; rien n'est ecrit dans ecran.json), Refuser, Repondre, et « Traiter les remarques (Claude) »
(POST /remarques/traiter puis GET /remarques/etat toutes les 2 s). Epingles numerotees dessinees sur l'ecran
(dessineEpingles, appele par dessineEcran). Textes des remarques et de Claude : textContent seulement.
"""

JS = r"""
var R = { liste: [], traitement: { etat: 'libre' }, zone: null, trace: null, outilZone: false, message: '', suivi: null, brouillon: '',
          appliquees: {} };    // id -> longueur de l'historique apres Appliquer ; envoyes avec /ecrire
var ETATS_RQ = { ouverte: 'ouverte', proposee: 'proposition de Claude', appliquee: 'appliquée', refusee: 'refusée' };

function libelleCible(c) {
  if (!c || typeof c !== 'object') return '';
  if ('objet' in c) {
    var o = objet(c.page, c.objet), t = o && o.attributs && o.attributs.text;
    return 'Objet ' + c.objet + (o ? ' · ' + o.type + (t ? ' « ' + t + ' »' : '') : '') + ' · page ' + c.page;
  }
  if ('zone' in c) return 'Zone ' + c.zone[0] + ',' + c.zone[1] + ' → ' + (c.zone[0] + c.zone[2]) + ',' + (c.zone[1] + c.zone[3]) + ' · page ' + c.page;
  return 'Page ' + c.page;
}
function cibleCourante() {
  if (R.zone && R.zonePage === E.page) return { page: E.page, zone: R.zone };      // zone d'une autre page : oubliee
  var o = choisi();
  return o ? { page: o.page, objet: o.id } : { page: E.page };
}
function libelleOperation(op) {
  if (op.op === 'ajoute') return 'ajoute ' + ((op.objet || {}).type || 'objet') + ' id ' + (op.objet || {}).id + ' page ' + (op.objet || {}).page;
  if (op.op === 'retire') return 'retire id ' + op.id + ' page ' + op.page;
  var champs = Object.keys(op.attributs || {}).map(function (k) { return k + ' = ' + JSON.stringify(op.attributs[k]); });
  ['x', 'y', 'l', 'h'].forEach(function (k) { if (k in op) champs.push(k + ' = ' + op[k]); });
  return 'id ' + op.id + ' page ' + op.page + ' : ' + champs.join(', ');
}
function messageRq(t) { R.message = t || ''; dessineRemarques(); }

function chargeRemarques() {
  var env = E.env;
  return requete('GET', '/remarques?env=' + encodeURIComponent(env)).then(function (r) {
    if (env !== E.env) return;
    R.liste = r.remarques; R.traitement = r.traitement; R.message = '';
    dessineRemarques(); dessineEpingles(); if (R.traitement.etat === 'en_cours') suitTraitement();
  }).catch(function (e) { if (env === E.env) { R.liste = []; messageRq('Remarques illisibles : ' + e.message); } });
}
function postRemarques(url, corps) {
  corps.env = E.env;
  return requete('POST', url, corps).then(function (r) {
    if (r.remarques) R.liste = r.remarques;
    R.message = ''; dessineRemarques(); dessineEpingles(); return r;
  }).catch(function (e) { messageRq(e.message); return null; });
}
function epingle() {
  var t = $('rqTexte').value.trim();
  if (!t) { messageRq('Écrire la remarque avant de l’épingler.'); return; }
  postRemarques('/remarques', { action: 'epingle', cible: cibleCourante(), texte: t, description: E.desc }).then(function (r) {
    if (r) { R.brouillon = ''; R.zone = null; dessineRemarques(); dessineEpingles(); }
  });
}
function appliqueRq(id) {
  if (lecture()) { messageRq('Revenir à l’écran de la carte pour appliquer une proposition.'); return; }
  postRemarques('/remarques/appliquer', { id: id, description: E.desc }).then(function (r) {
    if (!r) return;
    if (r.description) { modifie(function () { E.desc = r.description; }); R.appliquees[id] = E.histo.length; dessineRemarques(); }
    else messageRq('Proposition refusée par le validateur :\n' + r.erreurs.join('\n'));
  });
}
function traite() {
  if (E.histo.length) messageRq('Claude lit la description écrite dans le dépôt : les modifications de cette page ne sont pas encore écrites.');
  requete('POST', '/remarques/traiter', { env: E.env }).then(function (r) { R.traitement = r; dessineRemarques(); suitTraitement(); })
    .catch(function (e) { messageRq('Traitement refusé : ' + e.message); });
}
function suitTraitement() {
  clearTimeout(R.suivi);
  R.suivi = setTimeout(function () {
    requete('GET', '/remarques/etat').then(function (r) {
      R.traitement = r; dessineRemarques();
      if (r.etat === 'en_cours') suitTraitement(); else chargeRemarques();
    }).catch(function () { suitTraitement(); });
  }, 2000);
}

function bouton(texte, classe, action) { var b = el('button', { type: 'button', class: 'btn' + (classe ? ' ' + classe : '') }, texte); b.onclick = action; return b; }
function dessineRemarques() {
  var pn = $('remarques'); if (!pn) return;
  vide(pn);
  var compte = function (e) { return R.liste.filter(function (r) { return r.etat === e; }).length; };
  var ouvertes = compte('ouverte'), proposees = compte('proposee');
  var pa = $('pastilleRemarques');
  pa.hidden = !(ouvertes + proposees);
  pa.textContent = ouvertes + ' remarque(s) ouverte(s)' + (proposees ? ', ' + proposees + ' proposition(s)' : '');
  $('ongletRemarques').textContent = 'Remarques (' + (ouvertes + proposees) + ')';
  var tete = el('div', { class: 'ligne' });
  tete.appendChild(el('span', { class: 'pastille or' }, ouvertes + ' ouverte(s)'));
  tete.appendChild(el('span', { class: 'pastille bleu' }, proposees + ' proposée(s)'));
  var t = R.traitement || {}, enCours = t.etat === 'en_cours';
  var bt = bouton(enCours ? 'Claude travaille…' : '▶ Traiter les remarques (Claude)', 'prim', traite);
  bt.disabled = enCours || !ouvertes; bt.style.marginLeft = 'auto';
  tete.appendChild(bt); pn.appendChild(tete);
  var info = enCours ? 'En cours depuis ' + Math.round(Date.now() / 1000 - t.debut) + ' s (10 min au plus) : ' + t.message
           : t.etat === 'fini' || t.etat === 'echec' ? (t.etat === 'fini' ? 'Dernier traitement : ' : 'Dernier traitement en échec : ') + t.message
           : 'Claude lit les remarques ouvertes avec la skill lvgl-haspmota, en lecture seule, et rend des propositions vérifiées par la page.';
  pn.appendChild(el('p', { class: 'doux petit' }, info));
  if (R.message) pn.appendChild(el('div', { class: 'avert' }, R.message));
  R.liste.slice().reverse().forEach(function (r) {
    var d = el('div', { class: 'rq ' + r.etat });
    var l = el('div'); l.appendChild(el('span', { class: 'num' }, r.id)); l.appendChild(el('b', null, libelleCible(r.cible)));
    l.appendChild(el('span', { class: 'doux petit' }, ' ' + r.date + ' · ' + (ETATS_RQ[r.etat] || r.etat)));
    d.appendChild(l); d.appendChild(el('div', { class: 'rqTexte' }, r.texte));
    (r.reponses || []).forEach(function (x) { d.appendChild(el('div', { class: 'petit' }, '↳ ' + x.texte + ' (' + x.date + ')')); });
    if (r.proposition) {
      d.appendChild(el('div', { class: 'petit doux' }, 'Proposition de Claude : ' + r.proposition.texte));
      var ul = el('ul', { class: 'petit doux' });
      (r.proposition.operations || []).forEach(function (op) { ul.appendChild(el('li', null, libelleOperation(op))); });
      if ((r.proposition.operations || []).length) d.appendChild(ul);
    }
    var actions = el('div', { class: 'ligne' });
    var surCanevas = r.etat === 'proposee' && R.appliquees.hasOwnProperty(r.id);
    if (surCanevas) d.appendChild(el('div', { class: 'petit' }, 'Appliquée sur le canevas : « appliquée » à l’écriture dans le dépôt.'));
    else if (r.etat === 'proposee') actions.appendChild(bouton('Appliquer', '', function () { appliqueRq(r.id); }));
    if (r.etat === 'ouverte' || r.etat === 'proposee') actions.appendChild(bouton(r.etat === 'proposee' ? 'Refuser' : 'Clore', '', function () { postRemarques('/remarques', { action: 'refuse', id: r.id }); }));
    var rep = el('input', { type: 'text', 'aria-label': 'Réponse à la remarque ' + r.id, placeholder: 'Répondre…' });
    actions.appendChild(rep);
    actions.appendChild(bouton('Répondre', '', function () { if (rep.value.trim()) postRemarques('/remarques', { action: 'repond', id: r.id, texte: rep.value }); }));
    d.appendChild(actions); pn.appendChild(d);
  });
  pn.appendChild(el('h3', null, 'Nouvelle remarque'));
  var ta = el('textarea', { id: 'rqTexte', rows: '3', 'aria-label': 'Nouvelle remarque', style: 'width:100%' });
  ta.value = R.brouillon; ta.oninput = function () { R.brouillon = ta.value; }; pn.appendChild(ta);
  var c = el('div', { class: 'ligne' });
  c.appendChild(el('span', { class: 'doux petit' }, 'Accrochée à : ' + libelleCible(cibleCourante())));
  c.appendChild(bouton(R.outilZone ? 'Tracez sur l’écran…' : '▭ Tracer une zone', '', function () { R.outilZone = !R.outilZone; R.zone = null; dessineRemarques(); }));
  if (R.zone && R.zonePage === E.page) c.appendChild(bouton('Oublier la zone', '', function () { R.zone = null; dessineRemarques(); dessineEpingles(); }));
  var ep = bouton('Épingler', 'prim', epingle); ep.style.marginLeft = 'auto'; c.appendChild(ep);
  pn.appendChild(c);
  pn.appendChild(el('p', { class: 'doux petit' }, 'Sans zone tracée, la remarque va sur l’objet choisi, ou sinon sur la page.'));
}

function dessineEpingles(ec) {
  ec = ec || $('ecranCarte');
  Array.prototype.forEach.call(ec.querySelectorAll('.epingle,.zoneRq'), function (x) { x.remove(); });
  var pose = function (x, y, n, classe) { var p = el('div', { class: 'epingle ' + (classe || '') }, n); p.style.left = (x - 15) + 'px'; p.style.top = (y - 15) + 'px'; ec.appendChild(p); };
  var cadre = function (z, classe) { var d = el('div', { class: 'zoneRq ' + (classe || '') }); d.style.left = z[0] + 'px'; d.style.top = z[1] + 'px'; d.style.width = z[2] + 'px'; d.style.height = z[3] + 'px'; ec.appendChild(d); };
  R.liste.forEach(function (r) {
    if (!r.cible || r.cible.page !== E.page || (r.etat !== 'ouverte' && r.etat !== 'proposee')) return;
    if ('zone' in r.cible) { cadre(r.cible.zone); pose(r.cible.zone[0] + r.cible.zone[2], r.cible.zone[1], r.id, r.etat); }
    else if ('objet' in r.cible) { var o = objet(r.cible.page, r.cible.objet); if (o) pose(o.x + o.l, o.y, r.id, r.etat); }
  });
  if (R.zone && R.zonePage === E.page) cadre(R.zone, 'neuve');
  if (R.trace) cadre(R.trace, 'neuve');
}

// Trace d'une zone : ecouteurs en phase de capture, les gestes du canevas ne voient rien pendant le trace
(function () {
  var ec = $('ecranCarte'), depart = null;
  var coupe = function (ev) { ev.stopImmediatePropagation(); ev.preventDefault(); };
  ec.addEventListener('pointerdown', function (ev) {
    if (!R.outilZone || ev.button !== 0) return;
    coupe(ev); depart = pointEcran(ev); ec.setPointerCapture(ev.pointerId);
  }, true);
  var trace = function (ev) {
    var p = pointEcran(ev), D = dims();
    var x1 = Math.max(0, Math.round(Math.min(depart.x, p.x))), y1 = Math.max(0, Math.round(Math.min(depart.y, p.y)));
    var x2 = Math.min(D.l, Math.round(Math.max(depart.x, p.x))), y2 = Math.min(D.h, Math.round(Math.max(depart.y, p.y)));
    R.trace = [x1, y1, Math.max(1, x2 - x1), Math.max(1, y2 - y1)];
  };
  ec.addEventListener('pointermove', function (ev) { if (depart) { coupe(ev); trace(ev); dessineEpingles(); } }, true);
  var fin = function (ev) {
    if (!depart) return;
    coupe(ev); trace(ev); depart = null; R.outilZone = false;     // le point de relache compte
    if (R.trace && R.trace[2] > 4 && R.trace[3] > 4) { R.zone = R.trace; R.zonePage = E.page; }
    R.trace = null; dessineRemarques(); dessineEpingles();
  };
  ec.addEventListener('pointerup', fin, true); ec.addEventListener('pointercancel', fin, true);
})();
"""
