"""Script du mode modification et de la suppression verifiee de la page « Assistant persist » (A10, spec §10.4).

Insere dans assistant_persist_page_js.JS a la place de /*ENV*/ (meme portee : il se sert de E, api, el, vide, liste...).
  - liste « Env » + « Charger » : GET /env?nom= remplit toutes les etapes ; lieu, nom, puce et base sont grises (renommer =
    page 7800) ; `modif` = l'env charge, "" en mode creation ;
  - lieu + nom (+ puce) d'une carte du parc en mode creation : libelle « Modifier l'environnement » et bandeau ;
  - suppression : POST /suppression/prepare, panneau (elements, refus, avertissements, diff), case « J'ai verifie »
    qui seule active « Supprimer » ; apres succes, retour au mode creation et parc.cartes relu par GET /parc.
Aucun mot de passe n'est lu ni envoye par la page : le serveur les recopie lui-meme. Textes par textContent uniquement.
"""

JS = r"""
// ---- Mode modification (A10) ----
var FIGES = ["f-lieu", "f-nom", "f-puce", "f-base"], prepSuppr = null;
function prefixe() { return {ESP32: "tasmota32", ESP32S3: "tasmota32s3", ESP32P4: "tasmota32p4"}[E.puce]; }
function envSaisi() { return E.lieu && E.nom ? prefixe() + "-" + E.lieu + "-" + E.nom : ""; }
function carteExiste() {
  var n = envSaisi();
  return !modif && !!parc && !!n && parc.cartes.some(function (c) { return c.env === n; });
}
function majLibelle() {
  var existe = carteExiste(), mode = !!modif || existe;
  $("creer").textContent = mode ? "Modifier l'environnement" : "Créer l'env";
  $("creer-aide").textContent = modif ? "Voir le diff d'abord : seul l'écart est appliqué aux fichiers de l'env."
    : "Voir le diff d'abord ; toute saisie ensuite le grise.";
  $("bandeau-existe").classList.toggle("cache", !existe);
  $("charger-existe").textContent = existe ? "Charger ses réglages (" + envSaisi() + ")" : "";
  $("supprimer-env").classList.toggle("cache", !modif);
}
function dessineListeEnv() {
  var choisi = $("f-env").value;
  remplit($("f-env"), [["", "(nouvel env)"]].concat(parc.cartes.map(function (c) { return [c.env, c.env]; })), modif || choisi);
}
function griseFiges(g) { FIGES.forEach(function (i) { $(i).disabled = g; }); }
function quitteModif() {
  modif = ""; manuel = {}; griseFiges(false); ferme_suppr(); invalideDiff();
  if (parc) { dessineListeEnv(); majLibelle(); }
}
// Reponses relues de la carte -> E, puis tout le formulaire. garder : ne pas effacer le resultat d'une creation.
async function chargeEnv(env, garder) {
  var zone = vide($("retours-env")), r = await api("/env?nom=" + encodeURIComponent(env));
  if (!r.ok || !r.donnees) { liste(zone, [r.texte], "avert rouge"); return false; }
  var d = r.donnees.reponses;
  Object.keys(E).forEach(function (k) { if (d[k] !== undefined) E[k] = copie(d[k]); });
  E.define = d.define || ""; E.elements = copie(d.elements || {}); E.elements_groupe = copie(d.elements_groupe || {});
  if (!E.metiers.length) E.metiers = [""];
  IDENT.forEach(function (k) { manuel[k] = true; });
  modif = env; invalideDiff(); ferme_suppr();
  $("f-puce").value = E.puce; remplitBases();
  document.querySelectorAll("[data-k]").forEach(function (c) {
    if (c.type === "checkbox") c.checked = !!E[c.getAttribute("data-k")]; else c.value = E[c.getAttribute("data-k")];
  });
  $("role-" + E.role).checked = true; $("f-id").value = E.id;
  griseFiges(true); dessineMetiers(); dessineElements(); dessineListeEnv(); reagit();
  if (!garder) vide($("resultat"));
  liste(zone, r.donnees.avertissements, "avert");
  if (r.donnees.reglages_propres) liste(zone, [r.donnees.reglages_propres + " réglage(s) propre(s) à cette carte, conservé(s) tels quels."], "discret");
  return true;
}
async function relitParc() {
  var r = await api("/parc");
  if (r.ok && r.donnees) { parc.cartes = r.donnees.cartes; parc.ids_pris = r.donnees.ids_pris; parc.maitres = r.donnees.maitres; }
}

// ---- Modification : /modification/prepare puis /modification ----
function modifie_env() {
  return api("/modification", {env: modif, reponses: JSON.parse(signatureDiff), empreinte: diff.empreinte});
}
async function modifieEnv() {
  $("creer").disabled = true;
  var r = await modifie_env(), zone = vide($("resultat"));
  if (!r.ok || !r.donnees) {
    if (r.statut === 409) invalideDiff();
    zone.appendChild(el("div", {"class": "avert rouge", id: "modification-erreur"}, r.texte)); majCreer(); return;
  }
  var c = r.donnees;
  zone.appendChild(el("p", {"class": "ok", id: "modification-ok"}, "Env " + c.env + " modifié (sauvegarde : " + c.sauvegarde + ")."));
  liste(zone, c.avertissements || [], "avert"); zone.appendChild(el("pre", {id: "modification-diff"}, c.diff));
  await chargeEnv(c.env, true);
}

// ---- Suppression verifiee ----
function ferme_suppr() { prepSuppr = null; $("panneau-suppr").classList.add("cache"); }
function majSuppr() {
  $("suppr-confirme").disabled = !(prepSuppr && prepSuppr.empreinte && prepSuppr.refus.length === 0 && $("suppr-verifie").checked);
}
async function prepareSuppr() {
  var zone = vide($("suppr-retours")), ul = vide($("suppr-elements"));
  $("suppr-verifie").checked = false; prepSuppr = null; $("suppr-diff").textContent = "";
  $("panneau-suppr").classList.remove("cache");
  var r = await api("/suppression/prepare", {env: modif});
  if (!r.ok || !r.donnees) { liste(zone, [r.texte], "avert rouge"); majSuppr(); return; }
  prepSuppr = r.donnees;
  r.donnees.elements.forEach(function (t) { ul.appendChild(el("li", {}, t)); });
  liste(zone, r.donnees.refus, "avert rouge"); liste(zone, r.donnees.avertissements, "avert");
  $("suppr-diff").textContent = r.donnees.diff; majSuppr();
}
async function confirmeSuppr() {
  $("suppr-confirme").disabled = true;
  var env = modif, r = await api("/suppression", {env: env, empreinte: prepSuppr.empreinte}), zone = vide($("suppr-retours"));
  if (!r.ok || !r.donnees) {                                    // 409 : fichiers changes depuis le diff -> nouveau diff exige
    prepSuppr = null; zone.appendChild(el("div", {"class": "avert rouge", id: "suppression-erreur"}, r.texte)); majSuppr(); return;
  }
  var s = r.donnees;
  quitteModif(); await relitParc(); dessineListeEnv(); majLibelle();
  var res = vide($("resultat"));
  res.appendChild(el("p", {"class": "ok", id: "suppression-ok"}, "Env " + env + " supprimé" +
    (s.dossier_sauvegarde ? " (dossier renommé en " + s.dossier_sauvegarde + ")" : "") + " ; sauvegarde : " + s.sauvegarde + "."));
  liste(res, s.avertissements || [], "avert");
}

$("charger").onclick = function () { if ($("f-env").value) chargeEnv($("f-env").value, false); };
$("f-env").onchange = function () { if (!$("f-env").value && modif) quitteModif(); };
$("charger-existe").onclick = function () { var n = envSaisi(); $("f-env").value = n; chargeEnv(n, false); };
$("supprimer-env").onclick = prepareSuppr;
$("suppr-verifie").onchange = majSuppr;
$("suppr-confirme").onclick = confirmeSuppr;
$("suppr-annule").onclick = ferme_suppr;
"""
