"""Envoi par le reseau (OTA) du file system d'une carte Tasmota, pour la page Build.

Fonctions appelees par build_serie.Serie (et build_fichiers pour l'onglet Fichiers) apres le `pio run -t buildfs` :

  extrait_image(image, dossier)
      fichiers de .pio/build/<env>/littlefs.bin, l'image que `pio run -t buildfs` vient d'ecrire (celle
      qu'un uploadfs par cable flasherait), copies dans un dossier temporaire. PAS littlefs_data : ce
      dossier est rempli par post_esp32.py apres chaque edition des liens, jamais vide, et ne recoit
      data/fs, data/json, data/sd que pour certaines cibles (spec, choix 10.1 revise).
  verifie_identite(dossier_fs, persist_env, env)
      l'image porte-t-elle le nom d'hote et le topic de l'env ? Sinon rien n'est envoye.
  envoie_fs_ota(env, ip, dossier_fs, sauvegardes, rapporte)
      tout ce dossier (ou les `fichiers=` choisis dans l'onglet Fichiers) par /ufsu, sous-dossiers compris
      (deroule du choix 10 de docs/superpowers/specs/2026-10-24-page-build-televersement-design.md).

Firmware : build_ota_firmware.py ; esclave joint par le maitre : build_ota_maitre.py ; transport HTTP et noms
des etapes : build_ota_http.py.

Ce que fait Tasmota, et que ce module suit (tasmota/tasmota_xdrv_driver/xdrv_50_filesystem.ino) :
  - un fichier envoye par /ufsu va dans <dossier courant>/<nom> (UfsUploadFileOpen). Le dossier
    courant est remis a / par chaque GET /ufsd et devient <d> avec `download=<d>` si <d> est un
    dossier. `dir=0` vise la flash (dir=1 = carte SD, que la page de fichiers a pu choisir) ;
  - aucune commande ne cree de dossier : on passe par Berry, `path.mkdir` (qui agit sur la flash) ;
  - chemin complet limite a 49 caracteres (UFS_FILENAME_SIZE = 50) : verifie avant tout envoi.

Erreurs : RuntimeError("<étape> : <motif>"). `rapporte` recoit {"etape", "pourcent", "detail"}.
littlefs-python pour lire l'image (present dans le penv de PlatformIO, qui s'en sert pour l'ecrire).
"""

import http.client
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from build_ota_http import (ETAPE_BERRY, ETAPE_DOSSIERS, ETAPE_ENVOI, ETAPE_IMAGE, ETAPE_RECHARGEMENT,
                            ETAPE_REDEMARRAGE, ETAPE_RELECTURE, ETAPE_SAUVEGARDE, ETAPE_VERIFICATION,
                            _attend_retour, _commande, _get, _page_en_echec, _poste, _resume)

PERSIST = "_persist.json"
# Spec, choix 10.5 : sans ce rechargement, l'evenement System#Save du Restart recopie les globales
# (encore l'ancien contenu) dans le persist et ecrase celui qu'on vient d'envoyer (lecon du 2026-10-18).
BR_RECHARGE = ("Br import persist persist.load() serveur = persist.serveur diverses = persist.diverses "
               "modules = persist.modules drivers = persist.drivers")
LONGUEUR_MAX = 49                    # UFS_FILENAME_SIZE - 1 (xdrv_50_filesystem.ino:90)
# Parametres de l'image ecrite par `pio run -t buildfs` : build_fs_image de
# ~/.platformio/platforms/espressif32/builder/main.py:549-560 (block_size = FS_BLOCK = 0x1000, l.478 ;
# block_count = FS_SIZE // block_size = taille de l'image, qui est tout le tampon). disk_version n'est
# pas passe : au montage, littlefs accepte toute version 2.x de mineure <= la sienne (2.0 et 2.1).
BLOC_IMAGE = 4096
REGLAGES_IMAGE = {"block_size": BLOC_IMAGE, "read_size": 1, "prog_size": 1, "cache_size": BLOC_IMAGE,
                  "lookahead_size": 32, "block_cycles": 500, "name_max": 64}


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
