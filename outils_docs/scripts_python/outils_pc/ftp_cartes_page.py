"""Page « Navigateur FTP des cartes » (ftp_cartes_web.py), modele A de la spec : explorateur a deux volets (arbre, tableau, actions).

Tout ce qui vient de la carte (noms de fichiers, messages) est insere par textContent ou creation de noeuds, jamais par innerHTML.
Aucune ressource externe. Le FTP de la carte s'allume au choix d'une carte et s'eteint a « Deconnecter » ou a la fermeture du DERNIER onglet
(pagehide + sendBeacon sur /ferme avec l'identifiant de l'onglet) ; le serveur compte aussi 15 min d'inactivite et 90 s sans sondage d'onglet.
La page sonde /etat?onglet= toutes les 5 s pour que la pastille suive (fermeture par un autre onglet, inactivite, carte redemarree) et pour
se signaler. Sonde : test_ftp_cartes_page_chrome.py (+ _onglets.py).
"""
import json

import lieux

CSS = """
:root{color-scheme:light;--fond:#f6f7f9;--carte:#fff;--bord:#ddd;--texte:#222;--doux:#666;--bleu:#2563eb;--vert:#1e7e3a;--rouge:#c62828;--orange:#8a5300;
  --btn:#fff;--btn-bord:#888;--piste:#e9e9ea;--champ:#fff;--sur-bleu:#fff;--coche:rgba(37,99,235,.12);--interrupteur:#fff;--interrupteur-on:#34c759;--ombre:rgba(0,0,0,.3)}
:root[data-theme="sombre"]{color-scheme:dark;--fond:#121417;--carte:#1d2025;--bord:#3a3f47;--texte:#e6e6e6;--doux:#a8adb5;--bleu:#5b93ff;
  --vert:#3fbf63;--rouge:#ff6b6b;--orange:#e0a040;--btn:#262a30;--btn-bord:#555b64;--piste:#39393d;--champ:#15171b;--sur-bleu:#0b0d10;--coche:rgba(91,147,255,.2)}
*{box-sizing:border-box}
body{margin:0;font:14px system-ui,sans-serif;color:var(--texte);background:var(--fond)}
main{max-width:1200px;margin:0 auto;padding:12px 16px 24px}
header{display:flex;align-items:baseline;gap:14px;margin-bottom:10px;flex-wrap:wrap}
h1{font-size:20px;margin:0}
.theme{margin-left:auto;align-self:center;display:flex;align-items:center;gap:8px;font-size:13px;color:var(--doux);cursor:pointer;user-select:none}
.theme input{position:absolute;opacity:0;width:1px;height:1px;margin:0}
.interrupteur{position:relative;flex:none;width:2.6em;height:1.5em;border-radius:.75em;background:var(--piste);transition:background .2s}
.interrupteur::after{content:"";position:absolute;top:.15em;left:.15em;width:1.2em;height:1.2em;border-radius:50%;background:var(--interrupteur);
  box-shadow:0 1px 3px var(--ombre);transition:transform .2s}
.theme input:checked + .interrupteur{background:var(--interrupteur-on)}
.theme input:checked + .interrupteur::after{transform:translateX(1.1em)}
.theme input:focus-visible + .interrupteur{outline:2px solid var(--bleu);outline-offset:2px}
.doux{color:var(--doux)} .petit{font-size:12px} [hidden]{display:none!important}
.cadre{background:var(--carte);border:1px solid var(--bord);border-radius:8px;overflow:hidden}
.barre,.actions{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:8px}
.barre{border-bottom:1px solid var(--bord)} .actions{border-top:1px solid var(--bord)}
select,input[type=text]{font:inherit;padding:5px 8px;border:1px solid var(--bord);border-radius:5px;background:var(--champ);color:var(--texte);max-width:100%}
.btn{display:inline-block;padding:5px 11px;border:1px solid var(--btn-bord);border-radius:6px;background:var(--btn);font:inherit;color:inherit;cursor:pointer}
.btn:disabled{opacity:.45;cursor:not-allowed}
.btn.prim,.btn[aria-pressed=true]{background:var(--bleu);border-color:var(--bleu);color:var(--sur-bleu)}
.btn.danger{color:var(--rouge);border-color:var(--rouge)}
.bascule{display:inline-flex} .bascule .btn:first-child{border-radius:6px 0 0 6px} .bascule .btn:last-child{border-radius:0 6px 6px 0;margin-left:-1px}
.pastille{font-weight:600} .pastille[data-etat=actif]{color:var(--vert)} .pastille[data-etat=allumage]{color:var(--orange)}
.pastille[data-etat=erreur]{color:var(--rouge)} .pastille[data-etat=eteint]{color:var(--doux)}
.corps{display:flex;min-height:260px}
.arbre{width:32%;min-width:150px;padding:8px;border-right:1px solid var(--bord);overflow:auto;font-size:13px}
.enfants{margin-left:14px}
.noeud>button{background:none;border:0;color:var(--texte);font:inherit;cursor:pointer;padding:2px 4px;border-radius:4px;text-align:left;overflow-wrap:anywhere}
.noeud>button:hover,.noeud>button.courant{background:var(--coche)} .noeud>button.courant{font-weight:600}
.liste{flex:1;min-width:0;overflow:auto}
.fil{display:flex;gap:8px;align-items:center;padding:6px 8px;border-bottom:1px solid var(--bord);font-family:ui-monospace,Consolas,monospace;font-size:13px}
table{border-collapse:collapse;width:100%} th,td{text-align:left;padding:4px 8px;border-bottom:1px solid var(--bord);overflow-wrap:anywhere}
th{color:var(--doux);font-weight:600;font-size:12px} td.n{text-align:right;white-space:nowrap} tr.coche td{background:var(--coche)}
td button{background:none;border:0;color:var(--bleu);font:inherit;cursor:pointer;padding:0;text-align:left}
#msg{padding:8px 12px;min-height:1.5em} #msg.erreur{color:var(--rouge)}
.boite{margin:8px;padding:10px 12px;border:2px solid var(--bleu);border-radius:8px;background:var(--carte)}
.boite .ligne{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}
.boite input{flex:1;min-width:200px}
@media (max-width:640px){.corps{flex-direction:column}.arbre{width:auto;border-right:0;border-bottom:1px solid var(--bord);max-height:180px}}
"""

HTML = """
<main>
<header><h1>Navigateur FTP des cartes</h1><span class="doux petit">Le FTP de la carte est allumé à la demande et éteint à la déconnexion, à la fermeture du dernier onglet, ou après 90 s sans sondage.</span>
<label class="theme"><span>Mode sombre</span><input type="checkbox" id="theme"><span class="interrupteur"></span></label></header>
<div class="cadre">
<div class="barre">
 <label>Lieu <select id="lieu"></select></label>
 <label>Carte <select id="carte"></select></label>
 <span class="pastille" id="pastille" data-etat="eteint" role="status">● FTP éteint</span>
 <span class="bascule"><button class="btn" id="b-flash" type="button" aria-pressed="false">Flash</button><button class="btn" id="b-sd" type="button" aria-pressed="false">SD</button></span>
 <span class="doux petit" id="sd-note"></span>
 <button class="btn" id="b-histo" type="button">Historique et énergie</button>
 <button class="btn" id="b-deco" type="button" disabled>Déconnecter</button>
</div>
<div class="corps">
 <div class="arbre" id="arbre" aria-label="Dossiers"></div>
 <div class="liste"><div class="fil"><button class="btn" id="haut" type="button" title="Dossier parent" disabled>↑</button><span id="fil">/</span></div>
 <table><thead><tr><th><input type="checkbox" id="tout" aria-label="Tout cocher"></th><th>Nom</th><th class="n">Taille</th><th>Modifié</th></tr></thead><tbody id="lignes"></tbody></table></div>
</div>
<div class="boite" id="boite" hidden><div id="boite-texte"></div><div class="ligne"><input type="text" id="boite-champ" aria-label="Saisie" hidden>
 <button class="btn prim" id="boite-ok" type="button">Confirmer</button><button class="btn" id="boite-non" type="button">Annuler</button></div></div>
<div class="actions">
 <button class="btn prim" id="b-zip" type="button" disabled>Télécharger (zip)</button>
 <button class="btn" id="b-env" type="button" disabled>Envoyer…</button><input type="file" id="fichier" multiple hidden>
 <button class="btn" id="b-dos" type="button" disabled>Nouveau dossier</button>
 <button class="btn" id="b-dep" type="button" disabled>Déplacer vers…</button>
 <button class="btn" id="b-ren" type="button" disabled>Renommer</button>
 <button class="btn danger" id="b-supp" type="button" disabled>Supprimer</button>
</div>
<div id="msg" role="status"></div>
</div>
</main>
"""

JS = r"""
var MAX_ENVOI = 16 * 1024 * 1024;
var AUTRE = "Un autre onglet a changé de carte ou de support : l'affichage suit la nouvelle session.";
var S = {etat: {env: "", support: "", etat: "eteint", message: "", sd: null}, derniere: null, cartes: [], dossier: "/", entrees: [], coches: {}, noeuds: {}, occupe: 0, ecrit: false, fermeBoite: null, gen: 0};
// Identifiant de cet onglet (16 octets, hexadecimal minuscule) : le serveur n'eteint le FTP qu'avec le dernier onglet qui s'est signale.
var ONGLET = (function () { var a = new Uint8Array(16); crypto.getRandomValues(a); return Array.prototype.map.call(a, function (x) { return ("0" + x.toString(16)).slice(-2); }).join(""); })();
function $(id) { return document.getElementById(id); }
function vide(n) { while (n.firstChild) n.removeChild(n.firstChild); }
function el(tag, classe, texte) { var e = document.createElement(tag); if (classe) e.className = classe; if (texte != null) e.textContent = texte; return e; }
function pose(n, t) { if (n.textContent !== t) n.textContent = t; }          // une zone role=status n'est reecrite que si son texte change
function nomDe(chemin) { return chemin.replace(/\/+$/, "").split("/").pop() || "/"; }
function joint(d, n) { return (d === "/" ? "" : d) + "/" + n; }
function dossierParent(chemin) { var i = chemin.lastIndexOf("/"); return i <= 0 ? "/" : chemin.slice(0, i); }
function taille(n) { return n >= 1048576 ? (n / 1048576).toFixed(1) + " Mo" : n >= 1024 ? (n / 1024).toFixed(1) + " Ko" : n + " o"; }
function json(r) { try { return JSON.parse(r.texte); } catch (e) { return null; } }
// Le message d'une action survit au rafraichissement de la liste : on ne le vide qu'au debut d'une nouvelle action.
function msg(texte, erreur, action) {
  var m = $("msg"); m.className = erreur ? "erreur" : "";
  if (!action && !m.firstElementChild) { pose(m, texte || ""); return; }
  vide(m); m.appendChild(document.createTextNode(texte || ""));
  if (action) { var b = el("button", "btn", action.libelle); b.type = "button"; b.id = "msg-action"; b.onclick = action.fait; m.appendChild(document.createTextNode(" ")); m.appendChild(b); }
}
function envCourant() { return S.etat.env && S.etat.etat !== "eteint" ? S.etat.env : $("carte").value; }
function sess() { return {env: S.etat.env, support: S.etat.support}; }      // la session que la page affiche : le serveur refuse si elle a change
// Un geste d'ecriture fige session, dossier, liste et selection AVANT son premier await (boite de confirmation comprise) : apres un sondage
// qui a change S.etat, la requete part quand meme avec l'ancienne paire, donc le serveur rend un vrai 409.
function fige() { return {env: S.etat.env, support: S.etat.support, dossier: S.dossier, entrees: S.entrees, selection: selection(), gen: S.gen}; }
// Session fermee ou changee, ou geste de navigation (ouvrir, deconnecter) : la boite ouverte se ferme et le geste en cours est « mort » (`mort(cible)`).
// Il s'arrete en tete de chaque tour de sa boucle et apres chaque boite : aucun POST d'ecriture ne part plus, rien n'est ecrit a l'ecran
// (le sondage ou l'action en cours a deja mis la page et son message a jour). Un POST deja parti n'est pas rattrape.
function abandonne() { S.gen++; if (S.fermeBoite) S.fermeBoite(null); }
function mort(cible) { return cible.gen !== S.gen; }
function progres(cible, texte) { if (!mort(cible)) msg(texte); }          // le message d'avancement n'ecrase pas celui du sondage
// Fin d'un geste d'ecriture : relit le dossier puis dit le resultat, sauf si la session a change entre-temps.
async function fini(cible, erreur, ok) {
  if (mort(cible)) return;
  if (erreur === AUTRE) { msg(AUTRE, true); return; }          // 409 « session a change » : le sondage force (traite409) refait les vues, pas de relecture sous l'ancien etat
  await ouvreDossier(S.dossier);
  if (mort(cible)) return;
  if (erreur) msg(erreur, true); else msg(ok);
}
function sessDe(c) { return {env: c.env, support: c.support}; }
function perimee(r) { return r.status === 409 && r.texte === AUTRE; }

function traite409(r) {
  if (r.status === 409 && /session a change/.test(r.texte)) { r.texte = AUTRE; setTimeout(sonde, 0, true); }
  return r;
}
function etatServeur() { return api("GET", "/etat?onglet=" + ONGLET); }
function api(methode, url, corps) {
  var o = {method: methode, headers: {}};
  if (methode === "POST") {
    o.headers["X-Ftp-Cartes"] = "1";
    if (corps instanceof Blob) o.body = corps;
    else if (corps !== undefined) { o.body = JSON.stringify(corps); o.headers["Content-Type"] = "application/json"; }
    else o.body = "{}";
  }
  return fetch(url, o).then(function (r) { return r.text().then(function (t) { return {ok: r.ok, status: r.status, texte: t}; }); },
    function (e) { return {ok: false, status: 0, texte: "Serveur de l'outil injoignable : " + e.message}; }).then(traite409);
}

// ---- etat, pastille, boutons --------------------------------------------------------------------------------------
function majEtat(e) {
  S.etat = e;
  var actif = e.etat === "actif";
  if (actif) S.derniere = {env: e.env, support: e.support};
  var t = {eteint: "FTP éteint", allumage: "Allumage du FTP…", actif: "FTP actif (" + (e.support === "sd" ? "SD" : "Flash") + ")", erreur: "Erreur"}[e.etat] || e.etat;
  if (e.message) t += " : " + e.message;
  var p = $("pastille"); p.setAttribute("data-etat", e.etat); pose(p, "● " + t);
  $("b-sd").setAttribute("aria-pressed", String(actif && e.support === "sd"));
  $("b-flash").setAttribute("aria-pressed", String(actif && e.support === "flash"));
  $("b-sd").disabled = $("b-histo").disabled = e.sd === false;
  pose($("sd-note"), !e.env ? "" : e.sd === false ? "Pas de SD" : e.sd === null ? "SD inconnue" : "");
  $("b-deco").disabled = e.etat === "eteint";
  majActions();
}
function selection() { return Object.keys(S.coches).filter(function (c) { return S.coches[c]; }); }
function majActions() {
  var n = selection().length, libre = S.etat.etat === "actif" && !S.ecrit;
  $("b-zip").disabled = $("b-dep").disabled = $("b-supp").disabled = !libre || n === 0;
  $("b-ren").disabled = !libre || n !== 1;
  $("b-env").disabled = $("b-dos").disabled = !libre;
  pose($("b-zip"), n ? "Télécharger (" + n + ") en zip" : "Télécharger (zip)");
}
// Un geste d'ecriture a la fois : la barre est grisee pendant qu'il tourne (et aucune seconde boite de confirmation ne s'ouvre).
async function ecrit(f) {
  if (S.ecrit) return;
  S.ecrit = true; msg(""); majActions();
  try { await f(); } finally { S.ecrit = false; majActions(); }
}

// ---- arbre et tableau ---------------------------------------------------------------------------------------------
function navigue(chemin) { msg(""); return ouvreDossier(chemin); }
function noeud(chemin, nom, hote) {
  var n = el("div", "noeud"), b = el("button", null, nom);
  b.type = "button"; b.setAttribute("data-chemin", chemin);
  b.onclick = function () { navigue(chemin); };
  var enf = el("div", "enfants"); n.appendChild(b); n.appendChild(enf); hote.appendChild(n);
  S.noeuds[chemin] = {b: b, enf: enf};
}
function initArbre() { vide($("arbre")); S.noeuds = {}; noeud("/", "/", $("arbre")); }
function effaceVues() {
  S.dossier = "/"; S.entrees = []; S.coches = {}; initArbre(); vide($("lignes")); pose($("fil"), "/"); $("haut").disabled = true; $("tout").checked = false; majActions();
}
function rendArbre(chemin, entrees) {
  var n = S.noeuds[chemin];
  Object.keys(S.noeuds).forEach(function (c) { S.noeuds[c].b.classList.toggle("courant", c === chemin); });
  if (!n) return;
  vide(n.enf);
  entrees.filter(function (e) { return e.type === "dossier"; }).forEach(function (e) { noeud(joint(chemin, e.nom), e.nom, n.enf); });
}
function rendTableau() {
  var corps = $("lignes"); vide(corps);
  pose($("fil"), S.dossier); $("haut").disabled = S.dossier === "/"; $("tout").checked = false;
  S.entrees.slice().sort(function (a, b) { return a.type === b.type ? a.nom.localeCompare(b.nom) : a.type === "dossier" ? -1 : 1; }).forEach(function (e) {
    var chemin = joint(S.dossier, e.nom), tr = el("tr"), c = el("td"), ck = el("input");
    tr.setAttribute("data-nom", e.nom);
    ck.type = "checkbox"; ck.setAttribute("aria-label", "Cocher " + e.nom);
    ck.onchange = function () { S.coches[chemin] = ck.checked; tr.className = ck.checked ? "coche" : ""; majActions(); };
    c.appendChild(ck); tr.appendChild(c);
    var nom = el("td");
    if (e.type === "dossier") { var b = el("button", null, "📁 " + e.nom); b.type = "button"; b.onclick = function () { navigue(chemin); }; nom.appendChild(b); }
    else nom.textContent = e.nom;
    tr.appendChild(nom); tr.appendChild(el("td", "n", e.type === "dossier" ? "" : taille(e.taille))); tr.appendChild(el("td", null, e.date || ""));
    corps.appendChild(tr);
  });
  majActions();
}
function ouvreDossier(chemin) {
  S.occupe++;
  return api("GET", "/liste?chemin=" + encodeURIComponent(chemin)).then(function (r) {
    S.occupe--;                                                      // avant tout le reste : le sondage ne s'arrete jamais
    try {
      var d = r.ok ? json(r) : null;
      if (!d || !Array.isArray(d.entrees)) { msg(r.ok ? "Réponse illisible du serveur." : r.texte, true); return sonde(true); }
      S.dossier = d.chemin; S.entrees = d.entrees; S.coches = {};
      rendArbre(chemin, d.entrees); rendTableau();                   // le message de la derniere action reste affiche
    } catch (e) { msg("Affichage impossible : " + e.message, true); }
  });
}

// ---- session ------------------------------------------------------------------------------------------------------
function ouvrir(env, support, repli) {
  abandonne(); msg(""); S.occupe++;
  majEtat({env: env, support: support, etat: "allumage", message: "", sd: null});
  return api("POST", "/ouvre", {env: env, support: support, onglet: ONGLET}).then(function (r) {
    S.occupe--;
    if (r.ok) {
      var e = json(r);
      if (!e || typeof e.etat !== "string") { effaceVues(); msg("Réponse illisible du serveur à l'allumage.", true); return sonde(true); }
      majEtat(e); effaceVues(); return ouvreDossier("/");
    }
    return etatServeur().then(function (x) {
      var e = json(x);
      if (e) majEtat(e);
      if (e && support === "sd" && !repli && e.sd === false) return ouvrir(env, "flash", true);
      msg(r.texte, true); effaceVues();
    });
  });
}
function deconnecter() {
  abandonne(); S.occupe++;
  return api("POST", "/ferme").then(etatServeur).then(function (x) {                // sans `onglet` : ferme toujours, meme si un autre onglet est ouvert
    S.occupe--; var e = json(x); if (e) majEtat(e); effaceVues(); $("carte").value = ""; msg("");
  });
}
function rallumer() {
  var d = S.derniere; if (!d) return;
  choisitCarte(d.env); ouvrir(d.env, d.support, true);
}
function sonde(force) {
  if (S.occupe && !force) { fetch("/etat?onglet=" + ONGLET).catch(function () {}); return; }      // un geste long (zip) suspend le sondage : l'onglet se signale quand meme
  var gen = S.gen;
  etatServeur().then(function (x) {
    var e = json(x); if (!e || S.occupe || S.gen !== gen) return;    // reponse perimee : un ouvrir, un deconnecter ou un changement de session a eu lieu depuis la requete
    var avant = S.etat;
    if (e.env !== avant.env || e.support !== avant.support || e.etat !== "actif") abandonne();   // session changee : confirmation perimee, geste en cours abandonne
    majEtat(e);
    if (avant.etat === "actif" && e.etat !== "actif") {
      effaceVues();
      msg("La session FTP est fermée (inactivité, autre onglet ou carte redémarrée).", true, {libelle: "Rallumer", fait: rallumer});
    } else if (e.etat === "actif" && (avant.etat !== "actif" || e.env !== avant.env || e.support !== avant.support)) {
      effaceVues(); choisitCarte(e.env);
      if (avant.etat === "actif") msg(AUTRE, true);
      ouvreDossier("/");
    }
  });
}

// ---- listes Lieu et Carte ------------------------------------------------------------------------------------------
function remplitCartes(choisi) {
  var lieu = $("lieu").value, sel = $("carte");
  remplitParLieu(sel, S.cartes.filter(function (c) { return !lieu || c.lieu === lieu; }).map(function (c) { return {nom: c.env, lieu: c.lieu}; }), LIEUX, choisi, []);
  var o = el("option", null, "Choisir une carte…"); o.value = ""; sel.insertBefore(o, sel.firstChild);
  sel.value = choisi && Array.prototype.some.call(sel.options, function (x) { return x.value === choisi; }) ? choisi : "";
}
function choisitCarte(env) { $("lieu").value = ""; remplitCartes(env); }
function remplitLieux() {
  var s = $("lieu"), vus = {}; S.cartes.forEach(function (c) { vus[c.lieu] = true; });
  var o = el("option", null, "Tous les lieux"); o.value = ""; s.appendChild(o);
  LIEUX.concat(Object.keys(vus).filter(function (c) { return !LIEUX.some(function (l) { return l[0] === c; }); }).map(function (c) { return [c, c]; }))
    .filter(function (l) { return vus[l[0]]; }).forEach(function (l) { var x = el("option", null, l[1]); x.value = l[0]; s.appendChild(x); });
  var demande = lieuDemande(LIEUX); if (demande && vus[demande]) s.value = demande;
}

// ---- actions ------------------------------------------------------------------------------------------------------
function demande(texte, champ, ok) {
  return new Promise(function (resolve) {
    var c = $("boite-champ"), b = $("boite");
    pose($("boite-texte"), texte); c.hidden = champ == null; c.value = champ == null ? "" : champ;
    $("boite-ok").textContent = ok || "Confirmer"; b.hidden = false; (champ == null ? $("boite-ok") : c).focus();
    function fin(v) { b.hidden = true; S.fermeBoite = null; $("boite-ok").onclick = $("boite-non").onclick = c.onkeydown = null; resolve(v); }
    S.fermeBoite = fin;
    $("boite-ok").onclick = function () { fin(champ == null ? true : c.value.trim() || null); };
    $("boite-non").onclick = function () { fin(null); };
    c.onkeydown = function (ev) { if (ev.key === "Enter") $("boite-ok").onclick(); else if (ev.key === "Escape") fin(null); };
  });
}
function telecharge(url, nom) { var a = el("a"); a.href = url; a.download = nom; document.body.appendChild(a); a.click(); document.body.removeChild(a); }
function estDossier(chemin, cible) { cible = cible || fige(); return cible.entrees.some(function (e) { return e.type === "dossier" && joint(cible.dossier, e.nom) === chemin; }); }
function decrit(liste, cible) {                                             // ce qui part : dossiers avec leur contenu, au plus 5 noms
  var noms = liste.slice(0, 5).map(function (c) { return estDossier(c, cible) ? "le dossier « " + nomDe(c) + " » et tout son contenu" : "« " + nomDe(c) + " »"; });
  return noms.join(", ") + (liste.length > 5 ? " et " + (liste.length - 5) + " autres" : "");
}
async function zip() {
  var cible = fige(), liste = cible.selection; if (!liste.length) return;
  var une = liste.length === 1 && cible.entrees.some(function (e) { return e.type === "fichier" && joint(cible.dossier, e.nom) === liste[0]; });
  if (une) { telecharge("/telecharge?chemin=" + encodeURIComponent(liste[0]) + "&env=" + encodeURIComponent(cible.env) + "&support=" + encodeURIComponent(cible.support), nomDe(liste[0])); return; }
  S.occupe++;
  try {
    var r = await fetch("/zip", {method: "POST", headers: {"X-Ftp-Cartes": "1", "Content-Type": "application/json"}, body: JSON.stringify(Object.assign({chemins: liste}, sessDe(cible)))});
    if (!r.ok) { msg(traite409({status: r.status, texte: await r.text()}).texte, true); return; }
    var u = URL.createObjectURL(await r.blob());
    telecharge(u, "carte.zip"); setTimeout(function () { URL.revokeObjectURL(u); }, 60000);
  } catch (e) { msg("Zip impossible : " + e.message, true); } finally { S.occupe--; }
}
function envoie(fichiers) {
  return ecrit(async function () {
    var cible = fige(), n = fichiers.length, faits = 0, erreur = "";
    for (var i = 0; i < n; i++) {
      if (mort(cible)) return;
      var f = fichiers[i];
      if (f.size > MAX_ENVOI) { erreur = "« " + f.name + " » dépasse 16 Mo : refusé avant tout envoi."; continue; }
      var url = "/envoie?dossier=" + encodeURIComponent(cible.dossier) + "&nom=" + encodeURIComponent(f.name) + "&env=" + encodeURIComponent(cible.env) + "&support=" + cible.support + "&ecraser=";
      var question = "« " + f.name + " » existe déjà dans " + cible.dossier + " : l'écraser ?";
      // Deja dans la liste affichee : on demande AVANT d'envoyer le corps (un fichier de 16 Mo ne part qu'une fois). Absent de la liste (perimee) : repli sur le 409 de la carte.
      var ecraser = cible.entrees.some(function (e) { return e.type === "fichier" && e.nom === f.name; });
      if (ecraser && !await demande(question, null, "Écraser")) { if (mort(cible)) return; continue; }
      progres(cible, "Envoi de « " + f.name + " » (" + (i + 1) + "/" + n + ")…");
      var r = await api("POST", url + (ecraser ? "1" : "0"), f);
      if (!ecraser && r.status === 409 && /existe deja/.test(r.texte)) {
        if (!await demande(question, null, "Écraser")) { if (mort(cible)) return; continue; }
        r = await api("POST", url + "1", f);
      }
      if (r.ok) faits++; else erreur = r.texte;
      if (perimee(r)) break;                                          // session changee : on n'insiste pas fichier apres fichier
    }
    await fini(cible, erreur, faits ? "Envoyé : " + faits + " fichier(s)." : "Aucun fichier envoyé.");
  });
}
// Suppression ou deplacement d'un element : sur le refus « seconde confirmation » du serveur (fichier protege, ou dossier qui en contient un : la page ne devine
// rien, elle suit le 409), on redemande puis on renvoie avec confirmations: 2. Rend {r} (reponse finale) ou {r, annule} si l'utilisateur renonce.
async function geste(route, corps, cible, verbe, vers) {
  var nom = nomDe(corps.chemin || corps.source), r = await api("POST", route, Object.assign({}, corps, {confirmations: 1}, sessDe(cible)));
  if (r.status !== 409 || !/seconde confirmation/.test(r.texte)) return {r: r};
  if (!await demande("« " + nom + " » est protégé : fichier de configuration de la carte (démarrage ou réglages), ou dossier qui en contient un. Seconde confirmation : le " + verbe + " vraiment" + vers + " ?",
    null, verbe.charAt(0).toUpperCase() + verbe.slice(1) + " quand même") || mort(cible)) return {r: r, annule: true};
  return {r: await api("POST", route, Object.assign({}, corps, {confirmations: 2}, sessDe(cible)))};
}
function supprime() {
  return ecrit(async function () {
    var cible = fige(), liste = cible.selection; if (!liste.length) return;
    if (!await demande("Supprimer de la carte : " + decrit(liste, cible) + " ? Action irréversible.", null, "Supprimer")) return;
    var erreur = "", annule = "";
    for (var i = 0; i < liste.length; i++) {
      if (mort(cible)) return;
      progres(cible, "Suppression (" + (i + 1) + "/" + liste.length + ")…");
      var g = await geste("/supprime", {chemin: liste[i]}, cible, "supprimer", "");
      if (g.annule) { if (mort(cible)) return; annule = "Suppression annulée : " + nomDe(liste[i]); }
      else if (!g.r.ok) erreur = g.r.texte;
      if (perimee(g.r)) break;                                        // session changee : plus rien n'est envoye
    }
    await fini(cible, erreur, annule || "Supprimé.");
  });
}
function deplace(renomme) {
  return ecrit(async function () {
    var cible = fige(), liste = cible.selection; if (!liste.length) return;
    var saisie = await demande(renomme ? "Nouveau nom de « " + nomDe(liste[0]) + " » :" : "Déplacer " + decrit(liste, cible) + " vers le dossier :", renomme ? nomDe(liste[0]) : cible.dossier, renomme ? "Renommer" : "Déplacer");
    if (!saisie) return;
    if (renomme ? /[\/\\]/.test(saisie) : saisie.charAt(0) !== "/") { msg(renomme ? "Un nom ne contient ni / ni \\." : "Le dossier cible commence par /.", true); return; }
    var cibles = liste.map(function (c) { return renomme ? joint(dossierParent(c), saisie) : joint(saisie, nomDe(c)); });
    var pris = cibles.filter(function (t) { return dossierParent(t) === cible.dossier && cible.entrees.some(function (e) { return e.nom === nomDe(t); }); });
    if (pris.length) { msg("« " + nomDe(pris[0]) + " » existe déjà dans " + cible.dossier + " : rien n'est déplacé (pas d'écrasement).", true); return; }
    var erreur = "", annule = "";
    for (var i = 0; i < liste.length; i++) {
      if (mort(cible)) return;
      progres(cible, (renomme ? "Renommage" : "Déplacement") + " (" + (i + 1) + "/" + liste.length + ")…");
      var g = await geste("/deplace", {source: liste[i], cible: cibles[i]}, cible, renomme ? "renommer" : "déplacer", renomme ? " en « " + saisie + " »" : " vers " + saisie);
      if (g.annule) { if (mort(cible)) return; annule = (renomme ? "Renommage" : "Déplacement") + " annulé : " + nomDe(liste[i]); break; }
      if (!g.r.ok) { erreur = g.r.texte; break; }                     // y compris session changee ou cible existante : on s'arrete au premier refus
    }
    await fini(cible, erreur, annule || (renomme ? "Renommé." : "Déplacé."));
  });
}
function nouveauDossier() {
  return ecrit(async function () {
    var cible = fige();
    var nom = await demande("Nom du nouveau dossier dans " + cible.dossier + " :", "", "Créer");
    if (!nom) return;
    if (/[\/\\]/.test(nom)) { msg("Un nom ne contient ni / ni \\.", true); return; }
    var r = await api("POST", "/dossier", Object.assign({chemin: joint(cible.dossier, nom)}, sessDe(cible)));
    await fini(cible, r.ok ? "" : r.texte, "Dossier créé.");
  });
}
function bascule(support) {
  var env = envCourant(); if (!env) { msg("Choisissez d'abord une carte.", true); return; }
  ouvrir(env, support, true);
}

$("carte").onchange = function () { if (this.value) ouvrir(this.value, "sd"); else deconnecter(); };
$("lieu").onchange = function () { remplitCartes(S.etat.env); };
$("b-flash").onclick = function () { bascule("flash"); };
$("b-sd").onclick = function () { bascule("sd"); };
$("b-histo").onclick = function () {
  var env = envCourant(); if (!env) { msg("Choisissez d'abord une carte.", true); return; }
  msg("");
  var pret = S.etat.etat === "actif" && S.etat.support === "sd" ? Promise.resolve() : ouvrir(env, "sd", true);
  pret.then(function () { if (S.etat.etat === "actif") return ouvreDossier("/histo"); });
};
$("b-deco").onclick = deconnecter;
$("haut").onclick = function () { navigue(dossierParent(S.dossier)); };
$("tout").onchange = function () {
  var v = this.checked; Array.prototype.forEach.call($("lignes").querySelectorAll("input"), function (c) { if (c.checked !== v) c.click(); });
};
$("b-zip").onclick = zip;
$("b-env").onclick = function () { $("fichier").click(); };
$("fichier").onchange = function () { var l = Array.prototype.slice.call(this.files); this.value = ""; envoie(l); };   // champ vide des le depart : re-choisir le meme fichier redeclenche change
$("b-dos").onclick = nouveauDossier;
$("b-dep").onclick = function () { deplace(false); };
$("b-ren").onclick = function () { deplace(true); };
$("b-supp").onclick = supprime;
// Fermeture de CETTE page : le serveur n'eteint le FTP que si c'etait le dernier onglet (la reponse n'est pas lue : un autre onglet peut le garder allume).
window.addEventListener("pagehide", function () { try { navigator.sendBeacon("/ferme", new Blob([JSON.stringify({onglet: ONGLET})], {type: "text/plain"})); } catch (e) {} });

initArbre();
api("GET", "/cartes").then(function (r) {
  var d = json(r);
  if (!d) { msg("Liste des cartes indisponible : " + r.texte, true); return null; }
  S.cartes = d.cartes; remplitLieux(); remplitCartes("");
  if (!d.cartes.length) msg("Aucune carte joignable par FTP (voir « exclues » de /cartes).", true);
  return etatServeur();
}).then(function (r) {
  var e = r && json(r); if (!e) return;
  majEtat(e);
  if (e.etat === "actif") { choisitCarte(e.env); ouvreDossier("/"); }
});
setInterval(function () { sonde(); }, 5000);                        // `sonde` relue a chaque tour : la sonde Chrome peut la neutraliser
"""

THEME_TETE = ("<script>(function () { var t = null; try { t = localStorage.getItem('ftp-theme'); } catch (e) {}"
              " if (t !== 'clair' && t !== 'sombre') t = (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches)"
              " ? 'sombre' : 'clair'; document.documentElement.setAttribute('data-theme', t); })();</script>")
THEME_INTERRUPTEUR = ("<script>(function () { var c = document.getElementById('theme');"
                      " c.checked = document.documentElement.getAttribute('data-theme') === 'sombre';"
                      " c.onchange = function () { var t = this.checked ? 'sombre' : 'clair';"
                      " document.documentElement.setAttribute('data-theme', t);"
                      " try { localStorage.setItem('ftp-theme', t); } catch (e) {} }; })();</script>")

PAGE = ("<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>Navigateur FTP des cartes</title><link rel=\"icon\" href=\"data:,\">" + THEME_TETE + "<style>" + CSS + "</style></head><body>"
        + HTML + THEME_INTERRUPTEUR + "<script>var LIEUX = " + json.dumps(lieux.pour_page()["lieux"]) + ";" + lieux.JS + JS + "</script></body></html>")
