# preinit.be de l'ecran de la cave (Waveshare ESP32-S3-Touch-LCD-7B), copie de celui de l'ecran des debits (plan
# debits-deux-cartes A8) : la sequence est propre a la carte 7B, pas au metier.
#
# Allume la dalle et le tactile par l'expandeur d'E/S I2C 0x24, AVANT que Tasmota initialise l'ecran. Ordre du firmware
# (tasmota.ino) : GpioInit demarre l'I2C, BerryInit execute ce fichier, puis FUNC_PRE_INIT initialise l'ecran
# (xdrv_13_display.ino::DisplayInitDriver) et le GT911 du script :UTI de display.ini. L'autoexec passe trop tard.
#
# Registres de l'expandeur (demo Waveshare io_extension.h) : 0x02 mode (0xFF = sorties), 0x03 sorties, 0x05 PWM.
# Sorties : EXIO1 reset du tactile, EXIO2 retroeclairage, EXIO3 reset de la dalle, EXIO4 CS de la carte SD (au repos a 1),
# EXIO5 USB (0) ou CAN (1), EXIO6 alimentation de la dalle ; EXIO0 et EXIO7 a 1 comme la demo.
# Sequence du GT911 (demo 08_TOUCH, gt911.cpp) : reset bas, INT (GPIO4) bas, reset haut -> adresse 0x5D.
#
# Charte des logs : log() direct, comme demarrage.be : ce fichier s'execute avant le chargement de logFonctions.
# Une erreur ici laisse l'ecran noir, jamais la carte arretee (page web et console restent joignables).

import gpio

def preinitEcran7B()
    var EXPANDEUR = 0x24
    var SORTIES = 0xDF           # toutes a 1 sauf EXIO5 (USB) ; reset du tactile relache
    var RESET_TACTILE = 0x02     # EXIO1
    var INT_TACTILE = 4          # GPIO4, voir :UTI de display.ini
    var w = tasmota.wire_scan(EXPANDEUR)
    if w == nil
        log("PREINIT_ECRAN_ERREUR: expandeur 0x24 absent du bus I2C (SDA 8, SCL 9) : ecran noir !", 1)
        return false
    end
    # toutes les EXIO en sortie, puis dalle alimentee et tactile tenu en reset ; Wire.write rend false sans ACK
    if !w.write(EXPANDEUR, 0x02, 0xFF, 1) || !w.write(EXPANDEUR, 0x03, SORTIES & ~RESET_TACTILE, 1)
        log("PREINIT_ECRAN_ERREUR: expandeur 0x24 refuse l'ecriture : ecran noir !", 1)
        return false
    end
    gpio.pin_mode(INT_TACTILE, gpio.OUTPUT)
    tasmota.delay(100)
    gpio.digital_write(INT_TACTILE, 0)                           # INT bas pendant le reset : GT911 en 0x5D
    tasmota.delay(100)
    var relache = w.write(EXPANDEUR, 0x03, SORTIES, 1)           # reset relache, retroeclairage allume
    tasmota.delay(200)
    gpio.pin_mode(INT_TACTILE, gpio.INPUT)                       # rendu au pilote GT911
    if !relache
        log("PREINIT_ECRAN_ERREUR: expandeur 0x24 : reset du tactile non relache, tactile inactif !", 1)
        return false
    end
    log("PREINIT_ECRAN: expandeur 0x24 pret (sorties 0xDF), tactile reinitialise en 0x5D !", 2)
    return true
end

try
    preinitEcran7B()
except .. as e, m
    log("PREINIT_ECRAN_ERREUR: " + str(e) + " " + str(m) + " : ecran noir !", 1)
end
