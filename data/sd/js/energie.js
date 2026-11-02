// Page /energie : trace en SVG, sans bibliotheque (le FS de la carte fait 320 Ko). Valeurs en Wh et en dix-milliemes d'euro.
// f=donnees au chargement, puis toutes les 5 min ; f=direct toutes les 10 s. Chaque graphique expose data-valeurs (banc_energie.py).
(function () {
	var L = 320, H = 90, BAS = 76, HAUT = 12;
	var $ = function (id) { return document.getElementById(id); };
	var url = location.pathname;

	function nombre(v, d) { return v.toFixed(d).replace('.', ','); }
	// Releve sur la carte le 2026-11-02 : 2 Wh par jour, relais coupe la nuit. D'ou les Wh sous 1 kWh et les euros fins sous 1 centime.
	function energie(wh) { return wh < 1000 ? wh + ' Wh' : nombre(wh / 1000, 2) + ' kWh'; }
	function euros(e) { return e > 0 ? nombre(e / 10000, e < 100 ? 4 : 2) + ' €' : '—'; }
	function echappe(t) { return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }

	function barres(id, valeurs, etiquettes) {
		var max = Math.max.apply(null, valeurs.concat([1])), n = valeurs.length, l = L / n, s = '';
		valeurs.forEach(function (v, i) {
			var h = v / max * (BAS - HAUT);
			s += "<rect class='e_barre' x='" + (i * l + 1).toFixed(1) + "' y='" + (BAS - h).toFixed(1) + "' width='" + Math.max(l - 2, 1).toFixed(1) + "' height='" + h.toFixed(1) + "'><title>" + echappe(etiquettes[i]) + ' : ' + energie(v) + "</title></rect>";
			if (etiquettes[i] && (n <= 12 || i % Math.ceil(n / 8) == 0)) s += "<text class='e_txt' x='" + (i * l + l / 2).toFixed(1) + "' y='87' text-anchor='middle'>" + echappe(etiquettes[i]) + '</text>';
		});
		s += "<line class='e_axe' x1='0' x2='" + L + "' y1='" + BAS + "' y2='" + BAS + "'/><text class='e_txt' x='0' y='9'>" + energie(max) + '</text>';
		var g = $(id);
		g.setAttribute('viewBox', '0 0 ' + L + ' ' + H);
		g.setAttribute('data-valeurs', JSON.stringify(valeurs));
		g.innerHTML = s;
	}

	function somme(l) { return l.reduce(function (a, b) { return a + b; }, 0); }
	function total(id, wh, e) {
		$(id).textContent = energie(wh) + ' · ' + euros(e);
		$(id).setAttribute('data-wh', wh);
		$(id).setAttribute('data-euros', e);
	}

	function courbe(points) {
		var max = Math.max.apply(null, points.filter(function (p) { return p !== null; }).concat([1]));
		var d = '', lever = true;
		points.forEach(function (p, i) {
			if (p === null) { lever = true; return; }
			var xy = (i * L / (points.length - 1)).toFixed(1) + ' ' + (BAS - p / max * (BAS - HAUT)).toFixed(1);
			d += lever ? 'M' + xy + 'h0' : 'L' + xy;     // h0 : un point isolé se dessine (extrémités rondes)
			lever = false;
		});
		var g = $('e_c');
		g.setAttribute('viewBox', '0 0 ' + L + ' ' + H);
		g.setAttribute('data-valeurs', JSON.stringify(points));
		g.innerHTML = "<path class='e_ligne' d='" + d + "'/><line class='e_axe' x1='0' x2='" + L + "' y1='" + BAS + "' y2='" + BAS + "'/><text class='e_txt' x='0' y='9'>" + max + " W</text><text class='e_txt' x='0' y='87'>-24 h</text><text class='e_txt' x='" + L + "' y='87' text-anchor='end'>maintenant</text>";
	}

	function prix(liste, jour) {
		var actuel = null;
		liste.forEach(function (p) { if (p[0] <= jour) actuel = p; });
		$('e_prixActuel').textContent = actuel ? 'Prix : ' + nombre(actuel[1] / 10000, 4) + ' €/kWh depuis le ' + actuel[0] : 'Aucun prix saisi : les coûts ne sont pas calculés.';
		var r = $('e_rappel');
		r.hidden = !(actuel && (new Date(jour) - new Date(actuel[0])) / 86400000 > 183);
		if (!r.hidden) r.textContent = 'Le prix a plus de 6 mois : vérifiez votre tarif.';
		if (!$('e_date').value) $('e_date').value = jour;
	}

	// Heure en cours, ni terminee ni ecrite en flash : ajoutee a l'affichage pour coller a « Energie aujourd'hui » de l'accueil
	function enCours(e, wh, liste) {
		var delta = wh === null ? 0 : wh - e.w;
		if (!(delta > 0) || e.a.length == 0) return;
		var p = 0, cout, heure = new Date(e.l * 1000).getUTCHours(), jour = parseInt(e.j.slice(8), 10) - 1, a = e.a[e.a.length - 1];
		liste.forEach(function (x) { if (x[0] <= e.j) p = x[1]; });
		cout = Math.round(delta * p / 1000);
		e.h[heure] += delta; e.he[heure] += cout;
		e.d[jour] += delta; e.de[jour] += cout;
		a[1] += delta; a[2] += cout;
	}

	function donnees() {
		return fetch(url + '?f=donnees').then(function (r) { if (!r.ok) throw r.status; return r.json(); }).then(function (o) {
			var e = o.etat, heures = [], jours = [];
			for (var i = 0; i < 24; i++) heures.push(i + ' h');
			prix(o.prix, o.aujourdhui);
			courbe(o.courbe);
			if (!e) { $('e_msg').textContent = "Aucun relevé pour l'instant : le premier est noté dans les 5 minutes suivant la mise à l'heure."; return; }
			$('e_msg').textContent = '';
			enCours(e, o.wCourant, o.prix);
			var an = parseInt(e.m.slice(0, 4), 10), mo = parseInt(e.m.slice(5, 7), 10), nb = new Date(an, mo, 0).getDate();
			for (i = 1; i <= nb; i++) jours.push(String(i));
			barres('e_h', e.h, heures);
			barres('e_d', e.d.slice(0, nb), jours);
			var mois = e.a.slice(-12);
			barres('e_a', mois.map(function (m) { return m[1]; }), mois.map(function (m) { return m[0].slice(5, 7); }));
			total('e_totalH', somme(e.h), somme(e.he));
			total('e_totalD', somme(e.d), somme(e.de));
			total('e_totalA', somme(mois.map(function (m) { return m[1]; })), somme(mois.map(function (m) { return m[2]; })));
		}).catch(function (x) { $('e_msg').textContent = 'Lecture des relevés impossible (' + x + ').'; });
	}

	function direct() {
		return fetch(url + '?f=direct').then(function (r) { return r.json(); }).then(function (o) {
			var v = function (x) { return typeof x == 'number'; };
			$('e_p').textContent = v(o.p) ? Math.round(o.p) : '--';
			$('e_i').textContent = v(o.i) ? nombre(o.i, 3) : '--';
			$('e_hz').textContent = v(o.hz) ? String(o.hz).replace('.', ',') : '--';
			$('e_f').textContent = v(o.f) ? nombre(o.f, 2) : '--';
			$('e_arc').setAttribute('stroke-dasharray', (v(o.f) ? Math.max(0, Math.min(1, o.f)) * 100 : 0) + ' 100');
		}).catch(function () {});
	}

	$('e_form').addEventListener('submit', function (ev) {
		ev.preventDefault();
		fetch(url, {method: 'POST', body: new URLSearchParams({jour: $('e_date').value, prix: $('e_montant').value})}).then(function (r) {
			return r.json().then(function (o) {
				$('e_msg').textContent = r.ok ? '' : o.erreur;
				if (r.ok) { $('e_montant').value = ''; donnees(); }
			});
		}).catch(function () { $('e_msg').textContent = 'Enregistrement impossible.'; });
	});

	donnees();
	direct();
	setInterval(direct, 10000);
	setInterval(donnees, 300000);
})();
