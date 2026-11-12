"""Banc de etiquettes_qr_verdict (capacites ISO en mode octet, verdict de lisibilite). Code de sortie 0 = vert.

Valeurs attendues calculees a la main ici, jamais tirees du module : H v10 = 119 octets, 57 modules ; 25 mm / (57 + 8).
Mutant : seuils inverses -> test_niveaux rouge.
"""

import os
import sys

import etiquettes_qr_verdict as v

ECHECS = []


def verifie(obtenu, attendu, libelle):
    if obtenu != attendu:
        ECHECS.append(libelle)
        print(f"ECHEC {libelle} : obtenu {obtenu!r}, attendu {attendu!r}")


def test_bornes():
    verifie(v.version(14, "M"), 1, "14 octets M -> version 1")
    verifie(v.version(15, "M"), 2, "15 octets M -> version 2")
    verifie(v.version(7, "H"), 1, "7 octets H -> version 1")
    verifie(v.version(2331, "M"), 40, "2331 octets M -> version 40")
    verifie(v.version(2332, "M"), None, "2332 octets M -> trop long")
    verifie(len(v.CAPACITE["M"]) == len(v.CAPACITE["H"]) == 40, True, "40 versions par niveau")
    verifie(v.correction(True), "H", "image -> H")
    verifie(v.correction(False), "M", "sans image -> M")


def test_octets_utf8():
    r = v.verdict("é" * 8, 25, "M")                           # 16 octets UTF-8, 8 caracteres
    verifie((r["octets"], r["version"], r["modules"]), (16, 2, 25), "« é » compte 2 octets")


def test_niveaux():
    r = v.verdict("a" * 100, 25, "H")                         # H v10 (98 < 100 <= 119) -> 57 modules ; 25/65 = 0,385
    verifie((r["version"], r["modules"], r["module_mm"], r["niveau"]), (10, 57, 0.385, "limite"), "100 o, 25 mm, H")
    verifie(v.verdict("a" * 14, 25, "M")["niveau"], "lisible", "14 o, 25 mm, M : 25/29 = 0,86 mm")
    verifie(v.verdict("a" * 100, 15, "H")["niveau"], "trop_dense", "100 o, 15 mm, H : 15/65 = 0,23 mm")
    verifie(v.verdict("a" * 3000, 25, "M")["niveau"], "trop_long", "3000 o -> trop long")


TESTS = [test_bornes, test_octets_utf8, test_niveaux]


def mutant(nom, applique, retablit, test):
    global ECHECS
    garde, ECHECS = ECHECS, []
    sortie, sys.stdout = sys.stdout, open(os.devnull, "w")    # les ECHEC attendus du mutant ne polluent pas la sortie
    applique()
    try:
        test()
    finally:
        retablit()
        sys.stdout.close()
        sys.stdout = sortie
        rouge, ECHECS = bool(ECHECS), garde
    print(f"mutant {nom} : {'rouge (detecte)' if rouge else 'VERT (non detecte)'}")
    verifie(rouge, True, f"mutant {nom} detecte")


if __name__ == "__main__":
    for t in TESTS:
        t()
    seuils = (v.SEUIL_LISIBLE, v.SEUIL_LIMITE)
    mutant("seuils inverses", lambda: (setattr(v, "SEUIL_LISIBLE", seuils[1]), setattr(v, "SEUIL_LIMITE", seuils[0])),
           lambda: (setattr(v, "SEUIL_LISIBLE", seuils[0]), setattr(v, "SEUIL_LIMITE", seuils[1])), test_niveaux)
    mutant("table decalee", lambda: v.CAPACITE["M"].insert(0, 10), lambda: v.CAPACITE["M"].pop(0), test_bornes)
    print("BANC_ETIQUETTES_QR_VERDICT:", "ECHEC " + str(len(ECHECS)) if ECHECS else "OK")
    sys.exit(1 if ECHECS else 0)
