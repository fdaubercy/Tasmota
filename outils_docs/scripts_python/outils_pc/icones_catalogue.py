"""Catalogue des icones et logos (plan atelier-ecrans A18) : glyphes MDI du firmware, PNG du depot, sites de l'annuaire. LECTURE SEULE.

`construit(racine)` rend {glyphes, pngs, sources, absentes} :
  glyphes  les glyphes de outils_docs/schemas/icones_firmware.json + `usages` (fichiers du depot qui portent leur code servi)
  pngs     les PNG de data/ et de outils_docs/atelier_ecrans/images/ (largeur, hauteur lues dans l'en-tete IHDR, poids)
  sources  les sites des sections 1 a 3 de outils_docs/ICONES_IMAGES_SOURCES.md (nom, url, licence, usage, categorie)
  absentes les codes U+E000..U+F8FF trouves dans les ecrans mais absents du catalogue (carres vides a l'ecran)
Usages cherches dans atelier_ecrans/cartes/*/ecran.json, data/**/pages.jsonl et data/**/*.be : le code ecrit `\\uE335` ou le caractere.
Ni fontTools ni reseau. Banc : test_icones_catalogue.py.
"""
import re
import struct
from pathlib import Path

import atelier_ecrans_icones as ic

MAX_USAGES = 20
MAX_OCTETS = 2 * 1024 * 1024          # un fichier plus gros n'est pas lu (shortcut : un usage dans un fichier geant est manque)
SOURCES = "outils_docs/ICONES_IMAGES_SOURCES.md"
CODE = re.compile(r"\\u([eE][0-9a-fA-F]{3}|[fF][0-8][0-9a-fA-F]{2})|([\ue000-\uf8ff])")
LIEN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _fichiers(racine):
    cartes = sorted((racine / "outils_docs" / "atelier_ecrans" / "cartes").glob("*/ecran.json"))
    data = racine / "data"
    autres = sorted(list(data.rglob("pages.jsonl")) + list(data.rglob("*.be"))) if data.is_dir() else []
    return cartes + autres


def _usages(racine):
    """{code servi en majuscules: [chemins relatifs]} (un chemin une fois par code), plafonne a MAX_USAGES."""
    trouve = {}
    for f in _fichiers(racine):
        try:
            if f.stat().st_size > MAX_OCTETS:
                continue
            texte = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = f.relative_to(racine).as_posix()
        for m in CODE.finditer(texte):
            code = (m.group(1) or format(ord(m.group(2)), "X")).upper()
            liste = trouve.setdefault(code, [])
            if rel not in liste and len(liste) < MAX_USAGES:
                liste.append(rel)
    return trouve


def _png(f):
    """(largeur, hauteur) lus dans l'en-tete IHDR ; None si le fichier n'est pas un PNG lisible."""
    with open(f, "rb") as h:
        tete = h.read(24)
    if len(tete) < 24 or tete[:8] != b"\x89PNG\r\n\x1a\n" or tete[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", tete[16:24])


def _pngs(racine):
    sortie = []
    for base in (racine / "data", racine / "outils_docs" / "atelier_ecrans" / "images"):
        for f in sorted(base.rglob("*.png")) if base.is_dir() else []:
            try:
                taille = _png(f)
                if taille:
                    sortie.append({"chemin": f.relative_to(racine).as_posix(), "largeur": taille[0], "hauteur": taille[1],
                                   "poids": f.stat().st_size})
            except OSError:
                pass
    return sortie


def _propre(texte):
    return LIEN.sub(r"\1", texte).replace("**", "").replace("`", "").strip()


def _sources(racine):
    """Lignes de tableau des sections « ## 1. » a « ## 3. » de l'annuaire."""
    f = racine / SOURCES
    if not f.is_file():
        return []
    sortie, categorie = [], None
    for ligne in f.read_text(encoding="utf-8", errors="replace").splitlines():
        if ligne.startswith("## "):
            categorie = ligne[3:].strip() if re.match(r"## [123]\.", ligne) else None
            continue
        if categorie is None or not ligne.startswith("|"):
            continue
        cases = [c.strip() for c in ligne.strip().strip("|").split("|")]
        if len(cases) < 2 or set(cases[0]) <= set("-: ") or cases[0] in ("Site",):
            continue
        lien = LIEN.search(cases[0])
        sortie.append({"nom": _propre(cases[0]), "url": lien.group(2) if lien else "",
                       "licence": _propre(cases[1]) if len(cases) >= 4 else "", "usage": _propre(cases[-1]), "categorie": categorie})
    return sortie


def construit(racine):
    racine = Path(racine)
    try:
        firmware = ic.charge(racine)["icones"]
    except LookupError:
        firmware = []
    usages = _usages(racine)
    servis = {g["servi"].upper() for g in firmware}
    glyphes = [dict(g, usages=usages.get(g["servi"].upper(), [])) for g in firmware]
    absentes = [{"code": c, "usages": u} for c, u in sorted(usages.items()) if c not in servis]
    return {"glyphes": glyphes, "pngs": _pngs(racine), "sources": _sources(racine), "absentes": absentes}
