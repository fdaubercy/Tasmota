#!/usr/bin/env python3
"""Reprend une conversation arretee par la limite d'utilisation, des que le compteur est reinitialise (2026-11-01).

Hook `StopFailure` (filtre rate_limit, .claude/settings.json) : une fois la limite atteinte, Claude ne peut plus rien
lancer, donc tout est declenche par ce hook. Il lit session_id, cwd et permission_mode sur stdin, puis demarre une
veille detachee et rend la main aussitot (la sortie d'un hook StopFailure est ignoree).

La veille essaie `claude -p --resume <session>` toutes les 15 minutes :
  - code 0 : reprise faite, fin ;
  - texte de limite (MOTS_LIMITE) : on attend et on recommence, 8 jours au plus (limite hebdomadaire comprise) ;
  - autre echec : 3 de suite et on abandonne (compte ou connexion : attendre n'y changerait rien).
Jamais de session en double (2026-11-13 : 4 conversations ouvertes dans VS Code reprises en meme temps par -p, travaux
faits deux fois et commits croises) : avant chaque tentative, rien n'est lance tant qu'un processus Claude vivant tient la
conversation (registre ~/.claude/sessions/<pid>.json : onglet VS Code, terminal) ; la veille attend sa fermeture. Et
elle s'arrete si le transcript a recu une vraie reponse depuis la limite (reprise a la main ; un message retape pendant
la limite ne laisse qu'une erreur rate_limit et ne compte pas).
Une seule veille par conversation (verrou PID). Ne change jamais de compte et ne contourne aucune limite. Mode de
permission : celui de la conversation, jamais bypassPermissions (remplace par auto). Journal et verrous dans
%LOCALAPPDATA%\\outils_tasmota\\reprise_limite\\.

shortcut: sonde toutes les 15 min au lieu de lire l'heure de reinitialisation, le format d'entree de StopFailure n'ayant
pas pu etre lu ; une sonde refusee ne fait aucun travail. A revoir si le champ d'heure est documente.
Banc : .claude/hooks/test_reprise_limite.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

DOSSIER = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "outils_tasmota" / "reprise_limite"
SESSIONS = Path.home() / ".claude" / "sessions"     # registre de Claude Code : un <pid>.json par processus vivant
PROJETS = Path.home() / ".claude" / "projects"      # transcripts <session>.jsonl
ATTENTE_S = 15 * 60
DUREE_MAX_S = 8 * 24 * 3600
ECHECS_MAX = 3
MOTS_LIMITE = re.compile(r"limit|resets?\b|429|quota", re.I)
SESSION_VALIDE = re.compile(r"^[0-9A-Za-z_-]{8,80}$")
MODES = {"default": "auto", "auto": "auto", "acceptEdits": "acceptEdits", "plan": "plan", "bypassPermissions": "auto"}
CONSIGNE = ("Le compteur d'utilisation est reinitialise. Reprends le travail interrompu de cette conversation la ou il "
            "s'est arrete, selon les autorisations deja donnees. Verifie d'abord qu'aucun build ne tourne. "
            "Si rien n'etait en cours, ne fais rien.")


def note(message, dossier=DOSSIER):
    dossier.mkdir(parents=True, exist_ok=True)
    with open(dossier / "journal.log", "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")


def pid_vivant(pid):
    if os.name == "nt":
        sortie = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, errors="replace")
        return str(pid) in sortie.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def prend_verrou(session, dossier=DOSSIER, vivant=pid_vivant):
    """Vrai si cette veille devient la seule de la conversation ; un verrou d'un processus mort est repris."""
    dossier.mkdir(parents=True, exist_ok=True)
    verrou = dossier / f"{session}.pid"
    try:
        if vivant(int(verrou.read_text(encoding="ascii"))):
            return False
    except (OSError, ValueError):
        pass
    verrou.write_text(str(os.getpid()), encoding="ascii")
    return True


def session_ouverte(session, dossier=SESSIONS, vivant=pid_vivant):
    """PID d'un processus Claude vivant qui tient deja cette conversation (onglet, terminal), sinon None."""
    try:
        fiches = list(dossier.glob("*.json"))
    except OSError:
        return None
    for fiche in fiches:
        try:
            d = json.loads(fiche.read_text(encoding="utf-8"))
            if d.get("sessionId") == session and vivant(int(d["pid"])):
                return int(d["pid"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return None


def surveille_transcript(chemin):
    """Fonction qui dit si le transcript a recu une vraie reponse (assistant, pas une erreur d'API) depuis maintenant."""
    if chemin is None:
        return lambda: False
    try:
        depart = chemin.stat().st_size
    except OSError:
        return lambda: False

    def repris():
        try:
            with open(chemin, "rb") as f:
                f.seek(depart)
                ajout = f.read().decode("utf-8", "replace")
        except OSError:
            return False
        for ligne in ajout.splitlines():
            try:
                d = json.loads(ligne)
            except ValueError:
                continue
            if isinstance(d, dict) and d.get("type") == "assistant" and not d.get("isApiErrorMessage"):
                return True
        return False
    return repris


def transcript(session, projets=PROJETS):
    return next(iter(projets.glob(f"*/{session}.jsonl")), None)


def lance_claude(session, cwd, mode):
    """(code, texte) d'une tentative de reprise."""
    claude = shutil.which("claude.cmd") or shutil.which("claude")
    if not claude:
        return 127, "claude introuvable"
    r = subprocess.run([claude, "-p", "--resume", session, "--permission-mode", mode, CONSIGNE], cwd=cwd,
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       stdin=subprocess.DEVNULL)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def veille(session, cwd, mode, lance=lance_claude, dort=time.sleep, horloge=time.time, journal=note,
           occupee=lambda: None, reprise=lambda: False):
    """Attend puis retente ; rend "repris", "deja_repris", "abandon" ou "delai".
    @occupee : PID du processus qui tient deja la conversation, ou None ; @reprise : vrai si elle a ete reprise ailleurs."""
    debut, echecs, tenue = horloge(), 0, None
    journal(f"{session} : limite atteinte, veille demarree (mode {mode})")
    while horloge() - debut < DUREE_MAX_S:
        dort(ATTENTE_S)
        if reprise():
            journal(f"{session} : conversation reprise ailleurs depuis la limite, veille arretee")
            return "deja_repris"
        pid = occupee()
        if pid:
            if pid != tenue:
                journal(f"{session} : ouverte dans le processus {pid} (onglet ou terminal), pas de reprise en double : attente")
            tenue = pid
            continue
        code, texte = lance(session, cwd, mode)
        if code == 0:
            journal(f"{session} : reprise faite")
            return "repris"
        if MOTS_LIMITE.search(texte):
            echecs = 0
            journal(f"{session} : encore limite")
            continue
        echecs += 1
        journal(f"{session} : echec {echecs}/{ECHECS_MAX}, code {code} : {texte.strip()[:200]}")
        if echecs >= ECHECS_MAX:
            journal(f"{session} : abandon")
            return "abandon"
    journal(f"{session} : abandon, delai depasse")
    return "delai"


def demarre_veille(session, cwd, mode):
    drapeaux = 0
    if os.name == "nt":             # console propre et hors du job : la veille survit a la fermeture de VS Code (lecon 132)
        drapeaux = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_BREAKAWAY_FROM_JOB | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--veille", session, cwd, mode], cwd=cwd,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=drapeaux)


def hook(entree, demarre=demarre_veille):
    """Valide l'entree du hook et demarre la veille ; rend le mode retenu, None si l'entree est inutilisable."""
    try:
        donnees = json.loads(entree)
    except ValueError:
        return None
    session, cwd = str(donnees.get("session_id") or ""), str(donnees.get("cwd") or "")
    if not SESSION_VALIDE.match(session) or not os.path.isdir(cwd):
        return None
    mode = MODES.get(donnees.get("permission_mode"), "auto")
    demarre(session, cwd, mode)
    return mode


def main():
    if len(sys.argv) == 5 and sys.argv[1] == "--veille":
        _, _, session, cwd, mode = sys.argv
        if prend_verrou(session):
            try:
                veille(session, cwd, mode, occupee=lambda: session_ouverte(session),
                       reprise=surveille_transcript(transcript(session)))
            finally:
                (DOSSIER / f"{session}.pid").unlink(missing_ok=True)
        return 0
    try:
        hook(sys.stdin.read())
    except Exception as erreur:                     # noqa: BLE001 - un hook ne doit jamais gener Claude Code
        note(f"hook en echec : {erreur!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
