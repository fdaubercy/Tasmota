"""Banc de l'ecriture de l'atelier des ecrans (atelier_ecrans_ecriture.py), plan atelier-ecrans A8.

UTILISATION (copie temporaire du depot, rien d'autre ; ~10 s)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_ecrans_ecriture.py
Verifie : description du depot -> rien a ecrire ; texte modifie -> les trois fichiers ecrits en une transaction, egaux
aux generateurs ; build en cours ou indetectable, fichier modifie apres le diff, ecran.json modifie depuis le chargement
de la page -> refus, rien d'ecrit ; fins de ligne CRLF gardees ; lien vers la page Build. Code de sortie 0 = vert.
"""
import copy
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atelier_ecrans_catalogue as cat     # noqa: E402
import atelier_ecrans_description as aed   # noqa: E402
import atelier_ecrans_ecriture as aee      # noqa: E402
import test_atelier_ecrans_web as taw      # noqa: E402

ENV = "tasmota32s3-bureau-ecran-debits-pac"
ECHECS = []
AUCUN = lambda: []                                    # noqa: E731


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)


def refuse(f, motif, libelle):
    try:
        f()
    except RuntimeError as e:
        verifie(motif in str(e), True, libelle + ("" if motif in str(e) else f" [{e}]"))
        return
    verifie("pas de refus", "refus", libelle)


def instantane(racine):
    return {p: (racine / p).read_bytes() for p in aee.chemins(ENV).values() if (racine / p).is_file()}


def main():
    with tempfile.TemporaryDirectory(prefix="banc_atelier_ecriture_") as t:
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "donnees")
        racine = Path(t) / "depot"
        racine.mkdir()
        taw.copie(racine)
        desc = aed.charge(racine, ENV)
        emp_desc = aed.empreinte(aed.chemin(racine, ENV).read_bytes())
        p = aee.prevu(racine, ENV, desc)
        verifie(p["fichiers"], [], "description du depot : rien a ecrire (generateurs identiques au depot)")

        d2 = copy.deepcopy(desc)
        next(o for o in d2["objets"] if o["page"] == 0 and o["id"] == 1)["attributs"]["text"] = "Debits du chauffage"
        p = aee.prevu(racine, ENV, d2)
        verifie(sorted(f["rel"] for f in p["fichiers"]), sorted(aee.chemins(ENV).values()), "texte modifie : les trois fichiers au diff")
        avant = instantane(racine)
        refuse(lambda: aee.ecrit(racine, ENV, d2, p["empreinte"], emp_desc, lambda: ["tasmota32s3 upload"]), "build est en cours", "build en cours -> refus")
        refuse(lambda: aee.ecrit(racine, ENV, d2, p["empreinte"], emp_desc, lambda: None), "impossible de savoir", "build indetectable -> refus")
        refuse(lambda: aee.ecrit(racine, ENV, d2, p["empreinte"], "autre", AUCUN), "chargement de la page", "ecran.json change depuis la page -> refus")
        pj = racine / aee.chemins(ENV)["pages.jsonl"]
        pj.write_bytes(pj.read_bytes() + b"\n")
        refuse(lambda: aee.ecrit(racine, ENV, d2, p["empreinte"], emp_desc, AUCUN), "refaire le diff", "fichier modifie apres le diff -> refus")
        pj.write_bytes(avant[aee.chemins(ENV)["pages.jsonl"]])
        verifie(instantane(racine), avant, "apres les refus : rien n'a ete ecrit")

        r = aee.ecrit(racine, ENV, d2, p["empreinte"], emp_desc, AUCUN)
        gen = aee.generes(d2, cat.charge(racine))
        verifie(sorted(r["ecrits"]), sorted(aee.chemins(ENV).values()), "ecriture : les trois fichiers")
        verifie(all((racine / aee.chemins(ENV)[n]).read_bytes().replace(b"\r\n", b"\n") == gen[n] for n in gen), True,
                "ecriture : contenus = generateurs (fins de ligne du depot gardees)")
        verifie(r["empreinte_description"], aed.empreinte(aed.chemin(racine, ENV).read_bytes()), "empreinte de ecran.json rendue a la page")
        verifie(aee.prevu(racine, ENV, d2)["fichiers"], [], "apres ecriture : plus rien a ecrire")
        sauv = list((Path(t) / "donnees").rglob("*atelier-ecrans*"))
        verifie(bool(sauv), True, "transaction : copie de sauvegarde horodatee")

        for rel in aee.chemins(ENV).values():          # fichiers en CRLF (core.autocrlf) : rien a ecrire, CRLF garde
            f = racine / rel
            f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        verifie(aee.prevu(racine, ENV, d2)["fichiers"], [], "fichiers en CRLF identiques : rien a ecrire")
        d3 = copy.deepcopy(d2)
        next(o for o in d3["objets"] if o["page"] == 0 and o["id"] == 1)["attributs"]["text"] = "Autre"
        p = aee.prevu(racine, ENV, d3)
        aee.ecrit(racine, ENV, d3, p["empreinte"], aed.empreinte(aed.chemin(racine, ENV).read_bytes()), AUCUN)
        verifie(b"\n" not in (racine / aee.chemins(ENV)["pages.jsonl"]).read_bytes().replace(b"\r\n", b""), True, "fins de ligne CRLF gardees")

        mauvaise = copy.deepcopy(desc)
        mauvaise["objets"][0]["x"] = 5000
        try:
            aee.prevu(racine, ENV, mauvaise)
            verifie("accepte", "refus", "description invalide refusee")
        except ValueError as e:
            verifie("refusee" in str(e), True, "description invalide refusee")
        u = aee.url_build(racine, ENV)
        verifie(("env=" + ENV in u, "fichiers=pages.jsonl&" in u), (True, True), "lien page Build : env et fichier de l'interface haspmota")
    print(f"\n{len(ECHECS)} echec(s) : " + ("VERT" if not ECHECS else "ROUGE"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
