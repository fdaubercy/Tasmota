// Banc node des fonctions pures du dessin de la facade des volets (plan visuel-reglage-volets A5).
//
// UTILISATION (depuis la racine du depot ; node ou bun)
//     node outils_docs/scripts_python/outils_pc/test_volets.mjs [--js FICHIER]
// Code de sortie 0 = vert. --js : charge volets.js depuis FICHIER (temoin sur une copie), sinon data/sd/js/volets.js.
//
// Verifie : ouverture (inversion du curseur), ouvertureAngle (comme vrFonctions.be::positionReelle, sans le 100 - p de
// ShutterInvert), poursuit (le dessin rejoint la derniere valeur lue a la vitesse du volet, sans la depasser, borne a
// [0, 100]). Depuis la facade du garage (2026-11-13, plan facade-garage-capteurs A1) : dessin sur un DOM minimal (decor seulement
// s'il est declare, dessin SANS decor inchange : empreintes relevees sur le volets.js d'avant), pastilles des fins de course
// (couleurs, titres, levier), coherence (position lue contre contacts, delai de 6 s), clignotement, choix de la source des
// etats (reponse de la source de l'ouverture, sinon /volets?f=capteurs). La boucle et le rendu reel : sonde Chrome test_volets_chrome.py.
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const i = process.argv.indexOf('--js');
const JS = i > 0 ? process.argv[i + 1] : path.join(process.cwd(), 'data/sd/js/volets.js');
const echecs = [];
let nb = 0;
function verifie(obtenu, attendu, libelle) {
  nb++;
  const ok = typeof attendu === 'number' && typeof obtenu === 'number' ? Math.abs(obtenu - attendu) < 1e-9 : JSON.stringify(obtenu) === JSON.stringify(attendu);
  if (!ok) { echecs.push(libelle); console.log('KO   ' + libelle + '  -> obtenu ' + JSON.stringify(obtenu) + ', attendu ' + JSON.stringify(attendu)); }
}

// DOM minimal : de quoi laisser dessine() construire son arbre, que l'on serialise pour le comparer
function noeud(nom) {
  return {nom, attrs: {}, enfants: [], style: {}, textContent: '',
    get firstChild() { return this.enfants[0] || null; },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    appendChild(e) { this.enfants.push(e); return e; },
    removeChild(e) { this.enfants.splice(this.enfants.indexOf(e), 1); return e; }};
}
const DOCUMENT = {createElementNS: (ns, nom) => noeud(nom)};
function serialise(n) { return {n: n.nom, a: n.attrs, s: n.style, t: n.textContent, c: n.enfants.map(serialise)}; }
function empreinte(n) { return crypto.createHash('sha1').update(JSON.stringify(serialise(n))).digest('hex').slice(0, 12); }
function tous(n, f, r = []) { if (f(n)) r.push(n); n.enfants.forEach(e => tous(e, f, r)); return r; }
const fenetre = {};
try {
  vm.runInContext(fs.readFileSync(JS, 'utf8'), vm.createContext({window: fenetre, document: DOCUMENT, Math, Number, String, Array, Object}));
} catch (e) {
  console.log('KO   chargement de ' + JS + ' : ' + e.message);
  process.exit(1);
}
const V = fenetre.Volets;
verifie(!!V && ['ouverture', 'ouvertureAngle', 'poursuit', 'dessine', 'demarre', 'coherence', 'poseCapteurs', 'clignote', 'etatsCapteurs'].every(f => typeof V[f] === 'function'), true,
  'window.Volets porte ouverture, ouvertureAngle, poursuit, dessine, demarre, coherence, poseCapteurs, clignote, etatsCapteurs');
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

// Dessin SANS decor : strictement celui d'avant (empreinte de l'arbre complet, relevee sur le volets.js du 2026-11-12)
const O = (id, type, extra) => Object.assign({id, nom: 'Volet ' + type, type, place: id, inverse: 0, tempsMontee: 5, tempsDescente: 5, inclinaison: null}, extra);
const dessin = (facade) => { const c = noeud('div'); const svg = V.dessine(c, facade); return [c, svg]; };
const FACADES = {
  rdc: {toit: 'deuxPans', ouvertures: [O(2, 'fenetre'), O(3, 'trappe'), O(1, 'porte')]},
  garage: {toit: 'unPan', ouvertures: [O(1, 'garage')]},
  etage2: {toit: 'aucun', ouvertures: [O(1, 'trappeEchelle')]},
};
const EMPREINTES = {rdc: '79a5feeabb64', garage: 'b972a74b0aa6', etage2: '3cab6f241cb6'};
for (const k of Object.keys(FACADES)) verifie(empreinte(dessin(FACADES[k])[0]), EMPREINTES[k], 'dessin ' + k + " sans decor : identique a celui d'avant");
verifie(empreinte(dessin(Object.assign({}, FACADES.garage, {decor: null}))[0]), EMPREINTES.garage, 'decor null (cle absente du persist) : dessin inchange');
verifie(empreinte(dessin(Object.assign({}, FACADES.garage, {decor: []}))[0]), EMPREINTES.garage, 'decor vide : dessin inchange');
verifie(dessin(FACADES.garage)[1].volets[0].capteurs, undefined, 'sans finsDeCourse : aucune pastille');

// Decor : pose seulement ce qui est declare, deterministe
const DECOR = ['chevrefeuille', 'porte', 'pergola'];
const AVEC = Object.assign({}, FACADES.garage, {decor: DECOR});
const [cd, sd] = dessin(AVEC);
const decors = (c) => tous(c, n => 'data-decor' in n.attrs).map(n => n.attrs['data-decor']);
verifie(decors(cd), DECOR, 'decor : chevrefeuille, porte et pergola poses (data-decor)');
verifie(sd.attrs.viewBox, '0 0 420 200', 'decor : dessin elargi (viewBox 420 x 200)');
verifie(tous(cd, n => n.nom === 'rect' && n.attrs.x === '70' && n.attrs.y === '94' && n.attrs.width === '176').length, 1, 'decor : rideau a x = 70 (maquette)');
verifie(tous(cd, n => n.nom === 'polygon' && n.attrs.points === '20,44 336,' + (44 + 16 * 316 / 380) + ' 336,196 20,196').length, 1, 'decor : mur arrete a 336, avant la pergola');
verifie(tous(cd, n => n.attrs['data-decor'] === 'chevrefeuille')[0].enfants.length > 100, true, 'decor : chevrefeuille garni de feuilles');
verifie(empreinte(dessin(AVEC)[0]), empreinte(cd), "decor : dessin identique d'un appel a l'autre (hasard a graine fixe)");
verifie(decors(dessin(Object.assign({}, FACADES.garage, {decor: ['porte']}))[0]), ['porte'], 'decor : seul « porte » declare -> seule la porte est posee');
verifie(decors(dessin(Object.assign({}, FACADES.rdc, {decor: DECOR}))[0]), [], 'decor : ignore hors toit unPan (greniers inchanges)');

// Pastilles des fins de course
const FINS = Object.assign({}, FACADES.garage, {decor: DECOR, ouvertures: [O(1, 'garage', {finsDeCourse: {ouverture: 'Capteur Ouverture Rideau Garage', fermeture: null}})]});
const [cf, sf] = dessin(FINS);
const v = sf.volets[0], cap = v.capteurs;
verifie(!!cap && !!cap.ouverture && !!cap.fermeture, true, 'finsDeCourse : deux pastilles (ouverture, fermeture)');
verifie(tous(cf, n => 'data-capteur' in n.attrs).map(n => n.attrs['data-capteur']), ['ouverture', 'fermeture'], 'finsDeCourse : data-capteur ouverture puis fermeture (haut puis bas)');
const y = n => Number(n.attrs.y);
verifie(y(cap.ouverture.boitier) < y(cap.fermeture.boitier), true, "finsDeCourse : capteur d'ouverture en haut, fermeture en bas");
verifie(Number(cap.ouverture.boitier.attrs.x) > 70 + 176, true, 'finsDeCourse : sur le rail droit du rideau');
V.poseCapteurs(v, {ouverture: 'ON', fermeture: 'OFF'});
verifie([cap.ouverture.boitier.style.fill, cap.fermeture.boitier.style.fill], ['#3cb04a', '#e0453a'], 'pastilles : ON = vert #3cb04a, OFF = rouge #e0453a');
verifie([cap.ouverture.titre.textContent, cap.fermeture.titre.textContent], ['Capteur Ouverture Rideau Garage : contact fermé', 'Capteur fermeture : contact ouvert'],
  "pastilles : titre « nom : contact fermé|ouvert » (nom par defaut si l'interrupteur est introuvable)");
verifie([cap.ouverture.levier.style.transform, cap.fermeture.levier.style.transform], ['rotate(0deg)', 'rotate(35deg)'], 'pastilles : levier plaque si contact ferme, ecarte de 35 degres si ouvert');
V.poseCapteurs(v, {ouverture: 'OFF'});
verifie([cap.ouverture.boitier.style.fill, cap.fermeture.boitier.style.fill, cap.fermeture.titre.textContent],
  ['#e0453a', '#8a8f94', 'Capteur fermeture : contact inconnu'], 'pastilles : etat absent -> gris, « contact inconnu »');
V.poseCapteurs(v, null);
verifie([cap.ouverture.boitier.style.fill, cap.ouverture.titre.textContent], ['#8a8f94', 'Capteur Ouverture Rideau Garage : contact inconnu'], 'pastilles : lecture en echec (null) -> gris');
V.poseCapteurs(v, {ouverture: 'ON', fermeture: 'ON'});
V.poseCapteurs(v, {ouverture: 'ON', fermeture: 'ON'});
verifie(cap.ouverture.boitier.style.fill, '#3cb04a', 'pastilles : poser deux fois le meme etat est sans effet');

// Source des etats : reponse de la source de l'ouverture (carte du rideau) si elle porte « capteurs », sinon /volets?f=capteurs (P4)
const vs = {o: {id: 1, source: '/rideau?f=position&id=1'}, lu: {ouverture: 10, muet: false, capteurs: {ouverture: 'ON', fermeture: 'OFF'}}};
verifie(V.etatsCapteurs(vs, {j: {1: {ouverture: 'OFF'}}}), {ouverture: 'ON', fermeture: 'OFF'}, 'etats : source avec capteurs -> ceux de la source');
vs.lu = {ouverture: 10, muet: false};
verifie(V.etatsCapteurs(vs, null), null, 'etats : source sans capteurs ni lecture du P4 -> null (gris)');
verifie(V.etatsCapteurs({o: {id: 1}}, {j: {1: {ouverture: 'OFF'}}}), {ouverture: 'OFF'}, 'etats : sans source -> lecture /volets?f=capteurs, par id du volet');
verifie(V.etatsCapteurs({o: {id: 2}}, {j: {1: {ouverture: 'OFF'}}}), {}, 'etats : volet absent de la reponse -> {} (inconnu)');
verifie(V.etatsCapteurs({o: {id: 1}}, {j: null}), null, 'etats : lecture en echec -> null');
verifie(V.etatsCapteurs({o: {id: 1}}, undefined), null, 'etats : rien lu encore -> null');

// Coherence : la position LUE (pas la dessinee) contre les contacts, plus de 6 s ; les deux contacts fermes = incoherent
const nu = {ouverture: false, fermeture: false};
let suivi = {};
verifie(V.coherence(suivi, 100, {ouverture: 'OFF', fermeture: 'OFF'}, 0), nu, "coherence : ouvert a 100 % et capteur d'ouverture OFF : pas encore (0 s)");
verifie(V.coherence(suivi, 100, {ouverture: 'OFF', fermeture: 'OFF'}, 6000), nu, 'coherence : exactement 6 s : pas encore');
verifie(V.coherence(suivi, 100, {ouverture: 'OFF', fermeture: 'OFF'}, 6001), {ouverture: true, fermeture: false}, "coherence : plus de 6 s, ouvert a 100 % sans contact d'ouverture : l'ouverture clignote");
verifie(V.coherence(suivi, 99, {ouverture: 'OFF', fermeture: 'OFF'}, 7000), {ouverture: true, fermeture: false}, 'coherence : 99 % compte deja pour ouvert');
verifie(V.coherence(suivi, 100, {ouverture: 'ON', fermeture: 'OFF'}, 7100), nu, "coherence : contact d'ouverture ON : coherent, plus de clignotement");
verifie(V.coherence(suivi, 100, {ouverture: 'OFF', fermeture: 'OFF'}, 7200), nu, 'coherence : le delai repart de zero apres une periode coherente');
suivi = {};
V.coherence(suivi, 0, {ouverture: 'OFF', fermeture: 'OFF'}, 0);
verifie(V.coherence(suivi, 0, {ouverture: 'OFF', fermeture: 'OFF'}, 6500), {ouverture: false, fermeture: true}, 'coherence : ferme a 0 % sans contact de fermeture : la fermeture clignote');
verifie(V.coherence(suivi, 1, {ouverture: 'OFF', fermeture: 'OFF'}, 9000), {ouverture: false, fermeture: true}, 'coherence : 1 % compte encore pour ferme');
verifie(V.coherence(suivi, 50, {ouverture: 'OFF', fermeture: 'OFF'}, 9100), nu, 'coherence : a mi-course, deux contacts ouverts : coherent');
suivi = {};
V.coherence(suivi, 50, {ouverture: 'ON', fermeture: 'ON'}, 0);
verifie(V.coherence(suivi, 50, {ouverture: 'ON', fermeture: 'ON'}, 6001), {ouverture: true, fermeture: true}, 'coherence : les deux contacts fermes plus de 6 s : les deux clignotent');
suivi = {};
V.coherence(suivi, 100, {}, 0);
verifie(V.coherence(suivi, 100, {}, 9000), nu, 'coherence : contacts inconnus (lecture en echec) : aucun verdict, pas de clignotement');
verifie(V.coherence(suivi, 100, null, 9500), nu, 'coherence : lecture nulle : aucun verdict');
verifie(V.coherence({}, null, {ouverture: 'OFF', fermeture: 'OFF'}, 9500), nu, 'coherence : position inconnue : aucun verdict');

// Clignotement : opacite alternee a ~2 Hz
const c2 = dessin(FINS)[1].volets[0];
V.clignote(c2, {ouverture: true, fermeture: false}, 0);
const o0 = c2.capteurs.ouverture.g.style.opacity;
V.clignote(c2, {ouverture: true, fermeture: false}, 250);
const o1 = c2.capteurs.ouverture.g.style.opacity;
V.clignote(c2, {ouverture: true, fermeture: false}, 500);
verifie([o0 !== o1, c2.capteurs.ouverture.g.style.opacity === o0, !c2.capteurs.fermeture.g.style.opacity], [true, true, true],
  "clignote : opacite alternee toutes les 250 ms (2 Hz), l'autre pastille intacte");
V.clignote(c2, {ouverture: false, fermeture: false}, 750);
verifie(c2.capteurs.ouverture.g.style.opacity, '', 'clignote : verdict leve -> opacite normale');

// Maison du RDC (decor 'maison', 2026-11-13) : dessin, places des ouvertures, porte blanche, rapporteur de la trappe, camera
const MAISON = Object.assign({}, FACADES.rdc, {decor: ['maison'], camera: {nom: 'Caméra de façade', id: 7}});
const [cm, sm] = dessin(MAISON);
verifie(sm.attrs.viewBox, '0 0 400 214', 'maison : viewBox 400 x 214 (marches sous la porte)');
verifie(decors(cm), ['maison'], 'maison : toit de la maison pose (data-decor maison), aucun decor du garage');
verifie(tous(cm, n => n.nom === 'pattern').map(n => n.attrs.id).filter(i => i === 'vf_brique' || i === 'vf_soldat'), ['vf_brique', 'vf_soldat'], 'maison : motifs briques et briques de champ');
const premierRect = id => tous(cm, n => n.attrs['data-id'] === String(id))[0].enfants.find(n => n.nom === 'rect');
verifie([premierRect(2).attrs.x, premierRect(3).attrs.x, premierRect(1).attrs.x], ['100', '194', '284'], 'maison : fenetre a 100, trappe a 194, porte a 284 (maquette)');
verifie(premierRect(1).attrs.fill, '#f4f4f2', "maison : porte d'entree blanche");
verifie(tous(cm, n => n.attrs.fill === '#c2902e').length, 1, 'maison : grand vitrage ocre de la porte');
verifie(tous(cm, n => n.nom === 'text' && n.textContent === '45').length, 1, 'maison : numero 45');
verifie(empreinte(dessin(MAISON)[0]), empreinte(cm), "maison : dessin identique d'un appel a l'autre");
verifie(empreinte(dessin(Object.assign({}, FACADES.rdc, {decor: null}))[0]), EMPREINTES.rdc, 'maison : decor null -> dessin du RDC inchange');
verifie(sm.volets.map(v => !!v.rapporteur), [false, true, false], 'maison : rapporteur sur la trappe seulement');
verifie(dessin(FACADES.rdc)[1].volets.some(v => v.rapporteur), false, 'sans decor maison : aucun rapporteur');
const rp = sm.volets[1].rapporteur;
verifie([rp.texte.textContent, rp.aiguille.style.display], ['?°', 'none'], "rapporteur : sans balise d'angle, « ?° », aiguille cachee");
V.poseAngle(rp, '47,0');
const deg = a => [rp.cx + rp.r * Math.cos(a * Math.PI / 180), rp.cy + rp.r * Math.sin(a * Math.PI / 180)].map(String);
verifie([rp.texte.textContent, rp.aiguille.style.display, rp.aiguille.attrs.x2, rp.aiguille.attrs.y2], ['47°', ''].concat(deg(47)),
  'rapporteur : angle 47,0 (virgule du firmware) -> « 47° », aiguille a 47 degres sous l\'horizontale');
V.poseAngle(rp, '3.4');
verifie([rp.texte.textContent].concat([rp.aiguille.attrs.x2, rp.aiguille.attrs.y2]), ['3°'].concat(deg(3.4)), 'rapporteur : 3,4 -> « 3° »');
V.poseAngle(rp, '120');
verifie([rp.texte.textContent, rp.aiguille.attrs.x2, rp.aiguille.attrs.y2], ['120°'].concat(deg(90)), 'rapporteur : au-dela de 90, aiguille bornee a la verticale');
V.poseAngle(rp, '');
verifie([rp.texte.textContent, rp.aiguille.style.display], ['?°', 'none'], 'rapporteur : angle vide -> « ?° »');
const cam = sm.camera;
verifie(!!cam && tous(cm, n => 'data-camera' in n.attrs).length === 1, true, 'camera declaree : dessinee (data-camera)');
verifie(dessin(Object.assign({}, MAISON, {camera: null}))[1].camera, undefined, 'camera absente du persist : pas de camera');
verifie(dessin(Object.assign({}, FACADES.rdc, {camera: {nom: 'x', id: 7}}))[1].camera, undefined, 'camera sans decor maison : pas de camera');
verifie([cam.voyant.style.fill, cam.halo.style.display, cam.titre.textContent], ['#777', 'none', 'Caméra de façade : état inconnu (clic pour allumer)'], 'camera : etat inconnu au depart, gris');
V.poseCamera(cam, 'ON');
verifie([cam.voyant.style.fill, cam.halo.style.display, cam.titre.textContent], ['#3cb04a', '', 'Caméra de façade : allumée (clic pour éteindre)'], 'camera ON : voyant vert, halo, titre');
V.poseCamera(cam, 'OFF');
verifie([cam.voyant.style.fill, cam.halo.style.display, cam.titre.textContent], ['#777', 'none', 'Caméra de façade : éteinte (clic pour allumer)'], 'camera OFF : voyant gris, sans halo');
verifie(typeof cam.g.onclick, 'function', 'camera : clic branche');

// Projecteur du garage (2026-11-14) : lanterne sous le toit cote pergola, voyant jaune, clic branche
const GL = Object.assign({}, FACADES.garage, {decor: ['chevrefeuille', 'porte', 'pergola'], lampe: {nom: 'Projecteur de Garage', id: 5}});
const [cl, sl] = dessin(GL);
verifie(!!sl.lampe && tous(cl, n => 'data-lampe' in n.attrs).length === 1, true, 'lampe declaree (garage) : dessinee (data-lampe)');
verifie(dessin(Object.assign({}, GL, {lampe: null}))[1].lampe, undefined, 'lampe absente du persist : pas de lampe');
verifie(dessin(Object.assign({}, GL, {toit: 'deuxPans'}))[1].lampe, undefined, 'lampe sans toit unPan : pas de lampe');
verifie([sl.lampe.globe.style.fill, sl.lampe.halo.style.display], ['#a9adb0', 'none'], 'lampe : etat inconnu au depart, gris');
V.poseLampe(sl.lampe, 'ON');
verifie([sl.lampe.globe.style.fill, sl.lampe.halo.style.display, sl.lampe.titre.textContent], ['#ffd54a', '', 'Projecteur de Garage : allumé (clic pour éteindre)'], 'lampe ON : globe jaune, halo, titre');
V.poseLampe(sl.lampe, 'OFF');
verifie([sl.lampe.globe.style.fill, sl.lampe.halo.style.display], ['#a9adb0', 'none'], 'lampe OFF : globe gris, sans halo');
verifie(typeof sl.lampe.g.onclick, 'function', 'lampe : clic branche');

console.log(echecs.length ? echecs.length + ' echec(s) sur ' + nb + ' verification(s)' : '0 echec(s) sur ' + nb + ' verifications');
process.exit(echecs.length ? 1 : 0);
