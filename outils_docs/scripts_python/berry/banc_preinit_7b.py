r"""Banc du preinit.be de la carte d'affichage des debits (Waveshare ESP32-S3-Touch-LCD-7B) : banc_preinit_7b.be, puis
temoins sur des copies modifiees de preinit.be.

    python outils_docs/scripts_python/berry/banc_preinit_7b.py

Code de sortie 0 si tout est vert. Ne prouve ni l'ordre reel du firmware (preinit avant l'ecran : lu dans tasmota.ino),
ni que l'expandeur reponde a ces registres, ni l'adresse du GT911 sur la vraie carte (essai du plan debits-deux-cartes, A8).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
BERRY = RACINE / "lib/libesp32/berry/berry.exe"
BANC = "outils_docs/scripts_python/berry/banc_preinit_7b.be"
PREINIT = RACINE / "data/bureau/tasmota32s3-ecran-debits-pac/preinit.be"
VERT = "BANC_PREINIT_7B: OK"

# Chaque mutant doit rendre le banc rouge : (nom, texte de preinit.be, remplacement)
MUTANTS = [
    ("EXIO laissees en entree", "w.write(EXPANDEUR, 0x02, 0xFF, 1)", "w.write(EXPANDEUR, 0x02, 0x00, 1)"),
    ("EXIO5 sur le CAN", "var SORTIES = 0xDF", "var SORTIES = 0xFF"),
    ("dalle sans alimentation (EXIO6)", "var SORTIES = 0xDF", "var SORTIES = 0x9F"),
    ("tactile jamais mis en reset", "SORTIES & ~RESET_TACTILE, 1)", "SORTIES, 1)"),
    ("INT laisse haut pendant le reset", "gpio.digital_write(INT_TACTILE, 0)", "gpio.digital_write(INT_TACTILE, 1)"),
    ("attente du GT911 raccourcie", "tasmota.delay(200)", "tasmota.delay(20)"),
    ("INT jamais rendu au pilote", "    gpio.pin_mode(INT_TACTILE, gpio.INPUT)", "    # rendu oublie"),
    ("expandeur absent non controle", "    if w == nil\n", "    if false\n"),
    ("ecritures du debut non controlees", "if !w.write(EXPANDEUR, 0x02, 0xFF, 1) || !w.write(EXPANDEUR, 0x03, SORTIES & ~RESET_TACTILE, 1)",
     "w.write(EXPANDEUR, 0x02, 0xFF, 1)    w.write(EXPANDEUR, 0x03, SORTIES & ~RESET_TACTILE, 1)\n    if false"),
    ("relache du reset non controle", "    if !relache\n", "    if false\n"),
    ("exception non attrapee", "try\n    preinitEcran7B()\nexcept .. as e, m\n", "if true\n    preinitEcran7B()\nelse\n"),
]


def lance_berry(dossier, preinit=None):
    args = [str(BERRY), BANC, str(dossier)] + ([str(preinit)] if preinit else [])
    r = subprocess.run(args, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    return r.stdout + r.stderr


def main():
    texte = PREINIT.read_text(encoding="utf-8").replace("\r\n", "\n")
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        (tmp / "banc").mkdir()
        sortie = lance_berry(tmp / "banc")
        print(sortie.rstrip())
        ok = VERT in sortie
        print("--- Temoins (chaque mutant doit etre rouge)")
        for i, (nom, avant, apres) in enumerate(MUTANTS):
            if texte.count(avant) != 1:
                print(f"  ECHEC temoin « {nom} » : texte absent ou ambigu")
                ok = False
                continue
            d = tmp / f"m{i}"
            d.mkdir()
            copie = d / "preinit.be"
            copie.write_text(texte.replace(avant, apres), encoding="utf-8")
            rouge = VERT not in lance_berry(d, copie)
            print(f"  {'OK   ' if rouge else 'ECHEC'} {nom}")
            ok = ok and rouge
    print("BANC_PREINIT_7B (enveloppe):", "VERT" if ok else "ROUGE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
