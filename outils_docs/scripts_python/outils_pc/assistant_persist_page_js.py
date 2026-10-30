"""Script de la page « Assistant persist » (assemble par assistant_persist_page.PAGE).

Etat unique E (les reponses), tout est re-derive de lui :
  - l'apercu (POST /apercu, anti-rebond 300 ms, reponses perimees ignorees) ;
  - les cases de fonctions : dependances cochees d'office et expliquees, cases grisees avec leur raison ;
  - le bandeau du modele (GET /modele/etat) : cles ajoutees d'office a relire, retraits et alignements proposes par le
    bouton « Mettre a jour le modele » (diff, puis validation) ;
  - « Creer l'env » : actif seulement si le dernier « Voir le diff » n'a aucun refus ET si rien n'a ete saisi depuis
    (signature des reponses comparee a celle du diff) ; sinon le serveur repondrait « saisie changee ».
Textes inseres par textContent uniquement.
"""

JS = r"""
"use strict";
var $ = function (id) { return document.getElementById(id); };
var ETAPES = ["Carte", "Réseau", "Fonctions", "Bloc métier", "Vérification"];
var IDENT = ["hostname", "nom_lisible", "nom_template", "client", "ssid_ap", "topic"];
var parc = null, etape = 0, minuteur = null, numero = 0, modif = "";
var diff = null, signatureDiff = null, manuel = {}, propositionModele = null;
var E = {puce: "ESP32S3", base: "", lieu: "", nom: "", ip: "0.0.0.0", heure: "NTP", role: "autonome", maitre: "", id: 0,
  reseau1: "", reseau2: "", blocs: [], metiers: [""], squelettes: true, elements: {},
  hostname: "", nom_lisible: "", nom_template: "", client: "", ssid_ap: "", topic: ""};

function el(tag, attrs, texte) {
  var e = document.createElement(tag);
  Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
  if (texte !== undefined) e.textContent = texte;
  return e;
}
function vide(e) { while (e.firstChild) e.removeChild(e.firstChild); return e; }

// Appel HTTP qui ne leve jamais : {ok, statut, donnees, texte}. Les POST portent X-Assistant-Persist: 1.
async function api(chemin, corps) {
  var opts = {};
  if (corps !== undefined) {
    opts.method = "POST";
    opts.headers = {"X-Assistant-Persist": "1", "Content-Type": "application/json"};
    opts.body = JSON.stringify(corps);
  }
  try {
    var r = await fetch(chemin, opts), texte = await r.text(), donnees = null;
    try { donnees = JSON.parse(texte); } catch (e) { donnees = null; }
    return {ok: r.ok, statut: r.status, donnees: donnees, texte: texte};
  } catch (e) {
    return {ok: false, statut: 0, donnees: null, texte: "outil injoignable : " + e};
  }
}

// ---- Valeurs par defaut de l'identite (miroir de fichiers_berry_creation.identite_par_defaut) ----
function defauts() {
  var l = E.lieu || "lieu", n = E.nom || "nom", projet = n.toUpperCase() + "-" + l.toUpperCase();
  var lisible = n.replace(/-/g, " "); lisible = lisible.charAt(0).toUpperCase() + lisible.slice(1).toLowerCase();
  return {hostname: projet, nom_lisible: lisible, nom_template: lisible, client: projet, ssid_ap: projet + "-GATEWAY",
    topic: l + "/" + n};
}
function majIdentite() {
  var d = defauts();
  IDENT.forEach(function (k) { if (!manuel[k]) { E[k] = d[k]; $("f-" + k).value = d[k]; } });
  var pre = prefixe();
  $("env-propose").textContent = "Env : " + pre + "-" + (E.lieu || "?") + "-" + (E.nom || "?") + " · dossier data/" +
    (E.lieu || "?") + "/" + pre + "-" + (E.nom || "?");
}

// ---- Fonctions : permissions, dependances, raisons ----
function bloc(id) { return parc.blocs.filter(function (b) { return b.id === id; })[0]; }
function permis(id) { var b = bloc(id); return !!b && b.puces.indexOf(E.puce) >= 0; }
function fermeture() {
  var res = [], file = E.blocs.filter(permis);
  if (E.heure === "RTC" && bloc("ds3231") && permis("ds3231")) file.push("ds3231");
  while (file.length) {
    var i = file.shift();
    if (res.indexOf(i) >= 0) continue;
    res.push(i);
    (bloc(i) ? bloc(i).dependances : []).forEach(function (d) { if (permis(d)) file.push(d); });
  }
  return res;
}
function requisPar(id, ferme) {
  var par = ferme.filter(function (x) { return x !== id && bloc(x).dependances.indexOf(id) >= 0; });
  if (id === "ds3231" && E.heure === "RTC") par.push("réglage de l'heure RTC");
  return par;
}
function dessineFonctions() {
  var ferme = fermeture(), cases = vide($("cases")), notes = [];
  parc.blocs.forEach(function (b) {
    var ok = permis(b.id), coche = ferme.indexOf(b.id) >= 0, par = coche ? requisPar(b.id, ferme) : [];
    var l = el("label", {title: b.aide || ""}), c = el("input", {type: "checkbox", id: "bloc-" + b.id, "data-bloc": b.id});
    c.checked = coche; c.disabled = !ok || par.length > 0;
    var raison = "";
    if (!ok) raison = " (non disponible sur " + E.puce + ")";
    else if (par.length) { raison = " (requis par " + par.join(", ") + ")"; if (E.blocs.indexOf(b.id) < 0) notes.push(b.id + " coché d'office : requis par " + par.join(", ")); }
    if (c.disabled) l.className = "grise";
    l.appendChild(c); l.appendChild(document.createTextNode(" " + b.libelle + raison));
    cases.appendChild(l);
  });
  $("note-deps").textContent = notes.join(" · ");
}

// ---- Reseau ----
function remplit(select, valeurs, choisi) {
  vide(select);
  valeurs.forEach(function (v) { var o = el("option", {value: v[0]}, v[1]); if (v[0] === choisi) o.selected = true; select.appendChild(o); });
}
function dessineReseau() {
  var esc = E.role === "esclave";
  $("bloc-esclave").classList.toggle("cache", !esc);
  $("bloc-reseaux").classList.toggle("cache", esc);
  var maitres = parc.maitres.filter(function (m) { return m.env; });
  if (esc && !E.maitre && maitres.length) E.maitre = maitres[0].env;
  remplit($("f-maitre"), maitres.map(function (m) { return [m.env, m.hostname + " (" + m.env + ")"]; }), E.maitre);
  if (esc && !E.id) { E.id = parc.id_libre; $("f-id").value = E.id; }
  var pris = parc.ids_pris[String(E.id)], ind = $("id-indice");
  ind.className = "indice" + (pris ? " av" : "");
  ind.textContent = pris ? "⚠ id déjà pris par " + pris.join(", ") + " (carte remplaçante ?)"
    : "✔ libre — pris : " + Object.keys(parc.ids_pris).join(", ");
  var noms = parc.reseaux.map(function (r) { return [r, r]; });
  if (!E.reseau1 && noms.length) E.reseau1 = noms[0][0];
  remplit($("f-reseau1"), noms, E.reseau1);
  remplit($("f-reseau2"), [["", "(identique au principal)"]].concat(noms), E.reseau2);
}

// ---- Bloc metier ----
function dessineMetiers() {
  var liste = vide($("metiers"));
  E.metiers.forEach(function (nom, i) {
    var ligne = el("div", {"class": "metier"}), champ = el("input", {type: "text", "data-metier": i, id: "metier-" + i,
      placeholder: i === 0 ? "ex. piscine (principal)" : "autre bloc"});
    champ.value = nom; ligne.appendChild(champ);
    if (E.metiers.length > 1) { var b = el("button", {"class": "btn", type: "button", "data-retire": i}, "Retirer"); ligne.appendChild(b); }
    liste.appendChild(ligne);
  });
  $("avert-metier").classList.toggle("cache", noms().length > 0);
}
function noms() { return E.metiers.map(function (m) { return m.trim(); }).filter(function (m) { return m; }); }

// ---- Entrees/sorties du bloc metier principal (un tableau par groupe, parc.groupes vient du modele) ----
function copie(x) { return JSON.parse(JSON.stringify(x)); }
function nouvelElement(g, n) { var e = copie(g.gabarit); e.nom = e.nom.replace(/\d+$/, "") + n; e.id = n; return e; }
function idSuivant(l) { return l.reduce(function (m, e) { return Math.max(m, parseInt(e.id, 10) || 0); }, 0) + 1; }
function champEl(tag, g, i, cle, valeur, options) {
  var c = el(tag, {"data-el": g + "|" + i + "|" + cle, id: "el-" + g + "-" + i + "-" + cle, "aria-label": cle});
  if (tag === "select") {
    options.forEach(function (o) { var op = el("option", {value: o[0]}, o[1]); if (String(o[0]) === String(valeur)) op.selected = true; c.appendChild(op); });
  } else { c.type = cle === "nom" ? "text" : "number"; c.value = valeur; }
  return c;
}
function optionsBroches(courante) {
  var l = [[-1, "aucune (-1)"]].concat((parc.broches[E.puce] || []).map(function (p) { return [p, "GPIO" + p]; }));
  if (l.every(function (o) { return o[0] !== courante; })) l.push([courante, "GPIO" + courante + " (hors plage)"]);
  return l;
}
function dessineElements() {
  var zone = vide($("elements"));
  parc.groupes.forEach(function (g) {
    var liste = E.elements[g.id] || [], d = el("details", {id: "groupe-" + g.id}), res = el("summary", {}, g.id + " (" + liste.length + ")");
    if (liste.length) d.setAttribute("open", "");
    d.appendChild(res);
    if (liste.length) {
      var tete = el("div", {"class": "ligne-el tete"});
      ["Activation", "Nom", "Broche", "Type", ""].forEach(function (t) { tete.appendChild(el("span", {}, t)); });
      d.appendChild(tete);
    }
    liste.forEach(function (e, i) {
      var l = el("div", {"class": "ligne-el"});
      l.appendChild(champEl("select", g.id, i, "activation", null, [["ON", "ON"], ["OFF", "OFF"]]));
      l.firstChild.value = e.activation;
      l.appendChild(champEl("input", g.id, i, "nom", e.nom));
      l.appendChild(champEl("select", g.id, i, "pin", e.pin, optionsBroches(e.pin)));
      l.appendChild(champEl("input", g.id, i, "type", e.type));
      l.appendChild(el("button", {"class": "btn", type: "button", id: "retire-" + g.id + "-" + i, "data-retire-el": g.id + "|" + i}, "Retirer"));
      d.appendChild(l);
    });
    d.appendChild(el("button", {"class": "btn", type: "button", id: "ajout-" + g.id, "data-ajout-el": g.id}, "+ Ajouter (" + g.singulier + ")"));
    zone.appendChild(d);
  });
}
function changeElement(t) {
  var p = t.getAttribute("data-el").split("|"), e = E.elements[p[0]][+p[1]], v = t.value;
  e[p[2]] = (p[2] === "nom" || p[2] === "activation") ? v : (parseInt(v, 10) || 0);
  if (p[2] === "pin") e.pin = parseInt(v, 10);
}
function ajouteElement(id) {
  var g = parc.groupes.filter(function (x) { return x.id === id; })[0], l = E.elements[id] || (E.elements[id] = []);
  l.push(nouvelElement(g, idSuivant(l))); dessineElements(); reagit();
}
function retireElement(id, i) { E.elements[id].splice(i, 1); dessineElements(); reagit(); }

// ---- Reponses envoyees au serveur ----
function reponses(pourApercu) {
  var esc = E.role === "esclave", d = defauts(), r = {puce: E.puce, base: E.base,
    lieu: E.lieu || (pourApercu ? "lieu" : ""), nom: E.nom || (pourApercu ? "nom" : ""), ip: E.ip, heure: E.heure,
    role: E.role, maitre: esc ? E.maitre : "", id: esc ? (parseInt(E.id, 10) || 0) : 0,
    reseau1: esc ? "" : E.reseau1, reseau2: esc ? "" : E.reseau2, blocs: fermeture(), metiers: noms(),
    squelettes: !!E.squelettes};
  if (Object.keys(E.elements).length) r.elements = E.elements;             // groupe absent = gabarit du modele
  IDENT.forEach(function (k) { r[k] = (E[k] === d[k]) ? "" : E[k]; });      // inchange -> defaut du serveur
  if (modif) { r.define = E.define; r.elements_groupe = E.elements_groupe; }   // relus de la carte, a renvoyer tels quels
  return r;
}

// ---- Apercu ----
function planifieApercu() { clearTimeout(minuteur); minuteur = setTimeout(apercu, 300); }
async function apercu() {
  var mon = ++numero, rep = await api("/apercu", {reponses: reponses(true)}), zone = vide($("apercu-refus"));
  if (mon !== numero) return;                                  // une saisie plus recente est deja partie
  if (!rep.ok || !rep.donnees) { zone.appendChild(el("div", {"class": "avert rouge"}, rep.texte)); return; }
  $("apercu").textContent = rep.donnees.persist;
  rep.donnees.refus.forEach(function (t) { zone.appendChild(el("div", {"class": "avert rouge"}, t)); });
  rep.donnees.avertissements.forEach(function (t) { zone.appendChild(el("div", {"class": "avert"}, t)); });
}

// ---- Diff et creation ----
function signature() { return JSON.stringify(reponses(false)); }
function majCreer() {
  var pret = !!diff && diff.refus.length === 0 && !!diff.empreinte && !diff.vide && signature() === signatureDiff;
  $("creer").disabled = !pret;
  if (diff && signature() !== signatureDiff) {                  // saisie apres le diff : il ne vaut plus
    diff = null; $("panneau-diff").classList.add("cache"); vide($("retours"));
  }
  $("voir-diff").disabled = noms().length === 0;
  majLibelle();
}
function invalideDiff() {                                      // le diff ne vaut plus : il faut en demander un autre
  diff = null; signatureDiff = null; $("panneau-diff").classList.add("cache"); vide($("retours")); majCreer();
}
function liste(zone, textes, classe) { textes.forEach(function (t) { zone.appendChild(el("div", {"class": classe}, t)); }); }
async function voirDiff() {
  var rep = reponses(false), zone = vide($("retours"));
  var r = modif ? await api("/modification/prepare", {env: modif, reponses: rep}) : await api("/prepare", {reponses: rep});
  if (!r.ok || !r.donnees) { liste(zone, [r.texte], "avert rouge"); return; }
  diff = r.donnees; signatureDiff = JSON.stringify(rep);
  liste(zone, diff.refus, "avert rouge"); liste(zone, diff.avertissements, "avert");
  if (diff.vide) liste(zone, ["Aucun changement : rien à modifier."], "avert");
  $("diff").textContent = diff.diff; $("autoexec").textContent = diff.apercu ? diff.apercu.autoexec : "";
  $("details-autoexec").classList.toggle("cache", !diff.apercu);
  $("panneau-diff").classList.toggle("cache", !diff.diff);
  majCreer();
}
function fichiers() {
  if (modif) { vide($("fichiers")).appendChild(el("li", {}, "Les seuls écarts du diff, dans les fichiers existants de l'env")); return; }
  var d = "data/" + (E.lieu || "?") + "/…", l = ["platformio_tasmota_cenv.ini", "tasmota/user_config_override.h",
    d + "/_persist.json", d + "/autoexec.be", d + "/graphiques.json"];
  if (E.squelettes) noms().forEach(function (n) { var c = n.charAt(0).toUpperCase() + n.slice(1); l.push(d + "/controle" + c + ".be", d + "/" + n + "Fonctions.be"); });
  var ul = vide($("fichiers")); l.forEach(function (x) { ul.appendChild(el("li", {}, x)); });
}
function lienHote(lien) {                                      // port et chemin du serveur, hote de la page (autre appareil, IPv6)
  var u = new URL(lien); u.hostname = location.hostname; return u.href;
}
async function cree_env() {
  $("creer").disabled = true;
  var r = await api("/creation", {reponses: JSON.parse(signatureDiff), empreinte: diff.empreinte}), zone = vide($("resultat"));
  if (!r.ok || !r.donnees) {
    if (r.statut === 409) invalideDiff();                       // saisie ou fichiers changes : un nouveau « Voir le diff » est exige
    zone.appendChild(el("div", {"class": "avert rouge", id: "creation-erreur"}, r.texte)); majCreer(); return;
  }
  var c = r.donnees;
  zone.appendChild(el("p", {"class": "ok", id: "creation-ok"}, "Env " + c.env + " créé (sauvegarde : " + c.sauvegarde + ")."));
  var liens = el("p", {"class": "liens"});
  [["lien-build", lienHote(c.liens.build), "Compiler et téléverser (page build)"],
   ["lien-fichiers", lienHote(c.liens.fichiers), "Fichiers Berry de l'env"]].forEach(function (x) {
    var a = el("a", {id: x[0], href: x[1], target: "_blank", rel: "noopener"}, x[2]); liens.appendChild(a);
  });
  zone.appendChild(liens); liste(zone, c.avertissements, "avert");
  zone.appendChild(el("pre", {id: "resume"}, c.resume));
  var copie = el("button", {"class": "btn", id: "copier", type: "button"}, "Copier le résumé");
  copie.onclick = function () { copier(c.resume, copie); };
  zone.appendChild(copie);
  await relitParc(); await chargeEnv(c.env, true);                // la page reste sur l'env cree, en mode modification
}
function copier(texte, bouton) {
  var fini = function () { bouton.textContent = "Copié"; };
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(texte).then(fini, function () { repli(texte); fini(); });
  else { repli(texte); fini(); }
}
function repli(texte) {
  var t = el("textarea"); t.value = texte; document.body.appendChild(t); t.select();
  try { document.execCommand("copy"); } catch (e) { /* tant pis : le resume reste affiche */ }
  document.body.removeChild(t);
}

// ---- Etapes ----
function afficheEtape(i) {
  etape = Math.max(0, Math.min(ETAPES.length - 1, i));
  for (var k = 0; k < ETAPES.length; k++) $("etape-" + k).classList.toggle("cache", k !== etape);
  var p = vide($("pastilles"));
  ETAPES.forEach(function (n, k) {
    var s = el("span", {"data-e": k, id: "pastille-" + k, "class": k === etape ? "actif" : (k < etape ? "fait" : "")}, (k + 1) + ". " + n);
    p.appendChild(s);
  });
  $("prec").disabled = etape === 0; $("suiv").classList.toggle("cache", etape === ETAPES.length - 1);
  if (etape === ETAPES.length - 1) fichiers();
}

// ---- Evenements ----
function reagit() { dessineFonctions(); dessineReseau(); majIdentite(); dessineMetierAvert(); majCreer(); planifieApercu(); }
function dessineMetierAvert() { $("avert-metier").classList.toggle("cache", noms().length > 0); }
function change(ev) {
  var t = ev.target;
  if (t.name === "role") E.role = t.value;
  else if (t.hasAttribute("data-bloc")) {
    var id = t.getAttribute("data-bloc"), i = E.blocs.indexOf(id);
    if (t.checked && i < 0) E.blocs.push(id); else if (!t.checked && i >= 0) E.blocs.splice(i, 1);
  } else if (t.hasAttribute("data-el")) changeElement(t);
  else if (t.hasAttribute("data-metier")) E.metiers[+t.getAttribute("data-metier")] = t.value;
  else if (t.hasAttribute("data-k")) {
    var k = t.getAttribute("data-k");
    E[k] = t.type === "checkbox" ? t.checked : t.value;
    if (t.hasAttribute("data-ident")) manuel[k] = t.value !== "";
    if (k === "puce") { E.base = parc.base_defaut[E.puce] || (parc.bases[E.puce] || [])[0] || ""; remplitBases(); E.blocs = E.blocs.filter(permis); dessineElements(); }
  }
  reagit();
}
function remplitBases() {
  remplit($("f-base"), (parc.bases[E.puce] || []).map(function (b) { return [b, b]; }), E.base);
}
async function demarre() {
  var r = await api("/parc");
  if (!r.ok || !r.donnees) { var b = $("bandeau-erreur"); b.textContent = "Le parc n'a pas pu être lu : " + r.texte; b.classList.remove("cache"); return; }
  parc = r.donnees;
  var eb = Object.keys(parc.erreur_broches || {});
  if (eb.length) { var bb = $("bandeau-erreur"); bb.textContent = eb.map(function (p) { return parc.erreur_broches[p]; }).join(" ; ") +
    " — les broches de ces puces ne sont pas vérifiables."; bb.classList.remove("cache"); }
  if (parc.erreur_modele) { var m = $("bandeau-erreur"); m.textContent = parc.erreur_modele + " — création impossible tant que le modèle est illisible."; m.classList.remove("cache"); }
  remplit($("f-puce"), parc.puces.map(function (p) { return [p, p]; }), E.puce);
  E.base = parc.base_defaut[E.puce] || (parc.bases[E.puce] || [])[0] || ""; remplitBases();
  $("f-ip").value = E.ip;
  afficheEtape(0); dessineElements(); dessineListeEnv(); reagit(); apercu(); majModele();
  var i = await api("/interrompues");
  if (i.ok && i.donnees) i.donnees.interrompues.forEach(function (op) { interrompue(op); });
}
// ---- Bandeau du modele (fusion automatique faite au demarrage ; retraits et alignements a la demande) ----
function pluriel(n, un, plusieurs) { return n + " " + (n > 1 ? plusieurs : un); }
async function majModele() {
  var r = await api("/modele/etat"), b = $("bandeau-modele");
  if (!r.ok || !r.donnees) return;
  var e = r.donnees, n = e.a_completer.length, ret = e.disparues.length, ali = Object.keys(e.divergentes).length, t = [];
  if (n) t.push(pluriel(n, "clé ajoutée", "clés ajoutées") + " au modèle, à compléter");
  if (ret) t.push(pluriel(ret, "clé du modèle absente", "clés du modèle absentes") + " du parc");
  if (ali) t.push(pluriel(ali, "défaut divergent", "défauts divergents"));
  b.classList.toggle("cache", !!e.erreur || t.length === 0);
  $("texte-modele").textContent = t.join(" · ");
  var l = vide($("liste-modele"));
  e.a_completer.forEach(function (c) {                          // une ligne par clé : chemin = défaut (secret masqué) + « Relue »
    var ligne = el("div", {}, c + " = " + e.valeurs[c] + " "), bt = el("button", {"class": "btn", type: "button"}, "Relue");
    bt.onclick = function () { proposeModele(c); };
    ligne.appendChild(bt); l.appendChild(ligne);
  });
}
async function proposeModele(relue) {                          // relue : chemin à marquer relu ; sinon retraits et alignements
  var zone = vide($("retours-modele")), r = await api("/modele/prepare", relue ? {relue: relue} : {});
  $("panneau-modele").classList.remove("cache");
  if (!r.ok || !r.donnees) { liste(zone, [r.texte], "avert rouge"); $("valide-modele").disabled = true; return; }
  propositionModele = r.donnees; propositionModele.relue = relue;
  var rien = !propositionModele.empreinte;
  if (rien) liste(zone, ["Rien à retirer ni à aligner : le modèle suit le parc."], "avert");
  $("diff-modele").textContent = propositionModele.diff;
  $("valide-modele").disabled = rien;
}
async function appliqueModele() {
  var zone = vide($("retours-modele")), r = await api("/modele/applique", {empreinte: propositionModele.empreinte, relue: propositionModele.relue});
  if (!r.ok || !r.donnees) { liste(zone, [r.texte], "avert rouge"); $("valide-modele").disabled = true; return; }
  $("panneau-modele").classList.add("cache"); propositionModele = null;
  invalideDiff();                                               // l'empreinte de la creation couvre le modele
  await majModele();
}
function interrompue(op) {
  var d = el("div", {"class": "avert rouge"}), b = el("button", {"class": "btn", type: "button"}, "J'ai vérifié");
  d.appendChild(document.createTextNode("Opération interrompue (" + op.nature + ", " + op.debut + ") : " + (op.etapes || []).join(" ; ") + " "));
  b.onclick = async function () { await api("/interrompue/acquitte", {nom: op.nom}); d.parentNode.removeChild(d); };
  d.appendChild(b); $("interrompues").appendChild(d);
}

/*ENV*/
$("formulaire").addEventListener("change", function (ev) { if (parc) change(ev); });
$("formulaire").addEventListener("input", function (ev) {
  if (!parc) return;
  var t = ev.target;
  if (t.type === "text" || t.type === "number") change(ev);
});
$("formulaire").addEventListener("click", function (ev) {
  var t = ev.target, r = t.getAttribute && t.getAttribute("data-retire");
  if (t.hasAttribute && t.hasAttribute("data-ajout-el")) { ajouteElement(t.getAttribute("data-ajout-el")); return; }
  if (t.hasAttribute && t.hasAttribute("data-retire-el")) { var q = t.getAttribute("data-retire-el").split("|"); retireElement(q[0], +q[1]); return; }
  if (r !== null && r !== undefined && t.hasAttribute("data-retire")) { E.metiers.splice(+r, 1); dessineMetiers(); reagit(); }
});
$("pastilles").addEventListener("click", function (ev) { var e = ev.target.getAttribute("data-e"); if (e !== null) afficheEtape(+e); });
$("prec").onclick = function () { afficheEtape(etape - 1); };
$("suiv").onclick = function () { afficheEtape(etape + 1); };
$("ajout-metier").onclick = function () { E.metiers.push(""); dessineMetiers(); };
$("voir-diff").onclick = voirDiff;
$("maj-modele").onclick = function () { proposeModele(); };
$("valide-modele").onclick = appliqueModele;
$("annule-modele").onclick = function () { $("panneau-modele").classList.add("cache"); propositionModele = null; };
$("creer").onclick = function () { return modif ? modifieEnv() : cree_env(); };
dessineMetiers();
demarre();
"""
