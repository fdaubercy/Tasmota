<script type='application/javascript'>
	var objTypeGPIO = "}20'>Aucun}3}265504'>Utilisateur}3}26208'>Option A}3}28448'>Option E}3}232'>Bouton}3}264'>Bouton_n}3}27680'>Bouton_d}3}296'>Bouton_i}3}2128'>Bouton_in}3}27712'>Bouton_id}3}25408'>Bouton_tc}3}2160'>Inter}3}2192'>Inter_n}3}27744'>Inter_d}3}2224'>Relais}3}2256'>Relais_i}3}29312'>Relais_b}3}29344'>Relais_bi}3}2288'>LED}3}2320'>LED_i}3}2352'>Compteur}3}2384'>Compteur_n}3}2416'>PWM}3}2448'>PWM_i}3}2480'>Buzzer}3}2512'>Buzzer_i}3}2544'>LedLink}3}2576'>LedLink_i}3}27648'>Input}3}27968'>Interrupt}3}23840'>Sortie Hi}3}23872'>Sortie Lo}3}28224'>Heartbeat}3}28256'>Heartbeat_i}3}28736'>Reset}3}2608'>I2C SCl}3}2640'>I2C SDa}3}2672'>SPI MISO}3}2704'>SPI MOSI}3}2736'>SPI Clk}3}2768'>SPI CS}3}2800'>SPI DC}3}26720'>CarteSD CS}3}28800'>SDIO Cmd}3}28832'>SDIO Clk}3}28864'>SDIO D0}3}28896'>SDIO D1}3}28928'>SDIO D2}3}28960'>SDIO D3}3}2832'>SSPI MISO}3}2864'>SSPI MOSI}3}2896'>SSPI SClk}3}2928'>SSPI CS}3}2960'>SSPI DC}3}23200'>Série Tx}3}23232'>Série Rx}3}21184'>DHT11}3}21216'>AM2301}3}21248'>SI7021}3}28768'>MS01}3}21280'>DHT11_o}3}23136'>ALux IrRcv}3}23168'>ALux IrSel}3}23008'>MY92x1 DI}3}23040'>MY92x1 DCkI}3}22912'>SM16716 Clk}3}22944'>SM16716 Dat}3}22976'>SM16716 Pwr}3}24032'>SM2135 Clk}3}24064'>SM2135 Dat}3}29088'>SM2335 Clk}3}29120'>SM2335 Dat}3}29664'>BP1658CJ Clk}3}29696'>BP1658CJ Dat}3}29024'>BP5758D Clk}3}29056'>BP5758D Dat}3}24640'>MOODL Tx}3}22592'>HLWBL Sel}3}22624'>HLWBL Sel_i}3}22656'>HLWBL CF1}3}22688'>HLW8012 CF}3}22720'>BL0937 CF}3}23456'>ADE7953 IRq}3}29472'>ADE7953 Rst}3}29568'>ADE7953 CS}3}27296'>CSE7761 Tx}3}27328'>CSE7761 Rx}3}23072'>CSE7766 Tx}3}23104'>CSE7766 Rx}3}22752'>MCP39F5 Tx}3}22784'>MCP39F5 Rx}3}22816'>MCP39F5 Rst}3}29984'>NrgMbus Tx Ena}3}21472'>PZEM0XX Tx}3}21504'>PZEM004 Rx}3}21536'>PZEM016 Rx}3}21568'>PZEM017 Rx}3}28128'>BL0939 Rx}3}25440'>BL0940 Rx}3}28160'>BL0942 Rx}3}27552'>ZC Pulse}3}21792'>SerBr Tx}3}21824'>SerBr Rx}3}24096'>Hibernation}3}28992'>Débit}3}27584'>Effet Hall}3}25536'>ETH Pwr}3}25568'>ETH MDC}3}25600'>ETH MDIO}3}24704'>ADC Entrée}3}24736'>ADC Temp.}3}24768'>ADC Lumière}3}24800'>ADC Bouton}3}24832'>ADC Bouton_i}3}24864'>ADC Distance}3}24896'>ADC CT Power}3}23328'>ADC Manette}3}26816'>ADC pH}3}28544'>ADC MQ}3";
	
    /* Crée élements 'option' des balises 'select' */
	function paramFormulaire(jsonData, url) {
		console.log("url=" + url);
		console.log("categorie=" + recupereParamURL('categorie', url));
		console.log(JSON.parse(jsonData));
		
		
		// Enregistre le json dans balise html
		eb("jsonData").innerHTML = jsonData;
		
        var json = JSON.parse(jsonData)["serveur"];
        var jsonDetail;

        //eb('module').value = eb('module').value;
        eb('categorie').value = recupereParamURL('categorie', url);
        eb('titreCaract').innerHTML = "<b>Module de " + json.nom + "</b>";
        
        creeOption('activation', json.activation, "}2ON'>ON}3}2OFF'>OFF}3");
		eb('nom').value = json.nom;
		eb('hostname').value = json.hostname;
		creeOption('mDNS', json.mDNS, "}2ON'>ON}3}2OFF'>OFF}3");
		
		// Remplit les champs de formulaires
		if (eb('categorie').value == "generale") {
			// Initialise le json
			enteteID = "ip";
			jsonDetail = json[enteteID];
			
			// Affiche ou efface les fieldsets correspondant aux relais existants
			if (jsonDetail == undefined) {
				if (qs("#fieldset_" + enteteID)) {
					qs("#groupe_" + enteteID).style.display = "none";
					qs("#fieldset_" + enteteID).style.display = "none";
				}
			} else {
				qs("#groupe_" + enteteID).style.display = "block";
				qs("#fieldset_" + enteteID).style.display = "block";
				
				eb('ipServeur').value = jsonDetail.IPAddress;
				eb('ipGateway').value = jsonDetail.IPGateway;
				eb('Subnet').value = jsonDetail.Subnet;
				eb('DNSServer').value = jsonDetail.DNSServer;
			}
		} else if (eb('categorie').value == 'wifi') {
			// Initialise le json
			enteteID = "wifi";
			jsonDetail = json[enteteID];

			// Affiche ou efface les fieldsets correspondant aux relais existants
			if (jsonDetail == undefined) {
				if (qs("#fieldset_" + enteteID)) {
					qs("#groupe_" + enteteID).style.display = "none";
					qs("#fieldset_" + enteteID).style.display = "none";
				}
			} else {
				qs("#groupe_" + enteteID).style.display = "block";
				qs("#fieldset_" + enteteID).style.display = "block";
				
				eb('wifi_power').value = jsonDetail.power;
				creeOption('wifi_selectSignalFort', jsonDetail.selectSignalFort, "}2ON'>ON}3}2OFF'>OFF}3");
				creeOption('wifi_reScanBy44', jsonDetail.reScanBy44, "}2ON'>ON}3}2OFF'>OFF}3");
				eb('wifi_reseau1_nomReseauWifi').value = jsonDetail.reseau1.nomReseauWifi;
				eb('wifi_reseau1_mdpWifi').value = jsonDetail.reseau1.mdpWifi;
				eb('wifi_reseau2_nomReseauWifi').value = jsonDetail.reseau2.nomReseauWifi;
				eb('wifi_reseau2_mdpWifi').value = jsonDetail.reseau2.mdpWifi;
			}
		} else if (eb('categorie').value == 'localisation') {
			// Initialise le json
			enteteID = "localisation";
			jsonDetail = json[enteteID];

			// Affiche ou efface les fieldsets correspondant aux relais existants
			if (jsonDetail == undefined) {
				if (qs("#fieldset_" + enteteID)) {
					qs("#groupe_" + enteteID).style.display = "none";
					qs("#fieldset_" + enteteID).style.display = "none";
				}
			} else {
				qs("#groupe_" + enteteID).style.display = "block";
				qs("#fieldset_" + enteteID).style.display = "block";

				eb('localisation_latitude').value = jsonDetail.latitude;
				eb('localisation_longitude').value = jsonDetail.longitude;
			}
		} else if (eb('categorie').value == 'mqtt') {
			// Initialise le json
			enteteID = "mqtt";
			jsonDetail = json[enteteID];

			// Affiche ou efface les fieldsets correspondant aux relais existants
			if (jsonDetail == undefined) {
				if (qs("#fieldset_" + enteteID)) {
					qs("#groupe_" + enteteID).style.display = "none";
					qs("#fieldset_" + enteteID).style.display = "none";
				}
			} else {
				qs("#groupe_" + enteteID).style.display = "block";
				qs("#fieldset_" + enteteID).style.display = "block";

				creeOption('mqtt_activation', jsonDetail.activation, "}2ON'>ON}3}2OFF'>OFF}3");
				eb('mqtt_hote').value = jsonDetail.hote;
				eb('mqtt_port').value = jsonDetail.port;
				eb('mqtt_client').value = jsonDetail.client;
				eb('mqtt_utilisateur').value = jsonDetail.utilisateur;
												
				eb('mqtt_mdp').value = jsonDetail.mdp;
				eb('mqtt_topic').value = jsonDetail.topic;
				
				eb('mqtt_groupTopic1').value = jsonDetail.groupTopic1;
				eb('mqtt_groupTopic2').value = jsonDetail.groupTopic2;
				eb('mqtt_groupTopic3').value = jsonDetail.groupTopic3;
			}
		} else if (eb('categorie').value == 'fuseauHoraire') {
			// Initialise le json
			enteteID = "fuseauHoraire";
			jsonDetail = json[enteteID];

			// Affiche ou efface les fieldsets correspondant aux relais existants
			if (jsonDetail == undefined) {
				if (qs("#fieldset_" + enteteID)) {
					qs("#groupe_" + enteteID).style.display = "none";
					qs("#fieldset_" + enteteID).style.display = "none";
				}
			} else {
				qs("#groupe_" + enteteID).style.display = "block";
				qs("#fieldset_" + enteteID).style.display = "block";

				eb('fuseauHoraire_timezone').value = jsonDetail.timezone;
				var heures = "}20'>0}3}21'>01}3}22'>02}3}23'>03}3}24'>04}3}25'>05}3}26'>06}3}27'>07}3}28'>08}3}29'>09}3}210'>10}3}211'>11}3}212'>12}3}213'>13}3}214'>14}3}215'>15}3}216'>16}3}217'>17}3}218'>18}3}219'>19}3}220'>20}3}221'>21}3}222'>22}3}223'>23}3";
				creeOption('fuseauHoraire_TimeStd_Hour', jsonDetail.TimeStd.Hour, heures);
				creeOption('fuseauHoraire_TimeDst_Hour', jsonDetail.TimeDst.Hour, heures);

				var days = "}21'>Dimanche}3}22'>Lundi}3}23'>Mardi}3}24'>Mercredi}3}25'>Jeudi}3}26'>Vendredi}27'>Samedi}3";
				creeOption('fuseauHoraire_TimeStd_Day', jsonDetail.TimeStd.Day, days);
				creeOption('fuseauHoraire_TimeDst_Day', jsonDetail.TimeDst.Day, days);

				var months = "}21'>Janvier}3}22'>Février}3}23'>Mars}3}24'>Avril}3}25'>Mai}3}26'>Juin}27'>Juillet}3}28'>Aout}3}29'>Septembre}3}210'>Octobre}3}211'>Novembre}3}212'>Décembre}3";
				creeOption('fuseauHoraire_TimeStd_Month', jsonDetail.TimeStd.Month, months);
				creeOption('fuseauHoraire_TimeDst_Month', jsonDetail.TimeDst.Month, months);

				var weeks = "}20'>Dernière semaine}3}21'>1ère semaine}3}22'>2ème semaine}3}23'>3ème semaine}3}24'>4ème semaine}3";
				creeOption('fuseauHoraire_TimeStd_Week', jsonDetail.TimeStd.Week, weeks);
				creeOption('fuseauHoraire_TimeDst_Week', jsonDetail.TimeDst.Week, weeks);

				var hemispheres = "}20'>Nord}3}21'>Sud}3";
				creeOption('fuseauHoraire_TimeStd_Hemisphere', jsonDetail.TimeStd.Hemisphere, hemispheres);
				creeOption('fuseauHoraire_TimeDst_Hemisphere', jsonDetail.TimeDst.Hemisphere, hemispheres);
				eb('fuseauHoraire_TimeStd_Offset').value = jsonDetail.TimeStd.Offset;
				eb('fuseauHoraire_TimeDst_Offset').value = jsonDetail.TimeDst.Offset;
			}
		} else if (eb('categorie').value == 'rangeExtender') {
			// Initialise le json
			enteteID = "rangeExtender";
			jsonDetail = json[enteteID];

			// Affiche ou efface les fieldsets correspondant aux relais existants
			if (jsonDetail == undefined) {
				if (qs("#fieldset_" + enteteID)) {
					qs("#groupe_" + enteteID).style.display = "none";
					qs("#fieldset_" + enteteID).style.display = "none";
				}
			} else {
				qs("#groupe_" + enteteID).style.display = "block";
				qs("#fieldset_" + enteteID).style.display = "block";

				eb('rangeExtender_idModuleRangeExpender').value = jsonDetail.idModuleRangeExpender;
				creeOption('rangeExtender_etat', jsonDetail.AP.etat, "}2ON'>ON}3}2OFF'>OFF}3");
				creeOption('rangeExtender_routeNAPT', jsonDetail.AP.routeNAPT, "}2ON'>ON}3}2OFF'>OFF}3");
				eb('rangeExtender_SSID').value = jsonDetail.AP.SSID;
				eb('rangeExtender_mdp').value = jsonDetail.AP.mdp;
				eb('rangeExtender_IPAddress').value = jsonDetail.AP.IPAddress;
				eb('rangeExtender_Subnet').value = (jsonDetail.AP.Subnet == "" ? "255.255.255.0" : jsonDetail.AP.Subnet);
			}
		}
		
        // Affiche ou efface les fieldsets correspondant au sous module
        document.querySelectorAll('[id^="fieldset_"]').forEach((fieldset) => {
			var categorie = recupereParamURL('categorie', url);
			
			if (recupereParamURL('categorie', url) == "wifi") {categorie = "generale";}
			if (fieldset.id.split("_")[1] == categorie) {
				qs("#groupe_" + enteteID).style.display = "block";
				fieldset.style.display = "block";
            } else {
				qs("#groupe_" + fieldset.id.split("_")[1]).style.display = "none";
				fieldset.style.display = "none";
            }
        });
	}
	
	/* Prépare la json modifié pour l'envoi en requête POST */
	function prepareJsonPost() {
		var json = JSON.parse(eb("jsonData").innerHTML)[recupereParamURL('categorie', url)];	
		var jsonDetail;
		var jsonModifie = {};
		var enteteID = "";
		var tabCategories = [];

		// Modifie le json avant envoi par requete POST
		if (eb('categorie').value == "generale") {
			// Initialise le json
			jsonDetail = json.serveur;
			
			jsonDetail.nom = eb('nom').value;
			jsonDetail.activation = eb("activation").value;
			jsonDetail.hostname = eb('hostname').value;
			jsonDetail.mDNS = eb("mDNS").value;		

			// Ajoute ou modifie les paramètres du capteur en json
			json.serveur = jsonDetail;	
			
			// Initialise le json
			jsonDetail = json.serveur["IP"];
			
			jsonDetail.IPAddress = eb('ipServeur').value;
			jsonDetail.IPGateway = eb('ipGateway').value;
			jsonDetail.Subnet = eb('Subnet').value;
			jsonDetail.DNSServer = eb('DNSServer').value;	

			// Ajoute ou modifie les paramètres du capteur en json
			json.serveur["IP"] = jsonDetail;			
		} else if (eb('categorie').value == "wifi") {
			// Initialise le json
			jsonDetail = json.serveur.wifi;			
			
			jsonDetail.power = eb('wifi_power').value;
			jsonDetail.selectSignalFort = eb('wifi_selectSignalFort').value;
			jsonDetail.reScanBy44 = eb('wifi_reScanBy44').value;
			jsonDetail.reseau1.nomReseauWifi = eb('wifi_reseau1_nomReseauWifi').value;
			jsonDetail.reseau1.mdpWifi = eb('wifi_reseau1_mdpWifi').value;
			jsonDetail.reseau2.nomReseauWifi = eb('wifi_reseau2_nomReseauWifi').value;
			jsonDetail.reseau2.mdpWifi = eb('wifi_reseau2_mdpWifi').value;
			
			// Ajoute ou modifie les paramètres du capteur en json
			json.serveur.wifi = jsonDetail;	
		} else if (eb('categorie').value == "localisation") {
			// Initialise le json
			jsonDetail = json.serveur.localisation;			
			
			jsonDetail.latitude = eb('localisation_latitude').value;
			jsonDetail.longitude = eb('localisation_longitude').value;
			
			// Ajoute ou modifie les paramètres du capteur en json
			json.serveur.localisation = jsonDetail;	
		} else if (eb('categorie').value == "mqtt") {
			// Initialise le json
			jsonDetail = json.serveur.mqtt;			
			
			jsonDetail.activation = eb('mqtt_activation').value;
			jsonDetail.hote = eb('mqtt_hote').value;
			jsonDetail.port = eb('mqtt_port').value;
			jsonDetail.client = eb('mqtt_client').value;
			jsonDetail.utilisateur = eb('mqtt_utilisateur').value;
												
			jsonDetail.mdp = eb('mqtt_mdp').value;
			jsonDetail.topic = eb('mqtt_topic').value;
			
			jsonDetail.groupTopic1 = eb('mqtt_groupTopic1').value;
			jsonDetail.groupTopic2 = eb('mqtt_groupTopic2').value;
			jsonDetail.groupTopic3 = eb('mqtt_groupTopic3').value;
				
			// Ajoute ou modifie les paramètres du capteur en json
			json.serveur.mqtt = jsonDetail;				
		} else if (eb('categorie').value == "fuseauHoraire") {
			// Initialise le json
			jsonDetail = json.serveur.fuseauHoraire;			
			
			jsonDetail.timezone = eb('fuseauHoraire_timezone').value;
			jsonDetail.TimeStd.Hour = eb('fuseauHoraire_TimeStd_Hour').value;
			jsonDetail.TimeDst.Hour = eb('fuseauHoraire_TimeDst_Hour').value;
			jsonDetail.TimeStd.Day = eb('fuseauHoraire_TimeStd_Day').value;
			jsonDetail.TimeDst.Day = eb('fuseauHoraire_TimeDst_Day').value;
			jsonDetail.TimeStd.Month = eb('fuseauHoraire_TimeStd_Month').value;
			jsonDetail.TimeDst.Month = eb('fuseauHoraire_TimeDst_Month').value;
			jsonDetail.TimeStd.Week = eb('fuseauHoraire_TimeStd_Week').value;
			jsonDetail.TimeDst.Week = eb('fuseauHoraire_TimeDst_Week').value;
			jsonDetail.TimeStd.Hemisphere = eb('fuseauHoraire_TimeStd_Hemisphere').value;
			jsonDetail.TimeDst.Hemisphere = eb('fuseauHoraire_TimeDst_Hemisphere').value;
			jsonDetail.TimeStd.Offset = eb('fuseauHoraire_TimeStd_Offset').value;
			jsonDetail.TimeDst.Offset = eb('fuseauHoraire_TimeDst_Offset').value;
				
			// Ajoute ou modifie les paramètres du capteur en json
			json.serveur.fuseauHoraire = jsonDetail;

		} else if (eb('categorie').value == 'rangeExtender') {
			// Initialise le json
			jsonDetail = json.serveur.rangeExtender;	
			
			jsonDetail.idModuleRangeExpender = parseInt(eb('rangeExtender_idModuleRangeExpender').value);
			jsonDetail.AP.etat = eb('rangeExtender_etat').value;
			jsonDetail.AP.routeNAPT = eb('rangeExtender_routeNAPT').value;
			jsonDetail.AP.SSID = eb('rangeExtender_SSID').value;
			jsonDetail.AP.mdp = eb('rangeExtender_mdp').value;
			jsonDetail.AP.IPAddress = eb('rangeExtender_IPAddress').value;
			jsonDetail.AP.Subnet = eb('rangeExtender_Subnet').value;	

			// Ajoute ou modifie les paramètres du capteur en json
			json.serveur.rangeExtender = jsonDetail;			
		}
		
		// Enregistre le json dans balise html
		eb("jsonData").innerHTML = JSON.stringify(json);
	}
</script>