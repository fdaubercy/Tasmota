r"""Script de la page « Etiquettes QR code » (plan A4). Aucune donnee du serveur n'entre par innerHTML : textContent seul.

Texte du QR code : TOUJOURS converti en octets UTF-8 (`octets`) et encode en mode Byte ; qr-code-styling garde sinon
`255 & charCode` (outils_docs/etiquettes_qr/lib/LISEZMOI.md). `optionsQR` est la seule source des options : la page
/qrcode de la carte (A6) en reprendra le texte pour dessiner EXACTEMENT le meme QR code.
"""

JS = r"""
const ETAT = {env: null, cartes: [], lieux: [], reglage: null, page: false, esp32: false, charge: '', arbre: [],
              apercu: null, minuterie: null, demande: 0, envDemande: null, images: [], planche: new Set()};
const $ = id => document.getElementById(id);
const LIBELLES = {hostname: 'Hostname', ip: 'IP', topic: 'Topic', env: 'Env', puce: 'Puce', lieu: 'Lieu',
                  range_extender: 'Range extender'};
const POINTS = [['rounded', 'arrondis'], ['square', 'carrés'], ['dots', 'ronds'], ['classy', 'classique'],
                ['classy-rounded', 'classique arrondi'], ['extra-rounded', 'très arrondis']];
const COINS = [['extra-rounded', 'très arrondis'], ['square', 'carrés'], ['dot', 'ronds']];
const ENTRE = [[' · ', '« · » (une seule ligne)'], [' | ', '« | » (une seule ligne)'], ['\n', 'saut de ligne (invisible sur iPhone)']];

async function api(chemin, corps) {
  const init = corps === undefined ? {} : {method: 'POST', body: JSON.stringify(corps),
    headers: {'Content-Type': 'application/json', 'X-Etiquettes-QR': '1'}};
  const r = await fetch(chemin, init);
  const t = await r.text();
  if (!r.ok) throw new Error(t || ('HTTP ' + r.status));
  return JSON.parse(t);
}

function el(balise, attributs, texte) {
  const e = document.createElement(balise);
  Object.entries(attributs || {}).forEach(([k, v]) => { if (k === 'class') e.className = v; else e.setAttribute(k, v); });
  if (texte !== undefined && texte !== null) e.textContent = texte;
  return e;
}

function options(select, liste, valeur) {
  select.replaceChildren(...liste.map(([v, t]) => { const o = el('option', {}, t); o.value = v; return o; }));
  select.value = valeur;
}

function octets(texte) {
  let s = '';
  new TextEncoder().encode(texte).forEach(b => { s += String.fromCharCode(b); });
  return s;
}

function optionsQR(texte, style, correction, image, px, modules) {
  const couleur = style.couleur || '#000000';
  return {width: px, height: px, type: 'svg', data: octets(texte), image: image || undefined,
    margin: modules ? Math.round(4 * px / (modules + 8)) : 0,
    qrOptions: {typeNumber: 0, mode: 'Byte', errorCorrectionLevel: correction},
    dotsOptions: {type: style.points || 'square', color: couleur},
    cornersSquareOptions: {type: style.coins || 'square', color: couleur},
    cornersDotOptions: {type: style.coins === 'square' ? 'square' : 'dot', color: couleur},
    backgroundOptions: {color: style.fond || '#ffffff'},
    imageOptions: {margin: 2, imageSize: 0.3, hideBackgroundDots: true}};
}

function clone(o) { return JSON.parse(JSON.stringify(o)); }
function empreinteLocale() { return JSON.stringify({r: ETAT.reglage, p: ETAT.page}); }
function sale() { return ETAT.reglage !== null && empreinteLocale() !== ETAT.charge; }

function avert(parent, texte, couleur) {
  parent.appendChild(el('div', {class: 'avert' + (couleur ? ' ' + couleur : '')}, texte));
}

// ---------------------------------------------------------------- cartes
function majPastilles() {
  const p = $('pastilles');
  p.replaceChildren();
  const c = ETAT.cartes.find(x => x.nom === ETAT.env);
  if (!c) return;
  p.appendChild(el('span', {class: 'pastille ' + (c.regle ? 'bleu' : '')}, c.regle ? 'réglage propre' : 'gabarit commun'));
  if (c.esp32) p.appendChild(el('span', {class: 'pastille ' + (c.page ? 'ok' : '')}, c.page ? 'page /qrcode' : 'sans page'));
  if (sale()) p.appendChild(el('span', {class: 'pastille or'}, 'modifications non écrites'));
}

function dessineListe() {
  const liste = $('liste-cartes');
  liste.replaceChildren();
  const groupes = ETAT.lieux.map(l => [l[1], ETAT.cartes.filter(c => c.lieu === l[0])]);
  const connus = ETAT.lieux.map(l => l[0]);
  ETAT.cartes.forEach(c => { if (connus.indexOf(c.lieu) < 0) groupes.push([c.lieu, [c]]); });
  groupes.forEach(([titre, cartes]) => {
    if (!cartes.length) return;
    liste.appendChild(el('div', {class: 'lieu'}, titre));
    cartes.forEach(c => {
      const ligne = el('div', {class: 'env-ligne'});
      const coche = el('input', {type: 'checkbox', 'aria-label': 'Planche : ' + c.nom});
      coche.checked = ETAT.planche.has(c.nom);
      coche.onchange = () => { if (coche.checked) ETAT.planche.add(c.nom); else ETAT.planche.delete(c.nom); majPlanche(); };
      ligne.appendChild(coche);
      const b = el('button', {type: 'button', class: 'env' + (c.nom === ETAT.env ? ' sel' : ''), title: c.nom});
      b.appendChild(el('span', {class: 'nom'}, c.nom.replace(/^tasmota(32\w*)?-/, '')));
      b.appendChild(el('span', {class: 'doux petit'}, (c.puce || '').replace(/^ESP32-/, '')));   // P4 et S3 homonymes
      if (c.regle) b.appendChild(el('span', {class: 'pastille bleu'}, 'propre'));
      if (c.page) b.appendChild(el('span', {class: 'pastille ok'}, 'page'));
      b.onclick = () => choisit(c.nom);
      ligne.appendChild(b);
      liste.appendChild(ligne);
    });
  });
  majPlanche();
}

async function chargeCartes(choisi) {
  const d = await api('/cartes');
  ETAT.cartes = d.cartes;
  ETAT.lieux = d.lieux;
  remplitParLieu($('choix-env'), ETAT.cartes, ETAT.lieux, choisi);
  dessineListe();
  majPastilles();
}

function siPropre(libelle, action) {
  // Modifications non ecrites : demande dans la page (jamais de confirm() qui bloque), sinon agit tout de suite
  if (!sale()) { action(); return; }
  const b = $('bandeau');
  b.replaceChildren();
  const d = el('div', {class: 'avert'}, 'Les modifications de ' + ETAT.env + ' ne sont pas écrites. ');
  const oui = el('button', {type: 'button', class: 'btn mini'}, 'Les abandonner et ' + libelle);
  const non = el('button', {type: 'button', class: 'btn mini'}, 'Rester');
  oui.onclick = () => { b.replaceChildren(); action(); };
  non.onclick = () => b.replaceChildren();
  d.append(oui, ' ', non);
  b.appendChild(d);
}

function choisit(env) {
  if (env === ETAT.env) return;
  $('choix-env').value = ETAT.env;
  siPropre('ouvrir ' + env, () => ouvre(env));
}

async function ouvre(env) {
  ETAT.envDemande = env;
  try {
    const [r, p] = await Promise.all([api('/reglage?env=' + encodeURIComponent(env)), api('/persist?env=' + encodeURIComponent(env))]);
    if (ETAT.envDemande !== env) return;              // un autre choix est arrive pendant le chargement
    ETAT.env = env;
    ETAT.reglage = r.reglage;
    ETAT.esp32 = r.esp32;
    ETAT.page = r.page;
    ETAT.charge = empreinteLocale();
    const choix = $('ajout-standard').value;
    options($('ajout-standard'), r.champs.map(c => [c, LIBELLES[c] || c]), r.champs.indexOf(choix) >= 0 ? choix : 'hostname');
    ETAT.arbre = p.arbre;
    const u = new URL(location.href);
    u.searchParams.set('env', env);
    history.replaceState(null, '', u);
    $('choix-env').value = env;
    $('ecriture').replaceChildren();
    $('bandeau').replaceChildren();
    dessineListe();
    dessineTout();
    activeImpression();
  } catch (e) {
    if (ETAT.envDemande !== env) return;
    if (ETAT.env) $('choix-env').value = ETAT.env;   // la page montre toujours l'ancienne carte
    $('bandeau').replaceChildren();
    avert($('bandeau'), 'Lecture de ' + env + ' impossible : ' + e.message, 'rouge');
  }
}

// ---------------------------------------------------------------- reglages
function change() {
  $('ecriture').replaceChildren();                   // un diff affiche ne vaut plus pour le reglage modifie
  majPastilles();
  clearTimeout(ETAT.minuterie);
  ETAT.minuterie = setTimeout(apercu, 250);
}

function dessineLignes() {
  const zone = $('lignes');
  zone.replaceChildren();
  const lignes = ETAT.reglage.lignes;
  lignes.forEach((l, i) => {
    const d = el('div', {class: 'lq'});
    d.appendChild(el('span', {class: 'src'}, {standard: 'standard', persist: 'persist', libre: 'libre'}[l.source] || l.source));
    if (l.source === 'libre') {
      const t = el('input', {type: 'text', maxlength: '120', 'aria-label': 'Texte libre', style: 'grid-column:2 / 4'});
      t.value = l.texte || '';
      t.oninput = () => { l.texte = t.value; change(); };
      d.appendChild(t);
    } else {
      const lib = el('input', {type: 'text', maxlength: '40', 'aria-label': 'Libellé', placeholder: 'libellé'});
      lib.value = l.libelle || '';
      lib.oninput = () => { l.libelle = lib.value; change(); };
      d.appendChild(lib);
      d.appendChild(el('span', {class: 'petit', title: l.cle || l.chemin}, l.source === 'standard' ? (LIBELLES[l.cle] || l.cle) : l.chemin));
    }
    const act = el('span', {class: 'act'});
    [['↑', -1, 'Monter'], ['↓', 1, 'Descendre']].forEach(([s, pas, titre]) => {
      const b = el('button', {type: 'button', class: 'btn mini', title: titre, 'aria-label': titre}, s);
      b.disabled = i + pas < 0 || i + pas >= lignes.length;
      b.onclick = () => { lignes.splice(i + pas, 0, lignes.splice(i, 1)[0]); dessineLignes(); change(); };
      act.appendChild(b);
    });
    const x = el('button', {type: 'button', class: 'btn mini', title: 'Retirer', 'aria-label': 'Retirer'}, '✕');
    x.disabled = lignes.length <= 1;
    x.onclick = () => { lignes.splice(i, 1); dessineLignes(); change(); };
    act.appendChild(x);
    d.appendChild(act);
    d.appendChild(el('span', {class: 'val'}));
    zone.appendChild(d);
  });
  majValeursLignes();
  $('btn-standard').disabled = $('btn-libre').disabled = lignes.length >= 20;
}

// Retour de l'apercu : seules la valeur lue et la bordure changent. Les champs ne sont JAMAIS recrees ici, sinon celui
// ou l'utilisateur tape perd le focus a chaque lettre (signale le 2026-11-12).
function majValeursLignes() {
  const lues = (ETAT.apercu && ETAT.apercu.lignes) || [];
  document.querySelectorAll('#lignes .lq').forEach((d, i) => {
    const lu = lues[i] || {};
    d.className = 'lq' + (lu.etat && lu.etat !== 'ok' ? ' ' + lu.etat : '');
    d.querySelector('.val').textContent = !lu.etat ? '' : lu.etat === 'ok' ? '= ' + lu.valeur
      : 'omise : ' + (lu.etat === 'refuse' ? 'refusée' : 'introuvable');
  });
}

function ajoute(ligne) {
  if (ETAT.reglage.lignes.length >= 20) return;
  ETAT.reglage.lignes.push(ligne);
  dessineLignes();
  change();
}

function dessinePersist() {
  const zone = $('persist');
  zone.replaceChildren();
  const f = $('filtre-persist').value.trim().toLowerCase();
  const liste = ETAT.arbre.filter(x => !f || x.chemin.toLowerCase().indexOf(f) >= 0 || String(x.valeur).toLowerCase().indexOf(f) >= 0);
  if (!ETAT.arbre.length) { zone.appendChild(el('div', {class: 'doux petit', style: 'padding:6px'}, 'Pas de persist pour cette carte.')); return; }
  liste.slice(0, 300).forEach(x => {
    const b = el('button', {type: 'button', title: 'Ajouter cette clé'}, x.chemin + ' ');
    b.appendChild(el('span', {class: 'v'}, '= ' + x.valeur));
    b.onclick = () => ajoute({source: 'persist', chemin: x.chemin, libelle: x.chemin.split('.').pop()});
    zone.appendChild(b);
  });
  if (liste.length > 300) zone.appendChild(el('div', {class: 'doux petit', style: 'padding:6px'}, (liste.length - 300) + ' clés de plus : affiner le filtre.'));
}

function dessineStyle() {
  const s = ETAT.reglage.style || (ETAT.reglage.style = {});
  options($('points'), POINTS, s.points || 'square');
  options($('coins'), COINS, s.coins || 'square');
  $('couleur').value = s.couleur || '#000000';
  $('fond').value = s.fond || '#ffffff';
  const img = $('image');
  options(img, [['', 'aucune']].concat(ETAT.images.map(n => [n, n])), s.image || '');
  if (s.image && img.value !== s.image) { const o = el('option', {}, s.image + ' (absente)'); o.value = s.image; img.appendChild(o); img.value = s.image; }
  const pc = $('page-carte');
  pc.checked = ETAT.page;
  pc.disabled = !ETAT.esp32;
  $('page-note').textContent = ETAT.esp32 ? 'route /qrcode de la carte' : 'impossible sur un ESP8266 : étiquette seulement';
}

function dessineTout() {
  const r = ETAT.reglage;
  $('separateur').value = r.separateur === undefined ? ' : ' : r.separateur;
  options($('entre-lignes'), ENTRE, r.entre_lignes === undefined ? '\n' : r.entre_lignes);
  $('taille').value = r.taille_mm || 25;
  $('mm').textContent = (r.taille_mm || 25) + ' mm';
  ETAT.apercu = null;
  dessineLignes();
  dessinePersist();
  dessineStyle();
  majPastilles();
  apercu();
}

// ---------------------------------------------------------------- apercu
async function apercu() {
  if (!ETAT.env) return;
  const n = ++ETAT.demande;
  let a;
  try {
    a = await api('/apercu', {env: ETAT.env, reglage: ETAT.reglage});
  } catch (e) {
    a = {erreurs: [e.message]};
  }
  if (n !== ETAT.demande) return;                    // une saisie plus recente a deja relance l'apercu
  ETAT.apercu = a.erreurs && a.erreurs.length ? null : a;
  majValeursLignes();
  const qr = $('qr'), lu = $('lu'), v = $('verdict'), av = $('avertissements');
  qr.replaceChildren(); av.replaceChildren();
  if (!ETAT.apercu) {
    lu.textContent = '';
    v.className = 'verdict cache';
    a.erreurs.forEach(m => avert(av, m, 'rouge'));
    return;
  }
  lu.textContent = a.texte;
  const vd = a.verdict;
  v.className = 'verdict ' + vd.niveau;
  const corr = 'correction ' + a.correction + (a.correction === 'H' ? ' (image)' : '');
  v.textContent = vd.niveau === 'trop_long'
    ? 'Trop long : ' + vd.octets + ' octets dépassent la capacité d\'un QR code (' + corr + '). Retirer des lignes.'
    : ({lisible: 'Lisible', limite: 'À la limite', trop_dense: 'Trop dense pour ' + ETAT.reglage.taille_mm + ' mm'}[vd.niveau])
      + ' : ' + vd.octets + ' octets, version ' + vd.version + ', ' + vd.modules + ' modules, module de '
      + vd.module_mm.toFixed(2).replace('.', ',') + ' mm (' + corr + ').';
  (a.avertissements || []).forEach(m => avert(av, m));
  if (!window.QRCodeStyling) avert(av, 'Bibliothèque de dessin absente (/lib.js) : QR code non dessiné.', 'rouge');
  else if (vd.niveau !== 'trop_long' && a.texte) {
    new QRCodeStyling(optionsQR(a.texte, ETAT.reglage.style || {}, a.correction, a.image, 220, vd.modules)).append(qr);
    qr.dataset.modules = vd.modules;
  }
}

// ---------------------------------------------------------------- ecriture
function montreDiff(prevu, titre, surConfirme) {
  const z = $('ecriture');
  z.replaceChildren();
  z.appendChild(el('h3', {}, titre));
  (prevu.signaux || []).forEach(m => avert(z, m));
  if (!prevu.fichiers.length) { avert(z, 'Rien à écrire : le dépôt est déjà à jour.', 'vert'); return; }
  prevu.fichiers.forEach(f => {
    z.appendChild(el('div', {class: 'petit'}, f.chemin + ' (+' + f.ajouts + ' −' + f.retraits + ')'));
    const pre = el('pre', {class: 'diff'});
    f.diff.split('\n').forEach(l => {
      const c = l.startsWith('+++') || l.startsWith('---') || l.startsWith('@@') ? 'c' : l.startsWith('+') ? 'p' : l.startsWith('-') ? 'm' : '';
      pre.appendChild(el('span', c ? {class: c} : {}, l + '\n'));
    });
    z.appendChild(pre);
  });
  const ok = el('button', {type: 'button', class: 'btn prim'}, 'Confirmer l\'écriture');
  const non = el('button', {type: 'button', class: 'btn'}, 'Annuler');
  ok.onclick = async () => {
    ok.disabled = non.disabled = true;
    try { await surConfirme(prevu.empreinte); } catch (e) { avert(z, 'Refusé : ' + e.message, 'rouge'); ok.disabled = non.disabled = false; }
  };
  non.onclick = () => z.replaceChildren();
  const l = el('div', {class: 'ligne'});
  l.append(ok, non);
  z.appendChild(l);
}

async function relitApres(env, succes) {
  // L'ecriture a reussi : un echec de relecture ne doit pas l'afficher comme refusee
  let probleme = null;
  try { await chargeCartes(env); await ouvre(env); } catch (e) { probleme = e.message; }
  const z = $('ecriture');
  z.replaceChildren();
  avert(z, succes, 'vert');
  if (probleme) avert(z, 'Relecture impossible : ' + probleme + '. Recharger la page.');
}

async function prepareEcriture() {
  const env = ETAT.env, corps = {env: env, reglage: clone(ETAT.reglage), page_carte: ETAT.page};
  try {
    const prevu = await api('/diff', corps);
    montreDiff(prevu, 'Écriture pour ' + env, async empreinte => {
      const r = await api('/ecrire', Object.assign(corps, {empreinte: empreinte}));
      await relitApres(env, r.ecrits.length + ' fichier(s) écrit(s) : ' + r.ecrits.join(', '));
    });
  } catch (e) {
    $('ecriture').replaceChildren();
    avert($('ecriture'), 'Écriture impossible : ' + e.message, 'rouge');
  }
}

async function prepareGabarit() {
  const g = clone(ETAT.reglage);
  try {
    const prevu = await api('/gabarit/diff', {gabarit: g});
    montreDiff(prevu, 'Nouveau gabarit commun (toutes les cartes sans réglage propre)', async empreinte => {
      const r = await api('/gabarit/ecrire', {gabarit: g, empreinte: empreinte});
      await relitApres(ETAT.env, 'Gabarit écrit : ' + r.ecrits.join(', ') + '.');
    });
  } catch (e) {
    $('ecriture').replaceChildren();
    avert($('ecriture'), 'Gabarit impossible : ' + e.message, 'rouge');
  }
}

// ---------------------------------------------------------------- branchements
document.querySelectorAll('.onglets button').forEach(b => b.onclick = () => {
  document.querySelectorAll('.onglets button').forEach(x => x.classList.toggle('actif', x === b));
  ['contenu', 'style', 'gabarit'].forEach(o => $('onglet-' + o).classList.toggle('cache', o !== b.dataset.onglet));
});
$('choix-env').onchange = e => choisit(e.target.value);
$('btn-standard').onclick = () => { const c = $('ajout-standard').value; ajoute({source: 'standard', cle: c, libelle: LIBELLES[c]}); };
$('btn-libre').onclick = () => ajoute({source: 'libre', texte: ''});
$('separateur').oninput = e => { ETAT.reglage.separateur = e.target.value; change(); };
$('entre-lignes').onchange = e => { ETAT.reglage.entre_lignes = e.target.value; change(); };
$('filtre-persist').oninput = dessinePersist;
$('taille').oninput = e => { ETAT.reglage.taille_mm = Number(e.target.value); $('mm').textContent = e.target.value + ' mm'; change(); };
['points', 'coins', 'couleur', 'fond'].forEach(id => $(id).oninput = e => { ETAT.reglage.style[id] = e.target.value; change(); });
$('image').onchange = e => { ETAT.reglage.style.image = e.target.value || null; change(); };
$('page-carte').onchange = e => { ETAT.page = e.target.checked; change(); };
$('btn-ecrire').onclick = prepareEcriture;
$('btn-gabarit').onclick = prepareGabarit;
$('btn-reprend').onclick = () => siPropre('reprendre le gabarit commun', async () => {
  try {
    ETAT.reglage = (await api('/gabarit')).gabarit;
    $('ecriture').replaceChildren();
    dessineTout();
  } catch (e) {
    avert($('bandeau'), 'Gabarit illisible : ' + e.message, 'rouge');
  }
});
window.addEventListener('beforeunload', e => { if (sale()) { e.preventDefault(); e.returnValue = ''; } });

(async () => {
  try {
    ETAT.images = (await api('/images')).images;
    $('planche-taille').value = (await api('/gabarit')).gabarit.taille_mm || 25;   // spec 7.9 : taille du gabarit par defaut
    await chargeCartes(null);
    const demande = new URLSearchParams(location.search).get('env');
    const lieu = lieuDemande(ETAT.lieux);
    const par = ETAT.cartes.find(c => c.nom === demande) || (lieu && ETAT.cartes.find(c => c.lieu === lieu)) || ETAT.cartes[0];
    if (par) await ouvre(par.nom);
    if (demande && (!par || par.nom !== demande)) avert($('bandeau'), 'Carte inconnue : ' + demande + '.');
  } catch (e) {
    avert($('bandeau'), 'Chargement impossible : ' + e.message, 'rouge');
  }
})();
"""
