"""Transport HTTP vers une carte Tasmota pour les envois OTA de la page Build (build_ota_firmware, build_ota_fs,
build_ota_maitre), et les noms des etapes rapportees au suivi.

Ce que fait Tasmota, et que ce module suit (lu dans tasmota/tasmota_xdrv_driver/) :
  - toute route autre que / exige `Referer: http://<ip>/` (SetOption128 0), sinon la connexion est
    fermee SANS reponse ; un fichier absent a telecharger aussi (xdrv_50 UfsDirectory) ;
  - les reponses d'envoi sont toujours HTTP 200 : l'echec se lit dans la page (« Failed », « Échoué ») ;
  - le safeboot ne connait aucune commande : seule sa page d'accueil le dit (_page_safeboot).
Adresse `ip` : IP, ou `IP:port` pour un esclave joint par la redirection du maitre (range extender).
stdlib seulement : urllib.request pour les GET, http.client pour les POST envoyes par morceaux.
"""

import http.client
import re
import time
import urllib.parse
import urllib.request
import uuid

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

ECHECS_PAGE = ("Failed", "Échoué", "denied")
MORCEAU = 8192
SANS_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # carte sur le reseau local


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


def _resume(texte):
    """Texte d'une page Tasmota sans balises, raccourci (pour un message d'erreur)."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", texte)).strip()[:200]
