"""Page « Menage du depot » (menage_web.py) : parametres de l'audit, lancement, propositions avec preuve et risque, « garder » / « ignorer ».

Tout ce qui vient du serveur ou de l'agent (chemins, constats, preuves, messages) s'affiche par textContent, jamais par innerHTML.
La page n'ecrit rien dans le depot : « Garder » memorise un chemin cote serveur (hors depot), « Ignorer » ne vaut que pour cet audit.
Un compteur de generation (S.gen) ecarte une reponse de /rapport depassee par un nouvel audit.
Sonde : test_menage_page_chrome.py.
"""

CSS = """
:root{color-scheme:light;--fond:#f6f7f9;--carte:#fff;--bord:#ddd;--texte:#222;--doux:#666;--bleu:#2563eb;--vert:#1e7e3a;
  --orange:#a86400;--rouge:#c0392b;--btn:#fff;--btn-bord:#888;--piste:#e9e9ea;--orange-fond:#fff4e0;--vert-fond:#e3f4e8;
  --rouge-fond:#fdecea;--champ:#fff}
:root[data-theme="sombre"]{color-scheme:dark;--fond:#121417;--carte:#1d2025;--bord:#3a3f47;--texte:#e6e6e6;--doux:#a8adb5;
  --bleu:#5b93ff;--vert:#3fbf63;--orange:#f0a020;--rouge:#ff6b5b;--btn:#262a30;--btn-bord:#555b64;--piste:#39393d;
  --orange-fond:#33270f;--vert-fond:#16301f;--rouge-fond:#3a1d1a;--champ:#15171b}
*{box-sizing:border-box}
body{margin:0;font:14px system-ui,sans-serif;color:var(--texte);background:var(--fond)}
main{max-width:1200px;margin:0 auto;padding:12px 16px 24px}
header{display:flex;align-items:baseline;gap:14px;margin-bottom:10px;flex-wrap:wrap}
h1{font-size:20px;margin:0} h2{font-size:15px;margin:0 0 8px}
.theme{margin-left:auto;align-self:center;display:flex;align-items:center;gap:8px;font-size:13px;color:var(--doux);cursor:pointer;user-select:none}
.theme input{position:absolute;opacity:0;width:1px;height:1px;margin:0}
.interrupteur{position:relative;flex:none;width:2.6em;height:1.5em;border-radius:.75em;background:var(--piste);transition:background .2s}
.interrupteur::after{content:"";position:absolute;top:.15em;left:.15em;width:1.2em;height:1.2em;border-radius:50%;background:#fff;
  box-shadow:0 1px 3px rgba(0,0,0,.3);transition:transform .2s}
.theme input:checked + .interrupteur{background:#34c759}
.theme input:checked + .interrupteur::after{transform:translateX(1.1em)}
.theme input:focus-visible + .interrupteur{outline:2px solid var(--bleu);outline-offset:2px}
.doux{color:var(--doux)} .petit{font-size:12px} [hidden]{display:none!important}
.colonnes{display:grid;grid-template-columns:290px minmax(0,1fr);gap:12px;align-items:start}
@media (max-width:760px){.colonnes{grid-template-columns:minmax(0,1fr)}}
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:12px;margin-bottom:12px;min-width:0}
.btn{display:inline-block;padding:6px 12px;border:1px solid var(--btn-bord);border-radius:6px;background:var(--btn);font:inherit;color:inherit;cursor:pointer}
.btn.prim{background:#2563eb;border-color:#2563eb;color:#fff} .btn:disabled{opacity:.45;cursor:default}
.ligne{display:flex;gap:8px;align-items:center;margin:6px 0;flex-wrap:wrap}
label.ch{display:flex;gap:6px;align-items:flex-start;margin:4px 0}
label.ch input{margin-top:3px;flex:none}
.champ{display:block;margin:8px 0} .champ span{display:block;font-size:12px;color:var(--doux);margin-bottom:2px}
input[type=number],select{font:inherit;padding:5px 7px;border:1px solid var(--bord);border-radius:5px;background:var(--champ);color:var(--texte);width:100%}
.etat{padding:8px 10px;border-radius:6px;background:var(--piste);margin-top:8px;overflow-wrap:anywhere}
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
  <div class="champ"><span>Dossiers à examiner</span><div id="p-zone"></div></div>
  <div class="champ"><span>Contrôles</span><div id="p-cat"></div></div>
  <label class="champ"><span>Travail « en cours » : modifié ou touché depuis moins de (jours)</span><input type="number" id="p-jours" min="0" max="365" value="3"></label>
  <label class="champ"><span>Modèle</span><select id="p-modele"></select></label>
  <label class="champ"><span>Effort</span><select id="p-effort"></select></label>
  <div class="ligne"><button class="btn prim" id="b-lance">Lancer l'audit</button><button class="btn" id="b-stop" disabled>Arrêter</button></div>
  <div class="etat" id="etat" role="status">Prêt.</div>
 </section>
 <section class="carte"><h2>Gardés <span class="doux petit" id="n-gardes"></span></h2>
  <p class="doux petit">Chemins à ne plus se voir proposer (mémorisés hors du dépôt).</p><div id="gardes"></div></section>
</div>
<section class="carte"><h2>Propositions <span class="doux petit" id="n-props"></span></h2>
 <p id="resume" class="doux"></p>
 <div class="ligne">
  <label>Catégorie <select id="f-cat"><option value="">toutes</option></select></label>
  <label>Risque <select id="f-risque"><option value="">tous</option><option>faible</option><option>moyen</option><option>eleve</option></select></label>
  <button class="btn" id="b-copie" disabled>Copier la liste</button>
 </div>
 <div id="props"><p class="doux">Aucun audit pour le moment.</p></div>
 <details id="encours" hidden><summary>En cours, à ne pas toucher (<span id="n-encours">0</span>)</summary><div id="props-encours"></div></details>
 <p class="doux petit" id="non-verifie"></p>
</section>
</div>
</main>
"""

JS = r"""
"use strict";
var S = {gen: 0, rapport: null, options: null, scrute: null};
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

function cases(conteneur, valeurs, cochees, nom) {
  vide(conteneur);
  valeurs.forEach(function (v) {
    var l = el("label", "ch"), c = document.createElement("input");
    c.type = "checkbox"; c.value = v; c.checked = !cochees || cochees.indexOf(v) >= 0; c.setAttribute("data-groupe", nom);
    l.appendChild(c); l.appendChild(el("span", null, v)); conteneur.appendChild(l);
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
          modele: $("p-modele").value, effort: $("p-effort").value};
}
function memorise() { memo("params", parametres()); }

function chargeOptions() {
  return api("GET", "/options").then(function (r) {
    if (!r.ok) { message("ko", "Options illisibles : " + r.texte); return; }
    S.options = r.donnees;
    var m = memo("params") || r.donnees.defauts;
    cases($("p-zone"), r.donnees.zones, m.zone, "zone");
    cases($("p-cat"), r.donnees.categories, m.categories, "cat");
    $("p-jours").value = m.anciennete_jours;
    remplitSelect($("p-modele"), r.donnees.modeles, m.modele);
    remplitSelect($("p-effort"), r.donnees.efforts, m.effort);
    var f = $("f-cat"); r.donnees.categories.forEach(function (c) { var o = el("option", null, c); o.value = c; f.appendChild(o); });
    ["p-zone", "p-cat"].forEach(function (id) { $(id).onchange = memorise; });
    ["p-jours", "p-modele", "p-effort"].forEach(function (id) { $(id).onchange = memorise; });
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
  d.appendChild(el("p", null, p.constat));
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
function rend() {
  var r = S.rapport, zone = $("props"), zoneEn = $("props-encours");
  vide(zone); vide(zoneEn);
  if (!r) { zone.appendChild(el("p", "doux", "Aucun audit pour le moment.")); $("encours").hidden = true; $("resume").textContent = "";
            $("non-verifie").textContent = ""; $("n-props").textContent = ""; $("b-copie").disabled = true; return; }
  var cat = $("f-cat").value, risque = $("f-risque").value;
  var tri = r.propositions.filter(function (p) { return (!cat || p.categorie === cat) && (!risque || p.risque === risque); })
    .sort(function (a, b) { return ORDRE[a.risque] - ORDRE[b.risque]; });
  var actives = tri.filter(function (p) { return !p.en_cours; }), en = tri.filter(function (p) { return p.en_cours; });
  actives.forEach(function (p) { zone.appendChild(propositionVue(p)); });
  if (!actives.length) zone.appendChild(el("p", "doux", "Aucune proposition."));
  en.forEach(function (p) { zoneEn.appendChild(propositionVue(p)); });
  $("encours").hidden = !en.length; $("n-encours").textContent = String(en.length);
  $("resume").textContent = r.resume; $("non-verifie").textContent = r.non_verifie ? "Non vérifié : " + r.non_verifie : "";
  $("n-props").textContent = "(" + actives.length + ")"; $("b-copie").disabled = !actives.length;
}

function chargeRapport() {
  var g = ++S.gen;
  return api("GET", "/rapport").then(function (r) {
    if (g !== S.gen) return;                       // un autre audit ou une autre action est passe : reponse depassee
    S.rapport = r.ok ? r.donnees : null; rend();
  });
}

function etat() {
  return api("GET", "/etat").then(function (r) {
    if (!r.ok) { message("ko", r.texte); return; }
    var e = r.donnees, enCours = e.etat === "en_cours";
    $("b-lance").disabled = enCours; $("b-stop").disabled = !enCours;
    if (enCours) {
      var s = e.debut ? Math.max(0, Math.round(Date.now() / 1000 - e.debut)) : 0;
      message("en", "Audit en cours depuis " + s + " s… (jusqu'à quelques minutes)");
      if (!S.scrute) S.scrute = setInterval(etat, 1500);
    } else {
      if (S.scrute) { clearInterval(S.scrute); S.scrute = null; }
      if (e.etat === "fini") { message("ok", "Audit terminé : " + e.message + "."); chargeRapport(); }
      else if (e.etat === "echec") message("ko", e.message);
      else message("", "Prêt.");
    }
  });
}

function lance() {
  var p = parametres();
  if (!p.zone.length || !p.categories.length) { message("ko", "Cochez au moins un dossier et un contrôle."); return; }
  if (!(p.anciennete_jours >= 0 && p.anciennete_jours <= 365)) { message("ko", "Ancienneté : un nombre de 0 à 365."); return; }
  S.gen++; S.rapport = null; rend();
  api("POST", "/lancer", p).then(function (r) {
    if (!r.ok) { message("ko", r.texte); return; }
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
