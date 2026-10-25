"""Page HTML de « Fichiers Berry par env » (servie par fichiers_berry_web.py), disposition B de la maquette :
un choix de fichier + son etat, puis trois colonnes (Sur le FS, Exclu, Solidifie) avec l'etat complet de l'env.

Les modifications restent dans la page (« en attente ») jusqu'a « Voir le diff puis enregistrer ».
Une ligne d'une liste partagee ([berry_commun], option d'une base) ouvre la fenetre « Modifier la liste
partagee (N envs) » / « Annuler ». Formulaire de creation d'env a partir d'une carte modele.
Textes inseres par textContent uniquement. Sonde : test_fichiers_berry_page_chrome.py.
"""

PAGE = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>Fichiers Berry par env</title>
<style>
  :root{color-scheme:light dark;--fond:#f6f7f9;--carte:#fff;--bord:#ddd;--texte:#222;--doux:#666;--discret:#777;--bleu:#2563eb;
    --vert:#2a9d4a;--orange:#c27400;--rouge:#c0392b;--btn:#fff;--btn-bord:#888;--rouge-fond:#fdecea;--orange-fond:#fff4e0;
    --bleu-fond:#eef3ff;--console:#1e1e1e;--console-texte:#d8dee9}
  @media (prefers-color-scheme: dark){:root{--fond:#121417;--carte:#1d2025;--bord:#33373e;--texte:#e6e6e6;--doux:#a8adb5;
    --discret:#8b9099;--bleu:#5b93ff;--vert:#3fbf63;--orange:#f0a020;--rouge:#ff6b5b;--btn:#262a30;--btn-bord:#555b64;
    --rouge-fond:#3a1d1b;--orange-fond:#3a2c12;--bleu-fond:#18233a;--console:#0b0e13}}
  *{box-sizing:border-box}
  body{margin:0;font:14px system-ui,sans-serif;color:var(--texte);background:var(--fond)}
  main{max-width:1200px;margin:0 auto;padding:12px 16px 40px}
  h1{font-size:20px;margin:6px 0 10px}
  h2{font-size:15px;margin:0 0 8px}
  .carte{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:10px 12px;margin-bottom:12px}
  .barre{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
  select,input[type=text]{font:inherit;font-size:13px;padding:4px 6px;background:var(--btn);color:var(--texte);border:1px solid var(--btn-bord);border-radius:4px;max-width:100%}
  .btn{padding:6px 12px;border-radius:6px;border:1px solid var(--btn-bord);background:var(--btn);color:var(--texte);font:inherit;font-size:13px;cursor:pointer}
  .btn.p{background:var(--bleu);color:#fff;border-color:var(--bleu);font-weight:600}
  .btn:disabled{opacity:.45;cursor:not-allowed}
  .lien{background:none;border:none;color:var(--bleu);cursor:pointer;font:inherit;font-size:12px;padding:0;text-decoration:underline}
  .radios label{margin-right:10px;cursor:pointer}
  .colonnes{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
  @media (max-width:800px){.colonnes{grid-template-columns:minmax(0,1fr)}}
  .colonne h2 .compte{font-weight:400;color:var(--discret);font-size:12px}
  .fichier{padding:3px 0;border-top:1px solid var(--bord);font-family:ui-monospace,Consolas,monospace;font-size:12.5px;overflow-wrap:anywhere}
  .badge{display:inline-block;font-family:system-ui,sans-serif;font-size:10.5px;padding:0 6px;margin-left:4px;border-radius:8px;background:var(--bleu-fond);color:var(--bleu)}
  .badge.carte-b{background:#e3f5e1;color:#1d6b2c}.badge.amont{background:var(--orange-fond);color:var(--orange)}
  .badge.alerte{background:var(--rouge-fond);color:var(--rouge)}
  .attente{background:var(--orange-fond)}
  .avert{font-size:12.5px;border-left:3px solid var(--orange);padding:2px 0 2px 8px;margin:4px 0}
  .avert.rouge{border-color:var(--rouge)}
  .discret{color:var(--discret);font-size:12px}
  .ok{color:var(--vert);font-weight:600}.erreur{color:var(--rouge)}
  pre{background:var(--console);color:var(--console-texte);padding:8px;border-radius:6px;overflow:auto;max-height:420px;font-size:12px}
  .cache{display:none}
  #fenetre-partage{position:fixed;inset:0;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;padding:16px}
  #fenetre-partage.cache{display:none}
  #fenetre-partage .carte{max-width:640px;width:100%}
  .grille{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:6px 12px}
  .grille label{display:flex;flex-direction:column;font-size:12px;color:var(--doux);gap:2px}
</style>
</head>
<body>
<main>
  <h1>Fichiers Berry par env</h1>
  <section class="carte">
    <div class="barre">
      <label for="env">Env :</label> <select id="env"></select>
      <button class="btn" id="reverifier">Revérifier les fichiers</button>
      <button class="btn" id="creer">Créer un env à partir de…</button>
      <span id="statut" class="discret"></span>
    </div>
    <div id="avertissements"></div>
  </section>

  <section class="carte">
    <div class="barre">
      <label for="fichier">Fichier :</label> <select id="fichier"></select>
      <span class="radios" id="radios"></span>
      <input type="text" id="raison" placeholder="Raison (facultatif, écrite en commentaire)" size="34">
      <button class="btn p" id="appliquer">Appliquer</button>
    </div>
    <div id="rappel-solidif" class="avert cache">Avant de compiler : vérifier le module par
      <code>berry/solidifie_et_compile_berry.py</code> ; une nouvelle globale du framework va dans <code>globs</code>
      de <code>solidify_all_python.be</code> ; un module qui s'appelle par son propre nom doit être importé au
      niveau fichier par l'autoexec.</div>
    <div id="refus-local" class="erreur"></div>
  </section>

  <div class="colonnes">
    <section class="carte colonne"><h2>Sur le FS <span class="compte" id="n-fs"></span></h2><div id="col-fs"></div></section>
    <section class="carte colonne"><h2>Exclu <span class="compte" id="n-exclu"></span></h2><div id="col-exclu"></div></section>
    <section class="carte colonne"><h2>Solidifié <span class="compte" id="n-solidifie"></span></h2><div id="col-solidifie"></div></section>
  </div>

  <section class="carte">
    <h2>Modifications en attente</h2>
    <div id="attente"></div>
    <div class="barre"><button class="btn p" id="voir-diff" disabled>Voir le diff puis enregistrer</button></div>
    <div id="panneau-diff" class="cache">
      <p class="avert">L'enregistrement change l'empreinte du projet : <b>le build suivant repart de zéro</b>.
        Le cenv d'avant est sauvegardé (copie horodatée, 30 jours) ; le chemin s'affiche après l'écriture.</p>
      <div id="cites"></div>
      <pre id="diff"></pre>
      <div class="barre"><button class="btn p" id="enregistrer">Enregistrer</button>
        <button class="btn" id="fermer-diff">Fermer</button></div>
    </div>
    <div id="message"></div>
  </section>

  <section class="carte cache" id="panneau-creation">
    <h2>Créer un env à partir d'une carte modèle</h2>
    <div class="grille">
      <label>Carte modèle<select id="c-modele"></select></label>
      <label>Base<select id="c-base"></select></label>
      <label>Lieu (minuscules)<input type="text" id="c-lieu" placeholder="garage"></label>
      <label>Nom (minuscules, tirets)<input type="text" id="c-nom" placeholder="porte-test"></label>
    </div>
    <div class="barre" style="margin:8px 0"><button class="btn" id="c-proposer">Proposer l'identité</button>
      <span id="c-env" class="discret"></span></div>
    <div class="grille" id="c-identite"></div>
    <div class="barre" style="margin-top:8px"><button class="btn p" id="c-prepare">Voir le diff</button>
      <button class="btn" id="c-creer" disabled>Créer</button></div>
    <div id="c-retours"></div>
    <pre id="c-diff" class="cache"></pre>
  </section>
</main>

<div id="fenetre-partage" class="cache"><div class="carte">
  <h2>Liste partagée</h2>
  <p id="partage-texte"></p>
  <ul id="partage-envs"></ul>
  <div class="barre"><button class="btn p" id="partage-modifier">Modifier la liste partagée</button>
    <button class="btn" id="partage-annuler">Annuler</button></div>
</div></div>

<script>
"use strict";
var $ = function (id) { return document.getElementById(id); };
var CHAMPS = ["CODE_IMAGE_STR", "PROJECT", "WIFI_IP_ADDRESS", "WIFI_RGX_SSID", "MQTT_CLIENT_ID", "MQTT_TOPIC",
              "MQTT_GRPTOPIC", "FRIENDLY_NAME"];
var LIBELLES = {fs: "Sur le FS", exclu: "Exclu", solidifie: "Solidifié", absent: "Absent", retire: "ligne retirée"};
var GROUPES = {fs: "data/fs", carte: "carte", amont: "amont"};
var URL_BUILD = "http://127.0.0.1:7700/";
var envs = [], etat = null, attente = {}, enAttenteDePartage = null, empreinte = "", creationEmpreinte = "";

function h(balise, attrs) {
  var e = document.createElement(balise);
  for (var k in (attrs || {})) {
    if (k.slice(0, 2) === "on") e[k] = attrs[k];
    else if (k === "texte") e.textContent = attrs[k];
    else e.setAttribute(k, attrs[k]);
  }
  for (var i = 2; i < arguments.length; i++) {
    var c = arguments[i];
    if (c === null || c === undefined || c === false) continue;
    e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return e;
}
function vide(e) { while (e.firstChild) e.removeChild(e.firstChild); return e; }

// Appel HTTP qui ne leve jamais : {ok, statut, donnees, texte}. Les POST portent X-Fichiers-Berry: 1.
async function appel(url, corps) {
  var opts = {cache: "no-store"};
  if (corps !== undefined) {
    opts.method = "POST";
    opts.headers = {"X-Fichiers-Berry": "1", "Content-Type": "application/json"};
    opts.body = JSON.stringify(corps);
  }
  try {
    var r = await fetch(url, opts), texte = await r.text(), donnees = null;
    try { donnees = JSON.parse(texte); } catch (e) {}
    return {ok: r.ok, statut: r.status, donnees: donnees, texte: texte};
  } catch (e) {
    return {ok: false, statut: 0, donnees: null, texte: "outil injoignable : " + e};
  }
}

function nom(chemin) { return chemin.split("/").pop(); }
function cible(f, et) {
  if (f.groupe === "amont") return et === "fs" ? "custom_files_upload" : null;
  return {exclu: "custom_files_exclude", solidifie: "custom_berry_solidify"}[et] || null;
}
function etatsPossibles(f) {
  if (f.figes) return ["fs"];
  return f.groupe === "amont" ? ["fs", "absent"] : ["fs", "exclu", "solidifie"];
}
function etatAffiche(f) { return attente[f.chemin] ? attente[f.chemin].etat : f.etat; }
function parChemin(c) { return etat.fichiers.filter(function (f) { return f.chemin === c; })[0]; }

async function chargeEnvs() {
  var r = await appel("/envs");
  if (!r.ok) { $("statut").textContent = r.texte; return; }
  envs = r.donnees.envs;
  [["env", null], ["c-modele", "cartes"], ["c-base", "bases"]].forEach(function (s) {
    var sel = vide($(s[0]));
    [["cartes", "Mes cartes"], ["bases", "Mes bases"]].forEach(function (fam) {
      if (s[1] && s[1] !== fam[0]) return;
      var g = h("optgroup", {label: fam[1]});
      envs.filter(function (e) { return e.famille === fam[0]; }).forEach(function (e) {
        g.appendChild(h("option", {value: e.nom, texte: e.nom}));
      });
      sel.appendChild(g);
    });
  });
  var demande = new URLSearchParams(location.search).get("env");
  if (demande && envs.some(function (e) { return e.nom === demande; })) $("env").value = demande;
}

async function chargeEtat() {
  $("statut").textContent = "recensement…";
  var r = await appel("/etat?env=" + encodeURIComponent($("env").value));
  if (!r.ok) { $("statut").textContent = r.texte; return; }
  etat = r.donnees;
  $("statut").textContent = etat.fichiers.length + " fichiers recensés à l'instant";
  dessine();
}

function badges(f) {
  var res = [h("span", {"class": "badge " + (f.groupe === "carte" ? "carte-b" : f.groupe === "amont" ? "amont" : ""),
                        texte: GROUPES[f.groupe]})];
  f.provenances.forEach(function (p) {
    if (p.partagee) res.push(h("span", {"class": "badge", texte: p.section === "berry_commun" ? p.option_ecrite : p.section}));
  });
  if (f.incoherent) res.push(h("span", {"class": "badge alerte", texte: "incohérent"}));
  if (f.homonyme) res.push(h("span", {"class": "badge alerte", texte: "homonyme"}));
  if (f.figes) res.push(h("span", {"class": "badge", texte: "figé"}));
  if (attente[f.chemin]) res.push(h("span", {"class": "badge alerte", texte: "en attente"}));
  return res;
}

function dessine() {
  var cols = {fs: [], exclu: [], solidifie: []};
  etat.fichiers.forEach(function (f) {
    var e = etatAffiche(f), col = e === "absent" ? "exclu" : e;
    cols[col].push(h.apply(null, ["div", {"class": "fichier" + (attente[f.chemin] ? " attente" : ""), title: f.chemin},
                                   nom(f.chemin) + (e === "absent" ? " (absent)" : "")].concat(badges(f))));
  });
  etat.hors_perimetre.forEach(function (x) {
    cols.exclu.push(h("div", {"class": "fichier", title: x.chemin}, nom(x.chemin), h("span", {"class": "badge", texte: "hors périmètre"})));
  });
  ["fs", "exclu", "solidifie"].forEach(function (c) {
    var col = vide($("col-" + c));
    cols[c].forEach(function (e) { col.appendChild(e); });
    $("n-" + c).textContent = "(" + cols[c].length + ")";
  });
  var av = vide($("avertissements"));
  if (!etat.exclude_solidified)
    av.appendChild(h("div", {"class": "avert", texte: "custom_files_exclude_solidified n'est pas à ON : un fichier solidifié reste AUSSI sur le FS."}));
  etat.disparus.forEach(function (x) {
    av.appendChild(h("div", {"class": "avert rouge"}, "Ligne vers un fichier disparu : " + x.chemin + " (" + x.option + ", " + x.section + ") ",
      /\.be$/.test(x.chemin) ? h("button", {"class": "lien", "data-retirer": x.chemin, texte: "retirer la ligne",
                                            onclick: function () { retireDisparu(x); }}) : null));
  });
  etat.fichiers.filter(function (f) { return f.homonyme && f.groupe === "carte"; }).forEach(function (f) {
    av.appendChild(h("div", {"class": "avert", texte: "Homonyme : " + f.chemin + " et " + f.homonyme + " — custom_files_exclude agit par NOM de fichier, il retirerait les deux."}));
  });
  var sel = $("fichier"), garde = sel.value;
  vide(sel);
  ["fs", "carte", "amont"].forEach(function (g) {
    var og = h("optgroup", {label: GROUPES[g]});
    etat.fichiers.filter(function (f) { return f.groupe === g; }).forEach(function (f) {
      og.appendChild(h("option", {value: f.chemin, texte: nom(f.chemin) + " — " + LIBELLES[etatAffiche(f)]}));
    });
    if (og.children.length) sel.appendChild(og);
  });
  if (garde && parChemin(garde)) sel.value = garde;
  radios();
  dessineAttente();
}

function radios() {
  var f = parChemin($("fichier").value), zone = vide($("radios"));
  if (!f) return;
  etatsPossibles(f).forEach(function (e) {
    var r = h("input", {type: "radio", name: "etat", value: e, id: "etat-" + e});
    r.checked = etatAffiche(f) === e;
    r.onchange = majRappel;
    zone.appendChild(h("label", {}, r, " " + LIBELLES[e]));
  });
  majRappel();
}
function etatChoisi() { var r = document.querySelector("input[name=etat]:checked"); return r ? r.value : null; }
function majRappel() { $("rappel-solidif").classList.toggle("cache", etatChoisi() !== "solidifie"); }

function appliquer() {
  var f = parChemin($("fichier").value), e = etatChoisi();
  $("refus-local").textContent = "";
  if (!f || !e) return;
  if (e === f.etat) { delete attente[f.chemin]; dessine(); return; }
  var retraits = f.provenances.filter(function (p) { return p.option !== cible(f, e); });
  var amont = retraits.filter(function (p) { return p.amont; });
  if (amont.length) {
    $("refus-local").textContent = "Impossible : la ligne vient de " + amont[0].fichier + " (liste de l'amont, non modifiable ici).";
    return;
  }
  var demande = {chemin: f.chemin, etat: e, raison: $("raison").value.trim(), partage_accepte: false};
  var sources = retraits.filter(function (p) { return p.partagee; }).map(source);
  // ajout dans l'option propre d'une base : ses cartes en heritent (extends ou ${env:base.option})
  var c = cible(f, e), ajoute = c && !f.provenances.some(function (p) { return p.option === c; });
  var heritiers = ajoute ? etat.heritiers[c] : [];
  if (heritiers.some(function (x) { return x !== etat.env; })) sources.push({libelle: "env:" + etat.env + "." + c, envs: heritiers});
  metEnAttente(demande, sources);
}

function source(p) {
  return {libelle: p.section === "berry_commun" ? "berry_commun." + p.option_ecrite : p.section + "." + p.option_ecrite, envs: p.envs};
}

// Sans liste partagee : en attente. Sinon, fenetre « Modifier la liste partagee (N envs) » / « Annuler ».
function metEnAttente(demande, sources) {
  if (!sources.length) { attente[demande.chemin] = demande; dessine(); return; }
  var tous = {};
  sources.forEach(function (s) { s.envs.forEach(function (x) { tous[x] = true; }); });
  var liste = Object.keys(tous).sort();
  $("partage-texte").textContent = nom(demande.chemin) + " : la liste partagée " +
    sources.map(function (s) { return s.libelle; }).join(", ") + " sera modifiée. Cela touche " + liste.length + " env(s) :";
  var ul = vide($("partage-envs"));
  liste.forEach(function (x) { ul.appendChild(h("li", {texte: x})); });
  $("partage-modifier").textContent = "Modifier la liste partagée (" + liste.length + " envs)";
  enAttenteDePartage = demande;
  $("fenetre-partage").classList.remove("cache");
}

function retireDisparu(x) {
  var demande = {chemin: x.chemin, etat: "retire", raison: "", partage_accepte: false};
  metEnAttente(demande, x.provenance.partagee ? [source(x.provenance)] : []);
}

function dessineAttente() {
  var zone = vide($("attente")), cles = Object.keys(attente);
  if (!cles.length) zone.appendChild(h("div", {"class": "discret", texte: "Aucune."}));
  cles.forEach(function (c) {
    var d = attente[c];
    zone.appendChild(h("div", {"class": "fichier", "data-attente": c}, nom(c) + " → " + LIBELLES[d.etat] +
      (d.partage_accepte ? " (liste partagée)" : "") + (d.raison ? " ; " + d.raison : "") + " ",
      h("button", {"class": "lien", texte: "retirer", onclick: function () { delete attente[c]; dessine(); }})));
  });
  $("voir-diff").disabled = !cles.length;
  // le diff vu ne vaut que pour les demandes d'alors : toute modification le referme
  $("panneau-diff").classList.add("cache");
  $("enregistrer").disabled = true;
}

async function voirDiff() {
  var r = await appel("/prepare", {env: etat.env, demandes: Object.values(attente)});
  vide($("message"));
  if (!r.ok) { $("message").appendChild(h("div", {"class": "erreur", texte: r.texte})); return; }
  var p = r.donnees, cites = vide($("cites"));
  empreinte = p.empreinte;
  p.refus.concat(p.confirmations.map(function (c) { return "À confirmer : " + c.chemin + " (" + c.section + "." + c.option + ")"; }))
    .forEach(function (t) { cites.appendChild(h("div", {"class": "avert rouge", texte: t})); });
  p.commentaires_cites.forEach(function (c) {
    cites.appendChild(h("div", {"class": "avert", texte: "Commentaire ligne " + c.ligne + " qui cite le fichier (à revoir) : " + c.texte}));
  });
  $("diff").textContent = p.diff || "(aucun changement)";
  $("enregistrer").disabled = !p.diff || p.refus.length > 0 || p.confirmations.length > 0;
  $("panneau-diff").classList.remove("cache");
}

async function enregistrer() {
  var env = etat.env, r = await appel("/enregistre", {env: env, demandes: Object.values(attente), empreinte: empreinte});
  var m = vide($("message"));
  if (!r.ok) { m.appendChild(h("div", {"class": "erreur", texte: "Refusé : " + r.texte})); return; }
  attente = {};
  $("panneau-diff").classList.add("cache");
  m.appendChild(h("div", {"class": "ok", id: "message-ok", texte: "Enregistré dans platformio_tasmota_cenv.ini. Sauvegarde : " + r.donnees.sauvegarde}));
  m.appendChild(h("a", {id: "lien-build", href: URL_BUILD + "?env=" + encodeURIComponent(env), target: "_blank",
                        texte: "Construire / téléverser le FS de " + env + " (page build)"}));
  await chargeEtat();
}

function identiteSaisie() {
  var res = {};
  CHAMPS.forEach(function (c) { res[c] = $("c-" + c).value.trim(); });
  return res;
}
function creationCorps() {
  return {modele: $("c-modele").value, base: $("c-base").value, lieu: $("c-lieu").value.trim(),
          nom: $("c-nom").value.trim(), identite: identiteSaisie(), define: $("c-define").value.trim()};
}
function construitIdentite() {
  var g = $("c-identite");
  CHAMPS.concat(["define"]).forEach(function (c) {
    g.appendChild(h("label", {}, c === "define" ? "-D (define du firmware)" : c, h("input", {type: "text", id: "c-" + c})));
  });
}
async function proposer() {
  var q = "base=" + encodeURIComponent($("c-base").value) + "&lieu=" + encodeURIComponent($("c-lieu").value.trim()) +
          "&nom=" + encodeURIComponent($("c-nom").value.trim());
  var r = await appel("/identite?" + q), z = vide($("c-retours"));
  if (!r.ok) { z.appendChild(h("div", {"class": "erreur", texte: r.texte})); return; }
  CHAMPS.forEach(function (c) { $("c-" + c).value = r.donnees.identite[c]; });
  $("c-define").value = r.donnees.define;
  $("c-env").textContent = "env : " + r.donnees.env;
}
async function prepareCreation() {
  var r = await appel("/creation/prepare", creationCorps()), z = vide($("c-retours"));
  $("c-creer").disabled = true;
  if (!r.ok) { z.appendChild(h("div", {"class": "erreur", texte: r.texte})); return; }
  var p = r.donnees;
  creationEmpreinte = p.empreinte;
  p.refus.forEach(function (t) { z.appendChild(h("div", {"class": "avert rouge", texte: t})); });
  p.avertissements.forEach(function (t) { z.appendChild(h("div", {"class": "avert", texte: t})); });
  $("c-diff").textContent = p.diff || "";
  $("c-diff").classList.toggle("cache", !p.diff);
  $("c-creer").disabled = p.refus.length > 0;
}
async function creer() {
  var r = await appel("/creation", Object.assign(creationCorps(), {empreinte: creationEmpreinte})), z = vide($("c-retours"));
  if (!r.ok) { z.appendChild(h("div", {"class": "erreur", texte: "Refusé : " + r.texte})); return; }
  $("c-creer").disabled = true;
  z.appendChild(h("div", {"class": "ok", id: "c-ok", texte: "Créé : " + r.donnees.env + " et " + r.donnees.dossier +
    " (rien n'est commité ; compléter IP et topic si besoin). Sauvegarde : " + r.donnees.sauvegarde}));
  await chargeEnvs();
  $("env").value = r.donnees.env;
  await chargeEtat();
}

$("env").onchange = function () { attente = {}; vide($("message")); $("panneau-diff").classList.add("cache"); chargeEtat(); };
$("reverifier").onclick = chargeEtat;
$("fichier").onchange = radios;
$("appliquer").onclick = appliquer;
$("voir-diff").onclick = voirDiff;
$("enregistrer").onclick = enregistrer;
$("fermer-diff").onclick = function () { $("panneau-diff").classList.add("cache"); };
$("partage-annuler").onclick = function () { enAttenteDePartage = null; $("fenetre-partage").classList.add("cache"); };
$("partage-modifier").onclick = function () {
  var d = enAttenteDePartage;
  enAttenteDePartage = null;
  $("fenetre-partage").classList.add("cache");
  if (d) { d.partage_accepte = true; attente[d.chemin] = d; dessine(); }
};
$("creer").onclick = function () { $("panneau-creation").classList.toggle("cache"); };
$("c-proposer").onclick = proposer;
$("c-prepare").onclick = prepareCreation;
$("c-creer").onclick = creer;
["input", "change"].forEach(function (t) {      // saisie changee apres « Voir le diff » : refaire le diff
  $("panneau-creation").addEventListener(t, function () { $("c-creer").disabled = true; });
});
construitIdentite();
chargeEnvs().then(chargeEtat);
</script>
</body>
</html>
"""
