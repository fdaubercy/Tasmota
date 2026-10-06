"""Page web du sniffeur ModBus (sniffeur_modbus.py), servie sur http://127.0.0.1:7300.

Routes (sniffeur_modbus.py) :
    GET  /         cette page
    GET  /flux     Server-Sent Events : 'etat', 'stats', l'historique ('trame'), puis le direct ;
                   aussi 'message' (erreur d'envoi) et 'raz'
    GET  /ports    ports serie presents [{port, description, ch343}]
    POST /port     {action: "ouvrir"|"fermer", port, debit}
    POST /envoi    {hex, crc, repete, intervalle}
    POST /emulation {actif, id}          POST /raz   (compteurs et historique)
Les POST exigent l'en-tete X-Sniffeur: 1 (protection contre une page tierce visant 127.0.0.1).
Fiche 'trame' : {t, dt (ms depuis la precedente), sens (bus|pc|emul|--), hex, crc, nature
(requete|reponse|exception|ko|timeout|?), id, fc, texte, lat (ms, reponse appariee)}.
"""

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
 .s-bus{background:#264f78} .s-pc{background:#6a3d9a} .s-emul{background:#7a5c00} .s---{background:#5a1d1d}
 .hx{color:#ce9178} .ok{color:#6a9955} .ko{color:#f14c4c} .lat{color:#29b8db}
 .n-reponse .tx{color:#89d185} .n-ko .tx,.n-exception .tx,.n-timeout .tx{color:#f14c4c}
</style></head><body>
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
 <label title="le PC repond comme la carte 16 relais (debrancher la vraie)"><input type="checkbox" id="emul"> emuler la carte relais, id</label>
 <input id="emulId" class="court" type="number" min="1" max="247" value="1">
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
 <input id="filtre" placeholder="filtre texte ou hexa">
 <button id="pause">Pause</button><button id="effacer">Effacer</button><button id="export">Exporter</button>
 <span class="gris" id="compte"></span>
</div>
<div id="stats"></div>
<div id="liste"></div>
<script>
const $ = id => document.getElementById(id);
const MAX = 20000;
let lignes = [], stats = [], enPause = false, attente = [];
const esc = t => String(t).replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"})[c]);
const h2 = n => (n & 255).toString(16).toUpperCase().padStart(2, "0");
const famille = n => n === "requete" ? "requete" : n === "reponse" ? "reponse" : "erreur";

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
    + `<span class="tx">${esc(l.texte)}</span>` + (l.lat !== null ? ` <span class="lat">(${l.lat} ms)</span>` : "");
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
      + (s.lat !== null ? ` <span class="n">latence ${s.lat} ms (max ${s.lat_max})</span>` : "");
    d.onclick = () => { $("filtreId").value = String(s.id) === $("filtreId").value ? "" : String(s.id); majStats(); redessine(); };
    return d;
  }));
}

let ouvert = false, portActif = "";
const flux = new EventSource("/flux");
flux.addEventListener("etat", e => {
  const s = JSON.parse(e.data);
  ouvert = s.ouvert; if (s.port) portActif = s.port;
  $("etat").textContent = (s.ouvert ? `${s.port} a ${s.debit} bauds` : "port ferme") + ` - ${s.nb} trames, ${s.ko} CRC KO`
    + (s.emulation ? ` - EMULATION id ${s.emulation}` : "") + (s.erreur ? ` - ${s.erreur}` : "");
  $("pastille").style.background = s.ouvert ? "#16825d" : "#a1260d";
  $("ouvrir").textContent = s.ouvert ? "Fermer" : "Ouvrir";
  $("ouvrir").classList.toggle("actif", s.ouvert);
  if (s.ouvert && s.port) { if (![...$("port").options].some(o => o.value === s.port)) $("port").add(new Option(s.port, s.port)); $("port").value = s.port; $("debit").value = String(s.debit); }
  $("emul").checked = !!s.emulation; if (s.emulation) $("emulId").value = s.emulation;
});
flux.addEventListener("stats", e => { stats = JSON.parse(e.data); majStats(); });
flux.addEventListener("trame", e => { const l = JSON.parse(e.data); enPause ? attente.push(l) : ajoute(l); });
flux.addEventListener("message", e => { $("message").textContent = JSON.parse(e.data).texte; });
flux.addEventListener("raz", () => { lignes = []; attente = []; redessine(); });
flux.onerror = () => { $("pastille").style.background = "#808080"; $("etat").textContent = "serveur injoignable (reconnexion...)"; };
flux.onopen = () => { lignes = []; attente = []; $("liste").replaceChildren(); };

$("rafraichir").onclick = () => listePorts($("port").value);
$("ouvrir").onclick = () => poste("/port", ouvert ? {action: "fermer"} : {action: "ouvrir", port: $("port").value, debit: +$("debit").value});
$("emul").onchange = () => poste("/emulation", {actif: $("emul").checked, id: +$("emulId").value});
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
  const texte = lignes.filter(visible).map(l => `${l.t} ${l.sens.padEnd(4)} ${l.hex.padEnd(40)} ${l.crc ? "CRC OK" : "CRC KO"} ${l.texte}`
    + (l.lat !== null ? ` (${l.lat} ms)` : "")).join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([texte + "\n"], {type: "text/plain"}));
  a.download = "modbus_" + new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-") + ".log"; a.click();
};
listePorts();
</script></body></html>
"""
