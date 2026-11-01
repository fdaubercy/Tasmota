#!/usr/bin/env python3
"""Banc de cfg_holder.py : quand le pre-script incremente CFG_HOLDER (plan temps-compilation, A1, 2026-11-01).

Fichiers factices dans un dossier temporaire ; le contrat avec l'ecrivain reel de la ligne exclue passe par la vraie
increment_config_holder du pre-script (extraite par ast, comme test_config_holder.py). Le vrai user_config_override.h
du depot est seulement LU. Puis chaque mutant de cfg_holder.py doit faire echouer au moins un cas.

    python outils_docs/scripts_python/build/test_cfg_holder.py

Code de sortie 0 = vert, 1 = rouge.
"""
import sys
import tempfile
import types
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import test_config_holder                                          # noqa: E402  (charge_fonction, FauxEnv)

SOURCE = (ICI / "cfg_holder.py").read_text(encoding="utf-8")
VRAI_H = ICI.parents[2] / "tasmota" / "user_config_override.h"
ENV = "tasmota32s3-garage-capteurs-cuve-modbus"
H = "#ifndef X\n#if defined(CFG_HOLDER) && (CFG_HOLDER == 4617)\n#undef CFG_HOLDER\n\t\t#define CFG_HOLDER \t\t1604\t\t\t// [Reset 1]\n#endif\n#define STA_SSID1 \"maison\"\n#endif\n"
MUTANTS = {
    "ligne CFG_HOLDER non exclue": ("if not LIGNE_CFG_HOLDER.match", "if True or not LIGNE_CFG_HOLDER.match"),
    "nobuild ignore": ('if "nobuild" in cibles:', 'if False:'),
    "buildfs compte comme firmware": ("return not cibles or", "return True or"),
    "fins de ligne non normalisees": ('.replace(b"\\r\\n", b"\\n")', ""),
    "persist ignore": ('(("user_config_override.h", "h"), ("_persist.json", "persist"))', '(("user_config_override.h", "h"),)'),
    "etat d'un autre env reutilise": ("_lit_etat(fichier).get(env)", "next(iter(_lit_etat(fichier).values()), None)"),
}


def module(source):
    m = types.ModuleType("cfg_holder_essai")
    exec(compile(source, "cfg_holder.py", "exec"), m.__dict__)
    return m


def cas(c):
    """Liste de (nom, ok) ; chaque cas a son dossier temporaire."""
    resultats = []

    def verifie(nom, ok):
        resultats.append((nom, bool(ok)))

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        h, persist, etat = d / "user_config_override.h", d / "_persist.json", d / "cfg_holder.json"
        h.write_text(H, newline="\n")
        persist.write_text('{"serveur": {"topic": "cuve"}}\n', newline="\n")

        verifie("env jamais vu -> increment (temoin)", c.doit_incrementer(ENV, h, persist, etat)[0])
        c.enregistre(ENV, h, persist, etat)
        verifie("rien de change -> pas d'increment", not c.doit_incrementer(ENV, h, persist, etat)[0])

        increment = test_config_holder.charge_fonction(test_config_holder.FauxEnv(str(d)))
        increment()                                                  # vraie fonction : reecrit la ligne, mode texte
        verifie("contrat : apres la vraie increment_config_holder, CFG_HOLDER a change dans le fichier",
                "1605" in h.read_text())
        verifie("contrat : seule la ligne CFG_HOLDER a change -> pas d'increment",
                not c.doit_incrementer(ENV, h, persist, etat)[0])

        h.write_bytes(h.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        verifie("fins de ligne CRLF seules -> pas d'increment", not c.doit_incrementer(ENV, h, persist, etat)[0])

        verifie("autre env jamais vu -> increment", c.doit_incrementer("tasmota32p4-garage-serveur-modbus", h, persist, etat)[0])

        persist.write_text('{"serveur": {"topic": "cuve2"}}\n', newline="\n")
        oui, motif = c.doit_incrementer(ENV, h, persist, etat)
        verifie("persist modifie -> increment, motif le nomme", oui and "_persist.json" in motif)
        c.enregistre(ENV, h, persist, etat)

        h.write_text(H.replace("maison", "garage"), newline="\n")
        oui, motif = c.doit_incrementer(ENV, h, persist, etat)
        verifie("autre ligne du .h modifiee -> increment, motif le nomme", oui and "user_config_override.h" in motif)
        c.enregistre(ENV, h, persist, etat)

        persist.unlink()
        verifie("persist supprime -> increment", c.doit_incrementer(ENV, h, persist, etat)[0])

        etat.write_text("{pas du json", encoding="utf-8")
        verifie("etat illisible -> increment", c.doit_incrementer(ENV, h, persist, etat)[0])
        c.enregistre(ENV, h, persist, etat)
        verifie("etat illisible reecrit par enregistre", not c.doit_incrementer(ENV, h, persist, etat)[0])

    attendus = {(): True, ("upload",): True, ("erase_upload",): True, ("nobuild", "upload"): False,
                ("buildfs",): False, ("uploadfs",): False, ("buildfs", "uploadfs"): False}
    for cibles, attendu in attendus.items():
        verifie(f"construit_firmware{list(cibles)} = {attendu}", c.construit_firmware(cibles) == attendu)

    if VRAI_H.is_file():                                             # lecture seule du vrai fichier
        verifie("vrai user_config_override.h : la ligne CFG_HOLDER est bien retiree de l'empreinte",
                c._empreinte(VRAI_H, sans_cfg_holder=True) != c._empreinte(VRAI_H))
    return resultats


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")     # le pre-script affiche un ✔ (cp1252 sinon)
    echecs = 0
    for nom, ok in cas(module(SOURCE)):
        echecs += 0 if ok else 1
        print(("OK " if ok else "KO ") + nom)
    for nom, (avant, apres) in MUTANTS.items():
        if avant not in SOURCE:
            echecs += 1
            print(f"KO mutant « {nom} » : motif introuvable dans cfg_holder.py")
            continue
        tues = [n for n, ok in cas(module(SOURCE.replace(avant, apres, 1))) if not ok]
        echecs += 0 if tues else 1
        print(("OK " if tues else "KO ") + f"mutant « {nom} » " + (f"tue par : {tues[0]}" if tues else "SURVIT"))
    print("VERT" if echecs == 0 else f"ROUGE : {echecs} echec(s)")
    return 0 if echecs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
