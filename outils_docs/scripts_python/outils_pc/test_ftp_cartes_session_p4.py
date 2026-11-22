"""Banc voisin de test_ftp_cartes_session_garde.py : carte qui IGNORE l'argument de MLSD et de LIST (constate sur le P4 du garage le 2026-11-22,
essai A7 : `MLSD /ftp_test_a7` rendait la racine ; seul `CWD` puis `MLSD` sans argument rend le bon dossier). Code de sortie 0 = vert.

Le faux serveur est mis dans ce mode par `liste_sans_argument` : tout geste qui lit un sous-dossier (liste, zip, suppression recursive,
protege, envoi, deplacement) doit voir le bon dossier, et la session doit rendre le dossier courant a « / ».
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_ftp_cartes_session_p4.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import io
import sys
import zipfile

import ftp_cartes_session as fs
from test_ftp_cartes_session import CARTE, ECHECS, Banc, leve, verifie
from test_ftp_cartes_session_garde import SECONDE, ecritures


def banc(**opts):
    b = Banc(**opts)
    b.srv.liste_sans_argument = True
    b.fichier("/racine.txt", b"R")
    b.fichier("/d/dedans.txt", b"D")
    b.fichier("/d/sous/profond.txt", b"P")
    b.fichier("/d/autoexec.be", b"cfg")
    return b


def noms(entrees):
    return sorted(e["nom"] for e in entrees)


def cas_liste_sous_dossier():
    """Un sous-dossier se liste par lui-meme, pas par la racine ; le dossier courant revient a « / »."""
    for sans_mlsd in (False, True):                                       # MLSD, puis repli LIST
        with banc(sans_mlsd=sans_mlsd) as b:
            b.s.ouvre(CARTE, "flash")
            quoi = "LIST" if sans_mlsd else "MLSD"
            verifie(noms(b.s.liste("/")), ["d", "racine.txt"], "%s : la racine" % quoi)
            verifie(noms(b.s.liste("/d")), ["autoexec.be", "dedans.txt", "sous"], "%s : /d liste /d (pas la racine)" % quoi)
            verifie(noms(b.s.liste("/d/sous")), ["profond.txt"], "%s : /d/sous liste /d/sous" % quoi)
            verifie(b.srv.commandes[-1], ("CWD", "/"), "%s : le dossier courant revient a la racine apres le listage" % quoi)
            verifie(leve(fs.RefusFtp, b.s.liste, "/absent") is not None, True, "%s : dossier absent refuse (CWD 550), pas la racine" % quoi)
            verifie(noms(b.s.liste("/d")), ["autoexec.be", "dedans.txt", "sous"], "%s : la session reste utilisable apres le refus" % quoi)
            verifie(all(a == "" for c, a in b.srv.commandes if c in ("MLSD", "LIST")), True, "%s : jamais d'argument de chemin" % quoi)


def cas_zip_dossier():
    """Zip d'un sous-dossier : seulement ses fichiers, aux bons chemins (aucun .drvset de la racine cherche dedans)."""
    with banc() as b:
        b.s.ouvre(CARTE, "flash")
        sortie = io.BytesIO()
        verifie(leve(fs.RefusFtp, b.s.zip, ["/d"], sortie), None, "zip de /d sans erreur")
        z = zipfile.ZipFile(sortie)
        verifie(sorted(z.namelist()), ["d/autoexec.be", "d/dedans.txt", "d/sous/profond.txt"], "contenu du zip = ce que /d contient")


def cas_supprime_recursif():
    """Suppression recursive d'un sous-dossier : le contenu de la racine reste intact."""
    with banc() as b:
        b.fichier("/d/ordinaire.bin", b"o")
        b.s.ouvre(CARTE, "flash")
        verifie(SECONDE in (leve(fs.RefusFtp, b.s.supprime, "/d", 1) or ""), True, "/d contient autoexec.be : 2 confirmations")
        verifie(leve(fs.RefusFtp, lambda: b.s.supprime("/d", 2, None, type_attendu="dossier")), None, "supprime /d avec 2 confirmations")
        verifie(sorted(p.name for p in b.srv.racine.iterdir()), ["racine.txt"], "seul /d a disparu, racine.txt est intact")


def cas_gestes_dans_un_sous_dossier():
    """Envoi (existe deja), type attendu, deplacement et protege dans /d : vus sur /d, pas sur la racine."""
    with banc() as b:
        b.s.ouvre(CARTE, "flash")
        msg = leve(fs.RefusFtp, b.s.envoie, "/d", "racine.txt", io.BytesIO(b"x"), False)
        verifie(msg, None, "racine.txt n'existe qu'a la racine : envoi dans /d accepte")
        msg = leve(fs.RefusFtp, b.s.envoie, "/d", "dedans.txt", io.BytesIO(b"x"), False)
        verifie(msg is not None and "existe deja" in msg, True, "dedans.txt existe dans /d : refus (%r)" % msg)
        verifie(leve(fs.RefusFtp, lambda: b.s.deplace("/d/dedans.txt", "/d/sous/dedans2.txt", None, type_attendu="fichier")), None,
                "deplace /d/dedans.txt avec type attendu « fichier »")
        verifie((b.srv.racine / "d/sous/dedans2.txt").exists(), True, "le fichier a bien ete deplace")
        msg = leve(fs.RefusFtp, lambda: b.s.supprime("/d/sous/profond.txt", 1, None, type_attendu="dossier"))
        verifie((msg or "").startswith("le type de l'element a change"), True, "type attendu faux dans un sous-dossier : refus (%r)" % msg)
        verifie(ecritures(b).count("DELE") + ecritures(b).count("RMD"), 0, "aucune suppression")


if __name__ == "__main__":
    for cas in (cas_liste_sous_dossier, cas_zip_dossier, cas_supprime_recursif, cas_gestes_dans_un_sous_dossier):
        print(f"-- {cas.__name__}")
        try:
            cas()
        except Exception as e:                                         # phase rouge : une signature absente ne doit pas cacher les autres cas
            verifie(repr(e), "pas d'exception", cas.__name__ + " leve")
    print("\nECHECS : " + (", ".join(ECHECS) if ECHECS else "aucun"))
    sys.exit(1 if ECHECS else 0)
