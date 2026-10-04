#- =====================================================================================
   TEST DE LIAISON MODBUS RTU (RS485) ENTRE UN MAITRE ET UN ESCLAVE
   A charger sur les DEUX modules, puis piloter par les commandes ci-dessous.
   Rien n'est persiste ; seul ce fichier est depose sur le systeme de fichiers.

   /!\ NE PAS COLLER ce fichier dans la console Berry : elle envoie le code par une
   requete GET, que le serveur web de l'ESP32 refuse au-dela de 2048 octets d'URL
   (WEBSERVER_MAX_URI_LEN, reponse 414) ; la page ignore l'echec SANS rien afficher,
   et 'mbt' reste ensuite "undeclared". Faire plutot :
     1. Outils > Gestion du systeme de fichiers > televerser test_liaison_modbus.be
     2. console Berry :  tasmota.load("/test_liaison_modbus.be")
     3. apres les tests, supprimer le fichier depuis la meme page

   Ce que fait l'outil 'mbt' :
     - ecoute le bus et affiche chaque trame recue : octets en hexa, CRC OK/KO,
       decodage des champs (adresse, fonction, registre, quantite, valeurs) ;
     - emet une trame brute (CRC ajoute automatiquement s'il manque) ;
     - cote esclave, peut repondre lui-meme aux requetes qui lui sont adressees
       (echo pour 0x05/0x06, valeurs de test pour 0x01-0x04), sans le framework ;
     - cote maitre, envoie par le pont Tasmota (ModbusSend) et affiche ModbusReceived.

   ---- ESCLAVE (cuve id 2 / rideau id 3) -------------------------------------------
     mbt.prendrePort()      emprunte le port serie ouvert par le framework : celui-ci
                            ne lit plus rien pendant le test (ses envois passent encore)
     mbt.auto(true)         repond aux requetes adressees a cet id (false = ecoute seule)
     mbt.envoi("02 03 02 12 34")      emet une trame (CRC ajoute) -> visible cote maitre
                                      en mode brut seulement (le pont ignore le spontane)
     mbt.rendrePort()       FIN DU TEST : rend le port au framework

   ---- MAITRE (P4 id 0) : 2 facons ---------------------------------------------------
   A) Par le pont Tasmota (chemin de production, n'abime rien) :
     mbt.pont('{"DeviceAddress":2,"FunctionCode":3,"StartAddress":1,"type":"uint16","Count":2}')
     mbt.pont('{"DeviceAddress":2,"FunctionCode":6,"StartAddress":1,"type":"uint8","Count":1,"Values":[1,0]}')
     -> affiche la TRAME ATTENDUE (recalculee en Berry : le pont C++ ne montre pas ses
        octets) puis, a reception, le ModbusReceived. Verite terrain : '<-- RECU' esclave.
     mbt.finPont()          retire la regle d'affichage
   B) En brut (voir les octets exacts, y compris les envois spontanes 0x80|fc) :
     mbt.ouvrirPort()       /!\ prend les GPIO du pont ModBr : le pont ne peut plus
                            EMETTRE jusqu'au redemarrage -> finir par 'Restart 1'
     mbt.envoi("02 03 00 01 00 02")   requete lecture 2 registres a l'esclave 2
     mbt.fermerPort()

   ---- COMMUN -------------------------------------------------------------------------
     mbt.etat()             parametres, port, compteurs
     mbt.envoi("01 06 00 01 01 00 00 00", true)   emet SANS toucher au CRC (test CRC KO)
     mbt.arret()            arrete l'ecoute (equivaut a rendrePort/fermerPort)

   Scenario conseille : esclave -> prendrePort() + auto(true) ; maitre -> pont(...).
   L'esclave affiche la requete exacte emise par le pont, le maitre la reponse decodee.
   Si le maitre voit "Error 11" (timeout) alors que l'esclave a affiche la requete
   avec CRC OK, la liaison maitre->esclave est bonne : chercher cote retour (TX esclave,
   A/B inverses au retour, debit). Si l'esclave n'affiche RIEN : cablage A/B, masse,
   debit/parite, ou GPIO.
   ===================================================================================== -#

# Faux port laisse au framework de l'esclave pendant le test : il ne lit rien
# (les octets restent pour mbt), mais ses emissions partent sur le vrai port.
class MBT_PORT_FANTOME
    var vrai, outil
    def init(vrai, outil)    self.vrai = vrai    self.outil = outil    end
    def available()    return 0    end
    def read()    return bytes()    end
    def flush()    end
    def write(b)
        self.outil.affiche(b, "--> ENVOI (framework)")
        return self.vrai.write(b)
    end
end

class MBT_TEST : Driver
    var port            # objet serial utilise par le test
    var portOrigine     # esclave : vrai port du framework, a rendre
    var portPropre      # true si le port a ete ouvert par mbt (donc a fermer par mbt)
    var tampon          # octets recus, en attente d'un silence de fin de trame
    var tEnvoi          # millis() du dernier envoi (latence de la reponse)
    var id              # adresse ModBus de ce module (reponses automatiques)
    var repondre        # esclave : true = repond aux requetes adressees a self.id
    var nbRx, nbTx, nbKO
    var actif

    def init()
        self.tampon = bytes()
        self.tEnvoi = 0
        self.repondre = false
        self.portPropre = false
        self.actif = false
        self.nbRx = 0    self.nbTx = 0    self.nbKO = 0
        self.id = self.config()["id"]
    end

    # Parametres lus dans le persist (lecture seule), avec des defauts surs
    def config()
        import global
        var mb = (global.drivers != nil) ? global.drivers.find("ModBus", {}) : {}
        var pins = mb.find("environnement", {}).find("pinsModBus", {})
        return {"rx": pins.find("RX", {}).find("pin", 4), "tx": pins.find("TX", {}).find("pin", 5),
                "debit": mb.find("debit", 19200), "mode": mb.find("mode", "8N1"), "id": mb.find("id", 0)}
    end

    # ------------------------------------------------------------------ trames
    def crc(b)
        var c = 0xFFFF
        for i: 0 .. size(b) - 1
            c ^= b[i]
            for j: 0 .. 7
                if (c & 1)    c = (c >> 1) ^ 0xA001    else    c = c >> 1    end
            end
        end
        return c
    end

    def avecCRC(b)
        var t = bytes() + b
        t.add(self.crc(b), 2)           # CRC ModBus : octet de poids faible en premier
        return t
    end

    def crcOK(t)
        var n = size(t)
        return n >= 4 && self.crc(t[0 .. n - 3]) == t.get(n - 2, 2)
    end

    def hex(b)
        import string
        var s = ""
        for i: 0 .. size(b) - 1    s += string.format("%02X ", b[i])    end
        return s
    end

    # Un bloc lu peut contenir plusieurs trames collees (requete + reponse d'un autre
    # noeud) : on coupe au plus court prefixe dont le CRC tombe juste. Le reste sans
    # CRC valide est rendu tel quel, pour etre affiche en KO.
    def decoupe(b)
        var trames = []
        var pos = 0
        var n = size(b)
        while pos < n
            var l = 4
            var trouve = 0
            while pos + l <= n
                if self.crcOK(b[pos .. pos + l - 1])    trouve = l    break    end
                l += 1
            end
            if trouve == 0    trames.push(b[pos .. n - 1])    break    end
            trames.push(b[pos .. pos + trouve - 1])
            pos += trouve
        end
        return trames
    end

    # Decodage lisible des champs d'une trame (CRC deja controle par l'appelant)
    def explique(t)
        import string
        var n = size(t)
        if n < 4    return "trame trop courte"    end
        var noms = {1: "Lecture coils", 2: "Lecture entrees discretes", 3: "Lecture holding registers",
                    4: "Lecture input registers", 5: "Ecriture 1 coil", 6: "Ecriture 1 registre",
                    15: "Ecriture N coils", 16: "Ecriture N registres", 17: "Report Slave ID"}
        var fc = t[1]
        var f = fc & 0x7F
        var s = string.format("esclave %d | fc 0x%02X %s", t[0], fc, noms.find(f, "?"))
        if (fc & 0x80)
            if n == 5    return s + string.format(" | EXCEPTION code %d (ou envoi spontane court)", t[2])    end
            s += " | bit 0x80 = envoi SPONTANE esclave (protocole maison)"
        end
        if f >= 1 && f <= 4
            if n == 8
                s += string.format(" | REQUETE depart 0x%04X (%d), quantite %d", t.get(2, -2), t.get(2, -2), t.get(4, -2))
            else
                s += string.format(" | REPONSE %d octet(s) : %s", t[2], self.hex(t[3 .. n - 3]))
                if f >= 3 && t[2] >= 2
                    var regs = []
                    for i: 0 .. t[2] / 2 - 1    regs.push(t.get(3 + 2 * i, -2))    end
                    s += "= registres " + str(regs)
                end
            end
        elif f == 5 || f == 6
            s += string.format(" | adresse 0x%04X (%d) valeur 0x%04X (%d) [requete ou echo]", t.get(2, -2), t.get(2, -2), t.get(4, -2), t.get(4, -2))
        elif f == 15 || f == 16
            s += string.format(" | depart 0x%04X quantite %d", t.get(2, -2), t.get(4, -2))
            if n > 8    s += string.format(" | REQUETE %d octet(s) : %s", t[6], self.hex(t[7 .. n - 3]))
            else    s += " | REPONSE (accuse)"
            end
        else
            s += " | donnees : " + self.hex(t[2 .. n - 3])
        end
        return s
    end

    def affiche(t, sens)
        import string
        var ok = self.crcOK(t)
        if !ok && sens[0] == "<"    self.nbKO += 1    end
        var lat = ""
        if sens[0] == "<" && self.tEnvoi > 0
            lat = string.format(" (+%d ms apres le dernier envoi)", tasmota.millis() - self.tEnvoi)
        end
        print(string.format("MBT: %s %d octet(s) : %s [CRC %s]%s", sens, size(t), self.hex(t), ok ? "OK" : "KO", lat))
        if ok    print("MBT:      " + self.explique(t))
        elif size(t) >= 2
            print(string.format("MBT:      CRC attendu %04X (octets %02X %02X) -> trame tronquee, debit/parite faux, ou parasite",
                                self.crc(t[0 .. size(t) - 3]), self.crc(t[0 .. size(t) - 3]) & 0xFF, self.crc(t[0 .. size(t) - 3]) >> 8))
        end
    end

    # ------------------------------------------------------------------ esclave : reponse de test
    def repondA(t)
        if !self.crcOK(t) || t[0] != self.id || self.id == 0    return    end
        var n = size(t)
        var f = t[1]
        var r = bytes()
        r.add(t[0], 1)    r.add(f, 1)
        if f >= 1 && f <= 4 && n == 8
            var debut = t.get(2, -2)
            var qte = t.get(4, -2)
            if f <= 2
                var nb = (qte + 7) / 8
                r.add(nb, 1)
                for i: 0 .. nb - 1    r.add(0x55, 1)    end                 # motif 01010101
            else
                r.add(2 * qte, 1)
                for i: 0 .. qte - 1    r.add((debut + i) & 0xFFFF, -2)    end   # registre k vaut k
            end
        elif f == 5 || f == 6
            r = t[0 .. n - 3]                                               # echo
        elif (f == 15 || f == 16) && n > 8
            r = t[0 .. 5]                                                   # accuse depart + quantite
        else
            r = bytes()    r.add(t[0], 1)    r.add(f | 0x80, 1)    r.add(1, 1)  # exception 1 : fonction illegale
        end
        self.ecrit(self.avecCRC(r), "--> REPONSE AUTO")
    end

    # ------------------------------------------------------------------ boucle d'ecoute
    def every_50ms()
        if self.port == nil    return    end
        try
            if self.port.available() > 0
                self.tampon += self.port.read()
                if size(self.tampon) > 256    self.vide()    end           # bus bruite : borne la RAM
            elif size(self.tampon) > 0                                    # 50 ms de silence = fin de bloc
                self.vide()
            end
        except .. as e, m
            print("MBT_ERREUR: ecoute arretee -> " + str(e) + " : " + str(m))
            self.arret()
        end
    end

    def vide()
        var bloc = self.tampon
        self.tampon = bytes()
        for t: self.decoupe(bloc)
            self.nbRx += 1
            self.affiche(t, "<-- RECU")
            if self.repondre    self.repondA(t)    end
            tasmota.yield()
        end
    end

    def ecrit(b, sens)
        self.port.write(b)
        self.tEnvoi = tasmota.millis()
        self.nbTx += 1
        self.affiche(b, sens)
    end

    def demarre()
        if !self.actif    tasmota.add_driver(self)    self.actif = true    end
        self.etat()
    end

    # ------------------------------------------------------------------ commandes
    def prendrePort()
        import global
        var e = global._etatModbusFonctions
        if e == nil || e.find("serialModBus") == nil
            print("MBT: aucun port serie ouvert par le framework (maitre, ou Serial OFF) -> mbt.ouvrirPort()")
            return
        end
        if !isinstance(e["serialModBus"], MBT_PORT_FANTOME)
            self.portOrigine = e["serialModBus"]
            e["serialModBus"] = MBT_PORT_FANTOME(self.portOrigine, self)
        end
        self.port = self.portOrigine
        self.portPropre = false
        print("MBT: port emprunte au framework (il ne lit plus le bus jusqu'a mbt.rendrePort())")
        self.demarre()
    end

    def rendrePort()
        import global
        var e = global._etatModbusFonctions
        if e != nil && self.portOrigine != nil
            e["serialModBus"] = self.portOrigine
            print("MBT: port rendu au framework")
        end
        self.portOrigine = nil
        self.arret()
    end

    def ouvrirPort()
        import global
        import introspect
        var e = global._etatModbusFonctions
        if e != nil && e.find("serialModBus") != nil && !isinstance(e["serialModBus"], MBT_PORT_FANTOME)
            print("MBT: le framework tient deja ce port -> utiliser mbt.prendrePort()")
            return
        end
        var c = self.config()
        if self.port == nil
            self.port = serial(c["rx"], c["tx"], c["debit"], introspect.get(serial, "SERIAL_" + c["mode"]))
            self.portPropre = true
        end
        if c["id"] == 0
            print("MBT: /!\\ maitre : le pont ModBr ne peut plus emettre -> 'Restart 1' apres le test")
        end
        self.demarre()
    end

    def fermerPort()    self.arret()    end

    def arret()
        if self.portOrigine != nil    self.rendrePort()    return    end
        if self.port != nil && self.portPropre    self.port.close()    end
        self.port = nil
        self.portPropre = false
        self.tampon = bytes()
        if self.actif    tasmota.remove_driver(self)    self.actif = false    end
        print("MBT: ecoute arretee")
    end

    def auto(oui)
        self.repondre = (oui == true)
        print("MBT: reponse automatique " + (self.repondre ? "ACTIVE pour l'adresse " + str(self.id) : "coupee"))
    end

    # trame : bytes, ou texte hexa ("01 06 00 01 01 00", espaces permis)
    # brut  : true = envoyer exactement, sans ajouter de CRC
    def envoi(trame, brut)
        import string
        if self.port == nil    print("MBT: pas de port -> prendrePort() (esclave) ou ouvrirPort()")    return    end
        var b = trame
        if type(trame) == "string"    b = bytes(string.replace(string.replace(trame, " ", ""), "0x", ""))    end
        if brut != true && !self.crcOK(b)    b = self.avecCRC(b)    end
        self.ecrit(b, "--> ENVOI")
    end

    # ------------------------------------------------------------------ trame recalculee du pont
    # Copie de CmndModbusBridgeSend (xdrv_63_modbus_bridge.ino:883-1147) + TasmotaModbus::Send
    # (TasmotaModbus.cpp:92-185), bizarreries comprises (/15 en bit, [k/2] en int8, malloc non
    # initialise). Trame ATTENDUE, pas observee. Retourne [trame ou nil, remarque ou nil].
    def mot(wd, i, v)    if i < size(wd)    wd[i] = v & 0xFFFF    end    end
    def ajoute(wd, i, v)    if i < size(wd) && wd[i] != nil    wd[i] = (wd[i] + v) & 0xFFFF    end    end
    def swap(x)    return ((x >> 8) | (x << 8)) & 0xFFFF    end
    def s8(v)    var b = v & 0xFF    return b > 127 ? b - 256 : b    end

    def tramePont(texte)
        import json
        import string
        # Le pont accepte 0x01 dans son JSON (exemples de MODBUS.md), json.load non : -> decimal
        var s = ""    var i = 0    var n = size(texte)
        while i < n
            if texte[i] == "0" && i + 2 < n && string.tolower(texte[i + 1]) == "x" && string.find("0123456789abcdefABCDEF", texte[i + 2]) >= 0
                var j = i + 2
                while j < n && string.find("0123456789abcdefABCDEF", texte[j]) >= 0    j += 1    end
                s += str(int("0x" + texte[i + 2 .. j - 1]))
                i = j
            else    s += texte[i]    i += 1
            end
        end
        var brut = json.load(s)
        if !isinstance(brut, map)    return [nil, "JSON illisible par Berry : recalcul impossible"]    end
        var p = {}
        for k: brut.keys()    p[string.tolower(k)] = brut[k]    end       # cles insensibles a la casse, comme le pont

        var adr = int(p.find("deviceaddress", 0)) & 0xFF
        var fc = int(p.find("functioncode", 0)) & 0xFF
        var debut = int(p.find("startaddress", 0)) & 0xFFFF
        var typ = p.find("type", "uint8")
        var nb = int(p.find("count", 1)) & 0xFFFF
        var vals = p.find("values")
        var liste = isinstance(vals, list)
        var nbv = liste ? size(vals) & 0xFF : 0
        var bit = (fc == 1 || fc == 2 || fc == 15)
        var lsb = bit
        if p.find("endian") == "msb"    lsb = false    elif p.find("endian") == "lsb"    lsb = true    end

        # Comme en C, chaque controle ecrase le code precedent : seul le dernier compte
        var err = 0
        if adr == 0    err = 2    end
        if fc == 0 || (fc > 6 && fc != 15 && fc != 16)    err = 3    end
        var dc = 0
        var demi = ((nb - 1) / 2) + 1
        if typ == "int8" || typ == "uint8" || typ == "raw" || typ == "hex"    dc = bit ? nb : demi
        elif typ == "int16" || typ == "uint16" || typ == ""    dc = nb
        elif typ == "int32" || typ == "uint32" || typ == "float"    dc = bit ? nb : 2 * nb
        elif typ == "bit"    dc = bit ? nb : ((nb - 1) / 16) + 1
        else    err = 5
        end
        if (!bit && dc > 64) || (bit && dc > 512)    err = 7    end
        if fc == 15
            var f = {"bit": 1, "uint8": 8, "int8": 8, "raw": 8, "hex": 8, "uint16": 16, "int16": 16, "uint32": 32, "int32": 32}.find(typ)
            if f != nil && nb > nbv * f    err = 7    end
        elif (fc == 5 || fc == 6) && nb != 1    err = 7
        elif fc == 16 && nb != nbv    err = 7
        end

        var wd = nil                    # mots de 16 bits a ecrire ; nil = non initialise (malloc)
        if err == 0 && liste
            if dc > 40    err = 8
            else
                wd = []    wd.resize(dc)
                for k: 0 .. nbv - 1
                    if err != 0    break    end
                    var v = int(vals[k])
                    if typ == "bit"
                        if k % 16 == 0    self.mot(wd, k / 15, 0)    end
                        var bp = (k % 16) + 8
                        if bp > 15    bp -= 16    end
                        self.ajoute(wd, k / 16, (v == 1 ? 1 : 0) << bp)
                    elif typ == "int8"
                        if k % 2    self.ajoute(wd, k / 2, self.s8(v))    else    self.mot(wd, k / 2, self.s8(int(vals[k / 2])) << 8)    end
                        if dc != nbv / 2    err = 7    end
                    elif typ == "uint8" || typ == "raw" || typ == "hex"
                        if k % 2    self.ajoute(wd, k / 2, v & 0xFF)    else    self.mot(wd, k / 2, (v & 0xFF) << 8)    end
                        if dc != nbv / 2    err = 7    end
                    elif typ == "int16" || typ == "uint16"
                        self.mot(wd, k, lsb ? self.swap(v & 0xFFFF) : v)
                    elif typ == "int32" || typ == "uint32"
                        self.mot(wd, 2 * k, lsb ? (v >> 16) : self.swap(v & 0xFFFF))
                        self.mot(wd, 2 * k + 1, lsb ? v : self.swap((v >> 16) & 0xFFFF))
                    else    err = 5                                   # float en ecriture : 'TODO' dans le pont
                    end
                end
                if fc == 5 && dc > 0 && wd[0] != nil    wd[0] = wd[0] ? 0xFF00 : 0x0000    end
            end
        end
        var raisons = {2: "adresse esclave 0", 3: "code fonction refuse", 5: "type inconnu (ou float en ecriture)",
                       7: "Count incoherent avec type/Values", 8: "plus de 40 mots a ecrire"}
        if err != 0    return [nil, string.format("le pont refuse (MBR Send Error %d : %s), RIEN n'est emis", err, raisons.find(err, "?"))]    end

        # TasmotaModbus::Send
        if fc == 5 || fc == 6    dc = 1    end
        var nbo = bit ? ((dc - 1) / 8) + 1 : dc * 2
        var t = bytes()
        t.add(adr, 1)    t.add(fc, 1)    t.add(debut, -2)
        var inconnu = false
        if fc < 5
            t.add(dc & 0xFFFF, -2)
        elif wd == nil
            return [nil, "Values absent : le pont n'emet rien (erreur 13)"]
        elif fc == 5 || fc == 6
            if size(wd) == 0 || wd[0] == nil    inconnu = true    t.add(0, -2)    else    t.add(wd[0], -2)    end
        else
            if dc == 0    return [nil, "Count 0 : le pont n'emet rien (erreur 12)"]    end
            t.add(dc & 0xFFFF, -2)    t.add(nbo & 0xFF, 1)
            for b: 0 .. nbo - 1
                var w = (b / 2 < size(wd)) ? wd[b / 2] : nil
                if w == nil    inconnu = true    w = 0    end
                t.add(b % 2 ? w & 0xFF : (w >> 8) & 0xFF, 1)
            end
        end
        return [self.avecCRC(t), inconnu ? "contient des octets NON INITIALISES par le pont (valeur aleatoire, affiches 00)" : nil]
    end

    # Maitre : envoi par le pont Tasmota, reponse affichee par une regle temporaire
    def pont(jsonModbusSend)
        import json
        var calcul = self.tramePont(jsonModbusSend)
        tasmota.remove_rule("ModbusReceived", "mbt_pont")
        tasmota.add_rule("ModbusReceived", def (valeur, declencheur, msg)
            import string
            print(string.format("MBT: <-- PONT (+%d ms) %s", tasmota.millis() - self.tEnvoi, json.dump(msg)))
        end, "mbt_pont")
        self.tEnvoi = tasmota.millis()
        print("MBT: --> PONT ModbusSend " + jsonModbusSend)
        if calcul[0] != nil    self.affiche(calcul[0], "--> TRAME ATTENDUE (recalculee)")    end
        if calcul[1] != nil    print("MBT:      /!\\ " + calcul[1])    end
        print("MBT:     reponse immediate : " + json.dump(tasmota.cmd("ModbusSend " + jsonModbusSend, true)))
    end

    def finPont()    tasmota.remove_rule("ModbusReceived", "mbt_pont")    print("MBT: regle pont retiree")    end

    def etat()
        import string
        var c = self.config()
        print(string.format("MBT: id %d | RX GPIO%d TX GPIO%d | %d bauds %s | port %s%s | reponse auto %s | recues %d (KO %d) emises %d",
              c["id"], c["rx"], c["tx"], c["debit"], c["mode"],
              self.port == nil ? "ferme" : (self.portOrigine != nil ? "emprunte au framework" : "ouvert par mbt"),
              self.actif ? ", ecoute ON" : "", self.repondre ? "ON" : "OFF", self.nbRx, self.nbKO, self.nbTx))
    end
end

# Un second collage remplace proprement le premier (ancien port rendu, ancien driver retire)
import global
if global.mbt != nil    global.mbt.arret()    end
global.mbt = MBT_TEST()
global.mbt.etat()
