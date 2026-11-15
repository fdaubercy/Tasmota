"""Page « Menage du depot » (menage_web.py) : parametres de l'audit, lancement, propositions avec preuve et risque, « garder » / « ignorer ».

Tout ce qui vient du serveur ou de l'agent (chemins, constats, preuves, messages) s'affiche par textContent, jamais par innerHTML.
La page n'ecrit rien dans le depot : « Garder » memorise un chemin cote serveur (hors depot), « Ignorer » ne vaut que pour cet audit.
Un compteur de generation (S.gen) ecarte une reponse de /rapport depassee par un nouvel audit.
Sonde : test_menage_page_chrome.py.
"""

CSS = """
:root{color-scheme:light;--fond:#f6f7f9;--carte:#fff;--bord:#ddd;--texte:#222;--doux:#666;--bleu:#2563eb;--vert:#1e7e3a;
  --orange:#a86400;--rouge:#c0392b;--btn:#fff;--btn-bord:#888;--piste:#e9e9ea;--orange-fond:#fff4e0;--vert-fond:#e3f4e8;
  --rouge-fond:#fdecea;--champ:#fff;--sur-bleu:#fff;--interrupteur:#fff;--interrupteur-on:#34c759;--ombre:rgba(0,0,0,.3)}
:root[data-theme="sombre"]{color-scheme:dark;--fond:#121417;--carte:#1d2025;--bord:#3a3f47;--texte:#e6e6e6;--doux:#a8adb5;
  --bleu:#5b93ff;--vert:#3fbf63;--orange:#f0a020;--rouge:#ff6b5b;--btn:#262a30;--btn-bord:#555b64;--piste:#39393d;
  --orange-fond:#33270f;--vert-fond:#16301f;--rouge-fond:#3a1d1a;--champ:#15171b;--sur-bleu:#0b0d10}
*{box-sizing:border-box}
body{margin:0;font:14px system-ui,sans-serif;color:var(--texte);background:var(--fond)}
main{max-width:1200px;margin:0 auto;padding:12px 16px 24px}
header{display:flex;align-items:baseline;gap:14px;margin-bottom:10px;flex-wrap:wrap}
h1{font-size:20px;margin:0} h2{font-size:15px;margin:0 0 8px}
.theme{margin-left:auto;align-self:center;display:flex;align-items:center;gap:8px;font-size:13px;color:var(--doux);cursor:pointer;user-select:none}
.theme input{position:absolute;opacity:0;width:1px;height:1px;margin:0}
.interrupteur{position:relative;flex:none;width:2.6em;height:1.5em;border-radius:.75em;background:var(--piste);transition:background .2s}
.interrupteur::after{content:"";position:absolute;top:.15em;left:.15em;width:1.2em;height:1.2em;border-radius:50%;background:var(--interrupteur);
  box-shadow:0 1px 3px var(--ombre);transition:transform .2s}
.theme input:checked + .interrupteur{background:var(--interrupteur-on)}
.theme input:checked + .interrupteur::after{transform:translateX(1.1em)}
.theme input:focus-visible + .interrupteur{outline:2px solid var(--bleu);outline-offset:2px}
.doux{color:var(--doux)} .petit{font-size:12px} [hidden]{display:none!important}
.colonnes{display:grid;grid-template-columns:290px minmax(0,1fr);gap:12px;align-items:start}
@media (max-width:760px){.colonnes{grid-template-columns:minmax(0,1fr)}}
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:12px;margin-bottom:12px;min-width:0}
.btn{display:inline-block;padding:6px 12px;border:1px solid var(--btn-bord);border-radius:6px;background:var(--btn);font:inherit;color:inherit;cursor:pointer}
.btn.prim{background:var(--bleu);border-color:var(--bleu);color:var(--sur-bleu)} .btn:disabled{opacity:.45;cursor:default}
.ligne{display:flex;gap:8px;align-items:center;margin:6px 0;flex-wrap:wrap}
label.ch{display:flex;gap:6px;align-items:flex-start;margin:4px 0}
label.ch input{margin-top:3px;flex:none}
.resume{margin:4px 0;padding-left:20px} #plan h3{font-size:13px;margin:10px 0 4px} #plan ul{margin:2px 0;padding-left:18px;font-size:12px}
.groupe>summary{font-size:12px;margin-bottom:2px} .champ{display:block;margin:8px 0} .champ span{display:block;font-size:12px;color:var(--doux);margin-bottom:2px}
input[type=number],select{font:inherit;padding:5px 7px;border:1px solid var(--bord);border-radius:5px;background:var(--champ);color:var(--texte);width:100%}
.etat{padding:8px 10px;border-radius:6px;background:var(--piste);margin-top:8px;overflow-wrap:anywhere}
.detail{margin-top:8px} .detail pre{max-height:180px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;margin:6px 0 0}
.suivi{border-color:var(--bleu)} .suivi h2{display:flex;gap:8px;align-items:center}
.maintenant{font-size:14px;min-height:2.6em;overflow-wrap:anywhere} .maintenant .o{color:var(--bleu);font-weight:600}
.pastille{display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--bleu);animation:pulse 1.2s ease-in-out infinite}
@keyframes pulse{50%{opacity:.25}} @media (prefers-reduced-motion:reduce){.pastille{animation:none}}
.couv-ligne{display:flex;gap:10px;align-items:flex-start;margin:6px 0} .couv-ligne .badge{flex:none;min-width:84px;text-align:center}
#limites-bloc h3{font-size:13px;margin:10px 0 2px} #limites-bloc ul{margin:0;padding-left:18px} #brut pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}
.avance{margin-top:8px} .barre{height:8px;border-radius:4px;background:var(--piste);overflow:hidden}
.rempli{height:100%;width:0;background:var(--bleu);transition:width .6s ease}
.journal{margin-top:8px;max-height:240px;overflow:auto;padding:6px 8px;border:1px solid var(--bord);border-radius:6px;background:var(--champ);
  font:12px/1.45 ui-monospace,Consolas,monospace}
.journal div{overflow-wrap:anywhere} .journal .t{color:var(--doux)} .journal .o{color:var(--bleu);font-weight:600}
.etat.ok{background:var(--vert-fond);color:var(--vert)} .etat.ko{background:var(--rouge-fond);color:var(--rouge)} .etat.en{background:var(--orange-fond);color:var(--orange)}
.prop{border:1px solid var(--bord);border-radius:6px;padding:8px 10px;margin:8px 0;background:var(--carte)}
.prop.encours{opacity:.75}
.chemin{font:13px ui-monospace,Consolas,monospace;overflow-wrap:anywhere;font-weight:600}
.badge{display:inline-block;font-size:11px;padding:1px 7px;border-radius:10px;border:1px solid var(--bord);margin-right:4px}
.badge.faible{background:var(--vert-fond);color:var(--vert)} .badge.moyen{background:var(--orange-fond);color:var(--orange)} .badge.eleve{background:var(--rouge-fond);color:var(--rouge)}
.prop p{margin:6px 0;overflow-wrap:anywhere}
details summary{cursor:pointer;color:var(--doux);font-size:12px}
pre{margin:4px 0;white-space:pre-wrap;overflow-wrap:anywhere;font:12px ui-monospace,Consolas,monospace}
.actions{display:flex;gap:8px;margin-top:6px;flex-wrap:wrap}
"""

HTML = """
<main>
<header><h1>Ménage du dépôt</h1><span class="doux petit">Propositions de rangement : rien n'est déplacé ni supprimé dans le dépôt.</span>
<label class="theme"><span>Mode sombre</span><input type="checkbox" id="theme"><span class="interrupteur"></span></label></header>
<div class="colonnes">
<div>
 <section class="carte"><h2>Paramètres de l'audit</h2>
  <details class="champ groupe" open><summary>Dossiers à examiner <span class="doux" id="n-zone"></span></summary><div id="p-zone"></div></details>
  <details class="champ groupe" open><summary>Contrôles <span class="doux" id="n-cat"></span></summary><div id="p-cat"></div></details>
  <label class="champ"><span>Travail « en cours » : modifié ou touché depuis moins de (jours)</span><input type="number" id="p-jours" min="0" max="365" value="3"></label>
  <label class="champ"><span>Modèle</span><select id="p-modele"></select></label>
  <label class="champ"><span>Effort</span><select id="p-effort"></select></label>
  <label class="champ"><span>Budget estimé de l'audit (1 à 20, quota de l'abonnement)</span><input type="number" id="p-budget" min="1" max="20" value="8"></label>
  <div class="ligne"><button class="btn prim" id="b-lance">Lancer l'audit</button><button class="btn" id="b-stop" disabled>Arrêter</button></div>
  <div class="etat" id="etat" role="status">Prêt.</div>
  <details class="detail" id="detail" hidden><summary>Détail technique (texte d'origine de claude, en anglais)</summary><pre id="detail-texte"></pre></details>
 </section>
 <section class="carte"><h2>Gardés <span class="doux petit" id="n-gardes"></span></h2>
  <p class="doux petit">Chemins à ne plus se voir proposer (mémorisés hors du dépôt).</p><div id="gardes"></div></section>
</div>
<div>
<section class="carte suivi" id="suivi" hidden aria-live="polite"><h2 id="suivi-titre">Audit en cours</h2>
 <div class="maintenant" id="maintenant"></div>
 <div class="avance" id="avance"><div class="barre" role="progressbar" aria-valuemin="0" aria-valuemax="100" id="barre"><div class="rempli" id="rempli"></div></div>
  <div class="doux petit" id="pct"></div></div>
 <div class="journal" id="journal" tabindex="0" aria-label="Actions de l'agent en direct"></div>
</section>
<section class="carte" id="couverture" hidden><h2>Couverture de l'audit <span class="doux petit" id="n-couv"></span></h2>
 <p class="doux petit">Ce que l'agent a vraiment contrôlé, et ce qu'il n'a pas pu faire.</p>
 <div id="couv"></div>
 <div id="limites-bloc"></div>
 <div class="ligne"><button class="btn" id="b-refaire" hidden>Cocher les contrôles à refaire</button></div>
 <details id="brut" hidden><summary>Texte brut de l'agent</summary><pre id="brut-texte"></pre></details>
</section>
<section class="carte"><h2>Propositions <span class="doux petit" id="n-props"></span></h2>
 <ul id="resume" class="doux resume"></ul>
 <div id="plan" hidden></div>
 <div class="ligne">
  <label>Catégorie <select id="f-cat"><option value="">toutes</option></select></label>
  <label>Risque <select id="f-risque"><option value="">tous</option><option>faible</option><option>moyen</option><option>eleve</option></select></label>
  <button class="btn" id="b-copie" disabled>Copier la liste</button>
 </div>
 <div id="props"><p class="doux">Aucun audit pour le moment.</p></div>
 <details id="encours" hidden><summary>En cours, à ne pas toucher (<span id="n-encours">0</span>)</summary><div id="props-encours"></div></details>
</section>
</div>
</div>
</main>
"""

JS = r"""
"use strict";
var S = {gen: 0, rapport: null, options: null, scrute: null, recu: 0, derniere: null, demandes: null, arefaire: []};
function $(id) { return document.getElementById(id); }
function vide(n) { while (n.firstChild) n.removeChild(n.firstChild); }
function el(tag, classe, texte) { var e = document.createElement(tag); if (classe) e.className = classe; if (texte != null) e.textContent = texte; return e; }
function api(methode, chemin, corps) {
  var opt = {method: methode, headers: {"Content-Type": "application/json"}};
  if (methode === "POST") { opt.headers["X-Menage"] = "1"; opt.body = JSON.stringify(corps || {}); }
  return fetch(chemin, opt).then(function (r) {
    return r.text().then(function (t) {
      var d = null; try { d = JSON.parse(t); } catch (e) {}
      return {ok: r.ok, statut: r.status, texte: t, donnees: d};
    });
  }, function (e) { return {ok: false, statut: 0, texte: "serveur injoignable : " + e, donnees: null}; });
}
function message(classe, texte) { var e = $("etat"); e.className = "etat " + (classe || ""); e.textContent = texte; }
function memo(cle, valeur) {
  try { if (valeur === undefined) return JSON.parse(localStorage.getItem("menage-" + cle)); localStorage.setItem("menage-" + cle, JSON.stringify(valeur)); } catch (e) {}
  return null;
}

var LIBELLES = {orphelin: "Orphelins : fichiers que plus rien n'utilise", reste: "Restes : .bak, copies, anciens exports",
  hors_dossier: "Classement : fichiers mal rangés", doublon: "Doublons : fichiers identiques", taille: "Taille : fichiers proches de 500 lignes",
  poids: "Poids : plus gros fichiers du dépôt", vide: "Dossiers vides et grosses images"};
var ETATS = {fait: ["faible", "✓ Fait"], partiel: ["moyen", "◐ Partiel"], non_fait: ["eleve", "✗ Non fait"], non_declare: ["", "? Non déclaré"]};

function liste(titre, textes) {
  var z = $("limites-bloc");
  if (!textes || !textes.length) return;
  z.appendChild(el("h3", null, titre));
  var u = el("ul"); textes.forEach(function (t) { u.appendChild(el("li", null, t)); }); z.appendChild(u);
}
function rendCouverture(r) {
  var z = $("couv"), lb = $("limites-bloc"); vide(z); vide(lb);
  var cov = r.couverture || [], demandes = S.demandes || [];   // inconnues apres un rechargement : pas de « non declare » devine d'apres les cases du moment
  var parC = {}; cov.forEach(function (c) { parC[c.controle] = c; });
  var lignes = Object.keys(LIBELLES).filter(function (k) { return parC[k] || demandes.indexOf(k) >= 0; }).map(function (k) {
    return parC[k] || {controle: k, etat: "non_declare", note: "L'agent n'a rien dit sur ce contrôle."};
  });
  var arefaire = [];
  lignes.forEach(function (c) {
    var e = ETATS[c.etat], l = el("div", "couv-ligne");
    l.appendChild(el("span", "badge " + e[0], e[1]));
    var t = el("div"); t.appendChild(el("strong", null, LIBELLES[c.controle])); if (c.note) t.appendChild(el("div", "doux", c.note));
    l.appendChild(t); z.appendChild(l);
    if (c.etat !== "fait") arefaire.push(c.controle);
  });
  var faits = lignes.filter(function (c) { return c.etat === "fait"; }).length;
  $("n-couv").textContent = lignes.length ? "(" + faits + " contrôle(s) sur " + lignes.length + " menés jusqu'au bout)" : "";
  liste("Ce qui a gêné l'agent", r.limites); liste("Écarté volontairement", r.ecartes);
  var b = $("b-refaire"); b.hidden = !arefaire.length; S.arefaire = arefaire;
  $("brut").hidden = !(r.non_verifie && !cov.length); $("brut-texte").textContent = r.non_verifie || "";
  $("couverture").hidden = !(lignes.length || (r.limites || []).length || (r.ecartes || []).length || r.non_verifie);
}
function refaire() {
  var a = S.arefaire || [];
  document.querySelectorAll("#p-cat input").forEach(function (c) { c.checked = a.indexOf(c.value) >= 0; });
  memorise(); $("b-lance").scrollIntoView({block: "center"});
  message("", "Contrôles à refaire cochés : relancez l'audit pour les mener (vous pouvez aussi choisir un modèle moins coûteux).");
}

function cases(conteneur, valeurs, cochees, nom) {
  vide(conteneur);
  valeurs.forEach(function (v) {
    var l = el("label", "ch"), c = document.createElement("input");
    c.type = "checkbox"; c.value = v; c.checked = !cochees || cochees.indexOf(v) >= 0; c.setAttribute("data-groupe", nom);
    l.appendChild(c); l.appendChild(el("span", null, (nom === "cat" && LIBELLES[v]) || v)); conteneur.appendChild(l);
  });
}
function coches(conteneur) {
  return Array.prototype.filter.call(conteneur.querySelectorAll("input"), function (c) { return c.checked; }).map(function (c) { return c.value; });
}
function remplitSelect(s, valeurs, choisie) {
  vide(s); valeurs.forEach(function (v) { var o = el("option", null, v); o.value = v; s.appendChild(o); }); s.value = choisie;
}

function parametres() {
  return {zone: coches($("p-zone")), categories: coches($("p-cat")), anciennete_jours: parseInt($("p-jours").value, 10),
          modele: $("p-modele").value, effort: $("p-effort").value, budget: parseInt($("p-budget").value, 10)};
}
function comptes() {
  [["p-zone", "n-zone"], ["p-cat", "n-cat"]].forEach(function (g) {
    var t = $(g[0]).querySelectorAll("input"); $(g[1]).textContent = t.length ? "(" + coches($(g[0])).length + "/" + t.length + ")" : "";
  });
}
function memorise() { comptes(); memo("params", parametres()); }

function chargeOptions() {
  return api("GET", "/options").then(function (r) {
    if (!r.ok) { message("ko", "Options illisibles : " + r.texte); return; }
    S.options = r.donnees;
    var m = memo("params") || r.donnees.defauts;
    cases($("p-zone"), r.donnees.zones, m.zone, "zone");
    cases($("p-cat"), r.donnees.categories, m.categories, "cat");
    $("p-jours").value = m.anciennete_jours; $("p-budget").value = m.budget || 8;
    remplitSelect($("p-modele"), r.donnees.modeles, m.modele);
    remplitSelect($("p-effort"), r.donnees.efforts, m.effort);
    var f = $("f-cat"); r.donnees.categories.forEach(function (c) { var o = el("option", null, c); o.value = c; f.appendChild(o); });
    ["p-zone", "p-cat"].forEach(function (id) { $(id).onchange = memorise; });
    ["p-jours", "p-budget", "p-modele", "p-effort"].forEach(function (id) { $(id).onchange = memorise; });
    comptes();
  });
}

function chargeGardes() {
  return api("GET", "/gardes").then(function (r) {
    var z = $("gardes"); vide(z);
    var liste = (r.donnees && r.donnees.gardes) || [];
    $("n-gardes").textContent = "(" + liste.length + ")";
    if (!liste.length) z.appendChild(el("p", "doux petit", "Aucun."));
    liste.forEach(function (c) {
      var l = el("div", "ligne"); l.appendChild(el("span", "chemin", c));
      var b = el("button", "btn", "Retirer"); b.onclick = function () {
        api("POST", "/degarder", {chemin: c}).then(function (x) { if (!x.ok) message("ko", x.texte); chargeGardes(); chargeRapport(); });
      };
      l.appendChild(b); z.appendChild(l);
    });
  });
}

function propositionVue(p) {
  var d = el("div", "prop" + (p.en_cours ? " encours" : ""));
  d.appendChild(el("div", "chemin", p.chemin));
  var b = el("div"); b.appendChild(el("span", "badge", p.categorie)); b.appendChild(el("span", "badge " + p.risque, "risque " + p.risque));
  b.appendChild(el("span", "badge", "→ " + p.action + (p.vers ? " vers " + p.vers : ""))); d.appendChild(b);
  var v = p.verif;
  if (v && v.disponible) {
    var vb = el("div", "verif");
    vb.appendChild(el("span", "doux petit", "Vérifié par git : "));
    if (v.perimee) vb.appendChild(el("span", "badge eleve", "périmée : le chemin n'existe plus"));
    if (v.modifie) vb.appendChild(el("span", "badge moyen", v.suivi ? "modifié : en cours" : "non suivi : en cours"));
    if (v.n_code) vb.appendChild(el("span", "badge eleve", "référencé par " + v.n_code + " fichier(s) de code ou de config"));
    if (v.n_docs) vb.appendChild(el("span", "badge moyen", v.n_docs + " document(s) le citent"));
    if (v.destination_existe) vb.appendChild(el("span", "badge eleve", "la destination existe déjà"));
    if (p.risque_agent) vb.appendChild(el("span", "badge", "risque relevé (agent : " + p.risque_agent + ")"));
    if (!v.perimee && !v.n_code && !v.n_docs) vb.appendChild(el("span", "badge faible", "aucun renvoi trouvé"));
    d.appendChild(vb);
  } else if (v) {
    d.appendChild(el("div", "doux petit", "Contre-vérification par git indisponible : " + (v.erreur || "")));
  }
  d.appendChild(el("p", null, p.constat));
  if (v && v.disponible && (v.n_code || v.n_docs)) {
    var rv = el("details", "renvois"); rv.appendChild(el("summary", null, "Renvois trouvés par la page"));
    rv.appendChild(el("pre", null, v.renvois_code.map(function (f) { return "code/config  " + f; }).concat(
      v.renvois_docs.map(function (f) { return "document     " + f; })).join("\n")));
    d.appendChild(rv);
  }
  var c = el("details"); c.appendChild(el("summary", null, "Ce que ça casserait")); c.appendChild(el("pre", null, p.casserait)); d.appendChild(c);
  var pr = el("details"); pr.appendChild(el("summary", null, "Preuve")); pr.appendChild(el("pre", null, p.preuve)); d.appendChild(pr);
  if (!p.en_cours) {
    var a = el("div", "actions");
    var g = el("button", "btn", "Garder"); g.title = "Ne plus jamais proposer ce chemin";
    g.onclick = function () { api("POST", "/garder", {chemin: p.chemin}).then(function (x) { if (!x.ok) message("ko", x.texte); chargeGardes(); chargeRapport(); }); };
    var i = el("button", "btn", "Ignorer cette fois"); i.title = "Masquer jusqu'au prochain audit";
    i.onclick = function () { api("POST", "/ignorer", {id: p.id}).then(function (x) { if (!x.ok) message("ko", x.texte); chargeRapport(); }); };
    a.appendChild(g); a.appendChild(i); d.appendChild(a);
  }
  return d;
}

var ORDRE = {faible: 0, moyen: 1, eleve: 2};
function rendResume(texte) {
  var z = $("resume"); vide(z);
  var lignes = String(texte || "").split(/\n+/);
  if (lignes.length < 2) lignes = lignes[0].split(/(?<=[.;])\s+(?=[A-ZÉÈÀ])/);   // ancien rapport en un paragraphe : une phrase par ligne
  lignes.forEach(function (t) { t = t.replace(/^\s*[-*•]\s*/, "").trim(); if (t) z.appendChild(el("li", null, t)); });
}
var ETAPES = [
  ["sur", "1. À appliquer d'un bloc : aucun fichier ne les cite (vérifié par git)"],
  ["docs", "2. Après mise à jour des renvois dans les documents (même commit, puis verifie_references_docs.py)"],
  ["code", "3. Un par un : cités par du code ou une configuration"],
  ["main", "4. À vérifier à la main : vérification indisponible, chemin disparu ou destination déjà prise"]
];
function etapeDe(p) {
  var v = p.verif;
  if (p.action === "garder") return null;
  if (!v || !v.disponible || v.perimee || v.destination_existe) return "main";
  if (v.n_code) return "code";
  if (v.n_docs) return "docs";
  return "sur";
}
function rendPlan(r) {
  var z = $("plan"); vide(z);
  var groupes = {sur: [], docs: [], code: [], main: []};
  r.propositions.forEach(function (p) { var e = p.en_cours ? null : etapeDe(p); if (e) groupes[e].push(p); });
  var total = 0; ETAPES.forEach(function (e) { total += groupes[e[0]].length; });
  if (!total) return;
  z.appendChild(el("h3", null, "Actions à réaliser, par priorité"));
  ETAPES.forEach(function (e) {
    var l = groupes[e[0]]; if (!l.length) return;
    var d = el("details"); if (e[0] === "sur") d.open = true;
    d.appendChild(el("summary", null, e[1] + " (" + l.length + ")"));
    var u = el("ul"); l.forEach(function (p) { u.appendChild(el("li", null, p.action + " " + p.chemin + (p.vers ? " vers " + p.vers : ""))); });
    d.appendChild(u); z.appendChild(d);
  });
  z.hidden = false;
}
function rend() {
  var r = S.rapport, zone = $("props"), zoneEn = $("props-encours");
  vide(zone); vide(zoneEn);
  if (!r) { zone.appendChild(el("p", "doux", "Aucun audit pour le moment.")); $("encours").hidden = true; vide($("resume")); $("plan").hidden = true;
            $("couverture").hidden = true; $("n-props").textContent = ""; $("b-copie").disabled = true; return; }
  var cat = $("f-cat").value, risque = $("f-risque").value;
  var tri = r.propositions.filter(function (p) { return (!cat || p.categorie === cat) && (!risque || p.risque === risque); })
    .sort(function (a, b) { return ORDRE[a.risque] - ORDRE[b.risque]; });
  var actives = tri.filter(function (p) { return !p.en_cours; }), en = tri.filter(function (p) { return p.en_cours; });
  actives.forEach(function (p) { zone.appendChild(propositionVue(p)); });
  if (!actives.length) zone.appendChild(el("p", "doux", "Aucune proposition."));
  en.forEach(function (p) { zoneEn.appendChild(propositionVue(p)); });
  $("encours").hidden = !en.length; $("n-encours").textContent = String(en.length);
  rendResume(r.resume); rendPlan(r); rendCouverture(r);
  $("n-props").textContent = "(" + actives.length + ")"; $("b-copie").disabled = !actives.length;
}

function chargeRapport() {
  var g = ++S.gen;
  return api("GET", "/rapport").then(function (r) {
    if (g !== S.gen) return;                       // un autre audit ou une autre action est passe : reponse depassee
    S.rapport = r.ok ? r.donnees : null; rend();
  });
}

function duree(s) { return Math.floor(s / 60) + ":" + ("0" + Math.floor(s % 60)).slice(-2); }
function journalise(e) {
  var j = $("journal");
  if (e.appels < S.recu) { vide(j); S.recu = 0; S.derniere = null; }          // nouvel audit : on repart de zero
  var bas = j.scrollHeight - j.scrollTop - j.clientHeight < 30;
  (e.activite || []).forEach(function (a) {
    var l = el("div"); l.appendChild(el("span", "t", duree(a.t) + "  ")); l.appendChild(el("span", "o", a.outil + "  ")); l.appendChild(document.createTextNode(a.detail));
    j.appendChild(l); S.derniere = a;
  });
  S.recu = e.appels;
  var enCours = e.etat === "en_cours";
  $("suivi").hidden = !(enCours || j.childNodes.length > 0);
  if (bas) j.scrollTop = j.scrollHeight;
  var pct = e.etat === "fini" ? 100 : e.progression || 0;
  $("rempli").style.width = pct + "%"; $("barre").setAttribute("aria-valuenow", pct);
  $("pct").textContent = (enCours ? "≈ " + pct + " % (estimation : le nombre d'actions n'est pas connu d'avance) · " : pct + " % · ")
    + e.appels + " action" + (e.appels > 1 ? "s" : "") + (e.debut ? " · " + duree(Math.max(0, Math.round((e.fin || Date.now() / 1000) - e.debut))) : "");
  var t = $("suivi-titre"); vide(t);
  if (enCours) t.appendChild(el("span", "pastille"));
  t.appendChild(document.createTextNode(enCours ? "Audit en cours" : e.etat === "fini" ? "Audit terminé" : "Audit interrompu"));
  var m = $("maintenant"); vide(m);
  if (enCours) {
    if (e.message && e.message !== "audit en cours") m.appendChild(el("span", "o", e.message));          // phase : contre-verification, etc.
    else if (S.derniere) { m.appendChild(document.createTextNode("En ce moment : ")); m.appendChild(el("span", "o", S.derniere.outil + "  ")); m.appendChild(document.createTextNode(S.derniere.detail)); }
    else m.appendChild(document.createTextNode("L'agent démarre et prépare sa première recherche…"));
  }
}

function etat() {
  return api("GET", "/etat?depuis=" + S.recu).then(function (r) {
    if (!r.ok) { message("ko", r.texte); return; }
    var e = r.donnees, enCours = e.etat === "en_cours";
    journalise(e);
    var dt = e.etat === "echec" ? (e.detail || "") : "";
    $("detail").hidden = !dt; $("detail-texte").textContent = dt;
    $("b-lance").disabled = enCours; $("b-stop").disabled = !enCours;
    if (enCours) {
      var s = e.debut ? Math.max(0, Math.round(Date.now() / 1000 - e.debut)) : 0;
      message("en", "Audit en cours depuis " + duree(s) + "… (jusqu'à quelques minutes)");
      if (!S.scrute) S.scrute = setInterval(etat, 1500);
    } else {
      if (S.scrute) { clearInterval(S.scrute); S.scrute = null; }
      if (e.etat === "fini") { message("ok", "Audit terminé : " + e.message + "."); chargeRapport(); }
      else if (e.etat === "echec") message("ko", "L'audit a échoué. " + e.message);
      else message("", "Prêt.");
    }
  });
}

function lance() {
  var p = parametres();
  if (!p.zone.length || !p.categories.length) { message("ko", "Cochez au moins un dossier et un contrôle."); return; }
  if (!(p.budget >= 1 && p.budget <= 20)) { message("ko", "Budget : un nombre de 1 à 20."); return; }
  if (!(p.anciennete_jours >= 0 && p.anciennete_jours <= 365)) { message("ko", "Ancienneté : un nombre de 0 à 365."); return; }
  api("POST", "/lancer", p).then(function (r) {
    if (!r.ok) { message("ko", r.texte); return; }
    S.demandes = p.categories;
    S.gen++; S.rapport = null; rend();
    vide($("journal")); S.recu = 0; S.derniere = null; $("suivi").hidden = false; $("suivi").scrollIntoView({block: "nearest"});
    etat();
  });
}
function arrete() { api("POST", "/arreter", {}).then(function () { etat(); }); }

function copie() {
  var r = S.rapport; if (!r) return;
  var texte = r.propositions.filter(function (p) { return !p.en_cours; }).map(function (p) {
    return p.action + "\t" + p.risque + "\t" + p.chemin + (p.vers ? " -> " + p.vers : "") + "\t" + p.constat;
  }).join("\n");
  function repli() {
    var t = document.createElement("textarea"); t.value = texte; document.body.appendChild(t); t.select();
    try { document.execCommand("copy"); message("ok", "Liste copiée."); } catch (e) { message("ko", "Copie impossible."); }
    document.body.removeChild(t);
  }
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(texte).then(function () { message("ok", "Liste copiée."); }, repli);
  else repli();
}

$("b-lance").onclick = lance;
$("b-refaire").onclick = refaire;
$("b-stop").onclick = arrete;
$("b-copie").onclick = copie;
$("f-cat").onchange = $("f-risque").onchange = rend;
chargeOptions().then(function () { chargeGardes(); etat(); });
"""

THEME_TETE = ("<script>(function () { var t = null; try { t = localStorage.getItem('menage-theme'); } catch (e) {}"
              " if (t !== 'clair' && t !== 'sombre') t = (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches)"
              " ? 'sombre' : 'clair'; document.documentElement.setAttribute('data-theme', t); })();</script>")
THEME_INTERRUPTEUR = ("<script>(function () { var c = document.getElementById('theme');"
                      " c.checked = document.documentElement.getAttribute('data-theme') === 'sombre';"
                      " c.onchange = function () { var t = this.checked ? 'sombre' : 'clair';"
                      " document.documentElement.setAttribute('data-theme', t);"
                      " try { localStorage.setItem('menage-theme', t); } catch (e) {} }; })();</script>")

PAGE = ("<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>Ménage du dépôt</title><link rel=\"icon\" href=\"data:,\">" + THEME_TETE + "<style>" + CSS + "</style></head><body>"
        + HTML + THEME_INTERRUPTEUR + "<script>" + JS + "</script></body></html>")
