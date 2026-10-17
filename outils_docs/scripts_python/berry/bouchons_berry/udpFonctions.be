# Bouchon du module de framework 'udpFonctions' pour banc_test_modbus.be.
# envoiUDP() n'emet rien : il memorise les datagrammes pour que le banc verifie
# ce qui serait parti (type d'envoi, destinataire, message). Il rend true (envoye),
# ou false si le banc pose udpFonctions.refuse = true (envoi refuse, 2026-10-17).
# estIPv4() : copie de la vraie fonction (data/fs/udpFonctions.be).
var udpFonctions = module("udpFonctions")
udpFonctions.envois = []
udpFonctions.refuse = false
udpFonctions.envoiUDP = def (typeComm, ip, message) udpFonctions.envois.push([typeComm, ip, message]) return !udpFonctions.refuse end
udpFonctions.log = def (msg, niveau) end
udpFonctions.estIPv4 = def (texte)
    import string
    var s = str(texte)
    var morceaux = string.split(s, ".")
    if (size(morceaux) != 4 || s == "0.0.0.0")    return false    end
    for m: morceaux
        if (size(m) == 0 || size(m) > 3)    return false    end
        for i: 0 .. size(m) - 1
            if (m[i] < "0" || m[i] > "9")    return false    end
        end
        if (int(m) > 255)    return false    end
    end
    return true
end
return udpFonctions
