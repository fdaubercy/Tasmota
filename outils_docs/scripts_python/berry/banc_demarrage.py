r"""Enveloppe du banc d'equivalence du demarrage (banc_demarrage.be), audit Berry P4.2 (2026-10-25).

Fait tourner l'autoexec.be ENTIER de chacune des 6 cartes maintenues sur le faux firmware de banc_boot et
compare son INSTANTANE (drivers, regles, commandes, crons, minuteries, fichiers compiles, globales, erreurs)
a la reference enregistree dans bouchons_berry/demarrage/<env>.txt. Une refonte de l'autoexec (module
'demarrage' commun) doit rendre les memes instantanes ; un ecart voulu se relit puis s'enregistre.

    python outils_docs/scripts_python/berry/banc_demarrage.py                 # compare les 6 cartes
    python outils_docs/scripts_python/berry/banc_demarrage.py --enregistre    # (re)ecrit les references
    python outils_docs/scripts_python/berry/banc_demarrage.py --carte <env>   # une seule carte
    python outils_docs/scripts_python/berry/banc_demarrage.py --sources <copie de data/fs>

Code de sortie 0 = vert (identiques), 1 = rouge (ecart ou echec), avec le diff des rubriques qui different.
Les cartes gelees (ancien maitre S3 du garage, cave ESP32) ne sont pas suivies.
"""
import difflib
import os
import subprocess
import sys

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BERRY = os.path.join(RACINE, "lib", "libesp32", "berry", "berry.exe" if os.name == "nt" else "berry")
BANC = "outils_docs/scripts_python/berry/banc_demarrage.be"
REFERENCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bouchons_berry", "demarrage")
CARTES = {
    "tasmota32p4-garage-serveur-modbus": "data/garage/tasmota32p4-serveur-modbus",
    "tasmota32s3-garage-capteurs-cuve-modbus": "data/garage/tasmota32s3-capteurs-cuve-modbus",
    "tasmota32s3-garage-rideau-garage-modbus": "data/garage/tasmota32s3-rideau-garage-modbus",
    "tasmota32s3-cave-serveur-rly": "data/cave/tasmota32s3-serveur-rly",
    "tasmota32-bureau-interrupteur-differentiel": "data/bureau/tasmota32-interrupteur-differentiel",
    "tasmota32s3-etage2-grenier": "data/etage2/tasmota32s3-grenier",
}


def instantane(env, carte, sources):
    sortie = subprocess.run([BERRY, BANC, "--env", env, "--carte", carte, sources], cwd=RACINE,
                            capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    lignes = sortie.splitlines()
    debut = next((i for i, l in enumerate(lignes) if l.startswith("carte : ")), None)
    return None if debut is None else "\n".join(lignes[debut:]) + "\n", sortie


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    enregistre = "--enregistre" in args
    sources = args[args.index("--sources") + 1] if "--sources" in args else "data/fs"
    cartes = {args[args.index("--carte") + 1]: CARTES[args[args.index("--carte") + 1]]} if "--carte" in args else CARTES
    os.makedirs(REFERENCES, exist_ok=True)
    rouges = []
    for env, carte in cartes.items():
        obtenu, brut = instantane(env, carte, sources)
        if obtenu is None:
            rouges.append(env)
            print("KO %s : instantane absent (le banc a echoue)\n%s" % (env, brut[-1500:]))
            continue
        chemin = os.path.join(REFERENCES, env + ".txt")
        if enregistre:
            with open(chemin, "w", encoding="utf-8", newline="\n") as f:
                f.write(obtenu)
            print("ENREGISTRE %s" % env)
            continue
        if not os.path.exists(chemin):
            rouges.append(env)
            print("KO %s : pas de reference (lancer --enregistre)" % env)
            continue
        attendu = open(chemin, encoding="utf-8").read()
        if obtenu == attendu:
            print("OK %s" % env)
        else:
            rouges.append(env)
            print("KO %s : instantane different de la reference" % env)
            for l in difflib.unified_diff(attendu.splitlines(), obtenu.splitlines(), "reference", "obtenu", lineterm="", n=0):
                print("    " + l[:600])
    if not enregistre:
        print("VERT" if not rouges else "ROUGE : %d carte(s) : %s" % (len(rouges), ", ".join(rouges)))
    return 1 if rouges else 0


if __name__ == "__main__":
    sys.exit(main())
