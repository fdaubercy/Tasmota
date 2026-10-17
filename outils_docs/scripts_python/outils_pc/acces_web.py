"""Acces web des outils PC : lien cliquable, ouverture du navigateur, acces depuis le reseau local.

Utilise par pont_serie, testeur_udp, sniffeur_mqtt, syslog_tasmota, sniffeur_modbus (ce dossier) et
par maintenance/synchro_fork_web.py.

Regle d'acces (decidee le 2026-10-17) :
  - depuis CE PC (127.0.0.1, ::1) : comme avant, sans jeton. La protection contre une page tierce
    ouverte dans le navigateur reste celle de chaque outil : en-tete X-... sur les POST et meme
    origine, comparee a 127.0.0.1 / localhost seulement (pas au Host : parade au DNS rebinding) ;
  - depuis un autre appareil du reseau : jeton obligatoire. Tire au lancement, il figure dans le
    lien « reseau » affiche par la console. Au premier passage le serveur le pose en cookie
    (HttpOnly, SameSite=Strict, un nom par port) et redirige vers l'URL sans jeton : la page, ses
    fetch et ses EventSource n'ont rien a transmettre ;
  - --local : ecoute sur 127.0.0.1 seulement (le comportement d'avant).

Integration dans un outil :
    acces_web.ajoute_options(parser)                       # --local, --sans-navigateur
    acces = acces_web.Acces(args.http, args.local, "Sniffeur MQTT")
    serveur = ThreadingHTTPServer((acces.hote, args.http), ...)
    acces.annonce(not args.sans_navigateur)                # liens + ouverture du navigateur
    # en tete de do_GET et do_POST :
    if not acces.controle(self): return
    # controle d'origine des POST :
    acces.origine_autorisee(self)

Fiche de presence (annuaire des outils, port 7600) : annonce() depose presence/<port>.json dans le
dossier de donnees (%LOCALAPPDATA%/outils_tasmota, ou OUTILS_TASMOTA_DOSSIER s'il est defini) avec
nom, port, pid, debut, jeton (None si --local), local, lance_par (variable OUTILS_TASMOTA_LANCE_PAR,
posee par l'annuaire quand c'est lui qui lance l'outil). L'annuaire s'en sert pour savoir qui tourne,
avec quel PID et quel jeton. La fiche est ecrite de facon atomique et effacee a la sortie normale
(atexit) ; apres un arret brutal elle reste : l'annuaire verifie le PID avant de la croire.
"""

import atexit
import hmac
import json
import os
import secrets
import socket
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

PAGE_REFUSEE = ("<!doctype html><html lang=fr><meta charset=utf-8><title>Acces refuse</title>"
                "<body style='font-family:sans-serif;margin:2em'><h1>Acces refuse</h1>"
                "<p>Depuis un autre appareil, ouvrez le lien <b>« depuis le reseau »</b> affiche par la "
                "console de l'outil : il contient le jeton de cette session (un nouveau a chaque lancement).</p>")


def ajoute_options(parser):
    parser.add_argument("--local", action="store_true",
                        help="n'ecouter que sur 127.0.0.1 (pas d'acces depuis un autre appareil du reseau)")
    parser.add_argument("--sans-navigateur", action="store_true",
                        help="ne pas ouvrir la page dans le navigateur au lancement")


def ips_reseau():
    """IPv4 de ce PC sur le reseau local (hors 127.x et 169.254.x), celle de la route par defaut d'abord."""
    ips = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))     # UDP : aucun paquet emis, seule la route est choisie
            ips.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    return [ip for ip in ips if not ip.startswith(("127.", "169.254.", "0."))]


def est_local(adresse):
    """Adresse cliente de ce PC (boucle locale IPv4, IPv6, ou IPv4 projetee en IPv6)."""
    ip = str(adresse[0] if isinstance(adresse, tuple) else adresse)
    if ip.startswith("::ffff:"):
        ip = ip[7:]
    return ip.startswith("127.") or ip == "::1"


def dossier_donnees():
    """Dossier de donnees des outils : OUTILS_TASMOTA_DOSSIER, sinon %LOCALAPPDATA%\\outils_tasmota."""
    force = os.environ.get("OUTILS_TASMOTA_DOSSIER")
    if force:
        return Path(force)
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "outils_tasmota"


def dossier_presence():
    """Dossier des fiches de presence (cree a la demande)."""
    dossier = dossier_donnees() / "presence"
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


class Acces:
    def __init__(self, port, local=False, nom="outil"):
        self.port = int(port)
        self.local = bool(local)
        self.nom = nom
        self.hote = "127.0.0.1" if self.local else "0.0.0.0"
        self.jeton = secrets.token_urlsafe(18)
        self.cookie = f"jeton_{self.port}"      # les cookies ignorent le port : un nom par outil

    def lien_local(self, chemin="/"):
        return f"http://127.0.0.1:{self.port}{chemin}"

    def liens_reseau(self, chemin="/"):
        if self.local:
            return []
        return [f"http://{ip}:{self.port}{chemin}?jeton={self.jeton}" for ip in ips_reseau()]

    def annonce(self, ouvrir=True, chemin="/"):
        """Affiche les liens (Ctrl+clic dans le terminal VS Code) et ouvre la page sur ce PC."""
        print(f"{self.nom} -> {self.lien_local(chemin)}   (ce PC : Ctrl+clic sur le lien)", flush=True)
        reseau = self.liens_reseau(chemin)
        for lien in reseau:
            print(f"   depuis un autre appareil du reseau : {lien}", flush=True)
        if self.local:
            print("   (--local : pas d'acces depuis le reseau)", flush=True)
        elif not reseau:
            print("   (aucune adresse reseau trouvee : acces depuis ce PC seulement)", flush=True)
        self._ecrit_presence()
        if ouvrir:
            threading.Timer(0.6, webbrowser.open, (self.lien_local(chemin),)).start()

    def _fiche(self):
        return dossier_presence() / f"{self.port}.json"

    def _ecrit_presence(self):
        """Depose la fiche de presence (atomique : .tmp puis replace) ; n'empeche jamais l'outil de demarrer."""
        try:
            fiche = self._fiche()
            contenu = {"nom": self.nom, "port": self.port, "pid": os.getpid(),
                       "debut": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                       "jeton": None if self.local else self.jeton, "local": self.local,
                       "lance_par": os.environ.get("OUTILS_TASMOTA_LANCE_PAR", "")}
            tmp = fiche.with_name(fiche.name + ".tmp")
            tmp.write_text(json.dumps(contenu, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, fiche)
            atexit.register(self.efface_presence)
        except OSError as e:
            print(f"   (fiche de presence non ecrite : {e})", flush=True)

    def efface_presence(self):
        """Supprime la fiche si elle porte notre PID ; silencieux sinon (autre processus, fiche absente)."""
        try:
            fiche = self._fiche()
            if json.loads(fiche.read_text(encoding="utf-8")).get("pid") == os.getpid():
                fiche.unlink()
        except (OSError, ValueError):
            pass

    def _jeton_valide(self, donne):
        return isinstance(donne, str) and hmac.compare_digest(donne.encode("utf-8"), self.jeton.encode("utf-8"))

    def _jeton_cookie(self, handler):
        for morceau in (handler.headers.get("Cookie", "") or "").split(";"):
            nom, _, valeur = morceau.strip().partition("=")
            if nom == self.cookie:
                return valeur
        return None

    def autorise(self, handler):
        """Requete autorisee sans rien envoyer : ce PC, ou jeton valide (URL ou cookie)."""
        if est_local(handler.client_address):
            return True
        donne = dict(parse_qsl(urlsplit(handler.path).query, keep_blank_values=True)).get("jeton")
        return self._jeton_valide(donne) or self._jeton_valide(self._jeton_cookie(handler))

    def controle(self, handler):
        """En tete de do_GET / do_POST. True : continuer. False : reponse deja envoyee (403 ou redirection)."""
        if est_local(handler.client_address):
            return True
        url = urlsplit(handler.path)
        params = parse_qsl(url.query, keep_blank_values=True)
        donne = dict(params).get("jeton")
        if self._jeton_valide(donne) and handler.command == "GET":
            # Jeton pose en cookie, puis retire de l'adresse (historique, copie du lien, en-tete Referer).
            reste = urlencode([(k, v) for k, v in params if k != "jeton"])
            handler.send_response(303)
            handler.send_header("Location", url.path + ("?" + reste if reste else ""))
            handler.send_header("Set-Cookie", f"{self.cookie}={self.jeton}; HttpOnly; SameSite=Strict; Path=/")
            handler.send_header("Content-Length", "0")
            handler.end_headers()
            return False
        if self._jeton_valide(donne) or self._jeton_valide(self._jeton_cookie(handler)):
            return True
        # Corps de la requete non lu : en HTTP/1.1 la connexion ne doit pas resservir (sinon ce corps
        # serait lu comme la requete suivante).
        handler.close_connection = True
        corps = PAGE_REFUSEE.encode("utf-8")
        handler.send_response(403)
        handler.send_header("Content-Type", "text/html; charset=utf-8")
        handler.send_header("Content-Length", str(len(corps)))
        handler.end_headers()
        handler.wfile.write(corps)
        return False

    def origines(self, handler):
        """Origines admises pour un POST. Ce PC : 127.0.0.1 / localhost seulement (pas le Host, que le
        DNS rebinding controle). Autre appareil (jeton deja verifie) : en plus, l'hote qu'il a vise."""
        admises = {f"http://127.0.0.1:{self.port}", f"http://localhost:{self.port}"}
        if not est_local(handler.client_address):
            hote = handler.headers.get("Host", "")
            if hote:
                admises.add(f"http://{hote}")
        return admises

    def origine_autorisee(self, handler):
        origine = handler.headers.get("Origin", "")
        return not origine or origine in self.origines(handler)
