"""Suite de la sonde Chrome du navigateur FTP des cartes (test_ftp_cartes_page_chrome.py, qui l'appelle en fin de scenario).

Cas de la tache A8 : identifiant d'onglet (/etat, /ouvre, beacon pagehide, DEUX pages), seconde confirmation du deplacement et
des dossiers contenant un fichier protege, paire env/support du zip et du telechargement, arret au premier refus des boucles
multi-fichiers, mineurs de la page (message ecrase par un geste interrompu, boite fermee par ouvrir/deconnecter, envoi unique
d'un fichier qui existe deja). Contient aussi les petites aides de la sonde (coche, clique, noms, pose_fichiers).
Ce module n'importe rien de la sonde principale : elle recoit `tol` (les 409 voulus) en parametre.
"""
import json
import time
import urllib.request

import ftp_cartes_liste
import test_ftp_cartes_web as banc_web
from test_build_page_chrome import Cdp, attend

verifie = banc_web.verifie
ENV = banc_web.ENV
GROS = 11                                         # taille des fichiers « petit.bin » envoyes pour ecraser celui de la carte (2 octets)


def coche(cdp, nom):
    cdp.js("(function(){var r=Array.prototype.find.call(document.querySelectorAll('#lignes tr'),function(t){return t.getAttribute('data-nom')===" + json.dumps(nom)
           + "}); r.querySelector('input').click();})()")


def noms(cdp):
    return cdp.js("Array.prototype.map.call(document.querySelectorAll('#lignes tr'),function(t){return t.getAttribute('data-nom')})")


def pose_fichiers(cdp, specs):
    """Fichiers synthetiques [(nom, octets)] dans l'input #fichier puis evenement change (aucun fichier reel)."""
    cdp.js("(function(){var d=new DataTransfer();" + "".join("d.items.add(new File([new Uint8Array(%d)],%s));" % (n, json.dumps(nom)) for nom, n in specs)
           + "var i=document.getElementById('fichier'); i.files=d.files; i.dispatchEvent(new Event('change',{bubbles:true}));})()")


def clique(cdp, ident):
    cdp.js("document.getElementById(" + json.dumps(ident) + ").click()")


def champ(cdp, valeur):
    cdp.js("document.getElementById('boite-champ').value=" + json.dumps(valeur))


# ---- aides propres a ces cas ----------------------------------------------------------------------------------------------
def ident(cdp):
    v = cdp.js("typeof ONGLET==='string' ? ONGLET : ''")
    return v if isinstance(v, str) else ""


def vus(b):
    return dict(b.session.onglets._vus)                  # identifiant -> derniere vue : ce que le serveur sait des onglets


def attend_sonde(cdp, expression, delai=25, pas=1.0):
    """Attend une condition qui depend du sondage de la page. Un sondage FORCE part a chaque tour : ni le tick de 5 s, ni la charge de la machine ne comptent
    (avec une duree fixe de 12 s, un sondage ralenti faisait rougir la sonde par intermittence). Le delai est un maximum, pas une attente."""
    limite = time.monotonic() + delai
    while True:
        v = cdp.js(expression)
        if v and not (isinstance(v, dict) and "_exception_sonde" in v):
            return v
        if time.monotonic() >= limite:
            return v
        cdp.js("sonde(true)")
        time.sleep(pas)


def pastille(cdp, etat, delai=12):
    return bool(attend_sonde(cdp, "document.getElementById('pastille').getAttribute('data-etat')===" + json.dumps(etat), max(delai, 25)))


def calme(cdp, oui=True):
    """Coupe (ou remet) le sondage de la page : le serveur et la page ne se croisent plus qu'aux moments voulus.
    oui="force" : seuls les sondages FORCES (api() apres un 409, appel direct `sonde(true)`) passent, pas les tours de l'intervalle."""
    corps = {True: "function(){}", False: "window.__sonde", "force": "function(f){ if (f) return window.__sonde(f); }"}[oui]
    cdp.js("window.__sonde=window.__sonde||window.sonde; window.sonde=" + corps + "; 0")


def choisit(cdp):
    cdp.js("var s=document.getElementById('carte'); s.value=" + json.dumps(ENV) + "; s.dispatchEvent(new Event('change',{bubbles:true}))")
    return pastille(cdp, "actif", 15)


def a_ligne(nom):
    return ("!!Array.prototype.find.call(document.querySelectorAll('#lignes tr'),function(t){return t.getAttribute('data-nom')===" + json.dumps(nom) + "})")


def relit(cdp, nom):
    """Relit la racine et attend la liste NOUVELLE (S.occupe retombe a 0) avec la ligne `nom` : sans cela la liste d'avant, encore affichee, satisfait l'attente."""
    cdp.js("document.querySelector('#arbre button[data-chemin=\"/\"]').click()")
    return bool(attend(cdp, "S.occupe === 0 && document.getElementById('fil').textContent==='/' && " + a_ligne(nom), 10))


def espionne(cdp):
    """Journal des POST de la page (url + corps) dans window.__posts et de TOUTES ses requetes dans window.__req ('METHODE url'), remis a zero par `oublie`.
    window.__lent : delai (ms) impose a la reponse de chaque POST ; window.__lentEtat : delai impose a la reponse du PROCHAIN GET /etat (la requete part tout de suite) ; window.__lentEtatTous : delai de TOUS les GET /etat."""
    cdp.js("window.__posts=[]; window.__req=[]; window.__fait=0; if(!window.__f3){window.__f3=window.fetch; window.fetch=function(u,o){ var m=(o&&o.method)||'GET', s=String(u), d=0;"
           " window.__req.push(m+' '+s); if(m==='POST') window.__posts.push({u:s,b:(o&&typeof o.body==='string')?o.body:'<blob>'});"
           " var r=window.__f3.apply(this,arguments); if(m==='POST'){var f=function(){window.__fait=(window.__fait||0)+1}; r.then(f,f);}"
           " if(m==='POST') d=window.__lent||0; else if(/[/]etat/.test(s)){d=window.__lentEtat||window.__lentEtatTous||0; window.__lentEtat=0;}"
           " return d ? new Promise(function(ok,ko){setTimeout(function(){r.then(ok,ko)},d)}) : r;};} 0")


def oublie(cdp):
    cdp.js("window.__posts=[]; window.__req=[]; window.__fait=0; 0")


def posts(cdp, route):
    return [p for p in cdp.js("window.__posts") if p["u"].startswith(route)]


def confirmations(cdp, route):
    return [json.loads(p["b"]).get("confirmations") for p in posts(cdp, route)]


def attend_ufs(b, condition, delai):
    limite = time.monotonic() + delai
    while time.monotonic() < limite and not condition(b.ufsftp()):
        time.sleep(0.2)


def boite_seconde(cdp, delai=10):
    return bool(attend(cdp, "!document.getElementById('boite').hidden && document.getElementById('boite-texte').textContent.indexOf('Seconde confirmation') >= 0", delai))


def texte(cdp, ident_):
    return cdp.js("document.getElementById(" + json.dumps(ident_) + ").textContent")


def seconde_page(m):
    """Ouvre une seconde page dans le meme Chrome et rend son Cdp (ou None)."""
    cible = m.cdp.appel("Target.createTarget", url=m.url)["targetId"]
    limite = time.monotonic() + 10
    while time.monotonic() < limite:
        with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % m.port_cdp, timeout=3) as r:
            for c in json.loads(r.read().decode("utf-8")):
                if c.get("id") == cible:
                    cdp2 = Cdp(c["webSocketDebuggerUrl"])
                    cdp2.appel("Runtime.enable")
                    return cible, cdp2
        time.sleep(0.2)
    return cible, None


def scenario_onglets(m, tol):
    # Ces cas ferment ou changent la session sous la page a dessein : une relecture de liste de la page en vol peut atterrir apres, et le serveur la
    # refuse en 409 (« aucune session » ou changee). C'est un 409 voulu, qu'aucun bloc `with tol` ne peut dater : ceux de /liste sont toleres ICI
    # seulement ; la suite (test_ftp_cartes_page_chrome_corrections.py) retrouve la regle stricte.
    tol.liste_tolere(True)
    try:
        _scenario_onglets(m, tol)
    finally:
        tol.liste_tolere(False)


def _scenario_onglets(m, tol):
    cdp, b = m.cdp, m.banc
    racine = b.srv.racine
    b.srv.noms_pieges.clear()                                  # les noms pieges de la sonde principale s'ajoutent a TOUTE liste, dossiers compris
    cdp.appel("Emulation.setDeviceMetricsOverride", width=1280, height=1000, deviceScaleFactor=1, mobile=False)
    calme(cdp, False)                                          # le sondage de la page 1 avait ete coupe pour la fermeture reelle d'un onglet
    espionne(cdp)

    # P1 : identifiant d'onglet
    mon = ident(cdp)
    verifie(len(mon) == 32 and all(c in "0123456789abcdef" for c in mon), True, "onglet : identifiant de 32 caracteres hexadecimaux minuscules")
    t0 = vus(b).get(mon, -1)                                  # sans vider le registre : l'heure de derniere vue de CET onglet doit avancer
    cdp.js("sonde(true)")
    attend_vu = time.monotonic() + 5
    while time.monotonic() < attend_vu and vus(b).get(mon, -1) <= t0:
        time.sleep(0.2)
    verifie(mon != "" and vus(b).get(mon, -1) > t0, True, "onglet : GET /etat porte l'identifiant")
    # un geste long (zip) suspend le sondage : l'onglet continue de se signaler (sinon le serveur le croit parti apres 90 s)
    t0 = vus(b).get(mon, 0)
    cdp.js("S.occupe=1; 0")                                   # le sondage ne passe plus que par le battement ; on attend qu'il arrive (condition observable)
    limite = time.monotonic() + 20
    while time.monotonic() < limite and vus(b).get(mon, 0) <= t0:
        time.sleep(0.25)
    cdp.js("S.occupe=0; 0")
    verifie(vus(b).get(mon, 0) > t0, True, "onglet : le sondage suspendu par un geste long continue de signaler l'onglet")
    calme(cdp)
    time.sleep(0.6)                                           # un sondage parti avant `calme` a le temps d'arriver
    t0 = vus(b).get(mon, -1)
    choisit(cdp)
    verifie(mon != "" and vus(b).get(mon, -1) > t0, True, "onglet : POST /ouvre porte l'identifiant (sans sondage)")
    calme(cdp, False)

    # P1 : deux pages. Fermer l'une laisse le FTP allume, fermer la derniere l'eteint.
    cible2, cdp2 = seconde_page(m)
    mon2 = ident(cdp2) if cdp2 else ""
    if cdp2:
        attend(cdp2, "typeof ONGLET==='string'", 15)
        mon2 = ident(cdp2)
        limite = time.monotonic() + 8
        while time.monotonic() < limite and mon2 not in vus(b):
            time.sleep(0.2)
    verifie(mon2 != "" and mon2 != mon and {mon, mon2} <= set(vus(b)), True, "deux pages : deux identifiants distincts connus du serveur")
    calme(cdp)                                                # page 1 ne se re-signale pas entre-temps
    if cdp2:
        calme(cdp2)                                           # page 2 non plus : seul le registre du serveur la garde
    # C4 : la page 1 change de carte (meme requete que son POST /ouvre, vers une seconde carte du faux serveur) : la page 2 reste connue
    carte = dict(ftp_cartes_liste.liste(b.racine)["cartes"][0], adresse="localhost", env="autre")
    b.session.ouvre_ou_reprend(carte, "sd", mon)
    verifie((b.session.etat()["env"], mon2 in vus(b)), ("autre", True), "changement de carte par la page 1 : la page 2 reste dans le registre")
    n0 = len(b.ufsftp())
    cdp.js("window.dispatchEvent(new PageTransitionEvent('pagehide'))")
    limite = time.monotonic() + 5
    while time.monotonic() < limite and mon in vus(b):
        time.sleep(0.2)
    verifie(mon in vus(b), False, "deux pages : le beacon de la page 1 retire son identifiant")
    time.sleep(1)
    verifie((b.session.etat()["etat"], b.ufsftp()[n0:]), ("actif", []), "deux pages, apres un changement de carte de la page 1 : la fermer laisse le FTP allume pour la page 2 (pas de UfsFTP 0)")
    if cdp2:
        cdp2.js("window.dispatchEvent(new PageTransitionEvent('pagehide'))")
    attend_ufs(b, lambda u: len(u) > n0 and u[-1] == 0, 8)
    verifie((b.ufsftp()[n0:], b.session.etat()["etat"]), ([0], "eteint"), "deux pages : fermer la derniere eteint le FTP")
    try:
        cdp.appel("Target.closeTarget", targetId=cible2)
    except Exception:
        pass
    calme(cdp, False)
    cdp.js("sonde(true)")
    pastille(cdp, "eteint", 8)

    # P1 : « Deconnecter » ferme malgre un autre onglet connu du serveur
    choisit(cdp)
    b.req("GET", "/etat?onglet=" + "cd" * 16)
    n0 = len(b.ufsftp())
    clique(cdp, "b-deco")
    attend_ufs(b, lambda u: len(u) > n0 and u[-1] == 0, 8)
    verifie((b.ufsftp()[n0:], b.session.etat()["etat"]), ([0], "eteint"), "Deconnecter : ferme malgre un autre onglet (sans identifiant)")

    # ---- fixtures du reste ------------------------------------------------------------------------------------------
    for nom in ("a.txt", "b.txt", "autoexec.be", "petit.bin"):
        b.fichier("/" + nom, b"zz")
    b.fichier("/json/a.txt")
    b.fichier("/dossprot/autoexec.be")
    b.fichier("/dp2/autoexec.be")
    choisit(cdp)
    relit(cdp, "dp2")
    oublie(cdp)

    def rnfr():
        return sum(1 for c, _ in b.srv.commandes if c == "RNFR")

    # P2 : deplacer un fichier protege : 1 confirmation = refus, la boite demande la SECONDE (texte de deplacement), 2 = deplace
    coche(cdp, "autoexec.be")
    clique(cdp, "b-dep")
    champ(cdp, "/json")
    n0 = rnfr()
    with tol:
        clique(cdp, "boite-ok")
        verifie(boite_seconde(cdp), True, "deplacer un fichier protege : une seconde confirmation est demandee")
    verifie(tol.n >= 1, True, "deplacer un fichier protege : le serveur a bien rendu un 409")
    t = texte(cdp, "boite-texte")
    verifie(("déplacer" in t, "protégé" in t, "supprim" in t, "/json" in t), (True, True, False, True), "seconde confirmation du deplacement : le texte parle d'un deplacement")
    verifie(((racine / "autoexec.be").exists(), rnfr()), (True, n0), "apres 1 confirmation : rien n'est deplace, aucun RNFR")
    clique(cdp, "boite-ok")
    verifie(bool(attend(cdp, "!" + a_ligne("autoexec.be"), 10)), True, "apres 2 confirmations : retire de la liste")
    verifie(((racine / "json" / "autoexec.be").exists(), (racine / "autoexec.be").exists()), (True, False), "apres 2 confirmations : deplace sur la carte")
    verifie(confirmations(cdp, "/deplace"), [1, 2], "deplacement : premier appel avec confirmations 1, second avec 2")
    corps = json.loads(posts(cdp, "/deplace")[0]["b"])
    verifie((corps.get("env"), corps.get("support")), (ENV, "sd"), "deplacement : la paire env/support part avec le geste")

    # P2 : cible existante : le texte du serveur, aucune boite ; arret au premier refus de la boucle multi-fichiers
    oublie(cdp)
    coche(cdp, "a.txt")
    coche(cdp, "b.txt")
    clique(cdp, "b-dep")
    champ(cdp, "/json")
    with tol:
        clique(cdp, "boite-ok")
        verifie(bool(attend(cdp, "document.getElementById('msg').textContent.indexOf('existe deja') >= 0", 10)), True, "cible existante : le texte du serveur est affiche")
    verifie(tol.n >= 1, True, "cible existante : le serveur a bien rendu un 409")
    verifie(cdp.js("document.getElementById('boite').hidden"), True, "cible existante : aucune boite de confirmation")
    verifie(len(posts(cdp, "/deplace")), 1, "deplacement de 2 fichiers : arret au premier refus (un seul appel)")
    verifie(((racine / "b.txt").exists(), (racine / "a.txt").exists()), (True, True), "cible existante : rien n'a bouge")

    # P3 : dossier contenant un fichier protege, supprime (2 confirmations) puis deplace (annule a la seconde)
    relit(cdp, "dossprot")
    oublie(cdp)
    coche(cdp, "dossprot")
    clique(cdp, "b-supp")
    with tol:
        clique(cdp, "boite-ok")
        verifie(boite_seconde(cdp), True, "dossier contenant un fichier protege : seconde confirmation de la suppression")
    verifie((racine / "dossprot" / "autoexec.be").exists(), True, "apres 1 confirmation : le dossier est la")
    clique(cdp, "boite-ok")
    verifie(bool(attend(cdp, "!" + a_ligne("dossprot"), 10)), True, "dossier protege : retire de la liste apres 2 confirmations")
    verifie(((racine / "dossprot").exists(), confirmations(cdp, "/supprime")), (False, [1, 2]), "dossier protege : supprime sur la carte, confirmations 1 puis 2")
    oublie(cdp)
    coche(cdp, "dp2")
    clique(cdp, "b-dep")
    champ(cdp, "/json")
    with tol:
        clique(cdp, "boite-ok")
        verifie(boite_seconde(cdp), True, "dossier contenant un fichier protege : seconde confirmation du deplacement")
    clique(cdp, "boite-non")
    verifie(bool(attend(cdp, "document.getElementById('msg').textContent.indexOf('annulé') >= 0", 10)), True, "deplacement annule a la seconde confirmation : message")
    verifie(((racine / "dp2" / "autoexec.be").exists(), len(posts(cdp, "/deplace"))), (True, 1), "deplacement annule : le dossier n'a pas bouge")

    # P4 : le lien de telechargement et le zip portent la paire env/support ; un 409 « session a change » est traite
    relit(cdp, "a.txt")
    cdp.js("window.__lien=null; window.__blob=null; 0")
    coche(cdp, "a.txt")
    clique(cdp, "b-zip")
    lien = cdp.js("window.__lien")
    verifie(lien and lien["href"], "/telecharge?chemin=%2Fa.txt&env=" + ENV + "&support=sd", "telechargement : le lien porte env et support")
    coche(cdp, "a.txt")
    coche(cdp, "b.txt")
    coche(cdp, "dp2")
    calme(cdp)
    n0 = sum(1 for c, _ in b.srv.commandes if c == "RETR")
    verifie(b.ouvre("flash")[0], 200, "zip : l'autre onglet passe sur la flash")
    with tol:
        clique(cdp, "b-zip")
        verifie(bool(attend_sonde(cdp, "document.getElementById('msg').textContent.indexOf('autre onglet') >= 0", 25)), True, "zip d'une session perimee : message « autre onglet »")
    verifie(tol.n >= 1, True, "zip d'une session perimee : le serveur a bien rendu un 409")
    verifie((cdp.js("window.__blob"), sum(1 for c, _ in b.srv.commandes if c == "RETR")), (None, n0), "zip d'une session perimee : aucun zip produit, aucun RETR")
    calme(cdp, False)
    cdp.js("sonde(true)")
    verifie(bool(attend_sonde(cdp, "document.getElementById('pastille').textContent.indexOf('Flash') >= 0 && document.querySelectorAll('#lignes tr input:checked').length === 0", 25)),
            True, "zip d'une session perimee : la page suit la nouvelle session, aucune case cochee")
    b.ouvre("sd")
    cdp.js("sonde(true)")
    pastille(cdp, "actif", 8)
    attend_sonde(cdp, "document.getElementById('pastille').textContent.indexOf('SD') >= 0", 25)

    # B15 : un fichier deja dans la liste affichee : la boite s'ouvre AVANT l'envoi du corps (un seul envoi, avec ecraser=1)
    relit(cdp, "petit.bin")
    oublie(cdp)
    pose_fichiers(cdp, [("petit.bin", GROS)])
    verifie(bool(attend(cdp, "!document.getElementById('boite').hidden && document.getElementById('boite-texte').textContent.indexOf('existe déjà') >= 0", 10)), True,
            "fichier existant : la boite « ecraser » s'ouvre")
    verifie(len(posts(cdp, "/envoie")), 0, "fichier existant : aucun corps envoye tant que l'ecrasement n'est pas confirme")
    clique(cdp, "boite-non")
    verifie(bool(attend(cdp, "document.getElementById('msg').textContent.indexOf('Aucun fichier') >= 0", 10)), True, "ecrasement refuse : « Aucun fichier envoye » (pas « Envoye : 0 »)")
    oublie(cdp)
    pose_fichiers(cdp, [("petit.bin", GROS)])
    attend(cdp, "!document.getElementById('boite').hidden", 10)
    clique(cdp, "boite-ok")
    verifie(bool(attend(cdp, "document.getElementById('msg').textContent.indexOf('Envoyé : 1') >= 0", 10)), True, "ecrasement confirme : « Envoye : 1 fichier »")
    env_posts = posts(cdp, "/envoie")
    verifie((len(env_posts), "ecraser=1" in env_posts[0]["u"] if env_posts else None), (1, True), "ecrasement confirme : un seul envoi, avec ecraser=1")
    verifie((racine / "petit.bin").stat().st_size, GROS, "ecrasement confirme : le fichier de la carte est remplace")

    # P5a : la session se ferme ailleurs pendant la boite « ecraser » : le message du sondage n'est pas ecrase
    relit(cdp, "petit.bin")
    pose_fichiers(cdp, [("petit.bin", GROS)])
    attend(cdp, "!document.getElementById('boite').hidden", 10)
    b.json("POST", "/ferme", {})
    cdp.js("sonde(true)")
    verifie(bool(attend(cdp, "!!document.getElementById('msg-action')", 10)), True, "session fermee pendant la boite : bouton Rallumer propose")
    time.sleep(1.2)
    verifie((cdp.js("!!document.getElementById('msg-action')"), "Envoy" in texte(cdp, "msg"), cdp.js("document.getElementById('boite').hidden")), (True, False, True),
            "session fermee pendant un geste : le message du sondage survit (pas de « Envoye : 0 »), la boite est fermee")
    verifie(cdp.js("document.getElementById('fichier').value"), "", "envoi abandonne : le champ fichier est vide (re-choisir le meme fichier redeclenche change)")
    clique(cdp, "msg-action")
    pastille(cdp, "actif", 12)
    # P5a : l'autre onglet change de support pendant la seconde confirmation d'une suppression
    b.fichier("/autoexec.be")
    relit(cdp, "autoexec.be")
    coche(cdp, "autoexec.be")
    clique(cdp, "b-supp")
    with tol:
        clique(cdp, "boite-ok")
        boite_seconde(cdp)
    b.ouvre("flash")
    cdp.js("sonde(true)")
    verifie(bool(attend_sonde(cdp, "document.getElementById('msg').textContent.indexOf('autre onglet') >= 0", 25)), True, "support change pendant la seconde confirmation : message « autre onglet »")
    time.sleep(1.2)
    verifie(("autre onglet" in texte(cdp, "msg"), "annulée" in texte(cdp, "msg"), (racine / "autoexec.be").exists()), (True, False, True),
            "support change pendant un geste : le message n'est pas ecrase par « annulee », rien supprime")
    b.ouvre("sd")
    cdp.js("sonde(true)")
    pastille(cdp, "actif", 8)
    attend_sonde(cdp, "document.getElementById('pastille').textContent.indexOf('SD') >= 0", 25)

    # P5c : ouvrir et deconnecter ferment une boite de confirmation ouverte
    calme(cdp)
    relit(cdp, "a.txt")
    coche(cdp, "a.txt")
    clique(cdp, "b-supp")
    verifie(cdp.js("document.getElementById('boite').hidden"), False, "boite ouverte avant le changement de support")
    clique(cdp, "b-flash")
    verifie(bool(attend(cdp, "document.getElementById('boite').hidden", 5)), True, "ouvrir : ferme la boite de confirmation ouverte")
    pastille(cdp, "actif", 8)
    relit(cdp, "a.txt")
    coche(cdp, "a.txt")
    clique(cdp, "b-supp")
    clique(cdp, "b-deco")
    verifie(bool(attend(cdp, "document.getElementById('boite').hidden", 5)), True, "deconnecter : ferme la boite de confirmation ouverte")
    verifie((racine / "a.txt").exists(), True, "boite fermee par ouvrir ou deconnecter : rien n'est supprime")
    pastille(cdp, "eteint", 8)

    # P5b : un 200 non JSON a l'allumage vide aussi les vues
    calme(cdp, False)
    choisit(cdp)
    relit(cdp, "a.txt")
    calme(cdp)
    cdp.js("window.__fetch2=window.fetch; window.fetch=function(u){ return /ouvre/.test(String(u)) ? Promise.resolve(new Response('oups', {status: 200})) : window.__fetch2.apply(this, arguments); }; 0")
    cdp.js("ouvrir(S.etat.env, 'sd', true)")
    verifie(bool(attend(cdp, "document.getElementById('msg').textContent.indexOf('illisible') >= 0", 10)), True, "allumage non JSON : message lisible")
    verifie(cdp.js("document.querySelectorAll('#lignes tr').length"), 0, "allumage non JSON : le tableau est vide")
    cdp.js("window.fetch=window.__fetch2; 0")
    calme(cdp, False)
    cdp.js("sonde(true)")
    pastille(cdp, "actif", 10)

    # l'arret au premier 409 de la suppression de plusieurs fichiers
    relit(cdp, "a.txt")
    oublie(cdp)
    coche(cdp, "a.txt")
    coche(cdp, "b.txt")
    calme(cdp)
    clique(cdp, "b-supp")
    cdp.js("S.fermeBoite = null")                                    # la boite reste ouverte : la confirmation part avec l'ANCIENNE session
    verifie(b.ouvre("flash")[0], 200, "suppression multiple : l'autre onglet passe sur la flash")
    with tol:
        clique(cdp, "boite-ok")
        attend_sonde(cdp, "document.getElementById('msg').textContent.indexOf('autre onglet') >= 0", 25)
    verifie(tol.n >= 1, True, "suppression multiple : le serveur a bien rendu un 409")
    time.sleep(0.5)
    verifie((len(posts(cdp, "/supprime")), (racine / "a.txt").exists(), (racine / "b.txt").exists()), (1, True, True),
            "suppression multiple : arret au premier 409 (un seul appel), rien supprime")
    calme(cdp, False)
    b.ouvre("sd")
    cdp.js("sonde(true)")
    pastille(cdp, "actif", 8)

    verifie(tol.restantes(), [], "aucune erreur de page dans les cas des onglets, hors les 409 voulus")
