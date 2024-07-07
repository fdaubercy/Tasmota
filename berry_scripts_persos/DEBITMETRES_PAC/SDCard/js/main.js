<script type='application/javascript'>
    /* Récupère les données présentes dans l'url */
	function recupereParamURL(paramRecherche = '', url = '') {
	    let queryString = "";

	    if (url == '') {
		    queryString = window.location.search;
	    } else {
		    queryString = url;
	    }

	    const urlParams = new URLSearchParams (queryString);
	    const entrees = urlParams.entries();
	    if (paramRecherche == '') {
		    return entrees;
	    } else {
		    if (urlParams.has(paramRecherche)) {
			    return urlParams.get(paramRecherche);
		    }
	    }
    }

    var f1; var f2; var reception;
	
	//eb=s=>document.getElementById(s);
	//qs=s=>document.querySelector(s);
	qsAll=s=>document.querySelectorAll(s);

    /* Envoi des données du formulaire */
	function sendData(data) {
		const XHR = new XMLHttpRequest();

		XHR.onload = function() {
			if (XHR.readyState == 4 && XHR.status == 200) {
				reception = XHR.responseText;
				console.log(reception);
			}
		};

		/* pré-remplir FormData du formulaire */
		let formData = new FormData(data);

		/* On prépare la requête */
		XHR.open('POST', '/modif?module=' + recupereParamURL('module') + '&categorie=' + recupereParamURL('categorie') + '&commande=modifParam', true);
		XHR.responseType = 'text';

		/* On envoie les données */
		XHR.send(formData);
	}

    function httpRequest(url, typeRequete, boolTimeout, callBack = '', donneesPOST = '') {
		var adresseURL = url || '';

		clearTimeout(f1);
		clearTimeout(f2);

		var xhr = new XMLHttpRequest();
		xhr.onload = function() {
			if (xhr.readyState == 4 && xhr.status == 200) {
				reception = xhr.responseText.replace(/{t}/g, "<table style='width:100%'>").replace(/{s}/g, "<tr><th>").replace(/{m}/g, "</th><td style='width:20px;white-space:nowrap'>").replace(/{e}/g, "</td></tr>");
				callBack == '' ? '' : callBack(reception, adresseURL);

				if (boolTimeout) {
					clearTimeout(f1);
					clearTimeout(f2);

					f2 = setTimeout(() => {httpRequest(adresseURL, typeRequete, boolTimeout, callBack)}, 2345);
				}
			}
		};

		xhr.onerror = function() {
		    console.log("Echec de la requête sur l'url: " + adresseURL);
		};
		xhr.open(typeRequete, adresseURL, true);
		xhr.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
		//xhr.responseType = 'text';
		(typeRequete == 'GET') ? xhr.send(null) : xhr.send(donneesPOST);
		if (boolTimeout) {
			f1 = setTimeout(() => {httpRequest(adresseURL, typeRequete, boolTimeout, callBack)}, 2e4);
		}
	}

	/* Crée élement 'option' */
	function creeOption(idSelect, valueOption, objTxt) {
		var indice = 0, p, l;

		/* Sélectionne le select d'id='' */
		var selection = qs('#' + idSelect);

		/* Pour supprimer les options */
		var nbOptions = selection.options.length;
		for (i = nbOptions; i; i--) {
			p = selection.options[i - 1].parentNode;
			p.removeChild(selection.options[i - 1]);
		}

		/* Crée les nouvelles options du select */
		var txt = objTxt.replace(/}2/g, "<option value='").replace(/}3/g, "</option>");
		eb(idSelect).innerHTML = txt;
		eb(idSelect).value = valueOption;
	}

	/* Affiche le paragraphe demandé */
	function afficheParagraphe(flecheID, paragrapheID) {
		const fleche = eb(flecheID);
		const paragraphe = eb(paragrapheID);

		// Modifie l'affichage de la fleche
		// Affiche ou cache le paragraphe demandé
		if (fleche.innerHTML == '△') {
			fleche.innerHTML = '▼';
			paragraphe.style.display = 'block';
		} else {
			fleche.innerHTML = '△';
			paragraphe.style.display = 'none';
		}
	}

    /* Lance l'envoi des formulaire en POST sur appui sur le bouton balise 'button' */
 	const btns = qsAll('[id^="btn_"]')
	if (btns != []) {
		btns.forEach((item) => {
			item.addEventListener('click', (event) => {
				if (item.id == 'btn_actionPompe') {
                    httpRequest('/json?module=' + recupereParamURL('module') + '&commande=togglePompeVideCave', 'GET', false, traiteRequete);
				} else if (item.id == 'btn_graphiques') {
					window.location.href="/graphiques?module=" + selectModule.value + (selectCategorie ? "&categorie=" + selectCategorie.value : "&categorie=generale");
				} else if (item.id.indexOf('btn_ajouter_element') > - 1) {
					// Pour lancer la popup
					//togglePopup();
					
					// element à ajouter
					ajouteElement(eb('categorie').value.slice(0, -1));
                } else if (item.id == 'btn_paramModules') {
					prepareJsonPost();
					httpRequest("/json" + window.location.search + "&commande=modifParam", 'POST', false, '', 'json=' + eb("jsonData").innerHTML);
                } else if (item.id == 'btn_supprBerryFS' || item.id == 'btn_resetESP32') {
					var commande = item.id.split("btn_")[1];
					httpRequest("/json" + window.location.search + "&commande=" + commande, 'POST', false, '', 'json=' + eb("jsonData").innerHTML);
                }

                console.log('Envoi du formulaire : ' + item.id.split('_')[1] + ' !');				
			});
		});
	}

    /* Lance les evenements sur changement de la valeur de la liste déroulante d'entête */
	var selectModule = document.forms.selectParametres.module;
	var selectCategorie = document.forms.selectParametres.categorie;

	if (selectModule) {
		document.forms.selectParametres.module.addEventListener('change', (event) => {
		    console.log("Changement de module !");
			//window.location.href="/modules?module=" + selectModule.value + 
									//(selectCategorie != undefined ? "&categorie=" + selectCategorie.value : "&categorie=generale");
			window.location.href = window.location.pathname + "?module=" + selectModule.value + 
									(selectCategorie != undefined ? "&categorie=" + selectCategorie.value : "&categorie=generale");
		});
	}

	if (selectCategorie) {
		document.forms.selectParametres.categorie.addEventListener('change', (event) => {
		    console.log("Changement de catégorie !");
			window.location.href="/modules?module=" + selectModule.value + (selectCategorie ? "&categorie=" + selectCategorie.value : "&categorie=generale");
		});
	}

	/* Lance la suppression d'un élément en json */
	const casesSuppr = qsAll('[name$="_suppression"]')
	if (casesSuppr != []) {
		casesSuppr.forEach((item) => {
			item.addEventListener('click', (event) => {
				if (item.checked) {
					var elt = item.id.split("_")[0];
					httpRequest("/json" + window.location.search + "&commande=supprElement&element=" + elt, 'GET', false, '');
				}
			});
		});
	}

    /* Execute les fonctions une 1ère fois */
    window.addEventListener('load', (event) => {
        console.log('La page est complètement chargée !');
        httpRequest("/json" + window.location.search, 'GET', false, paramFormulaire);
    });
</script>