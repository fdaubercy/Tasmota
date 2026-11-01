"""Onglet « Mémoire et partitions » de la page Build et televersement (plan temps-compilation A8, modele B retenu le
2026-11-01, maquette outils_docs/partitions/) : CSS, HTML et JS inseres dans build_page.PAGE a la place des marques
/*CSS_MEMOIRE*/, <!--VUE_MEMOIRE--> et /*JS_MEMOIRE*/.

Env par defaut : le premier coche de l'onglet Build (le choisir ici ne change pas les cases). Occupation lue par
GET /memoire?env= (derniere analyse enregistree), « Analyser » = POST /memoire/analyser (relit le dernier build, aucun
pio). Jauges orange a 85 %, rouge a 95 %. Table : un curseur et un champ par partition, par pas de 64 Ko ; le FS
(sinon app0) compense pour que la flash reste repartie ; nvs, otadata et app0 non supprimables. « Voir le diff » =
POST /partitions/diff, « Écrire » = POST /partitions/ecrire apres confirmation (build_partitions.py valide tout cote
serveur ; la page ne fait que proposer). « Partir d'une table existante » (GET /partitions/tables) regle les curseurs
sur une table de partitions/ ; identique a l'ecriture, l'env pointe vers ce fichier. « Importer un CSV » passe par
POST /partitions/importer, « Exporter » par le texte du diff, « Ajouter » insere avant le FS. Tout texte venu du serveur passe par textContent (fonction h de build_page).
"""

CSS = r"""
  .m-barre{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
  .m-barre select,#m-table,#m-ajout-type{font:inherit;color:inherit;background:var(--btn);border:1px solid var(--btn-bord);border-radius:6px;padding:5px 8px}
  .m-grille{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:10px}
  .m-zone .tete{display:flex;justify-content:space-between;gap:6px;font-size:13px}
  .m-jauge{height:9px;background:var(--piste);border-radius:5px;overflow:hidden;margin:4px 0 2px}
  .m-jauge i{display:block;height:100%;background:var(--vert)}
  .m-jauge i.o{background:var(--orange)}.m-jauge i.r{background:var(--rouge)}
  .m-ruban{position:relative;height:40px;background:var(--piste);border-radius:6px;overflow:hidden;margin:8px 0}
  .m-ruban .seg{position:absolute;top:0;bottom:0;color:#fff;font-size:12px;display:flex;align-items:center;justify-content:center;white-space:nowrap;overflow:hidden;border-right:1px solid rgba(255,255,255,.7)}
  .m-ruban .plein{position:absolute;left:0;top:0;bottom:0;background:rgba(0,0,0,.24)}
  .m-ruban .seg span{position:relative}
  .m-table{border-collapse:collapse;width:100%;min-width:640px}
  .m-table th{font-size:12px;color:var(--doux);text-align:left;font-weight:600;padding:5px 6px;border-bottom:1px solid var(--bord)}
  .m-table td{padding:6px;border-bottom:1px solid var(--bord);vertical-align:middle}
  .m-table tr.suppr td{opacity:.5;text-decoration:line-through}.m-table tr.suppr td:first-child{opacity:1;text-decoration:none}
  .m-table input[type=range]{width:100%;accent-color:var(--bleu)}
  .m-num{width:92px;text-align:right;font:inherit;color:inherit;background:var(--btn);border:1px solid var(--btn-bord);border-radius:6px;padding:4px 6px}
  .m-role{display:block;font-size:11px;line-height:1.3;color:var(--doux);margin-top:2px;max-width:260px}
  .m-pastille{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
  .m-defile{overflow-x:auto}
  .m-deux{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
  .m-messages div{padding:6px 10px;border-radius:6px;margin-bottom:6px}
  .m-messages .r{background:var(--rouge-fond);color:var(--rouge)}.m-messages .o{background:var(--orange-fond);color:var(--orange)}
  .m-messages .v{color:var(--vert);padding:2px 0}
  .m-pre{margin:0;background:var(--console);color:var(--console-texte);border-radius:6px;padding:10px;overflow:auto;max-height:340px;font:12.5px/1.45 Consolas,monospace;white-space:pre}
  .m-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}
  @media (max-width:720px){.m-deux{grid-template-columns:1fr}}
"""

HTML = r"""
  <div id="vue-memoire" role="tabpanel" aria-labelledby="onglet-memoire" hidden>
    <div class="carte m-barre">
      <label>Environnement <select id="m-env" aria-label="Environnement analysé"></select></label>
      <span id="m-env-note" class="discret"></span>
      <span style="flex:1"></span>
      <span id="m-date" class="discret"></span>
      <button id="m-analyser" class="btn p" type="button" title="Relit le dernier build de l'env (aucune compilation)">Analyser</button>
    </div>
    <div class="carte"><h2>Occupation, selon les capacités paramétrées</h2>
      <div id="m-zones" class="m-grille"></div><p id="m-notes" class="discret" style="margin:6px 0 0"></p></div>
    <div class="carte" style="margin-top:10px"><h2>Régler chaque partition</h2>
      <div class="m-actions" style="margin:0 0 6px">
        <label>Partir d'une table existante <select id="m-table" aria-label="Table existante"></select></label>
        <button id="m-importer" class="btn" type="button">Importer un CSV</button>
        <input id="m-fichier" type="file" accept=".csv,text/csv" hidden>
        <button id="m-exporter" class="btn" type="button">Exporter en CSV</button>
        <span style="flex:1"></span>
        <label>Ajouter <select id="m-ajout-type" aria-label="Sous-type de la partition ajoutée">
          <option value="coredump">coredump</option><option value="ota_1">ota_1</option>
          <option value="fat">fat</option><option value="littlefs">littlefs</option></select></label>
        <input id="m-ajout-nom" class="m-num" style="text-align:left" maxlength="16" placeholder="nom" aria-label="Nom de la partition ajoutée">
        <button id="m-ajouter" class="btn" type="button">Ajouter la partition</button>
      </div>
      <div id="m-ruban" class="m-ruban"></div>
      <div class="m-defile"><table class="m-table"><thead><tr><th>Suppr.</th><th>Partition</th><th>Adresse</th>
        <th style="width:40%">Taille</th><th>Ko</th><th>Occupé</th></tr></thead><tbody id="m-parts"></tbody></table></div>
    </div>
    <div class="m-deux">
      <div class="carte"><h2>Contrôles</h2><div id="m-messages" class="m-messages"></div>
        <label class="discret" style="display:block;margin-top:8px">Nom du fichier de la table (facultatif)
          <input id="m-nom" maxlength="64" placeholder="env_&lt;env&gt;.csv si vide" aria-label="Nom du fichier de la table"
            style="font:inherit;color:inherit;background:var(--btn);border:1px solid var(--btn-bord);border-radius:6px;padding:5px 8px;width:100%;box-sizing:border-box;margin-top:4px"></label>
        <div class="m-actions">
          <button id="m-diff" class="btn" type="button">Voir le diff</button>
          <button id="m-ecrire" class="btn p" type="button" disabled title="Voir le diff d'abord">Écrire la table de l'env</button>
          <button id="m-annuler" class="btn" type="button">Revenir à la table actuelle</button>
        </div>
        <p class="discret" style="margin:8px 0 0">Effet au prochain « Effacer puis téléverser » par câble : une OTA ne change
          jamais la table, elle reste bloquée pour cet env jusque-là.</p></div>
      <div class="carte"><h2 id="m-titre-diff">Diff</h2><pre id="m-diff-texte" class="m-pre">« Voir le diff » montre ce qui serait écrit.</pre></div>
    </div>
  </div>
"""

JS = r"""
// ---------- onglet « Mémoire et partitions » (A8, build_page_memoire.py) ----------
var M = {env: "", analyse: null, parts: [], flash: 0, empreinte: "", lecture: 0};
var M_COUL = {nvs: "#8b95a5", otadata: "#8b95a5", safeboot: "#b07ad9", app0: "#2563eb", spiffs: "#0d9488"};
var M_RAISON = {nvs: "position fixe 0x9000 : réglages Tasmota et Wi-Fi", otadata: "position fixe 0xE000 : boot_app0.bin y est écrit",
                app0: "le firmware : indispensable"};
// Utilite de chaque partition, sous son nom (par nom, sinon par sous-type)
var M_ROLE = {nvs: "Réglages Tasmota et Wi-Fi, écrits par la carte elle-même.",
              otadata: "Dit au démarrage quelle application lancer : safeboot ou app0.",
              safeboot: "Firmware minimal de secours : il reçoit l'OTA et écrit le nouveau firmware dans app0.",
              app0: "Le firmware Tasmota de la carte, Berry solidifié compris.",
              spiffs: "Système de fichiers LittleFS : autoexec, persist, scripts Berry, pages web.",
              ota_1: "Second emplacement de firmware.", coredump: "Vidage de la mémoire après un plantage.",
              fat: "Système de fichiers FAT.", littlefs: "Système de fichiers LittleFS."};

function mKo(o) { return Math.round(o / 1024); }
function mFmt(k) { return k >= 1024 ? (k / 1024).toFixed(k % 1024 ? 2 : 0).replace(".", ",") + " Mo" : String(k).replace(".", ",") + " Ko"; }
function mHex(k) { return "0x" + (k * 1024).toString(16).toUpperCase(); }
function mVivantes() { return M.parts.filter(function (p) { return !p.suppr; }); }
function mPart(n) { return M.parts.filter(function (p) { return p.nom === n; })[0]; }
function mFixe(p) { return p.nom === "nvs" || p.nom === "otadata"; }
function mMinimum(p) { return p.u == null ? 64 : Math.ceil(p.u / 64) * 64; }
function mOffsets() {
  var o = 36, r = {};
  mVivantes().forEach(function (p) { if (!mFixe(p) && o % 64) o = Math.ceil(o / 64) * 64; r[p.nom] = o; o += p.k; });
  r._fin = o;
  return r;
}
// Le FS compense, sinon app0 : la flash reste entierement repartie
function mCompensateur(p) {
  var fs = mPart("spiffs"), app = mPart("app0");
  if (p !== fs && fs && !fs.suppr) return fs;
  if (p !== app && app && !app.suppr) return app;
  return null;
}
function mBornes(p) {
  var c = mCompensateur(p);
  return [mMinimum(p), c ? p.k + c.k - mMinimum(c) : p.k + Math.max(0, M.flash - mOffsets()._fin)];
}
function mRegle(p, v) {
  var b = mBornes(p), c = mCompensateur(p);
  v = Math.max(b[0], Math.min(b[1], Math.round(v / 64) * 64));
  if (c) c.k -= v - p.k;
  p.k = v;
  M.empreinte = "";
  mRendu();
}
function mJauge(u, t) {
  var pc = t ? 100 * u / t : 0;
  return h("div", {"class": "m-jauge"}, h("i", {"class": pc >= 95 ? "r" : pc >= 85 ? "o" : "", style: "width:" + Math.min(100, pc) + "%"}));
}
function mPourcent(u, t) { return t ? (100 * u / t).toFixed(1).replace(".", ",") + " %" : "—"; }
function mZone(nom, couleur, u, t, estime) {
  var a = estime ? "≈ " : "";
  return h("div", {"class": "m-zone"},
    h("div", {"class": "tete"}, h("b", {}, h("span", {"class": "m-pastille", style: "background:" + couleur}), nom),
      h("span", {texte: u == null ? "non mesuré" : a + mPourcent(u, t)})),
    mJauge(u || 0, t),
    h("span", {"class": "discret", texte: (u == null ? "— " : a + mFmt(+(u / 1024).toFixed(1))) + " sur " + mFmt(+(t / 1024).toFixed(1))
      + (u == null ? "" : " · libre " + mFmt(+(Math.max(0, t - u) / 1024).toFixed(1)))}));
}

function mEnvs() {
  var sel = $("m-env");
  if (!envs.length || sel.options.length) return;
  var candidats = envs.filter(function (e) { return e.famille === "cartes" || e.famille === "bases"; });
  candidats.forEach(function (e) { sel.appendChild(h("option", {value: e.nom, texte: e.nom})); });
  var coche = candidats.filter(function (e) { return choix[e.nom] && choix[e.nom].coche; })[0]
    || candidats.filter(function (e) { return e.famille === "cartes"; })[0] || candidats[0];
  if (!coche) return;
  sel.value = coche.nom;
  $("m-env-note").textContent = choix[coche.nom] && choix[coche.nom].coche ? "repris de l'onglet Build (env coché)" : "";
  mCharge(coche.nom);
}
$("m-env").onchange = function () {
  $("m-env-note").textContent = "choisi ici (ne change pas les cases de l'onglet Build)";
  mCharge($("m-env").value);
};

async function mCharge(env, analyser) {
  var n = ++M.lecture;
  M.env = env;
  $("m-date").textContent = analyser ? "Analyse…" : "Lecture…";
  var r = analyser ? await appel("/memoire/analyser", {env: env}) : await appel("/memoire?env=" + encodeURIComponent(env));
  if (n !== M.lecture) return;                           // un autre env choisi entre-temps
  if (!r.ok) { $("m-date").textContent = ""; $("m-notes").textContent = "Analyse indisponible : " + (r.texte || "HTTP " + r.statut); return; }
  if (!r.donnees && !analyser) return mCharge(env, true);   // jamais analyse : une premiere lecture du dernier build
  M.analyse = r.donnees;
  await mTables(env);
  mDepuisAnalyse();
}
function mDepuisAnalyse() {
  var a = M.analyse;
  M.flash = a.flash ? mKo(a.flash) : 0;
  M.parts = a.partitions.map(function (p) {
    return {nom: p.nom, type: p.type, sous_type: p.sous_type, k: mKo(p.taille), u: p.utilise == null ? null : p.utilise / 1024,
            estime: p.estime, suppr: false};
  });
  M.empreinte = "";
  $("m-date").textContent = a.date_build ? "build du " + dateLisible(a.date_build) + " · analyse du " + dateLisible(a.date) : "analyse du " + dateLisible(a.date);
  $("m-notes").textContent = (a.notes || []).join(" ; ") || "Taille du FS estimée d'après les fichiers de l'image ; le reste vient du journal de compilation.";
  $("m-titre-diff").textContent = "Diff";
  $("m-diff-texte").textContent = "« Voir le diff » montre ce qui serait écrit.";
  $("m-table").value = "";
  $("m-nom").value = "";
  M.doublon = false;
  mRendu();
}
async function mTables(env) {
  var r = await appel("/partitions/tables?env=" + encodeURIComponent(env));
  if (env !== M.env) return;
  var sel = $("m-table");
  sel.textContent = "";
  sel.appendChild(h("option", {value: "", texte: "Table actuelle de l'env"}));
  M.tables = r.ok && r.donnees ? r.donnees : [];
  M.tables.forEach(function (t) {
    var o = h("option", {value: t.csv, texte: t.csv.replace("partitions/", "") + (t.erreurs.length ? " (ne convient pas)" : "")});
    o.disabled = t.erreurs.length > 0;
    if (o.disabled) o.title = t.erreurs.join(" ; ");
    sel.appendChild(o);
  });
}
$("m-table").onchange = function () {
  var t = (M.tables || []).filter(function (x) { return x.csv === $("m-table").value; })[0];
  if (!t) { if (M.analyse) mDepuisAnalyse(); return; }
  mPose(t.partitions);
};
// Regle les curseurs sur une table (occupation reprise de l'analyse, par nom)
function mPose(parts) {
  var avant = M.parts;
  M.parts = parts.map(function (p) {
    var a = avant.filter(function (x) { return x.nom === p.nom; })[0] || {};
    return {nom: p.nom, type: p.type, sous_type: p.sous_type, k: mKo(p.taille), u: a.u == null ? null : a.u, estime: a.estime, suppr: false};
  });
  M.empreinte = "";
  mRendu();
}
async function mImporte(texte) {
  var r = await appel("/partitions/importer", {env: M.env, texte: texte});
  if (!r.ok || !r.donnees) { mMessages([["r", "Import impossible : " + (r.texte || "HTTP " + r.statut)]]); return; }
  if (r.donnees.erreurs.length) { mMessages(r.donnees.erreurs.map(function (e) { return ["r", "CSV refusé : " + e]; })); return; }
  mPose(r.donnees.partitions);
}
$("m-importer").onclick = function () { $("m-fichier").value = ""; $("m-fichier").click(); };
$("m-fichier").onchange = async function () {
  var f = $("m-fichier").files[0];
  if (f) mImporte(await f.text());
};
function mTelecharge(nom, texte) {
  var a = h("a", {href: URL.createObjectURL(new Blob([texte], {type: "text/csv"}))});
  a.download = nom;
  a.click();
  URL.revokeObjectURL(a.href);
}
$("m-exporter").onclick = async function () {
  if (!M.env) return;
  var r = await appel("/partitions/diff", {env: M.env, partitions: mDemande(), nom: $("m-nom").value});
  if (!r.ok || !r.donnees) { mMessages([["r", "Export impossible : " + (r.texte || "HTTP " + r.statut)]]); return; }
  if (r.donnees.erreurs.length) { mMessages(r.donnees.erreurs.map(function (e) { return ["r", "Export refusé : " + e]; })); return; }
  mTelecharge(r.donnees.csv.replace("partitions/", ""), r.donnees.texte_csv);
};
$("m-ajouter").onclick = function () {
  var nom = $("m-ajout-nom").value.trim(), st = $("m-ajout-type").value;
  if (!/^[A-Za-z0-9_]{1,16}$/.test(nom) || mPart(nom)) { mMessages([["r", "Nom invalide ou déjà pris : lettres, chiffres, _ (16 au plus)."]]); return; }
  var p = {nom: nom, type: st === "ota_1" ? "app" : "data", sous_type: st, k: 64, u: null, estime: false, suppr: false};
  var c = mCompensateur(p), fs = M.parts.indexOf(mPart("spiffs"));
  if (c) c.k -= p.k;
  M.parts.splice(fs < 0 ? M.parts.length : fs, 0, p);
  $("m-ajout-nom").value = "";
  M.empreinte = "";
  mRendu();
};

function mRendu() {
  var zones = $("m-zones");
  zones.textContent = "";
  M.parts.forEach(function (p) {
    if (!mFixe(p) && !p.suppr) zones.appendChild(mZone("Flash " + p.nom, M_COUL[p.nom] || "#d97706", p.u == null ? null : p.u * 1024, p.k * 1024, p.estime));
  });
  ((M.analyse && M.analyse.ram) || []).forEach(function (z) { zones.appendChild(mZone(z.zone, "#8b95a5", z.utilise, z.total)); });
  var o = mOffsets(), f = M.flash || o._fin, ruban = $("m-ruban");
  ruban.textContent = "";
  mVivantes().forEach(function (p) {
    var w = p.k / f * 100;
    ruban.appendChild(h("div", {"class": "seg", style: "left:" + (o[p.nom] / f * 100) + "%;width:" + w + "%;background:" + (M_COUL[p.nom] || "#d97706")},
      h("div", {"class": "plein", style: "width:" + (p.u ? Math.min(100, p.u / p.k * 100) : 0) + "%"}),
      h("span", {texte: w > 7 ? p.nom + " " + mFmt(p.k) : ""})));
  });
  var corps = $("m-parts");
  corps.textContent = "";
  M.parts.forEach(function (p) {
    var interdit = mFixe(p) || p.nom === "app0", b = mBornes(p);
    var caseS = h("input", {type: "checkbox", "aria-label": "Supprimer " + p.nom});
    caseS.checked = p.suppr;
    caseS.disabled = interdit;
    if (interdit) caseS.title = M_RAISON[p.nom];
    caseS.onchange = function () {
      p.suppr = caseS.checked;
      var c = mCompensateur(p);
      if (c) c.k += p.suppr ? p.k : -p.k;
      M.empreinte = "";
      mRendu();
    };
    var curseur = null, champ = null;
    if (!mFixe(p)) {
      curseur = h("input", {type: "range", "aria-label": "Taille de " + p.nom, min: b[0], max: b[1], step: 64});
      curseur.value = p.k;
      curseur.disabled = p.suppr;
      curseur.oninput = function () { mRegle(p, +curseur.value); var q = document.querySelector("[aria-label='Taille de " + p.nom + "']"); if (q) q.focus(); };
      champ = h("input", {"class": "m-num", type: "number", step: 64, "aria-label": "Taille de " + p.nom + " en Ko"});
      champ.value = p.k;
      champ.disabled = p.suppr;
      champ.onchange = function () { mRegle(p, +champ.value); };
    }
    corps.appendChild(h("tr", {"class": p.suppr ? "suppr" : ""},
      h("td", {}, caseS),
      h("td", {}, h("span", {"class": "m-pastille", style: "background:" + (M_COUL[p.nom] || "#d97706")}), h("b", {texte: p.nom}),
        h("span", {"class": "m-role", texte: M_ROLE[p.nom] || M_ROLE[p.sous_type] || ""})),
      h("td", {"class": "mono", texte: p.suppr ? "—" : mHex(o[p.nom])}),
      h("td", {}, curseur || h("span", {"class": "discret", texte: M_RAISON[p.nom] || ""})),
      h("td", {}, champ || String(p.k)),
      h("td", {texte: p.u == null ? "—" : (p.estime ? "≈ " : "") + mFmt(Math.round(p.u))})));
  });
  mControles();
}
// Avis de la page (le serveur valide tout) : ce qui change pour la carte
function mControles() {
  var m = [], s = mPart("safeboot"), fs = mPart("spiffs"), a = mPart("app0"), o = mOffsets();
  if (s && s.suppr) m.push(["r", "Sans safeboot : plus d'OTA du firmware, ni par Tasmota ni par la page. Seul le câble reste."]);
  if (fs && fs.suppr) m.push(["r", "Sans FS : ni autoexec, ni persist, ni Berry de la carte. Le module démarre sans son programme."]);
  if (a && a.u != null && (a.k - a.u) / a.k < .05) m.push(["o", "Marge de app0 sous 5 % : le prochain firmware peut ne plus tenir."]);
  if (M.flash && o._fin !== M.flash) m.push(["r", "La table finit en " + mHex(o._fin) + ", la flash fait " + mFmt(M.flash) + "."]);
  if (!M.flash) m.push(["o", "Taille de la flash inconnue : board_upload.flash_size absent de l'env."]);
  if (!m.length) m.push(["v", "Table cohérente : tout tient dans " + mFmt(M.flash) + ", pas de 64 Ko respecté."]);
  mMessages(m);
  $("m-ecrire").disabled = !M.empreinte;
}
function mMessages(m) {
  var zone = $("m-messages");
  zone.textContent = "";
  m.forEach(function (x) { zone.appendChild(h("div", {"class": x[0], texte: x[1]})); });
}
function mDemande() {
  return mVivantes().map(function (p) { return {nom: p.nom, type: p.type, sous_type: p.sous_type, taille: p.k * 1024}; });
}

$("m-analyser").onclick = function () { if (M.env) mCharge(M.env, true); };
$("m-annuler").onclick = function () { if (M.analyse) mDepuisAnalyse(); };
$("m-nom").oninput = function () { M.empreinte = ""; M.doublon = false; $("m-ecrire").disabled = true; };
$("m-diff").onclick = function () { mDiff(false); };
async function mDiff(doublon) {
  if (!M.env) return;
  var r = await appel("/partitions/diff", {env: M.env, partitions: mDemande(), nom: $("m-nom").value, doublon: doublon});
  if (!r.ok || !r.donnees) { mMessages([["r", "Diff impossible : " + (r.texte || "HTTP " + r.statut)]]); return; }
  var d = r.donnees;
  M.doublon = doublon;
  if (d.proposition && d.proposition !== $("m-table").value && !confirm("Une table identique existe déjà : " + d.proposition
      + "\n\nOK : utiliser ce fichier, sans en créer un autre.\nAnnuler : créer quand même " + d.cible + ".")) { mDiff(true); return; }
  M.empreinte = d.erreurs.length || d.inchange ? "" : d.empreinte;
  M.avertissements = d.avertissements;
  mMessages(d.inchange && !d.erreurs.length ? [["v", "C'est déjà la table de cet env : rien à écrire."]]
    : d.erreurs.map(function (e) { return ["r", e]; }).concat(d.proposition ? [["v", "Table identique déjà enregistrée : " + d.proposition + ". Aucun fichier créé."]] : [],
      d.avertissements.map(function (e) { return ["o", e]; })));
  $("m-titre-diff").textContent = d.erreurs.length ? "Diff (table refusée)" : "Diff : " + d.csv;
  $("m-diff-texte").textContent = d.diff || "(aucun changement)";
  $("m-ecrire").disabled = !M.empreinte;
}
$("m-ecrire").onclick = async function () {
  if (!M.empreinte || !confirm("Écrire la table de " + M.env + " ?\n\n- " + (M.avertissements || []).join("\n- "))) return;
  var r = await appel("/partitions/ecrire", {env: M.env, partitions: mDemande(), empreinte: M.empreinte, nom: $("m-nom").value, doublon: !!M.doublon});
  M.empreinte = "";
  $("m-ecrire").disabled = true;
  if (!r.ok) { mMessages([["r", "Écriture refusée : " + (r.texte || "HTTP " + r.statut)]]); return; }
  mMessages([["v", "Table écrite : env réglé sur " + r.donnees.csv + " (copie d'origine : " + r.donnees.sauvegarde + "). OTA de l'env bloquée jusqu'au prochain « Effacer puis téléverser »."]]);
};
"""
