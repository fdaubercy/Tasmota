"""Envoi par le reseau (OTA) du firmware et du file system d'une carte Tasmota, pour la page Build.

Deux fonctions, appelees par build_serie.Serie apres le `pio run` qui produit ce qu'elles envoient :

  envoie_firmware_ota(env, ip, dossier_build, rapporte)
      .pio/build/<env>/firmware.bin.gz, sinon firmware.bin, par POST /u2 (champ `file`), protocole de
      pio-tools/espupload.py ; puis attente du retour de la carte (`/cm?cmnd=Status`).
  envoie_fs_ota(env, ip, dossier_fs, sauvegardes, rapporte)
      tout .pio/build/<env>/littlefs_data par /ufsu, sous-dossiers compris (deroule du choix 10 de
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
  - un fichier envoye par /ufsu va dans <dossier courant>/<nom> (UfsUploadFileOpen). Le dossier
    courant est remis a / par chaque GET /ufsd et devient <d> avec `download=<d>` si <d> est un
    dossier. `dir=0` vise la flash (dir=1 = carte SD, que la page de fichiers a pu choisir) ;
  - aucune commande ne cree de dossier : on passe par Berry, `path.mkdir` (qui agit sur la flash) ;
  - chemin complet limite a 49 caracteres (UFS_FILENAME_SIZE = 50) : verifie avant tout envoi.

Erreurs : RuntimeError("<étape> : <motif>"). `rapporte` recoit {"etape", "pourcent", "detail"}.
stdlib seule (urllib.request pour les GET, http.client pour les POST envoyes par morceaux).
"""

import http.client
import re
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ETAPE_TELEVERSEMENT = "Téléversement"
ETAPE_SAUVEGARDE = "Sauvegarde du persist"
ETAPE_DOSSIERS = "Création des dossiers"
ETAPE_ENVOI = "Envoi des fichiers"
ETAPE_RELECTURE = "Relecture du persist"
ETAPE_RECHARGEMENT = "Rechargement du persist"
ETAPE_REDEMARRAGE = "Redémarrage"
ETAPE_VERIFICATION = "Vérification après redémarrage"

PERSIST = "_persist.json"
# Spec, choix 10.5 : sans ce rechargement, l'evenement System#Save du Restart recopie les globales
# (encore l'ancien contenu) dans le persist et ecrase celui qu'on vient d'envoyer (lecon du 2026-10-18).
BR_RECHARGE = ("Br import persist persist.load() serveur = persist.serveur diverses = persist.diverses "
               "modules = persist.modules drivers = persist.drivers")
ECHECS_PAGE = ("Failed", "Échoué", "denied")
LONGUEUR_MAX = 49                    # UFS_FILENAME_SIZE - 1 (xdrv_50_filesystem.ino:90)
MORCEAU = 8192
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

def envoie_firmware_ota(env, ip, dossier_build, rapporte, *, delai_retour=90.0, attente_min=15.0,
                        sondage=2.0, delai_http=30.0):
    """Envoie firmware.bin.gz (sinon firmware.bin) de `dossier_build` par /u2, puis attend le retour."""
    dossier_build = Path(dossier_build)
    fichier = next((f for f in (dossier_build / "firmware.bin.gz", dossier_build / "firmware.bin") if f.is_file()),
                   None)
    if fichier is None:
        raise RuntimeError(f"{ETAPE_TELEVERSEMENT} : ni firmware.bin.gz ni firmware.bin dans {dossier_build}")
    donnees = fichier.read_bytes()
    nom = env + fichier.name[len("firmware"):]                  # <env>.bin(.gz), comme espupload.py
    dernier = [-1]

    def progression(envoyes, total):
        pourcent = envoyes * 100 // total
        if pourcent != dernier[0]:                             # un evenement par point de %
            dernier[0] = pourcent
            rapporte({"etape": ETAPE_TELEVERSEMENT, "pourcent": pourcent, "detail": f"{nom} vers {ip}"})

    rapporte({"etape": ETAPE_TELEVERSEMENT, "pourcent": 0, "detail": f"{nom} vers {ip}"})
    try:
        _get(ip, "/up", delai_http)                            # arme l'envoi (UPL_TASMOTA)
        statut, texte = _poste(ip, f"/u2?fsz={len(donnees)}", "file", nom, donnees, delai_http, progression)
    except (OSError, http.client.HTTPException) as erreur:
        raise RuntimeError(f"{ETAPE_TELEVERSEMENT} : carte {ip} injoignable ou coupée ({erreur})") from None
    if _page_en_echec(statut, texte):
        raise RuntimeError(f"{ETAPE_TELEVERSEMENT} : refusé par la carte (HTTP {statut}) : {_resume(texte)}")
    rapporte({"etape": ETAPE_REDEMARRAGE, "pourcent": None, "detail": f"attente du retour de {ip}"})
    _attend_retour(ip, delai_retour, attente_min, sondage, delai_http)


def _resume(texte):
    """Texte d'une page Tasmota sans balises, raccourci (pour un message d'erreur)."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", texte)).strip()[:200]


# -- file system --------------------------------------------------------------------------------------

def _inventaire(dossier_fs):
    """Fichiers relatifs (posix) a envoyer, persist en dernier, et dossiers a creer (parent d'abord)."""
    if not dossier_fs.is_dir():
        raise RuntimeError(f"{ETAPE_ENVOI} : dossier {dossier_fs} absent (construction du FS manquante ?)")
    fichiers = sorted(p.relative_to(dossier_fs).as_posix() for p in dossier_fs.rglob("*") if p.is_file())
    if PERSIST not in fichiers:
        raise RuntimeError(f"{ETAPE_ENVOI} : {PERSIST} absent de {dossier_fs}")
    # Persist en dernier : un echec en cours de route laisse a la carte son persist d'origine.
    fichiers = [f for f in fichiers if f != PERSIST] + [PERSIST]
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
                  sondage=2.0, delai_http=30.0):
    """Envoie tout `dossier_fs` a la carte (deroule du choix 10 de la spec)."""
    dossier_fs, sauvegardes = Path(dossier_fs), Path(sauvegardes)
    fichiers, dossiers = _inventaire(dossier_fs)
    erreurs_reseau = (OSError, http.client.HTTPException)

    # 2. persist de la carte : sans lui, rien n'est envoye
    rapporte({"etape": ETAPE_SAUVEGARDE, "pourcent": None, "detail": f"depuis {ip}"})
    try:
        ancien = _telecharge_persist(ip, delai_http)
    except erreurs_reseau as erreur:
        raise RuntimeError(f"{ETAPE_SAUVEGARDE} : impossible de télécharger {PERSIST} de {ip} ({erreur}) ; "
                           "rien n'a été envoyé") from None
    if not ancien.strip():
        raise RuntimeError(f"{ETAPE_SAUVEGARDE} : {PERSIST} de {ip} vide ; rien n'a été envoyé")
    copie = _sauvegarde(env, ancien, sauvegardes)

    # 3. dossiers puis fichiers
    etape, en_cours = ETAPE_DOSSIERS, ""
    try:
        for i, dossier in enumerate(dossiers, 1):
            en_cours = dossier
            rapporte({"etape": etape, "pourcent": i * 100 // len(dossiers), "detail": dossier})
            reponse = _commande(ip, f'Br import path path.mkdir("{dossier}")', delai_http)
            if "_error" in reponse:
                raise RuntimeError(f"{etape} : {dossier} : {reponse} ; sauvegarde du persist : {copie}")
        etape = ETAPE_ENVOI
        for i, rel in enumerate(fichiers, 1):
            en_cours = rel
            parent, _, nom = rel.rpartition("/")
            # dossier courant de la carte : / puis <parent> (sur un dossier, download= ne telecharge pas)
            _get(ip, "/ufsd?dir=0" + (f"&download=/{urllib.parse.quote(parent)}" if parent else ""), delai_http)
            donnees = (dossier_fs / rel).read_bytes()
            statut, texte = _poste(ip, f"/ufsu?fsz={len(donnees)}", "ufsu", nom, donnees, delai_http)
            if _page_en_echec(statut, texte):
                raise RuntimeError(f"{etape} : {rel} refusé par la carte (HTTP {statut}) : {_resume(texte)} ; "
                                   f"sauvegarde du persist : {copie}")
            rapporte({"etape": etape, "pourcent": i * 100 // len(fichiers), "detail": f"{i}/{len(fichiers)} {rel}"})
    except erreurs_reseau as erreur:
        # Tasmota ferme aussi sans repondre quand le dossier demande n'existe pas.
        raise RuntimeError(f"{etape} : {en_cours} : pas de réponse de la carte {ip} ({erreur}) ; "
                           f"sauvegarde du persist : {copie}") from None

    # 4. relecture, comparaison exacte des octets, AVANT le rechargement
    attendu = (dossier_fs / PERSIST).read_bytes()
    _compare(ip, attendu, ETAPE_RELECTURE, copie, delai_http, rapporte)

    # 5. rechargement des globales Berry, 6. redemarrage et verification
    rapporte({"etape": ETAPE_RECHARGEMENT, "pourcent": None, "detail": "persist.load()"})
    try:
        reponse = _commande(ip, BR_RECHARGE, delai_http)
    except erreurs_reseau as erreur:
        raise RuntimeError(f"{ETAPE_RECHARGEMENT} : {ip} ne répond pas ({erreur}) ; "
                           f"sauvegarde du persist : {copie}") from None
    if "_error" in reponse:
        raise RuntimeError(f"{ETAPE_RECHARGEMENT} : {reponse} ; sauvegarde du persist : {copie}")
    rapporte({"etape": ETAPE_REDEMARRAGE, "pourcent": None, "detail": f"Restart 1, attente du retour de {ip}"})
    try:
        _commande(ip, "Restart 1", delai_http)
    except erreurs_reseau as erreur:
        raise RuntimeError(f"{ETAPE_REDEMARRAGE} : Restart 1 sans réponse ({erreur})") from None
    _attend_retour(ip, delai_retour, attente_min, sondage, delai_http)
    _compare(ip, attendu, ETAPE_VERIFICATION, copie, delai_http, rapporte)


def _compare(ip, attendu, etape, copie, delai, rapporte):
    """Relit le persist de la carte ; different de `attendu` -> erreur (pas de restauration)."""
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
