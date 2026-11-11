// Banc node des fonctions pures du dessin de la facade des volets (plan visuel-reglage-volets A5).
//
// UTILISATION (depuis la racine du depot ; node ou bun)
//     node outils_docs/scripts_python/outils_pc/test_volets.mjs [--js FICHIER]
// Code de sortie 0 = vert. --js : charge volets.js depuis FICHIER (temoin sur une copie), sinon data/sd/js/volets.js.
//
// Verifie : ouverture (inversion du curseur), ouvertureAngle (comme vrFonctions.be::positionReelle, sans le 100 - p de
// ShutterInvert), poursuit (le dessin rejoint la derniere valeur lue a la vitesse du volet, sans la depasser, borne a
// [0, 100]). Ne teste PAS le dessin ni la boucle (DOM) : sonde Chrome test_volets_chrome.py.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const i = process.argv.indexOf('--js');
const JS = i > 0 ? process.argv[i + 1] : path.join(process.cwd(), 'data/sd/js/volets.js');
const echecs = [];
let nb = 0;
function verifie(obtenu, attendu, libelle) {
  nb++;
  const ok = typeof attendu === 'number' && typeof obtenu === 'number' ? Math.abs(obtenu - attendu) < 1e-9 : obtenu === attendu;
  if (!ok) { echecs.push(libelle); console.log('KO   ' + libelle + '  -> obtenu ' + JSON.stringify(obtenu) + ', attendu ' + JSON.stringify(attendu)); }
}

const fenetre = {};
try {
  vm.runInContext(fs.readFileSync(JS, 'utf8'), vm.createContext({window: fenetre, Math, Number, String, Array, Object}));
} catch (e) {
  console.log('KO   chargement de ' + JS + ' : ' + e.message);
  process.exit(1);
}
const V = fenetre.Volets;
verifie(!!V && ['ouverture', 'ouvertureAngle', 'poursuit', 'dessine', 'demarre'].every(f => typeof V[f] === 'function'), true,
  'window.Volets porte ouverture, ouvertureAngle, poursuit, dessine, demarre (et rien ne casse sans document)');
if (echecs.length) process.exit(1);      // API absente : rien d'autre a verifier

// Curseur -> % d'ouverture
verifie(V.ouverture(30, 0), 30, 'ouverture(30, 0) = 30');
verifie(V.ouverture(30, 1), 70, 'ouverture(30, 1) = 70 (ShutterInvert 1)');
verifie(V.ouverture('30', 1), 70, "ouverture('30', 1) : valeur du curseur en texte");
verifie(V.ouverture(0, 1), 100, 'ouverture(0, 1) = 100 (porte de garage ouverte, curseur a 0)');

// Angle du MPU6050 -> % d'ouverture
const incl = {ouvert: 85, ferme: 3};
verifie(V.ouvertureAngle(44, incl), 50, 'ouvertureAngle(44, {85, 3}) = 50');
verifie(V.ouvertureAngle('44.0', incl), 50, "ouvertureAngle('44.0') : angle lu dans data-angle");
verifie(V.ouvertureAngle('47,0', incl), (47 - 3) * 100 / 82, "ouvertureAngle('47,0') : virgule de web_send_decimal (firmware fr_FR)");
verifie(V.ouvertureAngle(-10, incl), 0, 'ouvertureAngle bornee a 0');
verifie(V.ouvertureAngle(120, incl), 100, 'ouvertureAngle bornee a 100');
verifie(V.ouvertureAngle(44, {ouvert: 3, ferme: 85}), 50, 'ouvertureAngle, montage inverse (ouvert < ferme) : 44 -> 50');
verifie(V.ouvertureAngle(80, {ouvert: 3, ferme: 85}), (80 - 85) * 100 / (3 - 85), 'ouvertureAngle, montage inverse : 80 -> 6,1');
verifie(V.ouvertureAngle('', incl), null, "ouvertureAngle('') = null (capteur muet : retour au curseur)");
verifie(V.ouvertureAngle(44, {ouvert: 3, ferme: 3}), null, 'ouvertureAngle avec ouvert = ferme : null');

// Poursuite : le dessin rejoint la derniere valeur lue a la vitesse du volet, sans la depasser
const o = {tempsMontee: 15, tempsDescente: 15};
verifie(V.poursuit(20, 80, 1500, o), 30, 'poursuit : +10 % en 1,5 s a 15 s de course');
verifie(V.poursuit(20, 25, 1500, o), 25, 'poursuit : rejoint la cible sans la depasser (montee)');
verifie(V.poursuit(50, 48, 1500, o), 48, 'poursuit : rejoint la cible sans la depasser (descente)');
verifie(V.poursuit(50, 0, 1500, o), 40, 'poursuit : -10 % en 1,5 s en descente');
verifie(V.poursuit(50, 0, 1500, {tempsMontee: 15, tempsDescente: 30}), 45, 'poursuit : descente a la vitesse de tempsDescente');
verifie(V.poursuit(50, 100, 1500, {tempsMontee: 30, tempsDescente: 15}), 55, 'poursuit : montee a la vitesse de tempsMontee');
verifie(V.poursuit(30, 30, 1500, o), 30, 'poursuit : cible atteinte -> immobile');
verifie(V.poursuit(30, 30, 0, o), 30, 'poursuit : dt 0 -> immobile');
verifie(V.poursuit(30, 80, 0, o), 30, 'poursuit : dt 0 -> pas de saut');
verifie(V.poursuit(null, 64, 16, o), 64, 'poursuit : premiere lecture -> la cible directement');
verifie(V.poursuit(undefined, 64, 16, o), 64, 'poursuit : dessin non initialise -> la cible directement');
verifie(V.poursuit(20, 80, 1500, {tempsMontee: 0, tempsDescente: 0}), 80, 'poursuit : duree 0 -> la cible directement');
verifie(V.poursuit(20, 150, 99999, o), 100, 'poursuit : bornee a 100');
verifie(V.poursuit(20, -50, 99999, o), 0, 'poursuit : bornee a 0');
let p = 0;
for (let k = 0; k < 600; k++) p = V.poursuit(p, 37, 16, o);      // 600 images de 16 ms : 9,6 s, plus que les 5,6 s du trajet
verifie(p, 37, 'poursuit image par image : arrive sur la cible et y reste (jamais au-dela)');
let q = 0, max = 0;
for (let k = 0; k < 100; k++) { q = V.poursuit(q, 37, 16, o); max = Math.max(max, q); }
verifie(max <= 37, true, 'poursuit image par image : jamais au-dela de la cible pendant le trajet');

// Deux volets independants : chacun a sa vitesse
verifie(V.poursuit(10, 100, 1500, o), 20, 'deux volets : le 1er ouvre a sa vitesse');
verifie(V.poursuit(80, 0, 1500, {tempsMontee: 30, tempsDescente: 30}), 75, 'deux volets : le 2e ferme a la sienne');

console.log(echecs.length ? echecs.length + ' echec(s) sur ' + nb + ' verification(s)' : '0 echec(s) sur ' + nb + ' verifications');
process.exit(echecs.length ? 1 : 0);
