// Options de qr-code-styling : SOURCE UNIQUE, servie par la carte (/qrcode, data/fs/qrcodePage.be) et inseree dans la page
// de l'outil « Etiquettes QR code » (outils_pc/etiquettes_qr_page_js.py), pour dessiner EXACTEMENT le meme QR code.
// Texte toujours converti en octets UTF-8 et encode en mode Byte : la bibliotheque garde sinon 255 & charCode
// (outils_docs/etiquettes_qr/lib/LISEZMOI.md). Marge = 4 modules blancs (modules : nombre de modules du code, du reglage).
function octets(texte) {
  let s = '';
  new TextEncoder().encode(texte).forEach(b => { s += String.fromCharCode(b); });
  return s;
}

function optionsQR(texte, style, correction, image, px, modules) {
  const couleur = style.couleur || '#000000';
  return {width: px, height: px, type: 'svg', data: octets(texte), image: image || undefined,
    margin: modules ? Math.round(4 * px / (modules + 8)) : 0,
    qrOptions: {typeNumber: 0, mode: 'Byte', errorCorrectionLevel: correction},
    dotsOptions: {type: style.points || 'square', color: couleur},
    cornersSquareOptions: {type: style.coins || 'square', color: couleur},
    cornersDotOptions: {type: style.coins === 'square' ? 'square' : 'dot', color: couleur},
    backgroundOptions: {color: style.fond || '#ffffff'},
    imageOptions: {margin: 2, imageSize: 0.3, hideBackgroundDots: true}};
}
