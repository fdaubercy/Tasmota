#- TAILLE DU BINOME (genere par outils_docs/scripts_python/berry/mesure_binomes.py --ecrire, ne pas editer)
   fichier                                .be      .bec  solidifie
   controleHue.be                      9,7 Ko    5,0 Ko     3,9 Ko
   hueFonctions.be                     8,1 Ko    4,5 Ko     3,6 Ko
   total                              17,8 Ko    9,6 Ko     7,5 Ko  + 162 chaines
   .be : LittleFS si non solidifie (hors ce bloc). .bec : LittleFS, et ordre de grandeur de la RAM du code charge
   (berry.exe du PC). solidifie : partition app (objet xtensa -Os), pas de RAM pour le code ; chaines dans la
   table globale du firmware, en partie partagees. RAM reelle : tasmota.gc() sur une carte.
FIN TAILLE DU BINOME -#
# Driver de l'emulation Hue (Alexa) : publie le pont Berry global.hue_bridge, que le firmware appelle AVANT son code natif
# (xdrv_52_3_berry_hue.ino : be_hue_discovery, be_hue_status, be_hue_command, be_hue_groups ; xdrv_20_hue.ino::HueLights).
# Charge SANS garde d'activation par l'autoexec : a OFF, il remet Emulation a 0 et publie un pont vide qui refuse tout.
# A ON : FriendlyName1 a 8 prefixes de « $ » (relais natifs caches de la decouverte, HueActive), puis Emulation 2.
# CmndEmulation redemarre la carte a CHAQUE envoi, meme sans changement : comparaison d'abord (configGlobal.testeParam).
# FAILLE AMONT COUVERTE : en natif, PUT /api/x/lights/<n>/state commande n'importe quel POWER, masque ou non. Le firmware
# appelle cmd() d'abord et tient toute chaine rendue pour « traite » : cmd() et full_status() rendent donc une chaine pour
# TOUT id (erreur Hue hors liste blanche), jamais nil, et ne levent jamais (un pcall en erreur rendrait la main au natif).
# Commande d'un relais par tasmota.set_power : les relais virtuels (ModBus, MQTT, TCA9554) suivent par
# controleGeneral.set_power_handler, rien n'est duplique ici.
# Solidifiable : aucun import ni appel tasmota au niveau fichier ; etat dans l'instance (piege 12), return final (piege 13).
#@ solidify:controleHue
var controleHue = module("controleHue")

class CONTROLE_HUE
    static ERREUR_INTERNE = "[{\"error\":{\"type\":901,\"address\":\"/\",\"description\":\"Internal Error\"}}]"
    var liste             # sorties exposees [{"n", "nom", "cle"}] : la liste blanche
    var mac               # MAC lue a la derniere requete ; par_id est calcule pour elle
    var par_id            # id Hue -> sortie, pour cette MAC
    var macKo             # MAC illisible deja signalee (une ligne de log par panne)

    def init(liste)
        self.liste = liste
        self.macKo = false
        self.mac = nil
        self.par_id = {}
    end

    # MAC lue A CHAQUE requete, comme le natif (EncodeLightIdZigbee) : sur le P4, celle du C6 peut etre nulle au demarrage
    # (Status 5, banc_boot). Table id -> sortie recalculee si la MAC change ; nil si elle est illisible ou nulle.
    def table()
        import hueFonctions
        var w = tasmota.wifi()
        var mac = isinstance(w, map) ? str(w.find("mac", "")) : ""
        if hueFonctions.idHue(1, mac) == nil || mac == "00:00:00:00:00:00"
            # une seule ligne par panne (un Alexa qui interroge souvent ne doit pas inonder le syslog)
            if !self.macKo    hueFonctions.log("CONTROLE_HUE_ERREUR: MAC illisible (" + mac + "), aucun appareil expose !", LOG_LEVEL_ERREUR)    end
            self.macKo = true
            return nil
        end
        self.macKo = false
        if mac != self.mac
            self.par_id = {}
            for a: self.liste
                var id = hueFonctions.idHue(a["n"], mac)
                if id != nil    self.par_id[id] = a    end
            end
            self.mac = mac
        end
        return self.par_id
    end

    # Echo de 1re generation (SetOption109) : bri impose dans l'etat
    def gen1()
        return tasmota.get_option(109) == 1
    end

    def allume(p, n)
        return n <= size(p) ? p[n - 1] == true : false
    end

    # /api/x/lights : fragments "id":{fiche} separes par des virgules, nil si aucun appareil
    def discover()
        import hueFonctions
        try
            var t = self.table()
            if t == nil    return nil    end
            var p = tasmota.get_power()
            var g = self.gen1()
            var f = []
            for id: t.keys()
                var a = t[id]
                f.push("\"" + str(id) + "\":" + hueFonctions.fiche(a["n"], a["nom"], self.allume(p, a["n"]), self.mac, g))
            end
            return size(f) > 0 ? f.concat(",") : nil
        except .. as e, m
            hueFonctions.log("CONTROLE_HUE_ERREUR: decouverte : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
            return nil
        end
    end

    # /api/x/lights/<id> : fiche de l'appareil, erreur Hue hors liste blanche (jamais l'etat d'un relais masque)
    def full_status(id)
        import hueFonctions
        try
            var t = self.table()
            if t == nil    return self.ERREUR_INTERNE    end
            var a = t.find(id)
            if a == nil    return hueFonctions.erreur(id, 3, "resource, /lights/" + str(id) + ", not available")    end
            return hueFonctions.fiche(a["n"], a["nom"], self.allume(tasmota.get_power(), a["n"]), self.mac, self.gen1())
        except .. as e, m
            hueFonctions.log("CONTROLE_HUE_ERREUR: etat de " + str(id) + " : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
            return self.ERREUR_INTERNE
        end
    end

    # PUT /api/x/lights/<id>/state : seul "on" est traite (type onoff). Toujours une chaine.
    def cmd(id, arg)
        try
            import hueFonctions
            import logFonctions
            if logFonctions.actif(LOG_LEVEL_DEBUG_PLUS, "emulationHue")
                hueFonctions.log("CONTROLE_HUE: commande recue pour " + str(id) + " : " + str(arg) + " !", LOG_LEVEL_DEBUG_PLUS)
            end
            var t = self.table()
            if t == nil    return self.ERREUR_INTERNE    end
            var a = t.find(id)
            if a == nil
                hueFonctions.log("CONTROLE_HUE_ERREUR: commande refusee pour l'id " + str(id) + ", hors liste blanche !", LOG_LEVEL_ERREUR)
                return hueFonctions.erreur(id, 3, "resource, /lights/" + str(id) + ", not available")
            end
            var on = hueFonctions.lit(arg)
            if on == nil
                hueFonctions.log("CONTROLE_HUE_ERREUR: commande refusee pour " + a["nom"] + ", corps sans booleen on !", LOG_LEVEL_ERREUR)
                return hueFonctions.erreur(id, 6, "parameter, on, not available")
            end
            # set_power rend nil (sans exception) pour un index >= devices_present : rien n'a commute, Alexa ne doit pas entendre « fait »
            if tasmota.set_power(a["n"] - 1, on) == nil
                hueFonctions.log("CONTROLE_HUE_ERREUR: relais " + str(a["n"]) + " (" + a["nom"] + ") hors des canaux de la carte, rien n'a commute !", LOG_LEVEL_ERREUR)
                return self.ERREUR_INTERNE
            end
            hueFonctions.log("CONTROLE_HUE: " + a["nom"] + " (relais " + str(a["n"]) + ") -> " + (on ? "ON" : "OFF") + " par Alexa !", LOG_LEVEL_INFO)
            return hueFonctions.succes(id, on)
        except .. as e, m
            # un import rate ou un log qui leve ne doit jamais rendre la main au natif (il commuterait n'importe quel relais)
            try
                import hueFonctions as hf
                hf.log("CONTROLE_HUE_ERREUR: commande " + str(id) + " : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
            except ..
            end
            return self.ERREUR_INTERNE
        end
    end

    # Groupe 0 : xdrv_20_hue.ino::HueGroups y liste deja tous les relais 1 a 32 par la formule native, nos ids compris ;
    # rendre nil n'y ajoute rien (une chaine les doublerait)
    def groups()
        return nil
    end
end

controleHue.CONTROLE_HUE = CONTROLE_HUE

# Regle le firmware : ON -> FriendlyName1 a 8 masques (« $ ») PUIS Emulation 2 ; OFF -> Emulation 0. Rien n'est envoye si la
# valeur est deja la bonne (Emulation redemarre la carte). Masquage non verifie -> Emulation 0 : les relais natifs
# seraient listes. Une commande inconnue (firmware sans Hue) est journalisee, sans exception.
def controleHue_regle(actif)
    import configGlobal
    import hueFonctions
    try
        var cible = 0
        if actif
            var r = tasmota.cmd("FriendlyName", boolMute)
            for i: 1 .. 8
                var nom = isinstance(r, map) ? r.find("FriendlyName" + str(i)) : nil
                if type(nom) == "string" && (size(nom) == 0 || nom[0] != "$")
                    tasmota.cmd("FriendlyName" + str(i) + " $" + nom, boolMute)
                end
            end
            r = tasmota.cmd("FriendlyName", boolMute)
            var masques = 0
            for i: 1 .. 8
                var nom = isinstance(r, map) ? r.find("FriendlyName" + str(i)) : nil
                if type(nom) == "string" && size(nom) > 0 && nom[0] == "$"    masques += 1    end
            end
            if masques == 8
                cible = 2
            else
                hueFonctions.log("CONTROLE_HUE_ERREUR: FriendlyName non masques (" + str(masques) + "/8), emulation Hue laissee a l'arret !", LOG_LEVEL_ERREUR)
            end
        end
        if configGlobal.testeParam("Emulation", cible, "int")
            hueFonctions.log("CONTROLE_HUE: Emulation " + str(cible) + " posee, la carte redemarre !", LOG_LEVEL_INFO)
        end
    except .. as e, m
        hueFonctions.log("CONTROLE_HUE_ERREUR: reglage de l'emulation : " + str(e) + " " + str(m) + " !", LOG_LEVEL_ERREUR)
    end
end
controleHue.regle = controleHue_regle

# init() : APPELEE AUTOMATIQUEMENT par 'import controleHue'. Le pont est publie AVANT de regler le firmware : une requete
# arrivee pendant le redemarrage demande est deja filtree. Activation OFF ou persist invalide : pont vide.
def controleHue_init(m)
    import global
    import persist
    import hueFonctions
    var s = persist.find("serveur", {})
    var b = isinstance(s, map) ? s.find("emulationHue") : nil
    var actif = isinstance(b, map) && b.find("activation", "OFF") == "ON"
    var liste = actif ? hueFonctions.appareils(persist.find("modules", {}), persist.find("drivers", {})) : []
    var inst = m.CONTROLE_HUE(liste)
    global.hue_bridge = inst
    if actif    hueFonctions.log("CONTROLE_HUE: " + str(size(liste)) + " appareil(s) expose(s) a Alexa !", LOG_LEVEL_INFO)    end
    m.regle(actif)
    return m
end
controleHue.init = controleHue_init

# Rend le module a son import depuis le LittleFS (carte au firmware sans module solidifie, piege 13)
return controleHue
