"""Banc de fichiers_berry_sauvegarde (sauvegardes horodatees, transaction annulee sur exception).

Code de sortie 0 = vert. Tout se passe dans un dossier temporaire : un faux depot, et OUTILS_TASMOTA_DOSSIER
pointe vers un dossier temporaire (le vrai %LOCALAPPDATA%\\outils_tasmota n'est jamais touche).
"""

import os
import sys
import tempfile
import time
from pathlib import Path

ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def depot(t):
    racine = Path(t) / "depot"
    (racine / "data/lieu/carte").mkdir(parents=True)
    (racine / "a.ini").write_bytes(b"a\r\n")
    (racine / "b.h").write_bytes(b"b\r\n")
    (racine / "data/lieu/carte/autoexec.be").write_bytes(b"x")
    return racine


def test_sauvegarde_avant_ecriture(fbs, t):
    racine = depot(t)
    with fbs.Transaction(racine, "essai") as tr:
        tr.ecrit("a.ini", b"A\r\n")
    verifie((racine / "a.ini").read_bytes(), b"A\r\n", "ecrit : nouveau contenu")
    verifie((tr.dossier / "a.ini").read_bytes(), b"a\r\n", "ecrit : copie d'origine dans la sauvegarde")
    verifie(tr.dossier.parent == fbs.dossier_sauvegardes() and str(tr.dossier).startswith(os.environ["OUTILS_TASMOTA_DOSSIER"]),
            True, "sauvegarde sous OUTILS_TASMOTA_DOSSIER/fichiers_berry/sauvegardes")
    verifie(tr.dossier.name.endswith("-essai"), True, "nom de la sauvegarde : horodatage puis nature")


def test_annulation(fbs, t):
    racine = depot(t)
    try:
        with fbs.Transaction(racine, "essai") as tr:
            tr.ecrit("a.ini", b"A\r\n")
            tr.copie_dossier("data/lieu/carte", "data/lieu/copie")
            tr.renomme("data/lieu/carte", "data/lieu/carte-sauvegarde")
            tr.ecrit("nouveau.txt", b"n")
            tr.ecrit("b.h", b"B\r\n")
            raise RuntimeError("panne simulee")
        verifie("pas d'exception", "RuntimeError", "annulation : l'exception repart")
    except RuntimeError:
        pass
    verifie(((racine / "a.ini").read_bytes(), (racine / "b.h").read_bytes()), (b"a\r\n", b"b\r\n"),
            "annulation : fichiers remis")
    verifie((racine / "nouveau.txt").exists(), False, "annulation : fichier cree retire")
    verifie(((racine / "data/lieu/copie").exists(), (racine / "data/lieu/carte-sauvegarde").exists(),
             (racine / "data/lieu/carte/autoexec.be").is_file()), (False, False, True),
            "annulation : copie retiree, renommage defait")


def test_refus_cible_existante(fbs, t):
    racine = depot(t)
    (racine / "data/lieu/pris").mkdir()
    for action in (lambda tr: tr.renomme("data/lieu/carte", "data/lieu/pris"),
                   lambda tr: tr.copie_dossier("data/lieu/carte", "data/lieu/pris")):
        try:
            with fbs.Transaction(racine, "essai") as tr:
                action(tr)
            verifie("ecrase", "refus", "cible existante : refus")
        except FileExistsError:
            verifie((racine / "data/lieu/pris").exists() and not any((racine / "data/lieu/pris").iterdir()), True,
                    "cible existante : refus, rien d'ecrase")


def test_annulation_incomplete(fbs, t):
    """Une annulation qui echoue ne doit pas passer sous silence : erreur qui la nomme, avec la sauvegarde."""
    racine = depot(t)
    try:
        with fbs.Transaction(racine, "essai") as tr:
            tr.ecrit("a.ini", b"A\r\n")
            tr.renomme("data/lieu/carte", "data/lieu/carte2")
            (racine / "data/lieu/carte").mkdir()        # le retour du dossier sera impossible
            raise ValueError("panne simulee")
    except fbs.AnnulationIncomplete as erreur:
        texte = str(erreur)
        verifie(("data/lieu/carte2" in texte, "panne simulee" in texte, str(tr.dossier) in texte), (True, True, True),
                "annulation incomplete : chemin non defait, erreur d'origine et sauvegarde nommes")
    except Exception as erreur:
        verifie(repr(erreur), "AnnulationIncomplete", "annulation incomplete : erreur dediee")
    verifie((racine / "a.ini").read_bytes(), b"a\r\n", "annulation incomplete : les autres etapes sont defaites")


def test_purge(fbs, t):
    racine = fbs.dossier_sauvegardes()
    vieux, recent = racine / "20000101-000000-ancien", racine / "recent"
    for d in (vieux, recent):
        d.mkdir(parents=True)
        (d / "f").write_bytes(b"x")
    ancien = time.time() - 31 * 86400
    os.utime(vieux, (ancien, ancien))
    fbs.purge()
    verifie((vieux.exists(), recent.exists()), (False, True), "purge : plus de 30 jours retire, recent garde")


def principal():
    for test in (test_sauvegarde_avant_ecriture, test_annulation, test_refus_cible_existante, test_purge,
                 test_annulation_incomplete):
        with tempfile.TemporaryDirectory() as t:
            os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "outils")
            try:
                import fichiers_berry_sauvegarde as fbs
                test(fbs, t)
            except Exception as exc:
                verifie(repr(exc), "pas d'exception", test.__name__)
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
