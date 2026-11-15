"""Page « Liens web » (HTML + CSS + JS dans une constante, servie par liens_web_web.py).

Tout texte venu des donnees passe par textContent (jamais innerHTML) : un lien ou une note ne peut pas injecter de script.
"""

PAGE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Liens web</title>
<style>
:root{--fond:#fff;--texte:#1f2328;--doux:#656d76;--bord:#d0d7de;--carte:#f6f8fa;--accent:#0969da;--ok:#1a7f37;--ko:#cf222e}
@media (prefers-color-scheme:dark){:root{--fond:#0d1117;--texte:#e6edf3;--doux:#8d96a0;--bord:#30363d;--carte:#161b22;--accent:#58a6ff;--ok:#3fb950;--ko:#f85149}}
body{margin:0;padding:16px;background:var(--fond);color:var(--texte);font:14px/1.45 system-ui,sans-serif}
h1{font-size:20px;margin:0 0 4px}.doux{color:var(--doux)}
.barre,.ajout{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
input,select,button,textarea{font:inherit;color:inherit;background:var(--carte);border:1px solid var(--bord);border-radius:6px;padding:6px 8px}
input.q{flex:1 1 260px}button{cursor:pointer}button:disabled{opacity:.5;cursor:default}
details{border:1px solid var(--bord);border-radius:8px;margin:8px 0;background:var(--carte);padding:8px 12px}
summary{cursor:pointer;font-weight:600}
.lien{padding:8px 0;border-top:1px solid var(--bord)}.lien:first-of-type{border-top:0}
.lien a{color:var(--accent);word-break:break-all}.src{font-size:12px;color:var(--doux);word-break:break-all}
.pastille{display:inline-block;font-size:12px;border-radius:10px;padding:0 8px;border:1px solid var(--ok);color:var(--ok);margin-left:6px}
.actions{margin-top:4px;display:flex;gap:6px;flex-wrap:wrap}.actions button,.actions a{font-size:12px}
#msg{min-height:20px}.ko{color:var(--ko)}.ok{color:var(--ok)}
</style></head><body>
<h1>Liens web du dépôt</h1>
<div class="doux">Liens cités dans les fichiers du fork et liens ajoutés ici. Les archives PDF restent sur ce PC (hors git).</div>
<div class="barre">
 <input class="q" id="q" type="search" placeholder="Rechercher (adresse, titre, note, fichier)">
 <select id="cat"><option value="">Tous les thèmes</option></select>
 <select id="arch"><option value="">Archivés ou non</option><option value="oui">Archivés</option><option value="non">Non archivés</option></select>
 <button id="doc" title="Réécrit outils_docs/LIENS_WEB.md">Régénérer LIENS_WEB.md</button>
</div>
<details><summary>Ajouter un lien</summary>
 <div class="ajout">
  <input id="a_url" class="q" placeholder="https://…">
  <input id="a_titre" placeholder="Titre">
  <select id="a_cat"></select>
  <input id="a_note" class="q" placeholder="Note (pourquoi ce lien)">
  <button id="a_ok">Ajouter</button>
 </div>
</details>
<div id="msg" role="status"></div>
<div id="liste"></div>
<script>
let DONNEES={liens:[],categories:[],chrome:false};
const $=s=>document.getElementById(s);
function msg(t,ko){const m=$("msg");m.textContent=t||"";m.className=ko?"ko":"ok";}
async function api(chemin,corps){
  const opt=corps===undefined?{}:{method:"POST",headers:{"X-Liens":"1","Content-Type":"application/json"},body:JSON.stringify(corps)};
  const r=await fetch(chemin,opt);const t=await r.text();
  if(!r.ok)throw new Error(t||("erreur "+r.status));
  return JSON.parse(t);
}
function el(nom,texte,classe){const e=document.createElement(nom);if(texte!==undefined)e.textContent=texte;if(classe)e.className=classe;return e;}
function taille(o){return o>1048576?(o/1048576).toFixed(1)+" Mo":Math.max(1,Math.round(o/1024))+" Ko";}
function ligne(l){
  const d=el("div",undefined,"lien");
  const a=el("a",l.titre||l.url);a.href=l.url;a.target="_blank";a.rel="noopener noreferrer";d.appendChild(a);
  if(l.archive)d.appendChild(el("span","archivé "+l.archive.date.slice(0,10),"pastille"));
  if(l.titre)d.appendChild(el("div",l.url,"src"));
  if(l.note)d.appendChild(el("div",l.note,"doux"));
  d.appendChild(el("div",l.ajoute?"ajouté à la main":"cité dans "+l.fichiers.join(", "),"src"));
  const ac=el("div",undefined,"actions");
  const b=el("button",l.archive?"Réarchiver":"Archiver en PDF");
  b.disabled=!DONNEES.chrome&&!l.url.toLowerCase().includes(".pdf");
  b.title=DONNEES.chrome?"":"Chrome introuvable : seuls les liens PDF s'archivent";
  b.onclick=async()=>{b.disabled=true;msg("Archivage en cours (jusqu'à 90 s)…");
    try{const r=await api("/archiver",{url:l.url});msg("Archivé : "+r.fichier+" ("+taille(r.taille)+")");await charge();}
    catch(e){msg(e.message,true);b.disabled=false;}};
  ac.appendChild(b);
  if(l.archive){const o=el("a","Ouvrir l'archive ("+taille(l.archive.taille)+")");o.href="/archive/"+encodeURIComponent(l.archive.fichier);o.target="_blank";ac.appendChild(o);}
  if(l.ajoute){const r=el("button","Retirer");r.onclick=async()=>{try{await api("/retirer",{id:l.id});await charge();}catch(e){msg(e.message,true);}};ac.appendChild(r);}
  d.appendChild(ac);return d;
}
function dessine(){
  const q=$("q").value.trim().toLowerCase(),c=$("cat").value,ar=$("arch").value;
  const groupes={};let n=0;
  for(const l of DONNEES.liens){
    if(c&&l.categorie!==c)continue;
    if(ar==="oui"&&!l.archive)continue;if(ar==="non"&&l.archive)continue;
    if(q&&!(l.url+" "+l.titre+" "+l.note+" "+l.fichiers.join(" ")).toLowerCase().includes(q))continue;
    (groupes[l.categorie]=groupes[l.categorie]||[]).push(l);n++;
  }
  const racine=$("liste");racine.replaceChildren();
  for(const cat of DONNEES.categories){
    const g=groupes[cat];if(!g)continue;
    const dt=el("details");dt.open=!!(q||c||ar)||g.length<=12;
    dt.appendChild(el("summary",cat+" ("+g.length+")"));
    for(const l of g)dt.appendChild(ligne(l));racine.appendChild(dt);
  }
  if(!n)racine.appendChild(el("p","Aucun lien.","doux"));
}
async function charge(){
  DONNEES=await api("/liens");
  for(const id of ["cat","a_cat"]){const s=$(id);const v=s.value;
    const premier=id==="cat"?s.firstElementChild:null;s.replaceChildren();if(premier)s.appendChild(premier);
    for(const c of DONNEES.categories){const o=el("option",c);o.value=c;s.appendChild(o);}s.value=v;}
  dessine();
}
for(const id of ["q","cat","arch"])$(id).addEventListener("input",dessine);
$("a_ok").onclick=async()=>{try{await api("/ajouter",{url:$("a_url").value,titre:$("a_titre").value,categorie:$("a_cat").value,note:$("a_note").value});
  for(const id of ["a_url","a_titre","a_note"])$(id).value="";msg("Lien ajouté.");await charge();}catch(e){msg(e.message,true);}};
$("doc").onclick=async()=>{try{const r=await api("/regenere",{});msg("LIENS_WEB.md réécrit ("+r.lignes+" lignes).");}catch(e){msg(e.message,true);}};
charge().catch(e=>msg(e.message,true));
</script></body></html>
"""
