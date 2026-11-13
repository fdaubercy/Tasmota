"""Panneau « Icones » de la page de l'atelier des ecrans (plan atelier-ecrans A15) : CSS, JS (le conteneur #icones est dans atelier_ecrans_page.py).

Grille des glyphes Material Design embarques dans le firmware (GET /icones, genere d'apres gen.sh), recherche par nom ; un clic
pose le glyphe (montserrat-28, comme `text` U+E335...) dans l'objet choisi s'il porte un texte, sinon dans un nouveau libelle.
Apercu : le texte d'un libelle ou d'un bouton dont un caractere est un code servi du catalogue est dessine par la police locale
(GET /lib/mdi.ttf, code MDI F0335 pour U+E335), aucun CDN. Les symboles Font Awesome du firmware ne sont pas dessines (carre vide).
Textes venus du catalogue ou de la description : textContent.
"""

CSS = """
@font-face{font-family:MDI;src:url(/lib/mdi.ttf) format('truetype')}
.mdi{font-family:MDI}
.grilleIcones{display:grid;grid-template-columns:repeat(auto-fill,minmax(82px,1fr));gap:6px;margin-top:8px}
.grilleIcones button{display:flex;flex-direction:column;align-items:center;gap:2px;padding:6px 2px;background:var(--champ);
 border:1px solid var(--bord);border-radius:6px;color:var(--texte);cursor:pointer;font:inherit}
.grilleIcones button:hover,.grilleIcones button:focus-visible{border-color:var(--bleu)}
.grilleIcones .glyphe{font-family:MDI;font-size:28px;line-height:34px}
.grilleIcones .nom{font-size:11px;color:var(--doux);word-break:break-all;text-align:center}
"""

JS = r"""
var IC = { liste: [], versMdi: {}, erreur: false, filtre: '' };   // versMdi : code servi (E335) -> code MDI (F0335)
var POLICE_ICONES = 'montserrat-28';
var SITES_ICONES = [
  ['Pictogrammers MDI', 'https://pictogrammers.com/library/mdi/', 'Apache 2.0'],
  ['Material Symbols', 'https://fonts.google.com/icons', 'Apache 2.0'],
  ['Tabler', 'https://tabler.io/icons', 'MIT'],
  ['Lucide', 'https://lucide.dev/icons/', 'ISC'],
  ['Phosphor', 'https://phosphoricons.com/', 'MIT'],
  ['Simple Icons (logos)', 'https://simpleicons.org/', 'CC0, marques à leurs propriétaires'],
  ['Iconify (recherche)', 'https://icon-sets.iconify.design/', 'celle de la collection']
];
function chargeIcones() {
  requete('GET', '/icones').then(function (r) {
    IC.liste = r.icones; IC.versMdi = {};
    r.icones.forEach(function (i) { IC.versMdi[parseInt(i.servi, 16)] = parseInt(i.mdi, 16); });
    if (E.desc) dessineTout();                   // les libelles deja dessines prennent leurs glyphes
    dessineIcones();
  }).catch(function () { IC.erreur = true; dessineIcones(); });
}
function posteTexte(d, t) {                      // texte d'un libelle ou d'un bouton, glyphes du firmware par la police MDI
  t = t === undefined ? '' : String(t);
  d.textContent = '';
  t.split(/([-])/).forEach(function (m) {
    if (!m) return;
    var mdi = m.length === 1 ? IC.versMdi[m.charCodeAt(0)] : undefined;
    if (mdi) d.appendChild(el('span', { class: 'mdi' }, String.fromCodePoint(mdi))); else d.appendChild(document.createTextNode(m));
  });
}
function poseIcone(i) {
  if (lecture()) return;
  var glyphe = String.fromCharCode(parseInt(i.servi, 16)), o = choisi();
  if (!o || (o.type !== 'label' && o.type !== 'btn')) { ajouteObjet('label', 16, 16); o = choisi(); }   // shortcut: deux etapes d'historique
  if (!o) return;
  modifie(function () { o.attributs.text = glyphe; o.attributs.text_font = POLICE_ICONES; });
}
function dessineIcones() {
  var p = vide($('icones'));
  if (IC.erreur) { p.appendChild(el('p', { class: 'avert' }, 'Catalogue des icônes indisponible : relancer genere_icones_firmware.py puis recharger la page.')); return; }
  p.appendChild(el('p', { class: 'doux petit' }, IC.liste.length + ' glyphes Material Design embarqués dans le firmware (polices montserrat-10 à 28). '
    + 'Clic : le glyphe va dans l’objet choisi (libellé ou bouton), sinon dans un nouveau libellé, en montserrat-28.'));
  var q = el('input', { type: 'search', 'aria-label': 'Chercher une icône par nom', placeholder: 'chercher : pump, wifi, light…' });
  q.value = IC.filtre; p.appendChild(q);
  var g = el('div', { class: 'grilleIcones' }); p.appendChild(g);
  function remplit() {
    vide(g); var f = IC.filtre.trim().toLowerCase();
    IC.liste.filter(function (i) { return !f || i.nom.indexOf(f) >= 0; }).forEach(function (i) {
      var b = el('button', { type: 'button', title: i.nom + ' : U+' + i.servi + ' (MDI ' + i.mdi + ')' });
      b.appendChild(el('span', { class: 'glyphe', 'aria-hidden': 'true' }, String.fromCodePoint(parseInt(i.mdi, 16))));
      b.appendChild(el('span', { class: 'nom' }, i.nom));
      b.onclick = function () { poseIcone(i); };
      g.appendChild(b);
    });
    if (!g.firstChild) g.appendChild(el('p', { class: 'doux petit' }, 'Aucun glyphe du firmware pour « ' + IC.filtre + ' ». Voir les sites ci-dessous.'));
  }
  q.oninput = function () { IC.filtre = q.value; remplit(); };
  remplit();
  p.appendChild(el('h4', null, 'Une icône absente du firmware'));
  p.appendChild(el('p', { class: 'doux petit' }, 'Glyphe du firmware d’abord (rien sur le FS). Sinon un PNG à la taille d’affichage, blanc sur fond '
    + 'transparent, rangé sous /sd/images/PNG/ et posé dans un objet image : sa couleur vient de image_recolor et image_recolor_opa. '
    + 'Un SVG se convertit en PNG avant (Inkscape, ou le convertisseur d’images de LVGL). Garder la licence de la collection à côté du fichier.'));
  var ul = el('ul', { class: 'doux petit' });
  SITES_ICONES.forEach(function (s) {
    var li = el('li'); li.appendChild(el('a', { href: s[1], target: '_blank', rel: 'noopener noreferrer' }, s[0])); li.appendChild(document.createTextNode(' : ' + s[2]));
    ul.appendChild(li);
  });
  p.appendChild(ul);
}
chargeIcones();
"""
