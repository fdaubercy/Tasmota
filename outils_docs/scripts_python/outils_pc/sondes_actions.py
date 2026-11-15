"""Arret des sondes depuis la page « Sondes en cours » (POST /arreter, plan sondes-en-cours A3).

Deux demandes : {"pid": N} ou {"orphelines": true}. Un pid n'est accepte que s'il figure dans le DERNIER releve, vivant, de nature chrome ou banc
(jamais un pid arbitraire : LookupError -> 404). L'arbre est tue par `taskkill /T /F /PID` (liste d'arguments, jamais shell=True) ; l'appel est injectable
(`tue`), le banc ne tue jamais un vrai processus. Banc : test_sondes_web.py.
"""

import os
import subprocess

import sondes_scan

VIVANTS = ("en_cours", "sans_suivi", "orpheline")


def taskkill(pid):
    """(ok, message) : arbre du processus tue par taskkill."""
    r = subprocess.run(["taskkill", "/T", "/F", "/PID", str(int(pid))], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    return r.returncode == 0, (r.stdout or r.stderr).strip()[:200]


def _proteges(releve):
    """Le serveur, son parent et tous ses ancetres connus du releve : `taskkill /T` sur l'un d'eux tuerait le serveur lui-meme."""
    parents = {s["pid"]: s.get("parent") for s in releve}
    proteges, pile = set(), [os.getpid(), os.getppid()]
    while pile:
        p = pile.pop()
        if p and p not in proteges:
            proteges.add(p)
            pile.append(parents.get(p))
    return proteges


def _cibles(releve, pid=None, orphelines=False):
    proteges = _proteges(releve)
    return [s for s in releve if s["nature"] in ("chrome", "banc") and s["etat"] in VIVANTS and s["pid"] not in proteges
            and ((s["etat"] == "orpheline") if orphelines else s["pid"] == pid)]


def meme_processus(s, relit):
    """True si le processus vivant de ce numero est encore CELUI du releve : meme nature, meme nom, meme heure de creation.
    Windows reutilise les numeros : sans cette preuve, un arret tardif pourrait tuer un autre programme de l'utilisateur (et son arbre)."""
    if s.get("proc_debut") is None:
        return False                                          # releve sans heure de creation : on ne tue pas a l'aveugle
    try:
        actuel = relit(s["pid"])
    except Exception:                                         # noqa: BLE001 - PowerShell en panne : on ne tue pas
        return False
    if not actuel:
        return False
    classe = sondes_scan.processus(lambda: [actuel])
    return bool(classe) and classe[0]["nature"] == s["nature"] and classe[0]["debut"] == s["proc_debut"]


def arrete(demande, releve, tue=taskkill, relit=sondes_scan.relit_processus):
    """Applique `demande` au `releve` (dernier releve rendu a la page). Rend {arretes: [...], echecs: [...]}."""
    if demande.get("orphelines") is True:
        cibles = _cibles(releve, orphelines=True)
    else:
        pid = demande.get("pid")
        if isinstance(pid, bool) or not isinstance(pid, int):
            raise ValueError("pid entier attendu")
        cibles = _cibles(releve, pid=pid)
        if not cibles:
            raise LookupError("pid absent du dernier releve (ou deja arrete)")
    arretes, echecs = [], []
    for s in cibles:
        if not meme_processus(s, relit):                      # relu JUSTE avant de tuer
            echecs.append({"pid": s["pid"], "message": "le processus a change ou n'existe plus (numero reutilise) : rien tue"})
            continue
        ok, msg = tue(s["pid"])
        if ok:
            arretes.append(s["pid"])
        else:
            echecs.append({"pid": s["pid"], "message": msg})
    return {"arretes": arretes, "echecs": echecs}
