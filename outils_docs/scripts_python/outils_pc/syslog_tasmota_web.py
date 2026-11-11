"""Page web du serveur syslog Tasmota (syslog_tasmota.py), servie sur http://127.0.0.1:7200
(et depuis le reseau local, avec le jeton de la session : acces_web.py).

Routes (syslog_tasmota.py) :
    GET /         cette page
    GET /flux     Server-Sent Events : 'etat', les modules connus ('module'), l'historique ('log'), puis le direct
    GET /etat     ecoute UDP, nombre de lignes recues, journal       GET /modules  registre des modules vus
    GET /lieux    table des lieux et identites des cartes (lieux.py) : puces de lieu, etiquettes, ?lieu=
Fiche 'log' : {t, ip, module, sev (0..7 ou null), horodatage (celui du module), app, categorie, texte}.

Barre : module (tous / un seul), severites affichees, filtre texte (ou regex), pause, effacer (l'affichage
seulement), export. Tableau des modules : clic = n'afficher que ce module.
"""

import lieux

PAGE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Syslog Tasmota</title>
<style>
 body{margin:0;background:#1e1e1e;color:#d4d4d4;font:13px Consolas,monospace;display:flex;flex-direction:column;height:100vh}
 .barre{display:flex;flex-wrap:wrap;gap:8px;padding:6px;background:#252526;border-bottom:1px solid #333;align-items:center}
 input,select{background:#3c3c3c;color:#fff;border:1px solid #555;padding:4px;font:inherit}
 input.erreur{border-color:#f14c4c}
 button{background:#0e639c;color:#fff;border:0;padding:4px 10px;cursor:pointer;font:inherit} button.actif{background:#a1260d}
 .pastille{display:inline-block;width:10px;height:10px;border-radius:50%;background:#808080;margin-right:4px}
 .gris{color:#9d9d9d} label{white-space:nowrap}
 #filtre{flex:1;min-width:180px} #module{min-width:200px}
 #modules{display:flex;flex-wrap:wrap;gap:6px;padding:4px 6px;background:#202020;border-bottom:1px solid #333}
 .mod{background:#2d2d30;border:1px solid #444;border-radius:3px;padding:2px 6px;cursor:pointer}
 .mod.choisi{border-color:#29b8db} .mod .n{color:#9d9d9d} .mod .e{color:#f14c4c}
 #lieux{display:flex;flex-wrap:wrap;gap:6px;padding:4px 6px;background:#202020;border-bottom:1px solid #333;align-items:center}
 #lieux:empty{display:none}
 .puce{background:#2d2d30;border:1px solid #444;border-radius:3px;padding:2px 6px;color:#d4d4d4}
 .puce.choisi{border-color:#29b8db} .puce .n{color:#9d9d9d} .puce .e{color:#f14c4c}
 .lieu{color:#dcdcaa} .bandeau-lieu{padding:4px 6px;background:#264f78;border-bottom:1px solid #333}
 #liste{flex:1;overflow:auto;padding:2px 6px}
 .l{white-space:pre-wrap;word-break:break-all;padding:1px 0;border-bottom:1px solid #2a2a2a}
 .t{color:#808080} .h{color:#6a9955} .md{color:#29b8db} .c{color:#c586c0}
 .s3{color:#f14c4c} .s4{color:#e5e510} .s6{color:#d4d4d4} .s7{color:#9d9d9d} .sx{color:#ce9178}
</style></head><body>
<div class="barre">
 <span><span class="pastille" id="pastille"></span><span id="etat">connexion...</span></span>
 <select id="module" title="module affiche"><option value="">Tous les modules</option></select>
 <label><input type="checkbox" class="sev" value="err" checked> erreurs</label>
 <label><input type="checkbox" class="sev" value="info" checked> info</label>
 <label><input type="checkbox" class="sev" value="debug" checked> debug</label>
 <input id="filtre" placeholder="filtre (texte, module, categorie BRY:...)">
 <label><input type="checkbox" id="regex"> regex</label>
 <label><input type="checkbox" id="hdev"> heure module</label>
 <button id="pause">Pause</button><button id="effacer">Effacer</button><button id="export">Exporter</button>
 <span class="gris" id="compte"></span>
</div>
<div id="lieux"></div>
<div id="modules"></div>
<div id="liste"></div>
<script>
/*LIEUX_JS*/
const $ = id => document.getElementById(id);
const MAX = 20000;                       // lignes gardees dans la page
let lignes = [], modules = {}, enPause = false, attente = [], filtreRe = null;
const nomSev = s => s === null ? "?" : ["EMERG","ALERT","CRIT","ERR","WARN","NOTICE","INFO","DEBUG"][s];
const famille = s => s === null ? "info" : s <= 4 ? "err" : s <= 6 ? "info" : "debug";
const esc = t => t.replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"})[c]);

function compileFiltre() {
  const f = $("filtre").value; $("filtre").classList.remove("erreur"); filtreRe = null;
  if (!f) return;
  try { filtreRe = $("regex").checked ? new RegExp(f, "i") : null; } catch (e) { $("filtre").classList.add("erreur"); }
}
function visible(l) {
  const m = $("module").value;
  if (m && l.module !== m) return false;
  if (lieuChoisi && codeLieu(l) !== lieuChoisi) return false;
  if (!document.querySelector(`.sev[value=${famille(l.sev)}]`).checked) return false;
  const f = $("filtre").value;
  if (!f) return true;
  const cible = l.module + " " + l.ip + " " + l.texte;
  if ($("regex").checked) return filtreRe ? filtreRe.test(cible) : true;
  return cible.toLowerCase().includes(f.toLowerCase());
}
function rendu(l) {
  const d = document.createElement("div");
  d.className = "l s" + (l.sev === null ? "x" : l.sev <= 3 ? 3 : l.sev);
  const heure = $("hdev").checked && l.horodatage ? l.horodatage : l.t;
  const etiquette = lieux.length ? `<span class="lieu">${esc(libelleLieu(codeLieu(l)))}</span> ` : "";
  d.innerHTML = `<span class="t">${esc(heure)}</span> ${etiquette}<span class="md">${esc(l.module)}</span> `
    + `<span class="h">${nomSev(l.sev)}</span> ` + esc(l.texte);
  return d;
}
function redessine() {
  const liste = $("liste"), frag = document.createDocumentFragment();
  let n = 0;
  for (const l of lignes) if (visible(l)) { frag.appendChild(rendu(l)); n++; }
  liste.replaceChildren(frag); liste.scrollTop = liste.scrollHeight;
  $("compte").textContent = `${n} / ${lignes.length} lignes`;
}
function ajoute(l) {
  lignes.push(l); compteLigne(l);
  if (lignes.length > MAX) { lignes.splice(0, lignes.length - MAX); redessine(); return; }
  if (!visible(l)) { $("compte").textContent = $("compte").textContent.replace(/\/ \d+/, "/ " + lignes.length); return; }
  const liste = $("liste"), enBas = liste.scrollHeight - liste.scrollTop - liste.clientHeight < 40;
  liste.appendChild(rendu(l));
  if (enBas) liste.scrollTop = liste.scrollHeight;
  const c = $("compte").textContent.match(/^(\d+)/);
  $("compte").textContent = `${(c ? +c[1] : 0) + 1} / ${lignes.length} lignes`;
}
function majModules() {
  const choix = $("module").value, sel = $("module"), bandeau = $("modules");
  const noms = Object.keys(modules).sort().filter(n => !lieuChoisi || codeLieu(modules[n]) === lieuChoisi);
  sel.replaceChildren(new Option("Tous les modules", ""), ...noms.map(n => new Option(`${n} (${modules[n].ip})`, n)));
  sel.value = choix;
  bandeau.replaceChildren(...noms.map(n => {
    const m = modules[n], d = document.createElement("span");
    d.className = "mod" + (n === choix ? " choisi" : "");
    d.title = `${m.ip} - derniere ligne ${m.dernier}`;
    d.innerHTML = `${esc(n)} <span class="n">${m.nb}</span>` + (m.erreurs ? ` <span class="e">${m.erreurs} err</span>` : "")
      + ` <span class="n">${esc(m.dernier || "")}</span>`;
    d.onclick = () => { $("module").value = n === $("module").value ? "" : n; majModules(); redessine(); };
    return d;
  }));
}

// Lieu d'une ligne : index par (module, ip) rempli a la demande, lieuDeHote ne parcourt les cartes qu'une fois par couple.
let cartes = [], lieux = [], lieuChoisi = "", cacheLieu = new Map(), compte = {}, puces = {};
function codeLieu(l) {
  const cle = l.module + "|" + l.ip;
  let c = cacheLieu.get(cle);
  if (c === undefined) {
    c = lieuDeHote(l.module, l.ip, cartes);
    if (!lieux.some(x => x[0] === c)) c = "autres";
    if (cacheLieu.size > 5000) cacheLieu.clear();       // les noms viennent du reseau : cache borne
    cacheLieu.set(cle, c);
  }
  return c;
}
const libelleLieu = c => (lieux.find(x => x[0] === c) || [0, "Autres"])[1];
function majPuce(code) {
  const p = puces[code], c = compte[code] || {n: 0, e: 0};
  if (!p) return;
  p.n.textContent = c.n; p.e.textContent = c.e ? " " + c.e + " err" : "";
}
function compteLigne(l) {
  if (!lieux.length) return;
  const e = l.sev !== null && l.sev <= 3 ? 1 : 0;
  for (const code of ["", codeLieu(l)]) {
    const c = compte[code] || (compte[code] = {n: 0, e: 0});
    c.n++; c.e += e; majPuce(code);
  }
}
function recompte() { compte = {}; Object.keys(puces).forEach(majPuce); lignes.forEach(compteLigne); }
function choisitLieu(code) {
  lieuChoisi = code;
  for (const k in puces) puces[k].bouton.classList.toggle("choisi", k === code);
  majModules(); redessine();
}
function dessinePuces() {
  const bloc = $("lieux"), tete = document.createElement("span");
  tete.className = "gris"; tete.textContent = "Lieu";
  bloc.replaceChildren(tete); puces = {};
  for (const [code, libelle] of [["", "Tous"], ...lieux, ["autres", "Autres"]]) {
    const b = document.createElement("button"), n = document.createElement("span"), e = document.createElement("span");
    b.type = "button"; b.className = "puce"; b.dataset.lieu = code || "tous";
    n.className = "n"; e.className = "e";
    b.append(libelle + " ", n, e);
    b.onclick = () => choisitLieu(code === lieuChoisi ? "" : code);
    bloc.appendChild(b); puces[code] = {bouton: b, n, e};
  }
}
fetch("/lieux").then(r => r.json()).then(d => {
  cartes = d.cartes; lieux = d.lieux; cacheLieu.clear();
  dessinePuces(); recompte();
  const demande = lieuDemande(lieux);                  // ?lieu= : premier chargement seulement, jamais memorise
  if (demande) {
    bandeauLieu(document.body, libelleLieu(demande), () => choisitLieu(""));
    choisitLieu(demande);
  } else choisitLieu(lieuChoisi);
}).catch(() => {});                                     // echec : pas de puces, page d'avant

const flux = new EventSource("/flux");
flux.addEventListener("etat", e => {
  const s = JSON.parse(e.data);
  $("etat").textContent = `UDP ${s.ecoute}` + (s.logHost ? ` (SYS_LOG_HOST ${s.logHost})` : "") + ` - depuis ${s.depuis}`;
  $("pastille").style.background = "#16825d";
});
flux.addEventListener("module", e => { const m = JSON.parse(e.data); modules[m.module] = m; majModules(); });
flux.addEventListener("log", e => { const l = JSON.parse(e.data); enPause ? attente.push(l) : ajoute(l); });
flux.onerror = () => { $("pastille").style.background = "#f14c4c"; $("etat").textContent = "serveur injoignable (reconnexion...)"; };
flux.onopen = () => { lignes = []; modules = {}; attente = []; recompte(); $("liste").replaceChildren(); };

$("module").onchange = () => { majModules(); redessine(); };
document.querySelectorAll(".sev").forEach(c => c.onchange = redessine);
$("filtre").oninput = () => { compileFiltre(); redessine(); };
$("regex").onchange = () => { compileFiltre(); redessine(); };
$("hdev").onchange = redessine;
$("pause").onclick = () => {
  enPause = !enPause; $("pause").textContent = enPause ? `Reprendre` : "Pause"; $("pause").classList.toggle("actif", enPause);
  if (!enPause) { attente.forEach(ajoute); attente = []; }
};
$("effacer").onclick = () => { lignes = []; attente = []; recompte(); redessine(); };
$("export").onclick = () => {
  const texte = lignes.filter(visible).map(l => `${l.t} ${l.ip} ${l.module} ${nomSev(l.sev)} ${l.texte}`).join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([texte + "\n"], {type: "text/plain"}));
  a.download = "syslog_" + new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-") + ".log"; a.click();
};
</script></body></html>
""".replace("/*LIEUX_JS*/", lieux.JS)
