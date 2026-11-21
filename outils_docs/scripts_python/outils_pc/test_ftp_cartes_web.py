"""Banc de ftp_cartes_web (serveur et routes du navigateur FTP des cartes). Code de sortie 0 = vert.

Serveur REEL sur 127.0.0.1 (port libre, jamais 7450), faux serveur FTP de carte et fausse commande HTTP
(`faux_ftp_carte.py`), mini-depot temporaire avec un FAUX mot de passe (`test_ftp_cartes_liste.depot`). Un second serveur
rend la meme application avec une adresse cliente simulee (192.168.0.50) pour les gestes reserves a ce PC.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_ftp_cartes_web.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import http.client
import io
import json
import ftplib
import sys
import threading
import time
import zipfile
from http.server import ThreadingHTTPServer
from urllib.parse import quote

import acces_web
import faux_ftp_carte as faux
import ftp_cartes_session as fs
import ftp_cartes_web as fw
import test_ftp_cartes_liste as tl

ECHECS = []
REPONSES = []                                   # tout ce que les serveurs ont rendu : cas_secret le fouille
MDP = tl.FAUX_MDP
ENV = "tasmota32s3-garage-essai"
FIRMWARE = "FIRMWARE_ESSAI"
UFS_SD = '{"Ufs":{"Type":1,"Size":1000,"Free":500},{"Type":3,"Size":100,"Free":50}}'


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


class Banc:
    """Mini-depot + faux serveur FTP + serveur web local (et distant simule)."""

    def __init__(self):
        sections = tl.sec(FIRMWARE, '#define WIFI_IP_ADDRESS "127.0.0.1"\n')
        self.racine = tl.depot(sections, {ENV: tl.persist("essai")}, {ENV: FIRMWARE})
        self.srv = faux.FauxFtpCarte(identifiants=("admin", MDP))
        self.fc = faux.FausseCommande(UFS_SD)
        self.session = fs.Session(commande=self.fc, port=self.srv.port, delai_allumage=1, identifiants=lambda f: ("admin", MDP))
        self.acces = acces_web.Acces(0, True, "Banc FTP")
        gestionnaire = fw.fabrique_gestionnaire(self.acces, self.racine, self.session)

        class Distant(gestionnaire):                # meme application, client vu comme un autre appareil du reseau
            def __init__(self, request, client_address, server):
                super().__init__(request, ("192.168.0.50", 5555), server)

        self.local = ThreadingHTTPServer(("127.0.0.1", 0), gestionnaire)
        self.distant = ThreadingHTTPServer(("127.0.0.1", 0), Distant)
        for s in (self.local, self.distant):
            s.daemon_threads = True
            threading.Thread(target=s.serve_forever, daemon=True).start()
        self.port, self.port_distant = self.local.server_address[1], self.distant.server_address[1]
        self.acces.port, self.acces.cookie = self.port, "jeton_%d" % self.port
        (self.srv.racine / "sd").mkdir()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.session.ferme("fin du banc")
        for s in (self.local, self.distant):
            s.shutdown()
            s.server_close()
        self.srv.arrete()

    def req(self, methode, chemin, corps=None, ent=None, distant=False, json_=True, avec_x=True):
        """(statut, corps, en-tetes). `ent` complete ou remplace les en-tetes ; avec_x : en-tete anti-CSRF des POST."""
        port = self.port_distant if distant else self.port
        h = {}
        if methode == "POST" and avec_x:
            h[fw.ENTETE] = "1"
        if distant:
            h["Cookie"] = "%s=%s" % (self.acces.cookie, self.acces.jeton)
        if isinstance(corps, (dict, list)):
            corps = json.dumps(corps).encode("utf-8")
        h.update(ent or {})
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
        try:
            c.request(methode, chemin, body=corps, headers=h)
            r = c.getresponse()
            donnees = r.read()
            REPONSES.append(donnees + str(r.getheaders()).encode("utf-8"))
            return r.status, donnees, dict(r.getheaders())
        finally:
            c.close()

    def json(self, *a, **k):
        st, corps, _ = self.req(*a, **k)
        return st, (json.loads(corps) if corps[:1] in (b"{", b"[") else corps.decode("utf-8", "replace"))

    def ouvre(self, support="sd", **k):
        return self.json("POST", "/ouvre", {"env": ENV, "support": support}, **k)

    def fichier(self, chemin, contenu=b"abc"):
        p = self.srv.racine / chemin.lstrip("/")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(contenu)
        return p

    def ufsftp(self):
        return [n for _, n in self.fc.ufsftp()]


def cas_routes():
    with Banc() as b:
        st, cartes = b.json("GET", "/cartes")
        verifie((st, [c["env"] for c in cartes["cartes"]]), (200, [ENV]), "GET /cartes : la carte du mini-depot")
        st, page = b.req("GET", "/")[:2]
        verifie((st, b"<html" in page.lower()), (200, True), "GET / : une page")
        verifie(b.json("GET", "/etat"), (200, {"env": "", "support": "", "etat": "eteint", "message": "", "sd": None}), "GET /etat : eteint")
        verifie(b.json("GET", "/liste?chemin=/")[0], 409, "GET /liste sans session : 409")
        verifie(b.ouvre("sd")[0], 200, "POST /ouvre : 200")
        verifie(b.json("POST", "/ouvre", {"env": "inconnu", "support": "sd"})[0], 404, "POST /ouvre env inconnu : 404")
        verifie(b.json("POST", "/ouvre", {"env": ENV, "support": "usb"})[0], 409, "POST /ouvre support inconnu : 409")
        b.ouvre("sd")
        b.fichier("sd/a b é#.txt", b"contenu 1")
        b.fichier("sd/dossier/x.txt", b"xx")
        st, liste = b.json("GET", "/liste?chemin=/sd")
        verifie((st, sorted(e["nom"] for e in liste["entrees"])), (200, ["a b é#.txt", "dossier"]), "GET /liste : entrees de /sd")
        verifie(b.json("GET", "/liste?chemin=relatif")[0], 400, "GET /liste chemin invalide : 400 (pas 500)")
        verifie(b.json("GET", "/liste?chemin=/sd/../x")[0], 400, "GET /liste avec .. : 400")
        st, corps, ent = b.req("GET", "/telecharge?chemin=" + quote("/sd/a b é#.txt"))
        verifie((st, corps), (200, b"contenu 1"), "GET /telecharge : nom special, contenu exact")
        cd = ent.get("Content-Disposition", "")
        verifie(("attachment" in cd, "filename*=UTF-8''a%20b%20%C3%A9%23.txt" in cd, 'filename="' in cd), (True, True, True),
                "telechargement : attachment, filename* encode et repli ASCII")
        st, corps, _ = b.req("POST", "/zip", {"chemins": ["/sd/dossier", "/sd/a b é#.txt"]})
        noms = sorted(zipfile.ZipFile(io.BytesIO(corps)).namelist()) if st == 200 else st
        verifie(noms, ["sd/a b é#.txt", "sd/dossier/x.txt"], "POST /zip : zip des chemins demandes")
        st, _, _ = b.req("POST", "/envoie?dossier=/sd&nom=neuf.txt&ecraser=0", b"neuf")
        verifie((st, (b.srv.racine / "sd/neuf.txt").read_bytes() if st == 200 else None), (200, b"neuf"), "POST /envoie : fichier cree")
        verifie(b.req("POST", "/envoie?dossier=/sd&nom=neuf.txt&ecraser=0", b"autre")[0], 409, "POST /envoie sans ecraser : 409")
        verifie(b.req("POST", "/envoie?dossier=/sd&nom=neuf.txt&ecraser=1", b"autre")[0], 200, "POST /envoie ecraser=1 : 200")
        verifie(b.req("POST", "/envoie?dossier=/sd&nom=../x&ecraser=0", b"x")[0], 400, "POST /envoie nom invalide : 400")
        verifie(b.json("POST", "/dossier", {"chemin": "/sd/nouveau"})[0], 200, "POST /dossier : 200")
        verifie((b.srv.racine / "sd/nouveau").is_dir(), True, "dossier cree sur la carte")
        verifie(b.json("POST", "/deplace", {"source": "/sd/neuf.txt", "cible": "/sd/nouveau/neuf.txt"})[0], 200, "POST /deplace : 200")
        verifie((b.srv.racine / "sd/nouveau/neuf.txt").is_file(), True, "fichier deplace")
        verifie(b.json("POST", "/supprime", {"chemin": "/sd/nouveau/neuf.txt", "confirmations": 0})[0], 409, "POST /supprime non confirme : 409")
        verifie(b.json("POST", "/supprime", {"chemin": "/sd/nouveau/neuf.txt", "confirmations": 1})[0], 200, "POST /supprime confirme : 200")
        verifie(b.json("POST", "/supprime", {"chemin": "/sd/autoexec.be", "confirmations": 1})[0], 409, "fichier protege : seconde confirmation (409)")
        verifie(b.json("POST", "/supprime", {"chemin": "/sd/x", "confirmations": "oui"})[0], 400, "confirmations non entier : 400")
        verifie(b.req("POST", "/ouvre", b"pas du json")[0], 400, "corps non JSON : 400")
        verifie(b.json("POST", "/ferme", {})[0], 200, "POST /ferme : 200")
        verifie(b.json("GET", "/etat")[1]["etat"], "eteint", "apres /ferme : eteint")
        verifie(b.ufsftp()[-1], 0, "UfsFTP 0 envoye")
        verifie(b.req("PUT", "/etat")[0], 405, "PUT : 405")
        verifie(b.req("DELETE", "/etat")[0], 405, "DELETE : 405")
        verifie(b.req("GET", "/inconnue")[0], 404, "GET route inconnue : 404")
        verifie(b.req("POST", "/inconnue", {})[0], 404, "POST route inconnue : 404")


def cas_ecritures_ce_pc():
    with Banc() as b:
        b.ouvre("sd")                                            # session ouverte depuis ce PC
        b.fichier("sd/lu.txt", b"lu")
        d = {"distant": True}
        verifie(b.json("POST", "/ouvre", {"env": ENV, "support": "sd"}, **d)[0], 403, "distant : POST /ouvre refuse")
        verifie(b.req("POST", "/envoie?dossier=/sd&nom=z.txt&ecraser=0", b"z", **d)[0], 403, "distant : POST /envoie refuse")
        verifie(b.json("POST", "/supprime", {"chemin": "/sd/lu.txt", "confirmations": 1}, **d)[0], 403, "distant : POST /supprime refuse")
        verifie(b.json("POST", "/dossier", {"chemin": "/sd/d"}, **d)[0], 403, "distant : POST /dossier refuse")
        verifie(b.json("POST", "/deplace", {"source": "/sd/lu.txt", "cible": "/sd/m.txt"}, **d)[0], 403, "distant : POST /deplace refuse")
        verifie([p.name for p in (b.srv.racine / "sd").iterdir()], ["lu.txt"], "distant : rien n'a ete ecrit sur la carte")
        verifie(b.json("GET", "/liste?chemin=/sd", **d)[0], 200, "distant avec jeton : GET /liste 200")
        verifie(b.req("GET", "/telecharge?chemin=/sd/lu.txt", **d)[:2], (200, b"lu"), "distant avec jeton : GET /telecharge 200")
        verifie(b.req("GET", "/liste?chemin=/sd", ent={"Cookie": ""}, distant=True)[0], 403, "distant sans jeton : 403")


def cas_beacon():
    with Banc() as b:
        b.ouvre("sd")
        origine = {"Origin": "http://127.0.0.1:%d" % b.port}
        verifie(b.json("POST", "/supprime", {"chemin": "/sd/x", "confirmations": 1}, avec_x=False, ent=origine)[0], 403, "/supprime sans en-tete X : refuse")
        verifie(b.json("POST", "/dossier", {"chemin": "/sd/x"}, avec_x=False, ent=origine)[0], 403, "/dossier sans en-tete X : refuse")
        verifie(b.json("POST", "/ferme", {"chemin": 1}, avec_x=False, ent={"Origin": "http://evil.example"})[0], 403, "/ferme origine etrangere : refuse")
        verifie(b.json("GET", "/etat")[1]["etat"], "actif", "origine etrangere : la session reste ouverte")
        verifie(b.json("POST", "/ferme", None, avec_x=False, ent=origine)[0], 200, "/ferme sans en-tete X, origine locale : 200")
        verifie(b.ufsftp(), [1, 0], "sendBeacon : UfsFTP 0 envoye")
        b.ouvre("sd")
        verifie(b.json("POST", "/ferme", None, avec_x=False)[0], 200, "/ferme sans Origin : 200")
        verifie(b.ufsftp(), [1, 0, 1, 0], "UfsFTP 0 de nouveau")


def cas_session_changee():
    """Un geste qui nomme une autre carte ou un autre support que la session est refuse (409) sans rien ecrire ; sans env ni support : comme avant."""
    with Banc() as b:
        b.ouvre("sd")
        b.fichier("/a.bin")
        autre = {"env": ENV, "support": "flash"}
        verifie(b.json("POST", "/supprime", {"chemin": "/a.bin", "confirmations": 1, **autre})[0], 409, "/supprime d'un autre support : 409")
        verifie((b.srv.racine / "a.bin").exists(), True, "/supprime refuse : le fichier est toujours la")
        verifie(b.json("POST", "/dossier", {"chemin": "/d", **autre})[0], 409, "/dossier d'un autre support : 409")
        verifie((b.srv.racine / "d").exists(), False, "/dossier refuse : rien cree")
        verifie(b.json("POST", "/deplace", {"source": "/a.bin", "cible": "/b.bin", **autre})[0], 409, "/deplace d'un autre support : 409")
        verifie(b.json("POST", "/zip", {"chemins": ["/a.bin"], **autre})[0], 409, "/zip d'un autre support : 409")
        verifie(b.req("POST", "/envoie?dossier=/&nom=n.bin&env=%s&support=flash" % ENV, b"xyz")[0], 409, "/envoie d'un autre support : 409")
        verifie((b.srv.racine / "n.bin").exists(), False, "/envoie refuse : rien ecrit")
        verifie(b.json("POST", "/supprime", {"chemin": "/a.bin", "confirmations": 1, "env": "autre-env", "support": "sd"})[0], 409, "/supprime d'une autre carte : 409")
        verifie(b.json("POST", "/dossier", {"chemin": "/d", "env": ENV, "support": "sd"})[0], 200, "meme env et meme support : accepte")
        verifie(b.req("POST", "/envoie?dossier=/&nom=n.bin", b"xyz")[0], 200, "sans env ni support : comme avant")
        verifie(b.json("POST", "/ferme", {"env": "autre", "support": "flash"})[0], 200, "/ferme n'est pas garde")


def cas_geste_pendant_changement_de_carte():
    """Un POST garde arrive pendant un changement de carte (ouvre tient le verrou, UfsFTP 0 lent) : 409, rien n'est fait sur la nouvelle carte."""
    with Banc() as b:
        b.ouvre("sd")
        b.fichier("/a.bin")
        lente = b.session._commande
        b.session._commande = lambda ip, cmnd, delai: (time.sleep(1.5) if cmnd == "UfsFTP 0" else None, lente(ip, cmnd, delai))[1]
        autre = {"env": "autre", "lieu": "garage", "nom": "autre", "hote": "autre", "adresse": "localhost", "puce": "ESP32", "firmware": FIRMWARE}
        t = threading.Thread(target=lambda: b.session.ouvre(autre, "sd"))
        t.start()
        time.sleep(0.4)
        st, texte = b.json("POST", "/supprime", {"chemin": "/a.bin", "confirmations": 1, "env": ENV, "support": "sd"})
        verifie((st, texte), (409, "la session a change (carte ou support)"), "/supprime pendant le changement de carte : 409")
        t.join(20)
        verifie((b.srv.racine / "a.bin").exists(), True, "le fichier est toujours la")
        st, _ = b.json("POST", "/dossier", {"chemin": "/d", "env": ENV, "support": "sd"})
        verifie((st, (b.srv.racine / "d").exists()), (409, False), "/dossier apres le changement : 409, rien cree")


def cas_deux_onglets():
    with Banc() as b:
        b.ouvre("sd")
        e1, e2 = b.json("GET", "/etat")[1], b.json("GET", "/etat")[1]
        verifie((e1, e1["etat"]), (e2, "actif"), "deux GET /etat voient la meme session ouverte")
        st, e3 = b.ouvre("sd")
        verifie((st, e3), (200, e1), "second POST /ouvre (meme carte, meme support) : l'etat existant")
        verifie(b.ufsftp(), [1], "pas de second UfsFTP")
        verifie(sum(1 for c, _ in b.srv.commandes if c == "USER"), 1, "une seule connexion FTP")
        b.ouvre("flash")
        verifie(b.json("GET", "/etat")[1]["support"], "flash", "un autre support passe par ouvre")
        verifie(b.ufsftp(), [1, 2], "UfsFTP 2 pour la flash")


def cas_envoi_trop_gros():
    with Banc() as b:
        b.ouvre("sd")
        c = http.client.HTTPConnection("127.0.0.1", b.port, timeout=15)
        c.putrequest("POST", "/envoie?dossier=/sd&nom=gros.bin&ecraser=0")
        c.putheader(fw.ENTETE, "1")
        c.putheader("Content-Length", str(fw.MAX_ENVOI + 1))
        c.endheaders()
        r = c.getresponse()
        REPONSES.append(r.read())
        c.close()
        verifie(r.status, 413, "Content-Length > MAX_ENVOI : 413")
        verifie(any(cmd == "STOR" for cmd, _ in b.srv.commandes), False, "aucun STOR recu par la carte")
        verifie((b.srv.racine / "sd/gros.bin").exists(), False, "rien d'ecrit sur la carte")
        verifie(b.req("POST", "/envoie?dossier=/sd&nom=ok.bin&ecraser=0", b"ok")[0], 200, "sous la limite : 200")


class FtpCite(ftplib.FTP):
    """Carte dont le refus 530 cite le mot de passe : la session doit le masquer."""

    def login(self, *a, **k):
        raise ftplib.error_perm("530 mot de passe %s refuse" % MDP)


def cas_secret():
    with Banc() as b:
        b.ouvre("sd")
        b.json("GET", "/liste?chemin=/sd")
        b.json("GET", "/liste?chemin=/absent")
        b.json("POST", "/supprime", {"chemin": "/sd/y", "confirmations": 1})
        b.json("POST", "/ouvre", {"env": "inconnu", "support": "sd"})
        b.json("POST", "/ferme", {})
        b.session._fabrique = FtpCite                        # (a) le refus 530 de la carte cite le mot de passe
        st, corps, _ = b.req("POST", "/ouvre", {"env": ENV, "support": "sd"})
        verifie(st, 409, "refus 530 citant le mot de passe : 409")
        verifie(MDP.encode("utf-8") in corps, False, "la reponse de /ouvre ne contient pas le mot de passe")
        verifie(b"***" in corps, True, "le mot de passe est remplace par ***")

        def casse(*a, **k):
            raise RuntimeError("secret " + MDP)

        b.session.liste = casse                              # (b) exception inattendue dont le message cite le mot de passe
        st, corps, _ = b.req("GET", "/liste?chemin=/sd")
        verifie(st, 500, "exception inattendue : 500")
        verifie(MDP.encode("utf-8") in corps, False, "le 500 ne rend pas le message de l'exception")
        verifie(b"RuntimeError" in corps, True, "le 500 nomme le type de l'exception")
        b.json("GET", "/cartes"), b.json("GET", "/etat")
    verifie(any(MDP.encode("utf-8") in r for r in REPONSES), False, "aucune reponse (cartes, etat, erreurs) ne contient le mot de passe")
    verifie(len(REPONSES) > 10, True, "le banc a bien collecte les reponses")


def cas_concurrence():
    with Banc() as b:
        lente = b.session._commande
        b.session._commande = lambda ip, c, d: (time.sleep(0.3), lente(ip, c, d))[1]     # elargit la fenetre de course
        res = []
        fils = [threading.Thread(target=lambda: res.append(b.ouvre("sd")[0])) for _ in range(2)]
        for f in fils:
            f.start()
        for f in fils:
            f.join()
        verifie(res, [200, 200], "deux POST /ouvre simultanes : 200 et 200")
        verifie(b.ufsftp(), [1], "un seul UfsFTP")
        verifie(sum(1 for c, _ in b.srv.commandes if c == "USER"), 1, "une seule connexion FTP")


def cas_serveur():
    with Banc() as b:
        try:
            fw.ServeurFtp(("127.0.0.1", b.port), fw.fabrique_gestionnaire(b.acces, b.racine, b.session)).server_close()
            leve = False
        except OSError:
            leve = True
        verifie(leve, True, "un second serveur sur le meme port leve OSError")
        for m in ("HEAD", "OPTIONS"):
            verifie(b.req(m, "/etat")[0], 405, m + " : 405")


def cas_host_hostile():
    with Banc() as b:
        verifie(b.req("GET", "/etat", ent={"Host": "evil.example"})[0], 403, "Host evil.example : GET refuse")
        verifie(b.req("POST", "/ferme", {}, ent={"Host": "evil.example"})[0], 403, "Host evil.example : POST /ferme refuse")
        verifie(b.req("GET", "/etat", ent={"Host": "localhost:%d" % b.port})[0], 200, "Host localhost:port : accepte")


def main():
    for cas in (cas_routes, cas_ecritures_ce_pc, cas_beacon, cas_session_changee, cas_geste_pendant_changement_de_carte, cas_deux_onglets, cas_envoi_trop_gros, cas_secret, cas_concurrence, cas_serveur, cas_host_hostile):
        print("---", cas.__name__)
        cas()
    print("\n%s" % ("VERT" if not ECHECS else "ROUGE : %d echec(s) : %s" % (len(ECHECS), "; ".join(ECHECS))))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
