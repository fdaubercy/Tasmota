"""Banc de build_ota_fs (envoi du firmware par /u2 et du file system par /ufsu) sur une carte simulee.

Code de sortie 0 = vert. La carte simulee (build_ota_carte_simulee.Carte) est un serveur HTTP sur
127.0.0.1 (port libre) qui imite Tasmota : Referer exige, /ufsd, /ufsu, /up, /u2, /u4 (safeboot),
/cm (Br, Restart 1, Status, Status 2). Aucune vraie carte n'est contactee.
"""

import json
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
    return {"Restart 1": "restart", "Status": "status"}.get(cmnd, chemin)


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
        verifie([r["detail"].split(" ")[0] for r in envois], ["1/5", "2/5", "3/5", "4/5", "5/5"],
                "ota_fs_progression : un rapport par fichier, fichiers envoyes / total")
        verifie([r["pourcent"] for r in envois], [20, 40, 60, 80, 100], "ota_fs_progression : pourcentages")
        verifie(envois[-1]["detail"] if envois else "", "5/5 _persist.json",
                "ota_fs_progression : detail = n/total chemin (persist en dernier)")
        verifie("sd/js/graphiques.js" in [r["detail"].split(" ", 1)[1] for r in envois], True,
                "ota_fs_progression : chemin relatif avec ses dossiers")
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


def principal():
    for test in (test_ota_fs_ordre, test_ota_fs_sauvegarde, test_ota_fs_persist_injoignable,
                 test_ota_fs_relecture_differente, test_ota_fs_sous_dossiers, test_ota_fs_referer,
                 test_ota_fs_echec_ufsu, test_ota_fs_pas_de_retour, test_ota_fs_attente_retour,
                 test_ota_fs_persist_reformate, test_ota_fs_progression,
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
