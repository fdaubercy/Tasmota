"""Page de build_web.py (GET /, http://127.0.0.1:7700) : liste des envs, actions, suivi en direct.

PAGE est une chaine servie telle quelle (HTML + CSS + JS, aucune ressource externe : la page doit
marcher hors ligne). Disposition validee par l'utilisateur (maquette « B ») : liste des envs a gauche
(une ligne par env : case, nom, interrupteur COM / OTA, champ port ou IP), actions a droite, panneau de
suivi dessous (un bloc par env, bandeau rouge par echec). Sur telephone, les colonnes s'empilent.

Routes appelees (formats : docstring de build_web.py ; evenements du flux : docstring de build_serie.py) :
    GET /envs (au chargement, et apres un lancement : littlefs.bin a pu apparaitre), GET /execution,
    GET /flux?depuis=0 (EventSource : la reprise apres coupure envoie Last-Event-ID tout seul),
    GET /journal?env= (journal deplie), POST /lancer, /port, /arreter avec l'en-tete X-Build: 1.
Tout texte venu du serveur est insere par textContent, jamais par innerHTML.

Rattachements du suivi (pour ne pas creer de ligne « fantome » dans le bloc d'un env) :
  - la preparation d'un uploadfs OTA arrive avec action="buildfs" meme si buildfs n'est pas coche :
    elle est affichee sur la ligne « Téléverser le file system » (prefixe « Préparation ») ;
  - si compiler ET upload sont coches, seul upload part (choix 9 de la spec) : ses etapes Pré-build,
    Compilation et Édition des liens sont affichees sur la ligne « Compiler le firmware ».
Un `detail` qui commence par « AVERTISSEMENT » (verification apres redemarrage de l'OTA du FS) donne un
bandeau orange, distinct d'un echec (bandeau rouge).
"""

PAGE = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>Build et téléversement</title>
<script>
  // Theme applique AVANT le rendu (pas d'eclair blanc) : choix memorise, sinon celui du systeme.
  (function () {
    var t = null;
    try { t = localStorage.getItem("build-theme"); } catch (e) {}
    if (t !== "clair" && t !== "sombre")
      t = (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches) ? "sombre" : "clair";
    document.documentElement.setAttribute("data-theme", t);
  })();
</script>
<style>
  :root{color-scheme:light;--fond:#f6f7f9;--carte:#fff;--bord:#ddd;--texte:#222;--doux:#666;--discret:#777;--bleu:#2563eb;--vert:#2a9d4a;--gris:#aaa;--orange:#c27400;--rouge:#c0392b;
    --btn:#fff;--btn-bord:#888;--piste:#e9e9ea;--survol:#f0f3f8;--rouge-fond:#fdecea;--orange-fond:#fff4e0;--bleu-fond:#eef3ff;--console:#1e1e1e;--console-texte:#d8dee9}
  :root[data-theme="sombre"]{color-scheme:dark;--fond:#121417;--carte:#1d2025;--bord:#33373e;--texte:#e6e6e6;--doux:#a8adb5;--discret:#8b9099;--bleu:#5b93ff;--vert:#3fbf63;--gris:#6b7078;--orange:#f0a020;--rouge:#ff6b5b;
    --btn:#262a30;--btn-bord:#555b64;--piste:#39393d;--survol:#23272d;--rouge-fond:#3a1d1b;--orange-fond:#3a2c12;--bleu-fond:#18233a;--console:#0b0e13;--console-texte:#d8dee9}
  *{box-sizing:border-box}
  body{margin:0;font:14px system-ui,sans-serif;color:var(--texte);background:var(--fond)}
  main{max-width:1200px;margin:0 auto;padding:12px 16px 40px}
  .entete{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
  .entete .gauche{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
  h1{font-size:20px;margin:6px 0 10px}
  h2{font-size:15px;margin:0 0 8px}
  .puce{padding:2px 9px;border-radius:12px;border:1px solid var(--bord);white-space:nowrap;font-size:12px;color:var(--doux)}
  .puce.encours{color:var(--bleu);border-color:var(--bleu)}.puce.ok{color:var(--vert);border-color:var(--vert)}
  .puce.erreur{color:var(--rouge);border-color:var(--rouge)}.puce.alerte{color:var(--orange);border-color:var(--orange)}
  .theme{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--doux);cursor:pointer;user-select:none}
  .theme input{position:absolute;opacity:0;width:1px;height:1px;margin:0}
  .interrupteur{position:relative;flex:none;width:2.6em;height:1.5em;border-radius:.75em;background:var(--piste);transition:background .2s}
  .interrupteur::after{content:"";position:absolute;top:.15em;left:.15em;width:1.2em;height:1.2em;border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.3);transition:transform .2s}
  .theme input:checked + .interrupteur{background:#34c759}
  .theme input:checked + .interrupteur::after{transform:translateX(1.1em)}
  .theme input:focus-visible + .interrupteur{outline:2px solid var(--bleu);outline-offset:2px}
  .carte{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:10px 12px}
  .disposition{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:12px;align-items:start}
  .commandes{position:sticky;top:8px;display:flex;flex-direction:column;gap:10px}
  .erreur{color:var(--rouge);font-size:12px}
  .doux{color:var(--doux)}.discret{color:var(--discret);font-size:12px}
  /* familles et sous-groupes */
  details.famille{background:var(--carte);border:1px solid var(--bord);border-radius:8px;margin-bottom:10px}
  details.famille > summary,details.sous-groupe > summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:8px;user-select:none}
  details.famille > summary{padding:9px 12px;font-weight:600;font-size:14px}
  details.famille > summary::-webkit-details-marker,details.sous-groupe > summary::-webkit-details-marker{display:none}
  details.famille > summary::before,details.sous-groupe > summary::before{content:"";flex:none;width:0;height:0;border-left:5px solid var(--doux);border-top:4px solid transparent;border-bottom:4px solid transparent;transition:transform .15s}
  details.famille[open] > summary::before,details.sous-groupe[open] > summary::before{transform:rotate(90deg)}
  summary .compte{font-weight:400;color:var(--discret);font-size:12px}
  details.sous-groupe{border-top:1px solid var(--bord)}
  details.sous-groupe > summary{padding:7px 12px 7px 22px;font-size:13px;color:var(--doux)}
  details.sous-groupe .env{padding-left:22px}
  /* une ligne par env */
  .env{display:grid;grid-template-columns:auto minmax(0,1fr) auto 9.5em;grid-template-areas:"case nom methode champ" ". notes notes notes";
    align-items:center;column-gap:10px;row-gap:2px;padding:6px 12px;border-top:1px solid var(--bord)}
  .env:hover{background:var(--survol)}
  .env.coche{background:var(--bleu-fond)}
  .env > input[type=checkbox]{grid-area:case;width:16px;height:16px;margin:0}
  .env .nom{grid-area:nom;overflow-wrap:anywhere;cursor:pointer;font-family:ui-monospace,Consolas,monospace;font-size:12.5px}
  .env .methode{grid-area:methode}
  .env .champ{grid-area:champ;width:100%;font:inherit;font-size:13px;padding:3px 6px;background:var(--btn);color:var(--texte);border:1px solid var(--btn-bord);border-radius:4px}
  .env .champ.requis{border-color:var(--rouge);background:var(--rouge-fond)}
  .env .notes{grid-area:notes;font-size:12px;display:flex;flex-direction:column;gap:1px}
  .env .notes:empty{display:none}
  .note-fs{color:var(--orange)}.note-port{color:var(--bleu)}.note-info{color:var(--discret)}
  .methode{display:inline-flex;border:1px solid var(--btn-bord);border-radius:5px;overflow:hidden}
  .methode button{font:inherit;font-size:12px;padding:2px 9px;border:0;background:var(--btn);color:var(--texte);cursor:pointer}
  .methode button + button{border-left:1px solid var(--btn-bord)}
  .methode button[aria-pressed="true"]{background:var(--bleu);color:#fff}
  .methode button:disabled{opacity:.4;cursor:not-allowed}
  /* actions */
  .action{display:flex;align-items:center;gap:8px;padding:4px 0;font-size:13.5px;cursor:pointer}
  .action input{width:16px;height:16px;margin:0}
  .btn{display:inline-block;padding:6px 12px;border-radius:6px;border:1px solid var(--btn-bord);background:var(--btn);color:var(--texte);font:inherit;font-size:13px;cursor:pointer;text-align:center}
  .btn.p{background:var(--bleu);color:#fff;border-color:var(--bleu);font-weight:600}
  .btn.danger{color:var(--rouge);border-color:var(--rouge)}
  .btn:disabled{opacity:.45;cursor:not-allowed}
  .pile{display:flex;flex-direction:column;gap:6px}
  .avert{font-size:12px;color:var(--doux);border-left:3px solid var(--orange);padding:2px 0 2px 8px}
  #refus ul{margin:4px 0 0;padding-left:18px}
  .lien{background:none;border:none;color:var(--bleu);cursor:pointer;font:inherit;font-size:12px;padding:0;text-decoration:underline}
  /* suivi */
  #suivi{margin-top:14px}
  .bandeau{border-radius:6px;padding:8px 12px;margin-bottom:8px;font-size:13px;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
  .bandeau.echec{background:var(--rouge-fond);border:1px solid var(--rouge);border-left:6px solid var(--rouge)}
  .bandeau.avertissement{background:var(--orange-fond);border:1px solid var(--orange);border-left:6px solid var(--orange)}
  .bandeau.attente{background:var(--bleu-fond);border:1px solid var(--bleu);border-left:6px solid var(--bleu)}
  .bandeau b,.bandeau span{overflow-wrap:anywhere;min-width:0}
  .blocs{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(340px,100%),1fr));gap:10px;align-items:start}
  .bloc{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:10px 12px;display:flex;flex-direction:column;gap:6px;min-width:0}
  .bloc.echec{border-color:var(--rouge);box-shadow:inset 4px 0 0 var(--rouge)}
  .bloc.encours{border-color:var(--bleu)}
  .bloc .tete{display:flex;justify-content:space-between;gap:8px;align-items:baseline;flex-wrap:wrap}
  .bloc .tete strong{font-family:ui-monospace,Consolas,monospace;font-size:13px;overflow-wrap:anywhere}
  .rang{display:flex;flex-direction:column;gap:3px;padding-top:4px}
  .rang .libelle{display:flex;justify-content:space-between;gap:8px;font-size:12.5px}
  .rang .libelle span:last-child{color:var(--doux);text-align:right}
  .barre{height:8px;border-radius:4px;background:var(--piste);overflow:hidden}
  .barre span{display:block;height:100%;width:0;background:var(--bleu);border-radius:4px}
  .barre.succes span{background:var(--vert)}.barre.echec span{background:var(--rouge)}.barre.annulee span{background:var(--gris)}
  .barre.indet span{width:35%;animation:va 1.3s ease-in-out infinite alternate}
  @keyframes va{from{margin-left:0}to{margin-left:65%}}
  .durees{font-size:11.5px;color:var(--discret)}
  .commande{font:11px ui-monospace,Consolas,monospace;color:var(--discret);overflow-wrap:anywhere}
  .derniere{font:11px ui-monospace,Consolas,monospace;color:var(--discret);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  pre{font:11.5px/1.4 ui-monospace,Consolas,monospace;white-space:pre-wrap;word-break:break-word;margin:0}
  pre.extrait{background:var(--rouge-fond);color:var(--texte);border-radius:5px;padding:6px 8px;max-height:180px;overflow:auto}
  details.journal summary{cursor:pointer;font-size:12px;color:var(--bleu)}
  details.journal pre{background:var(--console);color:var(--console-texte);padding:8px;border-radius:6px;max-height:340px;overflow:auto;margin-top:4px}
  #recap{margin-top:10px}
  #recap .fichiers{color:var(--orange);margin-top:4px}
  .vide{color:var(--discret);font-size:13px}
  @media (max-width:820px){.disposition{grid-template-columns:1fr}.commandes{position:static}}
  @media (max-width:520px){
    main{padding:8px 16px 30px}
    .env{grid-template-columns:auto minmax(0,1fr) auto;grid-template-areas:"case nom methode" ". champ champ" ". notes notes"}
    .blocs{grid-template-columns:1fr}
  }
</style>
</head>
<body>
<main>
  <div class="entete">
    <div class="gauche"><h1>Build et téléversement</h1><span id="etat" class="puce">au repos</span></div>
    <label class="theme" for="theme">
      <span>Mode sombre</span>
      <input id="theme" type="checkbox" role="switch">
      <span class="interrupteur" aria-hidden="true"></span>
    </label>
  </div>
  <div id="message" class="erreur"></div>
  <div class="disposition">
    <section id="liste" aria-label="Environnements"><div class="vide">Lecture des environnements…</div></section>
    <aside class="commandes">
      <div class="carte">
        <h2>Actions</h2>
        <label class="action"><input type="checkbox" name="action" value="compiler"> Compiler le firmware</label>
        <label class="action"><input type="checkbox" name="action" value="upload"> Téléverser le firmware</label>
        <label class="action"><input type="checkbox" name="action" value="buildfs"> Construire le file system</label>
        <label class="action"><input type="checkbox" name="action" value="uploadfs"> Téléverser le file system</label>
        <p class="discret" style="margin:6px 0 0">Ordre dans un env : compiler → téléverser le firmware → construire le FS →
          téléverser le FS. Un échec arrête cet env ; les suivants continuent.</p>
      </div>
      <div class="carte pile">
        <button id="lancer" class="btn p" type="button" disabled>Lancer (0 env, l'un après l'autre)</button>
        <div id="refus" class="erreur"></div>
        <button id="arreter" class="btn" type="button" disabled>Arrêter après cet env</button>
        <button id="arret-immediat" class="btn danger" type="button" disabled>Arrêt immédiat</button>
        <div class="avert">Arrêt immédiat : le <code>pio</code> en cours est tué. Une carte en plein téléversement peut rester
          à moitié flashée, et des copies temporaires peuvent rester dans data/&lt;lieu&gt;/&lt;carte&gt; (la page ne les efface pas).</div>
        <div id="info-arret" class="discret"></div>
      </div>
    </aside>
  </div>
  <section id="suivi" class="carte" aria-live="polite">
    <h2>Suivi</h2>
    <div id="bandeaux"></div>
    <div id="blocs" class="blocs"></div>
    <div id="recap"></div>
    <div id="suivi-vide" class="vide">Aucun lancement depuis le démarrage de l'outil.</div>
  </section>
</main>

<script>
"use strict";
var $ = function (id) { return document.getElementById(id); };
var DELAI_APPEL = 15000;
var ACTIONS = ["compiler", "upload", "buildfs", "uploadfs"];
var LIBELLES = {compiler: "Compiler le firmware", upload: "Téléverser le firmware",
                buildfs: "Construire le file system", uploadfs: "Téléverser le file system"};
var FAMILLES = [["cartes", "Mes cartes", true], ["bases", "Mes bases", true], ["amont", "Tasmota (amont)", false]];
var SOUS_GROUPES = [["safeboot", "Safeboot"], ["esp32", "ESP32"], ["langues", "Langues"], ["esp8266", "ESP8266"]];
var ETAPES_COMPILATION = ["Pré-build", "Compilation", "Édition des liens"];
var STATUTS = {succes: "réussi", echec: "échec", annulee: "annulée", arrete: "arrêté"};
var PORT = /^COM\d{1,3}$/i;
var IPV4 = /^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$/;

var envs = [], parNom = {}, choix = {}, ui = {}, uiBlocs = {}, enCours = false, dernierN = 0, fluxCoupe = false;
var L = null;                 // lancement suivi : {lignes, actions, blocs, ordre, bandeaux, attente, fin}
var aDessiner = {}, minuterie = null;

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

// Appel HTTP qui ne leve jamais : {ok, statut, donnees, texte}. Les POST portent X-Build: 1.
async function appel(url, corps) {
  var ctrl = new AbortController();
  var minuteur = setTimeout(function () { ctrl.abort(); }, DELAI_APPEL);
  var opts = {cache: "no-store", signal: ctrl.signal};
  if (corps !== undefined) {
    opts.method = "POST";
    opts.headers = {"X-Build": "1", "Content-Type": "application/json"};
    opts.body = JSON.stringify(corps);
  }
  try {
    var r = await fetch(url, opts);
    var texte = await r.text();
    clearTimeout(minuteur);
    var donnees = null;
    try { donnees = JSON.parse(texte); } catch (e) { donnees = null; }
    return {ok: r.ok, statut: r.status, donnees: donnees, texte: texte};
  } catch (e) {
    clearTimeout(minuteur);
    return {ok: false, statut: 0, donnees: null,
            texte: ctrl.signal.aborted ? "pas de réponse en " + (DELAI_APPEL / 1000) + " s" : "outil injoignable"};
  }
}

function duree(s) {
  if (s === null || s === undefined) return "";
  if (s < 10) return s.toFixed(1).replace(".", ",") + " s";
  if (s < 60) return Math.round(s) + " s";
  var m = Math.floor(s / 60), r = Math.round(s - m * 60);
  if (r === 60) { m += 1; r = 0; }
  return m + " min " + (r < 10 ? "0" : "") + r + " s";
}

function actionsCochees() {
  return ACTIONS.filter(function (a) { return document.querySelector('input[name=action][value="' + a + '"]').checked; });
}
function aUnEnvoi(actions) { return actions.indexOf("upload") >= 0 || actions.indexOf("uploadfs") >= 0; }

// ---------- liste des environnements ----------
function valeurInitiale(e, d) {
  var methode = d && d.methode === "ota" && e.ota_possible ? "ota" : "com";
  var port = e.ecrivable ? e.port : ((d && d.port) || e.port);
  var ip = e.ip || (d && d.ip) || "";
  return {coche: !!d, methode: methode, port: port || "", ip: ip, note: "", erreur: ""};
}

function construitListe(donnees) {
  envs = donnees.envs || [];
  parNom = {};
  envs.forEach(function (e) { parNom[e.nom] = e; });
  var derniers = {};
  ((donnees.derniers && donnees.derniers.lignes) || []).forEach(function (l) { derniers[l.env] = l; });
  envs.forEach(function (e) { if (!choix[e.nom]) choix[e.nom] = valeurInitiale(e, derniers[e.nom]); });
  var acts = (donnees.derniers && donnees.derniers.actions) || null;
  if (acts && !construitListe.dejaFait)
    ACTIONS.forEach(function (a) { document.querySelector('input[name=action][value="' + a + '"]').checked = acts.indexOf(a) >= 0; });
  construitListe.dejaFait = true;

  var liste = $("liste");
  liste.textContent = "";
  ui = {};
  FAMILLES.forEach(function (f) {
    var membres = envs.filter(function (e) { return e.famille === f[0]; });
    if (!membres.length) return;
    var compte = h("span", {"class": "compte"});
    var fam = h("details", {"class": "famille", "data-famille": f[0]}, h("summary", {}, f[1], compte));
    fam.open = f[2] || membres.some(function (e) { return choix[e.nom].coche; });
    if (f[0] === "amont") {
      SOUS_GROUPES.forEach(function (g) {
        var sous = membres.filter(function (e) { return e.sous_groupe === g[0]; });
        if (!sous.length) return;
        var c2 = h("span", {"class": "compte"});
        var det = h("details", {"class": "sous-groupe", "data-sous-groupe": g[0]}, h("summary", {}, g[1], c2));
        det.open = sous.some(function (e) { return choix[e.nom].coche; });
        sous.forEach(function (e) { det.appendChild(ligneEnv(e)); });
        det._compte = [c2, sous];
        fam.appendChild(det);
      });
    } else {
      membres.forEach(function (e) { fam.appendChild(ligneEnv(e)); });
    }
    fam._compte = [compte, membres];
    liste.appendChild(fam);
  });
  majTout();
}

function ligneEnv(e) {
  var c = choix[e.nom];
  var caseEnv = h("input", {type: "checkbox", id: "env-" + e.nom});
  caseEnv.checked = c.coche;
  caseEnv.onchange = function () { c.coche = caseEnv.checked; majTout(); };
  var bCom = h("button", {type: "button", texte: "COM", title: "Téléverser par le câble (port COM)"});
  var bOta = h("button", {type: "button", texte: "OTA", title: e.ota_possible ? "Téléverser par le réseau (OTA)" :
    "OTA impossible : cet environnement ne charge pas le pré-script du dépôt (ESP8266…)"});
  bOta.disabled = !e.ota_possible;
  bCom.onclick = function () { c.methode = "com"; majLigne(e.nom); majBouton(); };
  bOta.onclick = function () { c.methode = "ota"; majLigne(e.nom); majBouton(); };
  var champ = h("input", {"class": "champ", type: "text", autocomplete: "off", spellcheck: "false"});
  champ.oninput = function () {
    if (c.methode === "com") c.port = champ.value; else c.ip = champ.value;
    c.erreur = "";
    if (c.methode === "ota") majLigne(e.nom);
  };
  champ.onchange = function () { if (c.methode === "com") changePort(e.nom); else majLigne(e.nom); };
  var notes = h("div", {"class": "notes"});
  var ligne = h("div", {"class": "env", "data-env": e.nom}, caseEnv,
    h("label", {"class": "nom", "for": "env-" + e.nom, texte: e.nom, title: e.firmware || ""}),
    h("span", {"class": "methode", role: "group", "aria-label": "Méthode d'envoi"}, bCom, bOta), champ, notes);
  ui[e.nom] = {ligne: ligne, caseEnv: caseEnv, bCom: bCom, bOta: bOta, champ: champ, notes: notes};
  majLigne(e.nom);
  return ligne;
}

function majLigne(nom) {
  var e = parNom[nom], c = choix[nom], u = ui[nom];
  if (!u) return;
  var acts = actionsCochees();
  u.ligne.classList.toggle("coche", c.coche);
  u.bCom.setAttribute("aria-pressed", String(c.methode === "com"));
  u.bOta.setAttribute("aria-pressed", String(c.methode === "ota"));
  var champ = u.champ;
  if (c.methode === "com") {
    if (document.activeElement !== champ) champ.value = c.port;
    champ.placeholder = "COMn";
    champ.title = e.ecrivable ? "Port écrit dans platformio_tasmota_cenv.ini à la validation" :
                                "Env amont : port valable pour ce lancement seulement";
    champ.classList.remove("requis");
  } else {
    if (document.activeElement !== champ) champ.value = c.ip;
    champ.placeholder = "IP à saisir";
    champ.title = "Adresse IP de la carte (OTA)";
    champ.classList.toggle("requis", !c.ip.trim());
  }
  var notes = [];
  if (c.erreur) notes.push(["erreur", c.erreur]);
  if (c.methode === "com" && e.port_herite && c.port === e.port) notes.push(["note-info", "port hérité (extends)"]);
  if (c.note && c.methode === "com") notes.push(["note-port", c.note]);
  if (c.methode === "ota") {
    if (!c.ip.trim()) notes.push(["erreur", "IP à saisir : aucune adresse connue pour cet env (WIFI_IP_ADDRESS absente ou 0.0.0.0)"]);
    else if (!IPV4.test(c.ip.trim())) notes.push(["erreur", "adresse IPv4 invalide"]);
    else if (c.ip.trim() !== e.ip) notes.push(["note-info", "IP valable pour ce lancement seulement (user_config_override.h n'est pas modifié)"]);
  }
  if (c.coche && c.methode === "com" && acts.indexOf("upload") >= 0 && e.littlefs)
    notes.push(["note-fs", "le file system (persist compris) sera aussi flashé : littlefs.bin existe pour cet env"]);
  u.notes.textContent = "";
  notes.forEach(function (n) { u.notes.appendChild(h("div", {"class": n[0], texte: n[1]})); });
}

function majComptes() {
  document.querySelectorAll("details.famille, details.sous-groupe").forEach(function (d) {
    if (!d._compte) return;
    var n = d._compte[1].filter(function (e) { return choix[e.nom].coche; }).length;
    d._compte[0].textContent = "(" + d._compte[1].length + (n ? " · " + n + " coché" + (n > 1 ? "s" : "") : "") + ")";
  });
}

function envsCoches() { return envs.filter(function (e) { return choix[e.nom].coche; }); }

function majBouton() {
  var n = envsCoches().length;
  var b = $("lancer");
  b.textContent = "Lancer (" + n + " env, l'un après l'autre)";
  b.disabled = enCours || !n || !actionsCochees().length;
  $("arreter").disabled = !enCours;
  $("arret-immediat").disabled = !enCours;
}

function majTout() {
  Object.keys(ui).forEach(majLigne);
  majComptes();
  majBouton();
}

// Port d'un env : ecrit dans le .ini si l'env est ecrivable (POST /port), sinon garde pour le lancement.
async function changePort(nom) {
  var e = parNom[nom], c = choix[nom];
  var v = c.port.trim().toUpperCase();
  c.port = v;
  c.erreur = "";
  if (v && !PORT.test(v)) { c.erreur = "port invalide : COMn attendu"; majLigne(nom); return; }
  if (!e.ecrivable) {
    c.note = "port valable pour ce lancement seulement (env amont : aucun fichier modifié)";
    majLigne(nom);
    return;
  }
  if (v === e.port) { majLigne(nom); return; }
  c.note = "écriture dans platformio_tasmota_cenv.ini…";
  majLigne(nom);
  var r = await appel("/port", {env: nom, port: v});
  if (r.ok) {
    await chargeEnvs(true);
    var effectif = parNom[nom] ? parNom[nom].port : v;
    c.port = effectif;
    c.note = (v ? "upload_port = " + v + " écrit" : "ligne upload_port retirée" + (effectif ? " (port hérité : " + effectif + ")" : "")) +
             " dans platformio_tasmota_cenv.ini : le prochain build repartira de zéro (empreinte du projet changée)";
  } else {
    c.note = "";
    c.erreur = "port non écrit : " + (r.texte || ("HTTP " + r.statut)) + " (valeur gardée pour le lancement)";
  }
  majLigne(nom);
}

async function chargeEnvs(rafraichir) {
  var r = await appel("/envs");
  if (!r.ok || !r.donnees || !Array.isArray(r.donnees.envs)) {
    $("message").textContent = "Liste des environnements indisponible : " + (r.texte || r.statut) + " (nouvel essai dans 3 s)";
    setTimeout(function () { chargeEnvs(rafraichir); }, 3000);
    return;
  }
  $("message").textContent = "";
  if (rafraichir && envs.length) {          // garde cases, methodes et saisies ; met a jour port, littlefs...
    r.donnees.envs.forEach(function (e) {
      var c = choix[e.nom], ancien = parNom[e.nom];
      if (c && ancien && c.port === ancien.port && e.ecrivable) c.port = e.port;
    });
  }
  var ouverts = {};
  document.querySelectorAll("details[data-famille], details[data-sous-groupe]").forEach(function (d) {
    ouverts[d.getAttribute("data-famille") || d.getAttribute("data-sous-groupe")] = d.open;
  });
  construitListe(r.donnees);
  document.querySelectorAll("details[data-famille], details[data-sous-groupe]").forEach(function (d) {
    var k = d.getAttribute("data-famille") || d.getAttribute("data-sous-groupe");
    if (k in ouverts) d.open = ouverts[k] || d.open;
  });
}

document.querySelectorAll("input[name=action]").forEach(function (i) { i.onchange = majTout; });

// ---------- lancement et arret ----------
$("lancer").onclick = async function () {
  var acts = actionsCochees(), envoi = aUnEnvoi(acts), bloque = false;
  var lignes = envsCoches().map(function (e) {
    var c = choix[e.nom];
    var l = {env: e.nom, methode: c.methode, port: c.port.trim().toUpperCase(), ip: c.ip.trim()};
    if (envoi && c.methode === "ota" && !IPV4.test(l.ip)) { c.erreur = "IP à saisir avant de lancer"; bloque = true; }
    if (envoi && c.methode === "com" && !PORT.test(l.port)) { c.erreur = "port COM à saisir avant de lancer"; bloque = true; }
    return l;
  });
  $("refus").textContent = "";
  majTout();
  if (bloque) { $("refus").textContent = "Lancement impossible : compléter les champs signalés en rouge."; return; }
  $("lancer").disabled = true;
  var r = await appel("/lancer", {lignes: lignes, actions: acts});
  if (r.ok) enCours = true;
  if (!r.ok) {
    var ul = h("ul", {});
    (r.texte || ("HTTP " + r.statut)).split(" ; ").forEach(function (m) { ul.appendChild(h("li", {texte: m})); });
    $("refus").appendChild(h("div", {texte: "Lancement refusé :"}));
    $("refus").appendChild(ul);
  } else {
    $("info-arret").textContent = "";
    $("suivi").scrollIntoView({block: "start", behavior: "smooth"});
  }
  majBouton();
};

$("arreter").onclick = async function () {
  var r = await appel("/arreter", {immediat: false});
  $("info-arret").textContent = r.ok ? "Arrêt demandé : la série s'arrêtera à la fin de l'env en cours." :
                                       "Arrêt refusé : " + r.texte;
};
$("arret-immediat").onclick = async function () {
  if (!confirm("Arrêt immédiat : le pio en cours est tué.\n\nUne carte en plein téléversement peut rester à moitié " +
               "flashée, et des copies temporaires peuvent rester dans data/<lieu>/<carte> (la page ne les efface pas).\n\n" +
               "Un envoi OTA en cours n'est pas coupé : la série s'arrête à sa fin.\n\nContinuer ?")) return;
  var r = await appel("/arreter", {immediat: true});
  $("info-arret").textContent = r.ok ? "Arrêt immédiat demandé." : "Arrêt refusé : " + r.texte;
};

// ---------- suivi : evenements du flux ----------
function nouveauBloc(l, actions) {
  var b = {env: l.env, methode: l.methode, port: l.port, ip: l.ip, actions: actions.slice(), statut: "attente",
           rangs: {}, secondes: null, motif: "", extrait: [], derniere: "", fsAussi: false, repris: false};
  actions.forEach(function (a) { b.rangs[a] = nouveauRang(a); });
  return b;
}
function nouveauRang(a) {
  return {action: a, etape: "", pourcent: null, detail: "", durees: [], statut: null, commande: "", actif: false, prepa: false};
}
function assureL() {
  if (!L) L = {lignes: [], actions: [], blocs: {}, ordre: [], bandeaux: [], attente: null, fin: null};
}
function bloc(env) {
  assureL();
  if (!L.blocs[env]) { L.blocs[env] = nouveauBloc({env: env, methode: "", port: "", ip: ""}, L.actions); L.ordre.push(env); }
  return L.blocs[env];
}

// Ligne du bloc a laquelle rattacher un evenement (pas de ligne « fantome », voir la docstring du module).
function rang(b, action, etape) {
  var a = action, prepa = false;
  if (a === "buildfs" && b.actions.indexOf("buildfs") < 0 && b.actions.indexOf("uploadfs") >= 0) { a = "uploadfs"; prepa = true; }
  else if (a === "upload" && b.actions.indexOf("compiler") >= 0 && ETAPES_COMPILATION.indexOf(etape) >= 0) a = "compiler";
  if (!b.rangs[a]) { b.rangs[a] = nouveauRang(a); if (b.actions.indexOf(a) < 0) b.actions.push(a); }
  var r = b.rangs[a];
  return {r: r, prepa: prepa, a: a};
}

function rangActif(b) {
  for (var a in b.rangs) if (b.rangs[a].actif) return {r: b.rangs[a], prepa: b.rangs[a].prepa, a: a};
  return null;
}

function activeRang(b, r) {
  Object.keys(b.rangs).forEach(function (k) {
    var autre = b.rangs[k];
    if (autre !== r && autre.actif) {
      autre.actif = false;
      if (autre.statut === null && autre.action === "compiler" && r.action === "upload") autre.pourcent = 100;
    }
  });
  r.actif = true;
}

function traite(e) {
  if (typeof e.n === "number") {
    if (e.n === 1 && dernierN > 1) dernierN = 0;   // outil redemarre sous la page : numerotation repartie de 1
    if (e.n <= dernierN) return;          // deja vu (reprise du flux)
    dernierN = e.n;
  }
  var b, x;
  if (e.type === "debut" && e.env === null) {
    L = {lignes: e.lignes || [], actions: e.actions || [], blocs: {}, ordre: [], bandeaux: [], attente: null, fin: null};
    L.lignes.forEach(function (l) { L.blocs[l.env] = nouveauBloc(l, L.actions); L.ordre.push(l.env); });
    enCours = true;
    construitSuivi();
  } else if (e.type === "debut") {
    b = bloc(e.env);
    b.statut = "encours";
    if (e.actions) { b.actions = e.actions.slice(); e.actions.forEach(function (a) { if (!b.rangs[a]) b.rangs[a] = nouveauRang(a); }); }
    b.methode = e.methode || b.methode; b.port = e.port || b.port; b.ip = e.ip || b.ip;
    planifie(e.env);
  } else if (e.type === "etape") {
    b = bloc(e.env);
    x = rang(b, e.action, e.etape);
    activeRang(b, x.r);
    x.r.prepa = x.prepa;
    x.r.etape = e.etape || x.r.etape;
    x.r.pourcent = (e.pourcent === null || e.pourcent === undefined) ? null : e.pourcent;
    x.r.detail = e.detail || "";
    if (e.commande) x.r.commande = e.commande;
    if (x.r.detail.indexOf("AVERTISSEMENT") === 0)
      L.bandeaux.push({genre: "avertissement", env: e.env, titre: "Avertissement — " + e.env + " · " + LIBELLES[x.a] +
                       " · " + x.r.etape, texte: x.r.detail});
    planifie(e.env);
  } else if (e.type === "duree") {
    b = bloc(e.env);
    x = rang(b, e.action, e.etape);
    x.r.durees.push({etape: (x.prepa ? "préparation : " : "") + e.etape, secondes: e.secondes});
    planifie(e.env);
  } else if (e.type === "ligne") {
    b = bloc(e.env);
    b.derniere = e.texte || "";
    if (/Utilisera une commande de téléchargement personnalisée/.test(b.derniere) && !b.fsAussi) { b.fsAussi = true; planifie(e.env); }
    if (uiBlocs[e.env] && b.statut === "encours") uiBlocs[e.env].derniere.textContent = b.derniere;
  } else if (e.type === "echec") {
    if (e.env === null || e.env === undefined) {
      assureL();
      L.bandeaux.push({genre: "echec", env: "", titre: "Échec de la série", texte: e.motif || ""});
    } else {
      b = bloc(e.env);
      x = rangActif(b) || rang(b, e.action || b.actions[0], null);
      x.r.statut = "echec";
      b.motif = e.motif || "";
      b.extrait = e.extrait || [];
      L.bandeaux.push({genre: "echec", env: e.env, titre: "Échec — " + e.env + " · " + (LIBELLES[x.a] || e.action) +
                       (x.r.etape ? " · étape « " + x.r.etape + " »" : ""), texte: b.motif});
      planifie(e.env);
    }
  } else if (e.type === "fin_env") {
    b = bloc(e.env);
    b.statut = e.resultat || "succes";
    b.secondes = e.secondes;
    Object.keys(e.statuts || {}).forEach(function (a) {
      var r = b.rangs[a] || (b.rangs[a] = nouveauRang(a));
      r.statut = e.statuts[a];
      r.actif = false;
      if (r.statut === "succes") r.pourcent = 100;
    });
    planifie(e.env);
  } else if (e.type === "attente") {
    bloc(e.env);
    if (e.builds && e.builds.length) L.attente = {env: e.env, builds: e.builds};
    else { L.attente = null; L.blocs[e.env].repris = true; planifie(e.env); }
  } else if (e.type === "fin") {
    assureL();
    L.fin = e;
    L.attente = null;
    enCours = false;
    majBouton();
    chargeEnvs(true);              // littlefs.bin a pu apparaitre (buildfs)
  }
  if (e.type !== "ligne") { majEtat(); planifie(null); }
}

function majEtat() {
  var etat = $("etat");
  if (fluxCoupe) { etat.textContent = "flux coupé : reconnexion…"; etat.className = "puce alerte"; }
  else if (enCours) { etat.textContent = L && L.attente ? "en attente d'un autre build" : "lancement en cours"; etat.className = "puce encours"; }
  else if (L && L.fin) {
    var ko = (L.fin.echecs || []).length;
    etat.textContent = L.fin.resultat === "arrete" ? "arrêté" : (ko ? "terminé avec " + ko + " échec" + (ko > 1 ? "s" : "") : "terminé");
    etat.className = "puce " + (ko || L.fin.resultat === "arrete" ? "erreur" : "ok");
  } else { etat.textContent = "au repos"; etat.className = "puce"; }
  majBouton();
}

// Rendu groupe : plusieurs evenements -> un seul dessin (le flux peut rejouer des milliers d'evenements).
function planifie(env) {
  if (env !== null && env !== undefined) aDessiner[env] = true;
  if (minuterie) return;
  minuterie = setTimeout(function () {
    minuterie = null;
    var lot = aDessiner;
    aDessiner = {};
    Object.keys(lot).forEach(dessineBloc);
    dessineBandeaux();
    dessineRecap();
  }, 60);
}

// Squelette des blocs (cree une fois par lancement : le journal deplie garde son etat).
function construitSuivi() {
  var zone = $("blocs");
  zone.textContent = "";
  uiBlocs = {};
  $("suivi-vide").style.display = L ? "none" : "";
  if (!L) return;
  L.ordre.forEach(function (env) { squelette(env); aDessiner[env] = true; });
}

function squelette(env) {
  var pre = h("pre", {texte: "…"});
  var journal = h("details", {"class": "journal"}, h("summary", {texte: "Journal complet (dernier lancement)"}), pre,
    h("button", {"class": "lien", type: "button", texte: "recharger", onclick: function () { chargeJournal(env, pre); }}));
  journal.ontoggle = function () { if (journal.open) chargeJournal(env, pre); };
  var u = {tete: h("div", {"class": "tete"}), rangs: h("div", {}), notes: h("div", {}), extrait: h("div", {}),
           derniere: h("div", {"class": "derniere"}), journal: journal};
  u.bloc = h("div", {"class": "bloc", "data-bloc": env}, u.tete, u.rangs, u.notes, u.extrait, u.derniere, journal);
  uiBlocs[env] = u;
  $("blocs").appendChild(u.bloc);
  return u;
}

async function chargeJournal(env, pre) {
  pre.textContent = "lecture…";
  var r = await appel("/journal?env=" + encodeURIComponent(env));
  pre.textContent = r.ok ? (r.texte || "(journal vide : cet env n'a pas encore lancé de pio)") : "Journal indisponible : " + r.texte;
  pre.scrollTop = pre.scrollHeight;
}

function dessineBloc(env) {
  if (!L || !L.blocs[env] || env === "") return;
  var b = L.blocs[env];
  var u = uiBlocs[env] || squelette(env);
  $("suivi-vide").style.display = "none";
  u.bloc.className = "bloc" + (b.statut === "echec" ? " echec" : b.statut === "encours" ? " encours" : "");
  var classe = {attente: "", encours: "encours", succes: "ok", echec: "erreur", arrete: "alerte"}[b.statut] || "";
  var libelle = {attente: "en attente", encours: "en cours"}[b.statut] || STATUTS[b.statut] || b.statut;
  var methode = b.methode === "ota" ? "OTA " + (b.ip || "?") : (b.port ? "COM · " + b.port : "COM");
  u.tete.textContent = "";
  u.tete.appendChild(h("strong", {texte: env}));
  u.tete.appendChild(h("span", {}, h("span", {"class": "discret", texte: methode + "  "}),
    h("span", {"class": "puce " + classe, texte: libelle + (b.secondes !== null ? " · " + duree(b.secondes) : "")})));
  u.rangs.textContent = "";
  ACTIONS.filter(function (a) { return b.rangs[a]; }).forEach(function (a) { u.rangs.appendChild(dessineRang(b, b.rangs[a])); });
  u.notes.textContent = "";
  if (b.fsAussi) u.notes.appendChild(h("div", {"class": "note-fs", texte: "Le file system (persist compris) est aussi flashé avec le firmware."}));
  if (b.repris) u.notes.appendChild(h("div", {"class": "discret", texte: "Reprise après l'attente d'un autre build."}));
  u.extrait.textContent = "";
  if (b.motif) u.extrait.appendChild(h("div", {"class": "erreur", texte: b.motif}));
  if (b.extrait && b.extrait.length) u.extrait.appendChild(h("pre", {"class": "extrait", texte: b.extrait.join("\n")}));
  u.derniere.textContent = b.statut === "encours" ? b.derniere : "";
}

function dessineRang(b, r) {
  var enCoursB = b.statut === "encours";
  var etape = r.etape ? (r.prepa ? "Préparation — " : "") + r.etape : "";
  var droite;
  if (r.statut) droite = STATUTS[r.statut] + (r.statut === "succes" ? " · 100 %" : "");
  else if (r.actif && enCoursB) droite = etape + (r.detail ? " · " + r.detail : "") + (r.pourcent !== null ? " · " + r.pourcent + " %" : "");
  else if (r.pourcent === 100) droite = "terminé";
  else droite = enCoursB || b.statut === "attente" ? "à venir" : "";
  var barre = h("div", {"class": "barre" + (r.statut ? " " + r.statut : (r.actif && enCoursB && r.pourcent === null ? " indet" : ""))},
                h("span", {}));
  var p = r.statut === "succes" ? 100 : r.statut === "annulee" ? 0 : (r.pourcent || 0);
  if (!(r.actif && enCoursB && r.pourcent === null && !r.statut)) barre.firstChild.style.width = p + "%";
  if (r.statut === "echec") barre.firstChild.style.width = Math.max(p, 4) + "%";
  return h("div", {"class": "rang", "data-action": r.action, "data-pourcent": String(r.statut === "succes" ? 100 : r.pourcent)},
    h("div", {"class": "libelle"}, h("span", {texte: LIBELLES[r.action] || r.action}), h("span", {texte: droite})),
    barre,
    r.durees.length ? h("div", {"class": "durees", texte: r.durees.map(function (d) { return d.etape + " " + duree(d.secondes); }).join(" · ")}) : null,
    r.commande && (r.actif || r.statut === "echec") ? h("div", {"class": "commande", texte: r.commande}) : null);
}

function dessineBandeaux() {
  var zone = $("bandeaux");
  zone.textContent = "";
  if (!L) return;
  if (L.attente) {
    var b = L.attente.builds;
    var texte = b.indexOf("détection impossible") >= 0 && b.length === 1 ?
      "Détection des builds en cours impossible (PowerShell en erreur ou trop lent) : la série attend avant " + L.attente.env +
      " et réessaie toutes les 5 s." :
      "Un build tourne ailleurs (" + b.join(", ") + ") : la série attend avant " + L.attente.env +
      " et reprendra seule à sa fin. « Arrêter après cet env » annule la suite.";
    zone.appendChild(h("div", {"class": "bandeau attente"}, h("b", {texte: "En attente"}), h("span", {texte: texte})));
  }
  L.bandeaux.forEach(function (x) {
    var d = h("div", {"class": "bandeau " + x.genre, "data-env": x.env}, h("b", {texte: x.titre}), h("span", {texte: x.texte}));
    if (x.env) d.appendChild(h("button", {"class": "lien", type: "button", texte: "voir le bloc", onclick: function () {
      var u = uiBlocs[x.env]; if (u) u.bloc.scrollIntoView({block: "center", behavior: "smooth"}); }}));
    zone.appendChild(d);
  });
}

function dessineRecap() {
  var zone = $("recap");
  zone.textContent = "";
  if (!L || !L.fin) return;
  var f = L.fin;
  var ok = f.succes || [], ko = f.echecs || [], nl = f.non_lances || [];
  var t = (f.resultat === "arrete" ? "Lancement arrêté" : "Lancement terminé") + " : " + ok.length + " réussi" + (ok.length > 1 ? "s" : "") +
          ", " + ko.length + " échec" + (ko.length > 1 ? "s" : "") + (ko.length ? " (" + ko.join(", ") + ")" : "") +
          (nl.length ? ", " + nl.length + " non lancé" + (nl.length > 1 ? "s" : "") + " (" + nl.join(", ") + ")" : "") + ".";
  zone.appendChild(h("div", {"class": ko.length ? "erreur" : "", style: "font-size:13px", texte: t}));
  if (f.fichiers_modifies && f.fichiers_modifies.length)
    zone.appendChild(h("div", {"class": "fichiers", texte: "Fichiers réécrits par le build, à commiter : " + f.fichiers_modifies.join(", ")}));
  var immediat = Object.keys(L.blocs).some(function (k) { return /^arrêt immédiat/.test(L.blocs[k].motif); });
  if (immediat)
    zone.appendChild(h("div", {"class": "avert", texte: "Arrêt immédiat : vérifier la carte (peut-être à moitié flashée) et les copies " +
      "temporaires laissées dans data/<lieu>/<carte> par le pré-script : la page ne les efface pas."}));
}

// ---------- flux SSE (reprise automatique : EventSource renvoie Last-Event-ID) ----------
// Outil redemarre sous la page (il meurt avec VS Code, l'onglet reste) : le serveur rejoue depuis 0 un
// Last-Event-ID plus grand que sa numerotation (build_web.py) et traite() repart a n === 1. Un lancement
// coupe par ce redemarrage n'enverra jamais `fin` : a la reconnexion, /execution dit s'il tourne encore.
async function verifieExecution() {
  var r = await appel("/execution");
  if (!r.ok || !r.donnees || r.donnees.en_cours || !enCours) return;
  enCours = false;
  if (L && !L.fin) {
    L.ordre.forEach(function (env) { var b = L.blocs[env]; if (b.statut === "encours" || b.statut === "attente") { b.statut = "arrete"; planifie(env); } });
    L.bandeaux.push({genre: "avertissement", env: "", titre: "Lancement interrompu",
                     texte: "l'outil a redémarré pendant le lancement : vérifier les cartes concernées (fin jamais reçue)."});
    L.attente = null;
  }
  majEtat();
  planifie(null);
}

function ecoute() {
  var source = new EventSource("/flux?depuis=0");
  source.onmessage = function (m) {
    var e;
    try { e = JSON.parse(m.data); } catch (err) { return; }
    traite(e);
  };
  source.onerror = function () {
    fluxCoupe = true; majEtat();
    // ferme pour de bon (reponse non 200 pendant un redemarrage) : rouvrir ; le rejeu depuis 0 repart a n === 1
    if (source.readyState === EventSource.CLOSED) setTimeout(ecoute, 3000);
  };
  source.onopen = function () { if (fluxCoupe) { fluxCoupe = false; majEtat(); setTimeout(verifieExecution, 1500); } };   // apres le rejeu eventuel
}

// Interrupteur clair / sombre (theme pose par le script du <head>, memorise ici).
$("theme").checked = document.documentElement.getAttribute("data-theme") === "sombre";
$("theme").onchange = function () {
  var t = this.checked ? "sombre" : "clair";
  document.documentElement.setAttribute("data-theme", t);
  try { localStorage.setItem("build-theme", t); } catch (e) {}
};

async function demarre() {
  await chargeEnvs(false);
  var r = await appel("/execution");
  if (r.ok && r.donnees) { enCours = !!r.donnees.en_cours || enCours; majEtat(); }
  ecoute();
}
demarre();
</script>
</body>
</html>
"""
