"""Page « Energie (/energie) » de l'atelier (plan energie-atelier A5, spec 2026-11-08 §4.3) : bloc du script, ajoute APRES
atelier_graphiques_page_js.JS (meme <script>, memes globales : $, etat, copie, echappe, lis, poste, message, source, televerse...).

Pour un env dont /envs dit `energie` (le differentiel), le bloc REMPLACE par enveloppement les fonctions de la page (choisitEnv,
dessine, dessineAlertes, actualise, apercu, verifieEtDiff, corpsEcriture, litSeries) : si etat.dest != 'energie' elles rendent la
version d'origine telle quelle. Rien d'autre n'est touche : l'ecriture (« Ecrire », « Televerser ») est celle de la page.

Description en cours = etat.desc (`{version, elements}`), validee par window.Energie.valide (le validateur de la carte, memes verdicts
que le serveur) puis POST /diff {destination: 'energie'}. Depart : GET /composition (carte comparee au depot) ; si elles different, le
choix « carte / depot » est exige AVANT toute modification (etat.base). Apercu : le VRAI rendu de la carte, Energie.trace sur
#a_grille (pas #e_grille : energie.js ne doit pas se lancer seul), donnees de GET /energie/<env>?f=donnees|direct|mois.
Un graphique « jour » dont le mois n'a pas d'archive (f=mois en 404) est signale avant l'ecriture. Texte de la carte ou du depot
(titres, motifs, diff) : textContent, ou echappe() pour le diff.
"""

JS_ENERGIE = r"""
// ---- page « Energie (/energie) » du differentiel ----
var GROUPE_VALEUR = ['valeur', 'cadran', 'demi-cercle'], GROUPE_FLASH = ['barres', 'courbe', 'aire', 'escalier'];
var BORNES_JAUGE = {Factor: [0, 1], Power: [0, 3000], ApparentPower: [0, 3000], ReactivePower: [0, 3000], Voltage: [0, 300], Current: [0, 20], Frequency: [40, 60]};
var enc = function () { return etat.dest === 'energie'; };
function creeEl(tag, attrs, texte) {
  var n = document.createElement(tag);
  Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
  if (texte !== undefined) n.textContent = texte;
  return n;
}
function libSource(s) {
  return s.direct ? 'direct · ' + s.direct : s.total ? 'total ' + s.total + ' · ' + s.grandeur : s.flash === 'minutes' ? 'historique · puissance 24 h (W)' : 'historique · ' + s.flash + ' · ' + s.grandeur;
}
function cleSource(s) { return s.direct ? 'd:' + s.direct : s.total ? 't:' + s.total + ':' + s.grandeur : 'f:' + s.flash + ':' + (s.grandeur || ''); }
function elementCourant() { return etat.desc && etat.desc.elements[etat.en.sel]; }

// -- enveloppes des fonctions de la page --
var choisitEnvPages = choisitEnv, dessinePagesFn = dessine, alertesPages = dessineAlertes, actualisePages = actualise, apercuPages = apercu;
var verifiePages = verifieEtDiff, corpsPages = corpsEcriture, litSeriesPages = litSeries;
choisitEnv = function (env) {
  var e = etat.envs.filter(function (x) { return x.nom === env; })[0];
  document.body.classList.toggle('energie', !!(e && e.energie));
  if (e && e.energie) return energieCharge(env);
  $('energie-ed').textContent = ''; etat.en = null;        // rien de la page Energie ne survit sur une carte « pages »
  return choisitEnvPages(env);
};
dessine = function () { return enc() ? energieDessine() : dessinePagesFn(); };
dessineAlertes = function () { return enc() ? energieAlertes() : alertesPages(); };
actualise = function () {
  if (!enc()) return actualisePages();
  clearTimeout(minuterie);
  minuterie = setTimeout(function () { apercu(); verifieEtDiff(); }, 300);
};
apercu = function () { return enc() ? energieApercu() : apercuPages(); };
verifieEtDiff = function () { return enc() ? energieVerifie() : verifiePages(); };
corpsEcriture = function () { return enc() ? {env: etat.env, destination: 'energie', description: etat.desc} : corpsPages(); };
litSeries = function () {
  if (!enc()) return litSeriesPages();
  var env = etat.env;
  return lis('/series?env=' + encodeURIComponent(env)).then(function (s) {
    if (env !== etat.env) return;
    etat.series = s; etat.en.don = null; source(s.origine === 'carte' ? 'carte' : 'simulee', 'carte injoignable ou sans bloc ENERGY');
  });
};

// -- chargement : sources, puis composition (carte comparee au depot) --
function energieCharge(env) {
  etat.env = env; etat.dest = 'energie'; etat.compo = null; etat.base = null; etat.indexEcrit = null; etat.desc = null; etat.diff = null; etat.motifs = [];
  etat.en = {sel: 0, don: null, dir: null, jeton: 0, archives: {}};
  clearTimeout(minuterie);       // le rafraichissement differe de l'env quitte lirait une description de pages
  televerseCache(); dernieres = {};
  history.replaceState(null, '', '?env=' + encodeURIComponent(env));
  $('nom-carte').textContent = env;
  $('lien-build').href = 'http://127.0.0.1:7700/?env=' + encodeURIComponent(env) + '&depuis=atelier&fichiers=&redemarrer=0';
  ['destination', 'compo-liste', 'motifs', 'alertes'].forEach(function (id) { $(id).textContent = ''; });
  message('');
  return litSeries().then(function () { return lis('/composition?env=' + encodeURIComponent(env)); }).then(function (c) {
    if (env !== etat.env) return;
    etat.compo = c; energieDepart(); dessine(); actualise();
  }).catch(function (e) { if (env === etat.env) message('Lecture impossible : ' + echappe(e.message), 'rouge'); });
}
// Depart de l'edition : le depot, ou la carte si l'utilisateur l'a choisie ; rien tant que le choix est attendu
function energieDepart() {
  var c = etat.compo;
  etat.desc = attendChoix() ? null : copie((etat.base === 'carte' ? c.carte : c.depot) || Energie.DEFAUT);
  etat.en.sel = 0;
}

// -- colonne de droite : choix de depart, liste des elements, formulaire de l'element choisi --
function energieDessine() {
  var z = $('energie-ed'), c = etat.compo, d = etat.desc;
  z.textContent = '';
  var page = $('r-page');
  page.textContent = '';
  page.appendChild(creeEl('option', {value: 'energie'}, 'Énergie (/energie)'));
  if (!c) return;
  if (c.etat === 'non_verifiee') z.appendChild(creeEl('div', {'class': 'avert'}, 'Description de la carte non vérifiée : ' + (c.motif || 'carte injoignable') + '. Le dépôt sert de départ.'));
  if (c.firmware_requis) z.appendChild(creeEl('div', {'class': 'avert rouge'}, 'Le firmware de cette carte est antérieur à la page pilotée par description : « Téléverser » est indisponible, compilez et envoyez le firmware par la page Build.'));
  if (c.etat === 'differente') energieChoix(z, c);
  if (!d) return;
  var oct = new TextEncoder().encode(JSON.stringify(d)).length;
  z.appendChild(creeEl('div', {'class': 'petit doux', id: 'en-bilan'}, d.elements.length + ' élément(s) sur 16 · ' + oct + ' octets sur 4096'));
  var ul = creeEl('ul', {'class': 'en-liste', id: 'en-liste'});
  z.appendChild(ul);
  var ajout = creeEl('button', {'class': 'btn mini', id: 'en-ajout'}, '+ Élément');
  ajout.disabled = d.elements.length >= 16;
  z.appendChild(ajout);
  energieListe();
  if (elementCourant()) z.appendChild(energieForme(elementCourant()));
}
function energieChoix(z, c) {
  var b = creeEl('div', {'class': 'avert'});
  b.appendChild(creeEl('b', {}, 'La description de /energie diffère entre la carte et le dépôt : changée sur la carte, ou écriture pas encore téléversée.'));
  b.appendChild(document.createTextNode(' (diff dépôt → carte)'));
  z.appendChild(b);
  var pre = creeEl('pre', {'class': 'code'});
  pre.innerHTML = c.diff.split('\n').map(ligneDiff).join('\n');         // ligneDiff echappe chaque ligne
  z.appendChild(pre);
  [['carte', 'Partir de la version de la carte', 'Les écritures du dépôt pas encore téléversées seront perdues.'],
   ['depot', 'Garder celle du dépôt (page par défaut s\'il n\'y en a pas)', 'Les changements faits sur la carte seront perdus à l\'envoi.']].forEach(function (o) {
    var l = creeEl('label', {'class': 'ch'}), r = creeEl('input', {type: 'radio', name: 'base-en', value: o[0]});
    r.checked = etat.base === o[0]; r.disabled = o[0] === 'carte' && !c.carte_valide;
    l.appendChild(r); l.appendChild(document.createTextNode(' ' + o[1]));
    z.appendChild(l); z.appendChild(creeEl('div', {'class': 'petit', style: 'color:var(--rouge)'}, o[2]));
  });
  if (!c.carte_valide) z.appendChild(creeEl('div', {'class': 'petit doux'}, 'Version de la carte indisponible : ' + (c.motif || 'illisible')));
  if (!etat.base) z.appendChild(creeEl('div', {'class': 'petit doux'}, 'Sans choix, rien n\'est modifié ni écrit.'));
}
function energieListe() {
  var ul = $('en-liste');
  if (!ul) return;
  ul.textContent = '';
  etat.desc.elements.forEach(function (e, i) {
    var li = creeEl('li', {'data-i': i, 'class': i === etat.en.sel ? 'sel' : ''});
    li.appendChild(creeEl('span', {'class': 'lib', 'data-act': 'choisit'}, (i + 1) + '. ' + (e.titre || '(sans titre)')));
    li.appendChild(creeEl('span', {'class': 'doux petit'}, ' ' + e.type + ' '));
    [['tete', '⤒', 'En tête'], ['haut', '▲', 'Monter'], ['bas', '▼', 'Descendre'], ['retire', '✕', 'Retirer']].forEach(function (a) {
      li.appendChild(creeEl('button', {'class': 'btn mini', 'data-act': a[0], title: a[2], 'aria-label': a[2]}, a[1]));
    });
    ul.appendChild(li);
  });
}
$('energie-ed').addEventListener('click', function (ev) {
  var a = ev.target.getAttribute && ev.target.getAttribute('data-act'), li = ev.target.closest && ev.target.closest('li'), l = etat.desc && etat.desc.elements;
  if (!l) return;
  if (ev.target.id === 'en-ajout') {
    l.push({type: 'valeur', titre: 'Puissance', source: {direct: 'Power'}, unite: 'W', couleur: '#4a9eda', largeur: 'demi', hauteur: 'petite'});
    etat.en.sel = l.length - 1; return modifie(true);
  }
  if (!a || !li || !l) return;
  var i = +li.getAttribute('data-i'), j = a === 'tete' ? 0 : a === 'haut' ? i - 1 : i + 1;
  if (a === 'choisit') etat.en.sel = i;
  else if (a === 'retire') { l.splice(i, 1); etat.en.sel = Math.max(0, Math.min(etat.en.sel, l.length - 1)); }
  else if (j >= 0 && j < l.length && j !== i) { l.splice(j, 0, l.splice(i, 1)[0]); etat.en.sel = j; }
  modifie(true);
});
$('energie-ed').addEventListener('change', function (ev) {
  if (ev.target.name !== 'base-en') return;
  etat.base = ev.target.value; energieDepart(); modifie(true);
});

// Un champ du formulaire : regle `ecrit(e, valeur)` sur l'element, puis relance (structure : le formulaire est redessine)
function champ(forme, id, libelle, noeud, ecrit, structure) {
  var l = creeEl('div', {'class': 'ligne'});
  l.appendChild(creeEl('span', {'class': 'etiq'}, libelle));
  noeud.id = id;
  noeud.addEventListener(noeud.tagName === 'SELECT' || noeud.type === 'checkbox' || noeud.type === 'color' ? 'change' : 'input', function () {
    var e = elementCourant();
    if (!e) return;
    ecrit(e, noeud.type === 'checkbox' ? noeud.checked : noeud.value);
    if (id === 'en-titre') energieListe();
    modifie(!!structure);
  });
  l.appendChild(noeud);
  forme.appendChild(l);
  return noeud;
}
function select(valeurs, courante, libelles) {
  var s = creeEl('select');
  valeurs.forEach(function (v, i) { var o = creeEl('option', {value: v}, libelles ? libelles[i] : v); s.appendChild(o); });
  s.value = courante;
  return s;
}
function saisie(type, valeur, attrs) { var n = creeEl('input', Object.assign({type: type}, attrs || {})); n.value = valeur === undefined ? '' : valeur; return n; }
function nombreOu(e, cle, v) { if (v === '' || isNaN(+v)) delete e[cle]; else e[cle] = +v; }
function ajusteElement(e) {
  var jauge = e.type === 'cadran' || e.type === 'demi-cercle', f = e.source.flash;
  if (jauge) {
    var b = BORNES_JAUGE[e.source.direct] || [0, 100];
    if (typeof e.min !== 'number') e.min = b[0];
    if (typeof e.max !== 'number') e.max = b[1];
  } else { delete e.min; delete e.max; }
  if (!f || f === 'minutes') delete e.total;
}
function energieForme(e) {
  var f = creeEl('div', {'class': 'en-forme', id: 'en-forme'}), src = (etat.series && etat.series.sources) || [], flash = !!e.source.flash;
  var cles = src.map(cleSource), courante = cleSource(e.source);
  if (cles.indexOf(courante) < 0) { src = src.concat([e.source]); cles.push(courante); }      // source hors du catalogue : gardee, a l'utilisateur de la changer
  champ(f, 'en-source', 'Source', select(cles, courante, src.map(libSource)), function (el, v) {
    var s = copie(src[cles.indexOf(v)]), avant = el.source;
    ['mois', 'decalage', 'nombre'].forEach(function (k) { if (avant.flash && avant.flash === s.flash && k in avant) s[k] = avant[k]; });
    var etaitFlash = !!avant.flash;
    el.source = s;
    if (s.flash && GROUPE_FLASH.indexOf(el.type) < 0) el.type = s.flash === 'minutes' ? 'courbe' : 'barres';
    if (!s.flash && GROUPE_VALEUR.indexOf(el.type) < 0) el.type = 'valeur';
    if (!etaitFlash && s.flash) { el.largeur = 'pleine'; el.hauteur = 'moyenne'; } else if (etaitFlash && !s.flash) { el.largeur = 'demi'; el.hauteur = 'petite'; }
    ajusteElement(el);
  }, true);
  var styles = flash ? GROUPE_FLASH : GROUPE_VALEUR;       // styles restreints a ceux que la source sait tracer
  champ(f, 'en-type', 'Style', select(styles, styles.indexOf(e.type) < 0 ? styles[0] : e.type), function (el, v) { el.type = v; ajusteElement(el); }, true);
  champ(f, 'en-titre', 'Titre', saisie('text', e.titre, {maxlength: 40}), function (el, v) { el.titre = v; });
  if (!flash) champ(f, 'en-unite', 'Unité', saisie('text', e.unite, {maxlength: 10}), function (el, v) { if (v) el.unite = v; else delete el.unite; });
  champ(f, 'en-couleur', 'Couleur', saisie('color', e.couleur || '#4a9eda'), function (el, v) { el.couleur = v; });
  champ(f, 'en-largeur', 'Largeur', select(['demi', 'pleine'], e.largeur || 'demi'), function (el, v) { el.largeur = v; });
  champ(f, 'en-hauteur', 'Hauteur', select(['petite', 'moyenne', 'grande'], e.hauteur || 'petite'), function (el, v) { el.hauteur = v; });
  if (e.type === 'cadran' || e.type === 'demi-cercle') {
    champ(f, 'en-min', 'Minimum', saisie('number', e.min), function (el, v) { nombreOu(el, 'min', v); });
    champ(f, 'en-max', 'Maximum', saisie('number', e.max), function (el, v) { nombreOu(el, 'max', v); });
  }
  if (e.source.flash === 'jour') {
    var mode = 'mois' in e.source ? 'fixe' : 'decalage' in e.source ? 'relatif' : 'courant';
    champ(f, 'en-mois-mode', 'Mois', select(['courant', 'relatif', 'fixe'], mode, ['en cours', 'relatif (il y a N mois)', 'fixe (AAAA-MM)']), function (el, v) {
      delete el.source.mois; delete el.source.decalage;
      if (v === 'relatif') el.source.decalage = 1;
      if (v === 'fixe') el.source.mois = mois0();
    }, true);
    if (mode === 'relatif') champ(f, 'en-decalage', 'Il y a', saisie('number', e.source.decalage, {min: 0, max: 23}), function (el, v) { nombreOu(el.source, 'decalage', v); });
    if (mode === 'fixe') champ(f, 'en-mois', 'Mois fixe', saisie('text', e.source.mois, {placeholder: 'AAAA-MM', maxlength: 7}), function (el, v) { el.source.mois = v; });
  }
  if (e.source.flash === 'mois') champ(f, 'en-nombre', 'Nombre', saisie('number', e.source.nombre, {min: 1, max: 24, placeholder: '12'}),
    function (el, v) { nombreOu(el.source, 'nombre', v); });
  if (e.source.flash && e.source.flash !== 'minutes') {
    var c = saisie('checkbox'); c.checked = !!e.total;
    champ(f, 'en-total', 'Total', c, function (el, v) { if (v) el.total = true; else delete el.total; });
  }
  return f;
}
function mois0() { var d = new Date(); d.setMonth(d.getMonth() - 1); return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2); }

// -- apercu : Energie.trace de la carte sur #a_grille --
function lisEnergie(env, url) {
  return fetch(url).then(function (r) {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    if (env === etat.env) source(r.headers.get('X-Source'));
    return r.json();
  });
}
function energieApercu() {
  var p = $('cadre'), env = etat.env, en = etat.en, jeton = ++en.jeton, base = '/energie/' + encodeURIComponent(env), d = etat.desc;
  p.className = 'cadre' + (etat.vue === 'telephone' ? ' telephone' : '') + (etat.sombre ? ' sombre' : '');
  $('tete-carte').textContent = 'Tasmota · ' + env; $('tete-titre').textContent = '';
  $('titre-apercu').textContent = 'Aperçu — page /energie (' + (etat.source === 'carte' ? 'vraies valeurs de la carte' : 'valeurs simulées') + ')';
  if (!d) { $('apercu').textContent = 'Choisir d\'abord la version de départ (carte ou dépôt).'; return; }
  if (Energie.valide(d).length) return;                      // description en cours de saisie : l'apercu garde le dernier rendu, les motifs sont affiches
  var lit = en.don ? Promise.resolve() : Promise.all([lisEnergie(env, base + '?f=donnees'), lisEnergie(env, base + '?f=direct')]).then(function (r) {
    en.don = r[0]; en.dir = r[1];
  });
  lit.then(function () { return Energie.archives(base, d, en.don); }).then(function () {
    if (en !== etat.en || jeton !== en.jeton || env !== etat.env) return;   // carte changee pendant la lecture : etat.en remis a null ou neuf
    var zone = $('apercu'), g = creeEl('div', {id: 'a_grille'}), w = creeEl('div', {id: 'e_zone'});
    zone.textContent = ''; w.appendChild(g); zone.appendChild(w);
    Energie.trace(g, copie(d), en.don, en.dir);
    en.archives = en.don.archives || {};
    g.setAttribute('data-pret', '1');
    energieAlertes();
  }).catch(function (e) { if (en === etat.en && jeton === en.jeton) $('apercu').textContent = 'Lecture impossible : ' + e.message; });
}
// Mois d'un graphique « jour » (meme calcul que energie.js::cible) ; null tant que la carte n'a rendu aucun releve
function moisDe(s) {
  var e = etat.en.don && etat.en.don.etat;
  if (s.mois || !e) return s.mois || null;
  var m = +e.m.slice(0, 4) * 12 + +e.m.slice(5, 7) - 1 - (s.decalage || 0);
  return Math.floor(m / 12) + '-' + ('0' + (m % 12 + 1)).slice(-2);
}
function energieAlertes() {
  var z = $('alertes'), c = etat.compo, e = etat.en.don && etat.en.don.etat;
  z.textContent = '';
  if (!etat.desc) return;
  etat.desc.elements.forEach(function (x, i) {
    var m = x.source.flash === 'jour' ? moisDe(x.source) : null;
    if (m && e && m !== e.m && etat.en.archives[m] === 404)           // 404 de f=mois : archive purgee ou jamais faite
      z.appendChild(creeEl('div', {'class': 'avert'}, 'Élément ' + (i + 1) + ' « ' + x.titre + ' » : aucune archive pour ' + m + ' sur la carte, le graphique sera vide (« archive effacée »).'));
  });
  if (c && c.firmware_requis) z.appendChild(creeEl('div', {'class': 'avert rouge'}, 'Firmware de la carte trop ancien pour cette page : écriture possible, envoi par la page Build.'));
}

// -- validation (celle de la carte) puis diff du serveur --
function energieVerifie() {
  if (attendChoix()) { etat.diff = null; dessineCode(); $('motifs').textContent = ''; $('resume').textContent = 'choisir la version de départ : rien n\'est écrit'; return; }
  if (!etat.desc) return;
  var sig = JSON.stringify(corpsEcriture()), corps = JSON.parse(sig), z = $('motifs');
  etat.motifs = Energie.valide(etat.desc);
  z.textContent = '';
  if (etat.motifs.length) {
    var b = creeEl('div', {'class': 'avert rouge'});
    b.appendChild(creeEl('b', {}, 'Description refusée :'));
    etat.motifs.forEach(function (t) { b.appendChild(creeEl('br')); b.appendChild(document.createTextNode(t)); });
    z.appendChild(b); etat.diff = null; dessineCode(); return;
  }
  poste('/diff', corps).then(function (d) {
    if (sig !== JSON.stringify(corpsEcriture())) return;     // modifiee pendant le calcul : un autre diff suit
    d.signaux = d.signaux || [];                             // /diff Energie : ni cenv ni autoexec, donc aucun signal
    etat.diff = d; etat.diffSig = sig; dessineCode();
  }).catch(function (e) {
    etat.diff = null; dessineCode();
    z.textContent = ''; z.appendChild(creeEl('div', {'class': 'avert rouge'}, 'Refusé : ' + e.message));
  });
}
"""
