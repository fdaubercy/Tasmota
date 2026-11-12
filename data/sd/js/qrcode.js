// Page /qrcode (data/fs/qrcodePage.be) : dessine le QR code de /qrcode?f=reglage avec optionsQR (qrcode_options.js),
// puis compare l'IP inscrite a l'IP reelle de la carte (/qrcode?f=etat). Bibliotheque /qrcode?f=lib.js.gz : decompressee
// par le navigateur, gardee dans localStorage sous une cle versionnee (a changer avec le .gz).
(function () {
  var CLE = 'qr-code-styling-1.9.2';
  var $ = function (id) { return document.getElementById(id); };

  function message(texte, erreur) {
    var m = $('q_msg');
    m.textContent = texte;
    m.className = erreur ? 'erreur' : '';
    m.hidden = !texte;
  }

  function lis() { try { return localStorage.getItem(CLE); } catch (e) { return null; } }
  function memorise(texte) {
    try {
      for (var i = localStorage.length - 1; i >= 0; i--) {
        var k = localStorage.key(i);
        if (k && k.indexOf('qr-code-styling-') === 0 && k !== CLE) localStorage.removeItem(k);
      }
      localStorage.setItem(CLE, texte);
    } catch (e) { /* stockage indisponible ou plein : la bibliotheque sera redemandee a la carte */ }
  }

  function chargeBibliotheque() {
    if (window.QRCodeStyling) return Promise.resolve();
    var texte = lis();
    var source = texte ? Promise.resolve(texte) : fetch('/qrcode?f=lib.js.gz').then(function (r) {
      if (!r.ok) throw new Error('Bibliothèque absente de la carte (HTTP ' + r.status + ').');
      if (typeof DecompressionStream === 'undefined' || !r.body) {
        throw new Error('Navigateur trop ancien : il ne sait pas décompresser la bibliothèque (DecompressionStream).');
      }
      return new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).text();
    }).then(function (t) { memorise(t); return t; });
    return source.then(function (t) {
      var s = document.createElement('script');
      s.textContent = t;
      document.head.appendChild(s);
      if (!window.QRCodeStyling) {
        try { localStorage.removeItem(CLE); } catch (e) { /* rien */ }
        throw new Error('Bibliothèque illisible : recharger la page.');
      }
    });
  }

  function json(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + ' : HTTP ' + r.status);
      return r.json();
    });
  }

  // IP inscrite avec un port (esclave joint par le maitre, 192.168.0.51:8081) : jamais l'IP propre de la carte
  function compareIP(inscrite, etat) {
    if (!inscrite || inscrite.indexOf(':') >= 0 || !etat.ip || inscrite === etat.ip) return;
    var a = $('q_avert');
    a.textContent = 'IP inscrite dans le QR code : ' + inscrite + ' ; IP actuelle de la carte : ' + etat.ip
      + '. Régénérez le QR code dans l\'outil « Étiquettes QR code », puis renvoyez-le sur la carte.';
    a.hidden = false;
  }

  Promise.all([chargeBibliotheque(), json('/qrcode?f=reglage')]).then(function (r) {
    var d = r[1];
    if (!d || typeof d.texte !== 'string' || !d.texte) throw new Error('Réglage du QR code invalide (texte absent).');
    new QRCodeStyling(optionsQR(d.texte, d.style || {}, d.correction || 'M', d.image, 260, d.modules)).append($('q_code'));
    $('q_texte').textContent = d.texte;
    message('');
    return json('/qrcode?f=etat').then(function (etat) { compareIP(d.ip_inscrite, etat); },
      function () { /* etat indisponible : le QR code reste affiche, sans comparaison */ });
  }).catch(function (e) { message(e.message, true); });
})();
