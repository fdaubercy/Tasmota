// Banc node du traceur commun des pages de graphiques (atelier des graphiques, plan A3).
//
// UTILISATION (depuis la racine du depot)
//     node outils_docs/scripts_python/outils_pc/test_pages_graphiques.mjs [--js DOSSIER]
// Code de sortie 0 = vert. --js : charge pages_graphiques_formule.js et pages_graphiques.js depuis DOSSIER (temoin sur
// une copie dans le scratchpad), sinon depuis data/sd/js/.
//
// Les deux fichiers sont executes dans UN contexte vm, comme sur la carte ou ils sont concatenes dans un seul <script>
// (data/fs/pagesGraphiques.be::pagesGraphiques_page). Ce qui est verifie :
//  1. aucun appel d'evaluation dynamique dans le code (motif `eval(`, `Function(`) ;
//  2. PagesFormule.analyse : refus et acceptations du brief, puis PARITE avec la reference Python
//     (atelier_graphiques_description.py::valide_formule) sur chaque formule de cas_description.json et sur des formules
//     du banc. Separation : analyse ne juge que la GRAMMAIRE ; un cas refuse pour un autre motif (nature, cumul, id) a
//     une formule que valide_formule accepte, et c'est valide_formule, pas le verdict du cas, qui sert d'oracle ;
//  3. PagesFormule.calcule : valeurs, null si une serie manque ou vaut null, division par zero -> null ;
//  4. PagesGraphiques.optionDe : pour chaque graphique des descriptions VALIDES du fichier de cas, le type ECharts
//     attendu de son style ; chaque style de `styles` couvert ; seuils et zones ; « série absente » dans le titre ;
//     series en forme objet (A7b) : libelle (legende), unite (infobulle, axes), couleur (palette remplacee), lecture par chemin.
//  5. PagesGraphiques.lecteurCarte (fetch simule) : paquets de 12 chemins, /histo jour et mois (colonnes de seriesFichier).
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {spawnSync} from 'node:child_process';

const RACINE = process.cwd();
const i = process.argv.indexOf('--js');
const DOSSIER_JS = i > 0 ? process.argv[i + 1] : path.join(RACINE, 'data/sd/js');
const CAS = JSON.parse(fs.readFileSync(path.join(RACINE,
  'outils_docs/scripts_python/berry/bouchons_berry/pages_graphiques/cas_description.json'), 'utf8'));
const echecs = [];
let nb = 0;

function verifie(ok, libelle, detail) {
  nb++;
  if (!ok) echecs.push(libelle);
  if (!ok || process.env.BANC_BAVARD) console.log((ok ? 'OK   ' : 'KO   ') + libelle + (ok || detail === undefined ? '' : '  -> ' + JSON.stringify(detail)));
}

// ---- 0. Chargement -------------------------------------------------------------------------------
const contexte = vm.createContext({console, TextEncoder, Intl, Date, Math, JSON});
let sources = '';
try {
  for (const f of ['pages_graphiques_formule.js', 'pages_graphiques.js']) {
    const s = fs.readFileSync(path.join(DOSSIER_JS, f), 'utf8');
    sources += s;
    vm.runInContext(s, contexte, {filename: f});
  }
} catch (e) {
  console.log('ROUGE : chargement impossible : ' + e.message);
  process.exit(1);
}
const F = contexte.PagesFormule, G = contexte.PagesGraphiques;
verifie(F && typeof F.analyse === 'function' && typeof F.calcule === 'function', 'PagesFormule.analyse et .calcule exposes');
verifie(G && typeof G.optionDe === 'function' && typeof G.page === 'function', 'PagesGraphiques.optionDe et .page exposes');
if (echecs.length) { console.log('ROUGE : ' + echecs.join(' ; ')); process.exit(1); }

// ---- 1. Aucune evaluation dynamique -------------------------------------------------------------
verifie(!/\beval\s*\(|\bFunction\s*\(/.test(sources), 'aucun appel eval( ni Function( dans les deux fichiers');

// ---- 2. Analyse ------------------------------------------------------------------------------------
const a = F.analyse('6732 - sensorsCuve.niveauCuve.volume');
verifie(a.ok && JSON.stringify(a.series) === '["sensorsCuve.niveauCuve.volume"]', 'analyse accepte 6732 - sensorsCuve.niveauCuve.volume', a);
for (const f of ['eval(1)', 'a.b; x', 'constructor', 'a.constructor + 1', 'Function("x")', 'x.__proto__', 'a.prototype',
                 'alert(1)', 'min.x(1)', '1e3', '0x10', 'a ** 2', 'window', '']) {
  if (f === 'window') continue;          // un chemin nomme window est un chemin comme un autre (lu dans le SENSOR)
  const r = F.analyse(f);
  verifie(!r.ok && typeof r.erreur === 'string' && r.erreur.length > 0, 'analyse refuse ' + JSON.stringify(f), r);
}
verifie(!F.analyse(42).ok && !F.analyse(null).ok, 'analyse refuse une formule non textuelle');
verifie(JSON.stringify(F.analyse('max(a.b, a.b, c) + a.b').series) === '["a.b","c"]', 'series sans doublon, dans l\'ordre');

// Parite avec la reference Python : chaque formule des cas + formules du banc
const formules = [];
for (const c of CAS.cas) {
  const calc = c.description && c.description.calculees;
  if (calc && typeof calc === 'object') for (const k of Object.keys(calc)) if (calc[k] && typeof calc[k] === 'object' && 'formule' in calc[k]) formules.push(calc[k].formule);
}
const nbCas = formules.length;
formules.push('1', ' 1 ', '1.5', '1.', '.5', '١', 'a', 'a.b.c', 'a..b', 'a.1', '_x', '1a', 'a__b', 'min(1,2)', 'min (1, 2)',
  'abs()', 'round(1)', 'max(1,2,3,4)', '((1))', '(1', '1)', '-(-1)', '-', '1 - - 1', '1 * -2', 'a(1)', 'abs', 'min.x',
  'a\t+\tb', 'a\r+b', 'x'.repeat(201), 'é', 'a + é', '2 * (a.b - min(c.d, 3)) / round(e)', 'a.b.prototype', 'constructor.x',
  '1 2', 'round(1)(2)', 'max(1,)', '1/0');
const py = spawnSync('python', ['-c', `import json,sys
sys.path.insert(0, 'outils_docs/scripts_python/outils_pc')
from atelier_graphiques_description import valide_formule
print(json.dumps([valide_formule(f) is None for f in json.load(sys.stdin)]))`], {input: JSON.stringify(formules), encoding: 'utf8'});
let oracle = null;
try { oracle = JSON.parse(py.stdout); } catch (e) { /* signale ci-dessous */ }
verifie(Array.isArray(oracle) && oracle.length === formules.length, 'reference Python lancee (valide_formule)', py.stderr);
if (Array.isArray(oracle)) {
  formules.forEach((f, k) => verifie(F.analyse(f).ok === oracle[k],
    'parite Python ' + (k < nbCas ? '(cas) ' : '(banc) ') + JSON.stringify(f).slice(0, 60), {js: F.analyse(f), python: oracle[k]}));
}
// Les cas refuses pour motif « formule interdite » sont bien refuses (lecture directe du fichier, sans Python)
for (const c of CAS.cas) {
  const calc = c.description && c.description.calculees;
  if (!calc || typeof calc !== 'object' || String(c.motif).indexOf('formule interdite') < 0) continue;
  for (const k of Object.keys(calc)) if (calc[k] && 'formule' in calc[k] && typeof calc[k].formule === 'string') {
    verifie(!F.analyse(calc[k].formule).ok, 'cas « ' + c.nom + ' » : formule refusee');
  }
}

// ---- 3. Calcul -------------------------------------------------------------------------------------
function calc(f, v) { const r = F.analyse(f); return r.ok ? F.calcule(r.arbre, v) : 'refusee'; }
verifie(calc('6732 - sensorsCuve.niveauCuve.volume', {'sensorsCuve.niveauCuve.volume': 1000}) === 5732, 'calcule 6732 - volume');
verifie(calc('6732 - sensorsCuve.niveauCuve.volume', {'sensorsCuve.niveauCuve.volume': null}) === null, 'calcule : serie null -> null');
verifie(calc('a + 1', {}) === null, 'calcule : serie absente -> null');
verifie(calc('1 + 2 * 3', {}) === 7 && calc('(1 + 2) * 3', {}) === 9 && calc('8 / 4 / 2', {}) === 1 && calc('7 - 2 - 1', {}) === 4,
  'calcule : priorites et associativite a gauche');
verifie(calc('max(a.b, 0) * 2', {'a.b': -3}) === 0 && calc('max(a.b, 0) * 2', {'a.b': 4}) === 8, 'calcule max');
verifie(calc('min(a, b, 3)', {a: 5, b: 4}) === 3 && calc('abs(-a)', {a: 2}) === 2 && calc('round(a)', {a: 2.6}) === 3, 'calcule min, abs, round');
verifie(calc('a*-b', {a: 2, b: 3}) === -6 && calc('-a.b', {'a.b': 4}) === -4, 'calcule moins unaire');
verifie(calc('1/0', {}) === null && calc('a / b', {a: 1, b: 0}) === null, 'calcule : division par zero -> null');
verifie(calc('a + 1', {a: 'x'}) === null && calc('a + 1', {a: true}) === null, 'calcule : valeur non numerique -> null');

// ---- 4. optionDe -----------------------------------------------------------------------------------
const TYPES = {courbe: 'line', aire: 'line', escalier: 'line', barres: 'bar', 'barres-empilees': 'bar', 'barres-periode': 'bar',
  'deux-axes': 'line', lies: 'line', cadran: 'gauge', anneau: 'pie', chaleur: 'heatmap', nuage: 'scatter', radar: 'radar',
  liquide: 'liquidFill', 'demi-cercle': 'svg'};
verifie(JSON.stringify(Object.keys(TYPES)) === JSON.stringify(CAS.styles), 'table du banc = styles du fichier de cas');
verifie(JSON.stringify(Array.from(G.STYLES)) === JSON.stringify(CAS.styles), 'PagesGraphiques.STYLES = styles du fichier de cas');
const THEME = {texte: '#eaeaea', grille: 'rgba(128,128,128,0.25)', fond: '#252525'};
const T0 = 1762128000;           // 2025-11-03 00:00 UTC
function donneesDe(series, n = 30) {
  const d = {t: [], valeurs: {}};
  for (let k = 0; k < n; k++) d.t.push(T0 + k * 1800);
  series.forEach((s, j) => { d.valeurs[s] = d.t.map((_, k) => 10 + j * 5 + k); });
  return d;
}
function typeRendu(o) {
  if (o && typeof o.svg === 'string') return 'svg';
  return o && o.series && o.series[0] && o.series[0].type;
}
const vus = new Set();
for (const c of CAS.cas.filter(c => c.valide)) {
  for (const p of c.description.pages) for (const g of p.graphiques) {
    const o = G.optionDe(g, donneesDe(g.series.map(s => s && typeof s === 'object' ? s.chemin : s)), THEME);
    vus.add(g.type);
    verifie(typeRendu(o) === TYPES[g.type], `cas « ${c.nom} » : ${g.type} -> ${TYPES[g.type]}`, typeRendu(o));
    verifie(JSON.stringify(o).indexOf('série absente') < 0, `cas « ${c.nom} » : pas de « série absente » avec toutes les series`);
  }
}
verifie(CAS.styles.every(s => vus.has(s)), 'chaque style de `styles` couvert par une description valide', CAS.styles.filter(s => !vus.has(s)));

function cp0() { return {t: [T0, T0 + 1200, T0 + 2400, T0 + 3600, T0 + 4800, T0 + 6000], valeurs: {'e.kwh': [100, 101, 103, 0, 2, 5]}}; }
// Details de rendu par style
const opt = (type, extra, series = ['a.b', 'c.d']) => G.optionDe(Object.assign({type, titre: 'T', series}, extra || {}),
  donneesDe(series.map(s => typeof s === 'object' ? s.chemin : s)), THEME);
verifie(!!opt('aire').series[0].areaStyle && !opt('courbe').series[0].areaStyle, 'aire : areaStyle, courbe : sans');
verifie(!!opt('escalier').series[0].step, 'escalier : step');
verifie(opt('barres-empilees').series.every(s => s.stack === opt('barres-empilees').series[0].stack && s.stack), 'barres empilees : meme stack');
const da = opt('deux-axes');
verifie(da.yAxis.length === 2 && da.series[0].yAxisIndex === 0 && da.series[1].yAxisIndex === 1, 'deux-axes : 2 axes Y, une serie par axe');
verifie(opt('anneau').series[0].data.length === 2 && Array.isArray(opt('anneau').series[0].radius), 'anneau : une part par serie, rayon interieur');
verifie(opt('radar').radar.indicator.length === 2, 'radar : un indicateur par serie');
const homonymes = opt('courbe', {}, ['DS18B20.Temperature', 'ESP32.Temperature', 'a.Humidity']).series.map(s => s.name);
verifie(JSON.stringify(homonymes) === '["DS18B20.Temperature","ESP32.Temperature","Humidity"]', 'libelles : deux derniers segments si homonymes', homonymes);
const nu = opt('nuage');
verifie(nu.series[0].data[0][0] === 10 && nu.series[0].data[0][1] === 15, 'nuage : x = 1re serie, y = 2e serie');
const ch = opt('chaleur', {}, ['a.b']);
verifie(ch.xAxis.data.length === 24 && ch.series[0].data.length > 0 && !!ch.visualMap, 'chaleur : 24 heures en x, visualMap');

// Series en forme objet {chemin, libelle, unite, couleur} (A7b) : lues par leur chemin, melees aux chaines
const CUVE = {chemin: 'a.b', libelle: 'Cuve', unite: '°C', couleur: '#ff00aa'};
const ob = opt('courbe', {}, [CUVE, 'c.d']);
const s0 = ob.series[0], s1 = ob.series[1];
verifie(s0.name === 'Cuve' && s1.name === 'd', 'objet : libelle dans la legende, chaine : dernier segment', [s0.name, s1.name]);
verifie(s0.color === '#ff00aa' && s1.color === Array.from(G.PALETTE)[1], 'objet : couleur posee, chaine : couleur de la palette', [s0.color, s1.color]);
verifie(s0.data.length === 30 && s0.data[3][1] === 13, 'objet : valeurs lues par le chemin', s0.data[3]);
verifie(!!s0.tooltip && s0.tooltip.valueFormatter(12.5) === '12,5 °C' && s0.tooltip.valueFormatter([T0, 3]) === '3 °C' &&
  s0.tooltip.valueFormatter(null) === '-- °C' && !s1.tooltip, 'objet : unite dans l\'infobulle (chaine : infobulle par defaut)');
verifie(!ob.yAxis.name, 'axe unique, unites differentes : pas d\'unite sur l\'axe', ob.yAxis.name);
verifie(opt('aire', {}, [CUVE, {chemin: 'c.d', unite: '°C'}]).yAxis.name === '°C', 'axe unique, meme unite : unite sur l\'axe');
const da2 = opt('deux-axes', {}, [CUVE, {chemin: 'c.d', unite: '%', couleur: '#00aa00'}]);
verifie(da2.yAxis[0].name === '°C' && da2.yAxis[1].name === '%' && da2.series[1].color === '#00aa00', 'deux-axes : chaque axe avec l\'unite de sa serie',
  da2.yAxis.map(a => a.name));
const bp2 = G.optionDe({type: 'barres-periode', titre: 'kWh', series: [{chemin: 'e.kwh', libelle: 'Conso', unite: 'kWh', couleur: '#123456'}], cumul: 'heure'}, cp0(), THEME);
verifie(bp2.series[0].name === 'Conso' && bp2.series[0].color === '#123456' && bp2.yAxis.name === 'kWh' &&
  bp2.series[0].tooltip.valueFormatter(3) === '3 kWh', 'barres par periode : libelle, couleur, unite (axe et infobulle)', bp2.series[0]);
const an = opt('anneau', {}, [CUVE, 'c.d']).series[0].data;
verifie(an[0].name === 'Cuve' && an[0].itemStyle.color === '#ff00aa' && an[1].itemStyle.color === Array.from(G.PALETTE)[1] &&
  an[0].tooltip.valueFormatter(4) === '4 °C', 'anneau : libelle, couleur et unite de la part', an[0]);
const ca2 = opt('cadran', {min: 0, max: 100}, [CUVE]).series[0];
verifie(ca2.detail.formatter === '39 °C' && ca2.data[0].name === 'Cuve' && JSON.stringify(ca2.axisLine.lineStyle.color) === '[[1,"#ff00aa"]]',
  'cadran : unite sous l\'aiguille, libelle, couleur hors zones', ca2);
const li2 = G.optionDe({type: 'liquide', titre: 'L', series: [CUVE], min: 0, max: 100}, {t: [T0], valeurs: {'a.b': [10]}}, THEME).series[0];
verifie(li2.color[0] === '#ff00aa' && li2.label.formatter === '10 °C', 'liquide : couleur et unite de la serie', li2);
const dc2 = G.optionDe({type: 'demi-cercle', titre: 'T', series: [{chemin: 'a.b', unite: '<b>', couleur: '#ff00aa'}], min: 0, max: 100},
  {t: [T0], valeurs: {'a.b': [10]}}, THEME).svg;
verifie(dc2.indexOf('#ff00aa') > 0 && dc2.indexOf('10 &#60;b&#62;') > 0 && dc2.indexOf('<b>') < 0, 'demi-cercle : couleur, unite echappee', dc2);
const nu2 = opt('nuage', {}, [CUVE, {chemin: 'c.d', libelle: 'Humidite', unite: '%'}]);
verifie(nu2.xAxis.name === 'Cuve °C' && nu2.yAxis.name === 'Humidite %' && nu2.series[0].color === '#ff00aa', 'nuage : axes nommes avec unite, couleur',
  [nu2.xAxis.name, nu2.yAxis.name, nu2.series[0].color]);
verifie(opt('radar', {}, [CUVE, 'c.d']).radar.indicator[0].name === 'Cuve', 'radar : libelle de l\'indicateur');
const ho = opt('courbe', {}, [{chemin: 'DS18B20.Temperature', libelle: 'Cuve'}, 'ESP32.Temperature', 'a.Temperature']).series.map(s => s.name);
verifie(JSON.stringify(ho) === '["Cuve","ESP32.Temperature","a.Temperature"]', 'homonymes : une serie a libelle ne compte plus', ho);
const ho2 = opt('courbe', {}, [{chemin: 'DS18B20.Temperature', libelle: 'Cuve'}, 'ESP32.Temperature']).series.map(s => s.name);
verifie(JSON.stringify(ho2) === '["Cuve","Temperature"]', 'homonyme a libelle : l\'autre serie garde le dernier segment', ho2);
const ab = G.optionDe({type: 'courbe', titre: 'V', series: [CUVE, {chemin: 'absente.x', libelle: 'X'}]}, donneesDe(['a.b']), THEME);
verifie(ab.title.text.indexOf('série absente') > 0 && ab.series.length === 1 && ab.series[0].name === 'Cuve', 'objet : serie absente reperee par son chemin');

// Cumul par periode : hausses d'un compteur ; apres une remise a zero, la nouvelle valeur compte depuis zero
const cp = cp0();
const bp = G.optionDe({type: 'barres-periode', titre: 'kWh', series: ['e.kwh'], cumul: 'heure'}, cp, THEME);
verifie(JSON.stringify(bp.series[0].data) === '[3,5]', 'barres par periode (heure) : 3 puis 5', bp.series[0].data);
const rz = G.optionDe({type: 'barres-periode', titre: 'kWh', series: ['e.kwh'], cumul: 'heure'},
  {t: [T0, T0 + 600, T0 + 1200, T0 + 1800], valeurs: {'e.kwh': [10, 12, 1, 4]}}, THEME);
verifie(JSON.stringify(rz.series[0].data) === '[6]', 'barres par periode : remise a zero vers 1 comptee (2 + 1 + 3)', rz.series[0].data);

// Seuils et zones
const zones = [[0.2, '#c0392b'], [0.4, '#c27400']];
const co = opt('courbe', {min: 0, max: 100, zones});
const ma = co.series[0].markArea, ml = co.series[0].markLine;
verifie(ma && ma.data.length === 2 && ma.data[0][0].yAxis === 0 && ma.data[0][1].yAxis === 20 && ma.data[1][1].yAxis === 40,
  'courbe : markArea 0-20 et 20-40', ma);
verifie(ml && JSON.stringify(ml.data.map(x => x.yAxis)) === '[20,40]', 'courbe : markLine a 20 et 40', ml);
verifie(co.yAxis.min === 0 && co.yAxis.max === 100, 'courbe : bornes min et max sur l\'axe Y');
const ca = opt('cadran', {min: 0, max: 6732, zones}, ['v']);
const couleurs = ca.series[0].axisLine.lineStyle.color;
verifie(couleurs.length === 3 && couleurs[0][0] === 0.2 && couleurs[0][1] === '#c0392b' && couleurs[2][0] === 1,
  'cadran : axisLine = zones puis couleur par defaut jusqu\'a 1', couleurs);
verifie(ca.series[0].min === 0 && ca.series[0].max === 6732 && ca.series[0].data[0].value === 39, 'cadran : bornes et derniere valeur');
const bas = {t: [T0], valeurs: {v: [10]}};
const li = G.optionDe({type: 'liquide', titre: 'L', series: ['v'], min: 0, max: 100, zones}, bas, THEME);
verifie(li.series[0].data[0] === 0.1 && li.series[0].color[0] === '#c0392b', 'liquide : fraction 0,1 et couleur de la zone basse', li.series[0]);
const dc = G.optionDe({type: 'demi-cercle', titre: 'Taux', series: ['v'], min: 0, max: 100, zones}, bas, THEME);
verifie(dc.svg.indexOf('#c0392b') > 0 && dc.svg.indexOf('stroke-dasharray="10 100"') > 0 && dc.svg.indexOf('<svg') === 0,
  'demi-cercle : arc a 10 % dans la couleur de la zone basse', dc.svg);
const haut = G.optionDe({type: 'demi-cercle', titre: 'Taux', series: ['v'], min: 0, max: 100, zones}, {t: [T0], valeurs: {v: [90]}}, THEME);
verifie(haut.svg.indexOf('#c0392b') < 0 && haut.svg.indexOf('#c27400') < 0, 'demi-cercle : hors zones, couleur par defaut');
const dangereux = G.optionDe({type: 'demi-cercle', titre: '<script>x</script>', series: ['v']}, bas, THEME);
verifie(dangereux.svg.indexOf('<script') < 0, 'demi-cercle : titre echappe');

// Serie absente (« A surveiller » 2) : titre suffixe, les autres series restent tracees
for (const s of CAS.styles) {
  const o = G.optionDe({type: s, titre: 'Volume', series: ['a.b', 'absente.x']}, donneesDe(['a.b']), THEME);
  const titre = o.svg !== undefined ? o.svg : (o.title && o.title.text);
  verifie(typeof titre === 'string' && titre.indexOf('Volume') >= 0 && titre.indexOf('série absente') > 0,
    s + ' : titre suffixe « série absente »', titre);
}
const nulles = G.optionDe({type: 'courbe', titre: 'V', series: ['a.b']}, {t: [T0, T0 + 1], valeurs: {'a.b': [null, null]}}, THEME);
verifie(nulles.title.text.indexOf('série absente') > 0, 'serie presente mais toute a null : « série absente »');
const partielle = G.optionDe({type: 'courbe', titre: 'V', series: ['a.b', 'absente.x']}, donneesDe(['a.b']), THEME);
verifie(partielle.series.length === 1 && partielle.series[0].data.length === 30, 'serie absente : la serie presente reste tracee');
const vide = G.optionDe({type: 'cadran', titre: 'V', series: ['a.b']}, {t: [], valeurs: {}}, THEME);
verifie(vide.title.text.indexOf('série absente') > 0 && vide.series[0].type === 'gauge', 'donnees vides : cadran trace, série absente');
// Capteur debranche en direct : le tampon garde [5, 6] puis la carte rend null -> aucune valeur perimee en instantane
const perime = {t: [T0, T0 + 10, T0 + 20], valeurs: {'a.b': [5, 6, null]}};
for (const s of ['cadran', 'anneau', 'radar', 'liquide', 'demi-cercle']) {
  const o = G.optionDe({type: s, titre: 'V', series: ['a.b']}, perime, THEME);
  const texte = o.svg !== undefined ? o.svg : o.title.text;
  verifie(texte.indexOf('série absente') > 0 && JSON.stringify(o).indexOf('"6"') < 0 && !/>6</.test(texte) &&
    !(o.series && o.series[0] && o.series[0].data && o.series[0].data[0] && o.series[0].data[0].value === 6),
    s + ' : dernier point null -> série absente, 6 jamais montre', texte);
}
const courbePerime = G.optionDe({type: 'courbe', titre: 'V', series: ['a.b']}, perime, THEME);
verifie(courbePerime.title.text.indexOf('série absente') < 0 &&
  JSON.stringify(courbePerime.series[0].data.map(p => p[1])) === '[5,6,null]', 'courbe : les points precedents restent traces');

// ---- 5. Lecteur de la carte (fetch simule : URL appelees, formes de /pages et /histo) -------------------
const appels = [];
const REPONSES = {
  pages: u => ({t: 1000, valeurs: Object.fromEntries(new URL(u, 'http://c').searchParams.get('c').split(',')
    .map(c => [c, c === 'x.absent' ? null : 1]))}),
  jour: () => ({series: ['a.b', 'c.d'], pas: 300, t0: T0, valeurs: [[1, 2], [3, 4]], tEncours: T0 + 600, encours: [5, 6]}),
  // colonnes du fichier (seriesFichier) dans un autre ordre que la liste du moment (series)
  mois: () => ({series: ['c.d', 'a.b'], seriesFichier: ['a.b', 'c.d'], lignes: [[T0, 0, 7, 9, 0, 8, 9]]})};
contexte.fetch = u => {
  appels.push(u);
  const k = u.indexOf('/pages') === 0 ? 'pages' : u.indexOf('p=jour') > 0 ? 'jour' : 'mois';
  return Promise.resolve({ok: true, status: 200, json: () => Promise.resolve(REPONSES[k](u))});
};
const lecteur = G.lecteurCarte('mesures', true);
const quatorze = Array.from({length: 13}, (_, k) => 's.v' + k).concat(['x.absent']);
const direct = await lecteur(quatorze, 'direct');
verifie(appels.length === 2 && appels[0].indexOf('/pages?f=valeurs&c=s.v0,') === 0, '14 chemins : 2 requetes /pages (12 au plus)', appels);
verifie(direct.t[0] === 1000 && direct.valeurs['s.v12'][0] === 1 && direct.valeurs['x.absent'][0] === null, 'direct : un point {t, valeurs}');
const jour = await lecteur(['c.d'], 'jour');
verifie(appels[2] === '/histo?n=mesures&p=jour', 'jour : /histo?n=mesures&p=jour', appels[2]);
verifie(JSON.stringify(jour) === JSON.stringify({t: [T0, T0 + 300, T0 + 600], valeurs: {'c.d': [3, 4, 6]}}),
  'jour : t0 + k * pas, puis le pas en cours', jour);
const mois = await lecteur(['a.b'], 'mois');
verifie(/^\/histo\?n=mesures&p=mois&m=\d{4}-\d{2}$/.test(appels[3]), 'mois : mois UTC en cours', appels[3]);
verifie(JSON.stringify(mois.valeurs) === '{"a.b":[7]}', 'mois : moyenne lue dans la colonne de seriesFichier', mois.valeurs);
const sansHisto = await G.lecteurCarte('mesures', false)(['a.b'], 'jour');
verifie(appels.length === 4 && JSON.stringify(sansHisto) === '{"t":[],"valeurs":{}}', 'sans historique : aucune requete, series absentes');
// Carte qui vient de demarrer : /histo repond 404 « historique inconnu » tant que l'historique n'est pas cree (~3 min)
const reponse404 = corps => () => Promise.resolve({ok: false, status: 404, json: () => Promise.resolve(corps)});
contexte.fetch = reponse404({erreur: 'historique inconnu', noms: []});
const attente = await lecteur(['a.b'], 'jour').then(() => null, e => e);
verifie(attente && attente.attente === true && attente.message === 'La carte vient de démarrer, historique en préparation',
  '404 « historique inconnu » : message d\'attente, marque attente', attente && attente.message);
contexte.fetch = reponse404({erreur: 'autre'});
const autre404 = await lecteur(['a.b'], 'jour').then(() => null, e => e);
verifie(autre404 && !autre404.attente && autre404.message === 'lecture de /histo impossible (HTTP 404)', 'autre 404 : erreur inchangee', autre404 && autre404.message);

console.log(`\n${nb} verification(s), ${echecs.length} echec(s)`);
console.log(echecs.length ? 'ROUGE : ' + echecs.slice(0, 20).join(' ; ') : 'VERT');
process.exit(echecs.length ? 1 : 0);
