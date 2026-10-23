# Bouchon du module natif 'webserver' pour banc_boot.be : au demarrage, les modules ne font que DECLARER
# leurs routes (on) ; elles sont gardees dans 'routes' (route -> fonction). Le reste ne fait rien.
var webserver = module("webserver")
webserver.HTTP_GET = 1
webserver.HTTP_POST = 2
webserver.HTTP_ANY = 0
webserver.HTTP_OPTIONS = 3
webserver.BUTTON_MAIN = 0
webserver.BUTTON_CONFIGURATION = 1
webserver.BUTTON_INFORMATION = 2
webserver.BUTTON_MANAGEMENT = 3
webserver.BUTTON_MODULE = 4
webserver.routes = {}
webserver.on = def (route, f, methode) webserver.routes[route] = f end
webserver.member = def (n) return def (*a) return nil end end
return webserver
