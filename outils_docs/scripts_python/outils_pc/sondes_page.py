"""Page « Sondes en cours » (sondes_web.py) : une carte par banc ou sonde Chrome, avec avancement reel, rafraichie toutes les 2 s.

Tout ce qui vient des fichiers de suivi ou des processus (nom, phase, dernier cas, echecs) s'affiche par textContent (helper `el`), jamais par innerHTML.
Arreter une sonde passe par un bouton a DEUX TEMPS (1er clic = armer, 2e = confirmer, 6 s) ; POST /arreter avec l'en-tete X-Sondes: 1.
Sonde : test_sondes_page_chrome.py.
"""

CSS = """
:root{color-scheme:light;--fond:#f6f7f9;--carte:#fff;--bord:#ddd;--texte:#222;--doux:#666;--vert:#1e7e3a;--orange:#a86400;--rouge:#c0392b;
  --orange-fond:#fff4e0;--vert-fond:#e3f4e8;--rouge-fond:#fdecea;--btn:#fff;--btn-bord:#888;--barre:#d8dce2;--barre-ok:#2563eb}
@media (prefers-color-scheme:dark){:root:not([data-theme="clair"]){color-scheme:dark;--fond:#121417;--carte:#1d2025;--bord:#3a3f47;--texte:#e6e6e6;
  --doux:#a8adb5;--vert:#3fbf63;--orange:#f0a020;--rouge:#ff6b5b;--orange-fond:#33270f;--vert-fond:#16301f;--rouge-fond:#3a1d1a;--btn:#262a30;--btn-bord:#555b64;--barre:#343942;--barre-ok:#5b93ff}}
*{box-sizing:border-box}
body{margin:0;font:14px system-ui,sans-serif;color:var(--texte);background:var(--fond)}
main{max-width:1000px;margin:0 auto;padding:12px 16px 24px}
header{display:flex;align-items:baseline;gap:14px;margin-bottom:10px;flex-wrap:wrap}
h1{font-size:20px;margin:0} .doux{color:var(--doux)} .petit{font-size:12px}
.bandeau{padding:10px 14px;border-radius:8px;font-weight:600;margin-bottom:12px;border:1px solid var(--bord);overflow-wrap:anywhere}
.bandeau.vert{background:var(--vert-fond);color:var(--vert)} .bandeau.orange{background:var(--orange-fond);color:var(--orange)} .bandeau.rouge{background:var(--rouge-fond);color:var(--rouge)}
.sonde{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:10px 12px;margin-bottom:8px;min-width:0}
.sonde.orpheline{border-color:var(--rouge);border-width:2px}
.tete{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap} .tete .nom{font-weight:600;overflow-wrap:anywhere}
.badge{display:inline-block;font-size:11px;padding:1px 7px;border-radius:10px;border:1px solid var(--bord)}
.badge.ok{background:var(--vert-fond);color:var(--vert)} .badge.ko{background:var(--rouge-fond);color:var(--rouge)} .badge.en{background:var(--orange-fond);color:var(--orange)}
.barre{height:8px;border-radius:4px;background:var(--barre);overflow:hidden;margin:6px 0} .barre>i{display:block;height:100%;background:var(--barre-ok)}
.ligne{margin:3px 0;overflow-wrap:anywhere} code{font:12px ui-monospace,Consolas,monospace;overflow-wrap:anywhere}
ul.echecs{margin:4px 0;padding-left:18px;color:var(--rouge)} ul.echecs li{overflow-wrap:anywhere}
.btn{padding:6px 12px;border:1px solid var(--btn-bord);border-radius:6px;background:var(--btn);font:inherit;color:inherit;cursor:pointer}
.btn.danger{border-color:var(--rouge);color:var(--rouge)} .msg{min-height:1em;margin:6px 0;overflow-wrap:anywhere}
"""

JS = r"""
function $(id) { return document.getElementById(id); }
function el(tag, cls, texte) {
  var e = document.createElement(tag);
  if (cls) e.className = cls;
  if (texte != null) e.textContent = texte;
  return e;
}
function duree(s) { return s < 90 ? s + " s" : s < 5400 ? Math.round(s / 60) + " min" : (s / 3600).toFixed(1) + " h"; }
var LIBELLE = { en_cours: "en cours", sans_suivi: "sans suivi", termine: "terminée", disparue: "disparue", orpheline: "orpheline" };
var armes = {};                       // pid -> minuteur : l'etat « arme » survit au rafraichissement de 2 s

function post(corps) {
  return fetch("/arreter", { method: "POST", headers: { "Content-Type": "application/json", "X-Sondes": "1" }, body: JSON.stringify(corps) }).then(function (r) {
    return r.text().then(function (t) { if (!r.ok) throw new Error(t || ("HTTP " + r.status)); return t ? JSON.parse(t) : {}; });
  });
}
function message(texte, ko) { var m = $("msg"); m.textContent = texte; m.className = "msg " + (ko ? "alerte" : "doux"); m.style.color = ko ? "var(--rouge)" : ""; }
function deuxTemps(cle, texte, attention, corps) {
  var b = el("button", "btn", armes[cle] ? "Confirmer : " + attention : texte);
  if (armes[cle]) b.className = "btn danger";
  b.onclick = function () {
    if (!armes[cle]) { armes[cle] = setTimeout(function () { delete armes[cle]; rend(dernier); }, 6000); rend(dernier); return; }
    clearTimeout(armes[cle]); delete armes[cle]; rend(dernier);
    message("En cours...", false);
    post(corps).then(function (r) { message("Arrêtés : " + (r.arretes.length ? r.arretes.join(", ") : "aucun") + (r.echecs.length ? " ; échecs : " + r.echecs.length : ""), r.echecs.length > 0); charge(); })
      .catch(function (x) { message(x.message, true); });
  };
  return b;
}
function carte(s) {
  var c = el("section", "sonde " + s.etat), t = el("div", "tete");
  t.appendChild(el("span", "nom", s.nom));
  t.appendChild(el("span", "badge " + (s.etat === "orpheline" || s.etat === "disparue" ? "ko" : s.etat === "termine" ? (s.verdict === "rouge" ? "ko" : "ok") : "en"), LIBELLE[s.etat] || s.etat));
  if (s.verdict) t.appendChild(el("span", "badge " + (s.verdict === "vert" ? "ok" : "ko"), s.verdict === "vert" ? "vert" : "rouge"));
  t.appendChild(el("span", "doux petit", (s.nature === "chrome" ? "Chrome" : "banc") + " · pid " + s.pid + " · " + duree(s.duree_s)));
  c.appendChild(t);
  if (s.etat === "en_cours" || s.etat === "termine" || s.etat === "disparue") {
    if (s.total) { var b = el("div", "barre"), i = el("i"); i.style.width = Math.min(100, Math.round(100 * s.faits / s.total)) + "%"; b.appendChild(i); c.appendChild(b); }
    c.appendChild(el("div", "ligne", s.faits + (s.total ? " / " + s.total : "") + " vérification(s) faite(s)" + (s.phase ? " · phase : " + s.phase : "")));
    if (s.dernier) c.appendChild(el("div", "ligne doux petit", "Dernier cas : " + s.dernier));
  } else if (s.etat === "orpheline") {
    c.appendChild(el("div", "ligne", "Le processus qui l'a lancée (pid " + s.parent + ") n'existe plus : ce Chrome reste ouvert pour rien."));
  } else {
    c.appendChild(el("div", "ligne doux", "Pas de suivi d'avancement pour ce processus (durée seulement)."));
  }
  if (s.echecs.length) { var u = el("ul", "echecs"); s.echecs.forEach(function (e) { u.appendChild(el("li", null, e)); }); c.appendChild(u); }
  if (s.etat === "en_cours" || s.etat === "sans_suivi" || s.etat === "orpheline") {
    var r = el("div", "ligne"); r.appendChild(deuxTemps("p" + s.pid, "Arrêter", "arrêter " + s.nom + " et ses sous-processus", { pid: s.pid })); c.appendChild(r);
  }
  return c;
}
var dernier = null, enCours = false;
function rend(e) {
  if (!e) return;
  var b = $("bandeau"); b.className = "bandeau " + e.niveau; b.textContent = e.phrase;
  $("instant").textContent = "Relevé du " + e.instant;
  var z = $("liste"); z.textContent = "";
  if (!e.sondes.length) z.appendChild(el("p", "doux", "Aucun banc ni sonde Chrome en cours ou récent."));
  e.sondes.forEach(function (s) { z.appendChild(carte(s)); });
  var o = $("orph"); o.textContent = "";
  if (e.sondes.some(function (s) { return s.etat === "orpheline"; })) o.appendChild(deuxTemps("orphelines", "Arrêter les orphelines", "arrêter tous les Chrome orphelins", { orphelines: true }));
}
function charge() {
  if (enCours) return; enCours = true;
  fetch("/etat", { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
    .then(function (e) { dernier = e; rend(e); })
    .catch(function (x) { var b = $("bandeau"); b.className = "bandeau orange"; b.textContent = "L'outil ne répond pas : " + x.message; })
    .then(function () { enCours = false; });
}
setInterval(charge, 2000);
charge();
"""

HTML = """<main><header><h1>Sondes en cours</h1><span class="doux petit" id="instant"></span></header>
<div class="bandeau orange" id="bandeau">Lecture en cours...</div>
<div id="orph"></div><div class="msg doux" id="msg"></div><div id="liste"></div>
<p class="doux petit">Bancs <code>test_*.py</code> / <code>banc_*.py</code> et Chrome de sonde de ce PC. L'avancement vient des lignes <code>OK</code> / <code>KO</code> que le banc imprime
(module <code>suivi_sondes</code>) : un banc sans suivi n'a que sa durée. « Arrêter » tue le processus et ses sous-processus, seulement depuis ce PC.</p></main>"""

PAGE = ("<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>Sondes en cours</title><link rel=\"icon\" href=\"data:,\"><style>" + CSS + "</style></head><body>"
        + HTML + "<script>" + JS + "</script></body></html>")
