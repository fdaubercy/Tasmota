"""Onglet « Fichiers » de la page Build et televersement (A15, spec choix 24, maquette E) : CSS, HTML et JS
inseres dans build_page.PAGE a la place des marques /*CSS_FICHIERS*/, <!--VUE_FICHIERS--> et /*JS_FICHIERS*/.

A gauche, la carte destinataire (envs « Mes cartes » envoyables en OTA, adresse partagee avec l'onglet Build :
`choix[env].ip`) ; en haut, « Préparer la liste » (POST /lancer, action buildfs) et la date de l'image ; puis
Dossiers / fichiers de l'image (GET /fichiers?env=) / panier « À envoyer » avec ses options, et l'envoi
(POST /lancer, action « fichiers », jeton de la liste). Les deux lancements portent `onglet: "fichiers"` :
le serveur n'ecrit pas les derniers choix de l'onglet Build.
Transport (A16, spec choix 25 a 28) : HTTP (adresse de la carte) ou MQTT (broker, module fsMqtt.be de la carte, adresse
inutile) ; « Effacer tout le FS avant l'envoi » : MQTT seulement, confirmation, puis TOUTE l'image part.
Avancement dans l'onglet : barre en pourcentage et journal des etapes, nourris par les evenements du flux du
lancement parti d'ici (fichiersEvenement, appele par traite() de build_page). Le Suivi commun reste dessous.
Tout texte venu du serveur passe par textContent (fonction h de build_page).
"""

CSS = r"""
  [hidden]{display:none!important}
  .onglets{display:flex;gap:4px;border-bottom:1px solid var(--bord);margin:0 0 12px}
  .onglets button{font:inherit;font-size:13.5px;padding:7px 14px;border:1px solid transparent;border-bottom:0;border-radius:6px 6px 0 0;
    background:none;color:var(--doux);cursor:pointer;margin-bottom:-1px}
  .onglets button[aria-selected="true"]{background:var(--carte);border-color:var(--bord);color:var(--texte);font-weight:600}
  .onglets button:focus-visible{outline:2px solid var(--bleu);outline-offset:-2px}
  .f-grille{display:grid;grid-template-columns:250px minmax(0,1fr);gap:12px;align-items:start}
  .f-droite{display:flex;flex-direction:column;gap:10px;min-width:0}
  .f-trois{display:grid;grid-template-columns:170px minmax(0,1fr) 240px;gap:10px;align-items:start}
  .f-tete{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
  .f-carte{display:grid;grid-template-columns:auto minmax(0,1fr);column-gap:8px;padding:7px 4px;border-top:1px solid var(--bord)}
  .f-carte.coche{background:var(--bleu-fond)}
  .f-carte input[type=radio]{margin:2px 0 0;width:15px;height:15px}
  .f-carte .nom{font-family:ui-monospace,Consolas,monospace;font-size:12.5px;overflow-wrap:anywhere;cursor:pointer}
  .f-carte .champ{width:100%;font:inherit;font-size:12.5px;padding:3px 6px;margin-top:4px;background:var(--btn);color:var(--texte);
    border:1px solid var(--btn-bord);border-radius:4px}
  .f-carte .champ.requis{border-color:var(--rouge);background:var(--rouge-fond)}
  .f-dossier{display:flex;justify-content:space-between;gap:8px;width:100%;text-align:left;font:inherit;font-size:12.5px;padding:4px 6px;
    border:0;border-radius:4px;background:none;color:var(--texte);cursor:pointer;overflow-wrap:anywhere}
  .f-dossier[aria-pressed="true"]{background:var(--bleu-fond);color:var(--bleu);font-weight:600}
  .f-defile{overflow-x:auto}
  table.f{width:100%;border-collapse:collapse;font-size:12.5px}
  table.f th{text-align:left;font-weight:600;color:var(--doux);padding:4px 6px}
  table.f td{padding:4px 6px;border-top:1px solid var(--bord);vertical-align:top}
  table.f tr.coche td{background:var(--bleu-fond)}
  table.f td.chemin,.f-panier .chemin{font-family:ui-monospace,Consolas,monospace;overflow-wrap:anywhere}
  table.f td.nombre{white-space:nowrap;text-align:right}
  .f-recent{color:var(--orange)}
  .f-panier{list-style:none;margin:0;padding:0;font-size:12.5px;max-height:260px;overflow:auto}
  .f-panier li{display:flex;justify-content:space-between;gap:8px;padding:3px 0;border-top:1px solid var(--bord)}
  .f-journal{font:11.5px/1.45 ui-monospace,Consolas,monospace;color:var(--doux);max-height:220px;overflow:auto;margin:6px 0 0;padding-left:22px}
  @media (max-width:1000px){.f-trois{grid-template-columns:1fr}}
  @media (max-width:820px){.f-grille{grid-template-columns:1fr}}
"""

HTML = r"""
  <div id="vue-fichiers" class="f-grille" role="tabpanel" aria-labelledby="onglet-fichiers" hidden>
    <aside class="carte">
      <h2>Carte destinataire</h2>
      <div id="f-cartes"><div class="vide">Lecture des environnements…</div></div>
      <p class="discret" style="margin:8px 0 0">Envoi par le réseau (OTA, HTTP). Esclave du range extender : adresse
        du maître:port (redirection posée et nom d'hôte vérifié avant l'envoi).</p>
    </aside>
    <section class="f-droite">
      <div class="carte">
        <div class="f-tete">
          <button id="f-preparer" class="btn" type="button" disabled
            title="Construit l'image du FS de la carte (pio run -t buildfs) à partir des fichiers du dépôt">Préparer la liste</button>
          <span id="f-image" class="doux">Choisir une carte à gauche.</span>
        </div>
        <div id="f-erreur" class="erreur"></div>
      </div>
      <div class="f-trois">
        <div class="carte"><h2>Dossiers</h2><div id="f-dossiers"></div></div>
        <div class="carte"><h2>Fichiers de l'image</h2><div id="f-table"></div></div>
        <div class="carte pile">
          <h2>À envoyer</h2>
          <div id="f-panier"></div>
          <div role="radiogroup" aria-label="Transport">
            <label class="action" title="POST /ufsu vers l'adresse de la carte (ou du maître:port)">
              <input type="radio" name="f-transport" value="http" checked> HTTP (adresse de la carte)</label>
            <label class="action" title="Par le broker de user_config_override.h, vers le module fsMqtt.be de la carte">
              <input type="radio" name="f-transport" value="mqtt"> MQTT (module fsMqtt.be)</label>
          </div>
          <label class="action" title="MQTT seulement : tout le FS de la carte est supprimé, puis toute l'image est envoyée">
            <input type="checkbox" id="f-effacer" disabled> Effacer tout le FS avant l'envoi</label>
          <label class="action"><input type="checkbox" id="f-berry"> Recharger Berry (BrRestart)</label>
          <label class="action"><input type="checkbox" id="f-restart"> Redémarrer la carte (Restart 1)</label>
          <div id="f-note" class="discret"></div>
          <button id="f-envoyer" class="btn p" type="button" disabled>Envoyer 0 fichier</button>
          <div id="f-pourquoi" class="discret"></div>
          <div id="f-refus" class="erreur"></div>
        </div>
      </div>
      <div id="f-suivi" class="carte" aria-live="polite" hidden>
        <h2 id="f-suivi-titre"></h2>
        <div class="rang">
          <div class="libelle"><span id="f-etape"></span><span id="f-pourcent"></span></div>
          <div id="f-barre" class="barre" role="progressbar" aria-labelledby="f-suivi-titre" aria-valuemin="0" aria-valuemax="100"><span></span></div>
        </div>
        <ol id="f-journal" class="f-journal"></ol>
      </div>
    </section>
  </div>
"""

JS = r"""
// ---------- onglet « Fichiers » (A15, build_page_fichiers.py) ----------
var F = {env: "", liste: null, dossier: null, coches: {}, berryTouche: false, prepa: false, suivi: null, lecture: 0,
         tout: null, vus: [], dessin: null};

function montreOnglet(nom) {
  var fichiers = nom === "fichiers";
  $("vue-build").hidden = fichiers;
  $("vue-fichiers").hidden = !fichiers;
  $("onglet-build").setAttribute("aria-selected", String(!fichiers));
  $("onglet-fichiers").setAttribute("aria-selected", String(fichiers));
  try { localStorage.setItem("build-onglet", nom); } catch (e) {}
  if (fichiers) fichiersCartes();
}
$("onglet-build").onclick = function () { montreOnglet("build"); };
$("onglet-fichiers").onclick = function () { montreOnglet("fichiers"); };

function parentDe(chemin) { var i = chemin.lastIndexOf("/"); return i < 0 ? "" : chemin.slice(0, i); }
function tailleLisible(o) { return o < 1024 ? o + " o" : (o / 1024).toFixed(1).replace(".", ",") + " Ko"; }
function dateLisible(s) {
  return new Date(s * 1000).toLocaleString("fr-FR", {day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"});
}
function choisis() { return F.liste ? F.liste.fichiers.filter(function (f) { return F.coches[f.chemin]; }) : []; }
function transport() { return document.querySelector("input[name=f-transport]:checked").value; }
function effaceFs() { return transport() === "mqtt" && $("f-effacer").checked; }
// Fichiers qui partiront : tous ceux de l'image si l'on efface d'abord, sinon les coches
function aEnvoyer() { return effaceFs() && F.liste ? F.liste.fichiers : choisis(); }

// Cartes destinataires : appelee aussi par construitListe (envs relus). Adresse = celle de l'onglet Build.
function fichiersCartes() {
  if (!envs.length) return;
  var zone = $("f-cartes");
  if (zone.contains(document.activeElement)) return;      // saisie en cours : ne pas lui voler le focus
  zone.textContent = "";
  var cartes = envs.filter(function (e) { return e.famille === "cartes" && e.ota_possible; });
  if (!cartes.length) { zone.appendChild(h("div", {"class": "vide", texte: "Aucune carte envoyable par le réseau."})); return; }
  cartes.forEach(function (e) {
    var c = choix[e.nom];
    var radio = h("input", {type: "radio", name: "f-carte", id: "f-carte-" + e.nom, value: e.nom});
    radio.checked = F.env === e.nom;
    radio.onchange = function () { choisitCarte(e.nom); };
    var champ = h("input", {"class": "champ", type: "text", autocomplete: "off", spellcheck: "false", placeholder: "IP à saisir",
                            "aria-label": "Adresse de " + e.nom, title: "IP, ou IP du maître:port pour un esclave du range extender"});
    champ.value = c.ip;
    champ.classList.toggle("requis", !IPV4.test(c.ip.trim()));
    champ.oninput = function () { c.ip = champ.value; champ.classList.toggle("requis", !IPV4.test(c.ip.trim())); majBoutonsFichiers(); };
    var source = !IPV4.test(c.ip.trim()) ? "adresse à saisir (aucune connue)" : c.ip.trim() !== e.ip ? "adresse saisie pour cette page" :
                 e.ip_source === "maitre" ? "par le maître (range extender, persist)" :
                 e.ip_source === "h" ? "IP fixe de user_config_override.h" : "";
    zone.appendChild(h("div", {"class": "f-carte" + (F.env === e.nom ? " coche" : "")}, radio,
      h("div", {}, h("label", {"for": radio.id, "class": "nom", texte: e.nom}), champ,
        source ? h("div", {"class": "discret", texte: source}) : null)));
  });
}

function choisitCarte(nom) {
  F.env = nom; F.liste = null; F.dossier = null; F.coches = {}; F.berryTouche = false;
  $("f-refus").textContent = "";
  fichiersCartes();
  majFichiers();
  chargeListe();
}

async function chargeListe() {
  var n = ++F.lecture;
  $("f-image").textContent = "Lecture de l'image du FS…";
  var r = await appel("/fichiers?env=" + encodeURIComponent(F.env));
  if (n !== F.lecture) return;                            // une autre carte choisie entre-temps
  F.liste = r.ok && r.donnees ? r.donnees : {image: {present: false}, identite: "", fichiers: [], dossiers: {},
    erreur: "liste indisponible : " + (r.texte || ("HTTP " + r.statut))};
  var presents = {};
  F.liste.fichiers.forEach(function (f) { presents[f.chemin] = true; });
  Object.keys(F.coches).forEach(function (k) { if (!presents[k]) delete F.coches[k]; });   // image reconstruite
  if (F.dossier !== null && !(F.dossier in F.liste.dossiers)) F.dossier = null;
  majFichiers();
}

function cocheFichier(chemin, oui) { if (oui) F.coches[chemin] = true; else delete F.coches[chemin]; }

// Rendu complet (carte choisie, liste lue, dossier) ; une case cochee ne redessine que le panier (majPanier).
function majFichiers() {
  var l = F.liste;
  $("f-image").textContent = !F.env ? "Choisir une carte à gauche." : !l ? "Lecture de l'image du FS…" :
    l.image.present ? "Image du FS du " + dateLisible(l.image.date) + " · " + l.fichiers.length + " fichiers" +
                      (l.identite ? " · " + l.identite : "") :
    "Pas encore d'image du FS pour " + F.env + ".";
  $("f-erreur").textContent = l ? l.erreur : "";
  var zd = $("f-dossiers"), zt = $("f-table");
  zd.textContent = ""; zt.textContent = ""; F.tout = null; F.vus = [];
  if (!l || !l.fichiers.length) {
    zt.appendChild(h("div", {"class": "vide", texte: !F.env ? "Choisir une carte." : !l ? "Lecture…" : "Aucun fichier : préparer la liste."}));
    majPanier();
    return;
  }
  [[null, "Tous", l.fichiers.length]].concat(Object.keys(l.dossiers).sort().map(function (d) {
    return [d, d ? d + "/" : "/ (racine)", l.dossiers[d]];
  })).forEach(function (d) {
    var b = h("button", {type: "button", "class": "f-dossier", "aria-pressed": String(F.dossier === d[0])},
              h("span", {texte: d[1]}), h("span", {"class": "discret", texte: String(d[2])}));
    b.onclick = function () { F.dossier = d[0]; majFichiers(); };
    zd.appendChild(b);
  });
  F.vus = l.fichiers.filter(function (f) { return F.dossier === null || parentDe(f.chemin) === F.dossier; });
  F.tout = h("input", {type: "checkbox", "aria-label": "Tout cocher (fichiers affichés)", title: "Tout cocher (fichiers affichés)"});
  F.tout.onchange = function () {
    var oui = F.tout.checked;
    F.vus.forEach(function (f) { cocheFichier(f.chemin, oui); });
    zt.querySelectorAll("tbody input").forEach(function (c) { c.checked = oui; c.closest("tr").classList.toggle("coche", oui); });
    majPanier();
  };
  var corps = h("tbody", {});
  F.vus.forEach(function (f, i) {
    var cc = h("input", {type: "checkbox", id: "f-f" + i, "data-chemin": f.chemin});
    cc.checked = !!F.coches[f.chemin];
    var tr = h("tr", {"class": cc.checked ? "coche" : ""});
    cc.onchange = function () { cocheFichier(f.chemin, cc.checked); tr.classList.toggle("coche", cc.checked); majPanier(); };
    var etat = h("td", {});
    if (f.plus_recent) etat.appendChild(h("div", {"class": "f-recent", texte: "dépôt plus récent que l'image : préparer à nouveau"}));
    if (f.chemin === "_persist.json") etat.appendChild(h("div", {"class": "discret", texte: "sauvegardé avant l'envoi"}));
    tr.appendChild(h("td", {}, cc));
    tr.appendChild(h("td", {"class": "chemin"}, h("label", {"for": cc.id, texte: f.chemin})));
    tr.appendChild(h("td", {"class": "nombre", texte: tailleLisible(f.taille)}));
    tr.appendChild(h("td", {"class": "nombre", texte: f.depot ? dateLisible(f.depot) : "—",
                            title: f.depot ? "date du fichier dans le dépôt" : "fichier introuvable dans le dépôt"}));
    tr.appendChild(etat);
    corps.appendChild(tr);
  });
  zt.appendChild(h("div", {"class": "f-defile"}, h("table", {"class": "f"},
    h("thead", {}, h("tr", {}, h("th", {}, F.tout), h("th", {texte: "Fichier"}), h("th", {texte: "Taille"}),
                    h("th", {texte: "Dépôt"}), h("th", {texte: "État"}))), corps)));
  majPanier();
}

function majPanier() {
  var liste = choisis(), zp = $("f-panier");
  zp.textContent = "";
  if (F.tout) {
    var n = F.vus.filter(function (f) { return F.coches[f.chemin]; }).length;
    F.tout.checked = n > 0 && n === F.vus.length;
    F.tout.indeterminate = n > 0 && n < F.vus.length;
  }
  if (!liste.length) zp.appendChild(h("div", {"class": "vide", texte: "Aucun fichier coché."}));
  else {
    var ul = h("ul", {"class": "f-panier"});
    liste.forEach(function (f) {
      var x = h("button", {type: "button", "class": "lien", texte: "retirer", "aria-label": "Retirer " + f.chemin});
      x.onclick = function () { cocheFichier(f.chemin, false); majFichiers(); };
      ul.appendChild(h("li", {}, h("span", {"class": "chemin", texte: f.chemin}), x));
    });
    zp.appendChild(ul);
    zp.appendChild(h("div", {"class": "discret", texte: "Total : " + tailleLisible(liste.reduce(function (s, f) { return s + f.taille; }, 0))}));
  }
  if (effaceFs()) liste = aEnvoyer();
  var persist = liste.some(function (f) { return f.chemin === "_persist.json"; });
  // Recharger Berry : coche d'office si un .be ou le persist part, tant que l'utilisateur n'y a pas touche
  if (!F.berryTouche) $("f-berry").checked = persist || liste.some(function (f) { return /\.be$/.test(f.chemin); });
  $("f-note").textContent = (effaceFs() ? "Tout le FS de la carte sera supprimé (persist compris), puis les " + liste.length +
    " fichiers de l'image envoyés. " : "") + (persist ? "_persist.json : le persist de la carte est sauvegardé avant l'envoi, puis rechargé " +
    "(persist.load()) avant tout redémarrage. " : "") + ($("f-restart").checked ? "Le redémarrage recharge aussi Berry." : "");
  majBoutonsFichiers();
}
$("f-berry").onchange = function () { F.berryTouche = true; };
$("f-restart").onchange = function () { $("f-berry").disabled = this.checked; majPanier(); };
$("f-effacer").onchange = function () { majPanier(); };
document.querySelectorAll("input[name=f-transport]").forEach(function (r) {
  r.onchange = function () {
    $("f-effacer").disabled = transport() !== "mqtt";
    if (transport() !== "mqtt") $("f-effacer").checked = false;
    majPanier();
  };
});

// Appelee aussi par majBouton (build_page) : un lancement qui commence ou finit change les boutons.
function majBoutonsFichiers() {
  var l = F.liste, c = F.env ? choix[F.env] : null, occupe = enCours || F.prepa;
  var n = l && l.image.present ? aEnvoyer().length : 0;
  $("f-preparer").disabled = !F.env || occupe;
  $("f-preparer").textContent = F.prepa ? "Préparation…" : "Préparer la liste";
  var manque = !F.env ? "choisir une carte" : occupe ? "un lancement est en cours" :
    transport() === "http" && (!c || !IPV4.test(c.ip.trim())) ? "adresse de la carte à saisir (IPv4, ou IPv4:port par le maître)" :
    !l || !l.image.present ? "préparer la liste" : !n ? "cocher des fichiers" : "";
  $("f-envoyer").disabled = !!manque;
  $("f-envoyer").textContent = (effaceFs() ? "Effacer puis envoyer " : "Envoyer ") + n + " fichier" + (n > 1 ? "s" : "") +
    (transport() === "mqtt" ? " par MQTT" : "");
  $("f-pourquoi").textContent = manque ? "Envoi impossible : " + manque + "." : "";
}

function refusFichiers(r) {
  var ul = h("ul", {});
  (r.texte || ("HTTP " + r.statut)).split(" ; ").forEach(function (m) { ul.appendChild(h("li", {texte: m})); });
  $("f-refus").textContent = "";
  $("f-refus").appendChild(h("div", {texte: "Lancement refusé :"}));
  $("f-refus").appendChild(ul);
}

$("f-preparer").onclick = async function () {
  $("f-refus").textContent = "";
  F.prepa = true;
  majBoutonsFichiers();
  var r = await appel("/lancer", {lignes: [{env: F.env, methode: "com", port: "", ip: ""}], actions: ["buildfs"], onglet: "fichiers"});
  if (r.ok) enCours = true;
  else { F.prepa = false; refusFichiers(r); }
  majBoutonsFichiers();
};

$("f-envoyer").onclick = async function () {
  var c = choix[F.env];
  if (effaceFs() && !confirm("Effacer tout le FS de " + F.env + " : TOUS ses fichiers sont supprimés, persist, autoexec et " +
      "fsMqtt.be compris, puis les " + aEnvoyer().length + " fichiers de l'image sont envoyés par MQTT.\n\nLe persist de la " +
      "carte est sauvegardé avant. Si la carte redémarre entre les deux, elle repart sans Berry : la reprendre en HTTP " +
      "(onglet Fichiers) ou par câble.\n\nContinuer ?")) return;
  $("f-refus").textContent = "";
  $("f-envoyer").disabled = true;
  var r = await appel("/lancer", {lignes: [{env: F.env, methode: "ota", port: "", ip: c.ip.trim()}], actions: ["fichiers"],
    onglet: "fichiers", fichiers: {liste: aEnvoyer().map(function (f) { return f.chemin; }), jeton: F.liste.image.jeton,
                                   transport: transport(), effacer: effaceFs(),
                                   recharger_berry: $("f-berry").checked && !$("f-restart").checked,
                                   redemarrer: $("f-restart").checked}});
  if (r.ok) enCours = true; else refusFichiers(r);
  majBoutonsFichiers();
};

// Evenements du flux (appele par traite) : seul le lancement parti de cet onglet est suivi ici.
function fichiersEvenement(e, rejeu) {
  var s = F.suivi;
  if (e.type === "debut" && e.env === null) {
    var acts = e.actions || [], l0 = (e.lignes || [])[0] || {};
    var genre = acts.length === 1 && acts[0] === "fichiers" ? "envoi" :
                F.prepa && acts.length === 1 && acts[0] === "buildfs" && l0.env === F.env ? "prepa" : "";
    F.suivi = genre ? {genre: genre, env: l0.env, etape: "", pourcent: null, journal: [], statut: "encours"} : null;
  } else if (s && e.env === s.env) {
    if (e.type === "etape") {
      s.etape = e.etape || s.etape;
      s.pourcent = typeof e.pourcent === "number" ? e.pourcent : null;
      var t = (e.etape || "") + (e.detail ? " · " + e.detail : "");
      if (s.journal[s.journal.length - 1] !== t) s.journal.push(t);
    } else if (e.type === "echec") { s.statut = "echec"; s.journal.push("Échec : " + (e.motif || "")); }
    else if (e.type === "fin_env") { s.statut = e.resultat || "succes"; if (s.statut === "succes") s.pourcent = 100; }
  }
  if (e.type === "fin") {
    if (F.suivi && F.suivi.statut === "encours") F.suivi.statut = "arrete";
    if (F.prepa) { F.prepa = false; if (F.suivi && F.suivi.genre === "prepa") chargeListe(); }
    majBoutonsFichiers();
  }
  if (e.type === "ligne" || F.dessin) return;
  F.dessin = setTimeout(function () { F.dessin = null; dessineSuiviFichiers(); }, 60);   // rejeu : un seul dessin
}

function dessineSuiviFichiers() {
  var s = F.suivi;
  $("f-suivi").hidden = !s;
  if (!s) return;
  $("f-suivi-titre").textContent = (s.genre === "envoi" ? "Envoi des fichiers vers " : "Préparation de la liste de ") + s.env +
    " — " + (s.statut === "encours" ? "en cours" : STATUTS[s.statut] || s.statut);
  var p = s.statut === "succes" ? 100 : s.pourcent, barre = $("f-barre");
  barre.className = "barre" + (s.statut === "encours" ? (p === null ? " indet" : "") : " " + ({succes: "succes", echec: "echec"}[s.statut] || "annulee"));
  barre.firstChild.style.width = p === null ? "" : p + "%";
  if (p === null) barre.removeAttribute("aria-valuenow"); else barre.setAttribute("aria-valuenow", String(p));
  $("f-pourcent").textContent = p === null ? "" : p + " %";
  $("f-etape").textContent = s.etape;
  var j = $("f-journal");
  j.textContent = "";
  s.journal.forEach(function (t) { j.appendChild(h("li", {texte: t})); });
  j.scrollTop = j.scrollHeight;
}

try { if (localStorage.getItem("build-onglet") === "fichiers") montreOnglet("fichiers"); } catch (e) {}
"""
