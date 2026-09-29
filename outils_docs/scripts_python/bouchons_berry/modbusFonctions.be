# RELAIS (pas un bouchon) pour banc_test_modbus.be : le banc charge le VRAI
# data/fs/modbusFonctions.be par compile(), ce qui cree une globale. Les fonctions
# qui font 'import modbusFonctions' (ex. le handler de modBus_TasmotaSlaveModBus)
# recoivent ici ce meme module, pas une copie.
import global
return global.modbusFonctions
