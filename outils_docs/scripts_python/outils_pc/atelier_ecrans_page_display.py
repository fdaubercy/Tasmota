"""Onglet « display.ini » de l'atelier des ecrans (plan atelier-ecrans A15, spec 2026-11-12 § 6.3) : HTML, CSS et JS.

Bascule « Interface | display.ini » de l'en-tete. Colonne gauche : fichiers (cartes, ma bibliotheque, Tasmota). Centre :
texte du fichier, analyse ligne par ligne (POST /display/analyse, 300 ms apres la frappe) avec arguments expliques au
survol, erreurs et avertissements ; « Enregistrer dans ma bibliotheque » = diff puis confirmation (POST /display/diff
puis /display/enregistrer) ; notes de terrain du fichier de la bibliotheque. Droite : panneau « Parametres » (reference,
parametres du bus de :H), « Ajouter » = POST /display/inserer. Tout texte venu d'un fichier : textContent.
"""

CSS = """
#vueDisplay textarea{width:100%;font:12px/1.45 Consolas,monospace;white-space:pre;resize:vertical}
#diLignes td{vertical-align:top} #diLignes td.t{font:12px Consolas,monospace;white-space:pre;max-width:340px;overflow:hidden;text-overflow:ellipsis}
#diLignes .arg{display:inline-block;margin:0 6px 2px 0;padding:0 5px;border-radius:4px;background:var(--piste);font-size:12px;cursor:help}
#diLignes .arg.trop{background:var(--orange-fond);color:var(--orange)}
.diErr{color:var(--rouge)} .diAv{color:var(--orange)}
.diErreurs{background:var(--orange-fond);border-left:3px solid var(--rouge);padding:5px 8px;font-size:12px;border-radius:4px;margin:6px 0}
#diParams .rq b{font-family:Consolas,monospace}
"""

HTML = """
<div id="vueDisplay" class="grille3" hidden>
 <div class="carte">
  <h2>Fichiers display.ini</h2><div id="diListe" class="arbre" style="max-height:680px"></div>
  <p class="doux petit">Cartes : lecture seule (la carte change par « Appliquer à la carte »). Ma bibliothèque :
   outils_docs/atelier_ecrans/display/. Tasmota : lecture seule, à enregistrer dans ma bibliothèque pour la modifier.</p>
 </div>
 <div class="carte" style="min-width:0">
  <div class="ligne"><b id="diTitre">Choisir un fichier à gauche</b><span id="diSource" class="pastille"></span>
   <span id="diResume" class="doux petit" style="margin-left:auto"></span></div>
  <textarea id="diTexte" rows="14" spellcheck="false" aria-label="Texte du display.ini" disabled></textarea>
  <div id="diErreurs" class="diErreurs" hidden></div>
  <div style="max-height:520px;overflow:auto"><table id="diLignes"></table></div>
  <div class="ligne" style="margin-top:8px"><label class="doux petit" for="diNom">nom dans ma bibliothèque</label>
   <input id="diNom" maxlength="64" pattern="[A-Za-z0-9_-]{1,64}" disabled>
   <button id="diEnregistrer" class="btn prim" type="button" disabled>Enregistrer dans ma bibliothèque</button>
   <button id="diAppliquer" class="btn" type="button" hidden title="Changement d'écran de la carte choisie en haut : diff, broches, page Build">Appliquer à la carte</button></div>
  <div id="diConfirmation" class="carte" hidden style="margin-top:8px"></div>
  <div id="diMessage" class="avert" hidden></div>
  <details id="diNotesBoite" hidden style="margin-top:8px"><summary><b>Notes de terrain</b>
   <span class="doux petit">(réglage essayé, effet constaté ; carte choisie en haut)</span></summary>
   <pre id="diNotes" class="code"></pre>
   <textarea id="diNote" rows="3" aria-label="Nouvelle observation"></textarea>
   <div class="ligne"><button id="diAjoutNote" class="btn" type="button">Ajouter la note</button></div>
  </details>
 </div>
 <div class="carte">
  <h2>Paramètres <span id="diBus" class="pastille bleu"></span></h2>
  <p class="doux petit">Lignes lues par le pilote pour ce bus ; « Ajouter » insère la ligne à sa place, valeurs par défaut.</p>
  <div id="diParams" style="max-height:700px;overflow:auto"></div>
 </div>
</div>
"""

JS = r"""
var D = { ref: null, liste: [], fichier: null, analyse: null, seq: 0, seqA: 0, minuterie: null, prevu: null };
var SOURCES = [['carte', 'Cartes'], ['perso', 'Ma bibliothèque'], ['amont', 'Tasmota (lecture seule)']];

function modeAtelier(m) {
  $('vueInterface').hidden = m !== 'interface'; $('vueDisplay').hidden = m !== 'display';
  Array.prototype.forEach.call(document.querySelectorAll('#modes button'), function (b) { b.classList.toggle('actif', b.getAttribute('data-mode') === m); });
  if (m === 'display' && !D.ref) chargeDisplay();
}
function messageDisplay(t) { var m = $('diMessage'); m.textContent = t || ''; m.hidden = !t; }
function chargeDisplay(ouvrir) {
  return Promise.all([D.ref ? D.ref : requete('GET', '/display/reference'), requete('GET', '/display/liste')]).then(function (r) {
    D.ref = r[0]; D.liste = r[1].fichiers; dessineListeDisplay(); dessineParams();
    if (ouvrir) return ouvreDisplay(ouvrir[0], ouvrir[1]);
  }).catch(function (e) { messageDisplay('Lecture des display.ini impossible : ' + e.message); });
}
function dessineListeDisplay() {
  var l = vide($('diListe'));
  SOURCES.forEach(function (s) {
    var f = D.liste.filter(function (x) { return x.source === s[0]; });
    l.appendChild(el('h3', null, s[1] + ' (' + f.length + ')'));
    f.forEach(function (x) {
      var d = el('div', { tabindex: '0', title: x.rel }, x.nom + (x.pilote ? ' · ' + x.pilote + ' ' + x.largeur + '×' + x.hauteur + ' ' + x.bus : '') + (x.tactile ? ' · tactile' : ''));
      if (D.fichier && D.fichier.source === x.source && D.fichier.nom === x.nom) d.className = 'sel';
      d.onclick = function () { ouvreDisplay(x.source, x.nom); };
      d.onkeydown = function (ev) { if (ev.key === 'Enter') ouvreDisplay(x.source, x.nom); };
      l.appendChild(d);
    });
  });
}
function nomPropose(f) { return (f.source === 'perso' ? f.nom : f.nom.replace(/\.ini$/i, '').replace(/[^A-Za-z0-9_-]+/g, '-')).slice(0, 64); }
function ouvreDisplay(source, nom) {
  var mien = ++D.seq;
  clearTimeout(D.minuterie); ++D.seqA;              // analyse en vol : celle de l'ancien fichier
  return requete('GET', '/display/lire?source=' + encodeURIComponent(source) + '&nom=' + encodeURIComponent(nom)).then(function (r) {
    if (mien !== D.seq) return;
    D.fichier = r; oublieEnregistrement(); messageDisplay('');
    $('diTitre').textContent = r.rel; $('diSource').textContent = r.modifiable ? 'ma bibliothèque' : 'lecture seule';
    $('diTexte').value = r.texte; $('diTexte').disabled = false; $('diNom').disabled = false; $('diNom').value = nomPropose(r);
    $('diEnregistrer').disabled = false; $('diAppliquer').hidden = !r.modifiable;
    $('diNotesBoite').hidden = !r.modifiable; $('diNotes').textContent = r.notes || '(aucune note)';
    afficheAnalyse(r.analyse); dessineListeDisplay();
    return true;
  }).catch(function (e) { if (mien === D.seq) messageDisplay('Ouverture impossible : ' + e.message); return false; });
}
function oublieEnregistrement() { D.prevu = null; $('diConfirmation').hidden = true; }
function analyseDisplay() {
  var mien = ++D.seqA;
  requete('POST', '/display/analyse', { texte: $('diTexte').value }).then(function (a) { if (mien === D.seqA) afficheAnalyse(a); })
    .catch(function (e) { if (mien === D.seqA) messageDisplay('Analyse impossible : ' + e.message); });
}
function titreArg(a) {
  return [a.nom + (a.unite ? ' (' + a.unite + ')' : ''), a.explication, a.valeurs, a.defaut ? 'défaut : ' + a.defaut : '']
    .filter(Boolean).join('\n');
}
function afficheAnalyse(a) {
  D.analyse = a;
  $('diBus').textContent = a.bus || 'bus ?';
  $('diResume').textContent = a.erreurs.length + ' erreur(s), ' + a.avertissements.length + ' avertissement(s)';
  var e = vide($('diErreurs'));
  e.hidden = !a.erreurs.length;
  a.erreurs.forEach(function (m) { e.appendChild(el('div', null, m)); });
  var t = vide($('diLignes'));
  var tete = el('tr'); ['n°', 'ligne', 'section', 'arguments', 'remarques'].forEach(function (h) { tete.appendChild(el('th', null, h)); });
  t.appendChild(tete);
  a.lignes.forEach(function (L) {
    if (!L.texte.trim()) return;
    var tr = el('tr');
    tr.appendChild(el('td', { class: 'num' }, L.n)); tr.appendChild(el('td', { class: 't', title: L.texte }, L.texte));
    tr.appendChild(el('td', null, L.section || ''));
    var td = el('td');
    L.arguments.forEach(function (x) {
      td.appendChild(el('span', { class: 'arg' + (x.nom === '(en trop)' ? ' trop' : ''), title: titreArg(x) }, x.nom + ' = ' + x.valeur));
    });
    tr.appendChild(td);
    var r = el('td');
    L.erreurs.forEach(function (m) { r.appendChild(el('div', { class: 'diErr' }, m)); });
    L.avertissements.forEach(function (m) { r.appendChild(el('div', { class: 'diAv' }, m)); });
    tr.appendChild(r); t.appendChild(tr);
  });
  var g = a.avertissements.filter(function (m) { return !/^ligne \d+ :/.test(m); });   // avertissements du fichier entier
  if (g.length) { var tr2 = el('tr'), c = el('td', { colspan: '5', class: 'diAv' }, g.join(' ; ')); tr2.appendChild(c); t.appendChild(tr2); }
  dessineParams();
}
function dessineParams() {
  var p = vide($('diParams'));
  if (!D.ref) return;
  var bus = D.analyse && D.analyse.bus;
  D.ref.sections.forEach(function (s) {
    if (bus && s.bus.indexOf('tous') < 0 && s.bus.indexOf(bus) < 0) return;
    var b = el('div', { class: 'rq' }), l = el('div', { class: 'ligne' });
    l.appendChild(el('b', null, s.ligne)); l.appendChild(el('span', { class: 'doux petit' }, s.bus.join(', ') + (s.obligatoire && s.obligatoire !== 'non' ? ' · ' + s.obligatoire : '')));
    var aj = el('button', { type: 'button', class: 'btn', style: 'margin-left:auto' }, 'Ajouter');
    aj.disabled = !D.fichier; aj.onclick = function () { ajouteParametre(s.ligne); };
    l.appendChild(aj); b.appendChild(l);
    b.appendChild(el('div', { class: 'rqTexte' }, s.role || ''));
    var args = (bus && s.variantes && s.variantes[bus] && s.ligne !== ':H') ? s.variantes[bus] : (s.arguments || []);
    if (s.ligne === ':H' && bus && s.variantes && s.variantes[bus]) args = args.concat(s.variantes[bus]);
    if (args.length) {
      var ul = el('ul', { class: 'petit' });
      args.forEach(function (x) { ul.appendChild(el('li', null, titreArg(x).replace(/\n/g, ' : ') + (x.repete ? ' (× ' + x.repete + ')' : ''))); });
      b.appendChild(ul);
    }
    if (s.comme) b.appendChild(el('div', { class: 'doux petit' }, 'Arguments : comme ' + s.comme));
    (s.pieges || []).forEach(function (m) { b.appendChild(el('div', { class: 'avert' }, m)); });
    p.appendChild(b);
  });
}
function ajouteParametre(ligne) {
  var mien = D.seq, envoye = $('diTexte').value;
  requete('POST', '/display/inserer', { texte: envoye, ligne: ligne }).then(function (r) {
    if (mien !== D.seq || $('diTexte').value !== envoye) return;     // autre fichier ouvert ou texte retape entre-temps
    clearTimeout(D.minuterie); ++D.seqA; oublieEnregistrement();
    $('diTexte').value = r.texte; afficheAnalyse(r.analyse);
    messageDisplay(ligne + ' ajoutée à sa place, valeurs par défaut : à régler puis enregistrer.');
  }).catch(function (e) { messageDisplay('Ajout impossible : ' + e.message); });
}
function prepareEnregistrement() {
  var nom = $('diNom').value.trim(), texte = $('diTexte').value;
  requete('POST', '/display/diff', { nom: nom, texte: texte }).then(function (d) {
    var c = vide($('diConfirmation')); c.hidden = false;
    if (!d.change) { c.appendChild(el('b', null, 'Rien à écrire : ' + d.rel + ' a déjà ce texte.')); return; }
    D.prevu = { nom: nom, texte: texte, empreinte: d.empreinte };
    c.appendChild(el('b', null, (d.empreinte ? 'Remplacer ' : 'Créer ') + d.rel + ' (+' + d.ajouts + ' −' + d.retraits + ') ?'));
    c.appendChild(el('pre', { class: 'code' }, d.diff));
    c.appendChild(el('div', { class: 'doux petit' }, 'Le catalogue des écrans (outils_docs/schemas/catalogue_ecran.json) est mis à jour avec.'));
    var l = el('div', { class: 'ligne' }), ok = el('button', { type: 'button', class: 'btn prim' }, 'Confirmer l’enregistrement');
    var non = el('button', { type: 'button', class: 'btn' }, 'Annuler');
    ok.onclick = function () { ok.disabled = true; confirmeEnregistrement(); };
    non.onclick = function () { c.hidden = true; D.prevu = null; };
    l.appendChild(ok); l.appendChild(non); c.appendChild(l);
  }).catch(function (e) { messageDisplay('Enregistrement impossible : ' + e.message); });
}
function confirmeEnregistrement() {
  var p = D.prevu;
  requete('POST', '/display/enregistrer', p).then(function (r) {
    $('diConfirmation').hidden = true; D.prevu = null;
    return chargeDisplay(['perso', p.nom]).then(function (relu) {
      messageDisplay('Enregistré : ' + r.ecrits.join(', ') + (relu ? '.' : ', mais la relecture a échoué : recharger la page.'));
    });
  }).catch(function (e) { $('diConfirmation').hidden = true; messageDisplay('Enregistrement refusé : ' + e.message); });
}
function sansCr(s) { return s.split(String.fromCharCode(13)).join('').trim(); }
function appliqueACarte() {
  var f = D.fichier;
  if (!f || f.source !== 'perso') return;
  if (sansCr($('diTexte').value) !== sansCr(f.texte)) { messageDisplay('Enregistrer d’abord le texte modifié : la carte reçoit le fichier de la bibliothèque.'); return; }
  if (!E.env) { messageDisplay('Choisir la carte en haut.'); return; }
  requete('GET', '/catalogue').then(function (c) {
    E.catalogue = c;
    var cle = Object.keys(c.ecrans).filter(function (k) { return c.ecrans[k].display_ini === f.rel; })[0];
    if (!cle) { messageDisplay('Écran absent du catalogue (ligne :H illisible ?).'); return; }
    if (c.ecrans[cle].couleur === false) { messageDisplay('Écran monochrome : pas d’interface LVGL possible.'); return; }
    remplitEcrans(); choisitEcran(cle); $('ecran').value = cle;
    modeAtelier('interface'); proposeChangement();
  }).catch(function (e) { messageDisplay('Catalogue illisible : ' + e.message); });
}
function ajouteNote() {
  var f = D.fichier, t = $('diNote').value;
  if (!f || !t.trim()) return;
  requete('POST', '/display/notes', { nom: f.nom, carte: E.env || null, texte: t }).then(function (r) {
    $('diNotes').textContent = r.notes; $('diNote').value = ''; messageDisplay('Note ajoutée.');
  }).catch(function (e) { messageDisplay('Note refusée : ' + e.message); });
}
Array.prototype.forEach.call(document.querySelectorAll('#modes button'), function (b) {
  b.onclick = function () { modeAtelier(b.getAttribute('data-mode')); };
});
$('diTexte').oninput = function () { oublieEnregistrement(); clearTimeout(D.minuterie); D.minuterie = setTimeout(analyseDisplay, 300); };
$('diNom').oninput = oublieEnregistrement;
$('diAppliquer').onclick = appliqueACarte;
$('diEnregistrer').onclick = prepareEnregistrement;
$('diAjoutNote').onclick = ajouteNote;
"""
