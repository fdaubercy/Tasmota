"""Registre des outils PC de l'annuaire (port 7600) : donnees pures et validation des parametres.

Rien ici ne lance de processus ni n'ouvre de port. L'annuaire (serveur, page) consomme :
    OUTILS, GROUPES, DEBITS, par_id(), valide(), en_json().
Securite : valide() est la seule porte par ou des valeurs venues de la page deviennent des arguments
de ligne de commande. Chaque valeur est contrainte (liste fermee ou entier borne), jamais un texte libre.
"""

from dataclasses import dataclass

GROUPES = ["Bus et cartes", "Réseau et journaux", "Maintenance"]
DEBITS = [9600, 19200, 38400, 57600, 74880, 115200, 230400, 460800, 921600]
CONSOLE = "%LOCALAPPDATA%\\outils_tasmota\\consoles\\{}.log"
DOSSIER = "outils_docs/scripts_python/"
ARRET = ("Pour l'arrêter : bouton Arrêter de l'annuaire, ou Ctrl+C dans son terminal "
         "s'il a été lancé ailleurs.")


@dataclass
class Parametre:
    cle: str
    libelle: str
    option: str
    defaut: str
    genre: str          # com | com_ou_pont | debit | port_http | drapeau (case : "on" -> option seule, "off" -> rien)


@dataclass
class Outil:
    id: str
    nom_acces: str
    nom: str
    groupe: str
    interet: str
    aide: str
    script: str
    parametres: list
    cle_port_page: str
    journaux: str
    dans_job: bool = True
    route_occupe: str = ""
    arret_refuse: str = ""          # pourquoi l'arret est refuse quand route_occupe repond en_cours (aide de la page)

    @property
    def a_port_com(self):
        return any(p.genre in ("com", "com_ou_pont") for p in self.parametres)

    def port_page(self, valeurs):
        for p in self.parametres:
            if p.cle == self.cle_port_page:
                return int(valeurs.get(p.cle, p.defaut))
        raise KeyError(self.cle_port_page)


def _port(cle, defaut, libelle="Port de la page"):
    return Parametre(cle, libelle, "--" + cle.replace("_", "-"), str(defaut), "port_http")


OUTILS = [
    Outil(
        "pont_serie", "Pont serie", "Pont série", GROUPES[0],
        "Partage le port série d'une carte entre plusieurs terminaux, avec une page web.",
        "Ouvre le port série d'une carte (ESP32) et le partage : terminal sur la page web et flux TCP brut "
        "pour les autres outils (testeur UDP, console). Paramètres : le port série (auto = le seul port USB "
        "présent), la vitesse, le port TCP/HTTP (7000 par défaut) et « Relancer le log série Tasmota » "
        "(--relance-log : Tasmota coupe son log série 600 s après son démarrage, le pont lui renvoie SerialLog "
        "à l'ouverture du port et à chaque coupure ; la case de la page du pont reste utilisable). " + ARRET,
        DOSSIER + "outils_pc/pont_serie.py",
        [Parametre("port", "Port série", "--port", "auto", "com"),
         Parametre("vitesse", "Vitesse (bauds)", "--vitesse", "115200", "debit"),
         _port("tcp", 7000, "Port TCP et page"),
         Parametre("relance_log", "Relancer le log série Tasmota", "--relance-log", "off", "drapeau")],
        "tcp",
        "Console capturée : " + CONSOLE.format("pont_serie") + ". Copie brute du flux : option --journal "
        "du script (pas de fichier par défaut)."),
    Outil(
        "sniffeur_modbus", "sniffeur ModBus", "Sniffeur ModBus", GROUPES[0],
        "Écoute le bus ModBus RS485 et décode les trames en direct, avec appariement requête/réponse.",
        "Écoute le bus ModBus par un convertisseur USB-RS485 : trames en direct, latences, réponses "
        "manquantes, décodage champ par champ, envoi de trames et émulation de la carte 16 relais. "
        "Paramètres : le port série (auto = le seul convertisseur présent), le débit du bus (19200) et "
        "le port de la page (7300). " + ARRET,
        DOSSIER + "outils_pc/sniffeur_modbus.py",
        [Parametre("port", "Port série", "--port", "auto", "com"),
         Parametre("debit", "Débit du bus (bauds)", "--debit", "19200", "debit"),
         _port("http", 7300)],
        "http",
        "Console capturée : " + CONSOLE.format("sniffeur_modbus") + ". Copie des trames : option --journal "
        "du script (pas de fichier par défaut)."),
    Outil(
        "testeur_udp", "Testeur UDP", "Testeur UDP", GROUPES[0],
        "Teste l'UDP entre le maître et l'esclave ModBus et juge chaque essai.",
        "Ouvre les ports série du maître et de l'esclave (ou le pont série, pont:7000), envoie des trames "
        "UDP en unicast ou multicast et juge chaque essai (reçu, émis non reçu, non émis...). Paramètres : "
        "port du maître, port de l'esclave (vides = fermés), vitesse et port de la page (7400). " + ARRET,
        DOSSIER + "outils_pc/testeur_udp.py",
        [Parametre("port_maitre", "Port du maître", "--port-maitre", "", "com_ou_pont"),
         Parametre("port_esclave", "Port de l'esclave", "--port-esclave", "", "com_ou_pont"),
         Parametre("vitesse", "Vitesse (bauds)", "--vitesse", "115200", "debit"),
         _port("http", 7400)],
        "http",
        "Console capturée : " + CONSOLE.format("testeur_udp") + ". Lignes des deux cartes (mot de passe "
        "masqué) : option --journal du script (pas de fichier par défaut)."),
    Outil(
        "sniffeur_mqtt", "Sniffeur MQTT", "Sniffeur MQTT", GROUPES[1],
        "Sniffeur et publieur MQTT : messages en direct, abonnements, audit discovery, logs par carte.",
        "Se connecte à un ou plusieurs brokers MQTT : messages en direct avec filtre et différences, "
        "abonnements mémorisés par broker, publication, audit discovery et logs par carte. Le broker "
        "par défaut est lu dans user_config_override.h. Seul paramètre ici : le port de la page (7100). "
        + ARRET,
        DOSSIER + "outils_pc/sniffeur_mqtt.py",
        [_port("http", 7100)],
        "http",
        "Console capturée : " + CONSOLE.format("sniffeur_mqtt") + ". Copie des messages : option --journal "
        "du script (pas de fichier par défaut)."),
    Outil(
        "syslog", "Serveur syslog", "Serveur syslog", GROUPES[1],
        "Reçoit les logs syslog (UDP 514) des modules Tasmota et les affiche sur une page filtrable.",
        "Écoute les logs envoyés en UDP par les modules (SYS_LOG_HOST) : page avec filtre module, sévérité "
        "et texte, registre des modules vus, export. Seul paramètre ici : le port de la page (7200). "
        + ARRET,
        DOSSIER + "outils_pc/syslog_tasmota.py",
        # Journal sur disque par defaut (2026-10-31) : la memoire (5000 lignes) ne couvre que ~1 h 20
        [_port("http", 7200), Parametre("journal", "Journal sur disque", "--journal", "on", "drapeau")],
        "http",
        "Console capturée : " + CONSOLE.format("syslog") + ". Journal des messages (une ligne par message, "
        "rotation à 20 Mo) : %TEMP%\\syslog_tasmota.log, comme la cible Custom (case « Journal sur disque »)."),
    Outil(
        "synchro_fork", "Synchro du fork", "Synchro du fork", GROUPES[2],
        "Synchronise le fork avec l'amont arendst/Tasmota, questions posées par boutons.",
        "Page web de la synchro du fork : état du fork, nouveautés de l'amont, fichiers modifiés et leur "
        "diff, puis lancement des scripts de synchro (merge ou rebase) dont les questions deviennent des "
        "boutons. Seul paramètre ici : le port de la page (7500). Pour l'arrêter : bouton Arrêter de "
        "l'annuaire (refusé pendant une synchro), ou Ctrl+C dans son terminal s'il a été lancé ailleurs.",
        DOSSIER + "maintenance/synchro_fork_web.py",
        [_port("http", 7500)],
        "http",
        "Console capturée : " + CONSOLE.format("synchro_fork") + ". Historique des synchros : "
        "outils_docs/HISTORIQUE_SYNCHRO_FORK.md.",
        dans_job=False, route_occupe="/execution",
        arret_refuse="L'arrêt est refusé tant qu'une opération est en cours (synchro, fusion ou envoi : l'outil le "
                     "signale par /execution), pour ne pas laisser un dépôt à moitié modifié."),
    Outil(
        "build", "Build et téléversement", "Build et téléversement", GROUPES[2],
        "Compile et téléverse les cartes du parc (firmware et file system, COM ou OTA), avec suivi en direct.",
        "Page web de build : on coche des environnements PlatformIO et des actions (compiler, téléverser le "
        "firmware, construire le file system, téléverser le file system), COM ou OTA par ligne ; les "
        "environnements passent l'un après l'autre, avec étape, pourcentage, durées et échecs en direct. "
        "Seul paramètre ici : le port de la page (7700). Pour l'arrêter : bouton Arrêter de l'annuaire "
        "(refusé pendant un lancement), ou Ctrl+C dans son terminal s'il a été lancé ailleurs.",
        DOSSIER + "outils_pc/build_web.py",
        [_port("http", 7700)],
        "http",
        "Console capturée : " + CONSOLE.format("build") + ". Sortie complète de chaque pio run : "
        "%LOCALAPPDATA%\\outils_tasmota\\build\\journaux\\.",
        dans_job=False, route_occupe="/execution",
        arret_refuse="Tant qu'un lancement de build est en cours (l'outil le signale par /execution), l'arrêt est "
                     "refusé jusqu'à sa fin, pour ne pas couper un téléversement ni laisser un pio orphelin. Pour "
                     "abréger, l'arrêter d'abord depuis sa page (« Arrêter après cet env » ou « Arrêt immédiat »)."),
    Outil(
        "fichiers_berry", "Fichiers Berry par env", "Fichiers Berry par env", GROUPES[2],
        "Choisit, env par env, les fichiers Berry sur le FS, exclus ou solidifiés, et crée un env à partir "
        "d'une carte modèle.",
        "Page web qui lit et écrit platformio_tasmota_cenv.ini : pour chaque fichier Berry (data/fs, dossier de "
        "la carte, modules de l'amont), son état dans l'env (sur le FS, exclu, solidifié) et d'où vient sa ligne ; "
        "une liste partagée ([berry_commun], option d'une base) n'est modifiée qu'après avoir vu les envs touchés. "
        "Diff avant chaque écriture, copie .bak, écriture refusée pendant un build. Crée aussi un env (section du "
        "cenv, dossier data/, section de user_config_override.h) à partir d'une carte modèle. Seul paramètre ici : "
        "le port de la page (7800). Rien n'est écrit sans « Enregistrer » : l'arrêter à tout moment.",
        DOSSIER + "outils_pc/fichiers_berry_web.py",
        [_port("http", 7800)],
        "http",
        "Console capturée : " + CONSOLE.format("fichiers_berry") + ". Copies avant écriture : "
        "platformio_tasmota_cenv.ini.bak et tasmota/user_config_override.h.bak."),
    Outil(
        "assistant_persist", "Assistant persist", "Assistant persist", GROUPES[2],
        "Crée une nouvelle carte : pose des questions, produit le persist, l'autoexec et les sections du cenv et du .h.",
        "Page web en cinq étapes (carte, réseau, fonctions, bloc métier, vérification) : aperçu du _persist.json en "
        "direct, mots de passe recopiés du parc par le serveur (jamais affichés), diff avant écriture, création "
        "atomique du dossier data/, de la section du cenv et de celle de user_config_override.h, refusée pendant un "
        "build. Seul paramètre ici : le port de la page (7900). Rien n'est écrit sans « Créer l'env » : "
        "l'arrêter à tout moment.",
        DOSSIER + "outils_pc/assistant_persist_web.py",
        [_port("http", 7900)],
        "http",
        "Console capturée : " + CONSOLE.format("assistant_persist") + ". Sauvegardes horodatées avant création : "
        "%LOCALAPPDATA%\\outils_tasmota\\fichiers_berry\\sauvegardes\\."),
]


def par_id(id):
    for o in OUTILS:
        if o.id == id:
            return o
    raise KeyError(id)


def _entier(valeur, libelle):
    try:
        return int(str(valeur).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{libelle} : nombre entier attendu")


def _valide_une(p, valeur, ports_detectes, ponts):
    """Renvoie la valeur validee (chaine) d'un parametre, ou leve ValueError."""
    if p.genre == "com":
        v = str(valeur)
        if v != "auto" and v not in ports_detectes:
            raise ValueError(f"{p.libelle} : port inconnu")
        return v
    if p.genre == "com_ou_pont":
        v = str(valeur)
        if v == "" or v in ports_detectes:
            return v
        n = v[5:]
        if v.startswith("pont:") and n.isdigit() and v == f"pont:{int(n)}" and int(n) in ponts:
            return v
        raise ValueError(f"{p.libelle} : port ou pont inconnu")
    if p.genre == "debit":
        n = _entier(valeur, p.libelle)
        if n not in DEBITS:
            raise ValueError(f"{p.libelle} : débit non pris en charge")
        return str(n)
    if p.genre == "port_http":
        n = _entier(valeur, p.libelle)
        if not 1024 <= n <= 65535:
            raise ValueError(f"{p.libelle} : port entre 1024 et 65535 attendu")
        return str(n)
    if p.genre == "drapeau":
        v = {"on": "on", "off": "off", "true": "on", "false": "off"}.get(str(valeur).strip().lower())
        if v is None:
            raise ValueError(f"{p.libelle} : on ou off attendu")
        return v
    raise ValueError(f"{p.libelle} : genre inconnu")


def valide(outil, valeurs, ports_detectes, ponts):
    """Arguments CLI [option, valeur, ...] dans l'ordre des parametres ; ValueError sinon."""
    inconnues = sorted(set(valeurs) - {p.cle for p in outil.parametres})
    if inconnues:
        raise ValueError("paramètre inconnu : " + ", ".join(inconnues))
    args = []
    for p in outil.parametres:
        v = _valide_une(p, valeurs.get(p.cle, p.defaut), ports_detectes, ponts)
        if p.genre == "com_ou_pont" and v == "":
            continue
        if p.genre == "drapeau":       # option sans valeur, presente seulement si cochee
            args += [p.option] if v == "on" else []
            continue
        args += [p.option, v]
    return args


def en_json():
    outils = []
    for o in OUTILS:
        outils.append({"id": o.id, "nom_acces": o.nom_acces, "nom": o.nom, "groupe": o.groupe,
                       "interet": o.interet, "aide": o.aide, "parametres": [vars(p).copy() for p in o.parametres],
                       "cle_port_page": o.cle_port_page, "journaux": o.journaux, "dans_job": o.dans_job,
                       "route_occupe": o.route_occupe, "arret_refuse": o.arret_refuse, "a_port_com": o.a_port_com,
                       "port_defaut": o.port_page({})})
    return {"groupes": list(GROUPES), "outils": outils, "debits": list(DEBITS)}
