<script type='application/javascript'>
    var objTypeGPIO = "}20'>Aucun}3}265504'>Utilisateur}3}26208'>Option A}3}28448'>Option E}3}232'>Bouton}3}264'>Bouton_n}3}27680'>Bouton_d}3}296'>Bouton_i}3}2128'>Bouton_in}3}27712'>Bouton_id}3}25408'>Bouton_tc}3}2160'>Inter}3}2192'>Inter_n}3}27744'>Inter_d}3}2224'>Relais}3}2256'>Relais_i}3}29312'>Relais_b}3}29344'>Relais_bi}3}2288'>LED}3}2320'>LED_i}3}2352'>Compteur}3}2384'>Compteur_n}3}2416'>PWM}3}2448'>PWM_i}3}2480'>Buzzer}3}2512'>Buzzer_i}3}2544'>LedLink}3}2576'>LedLink_i}3}27648'>Input}3}27968'>Interrupt}3}23840'>Sortie Hi}3}23872'>Sortie Lo}3}28224'>Heartbeat}3}28256'>Heartbeat_i}3}28736'>Reset}3}2608'>I2C SCl}3}2640'>I2C SDa}3}2672'>SPI MISO}3}2704'>SPI MOSI}3}2736'>SPI Clk}3}2768'>SPI CS}3}2800'>SPI DC}3}26720'>CarteSD CS}3}28800'>SDIO Cmd}3}28832'>SDIO Clk}3}28864'>SDIO D0}3}28896'>SDIO D1}3}28928'>SDIO D2}3}28960'>SDIO D3}3}2832'>SSPI MISO}3}2864'>SSPI MOSI}3}2896'>SSPI SClk}3}2928'>SSPI CS}3}2960'>SSPI DC}3}23200'>Série Tx}3}23232'>Série Rx}3}21184'>DHT11}3}21216'>AM2301}3}21248'>SI7021}3}28768'>MS01}3}21280'>DHT11_o}3}23136'>ALux IrRcv}3}23168'>ALux IrSel}3}23008'>MY92x1 DI}3}23040'>MY92x1 DCkI}3}22912'>SM16716 Clk}3}22944'>SM16716 Dat}3}22976'>SM16716 Pwr}3}24032'>SM2135 Clk}3}24064'>SM2135 Dat}3}29088'>SM2335 Clk}3}29120'>SM2335 Dat}3}29664'>BP1658CJ Clk}3}29696'>BP1658CJ Dat}3}29024'>BP5758D Clk}3}29056'>BP5758D Dat}3}24640'>MOODL Tx}3}22592'>HLWBL Sel}3}22624'>HLWBL Sel_i}3}22656'>HLWBL CF1}3}22688'>HLW8012 CF}3}22720'>BL0937 CF}3}23456'>ADE7953 IRq}3}29472'>ADE7953 Rst}3}29568'>ADE7953 CS}3}27296'>CSE7761 Tx}3}27328'>CSE7761 Rx}3}23072'>CSE7766 Tx}3}23104'>CSE7766 Rx}3}22752'>MCP39F5 Tx}3}22784'>MCP39F5 Rx}3}22816'>MCP39F5 Rst}3}29984'>NrgMbus Tx Ena}3}21472'>PZEM0XX Tx}3}21504'>PZEM004 Rx}3}21536'>PZEM016 Rx}3}21568'>PZEM017 Rx}3}28128'>BL0939 Rx}3}25440'>BL0940 Rx}3}28160'>BL0942 Rx}3}27552'>ZC Pulse}3}21792'>SerBr Tx}3}21824'>SerBr Rx}3}24096'>Hibernation}3}28992'>Débit}3}27584'>Effet Hall}3}25536'>ETH Pwr}3}25568'>ETH MDC}3}25600'>ETH MDIO}3}24704'>ADC Entrée}3}24736'>ADC Temp.}3}24768'>ADC Lumière}3}24800'>ADC Bouton}3}24832'>ADC Bouton_i}3}24864'>ADC Distance}3}24896'>ADC CT Power}3}23328'>ADC Manette}3}26816'>ADC pH}3}28544'>ADC MQ}3";
	var objSwitchMode = "}20'>Mode bascule (0 = TOGGLE, 1 = TOGGLE)}3}21'>Mode suivi (0 = OFF, 1 = ON)}3}22'>Mode de suivi inversé (0 = ON, 1 = OFF)}3}23'>Mode bouton-poussoir (0 = TOGGLE, 1 = ON (par défaut))}3}24'>Mode bouton-poussoir inversé (0 = OFF (par défaut), 1 = TOGGLE)}3}25'>Mode bouton-poussoir avec mode appui long (0 = TOGGLE, 1 = ON (par défaut), appui long = HOLD)}3}26'>Mode bouton-poussoir inversé avec mode appui long (0 = OFF (par défaut), 1 = TOGGLE, appui long = HOLD)}3}27'>Mode bouton-poussoir}3}28'>Mode bascule multi-changement (0 = TOGGLE, 1 = TOGGLE, 2x changement = HOLD)}3}29'>Mode de suivi multi-changements (0 = OFF, 1 = ON, 2x changement = HOLD)}3}210'>Mode de suivi inversé multi-changements (0 = ON, 1 = OFF, 2x changement = HOLD)}3}211'>Mode bouton-poussoir avec mode variateur incl. fonction double pression3}212'>Mode bouton-poussoir inversé avec mode variateur incl. fonction double pression}3}213'>Mode \"push to on\" (1 = ON, 0 = rien)}3}214'>Mode \"push to on\" inversé (0 = ON, 1 = rien)}3}215'>Envoi uniquement un message MQTT lors du changement de commutateur}3}216'>Envoi uniquement un message MQTT en cas de changement de commutateur inversé}3";
	
	/* 
	Manipule le DOM pour créer les éléments au titre
	*/
	function ajouteElementTitre(elDiv) {	
		var div;
		var label;
		var select;
		
		if (elDiv == "debitmetre") {	
			// Ajoute des informations à la div 'titre'
			const section2 = qs('[id="titre"]');
			
			div = document.createElement("div");
			section2.appendChild(div);
			
				label = document.createElement("label");
				label.textContent = "Réglage :";
				div.appendChild(label);	
			
				select = document.createElement("select");
				select.id = "reglage";
				div.appendChild(select);		
			
			div = document.createElement("div");
			section2.appendChild(div);
			
				label = document.createElement("label");
				label.textContent = "Sensors Période :";
				div.appendChild(label);	
				
				var input = document.createElement("input");
				input.setAttribute("type", "text");
				input.id = "sensorPeriod";
				input.setAttribute("name", "sensorPeriod");
				input.setAttribute("value", "300");	
				div.appendChild(input);
			div = document.createElement("div");
			section2.appendChild(div);
			
				label = document.createElement("label");
				label.textContent = "Unité de Débit :";
				div.appendChild(label);	
			
				select = document.createElement("select");
				select.id = "unit";
				div.appendChild(select);	
			div = document.createElement("div");
			section2.appendChild(div);
			
				label = document.createElement("label");
				label.textContent = "Source :";
				div.appendChild(label);	
			
				select = document.createElement("select");
				select.id = "source";
				div.appendChild(select);	
		}
	}
	
	/* 
	Manipule le DOM pour créer les éléments
	Pour les éléments suivants : bouton / capteur / relai / debitmetre
	*/
	function ajouteElement(elDiv) {	
		var div;
		var label;
		var select;
		
		// Vérifie si il n'y pas des fieldset cachés à afficher avant d'en créer un nouveau
		qs('#groupe_' + elDiv + 's').style.display = "block";

		// Crée nouveau fieldset
		const section = qs('[id="groupe_' + elDiv + 's"]');
		var nb = qsAll('[name="fieldset_' + elDiv + 's"]').length;
		
		const fieldset = document.createElement("fieldset");
		fieldset.id = "fieldset_" + elDiv + parseInt(nb + 1);
		fieldset.name = "fieldset_" + elDiv + "s";		
		section.appendChild(fieldset);
		
		const legend = document.createElement("legend");
		legend.setAttribute("class", "activable");
		fieldset.appendChild(legend);
		
			div = document.createElement("div");
			legend.appendChild(div);
			
				const b = document.createElement("b");
				if (elDiv == "bouton") {
						b.textContent = "Bouton " + parseInt(nb + 1);
				} else if (elDiv == "relai") {
					b.textContent = "Relai " + parseInt(nb + 1);
				} else if (elDiv == "capteur") {
					b.textContent = "Capteur " + parseInt(nb + 1);
				} else if (elDiv == "thermometre") {
					b.textContent = "Thermomètre " + parseInt(nb + 1);
				} else if (elDiv == "debitmetre") {
					b.textContent = "Débitmètre " + parseInt(nb + 1);
				}
				div.appendChild(b);
				
				const span = document.createElement("span");
				span.setAttribute("class", "fleche");
				span.id = "fleche_" + elDiv + parseInt(nb + 1);
				span.setAttribute("onClick", "afficheParagraphe('fleche_" + elDiv + parseInt(nb + 1) + "', '" + elDiv + parseInt(nb + 1) + "');");
				span.textContent = "▼";
				div.appendChild(span);
				
		div = document.createElement("div");
		div.style.display = "block";
		div.id = elDiv + parseInt(nb + 1);
		div.setAttribute("class", "visible");
		fieldset.appendChild(div);
		
			var div2 = document.createElement("div");
			div.appendChild(div2);

				label = document.createElement("label");
				label.textContent = "Suppression :";
				div2.appendChild(label);			
			
					input = document.createElement("input");
					input.setAttribute("type", "checkbox");
					input.id = elDiv + parseInt(nb + 1) + "_suppression";
					input.setAttribute("name", elDiv + parseInt(nb + 1) + "_suppression");
					input.setAttribute("value", "1");	
					div2.appendChild(input);			
			
			var div2 = document.createElement("div");
			div.appendChild(div2);
			
				var label = document.createElement("label");
				label.textContent = "Activation :";
				div2.appendChild(label);
				
				select = document.createElement("select");
				select.id = elDiv + parseInt(nb + 1) + "_activation";
				select.setAttribute("onChange", 'desactiveFieldset(this);');
				div2.appendChild(select);
					
		if (elDiv == "relai" || elDiv == "capteur" || elDiv == "debitmetre") {				
				div2 = document.createElement("div");
				div.appendChild(div2);
				
					label = document.createElement("label");
					label.textContent = "Nom :";
					div2.appendChild(label);
					
					var input = document.createElement("input");
					input.setAttribute("type", "text");
					input.id = elDiv + parseInt(nb + 1) + "_nom";
					input.setAttribute("value", "");	
					div2.appendChild(input);
		}
		
				div2 = document.createElement("div");
				div.appendChild(div2);
				
					label = document.createElement("label");
					label.textContent = "ID :";
					div2.appendChild(label);
					
					input = document.createElement("input");
					input.setAttribute("type", "text");
					input.id = elDiv + parseInt(nb + 1) + "_id";
					input.setAttribute("value", "");	
					div2.appendChild(input);
					
				div2 = document.createElement("div");
				div.appendChild(div2);
				
					label = document.createElement("label");
					label.textContent = "Pin :";
					div2.appendChild(label);
					
					input = document.createElement("input");
					input.setAttribute("type", "text");
					input.id = elDiv + parseInt(nb + 1) + "_pin";
					input.setAttribute("value", "");	
					div2.appendChild(input);
					
				div2 = document.createElement("div");
				div.appendChild(div2);
				
					label = document.createElement("label");
					label.textContent = "Type :";
					div2.appendChild(label);
					
					select = document.createElement("select");
					select.id = elDiv + parseInt(nb + 1) + "_type";
					div2.appendChild(select);
		if (elDiv == "debitmetre") {
				div2 = document.createElement("div");
				div.appendChild(div2);
				
					label = document.createElement("label");
					label.textContent = "Virtuel :";
					div2.appendChild(label);
					
					select = document.createElement("select");
					select.id = elDiv + parseInt(nb + 1) + "_virtuel";
					div2.appendChild(select);	

				div2 = document.createElement("div");
				div.appendChild(div2);
				
					label = document.createElement("label");
					label.textContent = "Facteur de correction :";
					div2.appendChild(label);
					
					input = document.createElement("input");
					input.setAttribute("type", "text");
					input.id = elDiv + parseInt(nb + 1) + "_facteurCorrection";
					input.setAttribute("value", "");	
					div2.appendChild(input);	
				div2 = document.createElement("div");
					div2.setAttribute("style", "margin-left:60px;width=50%;");
				div.appendChild(div2);
				
					label = document.createElement("label");
					label.textContent = "Débit affiché :";
					div2.appendChild(label);
					
					input = document.createElement("input");
					input.setAttribute("type", "text");
					input.id = elDiv + parseInt(nb + 1) + "_debitAffiche";
					input.setAttribute("value", "");	
					div2.appendChild(input);	
				div2 = document.createElement("div");
					div2.setAttribute("style", "margin-left:60px;width=50%;");
				div.appendChild(div2);
				
					label = document.createElement("label");
					label.textContent = "Débit réel :";
					div2.appendChild(label);
					
					input = document.createElement("input");
					input.setAttribute("type", "text");
					input.id = elDiv + parseInt(nb + 1) + "_debitReel";
					input.setAttribute("value", "");	
					div2.appendChild(input);						
		}
		if (elDiv == "thermometre" || elDiv == "debitmetre") {
				div2 = document.createElement("div");
				div.appendChild(div2);
				
					label = document.createElement("label");
					label.textContent = "Valeur :";
					div2.appendChild(label);
					
					input = document.createElement("input");
					input.setAttribute("type", "text");
					input.id = elDiv + parseInt(nb + 1) + "_value";
					input.setAttribute("value", "");	
					div2.appendChild(input);
		}
		if (elDiv == "bouton" || elDiv == "capteur") {												
				div2 = document.createElement("div");
				div.appendChild(div2);
				
					label = document.createElement("label");
					label.textContent = "SwitchMode :";
					div2.appendChild(label);
					
					select = document.createElement("select");
					select.id = elDiv + parseInt(nb + 1) + "_SwitchMode";
					div2.appendChild(select);
		}
		if (elDiv == "bouton" || elDiv == "capteur" || elDiv == "relai") {
				div2 = document.createElement("div");
				div.appendChild(div2);
				
					label = document.createElement("label");
					label.textContent = "Etat :";
					div2.appendChild(label);
					
					input = document.createElement("input");
					input.setAttribute("type", "text");
					input.id = elDiv + parseInt(nb + 1) + "_etat";
					input.setAttribute("value", "");	
					div2.appendChild(input);
		}			
		if (elDiv == "relai") {	
				div2 = document.createElement("div");
				div.appendChild(div2);
				
					label = document.createElement("label");
					label.textContent = "Timer :";
					div2.appendChild(label);
					
					input = document.createElement("input");
					input.setAttribute("type", "text");
					input.id = "relai" + parseInt(nb + 1) + "_timer";
					input.setAttribute("value", "");	
					div2.appendChild(input);
					
				div2 = document.createElement("div");
				div.appendChild(div2);
				
					label = document.createElement("label");
					label.textContent = "Topic :";
					div2.appendChild(label);
					
					input = document.createElement("input");
					input.setAttribute("type", "text");
					input.id = "relai" + parseInt(nb + 1) + "_topic";
					input.setAttribute("value", "");	
					div2.appendChild(input);
		}
		
		if (elDiv == "bouton" || elDiv == "capteur" || elDiv == "thermometre") {										
				div2 = document.createElement("div");
				div2.textContent = "Relais Liés :";
				div.appendChild(div2);		

				div2 = document.createElement("div");
				div2.setAttribute("class", "relaisLie");
				div.appendChild(div2);		

					var div3;
					for (let i = 1; i < 9; i ++) {
						div3 = document.createElement("div");
						div3.setAttribute("class", "num");
						div3.textContent = i;
						div2.appendChild(div3);	
					}
					
				div2 = document.createElement("div");
				div2.setAttribute("class", "relaisLie");
				div.appendChild(div2);	
					
					for (let i = 1; i < 9; i ++) {
						input = document.createElement("input");
						input.setAttribute("type", "checkbox");
						input.id = elDiv + parseInt(nb + 1) + "_relaisLie_" + parseInt(i);
						input.setAttribute("name", elDiv + parseInt(nb + 1) + "_relaisLie");
						input.setAttribute("value", parseInt(i));	
						div2.appendChild(input);
					}
		}
		
		if (elDiv == "thermometre") {						
				div2 = document.createElement("div");
				div2.setAttribute("class", "relaisLie");
				div.appendChild(div2);	

					label = document.createElement("label");
					label.setAttribute("class", "labelRelaisLie");
					label.textContent = "Limite basse :";
					div2.appendChild(label);

					input = document.createElement("input");
					input.setAttribute("type", "text");
					input.id = elDiv + parseInt(nb + 1) + "_relaisLie_limite1";
					input.setAttribute("value", "");	
					div2.appendChild(input);

				div2 = document.createElement("div");
				div2.setAttribute("class", "relaisLie");
				div.appendChild(div2);	

					label = document.createElement("label");
					label.setAttribute("class", "labelRelaisLie");
					label.textContent = "Limite haute :";
					div2.appendChild(label);

					input = document.createElement("input");
					input.setAttribute("type", "text");
					input.id = elDiv + parseInt(nb + 1) + "_relaisLie_limite2";
					input.setAttribute("value", "");	
					div2.appendChild(input);
		}

		if (elDiv == "bouton" || elDiv == "capteur" || elDiv == "thermometre") {	
				div2 = document.createElement("div");
				div2.setAttribute("class", "relaisLie");
				div.appendChild(div2);	
				
					label = document.createElement("label");
					label.setAttribute("class", "labelRelaisLie");
					label.textContent = "Délai :";
					div2.appendChild(label);
					
					input = document.createElement("input");
					input.setAttribute("type", "text");
					input.id = elDiv + parseInt(nb + 1) + "_relaisLie_delai";
					input.setAttribute("value", "");	
					div2.appendChild(input);
					
				div2 = document.createElement("div");
				div2.textContent = "Type d'action :";
				div2.setAttribute("style", "font-size: 16px;margin-left: 10px;");
				div.appendChild(div2);	

				div2 = document.createElement("div");
				div2.setAttribute("class", "relaisLie");
				div.appendChild(div2);	
				
					input = document.createElement("input");
					input.setAttribute("type", "checkbox");
					input.id = elDiv + parseInt(nb + 1) + "_relaisLie_type_ON";
					input.setAttribute("name", elDiv + parseInt(nb + 1) + "_relaisLie_type");	
					input.setAttribute("value", "ON");	
					input.textContent = "ON";
					div2.appendChild(input);
					
					label = document.createElement("label");
					label.setAttribute("class", "num");
					label.textContent = "ON";
					div2.appendChild(label);
					
					input = document.createElement("input");
					input.setAttribute("type", "checkbox");
					input.id = elDiv + parseInt(nb + 1) + "_relaisLie_type_OFF";
					input.setAttribute("name", elDiv + parseInt(nb + 1) + "_relaisLie_type");	
					input.setAttribute("value", "OFF");
					input.textContent = "OFF";					
					div2.appendChild(input);
					
					label = document.createElement("label");
					label.setAttribute("class", "num");
					label.textContent = "OFF";
					div2.appendChild(label);
					
					input = document.createElement("input");
					input.setAttribute("type", "checkbox");
					input.id = elDiv + parseInt(nb + 1) + "_relaisLie_type_ON-OFF";
					input.setAttribute("name", elDiv + parseInt(nb + 1) + "_relaisLie_type");	
					input.setAttribute("value", "ON/OFF");	
					input.textContent = "ON/OFF";
					div2.appendChild(input);
					
					label = document.createElement("label");
					label.setAttribute("class", "num");
					label.textContent = "ON/OFF";
					div2.appendChild(label);
					
					input = document.createElement("input");
					input.setAttribute("type", "checkbox");
					input.id = elDiv + parseInt(nb + 1) + "_relaisLie_type_Switch";
					input.setAttribute("name", elDiv + parseInt(nb + 1) + "_relaisLie_type");	
					input.setAttribute("value", "Switch");	
					input.textContent = "Switch";
					div2.appendChild(input);
					
					label = document.createElement("label");
					label.setAttribute("class", "num");
					label.textContent = "Switch";
					div2.appendChild(label);
		}
	}
	
    /* Crée élements 'option' des balises 'select' */
	function paramFormulaire(jsonData, url) {
		var tabElements = [];
		
		console.log(JSON.parse(jsonData));
		console.log("categorie=" + recupereParamURL('categorie', url));
	
		// Enregistre le json dans balise html
		eb("jsonData").innerHTML = jsonData;
        eb('categorie').value = recupereParamURL('categorie', url);

        var json = JSON.parse(jsonData)[eb('module').value];
        var jsonDetail;
		
		// Renseignements généraux du module
		ajouteElementTitre(eb('categorie').value.slice(0, -1));
		
        eb('titreCaract').innerHTML = "<b>Module de " + json.name + "</b>";
        eb('name').value = json.name;
        creeOption('activation', json.activation, "}2ON'>ON}3}2OFF'>OFF}3");	
		
		if (eb('categorie').value == "debitmetres") {
			creeOption('reglage', json.reglage, "}2ON'>ON}3}2OFF'>OFF}3");
			eb('sensorPeriod').value = json.sensorPeriod;
			creeOption('unit', json.environnement[eb('categorie').value].unit, "}2l/min'>l/min}3}2m³/h'>m³/h}3");
			creeOption('source', json.environnement[eb('categorie').value].source, "}2average'>moyenne}3}2raw'>instantanée}3");
		}
		
		// Parcours les éléments du module existants dans l'environnement du module (categorie)
		// Si environnement existant & catégorie existe (exemple: boutons)
		if (json.environnement != undefined && json.environnement[eb('categorie').value] != undefined) {
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
		
		// Parcours les éléments du module existants dans l'environnement du module (categorie)
		// Si environnement existant
		if (json.environnement != undefined) {
			// On affiche la 'div d'environnement' (exemple: id=environnement)
			qs("#environnement").style.display = "block";
				
			// Si la catégorie existe (exemple: boutons)
			if (json.environnement[eb('categorie').value] != undefined) {
				// On affiche la 'div d'environnement' (exemple: id=groupe_boutons)
				if (qs("#groupe_" + eb('categorie').value)) {
					qs("#groupe_" + eb('categorie').value).style.display = "block";
				}
			
				// On parcours les elements de la catégorie (exemple: boutons)
				// Création de cette partie si n'existe pas dans l'html
				for (var key in tabElements) {
				//for (var key in json.environnement[eb('categorie').value]) {
					jsonDetail = json.environnement[eb('categorie').value][tabElements[key]];
					
					// On ne crée pas de nouvel élement si 'key' n'est pas un objet
					if (typeof(jsonDetail) != "object") {continue;}
					
					// On rend visible le 'fieldset de l'élément' (exemple: id=fieldset_bouton1) si il existe
					if (qs("#fieldset_" + tabElements[key])) {
						qs("#fieldset_" + tabElements[key]).style.display = "block";
					} else {
						// On la crée sur la page web (DOM HTML)
						console.log("Création d'un nouvel élément " + eb('categorie').value);
						ajouteElement(eb('categorie').value.slice(0, -1));
					}
				}
				
				// On parcours les elements de la catégorie (exemple: boutons)
				// On complète le formulaire
				for (var key in json.environnement[eb('categorie').value]) {
					jsonDetail = json.environnement[eb('categorie').value][key];
					
					// On passe si 'key' n'est pas un objet
					if (typeof(jsonDetail) != "object") {continue;}
					
					// Remplit les champs de formulaires
					// Champs en commun pour tous les éléments
					creeOption(key + '_activation', jsonDetail.activation, "}2ON'>ON}3}2OFF'>OFF}3");
					eb(key + '_id').value = jsonDetail.id;
					eb(key + '_pin').value = jsonDetail.pin;
					creeOption(key + '_type', (jsonDetail.type  >> 5) & 0xffe0, objTypeGPIO);
					
					// Champs spécifiques à un ou  plusieurs type d'éléments
					if (eb('categorie').value == "boutons" || eb('categorie').value == "capteurs" || eb('categorie').value == "relais") {
						eb(key + '_etat').value = jsonDetail.etat;
					}
					if (eb('categorie').value == "boutons" || eb('categorie').value == "capteurs") {
						//eb(key + '_SwitchMode').value = jsonDetail.SwitchMode;
						creeOption(key + '_SwitchMode', jsonDetail.SwitchMode, objSwitchMode);
					}
					if (eb('categorie').value == "boutons" || eb('categorie').value == "capteurs" || eb('categorie').value == "thermometres") {
						qsAll('input[name="' + key + '_relaisLie"]').forEach((checkbox) => {
							if (jsonDetail.relaisLie.ids.includes(parseInt(checkbox.value))) {
								checkbox.checked = true;
							}
						});
						eb(key + '_relaisLie_delai').value = jsonDetail.relaisLie.delai + "s";
						qsAll('input[name="' + key + '_relaisLie_type"]').forEach((checkbox) => {
							if (jsonDetail.relaisLie.type == checkbox.value) {
								checkbox.checked = true;
							}
						});													
					} 
					if (eb('categorie').value == "relais" || eb('categorie').value == "capteurs" || eb('categorie').value == "debitmetres") {
						eb(key + '_nom').value = jsonDetail.nom;
					}
					if (eb('categorie').value == "debitmetres") {
						creeOption(key + '_virtuel', jsonDetail.virtuel, "}2ON'>ON}3}2OFF'>OFF}3");
						eb(key + '_facteurCorrection').value = parseFloat(jsonDetail.facteurCorrection);
						eb(key + '_debitAffiche').value = 254.39;
						eb(key + '_debitReel').value = 254.39 * parseFloat(jsonDetail.facteurCorrection);
					}
					if (eb('categorie').value == "relais") {						
						eb(key + '_timer').value = jsonDetail.timer + "s";
						eb(key + '_topic').value = jsonDetail.publishMQTT.topic;	
					} 
					if (eb('categorie').value == "thermometres" || eb('categorie').value == "debitmetres") {
						eb(key + '_value').value = jsonDetail.value;
						if (eb('categorie').value == "thermometres") {
							eb(key + '_relaisLie_limite1').value = jsonDetail.relaisLie.limites[0] + "°C";
							eb(key + '_relaisLie_limite2').value = jsonDetail.relaisLie.limites[1] + "°C";
						}
					}
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
		
        // Affiche ou efface les fieldsets correspondant au sous module
		qsAll('[name^="fieldset_"]').forEach((fieldset) => {
			if (fieldset.name.split("_")[1] == eb('categorie').value && json.environnement[fieldset.name.split("_")[1]] != undefined) {
                fieldset.style.display = "block";
            } else {
                fieldset.style.display = "none";
            }
        });	
		
		// Modifie le titre du bouton d'ajout d'un élément
		qs('#btn_ajouter_element').innerHTML = "Ajouter un " + eb('categorie').value.slice(0, -1);
		
		/* Lance la déselection des autres checkbox d'un même groupe */
		let ckeckItem = ""
		qsAll('input[name$="_relaisLie_type"]').forEach((checkbox) => {
			checkbox.addEventListener('click', (event) => {
				qsAll('input[name="' + checkbox.name + '"]').forEach((checkbox2) => {
					//console.log(checkbox.id + "_" + checkbox2.id);
					if (checkbox.checked && checkbox2.id != checkbox.id) {
						checkbox2.checked = false;
					}
				});		
			});
		});	
	}
	
	/* Prépare la json modifié pour l'envoi en requête POST */
	function prepareJsonPost() {
		var json = JSON.parse(eb("jsonData").innerHTML)[eb('module').value];	
		var jsonDetail;
		var jsonModifie = {};
		var enteteID = "";
		
		// Pour debug
		console.log("jsonData ->");	console.log(JSON.parse(eb("jsonData").innerHTML));
		console.log("json ->");	console.log(json);

		// Modifie le json avant envoi par requete POST
		json.name = eb('name').value;
		json.activation = eb("activation").value;	
		
		if (eb('categorie').value == "debitmetres") {
			json.reglage = eb("reglage").value;
			json.sensorPeriod = parseInt(eb("sensorPeriod").value);
			json.environnement[eb('categorie').value].unit = eb("unit").value;
			json.environnement[eb('categorie').value].source = eb("source").value;
		}

		qsAll('[name="fieldset_' + eb('categorie').value + '"]').forEach((item) => {
			enteteID = item.id.split("_")[1];
			jsonDetail = json.environnement[eb('categorie').value][enteteID];	
			if (jsonDetail == undefined) {jsonDetail = {};}

			// Modifie le json pour les champs en commun pour tous les éléments
			jsonDetail.activation = eb(enteteID + "_activation").value;
			jsonDetail.id = (eb(enteteID + "_id").value == "" ? 0 : parseInt(eb(enteteID + "_id").value));
			jsonDetail.pin = (eb(enteteID + "_pin").value == "" ? 0 : parseInt(eb(enteteID + "_pin").value));
			jsonDetail.type = ((eb(enteteID + "_type").value << 5) & 0xffe0) + jsonDetail.id - 1;	
			
			// Modifie le json pour les champs spécifiques à un ou  plusieurs type d'éléments
			if (eb('categorie').value == "boutons" || eb('categorie').value == "capteurs" || eb('categorie').value == "relais") {
				jsonDetail.etat = eb(enteteID + "_etat").value;
			}
			if (eb('categorie').value == "boutons" || eb('categorie').value == "capteurs") {
				jsonDetail.SwitchMode = (eb(enteteID + "_SwitchMode").value == "" ? 0 : parseInt(eb(enteteID + "_SwitchMode").value));
			}
			if (eb('categorie').value == "boutons" || eb('categorie').value == "capteurs" || eb('categorie').value == "thermometres") {
				jsonDetail.relaisLie = (jsonDetail.relaisLie == undefined ? {} : jsonDetail.relaisLie);
				jsonDetail.relaisLie["ids"] = [];	
				jsonDetail.relaisLie.ids = (jsonDetail.relaisLie.ids == undefined ? [] : jsonDetail.relaisLie.ids.splice(0, jsonDetail.relaisLie.ids.length));
				qsAll('input[name="' + enteteID + '_relaisLie"]').forEach((checkbox) => {
					if (checkbox.checked) {
						jsonDetail.relaisLie.ids.push(parseInt(checkbox.value));
					}
				});
				jsonDetail.relaisLie.delai = (eb(enteteID + "_relaisLie_delai").value.split("s")[0] == "" ? 0 : parseInt(eb(enteteID + "_relaisLie_delai").value.split("s")[0]));
				
				jsonDetail.relaisLie.type = "";
				qsAll('input[name="' + enteteID + '_relaisLie_type"]').forEach((checkbox) => {
					if (checkbox.checked) {
						jsonDetail.relaisLie.type = checkbox.value;
					}
				});												
			} 
			if (eb('categorie').value == "relais" || eb('categorie').value == "capteurs" || eb('categorie').value == "debitmetre") {
				jsonDetail.nom = eb(enteteID + "_nom").value;
			}
			if (eb('categorie').value == "relais") {						
				jsonDetail.timer = (eb(enteteID + "'_timer'").value.split("s")[0] == "" ? 0 : parseInt(eb(enteteID + "'_timer'").value.split("s")[0]));
				jsonDetail.publishMQTT.topic = eb(enteteID + "_topic").value;	
			} 
			if (eb('categorie').value == "debitmetre") {
				jsonDetail.virtuel = eb(enteteID + "_virtuel").value;
				
				// Calcul du nouveau facteur de correction
				let newFactor = parseFloat(eb(enteteID + '_debitReel').value / (parseFloat(eb(enteteID + '_facteurCorrection').value) * parseFloat(eb(enteteID + '_debitAffiche').value)));//M / (c * D)
				jsonDetail.facteurCorrection = newFactor;
				console.log(enteteID + '_facteurCorrection=' + newFactor);
			}
			if (eb('categorie').value == "thermometres" || eb('categorie').value == "debitmetre") {
				jsonDetail.value = eb(enteteID + "_value").value;
				if (eb('categorie').value == "thermometres") {
					jsonDetail.relaisLie.limites[0] = (eb(enteteID + "_relaisLie_limite1").value.split("°C")[0] == "" ? 0 : parseInt(eb(enteteID + "_relaisLie_limite1").value.split("°C")[0]));
					jsonDetail.relaisLie.limites[1] = (eb(enteteID + "_relaisLie_limite2").value.split("°C")[0] == "" ? 0 : parseInt(eb(enteteID + "_relaisLie_limite2").value.split("°C")[0]));
				}
			}
			
			// Ajoute ou modifie les paramètres du capteur en json
			json.environnement[eb('categorie').value][enteteID] = jsonDetail;		
		});
		
		// Enregistre le json dans balise html
		jsonModifie[eb('module').value] = json;
		eb("jsonData").innerHTML = JSON.stringify(jsonModifie);		
	}
	
	/* Affiche ou efface la fenêtre popup */
	function togglePopup() {
		let popup = qs("#popup-overlay");	  
		
		// Enregistre le choix dans une DIV
		if (popup.className == "open") {
			ajouteElement(qs('#select_elementAAjouter').value);
		}
		
		// Change son apparence
		popup.classList.toggle("open");
	}
	
	function desactiveFieldset(elt) {
		// Selectionne la div parent
		const section = elt.parentNode.parentNode;
		
		// Récupère un tableau de div enfants
		const sectionDivChild = section.children;
		
		for (var i = 0; i < sectionDivChild.length; i ++) {
			var enfants = sectionDivChild[i].children;

			for (var j = 0; j < enfants.length; j ++) {
				if (enfants[j].nodeName == "INPUT" || enfants[j].nodeName == "SELECT") {
					if (enfants[j].id.indexOf("suppression") == -1 && enfants[j].id != elt.id) {
						if (elt.value == "OFF") {
							enfants[j].setAttribute("disabled", "true");
						} else {
							enfants[j].removeAttribute("disabled");
						}
					}
				}
			}
		}
	}
</script>