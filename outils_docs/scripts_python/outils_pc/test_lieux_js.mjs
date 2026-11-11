// Banc des fonctions JS communes de lieux.JS (sans DOM). Code de sortie 0 = vert.
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

const ici = dirname(fileURLToPath(import.meta.url));
const py = process.env.PYTHON || 'python';
const JS = execFileSync(py, ['-c', 'import lieux; print(lieux.JS)'], { cwd: ici, encoding: 'utf8', env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });
let echecs = 0;
const verifie = (obtenu, attendu, libelle) => {
  if (obtenu !== attendu) { echecs++; console.log(`ECHEC ${libelle} : obtenu ${obtenu}, attendu ${attendu}`); }
};
const charge = (search) => new Function('location', JS + '; return {lieuDeHote, lieuDeTopic, lieuDemande};')({ search });
const f = charge('');
const cartes = [
  { env: 'g', lieu: 'etage2', hote: 'GRENIER', topic: 'grenier', ip: '192.168.0.60' },
  { env: 'p4', lieu: 'garage', hote: 'MAITRE-GARAGE', topic: 'garage', ip: '192.168.0.50' },
  { env: 's3', lieu: 'garage', hote: 'NIVEAU-GARAGE', topic: 'garage/niveau', ip: '192.168.0.52' },
  { env: 'cuve', lieu: 'garage', hote: 'CAPTEURS-CUVE', topic: 'jardin/cuve', ip: '' },
  { env: 'rideau', lieu: 'garage', hote: 'RIDEAU-GARAGE', topic: 'garage/rideau', ip: '' },
  { env: 'porte', lieu: 'rdc', hote: '', topic: '', ip: '192.168.0.46' },
];
verifie(f.lieuDeHote('capteurs-cuve', '', cartes), 'garage', 'casse differente');
verifie(f.lieuDeHote('RIDEAU-GARAGE', '192.168.0.50', cartes), 'garage', 'esclave NAPT : nom avant IP');
verifie(f.lieuDeHote('INCONNU', '192.168.0.46', cartes), 'rdc', 'hote inconnu : IP');
verifie(f.lieuDeHote('INCONNU', '', cartes), null, 'hote inconnu sans IP');
verifie(f.lieuDeHote('', '', cartes), null, 'hote vide ne prend pas la carte sans hote');
verifie(f.lieuDeTopic('tele/garage/niveau/STATE', cartes), 'garage', 'topic le plus long (niveau)');
verifie(f.lieuDeTopic('tele/garagex/STATE', cartes), null, 'prefixe sans /');
verifie(f.lieuDeTopic('stat/jardin/cuve/RESULT', cartes), 'garage', 'cuve');
verifie(f.lieuDeTopic('tele/grenier/STATE', cartes), 'etage2', 'grenier');
verifie(f.lieuDeTopic('garage/rideau', cartes, true), 'garage', 'topic nu');
verifie(f.lieuDeTopic('zigbee2mqtt/bridge/state', cartes), null, 'topic etranger');
const lieux = [['cave', 'Cave'], ['garage', 'Garage']];
verifie(charge('?lieu=cave').lieuDemande(lieux), 'cave', 'lieu demande');
verifie(charge('?lieu=inconnu').lieuDemande(lieux), null, 'lieu inconnu');
verifie(charge('?lieu=%3Cb%3Ex').lieuDemande(lieux), null, 'lieu balise');
verifie(charge('').lieuDemande(lieux), null, 'sans parametre');
// bandeauLieu avec un faux DOM : texte en textContent, fermeture = retire ?lieu, le bandeau, appelle surFermeture
{
  const el = () => ({ children: [], firstChild: null, remove() { this.retire = true; }, appendChild(c) { this.children.push(c); return c; } });
  const remplace = [];
  const parent = { firstChild: null, insertBefore(n) { this.insere = n; } };
  const loc = { search: '?lieu=cave&x=1', href: 'http://h/page?lieu=cave&x=1#a' };
  const doc = { createElement: () => el(), createTextNode: (t) => ({ t }) };
  const h = { replaceState: (a, b, u) => remplace.push(u) };
  const g = new Function('location', 'document', 'history', 'URL', JS + '; return bandeauLieu;')(loc, doc, h, URL);
  let ferme = 0;
  const b = g(parent, 'Cave', () => ferme++);
  verifie(parent.insere, b, 'bandeau insere en tete');
  verifie(b.className, 'bandeau-lieu', 'classe du bandeau');
  verifie(b.children[0].t.indexOf('Cave') > 0, true, 'libelle dans le texte');
  b.children[1].onclick();
  verifie(remplace[0], '/page?x=1#a', 'lieu retire de l\'adresse');
  verifie(b.retire, true, 'bandeau retire');
  verifie(ferme, 1, 'surFermeture appele');
}
// libelleLieu
{
  const L = [['cave', 'Cave'], ['garage', 'Garage']];
  const g = charge('');
  const lib = new Function(JS + '; return libelleLieu;')();
  verifie(lib(L, 'cave'), 'Cave', 'libelle connu');
  verifie(lib(L, 'jardin'), 'jardin', 'libelle : code inconnu = le code');
  verifie(lib(L, 'autres'), 'Autres', 'libelle : autres');
  verifie(lib(L, ''), 'Autres', 'libelle : vide');
  verifie(lib(L, null), 'Autres', 'libelle : null');
}
// pucesLieu avec un faux DOM : comptes par cle, jamais decrementes, recalcules d'apres les cles, efface remet a zero
{
  const el = () => { const e = { children: [], dataset: {}, textContent: '', classes: new Set(),
    classList: { toggle(c, v) { v ? e.classes.add(c) : e.classes.delete(c); } },
    append(...x) { x.forEach(c => e.children.push(c)); }, appendChild(c) { e.children.push(c); return c; },
    replaceChildren(...x) { e.children = x; } }; return e; };
  const doc = { createElement: () => el() };
  const f = new Function('document', 'location', JS + '; return {pucesLieu, lieuDeHote};')(doc, { search: '' });
  const cont = el();
  let redessins = 0;
  const P = f.pucesLieu(cont, { erreurs: true, surChoix: () => redessins++ });
  const cartes = [{ lieu: 'cave', hote: 'CAVE', ip: '' }, { lieu: 'garage', hote: 'RIDEAU', ip: '' }];
  const cle = (m) => m, calc = (m) => (c) => f.lieuDeHote(m, '', c);
  const n = (code) => String(P.puces[code].n.textContent);
  // avant /lieux : tout est compte, sous « autres »
  P.compte('CAVE|', calc('CAVE'), false); P.compte('CAVE|', calc('CAVE'), true); P.compte('RIDEAU|', calc('RIDEAU'), false);
  P.recoit({ cartes, lieux: [['cave', 'Cave'], ['garage', 'Garage']] }, null);
  verifie(n(''), '3', 'lignes avant /lieux comptees (Tous)');
  verifie(n('cave'), '2', 'lieu cave recalcule de la cle');
  verifie(n('garage'), '1', 'lieu garage');
  verifie(P.puces[''].e.textContent, ' 1 err', 'erreurs comptees');
  verifie(redessins, 1, 'surChoix appele par recoit');
  P.compte('CAVE|', calc('CAVE'), false);
  verifie(n('cave'), '3', 'compte apres /lieux');
  verifie(P.code('CAVE|', calc('CAVE')), 'cave', 'code d une cle');
  verifie(P.code('X|', calc('X')), 'autres', 'cle inconnue : autres');
  P.puces['cave'].bouton.onclick();
  verifie(P.choisi, 'cave', 'clic = choisi');
  P.puces['cave'].bouton.onclick();
  verifie(P.choisi, '', 'second clic = Tous');
  verifie(P.puces['cave'].bouton.dataset.lieu + P.puces[''].bouton.dataset.lieu, 'cavetous', 'data-lieu');
  P.efface();
  verifie(n('') + n('cave'), '00', 'efface remet a zero');
}
verifie(/innerHTML/.test(JS), false, 'sans innerHTML');
console.log(echecs ? `ROUGE : ${echecs} echec(s)` : 'VERT');
process.exit(echecs ? 1 : 0);
