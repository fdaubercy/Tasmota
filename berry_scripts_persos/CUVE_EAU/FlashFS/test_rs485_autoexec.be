#- *********************************************************************************************
 * ADS1115 - 4 channel 16BIT A/D converter
 * I2C Address: 0x48, 0x49, 0x4A or 0x4B
 *
 * The ADC input range (or gain) can be changed via the following
 * defines, but be careful never to exceed VDD +0.3V max, or to
 * exceed the upper and lower limits if you adjust the input range!
 * Setting these values incorrectly may destroy your ADC!
 * ADS1115
 * -------
 * Setting "S0" -> 2/3x gain +/- 6.144V  1 bit = 0.1875mV (default)
 * Setting "S1" ->  1x gain   +/- 4.096V  1 bit = 0.125mV
 * Setting "S2" ->  2x gain   +/- 2.048V  1 bit = 0.0625mV
 * Setting "S3" ->  4x gain   +/- 1.024V  1 bit = 0.03125mV
 * Setting "S4" ->  8x gain   +/- 0.512V  1 bit = 0.015625mV
 * Setting "S5" ->  16x gain  +/- 0.256V  1 bit = 0.0078125mV
********************************************************************************************* -#

#- *********************************************************************************************
 * Capteur Analogique immergé dans l'eau de la cuve
 * Détecte la hauteur d'eau dans la Cuve
 * Variation de tension de 0 à 10V
 *
 * Attention l'ADS1115 n'accepte des tensions que de 0 à 6.144V
 * Donc nécessite l'emploi d'un pont diviseur de tension 10V vers 6V
********************************************************************************************* -#
# Recense toutes les variables globales
var boolMute = true

# Déclaration des variables de LOG
var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var logSerial = LOG_LEVEL_INFO
var logWeb = LOG_LEVEL_INFO

var capteursCuve

class CAPTEURS_CUVE : Driver
	# Variables
	var sensors
    var gain
    var ajustement
    var ads1115
    var ser
    var msg

    def init()
        import json
        import string

        self.ads1115 = [0.00, 0.00, 0.00, 0.00]

		# # Récupère le capteur analagique 'A0' étalon
		# self.ajustement = json.load(tasmota.read_sensors())["ADS1115"]["A0"]
        # log (string.format("CAPTEURS_CUVE: Ajustement=%d", self.ajustement), LOG_LEVEL_INFO)

        # # Récupère le gain du capteur
        # var pasGain = [0.1875, 0.125, 0.0625, 0.03125, 0.015625, 0.0078125]
        # self.gain = pasGain[int(string.split(tasmota.cmd("Sensor12", boolMute)["ADS1115"]["Settings"], "S")[1])]
        # log (string.format("CAPTEURS_CUVE: Gain=%.4f", self.gain), LOG_LEVEL_INFO)

        # # Interdit l'affichage des valeurs de capteurs sur la page html
        # tasmota.cmd("WebSensor12 0", boolMute)

        # Paramétrage port RS485 : gpio_rx:4 gpio_tx:5
        self.ser = serial(4, 5, 9600, serial.SERIAL_8N1)
    end

    def every_second()
        import string
        import crc
        import re

        # Envoi du message sur port RS485 -> "\r" + deviceAddress  + ";" + functionCode + ";" + values + ";" + crc + "\n"
        # values est non-nul si le maitre envoi un parametre à modifier
        self.msg = string.format("%i;%s;%i", 0x1F, (tasmota.read_sensors() == nil ? "pas de sensor" : tasmota.read_sensors()), 12)

        # Calcul & Ajout du CRC au message
        var calculCRC = crc.crc8(0xFF, bytes().fromstring(self.msg))
        self.msg = "\r" + self.msg + ";" + str(calculCRC) + "\n"

        # Envoi le message sur le port RS485
        self.ser.write(bytes().fromstring(self.msg))
        print("Message RS485 envoyé = " + self.msg)

        # Recoit message sur le port RS485
        self.msg = self.ser.read()
        
        # teste la presence des caractères de début et de fin
        if (string.find(self.msg.asstring(), "\r") | string.find(self.msg.asstring(), "\n")) > -1
            # Extrait le texte entre '\r' & '\n'
            if re.match("\r(.*?)\n", self.msg.asstring()) != nil
                self.msg = re.match("(.*?)\r(.*?)\n", self.msg.asstring())[2]
                print("Message RS485 reçu = " + self.msg)
            else print("Message RS485 reçu érroné ! ")
            end
        end
    end

    def web_sensor()
        # import json
        # import string

        # var htmlSensor = ""

        # # Récupère les capteurs
        # self.sensors = json.load(tasmota.read_sensors())

        # # Corrige les valeurs des capteurs analogiques avec la valeur étalon
        # self.ajustement = self.sensors["ADS1115"]["A0"]
        # for nb: 0 .. 3
        #     self.ads1115[nb] = self.sensors["ADS1115"]["A" + str(nb)] - self.ajustement
        # end

        # # Affichage sur page web
        # log (string.format("CAPTEURS_CUVE: %d", self.ads1115[3]), LOG_LEVEL_INFO)
        # htmlSensor += string.format("{s}Capteur de Niveau de Cuve{m}%.3fV{e}", real(self.ads1115[3] * self.gain) / 1000)
        # tasmota.web_send(htmlSensor)
    end
end

# Active le Driver de controle global des modules
capteursCuve = CAPTEURS_CUVE()
tasmota.add_driver(capteursCuve)