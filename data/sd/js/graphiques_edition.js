// graphiques_edition.js - Mode edition de la page /graphiques (2026-10-19, plan graphiques-web A9)
// Charge AVANT graphiques.js, qui appelle window.GraphiquesEdition(api) une fois la page tracee (api : voir la fin
// de graphiques.js). Bouton « Modifier les graphiques » : un brouillon de la composition, edite dans la page ;
// « Enregistrer » l'envoie a la carte (POST /graphiques, graphiques.json), « Annuler » l'abandonne, « Retablir »
// revient a la composition par defaut (cle supprimee sur la carte). Les limites sont controlees ici pour un message
// immediat, et de nouveau par la carte (frontiere systeme) : 8 graphiques, 12 series chacun, titre de 1 a 60 octets.
window.GraphiquesEdition = function (api) {
  'use strict';
  var MAX_GRAPHIQUES = 8, MAX_SERIES = 12, MAX_TITRE = 60;
  var NOMS_TYPES = {courbe: 'Courbes', barres: 'Barres', escalier: 'Escalier', aire: 'Aires'};
  var brouillon = null;
  var panneau = document.getElementById('g_edition');
  var bouton = document.getElementById('g_modifier');

  function el(balise, attributs, texte) {
    var e = document.createElement(balise);
    Object.keys(attributs || {}).forEach(function (k) { e.setAttribute(k, attributs[k]); });
    if (texte !== undefined) e.textContent = texte;
    return e;
  }

  function liste(valeurs, libelles, valeur, classe) {
    var s = el('select', {'class': classe});
    valeurs.forEach(function (v, i) { var o = el('option', {value: v}, libelles[i]); s.appendChild(o); });
    s.value = valeur;
    return s;
  }

  function octets(texte) { return new TextEncoder().encode(texte).length; }

  function etatEdition(texte, erreur) {
    var m = document.getElementById('g_ed_msg');
    m.textContent = texte || '';
    m.style.color = erreur ? '#ff5661' : '';
  }

  // ---- Lecture du formulaire dans le brouillon ----------------------------------------------------
  function relit() {
    var cartes = panneau.querySelectorAll('.g_ed_graphique');
    brouillon = Array.prototype.map.call(cartes, function (carte) {
      var g = {titre: carte.querySelector('.g_ed_titre').value.trim(), periode: carte.querySelector('.g_ed_periode').value,
               type: carte.querySelector('.g_ed_type').value};
      if (carte.querySelector('.g_ed_autres').checked) {
        g.series = 'autres';
      } else {
        g.series = [];
        Array.prototype.forEach.call(carte.querySelectorAll('.g_ed_serie'), function (ligne) {
          if (!ligne.querySelector('input').checked) return;
          var s = {chemin: ligne.getAttribute('data-chemin')};
          var t = ligne.querySelector('select').value;
          if (t) s.type = t;
          g.series.push(s);
        });
      }
      return g;
    });
    return brouillon;
  }

  // Erreur de la composition, ou '' : memes limites que la carte
  function verifie(c) {
    if (c.length > MAX_GRAPHIQUES) return 'Au plus ' + MAX_GRAPHIQUES + ' graphiques.';
    for (var i = 0; i < c.length; i++) {
      var g = c[i], nom = '« ' + (g.titre || 'sans titre') + ' » : ';
      if (!g.titre || octets(g.titre) > MAX_TITRE) return 'Graphique ' + (i + 1) + ' : titre de 1 à ' + MAX_TITRE + ' caractères.';
      if (g.series !== 'autres' && g.series.length === 0) return nom + 'cocher au moins une série, ou « toutes les autres ».';
      if (g.series !== 'autres' && g.series.length > MAX_SERIES) return nom + 'au plus ' + MAX_SERIES + ' séries.';
    }
    return '';
  }

  // ---- Formulaire ---------------------------------------------------------------------------------
  function carteGraphique(g, i, n) {
    var carte = el('fieldset', {'class': 'g_ed_graphique'});
    carte.appendChild(el('legend', {}, 'Graphique ' + (i + 1)));
    var ligne = el('div', {'class': 'g_ed_ligne'});
    var titre = el('input', {'class': 'g_ed_titre', type: 'text', maxlength: String(MAX_TITRE), placeholder: 'Titre'});
    titre.value = g.titre || '';
    ligne.appendChild(titre);
    ligne.appendChild(liste(api.TYPES, api.TYPES.map(function (t) { return NOMS_TYPES[t]; }), g.type || 'courbe', 'g_ed_type'));
    var periodes = api.periodes();
    if (periodes.indexOf(g.periode) < 0 && g.periode) periodes.push(g.periode);
    ligne.appendChild(liste(periodes, periodes.map(api.libellePeriode), g.periode || 'jour', 'g_ed_periode'));
    [['g_ed_monter', '▲', 'Monter', i === 0], ['g_ed_descendre', '▼', 'Descendre', i === n - 1],
     ['g_ed_supprimer', '✕', 'Supprimer ce graphique', false]].forEach(function (b) {
      var bt = el('button', {'class': b[0], type: 'button', title: b[2]}, b[1]);
      bt.disabled = b[3];
      bt.onclick = function () { deplace(i, b[0]); };
      ligne.appendChild(bt);
    });
    carte.appendChild(ligne);

    var autres = el('input', {'class': 'g_ed_autres', type: 'checkbox'});
    autres.checked = g.series === 'autres';
    var etiquette = el('label', {'class': 'g_ed_choix'});
    etiquette.appendChild(autres);
    etiquette.appendChild(document.createTextNode(' Toutes les séries placées dans aucun autre graphique (et les nouvelles)'));
    carte.appendChild(etiquette);

    var choisies = Array.isArray(g.series) ? g.series : [];
    var chemins = api.series();
    choisies.forEach(function (s) { if (chemins.indexOf(s.chemin) < 0) chemins.push(s.chemin); });   // absentes gardees
    var zone = el('div', {'class': 'g_ed_series'});
    chemins.forEach(function (c) {
      var s = choisies.filter(function (x) { return x.chemin === c; })[0];
      var l = el('div', {'class': 'g_ed_serie', 'data-chemin': c});
      var lab = el('label');
      var coche = el('input', {type: 'checkbox'});
      coche.checked = !!s;
      lab.appendChild(coche);
      lab.appendChild(document.createTextNode(' ' + api.legende(c) + (api.series().indexOf(c) < 0 ? ' (absente)' : '')));
      l.appendChild(lab);
      l.appendChild(liste([''].concat(api.TYPES), ['type du graphique'].concat(api.TYPES.map(function (t) { return NOMS_TYPES[t]; })),
                          (s && s.type) || '', ''));
      zone.appendChild(l);
    });
    zone.style.display = autres.checked ? 'none' : '';
    autres.onchange = function () { zone.style.display = autres.checked ? 'none' : ''; };
    carte.appendChild(zone);
    return carte;
  }

  function dessine() {
    var cartes = document.getElementById('g_ed_cartes');
    cartes.innerHTML = '';
    brouillon.forEach(function (g, i) { cartes.appendChild(carteGraphique(g, i, brouillon.length)); });
    document.getElementById('g_ed_ajouter').disabled = brouillon.length >= MAX_GRAPHIQUES;
  }

  function deplace(i, action) {
    relit();
    if (action === 'g_ed_supprimer') brouillon.splice(i, 1);
    else {
      var j = action === 'g_ed_monter' ? i - 1 : i + 1;
      var g = brouillon[i]; brouillon[i] = brouillon[j]; brouillon[j] = g;
    }
    dessine();
  }

  // ---- Actions ------------------------------------------------------------------------------------
  function ouvre() {
    brouillon = api.composition();
    panneau.innerHTML = '';
    panneau.appendChild(el('h3', {}, 'Modifier les graphiques'));
    panneau.appendChild(el('div', {id: 'g_ed_cartes'}));
    var pied = el('div', {'class': 'g_ed_pied'});
    [['g_ed_ajouter', 'Ajouter un graphique'], ['g_ed_enregistrer', 'Enregistrer sur la carte'], ['g_ed_annuler', 'Annuler'],
     ['g_ed_retablir', 'Rétablir la composition par défaut']].forEach(function (b) {
      pied.appendChild(el('button', {id: b[0], type: 'button'}, b[1]));
    });
    panneau.appendChild(pied);
    panneau.appendChild(el('p', {id: 'g_ed_msg'}));
    dessine();
    document.getElementById('g_ed_ajouter').onclick = function () {
      relit();
      brouillon.push({titre: 'Graphique ' + (brouillon.length + 1), periode: 'jour', type: 'courbe', series: []});
      dessine();
    };
    document.getElementById('g_ed_enregistrer').onclick = function () { envoie(relit()); };
    document.getElementById('g_ed_annuler').onclick = ferme;
    document.getElementById('g_ed_retablir').onclick = function () { envoie(null); };
    panneau.style.display = '';
    bouton.style.display = 'none';
    api.montre(false);
  }

  function ferme() {
    panneau.style.display = 'none';
    panneau.innerHTML = '';
    bouton.style.display = '';
    api.montre(true);
  }

  // Envoi a la carte (null = Retablir) ; en cas de refus, l'edition reste ouverte avec le message de la carte
  function envoie(composition) {
    var erreur = composition ? verifie(composition) : '';
    if (erreur) { etatEdition(erreur, true); return; }
    etatEdition('Enregistrement...');
    Array.prototype.forEach.call(panneau.querySelectorAll('button'), function (b) { b.disabled = true; });
    api.enregistre(composition).then(function (r) {
      ferme();
      return api.applique(r.graphiques).then(function () {
        api.message(composition ? 'Composition enregistrée sur la carte.' : 'Composition par défaut rétablie.');
      });
    }).catch(function (e) {
      Array.prototype.forEach.call(panneau.querySelectorAll('button'), function (b) { b.disabled = false; });
      dessine();
      etatEdition(e.message, true);
    });
  }

  bouton.style.display = '';
  bouton.onclick = ouvre;
};
