"""Session FTP d'une carte Tasmota (page « Navigateur FTP des cartes ») : allume le serveur FTP de la carte par HTTP
(`UfsFTP 1|2`), lui parle par ftplib, l'eteint (`UfsFTP 0`) a chaque fin de session.

Une carte active a la fois ; un verrou autour de toute operation FTP (le serveur de la carte n'accepte qu'un client).
La carte deconnecte un client muet depuis 5 min sans eteindre son serveur : chaque operation commence par un NOOP de
controle et, si la session est tombee, la rouvre une fois sans `UfsFTP` supplementaire. Les 15 min (`inactivite`) sans
action sont comptees ici par `tic()` (appele periodiquement par le serveur web), qui eteint alors le FTP.
Support : `UfsFTP 1` = SD si montee, sinon la flash ; `UfsFTP 2` = flash. La SD est donc exigee par `ouvre(.., "sd")`
(`Ufs` : premier objet de type 1), jamais la flash sous l'etiquette SD. Les identifiants viennent du .h
(`ftp_cartes_liste.identifiants`), ne sortent jamais d'ici et sont masques dans les messages.
Spec : docs/superpowers/specs/2026-11-20-navigateur-ftp-cartes-design.md §7 et §9. Banc : test_ftp_cartes_session.py.
"""
import ftplib
import io
import re
import socket
import threading
import time
import zipfile
from pathlib import Path

import build_ota_http
import ftp_cartes_liste

DEPOT = Path(__file__).resolve().parents[3]
DELAI_ALLUMAGE = 10          # s : attente du port 21 apres UfsFTP
DELAI_FTP = 30               # s : une operation FTP
INACTIVITE = 900             # s : sans action, le FTP est eteint
ADRESSE = re.compile(r"[A-Za-z0-9.-]+")
OBJET_UFS = re.compile(r'\{\s*"Type"\s*:\s*(\d+)\s*,\s*"Size"\s*:\s*(\d+)\s*,\s*"Free"\s*:\s*(\d+)\s*\}')
ERREURS_RESEAU = (OSError, EOFError, ftplib.error_temp, ftplib.error_proto)


class RefusFtp(Exception):
    """Refus ou echec metier, message lisible (code HTTP 409 cote web)."""


def valide_chemin(chemin):
    """Chemin de la carte : absolu, sans `..`, sans caractere de controle, 255 caracteres au plus. Rend le chemin normalise."""
    if not isinstance(chemin, str) or not chemin.startswith("/"):
        raise ValueError("chemin absolu attendu")
    if len(chemin) > 255:
        raise ValueError("chemin trop long (255 caracteres au plus)")
    if any(ord(c) < 32 or ord(c) == 127 for c in chemin):
        raise ValueError("caractere de controle interdit")
    if chemin == "/":
        return chemin
    morceaux = chemin[1:-1 if chemin.endswith("/") else None].split("/")
    if any(m in ("", ".", "..") for m in morceaux):
        raise ValueError("segment vide, « . » ou « .. » interdit")
    return "/" + "/".join(morceaux)


def protege(chemin):
    """True si la suppression exige une seconde confirmation : autoexec, persist, .bec, .drvset*, dossiers /sd et /json."""
    p = chemin.rstrip("/") or "/"
    nom = p.rsplit("/", 1)[-1]
    return p in ("/sd", "/json") or nom in ("autoexec.be", "autoexec.bat", "_persist.json") \
        or nom.endswith(".bec") or nom.startswith(".drvset")


def _nom_sain(nom):
    """Nom rendu par la carte : un segment simple (ni `/`, ni `\`, ni controle, ni . ou ..), sinon il est ignore."""
    return bool(nom) and nom not in (".", "..") and len(nom) <= 255 and "/" not in nom and "\\" not in nom         and not any(ord(c) < 32 or ord(c) == 127 for c in nom)


def _lit_ufs(texte):
    """[(type, taille_ko, libre_ko)] d'une reponse `Ufs` (pas du JSON valide a deux supports : lecture par regex)."""
    return [tuple(int(x) for x in m) for m in OBJET_UFS.findall(texte or "")]


def _date_mlsd(valeur):
    """20261103142501 -> 2026-11-03 14:25:01 ; autre forme rendue telle quelle."""
    m = re.fullmatch(r"(\d{4})(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(?:\.\d+)?", valeur or "")
    return "%s-%s-%s %s:%s:%s" % m.groups() if m else (valeur or "")


class Session:
    def __init__(self, commande=build_ota_http._commande, fabrique_ftp=ftplib.FTP, horloge=time.monotonic,
                 inactivite=INACTIVITE, identifiants=None, port=21, delai_allumage=DELAI_ALLUMAGE):
        self._commande, self._fabrique, self._horloge = commande, fabrique_ftp, horloge
        self._inactivite, self._port, self._delai_allumage = inactivite, port, delai_allumage
        self._identifiants = identifiants or (lambda fw: ftp_cartes_liste.identifiants(DEPOT, fw))
        self._verrou = threading.RLock()
        self._ftp = None
        self._carte, self._mdp, self._utilisateur, self._objets = None, "", "", []
        self.noms_ignores = []               # noms de la carte refuses par _nom_sain (zip-slip, suppression hors dossier)
        self._allume = False                 # UfsFTP 1|2 envoye, UfsFTP 0 pas encore
        self._env, self._support, self._etat, self._message, self._sd = "", "", "eteint", "", None
        self._derniere = 0.0
        self.derniere_raison = ""

    # ---- etat -------------------------------------------------------------------------------------------------
    def etat(self):
        return {"env": self._env, "support": self._support, "etat": self._etat, "message": self._message, "sd": self._sd}

    def _propre(self, texte):
        return str(texte).replace(self._mdp, "***") if self._mdp else str(texte)

    def _echec(self, message):
        """Etat « erreur » + RefusFtp lisible (mot de passe masque)."""
        self._etat, self._message = "erreur", self._propre(message)
        raise RefusFtp(self._message)

    # ---- allumage et extinction -------------------------------------------------------------------------------
    def _ufs(self, adresse):
        try:
            return _lit_ufs(self._commande(adresse, "Ufs", 10))
        except Exception:                    # carte muette, delai : SD inconnue
            return []

    def _envoie_ufsftp(self, adresse, n):
        try:
            self._commande(adresse, "UfsFTP %d" % n, 10)
        except Exception as e:
            raise OSError("la carte ne repond pas a UfsFTP %d (%s)" % (n, e))

    def ouvre(self, carte, support):
        """Allume le FTP de la carte (`support` : "sd" ou "flash"), ouvre la session ftplib."""
        adresse = str(carte.get("adresse", ""))
        if support not in ("sd", "flash"):
            raise RefusFtp("support inconnu : " + repr(support))
        if not ADRESSE.fullmatch(adresse):
            raise RefusFtp("adresse de carte invalide")
        with self._verrou:
            if self._carte and self._carte != adresse:
                self.ferme("changement de carte")
            elif self._ftp:
                self._quitte_ftp()
            self._env, self._support, self._etat, self._message = carte.get("env", ""), support, "allumage", ""
            self._derniere = self._horloge()
            objets = self._ufs(adresse)
            self._sd = (objets[0][0] == 1) if objets else None
            if support == "sd" and self._sd is not True:
                self._refuse("SD absente ou non detectee : la flash n'est pas proposee sous l'etiquette SD")
            utilisateur, mdp = self._identifiants(carte.get("firmware", ""))
            if not mdp:
                self._refuse("identifiants FTP introuvables dans user_config_override.h")
            self._objets, self._mdp = objets, mdp
            # _allume avant l'envoi : si UfsFTP atteint la carte mais que la reponse se perd, ferme() enverra UfsFTP 0
            self._carte, self._allume = adresse, True
            try:
                self._envoie_ufsftp(adresse, 1 if support == "sd" else 2)
                self._connecte(utilisateur)
            except (RefusFtp,) + ERREURS_RESEAU as e:
                msg = self._propre(e if isinstance(e, RefusFtp) else "connexion FTP impossible : %s" % e)
                self.ferme("echec de l'allumage")
                self._echec(msg)
            self._etat, self._message, self._derniere = "actif", "", self._horloge()
            return self.etat()

    def ouvre_ou_reprend(self, carte, support):
        """Deuxieme onglet ou POST simultane : meme carte et meme support deja actifs -> l'etat, sans UfsFTP ni reconnexion (sous verrou)."""
        with self._verrou:
            if self._etat == "actif" and self._carte == str(carte.get("adresse", "")) and self._support == support:
                self._derniere = self._horloge()
                return self.etat()
            return self.ouvre(carte, support)

    def _refuse(self, message):
        """Refus dans ouvre : si le FTP de la carte est allume (changement de support), il est eteint d'abord."""
        if self._allume:
            self.ferme("refus : " + message)
        self._etat, self._message = "eteint", message
        raise RefusFtp(message)

    def _attend_port(self, adresse):
        fin = time.monotonic() + self._delai_allumage
        while True:
            try:
                socket.create_connection((adresse, self._port), timeout=1).close()
                return
            except OSError:
                if time.monotonic() >= fin:
                    raise OSError("le port FTP de la carte ne repond pas")
                time.sleep(0.2)

    def _connecte(self, utilisateur=None):
        """Ouvre la session ftplib (port 21 attendu au plus delai_allumage s). ftplib garde l'hote du controle pour
        les donnees (adresse PASV ignoree) : defaut conserve."""
        self._attend_port(self._carte)
        if utilisateur is None:
            utilisateur = self._utilisateur
        self._utilisateur = utilisateur
        ftp = self._fabrique(encoding="utf-8", timeout=DELAI_FTP)
        try:
            ftp.connect(self._carte, self._port, DELAI_FTP)
            ftp.login(utilisateur, self._mdp)
            ftp.set_pasv(True)
        except ftplib.error_perm as e:
            self._ferme_ftp(ftp)
            raise RefusFtp("la carte refuse la connexion FTP : %s" % self._propre(e))
        except ERREURS_RESEAU:
            self._ferme_ftp(ftp)
            raise
        self._ftp = ftp

    @staticmethod
    def _ferme_ftp(ftp):
        try:
            ftp.quit()
        except Exception:
            try:
                ftp.close()
            except Exception:
                pass

    def _quitte_ftp(self):
        ftp, self._ftp = self._ftp, None
        if ftp:
            self._ferme_ftp(ftp)

    def ferme(self, raison):
        """Ferme la session et envoie `UfsFTP 0` dans tous les cas ou le FTP a ete allume."""
        with self._verrou:
            self._quitte_ftp()
            if self._allume:
                try:
                    self._envoie_ufsftp(self._carte, 0)
                    self._message = "Session fermee (%s)" % raison
                except OSError as e:
                    self._message = "UfsFTP 0 non confirme : %s" % self._propre(e)
                self._allume = False
            self._carte, self._mdp, self.derniere_raison = None, "", raison
            if self._etat != "erreur":
                self._etat = "eteint"
            return self.etat()

    def tic(self):
        """Eteint le FTP apres `inactivite` secondes sans action (appele periodiquement par le serveur)."""
        with self._verrou:
            if self._carte and self._horloge() - self._derniere > self._inactivite:
                self.ferme("inactivite")

    # ---- operations -------------------------------------------------------------------------------------------
    def _op(self, f):
        """Execute f(ftp) sous verrou. NOOP de controle, session rouverte une fois si elle est tombee."""
        with self._verrou:
            if not self._carte:
                raise RefusFtp("aucune session ouverte : choisissez une carte")
            try:
                try:
                    if not self._ftp:
                        raise EOFError
                    self._ftp.voidcmd("NOOP")
                except ERREURS_RESEAU:
                    self._quitte_ftp()
                    self._connecte()
                resultat = f(self._ftp)
            except RefusFtp:
                raise
            except ftplib.error_perm as e:
                raise RefusFtp("la carte refuse : %s" % self._propre(e))
            except ERREURS_RESEAU as e:
                self._quitte_ftp()
                self._echec("carte injoignable : %s" % e)
            self._etat, self._message, self._derniere = "actif", "", self._horloge()
            return resultat

    def _entrees(self, ftp, chemin):
        """[{"nom", "type", "taille", "date"}] d'un dossier : MLSD, repli LIST si la carte ne le connait pas."""
        res = []
        try:
            for nom, f in ftp.mlsd(chemin):
                if f.get("type") in ("cdir", "pdir") or nom in (".", ".."):
                    continue
                if not _nom_sain(nom):
                    self.noms_ignores.append(nom)
                    continue
                res.append({"nom": nom, "type": "dossier" if f.get("type") == "dir" else "fichier",
                            "taille": int(f.get("size", 0) or 0), "date": _date_mlsd(f.get("modify"))})
            return res
        except ftplib.error_perm as e:
            if not str(e).startswith(("500", "501", "502", "504")):
                raise
        lignes = []
        ftp.retrlines("LIST " + chemin, lignes.append)
        for ligne in lignes:
            p = ligne.split(None, 8)
            if len(p) == 9 and p[8] not in (".", "..") and not _nom_sain(p[8]):
                self.noms_ignores.append(p[8])
            elif len(p) == 9 and p[8] not in (".", ".."):
                res.append({"nom": p[8], "type": "dossier" if p[0].startswith("d") else "fichier",
                            "taille": int(p[4]) if p[4].isdigit() else 0, "date": " ".join(p[5:8])})
        return res

    def liste(self, chemin):
        chemin = valide_chemin(chemin)
        return self._op(lambda ftp: self._entrees(ftp, chemin))

    def _type(self, ftp, chemin):
        """"dossier", "fichier" ou None (absent), d'apres la liste du dossier parent."""
        if chemin == "/":
            return "dossier"
        parent, _, nom = chemin.rpartition("/")
        for e in self._entrees(ftp, parent or "/"):
            if e["nom"] == nom:
                return e["type"]
        return None

    def lit(self, chemin, sortie):
        chemin = valide_chemin(chemin)
        self._op(lambda ftp: ftp.retrbinary("RETR " + chemin, sortie.write))

    def zip(self, chemins, sortie):
        """Zip des fichiers et dossiers (recursif), noms relatifs a la racine de la carte."""
        chemins = [valide_chemin(c) for c in chemins]

        def ajoute(ftp, z, chemin):
            if self._type(ftp, chemin) == "dossier":
                for e in self._entrees(ftp, chemin):
                    ajoute(ftp, z, chemin.rstrip("/") + "/" + e["nom"])
            else:
                with z.open(chemin.lstrip("/"), "w", force_zip64=True) as f:
                    ftp.retrbinary("RETR " + chemin, f.write)

        def tout(ftp):
            with zipfile.ZipFile(sortie, "w", zipfile.ZIP_DEFLATED) as z:
                for c in chemins:
                    ajoute(ftp, z, c)

        self._op(tout)

    def _libre(self):
        """Place libre en octets du support actif d'apres `Ufs`, None si inconnue."""
        objets = _lit_ufs(self._commande_ufs())
        if not objets:
            return None
        if self._support == "sd":
            return objets[0][2] * 1024 if objets[0][0] == 1 else None
        if len(objets) == 1 and objets[0][0] == 1:
            return None
        return objets[-1][2] * 1024

    def _commande_ufs(self):
        try:
            return self._commande(self._carte, "Ufs", 10)
        except Exception:
            return ""

    def envoie(self, dossier, nom, flux, ecraser):
        dossier = valide_chemin(dossier)
        if not nom or "/" in nom or valide_chemin("/" + nom) != "/" + nom or nom in (".", ".."):
            raise ValueError("nom de fichier invalide")
        cible = dossier.rstrip("/") + "/" + nom
        flux.seek(0, io.SEEK_END)
        taille = flux.tell()
        flux.seek(0)

        def envoi(ftp):
            if not ecraser and any(e["nom"] == nom for e in self._entrees(ftp, dossier)):
                raise RefusFtp("« %s » existe deja dans %s" % (nom, dossier))
            libre = self._libre()
            if libre is not None and taille > libre:
                raise RefusFtp("pas assez de place sur la carte : %d Ko libres pour %d Ko" % (libre // 1024, -(-taille // 1024)))
            ftp.storbinary("STOR " + cible, flux)

        self._op(envoi)

    def _supprime(self, ftp, chemin):
        if self._type(ftp, chemin) == "dossier":
            for e in self._entrees(ftp, chemin):
                self._supprime(ftp, chemin.rstrip("/") + "/" + e["nom"])
            ftp.rmd(chemin)
        else:
            ftp.delete(chemin)

    def supprime(self, chemin, confirmations):
        """Supprime un fichier ou un dossier (recursif). 1 confirmation, 2 pour un fichier protege."""
        chemin = valide_chemin(chemin)
        if chemin == "/":
            raise RefusFtp("la racine ne se supprime pas")
        if confirmations < (2 if protege(chemin) else 1):
            raise RefusFtp("suppression non confirmee" + (" (fichier protege : seconde confirmation)" if protege(chemin) else ""))
        self._op(lambda ftp: self._supprime(ftp, chemin))

    def cree_dossier(self, chemin):
        chemin = valide_chemin(chemin)
        self._op(lambda ftp: ftp.mkd(chemin))

    def deplace(self, source, cible):
        source, cible = valide_chemin(source), valide_chemin(cible)
        self._op(lambda ftp: ftp.rename(source, cible))
