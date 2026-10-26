r"""Banc de l'alerte « firmware du coprocesseur Wi-Fi (ESP32-C6) pas a jour » des P4 (controleCoprocesseur.be).

UTILISATION
-----------
    python outils_docs/scripts_python/berry/banc_coprocesseur.py [--sans-navigateur] [--sources DOSSIER]

Depuis n'importe quel dossier : la racine du depot, berry.exe et Chrome (ou Edge) sont deduits.
Code de sortie 0 si tout est vert, 1 sinon -> utilisable comme garde avant un televersement.
  --sans-navigateur : seulement la partie Berry (la page n'est alors PAS rendue).
  --sources DOSSIER : dossier des sources (defaut data/fs), pour eprouver une copie (temoin).

CE QU'IL FAIT
-------------
1. Lance `berry.exe banc_coprocesseur.be <sources> <page.html>` DEPUIS LA RACINE : garde du persist, comparaison
   numerique des versions, lecture de l'en-tete d'image (esp_app_desc_t), essais vers le serveur (a jour : aucun ;
   en retard : un, puis un par heure en cas d'echec, 6 au plus), ligne d'accueil, page /coprocesseur, HostedOta.
2. Rend la page /coprocesseur du scenario « en retard, publie » (gabarit reel data/sd/html/coprocesseur.html +
   donnees produites par le module) dans Chrome sans interface et juge le DOM rempli par son script : versions
   affichees, bouton present, aucune erreur JS (lecon du 2026-10-16 : une page s'execute dans un vrai navigateur).

CE QU'IL NE TESTE PAS
---------------------
Ni le vrai serveur web de Tasmota, ni le reseau, ni ota.tasmota.com, ni la mise a jour reelle du C6 : un banc
vert ne remplace pas l'essai sur le P4 (A5 du plan alerte-firmware-c6).
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from banc_graphiques import trouve_navigateur  # noqa: E402  (meme dossier : module voisin)


def trouve_racine() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    sys.exit("ERREUR : racine du depot introuvable.")


def trouve_berry(racine: Path) -> Path:
    for c in (racine / "lib" / "libesp32" / "berry" / "berry.exe",
              racine / "lib" / "libesp32" / "berry" / "berry"):
        if c.exists():
            return c
    sys.exit("ERREUR : berry.exe introuvable sous lib/libesp32/berry/. Un build a-t-il deja ete fait une fois ?")


# Sonde injectee en tete de page : erreurs JS captees, bilan ecrit dans le DOM apres le chargement
SONDE = ("<script>window.__erreurs=[];window.addEventListener('error',function(e){window.__erreurs.push(e.message)});"
         "window.addEventListener('load',function(){setTimeout(function(){var d=document.createElement('pre');"
         "d.id='bilan_sonde';d.textContent='ERREURS='+window.__erreurs.length+' '+window.__erreurs.join(' | ');"
         "document.body.appendChild(d)},300)});</script>")


def texte(dom: str, ident: str) -> str:
    m = re.search(r"id=\"%s\"[^>]*>(.*?)</" % re.escape(ident), dom, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def partie_navigateur(navigateur: str, page: Path, dossier: Path) -> int:
    html = page.read_text(encoding="utf-8")
    fichier = dossier / "coprocesseur_rendu.html"
    fichier.write_text("<!doctype html><html><head><meta charset='utf-8'></head><body>" + SONDE + html
                       + "</body></html>", encoding="utf-8")
    r = subprocess.run([navigateur, "--headless=new", "--disable-gpu", "--no-first-run", "--lang=fr-FR",
                        f"--user-data-dir={dossier / 'profil'}", "--virtual-time-budget=3000", "--dump-dom",
                        fichier.as_uri()], capture_output=True, timeout=90)
    dom = r.stdout.decode("utf-8", "replace")
    echecs = 0

    def verifie(c, nom):
        nonlocal echecs
        print(("  ok   " if c else "  ECHEC ") + nom)
        if not c:
            echecs += 1

    print("R. Rendu de la page /coprocesseur dans le navigateur")
    bilan = texte(dom, "bilan_sonde")
    verifie(bilan.startswith("ERREURS=0"), f"aucune erreur JS ({bilan or 'bilan absent'})")
    verifie(texte(dom, "c_c6") == "2.6.6", f"version du C6 affichee ({texte(dom, 'c_c6')!r})")
    verifie(texte(dom, "c_hote") == "2.12.13", f"version visee affichee ({texte(dom, 'c_hote')!r})")
    verifie("2.12.6" in texte(dom, "c_defaut"), "version du fichier par defaut signalee")
    verifie(re.search(r"id=\"c_maj\"(?![^>]*display:\s*none)", dom) is not None, "formulaire de mise a jour visible")
    verifie(re.search(r"<form[^>]*method=\"post\"[^>]*action=\"/coprocesseur\"", dom, re.I) is not None
            or re.search(r"<form[^>]*action=\"/coprocesseur\"[^>]*method=\"post\"", dom, re.I) is not None,
            "formulaire POST /coprocesseur")
    verifie(re.search(r"id=\"c_lancee\"[^>]*display:\s*none", dom) is not None, "message « lancee » cache")
    return echecs


def main() -> int:
    ap = argparse.ArgumentParser(description="Banc de l'alerte du firmware du coprocesseur C6 (Berry + rendu Chrome).")
    ap.add_argument("--sans-navigateur", action="store_true")
    ap.add_argument("--sources", default="data/fs")
    args = ap.parse_args()

    racine = trouve_racine()
    berry = trouve_berry(racine)
    banc = Path(__file__).with_suffix(".be")
    with tempfile.TemporaryDirectory() as tmp:
        dossier = Path(tmp)
        page = dossier / "page.html"
        # cwd = racine : le banc lit data/fs/*.be, data/sd/html/ et ses bouchons par chemin relatif
        r = subprocess.run([str(berry), str(banc), args.sources, str(page)], cwd=str(racine),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        sortie = (r.stdout or "") + (r.stderr or "")
        print(sortie, end="" if sortie.endswith("\n") else "\n")
        if r.returncode != 0:
            print(f"\n>>> berry a quitte en erreur (rc={r.returncode}).")
            return 1
        if "BANC_COPROCESSEUR: OK" not in sortie:
            print("\n>>> Partie Berry en echec (ou verdict introuvable).")
            return 1
        if args.sans_navigateur:
            print("\n>>> Partie Berry verte ; rendu NON verifie (--sans-navigateur).")
            return 0
        navigateur = trouve_navigateur()
        if navigateur is None:
            print("\n>>> Chrome ou Edge introuvable : rendu non verifie. Relancer avec --sans-navigateur.")
            return 1
        if not page.is_file():
            print("\n>>> La partie Berry n'a pas ecrit la page.")
            return 1
        echecs = partie_navigateur(navigateur, page, dossier)
    print("\nBANC_COPROCESSEUR_COMPLET: " + ("OK" if echecs == 0 else f"ECHEC ({echecs})"))
    return 0 if echecs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
