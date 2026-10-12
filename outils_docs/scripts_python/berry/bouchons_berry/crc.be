# Bouchon du module natif Tasmota 'crc' pour banc_test_modbus.be.
# decrypteMSG (modbusFonctions.be) l'importe sans l'utiliser : le CRC est recalcule
# par modbusFonctions.crc16modbus. Le module vide suffit.
var crc = module("crc")
return crc
