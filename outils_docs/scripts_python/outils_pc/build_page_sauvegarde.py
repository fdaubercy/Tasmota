"""Onglet « Sauvegarde configuration » de la page Build et televersement (plan sauvegarde-config-cartes, modele B retenu
le 2026-11-03, maquette outils_docs/sauvegarde_config/modele-B.png) : CSS, HTML et JS inseres dans build_page.PAGE a la
place des marques /*CSS_SAUVEGARDE*/, <!--VUE_SAUVEGARDE--> et /*JS_SAUVEGARDE*/.

Carte choisie en haut (adresse reprise de l'onglet Build), historique a gauche, parametres de la sauvegarde choisie a
droite, replies par theme (groupes de decode-config). Une valeur changee est surlignee ; « Enregistrer la copie » cree
une nouvelle sauvegarde (POST /sauvegarde/copier), l'originale n'est jamais reecrite. « Restaurer la selection » montre
d'abord les ecarts avec la carte (POST /sauvegarde/comparer) puis les fait confirmer. Serveur : build_sauvegarde.py.
Tout texte venu du serveur passe par textContent (fonction h de build_page).
"""

CSS = r"""
  .s-haut{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
  .s-haut .droite{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap}
  .btn.o{color:var(--orange);border-color:var(--orange)}
  .s-corps{display:grid;grid-template-columns:minmax(260px,1fr) 2fr;gap:10px;align-items:start}
  @media (max-width:820px){.s-corps{grid-template-columns:1fr}}
  .s-hist{width:100%;border-collapse:collapse;font-size:13px}
  .s-hist th{text-align:left;font-weight:600;color:var(--doux);padding:5px 6px}
  .s-hist td{padding:7px 6px;border-top:1px solid var(--bord)}
  .s-hist tr.l{cursor:pointer}.s-hist tr.l:hover{background:var(--survol)}
  .s-hist tr.choisie{background:var(--bleu-fond);box-shadow:inset 3px 0 0 var(--bleu)}
  .s-comparer{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:10px}
  .s-tete{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px}
  .s-tete h2{margin:0}.s-tete input{margin-left:auto;min-width:160px}
  .s-theme{border:1px solid var(--bord);border-radius:6px;margin-bottom:6px;overflow:hidden}
  .s-theme > summary{padding:8px 10px;cursor:pointer;display:flex;justify-content:space-between;gap:8px}
  .s-theme > summary .n{color:var(--discret);font-size:12px}.s-theme > summary .n.m{color:var(--orange)}
  .s-p{display:grid;grid-template-columns:minmax(140px,1fr) 2fr;gap:8px;align-items:center;padding:4px 10px;border-top:1px solid var(--bord)}
  .s-p code{font-size:12px;overflow-wrap:anywhere}
  .s-val{display:flex;gap:6px;align-items:flex-start}
  .s-val textarea{flex:1;min-width:0;box-sizing:border-box;font:12px/1.45 ui-monospace,Consolas,monospace;resize:vertical;
    overflow:hidden;padding:3px 5px;white-space:pre-wrap;overflow-wrap:anywhere}
  .s-json{flex:none;padding:1px 6px;border-radius:4px;border:1px solid var(--btn-bord);background:var(--btn);color:var(--doux);
    font:11px ui-monospace,Consolas,monospace;cursor:pointer}
  .s-json[aria-pressed="true"]{color:var(--bleu);border-color:var(--bleu);background:var(--bleu-fond)}
  .s-p.modif{background:var(--orange-fond)}.s-p.ecart code{color:var(--bleu);font-weight:600}
  .s-p.faux textarea{border-color:var(--rouge)}
  .s-messages div{padding:6px 10px;border-radius:6px;margin-bottom:6px;font-size:13px}
  .s-messages .r{background:var(--rouge-fond);color:var(--rouge)}.s-messages .o{background:var(--orange-fond);color:var(--orange)}
  .s-messages .v{color:var(--vert);padding:2px 0}
"""

HTML = r"""
  <div id="vue-sauvegarde" role="tabpanel" aria-labelledby="onglet-sauvegarde" hidden>
    <div class="carte s-haut">
      <label>Carte <select id="s-env" aria-label="Carte sauvegardée"></select></label>
      <span id="s-adresse" class="discret"></span>
      <span class="droite">
        <button id="s-prendre" class="btn p" type="button">Sauvegarder maintenant</button>
        <button id="s-restaurer" class="btn o" type="button" disabled>Restaurer la sélection</button>
      </span>
    </div>
    <div id="s-messages" class="s-messages" aria-live="polite"></div>
    <div class="s-corps">
      <div class="carte">
        <h2>Sauvegardes de cette carte</h2>
        <table class="s-hist"><thead><tr><th>Date</th><th>Version</th><th>Origine</th></tr></thead>
          <tbody id="s-liste"><tr><td colspan="3" class="vide">Aucune carte choisie.</td></tr></tbody></table>
        <div class="s-comparer">
          <label>Comparer <select id="s-autre" aria-label="Comparer la sélection à"></select></label>
          <button id="s-comparer" class="btn" type="button" disabled>Comparer</button>
        </div>
        <p id="s-ecarts" class="discret" style="margin:8px 0 0"></p>
        <p class="discret" style="margin:10px 0 0">Une sauvegarde est le fichier <code>/dl</code> de la carte : ses Settings
          (Wi-Fi, MQTT, minuteries, gabarit, règles…) et ses fichiers <code>.drvset*</code> (calibrage, compteurs). Rangée
          dans <code>outils_docs/sauvegardes_cartes/</code>, ignorée par git (mots de passe en clair). Au démarrage, le persist
          et l'<code>autoexec.bat</code> reposent leurs réglages : ils l'emportent sur une valeur restaurée.</p>
      </div>
      <div class="carte">
        <div class="s-tete"><h2>Paramètres de la sauvegarde</h2>
          <button id="s-copier" class="btn p" type="button" hidden>Enregistrer la copie</button>
          <input id="s-filtre" type="search" placeholder="Filtrer…" aria-label="Filtrer les paramètres"></div>
        <div id="s-params"><div class="vide">Choisir une sauvegarde.</div></div>
      </div>
    </div>
  </div>
"""

JS = r"""
// ---------- onglet « Sauvegarde configuration » (build_page_sauvegarde.py) ----------
var S = {env: "", fichier: "", liste: [], params: null, modifs: {}, ecarts: {}, numero: 0};
var S_THEMES = {Wifi: "Réseau et Wi-Fi", MQTT: "MQTT", Power: "Relais et alimentation", Sensor: "Mesure et capteurs",
  Timer: "Minuteries", Rules: "Règles", Control: "Commandes et boutons", Management: "Gestion", System: "Système",
  Light: "Lumière", Serial: "Série", Display: "Affichage", Shutter: "Volets", Internal: "Interne", Rf: "RF",
  Hdmi: "HDMI", Divers: "Divers"};

function sMessages(liste) {
  var zone = $("s-messages");
  zone.textContent = "";
  liste.forEach(function (m) { zone.appendChild(h("div", {"class": m[0], texte: m[1]})); });
}
function sAdresse() { var c = choix[S.env]; return (c && c.ip) || (parNom[S.env] && parNom[S.env].ip) || ""; }
function sTexte(v) { return typeof v === "string" ? v : JSON.stringify(v); }
// Hauteur du champ = son contenu : une valeur plus longue que la zone passe sur plusieurs lignes
function sAjuste(champ) { champ.style.height = "auto"; champ.style.height = champ.scrollHeight + 2 + "px"; }

function sEnvs() {
  var sel = $("s-env");
  if (!envs.length || sel.options.length) return;
  var cartes = envs.filter(function (e) { return e.famille === "cartes"; });
  cartes.forEach(function (e) { sel.appendChild(h("option", {value: e.nom, texte: e.nom})); });
  var coche = cartes.filter(function (e) { return choix[e.nom] && choix[e.nom].coche; })[0] || cartes[0];
  if (coche) { sel.value = coche.nom; sCharge(coche.nom); }
}
$("s-env").onchange = function () { sCharge($("s-env").value); };

async function sCharge(env, garder) {
  S.env = env;
  var adresse = sAdresse();
  $("s-adresse").textContent = adresse ? adresse : "adresse inconnue : la saisir sur la ligne de l'env, onglet Build (méthode OTA)";
  var r = await appel("/sauvegardes?env=" + encodeURIComponent(env));
  if (!r.ok || !r.donnees) { sMessages([["r", "Lecture impossible : " + (r.texte || "HTTP " + r.statut)]]); return; }
  if (!r.donnees.decode_config) sMessages([["o", "decode-config absent : lancer outils_pc/decode_config.py (paramètres illisibles, sauvegarde et restauration possibles)"]]);
  S.liste = r.donnees.sauvegardes;
  if (!garder || !S.liste.some(function (f) { return f.fichier === S.fichier; })) S.fichier = S.liste.length ? S.liste[0].fichier : "";
  sListe();
  if (S.fichier) sChoisit(S.fichier); else { S.params = null; sParams(); }
}

function sListe() {
  var corps = $("s-liste"), autre = $("s-autre");
  corps.textContent = "";
  autre.textContent = "";
  autre.appendChild(h("option", {value: "", texte: "à la carte en ligne"}));
  if (!S.liste.length) corps.appendChild(h("tr", {}, h("td", {colspan: "3", "class": "vide", texte: "Aucune sauvegarde : « Sauvegarder maintenant »."})));
  S.liste.forEach(function (f) {
    var tr = h("tr", {"class": "l" + (f.fichier === S.fichier ? " choisie" : ""), title: f.fichier},
               h("td", {texte: f.date || f.fichier}), h("td", {texte: f.version}), h("td", {texte: f.origine}));
    tr.onclick = function () { sChoisit(f.fichier); };
    corps.appendChild(tr);
    autre.appendChild(h("option", {value: f.fichier, texte: (f.date || f.fichier) + " · " + f.origine}));
  });
  $("s-restaurer").disabled = !S.fichier;
  $("s-comparer").disabled = !S.fichier;
}

async function sChoisit(fichier) {
  var numero = ++S.numero;
  S.fichier = fichier; S.modifs = {}; S.ecarts = {};
  $("s-ecarts").textContent = "";
  sListe();
  $("s-params").textContent = "";
  $("s-params").appendChild(h("div", {"class": "vide", texte: "Lecture de la sauvegarde (decode-config, quelques secondes)…"}));
  var r = await appel("/sauvegarde?env=" + encodeURIComponent(S.env) + "&fichier=" + encodeURIComponent(fichier), undefined, 60000);
  if (numero !== S.numero) return;
  S.params = r.ok ? r.donnees : null;
  if (!r.ok) sMessages([["r", "Lecture impossible : " + (r.texte || "HTTP " + r.statut)]]);
  sParams();
}

function sCopierEtat() {
  var n = Object.keys(S.modifs).length;
  $("s-copier").hidden = !n;
  $("s-copier").textContent = "Enregistrer la copie (" + n + (n > 1 ? " modifiés)" : " modifié)");
  document.querySelectorAll("#s-params .s-theme").forEach(function (t) {
    var m = t.querySelectorAll(".s-p.modif").length, n2 = t.querySelector("summary .n");
    n2.textContent = m ? m + (m > 1 ? " modifiés" : " modifié") : n2.dataset.total;
    n2.classList.toggle("m", m > 0);
  });
}

function sParams() {
  var zone = $("s-params"), p = S.params, filtre = $("s-filtre").value.trim().toLowerCase();
  zone.textContent = "";
  if (!p) { zone.appendChild(h("div", {"class": "vide", texte: "Choisir une sauvegarde."})); return; }
  if (p.message) zone.appendChild(h("div", {"class": "vide", texte: p.message}));
  Object.keys(p.groupes).sort(function (a, b) { return (S_THEMES[a] || a).localeCompare(S_THEMES[b] || b); }).forEach(function (g) {
    var cles = Object.keys(p.groupes[g]).filter(function (k) {
      return !filtre || k.toLowerCase().indexOf(filtre) >= 0 || sTexte(p.groupes[g][k]).toLowerCase().indexOf(filtre) >= 0;
    });
    if (!cles.length) return;
    var n = h("span", {"class": "n", texte: String(cles.length)});
    n.dataset.total = String(cles.length);
    var bloc = h("details", {"class": "s-theme"}, h("summary", {}, S_THEMES[g] || g, n));
    bloc.ontoggle = function () { if (bloc.open) bloc.querySelectorAll("textarea").forEach(sAjuste); };
    if (filtre || cles.some(function (k) { return k in S.modifs || k in S.ecarts; })) bloc.open = true;
    cles.forEach(function (k) {
      var origine = p.groupes[g][k], champ = h("textarea", {rows: "1", "aria-label": k, spellcheck: "false"});
      champ.value = k in S.modifs ? sTexte(S.modifs[k]) : sTexte(origine);
      champ.disabled = !p.editable;
      var valeur = h("span", {"class": "s-val"}, champ);
      if (origine !== null && typeof origine === "object") {   // liste ou objet : vue formatee a la demande
        var bouton = h("button", {type: "button", "class": "s-json", "aria-pressed": "false", texte: "{ }",
                                  title: "Afficher formaté", "aria-label": "Afficher " + k + " formaté"});
        bouton.onclick = function () {
          var formate = bouton.getAttribute("aria-pressed") !== "true";
          try { champ.value = JSON.stringify(JSON.parse(champ.value), null, formate ? 2 : 0); } catch (e) { return; }
          bouton.setAttribute("aria-pressed", String(formate));
          bouton.title = formate ? "Afficher sur une ligne" : "Afficher formaté";
          sAjuste(champ);
        };
        valeur.appendChild(bouton);
      }
      var ligne = h("div", {"class": "s-p" + (k in S.modifs ? " modif" : "") + (k in S.ecarts ? " ecart" : "")},
                    h("code", {texte: k}), valeur);
      if (k in S.ecarts) ligne.title = "Autre valeur : " + sTexte(S.ecarts[k]);
      champ.oninput = function () {
        var v = champ.value, ok = true;
        if (typeof origine !== "string") { try { v = JSON.parse(v); } catch (e) { ok = false; } }
        ligne.classList.toggle("faux", !ok);
        if (ok && sTexte(v) !== sTexte(origine)) S.modifs[k] = v; else delete S.modifs[k];
        ligne.classList.toggle("modif", k in S.modifs);
        sAjuste(champ);
        sCopierEtat();
      };
      bloc.appendChild(ligne);
    });
    zone.appendChild(bloc);
    if (bloc.open) bloc.querySelectorAll("textarea").forEach(sAjuste);
  });
  var fichiers = Object.keys(p.fichiers || {});
  if (fichiers.length) zone.appendChild(h("p", {"class": "discret", texte: "Fichiers des pilotes (non modifiables ici) : "
    + fichiers.map(function (f) { return f + " (" + p.fichiers[f] + " o)"; }).join(", ")}));
  sCopierEtat();
}
$("s-filtre").oninput = sParams;

$("s-prendre").onclick = async function () {
  var adresse = sAdresse(), bouton = this;
  if (!adresse) { sMessages([["r", "Adresse de la carte inconnue : la saisir sur la ligne de l'env, onglet Build (méthode OTA)."]]); return; }
  bouton.disabled = true;
  sMessages([["v", "Sauvegarde de " + S.env + " (" + adresse + ")…"]]);
  var r = await appel("/sauvegarde/prendre", {env: S.env, adresse: adresse}, 90000);
  bouton.disabled = false;
  if (!r.ok) { sMessages([["r", "Non sauvegardée : " + (r.texte || "HTTP " + r.statut)]]); return; }
  S.fichier = r.donnees.fichier;
  sMessages([["v", "Sauvegardée : " + r.donnees.fichier + " (" + r.donnees.taille + " o, " + r.donnees.version + ")"]]);
  sCharge(S.env, true);
};

$("s-copier").onclick = async function () {
  var bouton = this;
  bouton.disabled = true;
  var r = await appel("/sauvegarde/copier", {env: S.env, fichier: S.fichier, modifs: S.modifs}, 120000);
  bouton.disabled = false;
  if (!r.ok) { sMessages([["r", "Copie refusée : " + (r.texte || "HTTP " + r.statut)]]); return; }
  sMessages([["v", "Copie enregistrée : " + r.donnees.fichier + " (l'originale est inchangée)"]]);
  S.fichier = r.donnees.fichier;
  sCharge(S.env, true);
};

function sEcartsTexte(ecarts) {
  return ecarts.length ? ecarts.length + (ecarts.length > 1 ? " écarts : " : " écart : ") + ecarts.map(function (e) { return e.cle; }).join(", ")
    : "Aucun écart.";
}

$("s-comparer").onclick = async function () {
  var autre = $("s-autre").value, adresse = sAdresse(), bouton = this;
  if (!autre && !adresse) { sMessages([["r", "Adresse de la carte inconnue : la saisir dans l'onglet Build."]]); return; }
  bouton.disabled = true;
  $("s-ecarts").textContent = "Comparaison…";
  var r = await appel("/sauvegarde/comparer", {env: S.env, fichier: S.fichier, autre: autre, adresse: adresse}, 120000);
  bouton.disabled = false;
  if (!r.ok) { $("s-ecarts").textContent = ""; sMessages([["r", "Comparaison impossible : " + (r.texte || "HTTP " + r.statut)]]); return; }
  S.ecarts = {};
  r.donnees.ecarts.forEach(function (e) { S.ecarts[e.cle] = e.b; });
  $("s-ecarts").textContent = sEcartsTexte(r.donnees.ecarts) + (autre ? "" : " (avec la carte)");
  sParams();
};

$("s-restaurer").onclick = async function () {
  var adresse = sAdresse(), bouton = this;
  if (!adresse) { sMessages([["r", "Adresse de la carte inconnue : la saisir sur la ligne de l'env, onglet Build (méthode OTA)."]]); return; }
  bouton.disabled = true;
  sMessages([["v", "Lecture de la carte pour les écarts…"]]);
  var c = await appel("/sauvegarde/comparer", {env: S.env, fichier: S.fichier, adresse: adresse}, 120000);
  if (!c.ok) { bouton.disabled = false; sMessages([["r", "Écarts illisibles : " + (c.texte || "HTTP " + c.statut)]]); return; }
  var e = c.donnees.ecarts, liste = e.slice(0, 25).map(function (x) { return "- " + x.cle + " : " + sTexte(x.b) + " → " + sTexte(x.a); });
  if (e.length > 25) liste.push("… et " + (e.length - 25) + " autres");
  var autreCarte = e.filter(function (x) { return x.cle === "hostname"; })[0];
  if (autreCarte && !confirm("ATTENTION : la carte jointe à " + adresse + " s'appelle « " + sTexte(autreCarte.b)
      + " », la sauvegarde « " + sTexte(autreCarte.a) + " ».\n\nEst-ce bien la carte à restaurer ?")) { bouton.disabled = false; sMessages([]); return; }
  if (!confirm("Restaurer " + S.fichier + " sur " + S.env + " (" + adresse + ") ?\n\nUne sauvegarde de la carte est prise d'abord, "
      + "puis la carte redémarre : l'état des relais peut changer (vu sur le différentiel : relais revenu ON).\n" + sEcartsTexte(e) + "\n" + liste.join("\n"))) { bouton.disabled = false; sMessages([]); return; }
  sMessages([["v", "Restauration en cours (sauvegarde d'abord, puis envoi et redémarrage de la carte)…"]]);
  var r = await appel("/sauvegarde/restaurer", {env: S.env, fichier: S.fichier, adresse: adresse, jeton: c.donnees.jeton}, 300000);
  bouton.disabled = false;
  if (!r.ok) { sMessages([["r", "Restauration échouée : " + (r.texte || "HTTP " + r.statut)]]); sCharge(S.env, true); return; }
  sMessages([["v", "Restaurée. Sauvegarde d'avant : " + r.donnees.avant.fichier],
             [r.donnees.ecarts.length ? "o" : "v", "Relu sur la carte après redémarrage : " + sEcartsTexte(r.donnees.ecarts)]]);
  sCharge(S.env, true);
};

$("onglet-sauvegarde").onclick = function () { montreOnglet("sauvegarde"); };
try { if (localStorage.getItem("build-onglet") === "sauvegarde") montreOnglet("sauvegarde"); } catch (e) {}
"""
