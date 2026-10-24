# Bouchon de ledsFonctions pour banc_test_modbus.be (section 29) : enregistre les appels de
# modbusFonctions (actionRubanMaitre, modeRuban). Dossier a part, ajoute au chemin par ce seul
# banc : banc_leds.be doit charger le VRAI data/fs/ledsFonctions.be, et berry.exe cherche les
# modules du dernier chemin ajoute au premier (un bouchon de bouchons_berry/ le masquerait).
var ledsFonctions = module("ledsFonctions")
ledsFonctions.appels = []
ledsFonctions.manuel = false
ledsFonctions.reste = 30
ledsFonctions.estManuel = def () return ledsFonctions.manuel end
ledsFonctions.resteMinutes = def () return ledsFonctions.reste end
ledsFonctions.passeManuel = def (source) ledsFonctions.appels.push("manuel:" + str(source)) ledsFonctions.manuel = true end
ledsFonctions.retourAuto = def (source) ledsFonctions.appels.push("auto:" + str(source)) ledsFonctions.manuel = false end
ledsFonctions.couleurSuivante = def () ledsFonctions.appels.push("suivante") end
ledsFonctions.recente = nil             # animation rendue par animationRecente (nil = perimee) - P5.3
ledsFonctions.animationRecente = def () return ledsFonctions.recente end
return ledsFonctions
