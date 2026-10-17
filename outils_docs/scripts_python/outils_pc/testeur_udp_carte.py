"""Connexion serie d'UNE carte du testeur UDP : ouverture sans reset, lecture par lignes, reouverture auto.

- Le port est ouvert SANS basculer DTR/RTS (pas de reset de l'ESP32), comme pont_serie.py.
- Les lignes lues sont decoupees sur les octets (UTF-8, errors="replace"), nettoyees des codes ANSI,
  puis passees au Masque (mot de passe Wi-Fi remplace par ***) AVANT tout rappel : ni la page ni
  le journal ne voient le secret.
- Port perdu (ESP32-S3 qui redemarre : le port USB disparait puis reapparait) : la carte reste
  « souhaitee » et la boucle tente de la rouvrir toutes les secondes, sans action de l'utilisateur.
  Un echec d'ouverture demande par l'utilisateur, lui, n'est PAS retente : il recoit l'avertissement.
- Par le PONT SERIE (nom de port « pont:7000 ») : le testeur ne prend pas le port COM, il se branche
  en TCP brut sur pont_serie.py (127.0.0.1:<tcp>), qui garde le port et sa page. Avant, GET /etat du
  pont : pont absent ou port COM ferme -> avertissement (demarrer le script, cliquer « Demarrer »).
  Le pont NE rouvre PAS un port perdu : sur son annonce « [pont] port X perdu », le testeur le lui
  redemande (POST /ouvrir) a chaque tentative ; sur « [pont] port X ferme » (bouton Arreter, flash),
  il attend sans rien redemander.
"""

import json
import re
import threading
import time
import urllib.error
import urllib.request

import serial

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
MAX_TAMPON = 64 * 1024
PERIODE_REOUVERTURE = 1.0
PREFIXE_PONT = "pont:"
PONTS_PROPOSES = (7000, 7001)          # toujours listes, meme pas demarres : l'utilisateur voit l'option
PONTS_CHERCHES = range(7000, 7006)
RE_PONT_PERDU = re.compile(r"^\[pont\] port (\S+) perdu")
RE_PONT_FERME = re.compile(r"^\[pont\] port (\S+) ferme")
SCRIPT_PONT = "outils_docs/scripts_python/outils_pc/pont_serie.py"


class PontIndisponible(OSError):
    """Pont serie absent, ou present avec son port COM ferme : le message dit quoi faire."""


def port_pont(nom):
    """'pont:7000' -> 7000 ; autre nom -> None."""
    nom = str(nom or "")
    if not nom.startswith(PREFIXE_PONT):
        return None
    try:
        tcp = int(nom[len(PREFIXE_PONT):])
    except ValueError:
        raise ValueError(f"port de pont invalide : {nom!r} (attendu pont:7000)") from None
    if not 1 <= tcp <= 65535:
        raise ValueError(f"port de pont invalide : {nom!r}")
    return tcp


def message_pont_absent(tcp):
    return (f"aucun pont serie sur 127.0.0.1:{tcp} : demarrez le script « pont serie » (pioarduino > Custom > "
            f"« Pont serie (TCP/HTTP 127.0.0.1) », ou python {SCRIPT_PONT} --tcp {tcp}), ouvrez-y le port COM de "
            "la carte, puis reessayez")


def etat_pont(tcp, delai=0.5):
    """GET /etat du pont -> dict. PontIndisponible si personne ne repond sur ce port."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{tcp}/etat", timeout=delai) as reponse:
            return json.loads(reponse.read().decode("utf-8"))
    except (OSError, ValueError) as erreur:      # URLError, refus, delai, reponse illisible
        raise PontIndisponible(message_pont_absent(tcp)) from erreur


def demande_ouverture_pont(tcp, port_serie, vitesse, delai=2.0):
    """Le pont rouvre son port COM (route de sa page, en-tete X-Pont). -> True si ouvert."""
    corps = json.dumps({"port": port_serie, "vitesse": int(vitesse)}).encode("utf-8")
    requete = urllib.request.Request(f"http://127.0.0.1:{tcp}/ouvrir", data=corps, method="POST",
                                     headers={"X-Pont": "1", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(requete, timeout=delai):
            return True
    except (OSError, ValueError):                 # 409 : port pas encore revenu ; pont arrete
        return False


def liste_ponts():
    """Ponts a proposer dans la liste des ports : ceux qui repondent sur 7000-7005, plus 7000 et 7001."""
    ponts = []
    for tcp in PONTS_CHERCHES:
        try:
            etat = etat_pont(tcp, delai=0.3)
        except PontIndisponible:
            if tcp in PONTS_PROPOSES:
                ponts.append({"port": f"{PREFIXE_PONT}{tcp}", "pont": True, "usb": False,
                              "description": f"Pont serie 127.0.0.1:{tcp} (pas demarre)"})
            continue
        com = (f"{etat.get('port')} ouvert" if etat.get("ouvert") else "port COM ferme")
        ponts.append({"port": f"{PREFIXE_PONT}{tcp}", "pont": True, "usb": False,
                      "description": f"Pont serie 127.0.0.1:{tcp} ({com})"})
    return ponts


class Masque:
    """Remplace par *** toute occurrence d'un secret dans un texte."""

    def __init__(self):
        self.secrets = set()

    def ajoute(self, secret):
        if secret:
            self.secrets.add(str(secret))

    def applique(self, texte):
        for secret in sorted(self.secrets, key=len, reverse=True):
            texte = texte.replace(secret, "***")
        return texte


def fabrique_defaut(nom, vitesse):
    """Ouvre un port reel (ou loop://) sans toucher a DTR/RTS ; « pont:<tcp> » : le pont serie, en TCP brut."""
    tcp = port_pont(nom)
    if tcp is not None:
        etat = etat_pont(tcp)
        if not etat.get("ouvert"):
            raise PontIndisponible(f"le pont serie 127.0.0.1:{tcp} tourne mais son port COM est ferme : cliquez "
                                   f"« Demarrer » dans sa page http://127.0.0.1:{tcp}")
        # Le pont attend 0,3 s qu'un client parle pour reconnaitre le HTTP : un client muet est un client TCP brut
        return serial.serial_for_url(f"socket://127.0.0.1:{tcp}", timeout=0.2)
    serie = serial.serial_for_url(nom, do_not_open=True, baudrate=int(vitesse), timeout=0.2)
    serie.dtr, serie.rts = False, False
    serie.open()
    return serie


def message_ouverture_echouee(nom, erreur):
    """Texte d'avertissement affiche quand le port ne s'ouvre pas."""
    texte = str(erreur)
    if isinstance(erreur, PontIndisponible):
        return texte
    if "PermissionError" in texte or "denied" in texte.lower() or "(13," in texte or "Acc" in texte:
        return (f"{nom} est deja ouvert par un autre programme (pont serie, moniteur serie...) : fermez-le puis "
                "reessayez - ou, si c'est le pont serie, choisissez « Pont serie 127.0.0.1:<port> » dans la liste")
    if "FileNotFoundError" in texte or "(2," in texte:
        return f"{nom} est introuvable (carte debranchee ?) : {texte}"
    return f"impossible d'ouvrir {nom} : {texte}"


class Carte:
    """Une carte : role 'maitre' ou 'esclave'. Les rappels sont appeles depuis le thread de lecture :
    sur_ligne(role, texte, t), sur_ouverture(role, reouverte), sur_perte(role), sur_note(role, texte)."""

    def __init__(self, role, vitesse, masque, sur_ligne, sur_ouverture, sur_perte, sur_note, fabrique=None):
        self.role, self.vitesse, self.masque = role, int(vitesse), masque
        self.sur_ligne, self.sur_ouverture, self.sur_perte, self.sur_note = sur_ligne, sur_ouverture, sur_perte, sur_note
        self.fabrique = fabrique or fabrique_defaut
        self.serie = None
        self.nom_port = None            # port actuellement ouvert
        self.souhait = None             # port voulu par l'utilisateur (reste rempli pendant une perte)
        self.perdu = False
        self.message = "port ferme"
        self.generation = 0             # +1 a chaque ouverture : arrete les initialisations perimees
        self.verrou = threading.Lock()
        self.tampon = b""
        self.arret = False
        self.dernier_essai = 0.0
        self.pont_relance = None        # port COM a redemander au pont (il l'a perdu : carte redemarree)
        self._pont_coupe = False        # annonce du pont lue : couper la liaison TCP, reprise automatique
        threading.Thread(target=self._boucle, daemon=True).start()

    @property
    def ouvert(self):
        return self.serie is not None

    # ------------------------------------------------------------------ ouverture / fermeture
    def ouvre(self, nom, vitesse):
        """Ouverture demandee par l'utilisateur. -> (ok, message). Un echec n'est pas retente."""
        nom = str(nom).strip()
        with self.verrou:
            self._ferme_sans_verrou()
            self.souhait, self.perdu = None, False
            try:
                serie = self.fabrique(nom, int(vitesse))
            except (serial.SerialException, ValueError, OSError) as erreur:
                self.message = message_ouverture_echouee(nom, erreur)
                return False, self.message
            self._installe(serie, nom, int(vitesse))
            self.souhait = nom
        self.sur_ouverture(self.role, False)
        return True, self.message

    def _installe(self, serie, nom, vitesse):
        self.serie, self.nom_port, self.vitesse, self.tampon = serie, nom, vitesse, b""
        self.generation += 1
        tcp = port_pont(nom)
        self.message = (f"connecte au pont serie http://127.0.0.1:{tcp} (le pont garde le port COM)" if tcp
                        else f"{nom} ouvert a {vitesse} bauds")

    def ferme(self):
        with self.verrou:
            self.souhait, self.perdu = None, False
            self._ferme_sans_verrou()
            self.message = "port ferme"

    def _ferme_sans_verrou(self):
        if self.serie is not None:
            serie, self.serie = self.serie, None
            try:
                serie.close()
            except (serial.SerialException, OSError):
                pass

    def arrete(self):
        self.arret = True
        self.ferme()

    # ------------------------------------------------------------------ ecriture
    def ecrit(self, commande):
        """Une commande = une ligne terminee par \\n. False si le port est ferme. L'echo est masque."""
        commande = commande.replace("\r", " ").replace("\n", " ").strip()
        if not commande:
            return False
        with self.verrou:
            if self.serie is None:
                return False
            try:
                self.serie.write((commande + "\n").encode("utf-8"))
            except (serial.SerialException, OSError):
                return False
        self.sur_note(self.role, "envoi -> " + self.masque.applique(commande))
        return True

    # ------------------------------------------------------------------ lecture
    def _perte(self, serie):
        with self.verrou:
            if self.serie is not serie:
                return
            self._ferme_sans_verrou()
            self.perdu = self.souhait is not None
            self.message = (f"port {self.nom_port} perdu (redemarrage ?) : reouverture automatique..."
                            if self.perdu else "port ferme")
        self.sur_perte(self.role)

    def _boucle(self):
        while not self.arret:
            serie = self.serie
            if serie is None:
                if self.perdu and time.monotonic() - self.dernier_essai >= PERIODE_REOUVERTURE:
                    self.dernier_essai = time.monotonic()
                    self._tente_reouverture()
                else:
                    time.sleep(0.1)
                continue
            try:
                brut = serie.read(4096)
            except (serial.SerialException, OSError, TypeError, AttributeError, ValueError):
                self._perte(serie)
                continue
            if brut:
                self._lignes(brut)
            if self._pont_coupe:
                self._pont_coupe = False
                self._perte(serie)

    def _tente_reouverture(self):
        nom, vitesse = self.souhait, self.vitesse
        if not nom:
            return
        tcp = port_pont(nom)
        if tcp and self.pont_relance:
            try:      # le pont garde la vitesse du port perdu
                demande_ouverture_pont(tcp, self.pont_relance, etat_pont(tcp).get("vitesse") or vitesse)
            except PontIndisponible:
                pass
        try:
            serie = self.fabrique(nom, vitesse)       # echec silencieux : le port n'est pas encore revenu
        except (serial.SerialException, ValueError, OSError):
            return
        with self.verrou:
            if self.souhait != nom or self.serie is not None:
                serie.close()
                return
            self._installe(serie, nom, vitesse)
            self.perdu, self.pont_relance = False, None
        self.sur_ouverture(self.role, True)

    def _lignes(self, brut):
        self.tampon += brut
        if len(self.tampon) > MAX_TAMPON and b"\n" not in self.tampon:
            self.tampon = self.tampon[-MAX_TAMPON:]
        *entieres, self.tampon = self.tampon.split(b"\n")
        for octets in entieres:
            texte = ANSI.sub("", octets.decode("utf-8", "replace")).replace("\r", "").rstrip()
            if texte.strip():
                self._annonce_pont(texte)
                self.sur_ligne(self.role, self.masque.applique(texte), time.time())

    def _annonce_pont(self, texte):
        """Annonce du pont serie sur son flux : la carte a quitte le port (perte ou bouton Arreter)."""
        if port_pont(self.nom_port) is None:
            return
        m = RE_PONT_PERDU.match(texte)
        if m:
            self.pont_relance, self._pont_coupe = m.group(1), True     # redemarrage : a redemander au pont
        elif RE_PONT_FERME.match(texte):
            self.pont_relance, self._pont_coupe = None, True            # Arreter (flash) : ne rien redemander
