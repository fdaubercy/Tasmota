"""Onglet Build de la page build_web.py : bascule « Classer par » Famille / Lieu / Puce (modele D).

Spec docs/superpowers/specs/2026-11-10-classement-par-lieu-design.md §5 ; maquette outils_docs/filtre_lieu/modele-D.png.
Insere dans build_page.PAGE par les marques /*CSS_LIEUX*/ et /*JS_LIEUX*/. Trois branchements dans build_page.py :
  - construitListe appelle lieuxGroupes(liste, membres, donnees) pour la famille « cartes » : en Lieu ou Puce, les
    cartes vont dans un details.famille par groupe (attribut data-groupe) ;
  - majComptes appelle lieuxMaj : filtre par nom, etat des cases d'en-tete, avertissement des coches masques ;
  - chargeEnvs garde l'ouverture par lieuxOuverts / lieuxRestaure.
Ouverture (decision du 2026-11-10) : la regle « ouvert s'il contient un coche » ne vaut qu'au premier dessin d'un
groupe dans la visite ; ensuite l'ouverture de chaque details (famille, sous-groupe, groupe de lieu ou de puce) est
gardee dans `lieuxMemo`, a travers chargeEnvs et les bascules. Un filtre non vide ouvre en Lieu ou Puce les groupes qui
gardent une ligne visible ; le filtre vide rend l'ouverture d'avant le filtre.
La bascule redessine par construitListe : cases, COM/OTA, port et IP vivent dans `choix`, qui survit.
L'ordre de `envs` n'est jamais touche : envsCoches() et donc POST /lancer restent identiques.
Classement garde dans localStorage (cle build.classement) ; le filtre texte ne l'est pas.
"""

CSS = r"""
  /* classement Famille / Lieu / Puce (build_page_lieux.py) */
  .l-barre{display:flex;gap:8px 12px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
  .l-barre .methode button{font-size:13px;padding:4px 12px}
  .l-filtre{flex:0 1 15em;min-width:0;font:inherit;font-size:13px;padding:4px 8px;background:var(--btn);color:var(--texte);border:1px solid var(--btn-bord);border-radius:4px}
  .l-masques{color:var(--orange);font-size:12.5px;margin:-4px 0 8px}
  .env[hidden]{display:none}
  .l-case{width:15px;height:15px;margin:0}
"""

JS = r"""
// ---------- classement Famille / Lieu / Puce de l'onglet Build (build_page_lieux.py) ----------
var CLASSEMENTS = [["famille", "Famille"], ["lieu", "Lieu"], ["puce", "Puce"]];
var ORDRE_PUCES = ["ESP32", "ESP32-S3", "ESP32-P4", "ESP8266"];
var classement = "famille", lieuxTable = [], lieuxCases = [], lieuxMemo = {}, lieuxAvantFiltre = null;
var lieuxVu = false, lieuxInitial = null, lieuxFichiers = null, lieuxOuvre = false;   // ?lieu= de l'annuaire : lu au premier dessin seulement
try {
  var classementLu = localStorage.getItem("build.classement");
  if (CLASSEMENTS.some(function (c) { return c[0] === classementLu; })) classement = classementLu;
} catch (e) {}
var classementMemo = classement;

// Barre creee une fois, au-dessus de #liste (que construitListe vide a chaque dessin), dans une colonne qui
// prend la place de #liste dans la grille .disposition.
var lieuxBarre = (function () {
  var boutons = h("span", {"class": "methode", role: "group", "aria-label": "Classer par"});
  CLASSEMENTS.forEach(function (c) {
    var b = h("button", {type: "button", "data-classement": c[0], texte: c[1]});
    b.onclick = function () { lieuxClasse(c[0]); };
    boutons.appendChild(b);
  });
  var filtre = h("input", {"class": "l-filtre", type: "search", placeholder: "Filtrer par nom…", autocomplete: "off",
                           spellcheck: "false", "aria-label": "Filtrer les environnements par nom"});
  filtre.oninput = function () {
    var actif = !!filtre.value.trim();
    if (actif && !lieuxAvantFiltre) lieuxAvantFiltre = Object.assign({}, lieuxOuverts());
    lieuxMaj();
    if (actif) lieuxOuvreFiltre();
    else if (lieuxAvantFiltre) { lieuxRestaure(lieuxAvantFiltre, true); lieuxAvantFiltre = null; }
  };
  var astuce = h("span", {"class": "discret", texte: "Mes bases et l'amont restent en bas."});
  var masques = h("div", {"class": "l-masques", role: "status", hidden: "hidden"});
  var liste = $("liste"), colonne = h("div", {"class": "l-colonne"});
  liste.parentNode.insertBefore(colonne, liste);
  colonne.appendChild(h("div", {"class": "l-barre"}, h("span", {"class": "discret", texte: "Classer par"}), boutons, filtre, astuce));
  colonne.appendChild(masques);
  colonne.appendChild(liste);
  return {boutons: boutons, filtre: filtre, astuce: astuce, masques: masques, colonne: colonne};
})();

function lieuxClasse(c, sansMemoire) {
  classement = c;
  if (!sansMemoire) try { localStorage.setItem("build.classement", c); classementMemo = c; } catch (e) {}
  if (!envs.length) return lieuxMaj();
  var ouverts = lieuxOuverts();
  construitListe({envs: envs, lieux: lieuxTable});
  lieuxRestaure(ouverts);
  if (lieuxBarre.filtre.value.trim()) lieuxOuvreFiltre();
}

// Memoire d'ouverture de la visite : chaque details de la liste, par sa cle (famille, sous-groupe ou groupe).
function lieuxCle(d) {
  return d.getAttribute("data-famille") || d.getAttribute("data-sous-groupe") || "groupe:" + d.getAttribute("data-groupe");
}
function lieuxOuverts() {
  document.querySelectorAll("#liste details").forEach(function (d) { lieuxMemo[lieuxCle(d)] = d.open; });
  return lieuxMemo;
}
// exact : rendre l'etat tel quel (filtre vide) ; sinon comme chargeEnvs avant : un details reste ouvert s'il l'etait
// ou si le dessin l'ouvre (coche).
function lieuxRestaure(o, exact) {
  document.querySelectorAll("#liste details").forEach(function (d) {
    var k = lieuxCle(d);
    if (k in o) d.open = exact ? o[k] : o[k] || d.open;
  });
}
function lieuxOuvreFiltre() {
  if (classement === "famille") return;
  document.querySelectorAll("#liste details[data-groupe]").forEach(function (d) { if (!d.hidden) d.open = true; });
}

function lieuVisible(e) {
  var f = lieuxBarre.filtre.value.trim().toLowerCase();
  return !f || e.nom.toLowerCase().indexOf(f) >= 0;
}

// Lieu venu de l'annuaire (?lieu=), au PREMIER dessin seulement : classement Lieu pour la visite (le classement
// memorise n'est pas ecrit), groupe du lieu ouvert, bandeau. Ne coche rien. La croix rend le classement memorise.
function lieuxArrivee() {
  if (lieuxVu || !lieuxTable.length) return;
  lieuxVu = true;
  lieuxInitial = lieuxFichiers = lieuDemande(lieuxTable);
  if (!lieuxInitial) return;
  var libelle = lieuxTable.filter(function (l) { return l[0] === lieuxInitial; })[0][1];
  classement = "lieu";
  lieuxOuvre = true;                            // le groupe du lieu s'ouvre au premier dessin seulement
  bandeauLieu(lieuxBarre.colonne, libelle, function () { lieuxInitial = lieuxFichiers = null; lieuxClasse(classementMemo, true); });
}
// Premiere carte du lieu d'arrivee (cochee de preference), ou null : choix initial des onglets Fichiers, Memoire, Sauvegardes.
function lieuxPremiere(cartes) {
  var d = lieuxInitial ? cartes.filter(function (e) { return e.lieu === lieuxInitial; }) : [];
  return d.filter(function (e) { return choix[e.nom] && choix[e.nom].coche; })[0] || d[0] || null;
}

// Branchement de construitListe : false en Famille (dessin d'aujourd'hui), sinon les groupes sont poses dans `liste`.
function lieuxGroupes(liste, membres, donnees) {
  lieuxTable = donnees.lieux || lieuxTable;
  lieuxCases = [];
  lieuxArrivee();
  if (classement === "famille") return false;
  var parLieu = classement === "lieu";
  var cle = function (e) { return (parLieu ? e.lieu : e.puce) || ""; };
  var libelles = {};
  var ordre = parLieu ? lieuxTable.map(function (l) { libelles[l[0]] = l[1]; return l[0]; }) : ORDRE_PUCES.slice();
  membres.forEach(function (e) { if (ordre.indexOf(cle(e)) < 0) ordre.push(cle(e)); });   // hors table : code brut, en dernier
  ordre.forEach(function (k) {
    var groupe = membres.filter(function (e) { return cle(e) === k; });
    if (!groupe.length) return;
    var caseG = h("input", {type: "checkbox", "class": "l-case", "aria-label": "Cocher ou décocher les cartes visibles du groupe",
                            title: "Coche ou décoche les cartes visibles du groupe (celles que le filtre laisse voir)"});
    var compte = h("span", {"class": "compte"});
    var det = h("details", {"class": "famille", "data-groupe": k}, h("summary", {}, caseG, h("span", {texte: libelles[k] || k || "Autres"}), compte));
    det.open = (lieuxOuvre && k === lieuxInitial) || groupe.some(function (e) { return choix[e.nom].coche; });
    caseG.onchange = function () {
      groupe.filter(lieuVisible).forEach(function (e) { choix[e.nom].coche = caseG.checked; ui[e.nom].caseEnv.checked = caseG.checked; });
      majTout();
    };
    groupe.forEach(function (e) { det.appendChild(ligneEnv(e)); });
    det._compte = [compte, groupe];               // compteur ecrit par majComptes, sur tout le groupe
    lieuxCases.push([caseG, groupe]);
    liste.appendChild(det);
  });
  lieuxOuvre = false;
  return true;
}

// Branchement de majComptes (et saisie du filtre).
function lieuxMaj() {
  lieuxBarre.boutons.querySelectorAll("button").forEach(function (b) {
    b.setAttribute("aria-pressed", String(b.getAttribute("data-classement") === classement));
  });
  lieuxBarre.astuce.hidden = classement === "famille";
  Object.keys(ui).forEach(function (nom) { ui[nom].ligne.hidden = !lieuVisible(parNom[nom]); });
  document.querySelectorAll("#liste details").forEach(function (d) { d.hidden = !d.querySelector(".env:not([hidden])"); });
  lieuxCases.forEach(function (g) {                // etat calcule sur les cartes VISIBLES : rien ne se coche a l'insu
    var vis = g[1].filter(lieuVisible), n = vis.filter(function (e) { return choix[e.nom].coche; }).length;
    g[0].checked = n > 0 && n === vis.length;
    g[0].indeterminate = n > 0 && n < vis.length;
  });
  var caches = envs.filter(function (e) { return choix[e.nom].coche && !lieuVisible(e); }).length;
  lieuxBarre.masques.hidden = !caches;
  lieuxBarre.masques.textContent = caches > 1 ? caches + " envs cochés masqués par le filtre partiront au lancement" :
                                                "1 env coché masqué par le filtre partira au lancement";
}
lieuxMaj();
"""
