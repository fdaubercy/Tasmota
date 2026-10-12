# Bouchon du module de framework 'globalFonctions' pour banc_test_modbus.be.
# modBus_TasmotaSlaveModBus l'importe dans son handler de reception sans en appeler
# de fonction : le module vide suffit.
var globalFonctions = module("globalFonctions")
return globalFonctions
