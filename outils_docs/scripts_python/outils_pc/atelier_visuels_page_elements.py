"""Points chauds de l'atelier des visuels (A6) : outils Voyant / Valeur / Liaison, deplacement, poignees d'une liaison, panneau de
l'element selectionne (source, style, etat simule) et mode apercu (un clic bascule l'etat simule).

Sources : GET /sources?env= SI le serveur la sert (listes de suggestions : relais, mesures, esclaves ModBus, esclaves reseau, seuils par defaut) ;
sinon saisie a la main (champs identiques, aucune suggestion). Les champs suivent atelier_visuels_description.valide : voyant = relais {n} ou
mesure {chemin, on?} ; valeur = mesure {chemin} ; liaison = modbus_serie / modbus_esclave {id} / esclave {mac} / wifi, avec seuil_s
(obligatoire en ModBus, facultatif sinon). La validation finale est celle du serveur, a l'ecriture.
"""

CSS_ELEMENTS = """
#avp-panel[hidden]{display:none}
#avp-panel label{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:4px 0}
#avp-panel input[type=text],#avp-panel input[type=number],#avp-panel select{width:9em}
#avp-panel input[type=color]{width:3em;padding:0}
.avp-poignee{fill:var(--carte);stroke:var(--acc);stroke-width:2;cursor:move}
"""

HTML_PALETTE = (
    "<div class='pan' id='avp-palette'><h2>Points chauds</h2><div class='g'>"
    "<div class='row'><button type='button' data-avp-outil='voyant' aria-pressed='false'>Voyant</button>"
    "<button type='button' data-avp-outil='valeur' aria-pressed='false'>Valeur</button>"
    "<button type='button' data-avp-outil='liaison' aria-pressed='false'>Liaison</button></div>"
    "<label class='doux'><input type='checkbox' id='avp-apercu'> Aperçu : un clic bascule l’état simulé</label>"
    "<div id='avp-note' class='doux' role='status'></div></div></div>"
)

HTML_PANNEAU = (
    "<div class='pan' id='avp-panel' hidden><h2 id='avp-titre'>Élément</h2><div class='g'>"
    "<label id='avp-l-etat'>État simulé <select id='avp-etat'></select></label>"
    "<label id='avp-l-stype'>Source <select id='avp-stype'></select></label>"
    "<label id='avp-l-n'>Relais n° <input type='number' id='avp-n' min='1' step='1' list='avp-dl-relais'></label>"
    "<label id='avp-l-chemin'>Mesure (chemin) <input type='text' id='avp-chemin' list='avp-dl-mesures' maxlength='80' placeholder='ANALOG.A1'></label>"
    "<label id='avp-l-on'>Allumé si = <input type='number' id='avp-on' step='any'></label>"
    "<label id='avp-l-id'>Esclave ModBus n° <input type='number' id='avp-id' min='1' step='1' list='avp-dl-esclaves'></label>"
    "<label id='avp-l-mac'>MAC <input type='text' id='avp-mac' list='avp-dl-reseau' maxlength='12' placeholder='AABBCCDDEEFF'></label>"
    "<label id='avp-l-seuil'>Muette après (s) <input type='number' id='avp-seuil' min='1' step='1'></label>"
    "<label id='avp-l-forme'>Forme <select id='avp-forme'><option value='rond'>rond</option><option value='carre'>carré</option></select></label>"
    "<label id='avp-l-taille'>Taille <input type='number' id='avp-taille' min='6' max='80' step='1'></label>"
    "<label id='avp-l-couleurs'>Couleurs ON / OFF / ? <span><input type='color' id='avp-c-on' value='#3ddc84'> "
    "<input type='color' id='avp-c-off' value='#8a8f98'> <input type='color' id='avp-c-inc' value='#c9ccd1'></span></label>"
    "<label id='avp-l-unite'>Unité <input type='text' id='avp-unite' maxlength='6'></label>"
    "<label id='avp-l-dec'>Décimales <input type='number' id='avp-dec' min='0' max='6' step='1'></label>"
    "<label id='avp-l-exemple'>Valeur d’essai <input type='text' id='avp-exemple' maxlength='12'></label>"
    "<div id='avp-alerte' class='alerte' role='status'></div>"
    "<button type='button' id='avp-supprime'>Supprimer l’élément</button>"
    "<datalist id='avp-dl-relais'></datalist><datalist id='avp-dl-mesures'></datalist><datalist id='avp-dl-esclaves'></datalist><datalist id='avp-dl-reseau'></datalist>"
    "</div></div>"
)

JS_ELEMENTS = r"""
(function () {
  var AV = window.AV, F = AV_FORMES, $ = function (i) { return document.getElementById(i); }, S = {outil: null, l0: null, drag: null}, SRC = null;
  var STYPES = {voyant: [['relais', 'Relais'], ['mesure', 'Entrée / mesure']], valeur: [['mesure', 'Mesure du JSON SENSOR']],
                liaison: [['modbus_serie', 'Voie série ModBus'], ['modbus_esclave', 'Esclave ModBus'], ['esclave', 'Carte (MAC)'], ['wifi', 'Wi-Fi de la carte']]};
  var ETATS = {voyant: [['on', 'allumé'], ['off', 'éteint'], ['inc', 'inconnu']], valeur: [], liaison: [['active', 'active'], ['muette', 'muette']]};
  function sel() { return AV.elCherche(AV.selEl); }
  function note(t) { $('avp-note').textContent = t || ''; }
  function remplit(s, liste) { while (s.firstChild) s.removeChild(s.firstChild); liste.forEach(function (o) { var e = document.createElement('option'); e.value = o[0]; e.textContent = o[1]; s.appendChild(e); }); }
  function datalist(id, valeurs) {
    var d = $(id); while (d.firstChild) d.removeChild(d.firstChild);
    valeurs.forEach(function (v) { var o = document.createElement('option'); o.value = String(v[0]); o.label = String(v[1] || ''); d.appendChild(o); });
  }

  // ---- sources proposees (route facultative)
  function chargeSources() {
    SRC = null;
    ['avp-dl-relais', 'avp-dl-mesures', 'avp-dl-esclaves', 'avp-dl-reseau'].forEach(function (i) { datalist(i, []); });
    if (!AV.env) return;
    var env = AV.env;
    AV.api('GET', '/sources?env=' + encodeURIComponent(env)).then(function (r) {
      if (env !== AV.env) return;
      if (!r.ok || !r.json) { note('Sources du persist non proposées par le serveur : saisie à la main.'); return; }
      SRC = r.json; note('');
      datalist('avp-dl-relais', (SRC.relais || []).map(function (x) { return [x.n, x.nom]; }));
      datalist('avp-dl-mesures', (SRC.mesures || []).map(function (x) { return [(x.chemin || []).join('.'), x.nom]; }));
      datalist('avp-dl-esclaves', (SRC.esclaves || []).map(function (x) { return [x.id, x.nom]; }));
      datalist('avp-dl-reseau', (SRC.esclaves_reseau || []).map(function (x) { return [x.mac, x.nom]; }));
    }).catch(function () { note('Sources indisponibles : saisie à la main.'); });
  }
  var c0 = AV.charge;
  AV.charge = function () { c0(); chargeSources(); };

  // seuil par defaut d'une liaison ModBus : 3 x la periode de releve du persist, 30 s sans elle (atelier_visuels_description.defauts_seuils)
  function seuilDefaut() { return SRC && SRC.periodeReleve ? 3 * SRC.periodeReleve : 30; }
  // ---- creation
  function defaut(type, x, y) {
    var id = AV.idEl(type === 'voyant' ? 'v' : type === 'valeur' ? 'n' : 'l');
    if (type === 'voyant') return {id: id, type: type, x: x, y: y, source: {type: 'relais', n: 1}, style: {forme: 'rond', taille: 14}};
    if (type === 'valeur') return {id: id, type: type, x: x, y: y, source: {type: 'mesure', chemin: ['ANALOG', 'A1']}, style: {unite: '', decimales: 1, exemple: '0'}};
    return {id: id, type: type, x: x, y: y, x2: x + 60, y2: y, source: {type: 'modbus_serie', seuil_s: seuilDefaut()}, style: {}};
  }
  function outil(t) {
    S.outil = t; S.l0 = null;
    document.querySelectorAll('[data-avp-outil]').forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-avp-outil') === t ? 'true' : 'false'); });
    note(t === 'liaison' ? 'Liaison : un clic pour le départ, un second pour l’arrivée.' : t ? 'Cliquez sur le canevas pour poser le point.' : '');
  }
  // ---- panneau
  function lignes(e) {
    var s = e.source || {}, st = e.style || {}, t = e.type;
    $('avp-l-stype').hidden = false;
    remplit($('avp-stype'), STYPES[t]); $('avp-stype').value = s.type || STYPES[t][0][0];
    var k = $('avp-stype').value;
    $('avp-l-n').hidden = !(t === 'voyant' && k === 'relais');
    $('avp-l-chemin').hidden = !(k === 'mesure'); $('avp-l-on').hidden = !(t === 'voyant' && k === 'mesure');
    $('avp-l-id').hidden = k !== 'modbus_esclave'; $('avp-l-mac').hidden = k !== 'esclave';
    $('avp-l-seuil').hidden = !(t === 'liaison' && k !== 'wifi');
    $('avp-l-forme').hidden = $('avp-l-couleurs').hidden = t !== 'voyant'; $('avp-l-taille').hidden = t === 'liaison';
    $('avp-l-unite').hidden = $('avp-l-dec').hidden = $('avp-l-exemple').hidden = t !== 'valeur';
    $('avp-l-etat').hidden = !ETATS[t].length;
    remplit($('avp-etat'), ETATS[t]); $('avp-etat').value = t === 'voyant' ? AV_CALQUES.etatVoyant(AV.sim, e.id) : (AV.sim[e.id] === 'muette' ? 'muette' : 'active');
    $('avp-n').value = s.n === undefined ? '' : s.n; $('avp-chemin').value = (s.chemin || []).join('.'); $('avp-on').value = s.on === undefined ? '' : s.on;
    $('avp-id').value = s.id === undefined ? '' : s.id; $('avp-mac').value = s.mac || ''; $('avp-seuil').value = s.seuil_s === undefined ? '' : s.seuil_s;
    $('avp-forme').value = st.forme || 'rond'; $('avp-taille').value = st.taille || 14;
    $('avp-c-on').value = st.couleur_on || '#3ddc84'; $('avp-c-off').value = st.couleur_off || '#8a8f98'; $('avp-c-inc').value = st.couleur_inconnu || '#c9ccd1';
    $('avp-unite').value = st.unite || ''; $('avp-dec').value = st.decimales === undefined ? 1 : st.decimales; $('avp-exemple').value = st.exemple === undefined ? '' : st.exemple;
  }
  function panneau() {
    var e = sel(), p = $('avp-panel');
    p.hidden = !e;
    if (!e) return;
    $('avp-titre').textContent = e.type === 'voyant' ? 'Voyant ' + e.id : e.type === 'valeur' ? 'Valeur ' + e.id : 'Liaison ' + e.id;
    if (document.activeElement && p.contains(document.activeElement) && document.activeElement.tagName !== 'SELECT') { alerte(e); return; }   // ne pas ecraser la saisie en cours
    lignes(e); alerte(e);
  }
  function alerte(e) {
    var s = e.source || {}, m = '';
    if (e.type === 'voyant' && s.type === 'relais' && !(s.n >= 1)) m = 'Indiquez le numéro du relais.';
    else if (s.type === 'mesure' && !(s.chemin && s.chemin.length)) m = 'Indiquez le chemin de la mesure.';
    else if (s.type === 'modbus_esclave' && !(s.id >= 1)) m = 'Indiquez l’identifiant ModBus de l’esclave.';
    else if (s.type === 'esclave' && !s.mac) m = 'Indiquez la MAC de la carte.';
    else if ((s.type === 'modbus_serie' || s.type === 'modbus_esclave') && !(s.seuil_s > 0)) m = 'Le seuil (en secondes) est obligatoire en ModBus.';
    $('avp-alerte').textContent = m;
  }
  function num(id) { var v = $(id).value; return v === '' || isNaN(+v) ? undefined : +v; }
  function lit() {
    var e = sel(), k = $('avp-stype').value, s, st;
    if (!e) return;
    if (k !== (e.source || {}).type) { s = {type: k}; if (k === 'modbus_serie' || k === 'modbus_esclave') s.seuil_s = seuilDefaut(); }
    else s = {type: k};
    if (k === 'relais') s.n = num('avp-n');
    if (k === 'mesure') { s.chemin = $('avp-chemin').value.split('.').map(function (x) { return x.trim(); }).filter(Boolean).slice(0, 8); if (e.type === 'voyant' && num('avp-on') !== undefined) s.on = num('avp-on'); }
    if (k === 'modbus_esclave') s.id = num('avp-id');
    if (k === 'esclave') s.mac = $('avp-mac').value.trim().toUpperCase();
    if (e.type === 'liaison' && k !== 'wifi') { var sv = num('avp-seuil'); if (sv !== undefined) s.seuil_s = sv; else if (k.indexOf('modbus') === 0 && s.seuil_s === undefined) s.seuil_s = 30; }
    st = e.style || {};
    if (e.type === 'voyant') { st.forme = $('avp-forme').value; st.couleur_on = $('avp-c-on').value; st.couleur_off = $('avp-c-off').value; st.couleur_inconnu = $('avp-c-inc').value; }
    if (e.type !== 'liaison' && num('avp-taille') !== undefined) st.taille = num('avp-taille');
    if (e.type === 'valeur') { st.unite = $('avp-unite').value; if (num('avp-dec') !== undefined) st.decimales = num('avp-dec'); st.exemple = $('avp-exemple').value; }
    var n = AV.normaliseEl({id: e.id, type: e.type, x: e.x, y: e.y, x2: e.x2, y2: e.y2, source: s, style: st});
    e.source = n.source; e.style = n.style;
    AV.sauveEls(); AV.dessine();
  }
  // ---- pointeur
  function pt(e) { var svg = $('avf-canevas'), r = svg.getBoundingClientRect(); return [(e.clientX - r.left) * AV.larg / r.width, (e.clientY - r.top) * AV.haut / r.height]; }
  function bas(e) {
    var p = pt(e).map(Math.round), n = e.target.closest ? e.target.closest('[data-el]') : null, po = e.target.closest ? e.target.closest('[data-pel]') : null, el;
    if (S.outil) {
      e.stopImmediatePropagation();
      if (S.outil === 'liaison') {
        if (!S.l0) { S.l0 = p; note('Cliquez pour l’arrivée.'); return; }
        el = defaut('liaison', S.l0[0], S.l0[1]); el.x2 = p[0]; el.y2 = p[1]; S.l0 = null;
      } else el = defaut(S.outil, p[0], p[1]);
      AV.ajoutEl(el); outil(null); return;
    }
    if (po && sel()) { e.stopImmediatePropagation(); S.drag = {mode: 'pt' + po.getAttribute('data-pel')}; return; }
    if (n) {
      e.stopImmediatePropagation();
      AV.selEl = n.getAttribute('data-el'); el = sel();
      if ($('avp-apercu').checked) { bascule(el); AV.dessine(); return; }
      S.drag = {mode: 'dep', x0: p[0], y0: p[1], o: JSON.parse(JSON.stringify(el))}; AV.dessine(); return;
    }
    if (AV.selEl) { AV.selEl = null; AV.dessine(); }
  }
  function bascule(el) {
    if (el.type === 'voyant') AV.sim[el.id] = AV_CALQUES.etatVoyant(AV.sim, el.id) === 'on' ? 'off' : 'on';
    else if (el.type === 'liaison') AV.sim[el.id] = AV.sim[el.id] === 'muette' ? 'active' : 'muette';
  }
  function bouge(e) {
    var d = S.drag, el = sel(), p, dx, dy;
    if (!d || !el) return;
    p = pt(e); dx = p[0] - d.x0; dy = p[1] - d.y0;
    if (d.mode === 'dep') {
      el.x = Math.round(d.o.x + dx); el.y = Math.round(d.o.y + dy);
      if (el.type === 'liaison') { el.x2 = Math.round(d.o.x2 + dx); el.y2 = Math.round(d.o.y2 + dy); }
    } else if (d.mode === 'pt1') { el.x = Math.round(p[0]); el.y = Math.round(p[1]); }
    else { el.x2 = Math.round(p[0]); el.y2 = Math.round(p[1]); }
    el.x = Math.max(0, Math.min(AV.larg, el.x)); el.y = Math.max(0, Math.min(AV.haut, el.y));
    if (el.type === 'liaison') { el.x2 = Math.max(0, Math.min(AV.larg, el.x2)); el.y2 = Math.max(0, Math.min(AV.haut, el.y2)); }
    AV.dessine();
  }
  function haut() { if (S.drag) { S.drag = null; AV.sauveEls(); } }
  // ---- poignees d'une liaison (par-dessus les calques)
  var d0 = AV.dessine;
  AV.dessine = function () {
    d0();
    var el = sel(), g = $('avc-g');
    if (el && el.type === 'liaison' && g) {
      [[el.x, el.y, '1'], [el.x2, el.y2, '2']].forEach(function (q) {
        g.appendChild(F.bati(['circle', {cx: q[0], cy: q[1], r: 5, 'class': 'avp-poignee', 'data-pel': q[2]}], document));
      });
    }
    panneau();
  };
  function demarre() {
    var svg = $('avf-canevas');
    svg.addEventListener('pointerdown', bas, true);
    document.addEventListener('pointermove', bouge); document.addEventListener('pointerup', haut);
    document.querySelectorAll('[data-avp-outil]').forEach(function (b) {
      b.addEventListener('click', function () { var t = b.getAttribute('data-avp-outil'); outil(S.outil === t ? null : t); });
    });
    ['avp-stype', 'avp-n', 'avp-chemin', 'avp-on', 'avp-id', 'avp-mac', 'avp-seuil', 'avp-forme', 'avp-taille', 'avp-c-on', 'avp-c-off', 'avp-c-inc', 'avp-unite', 'avp-dec', 'avp-exemple']
      .forEach(function (i) { $(i).addEventListener('input', lit); $(i).addEventListener('change', function () { lit(); if (i === 'avp-stype') { var e = sel(); if (e) lignes(e); } }); });
    $('avp-etat').addEventListener('change', function () { var e = sel(); if (e) { AV.sim[e.id] = this.value; AV.dessine(); } });
    $('avp-supprime').addEventListener('click', function () { if (AV.selEl) AV.suppEl(AV.selEl); });
    document.addEventListener('keydown', function (ev) {
      var t = ev.target && ev.target.tagName, e = sel(), k = ev.key, pas;
      if (!e || AV.modal || AV.selection !== null || t === 'INPUT' || t === 'SELECT' || t === 'TEXTAREA') {
        if (k === 'Escape' && S.outil) outil(null);
        return;
      }
      if (k === 'Delete' || k === 'Backspace') { ev.preventDefault(); AV.suppEl(e.id); }
      else if (k.indexOf('Arrow') === 0) {
        pas = ev.shiftKey ? 8 : 1; ev.preventDefault();
        var dx = k === 'ArrowLeft' ? -pas : k === 'ArrowRight' ? pas : 0, dy = k === 'ArrowUp' ? -pas : k === 'ArrowDown' ? pas : 0;
        e.x += dx; e.y += dy; if (e.type === 'liaison') { e.x2 += dx; e.y2 += dy; }
        AV.sauveEls(); AV.dessine();
      }
    });
  }
  demarre(); chargeSources(); AV.dessine();
})();
"""
