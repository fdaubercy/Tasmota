"""Banc de qrcode_build (plan etiquettes-qrcode A7, regeneration de qrcode.json par le pre-script). Code 0 = vert.

UTILISATION (Python de PlatformIO, comme les bancs d'outils_pc)
    python outils_docs/scripts_python/build/test_qrcode_build.py
Copie temporaire du depot (test_etiquettes_qr_ecriture.copie) : le vrai depot n'est jamais ecrit.
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / "outils_pc"))
sys.path.insert(0, str(ICI))

import fichiers_berry_etat as fbe          # noqa: E402
import qrcode_build                        # noqa: E402
import test_etiquettes_qr_ecriture as tqe  # noqa: E402
import test_etiquettes_qr_suivi as tqs     # noqa: E402

CUVE = tqe.CUVE
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def principal():
    with tempfile.TemporaryDirectory(prefix="banc_qrcode_build_") as t:
        racine = tqe.copie(t)
        tqe.fichiers_page(racine)
        verifie(qrcode_build.regenere(racine, CUVE), None, "env sans reglage d'etiquette : rien")

        modele = tqs.suivi.modele
        tqe.ecrit(racine, CUVE, modele.fusionne(modele.charge_gabarit(racine), tqs.REGLAGE), True)
        qr = racine / fbe.dossier_carte(CUVE) / "qrcode.json"
        os.utime(qr, (1_000_000_000, 1_000_000_000))
        avant = qr.read_bytes()
        verifie(qrcode_build.regenere(racine, CUVE), None, "persist inchange : rien")
        verifie((qr.read_bytes(), qr.stat().st_mtime), (avant, 1_000_000_000), "persist inchange : fichier intact, date comprise")

        tqs.change_persist(racine, ["hostname"], "CUVE-RENOMMEE")
        message = qrcode_build.regenere(racine, CUVE)
        verifie(("régénéré" in (message or ""), "CUVE-RENOMMEE" in json.loads(qr.read_text(encoding="utf-8"))["texte"]),
                (True, True), "hostname change : qrcode.json reecrit, ligne dans la sortie de pio")
        verifie(qrcode_build.regenere(racine, CUVE), None, "deuxieme passage : plus rien a faire")

        persist = racine / fbe.dossier_carte(CUVE) / "_persist.json"
        persist.write_text("{ casse", encoding="utf-8")
        bon = qr.read_bytes()
        debut = time.monotonic()
        message = qrcode_build.regenere(racine, CUVE)
        verifie(qr.read_bytes(), bon, "persist illisible : qrcode.json garde tel quel (jamais un hostname vide)")
        verifie((message or "").startswith("⚠"), True, "persist illisible : avertissement, aucune exception (le build continue)")
        verifie(time.monotonic() - debut < 30, True, "persist illisible : reponse rapide")

        qr.unlink()                                      # reglage present mais carte sans page : rien n'est cree
        persist.write_text(json.dumps({"serveur": {"hostname": "X"}}), encoding="utf-8")
        verifie((qrcode_build.regenere(racine, CUVE), qr.exists()), (None, False), "carte sans qrcode.json (pas de page) : rien de cree")

        # A11 : fiche en ligne a republier, signalee dans la sortie de pio (sans reseau, rien n'est envoye)
        verifie(qrcode_build.fiche(racine, tqe.PORTE), None, "fiche : env sans reglage d'etiquette, rien")
        verifie(qrcode_build.fiche(racine, CUVE), None, "fiche : carte en texte sans fiche en ligne, rien")
        surcharge = modele.chemin_surcharge(racine, CUVE)
        surcharge.write_text(json.dumps({**json.loads(surcharge.read_text(encoding="utf-8")), "contenu": "lien"}), encoding="utf-8")
        message = qrcode_build.fiche(racine, CUVE)
        verifie(("à republier" in (message or ""), "7970" in (message or "")), (True, True),
                "fiche : carte en lien sans fiche en ligne, ligne « à republier » qui renvoie a la page 7970")
        surcharge.write_text("{ casse", encoding="utf-8")
        verifie((qrcode_build.fiche(racine, CUVE) or "").startswith("⚠"), True, "fiche : reglage illisible, avertissement sans exception")
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
