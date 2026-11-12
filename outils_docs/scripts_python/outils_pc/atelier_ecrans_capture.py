"""Capture d'ecran d'une carte LVGL (atelier des ecrans) : `Br lv.screenshot()`, telechargement, effacement.

`capture(ip, get) -> bytes` : octets du BMP ecrit par la carte, tels quels ; RuntimeError (message en francais) sinon.
`get(ip, chemin, delai) -> bytes` : build_ota_http._get, ou une carte simulee (banc test_atelier_ecrans_capture.py).

Firmware lu (rien n'y est modifie) :
- xdrv_52_3_berry_lvgl.ino::lv0_screenshot : nil si LVGL n'est pas demarre ; sinon ecrit `/screenshot-<utc>.bmp`
  (BMP 16 bits, en-tete de 0x42 octets, taille totale declaree aux octets 2..6) sur `dfsp` et rend ce nom ;
- xdrv_52_9_berry.ino::CmndBrRun : {"Br": "<valeur en texte>"} ou {"Br": "[type] message"} ;
- xdrv_50_filesystem.ino::UfsDirectory : `/ufsd?dir=0` remet `dfsp` sur la flash AVANT toute autre lecture, puis
  `download=` et `delete=` agissent sur ce meme `dfsp`. D'ou le premier appel `/ufsd?dir=0` : ecriture, telechargement
  et effacement visent le meme systeme de fichiers, carte SD presente ou non.
shortcut: une page /ufsd ouverte ailleurs entre deux appels peut deplacer dfsp ; a revoir si une capture echoue ainsi.
"""

import json
import re
import struct
import urllib.parse

DELAI = 5                 # page /ufsd, effacement
DELAI_BR = 30             # ecriture de ~1,2 Mo (1024 x 600 x 2 o) sur la flash
DELAI_IMAGE = 90          # telechargement de ~1,2 Mo par le serveur web de la carte
NOM = re.compile(r"/screenshot-\d{1,12}\.bmp")
RESTE = "un /screenshot-*.bmp est peut-etre reste sur la carte (a effacer par Outils > Gestion des fichiers)"


def _bmp_valide(octets):
    return len(octets) >= 6 and octets[:2] == b"BM" and len(octets) >= struct.unpack_from("<I", octets, 2)[0]


def capture(ip, get):
    try:
        get(ip, "/ufsd?dir=0", DELAI)
    except Exception as e:                      # OSError, HTTPException : meme refus
        raise RuntimeError(f"carte injoignable ({ip}) : {e}") from None
    try:
        reponse = json.loads(get(ip, "/cm?cmnd=" + urllib.parse.quote("Br lv.screenshot()", safe=""), DELAI_BR)
                             .decode("utf-8", "replace"))
        nom = reponse.get("Br") if isinstance(reponse, dict) else None
    except Exception as e:
        raise RuntimeError(f"Br lv.screenshot() sans reponse lisible : {e} ; {RESTE}") from None
    if nom == "nil":
        raise RuntimeError("LVGL n'est pas demarre sur la carte (lv.screenshot() rend nil) : aucune capture")
    if not isinstance(nom, str) or not NOM.fullmatch(nom):
        raise RuntimeError(f"reponse inattendue de Br lv.screenshot() : {str(nom)[:200]!r} ; firmware sans LVGL ? {RESTE}")
    erreur = None
    try:
        image = get(ip, "/ufsd?dir=0&download=" + nom, DELAI_IMAGE)
        if not _bmp_valide(image):
            erreur = f"{nom} illisible ou tronque ({len(image)} octets) : systeme de fichiers de la carte plein ?"
    except Exception as e:
        erreur = f"telechargement de {nom} interrompu : {e}"
    try:
        get(ip, "/ufsd?dir=0&delete=" + nom, DELAI)
    except Exception as e:
        raise RuntimeError(f"{erreur + ' ; ' if erreur else ''}{nom} n'a pas pu etre efface de la carte ({e}) : "
                           "a effacer par Outils > Gestion des fichiers") from None
    if erreur:
        raise RuntimeError(erreur)
    return image
