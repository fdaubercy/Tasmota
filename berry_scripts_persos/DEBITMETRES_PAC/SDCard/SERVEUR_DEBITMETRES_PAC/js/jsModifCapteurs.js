<script type='application/javascript'>
	/* 
	Manipule le DOM pour créer les éléments
	Pour les éléments suivants : bouton / capteur / relai
	@elDiv=identifiant de lélément à ajouter (ex: bouton1)
	@value=identifiant dans le json_sensors
	*/
	function ajouteElement(elDiv) {	
		var btnInvisibleExist = false;
		
		// Vérifie si il n'y pas des fieldset cachés à afficher avant d'en créer un nouveau
		qs('#groupe_' + elDiv.slice(0, -1) + 's').style.display = "block";
		qsAll('[name="btn_modif_' + elDiv.slice(0, -1) + 's"]').forEach((btn) => {
			if (btn.id == "btn_modif_" + elDiv) {
				if (!btnInvisibleExist) {
					if (btn.style.display == "none") {
						btn.style.display = "block";
						btnInvisibleExist = true;
					}
				}
			}
        });	
		
		// Sort de la fonction si un fieldset invisible était présent
		if (btnInvisibleExist) {
			return;
		}
		
		// Crée nouveau bouton
		const section = qs('[id="' + elDiv.slice(0, -1) + 's"]');
		var nb = qsAll('[name="btn_modif_' + elDiv.slice(0, -1) + 's"]').length;
		
		const btn = document.createElement("button");
		btn.setAttribute("style", "display:none;margin:7px 7px 0 7px;max-width:95%;");
		btn.id = "btn_modif_" + elDiv;
		btn.name = "btn_modif_" + elDiv.slice(0, -1) + "s";	
		btn.setAttribute("class", "button bgrn");
		btn.value = ''
		section.appendChild(btn);	
	}
	
    /* Crée élements 'option' des balises 'select' */
	function paramFormulaire(jsonData, url) {
		var json = {};
		
		// Traite la réponse à la demande du json_sensors
		if (recupereParamURL('commande', url) == "jsonSensors") {
			// On complète la donnée value du bouton par le type de composant
			json = JSON.parse(jsonData);
			
			// On parcours le json à la recherche de chaque capteur
			json = JSON.parse(jsonData)["sensors"];
			for (var capteur in json) {	
				var txt = "";
				var valueHTML = "";
						
				// Paramètre le titre
				if (capteur != undefined || capteur != null) {
					valueHTML = capteur.slice(0, capteur.length - 1)
					if (valueHTML == "Button") {
						valueHTML = "Bouton";
					} else if (valueHTML == "Switch") {
						valueHTML = "Inter";
					}

					const btns = qsAll('[value^="' + valueHTML + '"]');
					if (btns != []) {
						btns.forEach((item) => {
							if (item.getAttribute("num") == capteur.slice(capteur.length - 1, capteur.length)) {
								if (valueHTML.indexOf("Bouton") > -1) {
									txt = item.textContent;
									txt = txt.split(": ")[0] + ": " + json[capteur];
								} else if (valueHTML.indexOf("Inter") > -1) {
									txt = item.textContent;
									txt = txt.split(": ")[0] + ": " + json[capteur];
								} else if (valueHTML.indexOf("AM230") > -1) {
									txt = item.textContent;
									txt = txt.split(": ")[0] + ": " + (json[capteur]["Temperature"] == null ? "--.-°C": json[capteur]["Temperature"] + "°C");
								}	

								item.textContent = txt;							
								item.setAttribute("class", "button bred");
								if (json[capteur] == "ON") {item.setAttribute("class", "button bgrn");}								
							}
						});
					}
				}
			}
			
			return;
		}
		
		// Enregistre le json dans balise html
		eb("jsonData").innerHTML = jsonData;	
		
        json = JSON.parse(jsonData)[eb('module').value];
        var jsonDetail;

		// Parcours les éléments du module existants dans l'environnement du module (categorie)
		// Si environnement existant
		if (json.environnement != undefined) {
			// On affiche la 'div d'environnement' (exemple: id=environnement)
			qs("#environnement").style.display = "block";		

			// On parcours chaque catégorie (exemple: boutons)
			for (var categorie in json.environnement) {
				if (json.environnement[categorie] != undefined && qs("#groupe_" + categorie) != undefined) {
					// On affiche la 'div d'environnement' (exemple: id=groupe_boutons)
					if (qs("#groupe_" + categorie)) {
						qs("#groupe_" + categorie).style.display = "block";
						qs("#fieldset_" + categorie).style.display = "block";
					}

					// On parcours les elements de la catégorie (exemple: boutons)
					for (var key in json.environnement[categorie]) {
						jsonDetail = json.environnement[categorie][key];	

						// On rend visible le 'fieldset de l'élément' (exemple: id=fieldset_bouton1) si il existe
						if (qs("#fieldset_" + key)) {
							qs("#fieldset_" + key).style.display = "block";
						} else {
							// On la crée sur la page web (DOM HTML)
							ajouteElement(key);
						}

						// On complète les éléments du bouton
						if (qs("#btn_modif_" + key)) {
							qs("#btn_modif_" + key).style.display = "block";
							
							// Complete la 'value' par le type de componentes & 'num' par l'id du bouton
							var type = jsonDetail.type + jsonDetail.id - 1;
								type = type >> 5;
							
							qs("#btn_modif_" + key).value = JSON.parse(jsonData)["componentes"][type];
							qs("#btn_modif_" + key).setAttribute("num", parseInt(jsonDetail.id));
				
							// Paramètre le titre
							if (JSON.parse(jsonData)["componentes"][type] == "Bouton") {
								qs("#btn_modif_" + key).textContent  = "Bouton" + jsonDetail.id + " de " + jsonDetail.nom + ": " + jsonDetail.etat;
							} else if (JSON.parse(jsonData)["componentes"][type] == "Inter") {
								qs("#btn_modif_" + key).textContent  = jsonDetail.nom + ": " + jsonDetail.etat;
							} else if (JSON.parse(jsonData)["componentes"][type] == "AM2301") {
								qs("#btn_modif_" + key).textContent  = jsonDetail.nom + ": " + jsonDetail.value + "°C";
							}
							
							// Change la couleur du bouton en fonction de la valeur
							if (JSON.parse(jsonData)["componentes"][type] == "Bouton" || JSON.parse(jsonData)["componentes"][type] == "Inter") {
								qs("#btn_modif_" + key).setAttribute("class", "button bred");
								if (jsonDetail.etat == "ON") {
									qs("#btn_modif_" + key).setAttribute("class", "button bgrn");
								}
							}
						}		
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
	
    /* Execute les fonctions une 1ère fois + interval */
    window.addEventListener('load', (event) => {
        setInterval(() => {
			httpRequest("/json" + window.location.search + "&commande=jsonSensors", 'GET', false, paramFormulaire);
		}, 1000);
    });
	
    /* Lance la changement d'état du capteur : Toggle */
 	const btn_modif = qsAll('[id^="btn_modif_"]')
	if (btn_modif != []) {
		btn_modif.forEach((item) => {
			if (item.id.indexOf("btn_modif_") > - 1) {
				if (item.value == "Bouton" || item.value == "Inter") {
					item.addEventListener('click', (event) => {
						httpRequest('/json' + window.location.search + '&commande=toggleSwitch&switchID=' + item.getAttribute("num"), 'GET', false, paramFormulaire);
					});
				}
			}
		});
	}
</script>