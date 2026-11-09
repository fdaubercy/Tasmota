# Extension sans .be embarque : le module est solidifie dans le firmware, l'extension ne fait que le charger.
# Differe apres /autoexec.be : le prologue de demarrage.be pose LOG_LEVEL_* et le persist dont logFonctions a besoin.
# add_extension : /ext affiche « Running » ; « Stop » appelle unload(), qui coupe la reception (le module reste en flash).
do
  class EXT_FSMQTT
    def unload()
      import global
      import mqtt
      tasmota.remove_timer("ext_fsmqtt")      # Stop dans la premiere seconde : le recepteur ne doit pas renaitre
      var r = global.contains("fsMqttRecepteur") ? global.fsMqttRecepteur : nil
      if r == nil    return    end
      if r.lecture != nil    r.lecture["f"].close()    r.lecture = nil    end   # lecture en cours : fichier ferme
      r.abandonne()                           # envoi en cours : /fsmqtt.tmp efface
      mqtt.unsubscribe(r.base + "ordre")
      mqtt.unsubscribe(r.base + "morceau")
      tasmota.remove_rule("Mqtt#Connected", "fsmqtt_pret")
      tasmota.remove_timer("fsmqtt_lit")
      global.fsMqttRecepteur = nil
    end
  end
  tasmota.add_extension(EXT_FSMQTT())   # chemin = tasmota.wd, valide pendant ce chargement seulement

  tasmota.set_timer(1000, def ()
    import global                 # LOG_LEVEL_* lus a l execution : a la compilation, avant /autoexec.be, ces noms n existent pas
    import logFonctions
    try
      import fsMqtt
      # relance apres « Stop » : 'import' ne rappelle pas init() (module en cache), le recepteur est recree ici
      if !global.contains("fsMqttRecepteur") || global.fsMqttRecepteur == nil    fsMqtt.init(fsMqtt)    end
      logFonctions.log("EXT_FSMQTT: module charge par l'extension !", global.LOG_LEVEL_INFO)
    except .. as e, m
      logFonctions.log(f"EXT_FSMQTT_ERREUR: chargement impossible : {e} - {m} !", global.LOG_LEVEL_ERREUR)
    end
  end, "ext_fsmqtt")
end
