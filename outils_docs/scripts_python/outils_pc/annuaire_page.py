"""Page de l'annuaire des outils PC (GET /) : onglets Outils et Aide, HTML/CSS/JS sans dependance.

PAGE est une chaine servie telle quelle par annuaire_outils.py. Elle interroge /registre (une fois),
/etat (toutes les 3 s, arrete quand l'onglet est cache), /ports (a l'ouverture de la fenetre de lancement),
/console (tant que le panneau est ouvert) et poste /lance et /arrete avec l'en-tete X-Annuaire: 1.
Tout texte venu du serveur ou des outils est insere par textContent, jamais par innerHTML.
"""

PAGE = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Annuaire des outils</title>
<style>
  :root{--fond:#f6f7f9;--carte:#fff;--bord:#ddd;--texte:#222;--doux:#666;--bleu:#2563eb;--vert:#2a9d4a;--gris:#aaa;--orange:#e08a00;--rouge:#c0392b}
  *{box-sizing:border-box}
  body{margin:0;font:14px system-ui,sans-serif;color:var(--texte);background:var(--fond)}
  main{max-width:1100px;margin:0 auto;padding:12px 16px 40px}
  h1{font-size:20px;margin:6px 0 10px}
  .onglets{display:flex;gap:4px;border-bottom:1px solid #ccc;margin-bottom:12px}
  .onglets button{padding:6px 16px;border:1px solid #ccc;border-bottom:none;border-radius:6px 6px 0 0;background:#e8e8e8;font:inherit;cursor:pointer}
  .onglets button.on{background:#fff;font-weight:600}
  .groupe{font-size:11px;text-transform:uppercase;color:#777;margin:14px 0 6px;letter-spacing:.04em}
  .tuiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:10px}
  .tuile{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:10px 12px;display:flex;flex-direction:column;gap:6px}
  .tuile h3{margin:0;font-size:15px}
  .tuile p{margin:0;color:var(--doux);font-size:12px}
  .pastille{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;background:var(--gris)}
  .pastille.marche{background:var(--vert)}.pastille.bloque{background:var(--orange)}
  .meta{font-size:11px;color:#888}
  .raison{font-size:12px;color:var(--orange)}
  .erreur{font-size:12px;color:var(--rouge)}
  .actions{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:auto}
  .btn{display:inline-block;padding:4px 12px;border-radius:5px;border:1px solid #888;background:#fff;color:var(--texte);font:inherit;font-size:13px;cursor:pointer;text-decoration:none}
  .btn.p{background:var(--bleu);color:#fff;border-color:var(--bleu)}
  .btn:disabled{opacity:.5;cursor:default}
  .lien{background:none;border:none;color:var(--bleu);cursor:pointer;font:inherit;font-size:12px;padding:0;text-decoration:underline}
  .reseau{background:#eef3ff;border:1px solid #c9d8ff;border-radius:8px;padding:8px 12px;margin-bottom:10px;font-size:12px}
  .reseau code{word-break:break-all}
  .reseau div{margin-top:4px}
  .console{background:#1e1e1e;color:#cfc;font:11px/1.35 Consolas,monospace;padding:8px;border-radius:6px;max-height:300px;overflow:auto;white-space:pre-wrap;word-break:break-all;margin:6px 0 0}
  #panneau{margin-top:16px;display:none}
  #panneau header{display:flex;justify-content:space-between;align-items:center}
  .voile{position:fixed;inset:0;background:rgba(0,0,0,.45);display:none;align-items:center;justify-content:center;padding:12px;z-index:5}
  .modale{background:#fff;border-radius:10px;padding:16px;width:100%;max-width:440px;max-height:92vh;overflow:auto}
  .modale h2{margin:0 0 10px;font-size:17px}
  .champ{display:flex;flex-direction:column;gap:3px;margin:8px 0;font-size:13px}
  .champ select,.champ input{font:inherit;padding:5px 6px;width:100%}
  .modale .actions{justify-content:flex-end;margin-top:14px}
  .aide section{background:#fff;border:1px solid var(--bord);border-radius:8px;padding:10px 14px;margin:10px 0}
  .aide h2{margin:0 0 4px;font-size:16px}
  .aide h3{margin:8px 0 2px;font-size:12px;text-transform:uppercase;color:#777}
  .aide p,.aide ul{margin:2px 0;font-size:13px}
  .intro{background:#fff;border:1px solid var(--bord);border-radius:8px;padding:10px 14px;font-size:13px}
  @media (max-width:600px){.tuiles{grid-template-columns:1fr}main{padding:8px 16px 30px}}
</style>
</head>
<body>
<main>
  <h1>Annuaire des outils</h1>
  <div class="onglets" role="tablist">
    <button id="onglet-outils" class="on" type="button">Outils</button>
    <button id="onglet-aide" type="button">Aide</button>
  </div>
  <div id="vue-outils">
    <div id="message" class="erreur"></div>
    <div id="reseau"></div>
    <div id="grille"></div>
    <div id="panneau">
      <header><strong id="panneau-titre"></strong><button id="panneau-ferme" class="lien" type="button">fermer</button></header>
      <pre id="panneau-texte" class="console"></pre>
    </div>
  </div>
  <div id="vue-aide" class="aide" style="display:none"></div>
</main>

<div id="voile" class="voile">
  <form id="modale" class="modale">
    <h2 id="modale-titre"></h2>
    <div id="modale-champs"></div>
    <div id="modale-erreur" class="erreur"></div>
    <div class="actions">
      <button id="modale-annule" class="btn" type="button">Annuler</button>
      <button id="modale-ok" class="btn p" type="submit">Lancer</button>
    </div>
  </form>
</div>

<script>
"use strict";
var $ = function (id) { return document.getElementById(id); };
var registre = null, etats = {}, liensReseau = [], occupe = {}, erreurs = {}, consoleId = null;
var modaleId = null, enCours = false;

// Cree un element : h("div", {class:"x", onclick:f}, enfants...) ; les textes passent par textContent.
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

// Appel HTTP qui ne leve jamais : {ok, statut, donnees, erreur}.
async function appel(url, corps) {
  var opts = {cache: "no-store"};
  if (corps !== undefined) {
    opts.method = "POST";
    opts.headers = {"X-Annuaire": "1", "Content-Type": "application/json"};
    opts.body = JSON.stringify(corps);
  }
  var texte = "", statut = 0;
  try {
    var r = await fetch(url, opts);
    statut = r.status;
    texte = await r.text();
  } catch (e) {
    return {ok: false, statut: 0, donnees: null, erreur: "Annuaire injoignable"};
  }
  var donnees = null;
  try { donnees = JSON.parse(texte); } catch (e) { donnees = null; }
  if (statut >= 200 && statut < 300 && donnees !== null) return {ok: true, statut: statut, donnees: donnees, erreur: ""};
  var msg = donnees && donnees.erreur ? donnees.erreur : "Réponse inattendue (" + statut + ")";
  return {ok: false, statut: statut, donnees: donnees, erreur: msg};
}

function heure(debut) { return debut && debut.length >= 16 ? debut.slice(11, 16) : ""; }
function parId(id) { return registre.outils.filter(function (o) { return o.id === id; })[0]; }

// ---------- tuiles ----------
function tuile(o) {
  var e = etats[o.id] || {etat: "arrete", port: o.port_defaut};
  var attente = occupe[o.id];
  var meta = ":" + (e.port || o.port_defaut) + (e.etat === "marche" && e.debut ? " · depuis " + heure(e.debut) : "");
  var actions = h("div", {"class": "actions"});
  if (attente) {
    actions.appendChild(h("span", {"class": "meta", texte: attente}));
  } else {
    if (e.etat === "marche" && e.lien)
      actions.appendChild(h("a", {"class": "btn p", href: e.lien, target: "_blank", rel: "noopener", texte: "Ouvrir ↗"}));
    if (e.etat !== "marche")
      actions.appendChild(h("button", {"class": "btn p", type: "button", texte: "Lancer", onclick: function () { ouvreLancement(o); }}));
    if (e.peut_arreter)
      actions.appendChild(h("button", {"class": "btn", type: "button", texte: "Arrêter", onclick: function () { arrete(o); }}));
    if (e.console)
      actions.appendChild(h("button", {"class": "lien", type: "button", texte: "console", onclick: function () { ouvreConsole(o); }}));
  }
  return h("div", {"class": "tuile", "data-id": o.id},
    h("h3", {}, h("span", {"class": "pastille " + (e.etat || "arrete")}), o.nom),
    h("p", {texte: o.interet}),
    h("div", {"class": "meta", texte: meta}),
    e.etat === "marche" && e.lance_ailleurs ? h("div", {"class": "meta", texte: "lancé ailleurs"}) : null,
    e.raison ? h("div", {"class": "raison", texte: e.raison}) : null,
    erreurs[o.id] ? h("div", {"class": "erreur", texte: erreurs[o.id]}) : null,
    actions);
}

function dessine() {
  var grille = $("grille");
  grille.textContent = "";
  if (!registre) return;
  registre.groupes.forEach(function (g) {
    var outils = registre.outils.filter(function (o) { return o.groupe === g; });
    if (!outils.length) return;
    grille.appendChild(h("div", {"class": "groupe", texte: g}));
    var bloc = h("div", {"class": "tuiles"});
    outils.forEach(function (o) { bloc.appendChild(tuile(o)); });
    grille.appendChild(bloc);
  });
  var r = $("reseau");
  r.textContent = "";
  if (liensReseau.length) {
    var boite = h("div", {"class": "reseau"}, h("strong", {texte: "Depuis un autre appareil du réseau"}));
    liensReseau.forEach(function (l) {
      boite.appendChild(h("div", {}, h("code", {texte: l}), " ",
        h("button", {"class": "lien", type: "button", texte: "copier", onclick: function () { copie(l); }})));
    });
    r.appendChild(boite);
  }
}

function copie(texte) {
  try {
    if (navigator.clipboard) { navigator.clipboard.writeText(texte).catch(function () {}); return; }
  } catch (e) {}
  var t = h("textarea", {}); t.value = texte; document.body.appendChild(t); t.select();
  try { document.execCommand("copy"); } catch (e) {}
  document.body.removeChild(t);
}

// ---------- interrogation periodique ----------
async function rafraichit() {
  if (enCours || !registre) return;
  enCours = true;
  var r = await appel("/etat");
  if (r.ok && r.donnees && Array.isArray(r.donnees.outils)) {
    etats = {};
    r.donnees.outils.forEach(function (e) { etats[e.id] = e; });
    liensReseau = r.donnees.liens_reseau || [];
    $("message").textContent = "";
  } else {
    $("message").textContent = "État indisponible : " + r.erreur;
  }
  enCours = false;
  dessine();
  if (consoleId) majConsole();
}

async function charge() {
  var r = await appel("/registre");
  if (!r.ok || !r.donnees || !Array.isArray(r.donnees.outils)) {
    $("message").textContent = "Registre indisponible : " + r.erreur;
    setTimeout(charge, 3000);
    return;
  }
  registre = r.donnees;
  construitAide();
  rafraichit();
}

setInterval(function () { if (!document.hidden) rafraichit(); }, 3000);
document.addEventListener("visibilitychange", function () { if (!document.hidden) rafraichit(); });

// ---------- arret et console ----------
async function arrete(o) {
  occupe[o.id] = "arrêt en cours…";
  erreurs[o.id] = "";
  dessine();
  var r = await appel("/arrete", {id: o.id});
  delete occupe[o.id];
  if (!r.ok) erreurs[o.id] = r.erreur;
  await rafraichit();
}

function ouvreConsole(o) {
  consoleId = o.id;
  $("panneau-titre").textContent = "Console de " + o.nom + " (200 dernières lignes)";
  $("panneau").style.display = "block";
  $("panneau-texte").textContent = "…";
  majConsole();
}

async function majConsole() {
  var id = consoleId;
  if (!id) return;
  var r = await appel("/console?id=" + encodeURIComponent(id));
  if (id !== consoleId) return;
  var zone = $("panneau-texte");
  var bas = zone.scrollTop + zone.clientHeight >= zone.scrollHeight - 20;
  if (r.ok && Array.isArray(r.donnees.lignes)) zone.textContent = r.donnees.lignes.join("\n") || "(console vide)";
  else zone.textContent = "Console indisponible : " + r.erreur;
  if (bas) zone.scrollTop = zone.scrollHeight;
}

$("panneau-ferme").onclick = function () { consoleId = null; $("panneau").style.display = "none"; };

// ---------- fenetre de lancement ----------
function champ(libelle, controle) { return h("label", {"class": "champ"}, h("span", {texte: libelle}), controle); }

function liste(options, valeur) {
  var s = h("select", {});
  options.forEach(function (o) {
    var opt = h("option", {value: o[0], texte: o[1]});
    s.appendChild(opt);
  });
  s.value = valeur;
  if (s.value !== valeur && options.length) s.selectedIndex = 0;
  return s;
}

function libellePort(p) {
  return p.port + (p.description ? " — " + p.description.replace(/\s*\(COM\d+\)\s*$/, "") : "") +
         (p.tenu_par ? " (tenu par " + p.tenu_par + ")" : "");
}

async function ouvreLancement(o) {
  erreurs[o.id] = "";
  if (!o.a_port_com) { lance(o, {}); return; }
  modaleId = o.id;
  $("modale-titre").textContent = "Lancer " + o.nom;
  $("modale-erreur").textContent = "";
  $("modale-champs").textContent = "";
  $("modale-ok").disabled = true;
  $("voile").style.display = "flex";
  var r = await appel("/ports");
  var ports = r.ok && Array.isArray(r.donnees) ? r.donnees : [];
  if (!r.ok) $("modale-erreur").textContent = "Ports série indisponibles : " + r.erreur;
  var pont = etats["pont_serie"];
  var champs = $("modale-champs");
  o.parametres.forEach(function (p) {
    var ctl;
    if (p.genre === "com" || p.genre === "com_ou_pont") {
      var opts = p.genre === "com" ? [["auto", "auto (le seul port USB présent)"]] : [["", "(aucun)"]];
      ports.forEach(function (x) { opts.push([x.port, libellePort(x)]); });
      if (p.genre === "com_ou_pont" && pont && pont.etat === "marche")
        opts.push(["pont:" + pont.port, "pont:" + pont.port + " — via le pont série"]);
      ctl = liste(opts, p.defaut);
    } else if (p.genre === "debit") {
      ctl = liste(registre.debits.map(function (d) { return [String(d), String(d)]; }), p.defaut);
    } else {
      ctl = h("input", {type: "number", min: "1024", max: "65535", value: p.defaut});
    }
    ctl.setAttribute("data-cle", p.cle);
    champs.appendChild(champ(p.libelle, ctl));
  });
  $("modale-ok").disabled = false;
}

function ferme() { modaleId = null; $("voile").style.display = "none"; }
$("modale-annule").onclick = ferme;

$("modale").onsubmit = async function (ev) {
  ev.preventDefault();
  var o = modaleId && parId(modaleId);
  if (!o) return;
  var valeurs = {};
  var controles = $("modale-champs").querySelectorAll("[data-cle]");
  for (var i = 0; i < controles.length; i++) valeurs[controles[i].getAttribute("data-cle")] = controles[i].value;
  $("modale-ok").disabled = true;
  $("modale-erreur").textContent = "";
  var r = await lance(o, valeurs);
  if (r.ok) ferme();
  else $("modale-erreur").textContent = r.erreur;
  $("modale-ok").disabled = false;
};

async function lance(o, valeurs) {
  occupe[o.id] = "lancement…";
  dessine();
  var r = await appel("/lance", {id: o.id, valeurs: valeurs});
  delete occupe[o.id];
  if (!r.ok && modaleId !== o.id) erreurs[o.id] = r.erreur;
  await rafraichit();
  return r;
}

// ---------- onglets et aide ----------
function montre(aide) {
  $("vue-outils").style.display = aide ? "none" : "block";
  $("vue-aide").style.display = aide ? "block" : "none";
  $("onglet-outils").className = aide ? "" : "on";
  $("onglet-aide").className = aide ? "on" : "";
}
$("onglet-outils").onclick = function () { montre(false); };
$("onglet-aide").onclick = function () { montre(true); };

function construitAide() {
  var v = $("vue-aide");
  v.textContent = "";
  v.appendChild(h("div", {"class": "intro", texte:
    "Cette page liste les outils PC du dépôt. Chaque tuile montre l'état de l'outil (vert : en marche, gris : arrêté, " +
    "orange : bloqué, par exemple parce qu'un port COM est tenu par un autre outil). « Ouvrir ↗ » affiche la page de " +
    "l'outil, « Lancer » le démarre, « Arrêter » l'arrête s'il a été lancé d'ici, « console » montre ses 200 dernières " +
    "lignes. L'état est relu toutes les 3 secondes tant que l'onglet est visible."}));
  registre.outils.forEach(function (o) {
    var params = h("ul", {});
    o.parametres.forEach(function (p) {
      params.appendChild(h("li", {texte: p.libelle + " : option " + p.option + ", défaut " + (p.defaut === "" ? "(aucun)" : p.defaut)}));
    });
    v.appendChild(h("section", {"data-aide": o.id},
      h("h2", {texte: o.nom}),
      h("h3", {texte: "Intérêt"}), h("p", {texte: o.aide}),
      h("h3", {texte: "Lancer"}),
      h("p", {texte: "Bouton Lancer de la tuile" + (o.a_port_com ? " : une fenêtre propose le port, le débit et le port de la page." :
        " : l'outil démarre avec ses valeurs par défaut.") +
        " Page par défaut : port " + o.port_defaut + "."}),
      h("h3", {texte: "Paramètres"}), params,
      h("h3", {texte: "Journaux"}), h("p", {texte: o.journaux})));
  });
}

charge();
</script>
</body>
</html>
"""
