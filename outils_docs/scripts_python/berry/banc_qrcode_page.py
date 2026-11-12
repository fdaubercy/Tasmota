r"""Banc de la page /qrcode de la carte (data/fs/qrcodePage.be) : partie Berry (banc_qrcode_page.be), puis fichiers recus.

UTILISATION
-----------
    python outils_docs/scripts_python/berry/banc_qrcode_page.py [--garde DOSSIER] [--sources DOSSIER]

Depuis n'importe quel dossier. Code de sortie 0 si tout est vert, 1 sinon.
  --garde DOSSIER    : garde les fichiers produits (page.html, lib_recue.js.gz, ...) dans DOSSIER ; la sonde Chrome
                       (outils_pc/test_qrcode_carte_chrome.py) sert la page.html ainsi produite.
  --sources DOSSIER  : (temoin) lit fs/ et sd/ dans DOSSIER au lieu de data/.

CE QU'IL FAIT
-------------
1. Lance `berry.exe banc_qrcode_page.be <dossier>` depuis la racine : driver pose seulement avec /json/qrcode.json,
   bouton, acces refuse, bibliotheque et reglage par morceaux, 404 journalise, etat {ip, hostname}, page.
2. Compare octet par octet la bibliotheque recue et data/sd/js/qr-code-styling.min.js.gz, et verifie l'empreinte de ce
   .gz (outils_docs/etiquettes_qr/lib/LISEZMOI.md).

Le rendu dans un navigateur est juge par outils_pc/test_qrcode_carte_chrome.py. Ni le serveur web de Tasmota (Referer),
ni la RAM ne sont testes : un banc vert ne remplace pas l'essai sur une carte.
"""
import argparse
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

SHA256_GZ = "094ef5a2d3cf35e485fc3fc2a3bdd00d7c2fd99821020dd54270e5b54a96b1fb"


def trouve_racine() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    sys.exit("ERREUR : racine du depot introuvable.")


def lance_berry(racine: Path, dossier: Path, sources: "Path | None" = None) -> tuple:
    """(vert, sortie) de la partie Berry ; verdict = derniere ligne."""
    berry = next((c for c in (racine / "lib/libesp32/berry/berry.exe", racine / "lib/libesp32/berry/berry") if c.exists()), None)
    if berry is None:
        sys.exit("ERREUR : berry.exe introuvable sous lib/libesp32/berry/.")
    cmd = [str(berry), str(Path(__file__).with_suffix(".be")), str(dossier)] + ([str(sources)] if sources else [])
    r = subprocess.run(cmd, cwd=str(racine), capture_output=True, text=True, encoding="utf-8", errors="replace")
    sortie = (r.stdout or "") + (r.stderr or "")
    lignes = sortie.strip().splitlines()
    return r.returncode == 0 and bool(lignes) and lignes[-1] == "BANC_QRCODE_PAGE: OK", sortie


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Banc de la page /qrcode de la carte.")
    ap.add_argument("--garde", metavar="DOSSIER", help="garder les fichiers produits dans DOSSIER")
    ap.add_argument("--sources", metavar="DOSSIER", help="temoin : dossier fs/ + sd/ a la place de data/")
    args = ap.parse_args()

    racine = trouve_racine()
    sources = Path(args.sources).resolve() if args.sources else racine / "data"
    if args.garde:
        dossier = Path(args.garde).resolve()
        dossier.mkdir(parents=True, exist_ok=True)
    else:
        temp = tempfile.TemporaryDirectory(prefix="banc_qrcode_page_")
        dossier = Path(temp.name)

    print("=== Partie Berry (banc_qrcode_page.be)")
    vert, sortie = lance_berry(racine, dossier, sources if args.sources else None)
    print(sortie, end="" if sortie.endswith("\n") else "\n")
    if not vert:
        print(">>> Partie Berry en echec (ou verdict introuvable).\nBANC_QRCODE_PAGE: ECHEC")
        return 1

    print("=== Fichiers recus")
    gz = sources / "sd/js/qr-code-styling.min.js.gz"
    recu = dossier / "lib_recue.js.gz"
    controles = [
        (recu.exists() and recu.read_bytes() == gz.read_bytes(), "bibliotheque recue identique au fichier du depot (octet par octet)"),
        (hashlib.sha256(gz.read_bytes()).hexdigest() == SHA256_GZ, "empreinte du .gz = celle de lib/LISEZMOI.md"),
    ]
    for ok, nom in controles:
        print(("  OK     " if ok else "  ECHEC  ") + nom)
    vert = all(ok for ok, _ in controles)
    print("BANC_QRCODE_PAGE: OK" if vert else "BANC_QRCODE_PAGE: ECHEC")
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())
