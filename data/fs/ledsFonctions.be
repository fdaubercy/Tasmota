#-
    - Module partage (singleton via module()) : les LED pilotees par la carte (2026-10-11, ruban 2026-10-13).

    - LED RGB WS2812 du dev-kit ESP32-S3.
      Persist : drivers.leds.environnement.leds.ledRGB = {activation, pin, id, type: 1377, luminosite}.
      Sur les clones HW-678, LED sur GPIO48, reliee seulement si le pont 'RGB' est soude.
      Ce que montre la LED, par priorite decroissante :
        1. une couleur IMPOSEE (imposeCouleur) : elle recopie le ruban allume, hors erreur ;
        2. rouge clignotant si un module a signale une erreur (signaleErreur) ;
        3. sinon un voyant d'etat : vert = reseau et MQTT connectes, orange = Wi-Fi/Ethernet ou MQTT
           perdu (MQTT ignore s'il est desactive, SetOption3 0).
      Pilotage : classe Leds (2e chaine WS2812, sans passer par le pilote light). Si un ruban occupe deja
      toute la memoire RMT de l'ESP32-S3, le firmware doit avoir TASMOTALED_HARDWARE_SPI (repli SPI),
      sinon Leds() leve 'LED interface not supported' : journalise une fois, plus d'essai ensuite.

    - Ruban WS2812 de la carte (relais de type 1376, virtuel OFF ; le pilote light n'en gere qu'un).
      Persist : drivers.leds.environnement.leds.ruban = {activation, bouton, dureeManuel, appuiLong, palette}.
        * Mode AUTO : la couleur est fixee par le module metier (appliqueAuto ; la cuve : son niveau).
          Rouge clignotant si une erreur est signalee (signaleErreur), ruban allume.
        * Mode MANUEL : le module metier perd la main pendant 'dureeManuel' minutes (0 = sans fin),
          relancees a chaque action. On y entre par toute action : bouton, couleur changee depuis la
          page web ou MQTT (ecart avec la derniere couleur posee), animation, commande. Pas de
          clignotement : la LED du dev-kit et la page web continuent de signaler l'erreur.
        * Bouton (Button<bouton>, detache par SetOption73) : appui court = allume/eteint,
          appui long = couleur suivante de la palette (maintenu : defile toutes les 'appuiLong'
          dixiemes de s, SetOption32), double appui = retour en AUTO.
-#

# Définition du module (solidifiable : nom sans barre oblique, 2026-10-20)
#@ solidify:ledsFonctions
var ledsFonctions = module("ledsFonctions")

ledsFonctions.LUMINOSITE = 40          # luminosite du voyant d'etat si le persist n'en donne pas (0..255)
ledsFonctions.VERT = 0x00FF00
ledsFonctions.ORANGE = 0xFF6000
ledsFonctions.ROUGE = 0xFF0000
# Palette du mode MANUEL si le persist n'en donne pas (teinte 0..360, saturation 0..100)
ledsFonctions.PALETTE = [{"nom": "rouge", "teinte": 0, "saturation": 100}, {"nom": "orange", "teinte": 30, "saturation": 100},
                         {"nom": "jaune", "teinte": 60, "saturation": 100}, {"nom": "vert", "teinte": 120, "saturation": 100},
                         {"nom": "cyan", "teinte": 180, "saturation": 100}, {"nom": "bleu", "teinte": 240, "saturation": 100},
                         {"nom": "violet", "teinte": 280, "saturation": 100}, {"nom": "blanc", "teinte": 0, "saturation": 0}]

# ETAT MODIFIABLE (solidification, 2026-10-20) : solidifie, le module est en flash et sa table est
# CONSTANTE (be_module.c:367) ; un 'ledsFonctions.x = ...' y leverait une exception. L'etat vit donc dans
# la globale cachee '.ledsFonctions', lue par member() et ecrite par setmember() (modele de
# berry_matter/src/embedded/Matter_Module.be). Ces attributs ne doivent JAMAIS etre poses au niveau fichier :
# la valeur figee en flash masquerait celle de l'etat. Non solidifie (LittleFS, bancs), les ecritures vont
# dans la table et les lectures d'un attribut jamais ecrit passent par member() : meme comportement.
#   erreurs         : source -> true : erreurs signalees par les modules
#   imposees        : source -> [couleur, luminosite] imposees a la LED du dev-kit
#   phase           : phase du clignotement : true = rouge, false = eteinte
#   led             : objet Leds de la LED du dev-kit, cree a la premiere ecriture
#   derniere        : derniere couleur ecrite sur la LED (pas de show inutile)
#   enEchec         : Leds() a echoue : plus d'essai jusqu'au redemarrage
#   mode            : mode du ruban : "AUTO" ou "MANUEL"
#   echeance        : tasmota.millis() de fin du MANUEL (nil = sans fin)
#   indexPalette    : derniere couleur de la palette posee
#   attendu         : [teinte, saturation] posees par ce module (detection d'un changement exterieur)
#   animation       : derniere animation (Scheme) vue
#   satAvant        : saturation du ruban a l'entree en MANUEL (rendue au retour en AUTO)
#   fonctionAuto    : fonction du module metier qui repose sa couleur au retour en AUTO
#   descriptionAuto : texte du retour en AUTO, pose par enregistreRetourAuto
#   clignote        : les pixels du ruban portent le clignotement (a repeindre)
#   ruban           : strip natif du pilote light (Leds()), pour le clignotement
#   pasDefile       : crans du defilement en cours (garde-fou si le relachement est perdu)
#   texteHold       : libelle de l'appui long (StateText4), lu au demarrage
def ledsFonctions_etat()
    import global
    if !global.contains(".ledsFonctions")
        global.(".ledsFonctions") = {"erreurs": {}, "imposees": {}, "phase": false, "led": nil, "derniere": nil, "enEchec": false,
                                        "mode": "AUTO", "echeance": nil, "indexPalette": -1, "attendu": nil, "animation": 0,
                                        "satAvant": nil, "fonctionAuto": nil,
                                        "descriptionAuto": "la couleur est fixee par le module de la carte", "clignote": false,
                                        "ruban": nil, "pasDefile": 0, "texteHold": "HOLD"}
    end
    return global.(".ledsFonctions")
end
ledsFonctions.etat = ledsFonctions_etat

def ledsFonctions_member(nom)
    import undefined
    var etat = ledsFonctions.etat()
    return etat.contains(nom) ? etat[nom] : undefined
end
ledsFonctions.member = ledsFonctions_member

def ledsFonctions_setmember(nom, valeur)
    var etat = ledsFonctions.etat()
    if !etat.contains(nom)    return false    end     # nom inconnu : erreur, comme une table figee
    etat[nom] = valeur
end
ledsFonctions.setmember = ledsFonctions_setmember

def ledsFonctions_log(msg, niveau)
    logFonctions.log(msg, niveau, "leds")
end
ledsFonctions.log = ledsFonctions_log

# L'entree ledRGB du persist si elle est activee (et le bloc leds aussi), sinon nil
def ledsFonctions_config()
    if (drivers.find("leds", {}).find("activation", "OFF") != "ON")    return nil    end
    var led = drivers["leds"].find("environnement", {}).find("leds", {}).find("ledRGB")
    if (led == nil || led.find("activation", "OFF") != "ON" || led.find("pin", -1) < 0)    return nil    end
    return led
end
ledsFonctions.config = ledsFonctions_config

# L'entree ruban du persist si elle est activee (et le bloc leds aussi), sinon nil
def ledsFonctions_configRuban()
    if (drivers.find("leds", {}).find("activation", "OFF") != "ON")    return nil    end
    var r = drivers["leds"].find("environnement", {}).find("leds", {}).find("ruban")
    if (r == nil || r.find("activation", "OFF") != "ON")    return nil    end
    return r
end
ledsFonctions.configRuban = ledsFonctions_configRuban

# Le relais du ruban reel de la carte (type 1376, actif, non virtuel), ou nil
def ledsFonctions_relaisRuban()
    for cle: modules.keys()
        var m = modules[cle]
        if (type(m) != "instance" || m.find("activation", "OFF") != "ON")    continue    end
        var relais = m.find("environnement", {}).find("relais")
        if (type(relais) != "instance")    continue    end
        for cleRelai: relais.keys()
            var r = relais[cleRelai]
            if (type(r) != "instance" || r.find("activation", "OFF") != "ON" || r.find("type") != 1376)    continue    end
            if (r.find("virtuel", "OFF") == "OFF")    return r    end
        end
    end
    return nil
end
ledsFonctions.relaisRuban = ledsFonctions_relaisRuban

# API des modules : signale (actif = true) ou leve (false) une erreur de la source 'source'
def ledsFonctions_signaleErreur(source, actif)
    if (actif)
        ledsFonctions.erreurs[source] = true
    elif (ledsFonctions.erreurs.contains(source))
        ledsFonctions.erreurs.remove(source)
    end
end
ledsFonctions.signaleErreur = ledsFonctions_signaleErreur

# API des modules : impose une couleur (0xRRGGBB, 0 = eteinte) a la luminosite 'bri' ; couleur nil = rend la main
def ledsFonctions_imposeCouleur(source, couleur, bri)
    if (couleur == nil)
        if (ledsFonctions.imposees.contains(source))    ledsFonctions.imposees.remove(source)    end
    else
        ledsFonctions.imposees[source] = [int(couleur), (bri == nil ? ledsFonctions.LUMINOSITE : int(bri))]
    end
end
ledsFonctions.imposeCouleur = ledsFonctions_imposeCouleur

# true si le module est connecte : reseau (Wi-Fi ou Ethernet) et, si MQTT est active, broker MQTT
def ledsFonctions_connecte()
    import mqtt
    var reseau = tasmota.wifi("up") || tasmota.eth("up")
    if (!reseau)    return false    end
    if (tasmota.get_option(3) == 0)    return true    end     # MQTT desactive : pas de broker a attendre
    return mqtt.connected()
end
ledsFonctions.connecte = ledsFonctions_connecte

# Cree le pilote de la LED : RMT d'abord, puis SPI si le RMT est plein (ruban present). Le SPI doit etre
# DEMANDE (Leds.SPI) : sans precision, TasmotaLEDPusher::ResolveHardware ne retient que le RMT et n'essaie
# jamais le SPI (constate sur la cuve le 2026-10-11 : 'RMT bus failed 48 err=261', aucun essai SPI).
def ledsFonctions_creeLeds(pin)
    try
        return Leds(1, pin)
    except .. as error, message
        ledsFonctions.log("PEINT_LED_RGB: RMT indisponible (" + str(message) + "), essai en SPI", LOG_LEVEL_DEBUG)
    end
    return Leds(1, pin, Leds.WS2812_GRB, Leds.SPI)
end
ledsFonctions.creeLeds = ledsFonctions_creeLeds

# Ecrit une couleur sur la LED (une seule fois par changement)
def ledsFonctions_peint(couleur, bri)
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
ledsFonctions.peint = ledsFonctions_peint

# Appelee chaque seconde par controleLeds : le ruban d'abord (il impose sa couleur a la LED), puis la LED
def ledsFonctions_maj()
    if (ledsFonctions.erreurs.size() > 0)    ledsFonctions.phase = !ledsFonctions.phase    end
    ledsFonctions.majRuban()
    ledsFonctions.majLed()
end
ledsFonctions.maj = ledsFonctions_maj

# LED du dev-kit : applique la priorite imposee > erreur > etat
def ledsFonctions_majLed()
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
        ledsFonctions.peint(ledsFonctions.phase ? ledsFonctions.ROUGE : 0, bri)
        return
    end

    # 3. Voyant d'etat
    ledsFonctions.peint(ledsFonctions.connecte() ? ledsFonctions.VERT : ledsFonctions.ORANGE, bri)
end
ledsFonctions.majLed = ledsFonctions_majLed

# --- Ruban : etat du pilote light ---

# Canal light du ruban, ou nil
def ledsFonctions_canal()
    var r = ledsFonctions.relaisRuban()
    return (r == nil ? nil : int(r.find("channel", 0)))
end
ledsFonctions.canal = ledsFonctions_canal

# Etat light du ruban ({power, hue, sat, bri, rgb...}), ou nil
def ledsFonctions_etatRuban()
    import light
    var ch = ledsFonctions.canal()
    return (ch == nil ? nil : light.get(ch))
end
ledsFonctions.etatRuban = ledsFonctions_etatRuban

# Ecart entre deux teintes 0..360 (le plus court sur le cercle)
def ledsFonctions_ecartTeinte(a, b)
    var d = int(a) - int(b)
    if (d < 0)    d = -d    end
    d = d % 360
    return (d > 180 ? 360 - d : d)
end
ledsFonctions.ecartTeinte = ledsFonctions_ecartTeinte

# Memorise la couleur que le ruban porte maintenant comme posee par ce module
def ledsFonctions_noteAttendu()
    var e = ledsFonctions.etatRuban()
    if (e != nil)    ledsFonctions.attendu = [int(e.find("hue", 0)), int(e.find("sat", 0))]    end
end
ledsFonctions.noteAttendu = ledsFonctions_noteAttendu

# Ecrit une couleur (0xRRGGBB) sur les pixels du ruban sans toucher l'etat light : light.set reecrit les
# Settings, et 'rgb' 000000 couperait le ruban (Power off, xdrv_52_3_berry_light.ino:273)
def ledsFonctions_peintRuban(couleur, bri)
    try
        if (ledsFonctions.ruban == nil)    ledsFonctions.ruban = Leds()    end
        ledsFonctions.ruban.clear_to(couleur, bri)
        ledsFonctions.ruban.show()
    except .. as error, message
        ledsFonctions.ruban = nil
        ledsFonctions.log("PEINT_RUBAN_ERREUR: " + str(error) + " -> " + str(message), LOG_LEVEL_ERREUR)
    end
end
ledsFonctions.peintRuban = ledsFonctions_peintRuban

# --- Ruban : modes AUTO / MANUEL ---

# API du module metier : la fonction qui repose sa couleur au retour en AUTO, et ce qu'elle fait (aide)
def ledsFonctions_enregistreRetourAuto(fonction, description)
    ledsFonctions.fonctionAuto = fonction
    if (description != nil)    ledsFonctions.descriptionAuto = description    end
end
ledsFonctions.enregistreRetourAuto = ledsFonctions_enregistreRetourAuto

# API du module metier : pose la teinte 0..360 du mode AUTO (ignoree en MANUEL)
def ledsFonctions_appliqueAuto(teinte)
    import light
    if (ledsFonctions.mode != "AUTO")    return    end
    var ch = ledsFonctions.canal()
    if (ch == nil)    return    end
    var e = light.get(ch)
    if (e == nil)    return    end
    if (ledsFonctions.ecartTeinte(e.find("hue", 0), teinte) > 1)    light.set({"hue": int(teinte)}, ch)    end
    ledsFonctions.noteAttendu()
end
ledsFonctions.appliqueAuto = ledsFonctions_appliqueAuto

# true si le ruban est en mode MANUEL
def ledsFonctions_estManuel()
    return (ledsFonctions.mode == "MANUEL")
end
ledsFonctions.estManuel = ledsFonctions_estManuel

# Minutes restantes du mode MANUEL (nil = sans fin, 0 en AUTO)
def ledsFonctions_resteMinutes()
    if (ledsFonctions.mode != "MANUEL")    return 0    end
    if (ledsFonctions.echeance == nil)    return nil    end
    var ms = ledsFonctions.echeance - tasmota.millis()
    return (ms <= 0 ? 0 : (ms + 59999) / 60000)
end
ledsFonctions.resteMinutes = ledsFonctions_resteMinutes

# Passe (ou reste) en MANUEL : l'echeance repart de la duree complete
def ledsFonctions_passeManuel(source)
    import string
    var cfg = ledsFonctions.configRuban()
    if (cfg == nil)    return    end
    var duree = int(cfg.find("dureeManuel", 30))
    if (ledsFonctions.mode != "MANUEL")
        var e = ledsFonctions.etatRuban()
        ledsFonctions.satAvant = (e != nil ? int(e.find("sat", 255)) : 255)
        ledsFonctions.log(string.format("LEDS_RUBAN: Mode MANUEL (%s) %s !", str(source), (duree > 0 ? "pour " + str(duree) + " min" : "jusqu'au double appui")), LOG_LEVEL_INFO)
    end
    ledsFonctions.mode = "MANUEL"
    ledsFonctions.echeance = (duree > 0 ? tasmota.millis() + duree * 60000 : nil)
end
ledsFonctions.passeManuel = ledsFonctions_passeManuel

# Retour en AUTO : saturation d'avant le MANUEL rendue, puis le module metier repose sa couleur
def ledsFonctions_retourAuto(source)
    import light
    ledsFonctions.arreteDefile()
    var etaitManuel = (ledsFonctions.mode == "MANUEL")
    ledsFonctions.mode = "AUTO"
    ledsFonctions.echeance = nil
    ledsFonctions.indexPalette = -1
    var ch = ledsFonctions.canal()
    if (ch != nil && ledsFonctions.satAvant != nil)    light.set({"sat": ledsFonctions.satAvant}, ch)    end
    ledsFonctions.satAvant = nil
    if (ledsFonctions.fonctionAuto != nil)
        try
            ledsFonctions.fonctionAuto()
        except .. as error, message
            ledsFonctions.log("LEDS_RUBAN_ERREUR: retour en AUTO : " + str(error) + " -> " + str(message), LOG_LEVEL_ERREUR)
        end
    end
    ledsFonctions.noteAttendu()
    if (etaitManuel)    ledsFonctions.log("LEDS_RUBAN: Retour en mode AUTO (" + str(source) + ") !", LOG_LEVEL_INFO)    end
end
ledsFonctions.retourAuto = ledsFonctions_retourAuto

# La palette du persist, ou celle par defaut
def ledsFonctions_palette()
    var cfg = ledsFonctions.configRuban()
    var p = (cfg != nil ? cfg.find("palette") : nil)
    return (isinstance(p, list) && p.size() > 0 ? p : ledsFonctions.PALETTE)
end
ledsFonctions.palette = ledsFonctions_palette

# Couleur suivante de la palette (animation arretee : une couleur fixe), allume le ruban si besoin
def ledsFonctions_couleurSuivante()
    import light
    var ch = ledsFonctions.canal()
    if (ch == nil)    return    end
    var pal = ledsFonctions.palette()
    ledsFonctions.indexPalette = (ledsFonctions.indexPalette + 1) % pal.size()
    var c = pal[ledsFonctions.indexPalette]
    if (ledsFonctions.animation != 0)    tasmota.cmd("Scheme 0", boolMute)    ledsFonctions.animation = 0    end
    var e = light.get(ch)
    if (e != nil && !e.find("power", false))    light.set({"power": true}, ch)    end
    light.set({"hue": int(c.find("teinte", 0)), "sat": tasmota.scale_uint(int(c.find("saturation", 100)), 0, 100, 0, 255)}, ch)
    ledsFonctions.noteAttendu()
    ledsFonctions.log("LEDS_RUBAN: Couleur " + str(c.find("nom", ledsFonctions.indexPalette + 1)) + " !", LOG_LEVEL_DEBUG)
end
ledsFonctions.couleurSuivante = ledsFonctions_couleurSuivante

# --- Ruban : bouton poussoir ---

# Defilement de l'appui maintenu : un cran toutes les 'appuiLong' dixiemes de s, jusqu'au relachement
def ledsFonctions_demarreDefile()
    var cfg = ledsFonctions.configRuban()
    var periode = int(cfg != nil ? cfg.find("appuiLong", 15) : 15) * 100
    ledsFonctions.pasDefile = 0
    tasmota.remove_timer("ledsRubanDefile")
    var cran
    cran = def()
        ledsFonctions.pasDefile += 1
        # Garde-fou : 2 tours de palette sans relachement recu -> arret
        if (ledsFonctions.pasDefile > 2 * ledsFonctions.palette().size())    return    end
        ledsFonctions.couleurSuivante()
        ledsFonctions.passeManuel("bouton")
        tasmota.set_timer(periode, cran, "ledsRubanDefile")
    end
    tasmota.set_timer(periode, cran, "ledsRubanDefile")
end
ledsFonctions.demarreDefile = ledsFonctions_demarreDefile

def ledsFonctions_arreteDefile()
    tasmota.remove_timer("ledsRubanDefile")
end
ledsFonctions.arreteDefile = ledsFonctions_arreteDefile

# Regle Button<n>#Action : SINGLE / DOUBLE / HOLD (StateText4) / CLEAR (relachement apres HOLD)
def ledsFonctions_actionBouton(value)
    import string
    var r = ledsFonctions.relaisRuban()
    if (ledsFonctions.configRuban() == nil || r == nil)    return    end
    var action = string.toupper(str(value))
    ledsFonctions.log("LEDS_RUBAN: Bouton : " + action + " !", LOG_LEVEL_DEBUG)

    if (action == "SINGLE")
        tasmota.cmd(string.format("Power%i TOGGLE", int(r.find("id", 1))), boolMute)
        ledsFonctions.passeManuel("bouton")
    elif (action == "DOUBLE")
        ledsFonctions.retourAuto("bouton")
    elif (action == string.toupper(ledsFonctions.texteHold))
        ledsFonctions.passeManuel("bouton")
        ledsFonctions.couleurSuivante()
        ledsFonctions.demarreDefile()
    elif (action == "CLEAR")
        ledsFonctions.arreteDefile()
    end
end
ledsFonctions.actionBouton = ledsFonctions_actionBouton

# --- Ruban : tache de chaque seconde ---

# Echeance du MANUEL, changement de couleur exterieur, clignotement d'erreur, recopie par la LED du dev-kit
def ledsFonctions_majRuban()
    if (ledsFonctions.configRuban() == nil)
        ledsFonctions.imposeCouleur("ruban", nil)
        return
    end
    var e = ledsFonctions.etatRuban()
    if (e == nil)    return    end

    # 1. Fin du mode MANUEL
    if (ledsFonctions.mode == "MANUEL" && ledsFonctions.echeance != nil && tasmota.time_reached(ledsFonctions.echeance))
        ledsFonctions.retourAuto("fin de duree")
        e = ledsFonctions.etatRuban()
    end

    # 2. Couleur ou animation changee hors de ce module (page web, MQTT...) : c'est une action -> MANUEL
    var reponse = tasmota.cmd("_Scheme", boolMute)
    var animation = (isinstance(reponse, map) ? int(reponse.find("Scheme", 0)) : 0)
    var teinte = int(e.find("hue", 0))
    var sat = int(e.find("sat", 0))
    if (animation != ledsFonctions.animation)
        ledsFonctions.animation = animation
        if (animation != 0)    ledsFonctions.passeManuel("animation " + str(animation))    end
        ledsFonctions.attendu = [teinte, sat]
    elif (animation == 0)
        if (ledsFonctions.attendu == nil)
            ledsFonctions.attendu = [teinte, sat]
        else
            var ecartSat = sat - ledsFonctions.attendu[1]
            if (ecartSat < 0)    ecartSat = -ecartSat    end
            var blancs = (sat < 5 && ledsFonctions.attendu[1] < 5)       # teinte sans objet sur du blanc
            if (ecartSat > 5 || (!blancs && ledsFonctions.ecartTeinte(teinte, ledsFonctions.attendu[0]) > 3))
                ledsFonctions.attendu = [teinte, sat]
                ledsFonctions.passeManuel("couleur changee hors bouton")
            end
        end
    end

    # 3. Clignotement d'erreur : en AUTO seulement, ruban allume
    var allume = e.find("power", false)
    var erreur = (ledsFonctions.erreurs.size() > 0)
    var bri = int(e.find("bri", 127))
    if (erreur && allume && ledsFonctions.mode == "AUTO")
        ledsFonctions.peintRuban(ledsFonctions.phase ? ledsFonctions.ROUGE : 0x000000, bri)
        ledsFonctions.clignote = true
    elif (ledsFonctions.clignote)
        ledsFonctions.clignote = false
        if (allume)    ledsFonctions.peintRuban(int("0x" + e.find("rgb", "000000")), bri)    end
    end

    # 4. LED du dev-kit : recopie le ruban allume ; en erreur, elle clignote en rouge (priorite 2)
    if (allume && !erreur)
        ledsFonctions.imposeCouleur("ruban", int("0x" + e.find("rgb", "000000")), bri)
    else
        ledsFonctions.imposeCouleur("ruban", nil)
    end
end
ledsFonctions.majRuban = ledsFonctions_majRuban

# --- Ruban : aide et page web ---

# Mode d'emploi du bouton (console et page web)
def ledsFonctions_aideBouton()
    var cfg = ledsFonctions.configRuban()
    var duree = int(cfg != nil ? cfg.find("dureeManuel", 30) : 30)
    var appui = int(cfg != nil ? cfg.find("appuiLong", 15) : 15)
    var noms = []
    for c: ledsFonctions.palette()    noms.push(str(c.find("nom", "?")))    end
    return ["Bouton poussoir du ruban :",
            "- appui court : allume ou eteint le ruban ;",
            "- appui long (" + str(appui / 10) + "," + str(appui % 10) + " s) : couleur suivante ; maintenu, les couleurs defilent (" + noms.concat(", ") + ") ;",
            "- double appui : retour au mode AUTO.",
            "Mode AUTO : " + ledsFonctions.descriptionAuto + " ; rouge clignotant = mesure en erreur.",
            "Mode MANUEL : toute action (bouton, couleur choisie sur la page web ou par MQTT, commande, maitre ModBus) fige la couleur " +
                (duree > 0 ? "pendant " + str(duree) + " min, delai relance a chaque action" : "jusqu'au double appui") + ", puis retour en AUTO.",
            "En MANUEL, le ruban ne clignote pas : la LED du boitier et la page web signalent toujours une erreur."]
end
ledsFonctions.aideBouton = ledsFonctions_aideBouton

# Pastille d'aide dans le coin du bouton du ruban (page d'accueil), commune avec le ruban virtuel du maitre
def ledsFonctions_scriptAideWeb()
    import ledsPanelFonctions
    var r = ledsFonctions.relaisRuban()
    if (r == nil)    return ""    end
    return ledsPanelFonctions.pastilleAide("o" + str(int(r.find("id", 1))), "ldAide", "Aide du ruban", ledsFonctions.aideBouton())
end
ledsFonctions.scriptAideWeb = ledsFonctions_scriptAideWeb

# Ligne d'etat du ruban (web_sensor) ; 'Auto' renvoie en AUTO par la page (argument ldAuto)
def ledsFonctions_ligneWeb()
    if (ledsFonctions.mode != "MANUEL")    return "{s}Ruban LED{m}AUTO{e}"    end
    var reste = ledsFonctions.resteMinutes()
    return "{s}Ruban LED{m}MANUEL" + (reste == nil ? "" : ", reste " + str(reste) + " min") +
           " <button onclick='la(\"&ldAuto=1\");' style='width:auto;padding:0 8px;line-height:1.6'>Auto</button>{e}"
end
ledsFonctions.ligneWeb = ledsFonctions_ligneWeb

# --- Commande ReglageLeds ---

# Aide de la commande ReglageLeds, appelee SEULEMENT par diversFonctions.traiteAide :
# sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> lignes de detail, ou nil
def ledsFonctions_aideReglageLeds(sujet)
    import string
    if (sujet == nil)
        return [
            ["rubanEtat", "rubanEtat", "etat du ruban : mode, minutes restantes, couleur de la palette"],
            ["rubanAuto", "rubanAuto", "retour immediat au mode AUTO"],
            ["rubanManuel", "rubanManuel", "passe en mode MANUEL (fige la couleur)"],
            ["rubanSuivante", "rubanSuivante", "couleur suivante de la palette (passe en MANUEL)"],
            ["rubanDuree", "rubanDuree <min>", "duree du mode MANUEL (0 = jusqu'au double appui)"],
            ["rubanAppuiLong", "rubanAppuiLong <dixiemes de s>", "duree d'un appui long (SetOption32)"],
            ["rubanBouton", "rubanBouton", "mode d'emploi du bouton poussoir"]
        ]
    end
    sujet = string.toupper(sujet)
    if (sujet == "RUBANDUREE")
        return ["Parametre : entier, en minutes ; 0 = le MANUEL dure jusqu'au double appui.",
                "Effet : memorise drivers leds environnement leds ruban dureeManuel (persist.save).",
                "        Le delai repart de cette duree a chaque action en MANUEL.",
                "Exemple : ReglageLeds rubanDuree 30"]
    end
    if (sujet == "RUBANAPPUILONG")
        return ["Parametre : entier, en dixiemes de seconde (15 = 1,5 s).",
                "Effet : SetOption32, COMMUN a tous les boutons de la carte, et periode du defilement.",
                "        Memorise drivers leds environnement leds ruban appuiLong (persist.save).",
                "Exemple : ReglageLeds rubanAppuiLong 15"]
    end
    if (sujet == "RUBANBOUTON")    return ledsFonctions.aideBouton()    end
    return nil
end
ledsFonctions.aideReglageLeds = ledsFonctions_aideReglageLeds

# Etat du ruban pour les reponses de commande
def ledsFonctions_etatCommande()
    var pal = ledsFonctions.palette()
    var i = ledsFonctions.indexPalette
    var cfg = ledsFonctions.configRuban()
    return {"mode": ledsFonctions.mode, "resteMin": ledsFonctions.resteMinutes(),
            "couleur": (i >= 0 && i < pal.size() ? pal[i].find("nom", i + 1) : nil),
            "dureeManuel": (cfg != nil ? cfg.find("dureeManuel", 30) : nil), "appuiLong": (cfg != nil ? cfg.find("appuiLong", 15) : nil),
            "bouton": (cfg != nil ? cfg.find("bouton", 0) : nil)}
end
ledsFonctions.etatCommande = ledsFonctions_etatCommande

#- Exemples :
    ReglageLeds rubanAuto          => retour au mode AUTO
    ReglageLeds rubanDuree 30      => mode MANUEL de 30 min
-#
def ledsFonctions_reglageLeds(cmd, idx, payload, payload_json)
    import string
    import json
    import persist
    import diversFonctions
    if diversFonctions.traiteAide("ReglageLeds", payload, ledsFonctions.aideReglageLeds, true)    return    end

    var cfg = ledsFonctions.configRuban()
    if (cfg == nil)
        tasmota.resp_cmnd(json.dump({"ReglageLeds": {"erreur": "ruban inactif (drivers leds environnement leds ruban)"}}))
        return
    end
    var mots = string.split(str(payload), " ")
    var fonction = string.toupper(mots[0])
    var valeur = (mots.size() > 1 && mots[1] != "" ? mots[1] : nil)

    if (fonction == "RUBANAUTO")             ledsFonctions.retourAuto("commande")
    elif (fonction == "RUBANMANUEL")         ledsFonctions.passeManuel("commande")
    elif (fonction == "RUBANSUIVANTE")
        ledsFonctions.passeManuel("commande")
        ledsFonctions.couleurSuivante()
    elif (fonction == "RUBANDUREE" && valeur != nil)
        cfg["dureeManuel"] = int(valeur)
        persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien (persist.be:91-92)
        if (ledsFonctions.mode == "MANUEL")    ledsFonctions.passeManuel("commande")    end
    elif (fonction == "RUBANAPPUILONG" && valeur != nil)
        cfg["appuiLong"] = int(valeur)
        persist.save(true)
        ledsFonctions.regleBouton()
    elif (fonction == "RUBANBOUTON")
        for l: ledsFonctions.aideBouton()    print(l)    end
    end
    tasmota.resp_cmnd(json.dump({"ReglageLeds": ledsFonctions.etatCommande()}))
end
ledsFonctions.reglageLeds = ledsFonctions_reglageLeds

# Reglages Tasmota du bouton : appui long (SetOption32) ; SetOption1 ON, sinon un appui de 10 x
# l'appui long lancerait 'Reset 1' (support_button_v4.ino:488). SetOption1 est inscrit dans le persist
# (diverses.eviteResetBTN, applique a chaque demarrage par configGlobal) : il ne repasse pas a OFF.
def ledsFonctions_regleBouton()
    import string
    import persist
    var cfg = ledsFonctions.configRuban()
    if (cfg == nil || int(cfg.find("bouton", 0)) <= 0)    return    end
    var appui = int(cfg.find("appuiLong", 15))
    if (int(tasmota.cmd("SetOption32", boolMute).find("SetOption32", 0)) != appui)
        tasmota.cmd(string.format("SetOption32 %i", appui), boolMute)
        ledsFonctions.log(string.format("LEDS_RUBAN: Appui long regle a %i dixiemes de s (SetOption32) !", appui), LOG_LEVEL_INFO)
    end
    if (diverses.find("eviteResetBTN", "OFF") != "ON")
        diverses["eviteResetBTN"] = "ON"
        persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien (persist.be:91-92)
        ledsFonctions.log("LEDS_RUBAN: eviteResetBTN ON inscrit dans le persist (SetOption1) !", LOG_LEVEL_INFO)
    end
    if (tasmota.cmd("SetOption1", boolMute).find("SetOption1") != "ON")
        tasmota.cmd("SetOption1 ON", boolMute)
        ledsFonctions.log("LEDS_RUBAN: SetOption1 ON : un appui tres long ne reinitialise plus la carte !", LOG_LEVEL_INFO)
    end
    var texte = tasmota.cmd("StateText4", boolMute)
    if (isinstance(texte, map) && texte.find("StateText4") != nil)    ledsFonctions.texteHold = str(texte["StateText4"])    end
end
ledsFonctions.regleBouton = ledsFonctions_regleBouton

# Retourne le module lors de l'importation
return ledsFonctions
