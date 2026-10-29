"""Banc de build_ota_fs (envoi du firmware par /u2 et du file system par /ufsu) sur une carte simulee.

Code de sortie 0 = vert. La carte simulee (build_ota_carte_simulee.Carte) est un serveur HTTP sur
127.0.0.1 (port libre) qui imite Tasmota : Referer exige, /ufsd, /ufsu, /up, /u2, /u4 (safeboot),
/cm (Br, Restart 1, Status, Status 2). Aucune vraie carte n'est contactee.
Les images LittleFS d'essai sont de VRAIES images, construites par littlefs-python (penv de PlatformIO)
avec les parametres de build_fs_image (~/.platformio/platforms/espressif32/builder/main.py:549-591).
"""

import json
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

import build_ota_fs as bo
from build_ota_carte_simulee import ANCIEN_PERSIST, Carte

ECHECS = []
NOUVEAU_PERSIST = b'{"serveur": {"nouveau": true}, "diverses": {}}'
BR_RECHARGE = ("Br import persist persist.load() serveur = persist.serveur diverses = persist.diverses "
               "modules = persist.modules drivers = persist.drivers")
RAPIDE = {"delai_retour": 5.0, "attente_min": 0.0, "sondage": 0.05}
FICHIERS_IMAGE = {"autoexec.be": b"print(1)", "json/graphiques.json": b"{}", "sd/js/graphiques.js": b"var x = 1;" * 50,
                  "sd/css/graphiques.css": b"body{}", "_persist.json": NOUVEAU_PERSIST}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def fs_essai(t, persist=NOUVEAU_PERSIST):
    """littlefs_data d'essai : racine, json/, sd/js/, sd/css/."""
    d = Path(t) / "littlefs_data"
    for rel, contenu in {"autoexec.be": b"print(1)", "json/graphiques.json": b"{}",
                         "sd/js/graphiques.js": b"var x = 1;" * 50, "sd/css/graphiques.css": b"body{}"}.items():
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_bytes(contenu)
    if persist is not None:
        (d / "_persist.json").write_bytes(persist)
    sauvegardes = Path(t) / "persist"
    sauvegardes.mkdir()
    return d, sauvegardes


def fabrique_image(chemin, fichiers, blocs=64, post_esp32=False):
    """Ecrit une vraie image LittleFS de `fichiers` ({chemin relatif: octets}) dans `chemin`.

    Par defaut, comme `pio run -t buildfs` : build_fs_image de builder/main.py:549-591 (block_size =
    FS_BLOCK 4096, name_max 64, disk_version 2.1, format() puis mount()). `post_esp32=True` : comme
    l'image ecrite apres l'edition des liens par pio-tools/post_esp32.py:239-245 (name_max par defaut
    de littlefs-python, disk_version 2.0).
    """
    from littlefs import LittleFS
    if post_esp32:
        fs = LittleFS(block_size=4096, block_count=blocs, disk_version=0x00020000, mount=True)
    else:
        fs = LittleFS(block_size=4096, block_count=blocs, read_size=1, prog_size=1, cache_size=4096,
                      lookahead_size=32, block_cycles=500, name_max=64, disk_version=0x00020001, mount=False)
        fs.format()
        fs.mount()
    for rel, contenu in fichiers.items():
        parent = rel.rpartition("/")[0]
        if parent:
            fs.makedirs(parent, exist_ok=True)
        with fs.open(rel, "wb") as f:
            f.write(contenu)
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    Path(chemin).write_bytes(bytes(fs.context.buffer))


def arbre(dossier):
    """{chemin relatif posix: octets} de tous les fichiers de `dossier` ({} s'il n'existe pas)."""
    dossier = Path(dossier)
    if not dossier.is_dir():
        return {}
    return {p.relative_to(dossier).as_posix(): p.read_bytes() for p in dossier.rglob("*") if p.is_file()}


def envoie_fs(carte, t, **options):
    """Lance envoie_fs_ota ; renvoie (message d'erreur ou None, rapports, dossier des sauvegardes)."""
    d, sauvegardes = fs_essai(t)
    rapports = []
    try:
        bo.envoie_fs_ota("tasmota32-essai", carte.ip, d, sauvegardes, rapports.append, **{**RAPIDE, **options})
        return None, rapports, sauvegardes
    except RuntimeError as erreur:
        return str(erreur), rapports, sauvegardes


def genre(methode, chemin):
    """Requete du journal -> etape du deroule (pour verifier l'ordre)."""
    cmnd = urllib.parse.unquote(chemin.split("cmnd=", 1)[1]) if "cmnd=" in chemin else ""
    if "download=/_persist.json" in chemin:
        return "persist"
    if "path.mkdir" in cmnd:
        return "dossier"
    if chemin.startswith(("/ufsd", "/ufsu")):
        return "envoi"
    if cmnd.startswith("Br import persist"):
        return "rechargement"
    return {"Restart 1": "restart", "Status": "status", "BrRestart": "brrestart"}.get(cmnd, chemin)


def compacte(liste):
    return [x for i, x in enumerate(liste) if i == 0 or x != liste[i - 1]]


# -- tests du file system -----------------------------------------------------------------------------

def test_ota_fs_ordre():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        erreur, _, _ = envoie_fs(carte, t)
        verifie(erreur, None, "ota_fs_ordre : envoi sans erreur")
        verifie(compacte([genre(m, c) for m, c in carte.requetes()]),
                ["persist", "dossier", "envoi", "persist", "rechargement", "restart", "status", "persist"],
                "ota_fs_ordre : sauvegarde -> dossiers -> envois -> relecture -> Br -> Restart 1 -> Status -> relecture")
        br = [urllib.parse.unquote(c.split("cmnd=", 1)[1]) for _, c in carte.requetes("cmnd=Br%20import%20persist")]
        verifie(br, [BR_RECHARGE], "ota_fs_ordre : commande Berry exacte de la spec (choix 10.5), URL-encodee")
        verifie(carte.flash["/_persist.json"], NOUVEAU_PERSIST, "ota_fs_ordre : persist de la carte remplace")
        carte.ferme()


def test_ota_fs_partiel():
    """Onglet « Fichiers » (A15, choix 24) : seuls les fichiers choisis partent ; persist non choisi -> ni sauvegarde,
    ni relecture, ni rechargement ; options apres envoi respectees."""
    cas = [  # (fichiers, options, deroule attendu)
        (["json/graphiques.json", "autoexec.be"], {}, ["dossier", "envoi", "restart", "status"]),
        (["autoexec.be"], {"redemarrer": False, "recharger_berry": True}, ["envoi", "brrestart"]),
        (["autoexec.be"], {"redemarrer": False}, ["envoi"]),
        (["_persist.json", "autoexec.be"], {"redemarrer": False, "recharger_berry": True},
         ["persist", "envoi", "persist", "rechargement", "brrestart"]),
        (["_persist.json"], {}, ["persist", "envoi", "persist", "rechargement", "restart", "status", "persist"]),
    ]
    for fichiers, options, attendu in cas:
        with tempfile.TemporaryDirectory() as t:
            carte = Carte()
            erreur, _, sauvegardes = envoie_fs(carte, t, fichiers=fichiers, **options)
            nom = f"ota_fs_partiel {fichiers} {options}"
            verifie(erreur, None, f"{nom} : envoi sans erreur")
            verifie(compacte([genre(m, c) for m, c in carte.requetes()]), attendu, f"{nom} : deroule")
            verifie(sorted(k for k in carte.flash if k != "/_persist.json"),
                    sorted("/" + f for f in fichiers if f != "_persist.json"), f"{nom} : seuls les fichiers choisis ecrits")
            avec = "_persist.json" in fichiers
            verifie((carte.flash["/_persist.json"] == NOUVEAU_PERSIST, len(list(sauvegardes.iterdir()))),
                    (avec, 1 if avec else 0), f"{nom} : persist remplace et sauvegarde seulement s'il est choisi")
            carte.ferme()
    for fichiers, motif in ((["absent.be"], "absents de l'image : absent.be"), ([], "aucun fichier choisi")):
        with tempfile.TemporaryDirectory() as t:
            carte = Carte()
            erreur, _, _ = envoie_fs(carte, t, fichiers=fichiers)
            verifie((motif in (erreur or ""), carte.requetes()), (True, []),
                    f"ota_fs_partiel : {fichiers} -> refus, carte non contactee")
            carte.ferme()


def test_ota_fs_sauvegarde():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        _, _, sauvegardes = envoie_fs(carte, t)
        fichiers = sorted(p.name for p in sauvegardes.iterdir())
        verifie([bool(re.fullmatch(r"tasmota32-essai-\d{8}-\d{6}\.json", f)) for f in fichiers], [True],
                "ota_fs_sauvegarde : persist/<env>-<AAAAMMJJ-HHMMSS>.json")
        verifie((sauvegardes / fichiers[0]).read_bytes() if fichiers else None, ANCIEN_PERSIST,
                "ota_fs_sauvegarde : contenu = persist de la carte AVANT l'envoi")
        carte.ferme()


def test_ota_fs_persist_injoignable():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        carte.persist_injoignable = True
        erreur, _, sauvegardes = envoie_fs(carte, t)
        verifie((erreur or "").startswith("Sauvegarde du persist : "), True,
                "ota_fs_persist_injoignable : erreur 'Sauvegarde du persist'")
        verifie([c for m, c in carte.requetes() if m == "POST" or "mkdir" in c or "Restart" in c], [],
                "ota_fs_persist_injoignable : aucun /ufsu, aucun dossier cree, pas de Restart")
        verifie(list(sauvegardes.iterdir()), [], "ota_fs_persist_injoignable : aucune sauvegarde ecrite")
        carte.ferme()
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(persist=None)                  # carte sans _persist.json : meme refus
        erreur, _, _ = envoie_fs(carte, t)
        verifie((erreur or "").startswith("Sauvegarde du persist : "), True,
                "ota_fs_persist_injoignable : persist absent de la carte -> meme erreur")
        carte.ferme()


def test_ota_fs_relecture_differente():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        carte.altere_persist = True
        erreur, _, sauvegardes = envoie_fs(carte, t)
        sauvegarde = next(iter(sauvegardes.iterdir()), None)
        verifie((erreur or "").startswith("Relecture du persist : "), True,
                "ota_fs_relecture_differente : erreur 'Relecture du persist'")
        verifie(bool(sauvegarde) and str(sauvegarde) in (erreur or ""), True,
                "ota_fs_relecture_differente : chemin de la sauvegarde dans le message")
        verifie([c for _, c in carte.requetes() if "persist.load" in urllib.parse.unquote(c) or "Restart" in c], [],
                "ota_fs_relecture_differente : ni rechargement ni Restart")
        verifie(carte.flash["/_persist.json"] != ANCIEN_PERSIST, True,
                "ota_fs_relecture_differente : pas de restauration automatique")
        carte.ferme()


def test_ota_fs_sous_dossiers():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(carte_sd=True)                 # carte SD choisie dans la page : on vise la flash
        erreur, _, _ = envoie_fs(carte, t)
        verifie(erreur, None, "ota_fs_sous_dossiers : envoi sans erreur")
        verifie(sorted(carte.dossiers), ["/", "/json", "/sd", "/sd/css", "/sd/js"],
                "ota_fs_sous_dossiers : json/, sd/, sd/js/, sd/css/ crees (parent avant enfant)")
        verifie((carte.flash.get("/sd/js/graphiques.js"), carte.flash.get("/json/graphiques.json"),
                 carte.flash.get("/autoexec.be")), (b"var x = 1;" * 50, b"{}", b"print(1)"),
                "ota_fs_sous_dossiers : fichiers ecrits dans leur dossier, dans la flash")
        verifie(carte.sd, {}, "ota_fs_sous_dossiers : rien sur la carte SD")
        carte.ferme()
    # temoin : la carte simulee refuse un fichier dont le dossier n'existe pas
    carte = Carte()
    carte.ufs_path = "/absent"
    verifie("Failed" in bo._poste(carte.ip, "/ufsu?fsz=1", "ufsu", "x.js", b"x", 5.0)[1], True,
            "ota_fs_sous_dossiers : temoin, dossier absent -> 'Failed' sur la carte simulee")
    carte.ferme()


def test_ota_fs_referer():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        envoie_fs(carte, t)
        verifie({r for _, _, r in carte.journal}, {f"http://{carte.ip}/"},
                "ota_fs_referer : toutes les requetes portent Referer: http://<ip>/")
        verifie(len(carte.journal) > 10, True, "ota_fs_referer : le journal couvre tout le deroule")
        # temoin : sans Referer, la carte simulee ne repond pas (comme Tasmota)
        try:
            urllib.request.urlopen(f"http://{carte.ip}/cm?cmnd=Status", timeout=3).read()
            sans = "repondu"
        except Exception:
            sans = "muette"
        verifie(sans, "muette", "ota_fs_referer : temoin, requete sans Referer -> pas de reponse")
        carte.ferme()


def test_ota_fs_echec_ufsu():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        carte.echec_fichier = "graphiques.js"
        erreur, _, _ = envoie_fs(carte, t)
        verifie((erreur or "").startswith("Envoi des fichiers : ") and "sd/js/graphiques.js" in erreur, True,
                "ota_fs_echec_ufsu : page 'Failed' -> erreur qui nomme le fichier")
        verifie([c for _, c in carte.requetes("Restart")], [], "ota_fs_echec_ufsu : pas de Restart")
        verifie(carte.flash["/_persist.json"], ANCIEN_PERSIST,
                "ota_fs_echec_ufsu : persist envoye en dernier, donc intact apres l'echec")
        carte.ferme()


def test_ota_fs_pas_de_retour():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(coupure=None)
        debut = time.monotonic()
        erreur, _, _ = envoie_fs(carte, t, delai_retour=1.0)
        verifie((erreur or "").startswith("Redémarrage : "), True,
                "ota_fs_pas_de_retour : pas de reponse apres Restart 1 -> erreur 'Redemarrage'")
        verifie(time.monotonic() - debut < 6, True, "ota_fs_pas_de_retour : delai reduit par parametre respecte")
        carte.ferme()


def test_ota_fs_attente_retour():
    """Juste apres Restart 1 la carte repond encore : ce Status-la ne vaut pas retour."""
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(coupure=0.3)
        carte.retard = 0.6
        debut = time.monotonic()
        erreur, _, _ = envoie_fs(carte, t, attente_min=20.0)
        duree = time.monotonic() - debut
        verifie(erreur, None, "ota_fs_attente_retour : envoi sans erreur")
        verifie(duree > 0.9, True, "ota_fs_attente_retour : pas de retour accepte avant la coupure de la carte")
        verifie(duree < 10, True, "ota_fs_attente_retour : carte vue muette puis revenue -> pas d'attente de attente_min")
        carte.ferme()


def test_ota_fs_persist_reformate():
    """Au Restart, System#Save reecrit le persist par json.dump : seul le contenu decode compte."""
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        carte.apres_redemarrage = lambda b: json.dumps(dict(reversed(list(json.loads(b).items()))),
                                                       separators=(",", ":")).encode()
        erreur, rapports, _ = envoie_fs(carte, t)
        verifie(carte.flash["/_persist.json"] != NOUVEAU_PERSIST, True,
                "ota_fs_persist_reformate : la carte simulee a bien reecrit le persist (autres octets)")
        verifie(erreur, None, "ota_fs_persist_reformate : reformate apres redemarrage -> succes")
        verifie([r["detail"] for r in rapports if "AVERTISSEMENT" in str(r.get("detail"))], [],
                "ota_fs_persist_reformate : meme contenu JSON -> pas d'avertissement")
        carte.ferme()
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        carte.apres_redemarrage = lambda b: ANCIEN_PERSIST           # globales anciennes resauvees
        erreur, rapports, sauvegardes = envoie_fs(carte, t)
        avert = [r for r in rapports if "AVERTISSEMENT" in str(r.get("detail"))]
        sauvegarde = next(iter(sauvegardes.iterdir()), None)
        verifie(erreur, None, "ota_fs_persist_reformate : contenu different apres redemarrage -> pas d'echec")
        verifie((len(avert), bool(avert) and avert[0]["etape"]), (1, "Vérification après redémarrage"),
                "ota_fs_persist_reformate : un avertissement a l'etape de verification")
        verifie(bool(avert) and str(sauvegarde) in avert[0]["detail"], True,
                "ota_fs_persist_reformate : avertissement avec le chemin de la sauvegarde")
        carte.ferme()


def test_ota_fs_progression():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        _, rapports, _ = envoie_fs(carte, t)
        envois = [r for r in rapports if r.get("etape") == "Envoi des fichiers"]
        rangs = list(dict.fromkeys(r["detail"].split(" ")[0] for r in envois))
        verifie(rangs, ["1/5", "2/5", "3/5", "4/5", "5/5"],
                "ota_fs_progression : chaque fichier annonce AVANT son envoi, n/total, dans l'ordre")
        pourcents = [r["pourcent"] for r in envois]
        verifie((pourcents[:1], pourcents[-1:], all(a <= b for a, b in zip(pourcents, pourcents[1:]))), ([0], [100], True),
                f"ota_fs_progression : % des octets, de 0 a 100 sans reculer ({pourcents})")
        verifie(envois[-1]["detail"] if envois else "", "5/5 _persist.json",
                "ota_fs_progression : detail = n/total chemin (persist en dernier)")
        verifie("sd/js/graphiques.js" in [r["detail"].split(" ", 1)[1] for r in envois], True,
                "ota_fs_progression : chemin relatif avec ses dossiers")
        carte.ferme()


def test_ota_fs_progression_octets():
    """A13 : % des octets, mis a jour PENDANT un gros fichier (echarts.min.js.gz = 368 Ko sur le P4, autres 10-40 Ko)."""
    with tempfile.TemporaryDirectory() as t:
        d = Path(t) / "fs"
        (d / "sd" / "js").mkdir(parents=True)
        (d / "sd" / "js" / "gros.js.gz").write_bytes(b"x" * (12 * bo.MORCEAU))
        (d / "autoexec.be").write_bytes(b"print(1)" * 100)
        (d / "_persist.json").write_bytes(NOUVEAU_PERSIST)
        carte, rapports = Carte(), []
        try:
            bo.envoie_fs_ota("tasmota32-essai", carte.ip, d, Path(t) / "persist", rapports.append, **RAPIDE)
            erreur = None
        except RuntimeError as e:
            erreur = str(e)
        verifie(erreur, None, "ota_fs_progression_octets : envoi sans erreur")
        gros = [r["pourcent"] for r in rapports if r.get("etape") == "Envoi des fichiers" and "gros.js.gz" in r["detail"]]
        verifie(len(set(gros)) >= 8, True, f"ota_fs_progression_octets : le % avance pendant le gros fichier ({gros})")
        verifie(max(gros, default=0) >= 90, True, "ota_fs_progression_octets : le gros fichier pese presque tout le total")
        carte.ferme()


def test_image_extraite():
    """C1 : le contenu envoye est celui de littlefs.bin (l'image du buildfs), pas littlefs_data."""
    with tempfile.TemporaryDirectory() as t:
        image = Path(t) / "littlefs.bin"
        fabrique_image(image, FICHIERS_IMAGE)
        dossier = Path(t) / "extrait"
        bo.extrait_image(image, dossier)
        verifie(arbre(dossier), FICHIERS_IMAGE, "image_extraite : fichiers et sous-dossiers de l'image, octet pour octet")
        carte = Carte()
        try:
            bo.envoie_fs_ota("tasmota32-essai", carte.ip, dossier, Path(t) / "persist", lambda r: None, **RAPIDE)
            erreur = None
        except RuntimeError as e:
            erreur = str(e)
        verifie(erreur, None, "image_extraite : envoi a la carte simulee sans erreur")
        verifie({k.lstrip("/"): v for k, v in carte.flash.items()}, FICHIERS_IMAGE,
                "image_extraite : la carte simulee a recu exactement le contenu de l'image")
        carte.ferme()


def test_image_illisible():
    with tempfile.TemporaryDirectory() as t:
        def essai(image, libelle):
            dossier = Path(t) / ("extrait-" + image.stem)
            try:
                bo.extrait_image(image, dossier)
                erreur = ""
            except RuntimeError as e:
                erreur = str(e)
            verifie((erreur.startswith(getattr(bo, "ETAPE_IMAGE", "?") + " : "), arbre(dossier)), (True, {}), libelle)
            return erreur

        erreur = essai(Path(t) / "absent.bin", "image_illisible : littlefs.bin absent -> erreur, rien d'extrait")
        verifie("absent" in erreur, True, "image_illisible : le message dit que l'image est absente")
        zeros = Path(t) / "zeros.bin"
        zeros.write_bytes(bytes(4096 * 16))
        essai(zeros, "image_illisible : image vierge -> erreur (pas de format() silencieux)")
        tronquee = Path(t) / "tronquee.bin"
        fabrique_image(tronquee, FICHIERS_IMAGE)
        tronquee.write_bytes(tronquee.read_bytes()[:-100])
        essai(tronquee, "image_illisible : taille non multiple de 4096 -> erreur")
        post = Path(t) / "post.bin"
        fabrique_image(post, FICHIERS_IMAGE, post_esp32=True)
        essai(post, "image_illisible : image de post_esp32 (name_max 255, pas celle du buildfs) -> erreur")
        # temoin : avec mount=True, littlefs-python formate en silence une image qu'il ne sait pas monter
        from littlefs import LittleFS, UserContext
        fs = LittleFS(context=UserContext(buffer=bytearray(post.read_bytes())), block_size=4096,
                      block_count=post.stat().st_size // 4096, name_max=64, mount=True)
        verifie(list(fs.walk("/")), [("/", [], [])],
                "image_illisible : temoin, mount=True rend un FS VIDE au lieu d'une erreur (d'ou mount() explicite)")


def test_ota_fs_persist_invalide():
    """I3 : un persist telecharge qui n'est pas du JSON (page HTML, octets tronques) : rien n'est envoye."""
    for persist in (b"<html>Gestion du systeme de fichiers</html>", b'{"serveur": {"ancien'):
        with tempfile.TemporaryDirectory() as t:
            carte = Carte(persist=persist)
            erreur, _, _ = envoie_fs(carte, t)
            verifie(((erreur or "").startswith("Sauvegarde du persist : "), "JSON" in (erreur or "")), (True, True),
                    f"ota_fs_persist_invalide : {persist[:12]!r}... -> erreur 'Sauvegarde du persist' (JSON)")
            verifie([c for m, c in carte.requetes() if m == "POST" or "mkdir" in c or "Restart" in c], [],
                    "ota_fs_persist_invalide : aucun /ufsu, aucun dossier cree, pas de Restart")
            carte.ferme()


# -- tests du firmware --------------------------------------------------------------------------------

def build_essai(t, gz=False, magique=b"\xe9"):
    d = Path(t) / "build"
    d.mkdir()
    (d / "firmware.bin").write_bytes(magique + bytes(range(256)) * 400)
    if gz:
        (d / "firmware.bin.gz").write_bytes(b"\x1f\x8b" + b"z" * 5000)
    return d


def envoie_firmware(carte, dossier, **options):
    rapports = []
    try:
        bo.envoie_firmware_ota("tasmota32-essai", carte.ip, dossier, rapports.append, **{**RAPIDE, **options})
        return None, rapports
    except RuntimeError as erreur:
        return str(erreur), rapports


def test_ota_firmware_envoi():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        d = build_essai(t)
        erreur, rapports = envoie_firmware(carte, d)
        verifie(erreur, None, "ota_firmware_envoi : envoi sans erreur")
        verifie(carte.firmware, ("tasmota32-essai.bin", (d / "firmware.bin").read_bytes()),
                "ota_firmware_envoi : firmware.bin recu tel quel (GET /up avant POST /u2)")
        verifie(compacte(etiquettes(carte)), ["Status 2", "/u4", "/up", "/u2", "Status", "Status 2"],
                "ota_firmware_envoi : version -> /u4 (none) -> /up -> POST /u2 -> retour -> version")
        televersement = [r["pourcent"] for r in rapports if r.get("etape") == "Téléversement"]
        verifie((len(televersement) > 3, televersement == sorted(televersement), televersement[-1:]),
                (True, True, [100]), "ota_firmware_envoi : % = octets envoyes / taille, croissant jusqu'a 100")
        verifie(any(c.startswith(f"/u2?fsz={(d / 'firmware.bin').stat().st_size}") for _, c in carte.requetes()),
                True, "ota_firmware_envoi : fsz = taille du fichier")
        carte.ferme()


def etiquettes(carte):
    """Requetes de la carte : chemin sans parametres, ou commande /cm decodee."""
    return [urllib.parse.unquote(c.split("cmnd=", 1)[1]) if "cmnd=" in c else c.split("?")[0]
            for _, c in carte.requetes()]


def test_ota_firmware_safeboot():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(safeboot=True)
        d = build_essai(t)
        erreur, rapports = envoie_firmware(carte, d)
        verifie(erreur, None, "ota_firmware_safeboot : envoi sans erreur")
        verifie(compacte(etiquettes(carte)), ["Status 2", "/u4", "/up", "/u2", "Status", "Status 2"],
                "ota_firmware_safeboot : Status 2 -> /u4 false (bascule) ... /u4 true -> /up -> /u2 -> retour -> Status 2")
        verifie(etiquettes(carte).count("/u4") >= 2, True,
                "ota_firmware_safeboot : /u4 redemande apres la bascule jusqu'a 'true'")
        verifie((carte.firmware or ("", b""))[1] == (d / "firmware.bin").read_bytes() and carte.mode == "app", True,
                "ota_firmware_safeboot : firmware ecrit depuis le safeboot, carte revenue sur l'appli")
        verifie(any(r.get("etape") == "Bascule en safeboot" for r in rapports), True,
                "ota_firmware_safeboot : etape de bascule rapportee")
        carte.ferme()
    # temoin : sur la carte simulee, sans bascule, l'appli refuse son propre ecrasement
    carte = Carte(safeboot=True)
    bo._get(carte.ip, "/up", 5.0)
    verifie("Failed" in bo._poste(carte.ip, "/u2?fsz=3", "file", "x.bin", b"\xe9xx", 5.0)[1], True,
            "ota_firmware_safeboot : temoin, POST /u2 sans bascule -> 'Failed' (partition unique)")
    carte.ferme()


def test_ota_firmware_sans_safeboot():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(safeboot=False)
        erreur, rapports = envoie_firmware(carte, build_essai(t))
        verifie(erreur, None, "ota_firmware_sans_safeboot : envoi sans erreur")
        verifie((etiquettes(carte).count("/u4"), carte.mode), (1, "app"),
                "ota_firmware_sans_safeboot : /u4 repond 'none', un seul appel, pas de bascule")
        verifie(any(r.get("etape") == "Bascule en safeboot" for r in rapports), False,
                "ota_firmware_sans_safeboot : pas d'etape de bascule")
        carte.ferme()


def test_ota_firmware_inchange():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(safeboot=True)
        carte.inchange = True
        erreur, _ = envoie_firmware(carte, build_essai(t))
        verifie((erreur or "").startswith("Vérification après redémarrage : ") and "inchangé" in erreur, True,
                "ota_firmware_inchange : Status 2 identique avant/apres -> echec firmware inchange")
        carte.ferme()
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(safeboot=True)
        carte.reste_en_safeboot = True
        erreur, _ = envoie_firmware(carte, build_essai(t))
        verifie((erreur or "").startswith("Vérification après redémarrage : ") and "safeboot" in erreur, True,
                "ota_firmware_inchange : carte restee en safeboot apres l'envoi -> echec")
        carte.ferme()


def test_ota_firmware_deja_en_safeboot():
    """Envoi coupe (A11, 2026-10-28) : carte laissee en safeboot, qui ne connait pas Status 2 -> l'envoi se relance."""
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(safeboot=True)
        carte.safeboot_reel, carte.mode = True, "safeboot"
        d = build_essai(t)
        erreur, rapports = envoie_firmware(carte, d)
        verifie(erreur, None, "ota_firmware_deja_en_safeboot : Status 2 inconnu + page SAFEBOOT -> envoi sans erreur")
        verifie(compacte(etiquettes(carte)), ["Status 2", "/", "/u4", "/up", "/u2", "Status", "Status 2"],
                "ota_firmware_deja_en_safeboot : Status 2 -> page d'accueil -> /u4 true -> /up -> /u2 -> retour -> Status 2")
        verifie(((carte.firmware or ("", b""))[1] == (d / "firmware.bin").read_bytes(), carte.mode), (True, "app"),
                "ota_firmware_deja_en_safeboot : firmware ecrit, carte revenue sur l'appli")
        verifie(any(r.get("etape") == "Bascule en safeboot" for r in rapports), False,
                "ota_firmware_deja_en_safeboot : deja en safeboot, pas de bascule")
        carte.ferme()
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(safeboot=True)
        carte.safeboot_reel, carte.mode, carte.reste_en_safeboot = True, "safeboot", True
        erreur, _ = envoie_firmware(carte, build_essai(t))
        verifie("restée en safeboot : renvoyer un firmware" in (erreur or ""), True,
                "ota_firmware_deja_en_safeboot : toujours en safeboot apres l'envoi -> dit, pas « Status 2 illisible »")
        carte.ferme()
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(safeboot=True)                 # temoin : Status 2 inconnu hors safeboot -> refus, rien envoye
        carte.commande = lambda h, cmnd: carte.repond(h, '{"Command":"Unknown"}', "application/json")
        erreur, _ = envoie_firmware(carte, build_essai(t))
        verifie(("Status 2 illisible" in (erreur or ""), carte.firmware), (True, None),
                "ota_firmware_deja_en_safeboot : temoin, Status 2 inconnu sans page SAFEBOOT -> refus, rien envoye")
        carte.ferme()


def test_coupe_sleep():
    """A11 : Sleep 0 sur le maitre le temps de l'envoi (pauses du NAPT a Sleep 50), valeur d'avant remise."""
    maitre = Carte()
    try:
        valeur, remet = bo.coupe_sleep(maitre.ip, delai=2)
        verifie((valeur, maitre.sleeps), ("50", [0]), "coupe_sleep : valeur d'avant lue, Sleep 0 pose")
        verifie((remet(), maitre.sleeps), ("", [0, 50]), "coupe_sleep : remet() repose la valeur d'avant")
        valeur, remet = bo.coupe_sleep(maitre.ip, delai=2)
        maitre.ferme()
        verifie("NON remis" in remet(), True, "coupe_sleep : maitre perdu -> remet() rend le message, sans lever")
        try:
            bo.coupe_sleep(maitre.ip, delai=2)
            verifie("leve", "RuntimeError", "coupe_sleep : maitre injoignable -> RuntimeError")
        except RuntimeError as e:
            verifie("rien n'a été envoyé" in str(e), True, "coupe_sleep : maitre injoignable -> RuntimeError, rien envoye")
    finally:
        maitre.ferme()


def test_maitre_lent():
    """Liaison du maitre irreguliere (2026-10-29) : commande sans reponse rejouee, ESSAIS_MAITRE fois au plus."""
    maitre, esclave = Carte(), Carte()
    maitre.maitre = True
    vraie, muettes = maitre.commande, [0]

    def lente(h, cmnd):
        if muettes[0] > 0:
            muettes[0] -= 1
            time.sleep(0.8)                          # au-dela du delai de 0,3 s : le client abandonne
            return None
        return vraie(h, cmnd)
    maitre.commande = lente
    try:
        muettes[0] = 2
        valeur, remet = bo.coupe_sleep(maitre.ip, delai=0.3)
        verifie((valeur, maitre.sleeps), ("50", [0]), "maitre_lent : 2 requetes sans reponse -> Sleep lu et coupe quand meme")
        muettes[0] = 2
        verifie((remet(), maitre.sleeps), ("", [0, 50]), "maitre_lent : remet() rejoue aussi")
        muettes[0] = bo.ESSAIS_MAITRE
        try:
            bo.coupe_sleep(maitre.ip, delai=0.3)
            verifie("leve", "RuntimeError", "maitre_lent : toujours muet -> RuntimeError")
        except RuntimeError as e:
            verifie((f"{bo.ESSAIS_MAITRE} essais" in str(e), "rien n'a été envoyé" in str(e)), (True, True),
                    "maitre_lent : toujours muet -> refus qui dit le nombre d'essais, rien envoye")
        time.sleep(1)                                # laisse finir les requetes abandonnees
        muettes[0] = 2
        r = bo.joint_par_maitre(esclave.ip, None, "cuve", lambda _: None, maitre=maitre.ip, delai=0.3)
        verifie("carte jointe" in r, True, "maitre_lent : RoutageRangeExtender rejoue -> carte jointe")
    finally:
        maitre.ferme()
        esclave.ferme()


def test_ota_firmware_echec_en_safeboot():
    """I4 : bascule en safeboot faite, puis /u2 refuse : le message dit que la carte est restee en safeboot."""
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(safeboot=True)
        carte.echec_u2 = True
        erreur, _ = envoie_firmware(carte, build_essai(t))
        verifie((carte.mode, (erreur or "").startswith("Téléversement : ")), ("safeboot", True),
                "ota_firmware_echec_en_safeboot : carte en safeboot, envoi refuse -> erreur 'Televersement'")
        verifie(f"carte restée en safeboot : renvoyer un firmware par http://{carte.ip}/up" in (erreur or ""), True,
                "ota_firmware_echec_en_safeboot : le message dit comment sortir du safeboot")
        carte.ferme()
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(safeboot=False)                # temoin : sans bascule, pas de mention du safeboot
        carte.echec_u2 = True
        erreur, _ = envoie_firmware(carte, build_essai(t))
        verifie(((erreur or "").startswith("Téléversement : "), "safeboot" in (erreur or "")), (True, False),
                "ota_firmware_echec_en_safeboot : temoin, pas de bascule -> pas de mention du safeboot")
        carte.ferme()


def test_ota_firmware_referer():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        envoie_firmware(carte, build_essai(t))
        verifie(({r for _, _, r in carte.journal}, len(carte.journal) >= 3), ({f"http://{carte.ip}/"}, True),
                "ota_firmware_referer : toutes les requetes portent Referer: http://<ip>/")
        carte.ferme()


def test_ota_firmware_gz_prefere():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        d = build_essai(t, gz=True)
        envoie_firmware(carte, d)
        verifie(carte.firmware, ("tasmota32-essai.bin.gz", (d / "firmware.bin.gz").read_bytes()),
                "ota_firmware_gz_prefere : firmware.bin.gz envoye de preference")
        verifie("/u4" in etiquettes(carte), False,
                "ota_firmware_gz_prefere : image compressee -> pas de /u4 (comme upl() du navigateur)")
        carte.ferme()


def test_ota_firmware_gz_perime():
    """M5 : un firmware.bin.gz plus ancien que firmware.bin n'est pas envoye ; s'il est a jour, il l'est."""
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        d = build_essai(t, gz=True)
        vieux = time.time() - 3600
        os.utime(d / "firmware.bin.gz", (vieux, vieux))
        envoie_firmware(carte, d)
        recu = carte.firmware or ("", b"")
        verifie((recu[0], recu[1] == (d / "firmware.bin").read_bytes()), ("tasmota32-essai.bin", True),
                "ota_firmware_gz_perime : .gz plus ancien que firmware.bin -> firmware.bin envoye")
        carte.ferme()


def test_ota_firmware_echec():
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        erreur, _ = envoie_firmware(carte, build_essai(t, magique=b"\x00"))
        verifie((erreur or "").startswith("Téléversement : "), True,
                "ota_firmware_echec : page 'Failed' (signature invalide) -> erreur 'Televersement'")
        verifie([e for e in etiquettes(carte) if e == "Status"], [],
                "ota_firmware_echec : pas d'attente de retour apres un echec")
        carte.ferme()
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        vide = Path(t) / "vide"
        vide.mkdir()
        erreur, _ = envoie_firmware(carte, vide)
        verifie(((erreur or "").startswith("Téléversement : "), carte.journal), (True, []),
                "ota_firmware_echec : firmware absent -> erreur, carte non contactee")
        carte.ferme()
    with tempfile.TemporaryDirectory() as t:
        carte = Carte(coupure=None)
        erreur, _ = envoie_firmware(carte, build_essai(t), delai_retour=1.0)
        verifie((erreur or "").startswith("Redémarrage : "), True,
                "ota_firmware_echec : carte pas revenue -> erreur 'Redemarrage'")
        carte.ferme()
    with tempfile.TemporaryDirectory() as t:
        carte = Carte()
        carte.serveur.shutdown()
        carte.serveur.server_close()                 # carte injoignable
        erreur, _ = envoie_firmware(carte, build_essai(t), delai_http=2.0)
        verifie((erreur or "").startswith("Téléversement : "), True,
                "ota_firmware_echec : carte injoignable -> erreur 'Televersement'")


def persist_carte(hote, topic):
    return json.dumps({"serveur": {"hostname": hote, "mqtt": {"topic": topic}}, "diverses": {}}).encode("utf-8")


def test_identite_image():
    """L'image porte-t-elle l'identite de l'env ? (P4 avec le FS de la cuve le 2026-10-26)"""
    with tempfile.TemporaryDirectory() as t:
        image, env_p = Path(t) / "image", Path(t) / "env" / "_persist.json"
        image.mkdir()
        env_p.parent.mkdir()
        env_p.write_bytes(persist_carte("SERVEUR-GARAGE", "garage"))

        def essai(contenu_image):
            if contenu_image is None:
                (image / "_persist.json").unlink(missing_ok=True)
            else:
                (image / "_persist.json").write_bytes(contenu_image)
            try:
                return "ok", bo.verifie_identite(image, env_p, "tasmota32p4-garage-serveur-modbus")
            except RuntimeError as e:
                return "refus", str(e)

        r = essai(persist_carte("SERVEUR-GARAGE", "garage"))
        verifie((r[0], "SERVEUR-GARAGE" in r[1]), ("ok", True), "identite : meme nom d'hote et topic -> acceptee, dite")
        verifie(essai(persist_carte("serveur-garage", "garage"))[0], "ok", "identite : nom d'hote sans casse")
        r = essai(persist_carte("CAPTEURS-CUVE", "jardin/cuve"))
        verifie((r[0], r[1].startswith(bo.ETAPE_IMAGE), "CAPTEURS-CUVE" in r[1], "SERVEUR-GARAGE" in r[1],
                 "copy_fs_image" in r[1]), ("refus", True, True, True, True),
                "identite : image de la cuve pour le P4 -> refus qui nomme les deux identites et le journal a lire")
        verifie(essai(persist_carte("SERVEUR-GARAGE", "jardin/cuve"))[0], "refus", "identite : topic different -> refus")
        verifie(essai(None)[0], "refus", "identite : image sans _persist.json -> refus")
        verifie(essai(b"{pas du json")[0], "refus", "identite : _persist.json de l'image illisible -> refus")
        env_p.unlink()
        r = essai(persist_carte("CAPTEURS-CUVE", "jardin/cuve"))
        verifie((r[0], "non contrôlée" in r[1]), ("ok", True), "identite : pas de persist de l'env au depot -> non controlee, dit")


def test_par_maitre():
    """A11 : redirection posee par le maitre (RoutageRangeExtender), puis nom d'hote de la carte jointe verifie."""
    maitre, esclave = Carte(), Carte()
    maitre.maitre = True
    try:
        with tempfile.TemporaryDirectory() as t:
            env_p = Path(t) / "_persist.json"
            env_p.write_bytes(persist_carte("capteurs-cuve", "jardin/cuve"))
            etapes = []

            def essai(persist=env_p):
                etapes.clear()
                try:
                    return "ok", bo.joint_par_maitre(esclave.ip, persist, "cuve", etapes.append, maitre=maitre.ip, delai=2)
                except RuntimeError as e:
                    return "refus", str(e)

            r = essai()
            verifie((r[0], "CAPTEURS-CUVE" in r[1], etapes[0]["etape"]), ("ok", True, bo.ETAPE_CONNEXION),
                    "par_maitre : meme nom d'hote (sans casse) -> accepte, carte jointe dite")
            verifie([c for _, c, _ in maitre.journal], ["/cm?cmnd=RoutageRangeExtender"],
                    "par_maitre : le maitre pose ses redirections (RoutageRangeExtender)")
            verifie([c for _, c, _ in esclave.journal], ["/cm?cmnd=Status%205"], "par_maitre : puis Status 5 a la carte jointe")
            esclave.hostname = "RIDEAU-GARAGE"
            r = essai()
            verifie((r[0], "RIDEAU-GARAGE" in r[1], "capteurs-cuve" in r[1]), ("refus", True, True),
                    "par_maitre : autre carte derriere le port -> refus qui nomme les deux")
            r = essai(None)
            verifie((r[0], "non contrôlée" in r[1]), ("ok", True), "par_maitre : pas de persist au depot -> non controlee, dit")
            esclave.safeboot_reel, esclave.mode = True, "safeboot"   # envoi precedent coupe : Status 5 inconnu
            env_p.write_text(json.dumps({"serveur": {"nom": "capteurs de cuve", "hostname": "CAPTEURS-CUVE"}}), encoding="utf-8")
            r = essai()
            verifie((r[0], "Capteurs de Cuve" in r[1], "safeboot" in r[1]), ("ok", True, True),
                    "par_maitre : carte en safeboot -> nom de sa page = serveur.nom (sans casse), accepte et dit")
            esclave.nom = "Rideau du Garage"
            r = essai()
            verifie((r[0], "Rideau du Garage" in r[1]), ("refus", True), "par_maitre : autre carte en safeboot -> refus")
            esclave.safeboot_reel, esclave.mode = False, "app"
            maitre.maitre = False
            r = essai()
            verifie((r[0], "Berry" in r[1]), ("refus", True), "par_maitre : maitre sans RoutageRangeExtender -> refus")
            maitre.maitre = True
            esclave.ferme()
            r = essai()
            verifie((r[0], "aucune carte" in r[1]), ("refus", True), "par_maitre : rien derriere le port -> refus")
            maitre.ferme()
            r = essai()
            verifie((r[0], "injoignable" in r[1]), ("refus", True), "par_maitre : maitre eteint -> refus")
    finally:
        maitre.ferme()
        esclave.ferme()


def principal():
    for test in (test_identite_image, test_par_maitre, test_coupe_sleep, test_maitre_lent,test_ota_firmware_deja_en_safeboot, test_ota_fs_ordre, test_ota_fs_partiel, test_ota_fs_sauvegarde, test_ota_fs_persist_injoignable,
                 test_ota_fs_relecture_differente, test_ota_fs_sous_dossiers, test_ota_fs_referer,
                 test_ota_fs_echec_ufsu, test_ota_fs_pas_de_retour, test_ota_fs_attente_retour,
                 test_ota_fs_persist_reformate, test_ota_fs_progression, test_ota_fs_progression_octets,
                 test_ota_fs_persist_invalide,
                 test_image_extraite, test_image_illisible, test_ota_firmware_echec_en_safeboot,
                 test_ota_firmware_gz_perime,
                 test_ota_firmware_envoi, test_ota_firmware_safeboot, test_ota_firmware_sans_safeboot,
                 test_ota_firmware_inchange, test_ota_firmware_referer, test_ota_firmware_gz_prefere,
                 test_ota_firmware_echec):
        try:
            test()
        except Exception as erreur:                  # un test qui plante ne masque pas les suivants
            ECHECS.append(f"{test.__name__} : {erreur!r}")
            print(f"KO   {test.__name__} : exception {erreur!r}")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
