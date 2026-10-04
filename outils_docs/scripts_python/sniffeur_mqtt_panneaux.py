"""Panneaux de la page du sniffeur MQTT (servis sur /panneaux.js, charges apres sniffeur_mqtt_web.py).

Lit les registres tenus par la page : disco (fiches tasmota/discovery), evLwt (evenements LWT),
stats (par topic : nombre, heure et dernier payload), etat, et les fonctions $, echappe, poste,
effaceRetenu, redessine. La page appelle dessinePanneaux() (registres modifies) et surMessage(m)
(chaque message recu).

    Audit discovery  plusieurs roles sous une MAC, id / adresseMAC / nom / topic incoherents
    Connexions (LWT) (re)connexions par module, intervalles, chronologie
    Logs carte       stat/<topic>/LOGGING (MqttLog 2 ou 3 sur la carte) : historique du sniffeur + direct
    Commande         cmnd/<topic>/<Commande> selon le FullTopic du module ; reponses stat/<topic>/... 5 s
    Arborescence     topics recus en arbre, compteurs ; clic = filtre sur ce topic
"""

JS = r"""
const SECTIONS=[['btAudit','secAudit'],['btLwt','secLwt'],['btLogs','secLogs'],['btCmd','secCmd'],['btArbre','secArbre']];
const RE_ROLE=/^(maitre|esclave(\d+)|module\d+)$/;
function ouverte(sec){return $(sec).style.display!=='none';}
function bascule(bt,sec){const v=!ouverte(sec);$(sec).style.display=v?'':'none';$(bt).classList.toggle('actif',v);
  $('panneau').style.display=SECTIONS.some(([,s])=>ouverte(s))?'':'none';
  if(v&&sec==='secLogs')initLogs();if(v&&sec==='secCmd')initCmd();dessinePanneaux();}
for(const [bt,sec] of SECTIONS)$(bt).onclick=()=>bascule(bt,sec);
let minArbre=null;
function dessinePanneaux(){dessineAudit();dessineLwt();majModules();if(ouverte('secArbre'))dessineArbre();}
function surMessage(m){logsDirect(m);cmdReponse(m);
  if(ouverte('secArbre')&&!minArbre)minArbre=setTimeout(()=>{minArbre=null;dessineArbre();},1000);}
// ---------------------------------------------------------------- modules connus (fiches config)
function modules(){  // [{tp, dn, ft, pre:[cmnd,stat,tele], hn, mac}] tries par nom ; un seul par topic (fiches d'anciennes MAC)
  const l=[],vus=new Set();for(const e of Object.values(disco))if(e.cle==='config'&&e.tp&&!vus.has(e.tp)&&vus.add(e.tp))
    l.push({tp:e.tp,dn:e.dn||e.tp,ft:e.ft||'%prefix%/%topic%/',pre:Array.isArray(e.tpx)&&e.tpx.length>=2?e.tpx:['cmnd','stat','tele'],hn:e.hn||'',mac:e.mac});
  return l.sort((a,b)=>a.dn.localeCompare(b.dn));}
function nomModule(tp){const m=modules().find(x=>x.tp===tp);return m?m.dn:'';}
function remplitSelect(sel,options,vide){const v=sel.value;sel.innerHTML='';if(vide)sel.add(new Option(vide,''));
  for(const [val,txt] of options)sel.add(new Option(txt,val));if([...sel.options].some(o=>o.value===v))sel.value=v;}
function majModules(){const l=modules().map(m=>[m.tp,m.dn+' ('+m.tp+')']);
  if(ouverte('secCmd'))remplitSelect($('cmdModule'),l,'topic libre...');
  if(ouverte('secLogs')){const connus=new Set(l.map(x=>x[0]));
    remplitSelect($('logModule'),l.concat(Object.keys(logsModules).filter(t=>!connus.has(t)).map(t=>[t,t])).map(([t,x])=>[t,x+(logsModules[t]?' - '+logsModules[t]+' lignes':'')]),'choisir une carte...');}}
// ---------------------------------------------------------------- audit discovery
function audit(){  // {mac: {config, roles:[...], anomalies:[...], alertes:[...]}}
  const parMac={};
  for(const e of Object.values(disco)){const g=parMac[e.mac]??={roles:[],anomalies:[],alertes:[]};
    if(e.cle==='config')g.config=e;else g.roles.push(e);}
  for(const [mac,g] of Object.entries(parMac)){const c=g.config;
    if(g.roles.length>1)g.anomalies.push('plusieurs roles publies : '+g.roles.map(r=>r.cle).join(', '));
    for(const r of g.roles){const m=RE_ROLE.exec(r.cle),attendu=r.cle==='maitre'?0:(m&&m[2]!==undefined?parseInt(m[2]):null);
      if(r.invalide)g.anomalies.push(r.cle+' : JSON illisible');
      if(attendu!==null&&r.id!=null&&r.id!==attendu)g.anomalies.push(r.cle+' : id '+r.id+' (attendu '+attendu+')');
      if(r.macFiche&&r.macFiche.replace(/:/g,'').toUpperCase()!==mac)g.anomalies.push(r.cle+' : adresseMAC '+r.macFiche+' differente du topic');
      if(c&&r.nom&&c.dn&&r.nom!==c.dn)g.alertes.push(r.cle+' : nom \u00ab '+r.nom+' \u00bb \u2260 config \u00ab '+c.dn+' \u00bb');
      if(c&&r.tp&&c.tp&&r.tp!==c.tp)g.alertes.push(r.cle+' : topic '+r.tp+' \u2260 config '+c.tp);}}
  return parMac;}
function dessineAudit(){const a=audit(),macs=Object.keys(a).filter(m=>a[m].roles.length);
  const nbAno=macs.filter(m=>a[m].anomalies.length).length;
  $('btAudit').textContent='Audit discovery'+(nbAno?' ('+nbAno+' \u26a0)':'');
  if(!ouverte('secAudit'))return;
  macs.sort((x,y)=>(a[y].anomalies.length-a[x].anomalies.length)||(a[y].alertes.length-a[x].alertes.length)||x.localeCompare(y));
  let h='<h3>Audit discovery : '+macs.length+' modules publient un role, '+nbAno+' en anomalie</h3>';
  if(!macs.length)h+='<div class="vide">aucune fiche tasmota/discovery/&lt;MAC&gt;/&lt;role&gt; recue (abonnement # ou tasmota/discovery/# necessaire)</div>';
  else{h+='<table><tr><th>MAC</th><th>nom (config)</th><th>topic</th><th>IP</th><th>roles publies (&#x2715; = effacer du broker)</th><th>constat</th></tr>';
    for(const mac of macs){const g=a[mac],c=g.config||{};
      h+='<tr class="'+(g.anomalies.length?'alerte':g.alertes.length?'attention':'')+'"><td>'+mac+'</td><td>'+echappe(c.dn||'-')+'</td><td>'+echappe(c.tp||'-')+
        '</td><td>'+echappe(c.ip||'-')+'</td><td>'+g.roles.map(r=>'<span class="role" title="'+echappe((r.nom||'')+' id '+r.id+' - recu '+r.t+(r.retain?' (retenu)':''))+'">'+
        r.cle+'<button data-topic="'+echappe(r.topic)+'">&#x2715;</button></span>').join('')+'</td><td>'+
        g.anomalies.map(x=>'<div class="ano">'+echappe(x)+'</div>').join('')+g.alertes.map(x=>'<div class="warn">'+echappe(x)+'</div>').join('')+
        (g.anomalies.length||g.alertes.length?'':'<span class="lwtOn">ok</span>')+'</td></tr>';}
    h+='</table>';}
  $('secAudit').innerHTML=h;
  for(const b of $('secAudit').querySelectorAll('button[data-topic]'))b.onclick=()=>effaceRetenu(b.dataset.topic);}
// ---------------------------------------------------------------- connexions LWT
function duree(s){s=Math.round(s);return s<120?s+' s':s<7200?Math.round(s/60)+' min':(s/3600).toFixed(1)+' h';}
function dessineLwt(){if(!ouverte('secLwt'))return;
  const mods={};
  for(const e of evLwt){const tm=e.topic.replace(/^[^/]+\//,'').replace(/\/LWT$/,'');const g=mods[tm]??={ev:[],connexions:[],deco:0};
    g.ev.push(e);if(!e.retain&&e.etat==='Online')g.connexions.push(e.ts);if(!e.retain&&e.etat==='Offline')g.deco++;}
  const lignes=Object.entries(mods).map(([tm,g])=>{const der=g.ev[g.ev.length-1],iv=[];
    for(let i=1;i<g.connexions.length;i++)iv.push(g.connexions[i]-g.connexions[i-1]);
    const moy=iv.length?iv.reduce((x,y)=>x+y,0)/iv.length:null,min=iv.length?Math.min(...iv):null;
    return {tm,g,der,iv,moy,min,frequent:iv.length>=1&&moy<600};});
  lignes.sort((x,y)=>(y.g.connexions.length-x.g.connexions.length)||x.tm.localeCompare(y.tm));
  let h='<h3>Connexions des modules (LWT) depuis le choix du broker ('+echappe(etat.depuis||'?')+')</h3>'+
    '<div class="gris">Chaque \u00ab Online \u00bb non retenu = une (re)connexion MQTT du module. Ligne jaune : reconnexions a moins de 10 min d\'intervalle en moyenne.</div>';
  if(!lignes.length)h+='<div class="vide">aucun message LWT recu (abonnement # ou tele/+/LWT necessaire)</div>';
  else{h+='<table><tr><th>module (topic)</th><th>nom</th><th>etat</th><th>connexions</th><th>deconnexions vues</th><th>derniere</th><th>intervalle moyen / min / dernier</th></tr>';
    for(const l of lignes){const cls=l.der.etat==='Online'?'lwtOn':l.der.etat==='Offline'?'lwtOff':'';
      h+='<tr class="'+(l.frequent?'attention':'')+'"><td>'+echappe(l.tm)+'</td><td>'+echappe(nomModule(l.tm)||'-')+'</td><td class="'+cls+'">'+echappe(l.der.etat)+
        (l.der.retain?' <span class="gris">(retenu)</span>':'')+'</td><td>'+l.g.connexions.length+'</td><td>'+l.g.deco+'</td><td>'+l.der.t+'</td><td>'+
        (l.iv.length?duree(l.moy)+' / '+duree(l.min)+' / '+duree(l.iv[l.iv.length-1]):'-')+'</td></tr>';}
    h+='</table>';
    const recents=evLwt.filter(e=>!e.retain).slice(-40).reverse();
    if(recents.length){h+='<h3>Chronologie (40 derniers evenements)</h3><table><tr><th>heure</th><th>module</th><th>etat</th></tr>';
      for(const e of recents)h+='<tr><td>'+e.t+'</td><td>'+echappe(e.topic)+'</td><td class="'+(e.etat==='Online'?'lwtOn':'lwtOff')+'">'+echappe(e.etat)+'</td></tr>';
      h+='</table>';}}
  $('secLwt').innerHTML=h;}
// ---------------------------------------------------------------- logs d'une carte (stat/<topic>/LOGGING)
let logsModules={},logsInit=false;
const RE_LOG=/^(\d\d:\d\d:\d\d(?:\.\d+)?\s+)?([A-Z]{2,4}:)?(.*)$/s;
function initLogs(){if(logsInit)return chargeListeLogs();logsInit=true;
  $('secLogs').innerHTML='<h3>Logs carte (stat/&lt;topic&gt;/LOGGING)</h3><div class="barre" style="padding:2px 0;background:none;border:0">'+
    '<select id="logModule"></select> <input id="logFiltre" placeholder="filtrer les lignes" style="flex:1"> '+
    '<label><input type="checkbox" id="logSuivre" checked> defilement auto</label> <button id="logRecharger">Recharger</button> <button id="logVider">Vider</button>'+
    '<span class="gris">La carte ne publie ses logs que si <b>MqttLog</b> vaut 2 ou plus (commande ci-dessous).</span></div><div class="logs" id="logZone"></div>';
  $('logModule').onchange=chargeLogs;$('logRecharger').onclick=()=>{chargeListeLogs();chargeLogs();};
  $('logVider').onclick=()=>{$('logZone').innerHTML='';};
  $('logFiltre').oninput=()=>{clearTimeout(window._minLog);window._minLog=setTimeout(chargeLogs,250);};
  chargeListeLogs();}
function chargeListeLogs(){fetch('/logs').then(r=>r.json()).then(d=>{logsModules=d.modules||{};majModules();});}
function ligneLog(l){const d=document.createElement('div'),m=RE_LOG.exec(l.texte)||[],tag=m[2]||'',texte=m[3]??l.texte;
  const err=/\b(ERROR|ERREUR|Erreur|erreur|ERR|Exception|failed|echec)\b/.test(l.texte);
  d.innerHTML='<span class="lg-t">'+l.t+'</span> '+(tag?'<span class="'+(tag==='BRY:'?'lg-berry':'lg-tag')+'">'+echappe(tag)+'</span>':'')+
    '<span class="'+(err?'lg-err':'')+'">'+echappe(texte)+'</span>';return d;}
function filtreLog(texte){const f=$('logFiltre').value.toLowerCase();return !f||texte.toLowerCase().includes(f);}
function chargeLogs(){const mod=$('logModule').value,zone=$('logZone');zone.innerHTML='';
  if(!mod){zone.innerHTML='<div class="vide">choisir une carte</div>';return;}
  fetch('/logs?module='+encodeURIComponent(mod)).then(r=>r.json()).then(d=>{if($('logModule').value!==mod)return;
    const frag=document.createDocumentFragment();for(const l of d.lignes)if(filtreLog(l.texte))frag.appendChild(ligneLog(l));
    zone.appendChild(frag);if(!d.lignes.length)zone.innerHTML='<div class="vide">aucune ligne recue de '+echappe(mod)+' : MqttLog 2 sur la carte ? abonnement couvrant stat/'+echappe(mod)+'/LOGGING ?</div>';
    zone.scrollTop=zone.scrollHeight;});}
function logsDirect(m){const r=/^[^/]+\/(.+)\/LOGGING$/.exec(m.topic);if(!r||m.hex)return;
  const nouveau=!(r[1] in logsModules);logsModules[r[1]]=(logsModules[r[1]]||0)+1;
  if(!logsInit||!ouverte('secLogs'))return;if(nouveau)majModules();
  if($('logModule').value!==r[1]||!filtreLog(m.payload))return;
  const zone=$('logZone');if(zone.querySelector('.vide'))zone.innerHTML='';
  zone.appendChild(ligneLog({t:m.t,texte:m.payload}));while(zone.childElementCount>3000)zone.removeChild(zone.firstChild);
  if($('logSuivre').checked)zone.scrollTop=zone.scrollHeight;}
// ---------------------------------------------------------------- commande Tasmota
let cmdInit=false,cmdEnCours=null;
function initCmd(){if(cmdInit)return;cmdInit=true;
  $('secCmd').innerHTML='<h3>Commande Tasmota</h3><div class="barre" style="padding:2px 0;background:none;border:0">'+
    '<select id="cmdModule"></select> <input id="cmdTopicLibre" placeholder="topic du module (ex. garage)" style="width:160px"> '+
    '<input id="cmdCommande" list="cmdConnues" placeholder="commande (ex. Status)" style="width:160px" autocomplete="off"><datalist id="cmdConnues">'+
    ['Status','Status 0','Status 5','Status 11','Power','State','MqttLog','SerialLog','WebLog','Weblog','Restart','Br','Backlog','Time','Uptime','Ping4','Teleperiod','Rule1']
      .map(c=>'<option value="'+c+'">').join('')+'</datalist> '+
    '<input id="cmdArgument" placeholder="argument (ex. 0, ON, 3)" style="flex:1"> <button id="cmdEnvoyer">Envoyer</button>'+
    '<span class="gris" id="cmdTopic"></span></div><div id="cmdReponses"></div>';
  $('cmdModule').onchange=majCmdTopic;$('cmdTopicLibre').oninput=majCmdTopic;$('cmdCommande').oninput=majCmdTopic;
  $('cmdEnvoyer').onclick=envoieCmd;for(const id of ['cmdCommande','cmdArgument'])$(id).addEventListener('keydown',e=>{if(e.key==='Enter')envoieCmd();});
  majModules();majCmdTopic();}
function cibleCmd(){  // {cmnd: 'cmnd/garage/', stat: 'stat/garage/'} selon le FullTopic du module
  const m=modules().find(x=>x.tp===$('cmdModule').value),libre=$('cmdTopicLibre');libre.style.display=m?'none':'';
  if(!m){const t=libre.value.trim();return t?{cmnd:'cmnd/'+t+'/',stat:'stat/'+t+'/',nom:t}:null;}
  const base=p=>m.ft.replace('%prefix%',p).replace('%topic%',m.tp).replace('%hostname%',m.hn).replace('%id%',(m.mac||'').slice(-6));
  return {cmnd:base(m.pre[0]),stat:base(m.pre[1]),nom:m.dn};}
function majCmdTopic(){const c=cibleCmd(),cmd=$('cmdCommande').value.trim().split(/\s+/)[0];
  $('cmdTopic').textContent=c?'\u2192 '+c.cmnd+(cmd||'<commande>'):'';}
function envoieCmd(){const c=cibleCmd();let cmd=$('cmdCommande').value.trim(),arg=$('cmdArgument').value;
  if(!c||!cmd)return erreurPage('commande : module et commande obligatoires');
  const i=cmd.search(/\s/);if(i>0){arg=cmd.slice(i+1)+(arg?' '+arg:'');cmd=cmd.slice(0,i);}
  const bloc=document.createElement('div');bloc.style.borderBottom='1px solid #333';
  bloc.innerHTML='<div><span class="t">'+maintenant()+'</span> <span class="tp">'+echappe(c.cmnd+cmd)+'</span> = '+echappe(arg||'(vide)')+
    ' <span class="gris">- '+echappe(c.nom)+'</span> <span class="gris etatCmd">envoi...</span></div>';
  $('cmdReponses').prepend(bloc);while($('cmdReponses').childElementCount>10)$('cmdReponses').lastChild.remove();
  if(cmdEnCours)clearTimeout(cmdEnCours.fin);
  cmdEnCours={stat:c.stat,bloc,nb:0,fin:setTimeout(()=>{if(cmdEnCours&&cmdEnCours.bloc===bloc){
    bloc.querySelector('.etatCmd').textContent=cmdEnCours.nb?cmdEnCours.nb+' reponse(s)':'aucune reponse en 5 s (module hors ligne ? abonnement couvrant '+c.stat+'# ?)';cmdEnCours=null;}},5000)};
  poste('/publier',{topic:c.cmnd+cmd,payload:arg,format:'texte',retain:false}).then(ok=>{if(!ok&&cmdEnCours&&cmdEnCours.bloc===bloc){
    clearTimeout(cmdEnCours.fin);bloc.querySelector('.etatCmd').textContent='echec de publication';cmdEnCours=null;}
    else if(ok)bloc.querySelector('.etatCmd').textContent='en attente de reponse...';});}
function cmdReponse(m){if(!cmdEnCours||m.retain||!m.topic.startsWith(cmdEnCours.stat))return;
  const suite=m.topic.slice(cmdEnCours.stat.length);if(!suite||suite.includes('/')||suite==='LOGGING')return;   // pas stat/garage/rideau/... pour garage
  cmdEnCours.nb++;let texte=m.payload;try{const j=JSON.parse(texte);if(typeof j==='object'&&j)texte=JSON.stringify(j,null,2);}catch(e){}
  const d=document.createElement('div');d.style.whiteSpace='pre-wrap';d.style.marginLeft='14px';
  d.innerHTML='<span class="t">'+m.t+'</span> <span class="tp">'+echappe(m.topic)+'</span>\n<span class="apres">'+echappe(texte)+'</span>';
  cmdEnCours.bloc.appendChild(d);cmdEnCours.bloc.querySelector('.etatCmd').textContent=cmdEnCours.nb+' reponse(s)';}
// ---------------------------------------------------------------- arborescence des topics
const arbreOuvert=new Set();
function dessineArbre(){const racine={enfants:Object.create(null),n:0,nbTopics:0};   // Object.create(null) : un segment 'constructor' reste un segment
  for(const [topic,s] of Object.entries(stats)){let noeud=racine;racine.n+=s.n;racine.nbTopics++;const parts=topic.split('/');
    parts.forEach((p,i)=>{noeud=noeud.enfants[p]??={enfants:Object.create(null),n:0,nbTopics:0,chemin:parts.slice(0,i+1).join('/')};noeud.n+=s.n;noeud.nbTopics++;});
    noeud.feuille=s;noeud.topic=topic;}
  const sec=$('secArbre'),pan=$('panneau'),defil=pan.scrollTop;
  let h='<h3>Arborescence : '+racine.nbTopics+' topics, '+racine.n+' messages depuis l\'ouverture de la page (clic sur un topic = filtre)</h3>';
  if(!racine.nbTopics)h+='<div class="vide">aucun message recu</div>';
  function rend(noeud){let s='';
    for(const nom of Object.keys(noeud.enfants).sort((a,b)=>a.localeCompare(b))){const e=noeud.enfants[nom],sous=Object.keys(e.enfants).length;
      if(e.feuille){const f=e.feuille;s+='<div class="feuille" data-topic="'+echappe(e.topic)+'" title="'+echappe(e.topic)+'">'+(f.retain?'<span class="r">R</span>':'')+
        '<span class="tp">'+echappe(nom||'(vide)')+'</span> <span class="nb">('+f.n+', '+f.t+')</span> '+echappe(String(f.payload).slice(0,200))+'</div>';}
      if(sous)s+='<details data-chemin="'+echappe(e.chemin)+'"'+(arbreOuvert.has(e.chemin)?' open':'')+'><summary><span class="tp">'+echappe(nom||'(vide)')+
        '</span>/ <span class="nb">'+e.nbTopics+' topics, '+e.n+' messages</span></summary>'+rend(e)+'</details>';}
    return s;}
  sec.innerHTML=h+rend(racine);pan.scrollTop=defil;
  for(const d of sec.querySelectorAll('details'))d.addEventListener('toggle',()=>{if(d.open)arbreOuvert.add(d.dataset.chemin);else arbreOuvert.delete(d.dataset.chemin);});
  for(const f of sec.querySelectorAll('.feuille'))f.onclick=()=>{const t=f.dataset.topic;filtre.value=t;champ.value='topic';regex.checked=false;
    ecrit('filtre',t);ecrit('champ','topic');ecrit('regex','0');$('topicPub').value=t;redessine();};}
dessinePanneaux();
"""
