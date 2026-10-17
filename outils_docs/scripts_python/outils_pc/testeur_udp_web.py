r"""Page du testeur UDP (testeur_udp.py) : http://127.0.0.1:7400 sur ce PC, ou le lien avec jeton depuis le reseau.
Ses appels (fetch, EventSource) sont RELATIFS : ils suivent l'hote qui a servi la page.

Trois onglets : « Essais » (cartes, mode de l'esclave, essais, verdicts, journaux), « Grille ModBus »
(testeur_udp_grille_web, la grille de l'audit jugee sur les logs) et « Aide » (testeur_udp_aide.AIDE, insere a
la place de <!--AIDE-->). Routes : voir testeur_udp_http.py.
Les choix de ports, vitesses et reglages sont memorises par le navigateur (localStorage).
"""

import testeur_udp_aide
import testeur_udp_grille_web

PAGE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Testeur UDP maitre/esclave</title>
<style>
 body{margin:0;background:#1e1e1e;color:#d4d4d4;font:13px Consolas,monospace;display:flex;flex-direction:column;height:100vh}
 input,select{background:#3c3c3c;color:#fff;border:1px solid #555;padding:3px;font:inherit}
 button{background:#0e639c;color:#fff;border:0;padding:4px 10px;cursor:pointer;font:inherit}
 button:disabled{opacity:.5;cursor:default} button.rouge{background:#a1260d} button.vert{background:#16825d} button.gris{background:#555}
 .onglets{display:flex;background:#252526;border-bottom:1px solid #333} .onglets button{background:none;border-radius:0;padding:6px 16px}
 .onglets button.choisi{background:#1e1e1e;border-bottom:2px solid #29b8db}
 .cache{display:none!important} .vue{flex:1;overflow:auto;min-height:0}
 #vueEssais{display:flex;flex-direction:column}
 .cartes{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:6px}
 .carte{background:#252526;border:1px solid #333;padding:6px;display:flex;flex-direction:column;gap:5px}
 .carte h3{margin:0;color:#29b8db} .ligne{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
 .gris{color:#9d9d9d} .pastille{display:inline-block;width:10px;height:10px;border-radius:50%;background:#808080}
 .alerte{background:#5a1d1d;border:1px solid #be1100;padding:5px;color:#ffb3b3}
 .essais{padding:6px;background:#252526;margin:0 6px;border:1px solid #333;display:flex;flex-direction:column;gap:6px}
 table{border-collapse:collapse;width:100%} th,td{border:1px solid #333;padding:3px 6px;text-align:left;vertical-align:top}
 th{background:#2d2d2d} .RECU{color:#23d18b;font-weight:bold} .EMIS{color:#f5f543;font-weight:bold} .NON{color:#f14c4c;font-weight:bold}
 .ECHEC{color:#f14c4c;font-weight:bold} .RUBAN{color:#d670d6;font-weight:bold}
 .journaux{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:6px;flex:1;min-height:260px}
 .journal{background:#1b1b1b;border:1px solid #333;display:flex;flex-direction:column;min-height:0}
 .journal .tete{padding:3px 6px;background:#2d2d2d;color:#29b8db} .corps{flex:1;overflow:auto;padding:4px;white-space:pre-wrap;word-break:break-all}
 .l.udp{color:#4ec9b0;background:#10302b} .l.note{color:#c586c0} .l.err{color:#f14c4c}
 <!--GRILLE_STYLE-->
 .aide{padding:4px 16px 40px;font:13px/1.5 Segoe UI,Arial,sans-serif} .aide h2{color:#29b8db;border-bottom:1px solid #333;margin-top:22px}
 .aide code{font-family:Consolas,monospace;color:#ce9178} .aide pre{background:#1b1b1b;padding:6px;overflow:auto}
</style></head><body>
<div class="onglets"><button id="ongletEssais" class="choisi">Essais</button><button id="ongletGrille">Grille ModBus</button><button id="ongletAide">Aide</button>
 <span style="flex:1"></span><span id="liaison" class="gris" style="padding:6px">connexion...</span></div>
<div id="vueEssais" class="vue">
 <div class="cartes">
  <div class="carte" id="carte-maitre"><h3>Maitre (ESP32-P4)</h3></div>
  <div class="carte" id="carte-esclave"><h3>Esclave (ESP32-S3 : cuve ou rideau)</h3></div>
 </div>
 <div class="essais">
  <div class="ligne">
   <label>Sens <select id="sens"><option value="esclave>maitre">esclave &rarr; maitre</option><option value="maitre>esclave">maitre &rarr; esclave</option></select></label>
   <label>Type <select id="type"><option value="texte">Texte libre</option><option value="modbus">Trame ModbusUDP (E1)</option>
    <option value="imalive">ImAlive (multicast)</option><option value="push">Push d'etat (multicast)</option></select></label>
   <label>Envoi <select id="mode"><option value="UniCast">UniCast</option><option value="MultiCast">MultiCast</option></select></label>
   <label id="blocTexte">Texte <input id="texte" size="26" value="bonjour"></label>
   <span id="blocModbus" class="ligne cache"><label>Adresse ModBus <input id="adresse" size="3" value="2"></label>
    <label>tid <input id="tid" size="5" value="17"></label><label><input type="checkbox" id="sansTid"> sans tid (temoin)</label></span>
   <label>Attente (s) <input id="delai" size="3" value="3"></label>
   <button id="lancer">Lancer l'essai</button><span id="attente" class="gris"></span>
  </div>
  <div class="ligne">
   <label>IP du maitre (destination des envois de l'esclave) <input id="ipMaitre" size="15"></label><button class="gris" id="autoMaitre" title="reprendre la valeur detectee">auto</button>
   <label>IP de l'esclave <input id="ipEsclave" size="15"></label><button class="gris" id="autoEsclave" title="reprendre la valeur detectee">auto</button>
   <span id="aideType" class="gris"></span>
  </div>
  <div class="gris" id="rappel"></div>
  <table><thead><tr><th>Heure</th><th>Sens</th><th>Mode Wi-Fi</th><th>Type</th><th>Message</th><th>Verdict</th><th>Delai</th><th>Source vue</th><th>Details</th></tr></thead>
   <tbody id="verdicts"></tbody></table>
  <div class="ligne"><button class="gris" id="razVerdicts">Vider le tableau</button></div>
 </div>
 <div class="ligne" style="padding:6px 6px 0"><input id="filtre" placeholder="filtre (texte)" size="18">
  <label><input type="checkbox" id="seulementUdp"> lignes UDP seulement</label>
  <label><input type="checkbox" id="suivre" checked> defilement auto</label><button class="gris" id="effacer">Effacer les journaux</button></div>
 <div class="journaux"><div class="journal"><div class="tete">Maitre</div><div class="corps" id="log-maitre"></div></div>
  <div class="journal"><div class="tete">Esclave</div><div class="corps" id="log-esclave"></div></div></div>
</div>
<!--GRILLE-->
<div id="vueAide" class="vue aide cache"><!--AIDE--></div>
<script>
const $=id=>document.getElementById(id);
const ROLES=['maitre','esclave'];
let etat=null,vitesses=[9600,57600,74880,115200,230400,460800,921600],ports=[];
const lignes={maitre:[],esclave:[]};
function sto(cle,val){try{if(val===undefined)return localStorage.getItem('testeurudp.'+cle);localStorage.setItem('testeurudp.'+cle,val);}catch(e){return null;}}
async function post(chemin,corps){
  const r=await fetch(chemin,{method:'POST',headers:{'X-Testeur':'1','Content-Type':'application/json'},body:JSON.stringify(corps||{})});
  const t=await r.text();let j=null;try{j=JSON.parse(t);}catch(e){}
  return {ok:r.ok,statut:r.status,texte:t,json:j};
}
// ------------------------------------------------------------ cartes
function construitCarte(role){
  const c=$('carte-'+role);
  c.insertAdjacentHTML('beforeend',`
   <div class="ligne"><label>Port <select id="port-${role}"></select></label><button class="gris" id="rafr-${role}" title="relister les ports">&#x21bb;</button>
    <label>Vitesse <select id="vit-${role}">${vitesses.map(v=>`<option>${v}</option>`).join('')}</select></label>
    <button id="ouvrir-${role}" class="vert">Ouvrir</button><button id="fermer-${role}" class="rouge">Fermer</button></div>
   <div class="ligne"><span class="pastille" id="p-${role}"></span><span id="etat-${role}"></span></div>
   <div id="alerte-${role}" class="alerte cache"></div>
   <div class="gris" id="infos-${role}"></div><div class="gris" id="logs-${role}"></div>
   ${role==='esclave'?`<div class="ligne"><b>Mode de connexion :</b> <span id="modeActuel">?</span>
    <select id="modeChoix"><option value="RangeExtender">Range Extender</option><option value="WifiClassique">Wi-Fi classique</option></select>
    <button id="modeAppliquer">Appliquer</button><span id="redemarrage" class="gris"></span></div>`:''}
   <div class="ligne"><button class="gris" id="relire-${role}">Relire IP / logs / mode</button>${role==='maitre'?'<button class="gris" id="restaure">Restaurer les logs</button>':''}</div>`);
  $('vit-'+role).value=sto('vitesse-'+role)||'115200';
  $('rafr-'+role).onclick=()=>{ports=[];listePorts();};
  $('relire-'+role).onclick=()=>post('/relire',{carte:role});
  $('ouvrir-'+role).onclick=async()=>{
    const port=$('port-'+role).value; sto('port-'+role,port); sto('vitesse-'+role,$('vit-'+role).value);
    const r=await post('/port',{carte:role,action:'ouvrir',port,vitesse:+$('vit-'+role).value});
    const a=$('alerte-'+role); a.textContent=r.ok&&r.json&&r.json.ok?'':(r.json&&r.json.message)||r.texte; a.classList.toggle('cache',!a.textContent);};
  $('fermer-'+role).onclick=()=>{$('alerte-'+role).classList.add('cache');post('/port',{carte:role,action:'fermer'});};
}
async function listePorts(){
  let n;try{n=await (await fetch('/ports')).json();}catch(e){return;}
  if(JSON.stringify(n)===JSON.stringify(ports)&&$('port-maitre').options.length)return;
  ports=n;
  for(const role of ROLES){
    const s=$('port-'+role),cur=s.value||sto('port-'+role)||'';
    s.innerHTML='<option value="">(aucun)</option>'+ports.map(p=>`<option value="${p.port}">${p.pont?p.description:`${p.port} ${p.usb?'USB ':''}${p.description||''}`}</option>`).join('');
    if(cur&&!ports.some(p=>p.port===cur))s.insertAdjacentHTML('beforeend',`<option value="${cur}">${cur} (absent)</option>`);
    s.value=cur;
  }
}
function majEtat(e){
  etat=e;
  for(const role of ROLES){
    const c=e.cartes[role];
    $('p-'+role).style.background=c.ouvert?(c.muette?'#f14c4c':'#23d18b'):(c.attente?'#f5f543':'#808080');
    const viaPont=String(c.port||'').startsWith('pont:');
    $('etat-'+role).textContent=c.ouvert?(viaPont?c.message:`${c.port} ouvert a ${c.vitesse} bauds`):
     (c.attente?(viaPont?`pont ${c.port.slice(5)} : carte perdue (redemarrage ?), reprise automatique...`:`${c.port} perdu : reouverture automatique...`):'port ferme');
    if(c.ouvert&&c.muette)$('etat-'+role).textContent+=' - CARTE MUETTE : aucune reponse aux commandes, reset de la carte (RST)';
    $('ouvrir-'+role).disabled=c.ouvert; $('fermer-'+role).disabled=!c.ouvert&&!c.attente;
    $('infos-'+role).textContent=c.ouvert?`IP (Status 5) : ${c.ip||'?'}   Hostname : ${c.hostname||'?'}   MAC : ${c.mac||'?'}`:'';
    const poses=Object.entries(c.logs||{});
    $('logs-'+role).textContent=poses.length?'Logs poses : '+poses.map(([k,v])=>`${k}=${v} (avant : ${(c.originaux||{})[k]})`).join(', '):(c.originaux?'Logs : niveaux d\'origine':'');
  }
  $('modeActuel').textContent=e.mode_esclave==='RangeExtender'?'Range Extender':e.mode_esclave==='WifiClassique'?'Wi-Fi classique':
   e.mode_absent?'inconnu : ModeConnexion absent du firmware (a reflasher)':'inconnu';
  $('redemarrage').textContent=e.redemarrage?'redemarrage... (attente de la reconnexion du port)':'';
  $('modeAppliquer').disabled=e.redemarrage||e.mode_absent;
  if(e.mode_esclave&&document.activeElement!==$('modeChoix'))$('modeChoix').value=e.mode_esclave;
  rempli('ipEsclave',e.cartes.esclave.ip);
  rempli('ipMaitre',e.ip_vers_maitre_defaut);
  $('rappel').textContent=`Maitre : point d'acces ${e.ip_ap_maitre}`+(e.cartes.maitre.ip?` ; IP reseau maison ${e.cartes.maitre.ip}`:'')+
   (e.mode_esclave==='WifiClassique'?' - Wi-Fi classique : multicast de l\'esclave relaye par la box (mesure 2026-10-17) ;'+
    ' multicast du maitre par la box seulement si l\'esclave y est decouvert (ImAlive recu, Online, meme groupTopic) ;'+
    ' heure et ipMaitre en unicast.':'');
  $('lancer').disabled=e.essai_en_cours;
}
function rempli(id,val){const c=$(id);if(val&&!c.dataset.touche&&document.activeElement!==c)c.value=val;}
// Les cartes AVANT tout branchement sur leurs boutons (modeAppliquer, restaure) : sinon $() rend null,
// le script s'arrete la et plus rien ne marche, onglets compris (constate le 2026-10-16).
ROLES.forEach(construitCarte);
for(const [id,cle] of [['ipMaitre','autoMaitre'],['ipEsclave','autoEsclave']]){
  $(id).oninput=()=>{$(id).dataset.touche='1';};
  $(cle).onclick=()=>{delete $(id).dataset.touche;if(etat)majEtat(etat);};
}
$('modeAppliquer').onclick=async()=>{
  const m=$('modeChoix').value,nom=m==='RangeExtender'?'Range Extender':'Wi-Fi classique';
  if(!confirm(`Basculer l'esclave en ${nom} ?\nLa carte va redemarrer (le port se rouvrira tout seul).`))return;
  const r=await post('/mode',{mode:m,confirme:true}); if(!r.ok)alert(r.texte);
};
$('restaure').onclick=()=>post('/restaure');
// ------------------------------------------------------------ essais
const AIDES={texte:'Message prefixe automatiquement de TESTUDP-n ; unicast : ReglageUDP envoiUniCast <ip> <msg>, multicast : ReglageUDP envoiMultiCast <msg>.',
 modbus:'Maitre -> esclave en unicast : ReglageModbus envoiMessageUDP <ip> ModbusUDP <tid> <trame 0x01 relai 1>. Preuve : REPOND_UDP avec le meme tid, reception LIRE_UDP sur le maitre, aucune trame RS485 sur l\'esclave.',
 imalive:'Esclave -> maitre en multicast : ReglageUDP forceEnvoiParams ON ; preuve : LIRE_UDP "ImAlive" sur le maitre.',
 push:'Esclave -> maitre en multicast : etat reel du ruban 1376 pousse (Br ... pousseEtat) ; preuve : POUSSE_ETAT puis LIRE_UDP "ModbusPushUDP" sur le maitre.'};
function majType(){
  const t=$('type').value;
  if(t==='modbus'){$('sens').value='maitre>esclave';$('mode').value='UniCast';}
  if(t==='imalive'||t==='push'){$('sens').value='esclave>maitre';$('mode').value='MultiCast';}
  $('sens').disabled=$('mode').disabled=(t!=='texte');
  // Infobulle sur la liste ET son libelle : un element desactive ne recoit plus la souris
  const bulle=t==='texte'?'':(t==='modbus'?'Impose par le type ModbusUDP (E1) : maitre -> esclave, unicast.'
    :'Impose par le type '+(t==='imalive'?'ImAlive':'Push')+' : esclave -> maitre, multicast.')+' Choisir Texte libre pour le changer.';
  for(const id of ['sens','mode']){$(id).title=bulle;$(id).parentElement.title=bulle;}
  $('blocTexte').classList.toggle('cache',t!=='texte'); $('blocModbus').classList.toggle('cache',t!=='modbus');
  $('aideType').textContent=AIDES[t]; sto('type',t);
}
$('type').onchange=majType; $('type').value=sto('type')||'texte'; majType();
$('lancer').onclick=async()=>{
  $('lancer').disabled=true; $('attente').textContent='essai en cours...';
  const r=await post('/test',{type:$('type').value,sens:$('sens').value,mode:$('mode').value,texte:$('texte').value,delai:+$('delai').value,
    ip_maitre:$('ipMaitre').value.trim(),ip_esclave:$('ipEsclave').value.trim(),adresse:+$('adresse').value,tid:+$('tid').value,avec_tid:!$('sansTid').checked});
  $('attente').textContent=r.ok?'':'Refus : '+r.texte; $('lancer').disabled=false;
};
$('razVerdicts').onclick=async()=>{await post('/raz');$('verdicts').innerHTML='';};
function classeVerdict(v){return v==='RECU'?'RECU':v==='EMIS NON RECU'?'EMIS':v==='NON EMIS'?'NON':v==='PAS DE RUBAN'?'RUBAN':'ECHEC';}
function ajouteVerdict(e){
  const tr=document.createElement('tr');
  const cases=[e.heure,e.sens,e.mode_connexion,e.type+(e.type==='texte'||e.type==='modbus'?' '+e.mode:''),e.message,e.verdict,e.delai==null?'':e.delai+' s',e.source,(e.details||[]).join(' ; ')];
  cases.forEach((x,i)=>{const td=document.createElement('td');td.textContent=x;if(i===5)td.className=classeVerdict(e.verdict);tr.appendChild(td);});
  $('verdicts').prepend(tr);
}
// ------------------------------------------------------------ journaux
function classeLigne(l){return l.note?'l note':l.udp?'l udp':/ERREUR|Echec|Error/.test(l.x)?'l err':'l';}
function visible(l){
  const f=$('filtre').value.toLowerCase();
  return (!f||l.x.toLowerCase().includes(f))&&(!$('seulementUdp').checked||l.udp||l.note);
}
function dessine(role,l){
  if(!visible(l))return;
  const z=$('log-'+role),d=document.createElement('div');
  d.className=classeLigne(l); d.textContent=(l.h||'')+' '+l.x; z.appendChild(d);
  while(z.childElementCount>3000)z.removeChild(z.firstChild);
  if($('suivre').checked)z.scrollTop=z.scrollHeight;
}
function redessine(){for(const r of ROLES){$('log-'+r).innerHTML='';lignes[r].forEach(l=>dessine(r,l));}}
$('filtre').oninput=$('seulementUdp').onchange=redessine;
$('effacer').onclick=()=>{ROLES.forEach(r=>lignes[r].length=0);redessine();};
function recoit(m){
  if(m.k==='etat')return majEtat(m);
  if(m.k==='essai')return ajouteVerdict(m);
  if(m.k==='grille')return majGrille(m);
  const h=new Date(m.t*1000).toLocaleTimeString('fr-FR'),l={x:m.x,udp:!!m.udp,note:m.k==='note',h:'['+h+']'};
  for(const r of (m.c?[m.c]:ROLES)){const t=lignes[r];t.push(l);if(t.length>5000)t.shift();dessine(r,l);}
}
// ------------------------------------------------------------ onglets, flux
const VUES=['Essais','Grille','Aide'];
function onglet(nom){for(const v of VUES){$('vue'+v).classList.toggle('cache',v!==nom);$('onglet'+v).classList.toggle('choisi',v===nom);}
 sto('onglet',nom);}
for(const v of VUES)$('onglet'+v).onclick=()=>onglet(v);
function ouvreFlux(){
  const es=new EventSource('/flux');
  es.onopen=()=>{$('liaison').textContent='connecte';ROLES.forEach(r=>lignes[r].length=0);redessine();};
  es.onmessage=ev=>{try{recoit(JSON.parse(ev.data));}catch(e){}};
  es.onerror=()=>{$('liaison').textContent='liaison perdue, nouvel essai...';};
}
listePorts();
fetch('/essais').then(r=>r.json()).then(t=>t.forEach(ajouteVerdict)).catch(()=>{});
ouvreFlux();
setInterval(listePorts,10000);
<!--GRILLE_JS-->
if(VUES.includes(sto('onglet')))onglet(sto('onglet'));
</script></body></html>
"""

PAGE = (PAGE.replace("<!--AIDE-->", testeur_udp_aide.AIDE).replace("<!--GRILLE-->", testeur_udp_grille_web.VUE)
        .replace("<!--GRILLE_STYLE-->", testeur_udp_grille_web.STYLE).replace("<!--GRILLE_JS-->", testeur_udp_grille_web.SCRIPT))
