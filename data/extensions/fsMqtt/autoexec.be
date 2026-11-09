# Extension sans .be embarque : le module est solidifie dans le firmware, l'extension ne fait que le charger.
# Differe apres /autoexec.be : le prologue de demarrage.be pose LOG_LEVEL_* et le persist dont logFonctions a besoin.
# add_extension : /ext affiche « Running » ; « Stop » et « Uninstall » appellent unload(), qui coupe la reception
# SEULEMENT si l'extension l'a lancee : celle de l'autoexec de la carte n'est jamais touchee (le module reste en flash).
do
  class EXT_FSMQTT
    var proprietaire                          # vrai si le recepteur a ete cree par l'extension
    def unload()
      import global
      import mqtt
      tasmota.remove_timer("ext_fsmqtt")      # Stop dans la premiere seconde : le recepteur ne doit pas renaitre
      var r = global.contains("fsMqttRecepteur") ? global.fsMqttRecepteur : nil
      if r == nil || !self.proprietaire    return    end
      if r.lecture != nil    r.lecture["f"].close()    r.lecture = nil    end   # lecture en cours : fichier ferme
      r.abandonne()                           # envoi en cours : /fsmqtt.tmp efface
      mqtt.unsubscribe(r.base + "ordre")
      mqtt.unsubscribe(r.base + "morceau")
      tasmota.remove_rule("Mqtt#Connected", "fsmqtt_pret")
      tasmota.remove_timer("fsmqtt_lit")
      global.fsMqttRecepteur = nil
      self.proprietaire = false
    end
  end
  var ext = EXT_FSMQTT()
  tasmota.add_extension(ext)                  # chemin = tasmota.wd, valide pendant ce chargement seulement

  tasmota.set_timer(1000, def ()
    import global                 # LOG_LEVEL_* lus a l execution : a la compilation, avant /autoexec.be, ces noms n existent pas
    import logFonctions
    try
      var deja = global.contains("fsMqttRecepteur") && global.fsMqttRecepteur != nil   # lance par l'autoexec
      ext.proprietaire = !deja                # avant init : un recepteur a moitie cree reste coupe par unload()
      import fsMqtt
      # relance apres « Stop » : 'import' ne rappelle pas init() (module en cache), le recepteur est recree ici
      if !global.contains("fsMqttRecepteur") || global.fsMqttRecepteur == nil    fsMqtt.init(fsMqtt)    end
      logFonctions.log(deja ? "EXT_FSMQTT: reception deja lancee par l'autoexec, l'extension n'y touchera pas !"
                            : "EXT_FSMQTT: module charge par l'extension !", global.LOG_LEVEL_INFO)
    except .. as e, m
      logFonctions.log(f"EXT_FSMQTT_ERREUR: chargement impossible : {e} - {m} !", global.LOG_LEVEL_ERREUR)
    end
  end, "ext_fsmqtt")
end
