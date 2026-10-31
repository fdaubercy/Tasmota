"""Page web du sniffeur I2C (sniffeur_i2c.py), servie sur le port 7350 (ce PC, ou le reseau avec jeton).

Routes : sniffeur_i2c_http.py. Evenements SSE de /flux : 'etat', 'stats' (inventaire par adresse),
'lot' (liste de fiches : l'historique a l'ouverture, puis chaque lot lu sur le port), 'raz'.
Fiche : {n, h, nature (trame|alerte|info|ordre|reponse), texte} ; une trame ajoute
{a, rw, hex, nack, fin, f, tu, puce, ambigu, candidats, registre}.
Onglets : Bus (fil, filtres, inventaire), Envoi (par la carte / par le sniffeur), Aide (sniffeur_i2c_aide.AIDE).
Toutes les URL sont relatives : la page marche telle quelle depuis un autre appareil (jeton, acces_web.py).
"""

import sniffeur_i2c_aide

PAGE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Sniffeur I2C</title>
<style>
 body{margin:0;background:#1e1e1e;color:#d4d4d4;font:13px Consolas,monospace;display:flex;flex-direction:column;height:100vh}
 .barre{display:flex;flex-wrap:wrap;gap:8px;padding:6px;background:#252526;border-bottom:1px solid #333;align-items:center}
 input,select{background:#3c3c3c;color:#fff;border:1px solid #555;padding:4px;font:inherit} input.court{width:56px}
 button{background:#0e639c;color:#fff;border:0;padding:4px 10px;cursor:pointer;font:inherit} button.actif{background:#a1260d}
 button.discret{background:#3c3c3c} button:disabled{opacity:.5;cursor:default}
 .pastille{display:inline-block;width:10px;height:10px;border-radius:50%;background:#808080;margin-right:4px}
 .gris{color:#9d9d9d} label{white-space:nowrap} .sep{border-left:1px solid #444;height:20px}
 #filtre{flex:1;min-width:160px} #message{color:#f14c4c}
 #stats{display:flex;flex-wrap:wrap;gap:6px;padding:4px 6px;background:#202020;border-bottom:1px solid #333}
 .st{background:#2d2d30;border:1px solid #444;border-radius:3px;padding:2px 6px;cursor:pointer}
 .st.choisi{border-color:#29b8db} .st .e{color:#f14c4c} .st .n{color:#9d9d9d}
 #liste{flex:1;overflow:auto;padding:2px 6px}
 .l{white-space:pre-wrap;word-break:break-all;padding:1px 0;border-bottom:1px solid #2a2a2a}
 .t{color:#808080} .ad{color:#29b8db} .hx{color:#ce9178} .pu{color:#c586c0} .rg{color:#dcdcaa} .ko{color:#f14c4c}
 .s{display:inline-block;width:18px;text-align:center;border-radius:3px;margin:0 4px}
 .s-W{background:#6a3d9a} .s-R{background:#264f78}
 .n-alerte .tx{color:#e5a50a;font-weight:bold} .n-info .tx{color:#89d185;font-style:italic}
 .n-ordre .tx{color:#29b8db} .n-reponse .tx{color:#89d185}
 .onglets{display:flex;gap:2px;padding:4px 6px 0;background:#181818;border-bottom:1px solid #333}
 .onglets button{background:#2d2d30;color:#9d9d9d;border-radius:3px 3px 0 0} .onglets button.choisi{background:#0e639c;color:#fff}
 .vue{flex:1;display:flex;flex-direction:column;min-height:0} .cache{display:none !important}
 .aide,.envoi{overflow:auto;padding:4px 16px 40px;font:13px/1.5 Segoe UI,Arial,sans-serif;display:block}
 .aide h2,.envoi h2{color:#29b8db;border-bottom:1px solid #333;margin-top:22px} .aide h3{color:#c586c0;margin-bottom:4px}
 .aide code,.envoi code{font-family:Consolas,monospace;color:#ce9178}
 table{border-collapse:collapse;margin:6px 0} td,th{border:1px solid #3c3c3c;padding:3px 7px;text-align:left;vertical-align:top}
 th{background:#2d2d30} .apercu{font-family:Consolas,monospace;color:#ce9178;margin:6px 0;min-height:1.4em}
 .resultat{font-family:Consolas,monospace;color:#89d185;white-space:pre-wrap} .attention{color:#e5a50a}
</style></head><body>
<div class="onglets"><button id="ongletBus" class="choisi">Bus</button><button id="ongletEnvoi">Envoi</button><button id="ongletAide">Aide</button></div>
<div id="vueBus" class="vue">
<div class="barre">
 <span><span class="pastille" id="pastille"></span><span id="etat">connexion...</span></span>
 <select id="port" title="port USB du sniffeur"></select>
 <button class="discret" id="rafraichir" title="relister les ports">&#8635;</button>
 <button id="ouvrir">Ouvrir</button>
 <span class="sep"></span>
 <span class="gris">Carte observée</span><select id="carte" title="ses puces levent les ambiguites d'adresse (0x20, 0x68)"></select>
 <span class="sep"></span>
 <button class="discret" id="raz" title="remet a zero compteurs et historique (le journal sur disque reste)">RAZ</button>
 <a id="exportTxt" href="export?format=txt"><button class="discret">Exporter .txt</button></a>
 <a id="exportJson" href="export?format=json"><button class="discret">.json</button></a>
 <span id="message"></span>
</div>
<div class="barre">
 <select id="filtreAdr"><option value="">Toutes les adresses</option></select>
 <label><input type="checkbox" id="voirW" checked> écritures</label>
 <label><input type="checkbox" id="voirR" checked> lectures</label>
 <label><input type="checkbox" id="nackSeuls"> NACK seuls</label>
 <label><input type="checkbox" id="voirAutres" checked> alertes, ordres, infos</label>
 <input id="filtre" placeholder="filtre texte, puce, registre ou hexa">
 <button id="pause">Pause</button><button class="discret" id="effacer" title="vide l'affichage (pas l'historique)">Effacer</button>
 <span class="gris" id="compte"></span>
</div>
<div id="stats"></div>
<div id="liste"></div>
</div>
<div id="vueEnvoi" class="vue envoi cache">
<h2>Par la carte Tasmota (bus en service)</h2>
<p class="gris">La carte, seul maître du bus, fait l'échange (commande Berry <code>Br</code> par HTTP). Le fil du sniffeur doit ensuite montrer la trame.</p>
<div class="barre" style="background:none;border:0;padding:0">
 <span class="gris">IP</span><input id="cIp" placeholder="192.168.0.x ou ip:port" style="width:170px">
 <span class="gris">puce</span><select id="cPuce"></select>
 <span class="gris">adresse 0x</span><input id="cAdr" class="court" value="48">
 <span class="gris">registre</span><select id="cReg"></select>
 <span class="gris">octets</span><input id="cN" class="court" type="number" min="1" max="4" value="2">
 <span class="gris">valeur 0x (vide = lecture)</span><input id="cVal" class="court" style="width:90px">
 <button id="cApercu" class="discret">Aperçu</button><button id="cEnvoyer">Envoyer</button>
</div>
<div class="apercu" id="cCommande"></div><div class="resultat" id="cResultat"></div>
<h2>Par le sniffeur (composant isolé, au banc)</h2>
<p class="attention">Uniquement un composant DÉBRANCHÉ de sa carte : sur un bus en service, deux maîtres se percutent. Le firmware refuse si le bus a vécu dans les 2 dernières secondes.</p>
<div class="barre" style="background:none;border:0;padding:0">
 <label><input type="checkbox" id="mIsole"> composant débranché de sa carte</label>
 <span class="gris">opération</span><select id="mNom"><option value="MWR">écrire le registre puis lire</option><option value="MR">lire</option><option value="MW">écrire</option></select>
 <span class="gris">adresse 0x</span><input id="mAdr" class="court" value="48">
 <span class="gris">octets écrits (hexa)</span><input id="mD" style="width:120px" value="00">
 <span class="gris">octets lus</span><input id="mN" class="court" type="number" min="1" max="32" value="2">
 <button id="mApercu" class="discret">Aperçu</button><button id="mEnvoyer">Envoyer</button>
</div>
<div class="apercu" id="mCommande"></div><div class="resultat" id="mResultat"></div>
</div>
<div id="vueAide" class="vue aide cache"><!--AIDE--></div>
<script>
const $ = id => document.getElementById(id);
const MAX = 20000;
let lignes = [], stats = [], enPause = false, attente = [], puces = {}, ouvert = false, portActif = "";
const esc = t => String(t).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"})[c]);
const h2 = n => (n & 255).toString(16).toUpperCase().padStart(2, "0");

async function poste(chemin, corps, zone) {
  $("message").textContent = "";
  if (zone) zone.textContent = "";
  try {
    const r = await fetch(chemin, {method: "POST", headers: {"X-Sniffeur": "1", "Content-Type": "application/json"},
                                   body: JSON.stringify(corps || {})});
    const texte = await r.text();
    if (!r.ok) { (zone || $("message")).textContent = texte; return null; }
    try { return JSON.parse(texte); } catch (e) { return {}; }
  } catch (e) { (zone || $("message")).textContent = "serveur injoignable"; return null; }
}
async function listePorts(choix) {
  try {
    const ports = await (await fetch("ports")).json();
    $("port").replaceChildren(...ports.map(p => new Option(`${p.port}${p.sniffeur ? " (ESP32/Pico)" : ""} - ${p.description}`, p.port)));
    if (choix || portActif) $("port").value = choix || portActif;
  } catch (e) {}
}
// ---------------------------------------------------------------- fil
function visible(l) {
  if (l.nature !== "trame") return $("voirAutres").checked;
  const adr = $("filtreAdr").value;
  if (adr !== "" && String(l.a) !== adr) return false;
  if (!$(l.rw === "W" ? "voirW" : "voirR").checked) return false;
  if ($("nackSeuls").checked && l.nack === null) return false;
  const f = $("filtre").value.toLowerCase();
  return !f || [l.hex, l.puce, l.registre, l.texte, "0x" + h2(l.a)].join(" ").toLowerCase().includes(f);
}
function rendu(l) {
  const d = document.createElement("div");
  d.className = "l n-" + l.nature;
  if (l.nature !== "trame") { d.innerHTML = `<span class="t">${esc(l.h)}</span> <span class="tx">${esc(l.texte)}</span>`; return d; }
  const puce = l.puce ? l.puce + (l.ambigu ? " ?" : "") : (l.candidats || []).join("/") || "?";
  d.innerHTML = `<span class="t">${esc(l.h)}</span> <span class="ad">0x${h2(l.a)}</span><span class="s s-${l.rw}">${l.rw}</span>`
    + `<span class="hx">[${esc(l.hex || "-")}]</span>` + (l.nack !== null ? ` <span class="ko">NACK@${l.nack}</span>` : "")
    + (l.fin !== "STOP" ? ` <span class="${l.fin === "TRONQUE" ? "ko" : "gris"}">${l.fin}</span>` : "")
    + ` <span class="gris">${l.f ? l.f.toFixed(1) + " kHz" : ""}</span> <span class="pu" title="${esc((l.candidats || []).join(" ou "))}">${esc(puce)}</span>`
    + (l.registre ? ` <span class="rg">${esc(l.registre)}</span>` : "") + ` <span class="tx">${esc(l.texte)}</span>`;
  return d;
}
function compte() { $("compte").textContent = `${$("liste").childElementCount} / ${lignes.length} lignes` + (enPause ? ` (${attente.length} en attente)` : ""); }
function redessine() {
  const frag = document.createDocumentFragment();
  for (const l of lignes) if (visible(l)) frag.appendChild(rendu(l));
  $("liste").replaceChildren(frag); $("liste").scrollTop = $("liste").scrollHeight; compte();
}
function ajouteLot(lot) {
  lignes.push(...lot);
  if (lignes.length > MAX) { lignes.splice(0, lignes.length - MAX); redessine(); return; }
  const liste = $("liste"), enBas = liste.scrollHeight - liste.scrollTop - liste.clientHeight < 40;
  const frag = document.createDocumentFragment();
  for (const l of lot) if (visible(l)) frag.appendChild(rendu(l));
  liste.appendChild(frag);
  if (enBas) liste.scrollTop = liste.scrollHeight;
  compte();
}
function majStats() {
  const choix = $("filtreAdr").value;
  stats.sort((a, b) => a.a - b.a);
  $("filtreAdr").replaceChildren(new Option("Toutes les adresses", ""), ...stats.map(s => new Option(`0x${h2(s.a)} ${s.puce}`, String(s.a))));
  $("filtreAdr").value = choix;
  $("stats").replaceChildren(...stats.map(s => {
    const d = document.createElement("span");
    d.className = "st" + (String(s.a) === choix ? " choisi" : "");
    d.innerHTML = `0x${h2(s.a)} <span class="n">${esc(s.puce || "?")}</span> : ${s.transactions} (${s.ecritures} W / ${s.lectures} R)`
      + (s.nack ? ` <span class="e">${s.nack} NACK</span>` : "")
      + (s.f ? ` <span class="n">${s.f.toFixed(1)} kHz (max ${s.f_max.toFixed(1)})</span>` : "") + ` <span class="n">vue ${esc(s.derniere)}</span>`;
    d.onclick = () => { $("filtreAdr").value = String(s.a) === $("filtreAdr").value ? "" : String(s.a); majStats(); redessine(); };
    return d;
  }));
}
const flux = new EventSource("flux");
flux.addEventListener("etat", e => {
  const s = JSON.parse(e.data);
  ouvert = s.ouvert; if (s.port) portActif = s.port;
  const id = s.identite ? ` - ${s.identite.puce} SDA=${s.identite.sda} SCL=${s.identite.scl}, ${s.identite.ech} MHz` : (s.ouvert ? " - sniffeur muet ?" : "");
  $("etat").textContent = (s.ouvert ? s.port : "port fermé") + id + ` - ${s.nb} transactions, ${s.alertes} alerte(s)`
    + (s.perdues ? `, ${s.perdues} PERDUE(S)` : "") + (s.illisibles ? `, ${s.illisibles} ligne(s) illisible(s)` : "") + (s.erreur ? ` - ${s.erreur}` : "");
  $("pastille").style.background = s.ouvert ? (s.identite ? "#16825d" : "#e5a50a") : "#a1260d";
  $("ouvrir").textContent = s.ouvert ? "Fermer" : "Ouvrir";
  $("ouvrir").classList.toggle("actif", s.ouvert);
  if (s.ouvert && s.port) { if (![...$("port").options].some(o => o.value === s.port)) $("port").add(new Option(s.port, s.port)); $("port").value = s.port; }
  if ($("carte").value !== s.carte && [...$("carte").options].some(o => o.value === s.carte)) $("carte").value = s.carte;
});
flux.addEventListener("stats", e => { stats = JSON.parse(e.data); majStats(); });
flux.addEventListener("lot", e => { const lot = JSON.parse(e.data); if (enPause) { attente.push(...lot); compte(); } else ajouteLot(lot); });
flux.addEventListener("raz", () => { lignes = []; attente = []; redessine(); });
flux.onerror = () => { $("pastille").style.background = "#808080"; $("etat").textContent = "serveur injoignable (reconnexion...)"; };
flux.onopen = () => { lignes = []; attente = []; $("liste").replaceChildren(); };

$("rafraichir").onclick = () => listePorts($("port").value);
$("ouvrir").onclick = () => poste("port", ouvert ? {action: "fermer"} : {action: "ouvrir", port: $("port").value});
$("raz").onclick = () => poste("raz");
$("pause").onclick = () => {
  enPause = !enPause; $("pause").textContent = enPause ? "Reprendre" : "Pause"; $("pause").classList.toggle("actif", enPause);
  if (!enPause) { const lot = attente; attente = []; ajouteLot(lot); }
  compte();
};
$("effacer").onclick = () => { lignes = []; attente = []; redessine(); };
for (const id of ["filtreAdr", "voirW", "voirR", "nackSeuls", "voirAutres"]) $(id).onchange = () => { majStats(); redessine(); };
$("filtre").oninput = redessine;
$("carte").onchange = async () => {
  const r = await poste("carte", {carte: $("carte").value});
  if (r && r.ip !== undefined) $("cIp").value = r.ip || "";
  if (r && r.puces) { const p = Object.keys(r.puces)[0]; if (p) { $("cPuce").value = p; choisitPuce(); } }
};
// ---------------------------------------------------------------- envoi
function choisitPuce() {
  const p = puces[$("cPuce").value];
  if (!p) return;
  $("cAdr").value = h2(p.adresses[0]); $("cN").value = String(Math.min(p.taille, 4));
  $("cReg").replaceChildren(...Object.entries(p.registres).map(([r, nom]) => new Option(`0x${r} ${nom}`, r)));
}
$("cPuce").onchange = choisitPuce;
const ordreCarte = () => ({voie: "carte", ip: $("cIp").value, a: $("cAdr").value, reg: $("cReg").value || "00",
                           n: +$("cN").value, valeur: $("cVal").value.trim() || null});
const ordreMaitre = () => ({voie: "maitre", nom: $("mNom").value, a: $("mAdr").value, d: $("mD").value, n: +$("mN").value,
                            isole: $("mIsole").checked});
async function envoie(ordre, zoneCmd, zoneRes, ecriture) {
  const ap = await poste("ordre", {...ordre, apercu: true}, zoneRes);
  if (!ap) return;
  zoneCmd.textContent = ap.commande;
  if (ecriture && !confirm(`ÉCRITURE sur le bus :\n${ap.commande}\n\nEnvoyer ?`)) { zoneRes.textContent = "annulé : rien n'a été envoyé"; return; }
  zoneRes.textContent = "envoi...";
  const r = await poste("ordre", {...ordre, confirme: ecriture}, zoneRes);
  if (r) zoneRes.textContent = r.reponse !== undefined ? `${r.ok ? "réponse" : "échec"} : ${r.reponse}` : (r.ok ? `lu : [${r.d || "-"}]` : `refus : ${r.err}`);
}
$("cApercu").onclick = async () => { const ap = await poste("ordre", {...ordreCarte(), apercu: true}, $("cResultat")); if (ap) $("cCommande").textContent = ap.commande; };
$("mApercu").onclick = async () => { const ap = await poste("ordre", {...ordreMaitre(), apercu: true}, $("mResultat")); if (ap) $("mCommande").textContent = ap.commande; };
$("cEnvoyer").onclick = () => envoie(ordreCarte(), $("cCommande"), $("cResultat"), !!$("cVal").value.trim());
$("mEnvoyer").onclick = () => envoie(ordreMaitre(), $("mCommande"), $("mResultat"), $("mNom").value !== "MR");
// ---------------------------------------------------------------- onglets, chargement
for (const [onglet, vue] of [["ongletBus", "vueBus"], ["ongletEnvoi", "vueEnvoi"], ["ongletAide", "vueAide"]])
  $(onglet).onclick = () => {
    for (const v of ["vueBus", "vueEnvoi", "vueAide"]) $(v).classList.toggle("cache", v !== vue);
    for (const o of ["ongletBus", "ongletEnvoi", "ongletAide"]) $(o).classList.toggle("choisi", o === onglet);
  };
(async () => {
  listePorts();
  try {
    const cartes = await (await fetch("cartes")).json();
    $("carte").replaceChildren(new Option("aucune (toutes les puces possibles)", ""), ...cartes.map(c => new Option(c.replace(/^data\//, ""), c)));
    puces = await (await fetch("puces")).json();
    $("cPuce").replaceChildren(...Object.entries(puces).map(([p, f]) => new Option(f.nom, p)));
    choisitPuce();
  } catch (e) { $("message").textContent = "chargement des cartes impossible"; }
})();
</script></body></html>
""".replace("<!--AIDE-->", sniffeur_i2c_aide.AIDE)
