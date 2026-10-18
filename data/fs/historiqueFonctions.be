#- *********************************************************************************************
 * historiqueFonctions.be - Historique des mesures d'un module, conserve SUR le module (2026-10-13)
 *
 * Deux etages :
 *  - RAM   : les 'dureeHeures' (24) dernieres heures au pas de 'pasMinutes' (5). Chaque point est la
 *            moyenne des mesures recues pendant le pas. Perdu au redemarrage.
 *  - Flash : une ligne par HEURE (min, moyenne, max de chaque serie), en AJOUT SEUL, un fichier par
 *            mois UTC : /histo/<nom>-AAAA-MM.bin. Ajout seul : rien n'est reecrit en place, une coupure
 *            ne perd que l'heure en cours. Les mois au-dela de 'moisConserves' (24) sont supprimes.
 *
 * Format d'un fichier : en-tete "HST1" + nbSeries (1 o) + longueur (2 o) + noms des series separes
 * par des virgules, puis un enregistrement par heure : epoch UTC du debut de l'heure (4 o) + pour
 * chaque serie min, moy, max (3 float32). NaN = aucune mesure. L'en-tete rend chaque fichier lisible
 * seul, meme apres un changement de la liste des series. Cuve (4 series) : 52 o/h, ~38 Ko/mois.
 *
 * Reserve aux cartes ESP32-S3 et P4 (PSRAM) : les ESP32 classiques n'ont pas la memoire (2026-10-13).
 *
 * Configuration de la CARTE dans le persist, bloc diverses.historique :
 *     {"activation": "ON", "pasMinutes": 5, "dureeHeures": 24, "moisConserves": 24, "seriesMax": 12,
 *      "series": {"hauteurEau": "sensorsCuve.niveauCuve.hauteurEau", "temperature": "DS18B20.Temperature"}}
 *   - chaque serie = un chemin dans le JSON SENSOR de la carte (tasmota.read_sensors(), le meme que
 *     tele/<topic>/SENSOR), ou une source speciale : @power<n> (etat du relais n, 1/0), @rssi, @heap ;
 *   - "series" vide = mode AUTO : toutes les valeurs numeriques (et ON/OFF) du JSON SENSOR, relevees
 *     2 min apres le demarrage, dans la limite de seriesMax. Les series sont fixees a ce moment.
 *   Demarrage : autoexec.be -> historiqueFonctions.demarre(diverses["historique"]) ; releve chaque minute.
 *   Un module peut corriger les valeurs avant enregistrement (mesure en erreur -> nil) :
 *     historiqueFonctions.ajouteFiltre(fonction(chemins, valeurs))   (voir controleCuve.be)
 *
 * Lecture web (JSON, pour les futurs graphiques ; heures = epoch UTC en secondes, absent = null) :
 *     /histo?n=mesures&p=liste            -> {"nom","series","mois":["2026-09","2026-10"]}
 *     /histo?n=mesures&p=jour             -> {"nom","series","pas","t0","valeurs":[[serie 1],[serie 2]]}  (RAM)
 *     /histo?n=mesures&p=mois&m=2026-10   -> {"nom","series","lignes":[[t, min1, moy1, max1, min2, ...], ...]}
 * Page des graphiques : /graphiques, servie par graphiquesFonctions.be (route declaree par HISTORIQUE_WEB).
********************************************************************************************* -#

var historiqueFonctions = module("historiqueFonctions")

historiqueFonctions.DOSSIER = "/histo"
historiqueFonctions.instances = {}      # nom -> HISTORIQUE, pour la route /histo
historiqueFonctions.config = nil        # bloc diverses.historique de la carte (demarre)
historiqueFonctions.chemins = nil       # chemins des series dans le JSON SENSOR (ou @source)
historiqueFonctions.filtres = []        # fonctions(chemins, valeurs) appelees avant chaque mesure
historiqueFonctions.IGNORES = ["Time", "TempUnit", "PressureUnit", "SpeedUnit", "Id", "IPAddress"]

# Noms des historiques de la carte
def historiqueFonctions_nomsInstances()
    var noms = []
    for k: historiqueFonctions.instances.keys()    noms.push(k)    end
    return noms
end
historiqueFonctions.nomsInstances = historiqueFonctions_nomsInstances

# Texte JSON d'une valeur : null si NaN ou nil
def historiqueFonctions_texte(v)
    import string
    if (v == nil || v != v)    return "null"    end
    return string.format("%.2f", v)
end
historiqueFonctions.texte = historiqueFonctions_texte

class HISTORIQUE
    var nom, series, nbSeries
    var pas, nbPoints, moisConserves
    var ram, ramIndice, dernierPas                  # tampon circulaire RAM (float32), prochain emplacement, dernier pas ecrit
    var pasCourant, sommePas, nbPas                 # accumulateurs du pas en cours
    var heureCourante, minH, maxH, sommeH, nbH      # accumulateurs de l'heure en cours

    def init(nom, series, config)
        import path
        import math
        import string
        import historiqueFonctions
        if (config == nil)    config = {}    end

        self.nom = nom
        self.series = series
        self.nbSeries = size(series)
        self.pas = int(config.find("pasMinutes", 5)) * 60
        if (self.pas < 60)    self.pas = 60    end
        self.nbPoints = int(real(config.find("dureeHeures", 24)) * 3600 / self.pas)
        self.moisConserves = int(config.find("moisConserves", 24))

        self.ram = bytes(-(self.nbPoints * self.nbSeries * 4))
        for i: 0 .. self.nbPoints * self.nbSeries - 1    self.ram.setfloat(i * 4, math.nan)    end
        self.ramIndice = 0
        self.razPas()
        self.razHeure()

        path.mkdir(historiqueFonctions.DOSSIER)
        historiqueFonctions.instances[nom] = self
        self.purge()
        logFonctions.log(string.format("HISTORIQUE: '%s' pret : %i series, %i points de %i s en RAM, %i mois en flash !", nom, self.nbSeries, self.nbPoints, self.pas, self.moisConserves), LOG_LEVEL_DEBUG, nom)
    end

    def razPas()
        self.sommePas = []    self.nbPas = []
        for i: 1 .. self.nbSeries    self.sommePas.push(0.0)    self.nbPas.push(0)    end
    end

    def razHeure()
        self.minH = []    self.maxH = []    self.sommeH = []    self.nbH = []
        for i: 1 .. self.nbSeries    self.minH.push(0.0)    self.maxH.push(0.0)    self.sommeH.push(0.0)    self.nbH.push(0)    end
    end

    # Recoit une mesure par serie (nil ou NaN = absente). A appeler a intervalle regulier (chaque minute).
    def mesure(valeurs)
        var t = tasmota.rtc()["utc"]
        if (t < 1700000000)    return    end      # heure pas encore synchronisee : mesure non datable

        var p = t / self.pas
        var h = t / 3600
        if (self.pasCourant != nil && p != self.pasCourant)          self.cloturePas(p)       end
        if (self.heureCourante != nil && h != self.heureCourante)    self.clotureHeure()      end
        self.pasCourant = p
        self.heureCourante = h

        for i: 0 .. self.nbSeries - 1
            var v = (i < size(valeurs) ? valeurs[i] : nil)
            if (v != nil)    v = real(v)    end
            if (v != nil && v == v)
                self.sommePas[i] += v    self.nbPas[i] += 1
                if (self.nbH[i] == 0 || v < self.minH[i])    self.minH[i] = v    end
                if (self.nbH[i] == 0 || v > self.maxH[i])    self.maxH[i] = v    end
                self.sommeH[i] += v    self.nbH[i] += 1
            end
        end
    end

    # Ecrit un point (une valeur par serie) dans le tampon circulaire
    def ecritPoint(valeurs)
        var base = self.ramIndice * self.nbSeries * 4
        for i: 0 .. self.nbSeries - 1    self.ram.setfloat(base + i * 4, valeurs[i])    end
        self.ramIndice = (self.ramIndice + 1) % self.nbPoints
    end

    # Clot le pas en cours (moyenne) ; les pas sautes (coupure, reboot du WiFi...) deviennent des trous
    def cloturePas(nouveauPas)
        import math
        var moyennes = []
        for i: 0 .. self.nbSeries - 1    moyennes.push(self.nbPas[i] > 0 ? self.sommePas[i] / self.nbPas[i] : math.nan)    end
        self.ecritPoint(moyennes)

        var trous = nouveauPas - self.pasCourant - 1
        if (trous > self.nbPoints)    trous = self.nbPoints    end
        if (trous > 0)
            var vide = []
            for i: 1 .. self.nbSeries    vide.push(math.nan)    end
            for k: 1 .. trous    self.ecritPoint(vide)    end
        end

        self.dernierPas = nouveauPas - 1
        self.razPas()
    end

    # Chemin du fichier du mois (UTC) d'un epoch
    def fichierMois(epoch)
        import string
        import historiqueFonctions
        var d = tasmota.time_dump(epoch)
        return string.format("%s/%s-%04i-%02i.bin", historiqueFonctions.DOSSIER, self.nom, d["year"], d["month"])
    end

    # En-tete d'un fichier : "HST1" + nbSeries + longueur + noms
    def entete()
        var noms = self.series.concat(",")
        var b = bytes().fromstring("HST1")
        b.add(self.nbSeries, 1)
        b.add(size(noms), 2)
        b = b + bytes().fromstring(noms)
        return b
    end

    # Ajoute l'enregistrement de l'heure close au fichier de son mois
    def clotureHeure()
        import path
        import math
        import string
        var fichier = self.fichierMois(self.heureCourante * 3600)
        var enreg = bytes()
        enreg.add(self.heureCourante * 3600, 4)
        for i: 0 .. self.nbSeries - 1
            var n = self.nbH[i]
            enreg.addfloat(n > 0 ? self.minH[i] : math.nan)
            enreg.addfloat(n > 0 ? self.sommeH[i] / n : math.nan)
            enreg.addfloat(n > 0 ? self.maxH[i] : math.nan)
        end
        self.razHeure()

        var file
        try
            var nouveau = !path.exists(fichier)
            if (!nouveau && self.lisEntete(fichier) != self.series.concat(","))
                # Liste des series changee : l'ancien fichier du mois est mis de cote, lisible seul
                path.rename(fichier, string.format("%s-a.bin", fichier[0 .. size(fichier) - 5]))
                nouveau = true
                logFonctions.log(string.format("HISTORIQUE: Series de '%s' changees, %s mis de cote !", self.nom, fichier), LOG_LEVEL_INFO, self.nom)
            end
            file = open(fichier, "a")
            if (nouveau)    file.write(self.entete())    end
            file.write(enreg)
            file.close()
            if (nouveau)    self.purge()    end
        except .. as erreur, message
            if (file != nil)    file.close()    end
            logFonctions.log(string.format("HISTORIQUE_ERREUR: %s -> %s %s", fichier, erreur, message), LOG_LEVEL_ERREUR, self.nom)
        end
    end

    # Noms des series d'un fichier (texte de l'en-tete), nil si l'en-tete est illisible
    def lisEntete(fichier)
        var f = open(fichier, "r")
        var b = f.readbytes(7)
        var noms = nil
        if (size(b) == 7 && b[0 .. 3].asstring() == "HST1")    noms = f.readbytes(b.get(5, 2)).asstring()    end
        f.close()
        return noms
    end

    # Mois disponibles (suffixes 'AAAA-MM' ou 'AAAA-MM-a'), tries
    def mois()
        import path
        import string
        import historiqueFonctions
        var liste = []
        var prefixe = self.nom + "-"
        var fichiers = path.listdir(historiqueFonctions.DOSSIER)
        if (fichiers == nil)    return liste    end
        for f: fichiers
            if (string.startswith(f, prefixe) && string.endswith(f, ".bin") && size(f) >= size(prefixe) + 11)
                liste.push(f[size(prefixe) .. size(f) - 5])
            end
        end
        return historiqueFonctions.trie(liste)
    end

    # Supprime les mois plus anciens que 'moisConserves'
    def purge()
        import path
        import string
        import historiqueFonctions
        var d = tasmota.time_dump(tasmota.rtc()["utc"])
        if (d["year"] < 2023)    return    end      # heure non synchronisee : ne rien supprimer
        var limite = d["year"] * 12 + d["month"] - self.moisConserves
        for m: self.mois()
            if (int(m[0 .. 3]) * 12 + int(m[5 .. 6]) <= limite)
                path.remove(string.format("%s/%s-%s.bin", historiqueFonctions.DOSSIER, self.nom, m))
                logFonctions.log(string.format("HISTORIQUE: Mois %s de '%s' supprime (plus de %i mois) !", m, self.nom, self.moisConserves), LOG_LEVEL_INFO, self.nom)
            end
        end
    end

end
historiqueFonctions.HISTORIQUE = HISTORIQUE

# Driver de la route /histo, cree une fois par demarre() (au demarrage, avant le serveur web)
class HISTORIQUE_WEB : Driver
    def web_add_handler()
        import webserver
        import historiqueFonctions
        webserver.on("/histo", historiqueFonctions.page, webserver.HTTP_GET)
        # Graphiques (graphiquesFonctions.be) : module importe a la premiere requete seulement
        webserver.on("/graphiques", def () import graphiquesFonctions graphiquesFonctions.route() end, webserver.HTTP_GET)
    end
    def web_add_main_button()
        import webserver
        webserver.content_send("<p></p><form action='/graphiques' method='get'><button>Graphiques</button></form>")
    end
end
historiqueFonctions.HISTORIQUE_WEB = HISTORIQUE_WEB

# Valeur numerique d'une feuille du JSON : nombre, ou ON/OFF -> 1/0 ; nil sinon
def historiqueFonctions_nombre(v)
    if (type(v) == "int" || type(v) == "real")    return real(v)    end
    if (v == "ON")     return 1.0    end
    if (v == "OFF")    return 0.0    end
    return nil
end
historiqueFonctions.nombre = historiqueFonctions_nombre

# Valeur d'un chemin : 'DS18B20.Temperature' dans le JSON SENSOR, ou source speciale @power<n>, @rssi, @heap
def historiqueFonctions_lit(donnees, chemin)
    import string
    import historiqueFonctions
    if (string.startswith(chemin, "@"))
        if (chemin == "@rssi")    return historiqueFonctions.nombre(tasmota.wifi().find("rssi"))    end
        if (chemin == "@heap")    return real(tasmota.get_free_heap())    end
        if (string.startswith(chemin, "@power") && size(chemin) > 6)
            var etats = tasmota.get_power()
            var n = int(chemin[6 .. size(chemin) - 1]) - 1
            if (n >= 0 && n < size(etats))    return (etats[n] ? 1.0 : 0.0)    end
        end
        return nil
    end
    var v = donnees
    for cle: string.split(chemin, ".")
        if (!isinstance(v, map))    return nil    end
        v = v.find(cle)
    end
    return historiqueFonctions.nombre(v)
end
historiqueFonctions.lit = historiqueFonctions_lit

# Mode auto : chemins des feuilles numeriques (ou ON/OFF) du JSON SENSOR, dans la limite de 'max'
def historiqueFonctions_decouvre(donnees, prefixe, liste, max)
    import historiqueFonctions
    for cle: donnees.keys()
        if (size(liste) >= max)    break    end
        if (historiqueFonctions.IGNORES.find(cle) != nil)    continue    end
        var v = donnees[cle]
        var chemin = (prefixe == "" ? cle : prefixe + "." + cle)
        if (isinstance(v, map))
            historiqueFonctions.decouvre(v, chemin, liste, max)
        elif (historiqueFonctions.nombre(v) != nil)
            liste.push(chemin)
        end
    end
    return liste
end
historiqueFonctions.decouvre = historiqueFonctions_decouvre

# Tri par insertion d'une liste de chaines (quelques dizaines d'elements)
def historiqueFonctions_trie(liste)
    for i: 1 .. size(liste) - 1
        var x = liste[i]    var j = i - 1
        while (j >= 0 && liste[j] > x)    liste[j + 1] = liste[j]    j -= 1    end
        liste[j + 1] = x
    end
    return liste
end
historiqueFonctions.trie = historiqueFonctions_trie

# Un module enregistre une fonction(chemins, valeurs) qui peut remplacer une valeur par nil
def historiqueFonctions_ajouteFiltre(fonction)
    import historiqueFonctions
    historiqueFonctions.filtres.push(fonction)
end
historiqueFonctions.ajouteFiltre = historiqueFonctions_ajouteFiltre

# Demarrage (autoexec.be) : memorise la config, cree le driver web et la releve chaque minute
def historiqueFonctions_demarre(config)
    import historiqueFonctions
    if (config == nil || config.find("activation", "OFF") != "ON")    return    end
    historiqueFonctions.config = config
    tasmota.add_driver(historiqueFonctions.HISTORIQUE_WEB())
    tasmota.add_cron("*/60 * * * * *", historiqueFonctions.releve, "majHistorique")
    logFonctions.log("HISTORIQUE: Releve des mesures chaque minute activee !", LOG_LEVEL_DEBUG)
end
historiqueFonctions.demarre = historiqueFonctions_demarre

# Releve (chaque minute) : lit le JSON SENSOR, cree l'historique au premier passage utile, mesure
def historiqueFonctions_releve()
    import json
    import string
    import historiqueFonctions
    var config = historiqueFonctions.config
    try
        var texte = tasmota.read_sensors()
        var donnees = (texte != nil ? json.load(texte) : nil)
        if (!isinstance(donnees, map))    donnees = {}    end

        if (historiqueFonctions.chemins == nil)
            var noms = []
            var chemins = []
            var series = config.find("series", {})
            if (isinstance(series, map) && size(series) > 0)
                for nom: series.keys()    noms.push(nom)    end
                historiqueFonctions.trie(noms)
                for nom: noms    chemins.push(series[nom])    end
            else
                if (tasmota.millis() < 120000)    return    end     # mode auto : laisser les capteurs demarrer
                # Tout collecter, trier, PUIS tronquer : l'ordre d'une map n'est pas celui du JSON
                chemins = historiqueFonctions.trie(historiqueFonctions.decouvre(donnees, "", [], 64))
                var max = int(config.find("seriesMax", 12))
                if (size(chemins) > max)    chemins = chemins[0 .. max - 1]    end
                noms = chemins
                if (size(chemins) == 0)    return    end
            end
            historiqueFonctions.chemins = chemins
            historiqueFonctions.HISTORIQUE("mesures", noms, config)
            logFonctions.log(string.format("HISTORIQUE: Series enregistrees : %s !", json.dump(noms)), LOG_LEVEL_INFO)
        end

        var chemins = historiqueFonctions.chemins
        var valeurs = []
        for c: chemins    valeurs.push(historiqueFonctions.lit(donnees, c))    end
        for f: historiqueFonctions.filtres    f(chemins, valeurs)    end
        historiqueFonctions.instances["mesures"].mesure(valeurs)
    except .. as erreur, message
        logFonctions.log(string.format("HISTORIQUE_RELEVE_ERREUR: %s -> %s", erreur, message), LOG_LEVEL_ERREUR)
    end
end
historiqueFonctions.releve = historiqueFonctions_releve

# En-tete JSON commun : {"nom":..,"series":[..]
def historiqueFonctions_debutJson(h)
    import json
    import string
    return string.format("{\"nom\":%s,\"series\":%s", json.dump(h.nom), json.dump(h.series))
end
historiqueFonctions.debutJson = historiqueFonctions_debutJson

# Route /histo : n = nom de l'historique, p = liste | jour | mois, m = AAAA-MM[-a]
def historiqueFonctions_page()
    import webserver
    import json
    import string
    if (!webserver.check_privileged_access())    return nil    end

    var noms = historiqueFonctions.nomsInstances()
    var n = (webserver.has_arg("n") ? webserver.arg("n") : (size(noms) > 0 ? noms[0] : ""))
    var h = historiqueFonctions.instances.find(n)
    var p = (webserver.has_arg("p") ? webserver.arg("p") : "jour")
    if (h == nil)
        webserver.content_open(404, "application/json")
        webserver.content_send(string.format("{\"erreur\":\"historique inconnu\",\"noms\":%s}", json.dump(noms)))
        webserver.content_close()
        return
    end

    webserver.content_open(200, "application/json")
    webserver.content_send(historiqueFonctions.debutJson(h))

    if (p == "liste")
        webserver.content_send(string.format(",\"mois\":%s}", json.dump(h.mois())))
    elif (p == "mois")
        historiqueFonctions.envoieMois(h, webserver.has_arg("m") ? webserver.arg("m") : "")
    else
        var t0 = (h.dernierPas != nil ? (h.dernierPas - h.nbPoints + 1) * h.pas : nil)
        webserver.content_send(string.format(",\"pas\":%i,\"t0\":%s,\"valeurs\":[", h.pas, json.dump(t0)))
        for i: 0 .. h.nbSeries - 1
            var morceau = (i > 0 ? ",[" : "[")
            for k: 0 .. h.nbPoints - 1
                var idx = ((h.ramIndice + k) % h.nbPoints) * h.nbSeries + i
                morceau += (k > 0 ? "," : "") + historiqueFonctions.texte(h.ram.getfloat(idx * 4))
            end
            webserver.content_send(morceau + "]")
            tasmota.yield()
        end
        webserver.content_send("]}")
    end
    webserver.content_close()
end
historiqueFonctions.page = historiqueFonctions_page

# Envoie les lignes horaires d'un mois, par paquets de 24 (une journee) pour borner la RAM
def historiqueFonctions_envoieMois(h, m)
    import path
    import string
    import json
    import webserver
    # Validation de l'argument (frontiere systeme) : AAAA-MM ou AAAA-MM-a
    var valide = (size(m) == 7 || (size(m) == 9 && m[7] == "-")) && m[4] == "-"
    if (valide)
        for i: [0, 1, 2, 3, 5, 6]    if (m[i] < "0" || m[i] > "9")    valide = false    end    end
    end
    var fichier = string.format("%s/%s-%s.bin", historiqueFonctions.DOSSIER, h.nom, m)
    if (!valide || !path.exists(fichier))
        webserver.content_send(",\"lignes\":[]}")
        return
    end

    var f = open(fichier, "r")
    var b = f.readbytes(7)
    if (size(b) < 7 || b[0 .. 3].asstring() != "HST1")
        f.close()
        webserver.content_send(",\"lignes\":[],\"erreur\":\"en-tete illisible\"}")
        return
    end
    var nb = b[4]
    var noms = f.readbytes(b.get(5, 2)).asstring()
    var taille = 4 + nb * 12
    webserver.content_send(string.format(",\"seriesFichier\":%s,\"lignes\":[", json.dump(string.split(noms, ","))))

    var premiere = true
    while (true)
        var paquet = f.readbytes(taille * 24)
        var n = (paquet != nil ? size(paquet) / taille : 0)
        if (n == 0)    break    end
        var morceau = ""
        for r: 0 .. n - 1
            var o = r * taille
            morceau += (premiere ? "[" : ",[") + str(paquet.get(o, 4))
            premiere = false
            for k: 0 .. nb * 3 - 1    morceau += "," + historiqueFonctions.texte(paquet.getfloat(o + 4 + k * 4))    end
            morceau += "]"
        end
        webserver.content_send(morceau)
        tasmota.yield()
    end
    f.close()
    webserver.content_send("]}")
end
historiqueFonctions.envoieMois = historiqueFonctions_envoieMois

# Retourne le module lors de l'importation
return historiqueFonctions
