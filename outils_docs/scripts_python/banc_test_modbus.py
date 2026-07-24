r"""Enveloppe du banc de test Berry ModBus (banc_test_modbus.be).

UTILISATION
-----------
    python outils_docs/scripts_python/banc_test_modbus.py

Depuis n'importe quel dossier : la racine du depot et l'interpreteur berry
natif sont deduits. Code de sortie 0 si le banc est vert, 1 sinon (echec
inattendu, ou banc introuvable) -> utilisable comme garde avant un flash.

CE QU'IL FAIT
-------------
Lance `lib/libesp32/berry/berry.exe banc_test_modbus.be` DEPUIS LA RACINE (le
banc lit `data/fs/modbusFonctions.be` par chemin relatif), relaie sa sortie,
et traduit la derniere ligne `BANC_MODBUS: OK|ECHEC` en code de sortie.

POURQUOI UNE ENVELOPPE PYTHON
-----------------------------
Le banc est du Berry, mais il vit avec les autres outils Python du depot et se
lance comme eux. L'enveloppe rend le lancement independant du dossier courant
et fournit un code de sortie exploitable (le Berry n'en pose pas de lui-meme).

CE QU'IL NE TESTE PAS
---------------------
Voir l'en-tete de banc_test_modbus.be : logique deterministe seulement, pas le
timing, pas la file, pas la carte 16 reelle. Un banc vert ne remplace pas
l'observation sur bus reel apres flash.
"""
import subprocess
import sys
from pathlib import Path


def trouve_racine() -> Path:
    """Racine du depot, deduite de l'emplacement de ce script."""
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    sys.exit("ERREUR : racine du depot introuvable.")


def trouve_berry(racine: Path) -> Path:
    """L'interpreteur Berry natif livre avec le depot."""
    for c in (racine / "lib" / "libesp32" / "berry" / "berry.exe",
              racine / "lib" / "libesp32" / "berry" / "berry"):
        if c.exists():
            return c
    sys.exit("ERREUR : berry.exe introuvable sous lib/libesp32/berry/. "
             "Un build a-t-il deja ete fait une fois ?")


def main() -> int:
    racine = trouve_racine()
    berry = trouve_berry(racine)
    banc = Path(__file__).with_suffix(".be")
    if not banc.is_file():
        sys.exit(f"ERREUR : {banc.name} introuvable a cote de ce script.")

    # cwd = racine : le banc lit data/fs/modbusFonctions.be par chemin relatif.
    r = subprocess.run([str(berry), str(banc)], cwd=str(racine),
                       capture_output=True, text=True)
    sortie = (r.stdout or "") + (r.stderr or "")
    print(sortie, end="" if sortie.endswith("\n") else "\n")

    if r.returncode != 0:
        print(f"\n>>> berry a quitte en erreur (rc={r.returncode}).")
        return 1
    if "BANC_MODBUS: OK" in sortie:
        return 0
    if "BANC_MODBUS: ECHEC" in sortie:
        print("\n>>> Le banc signale un echec INATTENDU (pas un bug connu).")
        return 1
    print("\n>>> Verdict du banc introuvable dans la sortie -> anormal.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
