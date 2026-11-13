"""Fichiers display.ini de l'onglet « display.ini » de l'atelier des ecrans (plan atelier-ecrans A15, spec § 6.1 et 6.3).

Trois sources (atelier_ecrans_catalogue._fichiers) : cartes `data/<lieu>/<carte>/display.ini` (lecture ici ; on les change
par « Appliquer a la carte », chemin du changement d'ecran), bibliotheque personnelle `outils_docs/atelier_ecrans/display/`
(seule source ecrite par ce module, avec ses `<nom>.notes.md`), amont `tasmota/displaydesc/` (lecture seule : synchro du
fork ; « Copier dans ma bibliotheque » = enregistrer son texte sous un nom de la bibliotheque).
Un nom de la bibliotheque n'est jamais un chemin (NOM) ; une carte ou un fichier amont est cherche dans la liste, jamais
compose a partir de la requete. Ecritures : refus pendant un build, empreinte perimee ; atomiques (Transaction).
Banc : test_atelier_ecrans_display_fichiers.py.
"""
import difflib
import hashlib
import json
import re
import time
from pathlib import Path

import atelier_ecrans_catalogue as cat
import atelier_ecrans_display as adi
import atelier_ecrans_ecriture as aee
import fichiers_berry_sauvegarde as fbs

NOM = re.compile(r"[A-Za-z0-9_-]{1,64}")
MAX_TEXTE = 32 * 1024                   # le plus gros display.ini amont fait ~6 Ko
MAX_NOTE = 4000


def empreinte(octets):
    return None if octets is None else hashlib.sha256(octets).hexdigest()


def _nom_fichier(source, f, envs):
    return envs[0] if source == "carte" else f.stem if source == "perso" else f.name


def liste(racine):
    """[{source, nom, rel, envs, pilote, largeur, hauteur, bpp, bus, tactile}] : cartes, bibliotheque, amont."""
    racine = Path(racine)
    res = []
    for source, f, envs in cat._fichiers(racine):
        res.append({"source": source, "nom": _nom_fichier(source, f, envs), "rel": f.relative_to(racine).as_posix(),
                    "envs": envs, **(cat.lit_ecran(f) or {}), "tactile": cat._tactile(f)})
    return res


def _rel_perso(nom):
    if not isinstance(nom, str) or not NOM.fullmatch(nom):
        raise ValueError("nom de la bibliotheque : lettres, chiffres, - ou _ (64 caracteres au plus), sans .ini")
    return f"{cat.PERSO}/{nom}.ini"


def chemin(racine, source, nom):
    """Chemin relatif du fichier ; LookupError s'il n'est pas dans la liste (perso : nom valide, fichier present ou non)."""
    if source == "perso":
        return _rel_perso(nom)
    for s, f, envs in cat._fichiers(Path(racine)):
        if s == source and _nom_fichier(s, f, envs) == nom:
            return f.relative_to(Path(racine)).as_posix()
    raise LookupError(f"display.ini introuvable : {source} {nom!r}")


def _lit(racine, rel):
    p = Path(racine) / rel
    return p.read_bytes() if p.is_file() else None


def lire(racine, source, nom, ref):
    """{source, nom, rel, texte, empreinte, analyse, notes, modifiable} ; LookupError si absent."""
    rel = chemin(racine, source, nom)
    octets = _lit(racine, rel)
    if octets is None:
        raise LookupError(f"display.ini introuvable : {rel}")
    texte = octets.decode("utf-8", errors="replace")
    notes = _lit(racine, f"{cat.PERSO}/{nom}.notes.md") if source == "perso" else None
    return {"source": source, "nom": nom, "rel": rel, "texte": texte, "empreinte": empreinte(octets),
            "analyse": adi.analyse(texte, ref), "notes": notes.decode("utf-8", errors="replace") if notes else "",
            "modifiable": source == "perso"}


def texte_valide(texte):
    if not isinstance(texte, str) or len(texte) > MAX_TEXTE:
        raise ValueError(f"texte du display.ini attendu ({MAX_TEXTE // 1024} Ko au plus)")
    return texte


def _octets(texte, avant):
    t = texte_valide(texte).replace("\r\n", "\n")
    t = t if t.endswith("\n") else t + "\n"
    if avant is not None and b"\r\n" in avant:      # core.autocrlf : garder les fins de ligne du fichier deja la
        t = t.replace("\n", "\r\n")
    return t.encode("utf-8")


def diff(racine, nom, texte):
    """{rel, diff, ajouts, retraits, change, empreinte (du fichier lu | None)} : rien n'est ecrit."""
    rel = _rel_perso(nom)
    avant = _lit(racine, rel)
    apres = _octets(texte, avant)
    a = [] if avant is None else avant.decode("utf-8", errors="replace").splitlines()
    lignes = list(difflib.unified_diff(a, apres.decode("utf-8").splitlines(), "avant", "apres", lineterm="", n=2))
    return {"rel": rel, "diff": "\n".join(lignes), "change": avant != apres, "empreinte": empreinte(avant),
            "ajouts": sum(1 for l in lignes if l.startswith("+") and not l.startswith("+++")),
            "retraits": sum(1 for l in lignes if l.startswith("-") and not l.startswith("---"))}


def enregistre(racine, nom, texte, empreinte_lue, builds_en_cours):
    """{"ecrits"} ; RuntimeError (rien n'est ecrit) : build en cours, fichier change depuis le diff."""
    aee.refuse_build(builds_en_cours)
    racine = Path(racine)
    rel = _rel_perso(nom)
    avant = _lit(racine, rel)
    if empreinte(avant) != empreinte_lue:
        raise RuntimeError(f"{rel} modifie depuis le diff : refaire le diff, rien n'est ecrit")
    apres = _octets(texte, avant)
    if apres == avant:
        return {"ecrits": []}
    (racine / cat.PERSO).mkdir(parents=True, exist_ok=True)
    ecrits = [rel]
    with fbs.Transaction(racine, "atelier-ecrans-display") as tr:
        tr.ecrit(rel, apres)                         # d'abord le fichier : cat.ecrans le relit (ecran de la bibliotheque)
        catalogue = {**cat.charge(racine), "ecrans": cat.ecrans(racine)}     # objets et polices inchanges
        catalogue = (json.dumps(catalogue, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
        if catalogue != _lit(racine, cat.CATALOGUE):
            tr.ecrit(cat.CATALOGUE, catalogue)
            ecrits.append(cat.CATALOGUE)
    return {"ecrits": ecrits}


def ajoute_note(racine, nom, carte, texte, builds_en_cours, maintenant=None):
    """Observation datee ajoutee a `<nom>.notes.md` (fichier de la bibliotheque present) ; {"notes"}."""
    if _lit(racine, _rel_perso(nom)) is None:
        raise LookupError(f"{nom}.ini absent de la bibliotheque : l'enregistrer avant d'y noter")
    if not isinstance(texte, str) or not texte.strip() or len(texte) > MAX_NOTE:
        raise ValueError(f"note attendue (1 a {MAX_NOTE} caracteres)")
    aee.refuse_build(builds_en_cours)
    rel = f"{cat.PERSO}/{nom}.notes.md"
    avant = (_lit(racine, rel) or f"# Notes de terrain : {nom}.ini\n".encode("utf-8")).decode("utf-8", errors="replace")
    date = maintenant or time.strftime("%Y-%m-%d %H:%M")
    notes = avant.rstrip("\n") + f"\n\n## {date}{' (' + carte + ')' if carte else ''}\n{texte.strip().replace(chr(13), '')}\n"
    with fbs.Transaction(Path(racine), "atelier-ecrans-notes") as tr:
        tr.ecrit(rel, notes.encode("utf-8"))
    return {"notes": notes}
