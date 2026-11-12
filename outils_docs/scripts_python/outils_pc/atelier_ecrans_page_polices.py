"""Panneau « Importer une police » de l'atelier des ecrans (plan atelier-ecrans A9) : HTML et JS.

Fichier .ttf choisi par l'utilisateur -> POST /polices/analyse (famille, licence lue dans la police, caracteres francais
manquants) -> case « licence verifiee » -> POST /polices/importer (police dans le dossier de la carte, catalogue
regenere) -> catalogue relu, police chargee par FontFace. Textes venus de la police : textContent ; l'URL de licence
n'est un lien que si elle commence par http(s)://.
"""

HTML = """
  <details id="importPolice" style="margin-top:10px"><summary class="petit"><b>Importer une police (.ttf)</b></summary>
   <p class="doux petit">Sources libres : <a href="https://fonts.google.com" target="_blank" rel="noopener">Google Fonts</a>,
    <a href="https://www.fontsquirrel.com" target="_blank" rel="noopener">Font Squirrel</a> (licences « 100 % free »).
    Police TrueType statique, accents compris ; elle part sur le FS de la carte choisie et se range sous /sd/polices/.</p>
   <input type="file" id="policeFichier" accept=".ttf" aria-label="Fichier de police .ttf">
   <div id="policeResultat" class="petit"></div>
  </details>"""

JS = r"""
var P = { analyse: null, contenu: '', nom: '', seq: 0 };
function base64De(tampon) {
  var o = new Uint8Array(tampon), s = '', pas = 0x8000;
  for (var i = 0; i < o.length; i += pas) s += String.fromCharCode.apply(null, o.subarray(i, i + pas));
  return btoa(s);
}
function resultatPolice(enfants) { var r = vide($('policeResultat')); enfants.forEach(function (e) { r.appendChild(e); }); }
function analysePolice(fichier) {
  var mien = ++P.seq;                    // un second choix pendant l'analyse : la reponse tardive est ignoree
  P.analyse = null; P.nom = fichier.name.replace(/\s+/g, '-');
  resultatPolice([el('p', { class: 'doux' }, 'Analyse de ' + P.nom + '…')]);
  fichier.arrayBuffer().then(function (t) {
    if (mien !== P.seq) return null;
    P.contenu = base64De(t);
    return requete('POST', '/polices/analyse', { nom: P.nom, contenu: P.contenu });
  }).then(function (a) {
    if (mien !== P.seq || !a) return;
    P.analyse = a;
    var lignes = [el('div', null, 'Famille : ' + a.famille + ' · ' + Math.round(a.poids / 1024) + ' Ko')];
    var lic = el('div', null, 'Licence lue dans la police : ' + (a.licence || '(absente)'));
    if (/^https?:\/\//.test(a.url_licence)) { lic.appendChild(document.createTextNode(' ')); lic.appendChild(el('a', { href: a.url_licence, target: '_blank', rel: 'noopener' }, a.url_licence)); }
    lignes.push(lic);
    if (!a.libre) lignes.push(el('div', { class: 'avert' }, 'Licence non reconnue comme libre (OFL, Apache 2.0…) : la vérifier sur le site de la police avant d’importer.'));
    if (a.manque) lignes.push(el('div', { class: 'avert' }, 'Caractères français absents, import refusé : ' + a.manque));
    var c = el('input', { type: 'checkbox', id: 'policeLicence' }), l = el('label', { for: 'policeLicence' }, ' J’ai vérifié la licence (usage libre)');
    var b = el('button', { type: 'button', class: 'btn prim', id: 'policeImporter' }, 'Importer pour ' + E.env);
    b.disabled = true;
    c.onchange = function () { b.disabled = !c.checked || !!a.manque || !E.env; };
    b.onclick = importePolice;
    var ligne = el('div', { class: 'ligne' }); ligne.appendChild(c); ligne.appendChild(l);
    lignes.push(ligne); lignes.push(b);
    resultatPolice(lignes);
  }).catch(function (e) { if (mien === P.seq) resultatPolice([el('div', { class: 'avert' }, 'Police refusée : ' + e.message)]); });
}
function importePolice() {
  var b = $('policeImporter'); b.disabled = true;
  requete('POST', '/polices/importer', { env: E.env, nom: P.nom, contenu: P.contenu, licence_confirmee: true }).then(function (r) {
    var fait = 'Importée : ' + r.ecrits.join(', ') + '. ';
    return requete('GET', '/catalogue').then(function (c) {
      E.catalogue = c;
      try { var f = new FontFace(r.analyse.nom, 'url("/police?nom=' + encodeURIComponent(r.analyse.nom) + '")'); document.fonts.add(f); f.load().then(dessineEcran, function () {}); } catch (e) {}
      resultatPolice([el('div', null, fait + 'Elle apparaît dans la liste des polices ; à envoyer sur la carte avec ses autres fichiers (page Build).')]);
      dessineTout();
    }, function (e) {                     // police deja ecrite : ne pas dire « refusé »
      resultatPolice([el('div', { class: 'avert' }, fait + 'Le catalogue n’a pas pu être relu (' + e.message + ') : recharger la page.')]);
    });
  }, function (e) { b.disabled = false; resultatPolice([el('div', { class: 'avert' }, 'Import refusé : ' + e.message)]); });
}
$('policeFichier').onchange = function () { var f = this.files && this.files[0]; if (f) analysePolice(f); };
"""
