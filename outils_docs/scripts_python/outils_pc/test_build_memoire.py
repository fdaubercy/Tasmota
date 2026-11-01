#!/usr/bin/env python3
"""Banc de build_memoire.py (plan temps-compilation, A7) : faux depot temporaire, extraits copies de VRAIS journaux
(cuve S3 du 2026-11-01 06:40, P4 du 2026-11-01 04:32) ; le vrai depot n'est que lu (tables de partitions reelles).
Puis chaque mutant de build_memoire.py doit faire echouer au moins un cas.

    python outils_docs/scripts_python/outils_pc/test_build_memoire.py

Code de sortie 0 = vert, 1 = rouge.
"""
import os
import sys
import tempfile
import types
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
DEPOT = ICI.parents[2]
SOURCE = (ICI / "build_memoire.py").read_text(encoding="utf-8")
ENV = "tasmota32s3-garage-essai-memoire"

JOURNAL_S3 = """--- pio run -e ENV
Memory Type Usage Summary
┌─────────────────────┬──────────────┬──────────┬────────────────┬───────────────┐
│ Memory Type/Section │ Used [bytes] │ Used [%] │ Remain [bytes] │ Total [bytes] │
├─────────────────────┼──────────────┼──────────┼────────────────┼───────────────┤
│ Flash Code          │      1488872 │          │                │               │
│    .text            │      1488872 │          │                │               │
│ Flash Data          │      1336396 │          │                │               │
│    .rodata          │      1336072 │          │                │               │
│ DIRAM               │       129511 │     37.9 │         212249 │        341760 │
│    .text            │        58179 │    17.02 │                │               │
│    .bss             │        51288 │    15.01 │                │               │
│ IRAM                │        16384 │    100.0 │              0 │         16384 │
│    .text            │        15356 │    93.73 │                │               │
│ RTC SLOW            │          468 │    11.43 │           3628 │          4096 │
│ RTC FAST            │           92 │     1.12 │           8100 │          8192 │
└─────────────────────┴──────────────┴──────────┴────────────────┴───────────────┘
Total image size: 2919967 bytes (.bin may be padded larger)
RAM:   [==        ]  21.8% (used 71332 bytes from 327680 bytes)
Flash: [=======   ]  73.0% (used 2919551 bytes from 3997696 bytes)
 -  0x10000  | SAFEBOOT
======================== [SUCCESS] Took 3067.37 seconds ========================
"""
JOURNAL_P4 = """│ DIRAM               │       133488 │    29.97 │         311904 │        445392 │
│    .text            │        68216 │    15.32 │                │               │
│ HP core RAM         │         1408 │    17.19 │           6784 │          8192 │
│ LP RAM              │          488 │     2.11 │          22680 │         23168 │
│    .rtc_noinit      │          468 │     2.02 │                │               │
"""
JOURNAL_ECHEC = "Flash: [=======   ]  99.0% (used 1 bytes from 3997696 bytes)\n[FAILED] Took 655.11 seconds\n"
CENV = f"""[env:base-essai]
board                   = esp32s3-qio_opi
board_build.partitions  = partitions/essai.csv
board_upload.flash_size = 16MB

[env:{ENV}]
extends                 = env:base-essai

[env:sans-table]
board                   = carte-absente
"""
CSV = """# Name,   Type, SubType, Offset,  Size, Flags
nvs,      data, nvs,     0x9000,  0x5000,
otadata,  data, ota,     0xe000,  0x2000,
safeboot, app,  factory, 0x10000, 0xD0000,
app0,     app,  ota_0,   0xE0000, 0x3D0000,
spiffs,   data, spiffs,  0x4B0000,0xB50000,
"""
MUTANTS = {
    "zones sans total gardees": ("for m in _LIGNE_TABLE.finditer(texte) if m.group(4)]", "for m in _LIGNE_TABLE.finditer(texte) if m.group(4) or True]"),    "journal echoue accepte": ('and "[SUCCESS]" in texte', ""),
    "extends ignore": ('opt("board_build.partitions") or ', ""),
    "FS sans arrondi au bloc": ("-(-f.stat().st_size // BLOC_FS) * BLOC_FS", "f.stat().st_size"),
    "suffixe K ignore": ('{"": 1, "k": 1024, "m": 1024 * 1024}[m.group(2).lower()]', "1"),
    "offset vide non aligne": ('alignement = 0x10000 if cols[1] == "app" else 0x1000', "alignement = 1"),
}


def module(source):
    m = types.ModuleType("build_memoire_essai")
    exec(compile(source, "build_memoire.py", "exec"), m.__dict__)
    return m


def faux_depot(d, safeboot):
    (d / "partitions").mkdir()
    (d / "partitions" / "essai.csv").write_text(CSV, encoding="utf-8")
    (d / "platformio_tasmota_cenv.ini").write_text(CENV, encoding="utf-8")
    (d / "variants" / "tasmota").mkdir(parents=True)
    safeboot.write_bytes(b"s" * 795776)
    fs = d / ".pio" / "build" / ENV / "littlefs_data"
    (fs / "sd").mkdir(parents=True)
    (fs / "_persist.json").write_bytes(b"x" * 5000)                  # 2 blocs
    (fs / "sd" / "page.html").write_bytes(b"x" * 10)                 # 1 bloc


def cas(m):
    res = []

    def verifie(nom, ok):
        res.append((nom, bool(ok)))

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        safeboot = d / "variants" / "tasmota" / "tasmota32s3-safeboot.bin"
        faux_depot(d, safeboot)
        j = d / "journaux"
        j.mkdir()
        (j / f"20261101-064021-{ENV}-compiler.log").write_text(JOURNAL_S3.replace("SAFEBOOT", str(safeboot)), encoding="utf-8")
        recent = j / f"20261101-090000-{ENV}-compiler.log"
        recent.write_text(JOURNAL_ECHEC, encoding="utf-8")
        os.utime(recent, (2e9, 2e9))                                # le plus recent est un echec : a ignorer

        r = m.analyse(d, ENV, j)
        parts = {p["nom"]: p for p in r["partitions"]}
        verifie("table lue par extends (5 partitions)", list(parts) == ["nvs", "otadata", "safeboot", "app0", "spiffs"])
        verifie("flash 16 Mo", r["flash"] == 16 * 1024 * 1024)
        verifie("app0 = ligne Flash du journal REUSSI (pas l'echec plus recent)", parts.get("app0", {}).get("utilise") == 2919551)
        verifie("safeboot = binaire cite par le journal", parts.get("safeboot", {}).get("utilise") == 795776)
        verifie("FS estime, arrondi au bloc de 4096 (3 blocs)", parts.get("spiffs", {}).get("utilise") == 3 * 4096 and parts["spiffs"]["estime"])
        zones = {z["zone"]: (z["utilise"], z["total"]) for z in r["ram"]}
        verifie("zones S3 de premier niveau seulement", zones == {"DIRAM": (129511, 341760), "IRAM": (16384, 16384),
                                                                 "RTC SLOW": (468, 4096), "RTC FAST": (92, 8192)})
        verifie("adresse spiffs 0x4B0000", parts.get("spiffs", {}).get("debut") == 0x4B0000)

        r2 = m.analyse(d, "sans-table", j)
        verifie("env sans table : note, aucune partition", not r2["partitions"] and r2["notes"])
        try:
            m.analyse(d, "inconnu", j)
            verifie("env inconnu : LookupError", False)
        except LookupError:
            verifie("env inconnu : LookupError", True)

        m.enregistre(d, ENV, r)
        verifie("enregistre puis relit", m.derniere(d, ENV)["partitions"] == r["partitions"])
        verifie("derniere : absente -> None", m.derniere(d, "autre") is None)

    verifie("zones P4 (DIRAM, HP core RAM, LP RAM)", [z["zone"] for z in m.lit_table_memoire(JOURNAL_P4)] == ["DIRAM", "HP core RAM", "LP RAM"])
    verifie("taille : 0x, decimal, K, M", [m.taille(x) for x in ("0x5000", "20480", "20K", "1M")] == [20480, 20480, 20480, 1048576])
    calc = m.lit_csv("nvs,data,nvs,,20K,\nfactory,app,factory,,1M,\n")
    verifie("offsets vides : nvs 0x9000, app alignee sur 0x10000", [p["debut"] for p in calc] == [0x9000, 0x10000])
    for nom in ("esp32_partition_app3904k_fs11584k.csv", "esp32_partition_app2752k_fs448k.csv"):
        p = m.lit_csv((DEPOT / "partitions" / nom).read_text(encoding="utf-8"))
        fin = p[-1]["debut"] + p[-1]["taille"]
        verifie(f"vraie table {nom} : 5 partitions, fin {fin // 1048576} Mo", len(p) == 5 and fin in (4 * 1048576, 16 * 1048576))
    return res


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    echecs = 0
    for nom, ok in cas(module(SOURCE)):
        echecs += 0 if ok else 1
        print(("OK " if ok else "KO ") + nom)
    for nom, (avant, apres) in MUTANTS.items():
        if avant not in SOURCE:
            echecs += 1
            print(f"KO mutant « {nom} » : motif introuvable")
            continue
        try:
            tues = [n for n, ok in cas(module(SOURCE.replace(avant, apres, 1))) if not ok]
        except Exception as erreur:                                # noqa: BLE001 - un mutant qui plante est tue
            tues = [repr(erreur)]
        echecs += 0 if tues else 1
        print(("OK " if tues else "KO ") + f"mutant « {nom} » " + (f"tue par : {tues[0]}" if tues else "SURVIT"))
    print("VERT" if echecs == 0 else f"ROUGE : {echecs} echec(s)")
    return 0 if echecs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
