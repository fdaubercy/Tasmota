r"""Genere outils_docs/CARTE_MODULES_BERRY.md : la carte des modules Berry par carte.

UTILISATION
-----------
  python outils_docs/scripts_python/berry/carte_modules_berry.py [--sortie CHEMIN] [--racine DEPOT]

  Ecrit outils_docs/CARTE_MODULES_BERRY.md (regenere a chaque lancement), rien d'autre.

CE QU'IL LIT (lecture seule)
----------------------------
  data/fs/*.be et data/<lieu>/<carte>/*.be (dossiers "*sauvegarde*" ignores), l'autoexec.be
  et le _persist.json de chaque carte, et custom_berry_solidify de chaque env PlatformIO
  (valeur RESOLUE par ProjectConfig, jamais le .ini parse a la main). ProjectConfig vit dans
  le Python de penv : la lecture est isolee dans un sous-processus. Aucun `pio run`.

CODES DES CELLULES
------------------
  S  solidifie dans l'env (custom_berry_solidify)      I  importe par l'autoexec
  D  charge indirectement : importe par un module lui-meme charge sur la carte
  C  compileModule / loadBerryFile dans l'autoexec     #  reference seulement en commentaire
  P  fichier propre a la carte (present dans son dossier)
  puis la GARDE d'activation evaluee sur le _persist.json : ON / OFF / ? (non evaluable).

COMMENT LA GARDE EST TROUVEE
----------------------------
  1. premier `if` lisant le persist dans les 12 lignes de `<nom>_init(` du module ;
  2. ET les conditions `if ...` de la ligne / du bloc de l'autoexec ; sans _init, l'argument
     d'activation de compileModule / loadBerryFile s'y ajoute.
  Formes comprises : racine["cle"], .find("cle", defaut), == "ON", != false, && / ||.
  Tout le reste donne "?".
"""
import argparse, json, os, re, subprocess, sys

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RACINES_PERSIST = ("serveur", "diverses", "modules", "drivers")
INTERNES = {"partition_wizard", "leds_panel", "autoexec"}   # modules internes Tasmota
FAMILLES = ["Socle", "Reseau", "ModBus", "Peripheriques", "Carte", "Autres"]

# Lecture de la config PlatformIO, executee par le Python de penv (qui seul a `platformio`).
LECTEUR_PIO = r"""
import json, sys
from platformio.project.config import ProjectConfig
c = ProjectConfig("platformio.ini")
sortie = {}
for s in c.sections():
    if s.startswith("env:"):
        v = c.get(s, "custom_berry_solidify", None)
        if isinstance(v, str):
            v = v.splitlines()
        sortie[s[4:]] = v
print(json.dumps(sortie))
"""

# --- Config PlatformIO ---
def envs_platformio(racine):
    """{env: liste de fichiers custom_berry_solidify ou None}, via ProjectConfig (penv)."""
    candidats = [os.path.join(os.path.expanduser("~"), ".platformio", "penv", "Scripts", "python.exe"),
                 os.path.join(os.path.expanduser("~"), ".platformio", "penv", "bin", "python")]
    python_pio = next((p for p in candidats if os.path.isfile(p)), sys.executable)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([python_pio, "-c", LECTEUR_PIO], cwd=racine, capture_output=True,
                       text=True, encoding="utf-8", env=env)
    if r.returncode != 0:
        sys.exit("Lecture de la config PlatformIO impossible (%s) :\n%s" % (python_pio, r.stderr))
    return json.loads(r.stdout.strip().splitlines()[-1])

def dossier_de_env(nom):
    """Regle de transform_name() (outils_docs/scripts_python/build/pre_utilitaires_platformio.py,
    ~l.256) : 'tasmota32s3-cave-serveur-rly' -> 'data/cave/tasmota32s3-serveur-rly'.
    Reproduite ici : ce fichier est un script de build SCons, on ne l'importe pas."""
    parts = nom.split("-")
    if len(parts) < 2:
        return None
    reste = parts[2:]
    return "data/%s/%s" % (parts[1], "-".join([parts[0]] + reste) if reste else parts[0])

# --- Evaluation des gardes (logique a 3 valeurs : True / False / None = inconnu) ---
def et3(a, b):
    if a is False or b is False:
        return False
    return None if (a is None or b is None) else True

def ou3(a, b):
    if a is True or b is True:
        return True
    return None if (a is None or b is None) else False

_INCONNU = object()

def _parenthese_fermante(s, i):
    """Index de la parenthese fermante correspondant a celle ouverte juste avant i."""
    prof, quote = 1, None
    while i < len(s):
        c = s[i]
        if quote:
            quote = None if c == quote else quote
        elif c in "\"'":
            quote = c
        elif c in "([{":
            prof += 1
        elif c in ")]}":
            prof -= 1
            if prof == 0:
                return i
        i += 1
    return -1

def _decoupe_niveau0(s, sep):
    """Coupe s sur sep, hors parentheses / crochets / accolades / chaines."""
    morceaux, prof, quote, debut, i = [], 0, None, 0, 0
    while i < len(s):
        c = s[i]
        if quote:
            quote = None if c == quote else quote
        elif c in "\"'":
            quote = c
        elif c in "([{":
            prof += 1
        elif c in ")]}":
            prof -= 1
        elif prof == 0 and s.startswith(sep, i):
            morceaux.append(s[debut:i])
            i += len(sep)
            debut = i
            continue
        i += 1
    morceaux.append(s[debut:])
    return morceaux

def _valeur_litterale(txt):
    txt = txt.strip()
    if txt in ("false", "true"):
        return txt == "true"
    if txt == "nil":
        return None
    try:
        return json.loads(txt)        # "chaine", nombre, {}, [], {"a": "OFF"}
    except ValueError:
        return _INCONNU

def valeur_chaine(expr, persist):
    """Evalue racine["cle"] / .find("cle", defaut) repetes. _INCONNU si hors du dialecte."""
    expr = expr.strip()
    m = re.match(r"(%s)\b" % "|".join(RACINES_PERSIST), expr)
    if not m or not isinstance(persist, dict):
        return _INCONNU
    cur, i = persist.get(m.group(1), _INCONNU), m.end()
    while i < len(expr):
        if cur is _INCONNU or not isinstance(cur, dict):
            return _INCONNU
        m1 = re.compile(r'\s*\[\s*"([^"]+)"\s*\]').match(expr, i)
        m2 = re.compile(r'\s*\.\s*find\s*\(\s*"([^"]+)"\s*,').match(expr, i)
        if m1:
            cur, i = cur.get(m1.group(1), _INCONNU), m1.end()   # absent : Berry planterait
        elif m2:
            fin = _parenthese_fermante(expr, m2.end())
            if fin < 0:
                return _INCONNU
            defaut = _valeur_litterale(expr[m2.end():fin])
            cur, i = cur.get(m2.group(1), defaut), fin + 1
        else:
            return _INCONNU
    return cur

def evalue_condition(cond, persist):
    """True / False / None (non evaluable) pour une condition de garde."""
    cond = cond.strip()
    while cond.startswith("(") and _parenthese_fermante(cond, 1) == len(cond) - 1:
        cond = cond[1:-1].strip()
    ou = _decoupe_niveau0(cond, "||")
    if len(ou) > 1:
        res = False
        for p in ou:
            res = ou3(res, evalue_condition(p, persist))
        return res
    et = _decoupe_niveau0(cond, "&&")
    if len(et) > 1:
        res = True
        for p in et:
            res = et3(res, evalue_condition(p, persist))
        return res
    m = re.match(r'^(.+?)\s*(==|!=)\s*("[^"]*"|false|true|\d+)$', cond, re.S)
    if m:
        v, attendu = valeur_chaine(m.group(1), persist), _valeur_litterale(m.group(3))
        if v is _INCONNU:
            return None
        return (v == attendu) if m.group(2) == "==" else (v != attendu)
    ml = re.match(r'^"([^"]*)"$', cond)         # litterale seule (argument de compileModule)
    if ml:
        return ml.group(1) == "ON"
    v = valeur_chaine(cond, persist)          # chaine seule (argument de compileModule)
    return None if v is _INCONNU else (v == "ON")

def lit_persist(cond):
    return re.search(r"\b(%s)\s*[\[.]" % "|".join(RACINES_PERSIST), cond) is not None

def garde_init(chemin_be, nom):
    """Condition du premier `if` lisant le persist dans <nom>_init(), ou None."""
    try:
        lignes = open(chemin_be, encoding="utf-8-sig", errors="replace").read().splitlines()
    except OSError:
        return None
    for i, l in enumerate(lignes):
        if re.match(r"\s*def\s+%s_init\s*\(" % re.escape(nom), l):
            for suite in lignes[i + 1:i + 13]:
                m = re.match(r"\s*if\s+(.*)$", suite)
                if m and lit_persist(m.group(1)):
                    return re.sub(r"\s+#.*$", "", m.group(1)).strip()
            return None
    return None

# --- Analyse d'un autoexec.be ---
RE_IMPORT = re.compile(r"^(?:do\s+)?(?:if\s+(?P<cond>.+?)\s+)?import\s+(?P<mod>\w+)(?:\s+as\s+\w+)?\s*(?:end\s*)?(?:#.*)?$")
RE_CHARGE = re.compile(r"^(?:do\s+)?(?:if\s+(?P<cond>.+?)\s+)?gestionFileFolder\.(?P<fn>compileModule|loadBerryFile)\(\s*\"/(?P<mod>\w+)\"\s*(?P<reste>.*)$")

# Autoexec au format du module commun data/fs/demarrage.be (audit P4.2, 2026-10-25) : une ligne
# demarrage.<fn>([noms], "bloc.sous_bloc") equivaut aux compileModule / import / loadBerryFile d'avant.
RE_DEMARRAGE = re.compile(r'^demarrage\.(?P<fn>importe|compileSocle|compile|charge|chargeFichier|leds|historique)\((?P<args>.*)\)\s*(?:#.*)?$')
SOCLE_DEMARRAGE = ["configGlobal", "configDevices", "configModules", "gestionFileFolder", "globalFonctions", "diversFonctions", "logFonctions"]
COND_LEDS = ('drivers.find("leds", {}).find("activation", "OFF") == "ON" && (drivers.find("leds", {}).find("environnement", {}).find("leds", {}).find("ledRGB", {}).find("activation", "OFF") == "ON"'
             ' || drivers.find("leds", {}).find("environnement", {}).find("leds", {}).find("ruban", {}).find("activation", "OFF") == "ON")')

RE_CHARGE_MODULE = re.compile(r'^(?P<si>if\s+.+?\s+)?chargeModule\("\w+",\s*def\s*\(\)\s*(?P<corps>.+?)\s+end\)\s*(?P<fin>end)?\s*(?:#.*)?$')

def _activation_demarrage(chemin):
    """"serveur.udp" -> 'serveur.find("udp", {}).find("activation", "OFF")', comme demarrage.activation()."""
    parties = chemin.split(".")
    return parties[0] + "".join('.find("%s", {})' % p for p in parties[1:]) + '.find("activation", "OFF")'

def refs_demarrage(l, commente, pile):
    """References d'une ligne demarrage.<fn>(...), ou None si la ligne n'en est pas une."""
    m = RE_DEMARRAGE.match(l)
    if not m:
        return None
    noms = re.findall(r'"(\w+)"', m["args"].split("]")[0]) if "[" in m["args"] else []
    chemins = re.findall(r'"([\w.]+)"', m["args"].split("]")[-1]) if "[" in m["args"] else re.findall(r'"([\w.]+)"', m["args"])
    act = _activation_demarrage(chemins[-1]) if chemins and m["fn"] != "chargeFichier" else None
    ref = lambda mod, type, arg=None, conds=(): dict(mod=mod, type=type, commente=commente, arg=arg, conds=[c for c in pile + list(conds) if c])
    fn = m["fn"]
    if fn == "importe":
        return [ref(n, "I") for n in noms]
    if fn == "compileSocle":
        return [ref(n, "C", '"ON"') for n in SOCLE_DEMARRAGE] + [ref("webFonctions", "C", 'serveur.find("activation", "OFF")')]
    if fn == "compile":
        return [ref(n, "C", act or '"ON"') for n in noms]
    if fn == "charge":
        return [ref(n, "I", conds=[act + ' == "ON"'] if act else []) for n in noms]
    if fn == "chargeFichier":
        nom = re.findall(r'"(\w+)"', m["args"])[0]
        return [ref(nom, "C", _activation_demarrage(chemins[1]) if len(chemins) > 1 else '"ON"')]
    if fn == "leds":
        return [ref("ledsFonctions", "C", '"ON"', [COND_LEDS]), ref("controleLeds", "C", '"ON"', [COND_LEDS]), ref("controleLeds", "I", conds=[COND_LEDS])]
    cond = 'diverses.find("historique", {}).find("activation", "OFF") == "ON"'
    return [ref("historiqueFonctions", "C", '"ON"', [cond]), ref("historiqueFonctions", "I", conds=[cond])]

def analyse_autoexec(texte):
    """Liste de references {mod, type I/C, commente, conds [conditions englobantes+ligne], arg}."""
    refs, pile = [], []
    for brut in texte.splitlines():
        l = brut.strip()
        commente = l.startswith("#")
        if commente:
            l = l.lstrip("#").strip()
        # chargeModule("x", def () <corps> end) (P10.2, cartes gelees) : seul le corps compte
        mc = RE_CHARGE_MODULE.match(l)
        if mc:
            l = (mc["si"] or "") + mc["corps"] + (" end" if mc["fin"] else "")
        if not commente and "demarrage.prologue()" in l:      # prologue : log, divers, fichiers
            refs.extend(dict(mod=n, type="I", commente=False, arg=None, conds=[c for c in pile if c])
                        for n in ("logFonctions", "diversFonctions", "gestionFileFolder"))
        r = refs_demarrage(l, commente, pile)
        if r is not None:
            refs.extend(r)
            continue
        m = RE_IMPORT.match(l)
        if m:
            refs.append(dict(mod=m["mod"], type="I", commente=commente, arg=None,
                             conds=[c for c in pile + [m["cond"]] if c]))
            continue
        m = RE_CHARGE.match(l)
        if m:
            reste = m["reste"]
            fin = _parenthese_fermante(reste, 0)        # ")" qui ferme l'appel
            args = _decoupe_niveau0(reste[:fin] if fin >= 0 else reste, ",")
            arg = args[1].strip() if len(args) > 1 and args[1].strip() else None   # args[0] = vide (avant la 1re virgule)
            refs.append(dict(mod=m["mod"], type="C", commente=commente, arg=arg,
                             conds=[c for c in pile + [m["cond"]] if c]))
            continue
        if commente:
            continue
        # blocs if/do multi-lignes : on empile la condition du `if` (ou None)
        if re.match(r"^(if\b|do$)", l) and not re.search(r"\bend\s*(#.*)?$", l):
            mi = re.match(r"^if\s+(.*)$", l)
            pile.append(mi.group(1) if mi else None)
        elif re.match(r"^end\b", l) and pile:
            pile.pop()
        elif re.match(r"^else\b", l) and pile:
            pile[-1] = None
    return refs

def etat_ref(ref, persist, garde=None):
    """(etat, bloque) d'une reference active. Parties : garde _init (si elle existe) ET conditions
    de ligne/bloc ; sans garde _init, l'argument d'activation s'y ajoute. bloque = une condition
    de LIGNE vaut OFF (l'import / le chargement n'est alors jamais execute)."""
    conds = [c for c in ref["conds"] if lit_persist(c)]
    bloque = any(evalue_condition(c, persist) is False for c in conds)
    parties = ([garde] if garde else []) + conds
    if not garde and ref["arg"] and (lit_persist(ref["arg"]) or ref["arg"] in ('"ON"', '"OFF"')):
        parties.append(ref["arg"])
    if not parties:
        return "", False
    res = True
    for p in parties:
        res = et3(res, evalue_condition(p, persist))
    return {True: "ON", False: "OFF", None: "?"}[res], bloque

# --- Collecte ---
def stems_be(dossier):
    if not os.path.isdir(dossier):
        return []
    return sorted(f[:-3] for f in os.listdir(dossier) if f.endswith(".be") and f != "autoexec.be")

def collecte(racine):
    fs = {n: os.path.join(racine, "data", "fs", n + ".be") for n in stems_be(os.path.join(racine, "data", "fs"))}
    envs = envs_platformio(racine)
    cartes, anomalies = [], []
    dossiers = {}
    for lieu in sorted(os.listdir(os.path.join(racine, "data"))):
        base = os.path.join(racine, "data", lieu)
        if lieu == "fs" or not os.path.isdir(base):
            continue
        for carte in sorted(os.listdir(base)):
            d = os.path.join(base, carte)
            if "sauvegarde" not in carte.lower() and (os.path.isfile(os.path.join(d, "autoexec.be")) or os.path.isfile(os.path.join(d, "_persist.json"))):
                dossiers["data/%s/%s" % (lieu, carte)] = None
    for env, liste in envs.items():
        rel = dossier_de_env(env)
        if "-base" in env or rel is None:
            continue
        if rel in dossiers:
            dossiers[rel] = env
            cartes.append((rel, env, liste or []))
        elif liste:
            anomalies.append("L'env `%s` definit `custom_berry_solidify` mais son dossier `%s` n'existe pas." % (env, rel))
    for rel, env in dossiers.items():
        if env is None:
            anomalies.append("Le dossier `%s` ne correspond a aucun env PlatformIO." % rel)
    cartes.sort()
    return fs, cartes, anomalies

def analyse_carte(racine, rel, env, solidifies):
    dossier = os.path.join(racine, rel)
    persist = None
    chemin_p = os.path.join(dossier, "_persist.json")
    if os.path.isfile(chemin_p):
        try:
            persist = json.load(open(chemin_p, encoding="utf-8-sig"))
        except ValueError:
            persist = None
    chemin_a = os.path.join(dossier, "autoexec.be")
    refs = analyse_autoexec(open(chemin_a, encoding="utf-8-sig", errors="replace").read()) if os.path.isfile(chemin_a) else []
    sol = {os.path.splitext(os.path.basename(l.strip()))[0] for l in solidifies
           if l.strip() and not l.strip().startswith("#")}
    return dict(rel=rel, env=env, persist=persist, refs=refs, sol=sol, propres=stems_be(dossier),
                dossier=dossier, a_autoexec=os.path.isfile(chemin_a))

def famille(nom, propre):
    if propre:
        return "Carte"
    b = nom
    if b in ("controleLedTemoin", "controleWeb", "webFonctions", "controleGeneral", "gestionFileFolder"):
        return "Socle"
    b = re.sub(r"^controle", "", b)
    b = re.sub(r"Fonctions$", "", b).lower()
    if re.match(r"(config|global|divers|log)", b):
        return "Socle"
    if re.match(r"(udp|tcp|discovery|rangeextender)", b):
        return "Reseau"
    if re.match(r"modbus", b):
        return "ModBus"
    if re.match(r"(i2c_|es8311|led|vr|voletroulants|lorawan)", b):
        return "Peripheriques"
    return "Autres"

def cellule(nom, carte, fs, propre_carte):
    """(texte, etat, actif, tout_bloque) de la cellule module x carte."""
    codes, actives = [], [r for r in carte["refs"] if r["mod"] == nom and not r["commente"]]
    comm = [r for r in carte["refs"] if r["mod"] == nom and r["commente"]]
    for code, ok in (("S", nom in carte["sol"]), ("P", propre_carte),
                     ("I", any(r["type"] == "I" for r in actives)), ("C", any(r["type"] == "C" for r in actives)),
                     ("#", comm and not actives)):
        if ok:
            codes.append(code)
    etat, bloque = "", False
    if actives:
        chemin = fs.get(nom) or os.path.join(carte["dossier"], nom + ".be")
        garde = garde_init(chemin, nom)
        res = [etat_ref(r, carte["persist"], garde) for r in actives]
        etats = [e for e, _ in res if e]
        etat = "" if not etats else ("ON" if "ON" in etats else ("?" if "?" in etats else "OFF"))
        bloque = all(b for _, b in res)
    return (" ".join(codes + ([etat] if etat else [])), etat, bool(actives), bloque)

# --- Rendu Markdown ---
def court(rel):
    p = rel.split("/")
    return "%s<br>%s" % (p[1], p[2])

def dependances(fichiers):
    """{module: {modules Berry connus qu'il importe ou charge}}, commentaires ignores
    (un import dans une fonction compte : il s'execute quand la fonction tourne)."""
    deps = {}
    for nom, chemin in fichiers.items():
        brut = open(chemin, encoding="utf-8-sig", errors="replace").read().splitlines()
        code = chr(10).join(l.split("#")[0] for l in brut)
        trouves = re.findall(r"\bimport\s+(\w+)", code) + [m[1] for m in re.findall(r'(compileModule|loadBerryFile)\(\s*"/(\w+)"', code)]
        # demarrage.be cite les modules que l'autoexec lui demande de charger : ses vraies
        # dependances sont les references de l'autoexec (refs_demarrage), pas son propre code
        deps[nom] = set() if nom == "demarrage" else {t for t in trouves if t in fichiers and t != nom}
    return deps

def fermeture(graines, deps):
    vus, pile = set(graines), list(graines)
    while pile:
        for d in deps.get(pile.pop(), ()):
            if d not in vus:
                vus.add(d)
                pile.append(d)
    return vus

def mermaid_carte(carte, modules, fs):
    """Un flowchart LR : la carte -> ses modules actifs, groupes par famille."""
    ident = lambda s: "m_" + re.sub(r"\W", "_", s)
    lignes = ["```mermaid", "flowchart LR", '    CARTE(["%s"])' % carte["rel"].replace("data/", "")]
    par_fam, aretes = {f: [] for f in FAMILLES}, []
    for nom, propre in modules:
        txt, etat, actif, _ = carte["cellules"][nom]
        if not actif:
            continue
        par_fam[famille(nom, propre)].append(nom)
        if "D" not in txt.split():
            aretes.append("    CARTE %s %s" % ("-->" if etat in ("ON", "") else "-.->", ident(nom)))
        else:   # dependance : fleche depuis chaque module charge qui l'importe
            aretes += ["    %s -.->|import| %s" % (ident(a), ident(nom)) for a in sorted(carte["ferm"])
                       if nom in carte["deps"].get(a, ()) and carte["cellules"][a][2]]
    for f, noms in par_fam.items():
        if noms:
            lignes.append('    subgraph g_%s["%s"]' % (f, f))
            lignes += ['        %s["%s"]' % (ident(n), n) for n in noms]
            lignes.append("    end")
    lignes += aretes + ["```"]
    return lignes

def genere(racine, sortie):
    fs, cartes_brutes, anomalies = collecte(racine)
    cartes = [analyse_carte(racine, rel, env, sol) for rel, env, sol in cartes_brutes]
    propres_tous = sorted({n for c in cartes for n in c["propres"]} - set(fs))
    modules = [(n, False) for n in fs] + [(n, True) for n in propres_tous]
    modules.sort(key=lambda x: (FAMILLES.index(famille(*x)), x[0].lower()))
    for c in cartes:
        c["cellules"] = {n: cellule(n, c, fs, p and n in c["propres"]) for n, p in modules}
        fichiers = {n: fs.get(n) or os.path.join(c["dossier"], n + ".be") for n, _ in modules if n in fs or n in c["propres"]}
        c["deps"] = dependances(fichiers)
        c["ferm"] = fermeture([n for n, v in c["cellules"].items() if v[2] and not v[3]], c["deps"])
        for n in sorted(c["ferm"]):   # charge indirectement (D) : importe par un module charge
            t, e, a, b = c["cellules"][n]
            if not a or b:
                k = [x for x in t.split() if x in ("S", "P")]
                c["cellules"][n] = (" ".join(k + ["D"] + [x for x in t.split() if x not in ("S", "P", "#")]), e, True, False)
    inco, infos = list(anomalies), []
    for c in cartes:
        nom = c["rel"].replace("data/", "")
        if not c["a_autoexec"]:
            inco.append("`%s` : pas d'autoexec.be." % nom)
        if c["persist"] is None:
            inco.append("`%s` : `_persist.json` absent ou illisible, gardes non evaluables." % nom)
        for n in sorted(c["sol"]):
            # un module solidifie vit dans data/fs OU dans le dossier de la carte (controleRideau, audit S7)
            if n not in fs and n not in c["propres"]:
                inco.append("`%s` : `%s` est dans custom_berry_solidify mais ni `data/fs/%s.be` ni le dossier de la carte ne le contiennent." % (nom, n, n))
        for n, p in modules:
            txt, etat, actif, bloque = c["cellules"][n]
            codes = txt.split()
            if "S" in codes and not actif:
                if "#" in codes:
                    inco.append("`%s` : `%s` solidifie, reference seulement en commentaire dans l'autoexec." % (nom, n))
                else:
                    inco.append("`%s` : `%s` solidifie, jamais importe ni charge par l'autoexec." % (nom, n))
            if actif and "S" not in codes and "D" not in codes and not (p and n in c["propres"]):
                infos.append("`%s` : `%s` charge depuis `data/fs` sans etre solidifie (copie sur le FS, compile au demarrage)." % (nom, n))
            if p and n in c["propres"] and not actif:
                inco.append("`%s` : `%s.be` est dans le dossier de la carte mais l'autoexec ne le charge pas%s." % (nom, n, " (en commentaire)" if "#" in codes else ""))
            if actif and etat == "OFF":
                infos.append("`%s` : `%s` : %s." % (nom, n, "import / chargement conditionne par l'autoexec, condition evaluee OFF (non execute)" if bloque else "charge alors que sa garde vaut OFF"))
            if n in fs and n in c["propres"]:
                inco.append("`%s` : `%s.be` existe aussi dans `data/fs` (homonyme)." % (nom, n))
        for r in c["refs"]:
            if r["type"] == "C" and not r["commente"] and r["mod"] not in fs and r["mod"] not in c["propres"] and r["mod"] not in INTERNES:
                inco.append("`%s` : l'autoexec charge `/%s` mais aucun fichier de ce nom (ni data/fs ni dossier de carte)." % (nom, r["mod"]))
    for n in fs:
        etats = [c["cellules"][n][0].split() for c in cartes]
        if not any(("S" in e or any(x in e for x in ("I", "C"))) for e in etats):
            seul_comm = any("#" in e for e in etats)
            inco.append("`data/fs/%s.be` : %s." % (n, "reference seulement en commentaire, par aucune carte autrement" if seul_comm else "reference par aucune carte"))
    for chemin in [fs[n] for n in fs] + [os.path.join(c["dossier"], n + ".be") for c in cartes for n in c["propres"]]:
        if not open(chemin, encoding="utf-8-sig", errors="replace").read().strip():
            inco.append("`%s` : fichier vide." % os.path.relpath(chemin, racine).replace(os.sep, "/"))
    L = ["# Carte des modules Berry par carte", "",
         "> Fichier GENERE par carte_modules_berry.py - ne pas editer a la main.",
         "> Sortie deterministe (ni date, ni ordre de hachage) : regeneree sans changement de fond, elle ne",
         "> donne aucun diff. La date de generation est celle du commit.", "",
         "%d modules (%d dans `data/fs`, %d propres a une carte), %d cartes." % (len(modules), len(fs), len(propres_tous), len(cartes)),
         "", "## Tableau", "",
         "Legende : **S** solidifie dans l'env (`custom_berry_solidify`) - **I** importe par l'autoexec - "
         "**C** `compileModule` / `loadBerryFile` - **D** charge indirectement (importe par un module charge sur la carte) - **#** reference seulement commentee - **P** fichier propre a la carte "
         "- puis la garde d'activation evaluee sur le `_persist.json` de la carte : **ON** / **OFF** / **?** (non evaluable). "
         "Pas d'etat = pas de garde. Cellule vide = rien.", "",
         "| Module | Famille | " + " | ".join(court(c["rel"]) for c in cartes) + " |",
         "|---|---|" + "---|" * len(cartes)]
    for n, p in modules:
        L.append("| `%s` | %s | " % (n, famille(n, p)) + " | ".join(c["cellules"][n][0] for c in cartes) + " |")
    L += ["", "Envs : " + " ; ".join("`%s` = `%s`" % (c["rel"].replace("data/", ""), c["env"]) for c in cartes), "",
          "## Incoherences detectees", "",
          "Constats factuels, sans jugement : un module peut etre volontairement dans cet etat.", ""]
    L += ["- " + i for i in inco] or ["- (aucune)"]
    L += ["", "### Informations (normal ou voulu, listees pour memoire)", ""]
    L += ["- " + i for i in infos] or ["- (aucune)"]
    L += ["", "## Diagrammes", "",
          "Un diagramme par carte (tout dans un seul serait illisible). Modules **charges** par l'autoexec "
          "(import / compileModule / loadBerryFile non commentes). Fleche pleine = garde ON ou sans garde ; "
          "pointillee = garde OFF ou non evaluable (?).", ""]
    for c in cartes:
        L += ["### %s" % c["rel"].replace("data/", ""), ""] + mermaid_carte(c, modules, fs) + [""]
    L += ["## Comment regenerer", "", "```", "python outils_docs/scripts_python/berry/carte_modules_berry.py", "```", "",
          "Lecture seule : aucun build, aucune ecriture sous `data/`. La config PlatformIO est lue par l'API "
          "`ProjectConfig` dans le Python de PlatformIO (`~/.platformio/penv`).", ""]
    with open(sortie, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))
    return len(modules), len(cartes), inco, infos

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--racine", default=RACINE)
    ap.add_argument("--sortie", default=None)
    a = ap.parse_args()
    sortie = a.sortie or os.path.join(a.racine, "outils_docs", "CARTE_MODULES_BERRY.md")
    nm, nc, inco, infos = genere(a.racine, sortie)
    print("%s ecrit : %d modules, %d cartes, %d incoherences, %d informations." % (sortie, nm, nc, len(inco), len(infos)))

if __name__ == "__main__":
    main()
