#!/usr/bin/env python3
"""Banc d'atelier_visuels_icones_web.py : faux `ouvre`, aucun reseau. Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_atelier_visuels_icones_web.py
"""
import json
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import atelier_visuels_icones_web as ico

ECHECS = []
SVG_HOSTILE = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" onload="x()"><script>alert(1)</script>'
               '<image href="http://evil/x.png"/><path d="M0 0h24v24H0z"/></svg>')
COLLECTIONS = {"mdi": {"author": {"name": "Pictogrammers"}, "license": {"spdx": "Apache-2.0", "url": "u"}},
               "fa6-solid": {"author": {"name": "Dave"}, "license": {"spdx": "CC-BY-4.0"}},
               "gpl": {"license": {"spdx": "GPL-3.0"}}}


def verifie(ok, libelle):
    print(("OK   " if ok else "KO   ") + libelle)
    if not ok:
        ECHECS.append(libelle)


def leve(exc, f, libelle):
    try:
        f()
    except exc:
        return verifie(True, libelle)
    except Exception as e:
        return verifie(False, f"{libelle} (autre exception {e!r})")
    verifie(False, libelle + " (rien leve)")


class Faux:
    def __init__(self, taille=0):
        self.urls, self.taille = [], taille

    def __call__(self, url, delai, maxi):
        self.urls.append(url)
        if self.taille:
            return b"x" * self.taille
        if "/search" in url:
            return json.dumps({"icons": ["mdi:camera", "fa6-solid:camera", "gpl:camera", "../x:y"],
                               "collections": COLLECTIONS}).encode()
        if "/collections" in url:
            jeu = url.split("prefix=")[1]
            return json.dumps({jeu: COLLECTIONS[jeu]} if jeu in COLLECTIONS else {}).encode()
        return SVG_HOSTILE.encode()


def main():
    f = Faux()
    r = ico.recherche("camera", f)
    verifie([(x["jeu"], x["permissive"], x["attribution"]) for x in r] == [("mdi", True, False), ("fa6-solid", False, True)],
            "recherche : permissive et attribution gardees, GPL et identifiant douteux ecartes")
    verifie(all(u.startswith("https://api.iconify.design/") for u in f.urls), "recherche : hote fixe")
    for q in ("", "a" * 41, "a&b=c", "x/../y"):
        f2 = Faux()
        leve(ValueError, lambda: ico.recherche(q, f2), f"recherche {q[:12]!r} refusee")
        verifie(not f2.urls, f"recherche {q[:12]!r} : aucune requete")
    s = ico.svg("mdi", "camera", Faux())
    verifie("script" not in s["svg"] and "onload" not in s["svg"] and "image" not in s["svg"] and "<path" in s["svg"],
            "svg hostile nettoye")
    verifie((s["licence"], s["auteur"]) == ("Apache-2.0", "Pictogrammers"), "svg : licence et auteur")
    for jeu, nom in (("../x", "a"), ("MDI", "a"), ("mdi", "a.b"), ("mdi", "a/b"), ("m" * 70, "a"), ("mdi", "A"), ("mdi", "")):
        f2 = Faux()
        leve(ValueError, lambda: ico.svg(jeu, nom, f2), f"svg {jeu[:8]!r}/{nom!r} refuse")
        verifie(not f2.urls, f"svg {jeu[:8]!r}/{nom!r} : aucune requete")
    leve(ValueError, lambda: ico._get("https://evil.example/x", Faux(), None), "hote autre refuse")
    leve(ValueError, lambda: ico._get("https://api.iconify.design.evil.example/x", Faux(), None), "hote voisin refuse")
    leve(ico.HorsLigne, lambda: ico.svg("mdi", "camera", Faux(taille=ico.MAX_OCTETS + 1)), "reponse trop grosse refusee")
    leve(ValueError, lambda: ico.svg("gpl", "camera", Faux()), "svg : licence non permissive refusee")
    verifie([ico.licences_ok(x) for x in ("MIT", "Apache-2.0", "ISC", "CC0-1.0", "Unlicense", "CC-BY-4.0",
                                          "CC-BY-NC-4.0", "GPL-3.0", "", None)]
            == ["permissive"] * 5 + ["attribution", "masquee", "masquee", "masquee", "masquee"], "licences_ok")

    def coupe(*a, **k):
        raise urllib.error.URLError("pas de reseau")
    ancien = urllib.request.OpenerDirector.open
    urllib.request.OpenerDirector.open = coupe
    try:
        leve(ico.HorsLigne, lambda: ico.recherche("camera"), "hors ligne : HorsLigne")
        try:
            ico.recherche("camera")
        except ico.HorsLigne as e:
            verifie("injoignable" in str(e), "hors ligne : message clair")
    finally:
        urllib.request.OpenerDirector.open = ancien
    verifie(ico._SansRedirection().redirect_request(None, None, 302, "", {}, "http://evil") is None, "redirection non suivie")

    with tempfile.TemporaryDirectory() as t:
        cache = Path(t) / "c"
        f = Faux()
        ico.svg("mdi", "camera", f, cache)
        n = len(f.urls)
        ico.svg("mdi", "camera", f, cache)
        verifie(len(f.urls) == n, "cache relu sans nouvelle requete")
        racine = Path(t) / "depot"
        info = ico.svg("mdi", "camera", f, cache)
        p = ico.garde(racine, "mdi", "camera", info)
        registre = p.parent / "LICENCES.md"
        verifie(p.is_file() and "mdi-camera.svg" in registre.read_text(encoding="utf-8"), "garde : fichier et ligne de licence")
        leve(FileExistsError, lambda: ico.garde(racine, "mdi", "camera", info), "garde : ecrasement refuse")
        verifie(registre.read_text(encoding="utf-8").count("mdi-camera.svg") == 1, "garde : pas de ligne en double")
        fa = ico.svg("fa6-solid", "camera", f, cache)
        leve(ValueError, lambda: ico.garde(racine, "fa6-solid", "camera", fa), "garde : attribution sans confirmation refusee")
        verifie(not (p.parent / "fa6-solid-camera.svg").exists(), "garde : rien ecrit sans confirmation")
        ico.garde(racine, "fa6-solid", "camera", fa, confirme_attribution=True)
        verifie((p.parent / "fa6-solid-camera.svg").is_file(), "garde : attribution confirmee")
        ico.garde(racine, "mdi", "tiret", {"svg": "<svg/>", "licence": "MIT", "auteur": "A|B\nC", "origine": "http://x\r\ny"})
        ligne = next(l for l in registre.read_text(encoding="utf-8").splitlines() if "mdi-tiret.svg" in l)
        verifie(ligne.count("|") == 5, "LICENCES.md : | et retours a la ligne nettoyes dans auteur et origine")
        class Bizarre(Faux):
            def __call__(self, url, delai, maxi):
                return b'{"mdi": "pas un objet"}' if "/collections" in url else super().__call__(url, delai, maxi)
        leve(ico.HorsLigne, lambda: ico.svg("mdi", "camera", Bizarre()), "svg : info d'un jeu non dict = HorsLigne (503), pas 500")
        leve(ValueError, lambda: ico.garde(racine, "gpl", "x", {"svg": "<svg/>", "licence": "GPL-3.0"}), "garde : licence masquee refusee")
    print("VERT" if not ECHECS else f"ROUGE : {ECHECS}")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
