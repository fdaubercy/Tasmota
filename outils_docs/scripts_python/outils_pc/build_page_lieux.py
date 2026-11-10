"""Onglet Build de la page build_web.py : bascule « Classer par » Famille / Lieu / Puce (modele D).

Spec docs/superpowers/specs/2026-11-10-classement-par-lieu-design.md §5 ; maquette outils_docs/filtre_lieu/modele-D.png.
Insere dans build_page.PAGE par les marques /*CSS_LIEUX*/ et /*JS_LIEUX*/. Deux branchements dans build_page.py :
  - construitListe appelle lieuxGroupes(liste, membres, donnees) pour la famille « cartes » : en Lieu ou Puce, les
    cartes vont dans un details.famille par groupe (attribut data-groupe, pas data-famille : chargeEnvs ne restaure
    pas leur ouverture, la regle « ouvert s'il contient un coche » est recalculee a chaque dessin) ;
  - majComptes appelle lieuxMaj : filtre par nom, etat des cases d'en-tete, avertissement des coches masques.
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
var classement = "famille", lieuxTable = [], lieuxCases = [];
try {
  var classementLu = localStorage.getItem("build.classement");
  if (CLASSEMENTS.some(function (c) { return c[0] === classementLu; })) classement = classementLu;
} catch (e) {}

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
  filtre.oninput = lieuxMaj;
  var astuce = h("span", {"class": "discret", texte: "Mes bases et l'amont restent en bas."});
  var masques = h("div", {"class": "l-masques", role: "status", hidden: "hidden"});
  var liste = $("liste"), colonne = h("div", {"class": "l-colonne"});
  liste.parentNode.insertBefore(colonne, liste);
  colonne.appendChild(h("div", {"class": "l-barre"}, h("span", {"class": "discret", texte: "Classer par"}), boutons, filtre, astuce));
  colonne.appendChild(masques);
  colonne.appendChild(liste);
  return {boutons: boutons, filtre: filtre, astuce: astuce, masques: masques};
})();

function lieuxClasse(c) {
  classement = c;
  try { localStorage.setItem("build.classement", c); } catch (e) {}
  if (envs.length) construitListe({envs: envs, lieux: lieuxTable});
  else lieuxMaj();
}

function lieuVisible(e) {
  var f = lieuxBarre.filtre.value.trim().toLowerCase();
  return !f || e.nom.toLowerCase().indexOf(f) >= 0;
}

// Branchement de construitListe : false en Famille (dessin d'aujourd'hui), sinon les groupes sont poses dans `liste`.
function lieuxGroupes(liste, membres, donnees) {
  lieuxTable = donnees.lieux || lieuxTable;
  lieuxCases = [];
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
    det.open = groupe.some(function (e) { return choix[e.nom].coche; });
    caseG.onchange = function () {
      groupe.filter(lieuVisible).forEach(function (e) { choix[e.nom].coche = caseG.checked; ui[e.nom].caseEnv.checked = caseG.checked; });
      majTout();
    };
    groupe.forEach(function (e) { det.appendChild(ligneEnv(e)); });
    det._compte = [compte, groupe];               // compteur ecrit par majComptes, sur tout le groupe
    lieuxCases.push([caseG, groupe]);
    liste.appendChild(det);
  });
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
