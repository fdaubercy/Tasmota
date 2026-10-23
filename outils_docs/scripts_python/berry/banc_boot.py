r"""Enveloppe du banc de test Berry du demarrage du maitre P4 (banc_boot.be).

UTILISATION
-----------
    python outils_docs/scripts_python/berry/banc_boot.py [dossier_sources] [--verbeux]

dossier_sources (defaut data/fs, relatif a la racine) : pour eprouver un correctif ou une
mutation sur une COPIE ENTIERE de data/fs sans y toucher (une copie partielle : io_error).
--verbeux : imprime chaque log emis pendant le demarrage. Depuis n'importe quel dossier : la
racine du depot et l'interpreteur berry natif sont deduits. Code de sortie 0 si le banc est
vert, 1 sinon (echec inattendu, ou verdict introuvable) -> utilisable comme garde avant un flash.

CE QU'IL FAIT
-------------
Lance `lib/libesp32/berry/berry.exe banc_boot.be` DEPUIS LA RACINE, relaie sa sortie et
traduit la derniere ligne `BANC_BOOT: OK|ECHEC` en code de sortie. banc_boot.be lance lui-meme
un processus berry par cas (voir son en-tete) : persist reel du P4, persist '{}', persist prive
de serveur.wifi. Les defauts connus (CONNU) ne font pas echouer le banc.

Ecrit seulement dans .pio/banc_boot/ (enveloppes des modules solidifies, ignore par git) :
le LittleFS de la carte est simule en memoire, aucun port, aucun reseau.

CE QU'IL NE TESTE PAS
---------------------
Voir l'en-tete de banc_boot.be : pas de timing ni de memoire reels, pas de bus ModBus ni I2C,
le P4 seulement. Un banc vert ne remplace pas l'observation de la carte apres televersement.
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

    # cwd = racine : le banc lit data/, platformio_tasmota_cenv.ini et ses bouchons par chemin relatif.
    # Chemin du banc RELATIF a la racine : il est repasse tel quel aux processus des cas.
    r = subprocess.run([str(berry), banc.relative_to(racine).as_posix()] + sys.argv[1:],
                       cwd=str(racine), capture_output=True, text=True, encoding="utf-8", errors="replace")
    sortie = (r.stdout or "") + (r.stderr or "")
    print(sortie, end="" if sortie.endswith("\n") else "\n")

    lignes = [l for l in sortie.splitlines() if l.strip()]
    derniere = lignes[-1] if lignes else ""
    if derniere == "BANC_BOOT: OK":
        return 0
    if derniere.startswith("BANC_BOOT: ECHEC"):
        print("\n>>> Le banc signale un echec INATTENDU (les defauts connus s'affichent CONNU).")
        return 1
    print(f"\n>>> Verdict du banc introuvable en derniere ligne (rc berry={r.returncode}) -> anormal.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
