"""Barre de navigation construite d'apres les pages, dans la page de l'atelier des ecrans (plan atelier-ecrans A17) : CSS et JS.

`boutonsNav` refait le calcul de atelier_ecrans_navigation.py::boutons (meme largeur, memes ids 200 + n), compare par la sonde
Chrome ; les boutons sont dessines sur toutes les pages, en pointilles et non selectionnables (ils se reglent dans le panneau
« Barre de navigation » de la page 0 ; une page n >= 1 en sort par sa case « Dans la barre de navigation »).
"""

CSS = """
.ecran .o.nav{pointer-events:none;outline:1px dashed #ffffff80;outline-offset:2px}
"""

JS = r"""
var NAV_DEFAUT = { x: 24, y: 0, h: 46, ecart: 12,
  attributs: { radius: 23, border_width: 0, text_font: 24, bg_color: '#1F2B38', text_color: '#E8EDF2' },
  actif: { bg_color: '#3FA7FF', text_color: '#06121F' } };
function tailleNav(v) { if (typeof v === 'number') return v; var m = /-(\d+)$/.exec(String(v || '')); return m ? +m[1] : 14; }
function boutonsNav() {
  var n = E.desc && E.desc.navigation; if (!n) return [];
  var a = n.attributs || {}, x = n.x, res = [];
  E.desc.pages.forEach(function (p) {
    if (typeof p.n !== 'number' || p.n < 1 || p.menu === false) return;
    var t = p.titre || 'Page ' + p.n, l = Math.floor(Array.from(t).length * tailleNav(a.text_font) * 0.55 + 0.5) + n.h;
    var o = { id: 200 + p.n, page: 0, type: 'btn', x: x, y: n.y, l: l, h: n.h, attributs: Object.assign({}, a, { text: t }), toucher: { page: p.n } };
    if (n.actif) o.actif = Object.assign({}, n.actif);
    res.push(o); x += l + n.ecart;
  });
  return res;
}
function dessineNav(ec) {
  boutonsNav().forEach(function (o) { var d = dessineObjet(o, E.page !== 0); d.classList.add('nav'); ec.appendChild(d); });
}
function panneauNav(pn) {
  var n = E.desc.navigation;
  pn.appendChild(el('h3', null, 'Barre de navigation'));
  var c = el('input', { type: 'checkbox', 'aria-label': 'Barre de navigation construite' }); c.checked = !!n;
  c.onchange = function () {
    modifie(function () {
      if (!c.checked) { delete E.desc.navigation; return; }
      var b = JSON.parse(JSON.stringify(NAV_DEFAUT)); b.y = Math.max(0, dims().h - b.h - 14); E.desc.navigation = b;
    });
  };
  champ(pn, 'Construite', c);
  if (!n) { pn.appendChild(el('p', { class: 'doux petit' }, 'Un bouton par page, titre et changement de page tirés des pages ; les boutons de page posés à la main restent tels quels.')); return; }
  var l = el('div', { class: 'ligne' }); l.appendChild(el('span', { class: 'etiq' }, 'x, y, h, écart'));
  ['x', 'y', 'h', 'ecart'].forEach(function (k) {
    l.appendChild(saisie(n[k], 'number', function (v, i) {
      var e = entier(v); if (e === null || e < 0 || (k === 'h' && e === 0)) { i.value = n[k]; return; }
      modifie(function () { E.desc.navigation[k] = e; });
    }));
  });
  pn.appendChild(l);
  [['Fond', 'attributs', 'bg_color'], ['Texte', 'attributs', 'text_color'], ['Fond actif', 'actif', 'bg_color'], ['Texte actif', 'actif', 'text_color']].forEach(function (x) {
    champCouleur(pn, x[0], (n[x[1]] || {})[x[2]], function (v) {
      modifie(function () { var b = E.desc.navigation; b[x[1]] = b[x[1]] || {}; b[x[1]][x[2]] = v; });
    });
  });
  pn.appendChild(el('p', { class: 'doux petit' }, boutonsNav().length + ' bouton(s), ids 201 à 254 réservés sur la page 0. Une page en sort par sa case « Dans la barre de navigation ».'));
}
function casePageNav(pn, p) {
  if (!E.desc.navigation || p.n < 1) return;
  var c = el('input', { type: 'checkbox', 'aria-label': 'Dans la barre de navigation' }); c.checked = p.menu !== false;
  c.onchange = function () { modifie(function () { var q = pageDesc(p.n); if (c.checked) delete q.menu; else q.menu = false; }); };
  champ(pn, 'Dans la barre', c);
}
"""
