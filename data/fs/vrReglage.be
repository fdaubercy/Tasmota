#- *********************************************************************************************
 * vrReglage.be - Mode reglage des durees tempsMontee / tempsDescente d'un volet (2026-11-11)
 *
 * Fichier de fonctions SANS driver : appele par le driver des volets (CONTROLE_VR de controleVoletRoulants.be,
 * button_pressed) et par les routes de la page de reglage (vrPages.be). Spec :
 * docs/superpowers/specs/2026-11-11-visuel-volets-reglage-durees-design.md, section 5 ; plan
 * tasks/plans/visuel-reglage-volets.md, A3.
 *
 * Deroule : le volet est en bas ; debut(id) ; un appui -> le volet monte, chronometre ; un appui en haut -> arret,
 * tempsMontee retenu ; un appui -> il descend ; un appui en bas -> arret, tempsDescente retenu, ecriture dans le persist
 * de la carte, durees et boutons normaux remis (vrFonctions.configVRByJson), position recalee, sortie du mode.
 * Etapes : pret -> montee -> haut -> descente -> fini ; sorties sans rien ecrire : annule (bouton Annuler, ou arret que
 * le reglage n'a pas demande), delai (120 s sans appui), refus (mesure de moins de 2 s).
 * Le sens est IMPOSE PAR L'ETAPE, jamais par la fonction du bouton (toggle, up, down) : tout appui sur un bouton du
 * volet vaut « etape suivante ». Un appui moins de 1 s apres le precedent accepte est ignore (rebond, page et bouton
 * presque ensemble).
 *
 * Decisions (plan, section Contexte) :
 * - Suspension des boutons : ShutterButton<id> 0, puis renvoi des ShutterButton des AUTRES volets actifs. Bogue de
 *   xdrv_27_esp32_shutter.ino::CmndShutterButton : la boucle de « ShutterButton<x> 0 » n'a pas d'accolades, la remise a
 *   zero de shutter_number et des positions s'applique au bouton d'index i du compteur de jetons (0), donc a Button1,
 *   quel que soit son volet ; le renvoi des autres volets repare Button1 s'il n'est pas a ce volet. Un bouton retire
 *   n'est plus servi par le driver des volets : Berry le recoit par button_pressed (bouton()). Remise a la sortie :
 *   vrFonctions.configVRByJson() entier (durees du persist et boutons de tous les volets).
 * - Course allongee a COURSE_MAX s (ShutterOpenDuration / ShutterCloseDuration) pour que Tasmota n'arrete pas le moteur
 *   avant la vraie butee ; chaque etape a DELAI_MS pour recevoir l'appui suivant.
 * - Sens physique : tout ordre de course ou de recalage passe par vrFonctions.commandeSens (Tasmota inverse un ordre
 *   Berry quand ShutterInvert vaut 1).
 * - Durees ecrites en secondes entieres arrondies (configVRByJson les pose avec le type int).
 * - Refus de commencer : reglage deja actif, volet inconnu ou inactif, volet qui roule (Direction lue dans le JSON des
 *   capteurs, tasmota.read_sensors), volet arrete depuis moins de ShutterMotorStop + 100 ms (moteur). JAMAIS par ShutterPosition<id> sans argument : xdrv_27_esp32_shutter.ino::
 *   CmndShutterPosition garde target_position et relance le moteur si la cible differe de la position reelle.
 * - Fins de course et MPU6050 : vrFonctions.enReglage(id) neutralise le recalage et l'arret en butee ; le blocage et le
 *   sens inverse coupent toujours le moteur. Un arret que le reglage n'a pas demande (regle Shutter<id>#Direction 0,
 *   posee le temps du mode) l'arrete sans rien ecrire, cause « bloque », « sens inverse » ou « arret ». Un Direction 0
 *   ne compte qu'apres un Direction non nul de la MEME course (un 0 rapporte avant le vrai depart est ignore).
 * - Porte de garage (mode 3, type chrono) : aucun ordre au volet, ni suspension de bouton, ni course allongee, ni
 *   regle ; seuls les clics de la page (appui(id, "page")) font avancer ; configVRByJson apres l'ecriture seulement.
 *
 * L'etat vit dans vrFonctions.etat()["reglage"] (RAM : un redemarrage le perd sans rien ecrire). SOLIDIFIE sur les
 * envs a facade : aucun etat dans le module (sa table est en lecture seule, piege 12 de SOLIDIFICATION_BERRY.md).
********************************************************************************************* -#

#@ solidify:vrReglage
var vrReglage = module("vrReglage")

vrReglage.DELAI_MS = 120000             # attente maximale de l'appui suivant, a chaque etape
vrReglage.COURSE_MAX = 130              # course autorisee pendant la mesure (s) : au-dela du delai, Tasmota ne coupe pas avant lui
vrReglage.MESURE_MIN_MS = 2000          # mesure plus courte : refusee
vrReglage.REBOND_MS = 1000              # appui plus proche du precedent : ignore
# Texte de chaque etape en cours : [moteur, chrono] ; %i = duree de la montee
vrReglage.MESSAGES = {
    "pret": ["Prêt : un appui fait monter le volet.", "Prêt : lancez la porte, puis cliquez « Départ »."],
    "montee": ["Montée : un appui à l'arrivée en haut arrête le volet.", "Montée : cliquez « Arrivée » quand la porte est en haut."],
    "haut": ["En haut après %i s : un appui fait descendre le volet.", "En haut après %i s : lancez la porte, puis cliquez « Départ »."],
    "descente": ["Descente : un appui à l'arrivée en bas arrête le volet.", "Descente : cliquez « Arrivée » quand la porte est en bas."]
}

# Etat du mode (map), nil si aucun reglage n'a eu lieu depuis le demarrage
def vrReglage_etat()
    import vrFonctions
    return vrFonctions.etat().find("reglage")
end
vrReglage.etat = vrReglage_etat

# (Re)arme le delai de l'etape : le vrai set_timer ajoute sans dedoublonner, d'ou le remove_timer
def vrReglage_arme()
    import vrReglage
    tasmota.remove_timer("vrReglage_delai")
    tasmota.set_timer(vrReglage.DELAI_MS, vrReglage.delai, "vrReglage_delai")
end
vrReglage.arme = vrReglage_arme

def vrReglage_delai()
    import vrReglage
    vrReglage.annule("delai")
end
vrReglage.delai = vrReglage_delai

# Sortie du mode : delai et regle retires ; durees et boutons remis (moteur, ou chrono apres l'ecriture)
def vrReglage_sortie(etape, message, cause)
    import string
    import vrFonctions
    var r = vrFonctions.etat()["reglage"]
    r["actif"] = false
    r["etape"] = etape
    r["message"] = message
    r["cause"] = cause
    tasmota.remove_timer("vrReglage_delai")
    if (r["type"] == "moteur")
        tasmota.remove_rule(string.format("Shutter%i#Direction", r["id"]), "vrReglage_Direction")
    end
    if (r["type"] == "moteur" || etape == "fini")    vrFonctions.configVRByJson()    end
end
vrReglage.sortie = vrReglage_sortie

# Commence le reglage du volet 'id' : [true, message] ou [false, raison du refus]
def vrReglage_debut(id)
    import json
    import string
    import vrFonctions
    import vrReglage
    var r = vrReglage.etat()
    if (r != nil && r["actif"])    return [false, string.format("Un réglage est déjà en cours (volet %i).", r["id"])]    end
    var vr = vrFonctions.trouveVolet(id)
    if (vr == nil || vr.find("activation", "OFF") != "ON")    return [false, string.format("Volet %s inconnu ou inactif.", str(id))]    end
    var chrono = drivers["voletRoulants"].find("mode") == 3
    # Direction sans effet de bord : JSON des capteurs (FUNC_JSON_APPEND du Shutter) ; absent ou illisible -> pas de refus
    var capteurs = json.load(str(tasmota.read_sensors()))
    var position = isinstance(capteurs, map) ? capteurs.find("Shutter" + str(id)) : nil
    if (!isinstance(position, map))
        vrFonctions.log(string.format("VR_REGLAGE: Volet %i absent du JSON des capteurs : direction non verifiee !", id), LOG_LEVEL_DEBUG)
    elif (position.find("Direction", 0) != 0)
        return [false, "Le volet roule : attendez qu'il soit arrêté en bas."]
    end
    # ShutterSetClose juste apres un arret : ShutterWaitForMotorStart reentrerait dans loop() (meme calcul que commandeArret)
    var arret = vrFonctions.suiviInclinaison(id).find("arret")
    if (!chrono && arret != nil)
        var ms = tasmota.cmd("ShutterMotorStop", boolMute)
        if (tasmota.millis() - arret < (isinstance(ms, map) ? ms.find("ShutterMotorStop", 500) : 500) + 100)
            return [false, "Le volet vient de s'arrêter : réessayez dans une seconde"]
        end
    end

    var vrs = drivers["voletRoulants"]["environnement"]["VRs"]
    var cle = ""
    for k: vrs.keys()    if (vrs[k] == vr)    cle = k    end    end
    var boutons = []
    if (!chrono)
        for b: vr.find("boutons", {})
            if (b.find("activation", "OFF") == "ON" && b.find("id", -1) != -1)    boutons.push(b["id"])    end
        end
    end
    r = {"actif": true, "id": id, "cle": cle, "nom": vr.find("nom", cle), "type": chrono ? "chrono" : "moteur", "etape": "pret",
         "mesures": {}, "avant": {"tempsMontee": vr.find("tempsMontee"), "tempsDescente": vr.find("tempsDescente")},
         "boutons": boutons, "cause": nil, "message": vrReglage.MESSAGES["pret"][chrono ? 1 : 0],
         "t0": nil, "dernier": nil, "monArret": false, "parti": false}
    vrFonctions.etat()["reglage"] = r
    vrFonctions.suiviInclinaison(id).remove("durees")          # durees du MPU6050 : celles de CE reglage seulement
    try
        if (!chrono)
            tasmota.cmd(string.format("ShutterOpenDuration%i %i", id, vrReglage.COURSE_MAX), boolMute)
            tasmota.cmd(string.format("ShutterCloseDuration%i %i", id, vrReglage.COURSE_MAX), boolMute)
            tasmota.cmd(string.format("ShutterButton%i 0", id), boolMute)        # touche aussi Button1 (bogue, en-tete)
            for v: vrs
                if (type(v) == "instance" && v != vr && v.find("activation", "OFF") == "ON")    vrFonctions.configBoutons(v)    end
            end
            tasmota.cmd(vrFonctions.commandeSens(id, "posFerme"), boolMute)
            tasmota.add_rule(string.format("Shutter%i#Direction", id), vrReglage.direction, "vrReglage_Direction")
        end
        vrReglage.arme()
    except .. as erreur, message
        vrFonctions.log(string.format("VR_REGLAGE_ERREUR: Volet %i : %s -> %s", id, erreur, message), LOG_LEVEL_ERREUR)
        vrReglage.sortie("annule", "Réglage interrompu par une erreur : rien n'a été écrit.", nil)
        return [false, r["message"]]
    end
    vrFonctions.log(string.format("VR_REGLAGE: Volet %i (%s) : debut du reglage des durees (%s) !", id, cle, r["type"]), LOG_LEVEL_INFO)
    return [true, r["message"]]
end
vrReglage.debut = vrReglage_debut

# Etape suivante du volet 'id' (source "bouton" ou "page") : [true, message] ou [false, raison]
def vrReglage_appui(id, source)
    import string
    import persist
    import vrFonctions
    import vrReglage
    var r = vrReglage.etat()
    if (r == nil || !r["actif"] || r["id"] != id)    return [false, "Aucun réglage en cours pour ce volet."]    end
    var moteur = r["type"] == "moteur"
    if (!moteur && source != "page")    return [false, "Porte de garage : utilisez « Départ » et « Arrivée » sur la page."]    end
    var maintenant = tasmota.millis()
    if (r["dernier"] != nil && maintenant - r["dernier"] < vrReglage.REBOND_MS)
        vrFonctions.log(string.format("VR_REGLAGE: Volet %i, appui %s ignore (rebond) !", id, source), LOG_LEVEL_DEBUG)
        return [false, "Appui ignoré : moins d'une seconde après le précédent."]
    end
    r["dernier"] = maintenant
    var etape = r["etape"]

    if (etape == "pret" || etape == "haut")                  # depart d'une course
        r["monArret"] = false
        r["parti"] = false                                   # Direction non nul pas encore vu pour cette course
        r["t0"] = maintenant
        r["etape"] = etape == "pret" ? "montee" : "descente"
        if (moteur)
            # recalage differe encore en attente : parti en pleine course, il remettrait 'direction' a 0
            tasmota.remove_timer("vr" + vrFonctions.commandeSens(id, "posOuvert"))
            tasmota.remove_timer("vr" + vrFonctions.commandeSens(id, "posFerme"))
            tasmota.cmd(vrFonctions.commandeSens(id, etape == "pret" ? "ouvre" : "ferme"), boolMute)
        end
        r["message"] = vrReglage.MESSAGES[r["etape"]][moteur ? 0 : 1]
    else                                                     # arrivee : montee -> haut, descente -> fini
        var ms = maintenant - r["t0"]
        if (moteur)
            r["monArret"] = true                             # la regle Direction 0 qui suit vient de NOTRE arret
            tasmota.cmd(string.format("ShutterStop%i", id), boolMute)
            vrFonctions.suiviInclinaison(id)["arret"] = tasmota.millis()   # recalage differe (commandeArret)
        end
        if (ms < vrReglage.MESURE_MIN_MS)
            vrFonctions.log(string.format("VR_REGLAGE: Volet %i, mesure de %i ms refusee : rien d'ecrit !", id, ms), LOG_LEVEL_INFO)
            vrReglage.sortie("refus", "Mesure de moins de 2 s refusée : rien n'a été écrit.", nil)
            return [false, r["message"]]
        end
        var duree = int(ms / 1000.0 + 0.5)
        if (etape == "montee")
            r["mesures"]["tempsMontee"] = duree
            r["etape"] = "haut"
            if (moteur)    vrFonctions.commandeArret(id, vrFonctions.commandeSens(id, "posOuvert"))    end
            r["message"] = string.format(vrReglage.MESSAGES["haut"][moteur ? 0 : 1], duree)
        else
            r["mesures"]["tempsDescente"] = duree
            var vr = vrFonctions.trouveVolet(id)
            vr["tempsMontee"] = r["mesures"]["tempsMontee"]
            vr["tempsDescente"] = duree
            persist.drivers = drivers
            persist.save(true)
            try                                              # persist ecrit : la sortie "fini" doit suivre quoi qu'il arrive
                if (moteur)    vrFonctions.commandeArret(id, vrFonctions.commandeSens(id, "posFerme"))    end
                vrFonctions.log(string.format("VR_REGLAGE: Volet %i : tempsMontee %i s, tempsDescente %i s ecrits dans le persist !", id, vr["tempsMontee"], duree), LOG_LEVEL_INFO)
            except .. as erreur, message
                vrFonctions.log(string.format("VR_REGLAGE_ERREUR: Volet %i, recalage apres l'ecriture : %s -> %s", id, erreur, message), LOG_LEVEL_ERREUR)
            end
            vrReglage.sortie("fini", string.format("Durées écrites dans le persist de la carte : montée %i s, descente %i s.", vr["tempsMontee"], duree), nil)
            return [true, r["message"]]
        end
    end
    vrReglage.arme()
    vrFonctions.log(string.format("VR_REGLAGE: Volet %i, appui %s : %s !", id, source, r["etape"]), LOG_LEVEL_INFO)
    return [true, r["message"]]
end
vrReglage.appui = vrReglage_appui

# Annule le reglage en cours (motif "annule" ou "delai") : moteur arrete s'il tourne, rien d'ecrit
def vrReglage_annule(motif)
    import string
    import vrFonctions
    import vrReglage
    var r = vrReglage.etat()
    if (r == nil || !r["actif"])    return    end
    if (r["type"] == "moteur" && (r["etape"] == "montee" || r["etape"] == "descente"))
        r["monArret"] = true
        tasmota.cmd(string.format("ShutterStop%i", r["id"]), boolMute)
    end
    var delai = motif == "delai"
    vrFonctions.log(string.format("VR_REGLAGE: Volet %i, reglage %s en %s : rien d'ecrit !", r["id"], delai ? "sans appui depuis 120 s" : "annule", r["etape"]),
                    delai ? LOG_LEVEL_ERREUR : LOG_LEVEL_INFO)
    vrReglage.sortie(delai ? "delai" : "annule", !delai ? "Réglage annulé : rien n'a été écrit." :
                     (r["type"] == "moteur" ? "Pas d'appui depuis 120 s : volet arrêté, rien n'a été écrit." : "Pas d'appui depuis 120 s : rien n'a été écrit."), nil)
end
vrReglage.annule = vrReglage_annule

# Regle Shutter<id>#Direction, posee le temps du mode (moteur) : un arret que le reglage n'a pas demande l'arrete
def vrReglage_direction(value, trigger, msg)
    import string
    import vrFonctions
    import vrReglage
    var r = vrReglage.etat()
    if (r == nil || !r["actif"] || (r["etape"] != "montee" && r["etape"] != "descente"))    return    end
    if (isinstance(value, map))    for cle: value.keys()    value = value[cle]    break    end    end     # comme changementDirection
    if (value == nil)    return    end
    if (int(value) != 0)    r["parti"] = true    return    end
    if (r["monArret"] || !r["parti"])    return    end       # notre arret, ou 0 rapporte avant le vrai depart
    var suivi = vrFonctions.suiviInclinaison(r["id"])
    var cause = suivi.find("bloque", false) ? (suivi.find("cause") == "sens inverse" ? "sens inverse" : "bloque") : "arret"
    vrFonctions.log(string.format("VR_REGLAGE: Volet %i arrete en %s sans appui (%s) : reglage abandonne, rien d'ecrit !", r["id"], r["etape"], cause), LOG_LEVEL_ERREUR)
    vrReglage.sortie("annule", string.format("Le volet s'est arrêté sans appui (%s) : rien n'a été écrit.", cause), cause)
end
vrReglage.direction = vrReglage_direction

# Appel de button_pressed (idx = multipress<<24 | etat<<16 | ancien etat<<8 | index base 0, PRESSED = 0) :
# vrai si le bouton est au volet en reglage (appui, relache, maintien), l'appui fait avancer d'une etape
def vrReglage_bouton(idx)
    import vrReglage
    var r = vrReglage.etat()
    if (r == nil || !r["actif"] || r["boutons"].find((idx & 0xFF) + 1) == nil)    return false    end
    if (((idx >> 16) & 0xFF) == 0 && ((idx >> 8) & 0xFF) == 1)    vrReglage.appui(r["id"], "bouton")    end
    return true
end
vrReglage.bouton = vrReglage_bouton

# Etat lu par la page de reglage (route ?f=etat)
def vrReglage_etatPage()
    import vrFonctions
    import vrReglage
    var r = vrReglage.etat()
    if (r == nil)    return {"actif": false, "etape": nil}    end
    var e = {}
    for k: ["actif", "id", "cle", "nom", "type", "etape", "mesures", "avant", "boutons", "cause", "message"]    e[k] = r.find(k)    end
    e["chrono_ms"] = (r["actif"] && (r["etape"] == "montee" || r["etape"] == "descente")) ? tasmota.millis() - r["t0"] : 0
    var d = vrFonctions.suiviInclinaison(r["id"]).find("durees")
    e["mpu"] = (d != nil && size(d) > 0) ? {"tempsMontee": d.find("ouverture"), "tempsDescente": d.find("fermeture")} : nil
    return e
end
vrReglage.etatPage = vrReglage_etatPage

# Retourne le module lors de l'importation
return vrReglage
