// Sous-page Tarifs de l'electricite (/energie?f=tarifs) : liste, tarif en vigueur, saisie Base ou HC/HP
(function () {
	var url = '/energie';
	function $(i) { return document.getElementById(i); }
	function nombre(v, d) { return v.toFixed(d).replace('.', ','); }
	function euros(x) { return nombre(x / 10000, 4) + ' €/kWh'; }
	function date(j) { return j.split('-').reverse().join('/'); }

	// Masque (bit n = heure n) -> "22 h-6 h, 14 h-17 h"
	function plages(m) {
		var r = [], h, f;
		for (h = 0; h < 24; h++) {
			if ((m >> h) & 1 && !((m >> ((h + 23) % 24)) & 1)) {
				f = h;
				while ((m >> (f % 24)) & 1) f++;
				r.push(h + ' h-' + (f % 24) + ' h');
			}
		}
		return r.join(', ');
	}

	function ligne(cellules, balise) {
		var tr = document.createElement('tr');
		cellules.forEach(function (c) { var td = document.createElement(balise); td.textContent = c; tr.appendChild(td); });
		return tr;
	}

	function charge() {
		return fetch(url + '?f=donnees').then(function (r) { if (!r.ok) throw r.status; return r.json(); }).then(function (o) {
			var t = $('e_liste'), actuel = null;
			t.textContent = '';
			t.appendChild(ligne(['Depuis le', 'Abonnement', 'Prix', 'Heures creuses'], 'th'));
			o.prix.slice().reverse().forEach(function (p) {
				t.appendChild(ligne(p.length > 2 ? [date(p[0]), 'HC/HP', 'HP ' + euros(p[1]) + ', HC ' + euros(p[2]), plages(p[3])] : [date(p[0]), 'Base', euros(p[1]), ''], 'td'));
			});
			o.prix.forEach(function (p) { if (p[0] <= o.aujourdhui) actuel = p; });
			$('e_prixActuel').textContent = !actuel ? 'Aucun prix saisi : les coûts ne sont pas calculés.'
				: 'Prix : ' + (actuel.length > 2 ? 'HP ' + euros(actuel[1]) + ', HC ' + euros(actuel[2]) : euros(actuel[1])) + ' depuis le ' + date(actuel[0]);
			if (!$('e_date').value) $('e_date').value = o.aujourdhui;
		}).catch(function (x) { $('e_msg').textContent = 'Lecture des tarifs impossible (' + x + ').'; });
	}

	function abonnement() {
		var hchp = $('e_hchp').checked;
		$('e_zoneHc').hidden = !hchp;
		$('e_hc').required = hchp;
		$('e_plages').required = hchp;
		$('e_libelle').textContent = hchp ? 'Heures pleines, prix TTC (€/kWh)' : 'Prix TTC (€/kWh)';
	}
	document.querySelectorAll("input[name='e_abo']").forEach(function (b) { b.addEventListener('change', abonnement); });

	$('e_form').addEventListener('submit', function (ev) {
		ev.preventDefault();
		var champs = {jour: $('e_date').value, prix: $('e_montant').value};
		if ($('e_hchp').checked) { champs.hc = $('e_hc').value; champs.plages = $('e_plages').value; }
		fetch(url, {method: 'POST', body: new URLSearchParams(champs)}).then(function (r) {
			return r.json().then(function (o) {
				$('e_msg').textContent = r.ok ? '' : o.erreur;
				if (r.ok) { $('e_montant').value = ''; $('e_hc').value = ''; charge(); }
			});
		}).catch(function () { $('e_msg').textContent = 'Enregistrement impossible.'; });
	});

	charge();
})();
