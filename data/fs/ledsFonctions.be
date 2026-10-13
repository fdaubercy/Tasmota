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
var ledsFonctions = module("/ledsFonctions")

ledsFonctions.LUMINOSITE = 40          # luminosite du voyant d'etat si le persist n'en donne pas (0..255)
ledsFonctions.VERT = 0x00FF00
ledsFonctions.ORANGE = 0xFF6000
ledsFonctions.ROUGE = 0xFF0000

ledsFonctions.erreurs = {}             # source -> true : erreurs signalees par les modules
ledsFonctions.imposees = {}            # source -> [couleur, luminosite] imposees par les modules
ledsFonctions.phase = false            # phase du clignotement : true = rouge, false = eteinte
ledsFonctions.led = nil                # objet Leds, cree a la premiere ecriture
ledsFonctions.derniere = nil           # derniere couleur ecrite (pas de show inutile)
ledsFonctions.enEchec = false          # Leds() a echoue : plus d'essai jusqu'au redemarrage

ledsFonctions.log = def(msg, niveau)
    logFonctions.log(msg, niveau, "leds")
end

# L'entree ledRGB du persist si elle est activee (et le bloc leds aussi), sinon nil
ledsFonctions.config = def()
    if (drivers.find("leds", {}).find("activation", "OFF") != "ON")    return nil    end
    var led = drivers["leds"].find("environnement", {}).find("leds", {}).find("ledRGB")
    if (led == nil || led.find("activation", "OFF") != "ON" || led.find("pin", -1) < 0)    return nil    end
    return led
end

# API des modules : signale (actif = true) ou leve (false) une erreur de la source 'source'
ledsFonctions.signaleErreur = def(source, actif)
    if (actif)
        ledsFonctions.erreurs[source] = true
    elif (ledsFonctions.erreurs.contains(source))
        ledsFonctions.erreurs.remove(source)
    end
end

# API des modules : impose une couleur (0xRRGGBB, 0 = eteinte) a la luminosite 'bri' ; couleur nil = rend la main
ledsFonctions.imposeCouleur = def(source, couleur, bri)
    if (couleur == nil)
        if (ledsFonctions.imposees.contains(source))    ledsFonctions.imposees.remove(source)    end
    else
        ledsFonctions.imposees[source] = [int(couleur), (bri == nil ? ledsFonctions.LUMINOSITE : int(bri))]
    end
end

# true si le module est connecte : reseau (Wi-Fi ou Ethernet) et, si MQTT est active, broker MQTT
ledsFonctions.connecte = def()
    import mqtt
    var reseau = tasmota.wifi("up") || tasmota.eth("up")
    if (!reseau)    return false    end
    if (tasmota.get_option(3) == 0)    return true    end     # MQTT desactive : pas de broker a attendre
    return mqtt.connected()
end

# Cree le pilote de la LED : RMT d'abord, puis SPI si le RMT est plein (ruban present). Le SPI doit etre
# DEMANDE (Leds.SPI) : sans precision, TasmotaLEDPusher::ResolveHardware ne retient que le RMT et n'essaie
# jamais le SPI (constate sur la cuve le 2026-10-11 : 'RMT bus failed 48 err=261', aucun essai SPI).
ledsFonctions.creeLeds = def(pin)
    try
        return Leds(1, pin)
    except .. as error, message
        ledsFonctions.log("PEINT_LED_RGB: RMT indisponible (" + str(message) + "), essai en SPI", LOG_LEVEL_DEBUG)
    end
    return Leds(1, pin, Leds.WS2812_GRB, Leds.SPI)
end

# Ecrit une couleur sur la LED (une seule fois par changement)
ledsFonctions.peint = def(couleur, bri)
    if (ledsFonctions.enEchec)    return    end
    var led = ledsFonctions.config()
    if (led == nil)    return    end
    var cle = str(couleur) + "@" + str(bri)
    if (cle == ledsFonctions.derniere)    return    end
    try
        if (ledsFonctions.led == nil)    ledsFonctions.led = ledsFonctions.creeLeds(int(led["pin"]))    end
        ledsFonctions.led.clear_to(couleur, bri)
        ledsFonctions.led.show()
        ledsFonctions.derniere = cle
    except .. as error, message
        ledsFonctions.led = nil
        ledsFonctions.enEchec = true
        ledsFonctions.log("PEINT_LED_RGB_ERREUR: LED du dev-kit (GPIO" + str(led["pin"]) + ") : " + str(error) + " -> " + str(message), LOG_LEVEL_ERREUR)
    end
end

# Appelee chaque seconde par controleLeds : applique la priorite imposee > erreur > etat
ledsFonctions.maj = def()
    var led = ledsFonctions.config()
    if (led == nil)    return    end
    var bri = int(led.find("luminosite", ledsFonctions.LUMINOSITE))

    # 1. Couleur imposee par un module (la premiere trouvee)
    for source: ledsFonctions.imposees.keys()
        var c = ledsFonctions.imposees[source]
        ledsFonctions.peint(c[0], c[1])
        return
    end

    # 2. Erreur signalee : rouge clignotant
    if (ledsFonctions.erreurs.size() > 0)
        ledsFonctions.phase = !ledsFonctions.phase
        ledsFonctions.peint(ledsFonctions.phase ? ledsFonctions.ROUGE : 0, bri)
        return
    end

    # 3. Voyant d'etat
    ledsFonctions.peint(ledsFonctions.connecte() ? ledsFonctions.VERT : ledsFonctions.ORANGE, bri)
end

# Retourne le module lors de l'importation
return ledsFonctions
