"""JS de l'ecriture dans le depot et du changement d'ecran de l'atelier des ecrans (plan atelier-ecrans A8, spec § 5.5-5.6).

« Ecrire dans le depot » : POST /diff, liste des fichiers a confirmer dans la page, puis POST /ecrire avec l'empreinte du
diff et celle de ecran.json lue au chargement (E.empreinteDesc) ; lien « Envoyer par la page Build » (E.build).
Changement d'ecran (autre ecran choisi dans l'en-tete, page en lecture seule) : « Proposer le changement » appelle
POST /ecran/diff, dessine la description mise a l'echelle et ses fichiers (display.ini compris), liste avertissements
et refus ; « Changer l'ecran » appelle POST /ecran/changer avec la description d'AVANT la mise a l'echelle (le serveur la
recalcule). Revenir a l'ecran de la carte ou changer de carte oublie la proposition (oublieChangement).
"""

JS = r"""
var W = { prevu: null, changement: null, descAvant: null, enCours: false };

function messageEcriture(texte, lien, libelleLien) {
  var m = vide($('ecritureMessage'));
  m.hidden = !texte;
  if (!texte) return;
  m.appendChild(document.createTextNode(texte));
  if (lien) { var a = el('a', { href: lien, target: '_blank', rel: 'noopener' }, ' ' + libelleLien); m.appendChild(a); }
}
function confirmation(titre, fichiers, libelle, action, details) {
  var c = vide($('confirmation'));
  c.hidden = false;
  c.appendChild(el('b', null, titre));
  (details || []).forEach(function (d) { c.appendChild(el('div', { class: 'avert' }, d)); });
  var ul = el('ul', { class: 'petit' });
  fichiers.forEach(function (f) { ul.appendChild(el('li', null, f.chemin + '  (+' + f.ajouts + ' −' + f.retraits + ')')); });
  if (fichiers.length) c.appendChild(ul);
  var l = el('div', { class: 'ligne' });
  if (action) { var ok = el('button', { type: 'button', class: 'btn prim', id: 'confirmer' }, libelle); ok.onclick = action; l.appendChild(ok); }
  var non = el('button', { type: 'button', class: 'btn' }, action ? 'Annuler' : 'Fermer');
  non.onclick = function () { c.hidden = true; if (W.changement) oublieChangement(true); };
  l.appendChild(non); c.appendChild(l);
}
function fermeConfirmation() { $('confirmation').hidden = true; }

function prepareEcriture() {
  if (lecture() || W.enCours) return;
  messageEcriture('');
  requete('POST', '/diff', { env: E.env, description: E.desc }).then(function (r) {
    W.prevu = r;
    if (!r.fichiers.length) { confirmation('Rien à écrire : les fichiers du dépôt sont déjà ceux-là.', [], '', null); return; }
    confirmation('Écrire ces fichiers dans le dépôt ? (copie de sauvegarde horodatée avant écriture)', r.fichiers, 'Confirmer l’écriture', confirmeEcriture);
  }).catch(function (e) { messageEcriture('Écriture impossible : ' + e.message); });
}
function confirmeEcriture() {
  if (W.enCours) return;
  W.enCours = true; $('confirmer').disabled = true;
  var env = E.env;
  requete('POST', '/ecrire', { env: env, description: E.desc, empreinte: W.prevu.empreinte, empreinte_description: E.empreinteDesc,
                               remarques: Object.keys(R.appliquees).map(Number) })
    .then(function (r) {
      if (env !== E.env) return;
      if (r.remarques) R.liste = r.remarques;
      R.appliquees = {};
      E.empreinteDesc = r.empreinte_description; E.build = r.build; fermeConfirmation();
      E.cartes.forEach(function (c) { if (c.nom === env) c.description = true; });
      messageEcriture('Écrit dans le dépôt : ' + r.ecrits.length + ' fichier(s).', r.build, 'Envoyer par la page Build ↗');
      try { apercu(); dessineEcriture(); dessineRemarques(); } catch (e) {}       // l'ecriture a reussi : pas de « refusee » apres coup
    }, function (e) { fermeConfirmation(); messageEcriture('Écriture refusée : ' + e.message); })
    .then(function () { W.enCours = false; dessineEcriture(); });
}

function oublieChangement(redessine) {
  if (W.descAvant) E.desc = W.descAvant;
  W.changement = null; W.descAvant = null;
  if (redessine) { fermeConfirmation(); dessineTout(); apercu(); }
}
function proposeChangement() {
  var env = E.env, ecran = E.ecran;
  requete('POST', '/ecran/diff', { env: env, ecran: ecran, description: W.descAvant || E.desc }).then(function (r) {
    if (env !== E.env || ecran !== E.ecran) return;
    if (!W.descAvant) W.descAvant = E.desc;
    W.changement = r; E.desc = r.description; E.sel = null;
    E.fichiers = r.fichiers; E.erreurs = []; dessineTout(); dessineFichiers();
    var details = r.refus.map(function (x) { return 'Refus : ' + x; }).concat(r.avertissements);
    confirmation(r.refus.length ? 'Changement d’écran refusé (broches en conflit) :'
                 : 'Changer l’écran de la carte ? Disposition mise à l’échelle (visible sur l’écran ci-dessus) et fichiers :',
                 r.fichiers, 'Changer l’écran', r.refus.length ? null : confirmeChangement, details);
  }).catch(function (e) { messageEcriture('Changement d’écran impossible : ' + e.message); });
}
function confirmeChangement() {
  if (W.enCours) return;
  W.enCours = true; $('confirmer').disabled = true;
  var env = E.env;
  requete('POST', '/ecran/changer', { env: env, ecran: E.ecran, description: W.descAvant, empreinte: W.changement.empreinte,
                                      empreinte_description: E.empreinteDesc })
    .then(function (r) {
      W.changement = null; W.descAvant = null; fermeConfirmation();
      var fait = 'Écran changé (' + r.ecrits.length + ' fichier(s) écrits). Le firmware doit être recompilé et téléversé :';
      return requete('GET', '/cartes').then(function (c) { E.cartes = c.cartes; return chargeCarte(env); }).then(function () {
        messageEcriture(fait, r.build, 'page Build ↗');
      }, function (e) { messageEcriture(fait.replace('.', ', mais la page n’a pas pu se recharger (' + e.message + ').'), r.build, 'page Build ↗'); });
    }, function (e) { fermeConfirmation(); messageEcriture('Changement refusé : ' + e.message); })
    .then(function () { W.enCours = false; dessineEcriture(); });
}

function dessineEcriture() {
  var ro = lecture(), autre = !!(E.ecran && E.ecran !== E.ecranEnv);   // carte sans ecran comprise : lui en donner un
  $('ecrire').disabled = ro || W.enCours;
  $('build').hidden = !E.build || ro;
  if (E.build) $('build').href = E.build;
  var c = vide($('changement'));
  c.hidden = !autre || !!W.changement;
  if (autre && !W.changement) {
    var b = el('button', { type: 'button', class: 'btn prim', id: 'proposeChangement' }, 'Proposer le changement d’écran de la carte');
    b.onclick = proposeChangement; c.appendChild(b);
    c.appendChild(el('span', { class: 'doux petit' }, ' mise à l’échelle, display.ini, broches vérifiées ; rien n’est écrit avant confirmation'));
  }
}
"""
