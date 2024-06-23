<script type='application/javascript'>
    var objTypeGPIO = "}20'>Aucun}3}265504'>Utilisateur}3}26208'>Option A}3}28448'>Option E}3}232'>Bouton}3}264'>Bouton_n}3}27680'>Bouton_d}3}296'>Bouton_i}3}2128'>Bouton_in}3}27712'>Bouton_id}3}25408'>Bouton_tc}3}2160'>Inter}3}2192'>Inter_n}3}27744'>Inter_d}3}2224'>Relais}3}2256'>Relais_i}3}29312'>Relais_b}3}29344'>Relais_bi}3}2288'>LED}3}2320'>LED_i}3}2352'>Compteur}3}2384'>Compteur_n}3}2416'>PWM}3}2448'>PWM_i}3}2480'>Buzzer}3}2512'>Buzzer_i}3}2544'>LedLink}3}2576'>LedLink_i}3}27648'>Input}3}27968'>Interrupt}3}23840'>Sortie Hi}3}23872'>Sortie Lo}3}28224'>Heartbeat}3}28256'>Heartbeat_i}3}28736'>Reset}3}2608'>I2C SCl}3}2640'>I2C SDa}3}2672'>SPI MISO}3}2704'>SPI MOSI}3}2736'>SPI Clk}3}2768'>SPI CS}3}2800'>SPI DC}3}26720'>CarteSD CS}3}28800'>SDIO Cmd}3}28832'>SDIO Clk}3}28864'>SDIO D0}3}28896'>SDIO D1}3}28928'>SDIO D2}3}28960'>SDIO D3}3}2832'>SSPI MISO}3}2864'>SSPI MOSI}3}2896'>SSPI SClk}3}2928'>SSPI CS}3}2960'>SSPI DC}3}23200'>Série Tx}3}23232'>Série Rx}3}21184'>DHT11}3}21216'>AM2301}3}21248'>SI7021}3}28768'>MS01}3}21280'>DHT11_o}3}23136'>ALux IrRcv}3}23168'>ALux IrSel}3}23008'>MY92x1 DI}3}23040'>MY92x1 DCkI}3}22912'>SM16716 Clk}3}22944'>SM16716 Dat}3}22976'>SM16716 Pwr}3}24032'>SM2135 Clk}3}24064'>SM2135 Dat}3}29088'>SM2335 Clk}3}29120'>SM2335 Dat}3}29664'>BP1658CJ Clk}3}29696'>BP1658CJ Dat}3}29024'>BP5758D Clk}3}29056'>BP5758D Dat}3}24640'>MOODL Tx}3}22592'>HLWBL Sel}3}22624'>HLWBL Sel_i}3}22656'>HLWBL CF1}3}22688'>HLW8012 CF}3}22720'>BL0937 CF}3}23456'>ADE7953 IRq}3}29472'>ADE7953 Rst}3}29568'>ADE7953 CS}3}27296'>CSE7761 Tx}3}27328'>CSE7761 Rx}3}23072'>CSE7766 Tx}3}23104'>CSE7766 Rx}3}22752'>MCP39F5 Tx}3}22784'>MCP39F5 Rx}3}22816'>MCP39F5 Rst}3}29984'>NrgMbus Tx Ena}3}21472'>PZEM0XX Tx}3}21504'>PZEM004 Rx}3}21536'>PZEM016 Rx}3}21568'>PZEM017 Rx}3}28128'>BL0939 Rx}3}25440'>BL0940 Rx}3}28160'>BL0942 Rx}3}27552'>ZC Pulse}3}21792'>SerBr Tx}3}21824'>SerBr Rx}3}24096'>Hibernation}3}28992'>Débit}3}27584'>Effet Hall}3}25536'>ETH Pwr}3}25568'>ETH MDC}3}25600'>ETH MDIO}3}24704'>ADC Entrée}3}24736'>ADC Temp.}3}24768'>ADC Lumière}3}24800'>ADC Bouton}3}24832'>ADC Bouton_i}3}24864'>ADC Distance}3}24896'>ADC CT Power}3}23328'>ADC Manette}3}26816'>ADC pH}3}28544'>ADC MQ}3";
	
    /* Crée élements 'option' des balises 'select' */
	function paramFormulaire(jsonData, url) {
		console.log(JSON.parse(jsonData));
		console.log("categorie=" + recupereParamURL('categorie', url));
		
		// Enregistre le json dans balise html
		eb("jsonData").innerHTML = jsonData;
		
		var json = JSON.parse(jsonData).diverses;

		eb('telePeriod').value = json.telePeriod;
		creeOption('logs', json.logs, "}21'>LOG_LEVEL_ERREUR}3}22'>LOG_LEVEL_INFO}3}23'>LOG_LEVEL_DEBUG}3}24'>LOG_LEVEL_DEBUG_PLUS}3");
		creeOption('eviteResetBTN', json.eviteResetBTN, "}2ON'>ON}3}2OFF'>OFF}3");
		creeOption('ledPower', json.ledPower, "}2ON'>ON}3}2OFF'>OFF}3");
		creeOption('ledState', json.ledState, "}20'>Désactivé}3}21'>Affiche l\'état d\'alimentation}3}22'>Clignote si réception MQTT}3}23'>Affiche l\'état d\'alimentation & Clignote si réception MQTT}3}24'>Clignote si émission MQTT}3}25'>Affiche l\'état d\'alimentation & Clignote si émission MQTT}3}26'>Clignote pour tous les messages MQTT}3}27'>Affiche l\'état d\'alimentation & Clignote pour tous les messages MQTT}3}26'>Clignote pour tous les messages MQTT}3}28'>LED allumée lorsque le Wi-Fi et MQTT sont connectés}3");
		creeOption('ledLink_activation', json.leds.ledLink.activation, "}2ON'>ON}3}2OFF'>OFF}3");
		eb('ledLink_pin').value = json.leds.ledLink.pin;
		creeOption('ledLink_type', (json.leds.ledLink.type & 0xffe0) >> 5, objTypeGPIO);
		creeOption('led1_activation', json.leds.led1.activation, "}2ON'>ON}3}2OFF'>OFF}3");
		eb('led1_id').value = json.leds.led1.id;
		eb('led1_pin').value = json.leds.led1.pin;
		creeOption('led1_type', (json.leds.led1.type & 0xffe0) >> 5, objTypeGPIO);
	}
	/* wl(paramFormulaire); */
	
	/* Prépare la json modifié pour l'envoi en requête POST */
	function prepareJsonPost() {
		var json = JSON.parse(eb("jsonData").innerHTML)["diverses"];	
		var jsonDetail;
		var jsonModifie = {};
		var enteteID = "";
		
		// Pour debug
		console.log("jsonData ->");	console.log(JSON.parse(eb("jsonData").innerHTML));
		console.log("json ->");	console.log(json);	

		// Modifie le json avant envoi par requete POST
		json.telePeriod = parseInt(eb("telePeriod").value);		
		
		json.logs = parseInt(eb("logs").value);
		json.eviteResetBTN = eb("eviteResetBTN").value;	
		json.ledPower = eb("ledPower").value;	
		json.ledState = parseInt(eb("ledState").value);	
		
		json.leds.ledLink.activation = eb("ledLink_activation").value;	
		json.leds.ledLink.pin = parseInt(eb("ledLink_pin").value);	
		json.leds.ledLink.type = ((eb("ledLink_type").value << 5) & 0xffe0);
		
		json.leds.led1.activation = eb("led1_activation").value;
		json.leds.led1.id = parseInt(eb("led1_id").value);	
		json.leds.led1.pin = parseInt(eb("led1_pin").value);	
		json.leds.led1.type = ((eb("led1_type").value << 5) & 0xffe0) + json.leds.led1.id - 1;	
		
		// Enregistre le json dans balise html
		jsonModifie["diverses"] = json;
		eb("jsonData").innerHTML = JSON.stringify(jsonModifie);	
	}
</script>