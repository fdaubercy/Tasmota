"""Import d'un PNG dans l'atelier des ecrans (plan atelier-ecrans A15, sur le modele de l'import de polices A9).

`analyse(nom, octets)` controle le fichier (signature, IHDR, IDAT, IEND, poids, dimensions) et rend ce que la page affiche.
`importe` ecrit le PNG dans le dossier de la carte (`data/<lieu>/<carte>/<nom>.png` : il part sur le FS, `gestionFileFolder.be`
le range sous `/sd/images/PNG/` au demarrage, et l'objet `img` le choisit : GET /images), puis une note de licence HORS du
dossier de la carte (`outils_docs/atelier_ecrans/images/<env>/<nom>.licence.txt` : origine et confirmation de l'utilisateur),
en une Transaction ; refus pendant un build, licence non confirmee, origine absente, nom deja pris dans la carte.
shortcut: le contenu des donnees d'image n'est pas decode (le decodeur de la carte le fera) ; la blancheur de l'icone n'est pas controlee.
"""
import re
import struct
from pathlib import Path

import atelier_ecrans_ecriture as aee
import fichiers_berry_etat as fbe
import fichiers_berry_sauvegarde as fbs

TAILLE_MAX = 300 * 1024
DIM_MAX = 512                  # au-dela : refus (RAM de la carte) ; DIM_CONSEIL : avertissement
DIM_CONSEIL = 160
DOSSIER_LICENCES = "outils_docs/atelier_ecrans/images"
NOM = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.png")
RESERVES = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}   # noms de peripheriques Windows
SIGNATURE = b"\x89PNG\r\n\x1a\n"
SANS_ALPHA = {0: "niveaux de gris", 2: "couleurs"}      # types PNG sans canal alpha


def analyse(nom, octets):
    """{"nom", "largeur", "hauteur", "poids", "alpha", "avertissements"} ; ValueError si refuse."""
    if not isinstance(nom, str) or not NOM.fullmatch(nom):
        raise ValueError("nom de fichier attendu : lettres, chiffres, - ou _, fini par .png (64 caracteres au plus)")
    if nom[:-4].lower() in RESERVES:
        raise ValueError(f"nom de fichier {nom} reserve par Windows (peripherique) : renommer l'image")
    if len(octets) > TAILLE_MAX:
        raise ValueError(f"image trop lourde ({len(octets) // 1024} Ko, {TAILLE_MAX // 1024} Ko au plus sur le FS)")
    if octets[:8] != SIGNATURE or octets[12:16] != b"IHDR" or struct.unpack(">I", octets[8:12])[0] != 13:
        raise ValueError("ce n'est pas un PNG (signature ou en-tete IHDR absents) : JPG, BMP, SVG, WEBP refuses")
    largeur, hauteur, profondeur, type_ = struct.unpack(">IIBB", octets[16:26])
    if not (0 < largeur <= DIM_MAX and 0 < hauteur <= DIM_MAX):
        raise ValueError(f"dimensions {largeur} x {hauteur} hors 1..{DIM_MAX} : l'image se decode en RAM sur la carte, la dessiner a sa taille d'affichage")
    if b"IDAT" not in octets or not octets.rstrip(b"\x00").endswith(b"IEND\xaeB`\x82"):
        raise ValueError("PNG tronque (donnees IDAT ou fin IEND absentes)")
    alpha = type_ not in SANS_ALPHA and not (type_ == 3 and b"tRNS" not in octets)
    av = []
    if max(largeur, hauteur) > DIM_CONSEIL:
        av.append(f"{largeur} x {hauteur} : grande pour une icone, la dessiner a la taille d'affichage (le decodage coute de la RAM)")
    if not alpha:
        av.append("pas de transparence : image_recolor teindra tout le rectangle ; une icone s'exporte blanche sur fond transparent")
    return {"nom": nom[:-4], "fichier": nom, "largeur": largeur, "hauteur": hauteur, "poids": len(octets), "alpha": alpha,
            "avertissements": av}


def importe(racine, env, nom, octets, origine, licence_confirmee, builds_en_cours):
    """{"ecrits", "analyse"} ; ValueError (image refusee) ou RuntimeError (build en cours, nom deja pris)."""
    a = analyse(nom, octets)
    origine = (origine or "").strip() if isinstance(origine, str) else ""
    if not origine or len(origine) > 300 or not origine.isprintable():
        raise ValueError("origine a indiquer (site ou URL de l'image, 300 caracteres imprimables au plus, sur une ligne)")
    if not licence_confirmee:
        raise ValueError("licence a confirmer (libre d'usage) avant l'import")
    aee.refuse_build(builds_en_cours)
    racine = Path(racine)
    dossier = racine / fbe.dossier_carte(env)
    if any(p.name.lower() == nom.lower() for p in dossier.glob("*")):
        raise RuntimeError(f"un fichier {nom} existe deja dans le dossier de la carte : renommer l'image")
    texte = (f"Image : {nom}\nImportee par l'atelier des ecrans pour {env}\nOrigine : {origine}\n"
             f"Taille : {a['largeur']} x {a['hauteur']}, {a['poids']} octets\nLicence confirmee libre par l'utilisateur dans la page.\n").encode("utf-8")
    rel, rel_licence = f"{fbe.dossier_carte(env)}/{nom}", f"{DOSSIER_LICENCES}/{env}/{nom[:-4]}.licence.txt"
    (racine / DOSSIER_LICENCES / env).mkdir(parents=True, exist_ok=True)
    with fbs.Transaction(racine, "atelier-ecrans-image") as tr:
        tr.ecrit(rel, octets)
        tr.ecrit(rel_licence, texte)
    return {"ecrits": [rel, rel_licence], "analyse": a}
