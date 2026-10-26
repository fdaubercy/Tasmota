r"""Banc du controle des renvois des documents durables (verifie_references_docs.py) et de la carte des
modules deterministe (carte_modules_berry.py) - audit Berry P10.7.

  python outils_docs/scripts_python/maintenance/test_verifie_references_docs.py [--sans-carte]

Code de sortie 0 = vert. Partie 1 : chaque regle a un TEMOIN (renvoi faux qui doit etre signale) et un cas
CONFORME (renvoi juste qui doit passer). Partie 2 : les documents durables du depot, 0 defaut attendu.
Partie 3 (~1 min, sautee par --sans-carte) : carte_modules_berry.py genere deux fois avec deux graines de
hachage differentes -> sorties identiques octet pour octet (constat B16), sans le faux diagnostic sur
controleRideau (S7). Documents de test et cartes generees dans un dossier temporaire.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import verifie_references_docs as V  # noqa: E402

RACINE = V.racine_depot()
INDEX = V.Index(RACINE, externes=False)
PY_PIO = Path.home() / ".platformio" / "penv" / "Scripts" / "python.exe"
echecs = []


def verifie(nom, condition, detail=""):
    print(f"{'OK' if condition else 'KO'}  {nom}" + ("" if condition else f"\n      {detail}"))
    if not condition:
        echecs.append(nom)


def cas(nom, texte, genres_attendus, hors_attendus=0):
    """genres_attendus : liste des genres de defaut ('ligne', 'chemin', 'fonction'), dans l'ordre."""
    with tempfile.TemporaryDirectory() as d:
        doc = Path(d) / "doc.md"
        doc.write_text(texte, encoding="utf-8")
        defauts, hors = V.verifie_document(doc, RACINE, INDEX)
    genres = [l.split(": ", 2)[1] for l in defauts]
    verifie(nom, genres == genres_attendus and len(hors) == hors_attendus,
            f"attendu {genres_attendus} + {hors_attendus} hors depot ; obtenu {defauts} {hors}")


print("== 1. Regles (temoin signale / conforme muet) ==")
cas("ligne : fichier.be:N", "Voir `modbusFonctions.be:1791`.\n", ["ligne"])
cas("ligne : intervalle hors accents", "Voir be_module.c:282-288 pour l'ordre.\n", ["ligne"])
cas("ligne : forme courte `:N`", "Dans `udpFonctions.be` (`:485`).\n", ["ligne"])
cas("conforme : bloc de code ignore", "```\nmodbusFonctions.be:12\n`:13`\n```\n", [])
cas("chemin : absent du depot", "Le fichier `data/fs/nexistepas.be`.\n", ["chemin"])
cas("chemin : module de carte cherche a tort dans data/fs (B16)", "`data/fs/controleRideau.be`\n", ["chemin"])
cas("conforme : chemin present", "Le fichier `data/fs/logFonctions.be`.\n", [])
cas("conforme : chemin partiel (fin d'un chemin suivi)", "`berry/charte_logs.py` et `fs/logFonctions.be`\n", [])
cas("conforme : abreviation P/ des skills", "`P/berry/verifie_berry.py`\n", [])
cas("conforme : motif ou gabarit non verifie", "`data/<lieu>/<carte>/autoexec.be` et `data/fs/*.be`\n", [])
cas("hors depot : signale sans defaut", "`src/solidify/solidified_driver_class.h`\n", [], hors_attendus=1)
cas("genere par un build (absent hors build) : non verifie", "`tasmota/tasmota.ino.cpp` et `berry_custom/src/_temp_be_x_lib.c`\n",
    [], hors_attendus=2)
cas("temoin : chemin du depot absent, non genere -> defaut", "`tasmota/nexistepas.cpp`\n", ["chemin"])
cas("fonction : definie (Berry, nom court)", "`logFonctions.be::actif`\n", [])
cas("fonction : definie (Berry, nom complet)", "`logFonctions.be::logFonctions_actif`\n", [])
cas("fonction : definie (C)", "`be_module.c::be_module_load`\n", [])
cas("fonction : methode Python Classe.methode", "`verifie_references_docs.py::Index.trouve`\n", [])
cas("fonction : macro #define", "`user_config_override.h::USE_BERRY_DEBUG`\n", [])
cas("fonction : cle d'un .ini (presence)", "`platformio_tasmota_cenv.ini::custom_berry_solidify`\n", [])
cas("fonction : absente du fichier", "`logFonctions.be::fonctionQuiNexistePas`\n", ["fonction"])
cas("fonction : simple appel, pas une definition (C)", "`be_module.c::be_raise`\n", ["fonction"])
cas("fonction : fichier absent", "`data/fs/nexistepas.be::f`\n", ["chemin"])

print("\n== 2. Documents durables du depot ==")
r = subprocess.run([sys.executable, str(ICI / "verifie_references_docs.py")], cwd=str(RACINE),
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
print("    " + (r.stdout.strip().splitlines() or ["(aucune sortie)"])[-1])
verifie("documents durables : 0 defaut (code 0)", r.returncode == 0,
        "\n      ".join(l for l in r.stdout.splitlines() if "hors depot" not in l))

if "--sans-carte" not in sys.argv:
    print("\n== 3. carte_modules_berry.py deterministe (deux graines de hachage) ==")
    with tempfile.TemporaryDirectory() as d:
        sorties = []
        for graine in ("1", "3"):
            s = Path(d) / f"carte_{graine}.md"
            env = dict(os.environ, PYTHONHASHSEED=graine, PYTHONIOENCODING="utf-8")
            rc = subprocess.run([str(PY_PIO if PY_PIO.exists() else sys.executable),
                                 str(ICI.parent / "berry" / "carte_modules_berry.py"), "--sortie", str(s)],
                                cwd=str(RACINE), env=env, capture_output=True, timeout=300).returncode
            sorties.append(s.read_bytes() if rc == 0 and s.exists() else b"")
        verifie("carte generee", all(sorties), "une generation a echoue")
        verifie("deux generations identiques octet pour octet (B16)", sorties[0] == sorties[1] and sorties[0] != b"")
        verifie("pas de faux diagnostic sur controleRideau (S7)",
                b"controleRideau` est dans custom_berry_solidify" not in sorties[0])

print()
print("VERT" if not echecs else f"ROUGE : {len(echecs)} echec(s)")
sys.exit(1 if echecs else 0)
