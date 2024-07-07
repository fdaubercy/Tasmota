# Recense toutes les variables globales
var boolMute = true

# Déclaration des variables de LOG
var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var logSerial = LOG_LEVEL_INFO
var logWeb = LOG_LEVEL_INFO

# Vérifie si il y a une carte SD et des fichiers à copier dessus au 1er démarrage
load("/gestionCarteSD.be")

# Charge les fonctions utilisées

# Gère le script BERRY global à lancer
# Charge le Driver de controle global des modules