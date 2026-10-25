"""Hook PreToolUse (Bash | PowerShell) : refuse un `pio run` pendant un build deja en cours.

Regle du depot (CLAUDE.md, « Vigilances de build ») : jamais de build en parallele de celui de
l'utilisateur, et aucune cible PlatformIO pendant un build, meme un outil (sniffeurs, syslog,
annuaire : ce sont des `pio run`). Deux `pio` qui ecrivent `tasmota/tasmota.ino.cpp` se plantent, et
un `pio run` d'un autre env peut vider tout `.pio/build`.

Appele par `garde_build.sh`, qui ne le lance que si la commande contient « pio » ou « platformio ».
Detection : meme regle que la statusline (~/.claude/statusline.cjs) — seuls `platformio ... run` et
`scons` comptent ; `pio home`, lance en permanence par l'extension PlatformIO, n'est pas un build.

Un `pio run` dont TOUTES les cibles sont des cibles d'outils (CIBLES_OUTILS) n'est pas un build : l'outil
vit tant que la cible vit (annuaire, pont serie...), et le compter ferait attendre sans fin la page de build
et refuser tout `pio run`. Meme regle pour son scons, dont la ligne se termine par les cibles en arguments
nus. Une ligne scons sans cible reconnaissable reste un build. Le hook refuse toujours de LANCER une cible
d'outil pendant un vrai build (c'est un `pio run`, qui peut purger .pio/build).

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
# NOM_CIBLE des outils_docs/scripts_python/build/cible_*.py, recopies ici (le hook tourne en `python -I`,
# sans le depot dans son chemin) ; build/test_garde_build.py verifie que la liste reste alignee.
CIBLES_OUTILS = frozenset({'pont_serie', 'sniffeur_mqtt', 'syslog_tasmota', 'sniffeur_modbus', 'testeur_udp',
                           'synchro_fork', 'annuaire', 'build_web'})
PIO_RUN = re.compile(r'(?:platformio|pio)(?:\.exe)?"?(?:\s+-c\s+\S+)?\s+run\b', re.I)
CIBLE_PIO = re.compile(r'(?:\s-t|\s--target)[\s=]+"?([^\s"]+)')


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
    return analyse_commandes(ps.stdout.splitlines())


def cibles_scons(cmd):
    """Cibles d'une ligne scons de PlatformIO : les arguments nus qui la terminent, apres les variables
    `CLE=valeur` (platform/_run.py, _run_scons). None si scons.py n'y est pas reconnaissable."""
    try:
        mots = [m.strip('"\'') for m in shlex.split(cmd, posix=False)]
    except ValueError:
        return None
    noms = [os.path.basename(m.replace('\\', '/')).lower() for m in mots]
    if 'scons.py' not in noms:
        return None
    debut = noms.index('scons.py') + 1
    cibles = []
    for mot in reversed(mots[debut:]):
        if not mot or mot.startswith('-') or '=' in mot:
            break
        cibles.append(mot)
    return cibles


def analyse_commandes(lignes):
    """Libelles des builds parmi des lignes de commande de processus ([] si aucun)."""
    runs, scons = [], False
    for cmd in lignes:
        if PIO_RUN.search(cmd):
            cibles = CIBLE_PIO.findall(cmd)
            if cibles and set(cibles) <= CIBLES_OUTILS:
                continue                                   # cible d'outil : vit tant que l'outil vit
            env = re.search(r'(?:\s-e|--environment)[\s=]+"?([^\s"]+)', cmd)
            cible = CIBLE_PIO.search(cmd)
            runs.append(' '.join(x.group(1) for x in (env, cible) if x) or 'pio run')
        elif re.search(r'\bscons\b', cmd, re.I):
            cibles = cibles_scons(cmd)
            if cibles and set(cibles) <= CIBLES_OUTILS:
                continue
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
