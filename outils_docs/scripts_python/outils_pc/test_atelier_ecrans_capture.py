"""Banc de atelier_ecrans_capture (capture d'ecran d'une carte LVGL par `Br lv.screenshot()`), carte SIMULEE.

Code de sortie 0 = vert. Python de PlatformIO :
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_ecrans_capture.py
La carte est un `get(ip, chemin, delai)` injecte (aucun reseau) qui imite les reponses du firmware :
xdrv_52_9_berry.ino::CmndBrRun ({"Br": "<valeur>"} ou {"Br": "[type] message"}), xdrv_52_3_berry_lvgl.ino::lv0_screenshot
(nom /screenshot-<utc>.bmp, en-tete BMP de 0x42 octets, taille declaree aux octets 2..6), xdrv_50_filesystem.ino (/ufsd).
"""

import json
import struct
import sys
import urllib.parse

import atelier_ecrans_capture as cap

ECHECS = []
NOM = "/screenshot-1762953600.bmp"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def bmp(largeur=4, hauteur=2):
    taille = largeur * hauteur * 2 + 0x42
    tete = b"BM" + struct.pack("<III", taille, 0, 0x42) + struct.pack("<Iii", 0x28, largeur, hauteur)
    tete = tete.ljust(0x42, b"\0")
    return tete + bytes(range(256))[: largeur * hauteur * 2]


class Carte:
    """Carte simulee : `br` = valeur rendue par Br ; `image` = octets du fichier ; `morte` = aucune reponse."""

    def __init__(self, br=NOM, image=None, morte=False, efface_ko=False, telecharge_ko=False):
        self.br, self.image, self.morte = br, bmp() if image is None else image, morte
        self.efface_ko, self.telecharge_ko = efface_ko, telecharge_ko
        self.appels = []

    def get(self, ip, chemin, delai):
        self.appels.append((ip, urllib.parse.unquote(chemin), delai))
        if self.morte:
            raise OSError("timed out")
        if chemin.startswith("/cm?cmnd="):
            return json.dumps({"Br": self.br}).encode()
        if "delete=" in chemin:
            if self.efface_ko:
                raise OSError("connexion fermee")
            return b"<html>liste</html>"
        if "download=" in chemin:
            if self.telecharge_ko:
                raise OSError("connexion fermee")
            return self.image
        return b"<html>liste</html>"

    def chemins(self):
        return [c for _, c, _ in self.appels]


def refus(carte):
    """Message du refus (RuntimeError), ou None si la capture a ete rendue."""
    try:
        cap.capture("192.168.0.51", carte.get)
    except RuntimeError as e:
        return str(e)
    return None


def test_capture_ok():
    c = Carte()
    image = cap.capture("192.168.0.51", c.get)
    verifie(image, bmp(), "capture : octets du BMP de la carte, tels quels")
    ch = c.chemins()
    verifie(ch[0], "/ufsd?dir=0", "1er appel : /ufsd?dir=0 (fichiers de la carte sur la flash : dfsp = ffsp)")
    verifie(ch[1], "/cm?cmnd=Br lv.screenshot()", "2e appel : Br lv.screenshot()")
    verifie(ch[2:], [f"/ufsd?dir=0&download={NOM}", f"/ufsd?dir=0&delete={NOM}"],
            "puis telechargement et effacement du MEME fichier, sur le MEME systeme de fichiers (dir=0)")
    verifie({ip for ip, _, _ in c.appels}, {"192.168.0.51"}, "toujours l'adresse donnee")
    verifie(c.appels[1][2] >= 20 and c.appels[2][2] >= 30, True, "delais longs pour l'ecriture et le telechargement (~1,2 Mo)")


def test_refus():
    for br, motif in (("nil", "LVGL"), ("[attribute_error] the 'lv' object has no attribute 'screenshot'", "attribute_error"),
                      ("[syntax_error] input:1: 'lv' undeclared", "syntax_error")):
        c = Carte(br=br)
        m = refus(c)
        verifie((m is not None and motif in m, any("download" in x or "delete" in x for x in c.chemins())), (True, False),
                f"Br rend {br[:30]!r} : refus qui cite la reponse, ni telechargement ni effacement")
    c = Carte(br="[timeout_error] Berry code running for too long")
    m = refus(c)
    verifie(m is not None and "/screenshot-" in m, True, "Br en timeout : refus qui signale un /screenshot-*.bmp peut-etre reste")
    for br in ("/../_persist.json", "/screenshot-1.bmp?x=1", "/screenshot-1.bmp&delete=/autoexec.be", "screenshot-1.bmp"):
        c = Carte(br=br)
        verifie((refus(c) is not None, any("download" in x or "delete" in x for x in c.chemins())), (True, False),
                f"nom inattendu {br!r} : refuse, jamais mis dans une URL")


def test_hors_ligne():
    c = Carte(morte=True)
    m = refus(c)
    verifie((m is not None and "injoignable" in m, len(c.appels)), (True, 1), "carte hors ligne : refus « injoignable », un seul essai")


def test_image_invalide():
    for image, libelle in ((b"<html>liste</html>", "page HTML a la place du BMP"), (b"", "corps vide"),
                           (bmp()[:-10], "BMP tronque (FS plein)")):
        c = Carte(image=image)
        m = refus(c)
        verifie((m is not None, c.chemins()[-1]), (True, f"/ufsd?dir=0&delete={NOM}"), f"{libelle} : refus, fichier efface quand meme")
    c = Carte(telecharge_ko=True)
    verifie((refus(c) is not None, c.chemins()[-1]), (True, f"/ufsd?dir=0&delete={NOM}"),
            "telechargement coupe : refus, fichier efface quand meme")


def test_effacement_rate():
    c = Carte(efface_ko=True)
    m = refus(c)
    verifie(m is not None and NOM in m, True, "effacement rate : refus qui nomme le fichier reste sur la carte")


def principal():
    for t in (test_capture_ok, test_refus, test_hors_ligne, test_image_invalide, test_effacement_rate):
        print(f"--- {t.__name__}")
        try:
            t()
        except Exception as e:                  # un test qui plante est un echec, pas un arret du banc
            verifie(f"{type(e).__name__} : {e}", None, f"{t.__name__} : exception")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
