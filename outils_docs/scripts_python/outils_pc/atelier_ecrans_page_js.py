"""JS de la page de l'atelier des ecrans : etat, requetes, en-tete, listes, proprietes, liaison, tableau, fichiers.

Le dessin de l'ecran et les gestes (glisser, poignees, palette, zoom) sont dans atelier_ecrans_page_canevas.py.
Regles : DOM construit par textContent (jamais d'innerHTML avec une chaine de la description) ; POST avec l'en-tete
X-Atelier-Ecrans ; un objet se designe par (page, id), les id se repetent d'une page a l'autre ; /apercu est demande a
la fin d'un geste, et une reponse plus ancienne que la derniere demande est ignoree (E.seq).
"""

JS = r"""
var $ = function (id) { return document.getElementById(id); };
var E = { cartes: [], lieux: [], catalogue: null, env: '', ecranEnv: null, ecran: null, desc: null, page: 1, sel: null,
          zoom: 1, histo: [], futur: [], seq: 0, fichiers: [], erreurs: [], onglet: 'pages.jsonl', capture: false,
          demande: '', msgCarte: '', msgEcran: '' };

function el(tag, attrs, texte) {
  var e = document.createElement(tag);
  if (attrs) Object.keys(attrs).forEach(function (k) { if (k === 'class') e.className = attrs[k]; else e.setAttribute(k, attrs[k]); });
  if (texte !== undefined && texte !== null) e.textContent = String(texte);
  return e;
}
function vide(e) { while (e.firstChild) e.removeChild(e.firstChild); return e; }
function requete(methode, url, corps, enBlob) {
  var o = { method: methode, headers: {} };
  if (corps !== undefined) { o.headers['X-Atelier-Ecrans'] = '1'; o.headers['Content-Type'] = 'application/json'; o.body = JSON.stringify(corps); }
  return fetch(url, o).then(function (r) {
    if (!r.ok) return r.text().then(function (t) { throw new Error(t || ('HTTP ' + r.status)); });
    return enBlob ? r.blob() : r.json();
  });
}
function bandeau(texte) { var b = $('bandeau'); b.textContent = texte || ''; b.hidden = !texte; }
function afficheBandeau() { bandeau([E.msgCarte, E.msgEcran].filter(Boolean).join('\n')); }
// Apercu sur un autre ecran que celui de la carte : lecture seule (borne() recadrerait la description sur cet ecran)
function lecture() { return !E.desc || (E.ecran || null) !== (E.ecranEnv || E.desc.ecran || null); }

/* ---------- catalogue : types d'attributs et polices ---------- */
function typeAttr(type, k) {
  var o = E.catalogue.objets[type]; if (!o) return null;
  var a = o.attributs, a2 = k.slice(0, -2), propre = Object.prototype.hasOwnProperty;
  if (propre.call(a, k)) return a[k].type;
  if (/\d\d$/.test(k) && propre.call(a, a2)) return a[a2].type;
  return null;
}
function polices() { return E.catalogue.polices; }
function police(nom) { return polices().filter(function (p) { return p.nom === nom; })[0] || null; }
function lisPolice(v) {
  if (typeof v === 'number') return { nom: 'robotocondensed', taille: v };
  var m = /^A:sd\/polices\/(.+\.ttf)-(\d+)$/.exec(v || '');
  if (m) { var p = polices().filter(function (x) { return x.fichier === m[1]; })[0]; return { nom: p ? p.nom : m[1], taille: +m[2] }; }
  m = /^(montserrat|seg7)-(\d+)$/.exec(v || '');
  return m ? { nom: m[1], taille: +m[2] } : null;
}
function ecritPolice(nom, taille) {
  var p = police(nom);
  if (p && p.source === 'sd') return 'A:sd/polices/' + p.fichier + '-' + taille;
  return nom === 'robotocondensed' ? taille : nom + '-' + taille;
}
function refusTaille(nom, taille) {           // meme regle que atelier_ecrans_description._police
  var p = police(nom);
  if (!p) return 'police « ' + nom + ' » absente du catalogue';
  if (!(taille > 0) || Math.floor(taille) !== taille) return 'taille invalide : entier positif attendu';
  if (p.taille_libre || p.tailles.indexOf(taille) >= 0) return '';
  return 'Taille ' + taille + ' absente de ' + nom + ' : tailles possibles ' + p.tailles.join(', ') + '.';
}
function textePolice(v) { var p = lisPolice(v); return p ? p.nom + ' ' + p.taille : (v === undefined ? '' : String(v)); }

/* ---------- description : objets, historique ---------- */
// objets editables seulement : les lignes brutes d'un pages.jsonl importe sont dans bruts() (atelier_ecrans_page_import)
function objets(page) { return E.desc.objets.filter(function (o) { return o.page === page && o.type !== 'brut'; }); }
function objet(page, id) { return objets(page).filter(function (o) { return o.id === id; })[0] || null; }
function choisi() { return E.sel ? objet(E.sel[0], E.sel[1]) : null; }
function pageDesc(n) { return E.desc.pages.filter(function (p) { return p.n === n; })[0] || null; }
function descriptionVide(ecran) {
  return { version: 1, ecran: ecran, orientation: 0, modele: [], couleurs: {},
           pages: [{ n: 0, titre: 'Commun' }, { n: 1, titre: 'Page 1' }], objets: [] };
}
function modifie(fn) {
  if (lecture()) return;
  var avant = JSON.stringify(E.desc);
  fn();
  E.histo.push(avant); if (E.histo.length > 100) E.histo.shift(); E.futur = [];
  if (E.sel && !choisi()) E.sel = null;
  dessineTout(); apercu();
}
function deplaceHisto(de, vers) {
  if (!de.length || lecture()) return;
  vers.push(JSON.stringify(E.desc)); E.desc = JSON.parse(de.pop());
  // shortcut: une remarque annulee n'est pas reprise par Retablir (a reappliquer) ; au-dela de 100 etats l'index glisse
  for (var k in R.appliquees) if (R.appliquees[k] > E.histo.length) delete R.appliquees[k];
  if (E.sel && !choisi()) E.sel = null;
  if (!pageDesc(E.page)) E.page = E.desc.pages.length ? E.desc.pages[0].n : 0;
  dessineTout(); apercu();
}
function selectionne(page, id) { E.sel = id === null ? null : [page, id]; if (id !== null) E.page = page; dessineTout(); }

/* ---------- en-tete ---------- */
function libelleEcran(cle) {
  var e = E.catalogue.ecrans[cle];
  return e.pilote + ' · ' + e.largeur + ' × ' + e.hauteur + (e.tactile ? ' tactile' : '') + (cle === E.ecranEnv ? " (celui de l'env)" : '');
}
function remplitEcrans() {
  var s = vide($('ecran'));
  if (!E.ecranEnv) s.appendChild(el('option', { value: '' }, "aucun écran déclaré par l'env"));
  var groupes = { carte: 'Écrans des cartes', perso: 'Bibliothèque personnelle', amont: 'Fournis par Tasmota' };
  Object.keys(groupes).forEach(function (src) {
    var g = el('optgroup', { label: groupes[src] });
    Object.keys(E.catalogue.ecrans).forEach(function (cle) {
      var e = E.catalogue.ecrans[cle];   /* LVGL : ecrans couleur seulement, sauf celui de l'env */
      if ((e.source || 'carte') === src && (e.couleur !== false || cle === E.ecranEnv)) g.appendChild(el('option', { value: cle }, libelleEcran(cle)));
    });
    if (g.children.length) s.appendChild(g);
  });
  s.value = E.ecran || '';
}
function etat(classe, texte) { var p = $('etat'); p.className = 'pastille ' + classe; p.textContent = texte; }
function lisCarte() {
  var env = E.env;
  etat('', 'lecture de la carte…');
  requete('GET', '/valeurs?env=' + encodeURIComponent(env)).then(function (r) {
    if (env !== E.env) return;
    var c = E.cartes.filter(function (x) { return x.nom === env; })[0] || {};
    if (r.simule) etat('or', '○ ' + (r.motif || 'carte injoignable'));
    else etat('ok', '● en ligne' + (c.ip ? ' ' + c.ip : ''));
    $('sensorBoite').hidden = !r.sensor;
    $('sensor').textContent = r.sensor ? JSON.stringify(r.sensor, null, 1) : '';
  }).catch(function (e) { if (env === E.env) etat('or', '○ ' + e.message); });
}
function chargeCarte(env) {          // la carte d'avant reste en place tant que la nouvelle n'est pas lue
  E.demande = env;
  return requete('GET', '/description?env=' + encodeURIComponent(env)).then(function (r) {
    if (env !== E.demande) return;
    E.env = env;
    try { history.replaceState(null, '', '?env=' + encodeURIComponent(env)); } catch (e) {}
    var c = E.cartes.filter(function (x) { return x.nom === env; })[0] || {};
    $('interface').textContent = c.interface ? 'interface envoyée : ' + c.interface : 'interface : non déclarée';
    $('captureBoite').hidden = true;
    E.ecranEnv = r.ecran;
    W.changement = null; W.descAvant = null; fermeConfirmation(); messageEcriture('');
    E.empreinteDesc = r.empreinte; E.build = r.build;
    E.desc = r.description || descriptionVide(r.ecran);
    E.ecran = r.ecran || E.desc.ecran || null;
    E.histo = []; E.futur = []; E.sel = null;
    E.page = pageDesc(1) ? 1 : (E.desc.pages.length ? E.desc.pages[0].n : 0);
    if (r.description) E.msgCarte = r.erreurs.length ? 'Description de la carte refusée par le validateur :\n' + r.erreurs.join('\n') : '';
    else E.msgCarte = r.erreurs.length ? r.erreurs.join('\n') + "\nPage vierge proposée à la place : rien n'est écrit."
                                       : "Pas encore de description d'écran pour cette carte : page vierge, rien n'est écrit.";
    E.msgEcran = ''; afficheBandeau();
    R.liste = []; R.zone = null; R.outilZone = false; R.brouillon = ''; R.message = ''; R.appliquees = {};
    messageImport(''); dessineImport(); chargeImages();
    remplitEcrans(); zoomAjuste(); dessineTout(); apercu(); lisCarte(); chargeRemarques();
  }).catch(function (e) {
    if (env !== E.demande) return;
    E.demande = E.env; $('carte').value = E.env;
    bandeau('Lecture de la description de ' + env + ' impossible : ' + e.message + (E.env ? '\nLa carte ' + E.env + ' reste affichée.' : ''));
  });
}
function choisitEcran(cle) {
  if (W.descAvant) oublieChangement(false);
  fermeConfirmation();
  E.ecran = cle || null;
  E.msgEcran = lecture() ? "Aperçu sur un autre écran que celui de la carte, en lecture seule. « Proposer le changement » "
               + "met la disposition à l'échelle et montre les fichiers ; revenir à l'écran de la carte pour l'éditer." : '';
  afficheBandeau(); zoomAjuste(); dessineTout();
}

/* ---------- colonne gauche ---------- */
function libelleObjet(o) {
  var t = o.attributs && o.attributs.text;
  return o.id + ' ' + o.type + (t ? ' « ' + t + ' »' : '') + (o.liaison ? ' · ' + o.liaison.cle : '');
}
function dessineListes() {
  var pg = vide($('pages'));
  E.desc.pages.forEach(function (p) {
    var d = el('div', { class: p.n === E.page ? 'sel' : '', tabindex: '0' }, p.n + ' · ' + (p.titre || 'sans titre') + (p.n === 0 ? ' (toutes les pages)' : ''));
    d.onclick = function () { E.page = p.n; E.sel = null; dessineTout(); };
    d.onkeydown = entreeClique;
    pg.appendChild(d);
  });
  $('titreObjets').textContent = 'Objets de la page ' + E.page;
  var ob = vide($('objets'));
  objets(E.page).forEach(function (o) {
    var d = el('div', { class: E.sel && E.sel[0] === o.page && E.sel[1] === o.id ? 'sel' : '', tabindex: '0' }, libelleObjet(o));
    d.onclick = function () { selectionne(o.page, o.id); };
    d.onkeydown = entreeClique;
    ob.appendChild(d);
  });
  listeBruts(ob);
  if (!E.desc.objets.some(function (o) { return o.page === E.page; })) ob.appendChild(el('div', { class: 'doux' }, 'aucun objet'));
}
function entreeClique(ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); ev.currentTarget.click(); } }
function ajoutePage() {
  modifie(function () {
    var n = E.desc.pages.reduce(function (m, p) { return Math.max(m, p.n); }, 0) + 1;
    var modele = pageDesc(1), p = { n: n, titre: 'Page ' + n };
    if (modele && modele.attributs) p.attributs = JSON.parse(JSON.stringify(modele.attributs));
    E.desc.pages.push(p); E.page = n; E.sel = null;
  });
}

/* ---------- champs du panneau de droite ---------- */
function champ(parent, libelle, entree) { var l = el('div', { class: 'ligne' }); l.appendChild(el('span', { class: 'etiq' }, libelle)); l.appendChild(entree); parent.appendChild(l); return l; }
function saisie(valeur, type, surChange) {
  var i = el('input', { type: type || 'text' }); i.value = valeur === undefined ? '' : valeur;
  i.onchange = function () { surChange(i.value, i); };
  return i;
}
function entier(v) { var n = Number(v); return v !== '' && Math.floor(n) === n ? n : null; }
function refus(parent, texte) { var a = el('div', { class: 'avert' }, texte); parent.appendChild(a); return a; }
function champCouleur(parent, libelle, valeur, surChange) {
  var l = el('div', { class: 'ligne' }), c = el('input', { type: 'color', 'aria-label': libelle }), t = el('input', { type: 'text' });
  l.appendChild(el('span', { class: 'etiq' }, libelle));
  c.value = /^#[0-9A-Fa-f]{6}$/.test(valeur || '') ? valeur : '#000000'; t.value = valeur || '';
  c.onchange = function () { surChange(c.value.toUpperCase()); };
  t.onchange = function () { if (/^#[0-9A-Fa-f]{6}$/.test(t.value)) surChange(t.value.toUpperCase()); else { t.value = valeur || ''; alert('Couleur attendue : #RRGGBB'); } };
  l.appendChild(c); l.appendChild(t); parent.appendChild(l);
}
function champAttribut(parent, o, k) {
  var t = typeAttr(o.type, k), v = o.attributs[k];
  var poser = function (nv) { modifie(function () { choisi().attributs[k] = nv; }); };
  if (t === 'couleur') champCouleur(parent, k, v, poser);
  else if (t === 'lignes') champOptions(parent, k, v, poser);
  else if (o.type === 'img' && k === 'src') champImage(parent, v, poser);
  else if (t === 'booleen') { var b = el('input', { type: 'checkbox' }); b.checked = !!v; b.onchange = function () { poser(b.checked); }; champ(parent, k, b); }
  else champ(parent, k, saisie(v, t === 'entier' ? 'number' : 'text', function (nv, i) {
    if (t === 'entier') { var n = entier(nv); if (n === null) { i.value = v; return; } poser(n); } else poser(nv);
  }));
  var x = el('button', { class: 'btn', type: 'button', 'aria-label': 'Retirer ' + k }, '×');
  x.onclick = function () { modifie(function () { delete choisi().attributs[k]; }); };
  parent.lastChild.appendChild(x);
}
function champPolice(parent, o) {
  var p = lisPolice(o.attributs.text_font), l = el('div', { class: 'ligne' });
  var s = el('select', { 'aria-label': 'Police' }), n = el('input', { type: 'number', min: '1', 'aria-label': 'Taille' });
  polices().forEach(function (x) { s.appendChild(el('option', { value: x.nom }, x.nom + (x.source === 'sd' ? ' (/sd)' : ''))); });
  s.value = p ? p.nom : 'robotocondensed'; n.value = p ? p.taille : '';
  l.appendChild(el('span', { class: 'etiq' }, 'Police')); l.appendChild(s); l.appendChild(n); parent.appendChild(l);
  var msg = refus(parent, ''); msg.hidden = true;
  var applique = function () {
    var t = entier(n.value), r = refusTaille(s.value, t);
    if (r) { msg.textContent = r; msg.hidden = false; return; }
    modifie(function () { choisi().attributs.text_font = ecritPolice(s.value, t); });
  };
  s.onchange = applique; n.onchange = applique;
}
function dessineProprietes() {
  var pn = vide($('proprietes')), o = choisi();
  if (!o) {
    var p = pageDesc(E.page);
    pn.appendChild(el('p', { class: 'doux petit' }, "Cliquez un objet de l'écran, de la liste ou du tableau. Page " + E.page + ' :'));
    if (!p) return;
    champ(pn, 'Titre', saisie(p.titre || '', 'text', function (v) { modifie(function () { pageDesc(E.page).titre = v; }); }));
    if (E.page !== 0) champCouleur(pn, 'Fond', (p.attributs || {}).bg_color, function (v) {
      modifie(function () { var q = pageDesc(E.page); q.attributs = q.attributs || {}; q.attributs.bg_color = v; });
    });
    return;
  }
  var t = el('div', { class: 'ligne' }); t.appendChild(el('span', { class: 'etiq' }, 'Objet')); t.appendChild(el('b', null, o.type + ' · page ' + o.page + ' · id ' + o.id)); pn.appendChild(t);
  [['Position', 'x', 'y'], ['Taille', 'l', 'h']].forEach(function (g) {
    var l = el('div', { class: 'ligne' }); l.appendChild(el('span', { class: 'etiq' }, g[0]));
    [g[1], g[2]].forEach(function (k) {
      l.appendChild(saisie(o[k], 'number', function (v, i) {
        var n = entier(v); if (n === null || n < 0) { i.value = o[k]; return; }
        modifie(function () { choisi()[k] = n; borne(choisi()); });
      }));
    });
    pn.appendChild(l);
  });
  if (typeAttr(o.type, 'text') && o.type !== 'roller') champ(pn, 'Texte', saisie(o.attributs.text || '', 'text', function (v) { modifie(function () { choisi().attributs.text = v; }); }));
  if (typeAttr(o.type, 'text_font')) champPolice(pn, o);
  pn.appendChild(el('h3', null, 'Autres attributs'));
  Object.keys(o.attributs).forEach(function (k) { if (k !== 'text' && k !== 'text_font') champAttribut(pn, o, k); });
  var l = el('div', { class: 'ligne' }), s = el('select', { 'aria-label': 'Attribut à ajouter' }), b = el('button', { class: 'btn', type: 'button' }, 'Ajouter');
  Object.keys(E.catalogue.objets[o.type].attributs).sort().forEach(function (k) { if (!(k in o.attributs) && k !== 'qr_size' && !(o.type === 'roller' && k === 'text')) s.appendChild(el('option', { value: k }, k)); });
  b.onclick = function () {
    var k = s.value, ty = typeAttr(o.type, k);
    modifie(function () { choisi().attributs[k] = ty === 'couleur' ? '#FFFFFF' : ty === 'entier' ? 0 : ty === 'booleen' ? false : ty === 'lignes' ? 'Option 1' : ''; });
  };
  l.appendChild(s); l.appendChild(b); pn.appendChild(l);
  var sup = el('button', { class: 'btn danger', type: 'button' }, "Supprimer l'objet");
  sup.onclick = supprimeChoisi;
  pn.appendChild(el('div', { class: 'ligne' })).appendChild(sup);
}
function supprimeChoisi() {
  var o = choisi(); if (!o) return;
  modifie(function () { E.desc.objets = E.desc.objets.filter(function (x) { return x !== choisi(); }); E.sel = null; });
}

/* ---------- liaison et toucher ---------- */
function dessineLiaison() {
  var pn = vide($('liaison')), o = choisi();
  if (!o) { pn.appendChild(el('p', { class: 'doux petit' }, 'Choisir un objet pour lier une valeur ou une action au toucher.')); return; }
  var li = o.liaison || {};
  pn.appendChild(el('h3', null, 'Valeur liée (modèle de l’écran)'));
  var s = el('select', { 'aria-label': 'Valeur' }); s.appendChild(el('option', { value: '' }, 'aucune'));
  (E.desc.modele || []).forEach(function (m) { s.appendChild(el('option', { value: m.cle }, m.cle + ' (ex. ' + m.exemple + ')')); });
  if (li.cle && !(E.desc.modele || []).some(function (m) { return m.cle === li.cle; })) s.appendChild(el('option', { value: li.cle }, li.cle));
  s.value = li.cle || '';
  s.onchange = function () { modifie(function () { var c = choisi(); if (!s.value) delete c.liaison; else { c.liaison = c.liaison || { attribut: 'text' }; c.liaison.cle = s.value; } }); };
  champ(pn, 'Valeur', s);
  if (li.cle) {
    if (li.cle.indexOf('[]') >= 0) champ(pn, 'Indice', saisie(li.indice === undefined ? '' : li.indice, 'number', function (v, i) {
      var n = entier(v); if (n === null || n < 0) { i.value = li.indice; return; } modifie(function () { choisi().liaison.indice = n; });
    }));
    var a = el('select', { 'aria-label': 'Attribut lié' });
    Object.keys(E.catalogue.objets[o.type].attributs).sort().concat(['series']).forEach(function (k) { a.appendChild(el('option', { value: k }, k)); });
    a.value = li.attribut || 'text';
    a.onchange = function () { modifie(function () { choisi().liaison.attribut = a.value; }); };
    champ(pn, 'Attribut', a);
    var autres = Object.keys(li).filter(function (k) { return ['cle', 'indice', 'attribut'].indexOf(k) < 0; });
    if (autres.length) pn.appendChild(el('p', { class: 'doux petit' }, 'Réglages gardés tels quels : ' + autres.map(function (k) { return k + ' = ' + JSON.stringify(li[k]); }).join(' ; ')));
  }
  if (o.couleur_selon) pn.appendChild(el('p', { class: 'doux petit' }, 'Couleur selon une valeur : ' + o.couleur_selon.length + ' règle(s), gardées telles quelles.'));
  pn.appendChild(el('h3', null, 'Action au toucher'));
  var to = o.toucher || {}, genre = 'page' in to ? 'page' : 'commande' in to ? 'commande' : 'fonction' in to ? 'fonction' : '';
  var g = el('select', { 'aria-label': 'Action' });
  [['', 'aucune'], ['page', 'aller à une page'], ['commande', 'commande Tasmota'], ['fonction', 'fonction Berry']].forEach(function (x) { g.appendChild(el('option', { value: x[0] }, x[1])); });
  g.value = genre;
  g.onchange = function () { modifie(function () { var c = choisi(); if (!g.value) delete c.toucher; else { c.toucher = {}; c.toucher[g.value] = g.value === 'page' ? 1 : ''; } }); };
  champ(pn, 'Type', g);
  if (genre) champ(pn, genre === 'page' ? 'Page' : genre === 'commande' ? 'Commande' : 'Fonction', saisie(to[genre], genre === 'page' ? 'number' : 'text', function (v, i) {
    var nv = genre === 'page' ? entier(v) : v; if (nv === null) { i.value = to[genre]; return; }
    modifie(function () { choisi().toucher[genre] = nv; });
  }));
  if (genre && genre !== 'page' && ['switch', 'dropdown', 'roller'].indexOf(o.type) >= 0)
    pn.appendChild(el('p', { class: 'doux petit' }, 'Action au changement de valeur, qui la reçoit (interrupteur 1 ou 0, sinon '
      + 'index de l’option) : dernier argument d’une fonction, %val% dans une commande. Interface LVGL pur seulement ; '
      + 'avec HASPmota, une règle hasp#p<page>b<id>#event de la carte.'));
  if (genre === 'fonction') champ(pn, 'Arguments', saisie(JSON.stringify(to.args || []), 'text', function (v, i) {
    var a; try { a = JSON.parse(v); } catch (e) { a = null; }
    if (!Array.isArray(a)) { i.value = JSON.stringify(to.args || []); alert('Liste JSON attendue, par exemple ["fenetre", 1]'); return; }
    modifie(function () { choisi().toucher.args = a; });
  }));
}

/* ---------- tableau des objets ---------- */
function dessineTableau() {
  var t = vide($('tableau')), tete = el('tr');
  ['id', 'type', 'x', 'y', 'l', 'h', 'texte', 'police', 'couleur', 'liaison'].forEach(function (c) { tete.appendChild(el('th', null, c)); });
  t.appendChild(tete);
  objets(E.page).forEach(function (o) {
    var tr = el('tr', { class: E.sel && E.sel[0] === o.page && E.sel[1] === o.id ? 'sel' : '' });
    tr.appendChild(el('td', null, o.id)); tr.appendChild(el('td', null, o.type));
    var cellule = function (valeur, classe, surChange) {
      var td = el('td', { class: classe || '' }), i = el('input'); i.value = valeur === undefined ? '' : valeur;
      i.onfocus = function () { if (!(E.sel && E.sel[0] === o.page && E.sel[1] === o.id)) { E.sel = [o.page, o.id]; dessineListes(); dessineProprietes(); dessineLiaison(); dessineEcran(); } };
      i.onchange = function () { var r = surChange(i.value); if (r) { i.value = valeur === undefined ? '' : valeur; $('refusTableau').textContent = r; $('refusTableau').hidden = false; } else $('refusTableau').hidden = true; };
      td.appendChild(i); tr.appendChild(td);
    };
    ['x', 'y', 'l', 'h'].forEach(function (k) { cellule(o[k], 'num', function (v) { var n = entier(v); if (n === null || n < 0) return k + ' : entier positif attendu'; modifie(function () { var c = objet(o.page, o.id); c[k] = n; borne(c); }); }); });
    cellule(o.attributs.text, '', function (v) { if (!typeAttr(o.type, 'text')) return 'pas de texte pour ' + o.type; modifie(function () { objet(o.page, o.id).attributs.text = v; }); });
    cellule(textePolice(o.attributs.text_font), '', function (v) {
      var m = /^\s*(\S+)\s+(\d+)\s*$/.exec(v); if (!m) return 'Police attendue : « nom taille », par exemple « robotocondensed 24 ».';
      var r = refusTaille(m[1], +m[2]); if (r) return r;
      modifie(function () { objet(o.page, o.id).attributs.text_font = ecritPolice(m[1], +m[2]); });
    });
    var kc = o.type === 'label' ? 'text_color' : 'bg_color';
    cellule(o.attributs[kc], '', function (v) { if (!/^#[0-9A-Fa-f]{6}$/.test(v)) return kc + ' : couleur #RRGGBB attendue'; modifie(function () { objet(o.page, o.id).attributs[kc] = v.toUpperCase(); }); });
    tr.appendChild(el('td', null, o.liaison ? o.liaison.cle + (o.liaison.indice !== undefined ? '[' + o.liaison.indice + ']' : '') : ''));
    t.appendChild(tr);
  });
}

/* ---------- fichiers generes ---------- */
var minuterie = null;
function apercu() { clearTimeout(minuterie); minuterie = setTimeout(envoieApercu, 250); }
function envoieApercu() {
  var n = ++E.seq;
  requete('POST', '/apercu', { env: E.env, description: E.desc }).then(function (r) {
    if (n !== E.seq) return; E.erreurs = r.erreurs; E.fichiers = r.fichiers; dessineFichiers();
  }).catch(function (e) { if (n !== E.seq) return; E.erreurs = [e.message]; E.fichiers = []; dessineFichiers(); });
}
function dessineFichiers() {
  var on = vide($('ongletsFichiers')), pre = vide($('fichier'));
  $('erreurs').hidden = !E.erreurs.length; $('erreurs').textContent = E.erreurs.length ? 'Description refusée :\n' + E.erreurs.join('\n') : '';
  if (!E.fichiers.some(function (f) { return f.nom === E.onglet; })) E.onglet = E.fichiers.length ? E.fichiers[0].nom : E.onglet;
  var aj = 0, re = 0;
  E.fichiers.forEach(function (f) {
    aj += f.ajouts; re += f.retraits;
    var b = el('button', { type: 'button', class: f.nom === E.onglet ? 'actif' : '' }, f.nom + (f.diff ? ' (+' + f.ajouts + ' −' + f.retraits + ')' : ' (=)'));
    b.onclick = function () { E.onglet = f.nom; dessineFichiers(); };
    on.appendChild(b);
  });
  $('resumeFichiers').textContent = E.fichiers.length ? (aj || re ? aj + ' ligne(s) ajoutée(s), ' + re + ' retirée(s) par rapport au dépôt' : 'identique au dépôt') : '';
  var f = E.fichiers.filter(function (x) { return x.nom === E.onglet; })[0];
  if (!f) { pre.textContent = E.erreurs.length ? '' : 'génération en cours…'; return; }
  if (!f.diff) { pre.appendChild(el('span', { class: 'c' }, '(identique au fichier du dépôt : ' + f.chemin + ')\n')); pre.appendChild(document.createTextNode(f.contenu)); return; }
  f.diff.split('\n').forEach(function (l) {
    var c = l.slice(0, 2) === '@@' || l.slice(0, 3) === '---' || l.slice(0, 3) === '+++' ? 'c' : l[0] === '+' ? 'p' : l[0] === '-' ? 'm' : '';
    pre.appendChild(c ? el('span', { class: c }, l + '\n') : document.createTextNode(l + '\n'));
  });
}

/* ---------- capture de la carte ---------- */
function capture() {
  if (E.capture) return;
  E.capture = true; $('capture').disabled = true; $('captureEtat').textContent = 'capture en cours (jusqu’à 2 min)…';
  var env = E.env;
  requete('POST', '/capture', { env: env }, true).then(function (b) {
    if (env !== E.env) return;
    var img = $('captureImg'); if (img.src) URL.revokeObjectURL(img.src);
    img.src = URL.createObjectURL(b); $('captureBoite').hidden = false;
    $('captureLegende').textContent = 'Capture de ' + env + ' le ' + new Date().toLocaleString('fr-FR');
    $('captureEtat').textContent = '';
  }).catch(function (e) { $('captureEtat').textContent = 'Capture refusée : ' + e.message; })
    .then(function () { E.capture = false; $('capture').disabled = false; });
}

function dessineTout() {
  dessineListes(); dessineEcran(); dessineProprietes(); dessineLiaison(); dessineTableau(); dessineRemarques(); dessineEcriture();
  var ro = lecture();
  $('annuler').disabled = ro || !E.histo.length; $('retablir').disabled = ro || !E.futur.length; $('ajoutPage').disabled = ro;
  ['proprietes', 'liaison', 'tableau'].forEach(function (id) {
    Array.prototype.forEach.call($(id).querySelectorAll('input,select,button'), function (x) { x.disabled = ro; });
  });
  $('palette').style.opacity = ro ? '.45' : '';
}
"""
