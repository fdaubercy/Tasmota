r"""Banc du moteur commun des pages de graphiques (data/fs/pagesGraphiques.be, atelier des graphiques A2).

UTILISATION
-----------
    python outils_docs/scripts_python/berry/banc_pages_graphiques.py [--garde DOSSIER] [--sources DOSSIER]

Depuis n'importe quel dossier : la racine du depot et berry.exe sont deduits.
Code de sortie 0 si tout est vert, 1 sinon.
  --garde DOSSIER    : garde les fichiers produits (pages, reponses JSON, module copie) dans DOSSIER.
  --sources DOSSIER  : (temoin) lit pagesGraphiques.be, graphiquesFonctions.be et cuvePageFonctions.be dans DOSSIER au
                       lieu de data/fs ; sert a prouver que le banc mord, sur une COPIE mutee (jamais le vrai fichier).

CE QU'IL FAIT
-------------
1. Lance `berry.exe banc_pages_graphiques.be <dossier> <sources>` depuis la racine : module charge comme solidifie
   (globale du module et noms globaux de ses fonctions retires apres un import qui passe par init()), memes verdicts
   que atelier_graphiques_description::valide sur bouchons_berry/pages_graphiques/cas_description.json, description
   absente / tronquee / illisible / invalide / trop grosse (aucun bouton, page « Description invalide », erreur
   journalisee, aucune exception), index et boutons (acces "bouton" seulement), page (ordre du gabarit,
   window.PAGE_GRAPHIQUES, '</' echappe), f=valeurs (null si absent, 13 chemins refuses), f=sources, extension
   liquidfill par morceaux, mesure du tas Berry avant/apres demarre() avec 8 pages, table du module inchangee.
2. Compare octet par octet l'extension recue et data/sd/js/echarts-liquidfill.min.js.gz.

CE QU'IL NE TESTE PAS
---------------------
La vraie carte : ni le serveur web de Tasmota (Referer), ni la RAM de l'ESP32 (berry.exe est en 64 bits : la mesure
donne un ordre de grandeur), ni le vrai gabarit (bouchons de bouchons_berry/pages_graphiques/sd, action A3), ni le
trace dans un navigateur.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def trouve_racine() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    sys.exit("ERREUR : racine du depot introuvable.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Banc du moteur commun des pages de graphiques (pagesGraphiques.be).")
    ap.add_argument("--garde", help="dossier ou garder les fichiers produits")
    ap.add_argument("--sources", help="dossier contenant pagesGraphiques.be (temoin)")
    args = ap.parse_args()
    racine = trouve_racine()
    berry = next((c for c in (racine / "lib/libesp32/berry/berry.exe", racine / "lib/libesp32/berry/berry") if c.exists()), None)
    if berry is None:
        sys.exit("ERREUR : berry.exe introuvable sous lib/libesp32/berry/.")
    sources = Path(args.sources).resolve() if args.sources else racine / "data/fs"
    with tempfile.TemporaryDirectory() as tmp:
        dossier = Path(args.garde).resolve() if args.garde else Path(tmp)
        dossier.mkdir(parents=True, exist_ok=True)
        cmd = [str(berry), str(Path(__file__).with_suffix(".be")), dossier.as_posix(), sources.as_posix()]
        r = subprocess.run(cmd, cwd=str(racine), capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(r.stdout, end="")
        if r.stderr:
            print(r.stderr, end="")
        lignes = [l for l in r.stdout.splitlines() if l.strip()]
        ok = r.returncode == 0 and bool(lignes) and lignes[-1] == "BANC_PAGES_GRAPHIQUES: OK"     # verdict = derniere ligne
        recu = dossier / "liquidfill_recu.js.gz"
        attendu = racine / "data/sd/js/echarts-liquidfill.min.js.gz"
        identique = recu.exists() and recu.read_bytes() == attendu.read_bytes()
        print(("  OK     " if identique else "  ECHEC  ") + "extension recue identique a data/sd/js/echarts-liquidfill.min.js.gz"
              + (" (%d o)" % attendu.stat().st_size if identique else ""))
        ok = ok and identique
    print("BANC_PAGES_GRAPHIQUES (enveloppe) : " + ("OK" if ok else "ECHEC"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
