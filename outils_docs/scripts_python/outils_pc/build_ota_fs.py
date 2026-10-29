"""Envoi par le reseau (OTA) du firmware et du file system d'une carte Tasmota, pour la page Build.

Trois fonctions, appelees par build_serie.Serie apres le `pio run` qui produit ce qu'elles envoient :

  envoie_firmware_ota(env, ip, dossier_build, rapporte)
      .pio/build/<env>/firmware.bin.gz (s'il n'est pas plus ancien que firmware.bin), sinon
      firmware.bin, par POST /u2 (champ `file`), comme le navigateur sur la page /up de Tasmota
      (bascule en safeboot comprise, voir plus bas) ; puis attente du retour de la carte et preuve
      par `Status 2` (version + date de compilation changees).
  extrait_image(image, dossier)
      fichiers de .pio/build/<env>/littlefs.bin, l'image que `pio run -t buildfs` vient d'ecrire (celle
      qu'un uploadfs par cable flasherait), copies dans un dossier temporaire. PAS littlefs_data : ce
      dossier est rempli par post_esp32.py apres chaque edition des liens, jamais vide, et ne recoit
      data/fs, data/json, data/sd que pour certaines cibles (spec, choix 10.1 revise).
  envoie_fs_ota(env, ip, dossier_fs, sauvegardes, rapporte)
      tout ce dossier par /ufsu, sous-dossiers compris (deroule du choix 10 de
      docs/superpowers/specs/2026-10-24-page-build-televersement-design.md).

Pourquoi la page envoie le firmware elle-meme (spec, choix 7 revise) : ota-files-uploader.py lance
depuis le pre-script passerait AVANT post_esp32.py, qui remet esptool dans UPLOADCMD a chaque edition
des liens. Les scripts de build/ ne sont donc pas touches.

Ce que fait Tasmota, et que ce module suit (lu dans tasmota/tasmota_xdrv_driver/) :
  - toute route autre que / exige `Referer: http://<ip>/` (SetOption128 0), sinon la connexion est
    fermee SANS reponse ; un fichier absent a telecharger aussi (xdrv_50 UfsDirectory) ;
  - POST /u2 n'ecrit rien si la page /up n'a pas ete ouverte avant (Web.upload_file_type remis a
    UPL_NONE apres chaque envoi, xdrv_01_9 l.3469 et l.3551) ET repond quand meme « Successful » :
    d'ou le GET /up avant chaque envoi du firmware ;
  - les reponses d'envoi sont toujours HTTP 200 : l'echec se lit dans la page (« Failed », « Échoué ») ;
  - partition OTA unique + safeboot (tables partitions/esp32_partition_app3904k_fs11584k.csv et
    app2752k_fs448k.csv du fork) : l'appli ne peut pas s'ecraser elle-meme. La page /up sert alors
    HTTP_FORM_RST_UPG_FCT (xdrv_01_9 l.382-395, choisi l.3420) dont le script upl() / fct()
    (html_uncompressed/HTTP_HEAD_LAST_SCRIPT32.h l.28-64) fait, pour une image non compressee
    (1er octet 0xE9) : GET /u4?u4=fct&api= en boucle (« false » : la carte redemarre en safeboot,
    nouvel essai 6 s plus tard ; pas de reponse : nouvel essai 2 s plus tard ; « true » : en safeboot)
    puis envoi du formulaire. HandleSwitchBootPartition (l.3845-3896) repond « none » s'il n'y a pas
    de partition unique (aucun effet), et arme l'envoi (UPL_TASMOTA) quand il ne redemarre pas.
    Une image compressee (0x1F) part directement, comme dans le navigateur ;
  - un fichier envoye par /ufsu va dans <dossier courant>/<nom> (UfsUploadFileOpen). Le dossier
    courant est remis a / par chaque GET /ufsd et devient <d> avec `download=<d>` si <d> est un
    dossier. `dir=0` vise la flash (dir=1 = carte SD, que la page de fichiers a pu choisir) ;
  - aucune commande ne cree de dossier : on passe par Berry, `path.mkdir` (qui agit sur la flash) ;
  - chemin complet limite a 49 caracteres (UFS_FILENAME_SIZE = 50) : verifie avant tout envoi.

Erreurs : RuntimeError("<étape> : <motif>"). `rapporte` recoit {"etape", "pourcent", "detail"}.
stdlib (urllib.request pour les GET, http.client pour les POST envoyes par morceaux), plus
littlefs-python pour lire l'image (present dans le penv de PlatformIO, qui s'en sert pour l'ecrire).
"""

import http.client
import json
import re
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ETAPE_IMAGE = "Lecture de littlefs.bin"
ETAPE_CONNEXION = "Connexion par le maître"
ETAPE_TELEVERSEMENT = "Téléversement"
ETAPE_SAFEBOOT = "Bascule en safeboot"
ETAPE_SAUVEGARDE = "Sauvegarde du persist"
ETAPE_DOSSIERS = "Création des dossiers"
ETAPE_ENVOI = "Envoi des fichiers"
ETAPE_RELECTURE = "Relecture du persist"
ETAPE_RECHARGEMENT = "Rechargement du persist"
ETAPE_REDEMARRAGE = "Redémarrage"
ETAPE_BERRY = "Rechargement de Berry"
ETAPE_VERIFICATION = "Vérification après redémarrage"

PERSIST = "_persist.json"
# Spec, choix 10.5 : sans ce rechargement, l'evenement System#Save du Restart recopie les globales
# (encore l'ancien contenu) dans le persist et ecrase celui qu'on vient d'envoyer (lecon du 2026-10-18).
BR_RECHARGE = ("Br import persist persist.load() serveur = persist.serveur diverses = persist.diverses "
               "modules = persist.modules drivers = persist.drivers")
ECHECS_PAGE = ("Failed", "Échoué", "denied")
LONGUEUR_MAX = 49                    # UFS_FILENAME_SIZE - 1 (xdrv_50_filesystem.ino:90)
MORCEAU = 8192
# Parametres de l'image ecrite par `pio run -t buildfs` : build_fs_image de
# ~/.platformio/platforms/espressif32/builder/main.py:549-560 (block_size = FS_BLOCK = 0x1000, l.478 ;
# block_count = FS_SIZE // block_size = taille de l'image, qui est tout le tampon). disk_version n'est
# pas passe : au montage, littlefs accepte toute version 2.x de mineure <= la sienne (2.0 et 2.1).
BLOC_IMAGE = 4096
REGLAGES_IMAGE = {"block_size": BLOC_IMAGE, "read_size": 1, "prog_size": 1, "cache_size": BLOC_IMAGE,
                  "lookahead_size": 32, "block_cycles": 500, "name_max": 64}
SANS_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # carte sur le reseau local


# -- HTTP ---------------------------------------------------------------------------------------------

def _entetes(ip):
    return {"Referer": f"http://{ip}/"}


def _get(ip, chemin, delai):
    """GET -> corps (bytes) ; leve OSError / HTTPException si la carte ne repond pas."""
    requete = urllib.request.Request(f"http://{ip}{chemin}", headers=_entetes(ip))
    with SANS_PROXY.open(requete, timeout=delai) as reponse:
        if reponse.status != 200:
            raise OSError(f"HTTP {reponse.status}")
        return reponse.read()


def _commande(ip, cmnd, delai):
    """/cm?cmnd=<cmnd> URL-encodee -> texte de la reponse JSON."""
    return _get(ip, "/cm?cmnd=" + urllib.parse.quote(cmnd, safe=""), delai).decode("utf-8", "replace")


ESSAIS_MAITRE = 3   # liaison du maitre P4 irreguliere : 2 requetes sur 40 au-dela de 8 s, 15 % de ping perdus (2026-10-29)


def _commande_repetee(ip, cmnd, delai, essais=ESSAIS_MAITRE):
    """_commande rejouee jusqu'a `essais` fois sans reponse : seulement pour une commande sans effet si rejouee."""
    for _ in range(essais - 1):
        try:
            return _commande(ip, cmnd, delai)
        except (OSError, http.client.HTTPException):
            pass
    return _commande(ip, cmnd, delai)


def _poste(ip, chemin, champ, nom, donnees, delai, progression=None):
    """POST multipart (un seul fichier, ecrit a la main) envoye par morceaux -> (statut, texte).

    `progression(envoyes, total)` est appele apres chaque morceau.
    """
    hote, _, port = ip.partition(":")
    limite = "----build-web-" + uuid.uuid4().hex
    tete = (f'--{limite}\r\nContent-Disposition: form-data; name="{champ}"; filename="{nom}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n").encode("utf-8")
    queue = f"\r\n--{limite}--\r\n".encode("ascii")
    connexion = http.client.HTTPConnection(hote, int(port or 80), timeout=delai)
    try:
        connexion.putrequest("POST", chemin)
        connexion.putheader("Content-Type", f"multipart/form-data; boundary={limite}")
        connexion.putheader("Content-Length", str(len(tete) + len(donnees) + len(queue)))
        connexion.putheader("Referer", _entetes(ip)["Referer"])
        connexion.endheaders()
        connexion.send(tete)
        for debut in range(0, len(donnees), MORCEAU):
            connexion.send(donnees[debut:debut + MORCEAU])
            if progression:
                progression(min(debut + MORCEAU, len(donnees)), len(donnees))
        connexion.send(queue)
        reponse = connexion.getresponse()
        return reponse.status, reponse.read().decode("utf-8", "replace")
    finally:
        connexion.close()


def _page_en_echec(statut, texte):
    return statut != 200 or any(mot in texte for mot in ECHECS_PAGE)


def _attend_retour(ip, delai_retour, attente_min, sondage, delai_http):
    """Attend que la carte redemarree reponde a Status.

    Une reponse ne compte qu'une fois la carte vue muette, ou passe `attente_min` : juste apres
    l'ordre, la carte repond encore avant de redemarrer (ota-files-uploader.py attendait 15 s).
    """
    debut, vue_muette = time.monotonic(), False
    while time.monotonic() - debut < delai_retour:
        try:
            _commande(ip, "Status", min(3.0, delai_http))
            if vue_muette or time.monotonic() - debut >= attente_min:
                return
        except (OSError, http.client.HTTPException):
            vue_muette = True
        time.sleep(sondage)
    raise RuntimeError(f"{ETAPE_REDEMARRAGE} : la carte {ip} n'a pas répondu {delai_retour:g} s après le redémarrage")


# -- firmware -----------------------------------------------------------------------------------------

def _version(ip, delai):
    """(Version, BuildDateTime) de `Status 2` ; leve OSError / HTTPException / ValueError."""
    fwr = json.loads(_commande(ip, "Status 2", delai)).get("StatusFWR") or {}
    if not fwr.get("Version"):
        raise ValueError("pas de StatusFWR.Version dans la réponse")
    return fwr.get("Version"), fwr.get("BuildDateTime")


def _page_safeboot(ip, delai):
    """Nom de la carte si sa page d'accueil est celle du safeboot, sinon None.

    Le safeboot ne connait ni Status, ni Status 2, ni Status 5 (« Unknown », cuve le 2026-10-28), et /u4?api=
    repond « true » des qu'il y a une partition OTA unique : seule la page d'accueil le dit (<h3>SAFEBOOT</h3>,
    titre « <DeviceName> Main Menu »).
    """
    try:
        texte = _get(ip, "/", delai).decode("utf-8", "replace")
    except (OSError, http.client.HTTPException):
        return None
    if "<h3>SAFEBOOT</h3>" not in texte:
        return None
    titre = re.search(r"<title>(.*?)(?: Main Menu)?</title>", texte)
    return titre.group(1) if titre else ""


def _bascule_safeboot(ip, rapporte, delai_retour, sondage, delai_http):
    """Logique fct() du navigateur : True si la carte est en safeboot, False si pas de safeboot."""
    debut = time.monotonic()
    while time.monotonic() - debut < delai_retour:
        try:
            reponse = _get(ip, "/u4?u4=fct&api=", min(5.0, delai_http)).decode("utf-8", "replace").strip()
        except (OSError, http.client.HTTPException):
            time.sleep(sondage)                                 # carte en redemarrage
            continue
        if reponse == "none":
            return False
        if reponse == "true":
            return True
        if reponse != "false":
            raise RuntimeError(f"{ETAPE_SAFEBOOT} : réponse inattendue de /u4 : {_resume(reponse)!r}")
        rapporte({"etape": ETAPE_SAFEBOOT, "pourcent": None, "detail": f"{ip} redémarre en safeboot"})
        time.sleep(3 * sondage)                                 # 6 s par defaut, comme le navigateur
    raise RuntimeError(f"{ETAPE_SAFEBOOT} : la carte {ip} n'est pas revenue en safeboot en {delai_retour:g} s")


def envoie_firmware_ota(env, ip, dossier_build, rapporte, *, delai_retour=90.0, attente_min=15.0,
                        sondage=2.0, delai_http=30.0):
    """Envoie firmware.bin.gz (sinon firmware.bin) de `dossier_build` par /u2, puis prouve le changement.

    Sequence : Status 2 (version avant) -> [image 0xE9 : /u4?u4=fct&api=, bascule en safeboot si la
    carte a une partition OTA unique] -> GET /up -> POST /u2 -> attente du retour -> Status 2, qui doit
    differer (sinon « firmware inchangé ») et ne plus etre le safeboot.
    """
    dossier_build = Path(dossier_build)
    gz, binaire = dossier_build / "firmware.bin.gz", dossier_build / "firmware.bin"
    # .gz seulement s'il est au moins aussi recent que firmware.bin : une compression ratee ou
    # desactivee laisse l'ancien .gz a cote du nouveau firmware.bin.
    if gz.is_file() and (not binaire.is_file() or gz.stat().st_mtime >= binaire.stat().st_mtime):
        fichier = gz
    else:
        fichier = binaire if binaire.is_file() else None
    if fichier is None:
        raise RuntimeError(f"{ETAPE_TELEVERSEMENT} : ni firmware.bin.gz ni firmware.bin dans {dossier_build}")
    donnees = fichier.read_bytes()
    nom = env + fichier.name[len("firmware"):]                  # <env>.bin(.gz), comme espupload.py
    dernier = [-1]
    reseau = (OSError, http.client.HTTPException)

    def progression(envoyes, total):
        pourcent = envoyes * 100 // total
        if pourcent != dernier[0]:                             # un evenement par point de %
            dernier[0] = pourcent
            rapporte({"etape": ETAPE_TELEVERSEMENT, "pourcent": pourcent, "detail": f"{nom} vers {ip}"})

    rapporte({"etape": ETAPE_TELEVERSEMENT, "pourcent": 0, "detail": f"{nom} vers {ip}"})
    try:
        avant = _version(ip, delai_http)
    except reseau as erreur:
        raise RuntimeError(f"{ETAPE_TELEVERSEMENT} : carte {ip} injoignable ({erreur})") from None
    except ValueError as erreur:
        # Carte restee en safeboot par un envoi coupe : on relance l'envoi (essai A11 du 2026-10-28).
        if _page_safeboot(ip, delai_http) is None:
            raise RuntimeError(f"{ETAPE_TELEVERSEMENT} : Status 2 illisible ({erreur})") from None
        avant = ("safeboot", "carte trouvée en safeboot")
    en_safeboot = avant[0] == "safeboot"
    if donnees[:1] == b"\xe9":                                 # le navigateur ne bascule que dans ce cas
        en_safeboot = _bascule_safeboot(ip, rapporte, delai_retour, sondage, delai_http)
        rapporte({"etape": ETAPE_TELEVERSEMENT, "pourcent": 0, "detail": f"{nom} vers {ip}"})
    # Apres une bascule effective, un echec laisse la carte en safeboot (sans Berry ni drivers) : le dire.
    safeboot = f" ; carte restée en safeboot : renvoyer un firmware par http://{ip}/up" if en_safeboot else ""
    try:
        _get(ip, "/up", delai_http)                            # arme l'envoi (UPL_TASMOTA)
        statut, texte = _poste(ip, f"/u2?fsz={len(donnees)}", "file", nom, donnees, delai_http, progression)
    except reseau as erreur:
        raise RuntimeError(f"{ETAPE_TELEVERSEMENT} : carte {ip} injoignable ou coupée ({erreur}){safeboot}") from None
    if _page_en_echec(statut, texte):
        raise RuntimeError(f"{ETAPE_TELEVERSEMENT} : refusé par la carte (HTTP {statut}) : {_resume(texte)}{safeboot}")
    rapporte({"etape": ETAPE_REDEMARRAGE, "pourcent": None, "detail": f"attente du retour de {ip}"})
    _attend_retour(ip, delai_retour, attente_min, sondage, delai_http)
    rapporte({"etape": ETAPE_VERIFICATION, "pourcent": None, "detail": f"Status 2 (avant : {avant[0]}, {avant[1]})"})
    try:
        apres = _version(ip, delai_http)
    except reseau as erreur:
        raise RuntimeError(f"{ETAPE_VERIFICATION} : Status 2 illisible après l'envoi ({erreur})") from None
    except ValueError as erreur:
        if _page_safeboot(ip, delai_http) is not None:
            raise RuntimeError(f"{ETAPE_VERIFICATION} : la carte est restée en safeboot : renvoyer un firmware "
                               f"par http://{ip}/up") from None
        raise RuntimeError(f"{ETAPE_VERIFICATION} : Status 2 illisible après l'envoi ({erreur})") from None
    if apres == avant:
        raise RuntimeError(f"{ETAPE_VERIFICATION} : firmware inchangé ({apres[0]}, compilé {apres[1]}) : "
                           "la carte n'a pas pris le nouveau firmware")
    if "safeboot" in str(apres[0]).lower():
        raise RuntimeError(f"{ETAPE_VERIFICATION} : la carte est restée en safeboot ({apres[0]})")
    rapporte({"etape": ETAPE_VERIFICATION, "pourcent": None, "detail": f"nouveau firmware : {apres[0]}, compilé {apres[1]}"})


def _resume(texte):
    """Texte d'une page Tasmota sans balises, raccourci (pour un message d'erreur)."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", texte)).strip()[:200]


# -- file system --------------------------------------------------------------------------------------

def _identite(texte):
    """(nom d'hote, topic MQTT) d'un _persist.json : serveur.hostname et serveur.mqtt.topic."""
    serveur = json.loads(texte).get("serveur") or {}
    return str(serveur.get("hostname") or ""), str((serveur.get("mqtt") or {}).get("topic") or "")


def verifie_identite(dossier_fs, persist_env, env):
    """L'image extraite porte-t-elle l'identite de l'env ? RuntimeError(ETAPE_IMAGE) sinon, avant tout envoi.

    Le 2026-10-26, un buildfs a construit l'image du P4 avec le dossier de la cuve (data_dir du lancement
    precedent) : l'OTA a pose sur le P4 l'autoexec et le persist de la cuve, et la relecture (carte = image) ne
    pouvait pas le voir. On compare le nom d'hote (sans casse) et le topic du _persist.json de l'image a ceux du
    persist de l'env au depot (`persist_env`). Sans persist de l'env au depot : rien a comparer, on le dit.
    Rend le detail a afficher.
    """
    if not persist_env or not Path(persist_env).is_file():
        return f"identité non contrôlée : pas de {PERSIST} de {env} au dépôt"
    image = Path(dossier_fs) / PERSIST
    if not image.is_file():
        raise RuntimeError(f"{ETAPE_IMAGE} : l'image n'a pas de {PERSIST} ; rien n'a été envoyé")
    try:
        hote, topic = _identite(image.read_text(encoding="utf-8"))
    except (ValueError, AttributeError) as erreur:
        raise RuntimeError(f"{ETAPE_IMAGE} : {PERSIST} de l'image illisible ({erreur}) ; rien n'a été envoyé") from None
    hote_env, topic_env = _identite(Path(persist_env).read_text(encoding="utf-8"))
    if hote.lower() != hote_env.lower() or topic != topic_env:
        raise RuntimeError(f"{ETAPE_IMAGE} : l'image porte l'identité de {hote or '?'} ({topic or '?'}), pas celle de "
                           f"{env} ({hote_env}, {topic_env}) ; rien n'a été envoyé. Lire dans le journal du buildfs "
                           f"la ligne copy_fs_image : quel dossier a servi ?")
    return f"identité vérifiée : {hote}, topic {topic}"


def joint_par_maitre(adresse, persist_env, env, rapporte, *, maitre=None, delai=8.0):
    """Esclave joint par le maitre (`<ip maitre>:<port>`) : redirection posee, puis identite de la carte verifiee.

    La table RgxPort du maitre se vide a son redemarrage (constat du 2026-10-26) : on lui fait poser ses
    redirections (RoutageRangeExtender, d'apres sa table de decouverte), puis on demande son nom d'hote a la
    carte jointe par `adresse` (Status 5). Une redirection absente ou vers une autre carte -> RuntimeError,
    rien n'est envoye. `maitre` : adresse HTTP du maitre (defaut : l'IP de `adresse`, port 80).
    """
    maitre = maitre or adresse.rsplit(":", 1)[0]
    rapporte({"etape": ETAPE_CONNEXION, "pourcent": None, "detail": f"redirection posée par le maître {maitre}"})
    try:
        reponse = _commande_repetee(maitre, "RoutageRangeExtender", delai)
    except (OSError, http.client.HTTPException) as erreur:
        raise RuntimeError(f"{ETAPE_CONNEXION} : maître {maitre} injoignable après {ESSAIS_MAITRE} essais ({erreur}) ; "
                           f"rien n'a été envoyé") from None
    if "RoutageRangeExtender" not in reponse:
        raise RuntimeError(f"{ETAPE_CONNEXION} : le maître {maitre} ne connaît pas RoutageRangeExtender (Berry arrêté ?) : "
                           f"{_resume(reponse)} ; rien n'a été envoyé")
    try:
        hote = str(json.loads(_commande_repetee(adresse, "Status 5", delai)).get("StatusNET", {}).get("Hostname") or "")
    except (OSError, http.client.HTTPException, ValueError, AttributeError) as erreur:
        raise RuntimeError(f"{ETAPE_CONNEXION} : aucune carte derrière {adresse} ({erreur}) : esclave hors ligne pour le "
                           f"maître (fiche Offline de sa découverte) ? rien n'a été envoyé") from None
    # Safeboot : pas de Status 5, on compare le DeviceName du titre de sa page a serveur.nom du persist.
    nom = None if hote else _page_safeboot(adresse, delai)
    if not persist_env or not Path(persist_env).is_file():
        return f"carte jointe : {hote or nom or '?'} (identité non contrôlée : pas de {PERSIST} de {env} au dépôt)"
    texte = Path(persist_env).read_text(encoding="utf-8")
    if nom is not None:
        attendu = str((json.loads(texte).get("serveur") or {}).get("nom") or "")
        if nom.lower() != attendu.lower():
            raise RuntimeError(f"{ETAPE_CONNEXION} : {adresse} mène à une carte en safeboot nommée {nom or '?'}, pas à "
                               f"{env} ({attendu}) ; rien n'a été envoyé")
        return f"carte jointe par le maître : {nom} (en safeboot)"
    attendu = _identite(texte)[0]
    if hote.lower() != attendu.lower():
        raise RuntimeError(f"{ETAPE_CONNEXION} : {adresse} mène à {hote or '?'}, pas à {env} ({attendu}) ; "
                           f"rien n'a été envoyé")
    return f"carte jointe par le maître : {hote}"


def coupe_sleep(maitre, delai=8.0):
    """`Sleep 0` sur le maitre le temps d'un envoi par sa redirection -> (valeur d'avant, fonction qui la remet).

    Mesure du 2026-10-28 (1 Mo vers la cuve par la redirection) : `Sleep 50` -> pauses du relais NAPT jusqu'a
    7,8 s, au-dela des 5 s ou le serveur web de l'esclave abandonne un envoi (HTTP_MAX_POST_WAIT) ; `Sleep 0` ->
    74 a 102 Ko/s, aucune pause. La fonction rendue remet la valeur et rend "" ou le message d'echec.
    """
    try:
        valeur = re.search(r'"Sleep"\D*(\d+)', _commande_repetee(maitre, "Sleep", delai))   # {"Sleep":{"50":{"Active":"50"}}}
        if valeur is None:
            raise ValueError("réponse de Sleep illisible")
        _commande_repetee(maitre, "Sleep 0", delai)
    except (OSError, http.client.HTTPException) as erreur:
        raise RuntimeError(f"{ETAPE_CONNEXION} : Sleep du maître {maitre} non coupé après {ESSAIS_MAITRE} essais ({erreur}) ; "
                           f"rien n'a été envoyé") from None
    except ValueError as erreur:
        raise RuntimeError(f"{ETAPE_CONNEXION} : Sleep du maître {maitre} non coupé ({erreur}) ; rien n'a été envoyé") from None
    valeur = valeur.group(1)

    def remet():
        try:
            _commande_repetee(maitre, f"Sleep {valeur}", delai)
            return ""
        except (OSError, http.client.HTTPException) as erreur:
            return f"Sleep {valeur} NON remis sur le maître {maitre} ({erreur}) : le remettre à la main"
    return valeur, remet


def extrait_image(image, dossier):
    """Copie dans `dossier` (cree) tous les fichiers de l'image LittleFS `image` ; rend leur nombre.

    `image` = .pio/build/<env>/littlefs.bin juste apres `pio run -t buildfs` (cible AlwaysBuild,
    builder/main.py:1761-1765 : l'image est reecrite a chaque buildfs). Montage EXPLICITE (mount=False
    puis mount()) : avec mount=True, littlefs-python formate en silence une image qu'il ne sait pas
    monter et rendrait un FS vide. Une image illisible avec les parametres du buildfs (vierge,
    tronquee, ou ecrite par post_esp32.py, dont le name_max differe) est donc refusee.
    """
    image, dossier = Path(image), Path(dossier)
    if not image.is_file():
        raise RuntimeError(f"{ETAPE_IMAGE} : {image} absent après la construction du FS (buildfs) ; "
                           "rien n'a été envoyé")
    donnees = image.read_bytes()
    if not donnees or len(donnees) % BLOC_IMAGE:
        raise RuntimeError(f"{ETAPE_IMAGE} : taille de {image.name} ({len(donnees)} octets) non multiple de "
                           f"{BLOC_IMAGE} : image tronquée ? rien n'a été envoyé")
    try:
        from littlefs import LittleFS, UserContext
    except ImportError:
        raise RuntimeError(f"{ETAPE_IMAGE} : module littlefs-python absent : lancer la page avec le Python "
                           "de PlatformIO (%USERPROFILE%\\.platformio\\penv\\Scripts\\python.exe)") from None
    try:
        fs = LittleFS(context=UserContext(buffer=bytearray(donnees)), block_count=len(donnees) // BLOC_IMAGE,
                      mount=False, **REGLAGES_IMAGE)
        fs.mount()
        contenus = {}
        for racine, _, fichiers in fs.walk("/"):
            for nom in fichiers:
                rel = (racine.rstrip("/") + "/" + nom).lstrip("/")
                with fs.open(rel, "rb") as f:
                    contenus[rel] = f.read()
    except Exception as erreur:                                 # LittleFSError et erreurs de structure
        raise RuntimeError(f"{ETAPE_IMAGE} : {image} illisible avec les paramètres du buildfs ({erreur!r}) ; "
                           "rien n'a été envoyé") from None
    base = dossier.resolve()
    cibles = {rel: (dossier / rel).resolve() for rel in contenus}
    refuses = [rel for rel, cible in cibles.items() if base not in cible.parents]   # « .. », chemin absolu
    if refuses:
        raise RuntimeError(f"{ETAPE_IMAGE} : chemin refusé dans l'image : {', '.join(refuses)} ; rien n'a été envoyé")
    for rel, cible in cibles.items():
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_bytes(contenus[rel])
    return len(contenus)


def _inventaire(dossier_fs, choix=None):
    """Fichiers relatifs (posix) a envoyer, persist en dernier, et dossiers a creer (parent d'abord).

    `choix` : sous-ensemble de ces fichiers (onglet « Fichiers », A15) ; None = tous, persist obligatoire.
    """
    if not dossier_fs.is_dir():
        raise RuntimeError(f"{ETAPE_ENVOI} : dossier {dossier_fs} absent (construction du FS manquante ?)")
    fichiers = sorted(p.relative_to(dossier_fs).as_posix() for p in dossier_fs.rglob("*") if p.is_file())
    if choix is not None:
        inconnus = sorted(set(choix) - set(fichiers))
        if inconnus or not choix:
            raise RuntimeError(f"{ETAPE_ENVOI} : " + (f"absents de l'image : {', '.join(inconnus)}" if inconnus
                               else "aucun fichier choisi") + " ; rien n'a été envoyé")
        fichiers = sorted(set(choix))
    elif PERSIST not in fichiers:
        raise RuntimeError(f"{ETAPE_ENVOI} : {PERSIST} absent de {dossier_fs}")
    # Persist en dernier : un echec en cours de route laisse a la carte son persist d'origine.
    fichiers = [f for f in fichiers if f != PERSIST] + ([PERSIST] if PERSIST in fichiers else [])
    # Chemin ecrit par Tasmota : <dossier courant> + "/" + <nom>, soit "//nom" a la racine.
    trop_longs = [f for f in fichiers if len(("/" if "/" in f else "//") + f) > LONGUEUR_MAX]
    if trop_longs:
        raise RuntimeError(f"{ETAPE_ENVOI} : chemin trop long pour Tasmota ({LONGUEUR_MAX} caractères) : "
                           + ", ".join(trop_longs))
    dossiers = set()
    for f in fichiers:
        parties = f.split("/")[:-1]
        dossiers.update("/" + "/".join(parties[:i]) for i in range(1, len(parties) + 1))
    return fichiers, sorted(dossiers, key=lambda d: (d.count("/"), d))


def _telecharge_persist(ip, delai):
    return _get(ip, "/ufsu?dir=0&download=/" + PERSIST, delai)


def _sauvegarde(env, contenu, sauvegardes):
    sauvegardes.mkdir(parents=True, exist_ok=True)
    base = f"{env}-{time.strftime('%Y%m%d-%H%M%S')}"
    chemin, n = sauvegardes / f"{base}.json", 1
    while chemin.exists():                                     # deux envois dans la meme seconde
        n += 1
        chemin = sauvegardes / f"{base}-{n}.json"
    chemin.write_bytes(contenu)
    return chemin


def envoie_fs_ota(env, ip, dossier_fs, sauvegardes, rapporte, *, delai_retour=90.0, attente_min=15.0,
                  sondage=2.0, delai_http=30.0, fichiers=None, recharger_berry=False, redemarrer=True):
    """Envoie tout `dossier_fs` a la carte (deroule du choix 10 de la spec).

    Onglet « Fichiers » (choix 24) : `fichiers` = sous-ensemble a envoyer (chemins relatifs de l'image). Le persist
    n'est sauvegarde, relu et recharge que s'il en fait partie. Apres l'envoi : `redemarrer` -> Restart 1 (Berry
    repart avec la carte) ; sinon `recharger_berry` -> BrRestart (machine Berry neuve, autoexec rejoue).
    """
    dossier_fs, sauvegardes = Path(dossier_fs), Path(sauvegardes)
    fichiers, dossiers = _inventaire(dossier_fs, fichiers)
    erreurs_reseau = (OSError, http.client.HTTPException)
    avec_persist = PERSIST in fichiers
    copie = None
    sauve = ""                                 # suffixe des messages d'erreur : ou retrouver le persist d'avant

    # 2. persist de la carte : sans lui, rien n'est envoye
    if avec_persist:
        rapporte({"etape": ETAPE_SAUVEGARDE, "pourcent": None, "detail": f"depuis {ip}"})
        try:
            ancien = _telecharge_persist(ip, delai_http)
        except erreurs_reseau as erreur:
            raise RuntimeError(f"{ETAPE_SAUVEGARDE} : impossible de télécharger {PERSIST} de {ip} ({erreur}) ; "
                               "rien n'a été envoyé") from None
        if not ancien.strip():
            raise RuntimeError(f"{ETAPE_SAUVEGARDE} : {PERSIST} de {ip} vide ; rien n'a été envoyé")
        try:
            json.loads(ancien)                 # une page HTML ou un persist tronque n'est pas une sauvegarde
        except ValueError as erreur:
            raise RuntimeError(f"{ETAPE_SAUVEGARDE} : {PERSIST} de {ip} n'est pas du JSON valide ({erreur}) : "
                               f"pas de sauvegarde possible ; rien n'a été envoyé") from None
        copie = _sauvegarde(env, ancien, sauvegardes)
        sauve = f" ; sauvegarde du persist : {copie}"

    # 3. dossiers puis fichiers
    etape, en_cours = ETAPE_DOSSIERS, ""
    try:
        for i, dossier in enumerate(dossiers, 1):
            en_cours = dossier
            rapporte({"etape": etape, "pourcent": i * 100 // len(dossiers), "detail": dossier})
            reponse = _commande(ip, f'Br import path path.mkdir("{dossier}")', delai_http)
            if "_error" in reponse:
                raise RuntimeError(f"{etape} : {dossier} : {reponse}{sauve}")
        etape = ETAPE_ENVOI
        # % des OCTETS envoyes, mis a jour a chaque morceau (A13) : au nombre de fichiers, il restait fige pendant
        # echarts.min.js.gz (368 Ko sur le P4, contre 10 a 40 Ko pour les autres) puis sautait.
        total = sum((dossier_fs / rel).stat().st_size for rel in fichiers) or 1
        faits, dernier = 0, [-1]
        for i, rel in enumerate(fichiers, 1):
            en_cours = rel
            detail = f"{i}/{len(fichiers)} {rel}"
            parent, _, nom = rel.rpartition("/")
            rapporte({"etape": etape, "pourcent": faits * 100 // total, "detail": detail})      # fichier annonce avant

            def progression(envoyes, _taille, detail=detail, faits=faits):
                pourcent = min(99, (faits + envoyes) * 100 // total)    # 100 : dernier fichier ACCEPTE seulement
                if pourcent != dernier[0]:                     # un evenement par point de %
                    dernier[0] = pourcent
                    rapporte({"etape": etape, "pourcent": pourcent, "detail": detail})

            # dossier courant de la carte : / puis <parent> (sur un dossier, download= ne telecharge pas)
            _get(ip, "/ufsd?dir=0" + (f"&download=/{urllib.parse.quote(parent)}" if parent else ""), delai_http)
            donnees = (dossier_fs / rel).read_bytes()
            statut, texte = _poste(ip, f"/ufsu?fsz={len(donnees)}", "ufsu", nom, donnees, delai_http, progression)
            if _page_en_echec(statut, texte):
                raise RuntimeError(f"{etape} : {rel} refusé par la carte (HTTP {statut}) : {_resume(texte)}{sauve}")
            faits += len(donnees)
        rapporte({"etape": etape, "pourcent": 100, "detail": f"{len(fichiers)}/{len(fichiers)} {fichiers[-1]}"
                  if fichiers else "aucun fichier"})
    except erreurs_reseau as erreur:
        # Tasmota ferme aussi sans repondre quand le dossier demande n'existe pas.
        raise RuntimeError(f"{etape} : {en_cours} : pas de réponse de la carte {ip} ({erreur}){sauve}") from None

    if avec_persist:
        # 4. relecture, comparaison exacte des octets, AVANT le rechargement
        attendu = (dossier_fs / PERSIST).read_bytes()
        _compare(ip, attendu, ETAPE_RELECTURE, copie, delai_http, rapporte)

        # 5. rechargement des globales Berry : TOUJOURS si le persist part, il est en RAM et le System#Save d'un
        # redemarrage ecrirait l'ancien par-dessus le nouveau
        rapporte({"etape": ETAPE_RECHARGEMENT, "pourcent": None, "detail": "persist.load()"})
        try:
            reponse = _commande(ip, BR_RECHARGE, delai_http)
        except erreurs_reseau as erreur:
            raise RuntimeError(f"{ETAPE_RECHARGEMENT} : {ip} ne répond pas ({erreur}){sauve}") from None
        if "_error" in reponse:
            raise RuntimeError(f"{ETAPE_RECHARGEMENT} : {reponse}{sauve}")

    # 6. redemarrage et verification, ou Berry seul relance
    if redemarrer:
        rapporte({"etape": ETAPE_REDEMARRAGE, "pourcent": None, "detail": f"Restart 1, attente du retour de {ip}"})
        try:
            _commande(ip, "Restart 1", delai_http)
        except erreurs_reseau as erreur:
            raise RuntimeError(f"{ETAPE_REDEMARRAGE} : Restart 1 sans réponse ({erreur})") from None
        _attend_retour(ip, delai_retour, attente_min, sondage, delai_http)
        if avec_persist:
            _verifie_apres_redemarrage(ip, attendu, copie, delai_http, rapporte)
    elif recharger_berry:
        rapporte({"etape": ETAPE_BERRY, "pourcent": None, "detail": "BrRestart"})
        try:
            reponse = _commande(ip, "BrRestart", delai_http)
        except erreurs_reseau as erreur:
            raise RuntimeError(f"{ETAPE_BERRY} : {ip} ne répond pas ({erreur}){sauve}") from None
        if "restarted" not in reponse:
            raise RuntimeError(f"{ETAPE_BERRY} : réponse inattendue : {_resume(reponse)}{sauve}")


def _compare(ip, attendu, etape, copie, delai, rapporte):
    """Relit le persist de la carte, comparaison exacte des octets ; difference -> erreur, pas de restauration."""
    rapporte({"etape": etape, "pourcent": None, "detail": PERSIST})
    try:
        lu = _telecharge_persist(ip, delai)
    except (OSError, http.client.HTTPException) as erreur:
        raise RuntimeError(f"{etape} : impossible de relire {PERSIST} ({erreur}) ; "
                           f"sauvegarde du persist : {copie}") from None
    if lu != attendu:
        raise RuntimeError(f"{etape} : le {PERSIST} de la carte diffère de celui envoyé ({len(lu)} octets "
                           f"au lieu de {len(attendu)}) ; pas de restauration automatique, "
                           f"sauvegarde du persist : {copie}")



def _verifie_apres_redemarrage(ip, attendu, copie, delai, rapporte):
    """Relecture apres Restart : contenu JSON compare, une difference n'est qu'un AVERTISSEMENT.

    Au Restart, l'evenement System#Save reecrit le persist par json.dump de Berry (JSON compact, ordre
    des cles non garanti) : les octets changent meme quand le contenu est le bon. Les fichiers sont
    deja envoyes et la carte est revenue : l'env n'echoue pas, la page affiche l'avertissement.
    """
    rapporte({"etape": ETAPE_VERIFICATION, "pourcent": None, "detail": PERSIST})
    try:
        lu = _telecharge_persist(ip, delai)
    except (OSError, http.client.HTTPException) as erreur:
        motif = f"{PERSIST} illisible après le redémarrage ({erreur})"
    else:
        try:
            if json.loads(lu) == json.loads(attendu):
                rapporte({"etape": ETAPE_VERIFICATION, "pourcent": None,
                          "detail": f"{PERSIST} identique après le redémarrage (contenu JSON)"})
                return
            motif = f"le {PERSIST} relu après le redémarrage diffère (contenu JSON) de celui envoyé"
        except ValueError as erreur:
            motif = f"{PERSIST} relu après le redémarrage n'est pas du JSON valide ({erreur})"
    rapporte({"etape": ETAPE_VERIFICATION, "pourcent": None,
              "detail": f"AVERTISSEMENT : {motif} ; sauvegarde du persist d'avant : {copie}"})
