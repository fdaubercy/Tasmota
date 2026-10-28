"""Page HTML de synchro_fork_web.py (http://127.0.0.1:7500). Les POST portent l'en-tete X-Synchro: 1.
Le bloc de l'assistant (synchro_fork_page_assistant) est insere aux trois reperes BLOC, STYLE et SCRIPT."""

import synchro_fork_page_assistant as assistant

PAGE_BASE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Synchro du fork</title>
<style>
:root{--fond:#f6f7f9;--carte:#fff;--texte:#1d2330;--doux:#667085;--bord:#d9dde5;--accent:#2f6fde;--ok:#1f8a4c;
--alerte:#b7791f;--erreur:#c53030;--console:#11151c;--console-texte:#d8dee9}
@media (prefers-color-scheme:dark){:root{--fond:#14171d;--carte:#1c2028;--texte:#e3e7ee;--doux:#98a2b3;--bord:#323846;
--accent:#6d9cf0;--ok:#4cc38a;--alerte:#e0b252;--erreur:#f07878;--console:#0b0e13}}
*{box-sizing:border-box}body{margin:0;background:var(--fond);color:var(--texte);font:14px/1.45 system-ui,sans-serif}
header{padding:12px 16px;background:var(--carte);border-bottom:1px solid var(--bord);display:flex;flex-wrap:wrap;gap:8px;align-items:center}
h1{font-size:17px;margin:0 12px 0 0}.puce{padding:2px 9px;border-radius:12px;border:1px solid var(--bord);white-space:nowrap}
.puce.ok{color:var(--ok);border-color:var(--ok)}.puce.alerte{color:var(--alerte);border-color:var(--alerte)}
.puce.erreur{color:var(--erreur);border-color:var(--erreur)}
main{max-width:1100px;margin:0 auto;padding:12px 16px}
nav{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:10px}nav button{border-radius:6px 6px 0 0}
nav button.actif{background:var(--accent);color:#fff;border-color:var(--accent)}
button{font:inherit;padding:6px 12px;border-radius:6px;border:1px solid var(--bord);background:var(--carte);color:var(--texte);cursor:pointer}
button.principal{background:var(--accent);color:#fff;border-color:var(--accent)}
button.danger{background:var(--erreur);color:#fff;border-color:var(--erreur)}
button:disabled{opacity:.45;cursor:not-allowed}
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:12px;margin-bottom:10px}
.onglet{display:none}.onglet.actif{display:block}.actions{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
.avert{border-left:4px solid var(--alerte);padding:8px 12px;background:color-mix(in srgb,var(--alerte) 10%,transparent);margin:8px 0}
ul.commits{list-style:none;padding:0;margin:6px 0;max-height:320px;overflow:auto}ul.commits li{padding:2px 0}
.sha{font-family:ui-monospace,Consolas,monospace;color:var(--doux)}.saillant{font-weight:600}.marque{color:var(--alerte)}
pre{font:12.5px/1.4 ui-monospace,Consolas,monospace;white-space:pre-wrap;word-break:break-word;margin:0}
#console{background:var(--console);color:var(--console-texte);padding:10px;border-radius:8px;height:340px;overflow:auto}
#question{display:none;border:2px solid var(--accent)}#question.visible{display:block}
#diff{max-height:420px;overflow:auto;background:var(--console);color:var(--console-texte);padding:10px;border-radius:8px}
.fichier{cursor:pointer;text-decoration:underline dotted}.doux{color:var(--doux)}
.a{color:#4cc38a}.r{color:#f07878}.j{color:#e0b252}.c{color:#56b6c2}.m{color:#c678dd}.g{color:#8b95a7}.b{font-weight:700}
input[type=text]{font:inherit;padding:5px 8px;border-radius:6px;border:1px solid var(--bord);background:var(--fond);color:var(--texte)}
/*STYLE_ASSISTANT*/
</style></head><body>
<header><h1>Synchro du fork</h1><span id="etatBranche" class="puce">branche ?</span><span id="etatRetard" class="puce">…</span>
<span id="etatLocal" class="puce">…</span><span id="etatArbre" class="puce">…</span><span id="etatOperation" class="puce erreur" hidden></span>
<span id="etatExecution" class="puce">au repos</span><button id="rafraichir">Rafraichir</button></header>
<main>
<div id="erreurEtat" class="avert" hidden></div>
<nav id="onglets"><button data-onglet="merge" class="actif">Synchro (merge)</button>
<button data-onglet="fichiers">Fichiers modifies <span id="nbFichiers"></span></button><button data-onglet="historique">Historique</button>
<button data-onglet="aide">Aide</button>
<details id="avance"><summary>Avancé</summary><button data-onglet="rebase">Synchro (rebase)</button></details></nav>

<section id="onglet-merge" class="onglet actif"><div class="carte">
<p>Strategie habituelle de ce fork : <b>merge</b>, comme le bouton « Sync fork » de GitHub. Aucun commit publie n'est reecrit.
Le script s'arrete avant toute action si l'arbre est sale, puis demande deux confirmations : la synchro du fork en ligne, puis le push.</p>
<div class="actions"><button id="mergeDiag">Diagnostic seul (--dry-run)</button><button id="mergeLance" class="principal">Synchroniser…</button></div>
<div id="journal" class="avert" hidden>Le journal des synchros a ete complete et attend un commit.
<button id="commitJournal">Commiter le journal</button> <span id="resultatJournal" class="doux"></span></div>
<h3 id="titreCommits">Nouveautes de l'amont</h3><ul id="commits" class="commits"></ul></div></section>

<section id="onglet-rebase" class="onglet"><div class="carte">
<div class="avert"><b>Stratégie rebase : ne pas l'alterner avec le merge, c'est ce qui fait diverger un fork.</b> Pour la synchro habituelle, utiliser l'assistant de l'onglet « Synchro (merge) ».</div>
<div class="avert"><b>Attention : le rebase reecrit l'historique du fork</b> (tous ses commits propres sont rejoues sur l'amont)
puis propose un <b>push force</b> (--force-with-lease), qui ne s'active qu'apres saisie du nom de la branche.
Ne pas alterner merge et rebase au fil du temps : c'est ce qui fait diverger un fork. Une branche de sauvegarde
<span class="sha">backup-avant-rebase-…</span> est creee avant chaque rebase.</div>
<p>Conflits : chaque fichier en conflit est affiche, puis <b>Garder le mien</b>, <b>Prendre upstream</b>,
<b>Editer dans VS Code</b> (s'ouvre sur le PC du depot) ou <b>Annuler le rebase</b>.</p>
<div class="actions"><button id="rebaseSimule">Simuler les conflits (--dry-run)</button><button id="rebaseLance" class="danger">Lancer le rebase…</button></div>
</div></section>

<section id="onglet-fichiers" class="onglet"><div class="carte"><p class="doux">Fichiers suivis modifies (ils bloquent la synchro). Cliquer pour voir le diff.</p>
<ul id="listeFichiers"></ul><pre id="diff" hidden></pre></div></section>
<section id="onglet-historique" class="onglet"><div class="carte"><pre id="historique">…</pre></div></section>
<section id="onglet-aide" class="onglet"><div class="carte"><p><b>Assistant pas à pas</b> (onglet « Synchro (merge) », après « Diagnostic seul ») : une liste d'étapes propre au cas constaté. Sans conflit ni commit local non poussé, il lance le script de merge habituel. Sinon (voie B) il fait le merge en local, fichier par fichier, puis le commit et le push. Chaque bouton montre la commande git qu'il lance. Il ne force jamais un push, ne fait ni reset, ni stash, ni rebase.</p><p>Cette page lance les scripts tels qu'au terminal ; leurs questions
deviennent les boutons du cadre bleu. Depuis un autre appareil du reseau, utiliser le lien « depuis un autre appareil » de la console (il contient le jeton de la session).</p>
<h3>synchronise_fork_tasmota.py (merge)</h3><pre id="aideMerge">…</pre><h3>synchronise_upstream_tasmota.py (rebase)</h3><pre id="aideRebase">…</pre></div></section>

<div id="question" class="carte"><b id="questionTexte"></b><div id="questionConfirme" class="actions" hidden>
<label>Tapez <b id="questionAttendu"></b> pour confirmer : <input type="text" id="questionSaisie" autocomplete="off"></label></div>
<div id="questionChoix" class="actions"></div><span id="questionErreur" class="r"></span></div>
<div class="carte"><div class="actions" style="margin-top:0"><b>Sortie du script</b><span id="commande" class="doux"></span></div><pre id="console"></pre></div>
<!--BLOC_ASSISTANT-->
</main>
<script>
const $ = id => document.getElementById(id);
const ANSI = {"1":"b","2":"g","31":"r","91":"r","32":"a","92":"a","33":"j","93":"j","36":"c","96":"c","35":"m","95":"m","90":"g","97":""};
function echappe(t){return String(t).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
function ansiHtml(t){
  let classes = [], html = "";
  for (const morceau of String(t).split(/(\x1b\[[0-9;]*m)/)) {
    const m = morceau.match(/^\x1b\[([0-9;]*)m$/);
    if (m) { for (const code of (m[1] || "0").split(";")) { if (code === "0" || code === "") classes = []; else if (ANSI[code]) classes.push(ANSI[code]); } continue; }
    if (morceau) html += classes.length ? `<span class="${classes.join(" ")}">${echappe(morceau)}</span>` : echappe(morceau);
  }
  return html;
}
async function poste(url, corps){
  const r = await fetch(url, {method:"POST", headers:{"X-Synchro":"1","Content-Type":"application/json"}, body:JSON.stringify(corps || {})});
  const texte = await r.text();
  if (!r.ok) throw new Error(texte || ("HTTP " + r.status));
  return texte ? JSON.parse(texte) : {};
}
function puce(el, texte, classe){ el.textContent = texte; el.className = "puce" + (classe ? " " + classe : ""); }

let etatCourant = null;
async function chargeEtat(){
  $("rafraichir").disabled = true;
  puce($("etatRetard"), "interrogation de GitHub…", "");
  try {
    const e = await (await fetch("/etat")).json(); etatCourant = e;
    puce($("etatBranche"), "branche " + e.branche, e.branche === "development" ? "" : "alerte");
    if (e.retard === null) puce($("etatRetard"), "amont : ?", "erreur");
    else puce($("etatRetard"), `${e.retard} commit(s) de retard · ${e.avance} d'avance`, e.retard ? "alerte" : "ok");
    puce($("etatLocal"), e.non_pousses ? `${e.non_pousses} commit(s) non pousse(s)` : "local = fork", e.non_pousses ? "alerte" : "ok");
    puce($("etatArbre"), e.fichiers.length ? `arbre sale : ${e.fichiers.length} fichier(s)` : "arbre propre", e.fichiers.length ? "erreur" : "ok");
    $("etatOperation").hidden = !e.operation_git; $("etatOperation").textContent = e.operation_git ? e.operation_git + " en cours dans le depot" : "";
    $("erreurEtat").hidden = !e.erreur; $("erreurEtat").textContent = e.erreur || "";
    $("nbFichiers").textContent = e.fichiers.length ? `(${e.fichiers.length})` : "";
    $("journal").hidden = !e.journal_modifie;
    $("titreCommits").textContent = e.commits.length ? `Nouveautes de l'amont (${e.commits.length}), pas encore appliquees` : "Nouveautes de l'amont : aucune";
    $("commits").innerHTML = e.commits.map(c => `<li class="${c.saillant ? "saillant" : ""}"><span class="marque">${c.saillant ? "●" : "&nbsp;&nbsp;"}</span>
      <a class="sha" href="${echappe(c.url)}" target="_blank" rel="noopener">${echappe(c.sha)}</a> ${echappe(c.titre)}</li>`).join("");
    $("listeFichiers").innerHTML = e.fichiers.length ? e.fichiers.map(f => `<li><span class="sha">${echappe(f.etat)}</span>
      <span class="fichier" data-chemin="${echappe(f.chemin)}">${echappe(f.chemin)}</span></li>`).join("")
      : "<li class='doux'>aucun" + (e.non_suivis ? ` (${e.non_suivis} fichier(s) non suivi(s), sans effet sur le merge)` : "") + "</li>";
  } catch (err) { $("erreurEtat").hidden = false; $("erreurEtat").textContent = "etat illisible : " + err.message; }
  $("rafraichir").disabled = false;
}
async function chargeTexte(url, id){ try { $(id).textContent = await (await fetch(url)).text() || "(vide)"; } catch (err) { $(id).textContent = err.message; } }
async function chargeAide(){ try { const a = await (await fetch("/aide")).json(); $("aideMerge").textContent = a.merge; $("aideRebase").textContent = a.rebase; } catch (err) { $("aideMerge").textContent = err.message; } }

function choisitOnglet(nom){
  for (const b of document.querySelectorAll("#onglets button")) b.classList.toggle("actif", b.dataset.onglet === nom);
  for (const s of document.querySelectorAll(".onglet")) s.classList.toggle("actif", s.id === "onglet-" + nom);
  if (nom === "rebase") $("avance").open = true;
  if (nom === "historique") chargeTexte("/historique", "historique");
  try { localStorage.setItem("synchroOnglet", nom); } catch (e) {}
}

let questionCourante = null, enCours = false;
function boutonsActifs(){ for (const id of ["mergeDiag","mergeLance","rebaseSimule","rebaseLance","commitJournal"]) $(id).disabled = enCours; }
function afficheQuestion(q){
  questionCourante = q; $("questionErreur").textContent = "";
  $("question").classList.toggle("visible", !!q);
  if (!q) return;
  $("questionTexte").textContent = q.question;
  $("questionConfirme").hidden = !q.confirme; $("questionAttendu").textContent = q.confirme || ""; $("questionSaisie").value = "";
  $("questionChoix").innerHTML = "";
  q.choix.forEach(([valeur, libelle], i) => {
    const b = document.createElement("button"); b.textContent = libelle; b.dataset.valeur = valeur;
    b.className = i === 0 ? (q.confirme ? "danger" : "principal") : "";
    if (i === 0 && q.confirme) b.disabled = true;
    b.onclick = () => repond(valeur);
    $("questionChoix").appendChild(b);
  });
  $("question").scrollIntoView({block:"nearest"});
}
async function repond(valeur){
  try { await poste("/repond", {valeur, confirmation: $("questionSaisie").value}); afficheQuestion(null); }
  catch (err) { $("questionErreur").textContent = err.message; }
}
async function lance(script, simulation){
  if (etatCourant && etatCourant.fichiers.length && !simulation && !confirm("L'arbre de travail est sale : le script va s'arreter avant toute action. Lancer quand meme ?")) return;
  try { await poste("/lance", {script, simulation}); } catch (err) { ajouteLigne("\x1b[31mrefuse : " + err.message + "\x1b[0m"); }
}
function ajouteLigne(texte){
  const c = $("console"), enBas = c.scrollTop + c.clientHeight >= c.scrollHeight - 20;
  c.insertAdjacentHTML("beforeend", ansiHtml(texte) + "\n"); if (enBas) c.scrollTop = c.scrollHeight;
}
function traite(e){
  if (e.type === "debut") { $("console").textContent = ""; $("commande").textContent = e.commande; enCours = true;
    puce($("etatExecution"), "en cours : " + e.script + (e.simulation ? " (simulation)" : ""), "alerte"); }
  else if (e.type === "ligne") ajouteLigne(e.texte);
  else if (e.type === "question") afficheQuestion(e);
  else if (e.type === "reponse") afficheQuestion(null);
  else if (e.type === "fin") { enCours = false; afficheQuestion(null); ajouteLigne(`\x1b[90m--- fin du script (code ${e.code}) ---\x1b[0m`);
    puce($("etatExecution"), `termine (code ${e.code})`, e.code === 0 ? "ok" : "erreur"); chargeEtat(); }
  boutonsActifs();
}
function ecoute(){
  const source = new EventSource("/flux?depuis=0");
  source.onmessage = m => { try { traite(JSON.parse(m.data)); } catch (err) { console.error(err); } };
}

/*SCRIPT_ASSISTANT*/
for (const b of document.querySelectorAll("#onglets button")) b.onclick = () => choisitOnglet(b.dataset.onglet);
$("rafraichir").onclick = chargeEtat;
$("mergeDiag").onclick = () => lance("merge", true);
$("mergeLance").onclick = () => lance("merge", false);
$("rebaseSimule").onclick = () => lance("rebase", true);
$("rebaseLance").onclick = () => { if (confirm("Le rebase reecrit l'historique du fork. Continuer ?")) lance("rebase", false); };
$("commitJournal").onclick = async () => { try { const r = await poste("/commit-journal"); $("resultatJournal").textContent = "commite : " + r.commit; chargeEtat(); }
  catch (err) { $("resultatJournal").textContent = err.message; } };
$("questionSaisie").oninput = () => { const b = $("questionChoix").firstChild; if (b && questionCourante) b.disabled = $("questionSaisie").value !== questionCourante.confirme; };
$("listeFichiers").onclick = async ev => {
  const chemin = ev.target.dataset && ev.target.dataset.chemin; if (!chemin) return;
  const r = await fetch("/diff?chemin=" + encodeURIComponent(chemin)); const texte = await r.text();
  $("diff").hidden = false;
  $("diff").innerHTML = texte.split("\n").map(l => `<span class="${l.startsWith("+") ? "a" : l.startsWith("-") ? "r" : l.startsWith("@@") ? "c" : ""}">${echappe(l)}</span>`).join("\n") || "(pas de diff)";
};

let ongletMemorise = "merge"; try { ongletMemorise = localStorage.getItem("synchroOnglet") || "merge"; } catch (e) {}
choisitOnglet(document.getElementById("onglet-" + ongletMemorise) ? ongletMemorise : "merge");
boutonsActifs(); chargeEtat(); chargeAide(); ecoute();
</script></body></html>
"""
PAGE = (PAGE_BASE.replace("/*STYLE_ASSISTANT*/", assistant.STYLE).replace("<!--BLOC_ASSISTANT-->", assistant.BLOC)
        .replace("/*SCRIPT_ASSISTANT*/", assistant.SCRIPT))
