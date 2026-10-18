# Bouchon de data/fs/webFonctions.be pour banc_graphiques.be : controleWeb.init() en importe la regle
# de demarrage, web_add_main_button() ses logs. Rien d'autre n'est appele par le bouton Grafana.
var webFonctions = module("webFonctions")
webFonctions.changementEtatDemarrage = def (value, trigger, msg) end
webFonctions.log = def (msg, niveau) end
return webFonctions
