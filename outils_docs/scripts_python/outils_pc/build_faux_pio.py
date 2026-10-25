"""Faux pio des bancs de la page Build et televersement : rejoue un scenario, ne compile rien.

Appele a la place de pio.exe par la variable BUILD_WEB_PIO (build_serie.py lance un `.py` avec le
Python courant). Accepte la forme utilisee par la serie :

    build_faux_pio.py run -e <env> [-t nobuild] [-t <cible>] [--upload-port COMn]

Plusieurs -t : la derniere cible choisit le cas ; avec -t nobuild (envoi apres la pause « rebranchez la
carte » : firmware deja compile), la sortie nominale ne rejoue aucune compilation, comme le vrai pio.

Le scenario est un fichier JSON dont le chemin est dans BUILD_WEB_FAUX_SCENARIO :

    {"<env>": {"<cible>": {...}}, "*": {"<cible>": {...}}}

ou <cible> vaut "build" (pas de -t), "upload", "erase_upload", "buildfs" ou "uploadfs", et chaque cas porte :
  - "lignes"    : lignes ecrites sur la sortie ("{env}" remplace ; "@pause S" attend S secondes) ;
  - "delai"     : attente entre deux lignes (0.01 s par defaut) ;
  - "code"      : code de sortie (0 par defaut) ;
  - "o"         : nombre de fichiers .o a creer dans .pio/build/<env>/src/ (cwd = racine du depot) ;
  - "image"     : chemin d'une image LittleFS copiee dans .pio/build/<env>/littlefs.bin (ce qu'ecrit un
                  vrai buildfs ; le faux pio, lance sans site, ne sait pas en fabriquer) ;
  - "petit_fils": lance un processus petit-fils qui dort 60 s (pour verifier que l'arbre est tue).
Sans cas pour l'env ni pour "*", une sortie nominale propre a la cible est rejouee.

Si BUILD_WEB_FAUX_JOURNAL est pose, chaque appel y ajoute des lignes JSON : "debut" (arguments,
cible, port, TASMOTA_OTA_IP, PLATFORMIO_UPLOAD_PORT, PLATFORMIO_EXTRA_SCRIPTS, PYTHONIOENCODING,
PYTHONUTF8, cwd, heure), "petit_fils" (pid) et "fin" (code, heure). Un appel tue en plein vol n'a pas de ligne "fin".
"""

import json
import os
import sys
import time
from pathlib import Path

VAR_SCENARIO = "BUILD_WEB_FAUX_SCENARIO"
VAR_JOURNAL = "BUILD_WEB_FAUX_JOURNAL"

_COMPILE = ["Processing {env} (platform: espressif32)",
            "Compiling .pio\\build\\{env}\\src\\a.cpp.o",
            "Compiling .pio/build/{env}/src/b.cpp.o",
            "Linking .pio/build/{env}/firmware.elf"]
_ENVOI = ["Uploading .pio/build/{env}/firmware.bin",
          "Writing at 0x00010000 (50 %)",
          "Writing at 0x00020000 (100 %)"]
_FS = ["Building FS image from 'data' directory to .pio/build/{env}/littlefs.bin"]
# textes de la cible erase_upload de la plateforme et d'esptool v5.4.0 (voir build_progression, _EFFACEMENT)
_EFFACEMENT = ["Looking for upload port...", "Erasing...", "esptool v5.4.0", "Connecting...", "Uploading stub flasher...",
               "Erasing flash memory (this may take a while)...", "Flash memory erased successfully in 0.10 seconds."]
NOMINAL = {"build": _COMPILE, "upload": _COMPILE + _ENVOI, "erase_upload": _COMPILE + _EFFACEMENT + _ENVOI,
           "buildfs": _FS, "uploadfs": _FS + _ENVOI}


def analyse(argv):
    """(env, cible, port, cibles) d'un appel `run -e X [-t T]... [--upload-port P]` ; ValueError sinon."""
    if not argv or argv[0] != "run":
        raise ValueError(f"faux pio : seule la commande run est simulee ({argv!r})")
    env, cible, port, cibles, i = "", "build", "", [], 1
    while i < len(argv):
        option = argv[i]
        valeur = argv[i + 1] if i + 1 < len(argv) else ""
        if option in ("-e", "--environment"):
            env = valeur
        elif option in ("-t", "--target"):
            cibles.append(valeur)
            cible = valeur
        elif option == "--upload-port":
            port = valeur
        else:
            raise ValueError(f"faux pio : option inattendue {option!r}")
        i += 2
    if not env:
        raise ValueError("faux pio : -e manquant")
    return env, cible, port, cibles


def journalise(**enregistrement):
    chemin = os.environ.get(VAR_JOURNAL)
    if chemin:
        with open(chemin, "a", encoding="utf-8") as f:
            f.write(json.dumps(enregistrement, ensure_ascii=False) + "\n")


def cas(env, cible, cibles=()):
    chemin = os.environ.get(VAR_SCENARIO)
    scenario = json.loads(Path(chemin).read_text(encoding="utf-8")) if chemin else {}
    trouve = (scenario.get(env) or {}).get(cible) or (scenario.get("*") or {}).get(cible) or {}
    resultat = dict(trouve)
    if "lignes" not in resultat:
        fin = "[SUCCESS] Took 0.10 seconds" if not resultat.get("code") else "[FAILED] Took 0.10 seconds"
        nominal = NOMINAL.get(cible, [])
        if "nobuild" in cibles:                          # firmware deja compile : ni compilation ni edition des liens
            nominal = [ligne for ligne in nominal if ligne not in _COMPILE[1:]]
        resultat["lignes"] = nominal + [fin]
    return resultat


def main(argv):
    env, cible, port, cibles = analyse(argv)
    c = cas(env, cible, cibles)
    journalise(type="debut", pid=os.getpid(), argv=argv, env=env, cible=cible, cibles=cibles, port=port,
               ota_ip=os.environ.get("TASMOTA_OTA_IP"),
               platformio_upload_port=os.environ.get("PLATFORMIO_UPLOAD_PORT"),
               platformio_extra_scripts=os.environ.get("PLATFORMIO_EXTRA_SCRIPTS"), pythonioencoding=os.environ.get("PYTHONIOENCODING"),
               pythonutf8=os.environ.get("PYTHONUTF8"), cwd=os.getcwd(), t=time.time())
    if c.get("petit_fils"):
        import subprocess
        fils = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        journalise(type="petit_fils", pid=fils.pid)
        print("petit-fils lance", flush=True)
    delai = float(c.get("delai", 0.01))
    for ligne in c["lignes"]:
        if ligne.startswith("@pause "):
            time.sleep(float(ligne.split()[1]))
            continue
        print(ligne.replace("{env}", env), flush=True)
        time.sleep(delai)
    if c.get("image"):
        dossier = Path(".pio") / "build" / env
        dossier.mkdir(parents=True, exist_ok=True)
        (dossier / "littlefs.bin").write_bytes(Path(c["image"]).read_bytes())
    nb_o = int(c.get("o", 0))
    if nb_o:
        dossier = Path(".pio") / "build" / env / "src"
        dossier.mkdir(parents=True, exist_ok=True)
        for i in range(nb_o):
            (dossier / f"f{i}.cpp.o").write_bytes(b"")
    code = int(c.get("code", 0))
    journalise(type="fin", pid=os.getpid(), code=code, t=time.time())
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
