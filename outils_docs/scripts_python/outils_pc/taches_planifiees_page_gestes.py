"""Gestes de la page « Taches planifiees » (A4) : boutons activer / desactiver, heure, lancer, arreter, choix des envs. CSS et JS, inseres par taches_planifiees_page.

Meme regle que la page : tout ce qui vient du serveur (noms d'env, messages) s'affiche par textContent (helper `el`), jamais par innerHTML.
Les actions qui lancent, arretent ou ecrivent dans le depot passent par un bouton a DEUX TEMPS (1er clic = armer, 2e = confirmer, 6 s) : pas de
fenetre confirm() du navigateur. Les gestes partent en POST /geste avec l'en-tete X-Taches: 1 (taches_planifiees_web.py).
Sonde : test_taches_planifiees_page_chrome.py ; routes : test_taches_planifiees_post.py.
"""

CSS_GESTES = """
.gestes{border-top:1px solid var(--bord);margin-top:10px;padding-top:6px}
.rang{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:6px 0}
.btn.danger{border-color:var(--rouge);color:var(--rouge)}
.envs{columns:2 190px;column-gap:14px;margin:6px 0} .envs label{display:block;overflow-wrap:anywhere;margin:1px 0;cursor:pointer}
details.bloc{margin:6px 0} details.bloc summary{cursor:pointer}
input[type=time]{font:inherit;padding:4px 6px;border:1px solid var(--btn-bord);border-radius:6px;background:var(--btn);color:inherit}
.msg{margin:6px 0;min-height:1em;overflow-wrap:anywhere}
"""

JS_GESTES = r"""
var messages = { pc: null, github: null };

function post(voie, geste, valeur) {
  return fetch("/geste", { method: "POST", headers: { "Content-Type": "application/json", "X-Taches": "1" },
    body: JSON.stringify({ voie: voie, geste: geste, valeur: valeur === undefined ? null : valeur }) }).then(function (r) {
    return r.text().then(function (t) {
      if (!r.ok) throw new Error(t || ("HTTP " + r.status));
      return t ? JSON.parse(t) : {};
    });
  });
}
var occupe = { pc: false, github: false };      // un geste a la fois par voie : pas de double envoi par clics repetes
function affiche(zone, voie, texte, ko) {
  messages[voie] = { texte: texte, ko: ko };
  // la zone VIVANTE : un rechargement des cartes a pu remplacer celle que le geste avait capturee
  var vivante = document.querySelector("#" + (voie === "pc" ? "pc" : "gh") + " .msg") || zone;
  vivante.textContent = texte; vivante.className = "msg " + (ko ? "alerte" : "doux");
}
function geste(zone, voie, nom, valeur, dit, relit) {
  if (occupe[voie]) return;
  occupe[voie] = true;
  affiche(zone, voie, "En cours...", false);
  post(voie, nom, valeur).then(function (r) {
    occupe[voie] = false;
    affiche(zone, voie, dit(r.resultat || {}), false);
    if (relit !== false) charge(true);
  }).catch(function (x) { occupe[voie] = false; affiche(zone, voie, x.message, true); });
}
function deuxTemps(texte, attention, fn) {
  var b = el("button", "btn", texte), minuteur = null, arme = 0;
  function repos() { minuteur = null; b.textContent = texte; b.className = "btn"; }
  b.onclick = function () {
    if (minuteur === null) { arme = Date.now(); minuteur = setTimeout(repos, 6000); b.textContent = "Confirmer : " + attention; b.className = "btn danger"; return; }
    if (Date.now() - arme < 500) return;          // double-clic reflexe : la confirmation demande un vrai 2e geste
    clearTimeout(minuteur); repos(); fn();
  };
  return b;
}
function casesEnvs(voie, tous, exclus, zone, boutons) {
  var d = el("details", "bloc"), n = tous.length - exclus.length;
  d.appendChild(el("summary", null, "Envs compilés la nuit (" + n + " sur " + tous.length + ")"));
  var grille = el("div", "envs"), cases = [];
  tous.forEach(function (nom) {
    var l = el("label"), c = document.createElement("input");
    c.type = "checkbox"; c.checked = exclus.indexOf(nom) < 0; c.dataset.env = nom; cases.push(c);
    l.appendChild(c); l.appendChild(document.createTextNode(" " + nom)); grille.appendChild(l);
  });
  d.appendChild(grille);
  var rang = el("div", "rang"), tout = el("button", "btn", "Tout cocher"), rien = el("button", "btn", "Tout décocher");
  tout.onclick = function () { cases.forEach(function (c) { c.checked = true; }); };
  rien.onclick = function () { cases.forEach(function (c) { c.checked = false; }); };
  rang.appendChild(tout); rang.appendChild(rien); boutons(rang, function () {
    return cases.filter(function (c) { return !c.checked; }).map(function (c) { return c.dataset.env; });
  });
  d.appendChild(rang);
  return d;
}

function blocGestes(c, voie, existe, actif, e, exclus) {
  var z = el("div", "gestes"), zone = el("div", "msg");
  z.appendChild(el("h3", "petit", "Gestes"));
  var r1 = el("div", "rang"), ba = el("button", "btn", actif ? "Désactiver la planification" : "Activer la planification");
  ba.disabled = !existe;
  ba.onclick = function () {
    geste(zone, voie, actif ? "desactive" : "active", null, function () { return actif ? "Planification désactivée." : "Planification activée."; });
  };
  r1.appendChild(ba);
  if (voie === "pc" && existe) {
    var h = document.createElement("input"); h.type = "time"; h.setAttribute("aria-label", "Heure de la compilation de nuit"); h.value = String(e.pc.tache.heure || "02:00").slice(0, 5);
    var bh = el("button", "btn", "Changer l'heure");
    bh.onclick = function () {
      geste(zone, voie, "heure", h.value, function (t) { return "Heure changée, prochaine exécution : " + (t.prochaine || "-"); });
    };
    r1.appendChild(h); r1.appendChild(bh);
  }
  z.appendChild(r1);
  var r2 = el("div", "rang");
  r2.appendChild(deuxTemps("Lancer maintenant", voie === "pc" ? "compiler tous les envs cochés sur ce PC" : "lancer le workflow sur GitHub", function () {
    geste(zone, voie, "lancer", null, function () {
      return voie === "pc" ? "Lancé. Suivez-le sur la page Build (port 7700)." : "Lancement demandé : le run apparaît dans la liste dans quelques secondes.";
    });
  }));
  r2.appendChild(deuxTemps("Arrêter la compilation en cours", voie === "pc" ? "arrêt immédiat de la série de la page Build, même lancée à la main" : "annuler les runs en cours", function () {
    geste(zone, voie, "arreter", null, function (t) { return voie === "pc" ? "Arrêt immédiat demandé." : "Annulé : " + (t.annules || []).join(", "); });
  }));
  z.appendChild(r2);
  z.appendChild(casesEnvs(voie, e.envs, exclus, zone, function (rang, exclusDe) {
    if (voie === "pc") {
      var b = el("button", "btn", "Enregistrer la sélection");
      b.onclick = function () { geste(zone, voie, "envs", exclusDe(), function (t) { return "Sélection enregistrée (" + t.apres.length + " env exclu(s))."; }); };
      rang.appendChild(b);
      return;
    }
    var ap = el("button", "btn", "Aperçu des changements");
    ap.onclick = function () {
      geste(zone, voie, "envs_apercu", exclusDe(), function (t) {
        if (t.inchange) return "Aucun changement par rapport au dépôt.";
        return "Exclus ajoutés : " + (t.ajoutes.join(", ") || "aucun") + " ; retirés : " + (t.retires.join(", ") || "aucun") + ".";
      }, false);
    };
    rang.appendChild(ap);
    rang.appendChild(deuxTemps("Écrire, commiter et pousser", "écrit, commite et pousse seulement outils_docs/compilations_nuit/envs_github.json vers origin/development", function () {
      geste(zone, voie, "envs", exclusDe(), function (t) {
        return t.inchange ? "Aucun changement." : "Poussé (commit " + t.commit + "). Lancez ensuite le workflow pour que GitHub en tienne compte.";
      });
    }));
  }));
  if (e.github_exclus_erreur && voie === "github") z.appendChild(el("p", "panne", e.github_exclus_erreur));
  var m = messages[voie]; if (m) { zone.textContent = m.texte; zone.className = "msg " + (m.ko ? "alerte" : "doux"); }
  z.appendChild(zone); c.appendChild(z);
}
function gestesPc(c, e) { blocGestes(c, "pc", e.pc.tache.existe, e.pc.tache.actif, e, e.pc.config.envs_exclus); }
function gestesGh(c, e) { blocGestes(c, "github", e.github.workflow != null, e.github.workflow === "active", e, e.github_exclus); }
"""
