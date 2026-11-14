r"""Impression, planche A4 et export de la page « Etiquettes QR code » (plan A5).

Impression par la fenetre du navigateur : la page monte dans #impression des feuilles A4 (marges 10 mm, espacement 5 mm,
traits de coupe fins au milieu de l'espacement), QR codes en mm : la taille comprend la marge blanche de 4 modules, comme le
verdict (module = taille / (modules + 8)). Une regle de 50 mm en bas de la 1re feuille permet de verifier l'echelle 100 %.
L'impression est notee (empreinte du texte) APRES window.print(), qui ne dit pas si l'utilisateur a annule : « Annuler la
note » est donc toujours propose. La planche d'essai (tailles 15 a 30 mm) n'est jamais notee.
"""

CSS_IMPRESSION = """
#impression{display:none}
@page{size:A4;margin:10mm}
@media print{
  :root,:root[data-theme="sombre"]{color-scheme:light!important}   /* marges de la page peintes aux couleurs du theme */
  html,body{background:#fff!important}
  body > *:not(#impression){display:none!important}
  #impression{display:block}
}
.feuille{width:190mm;height:277mm;display:flex;flex-wrap:wrap;gap:5mm;align-content:flex-start;position:relative;
  break-after:page;page-break-after:always;color:#000;background:#fff}
.feuille:last-child{break-after:auto;page-break-after:auto}
.etiq-case{outline:.1mm dashed #888;outline-offset:2.5mm;text-align:center;overflow:hidden}
.etiq-case svg{display:block}
.etiq-nom{font:2.4mm/2.9mm system-ui,sans-serif;max-height:5.8mm;overflow:hidden;overflow-wrap:anywhere;margin-top:1mm}
.regle{position:absolute;left:0;bottom:0;width:50mm;border-top:.3mm solid #000;font:2.4mm system-ui,sans-serif;padding-top:.5mm}
.regle::before,.regle::after{content:"";position:absolute;top:-1.5mm;height:1.5mm;border-left:.3mm solid #000}
.regle::before{left:0} .regle::after{right:0}
.env-ligne{display:flex;align-items:center;gap:4px}
.env-ligne input{flex:none;margin:0 0 0 4px} .env-ligne .env{flex:1;min-width:0}
"""

JS_IMPRESSION = r"""
// ---------------------------------------------------------------- impression, planche, export (A5)
// A4 moins 10 mm de marge ; 8 mm pour la regle ; 0,01 mm de jeu : une rangee pile a 190 mm ne doit pas deborder a l'arrondi
const MARGE_FEUILLE = {largeur: 190 - 0.01, hauteur: 277 - 8 - 0.01, ecart: 5};

function grille(taille, nom) {
  const haut = taille + (nom ? 7 : 0);               // petit nom : 1 mm + 2 lignes de 2,9 mm
  const colonnes = Math.max(1, Math.floor((MARGE_FEUILLE.largeur + MARGE_FEUILLE.ecart) / (taille + MARGE_FEUILLE.ecart)));
  const lignes = Math.max(1, Math.floor((MARGE_FEUILLE.hauteur + MARGE_FEUILLE.ecart) / (haut + MARGE_FEUILLE.ecart)));
  return {colonnes: colonnes, lignes: lignes, parPage: colonnes * lignes};
}

function nomCourt(env) {
  // Petit nom imprime : sans le prefixe ; puce ajoutee si une autre carte a le meme (cave-serveur-rly ESP32 et S3)
  const court = n => n.replace(/^tasmota(32\w*)?-/, '');
  const c = ETAT.cartes.find(x => x.nom === env);
  const homonyme = ETAT.cartes.some(x => x.nom !== env && court(x.nom) === court(env));
  return court(env) + (homonyme && c && c.puce ? ' (' + c.puce.replace(/^ESP32-/, '') + ')' : '');
}

async function caseQR(item) {
  const taille = Number(item.taille);
  const c = el('div', {class: 'etiq-case', style: 'width:' + taille + 'mm'});
  const q = new QRCodeStyling(optionsQR(item.texte, item.style, item.correction, item.image, 400, item.modules));
  await q.getRawData('svg');                         // attend la fin du dessin (image au centre comprise)
  q.append(c);
  const svg = c.querySelector('svg');
  svg.style.width = svg.style.height = taille + 'mm';
  if (item.legende) c.appendChild(el('div', {class: 'etiq-nom'}, item.legende));
  return c;
}

async function monteFeuilles(items, parPage) {
  const z = $('impression');
  z.replaceChildren();
  for (let i = 0; i < items.length; i += parPage) {
    const f = el('div', {class: 'feuille'});
    for (const item of items.slice(i, i + parPage)) f.appendChild(await caseQR(item));
    if (i === 0) f.appendChild(el('div', {class: 'regle'}, '50 mm : à vérifier à la règle (échelle 100 %)'));
    z.appendChild(f);
  }
  return z.querySelectorAll('.feuille').length;
}

// Un item par carte : texte, correction et image resolus par le serveur, comme l'apercu
async function itemDe(env, reglage, taille, legende) {
  const a = await api('/apercu', {env: env, reglage: Object.assign(clone(reglage), {taille_mm: taille})});
  if (a.erreurs && a.erreurs.length) return {env: env, refus: a.erreurs.join(' ; ')};
  if (!a.texte) return {env: env, refus: 'aucune ligne lisible (valeurs introuvables)'};
  if (a.verdict.niveau === 'trop_long') return {env: env, refus: 'trop long pour un QR code'};
  return {env: env, reglage: reglage, texte: a.texte, style: reglage.style || {}, correction: a.correction, image: a.image,
          modules: a.verdict.modules, niveau: a.verdict.niveau, taille: taille, legende: legende};
}

function messages(liste, couleur) {
  const z = $('impression-messages');
  z.replaceChildren();
  liste.forEach(m => avert(z, m, couleur));
}

async function imprime(items, parPage, noter, taille) {
  const pages = await monteFeuilles(items, parPage);
  window.print();                                    // bloquant ; ne dit pas si l'utilisateur a annule
  if (!noter) return pages;
  const envs = items.map(i => i.env);
  try {
    await api('/impression', {impressions: items.map(i => ({env: i.env, reglage: Object.assign(clone(i.reglage), {taille_mm: taille})})),
                              taille_mm: taille});
  } catch (e) {
    messages(['Impression non notée : ' + e.message], 'rouge');
    return pages;
  }
  chargeSuivi();                                     // « à réimprimer » s'efface
  const z = $('impression-messages');
  const d = el('div', {class: 'avert vert'}, 'Impression notée pour ' + envs.length + ' carte(s). ');
  const b = el('button', {type: 'button', class: 'btn mini'}, 'Annuler la note');
  b.onclick = async () => {
    b.disabled = true;
    try { for (const e of envs) await api('/impression/annule', {env: e}); d.textContent = 'Note d\'impression annulée.'; chargeSuivi(); }
    catch (e) { avert(z, 'Annulation impossible : ' + e.message, 'rouge'); b.disabled = false; }
  };
  d.appendChild(b);
  z.appendChild(d);
  return pages;
}

async function imprimeCarte() {
  const t = ETAT.reglage.taille_mm || 25;
  const item = await itemDe(ETAT.env, ETAT.reglage, t, $('petit-nom').checked ? nomCourt(ETAT.env) : null);
  if (item.refus) { messages([ETAT.env + ' : ' + item.refus], 'rouge'); return 0; }
  messages(item.niveau === 'lisible' ? [] : [ETAT.env + ' : ' + (item.niveau === 'limite' ? 'à la limite' : 'trop dense') + ' à ' + t + ' mm']);
  return imprime([item], 1, true, t);
}

async function imprimePlanche() {
  const envs = ETAT.cartes.map(c => c.nom).filter(n => ETAT.planche.has(n));
  const taille = Number($('planche-taille').value);
  const nom = $('petit-nom').checked;
  if (!envs.length || !(taille >= 10 && taille <= 100)) { messages(['Planche : cocher des cartes, taille de 10 à 100 mm.'], 'rouge'); return 0; }
  const avertissements = [];
  if (envs.indexOf(ETAT.env) >= 0 && sale()) avertissements.push(ETAT.env + ' : imprimée avec ses modifications non écrites');
  const items = await Promise.all(envs.map(async env => {
    const reglage = env === ETAT.env ? ETAT.reglage : (await api('/reglage?env=' + encodeURIComponent(env))).reglage;
    return itemDe(env, reglage, taille, nom ? nomCourt(env) : null);
  }));
  items.filter(i => i.refus).forEach(i => avertissements.push(i.env + ' : ' + i.refus + ', absente de la planche'));
  items.filter(i => !i.refus && i.niveau !== 'lisible').forEach(i => avertissements.push(i.env + ' : ' + (i.niveau === 'limite' ? 'à la limite' : 'trop dense') + ' à ' + taille + ' mm'));
  const bons = items.filter(i => !i.refus);
  messages(avertissements);
  if (!bons.length) return 0;
  return imprime(bons, grille(taille, nom).parPage, true, taille);
}

// Planche d'essai (A5, calage des seuils) : carte affichee a 15, 20, 25 et 30 mm, texte court (1re ligne) et long,
// avec et sans image si une image est choisie ; legende sous chaque code ; jamais notee
async function imprimeEssai() {
  const r = ETAT.reglage, variantes = [['long', r]];
  if (r.lignes.length > 1) variantes.unshift(['court', Object.assign(clone(r), {lignes: [r.lignes[0]]})]);
  if (r.style && r.style.image) variantes.slice().forEach(([n, v]) => {
    const sans = clone(v); sans.style.image = null; variantes.push([n + ' sans img', sans]);
  });
  const items = [];
  for (const [nom, v] of variantes) for (const t of [15, 20, 25, 30]) {
    const i = await itemDe(ETAT.env, v, t, null);
    if (!i.refus) { i.legende = t + ' mm ' + nom; items.push(i); }
  }
  if (!items.length) { messages([ETAT.env + ' : aucune variante imprimable (lignes introuvables ou texte trop long)'], 'rouge'); return 0; }
  messages([]);
  return imprime(items, items.length, false, 0);
}

async function exporte(ext) {
  // Resolu a nouveau par le serveur : l'apercu peut dater d'avant la derniere saisie (minuterie de 250 ms)
  const t = ETAT.reglage.taille_mm || 25;
  const i = await itemDe(ETAT.env, ETAT.reglage, t, null);
  if (i.refus) { messages([ETAT.env + ' : export impossible, ' + i.refus], 'rouge'); return null; }
  const px = Math.max(300, Math.round(t / 25.4 * 300));   // 300 points par pouce
  const q = new QRCodeStyling(Object.assign(optionsQR(i.texte, i.style, i.correction, i.image, px, i.modules),
                                            {type: ext === 'svg' ? 'svg' : 'canvas'}));
  const blob = await q.getRawData(ext);
  const lien = el('a', {href: URL.createObjectURL(blob), download: 'qr_' + ETAT.env + '.' + ext});
  document.body.appendChild(lien);
  lien.click();
  lien.remove();
  setTimeout(() => URL.revokeObjectURL(lien.href), 2000);
  return blob;
}

function majPlanche() {
  const n = ETAT.cartes.filter(c => ETAT.planche.has(c.nom)).length;
  $('btn-planche').textContent = 'Planche (' + n + ' carte' + (n > 1 ? 's' : '') + ')';
  $('btn-planche').disabled = n === 0;
  const g = grille(Number($('planche-taille').value) || 25, $('petit-nom').checked);
  $('planche-grille').textContent = g.colonnes + ' × ' + g.lignes + ' par page' + (n ? ', ' + Math.ceil(n / g.parPage) + ' page(s)' : '');
  const tout = $('planche-tout');
  tout.checked = n > 0 && n === ETAT.cartes.length;
  tout.indeterminate = n > 0 && n < ETAT.cartes.length;
}

const garde = f => async () => {                     // un clic, un traitement : boutons bloques pendant la preparation
  const boutons = ['btn-imprimer', 'btn-planche', 'btn-essai', 'btn-png', 'btn-svg'].map($);
  boutons.forEach(b => { b.disabled = true; });
  try { await f(); } catch (e) { messages(['Impression ou export impossible : ' + e.message], 'rouge'); }
  finally { activeImpression(); }
};

function activeImpression() {                        // rien a imprimer tant qu'aucune carte n'est chargee
  ['btn-imprimer', 'btn-essai', 'btn-png', 'btn-svg'].forEach(id => { $(id).disabled = !ETAT.reglage; });
  majPlanche();
}
window.addEventListener('afterprint', () => $('impression').replaceChildren());   // un Ctrl+P suivant n'imprime pas l'ancienne planche
$('btn-imprimer').onclick = garde(imprimeCarte);
$('btn-planche').onclick = garde(imprimePlanche);
$('btn-essai').onclick = garde(imprimeEssai);
$('btn-png').onclick = garde(() => exporte('png'));
$('btn-svg').onclick = garde(() => exporte('svg'));
$('planche-taille').oninput = majPlanche;
$('petit-nom').onchange = () => { if ($('petit-nom').checked) ETAT.reglage.petit_nom = true; else delete ETAT.reglage.petit_nom; majPlanche(); change(); };
$('planche-tout').onchange = e => {
  ETAT.planche = new Set(e.target.checked ? ETAT.cartes.map(c => c.nom) : []);
  dessineListe();
};
"""
