"""Fonctions pures du navigateur FTP des cartes : chemins de la carte, fichiers proteges, noms rendus par la carte, reponse `Ufs`.

Sans reseau ni etat : importees (et reexportees) par ftp_cartes_session.py, dont les bancs appellent `ftp_cartes_session.valide_chemin`
et `.protege`. Spec : docs/superpowers/specs/2026-11-20-navigateur-ftp-cartes-design.md §9.
"""
import re

ADRESSE = re.compile(r"[A-Za-z0-9.-]+")
OBJET_UFS = re.compile(r'\{\s*"Type"\s*:\s*(\d+)\s*,\s*"Size"\s*:\s*(\d+)\s*,\s*"Free"\s*:\s*(\d+)\s*\}')
NOMS_PROTEGES = ("autoexec.be", "autoexec.bat", "_persist.json")
DOSSIERS_PROTEGES = ("/sd", "/json")


def valide_chemin(chemin):
    """Chemin de la carte : absolu, sans `..`, sans caractere de controle, 255 caracteres au plus. Rend le chemin normalise."""
    if not isinstance(chemin, str) or not chemin.startswith("/"):
        raise ValueError("chemin absolu attendu")
    if len(chemin) > 255:
        raise ValueError("chemin trop long (255 caracteres au plus)")
    if any(ord(c) < 32 or ord(c) == 127 for c in chemin):
        raise ValueError("caractere de controle interdit")
    if "\\" in chemin:                              # FatFs peut le lire comme un separateur : il sortirait du dossier et de protege()
        raise ValueError("caractere « \\ » interdit")
    if chemin == "/":
        return chemin
    morceaux = chemin[1:-1 if chemin.endswith("/") else None].split("/")
    if any(m in ("", ".", "..") for m in morceaux):
        raise ValueError("segment vide, « . » ou « .. » interdit")
    return "/" + "/".join(morceaux)


def cle_fat(nom):
    """Nom tel que FatFs le compare : sans casse, sans points ni espaces finaux (`AUTOEXEC.BE.` est `autoexec.be`).
    Les alias courts 8.3 (`AUTOEX~1.BE`) ne sont pas traites."""
    return nom.casefold().rstrip(". ")


def cle_chemin(chemin):
    """Chemin compare segment par segment selon cle_fat, sans barre finale (`/SD./` -> `/sd`)."""
    return "/".join(cle_fat(s) for s in chemin.split("/")).rstrip("/") or "/"


def dans_lui_meme(source, cible):
    """True si `cible` est `source` ou se trouve sous elle (comparaison FAT) : un dossier ne se deplace pas dans lui-meme."""
    s, c = cle_chemin(source), cle_chemin(cible)
    return c == s or c.startswith(s.rstrip("/") + "/")


def protege(chemin):
    """True si la suppression, le deplacement ou l'ecrasement exige une seconde confirmation : autoexec, persist, .bec, .drvset*, dossiers /sd et /json.
    Comparaison FAT (cle_chemin) : la SD ne distingue ni la casse ni les points et espaces finaux."""
    p = cle_chemin(chemin)
    nom = p.rsplit("/", 1)[-1]
    return p in DOSSIERS_PROTEGES or nom in NOMS_PROTEGES or nom.endswith(".bec") or nom.startswith(".drvset")


def _nom_sain(nom):
    """Nom rendu par la carte : un segment simple (ni `/`, ni `\\`, ni controle, ni . ou ..), sinon il est ignore."""
    return bool(nom) and nom not in (".", "..") and len(nom) <= 255 and "/" not in nom and "\\" not in nom \
        and not any(ord(c) < 32 or ord(c) == 127 for c in nom)


def _lit_ufs(texte):
    """[(type, taille_ko, libre_ko)] d'une reponse `Ufs` (pas du JSON valide a deux supports : lecture par regex)."""
    return [tuple(int(x) for x in m) for m in OBJET_UFS.findall(texte or "")]


def _date_mlsd(valeur):
    """20261103142501 -> 2026-11-03 14:25:01 ; autre forme rendue telle quelle."""
    m = re.fullmatch(r"(\d{4})(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(?:\.\d+)?", valeur or "")
    return "%s-%s-%s %s:%s:%s" % m.groups() if m else (valeur or "")
