# Exemple de code pour envoyer des données par UDP
#-
    u = udp()
    u.begin_multicast("224.3.0.1", 2000)
    u.send_multicast(bytes().fromstring("hello"))

    # alternatively
    u = udp()
    u.begin("", 0)      # send on all interfaces, choose random port number
    u.send("10.99.0.1", 2000, bytes().fromstring("world"))
-#

class UDP_LISTENER
    var udp

    def init(ip, port)
        self.udp = udp()

        log ("UDP_LISTENER: Connexion: " + (self.udp.begin_multicast(ip, port) ? "OK" : "Refusée"), LOG_LEVEL_DEBUG)
    end

    def every_50ms()
        import string

        var packet = self.udp.read()
		
        while packet != nil
            log (string.format("UDP_LISTENER: Données reçues:([%s]:%i) -> %s", self.udp.remote_ip, self.udp.remote_port, packet.asstring()), LOG_LEVEL_DEBUG)
            packet = self.udp.read()
        end
    end

    def sendMultiCast(message)
        self.udp.begin_multicast("224.3.0.1", 2000)
        self.udp.send_multicast(bytes().fromstring(message))
    end

    def sendUniCast(message)
        self.udp.begin("", 0)      # send on all interfaces, choose random port number
        self.udp.send("10.99.0.1", 2000, bytes().fromstring(message))
    end
end

# Charge la gestion des pages web
udpListener = UDP_LISTENER()
tasmota.add_driver(udpListener)	