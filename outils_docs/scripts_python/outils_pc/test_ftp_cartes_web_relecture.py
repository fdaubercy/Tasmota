"""Banc voisin de test_ftp_cartes_web.py (qui depasse deja 500 lignes) : correctifs des relectures du 2026-11-22 (tache 12, plan A8).

Anti-CSRF des GET a effet (C2 : `/etat?onglet=`, `/liste`, `/telecharge`), `\\` refuse (C5), champ `type` de /supprime et /deplace (C8),
`confirmations` de /envoie pour ecraser un fichier protege (C9). Meme montage que test_ftp_cartes_web.py (serveur reel sur un port libre,
faux serveur FTP, fausse commande, mini-depot au faux mot de passe). Code de sortie 0 = vert.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_ftp_cartes_web_relecture.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import sys

from test_ftp_cartes_web import ECHECS, MDP, REPONSES, Banc, verifie

A, B, C, D = "a" * 16, "b" * 16, "c" * 16, "d" * 16


def ecritures(b):
    return [c for c, _ in b.srv.commandes if c in ("RNFR", "RNTO", "DELE", "RMD", "MKD", "STOR")]


def cas_csrf_get():
    """C2 : un GET a effet venu d'une autre origine est refuse ; la page (same-origin), la navigation directe et urllib (sans en-tete) passent."""
    with Banc() as b:
        b.ouvre("sd")
        b.fichier("/a.bin", b"abc")
        loin = "http://evil.example"
        for ent, libelle in (({"Sec-Fetch-Site": "cross-site"}, "Sec-Fetch-Site cross-site"), ({"Origin": loin}, "Origin etranger"),
                             ({"Sec-Fetch-Site": "same-site"}, "Sec-Fetch-Site same-site (autre outil sur 127.0.0.1)")):
            verifie(b.req("GET", "/etat?onglet=" + A, ent=ent)[0], 403, "/etat?onglet=, %s : 403" % libelle)
            n = len(b.srv.commandes)
            verifie(b.req("GET", "/telecharge?chemin=/a.bin", ent=ent)[:2], (403, b"refuse"), "/telecharge, %s : 403" % libelle)
            verifie(b.req("GET", "/liste?chemin=/", ent=ent)[0], 403, "/liste, %s : 403 (ne repousse pas l'inactivite)" % libelle)
            verifie(len(b.srv.commandes), n, "%s : aucune commande FTP (ni RETR ni MLSD)" % libelle)
        verifie(A in b.session.onglets._vus, False, "aucun faux onglet enregistre par une autre origine")
        for ident, ent, libelle in ((B, {"Sec-Fetch-Site": "same-origin"}, "same-origin"), (C, {"Sec-Fetch-Site": "none"}, "none (barre d'adresse)"),
                                    (D, {}, "sans en-tete (urllib, ancien navigateur)")):
            verifie(b.req("GET", "/etat?onglet=" + ident, ent=ent)[0], 200, "/etat?onglet=, %s : 200" % libelle)
            verifie(ident in b.session.onglets._vus, True, "/etat?onglet=, %s : onglet enregistre" % libelle)
            verifie(b.req("GET", "/telecharge?chemin=/a.bin", ent=ent)[:2], (200, b"abc"), "/telecharge, %s : 200" % libelle)
            verifie(b.req("GET", "/liste?chemin=/", ent=ent)[0], 200, "/liste, %s : 200" % libelle)
        ent = {"Origin": "http://127.0.0.1:%d" % b.port, "Sec-Fetch-Site": "same-origin"}
        verifie(b.req("GET", "/telecharge?chemin=/a.bin", ent=ent)[0], 200, "/telecharge avec l'Origin de l'outil : 200")
        verifie(b.req("GET", "/etat", ent={"Sec-Fetch-Site": "cross-site"})[0], 200, "/etat SANS onglet (lecture seule) : 200")
        verifie(b.req("POST", "/zip", {"chemins": ["/a.bin"]}, ent={"Origin": loin})[0], 403, "/zip (POST) d'une autre origine : 403 (deja garde)")


def cas_antislash_web():
    """C5 : `\\` dans un chemin : 400, rien n'est envoye a la carte."""
    with Banc() as b:
        b.ouvre("sd")
        b.fichier("/d/x")
        n = len(b.srv.commandes)
        verifie(b.req("GET", "/liste?chemin=/d%5Cx")[0], 400, "GET /liste avec \\ : 400")
        verifie(b.json("POST", "/dossier", {"chemin": "/d\\n"})[0], 400, "POST /dossier avec \\ : 400")
        verifie(b.json("POST", "/supprime", {"chemin": "/d\\x", "confirmations": 2})[0], 400, "POST /supprime avec \\ : 400")
        verifie(b.req("POST", "/envoie?dossier=/&nom=d%5Cx&ecraser=1", b"z")[0], 400, "POST /envoie, nom avec \\ : 400")
        verifie((len(b.srv.commandes), (b.srv.racine / "d/x").exists()), (n, True), "aucune commande FTP, rien n'a bouge")


def cas_type_web():
    """C8 : `type` de /supprime et /deplace (ce que la page a vu) ; un type change donne 409 sans rien ecrire, une valeur inconnue 400."""
    with Banc() as b:
        b.ouvre("sd")
        b.fichier("/x/plein.bin")
        b.fichier("/f.bin")
        (b.srv.racine / "arch").mkdir()
        st, texte = b.json("POST", "/supprime", {"chemin": "/x", "confirmations": 1, "type": "fichier"})
        verifie((st, str(texte).startswith("le type de l'element a change")), (409, True), "/supprime, fichier vu, dossier sur la carte : 409 (%r)" % texte)
        st, texte = b.json("POST", "/deplace", {"source": "/x", "cible": "/arch/x", "type": "fichier"})
        verifie((st, str(texte).startswith("le type de l'element a change")), (409, True), "/deplace, type change : 409")
        for mauvais in ("lien", 5, ["fichier"]):
            verifie(b.json("POST", "/supprime", {"chemin": "/f.bin", "confirmations": 1, "type": mauvais})[0], 400, "/supprime type %r : 400" % (mauvais,))
        verifie(ecritures(b), [], "aucune commande de modification")
        verifie(b.json("POST", "/supprime", {"chemin": "/f.bin", "confirmations": 1, "type": "fichier"})[0], 200, "/supprime, type correct : 200")
        verifie(b.json("POST", "/deplace", {"source": "/x", "cible": "/arch/x", "type": "dossier"})[0], 200, "/deplace, type correct : 200")


def cas_ecrase_protege_web():
    """C9 : /envoie sur un fichier protege existant : 409 « seconde confirmation » sans STOR, puis `confirmations=2` ecrase."""
    with Banc() as b:
        b.ouvre("sd")
        b.fichier("/autoexec.be", b"cfg")
        st, corps, _ = b.req("POST", "/envoie?dossier=/&nom=autoexec.be&ecraser=1", b"neuf")
        verifie((st, b"seconde confirmation" in corps), (409, True), "/envoie ecraser=1 sur autoexec.be : 409 « seconde confirmation »")
        verifie(b.req("POST", "/envoie?dossier=/&nom=autoexec.be&ecraser=1&confirmations=1", b"neuf")[0], 409, "confirmations=1 : 409")
        for mauvais in ("deux", "-1", "1.5"):            # vide = absent (parse_qs) = 1
            verifie(b.req("POST", "/envoie?dossier=/&nom=autoexec.be&ecraser=1&confirmations=" + mauvais, b"neuf")[0], 400, "confirmations=%r : 400" % mauvais)
        verifie((ecritures(b), (b.srv.racine / "autoexec.be").read_bytes()), ([], b"cfg"), "aucun STOR, autoexec.be intact")
        verifie(b.req("POST", "/envoie?dossier=/&nom=autoexec.be&ecraser=1&confirmations=2", b"neuf")[0], 200, "confirmations=2 : 200")
        verifie(((b.srv.racine / "autoexec.be").read_bytes(), ecritures(b)), (b"neuf", ["STOR"]), "ecrase, un seul STOR")
    verifie(any(MDP.encode("utf-8") in r for r in REPONSES), False, "aucune reponse ne contient le mot de passe")


def main():
    for cas in (cas_csrf_get, cas_antislash_web, cas_type_web, cas_ecrase_protege_web):
        print("---", cas.__name__)
        try:
            cas()
        except Exception as e:                                         # phase rouge : un cas qui leve ne cache pas les suivants
            verifie(repr(e), "pas d'exception", cas.__name__ + " leve")
    print("\n%s" % ("VERT" if not ECHECS else "ROUGE : %d echec(s) : %s" % (len(ECHECS), "; ".join(ECHECS))))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
