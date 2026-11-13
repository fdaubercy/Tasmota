r"""Enveloppe du banc Berry de la affichage de l ecran de la cave (MQTT) (banc_ecran_cave.be).

    python outils_docs/scripts_python/berry/banc_ecran_cave.py

Lance berry.exe depuis la racine du depot et traduit la derniere ligne `BANC_ECRAN_CAVE: OK|ECHEC` en code de
sortie (0 = vert). Limites : voir l'en-tete de banc_ecran_cave.be (pas de firmware reel).
"""
import subprocess
import sys
from pathlib import Path


def main() -> int:
    p = Path(__file__).resolve().parent
    while p != p.parent and not (p / ".git").exists():
        p = p.parent
    berry = next((c for c in (p / "lib/libesp32/berry/berry.exe", p / "lib/libesp32/berry/berry") if c.exists()), None)
    if berry is None:
        sys.exit("ERREUR : berry.exe introuvable sous lib/libesp32/berry/.")
    banc = Path(__file__).with_suffix(".be")
    r = subprocess.run([str(berry), str(banc), *sys.argv[1:]], cwd=str(p), capture_output=True, text=True)
    sortie = (r.stdout or "") + (r.stderr or "")
    print(sortie, end="" if sortie.endswith("\n") else "\n")
    return 0 if r.returncode == 0 and "BANC_ECRAN_CAVE: OK" in sortie else 1


if __name__ == "__main__":
    sys.exit(main())
