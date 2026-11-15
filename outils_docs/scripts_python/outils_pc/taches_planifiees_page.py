"""Page « Taches planifiees » (taches_planifiees_web.py) : bandeau de sante, voie PC, voie GitHub.

Tout ce qui vient du serveur, de gh ou des fichiers de resultat (noms d'env, jobs, chemins, messages) s'affiche par textContent
(helper `el`), jamais par innerHTML. Liens GitHub : seulement https://github.com/ (verifie cote page). Les gestes (A4) sont dans taches_planifiees_page_gestes.py.
Sonde : test_taches_planifiees_page_chrome.py.
"""

from taches_planifiees_page_gestes import CSS_GESTES, JS_GESTES

CSS = """
:root{color-scheme:light;--fond:#f6f7f9;--carte:#fff;--bord:#ddd;--texte:#222;--doux:#666;--bleu:#2563eb;--vert:#1e7e3a;
  --orange:#a86400;--rouge:#c0392b;--orange-fond:#fff4e0;--vert-fond:#e3f4e8;--rouge-fond:#fdecea;--btn:#fff;--btn-bord:#888}
@media (prefers-color-scheme:dark){:root:not([data-theme="clair"]){color-scheme:dark;--fond:#121417;--carte:#1d2025;--bord:#3a3f47;--texte:#e6e6e6;
  --doux:#a8adb5;--bleu:#5b93ff;--vert:#3fbf63;--orange:#f0a020;--rouge:#ff6b5b;--orange-fond:#33270f;--vert-fond:#16301f;--rouge-fond:#3a1d1a;--btn:#262a30;--btn-bord:#555b64}}
:root[data-theme="sombre"]{color-scheme:dark;--fond:#121417;--carte:#1d2025;--bord:#3a3f47;--texte:#e6e6e6;--doux:#a8adb5;--bleu:#5b93ff;
  --vert:#3fbf63;--orange:#f0a020;--rouge:#ff6b5b;--orange-fond:#33270f;--vert-fond:#16301f;--rouge-fond:#3a1d1a;--btn:#262a30;--btn-bord:#555b64}
*{box-sizing:border-box}
body{margin:0;font:14px system-ui,sans-serif;color:var(--texte);background:var(--fond)}
main{max-width:1100px;margin:0 auto;padding:12px 16px 24px}
header{display:flex;align-items:baseline;gap:14px;margin-bottom:10px;flex-wrap:wrap}
h1{font-size:20px;margin:0} h2{font-size:15px;margin:0 0 8px}
.doux{color:var(--doux)} .petit{font-size:12px}
.bandeau{padding:10px 14px;border-radius:8px;font-weight:600;margin-bottom:12px;border:1px solid var(--bord);overflow-wrap:anywhere}
.bandeau.vert{background:var(--vert-fond);color:var(--vert)} .bandeau.orange{background:var(--orange-fond);color:var(--orange)} .bandeau.rouge{background:var(--rouge-fond);color:var(--rouge)}
.colonnes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;align-items:start}
@media (max-width:760px){.colonnes{grid-template-columns:minmax(0,1fr)}}
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:8px;padding:12px;min-width:0}
.btn{padding:6px 12px;border:1px solid var(--btn-bord);border-radius:6px;background:var(--btn);font:inherit;color:inherit;cursor:pointer}
.btn:disabled{opacity:.45;cursor:default}
.kv{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:3px 12px;margin:6px 0} .kv dt{color:var(--doux)} .kv dd{margin:0;overflow-wrap:anywhere}
ul.liste{margin:4px 0;padding-left:18px} ul.liste li{overflow-wrap:anywhere;margin:2px 0}
.badge{display:inline-block;font-size:11px;padding:1px 7px;border-radius:10px;border:1px solid var(--bord);margin-right:4px}
.badge.ok{background:var(--vert-fond);color:var(--vert)} .badge.ko{background:var(--rouge-fond);color:var(--rouge)} .badge.en{background:var(--orange-fond);color:var(--orange)}
.alerte{color:var(--rouge);margin:4px 0} .panne{color:var(--orange);margin:4px 0}
a{color:var(--bleu)} code{font:12px ui-monospace,Consolas,monospace;overflow-wrap:anywhere}
"""

JS = r"""
function $(id) { return document.getElementById(id); }
function el(tag, cls, texte) {
  var e = document.createElement(tag);
  if (cls) e.className = cls;
  if (texte != null) e.textContent = texte;
  return e;
}
function lien(url, texte) {
  if (typeof url !== "string" || url.indexOf("https://github.com/") !== 0) return el("span", null, texte);
  var a = el("a", null, texte); a.href = url; a.target = "_blank"; a.rel = "noopener noreferrer"; return a;
}
function ligne(dl, cle, valeur) {
  dl.appendChild(el("dt", null, cle));
  var d = el("dd"); if (valeur instanceof Node) d.appendChild(valeur); else d.textContent = valeur == null || valeur === "" ? "-" : String(valeur);
  dl.appendChild(d);
}
function liste(titre, items, rend) {
  var f = document.createDocumentFragment();
  f.appendChild(el("h3", "petit", titre));
  if (!items.length) { f.appendChild(el("p", "doux petit", "Aucun.")); return f; }
  var ul = el("ul", "liste");
  items.forEach(function (x) { var li = el("li"); li.appendChild(rend(x)); ul.appendChild(li); });
  f.appendChild(ul); return f;
}
function dureeH(s) { return s ? Math.round(s / 60) + " min" : "-"; }

function rendPc(c, pc) {
  c.textContent = ""; c.appendChild(el("h2", null, "Sur ce PC (tâche Windows)"));
  var t = pc.tache, dl = el("dl", "kv");
  ligne(dl, "Tâche", t.existe ? (t.actif ? "activée" : "désactivée") : "absente" + (t.erreur ? " (" + t.erreur + ")" : ""));
  if (t.existe) { ligne(dl, "Prochaine exécution", t.prochaine); ligne(dl, "Dernière exécution", t.derniere); }
  ligne(dl, "Configuration", (pc.config.actif ? "actif" : "inactif") + ", port " + pc.config.port + ", " + pc.config.envs_exclus.length + " env exclu(s)");
  c.appendChild(dl);
  var d = pc.dernier;
  if (!d) { c.appendChild(el("p", "doux", "Aucun résultat de nuit pour l'instant (" + pc.dossier + ").")); return; }
  if (d.illisible) { c.appendChild(el("p", "panne", "Résultat illisible : " + d.illisible)); return; }
  var dl2 = el("dl", "kv");
  ligne(dl2, "Dernière nuit", d.debut);
  ligne(dl2, "Code", d.code === 0 ? "0 (tout compile)" : d.code);
  if (d.refus) ligne(dl2, "Refus", d.refus);
  if (d.fin) ligne(dl2, "Fin", d.fin);
  ligne(dl2, "Envs compilés", d.nb_envs + (d.nb_prevus != null ? " sur " + d.nb_prevus : "") + ", durée " + dureeH(d.secondes));
  c.appendChild(dl2);
  c.appendChild(liste("Envs en échec", d.echecs, function (e) {
    var s = el("span"); s.appendChild(el("code", null, e.env)); s.appendChild(document.createTextNode(" : " + e.resultat));
    if (e.journal) { s.appendChild(document.createTextNode(" - journal ")); s.appendChild(el("code", null, e.journal)); }
    return s;
  }));
  c.appendChild(liste("Dernières nuits", pc.historique, function (h) {
    var s = el("span"); s.appendChild(document.createTextNode((h.debut || h.fichier) + " : "));
    s.appendChild(el("span", "badge " + (h.code === 0 ? "ok" : "ko"), "code " + h.code));
    s.appendChild(document.createTextNode(h.echecs.length + " échec(s)")); return s;
  }));
}

function rendGh(c, g) {
  c.textContent = ""; c.appendChild(el("h2", null, "Sur GitHub (workflow Build_custom)"));
  g.alertes.forEach(function (a) { c.appendChild(el("p", "alerte", a)); });
  g.pannes.forEach(function (p) { c.appendChild(el("p", "panne", "Non vérifié, " + p)); });
  var dl = el("dl", "kv");
  ligne(dl, "Actions du dépôt", g.permissions === true ? "autorisées" : g.permissions === false ? "désactivées" : "inconnu");
  ligne(dl, "Workflow", g.workflow || "inconnu");
  ligne(dl, "Dernier run planifié", g.age_planifie_h != null ? "il y a " + g.age_planifie_h + " h" : "inconnu");
  c.appendChild(dl);
  c.appendChild(liste("Jobs en échec du dernier run", g.echecs, function (j) { return lien(j.url, j.nom); }));
  c.appendChild(liste("Derniers runs", g.runs, function (r) {
    var s = el("span"); s.appendChild(lien(r.url, "#" + r.databaseId));
    s.appendChild(document.createTextNode(" " + r.event + " " + (r.createdAt || "") + " "));
    s.appendChild(el("span", "badge " + (r.conclusion === "success" ? "ok" : r.conclusion ? "ko" : "en"), r.conclusion || r.status)); return s;
  }));
}

var enCours = false, relance = false;     // relance : un geste reussi pendant un rechargement demande un NOUVEAU releve
function charge(frais) {
  if (enCours) { if (frais) relance = true; return; }
  enCours = true; $("actualiser").disabled = true;
  fetch("/etat" + (frais ? "?frais=1" : ""), { cache: "no-store" }).then(function (r) {
    if (!r.ok) throw new Error("HTTP " + r.status); return r.json();
  }).then(function (e) {
    var b = $("bandeau"); b.className = "bandeau " + e.niveau; b.textContent = e.phrase;
    $("instant").textContent = "Relevé du " + e.instant;
    rendPc($("pc"), e.pc); rendGh($("gh"), e.github); gestesPc($("pc"), e); gestesGh($("gh"), e);
  }).catch(function (x) {
    var b = $("bandeau"); b.className = "bandeau orange"; b.textContent = "L'outil ne répond pas : " + x.message;
  }).then(function () { enCours = false; $("actualiser").disabled = false; if (relance) { relance = false; charge(true); } });
}
$("actualiser").onclick = function () { charge(true); };
charge(false);
"""

HTML = """<main><header><h1>Tâches planifiées</h1><span class="doux petit" id="instant"></span>
<button class="btn" id="actualiser" style="margin-left:auto">Actualiser</button></header>
<div class="bandeau orange" id="bandeau">Lecture en cours...</div>
<div class="colonnes"><section class="carte" id="pc"></section><section class="carte" id="gh"></section></div>
<p class="doux petit">Les boutons agissent sur la tâche Windows de ce PC, sur le dépôt et sur GitHub, et seulement depuis ce PC. La sélection des envs GitHub est un fichier du dépôt : il part avec le prochain <code>git push</code>.</p></main>"""

PAGE = ("<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>Tâches planifiées</title><link rel=\"icon\" href=\"data:,\"><style>" + CSS + CSS_GESTES + "</style></head><body>"
        + HTML + "<script>" + JS_GESTES + JS + "</script></body></html>")
