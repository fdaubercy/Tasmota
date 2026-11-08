// Banc node de la validation de la page /energie (plan energie-atelier A3).
//
// UTILISATION (depuis la racine du depot ; node ou bun, PYTHON = l'interpreteur Python si `python` n'est pas dans le PATH)
//     node outils_docs/scripts_python/outils_pc/test_energie_rendu.mjs [--js FICHIER]      (ou : bun <meme chemin>)
// Code de sortie 0 = vert. --js : charge energie.js depuis FICHIER (temoin sur une copie), sinon data/sd/js/energie.js.
//
// Verifie : Energie.valide rend, sur CHAQUE cas de cas_energie.json, le meme verdict que le validateur Python (liste vide si
// le motif est vide, sinon non vide et contenant le motif) ; Energie.DEFAUT = le DEFAUT de atelier_energie_description.py (exporte par Python) ; bornes 4096/4097 octets.
// Ne teste PAS trace() : pas de DOM ici, elle est jugee par la sonde Chrome (berry/banc_energie.py).
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {spawnSync} from 'node:child_process';

const RACINE = process.cwd();
const i = process.argv.indexOf('--js');
const JS = i > 0 ? process.argv[i + 1] : path.join(RACINE, 'data/sd/js/energie.js');
const CAS = JSON.parse(fs.readFileSync(path.join(RACINE, 'outils_docs/scripts_python/outils_pc/cas_energie.json'), 'utf8'));
const echecs = [];
let nb = 0;
function verifie(ok, libelle, detail) {
  nb++;
  if (!ok) echecs.push(libelle);
  if (!ok) console.log('KO   ' + libelle + (detail === undefined ? '' : '  -> ' + JSON.stringify(detail)));
}

const fenetre = {};
vm.runInContext(fs.readFileSync(JS, 'utf8'), vm.createContext({window: fenetre, TextEncoder, JSON, Math, Array, Object, Number, String}));
const E = fenetre.Energie;
verifie(!!E && typeof E.valide === 'function', 'window.Energie.valide existe');
if (E && E.valide) {
  for (const c of CAS) {
    const m = E.valide(JSON.parse(JSON.stringify(c.description)));
    const ok = c.motif === '' ? m.length === 0 : m.length > 0 && m.some(x => x.includes(c.motif));
    verifie(ok, 'cas « ' + c.nom + ' »', {motif: c.motif, obtenu: m});
  }
  verifie(E.valide(E.DEFAUT).length === 0, 'DEFAUT est valide');

  const pyDefaut = spawnSync(process.env.PYTHON || 'python', ['-c', `import json,sys
sys.path.insert(0, 'outils_docs/scripts_python/outils_pc')
from atelier_energie_description import DEFAUT
print(json.dumps(DEFAUT, ensure_ascii=False))`], {encoding: 'utf8', env: {...process.env, PYTHONIOENCODING: 'utf-8'}});
  let defautPy = null;
  try { defautPy = JSON.parse(pyDefaut.stdout); } catch (e) { /* signale ci-dessous */ }
  verifie(defautPy !== null && deepEgal(E.DEFAUT, defautPy), 'DEFAUT = DEFAUT de atelier_energie_description.py', pyDefaut.stderr);
  // Borne des octets : 4 096 acceptes, 4 097 refuses, comptes en octets UTF-8 (titres accentues = 2 octets le caractere), verdict de Python en oracle.
  const octets = d => new TextEncoder().encode(JSON.stringify(d)).length;
  const fabrique = cible => {      // 16 jauges aux titres de 40 caracteres, dont n accentues (2 octets) : chaque octet en plus est un accent de plus
    const d = {version: 1, elements: []};
    for (let k = 0; k < 16; k++) d.elements.push({type: 'demi-cercle', titre: 'a'.repeat(40), source: {direct: 'ReactivePower'}, unite: 'WWWWWWWWWW',
      couleur: '#4a9eda', largeur: 'pleine', hauteur: 'moyenne', min: -1234567890123456, max: 1234567890123456});
    let reste = cible - octets(d);
    for (const e of d.elements) { const n = Math.max(0, Math.min(40, reste)); e.titre = 'é'.repeat(n) + 'a'.repeat(40 - n); reste -= n; }
    return d;
  };
  const bornes = [4096, 4097].map(fabrique);
  verifie(bornes.map(octets).join() === '4096,4097', 'descriptions de 4096 et 4097 octets construites', bornes.map(octets));
  const py = spawnSync(process.env.PYTHON || 'python', ['-c', `import json,sys
sys.path.insert(0, 'outils_docs/scripts_python/outils_pc')
from atelier_energie_description import valide
print(json.dumps([valide(d) for d in json.load(sys.stdin)]))`], {input: JSON.stringify(bornes), encoding: 'utf8', env: {...process.env, PYTHONIOENCODING: 'utf-8'}});
  let oracle = null;
  try { oracle = JSON.parse(py.stdout); } catch (e) { /* signale ci-dessous */ }
  verifie(Array.isArray(oracle) && oracle.length === 2, 'reference Python lancee (valide)', py.stderr);
  if (Array.isArray(oracle)) {
    const js = bornes.map(d => E.valide(d));
    verifie(oracle[0].length === 0 && js[0].length === 0, '4096 octets : valide (Python et JS)', {python: oracle[0], js: js[0]});
    verifie(oracle[1].length > 0 && js[1].length > 0 && js[1].some(x => x.includes('taille')), '4097 octets : refuse pour la taille (Python et JS)', {python: oracle[1], js: js[1]});
  }
}
function deepEgal(a, b) {
  if (a === b) return true;
  if (typeof a !== 'object' || typeof b !== 'object' || a === null || b === null || Array.isArray(a) !== Array.isArray(b)) return false;
  const ka = Object.keys(a), kb = Object.keys(b);
  return ka.length === kb.length && ka.every(k => deepEgal(a[k], b[k]));
}
console.log(echecs.length ? echecs.length + ' echec(s) sur ' + nb + ' verification(s)' : '0 echec(s) sur ' + nb + ' verifications');
process.exit(echecs.length ? 1 : 0);
