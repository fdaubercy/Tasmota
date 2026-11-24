"""Banc de garde_lecture.py : faux depot git temporaire, fausses valeurs, hook en sous-processus, puis mutants.

Lancer : python .claude/hooks/test_garde_lecture.py   (Python standard + git). Affiche VERT ou ROUGE, sort en 0 ou 1.
Chaque mutant est un remplacement de texte sur une COPIE du module ; le banc doit devenir rouge sur chacun.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.join(ICI, 'garde_lecture.py')
FAUX = ['FauxMqtt123', 'FauxWifi456', 'FauxImbrique789', 'FauxSta1Pass', 'FauxFtpPw']
PERSIST = '''{
  "mqtt": {
    "hote": "192.168.0.10",
    "mdp": "FauxMqtt123"
  },
  "reseau1": {
    "ssid": "Maison",
    "mdpWifi": "FauxWifi456"
  },
  "mdpWifi": {
    "reseau2": "FauxImbrique789"
  },
  "declencheur": "FauxPasSecret",
  "AP": { "mdp": "" }
}
'''   # lignes secretes : 4, 8, 11
OVERRIDE = '''#define STA_SSID1 "Maison"
#define STA_PASS1 "FauxSta1Pass"
#define D_PASSWORD "Mot de passe"
#define MQTT_PASS ""
#define PW_FTP "FauxFtpPw"
'''   # lignes secretes : 2, 5
BERRY = '''preproc.define('STA_PASS1', "FauxSta1Pass")
preproc.define('STA_SSID1', "Maison")
'''


def ecrit(depot, rel, texte):
    p = os.path.join(depot, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(texte)


def git(depot, *args):
    return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *args], cwd=depot,
                          capture_output=True, text=True, encoding='utf-8', errors='replace')


def suite(module):
    """Liste des echecs du module donne (vide = vert)."""
    echecs, n = [], [0]
    depot = tempfile.mkdtemp(prefix='garde_lecture_')
    try:
        git(depot, 'init', '-q')
        ecrit(depot, 'data/x/_persist.json', PERSIST)
        ecrit(depot, 'tasmota/user_config_override.h', OVERRIDE)
        ecrit(depot, 'tasmota/tasmota_defines_for_berry.be', BERRY)
        ecrit(depot, 'autre.txt', 'bonjour\nmdp ici\n')
        ecrit(depot, 'schemas/persist.schema.json', '{\n  "mdp": {\n    "type": "string"\n  }\n}\n')
        ecrit(depot, 'schemas/modele_persist.json', '{\n  "mdp": "@secret:wifi1",\n  "pwd": "{{mot_de_passe}}"\n}\n')
        git(depot, 'add', '-A'); git(depot, 'commit', '-q', '-m', 'init')

        def hook(outil, ti, attendu, brut=None):
            n[0] += 1
            entree = brut if brut is not None else json.dumps({'tool_name': outil, 'tool_input': ti, 'cwd': depot})
            r = subprocess.run([sys.executable, module], input=entree.encode(), capture_output=True, cwd=depot, timeout=60)
            if r.returncode != attendu:
                echecs.append(f"{outil} {ti} : code {r.returncode}, attendu {attendu}")
            if any(v.encode() in r.stderr for v in FAUX):
                echecs.append(f"{outil} {ti} : une fausse valeur dans le message")

        def cli(*args, sous=''):
            n[0] += 1
            return subprocess.run([sys.executable, module, *args], capture_output=True, cwd=os.path.join(depot, sous),
                                  timeout=120, text=True, encoding='utf-8', errors='replace')

        P = 'data/x/_persist.json'
        hook('Read', {'file_path': os.path.join(depot, P), 'offset': 1, 'limit': 5}, 2)
        hook('Read', {'file_path': os.path.join(depot, P), 'offset': 1, 'limit': 3}, 0)
        hook('Read', {'file_path': os.path.join(depot, P), 'offset': 12, 'limit': 4}, 0)
        hook('Read', {'file_path': os.path.join(depot, P)}, 2)
        hook('Read', {'file_path': os.path.join(depot, 'autre.txt')}, 0)
        hook('Read', {'file_path': os.path.join(depot, 'schemas/persist.schema.json')}, 0)   # schema : pas un fichier a secrets
        hook('Read', {'file_path': os.path.join(depot, 'tasmota/user_config_override.h'), 'offset': 3, 'limit': 2}, 0)
        hook('Grep', {'pattern': 'mdp', 'path': depot, 'output_mode': 'content'}, 2)
        hook('Grep', {'pattern': 'mdp', 'path': depot, 'output_mode': 'content', 'glob': '!**/*persist*.json'}, 0)
        hook('Grep', {'pattern': 'mdp', 'path': depot, 'output_mode': 'files_with_matches'}, 0)
        hook('Grep', {'pattern': 'mdp', 'path': depot}, 0)
        hook('Grep', {'pattern': 'hote', 'path': depot, 'output_mode': 'content'}, 0)
        hook('Grep', {'pattern': 'hote', 'path': depot, 'output_mode': 'content', '-A': 1}, 2)
        hook('Grep', {'pattern': '(', 'path': depot, 'output_mode': 'content'}, 2)
        hook('Grep', {'pattern': 'PASS', 'path': os.path.join(depot, 'tasmota'), 'output_mode': 'content'}, 2)
        B = lambda c, att: hook('Bash', {'command': c}, att)
        B(f'cat {P}', 2)
        B(f'cat {P} 2>&1 | head -3', 2)
        B(f'echo "$(cat {P})"', 2)
        B(f'cd {depot.replace(chr(92), "/")} && cat {P}', 2)
        B('cat autre.txt', 0)
        B('ls data/x && wc -l data/x/_persist.json', 0)
        B('git diff --stat', 0)
        B('git status --short', 0)
        B(f'git show HEAD:{P}', 2)
        B('git grep -n mdp', 2)
        B("git grep -n mdp -- ':!**/*persist*.json'", 0)
        B('git grep -l mdp', 0)
        B('git grep -n bonjour', 0)
        B('grep -rn mdp data/', 2)
        B(f'grep -n hote {P}', 0)
        B(f'grep -n mdp {P}', 2)
        B(f'grep -c mdp {P}', 0)
        B(f'git add {P}', 0)
        B(f"bash -c 'cat {P}'", 2)
        B(f"python - <<'EOF'\nimport json\nprint(json.load(open('{P}')))\nEOF", 2)
        B(f"python <<'EOF'\nprint(open('{P}').read())\nEOF", 2)
        B(f"python - <<'EOF'\nimport sys, json\nsys.path.insert(0, '.claude/hooks')\nfrom garde_lecture import masque\n"
          f"print(masque(json.load(open('{P}'))))\nEOF", 0)
        B(f'python -c "print(open(\'{P}\').read())"', 2)
        hook('PowerShell', {'command': r'Get-Content data\x\_persist.json'}, 2)
        hook('PowerShell', {'command': r'Get-Content autre.txt | Select-Object -First 2'}, 0)
        hook('Read', None, 2, brut='{"tool_name": "Read", "tool_input": {"file_path": "data/x/_persist.json"')
        hook('Read', None, 0, brut='{"tool_name": "Read", "tool_input": {"file_path": "autre.txt"')
        hook('Read', None, 2, brut=json.dumps({'tool_name': 'Read', 'tool_input': {'file_path': os.path.join(depot, P), 'offset': 'x'}}))
        hook('Read', None, 0, brut=json.dumps({'tool_name': 'Read', 'tool_input': {'file_path': os.path.join(depot, 'autre.txt'), 'offset': 'x'}}))

        # persist modifie hors ligne secrete : git diff le montre, refuse ; un autre fichier passe
        ecrit(depot, P, PERSIST.replace('192.168.0.10', '192.168.0.11'))
        B('git diff', 2)
        B('git diff -- autre.txt', 0)
        B("git diff -- . ':!**/*persist*.json'", 0)
        B('git log -p -1', 2)
        B('git log --oneline -3', 0)

        r = cli('--lire', P)
        if any(v in r.stdout for v in FAUX) or 'FauxPasSecret' not in r.stdout:
            echecs.append('--lire persist : fausse valeur visible ou ligne non secrete masquee')
        if '     4\t    "mdp": "***"' not in r.stdout or '    11\t    "reseau2": "***"' not in r.stdout:
            echecs.append('--lire persist : numeros de ligne ou masque faux')
        r = cli('--lire', 'tasmota/user_config_override.h')
        if any(v in r.stdout for v in FAUX) or 'Mot de passe' not in r.stdout:
            echecs.append('--lire .h : fausse valeur visible ou libelle D_ masque')
        r = cli('--lire', P, '--cle', 'mdpWifi')
        if any(v in r.stdout for v in FAUX) or '***' not in r.stdout:
            echecs.append('--lire --cle : valeur imbriquee non masquee')
        r = cli('--lire', P, '--lignes', '3-4')
        if r.stdout.count('\n') != 2 or 'FauxMqtt123' in r.stdout:
            echecs.append('--lire --lignes : plage fausse')

        ecrit(depot, 'copie.txt', 'avant\nxx FauxWifi456 yy\n')
        r = cli('--cherche-valeurs', 'copie.txt')
        if r.returncode != 1 or 'copie.txt:2' not in r.stdout or any(v in r.stdout for v in FAUX):
            echecs.append(f'--cherche-valeurs copie : code {r.returncode}')
        r = cli('--cherche-valeurs', '../copie.txt', sous='tasmota')
        if r.returncode != 1:
            echecs.append(f'--cherche-valeurs depuis un sous-dossier : code {r.returncode}')
        for args in (('--cherche-valeurs', '--diff', 'nexiste..HEAD'), ('--public', 'nexiste')):
            r = cli(*args)
            if r.returncode != 2:
                echecs.append(f'{" ".join(args)} : code {r.returncode}, attendu 2 (git en echec)')
        r = cli('--cherche-valeurs', 'autre.txt')
        if r.returncode != 0:
            echecs.append('--cherche-valeurs autre.txt : faux positif')
        ecrit(depot, 'marqueur.txt', 'le socle cite @secret:wifi1 et {{mot_de_passe}}\n')
        r = cli('--cherche-valeurs', 'marqueur.txt')
        if r.returncode != 0:
            echecs.append('--cherche-valeurs : un marqueur @secret: ou un gabarit {{...}} pris pour une valeur')
        with open(os.path.join(depot, 'autre.txt'), 'a', encoding='utf-8') as f:
            f.write('cle FauxMqtt123\n')
        r = cli('--cherche-valeurs', '--diff')
        if r.returncode != 1 or 'autre.txt:3' not in r.stdout or any(v in r.stdout for v in FAUX):
            echecs.append(f'--cherche-valeurs --diff : code {r.returncode}')
        git(depot, 'checkout', '-q', '--', 'autre.txt')
        r = cli('--cherche-valeurs', '--diff')
        if r.returncode != 0:
            echecs.append('--cherche-valeurs --diff propre : faux positif')

        ecrit(depot, 'tasmota/user_config_override.h', OVERRIDE + '#define WEB_PASSWORD "FauxNouveau000"\n')
        r = cli('--public', 'HEAD')
        if ('WEB_PASSWORD (14 car.) : NON publique' not in r.stdout or 'mqtt.mdp (11 car.) : deja publique' not in r.stdout
                or 'FauxNouveau000' in r.stdout or any(v in r.stdout for v in FAUX)):
            echecs.append('--public : etats faux ou valeur affichee')
    finally:
        shutil.rmtree(depot, ignore_errors=True)
    return echecs, n[0]


MUTANTS = [
    ('detection JSON neutralisee', "CLE_SECRETE = re.compile(r'mdp", "CLE_SECRETE = re.compile(r'zzzz"),
    ('code 1 au lieu de 2', 'REFUS = 2', 'REFUS = 1'),
    ('lecture masquee desactivee', '        l = l[:d] + MASQUE + l[f:]', '        pass'),
    ('git diff jamais relance', "    if sub not in ('diff',", "    if True or sub not in ('diff',"),
    ('contexte du Grep ignore', 'touchees & lignes_secretes(f)', 'touchees & set()'),
    ('echec de git ignore par la CLI', '    if r.returncode != 0:\n        sys.stderr', '    if False:\n        sys.stderr'),
    ('heredoc ignore','    if prog in PYTHONS and (corps or', '    if prog in PYTHONS and (False or'),
]


def main():
    echecs, n = suite(MODULE)
    for e in echecs:
        print('ECHEC', e)
    print(f"{n} cas, {len(echecs)} echec(s)")
    survivants = []
    with open(MODULE, encoding='utf-8') as f:
        source = f.read()
    for nom, avant, apres in MUTANTS:
        assert avant in source, f"mutant sans effet : {nom}"
        d = tempfile.mkdtemp(prefix='mutant_')
        try:
            p = os.path.join(d, 'garde_lecture.py')
            with open(p, 'w', encoding='utf-8') as f:
                f.write(source.replace(avant, apres))
            tue = bool(suite(p)[0])
        finally:
            shutil.rmtree(d, ignore_errors=True)
        print(f"mutant '{nom}' : {'tue' if tue else 'SURVIT'}")
        if not tue:
            survivants.append(nom)
    vert = not echecs and not survivants
    print(f"{len(MUTANTS)} mutants, {len(survivants)} survivant(s)")
    print('VERT' if vert else 'ROUGE')
    return 0 if vert else 1


if __name__ == '__main__':
    sys.exit(main())
