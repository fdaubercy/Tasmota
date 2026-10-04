# Bouchon du module 'rangeExtenderFonctions' pour test_discovery.be.
# Le banc charge le VRAI rangeExtenderFonctions.be par compile() (global) ; sur la carte,
# discoveryFonctions l'obtient par 'import'. Ce bouchon renvoie ce module deja charge, pour
# que l'import du banc teste le vrai code (redirige) et non une copie.
import global
return global.rangeExtenderFonctions
