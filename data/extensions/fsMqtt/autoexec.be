# Extension sans .be embarque : le module est solidifie dans le firmware, l'extension ne fait que le charger.
# Differe apres /autoexec.be : le prologue de demarrage.be pose LOG_LEVEL_* et le persist dont logFonctions a besoin.
do
  tasmota.set_timer(1000, def ()
    import global                 # LOG_LEVEL_* lus a l execution : a la compilation, avant /autoexec.be, ces noms n existent pas
    import logFonctions
    try
      import fsMqtt
      logFonctions.log("EXT_FSMQTT: module charge par l'extension !", global.LOG_LEVEL_INFO)
    except .. as e, m
      logFonctions.log(f"EXT_FSMQTT_ERREUR: chargement impossible : {e} - {m} !", global.LOG_LEVEL_ERREUR)
    end
  end)
end
