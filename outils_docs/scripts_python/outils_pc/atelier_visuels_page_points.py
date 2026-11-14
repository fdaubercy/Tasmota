"""Points chauds de l'atelier des visuels : modele des elements (valide a la creation et au rechargement), enregistrement par carte
(localStorage, revalide), appels au serveur (AV.api) et dessin des calques par-dessus le canevas d'edition.

Les calques sont des noeuds `data-el` (jamais `data-id` : l'editeur de formes y chercherait une forme). L'edition a la souris, le panneau
de l'element et l'apercu simule sont dans `atelier_visuels_page_elements.py`.
"""

JS_POINTS = r"""
(function () {
  var AV = window.AV, F = AV_FORMES, Cq = AV_CALQUES, NS = 'http://www.w3.org/2000/svg', TYPES = ['voyant', 'valeur', 'liaison'], gEl = null;
  AV.selEl = null;
  // appel JSON au serveur de l'outil : {ok, status, json, texte} ; l'en-tete anti-CSRF part avec chaque POST
  AV.api = function (methode, chemin, corps) {
    var o = {method: methode};
    if (methode === 'POST') {
      o.headers = {'X-Atelier-Visuels': '1', 'Content-Type': 'application/json'};
      o.body = typeof corps === 'string' || corps instanceof Blob ? corps : JSON.stringify(corps || {});
    }
    return fetch(chemin, o).then(function (r) {
      return r.text().then(function (t) { var j = null; try { j = JSON.parse(t); } catch (e) { /* texte brut (erreur) */ } return {ok: r.ok, status: r.status, json: j, texte: t}; });
    });
  };
  function copie(o) { try { return JSON.parse(JSON.stringify(o)); } catch (e) { return {}; } }
  AV.normaliseEl = function (e) {
    if (!e || typeof e !== 'object' || TYPES.indexOf(e.type) < 0 || typeof e.id !== 'string' || !/^[A-Za-z0-9_]{1,16}$/.test(e.id)) return null;
    var o = {id: e.id, type: e.type, x: Cq.num(e.x, 0, 0, 4000), y: Cq.num(e.y, 0, 0, 4000),
             source: e.source && typeof e.source === 'object' && !Array.isArray(e.source) ? copie(e.source) : {}, style: {}},
        s = e.style && typeof e.style === 'object' ? e.style : {}, t = o.style;
    if (e.type === 'liaison') { o.x2 = Cq.num(e.x2, o.x + 40, 0, 4000); o.y2 = Cq.num(e.y2, o.y, 0, 4000); }
    ['couleur_on', 'couleur_off', 'couleur_inconnu', 'couleur'].forEach(function (k) { if (Cq.coul(s[k], null)) t[k] = s[k]; });
    if (s.forme === 'rond' || s.forme === 'carre') t.forme = s.forme;
    if (typeof s.taille === 'number') t.taille = Cq.num(s.taille, 14, 6, 80);
    if (typeof s.unite === 'string') t.unite = s.unite.slice(0, 6);
    if (typeof s.decimales === 'number') t.decimales = Cq.num(Math.round(s.decimales), 1, 0, 6);
    if (s.exemple !== undefined) t.exemple = String(s.exemple).slice(0, 12);
    ['icone_on', 'icone_off', 'icone_inconnu'].forEach(function (k) {
      var ic = Cq.icone(s[k]);
      if (ic) { ic.jeu = String(s[k].jeu || '').slice(0, 40); ic.nom = String(s[k].nom || '').slice(0, 64); t[k] = ic; }
    });
    return o;
  };
  function cle() { return 'av.elements.' + (AV.carte || 'defaut'); }
  AV.sauveEls = function () { try { localStorage.setItem(cle(), JSON.stringify(AV.elements)); } catch (e) { /* stockage indisponible */ } };
  function chargeEls() {
    var t;
    try { t = JSON.parse(localStorage.getItem(cle()) || '[]'); } catch (e) { t = []; }
    AV.elements = (Array.isArray(t) ? t : []).slice(0, 200).map(AV.normaliseEl).filter(Boolean);
    AV.sim = {}; AV.selEl = null;
  }
  AV.idEl = function (prefixe) {
    var n = 1; while (AV.elements.some(function (e) { return e.id === prefixe + n; })) n++;
    return prefixe + n;
  };
  AV.elCherche = function (id) { return AV.elements.filter(function (e) { return e.id === id; })[0] || null; };
  AV.ajoutEl = function (el) {
    var e = AV.normaliseEl(el);
    if (!e || AV.elements.length >= 200) return null;
    AV.elements.push(e); AV.selEl = e.id; AV.sauveEls(); AV.dessine();
    return e;
  };
  AV.suppEl = function (id) {
    AV.elements = AV.elements.filter(function (e) { return e.id !== id; }); delete AV.sim[id];
    if (AV.selEl === id) AV.selEl = null;
    AV.sauveEls(); AV.dessine();
  };
  function overlay() {
    var svg = document.getElementById('avf-canevas'), el, c;
    if (!svg) return;
    if (gEl && gEl.parentNode) gEl.parentNode.removeChild(gEl);
    gEl = document.createElementNS(NS, 'g'); gEl.setAttribute('id', 'avc-g');
    Cq.rendu(AV.elements, AV.sim).forEach(function (n) { gEl.appendChild(F.bati(n, document)); });
    el = AV.elCherche(AV.selEl);
    if (el) {
      c = el.type === 'liaison' ? [Math.min(el.x, el.x2) - 6, Math.min(el.y, el.y2) - 6, Math.abs(el.x2 - el.x) + 12, Math.abs(el.y2 - el.y) + 12]
        : [el.x - 14, el.y - 14, 28, 28];
      gEl.appendChild(F.bati(['rect', {x: c[0], y: c[1], width: c[2], height: c[3], 'class': 'avf-cadre', 'stroke-dasharray': '3 3'}], document));
    }
    svg.appendChild(gEl);
  }
  var d0 = AV.dessine, c0 = AV.charge;
  AV.dessine = function () { d0(); overlay(); };
  AV.charge = function () { c0(); chargeEls(); AV.dessine(); };
  chargeEls(); AV.dessine();
})();
"""
