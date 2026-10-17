"""Banc des corrections de la relecture finale de l'annuaire (serveur annuaire_outils et etat annuaire_presence).

Code de sortie 0 = vert. Couvre : Host d'un client de ce PC (parade au DNS rebinding), ouverture du
navigateur hors du job, champs lie et peut_arreter de l'etat, copie de lances avant iteration, erreurs de
lanceur.lance et de liste_ports, route_occupee quand l'outil ne repond pas (fusion ou rebase dans un faux
.git). Aucun vrai outil, aucun navigateur, aucun port COM ; seul processus cree : pid_mort() (python -c pass).
"""

import http.client
import inspect
import json
import os
import subprocess
import sys
import tempfile
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer

DOSSIER = tempfile.mkdtemp(prefix="banc_annuaire_secu_")
os.environ["OUTILS_TASMOTA_DOSSIER"] = DOSSIER          # avant tout usage d'acces_web

import acces_web                     # noqa: E402
import annuaire_outils as ann        # noqa: E402
import annuaire_presence as pre      # noqa: E402
import annuaire_registre as reg      # noqa: E402
from annuaire_lanceur import CREATE_BREAKAWAY_FROM_JOB, CREATE_NO_WINDOW, Lanceur   # noqa: E402
from test_annuaire import ECHECS, RACINE, ecrit_fiche, pid_mort, port_libre, verifie   # noqa: E402

LIBRES = {o.id: port_libre() for o in reg.OUTILS}       # ports de page libres : aucun vrai outil sonde
ENT = {"X-Annuaire": "1"}


def appel(port, methode, chemin, corps=None, entetes=None):
    """(statut, json ou None) ; un Host dans entetes remplace celui que poserait http.client."""
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    donnees = None if corps is None else json.dumps(corps).encode("utf-8")
    c.request(methode, chemin, body=donnees, headers=dict(entetes or {}))
    r = c.getresponse()
    brut = r.read()
    c.close()
    try:
        return r.status, json.loads(brut.decode("utf-8"))
    except ValueError:
        return r.status, None


class Banc:
    """Annuaire sur 127.0.0.1:<port libre> avec un lanceur dont lance/arrete sont enregistres."""

    def __init__(self, git):
        with open(os.path.join(DOSSIER, "derniers.json"), "w", encoding="utf-8") as f:
            json.dump({o.id: {o.cle_port_page: LIBRES[o.id]} for o in reg.OUTILS}, f)
        self.lances, self.arrets = [], []
        self.lanceur = Lanceur(RACINE)
        self.lanceur.lance = self._lance
        self.lanceur.arrete = lambda outil, pid: self.arrets.append((outil.id, pid)) or True
        acces = acces_web.Acces(0, True, "Annuaire des outils")
        self.srv = ann.Serveur(("127.0.0.1", 0), ann.fabrique_gestionnaire(self.lanceur, acces, git))
        self.port = self.srv.server_address[1]
        acces.port = self.port
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def _lance(self, outil, args, valeurs=None):
        self.lances.append(outil.id)
        return 4242

    def get(self, chemin, hote=None):
        return appel(self.port, "GET", chemin, entetes={"Host": hote} if hote else None)

    def post(self, chemin, corps, hote=None):
        return appel(self.port, "POST", chemin, corps, dict(ENT, **({"Host": hote} if hote else {})))

    def ferme(self):
        self.srv.shutdown()
        self.srv.server_close()


def vide_presence():
    dossier = acces_web.dossier_presence()
    for f in os.listdir(dossier):
        os.remove(os.path.join(dossier, f))
    return str(dossier)


def section_hote(banc):
    print("== hote (DNS rebinding) ==")
    p = banc.port
    verifie(banc.get("/etat", f"evil.example:{p}")[0], 403, "GET /etat, Host evil.example -> 403")
    verifie(banc.get("/", f"evil.example:{p}")[0], 403, "GET /, Host evil.example -> 403")
    verifie(banc.get("/registre", f"evil.example:{p}")[0], 403, "GET /registre, Host evil.example -> 403")
    verifie(banc.get("/etat", f"127.0.0.1:{p + 1}")[0], 403, "GET /etat, Host 127.0.0.1 mais autre port -> 403")
    verifie(banc.post("/lance", {"id": "syslog", "valeurs": {}}, f"evil.example:{p}")[0], 403,
            "POST /lance, Host evil.example -> 403")
    verifie(banc.lances, [], "POST refuse : rien lance")
    s, j = banc.get("/etat", f"127.0.0.1:{p}")
    verifie((s, isinstance((j or {}).get("liens_reseau"), list)), (200, True), "TEMOIN GET /etat, Host 127.0.0.1 -> 200")
    verifie(banc.get("/etat", f"localhost:{p}")[0], 200, "TEMOIN GET /etat, Host localhost -> 200")
    verifie(banc.get("/etat", f"[::1]:{p}")[0], 200, "TEMOIN GET /etat, Host [::1] -> 200")
    verifie(banc.post("/lance", {"id": "syslog", "valeurs": {}}, f"127.0.0.1:{p}")[0], 200,
            "TEMOIN POST /lance, Host 127.0.0.1 -> 200")
    del banc.lances[:]
    distant = types.SimpleNamespace(client_address=("192.168.0.9", 5000), headers={"Host": "192.168.0.3:7600"})
    verifie(ann.hote_autorise(distant, 7600), True, "client distant : Host non controle (le jeton decide)")
    local = types.SimpleNamespace(client_address=("127.0.0.1", 5000), headers={"Host": "192.168.0.3:7600"})
    verifie(ann.hote_autorise(local, 7600), False, "client local, Host = IP reseau -> refuse")


def section_erreurs(banc):
    print("== erreurs de lance et de liste_ports ==")

    def lance_casse(outil, args, valeurs=None):
        raise OSError(2, "Le fichier specifie est introuvable")
    banc.lanceur.lance = lance_casse
    s, j = banc.post("/lance", {"id": "syslog", "valeurs": {}})
    verifie((s, "erreur" in (j or {})), (500, True), "lance leve OSError -> 500 avec erreur")
    verifie("introuvable" in (j or {}).get("erreur", ""), True, "500 : message de l'OSError transmis")
    banc.lanceur.lance = banc._lance
    verifie(banc.post("/lance", {"id": "syslog", "valeurs": {}})[0], 200, "TEMOIN lance normal -> 200")
    del banc.lances[:]

    ancien = sys.modules.get("pont_serie")
    faux = types.ModuleType("pont_serie")
    try:
        sys.modules["pont_serie"] = faux

        def detection_cassee():
            raise RuntimeError("SetupDi en echec")
        faux.liste_ports = detection_cassee
        verifie(ann.liste_ports(), [], "liste_ports : RuntimeError -> []")
        verifie(banc.get("/ports"), (200, []), "GET /ports : detection cassee -> 200 []")
        faux.liste_ports = lambda: [{"port": "COM7", "description": "USB"}]
        banc.lanceur.lances.clear()
        banc.lanceur.lances["pont_serie"] = {"pid": os.getpid(), "valeurs": {"port": "COM7"}}
        vrai = pre.pid_vivant
        n = [0]

        def pid_vivant_qui_mute(pid):          # un POST concurrent ajoute un outil pendant l'iteration
            n[0] += 1
            banc.lanceur.lances[f"zz_{n[0]}"] = {"pid": 0, "valeurs": {}}
            return vrai(pid)
        pre.pid_vivant = pid_vivant_qui_mute
        try:
            s, j = banc.get("/ports")
        finally:
            pre.pid_vivant = vrai
        verifie((s, j), (200, [{"port": "COM7", "description": "USB", "tenu_par": "Pont série"}]),
                "GET /ports : lances modifie pendant l'iteration -> 200, tenu_par")
    finally:
        banc.lanceur.lances.clear()
        if ancien is None:
            sys.modules.pop("pont_serie", None)
        else:
            sys.modules["pont_serie"] = ancien


def section_iteration():
    print("== iteration sur une copie de lances ==")
    vide_presence()
    vrai = pre.pid_vivant
    lances = {"pont_serie": {"pid": os.getpid(), "valeurs": {"port": "COM3"}}}
    n = [0]

    def pid_vivant_qui_mute(pid):
        n[0] += 1
        lances[f"zz_{n[0]}"] = {"pid": 0, "valeurs": {}}
        return vrai(pid)
    derniers = {o.id: {o.cle_port_page: LIBRES[o.id]} for o in reg.OUTILS}
    derniers["sniffeur_modbus"]["port"] = "COM3"
    pre.pid_vivant = pid_vivant_qui_mute
    try:
        try:
            e = next(x for x in pre.etat_outils(lances, derniers, None) if x["id"] == "sniffeur_modbus")
            resultat = (e["etat"], "COM3" in e["raison"])
        except RuntimeError as ex:
            resultat = repr(ex)
        verifie(resultat, ("bloque", True), "etat_outils : lances modifie pendant _com_tenu -> pas de RuntimeError")
        try:
            for _id, info in lances.items():
                pre.pid_vivant(info["pid"])
            temoin = "aucune erreur"
        except RuntimeError:
            temoin = "RuntimeError"
        verifie(temoin, "RuntimeError", "TEMOIN la meme mutation casse une iteration directe")
    finally:
        pre.pid_vivant = vrai


def section_peut_arreter_et_lie(banc):
    print("== peut_arreter (lance ici, sans fiche) et lie ==")
    vide_presence()
    derniers = {o.id: {o.cle_port_page: LIBRES[o.id]} for o in reg.OUTILS}

    def etat(id, lances):
        return next(e for e in pre.etat_outils(lances, derniers, None) if e["id"] == id)
    e = etat("syslog", {"syslog": {"pid": os.getpid(), "valeurs": {}}})
    verifie((e["etat"], e["peut_arreter"], e["lance_ailleurs"]), ("arrete", True, False),
            "lance ici, PID vivant, sans fiche : peut_arreter")
    verifie("lancé d'ici" in e["raison"], True, "lance ici sans fiche : raison affichee")
    e = etat("syslog", {"syslog": {"pid": pid_mort(), "valeurs": {}}})
    verifie((e["peut_arreter"], e["raison"]), (False, ""), "TEMOIN lance ici, PID mort : pas d'Arreter")
    verifie(etat("syslog", {})["peut_arreter"], False, "TEMOIN jamais lance : pas d'Arreter")
    lie = {"synchro_fork": {"pid": os.getpid(), "valeurs": {}, "lie": True}}
    verifie(etat("synchro_fork", lie)["lie"], True, "lances[id][lie] True, PID vivant -> lie True")
    verifie(etat("synchro_fork", {"synchro_fork": {"pid": os.getpid(), "valeurs": {}, "lie": False}})["lie"], False,
            "TEMOIN lie False -> lie False")
    verifie(etat("synchro_fork", {"synchro_fork": {"pid": pid_mort(), "valeurs": {}, "lie": True}})["lie"], False,
            "lie True mais PID mort -> lie False")
    verifie(all(x["lie"] is False for x in pre.etat_outils({}, derniers, None)), True, "/etat : lie False par defaut")

    banc.lanceur.lances["syslog"] = {"pid": os.getpid(), "valeurs": {}}
    del banc.arrets[:]
    verifie(banc.post("/arrete", {"id": "syslog"}), (200, {"ok": True}), "POST /arrete, lance ici sans fiche -> 200")
    verifie(banc.arrets, [("syslog", os.getpid())], "POST /arrete : PID de lances")
    banc.lanceur.lances.clear()
    verifie(banc.post("/arrete", {"id": "syslog"})[0], 409, "TEMOIN POST /arrete, ni fiche ni lances -> 409")


class FauxSynchro(BaseHTTPRequestHandler):
    reponse = b'{"en_cours": true}'

    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.reponse)))
        self.end_headers()
        self.wfile.write(self.reponse)


def section_route_occupee(banc, git):
    print("== route_occupee : outil muet -> le depot tranche ==")
    ferme = port_libre()
    verifie(ann.route_occupee(ferme, "/execution", git), False, "outil muet, depot propre -> arret permis")
    for nom, dossier in (("MERGE_HEAD", False), ("rebase-merge", True), ("rebase-apply", True)):
        chemin = os.path.join(git, nom)
        if dossier:
            os.mkdir(chemin)
        else:
            open(chemin, "w").close()
        verifie(ann.route_occupee(ferme, "/execution", git), True, f"outil muet, {nom} present -> refus")
        os.rmdir(chemin) if dossier else os.remove(chemin)

    faux = HTTPServer(("127.0.0.1", 0), FauxSynchro)
    threading.Thread(target=faux.serve_forever, daemon=True).start()
    p = faux.server_address[1]
    merge = os.path.join(git, "MERGE_HEAD")
    try:
        FauxSynchro.reponse = b"pas du json"
        open(merge, "w").close()
        verifie(ann.route_occupee(p, "/execution", git), True, "reponse non JSON + MERGE_HEAD -> refus")
        os.remove(merge)
        verifie(ann.route_occupee(p, "/execution", git), False, "reponse non JSON, depot propre -> arret permis")
        FauxSynchro.reponse = b'{"en_cours": true}'
        verifie(ann.route_occupee(p, "/execution", git), True, "TEMOIN en_cours true -> refus (outil cru)")
        FauxSynchro.reponse = b'{"en_cours": false}'
        open(merge, "w").close()
        verifie(ann.route_occupee(p, "/execution", git), False, "en_cours false : l'outil repond, il est cru")
        os.remove(merge)

        # Sans proxy : un proxy d'environnement injoignable ne doit pas changer la reponse.
        sauve = {k: os.environ.get(k) for k in ("http_proxy", "HTTP_PROXY", "no_proxy", "NO_PROXY")}
        try:
            for k in sauve:
                os.environ.pop(k, None)
            os.environ["http_proxy"] = "http://127.0.0.1:%d" % port_libre()
            FauxSynchro.reponse = b'{"en_cours": true}'
            verifie(ann.route_occupee(p, "/execution", git), True, "proxy d'environnement ignore -> en_cours lu")
            import urllib.request
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{p}/execution", timeout=2).read()
                temoin = "lu"
            except OSError:
                temoin = "echec"
            verifie(temoin, "echec", "TEMOIN urlopen par defaut : passe par le proxy -> echec")
        finally:
            for k, v in sauve.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    finally:
        faux.shutdown()
        faux.server_close()

    # Par le serveur : fiche de la synchro sur un port ferme, faux .git avec MERGE_HEAD.
    dossier = vide_presence()
    ecrit_fiche(dossier, "Synchro du fork", ferme, os.getpid())
    open(merge, "w").close()
    del banc.arrets[:]
    verifie(banc.post("/arrete", {"id": "synchro_fork"}), (409, {"erreur": ann.MSG_SYNCHRO}),
            "POST /arrete synchro muette + MERGE_HEAD -> 409")
    verifie(banc.arrets, [], "409 : rien arrete")
    os.remove(merge)
    verifie(banc.post("/arrete", {"id": "synchro_fork"})[0], 200, "TEMOIN synchro muette, depot propre -> 200")
    vide_presence()


def section_navigateur():
    print("== navigateur hors du job ==")
    url = "http://127.0.0.1:7600/"
    appels = []

    def popen(erreur=None):
        def faux(commande, **kw):
            appels.append((commande, kw.get("creationflags"), kw.get("stdin")))
            if erreur is not None and len(appels) == 1:
                raise erreur
            return None
        return faux
    ann.ouvre_navigateur(url, popen())
    commande, drapeaux, entree = appels[0]
    verifie(commande, ["cmd", "/c", "start", "", url], "commande cmd /c start \"\" url")
    verifie(subprocess.list2cmdline(commande), 'cmd /c start "" http://127.0.0.1:7600/', "ligne de commande")
    verifie((bool(drapeaux & CREATE_BREAKAWAY_FROM_JOB), bool(drapeaux & CREATE_NO_WINDOW), entree),
            (True, True, subprocess.DEVNULL), "drapeaux : breakaway + sans fenetre, stdin DEVNULL")
    del appels[:]
    ann.ouvre_navigateur(url, popen(OSError(None, "Acces refuse", None, 5)))
    verifie([a[1] for a in appels], [CREATE_BREAKAWAY_FROM_JOB | CREATE_NO_WINDOW, CREATE_NO_WINDOW],
            "winerror 5 : relance sans breakaway")
    del appels[:]
    ann.ouvre_navigateur(url, popen(FileNotFoundError(2, "cmd introuvable")))
    verifie(len(appels), 1, "TEMOIN FileNotFoundError : pas de relance, pas d'exception")
    src = inspect.getsource(ann.principal)
    verifie(("acces.annonce(False)" in src, "ouvre_navigateur(acces.lien_local())" in src, "annonce(not" in src),
            (True, True, False), "principal : annonce(False) puis ouvre_navigateur")


def principal():
    git = tempfile.mkdtemp(prefix="faux_git_")
    banc = Banc(git)
    try:
        for section in (lambda: section_hote(banc), lambda: section_erreurs(banc), section_iteration,
                        lambda: section_peut_arreter_et_lie(banc), lambda: section_route_occupee(banc, git),
                        section_navigateur):
            section()
            print()
    finally:
        banc.ferme()
        os.environ.pop("OUTILS_TASMOTA_DOSSIER", None)
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
