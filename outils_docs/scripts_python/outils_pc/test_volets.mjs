// Banc node des fonctions pures du dessin de la facade des volets (plan visuel-reglage-volets A5).
//
// UTILISATION (depuis la racine du depot ; node ou bun)
//     node outils_docs/scripts_python/outils_pc/test_volets.mjs [--js FICHIER]
// Code de sortie 0 = vert. --js : charge volets.js depuis FICHIER (temoin sur une copie), sinon data/sd/js/volets.js.
//
// Verifie : ouverture (inversion du curseur), ouvertureAngle (comme vrFonctions.be::positionReelle, sans le 100 - p de
// ShutterInvert), avance (extrapolation a la vitesse du volet, bornee, arretee apres 1,5 x rafraichissement : rend alors la
// position recue). Ne teste PAS le dessin ni la boucle (DOM) : sonde Chrome test_volets_chrome.py.
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
verifie(!!V && ['ouverture', 'ouvertureAngle', 'avance', 'dessine', 'demarre'].every(f => typeof V[f] === 'function'), true,
  'window.Volets porte ouverture, ouvertureAngle, avance, dessine, demarre (et rien ne casse sans document)');
if (!V) process.exit(1);

// Curseur -> % d'ouverture
verifie(V.ouverture(30, 0), 30, 'ouverture(30, 0) = 30');
verifie(V.ouverture(30, 1), 70, 'ouverture(30, 1) = 70 (ShutterInvert 1)');
verifie(V.ouverture('30', 1), 70, "ouverture('30', 1) : valeur du curseur en texte");
verifie(V.ouverture(0, 1), 100, 'ouverture(0, 1) = 100 (porte de garage ouverte, curseur a 0)');

// Angle du MPU6050 -> % d'ouverture
const incl = {ouvert: 85, ferme: 3};
verifie(V.ouvertureAngle(44, incl), 50, 'ouvertureAngle(44, {85, 3}) = 50');
verifie(V.ouvertureAngle('44.0', incl), 50, "ouvertureAngle('44.0') : angle lu dans data-angle");
verifie(V.ouvertureAngle(-10, incl), 0, 'ouvertureAngle bornee a 0');
verifie(V.ouvertureAngle(120, incl), 100, 'ouvertureAngle bornee a 100');
verifie(V.ouvertureAngle(44, {ouvert: 3, ferme: 85}), 50, 'ouvertureAngle, montage inverse (ouvert < ferme) : 44 -> 50');
verifie(V.ouvertureAngle(80, {ouvert: 3, ferme: 85}), (80 - 85) * 100 / (3 - 85), 'ouvertureAngle, montage inverse : 80 -> 6,1');
verifie(V.ouvertureAngle('', incl), null, "ouvertureAngle('') = null (capteur muet : retour au curseur)");
verifie(V.ouvertureAngle(44, {ouvert: 3, ferme: 3}), null, 'ouvertureAngle avec ouvert = ferme : null');

// Extrapolation : course de 15 s, rafraichissement 2000 ms (arret apres 3000 ms sans valeur nouvelle)
const o = {tempsMontee: 15, tempsDescente: 15};
const R = 2000;
verifie(V.avance({valeur: 20, t: 1000, sens: 1}, 2500, o, R), 30, 'avance : +10 % en 1,5 s a 15 s de course');
verifie(V.avance({valeur: 95, t: 1000, sens: 1}, 2500, o, R), 100, 'avance : bornee a 100');
verifie(V.avance({valeur: 5, t: 1000, sens: -1}, 2500, o, R), 0, 'avance : bornee a 0');
verifie(V.avance({valeur: 50, t: 1000, sens: -1}, 2500, o, R), 40, 'avance : sens de la derniere variation (fermeture)');
verifie(V.avance({valeur: 50, t: 1000, sens: -1}, 2500, {tempsMontee: 15, tempsDescente: 30}, R), 45,
  'avance : fermeture a la vitesse de tempsDescente');
verifie(V.avance({valeur: 20, t: 1000, sens: 1}, 3999, o, R) > 39.9, true, 'avance : extrapole encore juste avant 1,5 x R');
verifie(V.avance({valeur: 20, t: 1000, sens: 1}, 4001, o, R), 20, 'avance : 1,5 x R sans valeur nouvelle -> position recue');
verifie(V.avance({valeur: 20, t: 1000, sens: 1}, 9000, o, R), 20, 'avance : reste figee sur la position recue');
verifie(V.avance({valeur: 20, t: 1000, sens: 0}, 2500, o, R), 20, 'avance : sens 0 -> immobile');
verifie(V.avance({valeur: 20, t: 1000, sens: 1}, 2500, {tempsMontee: 0, tempsDescente: 0}, R), 20, 'avance : duree 0 -> pas d\'extrapolation');
verifie(V.avance({valeur: 20, t: 1000, sens: 1}, 4001, o), 20 + 100 * 3.001 / 15, 'avance : rafraichissement absent -> 2345 ms (4001 ms < 1,5 x 2345)');
verifie(V.avance({valeur: 20, t: 1000, sens: 1}, 4600, o), 20, 'avance : rafraichissement absent -> arret apres 3517 ms');

// Deux volets independants : le suivi de l'un ne change pas l'autre
const a = {valeur: 10, t: 0, sens: 1}, b = {valeur: 80, t: 0, sens: -1};
const pa = V.avance(a, 1500, o, R), pb = V.avance(b, 1500, {tempsMontee: 30, tempsDescente: 30}, R);
verifie(pa, 20, 'deux volets : le 1er ouvre a sa vitesse');
verifie(pb, 75, 'deux volets : le 2e ferme a la sienne');
verifie(JSON.stringify([a, b]), JSON.stringify([{valeur: 10, t: 0, sens: 1}, {valeur: 80, t: 0, sens: -1}]), 'avance ne modifie pas le suivi');

console.log(echecs.length ? echecs.length + ' echec(s) sur ' + nb + ' verification(s)' : '0 echec(s) sur ' + nb + ' verifications');
process.exit(echecs.length ? 1 : 0);
