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
verifie(/innerHTML/.test(JS), false, 'sans innerHTML');
console.log(echecs ? `ROUGE : ${echecs} echec(s)` : 'VERT');
process.exit(echecs ? 1 : 0);
