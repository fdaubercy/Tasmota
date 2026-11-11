"""Lieu des messages du sniffeur MQTT (modeles N et O) : CSS et JS inseres dans la page par sniffeur_mqtt_web.py.

Le topic ne dit rien du lieu (la cuve publie en jardin/cuve, le differentiel en bureau/pc) : seul le persist des
cartes le dit, par GET /lieux (lieux.pour_page_identites). Fonctions communes (lieuDeTopic, remplitParLieu,
lieuDemande, bandeauLieu) : lieux.JS, inserees juste avant ce JS.

    Puces       Tous, les lieux de la table, Autres : nombre de messages recus, clic = filtre d'AFFICHAGE
                (les abonnements au broker ne bougent pas), combine au filtre texte ; non memorise
    Etiquette   lieu en tete de chaque message
    ?lieu=      premier chargement seulement, bandeau ; la croix ne change aucune liste
    Panneaux    sniffeur_mqtt_panneaux.py (arborescence par lieu, listes groupees) lit P (P.lieux, P.libelle), codeLieuTopic, envParTopic
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
// Lieu d'un message : puces et comptes par topic dans lieux.JS (pucesLieu), comptes tenus des la reception (pause comprise).
const envParTopic=new Map();
const P=pucesLieu($('lieux'),{erreurs:false,surChoix:()=>redessine()});
function codeLieuTopic(topic,nu){return P.code((nu?'n:':'m:')+topic,c=>lieuDeTopic(topic,c,nu));}
const codeLieu=m=>codeLieuTopic(m.topic,false);
function etiqLieu(m){return P.lieux.length?'<span class="lieu">'+echappe(P.libelle(codeLieu(m)))+'</span> ':'';}
function compteLieu(m){if(!m.note)P.compte('m:'+m.topic,c=>lieuDeTopic(m.topic,c,false),false);}
fetch('/lieux').then(r=>r.json()).then(d=>{
  for(const c of d.cartes)if(c.topic){const l=envParTopic.get(c.topic);envParTopic.set(c.topic,l?l+', '+c.env:c.env);}
  P.recoit(d,document.body);
  if(window.dessinePanneaux)dessinePanneaux();
}).catch(()=>{});                                         // echec : pas de puces, page d'avant
"""
