"""Banc voisin de test_ftp_cartes_session_garde.py : correctifs des relectures du 2026-11-22 (tache 12, plan A8). Code de sortie 0 = vert.

Extinction non confirmee retentee (C1), registre d'onglets garde au changement de carte (C4), `\\` refuse et noms FAT (C5), casse (C6),
dossier deplace dans lui-meme (C7), type attendu pour supprimer et deplacer (C8), seconde confirmation pour ecraser un fichier protege (C9).
Memes aides que les bancs de la session (faux serveur FTP, fausse commande HTTP, horloge simulee). Le faux serveur tourne sur le disque de
Windows, insensible a la casse et qui retire les points et espaces finaux comme une SD en FAT : les cas comparent les COMMANDES envoyees.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_ftp_cartes_session_relecture.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import io
import json
import sys

import faux_ftp_carte as faux
import ftp_cartes_session as fs
from test_ftp_cartes_session import CARTE, ECHECS, MDP, UFS_SD, Banc, leve, verifie
from test_ftp_cartes_session_garde import A, B, SECONDE, ecritures

AUTRE = dict(CARTE, adresse="localhost", env="autre")            # meme faux serveur, autre adresse
TYPE_CHANGE = "le type de l'element a change"


class CommandeRetive(faux.FausseCommande):
    """Carte qui ne confirme pas `UfsFTP 0` tant que `refus` > 0, avec un message qui cite le faux mot de passe (la session doit le masquer)."""

    def __init__(self, ufs, refus):
        super().__init__(ufs)
        self.refus = refus

    def __call__(self, ip, cmnd, delai):
        if cmnd == "UfsFTP 0" and self.refus > 0:
            self.journal.append((ip, cmnd))
            self.refus -= 1
            raise OSError("delai depasse (mot de passe %s)" % MDP)
        return super().__call__(ip, cmnd, delai)


def retive(b, refus):
    b.fc = b.s._commande = CommandeRetive(UFS_SD, refus)
    return b.fc


def zeros(b):
    return [ip for ip, n in b.fc.ufsftp() if n == 0]


def users(b):
    return sum(1 for c, _ in b.srv.commandes if c == "USER")


def cas_extinction_retentee():
    """C1 : UfsFTP 0 non confirme : la session ne l'oublie pas, tic() le renvoie, en_session() reste vrai jusqu'a la confirmation."""
    with Banc() as b:
        retive(b, 2)
        b.s.ouvre(CARTE, "flash")
        b.s.ferme("clic")
        e = b.s.etat()
        verifie(b.s.en_session(), True, "UfsFTP 0 non confirme : en_session() reste vrai (l'annuaire refuse l'arret)")
        verifie((e["etat"], "extinction" in e["message"].lower() and "non confirm" in e["message"]), ("erreur", True),
                "etat « erreur » (Deconnecter reste utilisable) et message « extinction non confirmee » (%r)" % e["message"])
        verifie(MDP in json.dumps(e), False, "message d'etat sans le mot de passe")
        n = users(b)
        verifie(leve(fs.RefusFtp, b.s.liste, "/") is not None, True, "extinction en attente : plus aucun geste")
        verifie(users(b), n, "extinction en attente : aucune reconnexion FTP")
        b.s.tic()
        verifie((zeros(b), b.s.en_session()), (["127.0.0.1"] * 2, True), "tic : UfsFTP 0 renvoye a la meme carte, toujours en session")
        b.s.tic()
        verifie((zeros(b), b.s.en_session(), b.s.etat()["etat"]), (["127.0.0.1"] * 3, False, "eteint"), "3e essai confirme : session eteinte")
        b.s.tic()
        verifie(len(zeros(b)), 3, "extinction confirmee : plus aucun essai")
    with Banc() as b:                                                   # borne des essais automatiques
        cmd = retive(b, 99)
        b.s.ouvre(CARTE, "flash")
        b.s.ferme("inactivite")
        for _ in range(10):
            b.s.tic()
        verifie((len(zeros(b)), b.s.en_session()), (fs.ESSAIS_EXTINCTION, True), "borne : %d essais automatiques, en_session() toujours vrai" % fs.ESSAIS_EXTINCTION)
        message = b.s.etat()["message"]
        verifie(("Deconnecter" in message, MDP in message), (True, False), "borne atteinte : message clair, sans secret (%r)" % message)
        b.s.ferme("clic")
        verifie(len(zeros(b)), fs.ESSAIS_EXTINCTION + 1, "Deconnecter retente au-dela de la borne")
        cmd.refus = 0
        b.s.ferme("clic")
        verifie((b.s.en_session(), b.s.etat()["etat"], b.s._mdp), (False, "eteint", ""), "extinction confirmee : tout est remis a zero")
    with Banc() as b:                                                   # rouvrir la meme carte efface l'attente
        retive(b, 1)
        b.s.ouvre(CARTE, "flash")
        b.s.ferme("clic")
        b.s.ouvre(CARTE, "flash")
        b.s.tic()
        verifie((b.s.etat()["etat"], [n for _, n in b.fc.ufsftp()]), ("actif", [2, 0, 2]), "meme carte rouverte : l'attente est effacee, un tic n'eteint pas la nouvelle session")
    with Banc() as b:                                                   # autre carte : l'ancienne est eteinte d'abord, sinon refus
        cmd = retive(b, 2)
        b.s.ouvre(CARTE, "flash")
        b.s.ferme("clic")
        msg = leve(fs.RefusFtp, b.s.ouvre, AUTRE, "flash")
        verifie(msg is not None and not msg.startswith("AUTRE") and MDP not in msg, True, "autre carte, ancienne non eteinte : refus lisible (%r)" % msg)
        verifie(b.fc.ufsftp(), [("127.0.0.1", 2), ("127.0.0.1", 0), ("127.0.0.1", 0)], "UfsFTP 0 retente a l'ancienne, rien d'allume sur la nouvelle")
        verifie(b.s.en_session(), True, "l'attente de l'ancienne carte est gardee")
        b.s.ouvre(AUTRE, "flash")
        verifie(b.fc.ufsftp()[-2:], [("127.0.0.1", 0), ("localhost", 2)], "ancienne eteinte (confirme) AVANT l'allumage de la nouvelle")
        verifie(b.s.etat()["etat"], "actif", "nouvelle carte ouverte")


def cas_changement_de_carte_onglets():
    """C4 : un changement de carte garde le registre d'onglets ; seuls Deconnecter et l'extinction reelle le vident."""
    with Banc() as b:
        b.s.ouvre_ou_reprend(CARTE, "flash", A)
        b.s.onglets.vu(B)
        b.s.ouvre_ou_reprend(AUTRE, "flash", A)                         # l'onglet A passe sur une autre carte
        b.s.ferme_onglet(A)
        verifie((b.s.etat()["etat"], b.fc.ufsftp()[-1]), ("actif", ("localhost", 2)), "A change de carte puis se ferme : B est toujours la, FTP allume")
        b.s.ferme_onglet(B)
        verifie((b.s.etat()["etat"], b.fc.ufsftp()[-1]), ("eteint", ("localhost", 0)), "B se ferme : dernier onglet, FTP eteint")
    with Banc() as b:
        b.s.ouvre_ou_reprend(CARTE, "flash", A)
        b.s.onglets.vu(B)
        b.s.ouvre_ou_reprend(AUTRE, "flash", A)
        b.s.ferme_onglet(None)                                          # Deconnecter : sans identifiant
        verifie((b.s.etat()["etat"], b.fc.ufsftp()[-1]), ("eteint", ("localhost", 0)), "Deconnecter ferme malgre B")


def cas_antislash():
    """C5 : `\\` refuse partout (FatFs peut le prendre pour un separateur et sortir du dossier)."""
    verifie(leve(ValueError, fs.valide_chemin, "/d\\x") is not None, True, "valide_chemin(/d\\x) : ValueError")
    with Banc() as b:
        b.fichier("/d/x", b"x")
        b.fichier("/d/y", b"y")
        b.s.ouvre(CARTE, "flash")
        n = len(b.srv.commandes)
        for nom, f in (("envoie (nom)", lambda: b.s.envoie("/", "d\\x", io.BytesIO(b"z"), True)),
                       ("envoie (dossier)", lambda: b.s.envoie("/d\\x", "n", io.BytesIO(b"z"), True)),
                       ("supprime", lambda: b.s.supprime("/d\\x", 2)), ("deplace (source)", lambda: b.s.deplace("/d\\y", "/z", confirmations=2)),
                       ("deplace (cible)", lambda: b.s.deplace("/d/y", "/d\\z", confirmations=2)),
                       ("cree_dossier", lambda: b.s.cree_dossier("/d\\n")), ("liste", lambda: b.s.liste("/d\\"))):
            msg = leve(ValueError, f)
            verifie(msg is not None and not msg.startswith("AUTRE"), True, "%s avec \\ : ValueError (%r)" % (nom, msg))
        verifie(len(b.srv.commandes), n, "aucune commande FTP envoyee")
        verifie(sorted(p.name for p in (b.srv.racine / "d").iterdir()), ["x", "y"], "rien n'a bouge sur la carte")


def cas_points_finaux():
    """C5 : protege() normalise comme FatFs (points et espaces finaux de chaque segment retires). Les alias 8.3 (AUTOEX~1.BE) ne sont PAS traites."""
    for p in ("/autoexec.be.", "/AUTOEXEC.BE ", "/autoexec.be. .", "/x/_persist.json ", "/a.bec.", "/.drvset003 ", "/sd.", "/json ", "/sd./"):
        verifie(fs.protege(p), True, "protege(%r) : nom FAT de fichier protege" % p)
    for p in ("/autoexec.be.txt", "/x/autoexec", "/sd./x.bin"):
        verifie(fs.protege(p), False, "protege(%r) : ordinaire" % p)
    with Banc() as b:
        b.fichier("/autoexec.be")
        b.s.ouvre(CARTE, "flash")
        for chemin in ("/autoexec.be.", "/AUTOEXEC.BE "):
            verifie(SECONDE in (leve(fs.RefusFtp, b.s.supprime, chemin, 1) or ""), True, "supprime(%r, 1) : seconde confirmation" % chemin)
            verifie(SECONDE in (leve(fs.RefusFtp, b.s.deplace, chemin, "/z.be") or ""), True, "deplace(%r) : seconde confirmation" % chemin)
        verifie(ecritures(b), [], "aucune commande de modification")


def cas_casse():
    """C6 : la SD est en FAT : AUTOEXEC.BE est autoexec.be (existence de envoie et de deplace)."""
    with Banc() as b:
        b.fichier("/autoexec.be", b"cfg")
        b.fichier("/a.txt", b"A")
        b.fichier("/Pris.txt", b"P")
        b.s.ouvre(CARTE, "flash")
        msg = leve(fs.RefusFtp, b.s.envoie, "/", "AUTOEXEC.BE", io.BytesIO(b"neuf"), False)
        verifie(msg is not None and "existe deja" in msg, True, "envoie AUTOEXEC.BE sans ecraser, autoexec.be present : « existe deja » (%r)" % msg)
        msg = leve(fs.RefusFtp, b.s.envoie, "/", "A.TXT.", io.BytesIO(b"neuf"), False)
        verifie(msg is not None and "existe deja" in msg, True, "envoie A.TXT. sans ecraser, a.txt present : « existe deja » (%r)" % msg)
        msg = leve(fs.RefusFtp, b.s.deplace, "/a.txt", "/PRIS.TXT")
        verifie(msg, "la cible existe deja", "deplace vers PRIS.TXT, Pris.txt present : la cible existe deja")
        verifie(ecritures(b), [], "aucun STOR, RNFR ni RNTO envoye")
        verifie([(b.srv.racine / n).read_bytes() for n in ("autoexec.be", "a.txt", "Pris.txt")], [b"cfg", b"A", b"P"], "rien d'ecrase")


def cas_dans_lui_meme():
    """C7 : un dossier ne se deplace pas dans lui-meme (ni sous lui-meme) : refus avant toute commande FTP."""
    with Banc() as b:
        b.fichier("/histo/a.bin")
        b.s.ouvre(CARTE, "flash")
        n = len(b.srv.commandes)
        for cible in ("/histo/histo", "/HISTO/sous/histo", "/histo", "/Histo"):
            msg = leve(fs.RefusFtp, lambda: b.s.deplace("/histo", cible, None, confirmations=2))
            verifie(msg is not None and not msg.startswith("AUTRE") and "lui-meme" in msg, True, "deplace(/histo, %s) : refus « lui-meme » (%r)" % (cible, msg))
        verifie(leve(fs.RefusFtp, lambda: b.s.deplace("/", "/x", None, confirmations=2)) is not None, True, "la racine ne se deplace pas")
        verifie(len(b.srv.commandes), n, "aucune commande FTP (ni RNFR ni RNTO)")
        verifie(leve(fs.RefusFtp, b.s.deplace, "/histo", "/histo2"), None, "un nom voisin (/histo2) n'est pas « dans lui-meme »")


def cas_type_attendu():
    """C8 : la page dit le type qu'elle a vu ; s'il a change (fichier devenu dossier, ou disparu), refus avant toute modification."""
    with Banc() as b:
        b.fichier("/x/plein.bin")                                     # la page avait vu « x » comme un fichier
        b.fichier("/f.bin")
        b.fichier("/g.bin")
        (b.srv.racine / "archives").mkdir()
        b.s.ouvre(CARTE, "flash")
        for nom, f in (("supprime", lambda: b.s.supprime("/x", 1, None, type_attendu="fichier")),
                       ("deplace", lambda: b.s.deplace("/x", "/archives/x", None, confirmations=2, type_attendu="fichier")),
                       ("supprime d'un absent", lambda: b.s.supprime("/absent.bin", 1, None, type_attendu="fichier")),
                       ("supprime, dossier attendu", lambda: b.s.supprime("/f.bin", 1, None, type_attendu="dossier"))):
            msg = leve(fs.RefusFtp, f)
            verifie((msg or "").startswith(TYPE_CHANGE) and SECONDE not in msg, True, "%s : type change, refus (%r)" % (nom, msg))
        verifie(ecritures(b), [], "aucune commande DELE, RMD, RNFR ni RNTO")
        verifie((b.srv.racine / "x/plein.bin").exists(), True, "le dossier devenu plein est intact")
        verifie(leve(ValueError, lambda: b.s.supprime("/f.bin", 1, None, type_attendu="lien")) is not None, True, "type inconnu : ValueError")
        verifie(leve(fs.RefusFtp, lambda: b.s.supprime("/f.bin", 1, None, type_attendu="fichier")), None, "type correct (fichier) : supprime")
        verifie(leve(fs.RefusFtp, lambda: b.s.deplace("/x", "/archives/x", None, confirmations=1, type_attendu="dossier")), None, "type correct (dossier) : deplace")
        verifie(leve(fs.RefusFtp, lambda: b.s.supprime("/g.bin", 1, None, type_attendu="")), None, "type vide : pas de controle")
        verifie(((b.srv.racine / "f.bin").exists(), (b.srv.racine / "archives/x/plein.bin").exists()), (False, True), "les gestes acceptes ont agi")


def cas_ecrase_protege():
    """C9 : ecraser un fichier protege par un envoi exige la seconde confirmation ; un fichier ordinaire ou absent, non."""
    with Banc() as b:
        b.fichier("/autoexec.be", b"cfg")
        b.fichier("/a.txt", b"A")
        (b.srv.racine / "json").mkdir()
        b.s.ouvre(CARTE, "flash")
        for n, libelle in ((1, "1 confirmation"), (0, "0 confirmation")):
            msg = leve(fs.RefusFtp, lambda: b.s.envoie("/", "autoexec.be", io.BytesIO(b"neuf"), True, None, confirmations=n))
            verifie((msg or "").startswith("ecrasement non confirme") and SECONDE in msg, True, "ecraser autoexec.be, %s : refus (%r)" % (libelle, msg))
        msg = leve(fs.RefusFtp, b.s.envoie, "/", "AUTOEXEC.BE", io.BytesIO(b"neuf"), True)
        verifie(SECONDE in (msg or ""), True, "ecraser AUTOEXEC.BE (casse), confirmations par defaut : refus")
        verifie((ecritures(b), (b.srv.racine / "autoexec.be").read_bytes()), ([], b"cfg"), "aucun STOR, autoexec.be intact")
        verifie(b.s.etat()["etat"], "actif", "le refus laisse la session ouverte")
        verifie(leve(fs.RefusFtp, lambda: b.s.envoie("/", "autoexec.be", io.BytesIO(b"neuf"), True, None, confirmations=2)), None, "2 confirmations : ecrase")
        verifie(((b.srv.racine / "autoexec.be").read_bytes(), ecritures(b)), (b"neuf", ["STOR"]), "un seul STOR")
        verifie(leve(fs.RefusFtp, b.s.envoie, "/", "a.txt", io.BytesIO(b"B"), True), None, "fichier ordinaire : une confirmation suffit")
        verifie(leve(fs.RefusFtp, b.s.envoie, "/json", "_persist.json", io.BytesIO(b"{}"), False), None, "nom protege absent : creation sans confirmation de plus")


if __name__ == "__main__":
    for cas in (cas_extinction_retentee, cas_changement_de_carte_onglets, cas_antislash, cas_points_finaux, cas_casse, cas_dans_lui_meme,
                cas_type_attendu, cas_ecrase_protege):
        print(f"-- {cas.__name__}")
        try:
            cas()
        except Exception as e:                                         # phase rouge : une signature absente ne doit pas cacher les autres cas
            verifie(repr(e), "pas d'exception", cas.__name__ + " leve")
    print("\nECHECS : " + (", ".join(ECHECS) if ECHECS else "aucun"))
    sys.exit(1 if ECHECS else 0)
