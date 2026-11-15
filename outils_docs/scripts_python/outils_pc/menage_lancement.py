"""Lancement de l'audit de menage par la page : `claude -p --agent auditeur-menage` en LECTURE SEULE, rapport valide.

Modele : atelier_ecrans_remarques.py (meme facon de lancer claude, options verifiees avec claude 2.1.319). Rien n'est ecrit au depot.

    Audit(racine, builds_en_cours).lance(params) -> (ok, message)   demarre un fil ; refuse si un build tourne ou si un audit est en cours
    Audit.etat() -> dict {etat: repos|en_cours|fini|echec, message, rapport, debut, fin}
    Audit.arrete()                                               arrete proprement le processus fils
    parametres(brut) -> (params_propres, erreurs)                 liste blanche : rien de libre ne va dans la ligne de commande

Lecture seule : outils Read, Grep, Glob et Bash limite a des commandes git/ls/wc/du de lecture (--allowed-tools), Write/Edit refuses,
mode dontAsk (tout ce qui n'est pas autorise est refuse), pas de MCP, pas de hooks de l'utilisateur, budget borne.
shortcut: l'agent ne peut pas ecrire sa memoire (auditeur-menage.md) depuis la page, faute d'outil d'ecriture ; les chemins
« a garder » viennent de menage_memoire.py. A revoir si la memoire de l'agent devient utile ici.
"""

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

import acces_web
import menage_rapport
import menage_verification

DELAI = 900
BUDGET_USD = "3"
ZONES = ("data", "outils_docs", "tasks", ".claude", "docs", "lib/libesp32/berry_custom")
MAX_ACTIVITE = 300
MODELES = ("sonnet", "opus", "haiku")
EFFORTS = ("low", "medium", "high")
AGENT = "auditeur-menage"
BASH_LECTURE = ["Bash(git status:*)", "Bash(git log:*)", "Bash(git ls-files:*)", "Bash(git diff:*)", "Bash(git hash-object:*)",
                "Bash(git check-ignore:*)", "Bash(ls:*)", "Bash(wc:*)", "Bash(du:*)"]
OPTIONS = ["-p", "--agent", AGENT, "--tools", "Read,Grep,Glob,Bash", "--permission-mode", "dontAsk", "--strict-mcp-config",
           "--no-session-persistence", "--disable-slash-commands", "--output-format", "stream-json", "--verbose", "--max-budget-usd", BUDGET_USD,
           "--disallowed-tools", "Write", "Edit", "NotebookEdit", "--allowed-tools"] + BASH_LECTURE


def parametres(brut):
    """Liste blanche. Retourne (params, erreurs) ; erreurs non vide = refus."""
    erreurs = []
    brut = brut if isinstance(brut, dict) else {}
    zone = brut.get("zone", list(ZONES))
    if not isinstance(zone, list) or not zone or not all(z in ZONES for z in zone):
        erreurs.append(f"zone : sous-ensemble non vide de {ZONES}")
    categories = brut.get("categories", list(menage_rapport.CATEGORIES))
    if not isinstance(categories, list) or not categories or not all(c in menage_rapport.CATEGORIES for c in categories):
        erreurs.append(f"categories : sous-ensemble non vide de {menage_rapport.CATEGORIES}")
    jours = brut.get("anciennete_jours", 3)
    if isinstance(jours, bool) or not isinstance(jours, int) or not 0 <= jours <= 365:
        erreurs.append("anciennete_jours : entier de 0 a 365")
    modele = brut.get("modele", "sonnet")
    if modele not in MODELES:
        erreurs.append(f"modele : {MODELES}")
    effort = brut.get("effort", "medium")
    if effort not in EFFORTS:
        erreurs.append(f"effort : {EFFORTS}")
    if erreurs:
        return None, erreurs
    return {"zone": sorted(set(zone)), "categories": sorted(set(categories)), "anciennete_jours": jours,
            "modele": modele, "effort": effort}, []


def consigne(params, gardes):
    return (
        f"Audit de menage du depot (lecture seule). Parametres : zone = {', '.join(params['zone'])} ; "
        f"categories = {', '.join(params['categories'])} ; anciennete_jours = {params['anciennete_jours']}.\n"
        "Chemins a GARDER (ne jamais les proposer) : " + (", ".join(gardes) if gardes else "aucun") + ".\n"
        "Rappel : tout fichier modifie ou non suivi par git, ou touche depuis moins de anciennete_jours jours, est « en cours » "
        "(en_cours: true, jamais propose) ; un plan de statut actif n'est jamais propose a l'archivage.\n"
        "Si la categorie hors_dossier est demandee, propose aussi des DEPLACEMENTS pour mieux classer (action deplacer, vers = chemin exact sans texte ni commentaire, explications dans constat), pas "
        "seulement des suppressions.\n"
        "Bash : UNE seule commande simple par appel (git status --porcelain, git ls-files, git log, git diff, git hash-object, "
        "git check-ignore, ls, wc, du), sans cd, sans pipe, sans ; ni &&, sans redirection : le depot est deja le dossier courant, "
        "toute commande composee est refusee. Filtre avec Grep/Glob, pas avec grep/head.\n"
        "Remplis la COUVERTURE du rapport (un element par controle demande : fait, partiel ou non_fait, avec une phrase courte), les limites et les ecartes.\n"
        "Reponds par le rapport JSON demande par ton format de sortie (schema outils_docs/schemas/menage_rapport.schema.json), "
        "sans rien deplacer, supprimer ni ecrire."
    )


MAX_DETAIL = 1200
CLES_API = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")      # jamais transmises a claude : l'audit passe par la connexion claude.ai
# (motif sur le texte d'erreur en minuscules, cause en francais) : la 1re cause trouvee est la raison de l'echec
CAUSES = [
    (("credit balance", "insufficient credit", "billing"),
     "Le crédit du compte facturé à l'API est épuisé : claude refuse de travailler. La page ne transmet pas votre clé ANTHROPIC_API_KEY ; si claude "
     "facture quand même l'API, c'est que sa propre configuration (connexion à un compte API, apiKeyHelper) le demande : reconnectez-vous avec "
     "votre abonnement (/login dans claude) ou rechargez le crédit sur console.anthropic.com."),
    (("invalid api key", "authentication_error", "invalid x-api-key", "please run /login", "not logged in", "oauth token", "401"),
     "Claude a refusé la connexion : la clé API ou la session est invalide ou expirée. Reconnectez-vous (/login dans claude) ou corrigez la variable "
     "d'environnement ANTHROPIC_API_KEY."),
    (("limit reached", "usage limit", "rate limit", "rate_limit", "429", "quota"),
     "Limite d'utilisation de claude atteinte : réessayez plus tard (l'heure de reprise figure dans le détail technique) ou choisissez un modèle moins gourmand."),
    (("overloaded", "529", "503", "service unavailable"),
     "Les serveurs de claude sont surchargés ou indisponibles : réessayez dans quelques minutes."),
]
CONTEXTES = [
    (("anthropic_api_key",), "claude signale une clé API (ANTHROPIC_API_KEY) qui prend le pas sur votre connexion claude.ai. Cette page la retire pourtant "
                             "de l'environnement de claude : elle vient donc d'ailleurs (configuration de claude) ; si elle est invalide ou sans crédit, l'audit échoue."),
    (("not been trusted", "hastrustdialogaccepted"), "Claude Code n'a pas encore approuvé ce dossier : il ignore les autorisations de .claude/settings.json "
                                                     "(l'audit garde les siennes). Pour l'approuver, ouvrez claude une fois dans le dépôt et acceptez la confiance."),
]


def explique_echec(code, erreur, resultat=""):
    """(message en francais avec la raison, detail technique d'origine borne) pour un echec de claude."""
    brut = " ".join(x for x in (str(resultat or "").strip(), str(erreur or "").strip()) if x)
    bas = brut.lower()
    cause = next((c for motifs, c in CAUSES if any(m in bas for m in motifs)), None)
    contexte = [c for motifs, c in CONTEXTES if any(m in bas for m in motifs)]
    if cause is None:
        cause = f"claude s'est arrêté avec une erreur (code {code}) sans dire pourquoi en clair."
        if contexte:
            cause += " Les avertissements ci-dessous sont les seuls indices."
    return " ".join([cause] + contexte), brut[-MAX_DETAIL:]


def _resultat(d):
    """Texte de l'evenement final de claude (dict deja decode)."""
    if not isinstance(d, dict):
        raise ValueError("sortie de claude illisible (evenement final absent)")
    if d.get("is_error"):
        raise ValueError("claude a rendu une erreur : " + str(d.get("result") or d.get("subtype"))[:300])
    return d.get("result") or ""


def _detail(nom, entree):
    """Une ligne lisible pour une action de l'agent, secrets masques."""
    if not isinstance(entree, dict):
        return ""
    cle = {"Bash": "command", "Grep": "pattern", "Glob": "pattern", "Read": "file_path"}.get(nom)
    texte = str(entree.get(cle) if cle else entree)
    if nom == "Grep" and entree.get("path"):
        texte += "  dans " + str(entree["path"])
    return menage_rapport.masque(texte)[:160]


def progression_estimee(appels):
    """Approximation : on ne connait pas le nombre d'actions d'avance ; monte vite puis ralentit, jamais 100 avant la fin."""
    return min(95, round(100 * appels / (appels + 30)))


def reglages_sans_hooks():
    d = acces_web.dossier_donnees() / "menage"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "reglages_claude.json"
    f.write_text('{"disableAllHooks": true}\n', encoding="utf-8")
    return f


def _arrete_processus(p):
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
    else:
        p.kill()


class Audit:
    def __init__(self, racine, builds_en_cours, programme=None, delai=DELAI, gardes=lambda: []):
        self.racine, self.builds_en_cours, self.programme, self.delai, self.gardes = Path(racine), builds_en_cours, programme, delai, gardes
        self._verrou = threading.Lock()
        self._etat = {"etat": "repos", "message": "", "rapport": None, "debut": None, "fin": None, "activite": [], "appels": 0, "progression": 0, "detail": ""}
        self._proc = None
        self._arret = False

    def etat(self):
        with self._verrou:
            return dict(self._etat, activite=list(self._etat["activite"]))

    def _pose(self, **kw):
        with self._verrou:
            self._etat.update(kw)

    def lance(self, brut):
        params, erreurs = parametres(brut)
        if erreurs:
            return False, "parametres refuses : " + " ; ".join(erreurs)
        enc = self.builds_en_cours()
        if enc:
            return False, "un build est en cours (" + ", ".join(str(e) for e in list(enc)[:3]) + ") : audit refuse"
        with self._verrou:
            if self._etat["etat"] == "en_cours":
                return False, "un audit est deja en cours"
            self._etat = {"etat": "en_cours", "message": "audit en cours", "rapport": None, "debut": time.time(), "fin": None,
                           "activite": [], "appels": 0, "progression": 0, "detail": ""}
            self._arret = False
        threading.Thread(target=self._fil, args=(params,), daemon=True).start()
        return True, "audit lance"

    def arrete(self):
        self._arret = True
        p = self._proc
        if p is not None and p.poll() is None:
            _arrete_processus(p)

    def _fil(self, params):
        try:
            etat, message, rapport = self._traite(params)
        except Exception as e:      # le fil ne doit jamais mourir sans dire pourquoi
            etat, message, rapport = "echec", f"erreur inattendue : {type(e).__name__} : {e}"[:300], None
        self._pose(etat=etat, message=message, rapport=rapport, fin=time.time())
        if etat == "fini":
            self._pose(progression=100)

    def _lit_flux(self, p, finale):
        """Lit le flux stream-json de claude : chaque appel d'outil devient une ligne d'activite, l'evenement final est garde."""
        for brut in p.stdout:
            try:
                d = json.loads(brut.decode("utf-8", "replace"))
            except ValueError:
                continue
            if not isinstance(d, dict):
                continue
            if d.get("type") == "assistant":
                contenu = (d.get("message") or {}).get("content")
                for c in contenu if isinstance(contenu, list) else []:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        with self._verrou:
                            debut = self._etat["debut"] or time.time()
                            self._etat["appels"] += 1
                            self._etat["progression"] = progression_estimee(self._etat["appels"])
                            self._etat["activite"] = (self._etat["activite"] + [{"t": round(time.time() - debut, 1), "outil": str(c.get("name"))[:30],
                                                      "detail": _detail(c.get("name"), c.get("input"))}])[-MAX_ACTIVITE:]
            elif "result" in d and d.get("type") in (None, "result"):
                finale.append(d)

    def _traite(self, params):
        programme = self.programme or ([shutil.which("claude")] if shutil.which("claude") else None)
        if not programme:
            return "echec", "claude introuvable dans le PATH", None
        options = OPTIONS + ["--model", params["modele"], "--effort", params["effort"], "--settings", str(reglages_sans_hooks())]
        try:
            # Pas de cle API heritee : elle passerait avant l'abonnement claude.ai et l'audit serait facture sur son credit.
            env = {k: v for k, v in os.environ.items() if k not in CLES_API}
            p = subprocess.Popen(list(programme) + options, cwd=self.racine, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as e:
            return "echec", f"lancement de claude impossible : {e}", None
        self._proc = p
        finale, erreur = [], []
        lecteurs = [threading.Thread(target=self._lit_flux, args=(p, finale), daemon=True),
                    threading.Thread(target=lambda: erreur.append(p.stderr.read()), daemon=True)]
        for t in lecteurs:
            t.start()
        try:
            p.stdin.write(consigne(params, self.gardes()).encode("utf-8"))
            p.stdin.close()
        except OSError:
            pass                                  # claude mort avant d'avoir lu : le code de sortie le dira
        try:
            p.wait(timeout=self.delai)
        except subprocess.TimeoutExpired:
            _arrete_processus(p)
            return "echec", f"delai de {self.delai} s depasse : audit abandonne", None
        finally:
            self._proc = None
            for t in lecteurs:
                t.join(10)
        if self._arret:
            return "echec", "audit arrete par l'utilisateur", None
        sortie_erreur = (erreur[0] if erreur else b"").decode("utf-8", "replace")
        resultat = str((finale[-1] if finale else {}).get("result") or "") if finale and (p.returncode != 0 or finale[-1].get("is_error")) else ""
        if p.returncode != 0 or (finale and finale[-1].get("is_error")):
            message, detail = explique_echec(p.returncode, sortie_erreur, resultat)
            self._pose(detail=detail)
            return "echec", message, None
        try:
            texte = _resultat(finale[-1] if finale else None)
        except ValueError as e:
            return "echec", str(e), None
        rapport, erreurs = menage_rapport.valide(texte, self.racine)
        if rapport is None:
            return "echec", "rapport refuse : " + " ; ".join(erreurs[:5]), None
        self._pose(message="contre-verification des propositions par git...")
        try:
            rapport["propositions"] = menage_verification.enrichit(rapport["propositions"], self.racine)
        except Exception as e:                 # la contre-verification est un plus : un echec ne doit pas perdre l'audit
            for p in rapport["propositions"]:
                p["verif"] = {"disponible": False, "erreur": f"erreur interne : {type(e).__name__}"}
        n = len(rapport["propositions"])
        return "fini", f"{n} proposition(s)", rapport
