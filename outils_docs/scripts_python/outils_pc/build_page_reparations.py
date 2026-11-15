"""Reparations de la page Build (plan build-reparations A5) : bandeau « Reparation en cours », boutons du choix, panneau « Reparations ».

Insere dans build_page.PAGE par trois reperes (CSS_REPARATIONS, REPARATIONS, JS_REPARATIONS) et un appel,
`reparationsEvenement(e)`, dans `traite()` de la page. L'etat est reconstruit au rechargement par les evenements REJOUES
du flux (`reparation`, `choix_reparation`, formats : docstring de build_serie.py), sans autre requete que :
    GET  /reparations              regles (base + locales) et historique de la serie (titres, panneau)
    POST /reparation {env, choix}  reponse fermer | attendre | annuler a un choix ouvert (ce PC seulement)
    POST /reparations/supprime {id} retire une regle LOCALE (le bouton n'existe que pour elle)
    POST /reparations/diagnostic {env}        « Faire diagnostiquer par l'IA » (env en echec sans reparation ; ce PC seulement)
    POST /reparations/appliquer {env, regle}  « Appliquer et relancer » (la regle proposee, revalidee par le serveur)
Tout texte vient du serveur (processus, ligne de commande, titres) : il passe par h(..., {texte}) = textContent, jamais innerHTML.
"""

CSS = r"""
  #rep-panneau{margin-top:10px}
  #rep-panneau summary{cursor:pointer;font-weight:600}
  .rep-regle{border:1px solid var(--bord);background:var(--carte);border-radius:6px;padding:6px 10px;margin-top:6px;font-size:13px;
    display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
  .rep-regle code{overflow-wrap:anywhere;font-size:12px;color:var(--doux)}
  .rep-regle .corps{flex:1 1 320px;min-width:0}
  .rep-regle .origine{font-size:11px;border:1px solid var(--bord);border-radius:10px;padding:0 7px;color:var(--doux)}
  .rep-ia{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
  .rep-ia code{overflow-wrap:anywhere;font-size:12px;color:var(--doux)}
  .rep-histo{font-size:12px;color:var(--doux);margin-top:6px;overflow-wrap:anywhere}
"""

HTML = r"""
    <div id="rep-bandeaux"></div>
    <details id="rep-panneau"><summary id="rep-resume">Réparations</summary><div id="rep-corps" class="vide">Lecture du catalogue…</div></details>
"""

JS = r"""
// ---------- reparations : bandeaux (etat par env, rejoue avec le flux) et panneau ----------
var R = {}, repRegles = {}, repListe = null, repMin = null, repMessage = "";
function repEnv(env) { return R[env] || (R[env] = {etat: "", regle: "", message: "", choix: null}); }
function reparationsEvenement(e) {
  if (e.type === "debut") { if (e.env === null) R = {}; else delete R[e.env]; }
  else if (e.type === "reparation") {
    var c = repEnv(e.env);
    c.etat = e.etat; c.regle = e.regle || ""; c.message = e.message || ""; c.choix = null;   // la reponse (ou l'echec) clot le choix
    if (c.regle && !repRegles[c.regle]) repCharge();
  } else if (e.type === "choix_reparation") {
    repEnv(e.env).choix = {regle: e.regle, texte: e.texte || "", boutons: e.boutons || [], envoi: false, erreur: ""};
  } else if (e.type === "fin_env") { var f = repEnv(e.env); f.choix = null; f.echec = e.resultat === "echec"; }
  else return;
  if (!repMin) repMin = setTimeout(function () { repMin = null; dessineRep(); }, 50);
}
function repTitre(c) { var r = repRegles[c.regle]; return r ? r.titre : (c.regle || c.message); }
function dessineRep() {
  var zone = $("rep-bandeaux");
  zone.textContent = "";
  Object.keys(R).forEach(function (env) {
    var c = R[env];
    if (c.choix) { zone.appendChild(bandeauChoix(env, c)); return; }
    if (c.echec && !c.etat) { zone.appendChild(bandeauIA(env, c)); return; }
    if (!c.etat) return;
    var fait = c.etat === "reussie", rate = c.etat === "echouee";
    zone.appendChild(h("div", {"class": "bandeau " + (rate ? "avertissement" : "attente"), "data-env": env, "data-etat": c.etat},
      h("b", {texte: (fait ? "Réparation réussie : " : rate ? "Réparation échouée : " : "Réparation en cours : ") + repTitre(c)}),
      h("span", {texte: env + (c.message ? " · " + c.message : "")})));
  });
  var corps = $("rep-corps");
  if (!repListe) return;
  corps.textContent = ""; corps.className = "";
  $("rep-resume").textContent = "Réparations (" + repListe.regles.length + " règle" + (repListe.regles.length > 1 ? "s" : "") + ")";
  (repListe.avertissements || []).forEach(function (a) { corps.appendChild(h("div", {"class": "bandeau avertissement", texte: a})); });
  if (repMessage) corps.appendChild(h("div", {"class": "bandeau avertissement", texte: repMessage}));
  repListe.regles.forEach(function (r) {
    var ligne = h("div", {"class": "rep-regle", "data-id": r.id},
      h("div", {"class": "corps"}, h("b", {texte: r.titre}), " ", h("span", {"class": "origine", texte: r.origine}),
        h("div", {}, h("code", {texte: r.id + " · étapes : " + (r.etapes || []).join(", ") + " · actions : " +
          (r.actions || []).map(function (a) { return a.action; }).join(", ")})),
        h("div", {}, h("code", {texte: r.motif}))));
    if (r.supprimable) ligne.appendChild(h("button", {"class": "btn", type: "button", texte: "Supprimer", "data-supprime": r.id,
      onclick: function () { repSupprime(r.id); }}));
    corps.appendChild(ligne);
  });
  if (!repListe.regles.length) corps.appendChild(h("div", {"class": "vide", texte: "Aucune règle."}));
  if ((repListe.historique || []).length)
    corps.appendChild(h("div", {"class": "rep-histo", texte: "Cette série : " + repListe.historique.map(function (x) {
      return x.env + " " + x.regle + " " + x.etat; }).join(" · ")}));
}
async function repCharge() {
  var r = await appel("/reparations");
  if (!r.ok || !r.donnees) { repMessage = "Catalogue illisible : " + (r.texte || "HTTP " + r.statut).slice(0, 200); repListe = repListe || {regles: []}; }
  else {
    repMessage = ""; repListe = r.donnees; repRegles = {};
    repListe.regles.forEach(function (x) { repRegles[x.id] = x; });
  }
  dessineRep();
}
async function repSupprime(id) {
  var r = await appel("/reparations/supprime", {id: id});
  repMessage = r.ok ? "" : "Suppression refusée : " + (r.texte || "HTTP " + r.statut).slice(0, 200);
  await repCharge();
}
function bandeauChoix(env, c) {
  var k = c.choix, noms = {fermer: "Fermer le processus", attendre: "Attendre", annuler: "Annuler"};
  var boutons = k.boutons.map(function (nom) {
    var b = h("button", {"class": nom === "fermer" ? "btn p" : "btn", type: "button", texte: noms[nom] || nom, "data-choix": nom,
      onclick: function () { repRepond(env, nom); }});
    b.disabled = k.envoi;
    return b;
  });
  var zoneBoutons = h("span", {"class": "choix"});
  boutons.forEach(function (b) { zoneBoutons.appendChild(b); });
  return h("div", {"class": "bandeau carte", "data-env": env, "data-choix-ouvert": "1"},
    h("b", {texte: "Réparation de " + env + " : " + repTitre({regle: k.regle})}),
    h("span", {texte: k.texte}),
    k.erreur ? h("span", {"class": "erreur", texte: k.erreur}) : null,
    zoneBoutons);
}
async function repRepond(env, nom) {
  var k = R[env] && R[env].choix;
  if (!k || k.envoi) return;
  k.envoi = true; k.erreur = "";
  dessineRep();
  var r = await appel("/reparation", {env: env, choix: nom});
  // reponse acceptee : le choix se clot par le prochain evenement `reparation` ; refusee : boutons rendus
  if (!r.ok) { k.envoi = false; k.erreur = "Réponse refusée : " + (r.texte || "HTTP " + r.statut).slice(0, 200); }
  dessineRep();
}
function bandeauIA(env, c) {
  var d = c.diag || {}, x = d.donnees, el = h("div", {"class": "bandeau carte rep-ia", "data-env": env, "data-ia": d.etat || "libre"});
  el.appendChild(h("b", {texte: "Échec de " + env + " : aucune réparation connue"}));
  if (d.etat === "attente") el.appendChild(h("span", {texte: "Diagnostic en cours (jusqu'à 5 min)…"}));
  else if (d.etat === "applique") el.appendChild(h("span", {texte: d.message}));
  else {
    var b = h("button", {"class": "btn", type: "button", texte: "Faire diagnostiquer par l'IA", "data-diagnostic": env,
      onclick: function () { repDiagnostic(env); }});
    el.appendChild(b);
  }
  if (d.erreur) el.appendChild(h("span", {"class": "erreur", texte: d.erreur}));
  if (x) {
    if (x.cause) el.appendChild(h("span", {"data-ia-cause": "1", texte: "Cause : " + x.cause}));
    if (x.explication) el.appendChild(h("span", {texte: x.explication}));
    if (x.refus) el.appendChild(h("span", {"class": "erreur", texte: x.refus}));
    if (x.correctif_manuel) el.appendChild(h("span", {texte: "À faire à la main : " + x.correctif_manuel}));
    if (x.regle && d.etat !== "applique") {
      el.appendChild(h("code", {texte: x.regle.titre + " · " + x.regle.motif + " · " + x.regle.actions.map(function (a) {
        return a.action + (a.parametres && a.parametres.secondes !== undefined ? " " + a.parametres.secondes + " s" : ""); }).join(", ")}));
      el.appendChild(h("button", {"class": "btn p", type: "button", texte: "Appliquer et relancer", "data-applique": env,
        onclick: function () { repApplique(env); }}));
    }
  }
  return el;
}
async function repDiagnostic(env) {
  var c = repEnv(env);
  c.diag = {etat: "attente"}; dessineRep();
  var r = await appel("/reparations/diagnostic", {env: env}, 330000);
  if (!r.ok || !r.donnees) c.diag = {etat: "erreur", erreur: "Diagnostic refusé : " + (r.texte || "HTTP " + r.statut).slice(0, 200)};
  else c.diag = {etat: "fait", donnees: r.donnees, erreur: r.donnees.ok ? "" : r.donnees.erreur};
  dessineRep();
}
async function repApplique(env) {
  var c = repEnv(env), x = c.diag && c.diag.donnees;
  if (!x || !x.regle) return;
  var r = await appel("/reparations/appliquer", {env: env, regle: x.regle});
  if (!r.ok) { c.diag.erreur = "Application refusée : " + (r.texte || "HTTP " + r.statut).slice(0, 200); }
  else { c.diag.etat = "applique"; c.diag.erreur = "";
    c.diag.message = (r.donnees && r.donnees.attend) ? "En attente de la fin de la série, puis relance de l'env…" : "Actions de la règle puis relance de l'env…"; }
  dessineRep();
}
$("rep-panneau").addEventListener("toggle", function () { if (this.open) repCharge(); });
"""
