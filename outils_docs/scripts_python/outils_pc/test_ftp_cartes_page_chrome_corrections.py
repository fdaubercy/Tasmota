"""Suite 3 de la sonde Chrome du navigateur FTP des cartes (appelee par test_ftp_cartes_page_chrome.py apres test_ftp_cartes_page_chrome_onglets.py).

Tour de corrections : fini apres un 409 (le sondage force refait les vues), boucles multi-elements arretees a la mort de la session (Deconnecter),
geste mort pendant la SECONDE boite, garde de reponse /etat perimee (reponse retardee). Aides : test_ftp_cartes_page_chrome_onglets.py.
"""
import time

from test_build_page_chrome import attend
from test_ftp_cartes_page_chrome_onglets import (attend_sonde, boite_seconde, calme, champ, choisit, clique, coche, confirmations, oublie, pastille, pose_fichiers,
                                                 posts, relit, texte, verifie)


def corrections(cdp, b, tol):
    """Tour de corrections 1 : fini apres un 409, boucles qui s'arretent a la mort de la session, garde de reponse /etat perimee."""
    racine = b.srv.racine
    b.fichier("/a.txt")
    relit(cdp, "a.txt")

    # fini : apres un 409 « session a change » la page ne relit PAS la liste sous l'ancien etat ; le sondage force refait les vues (aucun sonde(true) manuel)
    calme(cdp, "force")                                       # l'intervalle ne passe pas : le geste part forcement avec l'ancienne paire
    oublie(cdp)
    coche(cdp, "a.txt")
    clique(cdp, "b-supp")
    with tol:
        verifie(b.ouvre("flash")[0], 200, "409 : l'autre onglet passe sur la flash")
        clique(cdp, "boite-ok")
        verifie(bool(attend_sonde(cdp, "document.getElementById('pastille').textContent.indexOf('Flash') >= 0 && document.getElementById('msg').textContent.indexOf('autre onglet') >= 0", 25)),
                True, "409 session changee : le sondage force met la page a jour sans appel manuel")
    verifie(tol.n >= 1, True, "409 session changee : le serveur a bien rendu un 409")
    time.sleep(2)                                             # negatif : on laisse a une relecture parasite le temps d'arriver
    tous = cdp.js("window.__req")
    k = next((i for i, r in enumerate(tous) if r.startswith("POST /supprime")), len(tous))
    # L'ordre des requetes depend du moment ou le sondage force part ; le nombre de relectures de la liste, lui, ne depend pas du hasard :
    # une seule (celle des vues refaites par le sondage). Une seconde serait la relecture de `fini` sous l'ancien etat.
    verifie(sum(1 for r in tous[k:] if r.startswith("GET /liste")), 1, "409 session changee : une seule relecture de la liste (celle du sondage force), pas de relecture sous l'ancien etat")
    verifie((racine / "a.txt").exists(), True, "409 session changee : rien n'a ete supprime")
    calme(cdp, False)
    b.ouvre("sd")
    cdp.js("sonde(true)")
    pastille(cdp, "actif", 8)
    attend_sonde(cdp, "document.getElementById('pastille').textContent.indexOf('SD') >= 0", 25)

    # boucles multi-elements : Deconnecter pendant la boucle, plus aucun POST d'ecriture apres la mort
    def coupe(route, lance, libelle, intacts):
        cdp.js("window.__lent=1500; 0")
        oublie(cdp)
        with tol:                                          # le premier POST, deja parti, peut arriver chez le serveur APRES /ferme : 409 « aucune session », voulu
            lance()
            limite = time.monotonic() + 10
            while time.monotonic() < limite and not posts(cdp, route):
                time.sleep(0.1)
            clique(cdp, "b-deco")
            time.sleep(3.5)
            attend(cdp, "window.__fait >= window.__posts.length", 30)   # le POST parti doit avoir recu sa reponse (son 409 eventuel) avant la fin de la tolerance
        verifie(len(posts(cdp, route)), 1, libelle + " : plus aucun POST d'ecriture apres Deconnecter")
        verifie(all((racine / n).exists() for n in intacts), True, libelle + " : les elements suivants n'ont pas ete touches")
        cdp.js("window.__lent=0; 0")
        pastille(cdp, "eteint", 10)
        choisit(cdp)

    for n in ("s1.txt", "s2.txt", "s3.txt", "m1.txt", "m2.txt", "m3.txt"):
        b.fichier("/" + n)
    relit(cdp, "s3.txt")

    def lance_supprime():
        for n in ("s1.txt", "s2.txt", "s3.txt"):
            coche(cdp, n)
        clique(cdp, "b-supp")
        clique(cdp, "boite-ok")
    coupe("/supprime", lance_supprime, "suppression de 3 fichiers", ("s2.txt", "s3.txt"))
    relit(cdp, "m3.txt")

    def lance_deplace():
        for n in ("m1.txt", "m2.txt", "m3.txt"):
            coche(cdp, n)
        clique(cdp, "b-dep")
        champ(cdp, "/json")
        clique(cdp, "boite-ok")
    coupe("/deplace", lance_deplace, "deplacement de 3 fichiers", ("m2.txt", "m3.txt"))
    relit(cdp, "m2.txt")
    coupe("/envoie", lambda: pose_fichiers(cdp, [("e1.bin", 10), ("e2.bin", 10), ("e3.bin", 10)]), "envoi de 3 fichiers", ())
    verifie(((racine / "e2.bin").exists(), (racine / "e3.bin").exists()), (False, False), "envoi de 3 fichiers : les fichiers suivants ne sont pas partis")

    # geste : la session meurt (gen change) pendant la SECONDE boite, boite laissee ouverte : la confirmation n'envoie pas le second POST
    b.fichier("/autoexec.be")
    relit(cdp, "autoexec.be")
    oublie(cdp)
    calme(cdp)
    coche(cdp, "autoexec.be")
    clique(cdp, "b-supp")
    with tol:
        clique(cdp, "boite-ok")
        verifie(boite_seconde(cdp), True, "seconde boite ouverte (fichier protege)")
    verifie(tol.n >= 1, True, "seconde boite : le premier appel a bien recu le 409 de seconde confirmation")
    cdp.js("S.fermeBoite = null; S.gen++; 0")                # comme un sondage qui voit la session changer sans pouvoir fermer la boite
    clique(cdp, "boite-ok")
    time.sleep(1.5)
    verifie((confirmations(cdp, "/supprime"), (racine / "autoexec.be").exists()), ([1], True), "geste mort pendant la seconde boite : aucun second appel, le fichier est toujours la")
    calme(cdp, False)
    cdp.js("sonde(true)")

    # garde de reponse /etat perimee : une reponse partie AVANT un ouvrir (support sd) arrive APRES (support flash) : la page reste sur la flash
    relit(cdp, "m2.txt")
    calme(cdp, "force")
    cdp.js("window.__lentEtat=1500; 0")
    cdp.js("sonde(true)")                                    # la requete part maintenant, sur la SD ; sa reponse arrivera dans 1,5 s
    clique(cdp, "b-flash")
    verifie(bool(attend(cdp, "document.getElementById('pastille').textContent.indexOf('Flash') >= 0 && document.getElementById('pastille').getAttribute('data-etat')==='actif'", 15)),
            True, "reponse /etat perimee : la page passe sur la flash")
    time.sleep(2.5)
    verifie((cdp.js("document.getElementById('pastille').textContent.indexOf('Flash') >= 0"), "autre onglet" in texte(cdp, "msg")), (True, False),
            "reponse /etat perimee (partie avant l'ouverture) : ignoree, la page reste sur la flash")
    calme(cdp, False)
    clique(cdp, "b-sd")
    pastille(cdp, "actif", 8)
    attend_sonde(cdp, "document.getElementById('pastille').textContent.indexOf('SD') >= 0", 25)
    verifie(tol.restantes(), [], "aucune erreur de page dans le tour de corrections, hors les 409 voulus")
