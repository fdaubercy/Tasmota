"""Page web du sniffeur MQTT (sniffeur_mqtt.py), servie sur http://127.0.0.1:7100.

Routes (sniffeur_mqtt.py) :
    GET  /             cette page            GET /panneaux.js  panneaux (sniffeur_mqtt_panneaux.py)
    GET  /flux         Server-Sent Events : 'etat', les registres ('disco' : fiches tasmota/discovery/MAC/role
                       et config ; 'lwt' : evenements LWT), l'historique ('msg', 'note'), puis le direct ;
                       'reset' : changement de broker (la page vide tout)
    GET  /etat         etat de la liaison broker          GET /brokers  brokers (SANS mots de passe)
    GET  /favoris      favoris de filtre                  GET /logs[?module=garage]  logs stat/<topic>/LOGGING
    POST /publier      {"topic": "cmnd/garage/POWER", "payload": "ON", "format": "texte|hex", "retain": false}
    POST /abonnements  {"filtres": ["#", "$SYS/#"]}      (memorises pour le broker actif)
    POST /brokers      {"action": "enregistrer", "broker": {...}} | {"action": "supprimer|selectionner", "id": "b1"}
    POST /favoris      {"nom", "filtre", "champ", "regex"} | {"action": "supprimer", "nom": "..."}
Chaque POST exige l'en-tete 'X-Sniffeur: 1' et la meme origine (protection contre une page tierce).

Ce fichier : barres Broker / abonnements / filtre / publication et liste des messages (differences avec
le message precedent du meme topic, favoris, export). Les panneaux (audit discovery, connexions LWT,
logs par carte, commande Tasmota, arborescence) sont dans sniffeur_mqtt_panneaux.py.
"""

PAGE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Sniffeur MQTT</title>
<style>
 body{margin:0;background:#1e1e1e;color:#d4d4d4;font:13px Consolas,monospace;display:flex;flex-direction:column;height:100vh}
 .barre{display:flex;flex-wrap:wrap;gap:8px;padding:6px;background:#252526;border-bottom:1px solid #333;align-items:center}
 input,select{background:#3c3c3c;color:#fff;border:1px solid #555;padding:4px;font:inherit}
 input.erreur{border-color:#f14c4c}
 button{background:#0e639c;color:#fff;border:0;padding:4px 10px;cursor:pointer;font:inherit}
 button:disabled{opacity:.5;cursor:default} button.actif{background:#16825d} button.danger{background:#a1260d}
 .pastille{display:inline-block;width:10px;height:10px;border-radius:50%;background:#808080;margin-right:4px}
 .gris{color:#9d9d9d} .vide{color:#808080;font-style:italic}
 #brokerSel{min-width:260px} #formBroker{display:none;background:#2d2d30} #formBroker input[type=text],#formBroker input[type=password]{width:150px}
 #abosListe{display:flex;flex-wrap:wrap;gap:4px} #nouvelAbo{flex:1;min-width:160px}
 .abo{background:#3c3c3c;border:1px solid #555;border-radius:3px;padding:1px 2px 1px 6px;color:#29b8db}
 .abo button,.role button{background:none;color:#f14c4c;padding:0 4px;margin-left:2px} .abo button:hover,.role button:hover{background:#5a1d1d}
 #filtre{flex:1;min-width:160px} #topicPub{flex:1;min-width:200px} #payloadPub{flex:2;min-width:200px}
 #liste{flex:1;overflow:auto;padding:2px 6px}
 .m{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding:1px 0;cursor:pointer;border-bottom:1px solid #2a2a2a}
 .m.ouvert{white-space:pre-wrap;word-break:break-all;background:#252526}
 .t{color:#808080}.r{color:#1e1e1e;background:#e5e510;padding:0 3px;margin-right:4px;border-radius:2px}
 .d{color:#1e1e1e;background:#d670d6;padding:0 3px;margin-right:4px;border-radius:2px}
 .tp{color:#29b8db}.tp:hover{text-decoration:underline}.p{color:#d4d4d4}.hx{color:#d670d6}
 .n{color:#bc3fbc;white-space:pre-wrap;padding:1px 0}
 .lwtOn{color:#23d18b}.lwtOff{color:#f14c4c}
 .ef{background:#5a1d1d;color:#f14c4c;padding:0 4px;margin-right:4px;font-size:11px}
 .diff{color:#e5e510} .avant{color:#f14c4c;text-decoration:line-through} .apres{color:#23d18b}
 #panneau{max-height:50vh;overflow:auto;border-bottom:1px solid #333;background:#202020}
 #panneau section{padding:4px 6px;border-bottom:1px solid #333} #panneau h3{margin:4px 0;font-size:13px;color:#e5e510}
 table{border-collapse:collapse;width:100%} th,td{border-bottom:1px solid #333;padding:2px 6px;text-align:left;vertical-align:top}
 th{color:#9d9d9d;font-weight:normal} tr.alerte td{background:#3a1d1d} tr.attention td{background:#3a331d}
 .role{display:inline-block;background:#3c3c3c;border:1px solid #555;border-radius:3px;padding:0 2px 0 5px;margin:1px 3px 1px 0;color:#29b8db}
 .ano{color:#f14c4c} .warn{color:#e5e510}
 .logs{max-height:35vh;overflow:auto;white-space:pre-wrap;word-break:break-all;background:#1e1e1e;padding:4px}
 .lg-tag{color:#29b8db}.lg-berry{color:#d670d6}.lg-err{color:#f14c4c}.lg-t{color:#808080}
 details{margin-left:14px} summary{cursor:pointer} .feuille{margin-left:28px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
 .feuille:hover{background:#2a2d2e} .nb{color:#808080}
</style></head><body>
<div class="barre">
 <span class="gris">Broker :</span>
 <select id="brokerSel" title="brokers parametres (memorises hors depot : %APPDATA%\sniffeur_mqtt\config.json)"></select>
 <button id="brConnecter" title="se connecter au broker selectionne">Connecter</button>
 <button id="brModifier">Modifier</button>
 <button id="brNouveau">+ Nouveau</button>
 <button id="brSupprimer" class="danger">Supprimer</button>
 <span style="flex:1"></span>
 <span title="page <-> sniffeur"><span class="pastille" id="pWeb"></span><span id="eWeb">connexion...</span></span>
 <span title="sniffeur <-> broker"><span class="pastille" id="pBroker"></span><span id="eBroker">broker ?</span></span>
 <span class="gris" id="infoClient"></span>
</div>
<div class="barre" id="formBroker">
 <input type="hidden" id="fbId">
 <label>Nom <input type="text" id="fbNom" maxlength="60"></label>
 <label>Hote <input type="text" id="fbHote" placeholder="192.168.0.5"></label>
 <label>Port <input type="number" id="fbPort" value="1883" min="1" max="65535" style="width:70px"></label>
 <label title="MQTT sur TLS (port 8883 en general)"><input type="checkbox" id="fbTls"> TLS</label>
 <label title="decocher pour un certificat auto-signe"><input type="checkbox" id="fbVerif" checked> verifier le certificat</label>
 <label>Utilisateur <input type="text" id="fbUser" autocomplete="off"></label>
 <label>Mot de passe <input type="password" id="fbMdp" autocomplete="new-password"></label>
 <label id="fbEffacerBloc" title="supprimer le mot de passe memorise"><input type="checkbox" id="fbEffacer"> sans mot de passe</label>
 <button id="fbEnregistrer">Enregistrer</button> <button id="fbAnnuler">Annuler</button>
</div>
<div class="barre">
 <span class="gris" title="abonnements MQTT du broker actif : filtrage COTE BROKER ; memorises par broker">Abonnements :</span>
 <span id="abosListe"></span>
 <input id="nouvelAbo" placeholder="ajouter (ex. tele/+/LWT, $SYS/#)" autocomplete="off" title="filtre d'abonnement MQTT ; Entree pour ajouter">
 <button id="ajouterAbo">+ Ajouter</button>
</div>
<div class="barre">
 <input id="filtre" placeholder="filtre d'affichage (texte)" autocomplete="off" title="filtre les messages deja recus et a venir">
 <select id="champ" title="ou chercher"><option value="tout">topic + payload</option><option value="topic">topic</option><option value="payload">payload</option></select>
 <label title="le filtre est une expression reguliere"><input type="checkbox" id="regex"> regex</label>
 <select id="favoris" title="favoris de filtre (memorises)"><option value="">favoris...</option></select>
 <button id="favAjouter" title="memoriser le filtre courant comme favori">&#9733;</button>
 <button id="favSupprimer" title="supprimer le favori selectionne">&#x2715;</button>
 <label title="afficher les messages retenus (rejoues par le broker a l'abonnement)"><input type="checkbox" id="retenus" checked> retenus</label>
 <label title="masquer un message identique au precedent du meme topic"><input type="checkbox" id="sansRepet"> sans repetitions</label>
 <label title="afficher les notes du sniffeur (connexion, publications)"><input type="checkbox" id="notes" checked> notes</label>
 <label><input type="checkbox" id="suivre" checked> defilement auto</label>
 <button id="pause" title="fige l'affichage ; les messages continuent d'etre recus">Pause</button>
 <button id="effacer">Effacer</button>
 <select id="formatExport"><option value="txt">.txt</option><option value="json">.json</option></select>
 <button id="exporter" title="telecharger les messages affiches (filtres)">Exporter</button>
 <span class="gris" id="compteur"></span>
</div>
<div class="barre">
 <span class="gris">Panneaux :</span>
 <button id="btAudit" title="fiches tasmota/discovery/MAC/role : plusieurs roles sous une MAC, id/nom/topic incoherents">Audit discovery</button>
 <button id="btLwt" title="connexions / deconnexions des modules (tele/.../LWT) depuis le choix du broker">Connexions (LWT)</button>
 <button id="btLogs" title="logs d'une carte publies sur stat/<topic>/LOGGING (MqttLog)">Logs carte</button>
 <button id="btCmd" title="envoyer une commande Tasmota a un module et voir sa reponse">Commande</button>
 <button id="btArbre" title="arborescence des topics recus, avec compteurs">Arborescence</button>
</div>
<div id="panneau" style="display:none"><section id="secAudit" style="display:none"></section><section id="secLwt" style="display:none"></section>
 <section id="secLogs" style="display:none"></section><section id="secCmd" style="display:none"></section><section id="secArbre" style="display:none"></section></div>
<div class="barre">
 <input id="topicPub" list="topicsVus" placeholder="topic (ex. cmnd/garage/POWER) - clic sur un topic de la liste pour le reprendre" autocomplete="off">
 <datalist id="topicsVus"></datalist>
 <input id="payloadPub" placeholder="payload (Entree pour publier ; vide + retenu = effacer un message retenu)" autocomplete="off">
 <select id="formatPub" title="format du payload"><option value="texte">Texte</option><option value="hex">Hex</option></select>
 <label title="message retenu par le broker"><input type="checkbox" id="retainPub"> retenu</label>
 <button id="publier">Publier</button>
</div>
<div id="liste"></div>
<script>
const $=id=>document.getElementById(id);
const liste=$('liste'),filtre=$('filtre'),champ=$('champ'),regex=$('regex'),retenus=$('retenus'),notes=$('notes'),suivre=$('suivre'),sansRepet=$('sansRepet');
let msgs=[],enPause=false,attente=[],topics=new Set(),etat={},minuteur=null,brokers={brokers:[],actif:''},favoris=[];
let disco={},evLwt=[],stats=Object.create(null),dernier=Object.create(null);          // registres lus par les panneaux (panneaux.js)
const MAX=5000;
function lit(c,d){try{return localStorage.getItem('sniffeur.'+c)??d;}catch(e){return d;}}
function ecrit(c,v){try{localStorage.setItem('sniffeur.'+c,v);}catch(e){}}
function echappe(t){return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function maintenant(){return new Date().toLocaleTimeString();}
function erreurPage(t){ajoute({note:true,t:maintenant(),texte:'ERREUR '+t});}
function poste(url,corps){return fetch(url,{method:'POST',headers:{'X-Sniffeur':'1','Content-Type':'application/json'},body:JSON.stringify(corps)})
  .then(r=>r.text().then(t=>{if(!r.ok)erreurPage(t||r.status);return r.ok?(t?JSON.parse(t):true):false;}));}
function planifiePanneaux(){if(window.dessinePanneaux){clearTimeout(window._minP);window._minP=setTimeout(dessinePanneaux,300);}}
// ---------------------------------------------------------------- filtre et lignes
function testeur(){const f=filtre.value;if(!f)return ()=>true;
  let re=null;if(regex.checked){try{re=new RegExp(f,'i');filtre.classList.remove('erreur');}catch(e){filtre.classList.add('erreur');return ()=>false;}}
  else filtre.classList.remove('erreur');
  const fl=f.toLowerCase(),ok=s=>re?re.test(s):s.toLowerCase().includes(fl);
  return m=>m.note?ok(m.texte):(champ.value==='topic'?ok(m.topic):champ.value==='payload'?ok(m.payload):ok(m.topic)||ok(m.payload));}
function visible(m,t){if(m.note)return notes.checked&&t(m);if(m.retain&&!retenus.checked)return false;
  if(sansRepet.checked&&m.repete)return false;return t(m);}
function aplatit(o,pre,sortie){  // {"a":{"b":1}} -> {"a.b":"1"}
  if(o!==null&&typeof o==='object'){for(const k of Object.keys(o))aplatit(o[k],pre?pre+'.'+k:k,sortie);}else sortie[pre||'(valeur)']=JSON.stringify(o);return sortie;}
function differences(avant,apres){  // texte HTML des differences entre deux payloads
  let a,b;try{a=JSON.parse(avant);b=JSON.parse(apres);}catch(e){a=b=undefined;}
  if(a===undefined||typeof a!=='object'||typeof b!=='object'||!a||!b)
    return '<div class="diff">precedent : <span class="avant">'+echappe(avant)+'</span></div>';
  const fa=aplatit(a,'',{}),fb=aplatit(b,'',{}),cles=[...new Set([...Object.keys(fa),...Object.keys(fb)])];let h='';
  for(const k of cles)if(fa[k]!==fb[k])h+='<div class="diff">'+echappe(k)+' : <span class="avant">'+echappe(fa[k]??'(absent)')+'</span> &rarr; <span class="apres">'+echappe(fb[k]??'(absent)')+'</span></div>';
  return h||'<div class="diff">(memes valeurs, ordre ou format different)</div>';}
function ligne(m){const d=document.createElement('div');
  if(m.note){d.className='n';d.textContent=m.t+' [sniffeur] '+m.texte;return d;}
  d.className='m';
  let p;if(!m.taille)p='<span class="vide">(vide)</span>';
  else{const cls=m.hex?'hx':(m.topic.endsWith('/LWT')?(m.payload==='Online'?'lwtOn':m.payload==='Offline'?'lwtOff':'p'):'p');
    p='<span class="'+cls+'">'+echappe(m.payload)+(m.tronque?' ... (tronque)':'')+'</span>';}
  const change=m.prec!==undefined&&!m.repete;
  d.innerHTML='<span class="t">'+m.t+'</span> '+(m.retain?'<span class="r" title="message retenu">R</span>':'')+
    (change?'<span class="d" title="different du message precedent de ce topic (cliquer pour voir)">&Delta;</span>':'')+
    (m.retain&&m.taille?'<button class="ef" title="effacer ce message retenu du broker (publication vide retenue)">effacer</button>':'')+
    '<span class="tp" title="reprendre ce topic pour publier">'+echappe(m.topic)+'</span> '+p;
  d.querySelector('.tp').onclick=e=>{e.stopPropagation();$('topicPub').value=m.topic;$('payloadPub').focus();};
  const ef=d.querySelector('.ef');if(ef)ef.onclick=e=>{e.stopPropagation();effaceRetenu(m.topic);};
  d.onclick=()=>{const ouvert=d.classList.toggle('ouvert'),zone=d.lastChild;
    if(ouvert&&!m.hex){try{const j=JSON.parse(m.payload);if(typeof j==='object'&&j)zone.textContent='\n'+JSON.stringify(j,null,2);}catch(e){}
      if(change){const x=document.createElement('div');x.className='diffs';x.innerHTML=differences(m.prec,m.payload);d.appendChild(x);}}
    else if(!ouvert){const x=d.querySelector('.diffs');if(x)x.remove();if(!m.hex&&m.taille)d.lastChild.textContent=m.payload;}};
  return d;}
function compte(){$('compteur').textContent=liste.childElementCount+' affiches / '+msgs.length+' en memoire'+(enPause?' (pause : '+attente.length+' en attente)':'');}
function redessine(){const t=testeur(),frag=document.createDocumentFragment();liste.innerHTML='';
  for(const m of msgs)if(visible(m,t))frag.appendChild(ligne(m));
  liste.appendChild(frag);compte();if(suivre.checked)liste.scrollTop=liste.scrollHeight;}
function ajoute(m){
  if(!m.note){m.prec=dernier[m.topic];m.repete=m.prec!==undefined&&m.prec===m.payload;dernier[m.topic]=m.payload;
    const s=stats[m.topic]??={n:0};s.n++;s.t=m.t;s.payload=m.payload;s.retain=m.retain;
    if(!topics.has(m.topic)&&topics.size<2000){topics.add(m.topic);const o=document.createElement('option');o.value=m.topic;$('topicsVus').appendChild(o);}
    if(window.surMessage)surMessage(m);}
  msgs.push(m);if(msgs.length>MAX)msgs.splice(0,msgs.length-MAX);
  if(enPause){attente.push(m);compte();return;}
  if(visible(m,testeur())){liste.appendChild(ligne(m));while(liste.childElementCount>MAX)liste.removeChild(liste.firstChild);
    if(suivre.checked)liste.scrollTop=liste.scrollHeight;}
  compte();}
function effaceRetenu(topic){
  if(!confirm('Effacer du broker le message retenu de :\n'+topic+' ?\n(publication vide retenue, irreversible)'))return;
  poste('/publier',{topic,payload:'',format:'texte',retain:true});}
// ---------------------------------------------------------------- etat, brokers, abonnements
function appliqueEtat(e){etat=e;
  $('pBroker').style.background=e.connecte?'#23d18b':'#f14c4c';
  $('eBroker').textContent=e.connecte?('connecte a '+e.hote+':'+e.port+(e.broker&&e.broker.tls?' (TLS)':'')):('deconnecte'+(e.erreur?' : '+e.erreur:''));
  $('infoClient').textContent=e.clientId+' - '+e.recus+' recus';
  dessineAbos(e.abonnements);$('publier').disabled=!e.connecte;
  if(e.broker&&brokers.actif!==e.broker.id)chargeBrokers();
  document.title='Sniffeur MQTT '+(e.broker?e.broker.nom:'')+(e.connecte?'':' (deconnecte)');}
function chargeBrokers(){return fetch('/brokers').then(r=>r.json()).then(b=>{brokers=b;const sel=$('brokerSel'),choisi=sel.value||b.actif;sel.innerHTML='';
  for(const x of b.brokers)sel.add(new Option((x.id===b.actif?'● ':'')+x.nom+' - '+x.hote+':'+x.port+(x.tls?' TLS':''),x.id));
  sel.value=b.brokers.some(x=>x.id===choisi)?choisi:b.actif;majBoutonsBroker();});}
function brokerChoisi(){return brokers.brokers.find(x=>x.id===$('brokerSel').value);}
function majBoutonsBroker(){const b=brokerChoisi();$('brModifier').disabled=$('brSupprimer').disabled=!b||b.fige;
  $('brConnecter').disabled=!b||(b.id===brokers.actif&&etat.connecte);}
$('brokerSel').onchange=majBoutonsBroker;
$('brConnecter').onclick=()=>{const b=brokerChoisi();if(b)poste('/brokers',{action:'selectionner',id:b.id}).then(chargeBrokers);};
$('brSupprimer').onclick=()=>{const b=brokerChoisi();if(b&&confirm('Supprimer le broker '+b.nom+' ?'))poste('/brokers',{action:'supprimer',id:b.id}).then(chargeBrokers);};
function ouvreForm(b){$('formBroker').style.display='flex';$('fbId').value=b?b.id:'';$('fbNom').value=b?b.nom:'';$('fbHote').value=b?b.hote:'';
  $('fbPort').value=b?b.port:1883;$('fbTls').checked=!!(b&&b.tls);$('fbVerif').checked=b?b.verifierCertificat!==false:true;
  $('fbUser').value=b?(b.utilisateur||''):'';$('fbMdp').value='';$('fbMdp').placeholder=b&&b.aMotDePasse?'(inchange)':'';
  $('fbEffacer').checked=false;$('fbEffacerBloc').style.display=b&&b.aMotDePasse?'':'none';$('fbNom').focus();}
$('brNouveau').onclick=()=>ouvreForm(null);
$('brModifier').onclick=()=>ouvreForm(brokerChoisi());
$('fbAnnuler').onclick=()=>{$('formBroker').style.display='none';};
$('fbTls').onchange=()=>{if($('fbTls').checked&&$('fbPort').value==='1883')$('fbPort').value=8883;else if(!$('fbTls').checked&&$('fbPort').value==='8883')$('fbPort').value=1883;};
$('fbEnregistrer').onclick=()=>{const b={id:$('fbId').value||undefined,nom:$('fbNom').value,hote:$('fbHote').value,port:parseInt($('fbPort').value),
    tls:$('fbTls').checked,verifierCertificat:$('fbVerif').checked,utilisateur:$('fbUser').value,motDePasse:$('fbMdp').value,effacerMotDePasse:$('fbEffacer').checked};
  poste('/brokers',{action:'enregistrer',broker:b}).then(r=>{if(!r)return;$('formBroker').style.display='none';$('fbMdp').value='';
    chargeBrokers().then(()=>{if(r.id){$('brokerSel').value=r.id;majBoutonsBroker();}});});};
let abosAffiches='';
function dessineAbos(abos){const cle=JSON.stringify(abos);if(cle===abosAffiches)return;abosAffiches=cle;
  const zone=$('abosListe');zone.innerHTML='';
  if(!abos.length){zone.innerHTML='<span class="vide">aucun : rien n\'est recu</span>';return;}
  for(const f of abos){const s=document.createElement('span');s.className='abo';s.textContent=f;
    const b=document.createElement('button');b.textContent='✕';b.title='se desabonner de '+f;
    b.onclick=()=>poste('/abonnements',{filtres:(etat.abonnements||[]).filter(x=>x!==f)});
    s.appendChild(b);zone.appendChild(s);}}
function ajouteAbo(){const f=$('nouvelAbo').value.trim();if(!f)return;const abos=etat.abonnements||[];
  if(abos.includes(f)){$('nouvelAbo').value='';return;}
  poste('/abonnements',{filtres:abos.concat([f])}).then(ok=>{if(ok)$('nouvelAbo').value='';});}
$('ajouterAbo').onclick=ajouteAbo;
$('nouvelAbo').addEventListener('keydown',e=>{if(e.key==='Enter')ajouteAbo();});
// ---------------------------------------------------------------- favoris, export, publication
function chargeFavoris(){return fetch('/favoris').then(r=>r.json()).then(f=>{favoris=f;const sel=$('favoris');sel.innerHTML='<option value="">favoris...</option>';
  for(const x of f)sel.add(new Option(x.nom,x.nom));});}
$('favoris').onchange=()=>{const f=favoris.find(x=>x.nom===$('favoris').value);if(!f)return;
  filtre.value=f.filtre;champ.value=f.champ;regex.checked=f.regex;ecrit('filtre',f.filtre);ecrit('champ',f.champ);ecrit('regex',f.regex?'1':'0');redessine();};
$('favAjouter').onclick=()=>{if(!filtre.value)return erreurPage('filtre vide : rien a memoriser');
  const nom=prompt('Nom du favori :',filtre.value.slice(0,40));if(!nom)return;
  poste('/favoris',{nom,filtre:filtre.value,champ:champ.value,regex:regex.checked}).then(ok=>ok&&chargeFavoris().then(()=>{$('favoris').value=nom;}));};
$('favSupprimer').onclick=()=>{const nom=$('favoris').value;if(nom&&confirm('Supprimer le favori '+nom+' ?'))poste('/favoris',{action:'supprimer',nom}).then(chargeFavoris);};
$('exporter').onclick=()=>{const t=testeur(),choix=msgs.filter(m=>visible(m,t)),json=$('formatExport').value==='json';
  const contenu=json?JSON.stringify(choix.map(m=>m.note?{t:m.t,note:m.texte}:{t:m.t,topic:m.topic,payload:m.payload,retain:m.retain,hex:m.hex}),null,1)
    :choix.map(m=>m.note?m.t+' [sniffeur] '+m.texte:m.t+' '+(m.retain?'R ':'')+m.topic+' = '+m.payload).join('\n');
  const a=document.createElement('a'),d=new Date(),pad=n=>String(n).padStart(2,'0');
  a.href=URL.createObjectURL(new Blob([contenu],{type:json?'application/json':'text/plain'}));
  a.download='sniffeur_mqtt_'+d.getFullYear()+pad(d.getMonth()+1)+pad(d.getDate())+'_'+pad(d.getHours())+pad(d.getMinutes())+pad(d.getSeconds())+(json?'.json':'.txt');
  a.click();setTimeout(()=>URL.revokeObjectURL(a.href),5000);};
function publie(){const topic=$('topicPub').value.trim();if(!topic)return;
  poste('/publier',{topic,payload:$('payloadPub').value,format:$('formatPub').value,retain:$('retainPub').checked}).then(ok=>{if(ok)ecrit('topicPub',topic);});}
$('publier').onclick=publie;
$('payloadPub').addEventListener('keydown',e=>{if(e.key==='Enter')publie();});
$('pause').onclick=()=>{enPause=!enPause;$('pause').textContent=enPause?'Reprendre':'Pause';
  if(!enPause){const t=testeur();for(const m of attente)if(visible(m,t))liste.appendChild(ligne(m));attente=[];
    if(suivre.checked)liste.scrollTop=liste.scrollHeight;}compte();};
$('effacer').onclick=()=>{msgs=[];attente=[];liste.innerHTML='';compte();};
for(const [el,c] of [[filtre,'filtre'],[champ,'champ']]){el.value=lit(c,el.value);
  el.addEventListener('input',()=>{ecrit(c,el.value);clearTimeout(minuteur);minuteur=setTimeout(redessine,200);});}
for(const [el,c] of [[regex,'regex'],[retenus,'retenus'],[notes,'notes'],[sansRepet,'sansRepet']]){el.checked=lit(c,el.checked?'1':'0')==='1';
  el.addEventListener('change',()=>{ecrit(c,el.checked?'1':'0');redessine();});}
$('formatPub').value=lit('formatPub',$('formatPub').value);$('formatPub').addEventListener('change',()=>ecrit('formatPub',$('formatPub').value));
$('topicPub').value=lit('topicPub','');
function videTout(){msgs=[];attente=[];liste.innerHTML='';disco={};evLwt=[];stats=Object.create(null);dernier=Object.create(null);compte();planifiePanneaux();}
function connecte(){const es=new EventSource('/flux');
  es.onopen=()=>{$('eWeb').textContent='sniffeur';$('pWeb').style.background='#23d18b';videTout();};
  es.addEventListener('reset',videTout);
  es.addEventListener('disco',e=>{const d=JSON.parse(e.data),k=d.mac+'/'+d.cle;if(d.vide)delete disco[k];else disco[k]=d;planifiePanneaux();});
  es.addEventListener('lwt',e=>{evLwt.push(JSON.parse(e.data));if(evLwt.length>5000)evLwt.shift();planifiePanneaux();});
  es.addEventListener('msg',e=>ajoute(JSON.parse(e.data)));
  es.addEventListener('note',e=>{const d=JSON.parse(e.data);d.note=true;ajoute(d);});
  es.addEventListener('etat',e=>appliqueEtat(JSON.parse(e.data)));
  es.onerror=()=>{$('eWeb').textContent='sniffeur injoignable';$('pWeb').style.background='#f14c4c';};}
setInterval(()=>{if(etat.connecte!==undefined)fetch('/etat').then(r=>r.json()).then(appliqueEtat).catch(()=>{});},5000);
chargeBrokers();chargeFavoris();connecte();
</script>
<script src="/panneaux.js"></script>
</body></html>
"""
