"""Import d'un pages.jsonl ecrit a la main dans l'atelier des ecrans (plan atelier-ecrans A13, spec 2026-11-12 § 5) : HTML,
CSS et JS de la page.

« Importer le pages.jsonl de la carte » (carte qui a un pages.jsonl) : POST /importer, la description importee remplace
celle de la page par `modifie` (donc « Annuler » la rend) ; rien n'est ecrit avant « Ecrire dans le depot », dont le diff
montre ecran.json, pages.jsonl et ecranLvgl.be. Objets `brut` (lignes gardees telles quelles) : cadre hache sur le canevas
quand la ligne porte x, y, w, h, ligne grisee dans la liste, jamais selectionnables ni editables (objets() et objet() les
ecartent). Texte venu du fichier : textContent / title.
"""

CSS = """
.ecran .o.brut{pointer-events:none;outline:1px dashed #ffffff99;color:#ffffffbb;font:11px Consolas,monospace;
  background:repeating-linear-gradient(45deg,#ffffff26 0 6px,transparent 6px 12px)}
.arbre .brut{color:var(--doux);font-style:italic;cursor:default}
"""

HTML = """
  <div id="importBoite" class="ligne" hidden><button id="importer" class="btn" type="button"
   title="Lit le pages.jsonl du dossier de la carte ; rien n'est écrit avant « Écrire dans le dépôt »">Importer le pages.jsonl de la carte</button></div>
  <div id="importMessage" class="avert" hidden></div>"""

JS = r"""
function bruts(page) { return E.desc.objets.filter(function (o) { return o.page === page && o.type === 'brut'; }); }
function messageImport(t) { var m = $('importMessage'); m.textContent = t || ''; m.hidden = !t; }
function dessineImport() {
  var c = E.cartes.filter(function (x) { return x.nom === E.env; })[0] || {};
  $('importBoite').hidden = !c.pages_jsonl;
  I.confirme = null; $('importer').textContent = 'Importer le pages.jsonl de la carte';
}
var I = { confirme: null };
function importePages() {
  var env = E.env, c = E.cartes.filter(function (x) { return x.nom === env; })[0] || {};
  if (W.enCours) return;
  fermeConfirmation(); W.prevu = null;          // un diff affiche avant l'import ne vaut plus pour la description importee
  if (c.description && I.confirme !== env) {     // ecran.json present : modele, liaisons et couleurs seraient perdus a l'ecriture
    I.confirme = env; $('importer').textContent = 'Confirmer l’import (remplace la description)';
    messageImport('Cette carte a déjà une description (ecran.json) : l’import la remplace, sans modèle, liaisons ni couleurs. '
      + 'Cliquer à nouveau pour importer ; « Annuler » la rendra tant que rien n’est écrit.');
    return;
  }
  I.confirme = null; $('importer').textContent = 'Importer le pages.jsonl de la carte';
  messageImport('Lecture du pages.jsonl de ' + env + '…');
  requete('POST', '/importer', { env: env }).then(function (r) {
    if (env !== E.env) return;
    if (lecture() && E.ecranEnv) choisitEcran(E.ecranEnv);
    modifie(function () {
      E.desc = r.description; E.sel = null;
      E.page = pageDesc(1) ? 1 : (E.desc.pages.length ? E.desc.pages[0].n : 0);
    });
    messageImport('Importé de ' + r.source + ' : ' + r.editables + ' objet(s) éditable(s), ' + r.bruts
      + ' ligne(s) gardée(s) telles quelles (hachurées). Aucune liaison importée. Rien n’est écrit avant « Écrire dans le dépôt » ; « Annuler » rend la description d’avant.'
      + (r.avertissements.length ? '\n' + r.avertissements.slice(0, 8).join('\n') + (r.avertissements.length > 8 ? '\n…' : '') : ''));
  }).catch(function (e) { if (env === E.env) messageImport('Import impossible : ' + e.message); });
}
function dessineBruts(ec) {
  bruts(E.page).forEach(function (o) {
    var l = o.ligne || {};
    if ([l.x, l.y, l.w, l.h].some(function (v) { return typeof v !== 'number'; })) return;
    var d = el('div', { class: 'o brut', title: JSON.stringify(l) }, (l.obj || '') + (o.id !== null ? ' ' + o.id : ''));
    d.style.left = l.x + 'px'; d.style.top = l.y + 'px'; d.style.width = l.w + 'px'; d.style.height = l.h + 'px';
    ec.appendChild(d);
  });
}
function listeBruts(ob) {
  bruts(E.page).forEach(function (o) {
    var t = o.texte !== undefined ? o.texte : JSON.stringify(o.ligne);
    ob.appendChild(el('div', { class: 'brut', title: t }, 'brut · ' + (o.ligne && o.ligne.obj ? o.ligne.obj + (o.id !== null ? ' ' + o.id : '') : t.slice(0, 40))));
  });
}
$('importer').onclick = importePages;
"""
