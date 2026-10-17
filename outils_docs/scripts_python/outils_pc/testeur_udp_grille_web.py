"""Onglet « Grille ModBus » de la page du testeur UDP (testeur_udp_web.py) : vue HTML, style et script.

Insere dans testeur_udp_web.PAGE a la place de <!--GRILLE--> (vue), <!--GRILLE_STYLE--> et <!--GRILLE_JS-->.
Le script reutilise $, post() et le flux /flux de la page : l'etat de la grille arrive en {"k": "grille", ...}.
Routes : GET /grille (etat), POST /grille {action: lancer|repondre|arreter, test, duree, reponse}, POST /cmd.
"""

STYLE = r"""
 .grille{padding:6px;display:flex;flex-direction:column;gap:8px}
 .bloc{background:#252526;border:1px solid #333;padding:6px}
 .bloc h3{margin:0 0 6px;color:#29b8db;display:flex;gap:8px;align-items:center}
 .st-OK{color:#23d18b;font-weight:bold} .st-ECHEC{color:#f14c4c;font-weight:bold} .st-NONVU{color:#f5f543;font-weight:bold}
 .st-INFO{color:#4ec9b0} .st-encours{color:#29b8db} .st-consigne{color:#d670d6;font-weight:bold} .st-attente,.st-annule{color:#808080}
 .consigne{background:#3b2a4a;border:1px solid #d670d6;padding:8px;font-size:14px}
 .detail{color:#9d9d9d;word-break:break-all}
 .decompte{color:#f5f543;font-weight:normal}
"""

VUE = r"""
<div id="vueGrille" class="vue grille cache">
 <div class="bloc ligne">
  <span id="grilleCible" class="gris"></span>
  <label>Duree du test 2 (s) <input id="grilleDuree" size="4" value="300"></label>
  <button class="rouge" id="grilleArreter">Arreter le test en cours</button>
  <span id="grilleMsg" class="gris"></span>
 </div>
 <div id="grilleConsigne" class="consigne cache"><div id="grilleConsigneTexte"></div><div class="ligne" id="grilleBoutons"></div></div>
 <div class="bloc ligne">
  <label>Commande libre sur <select id="cmdCarte"><option value="maitre">le maitre</option><option value="esclave">l'esclave</option></select></label>
  <input id="cmdTexte" size="48" placeholder="ex. Status 5, Power1, RgxState">
  <button id="cmdEnvoyer">Envoyer</button><span class="gris">la reponse s'affiche dans le journal de la carte (onglet Essais)</span>
 </div>
 <div id="grilleTests"></div>
</div>
"""

SCRIPT = r"""
// ------------------------------------------------------------ onglet Grille ModBus
let grille=null, finDecompte=null;
// Decompte de la fenetre d'observation (test 2 : 300 s par defaut) a cote du bouton Lancer du test en cours.
// Le serveur donne le reste en secondes a chaque mise a jour ; la page decompte seule entre deux.
function majDecompte(){
  if(!grille||!grille.en_cours||finDecompte==null)return;
  const e=$('decompte'+grille.en_cours);if(!e)return;
  const s=Math.max(0,Math.round((finDecompte-Date.now())/1000));
  e.textContent=s>0?`encore ${Math.floor(s/60)} min ${String(s%60).padStart(2,'0')} s`:'bilan en cours...';
}
setInterval(majDecompte,1000);
const STATUT_CLASSE={'OK':'st-OK','ECHEC':'st-ECHEC','NON VU':'st-NONVU','INFO':'st-INFO','en cours':'st-encours',
 'consigne':'st-consigne','attente':'st-attente','annule':'st-annule'};
function esc(t){return String(t==null?'':t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function majGrille(g){
  grille=g;
  const c=g.cible||{};
  $('grilleCible').textContent=`Esclave teste : ID ModBus ${c.id}, ruban POWER${c.power} du P4, registre ${c.registre}`+
    (g.en_cours?` - test ${g.en_cours} en cours`:'');
  $('grilleArreter').disabled=!g.en_cours;
  const k=g.consigne;
  $('grilleConsigne').classList.toggle('cache',!k);
  if(k){
    $('grilleConsigneTexte').textContent=k.texte;
    const b=$('grilleBoutons');
    if(b.dataset.cle!==k.cle){
      b.dataset.cle=k.cle;b.innerHTML='';
      for(const r of k.boutons){const x=document.createElement('button');x.textContent=r==='fait'?"C'est fait":r==='oui'?'Oui':'Non';
        if(r==='non')x.className='rouge';x.onclick=()=>actionGrille({action:'repondre',reponse:r});b.appendChild(x);}
    }
  } else $('grilleBoutons').dataset.cle='';
  $('grilleTests').innerHTML=g.tests.map(t=>`<div class="bloc"><h3>Test ${t.num} - ${esc(t.titre)}
    <button data-test="${t.num}" ${g.en_cours?'disabled':''}>Lancer</button><span class="decompte" id="decompte${t.num}"></span></h3>
    <table><thead><tr><th>Carte</th><th>Verification</th><th>Statut</th><th>Detail / preuve</th></tr></thead><tbody>`+
    t.verifs.map(v=>`<tr><td>${v.carte}</td><td>${esc(v.libelle)}</td><td class="${STATUT_CLASSE[v.statut]||''}">${esc(v.statut)}</td>
      <td class="detail">${esc(v.detail)}</td></tr>`).join('')+'</tbody></table></div>').join('');
  finDecompte=(g.en_cours&&g.reste!=null)?Date.now()+g.reste*1000:null;
  majDecompte();
  for(const b of document.querySelectorAll('#grilleTests button[data-test]'))
    b.onclick=()=>actionGrille({action:'lancer',test:+b.dataset.test,duree:+$('grilleDuree').value||300});
}
async function actionGrille(corps){
  const r=await post('/grille',corps);
  $('grilleMsg').textContent=r.ok?'':(r.texte||'erreur');
  if(r.ok&&r.json)majGrille(r.json);
}
$('grilleArreter').onclick=()=>actionGrille({action:'arreter'});
$('cmdEnvoyer').onclick=async()=>{
  const c=$('cmdTexte').value.trim();if(!c)return;
  const r=await post('/cmd',{carte:$('cmdCarte').value,commande:c});
  $('grilleMsg').textContent=r.ok?`envoye a la carte ${$('cmdCarte').value} : ${c}`:(r.texte||'erreur');
};
$('cmdTexte').onkeydown=e=>{if(e.key==='Enter')$('cmdEnvoyer').click();};
$('grilleDuree').value=sto('dureeGrille')||300; $('grilleDuree').onchange=()=>sto('dureeGrille',$('grilleDuree').value);
fetch('/grille').then(r=>r.json()).then(majGrille).catch(()=>{});
"""
