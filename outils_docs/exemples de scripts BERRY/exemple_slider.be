# Exemple de slider: Cf. lien ci-dessous
# https://blog.claudiupersoiu.ro/2024/11/10/adding-a-slider-to-tasmota-using-berryscript/

import webserver
import persist
import string

class MySlider
    def init()
        if (!persist.m_start_temp)
            persist.m_start_temp = 55
        end

        if (!persist.m_stop_temp)
            persist.m_stop_temp = 50
        end
    end
 
    def web_add_main_button()
        webserver.content_send("<div style='padding:0'><h3>Set pump temperature</h3></div>")
        webserver.content_send(self._render_button(persist.m_start_temp, "Start", "start"))
        webserver.content_send(self._render_button(persist.m_stop_temp, "Stop", "stop"))
    end

    def _render_button(persist_item, label, id)
        return "<div style='padding:0'>"+
                    "<table style='width: 100%'>"+
                    "<tr>"+
                        "<td><label>"..label.." </label></td>"+
                        "<td align=\"right\"><span id='lab_"..id.."'>"..persist_item.."</span>°C</td>"+
                    "</tr>"+
                    "</table>"+
                    "<input type=\"range\" min=\"20\" max=\"70\" step=\"1\" "+
                    "onchange='la(\"&m_"..id.."_temp=\"+this.value)' "+
                    "oninput=\"document.getElementById('lab_"..id.."').innerHTML=this.value\" "+
                    "value='"..persist_item.."'/>"+
                "</div>"
    end

    def web_sensor()
        if webserver.has_arg("m_start_temp")
            var m_start_temp = int(webserver.arg("m_start_temp"))
            persist.m_start_temp = m_start_temp
            persist.save()
        end

        if webserver.has_arg("m_stop_temp")
            var m_stop_temp = int(webserver.arg("m_stop_temp"))
            persist.m_stop_temp = m_stop_temp
            persist.save()
        end
    end

    def json_append()
        var start = int(persist.m_start_temp)
        var stop = int(persist.m_stop_temp)
        var msg = string.format(",\"Pump\":{\"start\":%i,\"stop\":%i}", start, stop)
        tasmota.response_append(msg)
    end
end

slider = MySlider()
tasmota.add_driver(slider)


# Réglage de l'automatisation
# Lorsque la température de démarrage est atteinte, démarrez la pompe.
# Lorsque la température est inférieure à la température réglée, arrêtez simplement la pompe.
def heater_control(value) 
    if value >= persist.m_start_temp
        tasmota.set_power(0, true)
    end
    
    if value < persist.m_stop_temp
        tasmota.set_power(0, false)
    end
end 

tasmota.add_rule("DS18B20#Temperature", heater_control)