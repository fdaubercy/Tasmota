"""Panneau « Icones » de l'atelier des visuels (spec § 2.4) : recherche en ligne (Iconify, via les routes du serveur), licence affichee sur
chaque resultat, conservation au depot (confirmation si licence a attribution), import d'un .svg du PC (nettoye par le serveur : POST /fond
type svg puis GET /fond), pose comme voyant, icone par etat (icone_on / icone_off / icone_inconnu) et taille reglable.

Seul le tracé `path` d'une icone est retenu ({w, h, d}) : les autres formes d'un SVG sont ignorees, avec un message. Hors ligne : le message du serveur.
Banque locale du firmware (`icones_firmware.json`) : aucune route ne la sert (police de glyphes, pas de tracé), donc non proposee ici.
"""

CSS_ICONES = """
#avi-res{display:flex;flex-wrap:wrap;gap:4px;max-height:150px;overflow:auto}
#avi-res button{font-size:12px;padding:3px 6px}
#avi-prev{width:48px;height:48px;background:var(--champ);border:1px solid var(--bord);border-radius:6px;color:var(--texte)}
"""

HTML_ICONES = (
    "<div class='pan' id='avi-panel'><h2>Icônes</h2><div class='g'>"
    "<div class='row'><input type='search' id='avi-q' maxlength='40' placeholder='Chercher (camera, lampe…)' aria-label='Recherche d’icône en ligne'>"
    "<button type='button' id='avi-cherche'>Chercher</button></div>"
    "<div id='avi-res' role='list' aria-label='Résultats'></div>"
    "<div class='row'><svg id='avi-prev' viewBox='0 0 24 24' role='img' aria-label='Aperçu de l’icône'></svg><div id='avi-info' class='doux' role='status'>Aucune icône choisie</div></div>"
    "<label id='avi-attr-l' hidden class='doux'><input type='checkbox' id='avi-attr'> J’ai lu la licence (attribution requise) et je l’accepte</label>"
    "<div class='row'><button type='button' id='avi-pose'>Poser comme voyant</button><button type='button' id='avi-garde'>Garder au dépôt</button></div>"
    "<div class='doux'>Pour l’élément sélectionné (un voyant) :</div>"
    "<div class='row'><button type='button' data-avi-etat='icone_on'>ON</button><button type='button' data-avi-etat='icone_off'>OFF</button>"
    "<button type='button' data-avi-etat='icone_inconnu'>Inconnu</button></div>"
    "<label class='row doux'>Taille <input type='range' id='avi-taille' min='8' max='80' value='24'></label>"
    "<div class='row'><button type='button' id='avi-importe'>Importer un .svg…</button><input type='file' id='avi-fichier' class='vh' accept='.svg,image/svg+xml' tabindex='-1' aria-label='SVG à importer'></div>"
    "</div></div>"
)

JS_ICONES = r"""
(function () {
  var AV = window.AV, F = AV_FORMES, Cq = AV_CALQUES, $ = function (i) { return document.getElementById(i); }, courante = null;
  function info(t, mauvais) { var e = $('avi-info'); e.textContent = t; e.className = mauvais ? 'mauvais' : 'doux'; }
  function vide(e) { while (e.firstChild) e.removeChild(e.firstChild); }
  // {w, h, d} d'un texte SVG (deja nettoye par le serveur) ; null si aucun tracé exploitable
  function trace(texte) {
    var doc = new DOMParser().parseFromString(texte, 'image/svg+xml'), r = doc.documentElement, vb, ch = [];
    if (!r || r.nodeName.toLowerCase() !== 'svg' || doc.getElementsByTagName('parsererror').length) return null;
    vb = (r.getAttribute('viewBox') || '0 0 24 24').split(/[\s,]+/).map(Number);
    [].forEach.call(r.getElementsByTagName('path'), function (p) { ch.push(p.getAttribute('d') || ''); });
    return Cq.icone({w: vb[2], h: vb[3], d: ch.join(' ').trim()});
  }
  function affiche(ic, jeu, nom, licence, attribution) {
    courante = ic ? Object.assign({}, ic, {jeu: jeu, nom: nom, licence: licence, attribution: attribution}) : null;
    var p = $('avi-prev'); vide(p);
    if (ic) { p.setAttribute('viewBox', '0 0 ' + ic.w + ' ' + ic.h); p.appendChild(F.bati(['path', {d: ic.d, fill: 'currentColor'}], document)); }
    $('avi-attr-l').hidden = !(ic && attribution); $('avi-attr').checked = false;
    info(ic ? jeu + ':' + nom + ' · licence ' + licence + (attribution ? ' (attribution)' : '') : 'Aucune icône choisie', false);
  }
  function cherche() {
    var q = $('avi-q').value.trim(), res = $('avi-res');
    if (!q) { info('Saisissez un mot à chercher', true); return; }
    info('Recherche…', false);
    AV.api('GET', '/icones/recherche?q=' + encodeURIComponent(q)).then(function (r) {
      vide(res);
      if (!r.ok) { info(r.texte || 'Recherche impossible', true); return; }
      var l = r.json.icones || [];
      info(l.length ? l.length + ' icône(s)' : 'Aucun résultat', !l.length);
      l.forEach(function (ic) {
        var li = document.createElement('div'), b = document.createElement('button');
        li.setAttribute('role', 'listitem'); li.appendChild(b);
        b.type = 'button'; b.textContent = ic.jeu + ':' + ic.nom + ' · ' + ic.licence + (ic.attribution ? ' ⚠' : '');
        b.addEventListener('click', function () { choisit(ic); });
        res.appendChild(li);
      });
    }).catch(function () { info('Serveur injoignable', true); });
  }
  function choisit(ic) {
    AV.api('GET', '/icones/svg?jeu=' + encodeURIComponent(ic.jeu) + '&nom=' + encodeURIComponent(ic.nom)).then(function (r) {
      if (!r.ok) { info(r.texte || 'Icône indisponible', true); return; }
      var t = trace(r.json.svg);
      if (!t) { info('Cette icône n’a pas de tracé simple (path) : choisissez-en une autre', true); return; }
      affiche(t, ic.jeu, ic.nom, r.json.licence, ic.attribution);
    }).catch(function () { info('Serveur injoignable', true); });
  }
  function icone() { return courante ? {w: courante.w, h: courante.h, d: courante.d, jeu: courante.jeu, nom: courante.nom} : null; }
  function pris() { if (!courante) { info('Choisissez d’abord une icône', true); return false; } return true; }
  $('avi-cherche').addEventListener('click', cherche);
  $('avi-q').addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); cherche(); } });
  $('avi-pose').addEventListener('click', function () {
    if (!pris()) return;
    var t = +$('avi-taille').value;
    AV.ajoutEl({id: AV.idEl('v'), type: 'voyant', x: Math.round(AV.larg / 2), y: Math.round(AV.haut / 2), source: {type: 'relais', n: 1},
                style: {taille: t, icone_on: icone(), icone_off: icone(), icone_inconnu: icone()}});
  });
  document.querySelectorAll('[data-avi-etat]').forEach(function (b) {
    b.addEventListener('click', function () {
      var e = AV.elCherche(AV.selEl);
      if (!pris()) return;
      if (!e || e.type !== 'voyant') { info('Sélectionnez d’abord un voyant', true); return; }
      e.style[b.getAttribute('data-avi-etat')] = icone(); AV.sauveEls(); AV.dessine();
    });
  });
  $('avi-taille').addEventListener('input', function () {
    var e = AV.elCherche(AV.selEl);
    if (e && e.type === 'voyant') { e.style.taille = +this.value; AV.sauveEls(); AV.dessine(); }
  });
  $('avi-garde').addEventListener('click', function () {
    if (!pris()) return;
    if (!courante.jeu) { info('Icône importée du PC : rien à garder (licence à confirmer à la main)', true); return; }
    if (courante.attribution && !$('avi-attr').checked) { info('Cochez la confirmation d’attribution pour garder cette icône', true); return; }
    AV.api('POST', '/icones/garde', {jeu: courante.jeu, nom: courante.nom, confirme_attribution: courante.attribution && $('avi-attr').checked})
      .then(function (r) { info(r.ok ? 'Gardée : ' + r.json.chemin : (r.texte || 'Refusé'), !r.ok); })
      .catch(function () { info('Serveur injoignable', true); });
  });
  // import d'un .svg du PC : nettoye par le serveur (POST /fond type svg) puis relu (GET /fond)
  $('avi-importe').addEventListener('click', function () { $('avi-fichier').click(); });
  $('avi-fichier').addEventListener('change', function (ev) {
    var f = ev.target.files[0], env = AV.env;
    if (!f) return;
    if (f.size > 200 * 1024) { info('SVG trop lourd (200 Ko au plus)', true); return; }
    f.text().then(function (txt) {
      return AV.api('POST', '/fond?env=' + encodeURIComponent(env) + '&type=svg', txt);
    }).then(function (r) {
      if (!r.ok) { info('SVG refusé : ' + (r.texte || r.status), true); return null; }
      return AV.api('GET', '/fond?env=' + encodeURIComponent(env) + '&empreinte=' + r.json.empreinte);
    }).then(function (r) {
      if (!r) return;
      var t = r.ok ? trace(r.texte) : null;
      if (!t) { info('Ce SVG n’a pas de tracé simple (path) exploitable', true); return; }
      affiche(t, '', f.name.slice(0, 40), 'à confirmer (import)', false);
    }).catch(function () { info('Import impossible', true); });
  });
})();
"""
