"""Banc de build_reparations_ia (plan build-reparations A6) : `claude` est remplacé par un faux programme, jamais d'appel réel,
faux pio pour la relance. Code de sortie 0 = vert. Python de PlatformIO, depuis la racine du depot.

    python outils_docs/scripts_python/outils_pc/test_build_reparations_ia.py
"""

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

import test_build_serie as t                      # Montage, faux pio, verifie (liste ECHECS commune)
import build_reparations as br
import build_reparations_ia as ia

verifie, A, com, du_type = t.verifie, t.A, t.com, t.du_type
SECRET = "motdepasse123"
FAUX = Path(tempfile.mkdtemp(prefix="faux_claude_")) / "faux_claude.py"
PROG = '''import json, os, sys
d = os.environ["FAUX_DOSSIER"]
open(os.path.join(d, "stdin.txt"), "w", encoding="utf-8").write(sys.stdin.read())
json.dump({"argv": sys.argv[1:], "api": [k for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN") if k in os.environ]},
          open(os.path.join(d, "env.json"), "w"))
sys.stdout.write(open(os.path.join(d, "reponse.txt"), encoding="utf-8").read())
'''
TIMEOUT = ("TimeoutExpired: Command '['C:\\\\Users\\\\x\\\\.platformio\\\\penv\\\\Scripts\\\\uv.exe', 'pip', 'install', '--quiet', "
           "'-e', 'C:\\\\x\\\\tool-esptoolpy']' timed out after 60 seconds:")
JOURNAL = "\n".join(["Processing env", f'#define STA_PASS1 "{SECRET}"', TIMEOUT, '  File "penv_setup.py", line 563:', "[FAILED]"])
REGLE = {"titre": "Délai uv", "motif": r"TimeoutExpired: Command .*uv\.exe.* timed out after \d+ seconds",
         "actions": [{"action": "attendre", "parametres": {"secondes": 0}}]}


def reponse(dossier, proposition):
    texte = proposition if isinstance(proposition, str) else json.dumps(proposition)
    (dossier / "reponse.txt").write_text(json.dumps({"result": texte}), encoding="utf-8")


def diag(dossier, proposition, journal=JOURNAL, etape="prebuild"):
    reponse(dossier, proposition)
    return ia.diagnostique(str(dossier), "tasmota-essai", etape, journal, programme=[sys.executable, str(FAUX)])


def test_diagnostic():
    FAUX.write_text(PROG, encoding="utf-8")
    try:
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            os.environ["FAUX_DOSSIER"] = str(d)
            os.environ["OUTILS_TASMOTA_DOSSIER"] = str(d / "donnees")
            os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"            # temoins : ne doivent pas atteindre le fils
            os.environ["ANTHROPIC_AUTH_TOKEN"] = "jeton-test"
            r = diag(d, {"cause": "uv trop lent", "explication": "Le réseau est lent.", "regle": REGLE, "correctif_manuel": None})
            envoye = (d / "stdin.txt").read_text(encoding="utf-8")
            verifie((TIMEOUT in envoye, "prebuild" in envoye, "tasmota-essai" in envoye, SECRET in envoye, "STA_PASS1 ***" in envoye),
                    (True, True, True, False, True), "consigne : fin du journal, etape, env ; mot de passe filtre")
            env = json.loads((d / "env.json").read_text())
            verifie((env["api"], "bypassPermissions" in env["argv"], "Read,Grep,Glob" in env["argv"], "--settings" in env["argv"]),
                    ([], False, True, True), "claude : ni ANTHROPIC_API_KEY ni ANTHROPIC_AUTH_TOKEN, lecture seule, hooks coupes")
            verifie((r["ok"], r["cause"], (r["regle"] or {}).get("origine"), (r["regle"] or {}).get("etapes"), r["refus"]),
                    (True, "uv trop lent", "ia", ["prebuild"], ""), "cas d'usage uv.exe 60 s : regle attendre proposee")
            verifie(r["regle"] and r["regle"]["id"].startswith("ia_"), True, "regle : identifiant calcule")
            r = diag(d, "ceci n'est pas du json")
            verifie((r["ok"], r["regle"], bool(r["erreur"])), (False, None, True), "sortie non JSON : aucune proposition")
            r = diag(d, {"cause": "x", "regle": dict(REGLE, motif=r"TOTALEMENT absent du journal")})
            verifie((r["ok"], r["regle"], "ne correspond pas" in r["refus"], bool(r["correctif_manuel"])), (True, None, True, True),
                    "motif absent du journal : refusee, texte manuel")
            for motif in (".*", "x*", "(.*)(.*)(.*)"):
                r = diag(d, {"cause": "x", "regle": dict(REGLE, motif=motif)})
                verifie(r["regle"], None, f"motif trop large {motif!r} : refuse")
            r = diag(d, {"cause": "x", "regle": dict(REGLE, actions=[{"action": "rm -rf", "parametres": {}}])})
            verifie((r["regle"], "hors de la liste" in r["refus"]), (None, True), "action hors liste : refusee")
            r = diag(d, {"cause": "x", "regle": dict(REGLE, actions=[{"action": "libere_verrou"}])})
            verifie(r["regle"], None, "libere_verrou sans chemin dans le journal : refusee")
            r = diag(d, {"cause": "x", "regle": dict(REGLE, actions=[{"action": "attendre"}])})
            verifie(r["regle"], None, "attendre sans secondes : refusee")
            r = diag(d, {"cause": "x", "regle": dict(REGLE, motif="(")})
            verifie(r["regle"], None, "motif qui ne compile pas : refuse")
            r = diag(d, {"cause": "x", "regle": None, "correctif_manuel": f"voir {SECRET}"})
            verifie((r["ok"], r["regle"], r["correctif_manuel"]), (True, None, f"voir {SECRET}"), "pas de regle : texte manuel seulement")
            r = ia.diagnostique(str(d), "e", "prebuild", JOURNAL, programme=[sys.executable, "-c", "import sys; sys.exit(3)"])
            verifie((r["ok"], r["regle"]), (False, None), "claude en echec : aucune proposition")
    finally:
        for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
            os.environ.pop(k, None)


def test_application():
    echec = {"code": 1, "lignes": ["Processing {env}", TIMEOUT, "[FAILED] Took 0.10 seconds"]}
    for reussit in (True, False):
        with tempfile.TemporaryDirectory() as tmp:
            m = t.Montage(tmp, {A: {"build": echec}})
            ev = m.lance([com(A)], {"compiler"})
            verifie((du_type(ev, "fin_env")[0]["resultat"], A in m.serie.derniers_echecs), ("echec", True), "application : echec sans regle enregistre")
            journal = "\n".join(e["texte"] for e in ev if e["type"] == "ligne")
            c, nom = ia.contexte(m.serie, A)
            regle = ia.valide_regle(REGLE, journal, nom)
            if reussit:
                m.scenario.write_text("{}", encoding="utf-8")                  # la panne a disparu
            n = m.n
            res = ia.applique_et_relance(m.serie, A, regle, journal, sondage=0.05)
            ev = m.serie.depuis(n, 0)
            local = m.dossier / "reparations.json"
            regles = json.loads(local.read_text(encoding="utf-8"))["regles"] if local.is_file() else []
            etats = [e["etat"] for e in du_type(ev, "reparation", env=A)]
            if reussit:
                verifie((res["ok"], [(r["id"], r["origine"]) for r in regles], etats[0], etats[-1], len(m.appels())),
                        (True, [(regle["id"], "ia")], "en_cours", "reussie", 2), "application : relance reussie -> regle ajoutee (origine ia)")
                verifie(A in m.serie.derniers_echecs, False, "application : plus d'echec enregistre apres succes")
            else:
                verifie((res["ok"], regles, "echouee" in etats, len(m.appels())), (False, [], True, 2),
                        "application : relance echouee -> rien ajoute")
    with tempfile.TemporaryDirectory() as tmp:                                   # un envoi n'est jamais diagnostique ni relance
        m = t.Montage(tmp)
        m.serie.derniers_echecs["x"] = {"ligne": com(A), "action": "upload", "etape": "Téléversement", "actions": ["upload"]}
        try:
            ia.contexte(m.serie, "x")
            verifie(True, False, "contexte : etape d'envoi refusee")
        except RuntimeError:
            pass
        try:
            ia.contexte(m.serie, "inconnu")
            verifie(True, False, "contexte : env sans echec refuse")
        except RuntimeError:
            pass


def test_build_externe():
    """Un vrai build etranger (ou detection impossible) : AUCUNE action destructrice, refus."""
    echec = {"code": 1, "lignes": ["Processing {env}", TIMEOUT, "[FAILED] Took 0.10 seconds"]}
    for builds, nom in ((lambda n: ["pio run -e x"], "build externe"), (lambda n: None, "detection impossible")):
        with tempfile.TemporaryDirectory() as tmp:
            m = t.Montage(tmp, {A: {"build": echec}})
            ev = m.lance([com(A)], {"compiler"})
            journal = "\n".join(e["texte"] for e in ev if e["type"] == "ligne")
            c, etape = ia.contexte(m.serie, A)
            regle = ia.valide_regle(dict(REGLE, actions=[{"action": "vide_build", "parametres": {}}]), journal, etape)
            temoin = m.racine / ".pio" / "build" / A / "objet.o"
            temoin.parent.mkdir(parents=True)
            temoin.write_text("x")
            m.builds, avant, n = builds, len(m.appels()), m.n
            res = ia.applique_et_relance(m.serie, A, regle, journal, sondage=0.05)
            etats = [e["etat"] for e in du_type(m.serie.depuis(n, 0), "reparation", env=A)]
            verifie((res["ok"], res["regle_ajoutee"], temoin.exists(), len(m.appels()) - avant, etats[-1:], bool(res["message"])),
                    (False, False, True, 0, ["echouee"], True), f"application refusee, rien execute ({nom})")


def test_motif_imbrique():
    fin = "a" * 40 + "!"
    for motif in ("(a+)+$", "(.*)*$$$$", "(a*)*$$$$", "(a|aa)+$$$$", "(?:a+){2,}$$"):
        debut = time.monotonic()
        try:
            ia._regle(dict(REGLE, motif=motif), fin, "prebuild")
            refus = False
        except ValueError:
            refus = True
        verifie((refus, time.monotonic() - debut < 1), (True, True), f"motif imbrique {motif!r} refuse vite")


def test_verrou_catalogue():
    with tempfile.TemporaryDirectory() as tmp:
        m = t.Montage(tmp)
        rp = br.Reparateur(m.serie, [], libere=t._libere_interdit)
        rp.chemin_local = Path(tmp) / "reparations.json"
        regle = ia._regle(REGLE, JOURNAL, "prebuild")
        fait = threading.Event()
        with br.VERROU_CATALOGUE:
            threading.Thread(target=lambda: (rp.ajoute_regle_locale(regle), fait.set()), daemon=True).start()
            verifie(fait.wait(0.3), False, "catalogue : l'ajout attend le verrou")
        verifie(fait.wait(5), True, "catalogue : l'ajout reprend a la liberation")


def principal():
    t.garde_fou()
    test_diagnostic()
    test_application()
    test_build_externe()
    test_motif_imbrique()
    test_verrou_catalogue()
    print("\n" + ("VERT" if not t.ECHECS else f"ROUGE : {len(t.ECHECS)} echec(s) : {t.ECHECS}"))
    return 1 if t.ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
