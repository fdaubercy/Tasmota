#!/usr/bin/env python3
"""Reprend une conversation arretee par la limite d'utilisation, des que le compteur est reinitialise (2026-11-01).

Hook `StopFailure` (filtre rate_limit, .claude/settings.json) : une fois la limite atteinte, Claude ne peut plus rien
lancer, donc tout est declenche par ce hook. Il lit session_id, cwd et permission_mode sur stdin, puis demarre une
veille detachee et rend la main aussitot (la sortie d'un hook StopFailure est ignoree).

La veille essaie `claude -p --resume <session>` toutes les 15 minutes :
  - code 0 : reprise faite, fin ;
  - texte de limite (MOTS_LIMITE) : on attend et on recommence, 8 jours au plus (limite hebdomadaire comprise) ;
  - autre echec : 3 de suite et on abandonne (compte ou connexion : attendre n'y changerait rien).
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


def lance_claude(session, cwd, mode):
    """(code, texte) d'une tentative de reprise."""
    claude = shutil.which("claude.cmd") or shutil.which("claude")
    if not claude:
        return 127, "claude introuvable"
    r = subprocess.run([claude, "-p", "--resume", session, "--permission-mode", mode, CONSIGNE], cwd=cwd,
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       stdin=subprocess.DEVNULL)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def veille(session, cwd, mode, lance=lance_claude, dort=time.sleep, horloge=time.time, journal=note):
    """Attend puis retente ; rend "repris", "abandon" ou "delai"."""
    debut, echecs = horloge(), 0
    journal(f"{session} : limite atteinte, veille demarree (mode {mode})")
    while horloge() - debut < DUREE_MAX_S:
        dort(ATTENTE_S)
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
                veille(session, cwd, mode)
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
