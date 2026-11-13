"""JS de la page de l'atelier des visuels : coque (cartes, fond, poids), import de la photo, recadrage, rotation, encodage, envoi.

Contrat avec atelier_visuels_page_formes.py : objet global window.AV (voir la docstring de atelier_visuels_page.py).
Aucun texte venu du reseau n'entre dans le DOM autrement que par textContent ; pas d'eval.
"""

JS = r"""
(function () {
  var $ = function (i) { return document.getElementById(i); };
  var AV = window.AV = { env: null, puce: '', photo: document.createElement('canvas'), mode: 'plat', formes: [],
    larg: 480, haut: 270, carte: null, src: null, rot: 0, rec: { x: 0, y: 0, w: 1, h: 1 },
    fond: null, abonnes: [] };
  AV.photo.width = AV.larg; AV.photo.height = AV.haut;
  AV.surChangement = function (fn) { AV.abonnes.push(fn); };
  AV.change = function () { AV.abonnes.forEach(function (f) { try { f(); } catch (e) { console.error(e); } }); poids(); };
  function redessine() { if (AV.dessine) AV.dessine(); }
  function stocke(cle, v) { try { localStorage.setItem(cle, JSON.stringify(v)); } catch (e) {} }
  function lit(cle) { try { return JSON.parse(localStorage.getItem(cle)); } catch (e) { return null; } }
  function info(texte, mauvais) { var m = $('av-msg'); m.textContent = texte; m.className = mauvais ? 'mauvais' : 'doux'; }
  function kio(n) { return (n / 1024).toFixed(1).replace('.', ',') + ' Ko'; }

  // ---- theme sombre / clair (memorise, defaut = systeme) ---------------------------------------
  function theme(t) {
    document.documentElement.setAttribute('data-theme', t);
    $('av-theme').textContent = t === 'sombre' ? 'Clair' : 'Sombre';
  }
  theme(document.documentElement.getAttribute('data-theme') || 'clair');
  $('av-theme').addEventListener('click', function () {
    var t = document.documentElement.getAttribute('data-theme') === 'sombre' ? 'clair' : 'sombre';
    theme(t); try { localStorage.setItem('atelier-visuels-theme', t); } catch (e) {}
  });

  // ---- cartes (GET /envs) ---------------------------------------------------------------------
  var cartes = [];
  fetch('/envs').then(function (r) { return r.json(); }).then(function (d) {
    cartes = d.envs;
    var dernier = null; try { dernier = localStorage.getItem('av.env'); } catch (e) {}
    remplitParLieu($('av-carte'), cartes.map(function (c) { return { nom: c.env, lieu: c.lieu }; }), d.lieux, dernier);
    choisitCarte();
  }).catch(function () { info('Liste des cartes indisponible', true); });
  function ratioMemo() { var m = lit('av.rec.' + AV.env); return m && m.r > 0 ? m.r : 0.5625; }
  function choisitCarte() {
    AV.env = AV.carte = $('av-carte').value || null;
    if (AV.charge) AV.charge();                    // relit les formes de cette carte (editeur de formes)
    var c = cartes.filter(function (x) { return x.env === AV.env; })[0];
    AV.puce = c ? c.puce : '';
    try { localStorage.setItem('av.env', AV.env); } catch (e) {}
    var m = lit('av.rec.' + AV.env);
    AV.rec = m && m.w > 0 && m.h > 0 ? { x: m.x, y: m.y, w: m.w, h: m.h } : { x: 0, y: 0, w: 1, h: 1 };
    AV.fond = null; $('av-empreinte').textContent = '';
    if (AV.src) applique(); else { AV.haut = Math.round(AV.larg * ratioMemo()); redessine(); AV.change(); }
  }
  $('av-carte').addEventListener('change', choisitCarte);

  // ---- photo : lecture, rotation, recadrage ---------------------------------------------------
  function charge(fichier) {
    if (!fichier || fichier.type.indexOf('image/') !== 0) { info("Ce fichier n'est pas une image", true); return; }
    var lecteur = new FileReader();
    lecteur.onload = function () {
      var img = new Image();
      img.onload = function () {
        AV.img = img; AV.rot = 0; AV.rec = { x: 0, y: 0, w: 1, h: 1 }; tourne(0);
        info('Photo chargee : ' + img.naturalWidth + ' x ' + img.naturalHeight + ' px', false);
      };
      img.onerror = function () { info('Image illisible', true); };
      img.src = lecteur.result;
    };
    lecteur.readAsDataURL(fichier);
  }
  function tourne(quarts) {
    AV.rot = (AV.rot + quarts + 4) % 4;
    var img = AV.img, echelle = Math.min(1, 2400 / Math.max(img.naturalWidth, img.naturalHeight));
    var w = Math.round(img.naturalWidth * echelle), h = Math.round(img.naturalHeight * echelle), impair = AV.rot % 2;
    var s = document.createElement('canvas'); s.width = impair ? h : w; s.height = impair ? w : h;
    var c = s.getContext('2d'); c.translate(s.width / 2, s.height / 2); c.rotate(AV.rot * Math.PI / 2);
    c.drawImage(img, -w / 2, -h / 2, w, h);
    AV.src = s;
    if (quarts) AV.rec = { x: 0, y: 0, w: 1, h: 1 };
    applique();
  }
  function applique() {
    AV.larg = +$('av-larg').value; $('av-larg-v').textContent = AV.larg + ' px';
    var sw = AV.rec.w * AV.src.width, sh = AV.rec.h * AV.src.height;
    AV.haut = Math.max(1, Math.round(AV.larg * sh / sw));
    AV.photo.width = AV.larg; AV.photo.height = AV.haut;
    AV.photo.getContext('2d').drawImage(AV.src, AV.rec.x * AV.src.width, AV.rec.y * AV.src.height, sw, sh, 0, 0, AV.larg, AV.haut);
    stocke('av.rec.' + AV.env, { x: AV.rec.x, y: AV.rec.y, w: AV.rec.w, h: AV.rec.h, r: AV.haut / AV.larg });
    dessineRecadrage(); redessine(); AV.change();
  }
  var rc = $('av-crop'), rctx = rc.getContext('2d');
  function dessineRecadrage() {
    if (!AV.src) { rc.hidden = true; return; }
    rc.hidden = false;
    rc.width = 260; rc.height = Math.round(260 * AV.src.height / AV.src.width);
    rctx.drawImage(AV.src, 0, 0, rc.width, rc.height);
    var r = AV.rec, x = r.x * rc.width, y = r.y * rc.height, w = r.w * rc.width, h = r.h * rc.height;
    rctx.fillStyle = 'rgba(0,0,0,.55)';
    rctx.fillRect(0, 0, rc.width, y); rctx.fillRect(0, y + h, rc.width, rc.height - y - h);
    rctx.fillRect(0, y, x, h); rctx.fillRect(x + w, y, rc.width - x - w, h);
    rctx.strokeStyle = '#1fa3ec'; rctx.lineWidth = 2; rctx.strokeRect(x, y, w, h);
    rctx.fillStyle = '#1fa3ec';
    [[x, y], [x + w, y], [x, y + h], [x + w, y + h]].forEach(function (p) { rctx.fillRect(p[0] - 5, p[1] - 5, 10, 10); });
  }
  var geste = null;
  function pointeur(e) { var b = rc.getBoundingClientRect(); return { x: (e.clientX - b.left) / b.width, y: (e.clientY - b.top) / b.height }; }
  rc.addEventListener('pointerdown', function (e) {
    var p = pointeur(e), r = AV.rec, tol = 12 / rc.getBoundingClientRect().width, coin = null;
    [[0, 0], [1, 0], [0, 1], [1, 1]].forEach(function (c) {
      if (Math.abs(p.x - (r.x + c[0] * r.w)) < tol && Math.abs(p.y - (r.y + c[1] * r.h)) < tol) coin = c;
    });
    var copie = { x: r.x, y: r.y, w: r.w, h: r.h };
    if (coin) geste = { coin: coin, r: copie };
    else if (p.x > r.x && p.x < r.x + r.w && p.y > r.y && p.y < r.y + r.h) geste = { dep: p, r: copie };
    if (geste) rc.setPointerCapture(e.pointerId);
  });
  rc.addEventListener('pointermove', function (e) {
    if (!geste) return;
    var p = pointeur(e), g = geste.r, mini = 0.05, x1 = g.x, y1 = g.y, x2 = g.x + g.w, y2 = g.y + g.h;
    var cl = function (v, a, b) { return Math.max(a, Math.min(b, v)); };
    if (geste.dep) {
      var dx = cl(p.x - geste.dep.x, -g.x, 1 - g.x - g.w), dy = cl(p.y - geste.dep.y, -g.y, 1 - g.y - g.h);
      AV.rec = { x: g.x + dx, y: g.y + dy, w: g.w, h: g.h };
    } else {
      if (geste.coin[0]) x2 = cl(p.x, x1 + mini, 1); else x1 = cl(p.x, 0, x2 - mini);
      if (geste.coin[1]) y2 = cl(p.y, y1 + mini, 1); else y1 = cl(p.y, 0, y2 - mini);
      AV.rec = { x: x1, y: y1, w: x2 - x1, h: y2 - y1 };
    }
    applique();
  });
  rc.addEventListener('pointerup', function () { geste = null; });

  $('av-fichier').addEventListener('change', function (e) { charge(e.target.files[0]); });
  var zone = $('av-zone');
  zone.addEventListener('dragover', function (e) { e.preventDefault(); zone.classList.add('survol'); });
  zone.addEventListener('dragleave', function () { zone.classList.remove('survol'); });
  zone.addEventListener('drop', function (e) { e.preventDefault(); zone.classList.remove('survol'); charge(e.dataTransfer.files[0]); });
  $('av-rot').addEventListener('click', function () { if (AV.img) tourne(1); });
  $('av-rec0').addEventListener('click', function () { if (AV.src) { AV.rec = { x: 0, y: 0, w: 1, h: 1 }; applique(); } });
  $('av-larg').addEventListener('input', function () {
    if (AV.src) { applique(); return; }
    AV.larg = +this.value; $('av-larg-v').textContent = AV.larg + ' px'; AV.haut = Math.round(AV.larg * ratioMemo());
    redessine(); AV.change();
  });

  // ---- mode de fond, poids, envoi -------------------------------------------------------------
  var S = window.AV_SEUILS, gen = 0, blob = null, type = null;
  function mode(m) {
    AV.mode = m; $('av-fond-plat').classList.toggle('on', m === 'plat'); $('av-fond-photo').classList.toggle('on', m === 'photo');
    $('av-qualite-l').hidden = m !== 'photo'; redessine(); AV.change();
  }
  $('av-fond-plat').addEventListener('click', function () { mode('plat'); });
  $('av-fond-photo').addEventListener('click', function () { mode('photo'); });
  $('av-qualite').addEventListener('input', function () { $('av-qualite-v').textContent = this.value + ' %'; AV.change(); });
  function fin(b, t, g) {
    if (g !== gen) return;
    blob = b; type = t;
    var el = $('av-poids'), limite = AV.puce === 'ESP32' ? S.esp32 : S.autre;
    el.textContent = b ? kio(b.size) : '-';
    el.className = !b ? 'doux' : b.size > limite ? 'mauvais' : b.size > S.avert ? 'alerte' : 'bon';
    el.title = b ? "Avertissement au-dessus de " + kio(S.avert) + ', refus au-dessus de ' + kio(limite) : '';
    $('av-garder').disabled = !b || b.size > limite;
    $('av-type').textContent = t || '';
  }
  function poids() {
    var g = ++gen;
    if (AV.mode === 'plat') {
      var s = AV.svg ? AV.svg() : '';
      fin(s ? new Blob([s], { type: 'image/svg+xml' }) : null, 'svg', g);
    } else if (!AV.src) fin(null, null, g);
    else {
      var q = $('av-qualite').value / 100;
      AV.photo.toBlob(function (b) {
        if (b && b.type === 'image/webp') fin(b, 'webp', g);
        else AV.photo.toBlob(function (j) { fin(j, 'jpg', g); }, 'image/jpeg', q);   // repli : navigateur sans encodeur WebP
      }, 'image/webp', q);
    }
  }
  $('av-garder').addEventListener('click', function () {
    if (!blob || !AV.env) return;
    var t = type, env = AV.env;
    fetch('/fond?env=' + encodeURIComponent(env) + '&type=' + t, { method: 'POST', headers: { 'X-Atelier-Visuels': '1' }, body: blob })
      .then(function (r) { return r.text().then(function (x) { return [r.status, x]; }); })
      .then(function (a) {
        if (a[0] !== 200) { info('Fond refuse : ' + a[1], true); return; }
        var d = JSON.parse(a[1]); AV.fond = { env: env, type: t, empreinte: d.empreinte, octets: d.octets };
        info('Fond garde (' + t + ', ' + kio(d.octets) + ')' + (d.avertissement ? ' : ' + d.avertissement : ''), false);
        $('av-empreinte').textContent = d.empreinte;
      }).catch(function () { info('Serveur injoignable', true); });
  });
  ['av-export', 'av-ecrire'].forEach(function (i) { $(i).disabled = true; $(i).title = 'a venir'; });
  $('av-larg-v').textContent = AV.larg + ' px'; $('av-qualite-v').textContent = $('av-qualite').value + ' %';
  AV.majPoids = poids;
  mode('plat');
})();
"""
