"""Bloc « Assistant » de la page synchro_fork_web.py : liste verticale d'etapes propre au cas constate, voie B
(merge local guide, conflits fichier par fichier), push. Insere dans PAGE (synchro_fork_page) par .replace()
sur trois reperes : BLOC (HTML), STYLE (CSS), SCRIPT (JS, dans le <script> de la page).

Regles (spec docs/superpowers/specs/2026-10-27-assistant-synchro-fork-design.md, §4, §6, §8) :
- GET /assistant fait un fetch reseau : jamais en boucle. Appele une fois au chargement SI /etat dit « merge en
  cours », apres un dry-run ou un lancement du script de merge lances DEPUIS CETTE PAGE (les evenements rejoues du
  flux ne comptent pas), et au bouton « Réanalyser ». Apres une action POST, on affiche `analyse` de la reponse.
- chaque bouton d'action montre la commande git qu'il lance ; aucune boite de dialogue : une confirmation est un
  second bouton « Confirmer ».
Les textes affiches sont en francais avec accents (le reste du fichier, comme ses voisins, n'en a pas).
"""

BLOC = r"""<div id="assistant" class="carte" hidden>
<div class="actions" style="margin-top:0"><b>Assistant pas à pas</b>
<span class="doux">L'état affiché est celui du dépôt, relu après chaque action.</span></div>
<div id="assistantContenu"></div>
<pre id="assistantMessage" class="doux"></pre>
<div id="assistantVoies" class="carte" hidden></div>
</div>"""

STYLE = r"""
#assistant[hidden]{display:none}
body:has(#onglet-merge:not(.actif)) #assistant{display:none}
ol.etapes{list-style:none;padding:0;margin:8px 0}
.etape{border-left:4px solid var(--bord);padding:6px 10px;margin:6px 0}
.etape.faite{border-color:var(--ok)}.etape.bloquee{border-color:var(--erreur)}.etape.attente{opacity:.65}
.etape.courante{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 7%,transparent)}
.icone{display:inline-block;width:1.5em}.etape .titre{font-weight:600}.etape .titre .doux{font-weight:400}
.act{display:inline-block;margin:4px 12px 4px 0;vertical-align:top}
.act code{display:block;font:11.5px ui-monospace,Consolas,monospace;color:var(--doux);margin-top:2px;max-width:34em;word-break:break-all}
table.conflits{border-collapse:collapse;width:100%}
table.conflits th,table.conflits td{border-bottom:1px solid var(--bord);padding:6px;text-align:left;vertical-align:top}
button.lien{border:0;background:none;color:var(--accent);text-decoration:underline;padding:0;font-family:ui-monospace,Consolas,monospace}
.colonnes{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.colonnes pre{background:var(--console);color:var(--console-texte);padding:8px;border-radius:6px;max-height:320px;overflow:auto}
@media (max-width:700px){.colonnes{grid-template-columns:1fr}}
#assistantMessage.ok{color:var(--ok)}#assistantMessage.erreur{color:var(--erreur)}
.etape ul{margin:4px 0;padding-left:20px}
"""

SCRIPT = r"""
// ---- assistant pas a pas (synchro_fork_page_assistant.py)
const ICONES = {faite:"✔", bloquee:"✖", attente:"○", courante:"▶"};
const NOTES = {UU:"modifié des deux côtés", AA:"ajouté des deux côtés", DD:"supprimé des deux côtés",
  DU:"supprimé chez moi, modifié dans l'amont", UD:"modifié chez moi, supprimé dans l'amont",
  AU:"ajouté chez moi seulement", UA:"ajouté dans l'amont seulement"};
let analyseCourante = null, occupe = false, confirmationEn = "", lancementPropre = null, assistantTeste = false;

function bouton(libelle, commande, attrs, classe){
  const inactif = occupe || enCours ? " disabled" : "";
  return `<div class="act"><button class="${classe || ""}" ${attrs}${inactif}>${echappe(libelle)}</button><code>${echappe(commande)}</code></div>`;
}
// confirmation = second bouton, jamais confirm() : 1er clic -> data-demande, 2e clic (Confirmer) -> l'action
function boutonConfirme(cle, libelle, commande){
  if (confirmationEn !== cle) return bouton(libelle, commande, `data-demande="${cle}"`);
  return bouton("Confirmer : " + libelle, commande, `data-action="${cle}" data-confirme="oui"`, "danger")
    + bouton("Annuler", "(rien n'est lancé)", 'data-annule="1"');
}
function diffHtml(texte){
  return texte.split("\n").map(l => `<span class="${l.startsWith("+") ? "a" : l.startsWith("-") ? "r" : l.startsWith("@@") ? "c" : ""}">${echappe(l)}</span>`).join("\n") || "(pas de diff)";
}
function boutonsConflit(c){
  const f = c.chemin, at = choix => `data-action="resout" data-choix="${choix}" data-chemin="${echappe(f)}"`;
  if (c.type === "UU" || c.type === "AA") {
    let h = bouton("Garder le mien", `git checkout --ours -- ${f} && git add -- ${f}`, at("mien"))
      + bouton("Prendre l'amont", `git checkout --theirs -- ${f} && git add -- ${f}`, at("amont"));
    if (!c.binaire) h += bouton("Ouvrir dans VS Code", `code -r ${f}`, `data-action="ouvre" data-chemin="${echappe(f)}"`)
      + bouton("Marquer résolu", `git add -- ${f}`, at("resolu"));
    return h;
  }
  if (c.type === "DD") return bouton("Le supprimer", `git rm -- ${f}`, at("supprimer"));
  if (["DU", "UD", "AU", "UA"].includes(c.type))
    return bouton("Garder le fichier", `git add -- ${f}`, at("garder")) + bouton("Le supprimer", `git rm -- ${f}`, at("supprimer"));
  return `<div class="avert">À résoudre au terminal : <code>git status</code>, puis <code>git add -- ${echappe(f)}</code> ou <code>git rm -- ${echappe(f)}</code>.</div>`;
}
function tableConflits(a){
  if (!a.conflits.length) return '<p class="doux">Aucun fichier en conflit.</p>';
  return '<table class="conflits"><thead><tr><th>Fichier</th><th>Type</th><th>Résolution</th></tr></thead><tbody>'
    + a.conflits.map(c => `<tr><td><button class="lien" data-voies="${echappe(c.chemin)}">${echappe(c.chemin)}</button></td>
      <td>${echappe(c.type)}${c.binaire ? " (binaire)" : ""}<div class="doux">${echappe(NOTES[c.type] || "")}</div></td><td>${boutonsConflit(c)}</td></tr>`).join("")
    + "</tbody></table>";
}
function corpsFusion(a){
  if (!a.merge_assistant) {
    if (a.retard_origin > 0) return bouton("Mettre à jour depuis origin", "git merge --ff-only origin/development", 'data-action="ff-origin"')
      + `<p class="doux">Le dépôt local a ${a.retard_origin} commit(s) de retard sur origin : à rattraper avant le merge.</p>`;
    return bouton("Lancer le merge", "git merge --no-ff --no-commit upstream/development", 'data-action="merge"');
  }
  return tableConflits(a) + bouton("Terminer le merge", "git commit --no-edit", 'data-action="termine"' + (a.conflits.length ? " disabled" : ""), "principal")
    + (a.conflits.length ? '<span class="doux">Actif quand plus aucun fichier n\'est en conflit.</span>' : "");
}
function liste(elements){ return "<ul>" + elements.map(x => `<li>${x}</li>`).join("") + "</ul>"; }
function corpsEtape(e, a){
  const actif = e.statut === "courante";
  switch (e.id) {
    case "operation": return a.operation === "merge" ? boutonConfirme("abandonne", "Abandonner le merge", "git merge --abort") : "";
    case "branche": return actif || e.statut === "bloquee" ? bouton("Basculer sur development", "git switch development",
      'data-action="bascule"' + (a.fichiers.length ? " disabled" : "")) : "";
    case "arbre": return liste(a.fichiers.map(f => `<span class="sha">${echappe(f.etat)}</span> ${echappe(f.chemin)}${f.build ? " (fichier de build)" : ""}`))
      + bouton("Revérifier", "git status --porcelain", 'data-reanalyse="1"');
    case "nouveautes": return a.commits.length ? `<details><summary>${a.commits.length} commit(s) de l'amont</summary>`
      + liste(a.commits.map(c => `<span class="${c.saillant ? "saillant" : ""}">${c.saillant ? "● " : ""}<span class="sha">${echappe(c.sha)}</span> ${echappe(c.titre)}</span>`)) + "</details>" : "";
    case "deux_cotes": return liste(a.touches_deux.map(f => `<button class="lien" data-voies="${echappe(f)}">${echappe(f)}</button>`));
    case "prevision": return a.prevision.conflits.length ? liste(a.prevision.conflits.map(echappe)) : "";
    case "synchro_a": return actif ? bouton("Lancer le script de merge", "python synchronise_fork_tasmota.py", 'data-lance="1"', "principal") : "";
    case "fusion_b": return actif ? corpsFusion(a) : "";
    case "pousser": return actif ? boutonConfirme("pousse", "Pousser vers origin", "git push origin development") : "";
    case "journal": return actif ? bouton("Commiter le journal", "git commit -- HISTORIQUE_SYNCHRO_FORK.md", 'data-journal="1"') : "";
  }
  return "";
}
function rendAssistant(){
  const a = analyseCourante, el = $("assistant");
  el.hidden = !a;
  if (!a) return;
  let html = "";
  if (a.erreur) html = `<div class="avert"><b>Analyse impossible :</b> ${echappe(a.erreur)}</div>`;
  else if (!a.etapes.length) html = '<p class="doux">Fork à jour : rien à faire.</p>';
  else html = '<ol class="etapes">' + a.etapes.map(e => `<li class="etape ${e.statut}" data-etape="${e.id}">
    <div class="titre"><span class="icone">${ICONES[e.statut] || "○"}</span>${echappe(e.titre)} <span class="doux">${echappe(e.detail)}</span></div>${corpsEtape(e, a)}</li>`).join("") + "</ol>";
  if (a.merge_assistant) html += boutonConfirme("abandonne", "Abandonner le merge", "git merge --abort");
  html += bouton("Réanalyser", "git fetch upstream development && git fetch origin", 'data-reanalyse="1"');
  $("assistantContenu").innerHTML = html;
}
function message(texte, classe){ const m = $("assistantMessage"); m.textContent = texte || ""; m.className = classe || "doux"; }

async function chargeAssistant(){
  try {
    const r = await fetch("/assistant"), texte = await r.text();
    if (!r.ok) throw new Error(texte || ("HTTP " + r.status));
    analyseCourante = JSON.parse(texte);
  } catch (err) { analyseCourante = {erreur: "analyse illisible : " + err.message, etapes: [], conflits: [], merge_assistant: false}; }
  confirmationEn = ""; rendAssistant();
}
async function agit(corps){
  if (occupe) return;
  occupe = true; confirmationEn = ""; message("…"); rendAssistant();
  try {
    const r = await poste("/assistant/action", corps);
    message(r.resultat, "ok"); analyseCourante = r.analyse; chargeEtat();
  } catch (err) { message(err.message, "erreur"); }
  occupe = false; rendAssistant();
}
async function commiteJournal(){
  occupe = true; message("…"); rendAssistant();
  try { const r = await poste("/commit-journal"); message("Journal commité : " + r.commit, "ok"); await chargeAssistant(); chargeEtat(); }
  catch (err) { message(err.message, "erreur"); }
  occupe = false; rendAssistant();
}
async function montreVoies(chemin){
  const z = $("assistantVoies"); z.hidden = false; z.textContent = "…";
  try {
    const r = await fetch("/trois-voies?chemin=" + encodeURIComponent(chemin)), texte = await r.text();
    if (!r.ok) throw new Error(texte || ("HTTP " + r.status));
    const v = JSON.parse(texte);
    z.innerHTML = `<b>${echappe(chemin)}</b> <button data-ferme="1">Fermer</button><div class="colonnes">
      <div><h4>Base → mon fork</h4><pre>${diffHtml(v.mien)}</pre></div><div><h4>Base → l'amont</h4><pre>${diffHtml(v.amont)}</pre></div></div>`;
  } catch (err) { z.textContent = err.message; }
}
$("assistant").onclick = ev => {
  const b = ev.target.closest("button"), d = b && b.dataset;
  if (!b || b.disabled) return;
  if (d.demande) { confirmationEn = d.demande; rendAssistant(); }
  else if (d.annule) { confirmationEn = ""; rendAssistant(); }
  else if (d.ferme) $("assistantVoies").hidden = true;
  else if (d.voies) montreVoies(d.voies);
  else if (d.reanalyse) chargeAssistant();
  else if (d.journal) commiteJournal();
  else if (d.lance) { lancementPropre = {script: "merge", simulation: false}; lance("merge", false); }
  else if (d.action) agit({action: d.action, chemin: d.chemin, choix: d.choix, confirmation: d.confirme});
};
// Les evenements du flux sont rejoues a chaque ouverture de la page : seuls comptent les lancements faits ICI.
$("mergeDiag").addEventListener("click", () => { lancementPropre = {script: "merge", simulation: true}; });
$("mergeLance").addEventListener("click", () => { lancementPropre = {script: "merge", simulation: false}; });
const traiteBase = traite;
traite = function(e){
  traiteBase(e);
  if (e.type === "debut" || e.type === "fin") rendAssistant();      // boutons inactifs pendant qu'un script tourne
  if (e.type === "fin" && lancementPropre && lancementPropre.script === e.script) {
    const p = lancementPropre; lancementPropre = null;
    if (!p.simulation || e.code === 0) chargeAssistant();             // dry-run en echec : le message du script suffit
  }
};
const chargeEtatBase = chargeEtat;
chargeEtat = async function(){
  await chargeEtatBase();
  if (!assistantTeste && etatCourant) { assistantTeste = true;        // une seule fois : merge laisse en cours ?
    if (etatCourant.operation_git === "merge") await chargeAssistant();
  }
};
"""
