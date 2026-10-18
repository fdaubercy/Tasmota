"""Hook PreToolUse (Bash | PowerShell) : refuse un `pio run` pendant un build deja en cours.

Regle du depot (CLAUDE.md, « Vigilances de build ») : jamais de build en parallele de celui de
l'utilisateur, et aucune cible PlatformIO pendant un build, meme un outil (sniffeurs, syslog,
annuaire : ce sont des `pio run`). Deux `pio` qui ecrivent `tasmota/tasmota.ino.cpp` se plantent, et
un `pio run` d'un autre env peut vider tout `.pio/build`.

Appele par `garde_build.sh`, qui ne le lance que si la commande contient « pio » ou « platformio ».
Detection : meme regle que la statusline (~/.claude/statusline.cjs) — seuls `platformio ... run` et
`scons` comptent ; `pio home`, lance en permanence par l'extension PlatformIO, n'est pas un build.

Sortie 2 = commande refusee (le message part a Claude). Sortie 0 = autorisee.
En cas d'echec de la detection : sortie 1, non bloquante, avec un avertissement.
"""
import json
import os
import re
import shlex
import subprocess
import sys

PIO = {'pio', 'pio.exe', 'platformio', 'platformio.exe'}
PYTHON = {'python', 'python.exe', 'python3', 'py', 'py.exe'}
SEPARATEURS = re.compile(r'\|\||&&|;|\||\n')
AFFECTATION = re.compile(r'^\$?[A-Za-z_][A-Za-z0-9_:]*=')


def lance_pio_run(commande):
    """Vrai si un segment de la commande lance `pio run` / `platformio run` / `python -m platformio run`."""
    for segment in SEPARATEURS.split(commande):
        try:
            mots = shlex.split(segment, posix=False)
        except ValueError:
            mots = segment.split()
        mots = [m.strip('"\'') for m in mots]
        while mots and (AFFECTATION.match(mots[0]) or mots[0] in ('&', 'sudo', 'time', 'nohup', '(', '{')):
            mots = mots[1:]
        if not mots:
            continue
        tete = os.path.basename(mots[0].replace('\\', '/')).lower()
        if tete in PYTHON and len(mots) > 2 and mots[1] == '-m' and mots[2].lower() == 'platformio':
            reste = mots[3:]
        elif tete in PIO:
            reste = mots[1:]
        else:
            continue
        # sauter les options globales (`-c vscode`), puis lire la sous-commande
        i = 0
        while i < len(reste) and reste[i].startswith('-'):
            i += 2 if reste[i] in ('-c', '--caller') else 1
        if i < len(reste) and reste[i] == 'run':
            return True
    return False


def builds_en_cours():
    """Liste des builds en cours (libelles), ou None si la detection a echoue."""
    ps = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
         "Get-CimInstance Win32_Process -Filter \"Name='pio.exe' OR Name='platformio.exe' OR "
         "Name='python.exe'\" | ForEach-Object { $_.CommandLine }"],
        capture_output=True, text=True, timeout=10)
    if ps.returncode != 0:
        return None
    runs, scons = [], False
    for cmd in ps.stdout.splitlines():
        if re.search(r'(?:platformio|pio)(?:\.exe)?"?(?:\s+-c\s+\S+)?\s+run\b', cmd, re.I):
            env = re.search(r'(?:\s-e|--environment)[\s=]+"?([^\s"]+)', cmd)
            cible = re.search(r'(?:\s-t|--target)[\s=]+"?([^\s"]+)', cmd)
            runs.append(' '.join(x.group(1) for x in (env, cible) if x) or 'pio run')
        elif re.search(r'\bscons\b', cmd, re.I):
            scons = True
    return sorted(set(runs)) or (['scons'] if scons else [])


def main():
    try:
        entree = json.load(sys.stdin)
    except ValueError:
        return 0
    commande = (entree.get('tool_input') or {}).get('command') or ''
    if not lance_pio_run(commande):
        return 0
    try:
        builds = builds_en_cours()
    except (OSError, subprocess.TimeoutExpired):
        builds = None
    if builds is None:
        print('garde_build : detection des builds impossible, commande laissee passer.', file=sys.stderr)
        return 1
    if builds:
        print(f"Refuse : un build PlatformIO est deja en cours ({', '.join(builds)}). Regle du depot : "
              "jamais de `pio run` (build, upload, ni cible Custom) pendant un build. Attendre la fin du "
              "build, ou lancer l'outil voulu hors PlatformIO : "
              "python outils_docs/scripts_python/outils_pc/<outil>.py", file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
