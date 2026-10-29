"""Banc de build_fichiers.py (onglet « Fichiers » de la page 7700, A15) : liste des fichiers de l'image du FS.

Depot d'essai temporaire (jamais le vrai depot), vraie image LittleFS (fabrique_image du banc OTA).
Code de sortie 0 = vert.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import build_fichiers as bf
from test_build_ota_fs import fabrique_image

ECHECS = []
ENV = "tasmota32-essai-carte"                     # dossier de la carte : data/essai/tasmota32-carte
CENV = f"""\
[env:tasmota32-essai-base]
extra_scripts           = pre:outils_docs/scripts_python/build/pre_utilitaires_platformio.py

[env:{ENV}]
extends                 = env:tasmota32-essai-base
custom_files_upload     = data/fs/commun.be
"""


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def persist(hote):
    return json.dumps({"serveur": {"hostname": hote, "mqtt": {"topic": "essai/carte"}}}).encode("utf-8")


def depot(t, hote_image="CARTE-ESSAI"):
    """Depot d'essai : cenv, dossier de la carte, data/fs, image du FS datee d'il y a une heure."""
    racine = Path(t) / "depot"
    carte = racine / "data" / "essai" / "tasmota32-carte"
    (carte / "json").mkdir(parents=True)
    (racine / "data" / "fs").mkdir(parents=True)
    (racine / "platformio_tasmota_cenv.ini").write_text(CENV, encoding="utf-8")
    (carte / "_persist.json").write_bytes(persist("carte-essai"))
    (carte / "autoexec.be").write_bytes(b"print(1)")
    (carte / "json" / "graphiques.json").write_bytes(b"{}")
    (racine / "data" / "fs" / "commun.be").write_bytes(b"print(2)")
    image = bf.image(racine, ENV)
    fabrique_image(image, {"_persist.json": persist(hote_image), "autoexec.be": b"print(1)",
                           "commun.be": b"print(2)", "json/graphiques.json": b"{}"})
    il_y_a_une_heure = image.stat().st_mtime - 3600
    os.utime(image, (il_y_a_une_heure, il_y_a_une_heure))
    for p in (carte / "_persist.json", carte / "json" / "graphiques.json", racine / "data" / "fs" / "commun.be"):
        os.utime(p, (il_y_a_une_heure - 60, il_y_a_une_heure - 60))     # plus anciens que l'image
    return racine, image


def test_liste():
    with tempfile.TemporaryDirectory() as t:
        racine, image = depot(t)
        r = bf.liste(racine, ENV)
        verifie((r["erreur"], r["image"]["present"], r["image"]["jeton"]), ("", True, str(image.stat().st_mtime_ns)),
                "liste : image presente, jeton = date de l'image en ns, sans erreur")
        verifie(r["identite"].startswith("identité vérifiée"), True, "liste : identite de l'image verifiee")
        verifie([(f["chemin"], f["taille"]) for f in r["fichiers"]],
                [("_persist.json", len(persist("CARTE-ESSAI"))), ("autoexec.be", 8), ("commun.be", 8),
                 ("json/graphiques.json", 2)], "liste : chemins du FS et tailles, tries")
        verifie(r["dossiers"], {"": 3, "json": 1}, "liste : nombre de fichiers par dossier")
        verifie({f["chemin"]: f["plus_recent"] for f in r["fichiers"]},
                {"_persist.json": False, "autoexec.be": True, "commun.be": False, "json/graphiques.json": False},
                "liste : seul autoexec.be (non vieilli) est plus recent que l'image")
        verifie(all(f["depot"] for f in r["fichiers"]), True,
                "liste : date du depot trouvee pour chaque fichier (carte, json/, custom_files_upload)")


def test_cas_limites():
    with tempfile.TemporaryDirectory() as t:
        racine, image = depot(t, hote_image="AUTRE-CARTE")
        r = bf.liste(racine, ENV)
        verifie(("AUTRE-CARTE" in r["erreur"], len(r["fichiers"])), (True, 4),
                "cas_limites : image d'une autre carte -> erreur dite, liste quand meme")
        image.unlink()
        r = bf.liste(racine, ENV)
        verifie((r["image"]["present"], r["image"]["jeton"], "Préparer" in r["erreur"], r["fichiers"]),
                (False, "", True, []), "cas_limites : pas d'image -> « Préparer la liste »")
        image.write_bytes(b"\xff" * 4096)
        r = bf.liste(racine, ENV)
        verifie((bool(r["erreur"]), r["fichiers"]), (True, []), "cas_limites : image illisible -> erreur, aucun fichier")
        try:
            bf.liste(racine, "tasmota32-inconnu-x")
            verifie("rien", "LookupError", "cas_limites : env inconnu -> LookupError")
        except LookupError:
            verifie(True, True, "cas_limites : env inconnu -> LookupError")


def principal():
    for test in (test_liste, test_cas_limites):
        try:
            test()
        except Exception as erreur:                  # un test qui plante ne masque pas les suivants
            ECHECS.append(f"{test.__name__} : {erreur!r}")
            print(f"KO   {test.__name__} : exception {erreur!r}")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
