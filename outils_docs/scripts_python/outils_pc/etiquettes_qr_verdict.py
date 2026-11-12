"""Verdict de lisibilite d'un QR code imprime (page « Etiquettes QR code », plan etiquettes-qrcode A2).

Le texte est code en mode octet (UTF-8) : la page et la carte forcent `qrOptions.mode = "Byte"` dans qr-code-styling, sinon
un texte en chiffres ou en majuscules passerait en mode numerique ou alphanumerique et ne ferait plus le meme nombre de
modules. Capacites : ISO/IEC 18004, mode octet, versions 1 a 40 ; confrontees a qr-code-styling 1.9.2 le 2026-11-12
(outils_docs/etiquettes_qr/lib/LISEZMOI.md).

Taille d'un module (carre elementaire) = taille imprimee / (modules + 8) : la taille demandee comprend la marge blanche de
4 modules de chaque cote. Seuils provisoires, a recaler par l'essai d'impression du plan (A5).
"""

CAPACITE = {
    "M": [14, 26, 42, 62, 84, 106, 122, 152, 180, 213, 251, 287, 331, 362, 412, 450, 504, 560, 624, 666,
          711, 779, 857, 911, 997, 1059, 1125, 1190, 1264, 1370, 1452, 1538, 1628, 1722, 1809, 1911, 1989, 2099, 2213, 2331],
    "H": [7, 14, 24, 34, 44, 58, 64, 84, 98, 119, 137, 155, 177, 194, 220, 250, 280, 310, 338, 382,
          403, 439, 461, 511, 535, 593, 625, 658, 698, 742, 790, 842, 898, 958, 983, 1051, 1093, 1139, 1219, 1273],
}
MARGE = 4               # modules blancs de chaque cote
# mm par module, cales le 2026-11-12 sur l'essai reel (iPhone, planche d'essai, imprimante de l'utilisateur) :
# toute la planche lue jusqu'a 15 mm en texte court = 25 modules = 0,45 mm. Plus petit : non essaye, d'ou « limite ».
SEUIL_LISIBLE = 0.45
SEUIL_LIMITE = 0.35


def correction(avec_image):
    """Niveau de correction : H avec une image au centre (elle masque des modules), M sinon."""
    return "H" if avec_image else "M"


def version(octets, niveau):
    """Plus petite version qui contient `octets` octets au niveau donne ; None si aucune (texte trop long)."""
    for v, cap in enumerate(CAPACITE[niveau], start=1):
        if octets <= cap:
            return v
    return None


def verdict(texte, taille_mm, niveau):
    """{"octets", "version", "modules", "module_mm", "niveau"} ; niveau : lisible | limite | trop_dense | trop_long."""
    octets = len(texte.encode("utf-8"))
    v = version(octets, niveau)
    if v is None:
        return {"octets": octets, "version": None, "modules": None, "module_mm": None, "niveau": "trop_long"}
    modules = 17 + 4 * v
    mm = taille_mm / (modules + 2 * MARGE)
    jugement = "lisible" if mm >= SEUIL_LISIBLE else "limite" if mm >= SEUIL_LIMITE else "trop_dense"
    return {"octets": octets, "version": v, "modules": modules, "module_mm": round(mm, 3), "niveau": jugement}
