// /energie en SVG d'apres f=description (sinon DEFAUT). Wh et dix-milliemes d'euro. window.Energie sert aussi l'apercu de l'atelier.
(function () {
	var L = 320, HAUT = 12, HAUTS = {petite: 60, moyenne: 90, grande: 140}, OCTETS = 4096, BLEU = '#4a9eda';
	var TYPES = ['valeur', 'cadran', 'demi-cercle', 'barres', 'courbe', 'aire', 'escalier'];
	var DIRECTS = ['Power', 'Current', 'Factor', 'Frequency', 'Voltage', 'ApparentPower', 'ReactivePower', 'Today', 'Yesterday', 'Total'];
	var CLES = ['type', 'titre', 'source', 'unite', 'couleur', 'largeur', 'hauteur', 'min', 'max', 'total'];
	var CLE_DIRECT = {Power: 'p', Current: 'i', Factor: 'f', Frequency: 'hz'};
	var DEC = {Current: 3, Factor: 2, Voltage: 1, Today: 3, Yesterday: 3, Total: 3};

	function el(t, ti, s, x) {
		var o = {type: t, titre: ti, source: s, couleur: BLEU, largeur: 'demi', hauteur: 'petite'};
		for (var k in x) o[k] = x[k];
		return o;
	}
	function large(t, ti, s, x) { x.largeur = 'pleine'; x.hauteur = 'moyenne'; return el(t, ti, s, x); }
	// = DEFAUT de atelier_energie_description.py (banc node)
	var DEFAUT = {version: 1, elements: [
		el('valeur', 'Puissance', {direct: 'Power'}, {unite: 'W'}),
		el('valeur', 'Courant', {direct: 'Current'}, {unite: 'A'}),
		el('cadran', 'Facteur', {direct: 'Factor'}, {min: 0, max: 1}),
		el('valeur', 'Fréquence', {direct: 'Frequency'}, {unite: 'Hz'}),
		large('barres', "Aujourd'hui par heure", {flash: 'heure', grandeur: 'kWh'}, {total: true}),
		large('barres', 'Ce mois par jour', {flash: 'jour', grandeur: 'kWh'}, {total: true}),
		large('barres', '12 derniers mois', {flash: 'mois', grandeur: 'kWh', nombre: 12}, {total: true}),
		large('courbe', 'Puissance sur 24 h', {flash: 'minutes'}, {})
	]};

	// ---- Validation : memes verdicts que atelier_energie_description.py::valide (cas_energie.json) ----
	function has(o, k) { return k in o; }
	function dans(l, v) { return l.indexOf(v) >= 0; }
	function objet(x) { return x !== null && typeof x === 'object' && !Array.isArray(x); }
	function entier(x, b, h) { return Number.isInteger(x) && x >= b && x <= h; }
	function texte(x, h) { return typeof x === 'string' && Array.from(x).length >= 1 && Array.from(x).length <= h; }

	function valideSource(s, type, ou, m) {
		if (!objet(s)) { m.push(ou + ' : source : objet attendu'); return null; }
		var genres = ['direct', 'total', 'flash'].filter(function (k) { return has(s, k); });
		if (genres.length != 1) { m.push(ou + ' : source : une seule cle'); return null; }
		var g = genres[0], v = s[g], permis = dans(['valeur', 'cadran', 'demi-cercle'], type) ? ['direct', 'total'] : ['flash'];
		var autres = {direct: [], total: ['grandeur'], flash: ['grandeur', 'mois', 'decalage', 'nombre']}[g];
		if (dans(TYPES, type) && !dans(permis, g)) m.push(ou + ' : source ' + g + ' impossible pour ' + type);
		Object.keys(s).forEach(function (k) { if (k != g && !dans(autres, k)) m.push(ou + ' : source : cle ' + k + ' refusee'); });
		if (g == 'direct') {
			if (!dans(DIRECTS, v)) m.push(ou + ' : direct inconnu');
			return null;
		}
		if (g == 'total' && !dans(['jour', 'mois', 'an'], v)) m.push(ou + ' : total inconnu');
		if (g == 'flash' && !dans(['minutes', 'heure', 'jour', 'mois', 'an'], v)) { m.push(ou + ' : flash inconnu'); return null; }
		if (v == 'minutes') {
			if (has(s, 'grandeur')) m.push(ou + ' : grandeur refusee sur minutes');
		} else if (!dans(['kWh', 'euros'], s.grandeur)) m.push(ou + ' : grandeur kWh ou euros');
		if (g != 'flash') return null;
		if (has(s, 'mois') && has(s, 'decalage')) m.push(ou + ' : mois et decalage ensemble');
		if (has(s, 'mois') && (v != 'jour' || typeof s.mois != 'string' || !/^[0-9]{4}-(0[1-9]|1[0-2])$/.test(s.mois))) m.push(ou + ' : mois AAAA-MM, jour seulement');
		if (has(s, 'decalage') && (v != 'jour' || !entier(s.decalage, 0, 23))) m.push(ou + ' : decalage 0..23, jour seulement');
		if (has(s, 'nombre') && (v != 'mois' || !entier(s.nombre, 1, 24))) m.push(ou + ' : nombre 1..24, mois seulement');
		return v;
	}

	function valideElement(e, ou, m) {
		if (!objet(e)) { m.push(ou + ' : element : objet attendu'); return; }
		Object.keys(e).forEach(function (k) { if (!dans(CLES, k)) m.push(ou + ' : cle inconnue ' + k); });
		var t = e.type, jauge = t == 'cadran' || t == 'demi-cercle', periode = valideSource(e.source, t, ou, m);
		if (!dans(TYPES, t)) m.push(ou + ' : type inconnu');
		if (!texte(e.titre, 40)) m.push(ou + ' : titre de 1 a 40 car.');
		if (has(e, 'unite') && !texte(e.unite, 10)) m.push(ou + ' : unite de 1 a 10 car.');
		if (has(e, 'couleur') && !(typeof e.couleur == 'string' && /^#[0-9a-fA-F]{6}$/.test(e.couleur))) m.push(ou + ' : couleur #rrggbb attendue');
		if (has(e, 'largeur') && !dans(['demi', 'pleine'], e.largeur)) m.push(ou + ' : largeur invalide');
		if (has(e, 'hauteur') && !dans(['petite', 'moyenne', 'grande'], e.hauteur)) m.push(ou + ' : hauteur invalide');
		['min', 'max'].forEach(function (k) {
			if (has(e, k) ? !(jauge && typeof e[k] == 'number') : jauge) m.push(ou + ' : ' + k + ' : nombre de jauge seulement');
		});
		if (jauge && e.min >= e.max) m.push(ou + ' : min >= max');
		if (has(e, 'total') && (typeof e.total != 'boolean' || periode === null || periode == 'minutes')) m.push(ou + ' : total : booleen, heure a an seulement');
	}

	function valide(d) {
		if (!objet(d)) return ['description : objet attendu'];
		var m = [], els = d.elements, n;
		Object.keys(d).forEach(function (k) { if (k != 'version' && k != 'elements') m.push('cle inconnue ' + k); });
		if (d.version !== 1) m.push('version : doit valoir 1');
		if (!Array.isArray(els) || !els.length) { m.push('elements : liste non vide attendue'); els = []; }
		else if (els.length > 16) m.push('elements : ' + els.length + ' > 16');
		els.forEach(function (e, i) { valideElement(e, 'element ' + (i + 1), m); });
		n = new TextEncoder().encode(JSON.stringify(d)).length;
		if (n > OCTETS) m.push('taille : ' + n + ' octets > ' + OCTETS);
		return m;
	}

	function nombre(v, d) { return v.toFixed(d).replace('.', ','); }
	// 2 Wh par jour (2026-11-02) : d'ou les Wh et les euros fins
	function energie(wh) { return wh < 1000 ? wh + ' Wh' : nombre(wh / 1000, 2) + ' kWh'; }
	function euros(e) { return e > 0 ? nombre(e / 10000, e < 100 ? 4 : 2) + ' €' : '—'; }
	function echappe(t) { return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/["']/g, '&quot;'); }
	function col(l, i) { return l.map(function (m) { return m[i]; }); }
	function txt(x, y, t, a) { return "<text class='e_txt' x='" + x + "' y='" + y + "'" + (a ? " text-anchor='" + a + "'" : '') + '>' + t + '</text>'; }
	function somme(l) { return l.reduce(function (a, b) { return a + b; }, 0); }
	function lit(dir, c) { var v = dir && dir[CLE_DIRECT[c] || c]; return typeof v == 'number' ? v : null; }
	function formate(c, v) { return c == 'Frequency' ? String(v).replace('.', ',') : nombre(v, DEC[c] || 0); }
	function z(zone, id) { return zone.querySelector('#' + id); }

	// ---- Serie d'un graphique : {v tracees, W Wh, E dix-milliemes, et etiquettes, part, vide, minutes} ----
	function cible(e, s) {
		if (s.mois) return s.mois;
		var a = +e.m.slice(0, 4), m = +e.m.slice(5, 7) - 1 - (s.decalage || 0);
		a += Math.floor(m / 12);
		m = (m % 12 + 12) % 12 + 1;
		return a + '-' + (m < 10 ? '0' : '') + m;
	}
	function serie(don, s) {
		var e = don.etat, f = s.flash, r = {et: []}, i;
		if (f == 'minutes') { r.v = don.courbe || []; r.minutes = true; return r; }
		if (!e) return null;
		if (f == 'heure') {
			r.W = e.h; r.E = e.he;
			for (i = 0; i < 24; i++) r.et.push(i + ' h');
		} else if (f == 'jour') {
			var c = cible(e, s), ar = don.archives && don.archives[c], nb = new Date(+c.slice(0, 4), +c.slice(5, 7), 0).getDate();
			if (c == e.m) ar = {d: e.d, de: e.de};
			if (!ar || typeof ar == 'number') { r.W = []; r.E = []; r.vide = ar == 404 ? 'archive effacée' : 'lecture impossible' + (ar ? ' (' + ar + ')' : ''); }
			else { r.W = ar.d.slice(0, nb); r.E = ar.de.slice(0, nb); }
			for (i = 1; i <= r.W.length; i++) r.et.push(String(i));
		} else if (f == 'mois') {
			var mois = e.a.slice(-(s.nombre || 12));
			r.W = col(mois, 1);
			r.E = col(mois, 2);
			r.et = col(mois, 0).map(function (m) { return m.slice(5, 7); });
		} else {                    // an : annee civile, 2 au plus ; la plus ancienne est partielle s'il lui manque des mois
			var ans = {}, cles;
			e.a.forEach(function (m) { var k = m[0].slice(0, 4), y = ans[k] = ans[k] || [0, 0, 0]; y[0] += m[1]; y[1] += m[2]; y[2]++; });
			cles = Object.keys(ans).sort().slice(-2);
			r.W = cles.map(function (y) { return ans[y][0]; });
			r.E = cles.map(function (y) { return ans[y][1]; });
			if (cles.length > 1 && ans[cles[0]][2] < 12) r.part = 0;
			r.et = cles.map(function (y, k) { return y + (k === r.part ? '*' : ''); });
		}
		r.v = s.grandeur == 'euros' ? r.E : r.W;
		return r;
	}

	// Total d'une valeur : jour, mois ou annee civile en cours
	function totaux(don, t) {
		var e = don.etat;
		if (!e) return null;
		if (t == 'jour') return {wh: somme(e.h), e: somme(e.he)};
		if (t == 'mois') return {wh: somme(e.d), e: somme(e.de)};
		var a = e.a.filter(function (m) { return m[0].slice(0, 4) == e.m.slice(0, 4); });
		return {wh: somme(col(a, 1)), e: somme(col(a, 2))};
	}

	function graphe(g, e, s, h) {
		var bas = h - 14, v = s.v, n = v.length, l = L / Math.max(n, 1), c = e.couleur || BLEU, st = e.type;
		var max = Math.max.apply(null, v.filter(function (p) { return p !== null; }).concat([1]));
		var fmt = s.minutes ? function (p) { return p + ' W'; } : e.source.grandeur == 'euros' ? euros : energie;
		var X = function (i) { return s.minutes ? i * L / Math.max(n - 1, 1) : (i + 0.5) * l; };
		var Y = function (p) { return (bas - p / max * (bas - HAUT)).toFixed(1); };
		var o = '', d = '', run = [];
		g.setAttribute('viewBox', '0 0 ' + L + ' ' + h);
		g.setAttribute('data-valeurs', JSON.stringify(v));
		if (s.vide) { g.innerHTML = txt(L / 2, h / 2, s.vide, 'middle'); return; }
		function ferme() {
			if (!run.length) return;
			if (st == 'aire') d += 'M' + run[0][0] + ' ' + bas + run.map(function (p) { return 'L' + p[0] + ' ' + p[1]; }).join('') + 'L' + run[run.length - 1][0] + ' ' + bas + 'Z';
			else d += 'M' + run[0][0] + ' ' + run[0][1] + 'h0' + run.slice(1).map(function (p) { return st == 'escalier' ? 'H' + p[0] + 'V' + p[1] : 'L' + p[0] + ' ' + p[1]; }).join('');
			run = [];
		}
		v.forEach(function (p, i) {
			if (p === null) { ferme(); return; }       // h0 : point isole visible
			if (st == 'barres') {
				var hb = p / max * (bas - HAUT);
				o += "<rect fill='" + c + "' x='" + (i * l + 1).toFixed(1) + "' y='" + (bas - hb).toFixed(1) + "' width='" + Math.max(l - 2, 1).toFixed(1) + "' height='" + hb.toFixed(1) + "'><title>" + echappe(s.et[i] || '') + (i === s.part ? ' (année partielle)' : '') + ' : ' + echappe(fmt(p)) + '</title></rect>';
			} else run.push([X(i).toFixed(1), Y(p)]);
		});
		ferme();
		if (d) o += "<path class='" + (st == 'aire' ? 'e_aire' : 'e_ligne') + "' d='" + d + "' " + (st == 'aire' ? 'fill' : 'stroke') + "='" + c + "'/>";
		v.forEach(function (p, i) {
			if (s.et[i] && (n <= 12 || i % Math.ceil(n / 8) == 0)) o += txt(X(i).toFixed(1), h - 3, echappe(s.et[i]), 'middle');
		});
		if (s.minutes) o += txt(0, h - 3, '-24 h') + txt(L, h - 3, 'maintenant', 'end');
		g.innerHTML = o + "<line class='e_axe' x1='0' x2='" + L + "' y1='" + bas + "' y2='" + bas + "'/>" + txt(0, 9, fmt(max));
	}

	// Valeur, cadran ou demi-cercle ; champ direct absent : « -- »
	function tuile(div, i, e, don, dir) {
		var co = e.couleur || BLEU, s = e.source, n = null, t = '--', eu = s.grandeur == 'euros', u = '', k, p, dem, arc, pa, ti = echappe(e.titre);
		if (s.direct) {
			n = lit(dir, s.direct);
			if (n !== null) t = formate(s.direct, n);
			u = e.unite ? ' ' + echappe(e.unite) : '';
		} else if ((k = totaux(don, s.total))) {
			n = eu ? k.e / 10000 : k.wh / 1000;
			t = eu ? euros(k.e) : energie(k.wh);
		}
		if (e.type == 'valeur') { div.innerHTML = "<b id='e_v" + i + "' style='color:" + co + "'>" + t + '</b>' + u + '<small>' + ti + '</small>'; return; }
		p = n === null ? 0 : Math.max(0, Math.min(1, (n - e.min) / (e.max - e.min)));
		dem = e.type == 'demi-cercle';
		arc = dem ? 'M30 50 A20 20 0 0 1 70 50' : 'M10 50 A40 40 0 0 1 90 50';
		pa = "d='" + arc + "' pathLength='100' stroke-width='" + (dem ? 40 : 9) + "'";
		div.innerHTML = "<svg viewBox='0 0 100 58' role='img' aria-label=\"" + ti + "\"><path class='e_fond' " + pa + "/><path id='e_a" + i + "' class='e_arc' " + pa + " stroke='" + co + "' stroke-dasharray='" + Math.round(p * 1000) / 10 + " 100'/><text id='e_v" + i + "' x='50' y='48' text-anchor='middle' class='" + (dem ? 'e_cadran e_dem' : 'e_cadran') + "'>" + t + u + '</text></svg><small>' + ti + '</small>';
	}

	function trace(zone, desc, don, dir) {
		zone.innerHTML = desc.elements.map(function (e, i) {
			var cl = 'e_el e_' + (e.largeur || 'demi') + ' e_h_' + (e.hauteur || 'petite'), ti = echappe(e.titre);
			if (e.source.flash) return "<section class='" + cl + "'><h3>" + ti + (e.total ? " <span id='e_t" + i + "' class='e_total'></span>" : '') + "</h3><svg id='e_g" + i + "' class='e_graphe' role='img' aria-label=\"" + ti + '"></svg></section>';
			return "<div id='e_el" + i + "' class='" + cl + " e_tuile'></div>";
		}).join('');
		desc.elements.forEach(function (e, i) {
			var s = e.source.flash && serie(don, e.source), tot;
			if (!e.source.flash) return tuile(z(zone, 'e_el' + i), i, e, don, dir);
			if (!s) return;
			graphe(z(zone, 'e_g' + i), e, s, HAUTS[e.hauteur || 'petite']);
			if (e.total && s.W) {
				tot = z(zone, 'e_t' + i);
				tot.textContent = energie(somme(s.W)) + ' · ' + euros(somme(s.E));
				tot.setAttribute('data-wh', somme(s.W));
				tot.setAttribute('data-euros', somme(s.E));
			}
		});
	}

	// Seuls les champs direct (toutes les 10 s)
	function direct(zone, desc, don, dir) {
		desc.elements.forEach(function (e, i) { if (e.source.direct) tuile(z(zone, 'e_el' + i), i, e, don, dir); });
	}

	// don.archives[AAAA-MM] = {d, de} ou code HTTP
	function archives(base, desc, don) {
		var e = don.etat, mois = {};
		don.archives = {};
		if (!e) return Promise.resolve();
		desc.elements.forEach(function (x) { if (x.source.flash == 'jour') { var c = cible(e, x.source); if (c != e.m) mois[c] = 1; } });
		return Promise.all(Object.keys(mois).map(function (c) {
			return fetch(base + '?f=mois&m=' + c).then(function (r) { return r.ok ? r.json() : r.status; }).catch(function () { return 0; }).then(function (a) { don.archives[c] = a; });
		}));
	}

	window.Energie = {DEFAUT: DEFAUT, valide: valide, trace: trace, direct: direct, archives: archives};

	if (typeof document == 'undefined' || !document.getElementById('e_grille')) return;
	var $ = function (id) { return document.getElementById(id); };
	var url = location.pathname, zone = $('e_grille'), desc = DEFAUT, don = {etat: null, courbe: [], prix: []}, dir = null;

	function note(t) { $('e_note').textContent = t; }
	function ign(m) { note('Description ignorée : ' + m + '.'); return DEFAUT; }

	// Element mal forme : ignore ; erreur d'ensemble : DEFAUT
	function lisDescription() {
		return fetch(url + '?f=description').then(function (r) {
			if (r.status == 404) { note('Description absente : disposition par défaut.'); return DEFAUT; }
			if (!r.ok) return ign('lecture impossible (' + r.status + ')');
			return r.text().then(function (t) {
				var n = new TextEncoder().encode(t).length, o, ent = [], mauvais = {}, lignes = [];
				if (n > OCTETS) return ign(n + ' octets, plus que ' + OCTETS);
				try { o = JSON.parse(t); } catch (x) { return ign('JSON illisible ou tronqué'); }
				valide(o).forEach(function (x) {
					var q = /^element (\d+) : /.exec(x);
					if (!q) ent.push(x);
					else if (!mauvais[q[1]]) { mauvais[q[1]] = 1; lignes.push('Élément ' + q[1] + ' ignoré : ' + x.slice(q[0].length)); }
				});
				if (ent.length) return ign(ent[0]);
				o.elements = o.elements.filter(function (x, i) { return !mauvais[i + 1]; });
				if (!o.elements.length) return ign('aucun élément valable');
				note(lignes.join('\n'));
				return o;
			});
		}).catch(function () { return ign('lecture impossible'); });
	}

	function prix(liste, jour) {
		var actuel = null, r = $('e_rappel');
		liste.forEach(function (p) { if (p[0] <= jour) actuel = p; });
		var vieux = actuel && (new Date(jour) - new Date(actuel[0])) / 86400000 > 183;
		r.hidden = !(vieux || !actuel);
		if (!r.hidden) r.textContent = actuel ? 'Le prix a plus de 6 mois : vérifiez votre tarif.' : 'Aucun prix saisi : les coûts ne sont pas calculés.';
	}

	// Heure en cours (pas en flash) ajoutee, comme l'accueil
	function enCours(e, wh, liste) {
		var delta = wh === null ? 0 : wh - e.w;
		if (!(delta > 0) || e.a.length == 0) return;
		var p = 0, cout, heure = new Date(e.l * 1000).getUTCHours(), jour = +e.j.slice(8) - 1, a = e.a[e.a.length - 1];
		liste.forEach(function (x) { if (x[0] <= e.j) p = x.length > 2 && (x[3] >> heure) & 1 ? x[2] : x[1]; });
		cout = Math.round(delta * p / 1000);
		e.h[heure] += delta; e.he[heure] += cout;
		e.d[jour] += delta; e.de[jour] += cout;
		a[1] += delta; a[2] += cout;
	}

	function lisDonnees() {
		return fetch(url + '?f=donnees').then(function (r) { if (!r.ok) throw r.status; return r.json(); }).then(function (o) {
			prix(o.prix, o.aujourdhui);
			don = o;
			$('e_msg').textContent = o.etat ? '' : "Aucun relevé pour l'instant : le premier est noté dans les 5 minutes suivant la mise à l'heure.";
			if (o.etat) enCours(o.etat, o.wCourant, o.prix);
		}).catch(function (x) { $('e_msg').textContent = 'Lecture des relevés impossible (' + x + ').'; });
	}

	function lisDirect() {
		return fetch(url + '?f=direct').then(function (r) { return r.json(); }).then(function (o) { dir = o; }).catch(function () {});
	}

	// Requetes en parallele, mois, UN trace, puis data-pret
	function rafraichit(premier) {
		return Promise.all([premier ? lisDescription() : desc, lisDonnees(), lisDirect()]).then(function (r) {
			desc = r[0];
			return archives(url, desc, don);
		}).then(function () { trace(zone, desc, don, dir); }).catch(function () {}).then(function () { document.body.dataset.pret = 1; });
	}

	rafraichit(true);
	setInterval(function () { if (document.body.dataset.pret) lisDirect().then(function () { direct(zone, desc, don, dir); }).catch(function () {}); }, 10000);
	setInterval(rafraichit, 300000);
})();
