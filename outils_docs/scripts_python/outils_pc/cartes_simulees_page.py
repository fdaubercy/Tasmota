"""Page « Cartes simulees » (cartes_simulees_web.py) : liste des cartes du parc, lancer / arreter la simulation, lien vers la page simulee.

Tout ce qui vient du serveur (noms, adresses, messages) s'affiche par textContent, jamais par innerHTML.
La page ne cree aucun fichier : elle commande des serveurs locaux qui s'arretent avec l'outil.
"""

PAGE = """<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cartes simulées</title><link rel="icon" href="data:,"><style>
:root{color-scheme:light dark;--fond:#f6f7f9;--carte:#fff;--bord:#ddd;--texte:#222;--doux:#666;--bleu:#2563eb;--vert:#1e7e3a;--rouge:#c0392b;
  --vert-fond:#e3f4e8;--rouge-fond:#fdecea;--orange-fond:#fff4e0;--orange:#a86400}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--fond:#121417;--carte:#1d2025;--bord:#3a3f47;--texte:#e6e6e6;--doux:#a8adb5;
  --bleu:#5b93ff;--vert:#3fbf63;--rouge:#ff6b5b;--vert-fond:#16301f;--rouge-fond:#3a1d1a;--orange-fond:#33270f;--orange:#f0a020}}
:root[data-theme="dark"]{--fond:#121417;--carte:#1d2025;--bord:#3a3f47;--texte:#e6e6e6;--doux:#a8adb5;--bleu:#5b93ff;--vert:#3fbf63;--rouge:#ff6b5b;
  --vert-fond:#16301f;--rouge-fond:#3a1d1a;--orange-fond:#33270f;--orange:#f0a020}
*{box-sizing:border-box}body{margin:0;font:14px system-ui,sans-serif;color:var(--texte);background:var(--fond)}
main{max-width:900px;margin:0 auto;padding:12px 16px 24px}h1{font-size:20px;margin:0 0 4px}.doux{color:var(--doux)}
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:10px 12px;margin:10px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.carte .nom{flex:1 1 220px;min-width:0;overflow-wrap:anywhere}.carte .nom b{display:block}
.badge{font-size:11px;padding:1px 7px;border-radius:10px;border:1px solid var(--bord)}.badge.berry{background:var(--vert-fond);color:var(--vert)}
.badge.on{background:var(--orange-fond);color:var(--orange)}
button,a.btn{font:inherit;padding:6px 12px;border:1px solid var(--bord);border-radius:6px;background:var(--carte);color:inherit;cursor:pointer;text-decoration:none}
button.prim{background:var(--bleu);border-color:var(--bleu);color:#fff}button:disabled{opacity:.45;cursor:default}
#msg{padding:8px 10px;border-radius:6px;background:var(--orange-fond);color:var(--orange);margin:8px 0}#msg[hidden]{display:none}
#msg.ko{background:var(--rouge-fond);color:var(--rouge)}
</style></head><body><main>
<h1>Cartes simulées</h1>
<p class="doux">Simule hors ligne une carte du parc : pages et modules Berry réels, identité réseau lue dans son persist. Une carte qui répond
sur le réseau n'est pas simulée. MQTT n'est jamais connecté.</p>
<div id="msg" hidden></div><div id="liste"></div>
</main><script>
var ENTETE={'X-Cartes-Simulees':'1','Content-Type':'application/json'};
function msg(t,ko){var m=document.getElementById('msg');m.textContent=t||'';m.className=ko?'ko':'';m.hidden=!t}
function ligne(c){
  var d=document.createElement('div');d.className='carte';
  var n=document.createElement('div');n.className='nom';var b=document.createElement('b');b.textContent=c.nom;n.appendChild(b);
  var s=document.createElement('span');s.className='doux';s.textContent=c.env+' · '+(c.adresse||'adresse inconnue')+' · port '+c.port;n.appendChild(s);d.appendChild(n);
  var g=document.createElement('span');g.className='badge '+(c.berry?'berry':'');g.textContent=c.berry?'modules Berry rejoués':'identité réseau seule';d.appendChild(g);
  if(c.lancee){var e=document.createElement('span');e.className='badge on';e.textContent='simulée';d.appendChild(e);
    var a=document.createElement('a');a.className='btn';a.target='_blank';a.rel='noopener';a.href=c.url;a.textContent='Ouvrir';d.appendChild(a)}
  var k=document.createElement('button');k.textContent=c.lancee?'Arrêter':'Lancer';if(!c.lancee)k.className='prim';
  k.onclick=function(){agit(c.lancee?'/arrete':'/lance',c.env,k)};d.appendChild(k);return d}
function agit(chemin,env,bouton){
  bouton.disabled=true;msg('');
  fetch(chemin,{method:'POST',headers:ENTETE,body:JSON.stringify({env:env})}).then(function(r){return r.text().then(function(t){return [r.ok,t]})})
  .then(function(x){if(!x[0])msg(x[1],true);charge()}).catch(function(e){msg('Erreur : '+e,true);charge()})}
function charge(){
  fetch('/etat').then(function(r){return r.json()}).then(function(j){
    var l=document.getElementById('liste');l.textContent='';j.cartes.forEach(function(c){l.appendChild(ligne(c))})})
  .catch(function(e){msg('Outil injoignable : '+e,true)})}
charge();setInterval(charge,4000);
</script></body></html>
"""
