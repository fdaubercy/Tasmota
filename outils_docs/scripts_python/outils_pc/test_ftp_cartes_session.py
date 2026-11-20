"""Banc de ftp_cartes_session (session FTP d'une carte, allumage par HTTP). Code de sortie 0 = vert.

Faux serveur FTP sur 127.0.0.1 et fausse commande HTTP (`faux_ftp_carte.py`) : aucun reseau reel, aucune carte,
identifiants factices injectes par le parametre `identifiants`, horloge injectee pour l'inactivite.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_ftp_cartes_session.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import ftplib
import io
import json
import sys
import threading
import zipfile

import faux_ftp_carte as faux
import ftp_cartes_session as fs

ECHECS = []
MDP = "faux-mdp-de-banc-456"
UFS_SD = '{"Ufs":{"Type":1,"Size":1000,"Free":500},{"Type":3,"Size":100,"Free":50}}'
UFS_FLASH = '{"Ufs":{"Type":3,"Size":100,"Free":50}}'
CARTE = {"env": "essai", "lieu": "garage", "nom": "essai", "hote": "essai", "adresse": "127.0.0.1",
         "puce": "ESP32-P4", "firmware": "FIRMWARE_ESSAI"}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def leve(exc, f, *a):
    try:
        f(*a)
    except exc as e:
        return str(e)
    except Exception as e:                      # autre exception : le cas est rouge
        return "AUTRE " + repr(e)
    return None


class FtpQuitCasse(ftplib.FTP):
    def quit(self):
        raise OSError("quit casse")


class Banc:
    """Un faux serveur, une fausse commande, une session branchee dessus."""

    def __init__(self, ufs=UFS_SD, sans_mlsd=False, noms_pieges=(), echoue_sur=(), **session):
        self.t = [0.0]
        self.srv = faux.FauxFtpCarte(identifiants=("u", MDP), sans_mlsd=sans_mlsd, noms_pieges=noms_pieges)
        self.fc = faux.FausseCommande(ufs, echoue_sur)
        opts = dict(commande=self.fc, horloge=lambda: self.t[0], port=self.srv.port, delai_allumage=1,
                    identifiants=lambda fw: ("u", MDP))
        opts.update(session)
        self.s = fs.Session(**opts)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.s.ferme("fin du banc")
        self.srv.arrete()

    def fichier(self, chemin, contenu=b"abc"):
        p = self.srv.racine / chemin.lstrip("/")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(contenu)
        return p


def cas_ouvre():
    with Banc() as b:
        b.s.ouvre(CARTE, "sd")
        verifie([n for _, n in b.fc.ufsftp()], [1], "ouvre sd envoie UfsFTP 1")
        verifie(b.s.etat()["etat"], "actif", "etat actif")
        verifie(b.s.etat()["sd"], True, "SD detectee (premier objet de type 1)")
        b.s.ouvre(CARTE, "flash")
        verifie([n for _, n in b.fc.ufsftp()], [1, 2], "ouvre flash envoie UfsFTP 2 (sans UfsFTP 0 pour la meme carte)")
        verifie(b.s.etat()["support"], "flash", "support flash")
    with Banc(UFS_FLASH) as b:
        verifie(b.s.ouvre(CARTE, "flash")["sd"], False, "une seule paire de type 3 : pas de SD")
        verifie(leve(fs.RefusFtp, b.s.ouvre, CARTE, "sd") is not None, True, "sd refusee sans SD")
        verifie(b.fc.ufsftp(), [(CARTE["adresse"], 2), (CARTE["adresse"], 0)], "aucun UfsFTP 1 pour la SD refusee, flash eteinte")


def cas_sd_inconnue():
    with Banc(None) as b:
        verifie(b.s.etat()["sd"], None, "avant tout : sd inconnue")
        msg = leve(fs.RefusFtp, b.s.ouvre, CARTE, "sd")
        verifie(msg is not None and not msg.startswith("AUTRE"), True, "ouvre sd sans reponse Ufs : RefusFtp")
        verifie(b.s.etat()["sd"], None, "sd reste None apres le refus")
        verifie(b.fc.ufsftp(), [], "rien n'est allume (jamais la flash sous l'etiquette SD)")
        b.s.ouvre(CARTE, "flash")
        verifie(b.s.etat()["etat"], "actif", "la flash reste accessible")


def cas_ferme_toujours():
    with Banc(fabrique_ftp=FtpQuitCasse) as b:
        b.s.ouvre(CARTE, "flash")
        b.s.ferme("clic")
        verifie(b.fc.ufsftp(), [("127.0.0.1", 2), ("127.0.0.1", 0)], "UfsFTP 0 envoye malgre un quit qui leve")
        verifie(b.s.etat()["etat"], "eteint", "etat eteint apres ferme")
    with Banc() as b:
        b.s.ouvre(CARTE, "flash")
        b.s.ouvre(dict(CARTE, adresse="localhost", env="autre"), "flash")
        verifie(b.fc.ufsftp(), [("127.0.0.1", 2), ("127.0.0.1", 0), ("localhost", 2)],
                "changement de carte : UfsFTP 0 a l'ancienne AVANT UfsFTP 2 a la nouvelle")
    with Banc() as b:                           # FTP allume mais session FTP impossible : eteint quand meme
        b.srv.perdre()
        msg = leve(fs.RefusFtp, b.s.ouvre, CARTE, "flash")
        verifie(msg is not None and not msg.startswith("AUTRE"), True, "carte muette : RefusFtp")
        verifie(b.fc.ufsftp(), [("127.0.0.1", 2), ("127.0.0.1", 0)], "allume sans session FTP : UfsFTP 0 envoye")


def cas_inactivite():
    with Banc() as b:
        b.s.ouvre(CARTE, "flash")
        b.t[0] = 899
        b.s.tic()
        verifie(b.s.etat()["etat"], "actif", "899 s : pas de fermeture")
        b.s.liste("/")                          # une action remet le compteur a zero
        b.t[0] = 899 + 899
        b.s.tic()
        verifie(b.s.etat()["etat"], "actif", "une action relance les 900 s")
        b.t[0] = 899 + 901
        b.s.tic()
        verifie(b.s.etat()["etat"], "eteint", "901 s apres la derniere action : fermee")
        verifie(b.fc.ufsftp()[-1], ("127.0.0.1", 0), "UfsFTP 0 envoye")
        verifie(b.s.derniere_raison, "inactivite", "raison inactivite")


def cas_reconnexion():
    with Banc() as b:
        b.fichier("/a.txt")
        b.s.ouvre(CARTE, "flash")
        b.srv.coupe_client()                    # timeout de 5 min de la carte
        verifie([x["nom"] for x in b.s.liste("/")], ["a.txt"], "liste reussit apres la coupure du client")
        verifie([n for _, n in b.fc.ufsftp()], [2], "aucun UfsFTP supplementaire")
        verifie(b.s.etat()["etat"], "actif", "toujours actif")


def cas_carte_perdue():
    with Banc() as b:
        b.s.ouvre(CARTE, "flash")
        b.srv.coupe_apres(1)                    # une commande (le NOOP de controle), puis plus rien
        msg = leve(fs.RefusFtp, b.s.liste, "/")
        verifie(msg is not None and not msg.startswith("AUTRE") and len(msg) > 5, True, "RefusFtp lisible : %r" % msg)
        verifie(b.s.etat()["etat"], "erreur", "etat erreur")
        verifie(len(b.s.etat()["message"]) > 5, True, "message d'etat lisible")
    with Banc() as b:
        b.s.ouvre(CARTE, "flash")
        b.srv.perdre()                          # reconnexion impossible
        msg = leve(fs.RefusFtp, b.s.liste, "/")
        verifie(msg is not None and not msg.startswith("AUTRE"), True, "carte perdue : RefusFtp")
        verifie(b.s.etat()["etat"], "erreur", "etat erreur (reconnexion impossible)")


def cas_chemins():
    for mauvais, nom in (("/a/../b", ".."), ("/a\x00b", "NUL"), ("/a\nb", "saut de ligne"), ("/" + "x" * 255, "256 car."),
                         ("a/b", "relatif"), ("", "vide"), ("/./sd", "segment ."), ("/sd/.", "segment . final"),
                         ("/autoexec.be/.", "segment . apres fichier"), ("/histo//a.bin", "segment vide"),
                         ("//sd", "double barre initiale")):
        msg = leve(ValueError, fs.valide_chemin, mauvais)
        verifie(msg is not None and not msg.startswith("AUTRE"), True, "refuse " + nom)
    verifie(fs.valide_chemin("/histo/mesures-2026-11.bin"), "/histo/mesures-2026-11.bin", "accepte un chemin normal")
    verifie(fs.valide_chemin("/histo/"), "/histo", "barre finale unique retiree")
    verifie(fs.valide_chemin("/"), "/", "racine acceptee")
    verifie(fs.valide_chemin("/mesures 2026#é.bin"), "/mesures 2026#é.bin", "espace, # et accent acceptes")


def cas_protege():
    for p, attendu in (("/autoexec.be", True), ("/autoexec.bat", True), ("/_persist.json", True), ("/x/y.bec", True),
                       ("/.drvset003", True), ("/sd", True), ("/json", True), ("/sd/", True), ("/histo/x.bin", False),
                       ("/sd/x.bin", False)):
        verifie(fs.protege(p), attendu, "protege(%s)" % p)
    with Banc() as b:
        b.fichier("/autoexec.be")
        b.fichier("/histo/x.bin")
        b.fichier("/sd/a.bin")
        b.fichier("/json/b.json")
        b.s.ouvre(CARTE, "flash")
        verifie(leve(fs.RefusFtp, b.s.supprime, "/autoexec.be", 1) is not None, True, "autoexec.be : 1 confirmation refusee")
        verifie((b.srv.racine / "autoexec.be").exists(), True, "autoexec.be intact")
        b.s.supprime("/autoexec.be", 2)
        verifie((b.srv.racine / "autoexec.be").exists(), False, "autoexec.be : 2 confirmations supprime")
        verifie(leve(fs.RefusFtp, b.s.supprime, "/sd", 1) is not None, True, "/sd : 1 confirmation refusee")
        verifie(leve(fs.RefusFtp, b.s.supprime, "/json", 1) is not None, True, "/json : 1 confirmation refusee")
        verifie(leve(fs.RefusFtp, b.s.supprime, "/histo/x.bin", 0) is not None, True, "0 confirmation refusee")
        b.s.supprime("/histo/x.bin", 1)
        verifie((b.srv.racine / "histo/x.bin").exists(), False, "/histo/x.bin : 1 confirmation supprime")
        b.s.supprime("/sd", 2)
        verifie((b.srv.racine / "sd").exists(), False, "/sd : 2 confirmations supprime le dossier et son contenu")


def cas_supprime_detours():
    with Banc() as b:
        b.fichier("/sd/a.bin")
        b.s.ouvre(CARTE, "flash")
        for forme in ("/./sd", "/sd/.", "/autoexec.be/."):
            msg = leve(ValueError, b.s.supprime, forme, 1)
            verifie(msg is not None and not msg.startswith("AUTRE"), True, "supprime(%s, 1) refuse" % forme)
        verifie((b.srv.racine / "sd/a.bin").exists(), True, "/sd intact")


def cas_noms_speciaux():
    nom = "mesures 2026#é.bin"
    with Banc() as b:
        b.fichier("/histo/" + nom, b"\x00\x01\xff")
        b.s.ouvre(CARTE, "flash")
        verifie([x["nom"] for x in b.s.liste("/histo")], [nom], "nom special liste")
        sortie = io.BytesIO()
        b.s.lit("/histo/" + nom, sortie)
        verifie(sortie.getvalue(), b"\x00\x01\xff", "nom special lu")
        b.s.supprime("/histo/" + nom, 1)
        verifie(b.s.liste("/histo"), [], "nom special supprime")
    with Banc(sans_mlsd=True) as b:             # repli LIST, noms avec espace
        b.fichier("/histo/a b.bin", b"12345")
        b.fichier("/histo/sous/c.bin")
        b.s.ouvre(CARTE, "flash")
        res = {x["nom"]: (x["type"], x["taille"]) for x in b.s.liste("/histo")}
        verifie(res, {"a b.bin": ("fichier", 5), "sous": ("dossier", 0)}, "repli LIST : noms, types et tailles")


def cas_liste_champs():
    with Banc() as b:
        b.fichier("/a.bin", b"1234")
        b.fichier("/d/x")
        b.s.ouvre(CARTE, "flash")
        res = b.s.liste("/")
        verifie(sorted(res[0]), ["date", "nom", "taille", "type"], "champs d'une entree")
        verifie([(x["nom"], x["type"], x["taille"]) for x in res], [("a.bin", "fichier", 4), ("d", "dossier", 0)],
                "liste : types et tailles")
        verifie(len(res[0]["date"]) >= 8, True, "date renseignee")


def cas_zip():
    with Banc() as b:
        b.fichier("/histo/a.bin", b"AAAA")
        b.fichier("/histo/sous/b.bin", b"\x00\xffB")
        b.fichier("/autre.txt", b"zz")
        b.s.ouvre(CARTE, "flash")
        sortie = io.BytesIO()
        b.s.zip(["/histo", "/autre.txt"], sortie)
        z = zipfile.ZipFile(io.BytesIO(sortie.getvalue()))
        verifie(sorted(z.namelist()), ["autre.txt", "histo/a.bin", "histo/sous/b.bin"], "noms relatifs dans le zip")
        verifie([z.read(n) for n in sorted(z.namelist())], [b"zz", b"AAAA", b"\x00\xffB"], "octets exacts")


def cas_noms_hostiles():
    pieges = ["../x", "a\b", "c/d", "ef"]
    with Banc(noms_pieges=pieges) as b:
        b.fichier("/histo/ok.bin", b"OK")
        b.s.ouvre(CARTE, "flash")
        verifie([x["nom"] for x in b.s.liste("/")], ["histo"], "liste : noms hostiles absents")
        sortie = io.BytesIO()
        b.s.zip(["/"], sortie)
        z = zipfile.ZipFile(io.BytesIO(sortie.getvalue()))
        verifie(z.namelist(), ["histo/ok.bin"], "zip : aucune entree hors dossier")
        verifie(sorted(b.s.noms_ignores)[:1] != [], True, "noms ignores signales")
        verifie([a for c, a in b.srv.commandes if c in ("RETR", "DELE", "RMD") and ("x" == a[-1] or "\\" in a)], [],
                "aucune commande vers un nom hostile")
    with Banc(noms_pieges=pieges, sans_mlsd=True) as b:
        b.s.ouvre(CARTE, "flash")
        verifie([x["nom"] for x in b.s.liste("/")], [], "repli LIST : noms hostiles absents")


def cas_ouvre_refus_eteint():
    with Banc(UFS_FLASH) as b:                  # session flash, puis SD demandee sur une carte sans SD
        b.s.ouvre(CARTE, "flash")
        msg = leve(fs.RefusFtp, b.s.ouvre, CARTE, "sd")
        verifie(msg is not None and not msg.startswith("AUTRE"), True, "sd refusee")
        verifie(b.fc.ufsftp(), [("127.0.0.1", 2), ("127.0.0.1", 0)], "UfsFTP 0 envoye au refus")
        verifie(b.s.etat()["etat"], "eteint", "etat eteint")
        verifie(leve(fs.RefusFtp, b.s.liste, "/") is not None, True, "plus de session")
    with Banc() as b:                           # identifiants vides sur changement de support
        b.s.ouvre(CARTE, "flash")
        b.s._identifiants = lambda fw: ("u", "")
        verifie(leve(fs.RefusFtp, b.s.ouvre, CARTE, "sd") is not None, True, "identifiants vides refuses")
        verifie(b.fc.ufsftp()[-1], ("127.0.0.1", 0), "UfsFTP 0 aussi")


def cas_allumage_delai():
    with Banc(echoue_sur=("UfsFTP 1",)) as b:
        msg = leve(fs.RefusFtp, b.s.ouvre, CARTE, "sd")
        verifie(msg is not None and not msg.startswith("AUTRE"), True, "reponse perdue a UfsFTP 1 : RefusFtp")
        verifie([c for _, c in b.fc.journal if c.startswith("UfsFTP")], ["UfsFTP 1", "UfsFTP 0"],
                "UfsFTP 0 tente apres un UfsFTP 1 sans reponse")
        verifie(b.s.etat()["etat"], "erreur", "etat erreur")


def cas_concurrence():
    with Banc() as b:
        b.fichier("/a.bin", b"A" * 5000)
        b.fichier("/d/b.bin", b"B" * 300)
        b.s.ouvre(CARTE, "flash")
        erreurs, fini = [], threading.Event()

        def travail(i):
            try:
                for _ in range(8):
                    noms = sorted(x["nom"] for x in b.s.liste("/"))
                    if noms != ["a.bin", "d"]:
                        erreurs.append("liste %r" % noms)
                    s = io.BytesIO()
                    b.s.lit("/a.bin" if i % 2 else "/d/b.bin", s)
                    if s.getvalue() != (b"A" * 5000 if i % 2 else b"B" * 300):
                        erreurs.append("octets du fil %d" % i)
            except Exception as e:
                erreurs.append("fil %d : %r" % (i, e))

        def horloge():
            while not fini.is_set():
                b.s.tic()

        fils = [threading.Thread(target=travail, args=(i,)) for i in range(4)]
        tic = threading.Thread(target=horloge)
        tic.start()
        for f in fils:
            f.start()
        for f in fils:
            f.join(60)
        fini.set()
        tic.join(10)
        verifie([f.is_alive() for f in fils] + [tic.is_alive()], [False] * 5, "aucun interblocage")
        verifie(erreurs, [], "aucune erreur, resultats corrects")
        verifie(b.s.etat()["etat"], "actif", "session toujours active")
        verifie([n for _, n in b.fc.ufsftp()], [2], "aucun UfsFTP en trop")


def cas_place():
    with Banc(UFS_FLASH) as b:                  # flash : 50 Ko libres
        b.s.ouvre(CARTE, "flash")
        msg = leve(fs.RefusFtp, b.s.envoie, "/", "gros.bin", io.BytesIO(b"x" * 60 * 1024), False)
        verifie(msg is not None and not msg.startswith("AUTRE"), True, "plus gros que la place libre : RefusFtp")
        verifie([c for c, _ in b.srv.commandes if c == "STOR"], [], "aucun STOR avant le refus")
        b.s.envoie("/", "petit.bin", io.BytesIO(b"x" * 1024), False)
        verifie((b.srv.racine / "petit.bin").stat().st_size, 1024, "ce qui tient est envoye")
    with Banc(UFS_SD) as b:                     # SD : 500 Ko libres, flash 50 Ko ; mode flash lit la 2e paire
        b.s.ouvre(CARTE, "flash")
        verifie(leve(fs.RefusFtp, b.s.envoie, "/", "gros.bin", io.BytesIO(b"x" * 60 * 1024), False) is not None, True,
                "mode flash avec SD : la place est celle de la flash")
        b.s.ouvre(CARTE, "sd")
        b.s.envoie("/", "gros.bin", io.BytesIO(b"x" * 60 * 1024), False)
        verifie((b.srv.racine / "gros.bin").stat().st_size, 60 * 1024, "mode sd : la place est celle de la SD")
    with Banc(None) as b:                       # place inconnue : on tente
        b.s.ouvre(CARTE, "flash")
        b.s.envoie("/", "x.bin", io.BytesIO(b"x" * 10), False)
        verifie((b.srv.racine / "x.bin").exists(), True, "place inconnue : envoi tente")


def cas_ecrasement():
    with Banc() as b:
        b.fichier("/a.bin", b"vieux")
        b.s.ouvre(CARTE, "flash")
        msg = leve(fs.RefusFtp, b.s.envoie, "/", "a.bin", io.BytesIO(b"neuf"), False)
        verifie(msg is not None and not msg.startswith("AUTRE"), True, "nom existant sans ecraser : RefusFtp")
        verifie((b.srv.racine / "a.bin").read_bytes(), b"vieux", "fichier intact")
        b.s.envoie("/", "a.bin", io.BytesIO(b"neuf"), True)
        verifie((b.srv.racine / "a.bin").read_bytes(), b"neuf", "ecraser=True remplace")
        verifie(leve(ValueError, b.s.envoie, "/", "../x", io.BytesIO(b"x"), True) is not None, True, "nom avec .. refuse")
        verifie(leve(ValueError, b.s.envoie, "/", "a/b", io.BytesIO(b"x"), True) is not None, True, "nom avec / refuse")


def cas_deplace():
    with Banc() as b:
        b.fichier("/histo/a.bin", b"AAA")
        (b.srv.racine / "archives").mkdir()
        b.s.ouvre(CARTE, "flash")
        b.s.deplace("/histo/a.bin", "/archives/a.bin")
        verifie([(b.srv.racine / "archives/a.bin").read_bytes(), (b.srv.racine / "histo/a.bin").exists()],
                [b"AAA", False], "deplace")
        b.s.cree_dossier("/nouveau")
        verifie((b.srv.racine / "nouveau").is_dir(), True, "cree_dossier")
        verifie(leve(fs.RefusFtp, b.s.cree_dossier, "/nouveau") is not None, True, "dossier existant : RefusFtp")
        verifie(leve(fs.RefusFtp, b.s.deplace, "/absent", "/archives/z") is not None, True, "source absente : RefusFtp")


def cas_sans_session():
    with Banc() as b:
        msg = leve(fs.RefusFtp, b.s.liste, "/")
        verifie(msg is not None and not msg.startswith("AUTRE"), True, "liste sans session ouverte : RefusFtp")


def cas_adresse_invalide():
    for mauvaise in ("a b", "x;rm", "http://x", "h/../x", "", "h\n", "h:21"):
        with Banc() as b:
            msg = leve(fs.RefusFtp, b.s.ouvre, dict(CARTE, adresse=mauvaise), "flash")
            verifie(msg is not None and not msg.startswith("AUTRE"), True, "adresse refusee : %r" % mauvaise)
            verifie(b.fc.journal, [], "aucune commande envoyee pour %r" % mauvaise)
    with Banc() as b:
        verifie(leve(fs.RefusFtp, b.s.ouvre, CARTE, "nimporte") is not None, True, "support inconnu refuse")


def cas_mot_de_passe():
    with Banc() as b:
        b.s.ouvre(CARTE, "flash")
        verifie(MDP in json.dumps(b.s.etat()), False, "etat() ne contient pas le mot de passe")
    with Banc(identifiants=lambda fw: ("u", MDP + "x")) as b:
        msg = leve(fs.RefusFtp, b.s.ouvre, CARTE, "flash")
        verifie(msg is not None and not msg.startswith("AUTRE"), True, "mauvais mot de passe : RefusFtp")
        verifie(MDP in (msg or "") or MDP in json.dumps(b.s.etat()), False, "ni message ni etat ne contiennent le mot de passe")
        verifie(b.fc.ufsftp()[-1][1], 0, "FTP eteint apres l'echec de connexion")
    with Banc(identifiants=lambda fw: ("u", "")) as b:           # identifiants absents du .h
        verifie(leve(fs.RefusFtp, b.s.ouvre, CARTE, "flash") is not None, True, "identifiants vides : RefusFtp")


if __name__ == "__main__":
    for cas in (cas_ouvre, cas_sd_inconnue, cas_ferme_toujours, cas_inactivite, cas_reconnexion, cas_carte_perdue,
                cas_chemins, cas_protege, cas_supprime_detours, cas_noms_speciaux, cas_noms_hostiles,
                cas_ouvre_refus_eteint, cas_allumage_delai, cas_concurrence, cas_liste_champs, cas_zip, cas_place, cas_ecrasement,
                cas_deplace, cas_sans_session, cas_adresse_invalide, cas_mot_de_passe):
        print(f"-- {cas.__name__}")
        cas()
    print("\nECHECS : " + (", ".join(ECHECS) if ECHECS else "aucun"))
    sys.exit(1 if ECHECS else 0)
