r"""Enveloppe du banc de test Berry ModBus (banc_test_modbus.be).

UTILISATION
-----------
    python outils_docs/scripts_python/berry/banc_test_modbus.py [dossier_sources]

dossier_sources (defaut data/fs, relatif a la racine) : pour eprouver un
correctif sur une copie sans toucher a data/fs. Depuis n'importe quel dossier : la racine du depot et l'interpreteur berry
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

Avant le banc, il controle aussi les IDENTIFIANTS des `_persist.json` suivis
(2026-10-18) : sur une carte ModBus active, serveur.udp.id et serveur.tcp.id
doivent valoir drivers.ModBus.id ; Range Extender actif, ModBus.id, udp.id et
tcp.id doivent valoir serveur.rangeExtender.id. C'est l'alignement que font
controleModbus et controleRangeExtender au demarrage (par un redemarrage) : un
persist du depot desaligne ferait redemarrer la carte apres chaque flash, et le
maitre journaliserait ID_INCOHERENT sur sa fiche. Un ecart fait echouer le banc.

CE QU'IL NE TESTE PAS
---------------------
Voir l'en-tete de banc_test_modbus.be : logique deterministe seulement, pas le
timing, pas la file, pas la carte 16 reelle. Un banc vert ne remplace pas
l'observation sur bus reel apres flash.
"""
import json
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


def persists_suivis(racine: Path) -> list:
    """Les _persist.json suivis par git sous data/, hors dossiers de sauvegarde."""
    r = subprocess.run(["git", "ls-files", "data"], cwd=str(racine), capture_output=True, text=True)
    return [racine / f for f in r.stdout.splitlines()
            if f.endswith("_persist.json") and "sauvegarde" not in f.lower()]


def ecarts_identifiants(fichiers: list) -> list:
    """Ecarts d'identifiants (texte) des persists donnes ; [] si tout est aligne."""
    ecarts = []
    for f in fichiers:
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            ecarts.append(f"{f} : illisible ({e})")
            continue
        serveur = d.get("serveur", {})
        modbus = d.get("drivers", {}).get("ModBus", {})
        rgx = serveur.get("rangeExtender", {})
        ids = {"udp.id": serveur.get("udp", {}).get("id"), "tcp.id": serveur.get("tcp", {}).get("id"),
               "ModBus.id": modbus.get("id")}
        # Range Extender actif : son id l'emporte (controleRangeExtender est charge apres controleModbus)
        if rgx.get("activation", "OFF") == "ON":
            reference, nom = rgx.get("id"), "rangeExtender.id"
        elif modbus.get("activation", "OFF") == "ON":
            reference, nom = modbus.get("id"), "ModBus.id"
        else:
            continue
        for cle, valeur in ids.items():
            if cle != nom and valeur is not None and valeur != reference:
                ecarts.append(f"{Path(f).parent.name} : {cle}={valeur} different de {nom}={reference}")
    return ecarts


def main() -> int:
    racine = trouve_racine()
    berry = trouve_berry(racine)

    fichiers = persists_suivis(racine)
    ecarts = ecarts_identifiants(fichiers)
    print(f"IDENTIFIANTS : {len(fichiers)} persists controles, {len(ecarts)} ecart(s)")
    for e in ecarts:
        print(f"  [FAIL] {e}")
    banc = Path(__file__).with_suffix(".be")
    if not banc.is_file():
        sys.exit(f"ERREUR : {banc.name} introuvable a cote de ce script.")

    # cwd = racine : le banc lit data/fs/*.be et ses bouchons par chemin relatif.
    # Argument optionnel transmis tel quel : dossier des sources (defaut data/fs).
    r = subprocess.run([str(berry), str(banc)] + sys.argv[1:], cwd=str(racine),
                       capture_output=True, text=True)
    sortie = (r.stdout or "") + (r.stderr or "")
    print(sortie, end="" if sortie.endswith("\n") else "\n")

    if r.returncode != 0:
        print(f"\n>>> berry a quitte en erreur (rc={r.returncode}).")
        return 1
    if ecarts:
        print("\n>>> Identifiants desalignes dans un _persist.json du depot (voir IDENTIFIANTS ci-dessus).")
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
