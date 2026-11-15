"""Menage du depot : rouvrir un rapport sauvegarde (A4 du plan menage-appliquer). Bloc HTML et JS ajoutes a menage_page.PAGE.

La page redemarree n'a aucun rapport en memoire ; les rapports vivent hors depot (menage_lancement.Audit._garde_rapport). La liste vient de
GET /rapports, l'ouverture de POST /rapports/ouvrir {nom} : le serveur revalide et recontre-verifie par git, la page n'envoie qu'un nom de la liste.
"""

HTML = """
 <section class="carte"><h2>Rapports sauvegardés <span class="doux petit" id="n-rapports"></span></h2>
  <p class="doux petit">Rouvrir un audit déjà fait, sans payer un nouvel audit : le rapport est revalidé et recontrôlé par git à l'ouverture.</p>
  <label class="champ"><span>Rapport</span><select id="p-rapport"></select></label>
  <div class="ligne"><button class="btn" id="b-rouvre" disabled>Rouvrir ce rapport</button></div>
 </section>
"""

JS = r"""
function chargeRapports() {
  return api("GET", "/rapports").then(function (r) {
    var s = $("p-rapport"); vide(s);
    var l = r.ok ? r.donnees.rapports : [];
    l.forEach(function (x) {
      var o = el("option", null, x.date + " · " + (x.propositions == null ? "illisible" : x.propositions + " proposition(s)") + " · " + x.nom);
      o.value = x.nom; s.appendChild(o);
    });
    $("b-rouvre").disabled = !l.length;
    $("n-rapports").textContent = l.length ? "(" + l.length + ")" : "(aucun)";
  });
}
function rouvre() {
  var nom = $("p-rapport").value; if (!nom) return;
  var b = $("b-rouvre"), t0 = Date.now(), tic;
  b.disabled = true; b.textContent = "Ouverture…"; $("p-rapport").disabled = true;
  function attente() { message("en", "Ouverture du rapport : contrôle de chaque proposition par git, depuis " + Math.round((Date.now() - t0) / 1000) + " s (jusqu'à une minute)…"); }
  attente(); tic = setInterval(attente, 1000);
  api("POST", "/rapports/ouvrir", {nom: nom}).then(function (r) {
    clearInterval(tic); b.textContent = "Rouvrir ce rapport"; b.disabled = false; $("p-rapport").disabled = false;
    if (!r.ok) { message("ko", r.texte); return; }
    S.demandes = null; S.appliques = []; S.lot.ids = []; S.lot.apercu = null;      // identifiants et « appliquees » de l'ancien rapport : git fait foi, la contre-verification vient d'etre refaite
    S.gen++; chargeRapport(); message("ok", r.donnees.message + ".");
  });
}
$("b-rouvre").onclick = rouvre;
chargeRapports();
"""
