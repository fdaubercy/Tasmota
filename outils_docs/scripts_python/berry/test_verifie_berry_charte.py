r"""Banc du controle de la charte des logs (charte_logs.py, appele par verifie_berry.py) - audit P7.6.

  python outils_docs/scripts_python/berry/test_verifie_berry_charte.py

Code de sortie 0 = vert. Chaque regle a un TEMOIN (source qui doit avertir) et un cas CONFORME (qui doit
rester muet) : un controle qui ne dit jamais rien, ou qui dit tout, ne passe pas.
Partie 2 : verifie_berry.py en vrai (sous-processus) - avertissements imprimes, code de sortie inchange
(0 si le code compile), --sans-charte, erreur de syntaxe toujours en code 1.
Partie 3 : une passe sur tout data/ (nombre d'avertissements actuels, aucun n'est corrige ici).
Partie 4 : mutants sur le vrai code (les ecarts corriges par l'audit, remis en memoire) : signales ?
Partie 5 : le hook d'edition de Claude dans un faux depot (erreur -> 2, ecarts -> additionalContext, propre -> muet).
Fichiers de test dans un dossier temporaire ; rien n'est ecrit dans le depot.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import charte_logs  # noqa: E402

RACINE = ICI.parents[2]
VERIFIE = ICI / "verifie_berry.py"
echecs = []


def cas(nom, source, attendu, fichier="essai.be"):
    """attendu : liste de (ligne, regle) ; [] = aucun avertissement."""
    obtenu = sorted((l, r) for l, r, _ in charte_logs.controle(fichier, source))
    ok = obtenu == sorted(attendu)
    print(f"{'OK' if ok else 'KO'}  {nom}" + ("" if ok else f"\n      attendu {sorted(attendu)}\n      obtenu  {obtenu}"))
    if not ok:
        echecs.append(nom)


def verifie(nom, condition, detail=""):
    print(f"{'OK' if condition else 'KO'}  {nom}" + ("" if condition else f"\n      {detail}"))
    if not condition:
        echecs.append(nom)


print("== 1. Regles, une par une (temoin qui avertit / cas conforme muet) ==")
cas("log-direct : log() nu", 'def f()\n  log("MOD: a", 2)\nend\n', [(2, "log-direct")])
cas("log-direct : tasmota.log()", 'def f()\n  tasmota.log("MOD: a", 2)\nend\n', [(2, "log-direct")])
cas("log-direct : print dans un except", 'def f()\n  try\n    g()\n  except .. as e, m\n    print("Erreur", e)\n  end\nend\n',
    [(5, "log-direct")])
cas("conforme : print hors except (aide)", 'def f()\n  print("ReglageX help")\nend\n', [])
cas("conforme : log() de logFonctions_log", 'def logFonctions_log(msg, niveau)\n  log(msg, niveau)\nend\n', [])
cas("conforme : methode nommee log", 'class A\n  def log(m) end\nend\n', [])
cas("conforme : log dans un commentaire ou une chaine",
    '# log("x", 2)\n#- log("y") -#\ndef f()\n  logFonctions.log("MOD: appel de log(x)", LOG_LEVEL_INFO)\nend\n', [])

cas("conforme : repli log() quand logFonctions est absent",
    'def f(msg)\n  if (global.contains("logFonctions"))    global.logFonctions.log(msg, LOG_LEVEL_ERREUR)\n'
    '  else    log(msg, 1)\n  end\nend\n', [])
cas("log-direct : log() hors du repli", 'def f(msg)\n  if (global.contains("logFonctions"))  g()  end\n  log(msg, 1)\nend\n',
    [(3, "log-direct")])
cas("niveau : chiffre", 'def f()\n  logFonctions.log("MOD: a", 3)\nend\n', [(2, "niveau")])
cas("niveau : absent", 'def f()\n  logFonctions.log("MOD: a")\nend\n', [(2, "niveau")])
cas("conforme : constante", 'def f()\n  logFonctions.log("MOD: a", LOG_LEVEL_DEBUG)\nend\n', [])
cas("conforme : niveau en variable (enrobeur)", 'def x_log(msg, niveau)\n  logFonctions.log(msg, niveau, "x")\nend\n', [])
cas("conforme : chiffre admis dans demarrage.be", 'def f()\n  logFonctions.log("AUTO_EXE: a", 3)\nend\n', [],
    fichier="data/fs/demarrage.be")

cas("prefixe : absent", 'def f()\n  logFonctions.log("Bonjour", LOG_LEVEL_INFO)\nend\n', [(2, "prefixe")])
cas("prefixe : CamelCase", 'def f()\n  udpFonctions.log("ReglageUDP: a", LOG_LEVEL_INFO)\nend\n', [(2, "prefixe")])
cas("prefixe : dans string.format", 'def f()\n  import string\n  logFonctions.log(string.format("valeur %i", 3), LOG_LEVEL_INFO)\nend\n',
    [(3, "prefixe")])
cas("conforme : prefixe NOM_MAJ_SNAKE", 'def f()\n  import string\n  logFonctions.log(string.format("MON_MODULE: valeur %i !", 3), LOG_LEVEL_INFO)\nend\n', [])
cas("conforme : prefixe suivi d'une tabulation", 'def f()\n  logFonctions.log("AFFICHE_DISCOVERY:\\t * IP", LOG_LEVEL_INFO)\nend\n', [])
cas("prefixe : deux-points colles", 'def f()\n  logFonctions.log("MODULE:valeur", LOG_LEVEL_INFO)\nend\n', [(2, "prefixe")])
cas("conforme : f-string dans string.format",
    'def f(b, t)\n  logFonctions.log(string.format(f"LIRE_TCP: {t:s} %s", b), LOG_LEVEL_INFO)\nend\n', [])
cas("conforme : message en variable (non lu)", 'def f(msg)\n  logFonctions.log(msg, LOG_LEVEL_INFO)\nend\n', [])
cas("prefixe : appel sur plusieurs lignes", 'def f()\n  import string\n  logFonctions.log(string.format(\n    "sans prefixe %s",\n    "x"),\n    LOG_LEVEL_DEBUG)\nend\n',
    [(3, "prefixe")])

cas("erreur-prefixe : except sans _ERREUR", 'def f()\n  try\n    g()\n  except .. as e, m\n    logFonctions.log("MOD: echec", LOG_LEVEL_ERREUR)\n  end\nend\n',
    [(5, "erreur-prefixe")])
cas("conforme : except avec _ERREUR", 'def f()\n  try\n    g()\n  except .. as e, m\n    logFonctions.log("MOD_ERREUR: echec", LOG_LEVEL_ERREUR)\n  end\nend\n', [])
cas("conforme : erreur hors except", 'def f()\n  logFonctions.log("MOD: fichier absent !", LOG_LEVEL_ERREUR)\nend\n', [])
cas("conforme : except, niveau debug (politique a trancher, pas controlee)",
    'def f()\n  try\n    g()\n  except .. as e, m\n    logFonctions.log("MOD: ignore", LOG_LEVEL_DEBUG)\n  end\nend\n', [])
cas("erreur-prefixe : try imbrique, except du try exterieur",
    'def f()\n  try\n    try\n      g()\n    except .. as e, m\n    end\n    h()\n  except .. as e, m\n    if true\n      logFonctions.log("MOD: echec", LOG_LEVEL_ERREUR)\n    end\n  end\nend\n',
    [(10, "erreur-prefixe")])
cas("conforme : apres la fin du try", 'def f()\n  try\n    g()\n  except .. as e, m\n  end\n  logFonctions.log("MOD: suite", LOG_LEVEL_ERREUR)\nend\n', [])

cas("info-frequent : every_second", 'class A : Driver\n  def every_second()\n    logFonctions.log("MOD: tic", LOG_LEVEL_INFO)\n  end\nend\n',
    [(3, "info-frequent")])
cas("info-frequent : web_sensor, dans une fonction anonyme",
    'class A : Driver\n  def web_sensor()\n    var f = def ()\n      logFonctions.log("MOD: valeur", LOG_LEVEL_INFO)\n    end\n  end\nend\n',
    [(4, "info-frequent")])
cas("conforme : debug dans every_second", 'class A : Driver\n  def every_second()\n    logFonctions.log("MOD: tic", LOG_LEVEL_DEBUG)\n  end\nend\n', [])
cas("conforme : info dans init", 'class A : Driver\n  def init()\n    logFonctions.log("MOD: pret", LOG_LEVEL_INFO)\n  end\nend\n', [])

cas("non-garde : json.dump en detail", 'def f(x)\n  import json\n  logFonctions.log("MOD: " + json.dump(x), LOG_LEVEL_DEBUG_PLUS)\nend\n',
    [(3, "non-garde")])
cas("non-garde : tohex en debug", 'def f(b)\n  logFonctions.log("MOD: " + b.tohex(), LOG_LEVEL_DEBUG)\nend\n', [(2, "non-garde")])
cas("conforme : garde actif()", 'def f(x)\n  import json\n  if logFonctions.actif(LOG_LEVEL_DEBUG_PLUS, "mod")\n    logFonctions.log("MOD: " + json.dump(x), LOG_LEVEL_DEBUG_PLUS, "mod")\n  end\nend\n', [])
cas("conforme : garde par variable", 'def f(x)\n  import json\n  var detail = logFonctions.actif(LOG_LEVEL_DEBUG_PLUS, "mod")\n  if (detail)\n    logFonctions.log("MOD: " + json.dump(x), LOG_LEVEL_DEBUG_PLUS, "mod")\n  end\nend\n', [])
cas("conforme : garde en ternaire", 'def f(x)\n  import json\n  var detail = logFonctions.actif(LOG_LEVEL_DEBUG_PLUS, "mod")\n  logFonctions.log("MOD: " + (detail ? json.dump(x) : ""), LOG_LEVEL_DEBUG_PLUS, "mod")\nend\n', [])
cas("non-garde : branche else d'une garde", 'def f(x)\n  import json\n  if logFonctions.actif(LOG_LEVEL_DEBUG_PLUS, "mod")\n    g()\n  else\n    logFonctions.log("MOD: " + json.dump(x), LOG_LEVEL_DEBUG_PLUS)\n  end\nend\n',
    [(6, "non-garde")])
cas("non-garde : apres la fin de la garde", 'def f(x)\n  import json\n  if logFonctions.actif(LOG_LEVEL_DEBUG_PLUS, "mod")  g()  end\n  logFonctions.log("MOD: " + json.dump(x), LOG_LEVEL_DEBUG_PLUS)\nend\n',
    [(4, "non-garde")])
cas("conforme : json.dump en erreur (toujours emis)", 'def f(x)\n  import json\n  logFonctions.log("MOD: " + json.dump(x), LOG_LEVEL_ERREUR)\nend\n', [])

print("\n== 2. verifie_berry.py en vrai ==")
with tempfile.TemporaryDirectory() as dossier:
    d = Path(dossier)
    avertit = d / "avertit.be"
    avertit.write_text('def f()\n  logFonctions.log("sans prefixe", 3)\nend\n', encoding="utf-8")
    casse = d / "casse.be"
    casse.write_text('def f()\n  logFonctions.log("sans prefixe", 3)\n  if\nend\n', encoding="utf-8")
    propre = d / "propre.be"
    propre.write_text('def f()\n  logFonctions.log("MOD: ok !", LOG_LEVEL_INFO)\nend\n', encoding="utf-8")

    def lance(*args):
        r = subprocess.run([sys.executable, "-I", str(VERIFIE), *map(str, args)], cwd=str(RACINE),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        return r.returncode, r.stdout

    rc, out = lance(avertit)
    verifie("avertissements imprimes au format fichier:ligne: avertissement:",
            "avertit.be:2: avertissement: [niveau]" in out and "avertit.be:2: avertissement: [prefixe]" in out, out)
    verifie("code de sortie 0 malgre les avertissements", rc == 0, f"rc={rc}")
    verifie("bilan : nombre d'avertissements", "2 avertissement(s) de charte" in out, out)
    rc, out = lance("--sans-charte", avertit)
    verifie("--sans-charte : aucun avertissement", rc == 0 and "avertissement:" not in out, f"rc={rc} {out}")
    rc, out = lance(casse)
    verifie("erreur de syntaxe : code 1, ligne erreur:", rc == 1 and "casse.be:" in out and ": erreur:" in out, f"rc={rc} {out}")
    rc, out = lance(propre)
    verifie("fichier conforme : muet, code 0", rc == 0 and "avertissement:" not in out, f"rc={rc} {out}")

print("\n== 3. Passe sur tout data/ (constat, rien n'est corrige) ==")
r = subprocess.run([sys.executable, "-I", str(VERIFIE)], cwd=str(RACINE), capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=300)
lignes = [l for l in r.stdout.splitlines() if ": avertissement: [" in l]
par_regle = {}
for l in lignes:
    regle = l.split(": avertissement: [", 1)[1].split("]", 1)[0]
    par_regle[regle] = par_regle.get(regle, 0) + 1
print("    " + (r.stdout.strip().splitlines() or ["(aucune sortie)"])[-1])
print("    par regle : " + ", ".join(f"{k} {v}" for k, v in sorted(par_regle.items())))
verifie("passe complete : code 0 (data/ compile)", r.returncode == 0, f"rc={r.returncode}")

print("\n== 4. Mutants sur le vrai code : les ecarts corriges par P7.3/P7.5/P7.4, remis un par un ==")


def mutants(fichier, avant, apres, regle, a_la_ligne=True):
    """Remet l'ecart a chaque occurrence de 'avant' (une a la fois) : combien sont signales ?
    a_la_ligne : l'avertissement doit tomber sur la ligne mutee ; sinon, n'importe ou dans le fichier."""
    source = (RACINE / fichier).read_text(encoding="utf-8")
    base = {(l, r) for l, r, _ in charte_logs.controle(fichier, source)}
    vus, total, pos = 0, 0, source.find(avant)
    while pos != -1:
        total += 1
        ligne = source.count("\n", 0, pos) + 1
        mute = source[:pos] + apres + source[pos + len(avant):]
        nouveaux = {(l, r) for l, r, _ in charte_logs.controle(fichier, mute)} - base
        if (ligne, regle) in nouveaux if a_la_ligne else any(r == regle for _, r in nouveaux):
            vus += 1
        pos = source.find(avant, pos + 1)
    return vus, total

vus, total = mutants("data/fs/discoveryFonctions.be", "_ERREUR: ", ": ", "erreur-prefixe")
print(f"    discoveryFonctions : _ERREUR retire -> {vus} signale(s) sur {total} occurrence(s)")
verifie("mutants _ERREUR retire (audit C7) : au moins 6 signales (les except de discoveryFonctions)", vus >= 6, f"{vus}/{total}")
vus, total = mutants("data/fs/udpFonctions.be", "REGLAGE_UDP: ", "ReglageUDP: ", "prefixe")
verifie(f"mutants prefixe CamelCase (audit C8) : tous signales ({vus}/{total})", total > 0 and vus == total, f"{vus}/{total}")
# Garde P7.4 retiree : TOUTES les affectations "detail = logFonctions.actif(" d'un coup (la variable de garde
# est reconnue dans tout le fichier : en retirer une seule ne la fait pas disparaitre)
source = (RACINE / "data/fs/modbusFonctions.be").read_text(encoding="utf-8")
avant = sum(r == "non-garde" for _, r, _ in charte_logs.controle("modbusFonctions.be", source))
mute = source.replace("detail = logFonctions.actif(", "detail = logFonctions.inactif(")
apres = sum(r == "non-garde" for _, r, _ in charte_logs.controle("modbusFonctions.be", mute))
verifie(f"mutant garde actif() retiree (audit C4) : tohex des trames signales ({avant} -> {apres})",
        mute != source and apres >= avant + 2, f"{avant} -> {apres}")

print("\n== 5. Hook d'edition de Claude (.claude/hooks/verifie_berry_edition.py), dans un faux depot ==")
HOOK = RACINE / ".claude" / "hooks" / "verifie_berry_edition.py"
with tempfile.TemporaryDirectory() as dossier:
    faux = Path(dossier)
    for rel in ("outils_docs/scripts_python/berry/verifie_berry.py", "outils_docs/scripts_python/berry/charte_logs.py",
                "lib/libesp32/berry/berry.exe", "lib/libesp32/berry_custom/solidify_all_python.be"):
        (faux / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(RACINE / rel, faux / rel)
    (faux / ".git").mkdir()
    (faux / "data" / "fs").mkdir(parents=True)
    sources = {"casse": 'def f()\n  logFonctions.log("sans prefixe", 3)\n  if\nend\n',
               "avertit": 'def f()\n  logFonctions.log("sans prefixe", 3)\nend\n',
               "propre": 'def f()\n  logFonctions.log("MOD: ok !", LOG_LEVEL_INFO)\nend\n'}
    for nom, src in sources.items():
        (faux / "data" / "fs" / f"{nom}.be").write_text(src, encoding="utf-8")

    def hook(nom):
        entree = json.dumps({"tool_input": {"file_path": str(faux / "data" / "fs" / f"{nom}.be")}})
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(faux))
        r = subprocess.run([sys.executable, str(HOOK)], input=entree, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env, timeout=60)
        return r.returncode, r.stdout, r.stderr

    rc, out, err = hook("casse")
    verifie("hook : erreur de syntaxe -> code 2, erreur sur stderr", rc == 2 and ": erreur:" in err, f"rc={rc} {err}")
    rc, out, err = hook("avertit")
    contexte = json.loads(out).get("hookSpecificOutput", {}) if out.strip() else {}
    verifie("hook : ecarts seuls -> code 0, avertissements en additionalContext",
            rc == 0 and contexte.get("hookEventName") == "PostToolUse" and "[prefixe]" in contexte.get("additionalContext", ""),
            f"rc={rc} {out} {err}")
    rc, out, err = hook("propre")
    verifie("hook : fichier conforme -> code 0, muet", rc == 0 and not out.strip() and not err.strip(), f"rc={rc} {out} {err}")

print()
print("VERT" if not echecs else f"ROUGE : {len(echecs)} echec(s)")
sys.exit(1 if echecs else 0)
