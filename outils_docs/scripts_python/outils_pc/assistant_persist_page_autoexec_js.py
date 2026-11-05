"""Script de l'onglet « autoexec.bat » de l'Assistant persist (plan autoexec-bat, A6), insere a la place de
/*JS_AUTOEXEC*/ dans le script de la page (il se sert de $, el, vide, api, remplit, pluriel et parc ; le reste est
enferme dans une fonction : aucun nom ne deborde sur l'onglet Persist).

  - le texte de la page est TOUJOURS le texte masque (`***`) ; le serveur demasque lui-meme (analyse, diff, ecriture) ;
  - analyse relancee a la frappe (anti-rebond 400 ms, reponses perimees ignorees) ; marge et liste re-dessinees ;
  - « Ecrire dans le depot » : sur le texte du dernier diff, avec l'empreinte de la lecture et rouges_lus = N si la
    case est cochee, 0 sinon (le serveur refuse et dit pourquoi) ;
  - « Envoyer a la carte (OTA)… » : seulement sans modification non ecrite (le serveur envoie le fichier du DEPOT) ;
    prepare -> fichier de la carte montre s'il differe (case pour le remplacer), « redemarrer ensuite » decochee ;
  - la ligne inseree est rendue ici (miroir d'autoexec_banque.rend) ; un modele ajoute est valide par le serveur.
Textes du serveur par textContent (el) ou attribut title, jamais innerHTML.
"""

from assistant_persist_page_autoexec_lignes_js import JS as LIGNES

JS = r"""
// ---- Onglets ----
function montreOnglet(nom) {
  ["persist", "autoexec"].forEach(function (o) {
    $("onglet-" + o).setAttribute("aria-selected", String(o === nom));
    $("vue-" + o).hidden = o !== nom;
  });
  if (nom === "autoexec") ongletAutoexec();
}
$("onglet-persist").onclick = function () { montreOnglet("persist"); };
$("onglet-autoexec").onclick = function () { montreOnglet("autoexec"); };

var ongletAutoexec = (function () {
var LH = 20, TYPES = {secret: "Secret en clair", doublon: "Doublon persist", inconnue: "Commande inconnue", longueur: "Ligne trop longue"};
var X = {env: "", lu: null, avert: [], banque: null, choisie: null, valeurs: {}, numero: 0, minuteur: null, diff: null,
  texteDiff: null, ligneIns: 0, prep: null, proposition: null, ouvert: false};
var M = {champs: []};

function texte() { return $("a-texte").value; }
function lignesDe(t) { var l = t.split("\n"); if (l[l.length - 1] === "") l.pop(); return l; }
function modifie() { return !!X.lu && texte() !== X.lu.texte; }
function rouges() { return X.avert.filter(function (a) { return a.niveau === "rouge"; }).length; }
function message(zone, classe, t, id) { var d = el("div", id ? {"class": classe, id: id} : {"class": classe}, t); zone.appendChild(d); return d; }

// ---- Marge, liste, en-tete ----
function dessineMarge() {
  var m = vide($("a-marge")), par = {}, total = texte().split("\n").length;
  X.avert.forEach(function (a) { (par[a.ligne] = par[a.ligne] || []).push(a); });
  for (var i = 1; i <= total; i++) {
    var avs = par[i] || [], d = el("div", {"data-ligne": i}), p;
    d.appendChild(el("span", {"class": "n"}, String(i)));
    p = el("span", {"class": "p" + (avs.length ? (avs.some(function (a) { return a.niveau === "rouge"; }) ? " rouge" : " orange") : "")}, avs.length ? "●" : "");
    if (avs.length) p.setAttribute("title", avs.map(function (a) { return libelle(a) + " : " + a.message + (a.correction ? " → " + a.correction : ""); }).join("\n"));
    d.appendChild(p); m.appendChild(d);
  }
  m.scrollTop = $("a-texte").scrollTop;
}
function libelle(a) {
  if (a.type === "redemarrage") return a.niveau === "rouge" ? "Redémarrage à répétition" : "Redémarrage si la valeur change";
  return TYPES[a.type] || a.type;
}
function dessineListe() {
  var z = vide($("a-avertissements"));
  $("a-titre-analyse").textContent = "Analyse : " + pluriel(X.avert.length, "avertissement", "avertissements");
  if (X.lu && !X.avert.length) message(z, "discret", "Aucun avertissement.");
  X.avert.forEach(function (a) {
    var d = el("div", {"class": "a-av " + (a.niveau === "rouge" ? "r" : "o"), "data-ligne": a.ligne, role: "button", tabindex: "0"}), s = el("span");
    d.appendChild(el("b", {}, "l. " + a.ligne));
    var lib = libelle(a), msg = a.message.indexOf(lib) === 0 ? a.message.slice(lib.length).replace(/^\s*:?\s*/, "") : a.message;
    s.appendChild(el("b", {}, lib + " ")); s.appendChild(document.createTextNode(msg));
    var ecrit = a.type === "inconnue" && a.correction && /^Commande inconnue : (.+)\.$/.exec(a.message);
    if (ecrit) {
      s.appendChild(document.createTextNode(" → " + a.correction + " ? "));
      var b = el("button", {"class": "btn s", type: "button", "data-corrige": a.ligne}, "Corriger");
      b.onclick = function (ev) { ev.stopPropagation(); corrige(a.ligne, ecrit[1], a.correction); };
      s.appendChild(b);
    } else if (a.correction) s.appendChild(el("span", {"class": "discret"}, " — " + a.correction));
    if (a.commande) boutonEnlever(a, s);
    d.appendChild(s);
    d.onclick = function () { vaLigne(a.ligne); };
    d.onkeydown = function (ev) { if (ev.target === d && (ev.key === "Enter" || ev.key === " ")) { ev.preventDefault(); vaLigne(a.ligne); } };
    z.appendChild(d);
  });
}
function majTete() {
  $("a-info").textContent = X.lu ? X.lu.chemin + " · " + (X.lu.existe ? "" : "nouveau fichier · ") +
    pluriel(lignesDe(texte()).length, "ligne", "lignes") + " · " + pluriel(X.avert.length, "avertissement", "avertissements") +
    (modifie() ? " · modifié" : "") : "";
  $("a-annuler").disabled = !modifie();
  $("a-enregistrer").disabled = !X.lu;
  var b = $("a-envoyer"), aide = !X.lu ? "" : modifie() ? "Écrire d'abord dans le dépôt : c'est le fichier du dépôt qui est envoyé."
    : !X.lu.existe ? "Pas d'autoexec.bat dans le dépôt pour cette carte." : "La carte l'exécute au prochain démarrage.";
  b.disabled = !X.lu || !X.lu.existe || modifie();
  b.title = aide; $("a-envoi-aide").textContent = aide;
  $("a-ecrire").disabled = !(X.diff && X.diff.diff && texte() === X.texteDiff);
}
function dessine() { dessineMarge(); dessineListe(); majTete(); majInsertion(); }

// ---- Texte : curseur, aller a une ligne, correction, analyse a la frappe ----
function bornes(n) {
  var l = texte().split("\n"), d = 0;
  for (var i = 0; i < n - 1 && i < l.length; i++) d += l[i].length + 1;
  return [d, d + (l[n - 1] || "").length];
}
function vaLigne(n) {
  var ta = $("a-texte"), b = bornes(n);
  ta.focus(); ta.setSelectionRange(b[0], b[1]);
  ta.scrollTop = Math.max(0, (n - 1) * LH - ta.clientHeight / 2);
  $("a-marge").scrollTop = ta.scrollTop; majCurseur();
}
function ligneCurseur() { var ta = $("a-texte"); return ta.value.slice(0, ta.selectionStart).split("\n").length; }
function ligneIns() { var max = lignesDe(texte()).length + 1; return X.ligneIns ? Math.min(X.ligneIns, max) : max; }
function majCurseur() {                              // seulement sur un geste dans le texte : un value = ... envoie le curseur a la fin
  if (document.activeElement === $("a-texte")) X.ligneIns = ligneCurseur() + 1;
  majInsertion();
}
function majInsertion() { majProposition(); majLignes(); }
function corrige(n, ecrit, par) {
  var l = texte().split("\n"), re = new RegExp("(^|[\\s;])" + ecrit.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "(?=$|[\\s=;])");
  var ta = $("a-texte"), d = ta.selectionStart, f = ta.selectionEnd;
  l[n - 1] = l[n - 1].replace(re, function (m0, avant) { return avant + par; });
  ta.value = l.join("\n"); ta.setSelectionRange(d, f); aChange();
}
function aChange() {
  X.numero++;                                          // une analyse partie avant cette frappe ne s'applique plus
  if (modifie()) fermeEnvoi();                         // l'envoi part du fichier du DEPOT : jamais avec un texte non ecrit
  document.querySelectorAll("[data-enleve]").forEach(function (b) { b.disabled = true; });   // numeros perimes jusqu'a la prochaine analyse
  dessineMarge(); majTete(); majInsertion();
  clearTimeout(X.minuteur); X.minuteur = setTimeout(analyse, 400);
}
async function analyse() {
  var n = ++X.numero, env = X.env, r = await api("/autoexec/analyse", {env: env, texte: texte()}), z = $("a-erreur-analyse");
  if (n !== X.numero || env !== X.env) return;
  if (!r.ok || !r.donnees) { z.textContent = r.texte; z.hidden = false; return; }
  z.hidden = true; X.avert = r.donnees.avertissements; dessine();
}

// ---- Carte ----
async function charge(env) {
  X.env = env; X.lu = null; X.avert = []; X.ligneIns = 0; X.numero++; clearTimeout(X.minuteur);
  fermeDiff(); $("a-panneau-envoi").hidden = true; $("a-erreur").hidden = true; $("a-erreur-analyse").hidden = true;
  $("a-texte").value = ""; $("a-texte").disabled = true;
  if (env) {
    var r = await api("/autoexec?env=" + encodeURIComponent(env));
    if (env !== X.env) return;
    if (!r.ok || !r.donnees) { $("a-erreur").textContent = r.texte; $("a-erreur").hidden = false; }
    else { X.lu = r.donnees; X.avert = X.lu.avertissements; $("a-texte").value = X.lu.texte; $("a-texte").disabled = false; }
  }
  dessine();
}
function annule() {
  if (!X.lu) return;
  X.numero++; clearTimeout(X.minuteur); $("a-erreur-analyse").hidden = true;
  $("a-texte").value = X.lu.texte; X.avert = X.lu.avertissements; fermeDiff(); dessine();
}

// ---- Diff et ecriture ----
function fermeDiff() {
  X.diff = null; X.texteDiff = null; vide($("a-retours")); $("a-ligne-rouges").hidden = true;
  var p = vide($("a-diff")); p.appendChild(el("span", {"class": "discret"}, "« Enregistrer… (diff) » montre ici les changements avant l'écriture."));
}
async function voirDiff() {
  var t = texte(), r = await api("/autoexec/diff", {env: X.env, texte: t});
  fermeDiff();
  if (!r.ok || !r.donnees) { message($("a-retours"), "avert rouge", r.texte); majTete(); return; }
  X.diff = r.donnees; X.texteDiff = t;
  var p = vide($("a-diff"));
  if (!X.diff.diff) p.appendChild(el("span", {"class": "discret"}, "Aucune modification."));
  else X.diff.diff.split("\n").forEach(function (l) {
    var c = l.slice(0, 3) === "+++" || l.slice(0, 3) === "---" ? "" : l.charAt(0) === "+" ? "plus" : l.charAt(0) === "-" ? "moins" : "";
    p.appendChild(el("div", c ? {"class": c} : {}, l));
  });
  $("a-rouges-lus").checked = false;
  $("a-rouges-texte").textContent = "J'ai lu les " + X.diff.rouges + " avertissements rouges";
  $("a-ligne-rouges").hidden = !X.diff.rouges;
  majTete();
  if (X.diff.empreinte !== X.lu.empreinte) message($("a-retours"), "avert", "Le fichier a changé sur le disque depuis sa lecture : l'écriture sera refusée.");
}
async function ecrit() {
  $("a-ecrire").disabled = true;
  var env = X.env, z = vide($("a-retours")), r = await api("/autoexec/ecrit", {env: env, texte: X.texteDiff, empreinte: X.lu.empreinte,
    rouges_lus: $("a-rouges-lus").checked ? X.diff.rouges : 0});
  if (!r.ok || !r.donnees) { message(z, "avert rouge", r.texte, "a-ecrit-erreur"); majTete(); return; }
  await charge(env);
  message($("a-retours"), "ok", "Écrit dans le dépôt : " + r.donnees.chemin + ". La carte l'exécutera une fois envoyé : « Puis envoyer à la carte (OTA)… ».", "a-ecrit-ok");
}

// ---- Envoi a la carte ----
function fermeEnvoi() { $("a-panneau-envoi").hidden = true; X.prep = null; majEnvoyer(); }
function majEnvoyer() { $("a-envoi-go").disabled = !(X.prep && (!X.prep.ecart || $("a-ecart-vu").checked)); }
async function prepareEnvoi() {
  var z = vide($("a-envoi-retours")), n = rouges();
  X.prep = null; $("a-panneau-envoi").hidden = false; $("a-ecart").hidden = true;
  $("a-redemarrer").checked = false; $("a-ecart-vu").checked = false; $("a-envoi-rouges-lus").checked = false;
  $("a-envoi-rouges").hidden = !n; $("a-envoi-rouges-texte").textContent = "J'ai lu les " + n + " avertissements rouges";
  $("a-envoi-adresse").textContent = "Lecture de la carte…"; majEnvoyer();
  var env = X.env, r = await api("/autoexec/envoi/prepare", {env: env});
  if (env !== X.env || modifie() || $("a-panneau-envoi").hidden) return;     // carte changee, texte modifie ou panneau ferme entre-temps
  if (!r.ok || !r.donnees) { $("a-envoi-adresse").textContent = ""; message(z, "avert rouge", r.texte); return; }
  X.prep = r.donnees;
  $("a-envoi-adresse").textContent = "Carte " + X.prep.hostname_carte + " à l'adresse " + X.prep.adresse + " (identité vérifiée).";
  $("a-ecart").hidden = !X.prep.ecart;
  $("a-sur-carte").textContent = X.prep.sur_carte === null ? "(aucun autoexec.bat sur la carte)" : X.prep.sur_carte;
  $("a-sur-depot").textContent = X.lu.texte;
  majEnvoyer();
}
async function envoie() {
  $("a-envoi-go").disabled = true;
  var z = vide($("a-envoi-retours")), r = await api("/autoexec/envoi", {env: X.env, jeton: X.prep.jeton,
    rouges_lus: $("a-envoi-rouges-lus").checked ? rouges() : 0, redemarrer: $("a-redemarrer").checked});
  if (!r.ok || !r.donnees) { message(z, "avert rouge", r.texte); majEnvoyer(); return; }
  message(z, "ok", "Envoyé à la carte." + (r.donnees.sauvegarde ? " Copie de l'ancien fichier de la carte : " + r.donnees.sauvegarde : ""), "a-envoi-ok");
  if (r.donnees.avertissement) message(z, "avert", r.donnees.avertissement);
  X.prep = null;
}

// ---- Banque : recherche, formulaire, apercu, insertion ----
function nomAffiche(e) { return e.modele.split(" ")[0].replace(/\{(\w+)\}/g, "<$1>"); }
function rendu(e, valeurs) {
  var par = {}, erreur = null;
  e.champs.forEach(function (c) {
    if (erreur) return;
    var v = valeurs[c.cle] !== undefined ? valeurs[c.cle] : c.defaut, t = v === null || v === undefined ? "" : String(v);
    if (t === "" && c.type !== "texte") { erreur = c.libelle + " : valeur manquante"; return; }
    if (/[\r\n]/.test(t)) erreur = c.libelle + " : pas de saut de ligne";
    else if (c.type === "nombre" || c.type === "relais") {
      var n = Number(t);
      if (t.trim() === "" || !isFinite(n)) erreur = c.libelle + " : « " + t + " » n'est pas un nombre";
      else if (c.type === "relais" && (n !== Math.floor(n) || n < 1)) erreur = c.libelle + " : un numéro de relais entier, 1 au moins";
      else if ((c.min !== undefined && c.min !== null && n < c.min) || (c.max !== undefined && c.max !== null && n > c.max))
        erreur = c.libelle + " : " + n + " hors de " + (c.min != null ? c.min : "…") + " à " + (c.max != null ? c.max : "…");
      t = String(n);
    } else if (c.type === "heure" && !/^([01]\d|2[0-3]):[0-5]\d$/.test(t)) erreur = c.libelle + " : « " + t + " » n'est pas une heure HH:MM";
    else if (c.type === "jours" && !/^[01]{7}$/.test(t)) erreur = c.libelle + " : 7 chiffres 0 ou 1, dimanche en premier";
    par[c.cle] = t;
  });
  return erreur ? {erreur: erreur} : {ligne: e.modele.replace(/\{([A-Za-z_]\w*)\}/g, function (m0, k) { return k in par ? par[k] : m0; })};
}
function numeroLibre(e, c) {             // Timer{n} : le premier numero absent du texte
  var m = /^([A-Za-z]+)\{(\w+)\}/.exec(e.modele);
  if (!m || m[2] !== c.cle || c.type !== "nombre") return c.defaut;
  var pris = {}, re = new RegExp("^\\s*" + m[1] + "(\\d+)(?![\\d\\w])", "i");
  texte().split("\n").forEach(function (l) { var k = re.exec(l); if (k) pris[+k[1]] = true; });
  for (var i = c.min || 1; i <= (c.max || 99); i++) if (!pris[i]) return i;
  return c.defaut;
}
function cherche() {
  var q = $("a-recherche").value.trim().toLowerCase(), z = vide($("a-resultats"));
  if (!X.banque) return;
  var trouve = X.banque.filter(function (e) { return !q || (e.nom + " " + e.categorie + " " + e.description).toLowerCase().indexOf(q) >= 0; });
  trouve.slice(0, 8).forEach(function (e) { z.appendChild(carteCommande(e, false)); });
  if (trouve.length > 8) message(z, "discret", (trouve.length - 8) + " autre(s) : préciser la recherche.");
  if (!trouve.length) message(z, "discret", "Aucune commande ne correspond : « Nouveau modèle… » pour l'ajouter.");
}
function carteCommande(e, perso) {
  var d = el("div", {"class": "a-cmd" + (X.choisie === e ? " choisie" : ""), role: "button", tabindex: "0", "data-nom": e.nom}), l = el("div", {"class": "a-l"});
  var r = perso ? rendu(e, {}) : null;
  l.appendChild(el("span", {"class": "code"}, perso ? r.ligne || e.modele : nomAffiche(e)));
  if (perso) {
    var b = el("button", {"class": "btn s", type: "button"}, "Insérer");
    b.onclick = function (ev) { ev.stopPropagation(); choisit(e); insereOuMontre(); };
    l.appendChild(b);
  } else l.appendChild(el("span", {"class": "etiq" + (e.origine === "perso" ? " u" : "")}, e.origine === "perso" ? "perso" : e.categorie));
  d.appendChild(l);
  if (!perso) d.appendChild(el("div", {"class": "discret"}, e.description));
  d.onclick = function () { choisit(e); };
  d.onkeydown = function (ev) { if (ev.target === d && ev.key === "Enter") choisit(e); };
  return d;
}
function choisit(e) {
  X.choisie = e; X.valeurs = {};
  e.champs.forEach(function (c) { X.valeurs[c.cle] = numeroLibre(e, c); });
  $("a-choix").hidden = false; $("a-choisie").textContent = nomAffiche(e); $("a-choisie-desc").textContent = e.description;
  var z = vide($("a-champs"));
  e.champs.forEach(function (c) { z.appendChild(saisie(c)); });
  cherche(); apercu();
}
function saisie(c) {
  var d = el("div", {"class": "a-champ"}), v = X.valeurs[c.cle], id = "a-c-" + c.cle, s;
  d.appendChild(el(c.type === "jours" ? "span" : "label", c.type === "jours" ? {} : {"for": id}, c.libelle));
  if (c.type === "liste") {
    s = el("select", {id: id, "data-cle": c.cle});
    c.choix.forEach(function (ch) {
      var val = typeof ch === "object" ? ch.valeur : ch;
      s.appendChild(el("option", {value: String(val)}, typeof ch === "object" ? ch.libelle + " (" + val + ")" : String(ch)));
    });
    s.value = v === null || v === undefined ? "" : String(v);
  } else if (c.type === "jours") {
    s = el("span", {"class": "a-jours", id: id, role: "group", "aria-label": c.libelle});
    ["D", "L", "M", "M", "J", "V", "S"].forEach(function (j, i) {
      var l = el("label", {title: ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"][i]}),
        b = el("input", {type: "checkbox", "data-jour": i, "data-cle": c.cle});
      b.checked = String(v || "0000000").charAt(i) === "1"; l.appendChild(b); l.appendChild(document.createTextNode(j)); s.appendChild(l);
    });
  } else {
    s = el("input", {id: id, "data-cle": c.cle, type: c.type === "heure" ? "time" : c.type === "texte" ? "text" : "number"});
    if (c.min !== undefined && c.min !== null) s.setAttribute("min", c.min);
    else if (c.type === "relais") s.setAttribute("min", 1);
    if (c.max !== undefined && c.max !== null) s.setAttribute("max", c.max);
    s.value = v === null || v === undefined ? "" : String(v);
  }
  d.appendChild(s);
  return d;
}
function litChamps() {
  if (!X.choisie) return;
  X.choisie.champs.forEach(function (c) {
    if (c.type === "jours") X.valeurs[c.cle] = Array.prototype.map.call(document.querySelectorAll("#a-c-" + c.cle + " input"), function (b) { return b.checked ? "1" : "0"; }).join("");
    else X.valeurs[c.cle] = $("a-c-" + c.cle).value;
  });
  apercu();
}
function apercu() {
  var r = rendu(X.choisie, X.valeurs);
  $("a-apercu").textContent = r.ligne || ""; $("a-ajout-erreur").textContent = r.erreur || "";
  $("a-inserer").disabled = !!r.erreur;
  majLignes();
}
function insere() {
  var r = rendu(X.choisie, X.valeurs), l = texte().split("\n"), n = ligneIns();
  if (r.erreur || !X.lu) return;
  l.splice(Math.min(n - 1, lignesDe(texte()).length), 0, r.ligne);
  $("a-texte").value = l.join("\n"); aChange(); vaLigne(n);
  choisit(X.choisie);                                  // numero libre suivant pour une deuxieme minuterie
}
async function chargeBanque() {
  var r = await api("/autoexec/banque"), z = $("a-banque-erreur");
  z.hidden = r.ok && Array.isArray(r.donnees);
  if (!z.hidden) z.textContent = "Banque illisible : " + r.texte;
  X.banque = z.hidden ? r.donnees : [];
  cherche(); dessinePerso(); majProposition();
}
function dessinePerso() {
  var z = vide($("a-perso")), perso = (X.banque || []).filter(function (e) { return e.origine === "perso"; });
  if (!perso.length) message(z, "discret", "Aucune pour l'instant.");
  perso.forEach(function (e) { z.appendChild(carteCommande(e, true)); });
}

/*JS_AUTOEXEC_MODELE*/

// ---- Evenements ----
var ta = $("a-texte");
ta.addEventListener("input", aChange);
ta.addEventListener("scroll", function () { $("a-marge").scrollTop = ta.scrollTop; });
["click", "keyup", "select", "focus"].forEach(function (t) { ta.addEventListener(t, majCurseur); });
$("a-env").onchange = function () {
  if (modifie()) {
    this.value = X.env; $("a-erreur").hidden = false;
    $("a-erreur").textContent = "Modifications non écrites : les écrire, ou « Annuler les modifications », avant de changer de carte.";
    return;
  }
  charge(this.value);
};
$("a-annuler").onclick = annule;
$("a-enregistrer").onclick = voirDiff;
$("a-ecrire").onclick = ecrit;
$("a-envoyer").onclick = prepareEnvoi;
$("a-ecart-vu").onchange = majEnvoyer;
$("a-envoi-go").onclick = envoie;
$("a-envoi-annule").onclick = fermeEnvoi;
$("a-recherche").addEventListener("input", cherche);
$("a-champs").addEventListener("input", litChamps);
$("a-champs").addEventListener("change", litChamps);
$("a-inserer").onclick = insere;
fermeDiff();

return async function () {                            // ouverture de l'onglet : liste des cartes et banque, une fois
  if (X.ouvert) return;
  X.ouvert = true;
  var cartes = parc && parc.cartes;
  if (!cartes) { var r = await api("/parc"); cartes = r.ok && r.donnees ? r.donnees.cartes : []; }
  remplit($("a-env"), [["", "(choisir une carte)"]].concat(cartes.map(function (c) { return [c.env, c.env]; })), "");
  dessine(); chargeBanque();
};
})();
"""

MODELE = r"""
// ---- Editeur de modele (« Tes commandes ») ----
var TYPES_CHAMP = ["texte", "nombre", "liste", "heure", "jours", "relais"];
function majProposition() {
  var n = ligneCurseur(), l = texte().split("\n")[n - 1] || "", t = l.trim(), p = $("a-proposition");
  var m = t && t.charAt(0) !== ";" && /^([A-Za-z_]\w*)(?:[\s=]+(.*))?$/.exec(t), cmd = m ? m[1].toLowerCase() : "";
  var connue = !!m && (X.banque || []).some(function (e) { var b = e.nom.toLowerCase(); return b === cmd || b === cmd.replace(/\d+$/, ""); });
  p.hidden = !(m && X.banque && X.lu && !connue);
  X.proposition = p.hidden ? null : {nom: m[1], reste: m[2] || ""};
  if (!p.hidden) $("a-proposition-texte").textContent = "Ligne " + n + " : « " + m[1] + " » n'est pas dans la banque. ";
}
function ouvreEditeur(p) {
  $("m-nom").value = p ? p.nom : ""; $("m-categorie").value = "Perso"; $("m-description").value = "";
  $("m-modele").value = p ? p.nom + " {valeur}" : "";
  M.champs = p ? [{cle: "valeur", type: "texte", libelle: "Valeur", defaut: p.reste.indexOf("***") >= 0 ? "" : p.reste, choix: "", min: "", max: ""}] : [];
  vide($("m-retours")); $("a-editeur").hidden = false; dessineChamps(); apercuModele();
}
function dessineChamps() {
  var z = vide($("m-champs"));
  M.champs.forEach(function (c, i) {
    var d = el("div", {"class": "m-ch"}), num = c.type === "nombre" || c.type === "relais";
    function ligne(k, lib, entree) { var r = el("div", {"class": "a-champ"}); r.appendChild(el("label", {"for": "m-" + k + "-" + i}, lib)); entree.id = "m-" + k + "-" + i; entree.setAttribute("data-i", i); entree.setAttribute("data-k", k); r.appendChild(entree); d.appendChild(r); }
    ["cle", "libelle", "defaut"].forEach(function (k) { var e = el("input", {type: "text"}); e.value = c[k]; ligne(k, {cle: "Clé", libelle: "Libellé", defaut: "Défaut"}[k], e); });
    var s = el("select"); TYPES_CHAMP.forEach(function (t) { s.appendChild(el("option", {value: t}, t)); }); s.value = c.type; ligne("type", "Type", s);
    if (c.type === "liste") { var ch = el("input", {type: "text", placeholder: "0=Éteindre, 1=Allumer"}); ch.value = c.choix; ligne("choix", "Choix", ch); }
    if (num) ["min", "max"].forEach(function (k) { var e = el("input", {type: "number"}); e.value = c[k]; ligne(k, k === "min" ? "Minimum" : "Maximum", e); });
    var b = el("button", {"class": "btn s", type: "button"}, "Retirer ce champ");
    b.onclick = function () { M.champs.splice(i, 1); dessineChamps(); apercuModele(); };
    d.appendChild(b); z.appendChild(d);
  });
}
function entreeModele() {
  return {nom: $("m-nom").value.trim(), categorie: $("m-categorie").value.trim(), description: $("m-description").value.trim(),
    modele: $("m-modele").value, champs: M.champs.map(function (c) {
      var r = {cle: c.cle.trim(), type: c.type, libelle: c.libelle.trim() || c.cle.trim()}, num = c.type === "nombre" || c.type === "relais";
      if (String(c.defaut) !== "") r.defaut = num && isFinite(Number(c.defaut)) ? Number(c.defaut) : c.defaut;
      if (c.type === "liste") r.choix = c.choix.split(",").map(function (x) { return x.trim(); }).filter(Boolean).map(function (x) {
        var i = x.indexOf("="), v = i < 0 ? x : x.slice(0, i).trim();
        return i < 0 ? x : {valeur: /^-?\d+(\.\d+)?$/.test(v) ? Number(v) : v, libelle: x.slice(i + 1).trim()};
      });
      if (num) ["min", "max"].forEach(function (k) { if (String(c[k]).trim() !== "") r[k] = Number(c[k]); });
      return r;
    })};
}
function apercuModele() {
  var cles = ($("m-modele").value.match(/\{[A-Za-z_]\w*\}/g) || []).map(function (x) { return x.slice(1, -1); });
  cles.forEach(function (k) {                          // une {cle} nouvelle dans la ligne : son champ texte est ajoute
    if (!M.champs.some(function (c) { return c.cle === k; })) { M.champs.push({cle: k, type: "texte", libelle: k, defaut: "", choix: "", min: "", max: ""}); dessineChamps(); }
  });
  var e = entreeModele(), r = rendu(e, {});
  $("m-apercu").textContent = r.ligne || r.erreur || "";
}
async function enregistreModele() {
  var e = entreeModele(), z = vide($("m-retours")), r = await api("/autoexec/banque/ajoute", {entree: e});
  if (!r.ok || !Array.isArray(r.donnees)) { message(z, "avert rouge", r.texte); return; }
  X.banque = r.donnees; $("a-editeur").hidden = true;
  cherche(); dessinePerso(); majProposition();
}
$("a-en-modele").onclick = function () { ouvreEditeur(X.proposition); };
$("a-nouveau-modele").onclick = function () { ouvreEditeur(null); };
$("m-ajout-champ").onclick = function () { M.champs.push({cle: "champ" + (M.champs.length + 1), type: "texte", libelle: "", defaut: "", choix: "", min: "", max: ""}); dessineChamps(); apercuModele(); };
$("m-annule").onclick = function () { $("a-editeur").hidden = true; };
$("m-enregistre").onclick = enregistreModele;
["m-nom", "m-categorie", "m-description", "m-modele"].forEach(function (i) { $(i).addEventListener("input", apercuModele); });
$("m-champs").addEventListener("input", function (ev) {
  var t = ev.target, i = t.getAttribute("data-i");
  if (i === null) return;
  M.champs[+i][t.getAttribute("data-k")] = t.value;
  if (t.getAttribute("data-k") === "type") dessineChamps();
  apercuModele();
});
"""

JS = JS.replace("/*JS_AUTOEXEC_MODELE*/", MODELE + LIGNES)
