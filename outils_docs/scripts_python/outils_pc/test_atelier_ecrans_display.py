"""Banc de l'analyseur de display.ini (atelier_ecrans_display.py) et de sa reference (plan atelier-ecrans A15).

UTILISATION (Python de PlatformIO ; quelques secondes)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_ecrans_display.py
Verifie : concordance de outils_docs/schemas/display_ini_parametres.json avec le code (sections `case` du parseur uDisplay,
sous-sections :IC/:IS/:II et :UTI/:UTT/:UTX/:UTY, motifs `strstr(ddesc, ":..")` de xdsp_17, commentaires C retires) ;
aucune ERREUR sur les display.ini du depot (cartes et tasmota/displaydesc) ; chaque piege fabrique detecte ; explication
des arguments. Code de sortie 0 = vert.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atelier_ecrans_catalogue as cat      # noqa: E402
import atelier_ecrans_display as aed        # noqa: E402

RACINE = Path(__file__).resolve().parents[3]
UDISPLAY = RACINE / "lib/lib_display/UDisplay/src/uDisplay.cpp"
XDSP17 = RACINE / "tasmota/tasmota_xdsp_display/xdsp_17_universal.ino"
ECHECS = []
RGB = ":H,ST7262,1024,600,16,RGB,40,41,39,42,2,8,3,46,9,1,5,6,7,15,16,4,45,48,47,21,14,14\n"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)


def sans_commentaires(c):
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", c, flags=re.S))


def sections_du_code(cpp, xdsp):
    """Lignes `:X` que le code lit : lettres du switch du parseur, sous-sections, motifs de xdsp_17."""
    cpp, xdsp = sans_commentaires(cpp), sans_commentaires(xdsp)
    lettres = set(re.findall(r"case '(.)':", cpp))
    res = {":" + l for l in lettres if l not in "IU"}
    if "I" in lettres:
        res |= {":I"} | {":I" + s for s in re.findall(r"\*lp1 == '([CSI])'", cpp)}
    if "U" in lettres:
        res |= {":U" + s for s in re.findall(r'strncmp\(lp1, "(T[ITXY])", 2\)', cpp)}
    res |= {m for m in re.findall(r'strstr\(ddesc, "(:[A-Za-z]+),?"\)', xdsp)}
    return res


def test_concordance(ref):
    code = sections_du_code(UDISPLAY.read_text(encoding="utf-8", errors="replace"),
                            XDSP17.read_text(encoding="utf-8", errors="replace"))
    lignes = {s["ligne"] for s in ref["sections"]} - {"#"}
    verifie(sorted(code - lignes), [], "toute section lue par le code est dans la reference")
    verifie(sorted(lignes - code), [], "toute section de la reference est lue par le code")
    temoin = sections_du_code("case 'H': case 'Z':", "")
    verifie(":Z" in temoin and ":H" in temoin, True, "temoin : une section ajoutee au code est vue")
    verifie(":n" in sections_du_code("", '/* cp = strstr(ddesc, ":n,"); */ cp = strstr(ddesc, ":n,");'), True,
            "temoin : motif actif vu")
    verifie(":n" in sections_du_code("", '/*\n cp = strstr(ddesc, ":n,");\n*/'), False, "temoin : motif en commentaire ignore")


def test_fichiers_du_depot(ref):
    fichiers = sorted(RACINE.glob("data/*/*/display.ini")) + sorted((RACINE / cat.AMONT).glob("*.ini"))
    verifie(len(fichiers) >= 60, True, f"{len(fichiers)} display.ini lus")
    fautifs = {}
    for f in fichiers:
        a = aed.analyse(f.read_text(encoding="utf-8", errors="replace"), ref)
        if a["erreurs"]:
            fautifs[f.relative_to(RACINE).as_posix()] = a["erreurs"][:2]
    verifie(fautifs, {}, "aucune erreur fausse sur les display.ini du depot")


def erreurs(texte, ref):
    a = aed.analyse(texte, ref)
    return " | ".join(a["erreurs"]), " | ".join(a["avertissements"])


def test_pieges(ref):
    base = RGB + ":B,40,34\n:V,1,40,48,40,1,13,3,32,1\n:0,00\n#\n"
    verifie(erreurs(base, ref), ("", ""), "fichier RGB correct : ni erreur ni avertissement")
    cas = [
        (":S,2,1,1,0,40,20\n" + base, "erreurs", "première ligne"),
        (base.replace(",21,14,14\n", ",14\n"), "erreurs", "broches"),
        (base.replace(":0,00", ":0," + "0" * 260), "erreurs", "256"),
        (":H,X,240,240,16,SPI,1,1,2,3,4,5,6,7,40\n:A,2A,2B,2C,16\n:F,2,4,0\n:R,36\n#\n", "erreurs", ":F"),
        (":H,X,240,240,16,SPI,1,1,2,3,4,5,6,7,40\n:f,22,1,F7\n:I\n01,80\n#\n", "erreurs", ":f"),
        (base.replace(":B,40,34", ":B,64"), "avertissements", "255"),
        (base.replace(":0,00", ":0,0G"), "erreurs", "hexadécimal"),
        (base.replace(":B,40,34", ":B,4x,34"), "erreurs", "décimal"),
        (base.replace("#\n", "; ecran RGB et non I2C\n#\n"), "avertissements", "I2C"),
        (base.replace(":H,ST7262,1024,600,16,RGB,40,", ":H,ST7262,1024,600,16,RGB,*,"), "erreurs", "*"),
        (base.replace("#\n", ""), "avertissements", "#"),
        (base.replace(":B,40,34", ":B,40, 34"), "erreurs", "espace"),
        (base.replace(":0,00", ":Q,00"), "avertissements", "inconnue"),
        (":H,X,240,240,16,TRUC,1\n#\n", "erreurs", "bus"),
    ]
    for texte, genre, mot in cas:
        e, a = erreurs(texte, ref)
        verifie(mot.lower() in (e if genre == "erreurs" else a).lower(), True, f"piege « {mot} » -> {genre} ({(e or a)[:90]})")
    ut = RGB + ":UTI,GT911,I1,5d,-1,-1\nRDWM 8140 4\nMV 0 1\n:UTT\nRDW 814E 1\n#\n"
    verifie(erreurs(ut, ref)[0], "", "scripts :UT* : operandes separes par une espace, pas d'erreur")


def test_explication(ref):
    a = aed.analyse(base := RGB + ":B,40,34\n#\n", ref)
    h = a["lignes"][0]
    noms = [x["nom"] for x in h["arguments"]]
    verifie((a["bus"], h["section"], noms[:7], noms[-1], len(noms)), ("RGB", ":H", ["nom", "largeur", "hauteur", "bpp", "bus", "de", "vsync"],
            "frequence", 5 + 5 + 16 + 1), "explication de :H en RGB : arguments nommes, 16 broches de donnees")
    b = a["lignes"][1]
    verifie(([x["nom"] for x in b["arguments"]], b["arguments"][1]["valeur"]), (["lignes_tampon", "drapeaux"], "34"), "explication de :B")
    verifie(len(base.splitlines()), len(a["lignes"]), "une entree par ligne du fichier")


def test_tolerances(ref):
    spi = ":H,X,240,240,16,SPI,*,*,*,*,*,*,*,*,40\n:I\nA8 7F\n67,0;\n:B,40,34\n#\n"
    e, a = erreurs(spi, ref)
    verifie((e, "collé" in a), ("", True), "SPI : * dans bus_spi, octets coupes par une espace, « 0; » : pas d'erreur")
    e, a = erreurs(": commentaire libre\n" + RGB + ":B,40,34 ; tampon\n#\n", ref)
    verifie((e, "fin de ligne" in a), ("", True), "« : » seul et commentaire en fin de ligne : avertissement, pas d'erreur")
    e, a = erreurs(RGB.replace(",14,14\n", ",14\n") + ":B,40,34\n#\n", ref)
    verifie((e, "fréquence absente" in a), ("", True), "RGB sans fréquence : avertissement (255)")


def test_insere(ref):
    texte = RGB + ":B,40,34\n:0,00\n#\n"
    v = aed.insere(texte, ":V", ref).splitlines()
    verifie((v[2], v[3].startswith(":V,"), v[4]), (":0,00", True, "#"), ":V (rang 55) insere apres :B (50) et :0 (41)")
    r = aed.insere(texte, ":R", ref).splitlines()
    verifie((r[1].startswith(":R"), r[2]), (True, ":B,40,34"), ":R (rang 40) insere avant :B (50)")
    s = aed.insere(texte, ":S", ref).splitlines()
    verifie((s[0][:9], s[1].startswith(":S,")), (":H,ST7262", True), ":S insere juste apres :H")
    f = aed.insere(texte, ":TR", ref).splitlines()
    verifie((f[-2].startswith(":TR"), f[-1]), (True, "#"), ":TR insere avant le # final")
    verifie(aed.analyse(aed.insere(texte, ":V", ref), ref)["erreurs"], [], "ligne inseree : sans erreur")


def main():
    ref = json.loads((RACINE / aed.REFERENCE).read_text(encoding="utf-8"))
    test_concordance(ref)
    test_fichiers_du_depot(ref)
    test_pieges(ref)
    test_explication(ref)
    test_tolerances(ref)
    test_insere(ref)
    print(f"\n{len(ECHECS)} echec(s) : " + ("VERT" if not ECHECS else "ROUGE"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
