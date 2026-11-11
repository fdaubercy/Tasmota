/* Page de reglage des durees des volets (/volets), plan visuel-reglage-volets A6.
 * window.VOLETS_REGLAGE = vrPages.facade() + "etat" (vrPages.be::route) ; etat relu par GET /volets?f=etat
 * (vrReglage.be::etatPage) toutes les 500 ms pendant un reglage, 3 s sinon ; ordres par POST /volets (action, id).
 * L'affichage suit TOUJOURS l'etat relu, jamais le seul code de reponse d'un POST (un 500 peut suivre un ordre pris).
 * Carte injoignable : etat et resultat masques (jamais presentes comme a jour). Texte de la carte : textContent seul. */
(function () {
	var D = window.VOLETS_REGLAGE || {}, E = D.etat || {}, joint = true, n = 0, minuterie = null, envoi = false;
	var ETAPES = {pret: 'Prêt', montee: 'Montée en cours', haut: 'En haut', descente: 'Descente en cours', fini: 'Terminé',
		annule: 'Annulé', delai: 'Délai dépassé : aucun appui pendant 120 s', refus: 'Mesure refusée : course de moins de 2 s'};
	var CAUSES = {
		'bloque': 'Cause : bloqué. L\'inclinomètre MPU6050 n\'a vu aucun mouvement alors que le moteur tournait et l\'a coupé. Vérifiez ce qui retient le volet avant de recommencer.',
		'sens inverse': 'Cause : sens inverse. L\'inclinomètre MPU6050 a vu le volet partir dans le mauvais sens et a coupé le moteur. Vérifiez le câblage ou le sens du volet avant de recommencer.',
		'arret': 'Cause : arrêt inattendu. Le volet s\'est arrêté sans appui (commande extérieure, fin de course de Tasmota) : recommencez.'};
	var APPUI = ['« Étape suivante » de cette page (ce volet n\'a pas de bouton déclaré)',
		'le bouton du volet ou « Étape suivante » de cette page',
		'l\'un ou l\'autre des deux boutons du volet, peu importe lequel (▼ fait aussi monter à l\'étape de montée), ou « Étape suivante » de cette page'];
	var DUREES = [['Montée', 'tempsMontee'], ['Descente', 'tempsDescente']];
	var CHEMIN = 'drivers.voletRoulants.environnement.VRs.';

	function $(id) { return document.getElementById(id); }
	function texte(id, t) { $(id).textContent = t || ''; }
	function montre(id, oui) { $(id).hidden = !oui; }
	function sec(v) { return v == null ? '–' : (Math.round(v * 10) / 10).toLocaleString('fr-FR') + ' s'; }
	function ligne(table, cellules, entete) {
		var tr = table.insertRow();
		cellules.forEach(function (c) { var td = document.createElement(entete ? 'th' : 'td'); td.textContent = c; tr.appendChild(td); });
	}

	function resultat() {
		var t = $('rv_durees'), m = E.mesures || {}, a = E.avant || {}, mpu = E.mpu, cle = E.cle || '?';
		t.textContent = '';
		ligne(t, ['', 'Mesurée', 'Avant'].concat(mpu ? ['MPU6050'] : []), true);
		DUREES.forEach(function (d) { ligne(t, [d[0], sec(m[d[1]]), sec(a[d[1]])].concat(mpu ? [sec(mpu[d[1]])] : [])); });
		texte('rv_recopie', DUREES.map(function (d) { return CHEMIN + cle + '.' + d[1] + ' = ' + m[d[1]]; }).join('\n'));
	}

	function rendu() {
		var sel = $('rv_volet'), actif = !!E.actif, et = E.etape;
		if (actif) sel.value = String(E.id);
		sel.disabled = actif || envoi;
		var concerne = E.id != null && String(E.id) === sel.value, connu = concerne && !!E.type, chrono = connu && E.type === 'chrono';
		var course = actif && (et === 'montee' || et === 'descente');
		montre('rv_injoignable', !joint);
		montre('rv_vivant', joint);
		document.querySelectorAll('#rv [data-rv]').forEach(function (b) {
			b.hidden = b.getAttribute('data-rv') !== (!connu ? 'inconnu' : chrono ? 'chrono' : 'moteur');
		});
		texte('rv_appui', APPUI[Math.min((E.boutons || []).length, 2)]);
		var vu = joint && concerne && !!et;
		texte('rv_etape', vu ? 'Étape : ' + (ETAPES[et] || et) : '');
		texte('rv_message', vu ? E.message : '');
		texte('rv_chrono', vu && course ? 'Chronomètre : ' + sec((E.chrono_ms || 0) / 1000) : '');
		texte('rv_question', !vu || !course ? '' : (et === 'montee' ? 'Le volet monte-t-il ? Sinon, Annuler.' : 'Le volet descend-il ? Sinon, Annuler.')
			+ (chrono ? ' La carte ne commande pas la porte : arrêtez-la vous-même si besoin.' : ''));
		texte('rv_cause', vu && !actif ? CAUSES[E.cause] : '');
		var fini = vu && et === 'fini' && !!E.mesures;
		montre('rv_resultat', fini);
		if (fini) resultat();
		montre('rv_debut', joint && !actif);
		montre('rv_suivant', joint && actif);
		$('rv_suivant').textContent = chrono ? (course ? 'Arrivée' : 'Départ') : 'Étape suivante';
		montre('rv_annuler', actif);           // reste offert si la carte ne repond plus : c'est l'arret
		['rv_debut', 'rv_suivant', 'rv_annuler'].forEach(function (b) { $(b).disabled = envoi; });
	}

	// Lecture de l'etat ; une seule chaine de lectures (n : la reponse d'une lecture depassee est ignoree)
	function lire() {
		clearTimeout(minuterie);
		var mien = ++n, ctl = new AbortController(), t = setTimeout(function () { ctl.abort(); }, 4000);
		fetch('/volets?f=etat', {signal: ctl.signal, cache: 'no-store'})
			.then(function (r) { if (!r.ok) throw r.status; return r.json(); })
			.then(function (e) { if (mien === n) { E = e || {}; joint = true; } }, function () { if (mien === n) joint = false; })
			.then(function () {
				clearTimeout(t);
				if (mien !== n) return;
				minuterie = setTimeout(lire, joint && E.actif ? 500 : 3000);     // avant rendu : une erreur d'affichage n'arrete pas la lecture
				rendu();
			}).catch(function () {});
	}

	function ordre(action) {
		var ctl = new AbortController(), t = setTimeout(function () { ctl.abort(); }, 6000);
		envoi = true;
		texte('rv_note', '');
		rendu();
		fetch('/volets', {method: 'POST', body: new URLSearchParams({action: action, id: $('rv_volet').value}), signal: ctl.signal})
			.then(function (r) {
				return r.json().then(function (o) {
					if (!r.ok) texte('rv_note', (o.message || 'Erreur') + ' (réponse ' + r.status + ') : état relu ci-dessus.');
					else if (!o.ok) texte('rv_note', o.message);
				}, function () { texte('rv_note', 'Réponse illisible de la carte (' + r.status + ') : état relu ci-dessus.'); });
			}, function () { texte('rv_note', 'Ordre sans réponse : il a pu être pris ou non, état relu ci-dessus.'); })
			.then(function () { clearTimeout(t); envoi = false; lire(); }).catch(function () {});
	}

	(D.ouvertures || []).forEach(function (o) {
		var opt = document.createElement('option');
		opt.value = String(o.id);
		opt.textContent = o.nom;
		$('rv_volet').appendChild(opt);
	});
	if (E.id != null && E.etape) $('rv_volet').value = String(E.id);
	$('rv_volet').onchange = rendu;
	$('rv_debut').onclick = function () { ordre('debut'); };
	$('rv_suivant').onclick = function () { ordre('appui'); };
	$('rv_annuler').onclick = function () { ordre('annuler'); };
	rendu();
	minuterie = setTimeout(lire, E.actif ? 500 : 3000);
})();
