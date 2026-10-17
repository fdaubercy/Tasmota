"""Lanceur de l'annuaire (port 7600) : lance et arrete les outils PC, capture leur console, Job Object.

- rattache_au_job() : l'annuaire se place lui-meme dans un Job Object Windows
  (JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_BREAKAWAY_OK). Les outils qu'il lance heritent
  du job : la mort de l'annuaire, meme brutale (VS Code ferme, taskkill /F), ferme le dernier handle du
  job et Windows tue tout ce qu'il contient. Le handle est garde dans _JOB jusqu'a la fin du processus.
- Exception : un outil dans_job=False (la synchro du fork : un merge ne doit jamais etre coupe en plein
  vol) est lance avec CREATE_BREAKAWAY_FROM_JOB, et CREATE_NO_WINDOW pour ne pas partager la console de
  l'annuaire (voir DRAPEAUX_HORS_JOB). Si un job parent refuse le breakaway, il est relance sans ce
  drapeau (donc lie a l'annuaire, mais toujours sur sa propre console) : sa console le dit en tete et
  lances[id]["lie"] vaut True (la tuile de la page l'affiche). Seule l'erreur 5 (acces refuse) est
  rattrapee ainsi ; toute autre OSError du lancement remonte.
- La console d'un outil va dans un FICHIER (dossier_donnees()/consoles/<id>.log), jamais un tube : une
  synchro qui survit a l'annuaire ne doit pas ecrire dans un tube casse.
- Arret : taskkill /T /F (l'arbre : le python.exe du penv est un lanceur qui cree un python enfant),
  puis verification de la mort ; un outil qui survit reste dans lances et arrete() rend False.
- derniers.json : derniers parametres choisis par outil, relus au prochain demarrage.
"""

import ctypes
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import acces_web
from annuaire_presence import pid_vivant

JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x800
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASSE = 9
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000
# Hors job (synchro) : sortie du job ET d'une console a elle, cachee. Sans CREATE_NO_WINDOW, l'outil
# resterait attache a la console de l'annuaire (le terminal VS Code) : a sa fermeture, node-pty tue
# chaque processus de GetConsoleProcessList (ou ConPTY envoie CTRL_CLOSE_EVENT), synchro comprise.
# Pas DETACHED_PROCESS : les enfants console (git) ouvriraient alors des fenetres visibles.
DRAPEAUX_HORS_JOB = CREATE_BREAKAWAY_FROM_JOB | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
ERROR_ACCESS_DENIED = 5          # winerror d'un CreateProcess dont le job parent refuse le breakaway
DELAI_ARRET = 5.0                # attente maximale de la mort du processus apres taskkill (s)
LIGNE_LIEE = "[annuaire] synchro liee a l'annuaire (le job parent refuse le breakaway) : " \
             "elle s'arretera avec lui"
ID_VALIDE = re.compile(r"^[a-z0-9_]+$")
TAILLE_LUE = 256 * 1024          # console() ne lit que la fin du fichier

_JOB = None                      # handle du Job Object, garde ouvert jusqu'a la mort du processus
_VERROU = threading.Lock()


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in ("ReadOperationCount", "WriteOperationCount",
                                                  "OtherOperationCount", "ReadTransferCount",
                                                  "WriteTransferCount", "OtherTransferCount")]


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", ctypes.c_uint32), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", ctypes.c_uint32),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", ctypes.c_uint32),
                ("SchedulingClass", ctypes.c_uint32)]


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION), ("IoInfo", _IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


def _kernel32():
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateJobObjectW.restype = ctypes.c_void_p
    k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    k32.SetInformationJobObject.restype = ctypes.c_int
    k32.SetInformationJobObject.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    k32.AssignProcessToJobObject.restype = ctypes.c_int
    k32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.GetCurrentProcess.argtypes = []
    k32.CloseHandle.restype = ctypes.c_int
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    return k32


def _rattache(drapeaux):
    """Cree un job aux drapeaux donnes et y place le processus courant. True si fait (ou deja fait)."""
    global _JOB
    if _JOB is not None:
        return True
    if os.name != "nt":
        print("[annuaire] pas de Job Object hors Windows : les outils survivront a l'annuaire", flush=True)
        return False
    k32 = _kernel32()
    job = k32.CreateJobObjectW(None, None)
    if not job:
        print(f"[annuaire] CreateJobObject a echoue (erreur {ctypes.get_last_error()}) : "
              "les outils survivront a l'annuaire", flush=True)
        return False
    info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = drapeaux
    if not k32.SetInformationJobObject(job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASSE,
                                       ctypes.byref(info), ctypes.sizeof(info)):
        etape = "SetInformationJobObject"
    elif not k32.AssignProcessToJobObject(job, k32.GetCurrentProcess()):
        etape = "AssignProcessToJobObject"
    else:
        _JOB = job               # jamais ferme : sa fermeture (mort du processus) tue le job
        return True
    print(f"[annuaire] {etape} a echoue (erreur {ctypes.get_last_error()}) : "
          "les outils survivront a l'annuaire", flush=True)
    k32.CloseHandle(job)
    return False


def rattache_au_job():
    """Place l'annuaire dans un Job Object tuant tout a sa fermeture, breakaway autorise. Bool."""
    return _rattache(JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_BREAKAWAY_OK)


class Lanceur:
    def __init__(self, racine, python=sys.executable):
        self.racine = Path(racine)
        self.python = python
        self.lances = {}         # id -> {"pid", "valeurs", "lie"}, outils lances depuis ce demarrage
        self._processus = {}     # id -> Popen : garde le handle, le PID ne peut pas etre recycle

    # --- fichiers ---------------------------------------------------------------------------------

    @staticmethod
    def _consoles():
        dossier = acces_web.dossier_donnees() / "consoles"
        dossier.mkdir(parents=True, exist_ok=True)
        return dossier

    @staticmethod
    def _fichier_derniers():
        return acces_web.dossier_donnees() / "derniers.json"

    def derniers(self):
        """{id: valeurs} des derniers parametres choisis ; {} si le fichier manque ou est illisible."""
        try:
            with open(self._fichier_derniers(), encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            return {}
        return d if isinstance(d, dict) else {}

    def memorise(self, id, valeurs):
        with _VERROU:
            d = self.derniers()
            d[id] = dict(valeurs)
            fichier = self._fichier_derniers()
            fichier.parent.mkdir(parents=True, exist_ok=True)
            tmp = fichier.with_name(fichier.name + ".tmp")
            tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, fichier)

    def console(self, id, lignes=200):
        """Les `lignes` dernieres lignes de consoles/<id>.log ; [] si absent ou id hors motif."""
        if not isinstance(id, str) or not ID_VALIDE.match(id):
            return []
        try:
            with open(self._consoles() / f"{id}.log", "rb") as f:
                f.seek(0, os.SEEK_END)
                taille = f.tell()
                f.seek(max(0, taille - TAILLE_LUE))
                brut = f.read()
        except OSError:
            return []
        texte = brut.decode("utf-8", errors="replace").splitlines()
        if taille > TAILLE_LUE and texte:
            texte = texte[1:]    # premiere ligne coupee par le seek
        return texte[-lignes:] if lignes > 0 else []

    # --- processus --------------------------------------------------------------------------------

    def lance(self, outil, args, valeurs=None):
        """Lance l'outil avec ses arguments valides ; rend le PID (celui du python.exe lance)."""
        commande = [self.python, "-u", str(self.racine / outil.script), *args, "--sans-navigateur"]
        env = dict(os.environ, PYTHONUTF8="1", OUTILS_TASMOTA_LANCE_PAR="annuaire")
        drapeaux = 0
        if os.name == "nt" and not outil.dans_job:
            drapeaux = DRAPEAUX_HORS_JOB
        fichier = self._consoles() / f"{outil.id}.log"
        with open(fichier, "wb") as sortie:         # une console par lancement : tronquee
            sortie.write(f"[annuaire] lance {datetime.now():%Y-%m-%d %H:%M:%S}\n".encode("utf-8"))
            sortie.flush()

            def demarre(fl):
                return subprocess.Popen(commande, cwd=str(self.racine), env=env, stdin=subprocess.DEVNULL,
                                        stdout=sortie, stderr=subprocess.STDOUT, creationflags=fl)
            lie = False          # True : breakaway refuse, l'outil hors job a ete relance DANS le job
            try:
                p = demarre(drapeaux)
            except OSError as e:
                # Seul le refus du breakaway (acces refuse) se rattrape ; le reste (python absent...) remonte.
                if not drapeaux & CREATE_BREAKAWAY_FROM_JOB or getattr(e, "winerror", None) != ERROR_ACCESS_DENIED:
                    raise
                sortie.write((LIGNE_LIEE + "\n").encode("utf-8"))
                sortie.flush()
                p = demarre(drapeaux & ~CREATE_BREAKAWAY_FROM_JOB)
                lie = True
        with _VERROU:
            self._processus[outil.id] = p
            self.lances[outil.id] = {"pid": p.pid, "valeurs": dict(valeurs or {}), "lie": lie}
        if valeurs is not None:
            self.memorise(outil.id, valeurs)
        return p.pid

    def _tue_arbre(self, pid):
        """taskkill /T /F /PID (l'arbre) ; code de retour ignore, la mort est verifiee apres."""
        try:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=CREATE_NO_WINDOW, check=False, timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            pass

    def _mort(self, pid):
        """True si le processus est termine (poll() si on tient son Popen, sinon par son PID)."""
        for p in list(self._processus.values()):
            if p.pid == pid:
                return p.poll() is not None
        return not pid_vivant(pid)

    def arrete(self, outil, pid):
        """Tue l'arbre du processus et verifie sa mort (DELAI_ARRET au plus). True si mort.

        lances[id] n'est retire que si son processus est mort : un outil encore vivant reste connu.
        """
        pid = int(pid)
        self._tue_arbre(pid)
        fin = time.monotonic() + DELAI_ARRET
        while not self._mort(pid) and time.monotonic() < fin:
            time.sleep(0.1)
        if not self._mort(pid):
            return False
        # Le PID tue peut etre le python reel (fiche de presence) et lances[id] son lanceur : il suit.
        connu = self.lances.get(outil.id)
        while connu and not self._mort(connu["pid"]) and time.monotonic() < fin:
            time.sleep(0.1)
        with _VERROU:
            connu = self.lances.get(outil.id)
            if connu and self._mort(connu["pid"]):
                self.lances.pop(outil.id, None)
                self._processus.pop(outil.id, None)
        return True
