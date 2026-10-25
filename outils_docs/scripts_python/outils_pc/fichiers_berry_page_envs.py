"""Panneaux « Renommer cet env » et « Supprimer cet env » de la page Fichiers Berry par env (spec §9, §10).

Inseres dans fichiers_berry_page.PAGE (marques <!--PANNEAUX_ENVS--> et /*JS_ENVS*/) : la page reste sous
500 lignes. Le JS utilise les fonctions de la page ($, h, vide, appel, CHAMPS, chargeEnvs, chargeEtat, envs).
Meme parcours que la creation : « Voir le diff », puis le bouton d'action, grise si refus ou si la saisie
(ou l'env choisi) change apres le diff. Textes inseres par textContent uniquement.
"""

HTML = r"""
  <section class="carte cache" id="panneau-renommage">
    <h2>Renommer l'env <span id="r-env"></span></h2>
    <p class="discret">Section du cenv reprise telle quelle (ports compris), section du .h remplacée avec l'identité
      nouvelle, dossier data/ déplacé, ligne de default_envs renommée. Sauvegarde horodatée ; rien n'est commité.</p>
    <div class="grille">
      <label>Nouveau lieu (minuscules)<input type="text" id="r-lieu"></label>
      <label>Nouveau nom (minuscules, tirets)<input type="text" id="r-nom"></label>
    </div>
    <div class="barre" style="margin:8px 0"><button class="btn" id="r-proposer">Proposer l'identité</button>
      <span id="r-nouvel" class="discret"></span></div>
    <div class="grille" id="r-identite"></div>
    <div class="barre" style="margin-top:8px"><button class="btn p" id="r-prepare">Voir le diff</button>
      <button class="btn" id="r-renommer" disabled>Renommer</button></div>
    <div id="r-retours"></div>
    <pre id="r-diff" class="cache"></pre>
  </section>

  <section class="carte cache" id="panneau-suppression">
    <h2>Supprimer l'env <span id="s-env"></span></h2>
    <p class="discret">Retire sa section du cenv et du .h et sa ligne de default_envs ; son dossier data/ est renommé
      en …-sauvegarde. Sauvegarde horodatée des fichiers ; rien n'est commité.</p>
    <div class="barre"><button class="btn p" id="s-prepare">Voir le diff</button>
      <button class="btn" id="s-supprimer" disabled>Supprimer</button></div>
    <div id="s-retours"></div>
    <pre id="s-diff" class="cache"></pre>
  </section>
"""

JS = r"""
var PANNEAUX = ["panneau-creation", "panneau-renommage", "panneau-suppression"];
var renommageEmpreinte = "", suppressionEmpreinte = "", suppressionEnv = "";

function ouvre(id) {                       // un seul panneau ouvert a la fois ; re-clic = fermer
  var ouvrir = $(id).classList.contains("cache");
  PANNEAUX.forEach(function (p) { $(p).classList.add("cache"); });
  if (ouvrir) $(id).classList.remove("cache");
  return ouvrir;
}
function retours(z, p) {
  p.refus.forEach(function (t) { z.appendChild(h("div", {"class": "avert rouge", texte: t})); });
  p.avertissements.forEach(function (t) { z.appendChild(h("div", {"class": "avert", texte: t})); });
}
function montreDiff(id, texte) { $(id).textContent = texte || ""; $(id).classList.toggle("cache", !texte); }

function renommageCorps() {
  var ident = {};
  CHAMPS.forEach(function (c) { ident[c] = $("r-" + c).value.trim(); });
  return {env: $("env").value, lieu: $("r-lieu").value.trim(), nom: $("r-nom").value.trim(), identite: ident,
          define: $("r-define").value.trim()};
}
async function proposeRenommage() {
  var q = "env=" + encodeURIComponent($("env").value) + "&lieu=" + encodeURIComponent($("r-lieu").value.trim()) +
          "&nom=" + encodeURIComponent($("r-nom").value.trim());
  var r = await appel("/identite?" + q), z = vide($("r-retours"));
  if (!r.ok) { z.appendChild(h("div", {"class": "erreur", texte: r.texte})); return; }
  CHAMPS.forEach(function (c) { $("r-" + c).value = r.donnees.identite[c]; });
  $("r-define").value = r.donnees.define;
  $("r-nouvel").textContent = "nouvel env : " + r.donnees.env;
  $("r-renommer").disabled = true;
}
async function prepareRenommage() {
  var r = await appel("/renommage/prepare", renommageCorps()), z = vide($("r-retours"));
  $("r-renommer").disabled = true;
  if (!r.ok) { z.appendChild(h("div", {"class": "erreur", texte: r.texte})); return; }
  renommageEmpreinte = r.donnees.empreinte;
  retours(z, r.donnees);
  montreDiff("r-diff", r.donnees.diff);
  $("r-renommer").disabled = r.donnees.refus.length > 0;
}
async function renommer() {
  var r = await appel("/renommage", Object.assign(renommageCorps(), {empreinte: renommageEmpreinte})), z = vide($("r-retours"));
  if (!r.ok) { z.appendChild(h("div", {"class": "erreur", texte: "Refusé : " + r.texte})); return; }
  $("r-renommer").disabled = true;
  montreDiff("r-diff", "");
  z.appendChild(h("div", {"class": "ok", id: "r-ok", texte: "Renommé en " + r.donnees.env + " (dossier " + r.donnees.dossier +
    "). Sauvegarde : " + r.donnees.sauvegarde}));
  retours(z, {refus: [], avertissements: r.donnees.avertissements});
  await chargeEnvs();
  $("env").value = r.donnees.env;
  $("r-env").textContent = r.donnees.env;
  await chargeEtat();
}

async function prepareSuppression() {
  var env = $("env").value, r = await appel("/suppression/prepare", {env: env}), z = vide($("s-retours"));
  $("s-supprimer").disabled = true;
  if (!r.ok) { z.appendChild(h("div", {"class": "erreur", texte: r.texte})); return; }
  suppressionEmpreinte = r.donnees.empreinte;
  suppressionEnv = env;
  retours(z, r.donnees);
  montreDiff("s-diff", r.donnees.diff);
  $("s-supprimer").textContent = "Supprimer " + env;
  $("s-supprimer").disabled = r.donnees.refus.length > 0;
}
async function supprimer() {
  var env = suppressionEnv, r = await appel("/suppression", {env: env, empreinte: suppressionEmpreinte});
  var z = vide($("s-retours"));
  if (!r.ok) { z.appendChild(h("div", {"class": "erreur", texte: "Refusé : " + r.texte})); return; }
  $("s-supprimer").disabled = true;
  montreDiff("s-diff", "");
  z.appendChild(h("div", {"class": "ok", id: "s-ok", texte: "Supprimé : " + env +
    (r.donnees.dossier_sauvegarde ? " ; dossier renommé en " + r.donnees.dossier_sauvegarde : "") +
    ". Sauvegarde : " + r.donnees.sauvegarde}));
  retours(z, {refus: [], avertissements: r.donnees.avertissements});
  await chargeEnvs();
  await chargeEtat();
}

(function () {
  var g = $("r-identite");
  CHAMPS.concat(["define"]).forEach(function (c) {
    g.appendChild(h("label", {}, c === "define" ? "-D (define du firmware)" : c, h("input", {type: "text", id: "r-" + c})));
  });
})();
$("renommer").onclick = function () {
  var e = envs.filter(function (x) { return x.nom === $("env").value; })[0], z = vide($("r-retours"));
  if (!ouvre("panneau-renommage")) return;
  $("r-env").textContent = $("env").value;
  if (e && e.famille !== "cartes") z.appendChild(h("div", {"class": "avert rouge", texte: "Seules les cartes se renomment (une base a des cartes qui en dépendent)."}));
};
$("supprimer").onclick = function () {
  if (!ouvre("panneau-suppression")) return;
  $("s-env").textContent = $("env").value;
  vide($("s-retours")); montreDiff("s-diff", ""); $("s-supprimer").disabled = true; $("s-supprimer").textContent = "Supprimer";
};
$("r-proposer").onclick = proposeRenommage;
$("r-prepare").onclick = prepareRenommage;
$("r-renommer").onclick = renommer;
$("s-prepare").onclick = prepareSuppression;
$("s-supprimer").onclick = supprimer;
["input", "change"].forEach(function (t) {      // saisie changee apres « Voir le diff » : refaire le diff
  $("panneau-renommage").addEventListener(t, function () { $("r-renommer").disabled = true; });
});
$("env").addEventListener("change", function () {   // le diff vu valait pour l'env d'avant
  $("r-renommer").disabled = true; $("s-supprimer").disabled = true;
  $("r-env").textContent = $("s-env").textContent = $("env").value;
  vide($("r-retours")); vide($("s-retours")); montreDiff("r-diff", ""); montreDiff("s-diff", "");
});
"""
