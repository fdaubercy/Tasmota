"""Session FTP d'une carte Tasmota (page « Navigateur FTP des cartes ») : allume le serveur FTP de la carte par HTTP
(`UfsFTP 1|2`), lui parle par ftplib, l'eteint (`UfsFTP 0`) a chaque fin de session.

Une carte active a la fois ; un verrou autour de toute operation FTP (le serveur de la carte n'accepte qu'un client).
La carte deconnecte un client muet depuis 5 min sans eteindre son serveur : chaque operation commence par un NOOP de
controle et, si la session est tombee, la rouvre une fois sans `UfsFTP` supplementaire. Les 15 min (`inactivite`) sans
action sont comptees ici par `tic()` (appele periodiquement par le serveur web), qui eteint alors le FTP.
Support : `UfsFTP 1` = SD si montee, sinon la flash ; `UfsFTP 2` = flash. La SD est donc exigee par `ouvre(.., "sd")`
(`Ufs` : premier objet de type 1), jamais la flash sous l'etiquette SD. Les identifiants viennent du .h
(`ftp_cartes_liste.identifiants`), ne sortent jamais d'ici et sont masques dans les messages.
Onglets : le FTP ne s'eteint au depart d'une page qu'avec le dernier onglet (`Onglets`, ftp_cartes_onglets.py) ; `tic()` eteint aussi quand
tous les onglets vus ont disparu sans le dire.
Spec : docs/superpowers/specs/2026-11-20-navigateur-ftp-cartes-design.md §7 et §9. Bancs : test_ftp_cartes_session.py et
test_ftp_cartes_session_garde.py (garde-fous : deplacement, dossiers proteges, `ouvre` sur exception, onglets).
"""
import ftplib
import io
import socket
import threading
import time
import zipfile
from pathlib import Path

import build_ota_http
import ftp_cartes_liste
from ftp_cartes_chemins import ADRESSE, OBJET_UFS, _date_mlsd, _lit_ufs, _nom_sain, cle_fat, dans_lui_meme, protege, valide_chemin   # noqa: F401 (reexportes : les bancs appellent fs.valide_chemin)
from ftp_cartes_onglets import Onglets, valide as ident_valide

DEPOT = Path(__file__).resolve().parents[3]
DELAI_ALLUMAGE = 10          # s : attente du port 21 apres UfsFTP
DELAI_FTP = 30               # s : une operation FTP
INACTIVITE = 900             # s : sans action, le FTP est eteint
NOMS_IGNORES_MAX = 100       # noms refuses gardes pour la page (les derniers)
PARCOURS_ENTREES = 500       # _contient_protege : entrees visitees au plus, puis fail-safe (True)
ESSAIS_EXTINCTION = 5        # UfsFTP 0 non confirme : essais automatiques au plus (ferme puis tic), puis « Deconnecter » seul
PARCOURS_NIVEAUX = 6         # _contient_protege : dossiers listes au plus sur 6 niveaux (le dossier lui-meme = niveau 1), puis fail-safe
TYPES = (None, "", "fichier", "dossier")      # type attendu par la page pour supprimer et deplacer (None ou "" : pas de controle)
TYPE_CHANGE = "le type de l'element a change (ou il a disparu) : rouvrez le dossier"
ERREURS_RESEAU = (OSError, EOFError, ftplib.error_temp, ftplib.error_proto)


class RefusFtp(Exception):
    """Refus ou echec metier, message lisible (code HTTP 409 cote web)."""


class Session:
    def __init__(self, commande=build_ota_http._commande, fabrique_ftp=ftplib.FTP, horloge=time.monotonic,
                 inactivite=INACTIVITE, identifiants=None, port=21, delai_allumage=DELAI_ALLUMAGE):
        self._commande, self._fabrique, self._horloge = commande, fabrique_ftp, horloge
        self._inactivite, self._port, self._delai_allumage = inactivite, port, delai_allumage
        self._identifiants = identifiants or (lambda fw: ftp_cartes_liste.identifiants(DEPOT, fw))
        self._verrou = threading.RLock()
        self._ftp = None
        self._carte, self._mdp, self._utilisateur, self._objets = None, "", "", []
        self.noms_ignores = []               # noms de la carte refuses par _nom_sain (zip-slip, suppression hors dossier) : les 100 derniers
        self.onglets = Onglets(horloge)      # pages ouvertes sur cette session (meme horloge : bancs a horloge simulee)
        self._allume = False                 # UfsFTP 1|2 envoye, UfsFTP 0 pas encore confirme
        self._extinction, self._essais = None, 0     # adresse dont UfsFTP 0 n'est pas confirme, essais faits (ferme, tic)
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
            try:
                return self._ouvre(carte, adresse, support)
            except RefusFtp:
                raise                        # refus propre : _refuse et _echec ont deja ferme
            except Exception as e:
                # exception inattendue (identifiants(), fabrique FTP...) apres un allumage : le FTP de la carte ne reste pas
                # allume jusqu'au tic(), et l'etat ne reste pas « allumage ». Seul le TYPE de l'exception remonte : son message
                # (identifiants(), fabrique FTP) pourrait citer le mot de passe, et le web rend str(ValueError) en 400.
                self._etat = "erreur"        # ferme() le garde
                try:
                    self.ferme("erreur a l'ouverture")
                except Exception:
                    pass
                self._message = "ouverture impossible : erreur inattendue (%s)" % type(e).__name__
                raise RuntimeError("ouverture impossible : %s" % type(e).__name__) from None

    def _ouvre(self, carte, adresse, support):
        ancienne = self._carte or self._extinction
        if ancienne and ancienne != adresse:
            self.ferme("changement de carte", garde_onglets=True)   # les autres onglets restent connus (C4)
            if self._extinction:                     # jamais deux cartes allumees : l'ancienne d'abord
                raise RefusFtp("la carte precedente n'a pas confirme l'extinction de son FTP : reessayez, ou « Deconnecter »")
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
        self._carte, self._allume, self._extinction, self._essais = adresse, True, None, 0   # meme carte rouverte : l'attente d'extinction est effacee
        try:
            self._envoie_ufsftp(adresse, 1 if support == "sd" else 2)
            self._connecte(utilisateur)
        except (RefusFtp,) + ERREURS_RESEAU as e:
            msg = self._propre(e if isinstance(e, RefusFtp) else "connexion FTP impossible : %s" % e)
            self.ferme("echec de l'allumage")
            self._echec(msg)
        self._etat, self._message, self._derniere = "actif", "", self._horloge()
        return self.etat()

    def ouvre_ou_reprend(self, carte, support, onglet=None):
        """Deuxieme onglet ou POST simultane : meme carte et meme support deja actifs -> l'etat, sans UfsFTP ni reconnexion (sous verrou).
        `onglet` : identifiant de la page, enregistre APRES l'ouverture (un changement de carte garde le registre : les autres onglets restent connus)."""
        with self._verrou:
            if self._etat == "actif" and self._carte == str(carte.get("adresse", "")) and self._support == support:
                self._derniere = self._horloge()
                etat = self.etat()
            else:
                etat = self.ouvre(carte, support)
            self.onglets.vu(onglet)
            return etat

    def _refuse(self, message):
        """Refus dans ouvre : si le FTP de la carte est allume (changement de support), il est eteint d'abord."""
        if self._allume:
            self.ferme("refus : " + message)
        if not self._extinction:                     # extinction non confirmee : l'etat « erreur » et son message restent
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
        except Exception:
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

    def ferme(self, raison, garde_onglets=False):
        """Ferme la session et envoie `UfsFTP 0` dans tous les cas ou le FTP a ete allume. Plus aucun geste ensuite (`_carte` vide).
        `UfsFTP 0` non confirme : l'adresse reste dans `_extinction` et `_allume` reste vrai (en_session() aussi, l'annuaire refuse l'arret) ;
        tic() le renvoie (ESSAIS_EXTINCTION essais au plus), « Deconnecter » aussi. `garde_onglets` : changement de carte (le registre reste)."""
        with self._verrou:
            if not garde_onglets:
                self.onglets.reinitialise()
            self._quitte_ftp()
            adresse, self._carte, self.derniere_raison = self._carte or self._extinction, None, raison
            attente = self._extinction
            if self._allume:
                try:
                    self._envoie_ufsftp(adresse, 0)
                except OSError as e:
                    self._extinction, self._essais = adresse, self._essais + 1
                    self._etat = "erreur"
                    self._message = ("Extinction du FTP de la carte non confirmee apres %d essais : son FTP est peut-etre encore allume ; "
                                     "« Deconnecter » pour reessayer" % self._essais if self._essais >= ESSAIS_EXTINCTION else
                                     "Extinction du FTP de la carte non confirmee (essai %d sur %d, nouvel essai automatique) : %s"
                                     % (self._essais, ESSAIS_EXTINCTION, self._propre(e)))
                    return self.etat()
                self._message = "Session fermee (%s)" % raison
                self._allume = False
            self._mdp, self._extinction, self._essais = "", None, 0
            if self._etat != "erreur" or attente:
                self._etat = "eteint"
            return self.etat()

    def ferme_onglet(self, ident):
        """Une page se ferme (sendBeacon) : le FTP ne s'eteint que si elle etait la derniere. Sans identifiant valide : ferme comme avant."""
        with self._verrou:
            if ident_valide(ident) and not self.onglets.ferme(ident):
                return self.etat()
            return self.ferme("page fermee")

    def en_session(self):
        """True tant que le FTP d'une carte est allume ou en cours d'allumage (sans verrou : /execution doit repondre pendant un envoi)."""
        return self._allume or self._etat == "allumage"

    def tic(self):
        """Eteint le FTP apres `inactivite` secondes sans action, ou quand tous les onglets vus ont disparu (appele periodiquement par le serveur)."""
        with self._verrou:
            if self._extinction:                     # UfsFTP 0 non confirme : renvoye a chaque tic, jusqu'a la borne
                if self._essais < ESSAIS_EXTINCTION:
                    self.ferme(self.derniere_raison)
                return
            if not self._carte:
                return
            if self._horloge() - self._derniere > self._inactivite:
                self.ferme("inactivite")
            elif self.onglets.perdu():
                self.ferme("onglet perdu")

    # ---- operations -------------------------------------------------------------------------------------------
    def _op(self, f, attendu=None):
        """Execute f(ftp) sous verrou. NOOP de controle, session rouverte une fois si elle est tombee.
        `attendu` = (env, support) que la page croit voir (None ou "" = indifferent) : controle fait SOUS le verrou, donc apres un
        changement de carte en cours (ouvre tient le verrou), et avant toute commande FTP."""
        with self._verrou:
            if attendu and any(a not in (None, "") and a != v for a, v in zip(attendu, (self._env, self._support))):
                raise RefusFtp("la session a change (carte ou support)")
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
            except Exception as e:                   # ni ValueError ni TypeError bruts : le web rendrait leur message (secret possible) en 400
                self._quitte_ftp()
                raise RuntimeError("operation impossible : %s" % type(e).__name__) from None
            self._etat, self._message, self._derniere = "actif", "", self._horloge()
            return resultat

    def _ignore(self, nom):
        """Consigne un nom refuse : pas deux fois de suite le meme, les NOMS_IGNORES_MAX derniers seulement."""
        if not self.noms_ignores or self.noms_ignores[-1] != nom:
            self.noms_ignores.append(nom)
        del self.noms_ignores[:-NOMS_IGNORES_MAX]

    def _entrees(self, ftp, chemin):
        """[{"nom", "type", "taille", "date"}] d'un dossier : MLSD, repli LIST si la carte ne le connait pas."""
        res = []
        try:
            for nom, f in ftp.mlsd(chemin):
                if f.get("type") in ("cdir", "pdir") or nom in (".", ".."):
                    continue
                if not _nom_sain(nom):
                    self._ignore(nom)
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
                self._ignore(p[8])
            elif len(p) == 9 and p[8] not in (".", ".."):
                res.append({"nom": p[8], "type": "dossier" if p[0].startswith("d") else "fichier",
                            "taille": int(p[4]) if p[4].isdigit() else 0, "date": " ".join(p[5:8])})
        return res

    def liste(self, chemin):
        chemin = valide_chemin(chemin)
        return self._op(lambda ftp: self._entrees(ftp, chemin))

    def _type(self, ftp, chemin):
        """"dossier", "fichier" ou None (absent), d'apres la liste du dossier parent. Le nom exact d'abord (la flash, LittleFS, distingue
        la casse), sinon le meme nom pour FatFs (cle_fat : la SD ne distingue ni la casse ni les points et espaces finaux)."""
        if chemin == "/":
            return "dossier"
        parent, _, nom = chemin.rpartition("/")
        entrees = self._entrees(ftp, parent or "/")
        exact = [e["type"] for e in entrees if e["nom"] == nom]
        return (exact or [e["type"] for e in entrees if cle_fat(e["nom"]) == cle_fat(nom)] or [None])[0]

    @staticmethod
    def _type_valide(type_attendu):
        if type_attendu not in TYPES:
            raise ValueError("type : « fichier » ou « dossier » attendu")

    def lit(self, chemin, sortie, attendu=None):
        chemin = valide_chemin(chemin)
        self._op(lambda ftp: ftp.retrbinary("RETR " + chemin, sortie.write), attendu)

    def zip(self, chemins, sortie, attendu=None):
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

        self._op(tout, attendu)

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

    def envoie(self, dossier, nom, flux, ecraser, attendu=None, *, confirmations=1):
        """Envoie un fichier. Nom deja pris (comparaison FAT) : refus sans `ecraser` ; ecraser un fichier protege demande 2 confirmations."""
        dossier = valide_chemin(dossier)
        if not nom or "/" in nom or valide_chemin("/" + nom) != "/" + nom or nom in (".", ".."):
            raise ValueError("nom de fichier invalide")
        cible = dossier.rstrip("/") + "/" + nom
        flux.seek(0, io.SEEK_END)
        taille = flux.tell()
        flux.seek(0)

        def envoi(ftp):
            if not ecraser or protege(cible):
                existe = any(cle_fat(e["nom"]) == cle_fat(nom) for e in self._entrees(ftp, dossier))
                if existe and not ecraser:
                    raise RefusFtp("« %s » existe deja dans %s" % (nom, dossier))
                if existe and confirmations < 2:
                    raise RefusFtp("ecrasement non confirme (fichier protege : seconde confirmation)")
            libre = self._libre()
            if libre is not None and taille > libre:
                raise RefusFtp("pas assez de place sur la carte : %d Ko libres pour %d Ko" % (libre // 1024, -(-taille // 1024)))
            ftp.storbinary("STOR " + cible, flux)

        self._op(envoi, attendu)

    def _supprime(self, ftp, chemin, genre=None):
        if (genre or self._type(ftp, chemin)) == "dossier":
            for e in self._entrees(ftp, chemin):
                self._supprime(ftp, chemin.rstrip("/") + "/" + e["nom"])
            ftp.rmd(chemin)
        else:
            ftp.delete(chemin)

    def _contient_protege(self, ftp, chemin):
        """True si le dossier `chemin` contient (a n'importe quelle profondeur) un nom protege. Parcours en largeur borne (PARCOURS_ENTREES
        entrees, PARCOURS_NIVEAUX niveaux) : la limite atteinte rend True, car dans le doute on demande deux confirmations."""
        file, vues = [(chemin, 1)], 0
        while file:
            dossier, niveau = file.pop(0)
            if niveau > PARCOURS_NIVEAUX:
                return True
            for e in self._entrees(ftp, dossier):
                vues += 1
                sous = dossier.rstrip("/") + "/" + e["nom"]
                if vues > PARCOURS_ENTREES or protege(sous):
                    return True
                if e["type"] == "dossier":
                    file.append((sous, niveau + 1))
        return False

    def supprime(self, chemin, confirmations, attendu=None, *, type_attendu=None):
        """Supprime un fichier ou un dossier (recursif). 1 confirmation, 2 pour un fichier protege ou un dossier qui en contient un.
        `type_attendu` : ce que la page a vu ("fichier" ou "dossier") ; s'il a change, refus avant toute commande de modification."""
        chemin = valide_chemin(chemin)
        self._type_valide(type_attendu)
        if chemin == "/":
            raise RefusFtp("la racine ne se supprime pas")
        if confirmations < (2 if protege(chemin) else 1):
            raise RefusFtp("suppression non confirmee" + (" (fichier protege : seconde confirmation)" if protege(chemin) else ""))

        def supprime(ftp):
            # RefusFtp leve ici traverse _op sans fermer la session ; aucune commande de modification n'est partie
            genre = self._type(ftp, chemin)
            if type_attendu and genre != type_attendu:
                raise RefusFtp(TYPE_CHANGE)
            if confirmations < 2 and genre == "dossier" and self._contient_protege(ftp, chemin):
                raise RefusFtp("suppression non confirmee (dossier contenant un fichier protege : seconde confirmation)")
            self._supprime(ftp, chemin, genre)

        self._op(supprime, attendu)

    def cree_dossier(self, chemin, attendu=None):
        chemin = valide_chemin(chemin)
        self._op(lambda ftp: ftp.mkd(chemin), attendu)

    def deplace(self, source, cible, attendu=None, *, confirmations=1, type_attendu=None):
        """Deplace ou renomme. Aucune confirmation pour un deplacement ordinaire ; 2 si la source ou la cible est protegee, ou si la source est
        un dossier qui contient un fichier protege. Jamais d'ecrasement : une cible existante (comparaison FAT) est refusee. Ni la source dans
        elle-meme (un renommage qui ne change que la casse aussi), ni un type de source different de `type_attendu`."""
        source, cible = valide_chemin(source), valide_chemin(cible)
        self._type_valide(type_attendu)
        if dans_lui_meme(source, cible):
            raise RefusFtp("« %s » ne se deplace pas dans lui-meme" % source)
        refus = "deplacement non confirme (fichier protege : seconde confirmation)"
        if confirmations < 2 and (protege(source) or protege(cible)):
            raise RefusFtp(refus)

        def deplace(ftp):
            genre = self._type(ftp, source)
            if type_attendu and genre != type_attendu:
                raise RefusFtp(TYPE_CHANGE)
            if self._type(ftp, cible):
                raise RefusFtp("la cible existe deja")
            if confirmations < 2 and genre == "dossier" and self._contient_protege(ftp, source):
                raise RefusFtp(refus)
            ftp.rename(source, cible)

        self._op(deplace, attendu)
