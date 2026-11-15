"""Pastille d'occupation en fin de compilation (plan build-fin-partitions, variante D de outils_docs/build_fin_partitions/).

Inseree dans build_page.PAGE par /*CSS_FIN_MEMOIRE*/ et /*JS_FIN_MEMOIRE*/, avec deux appels dans la page :
`finMemoireCharge(e)` (evenement `fin_env`) et `finMemoireTete(tete, env)` (dessin de la ligne de l'env).
Quand un env reussit sa COMPILATION, la page lit GET /memoire?env= (analyse que la serie vient d'enregistrer, aucun nouvel
evenement) et pose dans la ligne de l'env « Flash 87 % · RAM 32 % » : orange des 90 %, rouge des 95 % (partition ou zone
de RAM la plus pleine). Clic = fenetre de detail (alertes, ruban, jauges par partition et par zone de RAM), fermee par
Echap, un clic dehors ou « Fermer » ; « Onglet Mémoire » ouvre l'onglet de meme nom. Pas d'analyse ou aucune partition
mesuree : pas de pastille, aucune erreur. Tout texte du serveur passe par h(..., {texte}) = textContent, jamais innerHTML.
"""

CSS = r"""
  .fm-pastille{font:inherit;font-size:12px;padding:2px 9px;border-radius:12px;border:1px solid var(--vert);color:var(--vert);background:none;cursor:pointer;white-space:nowrap}
  .fm-pastille.o{border-color:var(--orange);color:var(--orange)}.fm-pastille.r{border-color:var(--rouge);color:var(--rouge)}
  .fm-voile{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:50;display:flex;align-items:flex-start;justify-content:center;padding:8vh 12px 12px;overflow:auto}
  .fm-fenetre{background:var(--carte);color:var(--texte);border:1px solid var(--bord);border-radius:10px;padding:16px;width:min(600px,100%);box-sizing:border-box}
  .fm-fenetre h2{margin:0 0 10px;font-size:15px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;overflow-wrap:anywhere}
  .fm-alerte{padding:6px 10px;border-radius:6px;margin-bottom:6px;font-size:13px;background:var(--orange-fond);color:var(--orange)}
  .fm-alerte.r{background:var(--rouge-fond);color:var(--rouge)}
  .fm-ruban{display:flex;height:30px;background:var(--piste);border-radius:6px;overflow:hidden;margin:10px 0}
  .fm-ruban span{color:#fff;font-size:11px;display:flex;align-items:center;justify-content:center;overflow:hidden;white-space:nowrap;border-right:1px solid rgba(255,255,255,.6)}
  .fm-ligne{display:grid;grid-template-columns:90px 1fr auto;gap:10px;align-items:center;font-size:13px;margin:4px 0}
  .fm-piste{height:9px;background:var(--piste);border-radius:5px;overflow:hidden}
  .fm-piste i{display:block;height:100%;background:var(--vert)}.fm-piste i.o{background:var(--orange)}.fm-piste i.r{background:var(--rouge)}
  .fm-titre{font-size:12px;color:var(--doux);margin-top:8px}
  .fm-pied{display:flex;gap:8px;justify-content:flex-end;margin-top:12px}
"""

JS = r"""
// ---------- pastille d'occupation en fin de compilation (build_page_fin_memoire.py) ----------
var FM = {}, FM_COUL = {nvs: "#8b95a5", otadata: "#8b95a5", safeboot: "#b07ad9", app0: "#2563eb", spiffs: "#0d9488"};
function fmNiveau(pc) { return pc >= 95 ? "r" : pc >= 90 ? "o" : ""; }
function fmPc(u, t) { return t ? 100 * u / t : 0; }
function fmKo(o) { var k = o / 1024; return k >= 1024 ? (k / 1024).toFixed(2).replace(".", ",") + " Mo" : Math.round(k) + " Ko"; }
// Chiffres de la pastille : null si aucune partition mesuree (pas de pastille)
function fmResume(a) {
  var mes = ((a && a.partitions) || []).filter(function (p) { return p.utilise != null && p.taille; });
  if (!mes.length) return null;
  var u = 0, t = 0, pire = 0;
  mes.forEach(function (p) { u += p.utilise; t += p.taille; pire = Math.max(pire, fmPc(p.utilise, p.taille)); });
  var ram = (a.ram || []).filter(function (z) { return z.total; });
  var z = ram.filter(function (x) { return x.zone === "DIRAM"; })[0] || ram[0];
  ram.forEach(function (x) { pire = Math.max(pire, fmPc(x.utilise, x.total)); });
  return {niveau: fmNiveau(pire), texte: "Flash " + Math.round(fmPc(u, t)) + " %"
          + (z ? " · RAM " + Math.round(fmPc(z.utilise, z.total)) + " %" : "") + (pire >= 90 ? " ⚠" : "")};
}
async function finMemoireCharge(e) {
  delete FM[e.env];                  // releve d'un lancement precedent : jamais montre pour celui-ci
  if (e.resultat !== "succes" || !e.statuts || e.statuts.compiler !== "succes") return;
  var r = await appel("/memoire?env=" + encodeURIComponent(e.env));
  if (!r.ok || !fmResume(r.donnees)) return;
  FM[e.env] = r.donnees;
  planifie(e.env);
}
function finMemoireTete(tete, env) {
  var a = FM[env], res = a && fmResume(a);
  if (!res || !L || !L.blocs[env] || L.blocs[env].statut !== "succes") return;
  tete.appendChild(h("button", {"class": "fm-pastille " + res.niveau, type: "button", texte: res.texte,
    title: "Occupation des partitions d'après ce build : ouvrir le détail", onclick: function () { finMemoireOuvre(env); }}));
}
function finMemoireLigne(nom, u, t, estime) {
  var pc = u == null ? 0 : fmPc(u, t);
  return h("div", {"class": "fm-ligne"}, h("span", {texte: nom}),
    h("div", {"class": "fm-piste"}, h("i", {"class": fmNiveau(pc), style: "width:" + Math.min(100, pc) + "%"})),
    h("span", {texte: u == null ? "non mesurable" : (estime ? "≈ " : "") + fmKo(u) + " / " + fmKo(t) + " · " + pc.toFixed(1).replace(".", ",") + " %"}));
}
function finMemoireOuvre(env) {
  var a = FM[env], res = a && fmResume(a);
  if (!res) return;
  var parts = a.partitions, somme = parts.reduce(function (s, p) { return s + p.taille; }, 0);
  var fenetre = h("div", {"class": "fm-fenetre", role: "dialog", "aria-modal": "true", "aria-label": "Occupation des partitions de " + env},
    h("h2", {}, h("span", {texte: env}), h("span", {"class": "fm-pastille " + res.niveau, texte: res.texte})));
  parts.concat((a.ram || []).map(function (z) { return {nom: z.zone, utilise: z.utilise, taille: z.total}; })).forEach(function (p) {
    var pc = p.utilise == null ? 0 : fmPc(p.utilise, p.taille);
    if (pc >= 90) fenetre.appendChild(h("div", {"class": "fm-alerte " + fmNiveau(pc), texte: "⚠ " + p.nom + " occupée à "
      + pc.toFixed(1).replace(".", ",") + " % : reste " + fmKo(p.taille - p.utilise) + "."}));
  });
  var ruban = h("div", {"class": "fm-ruban"});
  parts.forEach(function (p) {
    ruban.appendChild(h("span", {style: "width:" + (100 * p.taille / somme) + "%;background:" + (FM_COUL[p.nom] || "#6b7280"), title: p.nom, texte: p.nom}));
  });
  fenetre.appendChild(ruban);
  parts.forEach(function (p) { fenetre.appendChild(finMemoireLigne(p.nom, p.utilise, p.taille, p.estime)); });
  if ((a.ram || []).length) fenetre.appendChild(h("div", {"class": "fm-titre", texte: "RAM"}));
  (a.ram || []).forEach(function (z) { fenetre.appendChild(finMemoireLigne(z.zone, z.utilise, z.total, false)); });
  var voile = h("div", {"class": "fm-voile"}, fenetre);
  function ferme() { document.removeEventListener("keydown", touche); voile.remove(); }
  function touche(ev) { if (ev.key === "Escape") ferme(); }
  voile.onclick = function (ev) { if (ev.target === voile) ferme(); };
  document.addEventListener("keydown", touche);
  fenetre.appendChild(h("div", {"class": "fm-pied"},
    h("button", {"class": "btn", type: "button", texte: "Onglet Mémoire", onclick: function () { ferme(); mOuvre(env); }}),
    h("button", {"class": "btn p", type: "button", texte: "Fermer", onclick: ferme})));
  document.body.appendChild(voile);
}
"""
