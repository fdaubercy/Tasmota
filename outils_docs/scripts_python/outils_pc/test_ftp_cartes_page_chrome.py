"""Sonde Chrome de la page du navigateur FTP des cartes (ftp_cartes_page.PAGE). Code de sortie 0 = vert.

Hermetique : serveur de l'outil sur un port libre (jamais 7450) + faux serveur FTP de carte + fausse commande `UfsFTP` + mini-depot
temporaire (`test_ftp_cartes_web.Banc`), Chrome headless au profil `sonde_ftp_cartes_*`. Aucune vraie carte, rien d'ecrit dans le depot.
Suite des cas (onglets, deplacement, zip) : test_ftp_cartes_page_chrome_onglets.py.
Verifie : choix d'une carte (pastille « actif »), liste de /histo, noms speciaux (accent, espace, #, balise hostile) affiches tels quels,
zip du navigateur, suppression d'un fichier protege (1 confirmation : toujours la ; 2 : supprime), nouveau dossier, bascule Flash / SD
(SD grisee sans SD), fermeture de l'onglet (le faux serveur recoit `UfsFTP 0`), mode sombre, telephone, aucune erreur de console.

UTILISATION (Chrome tourne ~25 s)
    <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_ftp_cartes_page_chrome.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
import acces_barre                                                                  # noqa: E402
import ftp_cartes_page as page_mod                                                  # noqa: E402
import test_ftp_cartes_web as banc_web                                              # noqa: E402
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre, tue_arbre      # noqa: E402
from test_ftp_cartes_page_chrome_onglets import attend_sonde, attend_ufs, calme, clique, coche, espionne, ident, noms, oublie, pose_fichiers, posts, scenario_onglets, vus   # noqa: E402
from test_ftp_cartes_page_chrome_corrections import corrections, relectures   # noqa: E402

ECHECS = []
HOSTILE = "<img src=x onerror=window.__pwn=1>.txt"
SPECIAL = "é a#b.bin"
verifie = banc_web.verifie


class Montage:
    def __init__(self):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_ftp_cartes_"))
        self.chrome = None
        self.banc = banc_web.Banc()
        # Hermetique : la barre de acces_web.habille lirait les vraies fiches de presence et sonderait 7700 (page Build reelle).
        acces_barre.outils_vivants = lambda: []
        acces_barre._occupe = lambda *a: False
        acces_barre._CACHE["donnees"] = None
        self.url = f"http://127.0.0.1:{self.banc.port}/"
        chrome = next((c for c in CHROMES if c.is_file()), None)
        if chrome is None:
            raise FileNotFoundError("chrome.exe introuvable")
        port_cdp = self.port_cdp = port_libre()
        self.chrome = subprocess.Popen([str(chrome), "--headless=new", f"--remote-debugging-port={port_cdp}", "--remote-allow-origins=*",
                                        f"--user-data-dir={self.t / 'profil'}", "--no-first-run", "--no-default-browser-check",
                                        "--disable-extensions", "--window-size=1280,1000", "about:blank"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cibles = self._attend(f"http://127.0.0.1:{port_cdp}/json/list", 20)
        self.cdp = Cdp(next(c for c in json.loads(cibles) if c.get("type") == "page")["webSocketDebuggerUrl"])
        for domaine in ("Runtime.enable", "Log.enable", "Page.enable", "Network.enable"):
            self.cdp.appel(domaine)

    @staticmethod
    def _attend(url, delai):
        limite = time.monotonic() + delai
        while time.monotonic() < limite:
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    return r.read().decode("utf-8")
            except OSError:
                time.sleep(0.2)
        raise TimeoutError(f"{url} ne repond pas")

    def ferme(self):
        if self.chrome:
            tue_arbre(self.chrome)
        commande = ("$p = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'chrome.exe' -and $_.CommandLine -like '*" + self.t.name
                    + "*' }); $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; $p.Count")
        for _ in range(8):
            r = subprocess.run(["powershell", "-NoProfile", "-Command", commande], capture_output=True, text=True)
            if r.stdout.strip() == "0":
                break
            time.sleep(0.7)
        if getattr(self, "banc", None):
            self.banc.__exit__()
            shutil.rmtree(self.banc.racine, ignore_errors=True)
        shutil.rmtree(self.t, ignore_errors=True)


class Tolere:
    """Les 409 voulus sont des lignes du journal reseau de Chrome : on ne tolere que ceux apparus pendant un bloc annonce."""
    def __init__(self, cdp):
        self.cdp, self.ok, self.debut, self.n, self.liste_ok = cdp, set(), 0, 0, False      # n : 409 apparus pendant le dernier bloc (un 409 voulu qui n'arrive pas est un echec)

    def __enter__(self):
        time.sleep(0.3)
        self.debut = len(self.cdp.erreurs())

    def _stable(self):
        time.sleep(0.5)
        stable, derniere = 0, -1                           # les lignes du journal Chrome arrivent en differe : on attend qu'elles ne bougent plus (3 s au plus)
        limite = time.monotonic() + 3
        while stable < 2 and time.monotonic() < limite:
            n = len(self.cdp.erreurs())
            stable = stable + 1 if n == derniere else 0
            derniere = n
            time.sleep(0.25)

    def liste_tolere(self, oui):
        """Tolere (oui) ou non les 409 de /liste. Au retour a False, ceux deja arrives restent toleres, les suivants non."""
        if not oui:
            self._stable()
            self.ok.update(i for i, e in enumerate(self.cdp.erreurs()) if "409" in e and "/liste" in e)
        self.liste_ok = oui

    def __exit__(self, *_):
        self._stable()
        self.n = 0
        for i, e in enumerate(self.cdp.erreurs()):
            if i >= self.debut and "409" in e:
                self.ok.add(i)
                self.n += 1

    def restantes(self):
        return [e for i, e in enumerate(self.cdp.erreurs()) if i not in self.ok and not (self.liste_ok and "409" in e and "/liste" in e)]


def scenario(m):
    cdp, b = m.cdp, m.banc
    tol = Tolere(cdp)
    (b.srv.racine / "histo").mkdir()
    (b.srv.racine / "json").mkdir()
    (b.srv.racine / "histo" / "mesures-2026-11.bin").write_bytes(b"x" * 2048)
    (b.srv.racine / "histo" / SPECIAL).write_bytes(b"y" * 10)
    (b.srv.racine / "autoexec.be").write_bytes(b"var a = 1\n")
    b.srv.noms_pieges.append(HOSTILE)
    cdp.appel("Emulation.setDeviceMetricsOverride", width=1280, height=1000, deviceScaleFactor=1, mobile=False)

    # theme sombre quand le systeme le demande ; arrivee par ?lieu=
    cdp.appel("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "dark"}])
    cdp.appel("Page.navigate", url=m.url + "?lieu=garage")
    attend(cdp, "document.querySelectorAll('#carte option').length >= 2", 15)
    verifie(cdp.js("document.title"), "Navigateur FTP des cartes", "titre")
    verifie(cdp.js("document.documentElement.getAttribute('data-theme')"), "sombre", "theme : sombre quand le systeme est sombre")
    verifie(cdp.js("document.getElementById('lieu').value"), "garage", "?lieu=garage : le lieu est choisi")
    verifie(cdp.js("Array.prototype.map.call(document.querySelectorAll('#carte option'),function(o){return o.value}).join()"), "," + banc_web.ENV,
            "liste des cartes : le choix vide puis la carte du lieu")
    verifie(cdp.js("document.getElementById('pastille').getAttribute('data-etat')"), "eteint", "au depart : FTP eteint")
    verifie(b.ufsftp(), [], "au depart : aucun UfsFTP envoye")

    # choix d'une carte : pastille actif, racine listee, arbre
    cdp.js("var s=document.getElementById('carte'); s.value=" + json.dumps(banc_web.ENV) + "; s.dispatchEvent(new Event('change',{bubbles:true}))")
    verifie(bool(attend(cdp, "document.getElementById('pastille').getAttribute('data-etat')==='actif'", 15)), True, "carte choisie : pastille « actif »")
    verifie(cdp.js("document.getElementById('pastille').textContent.indexOf('SD') >= 0"), True, "pastille : support SD")
    verifie(b.ufsftp(), [1], "le serveur a envoye UfsFTP 1 (SD)")
    attend(cdp, "document.querySelectorAll('#lignes tr').length > 0", 10)
    verifie(sorted(noms(cdp)), sorted(["autoexec.be", "histo", "json", "sd", HOSTILE]), "racine : fichiers et dossiers de la carte")
    verifie(cdp.js("document.querySelectorAll('#arbre button').length"), 4, "arbre : racine + 3 dossiers (histo, json, sd)")

    # Historique et energie : /histo, noms speciaux affiches tels quels
    clique(cdp, "b-histo")
    verifie(bool(attend(cdp, "document.getElementById('fil').textContent==='/histo' && document.querySelectorAll('#lignes tr').length>=3", 10)), True,
            "Historique et energie : /histo listé")
    verifie(SPECIAL in noms(cdp), True, "nom special (accent, espace, #) affiche")
    verifie(cdp.js("document.getElementById('lignes').textContent.indexOf(" + json.dumps(HOSTILE) + ") >= 0"), True, "nom hostile affiche tel quel")
    verifie(cdp.js("document.querySelectorAll('#lignes img').length === 0 && window.__pwn === undefined"), True, "nom hostile : aucune balise creee")

    # zip : telechargement de deux fichiers (dont le nom special)
    cdp.js("window.__blob=null; var o=URL.createObjectURL; URL.createObjectURL=function(b){window.__blob=b; return o.call(URL,b);};"
           " window.__lien=null; HTMLAnchorElement.prototype.click=function(){window.__lien={href:this.getAttribute('href'),nom:this.download};}")
    # un seul fichier : lien direct /telecharge (nom special encode), reponse 200 en piece jointe, contenu identique
    coche(cdp, SPECIAL)
    clique(cdp, "b-zip")
    lien = cdp.js("window.__lien")
    verifie(lien and lien["nom"], SPECIAL, "un fichier : le lien porte le nom du fichier")
    st, corps, ent = b.req("GET", lien["href"]) if lien else (0, b"", {})
    verifie(st, 200, "un fichier : /telecharge repond 200")
    verifie("attachment" in ent.get("Content-Disposition", ""), True, "un fichier : piece jointe")
    verifie(corps, (b.srv.racine / "histo" / SPECIAL).read_bytes(), "un fichier : contenu egal a celui de la carte")
    coche(cdp, SPECIAL)
    coche(cdp, "mesures-2026-11.bin")
    coche(cdp, SPECIAL)
    verifie(cdp.js("document.getElementById('b-zip').disabled"), False, "deux fichiers coches : zip possible")
    clique(cdp, "b-zip")
    verifie(bool(attend(cdp, "window.__blob !== null", 10)), True, "zip : un blob est produit")
    verifie(cdp.js("window.__blob.type"), "application/zip", "zip : type de fichier")
    verifie(cdp.js("window.__blob.arrayBuffer().then(function(a){return String.fromCharCode.apply(null,new Uint8Array(a).slice(0,2));})"), "PK", "zip : signature PK")

    # nouveau dossier
    clique(cdp, "b-dos")
    verifie(cdp.js("document.getElementById('boite').hidden"), False, "nouveau dossier : la boite s'ouvre")
    cdp.js("document.getElementById('boite-champ').value='essai'")
    clique(cdp, "boite-ok")
    attend(cdp, "document.querySelectorAll('#lignes tr[data-nom=essai]').length === 1", 10)
    verifie((b.srv.racine / "histo" / "essai").is_dir(), True, "nouveau dossier : cree sur la carte")

    # B1 : le message d'une erreur d'action survit au rafraichissement de la liste
    with tol:
        clique(cdp, "b-dos")
        cdp.js("document.getElementById('boite-champ').value='essai'")
        clique(cdp, "boite-ok")
        attend(cdp, "document.getElementById('msg').className === 'erreur'", 10)
    time.sleep(1)
    verifie(cdp.js("document.getElementById('msg').className"), "erreur", "dossier existant : le message d'erreur est toujours la 1 s apres")
    verifie(cdp.js("document.getElementById('lignes').querySelectorAll('tr').length >= 3"), True, "dossier existant : la liste a ete rafraichie")
    pose_fichiers(cdp, [("gros.bin", 16 * 1024 * 1024 + 1)])
    attend(cdp, "document.getElementById('msg').textContent.indexOf('16 Mo') >= 0", 10)
    time.sleep(1)
    verifie(cdp.js("document.getElementById('msg').textContent.indexOf('dépasse 16 Mo') >= 0"), True, "envoi > 16 Mo : le message est toujours la 1 s apres")
    verifie((b.srv.racine / "histo" / "gros.bin").exists(), False, "envoi > 16 Mo : rien d'ecrit sur la carte")

    # B6 : pendant un envoi lent, toute la barre d'actions est grisee ; B11 : renommer vers un nom deja pris est refuse
    coche(cdp, "essai")
    cdp.js("window.__fetch=window.fetch; window.fetch=function(u,o){var r=window.__fetch.apply(this,arguments); return /envoie/.test(String(u)) ? new Promise(function(ok){setTimeout(function(){ok(r)},1500)}) : r;}")
    pose_fichiers(cdp, [("petit.bin", 10)])
    attend(cdp, "document.getElementById('msg').textContent.indexOf('Envoi de') === 0", 5)
    verifie(cdp.js("['b-zip','b-env','b-dos','b-dep','b-ren','b-supp'].every(function(i){return document.getElementById(i).disabled})"), True, "envoi lent : barre d'actions grisee")
    verifie(cdp.js("document.getElementById('msg').textContent"), "Envoi de « petit.bin » (1/1)…", "envoi lent : message de progression")
    verifie(bool(attend(cdp, "document.getElementById('b-dos').disabled === false", 10)), True, "envoi fini : barre rendue")
    verifie((b.srv.racine / "histo" / "petit.bin").exists(), True, "envoi : fichier arrive sur la carte")
    cdp.js("window.fetch=window.__fetch")
    coche(cdp, SPECIAL)
    clique(cdp, "b-ren")
    cdp.js("document.getElementById('boite-champ').value='mesures-2026-11.bin'")
    clique(cdp, "boite-ok")
    verifie(bool(attend(cdp, "document.getElementById('msg').textContent.indexOf('existe déjà') >= 0", 10)), True, "renommer vers un nom pris : refuse avec un message")
    verifie((b.srv.racine / "histo" / SPECIAL).exists(), True, "renommer refuse : le fichier n'a pas bouge")

    # B7 : le texte dit ce qui part
    coche(cdp, "essai")
    clique(cdp, "b-supp")
    verifie(cdp.js("document.getElementById('boite-texte').textContent.indexOf('le dossier « essai » et tout son contenu') >= 0"), True, "suppression d'un dossier : « et tout son contenu »")
    clique(cdp, "boite-non")
    verifie((b.srv.racine / "histo" / "essai").is_dir(), True, "suppression annulee : le dossier est la")

    # suppression d'un fichier protege : 1 confirmation = refus, 2 = supprime
    cdp.js("document.querySelector('#arbre button[data-chemin=\"/\"]').click()")
    attend(cdp, "document.getElementById('fil').textContent==='/' && document.querySelectorAll('#lignes tr').length>0", 10)
    coche(cdp, "autoexec.be")
    clique(cdp, "b-supp")
    verifie(cdp.js("document.getElementById('boite').hidden"), False, "suppression : la boite de confirmation s'ouvre")
    with tol:
        clique(cdp, "boite-ok")
        verifie(bool(attend(cdp, "!document.getElementById('boite').hidden && document.getElementById('boite-texte').textContent.indexOf('protégé') >= 0", 10)), True,
                "fichier protege : une seconde confirmation est demandee")
    verifie(tol.n >= 1, True, "fichier protege : le serveur a bien rendu un 409")
    verifie(cdp.js("document.getElementById('boite-texte').textContent.indexOf('fichier de configuration de la carte') >= 0"), True, "fichier protege : dit pourquoi")
    verifie((b.srv.racine / "autoexec.be").exists(), True, "apres 1 confirmation : le fichier est toujours la")
    clique(cdp, "boite-ok")
    verifie(bool(attend(cdp, "document.querySelectorAll('#lignes tr[data-nom=\"autoexec.be\"]').length === 0", 10)), True, "apres 2 confirmations : retire de la liste")
    verifie((b.srv.racine / "autoexec.be").exists(), False, "apres 2 confirmations : supprime sur la carte")

    # B2 : un autre onglet change de support ; la page suit, et un geste de l'ancienne vue est refuse par le serveur
    attend(cdp, "document.getElementById('fil').textContent==='/' && document.querySelectorAll('#lignes tr').length>0", 10)
    coche(cdp, "histo")
    calme(cdp)                                                # sans sondage : le geste part forcement avec l'ancienne paire (sinon pas de 409)
    with tol:
        verifie(b.ouvre("flash")[0], 200, "autre onglet : POST /ouvre flash")
        clique(cdp, "b-supp")
        clique(cdp, "boite-ok")
        verifie(bool(attend(cdp, "document.getElementById('msg').textContent.indexOf('autre onglet') >= 0", 12)), True, "autre onglet : la page l'annonce")
    verifie(tol.n >= 1, True, "autre onglet : le serveur a bien rendu un 409")
    calme(cdp, False)
    cdp.js("sonde(true)")
    verifie(bool(attend_sonde(cdp, "document.getElementById('pastille').textContent.indexOf('Flash') >= 0", 25)), True, "autre onglet : pastille Flash")
    verifie((b.srv.racine / "histo").is_dir(), True, "autre onglet : le geste de l'ancienne vue n'a rien supprime")
    verifie(cdp.js("document.querySelectorAll('#lignes tr input:checked').length"), 0, "autre onglet : aucune case restee cochee")
    # B5 : session fermee ailleurs -> bouton Rallumer
    verifie(b.json("POST", "/ferme", {})[0], 200, "autre onglet : /ferme")
    verifie(bool(attend_sonde(cdp, "!!document.getElementById('msg-action')", 25)), True, "session perdue : bouton Rallumer propose")
    clique(cdp, "msg-action")
    verifie(bool(attend(cdp, "document.getElementById('pastille').getAttribute('data-etat')==='actif' && document.getElementById('pastille').textContent.indexOf('Flash')>=0", 12)),
            True, "Rallumer : la session repart sur le meme support")
    # B10 : la liste Carte ne montre plus la carte active : les boutons visent quand meme la session active
    cdp.js("document.getElementById('carte').value=''")
    clique(cdp, "b-sd")
    verifie(bool(attend(cdp, "document.getElementById('pastille').textContent.indexOf('SD')>=0 && document.getElementById('pastille').getAttribute('data-etat')==='actif'", 10)),
            True, "liste Carte videe : la bascule SD vise la carte active")

    # Boite de confirmation perimee : l'autre onglet change de support pendant que la boite est ouverte
    def suppressions():
        return sum(1 for c, _ in b.srv.commandes if c in ("DELE", "RMD", "MKD", "STOR", "RNFR"))

    def relit_racine():
        cdp.js("document.querySelector('#arbre button[data-chemin=\"/\"]').click()")
        attend(cdp, "document.getElementById('fil').textContent==='/' && document.querySelectorAll('#lignes tr[data-nom=\"perime.bin\"]').length===1", 10)

    b.fichier("/perime.bin", b"xx")
    relit_racine()
    espionne(cdp)
    # (1) copie figee seule : la boite reste ouverte (fermeture par le sondage coupee) ; le geste est mort (la session a change) : la confirmation n'envoie RIEN
    coche(cdp, "perime.bin")
    # Pas de tick de 5 s (seuls les sondages forces passent) et clic + coupure de la fermeture dans UNE evaluation : un sondage en vol ne peut plus
    # fermer la boite entre le clic et `S.fermeBoite = null` (cause du rouge intermittent « la boite est restee ouverte »).
    calme(cdp, "force")
    cdp.js("document.getElementById('b-supp').click(); S.fermeBoite = null; 0")
    n0 = suppressions()
    oublie(cdp)
    with tol:
        verifie(b.ouvre("flash")[0], 200, "boite perimee : l'autre onglet passe sur la flash")
        verifie(bool(attend_sonde(cdp, "document.getElementById('pastille').textContent.indexOf('Flash') >= 0", 25)), True, "boite perimee : le sondage a mis la page a jour")
        verifie(cdp.js("document.getElementById('boite').hidden"), False, "boite perimee : la boite est restee ouverte (fermeture coupee)")
        clique(cdp, "boite-ok")
        verifie(bool(attend(cdp, "document.getElementById('msg').textContent.indexOf('autre onglet') >= 0", 12)), True, "boite perimee : le message du sondage reste affiche apres la confirmation")
    verifie((b.srv.racine / "perime.bin").exists(), True, "boite perimee : le fichier est toujours la")
    calme(cdp, False)
    verifie(suppressions(), n0, "boite perimee : aucune suppression ni ecriture recue par le faux serveur")
    verifie(len(posts(cdp, "/supprime")), 0, "boite perimee : la page n'a envoye aucun POST /supprime (garde cote client : le serveur aurait refuse en 409 sans rien ecrire)")
    # (2) la boite se ferme d'elle-meme quand la session change
    attend(cdp, "document.querySelectorAll('#lignes tr[data-nom=\"perime.bin\"]').length===1", 10)
    coche(cdp, "perime.bin")
    clique(cdp, "b-supp")
    verifie(cdp.js("document.getElementById('boite').hidden"), False, "boite : ouverte sur la flash")
    verifie(b.ouvre("sd")[0], 200, "boite : l'autre onglet repasse sur la SD")
    verifie(bool(attend_sonde(cdp, "document.getElementById('boite').hidden", 25)), True, "boite : fermee par le sondage quand la session change")
    clique(cdp, "boite-ok")
    time.sleep(0.5)
    verifie((b.srv.racine / "perime.bin").exists() and suppressions() == n0, True, "boite fermee : rien n'a ete supprime")
    # B13 : un 200 non JSON a l'allumage donne un message lisible et une pastille coherente
    attend(cdp, "document.getElementById('pastille').getAttribute('data-etat')==='actif'", 12)
    cdp.js("window.__fetch2=window.fetch; window.fetch=function(u){ return /ouvre/.test(String(u)) ? Promise.resolve(new Response('oups', {status: 200})) : window.__fetch2.apply(this, arguments); }")
    cdp.js("ouvrir(S.etat.env, 'sd', true)")
    verifie(bool(attend(cdp, "document.getElementById('msg').textContent.indexOf('illisible') >= 0", 10)), True, "allumage non JSON : message lisible")
    verifie(bool(attend(cdp, "document.getElementById('pastille').getAttribute('data-etat') !== 'allumage'", 10)), True, "allumage non JSON : pastille remise en coherence")
    cdp.js("window.fetch=window.__fetch2")

    # bascule Flash / SD : SD grisee quand la carte n'en a pas
    b.fc.ufs = '{"Ufs":{"Type":2,"Size":1000,"Free":500}}'
    clique(cdp, "b-flash")
    verifie(bool(attend(cdp, "document.getElementById('pastille').textContent.indexOf('Flash') >= 0", 10)), True, "bascule : pastille Flash")
    verifie(2 in b.ufsftp(), True, "bascule : UfsFTP 2 (flash)")
    verifie(cdp.js("document.getElementById('b-sd').disabled"), True, "sans SD : bouton SD grise")
    verifie(cdp.js("document.getElementById('sd-note').textContent"), "Pas de SD", "sans SD : mention")

    # telephone
    cdp.appel("Emulation.setDeviceMetricsOverride", width=375, height=800, deviceScaleFactor=1, mobile=True)
    verifie(bool(attend(cdp, "document.documentElement.scrollWidth <= window.innerWidth + 1", 5)), True, "telephone : pas de defilement horizontal")

    # erreurs de la page : seuls les 409 voulus (journal reseau de Chrome) sont toleres
    verifie(tol.restantes(), [], "aucune erreur de page (exception, console.error, CSP), hors les 409 voulus")

    # B4 : rien ne sort de ce serveur (ni 7600 ni 7700) et la barre ne liste aucun vrai outil
    with cdp.condition:
        urls = [e["params"]["request"]["url"] for e in cdp.evenements if e.get("method") == "Network.requestWillBeSent"]
    verifie([u for u in urls if not (u.startswith(m.url.rstrip("/")) or u.startswith("data:"))], [], "aucune requete hors de l'outil sonde")
    verifie(b.json("GET", "/_barre.json")[1], {"outils": []}, "barre : aucun vrai outil liste (hermetique)")

    # B3 (a) le gestionnaire pagehide seul, deterministe : evenement pagehide sur la page, le faux serveur recoit UfsFTP 0
    b.fc.ufs = banc_web.UFS_SD                              # la SD est revenue : la session peut repartir sur SD
    verifie(b.ouvre("sd")[0], 200, "avant pagehide : session ouverte")
    n0 = len(b.ufsftp())
    cdp.js("window.dispatchEvent(new PageTransitionEvent('pagehide'))")
    attend_ufs(b, lambda u: len(u) > n0 and u[-1] == 0, 8)
    verifie(b.ufsftp()[-1:], [0], "pagehide : le faux serveur a recu UfsFTP 0")
    verifie(b.session.etat()["etat"], "eteint", "pagehide : session eteinte")

    # B3 (b) vraie fermeture d'un onglet (Target.closeTarget), 15 s, une reprise avec une session rouverte. Le FTP ne s'eteint qu'avec le DERNIER
    # onglet : la page 1 (toujours ouverte) ne doit donc plus se signaler pendant cet essai, sinon elle garde la session allumee.
    calme(cdp)
    mon1 = ident(cdp)
    for essai in (1, 2, 3):
        b.session.onglets.reinitialise()                   # la page 1 a pu se signaler avant `calme` : elle ne compte plus (cause du rouge intermittent d'avant)
        b.ouvre("sd")
        n0 = len(b.ufsftp())
        cible = cdp.appel("Target.createTarget", url=m.url)["targetId"]
        cdp.appel("Target.activateTarget", targetId=cible)
        attend_vu = time.monotonic() + 15
        while time.monotonic() < attend_vu and not vus(b):  # le nouvel onglet s'est signale (sa page a charge /etat) : condition observable, pas une duree
            time.sleep(0.2)
        b.session.onglets.ferme(mon1)                      # un sondage de la page 1 parti avant `calme` a pu arriver apres le reinitialise
        cdp.appel("Target.closeTarget", targetId=cible)
        attend_ufs(b, lambda u: len(u) > n0 and u[-1] == 0, 15)
        if len(b.ufsftp()) > n0 and b.ufsftp()[-1] == 0:
            break
    verifie(b.ufsftp()[-1:], [0], "fermeture reelle d'un onglet : UfsFTP 0 (essai %d)" % essai)
    verifie(b.session.etat()["etat"], "eteint", "fermeture reelle d'un onglet : session eteinte")

    # A8 : identifiant d'onglet, deux pages, seconde confirmation du deplacement, paire env/support, mineurs de la page
    scenario_onglets(m, tol)
    corrections(cdp, b, tol)
    relectures(cdp, b, tol)


def main():
    m = Montage.__new__(Montage)
    m.t = m.chrome = m.banc = None
    try:
        m.__init__()
        scenario(m)
    finally:
        m.ferme()
    if ECHECS or banc_web.ECHECS:
        print(f"ROUGE : {len(ECHECS) + len(banc_web.ECHECS)} echec(s) : {ECHECS + banc_web.ECHECS}")
        return 1
    print("VERT : ftp_cartes_page_chrome")
    return 0


if __name__ == "__main__":
    sys.exit(main())
