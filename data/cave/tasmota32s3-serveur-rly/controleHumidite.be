# Thermo-hygrometre de la cave (AM2301) : affichage de la page d'accueil (tuiles + bande des bornes d'humidite) a la place
# des lignes par defaut de Tasmota, et page /humidite pour deplacer les bornes. SOLIDIFIABLE, sur le modele de controleEnergie :
# la classe est portee par le module 'controleHumidite' ; autoexec le charge par 'import', qui appelle controleHumidite_init(m).
#
# Bornes = modules.Thermo-Hygrometre.environnement.thermometres.<thermometre AM2301>.limites = [basse, haute] (pourcent d'humidite).
# Hysteresis de la ventilation (globalFonctions.be::changementEtatCapteur) : humidite >= haute -> relais lie ON, <= basse -> OFF,
# entre les deux -> il garde son etat. La page /humidite ecrit ces deux nombres dans le persist (persist.save(true)) : l'effet est
# immediat (la logique et l'affichage relisent 'limites' a chaque mesure) et reste apres un redemarrage.
# Les lignes par defaut de Tasmota sont masquees par 'affichageWebSensor' = "OFF" du bloc thermometres du module (configDevices.be
# lance alors WebSensor6 0) ; leurs valeurs restent dans la telemetrie MQTT.
# Valeurs affichees : JSON SENSOR de la carte (AM2301 : Temperature, Humidity, DewPoint), lu par controleGeneral.lectureSensors().
#
# Module solidifie : aucun import ni fonction de niveau fichier (le code de niveau fichier ne s'execute pas) ; tout est methode de la
# classe, les imports sont dans chaque methode ou closure qui les utilise.
#@ solidify:controleHumidite
var controleHumidite = module("controleHumidite")

class CONTROLE_HUMIDITE : Driver
    def init()
        # Commande Tasmota (console, HTTP, MQTT cmnd/<topic>/...) : ReglageHumidite [<basse> <haute>]
        #   sans argument : rend les bornes ; avec deux entiers : les regle (memes controles que la page /humidite)
        tasmota.add_cmd("ReglageHumidite", def(cmd, idx, payload, payload_json)
            import json
            import global
            import string
            import diversFonctions
            if diversFonctions.traiteAide("ReglageHumidite", payload, / sujet -> sujet == nil ? [["<basse> <haute>", "bornes d'humidité en % (basse < haute, 5 points d'écart au moins)", "sans argument : affiche les bornes"]] : nil, false)    return    end
            var c = global.controleHumidite
            var mots = string.split(str(payload), " ")
            if (size(str(payload)) > 0)
                if (size(mots) != 2)
                    tasmota.resp_cmnd(json.dump({"ReglageHumidite": {"erreur": "deux entiers attendus : <basse> <haute>"}}))
                    return
                end
                var erreur = c.regle(mots[0], mots[1])
                if (erreur != nil)
                    tasmota.resp_cmnd(json.dump({"ReglageHumidite": {"erreur": erreur}}))
                    return
                end
            end
            var b = c.bornes(c.thermo())
            tasmota.resp_cmnd(json.dump({"ReglageHumidite": (b == nil ? {"erreur": "aucun thermomètre AM2301 actif avec des limites"} : {"basse": b[0], "haute": b[1]})}))
        end)
    end

    # Thermometre AM2301 (type 1216) actif du module Thermo-Hygrometre, nil s'il n'y en a pas
    def thermo()
        var m = modules.find("Thermo-Hygrometre")
        if (type(m) != "instance" || m.find("activation", "OFF") != "ON")    return nil    end
        var ts = m.find("environnement", {}).find("thermometres", {})
        for cle: ts.keys()
            var t = ts[cle]
            if (type(t) == "instance" && t.find("activation", "OFF") == "ON" && t.find("type", 0) == 1216)    return t    end
        end
        return nil
    end

    # [basse, haute] entiers du thermometre th, nil si 'limites' manque ou n'a pas basse < haute
    def bornes(th)
        if (th == nil)    return nil    end
        var l = th.find("limites", [])
        if (size(l) > 1 && int(l[0]) < int(l[1]))    return [int(l[0]), int(l[1])]    end
        return nil
    end

    # Nombre a une decimale, virgule francaise
    def fmt(x)
        import string
        return string.replace(string.format("%.1f", x), ".", ",")
    end

    # Ecrit les bornes (texte ou entiers) : nil si c'est fait, sinon le message d'erreur. Rien n'est ecrit en cas d'erreur.
    def regle(bas, haut)
        import re
        import string
        import persist
        var th = self.thermo()
        if (th == nil)    return "Aucun thermomètre AM2301 actif."    end
        if (re.match("^[0-9]{1,3}$", str(bas)) == nil || re.match("^[0-9]{1,3}$", str(haut)) == nil)    return "Valeurs invalides : deux entiers de 0 à 100."    end
        var b = int(bas)
        var h = int(haut)
        if (h > 100 || h - b < 5)    return "La borne haute doit être au plus 100 et dépasser la basse d'au moins 5 points."    end
        th["limites"] = [b, h]
        persist.save(true)      # true : modif imbriquee, save() seul n'ecrit rien
        logFonctions.log(string.format("HUMIDITE: Bornes réglées à %i et %i %% !", b, h), LOG_LEVEL_INFO)
        return nil
    end

    # Zone des capteurs de la page d'accueil : trois tuiles (la tuile d'humidite change de couleur) puis la bande des bornes
    def web_sensor()
        import string
        import webserver
        var th = self.thermo()
        if (th == nil)    return    end
        var s = controleGeneral.lectureSensors().find("AM2301")
        if (!isinstance(s, map) || s.find("Humidity") == nil)    return    end
        var h = real(s["Humidity"])
        var b = self.bornes(th)
        var etat = ""
        if (b != nil)    etat = (h >= b[1] ? "thhum" : (h <= b[0] ? "thsec" : "thok"))    end

        webserver.content_send("<table style='width:100%'><fieldset><style>" +
            "div, fieldset, input, select{padding:3px;}fieldset{border-radius:0.3rem;}" +
            ".thT{display:flex;gap:8px;margin:8px 0 6px;}" +
            ".thc{flex:1;background:#3d3d3d;border-radius:8px;padding:8px 4px;text-align:center;border-bottom:4px solid #3d3d3d;}" +
            ".thc b{display:block;font-size:1.7rem;line-height:1.1;}.thc small{display:block;color:#bbb;font-size:0.75rem;margin-top:2px;}" +
            ".thc svg{width:26px;height:26px;}.thok{border-bottom-color:#4caf50;}.thsec{border-bottom-color:#3b82c4;}.thhum{border-bottom-color:#d43535;}" +
            ".thB{position:relative;height:22px;border-radius:5px;overflow:hidden;display:flex;margin:6px 0 0;padding:0;font-size:0.68rem;line-height:22px;text-align:center;}" +
            ".thB div{overflow:hidden;white-space:nowrap;padding:0;}.thB i{position:absolute;top:0;bottom:0;width:3px;background:#fff;box-shadow:0 0 3px #000;}" +
            ".thL{position:relative;height:16px;margin:2px 0;padding:0;font-size:0.7rem;color:#ccc;}.thL span{position:absolute;transform:translateX(-50%);}" +
            ".thR{text-align:right;margin-top:6px;font-size:0.8rem;}" +
            "</style><legend><b title='sensorHumidite'>Thermomètre Cave</b></legend>")
        webserver.content_send("<div class='thT'>" +
            "<div class='thc'><svg viewBox='0 0 24 24'><path d='M10 4a2 2 0 0 1 4 0v9.2a4 4 0 1 1-4 0z' fill='none' stroke='#ff8a65' stroke-width='2'/><circle cx='12' cy='17' r='2' fill='#ff8a65'/></svg>" +
                "<b>" + self.fmt(real(s.find("Temperature", 0))) + "°C</b><small>Température</small></div>" +
            "<div class='thc " + etat + "'><svg viewBox='0 0 24 24'><path d='M12 3c4 5 6 8 6 11a6 6 0 0 1-12 0c0-3 2-6 6-11z' fill='#4fc3f7'/></svg>" +
                "<b>" + self.fmt(h) + "%</b><small>Humidité</small></div>" +
            "<div class='thc'><svg viewBox='0 0 24 24'><path d='M12 3c3 4 5 7 5 9.5a5 5 0 0 1-10 0C7 10 9 7 12 3z' fill='none' stroke='#81d4fa' stroke-width='2'/><path d='M4 20h16' stroke='#81d4fa' stroke-width='2'/></svg>" +
                "<b>" + self.fmt(real(s.find("DewPoint", 0))) + "°C</b><small>Point de rosée</small></div></div>")
        if (b != nil)
            var pos = (h < 0 ? 0 : (h > 100 ? 100 : h))
            webserver.content_send("<div class='thB'>" +
                string.format("<div style='width:%i%%;background:#2a5d8f'>sec</div>", b[0]) +
                string.format("<div style='width:%i%%;background:#2e7d32'>plage visée</div>", b[1] - b[0]) +
                string.format("<div style='width:%i%%;background:#a02020'>ventilation</div>", 100 - b[1]) +
                string.format("<i style='left:%.1f%%'></i></div>", pos) +
                "<div class='thL'><span style='left:0;transform:none'>0</span>" +
                string.format("<span style='left:%i%%'><b>%i %%</b></span><span style='left:%i%%'><b>%i %%</b></span>", b[0], b[0], b[1], b[1]) +
                "<span style='left:100%;transform:translateX(-100%)'>100</span></div>" +
                "<div class='thR'><a href='/humidite'>Régler les bornes</a></div>")
        end
        webserver.content_send("</fieldset></table>")
    end

    def web_add_config_button()
        import webserver
        webserver.content_send("<p></p><form action='/humidite' method='get'><button>Réglage de l'humidité</button></form>")
    end

    # Page /humidite : deux curseurs, la bande se redessine en direct (script de la page, pas de la zone des capteurs).
    # texte : message de la derniere action ('' = aucun), erreur : true pour l'afficher en rouge
    def page(texte, erreur)
        import string
        import webserver
        var b = self.bornes(self.thermo())
        webserver.content_start("Humidité de la cave")
        webserver.content_send_style()
        if (b == nil)
            webserver.content_send("<p>Aucun thermomètre AM2301 actif avec des limites : rien à régler.</p>")
        else
            webserver.content_send("<style>.hp div{padding:0;}.hp .bd{display:flex;height:22px;border-radius:5px;overflow:hidden;margin:10px 0;font-size:0.7rem;line-height:22px;text-align:center;}" +
                ".hp input[type=range]{width:100%;}.hp .m{padding:6px;border-radius:5px;margin:6px 0;font-weight:bold;}</style><fieldset class='hp'><legend><b>Bornes d'humidité</b></legend>" +
                (texte != "" ? "<div class='m' style='background:" + (erreur ? "#b3261e" : "#2e7d32") + "'>" + texte + "</div>" : "") +
                "<form method='post' action='/humidite'>" +
                "<p>Borne basse, la ventilation s'arrête : <b id='vb'></b> %</p><input type='range' min='0' max='100' name='bas' value='" + str(b[0]) + "' oninput='maj()'>" +
                "<p>Borne haute, la ventilation démarre : <b id='vh'></b> %</p><input type='range' min='0' max='100' name='haut' value='" + str(b[1]) + "' oninput='maj()'>" +
                "<div class='bd' id='pv'><div style='background:#2a5d8f'>sec</div><div style='background:#2e7d32'>plage visée</div><div style='background:#a02020'>ventilation</div></div>" +
                "<p>Entre les deux bornes, la ventilation garde son état. Il faut au moins 5 points d'écart.</p>" +
                "<button>Enregistrer</button></form></fieldset>")
            webserver.content_send("<script>function maj(){var f=document.forms[0],b=+f.bas.value,h=+f.haut.value;" +
                "document.getElementById('vb').textContent=b;document.getElementById('vh').textContent=h;" +
                "var p=document.getElementById('pv').children;p[0].style.width=b+'%';p[1].style.width=Math.max(h-b,0)+'%';p[2].style.width=Math.max(100-h,0)+'%';}maj();</script>")
        end
        webserver.content_button(webserver.BUTTON_CONFIGURATION)
        webserver.content_stop()
    end

    def affiche()
        import webserver
        if (!webserver.check_privileged_access())    return nil    end
        self.page("", false)
    end

    def enregistre()
        import webserver
        if (!webserver.check_privileged_access())    return nil    end
        var erreur = self.regle(webserver.has_arg("bas") ? webserver.arg("bas") : "", webserver.has_arg("haut") ? webserver.arg("haut") : "")
        self.page(erreur == nil ? "Bornes enregistrées." : erreur, erreur != nil)
    end

    def web_add_handler()
        import webserver
        webserver.on("/humidite", / -> self.affiche(), webserver.HTTP_GET)
        webserver.on("/humidite", / -> self.enregistre(), webserver.HTTP_POST)
    end
end

# Publie la classe dans le module (solidification + import).
controleHumidite.CONTROLE_HUMIDITE = CONTROLE_HUMIDITE

# init() : APPELEE AUTOMATIQUEMENT par 'import controleHumidite'. Ne PAS la rappeler depuis autoexec. Driver enregistre seulement
# si le module Thermo-Hygrometre est active ; l'instance est publiee dans global.controleHumidite.
def controleHumidite_init(m)
    import global
    if (modules.find("Thermo-Hygrometre", {}).find("activation", "OFF") == "ON")
        var inst = m.CONTROLE_HUMIDITE()
        global.controleHumidite = inst
        tasmota.add_driver(inst)
        inst.web_add_handler()          # le serveur web peut deja tourner : FUNC_WEB_ADD_HANDLER ne viendrait plus
    end
    return m
end
controleHumidite.init = controleHumidite_init

# Valeur du module importe (sans elle, import rend nil et init() n'est pas appelee)
return controleHumidite
