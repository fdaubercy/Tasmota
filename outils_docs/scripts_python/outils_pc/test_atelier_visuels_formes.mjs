// Banc node de la logique pure de l'editeur de formes (atelier des visuels) : couleur mediane, aimantation, historique, AV.svg().
//
// UTILISATION (lance par test_atelier_visuels_page_formes.py, qui ecrit le JS dans un fichier et verifie les SVG avec nettoie_svg)
//     node test_atelier_visuels_formes.mjs --js FICHIER_JS [--sortie FICHIER_JSON]
// Code de sortie 0 = vert. --sortie : ecrit les SVG produits ({nom: svg}) pour le controle cote Python.
import fs from 'node:fs';
import vm from 'node:vm';

const arg = (n) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : null; };
const echecs = [];
let nb = 0;
function verifie(obtenu, attendu, libelle) {
  nb++;
  if (JSON.stringify(obtenu) !== JSON.stringify(attendu)) { echecs.push(libelle); console.log('KO   ' + libelle + '  -> obtenu ' + JSON.stringify(obtenu) + ', attendu ' + JSON.stringify(attendu)); }
}

// contexte sans DOM : la liaison DOM ne s'execute pas (typeof document === 'undefined')
const stock = {};
const AV = {larg: 200, haut: 100, mode: 'dessin', photo: null, carte: 'banc', surChangement() {}};
const ctx = {window: {AV}, localStorage: {getItem: (k) => (k in stock ? stock[k] : null), setItem: (k, v) => { stock[k] = String(v); }}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(arg('--js'), 'utf8') + '\nthis.AV_FORMES = AV_FORMES;', ctx);
const F = ctx.AV_FORMES;

// ---- couleur mediane : 10 x 10, moitie gauche rouge, droite bleue, un pixel aberrant
function image(l, h, f) { const d = new Uint8ClampedArray(l * h * 4); for (let y = 0; y < h; y++) for (let x = 0; x < l; x++) { const c = f(x, y); d.set([c[0], c[1], c[2], 255], (y * l + x) * 4); } return {data: d, width: l, height: h}; }
const img = image(10, 10, (x, y) => (x === 2 && y === 2 ? [0, 255, 0] : x < 5 ? [200, 20, 20] : [20, 20, 200]));
verifie(F.mediane(img, {type: 'rect', x: 0, y: 0, l: 5, h: 10}), '#c81414', 'mediane : aberrant ignore');
verifie(F.mediane(img, {type: 'rect', x: 5, y: 0, l: 5, h: 10}), '#1414c8', 'mediane : moitie droite');
verifie(F.mediane(img, {type: 'polygon', points: [[5, 0], [10, 0], [10, 10]]}), '#1414c8', 'mediane : polygone');
verifie(F.mediane(img, {type: 'rect', x: 50, y: 50, l: 5, h: 5}), null, 'mediane : hors photo');
verifie(F.mediane({data: new Uint8ClampedArray(16), width: 2, height: 2}, {type: 'rect', x: 0, y: 0, l: 2, h: 2}), null, 'mediane : pixels transparents');

// ---- aimantation 8 px
verifie(F.aimante(104, [0, 100, 200]), 100, 'aimante : proche');
verifie(F.aimante(108, [100]), 100, 'aimante : 8 px inclus');
verifie(F.aimante(109, [100]), 109, 'aimante : 9 px exclu');
verifie(F.aimanteBord(93, 20, [0, 120]), 100, 'aimanteBord : bord droit (113 -> 120)');
verifie(F.aimanteBord(50, 20, [0, 200]), 50, 'aimanteBord : rien a portee');
const c = F.cibles([{id: 1, type: 'rect', x: 10, y: 20, l: 30, h: 40}, {id: 2, type: 'rect', x: 5, y: 5, l: 5, h: 5}, {id: 3, type: 'rect', x: 99, y: 99, l: 5, h: 5, zone: 'effacer'}], 2, 200, 100);
verifie(c, {xs: [0, 200, 10, 40], ys: [0, 100, 20, 60]}, 'cibles : sans soi-meme ni zones');

// ---- historique : 100 pas
const h = F.historique(100, 's0');
for (let i = 1; i <= 105; i++) h.pousse('s' + i);
verifie(h.profondeur(), 100, 'historique : 100 pas conserves');
let dernier = null, n = 0;
while (true) { const s = h.annule(); if (s === null) break; dernier = s; n++; }
verifie([n, dernier], [100, 's5'], 'historique : annule 100 fois, puis butee');
verifie(h.retablit(), 's6', 'historique : retablit');
h.pousse('neuf');
verifie(h.retablit(), null, 'historique : nouvel etat vide le futur');
verifie(h.pousse('neuf'), false, 'historique : meme etat ignore');

// ---- AV : formes, commit, annule / retablit, sauvegarde
AV.formes.push(F.normalise({id: 1, type: 'rect', x: 10, y: 10, l: 100, h: 50, fill: '#c9b39c'}));
AV.commit();
AV.formes.push(F.nouveauGabarit('fenetre', 30, 20, 2));
AV.commit();
verifie(AV.formes.length, 2, 'AV : deux formes');
AV.annule();
verifie(AV.formes.length, 1, 'AV : annule');
AV.retablit();
verifie(AV.formes.length, 2, 'AV : retablit');
verifie(JSON.parse(stock['av.formes.banc']).length, 2, 'AV : sauvegarde par carte');
stock['av.formes.banc'] = JSON.stringify([{type: 'rect', x: 1, y: 1, l: 9, h: 9, fill: 'javascript:x', id: 7}, {type: 'evil'}, {type: 'gabarit', gabarit: 'constructor', x: 0, y: 0, l: 5, h: 5}, null]);
AV.charge();
verifie(AV.formes.length, 1, 'AV : localStorage revalide (formes invalides ecartees)');
verifie(AV.formes[0].fill, '#888888', 'AV : couleur invalide remplacee');
verifie(F.normalise({type: 'polygon', points: [[0, 0], [1, 1]]}), null, 'normalise : polygone a 2 points refuse');

// ---- AV.svg() : un dessin complet, chaque gabarit
const sorties = {};
function dessin(nom, formes) { AV.formes = formes; sorties[nom] = AV.svg(); return sorties[nom]; }
dessin('vide', []);
verifie(sorties.vide, '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100" width="200" height="100"></svg>', 'svg : vide');
let id = 1;
const tous = Object.keys(F.GAB).map((k, i) => F.nouveauGabarit(k, 5 + i * 3, 5 + i * 2, id++));
tous.push(F.normalise({id: id++, type: 'polygon', points: [[0, 0], [50, 0], [25, 30]], fill: '#aa3300', stroke: '#ffffff', sw: 2}));
tous.push(F.normalise({id: id++, type: 'rect', x: 1, y: 1, l: 20, h: 10, fill: '#112233', zone: 'effacer'}));
tous[0].texte = 'a<b&"c';
const numero = tous.find((f) => f.gabarit === 'numero');
numero.texte = '1<2&"';
const s = dessin('complet', tous);
verifie((s.match(/<pattern /g) || []).length, 3, 'svg : trois motifs (briques, tuiles, lames) une seule fois');
verifie(s.includes('<image') || s.includes('<script') || s.includes('javascript') || s.includes('onload'), false, 'svg : rien de dangereux');
verifie(s.includes('1&lt;2&amp;&quot;'), true, 'svg : texte echappe');
verifie(s.includes('#112233'), false, 'svg : zone effacer absente');
verifie(s.includes('url(#avm_briques)'), true, 'svg : motif reference');
dessin('toit_negatif', [Object.assign(F.nouveauGabarit('toitMono', 10, 10, 1), {pente: -12})]);
verifie(sorties.toit_negatif.includes('points="10,10 350,22 350,50 10,50"'), true, 'svg : toit monopente a pente inversee');
dessin('toit_pente', [Object.assign(F.nouveauGabarit('toitMono', 10, 10, 1), {pente: 16})]);
verifie(sorties.toit_pente.includes('points="10,26 350,10 350,50 10,50"'), true, 'svg : toit monopente');

const sortie = arg('--sortie');
if (sortie) fs.writeFileSync(sortie, JSON.stringify(sorties));
console.log(nb + ' verifications, ' + echecs.length + ' echec(s)');
process.exit(echecs.length ? 1 : 0);
