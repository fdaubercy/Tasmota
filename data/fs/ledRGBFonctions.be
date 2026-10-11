#-
    - Module partage (singleton via module()) : la LED RGB WS2812 du dev-kit ESP32-S3 (2026-10-11).
      Persist : drivers.leds.environnement.leds.ledRGB = {activation, pin, id, type: 1377, luminosite}.
      Sur les clones HW-678, LED sur GPIO48, reliee seulement si le pont 'RGB' est soude.

    - Ce que montre la LED, par priorite decroissante :
        1. une couleur IMPOSEE par un module (imposeCouleur) : la cuve y recopie son ruban ;
        2. rouge clignotant si un module a signale une erreur (signaleErreur) ;
        3. sinon un voyant d'etat : vert = reseau et MQTT connectes, orange = Wi-Fi/Ethernet ou MQTT
           perdu (MQTT ignore s'il est desactive, SetOption3 0).

    - Pilotage : classe Leds (2e chaine WS2812, sans passer par le pilote light). Si un ruban occupe deja
      toute la memoire RMT de l'ESP32-S3, le firmware doit avoir TASMOTALED_HARDWARE_SPI (repli SPI),
      sinon Leds() leve 'LED interface not supported' : journalise une fois, plus d'essai ensuite.
-#

# Définition du module
var ledRGBFonctions = module("/ledRGBFonctions")

ledRGBFonctions.LUMINOSITE = 40          # luminosite du voyant d'etat si le persist n'en donne pas (0..255)
ledRGBFonctions.VERT = 0x00FF00
ledRGBFonctions.ORANGE = 0xFF6000
ledRGBFonctions.ROUGE = 0xFF0000

ledRGBFonctions.erreurs = {}             # source -> true : erreurs signalees par les modules
ledRGBFonctions.imposees = {}            # source -> [couleur, luminosite] imposees par les modules
ledRGBFonctions.phase = false            # phase du clignotement : true = rouge, false = eteinte
ledRGBFonctions.led = nil                # objet Leds, cree a la premiere ecriture
ledRGBFonctions.derniere = nil           # derniere couleur ecrite (pas de show inutile)
ledRGBFonctions.enEchec = false          # Leds() a echoue : plus d'essai jusqu'au redemarrage

ledRGBFonctions.log = def(msg, niveau)
    logFonctions.log(msg, niveau, "ledRGB")
end

# L'entree ledRGB du persist si elle est activee (et le bloc leds aussi), sinon nil
ledRGBFonctions.config = def()
    if (drivers.find("leds", {}).find("activation", "OFF") != "ON")    return nil    end
    var led = drivers["leds"].find("environnement", {}).find("leds", {}).find("ledRGB")
    if (led == nil || led.find("activation", "OFF") != "ON" || led.find("pin", -1) < 0)    return nil    end
    return led
end

# API des modules : signale (actif = true) ou leve (false) une erreur de la source 'source'
ledRGBFonctions.signaleErreur = def(source, actif)
    if (actif)
        ledRGBFonctions.erreurs[source] = true
    elif (ledRGBFonctions.erreurs.contains(source))
        ledRGBFonctions.erreurs.remove(source)
    end
end

# API des modules : impose une couleur (0xRRGGBB, 0 = eteinte) a la luminosite 'bri' ; couleur nil = rend la main
ledRGBFonctions.imposeCouleur = def(source, couleur, bri)
    if (couleur == nil)
        if (ledRGBFonctions.imposees.contains(source))    ledRGBFonctions.imposees.remove(source)    end
    else
        ledRGBFonctions.imposees[source] = [int(couleur), (bri == nil ? ledRGBFonctions.LUMINOSITE : int(bri))]
    end
end

# true si le module est connecte : reseau (Wi-Fi ou Ethernet) et, si MQTT est active, broker MQTT
ledRGBFonctions.connecte = def()
    import mqtt
    var reseau = tasmota.wifi("up") || tasmota.eth("up")
    if (!reseau)    return false    end
    if (tasmota.get_option(3) == 0)    return true    end     # MQTT desactive : pas de broker a attendre
    return mqtt.connected()
end

# Ecrit une couleur sur la LED (une seule fois par changement)
ledRGBFonctions.peint = def(couleur, bri)
    if (ledRGBFonctions.enEchec)    return    end
    var led = ledRGBFonctions.config()
    if (led == nil)    return    end
    var cle = str(couleur) + "@" + str(bri)
    if (cle == ledRGBFonctions.derniere)    return    end
    try
        if (ledRGBFonctions.led == nil)    ledRGBFonctions.led = Leds(1, int(led["pin"]))    end
        ledRGBFonctions.led.clear_to(couleur, bri)
        ledRGBFonctions.led.show()
        ledRGBFonctions.derniere = cle
    except .. as error, message
        ledRGBFonctions.led = nil
        ledRGBFonctions.enEchec = true
        ledRGBFonctions.log("PEINT_LED_RGB_ERREUR: LED du dev-kit (GPIO" + str(led["pin"]) + ") : " + str(error) + " -> " + str(message), LOG_LEVEL_ERREUR)
    end
end

# Appelee chaque seconde par controleLedRGB : applique la priorite imposee > erreur > etat
ledRGBFonctions.maj = def()
    var led = ledRGBFonctions.config()
    if (led == nil)    return    end
    var bri = int(led.find("luminosite", ledRGBFonctions.LUMINOSITE))

    # 1. Couleur imposee par un module (la premiere trouvee)
    for source: ledRGBFonctions.imposees.keys()
        var c = ledRGBFonctions.imposees[source]
        ledRGBFonctions.peint(c[0], c[1])
        return
    end

    # 2. Erreur signalee : rouge clignotant
    if (ledRGBFonctions.erreurs.size() > 0)
        ledRGBFonctions.phase = !ledRGBFonctions.phase
        ledRGBFonctions.peint(ledRGBFonctions.phase ? ledRGBFonctions.ROUGE : 0, bri)
        return
    end

    # 3. Voyant d'etat
    ledRGBFonctions.peint(ledRGBFonctions.connecte() ? ledRGBFonctions.VERT : ledRGBFonctions.ORANGE, bri)
end

# Retourne le module lors de l'importation
return ledRGBFonctions
