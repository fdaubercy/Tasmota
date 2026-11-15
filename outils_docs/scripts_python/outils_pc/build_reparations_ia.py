"""Diagnostic par l'IA des pannes de la page Build (plan build-reparations A6, spec « Correction par l'IA »).

    diagnostique(racine, env, etape, journal, programme=None) -> dict   `claude -p` en LECTURE SEULE (mecanisme et options de
        atelier_ecrans_remarques.py : outils de lecture, hooks coupes, jamais bypassPermissions) ; ce PC seulement (garde des routes)
    valide_proposition(proposition, journal, etape)            -> dict   {cause, explication, correctif_manuel, regle, refus}
    applique_et_relance(serie, env, regle, journal)            -> dict   actions de la regle, relance de l'env, regle gardee
                                                                         (origine "ia") SEULEMENT si la relance reussit

Garde-fous : fin du journal passee par filtre_secrets avant l'envoi ; sortie non JSON = aucune proposition ; motif qui ne
correspond pas a la fin du journal fourni, trop court ou qui correspond au texte vide = regle refusee ; action hors de la liste
fermee de build_reparations.ACTIONS = regle refusee ; aucune commande libre ; rien n'est ecrit dans data/.
Le fils claude ne recoit JAMAIS ANTHROPIC_API_KEY ni ANTHROPIC_AUTH_TOKEN : il travaille sur l'abonnement claude.ai deja connecte
(meme garde que menage_lancement.py::CLES_API).
shortcut: les fichiers du depot changes pendant le diagnostic ne sont pas controles (git status), la lecture seule repose sur
les options de claude ; une serie arretee par l'utilisateur (_arret reste vrai) fait echouer « appliquer » jusqu'au lancement suivant.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time

import atelier_ecrans_remarques as rem
import build_reparations as rep

DELAI = 300                                   # 5 min au plus pour un diagnostic
MOTIF_MIN = 8                                 # un motif plus court correspond a trop de pannes
TEXTE_MAX = 1500
CLES_API = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
# shortcut: controle syntaxique d'un groupe quantifie qui contient un quantificateur ou « | » ; refuse aussi (foo|bar)+ legitime,
# a remplacer par un moteur sans retour arriere (re2) si un tel motif devient utile.
IMBRIQUE = re.compile(r"\((?:[^()\\]|\\.)*(?:[+*]|\{\d*,?\d*\}|\|)(?:[^()\\]|\\.)*\)\s*(?:[+*]|\{\d*,?\d*\})")
_DIAGNOSTIC = threading.Lock()
_APPLICATION = threading.Lock()


def fin_journal(journal):
    """Les 50 dernieres lignes : ce que cherche() regarde, donc ce que l'IA voit."""
    return "\n".join((journal or "").splitlines()[-rep.LIGNES_FIN:])


def consigne(env, etape, fin):
    return (
        "Page Build d'un depot Tasmota : une etape d'un `pio run` a echoue. Session lancee par la page, en LECTURE SEULE "
        "(tu ne peux que lire).\n"
        f"Carte (env PlatformIO) : {env}. Etape en echec : {etape}.\n"
        "Fin du journal de pio (les mots de passe sont masques par ***) :\n<<<\n" + fin + "\n>>>\n"
        "Cherche la cause (journal, puis fichiers du depot si utile). Reponds UNIQUEMENT par un objet JSON, sans texte autour :\n"
        '{"cause": "<une phrase>", "explication": "<courte, en francais>", "regle": {"titre": "<court>", "motif": "<expression '
        'reguliere Python qui correspond a une ligne de la fin du journal ci-dessus>", "actions": [{"action": "attendre", '
        '"parametres": {"secondes": 5}}]} ou null, "correctif_manuel": "<texte>" ou null}\n'
        "Actions permises, SEULEMENT celles-ci : attendre {secondes} ; libere_verrou {} (ferme le processus qui tient le fichier "
        "d'un « Permission denied: '<chemin>' ») ; vide_build {} (vide .pio/build/<env>). La page relancera ensuite la meme "
        "commande. Donne une regle seulement si une de ces actions peut corriger la panne ; sinon regle null et un "
        "correctif_manuel. Aucune commande libre. Le motif doit etre precis (jamais « .* » seul).\n")


def _regle(d, journal, etape, titre_defaut=""):
    """Regle complete et valide, ou ValueError qui dit pourquoi pas."""
    if not isinstance(d, dict):
        raise ValueError("objet attendu")
    motif, actions = d.get("motif"), d.get("actions")
    if not isinstance(motif, str) or len(motif) < MOTIF_MIN:
        raise ValueError(f"motif absent ou trop court (moins de {MOTIF_MIN} caracteres)")
    if not isinstance(actions, list) or not actions or not all(isinstance(a, dict) for a in actions):
        raise ValueError("actions : liste non vide attendue")
    propres = []
    for a in actions:                               # seuls les parametres connus de l'action sont gardes
        params = a.get("parametres") if isinstance(a.get("parametres"), dict) else {}
        propres.append({"action": a.get("action"), "parametres": {k: params[k] for k in rep.ACTIONS.get(a.get("action"), {}) if k in params}})
    titre = rep.filtre_secrets(str(d.get("titre") or titre_defaut or "Règle proposée par l'IA"))[:80]
    cle = hashlib.sha1((motif + json.dumps(propres, sort_keys=True)).encode("utf-8")).hexdigest()[:8]
    complete = {"id": "ia_" + cle, "titre": titre, "motif": motif, "etapes": [etape], "actions": propres,
                "origine": "ia", "ajoutee_le": time.strftime("%Y-%m-%d")}
    if IMBRIQUE.search(motif):                      # retour arriere catastrophique : refuse avant tout search()
        raise ValueError("motif refusé : quantificateur imbriqué ou alternance répétée")
    r = rep._valide(complete)                       # action hors liste, parametre manquant, motif qui ne compile pas
    fin = fin_journal(journal)
    if r._re.search(""):
        raise ValueError("motif trop large (correspond au texte vide)")
    if not r._re.search(fin):
        raise ValueError("le motif ne correspond pas au journal fourni")
    if any(a["action"] == "libere_verrou" for a in propres) and not rep._CHEMIN.search(fin):
        raise ValueError("libere_verrou : aucun « Permission denied: '<chemin>' » dans le journal")
    return complete


def valide_regle(d, journal, etape):
    """Pour la route « appliquer » : la regle renvoyee par la page est revalidee, jamais crue."""
    return _regle(d, journal, etape)


def valide_proposition(proposition, journal, etape="compilation"):
    p = proposition if isinstance(proposition, dict) else {}

    def texte(cle):
        return rep.filtre_secrets(str(p.get(cle) or ""))[:TEXTE_MAX]
    sortie = {"cause": texte("cause"), "explication": texte("explication"), "correctif_manuel": texte("correctif_manuel"),
              "regle": None, "refus": ""}
    if p.get("regle") is not None:
        try:
            sortie["regle"] = _regle(p["regle"], journal, etape, sortie["cause"])
        except ValueError as e:
            sortie["refus"] = f"règle refusée : {e}"
            sortie["correctif_manuel"] = sortie["correctif_manuel"] or sortie["explication"] or sortie["cause"]
    return sortie


def _echec(message):
    return {"ok": False, "erreur": message, "cause": "", "explication": "", "correctif_manuel": "", "regle": None, "refus": ""}


def diagnostique(racine, env, etape, journal, programme=None, delai=DELAI):
    """RuntimeError si un diagnostic est deja en cours ; sinon toujours un dict (`ok` faux + `erreur` en cas d'echec)."""
    if not _DIAGNOSTIC.acquire(blocking=False):
        raise RuntimeError("un diagnostic est déjà en cours")
    try:
        programme = programme or ([shutil.which("claude")] if shutil.which("claude") else None)
        if not programme:
            return _echec("claude introuvable dans le PATH")
        options = rem.OPTIONS + ["--settings", str(rem.reglages_sans_hooks())]
        environ = {k: v for k, v in os.environ.items() if k not in CLES_API}      # abonnement claude.ai, jamais la facturation API
        try:
            p = subprocess.Popen(list(programme) + options, cwd=racine, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, env=environ, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as e:
            return _echec(f"lancement de claude impossible : {e}")
        try:
            sortie, erreur = p.communicate(consigne(env, etape, rep.filtre_secrets(fin_journal(journal))).encode("utf-8"), timeout=delai)
        except subprocess.TimeoutExpired:
            rem._arrete(p)
            try:
                p.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                pass
            return _echec(f"délai de {delai} s dépassé : diagnostic abandonné")
        if p.returncode != 0:
            return _echec(f"claude a échoué (code {p.returncode}) : " + rep.filtre_secrets(erreur.decode("utf-8", "replace")[-300:]))
        try:
            proposition = rem._json_de(rem._resultat(sortie))
        except ValueError as e:
            return _echec(str(e))
        return {"ok": True, "erreur": "", **valide_proposition(proposition, journal, etape)}
    finally:
        _DIAGNOSTIC.release()


def contexte(serie, env):
    """(contexte de l'echec, nom d'etape du catalogue) ; RuntimeError si l'env n'a pas echoue ou si l'etape n'est pas reparable."""
    c = serie.derniers_echecs.get(env)
    if c is None:
        raise RuntimeError(f"{env} : aucun échec enregistré dans cette session de la page")
    nom = rep.ETAPES_SUIVI.get(c["etape"])
    if nom is None:
        raise RuntimeError(f"{env} : seul l'échec d'une compilation, des liens ou du buildfs se diagnostique (un envoi ne se relance pas)")
    return c, nom


def lance_application(serie, env, regle, journal, sondage=0.2):
    """Lance applique_et_relance dans un fil ; RuntimeError si une application est deja en cours."""
    if not _APPLICATION.acquire(blocking=False):
        raise RuntimeError("une application est déjà en cours")

    def travail():
        try:
            applique_et_relance(serie, env, regle, journal, sondage)
        except Exception as e:                          # noqa: BLE001 - le fil ne meurt pas en silence
            serie._ajoute("reparation", env, action="", regle=regle.get("id", ""), etat="echouee",
                          message=rep.filtre_secrets(f"application impossible : {type(e).__name__} : {e}"))
        finally:
            _APPLICATION.release()
    threading.Thread(target=travail, daemon=True).start()


def applique_et_relance(serie, env, regle, journal, sondage=0.2):
    """Attend la fin de la serie en cours, execute les actions de `regle`, relance l'env avec ses actions non reussies ;
    si la relance reussit, la regle entre dans le catalogue local (origine « ia »). Rend {ok, regle_ajoutee, message}."""
    c, nom = contexte(serie, env)
    ligne, action = c["ligne"], c["action"]
    r = rep._valide(regle)
    rp = rep.Reparateur(serie, [r])                    # chemin local = <dossier de la page>/reparations.json
    while serie.en_cours():                            # un seul Serie a la fois
        time.sleep(sondage)
    # shortcut: un build etranger lance entre ce controle et les actions n'est pas vu (la serie ne reserve rien avant lance()) ;
    # serie.lance() le controle encore, mais les actions destructrices seraient deja faites. Fenetre de quelques ms.
    builds = serie.builds_en_cours()
    if builds is None or builds:
        message = ("détection des builds en cours impossible, réessayer" if builds is None
                   else f"un build est en cours ({', '.join(builds)}) : réparation refusée, rien n'a été touché")
        serie._ajoute("reparation", env, action=action, regle=r.id, etat="echouee", message=rep.filtre_secrets(message))
        return {"ok": False, "regle_ajoutee": False, "message": rep.filtre_secrets(message)}
    if not rp.traite(ligne, action, "buildfs" if action == "buildfs" else "", c["etape"], journal, "", regle=r):
        if not rp.historique:
            serie._ajoute("reparation", env, action=action, regle=r.id, etat="echouee", message="la règle ne s'applique pas à ce journal")
        return {"ok": False, "regle_ajoutee": False, "message": "actions non appliquées"}
    n = serie.numero
    try:
        serie.lance([ligne], c["actions"])
    except RuntimeError as e:
        rp._clos(False, f"relance refusée : {rep.filtre_secrets(str(e))}")
        return {"ok": False, "regle_ajoutee": False, "message": "relance refusée"}
    while serie.en_cours():
        time.sleep(sondage)
    fins = [e for e in serie.depuis(n, 0) if e["type"] == "fin_env" and e["env"] == env]
    reussi = bool(fins) and fins[-1]["resultat"] == "succes"
    rp._clos(reussi, "relance réussie" if reussi else "la relance a échoué")
    if reussi:
        rp.ajoute_regle_locale(regle)
        serie._ajoute("reparation", env, action=action, regle=r.id, etat="reussie", message=f"Règle ajoutée au catalogue : {r.titre}")
    return {"ok": reussi, "regle_ajoutee": reussi, "message": "relance réussie" if reussi else "la relance a échoué, rien ajouté"}
