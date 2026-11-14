"""Assistant IA facultatif de l'atelier des visuels (A9, spec § 2.10) : panneau de la page.

Procede choisi parmi GET /ia/fournisseurs ; consigne ; AVERTISSEMENT avant chaque envoi qui nomme le service et dit ce qui part (la photo recadree) ;
pour un service externe, case de confirmation a recocher a CHAQUE envoi ; compteur de quota (GET /ia/quota et reponse de /ia/demande) ; depot de la
cle par POST /ia/cle (le champ est vide apres l'envoi, la cle n'est jamais relue ni gardee par la page : le serveur ne rend que « presente » et les
4 derniers caracteres). Resultat : un SVG deja nettoye par le serveur, ouvert dans l'editeur comme POINT DE DEPART : seuls les <rect> et <polygon>
deviennent des formes (le reste est compte et signale), ajoutees au dessin en une etape annulable. Un resultat « operations » est signale, non applique.
"""

CSS_IA = """
#avia-panel textarea{width:100%;min-height:70px;background:var(--champ);color:var(--texte);border:1px solid var(--bord);border-radius:6px;padding:6px;font:inherit}
#avia-avert{border:1px solid var(--alerte);border-radius:6px;padding:6px}
"""

HTML_IA = (
    "<div class='pan' id='avia-panel'><h2>Assistant IA (facultatif)</h2><div class='g'>"
    "<label class='row doux' for='avia-four'>Procédé</label><select id='avia-four'></select>"
    "<div id='avia-gratuit' class='doux'></div>"
    "<label class='doux' for='avia-consigne'>Consigne</label>"
    "<textarea id='avia-consigne' maxlength='2000' placeholder='Dessine la façade à plat, murs en briques, toit en tuiles…'></textarea>"
    "<div id='avia-avert' role='note'></div>"
    "<label id='avia-conf-l' hidden class='doux'><input type='checkbox' id='avia-confirme'> <span id='avia-conf-t'></span></label>"
    "<div id='avia-quota' class='doux' role='status'></div>"
    "<div id='avia-cle-b' hidden><label class='row doux' for='avia-cle'>Clé d’API</label>"
    "<div class='row'><input type='password' id='avia-cle' autocomplete='off' maxlength='512' spellcheck='false' aria-describedby='avia-cle-etat'>"
    "<button type='button' id='avia-cle-ok'>Enregistrer</button></div><div id='avia-cle-etat' class='doux'></div></div>"
    "<button type='button' id='avia-envoi' disabled>Envoyer la photo</button>"
    "<div id='avia-etat' class='doux' role='status'></div>"
    "<button type='button' id='avia-ouvre' hidden>Ouvrir dans l’éditeur</button>"
    "</div></div>"
)

JS_IA = r"""
(function () {
  var AV = window.AV, F = AV_FORMES, $ = function (i) { return document.getElementById(i); }, four = [], regl = {}, resultat = null, enCours = false;
  function etat(t, mauvais) { var e = $('avia-etat'); e.textContent = t; e.className = mauvais ? 'mauvais' : 'doux'; }
  function courant() { var id = $('avia-four').value; return four.filter(function (f) { return f.id === id; })[0] || null; }
  function majQuota(q) {
    $('avia-quota').textContent = q ? 'Envois aujourd’hui : ' + q.envois_jour + (q.plafond ? ' sur ' + q.plafond : '') + ' · ' + (q.etat === 'rouge' ? 'limite atteinte' + (q.reprise ? ' (reprise ' + q.reprise + ')' : '') : q.etat === 'orange' ? 'proche de la limite' : 'ok') : '';
    $('avia-quota').className = q && q.etat === 'rouge' ? 'mauvais' : q && q.etat === 'orange' ? 'alerte' : 'doux';
  }
  function peut() {
    var f = courant();
    $('avia-envoi').disabled = enCours || !f || !f.disponible || !AV.src || !$('avia-consigne').value.trim() || (f.externe && !$('avia-confirme').checked);
  }
  function majFour() {
    var f = courant(), r = f && regl[f.id];
    $('avia-gratuit').textContent = f ? (f.gratuit ? 'Offre : ' + f.gratuit : '') + (f.disponible ? '' : ' · indisponible sur ce poste') : '';
    $('avia-avert').textContent = !f ? '' : f.externe
      ? 'Avertissement : la photo recadrée sera envoyée à « ' + f.nom + ' », un service externe, avec votre consigne. N’envoyez pas une photo qui montre des personnes ou des informations privées.'
      : 'La photo recadrée est traitée sur ce PC par « ' + f.nom + ' » : elle ne part pas vers un service externe.';
    $('avia-conf-l').hidden = !(f && f.externe); $('avia-confirme').checked = false;
    $('avia-conf-t').textContent = f ? 'Je confirme l’envoi de ma photo à « ' + f.nom + ' »' : '';
    $('avia-cle-b').hidden = !(f && f.cle_requise);
    $('avia-cle-etat').textContent = r && r.cle && r.cle.presente ? 'Clé enregistrée (se termine par ' + (r.cle.fin || '…') + ')' : 'Aucune clé enregistrée';
    majQuota(null);
    if (f) AV.api('GET', '/ia/quota?fournisseur=' + encodeURIComponent(f.id)).then(function (q) { if (q.ok && courant() && courant().id === f.id) majQuota(q.json); });
    peut();
  }
  AV.api('GET', '/ia/fournisseurs').then(function (r) {
    if (!r.ok) { etat('Assistant indisponible : ' + (r.texte || r.status), true); return; }
    four = r.json.fournisseurs || []; regl = r.json.reglages || {};
    var s = $('avia-four');
    four.forEach(function (f) { var o = document.createElement('option'); o.value = f.id; o.textContent = f.nom + (f.externe ? ' (service externe)' : ' (sur ce PC)'); s.appendChild(o); });
    majFour();
  }).catch(function () { etat('Serveur injoignable', true); });
  $('avia-four').addEventListener('change', majFour);
  $('avia-confirme').addEventListener('change', peut); $('avia-consigne').addEventListener('input', peut);
  AV.surChangement(peut);
  $('avia-cle-ok').addEventListener('click', function () {
    var f = courant(), c = $('avia-cle').value;
    if (!f || !c) return;
    AV.api('POST', '/ia/cle', {fournisseur: f.id, cle: c}).then(function (r) {
      $('avia-cle').value = '';
      if (!r.ok) { $('avia-cle-etat').textContent = 'Clé refusée : ' + (r.texte || r.status); return; }
      regl[f.id] = Object.assign(regl[f.id] || {}, {cle: r.json.cle}); majFour();
    }).catch(function () { $('avia-cle').value = ''; $('avia-cle-etat').textContent = 'Serveur injoignable'; });
  });
  $('avia-envoi').addEventListener('click', function () {
    var f = courant();
    if (!f || !AV.src) return;
    var photo = AV.photo.toDataURL('image/jpeg', 0.85).split(',')[1], conf = f.externe && $('avia-confirme').checked;
    enCours = true; resultat = null; $('avia-ouvre').hidden = true; etat('Envoi à « ' + f.nom + ' »…', false); peut();
    AV.api('POST', '/ia/demande', {env: AV.env, fournisseur: f.id, consigne: $('avia-consigne').value, confirme: conf, photo: photo}).then(function (r) {
      enCours = false; $('avia-confirme').checked = false;                    // une confirmation par envoi
      if (!r.ok) { etat('Refusé : ' + (r.texte || r.status), true); peut(); return; }
      majQuota(r.json.quota);
      if (r.json.erreur) etat('Échec : ' + r.json.erreur, true);
      else if (r.json.svg) { resultat = r.json.svg; etat('Dessin reçu (' + r.json.svg.length + ' caractères). Ouvrez-le dans l’éditeur comme point de départ.', false); $('avia-ouvre').hidden = false; }
      else etat('Le service a répondu par des opérations : non appliquées par cette page.', true);
      peut();
    }).catch(function () { enCours = false; etat('Serveur injoignable', true); peut(); });
  });
  function hex(v) {
    var m = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.exec(v || '');
    return !m ? '#888888' : m[1].length === 3 ? '#' + m[1].replace(/./g, '$&$&') : '#' + m[1];
  }
  // texte SVG -> formes (rect, polygon) mises a l'echelle du repere de la page ; {formes, ignores}
  AV.svgVersFormes = function (texte) {
    var doc = new DOMParser().parseFromString(texte, 'image/svg+xml'), r = doc.documentElement, vb, sx, sy, out = [], ign = 0, id = AV.idSuivant();
    if (!r || r.nodeName.toLowerCase() !== 'svg' || doc.getElementsByTagName('parsererror').length) return null;
    vb = (r.getAttribute('viewBox') || '').split(/[\s,]+/).map(Number);
    if (vb.length !== 4 || !(vb[2] > 0) || !(vb[3] > 0)) vb = [0, 0, +r.getAttribute('width') || AV.larg, +r.getAttribute('height') || AV.haut];
    sx = AV.larg / vb[2]; sy = AV.haut / vb[3];
    [].forEach.call(r.getElementsByTagName('*'), function (e) {
      var n = e.nodeName.toLowerCase(), f, p;
      if (n === 'svg' || n === 'g' || n === 'defs' || n === 'title') return;
      if (out.length >= 200) { ign++; return; }
      if (n === 'rect') {
        f = F.normalise({id: id, type: 'rect', x: ((+e.getAttribute('x') || 0) - vb[0]) * sx, y: ((+e.getAttribute('y') || 0) - vb[1]) * sy,
                         l: (+e.getAttribute('width') || 0) * sx, h: (+e.getAttribute('height') || 0) * sy, fill: hex(e.getAttribute('fill'))});
      } else if (n === 'polygon') {
        p = (e.getAttribute('points') || '').trim().split(/[\s,]+/).map(Number);
        for (var pts = [], i = 0; i + 1 < p.length; i += 2) pts.push([(p[i] - vb[0]) * sx, (p[i + 1] - vb[1]) * sy]);
        f = pts.length >= 3 && p.every(isFinite) ? F.normalise({id: id, type: 'polygon', points: pts, fill: hex(e.getAttribute('fill'))}) : null;
      } else f = null;
      if (f) { out.push(f); id++; } else ign++;
    });
    return {formes: out, ignores: ign};
  };
  $('avia-ouvre').addEventListener('click', function () {
    var r = resultat && AV.svgVersFormes(resultat);
    if (!r || !r.formes.length) { etat('Ce dessin ne contient aucune forme exploitable (rectangles et polygones seulement)', true); return; }
    if (AV.mode !== 'plat') $('av-fond-plat').click();
    r.formes.forEach(function (f) { AV.formes.push(f); });
    AV.selection = null; AV.commit();
    etat(r.formes.length + ' forme(s) ajoutée(s) au dessin' + (r.ignores ? ' (' + r.ignores + ' élément(s) ignoré(s))' : '') + ' : Ctrl+Z pour annuler.', false);
  });
})();
"""
