// Banc node du moteur du visuel d'accueil data/sd/js/visuel.js (plan atelier-visuels A4).
//
// UTILISATION (depuis la racine du depot ; node)
//     node outils_docs/scripts_python/outils_pc/test_visuel_js.mjs [--js FICHIER] [--sans-mutants]
// Code de sortie 0 = vert : le vrai fichier passe tous les cas ET chaque mutant (copie du fichier avec une regle retiree) en echoue
// (temoins negatifs). --js : charge FICHIER a la place de data/sd/js/visuel.js.
//
// Verifie sur un DOM minimal maison (monte et applique, sans navigateur) : voyant par relais et par mesure (on, on_min), valeur
// formatee, liaison ModBus active puis muette au passage du seuil, esclave ok / muet / ip, wifi, element de type inconnu ignore,
// carte muette (etat null : grise, voyants inconnus), relais absent = inconnu, aucune balise fermante dans le texte du fichier.
// La boucle de lecture et le rendu reel : essai sur la carte (A4).
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const i = process.argv.indexOf('--js');
const JS = i > 0 ? process.argv[i + 1] : path.join(process.cwd(), 'data/sd/js/visuel.js');
const SOURCE = fs.readFileSync(JS, 'utf8');

function noeud(nom) {
  return {nom, attrs: {}, enfants: [], textContent: '',
    setAttribute(k, v) { this.attrs[k] = String(v); }, appendChild(e) { this.enfants.push(e); return e; }};
}
function trouve(n, id) {
  if (n.attrs && n.attrs['data-el'] === id) return n;
  for (const e of n.enfants) { const r = trouve(e, id); if (r) return r; }
  return null;
}
const DOC = {hidden: true, createElementNS: (ns, nom) => noeud(nom), getElementById: () => null};

function charge(source) {
  const fenetre = {};
  vm.runInNewContext(source, {window: fenetre, document: DOC, setTimeout: () => 0, clearTimeout: () => {}, fetch: () => Promise.reject(new Error('hors ligne')), console});
  return fenetre.VisuelAccueil;
}

function lance(source) {
  const echecs = [];
  let nb = 0;
  function verifie(obtenu, attendu, libelle) {
    nb++;
    if (JSON.stringify(obtenu) !== JSON.stringify(attendu)) echecs.push(libelle + '  -> obtenu ' + JSON.stringify(obtenu) + ', attendu ' + JSON.stringify(attendu));
  }
  const V = charge(source);
  const desc = {version: 1, fond: {type: 'svg', largeur: 480, hauteur: 320}, elements: [
    {id: 'r1', type: 'voyant', x: 10, y: 10, source: {type: 'relais', n: 1}},
    {id: 'r2', type: 'voyant', x: 20, y: 10, source: {type: 'relais', n: 2}},
    {id: 'r9', type: 'voyant', x: 30, y: 10, source: {type: 'relais', n: 9}},
    {id: 'sw', type: 'voyant', x: 40, y: 10, source: {type: 'mesure', chemin: ['Switch1'], on: 'ON'}},
    {id: 'mn', type: 'voyant', x: 50, y: 10, source: {type: 'mesure', chemin: ['ANALOG', 'A1'], on_min: 2}},
    {id: 'v', type: 'valeur', x: 100, y: 100, source: {type: 'mesure', chemin: ['ANALOG', 'A1']}, style: {unite: 'cm', decimales: 2, texte_avant: 'H '}},
    {id: 'vx', type: 'valeur', x: 100, y: 120, source: {type: 'mesure', chemin: ['ABSENT', 'X']}, style: {}},
    {id: 'ls', type: 'liaison', x: 1, y: 1, x2: 9, y2: 9, source: {type: 'modbus_serie', seuil_s: 90}},
    {id: 'le', type: 'liaison', x: 1, y: 2, x2: 9, y2: 9, source: {type: 'modbus_esclave', id: 3, seuil_s: 90}},
    {id: 'm1', type: 'liaison', x: 1, y: 3, x2: 9, y2: 9, source: {type: 'esclave', mac: 'AA'}},
    {id: 'm2', type: 'liaison', x: 1, y: 4, x2: 9, y2: 9, source: {type: 'esclave', mac: 'BB'}},
    {id: 'm3', type: 'liaison', x: 1, y: 5, x2: 9, y2: 9, source: {type: 'esclave', mac: 'CC'}},
    {id: 'm4', type: 'liaison', x: 1, y: 6, x2: 9, y2: 9, source: {type: 'esclave', mac: 'DD'}},
    {id: 'w', type: 'liaison', x: 1, y: 7, x2: 9, y2: 9, source: {type: 'wifi'}},
    {id: 'zz', type: 'bizarre', x: 1, y: 1, source: {type: 'relais', n: 1}},
  ]};
  const conteneur = noeud('div');
  conteneur.ownerDocument = DOC;
  const svg = V.monte(conteneur, desc, '/visuel?f=fond&v=abc');
  const classe = (id) => trouve(svg, id).attrs['class'];
  const enfantImage = svg.enfants.find((e) => e.nom === 'image');

  verifie(conteneur.enfants[0] === svg && svg.attrs.viewBox === '0 0 480 320', true, 'monte : svg dans le conteneur, viewBox du fond');
  verifie(!!enfantImage && enfantImage.attrs.href === '/visuel?f=fond&v=abc', true, 'monte : fond par image href vers /visuel?f=fond');
  verifie(trouve(svg, 'zz'), null, 'type inconnu : ignore');
  verifie(svg._vz.refs.length, 14, 'monte : 14 calques (le type inconnu n est pas dessine)');

  const etat = {t: 200000, power: [true, false], sensor: {Switch1: 'ON', ANALOG: {A1: 3.14159}},
    modbus: {serie_ms: 150000, esclaves: {'3': 50000}},
    reseau: [{mac: 'AA', etat: 'ok'}, {mac: 'BB', etat: 'muet'}, {mac: 'CC', etat: 'absent'}], wifi: true};
  V.applique(svg, etat);
  verifie(classe('r1'), 'av-v on', 'relais 1 allume : on');
  verifie(classe('r2'), 'av-v off', 'relais 2 eteint : off');
  verifie(classe('r9'), 'av-v inc', 'relais absent : inconnu');
  verifie(classe('sw'), 'av-v on', 'mesure Switch1 == ON : on');
  verifie(classe('mn'), 'av-v on', 'mesure 3,14 >= on_min 2 : on');
  verifie(trouve(svg, 'v').enfants[1].textContent, 'H 3.14 cm', 'valeur : texte avant, 2 decimales, unite');
  verifie(trouve(svg, 'vx').enfants[1].textContent, '--', 'valeur sans mesure : --');
  verifie(classe('ls'), 'av-l active', 'modbus serie : 50 s < 90 s, active');
  verifie(classe('le'), 'av-l muette', 'modbus esclave 3 : 150 s > 90 s, muette');
  verifie(classe('m1'), 'av-l active', 'esclave ok : active');
  verifie(classe('m2'), 'av-l alerte', 'esclave muet : alerte');
  verifie(classe('m3'), 'av-l muette', 'esclave absent : muette');
  verifie(classe('m4'), 'av-l muette', 'esclave sans ligne : muette');
  verifie(classe('w'), 'av-l active', 'wifi up : active');
  verifie(svg.attrs.opacity, '1', 'carte qui repond : pleine opacite');

  // passage du seuil : la meme liaison, 100 s plus tard, devient muette
  V.applique(svg, Object.assign({}, etat, {t: 250000}));
  verifie(classe('ls'), 'av-l muette', 'modbus serie : 100 s > 90 s, muette');
  V.applique(svg, Object.assign({}, etat, {t: 239999}));
  verifie(classe('ls'), 'av-l active', 'modbus serie : juste sous le seuil, active');
  V.applique(svg, Object.assign({}, etat, {sensor: {Switch1: 'OFF', ANALOG: {A1: 1}}, power: [false, true], wifi: false}));
  verifie([classe('r1'), classe('r2'), classe('sw'), classe('mn'), classe('w')], ['av-v off', 'av-v on', 'av-v off', 'av-v off', 'av-l muette'], 'bascule des etats');

  // carte muette : etat null
  V.applique(svg, null);
  verifie([svg.attrs.opacity, classe('r1'), classe('ls'), trouve(svg, 'v').enfants[1].textContent], ['0.45', 'av-v inc', 'av-l muette', '--'], 'etat null : grise, voyants inconnus, valeurs --');
  V.applique(svg, etat);
  verifie([svg.attrs.opacity, classe('r1')], ['1', 'av-v on'], 'la carte revient : le dessin est remis');
  // fond de la valeur proportionnel au texte
  verifie(trouve(svg, 'v').enfants[0].attrs.width, String(Math.round('H 3.14 cm'.length * 14 * 0.6 + 10)), 'fond de la valeur : largeur du texte');
  verifie(/<\/|<!/.test(source), false, 'aucune balise fermante ni commentaire HTML dans le fichier (injecte inline)');
  return {echecs, nb};
}

const bon = lance(SOURCE);
bon.echecs.forEach((e) => console.log('KO   ' + e));
let vert = bon.echecs.length === 0;
console.log((vert ? 'OK   ' : 'KO   ') + bon.nb + ' controles sur ' + path.basename(JS));

const MUTANTS = [
  ['seuil ignore', 't - ms < seuil', 'true'],
  ['seuil inclus a tort', 't - ms < seuil', 't - ms < seuil * 10'],
  ['relais decale d un cran', 'etat.power[s.n - 1]', 'etat.power[s.n]'],
  ['on_min ignore', 'ok >= s.on_min', 'true'],
  ['esclave muet pas en alerte', "l[i].etat === 'muet' || l[i].etat === 'ip'", 'false'],
  ['carte muette non grisee', 'inconnu ? 0.45 : 1', '1'],
  ['decimales ignorees', 'n.toFixed(num(st.decimales, 1, 0, 6))', 'n.toFixed(1)'],
  ['unite ignoree', "(st.unite ? ' ' + String(st.unite).slice(0, 6) : '')", "''"],
  ['relais absent allume', 'return v === undefined || v === null ? null : !!v;', 'return !!v;'],
  ['wifi toujours actif', "etat.wifi === true ? 'active' : 'muette'", "'active'"],
  ['type inconnu dessine', "else if (el.type === 'liaison') refs.push(liaison(doc, el, cal));", "else refs.push(liaison(doc, el, cal));"],
  ['balise fermante dans le fichier', "var NS = 'http://www.w3.org/2000/svg',", "var NS = 'http://www.w3.org/2000/svg', FIN = '</script>',"],
];
if (!process.argv.includes('--sans-mutants')) {
  for (const [nom, avant, apres] of MUTANTS) {
    const n = SOURCE.split(avant).length - 1;
    if (n !== 1) { console.log(`KO   mutant '${nom}' : texte a muter trouve ${n} fois`); vert = false; continue; }
    let rouge;
    try { rouge = lance(SOURCE.replace(avant, () => apres)).echecs.length > 0; } catch (e) { rouge = true; }
    console.log((rouge ? 'OK   ' : 'KO   ') + `mutant '${nom}' : test rouge`);
    vert = vert && rouge;
  }
}
console.log(vert ? 'VERT' : 'ROUGE');
process.exit(vert ? 0 : 1);
