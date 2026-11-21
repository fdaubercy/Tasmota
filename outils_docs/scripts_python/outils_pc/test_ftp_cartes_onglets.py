"""Banc de ftp_cartes_onglets (registre des onglets du navigateur FTP des cartes). Code de sortie 0 = vert.

Horloge simulee, aucun sleep, aucun reseau.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_ftp_cartes_onglets.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import sys

import ftp_cartes_onglets as fo

ECHECS = []
A, B, C, D = "a" * 16, "b" * 16, "c" * 16, "d" * 16


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def registre(**k):
    t = [0.0]
    return fo.Onglets(horloge=lambda: t[0], **k), t


def cas_identifiants():
    for bon in ("0123456789abcdef", "0123456789abcdef0123456789abcdef"):
        verifie(fo.valide(bon), True, "identifiant valide : %d caracteres" % len(bon))
    for mauvais in ("0123456789abcde", "0123456789abcdef0123456789abcdef0", "0123456789ABCDEF", "0123456789abcdeg", "0123456789abcde\n",
                    "", None, 5, ["a" * 16], "../" + "a" * 16):
        verifie(fo.valide(mauvais), False, "identifiant invalide : %r" % (mauvais,))
    o, _ = registre()
    for mauvais in ("trop-court", None, 7, ["a" * 16], "A" * 16):
        o.vu(mauvais)
    verifie(o.perdu(), False, "un identifiant invalide n'est pas enregistre (jamais vu : pas perdu)")
    verifie(o.ferme(A), True, "registre vide : ferme(inconnu) rend True")


def cas_dernier_onglet():
    o, _ = registre()
    o.vu(A), o.vu(B)
    verifie(o.ferme(A), False, "deux onglets : le premier qui part, le registre n'est pas vide")
    verifie(o.ferme(B), True, "le dernier qui part : registre vide")
    o.vu(A), o.vu(B)
    verifie(o.ferme(C), False, "un identifiant inconnu ne vide rien")
    verifie(o.ferme("pas un identifiant"), False, "un identifiant invalide est ignore")
    verifie(o.ferme(A), False, "A part, B reste")
    verifie(o.ferme(A), False, "A part deux fois : B reste")
    verifie(o.ferme(B), True, "B part : vide")


def cas_silencieux():
    o, t = registre(delai=90)
    o.vu(A)
    t[0] = 90
    verifie(o.perdu(), False, "silencieux depuis exactement le delai : encore la")
    t[0] = 90.5
    verifie(o.perdu(), True, "silencieux depuis plus que le delai : elague, plus aucun onglet, perdu")
    o, t = registre(delai=90)
    o.vu(A), o.vu(B)
    t[0] = 60
    o.vu(B)
    t[0] = 100
    verifie(o.ferme(B), True, "ferme(B) elague A, silencieux depuis 100 s : registre vide")
    o, t = registre(delai=90)
    o.vu(A)
    t[0] = 80
    o.vu(A)
    t[0] = 160
    verifie(o.perdu(), False, "une nouvelle vue relance le delai")
    t[0] = 171
    verifie(o.perdu(), True, "91 s apres la derniere vue : perdu")


def cas_perdu():
    o, t = registre()
    verifie(o.perdu(), False, "aucun onglet jamais vu : pas perdu (session sans identifiant)")
    t[0] = 10000
    verifie(o.perdu(), False, "toujours pas perdu, meme longtemps apres")
    o.vu(A)
    verifie(o.perdu(), False, "un onglet vu : pas perdu")
    o.ferme(A)
    verifie(o.perdu(), True, "le dernier onglet parti : perdu")
    o.reinitialise()
    verifie(o.perdu(), False, "reinitialise : plus rien de vu")
    o.vu(B)
    t[0] += 91
    verifie(o.perdu(), True, "apres reinitialise, un nouvel onglet silencieux : perdu")
    o.reinitialise()
    verifie(o.ferme(B), True, "reinitialise vide le registre")


def cas_maximum():
    o, _ = registre(maximum=3)
    for i in (A, B, C, D):
        o.vu(i)
    verifie(o.ferme(B), False, "maximum 3 : B reste")
    verifie(o.ferme(C), False, "C reste")
    verifie(o.ferme(D), True, "D reste puis part : A, le plus ancien, a ete oublie")
    o, _ = registre(maximum=3)
    for i in (A, B, C, A, D):
        o.vu(i)
    verifie([o.ferme(C), o.ferme(A), o.ferme(D)], [False, False, True],
            "une nouvelle vue rajeunit l'onglet : B, devenu le plus ancien, est oublie")
    o, _ = registre()
    for n in range(40):
        o.vu("%016x" % n)
    res = [o.ferme("%016x" % n) for n in range(39, -1, -1)]          # du plus recent au plus ancien
    verifie(res.index(True), 31, "maximum par defaut 32 : le registre se vide a la 32e fermeture")


if __name__ == "__main__":
    for cas in (cas_identifiants, cas_dernier_onglet, cas_silencieux, cas_perdu, cas_maximum):
        print("--", cas.__name__)
        cas()
    print("\nECHECS : " + (", ".join(ECHECS) if ECHECS else "aucun"))
    sys.exit(1 if ECHECS else 0)
