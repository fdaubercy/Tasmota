#!/usr/bin/env python3
"""Banc de cfg_holder.py : quand le pre-script incremente CFG_HOLDER (plan temps-compilation, A1, 2026-11-01).

Fichiers factices dans un dossier temporaire ; le contrat avec l'ecrivain reel de la ligne exclue passe par la vraie
increment_config_holder du pre-script (extraite par ast, comme test_config_holder.py). Le vrai user_config_override.h
du depot est seulement LU. Puis chaque mutant de cfg_holder.py doit faire echouer au moins un cas.

    python outils_docs/scripts_python/build/test_cfg_holder.py

Code de sortie 0 = vert, 1 = rouge.
"""
import hashlib
import sys
import tempfile
import types
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import test_config_holder                                          # noqa: E402  (charge_fonction, FauxEnv)

SOURCE = (ICI / "cfg_holder.py").read_text(encoding="utf-8")
VRAI_H = ICI.parents[2] / "tasmota" / "user_config_override.h"
H = "#ifndef X\n#if defined(CFG_HOLDER) && (CFG_HOLDER == 4617)\n#undef CFG_HOLDER\n\t\t#define CFG_HOLDER \t\t1604\t\t\t// [Reset 1]\n#endif\n#define STA_SSID1 \"maison\"\n#endif\n"
MUTANTS = {
    "ligne CFG_HOLDER non exclue": ("and not LIGNE_CFG_HOLDER.match(l)", "and True"),
    "nobuild ignore": ('if "nobuild" in cibles:', 'if False:'),
    "buildfs compte comme firmware": ("return not cibles or", "return True or"),
    "fins de ligne non normalisees": ('.replace(b"\\r\\n", b"\\n")', ""),
    "changement du .h ignore": ("if connu != empreinte(chemin_h, noms):", "if False:"),
    "etat absent = pas d'increment": ("if connu is None:\n        return True", "if connu is None:\n        return False"),
    "sections des autres envs comptees": ("if (d, f) != sienne for i", "if False for i"),
    "etat d'un seul env garde": ("envs[env] = empreinte", "envs = {}\n        envs[env] = empreinte"),
    "section : pas de rebouclage": ("apres = 1 if avant >= 65535 else avant + 1", "apres = avant + 1"),
    "ancien etat commun ignore": ('if connu is None and etat.get("h")', 'if False and etat.get("h")'),
    "ancien etat commun sans controle": ('etat["h"] == _empreinte_commune(chemin_h)', "True"),
    "fin de section ignoree": ("if ouverte and FIN_SECTION.match(l):", "if False:"),
}

# Chaine des firmwares comme dans le vrai .h (titres a 8 espaces, corps a 12)
H2 = ("#ifndef X\n#if defined(CFG_HOLDER) && (CFG_HOLDER == 4617)\n#undef CFG_HOLDER\n\t\t#define CFG_HOLDER \t\t1600\t\t\t// [Reset 1]\n"
      "#endif\n#define COMMUN 1\n        #if defined(FIRMWARE_A) || defined(FIRMWARE_A2)\n            #define SSID \"a\"\n"
      "        #elif defined(FIRMWARE_B)\n            #define SSID \"b\"\n        #endif\n#endif\n")


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
        h, etat = d / "user_config_override.h", d / "cfg_holder.json"
        h.write_text(H, newline="\n")

        verifie("etat absent -> increment (temoin)", c.doit_incrementer(h, "e", (), etat)[0])
        c.enregistre(h, "e", (), etat)
        verifie("rien de change -> pas d'increment", not c.doit_incrementer(h, "e", (), etat)[0])

        increment = test_config_holder.charge_fonction(test_config_holder.FauxEnv(str(d)))
        increment()                                                  # vraie fonction : reecrit la ligne, mode texte
        verifie("contrat : la vraie increment_config_holder a bien change CFG_HOLDER", "1605" in h.read_text())
        verifie("contrat : seule la ligne CFG_HOLDER a change -> pas d'increment", not c.doit_incrementer(h, "e", (), etat)[0])

        h.write_bytes(h.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        verifie("fins de ligne CRLF seules -> pas d'increment", not c.doit_incrementer(h, "e", (), etat)[0])

        h.write_text(H.replace("maison", "garage"), newline="\n")
        oui, motif = c.doit_incrementer(h, "e", (), etat)
        verifie("autre ligne du .h modifiee -> increment, motif le nomme", oui and "user_config_override.h" in motif)
        c.enregistre(h, "e", (), etat)
        verifie("apres enregistrement -> pas d'increment", not c.doit_incrementer(h, "e", (), etat)[0])

        etat.write_text("{pas du json", encoding="utf-8")
        verifie("etat illisible -> increment", c.doit_incrementer(h, "e", (), etat)[0])
        c.enregistre(h, "e", (), etat)
        verifie("etat illisible reecrit par enregistre", not c.doit_incrementer(h, "e", (), etat)[0])

        etat.write_text('{"h": "ancien format commun"}', encoding="utf-8")
        verifie("ancien etat commun perime -> increment", c.doit_incrementer(h, "e", (), etat)[0])
        commun = hashlib.sha1(b"\n".join(l for l in h.read_bytes().replace(b"\r\n", b"\n").split(b"\n")
                                         if not l.lstrip().startswith(b"#define CFG_HOLDER"))).hexdigest()
        etat.write_text('{"h": "%s"}' % commun, encoding="utf-8")
        verifie("ancien etat commun a jour -> repris, pas d'increment", not c.doit_incrementer(h, "e", (), etat)[0])
        verifie("ancien etat commun repris : env enregistre, h garde", '"envs"' in etat.read_text() and '"h"' in etat.read_text()
                and not c.doit_incrementer(h, "f", (), etat)[0])
        h.write_text(H.replace("maison", "cave"), newline="\n")
        verifie("ancien etat commun repris puis .h modifie -> increment", c.doit_incrementer(h, "e", (), etat)[0]
                and c.doit_incrementer(h, "g", (), etat)[0])

    with tempfile.TemporaryDirectory() as d:                         # CFG_HOLDER par env (sections du .h)
        d = Path(d)
        h, etat = d / "user_config_override.h", d / "cfg_holder.json"
        h.write_bytes(H2.replace("\n", "\r\n").encode())
        A, A2, B = {"FIRMWARE_A"}, {"FIRMWARE_A2", "AUTRE"}, {"FIRMWARE_B"}
        verifie("defines lus des build_flags", c.defines(["-DFIRMWARE_A", "-D FIRMWARE_B=1 -DX"]) == {"FIRMWARE_A", "FIRMWARE_B", "X"})
        verifie("section : 1er increment -> lignes posees, valeur commune + 1", c.incremente_section(h, A) == (1600, 1601))
        texte = h.read_bytes()
        verifie("section : fins de ligne CRLF gardees", b"\r\n" in texte and b"\n" not in texte.replace(b"\r\n", b""))
        verifie("section : la ligne commune ne bouge pas", b"CFG_HOLDER \t\t1600" in texte)
        verifie("section : increment suivant -> sa ligne, pas de doublon", c.incremente_section(h, A2) == (1601, 1602)
                and h.read_bytes().count(b"#undef CFG_HOLDER") == 2)
        verifie("section : env sans section -> None (ligne commune)", c.incremente_section(h, {"FIRMWARE_Z"}) is None)
        c.enregistre(h, "a", A, etat)
        c.enregistre(h, "b", B, etat)
        verifie("par env : rien de change -> ni a ni b", not c.doit_incrementer(h, "a", A, etat)[0] and not c.doit_incrementer(h, "b", B, etat)[0])
        c.incremente_section(h, A)
        verifie("par env : CFG_HOLDER de a change -> ni a ni b", not c.doit_incrementer(h, "a", A, etat)[0] and not c.doit_incrementer(h, "b", B, etat)[0])
        h.write_bytes(h.read_bytes().replace(b'SSID "a"', b'SSID "a2"'))
        verifie("par env : section de a modifiee -> a seulement", c.doit_incrementer(h, "a", A, etat)[0] and not c.doit_incrementer(h, "b", B, etat)[0])
        c.enregistre(h, "a", A, etat)
        verifie("par env : enregistrer a garde l'etat de b", not c.doit_incrementer(h, "b", B, etat)[0])
        h.write_bytes(h.read_bytes().replace(b"COMMUN 1", b"COMMUN 2"))
        verifie("par env : partie commune modifiee -> a et b", c.doit_incrementer(h, "a", A, etat)[0] and c.doit_incrementer(h, "b", B, etat)[0])
        h.write_bytes(h.read_bytes().replace(b"CFG_HOLDER  1603", b"CFG_HOLDER  65535"))
        verifie("section : 65535 -> 1", c.incremente_section(h, A) == (65535, 1))

    attendus = {(): True, ("upload",): True, ("erase_upload",): True, ("nobuild", "upload"): False,
                ("buildfs",): False, ("uploadfs",): False, ("buildfs", "uploadfs"): False}
    for cibles, attendu in attendus.items():
        verifie(f"construit_firmware{list(cibles)} = {attendu}", c.construit_firmware(cibles) == attendu)

    if VRAI_H.is_file():                                             # lecture seule du vrai fichier
        brut = hashlib.sha1(VRAI_H.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        verifie("vrai user_config_override.h : la ligne CFG_HOLDER est bien retiree de l'empreinte", c.empreinte(VRAI_H) != brut)
        lignes = VRAI_H.read_bytes().replace(b"\r\n", b"\n").split(b"\n")
        verifie("vrai .h : sections des cartes reconnues (cuve, P4)", {"FIRMWARE_ESP32S3_CAPTEURS_CUVE_MODBUS", "FIRMWARE_ESP32P4_GARAGE_SERVEUR_MODBUS"}
                <= set().union(*[n for _, _, n in c.sections(lignes)]))
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
