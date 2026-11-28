"""Liaison HTTP du pont serie : la console web d'une carte Tasmota a la place d'un port serie.

Le pont (pont_serie.py) ouvre « http://<ip> » comme un port : LiaisonHttp imite l'objet pyserial
(read, write, close), si bien que la lecture, la diffusion aux pages et au TCP brut restent les memes.

Protocole : celui de la console web Tasmota (xdrv_01_9_webserver.ino::HandleConsoleRefresh).
    GET /cs?c2=<index>            -> "<pointeur>}1<drapeau>}1<lignes separees par \\n>}1"
                                     index 0 = tout le tampon de log ; ensuite, le pointeur recu
    GET /cs?c2=<index>&c1=<cmd>   -> execute la commande (comme la console web), meme reponse
Sans Referer, le controle de HttpCheckPriviledgedAccess laisse passer. Le niveau des lignes lues est
celui du log web de la carte (WebLog), pas SerialLog.

shortcut: pas de WebPassword (401 = refus clair a l'ouverture) ; a ajouter si une carte en a un,
en lisant le mot de passe cote PC, jamais depuis la page (regle des outils PC).
"""

import re
import time
import urllib.error
import urllib.parse
import urllib.request

PREFIXE = "http://"
INTERVALLE = 2.0          # s entre deux lectures du log (la console web de Tasmota : WebRefresh, 2345 ms) ; menage les ESP32 sans PSRAM
DELAI = 3                 # s par requete
PERTE = 10                # s sans reponse -> liaison perdue (le pont ferme le « port »)
MAX_REPONSE = 1 << 20     # octets lus au plus par reponse (le tampon de log d'une carte fait quelques Ko)
BOUCLES = ("localhost", "127.", "0.", "169.254.")   # le PC lui-meme ou le lien local : jamais une carte


class DelaiDepasse(OSError):
    """Requete partie, reponse absente dans le delai : une commande a pu etre executee."""


def est_boucle(url):
    """'http://127.0.0.1:7700' -> True : adresse refusee quand l'ouverture vient d'un autre appareil."""
    hote = url[len(PREFIXE):].rsplit(":", 1)[0].lower() if est_http(url) else ""
    return hote.startswith(BOUCLES)


class _SansRedirection(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None                       # un 3xx reste une erreur : la requete ne part que vers l'hote saisi


_OUVREUR = urllib.request.build_opener(urllib.request.ProxyHandler({}), _SansRedirection)   # LAN direct, sans proxy
_HOTE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.\-]{0,251}[A-Za-z0-9])?(?::\d{1,5})?")


def est_http(nom_port):
    return isinstance(nom_port, str) and nom_port.lower().startswith(PREFIXE)


def normalise(saisie):
    """'192.168.1.50', 'http://carte.local:8080/' -> 'http://192.168.1.50'. ValueError si ce n'est pas un hote."""
    hote = str(saisie).strip()
    if hote.lower().startswith(PREFIXE):
        hote = hote[len(PREFIXE):]
    hote = hote.rstrip("/")
    if not _HOTE.fullmatch(hote) or (":" in hote and not 0 < int(hote.rsplit(":", 1)[1]) < 65536):
        raise ValueError(f"adresse invalide : '{saisie}' (attendu : IP ou nom, port facultatif)")
    return PREFIXE + hote


def decoupe(reponse):
    """Reponse de /cs -> (pointeur suivant, lignes). ValueError si ce n'est pas une console Tasmota."""
    morceaux = reponse.split("}1", 2)
    if len(morceaux) != 3 or not morceaux[0].isdigit():
        raise ValueError("reponse inattendue : ce n'est pas la console web d'une carte Tasmota")
    corps = morceaux[2][:-2] if morceaux[2].endswith("}1") else morceaux[2]
    return int(morceaux[0]), [ligne for ligne in corps.split("\n") if ligne]


class LiaisonHttp:
    """Console web d'une carte vue comme un port serie. OSError a l'ouverture si la carte ne repond pas."""

    def __init__(self, url):
        self.url = normalise(url)
        self.index = 0
        self.reste = b""                  # debut de commande ecrit sans fin de ligne
        self.prochaine = 0.0              # heure de la prochaine lecture du log
        self.derniere_reponse = time.time()
        self.ferme = False
        self.premiere = self._console()   # verifie la carte des l'ouverture (rendu au premier read)

    def _console(self, commande=None):
        """Une requete /cs ; renvoie le texte des nouvelles lignes (fin de ligne comprise) et avance l'index."""
        parametres = {"c2": self.index}
        if commande is not None:
            parametres["c1"] = commande
        try:
            requete = urllib.parse.urlencode(parametres, quote_via=urllib.parse.quote)   # espaces en %20, comme la console
            with _OUVREUR.open(f"{self.url}/cs?{requete}", timeout=DELAI) as r:
                texte = r.read(MAX_REPONSE).decode("utf-8", "replace")
        except urllib.error.HTTPError as erreur:
            if erreur.code == 401:
                raise OSError(f"{self.url} demande un mot de passe web (WebPassword) : non gere par le pont") from None
            raise OSError(f"{self.url} : HTTP {erreur.code}") from None
        except TimeoutError:
            # connexion etablie, requete envoyee (urllib range un echec de connexion en URLError) : reponse en retard
            raise DelaiDepasse(f"{self.url} : pas de reponse en {DELAI} s") from None
        except (urllib.error.URLError, ConnectionError) as erreur:
            raise OSError(f"{self.url} injoignable : {getattr(erreur, 'reason', erreur)}") from None
        try:
            index, lignes = decoupe(texte)
        except ValueError as erreur:
            raise OSError(f"{self.url} : {erreur}") from None
        self.derniere_reponse = time.time()
        if commande is None:              # seule la lecture avance : la reponse d'une commande est relue ensuite
            self.index = index
        return "".join(ligne + "\n" for ligne in lignes).encode("utf-8")

    def read(self, _taille=4096):
        """Comme pyserial (timeout 0,2 s) : b'' si rien de neuf. OSError apres PERTE s sans reponse."""
        if self.ferme:
            raise OSError("liaison fermee")
        if self.premiere:
            octets, self.premiere = self.premiere, b""
            return octets
        attente = self.prochaine - time.time()
        if attente > 0:
            time.sleep(min(attente, 0.2))
            return b""
        self.prochaine = time.time() + INTERVALLE
        try:
            return self._console()
        except OSError:
            if time.time() - self.derniere_reponse > PERTE:
                raise
            return b""                    # coupure breve (Wi-Fi) : on reessaie a la lecture suivante

    def write(self, octets):
        """Chaque ligne complete part comme une commande de la console web ; le reste attend sa fin de ligne."""
        lignes = (self.reste + bytes(octets)).replace(b"\r\n", b"\n").replace(b"\r", b"\n").split(b"\n")
        self.reste = lignes.pop()
        for ligne in lignes:
            commande = ligne.decode("utf-8", "replace").strip()
            if commande:
                try:
                    self._console(commande)
                except DelaiDepasse:
                    pass                  # la carte a pu l'executer : surtout ne pas la faire renvoyer (Power TOGGLE)
        return len(octets)

    def close(self):
        self.ferme = True
