#- *********************************************************************************************
 * energieFonctions.be - Historique de consommation et page /energie (2026-11-02)
 * Conception : docs/superpowers/specs/2026-10-31-page-energie-differentiel-design.md
 *
 * Generique : lit le bloc ENERGY du JSON SENSOR ; la carte garde elle-meme son historique, sans le Pi.
 * Driver et cron : data/fs/controleEnergie.be. Persist : diverses.energie (activation, calibrage).
 *
 * Source unique : ENERGY.Total (kWh cumules). L'ecart entre deux notes, prises au changement d'heure LOCALE, est
 * verse a l'heure, au jour et au mois. Unites ENTIERES dans les fichiers : Wh et dix-milliemes d'euro (Berry ecrit
 * les reels sur 6 chiffres significatifs : un compteur de 1234,567 kWh perdrait ses decimales).
 *
 * Fichiers (dossier DOSSIER) :
 *   etat.json : {"w","u","l" : derniere note en Wh, epoch UTC et local ; "j","h","he" : jour, 24 heures en Wh et en euros ;
 *                "m","d","de" : mois, 31 jours ; "a" : [[mois, Wh, euros], ...] sur MAX_MOIS mois}
 *               UN seul fichier, ecrit de facon atomique : une coupure ne peut pas compter deux fois une heure.
 *   mois-AAAA-MM.json : {"d","de"}, jours d'un mois clos ; les plus anciens partent d'abord (purge).
 *   prix.json : [[date d'effet, prix en dix-milliemes d'euro par kWh], ...] trie par date.
 *   courbe.bin : heure locale de la copie (4 octets) puis la courbe de puissance, copiee a chaque heure : une coupure
 *                en perd au plus une heure (decision de l'utilisateur du 2026-11-02).
 * Chaque consommation est valorisee au prix en vigueur a sa date, et le cout est garde a cote des kWh : un nouveau
 * prix ne touche jamais le passe.
 *
 * Coupure : l'ecart est porte a l'heure de la note precedente si moins de ECART_CONSECUTIF_S ont passe (passage a
 * l'heure d'ete ou d'hiver compris), sinon a l'heure ecoulee au moment ou la carte le constate, sans repartition.
 *
 * SOLIDIFIE : aucun etat dans le module, table en lecture seule (piege 12 de outils_docs/SOLIDIFICATION_BERRY.md) ; la
 * courbe de puissance vit dans le driver. Chaque fonction qui cite le module l'importe (il n'est pas un global).
********************************************************************************************* -#

#@ solidify:energieFonctions
var energieFonctions = module("energieFonctions")

energieFonctions.DOSSIER = "/energie"
energieFonctions.DESCRIPTION = "/json/energie_page.json"   # ecrit par l'atelier des graphiques, jamais lu par Berry (relaye tel quel)
energieFonctions.DESCRIPTION_MAX = 4096                    # octets du fichier ; au-dela, refus sans lecture
energieFonctions.CHAMPS_DIRECT = ["Voltage", "ApparentPower", "ReactivePower", "Today", "Yesterday", "Total"]
energieFonctions.SEUIL_KO = 16                  # place libre minimale du FS avant ecriture
energieFonctions.MAX_ARCHIVES = 24
energieFonctions.MAX_MOIS = 24
energieFonctions.MAX_PRIX = 60
energieFonctions.PRIX_MAX = 2.0                 # euros par kWh : au-dela, valeur refusee
energieFonctions.PUISSANCE_MAX_W = 10000        # au-dela, l'ecart de Total n'est pas une consommation (EnergyTotal retabli a la main)
energieFonctions.ECART_CONSECUTIF_S = 7500      # 2 h 05 : deux notes consecutives, heure d'hiver comprise
energieFonctions.HEURE_VALIDE = 1577836800      # 2020-01-01 : avant, l'heure n'est pas encore synchronisee
energieFonctions.PAS_COURBE_S = 300
energieFonctions.NB_POINTS = 288                # 24 h au pas de 5 min, 2 octets par point
energieFonctions.POINT_VIDE = 65535
energieFonctions.DEFAUTS_BL0942 = {"PowerCal": 596, "VoltageCal": 15187, "CurrentCal": 251213}

def energieFonctions_zeros(n)
    var l = []
    for i: 1 .. n    l.push(0)    end
    return l
end
energieFonctions.zeros = energieFonctions_zeros

# Contenu d'un fichier du dossier, ou nil s'il est absent ou illisible
def energieFonctions_lisJson(nom)
    import json
    import energieFonctions
    try
        var f = open(energieFonctions.DOSSIER + "/" + nom, "r")
        var texte = f.read()
        f.close()
        return json.load(texte)
    except ..
        return nil
    end
end
energieFonctions.lisJson = energieFonctions_lisJson

# Ecriture atomique (texte ou bytes) : fichier temporaire controle par sa taille, puis renommage. Rend false si
# l'ecriture a echoue (FS plein) : l'ancien fichier reste alors intact.
def energieFonctions_ecrisFichier(nom, contenu)
    import path
    import energieFonctions
    var chemin = energieFonctions.DOSSIER + "/" + nom
    var temporaire = chemin + ".tmp"
    try
        if (!path.exists(energieFonctions.DOSSIER))    path.mkdir(energieFonctions.DOSSIER)    end
        var f = open(temporaire, "w")
        f.write(contenu)
        f.close()
        f = open(temporaire, "r")
        var ecrit = f.size()
        f.close()
        if (ecrit != size(contenu))
            path.remove(temporaire)
            logFonctions.log("ENERGIE_ERREUR: Ecriture incomplete de " + nom + " (FS plein ?) !", LOG_LEVEL_ERREUR)
            return false
        end
        if (!path.rename(temporaire, chemin))
            path.remove(chemin)     # lisEtat reprend le temporaire si la carte s'arrete ici
            path.rename(temporaire, chemin)
        end
        return true
    except .. as erreur, message
        logFonctions.log("ENERGIE_ERREUR: Ecriture de " + nom + " : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR)
        return false
    end
end
energieFonctions.ecrisFichier = energieFonctions_ecrisFichier

def energieFonctions_ecrisJson(nom, valeur)
    import json
    import energieFonctions
    return energieFonctions.ecrisFichier(nom, json.dump(valeur))
end
energieFonctions.ecrisJson = energieFonctions_ecrisJson

def energieFonctions_lisEtat()
    import energieFonctions
    var etat = energieFonctions.lisJson("etat.json")
    if (etat == nil)    etat = energieFonctions.lisJson("etat.json.tmp")    end
    return (isinstance(etat, map) ? etat : nil)
end
energieFonctions.lisEtat = energieFonctions_lisEtat

# Place libre du FS en Ko. shortcut: une reponse illisible compte comme de la place, l'ecriture controle sa taille de toute facon
def energieFonctions_libreKo()
    var r = tasmota.cmd("UfsFree", boolMute)
    var libre = (isinstance(r, map) ? r.find("UfsFree") : nil)
    return (type(libre) == "int" ? libre : 1000000)
end
energieFonctions.libreKo = energieFonctions_libreKo

# Efface les archives les plus anciennes si elles sont trop nombreuses ou si le FS approche de la saturation
def energieFonctions_purge()
    import path
    import string
    import energieFonctions
    if (!path.exists(energieFonctions.DOSSIER))    return    end
    var archives = []
    for nom: path.listdir(energieFonctions.DOSSIER)
        if (string.find(nom, "mois-") == 0)    archives.push(nom)    end
    end
    while (size(archives) > 0 && (size(archives) > energieFonctions.MAX_ARCHIVES || energieFonctions.libreKo() < energieFonctions.SEUIL_KO))
        var ancien = 0
        for i: 1 .. size(archives) - 1
            if (archives[i] < archives[ancien])    ancien = i    end
        end
        path.remove(energieFonctions.DOSSIER + "/" + archives[ancien])
        logFonctions.log("ENERGIE: Archive " + archives[ancien] + " effacee (place ou nombre) !", LOG_LEVEL_INFO)
        archives.remove(ancien)
    end
    if (energieFonctions.libreKo() < energieFonctions.SEUIL_KO)
        logFonctions.log("ENERGIE_ERREUR: FS presque plein, plus aucune archive a effacer !", LOG_LEVEL_ERREUR)
    end
end
energieFonctions.purge = energieFonctions_purge

# Prix en dix-milliemes d'euro par kWh en vigueur a la date 'jour' et a l'heure 'heure', 0 si aucun.
# Entree de prix.json : [date, prix] (Base) ou [date, prix HP, prix HC, heures creuses (bit n = heure n)]
def energieFonctions_prixA(jour, heure)
    import energieFonctions
    var liste = energieFonctions.lisJson("prix.json")
    var prix = 0
    if (isinstance(liste, list))
        for p: liste
            if (p[0] <= jour)    prix = ((size(p) > 2 && ((p[3] >> heure) & 1) != 0) ? p[2] : p[1])    end
        end
    end
    return prix
end
energieFonctions.prixA = energieFonctions_prixA

# Etat de depart : aucune note
def energieFonctions_etatNeuf()
    import energieFonctions
    return {"j": "", "h": energieFonctions.zeros(24), "he": energieFonctions.zeros(24),
            "m": "", "d": energieFonctions.zeros(31), "de": energieFonctions.zeros(31), "a": []}
end
energieFonctions.etatNeuf = energieFonctions_etatNeuf

# Fait passer l'etat au jour et au mois de t (time_dump) ; le mois clos part en archive
def energieFonctions_bascule(etat, t)
    import string
    import energieFonctions
    var mois = string.format("%04i-%02i", t["year"], t["month"])
    var jour = mois + string.format("-%02i", t["day"])
    if (etat["m"] != mois)
        if (etat["m"] != "")
            energieFonctions.ecrisJson("mois-" + etat["m"] + ".json", {"d": etat["d"], "de": etat["de"]})
        end
        etat["m"] = mois
        etat["d"] = energieFonctions.zeros(31)
        etat["de"] = energieFonctions.zeros(31)
        etat["a"].push([mois, 0, 0])
        if (size(etat["a"]) > energieFonctions.MAX_MOIS)    etat["a"].remove(0)    end
    end
    if (etat["j"] != jour)
        etat["j"] = jour
        etat["h"] = energieFonctions.zeros(24)
        etat["he"] = energieFonctions.zeros(24)
    end
end
energieFonctions.bascule = energieFonctions_bascule

# Verse 'wh' a l'heure, au jour et au mois de l'instant local donne, valorises au prix de cette date
def energieFonctions_verse(etat, wh, instant)
    import energieFonctions
    var t = tasmota.time_dump(instant)
    energieFonctions.bascule(etat, t)
    var euros = int(real(wh) * energieFonctions.prixA(etat["j"], t["hour"]) / 1000 + 0.5)
    var a = etat["a"][-1]
    etat["h"][t["hour"]] += wh
    etat["he"][t["hour"]] += euros
    etat["d"][t["day"] - 1] += wh
    etat["de"][t["day"] - 1] += euros
    a[1] += wh
    a[2] += euros
end
energieFonctions.verse = energieFonctions_verse

# Note le compteur si l'heure locale a change ; rend true si l'etat a change
def energieFonctions_note(etat, wh, utc, local)
    import energieFonctions
    if (etat.find("u") != nil)
        if (local / 3600 == etat["l"] / 3600)    return false    end
        var ecoule = utc - etat["u"]
        var delta = wh - etat["w"]
        if (delta < 0 || real(delta) > real(energieFonctions.PUISSANCE_MAX_W) * (ecoule + 3600) / 3600)
            logFonctions.log("ENERGIE_ERREUR: Compteur incoherent (" + str(etat["w"]) + " -> " + str(wh) + " Wh) : ecart non compte !", LOG_LEVEL_ERREUR)
        else
            energieFonctions.verse(etat, delta, ecoule <= energieFonctions.ECART_CONSECUTIF_S ? etat["l"] : local - 3600)
        end
    end
    etat["w"] = wh
    etat["u"] = utc
    etat["l"] = local
    energieFonctions.bascule(etat, tasmota.time_dump(local))
    return true
end
energieFonctions.note = energieFonctions_note

# Bloc ENERGY du JSON SENSOR, lu au moment de l'appel ; nil si absent
def energieFonctions_mesure()
    import json
    var capteurs = tasmota.read_sensors()
    var lu = (capteurs != nil ? json.load(capteurs) : nil)
    var energie = (isinstance(lu, map) ? lu.find("ENERGY") : nil)
    return (isinstance(energie, map) ? energie : nil)
end
energieFonctions.mesure = energieFonctions_mesure

# Note de l'heure (etat relu en flash a chaque fois : rien de garde en RAM). Rend false tant que le compteur est illisible.
def energieFonctions_releve(mesure, rtc)
    import path
    import energieFonctions
    var total = mesure.find("Total")
    if (type(total) != "int" && type(total) != "real")    return false    end
    energieFonctions.purge()
    var etat = energieFonctions.lisEtat()
    if (etat == nil)
        var chemin = energieFonctions.DOSSIER + "/etat.json"
        if (path.exists(chemin))        # abime : mis de cote, pas ecrase en silence
            path.rename(chemin, chemin + ".corrompu")
            logFonctions.log("ENERGIE_ERREUR: etat.json illisible, mis de cote en etat.json.corrompu, historique repris a zero !", LOG_LEVEL_ERREUR)
        end
        etat = energieFonctions.etatNeuf()
    end
    if (energieFonctions.note(etat, int(real(total) * 1000 + 0.5), rtc["utc"], rtc["local"]))
        energieFonctions.ecrisJson("etat.json", etat)
        logFonctions.log("ENERGIE: Compteur note : " + str(total) + " kWh !", LOG_LEVEL_DEBUG)
    end
    return true
end
energieFonctions.releve = energieFonctions_releve

# Euros par kWh (texte) -> dix-milliemes d'euro, nil si hors limites
def energieFonctions_lisPrix(euros)
    import string
    import energieFonctions
    var valeur = real(string.replace(str(euros), ",", "."))
    if (!(valeur > 0) || valeur > energieFonctions.PRIX_MAX)    return nil    end
    return int(valeur * 10000 + 0.5)
end
energieFonctions.lisPrix = energieFonctions_lisPrix

# Heures creuses "22-6,14-17" -> masque (bit n = heure n) ; nil si illisible ou si elles couvrent toute la journee
def energieFonctions_masqueHC(texte)
    import string
    var masque = 0
    for plage: string.split(string.replace(str(texte), " ", ""), ",")
        var bornes = string.split(plage, "-")
        if (size(bornes) != 2)    return nil    end
        var debut = int(bornes[0])
        var fin = int(bornes[1])
        for i: 0 .. 1
            var lue = (i == 0 ? debut : fin)
            if (bornes[i] != str(lue) && bornes[i] != string.format("%02i", lue))    return nil    end
        end
        if (debut < 0 || debut > 23 || fin < 0 || fin > 24)    return nil    end
        fin = fin % 24
        if (debut == fin)    return nil    end
        while (debut != fin)
            masque = masque | (1 << debut)
            debut = (debut + 1) % 24
        end
    end
    return (masque == 0xFFFFFF ? nil : masque)
end
energieFonctions.masqueHC = energieFonctions_masqueHC

# Enregistre un tarif (date AAAA-MM-JJ, euros par kWh ; si HC/HP : 'euros' = HP, plus le prix HC et les plages d'heures
# creuses) ; rend nil, ou le message d'erreur. Meme date : tarif remplace.
def energieFonctions_ajoutePrix(jour, euros, eurosHC, plages)
    import string
    import energieFonctions
    if (type(jour) != "string" || size(jour) != 10 || jour[4] != "-" || jour[7] != "-")    return "Date invalide"    end
    var a = int(jour[0 .. 3])
    var m = int(jour[5 .. 6])
    var j = int(jour[8 .. 9])
    var bissextile = (a % 4 == 0 && (a % 100 != 0 || a % 400 == 0))
    if (a < 2000 || m < 1 || m > 12 || string.format("%04i-%02i-%02i", a, m, j) != jour)    return "Date invalide"    end
    if (j < 1 || j > [31, bissextile ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])    return "Date invalide"    end
    var prix = energieFonctions.lisPrix(euros)
    if (prix == nil)    return "Prix invalide"    end
    var nouveau = [jour, prix]
    if (eurosHC != nil)
        var hc = energieFonctions.lisPrix(eurosHC)
        if (hc == nil)    return "Prix invalide"    end
        var masque = energieFonctions.masqueHC(plages)
        if (masque == nil)    return "Heures creuses invalides"    end
        nouveau = [jour, prix, hc, masque]
    end
    var liste = energieFonctions.lisJson("prix.json")
    if (!isinstance(liste, list))    liste = []    end
    var i = 0
    while (i < size(liste) && liste[i][0] < jour)    i += 1    end
    if (i < size(liste) && liste[i][0] == jour)
        liste[i] = nouveau
    else
        if (size(liste) >= energieFonctions.MAX_PRIX)    return "Trop de prix enregistres"    end
        liste.insert(i, nouveau)
    end
    if (!energieFonctions.ecrisJson("prix.json", liste))    return "Ecriture impossible"    end
    logFonctions.log("ENERGIE: Tarif " + str(nouveau) + " enregistre !", LOG_LEVEL_INFO)
    return nil
end
energieFonctions.ajoutePrix = energieFonctions_ajoutePrix

# Courbe de puissance : un bytes garde par le driver, indexe par l'heure locale (repart vide au demarrage)
def energieFonctions_courbeVide()
    import energieFonctions
    var courbe = bytes(-2 * energieFonctions.NB_POINTS)
    for i: 0 .. energieFonctions.NB_POINTS - 1
        courbe.set(2 * i, energieFonctions.POINT_VIDE, 2)
    end
    return courbe
end
energieFonctions.courbeVide = energieFonctions_courbeVide

def energieFonctions_indexCourbe(local)
    import energieFonctions
    return (local / energieFonctions.PAS_COURBE_S) % energieFonctions.NB_POINTS
end
energieFonctions.indexCourbe = energieFonctions_indexCourbe

def energieFonctions_notePuissance(courbe, local, puissance)
    import energieFonctions
    if (type(puissance) != "int" && type(puissance) != "real")    return    end
    var w = int(puissance + 0.5)
    w = (w < 0 ? 0 : (w >= energieFonctions.POINT_VIDE ? energieFonctions.POINT_VIDE - 1 : w))
    courbe.set(2 * energieFonctions.indexCourbe(local), w, 2)
end
energieFonctions.notePuissance = energieFonctions_notePuissance

def energieFonctions_sauveCourbe(courbe, local)
    import energieFonctions
    var contenu = bytes(-4)
    contenu.set(0, local, 4)
    return energieFonctions.ecrisFichier("courbe.bin", contenu + courbe)
end
energieFonctions.sauveCourbe = energieFonctions_sauveCourbe

# Courbe relue de courbe.bin, ou courbe vide si le fichier est absent, abime ou vieux de plus de 24 h. Les points
# ecoules depuis la copie sont vides : sinon ceux de la veille passeraient pour ceux de la coupure.
def energieFonctions_lisCourbe(local)
    import energieFonctions
    var vide = energieFonctions.courbeVide()
    var contenu
    try
        var f = open(energieFonctions.DOSSIER + "/courbe.bin", "r")
        contenu = f.readbytes()
        f.close()
    except ..
        return vide
    end
    if (size(contenu) != 4 + size(vide))    return vide    end
    var copie = contenu.get(0, 4)
    var ecoule = local - copie
    if (ecoule < 0 || ecoule >= energieFonctions.NB_POINTS * energieFonctions.PAS_COURBE_S)    return vide    end
    var courbe = contenu[4 .. -1]
    var fin = energieFonctions.indexCourbe(local)
    var i = energieFonctions.indexCourbe(copie)
    while (i != fin)
        i = (i + 1) % energieFonctions.NB_POINTS
        courbe.set(2 * i, energieFonctions.POINT_VIDE, 2)
    end
    return courbe
end
energieFonctions.lisCourbe = energieFonctions_lisCourbe

# Rejoue le calibrage du persist si les trois valeurs lues sont les defauts du firmware (fichier /.drvset003 perdu par un
# flash serie du FS) ; un recalibrage manuel est respecte. Rend true si le calibrage a ete rejoue.
def energieFonctions_verifieCalibrage()
    import energieFonctions
    var calibrage = diverses.find("energie", {}).find("calibrage")
    if (!isinstance(calibrage, map))    return false    end
    for cle: energieFonctions.DEFAUTS_BL0942.keys()
        var r = tasmota.cmd(cle, boolMute)
        if (type(calibrage.find(cle)) != "int" || !isinstance(r, map) || r.find(cle) != energieFonctions.DEFAUTS_BL0942[cle])    return false    end
    end
    for cle: energieFonctions.DEFAUTS_BL0942.keys()
        tasmota.cmd(cle + " " + str(calibrage[cle]), boolMute)
    end
    logFonctions.log("ENERGIE: Calibrage du persist rejoue (valeurs par defaut trouvees) !", LOG_LEVEL_INFO)
    return true
end
energieFonctions.verifieCalibrage = energieFonctions_verifieCalibrage

# Compteur du moment en Wh, en texte JSON (entier : un reel perdrait ses decimales, voir l'en-tete) ; "null" s'il est illisible
def energieFonctions_totalWh()
    import energieFonctions
    var m = energieFonctions.mesure()
    var total = (m != nil ? m.find("Total") : nil)
    return ((type(total) == "int" || type(total) == "real") ? str(int(real(total) * 1000 + 0.5)) : "null")
end
energieFonctions.totalWh = energieFonctions_totalWh

# Reponse JSON de f=donnees : etat, prix, date de la carte et courbe, du point le plus ancien au plus recent
def energieFonctions_envoieDonnees(courbe)
    import json
    import string
    import webserver
    import energieFonctions
    var local = tasmota.rtc()["local"]
    var t = tasmota.time_dump(local)
    var prix = energieFonctions.lisJson("prix.json")
    webserver.content_send(string.format("{\"aujourdhui\":\"%04i-%02i-%02i\",\"etat\":", t["year"], t["month"], t["day"]))
    var etat = energieFonctions.lisEtat()
    webserver.content_send(etat == nil ? "null" : json.dump(etat))
    webserver.content_send(",\"wCourant\":" + energieFonctions.totalWh() + ",\"prix\":" + (prix == nil ? "[]" : json.dump(prix)) + ",\"courbe\":[")
    var debut = energieFonctions.indexCourbe(local) + 1
    var morceau = ""
    for i: 0 .. energieFonctions.NB_POINTS - 1
        var w = courbe.get(2 * ((debut + i) % energieFonctions.NB_POINTS), 2)
        morceau += (i > 0 ? "," : "") + (w == energieFonctions.POINT_VIDE ? "null" : str(w))
        if (i % 48 == 47)
            webserver.content_send(morceau)
            morceau = ""
            tasmota.yield()
        end
    end
    webserver.content_send("]}")
    webserver.content_close()
end
energieFonctions.envoieDonnees = energieFonctions_envoieDonnees

# Reponse JSON de f=direct : les valeurs instantanees (p i f hz) puis les champs ENERGY presents sous leur nom Tasmota
def energieFonctions_envoieDirect()
    import json
    import webserver
    import energieFonctions
    var m = energieFonctions.mesure()
    if (m == nil)    m = {}    end
    var r = {"p": m.find("Power"), "i": m.find("Current"), "f": m.find("Factor"), "hz": m.find("Frequency")}
    for cle: energieFonctions.CHAMPS_DIRECT
        if (m.contains(cle))    r[cle] = m[cle]    end
    end
    webserver.content_send(json.dump(r))
    webserver.content_close()
end
energieFonctions.envoieDirect = energieFonctions_envoieDirect

# Relaie un fichier JSON ligne par ligne (jamais lu en entier : tas). max > 0 : taille brute maximale, 413 au-dela sans lecture.
# Codes : 200 relaye, 404 absent, 413 trop gros.
def energieFonctions_relaie(chemin, max)
    import webserver
    import gestionFileFolder
    var taille = -1
    try
        var f = open(chemin, "r")
        taille = f.size()
        f.close()
    except ..
    end
    var code = (taille < 0 ? 404 : ((max > 0 && taille > max) ? 413 : 200))
    webserver.content_open(code, "application/json")
    if (code == 200)
        gestionFileFolder.readFileByLineAndContentSend(chemin)
    else
        webserver.content_send(code == 404 ? "{\"erreur\":\"absent\"}" : "{\"erreur\":\"trop gros\"}")
    end
    webserver.content_close()
    return code
end
energieFonctions.relaie = energieFonctions_relaie

# Reponse de f=description : le fichier de l'atelier, tel quel (200), 404 s'il manque, 413 au-dela de DESCRIPTION_MAX
def energieFonctions_envoieDescription()
    import energieFonctions
    return energieFonctions.relaie(energieFonctions.DESCRIPTION, energieFonctions.DESCRIPTION_MAX)
end
energieFonctions.envoieDescription = energieFonctions_envoieDescription

# Reponse de f=mois&m=AAAA-MM : l'archive du mois (200), 404 si purgee, 400 si 'm' n'est pas strictement AAAA-MM
def energieFonctions_envoieMois(m)
    import re
    import webserver
    import energieFonctions
    if (type(m) != "string" || re.match("^[0-9][0-9][0-9][0-9]-(0[1-9]|1[0-2])$", m) == nil)
        webserver.content_open(400, "application/json")
        webserver.content_send("{\"erreur\":\"mois invalide\"}")
        webserver.content_close()
        return 400
    end
    return energieFonctions.relaie(energieFonctions.DOSSIER + "/mois-" + m + ".json", 0)
end
energieFonctions.envoieMois = energieFonctions_envoieMois

# Page 'nom' (gabarit et script du meme nom), le bouton de retour en bas
def energieFonctions_page(nom, bouton)
    import webserver
    import gestionFileFolder
    logFonctions.log("ENERGIE: Page demandee !", LOG_LEVEL_DEBUG, "serveurWeb")
    webserver.content_start("Energie")
    webserver.content_send_style()
    webserver.content_send("<style>")
    gestionFileFolder.readFileByLineAndContentSend("/sd/css/energie.css")
    webserver.content_send("</style>")
    gestionFileFolder.readFileByLineAndContentSend("/sd/html/" + nom + ".html")
    webserver.content_send("<script>")
    gestionFileFolder.readFileByLineAndContentSend("/sd/js/" + nom + ".js")
    webserver.content_send("</script>")
    webserver.content_button(bouton)
    webserver.content_stop()
end
energieFonctions.page = energieFonctions_page

# Route GET /energie : f=donnees, f=direct, f=description, f=mois, f=tarifs (sous-page de Configuration), sinon la page. courbe : le bytes du driver
def energieFonctions_route(courbe)
    import webserver
    import energieFonctions
    if (!webserver.check_privileged_access())    return nil    end
    var f = (webserver.has_arg("f") ? webserver.arg("f") : "")
    var ouverte = false
    try
        if (f == "donnees" || f == "direct")
            webserver.content_open(200, "application/json")
            ouverte = true
        end
        if (f == "donnees")
            energieFonctions.envoieDonnees(courbe)
        elif (f == "direct")
            energieFonctions.envoieDirect()
        elif (f == "description")
            energieFonctions.envoieDescription()
        elif (f == "mois")
            energieFonctions.envoieMois(webserver.has_arg("m") ? webserver.arg("m") : "")
        elif (f == "tarifs")
            energieFonctions.page("energieTarifs", webserver.BUTTON_CONFIGURATION)
        else
            energieFonctions.page("energie", webserver.BUTTON_MAIN)
        end
    except .. as erreur, message
        logFonctions.log("ENERGIE_ERREUR: Route /energie : " + str(erreur) + " " + str(message) + " !", LOG_LEVEL_ERREUR, "serveurWeb")
        if (ouverte)    webserver.content_close()    end
    end
end
energieFonctions.route = energieFonctions_route

# Route POST /energie : jour (AAAA-MM-JJ), prix (euros par kWh) ; si HC/HP : hc (euros par kWh) et plages
def energieFonctions_enregistrePrix()
    import json
    import webserver
    import energieFonctions
    if (!webserver.check_privileged_access())    return nil    end
    var erreur = energieFonctions.ajoutePrix(webserver.has_arg("jour") ? webserver.arg("jour") : "", webserver.has_arg("prix") ? webserver.arg("prix") : "",
                                              webserver.has_arg("hc") ? webserver.arg("hc") : nil, webserver.has_arg("plages") ? webserver.arg("plages") : "")
    webserver.content_open(erreur == nil ? 200 : 400, "application/json")
    webserver.content_send(erreur == nil ? "{\"ok\":true}" : json.dump({"erreur": erreur}))
    webserver.content_close()
end
energieFonctions.enregistrePrix = energieFonctions_enregistrePrix

return energieFonctions
