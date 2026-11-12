# Bouchon de configDevices pour banc_pompe_cave.be : ne branche aucune regle, note seulement l'etat des
# capteurs de la pompe AU MOMENT ou l'init branche les regles (les capteurs doivent alors etre reactives)
# et pose les compteurs que l'init relit pour son journal.
var configDevices = module("configDevices")
configDevices.activationAuBranchement = nil
configDevices.configDevicesByRules = def (m, nb)
    if configDevices.activationAuBranchement == nil
        var c = m.find("pompeVideCave", {}).find("environnement", {}).find("capteurs", {})
        configDevices.activationAuBranchement = c.find("capteur1", {}).find("activation", "?") + "/" + c.find("capteur2", {}).find("activation", "?")
    end
    for g: ["relais", "WS2812", "switchs", "capteurs", "boutons", "analogiques", "thermometres", "compteurs"]
        nb[g] = {"actives": {"nb": 1}, "reels": {"nb": 1}}
    end
end
return configDevices
