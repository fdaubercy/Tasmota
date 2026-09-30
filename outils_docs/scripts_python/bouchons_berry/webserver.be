# Bouchon du module natif Tasmota 'webserver' pour test_discovery.be.
# Memorise le HTML envoye ('envoye') et si la page a ete terminee ('termine') :
# une page interrompue par une exception n'appelle jamais content_stop().
var webserver = module("webserver")
webserver.envoye = []
webserver.termine = false
webserver.HTTP_GET = 1
webserver.header = def (nom) return nom == "Host" ? "192.168.0.43" : nil end
webserver.content_start = def (titre) end
webserver.content_send_style = def (style) end
webserver.content_send = def (html) webserver.envoye.push(html) end
webserver.content_stop = def () webserver.termine = true end
return webserver
