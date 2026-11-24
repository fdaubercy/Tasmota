"""Garde des secrets a la LECTURE : hook PreToolUse (Read, Grep, Bash, PowerShell) et lecteur masque.

Refuse (code 2, message sur stderr) un appel d'outil qui AFFICHERAIT une ligne secrete d'un fichier protege :
`*persist*.json` (et `_persist.json.*`), `user_config_override.h*`, `tasmota_defines_for_berry.*`, tout fichier sous
un dossier `sauvegardes_cartes`. Un fichier protege sans ligne secrete, ou une plage qui les evite, reste lisible.
Code 1 ne bloque rien : seul le code 2 refuse. Exception interne : 2 si l'entree cite un fichier protege, sinon 0.

CLI (jamais une valeur secrete affichee) :
  --lire <fichier> [--lignes A-B] [--cle a.b.c]   fichier numerote, valeurs secretes remplacees par ***
  --cherche-valeurs [chemins] [--diff [PLAGE]] [--cached]   valeurs secretes recopiees ailleurs (code 1 si trouvee)
  --public REV                                    chaque valeur secrete : deja publique dans REV ou non
Import : `sys.path.insert(0, ".claude/hooks"); from garde_lecture import masque`.
Banc : .claude/hooks/test_garde_lecture.py
"""
import bisect
import fnmatch
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

REFUS = 2
MASQUE = '***'
FIN = time.monotonic() + 25   # budget du hook (timeout conseille : 30 s)
CLE_SECRETE = re.compile(r'mdp\w*|pwd|password|passwd|motdepasse|secret\w*|token\w*|psk\w*|api_?key', re.I)
NOM_DEFINE = r'(?!D_)(?:PW_\w+|\w*(?:PASS|PSK|TOKEN|SECRET|API_?KEY)\w*)'
DEFINE = re.compile(r'#\s*define\s+(' + NOM_DEFINE + r')\s+"((?:[^"\\]|\\.)+)"')
PREPROC = re.compile(r'''preproc\.define\(\s*['"](''' + NOM_DEFINE + r''')['"]\s*,\s*"((?:[^"\\]|\\.)+)"''')
VAL = r'''["']?[^\s"'$<{%(.\[]'''
# reprise de ~/.claude/helpers/garde_commit.cjs (SECRETS), sans ses deux entrees define et champ JSON (detecteurs dedies)
SECRETS = [(n, re.compile(r)) for n, r in [
    ('cle Anthropic', r'sk-ant-(?:api|oat)\d\d-[\w-]{20,}'), ('cle AWS', r'AKIA[0-9A-Z]{16}'),
    ('jeton GitHub', r'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}'), ('jeton Slack', r'xox[baprs]-[A-Za-z0-9-]{10,}'),
    ('cle privee', r'-----BEGIN [A-Z ]*PRIVATE KEY-----'), ('cle Google', r'AIza[\w-]{30,}'),
    ('mot de passe PuTTY', r'(?:plink|pscp|psftp)\b.*\s-pw\s+' + VAL), ('mot de passe sudo', r'echo\s+' + VAL + r'\S*\s*\|\s*sudo\s+-S'),
    ('mot de passe sshpass', r'sshpass\s+-p\s*' + VAL),
    ('commande Tasmota', r'\b(?:MqttPassword|WebPassword|RgxPassword|Password[12])\s+[^\s;"$%<{]')]]
PROTEGE_RE = re.compile(r'persist|user_config_override|defines_for_berry|sauvegardes_cartes', re.I)
DECLENCHE = re.compile(PROTEGE_RE.pattern + r'|\bgrep\b|\brg\b|select-string|\bsls\b|findstr|\bgit\b|\bbash\b|\bsh\b|pwsh|powershell', re.I)
IMPRIME = re.compile(r'print\s*\(|pprint|sys\.stdout|console\.log|process\.stdout|Write-(?:Output|Host)', re.I)
CONSEIL = ("Lire un fichier a secrets : python .claude/hooks/garde_lecture.py --lire <fichier> [--lignes A-B] [--cle a.b] "
           "(valeurs masquees). Rechercher : exclure les fichiers a secrets (Grep glob \"!**/*persist*.json\", "
           "git grep ... -- ':!**/*persist*.json', rg --glob '!**/*persist*.json') ou passer en mode liste (-l, -c, --stat).")


# ---------- noyau : fichiers proteges et lignes secretes ----------
def est_protege(chemin):
    p = str(chemin).replace('\\', '/').lower()
    nom = p.rsplit('/', 1)[-1]
    if nom.endswith('.schema.json'):   # schema JSON : ses "type": "string" sous mdp ne sont pas des valeurs
        return False
    return bool(('persist' in nom and re.search(r'\.json(\.|$)', nom)) or nom.startswith('user_config_override.h')
                or nom.startswith('tasmota_defines_for_berry.') or 'sauvegardes_cartes' in p.split('/')[:-1])


def _scan_json(lignes):
    """Chaines sous une cle secrete, a toute profondeur (pile d'accolades, chaines respectees)."""
    res, pile, cle = [], [(None, False)], None   # pile : (nom du conteneur, secret)
    for n, l in enumerate(lignes, 1):
        i = 0
        while i < len(l):
            c = l[i]
            if c == '"':
                j = i + 1
                while j < len(l) and l[j] != '"':
                    j += 2 if l[j] == '\\' else 1
                s, fin = l[i + 1:min(j, len(l))], min(j, len(l))
                if l[j + 1:].lstrip().startswith(':'):
                    cle = s
                else:
                    nom, secret = pile[-1]
                    if s and (secret or (cle is not None and CLE_SECRETE.fullmatch(cle))):
                        res.append((n, i + 1, fin, '.'.join(x for x in (nom, cle) if x), s))
                    cle = None
                i = j + 1
                continue
            if c in '{[':
                nom, secret = pile[-1]
                pile.append(('.'.join(x for x in (nom, cle) if x), secret or bool(cle and CLE_SECRETE.fullmatch(cle))))
                cle = None
            elif c in '}]':
                if len(pile) > 1:
                    pile.pop()
                cle = None
            elif c == ',':
                cle = None
            i += 1
    return res


def secrets_du_texte(texte):
    """[(ligne, debut, fin, cle, valeur)] ; valeur None quand elle n'est pas une valeur a rechercher ailleurs."""
    lignes = texte.split('\n')
    res = _scan_json(lignes)
    for n, l in enumerate(lignes, 1):
        for rx in (DEFINE, PREPROC):
            for m in rx.finditer(l):
                res.append((n, m.start(2), m.end(2), m.group(1), m.group(2)))
        for nom, rx in SECRETS:
            for m in rx.finditer(l):
                f = m.end()
                while f < len(l) and l[f] not in ' \t"\',;':
                    f += 1
                res.append((n, m.start(), f, nom, None if nom == 'cle privee' else l[m.start():f].split()[-1]))
    return res


_CACHE = {}


def _lit(chemin):
    with open(chemin, encoding='utf-8', errors='replace') as f:
        return f.read()


def secrets_du_fichier(chemin):
    if chemin not in _CACHE:
        try:
            _CACHE[chemin] = secrets_du_texte(_lit(chemin))
        except OSError:
            _CACHE[chemin] = []
    return _CACHE[chemin]


def lignes_secretes(chemin):
    return {s[0] for s in secrets_du_fichier(chemin)}


def masque(obj, secret=False):
    """Copie recursive : valeur sous une cle secrete (a toute profondeur) ou qui ressemble a un secret -> ***."""
    if isinstance(obj, dict):
        return {k: masque(v, secret or bool(CLE_SECRETE.fullmatch(str(k)))) for k, v in obj.items()}
    if isinstance(obj, list):
        return [masque(v, secret) for v in obj]
    if secret and obj not in ('', None):
        return MASQUE
    if isinstance(obj, str) and any(rx.search(obj) for _, rx in SECRETS):
        return MASQUE
    return obj


def _masque_ligne(l, spans):
    for d, f in sorted(spans, reverse=True):   # de droite a gauche : les indices restent justes
        l = l[:d] + MASQUE + l[f:]
    return l


def _fusionne(spans):
    out = []
    for d, f in sorted(spans):
        if out and d <= out[-1][1]:
            out[-1][1] = max(out[-1][1], f)
        else:
            out.append([d, f])
    return out


# ---------- utilitaires ----------
def _chemin(p, cwd):
    p = os.path.expanduser(str(p).strip().strip('"\''))
    p = re.sub(r'^/([a-zA-Z])(?=/|$)', r'\1:', p)
    return os.path.normpath(os.path.join(cwd, p))


def _run(argv, cwd=None, timeout=10):
    """Sortie texte d'une commande ; None si le programme manque ; TimeoutExpired remonte (= refus)."""
    reste = FIN - time.monotonic()
    if reste <= 0:
        raise subprocess.TimeoutExpired(argv, 0)
    try:
        r = subprocess.run(argv, cwd=cwd, capture_output=True, stdin=subprocess.DEVNULL, timeout=min(timeout, reste))
    except OSError:
        return None
    return r.stdout.decode('utf-8', 'replace')


def _proteges_sous(base, limite=50000):
    """Fichiers proteges sous base : git ls-files (comme ripgrep, .gitignore respecte), sinon parcours borne."""
    if os.path.isfile(base):
        return [base] if est_protege(base) else []
    if not os.path.isdir(base):
        return []
    sortie = _run(['git', '-C', base, 'ls-files', '-co', '--exclude-standard', '-z'])
    noms = [n for n in (sortie or '').split('\0') if n]
    if noms:
        return [os.path.join(base, n) for n in noms if est_protege(os.path.join(base, n))]
    trouves, vus = [], 0
    for d, sous, fichiers in os.walk(base):   # hors depot ou dossier ignore (sauvegardes_cartes)
        sous[:] = [s for s in sous if s not in ('.git', 'node_modules', '.pio')]
        trouves += [os.path.join(d, f) for f in fichiers if est_protege(os.path.join(d, f))]
        vus += len(fichiers)
        if vus > limite:   # shortcut: arbre enorme parcouru en partie seulement ; un vrai index le couvrirait
            break
    return trouves


def _avec_secrets(fichiers):
    return [f for f in fichiers if os.path.isfile(f) and lignes_secretes(f)]


def _refus(quoi, detail=''):
    return f"garde_lecture : refuse, {quoi} afficherait une ligne secrete{detail}. {CONSEIL}"


# ---------- Read et Grep ----------
def garde_read(ti, cwd):
    p = _chemin(ti.get('file_path', ''), cwd)
    if not est_protege(p) or not os.path.isfile(p):
        return None
    sec = sorted(lignes_secretes(p))
    debut = max(int(ti.get('offset') or 1), 1)
    fin = debut + int(ti.get('limit') or 2000) - 1
    dans = [n for n in sec if debut <= n <= fin]
    if dans:
        return _refus(f"la lecture de {os.path.basename(p)} (lignes {debut}-{fin})",
                      f" (lignes secretes : {', '.join(map(str, dans))} ; lire une plage qui les evite, ou --lire)")
    return None


def _globs_ok(rel, globs):
    if not globs:
        return True
    pos, neg = [], []
    for g in str(globs).split():
        m = re.match(r'(.*)\{([^}]*)\}(.*)', g)
        for x in ([m.group(1) + a + m.group(3) for a in m.group(2).split(',')] if m else [g]):
            (neg if x.startswith('!') else pos).append(x.lstrip('!'))
    nom = rel.rsplit('/', 1)[-1]
    ok = lambda g: (fnmatch.fnmatchcase(rel, g) or fnmatch.fnmatchcase(rel, g[3:] if g.startswith('**/') else g)
                    or ('/' not in g and fnmatch.fnmatchcase(nom, g)))
    return not any(ok(g) for g in neg) and (not pos or any(ok(g) for g in pos))


TYPES = {'json': ('.json',), 'c': ('.c', '.h'), 'cpp': ('.cpp', '.cc', '.h', '.hpp'), 'h': ('.h',), 'py': ('.py',)}


def _lignes_trouvees(motif, texte, avant, apres):
    nl = [i for i, c in enumerate(texte) if c == '\n']
    out = set()
    for m in motif.finditer(texte):
        a = bisect.bisect_left(nl, m.start()) + 1
        b = bisect.bisect_left(nl, max(m.end() - 1, m.start())) + 1
        out.update(range(a - avant, b + apres + 1))
    return out


def garde_grep(ti, cwd):
    if ti.get('output_mode', 'files_with_matches') != 'content':
        return None
    base = _chemin(ti.get('path') or cwd, cwd)
    racine = base if os.path.isdir(base) else os.path.dirname(base)
    ext = TYPES.get(ti.get('type') or '')
    cibles = [f for f in _avec_secrets(_proteges_sous(base))
              if _globs_ok(os.path.relpath(f, racine).replace('\\', '/'), ti.get('glob'))
              and (not ext or f.lower().endswith(ext))]
    if not cibles:
        return None
    try:
        motif = re.compile(ti.get('pattern', ''), re.M | (re.I if ti.get('-i') else 0) | (re.S if ti.get('multiline') else 0))
    except re.error:
        return _refus("cette recherche (motif non analysable, fichiers a secrets dans la portee)")
    ctx = int(ti.get('-C') or ti.get('context') or 0)
    for f in cibles:
        touchees = _lignes_trouvees(motif, _lit(f), int(ti.get('-B') or ctx), int(ti.get('-A') or ctx))
        if touchees & lignes_secretes(f):
            return _refus(f"cette recherche dans {os.path.relpath(f, cwd)}")
    return None


# ---------- Bash et PowerShell ----------
def segments(cmd, ps=False):
    """[(texte, corps de heredoc)] : coupe sur ; && || | & et retour a la ligne, hors guillemets."""
    segs, cur, corps, i, q, docs = [], [], [], 0, None, []
    esc, n = ('`' if ps else '\\'), len(cmd)
    def coupe():
        segs.append((''.join(cur), '\n'.join(corps)))
        cur.clear(); corps.clear()
    while i < n:
        c = cmd[i]
        if q:
            cur.append(c)
            if c == esc and q == '"' and i + 1 < n:
                cur.append(cmd[i + 1]); i += 1
            elif c == q:
                q = None
            i += 1
            continue
        if c in '"\'':
            q = c
        elif c == esc and i + 1 < n:
            cur.append(c + cmd[i + 1]); i += 2
            continue
        m = re.match(r'<<(?!<)-?\s*([\'"]?)(\w+)\1', cmd[i:]) if c == '<' else None
        if m:
            docs.append((m.group(2), '-' in m.group(0)[:3])); cur.append(m.group(0)); i += len(m.group(0))
            continue
        if c == '\n' and docs:
            j = i + 1
            for delim, tab in docs:
                while j < n:
                    e = cmd.find('\n', j); e = n if e < 0 else e
                    ligne, j = cmd[j:e].rstrip('\r'), e + 1
                    if (ligne.strip() if tab else ligne) == delim:
                        break
                    corps.append(ligne)
            docs = []; coupe(); i = j
            continue
        sep = next((s for s in ('&&', '||', ';', '|', '\n', '&') if cmd.startswith(s, i)), None)
        if sep == '&' and ((cur and cur[-1] == '>') or cmd.startswith('&>', i)):
            sep = None   # 2>&1, &> : redirections, pas un arriere-plan
        if sep:
            coupe(); i += len(sep)
            continue
        cur.append(c); i += 1
    coupe()
    # $(...), <(...), `...` : le corps s'execute aussi, meme entre guillemets doubles
    for texte, _ in list(segs):
        for m in re.finditer(r'[$<>]\(', texte):
            prof, k = 0, m.end() - 1
            while k < len(texte):
                prof += {'(': 1, ')': -1}.get(texte[k], 0)
                if prof == 0:
                    break
                k += 1
            segs += segments(texte[m.end():k], ps)
        if not ps:
            for corps_bt in re.findall(r'`([^`]*)`', texte):
                segs += segments(corps_bt, ps)
    return [s for s in segs if s[0].strip() or s[1]]


def jetons(s):
    lex = shlex.shlex(s, posix=True)
    lex.whitespace_split, lex.escape, lex.commenters = True, '', ''
    try:
        return list(lex)
    except ValueError:
        return s.split()


def _sans_redir(tok):
    out, saute = [], False
    for t in tok:
        if saute:
            saute = False
        elif re.fullmatch(r'\d*(>>?|<)|&>>?', t):
            saute = True
        elif not re.match(r'\d*>>?|&>|<|\d*>&', t):
            out.append(t)
    return out


def _fichiers_proteges(tok, cwd):
    """Fichiers proteges AVEC ligne secrete nommes par les jetons (globs developpes)."""
    out = []
    for t in tok:
        t = t.split('=', 1)[-1].split(':', 1)[-1] if t.startswith('-') else t
        t = t.strip('"\'()`;<>|&{}')
        if not t or not est_protege(t.replace('*', 'x')):
            continue
        p = _chemin(t, cwd)
        out += glob.glob(p) if re.search(r'[*?\[]', t) else [p]
    return _avec_secrets([p for p in out if est_protege(p)])


AVEC_VALEUR = {'-A', '-B', '-C', '-m', '-e', '-f', '-g', '-t', '-T', '-j', '-M', '-d', '-D', '-O', '--max-depth', '--type',
               '--type-not', '--glob', '--iglob', '--include', '--exclude', '--exclude-dir', '--max-count', '--threads',
               '--context', '--after-context', '--before-context', '--regexp', '--file', '--color', '--colors', '--sort',
               '--sortr', '--encoding', '--max-columns', '--pre', '--path-separator'}
LISTE = {'-l', '-L', '-c', '-q', '--count', '--count-matches', '--name-only', '--files-with-matches',
         '--files-without-match', '--quiet', '--files'}


def _analyse(args):
    motifs, positifs, opts, ctx, i = [], [], set(), 0, 0
    while i < len(args):
        a = args[i]
        if a == '--':
            positifs += args[i + 1:]
            break
        if a.startswith('-') and len(a) > 1:
            bas, val = a.split('=', 1)[0], None
            if bas in AVEC_VALEUR:
                if '=' in a:
                    val = a.split('=', 1)[1]
                elif i + 1 < len(args):
                    i += 1; val = args[i]
            elif re.fullmatch(r'-[ABC]\d+|-\d+', a):
                bas, val = '-C', re.sub(r'\D', '', a)
            elif re.fullmatch(r'-[a-zA-Z]+', a):
                opts.update('-' + x for x in a[1:])
            opts.add(bas)
            if bas in ('-e', '--regexp') and val is not None:
                motifs.append(val)
            if bas in ('-A', '-B', '-C', '--context', '--after-context', '--before-context') and val:
                ctx = max([ctx] + [int(x) for x in re.findall(r'\d+', val)])
        else:
            positifs.append(a)
        i += 1
    if not motifs and positifs:
        motifs = [positifs.pop(0)]
    return motifs, positifs, opts, ctx


def _touche_secret(f, motifs, opts, ctx):
    """Vrai si une ligne trouvee (ou son contexte) est secrete. Motif non litteral ou douteux : vrai (prudence)."""
    sec = lignes_secretes(f)
    if not sec:
        return False
    if not motifs or opts & {'-f', '--file', '-v', '--invert-match', '--not', '--passthru', '--passthrough', '-P'}:
        return True
    if not ('-F' in opts or '--fixed-strings' in opts or not any(re.search(r'[.^$*+?()\[\]{}|\\]', m) for m in motifs)):
        return True   # traduire une regex BRE/PCRE en Python sous-matcherait : regle grossiere
    insens = opts & {'-i', '--ignore-case', '-S', '--smart-case'}
    norm = (lambda s: s.lower()) if insens else (lambda s: s)
    ms = [norm(m) for m in motifs]
    trouvees = [n for n, l in enumerate(_lit(f).split('\n'), 1) if any(m in norm(l) for m in ms)]
    if not trouvees:
        return True   # le fichier a ete liste mais le motif retenu n'y est pas : analyse ratee
    return any(abs(n - s) <= ctx for n in trouvees for s in sec)


def _recherche(prog, tok, i, cwd):
    """grep, rg, git grep : relance en mode liste, puis controle des lignes touchees dans les fichiers proteges."""
    args = _sans_redir(tok[i + 1:])
    motifs, positifs, opts, ctx = _analyse(args)
    if opts & LISTE:
        return None
    recursif = prog in ('git', 'rg') or opts & {'-r', '-R', '--recursive', '--dereference-recursive'}
    if not recursif:
        listes = _fichiers_proteges(positifs, cwd)   # sans fichier : lit l'entree standard, deja jugee
    else:
        argv = tok[:i + 1] + ['-l'] + args if prog == 'git' else [shutil.which(prog) or prog, '-l'] + args
        sortie = _run(argv, cwd=cwd)
        if sortie is None:   # programme introuvable : portee entiere, par prudence
            bases = [_chemin(p, cwd) for p in positifs if os.path.exists(_chemin(p, cwd))] or [cwd]
            if any(_avec_secrets(_proteges_sous(b)) for b in bases):
                return _refus(f"cette recherche ({prog} non relancable, fichiers a secrets dans la portee)")
            return None
        listes = []
        for nom in filter(None, (x.strip() for x in sortie.splitlines())):
            if re.match(r'[^/\\:]+:(?![\\/])', nom) and est_protege(nom.split(':', 1)[1]):
                return _refus(f"cette recherche dans une revision ({nom})")
            if est_protege(nom):
                listes += _avec_secrets([_chemin(nom, cwd)])
    for f in listes:
        if _touche_secret(f, motifs, opts, ctx):
            return _refus(f"cette recherche dans {os.path.relpath(f, cwd)}")
    return None


RESUMES = ('--stat', '--name-only', '--name-status', '--numstat', '--shortstat', '--summary', '--no-patch', '--raw',
           '--dirstat', '--compact-summary', '--quiet')
PATCH = ('-p', '-u', '--patch')


def _git(tok, cwd):
    i = 1
    while i < len(tok) and tok[i].startswith('-'):
        i += 2 if tok[i] in ('-C', '-c', '--git-dir', '--work-tree') else 1
    if i >= len(tok):
        return None
    sub, args = tok[i], _sans_redir(tok[i + 1:])
    if sub == 'grep':
        return _recherche('git', tok, i, cwd)
    if sub in ('show', 'cat-file', 'diff'):
        for a in args:   # REV:chemin ; un jeton qui commence par ':' est un pathspec magique (:!exclu)
            if not a.startswith((':', '-')) and ':' in a and est_protege(a.split(':', 1)[1]):
                return _refus(f"git {sub} {a}")
    if sub == 'blame' and _fichiers_proteges(args, cwd):
        return _refus("git blame")
    if sub not in ('diff', 'show', 'log', 'whatchanged', 'stash', 'format-patch'):
        return None
    if any(a == '-s' or a.startswith(RESUMES) for a in args):
        return None
    if sub in ('log', 'whatchanged') and not any(a in PATCH or a.startswith(('-L', '--patch')) for a in args):
        return None
    if sub == 'stash' and (not args or args[0] != 'show' or not any(a in PATCH for a in args)):
        return None
    if sub == 'format-patch' and '--stdout' not in args:
        return None
    garde = [a for a in args if a not in PATCH and not a.startswith('--output')]
    if sub == 'format-patch':
        argv = tok[:i] + ['log', '--name-only', '--format='] + [a for a in garde if not a.startswith('-')]
    elif sub == 'stash':
        argv = tok[:i] + ['stash', 'show', '--name-only'] + garde[1:]
    else:   # options inserees juste apres la sous-commande : jamais apres un --
        argv = tok[:i + 1] + ['--name-only', '--no-color'] + (['--format='] if sub != 'diff' else []) + garde
    sortie = _run(argv, cwd=cwd)
    if sortie is None:
        return _refus(f"git {sub} (relance impossible)")
    noms = sorted({x.strip() for x in sortie.splitlines() if est_protege(x.strip())})
    if noms:
        return _refus(f"git {sub}", f" (fichiers a secrets touches : {', '.join(noms[:5])} ; ajouter --stat, "
                                    f"ou exclure par -- . ':!**/*persist*.json' ':!tasmota/user_config_override.h')")
    return None


PYTHONS = {'python', 'python3', 'py', 'pythonw', 'node'}
VERBES = {'cat', 'type', 'head', 'tail', 'less', 'more', 'sed', 'awk', 'gawk', 'cut', 'sort', 'uniq', 'strings', 'xxd', 'od',
          'nl', 'tac', 'jq', 'get-content', 'gc', 'format-hex', 'diff', 'fc', 'compare-object', 'hexdump'}


def garde_segment(texte, corps, cwd, ps, tout):
    tok = jetons(texte)
    while tok and (re.match(r'^\$?[A-Za-z_]\w*=', tok[0]) or tok[0] in ('sudo', 'time', 'nohup', 'command', 'exec', 'env', '&', '.')):
        tok = tok[1:]
    if not tok:
        return None, cwd
    prog = re.sub(r'\.exe$', '', os.path.basename(tok[0].replace('\\', '/')).lower())
    if prog in ('cd', 'set-location', 'sl', 'pushd') and len(tok) > 1:
        return None, _chemin(tok[1], cwd)
    if prog in PYTHONS and any(t.replace('\\', '/').endswith('garde_lecture.py') for t in tok[1:3]):
        return None, cwd
    if prog in PYTHONS and (corps or set(tok) & {'-c', '-e', '-', '-p'}):
        code = texte + '\n' + corps + ('\n' + tout if '-' in tok else '')
        imprime = IMPRIME.search(code) or (prog == 'node' and '-p' in tok)
        if PROTEGE_RE.search(code) and imprime and 'masque(' not in code:
            return _refus("ce code Python ou Node",
                          " (sys.path.insert(0, '.claude/hooks'); from garde_lecture import masque ; imprimer masque(obj))"), cwd
    if prog in ('bash', 'sh', 'zsh', 'pwsh', 'powershell') :
        for k, t in enumerate(tok[:-1]):
            if t.lower() in ('-c', '-command'):
                return garde_commande(tok[k + 1], cwd, prog in ('pwsh', 'powershell')), cwd
    if prog == 'git':
        return _git(tok, cwd), cwd
    if prog in ('grep', 'egrep', 'fgrep', 'rg'):
        return _recherche(prog, tok, 0, cwd), cwd
    if prog in ('select-string', 'sls', 'findstr'):
        args = [t.lower() for t in tok[1:]]
        if '-quiet' in args or '/m' in args:
            return None, cwd
        recursif = '/s' in args or re.search(r'-recurse\b|\bgci\b.*-r\b', tout, re.I)
        if _fichiers_proteges(tok[1:], cwd) or (recursif and _avec_secrets(_proteges_sous(cwd))):
            return _refus(f"{tok[0]} (fichiers a secrets dans la portee)"), cwd
        return None, cwd
    if prog in VERBES and not (prog == 'sed' and any(t.startswith(('-i', '--in-place')) for t in tok)):
        f = _fichiers_proteges(tok[1:], cwd)
        if f:
            return _refus(f"{tok[0]} {os.path.basename(f[0])}", f" (lignes secretes : {sorted(lignes_secretes(f[0]))[:8]})"), cwd
    return None, cwd


def garde_commande(cmd, cwd, ps=False):
    if not cmd or not DECLENCHE.search(cmd):
        return None
    for texte, corps in segments(cmd, ps):
        msg, cwd = garde_segment(texte, corps, cwd, ps, cmd)
        if msg:
            return msg
    return None


def juge(d):
    outil, ti = d.get('tool_name', ''), d.get('tool_input') or {}
    cwd = _chemin(d.get('cwd') or os.getcwd(), os.getcwd())
    try:
        if outil == 'Read':
            return garde_read(ti, cwd)
        if outil == 'Grep':
            return garde_grep(ti, cwd)
        if outil in ('Bash', 'PowerShell'):
            return garde_commande(ti.get('command', ''), cwd, outil == 'PowerShell')
    except subprocess.TimeoutExpired:
        return _refus("cette commande (relance de controle trop longue)")
    return None


def hook():
    brut = sys.stdin.buffer.read().decode('utf-8', 'replace')
    try:
        msg = juge(json.loads(brut))
    except Exception as e:   # jamais bloquer tous les outils pour un bug, sauf si un fichier a secrets est en jeu
        if not PROTEGE_RE.search(brut):
            return 0
        msg = f"garde_lecture : erreur interne ({type(e).__name__}) sur un appel qui touche un fichier a secrets : refuse par prudence. {CONSEIL}"
    if msg:
        sys.stderr.write(msg + '\n')
        return REFUS
    return 0


# ---------- CLI ----------
def lire(chemin, lignes=None, cle=None):
    texte = _lit(chemin)
    if cle:
        obj, secret = json.loads(texte), False
        for k in cle.split('.'):
            secret = secret or bool(CLE_SECRETE.fullmatch(k))
            obj = obj[int(k)] if isinstance(obj, list) else obj[k]
        print(json.dumps(masque(obj, secret), indent=2, ensure_ascii=False))
        return 0
    spans = {}
    for n, d, f, _, _ in secrets_du_texte(texte):
        spans.setdefault(n, []).append((d, f))
    a, _, b = (lignes or '1-').partition('-')
    a, b = int(a or 1), int(b) if b else (int(a) if lignes and '-' not in lignes else 10 ** 9)
    for n, l in enumerate(texte.split('\n'), 1):
        if a <= n <= b:
            print(f"{n:6}\t{_masque_ligne(l.rstrip(chr(13)), _fusionne(spans.get(n, [])))}")
    return 0


def nature(cle):
    c = cle.lower()
    if 'wifi' in c or 'sta_pass' in c or 'reseau' in c:
        return 'mot de passe Wi-Fi'
    if 'token' in c or 'jeton' in c:
        return 'jeton'
    return 'cle secrete' if ('secret' in c or 'key' in c or 'cle' in c) else 'mot de passe'


def _git_cli(racine, *args):
    """Sortie de git pour la CLI ; git en echec = code 2 (jamais un faux « rien trouve »)."""
    r = subprocess.run(['git', '-C', racine, *args], capture_output=True)
    if r.returncode != 0:
        sys.stderr.write(f"garde_lecture : git {args[0]} en echec (code {r.returncode}) : "
                         f"{r.stderr.decode('utf-8', 'replace').strip()[:200]}\n")
        raise SystemExit(2)
    return r.stdout.decode('utf-8', 'replace')


def valeurs_depot(racine):
    """{valeur: [(source, cle)]} des fichiers proteges suivis par git et presents sur disque. Aucune = code 2."""
    noms = [n for n in _git_cli(racine, 'ls-files', '-z').split('\0') if n and est_protege(n)]
    vals = {}
    for n in noms:
        p = os.path.join(racine, n)
        if os.path.isfile(p):
            for _, _, _, cle, v in secrets_du_fichier(p):
                if v and len(v) >= 4 and set(v) != {'*'}:
                    vals.setdefault(v, []).append((n.replace('\\', '/'), cle))
    if not vals:
        sys.stderr.write("garde_lecture : aucune valeur secrete extraite des fichiers proteges suivis : controle impossible\n")
        raise SystemExit(2)
    return vals, {os.path.normcase(os.path.abspath(os.path.join(racine, n))) for n in noms}


def cherche_valeurs(chemins, diff=None, cached=False, racine='.'):
    vals, sources = valeurs_depot(racine)
    rx = re.compile('|'.join(re.escape(v) for v in sorted(vals, key=len, reverse=True)))
    trouves = []
    def examine(nom, n, ligne):
        for m in rx.finditer(ligne):
            src, cle = vals[m.group(0)][0]
            trouves.append(f"{nom}:{n} : {nature(cle)} (valeur de {src}::{cle}, {len(m.group(0))} caracteres)")
    if diff is not None or cached or not chemins:
        argv = ['diff', '--no-color', '--no-ext-diff', '-U0'] + (['--cached'] if cached else []) + ([diff] if diff else [])
        nom, n = '?', 0
        for l in _git_cli(racine, *argv).splitlines():
            if l.startswith('+++ '):
                nom = l[6:] if l.startswith('+++ b/') else l[4:]
            elif l.startswith('@@'):
                n = int(re.search(r'\+(\d+)', l).group(1))
            elif l.startswith('+'):
                if not est_protege(nom):
                    examine(nom, n, l[1:])
                n += 1
    for c in chemins:
        fichiers = [c] if os.path.isfile(c) else []
        for d, sous, fs in os.walk(c):
            sous[:] = [x for x in sous if x != '.git']
            fichiers += [os.path.join(d, f) for f in fs]
        for f in fichiers:
            if os.path.normcase(os.path.abspath(f)) in sources:
                continue
            try:
                with open(f, 'rb') as h:
                    brut = h.read()
            except OSError:
                continue
            if b'\0' in brut[:8192]:
                continue
            for n, l in enumerate(brut.decode('utf-8', 'replace').split('\n'), 1):
                examine(f.replace('\\', '/'), n, l)
    print('\n'.join(trouves) if trouves else f"aucune valeur secrete trouvee ({len(vals)} valeurs cherchees)")
    return 1 if trouves else 0


def public(rev, racine='.'):
    vals, _ = valeurs_depot(racine)
    lignes, erreur = [], False
    for v, refs in vals.items():
        fd, tmp = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'wb') as h:
                h.write(v.encode('utf-8'))   # sans saut de ligne : une ligne vide dans -f matcherait tout
            r = subprocess.run(['git', '-C', racine, 'grep', '-F', '-q', '-f', tmp, rev], capture_output=True)
        finally:
            os.unlink(tmp)
        etat = {0: 'deja publique', 1: 'NON publique'}.get(r.returncode, 'inconnu (erreur git)')
        erreur = erreur or r.returncode not in (0, 1)
        lignes += [f"{src}::{cle} ({len(v)} car.) : {etat}" for src, cle in refs]
    print('\n'.join(sorted(lignes)))
    return 2 if erreur else 0


def main(argv):
    if not argv:
        return hook()
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass
    global FIN
    FIN = float('inf')   # le budget de 25 s ne vaut que pour le hook
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--lire')
    ap.add_argument('--lignes')
    ap.add_argument('--cle')
    ap.add_argument('--cherche-valeurs', nargs='*')
    ap.add_argument('--diff', nargs='?', const='')
    ap.add_argument('--cached', action='store_true')
    ap.add_argument('--public')
    a = ap.parse_args(argv)
    if a.lire:
        return lire(a.lire, a.lignes, a.cle)
    racine = _git_cli('.', 'rev-parse', '--show-toplevel').strip()
    if a.cherche_valeurs is not None:
        return cherche_valeurs(a.cherche_valeurs, a.diff, a.cached, racine)
    if a.public:
        return public(a.public, racine)
    ap.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
