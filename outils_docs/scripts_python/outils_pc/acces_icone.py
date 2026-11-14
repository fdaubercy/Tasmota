"""Icones PNG de l'application (manifeste de acces_web) : dessinees ici, sans bibliotheque d'images.

Meme motif que l'icone SVG (fond #1f2937, trois traits blancs arrondis), rasterise par distances signees
(bords anti-cretes) puis encode en PNG RGBA avec zlib. Resultat garde en memoire (le premier calcul d'une icone de
512 px prend moins d'une seconde). `maskable` : fond plein sans coins arrondis, le motif reste dans la zone sure
(le plus petit cercle central de 80 %), pour les icones adaptatives d'Android.
"""

import functools
import math
import os
import struct
import zlib
from pathlib import Path

FOND = (31, 41, 55)
BLANC = (255, 255, 255)
# Traits du motif en unites d'un viewBox de 64 : (x debut, x fin, y) ; epaisseur 6, bouts ronds.
TRAITS = ((14, 50, 22), (14, 50, 32), (14, 38, 42))
EPAISSEUR = 6
RAYON_COIN = 12


def _couverture(d):
    """Part du pixel couverte, d'apres la distance signee (en pixels) de son centre au bord."""
    return min(1.0, max(0.0, 0.5 - d))


VERSION = 1      # a monter si le dessin change : les fichiers du cache disque portent ce numero


def _fichier(taille, maskable):
    import acces_web                                  # ici : acces_web importe ce module
    return acces_web.dossier_donnees() / "icones" / f"icone-v{VERSION}-{taille}{'-maskable' if maskable else ''}.png"


@functools.lru_cache(maxsize=None)
def png(taille, maskable=False):
    """PNG de l'icone : en memoire, puis lu dans le cache disque (%LOCALAPPDATA%/outils_tasmota/icones), sinon dessine puis ecrit
    (le dessin d'un 512 px prend 1 a 9 s, selon la charge du poste : une fois par poste, pas par outil)."""
    try:
        fichier = _fichier(taille, maskable)
    except OSError:
        fichier = None
    try:
        donnees = fichier.read_bytes() if fichier else b""
        if donnees[:8] == SIGNATURE and donnees.endswith(FIN_PNG):
            return donnees
    except OSError:
        pass                                          # absent : dessine puis ecrit ci-dessous
    donnees = _dessine(taille, maskable)
    if fichier is not None:
        try:
            fichier.parent.mkdir(parents=True, exist_ok=True)
            tmp = fichier.with_name(fichier.name + f".{os.getpid()}.tmp")
            tmp.write_bytes(donnees)
            os.replace(tmp, fichier)
        except OSError:
            pass                                      # cache impossible : l'icone est quand meme servie
    return donnees


SIGNATURE = bytes.fromhex("89504e470d0a1a0a")
FIN_PNG = bytes.fromhex("0000000049454e44ae426082")    # morceau IEND complet : fichier non tronque


@functools.lru_cache(maxsize=None)
def _dessine(taille, maskable=False):
    s = taille / 64.0
    coin = 0.0 if maskable else RAYON_COIN * s
    demi = taille / 2.0
    r = EPAISSEUR * s / 2
    traits = [((x1 + x2) / 2 * s, (x2 - x1) / 2 * s, y * s) for x1, x2, y in TRAITS]
    plein = bytes(FOND) + bytes((255,))              # pixel de fond opaque
    bord = int(math.ceil(coin)) + 2                  # largeur des bords et des coins calculee pixel par pixel

    def pixel(i, j, proches):
        px, py = i + 0.5, j + 0.5
        qx, qy = abs(px - demi) - (demi - coin), abs(py - demi) - (demi - coin)
        alpha = _couverture(math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - coin)
        blanc = 0.0
        if alpha > 0:
            for cx, demi_long, cy in proches:
                blanc = max(blanc, _couverture(math.hypot(max(abs(px - cx) - demi_long, 0.0), py - cy) - r))
        return bytes((round(FOND[k] * (1 - blanc) + BLANC[k] * blanc) for k in range(3))) + bytes((round(255 * alpha),))

    lignes = []
    for j in range(taille):
        proches = [t for t in traits if abs(j + 0.5 - t[2]) <= r + 1]
        if j < 2 or j >= taille - 2:                 # rangees du haut et du bas : tout est bord
            spans = [(0, taille)]
        else:
            e = bord if (j < bord or j >= taille - bord) else 2    # la largeur des coins n'est utile qu'en haut et en bas
            spans = [(0, e), (taille - e, taille)]
            spans += [(max(0, int(cx - dl - r - 2)), min(taille, int(cx + dl + r + 3))) for cx, dl, _ in proches]
        fusion = []
        for debut, fin in sorted(spans):
            if fusion and debut <= fusion[-1][1]:
                fusion[-1][1] = max(fusion[-1][1], fin)
            else:
                fusion.append([debut, fin])
        ligne = bytearray([0])                      # filtre PNG 0 (aucun) en tete de rangee
        suite = 0
        for debut, fin in fusion:
            ligne += plein * (debut - suite)
            for i in range(debut, fin):
                ligne += pixel(i, j, proches)
            suite = fin
        ligne += plein * (taille - suite)
        lignes.append(bytes(ligne))

    def morceau(genre, donnees):
        return (struct.pack(">I", len(donnees)) + genre + donnees
                + struct.pack(">I", zlib.crc32(genre + donnees) & 0xFFFFFFFF))
    entete = struct.pack(">IIBBBBB", taille, taille, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + morceau(b"IHDR", entete)
            + morceau(b"IDAT", zlib.compress(b"".join(lignes), 6)) + morceau(b"IEND", b""))
