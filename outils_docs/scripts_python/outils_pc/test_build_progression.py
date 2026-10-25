"""Banc de build_progression (lecture de la sortie de pio) sur des lignes d'essai.

Code de sortie 0 = vert. Aucun appel a pio : le module est pur, il ne fait que lire du texte.
Les lignes sont ecrites d'apres les formats connus de PlatformIO / SCons / esptool, calibrees sur
de vraies sorties (action A8 du plan) ; `build_sortie_reelle_cuve.txt` en est un extrait.
"""

import sys
from pathlib import Path

import build_progression as bp

ECHECS = []
ESC = "\x1b"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def alimente(suivi, lignes):
    """Envoie les lignes ; renvoie le dernier evenement non None."""
    dernier = None
    for texte in lignes:
        ev = suivi.ligne(texte)
        if ev is not None:
            dernier = ev
    return dernier


def compile_n(n):
    return [f"Compiling .pio\\build\\e\\src\\x{i}.o" for i in range(n)]


def test_compilation():
    s = bp.Suivi("compiler", 1680)
    ev = alimente(s, compile_n(840))
    verifie(ev["etape"], "Compilation", "progression_compilation : etape")
    verifie(ev["pourcent"], 50, "progression_compilation : 840/1680 = 50 %")
    verifie(s.nb_o, 840, "progression_compilation : nb_o")
    verifie("840" in ev["detail"] and "1680" in ev["detail"], True, "progression_compilation : detail")


def test_sans_reference():
    s = bp.Suivi("compiler", None)
    ev = alimente(s, compile_n(840))
    verifie(ev["pourcent"], None, "progression_sans_reference : pourcent None")
    verifie(ev["detail"], "840 fichiers", "progression_sans_reference : detail")


def test_ansi():
    verifie(bp.retire_ansi(f"{ESC}[32mCompiling{ESC}[0m x.o"), "Compiling x.o", "progression_ansi : retire_ansi")
    s = bp.Suivi("compiler", 10)
    ev = alimente(s, [f"{ESC}[1;32mCompiling{ESC}[0m .pio/build/e/src/a.o", f"{ESC}[36mCompiling{ESC}[0m .pio\\build\\e\\b.o"])
    verifie(s.nb_o, 2, "progression_ansi : lignes colorees comptees")
    verifie(ev["pourcent"], 20, "progression_ansi : pourcent")


def test_chemins():
    s = bp.Suivi("compiler", 4)
    alimente(s, ["Compiling .pio/build/e/src/a.o", "Compiling .pio\\build\\e\\src\\b.o",
                 "Compiling C:\\Users\\x\\.platformio\\packages\\lib\\c.cpp.o", "Compiling /home/x/d.o"])
    verifie(s.nb_o, 4, "progression_chemins : / et \\")
    s2 = bp.Suivi("compiler", 4)
    alimente(s2, ["Compiling .pio\\build\\e\\src\\a.cpp", "Generating LD script x.ld", "Archiving .pio\\build\\e\\libx.a"])
    verifie(s2.nb_o, 0, "progression_chemins : ce qui n'est pas un .o n'est pas compte")


def test_liens():
    s = bp.Suivi("compiler", 10)
    alimente(s, compile_n(5))
    ev = s.ligne("Linking .pio\\build\\e\\firmware.elf")
    verifie(ev["etape"], "Édition des liens", "progression_liens : etape")
    verifie(s.etape, "Édition des liens", "progression_liens : etape retenue")


def test_esptool():
    s = bp.Suivi("upload", None)
    ev = s.ligne("Writing at 0x00010000 [=====>   ] 45.2% 123456/273000 bytes...")
    verifie((ev["etape"], ev["pourcent"]), ("Téléversement", 45), "progression_esptool : format actuel")
    s = bp.Suivi("upload", None)
    ev = s.ligne("Writing at 0x00010000... (45 %)")
    verifie((ev["etape"], ev["pourcent"]), ("Téléversement", 45), "progression_esptool : ancien format")
    s = bp.Suivi("uploadfs", None)
    ev = s.ligne("Writing at 0x00300000... (90 %)")
    verifie((ev["etape"], ev["pourcent"]), ("Téléversement", 90), "progression_esptool : uploadfs")
    s = bp.Suivi("upload", None)
    ev = s.ligne(f"{ESC}[0mUploading: [========        ] 52%")
    verifie((ev["etape"], ev["pourcent"]), ("Téléversement", 52), "progression_esptool : OTA espota")


def test_succes():
    s = bp.Suivi("compiler", 10)
    alimente(s, compile_n(3))
    ev = s.ligne("========================= [SUCCESS] Took 251.3 seconds =========================")
    verifie(s.resultat, "succes", "progression_succes : resultat")
    verifie(ev["pourcent"], 100, "progression_succes : 100 %")
    verifie(s.extrait_erreur, [], "progression_succes : pas d'extrait")


def test_echec():
    s = bp.Suivi("compiler", 10)
    alimente(s, ["Compiling x.o", "src/a.cpp:12:5: error: 'foo' was not declared in this scope",
                 "*** [.pio\\build\\e\\src\\a.o] Error 1", "ligne anodine",
                 "======== [FAILED] Took 12.3 seconds ========"])
    verifie(s.resultat, "echec", "progression_echec : resultat")
    verifie(len(s.extrait_erreur), 3, "progression_echec : extrait (3 lignes)")
    verifie("'foo'" in s.extrait_erreur[0], True, "progression_echec : erreur du compilateur")
    s = bp.Suivi("compiler", 10)
    alimente(s, [f"erreur-{i} error: x" for i in range(25)])
    verifie((len(s.extrait_erreur), s.extrait_erreur[-1]), (10, "erreur-24 error: x"), "progression_echec : 10 dernieres")


def test_fs_aussi():
    s = bp.Suivi("upload", None)
    verifie(s.fs_aussi, False, "progression_fs_aussi : faux au depart")
    s.ligne("Utilisera une commande de téléchargement personnalisée pour l'opération de flashage afin d'ajouter "
            "le système de fichiers défini pour cette cible de compilation.")
    verifie(s.fs_aussi, True, "progression_fs_aussi : vrai")


def test_buildfs_et_prebuild():
    s = bp.Suivi("buildfs", None)
    verifie(s.etape, "Pré-build", "progression_prebuild : etape de depart")
    ev = s.ligne("Nous allons créer le système de fichiers avec les fichiers suivants:")
    verifie(ev["etape"], "Construction du FS", "progression_buildfs : etape")
    verifie(s.ligne("quelconque"), None, "progression_prebuild : ligne neutre = pas d'evenement")


def test_pourcent_borne():
    s = bp.Suivi("compiler", 100)
    ev = alimente(s, compile_n(500))
    verifie(ev["pourcent"], 99, "pourcent_borne : compilation au-dela de la reference")
    s = bp.Suivi("upload", None)
    ev = s.ligne("Writing at 0x00010000... (100 %)")
    verifie(ev["pourcent"], 99, "pourcent_borne : esptool a 100 % avant SUCCESS")


def repris_n(n):
    return [f"Retrieved `.pio\\build\\e\\lib\\y{i}.cpp.o' from cache" for i in range(n)]


def test_increment():
    # Build incremental (calibrage A8, P4 : 191 Compiling, aucun objet repris) : base = dernier increment
    s = bp.Suivi("compiler", 1682, 190)
    ev = alimente(s, compile_n(95))
    verifie((ev["pourcent"], ev["detail"]), (50, "95/190 fichiers"), "increment : 95/190 = 50 %, pas 95/1682")
    ev = alimente(s, compile_n(1))
    verifie(ev["pourcent"], 50, "increment : toujours sur la base de l'increment")
    s = bp.Suivi("compiler", 1682, 190)
    ev = alimente(s, compile_n(191))
    verifie((ev["pourcent"], ev["detail"]), (11, "191/1682 fichiers"),
            "increment depasse : bascule sur le total (build complet sans cache)")


def test_cache():
    # Build complet (calibrage A8, cuve : 190 Compiling + 1492 repris du cache = 1682 .o sur disque)
    s = bp.Suivi("compiler", 1682, 190)
    ev = alimente(s, repris_n(841))
    verifie((ev["etape"], ev["pourcent"], ev["detail"]), ("Compilation", 50, "841/1682 fichiers"),
            "cache : un objet repris compte, et impose le total")
    ev = alimente(s, ["Retrieved `.pio\\build\\e\\libff5\\libWire.a' from cache"])
    verifie(s.nb_o, 841, "cache : une bibliotheque .a reprise ne compte pas")
    s = bp.Suivi("compiler", None, None)
    ev = alimente(s, repris_n(2) + compile_n(1))
    verifie((ev["pourcent"], ev["detail"]), (None, "3 fichiers"), "cache sans reference : compte seul")


def test_zone():
    s = bp.Suivi("upload")
    alimente(s, ["Writing 'C:\\x\\.pio\\build\\e\\bootloader.bin' at 0x00000000..."])
    ev = alimente(s, ["Writing at 0x00003630 [=====] 100.0% 9.45kB/9.45kB [0s] "])
    verifie((ev["etape"], ev["pourcent"], ev["detail"]), ("Téléversement", 99, "bootloader.bin"),
            "zone : le % d'esptool porte le nom de la zone")
    alimente(s, ["Writing '/x/.pio/build/e/littlefs.bin' at 0x004b0000..."])
    ev = alimente(s, ["Writing at 0x004c0000 [==   ] 12.0% 50kB/440kB [2s] "])
    verifie((ev["pourcent"], ev["detail"]), (12, "littlefs.bin"), "zone : chemin / et nouvelle zone")


def test_sortie_reelle():
    # Vraie sortie tronquee (upload COM12 de la cuve, 2026-10-25), sans la MAC de la carte
    chemin = Path(__file__).with_name("build_sortie_reelle_cuve.txt")
    s = bp.Suivi("upload", 1682, 190)
    etapes, zones = [], []
    for texte in chemin.read_text(encoding="utf-8").splitlines():
        ev = s.ligne(texte)
        if ev and (not etapes or etapes[-1] != ev["etape"]):
            etapes.append(ev["etape"])
        if ev and ev["etape"] == "Téléversement" and ev["detail"] and ev["detail"] not in zones and ev["detail"] != "terminé":
            zones.append(ev["detail"])
    verifie(etapes, ["Compilation", "Édition des liens", "Construction du FS", "Téléversement"],
            "sortie_reelle : enchainement des etapes")
    verifie((s.nb_o, s.fs_aussi, s.resultat, s.pourcent), (6, True, "succes", 100),
            "sortie_reelle : 3 compiles + 3 repris, FS aussi flashe, succes a 100 %")
    verifie(zones, ["bootloader.bin", "partitions.bin", "boot_app0.bin", "tasmota32s3-safeboot.bin",
                    "firmware.bin", "littlefs.bin"], "sortie_reelle : les 6 zones d'esptool nommees")


def principal():
    for t in (test_compilation, test_sans_reference, test_ansi, test_chemins, test_liens, test_esptool,
              test_succes, test_echec, test_fs_aussi, test_buildfs_et_prebuild, test_pourcent_borne,
              test_increment, test_cache, test_zone, test_sortie_reelle):
        t()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
