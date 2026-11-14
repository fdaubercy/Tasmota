"""Export de l'atelier des visuels (spec § 2.5) : SVG a telecharger, code SVG, code HTML autonome, PNG. Aucune ecriture au serveur ni au depot.

Le SVG exporte = le fond (dessin a plat, ou photo en data-URI) + les calques dans leur etat simule. Le fragment HTML ajoute un petit
script en ligne (clic = bascule d'etat) : ni requete ni dependance, il ne cite jamais visuel.js de la carte.
Crochets de test : AV.telecharge(nom, blob) et AV.presse(texte) (presse-papiers) sont remplacables.
"""

CSS_EXPORT = """
#avx-panel[hidden]{display:none}
"""

HTML_EXPORT = (
    "<div class='pan' id='avx-panel' hidden><h2>Exporter</h2><div class='g'>"
    "<button type='button' id='avx-svg'>Télécharger le SVG</button><button type='button' id='avx-copie-svg'>Copier le code SVG</button>"
    "<button type='button' id='avx-copie-html'>Copier le code HTML</button><button type='button' id='avx-png'>Télécharger le PNG</button>"
    "<div class='doux'>Rien n'est écrit au serveur ni au dépôt. Les points chauds sont montrés dans leur état simulé.</div></div></div>"
)

JS_EXPORT = r"""
(function () {
  var AV = window.AV, F = AV_FORMES, Cq = AV_CALQUES, $ = function (i) { return document.getElementById(i); };
  function info(t, mauvais) { var m = $('av-msg'); m.textContent = t; m.className = mauvais ? 'mauvais' : 'doux'; }
  function rien() {
    if (AV.mode === 'plat' ? !AV.formes.some(function (f) { return !f.zone; }) : !AV.src) { info('Rien à exporter : dessinez ou importez une photo d\'abord', true); return true; }
    return false;
  }
  AV.svgComplet = function () {
    var cal = AV.calques(), s, q;
    if (AV.mode === 'plat') return AV.svg().replace(/<\/svg>$/, cal + '</svg>');
    q = $('av-qualite').value / 100;
    s = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + AV.larg + ' ' + AV.haut + '" width="' + AV.larg + '" height="' + AV.haut + '">';
    s += F.ser(['image', {href: AV.fondPhoto().toDataURL('image/webp', q), x: 0, y: 0, width: AV.larg, height: AV.haut}]);
    return s + cal + '</svg>';
  };
  AV.fragmentHtml = function () {
    return '<div class="av-visuel" style="max-width:' + AV.larg + 'px">' + AV.svgComplet() + '<script>' + Cq.SCRIPT + '<\/script></div>';
  };
  AV.telecharge = function (nom, blob) {
    var a = document.createElement('a'), u = URL.createObjectURL(blob);
    a.href = u; a.download = nom; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(u); }, 10000);
  };
  AV.presse = function (texte) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(texte);
    return Promise.reject(new Error('presse-papiers indisponible'));
  };
  function copie(texte, quoi) {
    Promise.resolve().then(function () { return AV.presse(texte); }).then(function () { info(quoi + ' copié (' + texte.length + ' caractères)', false); })
      .catch(function () { info('Copie refusée par le navigateur : utilisez le téléchargement', true); });
  }
  function nom() { return 'visuel-' + (AV.env || 'carte'); }
  $('av-export').addEventListener('click', function () {
    var p = $('avx-panel'); p.hidden = !p.hidden; this.setAttribute('aria-expanded', p.hidden ? 'false' : 'true');
  });
  $('avx-svg').addEventListener('click', function () { if (!rien()) AV.telecharge(nom() + '.svg', new Blob([AV.svgComplet()], {type: 'image/svg+xml'})); });
  $('avx-copie-svg').addEventListener('click', function () { if (!rien()) copie(AV.svgComplet(), 'Code SVG'); });
  $('avx-copie-html').addEventListener('click', function () { if (!rien()) copie(AV.fragmentHtml(), 'Code HTML'); });
  $('avx-png').addEventListener('click', function () {
    if (rien()) return;
    var u = URL.createObjectURL(new Blob([AV.svgComplet()], {type: 'image/svg+xml'})), img = new Image();
    img.onload = function () {
      var c = document.createElement('canvas'); c.width = AV.larg; c.height = AV.haut;
      c.getContext('2d').drawImage(img, 0, 0, AV.larg, AV.haut); URL.revokeObjectURL(u);
      c.toBlob(function (b) { if (b) AV.telecharge(nom() + '.png', b); else info('Rendu PNG impossible', true); }, 'image/png');
    };
    img.onerror = function () { URL.revokeObjectURL(u); info('Rendu PNG impossible (SVG illisible)', true); };
    img.src = u;
  });
})();
"""
