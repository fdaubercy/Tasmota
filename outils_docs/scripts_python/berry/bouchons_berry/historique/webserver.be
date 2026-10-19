# Bouchon du module natif Tasmota 'webserver' pour banc_historique.be (copie de celui de bouchons_berry/graphiques :
# ce dossier-la contient aussi un bouchon de historiqueFonctions, qui masquerait le vrai module).
# Ecrit tout ce qui est envoye dans le fichier 'sortie' ouvert par le banc en "wb".
var webserver = module("webserver")
webserver.HTTP_GET = 1
webserver.BUTTON_MAIN = 0
webserver.sortie = nil          # fichier ouvert par le banc
webserver.code = nil            # code et type de content_open
webserver.mime = nil
webserver.envois = 0
webserver.ferme = false         # content_close appele
webserver.debut = nil           # titre de content_start
webserver.bouton = nil          # bouton de content_button
webserver.termine = false       # content_stop appele
webserver.args = {}
webserver.privilegie = true
webserver.raz = def (args)
    webserver.code = nil webserver.mime = nil webserver.envois = 0 webserver.ferme = false
    webserver.debut = nil webserver.bouton = nil webserver.termine = false
    webserver.args = (args != nil ? args : {})
end
webserver.check_privileged_access = def () return webserver.privilegie end
webserver.has_arg = def (n) return webserver.args.contains(n) end
webserver.arg = def (n) return webserver.args[n] end
webserver.content_open = def (c, t) webserver.code = c webserver.mime = t end
webserver.content_send = def (x) webserver.envois += 1 webserver.sortie.write(x) end
webserver.content_close = def () webserver.ferme = true end
webserver.content_start = def (titre) webserver.debut = titre webserver.sortie.write("<!doctype html><html><head><meta charset='utf-8'><title>" + titre + "</title>") end
webserver.content_send_style = def () webserver.sortie.write("<style>:root{--c_txt:#eaeaea;--c_bg:#252525}body{background:var(--c_bg);color:var(--c_txt);font-family:verdana}</style></head><body><div style='text-align:left;display:inline-block;min-width:340px'>") end
webserver.content_button = def (b) webserver.bouton = b webserver.sortie.write("<form action='/' method='get'><button>Menu principal</button></form>") end
webserver.content_stop = def () webserver.termine = true webserver.sortie.write("</div></body></html>") end
return webserver
