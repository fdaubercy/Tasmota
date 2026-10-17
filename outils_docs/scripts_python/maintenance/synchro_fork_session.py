"""Execution d'un script de synchro du fork pour la page synchro_fork_web.py.

Le script tourne dans un processus enfant, tel qu'au terminal : memes etapes, memes gardes. Sa sortie
devient une suite d'evenements numerotes (rejoues a un onglet qui se reconnecte), ses questions
(synchro_fork_question.MARQUE) attendent une reponse de la page. Une seule execution a la fois.

Pas d'arret force : tuer un merge ou un rebase en plein vol laisse un MERGE_HEAD ou un rebase a moitie
fait (CLAUDE.md, « Pourquoi le hook ne lance PAS la synchro »). Pour arreter, on repond aux questions ;
a la fermeture du serveur, l'entree standard se ferme et chaque question prend sa reponse prudente.
"""

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import synchro_fork_question

ICI = Path(__file__).resolve().parent
SCRIPTS = {"merge": "synchronise_fork_tasmota.py", "rebase": "synchronise_upstream_tasmota.py"}
MAX_EVENEMENTS = 20000


class Session:
    def __init__(self, dossier=ICI, racine=None, python=sys.executable):
        self.dossier = Path(dossier)
        self.racine = Path(racine) if racine else self.dossier
        self.python = python
        self.verrou = threading.Condition()
        self.evenements = []
        self.numero = 0
        self.proc = None
        self.script = ""
        self.question = None

    # -- evenements ---------------------------------------------------------------------------------

    def _ajoute(self, **evenement):
        with self.verrou:
            self.numero += 1
            evenement["n"] = self.numero
            self.evenements.append(evenement)
            del self.evenements[:-MAX_EVENEMENTS]
            self.verrou.notify_all()

    def depuis(self, n, attente=15.0):
        """Evenements de numero > n ; attend au plus `attente` s s'il n'y en a pas (flux SSE)."""
        with self.verrou:
            if self.numero <= n:
                self.verrou.wait(attente)
            return [e for e in self.evenements if e["n"] > n]

    def en_cours(self):
        with self.verrou:
            return self.proc is not None

    def etat(self):
        with self.verrou:
            return {"en_cours": self.proc is not None, "script": self.script, "question": self.question}

    # -- execution ----------------------------------------------------------------------------------

    def lance(self, script, simulation=False):
        if script not in SCRIPTS:
            raise ValueError(f"script inconnu : {script!r}")
        commande = [self.python, "-u", str(self.dossier / SCRIPTS[script])] + (["--dry-run"] if simulation else [])
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1",
                   GIT_EDITOR="true",           # rebase --continue : message du commit garde tel quel
                   GIT_TERMINAL_PROMPT="0")      # pas d'invite d'identifiants qui bloquerait sans terminal
        env[synchro_fork_question.VARIABLE] = "1"
        with self.verrou:
            if self.proc is not None:
                raise RuntimeError(f"une execution est deja en cours ({self.script})")
            self.proc = subprocess.Popen(commande, cwd=self.racine, env=env, stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, encoding="utf-8", errors="replace", bufsize=1)
            self.script = script
            self.question = None
        self._ajoute(type="debut", script=script, simulation=bool(simulation), commande=" ".join(commande[2:]))
        threading.Thread(target=self._lit, args=(self.proc,), daemon=True).start()

    def _lit(self, proc):
        for ligne in proc.stdout:
            ligne = ligne.rstrip("\n")
            if ligne.startswith(synchro_fork_question.MARQUE):
                try:
                    question = json.loads(ligne[len(synchro_fork_question.MARQUE):])
                except ValueError:
                    question = None
                if isinstance(question, dict):
                    with self.verrou:
                        self.question = question
                    self._ajoute(type="question", **question)
                    continue
            self._ajoute(type="ligne", texte=ligne)
        code = proc.wait()
        with self.verrou:
            self.proc = None
            self.question = None
        self._ajoute(type="fin", script=self.script, code=code)

    def repond(self, valeur, confirmation=""):
        """Transmet une reponse ; refuse ce qui n'est pas un des choix proposes (validation a la frontiere)."""
        with self.verrou:
            question, proc = self.question, self.proc
            if question is None or proc is None:
                raise RuntimeError("aucune question en attente")
            valeurs = [c[0] for c in question.get("choix", [])]
            if valeur not in valeurs:
                raise ValueError(f"reponse hors des choix proposes : {valeur!r}")
            confirme = question.get("confirme")
            if confirme and valeur == valeurs[0] and confirmation != confirme:
                raise ValueError(f"confirmation incorrecte : saisir exactement « {confirme} »")
            self.question = None
            try:
                proc.stdin.write(valeur + "\n")
                proc.stdin.flush()
            except OSError as erreur:
                raise RuntimeError(f"le script ne lit plus ses reponses : {erreur}")
        self._ajoute(type="reponse", valeur=valeur)

    def ferme(self, attente=120):
        """Fermeture du serveur : l'entree standard se ferme (reponses prudentes), on attend la fin."""
        with self.verrou:
            proc = self.proc
        if proc is None:
            return None
        try:
            proc.stdin.close()
        except OSError:
            pass
        try:
            return proc.wait(attente)
        except subprocess.TimeoutExpired:
            return None
