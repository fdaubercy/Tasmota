"""Banc du cache des compteurs de lieux de l'annuaire (annuaire_registre.en_json). Code de sortie 0 = vert.

Faux depot temporaire ; lieux.identites est remplace par un compteur d'appels : le cache doit eviter la relecture
tant qu'aucun fichier du parc ne change, la refaire des qu'un persist ou un .ini bouge, et ne rien garder d'une erreur.
Temoin : sans cache (cle toujours differente), le compteur monte a chaque appel et le banc le voit.
"""

import shutil
import sys
import tempfile
import time
from pathlib import Path

import annuaire_registre as reg
import lieux

ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def principal():
    racine = Path(tempfile.mkdtemp(prefix="cache_annuaire_"))
    appels = []
    vrai = lieux.identites
    try:
        (racine / "data" / "garage" / "p4-x").mkdir(parents=True)
        persist = racine / "data" / "garage" / "p4-x" / "_persist.json"
        persist.write_text("{}", encoding="utf-8")
        cenv = racine / "platformio_tasmota_cenv.ini"
        cenv.write_text("[env:a]", encoding="utf-8")        # seules la date et la taille comptent pour la cle

        def faux(_r):
            appels.append(1)
            return [{"lieu": "garage", "sauvegarde": False}, {"lieu": "garage", "sauvegarde": True}]
        lieux.identites = faux

        reg._CACHE.clear()
        n1 = {c: n for c, _, n in reg.en_json(racine)["lieux"]}
        verifie((n1.get("garage"), len(appels)), (1, 1), "1er appel : lit le parc, compte 1 carte (la sauvegarde ne compte pas)")
        reg.en_json(racine)
        verifie(len(appels), 1, "2e appel : cache, aucune relecture")
        time.sleep(0.02)
        persist.write_text('{"a": 1}', encoding="utf-8")
        reg.en_json(racine)
        verifie(len(appels), 2, "persist modifie : relecture")
        persist.unlink()
        reg.en_json(racine)
        verifie(len(appels), 3, "persist retire : relecture")
        cenv.write_text("[env:a][env:b]", encoding="utf-8")
        reg.en_json(racine)
        verifie(len(appels), 4, "cenv modifie : relecture")

        def casse(_r):
            appels.append(1)
            raise ValueError("cenv illisible")
        lieux.identites = casse
        cenv.write_text("x", encoding="utf-8")
        verifie(all(n == 0 for _, _, n in reg.en_json(racine)["lieux"]), True, "erreur : compteurs a 0, l'annuaire repond")
        avant = len(appels)
        reg.en_json(racine)
        verifie(len(appels), avant + 1, "erreur non gardee : la lecture suivante reessaie")

        # Temoin : un cache qui ne se souvient de rien doit faire monter le compteur (le banc le voit).
        lieux.identites = faux
        appels.clear()
        vraie_cle = reg._cle_parc
        compteur = iter(range(1000))
        reg._cle_parc = lambda _r: next(compteur)
        reg.en_json(racine)
        reg.en_json(racine)
        verifie(len(appels), 2, "TEMOIN cle instable : plus de cache, le compteur monte")
        reg._cle_parc = vraie_cle
    finally:
        lieux.identites = vrai
        shutil.rmtree(racine, ignore_errors=True)
    print()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
