"""Envoi du firmware d'une carte Tasmota par le reseau (OTA), pour la page Build : envoie_firmware_ota.

  envoie_firmware_ota(env, ip, dossier_build, rapporte)
      .pio/build/<env>/firmware.bin.gz (s'il n'est pas plus ancien que firmware.bin), sinon
      firmware.bin, par POST /u2 (champ `file`), comme le navigateur sur la page /up de Tasmota
      (bascule en safeboot comprise, voir plus bas) ; puis attente du retour de la carte et preuve
      par `Status 2` (version + date de compilation changees).

Pourquoi la page envoie le firmware elle-meme (spec, choix 7 revise) : ota-files-uploader.py lance
depuis le pre-script passerait AVANT post_esp32.py, qui remet esptool dans UPLOADCMD a chaque edition
des liens. Les scripts de build/ ne sont donc pas touches.

Ce que fait Tasmota (tasmota/tasmota_xdrv_driver/xdrv_01_9_webserver.ino) :
  - POST /u2 n'ecrit rien si la page /up n'a pas ete ouverte avant (Web.upload_file_type remis a
    UPL_NONE apres chaque envoi, xdrv_01_9 l.3469 et l.3551) ET repond quand meme « Successful » :
    d'ou le GET /up avant chaque envoi du firmware ;
  - partition OTA unique + safeboot (tables partitions/esp32_partition_app3904k_fs11584k.csv et
    app2752k_fs448k.csv du fork) : l'appli ne peut pas s'ecraser elle-meme. La page /up sert alors
    HTTP_FORM_RST_UPG_FCT (xdrv_01_9 l.382-395, choisi l.3420) dont le script upl() / fct()
    (html_uncompressed/HTTP_HEAD_LAST_SCRIPT32.h l.28-64) fait, pour une image non compressee
    (1er octet 0xE9) : GET /u4?u4=fct&api= en boucle (« false » : la carte redemarre en safeboot,
    nouvel essai 6 s plus tard ; pas de reponse : nouvel essai 2 s plus tard ; « true » : en safeboot)
    puis envoi du formulaire. HandleSwitchBootPartition (l.3845-3896) repond « none » s'il n'y a pas
    de partition unique (aucun effet), et arme l'envoi (UPL_TASMOTA) quand il ne redemarre pas.
    Une image compressee (0x1F) part directement, comme dans le navigateur.

Erreurs : RuntimeError("<étape> : <motif>"). `rapporte` recoit {"etape", "pourcent", "detail"}.
"""

import http.client
import json
import time
from pathlib import Path

from build_ota_http import (ETAPE_REDEMARRAGE, ETAPE_SAFEBOOT, ETAPE_TELEVERSEMENT, ETAPE_VERIFICATION, _attend_retour,
                            _commande, _get, _page_en_echec, _page_safeboot, _poste, _resume)


def _version(ip, delai):
    """(Version, BuildDateTime) de `Status 2` ; leve OSError / HTTPException / ValueError."""
    fwr = json.loads(_commande(ip, "Status 2", delai)).get("StatusFWR") or {}
    if not fwr.get("Version"):
        raise ValueError("pas de StatusFWR.Version dans la réponse")
    return fwr.get("Version"), fwr.get("BuildDateTime")


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
