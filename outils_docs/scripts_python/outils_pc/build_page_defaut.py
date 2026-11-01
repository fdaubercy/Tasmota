"""Onglet « Envs par défaut » de la page Build et televersement (plan default-envs-page, modele B retenu le 2026-11-01,
maquette outils_docs/default_envs/) : CSS, HTML et JS inseres dans build_page.PAGE a la place des marques /*CSS_DEFAUT*/,
<!--VUE_DEFAUT--> et /*JS_DEFAUT*/.

Une colonne par puce, puis « Modifications en attente » : le futur platformio_override.ini entier, lignes changees
surlignees, recalcule a chaque case par POST /defaut/diff (build_defaut.prepare, rien n'est ecrit). « Enregistrer » =
POST /defaut/ecrire avec l'empreinte du dernier apercu ; le bouton reste grise tant que cet apercu n'est pas arrive.
« Cocher ces envs dans l'onglet Build » remplace la selection de cet onglet, sans toucher aux actions. Tout texte venu
du serveur passe par textContent (fonction h de build_page).
"""

CSS = r"""
  .d-colonnes{display:grid;grid-template-columns:repeat(auto-fit,minmax(205px,1fr));gap:10px;align-items:start;margin-bottom:10px}
  .d-groupe{background:var(--carte);border:1px solid var(--bord);border-radius:8px;overflow:hidden}
  .d-groupe > .titre{padding:9px 12px;font-weight:600;display:flex;justify-content:space-between;gap:8px}
  .d-env{display:flex;align-items:flex-start;gap:7px;padding:7px 9px;border-top:1px solid var(--bord);cursor:pointer}
  .d-env:hover{background:var(--survol)}
  .d-env.coche{background:var(--bleu-fond)}
  .d-env input{width:16px;height:16px;margin:0;flex:none}
  .d-env .nom{display:block;font:11.5px ui-monospace,Consolas,monospace;overflow-wrap:anywhere}
  .d-marque{display:inline-block;margin-top:3px;font-size:11px;border:1px solid var(--orange);color:var(--orange);border-radius:10px;padding:0 7px}
  .d-marque.r{border-color:var(--rouge);color:var(--rouge)}
  .d-barre{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
  .d-gros{font-size:26px;font-weight:700;color:var(--bleu)}
  .d-messages div{padding:6px 10px;border-radius:6px;margin-bottom:6px;font-size:13px}
  .d-messages .r{background:var(--rouge-fond);color:var(--rouge)}.d-messages .o{background:var(--orange-fond);color:var(--orange)}
  .d-messages .v{color:var(--vert);padding:2px 0}
  .d-apercu{max-height:420px;overflow:auto;border:1px solid var(--bord);border-radius:6px;background:var(--fond);font:12px/1.5 ui-monospace,Consolas,monospace}
  .d-apercu:focus-visible{outline:2px solid var(--bleu)}
  .d-l{display:flex;white-space:pre;min-height:1.5em;width:max-content;min-width:100%}
  .d-l i{flex:none;width:3.5em;padding-right:8px;text-align:right;font-style:normal;color:var(--discret);user-select:none}
  .d-l.modif{background:var(--bleu-fond);box-shadow:inset 3px 0 0 var(--bleu);font-weight:600}
  .d-l.ajout{background:var(--orange-fond);box-shadow:inset 3px 0 0 var(--orange);font-weight:600}
"""

HTML = r"""
  <div id="vue-defaut" role="tabpanel" aria-labelledby="onglet-defaut" hidden>
    <div id="d-colonnes" class="d-colonnes"><div class="vide">Lecture de default_envs…</div></div>
    <div class="carte d-barre">
      <span><b id="d-total" class="d-gros">0</b> <span id="d-total-texte">env compilé par</span> <code>pio run</code></span>
      <button id="d-enregistrer" class="btn p" type="button" disabled>Enregistrer</button>
      <button id="d-reporter" class="btn" type="button">Cocher ces envs dans l'onglet Build</button>
    </div>
    <div id="d-messages" class="d-messages" aria-live="polite"></div>
    <div class="carte">
      <h2>Modifications en attente</h2>
      <p id="d-resume" class="discret" style="margin:0 0 6px"></p>
      <div id="d-apercu" class="d-apercu" tabindex="0" role="region" aria-label="Futur fichier platformio_override.ini"></div>
    </div>
  </div>
"""

JS = r"""
// ---------- onglet « Envs par défaut » (build_page_defaut.py) ----------
var D = {coches: {}, apercu: null, numero: 0};

function dListe() { return Object.keys(D.coches).filter(function (n) { return D.coches[n]; }); }

function dMessages(liste) {
  var zone = $("d-messages");
  zone.textContent = "";
  liste.forEach(function (m) { zone.appendChild(h("div", {"class": m[0], texte: m[1]})); });
}

function dColonnes(groupes) {
  var zone = $("d-colonnes");
  zone.textContent = "";
  groupes.forEach(function (g) {
    var compte = h("span", {"class": "compte"});
    var bloc = h("div", {"class": "d-groupe"}, h("div", {"class": "titre"}, g.titre, compte));
    function maj() {
      compte.textContent = g.envs.filter(function (e) { return D.coches[e.nom]; }).length + " / " + g.envs.length;
    }
    g.envs.forEach(function (e) {
      var c = h("input", {type: "checkbox", "data-env": e.nom});
      c.checked = !!D.coches[e.nom];
      var ligne = h("label", {"class": "d-env" + (c.checked ? " coche" : "")}, c,
                    h("span", {}, h("span", {"class": "nom", texte: e.nom}),
                      e.inconnu ? h("span", {"class": "d-marque r", texte: "env inconnu"}) :
                      e.absent ? h("span", {"class": "d-marque", texte: "absent du bloc"}) : null));
      c.onchange = function () {
        D.coches[e.nom] = c.checked;
        ligne.classList.toggle("coche", c.checked);
        maj();
        dCalcule();
      };
      bloc.appendChild(ligne);
    });
    maj();
    zone.appendChild(bloc);
  });
}

function dTotal() {
  var n = dListe().length;
  $("d-total").textContent = String(n);
  $("d-total-texte").textContent = n > 1 ? "envs compilés par" : "env compilé par";
}

function dApercu(d) {
  D.apercu = d;
  var zone = $("d-apercu");
  zone.textContent = "";
  var premiere = null, changees = 0;
  d.apercu.forEach(function (l, i) {
    var ligne = h("div", {"class": "d-l" + (l.m ? " " + l.m : "")}, h("i", {texte: String(i + 1)}), l.t.replace(/[\r\n]+$/, "") || " ");
    if (l.m) { changees++; premiere = premiere || ligne; }
    if (i === d.debut && !premiere) premiere = ligne;
    zone.appendChild(ligne);
  });
  $("d-resume").textContent = d.fichier + (d.inchange ? " : aucune modification, le fichier est affiché tel qu'il est."
    : " tel qu'il sera enregistré : " + changees + (changees > 1 ? " lignes changées, surlignées." : " ligne changée, surlignée."));
  if (premiere) zone.scrollTop = premiere.offsetTop - zone.offsetTop - 40;
  dMessages(d.erreurs.map(function (t) { return ["r", "Refusé : " + t]; })
    .concat(d.avertissements.map(function (t) { return ["o", "Attention : " + t]; })));
  $("d-enregistrer").disabled = d.inchange || d.erreurs.length > 0;
}

async function dCalcule() {
  var numero = ++D.numero;
  $("d-enregistrer").disabled = true;
  dTotal();
  var r = await appel("/defaut/diff", {coches: dListe()});
  if (numero !== D.numero) return;                       // une case plus recente a relance le calcul
  if (!r.ok || !r.donnees) { dMessages([["r", "Aperçu impossible : " + (r.texte || "HTTP " + r.statut)]]); return; }
  dApercu(r.donnees);
}

async function dCharge() {
  var numero = ++D.numero;
  var r = await appel("/defaut");
  if (numero !== D.numero) return;
  if (!r.ok || !r.donnees) { dMessages([["r", "Lecture impossible : " + (r.texte || "HTTP " + r.statut)]]); return; }
  D.coches = {};
  r.donnees.actifs.forEach(function (n) { D.coches[n] = true; });
  dColonnes(r.donnees.groupes);
  dTotal();
  dApercu(r.donnees);
}

// Retour sur l'onglet : des cases non enregistrees sont gardees, leur apercu repart du fichier actuel
function dOuvre() { if (D.apercu && !D.apercu.inchange) dCalcule(); else dCharge(); }

$("onglet-defaut").onclick = function () { montreOnglet("defaut"); };

$("d-enregistrer").onclick = async function () {
  var bouton = this;
  bouton.disabled = true;
  var r = await appel("/defaut/ecrire", {coches: dListe(), empreinte: D.apercu.empreinte});
  if (!r.ok) { dMessages([["r", "Non enregistré : " + (r.texte || "HTTP " + r.statut)]]); bouton.disabled = false; return; }
  await dCharge();
  dMessages([["v", "Enregistré. Sauvegarde : " + r.donnees.sauvegarde], ["o", "Attention : le prochain pio run videra .pio/build ; les objets inchangés reviennent du cache .cache"]]);
};

$("d-reporter").onclick = function () {
  envs.forEach(function (e) { if (choix[e.nom]) choix[e.nom].coche = !!D.coches[e.nom]; });
  construitListe({envs: envs, derniers: {}});
  montreOnglet("build");
};

try { if (localStorage.getItem("build-onglet") === "defaut") montreOnglet("defaut"); } catch (e) {}
"""
