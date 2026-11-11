"""Lieu des messages du sniffeur MQTT (modeles N et O) : CSS et JS inseres dans la page par sniffeur_mqtt_web.py.

Le topic ne dit rien du lieu (la cuve publie en jardin/cuve, le differentiel en bureau/pc) : seul le persist des
cartes le dit, par GET /lieux (lieux.pour_page_identites). Fonctions communes (lieuDeTopic, remplitParLieu,
lieuDemande, bandeauLieu) : lieux.JS, inserees juste avant ce JS.

    Puces       Tous, les lieux de la table, Autres : nombre de messages recus, clic = filtre d'AFFICHAGE
                (les abonnements au broker ne bougent pas), combine au filtre texte ; non memorise
    Etiquette   lieu en tete de chaque message
    ?lieu=      premier chargement seulement, bandeau ; la croix ne change aucune liste
    Panneaux    sniffeur_mqtt_panneaux.py (arborescence par lieu, listes groupees) lit lieux, codeLieuTopic,
                libelleLieu, envParTopic
"""

CSS = """
 #lieux{display:flex;flex-wrap:wrap;gap:6px;padding:4px 6px;background:#252526;border-bottom:1px solid #333;align-items:center}
 #lieux:empty{display:none}
 #lieux .puce{background:#3c3c3c;border:1px solid #555;border-radius:3px;padding:2px 6px;color:#d4d4d4}
 #lieux .puce.choisi{border-color:#29b8db} #lieux .puce .n{color:#9d9d9d}
 .lieu{color:#dcdcaa} .env{color:#9d9d9d} .bandeau-lieu{padding:4px 6px;background:#264f78;border-bottom:1px solid #333}
 .bandeau-lieu button{margin-left:6px}
"""

JS = r"""
// Lieu d'un message : cache borne par topic (les topics viennent du reseau), lieuDeTopic ne parcourt les cartes qu'une fois par topic.
let cartes=[],lieux=[],lieuChoisi='',cacheLieu=new Map(),nbLieu={},puces={},envParTopic=new Map();
function codeLieuTopic(topic,nu){const cle=(nu?'n:':'m:')+topic;let c=cacheLieu.get(cle);
  if(c===undefined){c=lieuDeTopic(topic,cartes,nu);if(!lieux.some(x=>x[0]===c))c='autres';
    if(cacheLieu.size>5000)cacheLieu.clear();cacheLieu.set(cle,c);}
  return c;}
const codeLieu=m=>codeLieuTopic(m.topic,false);
const libelleLieu=c=>(lieux.find(x=>x[0]===c)||[0,'Autres'])[1];
function etiqLieu(m){return lieux.length?'<span class="lieu">'+echappe(libelleLieu(codeLieu(m)))+'</span> ':'';}
function majPuce(code){const p=puces[code];if(p)p.n.textContent=nbLieu[code]||0;}
function compteLieu(m){if(!lieux.length||m.note)return;
  for(const code of ['',codeLieu(m)]){nbLieu[code]=(nbLieu[code]||0)+1;majPuce(code);}}
function recompte(){nbLieu={};Object.keys(puces).forEach(majPuce);msgs.forEach(compteLieu);}
function choisitLieu(code){lieuChoisi=code;
  for(const k in puces)puces[k].bouton.classList.toggle('choisi',k===code);
  redessine();}
function dessinePuces(){const bloc=$('lieux'),tete=document.createElement('span');
  tete.className='gris';tete.textContent='Lieu';bloc.replaceChildren(tete);puces={};
  for(const [code,libelle] of [['','Tous'],...lieux,['autres','Autres']]){
    const b=document.createElement('button'),n=document.createElement('span');
    b.type='button';b.className='puce';b.dataset.lieu=code||'tous';n.className='n';
    b.append(libelle+' ',n);b.onclick=()=>choisitLieu(code===lieuChoisi?'':code);
    bloc.appendChild(b);puces[code]={bouton:b,n};}}
fetch('/lieux').then(r=>r.json()).then(d=>{cartes=d.cartes;lieux=d.lieux;cacheLieu.clear();
  for(const c of cartes)if(c.topic){const l=envParTopic.get(c.topic);envParTopic.set(c.topic,l?l+', '+c.env:c.env);}
  dessinePuces();recompte();
  const demande=lieuDemande(lieux);                      // ?lieu= : premier chargement seulement, jamais memorise
  if(demande){bandeauLieu(document.body,libelleLieu(demande),()=>{});choisitLieu(demande);}
  else choisitLieu(lieuChoisi);
  if(window.dessinePanneaux)dessinePanneaux();
}).catch(()=>{});                                         // echec : pas de puces, page d'avant
"""
