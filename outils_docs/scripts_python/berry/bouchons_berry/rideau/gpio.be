# Bouchon du module gpio de Tasmota pour banc_rideau_facade.be : niveaux[pin] = 0 ou 1 rendu par digital_read ;
# panne = true -> digital_read leve une exception ; lus = broches lues.
var gpio = module("gpio")
gpio.niveaux = {}
gpio.panne = false
gpio.lus = []
def gpio_digital_read(pin)
    import gpio
    gpio.lus.push(pin)
    if gpio.panne    raise "io_error", "broche simulee en panne"    end
    return gpio.niveaux.find(pin)
end
gpio.digital_read = gpio_digital_read
return gpio
