"""Page de la Fabrique d'extensions (tapp_web.py) : guide en quatre etapes, de la creation d'un dossier a l'envoi d'un .tapp a une carte.

Tout ce qui vient du serveur s'affiche par textContent (noms, manifeste, messages de compilation) ; la page n'edite pas le code Berry.
Deux compteurs de generation : S.nSel (extension affichee) et S.nPrep (preparation de l'envoi) : une reponse depassee est ignoree, une
preparation perimee (autre voie, autre carte, nouvelle fabrication, autre extension) ne peut pas partir.
Sonde : test_tapp_page_chrome.py.
"""
import lieux

CSS = """
:root{color-scheme:light;--fond:#f6f7f9;--carte:#fff;--bord:#ddd;--texte:#222;--doux:#666;--bleu:#2563eb;--vert:#1e7e3a;
  --orange:#a86400;--rouge:#c0392b;--btn:#fff;--btn-bord:#888;--piste:#e9e9ea;--orange-fond:#fff4e0;--vert-fond:#e3f4e8;
  --rouge-fond:#fdecea;--bleu-fond:#eef3ff;--champ:#fff}
:root[data-theme="sombre"]{color-scheme:dark;--fond:#121417;--carte:#1d2025;--bord:#3a3f47;--texte:#e6e6e6;--doux:#a8adb5;
  --bleu:#5b93ff;--vert:#3fbf63;--orange:#f0a020;--rouge:#ff6b5b;--btn:#262a30;--btn-bord:#555b64;--piste:#39393d;
  --orange-fond:#33270f;--vert-fond:#16301f;--rouge-fond:#3a1d1a;--bleu-fond:#18233a;--champ:#15171b}
*{box-sizing:border-box}
body{margin:0;font:14px system-ui,sans-serif;color:var(--texte);background:var(--fond)}
main{max-width:1100px;margin:0 auto;padding:12px 16px 24px}
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
.colonnes{display:grid;grid-template-columns:280px minmax(0,1fr);gap:12px;align-items:start}
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:12px;margin-bottom:12px;min-width:0}
.btn{display:inline-block;padding:6px 12px;border:1px solid var(--btn-bord);border-radius:6px;background:var(--btn);font:inherit;color:inherit;cursor:pointer}
.btn.prim{background:#2563eb;border-color:#2563eb;color:#fff} .btn:disabled{opacity:.45;cursor:default}
.ligne{display:flex;gap:8px;align-items:center;margin:6px 0;flex-wrap:wrap}
label.ch{display:flex;gap:6px;align-items:flex-start;margin:6px 0}
label.ch input{margin-top:3px;flex:none}
.champ{display:block;margin:6px 0} .champ span{display:block;font-size:12px;color:var(--doux);margin-bottom:2px}
input[type=text],select{font:inherit;padding:5px 7px;border:1px solid var(--bord);border-radius:5px;background:var(--champ);color:var(--texte);width:100%;min-width:0}
ul.exts{list-style:none;margin:0 0 8px;padding:0}
ul.exts button{display:block;width:100%;text-align:left;padding:6px 8px;border:1px solid transparent;border-radius:6px;background:none;font:inherit;color:inherit;cursor:pointer;overflow-wrap:anywhere}
ul.exts button:hover{background:var(--bleu-fond)} ul.exts button.choisie{border-color:var(--bleu);background:var(--bleu-fond)}
ul.fichiers{margin:4px 0;padding-left:18px;overflow-wrap:anywhere}
.chemin{font-family:Consolas,monospace;font-size:12px;overflow-wrap:anywhere}
.msg{padding:6px 8px;font-size:13px;border-radius:4px;margin:8px 0 0;border-left:3px solid var(--orange);background:var(--orange-fond);white-space:pre-wrap;overflow-wrap:anywhere}
.msg.rouge{background:var(--rouge-fond);border-left-color:var(--rouge)} .msg.ok{background:var(--vert-fond);border-left-color:var(--vert)}
.points{list-style:none;margin:6px 0;padding:0} .points li{padding:2px 0;white-space:pre-wrap;overflow-wrap:anywhere}
.points .bon::before{content:"\\2713  ";color:var(--vert);font-weight:700} .points .non::before{content:"\\2717  ";color:var(--rouge);font-weight:700}
@media (max-width:760px){.colonnes{grid-template-columns:minmax(0,1fr)}}
"""

HTML = """<main>
<header><h1>Fabrique d'extensions</h1><span class="doux">un .tapp, du dossier source à la carte</span>
<label class="theme" for="theme"><span>Mode sombre</span><input id="theme" type="checkbox" role="switch"><span class="interrupteur" aria-hidden="true"></span></label></header>
<div class="colonnes">
<div>
  <section class="carte"><h2>Mes extensions</h2>
    <ul class="exts" id="liste"></ul>
    <p class="doux petit" id="vide" hidden>Aucune extension pour l'instant. Une extension est un petit dossier de code Berry que la carte charge d'elle-même au démarrage. Commence par en créer une ci-dessous.</p>
    <p class="doux petit" id="ignores" hidden></p>
  </section>
  <section class="carte"><h2>1. Créer depuis un modèle</h2>
    <label class="champ"><span>Nom du dossier (31 caractères au plus : lettres sans accent, chiffres, - et _)</span><input type="text" id="c-nom" maxlength="31" autocomplete="off"></label>
    <div id="c-gabarits"></div>
    <button class="btn prim" id="c-go" type="button">Créer le dossier</button>
    <div id="c-retour"></div>
  </section>
  <section class="carte petit doux"><h2>À savoir</h2>
    <p>Une extension se lance <b>avant</b> <span class="chemin">/autoexec.be</span> : <span class="chemin">logFonctions</span> et <span class="chemin">LOG_LEVEL_*</span> n'existent pas encore pendant sa compilation ni son chargement : écrire <span class="chemin">global.LOG_LEVEL_INFO</span>, sinon elle ne se lance pas (d'où la minuterie du premier modèle).</p>
    <p>Un <span class="chemin">.tapp</span> envoyé à une carte n'est pas dans son image : il disparaît au prochain formatage du FS ou flash série.</p>
    <p>Tout est expliqué dans <span class="chemin">outils_docs/EXTENSIONS_TAPP.md</span>.</p>
  </section>
</div>
<div id="fiche" hidden>
  <section class="carte"><h2>2. Écrire le code et le manifeste : <span id="f-nom"></span></h2>
    <p class="petit">Le code s'écrit dans VS Code, dans le dossier <span class="chemin" id="f-chemin"></span>. Ici, seul le manifeste se modifie.</p>
    <ul class="fichiers petit" id="f-fichiers"></ul>
    <div id="m-erreur"></div>
    <label class="champ"><span>Nom affiché dans /ext (obligatoire)</span><input type="text" id="m-name" autocomplete="off"></label>
    <label class="champ"><span>Version (entier ou 0x…)</span><input type="text" id="m-version" autocomplete="off"></label>
    <label class="champ"><span>Description</span><input type="text" id="m-description" autocomplete="off"></label>
    <label class="champ"><span>Version minimale de Tasmota (entier ou 0x… ; le firmware ne la compare pas)</span><input type="text" id="m-min" autocomplete="off"></label>
    <button class="btn" id="m-go" type="button">Enregistrer le manifeste</button>
    <div id="m-retour"></div>
  </section>
  <section class="carte"><h2>3. Vérifier et fabriquer</h2>
    <ul class="points" id="v-points"></ul>
    <div id="v-retour"></div>
    <p id="t-etat"></p>
    <div class="ligne"><button class="btn" id="v-go" type="button">Vérifier</button><button class="btn prim" id="t-go" type="button">Fabriquer le .tapp</button></div>
    <div id="t-retour"></div>
  </section>
  <section class="carte"><h2>4. Envoyer à une carte</h2>
    <label class="champ"><span>Carte</span><select id="e-carte"></select></label>
    <div class="ligne"><label><input type="radio" name="e-voie" id="e-http" checked> Wi-Fi (HTTP)</label><label><input type="radio" name="e-voie" id="e-mqtt"> MQTT</label><button class="btn" id="e-lire" type="button">Lire la carte</button></div>
    <p class="doux petit">MQTT : pour les esclaves derrière le point d'accès de leur maître ; la carte doit avoir chargé fsMqtt.</p>
    <p id="e-etat"></p>
    <div id="e-panneau" hidden>
      <label class="ch"><input type="checkbox" id="e-vu"><span id="e-vu-texte"></span></label>
      <label class="ch"><input type="checkbox" id="e-redemarrer"><span>Redémarrer ensuite. Sinon, l'extension se lance au démarrage suivant, ou par la page /ext de la carte.</span></label>
      <button class="btn prim" id="e-go" type="button" disabled>Envoyer</button>
    </div>
    <div id="e-retour"></div>
  </section>
</div>
</div>
</main>"""

JS = r"""
var S = {nom: null, nSel: 0, nPrep: 0, prep: null};
function $(i) { return document.getElementById(i); }
function vide(n) { while (n.firstChild) n.removeChild(n.firstChild); return n; }
function el(balise, classe, texte) { var e = document.createElement(balise); if (classe) e.className = classe; if (texte !== undefined) e.textContent = texte; return e; }
function message(zone, classe, texte) { vide(zone).appendChild(el("p", "msg " + classe, texte)); }
async function api(chemin, corps) {
  var options = corps ? {method: "POST", headers: {"Content-Type": "application/json", "X-Fabrique-Tapp": "1"}, body: JSON.stringify(corps)} : {};
  try {
    var r = await fetch(chemin, options), t = await r.text();
    if (!r.ok) return {ok: false, texte: t};
    return {ok: true, donnees: JSON.parse(t)};
  } catch (e) { return {ok: false, texte: "Outil injoignable : est-il encore lancé ? (" + e + ")"}; }
}

// ---- Liste et creation ----
async function chargeListe() {
  var r = await api("/extensions");
  if (!r.ok) { message($("c-retour"), "rouge", r.texte); return; }
  var z = vide($("liste"));
  r.donnees.extensions.forEach(function (x) {
    var li = el("li"), b = el("button", x.nom === S.nom ? "choisie" : "", x.nom);
    b.type = "button"; b.title = x.tapp.existe ? (x.tapp.a_jour ? ".tapp à jour" : ".tapp périmé") : "pas encore fabriquée";
    b.onclick = function () { choisit(x.nom); };
    li.appendChild(b); z.appendChild(li);
  });
  $("vide").hidden = r.donnees.extensions.length > 0;
  $("ignores").hidden = !r.donnees.ignores.length;
  $("ignores").textContent = "Dossiers ignorés (nom refusé) : " + r.donnees.ignores.join(", ");
  if (!$("c-gabarits").firstChild) r.donnees.gabarits.forEach(function (g, i) {
    var l = el("label", "ch"), e = el("input"), t = el("span");
    e.type = "radio"; e.name = "c-gabarit"; e.value = g.id; e.checked = !i; e.id = "c-g-" + g.id;
    t.appendChild(el("b", "", g.libelle)); t.appendChild(el("br")); t.appendChild(el("span", "doux petit", g.explication));
    l.appendChild(e); l.appendChild(t); $("c-gabarits").appendChild(l);
  });
}
async function cree() {
  var nom = $("c-nom").value.trim(), g = document.querySelector('input[name="c-gabarit"]:checked');
  var r = await api("/creer", {nom: nom, gabarit: g ? g.value : ""});
  if (!r.ok) { message($("c-retour"), "rouge", r.texte); return; }
  vide($("c-retour")); $("c-nom").value = "";
  await choisit(nom);
}

// ---- Fiche d'une extension ----
function rendFichiers(d) {
  $("f-nom").textContent = d.nom; $("f-chemin").textContent = d.chemin;
  var z = vide($("f-fichiers"));
  d.fichiers.forEach(function (f) { z.appendChild(el("li", "", f.nom + (f.dossier ? " (sous-dossier : interdit, à déplacer)" : " : " + f.taille + " octets"))); });
  if (!d.fichiers.length) z.appendChild(el("li", "doux", "Dossier vide."));
  if (d.manifeste_erreur) message($("m-erreur"), "", d.manifeste_erreur); else vide($("m-erreur"));
  var t = d.tapp, e = $("t-etat");
  e.textContent = !t.existe ? "Pas encore fabriqué." : t.a_jour ? "À jour : " + t.chemin + " (" + t.taille + " octets)." : "Plus ancien que ses sources : le fabriquer à nouveau avant de l'envoyer.";
}
function rendManifeste(m) { $("m-name").value = m.name; $("m-version").value = m.version; $("m-description").value = m.description; $("m-min").value = m.min_tasmota; }
async function choisit(nom) {
  var g = ++S.nSel;
  S.nom = nom; annulePrep();
  $("e-carte").value = "";
  vide($("m-retour")); vide($("t-retour")); vide($("v-retour")); vide($("e-retour")); vide($("v-points"));
  var r = await api("/extension?nom=" + encodeURIComponent(nom));
  if (g !== S.nSel) return;
  if (!r.ok) { message($("c-retour"), "rouge", r.texte); return; }
  $("fiche").hidden = false;
  rendFichiers(r.donnees); rendManifeste(r.donnees.manifeste);
  chargeListe();
  verifie();
}
async function verifie() {
  var g = S.nSel, nom = S.nom, z = vide($("v-points"));
  z.appendChild(el("li", "doux", "Vérification…"));
  $("v-go").disabled = true;
  var d = await api("/extension?nom=" + encodeURIComponent(nom)), r = await api("/verifie", {nom: nom});
  if (g !== S.nSel) return;
  $("v-go").disabled = false;
  if (d.ok) rendFichiers(d.donnees);
  vide(z); vide($("v-retour"));
  if (!r.ok) { message($("v-retour"), "rouge", r.texte); return; }
  r.donnees.points.forEach(function (p) { z.appendChild(el("li", p.motif ? "non" : "bon", p.point + (p.motif ? " : " + p.motif : ""))); });
  if (r.donnees.avertissements.length) message($("v-retour"), "", "Écarts à la charte des logs (non bloquants) :\n" + r.donnees.avertissements.join("\n"));
}
async function enregistre() {
  var g = S.nSel, r = await api("/manifeste", {nom: S.nom, name: $("m-name").value, version: $("m-version").value, description: $("m-description").value, min_tasmota: $("m-min").value});
  if (g !== S.nSel) return;
  if (!r.ok) { message($("m-retour"), "rouge", r.texte); return; }
  message($("m-retour"), "ok", "Manifeste enregistré. Il reste à fabriquer à nouveau le .tapp.");
  rendFichiers(r.donnees); rendManifeste(r.donnees.manifeste);
  annulePrep(); chargeListe(); verifie();
}
async function fabrique() {
  var g = S.nSel;
  $("t-go").disabled = true;
  var r = await api("/fabrique", {nom: S.nom});
  $("t-go").disabled = false;
  if (g !== S.nSel) return;
  if (!r.ok) { message($("t-retour"), "rouge", r.texte + "\nCorrige puis clique à nouveau : l'ancien .tapp, s'il existe, reste en place."); return; }
  message($("t-retour"), "ok", "Fabriqué : " + r.donnees.tapp.chemin + " (" + r.donnees.tapp.taille + " octets). Étape suivante : choisir une carte.");
  chargeListe(); verifie();
  // MQTT : lire la carte ouvre un echange avec fsMqtt, qui annulerait un transfert en cours : jamais sans geste
  if (voie() === "http") prepare();
  else { annulePrep(); if ($("e-carte").value) $("e-etat").textContent = "Archive refaite : clique sur « Lire la carte » pour préparer l'envoi par MQTT."; }
}

// ---- Envoi ----
function voie() { return $("e-mqtt").checked ? "mqtt" : "http"; }
function majEnvoyer() { $("e-go").disabled = !(S.prep && $("e-vu").checked); }
function annulePrep() {
  S.nPrep++; S.prep = null;
  $("e-panneau").hidden = true; $("e-vu").checked = false; $("e-redemarrer").checked = false; $("e-etat").textContent = "";
  majEnvoyer();
}
var SUR_CARTE = {absent: "Aucun fichier de ce nom sur la carte.", identique: "La carte a déjà ce fichier, identique.",
  different: "Un fichier de ce nom est sur la carte, différent : il sera remplacé.", inconnu: "Présence d'un fichier de ce nom non lue : s'il existe, il sera remplacé."};
async function prepare() {
  annulePrep();
  vide($("e-retour"));
  var g = S.nPrep, env = $("e-carte").value, nom = S.nom, transport = voie();
  if (!env || !nom) return;
  $("e-etat").textContent = "Lecture de la carte…";
  var r = await api("/envoi/prepare", {nom: nom, env: env, transport: transport});
  if (g !== S.nPrep) return;                       // preparation depassee : autre voie, carte, extension ou fabrication
  $("e-etat").textContent = "";
  if (!r.ok) { message($("e-retour"), "rouge", r.texte); return; }
  S.prep = {env: env, nom: nom, jeton: r.donnees.jeton, transport: r.donnees.transport, hote: r.donnees.hostname_carte, chemin: r.donnees.chemin};
  $("e-etat").textContent = "Carte " + r.donnees.hostname_carte + (transport === "mqtt" ? " par MQTT (" + r.donnees.adresse.slice(5) + ")" : " à l'adresse " + r.donnees.adresse)
    + " (identité vérifiée). Destination : " + r.donnees.chemin + ", " + r.donnees.taille + " octets. " + SUR_CARTE[r.donnees.sur_carte];
  $("e-vu-texte").textContent = "Envoyer ce fichier à " + r.donnees.hostname_carte;
  $("e-panneau").hidden = false;
  majEnvoyer();
}
async function envoie() {
  var p = S.prep, redemarre = $("e-redemarrer").checked;
  if (!p || !$("e-vu").checked) return;
  $("e-go").disabled = true;
  var z = vide($("e-retour"));
  z.appendChild(el("p", "doux", "Envoi en cours…"));
  var r = await api("/envoi", {nom: p.nom, env: p.env, jeton: p.jeton, transport: p.transport, confirme: true, redemarrer: redemarre});
  if (!r.ok) { message(z, "rouge", r.texte + "\nClique sur « Lire la carte » pour préparer à nouveau l'envoi."); if (S.prep === p) annulePrep(); return; }
  message(z, "ok", "Envoyé à " + p.hote + " : " + r.donnees.chemin + ". " + (redemarre ? "La carte a redémarré." : "L'extension se lancera au démarrage suivant, ou par la page /ext de la carte."));
  if (r.donnees.avertissement) z.appendChild(el("p", "msg", r.donnees.avertissement));
  if (S.prep === p) annulePrep();
}
var lieuVu = false;
async function chargeCartes() {
  var r = await api("/cartes"), avant = $("e-carte").value, s = vide($("e-carte")), o = el("option", "", "(choisir une carte)");
  o.value = ""; s.appendChild(o);
  if (!r.ok) { message($("e-retour"), "rouge", r.texte); return; }
  remplitParLieu(s, r.donnees.cartes.map(function (c) { return {nom: c.env, lieu: c.lieu}; }), r.donnees.lieux, avant, []);
  if (!lieuVu) {                                        // ?lieu= : bandeau seul, la carte d'un envoi se choisit a la main
    lieuVu = true;
    var lieu = lieuDemande(r.donnees.lieux);
    if (lieu) bandeauLieu(document.querySelector("main"), libelleLieu(r.donnees.lieux, lieu), function () {});
  }
  s.insertBefore(o, s.firstChild); s.value = avant;
  if (s.selectedIndex < 0) s.value = "";                // carte disparue : retour sur « (choisir une carte) »
}
$("c-go").onclick = cree;
$("m-go").onclick = enregistre;
$("v-go").onclick = verifie;
$("t-go").onclick = fabrique;
$("e-carte").onchange = $("e-http").onchange = $("e-mqtt").onchange = prepare;
$("e-lire").onclick = prepare;
$("e-vu").onchange = majEnvoyer;
$("e-go").onclick = envoie;
chargeListe();
chargeCartes();
"""

# Theme pose AVANT le rendu (pas d'eclair blanc) : choix memorise, sinon celui du systeme (comme annuaire_page.py)
THEME_TETE = ("<script>(function () { var t = null; try { t = localStorage.getItem('fabrique-tapp-theme'); } catch (e) {}"
              " if (t !== 'clair' && t !== 'sombre') t = (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches)"
              " ? 'sombre' : 'clair'; document.documentElement.setAttribute('data-theme', t); })();</script>")
THEME_INTERRUPTEUR = ("<script>(function () { var c = document.getElementById('theme');"
                      " c.checked = document.documentElement.getAttribute('data-theme') === 'sombre';"
                      " c.onchange = function () { var t = this.checked ? 'sombre' : 'clair';"
                      " document.documentElement.setAttribute('data-theme', t);"
                      " try { localStorage.setItem('fabrique-tapp-theme', t); } catch (e) {} }; })();</script>")

PAGE = ("<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>Fabrique d'extensions</title><link rel=\"icon\" href=\"data:,\">" + THEME_TETE + "<style>" + CSS + "</style></head><body>"
        + HTML + THEME_INTERRUPTEUR + "<script>" + lieux.JS + JS + "</script></body></html>")
