#!/usr/bin/env python3
"""Banc de atelier_visuels_fond.py : nettoyage du SVG (vigilance 1 du plan) et seuils de poids. Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_atelier_visuels_fond.py
"""
import sys
import xml.etree.ElementTree as ET

import atelier_visuels_fond as avf

ECHECS = []
NS = "http://www.w3.org/2000/svg"
SAIN = (f'<svg xmlns="{NS}" viewBox="0 0 480 360" width="480" height="360"><defs><pattern id="b" width="8" height="4" patternUnits="userSpaceOnUse">'
        f'<rect width="8" height="4" fill="#a55"/></pattern></defs><g transform="translate(1,2)"><path d="M0 0L10 10" fill="#fff" stroke="#000" stroke-width="2" opacity="0.5"/>'
        f'<rect x="1" y="2" width="30" height="40" fill="url(#b)"/><polygon points="0,0 5,5 0,9"/><circle cx="5" cy="5" r="3"/><line x1="0" y1="0" x2="9" y2="9"/>'
        f'<text x="3" y="4">No 12</text></g></svg>')


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def refuse(texte):
    try:
        avf.nettoie_svg(texte)
    except ValueError as e:
        return str(e)
    return None


def canon(texte):
    return ET.tostring(ET.fromstring(texte), encoding="unicode")


def svg(corps, attrs=""):
    return f'<svg xmlns="{NS}" {attrs}>{corps}</svg>'


def main():
    verifie(canon(avf.nettoie_svg(SAIN)), canon(SAIN), "SVG sain : meme arbre (formes, motif, texte, attributs) apres nettoyage")
    for libelle, corps, absent in (
        ("script", '<script>alert(1)</script><path d="M0 0"/>', "script"),
        ("a", '<a href="http://x"><path d="M0 0"/></a><path d="M1 1"/>', "href"),
        ("image", '<image href="http://x/i.png"/><path d="M0 0"/>', "image"),
        ("foreignObject", '<foreignObject><div>x</div></foreignObject><path d="M0 0"/>', "foreignObject"),
        ("style avec url(", '<style>rect{fill:url(http://x/a)}</style><path d="M0 0"/>', "style"),
        ("onload", '<path d="M0 0" onload="alert(1)" onclick="x()"/>', "on"),
        ("style en attribut", '<path d="M0 0" style="fill:url(http://x)"/>', "url("),
        ("xlink:href", '<path xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="http://x" d="M0 0"/>', "href"),
        ("fill url externe", '<path d="M0 0" fill="url(http://x/a)"/>', "x/a"),
        ("javascript:", '<path d="M0 0" fill="javascript:alert(1)"/>', "javascript"),
    ):
        try:
            sortie = avf.nettoie_svg(svg(corps))
        except ValueError as e:
            sortie, absent = "", None
            verifie(False, True, f"{libelle} : nettoyage (refus inattendu {e})")
        if absent is not None:
            verifie((absent in sortie, "<path" in sortie), (False, True), f"{libelle} : retire, le reste du dessin garde")
    verifie(avf.nettoie_svg(svg("<script>x</script>", 'onload="x()"')).count("onload"), 0, "onload sur la racine : retire")
    verifie("DOCTYPE" in (refuse(f'<!DOCTYPE svg SYSTEM "http://x/a.dtd">{SAIN}') or ""), True, "DOCTYPE : refuse")
    verifie(refuse(f'<!DOCTYPE svg [<!ENTITY a "bbbbbbbb">]>{svg("<text>&a;</text>")}') is not None, True, "entite interne : refusee")
    verifie(refuse(svg('<text>&a;</text>')) is not None, True, "entite non declaree : refusee")
    verifie(refuse("<html><body>pas du svg</body></html>") is not None, True, "HTML : ValueError")
    verifie(refuse("pas du xml") is not None, True, "texte quelconque : ValueError")
    verifie(refuse("<svg><path d='M0 0'/></svg>") is not None, True, "svg sans espace de noms : ValueError")
    # poids : 50 Ko ESP32 = avertissement, 70 Ko ESP32 = refus, 150 Ko S3 = rien
    verifie("alleger" in (avf.controle_fond("svg", b"x" * 50 * 1024, "ESP32") or ""), True, "50 Ko sur ESP32 : avertissement")
    verifie(avf.refuse(b"x" * 50 * 1024, "ESP32"), False, "50 Ko sur ESP32 : pas un refus")
    verifie(avf.refuse(b"x" * 70 * 1024, "ESP32"), True, "70 Ko sur ESP32 : refus")
    verifie("seuil" in (avf.controle_fond("svg", b"x" * 70 * 1024, "ESP32") or ""), True, "70 Ko sur ESP32 : message de refus")
    verifie(avf.controle_fond("svg", b"x" * 30 * 1024, "ESP32"), None, "30 Ko sur ESP32 : rien")
    verifie("alleger" in (avf.controle_fond("svg", b"x" * 150 * 1024, "S3") or ""), True, "150 Ko sur S3 : avertissement, pas de refus")
    verifie(avf.refuse(b"x" * 150 * 1024, "S3"), False, "150 Ko sur S3 : pas un refus")
    verifie(avf.refuse(b"x" * 201 * 1024, "S3"), True, "201 Ko sur S3 : refus")
    for t, o in (("bmp", b"x"), ("webp", b"pas une image"), ("jpg", b"RIFF....WEBP")):
        try:
            avf.controle_fond(t, o, "S3")
            verifie(False, True, f"type/contenu {t} refuse")
        except ValueError:
            verifie(True, True, f"type/contenu {t} refuse")
    verifie(avf.controle_fond("webp", b"RIFF\0\0\0\0WEBPVP8 ", "S3"), None, "entete WebP valide accepte")
    print("VERT" if not ECHECS else f"ROUGE : {ECHECS}")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
