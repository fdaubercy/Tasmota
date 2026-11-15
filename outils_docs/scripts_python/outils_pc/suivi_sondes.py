"""Suivi de l'avancement REEL des bancs et des sondes (page « Sondes en cours », sondes_web.py, plan sondes-en-cours A1).

UTILISATION : une ligne en tete d'un banc, `import suivi_sondes; suivi_sondes.suit()`  (ou `suit_si_script_test()` pour une aide commune).
    Une enveloppe sur sys.stdout compte les lignes de verdict que le banc imprime deja (rien n'est change a sa sortie) :
        « OK ... »            une verification faite
        « KO ... »/« ECHEC ... »  une verification faite ET en echec (libelle garde, 20 derniers)
        « == ... »            phase en cours (pendant une phase « == temoin... » ou « == mutant... », un KO est ATTENDU : compte comme fait, pas comme echec)
        derniere ligne vue    « dernier cas »
    L'etat est ecrit de facon atomique (.tmp puis os.replace, au plus toutes les 0,3 s sauf echec et fin) dans
    <dossier de donnees>/sondes/<pid>.json ; atexit le passe a « termine ». Un processus tue brutalement reste « en_cours » : le serveur le lit « disparue ».
    Dossier : OUTILS_TASMOTA_DOSSIER, sinon %LOCALAPPDATA%\\outils_tasmota (meme regle que acces_web.dossier_donnees).
    SUIVI_SONDES=0 : sans effet. Ne leve JAMAIS : un echec d'ecriture ne casse pas un banc.
Banc : test_suivi_sondes.py.
"""

import atexit
import json
import os
import re
import sys
import threading
import time
from pathlib import Path

PERIODE_S = 0.3
PURGE_S = 2 * 24 * 3600
MAX_ECHECS = 20
MAX_TEXTE = 300
_OK = re.compile(r"\s*OK\b")
_KO = re.compile(r"\s*(KO|ECHEC)\b")
_PHASE = re.compile(r"\s*==\s*(.*)")
_ACTIF = None            # le suivi en cours de ce processus (un seul)


def dossier_donnees():
    force = os.environ.get("OUTILS_TASMOTA_DOSSIER")
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(force) if force else Path(base) / "outils_tasmota"


def dossier_sondes():
    return dossier_donnees() / "sondes"


def vivant(pid):
    """True si le processus <pid> tourne (Windows : code de sortie 259 = STILL_ACTIVE)."""
    try:
        pid = int(pid)
        if pid <= 0:
            return False
        if os.name == "nt":
            import ctypes
            noyau = ctypes.windll.kernel32
            noyau.OpenProcess.restype = ctypes.c_void_p
            poignee = noyau.OpenProcess(0x1000, False, pid)         # PROCESS_QUERY_LIMITED_INFORMATION
            if not poignee:
                return False
            code = ctypes.c_ulong()
            ok = noyau.GetExitCodeProcess(ctypes.c_void_p(poignee), ctypes.byref(code))
            noyau.CloseHandle(ctypes.c_void_p(poignee))
            return bool(ok) and code.value == 259
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except Exception:
        return False


class Suivi:
    def __init__(self, nom, total, dossier):
        self.verrou = threading.RLock()
        self.dossier = Path(dossier)
        self.etat = {"pid": os.getpid(), "parent": os.getppid(), "nom": nom, "script": os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else "",
                     "debut": time.time(), "maj": time.time(), "total": total, "faits": 0, "echecs": [], "phase": "", "dernier": "", "etat": "en_cours"}
        self.dernier_ecrit = 0.0
        self.tampon = ""
        self.sale = False

    def ligne(self, texte):
        try:
            with self.verrou:
                e = self.etat
                brut = texte.rstrip("\r\n")
                if not brut.strip():
                    return
                force = False
                m = _PHASE.match(brut)
                if m:
                    e["phase"] = m.group(1)[:MAX_TEXTE]
                elif _OK.match(brut):
                    e["faits"] += 1
                elif _KO.match(brut):
                    e["faits"] += 1
                    # KO attendu d'un temoin : pas un echec, sauf le verdict « KO temoin ... » (temoin non detecte)
                    if not e["phase"].startswith(("temoin", "mutant")) or re.match(r"\s*KO\s+(temoin|mutant)", brut):
                        e["echecs"] = (e["echecs"] + [brut.strip()[:MAX_TEXTE]])[-MAX_ECHECS:]
                        force = True
                e["dernier"] = brut.strip()[:MAX_TEXTE]
                self.ecrit(force)
        except Exception:
            pass

    def ecrit(self, force=False):
        try:
            with self.verrou:
                if not force and time.monotonic() - self.dernier_ecrit < PERIODE_S:
                    self.sale = True            # ecriture differee : le fil de _relais() la fera, la derniere ligne ne reste jamais en retard
                    return
                self.sale = False
                self.dernier_ecrit = time.monotonic()
                self.etat["maj"] = time.time()
                self.dossier.mkdir(parents=True, exist_ok=True)
                cible = self.dossier / f"{os.getpid()}.json"
                tmp = cible.with_name(cible.name + ".tmp")
                tmp.write_text(json.dumps(self.etat, ensure_ascii=False), encoding="utf-8")
                os.replace(tmp, cible)
        except Exception:
            pass

    def fin(self):
        try:
            with self.verrou:
                if self.tampon:
                    self.ligne(self.tampon)
                    self.tampon = ""
                self.etat["etat"] = "termine"
                self.ecrit(True)
        except Exception:
            pass


class Enveloppe:
    """Transmet tout a la sortie d'origine, inchange, et passe chaque ligne complete au suivi."""

    def __init__(self, vraie, suivi):
        self._vraie, self._suivi = vraie, suivi

    def write(self, texte):
        retour = self._vraie.write(texte)
        try:
            s = self._suivi
            s.tampon += texte
            while "\n" in s.tampon:
                ligne, s.tampon = s.tampon.split("\n", 1)
                s.ligne(ligne)
        except Exception:
            pass
        return retour

    def __getattr__(self, nom):
        return getattr(self._vraie, nom)


def _purge(dossier):
    try:
        limite = time.time() - PURGE_S
        for f in Path(dossier).glob("*"):
            try:
                if f.stat().st_mtime < limite:
                    f.unlink()
            except OSError:
                pass
    except Exception:
        pass


def _relais(suivi):
    while True:
        time.sleep(PERIODE_S)
        if suivi.sale:
            suivi.ecrit(True)


def suit(nom=None, total=None):
    """A appeler UNE fois en tete d'un banc. Rend le Suivi (ou None si desactive / deja en cours / impossible)."""
    global _ACTIF
    try:
        if _ACTIF is not None or os.environ.get("SUIVI_SONDES") == "0":
            return None
        nom = nom or (Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else "banc")
        dossier = dossier_sondes()
        _purge(dossier)
        _ACTIF = Suivi(nom, total, dossier)
        sys.stdout = Enveloppe(sys.stdout, _ACTIF)
        atexit.register(_ACTIF.fin)
        threading.Thread(target=_relais, args=(_ACTIF,), daemon=True).start()
        _ACTIF.ecrit(True)
        return _ACTIF
    except Exception:
        return None


def suit_si_script_test(nom=None, total=None):
    """Comme suit(), mais seulement si le script lance s'appelle test_*.py ou banc_*.py (un serveur peut importer ce module sans danger)."""
    try:
        base = Path(sys.argv[0]).name if sys.argv and sys.argv[0] else ""
        if re.match(r"(test|banc)_.*\.py$", base) and "--serveur" not in sys.argv:        # --serveur : processus fils d'une sonde, pas un banc
            return suit(nom, total)
    except Exception:
        pass
    return None
