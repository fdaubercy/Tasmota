# Bouchon du module natif Tasmota 'webserver' pour banc_reglage_volets.be (groupe « routes » de vrPages.be).
# Tout ce qui est envoye s'accumule dans 'envoye' (liste) ; 'code' et 'mime' viennent de content_open ; 'ferme' =
# content_close appele ; 'termine' = content_stop appele ; 'routes' = [chemin, fonction, methode] declares par on().
var webserver = module("webserver")
webserver.HTTP_GET = 1
webserver.HTTP_POST = 2
webserver.BUTTON_MAIN = 0
webserver.args = {}
webserver.privilegie = true
webserver.routes = []
webserver.envoye = []
webserver.code = nil
webserver.mime = nil
webserver.ferme = false
webserver.termine = false
webserver.raz = def (args)
    webserver.args = (args != nil ? args : {})
    webserver.envoye = [] webserver.code = nil webserver.mime = nil webserver.ferme = false webserver.termine = false
end
webserver.texte = def ()
    var t = ""
    for x: webserver.envoye    t += x    end
    return t
end
webserver.on = def (chemin, f, methode) webserver.routes.push([chemin, f, methode]) end
webserver.check_privileged_access = def () return webserver.privilegie end
webserver.has_arg = def (n) return webserver.args.contains(n) end
webserver.arg = def (n) return webserver.args[n] end
webserver.content_open = def (c, t) webserver.code = c webserver.mime = t end
webserver.content_send = def (x) webserver.envoye.push(x) end
webserver.content_close = def () webserver.ferme = true end
webserver.content_start = def (titre) webserver.envoye.push("[start " + titre + "]") end
webserver.content_send_style = def () webserver.envoye.push("[style]") end
webserver.content_button = def (b) webserver.envoye.push("[bouton]") end
webserver.content_stop = def () webserver.termine = true end
return webserver
