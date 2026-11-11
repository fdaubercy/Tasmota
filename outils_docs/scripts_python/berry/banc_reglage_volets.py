r"""Enveloppe du banc de test Berry du mode reglage des durees des volets (banc_reglage_volets.be).

UTILISATION
-----------
    python outils_docs/scripts_python/berry/banc_reglage_volets.py [dossier_sources]

dossier_sources (defaut data/fs, relatif a la racine ou absolu) : pour eprouver une copie (temoin mute) sans toucher
a data/fs. Code de sortie 0 si le banc est vert, 1 sinon (echec, module absent, banc introuvable).

CE QU'IL FAIT
-------------
Lance `lib/libesp32/berry/berry.exe banc_reglage_volets.be` DEPUIS LA RACINE (le banc lit `data/fs/vrReglage.be`
et `data/fs/vrFonctions.be` par chemin relatif), relaie sa sortie et traduit la derniere ligne
`BANC_REGLAGE_VOLETS: OK|ECHEC` en code de sortie.

CE QU'IL NE TESTE PAS
---------------------
Voir l'en-tete de banc_reglage_volets.be : la logique du module seulement, pas le vrai Shutter de Tasmota, ni les
vrais boutons, ni le moteur. Un banc vert ne remplace pas l'essai sur la carte.
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

    # cwd = racine : le banc lit data/fs/*.be et ses bouchons par chemin relatif.
    r = subprocess.run([str(berry), str(banc)] + sys.argv[1:], cwd=str(racine),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    sortie = (r.stdout or "") + (r.stderr or "")
    print(sortie, end="" if sortie.endswith("\n") else "\n")

    if r.returncode != 0:
        print(f"\n>>> berry a quitte en erreur (rc={r.returncode}).")
        return 1
    if "BANC_REGLAGE_VOLETS: OK" in sortie:
        return 0
    if "BANC_REGLAGE_VOLETS: ECHEC" in sortie:
        print("\n>>> Le banc signale un echec.")
        return 1
    print("\n>>> Verdict du banc introuvable dans la sortie -> anormal.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
