"""Banc voisin de test_ftp_cartes_session.py (celui-ci approche les 500 lignes) : les garde-fous de la tache 7 (A8).

Seconde confirmation du deplacement d'un fichier protege, dossier contenant un fichier protege (suppression ET deplacement),
cible deja existante, `ouvre` sure sur exception, `noms_ignores` borne, paire env/support de `lit`, registre d'onglets branche
sur la session. Reprend les aides du banc de la session (faux serveur FTP, fausse commande HTTP, horloge simulee). Code de sortie 0 = vert.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_ftp_cartes_session_garde.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import ftplib
import io
import sys
import threading
import time

import faux_ftp_carte as faux
import ftp_cartes_session as fs
from test_ftp_cartes_session import CARTE, ECHECS, MDP, UFS_FLASH, Banc, leve, verifie

A, B = "a" * 16, "b" * 16
SECONDE = "seconde confirmation"


def ecritures(b):
    """Commandes FTP de modification recues par le faux serveur."""
    return [c for c, _ in b.srv.commandes if c in ("RNFR", "RNTO", "DELE", "RMD", "MKD", "STOR")]


def deplace(b, source, cible, confirmations):
    return leve(fs.RefusFtp, lambda: b.s.deplace(source, cible, None, confirmations=confirmations))


def cas_deplace_protege():
    with Banc() as b:
        b.fichier("/autoexec.be", b"cfg")
        b.fichier("/x.txt")
        b.fichier("/y.txt")
        b.fichier("/dossier/_persist.json")
        (b.srv.racine / "archives").mkdir()
        b.s.ouvre(CARTE, "flash")
        msg = leve(fs.RefusFtp, b.s.deplace, "/autoexec.be", "/archives/autoexec.be")
        verifie(SECONDE in (msg or "") and not (msg or "").startswith("AUTRE"), True, "source protegee, confirmations par defaut : « seconde confirmation » (%r)" % msg)
        verifie(SECONDE in (deplace(b, "/autoexec.be", "/archives/autoexec.be", 1) or ""), True, "source protegee, 1 confirmation : refuse")
        verifie(ecritures(b), [], "refus AVANT toute commande de modification")
        verifie((b.srv.racine / "autoexec.be").exists(), True, "autoexec.be intact")
        verifie((b.s.etat()["etat"], [n for _, n in b.fc.ufsftp()]), ("actif", [2]), "le refus ne ferme pas la session")
        verifie(deplace(b, "/autoexec.be", "/archives/autoexec.be", 2), None, "source protegee, 2 confirmations : deplace")
        verifie([(b.srv.racine / "archives/autoexec.be").read_bytes(), (b.srv.racine / "autoexec.be").exists()], [b"cfg", False], "autoexec.be est parti")
        verifie(SECONDE in (deplace(b, "/x.txt", "/archives/_persist.json", 1) or ""), True, "cible protegee (nom a creer), 1 confirmation : refuse")
        verifie((b.srv.racine / "x.txt").exists(), True, "x.txt intact")
        verifie(deplace(b, "/x.txt", "/archives/_persist.json", 2), None, "cible protegee, 2 confirmations : deplace")
        verifie(SECONDE in (deplace(b, "/dossier", "/archives/dossier", 1) or ""), True, "dossier contenant _persist.json, 1 confirmation : refuse")
        verifie((b.srv.racine / "dossier/_persist.json").exists(), True, "dossier intact")
        verifie(deplace(b, "/dossier", "/archives/dossier", 2), None, "dossier contenant un fichier protege, 2 confirmations : deplace")
        verifie((b.srv.racine / "archives/dossier/_persist.json").exists(), True, "le dossier est arrive")
        verifie(deplace(b, "/y.txt", "/archives/y.txt", 1), None, "deplacement ordinaire : aucune confirmation exigee")
        verifie(deplace(b, "/archives/y.txt", "/y2.txt", 0), None, "deplacement ordinaire : meme avec 0")
        verifie(leve(TypeError, b.s.deplace, "/archives/y2.txt", "/z", None, 2) is not None, True, "confirmations est un mot-cle (pas un argument positionnel)")


def cas_deplace_cible_existante():
    with Banc() as b:
        b.fichier("/a.bin", b"A")
        b.fichier("/b.bin", b"B")
        b.fichier("/d/x")
        (b.srv.racine / "e").mkdir()
        b.s.ouvre(CARTE, "flash")
        for cible, nom in (("/b.bin", "fichier"), ("/d", "dossier")):
            msg = leve(fs.RefusFtp, b.s.deplace, "/a.bin", cible)
            verifie(msg, "la cible existe deja", "cible existante (%s) : RefusFtp lisible" % nom)
        verifie(deplace(b, "/a.bin", "/b.bin", 2), "la cible existe deja", "meme avec deux confirmations")
        verifie(deplace(b, "/e", "/d", 1), "la cible existe deja", "dossier sur dossier : refuse")
        verifie(ecritures(b), [], "aucun RNFR ni RNTO envoye")
        verifie([(b.srv.racine / "a.bin").read_bytes(), (b.srv.racine / "b.bin").read_bytes()], [b"A", b"B"], "aucun fichier ecrase")
        verifie(b.s.etat()["etat"], "actif", "session intacte")
        verifie(leve(fs.RefusFtp, b.s.deplace, "/a.bin", "/c.bin"), None, "cible libre : deplace")


def cas_supprime_dossier_protege():
    with Banc() as b:
        b.fichier("/dossier/autoexec.be")
        b.fichier("/profond/a/b/c/_persist.json")
        b.fichier("/banal/a.bin")
        b.fichier("/banal/sous/b.bin")
        b.fichier("/drv/.drvset003")
        b.s.ouvre(CARTE, "flash")
        for dossier in ("/dossier", "/profond", "/drv"):
            msg = leve(fs.RefusFtp, b.s.supprime, dossier, 1)
            verifie(SECONDE in (msg or "") and not (msg or "").startswith("AUTRE"), True, "supprime(%s, 1) : seconde confirmation (%r)" % (dossier, msg))
        verifie(ecritures(b), [], "refus AVANT toute commande de modification")
        verifie((b.srv.racine / "dossier/autoexec.be").exists(), True, "le dossier est intact")
        verifie((b.s.etat()["etat"], [n for _, n in b.fc.ufsftp()]), ("actif", [2]), "le refus traverse _op : session ouverte, pas d'UfsFTP 0")
        verifie([x["nom"] for x in b.s.liste("/")], ["banal", "dossier", "drv", "profond"], "la session sert encore apres le refus")
        b.s.supprime("/banal", 1)
        verifie((b.srv.racine / "banal").exists(), False, "dossier sans fichier protege : 1 confirmation suffit")
        b.s.supprime("/dossier", 2)
        verifie((b.srv.racine / "dossier").exists(), False, "dossier avec fichier protege, 2 confirmations : supprime")
        b.s.supprime("/profond", 2)
        verifie((b.srv.racine / "profond").exists(), False, "fichier protege a 4 niveaux, 2 confirmations : supprime")


def cas_parcours_borne():
    """Le parcours rend True a la limite (fail-safe) : plus de 500 entrees ou plus de 6 niveaux."""
    def contient(b, chemin):
        return b.s._op(lambda ftp: b.s._contient_protege(ftp, chemin))

    with Banc() as b:
        for i in range(500):
            b.fichier("/cinq/f%03d.bin" % i, b"")
        for i in range(501):
            b.fichier("/six/f%03d.bin" % i, b"")
        (b.srv.racine / "niveaux/a/b/c/d/e").mkdir(parents=True)                 # 6 niveaux : niveaux, a, b, c, d, e
        (b.srv.racine / "trop/a/b/c/d/e/f").mkdir(parents=True)                  # 7 niveaux
        b.fichier("/protege-tard/a/b/c/d/e/autoexec.be")                         # au 6e niveau, trouve avant la limite
        b.s.ouvre(CARTE, "flash")
        verifie(contient(b, "/cinq"), False, "500 entrees sans fichier protege : False (limite non atteinte)")
        verifie(contient(b, "/six"), True, "501 entrees : limite atteinte, True (fail-safe)")
        verifie(contient(b, "/niveaux"), False, "6 niveaux sans fichier protege : False")
        verifie(contient(b, "/trop"), True, "7 niveaux : limite atteinte, True (fail-safe)")
        verifie(contient(b, "/protege-tard"), True, "fichier protege au 6e niveau : True")
        msg = leve(fs.RefusFtp, b.s.supprime, "/six", 1)
        verifie(SECONDE in (msg or ""), True, "supprime d'un dossier de 501 entrees : deux confirmations")


def cas_ouvre_exception():
    def casse(fw):
        raise RuntimeError("identifiants illisibles " + MDP)

    class FtpBizarre(ftplib.FTP):
        def connect(self, *a, **k):
            raise ValueError("pas une erreur reseau")

    with Banc() as b:                           # changement de support : la session flash est allumee quand identifiants() leve
        b.s.ouvre(CARTE, "flash")
        b.s._identifiants = casse
        msg = leve(RuntimeError, b.s.ouvre, CARTE, "sd")
        verifie(msg, "ouverture impossible : RuntimeError", "l'exception est relevee par son TYPE seul (jamais son message, qui peut citer un secret)")
        verifie([n for _, n in b.fc.ufsftp()], [2, 0], "UfsFTP 0 envoye apres l'exception")
        e = b.s.etat()
        verifie((e["etat"], MDP in repr(e)), ("erreur", False), "etat « erreur », sans le mot de passe")
        verifie(leve(fs.RefusFtp, b.s.liste, "/") is not None, True, "plus de session ouverte")
        verifie(b.s._allume, False, "la session sait que le FTP est eteint")
    with Banc() as b:                           # premiere ouverture : rien n'a ete allume, l'etat ne reste pas « allumage »
        b.s._identifiants = casse
        verifie(leve(RuntimeError, b.s.ouvre, CARTE, "flash"), "ouverture impossible : RuntimeError", "premiere ouverture : l'exception remonte, type seul")
        verifie((b.fc.ufsftp(), b.s.etat()["etat"]), ([], "erreur"), "rien d'allume, etat coherent (ni « allumage » ni « actif »)")
        b.s._identifiants = lambda fw: ("u", MDP)
        b.s.ouvre(CARTE, "flash")
        verifie(b.s.etat()["etat"], "actif", "une nouvelle ouverture marche")
    with Banc(fabrique_ftp=FtpBizarre) as b:    # exception hors reseau apres UfsFTP 1 : ancien comportement = FTP allume jusqu'au tic()
        verifie(leve(RuntimeError, b.s.ouvre, CARTE, "flash"), "ouverture impossible : ValueError", "exception de la fabrique FTP : remontee, type seul")
        verifie([n for _, n in b.fc.ufsftp()], [2, 0], "UfsFTP 0 envoye apres UfsFTP 2")
        verifie(b.s.etat()["etat"], "erreur", "etat « erreur »")


class FtpLeve(ftplib.FTP):
    """Fabrique dont une etape leve une exception NON reseau dont le MESSAGE cite le faux mot de passe."""
    etape, exception = "connect", ValueError

    def connect(self, *a, **k):
        if self.etape == "connect":
            raise self.exception("secret " + MDP)
        return super().connect(*a, **k)

    def login(self, *a, **k):
        if self.etape == "login":
            raise self.exception(MDP)
        return super().login(*a, **k)

    def mlsd(self, *a, **k):
        if self.etape == "mlsd":
            raise self.exception("secret " + MDP)
        return super().mlsd(*a, **k)


def fabrique(etape, exception=ValueError):
    return type("FtpLeve_" + etape, (FtpLeve,), {"etape": etape, "exception": exception})


def cas_secret_dans_exception():
    """Aucune exception relevee par ouvre ou par une operation ne porte le message d'une exception interne (il pourrait citer le mot de passe)."""
    def jamais(fw):
        raise ValueError("secret " + MDP)

    def tipe(fw):
        raise TypeError(MDP)

    for nom, session, attendu in (("identifiants ValueError", dict(identifiants=jamais), "ValueError"),
                                  ("identifiants TypeError", dict(identifiants=tipe), "TypeError"),
                                  ("fabrique connect ValueError", dict(fabrique_ftp=fabrique("connect")), "ValueError"),
                                  ("fabrique login TypeError", dict(fabrique_ftp=fabrique("login", TypeError)), "TypeError")):
        with Banc(**session) as b:
            msg = leve(RuntimeError, b.s.ouvre, CARTE, "flash")
            verifie(msg, "ouverture impossible : " + attendu, "ouvre, %s : RuntimeError au type seul" % nom)
            verifie(MDP in repr(b.s.etat()) + (msg or ""), False, "ouvre, %s : ni message ni etat() ne citent le mot de passe" % nom)
            verifie((b.s.etat()["etat"], [n for _, n in b.fc.ufsftp()][-1:] in ([], [0])), ("erreur", True), "ouvre, %s : session fermee, UfsFTP 0 si allume" % nom)
    for nom, etape, exc in (("reconnexion ValueError", "connect", ValueError), ("mlsd ValueError", "mlsd", ValueError), ("mlsd TypeError", "mlsd", TypeError)):
        with Banc() as b:                                              # une session saine, puis la carte coupe le client et l'etape leve
            b.s.ouvre(CARTE, "flash")
            b.s._fabrique = fabrique(etape, exc)
            if etape == "connect":
                b.srv.coupe_client()                                   # le NOOP echoue : _op rouvre par _connecte
            else:                                                      # la fabrique ne sert qu'a rouvrir : on force une nouvelle session
                b.s._quitte_ftp()
                b.s._connecte()
            msg = leve(RuntimeError, b.s.liste, "/")
            verifie((msg or "").startswith("operation impossible : ") and MDP not in (msg or ""), True,
                    "liste, %s : exception relevee par son type seul (%r)" % (nom, msg))
            verifie(MDP in repr(b.s.etat()), False, "liste, %s : etat() sans mot de passe" % nom)
            verifie(b.s.etat()["etat"] in ("actif", "erreur"), True, "liste, %s : etat coherent" % nom)


def cas_protege_casse():
    """La SD est en FAT : AUTOEXEC.BE est autoexec.be, /SD est /sd."""
    for p in ("/AUTOEXEC.BE", "/Autoexec.Bat", "/_PERSIST.JSON", "/x/Y.BEC", "/.DRVSET003", "/SD", "/Json", "/sd/", "/Sd/"):
        verifie(fs.protege(p), True, "protege(%s) : insensible a la casse" % p)
    for p in ("/histo/X.BIN", "/SD/x.bin", "/autoexec.be.txt"):
        verifie(fs.protege(p), False, "protege(%s) : ordinaire" % p)
    with Banc() as b:
        b.fichier("/AUTOEXEC.BE")
        (b.srv.racine / "archives").mkdir()
        b.s.ouvre(CARTE, "flash")
        verifie(SECONDE in (leve(fs.RefusFtp, b.s.supprime, "/AUTOEXEC.BE", 1) or ""), True, "supprime(/AUTOEXEC.BE, 1) : seconde confirmation")
        verifie(SECONDE in (deplace(b, "/AUTOEXEC.BE", "/archives/a.be", 1) or ""), True, "deplace(/AUTOEXEC.BE, 1) : seconde confirmation")
        verifie((b.srv.racine / "AUTOEXEC.BE").exists(), True, "intact")


def cas_faux_perdre_course():
    """Le faux serveur : arrete() ne joint jamais un fil pas encore demarre, meme si perdre() tarde a le demarrer (course reelle, intermittente)."""
    class Lent(threading.Thread):
        def start(self):
            time.sleep(0.4)
            super().start()

    class Shim:
        Thread, Semaphore, Lock, Event = Lent, threading.Semaphore, threading.Lock, threading.Event

    srv = faux.FauxFtpCarte()
    vrai, faux.threading = faux.threading, Shim
    try:
        erreur = []
        t = threading.Thread(target=srv.perdre)
        t.start()
        time.sleep(0.1)                                                # perdre() est dans le start() lent
        try:
            srv.arrete()
        except Exception as e:
            erreur.append(repr(e))
        t.join(5)
    finally:
        faux.threading = vrai
    verifie(erreur, [], "arrete() pendant un perdre() lent : aucune exception (RuntimeError cannot join thread before it is started)")


def cas_noms_ignores_borne():
    with Banc(noms_pieges=["../x%03d" % i for i in range(150)]) as b:
        b.s.ouvre(CARTE, "flash")
        b.s.liste("/")
        verifie(isinstance(b.s.noms_ignores, list), True, "noms_ignores reste une liste")
        verifie((len(b.s.noms_ignores), b.s.noms_ignores[0], b.s.noms_ignores[-1]), (100, "../x050", "../x149"), "les 100 dernieres entrees seulement")
        for _ in range(5):
            b.s.liste("/")
        verifie(len(b.s.noms_ignores), 100, "toujours 100 apres d'autres listes")
    with Banc(noms_pieges=["../x"]) as b:
        b.s.ouvre(CARTE, "flash")
        for _ in range(4):
            b.s.liste("/")
        verifie(b.s.noms_ignores, ["../x"], "un meme nom rendu a chaque liste n'est consigne qu'une fois de suite")
    with Banc(noms_pieges=["../x"], sans_mlsd=True) as b:     # repli LIST : meme garde-fou
        b.s.ouvre(CARTE, "flash")
        for _ in range(4):
            b.s.liste("/")
        verifie(b.s.noms_ignores, ["../x"], "repli LIST : meme regle")


def cas_lit_attendu():
    with Banc() as b:
        b.fichier("/a.bin", b"contenu")
        b.s.ouvre(CARTE, "sd")
        n = len(b.srv.commandes)
        sortie = io.BytesIO()
        msg = leve(fs.RefusFtp, b.s.lit, "/a.bin", sortie, ("essai", "flash"))
        verifie(msg, "la session a change (carte ou support)", "lit : support different, refuse")
        verifie(leve(fs.RefusFtp, b.s.lit, "/a.bin", sortie, ("autre", "sd")), "la session a change (carte ou support)", "lit : carte differente, refuse")
        verifie((len(b.srv.commandes), sortie.getvalue()), (n, b""), "aucune commande FTP envoyee, rien ecrit")
        b.s.lit("/a.bin", sortie, ("essai", "sd"))
        verifie(sortie.getvalue(), b"contenu", "paire conforme : lu")
        sortie = io.BytesIO()
        b.s.lit("/a.bin", sortie)
        b.s.lit("/a.bin", sortie, (None, ""))
        verifie(sortie.getvalue(), b"contenu" * 2, "sans paire ou paire indifferente : comme avant")


def cas_onglets_session():
    with Banc() as b:                           # deux onglets : le FTP s'eteint au dernier
        b.s.ouvre_ou_reprend(CARTE, "flash", A)
        b.s.onglets.vu(B)
        b.s.ferme_onglet(A)
        verifie((b.s.etat()["etat"], [n for _, n in b.fc.ufsftp()]), ("actif", [2]), "un onglet part, l'autre reste : FTP allume")
        b.s.ferme_onglet(B)
        verifie((b.s.etat()["etat"], [n for _, n in b.fc.ufsftp()], b.s.derniere_raison), ("eteint", [2, 0], "page fermee"), "le dernier part : UfsFTP 0")
    with Banc() as b:                           # onglet silencieux elague par tic()
        b.s.ouvre_ou_reprend(CARTE, "flash", A)
        b.s.onglets.vu(B)
        b.t[0] = 60
        b.s.onglets.vu(B)
        b.t[0] = 100
        b.s.tic()
        verifie(b.s.etat()["etat"], "actif", "A silencieux depuis 100 s, B vu a 60 s : la session reste")
        b.t[0] = 150
        b.s.tic()
        verifie(b.s.etat()["etat"], "actif", "B silencieux depuis 90 s exactement : la session reste")
        b.t[0] = 151
        b.s.tic()
        verifie((b.s.etat()["etat"], [n for _, n in b.fc.ufsftp()], b.s.derniere_raison), ("eteint", [2, 0], "onglet perdu"), "plus aucun onglet : UfsFTP 0, raison « onglet perdu »")
    with Banc() as b:                           # session sans identifiant : seule l'inactivite la ferme
        b.s.ouvre_ou_reprend(CARTE, "flash")
        b.t[0] = 500
        b.s.tic()
        verifie(b.s.etat()["etat"], "actif", "sans identifiant : pas d'onglet perdu")
        b.s.ferme_onglet(None)
        verifie((b.s.etat()["etat"], b.s.derniere_raison), ("eteint", "page fermee"), "ferme_onglet sans identifiant : ferme comme avant")
        b.s.ouvre_ou_reprend(CARTE, "flash", A)
        b.s.ferme_onglet("pas un identifiant")
        verifie(b.s.etat()["etat"], "eteint", "identifiant invalide : ferme comme avant")
    with Banc() as b:                           # un identifiant invalide n'enregistre rien
        b.s.ouvre_ou_reprend(CARTE, "flash", "invalide")
        b.t[0] = 500
        b.s.tic()
        verifie(b.s.etat()["etat"], "actif", "identifiant invalide a l'ouverture : ignore")
    with Banc() as b:                           # Deconnecter et changement de carte ferment sans regarder les onglets
        b.s.ouvre_ou_reprend(CARTE, "flash", A)
        b.s.onglets.vu(B)
        b.s.ferme("clic")
        verifie(b.s.etat()["etat"], "eteint", "Deconnecter ferme malgre un autre onglet")
        b.s.ouvre_ou_reprend(CARTE, "flash")                # session suivante ouverte sans identifiant : les onglets d'avant ne comptent plus
        b.t[0] = 500
        b.s.tic()
        verifie(b.s.etat()["etat"], "actif", "ferme() reinitialise le registre : pas d'onglet perdu fantome")
        b.s.ouvre_ou_reprend(CARTE, "flash", A)
        b.s.ouvre_ou_reprend(dict(CARTE, adresse="localhost", env="autre"), "flash", A)
        verifie([c for _, c in b.fc.journal if c.startswith("UfsFTP")], ["UfsFTP 2", "UfsFTP 0", "UfsFTP 2", "UfsFTP 0", "UfsFTP 2"],
                "changement de carte : ferme l'ancienne, ouvre la nouvelle")
        b.s.ferme_onglet(A)
        verifie(b.s.etat()["etat"], "eteint", "l'onglet qui a change de carte est enregistre sur la nouvelle session")
    with Banc() as b:                           # le sondage n'est pas une action : l'inactivite ferme quand meme
        b.s.ouvre_ou_reprend(CARTE, "flash", A)
        b.t[0] = 899
        b.s.onglets.vu(A)
        b.t[0] = 901
        b.s.tic()
        verifie((b.s.etat()["etat"], b.s.derniere_raison), ("eteint", "inactivite"), "un sondage d'onglet ne repousse pas les 15 min")
    with Banc() as b:                           # reprise : le second onglet s'enregistre sans reconnexion
        b.s.ouvre_ou_reprend(CARTE, "flash", A)
        b.s.ouvre_ou_reprend(CARTE, "flash", B)
        verifie([n for _, n in b.fc.ufsftp()], [2], "second onglet sur la meme session : pas de second UfsFTP")
        b.s.ferme_onglet(A)
        verifie(b.s.etat()["etat"], "actif", "le second onglet enregistre par la reprise garde le FTP allume")
    with Banc(UFS_FLASH) as b:                  # une ouverture refusee n'enregistre pas l'onglet
        verifie(leve(fs.RefusFtp, b.s.ouvre_ou_reprend, CARTE, "sd", A) is not None, True, "SD absente : refus")
        b.t[0] = 500
        b.s.tic()
        verifie(b.s.etat()["etat"], "eteint", "rien d'ouvert, rien a elaguer")


if __name__ == "__main__":
    for cas in (cas_deplace_protege, cas_deplace_cible_existante, cas_supprime_dossier_protege, cas_parcours_borne, cas_ouvre_exception,
                cas_secret_dans_exception, cas_protege_casse, cas_faux_perdre_course, cas_noms_ignores_borne, cas_lit_attendu, cas_onglets_session):
        print(f"-- {cas.__name__}")
        cas()
    print("\nECHECS : " + (", ".join(ECHECS) if ECHECS else "aucun"))
    sys.exit(1 if ECHECS else 0)
