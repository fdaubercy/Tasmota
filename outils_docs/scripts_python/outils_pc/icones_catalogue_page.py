"""Page « Catalogue d'icones » (icones_catalogue_web.py) : grille des glyphes du firmware, fiche au clic, PNG, sites, icones absentes.

Tout ce qui vient du catalogue (noms, chemins, licences, usages) s'affiche par textContent, jamais par innerHTML. Les glyphes sont dessines
par la police MDI du depot (GET /lib/mdi.ttf, code MDI F0335 pour le code servi U+E335) : aucune ressource externe. Lecture seule.
Sonde : test_icones_catalogue_page_chrome.py.
"""

CSS = """
:root{color-scheme:light;--fond:#f6f7f9;--carte:#fff;--bord:#ddd;--texte:#222;--doux:#666;--bleu:#2563eb;--vert:#1e7e3a;
  --btn:#fff;--btn-bord:#888;--piste:#e9e9ea;--champ:#fff;--sur-bleu:#fff;--interrupteur:#fff;--interrupteur-on:#34c759;--ombre:rgba(0,0,0,.3)}
:root[data-theme="sombre"]{color-scheme:dark;--fond:#121417;--carte:#1d2025;--bord:#3a3f47;--texte:#e6e6e6;--doux:#a8adb5;
  --bleu:#5b93ff;--vert:#3fbf63;--btn:#262a30;--btn-bord:#555b64;--piste:#39393d;--champ:#15171b;--sur-bleu:#0b0d10}
@font-face{font-family:MDI;src:url(/lib/mdi.ttf) format('truetype')}
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
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:12px;margin-bottom:12px;min-width:0}
.ligne{display:flex;gap:10px;align-items:center;margin:6px 0;flex-wrap:wrap}
input[type=search],select{font:inherit;padding:6px 8px;border:1px solid var(--bord);border-radius:5px;background:var(--champ);color:var(--texte)}
input[type=search]{flex:1;min-width:180px}
.btn{display:inline-block;padding:6px 12px;border:1px solid var(--btn-bord);border-radius:6px;background:var(--btn);font:inherit;color:inherit;cursor:pointer}
.btn.prim{background:var(--bleu);border-color:var(--bleu);color:var(--sur-bleu)}
.grille{display:grid;grid-template-columns:repeat(auto-fill,minmax(88px,1fr));gap:6px}
.grille button{display:flex;flex-direction:column;align-items:center;gap:2px;padding:6px 2px;background:var(--champ);border:1px solid var(--bord);
  border-radius:6px;color:var(--texte);cursor:pointer;font:inherit}
.grille button:hover,.grille button:focus-visible,.grille button.choisi{border-color:var(--bleu)}
.glyphe{font-family:MDI;font-size:28px;line-height:34px}
.grille .nom{font-size:11px;color:var(--doux);overflow-wrap:anywhere;text-align:center}
.fiche{display:grid;grid-template-columns:96px minmax(0,1fr);gap:14px;align-items:start}
.fiche .grand{font-family:MDI;font-size:80px;line-height:96px;text-align:center;border:1px solid var(--bord);border-radius:8px;background:var(--champ)}
@media (max-width:560px){.fiche{grid-template-columns:minmax(0,1fr)}}
code{font:13px ui-monospace,Consolas,monospace;background:var(--champ);border:1px solid var(--bord);border-radius:4px;padding:1px 6px;overflow-wrap:anywhere}
ul{margin:4px 0;padding-left:20px} li{overflow-wrap:anywhere}
table{border-collapse:collapse;width:100%} th,td{text-align:left;padding:4px 8px;border-bottom:1px solid var(--bord);overflow-wrap:anywhere}
th{color:var(--doux);font-weight:600;font-size:12px}
a{color:var(--bleu)}
"""

HTML = """
<main>
<header><h1>Catalogue d'icônes</h1><span class="doux petit">Glyphes du firmware, PNG du dépôt, sites libres : lecture seule, rien n'est écrit.</span>
<label class="theme"><span>Mode sombre</span><input type="checkbox" id="theme"><span class="interrupteur"></span></label></header>
<section class="carte"><div class="ligne">
 <input type="search" id="recherche" placeholder="Rechercher par nom, code ou chemin" aria-label="Rechercher">
 <label>Source <select id="source"><option value="">toutes</option><option value="firmware">Firmware</option><option value="png">PNG</option><option value="sites">Sites</option></select></label>
</div><div class="doux petit" id="etat" role="status">Chargement…</div></section>
<section class="carte" id="s-fiche" hidden><h2 id="f-titre"></h2><div class="fiche"><div class="grand" id="f-grand" aria-hidden="true"></div><div>
 <p>Code à copier pour l'attribut <code>text</code> : <code id="f-code"></code> <button class="btn prim" id="f-copie" type="button">Copier</button>
  <span class="doux petit" id="f-copie-etat" role="status"></span></p>
 <p>Nom MDI : <code id="f-nom"></code> · code MDI : <code id="f-mdi"></code> · <a id="f-lien" target="_blank" rel="noopener noreferrer">pictogrammers.com</a></p>
 <p>Polices : <span id="f-polices"></span></p>
 <div>Usages dans le parc : <ul id="f-usages"></ul></div></div></div></section>
<section class="carte" id="s-firmware"><h2>Firmware <span class="doux petit" id="n-firmware"></span></h2><div class="grille" id="grille"></div></section>
<section class="carte" id="s-png"><h2>PNG du dépôt <span class="doux petit" id="n-png"></span></h2><div id="pngs"></div></section>
<section class="carte" id="s-sites"><h2>Sites d'icônes et de logos <span class="doux petit" id="n-sites"></span></h2><div id="sites"></div></section>
<section class="carte" id="s-absentes"><h2>Absentes du firmware <span class="doux petit" id="n-absentes"></span></h2>
 <p class="doux petit">Codes utilisés dans les écrans mais absents des polices embarquées : l'écran affiche un carré vide.</p><div id="absentes"></div></section>
</main>
"""

JS = r"""
"use strict";
var C = {glyphes: [], pngs: [], sources: [], absentes: []};
function $(id) { return document.getElementById(id); }
function vide(n) { while (n.firstChild) n.removeChild(n.firstChild); }
function el(tag, classe, texte) { var e = document.createElement(tag); if (classe) e.className = classe; if (texte != null) e.textContent = texte; return e; }
function glyphe(mdi) { return String.fromCodePoint(parseInt(mdi, 16)); }
function codeServi(g) { return "\\u" + g.servi; }
function norme(t) { return String(t).toLowerCase(); }
function filtre() { return {q: norme($("recherche").value.trim()), s: $("source").value}; }

function rend() {
  var f = filtre();
  var gl = C.glyphes.filter(function (g) { return !f.q || norme(g.nom).indexOf(f.q) >= 0 || norme(g.servi).indexOf(f.q) >= 0 || norme(g.mdi).indexOf(f.q) >= 0; });
  var pn = C.pngs.filter(function (p) { return !f.q || norme(p.chemin).indexOf(f.q) >= 0; });
  var si = C.sources.filter(function (s) { return !f.q || norme(s.nom + " " + s.licence + " " + s.usage).indexOf(f.q) >= 0; });
  var ab = C.absentes.filter(function (a) { return !f.q || norme(a.code).indexOf(f.q) >= 0; });
  $("s-firmware").hidden = !!f.s && f.s !== "firmware";
  $("s-absentes").hidden = !!f.s && f.s !== "firmware";
  $("s-png").hidden = !!f.s && f.s !== "png";
  $("s-sites").hidden = !!f.s && f.s !== "sites";
  $("n-firmware").textContent = "(" + gl.length + "/" + C.glyphes.length + ")";
  $("n-png").textContent = "(" + pn.length + ")";
  $("n-sites").textContent = "(" + si.length + ")";
  $("n-absentes").textContent = "(" + ab.length + ")";
  rendGrille(gl); rendPngs(pn); rendSites(si); rendAbsentes(ab);
}

function rendGrille(liste) {
  var g = $("grille"); vide(g);
  liste.forEach(function (i) {
    var b = el("button"); b.type = "button"; b.setAttribute("data-nom", i.nom); b.title = i.nom;
    b.appendChild(el("span", "glyphe", glyphe(i.mdi))); b.appendChild(el("span", "nom", i.nom));
    b.onclick = function () { fiche(i); };
    g.appendChild(b);
  });
  if (!liste.length) g.appendChild(el("p", "doux", "Aucun glyphe."));
}

function tableau(entetes, lignes) {
  var t = el("table"), h = el("tr");
  entetes.forEach(function (e) { h.appendChild(el("th", null, e)); }); t.appendChild(h);
  lignes.forEach(function (l) { var r = el("tr"); l.forEach(function (c) { if (c instanceof Node) { var d = el("td"); d.appendChild(c); r.appendChild(d); } else r.appendChild(el("td", null, c)); }); t.appendChild(r); });
  return t;
}
function octets(n) { return n >= 1024 ? (n / 1024).toFixed(1) + " Ko" : n + " o"; }
function rendPngs(liste) {
  var d = $("pngs"); vide(d);
  if (!liste.length) { d.appendChild(el("p", "doux", "Aucun PNG dans data/ ni dans outils_docs/atelier_ecrans/images/.")); return; }
  d.appendChild(tableau(["Fichier", "Taille", "Poids"], liste.map(function (p) { return [p.chemin, p.largeur + " × " + p.hauteur, octets(p.poids)]; })));
}
function lienSur(url, texte) {
  if (!/^https?:\/\//.test(url)) return el("span", null, texte);
  var a = el("a", null, texte); a.setAttribute("href", url); a.setAttribute("target", "_blank"); a.setAttribute("rel", "noopener noreferrer"); return a;
}
function rendSites(liste) {
  var d = $("sites"); vide(d);
  if (!liste.length) { d.appendChild(el("p", "doux", "Aucun site (outils_docs/ICONES_IMAGES_SOURCES.md absent ?).")); return; }
  d.appendChild(tableau(["Site", "Licence", "Usage", "Catégorie"], liste.map(function (s) { return [lienSur(s.url, s.nom), s.licence, s.usage, s.categorie]; })));
}
function rendAbsentes(liste) {
  var d = $("absentes"); vide(d);
  if (!liste.length) { d.appendChild(el("p", "doux", "Aucune : tous les codes des écrans sont dans le catalogue.")); return; }
  d.appendChild(tableau(["Code", "Utilisé dans"], liste.map(function (a) { return ["\\u" + a.code, a.usages.join(", ")]; })));
}

function fiche(i) {
  $("s-fiche").hidden = false;
  Array.prototype.forEach.call($("grille").querySelectorAll("button"), function (b) { b.classList.toggle("choisi", b.getAttribute("data-nom") === i.nom); });
  $("f-titre").textContent = i.nom;
  $("f-grand").textContent = glyphe(i.mdi);
  $("f-code").textContent = codeServi(i);
  $("f-nom").textContent = i.nom;
  $("f-mdi").textContent = i.mdi;
  $("f-copie-etat").textContent = "";
  var lien = $("f-lien");
  if (/^[a-z0-9-]+$/.test(i.nom)) lien.setAttribute("href", "https://pictogrammers.com/library/mdi/icon/" + i.nom + "/"); else lien.removeAttribute("href");
  var p = i.polices && i.polices.length ? i.polices.join(", ") : "montserrat-28 recommandé (montserrat-10, -14 et -20 portent aussi les glyphes du firmware)";
  $("f-polices").textContent = p;
  var u = $("f-usages"); vide(u);
  if (!i.usages.length) u.appendChild(el("li", "doux", "aucun usage trouvé dans les écrans ni les .be"));
  i.usages.forEach(function (x) { u.appendChild(el("li", null, x)); });
  $("f-copie").onclick = function () { copie(codeServi(i)); };
}
function copie(texte) {
  var fin = function (ok) { $("f-copie-etat").textContent = ok ? "Copié : " + texte : "Copie impossible : sélectionnez le code à la main."; };
  var repli = function () {
    var t = document.createElement("textarea"); t.value = texte; document.body.appendChild(t); t.select();
    var ok = false; try { ok = document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(t); fin(ok);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(texte).then(function () { fin(true); }, repli); else repli();
}

function charge() {
  fetch("/catalogue").then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }).then(function (d) {
    C = d; $("etat").textContent = C.glyphes.length + " glyphes, " + C.pngs.length + " PNG, " + C.sources.length + " sites."; rend();
  }).catch(function (e) { $("etat").textContent = "Catalogue indisponible : " + e.message; });
}
$("recherche").oninput = rend;
$("source").onchange = rend;
charge();
"""

THEME_TETE = ("<script>(function () { var t = null; try { t = localStorage.getItem('icones-theme'); } catch (e) {}"
              " if (t !== 'clair' && t !== 'sombre') t = (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches)"
              " ? 'sombre' : 'clair'; document.documentElement.setAttribute('data-theme', t); })();</script>")
THEME_INTERRUPTEUR = ("<script>(function () { var c = document.getElementById('theme');"
                      " c.checked = document.documentElement.getAttribute('data-theme') === 'sombre';"
                      " c.onchange = function () { var t = this.checked ? 'sombre' : 'clair';"
                      " document.documentElement.setAttribute('data-theme', t);"
                      " try { localStorage.setItem('icones-theme', t); } catch (e) {} }; })();</script>")

PAGE = ("<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>Catalogue d'icônes</title><link rel=\"icon\" href=\"data:,\">" + THEME_TETE + "<style>" + CSS + "</style></head><body>"
        + HTML + THEME_INTERRUPTEUR + "<script>" + JS + "</script></body></html>")
