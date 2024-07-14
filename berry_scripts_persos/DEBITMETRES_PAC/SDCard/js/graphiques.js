<script type='application/javascript'>
	// Variables pour la mise à jour du graphique
	let categories = new Array();
	let tabSeries = new Array();
	let unite = "";
	let graphique;
	
	/* Génère un débit aléatoire */ 
	function getRandomIntInclusive(min, max) {
		min = Math.ceil(min);
		max = Math.floor(max);
		return Math.floor(Math.random() * (max - min + 1) + min);
	}

	
	/* 
	Manipule le DOM pour créer les éléments au titre
	*/
	function ajouteElementTitre(elDiv) {
		
	}
	
	/* 
	Manipule le DOM pour créer les éléments
	Pour les éléments suivants : bouton / capteur / relai / debitmetre
	*/
	function ajouteElement(elDiv) {	
	
	}
	
	// Récupère l'état des valeurs des débitmètres
	let dataset;
	let debitmetres = {};
	
	// Ajoute une liste déroulante au titre
	const section = eb('groupe_selectParametres');
	var div = document.createElement("div");
		div.setAttribute("style", "display:block;");
		section.appendChild(div);
		
		var label = document.createElement("label");
		label.textContent = "Test Graphique :";
		div.appendChild(label);	
		
		var select = document.createElement("select");
		select.id = "test_graphique";
		div.appendChild(select);
		creeOption('test_graphique', "OFF", "}2ON'>ON}3}2OFF'>OFF}3");
		
	div = document.createElement("div");
		div.setAttribute("style", "display:block;");
		section.appendChild(div);
		
		label = document.createElement("label");
		label.textContent = "Mode de fonctionnement :";
		div.appendChild(label);	
		
		select = document.createElement("select");
		select.id = "mode_fonction";
		div.appendChild(select);
		creeOption('mode_fonction', "NORMAL", "}2NORMAL'>Normal}3}2TEST'>Test de la carte}3}2REGLAGE'>Reglage de la PAC}3");
				
	/* Affichage du graphiquie par défaut */
	graphique = Highcharts.chart('container', {
		series: [],
		colors: ['#C6A90D', '#C0C0C0', '#CD7F32', '#6CC349', '#3B37A8', '#7E3692'],
		chart: {
			backgroundColor: '#dddddd',
			type: 'column',
			inverted: true,
			polar: true
		},
		accessibility: {
			keyboardNavigation: {
				seriesNavigation: {
					mode: 'serialize'
				}
			}
		},
		tooltip: {
			outside: true,
			pointFormat: 'Débit: <b>{point.y}</b><br/>',	/*'{series.name}: <b>{point.y}</b><br/>',*/
			valueSuffix: ' ',
		},
		pane: {
			size: '85%',
			innerSize: '20%',
			endAngle: 270
		},
		xAxis: {
			tickInterval: 1,
			labels: {
				align: 'right',
				useHTML: true,
				allowOverlap: true,
				step: 1,
				y: 3,
				style: {fontSize: '13px'}
			},
			lineWidth: 0
		},
		yAxis: {
			crosshair: {
				enabled: true,
				color: '#333'
			},
			lineWidth: 0,
			tickInterval: 10,
			reversedStacks: false,
			endOnTick: true,
			showLastLabel: true,
			accessibility: {
				description: 'Débits de PAC'
			}
		},
		plotOptions: {
			column: {
				stacking: 'normal',
				borderWidth: 0,
				pointPadding: 0,
				groupPadding: 0.15
			}
		},
		animation: {
            duration: 500
        }
	});
	
    /* Crée élements 'option' des balises 'select' */
	function paramFormulaire(jsonData, url) {
		var tabElements = new Array();
		
		// Enregistre le json dans balise html
		eb("jsonData").innerHTML = jsonData;
        eb('categorie').value = recupereParamURL('categorie', url);
		
		// Complete les modes de fonctionnement
		eb('mode_fonction').value = (JSON.parse(jsonData)[eb('module').value]["reglage"] == "ON" ? "REGLAGE" : "NORMAL");
		
		console.log(JSON.parse(jsonData));
		
        var json = JSON.parse(jsonData)[eb('module').value];
        var jsonDetail;
		
		// Parcours les éléments du module existants dans l'environnement du module (categorie)
		// Si environnement existant & catégorie existe (exemple: boutons)
		if (json != undefined && json.environnement[eb('categorie').value] != undefined && json.activation == "ON") {
			// On parcours les elements de la catégorie (exemple: boutons) pour compter leur nombre
			for (var key in json.environnement[eb('categorie').value]) {
				jsonDetail = json.environnement[eb('categorie').value][key];
					
				// On ne crée pas de nouvel élement si 'key' n'est pas un objet
				if (typeof(jsonDetail) != "object") {continue;}
					
				// Ajoute les clés au tableau 'tabElements'
				tabElements.push(key);
			}
			
			// Puis trie le tableau crée selon les clés
			tabElements.sort();
		}
		
		// Définit les séries de données du graphique
		unite = json.environnement[eb('categorie').value]["unit"];
		tabSeries = [];
		
		for (var key in tabElements) {
			categories.push(json.environnement[eb('categorie').value][tabElements[key]]["nom"].split("Débit ")[1]);
			
			var i = json.environnement[eb('categorie').value][tabElements[key]]["id"] - 1;
			tabSeries[i] = {};
			tabSeries[i]["name"] = json.environnement[eb('categorie').value][tabElements[key]]["nom"].split("Débit")[1];
			
			tabSeries[i]["data"] = [];
			tabSeries[i]["data"].length = tabElements.length;
			for (let j = 0; j < tabElements.length; j++) {
				tabSeries[i]["data"][j] = 0;
				if (j == i) {
					//tabSeries[i]["data"][j] = json.environnement[eb('categorie').value][tabElements[key]]["value"];
					tabSeries[i]["data"][j] = getRandomIntInclusive(0, 150);
				}
			}
		}
		
		// Mets à jour le graphique
		graphique.update(
			{
				title: {
					text: 'Débits de PAC'
				},
				tooltip: {
					outside: true,
					pointFormat: 'Débit: <b>{point.y}</b><br/>',	/*'{series.name}: <b>{point.y}</b><br/>',*/
					valueSuffix: ' ' + unite,
				},
				xAxis: {
					categories: categories,			/* Titre de chaque ligne du graphique*/
					accessibility: {description: 'Débits'}
				},
				series: tabSeries
			},
			true,
			true,
			true
		);
		
		// Parcours les éléments du module existants dans l'environnement du module (categorie)
		// Si environnement existant
		if (json.environnement != undefined) {
			// On affiche la 'div container'
			qs('#container').style.display = "block";

			// Si la catégorie existe (exemple: boutons)
			if (json.environnement[eb('categorie').value] != undefined) {
				// On affiche la 'div d'environnement' (exemple: id=groupe_boutons)
				if (qs("#groupe_" + eb('categorie').value)) {
					qs("#groupe_" + eb('categorie').value).style.display = "block";
				}
			
				// On parcours les elements de la catégorie (exemple: boutons)
				// Création de cette partie si n'existe pas dans l'html
				for (var key in tabElements) {
					
					
				}	
			} else {
				// On regirige vers la 1ere categorie existante
				for (var key in json.environnement) {
					if (typeof(json.environnement[key]) == "object") {
						window.location.assign(window.location.pathname + "?module=" + eb("module").value + "&categorie=" + key);
						break;
					}
				}
			}
		} else {
			// On cache la 'div d'environnement' (exemple: id=environnement) & On sort de la fonction
			if (qs("#environnement")) {
				qs("#environnement").style.display = "none";
				return;
			}
		}
	}
	
	/* Mets à jour régulièrement les données du graphique */
	setInterval(() => {
		(async () => {
			if (eb('test_graphique').value == "ON") {
				eb("mode_fonction").value = "NORMAL";
			}
			
			debitmetres = await fetch(
				'/jsonGraphiques' + window.location.search + '&commande=jsonSensors'
			).then(response => response.json());
			console.log("debitmetres=");
			console.log(debitmetres);
			
			let tabDebitmetres = new Array();
			
			// On parcoure le tableau json
			unite = debitmetres.sensors["Débit"]["Unit"];			
			
			tabSeries = [];
			for (var key in debitmetres.sensors["idDebitmetres"]) {
				var i = debitmetres.sensors["idDebitmetres"][key] - 1;

				tabSeries[i] = {};
				tabSeries[i]["name"] = debitmetres.sensors["nameDebitmetres"][i].split("Débit")[1];
				
				tabSeries[i]["data"] = [];
				tabSeries[i]["data"].length = debitmetres.sensors["idDebitmetres"].length;
				for (let j = 0; j < debitmetres.sensors["idDebitmetres"].length; j++) {
					tabSeries[i]["data"][j] = 0;
					if (j == i) {
						tabSeries[i]["data"][j] = debitmetres.sensors["Débit"]["Rate"][i];
						
						// Si test du graphique html activé
						if (eb('test_graphique').value == "ON") {tabSeries[i]["data"][j] = getRandomIntInclusive(0, 150);}
					}
				}
			}
			
			console.log("tabSeries=");
			console.log(tabSeries);

			graphique.update(
				{
					colors: ['#C6A90D', '#C0C0C0', '#CD7F32', '#6CC349', '#3B37A8', '#7E3692'],
					title: {
						text: 'Débits de PAC'
					},
					tooltip: {
						outside: true,
						pointFormat: 'Débit: <b>{point.y}</b><br/>',	/*'{series.name}: <b>{point.y}</b><br/>',*/
						valueSuffix: ' ' + unite,
					},
					xAxis: {
						categories: categories,			/* Titre de chaque ligne du graphique*/
						accessibility: {description: 'Débits'}
					},
					series: tabSeries
				},
				true,
				true,
				true
			);
		})()
	}, 3000);
	
	/* Evenements sur changement de valeur du formulaire*/
	eb("mode_fonction").addEventListener('change', (event) => {
		if (eb("mode_fonction").value == "REGLAGE" || eb("mode_fonction").value == "TEST") {
			eb('test_graphique').value = "OFF"
			httpRequest("/cm?cmnd=ReglageDebitmetre " + eb("mode_fonction").value + " ON", 'GET', false, '', 'json=' + eb("jsonData").innerHTML);
		} else {
			httpRequest("/cm?cmnd=Backlog ReglageDebitmetre REGLAGE OFF; ReglageDebitmetre TEST OFF;", 'GET', false, '', 'json=' + eb("jsonData").innerHTML);
		}
	});
	
</script>