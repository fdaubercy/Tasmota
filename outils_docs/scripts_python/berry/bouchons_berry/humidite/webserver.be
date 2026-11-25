# Bouchon du module natif 'webserver' pour banc_humidite.be : arguments de la requete dans webserver.args (map), HTML envoye
# dans 'envoye', 'termine' = content_stop() atteint (une page interrompue par une exception ne l'appelle jamais).
var webserver = module("webserver")
webserver.HTTP_GET = 1
webserver.HTTP_POST = 2
webserver.BUTTON_CONFIGURATION = 1
webserver.args = {}
webserver.envoye = []
webserver.termine = false
webserver.routes = []
webserver.on = def (url, f, m) webserver.routes.push([url, m]) end
webserver.check_privileged_access = def () return true end
webserver.has_arg = def (n) return webserver.args.contains(n) end
webserver.arg = def (n) return webserver.args.find(n, "") end
webserver.content_start = def (t) webserver.envoye = [] webserver.termine = false end
webserver.content_send_style = def () end
webserver.content_send = def (h) webserver.envoye.push(h) end
webserver.content_button = def (b) end
webserver.content_stop = def () webserver.termine = true end
return webserver
