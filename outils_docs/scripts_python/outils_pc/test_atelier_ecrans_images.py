"""Banc de l'import d'un PNG de l'atelier des ecrans (atelier_ecrans_images.py), plan atelier-ecrans A15.

    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_ecrans_images.py

Copie temporaire du depot. Verifie : PNG valides (avec et sans alpha, palette + tRNS), refus (autre format, tronque,
dimensions, poids, nom), import (origine, licence, build en cours, nom pris, ecritures exactes, rien d'ecrit en cas de refus).
Code de sortie 0 = vert. `png` est reutilise par les bancs de la page web.
"""
import struct
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atelier_ecrans_images as aim     # noqa: E402
import fichiers_berry_etat as fbe       # noqa: E402
import test_atelier_ecrans_web as taw   # noqa: E402

ENV = "tasmota32s3-bureau-ecran-debits-pac"
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)


def png(largeur=1, hauteur=1, type_=6, trns=False):
    """Un PNG minimal valide (donnees zlib reelles) du type demande : 0 gris, 2 RVB, 3 palette, 6 RVBA."""
    def bloc(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    canaux = {0: 1, 2: 3, 3: 1, 6: 4}[type_]
    brut = (b"\x00" + b"\x00" * (canaux * largeur)) * hauteur
    corps = bloc(b"IHDR", struct.pack(">IIBBBBB", largeur, hauteur, 8, type_, 0, 0, 0))
    if type_ == 3:
        corps += bloc(b"PLTE", b"\xff\xff\xff") + (bloc(b"tRNS", b"\x00") if trns else b"")
    return aim.SIGNATURE + corps + bloc(b"IDAT", zlib.compress(brut)) + bloc(b"IEND", b"")


def refuse(nom, octets):
    try:
        aim.analyse(nom, octets)
        return None
    except ValueError as e:
        return str(e)


def instantane(racine):
    return {p.relative_to(racine).as_posix(): p.read_bytes() for p in sorted(racine.rglob("*")) if p.is_file()}


def main():
    a = aim.analyse("rgba.png", png())
    verifie((a["alpha"], a["avertissements"], a["largeur"], a["nom"]), (True, [], 1, "rgba"), "RVBA : transparence, aucun avertissement")
    a = aim.analyse("rvb.png", png(type_=2))
    verifie((a["alpha"], len(a["avertissements"])), (False, 1), "RVB : sans transparence signale")
    verifie(aim.analyse("pal.png", png(type_=3, trns=True))["alpha"], True, "palette avec tRNS : transparence")
    verifie(aim.analyse("pal.png", png(type_=3))["alpha"], False, "palette sans tRNS : opaque")
    verifie(len(aim.analyse("grand.png", png(200, 4))["avertissements"]), 1, "200 px : conseil de taille d'affichage")
    for libelle, nom, octets, mot in [("JPG refuse", "a.png", b"\xff\xd8\xff\xe0" + b"\x00" * 40, "PNG"),
                                      ("tronque (sans IEND)", "a.png", png()[:-12], "tronque"),
                                      ("513 px refuse", "a.png", png(513, 1), "dimensions"),
                                      ("nom en .jpg", "a.jpg", png(), "nom"),
                                      ("nom avec espace", "a b.png", png(), "nom"),
                                      ("nom reserve Windows", "NUL.png", png(), "reserve"),
                                      ("nom en .PNG majuscule", "a.PNG", png(), "nom"),
                                      ("trop lourd", "a.png", png() + b"\x00" * aim.TAILLE_MAX, "lourde")]:
        m = refuse(nom, octets)
        verifie(bool(m) and mot in m, True, f"analyse : {libelle} ({(m or 'accepte !')[:60]})")
    with tempfile.TemporaryDirectory(prefix="banc_images_") as t:
        racine = Path(t) / "depot"
        racine.mkdir()
        taw.copie(racine)
        avant = instantane(racine)

        def importe(nom=b"x", origine="https://pictogrammers.com/library/mdi/", licence=True, builds=lambda: [], octets=None):
            try:
                return aim.importe(racine, ENV, "essai.png", octets or png(), origine, licence, builds)
            except (ValueError, RuntimeError) as e:
                return type(e).__name__ + " : " + str(e)
        for libelle, kw, mot in [("sans origine", {"origine": " "}, "origine"), ("licence non confirmee", {"licence": False}, "licence"),
                                 ("build en cours", {"builds": lambda: ["upload"]}, "build"), ("origine non texte", {"origine": 5}, "origine"),
                                 ("origine sur deux lignes", {"origine": "a" + chr(10) + "Licence : libre"}, "origine")]:
            r = importe(**kw)
            verifie((isinstance(r, str) and mot in r.lower(), instantane(racine) == avant), (True, True), f"import refuse : {libelle}, rien d'ecrit")
        octets = png(8, 8)
        r = importe(octets=octets)
        dossier = fbe.dossier_carte(ENV)
        verifie(r["ecrits"], [f"{dossier}/essai.png", f"outils_docs/atelier_ecrans/images/{ENV}/essai.licence.txt"], "import : deux fichiers ecrits")
        verifie((racine / dossier / "essai.png").read_bytes(), octets, "import : PNG ecrit octet pour octet dans le dossier de la carte")
        lic = (racine / "outils_docs/atelier_ecrans/images" / ENV / "essai.licence.txt").read_text(encoding="utf-8")
        verifie(("pictogrammers.com" in lic, "8 x 8" in lic, ENV in lic), (True, True, True), "import : note de licence avec origine, taille et carte")
        r2 = importe()
        verifie(isinstance(r2, str) and "existe deja" in r2, True, "import : nom deja pris dans la carte refuse")
    print(f"\n{len(ECHECS)} echec(s) : " + ("VERT" if not ECHECS else "ROUGE"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
