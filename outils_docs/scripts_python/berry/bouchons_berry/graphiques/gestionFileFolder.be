# Bouchon de gestionFileFolder pour banc_graphiques.be : readFileByLineAndContentSend() lit le VRAI
# fichier sous 'racine' (data, par defaut) et l'envoie au bouchon webserver.
var gestionFileFolder = module("gestionFileFolder")
gestionFileFolder.racine = "data"
gestionFileFolder.readFileByLineAndContentSend = def (chemin)
    import webserver
    var f = open(gestionFileFolder.racine + chemin, "r")
    webserver.content_send(f.read())
    f.close()
end
return gestionFileFolder
