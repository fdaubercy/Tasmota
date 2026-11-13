# Page « Systeme » des ecrans tactiles (plan tasks/plans/atelier-ecrans.md, A19) : memoire, flash, charge, redemarrages, reseau,
# ModBus, ecran, firmware et dernieres erreurs Berry de la carte, ecrits sur les objets de la page `modules.ecranSysteme.page`
# du persist par l'interface d'ecran demarree (ecranFonctions.interface : ecranHaspmota, ecranCaveHaspmota ou ecranLvgl genere).
# Commun aux cartes a ecran ; charge depuis le FS, forme SOLIDIFIABLE (fonctions nommees, `import` dans chaque fonction, etat dans
# la map de la globale cachee ".ecranSysteme" rendue par ecranSysteme.etat(), jamais d'attribut ecrit dans le module : piege 12 de
# outils_docs/SOLIDIFICATION_BERRY.md). Cadence (controleEcranSysteme, every_second) : RAM minimale et courbe d'une heure suivies
# EN CONTINU par tasmota.memory("heap_free") (sans map) ; mesures toutes les MAJ ms SEULEMENT page affichee ; commandes (Status 11,
# UfsSize, UfsFree, RgxClients : chaque reponse part aussi en MQTT, support_command.ino::CmndStatusResponse) toutes les LENT ms ;
# Status 1 et 2 une fois. CHAMPS = SEULE reference des donnees, relue ici par la page de l'atelier (expression reguliere : une
# entree par ligne) : [cle, libelle, unite, id du texte, id de la barre ou nil], ids 1 a 199 (201-254 : barre de navigation).
# Texte = valeur et unite ; barre (val 0-100) = taux d'OCCUPATION, sauf rssi (qualite) ; couleurs (text_color, bg_color10) d'apres
# SEUILS. Boutons BOUTON_GC et BOUTON_REDEMARRER (second appui dans les CONFIRMATION ms, le premier ecrit « Confirmer ? ») :
# ecranSysteme.appui(id) ; LVGL genere : toucher {"fonction": "ecranSysteme.appui", "args": [<id>]} ; HASPmota : regles du driver.
# Logs : charte du CLAUDE.md (logFonctions.log, cible ecranSysteme : ReglageLog ecranSysteme <niveau>).
var ecranSysteme = module("ecranSysteme")

ecranSysteme.CHAMPS = [
    ["ramLibre", "RAM interne libre", "Ko", 1, nil],
    ["ramMin", "RAM libre minimale", "Ko", 2, nil],
    ["fragmentation", "Fragmentation de la RAM", "%", 3, 4],
    ["psramTotale", "PSRAM totale", "Ko", 5, nil],
    ["psramLibre", "PSRAM libre", "Ko", 6, 7],
    ["ramGC", "RAM libre au dernier GC", "Ko", 8, nil],
    ["dureeGC", "Durée du dernier GC", "ms", 9, nil],
    ["pileMin", "Pile minimale", "Ko", 10, nil],
    ["iramLibre", "IRAM libre", "Ko", 11, nil],
    ["programme", "Programme", "Ko", 20, nil],
    ["otaLibre", "Place libre OTA", "Ko", 21, 22],
    ["ota", "Mise à jour OTA", "", 23, nil],
    ["fsTaille", "Système de fichiers", "Ko", 24, nil],
    ["fsLibre", "Système de fichiers libre", "Ko", 25, 26],
    ["charge", "Charge (LoadAvg)", "%", 30, 31],
    ["sleep", "Sleep", "ms", 32, nil],
    ["temperature", "Température de la puce", "°C", 33, nil],
    ["uptime", "En service depuis", "", 40, nil],
    ["cause", "Cause du redémarrage", "", 41, nil],
    ["demarrages", "Démarrages", "", 42, nil],
    ["rssi", "Signal Wi-Fi", "dBm", 50, 51],
    ["bssid", "Point d'accès (BSSID)", "", 52, nil],
    ["ip", "Adresse IP", "", 53, nil],
    ["pertesWifi", "Pertes du Wi-Fi", "", 54, nil],
    ["horsLigne", "Durée hors ligne", "", 55, nil],
    ["mqtt", "MQTT", "", 56, nil],
    ["reconnexionsMqtt", "Reconnexions MQTT", "", 57, nil],
    ["heure", "Heure", "", 58, nil],
    ["esclaves", "Esclaves ModBus joignables", "", 70, nil],
    ["delais", "Délais ModBus dépassés", "", 71, nil],
    ["dernierContact", "Dernier contact ModBus", "", 72, nil],
    ["clients", "Clients du point d'accès", "", 73, nil],
    ["luminosite", "Luminosité de l'écran", "%", 80, nil],
    ["veille", "Veille de l'écran", "min", 81, nil],
    ["version", "Version du firmware", "", 90, nil],
    ["compilation", "Compilé le", "", 91, nil],
    ["erreur1", "Dernière erreur", "", 101, nil],
    ["erreur2", "Erreur précédente", "", 102, nil],
    ["erreur3", "Erreur précédente", "", 103, nil],
    ["erreur4", "Erreur précédente", "", 104, nil],
    ["erreur5", "Erreur précédente", "", 105, nil]]

# Seuils des couleurs : cle -> [orange, rouge]. orange < rouge : plus haut = pire ; orange > rouge : plus bas = pire.
#   ramLibre, ramMin (Ko) : sous ~25 Ko, echecs d'allocation Berry et redemarrages (tasks/lessons.md, 2026-11-02) ; fragmentation (%) :
#   au-dela de la moitie un gros bloc (TLS, LVGL) ne trouve plus sa place ; psramLibre, fsLibre, otaLibre : occupation (%) ; pileMin
#   (Ko) : sous 1 Ko, debordement proche ; charge : LoadAvg (tasmota.ino : 100 * activite / sleep) ; rssi : -80 dBm = liaison
#   instable ; temperature : puce donnee jusqu'a 85 °C
ecranSysteme.SEUILS = {"ramLibre": [50, 25], "ramMin": [30, 15], "fragmentation": [30, 50], "psramLibre": [75, 90],
                       "pileMin": [2, 1], "otaLibre": [90, 100], "fsLibre": [80, 95], "charge": [50, 80], "rssi": [-70, -80],
                       "temperature": [70, 80]}
ecranSysteme.COULEURS = {"vert": 0x3FD08A, "orange": 0xFFA53F, "rouge": 0xFF5A5A, "neutre": 0xE8EDF2}
ecranSysteme.MAJ = 5000            # ms entre deux mesures, page affichee
ecranSysteme.LENT = 30000          # ms entre deux lectures par commande (Status 11, UfsSize, UfsFree, RgxClients, capteurs)
ecranSysteme.COURBE_POINTS = 120   # points de la courbe de la RAM libre (une heure)
ecranSysteme.COURBE_PAS = 30000    # ms entre deux points de la courbe
ecranSysteme.CONFIRMATION = 5000   # ms pour confirmer le redemarrage par un second appui
ecranSysteme.BOUTON_GC = 120
ecranSysteme.BOUTON_REDEMARRER = 121
ecranSysteme.TEXTE_REDEMARRER = "Redémarrer"
ecranSysteme.TEXTE_CONFIRMER = "Confirmer ?"
ecranSysteme.HEURE_VALIDE = 1451602800   # tasmota.h::START_VALID_TIME : heure synchronisee au-dela (2016-01-01)
ecranSysteme.LONGUEUR_ERREUR = 90        # caracteres d'un message d'erreur affiches

# Etat (globale cachee) : ramMin (Ko) ; courbe (voir courbe()), courbeA (millis du dernier point), points (ajoutes depuis le
# demarrage) ; majA, lentA : millis de la derniere mesure et lecture lente (nil : a faire) ; lent, fixe : valeurs lues par
# commande (LENT) et une fois (Status 1, 2) ; confirmeA : millis du premier appui sur « Redemarrer » (nil : rien en attente)
def ecranSysteme_etat()
    import global
    if (global.(".ecranSysteme") == nil)
        global.(".ecranSysteme") = {"ramMin": nil, "courbe": nil, "courbeA": nil, "points": 0, "majA": nil, "lentA": nil,
                                    "lent": nil, "fixe": nil, "confirmeA": nil}
    end
    return global.(".ecranSysteme")
end
ecranSysteme.etat = ecranSysteme_etat
# Courbe de la RAM libre (Ko) : COURBE_POINTS valeurs, nil = pas encore mesure, du plus vieux au plus recent ; nil avant le
# premier point. Points ajoutes depuis le demarrage : ecranSysteme.etat()["points"] (pousser seulement les nouveaux).
def ecranSysteme_courbe()    import ecranSysteme    return ecranSysteme.etat()["courbe"]    end
ecranSysteme.courbe = ecranSysteme_courbe
# Log du module sous le seuil de la cible ecranSysteme ; niveau = constante LOG_LEVEL_*
def ecranSysteme_log(msg, niveau)    logFonctions.log(msg, niveau, "ecranSysteme")    end
ecranSysteme.log = ecranSysteme_log
# Page Systeme du persist (modules.ecranSysteme.page), nil si absente (rien n'est ecrit)
def ecranSysteme_page()
    if (modules == nil)    return nil    end      # persist absent : pas de page
    var b = modules.find("ecranSysteme")
    var p = b != nil ? b.find("page") : nil
    return type(p) == "int" ? p : nil
end
ecranSysteme.page = ecranSysteme_page
# Vrai si l'interface est le LVGL genere (ecranLvgl : membre `page`, couleurs entieres) ; sinon HASPmota (couleurs "#RRGGBB")
def ecranSysteme_estLvgl(itf)    import introspect    return introspect.contains(itf, "page")    end
ecranSysteme.estLvgl = ecranSysteme_estLvgl
# Page affichee par l'interface : ecranLvgl.page (LVGL genere), sinon haspmota.lvh_page_cur_idx ; nil sans ecran
def ecranSysteme_pageAffichee()
    import ecranFonctions
    import ecranSysteme
    var itf = ecranFonctions.interface
    if (itf == nil)    return nil    end
    if (ecranSysteme.estLvgl(itf))    return itf.page    end
    import haspmota
    return haspmota.lvh_page_cur_idx
end
ecranSysteme.pageAffichee = ecranSysteme_pageAffichee
# Couleur `nom` : entier pour LVGL (lv.color), "#RRGGBB" pour HASPmota (lv_haspmota.be::parse_color rend du noir d'un entier)
def ecranSysteme_couleur(nom)
    import string
    import ecranFonctions
    import ecranSysteme
    var c = ecranSysteme.COULEURS[nom == nil ? "neutre" : nom]
    var itf = ecranFonctions.interface
    return (itf != nil && ecranSysteme.estLvgl(itf)) ? c : string.format("#%06X", c)
end
ecranSysteme.couleur = ecranSysteme_couleur
# Ecrit l'attribut `attr` de l'objet `id` de la page Systeme (l'interface garde un cache) ; sans page au persist ni ecran : rien
def ecranSysteme_ecris(id, attr, val)
    import ecranFonctions
    import ecranSysteme
    var p = ecranSysteme.page()
    var itf = ecranFonctions.interface
    if (p == nil || itf == nil)    return    end
    itf.ecris("p" + str(p) + "b" + str(id), attr, val)
end
ecranSysteme.ecris = ecranSysteme_ecris
# Niveau "vert" | "orange" | "rouge" de la valeur `x` de la donnee `cle` d'apres SEUILS ; nil sans seuil ou sans valeur
def ecranSysteme_niveau(cle, x)
    import ecranSysteme
    var s = ecranSysteme.SEUILS.find(cle)
    if (s == nil || x == nil)    return nil    end
    if (s[0] < s[1])    return x >= s[1] ? "rouge" : (x >= s[0] ? "orange" : "vert")    end
    return x <= s[1] ? "rouge" : (x <= s[0] ? "orange" : "vert")
end
ecranSysteme.niveau = ecranSysteme_niveau
# Nombre a virgule (affichage en francais) : 1.25 -> "1,3" (fmt "%.1f")
def ecranSysteme_virgule(x, fmt)    import string    return string.tr(string.format(fmt, x), ".", ",")    end
ecranSysteme.virgule = ecranSysteme_virgule
# Taille en Ko -> "512 Ko", au-dela de 1024 Ko "1,5 Mo"
def ecranSysteme_ko(n)    import ecranSysteme    return n >= 1024 ? ecranSysteme.virgule(n / 1024.0, "%.1f") + " Mo" : str(int(n)) + " Ko"    end
ecranSysteme.ko = ecranSysteme_ko
# Duree en secondes -> "3 j 4 h", "2 h 05 min", "4 min 12 s", "12 s"
def ecranSysteme_duree(s)
    import string
    if (s >= 86400)    return string.format("%d j %d h", s / 86400, (s % 86400) / 3600)    end
    if (s >= 3600)    return string.format("%d h %02d min", s / 3600, (s % 3600) / 60)    end
    if (s >= 60)    return string.format("%d min %02d s", s / 60, s % 60)    end
    return string.format("%d s", s)
end
ecranSysteme.duree = ecranSysteme_duree
# Duree Tasmota "1T02:03:04" (support_rtc.ino::GetDuration) -> secondes ; nil si illisible
def ecranSysteme_secondes(t)
    import string
    var j = string.split(str(t), "T")
    var h = string.split(j[-1], ":")
    if (size(j) != 2 || size(h) != 3)    return nil    end
    return int(j[0]) * 86400 + int(h[0]) * 3600 + int(h[1]) * 60 + int(h[2])
end
ecranSysteme.secondes = ecranSysteme_secondes
# Suivi continu, page affichee ou non : RAM minimale, un point de courbe toutes les COURBE_PAS ms (millis : l'heure saute au NTP)
def ecranSysteme_suit()
    import ecranSysteme
    var e = ecranSysteme.etat()
    var v = tasmota.memory("heap_free")
    if (v == nil)    return    end
    var m = e["ramMin"]
    if (m == nil || v < m)    e["ramMin"] = v    end
    var t = tasmota.millis()
    var a = e["courbeA"]
    if (a != nil && t >= a && t - a < ecranSysteme.COURBE_PAS)    return    end
    e["courbeA"] = t
    var c = e["courbe"]
    if (c == nil)
        c = []
        c.resize(ecranSysteme.COURBE_POINTS)   # nil partout : courbe vide avant les premiers points
        e["courbe"] = c
    end
    c.remove(0)
    c.push(v)
    e["points"] += 1
end
ecranSysteme.suit = ecranSysteme_suit
# Valeur `cle` d'une reponse de commande {"<Commande>": n} ou {"<Commande>": [SD, flash]} (UfsSize, UfsFree avec une carte SD :
# xdrv_50_filesystem.ino::UFSSize, la DERNIERE valeur est celle de la flash) ; nil si illisible
def ecranSysteme_nombre(r, cle)
    var v = (isinstance(r, map)) ? r.find(cle) : nil
    if (isinstance(v, list))    v = size(v) > 0 ? v[-1] : nil    end
    return type(v) == "int" ? v : nil
end
ecranSysteme.nombre = ecranSysteme_nombre
# Temperature de la puce, "ESP32":{"Temperature":x} du JSON des capteurs (xsns_127_esp32_sensors.ino : absente si un autre capteur
# a deja une Temperature), cherchee dans le texte sans json.load ; nil si absente
def ecranSysteme_temperature()
    import string
    var j = tasmota.read_sensors()
    var cle = "\"ESP32\":{\"Temperature\":"
    var i = j == nil ? -1 : string.find(j, cle)
    if (i < 0)    return nil    end
    # pas de « i += ... » suivi de « var f = i » : apres un return conditionnel, berry.exe y garde l'ancien i (constate le 2026-11-13)
    var debut = i + size(cle)
    var f = debut
    while (f < size(j) && string.find("-0123456789.", j[f]) >= 0)    f += 1    end
    return f > debut ? real(j[debut .. f - 1]) : nil
end
ecranSysteme.temperature = ecranSysteme_temperature
# Lectures par commande (toutes les LENT ms, page affichee) : Status 11 (support_tasmota.ino::MqttShowState : UptimeSec,
# LoadAvg, MqttCount, Wifi.LinkCount, Wifi.Downtime), UfsSize et UfsFree (Ko), RgxClients si le range extender est actif
# (xdrv_58_range_extender.ino::CmndRgxClients : une cle par client), temperature de la puce
def ecranSysteme_litLent()
    import ecranSysteme
    var r = tasmota.cmd("Status 11", boolMute)
    var sts = isinstance(r, map) ? r.find("StatusSTS") : nil
    var l = {"sts": isinstance(sts, map) ? sts : nil, "a": tasmota.millis(),
             "fsTaille": ecranSysteme.nombre(tasmota.cmd("UfsSize", boolMute), "UfsSize"),
             "fsLibre": ecranSysteme.nombre(tasmota.cmd("UfsFree", boolMute), "UfsFree"),
             "clients": nil, "temperature": ecranSysteme.temperature()}
    var rgx = serveur != nil ? serveur.find("rangeExtender") : nil
    if (isinstance(rgx, map) && rgx.find("activation", "OFF") == "ON")
        r = tasmota.cmd("RgxClients", boolMute)
        var c = isinstance(r, map) ? r.find("RgxClients") : nil
        if (isinstance(c, map))    l["clients"] = size(c)    end
    end
    ecranSysteme.etat()["lent"] = l
end
ecranSysteme.litLent = ecranSysteme_litLent
# Lu une fois (reussi) : Status 1 (support_command.ino::CmndStatus : RestartReason, BootCount), Status 2 (Version, BuildDateTime)
def ecranSysteme_litFixe()
    import string
    import ecranSysteme
    var r1 = tasmota.cmd("Status 1", boolMute)
    var r2 = tasmota.cmd("Status 2", boolMute)
    var prm = isinstance(r1, map) ? r1.find("StatusPRM") : nil
    var fwr = isinstance(r2, map) ? r2.find("StatusFWR") : nil
    if (!isinstance(prm, map) || !isinstance(fwr, map))    return    end
    var d = fwr.find("BuildDateTime")
    ecranSysteme.etat()["fixe"] = {"cause": prm.find("RestartReason"), "demarrages": prm.find("BootCount"), "version": fwr.find("Version"),
                         "compilation": d == nil ? nil : string.replace(str(d), "T", " ")}
end
ecranSysteme.litFixe = ecranSysteme_litFixe
# Pose la mesure `cle` dans `r` : [texte, barre (0-100) ou nil, niveau de couleur] ; niveau d'apres SEUILS sur `x`, ou force
def ecranSysteme_pose(r, cle, texte, barre, x, force)    import ecranSysteme    r[cle] = [texte, barre, force != nil ? force : ecranSysteme.niveau(cle, x)]    end
ecranSysteme.pose = ecranSysteme_pose
# Occupation en % de `utilise` sur `total`, bornee a 0..100 ; nil si total inconnu ou nul
def ecranSysteme_occupation(utilise, total)
    if (total == nil || utilise == nil || total <= 0)    return nil    end
    var p = int(utilise * 100 / total)
    return p < 0 ? 0 : (p > 100 ? 100 : p)
end
ecranSysteme.occupation = ecranSysteme_occupation
# Memoire et flash (tasmota.memory : xdrv_52_3_berry_tasmota.ino::l_memory, tout en Ko sauf frag en % et gc_time en ms ;
# psram et psram_free seulement avec PSRAM ; gc_time et gc_heap seulement apres un GC)
def ecranSysteme_memoire(r)
    import ecranSysteme
    var p = ecranSysteme.pose
    var k = ecranSysteme.ko
    var m = tasmota.memory()
    var v = m.find("heap_free")
    if (v != nil)    p(r, "ramLibre", k(v), nil, v)    end
    v = ecranSysteme.etat()["ramMin"]
    if (v != nil)    p(r, "ramMin", k(v), nil, v)    end
    v = m.find("frag")
    if (v != nil)    p(r, "fragmentation", str(v) + " %", v, v)    end
    var ps = m.find("psram")
    var pl = m.find("psram_free")
    if (ps != nil)    p(r, "psramTotale", k(ps), nil, nil)    end
    if (pl != nil)    var o = ecranSysteme.occupation(ps - pl, ps)    p(r, "psramLibre", k(pl), o, o)    end
    v = m.find("gc_heap")
    if (v != nil)    p(r, "ramGC", k(v), nil, nil)    end
    v = m.find("gc_time")
    if (v != nil)    p(r, "dureeGC", str(v) + " ms", nil, nil)    end
    v = m.find("stack_low")
    if (v != nil)    p(r, "pileMin", ecranSysteme.virgule(v, "%.1f") + " Ko", nil, v)    end
    v = m.find("iram_free")
    if (v != nil)    p(r, "iramLibre", k(v), nil, nil)    end
    var prog = m.find("program")
    var libre = m.find("program_free")
    if (prog != nil)    p(r, "programme", k(prog), nil, nil)    end
    if (prog != nil && libre != nil)
        var o = ecranSysteme.occupation(prog, libre)
        p(r, "otaLibre", k(libre), o, o)
        var possible = libre >= prog
        p(r, "ota", possible ? "possible" : "impossible", nil, nil, possible ? "vert" : "rouge")
    end
end
ecranSysteme.memoire = ecranSysteme_memoire
# Valeurs lues par commande (LENT) : systeme de fichiers, charge, uptime, Wi-Fi (pertes, hors ligne), MQTT, clients, temperature
def ecranSysteme_mesuresLentes(r)
    import ecranSysteme
    var p = ecranSysteme.pose
    var l = ecranSysteme.etat()["lent"]
    if (l == nil)    return    end
    var ft = l["fsTaille"]
    var fl = l["fsLibre"]
    if (ft != nil)    p(r, "fsTaille", ecranSysteme.ko(ft), nil, nil)    end
    if (fl != nil)    var o = ecranSysteme.occupation(ft == nil ? nil : ft - fl, ft)    p(r, "fsLibre", ecranSysteme.ko(fl), o, o)    end
    if (l["clients"] != nil)    p(r, "clients", str(l["clients"]), nil, nil)    end
    if (l["temperature"] != nil)    p(r, "temperature", ecranSysteme.virgule(l["temperature"], "%.1f") + " °C", nil, l["temperature"])    end
    var s = l["sts"]
    if (s == nil)    return    end
    var v = s.find("LoadAvg")
    if (type(v) == "int")    p(r, "charge", str(v) + " %", v > 100 ? 100 : v, v)    end
    v = s.find("UptimeSec")
    if (type(v) == "int")    p(r, "uptime", ecranSysteme.duree(v + (tasmota.millis() - l["a"]) / 1000), nil, nil)    end
    v = s.find("MqttCount")
    if (type(v) == "int")    p(r, "reconnexionsMqtt", str(v > 0 ? v - 1 : 0), nil, nil)    end
    var w = s.find("Wifi")
    if (!isinstance(w, map))    return    end
    v = w.find("LinkCount")      # une connexion de plus a chaque retour du Wi-Fi (support_wifi.ino::WifiSetState), la premiere comprise
    if (type(v) == "int")    p(r, "pertesWifi", str(v > 0 ? v - 1 : 0), nil, nil)    end
    v = ecranSysteme.secondes(w.find("Downtime"))
    if (v != nil)    p(r, "horsLigne", ecranSysteme.duree(v), nil, nil)    end
end
ecranSysteme.mesuresLentes = ecranSysteme_mesuresLentes
# ModBus (maitre seulement) : esclaves TasmotaSlaveModBus actifs moins ceux que le chien de garde tient pour muets, et age du
# dernier contact (reponse OU push : modBus_TasmotaSlaveModBus.be::noteContact). Instance du driver = global.modBus_TasmotaSlaveModBus
# (modBus_TasmotaSlaveModBus_init) ; absente (carte sans esclave) : rien. Delais depasses : aucun compteur expose, reste a « -- ».
def ecranSysteme_modbus(r)
    import global
    import ecranSysteme
    var d = global.modBus_TasmotaSlaveModBus
    if (type(d) != "instance" || drivers == nil)    return    end
    var esclaves = drivers.find("ModBus", {}).find("environnement", {}).find("TasmotaSlaveModBus", {})
    var n = 0
    for cle: esclaves.keys()
        var e = esclaves[cle]
        if (isinstance(e, map) && e.find("activation", "OFF") == "ON")    n += 1    end
    end
    var muets = d.esclavesMuets == nil ? 0 : size(d.esclavesMuets)
    ecranSysteme.pose(r, "esclaves", str(n - muets) + "/" + str(n), nil, nil, muets > 0 ? "rouge" : "vert")
    var dernier = nil
    for t: (d.derniersContacts == nil ? {} : d.derniersContacts)
        if (dernier == nil || t > dernier)    dernier = t    end
    end
    var maintenant = tasmota.rtc("local")
    if (dernier != nil && dernier <= maintenant)    ecranSysteme.pose(r, "dernierContact", "il y a " + ecranSysteme.duree(maintenant - dernier), nil, nil)    end
end
ecranSysteme.modbus = ecranSysteme_modbus
# Dernieres erreurs (logFonctions.dernieresErreurs, de la plus vieille a la plus recente) ; erreur1 = la plus recente
def ecranSysteme_erreurs(r)
    import ecranSysteme    import string
    var l = logFonctions.dernieresErreurs()
    for i: 1 .. size(l)
        var e = l[size(l) - i]
        var msg = str(e[1])
        if (size(msg) > ecranSysteme.LONGUEUR_ERREUR)    # coupe avant un octet de suite UTF-8 (10xxxxxx) : accent jamais coupe
            var n = ecranSysteme.LONGUEUR_ERREUR    while (n > 0 && (string.byte(msg[n]) & 0xC0) == 0x80)    n -= 1    end
            msg = msg[0 .. n - 1]
        end
        var h = type(e[0]) == "int" ? tasmota.strftime("%H:%M:%S", e[0]) + " " : ""
        ecranSysteme.pose(r, "erreur" + str(i), h + msg, nil, nil, "rouge")
    end
end
ecranSysteme.erreurs = ecranSysteme_erreurs
# Toutes les mesures : map cle -> [texte, barre, niveau] ; une donnee absente n'a pas de cle (affichee « -- »)
def ecranSysteme_mesures()
    import mqtt
    import ecranFonctions
    import ecranSysteme
    var r = {}
    var p = ecranSysteme.pose
    ecranSysteme.memoire(r)
    ecranSysteme.mesuresLentes(r)
    p(r, "sleep", str(tasmota.global.sleep) + " ms", nil, nil)
    var w = tasmota.wifi("rssi")
    if (w != nil)    p(r, "rssi", str(w) + " dBm", tasmota.wifi("quality"), w)    end
    w = tasmota.wifi("bssid")
    if (w != nil)    p(r, "bssid", str(w), nil, nil)    end
    w = tasmota.wifi("ip")
    if (w != nil)    p(r, "ip", str(w), nil, nil)    end
    var c = mqtt.connected()
    p(r, "mqtt", c ? "connecté" : "déconnecté", nil, nil, c ? "vert" : "rouge")
    c = tasmota.rtc("utc") > ecranSysteme.HEURE_VALIDE
    p(r, "heure", c ? "synchronisée" : "non synchronisée", nil, nil, c ? "vert" : "orange")
    var f = ecranSysteme.etat()["fixe"]
    for cle: ["cause", "demarrages", "version", "compilation"]
        if (f != nil && f[cle] != nil)    p(r, cle, str(f[cle]), nil, nil)    end
    end
    var v = ecranFonctions.reglage("veille")
    p(r, "luminosite", str(ecranFonctions.reglage("luminosite")) + " %", nil, nil)
    p(r, "veille", v == 0 ? "jamais" : str(v) + " min", nil, nil)
    ecranSysteme.modbus(r)
    ecranSysteme.erreurs(r)
    return r
end
ecranSysteme.mesures = ecranSysteme_mesures
# Ecrit toutes les mesures sur la page : texte et couleur de chaque CHAMPS, valeur et couleur de sa barre ; absente : « -- »
def ecranSysteme_rafraichit()
    import ecranSysteme
    var m = ecranSysteme.mesures()
    for c: ecranSysteme.CHAMPS
        var x = m.find(c[0])
        var coul = ecranSysteme.couleur(x == nil ? nil : x[2])
        ecranSysteme.ecris(c[3], "text", x == nil ? "--" : x[0])
        ecranSysteme.ecris(c[3], "text_color", coul)
        if (c[4] != nil)
            ecranSysteme.ecris(c[4], "val", (x == nil || x[1] == nil) ? 0 : x[1])
            ecranSysteme.ecris(c[4], "bg_color10", coul)
        end
    end
end
ecranSysteme.rafraichit = ecranSysteme_rafraichit
# Chaque seconde (callback frequent : pas de log info) : suivi, fin de confirmation, mesures toutes les MAJ ms SI page affichee
def ecranSysteme_tic()
    import ecranSysteme
    var e = ecranSysteme.etat()
    ecranSysteme.suit()
    var t = tasmota.millis()
    var a = e["confirmeA"]
    if (a != nil && (t < a || t - a >= ecranSysteme.CONFIRMATION))
        e["confirmeA"] = nil
        ecranSysteme.ecris(ecranSysteme.BOUTON_REDEMARRER, "text", ecranSysteme.TEXTE_REDEMARRER)
    end
    var p = ecranSysteme.page()
    if (p == nil || ecranSysteme.pageAffichee() != p)
        e["majA"] = nil    e["lentA"] = nil      # au retour sur la page : tout est relu aussitot
        return
    end
    a = e["majA"]
    if (a != nil && t >= a && t - a < ecranSysteme.MAJ)    return    end
    e["majA"] = t
    if (e["fixe"] == nil)    ecranSysteme.litFixe()    end
    a = e["lentA"]
    if (a == nil || t < a || t - a >= ecranSysteme.LENT)
        e["lentA"] = t
        ecranSysteme.litLent()
    end
    ecranSysteme.rafraichit()
end
ecranSysteme.tic = ecranSysteme_tic
# « Lancer le GC » : tasmota.gc() (tasmota_class.be::gc : gc.collect()), puis mesures relues au prochain tic
def ecranSysteme_gc()
    import ecranSysteme
    var avant = tasmota.memory("heap_free")
    tasmota.gc()
    ecranSysteme.etat()["majA"] = nil
    ecranSysteme.log("ECRAN_SYSTEME: GC lance depuis l'ecran, RAM libre " + str(avant) + " -> " + str(tasmota.memory("heap_free")) + " Ko !", LOG_LEVEL_DEBUG)
end
ecranSysteme.gc = ecranSysteme_gc
# « Redemarrer » : 1er appui = « Confirmer ? », 2e dans les CONFIRMATION ms = Restart 1 ; au-dela le texte revient (tic)
def ecranSysteme_redemarre()
    import ecranSysteme
    var e = ecranSysteme.etat()
    var t = tasmota.millis()
    var a = e["confirmeA"]
    if (a != nil && t >= a && t - a < ecranSysteme.CONFIRMATION)
        e["confirmeA"] = nil
        ecranSysteme.log("ECRAN_SYSTEME: redemarrage demande depuis l'ecran (Restart 1) !", LOG_LEVEL_INFO)
        tasmota.cmd("Restart 1", boolMute)
        return
    end
    e["confirmeA"] = t
    ecranSysteme.ecris(ecranSysteme.BOUTON_REDEMARRER, "text", ecranSysteme.TEXTE_CONFIRMER)
end
ecranSysteme.redemarre = ecranSysteme_redemarre
# Toucher d'un bouton de la page Systeme (LVGL genere : fonction du toucher ; HASPmota : ecranSysteme.bouton)
def ecranSysteme_appui(id)
    import ecranSysteme
    if (id == ecranSysteme.BOUTON_GC)    ecranSysteme.gc()
    elif (id == ecranSysteme.BOUTON_REDEMARRER)    ecranSysteme.redemarre()
    end
end
ecranSysteme.appui = ecranSysteme_appui
# Regle HASPmota d'un bouton (declencheur « hasp#p9b121#event ») : un appui relache (« up ») appelle appui(id)
def ecranSysteme_bouton(valeur, declencheur)
    import string
    import ecranSysteme
    if (valeur != "up")    return    end
    var o = string.split(string.split(str(declencheur), "#")[1], "b")
    if (size(o) == 2)    ecranSysteme.appui(int(o[1]))    end
end
ecranSysteme.bouton = ecranSysteme_bouton
# Regles HASPmota des deux boutons sur la page du persist (sans effet avec le LVGL genere, qui appelle appui lui-meme)
def ecranSysteme_regles()
    import ecranSysteme
    var p = ecranSysteme.page()
    if (p == nil)    return    end
    for id: [ecranSysteme.BOUTON_GC, ecranSysteme.BOUTON_REDEMARRER]
        tasmota.add_rule("hasp#p" + str(p) + "b" + str(id) + "#event", ecranSysteme.bouton, "ecranSysteme")
    end
end
ecranSysteme.regles = ecranSysteme_regles

# Retourne le module lors de l'importation
return ecranSysteme
