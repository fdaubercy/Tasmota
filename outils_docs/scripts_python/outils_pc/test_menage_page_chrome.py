"""Sonde Chrome de la page « Menage du depot » (menage_page.PAGE) : parametres, audit, rapport, filtres, garder / ignorer, texte hostile, theme, telephone.

UTILISATION (a la main ; aucun pio, aucune carte, faux `claude` ; Chrome tourne ~30 s par passage)
    python outils_docs/scripts_python/outils_pc/test_menage_page_chrome.py [--sans-temoin]
Code de sortie 0 = vert : la page passe toutes les verifications ET chaque temoin (meme page, une ligne changee) est detecte par SON test.

Serveur reel dans ce processus (127.0.0.1, port libre), depot et dossier de donnees temporaires, faux `claude`. Chrome headless arrete a la fin.
Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_menage_page_chrome.py
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import acces_web                                                                # noqa: E402
import menage_page                                                              # noqa: E402
import menage_web as mw                                                         # noqa: E402
from test_build_page_chrome import CHROMES, Cdp, attend, port_libre, tue_arbre   # noqa: E402

ECHECS = []
HOSTILE = "<img src=x onerror=window.__pwn=1> & <b>gras</b>"
HOSTILE_ACTION = "git status <img src=x onerror=window.__pwn2=1> & <b>x</b>"
PAGE_ORIGINALE = menage_page.PAGE
TEMOINS = {       # nom -> (texte de la page, remplacement, verification qui doit echouer)
    "innerHTML": ("if (texte != null) e.textContent = texte;", "if (texte != null) e.innerHTML = texte;", "hostile : le texte reste du texte, aucune balise creee"),
    "en-cours-actions": ("if (!p.en_cours) {", "if (true) {", "en cours : aucun bouton Garder ni Ignorer"),
    "journal-html": ("l.appendChild(document.createTextNode(a.detail));", "l.insertAdjacentHTML('beforeend', a.detail);",
                     "journal : l'action hostile reste du texte"),
    "verif-sans-code": ("if (v.n_code) vb.appendChild", "if (false) vb.appendChild", "verif : badge code/config sur le fichier cite par config.ini"),
    "detail-html": ('$("detail-texte").textContent = dt;', '$("detail-texte").innerHTML = dt;', "echec : le detail reste du texte"),
    "suivi-cache": ('$("suivi").hidden = !(enCours || j.childNodes.length > 0);', '$("suivi").hidden = true;', "suivi : bloc d'avancement visible, au-dessus des propositions, dans l'ecran"),
    "couv-html": ('l.appendChild(t); z.appendChild(l);', 'l.appendChild(t); t.innerHTML += c.note; z.appendChild(l);', "couverture : texte de l'agent affiche comme du texte"),
    "lot-sans-confirm": ('if (!aBlanc && !window.confirm(', 'if (false && !window.confirm(', "lot : confirmation refusee, rien n'est applique"),
    "lot-apercu-garde": ('$("b-blanc").disabled = true; $("b-applique").disabled = true;', '$("b-blanc").disabled = true;', "lot : changer la selection invalide l'apercu et grise « Appliquer »"),
    "lot-reponse-tardive": ('if (JSON.stringify(ids) !== JSON.stringify(S.lot.ids)) return;', 'if (false) return;', "lot : un apercu qui arrive apres un changement de selection n'arme pas « Appliquer »"),
    "pas-de-filtre-risque": ("(!risque || p.risque === risque)", "true", "filtre risque : seule la proposition du risque choisi"),
}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def clic(cdp, ident):
    return cdp.js(f"(function(){{var e=document.getElementById({json.dumps(ident)}); if(!e) return 'absent'; e.click(); return 'ok';}})()")


def clic_bouton(cdp, zone, texte, rang=0):
    """Clique le `rang`-ieme bouton de `texte` dans `zone` (selecteur CSS)."""
    return cdp.js("(function(){var b=Array.prototype.filter.call(document.querySelectorAll(" + json.dumps(zone + " button") + "),"
                  "function(x){return x.textContent===" + json.dumps(texte) + "});if(!b[" + str(rang) + "]) return 'absent'; b[" + str(rang) + "].click(); return 'ok';})()")


def faux_claude(dossier):
    f = dossier / "faux_claude.py"
    props = [
        {"id": "M1", "categorie": "reste", "chemin": "tasks/README.md", "constat": HOSTILE, "preuve": "git log", "action": "archiver",
         "casserait": "rien", "risque": "faible", "en_cours": False},
        {"id": "M2", "categorie": "orphelin", "chemin": "tasks/autre.md", "constat": "second", "preuve": "grep", "action": "supprimer",
         "casserait": "le cenv", "risque": "eleve", "en_cours": False},
        {"id": "M3", "categorie": "doublon", "chemin": "tasks/encours.md", "constat": "travail en cours", "preuve": "git status",
         "action": "supprimer", "casserait": "tout", "risque": "moyen", "en_cours": True},
    ]
    rapport = json.dumps({"resume": "- Premier point.\n- Second point.", "non_verifie": "rien de grave", "propositions": props,
                          "couverture": [{"controle": "reste", "etat": "fait", "note": "tout vu"},
                                         {"controle": "taille", "etat": "non_fait", "note": HOSTILE}],
                          "limites": [HOSTILE], "ecartes": ["les plans clos"]})
    action = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": HOSTILE_ACTION}}]}}
    f.write_text("import json, os, sys, time\nsys.stdin.buffer.read()\n"
                 "if os.environ.get('FAUX_MENAGE') == 'echec':\n"
                 "    print(json.dumps({'type': 'result', 'is_error': True, 'result': 'Credit balance is too low <b>x</b>'}), flush=True)\n"
                 "    sys.stderr.write('warning: ANTHROPIC_API_KEY is set'); sys.exit(1)\n"
                 "print(json.dumps(" + repr(action) + "), flush=True)\ntime.sleep(4)\n"
                 "print(json.dumps({'type': 'result', 'is_error': False, 'result': " + repr(rapport) + "}))\n", encoding="utf-8")
    return f


class Montage:
    def __init__(self, page):
        self.t = Path(tempfile.mkdtemp(prefix="sonde_menage_"))
        self.chrome = self.serveur = None
        racine = self.t / "depot"
        (racine / "tasks").mkdir(parents=True)
        for n in ("README.md", "autre.md", "encours.md"):
            (racine / "tasks" / n).write_text("x", encoding="utf-8")
        (racine / "config.ini").write_text("liste = tasks/encours.md\n", encoding="utf-8")     # un vrai renvoi, trouve par la contre-verification
        for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x"]):
            subprocess.run(["git"] + args, cwd=racine, capture_output=True, check=True)
        menage_page.PAGE = page
        self.port = port_libre()
        self.url = f"http://127.0.0.1:{self.port}/"
        self.acces = acces_web.Acces(self.port, True, "Menage du depot")
        etat = mw.Etat(racine, lambda: [], programme=[sys.executable, str(faux_claude(self.t))], dossier=self.t / "donnees", delai=30)
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port), mw.fabrique_gestionnaire(self.acces, etat))
        self.serveur.daemon_threads = True
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()
        chrome = next((c for c in CHROMES if c.is_file()), None)
        if chrome is None:
            raise FileNotFoundError("chrome.exe introuvable")
        self.port_cdp = port_libre()
        self.chrome = subprocess.Popen([str(chrome), "--headless=new", f"--remote-debugging-port={self.port_cdp}", "--remote-allow-origins=*",
                                        f"--user-data-dir={self.t / 'profil'}", "--no-first-run", "--no-default-browser-check",
                                        "--disable-extensions", "--window-size=1280,1000", "about:blank"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cibles = self._attend(f"http://127.0.0.1:{self.port_cdp}/json/list", 20)
        page_cdp = next(c for c in json.loads(cibles) if c.get("type") == "page")
        self.cdp = Cdp(page_cdp["webSocketDebuggerUrl"])
        for domaine in ("Runtime.enable", "Log.enable", "Page.enable"):
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
        if self.t:           # Chrome laisse des processus fils, parfois relances : on balaie par le profil de cette sonde
            commande = ("$p = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'chrome.exe' -and $_.CommandLine -like '*" + self.t.name
                        + "*' }); $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; $p.Count")
            for _ in range(8):      # jusqu'a ce qu'un balayage ne trouve plus rien (Chrome relance des fils pendant son arret)
                r = subprocess.run(["powershell", "-NoProfile", "-Command", commande], capture_output=True, text=True)
                if r.stdout.strip() == "0":
                    break
                time.sleep(0.7)
        if self.serveur:
            self.serveur.shutdown()
            self.serveur.server_close()
        menage_page.PAGE = PAGE_ORIGINALE
        shutil.rmtree(self.t, ignore_errors=True)


def scenario(m, temoin):
    cdp = m.cdp
    cdp.appel("Emulation.setDeviceMetricsOverride", width=1280, height=1000, deviceScaleFactor=1, mobile=False)
    cdp.appel("Page.navigate", url=m.url)
    verifie(bool(attend(cdp, "document.querySelectorAll('#p-zone input').length > 0", 15)), True, "page chargee, options remplies")
    verifie(cdp.js("document.querySelectorAll('#p-zone input').length"), len(mw.ml.ZONES), "une case par dossier")
    verifie(cdp.js("document.querySelectorAll('#p-cat input').length"), 7, "une case par controle")
    verifie(cdp.js("document.title"), "Ménage du dépôt", "titre")
    verifie(cdp.js("document.getElementById('b-copie').disabled"), True, "copier grise sans rapport")
    verifie(cdp.js("document.getElementById('n-zone').textContent"), "(%d/%d)" % (len(mw.ml.ZONES), len(mw.ml.ZONES)), "groupe dossiers : compte des cases cochees")
    verifie(cdp.js("(function(){var d=document.getElementById('p-cat').parentNode; d.open=false; var c=document.getElementById('p-cat'); var ferme=!c.checkVisibility({contentVisibilityAuto:true}); d.open=true; return d.tagName==='DETAILS' && ferme && c.checkVisibility()})()"), True, "groupe controles : repliable")

    cdp.js("document.querySelectorAll('#p-zone input').forEach(function(c){c.checked=false})")
    clic(cdp, "b-lance")
    verifie(bool(attend(cdp, "document.getElementById('etat').textContent.indexOf('Cochez') >= 0", 5)), True, "aucun dossier coche : refus cote page")
    cdp.js("document.querySelectorAll('#p-zone input').forEach(function(c){c.checked=true})")

    clic(cdp, "b-lance")
    # en direct : pendant l'audit, l'action de l'agent et une progression sont deja a l'ecran
    verifie(bool(attend(cdp, "document.querySelectorAll('#journal div').length > 0", 15)), True, "journal : une action apparait pendant l'audit")
    verifie(cdp.js("document.getElementById('etat').className.indexOf('en') >= 0 && document.getElementById('b-stop').disabled === false"), True,
            "journal : l'audit est encore en cours quand l'action s'affiche")
    verifie(cdp.js("document.querySelector('#journal div').textContent.indexOf('Bash') >= 0"), True, "journal : l'outil est nomme")
    verifie(cdp.js("(function(){var s=document.getElementById('suivi'),p=document.getElementById('props'); var r=s.getBoundingClientRect(); return !s.hidden && r.height > 0 && r.top < p.getBoundingClientRect().top && r.top < window.innerHeight;})()"),
            True, "suivi : bloc d'avancement visible, au-dessus des propositions, dans l'ecran")
    verifie(cdp.js("document.getElementById('maintenant').textContent.indexOf('En ce moment') >= 0 && document.getElementById('maintenant').textContent.indexOf('Bash') >= 0"), True,
            "suivi : « En ce moment » nomme l'action en cours")
    verifie(cdp.js("document.getElementById('suivi-titre').textContent"), "Audit en cours", "suivi : titre pendant l'audit")
    verifie(cdp.js("document.querySelectorAll('#journal img, #journal b').length === 0 && window.__pwn2 === undefined"), True,
            "journal : l'action hostile reste du texte")
    verifie(cdp.js("document.getElementById('journal').textContent.indexOf(" + json.dumps(HOSTILE_ACTION) + ") >= 0"), True, "journal : action affichee telle quelle")
    verifie(cdp.js("document.getElementById('avance').hidden === false && parseInt(document.getElementById('rempli').style.width) > 0"), True,
            "progression : barre visible et non vide pendant l'audit")
    verifie(bool(attend(cdp, "document.getElementById('etat').textContent.indexOf('terminé') >= 0", 40)), True, "audit termine")
    verifie(cdp.js("document.getElementById('rempli').style.width"), "100%", "progression : 100 % a la fin")
    verifie(cdp.js("document.getElementById('suivi-titre').textContent"), "Audit terminé", "suivi : titre a la fin (le journal reste consultable)")
    verifie(bool(attend(cdp, "document.querySelectorAll('#props .prop').length > 0", 15)), True, "rapport affiche apres l'audit")
    verifie(cdp.js("document.querySelectorAll('#props .prop').length"), 2, "2 propositions actives")
    verifie(cdp.js("document.getElementById('n-props').textContent"), "(2)", "compteur des propositions")
    verifie(cdp.js("document.querySelector('#props .prop .chemin').textContent"), "tasks/README.md", "tri par risque : la faible d'abord")
    verifie(cdp.js("Array.prototype.map.call(document.querySelectorAll('#resume li'),function(l){return l.textContent}).join('|')"), "Premier point.|Second point.",
            "resume : une ligne par point, sans le tiret du texte")
    verifie(cdp.js("Array.prototype.map.call(document.querySelectorAll('#plan summary'),function(s){return s.textContent.charAt(0)}).join('')"), "1",
            "plan d'action : seule l'etape 1 (aucun renvoi) existe pour ces propositions")
    verifie(cdp.js("document.querySelector('#plan details[open]').textContent.indexOf('tasks/README.md') >= 0 && document.querySelector('#plan details[open]').textContent.indexOf('tasks/encours.md') < 0"), True,
            "plan d'action : la proposition « en cours » n'entre pas dans le plan")
    # lot : cocher, voir ce que git ferait, jouer a blanc, appliquer (depot jetable de la sonde, jamais le vrai)
    depot = m.t / "depot"
    verifie(cdp.js("document.getElementById('lot').hidden === false && document.querySelectorAll('.lot-case input').length"), 1,
            "lot : une seule case, sur la suppression sans renvoi (ni l'archivage, ni la ligne en cours)")
    verifie(cdp.js("document.getElementById('b-apercu').disabled && document.getElementById('b-blanc').disabled && document.getElementById('b-applique').disabled"), True,
            "lot : rien de coche, tous les boutons grises")
    cdp.js("document.querySelector('.lot-case input').click()")
    verifie(cdp.js("document.getElementById('b-apercu').disabled === false && document.getElementById('b-applique').disabled"), True,
            "lot : coche, l'apercu est possible mais « Appliquer » reste grise tant que l'apercu n'est pas affiche")
    clic(cdp, "b-apercu")
    verifie(bool(attend(cdp, "document.getElementById('lot-apercu').textContent.indexOf('git rm -- tasks/autre.md') >= 0", 20)), True, "lot : l'apercu montre la commande exacte")
    verifie(cdp.js("document.getElementById('lot-apercu').textContent.indexOf('simulation par git -n') >= 0 && document.getElementById('b-applique').disabled === false"), True,
            "lot : apercu simule par git, « Appliquer » devient possible")
    cdp.js("document.querySelector('.lot-case input').click()")
    cdp.js("document.querySelector('.lot-case input').click()")
    verifie(cdp.js("document.getElementById('b-applique').disabled && document.getElementById('b-blanc').disabled && document.getElementById('lot-apercu').textContent"), "",
            "lot : changer la selection invalide l'apercu et grise « Appliquer »")
    clic(cdp, "b-apercu")
    attend(cdp, "document.getElementById('b-blanc').disabled === false", 20)
    clic(cdp, "b-blanc")
    verifie(bool(attend(cdp, "document.getElementById('lot-resultat').textContent.indexOf('rien n') >= 0", 20)), True, "lot : jouer a blanc affiche son resultat")
    verifie(((depot / "tasks" / "autre.md").exists(), "autre.md" in subprocess.run(["git", "status", "--short"], cwd=depot, capture_output=True).stdout.decode()), (True, False),
            "lot : a blanc, le fichier existe encore et git ne voit aucun changement")
    # reponse d'apercu en retard : la selection change pendant l'attente, l'ancien apercu ne doit pas armer « Appliquer »
    cdp.js("(function(){var r=window.fetch; window.fetch=function(u,o){var p=r.apply(this,arguments); return String(u).indexOf('/appliquer/apercu')>=0 ? new Promise(function(ok){setTimeout(function(){ok(p)},1500)}) : p;}; document.getElementById('b-apercu').click(); document.querySelector('.lot-case input').click(); document.querySelector('.lot-case input').click();})()")
    time.sleep(3)
    verifie(cdp.js("document.getElementById('b-applique').disabled"), True, "lot : un apercu qui arrive apres un changement de selection n'arme pas « Appliquer »")
    clic(cdp, "b-apercu")
    attend(cdp, "document.getElementById('b-blanc').disabled === false", 30)
    cdp.js("window.confirm = function () { return false; }")
    clic(cdp, "b-applique")
    verifie(bool(attend(cdp, "document.getElementById('lot-resultat').textContent.indexOf('Appliqu') >= 0", 6)), False, "lot : confirmation refusee, aucun resultat n'apparait")
    verifie((depot / "tasks" / "autre.md").exists(), True, "lot : confirmation refusee, rien n'est applique")
    cdp.js("window.confirm = function () { return true; }")
    clic(cdp, "b-applique")
    verifie(bool(attend(cdp, "document.getElementById('lot-resultat').textContent.indexOf('non commit') >= 0", 20)), True, "lot : application confirmee, resultat affiche")
    etat_git = subprocess.run(["git", "status", "--short"], cwd=depot, capture_output=True).stdout.decode()
    nb_commits = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=depot, capture_output=True).stdout.decode().strip()
    verifie((not (depot / "tasks" / "autre.md").exists(), "D" in etat_git and "autre.md" in etat_git, nb_commits), (True, True, "1"),
            "lot : le fichier est supprime dans l'arbre et l'index, RIEN n'est commite")
    verifie(cdp.js("document.getElementById('lot-resultat').textContent.indexOf('git restore --staged --worktree') >= 0"), True, "lot : la commande d'annulation est donnee")
    verifie(cdp.js("document.querySelectorAll('.lot-case input').length"), 0, "lot : la ligne appliquee n'est plus cochable (badge « appliquee »)")
    verifie(cdp.js("document.querySelectorAll('#lot img, #lot b').length < 3 && window.__pwn === undefined"), True, "lot : aucun HTML injecte")
    subprocess.run(["git", "restore", "--staged", "--worktree", "--", "tasks/autre.md"], cwd=depot, capture_output=True)      # la commande donnee a l'ecran ; la suite de la sonde a besoin du fichier
    verifie((depot / "tasks" / "autre.md").exists(), True, "lot : git restore --staged --worktree annule la suppression")
    verifie(cdp.js("document.getElementById('b-copie').disabled"), False, "copier actif avec un rapport")
    verifie(cdp.js("document.getElementById('couverture').hidden === false && document.querySelectorAll('#couv .couv-ligne').length"), 7,
            "couverture : une ligne par controle demande (les non declares y figurent)")
    verifie(cdp.js("Array.prototype.some.call(document.querySelectorAll('#couv .couv-ligne'),function(l){return l.textContent.indexOf('tout vu')>=0 && l.querySelector('.badge').textContent.indexOf('Fait')>=0})"), True, "couverture : pastille « Fait »")
    verifie(cdp.js("document.querySelectorAll('#couverture img, #couverture b').length === 0 && window.__pwn === undefined"), True,
            "couverture : texte de l'agent affiche comme du texte")
    verifie(cdp.js("document.getElementById('limites-bloc').textContent.indexOf('les plans clos') >= 0"), True, "couverture : ecartes affiches")
    verifie(cdp.js("document.getElementById('b-refaire').hidden"), False, "couverture : bouton « a refaire » present")
    cdp.js("document.getElementById('b-refaire').click()")
    verifie(cdp.js("Array.prototype.map.call(document.querySelectorAll('#p-cat input:checked'),function(c){return c.value}).join(',')"), "orphelin,hors_dossier,doublon,taille,poids,vide",
            "couverture : le bouton coche tous les controles sauf celui qui est fait")

    # texte hostile : du texte, jamais du HTML
    verifie(cdp.js("document.querySelectorAll('#props img, #props b').length === 0 && window.__pwn === undefined"), True,
            "hostile : le texte reste du texte, aucune balise creee")
    verifie(cdp.js("document.querySelector('#props .prop p').textContent"), HOSTILE, "hostile : affiche tel quel")

    # contre-verification par git : badges (M1 sans renvoi) et renvoi reel (M3, cite par config.ini)
    verifie(cdp.js("document.querySelector('#props .prop .verif').textContent.indexOf('aucun renvoi trouvé') >= 0"), True, "verif : aucun renvoi, badge vert")
    verifie(cdp.js("document.querySelector('#props-encours .prop .verif').textContent.indexOf('référencé par 1 fichier(s) de code ou de config') >= 0"), True,
            "verif : badge code/config sur le fichier cite par config.ini")
    verifie(cdp.js("document.querySelector('#props-encours .prop .renvois pre').textContent.indexOf('config.ini') >= 0"), True,
            "verif : la liste des renvois nomme config.ini")

    # en cours : replie, sans boutons
    verifie(cdp.js("document.getElementById('encours').hidden"), False, "bloc « en cours » visible")
    verifie(cdp.js("document.querySelectorAll('#props-encours .prop').length"), 1, "1 proposition en cours")
    verifie(cdp.js("document.querySelectorAll('#props-encours button').length"), 0, "en cours : aucun bouton Garder ni Ignorer")

    # filtres
    cdp.js("var s=document.getElementById('f-risque'); s.value='eleve'; s.dispatchEvent(new Event('change',{bubbles:true}))")
    verifie(cdp.js("Array.prototype.map.call(document.querySelectorAll('#props .chemin'),function(e){return e.textContent}).join(',')"),
            "tasks/autre.md", "filtre risque : seule la proposition du risque choisi")
    cdp.js("var s=document.getElementById('f-risque'); s.value=''; s.dispatchEvent(new Event('change',{bubbles:true}))")
    cdp.js("var s=document.getElementById('f-cat'); s.value='reste'; s.dispatchEvent(new Event('change',{bubbles:true}))")
    verifie(cdp.js("document.querySelectorAll('#props .prop').length"), 1, "filtre categorie")
    cdp.js("var s=document.getElementById('f-cat'); s.value=''; s.dispatchEvent(new Event('change',{bubbles:true}))")

    # ignorer, garder, retirer
    clic_bouton(cdp, "#props", "Ignorer cette fois", 0)
    verifie(bool(attend(cdp, "document.querySelectorAll('#props .prop').length === 1", 10)), True, "ignorer : la proposition disparait")
    clic_bouton(cdp, "#props", "Garder", 0)
    verifie(bool(attend(cdp, "document.querySelectorAll('#props .prop').length === 0", 10)), True, "garder : la proposition disparait")
    verifie(bool(attend(cdp, "document.getElementById('gardes').textContent.indexOf('tasks/autre.md') >= 0", 10)), True, "garder : listee dans « Gardes »")
    verifie(cdp.js("document.getElementById('n-gardes').textContent"), "(1)", "compteur des gardes")
    clic_bouton(cdp, "#gardes", "Retirer", 0)
    verifie(bool(attend(cdp, "document.querySelectorAll('#props .prop').length === 1", 10)), True, "retirer : la proposition revient")

    # echec de claude : la raison en francais d'abord, le texte anglais d'origine en detail depliable (en texte)
    os.environ["FAUX_MENAGE"] = "echec"
    try:
        clic(cdp, "b-lance")
        verifie(bool(attend(cdp, "document.getElementById('etat').textContent.indexOf('a échoué') >= 0", 20)), True, "echec : l'interface annonce l'echec")
        verifie(cdp.js("document.getElementById('etat').textContent.indexOf('crédit') >= 0 && document.getElementById('etat').textContent.indexOf('Credit balance') < 0"), True,
                "echec : la raison est en francais, sans l'anglais brut")
        verifie(cdp.js("document.getElementById('detail').hidden === false && document.getElementById('detail-texte').textContent.indexOf('Credit balance') >= 0"), True,
                "echec : le detail technique d'origine est disponible")
        verifie(cdp.js("document.querySelectorAll('#detail b').length"), 0, "echec : le detail reste du texte")
    finally:
        os.environ.pop("FAUX_MENAGE", None)

    # theme
    cdp.js("var c=document.getElementById('theme'); c.checked=!c.checked; c.dispatchEvent(new Event('change',{bubbles:true}))")
    verifie(cdp.js("document.documentElement.getAttribute('data-theme')") in ("clair", "sombre"), True, "theme pose")
    avant = cdp.js("document.documentElement.getAttribute('data-theme')")
    cdp.appel("Page.reload")
    attend(cdp, "document.querySelectorAll('#p-zone input').length > 0", 15)
    verifie(cdp.js("document.documentElement.getAttribute('data-theme')"), avant, "theme memorise au rechargement")

    # telephone : pas de defilement horizontal
    cdp.appel("Emulation.setDeviceMetricsOverride", width=375, height=800, deviceScaleFactor=1, mobile=True)
    time.sleep(0.5)
    verifie(cdp.js("document.documentElement.scrollWidth <= window.innerWidth + 1"), True, "telephone : pas de defilement horizontal")

    verifie(cdp.erreurs(), [], "aucune erreur de page (exception, console.error)") if not temoin else None


def passage(page, temoin=None):
    m = Montage.__new__(Montage)          # ferme() nettoie meme si __init__ plante apres avoir lance Chrome
    m.t = m.chrome = m.serveur = None
    try:
        m.__init__(page)
        scenario(m, temoin)
    finally:
        m.ferme()


def main():
    opt = argparse.ArgumentParser()
    opt.add_argument("--sans-temoin", action="store_true")
    args = opt.parse_args()
    print("== passage normal")
    passage(PAGE_ORIGINALE)
    if ECHECS:
        print(f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}")
        return 1
    if not args.sans_temoin:
        for nom, (ancien, nouveau, libelle) in TEMOINS.items():
            if PAGE_ORIGINALE.count(ancien) != 1:
                print(f"KO   temoin {nom} : texte a changer introuvable ou multiple")
                return 1
            print(f"== temoin {nom} (doit echouer sur : {libelle})")
            ECHECS.clear()
            passage(PAGE_ORIGINALE.replace(ancien, nouveau), temoin=nom)
            detecte = libelle in ECHECS
            print(("OK   " if detecte else "KO   ") + f"temoin {nom} detecte par son test")
            if not detecte:
                return 1
        ECHECS.clear()
    print("VERT : menage_page_chrome")
    return 0


if __name__ == "__main__":
    sys.exit(main())
