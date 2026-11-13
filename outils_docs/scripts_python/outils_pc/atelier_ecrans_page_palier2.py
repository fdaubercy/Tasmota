"""Objets du palier 2 dans la page de l'atelier des ecrans (plan atelier-ecrans A14, spec 2026-11-12 § 7) : CSS et JS.

Dessin approche de img, dropdown, switch, roller, qrcode (`dessinePalier2`, appele par dessineObjet) ; image choisie parmi
les PNG du dossier de la carte (GET /images, aperçu par GET /image) ou le logo Tasmota ; options d'une liste deroulante ou
d'une roue editees une par ligne (type `lignes` du catalogue) ; QR code dessine par qr-code-styling, la bibliotheque de la
page des etiquettes (GET /lib/qr.js), un carre gris si elle manque. Textes venus de la description : textContent.
"""

CSS = """
.ecran .o .bouton{position:absolute;top:3px;bottom:3px;aspect-ratio:1;border-radius:50%;background:#FFFFFF}
.ecran .o img{width:100%;height:100%;object-fit:contain;pointer-events:none}
.ecran .o .qr svg,.ecran .o .qr canvas{display:block;width:100%;height:100%}
.ecran .o .roue{opacity:.45}
textarea.lignes{width:100%;font:13px/1.4 Consolas,monospace}
"""

JS = r"""
var P2 = { images: [], env: null, erreur: false };   // erreur : liste GET /images indisponible
var TYPES_P2 = ['img', 'dropdown', 'switch', 'roller', 'qrcode'];
var IMAGE_SD = 'A:sd/images/PNG/';
function dansAtelier(t) { var c = E.catalogue.objets[t]; return !!c && (c.palier === 1 || c.palier === 2); }
function chargeImages() {
  var env = E.env; P2.images = []; P2.env = env; P2.erreur = false;
  requete('GET', '/images?env=' + encodeURIComponent(env)).then(function (r) {
    if (env === E.env) { P2.images = r.images; dessineTout(); }
  }).catch(function () { if (env === E.env) { P2.erreur = true; dessineTout(); } });
}
function nomImage(src) { return typeof src === 'string' && src.indexOf(IMAGE_SD) === 0 ? src.slice(IMAGE_SD.length) : null; }
function options(v) { return String(v || '').split('\n'); }
function centre(s) { s.display = 'flex'; s.alignItems = 'center'; s.justifyContent = 'center'; }
function dessinePalier2(o, a, d) {
  var s = d.style;
  if (o.type === 'img') {
    var n = nomImage(a.src);
    if (n && P2.images.indexOf(n) >= 0) d.appendChild(el('img', { alt: n, src: '/image?env=' + encodeURIComponent(E.env) + '&nom=' + encodeURIComponent(n) }));
    else { centre(s); s.outline = '1px dashed #888888'; d.textContent = a.src === 'tasmota_logo' ? 'logo Tasmota' : n ? n + (P2.erreur ? ' (liste des images indisponible)' : ' (absent du dossier)') : 'image'; }
  } else if (o.type === 'dropdown') {
    centre(s); s.justifyContent = 'space-between'; s.padding = '0 10px'; s.boxSizing = 'border-box';
    s.background = couleur(a.bg_color, '#FFFFFF'); s.color = couleur(a.text_color, '#212121');
    d.appendChild(el('span', null, String(a.text !== undefined ? a.text : options(a.options)[a.val || 0] || '')));
    d.appendChild(el('span', null, '▾'));
  } else if (o.type === 'switch') {
    var oui = a.val === true;
    s.borderRadius = Math.round(o.h / 2) + 'px';
    s.background = oui ? couleur(a.bg_color10, '#2196F3') : couleur(a.bg_color, '#BDBDBD');
    var b = el('div', { class: 'bouton' }); b.style[oui ? 'right' : 'left'] = '3px'; d.appendChild(b);
  } else if (o.type === 'roller') {
    var L = options(a.options), i = a.val || 0;
    s.background = couleur(a.bg_color, '#FFFFFF'); s.color = couleur(a.text_color, '#212121'); s.overflow = 'hidden';
    s.display = 'flex'; s.flexDirection = 'column'; s.justifyContent = 'center'; s.textAlign = 'center';
    [i - 1, i, i + 1].forEach(function (j) { d.appendChild(el('div', { class: j === i ? '' : 'roue' }, j >= 0 && j < L.length ? L[j] : '')); });
  } else if (o.type === 'qrcode') {
    s.background = couleur(a.qr_light_color, '#FFFFFF');
    if (typeof QRCodeStyling === 'function' && a.qr_text) {
      var z = el('div', { class: 'qr' }); z.style.width = '100%'; z.style.height = '100%'; d.appendChild(z);
      try {
        new QRCodeStyling({ width: o.l, height: o.l, type: 'svg', data: String(a.qr_text), margin: 0,
          dotsOptions: { color: couleur(a.qr_dark_color, '#000000'), type: 'square' },
          backgroundOptions: { color: couleur(a.qr_light_color, '#FFFFFF') } }).append(z);
      } catch (e) { z.textContent = 'QR code illisible'; }
    } else { centre(s); s.color = '#555555'; d.textContent = a.qr_text ? 'QR code' : 'QR code sans texte'; }
  }
}
function champOptions(parent, k, v, poser) {
  var t = el('textarea', { rows: '4', class: 'lignes', 'aria-label': k + ' (une option par ligne)' }); t.value = v || '';
  t.onchange = function () {
    var nv = t.value.replace(/\r/g, '').split('\n').map(function (x) { return x.trim(); }).filter(Boolean).join('\n');
    if (!nv) { t.value = v || ''; alert('Au moins une option, une par ligne.'); return; }
    poser(nv);
  };
  champ(parent, k + ' (une par ligne)', t);
}
function champImage(parent, v, poser) {
  var s = el('select', { 'aria-label': 'Image' });
  s.appendChild(el('option', { value: 'tasmota_logo' }, 'logo Tasmota (embarqué)'));
  P2.images.forEach(function (n) { s.appendChild(el('option', { value: IMAGE_SD + n }, n)); });
  if (v && v !== 'tasmota_logo' && P2.images.indexOf(nomImage(v)) < 0) s.appendChild(el('option', { value: v }, String(v) + ' (absent du dossier)'));
  s.value = v || 'tasmota_logo';
  s.onchange = function () { poser(s.value); };
  champ(parent, 'Image', s);
  parent.appendChild(el('p', { class: 'doux petit' }, P2.erreur ? 'Liste des images de la carte indisponible : recharger la page.' : P2.images.length
    ? 'PNG du dossier de la carte, rangés sous /sd/images/PNG/ au démarrage (le firmware ne décode que le PNG).'
    : 'Aucun PNG dans le dossier de la carte : déposez-y un .png, il sera rangé sous /sd/images/PNG/ au démarrage.'));
}
"""
