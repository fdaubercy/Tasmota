"""Registre des onglets de la page « Navigateur FTP des cartes » : le FTP d'une carte ne s'eteint qu'avec le dernier onglet.

Chaque onglet de la page se presente par un identifiant (16 a 32 caracteres hexadecimaux, tire par la page) a chaque sondage
`GET /etat?onglet=` et a l'ouverture (`POST /ouvre`). Un onglet qui part le dit par sendBeacon (`POST /ferme {onglet}`) :
`ferme(ident)` rend True quand il n'en reste aucun. Un onglet qui disparait sans le dire (plantage, veille) est elague apres `delai` s
sans nouvelle : `perdu()` le voit et la session (`ftp_cartes_session.Session.tic`) eteint alors le FTP.
`delai` = 90 s et non 15 s : Chrome ralentit a une fois par minute les minuteries d'un onglet cache depuis 5 min ; un delai plus
court eteindrait le FTP sous un onglet seulement cache.
Une session ouverte sans identifiant (client ancien, curl) n'est jamais « perdue » : seule l'inactivite la ferme.
Banc : test_ftp_cartes_onglets.py (horloge simulee).
"""
import re
import threading
import time

IDENT = re.compile(r"[0-9a-f]{16,32}")


def valide(ident):
    return isinstance(ident, str) and IDENT.fullmatch(ident) is not None


class Onglets:
    def __init__(self, horloge=time.monotonic, delai=90, maximum=32):
        self._horloge, self._delai, self._maximum = horloge, delai, maximum
        self._vus = {}                       # identifiant -> derniere vue ; l'ordre d'insertion va du plus ancien au plus recent
        self._connu = False                  # un onglet a ete vu depuis l'ouverture (reinitialise() le remet a False)
        self._verrou = threading.Lock()      # vu() vient des sondages, hors du verrou de la session

    def _elague(self):
        limite = self._horloge() - self._delai
        for ident in [i for i, t in self._vus.items() if t < limite]:
            del self._vus[ident]

    def vu(self, ident):
        """Enregistre ou rafraichit un onglet ; un identifiant invalide est ignore ; au-dela de `maximum`, le plus ancien est oublie."""
        if not valide(ident):
            return
        with self._verrou:
            self._vus.pop(ident, None)
            self._vus[ident] = self._horloge()
            while len(self._vus) > self._maximum:
                del self._vus[next(iter(self._vus))]
            self._connu = True

    def ferme(self, ident):
        """Retire l'onglet, elague les silencieux ; True si le registre est alors vide (le dernier onglet est parti)."""
        with self._verrou:
            if valide(ident):
                self._vus.pop(ident, None)
            self._elague()
            return not self._vus

    def perdu(self):
        """True si un onglet au moins a ete vu depuis l'ouverture et qu'il n'en reste aucun (tous partis ou silencieux)."""
        with self._verrou:
            self._elague()
            return self._connu and not self._vus

    def reinitialise(self):
        with self._verrou:
            self._vus.clear()
            self._connu = False
