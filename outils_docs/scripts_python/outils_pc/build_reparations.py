"""Catalogue des reparations de la page Build (plan build-reparations A1) : regles, correspondance, filtre des secrets.

Une regle = un motif cherche dans la FIN du journal d'un `pio run` rate + des actions d'une liste FERMEE (jamais une
commande libre). Verrou de fichier : build_reparations_verrou (A2).

    charge_catalogue(chemin_base, chemin_local) -> list[Regle]   (ValueError si une regle est invalide)
    cherche(regles, journal, etape, env)         -> Regle | None
    filtre_secrets(texte)                        -> texte sans valeur de mot de passe ni de jeton
    Reparateur(serie, regles, horloge)           -> execute / traite / repond_choix / ajoute_regle_locale (A3, branche
                                                    dans build_serie.Serie._execute_env ; evenements reparation, choix_reparation)

Catalogue de base : outils_docs/schemas/reparations_build.json (suivi par git, jamais ecrit par la page). Catalogue local
(%LOCALAPPDATA%\\outils_tasmota\\build\\reparations.json) : regles ajoutees et cle "supprimees" (ids retires), il l'emporte.
"""

import json
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

import build_reparations_verrou as verrou

BASE = Path(__file__).resolve().parents[2] / "schemas" / "reparations_build.json"
LIGNES_FIN = 50                      # la correspondance ne regarde que la fin du journal (borne le cout d'un motif lent)
# action -> parametres requis (nom -> type) ; toute autre action est refusee
ACTIONS = {"attendre": {"secondes": (int, float)}, "libere_verrou": {}, "vide_build": {}}
ETAPES_TOUTES = "toutes"
# jamais upload / erase_upload : un envoi n'est pas relance (spec, « Ce qu'une reparation relance »)
ETAPES_VALIDES = {"compilation", "liens", "prebuild", "buildfs", ETAPES_TOUTES}
SECONDES_MAX = 3600


@dataclass
class Regle:
    id: str
    titre: str
    motif: str
    etapes: list
    actions: list
    origine: str = "base"
    ajoutee_le: str = ""
    _re: object = field(default=None, repr=False, compare=False)


def _valide(d):
    """Construit une Regle depuis un dict du fichier ou leve ValueError."""
    if not isinstance(d, dict):
        raise ValueError("regle : objet attendu")
    for cle in ("id", "titre", "motif"):
        if not isinstance(d.get(cle), str) or not d[cle]:
            raise ValueError(f"regle : « {cle} » manquant")
    id_ = d["id"]
    etapes = d.get("etapes")
    if not isinstance(etapes, list) or not etapes or not all(e in ETAPES_VALIDES for e in etapes):
        raise ValueError(f"regle {id_} : « etapes » doit etre une liste non vide parmi {sorted(ETAPES_VALIDES)}")
    actions = d.get("actions")
    if not isinstance(actions, list) or not actions:
        raise ValueError(f"regle {id_} : « actions » doit etre une liste non vide")
    for a in actions:
        nom = a.get("action") if isinstance(a, dict) else None
        if nom not in ACTIONS:
            raise ValueError(f"regle {id_} : action « {nom} » hors de la liste")
        params = a.get("parametres", {})
        if not isinstance(params, dict):
            raise ValueError(f"regle {id_} : « parametres » doit etre un objet")
        for p, types in ACTIONS[nom].items():
            v = params.get(p)
            if isinstance(v, bool) or not isinstance(v, types) or not 0 <= v <= SECONDES_MAX:
                raise ValueError(f"regle {id_} : action {nom}, parametre « {p} » manquant ou invalide")
    try:
        motif = re.compile(d["motif"], re.MULTILINE)
    except re.error as e:
        raise ValueError(f"regle {id_} : motif invalide ({e})") from e
    return Regle(id_, d["titre"], d["motif"], etapes, actions, str(d.get("origine", "base")), str(d.get("ajoutee_le", "")), motif)


def _lit(chemin, obligatoire):
    chemin = Path(chemin)
    if not chemin.is_file():
        if obligatoire:
            raise ValueError(f"catalogue introuvable : {chemin}")
        return {}
    try:
        data = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"catalogue illisible : {chemin} ({e})") from e
    if not isinstance(data, dict) or not isinstance(data.get("regles", []), list):
        raise ValueError(f"catalogue mal forme : {chemin}")
    return data


def charge_catalogue_avec_avertissements(chemin_base, chemin_local):
    """(regles, avertissements). Base invalide = ValueError (bug du depot) ; local fautif = ignore et signale."""
    base = _lit(chemin_base, True)
    regles, avertissements = {}, []
    for d in base.get("regles", []):
        r = _valide(d)
        regles[r.id] = r
    try:
        local = _lit(chemin_local, False)
    except ValueError as e:
        return list(regles.values()), [str(e)]
    for d in local.get("regles", []):
        try:
            r = _valide(d)
        except ValueError as e:
            avertissements.append(f"regle locale ignoree : {e}")
            continue
        regles[r.id] = r
    sup = local.get("supprimees", [])
    if not isinstance(sup, list) or not all(isinstance(i, str) for i in sup):
        avertissements.append("« supprimees » du catalogue local ignore : liste de textes attendue")
        sup = []
    for id_ in sup:
        regles.pop(id_, None)
    return list(regles.values()), avertissements


def charge_catalogue(chemin_base, chemin_local):
    """Regles de base puis locales (une regle locale de meme id remplace celle de base), moins les « supprimees »."""
    return charge_catalogue_avec_avertissements(chemin_base, chemin_local)[0]


def cherche(regles, journal, etape, env):
    """Premiere regle dont `etapes` contient `etape` (ou « toutes ») et dont le motif correspond a la fin du journal."""
    lignes = (journal or "").splitlines()
    fin = "\n".join(lignes[-LIGNES_FIN:])
    if not fin.strip():
        return None
    for r in regles:
        if (etape in r.etapes or ETAPES_TOUTES in r.etapes) and r._re.search(fin):
            return r
    return None


# Un secret = une CLE (STA_PASS1, MQTT_PASS, PASSWORD, WIFI_PW, token...) suivie de = ou : (ou d'un espace puis un guillemet,
# comme `#define STA_PASS1 "x"`), puis sa valeur ; ou le mot apres « Bearer ». Un mot libre (« pass through ») ne compte pas.
# Longueurs bornees : pas de retour arriere quadratique sur une ligne geante.
_SECRET = re.compile(r"""(\b\w{0,60}(?:PASS(?:WORD|WD)?|PWD|TOKEN|SECRET|(?<![A-Za-z0-9])PW|_PW)[0-9_]{0,10}["']?"""
                     r"""(?:\s{0,5}[:=]\s{0,5}|\s{1,5}(?=["'])))"""
                     r"""(\\"[^\n]{0,200}?\\"|"[^"\n]{0,200}"|'[^'\n]{0,200}'|[^\s,;]{1,200})""", re.IGNORECASE)
_BEARER = re.compile(r"(\bBearer\s+)[^\s,;]{1,200}", re.IGNORECASE)


def filtre_secrets(texte):
    """Masque la valeur qui suit un nom de mot de passe ou de jeton ; le nom reste lisible."""
    return _SECRET.sub(lambda m: m.group(1) + "***", _BEARER.sub(r"\1***", texte))


# -- execution des regles dans la serie (A3) -------------------------------------------------------------------------------

RELANCES_MAX = 2                      # par etape (env, action, cible) et par serie
CHOIX_DELAI_S = 600                   # sans reponse en 10 min : pas de reparation, l'env echoue, la serie continue
BOUTONS = ("fermer", "attendre", "annuler")
# libelle d'etape de build_progression -> nom d'etape du catalogue ; toute autre etape (envoi...) n'est jamais reparee
ETAPES_SUIVI = {"Pré-build": "prebuild", "Compilation": "compilation", "Édition des liens": "liens",
                "Construction du FS": "buildfs"}
_CHEMIN = re.compile(r"Permission denied: '([^']+)'")
_NOM_ENV = re.compile(r"[A-Za-z0-9_.-]+")


def charge_defaut(chemin_local):
    """Catalogue de base du depot + local ; une erreur ne doit jamais casser la serie (alors : aucune regle)."""
    try:
        return charge_catalogue(BASE, chemin_local)
    except ValueError:
        return []


def pour_serie(serie):
    """Reparateur d'une serie (un par lancement : compteurs remis a zero) ; catalogue local a cote des donnees de la page."""
    local = Path(serie.dossier) / "reparations.json"
    return Reparateur(serie, charge_defaut(local), chemin_local=local)


class Reparateur:
    """Applique une regle quand un fils pio de la serie echoue, puis dit s'il faut relancer la meme etape.

    `serie` : la build_serie.Serie (verrou, _ajoute, depuis, _arret, _attend_builds, racine, dossier). Garde-fous, tous ici :
    jamais un envoi (cible upload, erase_upload, uploadfs), 2 relances au plus par etape, une regle ne s'applique pas deux
    fois a la meme panne (signature = id + ligne reconnue), un arret demande prime (alors `interrompue`)."""

    def __init__(self, serie, regles, horloge=time.monotonic, libere=None, libre=None, chemin_local=None):
        self.serie, self.regles, self.horloge = serie, list(regles), horloge
        self.libere = libere or verrou.libere
        self.libre = libre or verrou.est_libre
        self.chemin_local = Path(chemin_local) if chemin_local else Path(serie.dossier) / "reparations.json"
        self.interrompue = False          # un arret a coupe une reparation : l'env est « arrete »
        self.historique = []              # [{env, action, regle, titre, etat, message}] de la serie
        self._relances, self._signatures = {}, {}
        self._courante = None             # entree d'historique en_cours (relance pas encore jugee)
        self._choix = None                # demande ouverte : {env, choix}
        self._abandon = ""
        self._attendre_libre = False

    # -- boucle de relance (appelee par Serie._execute_env) --
    def execute(self, ligne, action, cible, lance_pio):
        """lance_pio(ligne, action, cible) ; relance tant que `traite` le demande ; rend le dernier resultat."""
        while True:
            n = self.serie.numero
            rendu = lance_pio(ligne, action, cible)
            if rendu[0] is not False:
                self._clos(bool(rendu[0]), "relance réussie" if rendu[0] else "arrêt demandé")
                return rendu
            journal = "\n".join(e.get("texte", "") for e in self.serie.depuis(n, 0)
                                if e["type"] == "ligne" and e["env"] == ligne.env)
            if not self.traite(ligne, action, cible, rendu[3], journal, rendu[2]):
                return rendu

    def traite(self, ligne, action, cible, etape, journal, extrait) -> bool:
        """Vrai = la regle a ete appliquee, relancer la meme etape."""
        env = ligne.env
        self._clos(False, "la relance a encore échoué")
        if cible.split()[-1:] not in ([], ["buildfs"]):   # un envoi n'est jamais relance (drvset, carte effacee)
            return False
        nom = ETAPES_SUIVI.get(etape)
        if nom is None or self.serie._arrete_demande():
            return False
        regle = cherche(self.regles, journal, nom, env)
        if regle is None:
            return False
        fin = "\n".join(journal.splitlines()[-LIGNES_FIN:])
        m = regle._re.search(fin)
        reconnue = fin[fin.rfind("\n", 0, m.start()) + 1:].split("\n", 1)[0]
        signature, cle = (regle.id, reconnue), (env, action, cible)
        vus = self._signatures.setdefault(cle, set())
        if self._relances.get(cle, 0) >= RELANCES_MAX or signature in vus:
            return False
        chemin = None
        if any(a["action"] == "libere_verrou" for a in regle.actions):
            trouve = _CHEMIN.search(reconnue) or _CHEMIN.search(fin)
            if not trouve:
                return False                               # pas de fichier a liberer : comportement d'avant
            chemin = trouve.group(1).replace("\\\\", "\\")
        vus.add(signature)
        self._relances[cle] = self._relances.get(cle, 0) + 1
        self._courante = {"env": env, "action": action, "regle": regle.id, "titre": regle.titre, "etat": "", "message": ""}
        self.historique.append(self._courante)
        self._annonce("en_cours", f"{regle.titre} (relance {self._relances[cle]}/{RELANCES_MAX})")
        self._abandon, self._attendre_libre = "", False
        for a in regle.actions:
            if not self._action(a, env, regle, chemin):
                break
        if self._abandon or self.serie._arrete_demande():
            self.interrompue = self.interrompue or self.serie._arrete_demande()
            self._clos(False, self._abandon or "arrêt demandé")
            return False
        return True

    def repond_choix(self, env, choix):
        if choix not in BOUTONS:
            raise ValueError(f"choix invalide : {choix!r} ({', '.join(BOUTONS)})")
        with self.serie.verrou:
            if self._choix is None or self._choix["env"] != env or self._choix["choix"] is not None:
                raise RuntimeError(f"aucune demande de réparation ouverte pour {env}")
            self._choix["choix"] = choix
            self.serie.verrou.notify_all()

    def ajoute_regle_locale(self, regle):
        """Valide puis ecrit `regle` (dict) dans le catalogue local (meme id remplace) ; rend la Regle."""
        r = _valide(regle)
        data = _lit(self.chemin_local, False) or {}
        data["regles"] = [d for d in data.get("regles", []) if not (isinstance(d, dict) and d.get("id") == r.id)] + [regle]
        self.chemin_local.parent.mkdir(parents=True, exist_ok=True)
        provisoire = self.chemin_local.with_suffix(".tmp")
        provisoire.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        os.replace(provisoire, self.chemin_local)
        self.regles = [x for x in self.regles if x.id != r.id] + [r]
        return r

    # -- interne --
    def _attend(self, secondes, condition=lambda: False):
        """Attente reveillee par l'arret (temps reel : l'horloge injectee ne regle que le delai du choix)."""
        limite = time.monotonic() + secondes
        with self.serie.verrou:
            while not self.serie._arret and not condition() and time.monotonic() < limite:
                self.serie.verrou.wait(min(0.1, max(0.0, limite - time.monotonic())))
        return condition()

    def _action(self, a, env, regle, chemin):
        """Execute une action ; faux = la suite de la regle est abandonnee (arret, annulation, expiration)."""
        if self.serie._arrete_demande():
            return False
        nom = a["action"]
        if nom == "attendre":
            self._attend(a["parametres"]["secondes"])
        elif nom == "vide_build":
            base = Path(self.serie.racine) / ".pio" / "build"
            if _NOM_ENV.fullmatch(env) and env not in (".", ".."):       # .pio/build/<env rate>, jamais un autre
                shutil.rmtree(base / env, ignore_errors=True)
                self._ligne(f"dossier de build vidé : {base / env}")
        elif nom == "libere_verrou":
            rendu = self.libere(chemin, verrou.LISTE_BLANCHE, None, self._demande(env, regle, chemin))
            quoi = [f"{cle} : " + ", ".join(f"{p.get('nom')} ({p.get('pid')})" for p in rendu[cle])
                    for cle in ("ferme", "attend", "refuse") if rendu.get(cle)]
            if rendu.get("erreur"):
                quoi.append("Restart Manager : " + rendu["erreur"])
            self._ligne(filtre_secrets(f"verrou de {chemin} : " + ("; ".join(quoi) or "aucun processus")))
            if self._abandon:
                return False
            if rendu.get("attend") and not self.serie._attend_builds(env):   # autre build : sa fin, jamais le fermer
                return False
            if self._attendre_libre and not self._attend(CHOIX_DELAI_S, lambda: self.libre(chemin)):
                self._abandon = self._abandon or ("" if self.serie._arret else "fichier toujours tenu après 10 min")
                return False
        return not self.serie._arrete_demande()

    def _demande(self, env, regle, chemin):
        """Rappel `demande(proc)` de libere : choix Fermer / Attendre / Annuler pose a la page, 10 min au plus."""
        def demande(p):
            if self._abandon:
                return False
            texte = filtre_secrets(f"{p.get('nom')} (pid {p.get('pid')}) tient {chemin}. "
                                   f"Ligne de commande : {(p.get('ligne') or '')[:300]}")
            v = self.serie.verrou
            with v:                                        # demande ouverte et annoncee sous la meme prise du verrou
                self._choix = {"env": env, "choix": None}
                self.serie._ajoute("choix_reparation", env, regle=regle.id, texte=texte, boutons=list(BOUTONS))
                limite = self.horloge() + CHOIX_DELAI_S
                while self._choix["choix"] is None and not self.serie._arret and self.horloge() < limite:
                    v.wait(0.05)
                choix, self._choix = self._choix["choix"], None
            if choix in ("fermer", "attendre"):
                self._annonce("en_cours", filtre_secrets(f"réponse : {choix} ({p.get('nom')})"))
                self._attendre_libre = self._attendre_libre or choix == "attendre"
                return choix == "fermer"
            self._abandon = ("arrêt demandé" if self.serie._arret else "annulé par l'utilisateur" if choix == "annuler"
                             else "sans réponse en 10 min")
            return False
        return demande

    def _annonce(self, etat, message):
        c = self._courante
        c.update(etat=etat, message=message)
        self.serie._ajoute("reparation", c["env"], action=c["action"], regle=c["regle"], etat=etat, message=message)
        self._ligne(f"{c['titre']} : {etat}, {message}")

    def _clos(self, ok, message):
        if self._courante is not None:
            self._annonce("reussie" if ok else "echouee", message)
            self._courante = None

    def _ligne(self, texte):
        """Ligne « [réparation] … » : evenement `ligne` et fin du dernier journal de l'env."""
        c = self._courante or {}
        texte = "[réparation] " + texte
        self.serie._ajoute("ligne", c.get("env"), action=c.get("action"), texte=texte)
        journaux = list((Path(self.serie.dossier) / "journaux").glob(f"*-{c.get('env')}-{c.get('action')}*.log"))
        if journaux:
            try:
                with open(max(journaux, key=lambda p: p.stat().st_mtime_ns), "a", encoding="utf-8") as f:
                    f.write(texte + "\n")
            except OSError:
                pass
