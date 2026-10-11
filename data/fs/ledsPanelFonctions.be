# Définition du module
#@ solidify:ledsPanelFonctions
var ledsPanelFonctions = module("ledsPanelFonctions")

#- Miroir du ruban WS2812 dans la page web (remplace leds_panel.bec, 2026-10-11).

   Pourquoi : le leds_panel amont sert sa page et son flux (EventSource) sur un SECOND serveur,
   port 8886, et son iframe vise l'IP Wi-Fi de la carte. Un esclave est derriere le NAPT du
   maitre RangeExtender (192.168.4.x) : ni cette IP ni ce port ne sont joignables depuis le
   reseau maison, la case "Leds mirroring" restait vide.

   Ici tout passe par le serveur web NORMAL de la carte (port 80) :
     - /leds       page du canvas (autonome, sans l'habillage Tasmota) ;
     - /leds_data  etat du ruban, une ligne de texte : "<largeur> <hauteur> <alterne> <octets/LED> <hexa>".
   La page interroge /leds_data environ 3 fois par seconde, uniquement case cochee et onglet
   visible, et jamais deux requetes a la fois (la suivante part apres la reponse).
   Les URL de la page sont RELATIVES : elle marche en direct (192.168.4.x), par la redirection
   du maitre (<maitre>:<routagePort>) et par l'acces distant, sans redirection supplementaire.
   Le maitre affiche une section par esclave equipe d'un ruban (rangeExtenderFonctions.afficheMiroirLedsEsclaves).

   Cout : un flux continu de ~1 Ko / 100 ms est remplace par ~3 requetes courtes par seconde,
   chacune occupant le serveur web quelques millisecondes ; rien quand la case est decochee.
   Plus de tcpserver ni de webserver_async permanents en RAM.
-#

# Cote d'une LED dans le canvas, en pixels internes ; le canvas est ensuite etire a 100 % de la
# largeur du cadre, la hauteur suit dans la meme proportion (iframe en aspect-ratio).
# Page /leds : la table gamma inverse est celle du leds_panel amont (le tampon est corrige gamma).
ledsPanelFonctions.PAGE =
    "<!DOCTYPE html><html><head><meta charset='utf-8'>"
    "<style>html,body{margin:0;padding:0;background:transparent;overflow:hidden;}"
    "canvas{display:block;width:100%;height:auto;image-rendering:pixelated;}</style>"
    "</head><body><canvas id='c' width='8' height='8'></canvas><script>"
    "var c=document.getElementById('c'),x=c.getContext('2d'),K=8,"
    "T=[[40,1],[80,3],[98,10],[124,26],[158,65],[190,112],[223,175],[255,255]];"
    "function g(v){var ps=0,pg=0;for(var i=0;i<T.length;i++){var s=T[i][0],m=T[i][1];"
      "if(v<=m)return Math.round(ps+(v-pg)*(s-ps)/(m-pg));ps=s;pg=m;}return 255;}"
    "function d(t){var p=t.split(' '),w=+p[0],h=+p[1],al=+p[2],o=(+p[3])*2,hx=p[4]||'';"
      "if(!(w>0&&h>0))return;"
      "if(c.width!=w*K||c.height!=h*K){c.width=w*K;c.height=h*K;}"
      "x.clearRect(0,0,c.width,c.height);"
      "for(var r=0;r<h;r++)for(var i=0;i<w;i++){var n=(r*w+i)*o;if(n+6>hx.length)return;"
        "var col=(al&&(r%2))?w-1-i:i;"
        "x.fillStyle='rgb('+g(parseInt(hx.substr(n,2),16))+','+g(parseInt(hx.substr(n+2,2),16))+','+g(parseInt(hx.substr(n+4,2),16))+')';"
        "x.fillRect(col*K+1,r*K+1,K-2,K-2);}}"
    "function p(){if(document.hidden){setTimeout(p,1000);return;}"
      "fetch('/leds_data',{cache:'no-store'}).then(function(r){return r.text();})"
      ".then(function(t){d(t);setTimeout(p,300);}).catch(function(){setTimeout(p,2000);});}"
    "p();"
    "</script></body></html>"

# Ruban natif de la carte (objet Leds), cree au premier appel et garde dans une GLOBALE :
# un module solidifie est constant (en flash), on ne peut pas y ecrire. nil sans GPIO WS2812.
def ledsPanelFonctions_ruban()
    import global
    import gpio

    if (!gpio.pin_used(gpio.WS2812, 0))    return nil    end
    if (global._rubanLedsPanel == nil)    global._rubanLedsPanel = Leds()    end
    return global._rubanLedsPanel
end
ledsPanelFonctions.ruban = ledsPanelFonctions_ruban

# Geometrie du ruban de la carte : [largeur, hauteur] en LED, ou nil s'il n'y a pas de ruban
# (ou une seule LED : rien a montrer, meme regle que l'ancien chargement de leds_panel)
def ledsPanelFonctions_geometrie()
    import ledsPanelFonctions

    var ruban = ledsPanelFonctions.ruban()
    if (ruban == nil)    return nil    end
    var nb = ruban.pixel_count()
    if (nb <= 1)    return nil    end
    var hauteur = tasmota.settings.light_pixels_height_1 + 1
    if (hauteur < 1 || hauteur > nb)    hauteur = 1    end
    return [nb / hauteur, hauteur]
end
ledsPanelFonctions.geometrie = ledsPanelFonctions_geometrie

# Enregistre /leds et /leds_data sur le serveur web de la carte, si elle porte un ruban.
# Appelee par controleWeb.web_add_handler().
def ledsPanelFonctions_ajouteRoutes()
    import webserver
    import ledsPanelFonctions

    if (ledsPanelFonctions.ruban() == nil)    return    end
    webserver.on("/leds", ledsPanelFonctions.envoiePage, webserver.HTTP_GET)
    webserver.on("/leds_data", ledsPanelFonctions.envoieDonnees, webserver.HTTP_GET)
    logFonctions.log("LEDS_PANEL: Pages /leds et /leds_data enregistrees !", LOG_LEVEL_DEBUG, "serveurWeb")
end
ledsPanelFonctions.ajouteRoutes = ledsPanelFonctions_ajouteRoutes

# GET /leds : la page du canvas, sans l'habillage Tasmota (elle vit dans une iframe)
def ledsPanelFonctions_envoiePage()
    import webserver
    import ledsPanelFonctions

    webserver.content_open(200, "text/html")
    webserver.content_send(ledsPanelFonctions.PAGE)
    webserver.content_close()
end
ledsPanelFonctions.envoiePage = ledsPanelFonctions_envoiePage

# GET /leds_data : "<largeur> <hauteur> <alterne> <octets/LED> <hexa>" ; "0 0 0 3 " sans ruban.
# Appelee ~3 fois par seconde par page ouverte : ni log, ni JSON, une seule chaine construite.
def ledsPanelFonctions_envoieDonnees()
    import webserver
    import ledsPanelFonctions

    try
        var geo = ledsPanelFonctions.geometrie()
        if (geo == nil)
            webserver.content_response("0 0 0 3 ")
            return
        end
        var ruban = ledsPanelFonctions.ruban()
        webserver.content_response(str(geo[0]) + " " + str(geo[1]) + " " +
                                   str(tasmota.settings.light_pixels_alternate ? 1 : 0) + " " +
                                   str(ruban.pixel_size()) + " " + ruban.pixels_buffer().tohex())
    except .. as error, message
        logFonctions.log(f"LEDS_PANEL_ERREUR: /leds_data -> {error} : {message}", LOG_LEVEL_ERREUR, "serveurWeb")
        webserver.content_response("0 0 0 3 ")
    end
end
ledsPanelFonctions.envoieDonnees = ledsPanelFonctions_envoieDonnees

# Envoie une section "Leds mirroring" dans la page en cours : une case a cocher et une iframe
# vers 'url' (la page /leds d'une carte). L'iframe garde le rapport largeur/hauteur du ruban
# (aspect-ratio) : le ruban occupe toute la largeur du cadre, la hauteur suit.
# suffixe : distingue les sections d'une meme page (une par carte).
def ledsPanelFonctions_afficheSection(suffixe, titre, url, largeur, hauteur)
    import webserver
    import string

    suffixe = str(suffixe)
    webserver.content_send(string.format(
        "<table style='width:100%%;'><tbody><tr><td>"
          "<fieldset style='background-color:%s;'>"
            "<legend style='text-align:left;'><label>"
              "<input type='checkbox' id='ledchk%s'>&nbsp;%s&nbsp;"
            "</label></legend>"
            "<div id='ledbox%s' hidden='true' style='padding:0px;'>"
              "<iframe id='led_iframe%s' src='about:blank' scrolling='no' "
                "style='display:block;width:100%%;aspect-ratio:%i/%i;border:0px none;margin:0px;padding:0px;'></iframe>"
            "</div>"
          "</fieldset>"
        "</td></tr></tbody></table>",
        tasmota.webcolor(1), suffixe, webserver.html_escape(str(titre)), suffixe, suffixe, int(largeur), int(hauteur)))
    webserver.content_send(string.format(
        "<script>wl(function(){"
          "var c=eb('ledchk%s'),f=eb('led_iframe%s'),b=eb('ledbox%s');"
          "c.addEventListener('change',function(){"
            "f.src=c.checked?'%s':'about:blank';"
            "b.hidden=!c.checked;"
          "});"
        "});</script>",
        suffixe, suffixe, suffixe, str(url)))
end
ledsPanelFonctions.afficheSection = ledsPanelFonctions_afficheSection

# Section du ruban de la carte elle-meme (page d'accueil), URL relative : marche quel que soit
# le chemin par lequel la page a ete ouverte. Appelee par controleWeb.web_add_main_button().
def ledsPanelFonctions_afficheSectionLocale()
    import ledsPanelFonctions

    var geo = ledsPanelFonctions.geometrie()
    if (geo == nil)    return    end
    ledsPanelFonctions.afficheSection("L", "Leds mirroring", "/leds", geo[0], geo[1])
end
ledsPanelFonctions.afficheSectionLocale = ledsPanelFonctions_afficheSectionLocale

# Retourne le module lors de l'importation
return ledsPanelFonctions
