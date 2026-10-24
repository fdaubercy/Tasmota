# Bouchon de gestionFileFolder pour banc_cuve.be : la page web de la cuve (controleCuve.web_sensor)
# passe ses variables de remplacement a readFileByLineReplaceAndWebSend ; le banc les relit dans
# 'envois' (liste de [chemin, variables]). Les autres lectures/ecritures ne font rien.
var gestionFileFolder = module("gestionFileFolder")
gestionFileFolder.envois = []
gestionFileFolder.readFileByLineAndContentSend = def (chemin, x, cible) end
gestionFileFolder.readFileByLineReplaceAndWebSend = def (chemin, variables, cible)
    gestionFileFolder.envois.push([chemin, variables])
end
gestionFileFolder.compteIndiceMaxFileLogs = def (f) return 0 end
gestionFileFolder.enregistreLogs = def (f, ctrl, data) end
return gestionFileFolder
