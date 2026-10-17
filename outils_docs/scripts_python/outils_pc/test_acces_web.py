"""Banc de acces_web.py (acces des outils PC depuis le reseau). Code de sortie 0 = vert.

« Autre appareil » simule en appelant le serveur par l'IP reseau de ce PC : le client n'est alors
plus 127.0.0.1. Sans adresse reseau (PC hors ligne), ces cas sont sautes et le banc le dit.
Temoin : un Acces dont controle() laisse tout passer DOIT faire echouer les cas « refuse ».
"""

import http.client
import json
import os
import shutil
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import acces_web

ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def serveur(acces):
    class Gestionnaire(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"           # comme les outils : connexions maintenues

        def log_message(self, *a):
            pass

        def _rep(self, statut, corps=b"ok"):
            self.send_response(statut)
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

        def do_GET(self):
            if acces.controle(self):
                self._rep(200)

        def do_POST(self):
            if not acces.controle(self):
                return
            self._rep(200 if acces.origine_autorisee(self) else 403)

    srv = ThreadingHTTPServer(("0.0.0.0", 0), Gestionnaire)
    acces.port = srv.server_address[1]
    acces.cookie = f"jeton_{acces.port}"
    Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def requete(hote, port, methode="GET", chemin="/", entetes=None):
    c = http.client.HTTPConnection(hote, port, timeout=5)
    c.request(methode, chemin, body=b"" if methode == "POST" else None, headers=entetes or {})
    r = c.getresponse()
    r.read()
    c.close()
    return r.status, dict(r.getheaders())


def cas_refus(acces, ip, port):
    """Les cas qui doivent etre refuses ; rend le nombre de refus obtenus."""
    refus = 0
    refus += requete(ip, port)[0] == 403
    refus += requete(ip, port, chemin="/?jeton=faux")[0] == 403
    refus += requete(ip, port, "POST", "/x")[0] == 403
    refus += requete(ip, port, entetes={"Cookie": f"{acces.cookie}=faux"})[0] == 403
    return refus


def keep_alive_apres_refus(ip, port):
    """POST refuse avec un corps « GET /pirate ... », puis une 2e requete sur la meme connexion.
    Attendu : connexion fermee. Sinon le corps non lu serait servi comme requete suivante."""
    import socket
    corps = b"GET /pirate HTTP/1.1\r\nHost: x\r\n\r\n"
    with socket.create_connection((ip, port), timeout=5) as s:
        s.sendall(b"POST /x HTTP/1.1\r\nHost: x\r\nContent-Length: %d\r\n\r\n" % len(corps) + corps)
        recu = b""
        try:
            while True:
                morceau = s.recv(4096)
                if not morceau:
                    break
                recu += morceau
        except socket.timeout:
            return "ouverte"
    return "fermee" if recu.count(b"HTTP/1.") == 1 else "resservie"


def lit_fiche(dossier, port):
    chemin = os.path.join(dossier, "presence", f"{port}.json")
    if not os.path.exists(chemin):
        return None
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def cas_presence():
    """Fiche de presence ecrite par annonce(), effacee par efface_presence() / a la sortie."""
    dossier = tempfile.mkdtemp(prefix="banc_presence_")
    os.environ["OUTILS_TASMOTA_DOSSIER"] = dossier
    os.environ.pop("OUTILS_TASMOTA_LANCE_PAR", None)
    try:
        verifie(str(acces_web.dossier_donnees()), dossier, "dossier_donnees suit OUTILS_TASMOTA_DOSSIER")
        verifie(acces_web.dossier_presence(), acces_web.dossier_donnees() / "presence",
                "dossier_presence = donnees/presence")

        a = acces_web.Acces(7999, False, "Outil test")
        verifie(lit_fiche(dossier, 7999), None, "pas de fiche avant annonce() (le constructeur n'ecrit rien)")
        a.annonce(ouvrir=False)
        f = lit_fiche(dossier, 7999) or {}
        verifie(f.get("nom"), "Outil test", "presence_ecrite : nom")
        verifie(f.get("port"), 7999, "presence_ecrite : port")
        verifie(f.get("pid"), os.getpid(), "presence_ecrite : pid")
        verifie(f.get("jeton"), a.jeton, "presence_ecrite : jeton")
        verifie(f.get("local"), False, "presence_ecrite : local")
        verifie(f.get("lance_par"), "", "presence_ecrite : lance_par vide par defaut")
        verifie(isinstance(f.get("debut"), str) and len(f["debut"]) == 19 and f["debut"][10] == "T", True,
                "presence_ecrite : debut AAAA-MM-JJTHH:MM:SS")
        verifie(sorted(f), sorted(["nom", "port", "pid", "debut", "jeton", "local", "lance_par"]),
                "presence_ecrite : exactement les 7 cles")
        verifie([n for n in os.listdir(os.path.join(dossier, "presence")) if n.endswith(".tmp")], [],
                "ecriture atomique : aucun .tmp restant")

        acces_web.Acces(7998, True, "x").annonce(False)
        verifie((lit_fiche(dossier, 7998) or {}).get("jeton", "absent"), None, "presence_locale_sans_jeton")
        verifie((lit_fiche(dossier, 7998) or {}).get("local"), True, "presence_locale : local vrai")

        os.environ["OUTILS_TASMOTA_LANCE_PAR"] = "annuaire"
        acces_web.Acces(7997, True, "y").annonce(False)
        verifie((lit_fiche(dossier, 7997) or {}).get("lance_par"), "annuaire", "lance_par depuis l'environnement")
        os.environ.pop("OUTILS_TASMOTA_LANCE_PAR")

        a.efface_presence()
        verifie(lit_fiche(dossier, 7999), None, "efface_presence : fiche supprimee")
        a.efface_presence()                                   # deja absente : silencieux
        a.annonce(ouvrir=False)
        chemin = os.path.join(dossier, "presence", "7999.json")
        etrangere = dict(lit_fiche(dossier, 7999), pid=1)
        with open(chemin, "w", encoding="utf-8") as fh:
            json.dump(etrangere, fh)
        a.efface_presence()
        verifie((lit_fiche(dossier, 7999) or {}).get("pid"), 1, "efface_presence : fiche au pid etranger gardee")
        # Temoin : la meme fiche au NOTRE pid doit, elle, etre effacee (sinon le cas ci-dessus ne prouve rien).
        with open(chemin, "w", encoding="utf-8") as fh:
            json.dump(dict(etrangere, pid=os.getpid()), fh)
        a.efface_presence()
        verifie(lit_fiche(dossier, 7999), None, "TEMOIN : meme fiche au pid propre -> effacee")

        code = ("import acces_web; acces_web.Acces(7996, True, 'sous-processus').annonce(False)")
        r = subprocess.run([sys.executable, "-c", code], cwd=os.path.dirname(os.path.abspath(__file__)),
                           capture_output=True, text=True, timeout=30)
        verifie(r.returncode, 0, "sous-processus : sortie normale" + (f" ({r.stderr.strip()})" if r.returncode else ""))
        verifie(lit_fiche(dossier, 7996), None, "presence_sous_processus : atexit efface la fiche")
        # Temoin : la fiche existait bien pendant la vie du sous-processus.
        code2 = ("import acces_web, os; acces_web.Acces(7995, True, 'z').annonce(False); "
                 "print(os.path.exists(os.path.join(os.environ['OUTILS_TASMOTA_DOSSIER'], 'presence', '7995.json')))")
        r = subprocess.run([sys.executable, "-c", code2], cwd=os.path.dirname(os.path.abspath(__file__)),
                           capture_output=True, text=True, timeout=30)
        verifie(r.stdout.strip().splitlines()[-1:], ["True"], "TEMOIN sous-processus : fiche presente avant la sortie")
    finally:
        os.environ.pop("OUTILS_TASMOTA_DOSSIER", None)
        os.environ.pop("OUTILS_TASMOTA_LANCE_PAR", None)
        shutil.rmtree(dossier, ignore_errors=True)


def principal():
    cas_presence()
    acces = acces_web.Acces(0, False, "banc")
    srv = serveur(acces)
    port = acces.port
    ips = acces_web.ips_reseau()

    verifie(acces.hote, "0.0.0.0", "par defaut : ecoute sur tout le reseau")
    verifie(acces_web.Acces(7100, True).hote, "127.0.0.1", "--local : 127.0.0.1 seulement")
    verifie(acces_web.Acces(7100, True).liens_reseau(), [], "--local : aucun lien reseau")
    verifie(acces_web.est_local(("::ffff:127.0.0.1", 1)), True, "IPv4 projetee en IPv6 = ce PC")
    verifie(acces_web.est_local(("192.168.0.3", 1)), False, "IP du reseau = autre appareil")

    # -- ce PC : comme avant
    verifie(requete("127.0.0.1", port)[0], 200, "ce PC : page sans jeton")
    verifie(requete("127.0.0.1", port, "POST", "/x", {"Origin": f"http://127.0.0.1:{port}"})[0], 200,
            "ce PC : POST de meme origine")
    verifie(requete("127.0.0.1", port, "POST", "/x", {"Origin": f"http://evil.example:{port}",
                                                      "Host": f"evil.example:{port}"})[0], 403,
            "ce PC : origine etrangere refusee meme si Host concorde (DNS rebinding)")

    if not ips:
        print("SAUTE  autre appareil : aucune adresse reseau sur ce PC")
    else:
        ip = ips[0]
        verifie(requete(ip, port)[0], 403, f"autre appareil ({ip}) : page sans jeton refusee")
        verifie(requete(ip, port, chemin="/?jeton=faux")[0], 403, "autre appareil : mauvais jeton refuse")
        statut, entetes = requete(ip, port, chemin=f"/?a=1&jeton={acces.jeton}")
        verifie(statut, 303, "autre appareil : bon jeton -> redirection")
        verifie(entetes.get("Location"), "/?a=1", "... vers l'adresse sans jeton, autres parametres gardes")
        cookie = entetes.get("Set-Cookie", "")
        verifie(cookie.startswith(f"{acces.cookie}={acces.jeton};") and "HttpOnly" in cookie
                and "SameSite=Strict" in cookie, True, "... jeton pose en cookie HttpOnly SameSite=Strict")
        avec = {"Cookie": f"autre=1; {acces.cookie}={acces.jeton}"}
        verifie(requete(ip, port, entetes=avec)[0], 200, "autre appareil : page avec le cookie")
        verifie(requete(ip, port, "POST", "/x", dict(avec, Origin=f"http://{ip}:{port}"))[0], 200,
                "autre appareil : POST avec cookie, origine = hote vise")
        verifie(requete(ip, port, "POST", "/x", dict(avec, Origin="http://evil.example"))[0], 403,
                "autre appareil : POST d'une origine etrangere refuse")
        verifie(requete(ip, port, "POST", "/x")[0], 403, "autre appareil : POST sans jeton refuse")
        verifie(requete(ip, port, entetes={"Cookie": "jeton_1=" + acces.jeton})[0], 403,
                "autre appareil : cookie d'un autre outil (autre port) ignore")
        verifie(cas_refus(acces, ip, port), 4, "les 4 cas de refus")
        verifie(keep_alive_apres_refus(ip, port), "fermee", "HTTP/1.1 : POST refuse (corps non lu) -> connexion fermee")

        # Temoin : un controle qui laisse tout passer doit faire tomber les cas de refus.
        acces.controle = lambda handler: True
        verifie(cas_refus(acces, ip, port) < 4, True, "TEMOIN controle inactif : les refus tombent")
    srv.shutdown()

    print()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
