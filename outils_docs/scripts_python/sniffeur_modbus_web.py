"""Page web du sniffeur ModBus (sniffeur_modbus.py), servie sur http://127.0.0.1:7300.

Routes (sniffeur_modbus.py) :
    GET  /         cette page
    GET  /flux     Server-Sent Events : 'etat', 'stats', l'historique ('trame'), puis le direct ;
                   aussi 'message' (erreur d'envoi) et 'raz'
    GET  /ports    ports serie presents [{port, description, ch343}]
    POST /port     {action: "ouvrir"|"fermer", port, debit}
    POST /envoi    {hex, crc, repete, intervalle}
    POST /emulation {id, actif} | {id, registre, champ, valeur}     POST /debit {action: chercher|corriger}
    POST /raz   (compteurs et historique)
    GET  /carte    esclaves et appareils du persist du maitre      POST /decode {hex, requete, crc}
Les POST exigent l'en-tete X-Sniffeur: 1 (protection contre une page tierce visant 127.0.0.1).
Evenements SSE en plus : 'emulation' (esclaves emulables et leurs valeurs), 'debit' (resultat
de la recherche / correction). Fiche 'trame' : {t, dt (ms depuis la precedente), sens (bus|pc|emul|udp|mqtt|--|!!),
hex, crc, nature (requete|reponse|exception|ko|timeout|alerte|info|?), id, fc, texte, norme, metier, champs, lat (ms, reponse appariee)}.
Onglet Aide : sniffeur_modbus_aide.AIDE, insere a la place de <!--AIDE-->. Un clic sur une trame du
bus en montre le detail champ par champ ; un clic sur un exemple de l'aide le decode.
"""

import sniffeur_modbus_aide

PAGE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Sniffeur ModBus</title>
<style>
 body{margin:0;background:#1e1e1e;color:#d4d4d4;font:13px Consolas,monospace;display:flex;flex-direction:column;height:100vh}
 .barre{display:flex;flex-wrap:wrap;gap:8px;padding:6px;background:#252526;border-bottom:1px solid #333;align-items:center}
 input,select{background:#3c3c3c;color:#fff;border:1px solid #555;padding:4px;font:inherit}
 input.erreur{border-color:#f14c4c} input.court{width:48px}
 button{background:#0e639c;color:#fff;border:0;padding:4px 10px;cursor:pointer;font:inherit} button.actif{background:#a1260d}
 button.discret{background:#3c3c3c}
 .pastille{display:inline-block;width:10px;height:10px;border-radius:50%;background:#808080;margin-right:4px}
 .gris{color:#9d9d9d} label{white-space:nowrap} .sep{border-left:1px solid #444;height:20px}
 #filtre{flex:1;min-width:160px} #hex{min-width:220px;flex:1}
 #message{color:#f14c4c}
 #stats{display:flex;flex-wrap:wrap;gap:6px;padding:4px 6px;background:#202020;border-bottom:1px solid #333}
 .st{background:#2d2d30;border:1px solid #444;border-radius:3px;padding:2px 6px;cursor:pointer}
 .st.choisi{border-color:#29b8db} .st .e{color:#f14c4c} .st .n{color:#9d9d9d}
 #liste{flex:1;overflow:auto;padding:2px 6px}
 .l{white-space:pre-wrap;word-break:break-all;padding:1px 0;border-bottom:1px solid #2a2a2a}
 .t{color:#808080} .dt{color:#6a6a6a;display:inline-block;width:70px;text-align:right}
 .s{display:inline-block;width:42px;text-align:center;border-radius:3px;margin:0 4px}
 .s-udp{background:#1f6f5c} .s-mqtt{background:#5c3d1f} .n-push .tx{color:#4ec9b0} .n-udp .tx{color:#9d9d9d}
 .s-bus{background:#264f78} .s-pc{background:#6a3d9a} .s-emul{background:#7a5c00} .s---{background:#5a1d1d}
 .hx{color:#ce9178} .ok{color:#6a9955} .ko{color:#f14c4c} .lat{color:#29b8db}
 .n-reponse .tx{color:#89d185} .n-ko .tx,.n-exception .tx,.n-timeout .tx{color:#f14c4c}
 .s-\!\!{background:#8a5a00} .n-alerte .tx{color:#e5a50a;font-weight:bold} .n-info .tx{color:#89d185;font-style:italic}
 #panneauEmul{padding:4px 6px;background:#202020;border-bottom:1px solid #333;max-height:40vh;overflow:auto}
 #panneauEmul td,#panneauEmul th{padding:1px 6px} .esc{margin:4px 0} #resDebit{color:#e5a50a}
 .l{cursor:pointer} .l:hover{background:#252526}
 .onglets{display:flex;gap:2px;padding:4px 6px 0;background:#181818;border-bottom:1px solid #333}
 .onglets button{background:#2d2d30;color:#9d9d9d;border-radius:3px 3px 0 0} .onglets button.choisi{background:#0e639c;color:#fff}
 .vue{flex:1;display:flex;flex-direction:column;min-height:0} .cache{display:none !important}
 .aide{overflow:auto;padding:4px 16px 40px;font:13px/1.5 Segoe UI,Arial,sans-serif;display:block}
 .aide h2{color:#29b8db;border-bottom:1px solid #333;margin-top:22px} .aide h3{color:#c586c0;margin-bottom:4px}
 .aide code,.detail code{font-family:Consolas,monospace;color:#ce9178}
 table{border-collapse:collapse;margin:6px 0} td,th{border:1px solid #3c3c3c;padding:3px 7px;text-align:left;vertical-align:top}
 th{background:#2d2d30}
 .ex{cursor:pointer;background:#2d2d30;padding:1px 5px;border-radius:3px} .ex:hover{outline:1px solid #29b8db}
 .exemple{margin:2px 0}
 .barre.plate{background:none;border:0;padding:6px 0} #decHex{flex:2;min-width:240px} #decReq{flex:1;min-width:180px}
 .detail{margin:3px 0 6px 120px;padding:4px 8px;background:#252526;border-left:2px solid #29b8db;font-size:12px;cursor:auto}
 .detail td{font-family:Consolas,monospace} .detail .m{color:#89d185}
</style></head><body>
<div class="onglets"><button id="ongletBus" class="choisi">Bus</button><button id="ongletAide">Aide</button></div>
<div id="vueBus" class="vue">
<div class="barre">
 <span><span class="pastille" id="pastille"></span><span id="etat">connexion...</span></span>
 <select id="port" title="port du convertisseur USB-RS485"></select>
 <button class="discret" id="rafraichir" title="relister les ports">&#8635;</button>
 <select id="debit">
  <option>1200</option><option>2400</option><option>4800</option><option>9600</option>
  <option selected>19200</option><option>38400</option><option>57600</option><option>115200</option>
 </select>
 <button id="ouvrir">Ouvrir</button>
 <span class="sep"></span>
 <button class="discret" id="boutonEmul" title="le PC repond a la place d'esclaves du persist (debrancher les vrais)">Emulation...</button>
 <button class="discret" id="raz" title="remet a zero compteurs et historique">RAZ</button>
 <span id="message"></span>
</div>
<div class="barre">
 <span class="gris">Carte relais id</span><input id="carteId" class="court" type="number" min="1" max="247" value="1">
 <button id="lire">Lire 16 sorties</button>
 <span class="gris">canal</span><input id="canal" class="court" type="number" min="0" max="16" value="1">
 <select id="ordre">
  <option value="1">open</option><option value="2">close</option><option value="3" selected>toggle</option>
  <option value="4">latch</option><option value="5">momentary</option><option value="6">delay</option>
  <option value="7">open all</option><option value="8">close all</option>
 </select>
 <span class="gris">tempo</span><input id="tempo" class="court" type="number" min="0" max="255" value="0">
 <button id="commander">Commander</button>
 <button class="discret" id="chercherDebit" title="balaie les debits : adresse lue en diffusion (le PC devient maitre)">Chercher debit / adresse</button>
 <button class="actif cache" id="corrigerDebit">Corriger</button><span id="resDebit"></span>
 <span class="sep"></span>
 <input id="hex" placeholder="trame hexa, ex. 01 03 00 01 00 10">
 <label><input type="checkbox" id="crc" checked> + CRC</label>
 <span class="gris">x</span><input id="repete" class="court" type="number" min="1" max="1000" value="1">
 <span class="gris">toutes les</span><input id="intervalle" class="court" type="number" min="0.05" step="0.05" value="0.5"><span class="gris">s</span>
 <button id="envoyer">Envoyer</button>
</div>
<div class="barre">
 <select id="filtreId"><option value="">Toutes les adresses</option></select>
 <label><input type="checkbox" class="nat" value="requete" checked> requetes</label>
 <label><input type="checkbox" class="nat" value="reponse" checked> reponses</label>
 <label><input type="checkbox" class="nat" value="erreur" checked> erreurs</label>
 <label><input type="checkbox" class="nat" value="alerte" checked> alertes</label>
 <label title="push des esclaves (ModbusPushUDP : multicast direct, ou MQTT = relaye par le maitre) et autres messages du groupe multicast"><input type="checkbox" class="nat" value="udp" checked> UDP</label>
 <input id="filtre" placeholder="filtre texte ou hexa">
 <button id="pause">Pause</button><button id="effacer">Effacer</button><button id="export">Exporter</button>
 <span class="gris" id="compte"></span>
</div>
<div id="panneauEmul" class="cache"></div>
<div id="stats"></div>
<div id="liste"></div>
</div>
<div id="vueAide" class="vue aide cache"><!--AIDE--></div>
<script>
const $ = id => document.getElementById(id);
const MAX = 20000;
let lignes = [], stats = [], enPause = false, attente = [];
const esc = t => String(t).replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"})[c]);
const h2 = n => (n & 255).toString(16).toUpperCase().padStart(2, "0");
const famille = n => ({requete: "requete", reponse: "reponse", alerte: "alerte", info: "alerte", push: "udp", udp: "udp"})[n] || "erreur";

async function poste(chemin, corps) {
  $("message").textContent = "";
  try {
    const r = await fetch(chemin, {method: "POST", headers: {"X-Sniffeur": "1", "Content-Type": "application/json"},
                                   body: JSON.stringify(corps || {})});
    if (!r.ok) $("message").textContent = await r.text();
    return r.ok;
  } catch (e) { $("message").textContent = "serveur injoignable"; return false; }
}
async function listePorts(choix) {
  try {
    const ports = await (await fetch("/ports")).json();
    $("port").replaceChildren(...ports.map(p => new Option(`${p.port}${p.ch343 ? " (CH343)" : ""} - ${p.description}`, p.port)));
    if (choix || portActif) $("port").value = choix || portActif;
  } catch (e) {}
}
function visible(l) {
  const id = $("filtreId").value;
  if (id !== "" && String(l.id) !== id) return false;
  if (!document.querySelector(`.nat[value=${famille(l.nature)}]`).checked) return false;
  const f = $("filtre").value.toLowerCase();
  return !f || (l.hex + " " + l.texte).toLowerCase().includes(f);
}
function rendu(l) {
  const d = document.createElement("div");
  d.className = "l n-" + l.nature;
  d.innerHTML = `<span class="t">${esc(l.t)}</span><span class="dt">${l.dt === null ? "" : "+" + l.dt + " ms"}</span>`
    + `<span class="s s-${esc(l.sens)}">${esc(l.sens.toUpperCase())}</span>`
    + (l.hex ? `<span class="hx">${esc(l.hex)}</span> ${l.crc ? '<span class="ok">CRC OK</span>' : '<span class="ko">CRC KO</span>'} ` : "")
    + `<span class="tx" title="${esc(l.norme || "")}">${esc(l.texte)}</span>` + (l.lat !== null ? ` <span class="lat">(${l.lat} ms)</span>` : "");
  if (l.champs) d.onclick = e => {
    if (e.target.closest(".detail")) return;
    const ouvert = d.querySelector(".detail");
    ouvert ? ouvert.remove() : d.appendChild(detail(l));
  };
  return d;
}
function detail(r) {
  const d = document.createElement("div");
  d.className = "detail";
  d.innerHTML = `<div>Norme : ${esc(r.norme || "")}</div>` + (r.metier ? `<div class="m">Sens : ${esc(r.metier)}</div>` : "")
    + "<table><tr><th>Champ</th><th>Octets</th><th>Norme</th><th>Sens</th></tr>"
    + (r.champs || []).map(c => `<tr><td>${esc(c.champ)}</td><td><code>${esc(c.hex)}</code></td><td>${esc(c.norme)}</td><td class="m">${esc(c.metier)}</td></tr>`).join("")
    + "</table>";
  return d;
}
function compte() { $("compte").textContent = `${$("liste").childElementCount} / ${lignes.length} trames`; }
function redessine() {
  const frag = document.createDocumentFragment();
  for (const l of lignes) if (visible(l)) frag.appendChild(rendu(l));
  $("liste").replaceChildren(frag); $("liste").scrollTop = $("liste").scrollHeight; compte();
}
function ajoute(l) {
  lignes.push(l);
  if (lignes.length > MAX) { lignes.splice(0, lignes.length - MAX); redessine(); return; }
  if (visible(l)) {
    const liste = $("liste"), enBas = liste.scrollHeight - liste.scrollTop - liste.clientHeight < 40;
    liste.appendChild(rendu(l));
    if (enBas) liste.scrollTop = liste.scrollHeight;
  }
  compte();
}
function majStats() {
  const choix = $("filtreId").value;
  stats.sort((a, b) => a.id - b.id);
  $("filtreId").replaceChildren(new Option("Toutes les adresses", ""), ...stats.map(s => new Option(`id ${s.id}`, String(s.id))));
  $("filtreId").value = choix;
  $("stats").replaceChildren(...stats.map(s => {
    const d = document.createElement("span");
    d.className = "st" + (String(s.id) === choix ? " choisi" : "");
    d.innerHTML = `id ${s.id} : ${s.requetes} req, ${s.reponses} rep`
      + (s.sans_reponse ? ` <span class="e">${s.sans_reponse} sans reponse</span>` : "")
      + (s.exceptions ? ` <span class="e">${s.exceptions} exception(s)</span>` : "")
      + (s.lat !== null ? ` <span class="n">latence ${s.lat} ms (max ${s.lat_max})</span>` : "")
      + (s.push ? ` <span class="n">${s.push} push UDP</span>` : "") + (s.push_ecartes ? ` <span class="e">${s.push_ecartes} ecarte(s)</span>` : "");
    d.onclick = () => { $("filtreId").value = String(s.id) === $("filtreId").value ? "" : String(s.id); majStats(); redessine(); };
    return d;
  }));
}

let ouvert = false, portActif = "";
const flux = new EventSource("/flux");
flux.addEventListener("etat", e => {
  const s = JSON.parse(e.data);
  ouvert = s.ouvert; if (s.port) portActif = s.port;
  $("etat").textContent = (s.ouvert ? `${s.port} a ${s.debit} bauds` : "port ferme") + ` - ${s.nb} trames, ${s.ko} CRC KO, ${s.alertes} alerte(s) - UDP ${s.udp} : ${s.push} push - relais MQTT ${s.mqtt}`
    + ` - echo local ${s.echo}` + (s.emulation.length ? ` - EMULATION id ${s.emulation.join(", ")}` : "")
    + (s.tache ? ` - ${s.tache} en cours...` : "") + (s.erreur ? ` - ${s.erreur}` : "");
  $("chercherDebit").disabled = !!s.tache;
  $("pastille").style.background = s.ouvert ? "#16825d" : "#a1260d";
  $("ouvrir").textContent = s.ouvert ? "Fermer" : "Ouvrir";
  $("ouvrir").classList.toggle("actif", s.ouvert);
  if (s.ouvert && s.port) { if (![...$("port").options].some(o => o.value === s.port)) $("port").add(new Option(s.port, s.port)); $("port").value = s.port; $("debit").value = String(s.debit); }
});
flux.addEventListener("stats", e => { stats = JSON.parse(e.data); majStats(); });
flux.addEventListener("trame", e => { const l = JSON.parse(e.data); enPause ? attente.push(l) : ajoute(l); });
flux.addEventListener("message", e => { $("message").textContent = JSON.parse(e.data).texte; });
flux.addEventListener("raz", () => { lignes = []; attente = []; redessine(); });
flux.onerror = () => { $("pastille").style.background = "#808080"; $("etat").textContent = "serveur injoignable (reconnexion...)"; };
flux.onopen = () => { lignes = []; attente = []; $("liste").replaceChildren(); };

$("rafraichir").onclick = () => listePorts($("port").value);
$("ouvrir").onclick = () => poste("/port", ouvert ? {action: "fermer"} : {action: "ouvrir", port: $("port").value, debit: +$("debit").value});
// ---------------------------------------------------------------- emulation des esclaves
let emulation = [];
$("boutonEmul").onclick = () => { $("panneauEmul").classList.toggle("cache"); dessineEmulation(true); };
function editeur(e, a) {
  const opts = (liste, v) => liste.map(o => `<option${o === v ? " selected" : ""}>${o}</option>`).join("");
  const att = `data-id="${e.id}" data-reg="${a.registre}" data-champ="${a.champ}"`;
  if (a.champ === "power" || a.champ === "etat") return `<select ${att}>${opts(["ON", "OFF"], a.valeur)}</select>`
    + (a.champ === "etat" ? ` <span class="gris">SwitchMode ${a.switchMode}</span>` : "");
  if (a.champ === "sortie") return `<select ${att}>${opts(["open", "close"], a.valeur)}</select>`;
  if (a.champ === "valeur") return `<input class="court" style="width:80px" type="number" step="any" value="${a.valeur}" ${att}>`
    + (a.humidite !== undefined ? ` humidite <input class="court" style="width:60px" type="number" step="any" value="${a.humidite}" data-id="${e.id}" data-reg="${a.registre}" data-champ="humidite">` : "");
  if (a.champ === "hsb") return `<span class="gris">teinte ${a.valeur[0]}, saturation ${a.valeur[1]}, luminosite ${a.valeur[2]}</span>`;
  return "-";
}
function dessineEmulation(force) {
  const panneau = $("panneauEmul");
  if (panneau.classList.contains("cache") || (!force && panneau.contains(document.activeElement))) return;
  panneau.innerHTML = emulation.length ? emulation.map(e => `<div class="esc"><label><input type="checkbox" data-actif="${e.id}"${e.actif ? " checked" : ""}>`
    + ` emuler id ${e.id} : ${esc(e.nom)} <span class="gris">(${e.driver === "conn16" ? "carte 16 relais" : "ESP32 Tasmota"})</span></label>`
    + (e.actif && e.appareils.length ? "<table>" + e.appareils.map(a => `<tr><td>${a.registre}</td><td>${esc(a.nom)}</td>`
      + `<td class="gris">${esc(a.famille)}</td><td>${editeur(e, a)}</td></tr>`).join("") + "</table>" : "") + "</div>").join("")
    : "aucun esclave dans le persist du maitre";
}
flux.addEventListener("emulation", e => { emulation = JSON.parse(e.data); dessineEmulation(false); });
$("panneauEmul").addEventListener("change", e => {
  const c = e.target;
  if (c.dataset.actif) return poste("/emulation", {id: +c.dataset.actif, actif: c.checked});
  if (c.dataset.champ) poste("/emulation", {id: +c.dataset.id, registre: +c.dataset.reg, champ: c.dataset.champ, valeur: c.value})
    .then(() => c.blur());
});
// ---------------------------------------------------------------- debit / adresse de la carte relais
$("chercherDebit").onclick = () => { $("resDebit").textContent = "recherche..."; $("corrigerDebit").classList.add("cache"); poste("/debit", {action: "chercher"}); };
$("corrigerDebit").onclick = () => {
  if (!confirm("Ecrire dans la carte 16 relais le debit et l'adresse du persist ?\nLe nouveau debit ne sera effectif qu'apres une coupure d'alimentation de la carte.")) return;
  $("corrigerDebit").classList.add("cache"); $("resDebit").textContent = "correction..."; poste("/debit", {action: "corriger"});
};
flux.addEventListener("debit", e => {
  const d = JSON.parse(e.data), r = d.resultat;
  if (d.erreur) $("resDebit").textContent = `${d.action} : ${d.erreur}`;
  else if (d.action === "corriger") $("resDebit").textContent = "fait : " + d.faits.join(" ; ");
  else if (!r) $("resDebit").textContent = "aucune reponse a aucun debit (cablage, alimentation, ou carte non seule a repondre)";
  else {
    $("resDebit").textContent = `carte trouvee : ${r.debit} bauds, adresse ${r.adresse}`
      + (r.ecarts.length ? ` - ECART avec le persist (${d.cible.debit} bauds, adresse ${d.cible.id}) : ${r.ecarts.join(" ; ")}` : " - conforme au persist");
    $("corrigerDebit").classList.toggle("cache", !r.ecarts.length);
  }
});
$("raz").onclick = () => poste("/raz");
const envoi = (hex, crc) => poste("/envoi", {hex, crc, repete: +$("repete").value || 1, intervalle: +$("intervalle").value || 0.5});
$("lire").onclick = () => envoi([+$("carteId").value, 3, 0, 1, 0, 16].map(h2).join(" "), true);
$("commander").onclick = () => envoi([+$("carteId").value, 6, 0, +$("canal").value, +$("ordre").value, +$("tempo").value].map(h2).join(" "), true);
$("envoyer").onclick = () => envoi($("hex").value, $("crc").checked);
$("hex").onkeydown = e => { if (e.key === "Enter") $("envoyer").click(); };
$("filtreId").onchange = () => { majStats(); redessine(); };
document.querySelectorAll(".nat").forEach(c => c.onchange = redessine);
$("filtre").oninput = redessine;
$("pause").onclick = () => {
  enPause = !enPause; $("pause").textContent = enPause ? "Reprendre" : "Pause"; $("pause").classList.toggle("actif", enPause);
  if (!enPause) { attente.forEach(ajoute); attente = []; }
};
$("effacer").onclick = () => { lignes = []; attente = []; redessine(); };
$("export").onclick = () => {
  const texte = lignes.filter(visible).map(l => `${l.t} ${l.sens.padEnd(4)} ${l.hex.padEnd(40)} ${l.crc ? "CRC OK" : "CRC KO"} `
    + (l.norme ? `${l.norme} | ${l.metier}` : l.texte)
    + (l.lat !== null ? ` (${l.lat} ms)` : "")).join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([texte + "\n"], {type: "text/plain"}));
  a.download = "modbus_" + new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-") + ".log"; a.click();
};
// ---------------------------------------------------------------- onglet Aide
const onglet = bus => {
  $("vueBus").classList.toggle("cache", !bus); $("vueAide").classList.toggle("cache", bus);
  $("ongletBus").classList.toggle("choisi", bus); $("ongletAide").classList.toggle("choisi", !bus);
  if (!bus && !$("tableCarte").childElementCount) chargeCarte();
};
$("ongletBus").onclick = () => onglet(true);
$("ongletAide").onclick = () => onglet(false);
function crc16(b) { let c = 0xFFFF; for (const o of b) { c ^= o; for (let i = 0; i < 8; i++) c = (c & 1) ? (c >> 1) ^ 0xA001 : c >> 1; } return c; }
const trame = b => { const c = crc16(b); return [...b, c & 255, c >> 8].map(h2).join(" "); };
const exemple = (b, req) => `<code class="ex" data-hex="${trame(b)}" data-req="${req ? trame(req) : ""}">${trame(b)}</code>`;
async function decodeManuel() {
  const r = await fetch("/decode", {method: "POST", headers: {"X-Sniffeur": "1", "Content-Type": "application/json"},
    body: JSON.stringify({hex: $("decHex").value, requete: $("decReq").value, crc: $("decCrc").checked})});
  if (!r.ok) { $("decResultat").textContent = await r.text(); return; }
  $("decResultat").replaceChildren(detail(await r.json()));
}
$("decoder").onclick = decodeManuel;
$("decHex").onkeydown = e => { if (e.key === "Enter") decodeManuel(); };
document.addEventListener("click", e => {
  const x = e.target.closest(".ex");
  if (!x) return;
  $("decHex").value = x.dataset.hex; $("decReq").value = x.dataset.req || ""; $("decCrc").checked = false;
  // aussi dans le champ d'envoi (onglet Bus), sans son CRC que l'envoi recalcule : rien ne part sans Envoyer
  if (!x.dataset.hex.startsWith("ModbusPushUDP")) { $("hex").value = x.dataset.hex.split(" ").slice(0, -2).join(" "); $("crc").checked = true; }
  decodeManuel(); $("titreDecodeur").scrollIntoView({behavior: "smooth"});
});
// Exemples par appareil, aux regles des drivers (aide, sections 3 et 4)
function exemplesAppareil(e, a) {
  const id = e.id, r = a.registre, hi = r >> 8, lo = r & 255;
  if (e.driver === "conn16") {
    const on = a.type === 256 ? 1 : 2;                 // Relais_i : ON = Open (sortie basse)
    return [exemple([id, 3, 0, 1, 0, 16]), `ON ${exemple([id, 6, hi, lo, on, 0])}<br>OFF ${exemple([id, 6, hi, lo, 3 - on, 0])}`];
  }
  if (["interrupteurs", "boutons", "capteurs"].includes(a.famille)) return [exemple([id, 2, hi, lo, 0, 1]), "-"];
  if (a.famille === "relais" && (a.type === 224 || a.type === 256)) {
    const on = a.type === 256 ? 1 : 2;                 // octet fort 02 = Power ON ; le maitre envoie ON = 01 pour un Relais_i
    return [exemple([id, 1, hi, lo, 0, 1]), `ON ${exemple([id, 6, hi, lo, on, 0])}<br>OFF ${exemple([id, 6, hi, lo, 3 - on, 0])}`];
  }
  if (a.type === 1376) return ["-", exemple([id, 16, hi, lo, 0, 3, 6, 0, 120, 0, 100, 0, 50])];
  if (["analogiques", "compteurs", "thermometres"].includes(a.famille)) return [exemple([id, 4, hi, lo, 0, a.type === 1216 ? 4 : 2]), "-"];
  return ["-", "-"];
}
async function chargeCarte() {
  try {
    const c = await (await fetch("/carte")).json();
    $("sourceCarte").textContent = `source : ${c.persist} - ${c.esclaves.length} esclave(s). Cliquer un exemple pour le decoder.`;
    const lignes = ["<tr><th>Adresse</th><th>Esclave</th><th>Appareil</th><th>Famille / type</th><th>Registre</th><th>Lecture</th><th>Commande</th></tr>"];
    for (const e of c.esclaves) for (const a of e.appareils) {
      const [lecture, commande] = exemplesAppareil(e, a);
      lignes.push(`<tr><td>${e.id}</td><td>${esc(e.nom)}<br><span class="gris">${e.driver === "conn16" ? "carte 16 relais" : "ESP32 Tasmota"}</span></td>`
        + `<td>${esc(a.nom)}<br><span class="gris">${esc(a.cle)}${a.activation !== "ON" ? " (inactif)" : ""}</span></td>`
        + `<td>${esc(a.famille)}<br><span class="gris">${a.type} ${esc(c.types[(a.type >> 5) << 5] || "")}</span></td>`
        + `<td>${a.registre}<br><span class="gris">0x${a.registre.toString(16).toUpperCase().padStart(4, "0")}</span></td><td>${lecture}</td><td>${commande}</td></tr>`);
    }
    $("tableCarte").innerHTML = lignes.join("");
  } catch (e) { $("sourceCarte").textContent = "carte indisponible : " + e; }
}
listePorts();
</script></body></html>
"""
PAGE = PAGE.replace("<!--AIDE-->", sniffeur_modbus_aide.AIDE)
