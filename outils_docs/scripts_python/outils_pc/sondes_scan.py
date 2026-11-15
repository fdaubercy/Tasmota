"""Releve des sondes et bancs en cours sur ce PC (page « Sondes en cours », plan sondes-en-cours A3).

Deux sources jointes par pid :
    - les processus (UN appel PowerShell Get-CimInstance Win32_Process par releve) : racines Chrome dont la ligne de commande contient « sonde_ »
      (sans --type=) et python dont la ligne de commande contient test_*.py ou banc_*.py ;
    - les fichiers de suivi ecrits par suivi_sondes.py (<dossier de donnees>/sondes/<pid>.json).
Etats : en_cours (vivant, avancement reel) ; sans_suivi (vivant, pas de fichier : duree seulement) ; termine (verdict vert/rouge) ;
disparue (fichier « en_cours » dont le processus est mort) ; orpheline (Chrome de sonde dont le parent est mort).
Les fichiers termine/disparue ne sont gardes que s'ils datent de moins d'une heure (10 termines au plus).
Tout appel externe (PowerShell, vivant, horloge) est injectable : test_sondes_scan.py.
"""

import json
import re
import subprocess
import time
from pathlib import Path

import suivi_sondes

GARDE_S = 3600
MAX_TERMINES = 10
PS = ("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe' or Name='python.exe' or Name='pythonw.exe'\" | Where-Object { $_.CommandLine -match 'sonde_|test_|banc_' } | ForEach-Object { "
      "[pscustomobject]@{ pid = [int]$_.ProcessId; parent = [int]$_.ParentProcessId; nom = $_.Name; ligne = $_.CommandLine; "
      "debut = ([datetimeoffset]$_.CreationDate).ToUnixTimeSeconds() } } | ConvertTo-Json -Compress")
_SCRIPT = re.compile(r"[\w.\-]*\b(?:test|banc)_[\w\-]*\.py", re.I)
_SONDE = re.compile(r"sonde_[\w\-]*")


def lance_ps(commande=PS, delai=40):
    """Execute le releve PowerShell et rend la liste brute des processus ([] si impossible : la page le dit autrement par ses fichiers)."""
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", commande], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=delai)
    if r.returncode != 0:
        raise OSError((r.stderr or "PowerShell a echoue").strip()[:200])
    sortie = r.stdout.strip()
    if not sortie:
        return []
    j = json.loads(sortie)
    return j if isinstance(j, list) else [j]


def processus(ps=lance_ps):
    """Chrome de sonde et python de banc, parmi les processus rendus par `ps` (liste de dicts pid, parent, nom, ligne, debut)."""
    sortie = []
    for p in ps():
        try:
            nom, ligne = str(p.get("nom") or "").lower(), str(p.get("ligne") or "")
            pid, parent, debut = int(p["pid"]), int(p.get("parent") or 0), p.get("debut")
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if nom == "chrome.exe" and "sonde_" in ligne and "--type=" not in ligne:
            m = _SONDE.search(ligne)
            sortie.append({"pid": pid, "parent": parent, "nature": "chrome", "nom": "Chrome " + (m.group(0) if m else "sonde_"), "debut": debut})
        elif nom in ("python.exe", "pythonw.exe", "python3.exe") and _SCRIPT.search(ligne):
            sortie.append({"pid": pid, "parent": parent, "nature": "banc", "nom": Path(_SCRIPT.search(ligne).group(0)).stem, "debut": debut})
    # Le python du venv PlatformIO est un lanceur qui demarre le vrai python avec le meme script : on garde le fils (c'est lui qui ecrit le suivi).
    lanceurs = {p["pid"] for p in sortie for q in sortie if p["nature"] == q["nature"] == "banc" and q["parent"] == p["pid"] and q["nom"] == p["nom"]}
    return [p for p in sortie if p["pid"] not in lanceurs]


PS_UN = ("Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\" | ForEach-Object { "
         "[pscustomobject]@{ pid = [int]$_.ProcessId; parent = [int]$_.ParentProcessId; nom = $_.Name; ligne = $_.CommandLine; "
         "debut = ([datetimeoffset]$_.CreationDate).ToUnixTimeSeconds() } } | ConvertTo-Json -Compress")


def relit_processus(pid, delai=20):
    """Releve NEUF d'un seul processus (dict pid, parent, nom, ligne, debut), ou None s'il n'existe plus. Leve OSError si PowerShell echoue."""
    pid = int(pid)
    liste = lance_ps(PS_UN.format(pid=pid), delai)
    return liste[0] if liste else None


def lit_fichiers(dossier):
    sortie = []
    try:
        fichiers = sorted(Path(dossier).glob("*.json"))
    except OSError:
        return sortie
    for f in fichiers:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(d, dict) and isinstance(d.get("pid"), int):
                sortie.append(d)
        except (OSError, ValueError):
            continue            # fichier en cours d'ecriture ou illisible : ignore
    return sortie


def _s(valeur, limite=300):
    return str(valeur if valeur is not None else "")[:limite]


def _entier(valeur):
    try:
        return int(valeur or 0)
    except (TypeError, ValueError):
        return 0


def liste_sure(valeur, maxi):
    """Les `maxi` derniers elements d'une liste lue dans un fichier de suivi, textes bornes ; [] si la forme est inattendue."""
    if not isinstance(valeur, list):
        return []
    sortie = []
    for v in valeur[-maxi:]:
        if isinstance(v, dict):
            sortie.append({"nom": _s(v.get("nom")), "t": v.get("t") if isinstance(v.get("t"), (int, float)) else 0,
                           "faits": _entier(v.get("faits")), "echecs": _entier(v.get("echecs"))})
        elif isinstance(v, list) and len(v) == 3:
            sortie.append([v[0] if isinstance(v[0], (int, float)) else 0, _s(v[1], 20), _s(v[2])])
    return sortie


def _sonde(pid, parent, nature, nom, debut, duree, faits, total, echecs, phase, dernier, etat, verdict, proc_debut=None, estime=False):
    # proc_debut : heure de creation du PROCESSUS (pas celle du fichier de suivi) : l'arret la reverifie avant de tuer (pid reutilise par Windows)
    return {"pid": pid, "parent": parent, "proc_debut": proc_debut, "nature": nature, "nom": _s(nom, 120), "debut": debut, "duree_s": max(0, int(duree)), "faits": faits,
            "total": total, "echecs": [_s(e) for e in echecs][-20:], "phase": _s(phase), "dernier": _s(dernier), "etat": etat, "verdict": verdict,
            "total_estime": bool(estime and total)}


def releve(procs, fichiers, vivant=suivi_sondes.vivant, maintenant=None):
    """Jointure pure par pid. `procs` : processus() ; `fichiers` : lit_fichiers()."""
    maintenant = time.time() if maintenant is None else maintenant
    par_pid = {f["pid"]: f for f in fichiers}
    sortie, vus = [], set()
    for p in procs:
        vus.add(p["pid"])
        f = par_pid.get(p["pid"])
        debut = (f or {}).get("debut") or p.get("debut") or maintenant
        if f is not None and f.get("etat") in ("en_cours", "termine"):
            echecs = f.get("echecs") or []
            sortie.append(_sonde(p["pid"], p["parent"], p["nature"], f.get("nom") or p["nom"], debut, maintenant - debut, int(f.get("faits") or 0),
                                 f.get("total"), echecs, f.get("phase"), f.get("dernier"), "en_cours", "rouge" if echecs else None, p.get("debut"),
                                 f.get("total_estime")))
        elif p["nature"] == "chrome" and not vivant(p["parent"]):
            sortie.append(_sonde(p["pid"], p["parent"], "chrome", p["nom"], debut, maintenant - debut, 0, None, [], "", "", "orpheline", None, p.get("debut")))
        else:
            sortie.append(_sonde(p["pid"], p["parent"], p["nature"], p["nom"], debut, maintenant - debut, 0, None, [], "", "", "sans_suivi", None, p.get("debut")))
    termines = []
    for f in fichiers:
        if f["pid"] in vus:
            continue
        maj, debut = float(f.get("maj") or 0), float(f.get("debut") or 0)
        if maintenant - maj > GARDE_S:
            continue
        echecs = f.get("echecs") or []
        args = (f["pid"], f.get("parent"), "banc", f.get("nom") or "?", debut, maj - debut, int(f.get("faits") or 0), f.get("total"),
                echecs, f.get("phase"), f.get("dernier"))
        if f.get("etat") == "termine":
            termines.append((maj, _sonde(*args, "termine", "rouge" if echecs else "vert", estime=f.get("total_estime"))))
        elif vivant(f["pid"]):          # sonde vivante que le scan n'a pas reconnue (lancee autrement)
            sortie.append(_sonde(args[0], args[1], "banc", args[3], debut, maintenant - debut, *args[6:], "en_cours", "rouge" if echecs else None, estime=f.get("total_estime")))
        else:
            sortie.append(_sonde(*args, "disparue", "rouge", estime=f.get("total_estime")))
    termines.sort(key=lambda t: -t[0])
    sortie.extend(s for _, s in termines[:MAX_TERMINES])
    ordre = {"en_cours": 0, "orpheline": 1, "sans_suivi": 2, "disparue": 3, "termine": 4}
    sortie.sort(key=lambda s: (ordre[s["etat"]], -(s["debut"] or 0)))
    return sortie
