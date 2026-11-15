"""Consignes de creation dans la page de l'atelier des visuels : lien « Consignes » (le fichier, en lecture seule) et rappel des regles
qui concernent l'element en cours d'edition (voyant, valeur, liaison) plus le jour et la nuit.

Les regles viennent de GET /consignes/regles, relu a chaque selection : une regle ajoutee a CONSIGNES_VISUELS.md apparait sans relancer l'outil.
Tout texte est pose par textContent (jamais innerHTML). Point d'entree : AV.rappel(element | null), appele par atelier_visuels_page_elements.py::panneau.
"""

HTML_LIEN = "<a class='btn' id='avc-lien' href='/consignes' target='_blank' rel='noopener'>Consignes</a>"

HTML_CONSIGNES = (
    "<div class='pan' id='avc-panel'><h2>Consignes</h2><div class='g'>"
    "<div id='avc-rappel' class='doux'>Sélectionnez un point chaud pour voir les règles qui le concernent.</div>"
    "<a href='/consignes' target='_blank' rel='noopener'>Toutes les consignes (fichier)</a></div></div>"
)

JS_CONSIGNES = r"""
(function () {
  var AV = window.AV, $ = function (i) { return document.getElementById(i); }, seq = 0;
  var INVITE = 'Sélectionnez un point chaud pour voir les règles qui le concernent.';
  var TITRES = {voyant: 'Voyant', valeur: 'Valeur', liaison: 'Liaison'};
  function ligne(zone, titre, texte) {
    var d = document.createElement('div'), b = document.createElement('strong');
    b.textContent = titre; d.appendChild(b); d.appendChild(document.createTextNode(' : ' + texte));
    d.style.margin = '4px 0'; zone.appendChild(d);
  }
  function pose(e, r) {
    var zone = $('avc-rappel'), noms = (e && r.par_type[e.type]) || [], vus = 0;
    while (zone.firstChild) zone.removeChild(zone.firstChild);
    zone.className = '';
    if (!e) { zone.className = 'doux'; zone.textContent = INVITE; return; }
    var t = document.createElement('div'); t.textContent = (TITRES[e.type] || 'Élément') + ' ' + e.id + ' : règles à respecter';
    t.className = 'doux'; zone.appendChild(t);
    r.organes.forEach(function (o) { if (noms.indexOf(o.nom) >= 0) { ligne(zone, o.nom, o.regle); vus++; } });
    if (e.type === 'liaison') r.clic.forEach(function (c) { ligne(zone, 'Commande', c); vus++; });
    r.jour_nuit.forEach(function (c) { ligne(zone, 'Jour et nuit', c); vus++; });
    if (!vus) zone.textContent = 'Aucune règle pour cet élément.';
  }
  AV.rappel = function (e) {
    var n = ++seq;
    fetch('/consignes/regles', {cache: 'no-store'}).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (r) { if (n === seq) pose(e, r); },
        function () { if (n === seq) { var z = $('avc-rappel'); z.textContent = 'Consignes illisibles pour le moment.'; z.className = 'alerte'; } });
  };
})();
"""
